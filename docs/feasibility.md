# Initial transit feasibility result

Run the standard-library prototype from the repository root:

```powershell
python scripts/verify_transit.py --date 2026-10-09
python -m unittest discover -s tests/backend -v
```

The first command downloads the complete UTA feed to `data/raw/gtfs/UTA.zip`
if it is absent. Subsequent runs reuse that snapshot. It writes an audit and
computed journey details to `data/processed/feasibility.json`. Both artifacts
are ignored by Git. Use a date covered by the downloaded feed; the demonstration
below intentionally uses Friday, October 9, 2026, rather than the current date.

## Dataset audit

Source: https://apps.rideuta.com/tms/gtfs/Static

Feed version: `2026 AUG_20261001`, covering August 16–December 5, 2026.

Snapshot SHA-256: `1a1d384ac3f9b539ed3b421a63f36cbe939d6507252a140e807eadd6785d0972`

The snapshot contains 5,425 stops, 86 routes, 11,078 trips, and 466,904
stop-time records. Checks found no duplicate primary identifiers, invalid
stop coordinates, broken trip/route/service/shape references, invalid
stop-time references, duplicate stop sequences, or non-monotonic trip times.
Calendar exceptions are applied when selecting active trips.

This is an initial structural audit, not comprehensive GTFS certification.
The full feed remains intact, including trips outside Salt Lake County.
County-wide boundary filtering has not yet been implemented.

## Computed demonstration

Origin: Vine St / Poplar St (WB), stop `14295`.

Destination: Millcreek Station, stop `18387`.

| Event | Normal journey | Simulated disruption |
| --- | --- | --- |
| Route 45 boarding | 7:02:34 AM | 7:02:34 AM |
| Murray Central bus arrival | 7:08 AM | 7:18 AM |
| Original Blue Line 701 departure | 7:15 AM, caught | 7:15 AM, missed |
| Selected train | Blue Line 701 at 7:15 AM | Red Line 703 at 7:25 AM |
| Millcreek arrival | 7:21 AM | 7:31 AM |

The connection-scan prototype calculates both journeys from the feed.
The results are not hardcoded. The simulated delay is ten minutes on the
segment from stop `14295` to `14296` of bus trip `5916692`, persisting at
downstream stops of that trip. Other trips remain unchanged.

## Assumptions and remaining work

- Only buses and light rail are included in this routing prototype.
- Station walking links are limited to Murray Central stops within 200 meters.
  Durations use straight-line distance at 1.2 meters/second, with a minimum
  of 60 seconds, plus a 120-second boarding buffer for transfers.
- Those walking links need physical-path and accessibility verification.
- The road disruption is currently represented as a delay on a chosen transit
  segment. Geographic road/route intersection detection is not implemented.
- The alternative is a later train connection, not a street detour.
- Vehicle-block propagation, realtime ingestion, an API, UI, and deployment
  are not implemented yet.

Next, validate the road segment and station transfer assumptions, move the
prototype into backend modules, and expose the verified scenario through an API
for early remote deployment.
