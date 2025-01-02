import random
import threading
import time
import json
import logging

import requests

from .sentry import Sentry
from .snapshotresizeparams import SnapshotResizeParams
from .repeattimer import RepeatTimer

class Gadget:

    # The default amount of time we will use for the first interval callback.
    c_defaultIntervalSec = 30

    # The default amount of time we will use if we can't get a snapshot.
    c_defaultIntervalSec_NoSnapshot = 120

    # The default amount of time we will use if there was a connection error.
    # Note this time is scaled on each failure.
    c_defaultIntervalSec_ConnectionErrorBackoffBase = 30

    # We keep track of the score history, up to a point.
    # Assuming 20 second checks, 100 checks is about 30 minutes of data.
    c_maxScoreHistoryItems = 100

    def __init__(self, logger:logging.Logger, notificationHandler, printerStateInterface):
        self.Logger = logger
        self.NotificationHandler = notificationHandler
        self.PrinterStateInterface = printerStateInterface
        self.Lock = threading.Lock()
        self.Timer = None
        self.DefaultProtocolAndDomain = "http://127.0.0.1:4500"
        self.FailedConnectionAttempts = 0

        # If there is a current host lock, this is the hostname.
        # This is cleared on error and as the start of each print.
        self.HostLockHostname = None
        # Dev param, can be set to disable host lock.
        self.DisableHostLock = False

        # The most recent Gadget score sent back and the time it was received at.
        self.MostRecentGadgetScore = 0.0
        self.MostRecentGadgetScoreUpdateTimeSec = 0
        self.ScoreHistory = []
        self.MostRecentIntervalSec = Gadget.c_defaultIntervalSec
        # These default to None, to indicate they haven't been done.
        self.MostRecentWarningTimeSec = None
        self.MostRecentPauseTimeSec = None
        self.IsSuppressed = False
        self._resetPerPrintState()

        # Optional - Image resizing params the server can set.
        # When set, we should make a best effort at respecting them.
        # If set to 0, they are disabled.
        self.ImageScaleCenterCropSize = 0
        self.ImageScaleMaxHeight = 0


    def SetServerProtocolAndDomain(self, protocolAndDomain:str):
        # If a custom domain is set, disable host lock, so we don't jump off it.
        Sentry.Info("GADGET", "Gadget default protocol and hostname set to: "+protocolAndDomain + " Host Lock Is DISABLED")
        self.DefaultProtocolAndDomain = protocolAndDomain
        self.DisableHostLock = True


    def StartWatching(self):
        with self.Lock:
            # Stop any running timer.
            self._stopTimerUnderLock()

            # Reset any per print stats, so they aren't stale
            self._resetPerPrintState()

            Sentry.Info("GADGET", "Gadget is now watching!")

            # Start a new timer.
            self.Timer = RepeatTimer(self.Logger, Gadget.c_defaultIntervalSec, self._timerCallback)
            self.Timer.start()


    def StopWatching(self):
        with self.Lock:
            self._stopTimerUnderLock()


    # Returns the last score Gadget sent us back.
    # Defaults to 0.0
    def GetLastGadgetScoreFloat(self):
        # * 1.0 to ensure it's a float.
        return self.MostRecentGadgetScore * 1.0


    # Returns the history of scores for this print.
    # Defaults to an empty list.
    def GetScoreHistoryFloats(self):
        return self.ScoreHistory


    # Returns the seconds since the last Gadget score update.
    # The default time is very large, since it's the time since 0.
    def GetLastTimeSinceScoreUpdateSecFloat(self):
        return time.time() - self.MostRecentGadgetScoreUpdateTimeSec


    # Returns the current interval Gadget has set for us.
    def GetCurrentIntervalSecFloat(self):
        # Note we can't use _getTimerInterval because the timer interval is set to the default
        # at the start of each call for error handling.
        # * 1.0 to ensure it's a float.
        return self.MostRecentIntervalSec * 1.0


    # Returns None if there has been no pause, otherwise, the amount of time since in seconds.
    def GetTimeOrNoneSinceLastPauseIntSec(self):
        timeSec = self.MostRecentPauseTimeSec
        if timeSec is None:
            return None
        return int(time.time() - timeSec)


    # Returns None if there has been no warning, otherwise, the amount of time since in seconds.
    def GetTimeOrNoneSinceLastWarningIntSec(self):
        timeSec = self.MostRecentWarningTimeSec
        if timeSec is None:
            return None
        return int(time.time() - timeSec)


    # Returns a bool if the current print is suppressed or not.
    def IsPrintSuppressed(self):
        return self.IsSuppressed


    # Can only be called when the timer isn't running to prevent race conditions.
    def _resetPerPrintState(self):
        # Reset the basic stats
        self.MostRecentIntervalSec = Gadget.c_defaultIntervalSec
        self.MostRecentGadgetScore = 0.0
        self.ScoreHistory = []

        # At the start of each print, clear the host lock settings.
        self._clearHostLockHostname()

        # These default to None, to indicate they haven't been done.
        self.MostRecentWarningTimeSec = None
        self.MostRecentPauseTimeSec = None
        self.IsSuppressed = False


    def _stopTimerUnderLock(self):
        if self.Timer is not None:
            Sentry.Info("GADGET", "Gadget has stopped watching!")
            self.Timer.Stop()
            self.Timer = None


    def _updateTimerInterval(self, newIntervalSec):
        timer = self.Timer
        if timer is not None:
            timer.SetInterval(newIntervalSec)


    def _getTimerInterval(self):
        timer = self.Timer
        if timer is not None:
            return timer.GetInterval()
        else:
            return Gadget.c_defaultIntervalSec


    def _timerCallback(self):
        try:
            # Before we do anything, update the timer interval to the default, incase there's some error
            # and we don't update it properly. In all cases either an error should update this or the response
            # from the inspect call.
            lastIntervalSec = self._getTimerInterval()
            self._updateTimerInterval(Gadget.c_defaultIntervalSec)

            # Check to ensure we should still be running. If the state is anything other than printing, we shouldn't be running
            # We will be restarted on a new print starting or when resume is called.
            if self.PrinterStateInterface.ShouldPrintingTimersBeRunning() is False:
                Sentry.Warn("GADGET", "Gadget timer is running but the print state is not printing, so the timer is topping.")
                self.StopWatching()
                return

            # If we should be running, then the print status is "PRINTING".
            # Next check to see if the printer is warming up. If we are warming up, we don't want to let Gadget predict.
            # We do this because during warm-up the printer can ooze some filament out of the hot end, that we don't want to predict on.
            if self.PrinterStateInterface.IsPrintWarmingUp():
                Sentry.Info("GADGET", "Waiting to predict with Gadget because the printer is warming up.")
                self._updateTimerInterval(Gadget.c_defaultIntervalSec)
                return

            # If we have any resize args set by the server, apply them now.
            # Remember these are best effort, so they might not be applied to the output image.
            # These values must be greater than 1 or the SnapshotResizeParams can't take them.
            snapshotResizeParams = None
            if self.ImageScaleCenterCropSize > 1:
                # If this is set, it takes priority over any other options.
                # Request a center crop square of the image scaled to the desired factor.
                snapshotResizeParams = SnapshotResizeParams(self.ImageScaleCenterCropSize, False, False, True)
            elif self.ImageScaleMaxHeight > 1:
                # Request a max height of the desired size. If the image is smaller than this it will be ignored.
                snapshotResizeParams = SnapshotResizeParams(self.ImageScaleMaxHeight, True, False, False)

            # Now, get the common event args, which will include the snapshot.
            requestData = self.NotificationHandler.BuildCommonEventArgs("inspect", None, None, snapshotResizeParams)

            # Handle the result indicating we don't have the proper var to send yet.
            if requestData is None:
                Sentry.Info("GADGET", "Gadget didn't send because we don't have the proper id and key yet.")
                self._updateTimerInterval(Gadget.c_defaultIntervalSec)
                return

            # Break out the args
            args = requestData[0]
            files = requestData[1]

            # Add the last interval, so the server knows
            args["LastIntervalSec"] = lastIntervalSec

            # Also add the score history, for the server.
            args["ScoreHistory"] = self.GetScoreHistoryFloats()

            # Next, check if there's a valid snapshot image.
            if len(files) == 0:
                # If not, update our interval to be the default no snapshot interval and return.
                Sentry.Debug("GADGET", "Gadget isn't making a prediction because it failed to get a snapshot.")
                self._updateTimerInterval(Gadget.c_defaultIntervalSec_NoSnapshot)
                return

            jsonResponse = None
            try:
                # Setup the url.
                gadgetApiUrl = self._getProtocolAndHostname() + "/api/gadget/inspect"

                # Since we are sending the snapshot, we must send a multipart form.
                # Thus we must use the data and files fields, the json field will not work.
                # Set a timeout, but make it long, so the server has time to process.
                r = requests.post(gadgetApiUrl, data=args, files=files, timeout=10*60)

                # Check for success. Anything but a 200 we will consider a connection failure.
                if r.status_code != 200:
                    raise Exception("Bad response code "+str(r.status_code))

                # Get the response
                jsonResponse = r.json()
                if jsonResponse is None:
                    raise Exception("No json response found.")

            except Exception as e:
                # For any connection based error, either we fail to connect or we get back not a 200,
                # We will handle it with out logging too much. This can happen if we need to load shed, so we
                # dont need to log about it much.
                if self.FailedConnectionAttempts % 20 == 0:
                    Sentry.Info("GADGET", "Failed to send gadget inspection due to a connection error. "+str(e))
                self.FailedConnectionAttempts += 1

                # On any error, clear the HostLock hostname, so we hit the root domain again. This is the recovery system
                # for if a host goes down or is having some issue.
                self._clearHostLockHostname()

                # Update our timer interval for the failure and return.
                # We back off the retry time so we can make a few faster attempts, but then fall back to longer term attempts.
                # Also add some random-ness to the retry, to prevent all clients coming back at once.
                nextIntervalSec = max(1, min(self.FailedConnectionAttempts, 5)) * Gadget.c_defaultIntervalSec_ConnectionErrorBackoffBase
                nextIntervalSec += random.randint(10, 30)
                self._updateTimerInterval(nextIntervalSec)
                return

            # Handle the json response. We should find an int telling us how long we should wait before sending the next
            # inspection report.
            if "Result" not in jsonResponse:
                Sentry.Warn("GADGET", "Gadget inspection result had no Result object")
                self._updateTimerInterval(Gadget.c_defaultIntervalSec)
                # On any error, clear the HostLock hostname, so we hit the root domain again.
                self._clearHostLockHostname()
                return
            resultObj = jsonResponse["Result"]
            if "NextInspectIntervalSec" not in resultObj:
                Sentry.Warn("GADGET", "Gadget inspection result had no NextInspectIntervalSec field")
                self._updateTimerInterval(Gadget.c_defaultIntervalSec)
                # On any error, clear the HostLock hostname, so we hit the root domain again.
                self._clearHostLockHostname()
                return

            # Update the next interval time according to what gadget is requesting.
            nextIntervalSec = int(resultObj["NextInspectIntervalSec"])
            self._updateTimerInterval(nextIntervalSec)
            self.MostRecentIntervalSec = nextIntervalSec

            # On a successful prediction, a score will be returned.
            # Parse the score and set the last time we updated it.
            if "Score" in resultObj and resultObj["Score"] is not None:
                self._updateGadgetScore(float(resultObj["Score"]))

            # Parse an optional that could be returned.
            if "DidWarning" in resultObj and resultObj["DidWarning"]:
                self.MostRecentWarningTimeSec = time.time()
            if "DidPause" in resultObj and resultObj["DidPause"]:
                self.MostRecentPauseTimeSec = time.time()
            if "IsSuppressed" in resultObj and resultObj["IsSuppressed"]:
                self.IsSuppressed = resultObj["IsSuppressed"]

            # If the server returned a host lock hostname, set it if needed.
            if "HostLock" in resultObj and resultObj["HostLock"]:
                self._setHostLockHostnameIfNeeded(resultObj["HostLock"])

            # Parse the optional image resizing params. If these fail to parse, just default them.
            if "IS_CCSize" in resultObj:
                try:
                    newValue = int(resultObj["IS_CCSize"])
                    if newValue != self.ImageScaleCenterCropSize:
                        Sentry.Info("GADGET", "Gadget ImageScaleCenterCropSize set to: "+str(newValue))
                        self.ImageScaleCenterCropSize = newValue
                except Exception as e:
                    Sentry.Warn("GADGET", "Gadget failed to parse IS_CCSize from response. "+str(e))
                    self.ImageScaleCenterCropSize = 0
            if "IS_MH" in resultObj:
                try:
                    newValue = int(resultObj["IS_MH"])
                    if newValue != self.ImageScaleMaxHeight:
                        Sentry.Info("GADGET", "Gadget ImageScaleMaxHeight set to: "+str(newValue))
                        self.ImageScaleMaxHeight = newValue
                except Exception as e:
                    Sentry.Warn("GADGET", "Gadget failed to parse IS_MH from response."+str(e))
                    self.ImageScaleMaxHeight = 0

            # Check if we have a log object in response. If so, the server wants us to log information into the local log file.
            if "Log" in resultObj and resultObj["Log"] is not None:
                try:
                    # Stringify the object sent back from the server.
                    logStr = json.dumps(resultObj["Log"])
                    Sentry.Info("GADGET", "Gadget Server Log - id:"+str(self.NotificationHandler.GetPrintId())+" int:"+str(nextIntervalSec)+" s:"+str(self.MostRecentGadgetScore)+" - "+logStr)
                except Exception as e:
                    Sentry.Warn("GADGET", "Gadget failed to parse Log from response."+str(e))

            # Reset the failed attempts counter
            self.FailedConnectionAttempts = 0

        except Exception as e:
            Sentry.Exception("Exception in gadget timer", e)
            # On any error, clear the HostLock hostname, so we hit the root domain again.
            self._clearHostLockHostname()


    def _updateGadgetScore(self, newScore):
        # We keep track of all scores, for stats.
        # Round the scores to 4 decimals, so 0.9583 is 95.8%
        self.ScoreHistory.insert(0, round(newScore, 3))
        while len(self.ScoreHistory) > Gadget.c_maxScoreHistoryItems:
            self.ScoreHistory.pop()

        # To smooth out outliers, use the new score and a sample of the old score.
        # But we also want the most recent score to stay responsive, due to interval delays.
        # After some testing, 0.7 feels about right, so the UI is updated, but isn't too responsive to random peaks or valleys.
        newScoreWeight = 0.7
        self.MostRecentGadgetScore = (float(newScore) * newScoreWeight) + (self.MostRecentGadgetScore * (1.0 - newScoreWeight))

        # Update the time this score was gotten.
        self.MostRecentGadgetScoreUpdateTimeSec = time.time()


    def _getProtocolAndHostname(self):
        # The idea of host lock is some light load balancing, while also keeping prints stick to the same
        # host of Gadget ideally. The Gadget hosting system can support inspections on any host, but it's more efficient and ideal
        # for the client and system if the same client talks to the same host for the entire print.

        # Check if we have a current host lock or if it's disabled.
        currentHostname = self.HostLockHostname
        if currentHostname is None or self.DisableHostLock:
            return self.DefaultProtocolAndDomain

        # Otherwise, return the host lock hostname. Note that the value will only be the hostname, it doesn't include
        # the protocol for security reasons, so https can't be disabled.
        return "https://"+currentHostname


    def _clearHostLockHostname(self):
        # Clear the hostname, but don't clear the dev force disable flag.
        # This will disable the current host lock (if there is one)
        if self.HostLockHostname is None:
            return
        Sentry.Info("GADGET", "Gadget HostLock cleared")
        self.HostLockHostname = None


    def _setHostLockHostnameIfNeeded(self, hostname):
        # If we are already host locked, don't set new values.
        # There will almost always be a value returned and it will always be the current server
        # with the lowest load. But the entire point of host lock is to try to stay stick on a single host.
        if self.HostLockHostname is not None:
            return
        Sentry.Info("GADGET", "Gadget HostLock set to: "+hostname)
        self.HostLockHostname = hostname
