# Visarjan Ghat Watch

Track 2 · Bhopal Municipal Corporation officer workspace

Turn the supplied 2023–2025 water tests into an explained list of ghats needing attention and a separate list needing fresh testing. Readings, recovery comparisons and bilingual briefs remain traceable to their evidence. This is a deterministic analysis application, not a trained AI predictor.

## Run

Python 3.10+ is required. The application has no third-party runtime dependencies, API keys, database, or external services.

1. Keep this folder beside the supplied `impactdata/` and `dataa/` folders.
2. On Windows, double-click `start-demo.cmd` (or `Start Visarjan Ghat Watch.cmd` in the parent folder). Alternatively run `python server.py` in this folder.
3. Open http://127.0.0.1:8765.

The launcher starts a hidden local server if needed. A foreground server stops with Ctrl+C. Directly opening `index.html` redirects to the server if available, or shows launch instructions. Uploads exist only in memory; reload the bundled data to discard them.

## One user, one workflow

The BMC officer chooses a report-year/festival scope, reviews pollution and testing priorities, inspects the evidence for a ghat, and exports a brief or priority CSV for follow-up.

- All **1,524 Bhopal readings** load by default, across seven sites, three years and two festivals.
- Choose the **453-row 2025 sample** from the Dataset selector for a smaller test.
- Recorded pollution and fresh testing have independent, explicit rankings.
- A known site remains visible when its entire selected event is absent. For Durga 2025 this includes Bairagarh and Malikhedi.
- Inspect before/during/after values, recovery findings, same-festival charts across years, and all 13 measured parameters with their source references.
- Export a consolidated or individual-site brief in Hindi and English, print both languages to PDF, export both priority lists to CSV, or download an event's measurements.
- Upload measurements for another site with the provided CSV template. Invalid uploads preserve the previous dataset. Uploads replace, rather than merge into, the current dataset.

## Ranking method v1.1

The server reads Class B reference values from `cpcb_water_quality_criteria.csv`. Currently these are pH 6.5–8.5, dissolved oxygen at least 5 mg/l, and BOD at most 3 mg/l. These comparisons assume the supplied units and compatible test methods; they do not establish complete Class B compliance.

**Pollution priority:** for each numeric, unflagged core reading, calculate deviation outside its reference: oxygen `(minimum-value)/minimum`, BOD `(value-maximum)/maximum`, and pH distance outside its reference range divided by the range width; clamp negative deviations to zero.

Sites are then grouped, in this order:

1. any dissolved oxygen below reference — ordered by lowest recorded oxygen, then by the share of that site's oxygen readings below reference;
2. breaches only in pH or BOD;
3. assessed with no breach;
4. no assessable core reading — these stay unranked.

Remaining ties use worst deviation descending, then breach proportion descending, then site name. Equal evidence shares a rank.

Dissolved oxygen is grouped ahead of the other parameters because its deviation is bounded at 1.0 while BOD's is unbounded; ranking on deviation alone put a single high BOD reading above water holding no oxygen at all. The method is a transparent project heuristic, not an official CPCB risk score or a validated forecast. All years have equal status; an old severe reading can determine the ranking, and its year is shown.

The priority CSV export records the reading that produced each rank in its `rank_reason_*` columns — the same reading shown on screen and in the brief — alongside the site's single largest deviation in `worst_deviation_*`. For a low-oxygen site these are usually different readings.

**Testing priority:** rank by lowest coverage, then oldest latest numeric evidence year, then uncertain site identity. Coverage has nine expected core checks per site/event. The latest evidence year uses only the selected festival(s) and no year later than the selected year. Report years are not exact sampling dates. Sites absent from the loaded dataset and events absent from the entire dataset cannot be inferred.

**Recovery:** “Returned within reference” requires an outside-reference during value and a within-reference after value. “Still outside reference” requires breaches at both stages. A before/after difference requires both numeric readings. None of these labels establishes causation, return to baseline, or current safety.

**History:** compare the same site, parameter, festival and phase across all loaded years. Missing readings break the chart lines. History deliberately shows all available years independently of the main year filter.

## Input contract and evidence

Required CSV columns: `year,festival,site,phase,parameter,value,flag,source_page`.

Recommended optional columns: `water_body,unit_assumed,site_match_confidence,source_document`.

- `site_match_confidence`: any stated value other than `high` marks the site's identity as uncertain, so `low` is never read as certain. Leaving it blank asserts nothing either way.

- `phase`: `pre`, `during`, or `after`.
- Core parameter names: `pH`, `Dissolved oxygen`, `BOD` (case variations normalised).
- Oxygen and BOD must be in mg/l; pH is dimensionless. Blank units use the documented assumptions. No automatic unit conversion is performed.
- `value` is numeric or blank. `flag` is blank, `BDL`, `ND`, `not sampled`, `*`, or `**`. Do not provide both a numeric value and a flag.
- BDL/ND remain censored values, not zero, passing, or an invented concentration.
- Duplicate columns/measurement keys, inconsistent row lengths, invalid numeric values, unsupported core units, negative values, and pH outside 0–14 are rejected. Upload limit: 2 MB.
- A PDF link is provided only when the site, year, festival, phase, parameter, value, flag, unit and source page match a bundled Bhopal measurement. It is a dataset match, not independent laboratory verification. The supplied Bhopal data itself was only spot-checked.
- For other measurements, supply a plain-text `source_document` description and keep the original laboratory/report evidence. The app does not invent official PDF citations for those rows.
- The full file and the 2025 sample overlap. Do not concatenate them. The statewide MP CSV has a different schema and is outside this implementation's Bhopal scope.

## Data and limitations

The app uses the supplied Bhopal CSV, its 2025 subset, the CPCB criteria CSV and the three original immersion PDFs. It reads the full Bhopal CSV to match source records even while displaying an upload. No extra public dataset or government connection is used.

Measurements end in 2025 by default and do not establish current conditions. Units are assumed in the reports' extracted data. Total coliform is absent, and the metal measurements do not have Class B thresholds in the supplied criteria. The combined Rani Kamlapati / Kamla Park name may represent two locations. This warning is carried into the briefs and into both CSV exports, as `identity_needs_check`. No health effects, immersion permission, or future water quality are inferred. Hindi/English summaries use templates rather than an AI service.

The app is intended for a local demonstration and officer review, not public multi-user hosting. It has no authentication, durable upload storage, GIS coordinates, forecasting, or validated intervention recommendations. Source data and reports retain their original ownership; the MIT licence covers this application's code.

## Development and checks

`server.py` validates input and serves the local app. `analysis.py` computes event coverage, both rankings, recovery and consolidated briefs. `app.js` handles the interface and charts; it does not independently recompute rankings. `styles.css` controls desktop, mobile and print layouts.

Run `python -m unittest test_server test_analysis -v` for backend checks. For Chrome tests, install development dependencies with `python -m pip install -r requirements-dev.txt`, then run `python -m unittest test_browser -v`. Browser tests use an existing Google Chrome installation and an isolated temporary server. They do not change the live demo.

Before a hackathon submission, add your actual team name and members, publish the repository with its supplied data dependencies, and record the demonstration. No public repository has been created by this local build.
