// Deterministic anonymized competitor set for the sample trade-area maps.
// One source of truth shared by TradeMap.astro (dot placement + labels) and the
// distance chart in sample.astro, so map, labels, chart, and the "nearest comp"
// stat can never drift. Distances are illustrative stand-ins anchored to the
// report's nearest-comp figure; bearings use the golden angle for an organic
// spread. Letters run A.. (count <= 26 expected). Returned sorted nearest→farthest.
export function genComps(count, radiusMi, nearestMi) {
  const maxMi = radiusMi * 0.85; // keep the farthest comp inside the trade-area ring
  const comps = [];
  for (let i = 0; i < count; i++) {
    const t = count <= 1 ? 0 : i / (count - 1);
    const distMi = Math.round((nearestMi + (maxMi - nearestMi) * Math.pow(t, 0.82)) * 100) / 100;
    const bearing = (i * 137.508) % 360; // golden angle
    comps.push({ letter: String.fromCharCode(65 + i), distMi, bearing });
  }
  return comps;
}

// Convert a distance (mi) + bearing (deg from north) to a lat/lng delta from a
// center latitude. ~69 mi per degree of latitude; longitude scaled by cos(lat).
export function compOffset(distMi, bearingDeg, lat) {
  const r = (bearingDeg * Math.PI) / 180;
  const dlat = (distMi * Math.cos(r)) / 69.0;
  const dlng = (distMi * Math.sin(r)) / (69.0 * Math.cos((lat * Math.PI) / 180));
  return { dlat, dlng };
}
