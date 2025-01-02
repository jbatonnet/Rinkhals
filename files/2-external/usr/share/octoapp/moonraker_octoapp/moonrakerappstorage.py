from octoapp.sentry import Sentry
from .moonrakerdatabase import MoonrakerDatabase
from octoapp.appsstorage import AppInstance, AppStorageHelper
import uuid

class MoonrakerAppStorage:

    def __init__(self, database):
        self.First = False
        self.Database = database


    # !! Platform Command Handler Interface Function !!
    #
    # This must return a list of AppInstance
    #
    def GetAllApps(self) -> [AppInstance]:
        apps = self.Database.GetAppsEntry()
        return list(map(lambda app: AppInstance.FromDict(app), apps))        


    # !! Platform Command Handler Interface Function !!
    #
    # This must receive a lsit of AppInstnace
    #
    def RemoveApps(self, apps:[AppInstance]):
        apps = list(map(lambda app: app.FcmToken, apps))
        self.Database.RemoveAppEntries(apps)

    # !! Platform Command Handler Interface Function !!
    #
    # This must receive a lsit of AppInstnace
    #
    def GetOrCreateEncryptionKey(self):
        return self.Database.GetOrCreateEncryptionKey()