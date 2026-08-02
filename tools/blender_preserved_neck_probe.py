import bpy
import os
import sys
from mathutils import Vector


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import render
from blender_neck_rebuild_probe import cut_head
from blender_pitch_cleanup_probe import delete_old_head_residue, pitch_head


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 1:
        raise SystemExit("expected OUTPUT_DIR")
    output_dir = os.path.abspath(argv[0])
    os.makedirs(output_dir, exist_ok=True)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]
    pitch_head(head)
    cut_head(head)
    removed = delete_old_head_residue(body)
    center = Vector((-0.005, 0.03, 0.855))
    for angle, name in (
        (0, "front"),
        (35, "three_quarter"),
        (90, "side"),
        (120, "rear_120"),
        (145, "rear_145"),
    ):
        render(
            os.path.join(output_dir, f"preserved_{name}.png"),
            center,
            0.40,
            angle,
            1000,
        )
    print(f"removed old-head vertices={removed}")


if __name__ == "__main__":
    main()
