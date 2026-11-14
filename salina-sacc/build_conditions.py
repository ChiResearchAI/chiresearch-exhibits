"""
Build the "Field conditions" view for the Salina SACC demonstration.

What this does
--------------
Fetches the current routine weather observation (METAR) and the terminal
aerodrome forecast (TAF) for Salina Regional Airport from the NOAA/NWS
Aviation Weather Center, then works out, for each of the four runways, how
much of the wind is acting along the runway (headwind) and how much is
acting across it (crosswind).

Why this is worth showing
-------------------------
FAA runway designators are MAGNETIC. METAR wind directions are TRUE. The
published magnetic variation at Salina is 7 degrees East. A platform that
compares the two without converting will report a crosswind that is wrong
by the variation. This script computes the answer both ways and shows both,
which is the same governance point the ten-year analysis makes, applied to
the conditions standing over the field right now.

The conversion and the crosswind formula are taken unchanged from
reproduce.py so that the two analyses cannot drift apart.

Output
------
conditions.json, read by index.html.
"""

import json
import math
import urllib.request
from datetime import datetime, timezone

STATION_ICAO = "KSLN"

METAR_URL = "https://aviationweather.gov/api/data/metar?ids=KSLN&format=json"
TAF_URL = "https://aviationweather.gov/api/data/taf?ids=KSLN&format=json"

# FAA runway designators are MAGNETIC. METAR wind directions are TRUE.
# The published magnetic variation at SLN is 7 degrees East, so:
#     true heading = magnetic heading + east variation
MAGNETIC_VARIATION_EAST = 7

RUNWAYS = [
    {"name": "17/35", "magnetic_heading": 170, "length_ft": 12301, "width_ft": 150},
    {"name": "12/30", "magnetic_heading": 120, "length_ft": 6510, "width_ft": 100},
    {"name": "18/36", "magnetic_heading": 180, "length_ft": 4301, "width_ft": 75},
    {"name": "04/22", "magnetic_heading": 40, "length_ft": 3648, "width_ft": 75},
]

# The allowable crosswind components in AC 150/5300-13B Change 1, by Runway
# Design Code. Used here only to say which band the current crosswind sits in.
CROSSWIND_BANDS_KT = [10.5, 13.0, 16.0, 20.0]


def fetch_json(url):
    """Fetch a URL and parse it as JSON. Returns None if anything goes wrong."""
    request = urllib.request.Request(url, headers={"User-Agent": "ChiResearch-SACC-demo"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        print("  could not fetch %s: %s" % (url, error))
        return None


def crosswind_component_kt(wind_direction_true, wind_speed_kt, runway_true_heading):
    """
    The part of the wind acting across the runway centerline.

    Absolute value is taken because the component is reported as a magnitude:
    a crosswind from the left at one end is the same magnitude as a crosswind
    from the right at the other.
    """
    angle_between_degrees = wind_direction_true - runway_true_heading
    angle_between_radians = math.radians(angle_between_degrees)
    return abs(wind_speed_kt * math.sin(angle_between_radians))


def headwind_component_kt(wind_direction_true, wind_speed_kt, runway_true_heading):
    """
    The part of the wind acting along the runway centerline.

    Positive means a headwind on the lower-numbered runway end; negative means
    a tailwind on that end, which is the same as a headwind on the reciprocal.
    """
    angle_between_degrees = wind_direction_true - runway_true_heading
    angle_between_radians = math.radians(angle_between_degrees)
    return wind_speed_kt * math.cos(angle_between_radians)


def band_for_crosswind(crosswind_kt):
    """Report the smallest AC 150/5300-13B band that contains this crosswind."""
    for band in CROSSWIND_BANDS_KT:
        if crosswind_kt <= band:
            return band
    return None


def describe_runway_end(runway_name, headwind_kt):
    """
    Name the end an aircraft would be landing on.

    "17/35" is two ends. A positive headwind component means the wind favours
    the first end as written; a negative one favours the reciprocal.
    """
    first_end, second_end = runway_name.split("/")
    if headwind_kt >= 0:
        return first_end
    return second_end


def main():
    print("Fetching current conditions for %s ..." % STATION_ICAO)

    metar_records = fetch_json(METAR_URL)
    taf_records = fetch_json(TAF_URL)

    if not metar_records:
        raise SystemExit("No METAR returned; not writing conditions.json.")

    observation = metar_records[0]

    wind_direction_true = observation.get("wdir")
    wind_speed_kt = observation.get("wspd")

    # A calm or variable wind reports direction as 0 or the string "VRB".
    # Neither can be resolved into components, so say so rather than guess.
    wind_is_resolvable = (
        isinstance(wind_direction_true, (int, float))
        and isinstance(wind_speed_kt, (int, float))
        and wind_speed_kt > 0
    )

    runway_results = []
    if wind_is_resolvable:
        for runway in RUNWAYS:
            magnetic_heading = runway["magnetic_heading"]
            true_heading = magnetic_heading + MAGNETIC_VARIATION_EAST

            # The correct computation: convert the runway to true, because the
            # wind is already true.
            crosswind_corrected = crosswind_component_kt(
                wind_direction_true, wind_speed_kt, true_heading
            )
            headwind_corrected = headwind_component_kt(
                wind_direction_true, wind_speed_kt, true_heading
            )

            # The common mistake: compare the true wind straight against the
            # magnetic designator, skipping the conversion entirely.
            crosswind_uncorrected = crosswind_component_kt(
                wind_direction_true, wind_speed_kt, magnetic_heading
            )

            runway_results.append({
                "name": runway["name"],
                "magnetic_heading": magnetic_heading,
                "true_heading": true_heading,
                "length_ft": runway["length_ft"],
                "width_ft": runway["width_ft"],
                "crosswind_kt": round(crosswind_corrected, 1),
                "headwind_kt": round(headwind_corrected, 1),
                "crosswind_uncorrected_kt": round(crosswind_uncorrected, 1),
                "error_kt": round(abs(crosswind_corrected - crosswind_uncorrected), 1),
                "band_kt": band_for_crosswind(crosswind_corrected),
                "favoured_end": describe_runway_end(runway["name"], headwind_corrected),
            })

        # The runway a controller or pilot would most likely use is the one with
        # the least crosswind, among those long enough to be in general use.
        runway_results.sort(key=lambda r: r["crosswind_kt"])

    forecast_periods = []
    if taf_records:
        raw_taf = taf_records[0].get("rawTAF", "")
    else:
        raw_taf = ""

    conditions = {
        "station": STATION_ICAO,
        "station_name": observation.get("name", "Salina Rgnl, KS, US"),
        "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observation_time_utc": observation.get("reportTime"),
        "raw_metar": observation.get("rawOb", ""),
        "raw_taf": raw_taf,
        "flight_category": observation.get("fltCat"),
        "temperature_c": observation.get("temp"),
        "dewpoint_c": observation.get("dewp"),
        "visibility_sm": observation.get("visib"),
        "altimeter_hpa": observation.get("altim"),
        "cloud_cover": observation.get("cover"),
        "wind_direction_true": wind_direction_true,
        "wind_speed_kt": wind_speed_kt,
        "wind_is_resolvable": wind_is_resolvable,
        "magnetic_variation_east": MAGNETIC_VARIATION_EAST,
        "runways": runway_results,
        "forecast_periods": forecast_periods,
        "source": "NOAA/NWS Aviation Weather Center, aviationweather.gov",
    }

    with open("conditions.json", "w") as output_file:
        json.dump(conditions, output_file, indent=2)

    print("  observation : %s" % conditions["raw_metar"])
    print("  category    : %s" % conditions["flight_category"])
    if wind_is_resolvable:
        print("  wind        : %s true at %s kt" % (wind_direction_true, wind_speed_kt))
        for runway in runway_results:
            print("    rwy %-6s xwind %4.1f kt (uncorrected %4.1f, error %.1f) favours %s"
                  % (runway["name"], runway["crosswind_kt"],
                     runway["crosswind_uncorrected_kt"], runway["error_kt"],
                     runway["favoured_end"]))
    else:
        print("  wind        : calm or variable - components not resolvable")
    print("Wrote conditions.json")


if __name__ == "__main__":
    main()
