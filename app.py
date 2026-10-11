"""Visarjan Ghat Watch - Streamlit Application
Bhopal Municipal Corporation (BMC) Durga Visarjan Planning Dashboard
Track 2: Visarjan Ghat Watch
"""
import os
from pathlib import Path
import pandas as pd
import streamlit as st

from backend import load_readings, make_brief, rank_ghats
from backend.config import DATA_DIR, LIMITS, LIMIT_TEXT, UNITS

# Page configuration
st.set_page_config(
    page_title="Visarjan Ghat Watch | BMC",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 24px;
        border-radius: 12px;
        color: #ffffff;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        color: #ffffff;
    }
    .main-header p {
        margin: 6px 0 0 0;
        font-size: 1.05rem;
        color: #cfd8dc;
    }
    .disclaimer-box {
        background-color: #fff8e1;
        border-left: 5px solid #ffb300;
        padding: 12px 18px;
        border-radius: 6px;
        color: #5d4037;
        font-size: 0.95rem;
        margin-bottom: 24px;
    }
    .caveat-box {
        background-color: #fbe9e7;
        border-left: 5px solid #ff7043;
        padding: 12px 16px;
        border-radius: 6px;
        color: #4e342e;
        font-size: 0.92rem;
        margin: 12px 0;
    }
    .gap-badge {
        background-color: #ffebee;
        color: #c62828;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .complete-badge {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .metric-card {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .footer-box {
        border-top: 1px solid #e0e0e0;
        padding-top: 16px;
        margin-top: 36px;
        color: #546e7a;
        font-size: 0.88rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def get_readings_data():
    """Load readings with caching."""
    return load_readings()


def format_status_word(row_status):
    """Return status in plain descriptive words as required by the spec."""
    mapping = {
        "pass": "pass",
        "fail": "fail",
        "very_low": "very low (BDL)",
        "missing": "missing (not sampled)",
        "no_limit": "reported with no limit set",
    }
    return mapping.get(row_status, str(row_status))


# ==========================================
# 1. Page Header & Disclaimer (Section 6.1)
# ==========================================
st.markdown("""
<div class="main-header">
    <h1>Visarjan Ghat Watch</h1>
    <p>Bhopal Municipal Corporation (BMC) &bull; Durga &amp; Ganesh Visarjan Water Quality Risk Dashboard</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="disclaimer-box">
    <strong>Disclaimer:</strong> Readings compared with CPCB Class B limits (outdoor bathing standard); 
    not legal or health advice; the municipal officer decides.
</div>
""", unsafe_allow_html=True)


# ==========================================
# 2. Sidebar Controls (Section 2 & 6.1)
# ==========================================
st.sidebar.header("Visarjan Planning Controls")

# Festival selection
festival_opt = st.sidebar.selectbox(
    "Festival",
    options=["Durga", "Ganesh", "Both"],
    index=0,
    help="Default is Durga, focusing on the upcoming Durga Visarjan on 20 October 2026.",
)
if festival_opt == "Both":
    selected_festivals = ["Durga", "Ganesh"]
else:
    selected_festivals = [festival_opt]

# Year selection
all_years = [2023, 2024, 2025]
selected_years = st.sidebar.multiselect(
    "Years",
    options=all_years,
    default=all_years,
    help="Select one or more years of MPPCB report data.",
)
if not selected_years:
    st.sidebar.warning("Please select at least one year. Reverting to all years.")
    selected_years = all_years

# Standard (Fixed: CPCB Class B)
st.sidebar.markdown("---")
st.sidebar.markdown("**Water Quality Standard:**")
st.sidebar.info(
    "**CPCB Class B (outdoor bathing standard)**\n\n"
    "*Reason:* Citizens and devotees come into direct contact with the water during visarjan immersion."
)
with st.sidebar.expander("Scored Parameters & Limits"):
    st.markdown("""
    - **Dissolved oxygen:** &ge; 5.0 mg/l *(lower is worse)*
    - **BOD:** &le; 3.0 mg/l *(higher is worse)*
    - **pH:** 6.5 to 8.5 *(outside range fails)*
    
    *Note:* COD, solids, turbidity, conductivity, and 4 metals (Cr, Pb, Zn, Cu) have no Class B limit and are marked as 'reported with no limit set'.
    """)

# Brief Language
st.sidebar.markdown("---")
brief_lang = st.sidebar.radio(
    "Officer Brief Language",
    options=["Hindi", "English"],
    index=0,
    help="Language for generating the executive brief for forwarding.",
)
lang_code = "hi" if brief_lang == "Hindi" else "en"

# Claude Polish Checkbox (disabled if no API key)
has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
use_claude = st.sidebar.checkbox(
    "Polish wording with Claude",
    value=False,
    disabled=not has_api_key,
    help="Requires ANTHROPIC_API_KEY environment variable. Offline plain brief is used if unchecked or key missing.",
)
if not has_api_key:
    st.sidebar.caption("*(Claude rewording disabled: ANTHROPIC_API_KEY not detected. Plain offline brief is active.)*")


# Load Data
df = get_readings_data()
ranked_df = rank_ghats(df, years=selected_years, festivals=selected_festivals)


# ==========================================
# 3. Ranked Table (Section 6.2 & Section 2)
# ==========================================
st.subheader("1. Ghat Risk Ranking (Highest Risk First)")
st.caption(
    f"Ranked according to CPCB Class B non-compliance across {festival_opt} "
    f"visarjan tests ({', '.join(map(str, sorted(selected_years)))})."
)

# Highlight data gap notice
durga_gap_ghats = [
    r["site"] for _, r in ranked_df.iterrows()
    if any(yr == 2025 and fest == "Durga" for yr, fest in r["table_gaps"])
]
if durga_gap_ghats:
    st.markdown(
        f"""
        <div class="caveat-box">
            <strong>Data Gap Notice:</strong> {', '.join(durga_gap_ghats)} have no Durga 2025 table in the official MPPCB report. 
            Under the evaluation rules, absent data is never clean; these ghats carry a data-gap badge and lower completeness.
        </div>
        """,
        unsafe_allow_html=True,
    )

# Format rows for display
ranked_rows = []
for i, r in ranked_df.iterrows():
    # Build reason from evidence[0]
    if r["evidence"]:
        e = r["evidence"][0]
        u = f" {e['unit']}" if e.get("unit") else ""
        reason_text = (
            f"{e['parameter']} {e['value']:g}{u} (limit: {e['limit']}), "
            f"{e['year']} {e['festival']} {e['phase']}, report page {e['source_page']}"
        )
    else:
        if r["risk_score"] is None:
            reason_text = "No scorable data in selected filters"
        else:
            reason_text = "All scored readings meet CPCB Class B limits"

    # Data gap badge text
    if r["table_gaps"]:
        gap_items = [f"No {yr} {fest} table in report" for yr, fest in r["table_gaps"]]
        gap_badge_text = "; ".join(gap_items)
    else:
        gap_badge_text = "None"

    # Risk score display
    score_display = f"{r['risk_score']:.1f}" if r["risk_score"] is not None else "No data"

    ranked_rows.append({
        "Rank": i + 1,
        "Ghat": r["site"],
        "Risk Score (0-100)": score_display,
        "Failing Readings": r["n_fail"],
        "Missing Readings": r["n_missing"],
        "Completeness": f"{int(round(r['completeness'] * 100))}%",
        "Data-Gap Badge": gap_badge_text,
        "Primary Reason": reason_text,
    })

display_ranked_df = pd.DataFrame(ranked_rows)
st.dataframe(
    display_ranked_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn(width="small"),
        "Risk Score (0-100)": st.column_config.TextColumn(width="small"),
        "Failing Readings": st.column_config.NumberColumn(width="small"),
        "Missing Readings": st.column_config.NumberColumn(width="small"),
        "Completeness": st.column_config.TextColumn(width="small"),
        "Data-Gap Badge": st.column_config.TextColumn(width="medium"),
        "Primary Reason": st.column_config.TextColumn(width="large"),
    },
)

# Rani Kamlapati / Kamla Park caveat callout
st.markdown("""
<div class="caveat-box">
    <strong>Caveat on Rani Kamlapati ghat / Kamla Park kund:</strong> 
    Medium match confidence. Ganesh festival tables report 'Kamla Park kund', while Durga festival tables report 'Lower Lake ghat'. 
    These may represent two distinct locations.
</div>
""", unsafe_allow_html=True)


# ==========================================
# 4. Ghat Detail View (Section 6.3)
# ==========================================
st.markdown("---")
st.subheader("2. Ghat Detailed Readings")
st.caption("Inspect every individual reading, parameter limit, and source report page for a specific ghat.")

# Selection dropdown (default is None per spec)
ghat_list = ["None"] + sorted(df["site"].unique().tolist())
selected_ghat = st.selectbox(
    "Select Ghat for Detail Inspection",
    options=ghat_list,
    index=0,
    help="Choose a ghat to inspect its underlying test data.",
)

if selected_ghat != "None":
    # Show Kamla Park caveat if selected
    if "Kamla" in selected_ghat or "Kamlapati" in selected_ghat:
        st.warning(
            "Caveat: Medium match confidence. Ganesh tables report 'Kamla Park kund', "
            "Durga tables report 'Lower Lake ghat'. These may be two separate sites."
        )

    # Filter readings for this ghat based on user filters
    ghat_readings = df[
        (df["site"] == selected_ghat)
        & (df["year"].isin(selected_years))
        & (df["festival"].isin(selected_festivals))
    ].copy()

    # Find stats from ranked_df
    ghat_rank_row = ranked_df[ranked_df["site"] == selected_ghat]
    if not ghat_rank_row.empty:
        gr = ghat_rank_row.iloc[0]
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Risk Score", f"{gr['risk_score']}/100" if gr["risk_score"] is not None else "No data")
        col2.metric("Failing Readings", gr["n_fail"])
        col3.metric("Missing Readings", gr["n_missing"])
        col4.metric("Completeness", f"{int(round(gr['completeness'] * 100))}%")
        col5.metric("Water Body", ghat_readings["water_body"].iloc[0] if not ghat_readings.empty else "N/A")

    if ghat_readings.empty:
        st.info(f"No test records found for {selected_ghat} with current filters ({festival_opt}, {selected_years}).")
    else:
        # Build detail table columns as required by section 6.3:
        # year, festival, phase, parameter, value as printed, unit, limit, status in words, source_page
        detail_rows = []
        for _, row in ghat_readings.iterrows():
            param_key = row["param_key"]
            unit_val = UNITS.get(param_key) or row.get("unit_assumed") or ""
            limit_val = LIMIT_TEXT.get(param_key, "no limit set")
            status_word = format_status_word(row["status"])
            val_printed = row["value_as_printed"]
            if pd.isna(val_printed):
                val_printed = str(row["value"]) if pd.notna(row["value"]) else "-"

            detail_rows.append({
                "Year": int(row["year"]),
                "Festival": row["festival"],
                "Phase": row["phase"],
                "Parameter": row["parameter"],
                "Value as Printed": val_printed,
                "Unit": unit_val,
                "Limit": limit_val,
                "Status": status_word,
                "Source Page": int(row["source_page"]) if pd.notna(row["source_page"]) else "-",
            })

        detail_df = pd.DataFrame(detail_rows)

        # Quick sub-filter for convenience
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            phase_filter = st.multiselect(
                "Filter Phase",
                options=["pre", "during", "after"],
                default=["pre", "during", "after"],
            )
        with filter_col2:
            status_filter = st.multiselect(
                "Filter Status",
                options=sorted(list(set(detail_df["Status"].unique()))),
                default=sorted(list(set(detail_df["Status"].unique()))),
            )

        filtered_detail_df = detail_df[
            (detail_df["Phase"].isin(phase_filter))
            & (detail_df["Status"].isin(status_filter))
        ]

        st.dataframe(
            filtered_detail_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Year": st.column_config.NumberColumn(width="small"),
                "Source Page": st.column_config.NumberColumn(
                    label="PDF Source Page",
                    help="Page number in that year's official MPPCB report for officer verification",
                    width="small",
                ),
            },
        )
        st.caption(f"Showing {len(filtered_detail_df)} of {len(detail_df)} readings for {selected_ghat}.")
else:
    st.info("Select a ghat from the dropdown above to view all its individual water quality readings.")


# ==========================================
# 5. Officer Brief Panel (Section 6.4)
# ==========================================
st.markdown("---")
st.subheader("3. Executive Brief for Forwarding")
st.caption(
    "Short plain-language briefing for the BMC officer to forward to ground teams. "
    "Generated completely from verified code numbers."
)

col_b1, col_b2 = st.columns([1, 4])
with col_b1:
    gen_clicked = st.button("Generate Brief", type="primary", use_container_width=True)

# Generate brief text
brief_text = make_brief(ranked_df, lang=lang_code, use_claude=use_claude)

st.text_area(
    f"Executive Brief ({brief_lang})",
    value=brief_text,
    height=240,
    help="Copy or download this text directly.",
)

file_lang_suffix = "hi" if lang_code == "hi" else "en"
st.download_button(
    label=f"Download Brief ({brief_lang} .txt)",
    data=brief_text,
    file_name=f"bmc_visarjan_brief_{file_lang_suffix}.txt",
    mime="text/plain",
)


# ==========================================
# 6. Map View (Section 6.5 - Optional, Last)
# ==========================================
st.markdown("---")
st.subheader("4. Ghat Locations Map (Optional)")

coords_file = DATA_DIR / "ghat_coordinates.csv"
if coords_file.exists():
    try:
        coords_df = pd.read_csv(coords_file)
        if {"site", "lat", "lon"}.issubset(coords_df.columns):
            st.map(coords_df, latitude="lat", longitude="lon")
        else:
            st.warning("Coordinates file exists but lacks required columns: 'site', 'lat', 'lon'.")
    except Exception as e:
        st.warning(f"Could not load coordinates file: {e}")
else:
    st.info(
        "Map view skipped: `data/ghat_coordinates.csv` is not present in the dataset. "
        "Per specification, coordinates are never invented."
    )


# ==========================================
# 7. Footer (Section 6.6 & Hard Rules)
# ==========================================
st.markdown("""
<div class="footer-box">
    <strong>Data Source &amp; Methodology Notes:</strong><br>
    &bull; <strong>Sources:</strong> Madhya Pradesh Pollution Control Board (MPPCB) Visarjan Reports (2023, 2024, 2025) and CPCB Class B (outdoor bathing) criteria.<br>
    &bull; <strong>Assumed Units:</strong> Units are assumed standard because the official MPPCB reports print no units.<br>
    &bull; <strong>Heavy Metals:</strong> Only four metals were tested (chromium, lead, zinc, copper). These have no Class B limit set. Never assume untested metals or water are clean.<br>
    &bull; <strong>No Health Claims:</strong> Readings are compared against statutory limits only. No claims of disease or illness are made.<br>
    &bull; <strong>Decision Support:</strong> This application points to documented evidence; operational decisions rest with the municipal authority.
</div>
""", unsafe_allow_html=True)
