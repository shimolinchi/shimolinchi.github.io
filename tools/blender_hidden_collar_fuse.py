import bpy
import bmesh
import json
import math
import os
import sys
from mathutils import Vector, kdtree


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import bounds, render


STITCH_COUNT = 12
REGION = {
    "x_abs_max": 0.070,
    "y_min": 0.018,
    "y_max": 0.095,
    "z_min": 0.735,
    "z_max": 0.790,
}


def argv_after_double_dash():
    if "--" not in sys.argv:
        raise SystemExit(
            "usage: blender --background --python script.py -- INPUT_BLEND ATLAS_DIR OUTPUT_DIR"
        )
    return sys.argv[sys.argv.index("--") + 1 :]


def tag_source_vertices(obj, group_name):
    group = obj.vertex_groups.new(name=group_name)
    chunk = 100000
    for start in range(0, len(obj.data.vertices), chunk):
        group.add(range(start, min(start + chunk, len(obj.data.vertices))), 1.0, "REPLACE")


def join_objects(body, head):
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    head.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = "SeatedPerson_DetailedHead_Fused"
    body.data.name = "SeatedPerson_DetailedHead_Fused_Mesh"
    return body


def in_hidden_collar(point):
    return (
        abs(point.x) <= REGION["x_abs_max"]
        and REGION["y_min"] <= point.y <= REGION["y_max"]
        and REGION["z_min"] <= point.z <= REGION["z_max"]
    )


def candidate_edges(obj, body_vertex_count):
    transform = obj.matrix_world
    body_edges = []
    head_edges = []
    for edge in obj.data.edges:
        a_index, b_index = edge.vertices
        is_body = a_index < body_vertex_count and b_index < body_vertex_count
        is_head = a_index >= body_vertex_count and b_index >= body_vertex_count
        if not (is_body or is_head):
            continue
        a = transform @ obj.data.vertices[a_index].co
        b = transform @ obj.data.vertices[b_index].co
        midpoint = (a + b) * 0.5
        length = (a - b).length
        if not in_hidden_collar(midpoint) or not 0.00005 <= length <= 0.006:
            continue
        record = {
            "vertices": (a_index, b_index),
            "points": (a, b),
            "midpoint": midpoint,
            "length": length,
        }
        (body_edges if is_body else head_edges).append(record)
    return body_edges, head_edges


def paired_edge_score(head_edge, body_edge):
    h0, h1 = head_edge["points"]
    b0, b1 = body_edge["points"]
    same = ((h0 - b0).length, (h1 - b1).length, False)
    flipped = ((h0 - b1).length, (h1 - b0).length, True)
    first, second, flip = same if max(same[:2]) <= max(flipped[:2]) else flipped
    h_direction = (h1 - h0).normalized()
    b_direction = ((b0 - b1) if flip else (b1 - b0)).normalized()
    orientation_penalty = 0.0015 * (1.0 - abs(h_direction.dot(b_direction)))
    length_penalty = 0.25 * abs(head_edge["length"] - body_edge["length"])
    return max(first, second) + orientation_penalty + length_penalty, flip, first, second


def choose_stitches(body_edges, head_edges):
    if not body_edges or not head_edges:
        raise RuntimeError(
            f"No collar candidates: body edges={len(body_edges)}, head edges={len(head_edges)}"
        )
    tree = kdtree.KDTree(len(body_edges))
    for index, edge in enumerate(body_edges):
        tree.insert(edge["midpoint"], index)
    tree.balance()

    candidates = []
    for head_index, head_edge in enumerate(head_edges):
        for _, body_index, midpoint_distance in tree.find_n(head_edge["midpoint"], 12):
            body_edge = body_edges[body_index]
            score, flip, distance_a, distance_b = paired_edge_score(head_edge, body_edge)
            candidates.append(
                {
                    "score": score,
                    "head_index": head_index,
                    "body_index": body_index,
                    "flip": flip,
                    "endpoint_distances": (distance_a, distance_b),
                    "midpoint_distance": midpoint_distance,
                }
            )
    candidates.sort(key=lambda item: item["score"])

    thresholds = (0.0025, 0.0035, 0.0050, 0.0075, 0.0100)
    for threshold in thresholds:
        selected = []
        used_vertices = set()
        used_midpoints = []
        for candidate in candidates:
            if candidate["score"] > threshold:
                break
            head_edge = head_edges[candidate["head_index"]]
            body_edge = body_edges[candidate["body_index"]]
            vertices = set(head_edge["vertices"] + body_edge["vertices"])
            midpoint = (head_edge["midpoint"] + body_edge["midpoint"]) * 0.5
            if vertices & used_vertices:
                continue
            if any((midpoint - existing).length < 0.004 for existing in used_midpoints):
                continue
            selected.append((candidate, head_edge, body_edge))
            used_vertices.update(vertices)
            used_midpoints.append(midpoint)
            if len(selected) == STITCH_COUNT:
                return selected, threshold, len(candidates)
    raise RuntimeError(
        f"Only {len(selected)} well-spaced stitch pairs found; need {STITCH_COUNT}"
    )


def remap_uvs_to_atlas(obj, body_material_index, head_material_index):
    uv_layer = obj.data.uv_layers.active
    if uv_layer is None:
        raise RuntimeError("Fused mesh has no UV map")
    body_faces = 0
    head_faces = 0
    for polygon in obj.data.polygons:
        if polygon.material_index == body_material_index:
            body_faces += 1
            offset = 0.0
        elif polygon.material_index == head_material_index:
            head_faces += 1
            offset = 0.5
        else:
            raise RuntimeError(f"Unexpected source material index {polygon.material_index}")
        for loop_index in polygon.loop_indices:
            uv = uv_layer.data[loop_index].uv
            uv.x = offset + 0.5 * uv.x
    return {"body_faces": body_faces, "head_faces": head_faces}


def stitch_edge_vertex_uvs(obj, stitches):
    wanted_edges = set()
    for _, head_edge, body_edge in stitches:
        wanted_edges.add(tuple(sorted(head_edge["vertices"])))
        wanted_edges.add(tuple(sorted(body_edge["vertices"])))
    uv_layer = obj.data.uv_layers.active
    edge_uvs = {}
    for polygon in obj.data.polygons:
        vertices = list(polygon.vertices)
        for offset in range(len(vertices)):
            a = vertices[offset]
            b = vertices[(offset + 1) % len(vertices)]
            signature = tuple(sorted((a, b)))
            if signature not in wanted_edges or signature in edge_uvs:
                continue
            loop_by_vertex = {
                obj.data.loops[loop_index].vertex_index: uv_layer.data[loop_index].uv.copy()
                for loop_index in polygon.loop_indices
            }
            edge_uvs[signature] = {a: loop_by_vertex[a], b: loop_by_vertex[b]}
        if len(edge_uvs) == len(wanted_edges):
            break
    if len(edge_uvs) != len(wanted_edges):
        raise RuntimeError(f"Missing UVs for {len(wanted_edges - set(edge_uvs))} stitch edges")

    result = {}
    for signature, values in edge_uvs.items():
        for vertex_index, uv in values.items():
            if vertex_index in result and (result[vertex_index] - uv).length > 1e-6:
                raise RuntimeError(f"Stitch vertex {vertex_index} was unexpectedly reused")
            result[vertex_index] = uv
    return result


def texture_kind(image_name):
    lowered = image_name.lower()
    if "basecolor" in lowered:
        return "basecolor"
    if "normal" in lowered:
        return "normal"
    if "_rm" in lowered or lowered.endswith("rm.jpg"):
        return "rm"
    return None


def build_atlas_material(source_material, atlas_dir):
    material = source_material.copy()
    material.name = "SeatedPerson_DetailedHead_Atlas"
    paths = {
        "basecolor": os.path.join(atlas_dir, "atlas_basecolor.jpg"),
        "normal": os.path.join(atlas_dir, "atlas_normal.jpg"),
        "rm": os.path.join(atlas_dir, "atlas_rm.jpg"),
    }
    images = {
        kind: bpy.data.images.load(path, check_existing=False) for kind, path in paths.items()
    }
    images["basecolor"].colorspace_settings.name = "sRGB"
    images["normal"].colorspace_settings.name = "Non-Color"
    images["rm"].colorspace_settings.name = "Non-Color"

    replacements = {}
    for node in material.node_tree.nodes:
        if node.type != "TEX_IMAGE" or node.image is None:
            continue
        kind = texture_kind(node.image.name)
        if kind:
            node.image = images[kind]
            replacements[kind] = replacements.get(kind, 0) + 1
    missing = set(paths) - set(replacements)
    if missing:
        raise RuntimeError(f"Atlas material did not replace texture nodes: {sorted(missing)}")
    return material, replacements


def add_stitch_triangles(obj, stitches, vertex_uvs):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.verify()
    records = []
    created = []
    transform = obj.matrix_world

    for candidate, head_edge, body_edge in stitches:
        h0_index, h1_index = head_edge["vertices"]
        b0_index, b1_index = body_edge["vertices"]
        if candidate["flip"]:
            b0_index, b1_index = b1_index, b0_index
        h0, h1 = bm.verts[h0_index], bm.verts[h1_index]
        b0, b1 = bm.verts[b0_index], bm.verts[b1_index]
        face_a = bm.faces.new((h0, h1, b1))
        face_b = bm.faces.new((h0, b1, b0))
        for face in (face_a, face_b):
            face.material_index = 0
            face.smooth = True
            for loop in face.loops:
                loop[uv_layer].uv = vertex_uvs[loop.vert.index]
        created.extend((face_a, face_b))
        records.append(
            {
                "head_vertices": (h0_index, h1_index),
                "body_vertices": (b0_index, b1_index),
                "head_edge_world": [list(transform @ h0.co), list(transform @ h1.co)],
                "body_edge_world": [list(transform @ b0.co), list(transform @ b1.co)],
                "endpoint_distances": list(candidate["endpoint_distances"]),
                "score": candidate["score"],
            }
        )

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return records, len(created)


def count_cross_source_triangles(obj):
    body_group = obj.vertex_groups["SourceBody"].index
    head_group = obj.vertex_groups["SourceHead"].index
    body_vertices = set()
    head_vertices = set()
    for vertex in obj.data.vertices:
        groups = {membership.group for membership in vertex.groups}
        if body_group in groups:
            body_vertices.add(vertex.index)
        if head_group in groups:
            head_vertices.add(vertex.index)
    mixed = 0
    for polygon in obj.data.polygons:
        vertices = set(polygon.vertices)
        if vertices & body_vertices and vertices & head_vertices:
            mixed += 1
    return mixed


def quantized_point(point, digits=5):
    return tuple(round(float(value), digits) for value in point)


def edge_signature(points):
    return tuple(sorted(quantized_point(Vector(point)) for point in points))


def verify_reimport(glb_path, stitch_records):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Re-import expected one mesh object, got {len(meshes)}")
    obj = meshes[0]
    if len(obj.material_slots) != 1:
        raise RuntimeError(f"Re-import expected one material, got {len(obj.material_slots)}")
    non_triangles = sum(polygon.loop_total != 3 for polygon in obj.data.polygons)
    if non_triangles:
        raise RuntimeError(f"Re-import contains {non_triangles} non-triangle faces")

    wanted_head = {edge_signature(record["head_edge_world"]) for record in stitch_records}
    wanted_body = {edge_signature(record["body_edge_world"]) for record in stitch_records}
    connected_head = set()
    connected_body = set()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    transform = obj.matrix_world
    for edge in bm.edges:
        if len(edge.link_faces) < 2:
            continue
        signature = tuple(
            sorted(quantized_point(transform @ vertex.co) for vertex in edge.verts)
        )
        if signature in wanted_head:
            connected_head.add(signature)
        if signature in wanted_body:
            connected_body.add(signature)
    bm.free()
    return obj, {
        "objects": 1,
        "materials": 1,
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "triangles": len(obj.data.polygons),
        "head_anchor_edges_shared": len(connected_head),
        "body_anchor_edges_shared": len(connected_body),
        "stitches": len(stitch_records),
    }


def main():
    argv = argv_after_double_dash()
    if len(argv) != 3:
        raise SystemExit("expected INPUT_BLEND ATLAS_DIR OUTPUT_DIR")
    input_blend, atlas_dir, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    blend_path = os.path.join(output_dir, "seated_person_detailed_head_fused.blend")
    glb_path = os.path.join(output_dir, "seated_person_detailed_head_fused_final.glb")
    report_path = os.path.join(output_dir, "fusion_report.json")

    bpy.ops.wm.open_mainfile(filepath=input_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]
    body_material = body.material_slots[0].material
    body_material_name = body_material.name
    head_material_name = head.material_slots[0].material.name
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
    uv_remap = remap_uvs_to_atlas(fused, body_material_index, head_material_index)
    body_edges, head_edges = candidate_edges(fused, body_vertex_count)
    stitches, selected_threshold, evaluated_pairs = choose_stitches(body_edges, head_edges)
    vertex_uvs = stitch_edge_vertex_uvs(fused, stitches)

    atlas_material, texture_replacements = build_atlas_material(body_material, atlas_dir)
    for polygon in fused.data.polygons:
        polygon.material_index = 0
    fused.data.materials.clear()
    fused.data.materials.append(atlas_material)
    stitch_records, bridge_triangles = add_stitch_triangles(fused, stitches, vertex_uvs)
    mixed_triangles = count_cross_source_triangles(fused)
    if mixed_triangles != bridge_triangles:
        raise RuntimeError(
            f"Expected {bridge_triangles} cross-source triangles, found {mixed_triangles}"
        )
    if any(polygon.loop_total != 3 for polygon in fused.data.polygons):
        raise RuntimeError("Fused source mesh contains non-triangle faces")

    fused["fusion_method"] = "hidden collar cross-source triangle stitches"
    fused["cross_source_triangles"] = mixed_triangles
    fused["stitch_count"] = len(stitch_records)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    source_blend_stats = {
        "objects": 1,
        "materials": len(fused.material_slots),
        "vertices": len(fused.data.vertices),
        "edges": len(fused.data.edges),
        "triangles": len(fused.data.polygons),
    }

    bpy.ops.object.select_all(action="DESELECT")
    fused.select_set(True)
    bpy.context.view_layer.objects.active = fused
    temporary_glb = os.path.join(output_dir, "seated_person_detailed_head_fused_final_new.glb")
    if os.path.exists(temporary_glb):
        os.remove(temporary_glb)
    bpy.ops.export_scene.gltf(
        filepath=temporary_glb,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_attributes=False,
        export_normals=False,
    )
    os.replace(temporary_glb, glb_path)

    imported, reimport = verify_reimport(glb_path, stitch_records)
    if reimport["head_anchor_edges_shared"] != len(stitch_records):
        raise RuntimeError(
            "Some head stitch edges were split during GLB export: "
            f"{reimport['head_anchor_edges_shared']}/{len(stitch_records)}"
        )
    if reimport["body_anchor_edges_shared"] != len(stitch_records):
        raise RuntimeError(
            "Some body stitch edges were split during GLB export: "
            f"{reimport['body_anchor_edges_shared']}/{len(stitch_records)}"
        )

    lo, hi = bounds([imported])
    full_center = (lo + hi) / 2
    full_scale = max(hi - lo) * 1.15
    head_center = Vector((-0.005, 0.03, 0.875))
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(
            os.path.join(output_dir, f"fused_full_{name}.png"),
            full_center,
            full_scale,
            angle,
            800,
        )
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(
            os.path.join(output_dir, f"fused_head_{name}.png"),
            head_center,
            0.34,
            angle,
            900,
        )

    report = {
        "sources_unchanged": True,
        "input_blend": input_blend,
        "outputs": {"blend": blend_path, "glb": glb_path},
        "fusion_method": "hidden collar cross-source triangle stitches",
        "hidden_region_world": REGION,
        "candidate_edges": {"body": len(body_edges), "head": len(head_edges)},
        "evaluated_edge_pairs": evaluated_pairs,
        "selection_threshold": selected_threshold,
        "stitch_count": len(stitch_records),
        "bridge_triangles": bridge_triangles,
        "cross_source_triangles": mixed_triangles,
        "uv_atlas": {
            "layout": "body left half; detailed head right half",
            "remapped_faces": uv_remap,
            "texture_node_replacements": texture_replacements,
        },
        "source_blend": source_blend_stats,
        "glb_reimport": reimport,
        "stitches": stitch_records,
    }
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
