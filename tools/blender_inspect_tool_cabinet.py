import bpy
from mathutils import Vector
from pathlib import Path


path = Path(r"C:\workspace\shimolinchi.github.io\assets\workbench-tool-cabinet.glb")
bpy.ops.import_scene.gltf(filepath=str(path))

for obj in bpy.context.scene.objects:
    if obj.type != "MESH":
        continue
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    mins = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maxs = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    print(
        "OBJECT",
        obj.name,
        "verts=", len(obj.data.vertices),
        "materials=", len(obj.data.materials),
        "min=", tuple(round(v, 5) for v in mins),
        "max=", tuple(round(v, 5) for v in maxs),
    )

    if obj.name.startswith("tripo_node"):
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
        components.sort(key=len, reverse=True)
        for index, component in enumerate(components[:30]):
            coords = [obj.matrix_world @ vertices[i].co for i in component]
            cmin = Vector((min(p.x for p in coords), min(p.y for p in coords), min(p.z for p in coords)))
            cmax = Vector((max(p.x for p in coords), max(p.y for p in coords), max(p.z for p in coords)))
            print(
                "COMPONENT", index,
                "verts=", len(component),
                "min=", tuple(round(v, 5) for v in cmin),
                "max=", tuple(round(v, 5) for v in cmax),
                "size=", tuple(round(v, 5) for v in cmax - cmin),
            )
