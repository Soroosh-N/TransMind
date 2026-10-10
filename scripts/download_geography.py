"""Download the authoritative county boundary and Utah OSM extract.

Raw datasets remain local; provenance and download code are versioned.
"""
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/geography'
LAYER = 'https://services1.arcgis.com/99lidPhWCzftIe9K/arcgis/rest/services/UtahCountyBoundaries/FeatureServer/0'
OSM = 'https://download.geofabrik.de/north-america/us/utah-latest.osm.pbf'


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        request = urllib.request.Request(url, headers={'User-Agent': 'TransitMind data preparation'})
        temporary = path.with_suffix(path.suffix + '.part')
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temporary.replace(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return {'url': url, 'file': path.relative_to(ROOT).as_posix(),
            'bytes': path.stat().st_size, 'sha256': digest.hexdigest(),
            'local_file_modified_utc': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}


def main():
    query = urllib.parse.urlencode({'where': "NAME='SALT LAKE'", 'outFields': '*',
                                   'outSR': '4326', 'f': 'geojson'})
    boundary_path = RAW / 'salt_lake_county.geojson'
    boundary = download(LAYER + '/query?' + query, boundary_path)
    collection = json.loads(boundary_path.read_text(encoding='utf-8'))
    if len(collection.get('features', [])) != 1:
        raise ValueError('Expected exactly one Salt Lake County polygon')
    print('County boundary downloaded and validated.', flush=True)
    osm = download(OSM, RAW / 'utah.osm.pbf')
    manifest = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                'county_boundary': {**boundary, 'attribution': 'Utah Geospatial Resource Center',
                                    'license': 'CC BY 4.0', 'item': '90431cac2f9f49f4bcf1505419583753'},
                'osm': {**osm, 'attribution': 'OpenStreetMap contributors; extract by Geofabrik',
                        'license': 'ODbL 1.0', 'license_url': 'https://www.openstreetmap.org/copyright'},
                'strategy': 'Preserve full UTA GTFS. Select OSM ways intersecting the county without trimming their geometry.'}
    target = ROOT / 'docs/geography-manifest.json'
    target.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
