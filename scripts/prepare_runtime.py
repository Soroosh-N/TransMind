"""Build a compact service-day routing dataset; preserve full GTFS on disk."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_transit import connections, load, search


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', type=date.fromisoformat, default=date(2026, 10, 9))
    args = parser.parse_args()
    stops, routes, trips, times, active, audit = load(args.date)
    if audit['errors']:
        raise ValueError('GTFS audit failed; inspect verify_transit.py output')
    demo = search(stops, routes, trips, times, active)
    if not demo:
        raise ValueError('No suitable transfer demonstration for this snapshot/service date')
    scenario = json.loads((ROOT / 'data/scenarios/murray_central.json').read_text())
    if demo['origin_id'] != scenario['origin_id'] or demo['destination_id'] != scenario['destination_id']:
        raise ValueError('Snapshot demo differs from geographically checked scenario; revalidate it')
    # Runtime calculations use the validated walking link, not the initial proximity links.
    runtime = {
        'audit': audit, 'demo': demo, 'geography': scenario,
        'stops': {sid: {'name': row['stop_name'], 'lon': float(row['stop_lon']), 'lat': float(row['stop_lat'])}
                  for sid, row in stops.items()},
        'routes': {rid: {'short_name': row['route_short_name'], 'name': row['route_long_name'], 'type': row['route_type']}
                   for rid, row in routes.items()},
        'trips': {tid: {'route_id': row['route_id']} for tid, row in trips.items()},
        'connections': connections(trips, routes, times, active),
    }
    output = ROOT / 'data/processed/runtime.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(runtime, separators=(',', ':')), encoding='utf-8')
    print(f'Prepared {len(runtime["connections"])} bus/light-rail connections for {args.date}; {output.stat().st_size:,} bytes.')


if __name__ == '__main__':
    main()
