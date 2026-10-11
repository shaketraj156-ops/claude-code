# Visarjan Ghat Watch

**Track 2 · Claude Impact Lab × Cerebras Café Compute, Bhopal · 11 October 2026**

> **Team name:** _TODO — add your team name_
> **Members:** _TODO — add each member and what they worked on_

Three years of MPPCB water tests at Bhopal's idol-immersion ghats sit inside 90–120 page PDFs that nobody lines up against the legal limits. This turns them into a ranked, sourced list a Bhopal Municipal Corporation officer can act on before **Durga visarjan on 20 October 2026**.

Every number on screen traces back to the report and page it came from. Missing readings are shown as missing, never as clean.

## The one user, the one workflow

**The BMC officer who plans Durga visarjan at the ghats** — the person deciding where to send extra cleaning, aeration and water testing.

They pick a year/festival scope → read the two priority lists → open a ghat to see the readings behind its rank → export a bilingual brief or a priority CSV to forward.

## Run it

Python 3.10+ is required. No third-party packages, no API keys, no database, no internet connection, no government system is contacted.

```cmd
cd Track2-ClaudeImpactLabs\visarjan-demo
python server.py
```

Then open **http://127.0.0.1:8765**. Press Ctrl+C to stop.

On Windows you can instead double-click **`Start Visarjan Ghat Watch.cmd`** in this folder.

> Keep `visarjan-demo/` beside `impactdata/` and `dataa/` — the server resolves its data and source PDFs from its parent folder.

## What it does

- **Two independent rankings.** "Recorded pollution" ranks what the readings show. "Fresh testing" ranks where the evidence is thinnest. A ghat with no readings cannot get a pollution rank but stays on the testing list.
- **Every rank is explained.** The ghat panel opens on the exact event holding the reading that drove the rank, with a link straight to that page of the source PDF.
- **Before / during / after** readings per event, compared against CPCB Class B references.
- **Recovery check** — whether a breach during immersion was back within reference a week after.
- **Across years** — same parameter, festival and phase charted over 2023–2025. Missing readings break the line; nothing is interpolated.
- **Bilingual briefs** in Hindi and English, per ghat or for the whole scope, downloadable or printable to PDF.
- **CSV exports** — both priority lists (with the rank-explaining reading in `rank_reason_*`) or a single event's measurements.
- **Upload your own measurements** with the built-in template; validation rejects bad units, duplicates and impossible values rather than silently accepting them.

## What works and what doesn't

**Works:** all 1,524 Bhopal readings across 7 ghats, 3 years and 2 festivals; both rankings; recovery; history charts; bilingual briefs; all exports; PDF page links for every bundled reading; upload validation. 40 automated tests pass, including Chrome UI tests.

**Deliberate limits — please read these before acting on anything here:**

- **The data ends in 2025.** This is historical evidence, not a live safety assessment, and not a forecast. Collect current samples before operational decisions.
- **Total coliform is absent** from the reports, so full Class B compliance cannot be established. Class B is used as a comparison benchmark, not as immersion permission.
- **Units are assumed.** The reports print no units; the standard unit for each test is applied.
- **BDL/ND are censored values**, never treated as zero or as passing.
- **Only pH, dissolved oxygen and BOD have Class B thresholds** in the supplied criteria. The four metals and the other parameters are shown but not scored.
- **"Rani Kamlapati ghat / Kamla Park kund" may be two different places.** The app flags this and carries the warning into the briefs.
- **No health effects are inferred.** The app reports readings against limits and nothing more.
- **Not built:** map/GIS coordinates, authentication, saved uploads, forecasting, validated intervention recommendations. Uploads live in memory only. The statewide MP CSV uses a different schema and is out of scope. Hindi text is template-based, not machine-translated.

## Method

Ranking method **v1.1**. Sites are grouped by low dissolved oxygen first, then other breaches, then clean, then unassessable. Full rules — including why oxygen is grouped ahead of BOD, and the exact deviation formulas — are in **[`visarjan-demo/README.md`](visarjan-demo/README.md)** and in the "How priorities are calculated" panel inside the app.

This is a deterministic, auditable project heuristic. It is **not** an official CPCB risk score, not a trained model, and not a validated prediction.

## Data

All supplied public data, unmodified:

| Path | Contents |
|---|---|
| `impactdata/bhopal_ghats_2023_2025.csv` | 1,524 readings · 7 Bhopal ghats · 2023–2025 |
| `impactdata/sample_bhopal_2025.csv` | 453-row 2025 subset for quick testing |
| `impactdata/mp_immersion_sites_2023_2025.csv` | Statewide MP data (not used by this app) |
| `impactdata/cpcb_water_quality_criteria.csv` | Official CPCB limits, classes A–E |
| `dataa/*.pdf` | Original MPPCB reports and Upper/Lower Lake water-quality reports |

Sources: [MPPCB](https://www.mppcb.mp.gov.in/) visarjan reports 2023/2024/2025 and lake water-quality reports; [CPCB water quality criteria](https://cpcb.gov.in/water-quality-criteria/). No data beyond the supplied pack was added. Source data and reports retain their original ownership.

## Tests

```cmd
cd visarjan-demo
python -m unittest test_server test_analysis
```

For the Chrome UI tests: `python -m pip install -r requirements-dev.txt` then `python -m unittest test_browser`.

## Licence

MIT — see [`LICENSE`](LICENSE). The code is offered to the Government of Madhya Pradesh through MPSeDC.
