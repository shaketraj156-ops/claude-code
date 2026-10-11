"""Start or reuse the local server, then open the working dashboard."""
from pathlib import Path
import json
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8765'


def ready():
    try:
        with urllib.request.urlopen(URL + '/api/health', timeout=1) as response:
            return json.load(response).get('app') == 'visarjan-ghat-watch'
    except (OSError, ValueError):
        return False


if not ready():
    with (ROOT / 'server.log').open('a') as log:
        subprocess.Popen([sys.executable, str(ROOT / 'server.py')], cwd=ROOT,
                         stdout=log, stderr=log,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    for _ in range(30):
        if ready():
            break
        time.sleep(0.2)
    else:
        raise SystemExit('Could not start the demo. Check server.log in this folder.')
webbrowser.open(URL)
print('Visarjan Ghat Watch ready at ' + URL)
