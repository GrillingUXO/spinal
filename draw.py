from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import IntEnum 
import json
import pygame
import math
import os

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
    r: float = 1.0
    g: float = 1.0
    b: float = 1.0
    a: float = 1.0
    
    def to_pygame_color(self) -> tuple:
        return (
            int(self.r * 255),
            int(self.g * 255), 
            int(self.b * 255),
            int(self.a * 255)
        )

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

@dataclass
class SlotData:
    """插槽数据"""
    name: str
    bone_data: BoneData
    color: Color = field(default_factory=Color)
    attachment_name: Optional[str] = None
    blend_mode: BlendMode = BlendMode.Normal

@dataclass
class Attachment:
    """附件基类"""
    name: str
    type: AttachmentType

@dataclass
class RegionAttachment(Attachment):
    """区域附件"""
    path: str = ""
    x: float = 0
    y: float = 0
    scaleX: float = 1
    scaleY: float = 1
    rotation: float = 0
    width: float = 0
    height: float = 0
    color: Color = field(default_factory=Color)
    region: Optional[TextureRegion] = None
    offset: List[float] = field(default_factory=lambda: [0] * 8)
    uvs: List[float] = field(default_factory=lambda: [0] * 8)

    def compute_world_vertices(self, bone, vertices: List[float], offset: int):
        """计算世界坐标系顶点"""
        # 实现顶点变换...
        pass

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

class Bone:
    """骨骼实例"""
    def __init__(self, data: BoneData, parent: Optional['Bone']):
        self.data = data
        self.parent = parent
        
        self.x = data.x
        self.y = data.y
        self.rotation = data.rotation
        self.scaleX = data.scaleX
        self.scaleY = data.scaleY
        self.shearX = data.shearX 
        self.shearY = data.shearY
        
        self.ax = 0  # Applied x
        self.ay = 0  # Applied y
        self.arotation = 0
        self.ascaleX = 0
        self.ascaleY = 0
        self.ashearX = 0
        self.ashearY = 0
        
        self.a = 1  # World transform
        self.b = 0
        self.c = 0
        self.d = 1
        self.world_x = 0
        self.world_y = 0
        
        self.update_applied_transform()
        
    def update_world_transform(self):
        """更新世界变换"""
        parent = self.parent
        
        # 旋转矩阵计算
        rotation = self.arotation
        cos = math.cos(math.radians(rotation))
        sin = math.sin(math.radians(rotation))
        
        # 缩放和错切
        scale_x = self.ascaleX
        scale_y = self.ascaleY
        shear_x = math.radians(self.ashearX)
        shear_y = math.radians(self.ashearY)
        
        self.a = (cos + math.sin(shear_x) * shear_y) * scale_x
        self.b = (sin + math.cos(shear_x) * shear_y) * scale_x
        self.c = (-sin + math.sin(shear_y)) * scale_y
        self.d = (cos + math.cos(shear_y)) * scale_y
        
        if parent:
            # 组合父骨骼变换
            self.world_x = self.ax * parent.a + self.ay * parent.b + parent.world_x
            self.world_y = self.ax * parent.c + self.ay * parent.d + parent.world_y
            
            if self.data.transform_mode <= TransformMode.NoScale:
                # 正常变换
                pa = parent.a
                pb = parent.b
                pc = parent.c
                pd = parent.d
                self.a = self.a * pa + self.b * pc
                self.b = self.a * pb + self.b * pd
                self.c = self.c * pa + self.d * pc
                self.d = self.c * pb + self.d * pd
            else:
                # 特殊变换模式...
                pass
        else:
            self.world_x = self.ax
            self.world_y = self.ay
            
    def update_applied_transform(self):
        """更新应用的变换"""
        self.ax = self.x
        self.ay = self.y
        self.arotation = self.rotation
        self.ascaleX = self.scaleX
        self.ascaleY = self.scaleY
        self.ashearX = self.shearX
        self.ashearY = self.shearY

class Slot:
    """插槽实例"""
    def __init__(self, data: SlotData, bone: Bone):
        self.data = data
        self.bone = bone
        self.color = Color(*data.color.__dict__.values())
        self.attachment: Optional[Attachment] = None
        self.attachment_time = 0
        
    def set_attachment(self, attachment: Optional[Attachment]):
        """设置附件"""
        self.attachment = attachment
        self.attachment_time = 0

class Skeleton:
    """骨骼动画实例"""
    def __init__(self, data: SkeletonData):
        # 修改骨骼实例化顺序为层级顺序
        self.bones = []
        bone_data_list = sorted(data.bones, key=lambda b: len(b.parent.name) if b.parent else 0)
        for bone_data in bone_data_list:
            parent = next((b for b in self.bones if b.data.name == bone_data.parent.name), None)
            bone = Bone(bone_data, parent)
            self.bones.append(bone)
            
        # 创建插槽实例
        self.slots: List[Slot] = []
        for slot_data in data.slots:
            bone = next(
                b for b in self.bones 
                if b.data.name == slot_data.bone_data.name
            )
            slot = Slot(slot_data, bone)
            self.slots.append(slot)
            
        # 设置初始附件
        self.skin: Optional[Skin] = None
        if data.default_skin:
            self.set_skin(data.default_skin)
            
    def set_skin(self, skin: Skin):
        """设置皮肤"""
        self.skin = skin
        
        # 应用初始附件
        if skin:
            for i, slot in enumerate(self.slots):
                name = slot.data.attachment_name
                if name:
                    attachment = skin.attachments.get((i, name))
                    if attachment:
                        slot.set_attachment(attachment)
                        
    def update_world_transform(self):
        """更新世界变换"""
        for bone in self.bones:
            bone.update_world_transform()

    def draw(self, surface: pygame.Surface):
            """渲染骨骼"""
            self.update_world_transform()
            
            for slot in self.slots:
                if not slot.attachment:
                    continue
                    
                if isinstance(slot.attachment, RegionAttachment):
                    region = slot.attachment.region
                    if not region or not region.texture:
                        continue
                    
                # 关键修改1：使用附件自身的偏移量
                bone = slot.bone
                attachment = slot.attachment
                x = attachment.x
                y = attachment.y
                
                # 计算世界坐标
                px = x * bone.a + y * bone.b + bone.world_x
                py = x * bone.c + y * bone.d + bone.world_y
                
                # 关键修改2：正确的旋转和缩放计算
                rotation = -math.degrees(math.atan2(bone.c, bone.a))
                scale_x = math.hypot(bone.a, bone.c)
                scale_y = math.hypot(bone.b, bone.d)
                
                # 获取原始纹理并转换
                texture = region.texture.copy()
                
                # 缩放处理
                if scale_x != 1 or scale_y != 1:
                    new_w = max(1, int(texture.get_width() * scale_x))
                    new_h = max(1, int(texture.get_height() * scale_y))
                    texture = pygame.transform.smoothscale(texture, (new_w, new_h))
                
                # 修复点：修正旋转后的子表面裁剪
                if rotation != 0:
                    rot_texture = pygame.transform.rotate(texture, rotation)
                    texture = rot_texture.copy() 

                
                # 颜色混合和透明度处理
                if slot.color != Color():
                    color_surf = pygame.Surface(texture.get_size(), pygame.SRCALPHA)
                    rgba = slot.color.to_pygame_color()
                    color_surf.fill(rgba)
                    texture.blit(color_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                
                if slot.color.a != 1:
                    texture.set_alpha(int(slot.color.a * 255))
                
                # 绘制位置修正
                draw_x = px - texture.get_width() / 2
                draw_y = py - texture.get_height() / 2
                surface.blit(texture, (draw_x, draw_y))   

           
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
running = True
while running:
    # 处理事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
    # 清屏
    screen.fill((255, 255, 255))
    
    # 更新和渲染骨骼
    skeleton.update_world_transform()
    skeleton.draw(screen)
    
    # 刷新屏幕
    pygame.display.flip()
    clock.tick(60)
    
pygame.quit()