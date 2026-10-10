"""Audit a complete UTA snapshot and search for a reproducible transfer demo.

Run: python scripts/verify_transit.py --date 2026-10-09
Uses only the Python standard library. This is a feasibility prototype.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://apps.rideuta.com/tms/gtfs/Static"
FEED = ROOT / "data/raw/gtfs/UTA.zip"


def seconds(value):
    h, m, s = map(int, value.split(":"))
    if h < 0 or not 0 <= m < 60 or not 0 <= s < 60:
        raise ValueError(f"Invalid GTFS time: {value}")
    return h * 3600 + m * 60 + s


def clock(value):
    return f"{value // 3600:02}:{value // 60 % 60:02}:{value % 60:02}"


def distance(a, b):
    lat1, lat2 = map(math.radians, (float(a['stop_lat']), float(b['stop_lat'])))
    dlat = lat2 - lat1
    dlon = math.radians(float(b['stop_lon']) - float(a['stop_lon']))
    return 6371000 * 2 * math.asin(min(1, math.sqrt(
        math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)))


def load(service_date):
    if not FEED.exists():
        FEED.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(URL, headers={'User-Agent': 'TransitMind feasibility audit'})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
        # Validate the archive before preserving it.
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            if archive.testzip() is not None:
                raise ValueError('GTFS archive integrity check failed')
        FEED.write_bytes(payload)
    with zipfile.ZipFile(FEED) as archive:
        def read(name):
            if name not in archive.namelist():
                return []
            with archive.open(name) as stream:
                return list(csv.DictReader(io.TextIOWrapper(stream, encoding='utf-8-sig')))
        tables = {name: read(name + '.txt') for name in (
            'agency', 'stops', 'routes', 'trips', 'stop_times', 'shapes',
            'calendar', 'calendar_dates', 'transfers', 'feed_info')}
    errors = []
    indexes = {}
    for table, key in [('stops', 'stop_id'), ('routes', 'route_id'), ('trips', 'trip_id')]:
        indexes[table] = {row[key]: row for row in tables[table]}
        if len(indexes[table]) != len(tables[table]):
            errors.append(f'Duplicate {key}')
    stops, routes, trips = (indexes[x] for x in ('stops', 'routes', 'trips'))
    for stop in stops.values():
        try:
            lat, lon = float(stop['stop_lat']), float(stop['stop_lon'])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                errors.append(f"Invalid coordinates: {stop['stop_id']}")
        except ValueError:
            errors.append(f"Missing coordinates: {stop['stop_id']}")
    services = {row['service_id'] for row in tables['calendar'] + tables['calendar_dates']}
    shape_ids = {row['shape_id'] for row in tables['shapes']}
    for trip in trips.values():
        if trip['route_id'] not in routes or trip['service_id'] not in services:
            errors.append(f"Invalid route/service reference: {trip['trip_id']}")
        if trip.get('shape_id') and trip['shape_id'] not in shape_ids:
            errors.append(f"Missing shape: {trip['trip_id']}")
    day = service_date.strftime('%Y%m%d')
    weekday = service_date.strftime('%A').lower()
    active = {row['service_id'] for row in tables['calendar']
              if row['start_date'] <= day <= row['end_date'] and row[weekday] == '1'}
    for row in tables['calendar_dates']:
        if row['date'] == day:
            if row['exception_type'] == '1':
                active.add(row['service_id'])
            elif row['exception_type'] == '2':
                active.discard(row['service_id'])
            else:
                errors.append('Invalid calendar exception type')
    stop_times = defaultdict(list)
    for row in tables['stop_times']:
        if row['trip_id'] not in trips or row['stop_id'] not in stops:
            errors.append('Invalid stop_times trip/stop reference')
            continue
        try:
            row['_arrival'] = seconds(row['arrival_time'])
            row['_departure'] = seconds(row['departure_time'])
            row['_sequence'] = int(row['stop_sequence'])
            stop_times[row['trip_id']].append(row)
        except ValueError:
            errors.append(f"Unusable stop time: {row['trip_id']}")
    for trip_id, rows in stop_times.items():
        rows.sort(key=lambda row: row['_sequence'])
        if len({row['_sequence'] for row in rows}) != len(rows):
            errors.append(f'Duplicate sequence: {trip_id}')
        for i, row in enumerate(rows):
            if row['_departure'] < row['_arrival'] or (i and row['_arrival'] < rows[i-1]['_departure']):
                errors.append(f'Non-monotonic schedule: {trip_id}')
    audit = {
        'source': URL, 'sha256': hashlib.sha256(FEED.read_bytes()).hexdigest(),
        'service_date': service_date.isoformat(), 'feed_info': tables['feed_info'],
        'agency_timezones': sorted({row['agency_timezone'] for row in tables['agency']}),
        'counts': {name: len(rows) for name, rows in tables.items()},
        'active_service_ids': sorted(active), 'errors': dict(Counter(errors)),
        'scope': 'Full UTA dataset preserved; demo candidates centered on Murray Central in Salt Lake County.',
    }
    return stops, routes, trips, stop_times, active, audit


def connections(trips, routes, times, active, delay_trip=None, delay_index=None, delay=0):
    result = []
    for trip_id, rows in times.items():
        trip = trips[trip_id]
        if trip['service_id'] not in active or routes[trip['route_id']]['route_type'] not in ('0', '3'):
            continue
        for i, (a, b) in enumerate(zip(rows, rows[1:])):
            affected = trip_id == delay_trip and i >= delay_index if delay_trip else False
            # Delay is incurred on the selected segment, then persists downstream.
            departure = a['_departure'] + (delay if affected and i > delay_index else 0)
            arrival = b['_arrival'] + (delay if affected else 0)
            result.append((departure, arrival, a['stop_id'], b['stop_id'], trip_id, i,
                           a.get('pickup_type', '0') != '1', b.get('drop_off_type', '0') != '1'))
    return sorted(result)


def plan(edges, footpaths, origin, destination, departure):
    """Connection scan with boarding restrictions and explicit station walks.

    Station footpaths are direct, measured assumptions; no street routing yet.
    Same-stop changes require two minutes. Remaining onboard requires no buffer.
    """
    labels = {}
    onboard = {}

    def relax(stop, arrival, path):
        if arrival >= labels.get(stop, (math.inf, None))[0]:
            return
        labels[stop] = (arrival, path)
        for other, duration in footpaths.get(stop, []):
            walk_arrival = arrival + duration
            if walk_arrival < labels.get(other, (math.inf, None))[0]:
                labels[other] = (walk_arrival, path + [{'walk': True, 'from': stop, 'to': other,
                                                     'departure': arrival, 'arrival': walk_arrival}])

    relax(origin, departure, [])
    for dep, arr, a, b, trip, index, pickup, dropoff in edges:
        if dep < departure:
            continue
        if dep > departure + 3 * 3600:
            break
        path = onboard.get(trip)
        label = labels.get(a)
        buffer = 0 if label and not label[1] else 120
        if pickup and label and label[0] + buffer <= dep:
            if path is None:
                path = label[1]
        if path is None:
            continue
        path = path + [{'trip': trip, 'from': a, 'to': b, 'departure': dep, 'arrival': arr, 'index': index}]
        onboard[trip] = path
        if dropoff:
            relax(b, arr, path)
    return labels.get(destination)


def search(stops, routes, trips, times, active):
    station = {sid for sid, row in stops.items() if 'Murray Central' in row['stop_name']}
    footpaths = {sid: [(other, max(60, math.ceil(distance(stops[sid], stops[other]) / 1.2)))
                      for other in station if sid != other and distance(stops[sid], stops[other]) <= 200]
                 for sid in station}
    edges = connections(trips, routes, times, active)
    rail_targets = set()
    for trip_id, rows in times.items():
        trip = trips[trip_id]
        if trip['service_id'] in active and routes[trip['route_id']]['route_short_name'] in ('701', '703'):
            for i, row in enumerate(rows):
                if row['stop_id'] in station:
                    rail_targets.update(r['stop_id'] for r in rows[i+2:i+5])
    candidates = []
    for trip_id, rows in times.items():
        trip = trips[trip_id]
        if trip['service_id'] not in active or routes[trip['route_id']]['route_type'] != '3':
            continue
        for i, row in enumerate(rows):
            if row['stop_id'] in station and i >= 3:
                start = rows[i-3]
                if 7 * 3600 <= start['_departure'] < 10 * 3600:
                    candidates.append((start['_departure'] - 60, start['stop_id']))
    for departure, origin in sorted(set(candidates)):
        for destination in sorted(rail_targets):
            baseline = plan(edges, footpaths, origin, destination, departure)
            if not baseline:
                continue
            rides = [leg for leg in baseline[1] if 'trip' in leg]
            trip_order = list(dict.fromkeys(leg['trip'] for leg in rides))
            if len(trip_order) != 2:
                continue
            bus, rail = trip_order
            if routes[trips[bus]['route_id']]['route_type'] != '3' or routes[trips[rail]['route_id']]['route_type'] != '0':
                continue
            bus_legs = [leg for leg in rides if leg['trip'] == bus]
            rail_legs = [leg for leg in rides if leg['trip'] == rail]
            if bus_legs[-1]['to'] not in station or rail_legs[0]['from'] not in station:
                continue
            delay = 600
            bus_arrival = bus_legs[-1]['arrival']
            rail_departure = rail_legs[0]['departure']
            if bus_arrival + delay <= rail_departure:
                continue
            incident_index = bus_legs[0]['index']
            disrupted = connections(trips, routes, times, active, bus, incident_index, delay)
            alternative = plan(disrupted, footpaths, origin, destination, departure)
            if not alternative or alternative[0] <= baseline[0]:
                continue
            def describe(result):
                arrival, path = result
                legs = []
                for leg in path:
                    detail = dict(leg)
                    detail['from_name'] = stops[leg['from']]['stop_name']
                    detail['to_name'] = stops[leg['to']]['stop_name']
                    detail['departure'] = clock(leg['departure'])
                    detail['arrival'] = clock(leg['arrival'])
                    if 'trip' in leg:
                        detail['route'] = routes[trips[leg['trip']]['route_id']]['route_short_name']
                    legs.append(detail)
                return {'arrival': clock(arrival), 'legs': legs}
            return {
                'origin': stops[origin]['stop_name'], 'origin_id': origin,
                'destination': stops[destination]['stop_name'], 'destination_id': destination,
                'departure': clock(departure), 'baseline': describe(baseline),
                'scenario': {'simulated': True, 'trip_id': bus, 'delay_seconds': delay,
                             'segment_from': bus_legs[0]['from'], 'segment_to': bus_legs[0]['to'],
                             'normal_transfer_arrival': clock(bus_arrival),
                             'delayed_transfer_arrival': clock(bus_arrival + delay),
                             'original_train_departure': clock(rail_departure)},
                'alternative': describe(alternative), 'arrival_penalty_seconds': alternative[0] - baseline[0],
                'assumptions': ['Ten-minute delay on one selected bus segment, persisting downstream.',
                                'Only the selected trip is delayed; no vehicle-block propagation.',
                                'Station walks use straight-line distances at 1.2 m/s, minimum 60 seconds.',
                                'A further 120-second boarding buffer applies to transfers.',
                                'Bus and light-rail services only; no FrontRunner or street walking network.',
                                'Road intersection and pedestrian accessibility have not been validated.'],
            }
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', type=date.fromisoformat, required=True)
    args = parser.parse_args()
    stops, routes, trips, times, active, audit = load(args.date)
    if audit['errors']:
        demo = None
    else:
        demo = search(stops, routes, trips, times, active)
    report = {'audit': audit, 'demo': demo}
    output = ROOT / 'data/processed/feasibility.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'audit': audit, 'demo_found': demo is not None,
                      'demo': demo, 'report': str(output)}, indent=2))
    if audit['errors'] or demo is None:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
