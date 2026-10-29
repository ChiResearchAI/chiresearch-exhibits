# After the Account — Global Findex 2025 exhibit

Worked analytical example prepared for the Women's World Banking RFQ
(Request for Qualifications: Consultants for Women's World Banking Projects).

**Author:** Wilfred C. Ikejiofor, ChiResearch Technologies, LLC
**Date:** 29 October 2026

## What it shows

Women's account ownership rose steeply across all four markets, and the gains in
the level of saving are large everywhere. The share of adult women saving at a
financial institution or through mobile money rose in India from 7.1% to 22.8%,
Kenya 19.2% to 49.1%, Indonesia 15.9% to 25.3%, and Viet Nam 13.7% (2014) to 46.5%.

India's expansion is the largest in the set on both measures: female account
ownership 26.5% to 89.3% (3.4x), the 17.3pp ownership gender gap closed entirely,
female saving more than tripled, and the absolute gender gap in saving narrowed
from 8.9pp to 8.3pp.

What held steady is the *rate* at which an account becomes savings: Indian women
converted at 26.8% in 2011 and 25.6% in 2024, men at 36.6% and 35.0%. A far larger
base produced proportionally the same result, so the conversion gap (9.8pp to
9.5pp) did not close alongside the ownership gap. Rate and level answer different
questions and both are reported for that reason.

Computing the identical conversion measure on the income split — poorest 40%
against richest 60%, same data, same years, same arithmetic — shows that in
India, Kenya and Indonesia the income conversion gap is now two to three times
the gender conversion gap. Viet Nam inverts the pattern: women there convert
accounts into savings and into digital merchant payments at higher rates
than men.

## Files

| File | What it is |
|---|---|
| `index.html` | The exhibit. Self-contained; no build step. |
| `reproduce.py` | Re-fetches the data and recomputes every figure. No API key needed. |
| `data/findex_raw.csv` | Tidy observations: measure, cut, country, year, value. |

## Reproducing

```
python3 reproduce.py
```

Stdlib only. Re-fetches from the World Bank indicator API each run, so a later
Findex round will change the output rather than silently reuse a cached file.

## Data note

Source 28 (Global Findex) leaves `countryiso3code` blank on every record; the
country is carried in `rec["country"]`. A harvest that reads the iso3 field
returns rows with no country attached.

## Limits

Stated in full in the exhibit. In short: a conversion rate is not a count and
reading it without the level will mislead; conversion is a ratio of two
population-denominated rates and is not a conditional probability; the measures
are not strictly nested; the debit-card series is distorted by mobile money
displacing cards in Kenya and is excluded from the charts; early-round ratios on
small ownership bases are unstable; and Findex is self-reported survey data with
country-level sampling error of a few percentage points.
