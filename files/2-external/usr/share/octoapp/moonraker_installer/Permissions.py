import os

from .Context import Context
from .Logging import Logger
from .Util import Util
from .Frontend import Frontend


class Permissions:
    # Must be lower case.
    c_RootUserName = "root"

    # For some companion setups, users only use one user on the device, root.
    # In this case, it's ok to install as root, but sometimes the $USER is empty
    # Thus, if the home user path is root, we will update the user to be root as well.
    # Note that since the install script always cd ~, we should have the correct home user.
    #
    # Also note, this function runs before the first context validation, so the vars could be null.
    def CheckUserAndCorrectIfRequired_RanBeforeFirstContextValidation(self, context:Context) -> None:
        # If this is a companion install, check if we need to set the user name.
        # It's ok be ran as root, but sometimes the bash USER var isn't set to the user name.
        if context.IsObserverSetup:
            if context.UserName is None or len(context.UserName) == 0:
                # Since the install script does a cd ~, we know if the user home path starts with /root/, the user is root.
                if context.UserHomePath is not None and context.UserHomePath.lower().startswith("/root/"):
                    Logger.Info("No user passed, but we detected the user is root.")
                    context.UserName = Permissions.c_RootUserName


    def EnsureRunningAsRootOrSudo(self, context:Context) -> None:
        # IT'S NOT OK TO INSTALL AS ROOT for the normal klipper setup.
        # This is because the moonraker updater system needs to get able to access the .git repo.
        # If the repo is owned by the root, it can't do that.
        # For the Sonic Pad and K1 setup, the only user is root, so it's ok.
        if context.IsObserverSetup is False and context.IsCrealityOs() is False:
            if context.UserName.lower() == Permissions.c_RootUserName:
                raise Exception("The installer was ran under the root user, this will cause problems with Moonraker. Please run the installer script as a non-root user, usually that's the `pi` user.")

        # But regardless of the user, we must have sudo permissions.
        # pylint: disable=no-member # Linux only
        if os.geteuid() != 0:
            if context.Debug:
                Logger.Warn("Not running as root, but ignoring since we are in debug.")
            else:
                raise Exception("Script not ran as root or using sudo. This is required to integrate into Moonraker.")


    # Called at the end of the setup process, just before the service is restarted or updated.
    # The point of this is to ensure we have permissions set correctly on all of our files,
    # so the plugin can access them.
    #
    # We always set the permissions for all of the files we touch, to ensure if something in the setup process
    # did it wrong, a user changed them, or some other service changed them, they are all correct.
    def EnsureFinalPermissions(self, context:Context):

        # A helper to set file permissions.
        # We try to set permissions to all paths and files in the context, some might be null
        # due to the setup mode. We don't care to difference the setup mode here, because the context
        # validation will do that for us already. Thus if a field is None, its ok.
        def SetPermissions(path:str):
            if path is not None and len(path) != 0:
                Util.SetFileOwnerRecursive(path, context.UserName)

        # For all setups, make sure the entire repo is owned by the user who launched the script.
        # This is required, in case the user accidentally used the wrong user at first and some part of the git repo is owned by the root user.
        # If Moonraker is running locally and this is owned by root for example, the Moonraker Updater can't access it, and will show errors.
        Util.SetFileOwnerRecursive(context.RepoRootFolder, context.UserName)

        # These following files or folders must be owned by the user the service is running under.
        f = Frontend()
        SetPermissions(f.GetOctoAppServiceConfigFilePath(context))
        SetPermissions(context.MoonrakerConfigFilePath)
        SetPermissions(context.ObserverDataPath)
        SetPermissions(context.LocalFileStorageFolder)
        SetPermissions(context.ObserverConfigFilePath)
