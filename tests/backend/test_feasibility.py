import unittest

from scripts.verify_transit import connections, plan, seconds


class RoutingTests(unittest.TestCase):
    def test_after_midnight_times(self):
        self.assertEqual(seconds('25:10:00'), 90600)

    def test_delay_breaks_transfer_and_next_train_is_found(self):
        normal = [(100, 200, 'A', 'B', 'bus', 0, True, True),
                  (350, 450, 'B', 'C', 'train1', 0, True, True),
                  (900, 1000, 'B', 'C', 'train2', 0, True, True)]
        delayed = [(100, 800, 'A', 'B', 'bus', 0, True, True), *normal[1:]]
        self.assertEqual(plan(normal, {}, 'A', 'C', 0)[0], 450)
        # 800 + 120 transfer buffer misses even the 900 departure.
        self.assertIsNone(plan(delayed, {}, 'A', 'C', 0))
        delayed.append((950, 1050, 'B', 'C', 'train3', 0, True, True))
        result = plan(delayed, {}, 'A', 'C', 0)
        self.assertEqual(result[0], 1050)
        self.assertEqual(result[1][-1]['trip'], 'train3')

    def test_remaining_onboard_needs_no_transfer_buffer(self):
        edges = [(100, 200, 'A', 'B', 'bus', 0, True, False),
                 (200, 300, 'B', 'C', 'bus', 1, False, True)]
        self.assertEqual(plan(edges, {}, 'A', 'C', 0)[0], 300)
        self.assertIsNone(plan(edges, {}, 'B', 'C', 0))
        self.assertIsNone(plan(edges, {}, 'A', 'B', 0))

    def test_station_walk_and_boarding_buffer(self):
        edges = [(100, 200, 'A', 'B', 'bus', 0, True, True),
                 (370, 450, 'P', 'C', 'early', 0, True, True),
                 (380, 500, 'P', 'C', 'valid', 0, True, True)]
        result = plan(edges, {'B': [('P', 60)]}, 'A', 'C', 0)
        self.assertEqual(result[0], 500)
        self.assertTrue(result[1][1]['walk'])

    def test_delay_is_incurred_on_segment_and_persists(self):
        trips = {'bus': {'route_id': 'r', 'service_id': 's'}}
        routes = {'r': {'route_type': '3'}}
        rows = [{'stop_id': sid, '_departure': time, '_arrival': time}
                for sid, time in [('A', 100), ('B', 200), ('C', 300), ('D', 400)]]
        edges = connections(trips, routes, {'bus': rows}, {'s'}, 'bus', 1, 600)
        self.assertEqual([(e[0], e[1]) for e in edges], [(100, 200), (200, 900), (900, 1000)])


if __name__ == '__main__':
    unittest.main()
