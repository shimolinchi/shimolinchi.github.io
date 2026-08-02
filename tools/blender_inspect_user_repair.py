import bpy
import bmesh
import json
from mathutils import Vector


def world_bounds(obj):
    pts = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {
        "min": [min(p[i] for p in pts) for i in range(3)],
        "max": [max(p[i] for p in pts) for i in range(3)],
    }


report = {"file": bpy.data.filepath, "objects": []}
for obj in bpy.context.scene.objects:
    item = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "scale": list(obj.scale),
    }
    if obj.type == "MESH":
        mesh = obj.data
        item.update({
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "materials": len(obj.material_slots),
            "uv_layers": [uv.name for uv in mesh.uv_layers],
            "bounds_world": world_bounds(obj),
        })
        bm = bmesh.new()
        bm.from_mesh(mesh)
        boundary = [e for e in bm.edges if len(e.link_faces) == 1]
        nonmanifold = [e for e in bm.edges if len(e.link_faces) != 2]
        item["boundary_edges"] = len(boundary)
        item["nonmanifold_edges"] = len(nonmanifold)
        if boundary:
            coords = [obj.matrix_world @ v.co for e in boundary for v in e.verts]
            item["boundary_bounds_world"] = {
                "min": [min(p[i] for p in coords) for i in range(3)],
                "max": [max(p[i] for p in coords) for i in range(3)],
            }
            bins = {}
            for p in coords:
                key = round(p.z, 2)
                bins[key] = bins.get(key, 0) + 1
            item["boundary_z_bins"] = sorted(bins.items(), key=lambda x: x[1], reverse=True)[:20]
        bm.free()
    report["objects"].append(item)

print("CODEX_REPAIR_INSPECT_BEGIN")
print(json.dumps(report, ensure_ascii=False, indent=2))
print("CODEX_REPAIR_INSPECT_END")
