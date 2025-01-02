
import configparser
import logging
import os

from octoapp.sentry import Sentry
from octoapp.compat import Compat

class ObserverConfigFile:

    # These sections and keys are shared with the installer plugin code, so we can't change them.
    c_SectionMoonraker = "moonraker"
    c_KeyIpOrHostname = "ip_or_hostname"
    c_KeyPort = "port"

    # The static instance.
    _Instance = None


    @staticmethod
    def Init(observerConfigFile:str):
        ObserverConfigFile._Instance = ObserverConfigFile(observerConfigFile)


    def __init__(self, observerConfigFile:str) -> None:
        # Note this will be None if we aren't in observer mode.
        self.ObserverConfigFile = observerConfigFile


    @staticmethod
    def Get():
        return ObserverConfigFile._Instance


    # Returns the (ip:str, port:str) if the config can be parsed. Otherwise (None, None)
    def TryToGetIpAndPortStr(self):
        if not Compat.IsObserverMode():
            Sentry.Error("Config", "Observer config file was attempted to be accessed without being in observer mode.")
            return (None, None)
        if not os.path.exists(self.ObserverConfigFile):
            Sentry.Error("Config", "No Observer config file was set into the observer config class.")
            return (None, None)
        try:
            config = configparser.ConfigParser(allow_no_value=True, strict=False)
            config.read(self.ObserverConfigFile)
            if config.has_section(ObserverConfigFile.c_SectionMoonraker):
                if ObserverConfigFile.c_KeyIpOrHostname in config[ObserverConfigFile.c_SectionMoonraker].keys() and ObserverConfigFile.c_KeyPort in config[ObserverConfigFile.c_SectionMoonraker].keys():
                    ip = config[ObserverConfigFile.c_SectionMoonraker][ObserverConfigFile.c_KeyIpOrHostname]
                    port = config[ObserverConfigFile.c_SectionMoonraker][ObserverConfigFile.c_KeyPort]
                    if len(ip) > 0:
                        portInt = int(port)
                        if portInt > 0 and portInt < 65535:
                            return (ip, port)
        except Exception as e:
            Sentry.Warn("Config", f"Failed to parse plugin observer config: {self.ObserverConfigFile}; " + str(e))
        return (None, None)
