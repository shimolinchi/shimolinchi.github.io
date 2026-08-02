import bpy
import json
import math
import os
import sys
from mathutils import Matrix, Vector, kdtree
import numpy as np


def argv_after_double_dash():
    if "--" not in sys.argv:
        raise SystemExit("usage: blender --background --python script.py -- BODY DETAIL OUTPUT_DIR")
    return sys.argv[sys.argv.index("--") + 1 :]


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_glb(filepath, prefix):
    existing = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=filepath)
    added = [obj for obj in bpy.context.scene.objects if obj not in existing]
    meshes = [obj for obj in added if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one mesh in {filepath}, got {len(meshes)}")
    mesh = meshes[0]
    mesh.name = prefix
    mesh.data.name = f"{prefix}_Mesh"
    for obj in added:
        if obj != mesh and obj.type == "EMPTY" and not obj.children:
            bpy.data.objects.remove(obj, do_unlink=True)
    return mesh


def world_vertex_coords(obj):
    mw = obj.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def initial_detail_matrix():
    return Matrix(
        (
            (0.3000, 0.0, 0.0, -0.0060),
            (0.0, 0.3000, 0.0, 0.0300),
            (0.0, 0.0, 0.3000, 0.68615),
            (0.0, 0.0, 0.0, 1.0),
        )
    )


def fit_similarity(source_points, target_points):
    src = np.asarray(source_points, dtype=np.float64)
    dst = np.asarray(target_points, dtype=np.float64)
    src_center = src.mean(axis=0)
    dst_center = dst.mean(axis=0)
    src0 = src - src_center
    dst0 = dst - dst_center
    covariance = src0.T @ dst0
    u, singular, vt = np.linalg.svd(covariance)
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0:
        vt[-1, :] *= -1
        rotation = vt.T @ u.T
    denominator = float(np.sum(src0 * src0))
    scale = float(np.sum(singular) / denominator) if denominator > 1e-12 else 1.0
    scale = max(0.985, min(1.015, scale))
    translation = dst_center - scale * (rotation @ src_center)
    result = np.eye(4, dtype=np.float64)
    result[:3, :3] = scale * rotation
    result[:3, 3] = translation
    return Matrix(result.tolist()), scale


def refine_alignment(detail, body, initial):
    source_all = [p for p in world_vertex_coords(detail) if p.z > 0.40]
    target_all = [
        p
        for p in world_vertex_coords(body)
        if p.z > 0.805 and abs(p.x) < 0.16 and p.y < 0.16
    ]
    source = source_all[:: max(1, len(source_all) // 16000)]
    target = target_all[:: max(1, len(target_all) // 50000)]
    tree = kdtree.KDTree(len(target))
    for index, point in enumerate(target):
        tree.insert(point, index)
    tree.balance()

    transform = initial.copy()
    history = []
    for iteration in range(7):
        pairs = []
        for original in source:
            current = transform @ original
            nearest, _, distance = tree.find(current)
            if distance < 0.028:
                pairs.append((distance, current, nearest))
        if len(pairs) < 100:
            break
        pairs.sort(key=lambda item: item[0])
        pairs = pairs[: int(len(pairs) * 0.82)]
        src = [[p[1].x, p[1].y, p[1].z] for p in pairs]
        dst = [[p[2].x, p[2].y, p[2].z] for p in pairs]
        delta, incremental_scale = fit_similarity(src, dst)
        candidate = delta @ transform
        total_scale = Vector(candidate.col[0].xyz).length
        if 0.285 <= total_scale <= 0.315:
            transform = candidate
        mean_distance = sum(p[0] for p in pairs) / len(pairs)
        history.append(
            {
                "iteration": iteration + 1,
                "pairs": len(pairs),
                "mean_distance": mean_distance,
                "incremental_scale": incremental_scale,
                "total_scale": Vector(transform.col[0].xyz).length,
            }
        )
    return transform, history, len(source), len(target)


def filter_linked_components(obj, seed_predicate, keep_selected, expected_range):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")

    seed_count = 0
    for vertex in obj.data.vertices:
        vertex.select = seed_predicate(obj.matrix_world @ vertex.co)
        seed_count += int(vertex.select)
    obj.data.update()
    if seed_count == 0:
        raise RuntimeError(f"No component seeds selected in {obj.name}")

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_linked()
    bpy.ops.object.mode_set(mode="OBJECT")
    linked_count = sum(int(vertex.select) for vertex in obj.data.vertices)
    low, high = expected_range
    print(
        f"Linked selection in {obj.name}: {seed_count} seed vertices expanded to "
        f"{linked_count} of {len(obj.data.vertices)} vertices"
    )
    if not low <= linked_count <= high:
        raise RuntimeError(
            f"Linked selection count {linked_count} for {obj.name} is outside safe range "
            f"[{low}, {high}]"
        )

    bpy.ops.object.mode_set(mode="EDIT")
    if keep_selected:
        bpy.ops.mesh.select_all(action="INVERT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    obj.data.update()
    return seed_count, linked_count


def delete_vertices(obj, predicate):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    selected_count = 0
    for vertex in obj.data.vertices:
        vertex.select = predicate(obj.matrix_world @ vertex.co)
        selected_count += int(vertex.select)
    obj.data.update()
    print(f"Deleting {selected_count} of {len(obj.data.vertices)} vertices from {obj.name}")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    obj.data.update()
    return selected_count


def bounds(objects):
    points = []
    for obj in objects:
        if obj.type == "MESH" and not obj.hide_render:
            points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return lo, hi


def clear_render_helpers():
    for obj in list(bpy.context.scene.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)


def add_camera(center, ortho_scale, angle_degrees, elevation=0.08):
    angle = math.radians(angle_degrees)
    direction = Vector((math.sin(angle), -math.cos(angle), elevation)).normalized()
    location = center + direction * max(ortho_scale * 2.5, 1.0)
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    camera.data.lens = 60
    camera.rotation_euler = (center - location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera


def add_lights(center, radius):
    for name, offset, energy, size in (
        ("Key", Vector((-0.7, -1.0, 1.1)), 700, 4.0),
        ("Fill", Vector((0.9, -0.2, 0.4)), 350, 3.0),
        ("Rim", Vector((0.2, 1.0, 0.9)), 550, 2.5),
    ):
        location = center + offset.normalized() * radius
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (center - location).to_track_quat("-Z", "Y").to_euler()


def render(filepath, center, ortho_scale, angle, resolution=800):
    clear_render_helpers()
    add_camera(center, ortho_scale, angle)
    add_lights(center, max(ortho_scale * 2.0, 1.0))
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = os.path.abspath(filepath)
    scene.world.color = (0.025, 0.025, 0.025)
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.ops.render.render(write_still=True)


def matrix_list(matrix):
    return [[round(float(v), 8) for v in row] for row in matrix]


def main():
    argv = argv_after_double_dash()
    if len(argv) != 3:
        raise SystemExit("expected BODY DETAIL OUTPUT_DIR")
    body_path, detail_path, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    reset_scene()

    body = import_glb(body_path, "BodyAndChair_Cut")
    detail = import_glb(detail_path, "DetailedHead")
    transform, history, source_samples, target_samples = refine_alignment(
        detail, body, initial_detail_matrix()
    )

    body_seed_count, body_linked_count = filter_linked_components(
        body,
        lambda p: (
            (p.z > 0.81 and p.y < 0.0 and abs(p.x) < 0.15)
            or (p.z > 0.92 and p.y < 0.12 and abs(p.x) < 0.13)
        ),
        keep_selected=False,
        expected_range=(30000, 350000),
    )
    detail_removed_count = delete_vertices(
        detail,
        lambda p: p.z < 0.20
        or (
            p.z < 0.33
            and (
                abs(p.x - 0.015) > 0.13 + (p.z - 0.20) * (0.03 / 0.13)
                or p.y < -0.09 - (p.z - 0.20) * (0.09 / 0.13)
                or p.y > 0.22
            )
        ),
    )
    detail.matrix_world = transform @ detail.matrix_world

    body["head_swap_role"] = "original body and chair with original head removed"
    detail["head_swap_role"] = "replacement high-detail head"
    detail["spatial_filter"] = "kept head above Z=0.33 plus a tapered central collar insert to Z=0.20"
    body["component_filter"] = "removed linked original head components"

    scene = bpy.context.scene
    scene["head_swap_notes"] = (
        "Original GLB files were imported read-only. The replacement head remains a separate "
        "mesh so its original UVs/material stay intact; the overlap is hidden inside the shirt collar."
    )
    bpy.ops.file.pack_all()
    blend_path = os.path.join(output_dir, "seated_person_detailed_head.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    for obj in scene.objects:
        obj.select_set(obj.type == "MESH")
    export_path = os.path.join(output_dir, "seated_person_detailed_head.glb")
    export_temp_path = os.path.join(output_dir, "seated_person_detailed_head_new.glb")
    if os.path.exists(export_temp_path):
        os.remove(export_temp_path)
    bpy.ops.export_scene.gltf(
        filepath=export_temp_path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )
    os.replace(export_temp_path, export_path)

    lo, hi = bounds([body, detail])
    full_center = (lo + hi) / 2
    full_scale = max((hi - lo)) * 1.15
    head_center = Vector((-0.005, 0.03, 0.875))
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(os.path.join(output_dir, f"preview_full_{name}.png"), full_center, full_scale, angle, 800)
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(os.path.join(output_dir, f"preview_head_{name}.png"), head_center, 0.34, angle, 900)

    report = {
        "body_source": body_path,
        "detail_source": detail_path,
        "outputs": {"blend": blend_path, "glb": export_path},
        "source_samples": source_samples,
        "target_samples": target_samples,
        "alignment_matrix": matrix_list(transform),
        "alignment_history": history,
        "component_filter": {
            "body_seed_vertices": body_seed_count,
            "body_removed_linked_vertices": body_linked_count,
            "detail_removed_by_tapered_collar_filter": detail_removed_count,
        },
        "remaining_vertices": {
            "body": len(body.data.vertices),
            "detail_head": len(detail.data.vertices),
        },
    }
    with open(os.path.join(output_dir, "head_swap_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
