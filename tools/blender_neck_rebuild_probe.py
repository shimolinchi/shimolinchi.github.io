import bpy
import bmesh
import json
import os
import sys
from collections import defaultdict, deque
from mathutils import Vector


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import render
from blender_pitch_cleanup_probe import pitch_head


HEAD_CUT_LOCAL_Z = 0.33
BODY_CUT_WORLD_Z = 0.755
WELD_DISTANCE = 0.001


def cut_head(head):
    bm = bmesh.new()
    bm.from_mesh(head.data)
    result = bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        dist=1e-6,
        plane_co=Vector((0.0, 0.0, HEAD_CUT_LOCAL_Z)),
        plane_no=Vector((0.0, 0.0, 1.0)),
        clear_inner=True,
        clear_outer=False,
    )
    cut_vertices = [
        element
        for element in result["geom_cut"]
        if isinstance(element, bmesh.types.BMVert)
    ]
    bmesh.ops.remove_doubles(bm, verts=cut_vertices, dist=WELD_DISTANCE)
    bm.to_mesh(head.data)
    bm.free()
    head.data.update()


def inside_body_removal(point):
    if point.z <= BODY_CUT_WORLD_Z + 1e-6:
        return False
    if point.z >= 0.795:
        return abs(point.x) <= 0.145 and -0.115 <= point.y <= 0.130

    factor = (point.z - BODY_CUT_WORLD_Z) / (0.795 - BODY_CUT_WORLD_Z)
    center_x = -0.005
    center_y = 0.055 - 0.020 * factor
    radius_x = 0.052 + 0.080 * factor
    radius_y = 0.035 + 0.095 * factor
    return (
        ((point.x - center_x) / radius_x) ** 2
        + ((point.y - center_y) / radius_y) ** 2
        <= 1.0
    )


def cut_body(body):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    result = bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        dist=1e-6,
        plane_co=Vector((0.0, 0.0, BODY_CUT_WORLD_Z)),
        plane_no=Vector((0.0, 0.0, 1.0)),
        clear_inner=False,
        clear_outer=False,
    )
    cut_vertices = [
        element
        for element in result["geom_cut"]
        if isinstance(element, bmesh.types.BMVert)
    ]
    bmesh.ops.remove_doubles(bm, verts=cut_vertices, dist=WELD_DISTANCE)
    delete = [
        vertex
        for vertex in bm.verts
        if inside_body_removal(body.matrix_world @ vertex.co)
    ]
    bmesh.ops.delete(bm, geom=delete, context="VERTS")
    removed = len(delete)
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    return removed


def boundary_components(obj, selector):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    transform = obj.matrix_world
    adjacency = defaultdict(set)
    points = {}
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        a, b = edge.verts
        pa = transform @ a.co
        pb = transform @ b.co
        if not selector(a.co, pa) or not selector(b.co, pb):
            continue
        adjacency[a.index].add(b.index)
        adjacency[b.index].add(a.index)
        points[a.index] = pa
        points[b.index] = pb

    components = []
    remaining = set(adjacency)
    while remaining:
        start = next(iter(remaining))
        queue = deque([start])
        indices = set()
        while queue:
            current = queue.popleft()
            if current in indices:
                continue
            indices.add(current)
            queue.extend(adjacency[current] - indices)
        remaining -= indices
        coords = [points[index] for index in indices]
        lo = Vector(map(min, zip(*coords)))
        hi = Vector(map(max, zip(*coords)))
        degrees = [len(adjacency[index]) for index in indices]
        endpoint_indices = [
            index for index in indices if len(adjacency[index]) == 1
        ]
        components.append(
            {
                "vertices": len(indices),
                "closed": bool(indices) and all(degree == 2 for degree in degrees),
                "bounds_min": list(map(float, lo)),
                "bounds_max": list(map(float, hi)),
                "endpoints": [
                    list(map(float, points[index])) for index in endpoint_indices
                ],
            }
        )
    bm.free()
    return sorted(components, key=lambda item: item["vertices"], reverse=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 3:
        raise SystemExit("expected CLEAN_BLEND OUTPUT_DIR OUTPUT_BLEND")
    clean_blend, output_dir, output_blend = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=clean_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]
    pitch_head(head)
    cut_head(head)
    removed_body_vertices = cut_body(body)

    head_components = boundary_components(
        head,
        lambda local, world: abs(local.z - HEAD_CUT_LOCAL_Z) <= 2e-5,
    )
    body_components = boundary_components(
        body,
        lambda local, world: (
            abs(world.z - BODY_CUT_WORLD_Z) <= 2e-5
            and abs(world.x) <= 0.08
            and -0.01 <= world.y <= 0.11
        ),
    )
    report = {
        "head_cut_local_z": HEAD_CUT_LOCAL_Z,
        "body_cut_world_z": BODY_CUT_WORLD_Z,
        "removed_body_vertices": removed_body_vertices,
        "head_boundary_components": head_components,
        "body_boundary_components": body_components,
    }
    report_path = os.path.join(output_dir, "report.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)

    center = Vector((-0.005, 0.03, 0.855))
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(
            os.path.join(output_dir, f"rebuild_{name}.png"),
            center,
            0.40,
            angle,
            1000,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
