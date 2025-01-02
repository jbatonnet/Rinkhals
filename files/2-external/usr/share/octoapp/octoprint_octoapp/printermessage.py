
from .subplugin import OctoAppSubPlugin

from octoprint.events import Events

class OctoAppPrinterMessageSubPlugin(OctoAppSubPlugin):

    def __init__(self, parent):
        super().__init__(parent)


    def OnGcodeQueued(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if gcode == "M117":
            message = cmd.split(' ', 1)[1]
            self.parent.PluginState["m117"] = message
            # This causes blobs in the print when combined with the Dasboard plugin
            #self._logger.debug("MESSAGE      | M117 message changed: %s" % message)
            self.parent.SendPluginStateMessage()
            return

    
    def OnEvent(self, event, payload):    
        if event == Events.PRINT_STARTED or event == Events.PRINT_DONE or event == Events.PRINT_FAILED or event == Events.PRINT_CANCELLED:
            self.parent.PluginState["m117"] = None
            self.parent.SendPluginStateMessage()
