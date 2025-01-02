from datetime import datetime, timedelta
from time import sleep
from threading import Thread

from .subplugin import OctoAppSubPlugin
from octoapp.notificationshandler import NotificationsHandler, StoppableThread
from octoapp.sentry import Sentry
from octoapp.layerutils import LayerUtils
from octoapp.notificationutils import NotificationUtils
from octoprint.filemanager import FileManager

class OctoAppNotificationsSubPlugin(OctoAppSubPlugin):

    def __init__(self, parent, notification_handler: NotificationsHandler):
        super().__init__(parent)
        self.NotificationHandler = notification_handler
        self._hasPrintTimeGenius = self.parent._plugin_manager.get_plugin("PrintTimeGenius") is not None
        self.Progress = 0
        self.GcodeSentCount = 0
        self.LayerMagicDisabledAt = datetime.fromtimestamp(0)
        self.FirstLayerDoneCommands = LayerUtils.CreateLayerChangeCommands(1)
        self.ThirdLayerDoneCommands = LayerUtils.CreateLayerChangeCommands(3)
        self.ScheduledNotifications = None
        self.ScheduledNotificationsThread = {}
        self.LastFilePos = 0

    def _getPrinterName(self):
        name = self.parent._settings.global_get(
            ["appearance", "name"]
        )

        if name == "" or name is None:
            name = "OctoPrint"

        return name


    def OnAfterStartup(self):
        self.NotificationHandler.NotificationSender.PrinterName = self._getPrinterName()
        Sentry.Info("NOTIFICATION",  "Has PrintTimeGenius: %s" % self._hasPrintTimeGenius)

    
    def OnCurrentData(self, data):
        filePos = data.get("progress", {}).get("filepos", None)
        if filePos != self.LastFilePos and self.ScheduledNotifications is not None and self.NotificationHandler is not None:
            NotificationUtils.SendScheduledNotifications(self.ScheduledNotifications, self.NotificationHandler, filePos, self.LastFilePos)
            self.LastFilePos = filePos


    def OnPrintProgress(self, storage, path, progress):
        self._updateProgressAndSendIfChanged()


    def OnEvent(self, event, payload):       
        self._updateProgressAndSendIfChanged()

        # Only check the event after the notification handler has been created.
        # Specifically here, we have seen the Error event be fired before `on_startup` is fired,
        # and thus the handler isn't created.
        if self.NotificationHandler is None:
            return

        # Ensure there's a payload
        if payload is None:
            payload = {}

        # Listen for the rest of these events for notifications.
        # OctoPrint Events
        # self.LayerMagic might be set before the PrintStarted event, so do not reset on start but end of print
        if event == "PrintStarted":
            self.Progress = 0
            self.LastFilePos = 0
            self.GcodeSentCount = 0
            Sentry.Info("NOTIFICATION", "Print started")
            fileName = self.GetDictStringOrEmpty(payload, "name")
            path = self.GetDictStringOrEmpty(payload, "path")
            origin = self.GetDictStringOrEmpty(payload, "origin")
            # Gather some stats from other places, if they exist.
            currentData = self.parent._printer.get_current_data()
            fileSizeKBytes = 0
            if self._exists(currentData, "job") and self._exists(currentData["job"], "file") and self._exists(currentData["job"]["file"], "size"):
                fileSizeKBytes = int(currentData["job"]["file"]["size"]) / 1024
            totalFilamentUsageMm = 0
            if self._exists(currentData, "job") and self._exists(currentData["job"], "filament") and self._exists(currentData["job"]["filament"], "tool0") and self._exists(currentData["job"]["filament"]["tool0"], "length"):
                totalFilamentUsageMm = int(currentData["job"]["filament"]["tool0"]["length"])
            self._updateProgressAndSendIfChanged()
            self.NotificationHandler.OnStarted(fileName, fileSizeKBytes, totalFilamentUsageMm)
            self._extractScheduledNotificationsIfNotStoppedBefore(origin, path)

        elif event == "PrintFailed" or event == "PrintCancelled":
            fileName = self.GetDictStringOrEmpty(payload, "name")
            durationSec = self.GetDictStringOrEmpty(payload, "time")
            reason = self.GetDictStringOrEmpty(payload, "reason")
            self.NotificationHandler.OnFailed(fileName, durationSec, reason)
            self.LayerMagicDisabledAt = datetime.fromtimestamp(0)
        elif event == "PrintDone":
            fileName = self.GetDictStringOrEmpty(payload, "name")
            durationSec = self.GetDictStringOrEmpty(payload, "time")
            self.NotificationHandler.OnDone(fileName, durationSec)
            self.LayerMagicDisabledAt = datetime.fromtimestamp(0)
        elif event == "PrintPaused":
            fileName = self.GetDictStringOrEmpty(payload, "name")
            self.NotificationHandler.OnPaused(fileName)
        elif event == "PrintResumed":
            fileName = self.GetDictStringOrEmpty(payload, "name")
            self.NotificationHandler.OnResume(fileName)

        # Printer Connection
        elif event == "Error":
            error = self.GetDictStringOrEmpty(payload, "error")
            self.NotificationHandler.OnError(error)

        # GCODE Events
        # Note most of these aren't sent when printing from the SD card
        elif event == "Waiting":
            self.NotificationHandler.OnWaiting()
        elif event == "FilamentChange":
            # We also handle some of these filament change gcode events ourselves, but since we already have
            # anti duplication logic in the notification handler for this event, might as well send it here as well.
            self.NotificationHandler.OnFilamentChange()
        elif event == "SettingsUpdated":
            # Name might have changed
            self.NotificationHandler.NotificationSender.PrinterName = self._getPrinterName()


    def OnGcodeQueued(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        # Check for our layer commands
        if cmd in LayerUtils.DisableLegacyLayerCommands:
            Sentry.Info("NOTIFICATION", "Layer magic disabled")
            self.LayerMagicDisabledAt = datetime.now()
            return False

        if cmd in self.FirstLayerDoneCommands and self.NotificationHandler:
            self.NotificationHandler.OnFirstLayerDone()
            return False
        
        if cmd in self.ThirdLayerDoneCommands and self.NotificationHandler:
            self.NotificationHandler.OnThirdLayerDone()
            return False
        
        message = NotificationUtils.GetMessageIfNotifyCommand(cmd)
        if message is not None and self.NotificationHandler:
            self.NotificationHandler.OnCustomNotification(message)
            return False
        
        if LayerUtils.IsOctoAppCommand(cmd):
            return False
        
        return True


    def OnGcodeSent(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        # Blocking will block the printer commands from being handled so we can't block here!

        # Check for progress updates every 250 gcode commands. If we have PrintTimeGenius the
        # progress shown to the user might update outside of OctoPrint's progress updates, so 
        # to keep up we regularly check during the print
        self.GcodeSentCount = self.GcodeSentCount + 1
        if self.GcodeSentCount % 250 == 0 and self._hasPrintTimeGenius:
            self._updateProgressAndSendIfChanged()

        # M600 is a filament change command.
        # https://marlinfw.org/docs/gcode/M600.html
        # We check for this both in sent and received, to make sure we cover all use cases. The OnFilamentChange will only allow one notification to fire every so often.
        # This M600 usually comes from filament change required commands embedded in the gcode, for color changes and such.
        if self.NotificationHandler is not None and gcode and gcode == "M600":
            Sentry.Info("NOTIFICATION", "Firing On Filament Change Notification From GcodeSent: "+str(gcode))
            # No need to use a thread since all events are handled on a new thread.
            self.NotificationHandler.OnFilamentChange()

        # M0 is a pause command
        # https://marlinfw.org/docs/gcode/M000-M001.html
        # We check for this both in sent and received, to make sure we cover all use cases. The OnUserInteractionNeeded will only allow one notification to fire every so often.
        if self.isPauseCommand(gcode):
            Sentry.Info("NOTIFICATION", "Firing On User Interaction Required From GcodeSent: "+str(gcode))
            # No need to use a thread since all events are handled on a new thread.
            self.NotificationHandler.OnUserInteractionNeeded()

    def OnGcodeReceived(self, comm_instance, line, *args, **kwargs):
        # Blocking will block the printer commands from being handled so we can't block here!

        if line and self.NotificationHandler is not None:
            # ToLower the line for better detection.
            lineLower = line.lower()

            # M600 is a filament change command.
            # https://marlinfw.org/docs/gcode/M600.html
            # On my Pursa, I see this "fsensor_update - M600" AND this "echo:Enqueuing to the front: "M600""
            # We check for this both in sent and received, to make sure we cover all use cases. The OnFilamentChange will only allow one notification to fire every so often.
            # This m600 usually comes from when the printer sensor has detected a filament run out.
            if "m600" in lineLower or "fsensor_update" in lineLower:
                Sentry.Info("NOTIFICATION", "Firing On Filament Change Notification From GcodeReceived: "+str(line))
                # No need to use a thread since all events are handled on a new thread.
                self.NotificationHandler.OnFilamentChange()
            elif "m300" in lineLower:
                timeLeft = self.NotificationHandler.PrinterStateInterface.GetPrintTimeRemainingEstimateInSeconds()
                progress = self.NotificationHandler.PrinterStateInterface.GetCurrentProgress()

                if timeLeft > 30 or (progress < 95 and progress >= 0):
                    Sentry.Debug("NOTIFICATION", "Performing beep, %s seconds left and %s percent" % (timeLeft, progress))    
                    self.NotificationHandler.OnBeep()
                else:
                    Sentry.Debug("NOTIFICATION", "Skipping beep, only %s seconds left and %s percent" % (timeLeft, progress)) 

            # Look for a line indicating user interaction is needed.
            elif self.isPauseCommand(lineLower):
                Sentry.Info("NOTIFICATION", "Firing On User Interaction Required From GcodeReceived: "+str(line))
                # No need to use a thread since all events are handled on a new thread.
                self.NotificationHandler.OnUserInteractionNeeded()

        # We must return line the line won't make it to OctoPrint!
        return line
    
    def isPauseCommand(self, line: str):
        lineLower = line.lower() if line is not None else ""
        return "paused for user" in lineLower or "// action:paused" in lineLower or "//action:pause" in lineLower or "@pause" in lineLower or "m0" == lineLower

    # A dict helper
    def _exists(self, dictObj:dict, key:str) -> bool:
        return key in dictObj and dictObj[key] is not None


    def GetDictStringOrEmpty(self, d, key):
        return str(d.get(key, ""))


    # Gets the current setting or the default value.
    def GetBoolFromSettings(self, name, default):
        value = self._settings.get([name])
        if value is None:
            return default
        return value is True


    # Gets the current setting or the default value.
    def GetFromSettings(self, name, default):
        value = self._settings.get([name])
        if value is None:
            return default
        return value
    

    # Depending on if we have PrintTimeGenius, use OctoPrints progress or emulate the PrintTimeGenius calculation 
    # (based on the printTimeLeft which is modified by PrintTimeGenius)
    def _updateProgressAndSendIfChanged(self):
        progressDict = self.parent._printer.get_current_data().get("progress", {})
        printTimeLeft = progressDict["printTimeLeft"]
        printTime = progressDict["printTime"]
        completion = progressDict["completion"]
        lastProgress = self.Progress

        if completion is None or printTime is None:
            return

        if self._hasPrintTimeGenius and printTime is not None and printTimeLeft is not None:
            self.Progress = int((printTime / float(printTime + printTimeLeft)) * 100.0)
        else:
            self.Progress = int(completion)

        if self.Progress != lastProgress and self.NotificationHandler is not None:
            Sentry.Debug("NOTIFICATION", "Progress change: %s -> %s" % (lastProgress, self.Progress))
            self.NotificationHandler.OnPrintProgress(self.Progress, None)


    def _extractScheduledNotificationsIfNotStoppedBefore(self, origin, path):
        def doLoad():
            try:
                if origin != "local":
                    Sentry.Info("NOTIFICATION", "Unsupported origin for layer magic: %s" % origin)
                    return
            
                sleep(5)
                if (datetime.now() - self.LayerMagicDisabledAt) < timedelta(seconds=10):
                    Sentry.Info("NOTIFICATION", "Layer magic was disabled, stopping")
                    return
            
           
                diskPath = self.parent._file_manager.path_on_disk(origin, path)
                Sentry.Info("NOTIFICATION", "Processing file at %s for layer magic" % path)
                with open(diskPath, 'r') as stream:
                    self.ScheduledNotifications = NotificationUtils.ExtractNotifications(stream, stopAfterLayer3 = True)
            except Exception as e:
                Sentry.ExceptionNoSend("Failed to process file for notifications", e)

        if self.ScheduledNotificationsThread:
            self.ScheduledNotificationsThread.stop()

        self.ScheduledNotifications = None
        self.ScheduledNotificationsThread = StoppableThread(target = doLoad, daemon=True)
        self.ScheduledNotificationsThread.start()
        
    