import bpy
import bmesh
import json
import os

SOURCE = bpy.data.filepath
OUTPUT = os.path.join(os.path.dirname(SOURCE), "Untitled_repaired_v2.blend")
WORLD_MERGE_DISTANCE = 0.00005  # 0.05 mm: effectively coincident points only.

obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
mesh = obj.data
mw = obj.matrix_world
uniform_scale = sum(abs(v) for v in obj.scale) / 3.0


def in_neck(v):
    p = mw @ v.co
    return 0.50 <= p.z <= 0.72 and abs(p.x) <= 0.085 and -0.08 <= p.y <= 0.14


bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
before = {
    "vertices": len(bm.verts),
    "edges": len(bm.edges),
    "faces": len(bm.faces),
    "neck_boundary_edges": sum(1 for e in bm.edges if len(e.link_faces) == 1 and all(in_neck(v) for v in e.verts)),
}

# Only vertices already belonging to an open boundary are eligible. Interior vertices,
# ordinary faces, UVs, materials and normals are left untouched.
eligible = {
    v
    for e in bm.edges
    if len(e.link_faces) == 1 and all(in_neck(v) for v in e.verts)
    for v in e.verts
}
bmesh.ops.remove_doubles(
    bm,
    verts=list(eligible),
    dist=WORLD_MERGE_DISTANCE / uniform_scale,
)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
after = {
    "vertices": len(bm.verts),
    "edges": len(bm.edges),
    "faces": len(bm.faces),
    "neck_boundary_edges": sum(1 for e in bm.edges if len(e.link_faces) == 1 and all(in_neck(v) for v in e.verts)),
}

# Safety gate: do not produce a candidate if Blender removed any face.
if after["faces"] != before["faces"]:
    bm.free()
    raise RuntimeError(f"Safety gate: face count changed {before['faces']} -> {after['faces']}")

bm.to_mesh(mesh)
bm.free()
mesh.update()
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT, copy=False)

report = {
    "source": SOURCE,
    "output": OUTPUT,
    "merge_distance_world_m": WORLD_MERGE_DISTANCE,
    "eligible_boundary_vertices": len(eligible),
    "before": before,
    "after": after,
}
with open(os.path.join(os.path.dirname(SOURCE), "Untitled_repaired_v2_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("CODEX_REPAIR_V2_RESULT")
print(json.dumps(report, ensure_ascii=False, indent=2))
