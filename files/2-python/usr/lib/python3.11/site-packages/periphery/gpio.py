import collections
import os
import select


class GPIOError(IOError):
    """Base class for GPIO errors."""
    pass


class EdgeEvent(collections.namedtuple('EdgeEvent', ['edge', 'timestamp'])):
    def __new__(cls, edge, timestamp):
        """EdgeEvent containing the event edge and event time reported by Linux.

        Args:
            edge (str): event edge, either "rising" or "falling".
            timestamp (int): event time in nanoseconds.
        """
        return super(EdgeEvent, cls).__new__(cls, edge, timestamp)


class GPIO(object):
    def __new__(cls, *args, **kwargs):
        if len(args) > 2:
            return CdevGPIO.__new__(cls, *args, **kwargs)
        else:
            return SysfsGPIO.__new__(cls, *args, **kwargs)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, t, value, traceback):
        self.close()

    # Methods

    def read(self):
        """Read the state of the GPIO.

        Returns:
            bool: ``True`` for high state, ``False`` for low state.

        Raises:
            GPIOError: if an I/O or OS error occurs.

        """
        raise NotImplementedError()

    def write(self, value):
        """Set the state of the GPIO to `value`.

        Args:
            value (bool): ``True`` for high state, ``False`` for low state.

        Raises:
            GPIOError: if an I/O or OS error occurs.
            TypeError: if `value` type is not bool.

        """
        raise NotImplementedError()

    def poll(self, timeout=None):
        """Poll a GPIO for the edge event configured with the .edge property
        with an optional timeout.

        For character device GPIOs, the edge event should be consumed with
        `read_event()`. For sysfs GPIOs, the edge event should be consumed with
        `read()`.

        `timeout` can be a positive number for a timeout in seconds, zero for a
        non-blocking poll, or negative or None for a blocking poll. Default is
        a blocking poll.

        Args:
            timeout (int, float, None): timeout duration in seconds.

        Returns:
            bool: ``True`` if an edge event occurred, ``False`` on timeout.

        Raises:
            GPIOError: if an I/O or OS error occurs.
            TypeError: if `timeout` type is not None or int.

        """
        raise NotImplementedError()

    def read_event(self):
        """Read the edge event that occurred with the GPIO.

        This method is intended for use with character device GPIOs and is
        unsupported by sysfs GPIOs.

        Returns:
            EdgeEvent: a namedtuple containing the string edge event that
            occurred (either ``"rising"`` or ``"falling"``), and the event time
            reported by Linux in nanoseconds.

        Raises:
            GPIOError: if an I/O or OS error occurs.
            NotImplementedError: if called on a sysfs GPIO.

        """
        raise NotImplementedError()

    @staticmethod
    def poll_multiple(gpios, timeout=None):
        """Poll multiple GPIOs for the edge event configured with the .edge
        property with an optional timeout.

        For character device GPIOs, the edge event should be consumed with
        `read_event()`. For sysfs GPIOs, the edge event should be consumed with
        `read()`.

        `timeout` can be a positive number for a timeout in seconds, zero for a
        non-blocking poll, or negative or None for a blocking poll. Default is
        a blocking poll.

        Args:
            gpios (list): list of GPIO objects to poll.
            timeout (int, float, None): timeout duration in seconds.

        Returns:
            list: list of GPIO objects for which an edge event occurred.

        Raises:
            GPIOError: if an I/O or OS error occurs.
            TypeError: if `timeout` type is not None or int.

        """
        if not isinstance(timeout, (int, float, type(None))):
            raise TypeError("Invalid timeout type, should be integer, float, or None.")

        # Setup poll
        p = select.poll()

        # Register GPIO file descriptors and build map of fd to object
        fd_gpio_map = {}
        for gpio in gpios:
            if isinstance(gpio, SysfsGPIO):
                p.register(gpio.fd, select.POLLPRI | select.POLLERR)
            else:
                p.register(gpio.fd, select.POLLIN | select.POLLRDNORM)

            fd_gpio_map[gpio.fd] = gpio

        # Scale timeout to milliseconds
        if isinstance(timeout, (int, float)) and timeout > 0:
            timeout *= 1000

        # Poll
        events = p.poll(timeout)

        # Gather GPIOs that had edge events occur
        results = []
        for (fd, _) in events:
            gpio = fd_gpio_map[fd]

            results.append(gpio)

            if isinstance(gpio, SysfsGPIO):
                # Rewind for read
                try:
                    os.lseek(fd, 0, os.SEEK_SET)
                except OSError as e:
                    raise GPIOError(e.errno, "Rewinding GPIO: " + e.strerror)

        return results

    def close(self):
        """Close the GPIO.

        Raises:
            GPIOError: if an I/O or OS error occurs.

        """
        raise NotImplementedError()

    # Immutable properties

    @property
    def devpath(self):
        """Get the device path of the underlying GPIO device.

        :type: str
        """
        raise NotImplementedError()

    @property
    def fd(self):
        """Get the line file descriptor of the GPIO object.

        :type: int
        """
        raise NotImplementedError()

    @property
    def line(self):
        """Get the GPIO object's line number.

        :type: int
        """
        raise NotImplementedError()

    @property
    def name(self):
        """Get the line name of the GPIO.

        This method is intended for use with character device GPIOs and always
        returns the empty string for sysfs GPIOs.

        :type: str
        """
        raise NotImplementedError()

    @property
    def label(self):
        """Get the line consumer label of the GPIO.

        This method is intended for use with character device GPIOs and always
        returns the empty string for sysfs GPIOs.

        :type: str
        """
        raise NotImplementedError()

    @property
    def chip_fd(self):
        """Get the GPIO chip file descriptor of the GPIO object.

        This method is intended for use with character device GPIOs and is unsupported by sysfs GPIOs.

        Raises:
            NotImplementedError: if accessed on a sysfs GPIO.

        :type: int
        """
        raise NotImplementedError()

    @property
    def chip_name(self):
        """Get the name of the GPIO chip associated with the GPIO.

        :type: str
        """
        raise NotImplementedError()

    @property
    def chip_label(self):
        """Get the label of the GPIO chip associated with the GPIO.

        :type: str
        """
        raise NotImplementedError()

    # Mutable properties

    def _get_direction(self):
        raise NotImplementedError()

    def _set_direction(self, direction):
        raise NotImplementedError()

    direction = property(_get_direction, _set_direction)
    """Get or set the GPIO's direction. Can be "in", "out", "high", "low".

    Direction "in" is input; "out" is output, initialized to low; "high" is
    output, initialized to high; and "low" is output, initialized to low.

    Raises:
        GPIOError: if an I/O or OS error occurs.
        TypeError: if `direction` type is not str.
        ValueError: if `direction` value is invalid.

    :type: str
    """

    def _get_edge(self):
        raise NotImplementedError()

    def _set_edge(self, edge):
        raise NotImplementedError()

    edge = property(_get_edge, _set_edge)
    """Get or set the GPIO's interrupt edge. Can be "none", "rising",
    "falling", "both".

    Raises:
        GPIOError: if an I/O or OS error occurs.
        TypeError: if `edge` type is not str.
        ValueError: if `edge` value is invalid.

    :type: str
    """

    def _get_bias(self):
        raise NotImplementedError()

    def _set_bias(self, bias):
        raise NotImplementedError()

    bias = property(_get_bias, _set_bias)
    """Get or set the GPIO's line bias. Can be "default", "pull_up",
    "pull_down", "disable".

    This property is not supported by sysfs GPIOs.

    Raises:
        GPIOError: if an I/O or OS error occurs.
        TypeError: if `bias` type is not str.
        ValueError: if `bias` value is invalid.

    :type: str
    """

    def _get_drive(self):
        raise NotImplementedError()

    def _set_drive(self, drive):
        raise NotImplementedError()

    drive = property(_get_drive, _set_drive)
    """Get or set the GPIO's line drive. Can be "default" (for push-pull),
    "open_drain", "open_source".

    This property is not supported by sysfs GPIOs.

    Raises:
        GPIOError: if an I/O or OS error occurs.
        TypeError: if `drive` type is not str.
        ValueError: if `drive` value is invalid.

    :type: str
    """

    def _get_inverted(self):
        raise NotImplementedError()

    def _set_inverted(self, inverted):
        raise NotImplementedError()

    inverted = property(_get_inverted, _set_inverted)
    """Get or set the GPIO's inverted (active low) property.

    Raises:
        GPIOError: if an I/O or OS error occurs.
        TypeError: if `inverted` type is not bool.

    :type: bool
    """

    # String representation

    def __str__(self):
        """Get the string representation of the GPIO.

        :type: str
        """
        raise NotImplementedError()


# Assign GPIO classes
from . import gpio_cdev1
from . import gpio_cdev2
from . import gpio_sysfs

CdevGPIO = gpio_cdev2.Cdev2GPIO if gpio_cdev2.Cdev2GPIO.SUPPORTED else gpio_cdev1.Cdev1GPIO
SysfsGPIO = gpio_sysfs.SysfsGPIO
