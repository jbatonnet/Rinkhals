import os
import json
import base64

from .Util import Util
from .Logging import Logger
from .Context import Context
from .Context import OsTypes


# Responsible for creating, running, and ensuring the service is installed and running.
class Service:

    def Install(self, context:Context):
        Logger.Header("Setting Up OctoApp's System Service...")

        # We always re-write the service file, to make sure it's current.
        if os.path.exists(context.ServiceFilePath):
            Logger.Info("Service file already exists, recreating.")

        # Create the service file.

        # First, we create a json object that we use as arguments. Using a json object makes parsing and such more flexible.
        # We base64 encode the json string to prevent any arg passing issues with things like quotes, spaces, or other chars.
        # Note some of these vars might be null, in the Observer Setup case
        argsJson = json.dumps({
            'KlipperConfigFolder': context.PrinterDataConfigFolder,
            'MoonrakerConfigFile': context.MoonrakerConfigFilePath,
            'KlipperLogFolder': context.PrinterDataLogsFolder,
            'LocalFileStoragePath': context.LocalFileStorageFolder,
            'ServiceName': context.ServiceName,
            'VirtualEnvPath': context.VirtualEnvPath,
            'RepoRootFolder': context.RepoRootFolder,
            'IsObserver' : context.IsObserverSetup,
            'ObserverConfigFilePath' : context.ObserverConfigFilePath,
            'ObserverInstanceIdStr' : context.ObserverInstanceId
        })
        # We have to convert to bytes -> encode -> back to string.
        argsJsonBase64 = base64.urlsafe_b64encode(bytes(argsJson, "utf-8")).decode("utf-8")

        # Base on the OS type, install the service differently
        if context.OsType == OsTypes.Debian:
            self._InstallDebian(context, argsJsonBase64)
        elif context.OsType == OsTypes.SonicPad:
            self._InstallSonicPad(context, argsJsonBase64)
        elif context.OsType == OsTypes.K1:
            self._InstallK1(context, argsJsonBase64)
        else:
            raise Exception("Service install is not supported for this OS type yet. Contact support!")


    # Install for debian setups
    def _InstallDebian(self, context:Context, argsJsonBase64):
        s = f'''\
    # OctoApp For Moonraker Service
    [Unit]
    Description=OctoApp For Moonraker
    # Start after network and moonraker has started.
    After=network-online.target moonraker.service

    [Install]
    WantedBy=multi-user.target

    # Simple service, targeting the user that was used to install the service, simply running our moonraker py host script.
    [Service]
    Type=simple
    User={context.UserName}
    WorkingDirectory={context.RepoRootFolder}
    ExecStart={context.VirtualEnvPath}/bin/python3 -m moonraker_octoapp "{argsJsonBase64}"
    Restart=always
    # Since we will only restart on a fatal Logger.Error, set the restart time to be a bit higher, so we don't spin and spam.
    RestartSec=10
'''
        if context.SkipSudoActions:
            Logger.Warn("Skipping service file creation, registration, and starting due to skip sudo actions flag.")
            return

        Logger.Debug("Service config file contents to write: "+s)
        Logger.Info("Creating service file "+context.ServiceFilePath+"...")
        with open(context.ServiceFilePath, "w", encoding="utf-8") as serviceFile:
            serviceFile.write(s)

        Logger.Info("Registering service...")
        Util.RunShellCommand("systemctl enable "+context.ServiceName)
        Util.RunShellCommand("systemctl daemon-reload")

        # Stop and start to restart any running services.
        Logger.Info("Starting service...")
        Service.RestartDebianService(context.ServiceName)

        Logger.Info("Service setup and start complete!")


    # Install for sonic pad setups.
    def _InstallSonicPad(self, context:Context, argsJsonBase64):
        # First, write the service file
        # Notes:
        #   Set start to be 66, so we start after Moonraker.
        #   OOM_ADJ=-17 prevents us from being killed in an OOM
        startNumberStr = "66"
        s = f'''\
#!/bin/sh /etc/rc.common
# Copyright (C) 2006-2011 OpenWrt.org

START={startNumberStr}
STOP=1
DEPEND=moonraker_service
USE_PROCD=1
OOM_ADJ=-17

start_service() {{
    procd_open_instance
    procd_set_param env HOME=/root
    procd_set_param env PYTHONPATH={context.RepoRootFolder}
    procd_set_param oom_adj $OOM_ADJ
    procd_set_param command {context.VirtualEnvPath}/bin/python3 -m moonraker_octoapp "{argsJsonBase64}"
    procd_close_instance
}}
'''
        if context.SkipSudoActions:
            Logger.Warn("Skipping service file creation, registration, and starting due to skip sudo actions flag.")
            return

        Logger.Debug("Service config file contents to write: "+s)
        Logger.Info("Creating service file "+context.ServiceFilePath+"...")
        with open(context.ServiceFilePath, "w", encoding="utf-8") as serviceFile:
            serviceFile.write(s)

        # Make the script executable.
        Logger.Info("Making the service executable...")
        Util.RunShellCommand(f"chmod +x {context.ServiceFilePath}")

        Logger.Info("Starting the service...")
        Service.RestartSonicPadService(context.ServiceFilePath)

        Logger.Info("Service setup and start complete!")


    # Install for k1 and k1 max
    def _InstallK1(self, context:Context, argsJsonBase64):
        # On the K1 start-stop-daemon is used to run services.
        # But, to launch our service, we have to use the py module run, which requires a environment var to be
        # set for PYTHONPATH. The command can't set the env, so we write this script to our store, where we then run
        # the service from.
        runScriptFilePath = os.path.join(context.LocalFileStorageFolder, "run-octoapp-service.sh")
        runScriptContents = f'''\
#!/bin/sh
#
# Runs OctoApp service on the K1 and K1 max.
# The start-stop-daemon can't handle setting env vars, but the python module run command needs PYTHONPATH to be set
# to find the module correctly. Thus we point the service to this script, which sets the env and runs py.
#
# Don't edit this script, it's generated by the ./install.sh script during the OE install and update..
#
PYTHONPATH={context.RepoRootFolder} {context.VirtualEnvPath}/bin/python3 -m moonraker_octoapp "{argsJsonBase64}"
exit $?
'''
        # Write the required service file, make it point to our run script.
        serviceFileContents = '''\
#!/bin/sh
#
# Starts OctoApp service.
#

PID_FILE=/var/run/octoapp.pid

start() {
        HOME=/root start-stop-daemon -S -q -b -m -p $PID_FILE --exec '''+runScriptFilePath+'''
}
stop() {
        start-stop-daemon -K -q -p $PID_FILE
}
restart() {
        stop
        sleep 1
        start
}

case "$1" in
  start)
        start
        ;;
  stop)
        stop
        ;;
  restart|reload)
        restart
        ;;
  *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
esac

exit $?
}}
'''
        if context.SkipSudoActions:
            Logger.Warn("Skipping service file creation, registration, and starting due to skip sudo actions flag.")
            return

        # Write the run script
        Logger.Debug("Run script file contents to write: "+runScriptContents)
        Logger.Info("Creating service run script...")
        with open(runScriptFilePath, "w", encoding="utf-8") as runScript:
            runScript.write(runScriptContents)

        # Make the script executable.
        Logger.Info("Making the run script executable...")
        Util.RunShellCommand(f"chmod +x {runScriptFilePath}")

        # The file name is specific to the K1 and it's set in the Configure step.
        Logger.Debug("Service config file contents to write: "+serviceFileContents)
        Logger.Info("Creating service file "+context.ServiceFilePath+"...")
        with open(context.ServiceFilePath, "w", encoding="utf-8") as serviceFile:
            serviceFile.write(serviceFileContents)

        # Make the script executable.
        Logger.Info("Making the service executable...")
        Util.RunShellCommand(f"chmod +x {context.ServiceFilePath}")

        # Use the common restart logic.
        Logger.Info("Starting the service...")
        Service.RestartK1Service(context.ServiceFilePath)

        Logger.Info("Service setup and start complete!")


    @staticmethod
    def RestartK1Service(serviceFilePath:str, throwOnBadReturnCode = True):
        # These some times fail depending on the state of the service, which is fine.
        Util.RunShellCommand(f"{serviceFilePath} stop", False)

        # Using this start-stop-daemon system, if we issue too many start, stop, restarts in quickly, the PID file gets out of
        # sync and multiple process can spawn. That's bad because the websockets will disconnect each other.
        # So we will run this run command to ensure that all of the process are dead, before we start a new one.
        Util.RunShellCommand("ps -ef | grep 'moonraker_octoapp' | grep -v grep | awk '{print $1}' | xargs -r kill -9", throwOnBadReturnCode)
        Util.RunShellCommand(f"{serviceFilePath} start", throwOnBadReturnCode)


    @staticmethod
    def RestartSonicPadService(serviceFilePath:str, throwOnBadReturnCode = True):
        # These some times fail depending on the state of the service, which is fine.
        Util.RunShellCommand(f"{serviceFilePath} stop", False)
        Util.RunShellCommand(f"{serviceFilePath} reload", False)
        Util.RunShellCommand(f"{serviceFilePath} enable" , False)
        Util.RunShellCommand(f"{serviceFilePath} start", throwOnBadReturnCode)


    @staticmethod
    def RestartDebianService(serviceName:str, throwOnBadReturnCode = True):
        (returnCode, output, errorOut) = Util.RunShellCommand("systemctl stop "+serviceName, throwOnBadReturnCode)
        if returnCode != 0:
            Logger.Warn(f"Service {serviceName} might have failed to stop. Output: {output} Error: {errorOut}")
        (returnCode, output, errorOut) = Util.RunShellCommand("systemctl start "+serviceName, throwOnBadReturnCode)
        if returnCode != 0:
            Logger.Warn(f"Service {serviceName} might have failed to start. Output: {output} Error: {errorOut}")
