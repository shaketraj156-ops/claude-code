"""Start the application from the repository root."""
from pathlib import Path
import runpy
import sys

APP_DIR = Path(__file__).resolve().parent / "Track2-ClaudeImpactLabs" / "visarjan-demo"

if __name__ == "__main__":
    sys.path.insert(0, str(APP_DIR))
    runpy.run_path(str(APP_DIR / "server.py"), run_name="__main__")
