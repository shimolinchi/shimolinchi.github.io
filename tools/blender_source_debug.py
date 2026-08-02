import bpy
import os
import sys
from mathutils import Vector


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from blender_head_swap import render


def material(name, color, metallic=0.0):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1.0)
    result.use_nodes = True
    principled = result.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Roughness"].default_value = 0.55
    principled.inputs["Metallic"].default_value = metallic
    return result


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 2:
        raise SystemExit("expected INPUT_BLEND OUTPUT_DIR")
    input_blend, output_dir = map(os.path.abspath, argv)
    os.makedirs(output_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=input_blend)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError(f"Expected one mesh, got {len(meshes)}")
    obj = meshes[0]
    body_group = obj.vertex_groups["SourceBody"].index
    head_group = obj.vertex_groups["SourceHead"].index
    source = [0] * len(obj.data.vertices)
    for vertex in obj.data.vertices:
        groups = {membership.group for membership in vertex.groups}
        if body_group in groups:
            source[vertex.index] |= 1
        if head_group in groups:
            source[vertex.index] |= 2

    obj.data.materials.clear()
    obj.data.materials.append(material("BODY_SOURCE_RED", (0.8, 0.025, 0.015)))
    obj.data.materials.append(material("HEAD_SOURCE_CYAN", (0.015, 0.55, 0.8), 0.05))
    obj.data.materials.append(material("CROSS_SOURCE_YELLOW", (0.95, 0.65, 0.01), 0.1))
    counts = [0, 0, 0]
    for polygon in obj.data.polygons:
        mask = 0
        for vertex_index in polygon.vertices:
            mask |= source[vertex_index]
        material_index = 2 if mask == 3 else (1 if mask == 2 else 0)
        polygon.material_index = material_index
        counts[material_index] += 1
    print(f"source face counts body/head/cross={counts}")

    center = Vector((-0.005, 0.03, 0.855))
    for angle, name in ((0, "front"), (35, "three_quarter"), (90, "side"), (180, "back")):
        render(
            os.path.join(output_dir, f"source_{name}.png"),
            center,
            0.40,
            angle,
            1000,
        )


if __name__ == "__main__":
    main()
