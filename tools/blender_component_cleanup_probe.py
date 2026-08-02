import bpy
import os
import sys
from mathutils import Vector


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import render
from blender_neck_cut_sweep import delete_head_below
from blender_pitch_cleanup_probe import delete_old_head_residue, pitch_head


def delete_lower_islands(head):
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for vertex in head.data.vertices:
        vertex.select = vertex.co.z >= 0.45
    head.data.update()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_linked()
    bpy.ops.object.mode_set(mode="OBJECT")
    selected = sum(int(vertex.select) for vertex in head.data.vertices)
    delete_count = 0
    for vertex in head.data.vertices:
        vertex.select = not vertex.select and vertex.co.z < 0.45
        delete_count += int(vertex.select)
    head.data.update()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    head.select_set(False)
    head.data.update()
    return selected, delete_count


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 2:
        raise SystemExit("expected CLEAN_BLEND OUTPUT_DIR")
    clean_blend, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=clean_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]
    pitch_head(head)
    old_body_removed = delete_old_head_residue(body)
    delete_head_below(head, 0.33)
    selected, islands_removed = delete_lower_islands(head)
    print(
        f"body residue removed={old_body_removed}, head linked selected={selected}, "
        f"lower-island vertices removed={islands_removed}"
    )
    center = Vector((-0.005, 0.03, 0.855))
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(
            os.path.join(output_dir, f"component_clean_{name}.png"),
            center,
            0.40,
            angle,
            1000,
        )


if __name__ == "__main__":
    main()
