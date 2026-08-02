import bpy
import json
import os
import sys


REGION = {
    "x_min": -0.15,
    "x_max": 0.15,
    "y_min": -0.11,
    "y_max": 0.16,
    "z_min": 0.70,
    "z_max": 0.84,
}


def in_region(point):
    return (
        REGION["x_min"] <= point.x <= REGION["x_max"]
        and REGION["y_min"] <= point.y <= REGION["y_max"]
        and REGION["z_min"] <= point.z <= REGION["z_max"]
    )


def face_centroid_in_region(obj, polygon):
    return in_region(obj.matrix_world @ polygon.center)


def delete_faces(obj, delete_if):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    selected = 0
    for polygon in obj.data.polygons:
        polygon.select = delete_if(polygon)
        selected += int(polygon.select)
    obj.data.update()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    obj.data.update()
    return selected


def split_local_patch(obj, suffix):
    local = obj.copy()
    local.data = obj.data.copy()
    local.name = f"{obj.name}_{suffix}"
    local.data.name = f"{obj.data.name}_{suffix}"
    bpy.context.collection.objects.link(local)
    total_faces = len(obj.data.polygons)
    removed_from_source = delete_faces(
        obj, lambda polygon: face_centroid_in_region(obj, polygon)
    )
    removed_from_local = delete_faces(
        local, lambda polygon: not face_centroid_in_region(local, polygon)
    )
    local_faces = len(local.data.polygons)
    if local_faces < 100 or removed_from_source != local_faces:
        raise RuntimeError(
            f"Local split mismatch for {obj.name}: source removed {removed_from_source}, "
            f"local kept {local_faces}, source total {total_faces}, local removed {removed_from_local}"
        )
    return local, removed_from_source


def apply_boolean_union(target, operand):
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    modifier = target.modifiers.new(name="LocalExactNeckUnion", type="BOOLEAN")
    modifier.operation = "UNION"
    modifier.solver = "EXACT"
    modifier.object = operand
    if hasattr(modifier, "use_self"):
        modifier.use_self = True
    if hasattr(modifier, "use_hole_tolerant"):
        modifier.use_hole_tolerant = True
    if hasattr(modifier, "material_mode"):
        modifier.material_mode = "TRANSFER"
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def join_and_weld(objects, active, threshold=0.00001):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active
    bpy.ops.object.join()
    active.name = "SeatedPerson_DetailedHead_Fused"
    active.data.name = "SeatedPerson_DetailedHead_Fused_Mesh"
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    before_vertices = len(active.data.vertices)
    bpy.ops.mesh.remove_doubles(threshold=threshold)
    bpy.ops.object.mode_set(mode="OBJECT")
    after_vertices = len(active.data.vertices)
    triangulate = active.modifiers.new(name="TriangulateFusion", type="TRIANGULATE")
    triangulate.keep_custom_normals = True
    bpy.context.view_layer.objects.active = active
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    return before_vertices - after_vertices


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 3:
        raise SystemExit("expected INPUT_BLEND OUTPUT_BLEND REPORT_JSON")
    input_blend, output_blend, report_path = map(os.path.abspath, argv)
    bpy.ops.wm.open_mainfile(filepath=input_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]

    before = {
        "body_vertices": len(body.data.vertices),
        "body_polygons": len(body.data.polygons),
        "head_vertices": len(head.data.vertices),
        "head_polygons": len(head.data.polygons),
    }
    body_local, body_local_faces = split_local_patch(body, "NeckPatch")
    head_local, head_local_faces = split_local_patch(head, "NeckPatch")
    local_faces_before = len(body_local.data.polygons) + len(head_local.data.polygons)

    apply_boolean_union(body_local, head_local)
    local_faces_after = len(body_local.data.polygons)
    if local_faces_after < min(body_local_faces, head_local_faces) // 4:
        raise RuntimeError(
            f"Local boolean result is too small: {local_faces_after} faces from "
            f"{local_faces_before} input faces"
        )
    bpy.data.objects.remove(head_local, do_unlink=True)

    welded_vertices = join_and_weld([body, head, body_local], body)
    final = body
    final["fusion_method"] = "local exact boolean union plus boundary vertex welding"
    final["fusion_region"] = json.dumps(REGION)
    final["weld_threshold"] = 0.00001
    final["welded_vertices"] = welded_vertices

    after = {
        "vertices": len(final.data.vertices),
        "edges": len(final.data.edges),
        "polygons": len(final.data.polygons),
        "objects": 1,
        "materials": [slot.material.name if slot.material else None for slot in final.material_slots],
    }
    report = {
        "region": REGION,
        "before": before,
        "local": {
            "body_faces": body_local_faces,
            "head_faces": head_local_faces,
            "faces_before_boolean": local_faces_before,
            "faces_after_boolean": local_faces_after,
            "welded_boundary_vertices": welded_vertices,
        },
        "after": after,
    }
    os.makedirs(os.path.dirname(output_blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
