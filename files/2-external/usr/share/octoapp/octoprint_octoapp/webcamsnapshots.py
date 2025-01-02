
from .subplugin import OctoAppSubPlugin

import threading
import time
from PIL import Image
import requests
from io import BytesIO
import flask
from datetime import datetime
from octoprint.access.permissions import Permissions
from octoapp.sentry import Sentry
from flask import send_file
from octoapp.webcamhelper import WebcamSettingItem

class OctoAppWebcamSnapshotsSubPlugin(OctoAppSubPlugin):


    def __init__(self, parent, octoPrintWebcamHelper):
        super().__init__(parent)
        self.WebcamSnapshotCache = {}
        self.WebcamSnapshotCacheLock = threading.Lock()
        self.OctoPrintWebcamHelper = octoPrintWebcamHelper


    def OnAfterStartup(self):
        self._continuouslyUpdateSnapshots()

    
    def OnApiCommand(self, command, data):
        if command == "getWebcamSnapshot":
            if not Permissions.PLUGIN_OCTOAPP_GET_DATA.can():
                return flask.make_response("Insufficient rights", 403)

            try:
                with self.WebcamSnapshotCacheLock:
                    webcamIndex = data.get("webcamIndex", 0)
                    applyTransform = data.get("applyTransform", True) is True
                    webcamSettings = self._getWebcamSettingsItem(webcamIndex)
                    cache = self.WebcamSnapshotCache.get(webcamIndex)
                    
                    if (cache == None):
                        return flask.make_response("Webcam image for {} not cached".format(webcamIndex), 406)
                    
                    secondsSince = (datetime.now() - cache.get("time")).total_seconds()
                    if (secondsSince > 60):
                         return flask.make_response("Webcam image for {} outdated".format(webcamIndex), 406)
                
                    image = Image.open(cache.get("bytes")).copy()
                    size = min(max(image.width, image.height), int(data.get("size", 720)))
                    image.thumbnail([size, size])

                    if (applyTransform and webcamSettings.Rotation != 0):
                        image = image.rotate(-webcamSettings.Rotation, expand=True)

                    if (applyTransform and webcamSettings.FlipV):
                        image = image.transpose(Image.FLIP_TOP_BOTTOM)

                    if (applyTransform and webcamSettings.FlipH):
                        image = image.transpose(Image.FLIP_LEFT_RIGHT)

                    imageBytes = BytesIO()
                    image.save(imageBytes, 'JPEG', quality=data.get("quality", 50))
                    imageBytes.seek(0)
                    return send_file(imageBytes, mimetype='image/jpeg')
            except Exception as e:
                Sentry.ExceptionNoSend("Failed to get webcam snapshot", e)
                return flask.make_response("Failed to process snapshot from webcam", 500)
        
        else:
            return None


    #
    # SNAPSHOTS
    #


    def _continuouslyUpdateSnapshots(self):
        t = threading.Thread(
            target=self._doContinuouslyUpdateSnapshots,
            args=[]
        )
        t.daemon = True
        t.start()


    def _doContinuouslyUpdateSnapshots(self):
        failure_count = 0
        success_count = 0
        
        while True:
            multiCamSettings = webcamSettings = self.parent._settings.global_get(
                ["plugins", "multicam", "multicam_profiles"]
            )

            success = True
            log = success_count % 10 == 0

            if (type(multiCamSettings) == list):
                for i in range(len(multiCamSettings)):
                   success = success and self._updateSnapshotCache(webcamIndex = i, log = log)
            else:
                success = success and self._updateSnapshotCache(webcamIndex = 0, log = log) 

            if success is False:
                failure_count += 1
                success_count = 0
            else:
                failure_count = 0
                success_count += 1

            time.sleep(min(120, (failure_count + 1) * 5))


    def _updateSnapshotCache(self, webcamIndex, log):
        try:
            webcamSettings = self._getWebcamSettingsItem(webcamIndex)
            snapshotUrl = webcamSettings.SnapshotUrl

            if snapshotUrl == "" or snapshotUrl is None or (not snapshotUrl.startswith("http://") and not snapshotUrl.startswith("https://")):
                return True

            imageBytes = BytesIO()
            raw = requests.get(snapshotUrl, timeout=float(15), stream=True)

            for chunk in raw.iter_content(chunk_size=128):
                imageBytes.write(chunk)

            with self.WebcamSnapshotCacheLock:
                self.WebcamSnapshotCache[webcamIndex] = dict(bytes=imageBytes, time=datetime.now())

            return True
        except Exception as e:
            Sentry.ExceptionNoSend("Failed to get webcam snapshot", e)
            return False
      
           
    def _getWebcamSettingsItem(self, webcamIndex) -> WebcamSettingItem:
        if (webcamIndex == 0):
            configs = self.OctoPrintWebcamHelper.GetWebcamConfig()
            if len(configs) >= 1:
                return configs[0]
            else:
                return None
        else:
            config = self.parent._settings.global_get(
                ["plugins", "multicam", "multicam_profiles"]
            )[webcamIndex]

            WebcamSettingItem(
                name="Multicam %s" % webcamIndex,
                snapshotUrl=config.get("snapshot", None),
                streamUrl=config.get("stream", None),
                flipHBool=config.get("flipH", False),
                flipVBool=config.get("flipV", False),
                rotationInt=90 if config.get("rotate90", False) else 0,
            )