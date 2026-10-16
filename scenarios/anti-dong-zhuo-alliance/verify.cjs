const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const scenario = JSON.parse(fs.readFileSync(path.join(__dirname, 'scenario.json'), 'utf8'));
const mapPath = process.argv[2] || path.join(__dirname, '../../gpkg_all_data.json');
const mapBytes = fs.readFileSync(mapPath);
const map = JSON.parse(mapBytes);
const hash = crypto.createHash('sha256').update(mapBytes).digest('hex');
assert.equal(hash, scenario.map_reference.sha256, 'Map version changed; review the scenario mapping before updating its checksum');
assert.equal(scenario.factions.length, 40);
assert.equal(map.provinces.length, 148);
assert.equal(scenario.city_ownership.length, map.provinces.length);
assert.equal(new Set(scenario.factions.map(f => f.id)).size, scenario.factions.length);
assert.equal(new Set(scenario.factions.map(f => f.name)).size, scenario.factions.length);
assert.equal(new Set(scenario.city_ownership.map(c => c.city_id)).size, map.provinces.length);
const factions = new Map(scenario.factions.map(f => [f.id, f]));
const cities = new Map(scenario.city_ownership.map(c => [c.city_id, c]));
const sourceIds = new Set(scenario.sources.map(s => s.id));
assert.equal(sourceIds.size, scenario.sources.length);
for (const record of [...scenario.factions, ...scenario.city_ownership]) {
  assert(record.source_ids.length > 0, 'Missing source references');
  for (const id of record.source_ids) assert(sourceIds.has(id), `Unknown source: ${id}`);
}
for (const province of map.provinces) {
  const city = cities.get(province.id);
  assert(city, `Missing city: ${province.id}`);
  assert.equal(city.name, province.name);
  assert.equal(city.map_state, province.state);
  assert(city.note.trim());
  assert(Object.hasOwn(scenario.basis_labels, city.basis));
  assert(!Object.hasOwn(city, 'polygon') && !Object.hasOwn(city, 'capital'));
  if (city.owner_faction_id === null) assert.equal(city.basis, 'local_administration');
  else assert(factions.has(city.owner_faction_id), `Unknown owner: ${city.owner_faction_id}`);
}
assert.equal(scenario.owner_semantics.null_is_empty, false);
for (const faction of scenario.factions) {
  assert.equal(faction.playable, true);
  assert.equal(cities.get(faction.start_city_id)?.owner_faction_id, faction.id, `Invalid start: ${faction.id}`);
  assert(scenario.city_ownership.some(c => c.owner_faction_id === faction.id));
  assert(faction.historical_note && faction.design_note);
}
assert.equal(scenario.start.year, 190);
assert.equal(scenario.start.month, 1);
const roles = {documented_participant_ids: 'documented_participant', campaign_partner_ids: 'campaign_partner'};
const participants = [...scenario.coalition.documented_participant_ids, ...scenario.coalition.campaign_partner_ids];
assert.equal(new Set(participants).size, participants.length);
for (const [field, role] of Object.entries(roles)) {
  assert.deepEqual(scenario.coalition[field].slice().sort(), scenario.factions.filter(f => f.coalition_role === role).map(f => f.id).sort());
}
assert(participants.includes(scenario.coalition.leader_faction_id));
assert.equal(factions.get(scenario.coalition.target_faction_id)?.coalition_role, 'target');
assert(!participants.includes(scenario.coalition.target_faction_id));
// These guard against copying later Wei/Wu labels or later conquests into 190.
assert.equal(cities.get('lujiang_wei').owner_faction_id, 'lu_kang');
assert.equal(cities.get('lujiang_wu').owner_faction_id, 'lu_kang');
assert.equal(cities.get('jiangxia_wei').owner_faction_id, 'liu_biao');
assert.equal(cities.get('jiangxia_wu').owner_faction_id, 'liu_biao');
assert.equal(cities.get('yecheng').owner_faction_id, 'han_fu');
assert.equal(cities.get('huainan').owner_faction_id, 'chen_wen');
assert.equal(cities.get('chenliu').owner_faction_id, 'zhang_miao');
assert.equal(cities.get('dongjun').owner_faction_id, 'qiao_mao');
assert.equal(cities.get('jiaozhi').owner_faction_id, 'shi_xie');
assert.equal(cities.get('kuaiji').owner_faction_id, null);
const ownershipDoc = fs.readFileSync(path.join(__dirname, '势力与城池归属.md'), 'utf8');
for (const city of scenario.city_ownership) assert(ownershipDoc.includes(`| ${city.city_id} | ${city.name} | ${factions.get(city.owner_faction_id)?.name || '地方官府（待考）'} |`), `Review table stale: ${city.city_id}`);
const colorTable = fs.readFileSync(path.join(__dirname, '势力色表.md'), 'utf8');
const colorRows = colorTable.split('\n').filter(line => /^\| .+ \| [a-z_]+ \| #[0-9A-F]{6} \| /.test(line)).map(line => line.split('|').slice(1, -1).map(cell => cell.trim()));
assert.equal(colorRows.length, scenario.factions.length);
assert.equal(new Set(colorRows.map(row => row[1])).size, scenario.factions.length);
assert.equal(new Set(colorRows.map(row => row[2])).size, scenario.factions.length);
for (const [name, id, hex, rgb, donor, kind, source] of colorRows) {
  assert.equal(factions.get(id)?.name, name, 'Color table faction mismatch');
  assert(/^#[0-9A-F]{6}$/.test(hex));
  assert.equal(rgb, [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(', '));
  assert(donor && ['同名势力原色', '新增势力借色'].includes(kind));
  assert(['C01', 'C02'].includes(source));
}
const basisCounts = {};
for (const city of scenario.city_ownership) basisCounts[city.basis] = (basisCounts[city.basis] || 0) + 1;
const assigned = scenario.city_ownership.filter(c => c.owner_faction_id !== null).length;
console.log(JSON.stringify({
  passed: true, faction_colors: colorRows.length, unique_faction_colors: new Set(colorRows.map(row => row[2])).size, basis_counts: basisCounts, factions: scenario.factions.length, cities: cities.size,
  assigned_cities: assigned, local_administration_cities: cities.size - assigned,
  documented_coalition_participants: scenario.coalition.documented_participant_ids.length,
  other_campaign_partners: scenario.coalition.campaign_partner_ids.length,
  map_sha256: hash, checks: ['unique IDs/names', 'complete map coverage', 'start city ownership', 'source references', 'coalition roles', 'local authority semantics', 'key timeline choices', 'exact map checksum', 'human review table matches JSON', '40 unique HEX colors and RGB conversion']
}, null, 2));
