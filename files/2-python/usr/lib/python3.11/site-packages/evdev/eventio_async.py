import asyncio
import select
import sys

from . import eventio
from .events import InputEvent

# needed for compatibility
from .eventio import EvdevError

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing import Any as Self


class ReadIterator:
    def __init__(self, device):
        self.current_batch = iter(())
        self.device = device

    # Standard iterator protocol.
    def __iter__(self) -> Self:
        return self

    def __next__(self) -> InputEvent:
        try:
            # Read from the previous batch of events.
            return next(self.current_batch)
        except StopIteration:
            r, w, x = select.select([self.device.fd], [], [])
            self.current_batch = self.device.read()
            return next(self.current_batch)

    def __aiter__(self) -> Self:
        return self

    def __anext__(self) -> "asyncio.Future[InputEvent]":
        future = asyncio.Future()
        try:
            # Read from the previous batch of events.
            future.set_result(next(self.current_batch))
        except StopIteration:

            def next_batch_ready(batch):
                try:
                    self.current_batch = batch.result()
                    future.set_result(next(self.current_batch))
                except Exception as e:
                    future.set_exception(e)

            self.device.async_read().add_done_callback(next_batch_ready)
        return future


class EventIO(eventio.EventIO):
    def _do_when_readable(self, callback):
        loop = asyncio.get_event_loop()

        def ready():
            loop.remove_reader(self.fileno())
            callback()

        loop.add_reader(self.fileno(), ready)

    def _set_result(self, future, cb):
        try:
            future.set_result(cb())
        except Exception as error:
            future.set_exception(error)

    def async_read_one(self):
        """
        Asyncio coroutine to read and return a single input event as
        an instance of :class:`InputEvent <evdev.events.InputEvent>`.
        """
        future = asyncio.Future()
        self._do_when_readable(lambda: self._set_result(future, self.read_one))
        return future

    def async_read(self):
        """
        Asyncio coroutine to read multiple input events from device. Return
        a generator object that yields :class:`InputEvent <evdev.events.InputEvent>`
        instances.
        """
        future = asyncio.Future()
        self._do_when_readable(lambda: self._set_result(future, self.read))
        return future

    def async_read_loop(self) -> ReadIterator:
        """
        Return an iterator that yields input events. This iterator is
        compatible with the ``async for`` syntax.

        """
        return ReadIterator(self)

    def close(self):
        try:
            loop = asyncio.get_event_loop()
            loop.remove_reader(self.fileno())
        except RuntimeError:
            # no event loop present, so there is nothing to
            # remove the reader from. Ignore
            pass
