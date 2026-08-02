import bpy
import os
import sys
from mathutils import Vector

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
from blender_head_swap import render

out_dir = os.path.join(os.path.dirname(bpy.data.filepath), "Untitled_repaired_preview")
os.makedirs(out_dir, exist_ok=True)
if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
center = Vector((0.0, 0.035, 0.63))
for angle, name in ((0, "front"), (45, "three_quarter"), (90, "side"), (135, "rear_quarter"), (180, "back")):
    render(os.path.join(out_dir, f"neck_{name}.png"), center, 0.26, angle, 900)
print("CODEX_PREVIEW_DIR", out_dir)
