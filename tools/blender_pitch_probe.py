import bpy
import math
import os
import sys
from mathutils import Matrix, Vector


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import import_glb, render


PIVOT = Vector((-0.001, 0.015, 0.855))
ANGLES = (0, 3, 6, 9)


def material(name, color, alpha=1.0):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, alpha)
    result.use_nodes = True
    principled = result.node_tree.nodes["Principled BSDF"]
    principled.inputs["Base Color"].default_value = (*color, alpha)
    principled.inputs["Roughness"].default_value = 0.5
    principled.inputs["Alpha"].default_value = alpha
    if alpha < 1.0:
        result.surface_render_method = "DITHERED"
    return result


def correction(angle_degrees):
    pivot = Matrix.Translation(PIVOT)
    inverse = Matrix.Translation(-PIVOT)
    rotation = Matrix.Rotation(math.radians(angle_degrees), 4, "X")
    return pivot @ rotation @ inverse


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 3:
        raise SystemExit("expected CLEAN_BLEND ORIGINAL_BODY_GLB OUTPUT_DIR")
    clean_blend, body_glb, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=clean_blend)
    old_body = bpy.data.objects["BodyAndChair_Cut"]
    bpy.data.objects.remove(old_body, do_unlink=True)
    body = import_glb(body_glb, "OriginalBodyForPitch")
    head = bpy.data.objects["DetailedHead"]
    original_matrix = head.matrix_world.copy()
    body.data.materials.clear()
    body.data.materials.append(material("ORIGINAL_BODY_RED", (0.65, 0.025, 0.015), 1.0))
    head.data.materials.clear()
    head.data.materials.append(material("DETAILED_HEAD_CYAN", (0.01, 0.60, 0.95), 0.58))

    center = Vector((-0.005, 0.02, 0.855))
    for angle in ANGLES:
        head.matrix_world = correction(angle) @ original_matrix
        for view_angle, name in ((35, "three_quarter"), (90, "side")):
            render(
                os.path.join(output_dir, f"pitch_{angle:02d}_{name}.png"),
                center,
                0.34,
                view_angle,
                1000,
            )


if __name__ == "__main__":
    main()
