class OctoAppSubPlugin():


    def __init__(self, parent):
        self.config = dict()
        self.parent = parent
        self._logger = parent._logger


    def OnAfterStartup(self):
        pass


    def OnFirmwareInfoReceived(self, comm_instance, firmware_name, firmware_data, *args, **kwargs):
        pass


    def OnApiCommand(self, command, data):
        return None


    def OnEmitWebsocketMessage(self, user, message, type, data):
        pass


    def OnPrintProgress(self, storage, path, progress):
        pass


    def OnEvent(self, event, payload):
        pass


    def OnGcodeSent(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        pass


    def OnGcodeQueued(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        return True


    def OnGcodeReceived(self, comm_instance, line, *args, **kwargs):
        pass


    def OnCurrentData(self, data):
        pass