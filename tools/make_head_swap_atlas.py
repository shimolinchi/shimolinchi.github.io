import argparse
import io
import json
import struct
from pathlib import Path

from PIL import Image


TEXTURE_KEYS = ("basecolor", "normal", "_rm")


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total_length != len(data):
        raise ValueError(f"Unsupported or invalid GLB: {path}")

    document = None
    binary = None
    offset = 12
    while offset < len(data):
        length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset : offset + length]
        offset += length
        if chunk_type == 0x4E4F534A:
            document = json.loads(chunk.decode("utf-8"))
        elif chunk_type == 0x004E4942:
            binary = chunk
    if document is None or binary is None:
        raise ValueError(f"GLB is missing JSON or BIN data: {path}")
    return document, binary


def embedded_image(document, binary, name_fragment):
    entry = next(
        image
        for image in document["images"]
        if name_fragment.lower() in image.get("name", "").lower()
    )
    view = document["bufferViews"][entry["bufferView"]]
    start = view.get("byteOffset", 0)
    encoded = binary[start : start + view["byteLength"]]
    with Image.open(io.BytesIO(encoded)) as image:
        return image.convert("RGB")


def build_atlas(body_image, head_image, tile_size):
    resampling = Image.Resampling.LANCZOS
    if body_image.size != (tile_size, tile_size):
        body_image = body_image.resize((tile_size, tile_size), resampling)
    if head_image.size != (tile_size, tile_size):
        head_image = head_image.resize((tile_size, tile_size), resampling)
    atlas = Image.new("RGB", (tile_size * 2, tile_size))
    atlas.paste(body_image, (0, 0))
    atlas.paste(head_image, (tile_size, 0))
    return atlas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("body_glb")
    parser.add_argument("head_glb")
    parser.add_argument("output_dir")
    parser.add_argument("--tile-size", type=int, default=4096)
    args = parser.parse_args()

    body_document, body_binary = read_glb(args.body_glb)
    head_document, head_binary = read_glb(args.head_glb)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}

    for key in TEXTURE_KEYS:
        body_image = embedded_image(body_document, body_binary, key)
        head_image = embedded_image(head_document, head_binary, key)
        atlas = build_atlas(body_image, head_image, args.tile_size)
        output_name = "atlas_rm.jpg" if key == "_rm" else f"atlas_{key}.jpg"
        output_path = output_dir / output_name
        atlas.save(output_path, quality=96, subsampling=0, optimize=True)
        outputs[key] = {
            "path": str(output_path.resolve()),
            "size": list(atlas.size),
            "body_source_size": list(body_image.size),
            "head_source_size": list(head_image.size),
        }

    report = {
        "body_source": str(Path(args.body_glb).resolve()),
        "head_source": str(Path(args.head_glb).resolve()),
        "layout": "body in left half; detailed head in right half",
        "uv_mapping": {
            "body": "u' = 0.5 * u, v' = v",
            "head": "u' = 0.5 + 0.5 * u, v' = v",
        },
        "outputs": outputs,
    }
    (output_dir / "atlas_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
