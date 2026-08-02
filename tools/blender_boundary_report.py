import bpy
import bmesh
import json
import os
import sys
from collections import defaultdict, deque
from mathutils import Vector


def boundary_components(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    boundary_edges = [edge for edge in bm.edges if edge.is_boundary]
    adjacency = defaultdict(list)
    for edge in boundary_edges:
        a, b = edge.verts
        adjacency[a.index].append(b.index)
        adjacency[b.index].append(a.index)

    components = []
    unseen = set(adjacency)
    while unseen:
        start = next(iter(unseen))
        queue = deque([start])
        indices = []
        unseen.remove(start)
        while queue:
            current = queue.popleft()
            indices.append(current)
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
        points = [obj.matrix_world @ bm.verts[index].co for index in indices]
        lo = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
        hi = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
        degree_counts = defaultdict(int)
        for index in indices:
            degree_counts[len(adjacency[index])] += 1
        components.append(
            {
                "vertices": len(indices),
                "bounds_min": [round(float(value), 6) for value in lo],
                "bounds_max": [round(float(value), 6) for value in hi],
                "center": [round(float(value), 6) for value in (lo + hi) / 2],
                "size": [round(float(value), 6) for value in hi - lo],
                "degree_counts": dict(degree_counts),
                "closed_simple_loop": all(len(adjacency[index]) == 2 for index in indices),
            }
        )
    bm.free()
    components.sort(key=lambda item: item["vertices"], reverse=True)
    return {
        "object": obj.name,
        "mesh_vertices": len(mesh.vertices),
        "mesh_polygons": len(mesh.polygons),
        "boundary_edges": len(boundary_edges),
        "components": components,
    }


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 2:
        raise SystemExit("expected INPUT_BLEND OUTPUT_JSON")
    input_path, output_path = map(os.path.abspath, argv)
    bpy.ops.wm.open_mainfile(filepath=input_path)
    report = [boundary_components(obj) for obj in bpy.context.scene.objects if obj.type == "MESH"]
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
