"""Chrome regression checks (optional dev dependency: pip install playwright)."""
import json
import csv
import io
import threading
import unittest
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from server import Handler, DATA_DIR, analyze
from analysis import METHOD_VERSION
from test_server import as_csv, record


class QuietHandler(Handler):
    def log_message(self, *_):
        pass


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel='chrome', headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.page = self.browser.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.goto(self.url+'/?dataset=sample')
        expect(self.page.locator('#loading')).to_contain_text('453 readings')

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.errors, [])

    def upload(self, text):
        self.page.locator('#upload').set_input_files({'name': 'test.csv', 'mimeType': 'text/csv', 'buffer': text.encode()})

    def test_complete_and_missing_coverage(self):
        self.page.locator('#ranking').get_by_role('button', name='Hathaikheda', exact=False).click()
        expect(self.page.locator('#coverage-note')).to_contain_text('All 9 core checks are available')
        expect(self.page.locator('#core-table td.bad')).to_have_count(4)
        self.page.locator('#ranking').get_by_role('button', name='Bairagarh', exact=False).click()
        expect(self.page.locator('#coverage-note')).to_contain_text('6 of 9 core checks could not be assessed')
        expect(self.page.locator('#coverage-note')).to_contain_text('0 of 3 core parameters')
        expect(self.page.locator('#core-table td.bad')).to_have_count(2)

    def test_all_years_festivals_and_core_measurements(self):
        self.page.locator('#upload').set_input_files(str(DATA_DIR / 'bhopal_ghats_2023_2025.csv'))
        expect(self.page.locator('#loading')).to_contain_text('1,524 readings')
        rows = analyze((DATA_DIR / 'bhopal_ghats_2023_2025.csv').read_text(encoding='utf-8-sig'))['rows']
        for year in ['2023', '2024', '2025']:
            self.page.select_option('#year', year)
            for festival in ['Ganesh', 'Durga']:
                self.page.select_option('#festival', festival)
                selected = [r for r in rows if str(r['year']) == year and r['festival'] == festival]
                sites = sorted(set(r['site'] for r in rows))
                expect(self.page.locator('#ranking button')).to_have_count(len(sites))
                for site in sites:
                    self.page.locator('#ranking').get_by_role('button', name=site, exact=False).click()
                    core = [r for r in selected if r['site'] == site and r['parameter'] in ('pH', 'BOD', 'Dissolved oxygen')]
                    numeric = [r for r in core if r['value'] is not None and not r['flag']]
                    bad = [r for r in numeric if (r['parameter'] == 'pH' and not 6.5 <= r['value'] <= 8.5)
                           or (r['parameter'] == 'BOD' and r['value'] > 3)
                           or (r['parameter'] == 'Dissolved oxygen' and r['value'] < 5)]
                    expect(self.page.locator('#core-table td.bad')).to_have_count(len(bad))
                    note = self.page.locator('#coverage-note').inner_text()
                    self.assertIn('All 9' if len(numeric) == 9 else f'{9-len(numeric)} of 9', note)
        # Changing years preserves the selected festival when it exists in both.
        self.page.select_option('#year', '2023')
        expect(self.page.locator('#festival')).to_have_value('Durga')

    def test_invalid_upload_retains_previous_dataset(self):
        self.upload(as_csv([record(unit_assumed='ug/l')]))
        expect(self.page.locator('#error')).to_contain_text('must be supplied in mg/l')
        expect(self.page.locator('#error')).to_contain_text('previous dataset')
        expect(self.page.locator('#sites')).to_have_text('7')
        self.page.get_by_role('button', name='Reload data').click()
        expect(self.page.locator('#error')).to_be_empty()

    def test_unknown_source_missing_only_and_markup_escaping(self):
        name = '<img src=x onerror=alert(1)> & Test'
        self.upload(as_csv([record(year='2025', site=name, value='', flag='BDL', source_page='28')]))
        expect(self.page.locator('#loading')).to_contain_text('Uploaded CSV')
        expect(self.page.locator('#detail h2')).to_have_text(name)
        expect(self.page.locator('#detail img')).to_have_count(0)
        expect(self.page.locator('#ranking')).to_contain_text('Unranked')
        expect(self.page.locator('#detail .badge')).to_have_text('Insufficient data')
        expect(self.page.locator('#detail a[href^="/reports/"]')).to_have_count(0)
        self.page.locator('#site-brief').click()
        expect(self.page.locator('#brief-en')).to_contain_text('Uploaded source not matched')
        self.page.locator('#close-brief').click()
        expect(self.page.locator('#core-table td.ok')).to_have_count(0)

    def test_tied_priorities_and_partial_before_after(self):
        rows = [record(site=site, parameter='pH', value='7', unit_assumed='', phase=phase)
                for site in ['A', 'B'] for phase in ['pre', 'after']]
        self.upload(as_csv(rows))
        expect(self.page.locator('#loading')).to_contain_text('4 readings')
        names = self.page.locator('#ranking button b').all_text_contents()
        self.assertEqual(names, ['A', 'B'])
        self.assertEqual(self.page.locator('#ranking .rank-number').all_text_contents(), ['1','1'])
        expect(self.page.locator('#coverage-note')).to_contain_text('1 of 3 core parameters')

    def test_download_and_print_include_hindi_and_caveats(self):
        self.page.locator('#ranking').get_by_role('button', name='Rani Kamlapati', exact=False).click()
        self.page.locator('#site-brief').click()
        with self.page.expect_download() as download:
            self.page.locator('#download-brief').click()
        text = download.value.path().read_text(encoding='utf-8')
        self.assertIn('हिंदी', text)
        self.assertIn('Site identity needs confirmation', text)
        self.assertIn('Total coliform', text)
        self.page.emulate_media(media='print')
        expect(self.page.locator('#brief-hi')).to_be_visible()
        expect(self.page.locator('#brief-en')).to_be_visible()
        expect(self.page.locator('.dialog-actions')).not_to_be_visible()

    def test_failed_initial_load_can_recover(self):
        self.page.route('**/api/sample', lambda route: route.abort())
        self.page.reload()
        expect(self.page.locator('#error')).to_contain_text('Could not load measurements')
        expect(self.page.locator('#year')).to_be_disabled()
        self.page.unroute('**/api/sample')
        self.page.locator('#reset').click()
        expect(self.page.locator('#year')).to_be_enabled()
        expect(self.page.locator('#festival')).to_have_value('Ganesh')

    def test_latest_request_wins_even_if_old_response_arrives_last(self):
        payloads = {name: analyze(as_csv([record(site=name)])) for name in ['slow', 'fast']}
        self.page.evaluate('''async (payloads) => {
          const original = window.fetch;
          window.fetch = (_, options) => new Promise(resolve => setTimeout(
            () => resolve({ok:true, json:async()=>payloads[options.body]}),
            options.body === 'slow' ? 200 : 10));
          try { await Promise.all([load('slow'), load('fast')]); }
          finally { window.fetch = original; }
        }''', payloads)
        expect(self.page.locator('#detail h2')).to_have_text('fast')

    def test_mobile_layout_does_not_overflow(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.locator('#ranking').get_by_role('button', name='Hathaikheda', exact=False).click()
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))

    def test_full_default_and_absent_sites_remain_in_testing_list(self):
        self.page.goto(self.url)
        expect(self.page.locator('#loading')).to_contain_text('1,524 readings')
        expect(self.page.locator('#year')).to_have_value('all')
        self.page.select_option('#year', '2025')
        self.page.select_option('#festival', 'Durga')
        expect(self.page.locator('#sites')).to_have_text('7')
        self.page.locator('#testing-tab').click()
        top = self.page.locator('#ranking button b').all_text_contents()[:2]
        self.assertTrue(any('Bairagarh' in name for name in top))
        self.assertTrue(any('Malikhedi' in name for name in top))
        self.page.locator('#ranking').get_by_role('button', name='Bairagarh', exact=False).click()
        expect(self.page.locator('#detail-content .warning')).to_contain_text('no records')
        expect(self.page.locator('#core-table td.bad')).to_have_count(0)
        expect(self.page.locator('#core-table td.ok')).to_have_count(0)
        expect(self.page.locator('#coverage-note')).to_contain_text('9 of 9')

    def test_map_markers_follow_ranking_and_select_sites(self):
        self.page.goto(self.url)
        expect(self.page.locator('#loading')).to_contain_text('1,524 readings')
        # The live map hides the schematic; the schematic stays the testable, offline-safe copy.
        self.page.evaluate("document.body.classList.remove('has-live-map')")
        markers = self.page.locator('#map .marker')
        expect(markers).to_have_count(7)
        # Marker numbers are the same ranks as the list, and clicking one selects that ghat.
        ranks = {m.get_attribute('data-site'): m.locator('text').first.text_content() for m in markers.all()}
        listed = dict(zip(self.page.locator('#ranking button b').all_text_contents(),
                          self.page.locator('#ranking .rank-number').all_text_contents()))
        self.assertEqual(ranks, listed)
        self.page.locator('#map .marker[data-site="Shahpura lake ghat"]').click()
        expect(self.page.locator('#detail h2')).to_have_text('Shahpura lake ghat')
        expect(self.page.locator('#map .marker.active')).to_have_attribute('data-site', 'Shahpura lake ghat')
        expect(self.page.locator('#breach-breakdown li')).to_have_count(3)
        expect(self.page.locator('#breach-breakdown')).to_contain_text('42 / 116')
        expect(self.page.locator('#breach-breakdown')).to_contain_text('100 / 112')
        # An uploaded site with no public position is reported, not silently dropped.
        self.upload(as_csv([record(site='Somewhere new', value=8)]))
        expect(self.page.locator('#loading')).to_contain_text('Uploaded CSV')
        expect(self.page.locator('#map .marker')).to_have_count(0)
        expect(self.page.locator('#map-note')).to_contain_text('Not on map')

    def test_recovery_history_evidence_and_report_links(self):
        self.page.select_option('#dataset', 'full')
        expect(self.page.locator('#loading')).to_contain_text('1,524 readings')
        self.page.select_option('#year', '2025')
        self.page.select_option('#festival', 'Ganesh')
        self.page.locator('#ranking').get_by_role('button', name='Hathaikheda', exact=False).click()
        self.page.locator('#tab-recovery').click()
        expect(self.page.locator('#recovery-table')).to_contain_text('Still outside reference')
        self.page.locator('#tab-history').click()
        self.page.select_option('#history-parameter', 'BOD')
        expect(self.page.locator('#history-table tbody tr')).to_have_count(3)
        expect(self.page.locator('#history-chart svg')).to_have_count(1)
        self.assertNotIn('NaN', self.page.locator('#history-chart').inner_html())
        self.page.locator('#tab-evidence').click()
        self.page.select_option('#evidence-parameter', 'BOD')
        expect(self.page.locator('#evidence-register tbody tr')).to_have_count(3)
        link = self.page.locator('#evidence-register a').first.get_attribute('href')
        response = self.page.request.get(self.url + link.split('#')[0])
        self.assertEqual(response.status, 200)
        self.assertTrue(response.body().startswith(b'%PDF'))
        with self.page.expect_download() as download:
            self.page.locator('#export-evidence').click()
        content = download.value.path().read_text(encoding='utf-8-sig')
        self.assertEqual(len(analyze(content)['rows']), 39)

    def test_priority_export_and_consolidated_bilingual_brief(self):
        self.page.goto(self.url)
        expect(self.page.locator('#loading')).to_contain_text('1,524 readings')
        with self.page.expect_download() as download:
            self.page.locator('#export-ranks').click()
        exported = list(csv.DictReader(io.StringIO(download.value.path().read_text(encoding='utf-8-sig'))))
        self.assertEqual(len(exported), 7)
        self.assertTrue(all(r['scope_year']=='all' and r['method_version']==METHOD_VERSION for r in exported))
        # The exported rank must be explained by the same reading the brief cites.
        top = exported[0]
        self.assertEqual((top['pollution_rank'], top['rank_reason_parameter']), ('1', 'Dissolved oxygen'))
        self.assertEqual(float(top['rank_reason_value']), 0.0)
        self.assertEqual(top['worst_deviation_parameter'], 'BOD')
        self.page.locator('#open-brief').click()
        expect(self.page.locator('#brief-en')).to_contain_text('Fresh testing priority')
        expect(self.page.locator('#brief-en')).to_contain_text(
            f"{top['rank_reason_parameter']} {float(top['rank_reason_value'])} mg/l")
        expect(self.page.locator('#brief-hi')).to_contain_text('नई जाँच की प्राथमिकता')
        with self.page.expect_download() as download:
            self.page.locator('#download-brief').click()
        self.assertIn('हिंदी', download.value.path().read_text(encoding='utf-8'))
        self.page.locator('#close-brief').click()
        self.page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
        expect(self.page.locator('#brief-dialog')).to_be_visible()
        self.page.evaluate("window.dispatchEvent(new Event('afterprint'))")
        expect(self.page.locator('#brief-dialog')).not_to_be_visible()

    def test_detail_opens_on_the_event_that_explains_the_rank(self):
        self.page.goto(self.url)
        expect(self.page.locator('#loading')).to_contain_text('1,524 readings')
        # The top ghat has no Durga 2025 records, so the latest event would show an
        # empty table directly under a reason citing Ganesh 2025.
        expect(self.page.locator('#detail h2')).to_contain_text('Bairagarh')
        expect(self.page.locator('.lead-reason')).to_contain_text('Ganesh 2025')
        expect(self.page.locator('#event')).to_have_value('2025|Ganesh')
        expect(self.page.locator('#detail-content .warning')).to_have_count(0)
        self.assertGreater(self.page.locator('#core-table td.bad').count(), 0)
        # Each ghat re-opens on its own rank-driving event rather than inheriting one.
        self.page.locator('#ranking').get_by_role('button', name='Rani Kamlapati', exact=False).click()
        expect(self.page.locator('.lead-reason')).to_contain_text('Durga 2025')
        expect(self.page.locator('#event')).to_have_value('2025|Durga')
        self.assertGreater(self.page.locator('#core-table td.bad').count(), 0)

    def test_event_csv_carries_the_site_identity_warning(self):
        self.page.goto(self.url)
        expect(self.page.locator('#loading')).to_contain_text('1,524 readings')
        self.page.locator('#ranking').get_by_role('button', name='Rani Kamlapati', exact=False).click()
        expect(self.page.locator('#detail > .warning')).to_contain_text('Confirm this site identity')
        self.page.locator('#tab-evidence').click()
        with self.page.expect_download() as download:
            self.page.locator('#export-evidence').click()
        rows = list(csv.DictReader(io.StringIO(download.value.path().read_text(encoding='utf-8-sig'))))
        self.assertTrue(rows)
        # The caveat on screen must survive into the file the officer forwards.
        self.assertTrue(all(r['identity_needs_check'] == 'yes' for r in rows))
        self.assertTrue(any(r['site_match_confidence'] == 'medium' for r in rows))

    def test_csv_formula_injection_is_escaped(self):
        self.upload(as_csv([record(site='=SUM(1,2)', value=8)]))
        expect(self.page.locator('#loading')).to_contain_text('Uploaded CSV')
        with self.page.expect_download() as download:
            self.page.locator('#export-ranks').click()
        exported = list(csv.DictReader(io.StringIO(download.value.path().read_text(encoding='utf-8-sig'))))
        self.assertEqual(exported[0]['site'], "'=SUM(1,2)")

    def test_chart_does_not_bridge_missing_year(self):
        self.upload(as_csv([record(year='2023', phase='during', value=8), record(year='2024', phase='during', value='', flag='not sampled'), record(year='2025', phase='during', value=6)]))
        expect(self.page.locator('#loading')).to_contain_text('3 readings')
        self.page.locator('#tab-history').click()
        self.page.select_option('#history-parameter', 'BOD')
        expect(self.page.locator('#history-chart circle')).to_have_count(2)
        expect(self.page.locator('#history-chart line[stroke="#b26047"]')).to_have_count(0)

    def test_new_site_template_and_dataset_switch(self):
        response = self.page.request.get(self.url + '/template.csv')
        self.upload(response.body().decode('utf-8-sig'))
        expect(self.page.locator('#loading')).to_contain_text('9 readings')
        expect(self.page.locator('#detail .badge')).to_have_text('Insufficient data')
        expect(self.page.locator('#coverage')).to_have_text('0%')
        self.page.select_option('#dataset', 'full')
        expect(self.page.locator('#loading')).to_contain_text('1,524 readings')
        expect(self.page.locator('#year option')).to_have_count(4)

    def test_small_numeric_value_is_not_displayed_as_zero(self):
        self.upload(as_csv([record(parameter='Dissolved oxygen', value='0.0001')]))
        expect(self.page.locator('#loading')).to_contain_text('1 readings')
        expect(self.page.locator('#core-table td.bad')).to_have_text('0.0001')

    def test_history_works_when_no_numeric_values_exist(self):
        self.upload(as_csv([record(parameter='Dissolved oxygen', value='', flag='ND')]))
        expect(self.page.locator('#loading')).to_contain_text('1 readings')
        self.page.locator('#tab-history').click()
        expect(self.page.locator('#history-chart')).to_contain_text('No numeric readings')
        expect(self.page.locator('#history-chart svg')).to_have_count(0)

    def test_dataset_dropdown_restores_uploaded_measurements(self):
        self.upload(as_csv([record(site='My uploaded ghat', value=8)]))
        expect(self.page.locator('#loading')).to_contain_text('Uploaded CSV')
        self.page.select_option('#dataset', 'full')
        expect(self.page.locator('#loading')).to_contain_text('1,524 readings')
        self.page.select_option('#dataset', 'upload')
        expect(self.page.locator('#loading')).to_contain_text('Uploaded CSV')
        expect(self.page.locator('#detail h2')).to_have_text('My uploaded ghat')
        expect(self.page.locator('#sites')).to_have_text('1')


if __name__ == '__main__':
    unittest.main()
