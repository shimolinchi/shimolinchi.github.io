import bpy
import bmesh
import json
import os
import sys
from collections import defaultdict, deque
from mathutils import Vector


SLICE_ZS = (0.735, 0.745, 0.755, 0.765, 0.775)


def component_report(body, z):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    result = bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        dist=1e-6,
        plane_co=Vector((0.0, 0.0, z)),
        plane_no=Vector((0.0, 0.0, 1.0)),
        clear_inner=False,
        clear_outer=False,
    )
    cut_edges = [
        element
        for element in result["geom_cut"]
        if isinstance(element, bmesh.types.BMEdge)
    ]
    adjacency = defaultdict(set)
    points = {}
    transform = body.matrix_world
    for edge in cut_edges:
        a, b = edge.verts
        pa = transform @ a.co
        pb = transform @ b.co
        if min(abs(pa.x), abs(pb.x)) > 0.15:
            continue
        if max(pa.y, pb.y) < -0.10 or min(pa.y, pb.y) > 0.18:
            continue
        adjacency[a].add(b)
        adjacency[b].add(a)
        points[a] = pa
        points[b] = pb

    components = []
    remaining = set(adjacency)
    while remaining:
        start = next(iter(remaining))
        queue = deque([start])
        vertices = set()
        while queue:
            current = queue.popleft()
            if current in vertices:
                continue
            vertices.add(current)
            queue.extend(adjacency[current] - vertices)
        remaining -= vertices
        coords = [points[vertex] for vertex in vertices]
        lo = Vector(map(min, zip(*coords)))
        hi = Vector(map(max, zip(*coords)))
        degrees = [len(adjacency[vertex]) for vertex in vertices]
        components.append(
            {
                "vertices": len(vertices),
                "closed": bool(vertices) and all(degree == 2 for degree in degrees),
                "bounds_min": list(map(float, lo)),
                "bounds_max": list(map(float, hi)),
                "center": list(map(float, (lo + hi) * 0.5)),
                "size": list(map(float, hi - lo)),
            }
        )
    bm.free()
    return sorted(components, key=lambda item: item["vertices"], reverse=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 2:
        raise SystemExit("expected CLEAN_BLEND OUTPUT_JSON")
    clean_blend, output_json = map(os.path.abspath, argv)
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=clean_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    report = {str(z): component_report(body, z) for z in SLICE_ZS}
    with open(output_json, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
