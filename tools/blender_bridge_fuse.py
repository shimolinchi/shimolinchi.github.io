import bpy
import bmesh
import json
import math
import os
import sys

import numpy as np
from mathutils import Vector, kdtree


RING_SEGMENTS = 64
HEAD_CUT_LOCAL_Z = 0.33
HEAD_CENTER_LOCAL = Vector((0.015, -0.055, HEAD_CUT_LOCAL_Z + 0.004))
HEAD_RADII_LOCAL = (0.13, 0.215)
BODY_CENTER_WORLD = Vector((-0.001, 0.024, 0.755))
BODY_RADII_WORLD = (0.050, 0.057)


def delete_head_below_cut(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    count = 0
    for vertex in obj.data.vertices:
        vertex.select = vertex.co.z < HEAD_CUT_LOCAL_Z
        count += int(vertex.select)
    obj.data.update()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    obj.data.update()
    return count


def head_boundary_candidates(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    indices = set()
    for edge in bm.edges:
        if not edge.is_boundary:
            continue
        for vertex in edge.verts:
            point = vertex.co
            if (
                HEAD_CUT_LOCAL_Z <= point.z <= HEAD_CUT_LOCAL_Z + 0.035
                and -0.16 <= point.x <= 0.19
                and -0.31 <= point.y <= 0.19
            ):
                indices.add(vertex.index)
    bm.free()
    return sorted(indices)


def body_collar_candidates(obj):
    indices = []
    transform = obj.matrix_world
    for vertex in obj.data.vertices:
        point = transform @ vertex.co
        if (
            0.715 <= point.z <= 0.795
            and -0.10 <= point.x <= 0.10
            and -0.055 <= point.y <= 0.125
        ):
            indices.append(vertex.index)
    return indices


def choose_ring(obj, candidate_indices, targets, coordinates="LOCAL"):
    if len(candidate_indices) < len(targets):
        raise RuntimeError(f"Only {len(candidate_indices)} ring candidates for {len(targets)} targets")
    tree = kdtree.KDTree(len(candidate_indices))
    transform = obj.matrix_world
    for slot, index in enumerate(candidate_indices):
        point = obj.data.vertices[index].co
        if coordinates == "WORLD":
            point = transform @ point
        tree.insert(point, slot)
    tree.balance()
    used = set()
    result = []
    for target in targets:
        choices = tree.find_n(target, min(128, len(candidate_indices)))
        selected_slot = next((slot for _, slot, _ in choices if slot not in used), None)
        if selected_slot is None:
            raise RuntimeError("Could not choose unique ring vertices")
        used.add(selected_slot)
        result.append(candidate_indices[selected_slot])
    return result


def ellipse_targets(center, radii, count):
    return [
        Vector(
            (
                center.x + radii[0] * math.cos(2 * math.pi * index / count),
                center.y + radii[1] * math.sin(2 * math.pi * index / count),
                center.z,
            )
        )
        for index in range(count)
    ]


def vertex_uvs(obj, vertex_indices):
    uv_layer = obj.data.uv_layers.active
    if uv_layer is None:
        raise RuntimeError(f"No active UV layer on {obj.name}")
    wanted = set(vertex_indices)
    found = {}
    for polygon in obj.data.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = obj.data.loops[loop_index].vertex_index
            if vertex_index in wanted and vertex_index not in found:
                found[vertex_index] = uv_layer.data[loop_index].uv.copy()
        if len(found) == len(wanted):
            break
    if len(found) != len(wanted):
        missing = wanted - set(found)
        raise RuntimeError(f"Missing UVs for {len(missing)} head ring vertices")
    return [found[index] for index in vertex_indices]


def choose_skin_uv(texture_path, uvs):
    image = bpy.data.images.load(texture_path, check_existing=False)
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape((height, width, 4))
    candidates = []
    for uv in uvs:
        x = max(0, min(width - 1, int((uv.x % 1.0) * (width - 1))))
        y = max(0, min(height - 1, int((uv.y % 1.0) * (height - 1))))
        red, green, blue = pixels[y, x, :3]
        score = float((red - green) + (red - blue))
        brightness = float((red + green + blue) / 3)
        if red > green > blue and red - blue > 0.06 and brightness > 0.08:
            candidates.append((score, uv.copy(), [float(red), float(green), float(blue)]))
    if not candidates:
        return uvs[0].copy(), None
    candidates.sort(key=lambda item: item[0])
    _, uv, color = candidates[len(candidates) // 2]
    return uv, color


def join_objects(body, head):
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    head.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = "SeatedPerson_DetailedHead_Fused"
    body.data.name = "SeatedPerson_DetailedHead_Fused_Mesh"
    return body


def nearest_vertex_indices(obj, world_positions):
    tree = kdtree.KDTree(len(obj.data.vertices))
    transform = obj.matrix_world
    for index, vertex in enumerate(obj.data.vertices):
        tree.insert(transform @ vertex.co, index)
    tree.balance()
    result = []
    for position in world_positions:
        _, index, distance = tree.find(position)
        if distance > 0.00002:
            raise RuntimeError(f"Joined vertex drifted by {distance}")
        result.append(index)
    return result


def verify_joined_indices(obj, indices, positions):
    transform = obj.matrix_world
    for index, position in zip(indices, positions):
        distance = (transform @ obj.data.vertices[index].co - position).length
        if distance > 0.00002:
            raise RuntimeError(f"Joined vertex index drifted by {distance}")


def add_bridge(
    obj,
    head_indices,
    body_indices,
    smooth_head_positions,
    smooth_body_positions,
    skin_uv,
    material_index,
):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.verify()
    head_ring = [bm.verts[index] for index in head_indices]
    body_ring = [bm.verts[index] for index in body_indices]
    inverse = obj.matrix_world.inverted()
    smooth_head_ring = [bm.verts.new(inverse @ point) for point in smooth_head_positions]
    smooth_body_ring = [bm.verts.new(inverse @ point) for point in smooth_body_positions]

    rings = [head_ring, smooth_head_ring]
    for t in (1 / 3, 2 / 3):
        ring = []
        for upper, lower in zip(smooth_head_ring, smooth_body_ring):
            point = upper.co.lerp(lower.co, t)
            ring.append(bm.verts.new(point))
        rings.append(ring)
    rings.extend((smooth_body_ring, body_ring))
    bm.verts.index_update()

    created_faces = []
    for upper, lower in zip(rings[:-1], rings[1:]):
        for index in range(len(upper)):
            next_index = (index + 1) % len(upper)
            face = bm.faces.new(
                (upper[index], lower[index], lower[next_index], upper[next_index])
            )
            face.material_index = material_index
            for loop in face.loops:
                loop[uv_layer].uv = skin_uv
            created_faces.append(face)
    bmesh.ops.triangulate(bm, faces=created_faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return len(created_faces) * 2


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 4:
        raise SystemExit("expected INPUT_BLEND TEXTURE_PREVIEW OUTPUT_BLEND REPORT_JSON")
    input_blend, texture_path, output_blend, report_path = map(os.path.abspath, argv)
    bpy.ops.wm.open_mainfile(filepath=input_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]
    removed_head_vertices = delete_head_below_cut(head)

    head_candidates = head_boundary_candidates(head)
    body_candidates = body_collar_candidates(body)
    head_targets = ellipse_targets(HEAD_CENTER_LOCAL, HEAD_RADII_LOCAL, RING_SEGMENTS)
    body_targets = ellipse_targets(BODY_CENTER_WORLD, BODY_RADII_WORLD, RING_SEGMENTS)
    head_ring_local = choose_ring(head, head_candidates, head_targets, "LOCAL")
    body_ring_local = choose_ring(body, body_candidates, body_targets, "WORLD")
    head_uvs = vertex_uvs(head, head_ring_local)
    skin_uv, sampled_color = choose_skin_uv(texture_path, head_uvs)
    head_positions = [head.matrix_world @ head.data.vertices[index].co for index in head_ring_local]
    body_positions = [body.matrix_world @ body.data.vertices[index].co for index in body_ring_local]
    smooth_head_positions = [head.matrix_world @ target for target in head_targets]
    smooth_body_positions = body_targets

    head_material_name = head.material_slots[0].material.name
    body_vertex_count = len(body.data.vertices)
    fused = join_objects(body, head)
    material_index = next(
        index
        for index, slot in enumerate(fused.material_slots)
        if slot.material and slot.material.name == head_material_name
    )
    body_indices = body_ring_local
    head_indices = [body_vertex_count + index for index in head_ring_local]
    verify_joined_indices(fused, body_indices, body_positions)
    verify_joined_indices(fused, head_indices, head_positions)
    bridge_triangles = add_bridge(
        fused,
        head_indices,
        body_indices,
        smooth_head_positions,
        smooth_body_positions,
        skin_uv,
        material_index,
    )
    fused["fusion_method"] = "explicit welded neck triangle bridge"
    fused["bridge_segments"] = RING_SEGMENTS
    fused["bridge_triangles"] = bridge_triangles

    report = {
        "fusion_method": "explicit welded neck triangle bridge",
        "removed_head_vertices_below_cut": removed_head_vertices,
        "head_boundary_candidates": len(head_candidates),
        "body_collar_candidates": len(body_candidates),
        "ring_segments": RING_SEGMENTS,
        "bridge_triangles": bridge_triangles,
        "sampled_skin_uv": [float(skin_uv.x), float(skin_uv.y)],
        "sampled_skin_linear_rgb": sampled_color,
        "final": {
            "objects": 1,
            "vertices": len(fused.data.vertices),
            "edges": len(fused.data.edges),
            "polygons": len(fused.data.polygons),
            "materials": [slot.material.name if slot.material else None for slot in fused.material_slots],
        },
        "head_ring_world": [[float(value) for value in point] for point in head_positions],
        "body_ring_world": [[float(value) for value in point] for point in body_positions],
    }
    os.makedirs(os.path.dirname(output_blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
