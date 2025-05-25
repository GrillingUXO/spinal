from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from mytypes import AttachmentType, BlendMode, Color, TransformMode
from dataclasses import dataclass, field
import math

@dataclass
class BoneData:
    """骨骼数据"""
    name: str
    parent: Optional['BoneData'] = None
    length: float = 0
    x: float = 0
    y: float = 0
    rotation: float = 0
    scaleX: float = 1
    scaleY: float = 1
    shearX: float = 0
    shearY: float = 0
    transform_mode: TransformMode = TransformMode.Normal
    skin_required: bool = False

@dataclass
class SlotData:
    """插槽数据"""
    name: str
    bone_data: BoneData
    attachment_name: Optional[str] = None
    color: Color = field(default_factory=Color)
    blend_mode: BlendMode = BlendMode.Normal

@dataclass
class Attachment:
    """附件基类"""
    name: str
    type: AttachmentType

@dataclass
class RegionAttachment(Attachment):

    def compute_world_vertices(self, bone: 'Bone', vertices: list, screen_height: int):
        """计算四个顶点在 Pygame 坐标系下的位置，支持 rotate"""
        x = bone.world_x
        y = bone.world_y
        a = bone.a
        b = bone.b
        c = bone.c
        d = bone.d

        # 区分 rotate:true 的纹理尺寸
        w = self.width
        h = self.height
        if self.region and self.region.rotate:
            w, h = h, w  # 宽高互换

        # 图像中心原点本地坐标
        local_vertices = [
            self.x - w / 2, self.y - h / 2,
            self.x + w / 2, self.y - h / 2,
            self.x + w / 2, self.y + h / 2,
            self.x - w / 2, self.y + h / 2,
        ]

        # 绕 attachment.rotation 旋转（注意是逆时针）
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
            vertices.append(wy)

            
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


@dataclass
class Skin:
    """皮肤"""
    name: str
    attachments: Dict[tuple[int, str], Attachment] = field(default_factory=dict)

@dataclass
class SkeletonData:
    
    """骨骼数据"""
    name: str = ""
    bones: List[BoneData] = field(default_factory=list)
    slots: List[SlotData] = field(default_factory=list) 
    skins: List[Skin] = field(default_factory=list)
    default_skin: Optional[Skin] = None
    