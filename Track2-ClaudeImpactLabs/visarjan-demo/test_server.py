"""Regression checks: python -m unittest test_server -v"""
import csv
import io
import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from server import analyze, Handler, DATA_DIR

FIELDS = ['year', 'festival', 'site', 'phase', 'parameter', 'value', 'flag', 'source_page', 'unit_assumed']


def record(**changes):
    result = dict(year='2026', festival='Ganesh', site='Test kund', phase='pre',
                  parameter='BOD', value='3', flag='', source_page='', unit_assumed='mg/l')
    result.update(changes)
    return result


def as_csv(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


class AnalysisTests(unittest.TestCase):
    def test_bundled_files_and_sources(self):
        for name, count in [('sample_bhopal_2025.csv', 453), ('bhopal_ghats_2023_2025.csv', 1524)]:
            data = analyze((DATA_DIR / name).read_text(encoding='utf-8-sig'))
            self.assertEqual(len(data['rows']), count)
            self.assertTrue(all(r['report'] for r in data['rows']))

    def test_bairagarh_actual_breaches_and_missing(self):
        data = analyze((DATA_DIR / 'sample_bhopal_2025.csv').read_text(encoding='utf-8-sig'))
        rows = [r for r in data['rows'] if 'Bairagarh' in r['site'] and r['festival'] == 'Ganesh'
                and r['parameter'] in ('pH', 'BOD', 'Dissolved oxygen')]
        self.assertEqual(sum(r['status'] == 'Outside reference' for r in rows), 2)
        self.assertEqual(sum(r['status'] == 'Not sampled / unavailable' for r in rows), 6)

    def test_reference_boundaries_and_zero(self):
        cases = [('pH', 6.5, False), ('pH', 8.5, False), ('pH', 8.51, True),
                 ('BOD', 3, False), ('BOD', 3.01, True), ('BOD', 0, False),
                 ('Dissolved oxygen', 5, False), ('Dissolved oxygen', 4.99, True), ('Dissolved oxygen', 0, True)]
        for parameter, value, breach in cases:
            with self.subTest(parameter=parameter, value=value):
                r = analyze(as_csv([record(parameter=parameter, value=value, unit_assumed='' if parameter == 'pH' else 'mg/l')]))['rows'][0]
                self.assertEqual(r['status'] == 'Outside reference', breach)

    def test_missing_and_censored_never_pass(self):
        for flag in ['', 'BDL', 'ND', 'not sampled', '*', '**']:
            row = analyze(as_csv([record(value='', flag=flag)]))['rows'][0]
            self.assertIsNone(row['value'])
            self.assertNotIn(row['status'], ('Within reference', 'Outside reference'))

    def test_invalid_values_flags_and_units(self):
        cases = [dict(value='NaN'), dict(value='inf'), dict(value='-1'), dict(value='2', flag='BDL'),
                 dict(value='', flag='clean'), dict(unit_assumed='ug/l'), dict(parameter='pH', value='15', unit_assumed=''),
                 dict(parameter='pH', value='7', unit_assumed='mg/l'), dict(parameter=''), dict(source_page='0'), dict(year='0')]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                analyze(as_csv([record(**values)]))

    def test_normalizes_case_and_detects_duplicates(self):
        row = record(parameter='bod', phase='PRE', festival='ganesh', unit_assumed='mg/L')
        result = analyze(as_csv([row]))['rows'][0]
        self.assertEqual(result['parameter'], 'BOD')
        self.assertEqual(result['festival'], 'Ganesh')
        with self.assertRaisesRegex(ValueError, 'duplicate measurement'):
            analyze(as_csv([row, record()]))

    def test_malformed_csv_rejected(self):
        valid = as_csv([record()])
        lines = valid.splitlines()
        for value in ['site,value\na,1', lines[0]+'\n', valid.rstrip()+',extra\n',
                      lines[0]+'\n'+','.join(lines[1].split(',')[:-1]),
                      lines[0]+',site\n'+lines[1]+',another site', lines[0]+'\n"unclosed']:
            with self.subTest(value=value), self.assertRaises((ValueError, csv.Error)):
                analyze(value)

    def test_sources_are_not_invented_for_uploaded_rows(self):
        original = next(csv.DictReader((DATA_DIR / 'sample_bhopal_2025.csv').read_text(encoding='utf-8-sig').splitlines()))
        self.assertIsNotNone(analyze(as_csv([original]))['rows'][0]['report'])
        for change in [dict(value='7.35'), dict(site='New kund'), dict(source_page='99')]:
            updated = dict(original, **change)
            self.assertIsNone(analyze(as_csv([updated]))['rows'][0]['report'])
        self.assertIsNone(analyze(as_csv([record(year='2025', source_page='28')]))['rows'][0]['report'])

    def test_noncore_does_not_enter_class_b_score(self):
        result = analyze(as_csv([record(parameter='COD', value='200')]))['rows'][0]
        self.assertEqual(result['status'], 'No Class B reference')


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_endpoints_and_upload(self):
        for path in ['/', '/app.js', '/styles.css', '/sample.csv', '/data.csv', '/template.csv', '/api/health', '/api/sample', '/api/data', '/reports/Ganesh_and_Durga_visarjan_report-2025.pdf']:
            with urllib.request.urlopen(self.url+path) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
        request = urllib.request.Request(self.url+'/api/analyze', data=as_csv([record()]).encode())
        with urllib.request.urlopen(request) as response:
            self.assertEqual(json.load(response)['rows'][0]['value'], 3)

    def test_bad_upload_returns_json_error(self):
        request = urllib.request.Request(self.url+'/api/analyze', data=b'bad csv')
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 400)
        self.assertIn('error', json.load(caught.exception))

    def test_missing_data_returns_error_instead_of_dropped_connection(self):
        with patch('server.analyze', side_effect=FileNotFoundError):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(self.url+'/api/sample')
        self.assertEqual(caught.exception.code, 404)
        self.assertIn('error', json.load(caught.exception))


if __name__ == '__main__':
    unittest.main()
