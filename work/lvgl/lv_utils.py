##############################################################################
# Event Loop module: advancing tick count and scheduling lvgl task handler.
# Import after lvgl module.
# This should be imported and used by display driver.
# Display driver should first check if an event loop is already running.
#
# Usage example with SDL:
#
#        SDL.init(auto_refresh=False)
#        # Register SDL display driver.
#        # Register SDL mouse driver
#        event_loop = lv_utils.event_loop()
#
#
# asyncio example with SDL:
#
#        SDL.init(auto_refresh=False)
#        # Register SDL display driver.
#        # Register SDL mouse driver
#        event_loop = lv_utils.event_loop(asynchronous=True)
#        asyncio.Loop.run_forever()
#
# asyncio example with ili9341:
#
#        event_loop = lv_utils.event_loop(asynchronous=True) # Optional!
#        self.disp = ili9341(asynchronous=True)
#        asyncio.Loop.run_forever()
#
# MIT license; Copyright (c) 2021 Amir Gonnen
#
##############################################################################

import lvgl as lv
import sys

# Try standard machine.Timer, or custom timer from lv_timer, if available
Timer = False
# try:
#     from machine import Timer
# except:
#     try:
#         from lv_timer import Timer
#     except:
#         if sys.platform != "darwin":
#             raise RuntimeError("Missing machine.Timer implementation!")

# Try to determine default timer id

default_timer_id = 0
if sys.platform == "pyboard":
    # stm32 only supports SW timer -1
    default_timer_id = -1

if sys.platform == "rp2":
    # rp2 only supports SW timer -1
    default_timer_id = -1

# Try importing asyncio, if available

try:
    import asyncio

    asyncio_available = True
except:
    asyncio_available = False

##############################################################################


class event_loop:
    _current_instance = None

    def __init__(
        self,
        freq=25,
        timer_id=default_timer_id,
        max_scheduled=2,
        refresh_cb=None,
        asynchronous=False,
        exception_sink=None,
    ):
        if self.is_running():
            raise RuntimeError("Event loop is already running!")

        if not lv.is_initialized():
            lv.init()

        event_loop._current_instance = self

        self.delay = 1000 // freq
        self.refresh_cb = refresh_cb
        self.exception_sink = (
            exception_sink if exception_sink else self.default_exception_sink
        )

        self.asynchronous = asynchronous
        if self.asynchronous:
            if not asyncio_available:
                raise RuntimeError(
                    "Cannot run asynchronous event loop. asyncio is not available!"
                )
            self.refresh_event = asyncio.Event()
            self.refresh_task = asyncio.create_task(self.async_refresh())
            self.timer_task = asyncio.create_task(self.async_timer())
        else:
            if Timer:
                self.timer = Timer(timer_id)
                self.timer.init(
                    mode=Timer.PERIODIC, period=self.delay, callback=self.timer_cb
                )
            self.task_handler_ref = self.task_handler  # Allocation occurs here
            self.max_scheduled = max_scheduled
            self.scheduled = 0

    def init_async(self):
        self.refresh_event = asyncio.Event()
        self.refresh_task = asyncio.create_task(self.async_refresh())
        self.timer_task = asyncio.create_task(self.async_timer())

    def deinit(self):
        if self.asynchronous:
            self.refresh_task.cancel()
            self.timer_task.cancel()
        else:
            if Timer:
                self.timer.deinit()
        event_loop._current_instance = None

    def disable(self):
        self.scheduled += self.max_scheduled

    def enable(self):
        self.scheduled -= self.max_scheduled

    @staticmethod
    def is_running():
        return event_loop._current_instance is not None

    @staticmethod
    def current_instance():
        return event_loop._current_instance

    def task_handler(self, _):
        try:
            if lv._nesting.value == 0:
                lv.task_handler()
                if self.refresh_cb:
                    self.refresh_cb()
            self.scheduled -= 1
        except Exception as e:
            if self.exception_sink:
                self.exception_sink(e)

    def tick(self):
        self.timer_cb(None)

    def run(self):
        if sys.platform == "darwin":
            while True:
                self.tick()

    def timer_cb(self, t):
        # Can be called in Interrupt context
        # Use task_handler_ref since passing self.task_handler would cause allocation.
        lv.tick_inc(self.delay)
        if self.scheduled < self.max_scheduled:
            try:
                micropython.schedule(self.task_handler_ref, 0)
                self.scheduled += 1
            except:
                pass

    async def async_refresh(self):
        while True:
            await self.refresh_event.wait()
            if True: #lv._nesting.value == 0:
                self.refresh_event.clear()
                try:
                    lv.task_handler()
                except Exception as e:
                    if self.exception_sink:
                        self.exception_sink(e)
                if self.refresh_cb:
                    self.refresh_cb()

    async def async_timer(self):
        while True:
            await asyncio.sleep(self.delay / 1000)
            lv.tick_inc(self.delay)
            self.refresh_event.set()

    def default_exception_sink(self, e):
        sys.print_exception(e)
        # event_loop.current_instance().deinit()
