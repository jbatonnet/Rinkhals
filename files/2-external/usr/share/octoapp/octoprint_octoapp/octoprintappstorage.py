
import os
import json
import time
import flask
import threading
import uuid
from Crypto import Random
from Crypto.Cipher import AES
from .subplugin import OctoAppSubPlugin
from octoprint.access.permissions import Permissions
from octoprint.events import Events
from octoapp.sentry import Sentry
from octoapp.appsstorage import AppInstance, AppStorageHelper

class OctoPrintAppStorageSubPlugin(OctoAppSubPlugin):

    def __init__(self, parent):
        super().__init__(parent)
        self.DataFile = None
        self.Lock = threading.Lock()
        self.DataFile = os.path.join(self.parent.get_plugin_data_folder(), "apps.json")
        Sentry.Info("OCTO STORAGE", "Using config file %s" % self.DataFile)
        Sentry.Debug("OCTO STORAGE", "-> __init__")
        with self.Lock:
            Sentry.Debug("OCTO STORAGE", "<- __init__")
            self._upgradeDataStructure()
            self._upgradeExpirationDate()
            self._sendSettingsPluginMessage(self._getAllApps())
            self._getOrCreateEncryptionKey()


    # !! Platform Command Handler Interface Function !!
    #
    # This must return a list of AppInstance
    #
    def GetAllApps(self) -> [AppInstance]:
        Sentry.Debug("OCTO STORAGE", "-> GetAllApps")
        with self.Lock:
            Sentry.Debug("OCTO STORAGE", "<- GetAllApps")
            return self._getAllApps()

    def OnEvent(self, event, payload):
        if event == Events.CLIENT_OPENED and self.DataFile is not None:
            Sentry.Debug("OCTO STORAGE", "-> OnEvent")
            with self.Lock:
                Sentry.Debug("OCTO STORAGE", "<- OnEvent")
                self._sendSettingsPluginMessage(self._getAllApps())


    # !! Platform Command Handler Interface Function !!
    #
    # This must receive a lsit of AppInstnace
    #
    def RemoveApps(self, apps:[AppInstance]):
        Sentry.Debug("OCTO STORAGE", "-> RemoveApps")
        with self.Lock:
            Sentry.Debug("OCTO STORAGE", "<- RemoveApps")
            allApps = self._getAllApps()
            for appToRemove in apps:
                allApps = list(filter(lambda app: app.FcmToken != appToRemove.FcmToken, allApps))

            self._setAllApps(allApps)


    def OnApiCommand(self, command, data):
        if command == "registerForNotifications":
            if not Permissions.PLUGIN_OCTOAPP_RECEIVE_NOTIFICATIONS.can():
                return flask.make_response("Insufficient rights", 403)

            fcmToken = data["fcmToken"]

            Sentry.Debug("OCTO STORAGE", "-> OnApiCommand")
            with self.Lock:
                Sentry.Debug("OCTO STORAGE", "<- OnApiCommand")
                # load apps and filter the given FCM token out
                apps = self._getAllApps()
                if apps:
                    apps = [app for app in apps if app.FcmToken != fcmToken]
                else:
                    apps = []

                # add app for new registration
                apps.append(
                    AppInstance(
                        fcmToken=fcmToken,
                        fcmFallbackToken=data.get("fcmTokenFallback", None),
                        instanceId=data["instanceId"],
                        displayName=data["displayName"],
                        displayDescription=data.get("displayDescription", None),
                        model=data["model"],
                        appVersion=data["appVersion"],
                        appBuild=data["appBuild"],
                        appLanguage=data["appLanguage"],
                        lastSeenAt=time.time(),
                        expireAt=(time.time() + data["expireInSecs"]) if "expireInSecs" in data else AppStorageHelper.Get().GetDefaultExpirationFromNow(),
                        excludeNotifications=data.get("excludeNotifications", [])
                    )
                )

                # save
                Sentry.Info("NOTIFICATION", "Registered app %s" % fcmToken)
                self._setAllApps(apps)
                self.parent._settings.save()
                return flask.jsonify(dict())
    
        else: 
            return None
        
    # !! Platform Command Handler Interface Function !!
    #
    # This must receive a lsit of AppInstnace
    #
    def GetOrCreateEncryptionKey(self):
        Sentry.Debug("OCTO STORAGE", "-> GetOrCreateEncryptionKey")
        with self.Lock:
            Sentry.Debug("OCTO STORAGE", "<- GetOrCreateEncryptionKey")
            return self._getOrCreateEncryptionKey()
        
    def _getOrCreateEncryptionKey(self):
        key = self.parent._settings.get(["encryptionKey"])
        if key is None:
            key = str(uuid.uuid4())
            Sentry.Info("NOTIFICATION", "Created new encryption key")
            self.parent._settings.set(["encryptionKey"], key)
        return key
        

    def _getAllApps(self) -> [AppInstance]:
        try: 
            if os.path.isfile(self.DataFile):
                with open(self.DataFile, 'r') as file:
                    apps = json.load(file)
                if apps is None:
                    apps = []
                
                return list(map(lambda x: AppInstance.FromDict(x), apps))
            else:
                return []
        except Exception as e: 
            Sentry.ExceptionNoSend("Failed to load apps", e)
            raise e
        

    def _setAllApps(self, apps:[AppInstance]):
        mapped_apps = list(map(lambda x: x.ToDict(), apps))

        with open(self.DataFile, 'w') as outfile:
            json.dump(mapped_apps, outfile)

        self._sendSettingsPluginMessage(apps)

    def _upgradeDataStructure(self):
        try:
            if not os.path.isfile(self.DataFile):
                Sentry.Info("APPS", "Dropping old app storage")
                self.parent._settings.remove(["registeredApps"])
        except Exception as e:
            Sentry.ExceptionNoSend("Failed to drop old app storage", e)


    def _upgradeExpirationDate(self):
        try:
            def add_expiration(app):
                before = app.ExpireAt
                app.ExpireAt = app.ExpireAt or AppStorageHelper.Get().GetDefaultExpirationFromNow()
                Sentry.Info("APPS", "Updating expire at for %s: %s => %s" % (app.InstanceId, before, app.ExpireAt))
                return app

            apps = self._getAllApps()
            Sentry.Info("APPS", "Ensuring all apps have expiration dates")
            apps = list(map(lambda app: add_expiration(app), apps))
            self._setAllApps(apps)
        except Exception as e:
            Sentry.ExceptionNoSend("Failed to upgrade expiration", e)

    def _sendSettingsPluginMessage(self, apps):
        mapped_apps = list(map(lambda x: dict(
            displayName=x.DisplayName,
            lastSeenAt=x.LastSeenAt,
            expireAt=x.ExpireAt,
            displayDescription=x.DisplayDescription,
            appVersion=x.AppVersion,
            appOutdated=x.AppBuild < 1_17_134
        ), apps))
        mapped_apps = sorted(mapped_apps, key=lambda d: d.get("expireAt", None) or float('inf'))
        self.parent._plugin_manager.send_plugin_message("%s.settings" % self.parent._identifier, {"apps": mapped_apps})
