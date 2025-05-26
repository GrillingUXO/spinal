import json
from skeleton_data import SkeletonData, BoneData, SlotData, Skin, RegionAttachment
from mytypes import Color, AttachmentType
from atlas import Atlas
from typing import Optional
from skeleton_data import SkeletonData, BoneData, SlotData, Skin, RegionAttachment, MeshAttachment
from skeleton_data import BoneData, SlotData, RegionAttachment, Attachment, Skin, SkeletonData, Animation, AnimationSlotTimeline



class SkeletonJson:
    """骨骼JSON加载器"""
    def __init__(self, atlas: Atlas):  # 接受Atlas实例
        self.atlas = atlas  # 保存图集引用
        self.scale = 1.0
        
    def read_skeleton_data(self, path: str) -> SkeletonData:
        """读取骨骼数据"""
        with open(path, 'r') as f:
            root = json.load(f)
        self.raw = root
            
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
            skins_root = root["skins"]

            if isinstance(skins_root, dict):
                # ✅ Spine 3.8+ 标准结构
                for skin_name, slots_dict in skins_root.items():
                    skin = Skin(skin_name)
                    for slot_name, attachments in slots_dict.items():
                        slot_index = next(
                            (i for i, s in enumerate(skeleton_data.slots) if s.name == slot_name),
                            -1
                        )
                        if slot_index == -1:
                            print(f"[WARNING] Slot not found: {slot_name}")
                            continue

                        for attachment_name, attachment_map in attachments.items():
                            attachment = self._read_attachment(attachment_map, attachment_name)
                            if attachment:
                                skin.attachments[(slot_index, attachment_name)] = attachment

                    skeleton_data.skins.append(skin)
                    if skin_name == "default":
                        skeleton_data.default_skin = skin

            elif isinstance(skins_root, list):
                # ✅ Spine 导出为列表结构
                for skin_obj in skins_root:
                    skin_name = skin_obj.get("name", "default")
                    attachments_dict = skin_obj.get("attachments", {})

                    skin = Skin(skin_name)
                    for slot_name, attachments in attachments_dict.items():
                        slot_index = next(
                            (i for i, s in enumerate(skeleton_data.slots) if s.name == slot_name),
                            -1
                        )
                        if slot_index == -1:
                            print(f"[WARNING] Slot not found: {slot_name}")
                            continue

                        for attachment_name, attachment_map in attachments.items():
                            attachment = self._read_attachment(attachment_map, attachment_name)
                            if attachment:
                                skin.attachments[(slot_index, attachment_name)] = attachment

                    skeleton_data.skins.append(skin)
                    if skin_name == "default":
                        skeleton_data.default_skin = skin

        # 读取动画
        if "animations" in root:
            for anim_name, anim_map in root["animations"].items():
                animation = Animation(name=anim_name, duration=0)
                slot_timelines = []

                slots = anim_map.get("slots", {})
                for slot_name, timelines in slots.items():
                    slot_timeline = AnimationSlotTimeline(slot_name=slot_name, timelines=[])
                    for timeline_name, keyframes in timelines.items():
                        if timeline_name == "attachment":
                            for frame in keyframes:
                                frame_name = frame.get("name")
                                if frame_name:
                                    slot_timeline.timelines.append({
                                        "time": frame["time"],
                                        "name": frame_name
                                    })
                    if slot_timeline.timelines:
                        slot_timelines.append(slot_timeline)

                animation.slot_timelines = slot_timelines
                skeleton_data.animations.append(animation)



        return skeleton_data
    
    def _read_attachment(self, attachment_map: dict, name: str) -> Optional[Attachment]:
        type_name = attachment_map.get("type", "region")
        attachment_type = AttachmentType[type_name.title()]

        path = attachment_map.get("path", name)

        if attachment_type == AttachmentType.Region:
            region = self.atlas.find_region(path)
            if not region:
                print(f"[WARNING] Region not found for: {path}")
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
            return attachment

        elif attachment_type == AttachmentType.Mesh:
            region = self.atlas.find_region(path)
            if not region:
                print(f"[WARNING] Region not found for mesh: {path}")
                return None

            mesh = MeshAttachment(
                name=name,
                type=attachment_type,
                path=path,
                color=Color(),
                uvs=[u * self.scale for u in attachment_map.get("uvs", [])],
                vertices=[v * self.scale for v in attachment_map.get("vertices", [])],
                triangles=attachment_map.get("triangles", []),
                region=region
            )

            if "color" in attachment_map:
                color = attachment_map["color"]
                if len(color) == 8:
                    mesh.color = Color(
                        int(color[0:2], 16) / 255.0,
                        int(color[2:4], 16) / 255.0,
                        int(color[4:6], 16) / 255.0,
                        int(color[6:8], 16) / 255.0
                    )

            return mesh
        

        print(f"[SKIP] Unsupported attachment type: {attachment_type.name} (name: {name})")
        return None




