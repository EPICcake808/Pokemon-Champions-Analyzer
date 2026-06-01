## Pokemon Champions Analyzer Web

This app is the Next.js frontend for the repository's existing Python analyzer. It renders the Champions Regulation M-A analysis output as a dark dashboard with sprite previews, custom speed graphics, matchup bars, and curated legal example teams.

The app does not reimplement team analysis in TypeScript. `src/lib/python-analyzer.ts` talks to the analyzer over HTTP when `POKEMON_ANALYZER_API_BASE_URL` is configured, and only falls back to the local Python CLI for local development.

## Requirements

- the root package installed in editable mode if you want local CLI fallback
- a local analyzer API at `http://127.0.0.1:8000` if you want to mirror the Vercel deployment shape during development
- Node.js dependencies installed inside `web/`

## Local Development

From the repository root:

```bash
python3 -m pip install -e .
python3 -m uvicorn pokemon_team_analyzer.api:app --reload
cd web
npm install
npm run dev
```

Then open `http://localhost:3000`.

To make the frontend use the HTTP analyzer service locally, set this in `web/.env.local`:

```bash
POKEMON_ANALYZER_API_BASE_URL=http://127.0.0.1:8000
```

If you launch the app through a wrapper script or from a different working directory, set `POKEMON_ANALYZER_REPO_ROOT` to the repository root. You can also set `POKEMON_ANALYZER_PYTHON` if the correct interpreter is not named `python3` for the local fallback path.

## Production Check

Use the build step to validate that the frontend and analyzer bridge resolve cleanly:

```bash
cd web
npm run build
```

## Notes

- The homepage server-renders an initial sample analysis so the UI loads populated.
- Featured examples are bundled inside `web/examples/`, so the frontend can deploy as a standalone Next.js project.
- The current UI defaults to `champions_regulation_m_a`, but the request payload already accepts arbitrary regulation ids for future Champions sets.
- Available regulations are loaded from the analyzer API, so the frontend regulation selector follows the backend catalog instead of hardcoding the format list.
- For Vercel, deploy this `web/` folder as a Next.js project and set `POKEMON_ANALYZER_API_BASE_URL` to the companion analyzer API project URL.
- If you want the hosted site to publish a runtime meta board, set `DATABASE_URL` and `CRON_SECRET`, then point the analyzer API's `POKEMON_ANALYZER_META_SNAPSHOT_URL` at `https://your-frontend-domain/api/meta-snapshot`. If `POKEMON_ANALYZER_API_BASE_URL` is already set, the refresh routes will default to `https://your-analyzer-api/api/meta-snapshot-source`. Only set `META_SNAPSHOT_SOURCE_URL` when you want to override that with a separate external curated feed.
- The hosted automatic path does not require `POKEMON_ANALYZER_ENABLE_DEEP_DISCOVERY`. The dedicated deep-refresh route enables deep discovery automatically. Only set that env var when you want to force deep discovery on the standard refresh route or during manual/local runs.
- Leave `Include files outside the root directory in the Build Step` disabled for the frontend Vercel project.

### Automated Meta Board Refresh

The frontend now includes two server routes for the hosted meta board:

- `GET /api/meta-snapshot` returns the latest published snapshot for a regulation.
- `GET /api/meta-snapshot/refresh` runs the hosted-safe base refresh from `META_SNAPSHOT_SOURCE_URL` when it is set, otherwise it falls back to `${POKEMON_ANALYZER_API_BASE_URL}/api/meta-snapshot-source`, and is intended to be called by Vercel Cron.
- `GET /api/meta-snapshot/deep-refresh` starts from the published board and runs the heavier export/article discovery pass on its own schedule.

The included `web/vercel.json` schedules both refresh routes automatically. The refresh routes are secret-protected and check `META_SNAPSHOT_REFRESH_SECRET` first, then fall back to `CRON_SECRET`.

The hosted automation is intentionally split in two. The standard refresh route keeps the smaller, reliable live-source set so the published board stays healthy on Vercel's request-path runtime budget. The dedicated deep-refresh route then handles the heavier Pokepaste/export sources and supported article-roster extraction automatically. The default feed source is still the analyzer API's built-in `/api/meta-snapshot-source` endpoint, which keeps the hosted board aligned with the current Python analyzer board without requiring a separate mirrored JSON file.

## Docker

From the repository root:

```bash
docker build -t pokemon-champions-analyzer .
docker run --rm -p 3000:3000 pokemon-champions-analyzer
```

The container installs the Python package, builds the Next.js frontend, and runs both surfaces in one runtime.

