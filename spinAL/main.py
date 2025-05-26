import pygame
from runtime import Skeleton, AttachmentType, Slot
from atlas import Atlas
from loader import SkeletonJson

from render import AttachmentSprite

from operation import print_all_animation_bones, update_sprites_for_animation

pygame.init()
screen = pygame.display.set_mode((1280, 720))
pygame.display.set_caption("Spine")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 16)
edit_mode = True

atlas = Atlas(".atlas")
json_loader = SkeletonJson(atlas)
skeleton_data = json_loader.read_skeleton_data(".json")
skeleton = Skeleton(skeleton_data)

print_all_animation_bones(json_loader)

current_animation_index = 0
animation_names = [a.name for a in skeleton_data.animations]

sprites = []
update_sprites_for_animation(animation_names[current_animation_index], skeleton_data, skeleton, json_loader, sprites, AttachmentSprite)

scroll_offset = 0
dragging_background = False
bg_drag_start = (0, 0)
view_drag_start = (0, 0)

running = True
while running:
    screen_width, screen_height = screen.get_size()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                edit_mode = not edit_mode
            elif event.key == pygame.K_TAB:
                current_animation_index = (current_animation_index + 1) % len(animation_names)
                update_sprites_for_animation(animation_names[current_animation_index], skeleton_data, skeleton, json_loader, sprites, AttachmentSprite)
            elif event.key == pygame.K_ESCAPE:
                pass
                # for sprite in sprites:
                #     if sprite.dragging:
                #         sprite.dragging = False
                #         sprite.bound_bone = None
            elif event.key == pygame.K_q:
                skeleton.render_settings.scale *= 1.1
            elif event.key == pygame.K_a:
                skeleton.render_settings.scale /= 1.1

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                pass
                # for sprite in reversed(sprites):
                #     if sprite.rect.collidepoint(event.pos):
                #         sprite.dragging = True
                #         mouse_x, mouse_y = event.pos
                #         sprite.offset_x = sprite.rect.x - mouse_x
                #         sprite.offset_y = sprite.rect.y - mouse_y
                #         break
            elif event.button == 2:
                dragging_background = True
                bg_drag_start = event.pos
                view_drag_start = (skeleton.render_settings.position_x, skeleton.render_settings.position_y)
            elif event.button == 4:
                scroll_offset = min(scroll_offset + 20, 0)
            elif event.button == 5:
                scroll_offset -= 20

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                pass
                # for sprite in sprites:
                #     if sprite.dragging:
                #         sprite.dragging = False
                #         mx, my = sprite.rect.center
                #         min_dist = 9999
                #         closest_bone = None
                #         for bone in skeleton.bones:
                #             wx = screen_width // 2 + (bone.world_x + skeleton.render_settings.position_x) * skeleton.render_settings.scale
                #             wy = screen_height // 2 + (bone.world_y + skeleton.render_settings.position_y) * skeleton.render_settings.scale
                #             dist = ((mx - wx) ** 2 + (my - wy) ** 2) ** 0.5
                #             if dist < 50 and dist < min_dist:
                #                 min_dist = dist
                #                 closest_bone = bone
                #         if closest_bone:
                #             sprite.bound_bone = closest_bone
            elif event.button == 2:
                dragging_background = False

        elif event.type == pygame.MOUSEMOTION:
            if dragging_background:
                dx = event.pos[0] - bg_drag_start[0]
                dy = event.pos[1] - bg_drag_start[1]
                skeleton.render_settings.position_x = view_drag_start[0] + dx
                skeleton.render_settings.position_y = view_drag_start[1] + dy
            # for sprite in sprites:
            #     if sprite.dragging:
            #         mouse_x, mouse_y = event.pos
            #         sprite.rect.x = mouse_x + sprite.offset_x
            #         sprite.rect.y = mouse_y + sprite.offset_y


    screen.fill((245, 245, 255))
    skeleton.update_world_transform()

    for i, sprite in enumerate(sprites):
        if not sprite.dragging and not sprite.bound_bone:
            sprite.rect.x = screen_width - 150
            sprite.rect.y = 100 + i * 100 + scroll_offset
        sprite.update(screen, skeleton)

    for slot in skeleton.slots:
        if slot.attachment:
            bone = slot.bone
            cx = screen_width // 2 + (bone.world_x + skeleton.render_settings.position_x) * skeleton.render_settings.scale
            cy = screen_height // 2 + (bone.world_y + skeleton.render_settings.position_y) * skeleton.render_settings.scale
            pygame.draw.circle(screen, (255, 0, 0), (int(cx), int(cy)), 4)
            label = font.render(bone.data.name, True, (0, 0, 255))
            screen.blit(label, (cx + 6, cy - 6))

    for sprite in sprites:
        sprite.draw(screen, font)

    mode_label = font.render("Tab，Space，ESC", True, (0, 0, 0))
    screen.blit(mode_label, (10, 10))

    anim_label = font.render(f"current: {animation_names[current_animation_index]}", True, (0, 0, 0))
    screen.blit(anim_label, (10, 40))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
