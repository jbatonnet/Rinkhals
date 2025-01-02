import time
import json

from octoapp.compat import Compat
from .moonrakerclient import MoonrakerClient

# Implements the platform specific logic for moonraker's smart pause.
class SmartPause:

    # The static instance.
    _Instance = None

    @staticmethod
    def Init():
        SmartPause._Instance = SmartPause()
        Compat.SetSmartPauseInterface(SmartPause._Instance)


    @staticmethod
    def Get():
        return SmartPause._Instance


    def __init__(self):
        self.LastPauseNotificationSuppressionTimeSec = 0


    # # Does the actual smart pause.
    # # Must return a CommandResponse
    # def ExecuteSmartPause(self, suppressNotificationBool) -> CommandResponse:

    #     # Set the pause suppress, if desired.
    #     # Do this first, since the notification will fire before we can suppress it.
    #     if suppressNotificationBool:
    #         Sentry.Info("Smart Pause", "Setting smart pause time to suppress the pause notification.")
    #         self.LastPauseNotificationSuppressionTimeSec = time.time()

    #     # The only parameter we take is the notification suppression
    #     # This is because moonraker already does a "smart pause" on it's own.
    #     # All pauses move the head way from the print and then put it back on resume.
    #     result = MoonrakerClient.Get().SendJsonRpcRequest("printer.print.pause", {})
    #     if result.HasError():
    #         Sentry.Error("Smart Pause", "SmartPause failed to request pause. "+result.GetLoggingErrorStr())
    #         return CommandResponse.Error(400, "Failed to request pause")

    #     # Check the response
    #     if result.GetResult() != "ok":
    #         Sentry.Error("Smart Pause", "SmartPause got an invalid request response. "+json.dumps(result.GetResult()))
    #         return CommandResponse.Error(400, "Invalid request response.")

    #     # Return success.
    #     return CommandResponse.Success(None)


    # !! Interface Function !! - See compat.py GetSmartPauseInterface for the details.
    # Returns None if there is no current suppression or the time of the last time it was requested
    def GetAndResetLastPauseNotificationSuppressionTimeSec(self):
        local = self.LastPauseNotificationSuppressionTimeSec
        self.LastPauseNotificationSuppressionTimeSec = None
        return local
