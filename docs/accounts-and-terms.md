# External accounts and data terms

## UDOT live incidents: user setup

1. Open [UDOT Traffic](https://udottraffic.utah.gov/).
2. Create an account and complete any email verification.
3. Sign in and open the [developer API page](https://udottraffic.utah.gov/developers/doc).
4. Request a developer key. Complete any required application information
   truthfully: TransitMind is a hackathon transit-disruption demonstration.
5. Keep the key private. Do not paste it into chat, source files, or commits.
6. For a local check, set it for the current PowerShell session:

   ```powershell
   $env:UDOT_API_KEY = Read-Host 'Enter your UDOT developer key' -MaskInput
   .\.venv\Scripts\python scripts/check_udot.py
   ```

   `-MaskInput` requires PowerShell 7. On Windows PowerShell 5.1, configure
   the variable through your preferred private credential workflow instead.
   A `.env` file is ignored, but the application does not automatically load it.

7. On the eventual host, use its private environment-variable settings.

The documented quota is ten calls per sixty seconds. A deployed integration
should poll centrally and cache results, rather than call UDOT per visitor.
The event response includes position, direction, closure information, and
sometimes polylines; it does not supply an empirically validated bus-delay model.
No account, developer key, or successful authenticated call exists yet.

The request form asks for a reason. It does not establish whether approval is
automatic, guarantee acceptance, or give a response time. Submit early and keep
the core simulation independent of approval. Suggested request text:

> I am developing TransitMind for the Ensign BUILD 2026 Hackathon, focusing on
> Salt Lake County. I would like to use UDOT traffic events, road closures, and
> incident locations to identify potentially affected UTA transit journeys.
> Data will be fetched by our backend, cached, and accessed within the documented
> rate limit. The project will credit UDOT and distinguish observed incidents
> from simulated delays. The API key will remain private.

## Hosting: user setup

1. Create a [Render](https://render.com/) account.
2. Install the Render plugin from ChatGPT's plugin directory and connect it
   to your Render account if you want deployment managed through this chat.
3. Alternatively, use Render's dashboard to connect GitHub and select
   `Soroosh-N/TransMind`. Exact build/start commands are in `docs/deployment.md`
   once the server implementation is prepared.
4. Start with free compute for an initial test. It sleeps after fifteen minutes
   of inactivity and has no persistent disk; assess a paid plan separately
   before judging if uninterrupted availability is needed.

Sources: [Render free-service limits](https://render.com/docs/free),
[Render FastAPI deployment](https://render.com/docs/deploy-fastapi).

## Data terms checked

- **UGRC boundary:** The authoritative ArcGIS item's terms explicitly identify
  CC BY 4.0. Credit Utah Geospatial Resource Center and identify modifications.
- **OpenStreetMap:** ODbL 1.0. Credit OpenStreetMap contributors, identify the
  database license, and follow applicable share-alike requirements when
  distributing a derived database. See [OSM copyright](https://www.openstreetmap.org/copyright).
- **UTA:** The current [Terms of Use](https://www.rideuta.com/About-UTA/Terms-of-Use)
  includes Open Data Portal terms but also directs developer-data use to the
  legacy developer terms. The legacy host did not resolve during this check.
  Feed access works, but the specific developer redistribution terms remain
  unverified. Keep raw GTFS out of the public repository and clarify applicable
  terms before publishing a data archive. Public API access is not a license.
- **UDOT:** Authentication and quota are verified from public documentation.
  Developer registration terms and redistribution conditions still need review
  during account setup.

This is a record of sources and unresolved terms, not a legal opinion.
