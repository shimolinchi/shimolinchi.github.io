import bpy
from mathutils import Vector
from pathlib import Path


ROOT = Path(r"C:\workspace\shimolinchi.github.io")
ASSET = ROOT / "public" / "models" / "tool-cabinet.glb"
OUTPUT = ROOT / "work" / "tool_cabinet_fixed_preview"
OUTPUT.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ASSET))
obj = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")

world = bpy.context.scene.world
world.color = (0.06, 0.06, 0.06)

bpy.ops.object.light_add(type="AREA", location=(2, -2, 3))
bpy.context.object.data.energy = 900
bpy.context.object.data.shape = "DISK"
bpy.context.object.data.size = 4

bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = 1.25
bpy.context.scene.camera = camera

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 700
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

center = Vector((0, 0, 0.5))
views = {
    "front_pos_y": Vector((0, 3, 0.5)),
    "back_neg_y": Vector((0, -3, 0.5)),
    "side_pos_x": Vector((3, 0, 0.5)),
}

for name, location in views.items():
    camera.location = location
    camera.rotation_euler = (center - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUTPUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(scene.render.filepath)
