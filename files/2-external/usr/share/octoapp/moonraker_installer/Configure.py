import os
import threading
import socket

from octoapp.websocketimpl import Client

from .Util import Util
from .Paths import Paths
from .Logging import Logger
from .Context import Context
from .Context import OsTypes
from .ObserverConfigFile import ObserverConfigFile

# The goal of this class is the take the context object from the Discovery Gen2 phase to the Phase 3.
class Configure:

    # This is the common service prefix (or word used in the file name) we use for all of our service file names.
    # This MUST be used for all instances running on this device, both local plugins and companions.
    # This also MUST NOT CHANGE, as it's used by the Updater logic to find all of the locally running services.
    c_ServiceCommonName = "octoapp"

    def Run(self, context:Context):

        Logger.Header("Starting configuration...")

        serviceSuffixStr = ""
        if context.IsObserverSetup:
            # For observers, we use the observer id, with a unique prefix to separate it from any possible local moonraker installs
            # Note that the moonraker service suffix can be numbers or letters, so we use the same rules.
            serviceSuffixStr = f"-companion{context.ObserverInstanceId}"
        elif context.OsType == OsTypes.SonicPad:
            # For Sonic Pad, we know the format of the service file is a bit different.
            # For the SonicIt is moonraker_service or moonraker_service.<number>
            if "." in context.MoonrakerServiceFileName:
                serviceSuffixStr = context.MoonrakerServiceFileName.split(".")[1]
        elif context.OsType == OsTypes.K1:
            # For the k1, there's only every one moonraker instance, so this isn't needed.
            pass
        else:
            # Now we need to figure out the instance suffix we need to use.
            # To keep with Kiauh style installs, each moonraker instances will be named moonraker-<number or name>.service.
            # If there is only one moonraker instance, the name is moonraker.service.
            # Default to empty string, which means there's no suffix and only one instance.
            serviceFileNameNoExtension = context.MoonrakerServiceFileName.split('.')[0]
            if '-' in serviceFileNameNoExtension:
                moonrakerServiceSuffix = serviceFileNameNoExtension.split('-')
                serviceSuffixStr = "-" + moonrakerServiceSuffix[1]
        Logger.Debug(f"Moonraker Service File Name: {context.MoonrakerServiceFileName}, Suffix: '{serviceSuffixStr}'")

        if context.IsObserverSetup:
            # For observer setups, there is no local moonraker config file, so things are setup differently.
            # The plugin data folder, which is normally the root printer data folder for that instance, becomes our per instance
            # observer folder.
            context.PrinterDataFolder = context.ObserverDataPath
            # We mock the same layout as the moonraker folder structure, to keep things common.
            context.PrinterDataConfigFolder = ObserverConfigFile.GetConfigFolderPathFromDataPath(context.PrinterDataFolder)
            # Set the path to where the observer config file will be.
            # This path is shared by the plugin logic, so it can't change!
            context.ObserverConfigFilePath = ObserverConfigFile.GetConfigFilePathFromDataPath(context.PrinterDataFolder)
            # Make a logs folder, so it's found bellow
            Util.EnsureDirExists(os.path.join(context.PrinterDataFolder, "logs"), context, True)
        elif context.OsType == OsTypes.SonicPad:
            # ONLY FOR THE SONIC PAD, we know the folder setup is different.
            # The user data folder will have /mnt/UDISK/printer_config<number> where the config files are and /mnt/UDISK/printer_logs<number> for logs.
            # Use the normal folder for the config files.
            context.PrinterDataConfigFolder = Util.GetParentDirectory(context.MoonrakerConfigFilePath)

            # There really is no printer data folder, so make one that's unique per instance.
            # So based on the config folder, go to the root of it, and them make the folder "octoapp_data"
            context.PrinterDataFolder = os.path.join(Util.GetParentDirectory(context.PrinterDataConfigFolder), f"octoapp_data{serviceSuffixStr}")
            Util.EnsureDirExists(context.PrinterDataFolder, context, True)
        else:
            # For now we assume the folder structure is the standard Klipper folder config,
            # thus the full moonraker config path will be .../something_data/config/moonraker.conf
            # Based on that, we will define the config folder and the printer data root folder.
            # Note that the K1 uses this standard folder layout as well.
            context.PrinterDataConfigFolder = Util.GetParentDirectory(context.MoonrakerConfigFilePath)
            context.PrinterDataFolder = Util.GetParentDirectory(context.PrinterDataConfigFolder)
            Logger.Debug("Printer data folder: "+context.PrinterDataFolder)


        # This is the name of our service we create. If the port is the default port, use the default name.
        # Otherwise, add the port to keep services unique.
        if context.OsType == OsTypes.SonicPad:
            # For Sonic Pad, since the service is setup differently, follow the conventions of it.
            # Both the service name and the service file name must match.
            # The format is <name>_service<number>
            # NOTE! For the Update class to work, the name must start with Configure.c_ServiceCommonNamePrefix
            context.ServiceName = Configure.c_ServiceCommonName + "_service"
            if len(serviceSuffixStr) != 0:
                context.ServiceName= context.ServiceName + "." + serviceSuffixStr
            context.ServiceFilePath = os.path.join(Paths.CrealityOsServiceFilePath, context.ServiceName)
        elif context.OsType == OsTypes.K1:
            # For the k1, there's only ever one moonraker and we know the exact service naming convention.
            # Note we use 66 to ensure we start after moonraker.
            context.ServiceName = f"S66{Configure.c_ServiceCommonName}_service"
            context.ServiceFilePath = os.path.join(Paths.CrealityOsServiceFilePath, context.ServiceName)
        else:
            # For normal setups, use the convention that Klipper users
            # NOTE! For the Update class to work, the name must start with Configure.c_ServiceCommonNamePrefix
            context.ServiceName = Configure.c_ServiceCommonName + serviceSuffixStr
            context.ServiceFilePath = os.path.join(Paths.SystemdServiceFilePath, context.ServiceName+".service")

        # Since the moonraker config folder is unique to the moonraker instance, we will put our storage in it.
        # This also prevents the user from messing with it accidentally.
        context.LocalFileStorageFolder = os.path.join(context.PrinterDataFolder, "octoapp-store")

        # Ensure the storage folder exists and is owned by the correct user.
        Util.EnsureDirExists(context.LocalFileStorageFolder, context, True)

        # There's not a great way to find the log path from the config file, since the only place it's located is in the systemd file.
        context.PrinterDataLogsFolder = None

        # First, we will see if we can find a named folder relative to this folder.
        context.PrinterDataLogsFolder = os.path.join(context.PrinterDataFolder, "logs")
        if os.path.exists(context.PrinterDataLogsFolder) is False:
            # Try an older path
            context.PrinterDataLogsFolder = os.path.join(context.PrinterDataFolder, "klipper_logs")
            if os.path.exists(context.PrinterDataLogsFolder) is False:
                # Try the path Creality OS uses, something like /mnt/UDISK/printer_logs<number>
                context.PrinterDataLogsFolder = os.path.join(Util.GetParentDirectory(context.PrinterDataConfigFolder), f"printer_logs{serviceSuffixStr}")
                if os.path.exists(context.PrinterDataLogsFolder) is False:
                    # Failed, make a folder in the printer data root.
                    context.PrinterDataLogsFolder = os.path.join(context.PrinterDataFolder, "octoapp-logs")
                    # Create the folder and force the permissions so our service can write to it.
                    Util.EnsureDirExists(context.PrinterDataLogsFolder, context, True)

        # Finally, if this is an observer setup, we need the user to tell us where moonraker is installed
        # and need to write the observer config file.
        if context.IsObserverSetup:
            self._EnsureObserverConfigure(context)

        # Report
        Logger.Info(f'Configured. Service: {context.ServiceName}, Path: {context.ServiceFilePath}, LocalStorage: {context.LocalFileStorageFolder}, Config Dir: {context.PrinterDataConfigFolder}, Logs: {context.PrinterDataLogsFolder}')


    def _EnsureObserverConfigure(self, context:Context):
        Logger.Debug("Running observer ensure config logic.")

        # See if there's a valid config already.
        ip, port = ObserverConfigFile.TryToParseConfig(context.ObserverConfigFilePath)
        if ip is not None and port is not None:
            # Check if we can still connect. This can happen if the IP address changes, the user might need to setup the
            # printer again.
            Logger.Info(f"Existing observer config file found. IP: {ip}:{port}")
            Logger.Info("Checking if we can connect to Klipper...")
            success, _ = self._CheckForMoonraker(ip, port, 10.0)
            if success:
                Logger.Info("Successfully connected to Klipper!")
                return
            else:
                # Let the user keep this connection setup, or try to set it up again.
                Logger.Blank()
                Logger.Warn(f"No Klipper connection found at {ip}:{port}.")
                if Util.AskYesOrNoQuestion("Do you want to setup the Klipper connection again for this OctoApp companion instance?") is False:
                    Logger.Info(f"Keeping the existing Klipper connection setup. {ip}:{port}")
                    return

        ip, port = self._SetupNewMoonrakerConnection()
        if ObserverConfigFile.WriteIpAndPort(context, context.ObserverConfigFilePath, ip, port) is False:
            raise Exception("Failed to write observer config.")
        Logger.Blank()
        Logger.Header("Klipper connection successful!")
        Logger.Blank()

    # Helps the user setup a moonraker connection via auto scanning or manual setup.
    # Returns (ip:str, port:str)
    def _SetupNewMoonrakerConnection(self):
        Logger.Blank()
        Logger.Blank()
        Logger.Blank()
        Logger.Header("##################################")
        Logger.Header("     Klipper Companion Setup")
        Logger.Header("##################################")
        Logger.Blank()
        Logger.Info("For OctoApp Companion to work, it needs to know how to connect to the Klipper device on your network.")
        Logger.Info("If you have any trouble, we are happy to help! Contact us at hello@octoapp.com")
        Logger.Blank()
        Logger.Info("Searching for local Klipper printers... please wait... (about 5 seconds)")
        foundIps = self._ScanForMoonrakerInstances()
        if len(foundIps) > 0:
            # Sort them so they present better.
            foundIps = sorted(foundIps)
            Logger.Blank()
            Logger.Info("Klipper was found on the following IP addresses:")
            count = 0
            for ip in foundIps:
                count += 1
                Logger.Info(f"  {count}) {ip}:7125")
            Logger.Blank()
            while True:
                response = input("Enter the number next to the Klipper instance you want to use or enter `m` to manually setup the connection: ")
                response = response.lower().strip()
                if response == "m":
                    # Break to fall through to the manual setup.
                    break
                try:
                    # Parse the input and -1 it, so it aligns with the array length.
                    tempInt = int(response.lower().strip()) - 1
                    if tempInt >= 0 and tempInt < len(foundIps):
                        return (foundIps[tempInt], "7125")
                except Exception as _:
                    Logger.Warn("Invalid input, try again.")
        else:
            Logger.Info("No local Klipper devices could be automatically found.")

        # Do the manual setup process.
        ipOrHostname = ""
        port = "7125"
        while True:
            try:
                Logger.Blank()
                Logger.Blank()
                Logger.Info("Please enter the IP address or Hostname of the device running Klipper/Moonraker/Mainsail/Fluidd.")
                Logger.Info("The IP address might look something like `192.168.1.5` or a Hostname might look like `klipper.local`")
                ipOrHostname = input("Enter the IP or Hostname: ")
                # Clean up what the user entered.
                ipOrHostname = ipOrHostname.lower().strip()
                if ipOrHostname.find("://") != -1:
                    ipOrHostname = ipOrHostname[ipOrHostname.find("://")+3:]
                if ipOrHostname.find("/") != -1:
                    ipOrHostname = ipOrHostname[:ipOrHostname.find("/")]

                Logger.Blank()
                Logger.Info("Please enter the port Moonraker is running on.")
                Logger.Info("If you don't know the port or want to use the default port (7125), press enter.")
                port = input("Enter Moonraker Port: ")
                if len(port) == 0:
                    port = "7125"

                Logger.Blank()
                Logger.Info(f"Trying to connect to Moonraker via {ipOrHostname}:{port} ...")
                success, exception = self._CheckForMoonraker(ipOrHostname, port, 10.0)

                # Handle the result.
                if success:
                    return (ipOrHostname, port)
                else:
                    Logger.Blank()
                    Logger.Blank()
                    if exception is not None:
                        Logger.Error("Klipper connection failed.")
                    else:
                        Logger.Error("Klipper connection timed out.")
                    Logger.Warn("Make sure the device is powered on, has an network connection, and the ip is correct.")
                    if exception is not None:
                        Logger.Warn(f"Error {str(exception)}")
            except Exception as e:
                Logger.Warn("Failed to setup Klipper, try again. "+str(e))


    # Given an ip or hostname and port, this will try to detect if there's a moonraker instance.
    # Returns (success:, exception | None)
    def _CheckForMoonraker(self, ip:str, port:str, timeoutSec:float = 5.0):
        doneEvent = threading.Event()
        lock = threading.Lock()
        result = {}

        # Create the URL
        url = f"ws://{ip}:{port}/websocket"

        # Setup the callback functions
        def OnOpened(ws):
            Logger.Debug(f"Test [{url}] - WS Opened")
        def OnMsg(ws, msg):
            with lock:
                if "success" in result:
                    return
                try:
                    # Try to see if the message looks like one of the first moonraker messages.
                    msgStr = msg.decode('utf-8')
                    Logger.Debug(f"Test [{url}] - WS message `{msgStr}`")
                    if "moonraker" in msgStr.lower():
                        Logger.Debug(f"Test [{url}] - Found Moonraker message, success!")
                        result["success"] = True
                        doneEvent.set()
                except Exception:
                    pass
        def OnClosed(ws):
            Logger.Debug(f"Test [{url}] - Closed")
            doneEvent.set()
        def OnError(ws, exception):
            Logger.Debug(f"Test [{url}] - Error: {str(exception)}")
            with lock:
                result["exception"] = exception
            doneEvent.set()

        # Create the websocket
        Logger.Debug(f"Checking for moonraker using the address: `{url}`")
        ws = Client(url, onWsOpen=OnOpened, onWsMsg=OnMsg, onWsError=OnError, onWsClose=OnClosed)
        ws.RunAsync()

        # Wait for the event or a timeout.
        doneEvent.wait(timeoutSec)

        # Get the results before we close.
        capturedSuccess = False
        capturedEx = None
        with lock:
            if result.get("success", None) is not None:
                capturedSuccess = result["success"]
            if result.get("exception", None) is not None:
                capturedEx = result["exception"]

        # Ensure the ws is closed
        try:
            ws.Close()
        except Exception:
            pass

        return (capturedSuccess, capturedEx)

    # Scans the subnet for Moonraker instances.
    # Returns a list of IPs where moonraker was found.
    def _ScanForMoonrakerInstances(self):
        foundIps = []
        try:
            localIp = self._TryToGetLocalIp()
            if localIp is None or len(localIp) == 0:
                Logger.Debug("Failed to get local IP")
                return foundIps
            Logger.Debug(f"Local IP found as: {localIp}")
            if ":" in localIp:
                Logger.Info("IPv6 addresses aren't supported for local discovery.")
                return foundIps
            lastDot = localIp.rfind(".")
            if lastDot == -1:
                Logger.Info("Failed to find last dot in local IP?")
                return foundIps
            ipPrefix = localIp[:lastDot+1]

            counter = 0
            doneThreads = [0]
            totalThreads = 255
            threadLock = threading.Lock()
            doneEvent = threading.Event()
            while counter <= totalThreads:
                fullIp = ipPrefix + str(counter)
                def threadFunc(ip):
                    try:
                        success, _ = self._CheckForMoonraker(ip, "7125", 5.0)
                        with threadLock:
                            if success:
                                foundIps.append(ip)
                            doneThreads[0] += 1
                            if doneThreads[0] == totalThreads:
                                doneEvent.set()
                    except Exception as e:
                        Logger.Error(f"Moonraker scan failed for {ip} "+str(e))
                t = threading.Thread(target=threadFunc, args=[fullIp])
                t.start()
                counter += 1
            doneEvent.wait()
            return foundIps
        except Exception as e:
            Logger.Error("Failed to scan for Moonraker instances. "+str(e))
        return foundIps


    def _TryToGetLocalIp(self) -> str:
        # Find the local IP. Works on Windows and Linux. Always gets the correct routable IP.
        # https://stackoverflow.com/a/28950776
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = None
        try:
            # doesn't even have to be reachable
            s.connect(('1.1.1.1', 1))
            ip = s.getsockname()[0]
        except Exception:
            pass
        finally:
            s.close()
        return ip
