import bpy
import bmesh
import json
import math
import os
import sys
from collections import defaultdict, deque
from mathutils import Vector, kdtree


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import bounds, import_glb, render
from blender_hidden_collar_fuse import (
    build_atlas_material,
    join_objects,
    remap_uvs_to_atlas,
    tag_source_vertices,
)


SEGMENTS = 96
BODY_CUT_Z = 0.780
HEAD_CUT_LOCAL_Z = 0.330
PITCH_DEGREES = 6.0
PITCH_PIVOT_WORLD = Vector((-0.001, 0.015, 0.855))
HEAD_CENTER_LOCAL = Vector((0.015, -0.055, 0.331))
HEAD_RADII_LOCAL = (0.130, 0.215)
BODY_CENTER_WORLD = Vector((0.001, 0.029, 0.7790))
BODY_RADII_WORLD = (0.080, 0.070)


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


def apply_pitch_correction(head):
    from mathutils import Matrix

    pivot = Matrix.Translation(PITCH_PIVOT_WORLD)
    inverse = Matrix.Translation(-PITCH_PIVOT_WORLD)
    rotation = Matrix.Rotation(math.radians(PITCH_DEGREES), 4, "X")
    head.matrix_world = pivot @ rotation @ inverse @ head.matrix_world


def boundary_candidates(obj, source):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    transform = obj.matrix_world
    indices = set()
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        for vertex in edge.verts:
            world = transform @ vertex.co
            if source == "head":
                keep = (
                    HEAD_CUT_LOCAL_Z <= vertex.co.z <= HEAD_CUT_LOCAL_Z + 0.010
                    and abs(world.x) <= 0.060
                    and -0.070 <= world.y <= 0.100
                )
            else:
                keep = (
                    0.775 <= world.z <= BODY_CUT_Z + 0.0001
                    and abs(world.x) <= 0.115
                    and -0.065 <= world.y <= 0.125
                )
            if keep:
                indices.add(vertex.index)
    bm.free()
    return sorted(indices)


def ellipse_targets(center, radii, count, transform=None):
    result = []
    for index in range(count):
        angle = 2.0 * math.pi * index / count
        point = Vector(
            (
                center.x + radii[0] * math.cos(angle),
                center.y + radii[1] * math.sin(angle),
                center.z,
            )
        )
        result.append(transform @ point if transform is not None else point)
    return result


def choose_unique_ring(obj, candidate_indices, targets):
    transform = obj.matrix_world
    unique = {}
    for index in candidate_indices:
        point = transform @ obj.data.vertices[index].co
        key = tuple(round(float(value), 5) for value in point)
        if key not in unique:
            unique[key] = (index, point)
    candidates = list(unique.values())
    if len(candidates) < len(targets):
        raise RuntimeError(f"Only {len(candidates)} unique boundary points for {len(targets)} targets")
    tree = kdtree.KDTree(len(candidates))
    for slot, (_, point) in enumerate(candidates):
        tree.insert(point, slot)
    tree.balance()

    used = set()
    ring = []
    distances = []
    for target in targets:
        selected = None
        for point, slot, distance in tree.find_n(target, min(512, len(candidates))):
            if slot not in used:
                selected = (slot, distance)
                break
        if selected is None:
            raise RuntimeError("Could not select a unique boundary ring")
        slot, distance = selected
        used.add(slot)
        ring.append(candidates[slot][0])
        distances.append(distance)
    return ring, distances


def representative_vertex_uvs(obj, vertex_indices):
    wanted = set(vertex_indices)
    uv_layer = obj.data.uv_layers.active
    result = {}
    for polygon in obj.data.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = obj.data.loops[loop_index].vertex_index
            if vertex_index in wanted and vertex_index not in result:
                result[vertex_index] = uv_layer.data[loop_index].uv.copy()
        if len(result) == len(wanted):
            break
    if len(result) != len(wanted):
        raise RuntimeError(f"Missing UVs for {len(wanted - set(result))} boundary vertices")
    return result


def add_neck_bridge(
    obj,
    head_indices,
    body_indices,
    head_targets,
    body_targets,
    source_uvs,
    skin_uv,
):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.verify()
    inverse = obj.matrix_world.inverted()
    source_head = [bm.verts[index] for index in head_indices]
    source_body = [bm.verts[index] for index in body_indices]
    smooth_head = [bm.verts.new(inverse @ point) for point in head_targets]
    smooth_body = [bm.verts.new(inverse @ point) for point in body_targets]
    middle_rings = []
    for factor in (0.25, 0.50, 0.75):
        ring = []
        for upper, lower in zip(smooth_head, smooth_body):
            ring.append(bm.verts.new(upper.co.lerp(lower.co, factor)))
        middle_rings.append(ring)
    rings = [source_head, smooth_head, *middle_rings, smooth_body, source_body]
    bm.verts.index_update()
    new_vertex_indices = {
        vertex.index
        for ring in [smooth_head, *middle_rings, smooth_body]
        for vertex in ring
    }
    created = []
    max_edge_length = 0.0
    for upper, lower in zip(rings[:-1], rings[1:]):
        for index in range(SEGMENTS):
            next_index = (index + 1) % SEGMENTS
            face = bm.faces.new(
                (upper[index], upper[next_index], lower[next_index], lower[index])
            )
            face.material_index = 0
            face.smooth = True
            for loop in face.loops:
                if loop.vert.index in source_uvs:
                    loop[uv_layer].uv = source_uvs[loop.vert.index]
                else:
                    loop[uv_layer].uv = skin_uv
            created.append(face)
            for edge in face.edges:
                max_edge_length = max(max_edge_length, edge.calc_length())
    triangulated = bmesh.ops.triangulate(bm, faces=created)["faces"]
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return {
        "quads_before_triangulation": len(created),
        "triangles": len(triangulated),
        "new_vertices": len(new_vertex_indices),
        "max_bridge_edge_length": max_edge_length,
    }


def bridge_connectivity(obj, head_indices, body_indices):
    head = set(head_indices)
    body = set(body_indices)
    adjacency = defaultdict(set)
    bridge_vertex_start = min(len(obj.data.vertices), max(max(head), max(body)) + 1)
    relevant = head | body | set(range(bridge_vertex_start, len(obj.data.vertices)))
    for edge in obj.data.edges:
        a, b = edge.vertices
        if a in relevant and b in relevant:
            adjacency[a].add(b)
            adjacency[b].add(a)
    queue = deque(head)
    reached = set(head)
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in reached:
                reached.add(neighbor)
                queue.append(neighbor)
    return {
        "head_anchor_vertices": len(head),
        "body_anchor_vertices": len(body),
        "body_anchors_reached": len(body & reached),
        "connected": bool(body & reached),
    }


def quantized(point, digits=5):
    return tuple(round(float(value), digits) for value in point)


def verify_reimport(glb_path, head_points, body_points):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one re-imported mesh, got {len(meshes)}")
    obj = meshes[0]
    if len(obj.material_slots) != 1:
        raise RuntimeError(f"Expected one re-imported material, got {len(obj.material_slots)}")
    if any(polygon.loop_total != 3 for polygon in obj.data.polygons):
        raise RuntimeError("Re-imported GLB contains non-triangle faces")

    head_keys = {quantized(point) for point in head_points}
    body_keys = {quantized(point) for point in body_points}
    key_by_index = [quantized(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices]
    start_vertices = {index for index, key in enumerate(key_by_index) if key in head_keys}
    target_vertices = {index for index, key in enumerate(key_by_index) if key in body_keys}
    relevant = set()
    for index, vertex in enumerate(obj.data.vertices):
        point = obj.matrix_world @ vertex.co
        if abs(point.x) <= 0.12 and -0.08 <= point.y <= 0.13 and 0.755 <= point.z <= 0.805:
            relevant.add(index)
    adjacency = defaultdict(set)
    for edge in obj.data.edges:
        a, b = edge.vertices
        if a in relevant and b in relevant:
            adjacency[a].add(b)
            adjacency[b].add(a)
    queue = deque(start_vertices & relevant)
    reached = set(queue)
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in reached:
                reached.add(neighbor)
                queue.append(neighbor)
    reached_targets = target_vertices & reached
    return obj, {
        "objects": 1,
        "materials": 1,
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "triangles": len(obj.data.polygons),
        "head_anchor_coordinate_vertices": len(start_vertices),
        "body_anchor_coordinate_vertices": len(target_vertices),
        "body_anchor_vertices_reached": len(reached_targets),
        "neck_connected": bool(reached_targets),
    }


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 4:
        raise SystemExit("expected CLEAN_BLEND ORIGINAL_BODY_GLB ATLAS_DIR OUTPUT_DIR")
    clean_blend, body_glb, atlas_dir, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    blend_path = os.path.join(output_dir, "seated_person_clean_neck_fused.blend")
    glb_path = os.path.join(output_dir, "seated_person_clean_neck_fused.glb")
    report_path = os.path.join(output_dir, "clean_neck_report.json")

    bpy.ops.wm.open_mainfile(filepath=clean_blend)
    old_body = bpy.data.objects["BodyAndChair_Cut"]
    bpy.data.objects.remove(old_body, do_unlink=True)
    body = import_glb(body_glb, "BodyPlaneCut")
    head = bpy.data.objects["DetailedHead"]
    apply_pitch_correction(head)
    body_material = body.material_slots[0].material
    body_material_name = body_material.name
    head_material_name = head.material_slots[0].material.name

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
    head_candidates = boundary_candidates(head, "head")
    body_candidates = boundary_candidates(body, "body")
    head_targets = ellipse_targets(
        HEAD_CENTER_LOCAL, HEAD_RADII_LOCAL, SEGMENTS, head.matrix_world
    )
    body_targets = ellipse_targets(BODY_CENTER_WORLD, BODY_RADII_WORLD, SEGMENTS)
    head_ring_local, head_distances = choose_unique_ring(head, head_candidates, head_targets)
    body_ring_local, body_distances = choose_unique_ring(body, body_candidates, body_targets)
    head_points = [head.matrix_world @ head.data.vertices[index].co for index in head_ring_local]
    body_points = [body.matrix_world @ body.data.vertices[index].co for index in body_ring_local]

    tag_source_vertices(body, "SourceBody")
    tag_source_vertices(head, "SourceHead")
    body_vertex_count = len(body.data.vertices)
    fused = join_objects(body, head)
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
    remapped = remap_uvs_to_atlas(fused, body_material_index, head_material_index)
    head_ring = [body_vertex_count + index for index in head_ring_local]
    body_ring = body_ring_local
    source_uvs = representative_vertex_uvs(fused, head_ring + body_ring)
    skin_uv = Vector((0.5 + 0.5 * 0.73388671875, 0.6328125))
    atlas_material, replacements = build_atlas_material(body_material, atlas_dir)
    for polygon in fused.data.polygons:
        polygon.material_index = 0
    fused.data.materials.clear()
    fused.data.materials.append(atlas_material)
    bridge = add_neck_bridge(
        fused,
        head_ring,
        body_ring,
        head_targets,
        body_targets,
        source_uvs,
        skin_uv,
    )
    connectivity = bridge_connectivity(fused, head_ring, body_ring)
    if not connectivity["connected"]:
        raise RuntimeError("Neck bridge did not connect head and body anchors")
    if any(polygon.loop_total != 3 for polygon in fused.data.polygons):
        raise RuntimeError("Fused blend contains non-triangle faces")
    fused["fusion_method"] = "clean plane cuts plus resampled neck triangle bridge"
    fused["bridge_segments"] = SEGMENTS
    fused["bridge_triangles"] = bridge["triangles"]
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    blend_stats = {
        "objects": 1,
        "materials": len(fused.material_slots),
        "vertices": len(fused.data.vertices),
        "edges": len(fused.data.edges),
        "triangles": len(fused.data.polygons),
    }

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
    imported, reimport = verify_reimport(glb_path, head_points, body_points)
    if not reimport["neck_connected"]:
        raise RuntimeError("GLB re-import lost the head/body neck connection")

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
        "fusion_method": "clean plane cuts plus resampled neck triangle bridge",
        "cuts": {
            "body_cut_world_z": BODY_CUT_Z,
            "body_removed_vertices": body_removed,
            "head_cut_local_z": HEAD_CUT_LOCAL_Z,
            "head_removed_vertices": head_removed,
        },
        "alignment_correction": {
            "pitch_degrees": PITCH_DEGREES,
            "pivot_world": list(PITCH_PIVOT_WORLD),
        },
        "boundary_candidates": {"head": len(head_candidates), "body": len(body_candidates)},
        "ring_fit": {
            "head_mean_distance": sum(head_distances) / len(head_distances),
            "head_max_distance": max(head_distances),
            "body_mean_distance": sum(body_distances) / len(body_distances),
            "body_max_distance": max(body_distances),
        },
        "bridge": bridge,
        "blend_connectivity": connectivity,
        "uv_atlas": {"remapped_faces": remapped, "texture_replacements": replacements},
        "blend": blend_stats,
        "glb_reimport": reimport,
    }
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
