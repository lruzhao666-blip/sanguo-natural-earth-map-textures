"""Build the small map runtime; originals stay at their existing paths."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image, ImageChops, ImageStat
from shapely.affinity import affine_transform
from shapely.geometry import box, mapping, MultiPolygon, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]


def encode(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def fingerprint(payload):
    return {'bytes': len(payload), 'sha256': sha256(payload).hexdigest()}


def simplify_region(points):
    """Remove straight-through vertices; retain the original first point."""
    ring = points[:-1]
    assert points[0] == points[-1] and len(ring) >= 3
    kept = []
    for i, current in enumerate(ring):
        previous, following = ring[i - 1], ring[(i + 1) % len(ring)]
        u = [current[j] - previous[j] for j in (0, 1)]
        v = [following[j] - current[j] for j in (0, 1)]
        if i == 0 or u[0] * v[1] != u[1] * v[0] or sum(a * b for a, b in zip(u, v)) <= 0:
            kept.append(current)
    result = kept + [kept[0]]
    # Re-expand every 2px edge to prove the original boundary is unchanged.
    expanded = []
    for a, b in zip(result, result[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        assert (dx == 0) != (dy == 0)
        distance = abs(dx) + abs(dy)
        assert distance % 2 == 0
        for step in range(distance // 2):
            expanded.append([a[0] + step * 2 * (dx > 0) - step * 2 * (dx < 0),
                             a[1] + step * 2 * (dy > 0) - step * 2 * (dy < 0)])
    assert expanded == ring
    return result


def build(check=False):
    source_map = load('gpkg_all_data.json')
    scenario = load('scenarios/anti-dong-zhuo-alliance/scenario.json')
    bounds = source_map['bounds_wgs84']
    west, south, east, north = [bounds[k] for k in ('min_x', 'min_y', 'max_x', 'max_y')]
    width, height = [source_map['canvas_size'][k] for k in ('w', 'h')]
    sx, sy = width / (east - west), height / (north - south)
    background_width = height * 16 / 9
    background_pad = (background_width - width) / 2
    background_west = west - background_pad / sx
    background_east = east + background_pad / sx
    background_bounds = [background_west, south, background_east, north]
    relief_size = (2880, 1620)
    assert sha256((ROOT / 'gpkg_all_data.json').read_bytes()).hexdigest() == scenario['map_reference']['sha256']
    provinces = []
    for province in source_map['provinces']:
        reduced = {key: province[key] for key in ('id', 'name', 'state', 'center_x', 'center_y')}
        reduced['polygon'] = simplify_region(province['polygon'])
        provinces.append(reduced)
    runtime_map = {key: source_map[key] for key in ('bounds_wgs84', 'canvas_size')}
    runtime_map['provinces'] = provinces

    colors = {}
    for line in (ROOT / 'scenarios/anti-dong-zhuo-alliance/势力色表.md').read_text(encoding='utf-8').splitlines():
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        if len(cells) == 7 and re.fullmatch(r'#[0-9A-F]{6}', cells[2]):
            assert cells[1] not in colors
            assert list(map(int, cells[3].split(','))) == [int(cells[2][i:i + 2], 16) for i in (1, 3, 5)]
            colors[cells[1]] = cells[2]
    assert len(colors) == len(set(colors.values())) == len(scenario['factions']) == 40
    factions = [{key: faction[key] for key in ('id', 'name', 'start_city_id')} |
                {'color': colors[faction['id']]} for faction in scenario['factions']]
    ownership = {record['city_id']: record['owner_faction_id'] for record in scenario['city_ownership']}
    assert len(ownership) == len(provinces) == len(scenario['city_ownership']) == 148
    assert set(ownership) == {p['id'] for p in provinces}
    assert all(owner is None or owner in colors for owner in ownership.values())
    assert all(ownership[f['start_city_id']] == f['id'] for f in factions)
    runtime_scenario = {
        'id': scenario['id'], 'name': scenario['name'],
        'start': {k: scenario['start'][k] for k in ('year', 'month')},
        'null_owner_label': '地方官府（待考，非空地）',
        'factions': factions, 'ownership': ownership,
    }

    source_land = load('natural-earth/ne_10m_land_asia.geojson')
    clipped = unary_union([shape(f['geometry']) for f in source_land['features']]).intersection(box(*background_bounds))
    assert clipped.is_valid and not clipped.is_empty
    project = [sx, 0, 0, -sy, -west * sx, north * sy]
    reference = affine_transform(clipped, project)
    # Use a conservative tolerance, then check the final boundary after coordinate rounding.
    simplified = reference.simplify(0.25, preserve_topology=True)
    geographic = affine_transform(simplified, [1 / sx, 0, 0, -1 / sy, west, north])
    polygons = [geographic] if geographic.geom_type == 'Polygon' else list(geographic.geoms)
    geographic = MultiPolygon([orient(p, sign=1.0) for p in polygons])
    geometry = mapping(geographic)
    def rounded(values):
        if isinstance(values[0], (int, float)):
            return [min(background_east, max(background_west, round(values[0], 6))), min(north, max(south, round(values[1], 6)))]
        return [rounded(value) for value in values]
    geometry['coordinates'] = rounded(geometry['coordinates'])
    final_land = shape(geometry)
    assert final_land.is_valid and not final_land.is_empty
    original_polygons = [clipped] if clipped.geom_type == 'Polygon' else list(clipped.geoms)
    assert len(final_land.geoms) == len(original_polygons)
    assert sum(len(p.interiors) for p in final_land.geoms) == sum(len(p.interiors) for p in original_polygons)
    assert box(*background_bounds).covers(final_land)
    land_error = reference.boundary.hausdorff_distance(affine_transform(final_land, project).boundary)
    assert land_error <= 0.501, f'Land outline error exceeds 0.5px plus rounding: {land_error}'
    land = {'type': 'FeatureCollection', 'bbox': background_bounds, 'features': [
        {'type': 'Feature', 'properties': {}, 'geometry': geometry}]}

    metadata = load('natural-earth/metadata.json')
    provenance = load('maintenance/original_relief.json')
    assert provenance['asia_crop']['sha256'] == metadata['sha256']['SR_HR_asia.png']
    assert provenance['archive']['sha256'] == metadata['sources']['shaded_relief']['archive_sha256']
    relief = metadata['shaded_relief']
    extent = metadata['extent_wgs84']
    a, d, b, e, c, f = map(float, (ROOT / 'natural-earth/SR_HR_asia.pgw').read_text().split())
    assert d == b == 0 and a > 0 and e < 0
    assert abs(c - a / 2 - extent['west']) < 1e-9
    assert abs(f - e / 2 - extent['north']) < 1e-9
    crop_box = ((background_west - extent['west']) / a, (north - extent['north']) / e,
                (background_east - extent['west']) / a, (south - extent['north']) / e)
    source_relief = ROOT / 'natural-earth' / relief['file']
    assert fingerprint(source_relief.read_bytes())['sha256'] == metadata['sha256'][relief['file']]
    with Image.open(source_relief) as image:
        assert image.mode == 'L' and image.size == (relief['width'], relief['height'])
        # Exact geographic edge crop; resize's float box avoids an integer-pixel offset.
        preview = image.resize(relief_size, Image.Resampling.LANCZOS, box=crop_box)
    buffer = BytesIO()
    preview.save(buffer, format='WEBP', quality=30, method=6)
    relief_bytes = buffer.getvalue()
    assert len(relief_bytes) < 320_000
    with Image.open(BytesIO(relief_bytes)) as decoded:
        assert decoded.format == 'WEBP' and decoded.size == relief_size
        luma_error = ImageStat.Stat(ImageChops.difference(decoded.convert('L'), preview)).mean[0]
        # Keep mean compression error below 2% of the 8-bit grayscale range.
        assert luma_error < 255 * 0.02, f'Relief compression lost too much detail: {luma_error}'
    coordinates = {
        'status': 'registered', 'scope': 'declared_bounds_affine_only',
        'status_label': '已配准（声明范围内的数学换算）',
        'independent_geographic_control_points_verified': False,
        'canvas_size': {'w': width, 'h': height}, 'bounds_lonlat': [west, south, east, north],
        'origin': 'top_left', 'pixel_convention': 'continuous_edges',
        'viewport': {'reference_css_size': [1920, 1080], 'responsive': True, 'fit': 'height',
                     'preserve_aspect_ratio': True, 'camera': 'pan_zoom', 'backing_scale': 'devicePixelRatio',
                     'initial_scale': 'viewport_height / canvas_height',
                     'initial_offset_x': '(viewport_width - canvas_width * scale) / 2',
                     'initial_offset_y': 0, 'preserve_full_north_south_extent': True},
        'canvas_to_lonlat': {'longitude': 'west + x / w * (east - west)', 'latitude': 'north - y / h * (north - south)'},
        'lonlat_to_canvas': {'x': '(longitude - west) / (east - west) * w', 'y': '(north - latitude) / (north - south) * h'},
        'land': {'file': 'assets/land.geojson', 'coordinate_order': '[longitude,latitude]'},
        'relief': {'file': 'assets/relief.webp', 'width': relief_size[0], 'height': relief_size[1],
                   'bounds_lonlat': background_bounds,
                   'draw_canvas_rect': [-background_pad, 0, background_width, height],
                   'lossy': True, 'webp_quality': 30},
    }
    # Both initial wide-screen views retain every original map vertex vertically.
    for vw, vh in ((1920, 1080), (2560, 1440)):
        scale = vh / height
        offset_x = (vw - width * scale) / 2
        for province in provinces:
            for x, y in province['polygon']:
                assert -1e-9 <= x * scale + offset_x <= vw + 1e-9
                assert -1e-9 <= y * scale <= vh + 1e-9
        assert abs(-background_pad * scale + offset_x) < 1e-9
        assert abs((-background_pad + background_width) * scale + offset_x - vw) < 1e-9
    outputs = {'map.json': encode(runtime_map), 'scenario.json': encode(runtime_scenario),
               'coordinates.json': encode(coordinates), 'assets/land.geojson': encode(land),
               'assets/relief.webp': relief_bytes}
    sources = ['gpkg_all_data.json', 'scenarios/anti-dong-zhuo-alliance/scenario.json',
               'scenarios/anti-dong-zhuo-alliance/势力色表.md', 'natural-earth/ne_10m_land_asia.geojson',
               'natural-earth/metadata.json', 'natural-earth/SR_HR_asia.pgw', 'natural-earth/SR_HR_asia.png',
               'maintenance/original_relief.json']
    manifest = {
        'sources': {name: fingerprint((ROOT / name).read_bytes()) for name in sources},
        'outputs': {name: fingerprint(payload) for name, payload in outputs.items()},
        'validation': {'provinces': len(provinces), 'factions': len(factions),
                       'source_region_vertices': sum(len(p['polygon']) for p in source_map['provinces']),
                       'runtime_region_vertices': sum(len(p['polygon']) for p in provinces),
                       'region_boundaries_exactly_preserved': True,
                       'initial_viewports_verified': [[1920, 1080], [2560, 1440]],
                       'all_region_vertices_visible_in_initial_views': True,
                       'background_north_south_extent_unchanged': True,
                       'land_max_boundary_error_canvas_px': land_error,
                       'land_crs': 'WGS84 longitude,latitude', 'land_polygons_and_holes_preserved': True,
                       'relief_mean_absolute_luma_error': luma_error, 'relief_source_pixel_crop_box': list(crop_box)},
    }
    outputs['maintenance/runtime_manifest.json'] = encode(manifest)
    if check:
        for name, payload in outputs.items():
            assert (ROOT / name).read_bytes() == payload, f'Stale output: {name}; run maintenance/build_runtime.py'
    else:
        for name, payload in outputs.items():
            destination = ROOT / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
    print(json.dumps({'passed': True, 'output_bytes': {n: len(v) for n, v in outputs.items()},
                      **manifest['validation']}, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify checked-in runtime files without writing')
    build(parser.parse_args().check)
