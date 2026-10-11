# Visarjan Ghat Watch (Track 2)

> **Claude Impact Lab x Cerebras Cafe Compute, Bhopal &bull; 11 October 2026**  
> *Target Deadline: Durga Visarjan on 20 October 2026*

---

## 1. Project Overview & The One User

- **Track:** Track 2: Visarjan Ghat Watch
- **Team Name:** Team White Eye
- **Team Member(s):** Shaket Raj ([@shaketraj156-ops](https://github.com/shaketraj156-ops))
- **The One User:** The **Bhopal Municipal Corporation (BMC) Officer** responsible for planning Durga Visarjan.
  - **The Operational Decision:** The officer must decide where to dispatch cleaning crews, emergency aeration equipment, and proactive water testing squads prior to Durga Visarjan on 20 October 2026.
  - **The Problem Solved:** Historically, Madhya Pradesh Pollution Control Board (MPPCB) water test results are buried across 90-to-120 page annual PDF reports that are rarely compared against legal standards or across multiple years. Visarjan Ghat Watch lines up three years (2023–2025) of MPPCB data against CPCB Class B bathing limits, ranks Bhopal's 7 immersion ghats by risk, highlights missing data as data gaps, links every number directly to its original report page, and generates actionable Hindi/English forwarding briefs.

---

## 2. Quickstart: Run in 5 Steps

```bash
# 1. Clone the repository
git clone https://github.com/shaketraj156-ops/claude-code.git
cd claude-code

# 2. Create and activate a virtual environment
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
# source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Confirm data is in place (bundled in data/)
# data/bhopal_ghats_2023_2025.csv is already bundled

# 5. Launch the Streamlit dashboard
streamlit run app.py
```

The application opens with useful defaults immediately (Durga festival, all three years 2023–2025, CPCB Class B limits, Hindi brief). The officer uploads nothing and types nothing.

---

## 3. How the Ranking Works (Plain Words & Weights)

### Why CPCB Class B Was Chosen
CPCB Class B defines criteria for **outdoor bathing**. During Ganesh and Durga visarjan ceremonies, devotees, municipal workers, and citizens enter the water to immerse idols and conduct rituals. Class B is the statutory standard designed to protect human body contact.

### Scored Parameters
Only three parameters have statutory Class B limits and are scored:
1. **Dissolved Oxygen (DO):** Minimum **5.0 mg/l** (*lower is worse; 0 mg/l represents 100% severity*).
2. **Biochemical Oxygen Demand (BOD):** Maximum **3.0 mg/l** (*higher is worse*).
3. **pH:** Acceptable range **6.5 to 8.5** (*values below 6.5 or above 8.5 fail*).

All other reported parameters (COD, total/dissolved/suspended solids, turbidity, conductivity, and the 4 heavy metals: chromium, lead, zinc, copper) have **no Class B limit** and are reported as *"reported with no limit set"*, without inventing artificial limits.

### Scoring Formula & Weighting
- **Per-Reading Severity (0 to 1):** Measures how far a failing reading breaches the threshold.
  - If a reading passes: `risk = 0.0`
  - If a reading fails: `risk = 0.5 + 0.5 * severity`
- **Phase Weights:**
  - `pre`: 1.0 (baseline)
  - `during`: 2.0 (highest impact during active visarjan)
  - `after`: 1.5 (post-immersion residual pollution)
- **Year Weights:**
  - `2023`: 1.0
  - `2024`: 1.5
  - `2025`: 2.0 (most recent data carries highest weight)
- **Ghat Risk Score (0 to 100):** Weighted average of risk across all scored measurements:
  $$\text{Risk Score} = 100 \times \frac{\sum (w_{\text{phase}} \times w_{\text{year}} \times \text{risk})}{\sum (w_{\text{phase}} \times w_{\text{year}})}$$
- **Treatment of Missing Data:**
  - `missing`, `not sampled`, `*`, `**`, and blank values are **never** treated as zero or clean water.
  - Missing readings are excluded from the denominator of risk, but explicitly surfaced through **`n_missing`**, **`completeness`**, and **`data-gap badges`**.
  - A missing table (e.g., Durga 2025 for Bairagarh and Malikhedi) is a **data gap**, never a clean ghat.

---

## 4. Honesty: What Works and What Does Not

| Feature / Aspect | Status | Details & Honesty Note |
|---|---|---|
| **Traceability to PDF pages** | **Works** | Every evidence item and table row links directly to the PDF page number in the MPPCB report. |
| **Offline Hindi & English Briefs** | **Works** | Complete templated briefs in Hindi and English generate instantaneously without requiring an internet connection or API keys. |
| **Optional Claude Rewording** | **Works** | Optional rewording is enabled only if `ANTHROPIC_API_KEY` is present. It strictly polishes wording and cannot invent numbers. |
| **Map Visualization** | **Conditional** | Per spec, coordinates are never fabricated. A map renders only if `data/ghat_coordinates.csv` is provided with `site, lat, lon`. Otherwise, it gracefully displays an informative notice. |
| **Hindi Text Accuracy** | **Caveat** | The Hindi template covers all critical data points clearly, but should undergo native editorial review prior to formal press release. |
| **Rani Kamlapati / Kamla Park** | **Caveat** | Ganesh tables say *Kamla Park kund*, while Durga tables say *Lower Lake ghat*. They have medium match confidence and may be two distinct locations. A prominent caveat is displayed. |
| **Assumed Units** | **Caveat** | MPPCB reports print no units. Units (`mg/l`, `pH Units`) are standard assumptions based on CPCB reporting conventions. |
| **Heavy Metals** | **Caveat** | Only four metals were tested (Cr, Pb, Zn, Cu). Never assume water is clean of other industrial toxins. |
| **Statewide Dataset** | **Out of Scope** | `data/mp_immersion_sites_2023_2025.csv` (21,600 rows) is statewide background context and is not used for Bhopal municipal planning. |

---

## 5. Extra Data Used & References

- **MPPCB Annual Idol Immersion Reports:**
  - 2023: *Report on Water Quality of Idol Immersion Sites in MP (CPCB/MPPCB)* (Pages 26–28, 59–61)
  - 2024: *Ganesh and Durga Visarjan Water Quality Report 2024* (Pages 23–26, 69–72)
  - 2025: *Ganesh and Durga Visarjan Water Quality Report 2025* (Pages 28–30, 64–65)
- **Bhopal Upper Lake Water Quality Report (2023–24):** Used for background reference regarding NGT bans and municipal lake restoration.
- **CPCB Water Quality Criteria:** Outdoor bathing Class B statutory notification ([CPCB Official Criteria](https://cpcb.nic.in/water-quality-criteria/)).

---

## 6. Verification & Test Results

### 1. Automated Test Suite (pytest)
- **Result:** `9 passed in 2.76s` (100% pass rate).
- Tested items:
  - `test_blank_is_missing_not_clean`: Blank/not sampled is missing, never clean.
  - `test_bdl_and_nd_are_very_low`: BDL and ND treated as very low, not zero.
  - `test_oxygen_limit`: DO threshold (< 5.0 mg/l fails, >= 5.0 passes).
  - `test_bod_limit`: BOD threshold (> 3.0 mg/l fails, <= 3.0 passes).
  - `test_ph_range`: pH 6.5–8.5 range.
  - `test_no_limit_parameter`: Unscored parameters return `no_limit`.
  - `test_severity_zero_oxygen_is_max`: DO of 0 mg/l yields maximum severity 1.0.
  - `test_ranking_and_gaps`: Correct ranking order and table gap detection.
  - `test_brief_has_page_and_gap_text`: Report pages and gap notices present in Hindi and English briefs.

### 2. Manual Spot-Check Verification (`spot_check.csv`)
15 random scored readings across all 7 ghats, 3 years, both festivals, and all phases have been compiled into `spot_check.csv` for independent cross-verification against the original PDF page numbers.

---

## 7. License

This project is licensed under the [MIT License](LICENSE).
