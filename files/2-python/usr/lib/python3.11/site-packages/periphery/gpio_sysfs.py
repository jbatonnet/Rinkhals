import errno
import os
import os.path
import select
import time

from .gpio import GPIO, GPIOError


class SysfsGPIO(GPIO):
    # Number of retries to check for GPIO export or direction on open
    _GPIO_STAT_RETRIES = 10
    # Delay between check for GPIO export or direction write on open (100ms)
    _GPIO_STAT_DELAY = 0.1

    def __init__(self, line, direction):
        """**Sysfs GPIO**

        Instantiate a GPIO object and open the sysfs GPIO with the specified
        line and direction.

        `direction` can be "in" for input; "out" for output, initialized to
        low; "high" for output, initialized to high; or "low" for output,
        initialized to low.

        Args:
            line (int): GPIO line number.
            direction (str): GPIO direction, can be "in", "out", "high", or
                             "low",

        Returns:
            SysfsGPIO: GPIO object.

        Raises:
            GPIOError: if an I/O or OS error occurs.
            TypeError: if `line` or `direction`  types are invalid.
            ValueError: if `direction` value is invalid.
            TimeoutError: if waiting for GPIO export times out.

        """
        self._fd = None
        self._line = None
        self._exported = False

        self._open(line, direction)

    def __new__(self, line, direction):
        return object.__new__(SysfsGPIO)

    def _open(self, line, direction):
        if not isinstance(line, int):
            raise TypeError("Invalid line type, should be integer.")
        if not isinstance(direction, str):
            raise TypeError("Invalid direction type, should be string.")
        if direction.lower() not in ["in", "out", "high", "low"]:
            raise ValueError("Invalid direction, can be: \"in\", \"out\", \"high\", \"low\".")

        gpio_path = "/sys/class/gpio/gpio{:d}".format(line)

        if not os.path.isdir(gpio_path):
            # Export the line
            try:
                with open("/sys/class/gpio/export", "w") as f_export:
                    f_export.write("{:d}\n".format(line))
            except IOError as e:
                raise GPIOError(e.errno, "Exporting GPIO: " + e.strerror)

            # Loop until GPIO is exported
            for i in range(SysfsGPIO._GPIO_STAT_RETRIES):
                if os.path.isdir(gpio_path):
                    self._exported = True
                    break

                time.sleep(SysfsGPIO._GPIO_STAT_DELAY)

            if not self._exported:
                raise TimeoutError("Exporting GPIO: waiting for \"{:s}\" timed out".format(gpio_path))

            # Loop until direction is writable. This could take some time after
            # export as application of udev rules after export is asynchronous.
            for i in range(SysfsGPIO._GPIO_STAT_RETRIES):
                try:
                    with open(os.path.join(gpio_path, "direction"), 'w'):
                        break
                except IOError as e:
                    if e.errno != errno.EACCES or (e.errno == errno.EACCES and i == SysfsGPIO._GPIO_STAT_RETRIES - 1):
                        raise GPIOError(e.errno, "Opening GPIO direction: " + e.strerror)

                time.sleep(SysfsGPIO._GPIO_STAT_DELAY)

        # Open value
        try:
            self._fd = os.open(os.path.join(gpio_path, "value"), os.O_RDWR)
        except OSError as e:
            raise GPIOError(e.errno, "Opening GPIO: " + e.strerror)

        self._line = line
        self._path = gpio_path

        # Initialize direction
        if self.direction != direction.lower():
            self.direction = direction

    # Methods

    def read(self):
        # Read value
        try:
            buf = os.read(self._fd, 2)
        except OSError as e:
            raise GPIOError(e.errno, "Reading GPIO: " + e.strerror)

        # Rewind
        try:
            os.lseek(self._fd, 0, os.SEEK_SET)
        except OSError as e:
            raise GPIOError(e.errno, "Rewinding GPIO: " + e.strerror)

        if buf[0] == b"0"[0]:
            return False
        elif buf[0] == b"1"[0]:
            return True

        raise GPIOError(None, "Unknown GPIO value: {}".format(buf))

    def write(self, value):
        if not isinstance(value, bool):
            raise TypeError("Invalid value type, should be bool.")

        # Write value
        try:
            if value:
                os.write(self._fd, b"1\n")
            else:
                os.write(self._fd, b"0\n")
        except OSError as e:
            raise GPIOError(e.errno, "Writing GPIO: " + e.strerror)

        # Rewind
        try:
            os.lseek(self._fd, 0, os.SEEK_SET)
        except OSError as e:
            raise GPIOError(e.errno, "Rewinding GPIO: " + e.strerror)

    def poll(self, timeout=None):
        if not isinstance(timeout, (int, float, type(None))):
            raise TypeError("Invalid timeout type, should be integer, float, or None.")

        # Setup poll
        p = select.poll()
        p.register(self._fd, select.POLLPRI | select.POLLERR)

        # Scale timeout to milliseconds
        if isinstance(timeout, (int, float)) and timeout > 0:
            timeout *= 1000

        # Poll
        events = p.poll(timeout)

        # If GPIO edge interrupt occurred
        if events:
            # Rewind
            try:
                os.lseek(self._fd, 0, os.SEEK_SET)
            except OSError as e:
                raise GPIOError(e.errno, "Rewinding GPIO: " + e.strerror)

            return True

        return False

    def read_event(self):
        raise NotImplementedError()

    def close(self):
        if self._fd is None:
            return

        try:
            os.close(self._fd)
        except OSError as e:
            raise GPIOError(e.errno, "Closing GPIO: " + e.strerror)

        self._fd = None

        if self._exported:
            # Unexport the line
            try:
                unexport_fd = os.open("/sys/class/gpio/unexport", os.O_WRONLY)
                os.write(unexport_fd, "{:d}\n".format(self._line).encode())
                os.close(unexport_fd)
            except OSError as e:
                raise GPIOError(e.errno, "Unexporting GPIO: " + e.strerror)

    # Immutable properties

    @property
    def devpath(self):
        return self._path

    @property
    def fd(self):
        return self._fd

    @property
    def line(self):
        return self._line

    @property
    def name(self):
        return ""

    @property
    def label(self):
        return ""

    @property
    def chip_fd(self):
        raise NotImplementedError("Sysfs GPIO does not have a gpiochip file descriptor.")

    @property
    def chip_name(self):
        gpio_path = os.path.join(self._path, "device")

        gpiochip_path = os.readlink(gpio_path)

        if '/' not in gpiochip_path:
            raise GPIOError(None, "Reading gpiochip name: invalid device symlink \"{:s}\"".format(gpiochip_path))

        return gpiochip_path.split('/')[-1]

    @property
    def chip_label(self):
        gpio_path = "/sys/class/gpio/{:s}/label".format(self.chip_name)

        try:
            with open(gpio_path, "r") as f_label:
                label = f_label.read()
        except (GPIOError, IOError) as e:
            if isinstance(e, IOError):
                raise GPIOError(e.errno, "Reading gpiochip label: " + e.strerror)

            raise GPIOError(None, "Reading gpiochip label: " + e.strerror)

        return label.strip()

    # Mutable properties

    def _get_direction(self):
        # Read direction
        try:
            with open(os.path.join(self._path, "direction"), "r") as f_direction:
                direction = f_direction.read()
        except IOError as e:
            raise GPIOError(e.errno, "Getting GPIO direction: " + e.strerror)

        return direction.strip()

    def _set_direction(self, direction):
        if not isinstance(direction, str):
            raise TypeError("Invalid direction type, should be string.")
        if direction.lower() not in ["in", "out", "high", "low"]:
            raise ValueError("Invalid direction, can be: \"in\", \"out\", \"high\", \"low\".")

        # Write direction
        try:
            with open(os.path.join(self._path, "direction"), "w") as f_direction:
                f_direction.write(direction.lower() + "\n")
        except IOError as e:
            raise GPIOError(e.errno, "Setting GPIO direction: " + e.strerror)

    direction = property(_get_direction, _set_direction)

    def _get_edge(self):
        # Read edge
        try:
            with open(os.path.join(self._path, "edge"), "r") as f_edge:
                edge = f_edge.read()
        except IOError as e:
            raise GPIOError(e.errno, "Getting GPIO edge: " + e.strerror)

        return edge.strip()

    def _set_edge(self, edge):
        if not isinstance(edge, str):
            raise TypeError("Invalid edge type, should be string.")
        if edge.lower() not in ["none", "rising", "falling", "both"]:
            raise ValueError("Invalid edge, can be: \"none\", \"rising\", \"falling\", \"both\".")

        # Write edge
        try:
            with open(os.path.join(self._path, "edge"), "w") as f_edge:
                f_edge.write(edge.lower() + "\n")
        except IOError as e:
            raise GPIOError(e.errno, "Setting GPIO edge: " + e.strerror)

    edge = property(_get_edge, _set_edge)

    def _get_bias(self):
        raise NotImplementedError("Sysfs GPIO does not support line bias property.")

    def _set_bias(self, bias):
        raise NotImplementedError("Sysfs GPIO does not support line bias property.")

    bias = property(_get_bias, _set_bias)

    def _get_drive(self):
        raise NotImplementedError("Sysfs GPIO does not support line drive property.")

    def _set_drive(self, drive):
        raise NotImplementedError("Sysfs GPIO does not support line drive property.")

    drive = property(_get_drive, _set_drive)

    def _get_inverted(self):
        # Read active_low
        try:
            with open(os.path.join(self._path, "active_low"), "r") as f_inverted:
                inverted = f_inverted.read().strip()
        except IOError as e:
            raise GPIOError(e.errno, "Getting GPIO active_low: " + e.strerror)

        if inverted == "0":
            return False
        elif inverted == "1":
            return True

        raise GPIOError(None, "Unknown GPIO active_low value: {}".format(inverted))

    def _set_inverted(self, inverted):
        if not isinstance(inverted, bool):
            raise TypeError("Invalid drive type, should be bool.")

        # Write active_low
        try:
            with open(os.path.join(self._path, "active_low"), "w") as f_active_low:
                f_active_low.write("1\n" if inverted else "0\n")
        except IOError as e:
            raise GPIOError(e.errno, "Setting GPIO active_low: " + e.strerror)

    inverted = property(_get_inverted, _set_inverted)

    # String representation

    def __str__(self):
        try:
            str_direction = self.direction
        except GPIOError:
            str_direction = "<error>"

        try:
            str_edge = self.edge
        except GPIOError:
            str_edge = "<error>"

        try:
            str_chip_name = self.chip_name
        except GPIOError:
            str_chip_name = "<error>"

        try:
            str_chip_label = self.chip_label
        except GPIOError:
            str_chip_label = "<error>"

        try:
            str_inverted = str(self.inverted)
        except GPIOError:
            str_inverted = "<error>"

        return "GPIO {:d} (device={:s}, fd={:d}, direction={:s}, edge={:s}, inverted={:s}, chip_name=\"{:s}\", chip_label=\"{:s}\", type=sysfs)" \
            .format(self._line, self._path, self._fd, str_direction, str_edge, str_inverted, str_chip_name, str_chip_label)
