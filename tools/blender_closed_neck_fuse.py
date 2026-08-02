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

from blender_direct_neck_fuse import local_connectivity, verify_reimport
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
from blender_pitch_cleanup_probe import delete_old_head_residue, pitch_head


NECK_BOTTOM_DROP = 0.003
NECK_RING_STEPS = 12
CLOSURE_RING_STEPS = 6


def ordered_boundary_loop(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    adjacency = defaultdict(set)
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        a, b = edge.verts
        if abs(a.co.z - HEAD_CUT_LOCAL_Z) > 2e-5:
            continue
        if abs(b.co.z - HEAD_CUT_LOCAL_Z) > 2e-5:
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
        raise RuntimeError("No detailed-head neck boundary found")
    component = max(components, key=len)
    if any(len(adjacency[index]) != 2 for index in component):
        raise RuntimeError("Detailed-head neck boundary is not a simple closed loop")

    start = min(component)
    ordered = [start]
    previous = None
    current = start
    while True:
        choices = adjacency[current] - ({previous} if previous is not None else set())
        following = min(choices)
        if following == start:
            break
        ordered.append(following)
        previous, current = current, following
        if len(ordered) > len(component):
            raise RuntimeError("Closed neck boundary traversal did not terminate")
    bm.free()
    if len(ordered) != len(component):
        raise RuntimeError(
            f"Closed neck loop traversal reached {len(ordered)}/{len(component)} vertices"
        )
    return ordered


def smoothstep(edge0, edge1, value):
    factor = min(1.0, max(0.0, (value - edge0) / (edge1 - edge0)))
    return factor * factor * (3.0 - 2.0 * factor)


def add_closed_neck_tube(obj, head_loop, body_vertex_count, skin_uv):
    source_uv_layer = obj.data.uv_layers.active
    top_uv_by_index = {}
    wanted = set(head_loop)
    for polygon in obj.data.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = obj.data.loops[loop_index].vertex_index
            if vertex_index in wanted and vertex_index not in top_uv_by_index:
                top_uv_by_index[vertex_index] = source_uv_layer.data[loop_index].uv.copy()
        if len(top_uv_by_index) == len(wanted):
            break
    if len(top_uv_by_index) != len(wanted):
        raise RuntimeError("Missing source UVs on detailed-head neck loop")

    transform = obj.matrix_world
    normal_matrix = transform.to_3x3().inverted().transposed()
    top_world_points = [
        transform @ obj.data.vertices[index].co for index in head_loop
    ]
    top_world_normals = [
        (normal_matrix @ obj.data.vertices[index].normal).normalized()
        for index in head_loop
    ]
    downward_tangents = []
    for index, normal in enumerate(top_world_normals):
        previous = top_world_points[index - 1]
        following = top_world_points[(index + 1) % len(top_world_points)]
        boundary_tangent = (following - previous).normalized()
        downward = normal.cross(boundary_tangent).normalized()
        if downward.z > 0.0:
            downward.negate()
        if downward.z > -0.25:
            downward = (downward + Vector((0.0, 0.0, -0.75))).normalized()
        downward_tangents.append(downward)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.verify()
    top_ring = [bm.verts[index] for index in head_loop]
    top_uvs = [top_uv_by_index[index] for index in head_loop]
    uv_by_vertex = {
        vertex: source_uv for vertex, source_uv in zip(top_ring, top_uvs)
    }
    source_edges = []
    for index in range(len(top_ring)):
        edge = bm.edges.get((top_ring[index], top_ring[(index + 1) % len(top_ring)]))
        if edge is None:
            raise RuntimeError("Detailed-head closed neck edge disappeared")
        source_edges.append(edge)

    inverse = transform.inverted()
    top_center = Vector((-0.005, 0.0415, 0.0))
    bottom_center = Vector((-0.005, 0.0415, 0.0))
    rings = [top_ring]
    for step in range(1, NECK_RING_STEPS + 1):
        factor = step / NECK_RING_STEPS
        h00 = 2.0 * factor**3 - 3.0 * factor**2 + 1.0
        h10 = factor**3 - 2.0 * factor**2 + factor
        h01 = -2.0 * factor**3 + 3.0 * factor**2
        h11 = factor**3 - factor**2
        ring = []
        for vertex, source_uv, initial_tangent in zip(
            top_ring, top_uvs, downward_tangents
        ):
            top_world = transform @ vertex.co
            bottom_world_z = top_world.z - NECK_BOTTOM_DROP
            bottom_world = Vector(
                (
                    bottom_center.x
                    + 0.98 * (top_world.x - top_center.x),
                    bottom_center.y
                    + 0.98 * (top_world.y - top_center.y),
                    bottom_world_z,
                )
            )
            distance = (bottom_world - top_world).length
            start_derivative = initial_tangent * distance * 0.85
            end_derivative = Vector((0.0, 0.0, -distance * 0.65))
            world_point = (
                h00 * top_world
                + h10 * start_derivative
                + h01 * bottom_world
                + h11 * end_derivative
            )
            new_vertex = bm.verts.new(inverse @ world_point)
            ring.append(new_vertex)
            uv_by_vertex[new_vertex] = source_uv
        rings.append(ring)

    quads = []
    for upper, lower in zip(rings[:-1], rings[1:]):
        for index in range(len(top_ring)):
            following = (index + 1) % len(top_ring)
            face = bm.faces.new(
                (upper[index], upper[following], lower[following], lower[index])
            )
            face.material_index = 0
            face.smooth = True
            quads.append(face)
    tube_faces = bmesh.ops.triangulate(bm, faces=quads)["faces"]

    outer_bottom_ring = rings[-1]
    outer_bottom_world = [transform @ vertex.co for vertex in outer_bottom_ring]
    closure_center = Vector((-0.005, 0.050, 0.0))
    closure_rings = [outer_bottom_ring]
    for step in range(1, CLOSURE_RING_STEPS + 1):
        factor = step / CLOSURE_RING_STEPS
        radial_scale = 1.0 - 0.90 * factor
        ring = []
        for outer_world, source_uv in zip(outer_bottom_world, top_uvs):
            world_point = Vector(
                (
                    closure_center.x
                    + radial_scale * (outer_world.x - closure_center.x),
                    closure_center.y
                    + radial_scale * (outer_world.y - closure_center.y),
                    outer_world.z + 0.012 * factor,
                )
            )
            new_vertex = bm.verts.new(inverse @ world_point)
            ring.append(new_vertex)
            uv_by_vertex[new_vertex] = source_uv
        closure_rings.append(ring)

    closure_quads = []
    for outer, inner in zip(closure_rings[:-1], closure_rings[1:]):
        for index in range(len(top_ring)):
            following = (index + 1) % len(top_ring)
            face = bm.faces.new(
                (outer[index], outer[following], inner[following], inner[index])
            )
            face.material_index = 0
            face.smooth = True
            closure_quads.append(face)
    closure_faces = bmesh.ops.triangulate(bm, faces=closure_quads)["faces"]

    anchor_target = Vector((-0.005, 0.050, 0.782))
    anchor_candidates = []
    for index in range(body_vertex_count):
        point = transform @ obj.data.vertices[index].co
        if (
            abs(point.x) <= 0.020
            and 0.030 <= point.y <= 0.070
            and 0.770 <= point.z <= 0.795
        ):
            anchor_candidates.append(
                ((point - anchor_target).length_squared, index, point)
            )
    if not anchor_candidates:
        raise RuntimeError("No body vertex available for the closed neck anchor")
    _, anchor_index, anchor_world = min(anchor_candidates)
    bm.verts.ensure_lookup_table()
    cap_center = bm.verts[anchor_index]
    uv_by_vertex[cap_center] = skin_uv
    cap_faces = []
    final_ring = closure_rings[-1]
    for index in range(len(top_ring)):
        following = (index + 1) % len(top_ring)
        face = bm.faces.new((final_ring[index], final_ring[following], cap_center))
        face.material_index = 0
        face.smooth = True
        cap_faces.append(face)

    added_faces = list(tube_faces) + list(closure_faces) + cap_faces
    bmesh.ops.recalc_face_normals(bm, faces=added_faces)
    for face in added_faces:
        face.material_index = 0
        face.smooth = True
        for loop in face.loops:
            loop[uv_layer].uv = uv_by_vertex[loop.vert]

    cut_non_triangles = [
        face for face in bm.faces if face not in added_faces and len(face.verts) != 3
    ]
    if cut_non_triangles:
        bmesh.ops.triangulate(bm, faces=cut_non_triangles)
    surface_edges = {edge for face in added_faces for edge in face.edges}
    added_edges = surface_edges - set(source_edges)
    bm.verts.index_update()
    bottom_indices = [vertex.index for vertex in rings[-1]]
    report = {
        "tube_triangles": len(tube_faces),
        "closure_triangles": len(closure_faces) + len(cap_faces),
        "triangles": len(added_faces),
        "new_vertices": len(top_ring)
        * (NECK_RING_STEPS + CLOSURE_RING_STEPS),
        "ring_steps": NECK_RING_STEPS,
        "closure_ring_steps": CLOSURE_RING_STEPS,
        "bottom_world_z_range": [
            min(point.z for point in outer_bottom_world),
            max(point.z for point in outer_bottom_world),
        ],
        "bottom_world_y_range": [
            min(point.y for point in outer_bottom_world),
            max(point.y for point in outer_bottom_world),
        ],
        "body_anchor_index": anchor_index,
        "body_anchor_world": list(map(float, anchor_world)),
        "body_anchor_target_distance": float((anchor_world - anchor_target).length),
        "max_added_edge": max(edge.calc_length() for edge in added_edges),
        "max_source_edge": max(edge.calc_length() for edge in source_edges),
        "cut_faces_triangulated": len(cut_non_triangles),
    }
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return bottom_indices, report, [anchor_world]


def generated_neck_topology(obj):
    source_group_indices = {
        obj.vertex_groups[name].index
        for name in ("SourceBody", "SourceHead")
        if obj.vertex_groups.get(name) is not None
    }
    generated = set()
    for vertex in obj.data.vertices:
        memberships = {membership.group for membership in vertex.groups}
        if not memberships.intersection(source_group_indices):
            generated.add(vertex.index)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    touching_edges = [
        edge
        for edge in bm.edges
        if any(vertex.index in generated for vertex in edge.verts)
    ]
    report = {
        "generated_vertices": len(generated),
        "touching_edges": len(touching_edges),
        "boundary_edges": sum(edge.is_boundary for edge in touching_edges),
        "non_manifold_edges": sum(not edge.is_manifold for edge in touching_edges),
    }
    bm.free()
    return report


def body_edge_candidates(obj, body_vertex_count):
    transform = obj.matrix_world
    result = []
    for edge in obj.data.edges:
        a_index, b_index = edge.vertices
        if a_index >= body_vertex_count or b_index >= body_vertex_count:
            continue
        a = transform @ obj.data.vertices[a_index].co
        b = transform @ obj.data.vertices[b_index].co
        midpoint = (a + b) * 0.5
        length = (a - b).length
        if not (
            abs(midpoint.x) <= 0.075
            and -0.005 <= midpoint.y <= 0.095
            and 0.715 <= midpoint.z <= 0.755
            and 0.00005 <= length <= 0.008
        ):
            continue
        result.append(
            {
                "vertices": (a_index, b_index),
                "points": (a, b),
                "midpoint": midpoint,
            }
        )
    if not result:
        raise RuntimeError("No body collar edges available for direct neck stitches")
    return result


def add_bottom_stitches(obj, bottom_indices, body_vertex_count, skin_uv):
    candidates = body_edge_candidates(obj, body_vertex_count)
    tree = kdtree.KDTree(len(candidates))
    for index, candidate in enumerate(candidates):
        tree.insert(candidate["midpoint"], index)
    tree.balance()

    transform = obj.matrix_world
    selected = []
    used_body_edges = set()
    stride = len(bottom_indices) / STITCH_COUNT
    for stitch_index in range(STITCH_COUNT):
        ring_index = int(round(stitch_index * stride)) % len(bottom_indices)
        following = (ring_index + 1) % len(bottom_indices)
        h_indices = (bottom_indices[ring_index], bottom_indices[following])
        h_points = tuple(transform @ obj.data.vertices[index].co for index in h_indices)
        midpoint = (h_points[0] + h_points[1]) * 0.5
        choice = None
        for _, candidate_index, _ in tree.find_n(midpoint, min(64, len(candidates))):
            if candidate_index in used_body_edges:
                continue
            candidate = candidates[candidate_index]
            same = (
                (h_points[0] - candidate["points"][0]).length,
                (h_points[1] - candidate["points"][1]).length,
                False,
            )
            flipped = (
                (h_points[0] - candidate["points"][1]).length,
                (h_points[1] - candidate["points"][0]).length,
                True,
            )
            score = same if max(same[:2]) <= max(flipped[:2]) else flipped
            choice = (candidate_index, candidate, score)
            break
        if choice is None:
            raise RuntimeError("Could not assign a unique body edge to every neck stitch")
        used_body_edges.add(choice[0])
        selected.append((h_indices, choice[1], choice[2]))

    wanted_vertices = set()
    for head_edge, body_edge, _ in selected:
        wanted_vertices.update(head_edge)
        wanted_vertices.update(body_edge["vertices"])
    source_uv_layer = obj.data.uv_layers.active
    vertex_uvs = {}
    for polygon in obj.data.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = obj.data.loops[loop_index].vertex_index
            if vertex_index in wanted_vertices and vertex_index not in vertex_uvs:
                vertex_uvs[vertex_index] = source_uv_layer.data[loop_index].uv.copy()
        if len(vertex_uvs) == len(wanted_vertices):
            break
    if len(vertex_uvs) != len(wanted_vertices):
        raise RuntimeError("Missing source UVs for direct collar stitches")

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.verify()
    created = []
    records = []
    body_anchor_points = []
    for head_edge, body_edge, score in selected:
        h0, h1 = (bm.verts[index] for index in head_edge)
        b_indices = list(body_edge["vertices"])
        if score[2]:
            b_indices.reverse()
        b0, b1 = (bm.verts[index] for index in b_indices)
        faces = (bm.faces.new((h0, h1, b1)), bm.faces.new((h0, b1, b0)))
        for face in faces:
            face.material_index = 0
            face.smooth = True
            for loop in face.loops:
                loop[uv_layer].uv = vertex_uvs[loop.vert.index]
        created.extend(faces)
        body_anchor_points.extend(body_edge["points"])
        records.append(
            {
                "tube_vertices": list(head_edge),
                "body_vertices": b_indices,
                "endpoint_distances": list(score[:2]),
            }
        )
    bmesh.ops.recalc_face_normals(bm, faces=created)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return records, body_anchor_points


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 3:
        raise SystemExit("expected CLEAN_BLEND ATLAS_DIR OUTPUT_DIR")
    clean_blend, atlas_dir, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    blend_path = os.path.join(output_dir, "seated_person_detailed_head_closed_fused.blend")
    glb_path = os.path.join(output_dir, "seated_person_detailed_head_closed_fused.glb")
    report_path = os.path.join(output_dir, "closed_fusion_report.json")

    bpy.ops.wm.open_mainfile(filepath=clean_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]
    pitch_head(head)
    cut_head(head)
    removed_body_vertices = delete_old_head_residue(body)
    head_loop_local = ordered_boundary_loop(head)

    body_material = body.material_slots[0].material
    body_material_name = body_material.name
    head_material_name = head.material_slots[0].material.name
    tag_source_vertices(body, "SourceBody")
    tag_source_vertices(head, "SourceHead")
    body_vertex_count = len(body.data.vertices)
    fused = join_objects(body, head)
    head_loop = [body_vertex_count + index for index in head_loop_local]
    head_points = [fused.matrix_world @ fused.data.vertices[index].co for index in head_loop]

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
    _, tube, body_points = add_closed_neck_tube(
        fused, head_loop, body_vertex_count, skin_uv
    )
    if any(polygon.loop_total != 3 for polygon in fused.data.polygons):
        raise RuntimeError("Closed neck fusion contains non-triangle faces")
    neck_topology = generated_neck_topology(fused)
    if neck_topology["boundary_edges"]:
        raise RuntimeError(
            f"Closed neck fusion still has {neck_topology['boundary_edges']} open edges"
        )
    if neck_topology["non_manifold_edges"]:
        raise RuntimeError(
            "Closed neck fusion introduced non-manifold generated edges: "
            f"{neck_topology['non_manifold_edges']}"
        )
    source_connectivity = local_connectivity(fused, head_points, body_points)
    if not source_connectivity["connected"]:
        raise RuntimeError("Closed neck tube is not directly connected to the body")

    fused["fusion_method"] = "closed detailed-head triangle neck fused to body anchor"
    fused["pitch_degrees"] = 6.0
    fused["head_cut_local_z"] = HEAD_CUT_LOCAL_Z
    fused["body_old_head_removal_world_z"] = 0.795
    fused["tube_triangles"] = tube["tube_triangles"]
    fused["closure_triangles"] = tube["closure_triangles"]
    blend_stats = {
        "objects": 1,
        "materials": len(fused.material_slots),
        "vertices": len(fused.data.vertices),
        "edges": len(fused.data.edges),
        "triangles": len(fused.data.polygons),
        "generated_neck_topology": neck_topology,
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
    render_angles = (
        (0, "front"),
        (35, "three_quarter"),
        (90, "side"),
        (120, "rear_120"),
        (145, "rear_145"),
        (180, "back"),
    )
    for angle, name in render_angles:
        if angle in {0, 35, 90, 180}:
            render(
                os.path.join(output_dir, f"full_{name}.png"),
                full_center,
                full_scale,
                angle,
                800,
            )
        render(os.path.join(output_dir, f"head_{name}.png"), head_center, 0.40, angle, 1000)

    report = {
        "sources_unchanged": True,
        "outputs": {"blend": blend_path, "glb": glb_path},
        "alignment": {"pitch_degrees": 6.0},
        "cuts": {
            "head_local_z": HEAD_CUT_LOCAL_Z,
            "body_old_head_removal_world_z": 0.795,
            "body_lower_neck_preserved": True,
            "body_removed_vertices": removed_body_vertices,
        },
        "head_loop_vertices": len(head_loop),
        "tube": tube,
        "attachment": {
            "method": "closed triangle surface sharing a body mesh vertex",
            "body_anchor_world": tube["body_anchor_world"],
            "target_distance": tube["body_anchor_target_distance"],
        },
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
