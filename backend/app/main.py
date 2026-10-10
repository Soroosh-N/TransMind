"""Single-service TransitMind demonstration API and frontend."""
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from scripts.verify_transit import clock, plan, seconds

ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(app):
    runtime_path = ROOT / 'data/processed/runtime.json'
    app.state.runtime = json.loads(runtime_path.read_text()) if runtime_path.exists() else None
    yield


app = FastAPI(title='TransitMind', version='0.1.0', lifespan=lifespan)
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
    return {'status': 'ready', 'service_date': app.state.runtime['audit']['service_date']}


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
        legs.append(detail)
    return {'arrival': clock(arrival), 'legs': legs}


def compute(runtime, delay_minutes):
    demo = runtime['demo']
    config = runtime['geography']
    origin, destination = demo['origin_id'], demo['destination_id']
    trip = demo['scenario']['trip_id']
    incident_index = next(leg['index'] for leg in demo['baseline']['legs'] if leg.get('trip') == trip)
    delay = delay_minutes * 60
    edges = runtime['connections']
    changed = []
    for dep, arr, a, b, tid, index, pickup, dropoff in edges:
        if tid == trip and index >= incident_index:
            dep += delay if index > incident_index else 0
            arr += delay
        changed.append((dep, arr, a, b, tid, index, pickup, dropoff))
    changed.sort()
    transfer = config['transfer']
    duration = max(60, transfer['duration_seconds'])
    paths = {config['bus_stop_id']: [(config['rail_stop_id'], duration)],
             config['rail_stop_id']: [(config['bus_stop_id'], duration)]}
    departure = seconds(demo['departure'])
    baseline = plan(edges, paths, origin, destination, departure)
    alternative = plan(changed, paths, origin, destination, departure)
    if baseline is None:
        raise ValueError('Geographically checked transfer cannot reproduce baseline journey')
    # Evaluate the actual baseline transfer selected by the runtime router.
    bus_legs = [leg for leg in baseline[1] if leg.get('trip') == trip]
    rail_legs = [leg for leg in baseline[1] if 'trip' in leg and leg['trip'] != trip]
    if not bus_legs or not rail_legs:
        raise ValueError('Baseline no longer has the expected bus-to-rail transfer')
    bus_arrival = bus_legs[-1]['arrival']
    train_departure = rail_legs[0]['departure']
    missed = bus_arrival + delay + duration + 120 > train_departure
    return {
        'service_date': runtime['audit']['service_date'], 'timezone': 'America/Denver',
        'origin': runtime['stops'][origin]['name'], 'destination': runtime['stops'][destination]['name'],
        'baseline': describe(runtime, baseline), 'alternative': describe(runtime, alternative),
        'scenario': {'simulated': True, 'delay_minutes': delay_minutes, 'affected_trip_id': trip,
                     'road': config['road']['name'], 'missed_transfer': missed,
                     'delayed_bus_arrival': clock(bus_arrival + delay),
                     'original_train_departure': clock(train_departure)},
        'arrival_penalty_minutes': (alternative[0] - baseline[0]) / 60 if alternative else None,
        'map': config['map'],
        'limitations': ['Fixed historical demo date; no live observations.',
                        'Delay affects only the selected bus trip, not every nearby route.',
                        'Road geometry matches; delay magnitude is an assumption.',
                        'Mapped pedestrian path includes unverified stop connectors; accessibility is unverified.',
                        'Only this station transfer is configured; not a general county walking planner.'],
    }


@app.get('/api/demo')
def demo(delay_minutes: int = Query(10, ge=0, le=60)):
    if app.state.runtime is None:
        raise HTTPException(503, 'Routing dataset is not prepared')
    return compute(app.state.runtime, delay_minutes)
