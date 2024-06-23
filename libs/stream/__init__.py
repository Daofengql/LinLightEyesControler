import cv2
import pygame
import threading
from queue import Queue
import os

current_module_path = os.path.dirname(os.path.abspath(__file__))

class StreamLive:
    def __init__(self, camera=0, width=1920, height=1080, tick=60) -> None:
        self.frame_queue = Queue(maxsize=500)  # 创建一个队列用于存储帧
        self.camera = camera  # 摄像头设备索引
        # 设置摄像头和显示窗口的分辨率
        self.WIDTH, self.HEIGHT = width, height
        self.tick = tick  # 设置帧率

    def _capture_frames(self):
        cap = cv2.VideoCapture(self.camera)  # 打开摄像头
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.WIDTH)  # 设置摄像头捕获帧的宽度
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.HEIGHT)  # 设置摄像头捕获帧的高度
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M', 'J', 'P', 'G')) 
        cap.set(cv2.CAP_PROP_FPS, self.tick) 
        while True:
            ret, frame = cap.read()  # 读取一帧
            if not ret:
                break  # 如果没有读取到帧，跳出循环
            if not self.frame_queue.full():
                self.frame_queue.put(frame)  # 将帧放入队列
            else:
                print("Queue is full, skipping frame")  # 如果队列已满，跳过当前帧

    def _display_frames(self):
        pygame.init()  # 初始化pygame
        screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.NOFRAME)  # 创建无边框窗口
        clock = pygame.time.Clock()  # 创建时钟对象

        # 显示启动提示
        font_large = pygame.font.Font(None, int(self.HEIGHT / 10))  # 创建大字体
        text_large = font_large.render("System was Starting...", True, (255, 255, 255))  # 渲染大字体文本
        text_large_rect = text_large.get_rect(center=(self.WIDTH/2, self.HEIGHT/2))  # 获取文本矩形并居中

        font_small = pygame.font.Font(None, int(self.HEIGHT / 20))  # 创建小字体
        text_small = font_small.render("Waiting for Camera(Opencv)..", True, (255, 255, 255))  # 渲染小字体文本
        text_small_rect = text_small.get_rect(center=(self.WIDTH/2, self.HEIGHT/2 + int(self.HEIGHT / 15)))  # 获取文本矩形并居中

        screen.blit(text_large, text_large_rect)  # 在屏幕上绘制大字体文本
        screen.blit(text_small, text_small_rect)  # 在屏幕上绘制小字体文本
        pygame.display.flip()  # 更新屏幕显示

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()  # 退出pygame
                    return

            if not self.frame_queue.empty():
                frame = self.frame_queue.get()  # 从队列中获取一帧
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # 将BGR格式转换为RGB格式
                frame = pygame.surfarray.make_surface(frame.swapaxes(0, 1))  # 将numpy数组转换为pygame表面
                screen.blit(frame, (0, 0))  # 在屏幕上绘制帧
                pygame.display.flip()  # 更新屏幕显示

            clock.tick(self.tick)  # 控制帧率

    def startStream(self):
        capture_thread = threading.Thread(target=self._capture_frames)  # 创建捕获帧的线程
        display_thread = threading.Thread(target=self._display_frames)  # 创建显示帧的线程
        # 启动线程
        capture_thread.start()
        display_thread.start()