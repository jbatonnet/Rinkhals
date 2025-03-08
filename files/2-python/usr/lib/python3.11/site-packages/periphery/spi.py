import os
import fcntl
import array
import ctypes
import platform


try:
    KERNEL_VERSION = tuple([int(s) for s in platform.release().split(".")[:2]])
except ValueError:
    KERNEL_VERSION = (0, 0)


class SPIError(IOError):
    """Base class for SPI errors."""
    pass


class _CSpiIocTransfer(ctypes.Structure):
    _fields_ = [
        ('tx_buf', ctypes.c_ulonglong),
        ('rx_buf', ctypes.c_ulonglong),
        ('len', ctypes.c_uint),
        ('speed_hz', ctypes.c_uint),
        ('delay_usecs', ctypes.c_ushort),
        ('bits_per_word', ctypes.c_ubyte),
        ('cs_change', ctypes.c_ubyte),
        ('tx_nbits', ctypes.c_ubyte),
        ('rx_nbits', ctypes.c_ubyte),
        ('pad', ctypes.c_ushort),
    ]


class SPI(object):
    # Constants scraped from <linux/spi/spidev.h>
    _SPI_CPHA = 0x1
    _SPI_CPOL = 0x2
    _SPI_LSB_FIRST = 0x8
    _SPI_IOC_WR_MODE = 0x40016b01
    _SPI_IOC_RD_MODE = 0x80016b01
    _SPI_IOC_WR_MODE32 = 0x40046b05
    _SPI_IOC_RD_MODE32 = 0x80046b05
    _SPI_IOC_WR_MAX_SPEED_HZ = 0x40046b04
    _SPI_IOC_RD_MAX_SPEED_HZ = 0x80046b04
    _SPI_IOC_WR_BITS_PER_WORD = 0x40016b03
    _SPI_IOC_RD_BITS_PER_WORD = 0x80016b03
    _SPI_IOC_MESSAGE_1 = 0x40206b00

    _SUPPORTS_MODE32 = KERNEL_VERSION >= (3, 15)

    def __init__(self, devpath, mode, max_speed, bit_order="msb", bits_per_word=8, extra_flags=0):
        """Instantiate a SPI object and open the spidev device at the specified
        path with the specified SPI mode, max speed in hertz, and the defaults
        of "msb" bit order and 8 bits per word.

        Args:
            devpath (str): spidev device path.
            mode (int): SPI mode, can be 0, 1, 2, 3.
            max_speed (int, float): maximum speed in Hertz.
            bit_order (str): bit order, can be "msb" or "lsb".
            bits_per_word (int): bits per word.
            extra_flags (int): extra spidev flags to be bitwise-ORed with the SPI mode.

        Returns:
            SPI: SPI object.

        Raises:
            SPIError: if an I/O or OS error occurs.
            TypeError: if `devpath`, `mode`, `max_speed`, `bit_order`, `bits_per_word`, or `extra_flags` types are invalid.
            ValueError: if `mode`, `bit_order`, `bits_per_word`, or `extra_flags` values are invalid.

        """
        self._fd = None
        self._devpath = None
        self._open(devpath, mode, max_speed, bit_order, bits_per_word, extra_flags)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, t, value, traceback):
        self.close()

    def _open(self, devpath, mode, max_speed, bit_order, bits_per_word, extra_flags):
        if not isinstance(devpath, str):
            raise TypeError("Invalid devpath type, should be string.")
        elif not isinstance(mode, int):
            raise TypeError("Invalid mode type, should be integer.")
        elif not isinstance(max_speed, (int, float)):
            raise TypeError("Invalid max_speed type, should be integer or float.")
        elif not isinstance(bit_order, str):
            raise TypeError("Invalid bit_order type, should be string.")
        elif not isinstance(bits_per_word, int):
            raise TypeError("Invalid bits_per_word type, should be integer.")
        elif not isinstance(extra_flags, int):
            raise TypeError("Invalid extra_flags type, should be integer.")

        if mode not in [0, 1, 2, 3]:
            raise ValueError("Invalid mode, can be 0, 1, 2, 3.")
        elif bit_order.lower() not in ["msb", "lsb"]:
            raise ValueError("Invalid bit_order, can be \"msb\" or \"lsb\".")
        elif bits_per_word < 0 or bits_per_word > 255:
            raise ValueError("Invalid bits_per_word, must be 0-255.")

        # Open spidev
        try:
            self._fd = os.open(devpath, os.O_RDWR)
        except OSError as e:
            raise SPIError(e.errno, "Opening SPI device: " + e.strerror)

        self._devpath = devpath

        bit_order = bit_order.lower()

        # Set mode, bit order, extra flags
        if extra_flags > 0xff:
            if not SPI._SUPPORTS_MODE32:
                raise SPIError(None, "32-bit mode configuration not supported by kernel version {}.{}.".format(*KERNEL_VERSION))

            # Use 32-bit mode if extra flags is wider than 8-bits
            buf = array.array("I", [mode | (SPI._SPI_LSB_FIRST if bit_order == "lsb" else 0) | extra_flags])
            try:
                fcntl.ioctl(self._fd, SPI._SPI_IOC_WR_MODE32, buf, False)
            except (OSError, IOError) as e:
                raise SPIError(e.errno, "Setting SPI mode: " + e.strerror)
        else:
            # Prefer 8-bit mode for compatibility with older kernels
            buf = array.array("B", [mode | (SPI._SPI_LSB_FIRST if bit_order == "lsb" else 0) | extra_flags])
            try:
                fcntl.ioctl(self._fd, SPI._SPI_IOC_WR_MODE, buf, False)
            except (OSError, IOError) as e:
                raise SPIError(e.errno, "Setting SPI mode: " + e.strerror)

        # Set max speed
        buf = array.array("I", [int(max_speed)])
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_WR_MAX_SPEED_HZ, buf, False)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Setting SPI max speed: " + e.strerror)

        # Set bits per word
        buf = array.array("B", [bits_per_word])
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_WR_BITS_PER_WORD, buf, False)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Setting SPI bits per word: " + e.strerror)

    # Methods

    def transfer(self, data):
        """Shift out `data` and return shifted in data.

        Args:
            data (bytes, bytearray, list): a byte array or list of 8-bit integers to shift out.

        Returns:
            bytes, bytearray, list: data shifted in.

        Raises:
            SPIError: if an I/O or OS error occurs.
            TypeError: if `data` type is invalid.
            ValueError: if data is not valid bytes.

        """
        if not isinstance(data, (bytes, bytearray, list)):
            raise TypeError("Invalid data type, should be bytes, bytearray, or list.")

        # Create mutable array
        try:
            buf = array.array('B', data)
        except OverflowError:
            raise ValueError("Invalid data bytes.")

        buf_addr, buf_len = buf.buffer_info()

        # Prepare transfer structure
        spi_xfer = _CSpiIocTransfer()
        spi_xfer.tx_buf = buf_addr
        spi_xfer.rx_buf = buf_addr
        spi_xfer.len = buf_len

        # Transfer
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_MESSAGE_1, spi_xfer)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "SPI transfer: " + e.strerror)

        # Return shifted out data with the same type as shifted in data
        if isinstance(data, bytes):
            return bytes(bytearray(buf))
        elif isinstance(data, bytearray):
            return bytearray(buf)
        elif isinstance(data, list):
            return buf.tolist()

    def close(self):
        """Close the spidev SPI device.

        Raises:
            SPIError: if an I/O or OS error occurs.

        """
        if self._fd is None:
            return

        try:
            os.close(self._fd)
        except OSError as e:
            raise SPIError(e.errno, "Closing SPI device: " + e.strerror)

        self._fd = None

    # Immutable properties

    @property
    def fd(self):
        """Get the file descriptor of the underlying spidev device.

        :type: int
        """
        return self._fd

    @property
    def devpath(self):
        """Get the device path of the underlying spidev device.

        :type: str
        """
        return self._devpath

    # Mutable properties

    def _get_mode(self):
        buf = array.array('B', [0])

        # Get mode
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_RD_MODE, buf, True)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Getting SPI mode: " + e.strerror)

        return buf[0] & 0x3

    def _set_mode(self, mode):
        if not isinstance(mode, int):
            raise TypeError("Invalid mode type, should be integer.")
        if mode not in [0, 1, 2, 3]:
            raise ValueError("Invalid mode, can be 0, 1, 2, 3.")

        # Read-modify-write mode, because the mode contains bits for other settings

        # Get mode
        buf = array.array('B', [0])
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_RD_MODE, buf, True)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Getting SPI mode: " + e.strerror)

        buf[0] = (buf[0] & ~(SPI._SPI_CPOL | SPI._SPI_CPHA)) | mode

        # Set mode
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_WR_MODE, buf, False)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Setting SPI mode: " + e.strerror)

    mode = property(_get_mode, _set_mode)
    """Get or set the SPI mode. Can be 0, 1, 2, 3.

    Raises:
        SPIError: if an I/O or OS error occurs.
        TypeError: if `mode` type is not int.
        ValueError: if `mode` value is invalid.

    :type: int
    """

    def _get_max_speed(self):
        # Get max speed
        buf = array.array('I', [0])
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_RD_MAX_SPEED_HZ, buf, True)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Getting SPI max speed: " + e.strerror)

        return buf[0]

    def _set_max_speed(self, max_speed):
        if not isinstance(max_speed, (int, float)):
            raise TypeError("Invalid max_speed type, should be integer or float.")

        # Set max speed
        buf = array.array('I', [int(max_speed)])
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_WR_MAX_SPEED_HZ, buf, False)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Setting SPI max speed: " + e.strerror)

    max_speed = property(_get_max_speed, _set_max_speed)
    """Get or set the maximum speed in Hertz.

    Raises:
        SPIError: if an I/O or OS error occurs.
        TypeError: if `max_speed` type is not int or float.

    :type: int, float
    """

    def _get_bit_order(self):
        # Get mode
        buf = array.array('B', [0])
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_RD_MODE, buf, True)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Getting SPI mode: " + e.strerror)

        if (buf[0] & SPI._SPI_LSB_FIRST) > 0:
            return "lsb"

        return "msb"

    def _set_bit_order(self, bit_order):
        if not isinstance(bit_order, str):
            raise TypeError("Invalid bit_order type, should be string.")
        elif bit_order.lower() not in ["msb", "lsb"]:
            raise ValueError("Invalid bit_order, can be \"msb\" or \"lsb\".")

        # Read-modify-write mode, because the mode contains bits for other settings

        # Get mode
        buf = array.array('B', [0])
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_RD_MODE, buf, True)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Getting SPI mode: " + e.strerror)

        bit_order = bit_order.lower()
        buf[0] = (buf[0] & ~SPI._SPI_LSB_FIRST) | (SPI._SPI_LSB_FIRST if bit_order == "lsb" else 0)

        # Set mode
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_WR_MODE, buf, False)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Setting SPI mode: " + e.strerror)

    bit_order = property(_get_bit_order, _set_bit_order)
    """Get or set the SPI bit order. Can be "msb" or "lsb".

    Raises:
        SPIError: if an I/O or OS error occurs.
        TypeError: if `bit_order` type is not str.
        ValueError: if `bit_order` value is invalid.

    :type: str
    """

    def _get_bits_per_word(self):
        # Get bits per word
        buf = array.array('B', [0])
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_RD_BITS_PER_WORD, buf, True)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Getting SPI bits per word: " + e.strerror)

        return buf[0]

    def _set_bits_per_word(self, bits_per_word):
        if not isinstance(bits_per_word, int):
            raise TypeError("Invalid bits_per_word type, should be integer.")
        if bits_per_word < 0 or bits_per_word > 255:
            raise ValueError("Invalid bits_per_word, must be 0-255.")

        # Set bits per word
        buf = array.array('B', [bits_per_word])
        try:
            fcntl.ioctl(self._fd, SPI._SPI_IOC_WR_BITS_PER_WORD, buf, False)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Setting SPI bits per word: " + e.strerror)

    bits_per_word = property(_get_bits_per_word, _set_bits_per_word)
    """Get or set the SPI bits per word.

    Raises:
        SPIError: if an I/O or OS error occurs.
        TypeError: if `bits_per_word` type is not int.
        ValueError: if `bits_per_word` value is invalid.

    :type: int
    """

    def _get_extra_flags(self):
        if SPI._SUPPORTS_MODE32:
            buf = array.array('I', [0])
            rd_cmd = SPI._SPI_IOC_RD_MODE32
        else:
            buf = array.array('B', [0])
            rd_cmd = SPI._SPI_IOC_RD_MODE

        try:
            fcntl.ioctl(self._fd, rd_cmd, buf, True)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Getting SPI mode: " + e.strerror)

        return buf[0] & ~(SPI._SPI_LSB_FIRST | SPI._SPI_CPHA | SPI._SPI_CPOL)

    def _set_extra_flags(self, extra_flags):
        if not isinstance(extra_flags, int):
            raise TypeError("Invalid extra_flags type, should be integer.")

        # Read-modify-write mode, because the mode contains bits for other settings

        if extra_flags > 0xff:
            if not SPI._SUPPORTS_MODE32:
                raise SPIError(None, "32-bit mode configuration not supported by kernel version {}.{}.".format(*KERNEL_VERSION))

            buf = array.array('I', [0])
            rd_cmd = SPI._SPI_IOC_RD_MODE32
            wr_cmd = SPI._SPI_IOC_WR_MODE32
        else:
            buf = array.array('B', [0])
            rd_cmd = SPI._SPI_IOC_RD_MODE
            wr_cmd = SPI._SPI_IOC_WR_MODE

        # Get mode
        try:
            fcntl.ioctl(self._fd, rd_cmd, buf, True)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Getting SPI mode: " + e.strerror)

        buf[0] = (buf[0] & (SPI._SPI_LSB_FIRST | SPI._SPI_CPHA | SPI._SPI_CPOL)) | extra_flags

        # Set mode
        try:
            fcntl.ioctl(self._fd, wr_cmd, buf, False)
        except (OSError, IOError) as e:
            raise SPIError(e.errno, "Setting SPI mode: " + e.strerror)

    extra_flags = property(_get_extra_flags, _set_extra_flags)
    """Get or set the spidev extra flags. Extra flags are bitwise-ORed with the SPI mode.

    Raises:
        SPIError: if an I/O or OS error occurs.
        TypeError: if `extra_flags` type is not int.
        ValueError: if `extra_flags` value is invalid.

    :type: int
    """

    # String representation

    def __str__(self):
        return "SPI (device={:s}, fd={:d}, mode={:d}, max_speed={:d}, bit_order={:s}, bits_per_word={:d}, extra_flags=0x{:08x})" \
            .format(self.devpath, self.fd, self.mode, self.max_speed, self.bit_order, self.bits_per_word, self.extra_flags)
