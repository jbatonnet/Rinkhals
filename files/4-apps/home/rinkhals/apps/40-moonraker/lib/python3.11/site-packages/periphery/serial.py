import os
import fcntl
import array
import termios
import select


class SerialError(IOError):
    """Base class for Serial errors."""
    pass


class Serial(object):
    _DATABITS_TO_CFLAG = {
        5: termios.CS5, 6: termios.CS6, 7: termios.CS7, 8: termios.CS8
    }
    _CFLAG_TO_DATABITS = {v: k for k, v in _DATABITS_TO_CFLAG.items()}

    _BAUDRATE_TO_OSPEED = {
        50: termios.B50, 75: termios.B75, 110: termios.B110, 134: termios.B134,
        150: termios.B150, 200: termios.B200, 300: termios.B300,
        600: termios.B600, 1200: termios.B1200, 1800: termios.B1800,
        2400: termios.B2400, 4800: termios.B4800, 9600: termios.B9600,
        19200: termios.B19200, 38400: termios.B38400, 57600: termios.B57600,
        115200: termios.B115200, 230400: termios.B230400,
        # Linux baudrates bits missing in termios module included below
        460800: 0x1004, 500000: 0x1005, 576000: 0x1006,
        921600: 0x1007, 1000000: 0x1008, 1152000: 0x1009,
        1500000: 0x100A, 2000000: 0x100B, 2500000: 0x100C,
        3000000: 0x100D, 3500000: 0x100E, 4000000: 0x100F,
    }
    _OSPEED_TO_BAUDRATE = {v: k for k, v in _BAUDRATE_TO_OSPEED.items()}

    def __init__(self, devpath, baudrate, databits=8, parity="none", stopbits=1, xonxoff=False, rtscts=False):
        """Instantiate a Serial object and open the tty device at the specified
        path with the specified baudrate, and the defaults of 8 data bits, no
        parity, 1 stop bit, no software flow control (xonxoff), and no hardware
        flow control (rtscts).

        Args:
            devpath (str): tty device path.
            baudrate (int): baudrate.
            databits (int): data bits, can be 5, 6, 7, 8.
            parity (str): parity, can be "none", "even", "odd".
            stopbits (int): stop bits, can be 1 or 2.
            xonxoff (bool): software flow control.
            rtscts (bool): hardware flow control.

        Returns:
            Serial: Serial object.

        Raises:
            SerialError: if an I/O or OS error occurs.
            TypeError: if `devpath`, `baudrate`, `databits`, `parity`, `stopbits`, `xonxoff`, or `rtscts` types are invalid.
            ValueError: if `baudrate`, `databits`, `parity`, or `stopbits` values are invalid.

        """
        self._fd = None
        self._devpath = None
        self._use_termios_timeout = False
        self._open(devpath, baudrate, databits, parity, stopbits, xonxoff, rtscts)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, t, value, traceback):
        self.close()

    def _open(self, devpath, baudrate, databits, parity, stopbits, xonxoff, rtscts):
        if not isinstance(devpath, str):
            raise TypeError("Invalid devpath type, should be string.")
        elif not isinstance(baudrate, int):
            raise TypeError("Invalid baud rate type, should be integer.")
        elif not isinstance(databits, int):
            raise TypeError("Invalid data bits type, should be integer.")
        elif not isinstance(parity, str):
            raise TypeError("Invalid parity type, should be string.")
        elif not isinstance(stopbits, int):
            raise TypeError("Invalid stop bits type, should be integer.")
        elif not isinstance(xonxoff, bool):
            raise TypeError("Invalid xonxoff type, should be boolean.")
        elif not isinstance(rtscts, bool):
            raise TypeError("Invalid rtscts type, should be boolean.")

        if baudrate not in Serial._BAUDRATE_TO_OSPEED:
            raise ValueError("Unknown baud rate: {:d}".format(baudrate))
        elif databits not in [5, 6, 7, 8]:
            raise ValueError("Invalid data bits, can be 5, 6, 7, 8.")
        elif parity.lower() not in ["none", "even", "odd"]:
            raise ValueError("Invalid parity, can be: \"none\", \"even\", \"odd\".")
        elif stopbits not in [1, 2]:
            raise ValueError("Invalid stop bits, can be 1, 2.")

        # Open tty
        try:
            self._fd = os.open(devpath, os.O_RDWR | os.O_NOCTTY)
        except OSError as e:
            raise SerialError(e.errno, "Opening serial port: " + e.strerror)

        self._devpath = devpath

        parity = parity.lower()

        (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = (0, 0, 0, 0, 0, 0, [0] * 32)

        ###
        # iflag

        # Ignore break characters
        iflag = termios.IGNBRK

        # Setup parity
        if parity != "none":
            iflag |= (termios.INPCK | termios.ISTRIP)

        # Setup xonxoff
        if xonxoff:
            iflag |= (termios.IXON | termios.IXOFF)

        #######
        # oflag
        oflag = 0

        #######
        # lflag
        lflag = 0

        #######
        # cflag

        # Enable receiver, ignore modem control lines
        cflag = (termios.CREAD | termios.CLOCAL)

        # Setup data bits
        cflag |= Serial._DATABITS_TO_CFLAG[databits]

        # Setup parity
        if parity == "even":
            cflag |= termios.PARENB
        elif parity == "odd":
            cflag |= (termios.PARENB | termios.PARODD)

        # Setup stop bits
        if stopbits == 2:
            cflag |= termios.CSTOPB

        # Setup rtscts
        if rtscts:
            cflag |= termios.CRTSCTS

        # Setup baud rate
        cflag |= Serial._BAUDRATE_TO_OSPEED[baudrate]

        ########
        # ispeed
        ispeed = Serial._BAUDRATE_TO_OSPEED[baudrate]

        ########
        # ospeed
        ospeed = Serial._BAUDRATE_TO_OSPEED[baudrate]

        # Set tty attributes
        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

        self._use_termios_timeout = False

    # Methods

    def read(self, length, timeout=None):
        """Read up to `length` number of bytes from the serial port with an
        optional timeout.

        `timeout` can be positive for a blocking read with a timeout in
        seconds, zero for a non-blocking read, or negative or None for a
        blocking read that will block until `length` number of bytes are read.
        Default is a blocking read.

        For a non-blocking or timeout-bound read, `read()` may return less than
        the requested number of bytes.

        For a blocking read with the VMIN setting configured, `read()` will
        block until at least VMIN bytes are read. For a blocking read with both
        VMIN and VTIME settings configured, `read()` will block until at least
        VMIN bytes are read or the VTIME interbyte timeout expires after the
        last byte read. In either case, `read()` may return less than the
        requested number of bytes.

        Args:
            length (int): length in bytes.
            timeout (int, float, None): timeout duration in seconds.

        Returns:
            bytes: data read.

        Raises:
            SerialError: if an I/O or OS error occurs.

        """
        data = b""

        while len(data) < length:
            (rlist, _, _) = select.select([self._fd], [], [], timeout)
            if self._fd not in rlist:
                break

            try:
                chunk = os.read(self._fd, length - len(data))
            except OSError as e:
                raise SerialError(e.errno, "Reading serial port: " + e.strerror)

            if self._use_termios_timeout:
                return chunk

            if not chunk:
                raise SerialError(0, "Reading serial port: unexpected empty read")

            data += chunk

        return data

    def write(self, data):
        """Write `data` to the serial port and return the number of bytes
        written.

        Args:
            data (bytes, bytearray, list): a byte array or list of 8-bit integers to write.

        Returns:
            int: number of bytes written.

        Raises:
            SerialError: if an I/O or OS error occurs.
            TypeError: if `data` type is invalid.
            ValueError: if data is not valid bytes.

        """
        if not isinstance(data, (bytes, bytearray, list)):
            raise TypeError("Invalid data type, should be bytes, bytearray, or list.")

        if isinstance(data, list):
            data = bytearray(data)

        try:
            return os.write(self._fd, data)
        except OSError as e:
            raise SerialError(e.errno, "Writing serial port: " + e.strerror)

    def poll(self, timeout=None):
        """Poll for data available for reading from the serial port with an
        optional timeout.

        `timeout` can be positive for a timeout in seconds, zero for a
        non-blocking poll, or negative or None for a blocking poll. Default is
        a blocking poll.

        Args:
            timeout (int, float, None): timeout duration in seconds.

        Returns:
            bool: ``True`` if data is available for reading from the serial port, ``False`` if not.

        """
        p = select.poll()
        p.register(self._fd, select.POLLIN | select.POLLPRI)
        events = p.poll(int(timeout * 1000))

        if len(events) > 0:
            return True

        return False

    def flush(self):
        """Flush the write buffer of the serial port, blocking until all bytes
        are written.

        Raises:
            SerialError: if an I/O or OS error occurs.

        """
        try:
            termios.tcdrain(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Flushing serial port: " + e.strerror)

    def input_waiting(self):
        """Query the number of bytes waiting to be read from the serial port.

        Returns:
            int: number of bytes waiting to be read.

        Raises:
            SerialError: if an I/O or OS error occurs.

        """
        # Get input waiting
        buf = array.array('I', [0])
        try:
            fcntl.ioctl(self._fd, termios.TIOCINQ, buf, True)
        except (OSError, IOError) as e:
            raise SerialError(e.errno, "Querying input waiting: " + e.strerror)

        return buf[0]

    def output_waiting(self):
        """Query the number of bytes waiting to be written to the serial port.

        Returns:
            int: number of bytes waiting to be written.

        Raises:
            SerialError: if an I/O or OS error occurs.

        """
        # Get input waiting
        buf = array.array('I', [0])
        try:
            fcntl.ioctl(self._fd, termios.TIOCOUTQ, buf, True)
        except (OSError, IOError) as e:
            raise SerialError(e.errno, "Querying output waiting: " + e.strerror)

        return buf[0]

    def close(self):
        """Close the tty device.

        Raises:
            SerialError: if an I/O or OS error occurs.

        """
        if self._fd is None:
            return

        try:
            os.close(self._fd)
        except OSError as e:
            raise SerialError(e.errno, "Closing serial port: " + e.strerror)

        self._fd = None

    # Immutable properties

    @property
    def fd(self):
        """Get the file descriptor of the underlying tty device.

        :type: int
        """
        return self._fd

    @property
    def devpath(self):
        """Get the device path of the underlying tty device.

        :type: str
        """
        return self._devpath

    # Mutable properties

    def _get_baudrate(self):
        # Get tty attributes
        try:
            (_, _, _, _, _, ospeed, _) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        if ospeed not in Serial._OSPEED_TO_BAUDRATE:
            raise SerialError(None, "Unknown baud rate: ospeed 0x{:x}".format(ospeed))

        return Serial._OSPEED_TO_BAUDRATE[ospeed]

    def _set_baudrate(self, baudrate):
        if not isinstance(baudrate, int):
            raise TypeError("Invalid baud rate type, should be integer.")

        if baudrate not in Serial._BAUDRATE_TO_OSPEED:
            raise ValueError("Unknown baud rate: {:d}".format(baudrate))

        # Get tty attributes
        try:
            (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        # Modify tty attributes
        cflag &= ~(termios.CBAUD | termios.CBAUDEX)
        cflag |= Serial._BAUDRATE_TO_OSPEED[baudrate]
        ispeed = Serial._BAUDRATE_TO_OSPEED[baudrate]
        ospeed = Serial._BAUDRATE_TO_OSPEED[baudrate]

        # Set tty attributes
        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

    baudrate = property(_get_baudrate, _set_baudrate)
    """Get or set the baudrate.

    Raises:
        SerialError: if an I/O or OS error occurs.
        TypeError: if `baudrate` type is not int.
        ValueError: if `baudrate` value is not supported.

    :type: int
    """

    def _get_databits(self):
        # Get tty attributes
        try:
            (_, _, cflag, _, _, _, _) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        cs = cflag & termios.CSIZE

        if cs not in Serial._CFLAG_TO_DATABITS:
            raise SerialError(None, "Unknown data bits setting: csize 0x{:x}".format(cs))

        return Serial._CFLAG_TO_DATABITS[cs]

    def _set_databits(self, databits):
        if not isinstance(databits, int):
            raise TypeError("Invalid data bits type, should be integer.")
        elif databits not in [5, 6, 7, 8]:
            raise ValueError("Invalid data bits, can be 5, 6, 7, 8.")

        # Get tty attributes
        try:
            (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        # Modify tty attributes
        cflag &= ~termios.CSIZE
        cflag |= Serial._DATABITS_TO_CFLAG[databits]

        # Set tty attributes
        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

    databits = property(_get_databits, _set_databits)
    """Get or set the data bits. Can be 5, 6, 7, 8.

    Raises:
        SerialError: if an I/O or OS error occurs.
        TypeError: if `databits` type is not int.
        ValueError: if `databits` value is invalid.

    :type: int
    """

    def _get_parity(self):
        # Get tty attributes
        try:
            (_, _, cflag, _, _, _, _) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        if (cflag & termios.PARENB) == 0:
            return "none"
        elif (cflag & termios.PARODD) == 0:
            return "even"
        else:
            return "odd"

    def _set_parity(self, parity):
        if not isinstance(parity, str):
            raise TypeError("Invalid parity type, should be string.")
        elif parity.lower() not in ["none", "even", "odd"]:
            raise ValueError("Invalid parity, can be: \"none\", \"even\", \"odd\".")

        parity = parity.lower()

        # Get tty attributes
        try:
            (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        # Modify tty attributes
        iflag &= ~(termios.INPCK | termios.ISTRIP)
        cflag &= ~(termios.PARENB | termios.PARODD)
        if parity != "none":
            iflag |= (termios.INPCK | termios.ISTRIP)
            cflag |= termios.PARENB
        if parity == "odd":
            cflag |= termios.PARODD

        # Set tty attributes
        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

    parity = property(_get_parity, _set_parity)
    """Get or set the parity. Can be "none", "even", "odd".

    Raises:
        SerialError: if an I/O or OS error occurs.
        TypeError: if `parity` type is not str.
        ValueError: if `parity` value is invalid.

    :type: str
    """

    def _get_stopbits(self):
        # Get tty attributes
        try:
            (_, _, cflag, _, _, _, _) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        if (cflag & termios.CSTOPB) != 0:
            return 2
        else:
            return 1

    def _set_stopbits(self, stopbits):
        if not isinstance(stopbits, int):
            raise TypeError("Invalid stop bits type, should be integer.")
        elif stopbits not in [1, 2]:
            raise ValueError("Invalid stop bits, can be 1, 2.")

        # Get tty attributes
        try:
            (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        # Modify tty attributes
        cflag &= ~termios.CSTOPB
        if stopbits == 2:
            cflag |= termios.CSTOPB

        # Set tty attributes
        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

    stopbits = property(_get_stopbits, _set_stopbits)
    """Get or set the stop bits. Can be 1 or 2.

    Raises:
        SerialError: if an I/O or OS error occurs.
        TypeError: if `stopbits` type is not int.
        ValueError: if `stopbits` value is invalid.

    :type: int
    """

    def _get_xonxoff(self):
        # Get tty attributes
        try:
            (iflag, _, _, _, _, _, _) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        if (iflag & (termios.IXON | termios.IXOFF)) != 0:
            return True
        else:
            return False

    def _set_xonxoff(self, enabled):
        if not isinstance(enabled, bool):
            raise TypeError("Invalid enabled type, should be boolean.")

        # Get tty attributes
        try:
            (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        # Modify tty attributes
        iflag &= ~(termios.IXON | termios.IXOFF | termios.IXANY)
        if enabled:
            iflag |= (termios.IXON | termios.IXOFF)

        # Set tty attributes
        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

    xonxoff = property(_get_xonxoff, _set_xonxoff)
    """Get or set software flow control.

    Raises:
        SerialError: if an I/O or OS error occurs.
        TypeError: if `xonxoff` type is not bool.

    :type: bool
    """

    def _get_rtscts(self):
        # Get tty attributes
        try:
            (_, _, cflag, _, _, _, _) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        if (cflag & termios.CRTSCTS) != 0:
            return True
        else:
            return False

    def _set_rtscts(self, enabled):
        if not isinstance(enabled, bool):
            raise TypeError("Invalid enabled type, should be boolean.")

        # Get tty attributes
        try:
            (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        # Modify tty attributes
        cflag = ~termios.CRTSCTS
        if enabled:
            cflag |= termios.CRTSCTS

        # Set tty attributes
        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

    rtscts = property(_get_rtscts, _set_rtscts)
    """Get or set hardware flow control.

    Raises:
        SerialError: if an I/O or OS error occurs.
        TypeError: if `rtscts` type is not bool.

    :type: bool
    """

    def _get_vmin(self):
        try:
            iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        return cc[termios.VMIN]

    def _set_vmin(self, vmin):
        if not isinstance(vmin, int):
            raise TypeError("Invalid vmin type, should be integer.")
        elif not (0 <= vmin <= 255):
            raise ValueError("Invalid vmin, can be 0 to 255.")

        try:
            iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

        cc[termios.VMIN] = vmin

        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

        self._use_termios_timeout = vmin > 0

    vmin = property(_get_vmin, _set_vmin)
    """Get or set the VMIN termios setting for minimum number of bytes returned
    from a blocking read. Can be between 0 and 255.

    When configured in conjunction with VTIME, VTIME acts as an interbyte
    timeout that restarts on every byte received, and a blocking read will
    block until at least VMIN bytes are read or the VTIME timeout expires after
    the last byte read. See the `termios` man page for more information.

    Raises:
        SerialError: if an I/O or OS error occurs.
        TypeError: if `vmin` type is not int.
        ValueError: if `vmin` value is invalid.

    :type: int
    """

    def _get_vtime(self):
        try:
            iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Getting serial port attributes: " + e.strerror)

        return float(cc[termios.VTIME]) / 10.0

    def _set_vtime(self, vtime):
        if not isinstance(vtime, (float, int)):
            raise TypeError("Invalid vtime type, should be float or integer.")
        elif not (0 <= vtime <= 25.5):
            raise ValueError("Invalid vtime, can be 0 to 25.5 seconds.")

        try:
            iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(self._fd)
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

        cc[termios.VTIME] = int(float(vtime) * 10.0)

        try:
            termios.tcsetattr(self._fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        except termios.error as e:
            raise SerialError(e.errno, "Setting serial port attributes: " + e.strerror)

    vtime = property(_get_vtime, _set_vtime)
    """Get or set the VTIME termios setting for timeout in seconds of a
    blocking read. Can be between 0 to 25.5 seconds, with a resolution of 0.1
    seconds.

    When configured in conjunction with VMIN, VTIME acts as an interbyte
    timeout that restarts on every byte received, and a blocking read will
    block until at least VMIN bytes are read or the VTIME timeout expires after
    the last byte read. See the `termios` man page for more information.

    Raises:
        SerialError: if an I/O or OS error occurs.
        TypeError: if `vtime` type is not float or int.
        ValueError: if `vtime` value is invalid.

    :type: float
    """

    # String representation
    def __str__(self):
        return "Serial (device={:s}, fd={:d}, baudrate={:d}, databits={:d}, parity={:s}, stopbits={:d}, xonxoff={:s}, rtscts={:s}, vmin={:d}, vtime={:.1f})" \
            .format(self.devpath, self.fd, self.baudrate, self.databits, self.parity, self.stopbits, str(self.xonxoff), str(self.rtscts), self.vmin, self.vtime)
