import ctypes
import hashlib
import os
import pickle


def check_cache(md5):
    return os.path.exists(f"./cache/{md5}.cache")


def make_cache(obj, md5):
    # 以二进制写模式打开文件
    with open(f"./cache/{md5}.cache", 'wb') as file:
        # 使用pickle将对象序列化并写入文件
        pickle.dump(obj, file)

def read_cache(md5):
    # 以二进制读模式打开文件
    with open(f"./cache/{md5}.cache", 'rb') as file:
        # 使用pickle加载并反序列化对象
        obj = pickle.load(file)
    return obj

def calculate_md5(file_path):
    # 创建一个MD5哈希对象
    md5_hash = hashlib.md5()

    # 以二进制模式读取文件
    with open(file_path, "rb") as f:
        # 分块读取文件内容，以避免内存占用过高
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)

    # 返回MD5值的16进制表示
    return md5_hash.hexdigest()


# 强制终止线程的函数
def terminate_thread(thread):
    if not thread.is_alive():
        return

    # 获取线程的ID
    thread_id = thread.ident
    # 使用ctypes发出终止请求
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(SystemExit))
    if res == 0:
        raise ValueError("Invalid thread id")
    elif res > 1:
        # 复位状态，如果出现异常
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
        raise SystemError("PyThreadState_SetAsyncExc failed")