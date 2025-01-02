import os
import threading

import configparser

# This is what we use as our important settings config.
# It's a bit heavy handed with the lock and aggressive saving, but these
# settings are important, and not accessed much.
class Config:

    # This can't change or all past plugins will fail. It's also used by the installer.
    ConfigFileName = "octoapp.conf"

    ServerSection = "server"

    RelaySection = "relay"
    RelayFrontEndPortKey = "frontend_port"            # This field is shared with the installer, the installer can write this value. It the name can't change!
    RelayFrontEndTypeHintKey = "frontend_type_hint"   # This field is shared with the installer, the installer can write this value. It the name can't change!

    LoggingSection = "logging"
    LogLevelKey = "log_level"
    LogFileMaxSizeMbKey = "max_file_size_mb"
    LogFileMaxCountKey = "max_file_count"

    WebcamSection = "webcam"
    WebcamAutoSettings = "auto_settings_detection"
    WebcamNameToUseAsPrimary = "webcam_name_to_use_as_primary"
    WebcamStreamUrl = "stream_url"
    WebcamSnapshotUrl = "snapshot_url"
    WebcamFlipH = "flip_horizontally"
    WebcamFlipV = "flip_vertically"
    WebcamRotation = "rotate"

    # This allows us to add comments into our config.
    # The objects must have two parts, first, a string they target. If the string is found, the comment will be inserted above the target string. This can be a section or value.
    # A string, which is the comment to be inserted.
    c_ConfigComments = [
        # { "Target": RelayFrontEndPortKey,  "Comment": "The port used for http relay. If your desired frontend runs on a different port, change this value. The OctoApp plugin service needs to be restarted before changes will take effect."},
        # { "Target": RelayFrontEndTypeHintKey,  "Comment": "A string only used by the UI to hint at what web interface this port is."},
        { "Target": LogLevelKey,  "Comment": "The active logging level. Valid values include: DEBUG, INFO, WARNING, or ERROR."},
        # { "Target": WebcamNameToUseAsPrimary,  "Comment": "This is the webcam name OctoApp will use. This much match the camera 'Name' from your Mainsail of Fluidd webcam settings. The default value of 'Default' will pick whatever camera the system can find."},
        # { "Target": WebcamAutoSettings,  "Comment": "Enables or disables auto webcam setting detection. If enabled, OctoApp will find the webcam settings configured via the frontend (Fluidd, Mainsail, etc) and use them. Disable to manually set the values and have them not be overwritten."},
        # { "Target": WebcamStreamUrl,  "Comment": "Webcam streaming URL. This can be a local relative path (ex: /webcam/?action=stream) or absolute http URL (ex: http://10.0.0.1:8080/webcam/?action=stream or http://webcam.local/webcam/?action=stream)"},
        # { "Target": WebcamSnapshotUrl,  "Comment": "Webcam snapshot URL. This can be a local relative path (ex: /webcam/?action=snapshot) or absolute http URL (ex: http://10.0.0.1:8080/webcam/?action=snapshot or http://webcam.local/webcam/?action=snapshot)"},
        # { "Target": WebcamFlipH,  "Comment": "Flips the webcam image horizontally. Valid values are True or False"},
        # { "Target": WebcamFlipV,  "Comment": "Flips the webcam image vertically. Valid values are True or False"},
        # { "Target": WebcamRotation,  "Comment": "Rotates the webcam image. Valid values are 0, 90, 180, or 270"},
    ]

    # The config lib we use doesn't support the % sign, even though it's valid .cfg syntax.
    # Since we save URLs into the config for the webcam, it's valid syntax to use a %20 and such, thus we should support it.
    PercentageStringReplaceString = "~~~PercentageSignPlaceholder~~~"


    def __init__(self, klipperConfigPath) -> None:
        self.Logger = None
        # Define our config path
        # Note this path and name MUST STAY THE SAME because the installer PY script looks for this file.
        self.OeConfigFilePath = os.path.join(klipperConfigPath, Config.ConfigFileName)
        # A lock to keep file access super safe
        self.ConfigLock = threading.Lock()
        self.Config = None
        # Load the config on init, to ensure it exists.
        # This will throw if there's an error reading the config.
        self._LoadConfigIfNeeded_UnderLock()


    # Allows the logger to be set when it's created.
    def SetLogger(self, logger):
        self.Logger = logger


    # Forces a full config read & parse from the file.
    def ReloadFromFile(self) -> None:
        # Lock and force a read.
        with self.ConfigLock:
            self._LoadConfigIfNeeded_UnderLock(forceRead=True)


    # Gets a value from the config given the header and key.
    # If the value isn't set, the default value is returned and the default value is saved into the config.
    def GetStr(self, section, key, defaultValue) -> str:
        with self.ConfigLock:
            # Ensure we have the config.
            self._LoadConfigIfNeeded_UnderLock()
            # Check if the section and key exists
            if self.Config.has_section(section):
                if key in self.Config[section].keys():
                    # If the value of None was written, it was an accidental serialized None value to string.
                    # Consider it not a valid value, and use the default value.
                    value = self.Config[section][key]
                    if value != "None":
                        # Reverse any possible string replaces we had to add.
                        value = value.replace(Config.PercentageStringReplaceString, "%")
                        return value
        # The value wasn't set, create it using the default.
        self.SetStr(section, key, defaultValue)
        return defaultValue


    # Gets a value from the config given the header and key.
    # If the value isn't set, the default value is returned and the default value is saved into the config.
    def GetInt(self, section, key, defaultValue) -> int:
        # Use a try catch, so if a user sets an invalid value, it doesn't crash us.
        try:
            return int(self.GetStr(section, key, str(defaultValue)))
        except Exception as e:
            self.Logger.error("Config settings error! "+key+" failed to get as int. Resetting to default. "+str(e))
            self.SetStr(section, key, str(defaultValue))
            return int(defaultValue)


    # Gets a value from the config given the header and key.
    # If the value isn't set, the default value is returned and the default value is saved into the config.
    def GetBool(self, section, key, defaultValue) -> bool:
        # Use a try catch, so if a user sets an invalid value, it doesn't crash us.
        try:
            strValue = self.GetStr(section, key, str(defaultValue)).lower()
            if strValue == "false":
                return False
            elif strValue == "true":
                return True
            raise Exception("Invalid bool value, value was: "+strValue)
        except Exception as e:
            self.Logger.error("Config settings error! "+key+" failed to get as bool. Resetting to default. "+str(e))
            self.SetStr(section, key, str(defaultValue))
            return bool(defaultValue)


    # The same as Get, but this version ensures that the value matches a case insensitive value in the
    # acceptable value list. If it's not, the default value is used.
    def GetStrIfInAcceptableList(self, section, key, defaultValue, acceptableValueList) -> str:
        existing = self.GetStr(section, key, defaultValue)
        # Check the acceptable values
        for v in acceptableValueList:
            # If we match, this is a good value, return it.
            if v.lower() == existing.lower():
                return existing

        # The acceptable was not found. Set they key back to default.
        self.SetStr(section, key, defaultValue)
        return defaultValue


    # The same as Get, but it makes sure the value is in a range.
    def GetIntIfInRange(self, section, key, defaultValue, lowerBoundInclusive, upperBoundInclusive) -> int:
        existingStr = self.GetStr(section, key, str(defaultValue))

        # Make sure the value is in range.
        try:
            existing = int(existingStr)
            if existing >= lowerBoundInclusive and existing <= upperBoundInclusive:
                return existing
        except Exception:
            pass

        # The acceptable was not found. Set they key back to default.
        self.SetStr(section, key, str(defaultValue))
        return defaultValue


    # Sets the value into the config and saves it.
    # Setting a value of None will delete the key from the config.
    def SetStr(self, section, key, value) -> None:
        # Ensure the value is a string, unless it's None
        if value is not None:
            value = str(value)
            # The config library we use doesn't allow for % to be used in strings, even though it should be legal.
            value = value.replace("%", Config.PercentageStringReplaceString)
        with self.ConfigLock:
            self._LoadConfigIfNeeded_UnderLock()
            # Ensure the section exists
            if self.Config.has_section(section) is False:
                self.Config.add_section(section)
            if value is None:
                # If we are setting to None, delete the key if it exists.
                if key in self.Config[section].keys():
                    del self.Config[section][key]
            else:
                # If not none, set the key
                self.Config[section][key] = value
            self._SaveConfig_UnderLock()


    def _LoadConfigIfNeeded_UnderLock(self, forceRead = False) -> None:
        if self.Config is not None and forceRead is False:
            return

        # Always create a new object.
        # For our config, we use strict and such, so we know the config is valid.
        self.Config = configparser.ConfigParser()

        # If a config exists, read it.
        # This will throw on failure.
        if os.path.exists(self.OeConfigFilePath):
            self.Config.read(self.OeConfigFilePath)
        else:
            # If no config exists, create a new file by writing the empty config now.
            print("Config file doesn't exist. Creating a new file now!")
            self._SaveConfig_UnderLock()


    def _SaveConfig_UnderLock(self) -> None:
        if self.Config is None:
            return

        # Write the current settings to the file.
        # This lets the config lib format everything how it wants.
        with open(self.OeConfigFilePath, 'w', encoding="utf-8") as f:
            self.Config.write(f)

        # After writing, read the file and insert any comments we have.
        finalOutput = ""
        with open(self.OeConfigFilePath, 'r', encoding="utf-8") as f:
            # Read all lines
            lines = f.readlines()
            for line in lines:
                lineLower = line.lower()
                # If anything in the line matches the target, add the comment just before this line.
                for cObj in Config.c_ConfigComments:
                    if cObj["Target"] in lineLower:
                        # Add the comment.
                        finalOutput += "# " + cObj["Comment"] + os.linesep
                        break
                finalOutput += line

        # Finally, write the file back one more time.
        with open(self.OeConfigFilePath, 'w', encoding="utf-8") as f:
            f.write(finalOutput)
