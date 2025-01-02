import os
import sys
import logging
import logging.handlers

from .config import Config

class LoggerInit:

    # Sets up and returns the main logger object
    @staticmethod
    def GetLogger(config, klipperLogDir, logLevelOverride_CanBeNone) -> logging.Logger:
        logger = logging.getLogger()

        # From the possible logging values, read the current value from the config.
        # If there is no value or it doesn't map, use the default.
        possibleValueList = [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
        ]
        logLevel = config.GetStrIfInAcceptableList(Config.LoggingSection, Config.LogLevelKey, "INFO", possibleValueList)

        # Allow the dev config to override the log level.
        if logLevelOverride_CanBeNone is not None:
            logLevelOverride_CanBeNone = logLevelOverride_CanBeNone.upper()
            print("Dev config override log level from "+logLevel+" to "+logLevelOverride_CanBeNone)
            logLevel = logLevelOverride_CanBeNone

        # Set the final log level.
        logger.setLevel(logLevel)

        # Define our format
        formatter = logging.Formatter("%(levelname)-8s | %(asctime)s | %(message)s")

        # Setup logging to standard out.
        std = logging.StreamHandler(sys.stdout)
        std.setFormatter(formatter)
        logger.addHandler(std)

        # Setup the file logger
        maxFileSizeBytes = config.GetIntIfInRange(Config.LoggingSection, Config.LogFileMaxSizeMbKey, 5, 1, 5000) * 1024 * 1024
        maxFileCount = config.GetIntIfInRange(Config.LoggingSection, Config.LogFileMaxCountKey, 3, 1, 50)
        file = logging.handlers.RotatingFileHandler(
            os.path.join(klipperLogDir, "octoapp.log"),
            maxBytes=maxFileSizeBytes, backupCount=maxFileCount)
        file.setFormatter(formatter)
        logger.addHandler(file)

        return logger
