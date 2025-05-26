import pygame
import math

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
            angle = -math.degrees(math.atan2(bone.c, bone.a)) + self.attachment.rotation
            rotated = pygame.transform.rotate(self.image, angle)
            self.rotated_image = rotated
            self.rotated_rect = rotated.get_rect(center=(
                screen.get_width() // 2 + (bone.world_x + skeleton.render_settings.position_x) * skeleton.render_settings.scale,
                screen.get_height() // 2 + (bone.world_y + skeleton.render_settings.position_y) * skeleton.render_settings.scale
            ))
        elif self.dragging:
            self.rotated_image = self.image
            self.rotated_rect = self.rect
        else:
            self.rotated_image = self.image
            self.rotated_rect = self.rect

    def draw(self, surface, font):
        surface.blit(self.rotated_image, self.rotated_rect.topleft)
        label = font.render(self.name, True, (0, 0, 0))
        surface.blit(label, (self.rotated_rect.x, self.rotated_rect.y - 18))
        if self.bound_bone:
            bname = self.bound_bone.data.name
            label2 = font.render(f"→ {bname}", True, (100, 0, 0))
            surface.blit(label2, (self.rotated_rect.x, self.rotated_rect.y - 36))
