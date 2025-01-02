import os
import json
from enum import Enum

from .Logging import Logger
from .Paths import Paths


# Indicates the OS type this installer is running on.
class OsTypes(Enum):
    Debian = 1
    SonicPad = 2
    K1 = 3 # Both the K1 and K1 Max


# This class holds the context of the installer, meaning all of the target vars and paths
# that this instance is using.
# There is a generation system, where generation defines what data is required by when.
# Generation 1 - Must always exist, from the start.
# Generation 2 - Must exist after the discovery phase.
# Generation 3 - Must exist after the configure phase.
class Context:

    def __init__(self) -> None:

        #
        # Generation 1
        #

        # This is the repo root of OctoApp. This is common for all instances.
        self.RepoRootFolder:str = None

        # This is the path to the PY virtual env for OctoApp. This is common for all instances.
        self.VirtualEnvPath:str = None

        # This is the user name of the user who launched the install script.
        # Useful because this module is running as a sudo user.
        self.UserName:str = None

        # This is the user home path of the user who launched the install script.
        # Useful because this module is running as a sudo user.
        self.UserHomePath:str = None

        # A string containing all of the args the install script was launched with.
        self.CmdLineArgs:str = None

        # Detected in this installer as we are starting, this indicates what type of OS we are running on.
        self.OsType:OsTypes = OsTypes.Debian

        # Parsed from the command line args, if debug should be enabled.
        self.Debug:bool = False

        # Parsed from the command line args, if we should show help.
        self.ShowHelp:bool = False

        # Parsed from the command line args, if we should skip sudo actions for debugging.
        self.SkipSudoActions:bool = False

        # Parsed from the command line args, if set, we shouldn't auto select the moonraker instance.
        self.DisableAutoMoonrakerInstanceSelection:bool = False

        # Parsed from the command line args, if set, this plugin should be installed as an observer.
        self.IsObserverSetup:bool = False

        # Parsed from the command line args, if set, the plugin install should be in update mode.
        self.IsUpdateMode:bool = False

        # Parsed from the command line args, if set, the plugin install should be in uninstall mode.
        self.IsUninstallMode:bool = False


        #
        # Generation 2
        #

        # This is the full file path to the moonraker config.
        self.MoonrakerConfigFilePath:str = None

        # This is the file name of the moonraker service we are targeting.
        self.MoonrakerServiceFileName:str = None

        ### - OR - ###
        # These values will be filled out if this is an observer setup.

        # The root folder where this plugin instance will setup it's data.
        self.ObserverDataPath:str = None

        # The observer instance id, so we can support multiple instances on one device.
        self.ObserverInstanceId:str = None


        #
        # Generation 3
        #

        # Generation 3 - This it the path to the printer data root folder.
        self.PrinterDataFolder:str = None

        # Generation 3 - This it the path to the printer data config folder.
        self.PrinterDataConfigFolder:str = None

        # Generation 3 - This it the path to the printer data logs folder.
        self.PrinterDataLogsFolder:str = None

        # Generation 3 - This is the name of this OctoApp instance's service.
        self.ServiceName:str = None

        # Generation 3 - The full file path and file name of this instance's service file.
        self.ServiceFilePath:str = None

        # Generation 3 - The path to where the local storage will be put for this instance.
        self.LocalFileStorageFolder:str = None

        # Generation 3 - Only set if this is an observer setup
        self.ObserverConfigFilePath:str = None

        #
        # Generation 4
        #

        # Generation 4 - If the instance config file existed before we created the service, this will hold the printer id.
        self.ExistingPrinterId:str = None


    # Returns true if the OS is Creality OS, aka K1 or Sonic Pad
    def IsCrealityOs(self) -> bool:
        return self.OsType == OsTypes.SonicPad or self.OsType == OsTypes.K1


    @staticmethod
    def LoadFromArgString(argString:str):
        Logger.Debug("Found config: "+argString)
        try:
            argObj = json.loads(argString)
            context = Context()
            context.RepoRootFolder = argObj["OCTOAPP_REPO_DIR"]
            context.VirtualEnvPath = argObj["OCTOAPP_ENV"]
            context.UserName = argObj["USERNAME"]
            context.UserHomePath = argObj["USER_HOME"]
            context.CmdLineArgs = argObj["CMD_LINE_ARGS"]
            return context
        except Exception as e:
            Logger.Error(f"Failed to parse bootstrap json args. args string: `{argString}`")
            raise e


    def Validate(self, generation = 1) -> None:
        self._ValidatePathAndExists(self.RepoRootFolder, "Required Env Var OCTOAPP_REPO_DIR was not found; make sure to run the install.sh script to begin the installation process")
        self._ValidatePathAndExists(self.VirtualEnvPath, "Required Env Var OCTOAPP_ENV was not found; make sure to run the install.sh script to begin the installation process")
        self._ValidatePathAndExists(self.UserHomePath, "Required Env Var USER_HOME was not found; make sure to run the install.sh script to begin the installation process")
        self._ValidateString(self.UserName, "Required Env Var USERNAME was not found; make sure to run the install.sh script to begin the installation process")
        # Can be an empty string, but not None.
        if self.CmdLineArgs is None:
            raise Exception("Required Env Var CMD_LINE_ARGS was not found; make sure to run the install.sh script to begin the installation process.")

        # Since these exist, clean them up.
        self.RepoRootFolder = self.RepoRootFolder.strip()
        self.VirtualEnvPath = self.VirtualEnvPath.strip()
        self.UserName = self.UserName.strip()
        self.UserHomePath = self.UserHomePath.strip()
        self.CmdLineArgs = self.CmdLineArgs.strip()

        if generation >= 2:
            if self.IsObserverSetup:
                self._ValidatePathAndExists(self.ObserverDataPath, "Required config var Observer Data Path was not found")
                self._ValidateString(self.ObserverInstanceId, "Required config var Observer Instance Id was not found")
                self.ObserverDataPath = self.ObserverDataPath.strip()
                self.ObserverInstanceId = self.ObserverInstanceId.strip()
                if self.OsType != OsTypes.Debian:
                    raise Exception("The OctoApp companion can only be installed on Debian based operating systems.")
            else:
                self._ValidatePathAndExists(self.MoonrakerConfigFilePath, "Required config var Moonraker Config File Path was not found")
                self._ValidateString(self.MoonrakerServiceFileName, "Required config var Moonraker Service File Name was not found")
                self.MoonrakerConfigFilePath = self.MoonrakerConfigFilePath.strip()
                self.MoonrakerServiceFileName = self.MoonrakerServiceFileName.strip()

        if generation >= 3:
            self._ValidatePathAndExists(self.PrinterDataFolder, "Required config var Printer Data Folder was not found")
            self._ValidatePathAndExists(self.PrinterDataConfigFolder, "Required config var Printer Data Config Folder was not found")
            self._ValidatePathAndExists(self.PrinterDataLogsFolder, "Required config var Printer Data Logs Folder was not found")
            self._ValidatePathAndExists(self.PrinterDataLogsFolder, "Required config var Printer Data Logs Folder was not found")
            self._ValidatePathAndExists(self.LocalFileStorageFolder, "Required config var local storage folder was not found")
            # This path wont exist on the first install, because it won't be created until the end of the install.
            self._ValidateString(self.ServiceFilePath, "Required config var service file path was not found")
            self._ValidateString(self.ServiceName, "Required config var service name was not found")
            if self.IsObserverSetup:
                self._ValidatePathAndExists(self.ObserverConfigFilePath, "Required config var Observer Config File Path was not found")

        if generation >= 4:
            # The printer ID can be None, this means it didn't exist before we installed the service.
            pass


    def ParseCmdLineArgs(self):
        # We must have a string, indicating the ./install script passed the var.
        # But it can be an empty string, that's fine.
        if self.CmdLineArgs is None:
            raise Exception("Required Env Var CMD_LINE_ARGS was not found; make sure to run the install.sh script to begin the installation process")

        # Handle the original cmdline args.
        # The format is <moonraker config file path> <moonraker service file path> -other -args
        # Where both file paths are optional, but if only one is given, it's assumed to be the config file path.
        args = self.CmdLineArgs.split(' ')
        for a in args:
            # Ensure there's a string and it's not empty.
            # If no args are passed, there will be one empty string after the split.
            if isinstance(a, str) is False or len(a) == 0:
                continue

            # Handle and flags passed.
            if a[0] == '-':
                rawArg = a[1:]
                if rawArg.lower() == "debug":
                    # Enable debug printing.
                    self.Debug = True
                    Logger.EnableDebugLogging()
                elif rawArg.lower() == "help" or rawArg.lower() == "usage" or rawArg.lower() == "h":
                    self.ShowHelp = True
                elif rawArg.lower() == "skipsudoactions":
                    Logger.Warn("Skipping sudo actions. ! This will not result in a valid install! ")
                    self.SkipSudoActions = True
                elif rawArg.lower() == "noatuoselect":
                    Logger.Info("Disabling Moonraker instance auto selection.")
                    self.DisableAutoMoonrakerInstanceSelection = True
                elif rawArg.lower() == "observer":
                    # This is the legacy flag
                    Logger.Info("Setup running in companion setup mode.")
                    self.IsObserverSetup = True
                elif rawArg.lower() == "companion":
                    Logger.Info("Setup running in companion setup mode.")
                    self.IsObserverSetup = True
                elif rawArg.lower() == "update":
                    Logger.Info("Setup running in update mode.")
                    self.IsUpdateMode = True
                elif rawArg.lower() == "uninstall":
                    Logger.Info("Setup running in uninstall mode.")
                    self.IsUninstallMode = True
                else:
                    raise Exception("Unknown argument found. Use install.sh -help for options.")

            # If there's a raw string, assume its a config path or service file name.
            else:
                if self.MoonrakerConfigFilePath is None:
                    self.MoonrakerConfigFilePath = a
                    Logger.Debug("Moonraker config file path found as argument:"+self.MoonrakerConfigFilePath)
                elif self.MoonrakerServiceFileName is None:
                    self.MoonrakerServiceFileName = a
                    Logger.Debug("Moonraker service file name found as argument:"+self.MoonrakerServiceFileName)
                else:
                    raise Exception("Unknown argument found. Use install.sh -help for options.")


    def _ValidatePathAndExists(self, path:str, error:str):
        if path is None or os.path.exists(path) is False:
            raise Exception(error)


    def _ValidateString(self, s:str, error:str):
        if s is None or isinstance(s, str) is False or len(s) == 0:
            raise Exception(error)


    def DetectOsType(self):
        #
        # Note! This should closely resemble the ostype.py class in the plugin and the logic in the ./install.sh script!
        #

        # For the k1 and k1 max, we look for the "buildroot" OS.
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r", encoding="utf-8") as osInfo:
                lines = osInfo.readlines()
                for l in lines:
                    if "ID=buildroot" in l:
                        # If we find it, make sure the user data path is where we expect it to be, and we are good.
                        if os.path.exists(Paths.CrealityOsUserDataPath_K1):
                            self.OsType = OsTypes.K1
                            return
                        raise Exception("We detected a K1 or K1 Max OS, but can't determine the data path. Please contact support.")

        # For the Sonic Pad, we look for the openwrt os
        if os.path.exists("/etc/openwrt_release"):
            with open("/etc/openwrt_release", "r", encoding="utf-8") as osInfo:
                lines = osInfo.readlines()
                for l in lines:
                    if "sonic" in l:
                        # If we find it, make sure the user data path is where we expect it to be, and we are good.
                        if os.path.exists(Paths.CrealityOsUserDataPath_SonicPad):
                            self.OsType = OsTypes.SonicPad
                            return
                        raise Exception("We detected a Sonic Pad, but can't determine the data path. Please contact support.")

        # The OS is debian
        self.OsType = OsTypes.Debian
        return
