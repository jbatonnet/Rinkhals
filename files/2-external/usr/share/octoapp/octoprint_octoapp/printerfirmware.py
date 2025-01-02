
from .subplugin import OctoAppSubPlugin

from octoprint.access.permissions import Permissions
from octoapp.sentry import Sentry
import flask

class OctoAppPrinterFirmwareSubPlugin(OctoAppSubPlugin):


    def __init__(self, parent):
        super().__init__(parent)
        self.firmware_info = {}


    def OnFirmwareInfoReceived(
        self, comm_instance, firmware_name, firmware_data, *args, **kwargs
    ):
        Sentry.Debug("FIRMWARE", "Received firmware info")
        self.firmware_info = firmware_data


    def OnApiCommand(self, command, data):
        if command == "getPrinterFirmware":
            if not Permissions.PLUGIN_OCTOAPP_GET_DATA.can():
                return flask.make_response("Insufficient rights", 403)
            return flask.jsonify(self.firmware_info)
        else: 
            return None