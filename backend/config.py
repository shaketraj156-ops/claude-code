"""Settings for the Ghat Watch backend. Change limits and weights here only."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
READINGS_CSV = DATA_DIR / "bhopal_ghats_2023_2025.csv"

# Load local gitignored .env if present
_env_path = ROOT / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# CPCB Class B (outdoor bathing). Keys are lowercase on purpose.
LIMITS = {
    "ph": ("range", 6.5, 8.5),
    "dissolved oxygen": ("min", 5.0),   # 5 or more is OK
    "bod": ("max", 3.0),                # 3 or less is OK
}
LIMIT_TEXT = {
    "ph": "6.5 to 8.5",
    "dissolved oxygen": "5 or more",
    "bod": "3 or less",
}
UNITS = {"ph": "", "dissolved oxygen": "mg/l", "bod": "mg/l"}

# Codes that mean "very low, but not zero and not missing"
BDL_FLAGS = {"bdl", "nd"}

# Our own choices. Explain them in the README.
PHASE_WEIGHT = {"pre": 1.0, "during": 2.0, "after": 1.5}
YEAR_WEIGHT = {2023: 1.0, 2024: 1.5, 2025: 2.0}
