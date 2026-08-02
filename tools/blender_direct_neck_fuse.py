import bpy
import bmesh
import json
import math
import os
import sys
from collections import defaultdict, deque
from mathutils import Vector


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import bounds, render
from blender_hidden_collar_fuse import (
    build_atlas_material,
    join_objects,
    remap_uvs_to_atlas,
    tag_source_vertices,
)
from blender_neck_rebuild_probe import (
    BODY_CUT_WORLD_Z,
    HEAD_CUT_LOCAL_Z,
    cut_body,
    cut_head,
)
from blender_pitch_cleanup_probe import pitch_head


MAX_BRIDGE_EDGE = 0.0065
NECK_BOTTOM_WORLD_Z = 0.720
NECK_RING_STEPS = 8


def ordered_boundary_chain(obj, selector):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    transform = obj.matrix_world
    adjacency = defaultdict(set)
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        a, b = edge.verts
        if not selector(a.co, transform @ a.co):
            continue
        if not selector(b.co, transform @ b.co):
            continue
        adjacency[a.index].add(b.index)
        adjacency[b.index].add(a.index)

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
        components.append(component)
    if not components:
        raise RuntimeError(f"No boundary chain found on {obj.name}")
    component = max(components, key=len)
    endpoints = [index for index in component if len(adjacency[index]) == 1]
    invalid = [index for index in component if len(adjacency[index]) not in (1, 2)]
    if len(endpoints) != 2 or invalid:
        raise RuntimeError(
            f"Expected one simple open chain on {obj.name}; "
            f"vertices={len(component)} endpoints={len(endpoints)} invalid={len(invalid)}"
        )

    ordered = [endpoints[0]]
    previous = None
    current = endpoints[0]
    while current != endpoints[1]:
        choices = adjacency[current] - ({previous} if previous is not None else set())
        if len(choices) != 1:
            raise RuntimeError(f"Ambiguous boundary traversal on {obj.name}")
        following = next(iter(choices))
        ordered.append(following)
        previous, current = current, following
    bm.free()
    return ordered


def align_chain_endpoints(fused, head_chain, body_chain):
    transform = fused.matrix_world

    def point(index):
        return transform @ fused.data.vertices[index].co

    same = (point(head_chain[0]) - point(body_chain[0])).length + (
        point(head_chain[-1]) - point(body_chain[-1])
    ).length
    crossed = (point(head_chain[0]) - point(body_chain[-1])).length + (
        point(head_chain[-1]) - point(body_chain[0])
    ).length
    if crossed < same:
        body_chain = list(reversed(body_chain))
    return body_chain


def add_dense_bridge(obj, head_chain, body_chain, skin_uv):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.verify()
    head_vertices = [bm.verts[index] for index in head_chain]
    body_vertices = [bm.verts[index] for index in body_chain]

    def densify_chain(chain):
        result = []
        for first, second in zip(chain[:-1], chain[1:]):
            result.append(first)
            edge = bm.edges.get((first, second))
            cuts = max(0, math.ceil(edge.calc_length() / 0.004) - 1)
            if not cuts:
                continue
            subdivided = bmesh.ops.subdivide_edges(
                bm,
                edges=[edge],
                cuts=cuts,
                use_grid_fill=False,
                smooth=0.0,
            )
            added = [
                element
                for element in subdivided.get("geom_inner", [])
                if isinstance(element, bmesh.types.BMVert)
                and element not in (first, second)
            ]
            direction = second.co - first.co
            added.sort(key=lambda vertex: (vertex.co - first.co).dot(direction))
            result.extend(added)
        result.append(chain[-1])
        return result

    head_vertices = densify_chain(head_vertices)
    body_vertices = densify_chain(body_vertices)
    source_boundary_edges = []
    for chain in (head_vertices, body_vertices):
        for first, second in zip(chain[:-1], chain[1:]):
            edge = bm.edges.get((first, second))
            if edge is None:
                raise RuntimeError("Boundary chain edge disappeared before bridge creation")
            source_boundary_edges.append(edge)

    reversed_body = list(reversed(body_vertices))
    connector_lengths = (
        (head_vertices[-1].co - reversed_body[0].co).length,
        (reversed_body[-1].co - head_vertices[0].co).length,
    )

    def connector_vertices(first, second):
        segments = max(1, math.ceil((first.co - second.co).length / MAX_BRIDGE_EDGE))
        return [
            bm.verts.new(first.co.lerp(second.co, index / segments))
            for index in range(1, segments)
        ]

    top_ring = list(head_vertices)
    top_ring.extend(connector_vertices(head_vertices[-1], reversed_body[0]))
    top_ring.extend(reversed_body)
    top_ring.extend(connector_vertices(reversed_body[-1], head_vertices[0]))
    transform = obj.matrix_world
    inverse = transform.inverted()
    top_center = Vector((-0.005, 0.0435, 0.0))
    bottom_center = Vector((-0.005, 0.0435, NECK_BOTTOM_WORLD_Z))
    rings = [top_ring]
    for step in range(1, NECK_RING_STEPS + 1):
        factor = step / NECK_RING_STEPS
        ring = []
        for vertex in top_ring:
            top_world = transform @ vertex.co
            bottom_world = Vector(
                (
                    bottom_center.x + 0.82 * (top_world.x - top_center.x),
                    bottom_center.y + 0.82 * (top_world.y - top_center.y),
                    NECK_BOTTOM_WORLD_Z,
                )
            )
            ring.append(bm.verts.new(inverse @ top_world.lerp(bottom_world, factor)))
        rings.append(ring)

    created_quads = []
    for upper, lower in zip(rings[:-1], rings[1:]):
        for index in range(len(top_ring)):
            following = (index + 1) % len(top_ring)
            face = bm.faces.new(
                (upper[index], upper[following], lower[following], lower[index])
            )
            face.material_index = 0
            face.smooth = True
            created_quads.append(face)
    bridge_faces = bmesh.ops.triangulate(bm, faces=created_quads)["faces"]
    bmesh.ops.recalc_face_normals(bm, faces=bridge_faces)
    for face in bridge_faces:
        face.material_index = 0
        face.smooth = True
        for loop in face.loops:
            loop[uv_layer].uv = skin_uv

    cut_non_triangles = [
        face for face in bm.faces if face not in bridge_faces and len(face.verts) != 3
    ]
    if cut_non_triangles:
        bmesh.ops.triangulate(bm, faces=cut_non_triangles)
    bridge_edges = {edge for face in bridge_faces for edge in face.edges}
    added_edges = bridge_edges - set(source_boundary_edges)
    max_edge = max(edge.calc_length() for edge in added_edges)
    max_source_boundary_edge = max(edge.calc_length() for edge in source_boundary_edges)
    bottom_boundary_max_edge = max(
        (rings[-1][index].co - rings[-1][(index + 1) % len(top_ring)].co).length
        for index in range(len(top_ring))
    )
    triangle_count = len(bridge_faces)
    new_vertices = max(0, len(bm.verts) - len(obj.data.vertices))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {
        "triangles": triangle_count,
        "new_vertices": new_vertices,
        "ring_steps": NECK_RING_STEPS,
        "bottom_world_z": NECK_BOTTOM_WORLD_Z,
        "max_bridge_edge": max_edge,
        "max_source_boundary_edge": max_source_boundary_edge,
        "bottom_boundary_max_edge": bottom_boundary_max_edge,
        "connector_lengths": connector_lengths,
        "cut_faces_triangulated": len(cut_non_triangles),
    }


def local_connectivity(obj, head_points, body_points):
    def key(point):
        return tuple(round(float(value), 5) for value in point)

    head_keys = {key(point) for point in head_points}
    body_keys = {key(point) for point in body_points}
    relevant = set()
    keys = []
    for index, vertex in enumerate(obj.data.vertices):
        point = obj.matrix_world @ vertex.co
        keys.append(key(point))
        if (
            abs(point.x) <= 0.10
            and -0.03 <= point.y <= 0.14
            and 0.675 <= point.z <= 0.800
        ):
            relevant.add(index)
    starts = {index for index in relevant if keys[index] in head_keys}
    targets = {index for index in relevant if keys[index] in body_keys}
    adjacency = defaultdict(set)
    for edge in obj.data.edges:
        a, b = edge.vertices
        if a in relevant and b in relevant:
            adjacency[a].add(b)
            adjacency[b].add(a)
    queue = deque(starts)
    reached = set(starts)
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in reached:
                reached.add(neighbor)
                queue.append(neighbor)
    reached_targets = reached & targets
    return {
        "head_anchor_vertices": len(starts),
        "body_anchor_vertices": len(targets),
        "reached_body_anchor_vertices": len(reached_targets),
        "connected": bool(reached_targets),
    }


def verify_reimport(glb_path, head_points, body_points):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one GLB mesh object, got {len(meshes)}")
    obj = meshes[0]
    if len(obj.material_slots) != 1:
        raise RuntimeError(f"Expected one GLB material, got {len(obj.material_slots)}")
    non_triangles = sum(polygon.loop_total != 3 for polygon in obj.data.polygons)
    if non_triangles:
        raise RuntimeError(f"GLB contains {non_triangles} non-triangle faces")
    connectivity = local_connectivity(obj, head_points, body_points)
    if not connectivity["connected"]:
        raise RuntimeError("Re-imported GLB lost direct head/body neck connectivity")
    return obj, connectivity


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 3:
        raise SystemExit("expected CLEAN_BLEND ATLAS_DIR OUTPUT_DIR")
    clean_blend, atlas_dir, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    blend_path = os.path.join(output_dir, "seated_person_detailed_head_direct_fused.blend")
    glb_path = os.path.join(output_dir, "seated_person_detailed_head_direct_fused.glb")
    report_path = os.path.join(output_dir, "direct_fusion_report.json")

    bpy.ops.wm.open_mainfile(filepath=clean_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]
    pitch_head(head)
    cut_head(head)
    removed_body_vertices = cut_body(body)

    head_chain_local = ordered_boundary_chain(
        head,
        lambda local, world: abs(local.z - HEAD_CUT_LOCAL_Z) <= 2e-5,
    )
    body_chain = ordered_boundary_chain(
        body,
        lambda local, world: (
            abs(world.z - BODY_CUT_WORLD_Z) <= 2e-5
            and abs(world.x) <= 0.08
            and -0.01 <= world.y <= 0.11
        ),
    )
    body_material = body.material_slots[0].material
    body_material_name = body_material.name
    head_material_name = head.material_slots[0].material.name
    tag_source_vertices(body, "SourceBody")
    tag_source_vertices(head, "SourceHead")
    body_vertex_count = len(body.data.vertices)
    fused = join_objects(body, head)
    head_chain = [body_vertex_count + index for index in head_chain_local]
    body_chain = align_chain_endpoints(fused, head_chain, body_chain)

    transform = fused.matrix_world
    head_points = [transform @ fused.data.vertices[index].co for index in head_chain]
    body_points = [transform @ fused.data.vertices[index].co for index in body_chain]
    body_material_index = next(
        index
        for index, slot in enumerate(fused.material_slots)
        if slot.material and slot.material.name == body_material_name
    )
    head_material_index = next(
        index
        for index, slot in enumerate(fused.material_slots)
        if slot.material and slot.material.name == head_material_name
    )
    uv_remap = remap_uvs_to_atlas(fused, body_material_index, head_material_index)
    atlas_material, texture_replacements = build_atlas_material(body_material, atlas_dir)
    for polygon in fused.data.polygons:
        polygon.material_index = 0
    fused.data.materials.clear()
    fused.data.materials.append(atlas_material)
    skin_uv = Vector((0.5 + 0.5 * 0.73388671875, 0.6328125))
    bridge = add_dense_bridge(fused, head_chain, body_chain, skin_uv)
    if bridge["max_bridge_edge"] > MAX_BRIDGE_EDGE * 1.05:
        raise RuntimeError(
            f"Bridge still contains long edge {bridge['max_bridge_edge']:.6f}"
        )
    if any(polygon.loop_total != 3 for polygon in fused.data.polygons):
        raise RuntimeError("Fused blend contains non-triangle faces")
    source_connectivity = local_connectivity(fused, head_points, body_points)
    if not source_connectivity["connected"]:
        raise RuntimeError("Blend mesh is not directly connected across the neck")

    fused["fusion_method"] = "direct dense triangle neck tube"
    fused["pitch_degrees"] = 6.0
    fused["head_cut_local_z"] = HEAD_CUT_LOCAL_Z
    fused["body_cut_world_z"] = BODY_CUT_WORLD_Z
    fused["bridge_triangles"] = bridge["triangles"]
    blend_stats = {
        "objects": 1,
        "materials": len(fused.material_slots),
        "vertices": len(fused.data.vertices),
        "edges": len(fused.data.edges),
        "triangles": len(fused.data.polygons),
        "neck_connectivity": source_connectivity,
    }
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    bpy.ops.object.select_all(action="DESELECT")
    fused.select_set(True)
    bpy.context.view_layer.objects.active = fused
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_attributes=False,
        export_normals=False,
    )
    imported, reimport_connectivity = verify_reimport(glb_path, head_points, body_points)

    lo, hi = bounds([imported])
    full_center = (lo + hi) * 0.5
    full_scale = max(hi - lo) * 1.15
    head_center = Vector((-0.005, 0.03, 0.855))
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(os.path.join(output_dir, f"full_{name}.png"), full_center, full_scale, angle, 800)
        render(os.path.join(output_dir, f"head_{name}.png"), head_center, 0.40, angle, 1000)

    report = {
        "sources_unchanged": True,
        "outputs": {"blend": blend_path, "glb": glb_path},
        "alignment": {"pitch_degrees": 6.0},
        "cuts": {
            "head_local_z": HEAD_CUT_LOCAL_Z,
            "body_world_z": BODY_CUT_WORLD_Z,
            "body_removed_vertices": removed_body_vertices,
        },
        "boundary_chains": {
            "head_vertices": len(head_chain),
            "body_vertices": len(body_chain),
        },
        "bridge": bridge,
        "uv_atlas": {
            "remapped_faces": uv_remap,
            "texture_replacements": texture_replacements,
        },
        "blend": blend_stats,
        "glb_reimport": {
            "objects": 1,
            "materials": len(imported.material_slots),
            "vertices": len(imported.data.vertices),
            "edges": len(imported.data.edges),
            "triangles": len(imported.data.polygons),
            "neck_connectivity": reimport_connectivity,
        },
    }
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
