"""
Reproduce every figure in the Salina Regional Airport (SLN) wind coverage exhibit.

    python3 reproduce.py

No API key, no credentials, no local data file required. The script fetches ten
complete years of SLN surface observations from a public archive and recomputes
every number that appears in index.html and in the ChiResearch Statement of
Qualifications for SAA-RFQ-2026-10.

Sources
    Observations : Iowa Environmental Mesonet ASOS archive, Iowa State University,
                   station SLN, hourly routine reports (report_type=3),
                   1 January 2016 - 31 December 2025 UTC.
    Runway record: FAA airport and runway record for KSLN. Dimensions and the
                   magnetic variation below are transcribed from it.
    Standard     : FAA Advisory Circular 150/5300-13B Change 1, "Airport Design",
                   active, issued 16 August 2024. It supersedes AC 150/5300-13A,
                   which was cancelled 31 March 2022.

Author: Wilfred C. Ikejiofor, ChiResearch Technologies, LLC
"""

import csv
import io
import json
import math
import urllib.request
from collections import defaultdict

# ---------------------------------------------------------------------------
# Configuration — every assumption in this exhibit is a named constant here
# ---------------------------------------------------------------------------

ARCHIVE_URL = (
    "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
    "?station=SLN"
    "&data=drct&data=sknt&data=gust&data=vsby&data=skyc1&data=skyl1&data=tmpf"
    "&year1=2016&month1=1&day1=1"
    "&year2=2026&month2=1&day2=1"
    "&tz=Etc/UTC&format=onlycomma&latlon=no&missing=M&trace=T"
    "&direct=no&report_type=3"
)

# FAA runway designators are MAGNETIC. METAR wind directions are TRUE.
# The published magnetic variation at SLN is 7 degrees East, so:
#     true heading = magnetic heading + east variation
# Getting this wrong is the subject of Check 1 at the end of this script.
MAGNETIC_VARIATION_EAST = 7

RUNWAYS = [
    {"name": "17/35", "magnetic_heading": 170, "length_ft": 12301, "width_ft": 150},
    {"name": "12/30", "magnetic_heading": 120, "length_ft": 6510, "width_ft": 100},
    {"name": "18/36", "magnetic_heading": 180, "length_ft": 4301, "width_ft": 75},
    {"name": "04/22", "magnetic_heading": 40, "length_ft": 3648, "width_ft": 75},
]

# The four allowable crosswind components in AC 150/5300-13B, by Runway Design Code:
#     A-I and B-I          10.5 kt
#     A-II and B-II        13   kt
#     C-I through D-III    16   kt
#     A-IV through D-VI    20   kt
CROSSWIND_THRESHOLDS_KT = [10.5, 13.0, 16.0, 20.0]

# FAA recommends a runway system provide at least this much wind coverage.
REQUIRED_COVERAGE_PERCENT = 95.0

COMPASS_POINTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
SPEED_BANDS = [(0, 6), (6, 11), (11, 17), (17, 22), (22, 9999)]
SPEED_BAND_LABELS = ["0-5", "6-10", "11-16", "17-21", "22+"]

STRONG_WIND_THRESHOLD_KT = 30


# ---------------------------------------------------------------------------
# 1. Fetch
# ---------------------------------------------------------------------------
def fetch_observations():
    """Download the archive and return it as a list of row dictionaries."""
    print("Fetching ten years of SLN observations ...")
    with urllib.request.urlopen(ARCHIVE_URL, timeout=300) as response:
        text = response.read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    print(f"  {len(rows):,} rows retrieved")
    return rows


# ---------------------------------------------------------------------------
# 2. Crosswind
# ---------------------------------------------------------------------------
def crosswind_component_kt(wind_direction_true, wind_speed_kt, runway_true_heading):
    """
    The crosswind component is the part of the wind acting across the runway
    centerline:

        crosswind = speed * sin(angle between the wind and the runway)

    The absolute value is taken because a runway is usable from either end, and
    a crosswind from the left at one end is the same magnitude as a crosswind
    from the right at the other.
    """
    angle_between_degrees = wind_direction_true - runway_true_heading
    angle_between_radians = math.radians(angle_between_degrees)
    return abs(wind_speed_kt * math.sin(angle_between_radians))


def true_heading_of(runway, apply_variation=True):
    """Runway heading in TRUE degrees, which is what METAR wind is measured in."""
    if apply_variation:
        return runway["magnetic_heading"] + MAGNETIC_VARIATION_EAST
    return runway["magnetic_heading"]


# ---------------------------------------------------------------------------
# 3. Wind coverage
# ---------------------------------------------------------------------------
def usable_wind_observations(rows):
    """
    Keep only observations that carry BOTH a wind direction and a wind speed.

    An observation missing either one cannot be placed on a wind rose, so
    counting it would quietly change the denominator of every percentage below.
    """
    usable = []
    dropped = 0
    for row in rows:
        if row["drct"] in ("M", "") or row["sknt"] in ("M", ""):
            dropped += 1
            continue
        usable.append({
            "timestamp": row["valid"],
            "wind_direction_true": float(row["drct"]),
            "wind_speed_kt": float(row["sknt"]),
            "visibility_sm": row["vsby"],
            "sky_cover": row["skyc1"],
            "ceiling_ft": row["skyl1"],
        })
    return usable, dropped


def compute_coverage(observations, apply_variation=True):
    """
    For each allowable crosswind, the share of observations each runway can
    accept, and the share the whole runway system can accept.

    Calm wind is handled explicitly rather than implicitly: at zero knots the
    crosswind component is zero against every runway, so a calm observation is
    covered by all of them.
    """
    results = {}
    for threshold in CROSSWIND_THRESHOLDS_KT:
        covered_per_runway = {runway["name"]: 0 for runway in RUNWAYS}
        covered_by_any_runway = 0
        covered_by_primary_pair = 0

        for observation in observations:
            any_runway_accepts = False
            primary_pair_accepts = False

            for runway in RUNWAYS:
                crosswind = crosswind_component_kt(
                    observation["wind_direction_true"],
                    observation["wind_speed_kt"],
                    true_heading_of(runway, apply_variation),
                )
                if crosswind <= threshold:
                    covered_per_runway[runway["name"]] += 1
                    any_runway_accepts = True
                    if runway["name"] in ("17/35", "12/30"):
                        primary_pair_accepts = True

            if any_runway_accepts:
                covered_by_any_runway += 1
            if primary_pair_accepts:
                covered_by_primary_pair += 1

        total = len(observations)
        results[threshold] = {
            "per_runway_percent": {
                name: 100.0 * count / total for name, count in covered_per_runway.items()
            },
            "all_four_runways_percent": 100.0 * covered_by_any_runway / total,
            "primary_pair_percent": 100.0 * covered_by_primary_pair / total,
        }
    return results


# ---------------------------------------------------------------------------
# 4. Flight category
# ---------------------------------------------------------------------------
def flight_category_components(observation):
    """
    Return the category implied by the ceiling alone and by the visibility alone.

    Ceiling is the lowest BROKEN, OVERCAST or VERTICAL VISIBILITY layer. The two
    are returned separately on purpose: the point of this part of the exhibit is
    that they disagree, and that "how many bad-weather hours" has no single
    answer until somebody certifies which element decides.
    """
    sky_cover = observation["sky_cover"]
    ceiling_text = observation["ceiling_ft"]
    visibility_text = observation["visibility_sm"]

    ceiling = None
    if sky_cover in ("BKN", "OVC", "VV") and ceiling_text not in ("M", "", None):
        try:
            ceiling = float(ceiling_text)
        except ValueError:
            ceiling = None

    try:
        visibility = float(visibility_text)
    except (TypeError, ValueError):
        visibility = None

    if ceiling is None:
        by_ceiling = "VFR"
    elif ceiling < 500:
        by_ceiling = "LIFR"
    elif ceiling < 1000:
        by_ceiling = "IFR"
    elif ceiling <= 3000:
        by_ceiling = "MVFR"
    else:
        by_ceiling = "VFR"

    if visibility is None:
        by_visibility = "VFR"
    elif visibility < 1:
        by_visibility = "LIFR"
    elif visibility < 3:
        by_visibility = "IFR"
    elif visibility <= 5:
        by_visibility = "MVFR"
    else:
        by_visibility = "VFR"

    return by_ceiling, by_visibility


# ---------------------------------------------------------------------------
# 5. Run everything and print it
# ---------------------------------------------------------------------------
def main():
    rows = fetch_observations()
    observations, dropped = usable_wind_observations(rows)
    total = len(observations)
    calm = sum(1 for o in observations if o["wind_speed_kt"] == 0)

    coverage = compute_coverage(observations, apply_variation=True)
    coverage_uncorrected = compute_coverage(observations, apply_variation=False)

    # --- flight category -----------------------------------------------------
    severity = {"VFR": 0, "MVFR": 1, "IFR": 2, "LIFR": 3}
    category_counts = defaultdict(int)
    driver_counts = defaultdict(int)
    month_total = defaultdict(int)
    month_below_vfr = defaultdict(int)

    for observation in observations:
        by_ceiling, by_visibility = flight_category_components(observation)
        worse = by_ceiling if severity[by_ceiling] >= severity[by_visibility] else by_visibility
        category_counts[worse] += 1

        month = int(observation["timestamp"][5:7])
        month_total[month] += 1

        if worse != "VFR":
            month_below_vfr[month] += 1
            if severity[by_ceiling] > severity[by_visibility]:
                driver_counts["ceiling only"] += 1
            elif severity[by_visibility] > severity[by_ceiling]:
                driver_counts["visibility only"] += 1
            else:
                driver_counts["both agree"] += 1

    below_vfr_total = total - category_counts["VFR"]

    # --- strong wind days ----------------------------------------------------
    strong_wind_days = {
        o["timestamp"][:10] for o in observations
        if o["wind_speed_kt"] >= STRONG_WIND_THRESHOLD_KT
    }

    # --- report --------------------------------------------------------------
    print()
    print(f"Rows retrieved            : {len(rows):,}")
    print(f"Observations used         : {total:,}")
    print(f"Dropped, missing wind     : {dropped:,}")
    print(f"Calm observations         : {calm:,}  ({100.0*calm/total:.2f}%)")
    print()
    print("ALL-WEATHER WIND COVERAGE (%), by allowable crosswind component")
    print(f"{'Runway':<13}" + "".join(f"{t:>10}" for t in CROSSWIND_THRESHOLDS_KT))
    for runway in RUNWAYS:
        line = f"{runway['name']:<13}"
        for threshold in CROSSWIND_THRESHOLDS_KT:
            line += f"{coverage[threshold]['per_runway_percent'][runway['name']]:>10.2f}"
        print(line)
    line = f"{'17/35+12/30':<13}"
    for threshold in CROSSWIND_THRESHOLDS_KT:
        line += f"{coverage[threshold]['primary_pair_percent']:>10.2f}"
    print(line)
    line = f"{'ALL FOUR':<13}"
    for threshold in CROSSWIND_THRESHOLDS_KT:
        line += f"{coverage[threshold]['all_four_runways_percent']:>10.2f}"
    print(line)
    print(f"\nFAA recommends at least {REQUIRED_COVERAGE_PERCENT}% coverage.")

    print()
    print("CHECK 1 - WHAT THE MAGNETIC VARIATION IS WORTH")
    print("Same observations, same formula. Only the heading convention differs.")
    for threshold in [10.5]:
        for runway in RUNWAYS:
            name = runway["name"]
            corrected = coverage[threshold]["per_runway_percent"][name]
            uncorrected = coverage_uncorrected[threshold]["per_runway_percent"][name]
            verdict_corrected = "over " if corrected >= REQUIRED_COVERAGE_PERCENT else "UNDER"
            verdict_uncorrected = "over " if uncorrected >= REQUIRED_COVERAGE_PERCENT else "UNDER"
            flip = "   <-- the verdict reverses" if verdict_corrected != verdict_uncorrected else ""
            print(f"  {name:<8} at {threshold} kt   corrected {corrected:6.2f} ({verdict_corrected})"
                  f"   uncorrected {uncorrected:6.2f} ({verdict_uncorrected}){flip}")

    print()
    print("FLIGHT CATEGORY DISTRIBUTION")
    for category in ("VFR", "MVFR", "IFR", "LIFR"):
        count = category_counts[category]
        print(f"  {category:<6} {count:>8,}   {100.0*count/total:>6.2f}%")

    print()
    print(f"WHAT PUT SLN BELOW VFR, across {below_vfr_total:,} hours")
    for label, count in sorted(driver_counts.items(), key=lambda item: -item[1]):
        print(f"  {label:<18} {count:>8,}   {100.0*count/below_vfr_total:>6.2f}%")

    print()
    print("BELOW-VFR RATE BY CALENDAR MONTH (%)")
    monthly = {m: 100.0 * month_below_vfr[m] / month_total[m] for m in range(1, 13)}
    for month in range(1, 13):
        print(f"  {month:>2}: {monthly[month]:>5.2f}")
    worst = max(monthly, key=monthly.get)
    best = min(monthly, key=monthly.get)
    print(f"  worst month {worst} at {monthly[worst]:.2f}%, best month {best} at "
          f"{monthly[best]:.2f}% - a factor of {monthly[worst]/monthly[best]:.1f}")

    print()
    print(f"HIGH-WIND DAYS at or above {STRONG_WIND_THRESHOLD_KT} kt sustained")
    print(f"  {len(strong_wind_days):,} days in ten years "
          f"({len(strong_wind_days)/10.0:.1f} per year)")

    # --- write results.json so the numbers can be checked without re-running ---
    output = {
        "source": "Iowa Environmental Mesonet ASOS archive, station SLN",
        "period": "2016-01-01 through 2025-12-31 UTC",
        "standard": "FAA AC 150/5300-13B Change 1, Airport Design, active",
        "rows_retrieved": len(rows),
        "observations_used": total,
        "observations_dropped_missing_wind": dropped,
        "calm_observations": calm,
        "calm_percent": round(100.0 * calm / total, 2),
        "magnetic_variation_east_degrees": MAGNETIC_VARIATION_EAST,
        "runways": RUNWAYS,
        "coverage_corrected": {str(k): v for k, v in coverage.items()},
        "coverage_uncorrected": {str(k): v for k, v in coverage_uncorrected.items()},
        "flight_category_counts": dict(category_counts),
        "below_vfr_total": below_vfr_total,
        "below_vfr_driver_counts": dict(driver_counts),
        "monthly_below_vfr_percent": {str(m): round(v, 2) for m, v in monthly.items()},
        "strong_wind_days_total": len(strong_wind_days),
        "strong_wind_days_per_year": round(len(strong_wind_days) / 10.0, 1),
    }
    with open("results.json", "w") as handle:
        json.dump(output, handle, indent=2)
    print("\nWrote results.json")

    # --- limits, stated rather than buried ------------------------------------
    print()
    print("LIMITS OF THIS ANALYSIS")
    print("  1. Runway true headings are derived from the FAA magnetic designators")
    print("     plus the published 7E variation, not from surveyed bearings. The")
    print("     Authority holds surveyed geometry in its electronic Airport Layout")
    print("     Plan; in an engagement the eALP becomes the authoritative source and")
    print("     this derivation is retired rather than carried forward.")
    print("  2. Hourly routine observations only. Special reports (SPECI) between")
    print("     the hour are excluded, so short-lived deteriorations are undercounted.")
    print("  3. ASOS is a point sensor. It reports conditions at its own location,")
    print("     not across a 2,900-acre site.")
    print("  4. Whether SLN's runway system is adequate turns on the airport's")
    print("     critical aircraft, which is established in the Authority's own master")
    print("     planning record and was not an input here. Nothing in this analysis")
    print("     is a finding about the adequacy of the airfield.")


if __name__ == "__main__":
    main()
