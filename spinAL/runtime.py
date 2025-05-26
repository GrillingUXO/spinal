from skeleton_data import BoneData, SlotData, RegionAttachment, Attachment, Skin, SkeletonData
from mytypes import Color, SpineRenderSettings, AttachmentType
import math
import pygame
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Bone:
    data: 'BoneData' 
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
        self.all_bones = []
        self.bones = []
        self.slots = []
        self.skin = None
        self.render_settings = SpineRenderSettings()
        
        # 确保父骨骼在前
        bone_map = {}
        for bone_data in data.bones:
            parent = None
            if bone_data.parent:
                parent = bone_map.get(bone_data.parent.name)
            bone = Bone(bone_data, parent)
            bone_map[bone_data.name] = bone
            self.bones.append(bone)

        for slot_data in data.slots:
            bone = bone_map.get(slot_data.bone_data.name)
            if bone:
                slot = Slot(slot_data, bone)
                self.slots.append(slot)
                
        if data.default_skin:
            self.set_skin(data.default_skin)
            
    def set_skin(self, skin: Skin):
        self.skin = skin
        if not skin:
            return

        for i, slot in enumerate(self.slots):
            slot_data = slot.data
            attachment_name = slot_data.attachment_name

            if attachment_name is None:
                continue

            key = (i, attachment_name)
            attachment = skin.attachments.get(key)

            if attachment:
                slot.set_attachment(attachment)
            else:
                print(f"[WARNING] Missing attachment for slot '{slot_data.name}' (index {i}) with name '{attachment_name}'")


    def update_world_transform(self):
        """更新所有骨骼的世界变换"""
        for bone in self.bones:
            if bone.active:
                bone.update_world_transform()


    def reset_bones_from_names(self, bone_names: set[str]):

        bone_instance_map = {bone.data.name: bone for bone in self.bones}
        
        for bone in self.bones:
            bone.active = False
        
        # 仅激活当前动画使用的骨骼及其父骨骼
        used_bones = set()
        def activate_bone(name):
            if name in used_bones or name not in bone_instance_map:
                return
            bone = bone_instance_map[name]
            bone.active = True
            used_bones.add(name)
            if bone.data.parent:
                activate_bone(bone.data.parent.name)
        
        for name in bone_names:
            activate_bone(name)

        self.bones = sorted(
            [bone for bone in self.bones if bone.active],
            key=lambda b: b.data.parent.name if b.data.parent else ""
        )


    def draw(self, surface: pygame.Surface):
        self.update_world_transform()

        screen_width = surface.get_width()
        screen_height = surface.get_height()
        center_x = screen_width // 2
        center_y = screen_height // 2

        scale = self.render_settings.scale
        offset_x = self.render_settings.position_x
        offset_y = self.render_settings.position_y

        if not self.skin:
            return

        used_attachments = set()

        for bone in self.bones:
            bone_name = bone.data.name

            matched_attachment = None
            for (slot_index, attachment_name), attachment in self.skin.attachments.items():
                if attachment.type != AttachmentType.Region:
                    continue
                if attachment.name.startswith(bone_name) or attachment.path.startswith(bone_name):

                    if attachment.name in used_attachments:
                        continue
                    matched_attachment = attachment
                    used_attachments.add(attachment.name)
                    break

            if not matched_attachment:
                continue

            attachment = matched_attachment
            region = attachment.region
            if not region or not region.texture:
                continue

            texture = region.texture.copy()

            local_x = attachment.x
            local_y = attachment.y
            world_x = bone.world_x + local_x * bone.a + local_y * bone.b
            world_y = bone.world_y + local_x * bone.c + local_y * bone.d

            px = center_x + (world_x + offset_x) * scale
            py = center_y + (world_y + offset_y) * scale

            if attachment.name not in used_attachments:
                print(f"[Bone] name={bone_name}, world=({bone.world_x:.2f}, {bone.world_y:.2f})")
                print(f"[Attachment] name={attachment.name}, region_center=({px:.2f}, {py:.2f}), bone={bone_name}")
                used_attachments.add(attachment.name)


            # 缩放
            bone_scale_x = math.sqrt(bone.a ** 2 + bone.c ** 2)
            bone_scale_y = math.sqrt(bone.b ** 2 + bone.d ** 2)
            raw_scale_x = bone_scale_x * attachment.scaleX * scale
            raw_scale_y = bone_scale_y * attachment.scaleY * scale
            scale_x = abs(raw_scale_x)
            scale_y = abs(raw_scale_y)

            if scale_x != 1 or scale_y != 1:
                new_w = max(1, int(texture.get_width() * scale_x))
                new_h = max(1, int(texture.get_height() * scale_y))
                try:
                    texture = pygame.transform.smoothscale(texture, (new_w, new_h))
                except ValueError:
                    continue

            if self.render_settings.flip_x or self.render_settings.flip_y:
                texture = pygame.transform.flip(texture, self.render_settings.flip_x, self.render_settings.flip_y)

            rotation = -math.degrees(math.atan2(bone.c, bone.a)) + attachment.rotation
            if rotation != 0:
                texture = pygame.transform.rotate(texture, rotation)

            # 忽略颜色
            tint_a = self.a * attachment.color.a
            if self.render_settings.use_premultiplied_alpha:
                texture.set_alpha(int(tint_a * 255))

            # 绘制到 Pygame surface
            blit_x = px - texture.get_width() // 2
            blit_y = py - texture.get_height() // 2
            surface.blit(texture, (blit_x, blit_y))

            pygame.draw.circle(surface, (255, 0, 0), (int(px), int(py)), 3)

    
    def draw_debug(self, surface: pygame.Surface):
        
        center_x = surface.get_width() // 2
        center_y = surface.get_height() // 2
        scale = self.render_settings.scale
        
        for bone in self.bones:
            wx = center_x + (bone.world_x + self.render_settings.position_x) * scale
            wy = center_y + (bone.world_y + self.render_settings.position_y) * scale
            
            pygame.draw.circle(surface, (255, 0, 0), (int(wx), int(wy)), 3)
            
            if bone.parent:
                parent_wx = center_x + (bone.parent.world_x + self.render_settings.position_x) * scale
                parent_wy = center_y + (bone.parent.world_y + self.render_settings.position_y) * scale
                pygame.draw.line(surface, (0, 255, 0),
                               (int(parent_wx), int(parent_wy)),
                               (int(wx), int(wy)), 1)
