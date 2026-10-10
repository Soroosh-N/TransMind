# Data acquisition and scope

## Acquired locally

- Full UTA static GTFS: `data/raw/gtfs/UTA.zip`.
- UGRC Salt Lake County boundary, EPSG:4326: `data/raw/geography/salt_lake_county.geojson`.
- Geofabrik's full Utah OpenStreetMap extract, including roads and pedestrian ways:
  `data/raw/geography/utah.osm.pbf`.

Run `python scripts/download_geography.py` to acquire the geographic sources.
Their URLs, sizes, checksums, and attribution are recorded in
[`geography-manifest.json`](geography-manifest.json).

The boundary is from UGRC's authoritative
[Utah County Boundaries layer](https://www.arcgis.com/home/item.html?id=90431cac2f9f49f4bcf1505419583753),
licensed CC BY 4.0. OSM is from the
[Geofabrik Utah extract](https://download.geofabrik.de/north-america/us/utah.html),
licensed ODbL 1.0 with attribution to OpenStreetMap contributors.

Keep the full UTA dataset and complete transit trips. Apply county membership
to map visibility, journey endpoint selection, and incident locations rather
than deleting out-of-county stops. Retain complete OSM way geometry for ways
intersecting the county to preserve boundary-crossing relationships.

Raw datasets, the local virtual environment, secrets, and generated reports
are excluded from Git. Source code and provenance documentation are committed.
Download scripts are not an immutable archive: upstream sources can change.
Compare checksums when reproducing the documented scenario.
