import bpy
import math
import os
import sys
from mathutils import Matrix, Vector


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import render


PITCH_PIVOT = Vector((-0.001, 0.015, 0.855))


def pitch_head(head):
    correction = (
        Matrix.Translation(PITCH_PIVOT)
        @ Matrix.Rotation(math.radians(6.0), 4, "X")
        @ Matrix.Translation(-PITCH_PIVOT)
    )
    head.matrix_world = correction @ head.matrix_world


def delete_old_head_residue(body):
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    count = 0
    for vertex in body.data.vertices:
        point = body.matrix_world @ vertex.co
        vertex.select = (
            point.z >= 0.795
            and abs(point.x) <= 0.145
            and -0.115 <= point.y <= 0.130
        )
        count += int(vertex.select)
    body.data.update()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    body.select_set(False)
    body.data.update()
    return count


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
    removed = delete_old_head_residue(body)
    print(f"removed old head residue vertices={removed}")
    center = Vector((-0.005, 0.03, 0.855))
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(
            os.path.join(output_dir, f"minimal_{name}.png"),
            center,
            0.40,
            angle,
            1000,
        )


if __name__ == "__main__":
    main()
