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
- Featured examples are loaded from the parent `examples/` directory.
- The current UI defaults to `champions_regulation_m_a`, but the request payload already accepts arbitrary regulation ids for future Champions sets.
- Available regulations are loaded from the analyzer API, so the frontend regulation selector follows the backend catalog instead of hardcoding the format list.
- For Vercel, deploy this `web/` folder as a Next.js project and set `POKEMON_ANALYZER_API_BASE_URL` to the companion analyzer API project URL.
- The Next config traces the parent `examples/` directory so curated example teams remain available in production builds.

## Docker

From the repository root:

```bash
docker build -t pokemon-champions-analyzer .
docker run --rm -p 3000:3000 pokemon-champions-analyzer
```

The container installs the Python package, builds the Next.js frontend, and runs both surfaces in one runtime.

