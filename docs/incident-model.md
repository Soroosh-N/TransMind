# Geographic incident model

The scenario is a simulated westbound disruption on Vine Street, centered at
longitude -111.8912398, latitude 40.6643417, with a 20-meter matching radius.
It starts at 7:00 AM on the fixed GTFS service date, October 9, 2026, and lasts
20 minutes by default. The assumed delay is ten minutes.

## Selecting affected trips

1. Preserve the complete UTA feed and apply service calendars and exceptions.
2. Read actual GTFS route shapes. Associate each stop with a nondecreasing
   shape vertex index for its trip pattern; no straight stop-to-stop lines are
   used for the displayed transit paths. Stop-to-shape mapping is approximate,
   particularly for looping routes and sparse shape vertices.
3. Test bus shape segments against the incident corridor in an approximate
   local metric projection centered on the Salt Lake Valley. Exclude rail.
4. Use the shape tangent near the crossing to classify eastbound/westbound
   travel. Reject perpendicular crossings with more than 45 degrees deviation.
5. Interpolate encounter time from that segment's scheduled departure/arrival.
   Require encounter time in [incident start, incident end).
6. Apply the assumed delay once per affected trip, at the first matching
   segment, and preserve it at downstream stops. Earlier segments stay intact.
7. Recompute journeys against the changed schedule, including walking and
   boarding buffers, and evaluate the original transfer.

The default scenario selects two scheduled trips: Route 45 at approximately
7:03:10 AM and Route 201 at 7:16:07 AM. The normal Millcreek arrival remains
7:21 AM; the replacement arrives at 7:31 AM. Neither trip identifier is used
as the spatial selection criterion.

Direction, start time, duration, and assumed delay are configurable through
`/api/demo`. Eastbound and out-of-window scenarios exclude the westbound
Route 45 trip. The initial journey selector offers eight geographically checked
stops in the Murray Central/Millcreek corridor. This is not yet an unrestricted
county-wide journey planner.

## Limits

Spatial matching and interpolated schedules provide scenario eligibility,
not proof of an observed delay. The model does not account for detours,
vehicle blocks, congestion feedback, multiple incidents, or delay-driven
changes to the incident encounter times of other trips. The road location is
currently the configured Vine Street scenario; arbitrary map incident placement
and more general direction handling remain future work. UDOT is not required.
