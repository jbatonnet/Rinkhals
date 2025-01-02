from .Logging import Logger
from .Installer import Installer

# Run the installer
try:
    i = Installer()
    i.Run()
except Exception as e:
    Logger.Error("Package handler got an exception. "+str(e))

# Allow the logger to flush.
Logger.Finalize()
