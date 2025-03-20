import fcntl
import functools
import os
import select
from typing import Iterator, Union

from . import _input, _uinput, ecodes
from .events import InputEvent


# --------------------------------------------------------------------------
class EvdevError(Exception):
    pass


class EventIO:
    """
    Base class for reading and writing input events.

    This class is used by :class:`InputDevice` and :class:`UInput`.

    - On, :class:`InputDevice` it used for reading user-generated events (e.g.
      key presses, mouse movements) and writing feedback events (e.g. leds,
      beeps).

    - On, :class:`UInput` it used for writing user-generated events (e.g.
      key presses, mouse movements) and reading feedback events (e.g. leds,
      beeps).
    """

    def fileno(self):
        """
        Return the file descriptor to the open event device. This makes
        it possible to pass instances directly to :func:`select.select()` and
        :class:`asyncore.file_dispatcher`.
        """
        return self.fd

    def read_loop(self) -> Iterator[InputEvent]:
        """
        Enter an endless :func:`select.select()` loop that yields input events.
        """

        while True:
            r, w, x = select.select([self.fd], [], [])
            for event in self.read():
                yield event

    def read_one(self) -> Union[InputEvent, None]:
        """
        Read and return a single input event as an instance of
        :class:`InputEvent <evdev.events.InputEvent>`.

        Return ``None`` if there are no pending input events.
        """

        # event -> (sec, usec, type, code, val)
        event = _input.device_read(self.fd)

        if event:
            return InputEvent(*event)

    def read(self) -> Iterator[InputEvent]:
        """
        Read multiple input events from device. Return a generator object that
        yields :class:`InputEvent <evdev.events.InputEvent>` instances. Raises
        `BlockingIOError` if there are no available events at the moment.
        """

        # events -> ((sec, usec, type, code, val), ...)
        events = _input.device_read_many(self.fd)

        for event in events:
            yield InputEvent(*event)

    # pylint: disable=no-self-argument
    def need_write(func):
        """
        Decorator that raises :class:`EvdevError` if there is no write access to the
        input device.
        """

        @functools.wraps(func)
        def wrapper(*args):
            fd = args[0].fd
            if fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_RDWR:
                # pylint: disable=not-callable
                return func(*args)
            msg = 'no write access to device "%s"' % args[0].path
            raise EvdevError(msg)

        return wrapper

    def write_event(self, event):
        """
        Inject an input event into the input subsystem. Events are
        queued until a synchronization event is received.

        Arguments
        ---------
        event: InputEvent
          InputEvent instance or an object with an ``event`` attribute
          (:class:`KeyEvent <evdev.events.KeyEvent>`, :class:`RelEvent
          <evdev.events.RelEvent>` etc).

        Example
        -------
        >>> ev = InputEvent(1334414993, 274296, ecodes.EV_KEY, ecodes.KEY_A, 1)
        >>> ui.write_event(ev)
        """

        if hasattr(event, "event"):
            event = event.event

        self.write(event.type, event.code, event.value)

    @need_write
    def write(self, etype: int, code: int, value: int):
        """
        Inject an input event into the input subsystem. Events are
        queued until a synchronization event is received.

        Arguments
        ---------
        etype
          event type (e.g. ``EV_KEY``).

        code
          event code (e.g. ``KEY_A``).

        value
          event value (e.g. 0 1 2 - depends on event type).

        Example
        ---------
        >>> ui.write(e.EV_KEY, e.KEY_A, 1) # key A - down
        >>> ui.write(e.EV_KEY, e.KEY_A, 0) # key A - up
        """

        _uinput.write(self.fd, etype, code, value)

    def syn(self):
        """
        Inject a ``SYN_REPORT`` event into the input subsystem. Events
        queued by :func:`write()` will be fired. If possible, events
        will be merged into an 'atomic' event.
        """

        self.write(ecodes.EV_SYN, ecodes.SYN_REPORT, 0)

    def close(self):
        pass
