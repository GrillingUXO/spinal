import pygame
from atlas import Atlas
from loader import SkeletonJson
from runtime import Skeleton
from mytypes import SpineRenderSettings


# 初始化pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# 加载资源
atlas = Atlas("/Users/michelleyan/Downloads/skel/xianghe.atlas") 
json_loader = SkeletonJson(atlas)
skeleton_data = json_loader.read_skeleton_data("/Users/michelleyan/Downloads/skel/xianghe.json")
skeleton = Skeleton(skeleton_data)

# 主循环
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                skeleton.render_settings.position_x -= 10
            elif event.key == pygame.K_RIGHT:
                skeleton.render_settings.position_x += 10
            elif event.key == pygame.K_UP:
                skeleton.render_settings.position_y -= 10
            elif event.key == pygame.K_DOWN:
                skeleton.render_settings.position_y += 10
            elif event.key == pygame.K_q:
                skeleton.render_settings.scale += 0.1
            elif event.key == pygame.K_a:
                skeleton.render_settings.scale = max(0.1, skeleton.render_settings.scale - 0.1)
            elif event.key == pygame.K_x:
                skeleton.render_settings.flip_x = not skeleton.render_settings.flip_x
            elif event.key == pygame.K_y:
                skeleton.render_settings.flip_y = not skeleton.render_settings.flip_y
            elif event.key == pygame.K_r:
                skeleton.render_settings = SpineRenderSettings()

    screen.fill((255, 255, 255))
    skeleton.draw(screen)
    skeleton.draw_debug(screen)
    pygame.display.flip()
    clock.tick(60)
