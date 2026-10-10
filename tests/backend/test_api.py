import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from scripts.verify_transit import seconds


@unittest.skipUnless(Path('data/processed/runtime.json').exists(), 'Prepare the real-feed runtime first')
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.context = TestClient(app)
        self.client = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)

    def test_real_feed_baseline_and_replacement(self):
        normal = self.client.get('/api/demo?delay_minutes=0').json()
        disrupted = self.client.get('/api/demo?delay_minutes=10').json()
        self.assertEqual(normal['baseline']['arrival'], '07:21:00')
        self.assertEqual(normal['alternative']['arrival'], '07:21:00')
        self.assertFalse(normal['scenario']['missed_transfer'])
        self.assertEqual(disrupted['alternative']['arrival'], '07:31:00')
        self.assertTrue(disrupted['scenario']['missed_transfer'])
        self.assertEqual(disrupted['scenario']['road'], 'Vine Street')
        self.assertEqual(disrupted['arrival_penalty_minutes'], 10)

    def test_every_returned_leg_matches_modified_schedule(self):
        runtime = app.state.runtime
        original = {(edge[4], edge[5]): edge for edge in runtime['connections']}
        for delay in (0, 2, 5, 10, 30):
            response = self.client.get(f'/api/demo?delay_minutes={delay}')
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            impacts = {item['trip_id']: item['first_affected_segment'] for item in payload['scenario']['impacts']}
            journey = payload['alternative']
            self.assertIsNotNone(journey)
            previous = None
            for leg in journey['legs']:
                dep, arr = seconds(leg['departure']), seconds(leg['arrival'])
                self.assertLessEqual(dep, arr)
                if previous:
                    buffer = 120 if 'trip' in leg and previous.get('trip') != leg['trip'] else 0
                    self.assertGreaterEqual(dep, seconds(previous['arrival']) + buffer)
                if 'trip' in leg:
                    edge = original[(leg['trip'], leg['index'])]
                    incident = impacts.get(leg['trip'])
                    delta = delay * 60 if incident is not None and leg['index'] >= incident else 0
                    self.assertEqual(arr, edge[1] + delta)
                    self.assertEqual(dep, edge[0] + (delta if incident is not None and leg['index'] > incident else 0))
                    self.assertEqual((leg['from'], leg['to']), (edge[2], edge[3]))
                else:
                    self.assertEqual(arr - dep, max(60, runtime['geography']['transfer']['duration_seconds']))
                previous = leg

    def test_invalid_delays_and_missing_data(self):
        for value in ('-1', '61', 'abc'):
            self.assertEqual(self.client.get(f'/api/demo?delay_minutes={value}').status_code, 422)
        app.state.runtime = None
        self.assertEqual(self.client.get('/api/demo').status_code, 503)
        self.assertEqual(self.client.get('/ready').status_code, 503)
        self.assertFalse(self.client.get('/health').json()['data_ready'])

    def test_frontend_and_health_are_served(self):
        self.assertEqual(self.client.get('/ready').status_code, 200)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('TransitMind', response.text)
        self.assertEqual(self.client.get('/assets/app.js').status_code, 200)

    def test_spatial_routes_time_filter_and_map_geometry(self):
        default = self.client.get('/api/demo').json()
        self.assertEqual(default['scenario']['affected_routes'], ['201', '45'])
        self.assertEqual(default['scenario']['affected_trip_count'], 2)
        self.assertGreater(len(default['map']['baseline_paths']), 0)
        self.assertGreater(len(default['map']['baseline_paths'][0]['coordinates']), 2)
        later = self.client.get('/api/demo?start_time=23:00').json()
        self.assertEqual(later['scenario']['affected_trip_count'], 0)
        self.assertEqual(later['alternative']['arrival'], later['baseline']['arrival'])
        eastern = self.client.get('/api/demo?direction=eastbound').json()
        self.assertNotIn('5916692', eastern['scenario']['affected_trip_ids'])
        self.assertFalse(eastern['scenario']['missed_transfer'])
        self.assertEqual(self.client.get('/api/demo?origin_id=invalid').status_code, 422)
        self.assertEqual(self.client.get('/api/demo?start_time=garbage').status_code, 422)
        self.assertEqual(self.client.get('/api/demo?direction=northbound').status_code, 422)

    def test_origin_destination_selection(self):
        options = self.client.get('/api/options').json()
        self.assertEqual(len(options['stops']), 8)
        result = self.client.get('/api/demo?destination_id=18391').json()
        self.assertEqual(result['destination'], 'Murray North Station')
        self.assertEqual(result['baseline']['arrival'], '07:17:00')
        self.assertEqual(result['alternative']['arrival'], '07:27:00')


    def test_map_selected_disruption(self):
        response = self.client.get('/api/disruption?direction=westbound&kind=event')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['alternative']['arrival'], '07:31:00')
        self.assertTrue(data['scenario']['missed_transfer'])
        self.assertEqual(data['scenario']['source'], 'User simulation')
        self.assertEqual(data['map']['incident_radius_meters'], 20)
        away = self.client.get('/api/disruption?longitude=-112.2&latitude=40.8').json()
        self.assertEqual(away['scenario']['affected_trip_count'], 0)
        self.assertEqual(away['alternative']['arrival'], away['baseline']['arrival'])
        self.assertEqual(self.client.get('/api/disruption?radius=9999').status_code, 422)
        self.assertEqual(self.client.get('/api/disruption?kind=fake').status_code, 422)
