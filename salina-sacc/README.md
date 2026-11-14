# Salina Regional Airport (KSLN) — Smart Airport Dashboard exhibit

Worked analytical example prepared for Salina Airport Authority
SAA-RFQ-2026-10 (Smart Airport Dashboard & Operational Intelligence Platform).

**Author:** Wilfred C. Ikejiofor, ChiResearch Technologies, LLC
**Date:** 13 November 2026

## What it shows

Ten years of hourly ASOS observations at KSLN (2016–2025), reduced to a
four-view common operating picture — executive leadership, airport operations,
maintenance and an airfield GIS — and three findings that are consequences of
the data rather than restatements of it.

The Authority has stated it maintains no enterprise GIS platform and that GIS
capability is an initial priority. The GIS view is that capability, standing:
the airfield as an interactive map with the wind-coverage determination carried
on the runway geometry itself. Changing the allowable crosswind component
recolours the airfield by Runway Design Code; changing the heading convention
moves Runway 17/35 across the 95% line while the reader watches.

**Finding 1 — Runway 17/35 does not meet the FAA 95% recommendation for the
smallest aircraft.** Wind coverage for Runway 17/35 at the 10.5-knot allowable
crosswind component (Runway Design Code A-I and B-I) is 94.74%, against the 95%
coverage recommended in AC 150/5300-13B Change 1. The shortfall is specific to
the smallest design aircraft; at 13 knots and above the runway clears the
recommendation comfortably. Reporting usability as a single airport-wide status
hides this, which is why the exhibit reports usability by aircraft category.

**Finding 2 — The magnetic-versus-true convention reverses that verdict.** FAA
runway designators are magnetic; METAR wind directions are true. Published
magnetic variation at SLN is 7° East. Treating the 170° designator as a true
bearing instead of converting it returns 95.29% for the same runway, the same
threshold and the same observations — above the recommendation rather than
below it. A dashboard that silently picks one convention reports a passing or
failing runway depending on an assumption its reader cannot see. Both figures
are published here for that reason.

**Finding 3 — Ceiling, not visibility, drives below-VFR conditions at KSLN.**
Across 11,331 observations below VFR, ceiling alone was the binding constraint
in 79.3%, visibility alone in 15.4%, and the two tied in 5.3%. The seasonal
spread is wide: January runs at 23.47% below VFR against June at 3.69%, a
factor of 6.4. This is a staffing and maintenance-window fact, not a weather
observation.

## Files

| File | What it is |
|---|---|
| `index.html` | The exhibit — four views (executive, operations, maintenance, airfield GIS). No build step. |
| `reproduce.py` | Re-fetches the archive and recomputes every figure. No API key needed. |
| `results.json` | Computed wind-coverage results by runway and crosswind threshold. |
| `airfield.geojson` | Airfield geometry: 4 runway pavements and 6 helipads from the FAA, 16 taxiway centrelines, 3 aprons and 13 hangars from OpenStreetMap. |
| `build_airfield.py` | Rebuilds `airfield.geojson` from both public sources. |
| `leaflet.css`, `leaflet.js` | Leaflet 1.9.4, vendored so the map has no CDN dependency. |

## Map sources, and why each one

Runway pavements come from the **FAA Aeronautical Information Services
`Runways` layer** — the regulator's own geometry. Runway shape is what the wind
analysis makes a compliance determination about, so it should not come from a
crowd-sourced map. The FAA's published dimensions independently agree with the
figures used throughout: 17/35 at 12,301 × 150 ft, 12/30 at 6,510 × 100,
18/36 at 4,301 × 75, 04/22 at 3,648 × 75.

Taxiways, aprons and hangars come from **OpenStreetMap**. They are context for
reading the airfield and carry no compliance meaning here, and the FAA publishes
no Airport Mapping Database for SLN.

**No basemap tiles are requested from any third party.** The map is vector-only,
so the exhibit cannot break because somebody else's tile server is down, and no
outside party learns who is reading it.

## Reproducing

```
python3 reproduce.py
```

Stdlib only, and `python3 build_airfield.py` likewise rebuilds the map data.
`reproduce.py` re-fetches from the Iowa Environmental Mesonet ASOS archive each
run (station SLN, `report_type=3`, hourly routine observations), so a later
observation period changes the output rather than silently reusing a cached
file. The script ends with three checks that re-derive the published findings
and fail loudly if any no longer holds.

## Population note

Every figure in this exhibit is computed on one population: the 85,824
observations of the 87,328 retrieved that carry both a wind direction and a wind
speed. Wind coverage requires both fields, so that subset is the only one on
which a coverage figure can be computed at all. Below-VFR rates are a function
of ceiling and visibility and could be computed on the full set, which would
return 22.80% for January against 3.65% for June — a factor of 6.25 rather than
6.4. Both denominators are defensible in isolation; mixing them inside one
document is not, so the wind-bearing population governs throughout and the
alternative is stated here rather than left implicit.

## Limits

Stated in full in the exhibit and printed by `reproduce.py`. In short: ASOS is a
point sensor at one location on the airfield and is not a model of wind across
it; hourly routine observations undercount short-lived gust events, and gusts
are excluded from the crosswind computation, which uses sustained speed as the
FAA method specifies; the AC 150/5300-13B wind-coverage method assumes the
observation set is representative of the long-term wind climate, and ten years
is the minimum period it contemplates; magnetic variation drifts, so the 7° East
figure is current rather than constant across the whole observation period;
flight-category thresholds follow the standard VFR/MVFR/IFR/LIFR definitions
and a different ceiling or visibility cut would move the below-VFR share;
and runway usability computed from wind alone is not an operational
availability figure, which also depends on surface condition, lighting,
approach minimums and NOTAMs that this exhibit does not model.

On the map specifically: this is a prototype built for a submittal, not a
deployed system and not a prior client implementation. Taxiway, apron and hangar
geometry is crowd-sourced and has not been surveyed. The Authority holds the
surveyed airfield geometry in its electronic Airport Layout Plan; in an
engagement the eALP becomes the authoritative source and the public geometry
here is retired rather than carried forward.
