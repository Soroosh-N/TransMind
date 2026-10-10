"""Explainable spatial/time matching for the configured road disruption."""
import math

from shapely.geometry import LineString, Point

SCALE_X = 111320 * math.cos(math.radians(40.66))
SCALE_Y = 111320


def spatial_match(coordinates, center, radius=20):
    if len(coordinates) < 2:
        return None
    line = LineString([(lon * SCALE_X, lat * SCALE_Y) for lon, lat in coordinates])
    point = Point(center[0] * SCALE_X, center[1] * SCALE_Y)
    if not line.length or line.distance(point) > radius:
        return None
    along = line.project(point)
    before = line.interpolate(max(0, along - 5))
    after = line.interpolate(min(line.length, along + 5))
    dx, dy = after.x - before.x, after.y - before.y
    if math.hypot(dx, dy) == 0:
        return None
    # This scenario is an east-west road. Reject perpendicular crossings.
    alignment = abs(dx) / math.hypot(dx, dy)
    if alignment < math.cos(math.radians(45)):
        return None
    return {'fraction': along / line.length, 'direction': 'westbound' if dx < 0 else 'eastbound',
            'distance_meters': round(line.distance(point), 2)}


def detect_impacts(runtime, start, end, direction='westbound'):
    """Match crossing time on original schedules; use one delay per trip."""
    impacts = {}
    for candidate in runtime['incident_candidates']:
        if direction != 'both' and candidate['direction'] != direction:
            continue
        encounter = candidate['departure'] + candidate['fraction'] * (candidate['arrival'] - candidate['departure'])
        if not start <= encounter < end:
            continue
        trip = candidate['trip_id']
        if trip not in impacts or candidate['index'] < impacts[trip]['index']:
            impacts[trip] = {**candidate, 'encounter_seconds': round(encounter)}
    return impacts


def apply_delays(edges, impacts, delay_seconds):
    changed = []
    for dep, arr, a, b, trip, index, pickup, dropoff in edges:
        incident = impacts.get(trip)
        if incident and index >= incident['index']:
            dep += delay_seconds if index > incident['index'] else 0
            arr += delay_seconds
        changed.append((dep, arr, a, b, trip, index, pickup, dropoff))
    return sorted(changed)
