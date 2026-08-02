import bpy
import bmesh
import json
from collections import Counter, defaultdict, deque
from mathutils import Vector
from mathutils.kdtree import KDTree

obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
mesh = obj.data
mw = obj.matrix_world
coords = [mw @ v.co for v in mesh.vertices]

# Broad band covering the manually rebuilt neck and collar interface.
indices = [i for i, p in enumerate(coords) if 0.50 <= p.z <= 0.72 and abs(p.x) <= 0.085 and -0.08 <= p.y <= 0.14]
index_set = set(indices)

kd = KDTree(len(indices))
for i in indices:
    kd.insert(coords[i], i)
kd.balance()

close_pairs = []
for i in indices:
    for p, j, dist in kd.find_range(coords[i], 0.001):
        if j > i:
            close_pairs.append((i, j, dist))

exact_faces = Counter()
spatial_faces = Counter()
region_faces = []
for poly in mesh.polygons:
    if all(i in index_set for i in poly.vertices):
        region_faces.append(poly.index)
        exact_faces[tuple(sorted(poly.vertices))] += 1
        key = tuple(sorted(tuple(round(coords[i][axis], 5) for axis in range(3)) for i in poly.vertices))
        spatial_faces[key] += 1

bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
boundary_edges = []
for e in bm.edges:
    a, b = e.verts[0].index, e.verts[1].index
    if a in index_set and b in index_set and len(e.link_faces) == 1:
        boundary_edges.append((a, b))
bm.free()

adj = defaultdict(set)
for a, b in boundary_edges:
    adj[a].add(b)
    adj[b].add(a)
seen = set()
components = []
for root in adj:
    if root in seen:
        continue
    q = [root]
    seen.add(root)
    comp = []
    while q:
        v = q.pop()
        comp.append(v)
        for n in adj[v]:
            if n not in seen:
                seen.add(n)
                q.append(n)
    components.append(comp)

def comp_info(comp):
    ps = [coords[i] for i in comp]
    degrees = Counter(len(adj[i]) for i in comp)
    return {
        "vertices": len(comp),
        "degree_counts": dict(degrees),
        "min": [min(p[a] for p in ps) for a in range(3)],
        "max": [max(p[a] for p in ps) for a in range(3)],
        "center": [sum(p[a] for p in ps) / len(ps) for a in range(3)],
    }

report = {
    "region_vertices": len(indices),
    "region_faces": len(region_faces),
    "close_pairs_under_1mm": len(close_pairs),
    "closest_pairs": sorted(close_pairs, key=lambda x: x[2])[:40],
    "duplicate_exact_face_groups": sum(1 for n in exact_faces.values() if n > 1),
    "duplicate_spatial_face_groups": sum(1 for n in spatial_faces.values() if n > 1),
    "boundary_edges_region": len(boundary_edges),
    "boundary_components": sorted((comp_info(c) for c in components), key=lambda x: x["vertices"], reverse=True)[:30],
}
print("CODEX_NECK_ANALYZE_BEGIN")
print(json.dumps(report, indent=2))
print("CODEX_NECK_ANALYZE_END")
