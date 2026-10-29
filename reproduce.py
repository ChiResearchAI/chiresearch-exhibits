#!/usr/bin/env python3
"""
Access Without Use — reproduction script
ChiResearch Technologies, LLC · Wilfred C. Ikejiofor · 2026-10-29

Rebuilds every figure in the exhibit from the World Bank Global Findex API.
No API key required. Run:  python3 reproduce.py

Source: World Bank Global Findex, API source 28 (the round published as the
Global Findex Database 2025, July 2025; survey year appears as 2024).
Viet Nam's intermediate round is 2022 where the other three countries use 2021.

Conversion = (use indicator / account indicator) * 100, within the same
demographic cut. See the exhibit's "What this measure will not bear" section
for what that ratio does and does not support.
"""
import json, urllib.request, csv, time, collections

COUNTRIES = "IND;KEN;IDN;VNM"
MEASURES = {
    "account.t.d":      "Account",
    "fin2.t.d":         "Debit card",
    "fin17a.17a1.d":    "Saved at FI or mobile money",
    "merchant.pay":     "Digital merchant payment",
    "mobileaccount.t.d":"Mobile money account",
}
CUTS = {"": "total", ".1": "female", ".2": "male", ".7": "poorest40", ".8": "richest60"}
USE = ["Saved at FI or mobile money", "Debit card", "Digital merchant payment"]


def fetch(indicator, retries=3):
    url = (f"https://api.worldbank.org/v2/country/{COUNTRIES}/indicator/"
           f"{indicator}?format=json&source=28&per_page=400")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception as exc:
            if attempt == retries - 1:
                print(f"  FAILED {indicator}: {exc}")
                return None
            time.sleep(2)


def harvest():
    rows = []
    for root, label in MEASURES.items():
        for suffix, cut in CUTS.items():
            payload = fetch(root + suffix)
            if not payload or len(payload) < 2 or not payload[1]:
                continue
            for rec in payload[1]:
                if rec["value"] is None:
                    continue
                # NOTE: source 28 leaves countryiso3code blank; the country is
                # carried in rec["country"]. Reading iso3 here returns nothing.
                rows.append([label, root, cut, rec["country"]["id"],
                             rec["country"]["value"], rec["date"],
                             round(rec["value"], 4)])
    return rows


def analyse(rows):
    D = collections.defaultdict(dict)
    for r in rows:
        D[(r[4], r[0], r[2])][int(r[5])] = float(r[6])

    def val(c, m, cut, y):
        return D[(c, m, cut)].get(y)

    def conv(c, m, cut, y):
        u, a = val(c, m, cut, y), val(c, "Account", cut, y)
        return None if (u is None or not a) else 100.0 * u / a

    out = {}
    for c in ["India", "Kenya", "Indonesia", "Viet Nam"]:
        prior = 2022 if c == "Viet Nam" else 2021
        rec = {"prior_round": prior, "ownership": {}, "conversion": {}}
        for y in (2011, prior, 2024):
            f, m = val(c, "Account", "female", y), val(c, "Account", "male", y)
            p, q = val(c, "Account", "poorest40", y), val(c, "Account", "richest60", y)
            rec["ownership"][y] = {
                "female": f, "male": m,
                "gap_pp": None if None in (f, m) else round(m - f, 2),
                "poorest40": p, "richest60": q,
                "income_gap_pp": None if None in (p, q) else round(q - p, 2)}
        for m in USE:
            rec["conversion"][m] = {}
            for y in (2011, prior, 2024):
                cf, cm = conv(c, m, "female", y), conv(c, m, "male", y)
                cp, cq = conv(c, m, "poorest40", y), conv(c, m, "richest60", y)
                rec["conversion"][m][y] = {
                    "female": None if cf is None else round(cf, 2),
                    "male":   None if cm is None else round(cm, 2),
                    "gap_pp": None if None in (cf, cm) else round(cm - cf, 2),
                    "poorest40": None if cp is None else round(cp, 2),
                    "richest60": None if cq is None else round(cq, 2),
                    "income_gap_pp": None if None in (cp, cq) else round(cq - cp, 2)}
        out[c] = rec
    return out


def main():
    print("Fetching Global Findex (source 28) for IND, KEN, IDN, VNM ...")
    rows = harvest()
    with open("findex_raw.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["measure", "root", "cut", "cid", "country", "year", "value"])
        w.writerows(rows)
    print(f"  wrote findex_raw.csv  ({len(rows)} observations)")

    results = analyse(rows)
    with open("findex_results.json", "w") as fh:
        json.dump({"countries": results}, fh, indent=1)
    print("  wrote findex_results.json")

    print("\nHeadline figures used in the exhibit")
    print("-" * 72)
    saved = "Saved at FI or mobile money"
    print(f"{'country':12s} {'own gap 11':>11} {'own gap 24':>11} "
          f"{'conv gap 11':>12} {'conv gap 24':>12} {'income gap 24':>14}")
    for c, r in results.items():
        o11 = r["ownership"][2011]["gap_pp"]
        o24 = r["ownership"][2024]["gap_pp"]
        s11 = r["conversion"][saved][2011]["gap_pp"]
        s24 = r["conversion"][saved][2024]["gap_pp"]
        i24 = r["conversion"][saved][2024]["income_gap_pp"]
        f = lambda v: "   n/a" if v is None else f"{v:6.2f}"
        print(f"{c:12s} {f(o11):>11} {f(o24):>11} {f(s11):>12} {f(s24):>12} {f(i24):>14}")


if __name__ == "__main__":
    main()
