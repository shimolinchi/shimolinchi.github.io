import bpy
import json
import os
import sys
from mathutils import Vector


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    input_path, output_path = map(os.path.abspath, argv)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=input_path)
    obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo_z = min(v.z for v in coords)
    hi_z = max(v.z for v in coords)
    steps = 50
    slices = []
    for i in range(steps):
        z0 = lo_z + (hi_z - lo_z) * i / steps
        z1 = lo_z + (hi_z - lo_z) * (i + 1) / steps
        pts = [v for v in coords if z0 <= v.z < z1 or (i == steps - 1 and v.z == z1)]
        if pts:
            xs = [p.x for p in pts]
            ys = [p.y for p in pts]
            slices.append(
                {
                    "z0": round(z0, 6),
                    "z1": round(z1, 6),
                    "count": len(pts),
                    "x_min": round(min(xs), 6),
                    "x_max": round(max(xs), 6),
                    "x_size": round(max(xs) - min(xs), 6),
                    "y_min": round(min(ys), 6),
                    "y_max": round(max(ys), 6),
                    "y_size": round(max(ys) - min(ys), 6),
                }
            )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(slices, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
