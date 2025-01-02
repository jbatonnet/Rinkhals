
# Some of the features we need to integrate into the octoapp package only exist on
# some platforms. This is basically an interface that allows us to dynamically control
# if some objects are available depending on the platform.
class Compat:

    _IsOctoPrintHost = False
    _IsMoonrakerHost = False
    _IsObserverMode = False
    @staticmethod
    def IsOctoPrint() -> bool:
        return Compat._IsOctoPrintHost
    @staticmethod
    def IsMoonraker() -> bool:
        return Compat._IsMoonrakerHost
    @staticmethod
    def IsObserverMode() -> bool:
        return Compat._IsObserverMode
    @staticmethod
    def SetIsOctoPrint(b):
        Compat._IsOctoPrintHost = b
    @staticmethod
    def SetIsMoonraker(b):
        Compat._IsMoonrakerHost = b
    @staticmethod
    def SetIsObserverMode(b):
        Compat._IsObserverMode = b


    _LocalAuthObj = None
    @staticmethod
    def GetLocalAuth():
        return Compat._LocalAuthObj
    @staticmethod
    def SetLocalAuth(obj):
        Compat._LocalAuthObj = obj
    @staticmethod
    def HasLocalAuth():
        return Compat._LocalAuthObj is not None


    _SlipstreamObj = None
    @staticmethod
    def GetSlipstream():
        return Compat._SlipstreamObj
    @staticmethod
    def SetSlipstream(obj):
        Compat._SlipstreamObj = obj
    @staticmethod
    def HasSlipstream():
        return Compat._SlipstreamObj is not None

    # Must implement the smart pause interface.
    #
    # GetAndResetLastPauseNotificationSuppressionTimeSec - Returns None if there is no current suppression or the time of the last time it was requested
    #
    _SmartPauseInterfaceObj = None
    @staticmethod
    def GetSmartPauseInterface():
        return Compat._SmartPauseInterfaceObj
    @staticmethod
    def SetSmartPauseInterface(obj):
        Compat._SmartPauseInterfaceObj = obj
    @staticmethod
    def HasSmartPauseInterface():
        return Compat._SmartPauseInterfaceObj is not None


    _WebRequestResponseHandler = None
    @staticmethod
    def GetWebRequestResponseHandler():
        return Compat._WebRequestResponseHandler
    @staticmethod
    def SetWebRequestResponseHandler(obj):
        Compat._WebRequestResponseHandler = obj
    @staticmethod
    def HasWebRequestResponseHandler():
        return Compat._WebRequestResponseHandler is not None


    _ApiRouterHandler = None
    @staticmethod
    def GetApiRouterHandler():
        return Compat._ApiRouterHandler
    @staticmethod
    def SetApiRouterHandler(obj):
        Compat._ApiRouterHandler = obj
    @staticmethod
    def HasApiRouterHandler():
        return Compat._ApiRouterHandler is not None
