
# A simple holder of commonly used paths.
class Paths:

    # The systemd path where we expect to find moonraker service files AND where we will put our service file.
    SystemdServiceFilePath = "/etc/systemd/system"

    # For the Creality OS, the service path is different.
    # The OS is based on WRT, so it's not Debian.
    CrealityOsServiceFilePath = "/etc/init.d"

    # For the Sonic Pad, this is the path we know we will find the printer configs and printer log locations.
    # The printer data will not be standard setup, so it will be like <root folder>/printer_config, <root folder>/printer_logs
    CrealityOsUserDataPath_SonicPad = "/mnt/UDISK"

    # For the K1/K1Max, this is the path we know we will find the printer configs and printer log locations.
    # They will be the standard Klipper setup, such as printer_data/config, printer_data/logs, etc.
    CrealityOsUserDataPath_K1 = "/usr/data"


    # Returns the correct service file folder path based on the OS
    @staticmethod
    def GetServiceFileFolderPath(context) -> str:
        if context.IsCrealityOs():
            return Paths.CrealityOsServiceFilePath
        else:
            return Paths.SystemdServiceFilePath
