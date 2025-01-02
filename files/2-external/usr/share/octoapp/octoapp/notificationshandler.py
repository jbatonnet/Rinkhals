import math
import time
import io
import threading
import random
import string
import logging

import requests

from .gadget import Gadget
from .sentry import Sentry
from .compat import Compat
from .snapshotresizeparams import SnapshotResizeParams
from .repeattimer import RepeatTimer
from .webcamhelper import WebcamHelper
from .finalsnap import FinalSnap
from .notificationsender import NotificationSender

try:
    # On some systems this package will install but the import will fail due to a missing system .so.
    # Since most setups don't use this package, we will import it with a try catch and if it fails we
    # won't use it.
    from PIL import Image
    from PIL import ImageFile
except Exception as _:
    pass

class ProgressCompletionReportItem:
    def __init__(self, value, reported):
        self.value = value
        self.reported = reported

    def Value(self):
        return self.value

    def Reported(self):
        return self.reported

    def SetReported(self, reported):
        self.reported = reported

class NotificationsHandler:

    # This is the max snapshot file size we will allow to be sent.
    MaxSnapshotFileSizeBytes = 2 * 1024 * 1024

    # The length of the random print id. This must be a large number, since it needs to be
    # globally unique. This value must stay in sync with the service.
    PrintIdLength = 60

    def __init__(self, printerStateInterface):
        # On init, set the key to empty.
        self.OctoKey = None
        self.PrinterId = None
        self.PrinterStateInterface = printerStateInterface
        self.NotificationSender = NotificationSender()
        self.ProgressTimer = None
        self.FinalSnapObj:FinalSnap = None
        self.PauseThread = None
        # self.Gadget = Gadget(logger, self, self.PrinterStateInterface)

        # Define all the vars
        self.CurrentFileName = ""
        self.CurrentFileSizeInKBytes = 0
        self.CurrentEstFilamentUsageMm = 0
        self.CurrentPrintStartTime = time.time()
        self.FallbackProgressInt = 0
        self.MoonrakerReportedProgressFloat_CanBeNone = None
        self.PingTimerHoursReported = 0
        self.ProgressCompletionReported = []
        self.PrintId = "none"
        self.PrintStartTimeSec = 0
        self.RestorePrintProgressPercentage = False
        self.CustomNotificationCounter = 0
        self.CustomNotificationLimit = 10

        self.SpammyEventTimeDict = {}
        self.SpammyEventLock = threading.Lock()

        # Since all of the commands don't send things we need, we will also track them.
        self.ResetForNewPrint(None)


    def ResetForNewPrint(self, restoreDurationOffsetSec_OrNone):
        self.CurrentFileName = ""
        self.CurrentFileSizeInKBytes = 0
        self.CurrentEstFilamentUsageMm = 0
        self.CurrentPrintStartTime = time.time()
        self.FallbackProgressInt = 0
        self.MoonrakerReportedProgressFloat_CanBeNone = None
        self.PingTimerHoursReported = 0
        self.RestorePrintProgressPercentage = False

        # Ensure there's no final snap running.
        self._getFinalSnapSnapshotAndStop()

        # If we have a restore time offset, back up the start time to make it reflect when the print started.
        if restoreDurationOffsetSec_OrNone is not None:
            self.CurrentPrintStartTime -= restoreDurationOffsetSec_OrNone

        # Each time a print starts, we generate a fixed length random id to identify it.
        # This id is used to globally identify the print for the user, so it needs to have high entropy.
        self.PrintId = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=NotificationsHandler.PrintIdLength))

        # Note the time this print started
        self.PrintStartTimeSec = time.time()

        # Reset our anti spam times.
        self._clearSpammyEventContexts()

        # Build the progress completion reported list.
        # Add an entry for each progress we want to report, not including 0 and 100%.
        # This list must be in order, from the lowest value to the highest.
        # See _getCurrentProgressFloat for usage.
        self.ProgressCompletionReported = []
        for x in range(1, 100):
            self.ProgressCompletionReported.append(ProgressCompletionReportItem(x, False))

    def GetPrintId(self) -> str:
        return self.PrintId

    def GetPrintStartTimeSec(self):
        return self.PrintStartTimeSec

    # Hints at if we are tracking a print or not.
    def IsTrackingPrint(self) -> bool:
        return self._IsPingTimerRunning()


    # A special case used by moonraker to restore the state of an ongoing print that we don't know of.
    # What we want to do is check moonraker's current state and our current state, to see if there's anything that needs to be synced.
    # Remember that we might be syncing because our service restarted during a print, or moonraker restarted, so we might already have
    # the correct context.
    #
    # Most importantly, we want to make sure the ping timer and thus Gadget get restored to the correct states.
    #
    def OnRestorePrintIfNeeded(self, moonrakerPrintStatsState, fileName_CanBeNone, totalDurationFloatSec_CanBeNone):
        if moonrakerPrintStatsState == "printing":
            # There is an active print. Check our state.
            if self._IsPingTimerRunning():
                Sentry.Info("NOTIFICATION", "Moonraker client sync state: Detected an active print and our timers are already running, there's nothing to do.")
                return
            else:
                Sentry.Info("NOTIFICATION", "Moonraker client sync state: Detected an active print but we aren't tracking it, so we will restore now.")
                # We need to do the restore of a active print.
        elif moonrakerPrintStatsState == "paused":
            # There is a print currently paused, check to see if we have a filename, which indicates if we know of a print or not.
            if self._HasCurrentPrintFileName():
                Sentry.Info("NOTIFICATION", "Moonraker client sync state: Detected a paused print, but we are already tracking a print, so there's nothing to do.")
                return
            else:
                Sentry.Info("NOTIFICATION", "Moonraker client sync state: Detected a paused print, but we aren't tracking any prints, so we will restore now")
        else:
            # There's no print running.
            if self._IsPingTimerRunning():
                Sentry.Info("NOTIFICATION", "Moonraker client sync state: Detected no active print but our ping timers ARE RUNNING. Stopping them now.")
                self.StopTimers()
                return
            else:
                Sentry.Info("NOTIFICATION", "Moonraker client sync state: Detected no active print and no ping timers are running, so there's nothing to do.")
                return

        # If we are here, we need to restore a print.
        # The print can be in an active or paused state.

        # Always restart for a new print.
        # If totalDurationFloatSec_CanBeNone is not None, it will update the print start time to offset it correctly.
        # This is important so our time elapsed number is correct.
        self.ResetForNewPrint(totalDurationFloatSec_CanBeNone)

        # Always set the file name, if not None
        if fileName_CanBeNone is not None:
            self._updateCurrentFileName(fileName_CanBeNone)

        # Set this flag so the first progress update will restore the progress to the current progress without
        # firing all of the progress points we missed.
        self.RestorePrintProgressPercentage = True

        # Make sure the timers are set correctly
        if moonrakerPrintStatsState == "printing":
            # If we have a total duration, use it to offset the "hours reported" so our time based notifications
            # are correct.
            hoursReportedInt = 0
            if totalDurationFloatSec_CanBeNone is not None:
                # Convert seconds to hours, floor the value, make it an int.
                hoursReportedInt = int(math.floor(totalDurationFloatSec_CanBeNone / 60.0 / 60.0))

            # Setup the timers, with hours reported, to make sure that the ping timer and Gadget are running.
            Sentry.Info("NOTIFICATION", "Moonraker client sync state: Restoring printing timer with existing duration of "+str(totalDurationFloatSec_CanBeNone))
            self.StartPrintTimers(False, hoursReportedInt)
        else:
            # On paused, make sure they are stopped.
            self.StopTimers()

    def _cancelDelayedPause(self):
        if self.PauseThread is not None and self.PauseThread.is_alive():
            Sentry.Info("NOTIFICATION", "Cancelling delayed pause")
            self.PauseThread.stop()
            self.PauseThread = None

    # Only used for testing.
    def OnTest(self):
        if self._shouldIgnoreEvent():
            return
        self._sendEvent("test")


    # Only used for testing.
    def OnGadgetWarn(self):
        if self._shouldIgnoreEvent():
            return
        self._sendEvent("gadget-warning")


    # Only used for testing.
    def OnGadgetPaused(self):
        if self._shouldIgnoreEvent():
            return
        self._sendEvent("gadget-paused")


    # Fired when a print starts.
    def OnStarted(self, fileName:str, fileSizeKBytes:int, totalFilamentUsageMm:int):
        if self._shouldIgnoreEvent(fileName):
            return
        self.ResetForNewPrint(None)
        self._updateCurrentFileName(fileName)
        self.CurrentFileSizeInKBytes = fileSizeKBytes
        self.CurrentEstFilamentUsageMm = totalFilamentUsageMm
        self.StartPrintTimers(True, None)
        self.CustomNotificationCounter = 0
        self._sendEvent(NotificationSender.EVENT_STARTED)
        Sentry.Info("NOTIFICATION", f"New print started; PrintId: {str(self.PrintId)} file:{str(self.CurrentFileName)} size:{str(self.CurrentFileSizeInKBytes)} filament:{str(self.CurrentEstFilamentUsageMm)}")


    # Triggered by a Gcode command
    def OnCustomNotification(self, message, unlimited = False):
        if unlimited:
            self._sendEvent(NotificationSender.EVENT_CUSTOM, { NotificationSender.STATE_CUSTOM_EVENT_MESSAGE: message })
        if self.CustomNotificationCounter < self.CustomNotificationLimit:
            self.CustomNotificationCounter += 1
            self._sendEvent(NotificationSender.EVENT_CUSTOM, { NotificationSender.STATE_CUSTOM_EVENT_MESSAGE: message })
        elif self.CustomNotificationCounter == self.CustomNotificationLimit:
            self.CustomNotificationCounter += 1
            self._sendEvent(NotificationSender.EVENT_CUSTOM, { NotificationSender.STATE_CUSTOM_EVENT_MESSAGE: "You reached the limit of %d Gcode notifications for this print" % self.CustomNotificationLimit })


    # Fired when a print fails
    def OnFailed(self, fileName, durationSecStr, reason):
        if self._shouldIgnoreEvent(fileName):
            return
        self._updateCurrentFileName(fileName)
        self._updateToKnownDuration(durationSecStr)
        self.StopTimers()
        self._cancelDelayedPause()
        self._sendEvent(NotificationSender.EVENT_CANCELLED, { "Reason": reason})


    # Fired when a print done
    # For moonraker, these vars aren't known, so they are None
    def OnDone(self, fileName_CanBeNone, durationSecStr_CanBeNone):
        if self._shouldIgnoreEvent(fileName_CanBeNone):
            return
        self._updateCurrentFileName(fileName_CanBeNone)
        self._updateToKnownDuration(durationSecStr_CanBeNone)
        self.StopTimers()
        self._cancelDelayedPause()
        self._sendEvent(NotificationSender.EVENT_DONE, useFinalSnapSnapshot=True)


    # Fired when a print is paused
    def OnPaused(self, fileName):
        if self._shouldIgnoreEvent(fileName):
            return
        
        def firePause(delay, event):
            _self = self.PauseThread 
            Sentry.Info("NOTIFICATION", "Delaying pause for %d seconds" % delay)
            time.sleep(delay)
            if _self.stopped() is False:
                Sentry.Info("NOTIFICATION", "Delayed pause not stopped, executing")
                self._sendEvent(event)
                self.PauseThread = None
            else: 
                 Sentry.Info("NOTIFICATION", "Delayed pause was stopped, dropping")
            
        def scheduleSent(delay, event):
            if self.PauseThread is None or self.PauseThread.is_alive() is False:
                if delay == 0:
                    self._sendEvent(event)
                else:
                    self.PauseThread = StoppableThread(target=firePause, args=(delay, event))
                    self.PauseThread.start()
            else:
                Sentry.Error("NOTIFICATION", "Skipping pause, already scheduled")

        # Always update the file name.
        self._updateCurrentFileName(fileName)

        delay = 0
        event = NotificationSender.EVENT_PAUSED
        if Compat.IsMoonraker():
            # Because filament runout doesn't work, let's treat every pause as "interaction needed"
            # Also delay in case of timlapse photo the pause will be super short. If the print is resumed within the delay, drop the pause
            delay = 3
            event = NotificationSender.EVENT_USER_INTERACTION_NEEDED

        # See if there is a pause notification suppression set. If this is not null and it was recent enough
        # suppress the notification from firing.
        # If there is no suppression, or the suppression was older than 30 seconds, fire the notification.
        if Compat.HasSmartPauseInterface():
            lastSuppressTimeSec = Compat.GetSmartPauseInterface().GetAndResetLastPauseNotificationSuppressionTimeSec()
            if lastSuppressTimeSec is None or time.time() - lastSuppressTimeSec > 20.0:
                scheduleSent(delay, event)
            else:
                Sentry.Info("NOTIFICATION", "Not firing the pause notification due to a Smart Pause suppression.")
        else:
            scheduleSent(delay, event)

        # Stop the ping timer, so we don't report progress while we are paused.
        self.StopTimers()

    # Fired when a print is resumed
    def OnResume(self, fileName):
        if self._shouldIgnoreEvent(fileName):
            return
        
        self._cancelDelayedPause()
        self._updateCurrentFileName(fileName)
        self._sendEvent(NotificationSender.EVENT_RESUME)

        # Clear any spammy event contexts we have, assuming the user cleared any issues before resume.
        self._clearSpammyEventContexts()

        # Start the ping timer, to ensure it's running now.
        self.StartPrintTimers(False, None)


    # Fired when OctoPrint or the printer hits an error.
    def OnError(self, error):
        if self._shouldIgnoreEvent():
            return

        self.StopTimers()
        self._cancelDelayedPause()

        # This might be spammy from OctoPrint, so limit how often we bug the user with them.
        if self._shouldSendSpammyEvent("on-error"+str(error), 30.0) is False:
            return

        self._sendEvent(NotificationSender.EVENT_ERROR, {"Error": error })


    # Fired when the waiting command is received from the printer.
    def OnWaiting(self):
        if self._shouldIgnoreEvent():
            return
        # Make this the same as the paused command.
        self.OnPaused(self.CurrentFileName)


    # Fired when we get a M600 command from the printer to change the filament
    def OnFilamentChange(self):
        if self._shouldIgnoreEvent():
            return
        # This event might fire over and over or might be paired with a filament change event.
        # In any case, we only want to fire it every so often.
        # It's important to use the same key to make sure we de-dup the possible OnUserInteractionNeeded that might fire second.
        if self._shouldSendSpammyEvent("user-interaction-needed", 5.0) is False:
            return

        # Otherwise, send it.
        self._sendEvent(NotificationSender.EVENT_FILAMENT_REQUIRED)


    # Fired when the printer needs user interaction to continue
    def OnUserInteractionNeeded(self):
        if self._shouldIgnoreEvent():
            return
        # This event might fire over and over or might be paired with a filament change event.
        # In any case, we only want to fire it every so often.
        # It's important to use the same key to make sure we de-dup the possible OnUserInteractionNeeded that might fire second.
        if self._shouldSendSpammyEvent("user-interaction-needed", 5.0) is False:
            return

        # Otherwise, send it.
        self._sendEvent(NotificationSender.EVENT_USER_INTERACTION_NEEDED)

    # Fired when the first layer is completed
    def OnFirstLayerDone(self):
        self._sendEvent(NotificationSender.EVENT_FIRST_LAYER_DONE)

     # Fired when the third layer is completed
    def OnThirdLayerDone(self):
        self._sendEvent(NotificationSender.EVENT_THIRD_LAYER_DONE)
    
     # Fired when the printer needs user interaction to continue
    def OnBeep(self):
        if self._shouldIgnoreEvent():
            return
        
        # This event might fire over and over or might be paired with a filament change event.
        # In any case, we only want to fire it every so often.
        # It's important to use the same key to make sure we de-dup the possible OnUserInteractionNeeded that might fire second.
        if self._shouldSendSpammyEvent("beep", 5.0) is False:
            return

        # Otherwise, send it.
        self._sendEvent(NotificationSender.EVENT_BEEP)


    # Fired when a print is making progress.
    def OnPrintProgress(self, octoPrintProgressInt, moonrakerProgressFloat):
        if self._shouldIgnoreEvent():
            return

        # Always set the fallback progress, which will be used if something better can be found.
        # For moonraker, make sure to set the reported float. See _getCurrentProgressFloat about why.
        #
        # Note that in moonraker this is called very frequently, so this logic must be fast!
        #
        if octoPrintProgressInt is not None:
            self.FallbackProgressInt = octoPrintProgressInt
        elif moonrakerProgressFloat is not None:
            self.FallbackProgressInt = int(moonrakerProgressFloat)
            self.MoonrakerReportedProgressFloat_CanBeNone = moonrakerProgressFloat
        else:
            Sentry.Error("NOTIFICATION", "OnPrintProgress called with no args!")
            return

        # Get the computed print progress value. (see _getCurrentProgressFloat about why)
        computedProgressFloat = self._getCurrentProgressFloat()

        # If we are near the end of the print, start the final snap image capture system, to ensure we get a good "done" image.
        # This is a tricky number to set. For long prints, 1% can be very long, where as for quick prints we might not even see
        # all of the % updates.
        # First of all, don't bother unless the % complete is > 90% (this also guards from divide by 0)
        # if computedProgressFloat > 90.0 and self.FinalSnapObj is None:
        #     currentTimeSec = self.GetCurrentDurationSecFloat()
        #     estTimeRemainingSec = (self.GetCurrentDurationSecFloat() * 100.0) / computedProgressFloat
        #     estTimeUntilCompleteSec = estTimeRemainingSec - currentTimeSec
        #     # If we guess the print will be done in less than one minute, then start the final snap system.
        #     if estTimeUntilCompleteSec < 60.0:
        #         if self.FinalSnapObj is None:
        #             self.FinalSnapObj = FinalSnap(self)

        # Since we are computing the progress based on the ETA (see notes in _getCurrentProgressFloat)
        # It's possible we get duplicate ints or even progresses that goes back in time.
        # To account for this, we will make sure we only send the update for each progress update once.
        # We will also collapse many progress updates down to one event. For example, if the progress went from 5% -> 45%, we wil only report once for 10, 20, 30, and 40%.
        # We keep track of the highest progress that hasn't been reported yet.
        progressToSendFloat = 0.0
        for item in self.ProgressCompletionReported:
            # Keep going through the items until we find one that's over our current progress.
            # At that point, we are done.
            if item.Value() > computedProgressFloat:
                break

            # If we are over this value and it's not reported, we need to report.
            # Since these items are in order, the largest progress will always be overwritten.
            if item.Reported() is False:
                progressToSendFloat = item.Value()

            # Make sure this is marked reported.
            item.SetReported(True)

        # The first progress update after a restore won't fire any notifications. We use this update
        # to clear out all progress points under the current progress, so we don't fire them.
        # Do this before we check if we had something to send, so we always do this on the first tick
        # after a restore.
        if self.RestorePrintProgressPercentage:
            self.RestorePrintProgressPercentage = False
            return

        # Return if there is nothing to do.
        if progressToSendFloat < 0.1:
            return

        # It's important we send the "snapped" progress here (rounded to the tens place) because the service depends on it
        # to filter out % increments the user didn't want to get notifications for.
        self._sendEvent(NotificationSender.EVENT_PROGRESS, None, progressToSendFloat)


    # Fired every hour while a print is running
    def OnPrintTimerProgress(self):
        if self._shouldIgnoreEvent():
            return
        # This event is fired by our internal timer only while prints are running.
        # It will only fire every hour.

        # We send a duration, but that duration is controlled by OctoPrint and can be changed.
        # Since we allow the user to pick "every x hours" to be notified, it's easier for the server to
        # keep track if we just send an int as well.
        # Since this fires once an hour, every time it fires just add one.
        self.PingTimerHoursReported += 1

        self._sendEvent(NotificationSender.EVENT_TIME_PROGRESS, { "HoursCount": str(self.PingTimerHoursReported) })


    # If possible, gets a snapshot from the snapshot URL configured in OctoPrint.
    # SnapshotResizeParams can be passed BUT MIGHT BE IGNORED if the PIL lib can't be loaded.
    # SnapshotResizeParams will also be ignored if the current image is smaller than the requested size.
    # If this fails for any reason, None is returned.
    def GetNotificationSnapshot(self, snapshotResizeParams = None):

        # If no snapshot resize param was specified, use the default for notifications.
        if snapshotResizeParams is None:
            # For notifications, if possible, we try to resize any image to be less than 720p.
            # This scale will preserve the aspect ratio and won't happen if the image is already less than 720p.
            # The scale might also fail if the image lib can't be loaded correctly.
            snapshotResizeParams = SnapshotResizeParams(1080, True, False, False)

        try:

            # Use the snapshot helper to get the snapshot. This will handle advance logic like relative and absolute URLs
            # as well as getting a snapshot directly from a mjpeg stream if there's no snapshot URL.
            octoHttpResponse = WebcamHelper.Get().GetSnapshot()

            # Check for a valid response.
            if octoHttpResponse is None or octoHttpResponse.Result is None or octoHttpResponse.Result.status_code != 200:
                return None

            # GetSnapshot will always return the full result already read.
            snapshot = octoHttpResponse.FullBodyBuffer
            if snapshot is None:
                Sentry.Error("NOTIFICATION", "WebcamHelper.Get().GetSnapshot() returned a web response but no FullBodyBuffer")
                return None

            # Ensure the snapshot is a reasonable size. If it's not, try to resize it if there's not another resize planned.
            # If this fails, the size will be checked again later and the image will be thrown out.
            if len(snapshot) > NotificationsHandler.MaxSnapshotFileSizeBytes:
                if snapshotResizeParams is None:
                    # Try to limit the size to be 1080 tall.
                    snapshotResizeParams = SnapshotResizeParams(1080, True, False, False)

            # Manipulate the image if needed.
            flipH = WebcamHelper.Get().GetWebcamFlipH()
            flipV = WebcamHelper.Get().GetWebcamFlipV()
            rotation = WebcamHelper.Get().GetWebcamRotation()
            if rotation != 0 or flipH or flipV or snapshotResizeParams is not None:
                try:
                    if Image is not None:

                        # We noticed that on some under powered or otherwise bad systems the image returned
                        # by mjpeg is truncated. We aren't sure why this happens, but setting this flag allows us to sill
                        # manipulate the image even though we didn't get the whole thing. Otherwise, we would use the raw snapshot
                        # buffer, which is still an incomplete image.
                        # Use a try catch incase the import of ImageFile failed
                        try:
                            ImageFile.LOAD_TRUNCATED_IMAGES = True
                        except Exception as _:
                            pass

                        # In pillow ~9.1.0 these constants moved.
                        # pylint: disable=no-member
                        OE_FLIP_LEFT_RIGHT = 0
                        OE_FLIP_TOP_BOTTOM = 0
                        try:
                            OE_FLIP_LEFT_RIGHT = Image.FLIP_LEFT_RIGHT
                            OE_FLIP_TOP_BOTTOM = Image.FLIP_TOP_BOTTOM
                        except Exception:
                            OE_FLIP_LEFT_RIGHT = Image.Transpose.FLIP_LEFT_RIGHT
                            OE_FLIP_TOP_BOTTOM = Image.Transpose.FLIP_TOP_BOTTOM
                        # pylint: enable=no-member

                        # Update the image
                        # Note the order of the flips and the rotates are important!
                        # If they are reordered, when multiple are applied the result will not be correct.
                        didWork = False
                        pilImage = Image.open(io.BytesIO(snapshot))
                        if flipH:
                            pilImage = pilImage.transpose(OE_FLIP_LEFT_RIGHT)
                            didWork = True
                        if flipV:
                            pilImage = pilImage.transpose(OE_FLIP_TOP_BOTTOM)
                            didWork = True
                        if rotation != 0:
                            # Our rotation is clockwise while PIL is counter clockwise.
                            # Subtract from 360 to get the opposite rotation.
                            rotation = 360 - rotation
                            pilImage = pilImage.rotate(rotation)
                            didWork = True

                        #
                        # Now apply any resize operations needed.
                        #
                        if snapshotResizeParams is not None:
                            # First, if we want to scale and crop to center, we will use the resize operation to get the image
                            # scale (preserving the aspect ratio). We will use the smallest side to scale to the desired outcome.
                            if snapshotResizeParams.CropSquareCenterNoPadding:
                                # We will only do the crop resize if the source image is smaller than or equal to the desired size.
                                if pilImage.height >= snapshotResizeParams.Size and pilImage.width >= snapshotResizeParams.Size:
                                    if pilImage.height < pilImage.width:
                                        snapshotResizeParams.ResizeToHeight = True
                                        snapshotResizeParams.ResizeToWidth = False
                                    else:
                                        snapshotResizeParams.ResizeToHeight = False
                                        snapshotResizeParams.ResizeToWidth = True

                            # Do any resizing required.
                            resizeHeight = None
                            resizeWidth = None
                            if snapshotResizeParams.ResizeToHeight:
                                if pilImage.height > snapshotResizeParams.Size:
                                    resizeHeight = snapshotResizeParams.Size
                                    resizeWidth = int((float(snapshotResizeParams.Size) / float(pilImage.height)) * float(pilImage.width))
                            if snapshotResizeParams.ResizeToWidth:
                                if pilImage.width > snapshotResizeParams.Size:
                                    resizeHeight = int((float(snapshotResizeParams.Size) / float(pilImage.width)) * float(pilImage.height))
                                    resizeWidth = snapshotResizeParams.Size
                            # If we have things to resize, do it.
                            if resizeHeight is not None and resizeWidth is not None:
                                pilImage = pilImage.resize((resizeWidth, resizeHeight))
                                didWork = True

                            # Now if we want to crop square, use the resized image to crop the remaining side.
                            if snapshotResizeParams.CropSquareCenterNoPadding:
                                left = 0
                                upper = 0
                                right = 0
                                lower = 0
                                if snapshotResizeParams.ResizeToHeight:
                                    # Crop the width - use floor to ensure if there's a remainder we float left.
                                    centerX = math.floor(float(pilImage.width) / 2.0)
                                    halfWidth = math.floor(float(snapshotResizeParams.Size) / 2.0)
                                    upper = 0
                                    lower = snapshotResizeParams.Size
                                    left = centerX - halfWidth
                                    right = (snapshotResizeParams.Size - halfWidth) + centerX
                                else:
                                    # Crop the height - use floor to ensure if there's a remainder we float left.
                                    centerY = math.floor(float(pilImage.height) / 2.0)
                                    halfHeight = math.floor(float(snapshotResizeParams.Size) / 2.0)
                                    upper = centerY - halfHeight
                                    lower = (snapshotResizeParams.Size - halfHeight) + centerY
                                    left = 0
                                    right = snapshotResizeParams.Size

                                # Sanity check bounds
                                if left < 0 or left > right or right > pilImage.width or upper > 0 or upper > lower or lower > pilImage.height:
                                    Sentry.Error("NOTIFICATION", "Failed to crop image. height: "+str(pilImage.height)+", width: "+str(pilImage.width)+", size: "+str(snapshotResizeParams.Size))
                                else:
                                    pilImage = pilImage.crop((left, upper, right, lower))
                                    didWork = True

                        #
                        # If we did some operation, save the image buffer back to a jpeg and overwrite the
                        # current snapshot buffer. If we didn't do work, keep the original, to preserve quality.
                        #
                        if didWork:
                            buffer = io.BytesIO()
                            pilImage.save(buffer, format="JPEG", quality=95)
                            snapshot = buffer.getvalue()
                            buffer.close()
                    else:
                        Sentry.Warn("NOTIFICATION", "Can't manipulate image because the Image rotation lib failed to import.")
                except Exception as ex:
                    # Note that in the case of an exception we don't overwrite the original snapshot buffer, so something can still be sent.
                    Sentry.ExceptionNoSend("Failed to manipulate image for notifications", ex)

            # Ensure in the end, the snapshot is a reasonable size.
            if len(snapshot) > NotificationsHandler.MaxSnapshotFileSizeBytes:
                Sentry.Error("NOTIFICATION", "Snapshot size if too large to send. Size: "+len(snapshot))
                return None

            # Return the image
            return snapshot

        except Exception as _:
            # Don't log here, because for those users with no webcam setup this will fail often.
            # TODO - Ideally we would log, but filter out the expected errors when snapshots are setup by the user.
            #Sentry.Info("NOTIFICATION", "Snapshot http call failed. " + str(e))
            pass

        # On failure return nothing.
        return None


    # Assuming the current time is set at the start of the printer correctly
    def GetCurrentDurationSecFloat(self):
        return float(time.time() - self.CurrentPrintStartTime)


    # When OctoPrint tells us the duration, make sure we are in sync.
    def _updateToKnownDuration(self, durationSecStr):
        # If the string is empty or None, return.
        # This is important for Moonraker
        if durationSecStr is None or len(durationSecStr) == 0:
            return

        # If we fail this logic don't kill the event.
        try:
            self.CurrentPrintStartTime = time.time() - float(durationSecStr)
        except Exception as e:
            Sentry.ExceptionNoSend("_updateToKnownDuration exception", e)


    # Updates the current file name, if there is a new name to set.
    def _updateCurrentFileName(self, fileNameStr):
        # The None check is important for Moonraker
        if fileNameStr is None or len(fileNameStr) == 0:
            return
        self.CurrentFileName = fileNameStr


    # Stops the final snap object if it's running and returns
    # the final image if possible.
    def _getFinalSnapSnapshotAndStop(self):
        # Capture the class member locally.
        localFs = self.FinalSnapObj
        self.FinalSnapObj = None

        # If there is one, stop it and return it's snapshot.
        if localFs is not None:
            return localFs.GetFinalSnapAndStop()
        return None


    # Returns the current print progress as a float.
    def _getCurrentProgressFloat(self):
        # Special platform logic here!
        # Since this function is used to get the progress for all platforms, we need to do things a bit differently.

        # For moonraker, the progress is reported via websocket messages super frequently. There's no better way to compute the
        # progress (unlike OctoPrint) so we just want to use it, if we have it.
        #
        # We also don't want to constantly call GetPrintTimeRemainingEstimateInSeconds on moonraker, since it will result in a lot of RPC calls.
        if self.MoonrakerReportedProgressFloat_CanBeNone is not None:
            return self.MoonrakerReportedProgressFloat_CanBeNone

        # Then for OctoPrint, we will do the following logic to get a better progress.
        # OctoPrint updates us with a progress int, but it turns out that's not the same progress as shown in the web UI.
        # The web UI computes the progress % based on the total print time and ETA. Thus for our notifications to have accurate %s that match
        # the web UIs, we will also try to do the same.
        try:
            # Try to get the print time remaining, which will use smart ETA plugins if possible.
            ptrSec = self.PrinterStateInterface.GetPrintTimeRemainingEstimateInSeconds()
            # If we can't get the ETA, default to OctoPrint's value.
            if ptrSec == -1:
                return float(self.FallbackProgressInt)

            # Compute the total print time (estimated) and the time thus far
            currentDurationSecFloat = self.GetCurrentDurationSecFloat()
            totalPrintTimeSec = currentDurationSecFloat + ptrSec

            # Sanity check for / 0
            if totalPrintTimeSec == 0:
                return float(self.FallbackProgressInt)

            # Compute the progress
            printProgressFloat = float(currentDurationSecFloat) / float(totalPrintTimeSec) * float(100.0)

            # Bounds check
            printProgressFloat = max(printProgressFloat, 0.0)
            printProgressFloat = min(printProgressFloat, 100.0)

            # Return the computed value.
            return printProgressFloat

        except Exception as e:
            Sentry.ExceptionNoSend("_getCurrentProgressFloat failed to compute progress.", e)

        # On failure, default to what OctoPrint has reported.
        return float(self.FallbackProgressInt) if isinstance(self.FallbackProgressInt, int) else 0.0


    # Sends the event
    # Returns True on success, otherwise False
    def _sendEvent(self, event, args = None, progressOverwriteFloat = None, useFinalSnapSnapshot = False):
        # Push the work off to a thread so we don't hang OctoPrint's plugin callbacks.
        thread = threading.Thread(target=self._sendEventThreadWorker, args=(event, args, progressOverwriteFloat, useFinalSnapSnapshot, ))
        thread.start()

        return True


    # Sends the event
    # Returns True on success, otherwise False
    def _sendEventThreadWorker(self, event, args = None, progressOverwriteFloat = None, useFinalSnapSnapshot = False):
        try:
            # Build the common even args.
            requestArgs = self.BuildCommonEventArgs(event, args, progressOverwriteFloat=progressOverwriteFloat, useFinalSnapSnapshot=useFinalSnapSnapshot)

            # Handle the result indicating we don't have the proper var to send yet.
            if requestArgs is None:
                Sentry.Info("NOTIFICATION", "NotificationsHandler didn't send the "+str(event)+" event because we don't have the proper id and key yet.")
                return False

            # Break out the response
            args = requestArgs[0]
            files = requestArgs[1]

            # Use fairly aggressive retry logic on notifications if they fail to send.
            # This is important because they power some of the other features of OctoApp now, so having them as accurate as possible is ideal.
            attempts = 0
            while attempts < 3:
                attempts += 1
                statusCode = 0
                try:
                    # Since we are sending the snapshot, we must send a multipart form.
                    # Thus we must use the data and files fields, the json field will not work.
                    #r = requests.post(eventApiUrl, data=args, files=files, timeout=5*60)
                    Sentry.Info("NOTIFICATIONS", "Sending %s (%s)" % (event, args))
                    self.NotificationSender.SendNotification(event=event, state=args)

                    # If success
                    return True

                except Exception as e:
                    # We must try catch the connection because sometimes it will throw for some connection issues, like DNS errors, server not connectable, etc.
                    Sentry.ExceptionNoSend("Failed to send notification due to a connection error. ", e)

                # On failure, log the issue.
                Sentry.Warn("NOTIFICATION", f"NotificationsHandler failed to send event {str(event)}. Code:{str(statusCode)}. Waiting and then trying again.")

                # If the error is in the 400 class, don't retry since these are all indications there's something
                # wrong with the request, which won't change. But we don't want to include anything above or below that.
                if statusCode > 399 and statusCode < 500:
                    return False

                # We have quite a few reties and back off a decent amount. As said above, we want these to be reliable as possible, even if they are late.
                # We want the first few retires to be quick, so the notifications happens ASAP. This will help in teh case where the server is updating, it should be
                # back withing 2-4 seconds, but 20 is a good time to wait.
                # If it's still failing, we want to allow the system some time to do a do a fail over or something, thus we give the retry timer more time.
                if attempts < 1: # Attempt 1 and 2 will wait 20 seconds.
                    time.sleep(20)
                else: # Attempt 3, 4, 5 will wait longer.
                    time.sleep(60 * attempts)

            # We never sent it successfully.
            Sentry.Error("NOTIFICATION", "NotificationsHandler failed to send event "+str(event)+" due to a network issues after many retries.")

        except Exception as e:
            Sentry.Exception("NotificationsHandler failed to send event code "+str(event), e)

        return False


    # Used by notifications and gadget to build a common event args.
    # Returns an array of [args, files] which are ready to be used in the request.
    # Returns None if the system isn't ready yet.
    def BuildCommonEventArgs(self, event, args=None, progressOverwriteFloat=None, snapshotResizeParams = None, useFinalSnapSnapshot = False):
        # Default args
        if args is None:
            args = {}

        # Add the required vars
        args["PrinterId"] = self.PrinterId
        args[NotificationSender.STATE_PRINT_ID] = self.PrintId
        args["OctoKey"] = self.OctoKey
        args["Event"] = event

        # Always add the file name and other common props
        args[NotificationSender.STATE_FILE_NAME] = str(self.CurrentFileName).split("/")[-1]
        args["FileSizeKb"] = str(self.CurrentFileSizeInKBytes)
        args["FilamentUsageMm"] = str(self.CurrentEstFilamentUsageMm)

        # Always include the ETA, note this will be -1 if the time is unknown.
        timeRemainEstStr =  str(self.PrinterStateInterface.GetPrintTimeRemainingEstimateInSeconds())
        args[NotificationSender.STATE_TIME_REMAINING_SEC] = timeRemainEstStr

        # Always include the layer height, if it can be gotten from the platform.
        currentLayer, totalLayers = self.PrinterStateInterface.GetCurrentLayerInfo()
        if currentLayer is not None and totalLayers is not None:
            # Note both of these values can be 0 if the layer counts aren't known yet!
            args["CurrentLayer"] = str(currentLayer)
            args["TotalLayers"] = str(totalLayers)

        # Always add the current progress
        # -> int to round -> to string for the API.
        # Allow the caller to overwrite the progress we report. This allows the progress update to snap the progress to a hole 10s value.
        progressFloat = 0.0
        if progressOverwriteFloat is not None:
            progressFloat = progressOverwriteFloat
        else:
            progressFloat = self._getCurrentProgressFloat()

        args[NotificationSender.STATE_PROGRESS_PERCENT] = str(int(progressFloat))

        # Always add the current duration
        args[NotificationSender.STATE_DURATION_SEC] = str(self.GetCurrentDurationSecFloat())

        # Also always include a snapshot if we can get one.
        files = {}
        snapshot = None

        # If we are requested to use a final snapshot, try to use the snapshot from it.
        # This should only be requested for the "done" notification.
        if useFinalSnapSnapshot:
            snapshot = self._getFinalSnapSnapshotAndStop()

        # If we don't have a snapshot, try to get one now.
        #if snapshot is None:
        #    snapshot = self.GetNotificationSnapshot(snapshotResizeParams)

        # If we got one, save it to the request.
        if snapshot is not None:
            files['attachment'] = ("snapshot.jpg", snapshot)

        return [args, files]


    # Stops any running timer, be it the progress timer, the Gadget timer, or something else.
    def StopTimers(self):
        # Capture locally & Stop
        progressTimer = self.ProgressTimer
        self.ProgressTimer = None
        if progressTimer is not None:
            progressTimer.Stop()

        # Stop Gadget From Watching
        # self.Gadget.StopWatching()


    # Starts all print timers, including the progress time
    def StartPrintTimers(self, resetHoursReported, restoreActionSetHoursReportedInt_OrNone):
        # First, stop any timer that's currently running.
        self.StopTimers()

        # Make sure the hours flag is cleared when we start a new timer.
        if resetHoursReported:
            self.PingTimerHoursReported = 0

        # If this is a restore, set the value
        if restoreActionSetHoursReportedInt_OrNone is not None:
            self.PingTimerHoursReported = int(restoreActionSetHoursReportedInt_OrNone)

        # Setup the progress timer
        intervalSec = 60 * 60 # Fire every hour.
        timer = RepeatTimer(intervalSec, self.ProgressTimerCallback)
        timer.start()
        self.ProgressTimer = timer

        # Start Gadget From Watching
        # self.Gadget.StartWatching()


    # Let's the caller know if the ping timer is running, and thus we are tracking a print.
    def _IsPingTimerRunning(self):
        return self.ProgressTimer is not None


    # Returns if we have a current print file name, indication if we are setup to track a print at all, even a paused one.
    def _HasCurrentPrintFileName(self):
        return self.CurrentFileName is not None and len(self.CurrentFileName) > 0


    # Fired when the ping timer fires.
    def ProgressTimerCallback(self):

        # Double check the state is still printing before we send the notification.
        # Even if the state is paused, we want to stop, since the resume command will restart the timers
        if self.PrinterStateInterface.ShouldPrintingTimersBeRunning() is False:
            Sentry.Info("NOTIFICATION", "Notification progress timer state doesn't seem to be printing, stopping timer.")
            self.StopTimers()
            return

        # Fire the event.
        self.OnPrintTimerProgress()


    # Only allows possibly spammy events to be sent every x minutes.
    # Returns true if the event can be sent, otherwise false.
    def _shouldSendSpammyEvent(self, eventName, minTimeBetweenMinutesFloat):
        with self.SpammyEventLock:

            # Check if the event has been added to the dict yet.
            if eventName not in self.SpammyEventTimeDict:
                # No event added yet, so add it now.
                self.SpammyEventTimeDict[eventName] = SpammyEventContext()
                return True

            # Check how long it's been since the last notification was sent.
            # If it's less than 5 minutes, don't allow the event to send.
            if self.SpammyEventTimeDict[eventName].ShouldSendEvent(minTimeBetweenMinutesFloat) is False:
                return False

            # Report we are sending an event and return true.
            self.SpammyEventTimeDict[eventName].ReportEventSent()
            return True


    def _clearSpammyEventContexts(self):
        with self.SpammyEventLock:
            self.SpammyEventTimeDict = {}


    # Very rarely, we want to ignore some notifications based on different metrics.
    # A filename can be passed to check, if not, the current file name will be used.
    def _shouldIgnoreEvent(self, fileName:str = None) -> bool:
        # Check if there was a file name passed, if so use it.
        # If not, fall back to the current file name.
        # If there is neither, dont ignore.
        if fileName is None or len(fileName) == 0:
            fileName = self.CurrentFileName
            if fileName is None or len(fileName) == 0:
                return False
        # One case we want to ignore is when the continuous print plugin uses it's "placeholder" .gcode files.
        # These files are used between prints to hold the printer before a new print starts.
        # The events are listed here, and the file name will be 'continuousprint_finish.gcode' for example.
        # https://github.com/smartin015/continuousprint/blob/bfb2c13da2ebbe0bfbfaa90f62a91db332c43b1b/continuousprint/data/__init__.py#L62
        fileNameLower = fileName.lower()
        if fileNameLower.startswith("continuousprint_"):
            Sentry.Info("NOTIFICATION", "Ignoring notification because it's a continuous print place holder file. "+str(fileName))
            return True
        return False

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

class SpammyEventContext:

    def __init__(self):
        self.ConcurrentCount = 0
        self.LastSentTimeSec = 0
        self.ReportEventSent()


    def ReportEventSent(self):
        self.ConcurrentCount += 1
        self.LastSentTimeSec = time.time()


    def ShouldSendEvent(self, baseTimeIntervalMinutesFloat):
        # Figure out what the delay multiplier should be.
        delayMultiplier = 1

        # For the first 3 events, don't back off.
        if self.ConcurrentCount > 3:
            delayMultiplier = self.ConcurrentCount

        # Sanity check.
        delayMultiplier = max(delayMultiplier, 1)

        # Ensure we don't try to delay too long.
        # Most of these timers are base intervals of 5 minutes, so 288 is one every 24 hours.
        delayMultiplier = min(delayMultiplier, 288)

        timeSinceLastSendSec = time.time() - self.LastSentTimeSec
        sendIntervalSec = baseTimeIntervalMinutesFloat * 60.0
        if timeSinceLastSendSec > sendIntervalSec * delayMultiplier:
            return True
        return False
