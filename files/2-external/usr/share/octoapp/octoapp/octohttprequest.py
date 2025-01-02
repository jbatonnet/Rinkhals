import platform
import requests

from .localip import LocalIpHelper
from .mdns import MDns
from .compat import Compat
from .Proto.PathTypes import PathTypes

class OctoHttpRequest:
    LocalHttpProxyPort = 80
    LocalHttpProxyIsHttps = False
    LocalOctoPrintPort = 5000
    LocalHostAddress = "127.0.0.1"

    @staticmethod
    def SetLocalHttpProxyPort(port):
        OctoHttpRequest.LocalHttpProxyPort = port
    @staticmethod
    def GetLocalHttpProxyPort():
        return OctoHttpRequest.LocalHttpProxyPort

    @staticmethod
    def SetLocalHttpProxyIsHttps(isHttps):
        OctoHttpRequest.LocalHttpProxyIsHttps = isHttps
    @staticmethod
    def GetLocalHttpProxyIsHttps():
        return OctoHttpRequest.LocalHttpProxyIsHttps

    @staticmethod
    def SetLocalOctoPrintPort(port):
        OctoHttpRequest.LocalOctoPrintPort = port
    @staticmethod
    def GetLocalOctoPrintPort():
        return OctoHttpRequest.LocalOctoPrintPort

    @staticmethod
    def SetLocalHostAddress(address):
        OctoHttpRequest.LocalHostAddress = address
    @staticmethod
    def GetLocalhostAddress():
        return OctoHttpRequest.LocalHostAddress


    # Based on the URL passed, this will return PathTypes.Relative or PathTypes.Absolute
    @staticmethod
    def GetPathType(url):
        if url.find("://") != -1:
            # If there is a protocol, it's for sure absolute.
            return PathTypes.Absolute
        # TODO - It might be worth to add some logic to try to detect no protocol hostnames, like test.com/helloworld.
        return PathTypes.Relative

    # The result of a successfully made http request.
    # "successfully made" means we talked to the server, not the the http
    # response is good.
    #
    # FullBodyBuffer defaults to None. But if it's set, it should be used instead of reading from the http response body.
    class Result():
        def __init__(self, result, url, didFallback, fullBodyBuffer=None):
            self.result = result
            self.url:str = url
            self.didFallback:bool = didFallback
            self.fullBodyBuffer = fullBodyBuffer
            self.isZlibCompressed:bool = False
            self.fullBodyBufferPreCompressedSize:int = 0

        @property
        def Result(self):
            return self.result

        @property
        def Url(self):
            return self.url

        @property
        def DidFallback(self):
            return self.didFallback

        @property
        def FullBodyBuffer(self):
            # Defaults to None
            return self.fullBodyBuffer

        @property
        def IsBodyBufferZlibCompressed(self):
            # There must be a buffer and the flag must be set.
            return self.isZlibCompressed and self.fullBodyBuffer is not None

        @property
        def BodyBufferPreCompressSize(self):
            # There must be a buffer
            if self.fullBodyBuffer is None:
                return 0
            return self.fullBodyBufferPreCompressedSize

        # Note the buffer can be bytes or bytearray object!
        # A bytes object is more efficient, but bytearray can be edited.
        def SetFullBodyBuffer(self, buffer, isZlibCompressed:bool = False, preCompressedSize:int = 0):
            self.fullBodyBuffer = buffer
            self.isZlibCompressed = isZlibCompressed
            self.fullBodyBufferPreCompressedSize = preCompressedSize
            if isZlibCompressed and preCompressedSize <= 0:
                raise Exception("The pre-compression full size must be set if the buffer is compressed.")

    # # Handles making all http calls out of the plugin to OctoPrint or other services running locally on the device or
    # # even on other devices on the LAN.
    # #
    # # The main point of this function is to abstract away the logic around relative paths, absolute URLs, and the fallback logic
    # # we use for different ports. See the comments in the function for details.
    # @staticmethod
    # def MakeHttpCallOctoStreamHelper(logger, httpInitialContext, method, headers, data=None):
    #     # Get the vars we need from the octostream initial context.
    #     path = OctoStreamMsgBuilder.BytesToString(httpInitialContext.Path())
    #     if path is None:
    #         raise Exception("Http request has no path field in open message.")
    #     pathType = httpInitialContext.PathType()

    #     # Make the common call.
    #     return OctoHttpRequest.MakeHttpCall(logger, path, pathType, method, headers, data)

    # allowRedirects should be false for all proxy calls. If it's true, then the content returned might be from a redirected URL and the actual URL will be incorrect.
    # Instead, the system needs to handle the redirect 301 or 302 call as normal, sending it back to the caller, and allowing them to follow the redirect if needed.
    # The X-Forwarded-Host header will tell the OctoPrint server the correct place to set the location redirect header.
    # However, for calls that aren't proxy calls, things like local snapshot requests and such, we want to allow redirects to be more robust.
    @staticmethod
    def MakeHttpCall(logger, pathOrUrl, pathOrUrlType, method, headers, data=None, allowRedirects=False):
        # First of all, we need to figure out what the URL is. There are two options
        #
        # 1) Absolute URLs
        # These are the easiest, because we just want to make a request to exactly what the absolute URL is. These are used
        # when the OctoPrint portal is trying to make an local LAN http request to the same device or even a different device.
        # For these to work properly on a remote browser, the OctoApp service will detect and convert the URLs in to encoded relative
        # URLs for the portal. This ensures when the remote browser tries to access the HTTP endpoint, it will hit OctoApp. The OctoApp
        # server detects the special relative URL, decodes the absolute URL, and sends that in the OctoMessage as "AbsUrl". For these URLs we just try
        # to hit them and we take whatever we get, we don't care if fails or not.
        #
        # 2) Relative Urls
        # These Urls are the most common, standard URLs. The browser makes the relative requests to the same hostname:port as it's currently
        # on. However, for our setup its a little more complex. The issue is the OctoApp plugin not knowing how the user's system is setup.
        # The plugin can with 100% certainty query and know the port OctoPrint's http server is running on directly. So we do that to know exactly what
        # OctoPrint server to talk to. (consider there might be multiple instances running on one device.)
        #
        # But, the other most common use case for http calls are the webcam streams to mjpegstreamer. This is the tricky part. There are two ways it can be
        # setup. 1) the webcam stream uses an absolute local LAN url with the ip and port. This is covered by the absolute URL system above. 2) The webcam stream
        # uses a relative URL and haproxy handles detecting the webcam path to send it to the proper mjpegstreamer instance. This is the tricky one, because we can't
        # directly query or know what the correct port for haproxy or mjpegstreamer is. We could look at the configs, but a user might not setup the configs in the
        # standard places. So to fix the issue, we use logic in the frontend JS to determine if a web browser is connecting locally, and if so what the port is. That gives
        # use a reliable way to know what port haproxy is running on. It sends that to the plugin, which is then given here as `localHttpProxyPort`.
        #
        # The last problem is knowing which calls should be sent to OctoPrint directly and which should be sent to haproxy. We can't rely on any URL matching, because
        # the user can setup the webcam stream to start with anything they want. So the method we use right now is to simply always request to OctoPrint first, and if we
        # get a 404 back try the haproxy. This adds a little bit of unneeded overhead, but it works really well to cover all of the cases.

        # Setup the protocol we need to use for the http proxy. We need to use the same protocol that was detected.
        httpProxyProtocol = "http://"
        if OctoHttpRequest.LocalHttpProxyIsHttps:
            httpProxyProtocol = "https://"

        # Figure out the main and fallback url.
        url = ""
        fallbackUrl = None
        fallbackWebcamUrl = None
        fallbackLocalIpOctoPrintPortSuffix = None
        fallbackLocalIpHttpProxySuffix = None
        if pathOrUrlType == PathTypes.Relative:

            # Note!
            # These URLs are very closely related to the logic in the OctoWebStreamWsHelper class and should stay in sync!

            # Fluidd seems to have a bug where the default webcam streaming value is .../webcam?action...
            # but crowsnest will send a redirect to .../webcam/?action...
            # To prevent that redirect hop every time the camera is loaded, we will try to correct it.
            # We should remove this eventually when the bug has been fixed for long enough.
            if pathOrUrl.startswith("/webcam?action"):
                pathOrUrl = pathOrUrl.replace("/webcam?action", "/webcam/?action")

            # The main URL is directly to this OctoPrint instance
            # This URL will only every be http, it can't be https.
            url = "http://" + OctoHttpRequest.LocalHostAddress + ":" + str(OctoHttpRequest.LocalOctoPrintPort) + pathOrUrl

            # The fallback URL is to where we think the http proxy port is.
            # For this address, we need set the protocol correctly depending if the client detected https
            # or not.
            fallbackUrl = httpProxyProtocol + OctoHttpRequest.LocalHostAddress + ":" +str(OctoHttpRequest.LocalHttpProxyPort) + pathOrUrl

            # Special case for systems with an API router (only moonraker as of now)
            # If the API router wants to redirect the URL, it must be tried first, since the default URL
            # might also work, but might be incorrect.
            if Compat.HasApiRouterHandler():
                reroutedUrl = Compat.GetApiRouterHandler().MapRelativePathToAbsolutePathIfNeeded(pathOrUrl, "http://")
                if reroutedUrl is not None:
                    # If we got a redirect URL, make sure it's the first URL, and use the default URL as the fallback.
                    fallbackUrl = url
                    url = reroutedUrl

            # If the two URLs above don't work, we will try to call the server using the local IP since the server might not be bound to localhost.
            # Note we only build the suffix part of the string here, because we don't want to do the local IP detection if we don't have to.
            # Also note this will only work for OctoPrint pages.
            # This case only seems to apply to OctoPrint instances running on Windows.
            fallbackLocalIpOctoPrintPortSuffix = ":" + str(OctoHttpRequest.LocalOctoPrintPort) + pathOrUrl
            fallbackLocalIpHttpProxySuffix =  ":" + str(OctoHttpRequest.LocalHttpProxyPort) + pathOrUrl

            # If all else fails, and because this logic isn't perfect, yet, we will also try to fallback to the assumed webcam port.
            # This isn't a great thing though, because more complex webcam setups use different ports and more than one instance.
            # Only setup this URL if the path starts with /webcam, which again isn't a great indicator because it can change per user.
            webcamUrlIndicator = "/webcam"
            pathLower = pathOrUrl.lower()
            if pathLower.startswith(webcamUrlIndicator):
                # We need to remove the /webcam* since we are trying to talk directly to mjpg-streamer
                # We do want to keep the second / though.
                secondSlash = pathOrUrl.find("/", 1)
                if secondSlash != -1:
                    webcamPath = pathOrUrl[secondSlash:]
                    fallbackWebcamUrl = "http://" + OctoHttpRequest.LocalHostAddress + ":8080" + webcamPath

        elif pathOrUrlType == PathTypes.Absolute:
            # For absolute URLs, only use the main URL and set it be exactly what was requested.
            url = pathOrUrl

            # The only exception to this is for mdns local domains. So here's the hard part. On most systems, mdns works for the
            # requests lib and everything will work. However, on some systems mDNS isn't support and the call will fail. On top of that, mDNS
            # is super flakey, and it will randomly stop working often. For both of those reasons, we will check if we find a local address, and try
            # to resolve it manually. Our logic has a cache and local disk backup, so if mDNS is being flakey, our logic will recover it.
            localResolvedUrl = MDns.Get().TryToResolveIfLocalHostnameFound(url)
            if localResolvedUrl is not None:
                # The function will only return back the full URL if a local hostname was found and it was able to resolve to an IP.
                # In this case, use our local IP result first, and then set the requested as the fallback.
                # This should be better, because it will use our already resolved IP url first, and if for some reason it fails, we still try the
                # OG URL.
                fallbackUrl = url
                url = localResolvedUrl
        else:
            raise Exception("Http request got a message with an unknown path type. "+str(pathOrUrlType))

        # Ensure if there's no data we don't set it. Sometimes our json message parsing will leave an empty
        # bytearray where it should be None.
        if data is not None and len(data) == 0:
            data = None

        # All of the users of MakeHttpCall don't handle compressed responses.
        # For OctoStream request, this header is already set in GatherRequestHeaders, but for things like webcam snapshot requests and such, it's not set.
        # Beyond nothing handling compressed responses, since the call is almost always over localhost, there's no point in doing compression, since it mainly just helps in transmit less data.
        # Thus, for all calls, we set the Accept-Encoding to identity, telling the server no response compression is allowed.
        # This is important for somethings like camera-streamer, which will use gzip by default. (which is also silly, because it's sending jpegs and jmpeg streams?)
        if headers is None:
            headers = {}
        headers["Accept-Encoding"] = "identity"

        # First, try the main URL.
        # For the first main url, we set the main response to None and is fallback to False.
        ret = OctoHttpRequest.MakeHttpCallAttempt(logger, "Main request", method, url, headers, data, None, False, fallbackUrl, allowRedirects)
        # If the function reports the chain is done, the next fallback URL is invalid and we should always return
        # whatever is in the Response, even if it's None.
        if ret.IsChainDone:
            return ret.Result

        # We keep track of the main response, if all future fallbacks fail. (This can be None)
        mainResult = ret.Result

        # Main failed, try the fallback, which should be the http proxy.
        ret = OctoHttpRequest.MakeHttpCallAttempt(logger, "Http proxy fallback", method, fallbackUrl, headers, data, mainResult, True, fallbackLocalIpHttpProxySuffix, allowRedirects)
        # If the function reports the chain is done, the next fallback URL is invalid and we should always return
        # whatever is in the Response, even if it's None.
        if ret.IsChainDone:
            return ret.Result

        # Try to get the local IP of this device and try to use the same ports with it.
        # We build these full URLs after the failures so we don't try to get the local IP on every call.
        localIp = LocalIpHelper.TryToGetLocalIp()

        # With the local IP, first try to use the http proxy URL, since it's the most likely to be bound to the public IP and not firewalled.
        # It's important we use the right http proxy protocol with the http proxy port.
        localIpFallbackUrl = httpProxyProtocol + localIp + fallbackLocalIpHttpProxySuffix
        ret = OctoHttpRequest.MakeHttpCallAttempt(logger, "Local IP Http Proxy Fallback", method, localIpFallbackUrl, headers, data, mainResult, True, fallbackLocalIpOctoPrintPortSuffix, allowRedirects)
        # If the function reports the chain is done, the next fallback URL is invalid and we should always return
        # whatever is in the Response, even if it's None.
        if ret.IsChainDone:
            return ret.Result

        # Now try the OcotoPrint direct port with the local IP.
        localIpFallbackUrl = "http://" + localIp + fallbackLocalIpOctoPrintPortSuffix
        ret = OctoHttpRequest.MakeHttpCallAttempt(logger, "Local IP fallback", method, localIpFallbackUrl, headers, data, mainResult, True, fallbackWebcamUrl, allowRedirects)
        # If the function reports the chain is done, the next fallback URL is invalid and we should always return
        # whatever is in the Response, even if it's None.
        if ret.IsChainDone:
            return ret.Result

        # If all others fail, try the hardcoded webcam URL.
        # Note this has to be last, because there commonly isn't a fallbackWebcamUrl, so it will stop the
        # chain of other attempts.
        ret = OctoHttpRequest.MakeHttpCallAttempt(logger, "Webcam hardcode fallback", method, fallbackWebcamUrl, headers, data, mainResult, True, None, allowRedirects)
        # No matter what, always return the result now.
        return ret.Result

    # Returned by a single http request attempt.
    # IsChainDone - indicates if the fallback chain is done and the response should be returned
    # Result - is the final result. Note the result can be unsuccessful or even `None` if everything failed.
    class AttemptResult():
        def __init__(self, isChainDone, result):
            self.isChainDone = isChainDone
            self.result = result

        @property
        def IsChainDone(self):
            return self.isChainDone

        @property
        def Result(self):
            return self.result

    # This function should always return a AttemptResult object.
    @staticmethod
    def MakeHttpCallAttempt(logger, attemptName, method, url, headers, data, mainResult, isFallback, nextFallbackUrl, allowRedirects:bool = False):
        response = None
        try:
            # Try to make the http call.
            #
            # Note we use a long timeout because some api calls can hang for a while.
            # For example when plugins are installed, some have to compile which can take some time.
            #
            # See the note about allowRedirects above MakeHttpCall.
            #
            # It's important to set the `verify` = False, since if the server is using SSL it's probably a self-signed cert.
            #
            # We always set stream=True because we use the iter_content function to read the content.
            # This means that response.content will not be valid and we will always use the iter_content. But it also means
            # iter_content will ready into memory on demand and throw when the stream is consumed. This is important, because
            # our logic relies on the exception when the stream is consumed to end the http response stream.
            response = requests.request(method, url, headers=headers, data=data, timeout=1800, allow_redirects=allowRedirects, stream=True, verify=False)
        except Exception as e:
            logger.info(attemptName + " http URL threw an exception: "+str(e))

        # We have seen when making absolute calls to some lower end devices, like external IP cameras, they can't handle the number of headers we send.
        # So if any call fails due to 431 (headers too long) we will retry the call with no headers at all. Note this will break most auth, but
        # most of these systems don't need auth headers or anything.
        # Strangely this seems to only work on Linux, where as on Windows the request.request function will throw a 'An existing connection was forcibly closed by the remote host' error.
        # Thus for windows, if the response is ever null, try again. This isn't ideal, but most windows users are just doing dev anyways.
        if response is not None and response.status_code == 431 or (platform.system() == "Windows" and response is None):
            if response is not None and response.status_code == 431:
                logger.info(url + " http call returned 431, too many headers. Trying again with no headers.")
            else:
                logger.warn(url + " http call returned no response on Windows. Trying again with no headers.")
            try:
                response = requests.request(method, url, headers={}, data=data, timeout=1800, allow_redirects=False, stream=True, verify=False)
            except Exception as e:
                logger.info(attemptName + " http NO HEADERS URL threw an exception: "+str(e))

        # Check if we got a valid response.
        if response is not None and response.status_code != 404:
            # We got a valid response, we are done.
            # Return true and the result object, so it can be returned.
            return OctoHttpRequest.AttemptResult(True, OctoHttpRequest.Result(response, url, isFallback))

        # Check if we have another fallback URL to try.
        if nextFallbackUrl is not None:
            # We have more fallbacks to try.
            # Return false so we keep going, but also return this response if we had one. This lets
            # use capture the main result object, so we can use it eventually if all fallbacks fail.
            return OctoHttpRequest.AttemptResult(False, OctoHttpRequest.Result(response, url, isFallback))

        # We don't have another fallback, so we need to end this.
        if mainResult is not None:
            # If we got something back from the main try, always return it (we should only get here on a 404)
            logger.info(attemptName + " failed and we have no more fallbacks. Returning the main URL response.")
            return OctoHttpRequest.AttemptResult(True, mainResult)
        else:
            # Otherwise return the failure.
            logger.error(attemptName + " failed and we have no more fallbacks. We DON'T have a main response.")
            return OctoHttpRequest.AttemptResult(True, None)
