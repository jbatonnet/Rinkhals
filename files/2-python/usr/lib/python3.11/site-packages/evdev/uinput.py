import ctypes
import os
import platform
import re
import stat
import time
from collections import defaultdict
from typing import Union, Tuple, Dict, Sequence, Optional

from . import _uinput, ecodes, ff, util
from .device import InputDevice, AbsInfo
from .events import InputEvent

try:
    from evdev.eventio_async import EventIO
except ImportError:
    from evdev.eventio import EventIO


class UInputError(Exception):
    pass


class UInput(EventIO):
    """
    A userland input device and that can inject input events into the
    linux input subsystem.
    """

    __slots__ = (
        "name",
        "vendor",
        "product",
        "version",
        "bustype",
        "events",
        "devnode",
        "fd",
        "device",
    )

    @classmethod
    def from_device(
        cls,
        *devices: Union[InputDevice, Union[str, bytes, os.PathLike]],
        filtered_types: Tuple[int] = (ecodes.EV_SYN, ecodes.EV_FF),
        **kwargs,
    ):
        """
        Create an UInput device with the capabilities of one or more input
        devices.

        Arguments
        ---------
        devices : InputDevice|str
          Varargs of InputDevice instances or paths to input devices.

        filtered_types : Tuple[event type codes]
          Event types to exclude from the capabilities of the uinput device.

        **kwargs
          Keyword arguments to UInput constructor (i.e. name, vendor etc.).
        """

        device_instances = []
        for dev in devices:
            if not isinstance(dev, InputDevice):
                dev = InputDevice(str(dev))
            device_instances.append(dev)

        all_capabilities = defaultdict(set)

        if "max_effects" not in kwargs:
            kwargs["max_effects"] = min([dev.ff_effects_count for dev in device_instances])

        # Merge the capabilities of all devices into one dictionary.
        for dev in device_instances:
            for ev_type, ev_codes in dev.capabilities().items():
                all_capabilities[ev_type].update(ev_codes)

        for evtype in filtered_types:
            if evtype in all_capabilities:
                del all_capabilities[evtype]

        return cls(events=all_capabilities, **kwargs)

    def __init__(
        self,
        events: Optional[Dict[int, Sequence[int]]] = None,
        name: str = "py-evdev-uinput",
        vendor: int = 0x1,
        product: int = 0x1,
        version: int = 0x1,
        bustype: int = 0x3,
        devnode: str = "/dev/uinput",
        phys: str = "py-evdev-uinput",
        input_props=None,
        # CentOS 7 has sufficiently old headers that FF_MAX_EFFECTS is not defined there,
        # which causes the whole module to fail loading. Fallback on a hardcoded value of
        # FF_MAX_EFFECTS if it is not defined in the ecodes.
        max_effects=ecodes.ecodes.get("FF_MAX_EFFECTS", 96),
    ):
        """
        Arguments
        ---------
        events : dict
          Dictionary of event types mapping to lists of event codes. The
          event types and codes that the uinput device will be able to
          inject - defaults to all key codes.

        name
          The name of the input device.

        vendor
          Vendor identifier.

        product
          Product identifier.

        version
          Version identifier.

        bustype
          Bustype identifier.

        phys
          Physical path.

        input_props
          Input properties and quirks.

        max_effects
          Maximum simultaneous force-feedback effects.

        Note
        ----
        If you do not specify any events, the uinput device will be able
        to inject only ``KEY_*`` and ``BTN_*`` event codes.
        """

        self.name: str = name  #: Uinput device name.
        self.vendor: int = vendor  #: Device vendor identifier.
        self.product: int = product  #: Device product identifier.
        self.version: int = version  #: Device version identifier.
        self.bustype: int = bustype  #: Device bustype - e.g. ``BUS_USB``.
        self.phys: str = phys  #: Uinput device physical path.
        self.devnode: str = devnode  #: Uinput device node - e.g. ``/dev/uinput/``.

        if not events:
            events = {ecodes.EV_KEY: ecodes.keys.keys()}

        self._verify()

        #: Write-only, non-blocking file descriptor to the uinput device node.
        self.fd = _uinput.open(devnode)

        # Prepare the list of events for passing to _uinput.enable and _uinput.setup.
        absinfo, prepared_events = self._prepare_events(events)

        # Set phys name
        _uinput.set_phys(self.fd, phys)

        # Set properties
        input_props = input_props or []
        for prop in input_props:
            _uinput.set_prop(self.fd, prop)

        for etype, code in prepared_events:
            _uinput.enable(self.fd, etype, code)

        _uinput.setup(self.fd, name, vendor, product, version, bustype, absinfo, max_effects)

        # Create the uinput device.
        _uinput.create(self.fd)

        self.dll = ctypes.CDLL(_uinput.__file__)
        self.dll._uinput_begin_upload.restype = ctypes.c_int
        self.dll._uinput_end_upload.restype = ctypes.c_int

        #: An :class:`InputDevice <evdev.device.InputDevice>` instance
        #: for the fake input device. ``None`` if the device cannot be
        #: opened for reading and writing.
        self.device: InputDevice = self._find_device(self.fd)

    def _prepare_events(self, events):
        """Prepare events for passing to _uinput.enable and _uinput.setup"""
        absinfo, prepared_events = [], []
        for etype, codes in events.items():
            for code in codes:
                # Handle max, min, fuzz, flat.
                if isinstance(code, (tuple, list, AbsInfo)):
                    # Flatten (ABS_Y, (0, 255, 0, 0, 0, 0)) to (ABS_Y, 0, 255, 0, 0, 0, 0).
                    f = [code[0]]
                    f.extend(code[1])
                    # Ensure the tuple is always 6 ints long, since uinput.c:uinput_create
                    # does little in the way of checking the length.
                    f.extend([0] * (6 - len(code[1])))
                    absinfo.append(f)
                    code = code[0]
                prepared_events.append((etype, code))
        return absinfo, prepared_events

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        if hasattr(self, "fd"):
            self.close()

    def __repr__(self):
        # TODO:
        v = (repr(getattr(self, i)) for i in ("name", "bustype", "vendor", "product", "version", "phys"))
        return "{}({})".format(self.__class__.__name__, ", ".join(v))

    def __str__(self):
        msg = 'name "{}", bus "{}", vendor "{:04x}", product "{:04x}", version "{:04x}", phys "{}"\nevent types: {}'

        evtypes = [i[0] for i in self.capabilities(True).keys()]
        msg = msg.format(
            self.name, ecodes.BUS[self.bustype], self.vendor, self.product, self.version, self.phys, " ".join(evtypes)
        )

        return msg

    def close(self):
        # Close the associated InputDevice, if it was previously opened.
        if self.device is not None:
            self.device.close()

        # Destroy the uinput device.
        if self.fd > -1:
            _uinput.close(self.fd)
            self.fd = -1

    def capabilities(self, verbose: bool = False, absinfo: bool = True):
        """See :func:`capabilities <evdev.device.InputDevice.capabilities>`."""
        if self.device is None:
            raise UInputError("input device not opened - cannot read capabilities")

        return self.device.capabilities(verbose, absinfo)

    def begin_upload(self, effect_id):
        upload = ff.UInputUpload()
        upload.effect_id = effect_id

        ret = self.dll._uinput_begin_upload(self.fd, ctypes.byref(upload))
        if ret:
            raise UInputError("Failed to begin uinput upload: " + os.strerror(ret))

        return upload

    def end_upload(self, upload):
        ret = self.dll._uinput_end_upload(self.fd, ctypes.byref(upload))
        if ret:
            raise UInputError("Failed to end uinput upload: " + os.strerror(ret))

    def begin_erase(self, effect_id):
        erase = ff.UInputErase()
        erase.effect_id = effect_id

        ret = self.dll._uinput_begin_erase(self.fd, ctypes.byref(erase))
        if ret:
            raise UInputError("Failed to begin uinput erase: " + os.strerror(ret))
        return erase

    def end_erase(self, erase):
        ret = self.dll._uinput_end_erase(self.fd, ctypes.byref(erase))
        if ret:
            raise UInputError("Failed to end uinput erase: " + os.strerror(ret))

    def _verify(self):
        """
        Verify that an uinput device exists and is readable and writable
        by the current process.
        """
        try:
            m = os.stat(self.devnode)[stat.ST_MODE]
            assert stat.S_ISCHR(m)
        except (IndexError, OSError, AssertionError):
            msg = '"{}" does not exist or is not a character device file - verify that the uinput module is loaded'
            raise UInputError(msg.format(self.devnode))

        if not os.access(self.devnode, os.W_OK):
            msg = '"{}" cannot be opened for writing'
            raise UInputError(msg.format(self.devnode))

        if len(self.name) > _uinput.maxnamelen:
            msg = "uinput device name must not be longer than {} characters"
            raise UInputError(msg.format(_uinput.maxnamelen))

    def _find_device(self, fd: int) -> InputDevice:
        """
        Tries to find the device node. Will delegate this task to one of
        several platform-specific functions.
        """
        if platform.system() == "Linux":
            try:
                sysname = _uinput.get_sysname(fd)
                return self._find_device_linux(sysname)
            except OSError:
                # UI_GET_SYSNAME returned an error code. We're likely dealing with
                # an old kernel. Guess the device based on the filesystem.
                pass

        # If we're not running or Linux or the above method fails for any reason,
        # use the generic fallback method.
        return self._find_device_fallback()

    def _find_device_linux(self, sysname: str) -> InputDevice:
        """
        Tries to find the device node when running on Linux.
        """

        syspath = f"/sys/devices/virtual/input/{sysname}"

        # The sysfs entry for event devices should contain exactly one folder
        # whose name matches the format "event[0-9]+". It is then assumed that
        # the device node in /dev/input uses the same name.
        regex = re.compile("event[0-9]+")
        for entry in os.listdir(syspath):
            if regex.fullmatch(entry):
                device_path = f"/dev/input/{entry}"
                break
        else:  # no break
            raise FileNotFoundError()

        # It is possible that there is some delay before /dev/input/event* shows
        # up on old systems that do not use devtmpfs, so if the device cannot be
        # found, wait for a short amount and then try again once.
        #
        # Furthermore, even if devtmpfs is in use, it is possible that the device
        # does show up immediately, but without the correct permissions that
        # still need to be set by udev. Wait for up to two seconds for either the
        # device to show up or the permissions to be set.
        for attempt in range(19):
            try:
                return InputDevice(device_path)
            except (FileNotFoundError, PermissionError):
                time.sleep(0.1)

        # Last attempt. If this fails, whatever exception the last attempt raises
        # shall be the exception that this function raises.
        return InputDevice(device_path)

    def _find_device_fallback(self) -> Union[InputDevice, None]:
        """
        Tries to find the device node when UI_GET_SYSNAME is not available or
        we're running on a system sufficiently exotic that we do not know how
        to interpret its return value.
        """
        #:bug: the device node might not be immediately available
        time.sleep(0.1)

        # There could also be another device with the same name already present,
        # make sure to select the newest one.
        # Strictly speaking, we cannot be certain that everything returned by list_devices()
        # ends at event[0-9]+: it might return something like "/dev/input/events_all". Find
        # the devices that have the expected structure and extract their device number.
        path_number_pairs = []
        regex = re.compile("/dev/input/event([0-9]+)")
        for path in util.list_devices("/dev/input/"):
            regex_match = regex.fullmatch(path)
            if not regex_match:
                continue
            device_number = int(regex_match[1])
            path_number_pairs.append((path, device_number))

        # The modification date of the devnode is not reliable unfortunately, so we
        # are sorting by the number in the name
        path_number_pairs.sort(key=lambda pair: pair[1], reverse=True)

        for path, _ in path_number_pairs:
            d = InputDevice(path)
            if d.name == self.name:
                return d
