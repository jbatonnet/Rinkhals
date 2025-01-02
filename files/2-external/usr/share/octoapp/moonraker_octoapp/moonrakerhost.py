import time
import logging
import traceback

from octoapp.mdns import MDns
from octoapp.sentry import Sentry
from octoapp.hostcommon import HostCommon
from octoapp.webcamhelper import WebcamHelper
from octoapp.octohttprequest import OctoHttpRequest
from octoapp.Proto.ServerHost import ServerHost
from octoapp.localip import LocalIpHelper
from octoapp.compat import Compat
from octoapp.appsstorage import AppStorageHelper

from .config import Config
from .secrets import Secrets
from .version import Version
from .logger import LoggerInit
from .smartpause import SmartPause
from .systemconfigmanager import SystemConfigManager
from .moonrakerclient import MoonrakerClient
from .moonrakerwebcamhelper import MoonrakerWebcamHelper
from .moonrakerdatabase import MoonrakerDatabase
from .webrequestresponsehandler import MoonrakerWebRequestResponseHandler
from .moonrakercredentailmanager import MoonrakerCredentialManager
from .filemetadatacache import FileMetadataCache
from .uiinjector import UiInjector
from .observerconfigfile import ObserverConfigFile
from .moonrakerappstorage import MoonrakerAppStorage

# This file is the main host for the moonraker service.
class MoonrakerHost:

    def __init__(self, klipperConfigDir, klipperLogDir, devConfig_CanBeNone) -> None:
        # When we create our class, make sure all of our core requirements are created.
        self.MoonrakerWebcamHelper = None
        self.MoonrakerDatabase = None
        self.Secrets = None

        # Let the compat system know this is an Moonraker host.
        Compat.SetIsMoonraker(True)

        try:
            # First, we need to load our config.
            # Note that the config MUST BE WRITTEN into this folder, that's where the setup installer is going to look for it.
            # If this fails, it will throw.
            self.Config = Config(klipperConfigDir)

            # Next, setup the logger.
            logLevelOverride_CanBeNone = self.GetDevConfigStr(devConfig_CanBeNone, "LogLevel")
            self.Logger = LoggerInit.GetLogger(self.Config, klipperLogDir, logLevelOverride_CanBeNone)
            self.Config.SetLogger(self.Logger)
            
            # Init sentry, since it's needed for Exceptions.
            Sentry.Init(self.Logger, "klipper", False)

        except Exception as e:
            tb = traceback.format_exc()
            print("Failed to init Moonraker Host! "+str(e) + "; "+str(tb))
            # Raise the exception so we don't continue.
            raise


    def RunBlocking(self, klipperConfigDir, isObserverMode, localStorageDir, serviceName, pyVirtEnvRoot, repoRoot,
                    moonrakerConfigFilePath, # Will be None in Observer mode
                    observerConfigFilePath, observerInstanceIdStr, # Will be None in NOT Observer mode
                    devConfig_CanBeNone):
        # Do all of this in a try catch, so we can log any issues before exiting
        try:
            Sentry.Info("Host", "###########################")
            Sentry.Info("Host", "#### OctoApp Starting #####")
            Sentry.Info("Host", "###########################")

            # Set observer mode flag as soon as we know it.
            Compat.SetIsObserverMode(isObserverMode)

            # Find the version of the plugin, this is required and it will throw if it fails.
            pluginVersionStr = Version.GetPluginVersion(repoRoot)
            Sentry.Info("Host", "Plugin Version: %s" % pluginVersionStr)

            # This logic only works if running locally.
            if not isObserverMode:
                # Before we do this first time setup, make sure our config files are in place. This is important
                # because if this fails it will throw. We don't want to let the user complete the install setup if things
                # with the update aren't working.
                SystemConfigManager.EnsureUpdateManagerFilesSetup(klipperConfigDir, serviceName, pyVirtEnvRoot, repoRoot)

            # Before the first time setup, we must also init the Secrets class and do the migration for the printer id and private key, if needed.
            # As of 8/15/2023, we don't store any sensitive things in teh config file, since all config files are sometimes backed up publicly.
            self.Secrets = Secrets(localStorageDir, self.Config)

            # Always init the observer config file class, even if we aren't in observer mode, it handles denying requests.
            ObserverConfigFile.Init(observerConfigFilePath)

            # Now, detect if this is a new instance and we need to init our global vars. If so, the setup script will be waiting on this.
            self.DoFirstTimeSetupIfNeeded(klipperConfigDir, serviceName)

            # Get our required vars
            printerId = self.GetPrinterId()
            privateKey = self.GetPrivateKey()

            # Unpack any dev vars that might exist
            DevLocalServerAddress_CanBeNone = self.GetDevConfigStr(devConfig_CanBeNone, "LocalServerAddress")
            if DevLocalServerAddress_CanBeNone is not None:
                Sentry.Warn("Host", "~~~ Using Local Dev Server Address: %s ~~~" % DevLocalServerAddress_CanBeNone)

            # Init the mdns client
            MDns.Init(localStorageDir)

            # Allow the UI injector to run and do it's thing.
            UiInjector.Init(repoRoot)

            # Setup the database helper
            self.MoonrakerDatabase = MoonrakerDatabase(printerId, pluginVersionStr)

            # Setup app storage
            moonrakerAppStorage = MoonrakerAppStorage(self.MoonrakerDatabase)
            AppStorageHelper.Init(moonrakerAppStorage)

            # Setup the credential manager.
            MoonrakerCredentialManager.Init(moonrakerConfigFilePath, isObserverMode)

            # Setup the http requester. We default to port 80 and assume the frontend can be found there.
            # TODO - parse nginx to see what front ends exist and make them switchable
            # TODO - detect HTTPS port if 80 is not bound.
            frontendPort = self.Config.GetInt(Config.RelaySection, Config.RelayFrontEndPortKey, 80)
            Sentry.Info("Host", "Setting up relay with frontend port %s" % str(frontendPort))
            OctoHttpRequest.SetLocalHttpProxyPort(frontendPort)
            OctoHttpRequest.SetLocalHttpProxyIsHttps(False)
            OctoHttpRequest.SetLocalOctoPrintPort(frontendPort)

            # If we are in observer mode, we need to update the local address to be the other local remote.
            if isObserverMode:
                (ipOrHostnameStr, portStr) = ObserverConfigFile.Get().TryToGetIpAndPortStr()
                if ipOrHostnameStr is None or portStr is None:
                    Sentry.Error("Host", "We are in observer mode but we can't get the ip and port from the observer config file.")
                    raise Exception("Failed to read observer config file.")
                OctoHttpRequest.SetLocalHostAddress(ipOrHostnameStr)
                # TODO - this could be an host name, not an IP. That might be a problem?
                LocalIpHelper.SetLocalIpOverride(ipOrHostnameStr)

            # Setup the snapshot helper
            self.MoonrakerWebcamHelper = MoonrakerWebcamHelper(self.Config)
            WebcamHelper.Init(self.MoonrakerWebcamHelper, localStorageDir)

            # Setup our smart pause helper
            SmartPause.Init()

            # When everything is setup, start the moonraker client object.
            # This also creates the Notifications Handler and Gadget objects.
            # This doesn't start the moon raker connection, we don't do that until OE connects.
            MoonrakerClient.Init(isObserverMode, moonrakerConfigFilePath, observerConfigFilePath, printerId, self, pluginVersionStr, self.MoonrakerDatabase)

            # Init our file meta data cache helper
            FileMetadataCache.Init(MoonrakerClient.Get())

            # If we have a local dev server, set it in the notification handler.
            if DevLocalServerAddress_CanBeNone is not None:
                MoonrakerClient.Get().GetNotificationHandler().SetServerProtocolAndDomain("http://"+DevLocalServerAddress_CanBeNone)
                MoonrakerClient.Get().GetNotificationHandler().SetGadgetServerProtocolAndDomain("http://"+DevLocalServerAddress_CanBeNone)

            # Setup the moonraker config handler
            MoonrakerWebRequestResponseHandler.Init()

            # Setup the moonraker API router
            # MoonrakerApiRouter.Init(self.Logger)

            # Now start the main runner!
            MoonrakerClient.Get().RunBlocking()
        except Exception as e:
            Sentry.Exception("!! Exception thrown out of main host run function.", e)

        # Allow the loggers to flush before we exit
        try:
            Sentry.Info("Host", "###########################")
            Sentry.Info("Host", "#### OctoApp Exiting ######")
            Sentry.Info("Host", "###########################")
            logging.shutdown()
        except Exception as e:
            print("Exception in logging.shutdown "+str(e))


    # Ensures all required values are setup and valid before starting.
    def DoFirstTimeSetupIfNeeded(self, klipperConfigDir, serviceName):
        # Try to get the printer id from the config.
        isFirstRun = False
        printerId = self.GetPrinterId()
        if HostCommon.IsPrinterIdValid(printerId) is False:
            if printerId is None:
                Sentry.Info("Host", "No printer id was found, generating one now!")
                # If there is no printer id, we consider this the first run.
                isFirstRun = True
            else:
                Sentry.Info("Host", "An invalid printer id was found [%s], regenerating!" % str(printerId))

            # Make a new, valid, key
            printerId = HostCommon.GeneratePrinterId()

            # Save it
            self.Secrets.SetPrinterId(printerId)
            Sentry.Info("Host", "New printer id created: %s" % printerId)

        # If this is the first run, do other stuff as well.
        if isFirstRun:
            SystemConfigManager.EnsureAllowedServicesFile(klipperConfigDir, serviceName)


    # Returns None if no printer id has been set.
    def GetPrinterId(self):
        return self.Secrets.GetPrinterId()


    # Returns None if no private id has been set.
    def GetPrivateKey(self):
        return self.Secrets.GetPrivateKey()


    # Tries to load a dev config option as a string.
    # If not found or it fails, this return None
    def GetDevConfigStr(self, devConfig, value):
        if devConfig is None:
            return None
        if value in devConfig:
            v = devConfig[value]
            if v is not None and len(v) > 0 and v != "None":
                return v
        return None


    # #
    # # StatusChangeHandler Interface - Called by the OctoApp logic when the server connection has been established.
    # #
    # def OnPrimaryConnectionEstablished(self, octoKey, connectedAccounts):
    #     Sentry.Info("Host", "Primary Connection To OctoApp Established - We Are Ready To Go!")

    #     # Check if this printer is unlinked, if so add a message to the log to help the user setup the printer if desired.
    #     # This would be if the skipped the printer link or missed it in the setup script.
    #     if connectedAccounts is None or len(connectedAccounts) == 0:
    #         Sentry.Warn("Host", "")
    #         Sentry.Warn("Host", "")
    #         Sentry.Warn("Host", "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    #         Sentry.Warn("Host", "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    #         Sentry.Warn("Host", "          This Plugin Isn't Connected To OctoApp!          ")
    #         Sentry.Warn("Host", " Use the following link to finish the setup and get remote access:")
    #         Sentry.Warn("Host", " %s", HostCommon.GetAddPrinterUrl(self.GetPrinterId(), False))
    #         Sentry.Warn("Host", "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    #         Sentry.Warn("Host", "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    #         Sentry.Warn("Host", "")
    #         Sentry.Warn("Host", "")p

    #     # Now that we are connected, start the moonraker client.
    #     # We do this after the connection incase it needs to send any notifications or messages when starting.
    #     MoonrakerClient.Get().StartRunningIfNotAlready(octoKey)


    #
    # StatusChangeHandler Interface - Called by the OctoApp logic when a plugin update is required for this client.
    #
    def OnPluginUpdateRequired(self):
        Sentry.Error("Host", "!!! A Plugin Update Is Required -- If This Plugin Isn't Updated It Might Stop Working !!!")
        Sentry.Error("Host", "!!! Please use the update manager in Mainsail of Fluidd to update this plugin         !!!")


    #
    # MoonrakerClient ConnectionStatusHandler Interface - Called by the MoonrakerClient every time the moonraker websocket is open and authed - BUT possibly not connected to klippy.
    # At this point it's ok to query things in moonraker like db items, webcam info, and such. But API calls that have to do with the physical printer will fail, since klippy might not be ready yet.
    #
    def OnMoonrakerWsOpenAndAuthed(self):

        # Kick off the webcam settings helper, to ensure it pulls fresh settings if desired.
        self.MoonrakerWebcamHelper.KickOffWebcamSettingsUpdate()

        # Also allow the database logic to ensure our public keys exist and are updated.
        self.MoonrakerDatabase.EnsureOctoAppDatabaseEntry()

    #
    # MoonrakerClient ConnectionStatusHandler Interface - Called by the MoonrakerClient when it gets a message that the webcam settings have changed.
    #
    def OnWebcamSettingsChanged(self):
        # Set the force flag to true, since we know the settings just changed.
        self.MoonrakerWebcamHelper.KickOffWebcamSettingsUpdate(True)

    #
    # MoonrakerClient ConnectionStatusHandler Interface - Called by the MoonrakerClient when the moonraker connection has been established and klippy is fully ready to use.
    #
    def OnMoonrakerClientConnected(self):
        pass
