# Street maps and route overlays

The passenger workspace uses locally vendored Leaflet 1.9.4, with its BSD license
in `frontend/public/vendor/leaflet/LICENSE`. The library source is distributed
from the pinned Leaflet package; map controls and assets do not depend on a CDN
at runtime.

The default basemap is the standard OpenStreetMap street tile layer. The app
requests tiles for the user's viewport only, shows attribution, and uses normal
browser caching. It does not bulk-download or archive standard OSM tiles.
Review the [tile policy](https://operations.osmfoundation.org/policies/tiles/)
before expanding usage beyond this small demo.

`map-context.geojson` is an independently downloaded OSM-derived road dataset,
not a tile archive. It is clipped and simplified around the demonstration
corridor and is distributed separately under ODbL 1.0, with attribution to
OpenStreetMap contributors. Its provenance is the Utah Geofabrik snapshot in
`geography-manifest.json`. Regenerate it with:

```powershell
.\.venv\Scripts\python scripts/export_map_context.py
```

The layer contains 8,575 OSM ways. It can be enabled in the layer control, and is
shown automatically if online tiles fail. Offline street coverage is limited
to the demo corridor; online map tiles provide broader viewing context.

Route overlays follow actual GTFS shape coordinates. Blue shows the normal
journey, dashed green the replacement, orange the shapes of routes containing
affected trips, and purple the mapped station walk. Orange whole-route context
is not a claim that every segment is delayed. Delays apply only downstream of
the incident on the identified trips. Stops and the incident have clickable
popups; the map supports pan, zoom, layer toggles, and fit-to-journey.

## Verification

Seventeen backend tests pass. Isolated Edge browser checks pass on 1440px desktop
and 390px mobile viewports: street tiles load, route overlays render, no page
overflow occurs, reset and direction controls work, and selectable destinations
recompute arrivals. With online tiles deliberately blocked, local roads and
journey calculations remain functional. This is mobile viewport verification,
not a physical-device or Safari test.

Install browser-test dependencies with `requirements-dev.txt`; with the local
server running, execute `python tests/frontend/verify_map.py --url <server-url>`.
The test uses an existing Edge installation in an isolated context and writes
ignored screenshots under `data/processed/browser-qa/`.
