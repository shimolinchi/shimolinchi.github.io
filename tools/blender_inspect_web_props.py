import bpy
from mathutils import Vector
from pathlib import Path


ASSETS = Path(r"C:\workspace\shimolinchi.github.io\assets")
FILES = [
    "computer-monitor.glb",
    "notebook.glb",
    "wooden-desk.glb",
    "wireless-mouse-white.glb",
    "monitor-white-legacy.glb",
    "mechanical-keyboard-white.glb",
]

for filename in FILES:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(ASSETS / filename))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    mins = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maxs = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    print(
        "PROP",
        filename,
        "meshes=", len(meshes),
        "materials=", sum(len(obj.data.materials) for obj in meshes),
        "min=", tuple(round(v, 6) for v in mins),
        "max=", tuple(round(v, 6) for v in maxs),
        "size=", tuple(round(v, 6) for v in maxs - mins),
    )
