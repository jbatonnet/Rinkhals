import os
from enum import Enum
import configparser
import requests

from moonraker_octoapp.config import Config

from .Logging import Logger
from .Context import Context
from .ObserverConfigFile import ObserverConfigFile
from .Util import Util

# Frontends that are known.
class KnownFrontends(Enum):
    Unknown  = 1
    Mainsail = 2
    Fluidd   = 3
    Creality = 4 # This is Creality's K1 default web interface (not nearly as good as the others)

    # Makes to str() cast not to include the class name.
    def __str__(self):
        return self.name

# A helper class.
class DiscoveryPair:
    def __init__(self, port:int, frontend:KnownFrontends) -> None:
        self.Port:int = port
        self.Frontend = frontend


# A Class to help with detecting and setting up a frontend.
class Frontend:

    # If called, this will walk the user though picking a frontend for the targeted device (local or remote for companion).
    # The frontend will be saved into the OE config, so this should be done before the service starts, if this is a first time run.
    def DoFrontendSetup(self, context:Context):
        Logger.Header("Starting Web Interface Setup")

        # Try to get the existing configured port.
        (currentPort, frontendHint_CanBeNone) = self._TryToReadCurrentFrontendSetup(context)
        if currentPort is not None:
            # There is already a config with a port setup.
            # Ask if the user wants to keep the current setup.
            Logger.Blank()
            Logger.Info("A web interface is already setup:")
            msg = ""
            if frontendHint_CanBeNone is not None and frontendHint_CanBeNone.lower() != str(KnownFrontends.Unknown):
                msg += frontendHint_CanBeNone
            else:
                msg += "An unknown web interface"
            msg += f" on port {currentPort}"
            Logger.Header(msg)
            Logger.Blank()
            if Util.AskYesOrNoQuestion("Do you want to keep this setup?"):
                # Keep the current setup
                return

        # Get a frontend port from the user.
        (portInt, frontendHint_CanBeNone) = self._GetDesiredFrontend(context)

        # We got a port, save it.
        self._WriteFrontendSetup(context, str(portInt), frontendHint_CanBeNone)


    # Returns the (port (int), frontendNameHint:str or None) of the frontend the user wants to use.
    def _GetDesiredFrontend(self, context:Context):
        # Find the target. If this is a local install, the target is local.
        # Otherwise, it's whatever the companion target is.
        targetIpOrHostname = "127.0.0.1"
        if context.IsObserverSetup:
            (ip, _) = ObserverConfigFile.TryToParseConfig(context.ObserverConfigFilePath)
            if ip is None or len(ip) == 0:
                raise Exception("Frontend setup failed to find companion ip from companion config file.")
            targetIpOrHostname = ip

        # Try to discover any known frontends
        foundFrontends = self._DiscoverKnownFrontends(targetIpOrHostname)

        # If we found something, ask the user if they want to use one.
        if len(foundFrontends) > 0:
            Logger.Blank()
            Logger.Info("The following web interfaces were automatically discovered:")
            count = 0
            # List them in the order we found them, since we order the port list in by priority.
            for f in foundFrontends:
                count += 1
                Logger.Info(f"  {count}) {str(f.Frontend).ljust(8)} - Port {str(f.Port)}")
            Logger.Blank()
            while True:
                response = input("Enter the number next to the web interface you would like to use, or enter `m` to manually setup the web interface: ")
                response = response.lower().strip()
                if response == "m":
                    # Break to fall through to the manual setup.
                    break
                try:
                    # Parse the input and -1 it, so it aligns with the array length.
                    tempInt = int(response.lower().strip()) - 1
                    if tempInt >= 0 and tempInt < len(foundFrontends):
                        item = foundFrontends[tempInt]
                        return (item.Port, str(item.Frontend))
                except Exception as _:
                    Logger.Warn("Invalid input, try again.")
        else:
            Logger.Info("No web interfaces could be detected.")


        # If we are here, the user selected m to do a manual frontend setup.
        firstTry = True
        while True:
            try:
                Logger.Blank()
                Logger.Blank()
                Logger.Blank()
                Logger.Info("Enter the port number or web address you use to access your printer.")
                Logger.Info("   Examples of port could be something like:")
                Logger.Info("        80")
                Logger.Info("        4408")
                Logger.Info("   Examples web address could be something like:")
                Logger.Info("        192.168.1.15:4409")
                Logger.Info("        https://192.168.1.15:4409/")
                Logger.Info("        myprinter.local:4409")
                Logger.Blank()
                if firstTry is False:
                    Logger.Info("If you're having trouble, contact us at hello2@octoapp.eu")
                    Logger.Blank()
                firstTry = False
                response = input("Please enter the port or web address: ")
                response = response.lower().strip()
                ogResponse = response


                # Parse the response. Start assuming a full web address, and strip down.
                #  Inputs could be:
                #     https://127.0.0.1/
                #     klipper.local:80
                #     127.0.0.1
                #     ...

                # First remote any protocol
                searchStr = "://"
                if response.find(searchStr) != -1:
                    response = response[response.find(searchStr) + len(searchStr):]
                # Next, remove anything before the next :, which would be the domain or IP
                if response.find(":") != -1:
                    response = response[response.find(":")+1:]
                else:
                    # If there's no : it means
                    #   This string is only a port
                    #   The string is URL with no port.
                    # If it's a URL, it must have a . for the domain
                    if response.find(".") != -1 or response.find("localhost") != -1:
                        # This is a url wit no port.
                        if ogResponse.find("https") != -1:
                            response = "443"
                        else:
                            response = "80"
                    else:
                        # The input is just a port.
                        pass
                # Finally, remove any trailing path stuff
                if response.find("/") != -1:
                    response = response[:response.find("/")]

                # Ensure it's an int.
                try:
                    int(response)
                except Exception as e:
                    Logger.Debug(f"Error: {str(e)}")
                    Logger.Warn(f"Input of `{response}` isn't a valid port, it must be a number. Please try again.")
                    continue

                # Test to see if we can find a frontend.
                Logger.Debug(f"Final port response `{response}`")
                (isValid, _, frontend) = self.CheckIfValidFrontend(targetIpOrHostname, response)

                # Report the result.
                Logger.Blank()
                if isValid:
                    if frontend != KnownFrontends.Unknown:
                        Logger.Info(f"We detected {str(frontend)} running on the port or web address you entered.")
                    else:
                        Logger.Info("We detected a web interface running on the port or web address you entered.")
                else:
                    Logger.Warn(f"We DIDN'T detect a web interface running on port {response}, which you entered.")

                # Ask the user, let them return it even if it's invalid.
                if Util.AskYesOrNoQuestion("Is this the web interface you want to use?"):
                    if frontend != KnownFrontends.Unknown:
                        return (int(response), str(frontend))
                    else:
                        return (int(response), None)

            except Exception as e:
                Logger.Debug(f"Manual frontend error {str(e)}")
                Logger.Warn("Error, please try again.")


    # If we can find a known frontend, this will return it.
    # Returns a list of DiscoveryPair, if any are found.
    def _DiscoverKnownFrontends(self, ipOrHostname:str):
        # We can't scan all ports, it will take to long. Instead we will scan known ports used by known common setups.
        # Note these ports are in order of importance, where ports near the top are more likely to be what the user wants.
        knownFrontendPorts = [
            4408, # On the K1, this is the Fluidd port. (This is set by the install script from GitHub Guilouz/Creality-K1-and-K1-Max)
            4409, # On the K1, this is the mainsail port. (This is set by the install script from GitHub Guilouz/Creality-K1-and-K1-Max)
            80,   # On most devices, this is the port the frontend is on. But note on the K1, this is Creality's own special frontend, most users don't want.
            81,   # A common port for an secondary frontend to run on, like Fluidd or Mainsail.
            443,  # Not ideal, but https might be here.
            8819  # Sonic Pad Mainsail port.
        ]

        # Try to find what we can.
        foundFrontends = []
        for port in knownFrontendPorts:
            (isValid, _, frontend) = self.CheckIfValidFrontend(ipOrHostname, str(port))
            if isValid:
                foundFrontends.append(DiscoveryPair(port, frontend))

        # Return anything we got.
        return foundFrontends


    # Checks if the hostname and ip are a valid http endpoint.
    # Returns (isValid:bool, isHttps:bool, frontendName:KnownFrontends)
    def CheckIfValidFrontend(self, ipOrHostname:str, portStr:str, timeoutSec:float = 2.0):
        try:
            # Don't allow redirects, so we can detect https upgrades redirects.
            url = f"http://{ipOrHostname}:{portStr}"
            result = requests.get(url=url, timeout=timeoutSec, allow_redirects=False)

            # Handle error codes.
            if result.status_code == 301 or  result.status_code == 308 or result.status_code == 307:
                location = None
                if "location" in result.headers:
                    location = result.headers["location"]
                    Logger.Warn(f"{url} resulted in a redirect request to {location}")
                raise Exception(f"Redirect to {location} requested.")
            if result.status_code != 200:
                raise Exception(f"Status code was not 200. Code: {result.status_code}")

            # We have a valid http response, try to figure out the frontend if possible.
            # If we fail, we still want to return valid.
            frontend = KnownFrontends.Unknown
            try:
                htmlLower = result.text.lower()
                if "mainsail" in htmlLower:
                    frontend = KnownFrontends.Mainsail
                elif "fluidd" in htmlLower:
                    frontend = KnownFrontends.Fluidd
                elif "creality" in htmlLower:
                    frontend = KnownFrontends.Creality
                else:
                    Logger.Debug(f"Unknown frontend type. html: {result.text}")
            except Exception as e:
                Logger.Debug(f"Failed to figure out http frontend. {e}")

            # We got a valid http response, so we pass
            return (True, False, frontend)

        except Exception as e:
            Logger.Debug(f"Frontend check failed. {ipOrHostname}:{portStr} {str(e)}")
        # Return failed.
        return (False, False, KnownFrontends.Unknown)


    # Returns the current configured port and frontend name hint.
    # (portStr:str, frontendHint:str (can be None))
    # Returns (None, None) if the file can't be found.
    def _TryToReadCurrentFrontendSetup(self, context:Context):
        filePath = self.GetOctoAppServiceConfigFilePath(context)
        # Don't try catch, let this throw if there's a problem reading the config,
        # That would be bad.
        if os.path.exists(filePath) is False:
            return (None, None)

        config = configparser.ConfigParser()
        config.read(filePath)
        if config.has_section(Config.RelaySection) is False:
            return (None, None)
        if Config.RelayFrontEndPortKey not in config[Config.RelaySection]:
            return (None, None)
        portStr = config[Config.RelaySection][Config.RelayFrontEndPortKey]
        frontendHint = None
        if Config.RelayFrontEndTypeHintKey in config[Config.RelaySection]:
            frontendHint = config[Config.RelaySection][Config.RelayFrontEndTypeHintKey]
        return (portStr, frontendHint)


    # Writes the current frontend setup into the main OE service config
    # We use the main config file, since it's already there, and we don't want to have overlapping settings in different places.
    # If the service hasn't ran yet, the file won't exist, in which case we will create it.
    def _WriteFrontendSetup(self, context:Context, portStr:str, frontendHint_CanBeNone:str):
        filePath = self.GetOctoAppServiceConfigFilePath(context)

        # Read the current config if there is one, this is important.
        config = configparser.ConfigParser()
        if os.path.exists(filePath):
            config.read(filePath)
        # Add the vars
        if config.has_section(Config.RelaySection) is False:
            config.add_section(Config.RelaySection)
        config[Config.RelaySection][Config.RelayFrontEndPortKey] = portStr
        if frontendHint_CanBeNone is None:
            if Config.RelayFrontEndTypeHintKey in config[Config.RelaySection]:
                del config[Config.RelaySection][Config.RelayFrontEndTypeHintKey]
        else:
            config[Config.RelaySection][Config.RelayFrontEndTypeHintKey] = frontendHint_CanBeNone
        # Write the file back or make a new one.
        with open(filePath, 'w', encoding="utf-8") as f:
            config.write(f)

        # Important! If we were the first ones to create this file, it will be owned by root and the service
        # won't have permission to open it. Thus we need to make sure it's owned correctly when we are done.
        Util.SetFileOwnerRecursive(filePath, context.UserName)


    def GetOctoAppServiceConfigFilePath(self, context:Context) -> str:
        # Don't do the join if there is no path, otherwise the result will just be a file name.
        if context.PrinterDataConfigFolder is None or len(context.PrinterDataConfigFolder) == 0:
            return None
        return os.path.join(context.PrinterDataConfigFolder, Config.ConfigFileName)
