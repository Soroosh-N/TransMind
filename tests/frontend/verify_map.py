"""Browser QA using an isolated existing Microsoft Edge installation."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8001')
args = parser.parse_args()
output = Path('data/processed/browser-qa')
output.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    for label, viewport in [('desktop', {'width': 1440, 'height': 1000}), ('mobile', {'width': 390, 'height': 844})]:
        context = browser.new_context(viewport=viewport, is_mobile=label == 'mobile', has_touch=label == 'mobile')
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='domcontentloaded')
        page.wait_for_function('window.transitMindMapState && window.transitMindMapState.normalPaths > 0', timeout=30000)
        page.locator('#map').scroll_into_view_if_needed()
        try:
            page.wait_for_function("Array.from(document.querySelectorAll('.leaflet-tile')).some(tile => tile.complete && tile.naturalWidth > 0)", timeout=15000)
            online_tiles = True
        except Exception:
            online_tiles = False
        page.screenshot(path=str(output / f'{label}.png'), full_page=True)
        assert page.locator('#normal-arrival').inner_text() == '07:21:00'
        assert page.locator('#alternative-arrival').inner_text() == '07:31:00'
        assert '2 affected trips' in page.locator('#impact-list').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal page overflow'
        page.locator('#reset').click()
        page.wait_for_function("document.getElementById('alternative-arrival').textContent === '07:21:00'")
        assert '0 affected trips' in page.locator('#impact-list').inner_text()
        page.locator('#delay').fill('10')
        page.locator('#direction').select_option('eastbound')
        page.locator('#run').click()
        page.wait_for_function("document.getElementById('alternative-arrival').textContent === '07:21:00' && !document.getElementById('run').disabled")
        page.locator('#direction').select_option('westbound')
        page.locator('#destination').select_option('18391')
        page.locator('#run').click()
        page.wait_for_function("document.getElementById('alternative-arrival').textContent === '07:27:00'")
        assert not errors, errors
        print(json.dumps({'viewport': label, 'online_tiles_loaded': online_tiles, 'javascript_errors': errors, 'map_state': page.evaluate('window.transitMindMapState')}))
        context.close()
    context = browser.new_context(viewport={'width': 1280, 'height': 900})
    context.route('https://tile.openstreetmap.org/**', lambda route: route.abort())
    page = context.new_page()
    page.goto(args.url)
    page.wait_for_function('window.transitMindMapState && window.transitMindMapState.normalPaths > 0', timeout=30000)
    assert page.locator('.leaflet-overlay-pane path').count() > 100, 'Local road layer missing'
    assert page.locator('#alternative-arrival').inner_text() == '07:31:00'
    page.screenshot(path=str(output / 'offline-tiles.png'), full_page=True)
    print('Blocked online tiles: local street map and journey computation passed.')
    context.close()
    browser.close()
