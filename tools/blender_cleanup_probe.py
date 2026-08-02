import bpy
import bmesh
import os
import sys
import numpy as np
from mathutils import Vector


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import render


def basecolor_pixels(body):
    material = body.material_slots[0].material
    image = next(
        node.image
        for node in material.node_tree.nodes
        if node.type == "TEX_IMAGE"
        and node.image is not None
        and "basecolor" in node.image.name.lower()
    )
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    return pixels.reshape((height, width, 4)), width, height


def remove_body_residue(body):
    mesh = body.data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        raise RuntimeError("Body mesh has no UV map")
    polygon_count = len(mesh.polygons)
    loop_count = len(mesh.loops)
    loop_totals = np.empty(polygon_count, dtype=np.int32)
    loop_starts = np.empty(polygon_count, dtype=np.int32)
    centers = np.empty(polygon_count * 3, dtype=np.float32)
    mesh.polygons.foreach_get("loop_total", loop_totals)
    mesh.polygons.foreach_get("loop_start", loop_starts)
    mesh.polygons.foreach_get("center", centers)
    if not np.all(loop_totals == 3):
        raise RuntimeError("Expected an all-triangle body mesh")

    uvs = np.empty(loop_count * 2, dtype=np.float32)
    uv_layer.data.foreach_get("uv", uvs)
    uvs = uvs.reshape((-1, 2))
    texture, width, height = basecolor_pixels(body)
    sampled = []
    for offset in (0, 1, 2):
        face_uv = uvs[loop_starts + offset]
        xs = np.clip((np.mod(face_uv[:, 0], 1.0) * (width - 1)).astype(np.int32), 0, width - 1)
        ys = np.clip((np.mod(face_uv[:, 1], 1.0) * (height - 1)).astype(np.int32), 0, height - 1)
        sampled.append(texture[ys, xs, :3])
    colors = (sampled[0] + sampled[1] + sampled[2]) / 3.0
    red, green, blue = colors[:, 0], colors[:, 1], colors[:, 2]
    skin = (red - blue > 0.055) & (red - green > 0.018) & (red > 0.12)

    center = centers.reshape((-1, 3))
    x, y, z = center[:, 0], center[:, 1], center[:, 2]
    old_head = (z >= 0.792) & (np.abs(x) <= 0.145) & (y >= -0.115) & (y <= 0.130)
    neck_radius = (x / 0.072) ** 2 + ((y - 0.025) / 0.090) ** 2
    old_neck = (z >= 0.720) & (z < 0.805) & (neck_radius <= 1.0) & skin
    delete_mask = old_head | old_neck

    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    mesh.polygons.foreach_set("select", delete_mask)
    mesh.update()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    body.select_set(False)
    mesh.update()

    bm = bmesh.new()
    bm.from_mesh(mesh)
    loose_vertices = [vertex for vertex in bm.verts if not vertex.link_faces]
    loose_count = len(loose_vertices)
    bmesh.ops.delete(bm, geom=loose_vertices, context="VERTS")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return {
        "old_head_faces": int(np.count_nonzero(old_head)),
        "old_neck_skin_faces": int(np.count_nonzero(old_neck & ~old_head)),
        "deleted_faces": int(np.count_nonzero(delete_mask)),
        "loose_vertices": loose_count,
    }


def color_material(name, color):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        *color,
        1.0,
    )
    material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.55
    return material


def render_views(output_dir, prefix):
    center = Vector((-0.005, 0.03, 0.855))
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(
            os.path.join(output_dir, f"{prefix}_{name}.png"),
            center,
            0.40,
            angle,
            1000,
        )


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 2:
        raise SystemExit("expected INPUT_BLEND OUTPUT_DIR")
    input_blend, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=input_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]
    removed = remove_body_residue(body)
    print(f"removed body residue: {removed}; remaining={len(body.data.vertices)}")
    render_views(output_dir, "textured")

    body.data.materials.clear()
    body.data.materials.append(color_material("BODY_RED", (0.8, 0.025, 0.015)))
    head.data.materials.clear()
    head.data.materials.append(color_material("HEAD_CYAN", (0.015, 0.55, 0.8)))
    render_views(output_dir, "source")


if __name__ == "__main__":
    main()
