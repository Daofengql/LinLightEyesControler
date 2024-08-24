import time
import json
import base64
import threading
import numpy as np
from io import BytesIO
import paho.mqtt.client as mqtt
from PIL import Image, ImageSequence
from mods.config import *
from mods.systems import terminate_thread
from mods.hardware.ST7789 import convert_rgba_to_rgb565

from mods.Render import (
    IrisAndScleraRender,
    EyeLidRender,
    crop_centered_region,
    map_float_to_array,
    combine_render
)

#正式加载开始
def init():

    global LEFT_IRIS_IMG, LEFT_SCLERA_IMG, RIGHT_IRIS_IMG, RIGHT_SCLERA_IMG
    global LEFT_IRIS_AND_SCLERA_RENDER, RIGHT_IRIS_AND_SCLERA_RENDER, EYELID_RENDER
    global INIT_STATUES


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
    INIT_STATUES = True

#加载动画 搞笑的
def loadingFrame():
    gif = Image.open(LOADING_GIF)
    success = Image.open(LOADING_JOKE)
    success = np.array(success.convert('RGBA'))

    #提交搞笑到屏幕
    LEFT_SCREEN.img_show(
        convert_rgba_to_rgb565(
            success
            )
    )
    RIGHT_SCREEN.img_show(
        convert_rgba_to_rgb565(
            success
            )
    )

    time.sleep(3)
    
    # 遍历GIF的每一帧
    while True:
        for frame in ImageSequence.Iterator(gif):
            if INIT_STATUES:
                return
            # 获取当前帧的延迟时间，单位是毫秒
            delay = frame.info['duration'] / 800.0
            

            frame_np = convert_rgba_to_rgb565(
                np.array(
                    frame.convert('RGBA')
                    )
            )
            #提交到屏幕
            LEFT_SCREEN.img_show(frame_np)
            RIGHT_SCREEN.img_show(frame_np)
            
            # 等待帧延迟时间
            time.sleep(delay)


def pushImg(leftimg,rightimg):
    #体提交到队列
    LEFT_FRAME_BUFFER.append(
        convert_rgba_to_rgb565(
            leftimg
            )
    )
    RIGHT_FRAME_BUFFER.append(
        convert_rgba_to_rgb565(
            rightimg
            )
    )


def EYErend(eyelid_percentage, radius, rel_x, rel_y):

    
    #计算瞳孔偏移后的缩小大小，模拟球面的透视效果
    pupil_dy =  1 - (1 if abs(rel_x)*1.6 > 1 else abs(rel_x)*1.6)

    left_ias_img = map_float_to_array(LEFT_IRIS_AND_SCLERA_RENDER.iris_and_sclera_array_list,pupil_dy)
    right_ias_img = map_float_to_array(RIGHT_IRIS_AND_SCLERA_RENDER.iris_and_sclera_array_list,pupil_dy)


    eyelid_img = map_float_to_array(EYELID_RENDER.eyelid_list,eyelid_percentage)

    #眨眼处理
    #if radius == 0:
        #eyelid_img = map_float_to_array(EYELID_RENDER.eyelid_list,1)
    eyelid_img = map_float_to_array(EYELID_RENDER.eyelid_list,radius)

    
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
        right_ias_img, 
        int(rel_x*100), 
        int(rel_y*100)
    )

    #合并最终图像
    left_eye = combine_render(left_eyelid_surface,left_ias_surface)
    right_eye = combine_render(right_eyelid_surface,right_ias_surface)

    pushImg(left_eye,right_eye)



def CustomScreenRend(leftimg,rightimg,n):
    def base64_to_nparray(base64_string):
        # 解码Base64字符串
        img_data = base64.b64decode(base64_string)
        
        # 将二进制数据转换为字节流
        img = BytesIO(img_data)
        
        # 使用Pillow打开图片
        image = Image.open(img)
        
        # 将Pillow图片对象转换为numpy数组
        img_array = np.array(image)
        
        return img_array
    
    left = base64_to_nparray(leftimg) 
    right = base64_to_nparray(rightimg)

    for _ in range(n):
        pushImg(left,right)

def MqttRender():
    def on_connect(client, userdata, flags, rc, properties=None):
        client.subscribe("controler/eye")

    def on_message(client, userdata, msg):
        try:

            message_payload = msg.payload.decode()
            message_json = json.loads(message_payload)
            args = message_json["data"]

            if not message_json["isCustomScreen"]:
                
                EYErend(**args)
            else:
                CustomScreenRend(**args)
                
        except:
            pass

    # Create an MQTT client instance
    client = mqtt.Client(client_id="EYE_Render")
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to the MQTT broker
    client.connect(**MQTT_CONF)
    

    # Start the loop in a separate thread
    client.loop_start()
    while True:
        time.sleep(0.01)


def SPIpipe():
    iteration_count = 0
    start_time = time.time()

    while True:
        if len(LEFT_FRAME_BUFFER) == 0 or len(RIGHT_FRAME_BUFFER) == 0:
            pass
        else:
            # 提交到屏幕
            l = LEFT_FRAME_BUFFER.popleft()
            r = RIGHT_FRAME_BUFFER.popleft()
            LEFT_SCREEN.img_show(l)
            RIGHT_SCREEN.img_show(r)
            iteration_count += 1
        
        # 每秒计算并打印循环次数
        if time.time() - start_time >= 1:
            #print(iteration_count)
            
            iteration_count = 0
            start_time = time.time()


def MqttPWM():
    def on_connect(client, userdata, flags, rc, properties=None):
        client.subscribe("controler/pwm")

    def on_message(client, userdata, msg):
        try:

            message_payload = msg.payload.decode()
            message_json = json.loads(message_payload)
            if message_json["type"] == "set":
                pwmdat = message_json["data"]
                channel = int(pwmdat["channel"])
                value = int(pwmdat["value"])
                if channel <= 15:
                    PWM.set_pwm(channel, 1, value)
            elif message_json["type"] == "breath":
                pwmdat = message_json["data"]
                channel = int(pwmdat["channel"])
                step1 = int(pwmdat["step1"])
                step2 = int(pwmdat["step2"])
                PWMrange = tuple(pwmdat["range"])

                terminate_thread(threads[f"{channel}"])
                threads[f"{channel}"] = threading.Thread(target = whilePWM ,args=(channel, step1, step2, PWMrange))
                threads[f"{channel}"].start()         
            else:
                pass

                
            
        except:
            pass

        
    def whilePWM(channel:int,step1:int,step2:int,PWMrange:tuple):
        while True:
            if step1 == 0:
                time.sleep(1)
            else:
                for i in range(PWMrange[0],PWMrange[1],step1):
                    PWM.set_pwm(channel, 1, i)
                
                for i in range(PWMrange[1],PWMrange[0],-step2):
                    PWM.set_pwm(channel, 1, i)


    threads = {}
    for i in range(16):
        threads[f"{i}"] =  threading.Thread(target = whilePWM ,args=(i, 0, 0,(0,0)))
        threads[f"{i}"].start()

    # Create an MQTT client instance
    client = mqtt.Client(client_id="PWM_Controler")
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to the MQTT broker
    client.connect(**MQTT_CONF)
    

    # Start the loop in a separate thread
    client.loop_start()
    while True:
        time.sleep(0.01)

if __name__ == "__main__":

    loadingThread = threading.Thread(target = loadingFrame)
    loadingThread.start()

    #初始化开始
    init()

    pipeThread = threading.Thread(target = SPIpipe)
    pipeThread.start()

    RenderThread = threading.Thread(target = MqttRender)
    RenderThread.start()

    PwmThread = threading.Thread(target = MqttPWM)
    PwmThread.start()


    while True:
        time.sleep(0.1)
    

    




        
