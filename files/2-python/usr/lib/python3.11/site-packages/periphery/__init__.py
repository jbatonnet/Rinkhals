import time

__version__ = "2.4.1"
"Module version string."

version = (2, 4, 1)
"Module version tuple."


def sleep(seconds):
    """Sleep for the specified number of seconds.

    Args:
        seconds (int, long, float): duration in seconds.

    """
    time.sleep(seconds)


def sleep_ms(milliseconds):
    """Sleep for the specified number of milliseconds.

    Args:
        milliseconds (int, long, float): duration in milliseconds.

    """
    time.sleep(milliseconds / 1000.0)


def sleep_us(microseconds):
    """Sleep for the specified number of microseconds.

    Args:
        microseconds (int, long, float): duration in microseconds.

    """
    time.sleep(microseconds / 1000000.0)


from periphery.gpio import GPIO, SysfsGPIO, CdevGPIO, EdgeEvent, GPIOError
from periphery.led import LED, LEDError
from periphery.pwm import PWM, PWMError
from periphery.spi import SPI, SPIError
from periphery.i2c import I2C, I2CError
from periphery.mmio import MMIO, MMIOError
from periphery.serial import Serial, SerialError
