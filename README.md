# TransitMind

TransitMind is a planned urban mobility intelligence platform for Salt Lake City, Utah, developed for the Ensign BUILD 2026 Hackathon. It aims to help public transit passengers understand how a transportation disruption affects their journey and find a practical alternative.

**The central question:** When a disruption occurs, which passengers and connections will be affected, and what should they do instead?

## Project status

The project has a working local demonstration. It preserves the full UTA GTFS feed, computes a real bus-to-TRAX journey in Salt Lake County, and finds a replacement connection after a simulated delay. A FastAPI backend serves the calculations and a responsive demonstration page. County membership, the Vine Street bus segment, and mapped station walking connectivity have been checked against geographic data. Seventeen backend tests pass. Desktop and mobile browser checks verify actual street tiles, route overlays, controls, and the local-road fallback.

The initial Render deployment is live at https://transitmind-hw1r.onrender.com/. The passenger workspace now includes an interactive street map, GTFS route-shape overlays, and spatial/time incident matching for the Vine Street scenario. General incident placement, live feeds, and county-wide walking routing remain unfinished. Dedicated driver, pedestrian, cyclist, and authority panels remain planned. See [the feasibility result](docs/feasibility.md), [deployment instructions](docs/deployment.md), and [account setup](docs/accounts-and-terms.md).

## The demonstration

The core demonstration will follow one repeatable workflow:

**Simulated incident â†’ affected routes â†’ estimated delays â†’ missed transfers â†’ alternative journey â†’ passenger alert**

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
| Frontend | Current demo: lightweight JavaScript, HTML, and responsive CSS |
| Map | Leaflet street basemap with actual GTFS shapes and a local OSM road fallback |
| Hosting | Prefer one deployable application serving the frontend and API |

The initial implementation uses a custom connection-scan routing prototype, FastAPI, Shapely, and OSM processing through pyosmium. Dependency versions are in `requirements.txt`. Render is the prepared early hosting option. Development takes place locally on Windows; public deployment remains a required milestone.

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
â”œâ”€â”€ backend/
â”‚   â””â”€â”€ app/
â”‚       â”œâ”€â”€ api/          # REST endpoints and request/response handling
â”‚       â”œâ”€â”€ transit/      # GTFS loading and transit network representation
â”‚       â”œâ”€â”€ incidents/    # Incident impact analysis and delay propagation
â”‚       â”œâ”€â”€ journeys/     # Routing, transfer checks, and journey comparisons
â”‚       â””â”€â”€ alerts/       # Selected-commute impact and in-app alerts
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ public/           # Public static assets
â”‚   â””â”€â”€ src/
â”‚       â”œâ”€â”€ api/          # Backend API client
â”‚       â”œâ”€â”€ components/   # Map, planner, journey panels, and controls
â”‚       â””â”€â”€ styles/       # Shared styles and responsive layouts
â”œâ”€â”€ data/
â”‚   â”œâ”€â”€ raw/
â”‚   â”‚   â””â”€â”€ gtfs/         # Original transit feed snapshots
â”‚   â”œâ”€â”€ processed/        # Prepared network data and derived artifacts
â”‚   â””â”€â”€ scenarios/        # Reproducible simulated incident definitions
â”œâ”€â”€ scripts/              # Data preparation and development utilities
â”œâ”€â”€ tests/
â”‚   â”œâ”€â”€ backend/          # Routing and incident-model verification
â”‚   â””â”€â”€ frontend/         # UI and API integration verification
â”œâ”€â”€ deploy/               # Server and deployment configuration
â””â”€â”€ docs/                 # Architecture, assumptions, and demo notes
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

From the repository root, using Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts/prepare_runtime.py --date 2026-10-09
.\.venv\Scripts\python -m unittest discover -s tests/backend -v
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. API documentation is at `/docs`. The first preparation run requires internet access to download the GTFS snapshot; later runs reuse it. Runtime journey requests do not require external APIs. The service date is a fixed demonstration date, not a live departure time. The full feed is preserved.

See [deployment instructions](docs/deployment.md) for geographic reproduction and remote setup. The existing demo URL is https://transitmind-hw1r.onrender.com/. UDOT access is optional and requires a private developer key.

## Hackathon and open-source intent

The project is intended to have publicly available source code. Development must follow the competition's rules, including its development window and disclosure of AI assistance. This repository's initial setup and documentation have been assisted by OpenAI Codex.

No open-source license has been selected yet. A license should be added before the project is presented as licensed open-source software.

For the implemented model and mapping details, see [incident model](docs/incident-model.md) and [street maps](docs/maps.md).
