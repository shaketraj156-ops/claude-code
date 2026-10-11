"""Load the readings CSV and add the columns the scoring code needs."""
import pandas as pd

from .config import READINGS_CSV
from .scoring import norm, status


def load_readings(path=READINGS_CSV):
    df = pd.read_csv(path)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["param_key"] = df["parameter"].map(norm)
    df["status"] = [status(p, v, f)
                    for p, v, f in zip(df["parameter"], df["value"], df["flag"])]
    return df
