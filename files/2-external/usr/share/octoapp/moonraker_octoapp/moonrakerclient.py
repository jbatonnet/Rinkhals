import os
import sys
import threading
import time
import json
import queue
import logging
import math
import urllib.request
from urllib.parse import quote

import configparser
from octoapp.compat import Compat

from octoapp.sentry import Sentry
from octoapp.notificationutils import NotificationUtils
from octoapp.websocketimpl import Client
from octoapp.notificationshandler import NotificationsHandler
from .moonrakercredentailmanager import MoonrakerCredentialManager
from .filemetadatacache import FileMetadataCache
from .observerconfigfile import ObserverConfigFile

# The response object for a json rpc request.
# Contains information on the state, and if successful, the result.
class JsonRpcResponse:

    # Our specific errors
    OE_ERROR_WS_NOT_CONNECTED = 99990001
    OE_ERROR_TIMEOUT = 99990002
    OE_ERROR_EXCEPTION = 99990003

    def __init__(self, resultObj, errorCode = 0, errorStr : str = None) -> None:
        self.Result = resultObj
        self.ErrorCode = errorCode
        self.ErrorStr = errorStr
        if self.ErrorCode == JsonRpcResponse.OE_ERROR_TIMEOUT:
            self.ErrorStr = "Timeout waiting for RPC response."
        if self.ErrorCode == JsonRpcResponse.OE_ERROR_WS_NOT_CONNECTED:
            self.ErrorStr = "No active websocket connected."

    def HasError(self) -> bool:
        return self.ErrorCode != 0

    def GetErrorCode(self) -> int:
        return self.ErrorCode

    def GetErrorStr(self) -> str:
        return self.ErrorStr

    def GetLoggingErrorStr(self) -> str:
        return str(self.ErrorCode) + " - " + str(self.ErrorStr)

    def GetResult(self):
        return self.Result


# This class is our main interface to interact with moonraker. This includes the logic to make
# requests with moonraker and logic to maintain a websocket connection.
class MoonrakerClient:

    # The max amount of time we will wait for a request before we timeout.
    # For some reason, some calls seem to take a really long time to complete (like database calls), so we make this timeout quite high.
    RequestTimeoutSec = 60.0

    # Logic for a static singleton
    _Instance = None


    @staticmethod
    def Init(isObserverMode:bool, moonrakerConfigFilePath:str, observerConfigPath:str, printerId, connectionStatusHandler, pluginVersionStr, moonrakerDatabase):
        MoonrakerClient._Instance = MoonrakerClient(isObserverMode, moonrakerConfigFilePath, observerConfigPath, printerId, connectionStatusHandler, pluginVersionStr, moonrakerDatabase)


    @staticmethod
    def Get():
        return MoonrakerClient._Instance


    def __init__(self, isObserverMode:bool, moonrakerConfigFilePath:str, observerConfigPath:str, printerId:str, connectionStatusHandler, pluginVersionStr:str, moonrakerDatabase) -> None:
        self.IsObserverMode = isObserverMode
        self.MoonrakerConfigFilePath = moonrakerConfigFilePath
        self.ObserverConfigPath = observerConfigPath
        self.MoonrakerHostAndPort = "127.0.0.1:7125"
        self.PrinterId = printerId
        self.ConnectionStatusHandler = connectionStatusHandler
        self.PluginVersionStr = pluginVersionStr
        self.MoonrakerDatabase = moonrakerDatabase
        self.ScheduledNotificationsCache = {}

        # Setup the json-rpc vars
        self.JsonRpcIdLock = threading.Lock()
        self.JsonRpcIdCounter = 0
        self.JsonRpcWaitingContexts = {}

        # Setup the Moonraker compat helper object.
        self.MoonrakerCompat = MoonrakerCompat(printerId)

        # Setup the non response message thread
        # See _NonResponseMsgQueueWorker to why this is needed.
        self.NonResponseMsgQueue = queue.Queue(20000)
        self.NonResponseMsgThread = threading.Thread(target=self._NonResponseMsgQueueWorker)
        self.NonResponseMsgThread.start()

        # Some instances use auth and we need an API key to access them. If this is not set to None, it's the API key.
        # This is found and set when we try to connect and we fail due to an unauthed socket.
        self.MoonrakerApiKey = None

        # Setup the WS vars and a websocket worker thread.
        # Don't run it until StartRunningIfNotAlready is called!
        self.WebSocket = None
        self.WebSocketConnected = False
        self.WebSocketKlippyReady = False
        self.WebSocketLock = threading.Lock()


    def GetNotificationHandler(self) -> NotificationsHandler:
        return self.MoonrakerCompat.GetNotificationHandler()


    def GetMoonrakerCompat(self):
        return self.MoonrakerCompat


    def GetIsKlippyReady(self):
        return self.WebSocketKlippyReady


    # Checks to moonraker config for the host and port. We use the moonraker config so we don't duplicate the
    # value in our settings, which could change. This is called by the Websocket and then the result is saved in the class
    # This is so every http call doesn't have to read the file, but as long as the WS is connected, we know the address is correct.
    def _UpdateMoonrakerHostAndPort(self) -> None:
        # Ensure we have a file. For now, this is required.
        if self.IsObserverMode:
            if os.path.exists(self.ObserverConfigPath) is False:
                Sentry.Error("Client", "Moonraker client failed to find a observer config. Re-run the ./install.sh script from the OctoApp repo to update the path.")
                raise Exception("No observer config file found")
        else:
            if os.path.exists(self.MoonrakerConfigFilePath) is False:
                Sentry.Error("Client", "Moonraker client failed to find a moonraker config. Re-run the ./install.sh script from the OctoApp repo to update the path.")
                raise Exception("No config file found")

        # Get the values.
        (hostStr, portInt) = self.GetMoonrakerHostAndPortFromConfig()

        # Set the new address
        self.MoonrakerHostAndPort =  hostStr + ":" + str(portInt)

    # Parses the config file for the hostname and port.
    # If no file is found or the server block is missing, this will return the default values.
    # Always returns the hostname as a string, and the port as an int.
    def GetMoonrakerHostAndPortFromConfig(self):
        currentPortInt = 7125
        currentHostStr = "0.0.0.0"
        try:
            # If we are in observer mode, we need to use the observer config to find the remote moonraker details.
            if Compat.IsObserverMode():
                ip, portStr = ObserverConfigFile.Get().TryToGetIpAndPortStr()
                if ip is None or portStr is None:
                    Sentry.Error("Client", "Failed to get observer moonraker details from observer config.")
                    return (currentHostStr, currentPortInt)
                return (ip, int(portStr))

            # Ensure we have a file.
            if os.path.exists(self.MoonrakerConfigFilePath) is False:
                Sentry.Error("Client", "GetMoonrakerHostAndPortFromConfig failed to find moonraker config file.")
                return (currentHostStr, currentPortInt)

            # Open and read the config.
            moonrakerConfig = configparser.ConfigParser()
            moonrakerConfig.read(self.MoonrakerConfigFilePath)

            # We have found that some users don't have a [server] block, so if they don't, return the defaults.
            if "server" not in moonrakerConfig:
                Sentry.Info("Client", "No server block found in the moonraker config, so we are returning the defaults. Host:"+currentHostStr+" Port:"+str(currentPortInt))
                return (currentHostStr, currentPortInt)

            # Otherwise, parse the host and port, if they exist.
            serverBlock = moonrakerConfig["server"]
            if "host" in serverBlock:
                currentHostStr = moonrakerConfig['server']['host']
            if "port" in serverBlock:
                currentPortInt = int(moonrakerConfig['server']['port'])

            # Done!
            return (currentHostStr, currentPortInt)

        except Exception as e:
            Sentry.Exception("Failed to read moonraker port and host from config, assuming defaults. Host:"+currentHostStr+" Port:"+str(currentPortInt), e)
            return (currentHostStr, currentPortInt)


    #
    # Below this is websocket logic.
    #

    # Sends a rpc request via the connected websocket. This request will block until a response is received or the request times out.
    # This will not throw, it will always return a JsonRpcResponse which can be checked for errors or success.
    #
    # Here are the docs on the WS and JSON-RPC
    # https://moonraker.readthedocs.io/en/latest/web_api/#json-rpc-api-overview
    # https://moonraker.readthedocs.io/en/latest/web_api/#websocket-setup
    #
    def SendJsonRpcRequest(self, method:str, paramsDict = None) -> JsonRpcResponse:
        msgId = 0
        waitContext = None
        with self.JsonRpcIdLock:
            # Get our unique ID
            msgId = self.JsonRpcIdCounter
            self.JsonRpcIdCounter += 1

            # Add our waiting context.
            waitContext = JsonRpcWaitingContext(msgId)
            self.JsonRpcWaitingContexts[msgId] = waitContext

        # From now on, we need to always make sure to clean up the wait context, even in error.
        try:
            # Create the request object
            obj = {
                "jsonrpc": "2.0",
                "method": method,
                "id": msgId
            }
            # Add the params, if there are any.
            if paramsDict is not None:
                obj["params"] = paramsDict

            # Try to send. default=str makes the json dump use the str function if it fails to serialize something.
            jsonStr = json.dumps(obj, default=str)
            Sentry.Debug("Client", "Moonraker RPC Request - "+str(msgId)+" : "+method+" "+jsonStr)
            if self._WebSocketSend(jsonStr) is False:
                Sentry.Info("Client", "Moonraker client failed to send JsonRPC request "+method)
                return JsonRpcResponse(None, JsonRpcResponse.OE_ERROR_WS_NOT_CONNECTED)

            # Wait for a response
            waitContext.GetEvent().wait(MoonrakerClient.RequestTimeoutSec)

            # Check if we got a result.
            result = waitContext.GetResult()
            if result is None:
                Sentry.Info("Client", "Moonraker client timeout while waiting for request. "+str(id)+" "+method)
                return JsonRpcResponse(None, JsonRpcResponse.OE_ERROR_TIMEOUT)

            # Check for an error if found, return the error state.
            if "error" in result:
                # Get the error parts
                errorCode = JsonRpcResponse.OE_ERROR_EXCEPTION
                errorStr = "Unknown"
                if "code" in result["error"]:
                    errorCode = result["error"]["code"]
                if "message" in result["error"]:
                    errorStr = result["error"]["message"]
                return JsonRpcResponse(None, errorCode, errorStr)

            # If there's a result, return the entire response
            if "result" in result:
                return JsonRpcResponse(result["result"])

            # Finally, both are missing?
            Sentry.Error("Client", "Moonraker client json rpc got a response that didn't have an error or result object? "+json.dumps(result))
            return JsonRpcResponse(None, JsonRpcResponse.OE_ERROR_EXCEPTION, "No result or error object")

        except Exception as e:
            Sentry.Exception("Moonraker client json rpc request failed to send.", e)
            return JsonRpcResponse(None, JsonRpcResponse.OE_ERROR_EXCEPTION, str(e))

        finally:
            # Before leaving, always clean up any waiting contexts.
            with self.JsonRpcIdLock:
                if msgId in self.JsonRpcWaitingContexts:
                    del self.JsonRpcWaitingContexts[msgId]


    # Sends a string to the connected websocket.
    # forceSend is used to send the initial messages before the system is ready.
    def _WebSocketSend(self, jsonStr:str) -> bool:
        # Only allow one send at a time, thus we do it under lock.
        with self.WebSocketLock:
            # Note that in the past we waited for klippy ready, but that doesn't really make sense because a lot of apis like db and such don't care.
            # Any api that needs klippy to be ready will fail with an error anyways.
            if self.WebSocketConnected is False:
                Sentry.Info("Client", "Moonraker client - tired to send a websocket message when the socket wasn't open.")
                return False
            localWs = self.WebSocket
            if localWs is None:
                Sentry.Info("Client", "Moonraker client - tired to send a websocket message before the websocket was created.")
                return False

            # Print for debugging.
            Sentry.Debug("Client WS", "-> %s" % jsonStr)

            # Send under lock.
            try:
                localWs.Send(jsonStr, False)
            except Exception as e:
                Sentry.Exception("Moonraker client exception in websocket send.", e)
                return False
        return True


    # Called when a new websocket is connected and klippy is ready.
    # At this point, we should setup anything we need to do and sync any state required.
    # This is called on a background thread, so we can block this.
    def _OnWsOpenAndKlippyReady(self):
        Sentry.Info("Client", "Moonraker client setting up default notification hooks")
        # First, we need to setup our notification subs
        # https://moonraker.readthedocs.io/en/latest/web_api/#subscribe-to-printer-object-status
        # https://moonraker.readthedocs.io/en/latest/printer_objects/
        #result = self.SendJsonRpcRequest("printer.objects.list")
        result = self.SendJsonRpcRequest("printer.objects.subscribe",
        {
            "objects":
            {
                # Using None allows us to get all of the data from the notification types.
                # For some types, using None has way too many updates, so we filter them down.
                "print_stats": { "state", "filename", "message" },
                "webhooks": None,
                "virtual_sdcard": None,
                "history" : None,
            }
        })

        # Verify success.
        if result.HasError():
            Sentry.Error("Client", "Failed to setup moonraker notification subs. "+result.GetLoggingErrorStr())
            self._RestartWebsocket()
            return

        # Call the event handler
        self.MoonrakerCompat.OnMoonrakerClientConnected()

        # Finally, tell the host that we are connected and ready.
        self.ConnectionStatusHandler.OnMoonrakerClientConnected()


    # Called when the websocket gets any other message that's not a RPC response.
    # If we throw from here, the websocket will close and restart.
    def _OnWsNonResponseMessage(self, msg:str):
        # Get the common method string
        if "method" not in msg:
            Sentry.Warn("Client", "Moonraker WS message received with no method "+json.dumps(msg))
            return
        method = msg["method"].lower()

        # These objects can come in all shapes and sizes. So we only look for exactly what we need, if we don't find it
        # We ignore the object, someone else might match it.

        # Used to watch for print starts, ends, and failures.
        if method == "notify_history_changed":
            actionContainerObj = self._GetWsMsgParam(msg, "action")
            if actionContainerObj is not None:
                action = actionContainerObj["action"]
                if action == "added":
                    jobContainerObj = self._GetWsMsgParam(msg, "job")
                    if jobContainerObj is not None:
                        jobObj = jobContainerObj["job"]
                        if "filename" in jobObj:
                            fileName = jobObj["filename"]
                            self.MoonrakerCompat.OnPrintStart(fileName)
                            self.DownloadFileForProcessing(fileName)
                            return
                elif action == "finished":
                    # This can be a finish canceled or failed.
                    # Oddly, this doesn't fire for print complete.
                    #
                    # We need to be able to find filename, total_duration, and status.
                    jobContainerObj = self._GetWsMsgParam(msg, "job")
                    if jobContainerObj is not None:
                        jobObj = jobContainerObj["job"]
                        if "filename" in jobObj:
                            fileName = jobObj["filename"]
                            if "total_duration" in jobObj:
                                totalDurationSecFloat = jobObj["total_duration"]
                                if "status" in jobObj:
                                    status = jobObj["status"]
                                    # We have everything we need
                                    if status == "cancelled":
                                        self.MoonrakerCompat.OnFailedOrCancelled(fileName, totalDurationSecFloat)
                                        return

        if method == "notify_status_update":
            # This is shared by a few things, so get it once.
            progressFloat_CanBeNone = self._GetProgressFromMsg(msg)
            filePos_CanBeNone = self._GetFilePosFromMsg(msg)

            # Check for a state container
            stateContainerObj = self._GetWsMsgParam(msg, "print_stats")
            if stateContainerObj is not None:
                ps = stateContainerObj["print_stats"]
                if "state" in ps:
                    state = ps["state"]
                    # Check for pause
                    if state == "paused":
                        self.MoonrakerCompat.OnPrintPaused()
                        return
                    # Resume is hard, because it's hard to tell the difference between printing we get from the starting message
                    # and printing we get from a resume. So the way we do it is by looking at the progress, to see if it's just starting or not.
                    # 0.01 == 1%, so if the print is resumed before then, this won't fire. For small prints, we need to have a high threshold,
                    # so they don't trigger something too much lower too easily.
                    elif state == "printing":
                        if progressFloat_CanBeNone is None or progressFloat_CanBeNone > 0.01:
                            self.MoonrakerCompat.OnPrintResumed()
                            return
                    elif state == "complete":
                        self.MoonrakerCompat.OnDone()
                        return

            # Report progress. Do this after the others so they will report before a potential progress update.
            # Progress updates super frequently (like once a second) so there's plenty of chances.
            if progressFloat_CanBeNone is not None and filePos_CanBeNone is not None:
                self.MoonrakerCompat.OnPrintProgress(progressFloat_CanBeNone, filePos_CanBeNone)

        # When the webcams change, kick the webcam helper.
        if method == "notify_webcams_changed":
            self.ConnectionStatusHandler.OnWebcamSettingsChanged()

    def DownloadFileForProcessing(self, fileName):
        try:
            modified = FileMetadataCache.Get().GetModified(fileName)
            cacheKey = fileName + ":" + str(modified)

            if cacheKey in self.ScheduledNotificationsCache.keys():
                Sentry.Info("Client", "Reusing cached notifications for " + fileName)
                self.MoonrakerCompat.ScheduleNotifications(self.ScheduledNotificationsCache[cacheKey])
                return

            path = '/'.join(list(map(quote, fileName.split("/"))))
            url = "http://" + self.MoonrakerHostAndPort + "/server/files/gcodes/" + path
            Sentry.Info("Client", "Processing file at %s" % url)
            with urllib.request.urlopen(url) as response:
                notifications = NotificationUtils.ExtractNotifications(response)
                self.MoonrakerCompat.ScheduleNotifications(notifications)
                Sentry.Info("Client", "File processed")
                self.ScheduledNotificationsCache[cacheKey] = notifications

        except Exception as e:
            Sentry.ExceptionNoSend("Failed to download file for notification processing", e)


    # If the message has a progress contained in the virtual_sdcard, this returns it. The progress is a float from 0.0->1.0
    # Otherwise None
    def _GetProgressFromMsg(self, msg):
        vsdContainerObj = self._GetWsMsgParam(msg, "virtual_sdcard")
        if vsdContainerObj is not None:
            vsd = vsdContainerObj["virtual_sdcard"]
            if "progress" in vsd:
                return vsd["progress"]
        return None

    
    # If the message has a progress contained in the virtual_sdcard, this returns it
    # Otherwise None
    def _GetFilePosFromMsg(self, msg):
        vsdContainerObj = self._GetWsMsgParam(msg, "virtual_sdcard")
        if vsdContainerObj is not None:
            vsd = vsdContainerObj["virtual_sdcard"]
            if "file_position" in vsd:
                return vsd["file_position"]
        return None


    # Given a property name, returns the correct param object that contains that object.
    def _GetWsMsgParam(self, msg, paramName):
        if "params" not in msg:
            return None
        paramArray = msg["params"]
        for p in paramArray:
            # Only test things that are dicts.
            if isinstance(p, dict) and paramName in p:
                return p
        return None


    def RunBlocking(self):
        Sentry.Info("Client", "Moonraker client starting websocket connection thread.")
        while True:
            try:
                # Every time we connect, call the function to update the host and port if required.
                # We only call this from the WS and cache result, so every http call doesn't need to do it.
                # We know if the WS is connected, the host and port must be correct.
                self._UpdateMoonrakerHostAndPort()

                # Create a websocket client and start it connecting.
                url = "ws://"+self.MoonrakerHostAndPort+"/websocket"
                Sentry.Info("Client", "Connecting to moonraker: "+url)
                with self.WebSocketLock:
                    self.WebSocket = Client(url,
                                    self._OnWsOpened,
                                    self._onWsMsg,
                                    None, # self._onWsData, all messages are passed to data and msg, so we don't need this.
                                    self._onWsClose,
                                    self._onWsError
                                    )

                # Run until the socket closes
                self.WebSocket.RunUntilClosed()

            except Exception as e:
                Sentry.Exception("Moonraker client exception in main WS loop.", e)

            # Inform that we lost the connection.
            Sentry.Info("Client", "Moonraker client websocket connection lost. We will try to restart it soon.")

            # Set that the websocket is disconnected.
            with self.WebSocketLock:
                self.WebSocketConnected = False
                self.WebSocketKlippyReady = False

            # When the websocket closes, we need to clear out all pending waiting contexts.
            with self.JsonRpcIdLock:
                for context in self.JsonRpcWaitingContexts.values():
                    context.SetSocketClosed()

            # This will only happen if the websocket closes or there was an error.
            # Sleep for a bit so we don't spam the system with attempts.
            time.sleep(2.0)


    # Based on the docs: https://moonraker.readthedocs.io/en/latest/web_api/#websocket-setup
    # After the websocket is open, we need to do this sequence to make sure the system is healthy and ready.
    def _AfterOpenReadyWaiter(self, targetWsObjRef):

        logCounter = 0
        Sentry.Info("Client", "Moonraker client waiting for klippy ready...")
        try:
            # Before we do anything, we need to identify ourselves.
            # This is also how we authorize ourself with the API key, if needed.
            # https://moonraker.readthedocs.io/en/latest/web_api/#identify-connection
            Sentry.Info("Client", "Authenticating with moonraker...")
            params = {
                "client_name": "OctoApp",
                "version": self.PluginVersionStr,
                "type": "agent", # We must be the agent type so that we can send agent-event, aka send messages to the UI.
                "url": "https://octoapp.eu",
            }
            if self.MoonrakerApiKey is not None:
                Sentry.Info("Client", "API key added to websocket identify message.")
                params["api_key"] =  self.MoonrakerApiKey
            # Since "server.info" already handles all of the error logic, we don't bother here,
            # since server.info will get the same error anyways. (timeouts, unauthorized, etc.)
            _ = self.SendJsonRpcRequest("server.connection.identify", params)

            # Since sometimes the moonraker instances ins't connected to klippy, we still want to notify some systems
            # When the websocket is established and we are authed, so they can use it.
            self.ConnectionStatusHandler.OnMoonrakerWsOpenAndAuthed()

            Sentry.Info("Client", "Moonraker client waiting for klippy ready...")
            while True:
                # Ensure we are still using the active websocket. We use this to know if the websocket we are
                # trying to monitor is gone and the system has started a new one.
                testWs = self.WebSocket
                if testWs is None or testWs is not targetWsObjRef:
                    Sentry.Warn("Client", "The target websocket changed while waiting on klippy ready.")
                    return

                # Query the state, use the force flag to make sure we send even though klippy ready is not set.
                result = self.SendJsonRpcRequest("server.info", None)

                # Check for error
                if result.HasError():
                    # Check if the error is Unauthorized, in which case we need to try to get credentials.
                    if result.ErrorCode == -32602 or result.ErrorStr == "Unauthorized":
                        Sentry.Info("Client", "Our websocket connection to moonraker needs auth, trying to get the API key...")
                        self.MoonrakerApiKey = MoonrakerCredentialManager.Get().TryToGetApiKey()
                        if self.MoonrakerApiKey is None:
                            Sentry.Error("Client", "Our websocket connection to moonraker needs auth and we failed to get the API key.")
                            raise Exception("Websocket unauthorized.")
                        else:
                            Sentry.Info("Client", "Successfully got the API key, restarting the websocket to try again using it.")
                            # Shut down the websocket so we do the reconnect logic.
                            self._RestartWebsocket()
                            return

                    # Handle the timeout without throwing, since this happens sometimes when the system is down.
                    if result.ErrorCode == JsonRpcResponse.OE_ERROR_TIMEOUT:
                        Sentry.Info("Client", "Moonraker client failed to send klippy ready query message, it hit a timeout.")
                        self._RestartWebsocket()
                        return
                    Sentry.Error("Client", "Moonraker client failed to send klippy ready query message. "+result.GetLoggingErrorStr())
                    raise Exception("Error returned from klippy state query. "+ str(result.GetLoggingErrorStr()))

                # Check for klippy state
                resultObj = result.GetResult()
                if "klippy_state" not in resultObj:
                    Sentry.Error("Client", "Moonraker client got a klippy ready query response, but there was no klippy_state? "+json.dumps(resultObj))
                    raise Exception("No klippy_state found in result object. "+ str(result.GetLoggingErrorStr()))

                # Handle klippy state
                state = resultObj["klippy_state"]
                if state == "ready":
                    # Ready
                    Sentry.Info("Client", "Moonraker client klippy state is ready. Moonraker connection is ready and stable.")
                    with self.WebSocketLock:
                        self.WebSocketKlippyReady = True
                    # Call the connected and ready function, to let anything else do a new connection setup.
                    self._OnWsOpenAndKlippyReady()
                    # Done
                    return

                if state == "startup" or state == "error" or state == "shutdown" or state == "initializing":
                    logCounter += 1
                    # 2 seconds * 150 = one log every 5 minutes. We don't want to log a ton if the printer is offline for a long time.
                    if logCounter % 150 == 1:
                        Sentry.Info("Client", "Moonraker client got klippy state '"+state+"', waiting for ready...")
                    # We need to wait until ready. The doc suggest we wait 2 seconds.
                    time.sleep(2.0)
                    continue

                # Unknown state
                Sentry.Error("Client", f"Moonraker client is in an unknown klippy waiting state. state '{state}'")
                raise Exception(f"Unknown klippy waiting state. {state}")

        except Exception as e:
            Sentry.Exception("Moonraker client exception in klippy waiting logic.", e)
            # Shut down the websocket so we do the reconnect logic.
            self._RestartWebsocket()


    # Kills the current websocket connection. Our logic will auto try to reconnect.
    def _RestartWebsocket(self):
        with self.WebSocketLock:
            if self.WebSocket is None:
                return
            Sentry.Info("Client", "Moonraker client websocket shutdown called.")
            self.WebSocket.Close()
            Sentry.Info("Client", "Moonraker client websocket shutdown complete.")


    # Called when the websocket is opened.
    def _OnWsOpened(self, ws):
        Sentry.Info("Client", "Moonraker client websocket opened.")

        # Set that the websocket is open.
        with self.WebSocketLock:
            self.WebSocketConnected = True

        # According to the docs, there's a startup sequence we need to before sending requests.
        # We use a new thread to do the startup sequence, since we can't block this or we won't get messages.
        t = threading.Thread(target=self._AfterOpenReadyWaiter, args=(ws,))
        t.start()


    def _onWsMsg(self, ws, msgBytes: bytes):
        try:
            # Parse the incoming message.
            msgObj = json.loads(msgBytes)

            # Get the method if there is one.
            method_CanBeNone = None
            if "method" in msgObj:
                method_CanBeNone = msgObj["method"]

            # Print for debugging
            if Sentry.Logger.isEnabledFor(logging.DEBUG):
                # Exclude this really chatty message.
                msgStr = msgBytes.decode(encoding="utf-8")
                if "moonraker_stats" not in msgStr:
                    Sentry.Debug("Client WS", "<- %s" % msgStr)

            # Check if this is a response to a request
            # info: https://moonraker.readthedocs.io/en/latest/web_api/#json-rpc-api-overview
            if "id" in msgObj:
                with self.JsonRpcIdLock:
                    idInt = int(msgObj["id"])
                    if idInt in self.JsonRpcWaitingContexts:
                        self.JsonRpcWaitingContexts[idInt].SetResultAndEvent(msgObj)
                    else:
                        Sentry.Warn("Client", "Moonraker RPC response received for request "+str(idInt) + ", but there is no waiting context.")
                    # If once the response is handled, we are done.
                    return

            # Check for a special message that indicates the klippy connection has been lost.
            # According to the docs, in this case, we should restart the klippy ready process, so we will
            # nuke the WS and start again.
            # The system seems to use both of these at different times. If there's a print running it uses notify_klippy_shutdown, where as if there's not
            # it seems to use notify_klippy_disconnected. We handle them both as the same.
            if method_CanBeNone is not None and (method_CanBeNone == "notify_klippy_disconnected" or method_CanBeNone == "notify_klippy_shutdown"):
                Sentry.Info("Client", "Moonraker client received %s notification, so we will restart our client connection." % method_CanBeNone)
                self._RestartWebsocket()
                self.MoonrakerCompat.KlippyDisconnectedOrShutdown()
                return

            # We use a queue to handle all non reply messages to prevent this thread from getting blocked.
            # The problem is if any of the code paths upstream from the non reply notification tried to issue a request/response
            # they would never get it, because this receive thread would be blocked.
            #
            # If this queue is full, it will throw, but it has a huge capacity, so that would be bad.
            self.NonResponseMsgQueue.put_nowait(msgObj)

        except Exception as e:
            Sentry.Exception("Exception while handing moonraker client websocket message.", e)
            # Raise again which will cause the websocket to close and reset.
            raise e


    def _NonResponseMsgQueueWorker(self):
        try:
            while True:
                # Wait for a message to process.
                msg = self.NonResponseMsgQueue.get()
                # Process and then wait again.
                self._OnWsNonResponseMessage(msg)
        except Exception as e:
            Sentry.Exception("_NonReplyMsgQueueWorker got an exception while handing messages. Killing the websocket. ", e)
        self._RestartWebsocket()


    # Called when the websocket is closed for any reason, connection loss or exception
    def _onWsClose(self, ws):
        Sentry.Info("Client", "Moonraker websocket connection closed.")


    # Called if the websocket hits an error and is closing.
    def _onWsError(self, ws, exception):
        Sentry.Exception("Exception rased from moonraker client websocket connection. The connection will be closed.", exception)


# A helper class used for waiting rpc requests
class JsonRpcWaitingContext:

    def __init__(self, msgId) -> None:
        self.Id = msgId
        self.WaitEvent = threading.Event()
        self.Result = None


    def GetEvent(self):
        return self.WaitEvent


    def GetResult(self):
        return self.Result


    def SetResultAndEvent(self, result):
        self.Result = result
        self.WaitEvent.set()


    def SetSocketClosed(self):
        self.Result = None
        self.WaitEvent.set()


# The goal of this class it add any needed compatibility logic to allow the moonraker system plugin into the
# common OctoApp logic.
class MoonrakerCompat:

    def __init__(self, printerId:str) -> None:

        # This indicates if we are ready to process notifications, so we don't
        # fire any notifications before we run the print state sync logic.
        self.IsReadyToProcessNotifications = False

        # We get progress updates super frequently, we don't need to handle them all.
        self.TimeSinceLastProgressUpdate = time.time()

        # This class owns the notification handler.
        # We pass our self as the Printer State Interface
        self.NotificationHandler = NotificationsHandler(self)
        # self.NotificationHandler.SetPrinterId(printerId)

        # Set the LastFilePos to a high value so the layer notifications are not send if the plugin
        # is started during a print
        self.LastFilePos = sys.maxsize
        self.ScheduledNotifications = {}


    def GetNotificationHandler(self):
        return self.NotificationHandler


    #
    # Events
    #


    # TODO - Notification Type Status!
    #  OnStarted - Done
    #  OnFailed - Partial
    #     But right now we don't differentiate between failed due to error and failed due to user cancel.
    #  OnDone - Done
    #  OnPaused - Done
    #  OnResume - Done
    #  OnError - Partial
    #     We report if klippy disconnects from moonraker
    #  OnWaiting - Missing
    #     Unsure if we get this from moonraker
    #  OnFilamentChange - Missing
    #     Unsure if we get this from moonraker
    #  OnUserInteractionNeeded - Missing
    #     Unsure if we get this from moonraker
    #  OnPrintProgress - Done


    # Called when a new websocket is established to moonraker.
    def OnMoonrakerClientConnected(self):

        # This is the hardest of all the calls. The reason being, this call can happen if our service or moonraker restarted, an print
        # can be running while either of those restart. So we need to sync the state here, and make sure things like Gadget and the
        # notification system having their progress threads running correctly.
        self._InitPrintStateForFreshConnect()

        # We are ready to process notifications!
        self.IsReadyToProcessNotifications = True


    # Called when moonraker's connection to klippy disconnects.
    # The systems seems to use disconnect and shutdown at different times for the same purpose, so we handle both the same.
    def KlippyDisconnectedOrShutdown(self):
        # Only process notifications when ready, aka after state sync.
        if self.IsReadyToProcessNotifications is False:
            return

        # Set the flag to false again, since we can't send any more notifications until we are reconnected and re-synced.
        self.IsReadyToProcessNotifications = False

        # Only fire this error if we are tracking a print.
        # The problem is this fires on Klipper setups whenever the printer is turned off, which can be common for scripts and plugins
        # to do after a print. This notification is good if it happens while a print is running, because that would be bad. Otherwise, ignore it
        # so it doesn't spam the user.
        if self.NotificationHandler.IsTrackingPrint() is False:
            Sentry.Info("Client", "Ignoring KlippyDisconnectedOrShutdown notification because we aren't tracking a print.")
            return

        # Since we will get this disconnected error for anything, including intentional restarts,
        # we defer the notification for a few seconds and check if the system is still disconnected.
        # If it's still down, we fire the notification.
        def disconnectWaiter():
            time.sleep(5.0)
            if MoonrakerClient.Get().GetIsKlippyReady() is False:
                # Send a notification to the user.
                self.NotificationHandler.OnError("Klipper Disconnected")

        # Push the work off to a thread so we don't hang OctoPrint's plugin callbacks.
        thread = threading.Thread(target=disconnectWaiter)
        thread.isDaemon = True
        thread.start()


    # Called when a new print is starting.
    def OnPrintStart(self, fileName):
        # Only process notifications when ready, aka after state sync.
        if self.IsReadyToProcessNotifications is False:
            return
        
        # Get our name
        self._updatePrinterName()
    
        # Since this is a new print, reset the cache. The file name might be the same as the last, but have
        # different props, so we will always reset. We know when we are printing the same file name will have the same props.
        FileMetadataCache.Get().ResetCache()

        # Try to get the starting file info if we can.
        filamentUsageMm = FileMetadataCache.Get().GetEstimatedFilamentUsageMm(fileName)
        fileSizeKBytes = FileMetadataCache.Get().GetFileSizeKBytes(fileName)

        # Commonize to the notification handler standard.
        filamentUsageMm = max(filamentUsageMm, 0)
        fileSizeKBytes = max(fileSizeKBytes, 0)

        # Fire on started.
        self.NotificationHandler.OnStarted(fileName, fileSizeKBytes, filamentUsageMm)
        self.ScheduledNotifications = {}
        self.LastFilePos = 0

    def _updatePrinterName(self):
        try:
            # Get our name
            name = MoonrakerClient.Get().MoonrakerDatabase.GetPrinterName()
            self.NotificationHandler.NotificationSender.PrinterName = name
            Sentry.Info("Client", "Printer is called %s" % name)
        except Exception as e:
            Sentry.ExceptionNoSend("Failed to update printer name", e)


    def ScheduleNotifications(self, notifications):
        self.ScheduledNotifications = notifications


    def OnDone(self):
        # Only process notifications when ready, aka after state sync.
        if self.IsReadyToProcessNotifications is False:
            return

        # For moonraker we don't know the file name and duration, so we pass None to use
        # past collected values.
        self.NotificationHandler.OnDone(None, None)


    # Called when a print ends due to a failure or was cancelled
    def OnFailedOrCancelled(self, fileName, totalDurationSecFloat):
        # Only process notifications when ready, aka after state sync.
        if self.IsReadyToProcessNotifications is False:
            return

        # The API expects the duration as a float of seconds, as a string.
        # The API expects either cancelled or error for the reason. This is the only two strings OctoPrint produces.
        # We can't differentiate between printer errors and user canceling the print right now, so we always use cancelled.
        self.NotificationHandler.OnFailed(fileName, str(totalDurationSecFloat), "cancelled")


    # Called the the print is paused.
    def OnPrintPaused(self):
        # Only process notifications when ready, aka after state sync.
        if self.IsReadyToProcessNotifications is False:
            return

        # Get the print filename. If we fail, the pause command accepts None, which will be ignored.
        stats = self._GetCurrentPrintStats()
        fileName = None
        if stats is not None:
            fileName = stats["filename"]
        self.NotificationHandler.OnPaused(fileName)


    # Called the the print is resumed.
    def OnPrintResumed(self):
        # Only process notifications when ready, aka after state sync.
        if self.IsReadyToProcessNotifications is False:
            return

        # Get the print filename. If we fail, the pause command accepts None, which will be ignored.
        stats = self._GetCurrentPrintStats()
        fileName = None
        if stats is not None:
            fileName = stats["filename"]
        self.NotificationHandler.OnResume(fileName)


    # Called when there's a print percentage progress update.
    def OnPrintProgress(self, progressFloat, filePos):
        # Only process notifications when ready, aka after state sync.
        if self.IsReadyToProcessNotifications is False:
            return
        
        # Trigger scheduled notifications
        NotificationUtils.SendScheduledNotifications(self.ScheduledNotifications, self.NotificationHandler, filePos, self.LastFilePos)
        self.LastFilePos = filePos

        # Moonraker sends about 3 of these per second, which is way faster than we need to process them.
        nowSec = time.time()
        timeDeltaSec = nowSec - self.TimeSinceLastProgressUpdate
        if timeDeltaSec < 5.0:
            return
        self.TimeSinceLastProgressUpdate = nowSec

        # Moonraker uses from 0->1 to progress while we assume 100->0
        self.NotificationHandler.OnPrintProgress(None, progressFloat*100.0)


    #
    # Printer State Interface
    #

    # ! Interface Function ! The entire interface must change if the function is changed.
    # This function will get the estimated time remaining for the current print.
    # Returns -1 if the estimate is unknown.
    def GetPrintTimeRemainingEstimateInSeconds(self):
        result = MoonrakerClient.Get().SendJsonRpcRequest("printer.objects.query",
        {
            "objects": {
                "virtual_sdcard": None,
                "print_stats": None,
                "gcode_move": None,
            }
        })
        # Like on OctoPrint, this logic is complicated.
        # So we use a shared common function to handle it.
        return int(self.GetPrintTimeRemainingEstimateInSeconds_WithPrintStatsVirtualSdCardAndGcodeMoveResult(result))


    # ! Interface Function ! The entire interface must change if the function is changed.
    # If the printer is warming up, this value would be -1. The First Layer Notification logic depends upon this!
    # Returns the current zoffset if known, otherwise -1.
    def GetCurrentZOffset(self):
        result = MoonrakerClient.Get().SendJsonRpcRequest("printer.objects.query",
        {
            "objects": {
                "toolhead": None,
                "print_stats": None
            }
        })
        if result.HasError():
            Sentry.Error("Client", "GetCurrentZOffset failed to query toolhead objects: "+result.GetLoggingErrorStr())
            return False

        # If we are warming up, don't return a value, since the z-axis could be at any level before the print starts.
        if self.CheckIfPrinterIsWarmingUp_WithPrintStats(result):
            return -1

        # Try to get the z-axis position
        try:
            res = result.GetResult()["status"]
            zAxisPositionFloat = res["toolhead"]["position"][2]
            return zAxisPositionFloat
        except Exception as e:
            Sentry.Exception("GetCurrentZOffset exception. ", e)
        return -1


    # ! Interface Function ! The entire interface must change if the function is changed.
    # If this platform DOESN'T support getting the layer info from the system, this returns (None, None)
    # If the platform does support it...
    #     If the current value is unknown, (0,0) is returned.
    #     If the values are known, (currentLayer(int), totalLayers(int)) is returned.
    #          Note that total layers will always be > 0, but current layer can be 0!
    def GetCurrentLayerInfo(self):
        try:
            result = MoonrakerClient.Get().SendJsonRpcRequest("printer.objects.query",
            {
                "objects": {
                    "print_stats": None,
                    "gcode_move": None
                }
            })
            if result.HasError():
                Sentry.Error("Client", "GetCurrentLayerInfo failed to query toolhead objects: "+result.GetLoggingErrorStr())
                return (0,0)

            res = result.GetResult()
            printStats = res["status"]["print_stats"]
            gcodeMove = res["status"]["gcode_move"]

            # Get the file name, required for looking up layer info.
            if "filename" not in printStats:
                # This happens when there's no file loaded, which is fine if nothing is printing.
                return (0,0)
            fileName = printStats["filename"]
            if fileName is None or len(fileName) == 0:
                # This happens when there's no file loaded, which is fine if nothing is printing.
                return (0,0)

            # Get the file's layer stats.
            # Any of these can return -1.0 if they aren't known.
            layerCount, layerHeight, firstLayerHeight, objectHeight = FileMetadataCache.Get().GetLayerInfo(fileName)

            # First, try to get the total layer height
            # Note these calculations are done similar to Moonraker and Fluidd, so that the values show the same for users on all interfaces.
            totalLayers = 0
            if "info" in printStats and "total_layer" in printStats["info"] and printStats["info"]["total_layer"] is not None:
                totalLayers = int(printStats["info"]["total_layer"])
            if totalLayers == 0 and layerCount > 0:
                totalLayers = int(layerCount)
            if totalLayers == 0 and firstLayerHeight > 0 and layerHeight > 0 and objectHeight > 0:
                totalLayers = int(math.ceil(
                    (objectHeight - firstLayerHeight) / layerHeight + 1)
                )
            if totalLayers == 0:
                Sentry.Error("Client", "GetCurrentLayerInfo failed to get a total layer count.")
                return (0,0)

            # Next, try to get the current layer.
            currentLayer = -1
            if "info" in printStats and "current_layer" in printStats["info"] and printStats["info"]["current_layer"] is not None:
                currentLayer = int(printStats["info"]["current_layer"])
            if currentLayer == -1 and firstLayerHeight > 0 and layerHeight > 0 and "gcode_position" in gcodeMove and len(gcodeMove["gcode_position"]) > 2:
                # Note that we need to check print_duration before checking this, because print duration will only start going after the hotend is in print position.
                # If we take the zAxisPosition before that, the z axis might be up in a pre-print position, and we will get the wrong value.
                if "print_duration" not in printStats:
                    Sentry.Error("Client", "GetCurrentLayerInfo print_duration not found in print stats.")
                    return (0,0)
                if float(printStats["print_duration"]) > 0.0:
                    zAxisPosition = gcodeMove["gcode_position"][2]
                    currentLayer = int(math.ceil(
                        (zAxisPosition - firstLayerHeight) / layerHeight + 1
                    ))
                else:
                    # If the print hasn't started yet, the layer height is 0.
                    currentLayer = 0
            if currentLayer == -1:
                Sentry.Error("Client", "GetCurrentLayerInfo failed to get a current layer count.")
                return (0,0)

            # Sanity check.
            currentLayer = min(currentLayer, totalLayers)

            return (currentLayer, totalLayers)
        except Exception as e:
            Sentry.Exception("GetCurrentLayerInfo exception. ", e)
        return (0,0)


    # ! Interface Function ! The entire interface must change if the function is changed.
    # Returns True if the printing timers (notifications and gadget) should be running, which is only the printing state. (not even paused)
    # False if the printer state is anything else, which means they should stop.
    def ShouldPrintingTimersBeRunning(self):
        stats = self._GetCurrentPrintStats()
        if stats is None:
            Sentry.Warn("Client", "ShouldPrintingTimersBeRunning failed to get current state.")
            return True
        # For moonraker, printing is the only state we want to allow the timers to run in.
        # All other states will resume them when moved out of.
        return stats["state"] == "printing"


    # ! Interface Function ! The entire interface must change if the function is changed.
    # If called while the print state is "Printing", returns True if the print is currently in the warm-up phase. Otherwise False
    def IsPrintWarmingUp(self):
        # For moonraker, we have found that if the print_stats reports a state of "printing"
        # but the "print_duration" is still 0, it means we are warming up. print_duration is the time actually spent printing
        # so it doesn't increment while the system is heating.
        result = MoonrakerClient.Get().SendJsonRpcRequest("printer.objects.query",
        {
            "objects": {
                "print_stats": None
            }
        })
        # Use the common helper function.
        return self.CheckIfPrinterIsWarmingUp_WithPrintStats(result)


    #
    # Helpers
    #

    def _InitPrintStateForFreshConnect(self):
        # Get the current state
        stats = self._GetCurrentPrintStats()
        if stats is None:
            Sentry.Error("Client", "Moonraker client init sync failed to get the printer state.")
            return

        # What this logic is trying to do is re-sync the notification handler with the current state.
        # The only tricky part is if there's an on-going print that we aren't tracking, we need to restore
        # the state as well as possible to get notifications in sync.
        state = stats["state"]
        fileName_CanBeNone = stats["filename"]
        totalDurationFloatSec_CanBeNone = stats["total_duration"] # Use the total duration
        Sentry.Info("Client", "Printer state at socket connect is: "+state)
        self._updatePrinterName()
        self.NotificationHandler.OnRestorePrintIfNeeded(state, fileName_CanBeNone, totalDurationFloatSec_CanBeNone)
        if fileName_CanBeNone:
            MoonrakerClient.Get().DownloadFileForProcessing(fileName_CanBeNone)


    # Queries moonraker for the current printer stats.
    # Returns null if the call falls or the resulting object DOESN'T contain at least: filename, state, total_duration, print_duration
    def _GetCurrentPrintStats(self):
        result = MoonrakerClient.Get().SendJsonRpcRequest("printer.objects.query",
        {
            "objects": {
                "print_stats": None
            }
        })
        # Validate
        if result.HasError():
            Sentry.Error("Client", "Moonraker client failed _GetCurrentPrintStats. "+result.GetLoggingErrorStr())
            return None
        res = result.GetResult()
        if "status" not in res or "print_stats" not in res["status"]:
            Sentry.Error("Client", "Moonraker client didn't find status in _GetCurrentPrintStats.")
            return None
        printStats = res["status"]["print_stats"]
        if "state" not in printStats or "filename" not in printStats or "total_duration" not in printStats or "print_duration" not in printStats:
            Sentry.Error("Client", "Moonraker client didn't find required field in _GetCurrentPrintStats. "+json.dumps(printStats))
            return None
        return printStats


    # A common function to check for the "warming up" state.
    # Returns True if the printer is warming up, otherwise False
    def CheckIfPrinterIsWarmingUp_WithPrintStats(self, result):
        # Check the result.
        if result.HasError():
            Sentry.Error("Client", "CheckIfPrinterIsWarmingUp_WithPrintStats failed to query print objects: "+result.GetLoggingErrorStr())
            return False

        try:
            res = result.GetResult()["status"]
            state = res["print_stats"]["state"]
            printDurationSec = res["print_stats"]["print_duration"]
            # This is how we define warming up. The state is printing but the print duration is very low.
            # Print duration only counts while the print is actually running, thus it excludes the warmup period.
            if state == "printing" and printDurationSec < 0.00001:
                return True
            return False
        except Exception as e:
            Sentry.Exception("IsPrintWarmingUp exception. ", e)
        return False


    # Using the result of printer.objects.query with print_stats and virtual_sdcard, this will get the estimated time remaining in the best way possible.
    # If it can be gotten, it's returned as an int.
    # If it fails, it's returns -1
    def GetPrintTimeRemainingEstimateInSeconds_WithPrintStatsVirtualSdCardAndGcodeMoveResult(self, result):
        # This logic is taken from the moonraker docs, that suggest how to find a good ETA
        # https://moonraker.readthedocs.io/en/latest/web_api/#basic-print-status
        #
        # From what we have seen, this is what we ended up with.
        #
        # There are three ways to compute the ETA
        #   1) Read it from the file if the slicer produces it
        #   2) Use the elapsed time and the current % to guess the total time
        #   3) Use the filament stat of how much filament is going to be used vs how much has been used. (mainsail does this)
        #
        # From our testing, it seems that #1 is the most accurate, if it's possible to get.
        # If we can get it, we use it, if not, we fallback to #2.
        #
        try:
            # Ensure the result is valid.
            if result.HasError():
                return -1

            # Validate we have what we need.
            res = result.GetResult()["status"]
            if "print_stats" not in res or "virtual_sdcard" not in res or "gcode_move" not in res:
                Sentry.Error("Client", "GetPrintTimeRemainingEstimateInSeconds_WithPrintStatsAndVirtualSdCardResult passed a result with missing objects")
                return -1

            # If nothing is printing or in the queue, sometimes these values won't be there.
            if "print_duration" not in res["print_stats"] or "filename" not in res["print_stats"] or "progress" not in res["virtual_sdcard"] or "speed_factor" not in res["gcode_move"]:
                return -1

            # Try to get the vars we need.
            # Use the print duration, since that's only the time spent printing (excluding warming up and pause time.)
            printTime = res["print_stats"]["print_duration"]
            filamentUsed = res["print_stats"]["filament_used"]
            fileName = res["print_stats"]["filename"]
            progressFloat = res["virtual_sdcard"]["progress"]
            # The runtime configured speed of the printer currently. Where 1.0 is 100%, 2.0 is 200%
            speedFactorFloat = res["gcode_move"]["speed_factor"]
            inverseSpeedFactorFloat = 1.0/speedFactorFloat
            estimatedPrintTime = FileMetadataCache.Get().GetEstimatedPrintTimeSec(fileName)
            totalFilamentUse = FileMetadataCache.Get().GetEstimatedFilamentUsageMm(fileName)
            def calcTimeLeftWithProgress(printTime, progress): return (printTime / progress) - printTime

            # Can we calculate yet?
            if printTime > 0:
                all = [
                    calcTimeLeftWithProgress(printTime=printTime, progress=progressFloat) if progressFloat is not None else None,
                    calcTimeLeftWithProgress(printTime=printTime, progress=filamentUsed/totalFilamentUse) if filamentUsed is not None and totalFilamentUse > 0 else None,
                    calcTimeLeftWithProgress(printTime=printTime, progress=printTime/estimatedPrintTime) if printTime is not None and estimatedPrintTime > 0 else None,
                ]
                available = list(filter(lambda x: x is not None, all))
                if len(available) > 0:
                    timeLeft = sum(available) / len(available)
                else:
                    timeLeft = estimatedPrintTime - printTime
            else:
                # Rely on slicer
                timeLeft = estimatedPrintTime

            # Before returning, we need to offset by the runtime speed, which will skew based on it.
            # For example, a speed of 200% will reduce the ETA by half.
            return timeLeft * inverseSpeedFactorFloat

        except Exception as e:
            Sentry.Exception("GetPrintTimeRemainingEstimateInSeconds exception while computing ETA. ", e)
        return -1
