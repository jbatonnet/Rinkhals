import os

from .Logging import Logger
from .Context import Context
from .Util import Util
from .ObserverConfigFile import ObserverConfigFile


# This class does the same function as the Discovery class, but for the observer plugin setup.
class DiscoveryObserver:

    # This is the base data folder name that will be used, the plugin id suffix will be added to end of it.
    # The folders will always be in the user's home path.
    c_ObserverPluginDataRootFolder_Lower = "octoapp-companion-"
    # The legacy name, only used to find existing folders.
    c_ObserverPluginDataRootFolder_old_Lower = ".octoapp-observer-"

    def ObserverDiscovery(self, context:Context):
        Logger.Debug("Starting observer discovery.")

        # Look for existing observer data installs.
        existingObserverFolders = []
        # Sort so the folder we find are ordered from 1-... This makes the selection process nicer, since the ID == selection.
        fileAndDirList = sorted(os.listdir(context.UserHomePath))
        for fileOrDirName in fileAndDirList:
            if fileOrDirName.lower().startswith(DiscoveryObserver.c_ObserverPluginDataRootFolder_Lower) or fileOrDirName.lower().startswith(DiscoveryObserver.c_ObserverPluginDataRootFolder_old_Lower):
                existingObserverFolders.append(fileOrDirName)
                Logger.Debug(f"Found existing data folder: {fileOrDirName}")

        # If there's an existing folders, ask the user if they want to use them.
        if len(existingObserverFolders) > 0:
            count = 1
            Logger.Blank()
            Logger.Header("Existing OctoApp Observer Plugins Found")
            Logger.Blank()
            Logger.Info( "If you want to update or re-setup an instance, select instance id.")
            Logger.Info( "                        - or - ")
            Logger.Info( "If you want to install a new instance, select 'n'.")
            Logger.Blank()
            Logger.Info("Options:")
            for folder in existingObserverFolders:
                instanceId = self._GetObserverIdFromFolderName(folder)
                # Try to parse the config, if there is one and it's valid.
                ip, port = ObserverConfigFile.TryToParseConfig(ObserverConfigFile.GetConfigFilePathFromDataPath(os.path.join(context.UserHomePath, folder)))
                if ip is None and port is None:
                    Logger.Info(f"  {count}) Instance Id {instanceId} - Path: {folder}")
                else:
                    Logger.Info(f"  {count}) Instance Id {instanceId} - {ip}:{port}")
                count += 1
            Logger.Info("  n) Setup a new observer plugin instance")
            Logger.Blank()
            Logger.Blank()
            # Ask the user which number they want.
            responseInt = -1
            isFirstPrint = True
            while True:
                try:
                    if isFirstPrint:
                        isFirstPrint = False
                    else:
                        Logger.Warn( "If you need help, contact us! hello@octoapp.eu")
                    response = input("Enter an instance id or 'n': ")
                    response = response.lower().strip()
                    # If the response is n, fall through.
                    if response == "n":
                        break
                    # Parse the input and -1 it, so it aligns with the array length.
                    tempInt = int(response.lower().strip()) - 1
                    if tempInt >= 0 and tempInt < len(existingObserverFolders):
                        responseInt = tempInt
                        break
                    Logger.Warn("Invalid number selection, try again.")
                except Exception as _:
                    Logger.Warn("Invalid input, try again.")

            # If there is a response, the user selected an instance.
            if responseInt != -1:
                # Use this instance
                self._SetupContextFromVars(context, existingObserverFolders[responseInt])
                Logger.Info(f"Existing observer instance selected. Path: {context.ObserverDataPath}, Id: {context.ObserverInstanceId}")
                return

        # Create a new instance path. Either there is no existing data path or the user wanted to create a new one.
        # Since we have all of the data paths, we will make this new instance id be the count + 1.
        newId = str(len(existingObserverFolders) + 1)
        self._SetupContextFromVars(context, f"{DiscoveryObserver.c_ObserverPluginDataRootFolder_Lower}{newId}")
        Logger.Info(f"Creating a new Observer plugin data path. Path: {context.ObserverDataPath}, Id: {context.ObserverInstanceId}")
        return


    def _SetupContextFromVars(self, context:Context, folderName:str):
        # First, ensure we can parse the id and set it.
        context.ObserverInstanceId = self._GetObserverIdFromFolderName(folderName)

        # Make the full path
        context.ObserverDataPath = os.path.join(context.UserHomePath, folderName)

        # Ensure the file exists and we have permissions
        Util.EnsureDirExists(context.ObserverDataPath, context, True)


    def _GetObserverIdFromFolderName(self, folderName:str):
        folderName_lower = folderName.lower()
        # If we can find either of the names, return everything after the prefix, aka the instance id.
        if folderName_lower.startswith(DiscoveryObserver.c_ObserverPluginDataRootFolder_Lower) is True:
            return folderName_lower[len(DiscoveryObserver.c_ObserverPluginDataRootFolder_Lower):]
        if folderName_lower.startswith(DiscoveryObserver.c_ObserverPluginDataRootFolder_old_Lower) is True:
            return folderName_lower[len(DiscoveryObserver.c_ObserverPluginDataRootFolder_old_Lower):]
        Logger.Error(f"We tried to get an observer id from a non-observer data folder. {folderName}")
        raise Exception("We tried to get an observer id from a non-observer data folder")
