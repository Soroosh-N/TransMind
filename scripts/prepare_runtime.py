"""Build a compact service-day routing dataset; preserve full GTFS on disk."""
import argparse
import csv
import io
import json
import math
import sys
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_transit import connections, load, search
from backend.app.incidents.impact import spatial_match


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
    shapes = defaultdict(list)
    with zipfile.ZipFile(ROOT / 'data/raw/gtfs/UTA.zip') as archive:
        with archive.open('shapes.txt') as stream:
            for row in csv.DictReader(io.TextIOWrapper(stream, encoding='utf-8-sig')):
                shapes[row['shape_id']].append((int(row['shape_pt_sequence']), float(row['shape_pt_lon']), float(row['shape_pt_lat'])))
    shapes = {sid: [[lon, lat] for _, lon, lat in sorted(rows)] for sid, rows in shapes.items()}
    patterns, pattern_ids, trip_patterns = {}, {}, {}
    for tid, rows in times.items():
        trip = trips[tid]
        if trip['service_id'] not in active or routes[trip['route_id']]['route_type'] not in ('0', '3'):
            continue
        shape_id = trip.get('shape_id')
        if shape_id not in shapes:
            raise ValueError(f'Missing shape for active trip {tid}')
        stop_ids = tuple(row['stop_id'] for row in rows)
        key = (shape_id, stop_ids)
        if key not in pattern_ids:
            coords = shapes[shape_id]
            positions = []
            cursor = 0
            for sid in stop_ids:
                lon, lat = float(stops[sid]['stop_lon']), float(stops[sid]['stop_lat'])
                cursor = min(range(cursor, len(coords)), key=lambda i: ((coords[i][0]-lon)*math.cos(math.radians(lat)))**2 + (coords[i][1]-lat)**2)
                positions.append(cursor)
            pid = str(len(patterns))
            pattern_ids[key] = pid
            patterns[pid] = {'shape_id': shape_id, 'positions': positions}
        trip_patterns[tid] = pattern_ids[key]
    edges = connections(trips, routes, times, active)
    matches, candidates = {}, []
    for dep, arr, a, b, tid, index, pickup, dropoff in edges:
        trip = trips[tid]
        if routes[trip['route_id']]['route_type'] != '3':
            continue
        pid = trip_patterns[tid]
        key = (pid, index)
        if key not in matches:
            pattern = patterns[pid]
            first, last = pattern['positions'][index:index+2]
            coords = shapes[pattern['shape_id']][first:last+1]
            matches[key] = spatial_match(coords, scenario['road']['incident_center'])
        match = matches[key]
        if match:
            candidates.append({**match, 'trip_id': tid, 'index': index, 'departure': dep, 'arrival': arr,
                               'route_id': trip['route_id'], 'from': a, 'to': b})
    runtime = {
        'audit': audit, 'demo': demo, 'geography': scenario,
        'stops': {sid: {'name': row['stop_name'], 'lon': float(row['stop_lon']), 'lat': float(row['stop_lat'])}
                  for sid, row in stops.items()},
        'routes': {rid: {'short_name': row['route_short_name'], 'name': row['route_long_name'], 'type': row['route_type']}
                   for rid, row in routes.items()},
        'trips': {tid: {'route_id': row['route_id'], 'pattern_id': trip_patterns.get(tid)} for tid, row in trips.items()},
        'connections': edges, 'shapes': shapes, 'patterns': patterns, 'incident_candidates': candidates,
    }
    output = ROOT / 'data/processed/runtime.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(runtime, separators=(',', ':')), encoding='utf-8')
    print(f'Prepared {len(runtime["connections"])} bus/light-rail connections for {args.date}; {output.stat().st_size:,} bytes.')
    print(f'{len(candidates)} scheduled bus crossings spatially match the configured Vine Street incident corridor.')


if __name__ == '__main__':
    main()
