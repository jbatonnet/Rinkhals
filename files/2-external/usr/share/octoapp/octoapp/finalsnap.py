import math
import time
import threading

from .sentry import Sentry
from .repeattimer import RepeatTimer

# A helper class to try to capture a better "print completed" image by taking images before the complete notification
# so we have images from shortly before the notification fires. This is needed because most printers will move the
# print head away from the print after completing. If the camera is mounted to the print arm, then the print might not
# be in frame.
class FinalSnap:

    # The default interval that we will snap an image at.
    c_defaultSnapIntervalSec = 1

    # This is how many snapshots we will keep in our buffer.
    # Thus, the amount of time we will keep in our buffer is seconds = (c_snapshotBufferDepth * c_defaultSnapIntervalSec)
    # We must keep this buffer a little larger, for the extrude command logic to have enough buffer to operate in.
    # This buffer must also be large enough to have data for the c_onCompleteSnapDelaySec time.
    c_snapshotBufferDepth = 40

    # When the on complete notification fires, this is how long we will try to go back in time to fetch a snapshot,
    # if we don't have a last extrude command sent time.
    c_onCompleteSnapDelaySec = 9


    # Creates the object and starts the timer.
    def __init__(self, notificationHandler) -> None:
        self.LastExtrudeCommandSent:float = 0.0
        self.NotificationHandler = notificationHandler
        self.SnapLock = threading.Lock()
        self.SnapHistory = []
        self.Timer = RepeatTimer(FinalSnap.c_defaultSnapIntervalSec, self._snapCallback)
        self.Timer.start()
        Sentry.Info("FINAL_SNAP", "Starting FinalSnap")


    # Called when the system knows an extrude command was sent to the printer.
    # This allows us to track the last time the printer actually extruded, which might would be a good time
    # to target for a snapshot.
    # Note some prints wont fire this, like if printing from an SD card.
    def ReportPositiveExtrudeCommandSent(self):
        self.LastExtrudeCommandSent = time.time()


    # Gets a final snapshot image is possible and shuts down the class.
    # If no final image exists, this will return null.
    def GetFinalSnapAndStop(self):
        # Stop the timer
        self.Timer.Stop()

        # Try to find the best snap.
        with self.SnapLock:
            if len(self.SnapHistory) > 0:

                # Find to get our target delta time.
                targetTimeDeltaSec:float = 0.0

                # If we have a `LastExtrudeCommandSent` and it's in our buffer, we will use it.
                # This is the most ideal indicator, because we know it's the last time the extruder did a positive extrude
                # But, not all platforms or even all prints (like printing from an SD card) will know this value.
                if self.LastExtrudeCommandSent != 0:
                    targetTimeDeltaSec = time.time() - self.LastExtrudeCommandSent

                # If we still dont have a targetTimeDeltaSec value, use our fixed value.
                if targetTimeDeltaSec <= 0.0001:
                    targetTimeDeltaSec = float(FinalSnap.c_onCompleteSnapDelaySec)

                # Compute our ideal image position in our buffer.
                # In terms of rounding, round up, to prefer a later image then the exact time.
                targetArrayIndex = int(math.ceil(targetTimeDeltaSec / float(FinalSnap.c_defaultSnapIntervalSec)))

                if targetArrayIndex < 0:
                    Sentry.Error("FINAL_SNAP", f"Target image index is less than 0? {targetArrayIndex}")
                    # Set something like our default snap interval.
                    targetArrayIndex = 5
                if targetArrayIndex >= len(self.SnapHistory):
                    Sentry.Warn("FINAL_SNAP", f"Target image index is larger than our buffer. {targetArrayIndex} {len(self.SnapHistory)}")
                    # Use the oldest image we have.
                    targetArrayIndex = len(self.SnapHistory) - 1

                # Return the image selected.
                # Clear the array to free up space of stored images, just incase this class leaks.
                Sentry.Info("FINAL_SNAP", f"Stopping final snap and using snapshot from ~{targetTimeDeltaSec} sec ago, index slot {targetArrayIndex} / {len(self.SnapHistory)}")
                snap = self.SnapHistory[targetArrayIndex]
                self.SnapHistory.clear()
                return snap

        # If we don't have an image, just return None.
        Sentry.Info("FINAL_SNAP", "Stopping final snap but there's no snapshot to use.")
        return None


    # Fires when we should take a new snapshot.
    def _snapCallback(self):
        try:
            # Try to get a snapshot.
            snapshot = self.NotificationHandler.GetNotificationSnapshot()
            if snapshot is None:
                Sentry.Info("FINAL_SNAP", "Failed to get a snapshot")
                return

            with self.SnapLock:
                # Make sure we are still running, otherwise there's no reason to store the image.
                if self.Timer.IsRunning() is False:
                    return

                # Add this most recent snapshot to the front.
                self.SnapHistory.insert(0, snapshot)

                # Figure out the desired buffer depth.
                # `c_snapshotBufferDepth` should always be large enough, but we will make sure.
                desiredBufferDepth = FinalSnap.c_snapshotBufferDepth
                minBufferDepthForFixedTime = int(math.ceil(float(FinalSnap.c_onCompleteSnapDelaySec) / float(FinalSnap.c_defaultSnapIntervalSec)))
                if minBufferDepthForFixedTime > desiredBufferDepth:
                    Sentry.Warn("FINAL_SNAP", f"Final snap had to expand the default buffer size due to the time. {minBufferDepthForFixedTime}")
                    desiredBufferDepth = minBufferDepthForFixedTime

                # Sanity check.
                if desiredBufferDepth < 1:
                    Sentry.Warn("FINAL_SNAP", f"FinalSnap desiredImageHistoryCount is < 1!! {desiredBufferDepth}")
                    desiredBufferDepth = 1

                while len(self.SnapHistory) > desiredBufferDepth:
                    # Remove the oldest image, which is the image at the end of the list.
                    self.SnapHistory.pop()

        except Exception as e:
            Sentry.Exception("FinalSnap::_snapCallback failed to get snapshot.", e)
