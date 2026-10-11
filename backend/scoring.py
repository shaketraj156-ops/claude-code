"""Core logic: status of each reading, and the ranking of ghats."""
import pandas as pd

from .config import (BDL_FLAGS, LIMITS, LIMIT_TEXT, PHASE_WEIGHT, UNITS,
                     YEAR_WEIGHT)


def norm(text):
    return str(text).strip().lower()


def status(parameter, value, flag):
    """Return one of: pass, fail, very_low, missing, no_limit.

    A blank value is NEVER treated as clean or as zero.
    """
    if pd.isna(value):
        if norm(flag) in BDL_FLAGS:
            return "very_low"      # below detection: very low, not zero, not missing
        return "missing"           # not sampled, blank, *, ** ...
    rule = LIMITS.get(norm(parameter))
    if rule is None:
        return "no_limit"          # reported, but Class B has no limit for it
    if rule[0] == "min":
        return "pass" if value >= rule[1] else "fail"
    if rule[0] == "max":
        return "pass" if value <= rule[1] else "fail"
    return "pass" if rule[1] <= value <= rule[2] else "fail"


def severity(parameter, value):
    """0 to 1: how far the reading is on the wrong side of the limit."""
    rule = LIMITS[norm(parameter)]
    if rule[0] == "min":
        s = (rule[1] - value) / rule[1]          # oxygen 0 -> 1.0
    elif rule[0] == "max":
        s = (value - rule[1]) / rule[1]
    else:
        lo, hi = rule[1], rule[2]
        span = hi - lo
        s = (lo - value) / span if value < lo else (value - hi) / span
    return max(0.0, min(1.0, s))


def rank_ghats(df, years=None, festivals=None):
    """Ranked table of ghats, highest risk first.

    df must have the columns added by data_loader.load_readings().
    """
    d = df[df["param_key"].isin(LIMITS)]
    if years:
        d = d[d["year"].isin(years)]
    if festivals:
        d = d[d["festival"].isin(festivals)]

    expected = set(map(tuple, d[["year", "festival"]].drop_duplicates().values))
    rows = []
    for site, g in d.groupby("site"):
        measured = g[g["status"].isin(["pass", "fail", "very_low"])]
        missing = g[g["status"] == "missing"]
        fails = g[g["status"] == "fail"]

        num = den = 0.0
        for _, r in measured.iterrows():
            w = (PHASE_WEIGHT.get(norm(r["phase"]), 1.0)
                 * YEAR_WEIGHT.get(int(r["year"]), 1.0))
            risk = 0.0
            if r["status"] == "fail":
                risk = 0.5 + 0.5 * severity(r["parameter"], r["value"])
            num += w * risk
            den += w
        score = round(100 * num / den, 1) if den else None

        evidence = []
        for _, r in fails.iterrows():
            key = r["param_key"]
            evidence.append({
                "year": int(r["year"]),
                "festival": r["festival"],
                "phase": r["phase"],
                "parameter": r["parameter"],
                "value": float(r["value"]),
                "unit": UNITS[key],
                "limit": LIMIT_TEXT[key],
                "source_page": r.get("source_page"),
                "severity": round(severity(r["parameter"], r["value"]), 3),
            })
        evidence.sort(key=lambda e: e["severity"], reverse=True)

        present = set(map(tuple, g[["year", "festival"]].drop_duplicates().values))
        total = len(measured) + len(missing)
        rows.append({
            "site": site,
            "risk_score": score,
            "n_measured": len(measured),
            "n_missing": len(missing),
            "n_fail": len(fails),
            "completeness": round(len(measured) / total, 2) if total else 0.0,
            "table_gaps": sorted(expected - present),
            "evidence": evidence[:3],
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return (out.sort_values("risk_score", ascending=False, na_position="last")
               .reset_index(drop=True))
