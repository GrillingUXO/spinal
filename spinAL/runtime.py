from skeleton_data import BoneData, SlotData, RegionAttachment, Attachment, Skin, SkeletonData
from mytypes import Color, SpineRenderSettings, AttachmentType
import math
import pygame
from dataclasses import dataclass, field
from typing import Optional


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