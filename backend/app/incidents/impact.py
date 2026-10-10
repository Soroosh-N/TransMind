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


def location_candidates(runtime, center, radius, direction):
    """Match bus shape segments to a user-selected area, never rail services."""
    matches, candidates = {}, []
    for dep, arr, a, b, tid, index, pickup, dropoff in runtime['connections']:
        trip = runtime['trips'][tid]
        if runtime['routes'][trip['route_id']]['type'] != '3':
            continue
        key = (trip['pattern_id'], index)
        if key not in matches:
            pattern = runtime['patterns'][key[0]]
            first, last = pattern['positions'][index:index+2]
            coords = runtime['shapes'][pattern['shape_id']][first:last+1]
            match = None
            if len(coords) > 1:
                # Cheap bounding-box rejection before geometric projection.
                xs, ys = zip(*coords)
                if min(xs)-radius/SCALE_X <= center[0] <= max(xs)+radius/SCALE_X and min(ys)-radius/SCALE_Y <= center[1] <= max(ys)+radius/SCALE_Y:
                    line = LineString([(x*SCALE_X, y*SCALE_Y) for x,y in coords])
                    point = Point(center[0]*SCALE_X, center[1]*SCALE_Y)
                    if line.length and line.distance(point) <= radius:
                        along = line.project(point)
                        before, after = line.interpolate(max(0, along-5)), line.interpolate(min(line.length, along+5))
                        dx, dy = after.x-before.x, after.y-before.y
                        bearing = ('eastbound' if dx >= 0 else 'westbound') if abs(dx) >= abs(dy) else ('northbound' if dy >= 0 else 'southbound')
                        match = {'fraction': along/line.length, 'direction': bearing, 'distance_meters': round(line.distance(point), 2)}
            matches[key] = match
        match = matches[key]
        if match and (direction == 'both' or match['direction'] == direction):
            candidates.append({**match, 'trip_id': tid, 'index': index, 'departure': dep, 'arrival': arr, 'route_id': trip['route_id'], 'from': a, 'to': b})
    return candidates
