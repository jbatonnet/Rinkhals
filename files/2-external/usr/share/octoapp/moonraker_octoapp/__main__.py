import os
import sys
import json
import base64
from enum import Enum

from .moonrakerhost import MoonrakerHost

#
# Helper functions for config parsing and validation.
#
class ConfigDataTypes(Enum):
    String = 1
    Path = 2
    Bool = 3

def _GetConfigVarAndValidate(config, varName:str, dataType:ConfigDataTypes):
    if varName not in config:
        raise Exception(f"{varName} isn't found in the json config.")
    var = config[varName]

    if var is None:
        raise Exception(f"{varName} returned None when parsing json config.")

    if dataType == ConfigDataTypes.String or dataType == ConfigDataTypes.Path:
        var = str(var)
        if len(var) == 0:
            raise Exception(f"{varName} is an empty string.")

        if dataType == ConfigDataTypes.Path:
            if os.path.exists(var) is False:
                raise Exception(f"{varName} is a path, but the path wasn't found.")

    elif dataType == ConfigDataTypes.Bool:
        var = bool(var)

    else:
        raise Exception(f"{varName} has an invalid config data type. {dataType}")
    return var

#
# Helper for errors.
#
def _PrintErrorAndExit(msg:str):
    print(f"\r\nPlugin Init Error - {msg}", file=sys.stderr)
    print( "\r\nPlease contact support so we can fix this for you! hello@octoapp.eu", file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    # The config and settings path is passed as the first arg when the service runs.
    # This allows us to run multiple services instances, each pointing at it's own config.
    if len(sys.argv) < 1:
        _PrintErrorAndExit("No program and json settings path passed to service")

    # The second arg should be a json string, which has all of our params.
    if len(sys.argv) < 2:
        _PrintErrorAndExit("No json settings path passed to service")

    # Try to parse the config
    jsonConfigStr = None
    try:
        # The args are passed as a urlbase64 encoded string, to prevent issues with passing some chars as args.
        argsJsonBase64 = sys.argv[1]
        jsonConfigStr = base64.urlsafe_b64decode(bytes(argsJsonBase64, "utf-8")).decode("utf-8")
        print("Loading Service Config: "+jsonConfigStr)
        config = json.loads(jsonConfigStr)

        #
        # 1) Parse the common, required args.
        #
        ServiceName = _GetConfigVarAndValidate(config, "ServiceName", ConfigDataTypes.String)
        VirtualEnvPath = _GetConfigVarAndValidate(config, "VirtualEnvPath", ConfigDataTypes.Path)
        RepoRootFolder = _GetConfigVarAndValidate(config, "RepoRootFolder", ConfigDataTypes.Path)
        KlipperConfigFolder = _GetConfigVarAndValidate(config, "KlipperConfigFolder", ConfigDataTypes.Path)
        KlipperLogFolder = _GetConfigVarAndValidate(config, "KlipperLogFolder", ConfigDataTypes.Path)
        LocalFileStoragePath = _GetConfigVarAndValidate(config, "LocalFileStoragePath", ConfigDataTypes.Path)

        #
        # 2) Parse the IsObserver flag, this will determine which other vars are required.
        #    Note that for older plugin installs, the IsObserver flag won't exist, implying False.
        #
        IsObserver = False
        if "IsObserver" in config:
            IsObserver = config["IsObserver"]
        IsObserver = bool(IsObserver)

        #
        # 3) Now parse the required vars based on the IsObserver flag state.
        #
        MoonrakerConfigFile = None
        ObserverConfigFilePath = None
        ObserverInstanceIdStr = None

        if IsObserver:
            ObserverConfigFilePath = _GetConfigVarAndValidate(config, "ObserverConfigFilePath", ConfigDataTypes.Path)
            ObserverInstanceIdStr   = _GetConfigVarAndValidate(config, "ObserverInstanceIdStr",  ConfigDataTypes.String)
        else:
            MoonrakerConfigFile = _GetConfigVarAndValidate(config, "MoonrakerConfigFile", ConfigDataTypes.Path)

    except Exception as e:
        _PrintErrorAndExit(f"Exception while loading json config. Error:{str(e)}, Config: {jsonConfigStr}")

    # For debugging, we also allow an optional dev object to be passed.
    devConfig_CanBeNone = None
    try:
        if len(sys.argv) > 2:
            devConfig_CanBeNone = json.loads(sys.argv[2])
            print("Using dev config: "+sys.argv[2])
    except Exception as e:
        _PrintErrorAndExit(f"Exception while DEV CONFIG. Error:{str(e)}, Config: {sys.argv[2]}")

    # Run!
    try:
        # Create and run the main host!
        host = MoonrakerHost(KlipperConfigFolder, KlipperLogFolder, devConfig_CanBeNone)
        host.RunBlocking(KlipperConfigFolder, IsObserver, LocalFileStoragePath, ServiceName, VirtualEnvPath, RepoRootFolder,
                        MoonrakerConfigFile,
                        ObserverConfigFilePath, ObserverInstanceIdStr,
                        devConfig_CanBeNone)
    except Exception as e:
        _PrintErrorAndExit(f"Exception leaked from main moonraker host class. Error:{str(e)}")

    # If we exit here, it's due to an error, since RunBlocking should be blocked forever.
    sys.exit(1)
