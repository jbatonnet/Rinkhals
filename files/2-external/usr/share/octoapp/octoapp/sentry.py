import logging
import time
import traceback

# import sentry_sdk
# from sentry_sdk.integrations.logging import LoggingIntegration
# from sentry_sdk.integrations.threading import ThreadingIntegration
# from sentry_sdk import capture_exception

# A helper class to handle Sentry logic.
class Sentry:
    logger = None
    isDevMode = False
    lastErrorReport = time.time()
    lastErrorCount = 0

# Sets up Sentry
    @staticmethod
    def Init(logger, versionString, isDevMode):
        # Capture the logger for future use.
        Sentry.Logger = logger

        # Set the dev mode flag.
        Sentry.isDevMode = isDevMode

        # Only setup sentry if we aren't in dev mode.
        if Sentry.isDevMode is False:
            try:
                # Disabled for now
                #
                # We don't want sentry to capture error logs, which is it's default.
                # We do want the logging for breadcrumbs, so we will leave it enabled.
                # sentry_logging = LoggingIntegration(
                #     level=logging.INFO,        # Capture info and above as breadcrumbs
                #     event_level=logging.FATAL  # Only send FATAL errors and above.
                # )
                # # Setup and init
                # sentry_sdk.init(
                #     dsn="https://a2eaa1b58ea447f08472545eedfc74fb@o1317704.ingest.sentry.io/6570908",
                #     integrations=[
                #         sentry_logging,
                #         ThreadingIntegration(propagate_hub=True),
                #     ],
                #     release=versionString,
                #     before_send=Sentry._beforeSendFilter
                # )
                pass
            except Exception as e:
                logger.error("Failed to init Sentry: "+str(e))


    @staticmethod
    def _beforeSendFilter(event, hint):
        # To prevent spamming, don't allow clients to send errors too quickly.
        # We will simply only allows up to 5 errors reported every 24h.
        timeSinceErrorSec = time.time() - Sentry.lastErrorReport
        if timeSinceErrorSec < 60 * 60 * 24:
            if Sentry.lastErrorCount > 5:
                return None
        else:
            # A new time window has been entered.
            Sentry.lastErrorReport = time.time()
            Sentry.lastErrorCount = 0

        # Increment the report counter
        Sentry.lastErrorCount += 1

        # Since all OctoPrint plugins run in the same process, sentry will pick-up unhandled exceptions
        # from all kinds of sources. To prevent that from spamming us, if we can pull out a call stack, we will only
        # send things that have some origin in our code. This can be any file in the stack or any module with our name in it.
        # Otherwise, we will ignore it.
        exc_info = hint.get("exc_info")
        if exc_info is None or len(exc_info) < 2 or hasattr(exc_info[2], "tb_frame") is False:
            return None

        # Check the stack
        try:
            stack = traceback.extract_stack((exc_info[2]).tb_frame)
            for s in stack:
                # Check for any "octoapp". The main source should be our package folder, which is
                # "octoprint_octoapp".
                filenameLower = s.filename.lower()
                if "octoapp" in filenameLower:
                    # If found, return the event so it's reported.
                    return event
        except Exception as e:
            Sentry.Logger.error("Failed to extract exception stack in sentry before send. "+str(e))

        # Return none to prevent sending.
        return None
    
    @staticmethod
    def Info(tag, msg):
        paddedTag = "{:<15}".format(tag).upper()
        Sentry.Logger.info(paddedTag + " | " + msg)

    @staticmethod
    def Debug(tag, msg):
        paddedTag = "{:<15}".format(tag).upper()
        Sentry.Logger.debug(paddedTag + " | " + msg)

    @staticmethod
    def Warn(tag, msg):
        paddedTag = "{:<15}".format(tag).upper()
        Sentry.Logger.warning(paddedTag + " | " + msg)

    @staticmethod
    def Error(tag, msg):
        paddedTag = "{:<15}".format(tag).upper()
        Sentry.Logger.error(paddedTag + " | " + msg)


    # Logs and reports an exception.
    @staticmethod
    def Exception(msg, exception):
        Sentry._handleException(msg, exception, True)


    # Only logs an exception, without reporting.
    @staticmethod
    def ExceptionNoSend(msg, exception):
        Sentry.Error("SENTRY", "Exception no send: %s" % exception)
        Sentry._handleException(msg, exception, False)


    # Does the work
    @staticmethod
    def _handleException(msg, exception, sendException):

        # This could be called before the class has been inited, in such a case just return.
        if Sentry.Logger is None:
            return

        tb = traceback.format_exc()
        exceptionClassType = "unknown_type"
        if exception is not None:
            exceptionClassType = exception.__class__.__name__
        Sentry.Logger.error(msg + "; "+str(exceptionClassType)+" Exception: " + str(exception) + "; "+str(tb))

        # Sentry is disabled for now.
        # Never send in dev mode, as Sentry will not be setup.
        # if sendException and Sentry.isDevMode is False:
        #     capture_exception(exception)
