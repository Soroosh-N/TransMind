"""Single-service TransitMind demonstration API and frontend."""
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from scripts.verify_transit import clock, plan, seconds
from backend.app.incidents.impact import apply_delays, detect_impacts

ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(app):
    runtime_path = ROOT / 'data/processed/runtime.json'
    app.state.runtime = json.loads(runtime_path.read_text()) if runtime_path.exists() else None
    yield


app = FastAPI(title='TransitMind', version='0.2.0', lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.mount('/assets', StaticFiles(directory=ROOT / 'frontend/public'), name='assets')


@app.get('/')
def index():
    return FileResponse(ROOT / 'frontend/public/index.html')


@app.get('/health')
def health():
    return {'status': 'ok', 'data_ready': app.state.runtime is not None}


@app.get('/ready')
def ready():
    if app.state.runtime is None:
        raise HTTPException(503, 'Run scripts/prepare_runtime.py before serving journeys')
    return {'status': 'ready', 'version': '0.2.0', 'service_date': app.state.runtime['audit']['service_date']}


def describe(runtime, result):
    if result is None:
        return None
    arrival, path = result
    legs = []
    for leg in path:
        detail = {**leg, 'departure': clock(leg['departure']), 'arrival': clock(leg['arrival']),
                  'from_name': runtime['stops'][leg['from']]['name'],
                  'to_name': runtime['stops'][leg['to']]['name']}
        if 'trip' in leg:
            detail['route'] = runtime['routes'][runtime['trips'][leg['trip']]['route_id']]['short_name']
            pattern = runtime['patterns'][runtime['trips'][leg['trip']]['pattern_id']]
            first, last = pattern['positions'][leg['index']:leg['index']+2]
            detail['coordinates'] = runtime['shapes'][pattern['shape_id']][first:last+1]
        legs.append(detail)
    return {'arrival': clock(arrival), 'legs': legs}


def compute(runtime, delay_minutes, start_time='07:00:00', duration_minutes=20,
            direction='westbound', origin_id=None, destination_id=None, departure_time=None):
    demo = runtime['demo']
    config = runtime['geography']
    origin, destination = origin_id or demo['origin_id'], destination_id or demo['destination_id']
    permitted = {stop['id'] for stop in config['map']['stops']}
    if origin not in permitted or destination not in permitted:
        raise HTTPException(422, 'Choose a stop from the verified Salt Lake County demonstration corridor')
    delay = delay_minutes * 60
    edges = runtime['connections']
    try:
        start = seconds(start_time if start_time.count(':') == 2 else start_time + ':00')
        departure_value = departure_time or demo['departure']
        departure = seconds(departure_value if departure_value.count(':') == 2 else departure_value + ':00')
    except (ValueError, TypeError):
        raise HTTPException(422, 'Use a valid service-day time in HH:MM or HH:MM:SS format')
    impacts = detect_impacts(runtime, start, start + duration_minutes * 60, direction) if delay else {}
    changed = apply_delays(edges, impacts, delay)
    transfer = config['transfer']
    duration = max(60, transfer['duration_seconds'])
    paths = {config['bus_stop_id']: [(config['rail_stop_id'], duration)],
             config['rail_stop_id']: [(config['bus_stop_id'], duration)]}
    baseline = plan(edges, paths, origin, destination, departure)
    alternative = plan(changed, paths, origin, destination, departure)
    missed = False
    bus_arrival = train_departure = None
    transfers = []
    path = baseline[1] if baseline else []
    for i, leg in enumerate(path):
        if leg.get('trip') not in impacts or leg['index'] < impacts[leg['trip']]['index']:
            continue
        if i + 1 < len(path) and path[i+1].get('trip') == leg['trip']:
            continue
        next_ride = next((item for item in path[i+1:] if 'trip' in item), None)
        if next_ride is None:
            continue
        next_index = next(j for j in range(i+1, len(path)) if 'trip' in path[j])
        walking = sum(item['arrival'] - item['departure'] for item in path[i+1:next_index] if 'walk' in item)
        target_delay = delay if next_ride['trip'] in impacts and next_ride['index'] > impacts[next_ride['trip']]['index'] else 0
        broken = leg['arrival'] + delay + walking + 120 > next_ride['departure'] + target_delay
        transfers.append({'from_trip': leg['trip'], 'to_trip': next_ride['trip'], 'missed': broken})
        if broken:
            missed = True
            bus_arrival, train_departure = leg['arrival'] + delay, next_ride['departure'] + target_delay
    baseline_description, alternative_description = describe(runtime, baseline), describe(runtime, alternative)
    def paths(journey):
        return [{'coordinates': leg['coordinates'], 'route': leg['route']} for leg in (journey or {}).get('legs', []) if 'trip' in leg and len(leg['coordinates']) >= 2]
    affected_shapes = list(dict.fromkeys(runtime['patterns'][runtime['trips'][tid]['pattern_id']]['shape_id'] for tid in impacts))
    map_data = {**config['map'], 'baseline_paths': paths(baseline_description), 'alternative_paths': paths(alternative_description),
                'affected_paths': [runtime['shapes'][sid] for sid in affected_shapes],
                'incident_radius_meters': 20}
    return {
        'service_date': runtime['audit']['service_date'], 'timezone': 'America/Denver',
        'origin': runtime['stops'][origin]['name'], 'destination': runtime['stops'][destination]['name'],
        'baseline': baseline_description, 'alternative': alternative_description,
        'scenario': {'simulated': True, 'delay_minutes': delay_minutes,
                     'affected_trip_ids': sorted(impacts), 'affected_trip_count': len(impacts),
                     'affected_routes': sorted({runtime['routes'][v['route_id']]['short_name'] for v in impacts.values()}),
                     'start_time': clock(start), 'duration_minutes': duration_minutes, 'direction': direction,
                     'impacts': [{'trip_id': tid, 'first_affected_segment': item['index'],
                                 'encounter_time': clock(item['encounter_seconds']), 'direction': item['direction']}
                                for tid, item in sorted(impacts.items())],
                     'road': config['road']['name'], 'missed_transfer': missed,
                     'delayed_bus_arrival': clock(bus_arrival) if bus_arrival is not None else None,
                     'original_train_departure': clock(train_departure) if train_departure is not None else None},
        'arrival_penalty_minutes': (alternative[0] - baseline[0]) / 60 if alternative and baseline else None,
        'transfers': transfers, 'map': map_data,
        'limitations': ['Fixed historical demo date; no live observations.',
                        'Bus shapes must cross the 20m corridor in the selected direction and time window.',
                        'Crossing times are interpolated from stop schedules; delay magnitude is an assumption.',
                        'No vehicle-block propagation or recursive congestion model.',
                        'Mapped pedestrian path includes unverified stop connectors; accessibility is unverified.',
                        'Only this station transfer is configured; not a general county walking planner.'],
    }


@app.get('/api/demo')
def demo(delay_minutes: int = Query(10, ge=0, le=60), start_time: str = '07:00:00',
         duration_minutes: int = Query(20, ge=1, le=180),
         direction: str = Query('westbound', pattern='^(westbound|eastbound|both)$'),
         origin_id: str | None = None, destination_id: str | None = None, departure_time: str | None = None):
    if app.state.runtime is None:
        raise HTTPException(503, 'Routing dataset is not prepared')
    return compute(app.state.runtime, delay_minutes, start_time, duration_minutes, direction,
                   origin_id, destination_id, departure_time)


@app.get('/api/options')
def options():
    if app.state.runtime is None:
        raise HTTPException(503, 'Routing dataset is not prepared')
    runtime = app.state.runtime
    return {'stops': runtime['geography']['map']['stops'], 'origin_id': runtime['demo']['origin_id'],
            'destination_id': runtime['demo']['destination_id'], 'service_date': runtime['audit']['service_date']}
