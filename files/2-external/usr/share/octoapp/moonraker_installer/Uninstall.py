import os
import shutil

from .Context import Context
from .Context import OsTypes
from .Logging import Logger
from .Configure import Configure
from .Paths import Paths
from .Util import Util

class Uninstall:

    def DoUninstall(self, context:Context):

        Logger.Blank()
        Logger.Blank()
        Logger.Header("You're about to uninstall OctoApp.")
        Logger.Info  ("This printer ID will be deleted, but you can always reinstall the plugin and re-add this printer.")
        Logger.Blank()
        r =     input("Are you want to uninstall? [y/n]")
        r = r.lower().strip()
        if r != "y":
            Logger.Info("Uninstall canceled.")
            Logger.Blank()
            return
        Logger.Blank()
        Logger.Blank()
        Logger.Header("Starting OctoApp uninstall")

        # Since all service names must use the same identifier in them, we can find any services using the same search.
        foundOeServices = []
        fileAndDirList = sorted(os.listdir(Paths.GetServiceFileFolderPath(context)))
        for fileOrDirName in fileAndDirList:
            Logger.Debug(f" Searching for OE services to remove, found: {fileOrDirName}")
            if Configure.c_ServiceCommonName in fileOrDirName.lower():
                foundOeServices.append(fileOrDirName)

        if len(foundOeServices) == 0:
            Logger.Warn("No local plugins or companions were found to remove.")
            return

        # TODO - We need to cleanup more, but for now, just make sure any services are shutdown.
        Logger.Info("Stopping services...")
        for serviceFileName in foundOeServices:
            if context.OsType == OsTypes.SonicPad:
                # We need to build the fill name path
                serviceFilePath = os.path.join(Paths.CrealityOsServiceFilePath, serviceFileName)
                Logger.Debug(f"Full service path: {serviceFilePath}")
                Logger.Info(f"Stopping and deleting {serviceFileName}...")
                Util.RunShellCommand(f"{serviceFilePath} stop", False)
                Util.RunShellCommand(f"{serviceFilePath} disable", False)
                os.remove(serviceFilePath)
            elif context.OsType == OsTypes.K1:
                # We need to build the fill name path
                serviceFilePath = os.path.join(Paths.CrealityOsServiceFilePath, serviceFileName)
                Logger.Debug(f"Full service path: {serviceFilePath}")
                Logger.Info(f"Stopping and deleting {serviceFileName}...")
                Util.RunShellCommand(f"{serviceFilePath} stop", False)
                Util.RunShellCommand("ps -ef | grep 'moonraker_octoapp' | grep -v grep | awk '{print $1}' | xargs -r kill -9", False)
                os.remove(serviceFilePath)
            elif context.OsType == OsTypes.Debian:
                Logger.Info(f"Stopping and deleting {serviceFileName}...")
                Util.RunShellCommand("systemctl stop "+serviceFileName, False)
                Util.RunShellCommand("systemctl disable "+serviceFileName, False)
            else:
                raise Exception("This OS type doesn't support uninstalling at this time.")

        # For now, systems that have fixed setups, set will remove files
        # TODO - We need to do a total cleanup of all files.
        if context.OsType == OsTypes.K1:
            self.DoK1FileCleanup()

        Logger.Blank()
        Logger.Blank()
        Logger.Header("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        Logger.Info(  "                OctoApp Uninstall Complete            ")
        Logger.Info(  "     We will miss you, please come back anytime!       ")
        Logger.Header("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        Logger.Blank()
        Logger.Blank()


    # For the K1, we know a the fixed paths where everything must be installed.
    # There's only one instance of moonraker, so there's no need to worry about multiple setups.
    def DoK1FileCleanup(self):
        # In modern setups, the env is here. In very few early installs, it's in /usr/share
        self.DeleteDirOrFileIfExists("/usr/data/octoapp-env")
        self.DeleteDirOrFileIfExists("/usr/share/octoapp-env")

        # For all installs, the storage folder will be here
        self.DeleteDirOrFileIfExists("/usr/data/printer_data/octoapp-store")
        # Delete any log files we have, there might be some rolling backups.
        self.DeleteAllFilesContaining("/usr/data/printer_data/logs", "octoapp")
        # Delete any config files.
        self.DeleteAllFilesContaining("/usr/data/printer_data/config", "octoapp")
        # Remove our system config file include in the moonraker file, if there is one.
        self.RemoveOctoAppSystemCfgInclude("/usr/data/printer_data/config/moonraker.conf")
        # Delete the installer file if it's still there
        self.DeleteDirOrFileIfExists("/usr/data/octoapp-installer.log")

        # Finally, remove the repo root. Note that /usr/share was used in very few early installs.
        self.DeleteDirOrFileIfExists("/usr/data/octoapp")
        self.DeleteDirOrFileIfExists("/usr/share/octoapp")


    # Deletes a file or directory, if it exists.
    def DeleteDirOrFileIfExists(self, path:str):
        Logger.Debug(f"Deleting file or dir [{path}]")
        try:
            if os.path.exists(path) is False:
                return
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)
            else:
                Logger.Error(f"DeleteDirOrFileIfExists can delete file type {path}")
        except Exception as e:
            Logger.Error(f"DeleteDirOrFileIfExists failed to delete {path} - {e}")


    # Deletes any in the dir that match the search string.
    def DeleteAllFilesContaining(self, path:str, searchStr:str):
        try:
            searchLower = searchStr.lower()
            for fileName in os.listdir(path):
                fullpath = os.path.join(path, fileName)
                if os.path.isfile(fullpath):
                    if searchLower in fileName.lower():
                        Logger.Debug(f"Deleting matched file: {fullpath}")
                        os.remove(fullpath)
        except Exception as e:
            Logger.Error(f"DeleteAllFilesContaining failed to delete {path} - {e}")


    # Deletes the octoapp-system.cfg file include if it exists in the moonraker config.
    def RemoveOctoAppSystemCfgInclude(self, moonrakerConfigPath:str):
        try:
            Logger.Debug(f"Looking for OE system config include in {moonrakerConfigPath}")
            output = []
            lineFound = False
            with open(moonrakerConfigPath, encoding="utf-8") as f:
                lines = f.readlines()
                for l in lines:
                    if "octoapp-system.cfg" in l.lower():
                        lineFound = True
                    else:
                        output.append(l)

            if lineFound is False:
                Logger.Debug("system config include not found.")
                return

            # Output the file without the line.
            with open(moonrakerConfigPath, encoding="utf-8", mode="w") as f:
                for o in output:
                    f.write(f"{o}")

            Logger.Debug(f"Removed octoapp system config from {moonrakerConfigPath}")
        except Exception as e:
            Logger.Error(f"DeleteAllFilesContaining failed to delete {moonrakerConfigPath} - {e}")
