"""Vercel serverless entry point. Reuses the local server's request handler unchanged.

Vercel rewrites /api/* and the CSV downloads here with the original path in the `p`
query parameter (see vercel.json); the handler reads it and routes as it does locally.
Static files (index.html, app.js, styles.css, resources/*.pdf) are served by Vercel.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import Handler  # noqa: E402


class handler(Handler):  # Vercel requires this lowercase class name.
    pass
