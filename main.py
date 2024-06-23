import threading
import asyncio
import queue
import socket
from libs.stream import streamLive

#主进程，负责启动追踪线程和图传线程


#图传线程上
s1 = streamLive(tick=60,camera=0)
s_thread = threading.Thread(target=s1.startStream)
s_thread.start()
