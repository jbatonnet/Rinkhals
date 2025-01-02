import json
import logging

from octoapp.compat import Compat
from octoapp.sentry import Sentry

# The context class we return if we want to handle this request.
class ResponseHandlerContext:
    # Possible context types.
    MainsailConfig = 1
    CameraStreamerWebRTCSdp = 2
    def __init__(self, t:int) -> None:
        self.Type = t

# Implements the platform specific logic for web request response handler.
# This does a few things:
#    1) It will fix up the mainsail config to not make the website prompt for printer IP addresses if there's multiple moonraker backend instances setup.
#    2) For camera-streamer WebRTC calls, it changes the local IP address to the public IP address, which then makes WebRTC connectable.
class MoonrakerWebRequestResponseHandler:


    # The static instance.
    _Instance = None


    @staticmethod
    def Init():
        MoonrakerWebRequestResponseHandler._Instance = MoonrakerWebRequestResponseHandler()
        Compat.SetWebRequestResponseHandler(MoonrakerWebRequestResponseHandler._Instance)


    @staticmethod
    def Get():
        return MoonrakerWebRequestResponseHandler._Instance


    # !! Interface Function !! This implementation must not change!
    # Given a URL (which can be absolute or relative) check if we might want to edit the response.
    # If no, then None is returned and the call is handled as normal.
    # If yes, some kind of context object must be returned, which will be given back to us.
    #     If yes, the entire response will be read as one full byte buffer, and given for us to deal with.
    def CheckIfResponseNeedsToBeHandled(self, uri:str) -> ResponseHandlerContext:
        uri = uri.lower()
        # Handle Mainsail configs
        if uri.endswith("/config.json"):
            return ResponseHandlerContext(ResponseHandlerContext.MainsailConfig)
        # Handle camera-streamer webrtc calls.
        # The path will look something like this:
        #   /webcam/webrtc
        # But if there are multiple cameras setup, the /webcam/ part might change.
        # if uri.endswith("/webrtc"):
        #     return ResponseHandlerContext(ResponseHandlerContext.CameraStreamerWebRTCSdp)
        return None


    # !! Interface Function !! This implementation must not change!
    # If we returned a context above in CheckIfResponseNeedsToBeHandled, this will be called after the web request is made
    # and the body is fully read. The entire body will be read into the bodyBuffer.
    # We are able to modify the bodyBuffer as we wish or not, but we must return the full bodyBuffer back to be returned.
    def HandleResponse(self, contextObject:ResponseHandlerContext, bodyBuffer: bytes) -> bytes:
        try:
            if contextObject.Type == ResponseHandlerContext.MainsailConfig:
                return self._HandleMainsailConfig(bodyBuffer)
            elif contextObject.Type == ResponseHandlerContext.CameraStreamerWebRTCSdp:
                return self._HandleWebRtcSdpResponse(bodyBuffer)
            else:
                Sentry.Error("Web request", "MoonrakerWebRequestResponseHandler tired to handle a context with an unknown Type? "+str(contextObject.Type))
        except Exception as e:
            Sentry.Exception("MainsailConfigHandler exception while handling mainsail config.", e)
        return bodyBuffer


    def _HandleMainsailConfig(self, bodyBuffer:bytes) -> bytes:
        #
        # Note that we identify this file just by dont a .endsWith("/config.json") to the URL. Thus other things could match it
        # and we need to be careful to only edit it if we find what we expect.
        #
        # Force the config to always point at "moonraker", which will force mainsail to always connect to the default instance of
        # moonraker running on the system at /websocket. Otherwise, if multiple instances are setup via Kiauh, this will be set to browser
        # and it will give the user a pop-up when they first load the portal.
        #
        # Right now we can't do anything else, because moonraker only allows the user to set custom hostname and ports, not paths, to call
        # the different websockets at. But in the future, we could look into redirecting the websocket and known moonraker http api paths to the
        # known moonraker instance running with this octoapp. instance.
        mainsailConfig = json.loads(bodyBuffer.decode("utf8"))
        if "instancesDB" in mainsailConfig:
            # Set mainsail and be sure to clear our any instances.
            mainsailConfig["instancesDB"] = "moonraker"
            mainsailConfig["instances"] = []
            # Older versions struggle to connect to the websocket if we don't set this port as well
            # We can always set it to 443, because we will always have SSL.
            mainsailConfig["port"] = 443
        return json.dumps(mainsailConfig, indent=4).encode("utf8")


    def _HandleWebRtcSdpResponse(self, bodyBuffer:bytes) -> bytes:
        #
        # As of Crowsnest 4.0, it now supports camera-stream (like OctoPrint) which supports WebRTC.
        # This is an obvious winner in camera streaming, because WebRTC is much better than mjpeg streaming.
        # But, the SDP returned uses the local IP address, not the WAN IP address. Thus from outside the network,
        # the SDP fails.
        # TODO
        txt = bodyBuffer.decode("utf8")
        return txt.encode("utf8")
