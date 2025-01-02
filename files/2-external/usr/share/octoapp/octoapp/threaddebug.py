import threading
import time
import sys
import traceback

class ThreadDebug:

    def Start(self, logger, delaySec):
        try:
            th = threading.Thread(target=self.threadWorker, args=(logger, delaySec))
            # pylint: disable=deprecated-method
            # This is deprecated in PY3.10
            th.setDaemon(True)
            th.start()
        except Exception as e:
            logger.error("Failed to start Thread Debug Thread: "+str(e))

    def threadWorker(self, logger, delaySec):
        while True:
            try:
                logger.info("ThreadDump - Starting Thread Dump")
                self.DoThreadDumpLogout(logger)
            except Exception as e:
                logger.error("Exception in ThreadDebug : "+str(e))
            time.sleep(delaySec)

    @staticmethod
    def DoThreadDumpLogout(logger):
        try:
            logger.info("ThreadDump - Starting Thread Dump")
            # pylint: disable=protected-access
            for threadId, stack in sys._current_frames().items():
                trace = ""
                for filename, _, name, _ in traceback.extract_stack(stack):
                    parts = filename.split("\\")
                    if len(parts) == 0:
                        parts  = filename.split("/")
                    if len(parts) > 0:
                        trace += ", "+parts[len(parts)-1]+":"+name
                    else:
                        trace += ", "+filename+":"+name
                logger.info("ThreadDump- Id: "+str(threadId) + " -> "+str(trace))
        except Exception as e:
            logger.error("Exception in ThreadDebug : "+str(e))
