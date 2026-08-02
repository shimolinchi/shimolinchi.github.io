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

from blender_head_swap import import_glb, render


BODY_CUT_Z = 0.780
HEAD_CUT_LOCAL_Z = 0.330


def delete_vertices(obj, predicate):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    count = 0
    for vertex in obj.data.vertices:
        vertex.select = predicate(obj.matrix_world @ vertex.co, vertex.co)
        count += int(vertex.select)
    obj.data.update()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    obj.data.update()
    return count


def boundary_components(obj, z_min, z_max):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    transform = obj.matrix_world
    adjacency = defaultdict(set)
    positions = {}
    perimeter_edges = set()
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        a = transform @ edge.verts[0].co
        b = transform @ edge.verts[1].co
        midpoint = (a + b) * 0.5
        if not (
            z_min <= midpoint.z <= z_max
            and abs(midpoint.x) <= 0.10
            and -0.08 <= midpoint.y <= 0.12
        ):
            continue
        ia, ib = edge.verts[0].index, edge.verts[1].index
        adjacency[ia].add(ib)
        adjacency[ib].add(ia)
        positions[ia] = a
        positions[ib] = b
        perimeter_edges.add(tuple(sorted((ia, ib))))

    components = []
    unseen = set(adjacency)
    while unseen:
        start = unseen.pop()
        queue = deque([start])
        vertices = {start}
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    vertices.add(neighbor)
                    queue.append(neighbor)
        points = [positions[index] for index in vertices]
        edges = [edge for edge in perimeter_edges if edge[0] in vertices and edge[1] in vertices]
        degree_histogram = defaultdict(int)
        for index in vertices:
            degree_histogram[len(adjacency[index])] += 1
        lo = [min(point[axis] for point in points) for axis in range(3)]
        hi = [max(point[axis] for point in points) for axis in range(3)]
        components.append(
            {
                "vertices": len(vertices),
                "edges": len(edges),
                "degrees": dict(degree_histogram),
                "bounds_min": lo,
                "bounds_max": hi,
                "center": [sum(point[axis] for point in points) / len(points) for axis in range(3)],
            }
        )
    bm.free()
    return sorted(components, key=lambda component: component["vertices"], reverse=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 3:
        raise SystemExit("expected CLEAN_BLEND ORIGINAL_BODY_GLB OUTPUT_DIR")
    clean_blend, body_glb, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=clean_blend)
    old_body = bpy.data.objects["BodyAndChair_Cut"]
    bpy.data.objects.remove(old_body, do_unlink=True)
    body = import_glb(body_glb, "BodyPlaneCut")
    head = bpy.data.objects["DetailedHead"]

    body_removed = delete_vertices(
        body,
        lambda world, local: (
            world.z > BODY_CUT_Z
            and abs(world.x) < 0.17
            and -0.14 < world.y < 0.145
        ),
    )
    head_removed = delete_vertices(
        head,
        lambda world, local: local.z < HEAD_CUT_LOCAL_Z,
    )
    report = {
        "body_removed": body_removed,
        "head_removed": head_removed,
        "body_boundary": boundary_components(body, 0.765, 0.795)[:20],
        "head_boundary": boundary_components(head, 0.765, 0.800)[:20],
    }
    with open(os.path.join(output_dir, "boundary_components.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    center = Vector((-0.005, 0.03, 0.855))
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(
            os.path.join(output_dir, f"plane_cut_{name}.png"),
            center,
            0.40,
            angle,
            1000,
        )


if __name__ == "__main__":
    main()
