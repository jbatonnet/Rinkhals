import platform
import ctypes
import fcntl
import os
import select

from .gpio import GPIO, GPIOError, EdgeEvent


try:
    KERNEL_VERSION = tuple([int(s) for s in platform.release().split(".")[:2]])
except ValueError:
    KERNEL_VERSION = (0, 0)


_GPIO_NAME_MAX_SIZE = 32
_GPIO_V2_LINES_MAX = 64
_GPIO_V2_LINE_NUM_ATTRS_MAX = 10


class _CGpiochipInfo(ctypes.Structure):
    _fields_ = [
        ('name', ctypes.c_char * _GPIO_NAME_MAX_SIZE),
        ('label', ctypes.c_char * _GPIO_NAME_MAX_SIZE),
        ('lines', ctypes.c_uint32),
    ]


class _CGpioV2LineValues(ctypes.Structure):
    _fields_ = [
        ('bits', ctypes.c_uint64),
        ('mask', ctypes.c_uint64),
    ]


class _CGpioV2LineAttributeData(ctypes.Union):
    _fields_ = [
        ('flags', ctypes.c_uint64),
        ('values', ctypes.c_uint64),
        ('debounce_period_us', ctypes.c_uint32),
    ]


class _CGpioV2LineAttribute(ctypes.Structure):
    _fields_ = [
        ('id', ctypes.c_uint32),
        ('padding', ctypes.c_uint32),
        ('data', _CGpioV2LineAttributeData),
    ]


class _CGpioV2LineConfigAttribute(ctypes.Structure):
    _fields_ = [
        ('attr', _CGpioV2LineAttribute),
        ('mask', ctypes.c_uint64),
    ]


class _CGpioV2LineConfig(ctypes.Structure):
    _fields_ = [
        ('flags', ctypes.c_uint64),
        ('num_attrs', ctypes.c_uint32),
        ('padding', ctypes.c_uint32 * 5),
        ('attrs', _CGpioV2LineConfigAttribute * _GPIO_V2_LINE_NUM_ATTRS_MAX),
    ]


class _CGpioV2LineRequest(ctypes.Structure):
    _fields_ = [
        ('offsets', ctypes.c_uint32 * _GPIO_V2_LINES_MAX),
        ('consumer', ctypes.c_char * _GPIO_NAME_MAX_SIZE),
        ('config', _CGpioV2LineConfig),
        ('num_lines', ctypes.c_uint32),
        ('event_buffer_size', ctypes.c_uint32),
        ('padding', ctypes.c_uint32 * 5),
        ('fd', ctypes.c_int32),
    ]


class _CGpioV2LineInfo(ctypes.Structure):
    _fields_ = [
        ('name', ctypes.c_char * _GPIO_NAME_MAX_SIZE),
        ('consumer', ctypes.c_char * _GPIO_NAME_MAX_SIZE),
        ('offset', ctypes.c_uint32),
        ('num_attrs', ctypes.c_uint32),
        ('flags', ctypes.c_uint64),
        ('attrs', _CGpioV2LineAttribute * _GPIO_V2_LINE_NUM_ATTRS_MAX),
        ('padding', ctypes.c_uint32 * 4),
    ]


class _CGpioV2LineEvent(ctypes.Structure):
    _fields_ = [
        ('timestamp_ns', ctypes.c_uint64),
        ('id', ctypes.c_uint32),
        ('offset', ctypes.c_uint32),
        ('seqno', ctypes.c_uint32),
        ('line_seqno', ctypes.c_uint32),
        ('padding', ctypes.c_uint32 * 6),
    ]


class Cdev2GPIO(GPIO):
    # Constants scraped from <linux/gpio.h>
    _GPIO_GET_CHIPINFO_IOCTL = 0x8044b401
    _GPIO_V2_GET_LINEINFO_IOCTL = 0xc100b405
    _GPIO_V2_GET_LINE_IOCTL = 0xc250b407
    _GPIO_V2_LINE_GET_VALUES_IOCTL = 0xc010b40e
    _GPIO_V2_LINE_SET_CONFIG_IOCTL = 0xc110b40d
    _GPIO_V2_LINE_SET_VALUES_IOCTL = 0xc010b40f
    _GPIO_V2_LINE_ATTR_ID_OUTPUT_VALUES = 0x2
    _GPIO_V2_LINE_EVENT_RISING_EDGE = 0x1
    _GPIO_V2_LINE_EVENT_FALLING_EDGE = 0x2
    _GPIO_V2_LINE_FLAG_ACTIVE_LOW = 0x2
    _GPIO_V2_LINE_FLAG_INPUT = 0x4
    _GPIO_V2_LINE_FLAG_OUTPUT = 0x8
    _GPIO_V2_LINE_FLAG_EDGE_RISING = 0x10
    _GPIO_V2_LINE_FLAG_EDGE_FALLING = 0x20
    _GPIO_V2_LINE_FLAG_OPEN_DRAIN = 0x40
    _GPIO_V2_LINE_FLAG_OPEN_SOURCE = 0x80
    _GPIO_V2_LINE_FLAG_BIAS_PULL_UP = 0x100
    _GPIO_V2_LINE_FLAG_BIAS_PULL_DOWN = 0x200
    _GPIO_V2_LINE_FLAG_BIAS_DISABLED = 0x400
    _GPIO_V2_LINE_FLAG_EVENT_CLOCK_REALTIME = 0x800

    SUPPORTED = KERNEL_VERSION >= (5, 10)

    def __init__(self, path, line, direction, edge="none", bias="default", drive="default", inverted=False, label=None):
        """**Character device GPIO (ABI version 2)**

        Instantiate a GPIO object and open the character device GPIO with the
        specified line and direction at the specified GPIO chip path (e.g.
        "/dev/gpiochip0"). Defaults properties can be overridden with keyword
        arguments.

        Args:
            path (str): GPIO chip character device path.
            line (int, str): GPIO line number or name.
            direction (str): GPIO direction, can be "in", "out", "high", or
                             "low".
            edge (str): GPIO interrupt edge, can be "none", "rising",
                        "falling", or "both".
            bias (str): GPIO line bias, can be "default", "pull_up",
                        "pull_down", or "disable".
            drive (str): GPIO line drive, can be "default", "open_drain", or
                         "open_source".
            inverted (bool): GPIO is inverted (active low).
            label (str, None): GPIO line consumer label.

        Returns:
            Cdev2GPIO: GPIO object.

        Raises:
            GPIOError: if an I/O or OS error occurs.
            TypeError: if `path`, `line`, `direction`, `edge`, `bias`, `drive`,
                       `inverted`, or `label` types are invalid.
            ValueError: if `direction`, `edge`, `bias`, or `drive` value is
                        invalid.
            LookupError: if the GPIO line was not found by the provided name.

        """
        self._devpath = None
        self._line = None
        self._line_fd = None
        self._chip_fd = None
        self._direction = None
        self._edge = None
        self._bias = None
        self._drive = None
        self._inverted = None
        self._label = None

        self._open(path, line, direction, edge, bias, drive, inverted, label)

    def __new__(self, path, line, direction, **kwargs):
        return object.__new__(Cdev2GPIO)

    def _open(self, path, line, direction, edge, bias, drive, inverted, label):
        if not isinstance(path, str):
            raise TypeError("Invalid path type, should be string.")

        if not isinstance(line, (int, str)):
            raise TypeError("Invalid line type, should be integer or string.")

        if not isinstance(direction, str):
            raise TypeError("Invalid direction type, should be string.")
        elif direction not in ["in", "out", "high", "low"]:
            raise ValueError("Invalid direction, can be: \"in\", \"out\", \"high\", \"low\".")

        if not isinstance(edge, str):
            raise TypeError("Invalid edge type, should be string.")
        elif edge not in ["none", "rising", "falling", "both"]:
            raise ValueError("Invalid edge, can be: \"none\", \"rising\", \"falling\", \"both\".")

        if not isinstance(bias, str):
            raise TypeError("Invalid bias type, should be string.")
        elif bias not in ["default", "pull_up", "pull_down", "disable"]:
            raise ValueError("Invalid bias, can be: \"default\", \"pull_up\", \"pull_down\", \"disable\".")

        if not isinstance(drive, str):
            raise TypeError("Invalid drive type, should be string.")
        elif drive not in ["default", "open_drain", "open_source"]:
            raise ValueError("Invalid drive, can be: \"default\", \"open_drain\", \"open_source\".")

        if not isinstance(inverted, bool):
            raise TypeError("Invalid drive type, should be bool.")

        if not isinstance(label, (type(None), str)):
            raise TypeError("Invalid label type, should be None or str.")

        if isinstance(line, str):
            line = self._find_line_by_name(path, line)

        # Open GPIO chip
        try:
            self._chip_fd = os.open(path, 0)
        except OSError as e:
            raise GPIOError(e.errno, "Opening GPIO chip: " + e.strerror)

        self._devpath = path
        self._line = line
        self._label = label.encode() if label is not None else b"periphery"

        self._reopen(direction, edge, bias, drive, inverted)

    def _reopen(self, direction, edge, bias, drive, inverted):
        flags = 0

        if bias == "pull_up":
            flags |= Cdev2GPIO._GPIO_V2_LINE_FLAG_BIAS_PULL_UP
        elif bias == "pull_down":
            flags |= Cdev2GPIO._GPIO_V2_LINE_FLAG_BIAS_PULL_DOWN
        elif bias == "disable":
            flags |= Cdev2GPIO._GPIO_V2_LINE_FLAG_BIAS_DISABLED

        if drive == "open_drain":
            flags |= Cdev2GPIO._GPIO_V2_LINE_FLAG_OPEN_DRAIN
        elif drive == "open_source":
            flags |= Cdev2GPIO._GPIO_V2_LINE_FLAG_OPEN_SOURCE

        if inverted:
            flags |= Cdev2GPIO._GPIO_V2_LINE_FLAG_ACTIVE_LOW

        # FIXME this should really use GPIOHANDLE_SET_CONFIG_IOCTL instead of
        # closing and reopening, especially to preserve output value on
        # configuration changes

        # Close existing line
        if self._line_fd is not None:
            try:
                os.close(self._line_fd)
            except OSError as e:
                raise GPIOError(e.errno, "Closing existing GPIO line: " + e.strerror)

            self._line_fd = None

        line_request = _CGpioV2LineRequest()

        if direction == "in":
            flags |= Cdev2GPIO._GPIO_V2_LINE_FLAG_EDGE_RISING if edge == "rising" else Cdev2GPIO._GPIO_V2_LINE_FLAG_EDGE_FALLING if edge == "falling" else (Cdev2GPIO._GPIO_V2_LINE_FLAG_EDGE_RISING | Cdev2GPIO._GPIO_V2_LINE_FLAG_EDGE_FALLING) if edge == "both" else 0
            flags |= Cdev2GPIO._GPIO_V2_LINE_FLAG_EVENT_CLOCK_REALTIME if edge != "none" else 0

            line_request.offsets[0] = self._line
            line_request.consumer = self._label
            line_request.config.flags = flags | Cdev2GPIO._GPIO_V2_LINE_FLAG_INPUT
            line_request.num_lines = 1

            try:
                fcntl.ioctl(self._chip_fd, Cdev2GPIO._GPIO_V2_GET_LINE_IOCTL, line_request)
            except (OSError, IOError) as e:
                raise GPIOError(e.errno, "Opening input line handle: " + e.strerror)
        else:
            initial_value = True if direction == "high" else False
            initial_value ^= inverted

            line_request.offsets[0] = self._line
            line_request.consumer = self._label
            line_request.config.flags = flags | Cdev2GPIO._GPIO_V2_LINE_FLAG_OUTPUT
            line_request.config.num_attrs = 1
            line_request.config.attrs[0].attr.id = Cdev2GPIO._GPIO_V2_LINE_ATTR_ID_OUTPUT_VALUES
            line_request.config.attrs[0].attr.data.values = int(initial_value)
            line_request.config.attrs[0].mask = 0x1
            line_request.num_lines = 1

            try:
                fcntl.ioctl(self._chip_fd, Cdev2GPIO._GPIO_V2_GET_LINE_IOCTL, line_request)
            except (OSError, IOError) as e:
                raise GPIOError(e.errno, "Opening output line handle: " + e.strerror)

        self._line_fd = line_request.fd

        self._direction = "in" if direction == "in" else "out"
        self._edge = edge
        self._bias = bias
        self._drive = drive
        self._inverted = inverted

    def _find_line_by_name(self, path, line):
        # Open GPIO chip
        try:
            fd = os.open(path, 0)
        except OSError as e:
            raise GPIOError(e.errno, "Opening GPIO chip: " + e.strerror)

        # Get chip info for number of lines
        chip_info = _CGpiochipInfo()
        try:
            fcntl.ioctl(fd, Cdev2GPIO._GPIO_GET_CHIPINFO_IOCTL, chip_info)
        except (OSError, IOError) as e:
            raise GPIOError(e.errno, "Querying GPIO chip info: " + e.strerror)

        # Get each line info
        line_info = _CGpioV2LineInfo()
        found = False
        for i in range(chip_info.lines):
            line_info.offset = i
            try:
                fcntl.ioctl(fd, Cdev2GPIO._GPIO_V2_GET_LINEINFO_IOCTL, line_info)
            except (OSError, IOError) as e:
                raise GPIOError(e.errno, "Querying GPIO line info: " + e.strerror)

            if line_info.name.decode() == line:
                found = True
                break

        try:
            os.close(fd)
        except OSError as e:
            raise GPIOError(e.errno, "Closing GPIO chip: " + e.strerror)

        if found:
            return i

        raise LookupError("Opening GPIO line: GPIO line \"{:s}\" not found by name.".format(line))

    # Methods

    def read(self):
        data = _CGpioV2LineValues()

        data.mask = 0x1

        try:
            fcntl.ioctl(self._line_fd, Cdev2GPIO._GPIO_V2_LINE_GET_VALUES_IOCTL, data)
        except (OSError, IOError) as e:
            raise GPIOError(e.errno, "Getting line value: " + e.strerror)

        return bool(data.bits & 0x1)

    def write(self, value):
        if not isinstance(value, bool):
            raise TypeError("Invalid value type, should be bool.")
        elif self._direction != "out":
            raise GPIOError(None, "Invalid operation: cannot write to input GPIO")

        data = _CGpioV2LineValues()

        data.mask = 0x1
        data.bits = int(value)

        try:
            fcntl.ioctl(self._line_fd, Cdev2GPIO._GPIO_V2_LINE_SET_VALUES_IOCTL, data)
        except (OSError, IOError) as e:
            raise GPIOError(e.errno, "Setting line value: " + e.strerror)

    def poll(self, timeout=None):
        if not isinstance(timeout, (int, float, type(None))):
            raise TypeError("Invalid timeout type, should be integer, float, or None.")
        elif self._direction != "in":
            raise GPIOError(None, "Invalid operation: cannot poll output GPIO")

        # Setup poll
        p = select.poll()
        p.register(self._line_fd, select.POLLIN | select.POLLPRI | select.POLLERR)

        # Scale timeout to milliseconds
        if isinstance(timeout, (int, float)) and timeout > 0:
            timeout *= 1000

        # Poll
        events = p.poll(timeout)

        return len(events) > 0

    def read_event(self):
        if self._direction != "in":
            raise GPIOError(None, "Invalid operation: cannot read event of output GPIO")
        elif self._edge == "none":
            raise GPIOError(None, "Invalid operation: GPIO edge not set")

        try:
            buf = os.read(self._line_fd, ctypes.sizeof(_CGpioV2LineEvent))
        except OSError as e:
            raise GPIOError(e.errno, "Reading GPIO event: " + e.strerror)

        line_event = _CGpioV2LineEvent.from_buffer_copy(buf)

        if line_event.id == Cdev2GPIO._GPIO_V2_LINE_EVENT_RISING_EDGE:
            edge = "rising"
        elif line_event.id == Cdev2GPIO._GPIO_V2_LINE_EVENT_FALLING_EDGE:
            edge = "falling"
        else:
            edge = "none"

        timestamp = line_event.timestamp_ns

        return EdgeEvent(edge, timestamp)

    def close(self):
        try:
            if self._line_fd is not None:
                os.close(self._line_fd)
        except OSError as e:
            raise GPIOError(e.errno, "Closing GPIO line: " + e.strerror)

        try:
            if self._chip_fd is not None:
                os.close(self._chip_fd)
        except OSError as e:
            raise GPIOError(e.errno, "Closing GPIO chip: " + e.strerror)

        self._line_fd = None
        self._chip_fd = None
        self._edge = "none"
        self._direction = "in"
        self._line = None

    # Immutable properties

    @property
    def devpath(self):
        return self._devpath

    @property
    def fd(self):
        return self._line_fd

    @property
    def line(self):
        return self._line

    @property
    def name(self):
        line_info = _CGpioV2LineInfo()
        line_info.offset = self._line

        try:
            fcntl.ioctl(self._chip_fd, Cdev2GPIO._GPIO_V2_GET_LINEINFO_IOCTL, line_info)
        except (OSError, IOError) as e:
            raise GPIOError(e.errno, "Querying GPIO line info: " + e.strerror)

        return line_info.name.decode()

    @property
    def label(self):
        line_info = _CGpioV2LineInfo()
        line_info.offset = self._line

        try:
            fcntl.ioctl(self._chip_fd, Cdev2GPIO._GPIO_V2_GET_LINEINFO_IOCTL, line_info)
        except (OSError, IOError) as e:
            raise GPIOError(e.errno, "Querying GPIO line info: " + e.strerror)

        return line_info.consumer.decode()

    @property
    def chip_fd(self):
        return self._chip_fd

    @property
    def chip_name(self):
        chip_info = _CGpiochipInfo()

        try:
            fcntl.ioctl(self._chip_fd, Cdev2GPIO._GPIO_GET_CHIPINFO_IOCTL, chip_info)
        except (OSError, IOError) as e:
            raise GPIOError(e.errno, "Querying GPIO chip info: " + e.strerror)

        return chip_info.name.decode()

    @property
    def chip_label(self):
        chip_info = _CGpiochipInfo()

        try:
            fcntl.ioctl(self._chip_fd, Cdev2GPIO._GPIO_GET_CHIPINFO_IOCTL, chip_info)
        except (OSError, IOError) as e:
            raise GPIOError(e.errno, "Querying GPIO chip info: " + e.strerror)

        return chip_info.label.decode()

    # Mutable properties

    def _get_direction(self):
        return self._direction

    def _set_direction(self, direction):
        if not isinstance(direction, str):
            raise TypeError("Invalid direction type, should be string.")
        if direction not in ["in", "out", "high", "low"]:
            raise ValueError("Invalid direction, can be: \"in\", \"out\", \"high\", \"low\".")

        if self._direction == direction:
            return

        self._reopen(direction, "none", self._bias, self._drive, self._inverted)

    direction = property(_get_direction, _set_direction)

    def _get_edge(self):
        return self._edge

    def _set_edge(self, edge):
        if not isinstance(edge, str):
            raise TypeError("Invalid edge type, should be string.")
        if edge not in ["none", "rising", "falling", "both"]:
            raise ValueError("Invalid edge, can be: \"none\", \"rising\", \"falling\", \"both\".")

        if self._direction != "in":
            raise GPIOError(None, "Invalid operation: cannot set edge on output GPIO")

        if self._edge == edge:
            return

        self._reopen(self._direction, edge, self._bias, self._drive, self._inverted)

    edge = property(_get_edge, _set_edge)

    def _get_bias(self):
        return self._bias

    def _set_bias(self, bias):
        if not isinstance(bias, str):
            raise TypeError("Invalid bias type, should be string.")
        if bias not in ["default", "pull_up", "pull_down", "disable"]:
            raise ValueError("Invalid bias, can be: \"default\", \"pull_up\", \"pull_down\", \"disable\".")

        if self._bias == bias:
            return

        self._reopen(self._direction, self._edge, bias, self._drive, self._inverted)

    bias = property(_get_bias, _set_bias)

    def _get_drive(self):
        return self._drive

    def _set_drive(self, drive):
        if not isinstance(drive, str):
            raise TypeError("Invalid drive type, should be string.")
        if drive not in ["default", "open_drain", "open_source"]:
            raise ValueError("Invalid drive, can be: \"default\", \"open_drain\", \"open_source\".")

        if self._direction != "out" and drive != "default":
            raise GPIOError(None, "Invalid operation: cannot set line drive on input GPIO")

        if self._drive == drive:
            return

        self._reopen(self._direction, self._edge, self._bias, drive, self._inverted)

    drive = property(_get_drive, _set_drive)

    def _get_inverted(self):
        return self._inverted

    def _set_inverted(self, inverted):
        if not isinstance(inverted, bool):
            raise TypeError("Invalid drive type, should be bool.")

        if self._inverted == inverted:
            return

        self._reopen(self._direction, self._edge, self._bias, self._drive, inverted)

    inverted = property(_get_inverted, _set_inverted)

    # String representation

    def __str__(self):
        try:
            str_name = self.name
        except GPIOError:
            str_name = "<error>"

        try:
            str_label = self.label
        except GPIOError:
            str_label = "<error>"

        try:
            str_direction = self.direction
        except GPIOError:
            str_direction = "<error>"

        try:
            str_edge = self.edge
        except GPIOError:
            str_edge = "<error>"

        try:
            str_bias = self.bias
        except GPIOError:
            str_bias = "<error>"

        try:
            str_drive = self.drive
        except GPIOError:
            str_drive = "<error>"

        try:
            str_inverted = str(self.inverted)
        except GPIOError:
            str_inverted = "<error>"

        try:
            str_chip_name = self.chip_name
        except GPIOError:
            str_chip_name = "<error>"

        try:
            str_chip_label = self.chip_label
        except GPIOError:
            str_chip_label = "<error>"

        return "GPIO {:d} (name=\"{:s}\", label=\"{:s}\", device={:s}, line_fd={:d}, chip_fd={:d}, direction={:s}, edge={:s}, bias={:s}, drive={:s}, inverted={:s}, chip_name=\"{:s}\", chip_label=\"{:s}\", type=cdev)" \
            .format(self._line, str_name, str_label, self._devpath, self._line_fd, self._chip_fd, str_direction, str_edge, str_bias, str_drive, str_inverted, str_chip_name, str_chip_label)
