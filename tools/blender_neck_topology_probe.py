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

from blender_pitch_cleanup_probe import delete_old_head_residue, pitch_head


HEAD_CUT_LOCAL_Z = 0.33
WELD_DISTANCE = 0.0002


def bisect_head(head):
    mesh = head.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    result = bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        dist=1e-6,
        plane_co=Vector((0.0, 0.0, HEAD_CUT_LOCAL_Z)),
        plane_no=Vector((0.0, 0.0, 1.0)),
        clear_inner=True,
        clear_outer=False,
    )
    cut_vertices = {
        element
        for element in result["geom_cut"]
        if isinstance(element, bmesh.types.BMVert)
    }
    bmesh.ops.remove_doubles(bm, verts=list(cut_vertices), dist=WELD_DISTANCE)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return len(cut_vertices)


def boundary_components(obj, plane_co_local, plane_no_local):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    transform = obj.matrix_world
    adjacency = defaultdict(set)
    points = {}
    edges = []
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        a, b = edge.verts
        if abs(plane_no_local.dot(a.co - plane_co_local)) > 2e-5:
            continue
        if abs(plane_no_local.dot(b.co - plane_co_local)) > 2e-5:
            continue
        for vertex in (a, b):
            adjacency[vertex.index]
            points[vertex.index] = transform @ vertex.co
        adjacency[a.index].add(b.index)
        adjacency[b.index].add(a.index)
        edges.append((a.index, b.index))

    components = []
    remaining = set(adjacency)
    while remaining:
        start = next(iter(remaining))
        queue = deque([start])
        component = set()
        while queue:
            current = queue.popleft()
            if current in component:
                continue
            component.add(current)
            queue.extend(adjacency[current] - component)
        remaining -= component
        component_points = [points[index] for index in component]
        component_edges = [edge for edge in edges if edge[0] in component]
        degrees = [len(adjacency[index]) for index in component]
        components.append(
            {
                "vertices": len(component),
                "edges": len(component_edges),
                "closed": bool(component) and all(degree == 2 for degree in degrees),
                "degree_histogram": {
                    str(degree): degrees.count(degree) for degree in sorted(set(degrees))
                },
                "bounds_min": list(map(float, Vector(map(min, zip(*component_points))))),
                "bounds_max": list(map(float, Vector(map(max, zip(*component_points))))),
            }
        )
    bm.free()
    return sorted(components, key=lambda item: item["vertices"], reverse=True)


def cut_body_above_plane(body, plane_point_world, plane_normal_world):
    mesh = body.data
    inverse = body.matrix_world.inverted()
    plane_co_local = inverse @ plane_point_world
    plane_no_local = (
        body.matrix_world.to_3x3().transposed() @ plane_normal_world
    ).normalized()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        dist=1e-6,
        plane_co=plane_co_local,
        plane_no=plane_no_local,
        clear_inner=False,
        clear_outer=False,
    )
    plane_vertices = [
        vertex
        for vertex in bm.verts
        if abs(plane_no_local.dot(vertex.co - plane_co_local)) <= 2e-5
    ]
    bmesh.ops.remove_doubles(bm, verts=plane_vertices, dist=WELD_DISTANCE)
    delete = []
    for vertex in bm.verts:
        world = body.matrix_world @ vertex.co
        signed_distance = plane_normal_world.dot(world - plane_point_world)
        if (
            signed_distance > 1e-6
            and abs(world.x) <= 0.145
            and -0.115 <= world.y <= 0.130
        ):
            delete.append(vertex)
    bmesh.ops.delete(bm, geom=delete, context="VERTS")
    removed = len(delete)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return removed, plane_co_local, plane_no_local


def main():
    global HEAD_CUT_LOCAL_Z
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) not in (2, 3):
        raise SystemExit("expected CLEAN_BLEND OUTPUT_JSON [HEAD_CUT_LOCAL_Z]")
    clean_blend, output_json = map(os.path.abspath, argv[:2])
    if len(argv) == 3:
        HEAD_CUT_LOCAL_Z = float(argv[2])
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=clean_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]
    pitch_head(head)
    plane_point_world = head.matrix_world @ Vector((0.0, 0.0, HEAD_CUT_LOCAL_Z))
    plane_normal_world = (
        head.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
    ).normalized()
    removed_body_vertices, body_plane_co, body_plane_no = cut_body_above_plane(
        body, plane_point_world, plane_normal_world
    )
    cut_vertices = bisect_head(head)
    report = {
        "head_cut_local_z": HEAD_CUT_LOCAL_Z,
        "head_cut_vertices": cut_vertices,
        "weld_distance": WELD_DISTANCE,
        "removed_body_vertices": removed_body_vertices,
        "plane_point_world": list(map(float, plane_point_world)),
        "plane_normal_world": list(map(float, plane_normal_world)),
        "head_boundary_components": boundary_components(
            head, Vector((0.0, 0.0, HEAD_CUT_LOCAL_Z)), Vector((0.0, 0.0, 1.0))
        ),
        "body_boundary_components": boundary_components(
            body, body_plane_co, body_plane_no
        ),
    }
    with open(output_json, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
