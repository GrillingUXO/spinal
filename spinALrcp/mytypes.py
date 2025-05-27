from enum import IntEnum
from dataclasses import dataclass, field
from typing import Optional





@dataclass
class SpineRenderSettings:

    use_premultiplied_alpha: bool = True  # 是否使用预乘Alpha
    scale: float = 1.0                    # 渲染缩放
    position_x: float = 0.0               # X位置偏移
    position_y: float = 0.0               # Y位置偏移
    flip_x: bool = False                  # X轴翻转
    flip_y: bool = False  

# 枚举定义
class BlendMode(IntEnum):
    Normal = 0 
    Additive = 1
    Multiply = 2
    Screen = 3

class AttachmentType(IntEnum):
    Region = 0
    BoundingBox = 1
    Mesh = 2
    LinkedMesh = 3
    Path = 4
    Point = 5
    Clipping = 6

class TransformMode(IntEnum): 
    Normal = 0 
    OnlyTranslation = 1
    NoRotationOrReflection = 2
    NoScale = 3
    NoScaleOrReflection = 4

@dataclass
class Color:
    """RGBA颜色"""
    r: float = 1.0
    g: float = 1.0
    b: float = 1.0
    a: float = 1.0
    
    def to_pygame_color(self):
        """转换为Pygame颜色元组"""
        return (int(self.r * 255), int(self.g * 255), 
                int(self.b * 255), int(self.a * 255))

