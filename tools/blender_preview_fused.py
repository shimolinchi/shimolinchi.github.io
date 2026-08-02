import bpy
import bmesh
import json
import os
import sys


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import bounds, render


def seam_boundary_stats(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    transform = obj.matrix_world
    total = 0
    core = 0
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        total += 1
        midpoint = transform @ ((edge.verts[0].co + edge.verts[1].co) * 0.5)
        if (
            -0.13 <= midpoint.x <= 0.13
            and -0.09 <= midpoint.y <= 0.14
            and 0.72 <= midpoint.z <= 0.82
        ):
            core += 1
    bm.free()
    return {"total_boundary_edges": total, "fusion_core_boundary_edges": core}


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 3:
        raise SystemExit("expected INPUT_BLEND OUTPUT_DIR REPORT_JSON")
    input_blend, output_dir, report_path = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=input_blend)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one fused mesh object, got {len(meshes)}")
    fused = meshes[0]
    lo, hi = bounds([fused])
    full_center = (lo + hi) / 2
    full_scale = max((hi - lo)) * 1.15
    head_center = (-0.005, 0.03, 0.875)
    from mathutils import Vector

    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(os.path.join(output_dir, f"fused_full_{name}.png"), full_center, full_scale, angle, 800)
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(
            os.path.join(output_dir, f"fused_head_{name}.png"),
            Vector(head_center),
            0.34,
            angle,
            900,
        )
    report = {
        "object": fused.name,
        "vertices": len(fused.data.vertices),
        "edges": len(fused.data.edges),
        "polygons": len(fused.data.polygons),
        "materials": [slot.material.name if slot.material else None for slot in fused.material_slots],
        "bounds_min": list(lo),
        "bounds_max": list(hi),
        "boundary": seam_boundary_stats(fused),
    }
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
