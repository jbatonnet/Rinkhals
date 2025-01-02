from octoapp.sentry import Sentry

# A helper class that caches known file metadata info, so we don't have to pull it often.
class FileMetadataCache:

    _Instance = None

    @staticmethod
    def Init(moonrakerClient):
        FileMetadataCache._Instance = FileMetadataCache(moonrakerClient)


    @staticmethod
    def Get():
        return FileMetadataCache._Instance


    def __init__(self, moonrakerClient) -> None:
        self.MoonrakerClient = moonrakerClient
        self.FileName:str = None
        self.EstimatedPrintTimeSec:float = -1.0
        self.EstimatedFilamentUsageMm:int = -1
        self.FileSizeKBytes:int = -1
        self.LayerCount:float = -1.0
        self.FirstLayerHeight:float = -1.0
        self.LayerHeight:float = -1.0
        self.ObjectHeight:float = -1.0
        self.Modified:float = 0.0
        self.ResetCache()


    # Clears the cache from all current values.
    def ResetCache(self):
        self.FileName = None
        self.EstimatedPrintTimeSec = -1.0
        self.EstimatedFilamentUsageMm = -1
        self.FileSizeKBytes = -1
        self.LayerCount = -1.0
        self.FirstLayerHeight = -1.0
        self.LayerHeight = -1.0
        self.ObjectHeight = -1.0
        self.Modified:float = 0.0


    # If the estimated time for the print can be gotten from the file metadata, this will return it.
    # It it's not known, returns -1.0
    def GetEstimatedPrintTimeSec(self, filename:str) -> float:
        # Check to see if we have checked for this file before.
        if self.FileName is not None:
            # Check if it's the same file, case sensitive.
            if self.FileName == filename:
                # Return the last result, this maybe valid or not.
                return self.EstimatedPrintTimeSec

        # The filename changed or we don't have one at all, do a refresh now.
        self._RefreshFileMetaDataCache(filename)

        # Return the value, which could still be -1 if it failed.
        return self.EstimatedPrintTimeSec


    # If the filament usage can be gotten from the file metadata, this will return it.
    # It it's not known, returns -1
    def GetEstimatedFilamentUsageMm(self, filename:str) -> int:
        # Check to see if we have checked for this file before.
        if self.FileName is not None:
            # Check if it's the same file, case sensitive.
            if self.FileName == filename:
                # Return the last result, this maybe valid or not.
                return self.EstimatedFilamentUsageMm

        # The filename changed or we don't have one at all, do a refresh now.
        self._RefreshFileMetaDataCache(filename)

        # Return the value, which could still be -1 if it failed.
        return self.EstimatedFilamentUsageMm


    # If the file size can be gotten from the file metadata, this will return it.
    # It it's not known, returns -1
    def GetFileSizeKBytes(self, filename:str) -> int:
        # Check to see if we have checked for this file before.
        if self.FileName is not None:
            # Check if it's the same file, case sensitive.
            if self.FileName == filename:
                # Return the last result, this maybe valid or not.
                return self.FileSizeKBytes

        # The filename changed or we don't have one at all, do a refresh now.
        self._RefreshFileMetaDataCache(filename)

        # Return the value, which could still be -1 if it failed.
        return self.FileSizeKBytes


    # If the file size can be gotten from the file metadata, this will return it.
    # Any of the values will return -1 if they are unknown.
    def GetLayerInfo(self, filename:str):
        # Check to see if we have checked for this file before.
        if self.FileName is not None:
            # Check if it's the same file, case sensitive.
            if self.FileName == filename:
                # Return the last result, this maybe valid or not.
                return (self.LayerCount, self.LayerHeight, self.FirstLayerHeight, self.ObjectHeight)

        # The filename changed or we don't have one at all, do a refresh now.
        self._RefreshFileMetaDataCache(filename)

        # Return the value, which could still be -1 if it failed.
        return (self.LayerCount, self.LayerHeight, self.FirstLayerHeight, self.ObjectHeight)
    
    
    # If the file size can be gotten from the file metadata, this will return it.
    # Any of the values will return -1 if they are unknown.
    def GetModified(self, filename:str):
        # Check to see if we have checked for this file before.
        if self.FileName is not None:
            # Check if it's the same file, case sensitive.
            if self.FileName == filename:
                # Return the last result, this maybe valid or not.
                return self.Modified

        # The filename changed or we don't have one at all, do a refresh now.
        self._RefreshFileMetaDataCache(filename)

        # Return the value, which could still be -1 if it failed.
        return self.Modified
    

    # Does a refresh of the file name metadata cache.
    def _RefreshFileMetaDataCache(self, filename:str) -> None:

        # Reset everything.
        self.ResetCache()

        # Make the call.
        result = self.MoonrakerClient.SendJsonRpcRequest("server.files.metadata",
        {
            "filename": filename
        })

        # If we fail this call, just return, which will keep the cache invalid.
        if result.HasError():
            Sentry.Error("Metadata Cache", "_RefreshFileMetaDataCache failed to get file meta. "+result.GetLoggingErrorStr())
            return

        # If we got here, we know we got a good result.
        # Set the cached vars so we don't call again, even though we might not be able to get them, meaning the file doesn't have them.
        self.FileName = filename

        # Get the value, if it exists and it's valid.
        res = result.GetResult()
        if "estimated_time" in res:
            value = float(res["estimated_time"])
            if value > 0.001:
                self.EstimatedPrintTimeSec = value
        if "size" in res:
            value = int(res["size"])
            if value > 0:
                self.FileSizeKBytes = int(value / 1024)
        if "modified" in res:
            value = res["modified"]
            if value > 0:
                self.Modified = value
        if "filament_total" in res:
            value = int(res["filament_total"])
            if value > 0:
                self.EstimatedFilamentUsageMm = value
        if "layer_count" in res and res["layer_count"] is not None:
            value = float(res["layer_count"])
            if value > 0:
                self.LayerCount = value
        if "first_layer_height" in res and res["first_layer_height"] is not None:
            value = float(res["first_layer_height"])
            if value > 0:
                self.FirstLayerHeight = value
        if "layer_height" in res and res["layer_height"] is not None:
            value = float(res["layer_height"])
            if value > 0:
                self.LayerHeight = value
        if "object_height" in res and res["object_height"] is not None:
            value = float(res["object_height"])
            if value > 0:
                self.ObjectHeight = value


        Sentry.Info("Metadata Cache", f"FileMetadataCache updated for file [{filename}]; est time: {str(self.EstimatedPrintTimeSec)}, size: {str(self.FileSizeKBytes)}, filament usage: {str(self.EstimatedFilamentUsageMm)}")
