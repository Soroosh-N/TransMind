# Local run and early deployment

## Windows development

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts/prepare_runtime.py --date 2026-10-09
.\.venv\Scripts\python -m unittest discover -s tests/backend -v
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. API documentation is at `/docs`; `/ready` confirms
the routing dataset is loaded. `/health` confirms the service is running and
reports whether data is ready. The frontend and backend use the same origin.

The preparation script downloads the full UTA ZIP only if it is absent, applies
calendar exceptions, audits it, and generates compact connections for the fixed
demonstration date. It retains complete trips and does not delete out-of-county
stops. Generated runtime data is about 13 MB; the complete feed stays on disk.

## Reproduce the geographic checks

```powershell
.\.venv\Scripts\python scripts/download_geography.py
.\.venv\Scripts\python scripts/verify_transit.py --date 2026-10-09
.\.venv\Scripts\python scripts/validate_geography.py
```

OSM extraction is a one-time preparation step with considerably more time and
memory than serving the prepared demo. It is not run during deployment.
The measured scenario configuration is already in `data/scenarios/`.

## Render deployment: account action required

No remote deployment has occurred yet. The following configuration is prepared
and locally tested; successful remote operation still needs verification.

1. Create a Render account and connect GitHub.
2. Ensure these commits are pushed to `Soroosh-N/TransMind`.
3. In Render, choose **New → Blueprint**, select that repository and its `master`
   branch. The root `render.yaml` declares the web service and free plan.
4. Review the service configuration and create the service. Alternatively,
   create a Python Web Service manually with:

   - Build: `pip install -r requirements.txt && python scripts/prepare_runtime.py --date 2026-10-09`
   - Start: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - Health-check path: `/ready`
   - Repository root as the working directory.

5. Wait for the build to finish and open the returned HTTPS URL.
6. Check `/ready`, `/docs`, and `/api/demo?delay_minutes=10`.
7. Open the page on a laptop and on a smartphone using cellular data. Test
   zero-delay reset and ten-minute simulation on both devices.
8. Record the URL and test result in this document after verification.

To manage deployment through chat instead, install and connect the Render
plugin. No Render connection or provider key is currently available here.

## Availability and snapshot behavior

The first remote build needs the UTA feed. Requests during the demo do not call
UTA, UDOT, map tile servers, or a routing service: they recompute journeys from
the prepared local connections. Assets and the geographic sketch are served
locally. The sketch is not a full interactive basemap.

A newly downloaded feed may change identifiers or no longer cover the fixed
date. Preparation intentionally fails if the audited journey differs from the
geographically checked scenario; revalidate and select a new covered date.
Archive the known-good snapshot privately for reproducibility, subject to the
applicable data terms. A future fresh build is not guaranteed to reproduce the
current feed.

Render free services sleep after fifteen minutes of inactivity and have no
persistent disk. Build-generated files are part of the deployed build; do not
depend on runtime file writes surviving restarts. Paid availability is a
separate decision; no paid resources have been authorized or created.

Sources: [FastAPI deployment](https://render.com/docs/deploy-fastapi),
[free-service limits](https://render.com/docs/free).

UDOT is not required for this deployment and its key must not be embedded in
the frontend. `scripts/check_udot.py` is an access check, not a live polling
integration.
