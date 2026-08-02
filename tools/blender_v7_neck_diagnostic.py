import bpy
import bmesh
import json
import os
import sys
from collections import defaultdict, deque
from mathutils import Vector


def source_groups(obj):
    return {
        name: obj.vertex_groups[name].index
        for name in ("SourceBody", "SourceHead")
        if obj.vertex_groups.get(name) is not None
    }


def source_name(vertex, groups):
    memberships = {membership.group for membership in vertex.groups}
    for name, group_index in groups.items():
        if group_index in memberships:
            return name
    return "Generated"


def component_report(obj, generated_indices):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    transform = obj.matrix_world
    adjacency = defaultdict(set)
    points = {}
    for edge in bm.edges:
        if not edge.is_boundary or not any(
            vertex.index in generated_indices for vertex in edge.verts
        ):
            continue
        a, b = edge.verts
        pa = transform @ a.co
        pb = transform @ b.co
        midpoint = (pa + pb) * 0.5
        if not (
            abs(midpoint.x) <= 0.16
            and -0.14 <= midpoint.y <= 0.20
            and 0.68 <= midpoint.z <= 0.94
        ):
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
        lo = Vector(tuple(min(point[axis] for point in coords) for axis in range(3)))
        hi = Vector(tuple(max(point[axis] for point in coords) for axis in range(3)))
        components.append(
            {
                "vertices": len(indices),
                "closed": all(len(adjacency[index]) == 2 for index in indices),
                "bounds_min": list(map(float, lo)),
                "bounds_max": list(map(float, hi)),
                "mean": [
                    sum(point[axis] for point in coords) / len(coords)
                    for axis in range(3)
                ],
            }
        )
    bm.free()
    return sorted(components, key=lambda item: item["vertices"], reverse=True)


def point_bounds(points):
    if not points:
        return None
    return {
        "count": len(points),
        "min": [min(point[axis] for point in points) for axis in range(3)],
        "max": [max(point[axis] for point in points) for axis in range(3)],
    }


def nearest_points(points, targets):
    results = []
    for target in targets:
        point = min(points, key=lambda candidate: (candidate - target).length_squared)
        results.append(
            {
                "target": list(map(float, target)),
                "point": list(map(float, point)),
                "distance": float((point - target).length),
            }
        )
    return results


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 1:
        raise SystemExit("expected OUTPUT_JSON")
    output_json = os.path.abspath(argv[0])
    obj = next(item for item in bpy.context.scene.objects if item.type == "MESH")
    transform = obj.matrix_world
    groups = source_groups(obj)

    body_points = []
    head_points = []
    generated_points = []
    bottom_points = []
    generated_indices = set()
    for vertex in obj.data.vertices:
        point = transform @ vertex.co
        if not (
            abs(point.x) <= 0.16
            and -0.14 <= point.y <= 0.20
            and 0.68 <= point.z <= 0.94
        ):
            continue
        source = source_name(vertex, groups)
        if source == "SourceBody":
            body_points.append(point)
        elif source == "SourceHead":
            head_points.append(point)
        else:
            generated_indices.add(vertex.index)
            generated_points.append(point)
            if abs(point.z - 0.750) <= 1e-5:
                bottom_points.append(point)

    report = {
        "neck_boundary_components": component_report(obj, generated_indices),
        "region_bounds": {
            "source_body": point_bounds(body_points),
            "source_head": point_bounds(head_points),
            "generated": point_bounds(generated_points),
            "generated_bottom_ring": point_bounds(bottom_points),
        },
        "nearest_body": nearest_points(
            body_points,
            [
                Vector((-0.005, 0.050, 0.700)),
                Vector((-0.005, 0.050, 0.720)),
                Vector((-0.005, 0.050, 0.735)),
                Vector((-0.005, 0.085, 0.720)),
                Vector((-0.005, 0.105, 0.720)),
            ],
        ),
    }
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
