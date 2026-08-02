import bpy
import os
import sys
from mathutils import Vector


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_closed_neck_fuse import add_closed_neck_tube, ordered_boundary_loop
from blender_head_swap import render
from blender_hidden_collar_fuse import join_objects, tag_source_vertices
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
    head_loop_local = ordered_boundary_loop(head)
    tag_source_vertices(body, "SourceBody")
    tag_source_vertices(head, "SourceHead")
    body_vertex_count = len(body.data.vertices)
    fused = join_objects(body, head)
    head_loop = [body_vertex_count + index for index in head_loop_local]
    _, tube, _ = add_closed_neck_tube(
        fused,
        head_loop,
        body_vertex_count,
        Vector((0.866943359375, 0.6328125)),
    )
    center = Vector((-0.005, 0.03, 0.855))
    for angle, name in (
        (0, "front"),
        (35, "three_quarter"),
        (90, "side"),
        (120, "rear_120"),
        (145, "rear_145"),
    ):
        render(
            os.path.join(output_dir, f"fused_{name}.png"),
            center,
            0.40,
            angle,
            1000,
        )
    print(f"removed={removed} tube={tube}")


if __name__ == "__main__":
    main()
