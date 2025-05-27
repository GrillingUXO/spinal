import pygame
import math

class MathUtils:
    """实现类似 Spine 的数学工具类"""
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

class AttachmentSprite:
    def __init__(self, name, attachment, image):
        self.name = name
        self.attachment = attachment
        self.image = image
        self.rect = image.get_rect()
        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0
        self.bound_bone = None
        
    def update(self, screen, skeleton):
        if self.bound_bone:
            bone = self.bound_bone
            
            # 1. 如果有父骨骼，计算完整的变换矩阵
            if bone.parent:
                # 获取父骨骼的变换矩阵
                pa = bone.parent.a
                pb = bone.parent.b
                pc = bone.parent.c
                pd = bone.parent.d
                
                # 计算当前骨骼的局部变换矩阵
                rotation_y = bone.rotation + 90 + bone.shear_y
                la = MathUtils.cos_deg(bone.rotation + bone.shear_x) * bone.scale_x
                lb = MathUtils.cos_deg(rotation_y) * bone.scale_y
                lc = MathUtils.sin_deg(bone.rotation + bone.shear_x) * bone.scale_x
                ld = MathUtils.sin_deg(rotation_y) * bone.scale_y
                
                # 组合变换矩阵
                a = pa * la + pb * lc
                b = pa * lb + pb * ld
                c = pc * la + pd * lc
                d = pc * lb + pd * ld
                
                # 应用全局缩放
                a *= skeleton.scale_x
                b *= skeleton.scale_x
                c *= skeleton.scale_y
                d *= skeleton.scale_y
                
                # 计算世界坐标
                world_x = pa * bone.x + pb * bone.y + bone.parent.world_x
                world_y = pc * bone.x + pd * bone.y + bone.parent.world_y
                
            else:
                # 根骨骼的处理
                rotation_y = bone.rotation + 90 + bone.shear_y
                sx = skeleton.scale_x
                sy = skeleton.scale_y
                
                # 计算变换矩阵
                a = MathUtils.cos_deg(bone.rotation + bone.shear_x) * bone.scale_x * sx
                b = MathUtils.cos_deg(rotation_y) * bone.scale_y * sx
                c = MathUtils.sin_deg(bone.rotation + bone.shear_x) * bone.scale_x * sy
                d = MathUtils.sin_deg(rotation_y) * bone.scale_y * sy
                
                # 计算世界坐标
                world_x = bone.x * sx + skeleton.x
                world_y = bone.y * sy + skeleton.y
                
            # 2. 计算附件的最终变换
            attachment_rotation = bone.rotation + self.attachment.rotation
            attachment_scale_x = bone.world_scale_x * self.attachment.scale_x
            attachment_scale_y = bone.world_scale_y * self.attachment.scale_y
            
            # 3. 转换到 Pygame 坐标系 (原点在左上角，Y轴向下)
            screen_x = screen.get_width() // 2 + (world_x + skeleton.render_settings.position_x) * skeleton.render_settings.scale
            screen_y = screen.get_height() // 2 - (world_y + skeleton.render_settings.position_y) * skeleton.render_settings.scale
            
            # 4. 计算最终图片变换
            scaled_image = pygame.transform.scale(
                self.image,
                (
                    int(self.image.get_width() * abs(attachment_scale_x)),
                    int(self.image.get_height() * abs(attachment_scale_y))
                )
            )
            
            # 应用旋转，注意 Pygame 的旋转方向与 Spine 相反
            self.rotated_image = pygame.transform.rotate(scaled_image, -attachment_rotation)
            
            # 如果有缩放翻转，需要翻转图片
            if attachment_scale_x < 0 or attachment_scale_y < 0:
                self.rotated_image = pygame.transform.flip(
                    self.rotated_image,
                    attachment_scale_x < 0,
                    attachment_scale_y < 0
                )
            
            # 设置图片位置
            self.rotated_rect = self.rotated_image.get_rect(center=(screen_x, screen_y))

    def draw(self, surface, font):
        if hasattr(self, 'rotated_image') and hasattr(self, 'rotated_rect'):
            surface.blit(self.rotated_image, self.rotated_rect.topleft)
            label = font.render(self.name, True, (0, 0, 0))
            surface.blit(label, (self.rotated_rect.x, self.rotated_rect.y - 18))
            if self.bound_bone:
                bname = self.bound_bone.data.name
                label2 = font.render(f"→ {bname}", True, (100, 0, 0))
                surface.blit(label2, (self.rotated_rect.x, self.rotated_rect.y - 36))