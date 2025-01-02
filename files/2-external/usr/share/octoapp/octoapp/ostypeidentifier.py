import os
import platform

from .Proto import OsType


class OsTypeIdentifier:

    #
    # Note! All of this logic and vars should stay in sync with the Moonraker installer OsType logic in Context.py and the ./install.sh script!
    #

    @staticmethod
    def DetectOsType() -> OsType:
        # Do a quick check for windows first.
        # This is only possible on OctoPrint right now.
        if platform.system().lower == "windows":
            return OsType.OsType.Windows

        # For the k1 and k1 max, we look for the "buildroot" OS.
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r", encoding="utf-8") as osInfo:
                lines = osInfo.readlines()
                for l in lines:
                    if "ID=buildroot" in l:
                        return OsType.OsType.CrealityK1

        # For the Sonic Pad, we look for the openwrt os
        if os.path.exists("/etc/openwrt_release"):
            with open("/etc/openwrt_release", "r", encoding="utf-8") as osInfo:
                lines = osInfo.readlines()
                for l in lines:
                    if "sonic" in l:
                        return OsType.OsType.CrealitySonicPad

        # Default the OS to debian.
        return OsType.OsType.Debian
