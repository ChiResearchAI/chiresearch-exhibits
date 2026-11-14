"""
Build the SLN airfield GeoJSON used by the Common Operating Picture exhibit.

Two sources, each chosen for a reason:

  Runways      FAA Aeronautical Information Services, Runways layer.
               Authoritative runway footprints, published by the FAA itself.
               Used because runway geometry is the thing the wind analysis
               makes a compliance determination about, so it should come
               from the regulator's own data and not a crowd-sourced map.

  Everything   OpenStreetMap. Taxiways, aprons and hangars are context for
  else         reading the airfield. They carry no compliance meaning here,
               and the FAA does not publish an Airport Mapping Database
               for SLN, so OpenStreetMap is the best public source.

Nothing in this file comes from a Salina Airport Authority system.
"""

import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

OUTPUT = "airfield.geojson"

# Salina Regional Airport (SLN) envelope: the whole airfield plus the
# Authority's adjoining industrial park.
SOUTH, WEST, NORTH, EAST = 38.765, -97.680, 38.815, -97.610

FAA_RUNWAYS_URL = (
    "https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/arcgis/rest/services"
    "/Runways/FeatureServer/0/query"
)
OSM_MAP_URL = "https://api.openstreetmap.org/api/0.6/map"

# Downloaded copies, so a re-run does not hit either service again.
CACHE_DIR = "build_cache"
FAA_RUNWAYS = os.path.join(CACHE_DIR, "faa_runways.geojson")
OSM_FILE = os.path.join(CACHE_DIR, "sln_osm.xml")


def download(url, destination, description):
    """Fetch a URL to a file, unless it has already been fetched."""
    if os.path.exists(destination):
        print(f"using cached {description}: {destination}")
        return

    os.makedirs(CACHE_DIR, exist_ok=True)
    print(f"fetching {description} ...")
    request = urllib.request.Request(
        url, headers={"User-Agent": "ChiResearch-SLN-exhibit/1.0"}
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    with open(destination, "wb") as handle:
        handle.write(payload)
    print(f"  wrote {len(payload)/1024:.0f} KB")


def download_sources():
    faa_params = {
        "geometry": f"{WEST},{SOUTH},{EAST},{NORTH}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "f": "geojson",
        "outSR": "4326",
    }
    download(FAA_RUNWAYS_URL + "?" + urllib.parse.urlencode(faa_params),
             FAA_RUNWAYS, "FAA runway polygons")

    osm_query = urllib.parse.urlencode({"bbox": f"{WEST},{SOUTH},{EAST},{NORTH}"})
    download(OSM_MAP_URL + "?" + osm_query, OSM_FILE, "OpenStreetMap airfield extract")

# The airfield proper. Buildings outside this box are town, not airport,
# and would only add noise to the map.
AIRFIELD_SOUTH, AIRFIELD_WEST = 38.770, -97.672
AIRFIELD_NORTH, AIRFIELD_EAST = 38.812, -97.620


def load_osm(path):
    """Return (nodes, ways). nodes maps id -> (lon, lat). ways maps id -> dict."""
    tree = ET.parse(path)
    root = tree.getroot()

    nodes = {}
    for node in root.findall("node"):
        node_id = node.get("id")
        nodes[node_id] = (float(node.get("lon")), float(node.get("lat")))

    ways = {}
    for way in root.findall("way"):
        way_id = way.get("id")
        tags = {}
        for tag in way.findall("tag"):
            tags[tag.get("k")] = tag.get("v")
        refs = []
        for nd in way.findall("nd"):
            refs.append(nd.get("ref"))
        ways[way_id] = {"tags": tags, "refs": refs}

    return nodes, ways


def coords_for(way, nodes):
    """Resolve a way's node references into a coordinate list."""
    points = []
    for ref in way["refs"]:
        if ref in nodes:
            points.append(list(nodes[ref]))
    return points


def is_closed(points):
    return len(points) > 3 and points[0] == points[-1]


def centroid(points):
    lon = sum(p[0] for p in points) / len(points)
    lat = sum(p[1] for p in points) / len(points)
    return lon, lat


def inside_airfield(points):
    lon, lat = centroid(points)
    return (AIRFIELD_WEST <= lon <= AIRFIELD_EAST
            and AIRFIELD_SOUTH <= lat <= AIRFIELD_NORTH)


def main():
    download_sources()
    nodes, ways = load_osm(OSM_FILE)
    features = []

    # ---- runways: FAA polygons -------------------------------------------
    faa = json.load(open(FAA_RUNWAYS))
    runway_count = 0
    helipad_count = 0
    for feature in faa["features"]:
        props = feature["properties"]
        designator = (props.get("DESIGNATOR") or "").strip()
        # Helipads are designated H1..H6 here; runways carry a NN/NN form.
        if "/" in designator:
            kind = "runway"
            runway_count += 1
        else:
            kind = "helipad"
            helipad_count += 1
        features.append({
            "type": "Feature",
            "geometry": feature["geometry"],
            "properties": {
                "layer": kind,
                "name": designator,
                "length_ft": props.get("LENGTH"),
                "width_ft": props.get("WIDTH"),
                "surface": props.get("COMP_CODE"),
                "source": "FAA AIS Runways",
            },
        })

    # ---- taxiways, aprons, hangars: OpenStreetMap ------------------------
    counts = {"taxiway": 0, "apron": 0, "hangar": 0}
    for way_id, way in ways.items():
        tags = way["tags"]
        aeroway = tags.get("aeroway")
        building = tags.get("building")

        if aeroway == "taxiway":
            layer, geom_type = "taxiway", "LineString"
        elif aeroway == "apron":
            layer, geom_type = "apron", "Polygon"
        elif aeroway == "hangar" or building == "hangar":
            layer, geom_type = "hangar", "Polygon"
        else:
            continue

        points = coords_for(way, nodes)
        if len(points) < 2:
            continue
        if not inside_airfield(points):
            continue

        if geom_type == "Polygon":
            if not is_closed(points):
                points = points + [points[0]]
            geometry = {"type": "Polygon", "coordinates": [points]}
        else:
            geometry = {"type": "LineString", "coordinates": points}

        counts[layer] += 1
        features.append({
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "layer": layer,
                "name": tags.get("ref") or tags.get("name") or "",
                "source": "OpenStreetMap",
            },
        })

    collection = {"type": "FeatureCollection", "features": features}
    json.dump(collection, open(OUTPUT, "w"))

    print(f"runways  (FAA): {runway_count}")
    print(f"helipads (FAA): {helipad_count}")
    for layer, n in counts.items():
        print(f"{layer:9s}(OSM): {n}")
    print(f"total features: {len(features)}")
    import os
    print(f"file size: {os.path.getsize(OUTPUT)/1024:.0f} KB")


main()
