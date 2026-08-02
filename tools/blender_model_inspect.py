import bpy
import json
import math
import os
import sys
from mathutils import Vector


def args_after_double_dash():
    if "--" not in sys.argv:
        raise SystemExit("usage: blender --background --python script.py -- INPUT OUT_DIR LABEL")
    return sys.argv[sys.argv.index("--") + 1 :]


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def world_bounds(objects):
    points = []
    for obj in objects:
        if obj.type == "MESH":
            points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    return (
        Vector(tuple(min(p[i] for p in points) for i in range(3))),
        Vector(tuple(max(p[i] for p in points) for i in range(3))),
    )


def vec(v):
    return [round(float(x), 6) for x in v]


def mesh_record(obj):
    lo, hi = world_bounds([obj])
    material_names = [slot.material.name if slot.material else None for slot in obj.material_slots]
    modifiers = []
    for mod in obj.modifiers:
        record = {"name": mod.name, "type": mod.type}
        if mod.type == "ARMATURE" and mod.object:
            record["object"] = mod.object.name
        modifiers.append(record)
    groups = []
    for group in obj.vertex_groups:
        groups.append({"index": group.index, "name": group.name})
    return {
        "name": obj.name,
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "polygons": len(obj.data.polygons),
        "materials": material_names,
        "vertex_groups": groups,
        "modifiers": modifiers,
        "location": vec(obj.location),
        "rotation_euler": vec(obj.rotation_euler),
        "scale": vec(obj.scale),
        "world_bounds": {"min": vec(lo), "max": vec(hi), "size": vec(hi - lo)},
    }


def armature_record(obj):
    bones = []
    for bone in obj.data.bones:
        bones.append(
            {
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else None,
                "head_local": vec(bone.head_local),
                "tail_local": vec(bone.tail_local),
            }
        )
    return {
        "name": obj.name,
        "location": vec(obj.location),
        "rotation_euler": vec(obj.rotation_euler),
        "scale": vec(obj.scale),
        "bones": bones,
    }


def image_record(image):
    return {
        "name": image.name,
        "size": list(image.size),
        "source": image.source,
        "filepath": image.filepath,
        "packed": bool(image.packed_file),
    }


def material_record(material):
    textures = []
    if material.use_nodes and material.node_tree:
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                textures.append(node.image.name)
    return {
        "name": material.name,
        "blend_method": getattr(material, "surface_render_method", None),
        "textures": textures,
    }


def add_camera_and_lights(center, size, angle_degrees):
    radius = max(size.length, 0.1)
    angle = math.radians(angle_degrees)
    direction = Vector((math.sin(angle), -math.cos(angle), 0.15)).normalized()
    cam_pos = center + direction * radius * 1.75
    bpy.ops.object.camera_add(location=cam_pos)
    camera = bpy.context.object
    camera.name = "InspectionCamera"
    camera.data.lens = 62
    camera.data.sensor_width = 36
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(size.x, size.y, size.z) * 1.2
    camera.rotation_euler = (center - cam_pos).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera

    for name, pos, energy, scale in (
        ("Key", center + Vector((-radius, -radius, radius)), 1300, 5.0),
        ("Fill", center + Vector((radius, -radius * 0.2, radius * 0.4)), 800, 4.0),
        ("Rim", center + Vector((0, radius, radius)), 1000, 3.0),
    ):
        bpy.ops.object.light_add(type="AREA", location=pos)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = scale
        light.rotation_euler = (center - pos).to_track_quat("-Z", "Y").to_euler()


def render_preview(filepath, center, size, angle_degrees):
    scene = bpy.context.scene
    for obj in list(scene.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    add_camera_and_lights(center, size, angle_degrees)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.045, 0.045, 0.045)
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)


def main():
    argv = args_after_double_dash()
    if len(argv) != 3:
        raise SystemExit("expected INPUT OUT_DIR LABEL")
    input_path, out_dir, label = argv
    input_path = os.path.abspath(input_path)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    reset_scene()
    bpy.ops.import_scene.gltf(filepath=input_path)

    imported = [obj for obj in bpy.context.scene.objects if obj.type not in {"CAMERA", "LIGHT"}]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    lo, hi = world_bounds(meshes)
    center = (lo + hi) / 2
    size = hi - lo
    stats = {
        "input": os.path.abspath(input_path),
        "scene_bounds": {"min": vec(lo), "max": vec(hi), "center": vec(center), "size": vec(size)},
        "objects": [{"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None} for o in imported],
        "meshes": [mesh_record(o) for o in meshes],
        "armatures": [armature_record(o) for o in armatures],
        "materials": [material_record(m) for m in bpy.data.materials],
        "images": [image_record(i) for i in bpy.data.images],
    }
    with open(os.path.join(out_dir, f"{label}_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    for angle, suffix in ((0, "front"), (90, "side"), (180, "back")):
        render_preview(os.path.join(out_dir, f"{label}_{suffix}.png"), center, size, angle)


if __name__ == "__main__":
    main()
