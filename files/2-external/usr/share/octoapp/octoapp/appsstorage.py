
from octoapp.sentry import Sentry
import threading
import time

class AppInstance:
        
    def __init__(
              self, 
              fcmToken:str, 
              fcmFallbackToken:str, 
              instanceId:str,
              displayName:str,
              displayDescription:str,
              model:str,
              appVersion:str,
              appBuild:int,
              appLanguage:str,
              lastSeenAt:float,
              expireAt:float,
              excludeNotifications:list,
    ):
        self.FcmToken = fcmToken
        self.FcmFallbackToken = fcmFallbackToken
        self.InstanceId = instanceId
        self.DisplayName = displayName
        self.DisplayDescription = displayDescription
        self.Model = model
        self.AppVersion = appVersion
        self.AppBuild = appBuild
        self.AppLanguage = appLanguage
        self.LastSeenAt = lastSeenAt
        self.ExpireAt = expireAt
        self.ExcludeNotifications = excludeNotifications


    def ToDict(self): 
        return dict(
            fcmToken=self.FcmToken,
            fcmTokenFallback=self.FcmFallbackToken,
            instanceId=self.InstanceId,
            displayName=self.DisplayName,
            displayDescription=self.DisplayDescription,
            model=self.Model,
            appVersion=self.AppVersion,
            appBuild=self.AppBuild,
            appLanguage=self.AppLanguage,
            lastSeenAt=self.LastSeenAt,
            expireAt=self.ExpireAt,
            excludeNotifications=self.ExcludeNotifications
        )

    @staticmethod
    def FromDict(dict:dict):
        return AppInstance(
            fcmToken=dict["fcmToken"],
            fcmFallbackToken=dict.get("fcmTokenFallback", None),
            instanceId=dict["instanceId"],
            displayName=dict.get("displayName", "Unknown"),
            displayDescription=dict.get("displayDescription", ""),
            model=dict.get("model", "Unknown"),
            appVersion=dict.get("appVersion", "Unknown"),
            appBuild=dict.get("appBuild", 1),
            appLanguage=dict.get("appLanguage", "en"),
            lastSeenAt=dict.get("lastSeenAt", 0),
            expireAt=dict.get("expireAt", 0),
            excludeNotifications=dict.get("excludeNotifications", []),
        )

       

class AppStorageHelper:

    # Logic for a static singleton
    _Instance = None

    @staticmethod
    def Init(appStoragePlatformHelper):
        AppStorageHelper._Instance = AppStorageHelper(appStoragePlatformHelper)

    @staticmethod
    def Get():
        return AppStorageHelper._Instance

    def __init__(self, appStoragePlatformHelper):
        self.AppStoragePlatformHelper = appStoragePlatformHelper

    def GetAndroidApps(self, apps):
        return list(filter(lambda app: not app.FcmToken.startswith("activity:") and not app.FcmToken.startswith("ios:"), apps))

    def GetExpiredApps(self, apps):
        return list(filter(lambda app: app.ExpireAt is not None and time.time() > app.ExpireAt, apps))

    def GetIosApps(self, apps):
        return list(filter(lambda app: app.FcmToken.startswith("ios:"), apps))

    def GetActivities(self, apps):
        return list(sorted(filter(lambda app: app.FcmToken.startswith("activity:"), apps), key=lambda app: app.LastSeenAt, reverse=True))
    
    def GetDefaultExpirationFromNow(self):
        return (time.time() + 2592000)

    def LogApps(self):
        apps = self.GetAllApps()
        Sentry.Debug("APPS", "Now %s apps registered" % len(apps))
        for app in apps:
            Sentry.Debug("APPS", "     => %s" % app.FcmToken[0:100])

    def RemoveTemporaryApps(self, for_instance_id=None):
        apps = self.GetAllApps()
        
        if for_instance_id is None:
            apps = list(filter(lambda app: app.FcmToken.startswith("activity:"), apps))
            Sentry.Debug("APPS", "Removed all temporary apps")
        else:
            apps = list(filter(lambda app: app.FcmToken.startswith("activity:") and app.instanceId == for_instance_id , apps))
            Sentry.Debug("APPS", "Removed all temporary apps for %s" % for_instance_id)

        self.RemoveApps(apps)

    def GetAllApps(self) -> [AppInstance]:
        apps = self.AppStoragePlatformHelper.GetAllApps()
        Sentry.Debug("APPS", "Loading %s apps" % len(apps))
        return apps

    def RemoveApps(self, apps: [AppInstance]):
        Sentry.Debug("APPS", "Removing %s apps" % len(apps))
        self.AppStoragePlatformHelper.RemoveApps(apps)
        self.LogApps()
     
    def GetOrCreateEncryptionKey(self):
        return self.AppStoragePlatformHelper.GetOrCreateEncryptionKey()
