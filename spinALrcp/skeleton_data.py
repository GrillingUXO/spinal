from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import math
from enum import Enum
from mytypes import Color, AttachmentType

class TransformMode(Enum):
    Normal = 0
    OnlyTranslation = 1
    NoRotationOrReflection = 2
    NoScale = 3
    NoScaleOrReflection = 4

class MathUtils:
    """实现 Spine 的数学工具类"""
    PI = 3.1415927
    PI2 = PI * 2
    RAD_DEG = 180 / PI
    DEG_RAD = PI / 180
    
    @staticmethod
    def sin_deg(degrees):
        return math.sin(degrees * MathUtils.DEG_RAD)
    
    @staticmethod
    def cos_deg(degrees):
        return math.cos(degrees * MathUtils.DEG_RAD)
    
    @staticmethod
    def atan2(y, x):
        return math.atan2(y, x)

@dataclass
class AnimationSlotTimeline:
    slot_name: str
    timelines: List[Dict]  

@dataclass
class Animation:
    name: str
    duration: float
    slot_timelines: List[AnimationSlotTimeline] = field(default_factory=list)

@dataclass
class BoneData:
    def __init__(self, 
                 name: str,
                 parent: Optional['BoneData'] = None,
                 length: float = 0,
                 x: float = 0,
                 y: float = 0,
                 rotation: float = 0,
                 scaleX: float = 1,
                 scaleY: float = 1,
                 shearX: float = 0,
                 shearY: float = 0):
        self.name = name
        self.parent = parent
        self.length = length
        self.x = x
        self.y = y
        self.rotation = rotation
        self.scaleX = scaleX
        self.scaleY = scaleY
        self.shearX = shearX
        self.shearY = shearY
        
        # 世界变换
        self.world_x = 0
        self.world_y = 0
        self.world_rotation = 0
        self.world_scaleX = 1
        self.world_scaleY = 1
        
        # 变换矩阵组件
        self.a = 1
        self.b = 0
        self.c = 0
        self.d = 1
        
        self.applied_valid = True
        self.ax = x
        self.ay = y
        self.arotation = rotation
        self.ascaleX = scaleX
        self.ascaleY = scaleY
        self.ashearX = shearX
        self.ashearY = shearY

        # 变换模式
        self.transform_mode = TransformMode.Normal

    def update_world_transform(self, skeleton=None):
        """更新世界变换 - 基于 Spine 3.8 实现"""
        if skeleton is None:
            sx = 1
            sy = 1
        else:
            sx = skeleton.scale_x
            sy = skeleton.scale_y

        parent = self.parent
        
        if parent is None:
            # 根骨骼
            rotation_y = self.rotation + 90 + self.shearY
            
            # 计算变换矩阵
            self.a = MathUtils.cos_deg(self.rotation + self.shearX) * self.scaleX * sx
            self.b = MathUtils.cos_deg(rotation_y) * self.scaleY * sx
            self.c = MathUtils.sin_deg(self.rotation + self.shearX) * self.scaleX * sy
            self.d = MathUtils.sin_deg(rotation_y) * self.scaleY * sy
            
            # 计算世界坐标
            if skeleton:
                self.world_x = self.x * sx + skeleton.x
                self.world_y = self.y * sy + skeleton.y
            else:
                self.world_x = self.x * sx
                self.world_y = self.y * sy
                
        else:
            # 子骨骼
            pa = parent.a
            pb = parent.b
            pc = parent.c
            pd = parent.d
            
            # 计算世界坐标
            self.world_x = pa * self.x + pb * self.y + parent.world_x
            self.world_y = pc * self.x + pd * self.y + parent.world_y
            
            # 根据变换模式计算矩阵
            if self.transform_mode == TransformMode.Normal:
                rotation_y = self.rotation + 90 + self.shearY
                la = MathUtils.cos_deg(self.rotation + self.shearX) * self.scaleX
                lb = MathUtils.cos_deg(rotation_y) * self.scaleY
                lc = MathUtils.sin_deg(self.rotation + self.shearX) * self.scaleX
                ld = MathUtils.sin_deg(rotation_y) * self.scaleY
                
                # 计算最终矩阵
                self.a = pa * la + pb * lc
                self.b = pa * lb + pb * ld
                self.c = pc * la + pd * lc
                self.d = pc * lb + pd * ld
            elif self.transform_mode == TransformMode.OnlyTranslation:
                rotation_y = self.rotation + 90 + self.shearY
                self.a = MathUtils.cos_deg(self.rotation + self.shearX) * self.scaleX
                self.b = MathUtils.cos_deg(rotation_y) * self.scaleY
                self.c = MathUtils.sin_deg(self.rotation + self.shearX) * self.scaleX
                self.d = MathUtils.sin_deg(rotation_y) * self.scaleY
            
        # 应用全局缩放
        self.a *= sx
        self.b *= sx
        self.c *= sy
        self.d *= sy
        
        # 更新世界变换属性
        self.world_rotation = MathUtils.atan2(self.c, self.a) * MathUtils.RAD_DEG
        self.world_scaleX = math.sqrt(self.a * self.a + self.c * self.c)
        self.world_scaleY = math.sqrt(self.b * self.b + self.d * self.d)

@dataclass
class SlotData:
    def __init__(self, 
                 name: str, 
                 bone_data: BoneData,
                 attachment_name: Optional[str] = None):
        self.name = name
        self.bone_data = bone_data
        self.attachment_name = attachment_name
        self.color = Color(1, 1, 1, 1) 
        self.blend_mode = "normal"   

@dataclass
class Attachment:
    """附件基类"""
    name: str
    type: AttachmentType

@dataclass
class RegionAttachment(Attachment):
    def __init__(self, name: str, **kwargs):
        """初始化区域附件"""
        super().__init__(name=name, type=AttachmentType.Region)
        self.path = kwargs.get('path', "")
        self.x = kwargs.get('x', 0)
        self.y = kwargs.get('y', 0)
        self.scaleX = kwargs.get('scaleX', 1)
        self.scaleY = kwargs.get('scaleY', 1)
        self.rotation = kwargs.get('rotation', 0)
        self.width = kwargs.get('width', 0)
        self.height = kwargs.get('height', 0)
        self.color = kwargs.get('color', Color())
        self.region = kwargs.get('region', None)
        self.offset = [0] * 8
        self.uvs = [0] * 8

    def compute_world_vertices(self, bone: 'Bone', vertices: list, screen_height: int):
        """计算四个顶点在 Pygame 坐标系下的位置，支持 rotate"""
        x = bone.world_x
        y = bone.world_y
        a = bone.a
        b = bone.b
        c = bone.c
        d = bone.d

        w = self.width
        h = self.height
        if self.region and self.region.rotate:
            w, h = h, w  

        # 图像中心原点本地坐标
        local_vertices = [  
            self.x - w / 2, self.y - h / 2,
            self.x + w / 2, self.y - h / 2,
            self.x + w / 2, self.y + h / 2,
            self.x - w / 2, self.y + h / 2,
        ]

        rad = math.radians(self.rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        for i in range(4):
            lx = local_vertices[i * 2]
            ly = local_vertices[i * 2 + 1]

            # 本地旋转
            rx = lx * cos_r - ly * sin_r
            ry = lx * sin_r + ly * cos_r

            # 应用骨骼变换
            wx = rx * a + ry * b + x
            wy = rx * c + ry * d + y

            # 转 Pygame Y 轴方向
            vertices.append(wx)
            vertices.append(screen_height - wy)

@dataclass
class MeshAttachment(Attachment):
    path: str
    color: Color = field(default_factory=Color)
    uvs: list = field(default_factory=list)
    vertices: list = field(default_factory=list)
    triangles: list = field(default_factory=list)
    region: Optional['TextureRegion'] = None

@dataclass
class Skin:
    """皮肤"""
    name: str
    attachments: Dict[Tuple[int, str], Attachment] = field(default_factory=dict)

@dataclass
class SkeletonData:
    """骨骼数据"""
    name: str = ""
    bones: List[BoneData] = field(default_factory=list)
    slots: List[SlotData] = field(default_factory=list)
    skins: List[Skin] = field(default_factory=list)
    default_skin: Optional[Skin] = None
    animations: List[Animation] = field(default_factory=list)
    
    # 添加全局属性
    scale_x: float = 1
    scale_y: float = 1
    x: float = 0
    y: float = 0
    
    # 版本信息
    version: str = ""
    hash: str = "" 
    width: float = 0
    height: float = 0
    fps: float = 30
    images_path: Optional[str] = None