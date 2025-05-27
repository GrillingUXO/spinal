def print_all_animation_bones(json_loader):
    print("\n========= bones =========")
    root = json_loader.raw
    for anim_name, anim_data in root.get("animations", {}).items():
        bone_names = set(anim_data.get("bones", {}).keys())
        print(f"动画: {anim_name}")
        for name in sorted(bone_names):
            print(f"  - {name}")
    print("====================================\n")

def get_attachment_names_for_animation(animation):
    names = set()
    for slot_timeline in animation.slot_timelines:
        for keyframe in slot_timeline.timelines:
            if keyframe["name"]:
                names.add(keyframe["name"])
    return names

def get_slot_names_for_animation(animation):
    return set(slot_timeline.slot_name for slot_timeline in animation.slot_timelines)

def update_sprites_for_animation(animation_name, skeleton_data, skeleton, json_loader, sprites, AttachmentSprite):

    # for sprite in sprites:
    #     sprite.bound_bone = None  
    sprites.clear()

    animation = next((a for a in skeleton_data.animations if a.name == animation_name), None)
    if not animation:
        print(f"no animation: {animation_name}")
        return

    used_attachment_names = get_attachment_names_for_animation(animation)
    used_slot_names = get_slot_names_for_animation(animation)
    skeleton.slots = [slot for slot in skeleton.slots if slot.data.name in used_slot_names]

    if skeleton.skin:
        for (slot_index, name), attachment in skeleton.skin.attachments.items():
            slot_data = skeleton_data.slots[slot_index]
            if (name in used_attachment_names and
                slot_data.name in used_slot_names and
                attachment.type == attachment.type.Region and
                attachment.region and attachment.region.texture):
                sprite = AttachmentSprite(name, attachment, attachment.region.texture.copy())

                # sprite.dragging = False  
                # sprite.bound_bone = None  

                sprites.append(sprite)

    used_bone_names = set()
    root = json_loader.raw
    anim_raw = root.get("animations", {}).get(animation_name, {})
    for bone_name in anim_raw.get("bones", {}).keys():
        used_bone_names.add(bone_name)

    def include_parents(name, bones_map, included):
        while name:
            if name in included:
                break
            included.add(name)
            parent = bones_map.get(name).parent.name if bones_map.get(name).parent else None
            name = parent

    bone_data_map = {b.name: b for b in skeleton_data.bones}
    for name in list(used_bone_names):
        include_parents(name, bone_data_map, used_bone_names)

    skeleton.reset_bones_from_names(used_bone_names)
    skeleton.update_world_transform()
