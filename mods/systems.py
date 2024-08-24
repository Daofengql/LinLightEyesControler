import ctypes


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