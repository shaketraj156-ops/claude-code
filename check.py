"""Quick terminal check. Run: python check.py"""
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend import load_readings, make_brief, rank_ghats

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

df = load_readings()
print(df["status"].value_counts(), "\n")
ranked = rank_ghats(df)
print(ranked[["site", "risk_score", "n_fail", "n_missing",
              "completeness", "table_gaps"]], "\n")
print(make_brief(ranked, "en"))
print()
print(make_brief(ranked, "hi"))
