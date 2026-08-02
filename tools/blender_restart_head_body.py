import bpy
from pathlib import Path


ROOT = Path(r"C:\workspace\shimolinchi.github.io")
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "output" / "head_swap"


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)


def import_glb(path: Path, object_name: str):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"No mesh imported from {path}")

    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    result = bpy.context.view_layer.objects.active
    result.name = object_name
    result.data.name = f"{object_name}_Mesh"
    return result


clear_scene()
body = import_glb(ASSETS / "seated-office-person.glb", "Body_Full")
head = import_glb(ASSETS / "detailed-human-head.glb", "Head_Detailed")

# Keep the two sources separate so the user can align and cut them before joining.
body["source_asset"] = "seated-office-person.glb"
head["source_asset"] = "detailed-human-head.glb"

bpy.ops.object.select_all(action="DESELECT")
head.select_set(True)
bpy.context.view_layer.objects.active = head

OUTPUT.mkdir(parents=True, exist_ok=True)
out_path = OUTPUT / "head_body_restart.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(out_path))
print(f"SAVED={out_path}")
print(f"BODY_MATERIALS={len(body.data.materials)}")
print(f"HEAD_MATERIALS={len(head.data.materials)}")
