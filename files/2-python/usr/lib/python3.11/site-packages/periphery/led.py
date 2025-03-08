import os
import os.path


class LEDError(IOError):
    """Base class for LED errors."""
    pass


class LED(object):
    def __init__(self, name, brightness=None):
        """Instantiate an LED object and open the sysfs LED corresponding to
        the specified name.

        `brightness` can be a boolean for on/off, integer value for a specific
        brightness, or None to preserve existing brightness. Default is
        preserve existing brightness.

        Args:
            name (str): Linux led name.
            brightness (bool, int, None): Initial brightness.

        Returns:
            LED: LED object.

        Raises:
            LEDError: if an I/O or OS error occurs.
            TypeError: if `name` or `brightness` types are invalid.
            LookupError: if LED name does not exist.
            ValueError: if `brightness` value is invalid.

        """
        self._path = None
        self._fd = None
        self._name = None
        self._max_brightness = None
        self._open(name, brightness)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, t, value, traceback):
        self.close()

    def _open(self, name, brightness):
        if not isinstance(name, str):
            raise TypeError("Invalid name type, should be string.")
        if not isinstance(brightness, (bool, int, type(None))):
            raise TypeError("Invalid brightness type, should be bool, int, or None.")

        led_path = "/sys/class/leds/{:s}".format(name)

        if not os.path.isdir(led_path):
            raise LookupError("Opening LED: LED \"{:s}\" not found.".format(name))

        # Read max brightness
        try:
            with open(os.path.join(led_path, "max_brightness"), "r") as f_max_brightness:
                self._max_brightness = int(f_max_brightness.read())
        except IOError as e:
            raise LEDError(e.errno, "Reading LED max brightness: " + e.strerror)

        # Open brightness
        try:
            self._fd = os.open(os.path.join(led_path, "brightness"), os.O_RDWR)
        except OSError as e:
            raise LEDError(e.errno, "Opening LED brightness: " + e.strerror)

        self._name = name
        self._path = led_path

        # Set initial brightness
        if brightness:
            self.write(brightness)

    # Methods

    def read(self):
        """Read the brightness of the LED.

        Returns:
            int: Current brightness.

        Raises:
            LEDError: if an I/O or OS error occurs.

        """
        # Read value
        try:
            buf = os.read(self._fd, 8)
        except OSError as e:
            raise LEDError(e.errno, "Reading LED brightness: " + e.strerror)

        # Rewind
        try:
            os.lseek(self._fd, 0, os.SEEK_SET)
        except OSError as e:
            raise LEDError(e.errno, "Rewinding LED brightness: " + e.strerror)

        return int(buf)

    def write(self, brightness):
        """Set the brightness of the LED to `brightness`.

        `brightness` can be a boolean for on/off, or integer value for a
        specific brightness.

        Args:
            brightness (bool, int): Brightness value to set.

        Raises:
            LEDError: if an I/O or OS error occurs.
            TypeError: if `brightness` type is not bool or int.

        """
        if not isinstance(brightness, (bool, int)):
            raise TypeError("Invalid brightness type, should be bool or int.")

        if isinstance(brightness, bool):
            brightness = self._max_brightness if brightness else 0
        else:
            if not 0 <= brightness <= self._max_brightness:
                raise ValueError("Invalid brightness value: should be between 0 and {:d}".format(self._max_brightness))

        # Write value
        try:
            os.write(self._fd, "{:d}\n".format(brightness).encode())
        except OSError as e:
            raise LEDError(e.errno, "Writing LED brightness: " + e.strerror)

        # Rewind
        try:
            os.lseek(self._fd, 0, os.SEEK_SET)
        except OSError as e:
            raise LEDError(e.errno, "Rewinding LED brightness: " + e.strerror)

    def close(self):
        """Close the sysfs LED.

        Raises:
            LEDError: if an I/O or OS error occurs.

        """
        if self._fd is None:
            return

        try:
            os.close(self._fd)
        except OSError as e:
            raise LEDError(e.errno, "Closing LED: " + e.strerror)

        self._fd = None

    # Immutable properties

    @property
    def devpath(self):
        """Get the device path of the underlying sysfs LED device.

        :type: str
        """
        return self._path

    @property
    def fd(self):
        """Get the file descriptor for the underlying sysfs LED "brightness"
        file of the LED object.

        :type: int
        """
        return self._fd

    @property
    def name(self):
        """Get the sysfs LED name.

        :type: str
        """
        return self._name

    @property
    def max_brightness(self):
        """Get the LED's max brightness.

        :type: int
        """
        return self._max_brightness

    # Mutable properties

    def _get_brightness(self):
        # Read brightness
        return self.read()

    def _set_brightness(self, brightness):
        return self.write(brightness)

    brightness = property(_get_brightness, _set_brightness)
    """Get or set the LED's brightness.

    Value can be a boolean for on/off, or integer value a for specific
    brightness.

    Raises:
        LEDError: if an I/O or OS error occurs.
        TypeError: if `brightness` type is not bool or int.
        ValueError: if `brightness` value is invalid.

    :type: int
    """

    # String representation

    def __str__(self):
        return "LED {:s} (device={:s}, fd={:d}, max_brightness={:d})".format(self._name, self._path, self._fd, self._max_brightness)
