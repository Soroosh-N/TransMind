# TransitMind

TransitMind is a planned urban mobility intelligence platform for Salt Lake City, Utah, developed for the Ensign BUILD 2026 Hackathon. It aims to help public transit passengers understand how a transportation disruption affects their journey and find a practical alternative.

**The central question:** When a disruption occurs, which passengers and connections will be affected, and what should they do instead?

## Project status

The project is in an early feasibility stage. A Python prototype downloads and audits the full UTA GTFS feed, computes a real bus-to-TRAX journey in Salt Lake County, and finds a replacement connection after a simulated delay. See [the feasibility result](docs/feasibility.md) for the measured outcome and modeling limitations. The API, website, geographic incident detection, and deployment have not yet been implemented. The capabilities below describe the intended MVP.

## The demonstration

The core demonstration will follow one repeatable workflow:

**Simulated incident → affected routes → estimated delays → missed transfers → alternative journey → passenger alert**

1. Plan a normal journey using real Utah Transit Authority (UTA) route and schedule data.
2. Activate a predefined, clearly labeled simulated road disruption.
3. Identify the transit trips and downstream stops affected by the scenario.
4. Estimate updated arrival times and identify connections that become infeasible.
5. Recalculate a feasible alternative journey.
6. Compare the normal journey, the disrupted journey, and the recommended alternative.
7. Display an in-app alert for a passenger's selected commute.

The demonstration should work on both laptops and smartphones, including when external data services are unavailable.

## MVP scope

- Import real UTA GTFS static data.
- Build a schedule-aware transit network and calculate journeys.
- Display routes, stops, journeys, and incidents on an interactive map.
- Model a reproducible incident with explicit delay assumptions.
- Detect affected trips, propagate downstream delays, and evaluate transfers.
- Compare arrival times, waiting, walking, and transfers across journey options.
- Provide a responsive interface through a publicly accessible HTTPS deployment.

Live feeds, machine learning, PWA installation, browser push notifications, and native mobile apps are optional follow-up work. They should not delay the working end-to-end demonstration.

## Planned architecture

TransitMind will use a client-server architecture. The backend will perform transit routing and incident calculations; the frontend will present the results and support passenger interaction.

| Layer | Proposed approach |
| --- | --- |
| Backend | Python and FastAPI, exposing a REST API |
| Transit processing | GTFS parsing and a schedule-aware routing algorithm |
| Incident analysis | Geometric intersection analysis, with Shapely where useful |
| Delay model | Deterministic, explainable downstream delay propagation |
| Frontend | React or lightweight JavaScript, with responsive HTML and CSS |
| Map | MapLibre GL JS |
| Hosting | Prefer one deployable application serving the frontend and API |

The frontend framework, routing implementation, dependencies, and hosting provider remain to be selected. Development will take place locally on Windows, with deployment to a remote server available to judges on different networks.

## Data and modeling principles

UTA GTFS static data is the intended foundation for routes, stops, trips, schedules, and route shapes. UTA realtime feeds, UDOT incident data, and OpenStreetMap information may be added after their availability and access requirements are verified.

- Retain a local data snapshot so the core demonstration does not depend on live APIs.
- Distinguish published schedules, live observations, simulated incidents, and modeled outcomes in the interface.
- Use route geometry, travel direction, and trip timing to determine impact. Geographic proximity alone is insufficient evidence that a trip is delayed.
- State delay and transfer assumptions explicitly; do not invent statistical confidence or claim scientific validation.
- Use environment variables for credentials and keep private keys out of the frontend and repository.

## Directory structure

```text
TransMind/
├── backend/
│   └── app/
│       ├── api/          # REST endpoints and request/response handling
│       ├── transit/      # GTFS loading and transit network representation
│       ├── incidents/    # Incident impact analysis and delay propagation
│       ├── journeys/     # Routing, transfer checks, and journey comparisons
│       └── alerts/       # Selected-commute impact and in-app alerts
├── frontend/
│   ├── public/           # Public static assets
│   └── src/
│       ├── api/          # Backend API client
│       ├── components/   # Map, planner, journey panels, and controls
│       └── styles/       # Shared styles and responsive layouts
├── data/
│   ├── raw/
│   │   └── gtfs/         # Original transit feed snapshots
│   ├── processed/        # Prepared network data and derived artifacts
│   └── scenarios/        # Reproducible simulated incident definitions
├── scripts/              # Data preparation and development utilities
├── tests/
│   ├── backend/          # Routing and incident-model verification
│   └── frontend/         # UI and API integration verification
├── deploy/               # Server and deployment configuration
└── docs/                 # Architecture, assumptions, and demo notes
```

Several folders are placeholders. Git will track empty folders once files are added.

## Development milestones

1. Verify GTFS access and load a real transit feed.
2. Calculate and verify a scheduled journey.
3. Display that journey on the map.
4. Introduce a deterministic incident and recompute the journey.
5. Show affected routes, delays, missed connections, and an alternative.
6. Deploy an early working version to a public HTTPS URL.
7. Verify the demonstration on laptop and smartphone browsers.
8. Add commute alerts and improve visual clarity and robustness.

Deployment should happen early and be updated incrementally. The complete demonstration takes priority over optional features.

## Running the project

With Python 3.10 or later, run the feasibility prototype from the repository root:

```powershell
python scripts/verify_transit.py --date 2026-10-09
python -m unittest discover -s tests/backend -v
```

It uses only the Python standard library. The first run requires internet access to download the GTFS snapshot; later runs reuse it. The service date is a fixed demonstration date. The full feed is preserved; county-wide boundary filtering is not yet implemented.

There are no runnable web services yet. Server setup, environment variables, API documentation, and the public demo URL will be added as implementation is completed and verified.

## Hackathon and open-source intent

The project is intended to have publicly available source code. Development must follow the competition's rules, including its development window and disclosure of AI assistance. This repository's initial setup and documentation have been assisted by OpenAI Codex.

No open-source license has been selected yet. A license should be added before the project is presented as licensed open-source software.
