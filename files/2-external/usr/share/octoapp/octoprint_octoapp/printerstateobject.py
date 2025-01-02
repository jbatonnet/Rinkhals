from octoprint.printer import PrinterInterface

from octoapp.sentry import Sentry

# Implements a common interface shared by OctoPrint and Moonraker.
class PrinterStateObject:

    def __init__(self, octoPrintPrinterObject: PrinterInterface):
        self.OctoPrintPrinterObject = octoPrintPrinterObject
        self.NotificationHandler = None


    # Sets the notification handler for use. This is required.
    def SetNotificationHandler(self, handler):
        self.NotificationHandler = handler

    def GetCurrentProgress(self) :
        try:
            return self.currentData.get("progress", -1)
        except Exception as e:
            Sentry.Exception("Failed to get current progress ", e)
            return -1

    # ! Interface Function ! The entire interface must change if the function is changed.
    # This function will get the estimated time remaining for the current print.
    # Returns -1 if the estimate is unknown.
    def GetPrintTimeRemainingEstimateInSeconds(self):
        # Try to get the progress object from the current data. This is at least set by things like PrintTimeGenius and is more accurate.
        try:
            currentData = self.OctoPrintPrinterObject.get_current_data()
            if "progress" in currentData:
                if "printTimeLeft" in currentData["progress"]:
                    # When the print is just starting, the printTimeLeft will be None.
                    printTimeLeftSec = currentData["progress"]["printTimeLeft"]
                    if printTimeLeftSec is not None:
                        printTimeLeft = int(float(currentData["progress"]["printTimeLeft"]))
                        return printTimeLeft
        except Exception as e:
            Sentry.Exception("Failed to find progress object in printer current data.", e)

        # If that fails, try to use the default OctoPrint estimate.
        try:
            jobData = self.OctoPrintPrinterObject.get_current_job()
            if "estimatedPrintTime" in jobData:

                # When the print is first starting and there is no known time, this can be none.
                # In that case, return -1, unknown.
                if jobData["estimatedPrintTime"] is None:
                    return -1

                printTimeEstSec = int(jobData["estimatedPrintTime"])
                # Compute how long this print has been running and subtract
                # Sanity check the duration isn't longer than the ETA.
                currentDurationSec = int(self.NotificationHandler.GetCurrentDurationSecFloat())
                if currentDurationSec > printTimeEstSec:
                    return 0
                return printTimeEstSec - currentDurationSec
        except Exception as e:
            Sentry.Exception("Failed to find time estimate from OctoPrint. ", e)

        # We failed.
        return -1


    # ! Interface Function ! The entire interface must change if the function is changed.
    # If the printer is warming up, this value would be -1. The First Layer Notification logic depends upon this!
    # Returns the current zoffset if known, otherwise -1.
    def GetCurrentZOffset(self):
        # Try to get the current value from the data.
        try:
            # Don't get the current zoffset until the print is running, since the tool could be at any
            # height before the print starts.
            if self.IsPrintWarmingUp():
                return -1

            # We have seen in client logs sometimes this value doesn't exist,
            # and sometime it does, but it's just None.
            currentData = self.OctoPrintPrinterObject.get_current_data()
            if "currentZ" in currentData and currentData["currentZ"] is not None:
                currentZ = float(currentData["currentZ"])
                return currentZ
        except Exception as e:
            Sentry.Exception("Failed to find current z offset.", e)

        # Failed to find it.
        return -1


    # ! Interface Function ! The entire interface must change if the function is changed.
    # If this platform DOESN'T support getting the layer info from the system, this returns (None, None)
    # If the platform does support it...
    #     If the current value is unknown, (0,0) is returned.
    #     If the values are known, (currentLayer(int), totalLayers(int)) is returned.
    #          Note that total layers will always be > 0, but current layer can be 0!
    def GetCurrentLayerInfo(self):
        # OctoPrint doesn't compute or track the layer height right now.
        return (None, None)


    # ! Interface Function ! The entire interface must change if the function is changed.
    # Returns True if the printing timers (notifications and gadget) should be running, which is only the printing state. (not even paused)
    # False if the printer state is anything else, which means they should stop.
    def ShouldPrintingTimersBeRunning(self):
        # Get the current state
        # States can be found here:
        # https://docs.octoprint.org/en/master/modules/printer.html#octoprint.printer.PrinterInterface.get_state_id
        # Note! The docs seem to be missing some states at the moment, like STATE_RESUMING, which can be found in comm.py
        state = self.OctoPrintPrinterObject.get_state_id()

        # Return if the state is printing or not.
        if state == "PRINTING" or state == "RESUMING" or state == "FINISHING" or state == "STARTING":
            return True

        Sentry.Warn("PRINTER_STATE", "ShouldPrintingTimersBeRunning is not in a printing state: "+str(state))
        return False


    # ! Interface Function ! The entire interface must change if the function is changed.
    # If called while the print state is "Printing", returns True if the print is currently in the warm-up phase. Otherwise False
    def IsPrintWarmingUp(self):
        # Using the current state, if the print time is None or 0, the print hasn't started because the system is warming up..
        # Using the get_current_data in this way is the same way the /api/job uses it.
        currentData = self.OctoPrintPrinterObject.get_current_data()
        if currentData is not None:
            progress = currentData["progress"]
            if progress is not None:
                printTime = progress["printTime"]
                if printTime is None or int(printTime) == 0:
                    return True

        # We aren't warming up.
        return False
