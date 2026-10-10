"""Export a small OSM street layer around the verified demo corridor."""
import json
from pathlib import Path
from shapely.geometry import box, mapping, shape
ROOT = Path(__file__).resolve().parents[1]

def main():
    config = json.loads((ROOT / 'data/scenarios/murray_central.json').read_text())
    stops = config['map']['stops']
    bounds = box(min(s['lon'] for s in stops)-.015, min(s['lat'] for s in stops)-.01, max(s['lon'] for s in stops)+.015, max(s['lat'] for s in stops)+.01)
    source = json.loads((ROOT / 'data/processed/county_ways.geojson').read_text())
    features = []
    for feature in source['features']:
        line = shape(feature['geometry'])
        if line.intersects(bounds):
            properties = feature['properties']
            features.append({'type': 'Feature', 'geometry': mapping(line.intersection(bounds).simplify(.000003)), 'properties': {k: properties[k] for k in ('osm_id', 'name', 'highway') if k in properties}})
    target = ROOT / 'frontend/public/map-context.geojson'
    target.write_text(json.dumps({'type': 'FeatureCollection', 'attribution': 'OpenStreetMap contributors', 'license': 'ODbL 1.0', 'license_url': 'https://www.openstreetmap.org/copyright', 'features': features}, separators=(',', ':')), encoding='utf-8')
    print(f'Exported {len(features)} OSM ways, {target.stat().st_size:,} bytes; clipped for display only, not routing.')

if __name__ == '__main__':
    main()
