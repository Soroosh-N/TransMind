"""Extract county highway ways and validate demo road/transfer geometry.

Run with the project virtual environment after download_geography.py.
Mapped pedestrian connectivity is evidence, not field accessibility verification.
"""
import csv
import heapq
import io
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

import osmium
from shapely.geometry import LineString, Point, shape
from shapely import transform
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/geography'
PROCESSED = ROOT / 'data/processed'
LAT = math.radians(40.66)


def meters(lon, lat, z=None):
    return lon * 111320 * math.cos(LAT), lat * 111320


def projected(geometry):
    return transform(geometry, meters, interleaved=False)


class CountyWays(osmium.SimpleHandler):
    def __init__(self, county):
        super().__init__()
        self.county = prep(county)
        self.features = []

    def way(self, way):
        if 'highway' not in way.tags:
            return
        try:
            coordinates = [(node.lon, node.lat) for node in way.nodes]
        except osmium.InvalidLocationError:
            return
        if len(coordinates) < 2:
            return
        line = LineString(coordinates)
        if not self.county.intersects(line):
            return
        self.features.append({'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': coordinates},
                              'properties': {'osm_id': way.id, 'node_ids': [n.ref for n in way.nodes],
                                             **dict(way.tags)}})


def shortest_walk(features, start, end):
    """Route only over mapped pedestrian/service ways, using actual node IDs."""
    graph = defaultdict(list)
    nodes = {}
    allowed = {'footway', 'path', 'pedestrian', 'steps', 'service'}
    for feature in features:
        tags = feature['properties']
        if tags['highway'] not in allowed or tags.get('foot') in ('no', 'private'):
            continue
        if tags.get('access') in ('no', 'private') and tags.get('foot') not in ('yes', 'designated', 'permissive'):
            continue
        ids = tags['node_ids']
        coords = feature['geometry']['coordinates']
        for node_id, coord in zip(ids, coords):
            nodes[node_id] = coord
        for a, b, p, q in zip(ids, ids[1:], coords, coords[1:]):
            length = math.dist(meters(*p), meters(*q))
            graph[a].append((b, length, tags['osm_id']))
            graph[b].append((a, length, tags['osm_id']))
    station_nodes = {node: coord for node, coord in nodes.items()
                     if math.dist(meters(*coord), meters(*start)) < 500}
    if not station_nodes:
        raise ValueError('No mapped pedestrian nodes near the station')
    def nearest(point):
        node = min(station_nodes, key=lambda n: math.dist(meters(*station_nodes[n]), meters(*point)))
        return node, math.dist(meters(*station_nodes[node]), meters(*point))
    origin, first_connector = nearest(start)
    destination, last_connector = nearest(end)
    if max(first_connector, last_connector) > 50:
        raise ValueError('GTFS stop is more than 50m from a mapped pedestrian node')
    queue = [(0, origin)]
    distances = {origin: 0}
    previous = {}
    while queue:
        length, node = heapq.heappop(queue)
        if length != distances[node]:
            continue
        if node == destination:
            break
        for other, weight, way_id in graph[node]:
            candidate = length + weight
            if candidate < distances.get(other, math.inf):
                distances[other] = candidate
                previous[other] = (node, way_id)
                heapq.heappush(queue, (candidate, other))
    if destination not in distances:
        raise ValueError('No mapped pedestrian path connects the station stops')
    path_nodes = [destination]
    way_ids = []
    while path_nodes[-1] != origin:
        parent, way_id = previous[path_nodes[-1]]
        way_ids.append(way_id)
        path_nodes.append(parent)
    coords = [list(start)] + [nodes[node] for node in reversed(path_nodes)] + [list(end)]
    total = distances[destination] + first_connector + last_connector
    return {'length_meters': round(total, 1), 'duration_seconds': math.ceil(total / 1.2),
            'connector_distances_meters': [round(first_connector, 1), round(last_connector, 1)],
            'osm_way_ids': sorted(set(way_ids)), 'coordinates': coords,
            'status': 'mapped_path_with_unverified_stop_connectors',
            'accessibility': 'Not field-verified; this is not wheelchair routing.'}


def main():
    county_json = json.loads((RAW / 'salt_lake_county.geojson').read_text())
    county = shape(county_json['features'][0]['geometry'])
    if not county.is_valid:
        raise ValueError('Invalid county boundary')
    cached = PROCESSED / 'county_ways.geojson'
    if not cached.exists():
        handler = CountyWays(county)
        handler.apply_file(str(RAW / 'utah.osm.pbf'), locations=True, idx='flex_mem')
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps({'type': 'FeatureCollection', 'features': handler.features}), encoding='utf-8')
    features = json.loads(cached.read_text())['features']
    report = json.loads((PROCESSED / 'feasibility.json').read_text())
    demo = report['demo']
    with zipfile.ZipFile(ROOT / 'data/raw/gtfs/UTA.zip') as archive:
        def read(name):
            with archive.open(name + '.txt') as stream:
                return list(csv.DictReader(io.TextIOWrapper(stream, encoding='utf-8-sig')))
        stops = {r['stop_id']: r for r in read('stops')}
        trips = {r['trip_id']: r for r in read('trips')}
        shape_id = trips[demo['scenario']['trip_id']]['shape_id']
        rows = sorted((r for r in read('shapes') if r['shape_id'] == shape_id),
                      key=lambda r: int(r['shape_pt_sequence']))
    def stop_coord(sid):
        return float(stops[sid]['stop_lon']), float(stops[sid]['stop_lat'])
    bus_legs = [leg for leg in demo['baseline']['legs'] if leg.get('trip') == demo['scenario']['trip_id']]
    rail_legs = [leg for leg in demo['baseline']['legs'] if leg.get('route') == '701']
    walk = shortest_walk(features, stop_coord(bus_legs[-1]['to']), stop_coord(rail_legs[0]['from']))
    coords = [(float(r['shape_pt_lon']), float(r['shape_pt_lat'])) for r in rows]
    def nearest_index(point):
        return min(range(len(coords)), key=lambda i: math.dist(meters(*coords[i]), meters(*point)))
    a = nearest_index(stop_coord(demo['scenario']['segment_from']))
    b = nearest_index(stop_coord(demo['scenario']['segment_to']))
    if b <= a:
        raise ValueError('Selected stops do not follow the shape direction')
    segment = LineString(coords[a:b+1])
    midpoint = projected(segment).interpolate(0.5, normalized=True)
    motor = {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link',
             'secondary', 'secondary_link', 'tertiary', 'tertiary_link', 'residential', 'unclassified'}
    roads = [f for f in features if f['properties']['highway'] in motor]
    center_lon = midpoint.x / (111320 * math.cos(LAT))
    center_lat = midpoint.y / 111320
    # Bounding-box filter avoids projecting every road in the county.
    roads = [f for f in roads
             if min(p[0] for p in f['geometry']['coordinates']) <= center_lon + .003
             and max(p[0] for p in f['geometry']['coordinates']) >= center_lon - .003
             and min(p[1] for p in f['geometry']['coordinates']) <= center_lat + .003
             and max(p[1] for p in f['geometry']['coordinates']) >= center_lat - .003]
    nearest_road = min(roads, key=lambda f: projected(shape(f['geometry'])).distance(midpoint))
    road_distance = projected(shape(nearest_road['geometry'])).distance(midpoint)
    checked_stops = {leg[key] for leg in demo['baseline']['legs'] + demo['alternative']['legs'] for key in ('from', 'to')}
    outside = [sid for sid in sorted(checked_stops) if not county.covers(Point(stop_coord(sid)))]
    if outside or road_distance > 20:
        raise ValueError(f'County/road validation failed: outside={outside}, road_distance={road_distance}')
    validation = {
        'county_way_count': len(features), 'journey_stop_count': len(checked_stops),
        'outside_county_stop_ids': outside, 'transfer': walk,
        'road': {'osm_id': nearest_road['properties']['osm_id'],
                 'name': nearest_road['properties'].get('name'), 'distance_from_shape_midpoint_meters': round(road_distance, 2),
                 'shape_id': shape_id, 'segment_geometry': {'type': 'LineString', 'coordinates': list(segment.coords)},
                 'incident_center': [midpoint.x / (111320 * math.cos(LAT)), midpoint.y / 111320],
                 'status': 'road_and_route_geometry_match; simulated_delay_not_empirically_validated'},
    }
    (PROCESSED / 'geography_validation.json').write_text(json.dumps(validation, indent=2), encoding='utf-8')
    ordered_stops = list(dict.fromkeys(sid for leg in demo['baseline']['legs'] for sid in (leg['from'], leg['to'])))
    config = {'origin_id': demo['origin_id'], 'destination_id': demo['destination_id'],
              'bus_stop_id': bus_legs[-1]['to'], 'rail_stop_id': rail_legs[0]['from'],
              'transfer': walk, 'road': validation['road'],
              'validation': {'outside_county_stop_ids': outside, 'county_way_count': len(features)},
              'map': {'stops': [{'id': sid, 'name': stops[sid]['stop_name'],
                                'lon': stop_coord(sid)[0], 'lat': stop_coord(sid)[1]} for sid in ordered_stops],
                      'walk_coordinates': walk['coordinates'], 'incident_center': validation['road']['incident_center']},
              'attribution': {'osm': 'OpenStreetMap contributors, ODbL 1.0',
                              'county': 'Utah Geospatial Resource Center, CC BY 4.0',
                              'transit': 'Utah Transit Authority'},
              'osm_license_url': 'https://www.openstreetmap.org/copyright'}
    scenario_path = ROOT / 'data/scenarios/murray_central.json'
    scenario_path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in validation.items() if k != 'transfer'}, indent=2))
    print(json.dumps({k: v for k, v in walk.items() if k != 'coordinates'}, indent=2))


if __name__ == '__main__':
    main()
