import json
from skeleton_data import (
    SkeletonData, 
    BoneData, 
    SlotData, 
    Skin, 
    RegionAttachment, 
    MeshAttachment,
    Attachment,
    Animation,  # 添加 Animation 导入
    AnimationSlotTimeline
)
from mytypes import Color, AttachmentType
from atlas import Atlas
from typing import Optional, Dict, List, Tuple

class SkeletonJson:
    """骨骼JSON加载器，基于SpineViewer重新实现"""
    
    def __init__(self, atlas: Atlas):
        self.atlas = atlas
        self.scale = 1.0
        self.raw = None 
        self.string_table: List[str] = []
        
    def read_skeleton_data(self, path: str) -> SkeletonData:
        """读取骨骼数据"""
        with open(path, 'r', encoding='utf-8') as f:
            self.raw = json.load(f)  # 保存原始 JSON 数据
            
        skeleton_data = SkeletonData()
        
        # 读取基本信息
        if "skeleton" in self.raw:
            skeleton = self.raw["skeleton"]
            skeleton_data.hash = skeleton.get("hash")
            skeleton_data.version = skeleton.get("spine")
            skeleton_data.width = skeleton.get("width", 0) * self.scale 
            skeleton_data.height = skeleton.get("height", 0) * self.scale
            skeleton_data.images_path = skeleton.get("images")
            skeleton_data.fps = skeleton.get("fps", 30)

        # 读取骨骼
        if "bones" in self.raw:
            self._read_bones(self.raw["bones"], skeleton_data)
            
        # 读取插槽
        if "slots" in self.raw:
            self._read_slots(self.raw["slots"], skeleton_data)
            
        # 读取皮肤
        if "skins" in self.raw:
            self._read_skins(self.raw["skins"], skeleton_data)
            
        # 读取动画
        if "animations" in self.raw:
            self._read_animations(self.raw["animations"], skeleton_data)
            
        return skeleton_data
    
        
    def _read_bones(self, bones_data: List[dict], skeleton_data: SkeletonData):
        """解析骨骼数据"""
        for bone_map in bones_data:
            parent = None
            if "parent" in bone_map:
                parent_name = bone_map["parent"]
                parent = next(
                    (b for b in skeleton_data.bones if b.name == parent_name),
                    None
                )
                
            # 1. 读取局部坐标
            local_x = bone_map.get("x", 0) * self.scale
            local_y = bone_map.get("y", 0) * self.scale
            
            # 2. 注意：这里不需要立即翻转Y轴，因为是局部坐标
            # Spine的坐标系统会在渲染时处理
            bone = BoneData(
                name=bone_map["name"],
                parent=parent,
                length=bone_map.get("length", 0) * self.scale,
                x=local_x,  # 使用局部坐标
                y=local_y,  # 使用局部坐标
                rotation=bone_map.get("rotation", 0),  # 局部旋转角度
                scaleX=bone_map.get("scaleX", 1),
                scaleY=bone_map.get("scaleY", 1),
                shearX=bone_map.get("shearX", 0),
                shearY=bone_map.get("shearY", 0)
            )
            
            skeleton_data.bones.append(bone)
            
    def _read_slots(self, slots_data: List[dict], skeleton_data: SkeletonData):
        """解析插槽数据"""
        if not slots_data:
            return
            
        for slot_map in slots_data:
            # 获取插槽对应的骨骼
            bone_name = slot_map["bone"]
            bone_data = next(
                (b for b in skeleton_data.bones if b.name == bone_name),
                None
            )
            
            if bone_data is None:
                print(f"[WARNING] Bone not found for slot: {slot_map['name']}")
                continue
                
            # 创建插槽数据
            slot_data = SlotData(
                name=slot_map["name"],
                bone_data=bone_data,
                attachment_name=slot_map.get("attachment")
            )
            
            # 处理插槽颜色
            if "color" in slot_map:
                color_str = slot_map["color"]
                if len(color_str) == 8:  # RGBA格式 (例如: "FFFFFFFF")
                    slot_data.color = Color(
                        int(color_str[0:2], 16) / 255.0,  # R
                        int(color_str[2:4], 16) / 255.0,  # G
                        int(color_str[4:6], 16) / 255.0,  # B
                        int(color_str[6:8], 16) / 255.0   # A
                    )
                    
            # 处理混合模式
            if "blend" in slot_map:
                slot_data.blend_mode = slot_map["blend"]
                
            # 添加到骨骼数据中
            skeleton_data.slots.append(slot_data)

    def _read_bones(self, bones_data: List[dict], skeleton_data: SkeletonData):
        """解析骨骼数据"""
        for bone_map in bones_data:
            parent = None
            if "parent" in bone_map:
                parent_name = bone_map["parent"]
                parent = next(
                    (b for b in skeleton_data.bones if b.name == parent_name),
                    None
                )
                
            # 保持原始坐标系统
            x = bone_map.get("x", 0) * self.scale
            y = bone_map.get("y", 0) * self.scale
            rotation = bone_map.get("rotation", 0)
            
            bone = BoneData(
                name=bone_map["name"],
                parent=parent,
                length=bone_map.get("length", 0) * self.scale,
                x=x,
                y=y,
                rotation=rotation,
                scaleX=bone_map.get("scaleX", 1),
                scaleY=bone_map.get("scaleY", 1),
                shearX=bone_map.get("shearX", 0),
                shearY=bone_map.get("shearY", 0)
            )
            skeleton_data.bones.append(bone)
            
        # 更新所有骨骼的世界变换
        for bone in skeleton_data.bones:
            bone.update_world_transform()
            
    def _read_skins(self, skins_data: Dict, skeleton_data: SkeletonData):
        """解析皮肤数据"""
        # 支持spine 3.8+的新格式和旧格式
        if isinstance(skins_data, dict):
            for skin_name, slots in skins_data.items():
                skin = self._create_skin(skin_name, slots, skeleton_data)
                skeleton_data.skins.append(skin)
                if skin_name == "default":
                    skeleton_data.default_skin = skin
        else:
            for skin_obj in skins_data:
                skin_name = skin_obj.get("name", "default") 
                slots = skin_obj.get("attachments", {})
                skin = self._create_skin(skin_name, slots, skeleton_data)
                skeleton_data.skins.append(skin)
                if skin_name == "default":
                    skeleton_data.default_skin = skin
                    
    def _create_skin(self, name: str, slots_data: Dict, skeleton_data: SkeletonData) -> Skin:
        """创建皮肤对象"""
        skin = Skin(name)
        for slot_name, attachments in slots_data.items():
            slot_index = self._find_slot_index(slot_name, skeleton_data.slots)
            if slot_index == -1:
                print(f"[WARNING] Slot not found: {slot_name}")
                continue
                
            for attachment_name, attachment_map in attachments.items():
                attachment = self._read_attachment(attachment_map, attachment_name)
                if attachment:
                    skin.attachments[(slot_index, attachment_name)] = attachment
                    
        return skin
        

    def _read_attachment(self, attachment_map: dict, name: str) -> Optional[Attachment]:
        """解析附件数据"""
        type_name = attachment_map.get("type", "region")
        attachment_type = AttachmentType[type_name.title()]
        path = attachment_map.get("path", name)
        
        if attachment_type == AttachmentType.Region:
            # RegionAttachment 部分保持不变...
            pass
            
        elif attachment_type == AttachmentType.Mesh:
            region = self.atlas.find_region(path)
            if not region:
                print(f"[WARNING] Region not found for mesh: {path}")
                return None
                
            # 处理顶点数据
            vertices = []
            raw_vertices = attachment_map.get("vertices", [])
            
            # 检查是否有权重数据
            if attachment_map.get("weights") and attachment_map.get("bones"):
                # 处理带权重的顶点
                weights = attachment_map["weights"]
                bones = attachment_map["bones"]
                vertex_count = len(weights) // 3  # 每个顶点有3个值：骨骼索引、权重x、权重y
                
                vertices = []
                i = 0
                while i < len(weights):
                    bone_count = bones[i]
                    i += 1
                    for j in range(bone_count):
                        bone_index = bones[i]
                        x = weights[i + 1] * self.scale
                        y = -weights[i + 2] * self.scale  # Y轴翻转
                        vertices.extend([x, y])
                        i += 3
            else:
                # 处理普通顶点
                for i in range(0, len(raw_vertices), 2):
                    if i + 1 < len(raw_vertices):
                        x = raw_vertices[i] * self.scale
                        y = -raw_vertices[i + 1] * self.scale  # Y轴翻转
                        vertices.extend([x, y])
            
            # 处理UV坐标
            uvs = attachment_map.get("uvs", [])
            if len(uvs) % 2 != 0:
                print(f"[WARNING] UVs array has odd length for mesh: {name}")
                uvs = []
                
            # 处理三角形索引
            triangles = attachment_map.get("triangles", [])
            
            mesh = MeshAttachment(
                name=name,
                type=attachment_type,
                path=path,
                color=Color(),
                uvs=uvs,
                vertices=vertices,
                triangles=triangles,
                region=region
            )
            
            if "color" in attachment_map:
                mesh.color = self._parse_color(attachment_map["color"])
                
            # 如果有hull数据，添加到mesh
            if "hull" in attachment_map:
                mesh.hull = attachment_map["hull"]
                
            # 如果有edges数据，添加到mesh
            if "edges" in attachment_map:
                mesh.edges = attachment_map["edges"]
                
            return mesh
            
        print(f"[SKIP] Unsupported attachment type: {attachment_type.name} (name: {name})")
        return None
    
        
    def _read_animations(self, animations_data: Dict, skeleton_data: SkeletonData):
        """解析动画数据"""
        for anim_name, anim_map in animations_data.items():
            # 计算动画持续时间
            duration = 0
            
            # 从时间轴中找出最长的持续时间
            if "slots" in anim_map:
                for slot_data in anim_map["slots"].values():
                    for timeline in slot_data.values():
                        if isinstance(timeline, list) and timeline:
                            last_frame = timeline[-1]
                            if isinstance(last_frame, dict) and "time" in last_frame:
                                duration = max(duration, last_frame["time"])
            
            animation = Animation(name=anim_name, duration=duration)
            slot_timelines = []
            
            slots = anim_map.get("slots", {})
            for slot_name, timelines in slots.items():
                slot_timeline = AnimationSlotTimeline(slot_name=slot_name, timelines=[])
                
                if "attachment" in timelines:
                    for frame in timelines["attachment"]:
                        if "name" in frame:
                            slot_timeline.timelines.append({
                                "time": frame["time"],
                                "name": frame["name"]
                            })
                            
                if slot_timeline.timelines:
                    slot_timelines.append(slot_timeline)
                    
            animation.slot_timelines = slot_timelines
            skeleton_data.animations.append(animation)
            
    @staticmethod
    def _parse_color(color_str: str) -> Color:
        """解析颜色值"""
        if len(color_str) == 8:
            return Color(
                int(color_str[0:2], 16) / 255.0,
                int(color_str[2:4], 16) / 255.0,
                int(color_str[4:6], 16) / 255.0,
                int(color_str[6:8], 16) / 255.0
            )
        return Color()
        
    @staticmethod
    def _find_bone(name: str, bones: List[BoneData]) -> Optional[BoneData]:
        """查找骨骼"""
        return next((b for b in bones if b.name == name), None)
        
    @staticmethod
    def _find_slot_index(name: str, slots: List[SlotData]) -> int:
        """查找插槽索引"""
        return next((i for i, s in enumerate(slots) if s.name == name), -1)