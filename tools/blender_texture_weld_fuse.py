import bpy
import json
import os
import sys

import numpy as np


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import (
    filter_linked_components,
    import_glb,
    initial_detail_matrix,
    refine_alignment,
    reset_scene,
)


def load_texture_pixels(filepath):
    image = bpy.data.images.load(filepath, check_existing=False)
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    return pixels.reshape((height, width, 4)), width, height


def delete_non_skin_lower_faces(obj, texture_path):
    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        raise RuntimeError("Detailed head mesh has no UV map")
    polygon_count = len(mesh.polygons)
    loop_count = len(mesh.loops)
    loop_totals = np.empty(polygon_count, dtype=np.int32)
    loop_starts = np.empty(polygon_count, dtype=np.int32)
    centers = np.empty(polygon_count * 3, dtype=np.float32)
    mesh.polygons.foreach_get("loop_total", loop_totals)
    mesh.polygons.foreach_get("loop_start", loop_starts)
    mesh.polygons.foreach_get("center", centers)
    if not np.all(loop_totals == 3):
        raise RuntimeError("Expected an all-triangle detailed mesh")

    uvs = np.empty(loop_count * 2, dtype=np.float32)
    uv_layer.data.foreach_get("uv", uvs)
    uvs = uvs.reshape((-1, 2))
    texture, width, height = load_texture_pixels(texture_path)
    sampled = []
    for offset in (0, 1, 2):
        face_uv = uvs[loop_starts + offset]
        xs = np.clip((np.mod(face_uv[:, 0], 1.0) * (width - 1)).astype(np.int32), 0, width - 1)
        ys = np.clip((np.mod(face_uv[:, 1], 1.0) * (height - 1)).astype(np.int32), 0, height - 1)
        sampled.append(texture[ys, xs, :3])
    colors = (sampled[0] + sampled[1] + sampled[2]) / 3.0
    red, green, blue = colors[:, 0], colors[:, 1], colors[:, 2]
    skin = (red - blue > 0.075) & (red - green > 0.025) & (red > 0.12)
    center_xyz = centers.reshape((-1, 3))
    center_x = center_xyz[:, 0]
    center_y = center_xyz[:, 1]
    center_z = center_xyz[:, 2]
    classify_material = (center_z < 0.46) & ((center_y > -0.18) | (center_z < 0.33))
    outside_lower_neck = (center_z < 0.33) & (np.abs(center_x - 0.015) > 0.16)
    delete_mask = (center_z < 0.18) | (classify_material & ~skin) | outside_lower_neck

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    mesh.polygons.foreach_set("select", delete_mask)
    mesh.update()
    deleted_faces = int(np.count_nonzero(delete_mask))
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    mesh.update()
    return {
        "deleted_faces": deleted_faces,
        "kept_faces": len(mesh.polygons),
        "skin_faces_in_classified_region": int(np.count_nonzero(classify_material & skin)),
    }


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


def weld_neck_region(obj, threshold=0.0030):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    selected = 0
    transform = obj.matrix_world
    for vertex in obj.data.vertices:
        point = transform @ vertex.co
        vertex.select = (
            -0.105 <= point.x <= 0.105
            and -0.04 <= point.y <= 0.14
            and 0.70 <= point.z <= 0.79
        )
        selected += int(vertex.select)
    obj.data.update()
    before = len(obj.data.vertices)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.remove_doubles(threshold=threshold)
    bpy.ops.object.mode_set(mode="OBJECT")
    after = len(obj.data.vertices)
    return {"selected_vertices": selected, "merged_vertices": before - after, "threshold": threshold}


def count_cross_source_vertices(obj):
    body_group = obj.vertex_groups["SourceBody"].index
    head_group = obj.vertex_groups["SourceHead"].index
    body_only = 0
    head_only = 0
    both = 0
    for vertex in obj.data.vertices:
        groups = {membership.group for membership in vertex.groups}
        has_body = body_group in groups
        has_head = head_group in groups
        if has_body and has_head:
            both += 1
        elif has_body:
            body_only += 1
        elif has_head:
            head_only += 1
    return {"shared_head_body_vertices": both, "body_only_vertices": body_only, "head_only_vertices": head_only}


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 6:
        raise SystemExit("expected BODY_GLb HEAD_GLB TEXTURE OUTPUT_BLEND REPORT_JSON ALIGNMENT_JSON")
    body_path, head_path, texture_path, output_blend, report_path, alignment_path = map(
        os.path.abspath, argv
    )
    reset_scene()
    body = import_glb(body_path, "BodyAndChair_Cut")
    head = import_glb(head_path, "DetailedHead")
    transform, history, source_samples, target_samples = refine_alignment(
        head, body, initial_detail_matrix()
    )
    body_seed_count, body_removed_count = filter_linked_components(
        body,
        lambda point: (
            (point.z > 0.81 and point.y < 0.0 and abs(point.x) < 0.15)
            or (point.z > 0.92 and point.y < 0.12 and abs(point.x) < 0.13)
        ),
        keep_selected=False,
        expected_range=(30000, 350000),
    )
    texture_filter = delete_non_skin_lower_faces(head, texture_path)
    head.matrix_world = transform @ head.matrix_world
    tag_source_vertices(body, "SourceBody")
    tag_source_vertices(head, "SourceHead")
    fused = join_objects(body, head)
    weld = weld_neck_region(fused)
    cross_source = count_cross_source_vertices(fused)
    if cross_source["shared_head_body_vertices"] == 0:
        raise RuntimeError("No head/body vertices were welded together")
    triangulate = fused.modifiers.new(name="TriangulateWeld", type="TRIANGULATE")
    triangulate.keep_custom_normals = True
    bpy.context.view_layer.objects.active = fused
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    fused["fusion_method"] = "UV skin extraction plus local head/body vertex welding"
    fused["shared_head_body_vertices"] = cross_source["shared_head_body_vertices"]
    fused["weld_threshold"] = weld["threshold"]

    report = {
        "fusion_method": "UV skin extraction plus local head/body vertex welding",
        "alignment_samples": {"source": source_samples, "target": target_samples},
        "alignment_history": history,
        "body_head_removal": {
            "seed_vertices": body_seed_count,
            "removed_linked_vertices": body_removed_count,
        },
        "texture_filter": texture_filter,
        "weld": weld,
        "source_membership": cross_source,
        "final": {
            "objects": 1,
            "vertices": len(fused.data.vertices),
            "edges": len(fused.data.edges),
            "polygons": len(fused.data.polygons),
            "materials": [slot.material.name if slot.material else None for slot in fused.material_slots],
        },
    }
    os.makedirs(os.path.dirname(output_blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    with open(alignment_path, "w", encoding="utf-8") as handle:
        json.dump([[float(value) for value in row] for row in transform], handle, indent=2)


if __name__ == "__main__":
    main()
