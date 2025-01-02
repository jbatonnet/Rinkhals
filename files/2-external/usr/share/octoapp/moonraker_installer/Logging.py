import os
from datetime import datetime

#
# Output Helpers
#
class BashColors:
    Green='\033[92m'
    Yellow='\033[93m'
    Magenta='\033[0;35m'
    Red="\033[1;31m"
    Cyan="\033[1;36m"
    Default="\033[0;0m"

class Logger:

    IsDebugEnabled = False
    OutputFile = None


    @staticmethod
    def InitFile(userHomePath):
        try:
            # pylint: disable=consider-using-with
            Logger.OutputFile = open(os.path.join(userHomePath, "octoapp-installer.log"), "w", encoding="utf-8")
        except Exception as e:
            print("Failed to make log file. "+str(e))


    @staticmethod
    def Finalize():
        try:
            Logger.OutputFile.flush()
            Logger.OutputFile.close()
        except Exception:
            pass


    @staticmethod
    def EnableDebugLogging():
        Logger.IsDebugEnabled = True


    @staticmethod
    def Debug(msg) -> None:
        Logger._WriteToFile("Debug", msg)
        if Logger.IsDebugEnabled is True:
            print(BashColors.Yellow+"DEBUG: "+BashColors.Green+msg+BashColors.Default)


    @staticmethod
    def Header(msg)  -> None:
        print(BashColors.Cyan+msg+BashColors.Default)
        Logger._WriteToFile("Info", msg)


    @staticmethod
    def Blank() -> None:
        print("")


    @staticmethod
    def Info(msg) -> None:
        print(BashColors.Green+msg+BashColors.Default)
        Logger._WriteToFile("Info", msg)


    @staticmethod
    def Warn(msg) -> None:
        print(BashColors.Yellow+msg+BashColors.Default)
        Logger._WriteToFile("Warn", msg)


    @staticmethod
    def Error(msg) -> None:
        print(BashColors.Red+msg+BashColors.Default)
        Logger._WriteToFile("Error", msg)


    @staticmethod
    def Purple(msg) -> None:
        print(BashColors.Magenta+msg+BashColors.Default)
        Logger._WriteToFile("Info", msg)


    @staticmethod
    def _WriteToFile(level:str, msg:str):
        try:
            Logger.OutputFile.write(str(datetime.now()) + " ["+level+"] - " + msg+"\n")
        except Exception:
            pass
