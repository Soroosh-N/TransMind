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
        affected = runtime['demo']['scenario']['trip_id']
        incident = next(leg['index'] for leg in runtime['demo']['baseline']['legs'] if leg.get('trip') == affected)
        for delay in (0, 2, 5, 10, 30):
            response = self.client.get(f'/api/demo?delay_minutes={delay}')
            self.assertEqual(response.status_code, 200)
            journey = response.json()['alternative']
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
                    delta = delay * 60 if leg['trip'] == affected and leg['index'] >= incident else 0
                    self.assertEqual(arr, edge[1] + delta)
                    self.assertEqual(dep, edge[0] + (delta if leg['index'] > incident else 0))
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
