import bpy
from pathlib import Path


ROOT = Path(r"C:\workspace\shimolinchi.github.io")
SOURCE = ROOT / "assets" / "workbench-tool-cabinet.glb"
OUTPUT = ROOT / "public" / "models" / "tool-cabinet.glb"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
obj = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")

vertices = obj.data.vertices
adjacency = [[] for _ in vertices]
for edge in obj.data.edges:
    a, b = edge.vertices
    adjacency[a].append(b)
    adjacency[b].append(a)

unseen = set(range(len(vertices)))
components = []
while unseen:
    seed = unseen.pop()
    stack = [seed]
    component = [seed]
    while stack:
        current = stack.pop()
        for neighbor in adjacency[current]:
            if neighbor in unseen:
                unseen.remove(neighbor)
                stack.append(neighbor)
                component.append(neighbor)
    components.append(component)


def in_drill_or_hammer(x, z):
    drill = -0.13 <= x <= 0.24 and 0.62 <= z <= 0.92
    hammer = -0.43 <= x <= -0.20 and 0.44 <= z <= 0.95
    return drill or hammer


moved_components = 0
moved_vertices = 0
for component in components:
    coords = [vertices[index].co for index in component]
    center_x = sum(co.x for co in coords) / len(coords)
    center_z = sum(co.z for co in coords) / len(coords)
    max_y = max(co.y for co in coords)
    # The backboard surface is at roughly Y=0.222. Tool fragments sit in front
    # of it at smaller Y values, so this threshold avoids deforming the board.
    if in_drill_or_hammer(center_x, center_z) and max_y < 0.218:
        for index in component:
            vertices[index].co.y -= 0.045
        moved_components += 1
        moved_vertices += len(component)

obj.data.update()
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(OUTPUT),
    export_format="GLB",
    use_selection=True,
    export_materials="EXPORT",
    export_image_format="JPEG",
    export_jpeg_quality=85,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
)

print(f"OUTPUT={OUTPUT}")
print(f"MOVED_COMPONENTS={moved_components}")
print(f"MOVED_VERTICES={moved_vertices}")
