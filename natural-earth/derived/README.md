# Sanguo Shaded Relief Derivatives

Game clients should load `../../assets/relief.webp` (2880 x 1620, about 285 KB)
with `../../coordinates.json`. The larger images here are source derivatives
for expanded views and higher detail; they are not the default runtime assets.

## Source

Input: `../SR_HR_asia.png`, Natural Earth Shaded Relief Basic, 9900 x 5820,
8-bit grayscale, north-up, geographic longitude/latitude (WGS84). Its pixel
resolution is one arc minute, not one meter. The source covers longitude
15 to 180 and latitude -15 to 82. Source downloads, version caveats, public
domain terms and checksums are recorded in `../metadata.json` and `../README.md`.

## Crop and Coordinates

Bounds are `[west, south, east, north] = [88, 10, 135, 48]`, in degrees.
The Pillow crop box is `(4380, 2040, 7200, 4320)`; right and bottom are
exclusive. The full crop is 2820 x 2280 with no resizing or color adjustment.

Pixel-edge coordinates, with the origin at the northwest corner:

```text
Source: x = (longitude - 15) * 60; y = (82 - latitude) * 60
Crop:   x = (longitude - 88) * 60; y = (48 - latitude) * 60
Half:   x = (longitude - 88) * 30; y = (48 - latitude) * 30
```

The southeast edge is `(2820, 2280)`, not a valid pixel index. Pixel `(i, j)`
has its center at crop-edge coordinates `(i + 0.5, j + 0.5)`. Both images
cover exactly the same bounds. Use the JSON bounds when positioning them;
WebP files do not carry the source PNG's world-file georeferencing.

| File | Dimensions | Processing |
| --- | --- | --- |
| `SR_sanguo.webp` | 2820 x 2280 | Fixed crop, WebP quality 80, method 6 |
| `SR_sanguo_half.webp` | 1410 x 1140 | Crop resized with LANCZOS, same WebP settings |
| `SR_sanguo.json` | n/a | Bounds, full dimensions, source SHA-256, WebP byte sizes and SHA-256 |

WebP is lossy: no tone/color adjustment is applied, but decoded grayscale
values may differ from the source. Pillow may expose these achromatic WebP
images as RGB rather than mode L; decoder rounding can separate neutral
channels by one level. Only the half-size image is resampled.
The JSON lists both image files; it excludes itself to avoid a circular hash.

## Rebuild and Verify

Requires Python 3.11+ and Pillow with WebP support. From the repository root:

```sh
python -m pip install Pillow
python natural-earth/derived/make_derived.py
python natural-earth/verify.py
```

The build also works from another directory because paths are relative to
the script. It overwrites only the two derived WebP files and their JSON.
Do not use Python's `-O` flag: verification uses assertions.

Every run verifies the source hash/size and metadata geometry, checks six
uncompressed crop pixels against source pixels using metadata coordinates
(four extreme pixels, the center and 120E/30N), then checks WebP decoding,
dimensions, neutral grayscale (allowing one-level decoder rounding) and the
strict limit of 1,000,000 bytes per
image. It prints pixel results and all three output sizes/checksums. Repeated
runs are byte-identical with the same Pillow/libwebp versions; encoder upgrades
can change compressed bytes and the generated hashes.

The source snapshot had a stale README checksum. The metadata checksum was
updated with the coordinate documentation; `../verify.py` now passes.
The source raster and vector asset checksums remain unchanged.

This is a visual backdrop, not historical geography. The root-level
`registration.json` records and verifies the affine conversion between the
existing 2000 x 1600 strategy-map canvas and WGS84 bounds. That is a
mathematical coordinate registration, not an independent historical
coastline/control-point survey. No original Natural Earth assets or Sanguo
regional data are modified.
