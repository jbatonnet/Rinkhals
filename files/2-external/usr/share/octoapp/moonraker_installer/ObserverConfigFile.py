
import configparser
import os

from .Logging import Logger
from .Util import Util
from .Context import Context

class ObserverConfigFile:

    # These sections and keys are shared with the moonraker plugin code, so we can't change them.
    c_SectionMoonraker = "moonraker"
    c_KeyIpOrHostname = "ip_or_hostname"
    c_KeyPort = "port"


    @staticmethod
    def GetConfigFolderPathFromDataPath(observerDataPath:str):
        # This path is shared with the plugin, so it can't be changed.
        return os.path.join(observerDataPath, "config")


    @staticmethod
    def GetConfigFilePathFromDataPath(observerDataPath:str):
        # This file name is shared with the plugin, so it can't be changed.
        return os.path.join(ObserverConfigFile.GetConfigFolderPathFromDataPath(observerDataPath), "octoapp-observer.cfg")


    # Returns the (ip:str, port:str) if the config can be parsed. Otherwise (None, None)
    @staticmethod
    def TryToParseConfig(configPath:str):
        if os.path.exists(configPath):
            try:
                config = configparser.ConfigParser(allow_no_value=True, strict=False)
                config.read(configPath)
                if config.has_section(ObserverConfigFile.c_SectionMoonraker):
                    if ObserverConfigFile.c_KeyIpOrHostname in config[ObserverConfigFile.c_SectionMoonraker].keys() and ObserverConfigFile.c_KeyPort in config[ObserverConfigFile.c_SectionMoonraker].keys():
                        ip = config[ObserverConfigFile.c_SectionMoonraker][ObserverConfigFile.c_KeyIpOrHostname]
                        port = config[ObserverConfigFile.c_SectionMoonraker][ObserverConfigFile.c_KeyPort]
                        if len(ip) > 0:
                            portInt = int(port)
                            if portInt > 0 and portInt < 65535:
                                return (ip, port)
            except Exception as e:
                Logger.Debug(f"Failed to parse plugin observer config: {configPath}; " + str(e))
        return (None, None)


    # Creates or uses an existing config, updates the ip and port.
    @staticmethod
    def WriteIpAndPort(context:Context, configPath:str, ip:str, port:str):
        try:
            # Ensure the dir exits.
            Util.EnsureDirExists(Util.GetParentDirectory(configPath), context, True)
            # Read the file, if there is one.
            config = configparser.ConfigParser(allow_no_value=True, strict=False)
            if os.path.exists(configPath):
                config.read(configPath)
            if config.has_section(ObserverConfigFile.c_SectionMoonraker) is False:
                config.add_section(ObserverConfigFile.c_SectionMoonraker)
            config[ObserverConfigFile.c_SectionMoonraker][ObserverConfigFile.c_KeyIpOrHostname] = ip
            config[ObserverConfigFile.c_SectionMoonraker][ObserverConfigFile.c_KeyPort] = port
            with open(configPath, 'w', encoding="utf-8") as f:
                config.write(f)
            return True
        except Exception as e:
            Logger.Error("Failed to write observer config. "+str(e))
            return False
