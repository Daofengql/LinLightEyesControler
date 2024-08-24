from periphery import I2C
import time
import math
import logging

# Registers/etc:
PCA9685_ADDRESS    = 0x40
MODE1              = 0x00
MODE2              = 0x01
PRESCALE           = 0xFE
LED0_ON_L          = 0x06
LED0_ON_H          = 0x07
LED0_OFF_L         = 0x08
LED0_OFF_H         = 0x09
ALL_LED_ON_L       = 0xFA
ALL_LED_ON_H       = 0xFB
ALL_LED_OFF_L      = 0xFC
ALL_LED_OFF_H      = 0xFD

# Bits:
RESTART            = 0x80
SLEEP              = 0x10
ALLCALL            = 0x01
INVRT              = 0x10
OUTDRV             = 0x04

logger = logging.getLogger(__name__)

class PCA9685:
    """PCA9685 PWM LED/servo controller using periphery."""

    def __init__(self, address=PCA9685_ADDRESS, i2c_dev="/dev/i2c-1"):
        """Initialize the PCA9685."""
        self.i2c = I2C(i2c_dev)
        self.address = address
        self.set_all_pwm(0, 0)
        self.write_byte(MODE2, OUTDRV)
        self.write_byte(MODE1, ALLCALL)
        time.sleep(0.005)  # wait for oscillator
        mode1 = self.read_byte(MODE1)
        mode1 = mode1 & ~SLEEP  # wake up (reset sleep)
        self.write_byte(MODE1, mode1)
        time.sleep(0.005)  # wait for oscillator

    def write_byte(self, reg, value):
        self.i2c.transfer(self.address, [I2C.Message([reg, value])])

    def read_byte(self, reg):
        read = I2C.Message([0], read=True)
        self.i2c.transfer(self.address, [I2C.Message([reg]), read])
        return read.data[0]

    def set_pwm_freq(self, freq_hz):
        """Set the PWM frequency to the provided value in hertz."""
        prescaleval = 25000000.0    # 25MHz
        prescaleval /= 4096.0       # 12-bit
        prescaleval /= float(freq_hz)
        prescaleval -= 1.0
        logger.debug('Setting PWM frequency to {0} Hz'.format(freq_hz))
        logger.debug('Estimated pre-scale: {0}'.format(prescaleval))
        prescale = int(math.floor(prescaleval + 0.5))
        logger.debug('Final pre-scale: {0}'.format(prescale))
        oldmode = self.read_byte(MODE1)
        newmode = (oldmode & 0x7F) | 0x10    # sleep
        self.write_byte(MODE1, newmode)  # go to sleep
        self.write_byte(PRESCALE, prescale)
        self.write_byte(MODE1, oldmode)
        time.sleep(0.005)
        self.write_byte(MODE1, oldmode | 0x80)

    def set_pwm(self, channel, on, off):
        """Sets a single PWM channel."""
        self.write_byte(LED0_ON_L+4*channel, on & 0xFF)
        self.write_byte(LED0_ON_H+4*channel, on >> 8)
        self.write_byte(LED0_OFF_L+4*channel, off & 0xFF)
        self.write_byte(LED0_OFF_H+4*channel, off >> 8)

    def set_all_pwm(self, on, off):
        """Sets all PWM channels."""
        self.write_byte(ALL_LED_ON_L, on & 0xFF)
        self.write_byte(ALL_LED_ON_H, on >> 8)
        self.write_byte(ALL_LED_OFF_L, off & 0xFF)
        self.write_byte(ALL_LED_OFF_H, off >> 8)
