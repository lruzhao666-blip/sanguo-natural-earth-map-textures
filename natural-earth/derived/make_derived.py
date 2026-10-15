"""Build and verify the fixed Sanguo relief crop. Requires Pillow with WebP."""

import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "SR_HR_asia.png"
BOUNDS = (88, 10, 135, 48)
CROP_BOX = (4380, 2040, 7200, 4320)


def fingerprint(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": digest}


def main():
    metadata = json.loads((ROOT.parent / "metadata.json").read_text(encoding="utf-8"))
    source_info = fingerprint(SOURCE)
    assert source_info["sha256"] == metadata["sha256"][SOURCE.name], "Source SHA-256 mismatch"
    assert source_info["bytes"] == metadata["bytes"][SOURCE.name], "Source size mismatch"
    extent = metadata["extent_wgs84"]
    relief = metadata["shaded_relief"]
    assert [extent[key] for key in ("west", "south", "east", "north")] == [15, -15, 180, 82]
    assert relief["source_resolution_arc_minutes"] == 1 and relief["north_up"]
    assert relief["pixel_size_degrees"] == [1 / 60, -1 / 60]
    west, south, east, north = BOUNDS
    computed_box = (
        round((west - extent["west"]) / relief["pixel_size_degrees"][0]),
        round((north - extent["north"]) / relief["pixel_size_degrees"][1]),
        round((east - extent["west"]) / relief["pixel_size_degrees"][0]),
        round((south - extent["north"]) / relief["pixel_size_degrees"][1]),
    )
    assert computed_box == CROP_BOX, "Crop does not match metadata coordinates"

    with Image.open(SOURCE) as source:
        assert source.format == "PNG" and source.mode == "L"
        assert source.size == (relief["width"], relief["height"]) == (9900, 5820)
        crop = source.crop(CROP_BOX)
        assert crop.mode == "L" and crop.size == (2820, 2280)
        # Check before lossy encoding: WebP pixels are not expected to be exact.
        for x, y in ((0, 0), (2819, 0), (0, 2279), (2819, 2279), (1410, 1140), (1920, 1080)):
            lon, lat = west + x / 60, north - y / 60
            sx = round((lon - extent["west"]) / relief["pixel_size_degrees"][0])
            sy = round((lat - extent["north"]) / relief["pixel_size_degrees"][1])
            assert (sx, sy) == (x + CROP_BOX[0], y + CROP_BOX[1])
            value = source.getpixel((sx, sy))
            assert crop.getpixel((x, y)) == value, (lon, lat)
            print(f"PASS pixel lon={lon:.6f}, lat={lat:.6f}: source({sx},{sy}) = crop({x},{y}) = {value}")

    images = {
        "SR_sanguo.webp": crop,
        "SR_sanguo_half.webp": crop.resize((1410, 1140), Image.Resampling.LANCZOS),
    }
    encoded = {}
    for name, image in images.items():
        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=80, method=6)
        payload = buffer.getvalue()
        assert len(payload) < 1_000_000, f"{name} exceeds 1 MB"
        with Image.open(BytesIO(payload)) as decoded:
            assert decoded.format == "WEBP" and decoded.size == image.size
            red, green, blue = decoded.convert("RGB").split()
            # YUV-to-RGB decoder rounding can separate neutral channels by one level.
            for first, second in ((red, green), (red, blue), (green, blue)):
                assert ImageChops.difference(first, second).getextrema()[1] <= 1
        encoded[name] = payload

    for name, payload in encoded.items():
        (ROOT / name).write_bytes(payload)
    manifest = {
        "bounds_lonlat": list(BOUNDS),
        "width": crop.width,
        "height": crop.height,
        "pixel_convention": "edge",
        "source": SOURCE.name,
        "source_sha256": source_info["sha256"],
        "files": {name: fingerprint(ROOT / name) for name in images},
    }
    manifest_path = ROOT / "SR_sanguo.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest
    for name in (*images, manifest_path.name):
        info = fingerprint(ROOT / name)
        print(f"{name}: {info['bytes']:,} bytes; sha256={info['sha256']}")


if __name__ == "__main__":
    main()
