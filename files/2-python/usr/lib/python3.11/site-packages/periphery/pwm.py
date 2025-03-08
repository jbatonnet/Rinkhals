import errno
import os
import time


class PWMError(IOError):
    """Base class for PWM errors."""
    pass


class PWM(object):
    # Number of retries to check for successful PWM export on open
    _PWM_STAT_RETRIES = 10
    # Delay between check for scucessful PWM export on open (100ms)
    _PWM_STAT_DELAY = 0.1

    def __init__(self, chip, channel):
        """Instantiate a PWM object and open the sysfs PWM corresponding to the
        specified chip and channel.

        Args:
            chip (int): PWM chip number.
            channel (int): PWM channel number.

        Returns:
            PWM: PWM object.

        Raises:
            PWMError: if an I/O or OS error occurs.
            TypeError: if `chip` or `channel` types are invalid.
            LookupError: if PWM chip does not exist.
            TimeoutError: if waiting for PWM export times out.

        """
        self._chip = None
        self._channel = None
        self._path = None
        self._period_ns = None
        self._open(chip, channel)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, t, value, traceback):
        self.close()

    def _open(self, chip, channel):
        if not isinstance(chip, int):
            raise TypeError("Invalid chip type, should be integer.")
        if not isinstance(channel, int):
            raise TypeError("Invalid channel type, should be integer.")

        chip_path = "/sys/class/pwm/pwmchip{}".format(chip)
        channel_path = "/sys/class/pwm/pwmchip{}/pwm{}".format(chip, channel)

        if not os.path.isdir(chip_path):
            raise LookupError("Opening PWM: PWM chip {} not found.".format(chip))

        if not os.path.isdir(channel_path):
            # Export the PWM
            try:
                with open(os.path.join(chip_path, "export"), "w") as f_export:
                    f_export.write("{:d}\n".format(channel))
            except IOError as e:
                raise PWMError(e.errno, "Exporting PWM channel: " + e.strerror)

            # Loop until PWM is exported
            exported = False
            for i in range(PWM._PWM_STAT_RETRIES):
                if os.path.isdir(channel_path):
                    exported = True
                    break

                time.sleep(PWM._PWM_STAT_DELAY)

            if not exported:
                raise TimeoutError("Exporting PWM: waiting for \"{:s}\" timed out".format(channel_path))

            # Loop until period is writable. This could take some time after
            # export as application of udev rules after export is asynchronous.
            for i in range(PWM._PWM_STAT_RETRIES):
                try:
                    with open(os.path.join(channel_path, "period"), 'w'):
                        break
                except IOError as e:
                    if e.errno != errno.EACCES or (e.errno == errno.EACCES and i == PWM._PWM_STAT_RETRIES - 1):
                        raise PWMError(e.errno, "Opening PWM period: " + e.strerror)

                time.sleep(PWM._PWM_STAT_DELAY)

        self._chip = chip
        self._channel = channel
        self._path = channel_path

        # Cache the period for fast duty cycle updates
        self._period_ns = self._get_period_ns()

    def close(self):
        """Close the PWM."""

        if self._channel is not None:
            # Unexport the PWM channel
            try:
                unexport_fd = os.open("/sys/class/pwm/pwmchip{}/unexport".format(self._chip), os.O_WRONLY)
                os.write(unexport_fd, "{:d}\n".format(self._channel).encode())
                os.close(unexport_fd)
            except OSError as e:
                raise PWMError(e.errno, "Unexporting PWM: " + e.strerror)

        self._chip = None
        self._channel = None

    def _write_channel_attr(self, attr, value):
        with open(os.path.join(self._path, attr), 'w') as f_attr:
            f_attr.write(value + "\n")

    def _read_channel_attr(self, attr):
        with open(os.path.join(self._path, attr), 'r') as f_attr:
            return f_attr.read().strip()

    # Methods

    def enable(self):
        """Enable the PWM output."""
        self.enabled = True

    def disable(self):
        """Disable the PWM output."""
        self.enabled = False

    # Immutable properties

    @property
    def devpath(self):
        """Get the device path of the underlying sysfs PWM device.

        :type: str
        """
        return self._path

    @property
    def chip(self):
        """Get the PWM chip number.

        :type: int
        """
        return self._chip

    @property
    def channel(self):
        """Get the PWM channel number.

        :type: int
        """
        return self._channel

    # Mutable properties

    def _get_period_ns(self):
        period_ns_str = self._read_channel_attr("period")

        try:
            period_ns = int(period_ns_str)
        except ValueError:
            raise PWMError(None, "Unknown period value: \"{:s}\"".format(period_ns_str))

        # Update our cached period
        self._period_ns = period_ns

        return period_ns

    def _set_period_ns(self, period_ns):
        if not isinstance(period_ns, int):
            raise TypeError("Invalid period type, should be int.")

        self._write_channel_attr("period", str(period_ns))

        # Update our cached period
        self._period_ns = period_ns

    period_ns = property(_get_period_ns, _set_period_ns)
    """Get or set the PWM's output period in nanoseconds.

    Raises:
        PWMError: if an I/O or OS error occurs.
        TypeError: if value type is not int.

    :type: int
    """

    def _get_duty_cycle_ns(self):
        duty_cycle_ns_str = self._read_channel_attr("duty_cycle")

        try:
            duty_cycle_ns = int(duty_cycle_ns_str)
        except ValueError:
            raise PWMError(None, "Unknown duty cycle value: \"{:s}\"".format(duty_cycle_ns_str))

        return duty_cycle_ns

    def _set_duty_cycle_ns(self, duty_cycle_ns):
        if not isinstance(duty_cycle_ns, int):
            raise TypeError("Invalid duty cycle type, should be int.")

        self._write_channel_attr("duty_cycle", str(duty_cycle_ns))

    duty_cycle_ns = property(_get_duty_cycle_ns, _set_duty_cycle_ns)
    """Get or set the PWM's output duty cycle in nanoseconds.

    Raises:
        PWMError: if an I/O or OS error occurs.
        TypeError: if value type is not int.

    :type: int
    """

    def _get_period(self):
        return float(self.period_ns) / 1e9

    def _set_period(self, period):
        if not isinstance(period, (int, float)):
            raise TypeError("Invalid period type, should be int or float.")

        # Convert period from seconds to integer nanoseconds
        self.period_ns = int(period * 1e9)

    period = property(_get_period, _set_period)
    """Get or set the PWM's output period in seconds.

    Raises:
        PWMError: if an I/O or OS error occurs.
        TypeError: if value type is not int or float.

    :type: int, float
    """

    def _get_duty_cycle(self):
        return float(self.duty_cycle_ns) / self._period_ns

    def _set_duty_cycle(self, duty_cycle):
        if not isinstance(duty_cycle, (int, float)):
            raise TypeError("Invalid duty cycle type, should be int or float.")
        elif not 0.0 <= duty_cycle <= 1.0:
            raise ValueError("Invalid duty cycle value, should be between 0.0 and 1.0.")

        # Convert duty cycle from ratio to nanoseconds
        self.duty_cycle_ns = int(duty_cycle * self._period_ns)

    duty_cycle = property(_get_duty_cycle, _set_duty_cycle)
    """Get or set the PWM's output duty cycle as a ratio from 0.0 to 1.0.

    Raises:
        PWMError: if an I/O or OS error occurs.
        TypeError: if value type is not int or float.
        ValueError: if value is out of bounds of 0.0 to 1.0.

    :type: int, float
    """

    def _get_frequency(self):
        return 1.0 / self.period

    def _set_frequency(self, frequency):
        if not isinstance(frequency, (int, float)):
            raise TypeError("Invalid frequency type, should be int or float.")

        self.period = 1.0 / frequency

    frequency = property(_get_frequency, _set_frequency)
    """Get or set the PWM's output frequency in Hertz.

    Raises:
        PWMError: if an I/O or OS error occurs.
        TypeError: if value type is not int or float.

    :type: int, float
    """

    def _get_polarity(self):
        return self._read_channel_attr("polarity")

    def _set_polarity(self, polarity):
        if not isinstance(polarity, str):
            raise TypeError("Invalid polarity type, should be str.")
        elif polarity.lower() not in ["normal", "inversed"]:
            raise ValueError("Invalid polarity, can be: \"normal\" or \"inversed\".")

        self._write_channel_attr("polarity", polarity.lower())

    polarity = property(_get_polarity, _set_polarity)
    """Get or set the PWM's output polarity. Can be "normal" or "inversed".

    Raises:
        PWMError: if an I/O or OS error occurs.
        TypeError: if value type is not str.
        ValueError: if value is invalid.

    :type: str
    """

    def _get_enabled(self):
        enabled = self._read_channel_attr("enable")

        if enabled == "1":
            return True
        elif enabled == "0":
            return False

        raise PWMError(None, "Unknown enabled value: \"{:s}\"".format(enabled))

    def _set_enabled(self, value):
        if not isinstance(value, bool):
            raise TypeError("Invalid enabled type, should be bool.")

        self._write_channel_attr("enable", "1" if value else "0")

    enabled = property(_get_enabled, _set_enabled)
    """Get or set the PWM's output enabled state.

    Raises:
        PWMError: if an I/O or OS error occurs.
        TypeError: if value type is not bool.

    :type: bool
    """

    # String representation

    def __str__(self):
        return "PWM {:d}, chip {:d} (period={:f} sec, duty_cycle={:f}%, polarity={:s}, enabled={:s})" \
            .format(self._channel, self._chip, self.period, self.duty_cycle * 100, self.polarity, str(self.enabled))
