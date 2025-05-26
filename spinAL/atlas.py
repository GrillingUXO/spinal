import os
import pygame
from dataclasses import dataclass
from typing import Dict, Optional


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


class Atlas:
    def __init__(self, file_path: str):
        self.regions: Dict[str, TextureRegion] = {}
        self.load(file_path)

    def load(self, atlas_path: str):
        atlas_dir = os.path.dirname(atlas_path)
        
        with open(atlas_path, 'r') as f:
            lines = [line.rstrip('\n') for line in f.readlines()] 
        
        i = 0
        current_page = None
        texture = None 
        
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
                
                # 跳过纹理页属性
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if not line:
                        break
                    if ':' not in line:  
                        break
                    i += 1
                continue
            
            # 处理区域定义
            region = TextureRegion()
            region.name = line
            i += 1  # 移动到属性行
            
            while i < len(lines):
                line = lines[i].strip()
                if not line: 
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
                    pass  # 原始尺寸不处理
                elif key == 'offset':
                    values = list(map(float, value.split(',')))
                    region.offset = values
                elif key == 'index':
                    pass  # 索引不处理
                
                i += 1
            
            # 计算UV坐标
            if texture:
                tex_width = texture.get_width()
                tex_height = texture.get_height()

                region.u = region.x / tex_width
                region.v = region.y / tex_height

                if region.rotate:
                    region.u2 = (region.x + region.height) / tex_width
                    region.v2 = (region.y + region.width) / tex_height
                    sub_rect = (region.x, region.y, region.height, region.width)
                else:
                    region.u2 = (region.x + region.width) / tex_width
                    region.v2 = (region.y + region.height) / tex_height
                    sub_rect = (region.x, region.y, region.width, region.height)

                # extract surface and rotate if needed
                try:
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

