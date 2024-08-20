import numpy as np
from PIL import Image
import cv2
import math

def calculate_distance(point1, point2):
    """
    计算两个点之间的欧几里得距离，并返回整数结果。

    参数：
    point1, point2: 表示点的元组，格式为 (x, y)

    返回：
    两个点之间的距离（整数）
    """
    x1, y1 = point1
    x2, y2 = point2
    distance = math.sqrt((x2 - x1) ** 2 + (y1 - y2) ** 2)
    return int(distance)

def generate_tuples(tuple1, tuple2, n):
    """
    根据给定的两个元组和中间点的数量，生成一系列插值元组。

    参数：
    tuple1, tuple2: 作为插值起始和结束的元组
    n: 插值元组的数量

    返回：
    插值元组的列表
    """
    if n < 2:
        raise ValueError("n must be at least 2 to generate intermediate tuples.")
    
    x1, y1 = tuple1
    x2, y2 = tuple2
    result = []

    for i in range(n):
        x = round(x1 + (x2 - x1) * i / (n - 1))
        y = round(y1 + (y2 - y1) * i / (n - 1))
        result.append((x, y))
    
    return result

def crop_centered_region(image, center_x, center_y):
    """
    从图像中以指定点为中心裁剪一个区域。裁剪区域的大小为图像宽高的一半。

    参数：
    image: 输入的图像（numpy数组，RGBA格式）
    center_x, center_y: 裁剪区域的中心点位置

    返回：
    裁剪后的图像（numpy数组，RGBA格式）
    """
    height, width, _ = image.shape
    crop_width, crop_height = width // 2, height // 2

    actual_center_x = width // 2 + center_x
    actual_center_y = height // 2 + center_y

    start_x = actual_center_x - crop_width // 2
    start_y = actual_center_y - crop_height // 2
    end_x = start_x + crop_width
    end_y = start_y + crop_height

    if start_x < 0:
        start_x = 0
        end_x = crop_width
    if start_y < 0:
        start_y = 0
        end_y = crop_height
    if end_x > width:
        end_x = width
        start_x = end_x - crop_width
    if end_y > height:
        end_y = height
        start_y = end_y - crop_height

    cropped_image = image[start_y:end_y, start_x:end_x]
    return cropped_image

def map_float_to_array(arr, float_num):
    """
    将浮点数映射到数组中的元素。

    参数：
    arr: 输入的数组
    float_num: 0到1之间的浮点数

    返回：
    数组中的元素
    """
    if not (0 <= float_num <= 1):
        raise ValueError("The floating point number must be between 0 and 1")
    
    index = int(float_num * len(arr))
    
    if index == len(arr):
        index -= 1
    
    return arr[index]

def combine_render(frame1, frame2):
    """
    叠加两个图像帧并返回合成结果。

    参数：
    frame1, frame2: 输入的图像帧（numpy数组，RGBA格式）

    返回：
    合成后的图像帧（numpy数组，RGBA格式）
    """
    rgb1 = frame1[:, :, :3]
    alpha1 = frame1[:, :, 3] / 255.0
    rgb2 = frame2[:, :, :3]
    alpha2 = frame2[:, :, 3] / 255.0

    alpha_combined = alpha1 + alpha2 * (1 - alpha1)
    rgb_combined = (rgb1 * alpha1[..., None] + rgb2 * alpha2[..., None] * (1 - alpha1[..., None])) / alpha_combined[..., None]

    combined_image = np.dstack((rgb_combined, alpha_combined * 255)).astype(np.uint8)
    return combined_image

class IrisAndScleraRender:
    def __init__(self, sclera, iris, frame_size=480, sclera_inner=(82, 86), sclera_outer=(240, 240),
                 iris_inner_normal=(10, 69), iris_inner_crazy_max=(18, 71), iris_smooth_n=15, iris_outer=(89, 90)):
        """
        眼部渲染器，通过简单纹理创造复杂的眼睛画面。

        参数：
        sclera: PIL.Image对象，巩膜的纹理
        iris: PIL.Image对象，虹膜的纹理
        frame_size: 整数，正方形渲染区的边长
        sclera_inner: 元组，巩膜内圈长轴和短轴
        sclera_outer: 元组，巩膜外圈长轴和短轴
        iris_inner_normal: 元组，虹膜正常内圈长轴和短轴
        iris_inner_crazy_max: 元组，虹膜最大内圈长轴和短轴
        iris_smooth_n: 整数，瞳孔缩放动画的平滑度
        iris_outer: 元组，虹膜外圈长轴和短轴
        """
        self._sclera_array = np.array(sclera)
        self._iris_array = np.array(iris)

        self.sclera_img = self._iris_and_sclera_render(self._sclera_array, sclera.size, frame_size, sclera_inner, sclera_outer)
        self.pupil_array = self._pupil_render(frame_size, iris_inner_crazy_max[1] + 2)

        iris_tuple_list = generate_tuples(iris_inner_normal, iris_inner_crazy_max, iris_smooth_n)
        self.iris_array_list = []
        self.iris_and_sclera_array_list = []

        for iris_tuple in iris_tuple_list:
            _tmp = self._iris_and_sclera_render(self._iris_array, iris.size, frame_size, iris_tuple, iris_outer)
            _combine_iris = combine_render(_tmp, self.pupil_array)
            self.iris_array_list.append(_combine_iris)
            _combine = combine_render(self.sclera_img, _combine_iris)
            self.iris_and_sclera_array_list.append(_combine)

    def _iris_and_sclera_render(self, frame_array, frame_size, size, inner, outer):
        """
        全局通用渲染器，用于渲染瞳孔、虹膜和巩膜。

        参数：
        frame_array: numpy数组，输入图像数据
        frame_size: 元组，帧的尺寸
        size: 整数，渲染尺寸
        inner: 元组，内圈尺寸
        outer: 元组，外圈尺寸

        返回：
        渲染后的图像（numpy数组，RGBA格式）
        """
        new_img = np.zeros((size, size, 4), dtype=np.uint8)
        center = size // 2

        t = np.linspace(0, 1, frame_size[1])[:, np.newaxis]
        a = inner[0] + t * (outer[0] - inner[0])
        b = inner[1] + t * (outer[1] - inner[1])
        theta = np.linspace(0, 2 * np.pi, frame_size[0])
        x = center + a * np.cos(theta)
        y = center + b * np.sin(theta)

        x = np.clip(x, 0, size - 1).astype(int)
        y = np.clip(y, 0, size - 1).astype(int)
        idx = np.arange(frame_size[0])

        new_img[y, x] = frame_array[np.arange(frame_size[1])[:, np.newaxis], idx]
        mask = new_img[:, :, 3] == 0
        new_img[mask] = [0, 0, 0, 0]

        return new_img

    def _pupil_render(self, size, radius):
        """
        瞳孔生成器。

        参数：
        size: 整数，画布大小
        radius: 整数，瞳孔半径

        返回：
        生成的瞳孔图像（numpy数组，RGBA格式）
        """
        canvas = np.zeros((size, size, 4), dtype=np.uint8)
        center = size // 2

        Y, X = np.ogrid[:size, :size]
        dist_from_center = np.sqrt((X - center) ** 2 + (Y - center) ** 2)
        mask = dist_from_center <= radius
        canvas[mask] = [0, 0, 0, 255]

        return canvas

    def apply_convex_lens_effect(self, img_array, lens_radius):
        """
        应用凸透镜效果。

        参数：
        img_array: numpy数组，输入图像
        lens_radius: 整数，透镜半径

        返回：
        应用透镜效果后的图像（numpy数组，RGBA格式）
        """
        height, width, channels = img_array.shape
        center_x, center_y = width // 2, height // 2

        y, x = np.indices((height, width))
        x = x - center_x
        y = y - center_y
        distance = np.sqrt(x ** 2 + y ** 2)

        lens_effect = distance < lens_radius
        factor = np.ones_like(distance)
        factor[lens_effect] = 1 - (distance[lens_effect] / lens_radius) ** 2

        x_new = center_x + x * factor
        y_new = center_y + y * factor

        x_new = np.clip(x_new, 0, width - 1).astype(np.float32)
        y_new = np.clip(y_new, 0, height - 1).astype(np.float32)

        lens_effect_img = cv2.remap(img_array, x_new, y_new, interpolation=cv2.INTER_LINEAR)
        return lens_effect_img

class EyeLidRender:
    def __init__(self, eyelid_color, Rsize=480, flash_n=10, axes_upper=(110, 60), axes_lower=(110, 1),
                 angle=10, sharpness=6):
        """
        眼睑渲染器，用于生成眨眼动画。

        参数：
        eyelid_color: 十六进制颜色字符串，眼睑的颜色
        Rsize: 整数，画布大小
        flash_n: 整数，眨眼动画的过渡帧数
        axes_upper: 元组，正常状态的眼睑
        axes_lower: 元组，闭眼状态的眼睑
        angle: 整数，眼睑的旋转角度
        sharpness: 整数，眼睑一侧的收缩程度
        """
        self.border_color_hex = eyelid_color
        self.sharpness = sharpness
        self.angle = angle
        self.Rsize = Rsize
        eyelid_tuple_list = generate_tuples(axes_upper, axes_lower, flash_n)
        self.eyelid_list = [self.create_custom_ellipse_image(axes) for axes in eyelid_tuple_list]

    def _hex_to_rgb(self, hex_color):
        """
        将十六进制颜色字符串转换为RGB元组。

        参数：
        hex_color: 十六进制颜色字符串

        返回：
        RGB元组
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def create_custom_ellipse_image(self, axes):
        """
        创建自定义椭圆图像。

        参数：
        axes: 元组，椭圆的长轴和短轴

        返回：
        生成的椭圆图像（numpy数组，RGBA格式）
        """
        border_color = self._hex_to_rgb(self.border_color_hex)
        image = np.zeros((self.Rsize, self.Rsize, 4), dtype=np.uint8)

        y, x = np.ogrid[:self.Rsize, :self.Rsize]
        cy = (self.Rsize // 2) + (self.Rsize // 20)
        cx = (self.Rsize // 2)

        rx, ry = axes
        angle_rad = np.deg2rad(self.angle)
        cos_angle = np.cos(angle_rad)
        sin_angle = np.sin(angle_rad)

        gradient = (1 - (y - cy) / self.Rsize) ** self.sharpness
        gradient = np.clip(gradient, 0, 1)

        ellipse = (((x - cx) * cos_angle + (y - cy) * sin_angle) ** 2) / (rx ** 2) + \
                  (((x - cx) * sin_angle - (y - cy) * cos_angle) ** 2) / ((ry * gradient) ** 2)

        mask = ellipse <= 1
        image[mask] = [0, 0, 0, 0]
        image[~mask] = list(border_color) + [255]

        return image
