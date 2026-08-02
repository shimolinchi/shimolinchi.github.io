import bpy
from mathutils import Vector
from pathlib import Path


ROOT = Path(r"C:\workspace\shimolinchi.github.io")
OUTPUT = ROOT / "public" / "models" / "tool-cabinet.glb"

if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")

meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not meshes:
    raise RuntimeError("No mesh objects found in the tool cabinet blend")

bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]

points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
mins = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
maxs = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(OUTPUT),
    export_format="GLB",
    use_selection=True,
    export_materials="EXPORT",
    export_image_format="JPEG",
    export_jpeg_quality=85,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
)

print(f"OUTPUT={OUTPUT}")
print(f"MESH_COUNT={len(meshes)}")
print(f"BOUNDS_MIN={tuple(round(v, 6) for v in mins)}")
print(f"BOUNDS_MAX={tuple(round(v, 6) for v in maxs)}")
print(f"SIZE={tuple(round(v, 6) for v in maxs - mins)}")
