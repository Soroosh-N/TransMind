import unittest
from backend.app.incidents.impact import apply_delays, detect_impacts, spatial_match

class ImpactTests(unittest.TestCase):
    def test_geometry_direction_and_unrelated_corridor(self):
        center = [-111.8912, 40.6643]
        west = [[-111.8908, 40.6643], [-111.8916, 40.6643]]
        self.assertEqual(spatial_match(west, center)['direction'], 'westbound')
        self.assertEqual(spatial_match(list(reversed(west)), center)['direction'], 'eastbound')
        self.assertIsNone(spatial_match([[-111.88, 40.6643], [-111.879, 40.6643]], center))
        self.assertIsNone(spatial_match([[-111.8912, 40.664], [-111.8912, 40.665]], center))

    def test_window_uses_interpolated_encounter_and_direction(self):
        candidates = [dict(trip_id='west', index=2, departure=100, arrival=300, fraction=.5, direction='westbound'),
                      dict(trip_id='east', index=2, departure=100, arrival=300, fraction=.5, direction='eastbound'),
                      dict(trip_id='late', index=2, departure=400, arrival=500, fraction=.5, direction='westbound')]
        runtime = {'incident_candidates': candidates}
        self.assertEqual(set(detect_impacts(runtime, 200, 250)), {'west'})
        self.assertEqual(set(detect_impacts(runtime, 200, 250, 'both')), {'west', 'east'})
        self.assertEqual(detect_impacts(runtime, 100, 200), {})

    def test_only_downstream_segments_of_impacted_trip_change(self):
        edges = [(100, 200, 'A', 'B', 'bus', 0, True, True), (200, 300, 'B', 'C', 'bus', 1, True, True),
                 (300, 400, 'C', 'D', 'bus', 2, True, True), (200, 300, 'B', 'C', 'other', 1, True, True)]
        changed = {(e[4],e[5]): e for e in apply_delays(edges, {'bus': {'index': 1}}, 600)}
        self.assertEqual(changed[('bus',0)][:2], (100,200))
        self.assertEqual(changed[('bus',1)][:2], (200,900))
        self.assertEqual(changed[('bus',2)][:2], (900,1000))
        self.assertEqual(changed[('other',1)][:2], (200,300))
