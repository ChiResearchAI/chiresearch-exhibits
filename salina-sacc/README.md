# Salina Regional Airport (KSLN) — Smart Airport Dashboard exhibit

Worked analytical example prepared for Salina Airport Authority
SAA-RFQ-2026-10 (Smart Airport Dashboard & Operational Intelligence Platform).

**Author:** Wilfred C. Ikejiofor, ChiResearch Technologies, LLC
**Date:** 13 November 2026

## What it shows

Ten years of hourly ASOS observations at KSLN (2016–2025), reduced to a
three-view common operating picture and three findings that are consequences of
the data rather than restatements of it.

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
| `index.html` | The exhibit — three views (executive, operations, maintenance). Self-contained; no build step. |
| `reproduce.py` | Re-fetches the archive and recomputes every figure. No API key needed. |
| `results.json` | Computed wind-coverage results by runway and crosswind threshold. |

## Reproducing

```
python3 reproduce.py
```

Stdlib only. Re-fetches from the Iowa Environmental Mesonet ASOS archive each
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
