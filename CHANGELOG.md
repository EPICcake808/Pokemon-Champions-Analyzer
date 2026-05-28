# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, with release sections grouped by what changed for the analyzer, API, and web app.

## [Unreleased]

## [0.2.0] - 2026-05-28

### Added

- Auth.js plus Neon-backed saved-team support in the web app, including native username/password auth and optional Google OAuth.
- Runtime meta snapshot publishing and scheduled refresh support so the hosted site can automatically update its tracked meta teams and common meta Pokemon list from a curated feed.
- Contextual reason output for matchup scoring, including broad matchup detail reasons and tournament-row reason snippets.
- This changelog as the release history source of truth.

### Changed

- Reweighted matchup scoring around the live Regulation M-A field, including a stronger tournament-result weighting layer.
- Deepened matchup scoring so broad archetype and tournament-row predictions consider real shell context such as stats, speed profile, move effects, support density, setup pressure, weather answers, coverage gaps, and mindgame pressure.
- Improved default and alternate team-preview plans so preview guidance is more coherent and matchup-aware.
- Repaired team-preview planning so default and alternate plans are less repetitive and better match the intended game plan.
- Updated the root README so the current deployment, auth, meta-refresh, and release story matches the shipped project.

### Fixed

- Fixed several legality edge cases around Champions species and form handling.
- Fixed sprite and form alias issues in the web UI, including the missing Hisuian Arcanine sprite.
- Fixed preview selection and rendering issues that could surface awkward or repetitive plans.

## [0.1.0]

### Added

- Initial split Vercel deployment shape: FastAPI analyzer API at the repository root and a separate Next.js frontend under `web/`.
- Hosted analyzer and frontend deployment documentation for the two-project Vercel setup.
- Root Docker runtime that can build and serve the analyzer and frontend together.