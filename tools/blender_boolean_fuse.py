import bpy
import json
import os
import sys


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) != 3:
        raise SystemExit("expected INPUT_BLEND OUTPUT_BLEND REPORT_JSON")
    input_blend, output_blend, report_path = map(os.path.abspath, argv)
    bpy.ops.wm.open_mainfile(filepath=input_blend)
    body = bpy.data.objects["BodyAndChair_Cut"]
    head = bpy.data.objects["DetailedHead"]
    before = {
        "body_vertices": len(body.data.vertices),
        "body_polygons": len(body.data.polygons),
        "head_vertices": len(head.data.vertices),
        "head_polygons": len(head.data.polygons),
    }

    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    modifier = body.modifiers.new(name="ExactHeadBodyUnion", type="BOOLEAN")
    modifier.operation = "UNION"
    modifier.solver = "EXACT"
    modifier.object = head
    if hasattr(modifier, "use_self"):
        modifier.use_self = True
    if hasattr(modifier, "use_hole_tolerant"):
        modifier.use_hole_tolerant = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    bpy.data.objects.remove(head, do_unlink=True)
    body.name = "SeatedPerson_DetailedHead_Fused"
    body.data.name = "SeatedPerson_DetailedHead_Fused_Mesh"
    after = {
        "vertices": len(body.data.vertices),
        "edges": len(body.data.edges),
        "polygons": len(body.data.polygons),
        "materials": [slot.material.name if slot.material else None for slot in body.material_slots],
    }
    if after["polygons"] < before["body_polygons"]:
        raise RuntimeError("Boolean result unexpectedly lost most source geometry")

    os.makedirs(os.path.dirname(output_blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump({"before": before, "after": after}, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
