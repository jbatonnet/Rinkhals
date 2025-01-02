import logging
import os
import json

from .sentry import Sentry
from .octohttprequest import OctoHttpRequest
from .requestsutils import RequestsUtils

#
# A platform agnostic definition of a webcam stream.
#
class WebcamSettingItem:

    # The snapshotUrl and streamUrl can be relative or absolute.
    #
    #  name must exist.
    #  snapshotUrl OR streamUrl can be None if the values aren't available, but not both.
    #  flipHBool & flipVBool & rotationInt must exist.
    #  rotationInt must be 0, 90, 180, or 270
    def __init__(self, name:str = "", snapshotUrl:str = "", streamUrl:str = "", flipHBool:bool = False, flipVBool:bool = False, rotationInt:int = 0):
        self.Name = name
        self.SnapshotUrl = snapshotUrl
        self.StreamUrl = streamUrl
        self.FlipH = flipHBool
        self.FlipV = flipVBool
        self.Rotation = rotationInt

    def Validate(self) -> bool:
        if self.Name is None or len(self.Name) == 0:
            Sentry.Error("WEBCAM_HELER", f"Name value in WebcamSettingItem is None or empty. {self.StreamUrl}")
            return False
        if self.Rotation is None or (self.Rotation != 0 and self.Rotation != 90 and self.Rotation != 180 and self.Rotation != 270):
            Sentry.Error("WEBCAM_HELER", f"Rotation value in WebcamSettingItem is an invalid int. {self.Name} - {self.Rotation}")
            return False
        if (self.SnapshotUrl is None or len(self.SnapshotUrl) == 0) and (self.StreamUrl is None or len(self.StreamUrl) == 0):
            Sentry.Error("WEBCAM_HELER", f"Snapshot and StreamUrl values in WebcamSettingItem are none or empty {self.Name}")
            return False
        if self.FlipH is None:
            Sentry.Error("WEBCAM_HELER", f"FlipH value in WebcamSettingItem is None {self.Name}")
            return False
        self.FlipH = bool(self.FlipH)
        if self.FlipV is None:
            Sentry.Error("WEBCAM_HELER", f"FlipV value in WebcamSettingItem is None {self.Name}")
            return False
        self.FlipV = bool(self.FlipV)
        return True


# The point of this class is to abstract the logic that needs to be done to reliably get a webcam snapshot and stream from many types of
# printer setups. The main entry point is GetSnapshot() which will try a number of ways to get a snapshot from whatever camera system is
# setup. This includes USB based cameras, external IP based cameras, and OctoPrint instances that don't have a snapshot URL defined.
class WebcamHelper:

    # A header we apply to all snapshot and webcam streams so the client can get the correct transforms the user has setup.
    c_OeWebcamTransformHeaderKey = "x-oe-webcam-transform"

    # Logic for a static singleton
    _Instance = None


    @staticmethod
    def Init(webcamPlatformHelperInterface, pluginDataFolderPath):
        WebcamHelper._Instance = WebcamHelper(webcamPlatformHelperInterface, pluginDataFolderPath)


    @staticmethod
    def Get():
        return WebcamHelper._Instance


    def __init__(self, webcamPlatformHelperInterface, pluginDataFolderPath:str):
        self.WebcamPlatformHelperInterface = webcamPlatformHelperInterface
        self.SettingsFilePath = os.path.join(pluginDataFolderPath, "webcam-settings.json")
        self.DefaultCameraName = None
        self._LoadDefaultCameraName()


    # Returns the snapshot URL from the settings.
    # Can be None if there is no snapshot URL set in the settings!
    # This URL can be absolute or relative.
    def GetSnapshotUrl(self, cameraName:str = None):
        obj = self._GetWebcamSettingObj(cameraName)
        if obj is None:
            return None
        return obj.SnapshotUrl


    # Returns the mjpeg stream URL from the settings.
    # Can be None if there is no URL set in the settings!
    # This URL can be absolute or relative.
    def GetWebcamStreamUrl(self, cameraName:str = None):
        obj = self._GetWebcamSettingObj(cameraName)
        if obj is None:
            return None
        return obj.StreamUrl


    # Returns if flip H is set in the settings.
    def GetWebcamFlipH(self, cameraName:str = None):
        obj = self._GetWebcamSettingObj(cameraName)
        if obj is None:
            return None
        return obj.FlipH


    # Returns if flip V is set in the settings.
    def GetWebcamFlipV(self, cameraName:str = None):
        obj = self._GetWebcamSettingObj(cameraName)
        if obj is None:
            return None
        return obj.FlipV


    # Returns if rotate 90 is set in the settings.
    def GetWebcamRotation(self, cameraName:str = None):
        obj = self._GetWebcamSettingObj(cameraName)
        if obj is None:
            return None
        return obj.Rotation


    # Given a set of request headers, this determine if this is a special Oracle call indicating it's a snapshot or webcam stream.
    def IsSnapshotOrWebcamStreamOracleRequest(self, requestHeadersDict):
        return self.IsSnapshotOracleRequest(requestHeadersDict) or self.IsWebcamStreamOracleRequest(requestHeadersDict)


    # Check if the special header is set, indicating this is a snapshot request.
    def IsSnapshotOracleRequest(self, requestHeadersDict):
        return "oe-snapshot" in requestHeadersDict


    # Check if the special header is set, indicating this is a webcam stream request.
    def IsWebcamStreamOracleRequest(self, requestHeadersDict):
        return "oe-webcamstream" in requestHeadersDict

    # If the header is set to specify a camera name, this returns it. Otherwise None
    def GetOracleRequestCameraName(self, requestHeadersDict):
        if "oe-webcam-name" in requestHeadersDict:
            return requestHeadersDict["oe-webcam-name"]
        return None

    # Called by the OctoWebStreamHelper when a Oracle snapshot or webcam stream request is detected.
    # It's important that this function returns a OctoHttpRequest that's very similar to what the default MakeHttpCall function
    # returns, to ensure the rest of the octostream http logic can handle the response.
    def MakeSnapshotOrWebcamStreamRequest(self, httpInitialContext, method, sendHeaders, uploadBuffer) -> OctoHttpRequest.Result:
        cameraNameOpt = self.GetOracleRequestCameraName(sendHeaders)
        if self.IsSnapshotOracleRequest(sendHeaders):
            return self.GetSnapshot(cameraNameOpt)
        elif self.IsWebcamStreamOracleRequest(sendHeaders):
            return self.GetWebcamStream(cameraNameOpt)
        else:
            raise Exception("Webcam helper MakeSnapshotOrWebcamStreamRequest was called but the request didn't have the oracle headers?")


    # Tries to get a webcam stream from the system using the webcam stream URL or falling back to the passed path.
    # Returns a OctoHttpResult on success and None on failure.
    #
    # On failure, this returns None. Returning None will fail out the request.
    # On success, this will return a valid OctoHttpRequest.
    def GetWebcamStream(self, cameraName:str = None) -> OctoHttpRequest.Result:
        # Wrap the entire result in the add transform function, so on success the header gets added.
        return self._AddOeWebcamTransformHeader(self._GetWebcamStreamInternal(cameraName), cameraName)


    def _GetWebcamStreamInternal(self, cameraName:str) -> OctoHttpRequest.Result:
        # Try to get the URL from the settings.
        webcamStreamUrl = self.GetWebcamStreamUrl(cameraName)
        if webcamStreamUrl is not None:
            # Try to make a standard http call with this stream url
            # Use use this HTTP call helper system because it might be somewhat tricky to know
            # Where to actually make the webcam request in terms of IP and port.
            # We use the allow redirects flag to make the API more robust, since some webcam images might need that.
            #
            # Whatever this returns, the rest of the request system will handle it, since it's expecting the OctoHttpRequest object
            return OctoHttpRequest.MakeHttpCall(webcamStreamUrl, OctoHttpRequest.GetPathType(webcamStreamUrl), "GET", {}, allowRedirects=True)

        # If we can't get the webcam stream URL, return None to fail out the request.
        return None


    # Tries to get a snapshot from the system using the snapshot URL or falling back to the mjpeg stream.
    # Returns a OctoHttpResult on success and None on failure.
    #
    # On failure, this returns None. Returning None will fail out the request.
    # On success, this will return a valid OctoHttpRequest that's fully filled out. The stream will always already be fully read, and will be FullBodyBuffer var.
    def GetSnapshot(self, cameraName:str = None) -> OctoHttpRequest.Result:
        # Wrap the entire result in the _EnsureJpegHeaderInfo function, so ensure the returned snapshot can be used by all image processing libs.
        # Wrap the entire result in the add transform function, so on success the header gets added.
        return self._AddOeWebcamTransformHeader(self._EnsureJpegHeaderInfo(self._GetSnapshotInternal(cameraName)), cameraName)


    def _GetSnapshotInternal(self, cameraName:str) -> OctoHttpRequest.Result:
        # First, try to get the snapshot using the string defined in settings.
        snapshotUrl = self.GetSnapshotUrl(cameraName)
        if snapshotUrl is not None:
            # Try to make a standard http call with this snapshot url
            # Use use this HTTP call helper system because it might be somewhat tricky to know
            # Where to actually make the webcam request in terms of IP and port.
            # We use the allow redirects flag to make the API more robust, since some webcam images might need that.
            Sentry.Debug("Webcam Helper", "Trying to get a snapshot using url: %s" % snapshotUrl)
            octoHttpResult = OctoHttpRequest.MakeHttpCall(snapshotUrl, OctoHttpRequest.GetPathType(snapshotUrl), "GET", {}, allowRedirects=True)
            # If the result was successful, we are done.
            if octoHttpResult is not None and octoHttpResult.Result is not None and octoHttpResult.Result.status_code == 200:
                return octoHttpResult

        # If getting the snapshot from the snapshot URL fails, try getting a single frame from the mjpeg stream
        streamUrl = self.GetWebcamStreamUrl()
        if streamUrl is None:
            Sentry.Debug("Webcam Helper", "Snapshot helper failed to get a snapshot from the snapshot URL, but we also don't have a stream URL.")
            return None
        return self._GetSnapshotFromStream(streamUrl)


    def _GetSnapshotFromStream(self, url) -> OctoHttpRequest.Result:
        try:
            # Try to connect the the mjpeg stream using the http helper class.
            # This is required because knowing the port to connect to might be tricky.
            # We use the allow redirects flag to make the API more robust, since some webcam images might need that.
            Sentry.Debug("Webcam Helper", "_GetSnapshotFromStream - Trying to get a snapshot using THE STREAM URL: %s" % url)
            octoHttpResult = OctoHttpRequest.MakeHttpCall(url, OctoHttpRequest.GetPathType(url), "GET", {}, allowRedirects=True)
            if octoHttpResult is None or octoHttpResult.Result is None:
                Sentry.Debug("Webcam Helper", "_GetSnapshotFromStream - Failed to make web request.")
                return None

            # Check for success.
            response = octoHttpResult.Result
            if response is None or response.status_code != 200:
                if response is None:
                    Sentry.Info("Webcam Helper", "Snapshot fallback failed due to the http call having no response object.")
                else:
                    Sentry.Info("Webcam Helper", "Snapshot fallback failed due to the http call having a bad status: "+str(response.status_code))
                return None

            # Hold the entire response in a with block, so that we we leave it will be cleaned up, since it's most likely a streaming stream.
            with response:
                # We expect this to be a multipart stream if it's going to be a mjpeg stream.
                isMultipartStream = False
                contentTypeLower = ""
                for name in response.headers:
                    nameLower = name.lower()
                    if nameLower == "content-type":
                        contentTypeLower = response.headers[name].lower()
                        if contentTypeLower.startswith("multipart/"):
                            isMultipartStream = True
                        break

                # If this isn't a multipart stream, get out of here.
                if isMultipartStream is False:
                    Sentry.Info("Webcam Helper", "Snapshot fallback failed not correct content type: "+str(contentTypeLower))
                    return None

                # Try to read some of the stream, so we can find the content type and the size of this first frame.
                # We use the raw response, so we can control directly how much we read.
                dataBuffer = response.raw.read(300)
                if dataBuffer is None:
                    Sentry.Info("Webcam Helper", "Snapshot fallback failed no data returned.")
                    return None

                # Decode the headers
                # Example --boundarydonotcross\r\nContent-Type: image/jpeg\r\nContent-Length: 48861\r\nX-Timestamp: 2122192.753042\r\n\r\n\x00!AVI1\x00\x01...
                #      or \r\n--boundarydonotcross\r\nContent-Type: image/jpeg\r\nContent-Length: 48861\r\nX-Timestamp: 2122192.753042\r\n\r\n\x00!AVI1\x00\x01...
                #      or boundarydonotcross\r\nContent-Type: image/jpeg\r\nContent-Length: 48861\r\nX-Timestamp: 2122192.753042\r\n\r\n\x00!AVI1\x00\x01...
                headerStr = dataBuffer.decode(errors="ignore")

                # Find out how long the headers are. The \r\n\r\n sequence ends the headers.
                endOfAllHeadersMatch = "\r\n\r\n"
                endOfHeaderMatch = "\r\n"
                headerStrSize = headerStr.find(endOfAllHeadersMatch)
                if headerStrSize == -1:
                    Sentry.Info("Webcam Helper", "Snapshot fallback failed no end of headers found.")
                    return None

                # Add 4 bytes for the \r\n\r\n end of header sequence.
                headerStrSize += 4

                # Try to find the size of this chunk.
                frameSizeInt = 0
                contentType = None
                headers = headerStr.split(endOfHeaderMatch)
                for header in headers:
                    headerLower = header.lower()
                    if headerLower.startswith("content-type"):
                        # We found the content-length header!
                        p = header.split(':')
                        if len(p) == 2:
                            contentType = p[1].strip()

                    if headerLower.startswith("content-length"):
                        # We found the content-length header!
                        p = header.split(':')
                        if len(p) == 2:
                            frameSizeInt = int(p[1].strip())

                if frameSizeInt == 0 or contentType is None:
                    if frameSizeInt == 0:
                        Sentry.Info("Webcam Helper", "Snapshot fallback failed to find frame size.")
                    if contentType is None:
                        Sentry.Info("Webcam Helper", "Snapshot fallback failed to find the content type.")
                    return None
                Sentry.Debug("Webcam Helper", "Image found in webcam stream. Size: %s, Type: %s" % (str(frameSizeInt), str(contentType)))

                # Read the entire first image into the buffer.
                totalDesiredBufferSize = frameSizeInt + headerStrSize
                toRead = totalDesiredBufferSize - len(dataBuffer)
                if toRead > 0:
                    data = response.raw.read(toRead)
                    if data is None:
                        Sentry.Error("Webcam Helper", "_GetSnapshotFromStream failed to read the rest of the image buffer.")
                        return None
                    dataBuffer += data

                # Since this is a stream, ideally we close it as soon as possible to not waste resources.
                # Otherwise this will be auto closed when the function leaves, since we are using the with: scope
                try:
                    response.close()
                except Exception:
                    pass

                # If we got extra data trim it.
                # This shouldn't happen, but just incase the api changes.
                if len(dataBuffer) > totalDesiredBufferSize:
                    dataBuffer = dataBuffer[:totalDesiredBufferSize]

                # Check we got what we wanted.
                if len(dataBuffer) != totalDesiredBufferSize:
                    Sentry.Error("Webcam Helper", "Snapshot callback failed, the data read loop didn't produce the expected data size. desired: "+str(totalDesiredBufferSize)+", got: "+str(len(dataBuffer)))
                    return None

                # Get only the jpeg buffer
                imageBuffer = dataBuffer[headerStrSize:]
                if len(imageBuffer) != frameSizeInt:
                    Sentry.Error("Webcam Helper", "Snapshot callback final image size was not the frame size. expected: "+str(frameSizeInt)+", got: "+str(len(imageBuffer)))

                # If successful, we will use the already existing response object but update the values to match the fixed size body and content type.
                response.status_code = 200
                # Clear all of the current
                response.headers.clear()
                # Set the content type to the header we got from the stream chunk.
                response.headers["content-type"] = contentType
                # It's very important this size matches the body buffer we give OctoHttpRequest, or the logic in the http loop will fail because it will keep trying to read more.
                response.headers["content-length"] = str(len(imageBuffer))
                # Return a result. Return the full image buffer which will be used as the response body.
                Sentry.Debug("Webcam Helper", "Successfully got image from stream URL. Size: %s, Format: %s" % (str(len(imageBuffer)), contentType))
                return OctoHttpRequest.Result(response, url, True, imageBuffer)
        except ConnectionError as e:
            # We have a lot of telemetry indicating a read timeout can happen while trying to read from the stream
            # in that case we should just get out of here.
            if "Read timed out" in str(e):
                Sentry.Debug("Webcam Helper", "_GetSnapshotFromStream got a timeout while reading the stream.")
                return None
            else:
                Sentry.Exception("Failed to get fallback snapshot due to ConnectionError", e)
        except Exception as e:
            Sentry.Exception("Failed to get fallback snapshot.", e)

        return None


    # Returns the default webcam setting object or None if there isn't one.
    def _GetWebcamSettingObj(self, cameraName:str = None):
        try:
            a = self.ListWebcams()
            if a is None or len(a) == 0:
                return None
            # If a camera name wasn't passed, see if there's a default.
            if cameraName is None or len(cameraName) == 0:
                cameraName = self.GetDefaultCameraName()
            # If we have a target name, see if we can find it.
            if cameraName is not None:
                cameraNameLower = cameraName.lower()
                for i in a:
                    if i.Name.lower() == cameraNameLower:
                        return i
                Sentry.Error("Webcam Helper", f"_GetWebcamSettingObj asked for {cameraName} but we didn't find it.")
            return a[0]
        except Exception as e:
            Sentry.Exception("WebcamHelper _GetWebcamSettingObj exception.", e)
        return None


    # Returns the currently known list of webcams.
    # The order they are returned is the order the use sees them.
    # The default is usually the index 0.
    def ListWebcams(self):
        try:
            a = self.WebcamPlatformHelperInterface.GetWebcamConfig()
            if a is None or len(a) == 0:
                return None
            return a
        except Exception as e:
            Sentry.Exception("WebcamHelper ListWebcams exception.", e)
        return None


    # Checks if the result was success and if so adds the common header.
    # Returns the octoHttpResult, so the function is chainable
    def _AddOeWebcamTransformHeader(self, octoHttpResult, cameraName:str):
        if octoHttpResult is None or octoHttpResult.Result is None:
            return octoHttpResult

        # Default to none
        transformStr = "none"

        # If there are any settings build a string with them all contaminated.
        settings = self._GetWebcamSettingObj(cameraName)
        if settings.FlipH or settings.FlipV or settings.Rotation != 0:
            transformStr = ""
            if settings.FlipH:
                transformStr += "fliph "
            if settings.FlipV:
                transformStr += "flipv "
            if settings.Rotation != 0:
                transformStr += "rotate="+str(settings.Rotation)+" "

        # Set the header
        octoHttpResult.Result.headers[WebcamHelper.c_OeWebcamTransformHeaderKey] = transformStr
        return octoHttpResult


    # Checks if the result was success and if so checks if the image is a jpeg and if the header info is set correctly.
    # For some webcam servers, we have seen them return jpegs that have incomplete jpeg binary header data, which breaks some image processing libs.
    # This seems to break ImageSharp and it also breaks whatever Telegram uses on it's server side for processing.
    # To combat this, we will check if the image is a jpeg, and if so, ensure the header is set correctly.
    #
    # Returns the octoHttpResult, so the function is chainable
    def _EnsureJpegHeaderInfo(self, octoHttpResult: OctoHttpRequest.Result):
        # Ensure we got a result.
        if octoHttpResult is None or octoHttpResult.Result is None:
            return octoHttpResult

        # The GetSnapshot API will always return the fully buffered snapshot.
        buf = RequestsUtils.ReadAllContentFromStreamResponse(octoHttpResult.Result)
        if buf is None:
            Sentry.Error("Webcam Helper", "_EnsureJpegHeaderInfo got a null body read from ReadAllContentFromStreamResponse")
            return None
        # Set the buffer now, incase of early returns.
        octoHttpResult.SetFullBodyBuffer(buf)

        # Handle the buffer.
        # In a nutshell, all jpeg images have a lot of header segments, but they must have the app0 header.
        # This header defines what sub type of image the jpeg is. It seems the app0 header is always there, but some
        # webcam servers don't set the identifier bits, which should be JFIF\0 or something like that.
        # We need to find the app0 header, and if we do, ensure the identifier is set.
        # This has to be efficient so it can run on low power hardware!
        try:

            # Check if this is a jpeg, it must start with FF D8
            bufLen = len(buf)
            if bufLen < 2 or buf[0] != 0xFF or buf[1] != 0xD8:
                return octoHttpResult

            # Search the headers for the APP0
            pos = 2
            while pos < bufLen:
                # Ensure we have room and sanity check the buffer headers.
                if pos + 1 >= bufLen:
                    Sentry.Error("Webcam Helper", "Ran out of buffer before we found a jpeg APP0 header")
                    return octoHttpResult
                if buf[pos] != 0xFF:
                    Sentry.Error("Webcam Helper", "jpeg segment header didn't start with 0xff")
                    return octoHttpResult

                # The first byte is always FF, so we only care about the second.
                segmentType = buf[pos+1]
                if segmentType == 0xDA:
                    # This is the start of the image, the headers are over.
                    Sentry.Debug("Webcam Helper", "We found the start of the jpeg image before we found the APP0 header.")
                    return octoHttpResult
                elif segmentType == 0xE0:
                    # This is the APP0 header.
                    # Skip past the segment header and size bytes
                    pos += 4

                    # If these next bytes aren't set, we will set them to the default of "JFIF\0"
                    # Note that the last byte should be 0!
                    needsChanges = buf[pos] == 0 or buf[pos+1] == 0 or buf[pos+2] == 0 or buf[pos+3] == 0 or buf[pos+4] == 0 or buf[pos+5] != 0

                    # If we don't need changes, we are done.
                    # No need to process more headers.
                    if needsChanges is False:
                        return octoHttpResult

                    # To edit the byte array, we need a bytearray.
                    # This adds overhead, but it's required because bytes objects aren't editable.
                    bufArray = bytearray(buf)
                    if bufArray[pos] == 0:
                        bufArray[pos] = 0x4a # J
                    pos += 1
                    if bufArray[pos] == 0:
                        bufArray[pos] = 0x46 # F
                    pos += 1
                    if bufArray[pos] == 0:
                        bufArray[pos] = 0x49 # I
                    pos += 1
                    if bufArray[pos] == 0:
                        bufArray[pos] = 0x46 # F
                    pos += 1
                    # This should be 0.
                    if bufArray[pos] != 0:
                        bufArray[pos] = 0 # /0
                    pos += 1

                    # We need to set the buffer again, since it's a new bytearray object now.
                    octoHttpResult.SetFullBodyBuffer(bufArray)

                    # Done, No need to process more headers.
                    return octoHttpResult
                else:
                    # This is some other header, skip it's length.
                    # First skip past the type two bytes.
                    pos += 2
                    # Now read the length, two bytes
                    segLen = (buf[pos] << 8) + buf[pos+1]
                    # Now skip past the segment length (the two length bytes are included in the length size)
                    pos += segLen

        except Exception as e:
            Sentry.Exception("WebcamHelper _EnsureJpegHeaderInfo failed to handle jpeg buffer", e)
            # On a failure, return the original result, since it's still good.
            return octoHttpResult

        # If we fall out of the while loop,
        Sentry.Debug("Webcam Helper", "_EnsureJpegHeaderInfo excited the while loop without finding the app0 header.")
        return octoHttpResult


    def GetDevAddress(self):
        return OctoHttpRequest.GetLocalhostAddress()+":"+str(OctoHttpRequest.GetLocalOctoPrintPort())


    # A static helper that provides common logic to detect urls for camera-streamer.
    #
    # Both OctoPrint and Klipper are using camera-streamer for WebRTC webcam streaming. If the system is going to be WebRTC based,
    # it's going to be camera-streamer. There are a ton of other streaming types use commonly, the most common being jmpeg from server sources, as well as HLS, and more.
    #
    # This function is designed to detect the camera-streamer URLs and fix them up for our internal use. We support WebRTC via the Klipper or OctoPrint portals,
    # but for all of our service related streaming we can't support WebRTC. For things like Live Links, WebRTC would expose the WAN IP of the user's device.
    # Thus, for anything internally to OctoApp, we convert camera-streamer's webrtc stream URL to jmpeg.
    #
    # If the camera-streamer webrtc stream URL is found, the correct camera-streamer jmpeg stream is returned.
    # Otherwise None is returned.
    @staticmethod
    def DetectCameraStreamerWebRTCStreamUrlAndTranslate(streamUrl:str) -> str:
        # Ensure there's something to work with
        if streamUrl is None:
            return None

        # try to find anything with /webrtc in it, which is a pretty unique signature for camera-streamer
        streamUrlLower = streamUrl.lower()
        webRtcLocation = streamUrlLower.find("/webrtc")
        if webRtcLocation == -1:
            return None

        # Since just /webrtc is vague, make sure there's no more paths after the webrtc
        forwardSlashAfterWebrtc = streamUrlLower.find('/', webRtcLocation + 1)
        if forwardSlashAfterWebrtc != -1:
            # If there's another / after the /webrtc chunk, this isn't camera streamer.
            return None

        # This is camera-streamer.
        # We want to preserver the URL before the /webrtc, and only replace the /webrtc.
        return streamUrl[:webRtcLocation] + "/stream"


    # A static helper that provides common logic to detect webcam urls missing a directory slash.
    # This works for any url that has the following format: '*webcam*?action=*'
    #
    # This is mostly a problem in Klipper, but if the webcam/?action=stream URL is formatted as 'webcam?action=stream' and the proxy was nginx, it will cause a redirect to 'webcam/?action=stream'.
    # This is ok, but it causes an extra hop before the webcam can show. Also internally this used to break the Snapshot logic, as we didn't follow redirects, so getting
    # a snapshot locally would break. We added the ability for non-proxy http calls to follow redirects, so this is no longer a problem.
    #
    # If the slash is detected to be missing, this function will return the URL with the slash added correctly.
    # Otherwise, it returns None.
    @staticmethod
    def FixMissingSlashInWebcamUrlIfNeeded(webcamUrl:str) -> str:
        # First, the stream must have webcam* and ?action= in it, otherwise, we don't care.
        streamUrlLower = webcamUrl.lower()
        webcamLocation = streamUrlLower.find("webcam")
        actionLocation = streamUrlLower.find("?action=")
        if webcamLocation == -1 or actionLocation == -1:
            return None

        # Next, we must we need to remember that some urls might be like 'webcam86?action=*', so we have to exclude the number.
        # We know that if we found ?action= there must be a / before the ?
        if actionLocation == 0:
            # This shouldn't happen, but we should check.
            return None
        if streamUrlLower[actionLocation-1] == '/':
            # The URL is good we know that just before ?action= there is a /
            return None

        # We know there is no slash before action, add it.
        newWebcamUrl = webcamUrl[:actionLocation] + "/" + webcamUrl[actionLocation:]
        Sentry.Info("Webcam Helper", f"Found incorrect webcam url, updating. [{webcamUrl}] -> [{newWebcamUrl}]")
        return newWebcamUrl


    #
    # Default camera name logic.
    #

    # Sets the default camera name and writes it to the settings file.
    def SetDefaultCameraName(self, name:str) -> None:
        name = name.lower()
        self.DefaultCameraName = name
        try:
            settings = {
                "DefaultWebcamName" : self.DefaultCameraName
            }
            with open(self.SettingsFilePath, encoding="utf-8", mode="w") as f:
                f.write(json.dumps(settings))
        except Exception as e:
            Sentry.Error("Webcam Helper", "SetDefaultCameraName failed "+str(e))


    # Returns the default camera name or None
    def GetDefaultCameraName(self) -> str:
        return self.DefaultCameraName


    # Loads the current name from our settings file.
    def _LoadDefaultCameraName(self) -> None:
        try:
            # Default the setting.
            self.DefaultCameraName = None

            # First check if there's a file.
            if os.path.exists(self.SettingsFilePath) is False:
                return

            # Try to open it and get the key. Any failure will null out the key.
            with open(self.SettingsFilePath, encoding="utf-8") as f:
                data = json.load(f)

            name = data["DefaultWebcamName"]
            if name is None or len(name) == 0:
                return
            self.DefaultCameraName = name
            Sentry.Info("Webcam Helper", f"Webcam settings loaded. Default camera name: {self.DefaultCameraName}")
        except Exception as e:
           Sentry.Error("Webcam Helper", "_LoadDefaultCameraName failed "+str(e))