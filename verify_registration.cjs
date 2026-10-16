const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const read = name => fs.readFileSync(path.join(__dirname, name));
const mapBytes = read('gpkg_all_data.json');
const map = JSON.parse(mapBytes);
const registration = JSON.parse(read('registration.json'));
const { w: width, h: height } = map.canvas_size;
const { min_x: west, max_x: east, min_y: south, max_y: north } = map.bounds_wgs84;
assert(width > 0 && height > 0 && west < east && south < north);
assert.equal(crypto.createHash('sha256').update(mapBytes).digest('hex'), registration.map_sha256);
assert.equal(registration.status, 'registered');
assert.equal(registration.scope, 'mathematical_canvas_to_wgs84');
assert.equal(registration.validation.independent_geographic_registration_verified, false);
assert.deepEqual(registration.canvas, {
  width, height, origin: 'top_left', x_axis: 'east', y_axis: 'south',
  coordinate_convention: 'continuous_canvas_edge',
});
assert.deepEqual(registration.wgs84_bounds, { west, south, east, north });
const toLonLat = ([x, y]) => [
  west + x / width * (east - west),
  north - y / height * (north - south),
];
const toCanvas = ([longitude, latitude]) => [
  (longitude - west) / (east - west) * width,
  (north - latitude) / (north - south) * height,
];
for (const [corner, point, expected] of [
  ['top_left', [0, 0], [west, north]],
  ['top_right', [width, 0], [east, north]],
  ['bottom_left', [0, height], [west, south]],
  ['bottom_right', [width, height], [east, south]],
]) {
  assert.deepEqual(registration.corner_mapping[corner], expected);
  assert.deepEqual(toLonLat(point), expected);
  assert.deepEqual(toCanvas(expected), point);
}
let vertices = 0;
let maxRoundTripError = 0;
for (const province of map.provinces) {
  assert.equal(province.polygon.length, province.num_vertices);
  assert.deepEqual(province.polygon[0], province.polygon.at(-1));
  for (const point of [...province.polygon, [province.center_x, province.center_y]]) {
    assert.equal(point.length, 2);
    const [x, y] = point;
    assert(point.every(Number.isFinite));
    assert(x >= 0 && x <= width && y >= 0 && y <= height, `${province.id}: canvas range`);
    const [longitude, latitude] = toLonLat(point);
    assert(longitude >= west && longitude <= east && latitude >= south && latitude <= north, `${province.id}: WGS84 range`);
    const roundTrip = toCanvas([longitude, latitude]);
    maxRoundTripError = Math.max(maxRoundTripError, Math.abs(roundTrip[0] - x), Math.abs(roundTrip[1] - y));
  }
  vertices += province.polygon.length;
}
assert.equal(map.provinces.length, 148);
assert.equal(vertices, registration.validation.polygon_vertices_checked);
assert(maxRoundTripError < 1e-9, `round-trip error: ${maxRoundTripError}`);
assert.equal(maxRoundTripError, registration.validation.round_trip_max_abs_error);
// Independent checks: known WGS84 raster/world-file geometry and both crop sizes.
const metadata = JSON.parse(read('natural-earth/metadata.json'));
const crop = JSON.parse(read('natural-earth/derived/SR_sanguo.json'));
const [a, d, b, e, c, f] = read('natural-earth/SR_HR_asia.pgw').toString().trim().split(/\s+/).map(Number);
assert(d === 0 && b === 0 && a > 0 && e < 0);
const extent = metadata.extent_wgs84;
for (const point of [[0, 0], [width, height], [width / 2, height / 2]]) {
  const [lon, lat] = toLonLat(point);
  const sx = (lon - extent.west) * 60;
  const sy = (extent.north - lat) * 60;
  assert(sx >= 0 && sx <= metadata.shaded_relief.width && sy >= 0 && sy <= metadata.shaded_relief.height);
  assert(Math.abs(c + (sx - 0.5) * a - lon) < 1e-9);
  assert(Math.abs(f + (sy - 0.5) * e - lat) < 1e-9);
  const [cw, cs, ce, cn] = crop.bounds_lonlat;
  assert(lon >= cw && lon <= ce && lat >= cs && lat <= cn);
  for (const size of [1, 0.5]) {
    const cx = (lon - cw) * 60 * size;
    const cy = (cn - lat) * 60 * size;
    assert(cx >= 0 && cx <= crop.width * size && cy >= 0 && cy <= crop.height * size);
    assert(Math.abs(cw + cx / (60 * size) - lon) < 1e-9);
    assert(Math.abs(cn - cy / (60 * size) - lat) < 1e-9);
  }
}
console.log(`PASS: affine mapping, ${vertices.toLocaleString()} vertices + 148 labels, max round-trip error ${maxRoundTripError} px; world file and both relief crops.`);
