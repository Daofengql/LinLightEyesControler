import board
import digitalio
from collections import deque
from periphery import SPI
from .hardware.ST7789 import ST7789
from .hardware.PCA9685 import PCA9685

#配置部分，定义各种硬件接口和资源文件
#I2C总线定义
I2C_BUS = "/dev/i2c-5"
#SPI总线定义
SPI_SPEED = 80000000                         #使用60MHZ的通信速率，实测比较稳定的最大速度
EYE_BL = board.GPIO11                        #两个眼睛共用同一个背光控制接口，可用pwm控制亮度，默认由屏幕控制器加载为最大亮度

#左眼接口定义
LEFT_EYE_TREE = "/dev/spidev3.0"             #系统spi设备树
LEFT_EYE_RES_PIN = board.GPIO13              #RES/RST数据位
LEFT_EYE_DC_PIN = board.GPIO15               #DC控制引脚
LEFT_EYE_EXCURISON = (5,5)                   #玻璃透镜贴的歪的程度，一个偏移矫正量

#右眼接口定义
RIGHT_EYE_TREE = "/dev/spidev3.1"            #系统spi设备数
RIGHT_EYE_RES_PIN = board.GPIO16             #RES/RST数据位
RIGHT_EYE_DC_PIN = board.GPIO18              #DC控制引脚
RIGHT_EYE_EXCURISON = (5,5)                  #玻璃透镜贴的歪的程度，一个偏移矫正量

#初始化各个眼睛的spi总线（一个总线，两个片选设备)
SPI_LEFT = SPI(LEFT_EYE_TREE, 0, SPI_SPEED)
SPI_RIGHT = SPI(RIGHT_EYE_TREE, 0, SPI_SPEED)

#各个眼睛控制器开始实例化
LEFT_SCREEN = ST7789(
                rst_pin=LEFT_EYE_RES_PIN,
                dc_pin=LEFT_EYE_DC_PIN,
                bus=SPI_LEFT
            )
RIGHT_SCREEN = ST7789(
                rst_pin=RIGHT_EYE_RES_PIN,
                dc_pin=RIGHT_EYE_DC_PIN,
                bus=SPI_RIGHT
            )
LEFT_SCREEN.lcd_init()                        #初始化LCD
LEFT_SCREEN.clear()
RIGHT_SCREEN.lcd_init()                       #初始化LCD
RIGHT_SCREEN.clear()

PWM = PCA9685(i2c_dev=I2C_BUS)
PWM.set_pwm_freq(1000)  # 通常舵机使用50-60Hz的PWM信号

#背光控制
EYE_BL = digitalio.DigitalInOut(EYE_BL)
EYE_BL.direction = digitalio.Direction.OUTPUT
EYE_BL.value = True                           #打开背光

#资源和渲染器
#定义个个纹理数据的路径
LEFT_IRIS_IMG = "assest/eyes/iris-L.png"        #左眼虹膜纹理
LEFT_SCLERA_IMG = "assest/eyes/sclera.png"    #左眼巩膜纹理
RIGHT_IRIS_IMG = "assest/eyes/iris-R.png"       #右眼虹膜纹理
RIGHT_SCLERA_IMG = "assest/eyes/sclera.png"   #右眼巩膜纹理
LOADING_GIF = "assest/loading_Render.gif"
LOADING_JOKE = "assest/loading_Render_joke.png"
PRELOADING_JOKE = "assest/preloading_Render_success.png"
#渲染器
LEFT_IRIS_AND_SCLERA_RENDER = None            #左眼主渲染器
RIGHT_IRIS_AND_SCLERA_RENDER = None           #右眼主渲染器
EYELID_RENDER = None
#渲染器参数
IAS_FRAME_SIZE = 480                          #眼部画布大小，一般为方/圆屏幕边分辨率的两倍
#渲染器具体参数，具体参数功能见IrisAndScleraRender和EyeLidRender的说明
LEFT_IASR_CONF = {
    "sclera_inner": (70,72),
    "sclera_outer": (120,120),
    "iris_inner_normal": (10,69),
    "iris_inner_crazy_max": (18,71),
    "iris_smooth_n":10,
    "iris_outer": (70,72)
}
RIGHT_IASR_CONF = {
    "sclera_inner": (70,72),
    "sclera_outer": (120,120),
    "iris_inner_normal": (10,69),
    "iris_inner_crazy_max": (18,71),
    "iris_smooth_n":10,
    "iris_outer": (70,72)
}
EYELID_RENDER_CONF = {
    "eyelid_color": "#000000",
    "Rsize": 480,
    "flash_n": 16,
    "axes_upper": (110, 80),
    "axes_lower": (110, 1),
    "angle": 15,
    "sharpness": 6
}

MQTT_CONF = {
    "host": "127.0.0.1",
    "port": 1883,
    "keepalive": 60
}
INIT_STATUES = False


LEFT_FRAME_BUFFER = deque(maxlen=10)
RIGHT_FRAME_BUFFER = deque(maxlen=10)