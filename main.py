from PIL import Image
import numpy as np
import cv2
import board
import digitalio
from periphery import SPI

from lib.Render import (
    IrisAndScleraRender,
    EyeLidRender,
    crop_centered_region,
    map_float_to_array,
    combine_render
)
from lib.EyesControler import detect_pupil
from lib.ST7789 import ST7789



#配置部分，定义各种硬件接口和资源文件
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
RIGHT_EYE_RES_PIN = board.GPIO18             #RES/RST数据位
RIGHT_EYE_DC_PIN = board.GPIO16              #DC控制引脚
RIGHT_EYE_EXCURISON = (5,5)                  #玻璃透镜贴的歪的程度，一个偏移矫正量

#初始化各个眼睛的spi总线（一个总线，两个片选设备)
SPI_LEFT = SPI(LEFT_EYE_TREE, 2, SPI_SPEED)
SPI_RIGHT = SPI(RIGHT_EYE_TREE, 2, SPI_SPEED)

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

#背光控制
EYE_BL = digitalio.DigitalInOut(EYE_BL)
EYE_BL.direction = digitalio.Direction.OUTPUT
EYE_BL.value = True                           #打开背光

#资源和渲染器
#定义个个纹理数据的路径
LEFT_IRIS_IMG = "assest/eyes/iris.png"        #左眼虹膜纹理
LEFT_SCLERA_IMG = "assest/eyes/sclera.png"    #左眼巩膜纹理
RIGHT_IRIS_IMG = "assest/eyes/iris.png"       #右眼虹膜纹理
RIGHT_SCLERA_IMG = "assest/eyes/sclera.png"   #右眼巩膜纹理

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

#识别器参数
DETECT_PUPIL_CONF = {
    "roi_percentage": 0.8,
    "min_pupil_diameter_percentage": 0.1,
    "eyelid_height_percentage": 0.2
}


#正式加载开始
def init():

    global LEFT_IRIS_IMG, LEFT_SCLERA_IMG, RIGHT_IRIS_IMG, RIGHT_SCLERA_IMG
    global LEFT_IRIS_AND_SCLERA_RENDER, RIGHT_IRIS_AND_SCLERA_RENDER, EYELID_RENDER


    #渲染器开始预渲染加载(高耗时步骤)
    #资源文件的加载，左右眼可独立设置对应的资源文件
    LEFT_IRIS_IMG = Image.open(LEFT_IRIS_IMG).resize((1024,80)).convert("RGBA")
    LEFT_SCLERA_IMG = Image.open(LEFT_SCLERA_IMG).resize((24000,512)).convert("RGBA")
    RIGHT_IRIS_IMG = Image.open(RIGHT_IRIS_IMG).resize((1024,80)).convert("RGBA")
    RIGHT_SCLERA_IMG = Image.open(RIGHT_SCLERA_IMG).resize((24000,512)).convert("RGBA")


    #渲染器开始预渲染纹理，将纹理载入内存
    LEFT_IRIS_AND_SCLERA_RENDER = IrisAndScleraRender(
        sclera=LEFT_SCLERA_IMG,
        iris=LEFT_IRIS_IMG,
        frame_size=IAS_FRAME_SIZE,
        **LEFT_IASR_CONF
    )
    RIGHT_IRIS_AND_SCLERA_RENDER = IrisAndScleraRender(
        sclera=RIGHT_SCLERA_IMG,
        iris=RIGHT_IRIS_IMG,
        frame_size=IAS_FRAME_SIZE,
        **RIGHT_IASR_CONF
    )
    EYELID_RENDER = EyeLidRender(
        **EYELID_RENDER_CONF
    )



if __name__ == "__main__":

    #初始化开始
    init()

    max_eyelid_height = 1

    #打开视频设备
    cap = cv2.VideoCapture("eye.mp4")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            # 如果视频结束，则重新开始
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        
        # 获取图像的尺寸
        rows, _, _ = frame.shape
        #获取追踪数据
        eyelid_height, radius, (rel_x, rel_y) = detect_pupil(frame, **DETECT_PUPIL_CONF)
        
        #判断眼睑高度是否大于已知最大高度，是否小于识别区高度，更新最大眼睑
        if eyelid_height > max_eyelid_height and eyelid_height < DETECT_PUPIL_CONF["roi_percentage"] * rows:
            max_eyelid_height = eyelid_height

        #计算眼睑打开的比例
        eyelid_percentage = 1 - eyelid_height / max_eyelid_height

        #计算瞳孔偏移后的缩小大小，模拟球面的透视效果
        pupil_dy =  1 - (1 if abs(rel_x)*1.5 > 1 else abs(rel_x)*1.5)


        left_ias_img = map_float_to_array(LEFT_IRIS_AND_SCLERA_RENDER.iris_and_sclera_array_list,pupil_dy)
        right_ias_img = map_float_to_array(RIGHT_IRIS_AND_SCLERA_RENDER.iris_and_sclera_array_list,pupil_dy)


        eyelid_img = map_float_to_array(EYELID_RENDER.eyelid_list,eyelid_percentage)

        #眨眼处理
        if radius == 0:
            eyelid_img = map_float_to_array(EYELID_RENDER.eyelid_list,1)

        
        #渲染最终图像
        left_eyelid_surface =  crop_centered_region(
            eyelid_img, 
            int(rel_x*3), 
            int(rel_y*12)
        )
        #右眼眼睑镜像
        right_eyelid_surface =  crop_centered_region(
            np.fliplr(
                eyelid_img
            ), 
            int(rel_x*3),
            int(rel_y*12)
        )


        left_ias_surface  = crop_centered_region(
            left_ias_img, 
            int(rel_x*100), 
            int(rel_y*100)
        )

        right_ias_surface  = crop_centered_region(
            left_ias_img, 
            int(rel_x*100), 
            int(rel_y*100)
        )

        #合并最终图像
        left_eye = combine_render(left_eyelid_surface,left_ias_surface)
        right_eye = combine_render(right_eyelid_surface,right_ias_surface)


        #提交到屏幕
        LEFT_SCREEN.img_show(left_eye)
        RIGHT_SCREEN.img_show(right_eye)
