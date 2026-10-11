"""Local, dependency-free Visarjan Ghat Watch application. Run: python server.py"""
import os
import csv
import io
import json
import math
import urllib.request
from functools import lru_cache
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse
from analysis import build_model, METHOD_VERSION

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent

HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 8765))

REPORTS = {2023: 'Idol_immer._Report_23_CPCB.pdf', 2024: 'Ganesh_and_Durga_visarjan_report-2024.pdf', 2025: 'Ganesh_and_Durga_visarjan_report-2025.pdf'}
PARAMETERS = {'pH', 'Dissolved oxygen', 'BOD'}
PARAMETER_NAMES = {p.casefold(): p for p in PARAMETERS}
FLAGS = {'': '', 'bdl': 'BDL', 'nd': 'ND', 'not sampled': 'not sampled', '*': '*', '**': '**'}


def signature(row):
    """Match evidence to the bundled reading, never just to its report year."""
    return (int(row['year']), row['festival'], row['site'], row['phase'],
            row['parameter'], float(row['value']) if row['value'] not in ('', None) else None,
            row['flag'], int(row['source_page']) if row['source_page'] else None,
            row.get('unit_assumed', '').casefold().replace(' ', ''))


@lru_cache(maxsize=1)
def bundled_sources():
    with (WORKSPACE / 'impactdata/bhopal_ghats_2023_2025.csv').open(encoding='utf-8-sig', newline='') as source:
        return {signature(row): row for row in csv.DictReader(source)}


def analyze(content):
    reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')), strict=True)
    required = {'year', 'festival', 'site', 'phase', 'parameter', 'value', 'flag', 'source_page'}
    if reader.fieldnames:
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('The CSV has duplicate column names.')
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('Missing columns: ' + ', '.join(sorted(required - set(reader.fieldnames or []))))
    with (WORKSPACE / 'impactdata/cpcb_water_quality_criteria.csv').open(encoding='utf-8') as source:
        criteria = list(csv.DictReader(source))
    limits = {r['parameter']: r['limit'] for r in criteria if r['class'] == 'B'}
    ph_min, ph_max = map(float, limits['pH'].split('-'))
    oxygen_min, bod_max = float(limits['Dissolved oxygen']), float(limits['BOD (5 days 20C)'])
    rows, seen = [], set()
    originals = bundled_sources()
    for line, raw in enumerate(reader, 2):
        if None in raw or any(v is None for v in raw.values()):
            raise ValueError(f'Row {line}: the number of cells does not match the header.')
        r = {k: (v or '').strip() for k, v in raw.items() if k is not None}
        r['phase'] = r['phase'].lower()
        r['festival'] = {'ganesh': 'Ganesh', 'durga': 'Durga'}.get(r['festival'].lower(), r['festival'])
        r['parameter'] = PARAMETER_NAMES.get(r['parameter'].casefold(), r['parameter'])
        if not r['site'] or r['phase'] not in ('pre', 'during', 'after') or not r['festival'] or not r['parameter']:
            raise ValueError(f'Row {line}: site, festival, parameter and a valid phase are required.')
        if r['flag'].lower() not in FLAGS:
            raise ValueError(f'Row {line}: unsupported flag. Use BDL, ND, not sampled, *, **, or leave it blank.')
        r['flag'] = FLAGS[r['flag'].lower()]
        try:
            r['year'] = int(r['year'])
            r['source_page'] = int(r['source_page']) if r['source_page'] else None
            r['value'] = float(r['value']) if r['value'] else None
        except ValueError:
            raise ValueError(f'Row {line}: invalid year, page or numeric value.')
        if r['value'] is not None and not math.isfinite(r['value']):
            raise ValueError(f'Row {line}: value must be finite.')
        if r['year'] < 1 or (r['source_page'] is not None and r['source_page'] < 1):
            raise ValueError(f'Row {line}: year and source page must be positive.')
        if r['flag'] and r['value'] is not None:
            raise ValueError(f'Row {line}: provide a numeric value OR a flag, not both.')
        if r['value'] is not None and (r['value'] < 0 or (r['parameter'] == 'pH' and r['value'] > 14)):
            raise ValueError(f'Row {line}: values must be nonnegative and pH must be between 0 and 14.')
        unit = r.get('unit_assumed', '').casefold().replace(' ', '')
        if r['parameter'] in ('Dissolved oxygen', 'BOD'):
            if unit not in ('', 'mg/l'):
                raise ValueError(f'Row {line}: {r["parameter"]} must be supplied in mg/l; convert the value before uploading.')
            r['unit_assumed'] = 'mg/l'
        elif r['parameter'] == 'pH':
            if unit not in ('', 'none', 'unitless', 'dimensionless', '-'):
                raise ValueError(f'Row {line}: pH must be dimensionless.')
            r['unit_assumed'] = ''
        key = tuple(r[k] for k in ('year', 'festival', 'site', 'phase', 'parameter'))
        if key in seen:
            raise ValueError(f'Row {line}: duplicate measurement. Remove duplicate rows before uploading.')
        seen.add(key)
        r['status'], r['severity'] = 'No Class B reference', 0
        if r['flag'] or r['value'] is None:
            r['status'] = 'Below detection / not detected' if r['flag'].upper() in ('BDL', 'ND') else 'Not sampled / unavailable'
        elif r['parameter'] in PARAMETERS:
            v, p = r['value'], r['parameter']
            severity = max(0, (oxygen_min-v)/oxygen_min) if p == 'Dissolved oxygen' else max(0, (v-bod_max)/bod_max) if p == 'BOD' else max(0, ph_min-v, v-ph_max)/(ph_max-ph_min)
            r['severity'] = severity
            r['status'] = 'Outside reference' if severity > 0 else 'Within reference'
        original = originals.get(signature(r))
        r['report'] = REPORTS.get(r['year']) if original else None
        if original:
            r['site_match_confidence'] = original['site_match_confidence']
        r['id'] = len(rows)
        rows.append(r)
    if not rows:
        raise ValueError('The CSV contains no measurements.')
    display_limits = {'pH': f'{ph_min:g}–{ph_max:g}', 'Dissolved oxygen': f'≥ {oxygen_min:g} mg/l', 'BOD': f'≤ {bod_max:g} mg/l'}
    return {'rows': rows, 'limits': display_limits, 'thresholds': {'pH': [ph_min, ph_max], 'Dissolved oxygen': [oxygen_min], 'BOD': [bod_max]}, 'model': build_model(rows, display_limits)}


class Handler(BaseHTTPRequestHandler):
    def send(self, code, data, kind='application/json; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            self.get_resource()
        except FileNotFoundError:
            self.send(404, json.dumps({'error': 'A required local data or report file is missing.'}).encode())
        except (ValueError, csv.Error):
            self.send(500, json.dumps({'error': 'The bundled data could not be read. Check the local CSV files.'}).encode())

    def get_resource(self):
        path = unquote(urlparse(self.path).path)
        if path == '/api/health':
            self.send(200, json.dumps({'app': 'visarjan-ghat-watch', 'version': METHOD_VERSION}).encode())
        elif path in ('/api/sample', '/api/data'):
            filename = 'sample_bhopal_2025.csv' if path == '/api/sample' else 'bhopal_ghats_2023_2025.csv'
            result = analyze((WORKSPACE / 'impactdata' / filename).read_text(encoding='utf-8-sig'))
            self.send(200, json.dumps(result).encode())
        elif path == '/sample.csv':
            self.send(200, (WORKSPACE / 'impactdata/sample_bhopal_2025.csv').read_bytes(), 'text/csv; charset=utf-8')
        elif path == '/data.csv':
            self.send(200, (WORKSPACE / 'impactdata/bhopal_ghats_2023_2025.csv').read_bytes(), 'text/csv; charset=utf-8')
        elif path == '/template.csv':
            from datetime import date
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['year', 'festival', 'site', 'phase', 'parameter', 'value', 'flag', 'source_page', 'unit_assumed', 'source_document'])
            for phase in ('pre', 'during', 'after'):
                for parameter in ('pH', 'Dissolved oxygen', 'BOD'):
                    writer.writerow([date.today().year, 'Durga', 'New site - replace this name', phase, parameter, '', 'not sampled', '', '' if parameter == 'pH' else 'mg/l', ''])
            self.send(200, output.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8')
        elif path.startswith('/reports/') and path.removeprefix('/reports/') in REPORTS.values():
            self.send(200, (WORKSPACE / 'dataa' / path.removeprefix('/reports/')).read_bytes(), 'application/pdf')
        elif path in ('/', '/index.html', '/app.js', '/styles.css'):
            name = path.lstrip('/') or 'index.html'
            kind = 'text/javascript' if name.endswith('.js') else 'text/css' if name.endswith('.css') else 'text/html'
            self.send(200, (ROOT / name).read_bytes(), kind + '; charset=utf-8')
        else:
            self.send(404, b'Not found', 'text/plain')

    def do_POST(self):
        if self.path != '/api/analyze':
            return self.send(404, b'Not found')
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 2_000_000:
                raise ValueError('Upload a CSV smaller than 2 MB.')
            result = analyze(self.rfile.read(size).decode('utf-8-sig'))
            self.send(200, json.dumps(result).encode())
        except (ValueError, UnicodeError, csv.Error) as exc:
            self.send(400, json.dumps({'error': str(exc)}).encode())
        except OSError:
            self.send(500, json.dumps({'error': 'Required local reference data could not be read.'}).encode())


class Server(ThreadingHTTPServer):
    # Windows lets a second process co-bind a port that already has SO_REUSEADDR set.
    # That silently shadows the first server and can serve stale code, so fail loudly.
    allow_reuse_address = False


def already_serving():
    try:
        with urllib.request.urlopen(f'http://{HOST}:{PORT}/api/health', timeout=1) as response:
            return json.load(response).get('app') == 'visarjan-ghat-watch'
    except (OSError, ValueError):
        return False


if __name__ == '__main__':
    if already_serving():
        print(f'Visarjan Ghat Watch is already running at http://{HOST}:{PORT}')
        print('Open that address in your browser; there is nothing else to start.')
        print('Changed a .py file? Stop the old one first:  taskkill /F /IM python.exe')
        raise SystemExit(0)
    print(f'Visarjan Ghat Watch: http://{HOST}:{PORT}', flush=True)
    print('Press Ctrl+C to stop.', flush=True)
    server = Server((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nVisarjan Ghat Watch stopped.', flush=True)
    finally:
        server.server_close()
