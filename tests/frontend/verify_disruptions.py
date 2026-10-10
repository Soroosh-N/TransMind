"""Exercise disruption editing, placement, and saved commutes."""
import argparse
from playwright.sync_api import sync_playwright
parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8002')
args = parser.parse_args()
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    for width in (1440, 390):
        context = browser.new_context(viewport={'width': width, 'height': 950})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url)
        page.wait_for_function('window.transitMindMapState')
        page.locator('#save-commute').click()
        page.locator('#destination').select_option('18391')
        page.locator('#load-commute').click()
        page.wait_for_function("document.getElementById('destination').value === '18387' && !document.getElementById('run').disabled")
        page.locator('#incident-kind').select_option('event')
        assert 'attendance' in page.locator('#type-help').inner_text()
        page.locator('#incident-radius').select_option('250')
        page.locator('#run').click()
        page.wait_for_function("document.getElementById('active-incident').textContent.includes('Public event') && !document.getElementById('run').disabled")
        page.locator('#place-incident').click()
        page.locator('#map').click(position={'x':100, 'y':200})
        page.wait_for_function("!document.body.classList.contains('placing') && !document.getElementById('run').disabled")
        assert 'demo location' not in page.locator('#location-label').inner_text()
        page.locator('#demo-location').click()
        page.wait_for_function("document.getElementById('alternative-arrival').textContent === '07:31:00' && !document.getElementById('run').disabled")
        page.reload()
        page.wait_for_function('window.transitMindMapState')
        page.locator('#load-commute').click()
        assert 'Saved commute loaded' in page.locator('#commute-status').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors, errors
        print(f'{width}px: event area, map placement, demo restoration, and persistent commute passed.')
        context.close()
    browser.close()
