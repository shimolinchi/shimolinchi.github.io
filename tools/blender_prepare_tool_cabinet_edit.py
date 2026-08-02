import bpy
from pathlib import Path


ROOT = Path(r"C:\workspace\shimolinchi.github.io")
SOURCE = ROOT / "assets" / "workbench-tool-cabinet.glb"
OUTPUT = ROOT / "output" / "tool_cabinet" / "tool_cabinet_edit.blend"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))

mesh = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
mesh.name = "Tool_Cabinet_Edit"
mesh.data.name = "Tool_Cabinet_Edit_Mesh"
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
print(f"SAVED={OUTPUT}")
