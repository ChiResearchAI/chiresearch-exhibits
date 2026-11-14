"""Characterise the obstacle environment around Salina Regional Airport (SLN)
from the FAA Digital Obstacle File. Public FAA data only."""
import json, math, collections

# SLN airport reference point, from the FAA runway geometry already used
# elsewhere in this exhibit (centre of the four runway pavements).
ARP_LAT, ARP_LON = 38.7910, -97.6522
NM_PER_DEGREE_LAT = 60.0

def nautical_miles(lat, lon):
    """Great-circle distance from the airport reference point, in NM."""
    d_lat = lat - ARP_LAT
    d_lon = (lon - ARP_LON) * math.cos(math.radians(ARP_LAT))
    return math.sqrt(d_lat * d_lat + d_lon * d_lon) * NM_PER_DEGREE_LAT

def to_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None

data = json.load(open('/tmp/slnraw/obstacles.geojson'))
rows = []
for feature in data['features']:
    p = feature['properties']
    lon, lat = feature['geometry']['coordinates'][:2]
    rows.append({
        "lat": lat, "lon": lon,
        "nm": nautical_miles(lat, lon),
        "type": (p.get('Type_Code') or '').strip(),
        "agl": to_int(p.get('AGL')),
        "amsl": to_int(p.get('AMSL')),
        # FAA codes. Lighting: N none, U unknown, R red, D dual, M medium.
        # Marking:  N none, U unknown, M marked, P partial.
        # Verified: O verified by FAA, U unverified.
        "light": (p.get('Lighting') or '').strip(),
        "mark": (p.get('Marking') or '').strip(),
        "verified": (p.get('Verified') or '').strip(),
    })

for radius in (5, 10):
    near = [r for r in rows if r['nm'] <= radius]
    print(f"=== within {radius} NM of the ARP: {len(near)} obstacles ===")
    unlit   = [r for r in near if r['light'] == 'N']
    unknown = [r for r in near if r['light'] == 'U']
    unver   = [r for r in near if r['verified'] == 'U']
    print(f"  lighting 'none'    : {len(unlit):>4}  ({100*len(unlit)/len(near):.1f}%)")
    print(f"  lighting 'unknown' : {len(unknown):>4}  ({100*len(unknown)/len(near):.1f}%)")
    print(f"  not known to be lit: {len(unlit)+len(unknown):>4}  "
          f"({100*(len(unlit)+len(unknown))/len(near):.1f}%)")
    print(f"  unverified by FAA  : {len(unver):>4}  ({100*len(unver)/len(near):.1f}%)")
    tall = [r for r in near if (r['agl'] or 0) >= 200]
    tall_unlit = [r for r in tall if r['light'] in ('N', 'U')]
    print(f"  >=200 ft AGL       : {len(tall):>4}   of which not known lit: {len(tall_unlit)}")
    print()

print("=== type mix, within 10 NM ===")
near10 = [r for r in rows if r['nm'] <= 10]
for t, n in collections.Counter(r['type'] for r in near10).most_common(10):
    print(f"  {t:<18} {n}")
print()
print("=== tallest within 10 NM ===")
for r in sorted(near10, key=lambda r: -(r['agl'] or 0))[:6]:
    print(f"  {r['type']:<12} AGL {r['agl']:>4} ft  AMSL {r['amsl']:>5} ft  "
          f"{r['nm']:.1f} NM  light={r['light']} mark={r['mark']} verified={r['verified']}")

json.dump(rows, open('obstacles_rows.json', 'w'))
print(f"\nwrote {len(rows)} rows")
