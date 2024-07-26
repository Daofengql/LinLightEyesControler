import cv2
import numpy as np

# 定义全局变量来存储旧数据
previous_data = (0, 0, (0.0, 0.0))

def initialize_kalman() -> cv2.KalmanFilter:
    """
    初始化卡尔曼滤波器。

    返回：
        cv2.KalmanFilter: 初始化后的卡尔曼滤波器对象。
    """
    kalman = cv2.KalmanFilter(2, 1, 0)
    # 测量矩阵：从状态转换到测量的关系
    kalman.measurementMatrix = np.array([[1, 0]], np.float32)
    # 状态转换矩阵：定义状态更新的模型
    kalman.transitionMatrix = np.array([[1, 1], [0, 1]], np.float32)
    # 过程噪声协方差矩阵：过程噪声的假设大小
    kalman.processNoiseCov = np.array([[1, 0], [0, 1]], np.float32) * 1
    # 测量噪声协方差矩阵：测量噪声的假设大小
    kalman.measurementNoiseCov = np.array([[1]], np.float32) * 1e-1
    # 后验误差协方差矩阵：状态估计的初始不确定性
    kalman.errorCovPost = np.array([[1, 0], [0, 1]], np.float32)
    # 初始状态
    kalman.statePost = np.array([[0], [0]], np.float32)
    return kalman

# 初始化多个卡尔曼滤波器实例，用于不同的测量值
kalman_radius = initialize_kalman()
kalman_x = initialize_kalman()
kalman_y = initialize_kalman()
kalman_eyelid_height = initialize_kalman()

def kalman_filter(kalman: cv2.KalmanFilter, measurement: float) -> float:
    """
    使用卡尔曼滤波器处理测量值。

    参数：
        kalman (cv2.KalmanFilter): 卡尔曼滤波器对象。
        measurement (float): 当前测量值。

    返回：
        float: 经过滤波的预测值。
    """
    # 更新卡尔曼滤波器的测量值
    kalman.correct(np.array([[np.float32(measurement)]]))
    # 获取卡尔曼滤波器的预测值
    prediction = kalman.predict()
    return prediction[0][0]

def aspect_ratio_similarity(contour: np.ndarray) -> float:
    """
    计算一个轮廓接近正方形的程度。

    参数：
        contour (numpy.ndarray): 轮廓点集。

    返回：
        float: 轮廓的宽高比与1.0的差值。
    """
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = float(w) / h if h != 0 else 0
    return abs(aspect_ratio - 1.0)

def center_crop_16_9(image):
    """
    Crop the largest possible 16:9 area from the center of the image.

    Parameters:
    image (numpy.ndarray): The input image as a numpy array of shape (height, width, channels).

    Returns:
    numpy.ndarray: The cropped image as a numpy array.
    """
    height, width, _ = image.shape

    # Calculate the new dimensions for a 16:9 aspect ratio
    if width / height > 16 / 9:
        new_width = int(height * 16 / 9)
        new_height = height
    else:
        new_height = int(width * 9 / 16)
        new_width = width

    # Calculate the cropping coordinates
    x_start = (width - new_width) // 2
    y_start = (height - new_height) // 2

    # Crop the image
    cropped_image = image[y_start:y_start + new_height, x_start:x_start + new_width]
    return cropped_image

def detect_pupil(frame: np.ndarray, roi_percentage: float, min_pupil_diameter_percentage: float, eyelid_height_percentage: float) -> tuple:
    """
    检测瞳孔。

    参数：
        frame (numpy.ndarray): 输入的图像帧。
        roi_percentage (float): 感兴趣区域（ROI）的百分比。
        min_pupil_diameter_percentage (float): 瞳孔最小直径的百分比。
        eyelid_height_percentage (float): 眼睑高度的百分比。

    返回：
        tuple: 过滤后的眼睑高度、瞳孔半径和瞳孔中心相对位置的比例。
    """
    global previous_data

    frame = center_crop_16_9(frame)
    
    # 获取图像的尺寸
    rows, cols, _ = frame.shape
    
    # 将图像转换为灰度图像
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 增加高斯模糊的强度，以去除噪声
    gray_frame = cv2.GaussianBlur(gray_frame, (25, 25), 0)
    
    # 应用二值化阈值以突出瞳孔
    _, threshold_pupil = cv2.threshold(gray_frame, 12, 255, cv2.THRESH_BINARY_INV)
    # 应用二值化阈值以突出眼睑
    _, threshold_eyelid = cv2.threshold(gray_frame, 90, 150, cv2.THRESH_BINARY_INV)
    
    # 查找瞳孔和眼睑的轮廓
    pupil_contours, _ = cv2.findContours(threshold_pupil, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    eyelid_contours, _ = cv2.findContours(threshold_eyelid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # 如果找到了轮廓
    if pupil_contours is not None and len(pupil_contours) > 0 and eyelid_contours is not None and len(eyelid_contours) > 0:
        
        # 根据轮廓面积和接近正方形的程度排序瞳孔轮廓
        pupil_contours = sorted(pupil_contours, key=lambda x: (cv2.contourArea(x), -aspect_ratio_similarity(x)), reverse=True)
        # 根据轮廓面积排序眼睑轮廓
        eyelid_contours = sorted(eyelid_contours, key=lambda x: cv2.contourArea(x), reverse=True)
        
        # 获取最大的瞳孔和眼睑轮廓
        cnt = pupil_contours[0]
        eyelidcnt = eyelid_contours[0]

        x, y, w, h = cv2.boundingRect(cnt)
        x2, y2, w2, h2 = cv2.boundingRect(eyelidcnt)
        
        # 计算瞳孔的中心位置
        center_x = x + w // 2
        center_y = y + h // 2
        
        # 定义居中区域的边界，占画面宽度和高度的百分比
        margin_x = int(cols * (1 - roi_percentage) / 2)
        margin_y = int(rows * (1 - roi_percentage) / 2)
        center_region_x1 = margin_x
        center_region_x2 = cols - margin_x
        center_region_y1 = margin_y
        center_region_y2 = rows - margin_y
        
        # 计算边界高度的最小瞳孔直径百分比
        boundary_height = center_region_y2 - center_region_y1
        min_radius = int(boundary_height * min_pupil_diameter_percentage / 2)
        min_eyelid_height = int(boundary_height * eyelid_height_percentage)
        
        # 检查眼睑高度是否满足条件
        if h2 < min_eyelid_height:
            return 0, 0, (0.0, 0.0)
        
        # 检查瞳孔位置是否在中心区域内
        if center_region_x1 <= center_x <= center_region_x2 and center_region_y1 <= center_y <= center_region_y2:
            # 计算瞳孔半径
            if h >= min_radius * 2:
                radius = h // 2
                # 计算瞳孔坐标相对于识别中心的位置比例，并反转Y轴
                center_region_center_x = (center_region_x1 + center_region_x2) // 2
                center_region_center_y = (center_region_y1 + center_region_y2) // 2
                rel_x = (center_x - center_region_center_x) / ((center_region_x2 - center_region_x1) // 2)
                rel_y = -(center_y - center_region_center_y) / ((center_region_y2 - center_region_y1) // 2)  # 反转Y轴
                
                # 确保比例在 -1 到 1 之间
                rel_x = max(min(rel_x, 1), -1)
                rel_y = max(min(rel_y, 1), -1)
                
                # 使用卡尔曼滤波器对测量值进行平滑处理
                filtered_radius = round(kalman_filter(kalman_radius, radius), 3)
                filtered_x = round(kalman_filter(kalman_x, rel_x), 3)
                filtered_y = round(kalman_filter(kalman_y, rel_y), 3)
                filtered_eyelid_height = round(kalman_filter(kalman_eyelid_height, h2), 3)
                
                # 更新全局变量previous_data
                previous_data = (filtered_eyelid_height, filtered_radius, (filtered_x, filtered_y))
                return previous_data
            else:
                return 0, 0, (0.0, 0.0)
        else:
            return previous_data
    
    return 0, 0, (0.0, 0.0)
