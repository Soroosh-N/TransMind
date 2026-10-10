import unittest

from scripts.validate_geography import shortest_walk


class WalkingTests(unittest.TestCase):
    def feature(self, ids, coordinates, **tags):
        return {'geometry': {'coordinates': coordinates},
                'properties': {'osm_id': 1, 'node_ids': ids, 'highway': 'footway', **tags}}

    def test_connected_node_path_has_measured_length(self):
        coords = [[-111.9, 40.66], [-111.8999, 40.66], [-111.8998, 40.66]]
        result = shortest_walk([self.feature([1, 2, 3], coords)], coords[0], coords[-1])
        self.assertGreater(result['length_meters'], 16)
        self.assertLess(result['length_meters'], 18)

    def test_crossing_geometry_without_shared_node_is_not_connected(self):
        a = [[-111.9, 40.66], [-111.8998, 40.66]]
        b = [[-111.8999, 40.6599], [-111.8999, 40.6601]]
        with self.assertRaisesRegex(ValueError, 'No mapped pedestrian path'):
            shortest_walk([self.feature([1, 2], a), self.feature([3, 4], b)], a[0], b[-1])

    def test_private_path_is_excluded(self):
        coords = [[-111.9, 40.66], [-111.8998, 40.66]]
        with self.assertRaises(ValueError):
            shortest_walk([self.feature([1, 2], coords, access='private')], *coords)
