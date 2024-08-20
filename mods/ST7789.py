import time
import numpy as np
import digitalio
from periphery import SPI


class ST7789():
    def __init__(
            self,
            rst_pin,
            dc_pin,
            bus:SPI
            ):
        self.rst = digitalio.DigitalInOut(rst_pin)
        self.dc = digitalio.DigitalInOut(dc_pin)

        self.rst.direction = digitalio.Direction.OUTPUT
        self.dc.direction = digitalio.Direction.OUTPUT
        
        self.spi = bus
        
        # 定义LCD的宽度和高度
        self.w = 240
        self.h = 240
        
    def write_cmd(self, cmd):
        """发送命令"""
        self.dc.value = False

        self.spi.transfer([cmd])

        
    def write_data(self, value):
        """发送数据"""
        self.dc.value = True

        self.spi.transfer([value])

    def write_data_word(self, value):
        """发送双字节数据"""
        self.dc.value = True

        self.spi.transfer([value >> 8, value & 0xFF])

        
    def reset(self):
        """复位LCD"""
        self.rst.value = True
        time.sleep(0.04)
        self.rst.value = False
        time.sleep(0.04)
        self.rst.value = True
        time.sleep(0.04)
        
    def lcd_init(self):

        
        """LCD初始化"""
        self.reset()
        
        #屏幕显示方向
        self.write_cmd(0x36) 
        self.write_data(0x00) #0x00 竖屏 0xA0 向左横屏
        
        #65k 颜色 565模式
        self.write_cmd(0x3A) 
        self.write_data(0x05)

        #ST7789 Frame rate setting
        self.write_cmd(0xB2)
        self.write_data(0x05)
        self.write_data(0x05)
        self.write_data(0x00)
        self.write_data(0x30)
        self.write_data(0x30)

        self.write_cmd(0xB7) 
        self.write_data(0x35)

        #ST7789 Power setting
        self.write_cmd(0xBB)
        self.write_data(0x19)

        self.write_cmd(0xC0)
        self.write_data(0x2C)

        self.write_cmd(0xC2)
        self.write_data(0x01)

        self.write_cmd(0xC3)
        self.write_data(0x12)   

        self.write_cmd(0xC4)
        self.write_data(0x20)

        self.write_cmd(0xC6) 
        self.write_data(0x0F)    

        self.write_cmd(0xD0) 
        self.write_data(0xA4)
        self.write_data(0xA1)

        #ST7789 gamma setting
        self.write_cmd(0xE0)  # Set Gamma
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0D)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2B)
        self.write_data(0x3F)
        self.write_data(0x54)
        self.write_data(0x4C)
        self.write_data(0x18)
        self.write_data(0x0D)
        self.write_data(0x0B)
        self.write_data(0x1F)
        self.write_data(0x23)

        self.write_cmd(0xE1)  # Set Gamma
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0C)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2C)
        self.write_data(0x3F)
        self.write_data(0x44)
        self.write_data(0x51)
        self.write_data(0x2F)
        self.write_data(0x1F)
        self.write_data(0x1F)
        self.write_data(0x20)
        self.write_data(0x23)

        self.write_cmd(0x21)

        self.write_cmd(0x11) 

        self.write_cmd(0x29)
        
    def set_cursor(self, start_x, start_y, end_x, end_y):
        """设置光标位置"""
        self.write_cmd(0x2A)
        self.write_data(start_x >> 8)
        self.write_data(start_x & 0xFF)
        self.write_data(end_x >> 8)
        self.write_data(end_x & 0xFF)
        
        self.write_cmd(0x2B)
        self.write_data((start_y + 40) >> 8)
        self.write_data((start_y + 40) & 0xFF)
        self.write_data((end_y + 40) >> 8)
        self.write_data((end_y + 40) & 0xFF)
        
        self.write_cmd(0x2C)

    def clear(self, color=0xFFFF):
        """清屏"""
        self.set_cursor(0, 0, self.w - 1, self.h - 1)
        self.dc.value = True
        buf = [color >> 8, color & 0xFF] * (self.w * self.h)
        for i in range(0, len(buf), 4096):

            self.spi.transfer(buf[i:i+4096])

    def clear_window(self, start_x, start_y, end_x, end_y, color=0xFFFF):
        """清除窗口区域"""
        self.set_cursor(start_x, start_y, end_x, end_y)
        self.dc.value = True
        buf = [color >> 8, color & 0xFF] * ((end_x - start_x) * (end_y - start_y))
        for i in range(0, len(buf), 4096):

            self.spi.transfer(buf[i:i+4096])

    
    def set_pixel(self, x, y, color):
        """设置像素颜色"""
        self.set_cursor(x, y, x, y)
        self.write_data_word(color)

    def img_show(self, pixel):
        """显示图像"""
        self.set_cursor(0, 0, self.w, self.h)
        self.dc.value = True
        for i in range(0, len(pixel), 4096):
            self.spi.transfer(pixel[i:i+4096])


def convert_rgba_to_rgb565(image):
    """将RGBA图像转换为RGB565格式"""
    r = image[..., 0] & 0xF8
    g = image[..., 1]
    b = image[..., 2] & 0xFC

    pixel_high = r | (g >> 5)
    pixel_low = ((g << 3) & 0xE0) | (b >> 3)

    # 将高低字节交错合并并展平为一维数组
    pixel = np.dstack((pixel_high, pixel_low)).flatten().tolist()
    return pixel
