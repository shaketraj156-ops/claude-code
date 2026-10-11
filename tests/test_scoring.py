import pandas as pd

from backend.brief import make_brief
from backend.scoring import norm, rank_ghats, severity, status

NAN = float("nan")


def test_blank_is_missing_not_clean():
    assert status("BOD", NAN, "not sampled") == "missing"
    assert status("BOD", NAN, None) == "missing"


def test_bdl_and_nd_are_very_low():
    assert status("Lead", NAN, "BDL") == "very_low"
    assert status("Lead", NAN, "ND") == "very_low"


def test_oxygen_limit():
    assert status("Dissolved oxygen", 0, None) == "fail"
    assert status("Dissolved oxygen", 4.9, None) == "fail"
    assert status("Dissolved oxygen", 5, None) == "pass"


def test_bod_limit():
    assert status("BOD", 4, None) == "fail"
    assert status("BOD", 3, None) == "pass"


def test_ph_range():
    assert status("pH", 6.4, None) == "fail"
    assert status("pH", 7.0, None) == "pass"
    assert status("pH", 8.6, None) == "fail"


def test_no_limit_parameter():
    assert status("Chromium", 0.2, None) == "no_limit"


def test_severity_zero_oxygen_is_max():
    assert severity("Dissolved oxygen", 0) == 1.0
    assert severity("Dissolved oxygen", 5) == 0.0


def _frame(rows):
    df = pd.DataFrame(rows, columns=["site", "year", "festival", "phase",
                                     "parameter", "value", "flag", "source_page"])
    df["param_key"] = df["parameter"].map(norm)
    df["status"] = [status(p, v, f) for p, v, f in
                    zip(df["parameter"], df["value"], df["flag"])]
    return df


def test_ranking_and_gaps():
    df = _frame([
        ["Bad kund", 2025, "Durga", "during", "Dissolved oxygen", 0.0, None, 28],
        ["Bad kund", 2025, "Durga", "pre", "BOD", 2.0, None, 28],
        ["Good ghat", 2025, "Durga", "during", "Dissolved oxygen", 7.0, None, 30],
        ["Good ghat", 2025, "Durga", "during", "BOD", NAN, "not sampled", 30],
        ["No Durga ghat", 2025, "Ganesh", "during", "BOD", 1.0, None, 12],
    ])
    r = rank_ghats(df)
    assert r.iloc[0]["site"] == "Bad kund"
    assert r.iloc[0]["risk_score"] == 66.7            # 100 * 4 / (4 + 2)
    assert r.iloc[0]["evidence"][0]["source_page"] == 28
    good = r[r["site"] == "Good ghat"].iloc[0]
    assert good["n_missing"] == 1 and good["completeness"] == 0.5
    gap = r[r["site"] == "No Durga ghat"].iloc[0]
    assert (2025, "Durga") in gap["table_gaps"]


def test_brief_has_page_and_gap_text():
    df = _frame([
        ["Bad kund", 2025, "Durga", "during", "Dissolved oxygen", 0.0, None, 28],
        ["Other", 2025, "Ganesh", "during", "BOD", 1.0, None, 12],
    ])
    r = rank_ghats(df)
    en = make_brief(r, "en")
    hi = make_brief(r, "hi")
    assert "report page 28" in en and "no 2025 Durga table" in en
    assert "विसर्जन" in hi
