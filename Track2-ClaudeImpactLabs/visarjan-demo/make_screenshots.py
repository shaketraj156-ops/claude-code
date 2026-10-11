"""Regenerate the README screenshots and the sample officer brief PDF in docs/.

Development helper only (pip install -r requirements-dev.txt). Starts an isolated
server on a free port, so it never touches a running demo. Run: python make_screenshots.py
"""
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from server import Handler

OUT = Path(__file__).resolve().parent / 'docs'


class QuietHandler(Handler):
    def log_message(self, *_):
        pass


def main():
    OUT.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url)
        expect(page.locator('#loading')).to_contain_text('1,524 readings')
        expect(page.locator('#map svg')).to_have_count(1)
        page.screenshot(path=str(OUT / 'overview.png'), full_page=True)
        page.locator('.priority-panel').screenshot(path=str(OUT / 'map-and-ranking.png'))
        page.locator('#tab-history').click()
        page.select_option('#history-parameter', 'Dissolved oxygen')
        page.locator('#detail').screenshot(path=str(OUT / 'history.png'))
        page.locator('#tab-overview').click()
        page.locator('#open-brief').click()
        page.locator('#brief-dialog').screenshot(path=str(OUT / 'brief.png'))
        page.emulate_media(media='print')
        page.pdf(path=str(OUT / 'officer-brief-sample.pdf'), format='A4', print_background=True,
                 margin={'top': '12mm', 'bottom': '12mm', 'left': '12mm', 'right': '12mm'})
        page.emulate_media(media='screen')
        page.locator('#close-brief').click()
        page.set_viewport_size({'width': 390, 'height': 844})
        page.screenshot(path=str(OUT / 'mobile.png'), full_page=True)
        browser.close()
    server.shutdown()
    server.server_close()
    if errors:
        raise SystemExit('Page errors: ' + '; '.join(errors))
    print('Wrote screenshots and officer-brief-sample.pdf to', OUT)


if __name__ == '__main__':
    main()
