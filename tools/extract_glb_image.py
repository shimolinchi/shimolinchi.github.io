import argparse
import json
import struct
from pathlib import Path

from PIL import Image


def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total_length != len(data):
        raise ValueError(f"Unsupported or invalid GLB: {path}")
    offset = 12
    chunks = {}
    while offset < len(data):
        length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunks[chunk_type] = data[offset : offset + length]
        offset += length
    document = json.loads(chunks[0x4E4F534A].decode("utf-8"))
    return document, chunks[0x004E4942]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_glb")
    parser.add_argument("output_image")
    parser.add_argument("--name-contains", default="basecolor")
    parser.add_argument("--size", type=int, default=512)
    args = parser.parse_args()

    document, binary = read_glb(args.input_glb)
    image_entry = next(
        image
        for image in document["images"]
        if args.name_contains.lower() in image.get("name", "").lower()
    )
    view = document["bufferViews"][image_entry["bufferView"]]
    start = view.get("byteOffset", 0)
    encoded = binary[start : start + view["byteLength"]]
    output = Path(args.output_image)
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded_path = output.with_suffix(".source.jpg")
    encoded_path.write_bytes(encoded)
    with Image.open(encoded_path) as image:
        image.thumbnail((args.size, args.size), Image.Resampling.LANCZOS)
        image.convert("RGB").save(output, quality=95)
    encoded_path.unlink()
    print(f"Extracted {image_entry.get('name', '<unnamed>')} to {output}")


if __name__ == "__main__":
    main()
