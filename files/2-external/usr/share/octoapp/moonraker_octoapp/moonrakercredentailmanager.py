import os
import socket
import random
import json
import logging
import time

import configparser

from octoapp.sentry import Sentry

# A class that handles trying to get user credentials from Moonraker if needed.
#
# If the user has set the force_logins in the [authorization] block of the moonraker config AND they have created a user (which can be done in Fluidd)
# moonraker will require credentials to use the websocket, regardless if you're local host or not. Mainsail is also looking to add this logic soon.
#
# Moonraker exposes a unix socket file that can be used to access the server in the same way as the websocket, but it never needs auth.
# We could use that socket for all of our needs, but since we already have the WS implementation, we don't. But, using this socket, we can access the
# moonraker APIs and thus we can pull the API key, which is global.
#
# Info on the moonraker unix socket
# https://moonraker.readthedocs.io/en/latest/web_api/#unix-socket-connection
#
class MoonrakerCredentialManager:

    c_MoonrakerUnixSocketFileName = "moonraker.sock"
    c_MoonrakerUnixSocketFileNameWithCommsFolder = "comms/moonraker.sock"

    # The static instance.
    _Instance = None


    @staticmethod
    def Init(moonrakerConfigFilePath:str, isObserverMode:bool):
        MoonrakerCredentialManager._Instance = MoonrakerCredentialManager(moonrakerConfigFilePath, isObserverMode)


    @staticmethod
    def Get():
        return MoonrakerCredentialManager._Instance


    def __init__(self, moonrakerConfigFilePath:str, isObserverMode:bool):
        self.MoonrakerConfigFilePath = moonrakerConfigFilePath
        self.IsObserverMode = isObserverMode


    def TryToGetApiKey(self) -> str or None:
        # If this is an observer plugin, we dont' have the moonraker config file nor can we access the UNIX socket.
        if self.IsObserverMode:
            Sentry.Info("Credetials", "OctoApp Companion Plugins dont' support Moonraker setups with auth.")
            return None

        # First, we need to find the unix socket to connect to
        moonrakerSocketFilePath = self._TryToFindUnixSocket()
        if moonrakerSocketFilePath is None:
            Sentry.Warn("Credetials", "No moonraker unix socket file could be found.")
            return None

        try:
            # Try to open the socket.
            # pylint: disable=no-member # Only exists on linux
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(moonrakerSocketFilePath)

            # Create the db request query.
            msgId = random.randint(100000, 99999999)
            obj = {
                "jsonrpc": "2.0",
                "method": "access.get_api_key",
                "id": msgId
            }
            jsonStr = json.dumps(obj, default=str)
            # Add the End Of Text ascii value of 3 to the string to indicate the end of message.
            jsonStr += b'\x03'.decode()

            # Send it on the socket.
            sock.sendall(jsonStr.encode(encoding="utf-8"))

            # Moonraker sends state messages along with responses, so we need to eat them until we find what we need.
            startTime = time.time()
            msgCount = 0
            while True:
                jsonMsg = self._ReadSingleJsonObject(sock)
                if jsonMsg is None:
                    return None

                msgCount += 1
                jsonRpcResponse = json.loads(jsonMsg)
                # Only messages with the ID field are responses, so we don't care about the others.
                if "id" not in jsonRpcResponse:
                    if time.time() - startTime > 20.0:
                        Sentry.Warn("Credetials", "TryToGetCredentials timeout waiting for db query response after "+str(msgCount)+" messages.")
                        return None
                    continue

                # Make sure this is us.
                if jsonRpcResponse["id"] != msgId:
                    Sentry.Info("Credetials", "TryToGetCredentials got a response for a different id? got:"+str(jsonRpcResponse["id"]) + " expected:"+str(msgId))
                    continue
                # Check for error.
                if "error" in jsonRpcResponse:
                    Sentry.Warn("Credetials", "TryToGetCredentials got a response but it had an error. "+str(jsonRpcResponse["error"]))
                    return None

                # Look for the result string.
                if "result" not in jsonRpcResponse:
                    Sentry.Warn("Credetials", "TryToGetCredentials got a response but with no result object.")
                    return None
                result  = jsonRpcResponse["result"]
                if isinstance(result, str) is False:
                    Sentry.Warn("Credetials", "TryToGetCredentials got a response but result is not a str. "+str(result))
                    return None

                # We got it!
                Sentry.Info("Credetials", "MoonrakerCredentialManager successfully found the API key.")
                return result

        except Exception as e:
            Sentry.Exception("TryToGetCredentials failed to open the unix socket.", e)
            return None


    def _TryToFindUnixSocket(self) -> str or None:

        # First, try to parse the moonraker config to find the klipper socket path, since the moonraker socket should be similar.
        try:
            # Open and read the config.
            # allow_no_value allows keys with no values - strict allows duplicate sections, because sometimes that happens for unknown reasons.
            # Since this is edited by the user, we allow non-strict stuff, since they can make mistakes like multiple sections.
            moonrakerConfig = configparser.ConfigParser(allow_no_value=True, strict=False)
            moonrakerConfig.read(self.MoonrakerConfigFilePath)
            if "server" not in moonrakerConfig:
                Sentry.Info("Credetials", "_TryToFindUnixSocket - No server block found in moonraker config.")
            else:
                if "klippy_uds_address" not in moonrakerConfig["server"]:
                    Sentry.Info("Credetials", "_TryToFindUnixSocket - klippy_uds_address found in moonraker config.")
                else:
                    # In most installs, this will be something like `~/printer_data/comms/klippy.sock`
                    klippySocketFilePath = moonrakerConfig["server"]["klippy_uds_address"]
                    Sentry.Info("Credetials", "Moonraker klippy unix socket path found in config: "+klippySocketFilePath)
                    possibleComFolderPath = self._GetParentDirectory(klippySocketFilePath)
                    possibleMoonrakerSocketFilePath = os.path.join(possibleComFolderPath, MoonrakerCredentialManager.c_MoonrakerUnixSocketFileName)
                    if os.path.exists(possibleMoonrakerSocketFilePath):
                        Sentry.Info("Credetials", "Moonraker socket path found from moonraker config klippy socket path. :"+possibleMoonrakerSocketFilePath)
                        return possibleMoonrakerSocketFilePath
        except Exception as e:
            Sentry.Exception("_TryToFindUnixSocket failed to handle moonraker config.", e)

        # If that failed, try to find the path by stepping back from the moonraker config a few times.
        moonrakerConfigFolderPath = self._GetParentDirectory(self.MoonrakerConfigFilePath)

        # Test the config folder for the file and file + comms folder
        # This isn't likely, but we might as well try.
        testPath = os.path.join(moonrakerConfigFolderPath, MoonrakerCredentialManager.c_MoonrakerUnixSocketFileName)
        if os.path.exists(testPath):
            Sentry.Info("Credetials", "Moonraker unix socket path found from moonraker config path. :"+testPath)
            return testPath
        testPath = os.path.join(moonrakerConfigFolderPath, MoonrakerCredentialManager.c_MoonrakerUnixSocketFileNameWithCommsFolder)
        if os.path.exists(testPath):
            Sentry.Info("Credetials", "Moonraker unix socket path found from moonraker config path. :"+testPath)
            return testPath

        # Move a folder up and try again. This is where we expect the comms folder to be located, next to the config folder
        moonrakerPrinterFolderPath = self._GetParentDirectory(moonrakerConfigFolderPath)
        testPath = os.path.join(moonrakerPrinterFolderPath, MoonrakerCredentialManager.c_MoonrakerUnixSocketFileName)
        if os.path.exists(testPath):
            Sentry.Info("Credetials", "Moonraker unix socket path found from moonraker printer folder path. :"+testPath)
            return testPath
        testPath = os.path.join(moonrakerPrinterFolderPath, MoonrakerCredentialManager.c_MoonrakerUnixSocketFileNameWithCommsFolder)
        if os.path.exists(testPath):
            Sentry.Info("Credetials", "Moonraker unix socket path found from moonraker printer folder path. :"+testPath)
            return testPath
        return None


    # Returns the parent directory of the passed directory or file path.
    def _GetParentDirectory(self, path):
        return os.path.abspath(os.path.join(path, os.pardir))


    def _ReadSingleJsonObject(self, sock) -> str or None:
        # Since sock.recv blocks, we must read each char one by one so we know when the message ends.
        # This is messy, but since it only happens very occasionally, it's fine.
        message = bytearray()
        while True:
            # Sanity check so we don't spin for ever.
            if len(message) > 10000:
                Sentry.Error("Credetials", "_ReadSingleJsonObject failed to read message, it was too long. "+message.decode(encoding="utf=8"))
                return None

            # Read one, add it to the buffer, and see if we are done.
            data = sock.recv(1)
            if data[0] == 3: # This is EXT aka End of text. It separates the json messages.
                return message.decode(encoding="utf=8")
            message += data
