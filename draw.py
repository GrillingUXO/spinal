
from typing import List, Dict, Optional
from enum import IntEnum 
import json
import pygame
import math
import os

from dataclasses import dataclass, field


@dataclass
class SpineRenderSettings:
    """Spine渲染设置"""
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
class TextureRegion:
    """纹理区域数据"""
    name: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    u: float = 0.0
    v: float = 0.0
    u2: float = 1.0
    v2: float = 1.0
    rotate: bool = False
    texture: Optional[pygame.Surface] = None

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
class Bone:
    """骨骼实例，所有坐标系相关的变换都在这里处理"""
    data: 'BoneData'  # 需要定义在前面
    parent: Optional['Bone'] = None
    
    # 本地变换属性
    x: float = 0
    y: float = 0
    rotation: float = 0
    scaleX: float = 1
    scaleY: float = 1
    shearX: float = 0
    shearY: float = 0
    
    # 激活状态
    active: bool = True
    
    # 世界变换矩阵
    a: float = 1  # scale * cos
    b: float = 0  # scale * sin
    c: float = 0  # -sin * scale
    d: float = 1  # cos * scale
    world_x: float = 0
    world_y: float = 0
    
    def __post_init__(self):
        """初始化完成后设置初始状态"""
        self.x = self.data.x
        self.y = self.data.y
        self.rotation = self.data.rotation
        self.scaleX = self.data.scaleX
        self.scaleY = self.data.scaleY
        self.shearX = self.data.shearX
        self.shearY = self.data.shearY
        self.update_world_transform()
    
    def update_world_transform(self):
        """更新世界变换 - 基于Spine v38的实现"""
        rotation = math.radians(self.rotation)
        cos = math.cos(rotation)
        sin = math.sin(rotation)
        
        # 本地变换矩阵
        self.a = cos * self.scaleX
        self.b = sin * self.scaleX
        self.c = -sin * self.scaleY
        self.d = cos * self.scaleY
        
        if self.parent:
            # 组合父骨骼变换
            pa = self.parent.a
            pb = self.parent.b
            pc = self.parent.c
            pd = self.parent.d
            
            # 计算世界坐标
            self.world_x = self.x * pa + self.y * pb + self.parent.world_x
            self.world_y = self.x * pc + self.y * pd + self.parent.world_y
            
            # 合并变换矩阵
            temp_a = self.a
            temp_b = self.b
            temp_c = self.c
            temp_d = self.d
            
            self.a = temp_a * pa + temp_b * pc
            self.b = temp_a * pb + temp_b * pd
            self.c = temp_c * pa + temp_d * pc
            self.d = temp_c * pb + temp_d * pd
        else:
            # 没有父骨骼，直接使用本地坐标
            self.world_x = self.x
            self.world_y = self.y

class Slot:
    """插槽实例"""
    def __init__(self, data: SlotData, bone: 'Bone'):
        self.data = data
        self.bone = bone
        self.color = Color(*data.color.__dict__.values())
        self.attachment: Optional[Attachment] = None
        self.attachment_time = 0
        self.blend_mode = data.blend_mode  # 使用枚举
        
        # 颜色分量
        self.r = 1.0
        self.g = 1.0
        self.b = 1.0
        self.a = 1.0

    def set_attachment(self, attachment: Optional[Attachment]):
        """设置附件"""
        self.attachment = attachment
        self.attachment_time = 0


def _read_attachment(self, attachment_map: dict, name: str) -> Optional[Attachment]:
    """读取附件数据"""
    type_name = attachment_map.get("type", "region")
    attachment_type = AttachmentType[type_name.title()]
    
    if attachment_type == AttachmentType.Region:
        path = attachment_map.get("path", name)
        region = self.atlas.find_region(path)
        if not region:
            return None
            
        attachment = RegionAttachment(
            name=name,
            path=path,
            x=attachment_map.get("x", 0) * self.scale,
            y=attachment_map.get("y", 0) * self.scale,
            scaleX=attachment_map.get("scaleX", 1),
            scaleY=attachment_map.get("scaleY", 1),
            rotation=attachment_map.get("rotation", 0),
            width=attachment_map.get("width", region.width) * self.scale,
            height=attachment_map.get("height", region.height) * self.scale,
            region=region
        )
        
        if "color" in attachment_map:
            color = attachment_map["color"] 
            if len(color) == 8:
                attachment.color = Color(
                    int(color[0:2], 16) / 255.0,
                    int(color[2:4], 16) / 255.0,
                    int(color[4:6], 16) / 255.0,
                    int(color[6:8], 16) / 255.0
                )
        
        return attachment
        
    return None

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
    
class Atlas:
    def __init__(self, file_path: str):
        self.regions: Dict[str, TextureRegion] = {}
        self.load(file_path)

    def load(self, atlas_path: str):
        atlas_dir = os.path.dirname(atlas_path)
        
        with open(atlas_path, 'r') as f:
            lines = [line.rstrip('\n') for line in f.readlines()]  # 移除换行符
        
        i = 0
        current_page = None
        texture = None  # 显式声明texture变量
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                current_page = None
                i += 1
                continue
            
            # 处理新纹理页
            if not current_page:
                texture_path = os.path.join(atlas_dir, line)
                try:
                    texture = pygame.image.load(texture_path).convert_alpha()
                except pygame.error:
                    print(f"无法加载纹理: {texture_path}")
                    return
                current_page = texture
                
                # 跳过纹理页属性（不使用的字段）
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if not line:
                        break
                    if ':' not in line:  # 新区域开始
                        break
                    i += 1
                continue
            
            # 处理区域定义
            region = TextureRegion()
            region.name = line
            i += 1  # 移动到属性行
            
            while i < len(lines):
                line = lines[i].strip()
                if not line:  # 空行表示区域结束
                    i += 1
                    break
                if ':' not in line:  # 新区域开始
                    break
                
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'rotate':
                    region.rotate = (value == 'true')
                elif key == 'xy':
                    region.x, region.y = map(int, value.split(','))
                elif key == 'size':
                    region.width, region.height = map(int, value.split(','))
                elif key == 'orig':
                    pass  # 原始尺寸不需要处理
                elif key == 'offset':
                    pass  # 偏移量不需要处理
                elif key == 'index':
                    pass  # 索引不需要处理
                
                i += 1  # 确保每次处理都递增
            
            # 计算UV坐标
            if texture:
                tex_width = texture.get_width()
                tex_height = texture.get_height()
                
                region.u = region.x / tex_width
                region.v = region.y / tex_height
                if region.rotate:
                    region.u2 = (region.x + region.height) / tex_width
                    region.v2 = (region.y + region.width) / tex_height
                else:
                    region.u2 = (region.x + region.width) / tex_width
                    region.v2 = (region.y + region.height) / tex_height
                
                # 提取子纹理
                try:
                    sub_rect = (region.x, region.y, region.width, region.height)
                    sub_surface = texture.subsurface(sub_rect)
                    if region.rotate:
                        sub_surface = pygame.transform.rotate(sub_surface, -90)
                    region.texture = sub_surface
                except ValueError:
                    print(f"无效的纹理区域: {region.name}")
                    continue
            
            self.regions[region.name] = region

    def find_region(self, name: str) -> Optional[TextureRegion]:
        return self.regions.get(name)


class SkeletonJson:
    """骨骼JSON加载器"""
    def __init__(self, atlas: Atlas):  # 接受Atlas实例
        self.atlas = atlas  # 保存图集引用
        self.scale = 1.0
        
    def read_skeleton_data(self, path: str) -> SkeletonData:
        """读取骨骼数据"""
        with open(path, 'r') as f:
            root = json.load(f)
            
        skeleton_data = SkeletonData()
        
        # 读取骨骼
        if "bones" in root:
            for bone_map in root["bones"]:
                parent = None
                if "parent" in bone_map:
                    parent_name = bone_map["parent"]
                    parent = next(
                        (b for b in skeleton_data.bones if b.name == parent_name),
                        None
                    )
                
                bone_data = BoneData(
                    name=bone_map["name"],
                    parent=parent,
                    length=bone_map.get("length", 0) * self.scale,
                    x=bone_map.get("x", 0) * self.scale,
                    y=bone_map.get("y", 0) * self.scale,
                    rotation=bone_map.get("rotation", 0),
                    scaleX=bone_map.get("scaleX", 1),
                    scaleY=bone_map.get("scaleY", 1),
                    shearX=bone_map.get("shearX", 0),
                    shearY=bone_map.get("shearY", 0)
                )
                skeleton_data.bones.append(bone_data)
                
        # 读取插槽
        if "slots" in root:
            for slot_map in root["slots"]:
                bone_name = slot_map["bone"]
                bone_data = next(
                    (b for b in skeleton_data.bones if b.name == bone_name),
                    None
                )
                if not bone_data:
                    raise Exception(f"Bone not found: {bone_name}")
                    
                slot_data = SlotData(
                    name=slot_map["name"],
                    bone_data=bone_data,
                    attachment_name=slot_map.get("attachment")
                )
                
                if "color" in slot_map:
                    color = slot_map["color"]
                    if len(color) == 8:
                        slot_data.color = Color(
                            int(color[0:2], 16) / 255.0,
                            int(color[2:4], 16) / 255.0,
                            int(color[4:6], 16) / 255.0,
                            int(color[6:8], 16) / 255.0
                        )
                        
                skeleton_data.slots.append(slot_data)
                
        # 读取皮肤
        if "skins" in root:
            for skin_obj in root["skins"]:  # 遍历皮肤列表
                skin_name = skin_obj.get("name", "default")
                skin = Skin(skin_name)
                
                # 获取附件数据（假设结构为skin_obj["attachments"]）
                for slot_name, slot_map in skin_obj.get("attachments", {}).items():
                    slot_index = next(
                        (i for i, s in enumerate(skeleton_data.slots) 
                         if s.name == slot_name),
                        -1
                    )
                    if slot_index == -1:
                        continue
                        
                    for attachment_name, attachment_map in slot_map.items():
                        attachment = self._read_attachment(
                            attachment_map,
                            attachment_name
                        )
                        if attachment:
                            skin.attachments[(slot_index, attachment_name)] = attachment
                
                skeleton_data.skins.append(skin)
                if skin_name == "default":
                    skeleton_data.default_skin = skin

        return skeleton_data
    
    def _read_attachment(self, 
                        attachment_map: dict, 
                        name: str) -> Optional[Attachment]:
        """读取附件数据"""
        type_name = attachment_map.get("type", "region")
        attachment_type = AttachmentType[type_name.title()]
        
        if attachment_type == AttachmentType.Region:
            path = attachment_map.get("path", name)
            region = self.atlas.find_region(path)
            if not region:
                return None
                
            attachment = RegionAttachment(
                name=name,
                type=attachment_type,
                path=path,
                x=attachment_map.get("x", 0) * self.scale,
                y=attachment_map.get("y", 0) * self.scale,
                scaleX=attachment_map.get("scaleX", 1),
                scaleY=attachment_map.get("scaleY", 1),
                rotation=attachment_map.get("rotation", 0),
                width=attachment_map.get("width", region.width) * self.scale,
                height=attachment_map.get("height", region.height) * self.scale
            )
            
            if "color" in attachment_map:
                color = attachment_map["color"] 
                if len(color) == 8:
                    attachment.color = Color(
                        int(color[0:2], 16) / 255.0,
                        int(color[2:4], 16) / 255.0,
                        int(color[4:6], 16) / 255.0,
                        int(color[6:8], 16) / 255.0
                    )
                    
            attachment.region = region
            # 计算顶点偏移和UV...
            return attachment
            
        return None


class Skeleton:

    def __init__(self, data: SkeletonData):
        self.r = 1.0  # 红色分量
        self.g = 1.0  # 绿色分量
        self.b = 1.0  # 蓝色分量
        self.a = 1.0  

        self.data = data
        self.bones = []
        self.slots = []
        self.skin = None
        self.render_settings = SpineRenderSettings()
        
        # 初始化骨骼 - 确保父骨骼在前
        bone_map = {}
        for bone_data in data.bones:
            parent = None
            if bone_data.parent:
                parent = bone_map.get(bone_data.parent.name)
            bone = Bone(bone_data, parent)
            bone_map[bone_data.name] = bone
            self.bones.append(bone)
        
        # 初始化插槽 - 按照原始顺序
        for slot_data in data.slots:
            bone = bone_map.get(slot_data.bone_data.name)
            if bone:
                slot = Slot(slot_data, bone)
                self.slots.append(slot)
                
        # 设置默认皮肤
        if data.default_skin:
            self.set_skin(data.default_skin)
            
    def set_skin(self, skin: Skin):
        self.skin = skin
        if skin:
            for i, slot in enumerate(self.slots):
                name = slot.data.attachment_name
                if name:
                    attachment = skin.attachments.get((i, name))
                    if attachment:
                        slot.set_attachment(attachment)

    def update_world_transform(self):
        """更新所有骨骼的世界变换"""
        for bone in self.bones:
            if bone.active:
                bone.update_world_transform()

    def draw(self, surface: pygame.Surface):
        self.update_world_transform()
        
        screen_width = surface.get_width()
        screen_height = surface.get_height()
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        # 渲染设置
        scale = self.render_settings.scale
        offset_x = self.render_settings.position_x
        offset_y = self.render_settings.position_y
        
        for slot in self.slots:
            if not slot.bone.active:
                continue
                
            attachment = slot.attachment
            if not attachment or attachment.type != AttachmentType.Region:
                continue
                
            region = attachment.region
            if not region or not region.texture:
                continue
                
            texture = region.texture.copy()
            
            # 计算颜色混合
            tint_r = self.r * slot.r * attachment.color.r
            tint_g = self.g * slot.g * attachment.color.g
            tint_b = self.b * slot.b * attachment.color.b
            tint_a = self.a * slot.a * attachment.color.a
            
            # 计算顶点数据（适配Pygame坐标系）
            vertices = []
            attachment.compute_world_vertices(slot.bone, vertices, screen_height)
            
            # 使用第一个顶点的位置作为基准
            world_x = vertices[0]
            world_y = vertices[1]
            
            # 应用全局变换
            avg_x = sum(vertices[i*2] for i in range(4)) / 4
            avg_y = sum(vertices[i*2+1] for i in range(4)) / 4
            px = center_x + (world_x + offset_x) * scale
            py = screen_height - ((world_y + offset_y) * scale)
            
            # 计算缩放
            bone = slot.bone
            bone_scale_x = math.sqrt(bone.a ** 2 + bone.c ** 2)
            bone_scale_y = math.sqrt(bone.b ** 2 + bone.d ** 2)
            raw_scale_x = bone_scale_x * attachment.scaleX * scale
            raw_scale_y = bone_scale_y * attachment.scaleY * scale

            # 处理翻转
            scale_x = abs(raw_scale_x)
            scale_y = abs(raw_scale_y)

            # 仅根据全局设置是否翻转
            flip_x = self.render_settings.flip_x
            flip_y = self.render_settings.flip_y

            # 缩放纹理
            if scale_x != 1 or scale_y != 1:
                new_w = max(1, int(texture.get_width() * scale_x))
                new_h = max(1, int(texture.get_height() * scale_y))
                try:
                    texture = pygame.transform.smoothscale(texture, (new_w, new_h))
                except ValueError:
                    continue

            # 翻转纹理
            if flip_x or flip_y:
                texture = pygame.transform.flip(texture, flip_x, flip_y)

            # 计算旋转（适配Pygame的顺时针方向）
            rotation = math.degrees(math.atan2(bone.c, bone.a))
            rotation = -rotation
            rotation += attachment.rotation

            # 旋转纹理
            if rotation != 0:
                texture = pygame.transform.rotate(texture, rotation)

            # 颜色混合和透明度
            if self.render_settings.use_premultiplied_alpha:
                texture.set_alpha(int(tint_a * 255))
                if tint_r != 1.0 or tint_g != 1.0 or tint_b != 1.0:
                    color_surf = pygame.Surface(texture.get_size(), pygame.SRCALPHA)
                    color = (int(tint_r * 255), int(tint_g * 255), int(tint_b * 255), 255)
                    color_surf.fill(color)
                    texture.blit(color_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            # 最终绘制（底部中心锚点）
            min_x = min(vertices[i*2] for i in range(4))
            min_y = min(vertices[i*2+1] for i in range(4))
            draw_x = center_x + (min_x + offset_x) * scale
            draw_y = center_y + (min_y + offset_y) * scale
            surface.blit(texture, (draw_x, draw_y))


                    

    
    def draw_debug(self, surface: pygame.Surface):
        """绘制调试信息"""
        center_x = surface.get_width() // 2
        center_y = surface.get_height() // 2
        scale = self.render_settings.scale
        
        for bone in self.bones:
            # 计算世界坐标
            wx = center_x + (bone.world_x + self.render_settings.position_x) * scale
            wy = center_y + (bone.world_y + self.render_settings.position_y) * scale
            
            # 绘制骨骼点
            pygame.draw.circle(surface, (255, 0, 0), (int(wx), int(wy)), 3)
            
            # 绘制骨骼连接线
            if bone.parent:
                parent_wx = center_x + (bone.parent.world_x + self.render_settings.position_x) * scale
                parent_wy = center_y + (bone.parent.world_y + self.render_settings.position_y) * scale
                pygame.draw.line(surface, (0, 255, 0),
                               (int(parent_wx), int(parent_wy)),
                               (int(wx), int(wy)), 1)

                
                
# 初始化pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# 加载Spine资源
atlas = Atlas("/Users/michelleyan/Downloads/skel/xianghe.atlas") 
json_loader = SkeletonJson(atlas) 
skeleton_data = json_loader.read_skeleton_data("/Users/michelleyan/Downloads/skel/xianghe.json")
skeleton = Skeleton(skeleton_data)


# 游戏主循环
# 游戏主循环
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            # 位置控制
            if event.key == pygame.K_LEFT:
                skeleton.render_settings.position_x -= 10
            elif event.key == pygame.K_RIGHT:
                skeleton.render_settings.position_x += 10
            elif event.key == pygame.K_UP:
                skeleton.render_settings.position_y -= 10
            elif event.key == pygame.K_DOWN:
                skeleton.render_settings.position_y += 10
            # 缩放控制    
            elif event.key == pygame.K_q:
                skeleton.render_settings.scale += 0.1
            elif event.key == pygame.K_a:
                skeleton.render_settings.scale = max(0.1, skeleton.render_settings.scale - 0.1)
            # 翻转控制
            elif event.key == pygame.K_x:
                skeleton.render_settings.flip_x = not skeleton.render_settings.flip_x
            elif event.key == pygame.K_y:
                skeleton.render_settings.flip_y = not skeleton.render_settings.flip_y
            # 重置
            elif event.key == pygame.K_r:
                skeleton.render_settings = SpineRenderSettings()
                
    # 清屏
    screen.fill((255, 255, 255))
    
    # 绘制
    skeleton.draw(screen)
    skeleton.draw_debug(screen)
    
    pygame.display.flip()
    clock.tick(60)