import threading
import certifi
import websocket
from websocket import WebSocketApp

from .sentry import Sentry

# This class gives a bit of an abstraction over the normal ws
class Client:

    def __init__(self, url, onWsOpen = None, onWsMsg = None, onWsData = None, onWsClose = None, onWsError = None, headers = None):

        # Since we also fire onWsError if there is a send error, we need to capture
        # the callback and have some vars to ensure it only gets fired once.
        self.clientWsErrorCallback = onWsError
        self.wsErrorCallbackLock = threading.Lock()
        self.hasFiredWsErrorCallback = False

        # Used to log more details about what's going on with the websocket.
        # websocket.enableTrace(True)

        # Used to indicate if the client has started to close this WS. If so, we won't fire
        # any errors.
        self.hasClientRequestedClose = False

        def OnOpen(ws):
            if onWsOpen:
                onWsOpen(self)

        def OnMsg(ws, msg):
            if onWsMsg:
                onWsMsg(self, msg)

        # Note that the API says this only takes one arg, but after looking into the code
        # _get_close_args will try to send 3 args sometimes. There have been client errors showing that
        # sometimes it tried to send 3 when we only accepted 1.
        def OnClosed(ws, _, __):
            if onWsClose:
                onWsClose(self)

        def OnData(ws, buffer, msgType, continueFlag):
            if onWsData:
                onWsData(self, buffer, msgType)

        def OnError(ws, exception):
            # For this special case, call our function.
            self.handleWsError(exception)

        # Create the websocket. Once created, this is never destroyed while this class exists.
        self.Ws = WebSocketApp(url,
                                  on_open = OnOpen,
                                  on_message = OnMsg,
                                  on_close = OnClosed,
                                  on_error = OnError,
                                  on_data = OnData,
                                  header = headers
        )


    # This can be called from our logic internally in this class or from
    # The websocket class itself
    def handleWsError(self, exception):
        # If the client is trying to close this websocket and has made the close call to do so,
        # we won't fire any more errors out of it. This can happen if a send is trying to send data
        # at the same time as the socket is closing for example.
        if self.hasClientRequestedClose:
            return

        # Since this callback can be fired from many sources, we want to ensure it only
        # gets fired once.
        with self.wsErrorCallbackLock:
            if self.hasFiredWsErrorCallback:
                return
            self.hasFiredWsErrorCallback = True

        # To prevent locking issues or other issues, spin off a thread to fire the callback.
        # This prevents the case where send() fires the callback, we don't want to overlap the
        # send path callback.
        callbackThread = threading.Thread(target=self.fireWsErrorCallbackThread, args=(exception, ))
        callbackThread.start()


    def fireWsErrorCallbackThread(self, exception):
        try:
            # Fire the error callback.
            if self.clientWsErrorCallback:
                self.clientWsErrorCallback(self, exception)

            # Now ensure the websocket is closing. Since it most likely already is,
            # ignore any exceptions.
            try:
                self.Ws.close()
            except Exception as _ :
                pass
        except Exception as e :
            Sentry.Exception("Websocket client exception in fireWsErrorCallbackThread", e)


    def RunUntilClosed(self):
        #
        # The client is responsible for sending keep alive pings the server will then pong respond to.
        # If that's not done, the connection will timeout. We will send a ping every 10 minutes.
        #
        # skip_utf8_validation=True is important, because otherwise we waste a lot of time doing slow, py based validation code.
        #
        # Important note! This websocket lib won't use certify which a Root CA store that mirrors what firefox uses.
        # Since let's encrypt updated their CA root, we need to use certify's root or the connection will likely fail.
        # The requests lib already does this, so we only need to worry about it for websockets.
        #
        # Another important note!
        # The ping_timeout is used to timeout the select() call when the websocket is waiting for data. There's a bug in the WebSocketApp
        # where it will call select() after the socket is closed, which makes select() hang until the time expires.
        # Thus we need to keep the ping_timeout low, so when this happens, it doesn't hang forever.
        try:
            self.Ws.run_forever(skip_utf8_validation=True, ping_interval=600, ping_timeout=20, sslopt={"ca_certs":certifi.where()})
        except Exception as e:
            # There's a compat issue where  run_forever will try to access "isAlive" when the socket is closing
            # "isAlive" apparently doesn't exist in some PY versions of thread, so this throws. We will ignore that error,
            # But for others we will call OnError.
            #
            # If it is the error message we will just return indication that the socket is closed.
            msg = str(e)
            if "'Thread' object has no attribute 'isAlive'" not in msg:
                self.handleWsError(e)


    def RunAsync(self):
        t = threading.Thread(target=self.RunUntilClosed, args=())
        t.daemon = True
        t.start()


    def Close(self):
        self.hasClientRequestedClose = True
        # Always try to call close, even if we have already done it.
        try:
            self.Ws.close()
        except Exception:
            pass


    def Send(self, msgBytes, isData):
        if isData:
            self.SendWithOptCode(msgBytes, websocket.ABNF.OPCODE_BINARY)
        else:
            self.SendWithOptCode(msgBytes, websocket.ABNF.OPCODE_TEXT)


    def SendWithOptCode(self, msgBytes, opcode):
        try:
            self.Ws.send(msgBytes, opcode)
        except Exception as e:
            # If any exception happens during sending, we want to report the error
            # and shutdown the entire websocket.
            self.handleWsError(e)
