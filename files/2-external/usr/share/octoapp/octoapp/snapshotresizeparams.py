
#  A class argument that allows requesters to resize down and crop the image if desired.
class SnapshotResizeParams:

    def __init__(self, size, resizeToHeight = False, resizeToWidth = False, cropSquareCenterNoPadding = False):
        # The size that will be used for the resize.
        self.Size = size
        if self.Size < 2:
            raise Exception("SnapshotResize size can't be less than 2.")

        #
        # Note only one of the flags below should be set.
        #
        # If set to True, the size will be used for the height, and the width will be adjusted according to the aspect ratio.
        self.ResizeToHeight = resizeToHeight
        # If set to True, the size will be used for the width, and the height will be adjusted according to the aspect ratio.
        self.ResizeToWidth = resizeToWidth
        # If set to True, the size will be used for the height and width, and the image will remain uniform, but cropped to center.
        self.CropSquareCenterNoPadding = cropSquareCenterNoPadding
