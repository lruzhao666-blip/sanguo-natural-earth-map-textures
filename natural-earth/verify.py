"""Verify the cropped Natural Earth assets using only the Python standard library."""
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent


def verify():
    metadata = json.loads((ROOT / 'metadata.json').read_text(encoding='utf-8'))
    extent = metadata['extent_wgs84']
    west, south, east, north = (extent[k] for k in ('west', 'south', 'east', 'north'))
    assert -180 <= west < east <= 180 and -90 <= south < north <= 90
    for filename, expected in metadata['sha256'].items():
        content = (ROOT / filename).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected, filename
        assert len(content) == metadata['bytes'][filename], filename

    land = json.loads((ROOT / metadata['land']['file']).read_text(encoding='utf-8'))
    assert land['type'] == 'FeatureCollection' and 'crs' not in land
    assert land['bbox'] == [west, south, east, north]
    assert len(land['features']) == metadata['land']['features'] > 0
    vertices = 0
    for feature in land['features']:
        assert feature['type'] == 'Feature'
        geometry = feature['geometry']
        assert geometry['type'] in ('Polygon', 'MultiPolygon')
        polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
        assert polygons
        for polygon in polygons:
            assert polygon
            for ring_index, ring in enumerate(polygon):
                assert len(ring) >= 4 and ring[0] == ring[-1]
                for lon, lat in ring:
                    assert math.isfinite(lon) and math.isfinite(lat)
                    assert west <= lon <= east and south <= lat <= north
                area2 = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:]))
                assert area2 > 0 if ring_index == 0 else area2 < 0
                vertices += len(ring)

    relief = metadata['shaded_relief']
    header = (ROOT / relief['file']).read_bytes()[:33]
    assert header[:8] == b'\x89PNG\r\n\x1a\n' and header[12:16] == b'IHDR'
    width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', header[16:29])
    assert (width, height) == (relief['width'], relief['height']) == (9900, 5820)
    assert (depth, color, compression, filtering, interlace) == (8, 0, 0, 0, 0)
    a, d, b, e, c, f = map(float, (ROOT / relief['world_file']).read_text().split())
    assert d == b == 0 and a > 0 and e < 0
    for actual, expected in [(c - a / 2, west), (f - e / 2, north),
                             (c - a / 2 + width * a, east), (f - e / 2 + height * e, south)]:
        assert math.isclose(actual, expected, abs_tol=1e-9)
    assert 'WGS_1984' in (ROOT / relief['projection_file']).read_text()
    assert west <= 93.70078227974147 < 129.11170474442486 <= east
    assert south <= 16.625785315954424 < 42.916921146263945 <= north
    print(f'PASS: hashes, {len(land["features"])} land features / {vertices:,} vertices, '
          f'{width}x{height} grayscale PNG, matching geographic extent and world file.')


if __name__ == '__main__':
    verify()
