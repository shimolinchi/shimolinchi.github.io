import bpy
import bmesh
import json
import os
from collections import defaultdict

SOURCE = bpy.data.filepath
OUTPUT = os.path.join(os.path.dirname(SOURCE), "Untitled_repaired.blend")
WORLD_MERGE_DISTANCE = 0.00035  # 0.35 mm; deliberately conservative.

obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
mesh = obj.data
mw = obj.matrix_world
uniform_scale = sum(abs(v) for v in obj.scale) / 3.0
local_merge_distance = WORLD_MERGE_DISTANCE / uniform_scale


def in_neck(v):
    p = mw @ v.co
    return 0.50 <= p.z <= 0.72 and abs(p.x) <= 0.085 and -0.08 <= p.y <= 0.14


def counts(bm):
    boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonmanifold = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    neck_boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1 and all(in_neck(v) for v in e.verts))
    return {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges_total": boundary,
        "nonmanifold_edges_total": nonmanifold,
        "boundary_edges_neck_region": neck_boundary,
    }


bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
before = counts(bm)

target_verts = [v for v in bm.verts if in_neck(v)]
verts_before = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=target_verts, dist=local_merge_distance)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
merged_vertices = verts_before - len(bm.verts)

# Remove zero-length edges and zero-area faces created by welding.
target_edges = [e for e in bm.edges if all(in_neck(v) for v in e.verts)]
bmesh.ops.dissolve_degenerate(bm, dist=local_merge_distance * 0.1, edges=target_edges)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

# Remove exact duplicate faces that become apparent after welding.
seen = {}
duplicate_faces = []
for face in bm.faces:
    key = tuple(sorted(v.index for v in face.verts))
    if key in seen:
        duplicate_faces.append(face)
    else:
        seen[key] = face
if duplicate_faces:
    bmesh.ops.delete(bm, geom=duplicate_faces, context="FACES_ONLY")

# Fill only small, fully enclosed boundary loops wholly inside the neck region.
boundary_edges = [e for e in bm.edges if len(e.link_faces) == 1 and all(in_neck(v) for v in e.verts)]
edge_adj = defaultdict(list)
for e in boundary_edges:
    for v in e.verts:
        edge_adj[v].append(e)
seen_edges = set()
filled_loops = 0
for root in boundary_edges:
    if root in seen_edges:
        continue
    stack = [root]
    comp = []
    comp_verts = set()
    seen_edges.add(root)
    while stack:
        edge = stack.pop()
        comp.append(edge)
        for v in edge.verts:
            comp_verts.add(v)
            for nxt in edge_adj[v]:
                if nxt not in seen_edges:
                    seen_edges.add(nxt)
                    stack.append(nxt)
    closed = len(comp_verts) >= 3 and all(sum(1 for e in edge_adj[v] if e in comp) == 2 for v in comp_verts)
    if closed and len(comp) <= 12:
        result = bmesh.ops.holes_fill(bm, edges=comp, sides=12)
        if result.get("faces"):
            filled_loops += 1

# Recalculate normals only around the repaired band.
neck_faces = [f for f in bm.faces if any(in_neck(v) for v in f.verts)]
if neck_faces:
    bmesh.ops.recalc_face_normals(bm, faces=neck_faces)

bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
after = counts(bm)
bm.to_mesh(mesh)
bm.free()
mesh.update()

# Preserve the user's current transforms and packed image data; save to a new file.
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT, copy=False)
report = {
    "source": SOURCE,
    "output": OUTPUT,
    "merge_distance_world_m": WORLD_MERGE_DISTANCE,
    "merged_vertices": merged_vertices,
    "duplicate_faces_removed": len(duplicate_faces),
    "small_boundary_loops_filled": filled_loops,
    "before": before,
    "after": after,
}
report_path = os.path.join(os.path.dirname(SOURCE), "Untitled_repaired_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("CODEX_REPAIR_RESULT")
print(json.dumps(report, ensure_ascii=False, indent=2))
