# encoding: utf-8

import os
import warnings
import contextlib
import collections

from evdev import _input, ecodes, util
from evdev.events import InputEvent

try:
    from evdev.eventio_async import EventIO, EvdevError
except ImportError:
    from evdev.eventio import EventIO, EvdevError


# --------------------------------------------------------------------------
_AbsInfo = collections.namedtuple("AbsInfo", ["value", "min", "max", "fuzz", "flat", "resolution"])

_KbdInfo = collections.namedtuple("KbdInfo", ["repeat", "delay"])

_DeviceInfo = collections.namedtuple("DeviceInfo", ["bustype", "vendor", "product", "version"])


class AbsInfo(_AbsInfo):
    """Absolute axis information.

    A ``namedtuple`` used for storing absolute axis information -
    corresponds to the ``input_absinfo`` struct:

    Attributes
    ---------
    value
      Latest reported value for the axis.

    min
      Specifies minimum value for the axis.

    max
      Specifies maximum value for the axis.

    fuzz
      Specifies fuzz value that is used to filter noise from the
      event stream.

    flat
      Values that are within this value will be discarded by joydev
      interface and reported as 0 instead.

    resolution
      Specifies resolution for the values reported for the axis.
      Resolution for main axes (``ABS_X, ABS_Y, ABS_Z``) is reported
      in units per millimeter (units/mm), resolution for rotational
      axes (``ABS_RX, ABS_RY, ABS_RZ``) is reported in units per
      radian.

    Note
    ----
    The input core does not clamp reported values to the ``[minimum,
    maximum]`` limits, such task is left to userspace.

    """

    def __str__(self):
        return "val {}, min {}, max {}, fuzz {}, flat {}, res {}".format(*self)


class KbdInfo(_KbdInfo):
    """Keyboard repeat rate.

    Attributes
    ----------
    repeat
      Keyboard repeat rate in characters per second.

    delay
      Amount of time that a key must be depressed before it will start
      to repeat (in milliseconds).
    """

    def __str__(self):
        return "repeat {}, delay {}".format(*self)


class DeviceInfo(_DeviceInfo):
    """
    Attributes
    ----------
    bustype
    vendor
    product
    version
    """

    def __str__(self):
        msg = "bus: {:04x}, vendor {:04x}, product {:04x}, version {:04x}"
        return msg.format(*self)


class InputDevice(EventIO):
    """
    A linux input device from which input events can be read.
    """

    __slots__ = ("path", "fd", "info", "name", "phys", "uniq", "_rawcapabilities", "version", "ff_effects_count")

    def __init__(self, dev):
        """
        Arguments
        ---------
        dev : str|bytes|PathLike
          Path to input device
        """

        #: Path to input device.
        self.path = dev if not hasattr(dev, "__fspath__") else dev.__fspath__()

        # Certain operations are possible only when the device is opened in
        # read-write mode.
        try:
            fd = os.open(dev, os.O_RDWR | os.O_NONBLOCK)
        except OSError:
            fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)

        #: A non-blocking file descriptor to the device file.
        self.fd = fd

        # Returns (bustype, vendor, product, version, name, phys, capabilities).
        info_res = _input.ioctl_devinfo(self.fd)

        #: A :class:`DeviceInfo <evdev.device.DeviceInfo>` instance.
        self.info = DeviceInfo(*info_res[:4])

        #: The name of the event device.
        self.name = info_res[4]

        #: The physical topology of the device.
        self.phys = info_res[5]

        #: The unique identifier of the device.
        self.uniq = info_res[6]

        #: The evdev protocol version.
        self.version = _input.ioctl_EVIOCGVERSION(self.fd)

        #: The raw dictionary of device capabilities - see `:func:capabilities()`.
        self._rawcapabilities = _input.ioctl_capabilities(self.fd)

        #: The number of force feedback effects the device can keep in its memory.
        self.ff_effects_count = _input.ioctl_EVIOCGEFFECTS(self.fd)

    def __del__(self):
        if hasattr(self, "fd") and self.fd is not None:
            try:
                self.close()
            except (OSError, ImportError, AttributeError):
                pass

    def _capabilities(self, absinfo=True):
        res = {}

        for etype, _ecodes in self._rawcapabilities.items():
            for code in _ecodes:
                l = res.setdefault(etype, [])
                if isinstance(code, tuple):
                    if absinfo:
                        a = code[1]  # (0, 0, 0, 255, 0, 0)
                        i = AbsInfo(*a)
                        l.append((code[0], i))
                    else:
                        l.append(code[0])
                else:
                    l.append(code)

        return res

    def capabilities(self, verbose=False, absinfo=True):
        """
        Return the event types that this device supports as a mapping of
        supported event types to lists of handled event codes.

        Example
        --------
        >>> device.capabilities()
        { 1: [272, 273, 274],
          2: [0, 1, 6, 8] }

        If ``verbose`` is ``True``, event codes and types will be resolved
        to their names.

        ::

          { ('EV_KEY', 1): [('BTN_MOUSE', 272),
                            ('BTN_RIGHT', 273),
                            ('BTN_MIDDLE', 273)],
            ('EV_REL', 2): [('REL_X', 0),
                            ('REL_Y', 1),
                            ('REL_HWHEEL', 6),
                            ('REL_WHEEL', 8)] }

        Unknown codes or types will be resolved to ``'?'``.

        If ``absinfo`` is ``True``, the list of capabilities will also
        include absolute axis information in the form of
        :class:`AbsInfo` instances::

          { 3: [ (0, AbsInfo(min=0, max=255, fuzz=0, flat=0)),
                 (1, AbsInfo(min=0, max=255, fuzz=0, flat=0)) ]}

        Combined with ``verbose`` the above becomes::

          { ('EV_ABS', 3): [ (('ABS_X', 0), AbsInfo(min=0, max=255, fuzz=0, flat=0)),
                             (('ABS_Y', 1), AbsInfo(min=0, max=255, fuzz=0, flat=0)) ]}

        """

        if verbose:
            return dict(util.resolve_ecodes_dict(self._capabilities(absinfo)))
        else:
            return self._capabilities(absinfo)

    def input_props(self, verbose=False):
        """
        Get device properties and quirks.

        Example
        -------
        >>> device.input_props()
        [0, 5]

        If ``verbose`` is ``True``, input properties are resolved to their
        names. Unknown codes are resolved to ``'?'``::

        [('INPUT_PROP_POINTER', 0), ('INPUT_PROP_POINTING_STICK', 5)]

        """
        props = _input.ioctl_EVIOCGPROP(self.fd)
        if verbose:
            return util.resolve_ecodes(ecodes.INPUT_PROP, props)

        return props

    def leds(self, verbose=False):
        """
        Return currently set LED keys.

        Example
        -------
        >>> device.leds()
        [0, 1, 8, 9]

        If ``verbose`` is ``True``, event codes are resolved to their
        names. Unknown codes are resolved to ``'?'``::

        [('LED_NUML', 0), ('LED_CAPSL', 1), ('LED_MISC', 8), ('LED_MAIL', 9)]

        """
        leds = _input.ioctl_EVIOCG_bits(self.fd, ecodes.EV_LED)
        if verbose:
            return util.resolve_ecodes(ecodes.LED, leds)

        return leds

    def set_led(self, led_num, value):
        """
        Set the state of the selected LED.

        Example
        -------
        >>> device.set_led(ecodes.LED_NUML, 1)
        """
        self.write(ecodes.EV_LED, led_num, value)

    def __eq__(self, other):
        """
        Two devices are equal if their :data:`info` attributes are equal.
        """
        return isinstance(other, self.__class__) and self.info == other.info and self.path == other.path

    def __str__(self):
        msg = 'device {}, name "{}", phys "{}", uniq "{}"'
        return msg.format(self.path, self.name, self.phys, self.uniq or "")

    def __repr__(self):
        msg = (self.__class__.__name__, self.path)
        return "{}({!r})".format(*msg)

    def __fspath__(self):
        return self.path

    def close(self):
        if self.fd > -1:
            try:
                super().close()
                os.close(self.fd)
            finally:
                self.fd = -1

    def grab(self):
        """
        Grab input device using ``EVIOCGRAB`` - other applications will
        be unable to receive events until the device is released. Only
        one process can hold a ``EVIOCGRAB`` on a device.

        Warning
        -------
        Grabbing an already grabbed device will raise an ``OSError``.
        """

        _input.ioctl_EVIOCGRAB(self.fd, 1)

    def ungrab(self):
        """
        Release device if it has been already grabbed (uses `EVIOCGRAB`).

        Warning
        -------
        Releasing an already released device will raise an
        ``OSError('Invalid argument')``.
        """

        _input.ioctl_EVIOCGRAB(self.fd, 0)

    @contextlib.contextmanager
    def grab_context(self):
        """
        A context manager for the duration of which only the current
        process will be able to receive events from the device.
        """
        self.grab()
        yield
        self.ungrab()

    def upload_effect(self, effect):
        """
        Upload a force feedback effect to a force feedback device.
        """

        data = memoryview(effect).tobytes()
        ff_id = _input.upload_effect(self.fd, data)
        return ff_id

    def erase_effect(self, ff_id):
        """
        Erase a force effect from a force feedback device. This also
        stops the effect.
        """

        _input.erase_effect(self.fd, ff_id)

    @property
    def repeat(self):
        """
        Get or set the keyboard repeat rate (in characters per
        minute) and delay (in milliseconds).
        """

        return KbdInfo(*_input.ioctl_EVIOCGREP(self.fd))

    @repeat.setter
    def repeat(self, value):
        return _input.ioctl_EVIOCSREP(self.fd, *value)

    def active_keys(self, verbose=False):
        """
        Return currently active keys.

        Example
        -------

        >>> device.active_keys()
        [1, 42]

        If ``verbose`` is ``True``, key codes are resolved to their
        verbose names. Unknown codes are resolved to ``'?'``. For
        example::

          [('KEY_ESC', 1), ('KEY_LEFTSHIFT', 42)]

        """
        active_keys = _input.ioctl_EVIOCG_bits(self.fd, ecodes.EV_KEY)
        if verbose:
            return util.resolve_ecodes(ecodes.KEY, active_keys)

        return active_keys

    @property
    def fn(self):
        msg = "Please use {0}.path instead of {0}.fn".format(self.__class__.__name__)
        warnings.warn(msg, DeprecationWarning, stacklevel=2)
        return self.path

    def absinfo(self, axis_num):
        """
        Return current :class:`AbsInfo` for input device axis

        Arguments
        ---------
        axis_num : int
          EV_ABS keycode (example :attr:`ecodes.ABS_X`)

        Example
        -------
        >>> device.absinfo(ecodes.ABS_X)
        AbsInfo(value=1501, min=-32768, max=32767, fuzz=0, flat=128, resolution=0)
        """
        return AbsInfo(*_input.ioctl_EVIOCGABS(self.fd, axis_num))

    def set_absinfo(self, axis_num, value=None, min=None, max=None, fuzz=None, flat=None, resolution=None):
        """
        Update :class:`AbsInfo` values. Only specified values will be overwritten.

        Arguments
        ---------
        axis_num : int
          EV_ABS keycode (example :attr:`ecodes.ABS_X`)

        Example
        -------
        >>> device.set_absinfo(ecodes.ABS_X, min=-2000, max=2000)

        You can also unpack AbsInfo tuple that will overwrite all values

        >>> device.set_absinfo(ecodes.ABS_Y, *AbsInfo(0, -2000, 2000, 0, 15, 0))
        """

        cur_absinfo = self.absinfo(axis_num)
        new_absinfo = AbsInfo(
            value if value is not None else cur_absinfo.value,
            min if min is not None else cur_absinfo.min,
            max if max is not None else cur_absinfo.max,
            fuzz if fuzz is not None else cur_absinfo.fuzz,
            flat if flat is not None else cur_absinfo.flat,
            resolution if resolution is not None else cur_absinfo.resolution,
        )
        _input.ioctl_EVIOCSABS(self.fd, axis_num, new_absinfo)
