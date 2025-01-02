from .sentry import Sentry
from .layerutils import LayerUtils

class NotificationUtils:
    
    NotificationCommand = "OCTOAPP_NOTIFY"
    FirstLayerCompletedAt = "FirstLayerCompletedAt" 
    ThirdLayerCompletedAt = "ThirdLayerCompletedAt" 

    @staticmethod
    def CreateNotificationCommand(message):
        return NotificationUtils.NotificationCommand + " MESSAGE=" + message
    

    @staticmethod
    def GetMessageIfNotifyCommand(line):
        def removeQuotes(s):
            if s.startswith('"') and s.endswith('"'):
                return s[1:-1]
            elif s.startswith("'") and s.endswith("'"):
                return s[1:-1]
            return s
        
        base = NotificationUtils.CreateNotificationCommand("")
        commands = [ base, ";" + base, "; " + base, "M118 E1 " + base]
        
        for command in commands:
            if line.startswith(command):
                return removeQuotes(line[len(command):])
        
    @staticmethod
    def SendScheduledNotifications(notifications, notificationHandler, filePos, lastFilePos):
        for notificationFilePos in notifications:
            if notificationFilePos > lastFilePos and filePos >= notificationFilePos:
                message = notifications[notificationFilePos]
                Sentry.Info("NOTIFICATIONS", "Sending scheduled notification at %d: %s" % (filePos, message))
                if message == NotificationUtils.FirstLayerCompletedAt:
                    notificationHandler.OnFirstLayerDone()
                elif message == NotificationUtils.ThirdLayerCompletedAt:
                    notificationHandler.OnThirdLayerDone()
                else:
                    notificationHandler.OnCustomNotification(message)
    
    @staticmethod
    def ExtractNotifications(response, stopAfterLayer3 = False):
        buffer = ""
        filePos = 0
        context = {}
        notifications = {}
    
        def processLine(line):
            context['layerCounter'] = context.get('layerCounter', 0)
            
            try:
                if LayerUtils.IsLayerChange(line, context):
                    if context['layerCounter'] <= 4:
                        Sentry.Info("NOTIFICATIONS", "Layer " + str(context['layerCounter']) + " completed at at " + str(filePos))

                    if context['layerCounter'] == 1:
                        notifications[filePos] = NotificationUtils.FirstLayerCompletedAt

                    if context['layerCounter'] == 3:
                        notifications[filePos] = NotificationUtils.ThirdLayerCompletedAt
                        if stopAfterLayer3:
                            return False

                    context['layerCounter'] += 1
                
                notifyMessage = NotificationUtils.GetMessageIfNotifyCommand(line)
                if notifyMessage is not None:
                    Sentry.Info("NOTIFICATIONS", "Custom notification at " + str(filePos))
                    notifications[filePos] = notifyMessage

            except Exception as e:
                Sentry.ExceptionNoSend("Failed to detect layer change", e)

            return True

        # Do not read by line! We need to keep track of \r and \n because they are part of the filePos
        # later used. If read by line we do not know if \r\n or \n was used
        while True:
            chunk = response.read(4096)
            if not chunk:
                break

            buffer += chunk if type(chunk) == str else chunk.decode('utf-8')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                filePos += len(line) + 1 # +1 for \n
                if processLine(line.strip()) is False:
                    Sentry.Info("NOTIFICATIONS", "Processing stopped prematurely, all notifications extracted")
                    return notifications

        if buffer:
            processLine(line)
        
        return notifications