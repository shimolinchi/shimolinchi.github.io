import bpy
import os
import sys
from mathutils import Vector


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import render
from blender_pitch_cleanup_probe import delete_old_head_residue, pitch_head


CUTS = (0.24, 0.27, 0.30, 0.33)


def delete_head_below(head, cut):
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for vertex in head.data.vertices:
        vertex.select = vertex.co.z < cut
    head.data.update()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    head.select_set(False)
    head.data.update()


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 2:
        raise SystemExit("expected CLEAN_BLEND OUTPUT_DIR")
    clean_blend, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    center = Vector((-0.005, 0.03, 0.855))
    for cut in CUTS:
        bpy.ops.wm.open_mainfile(filepath=clean_blend)
        body = bpy.data.objects["BodyAndChair_Cut"]
        head = bpy.data.objects["DetailedHead"]
        pitch_head(head)
        delete_old_head_residue(body)
        delete_head_below(head, cut)
        label = f"{int(round(cut * 100)):02d}"
        for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side")):
            render(
                os.path.join(output_dir, f"cut_{label}_{name}.png"),
                center,
                0.40,
                angle,
                1000,
            )


if __name__ == "__main__":
    main()
