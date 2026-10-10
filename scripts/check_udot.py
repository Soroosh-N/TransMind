"""Check UDOT access without logging the key or request URL.

Export UDOT_API_KEY before running; raw results stay in ignored local storage.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]


def main():
    key = os.environ.get('UDOT_API_KEY')
    if not key:
        print('UDOT_API_KEY is not configured. Create an account and request a developer key at https://udottraffic.utah.gov/developers/doc')
        return 2
    query = urllib.parse.urlencode({'key': key, 'format': 'json'})
    request = urllib.request.Request('https://www.udottraffic.utah.gov/api/v2/get/event?' + query,
                                    headers={'User-Agent': 'TransitMind incident access check'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            events = json.load(response)
    except urllib.error.HTTPError as error:
        print(f'UDOT request failed with HTTP {error.code}. Key and response details withheld.')
        return 1
    except (urllib.error.URLError, TimeoutError, ValueError):
        print('UDOT request failed or returned invalid JSON. Request details withheld.')
        return 1
    if not isinstance(events, list):
        print('Unexpected UDOT response format; verify account access.')
        return 1
    boundary = json.loads((ROOT / 'data/raw/geography/salt_lake_county.geojson').read_text())
    county = shape(boundary['features'][0]['geometry'])
    selected = []
    for event in events:
        try:
            point = Point(float(event['Longitude']), float(event['Latitude']))
        except (KeyError, ValueError, TypeError):
            continue
        if county.covers(point):
            selected.append(event)
    target = ROOT / 'data/processed/udot_events.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(selected, indent=2), encoding='utf-8')
    print(f'UDOT access verified: {len(events)} statewide events, {len(selected)} county event locations.')
    print('County filtering currently uses event primary coordinates; crossing incident geometry requires additional analysis.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
