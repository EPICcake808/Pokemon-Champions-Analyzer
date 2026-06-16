# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, with release sections grouped by what changed for the analyzer, API, and web app.

## [Unreleased]

## [0.4.1] - 2026-06-15

A correctness pass over the analyzer's generated guidance and the damage calculator, driven by an
external review. Most changes tighten or re-word heuristic outputs so they no longer overstate
mechanics or read as more precise than they are.

### Added

- A continuous-integration workflow (`.github/workflows/ci.yml`) that runs the Python test suite and the web lint, typecheck, and build on every push and pull request, plus a declared `dev` extra (`pip install -e ".[dev]"`) and pytest configuration so the suite has a single documented entry point.
- The damage engine now models the 1.2x type-boost held items (Charcoal, Mystic Water, Soft Sand, and the rest of the Regulation M-A type-enhancing items) as a base-power modifier, so legal offensive items are scored instead of being reported back as unmodeled (`pokemon_team_analyzer/damage.py`).
- Sand and snow are now selectable weather conditions in the interactive damage calculator and modeled by the engine: sand grants Rock-type defenders a 1.5x Special Defense boost and snow grants Ice-type defenders a 1.5x Defense boost (`pokemon_team_analyzer/damage.py`, `web/src/components/damage-calculator.tsx`).
- Per-section confidence labels: the analysis now emits a `confidence` tier per section (legality and role/move/item reads are high, archetype and mode detection medium, matchup and meta-board scores low) with caveat text, and the web shows a confidence badge on the score-lane and matchup sections so heuristic scores are not read as precise predictions (`pokemon_team_analyzer/models.py`, `web/src/components/analyzer-workspace.tsx`).
- Offensive coverage is now classified by reliability — hard gap, thin, centralized, or positioning-dependent, with the contributing attacker named — instead of a flat "coverage gap" list, so a type with a real super-effective answer is never reported as a hard gap (`pokemon_team_analyzer/analyzer.py`, `web/src/components/analyzer-workspace.tsx`).
- The interactive damage calculator now exposes Reflect, Light Screen, and Aurora Veil toggles (the engine already modeled screens) and discloses per-roll assumptions for variable-power and field-dependent moves (Last Respects, Weather Ball, Electro Shot, Low Kick, Heavy Slam, spread, crit, burn, screens, weather) so no variable row is shown as if it were exact (`pokemon_team_analyzer/damage.py`, `web/src/components/damage-calculator.tsx`).
- A Fairy / Mega Floette defensive-pressure warning fires when no team member resists Fairy, even when the team can hit Fairy super-effectively, since offensive Steel/Poison coverage is not a defensive switch-in (`pokemon_team_analyzer/analyzer.py`).

### Changed

- Bumped the analyzer package and web app to 0.4.1.
- Matchup explanations are split into "why you have play" and "why this is dangerous" buckets, and a clearly-negative matchup whose edge is purely the archetype clash now carries an explicit structural danger reason instead of only mitigation notes (`pokemon_team_analyzer/analyzer.py`, `web/src/components/analyzer-workspace.tsx`).
- Support-heavy / board-control teams (screens, redirection, healing, pivots) are no longer mislabeled Hyper Offense; dense support density now reads as bulky offense or balance unless the plan is genuinely fast damage (`pokemon_team_analyzer/analyzer.py`).
- Choice Scarf attackers are now classified as fast revenge killers / cleaners rather than bulky attackers, since the item is a speed investment, not defensive bulk (`pokemon_team_analyzer/analyzer.py`).
- Preview watchlists tag each meta Pokemon as a mode setter, abuser, or support piece instead of grouping them all under the mode label (`pokemon_team_analyzer/analyzer.py`).
- Meta-board rows now headline a concrete opposing anchor and a concrete team tool that answers or fails into it, instead of a generic counterplay line, and surface a per-row form breakdown for families whose forms need different prep (Mega Charizard X vs Y) (`pokemon_team_analyzer/analyzer.py`, `web/src/components/analyzer-workspace.tsx`).
- Combined team modes (for example Rain Tailwind) are presented as a primary mode with their components demoted to "subtools" rather than listed as duplicate equal labels (`web/src/components/analyzer-workspace.tsx`).

### Fixed

- Replaced the illegal Choice Band sets in the curated damage grid's "defining nukes" with Regulation M-A-legal type-boost items (Soft Sand Garchomp Earthquake and Rain Mystic Water Basculegion Wave Crash), so every benchmark in the grid is now a legal Champions build; Kingambit's already-legal Black Glasses also now correctly applies its 1.2x boost.
- Fixed the Basculegion nuke benchmark, which silently never appeared in the grid because the bare "Basculegion" name does not resolve through the data provider; it now uses the canonical "Basculegion (Male)" form.
- The damage engine now treats Rough Skin, Swift Swim, Armor Tail, Defiant, and Intimidate as having no effect on a single damage roll (recoil, weather speed, priority denial, and Attack changes that are already fed in as stat stages), so the curated grid rows no longer carry spurious "unmodeled" caveats.
- Wide Guard and Intimidate are no longer described as Trick Room counterplay; Wide Guard is scoped to spread-damage mitigation, and "Trick Room denial" now means only Taunt, Encore, Imprison, your own Trick Room, or Fake Out on the setter (`pokemon_team_analyzer/analyzer.py`).
- Redirection and healing are described as softening the first Trick Room turn rather than contesting the setup turn, which only genuine denial tools do (`pokemon_team_analyzer/analyzer.py`).
- A Tailwind counterplay tip no longer suggests Fake Out when no team member runs it (`pokemon_team_analyzer/analyzer.py`).

### Repo

- Removed the duplicate sync-artifact files (`* 2.py`, `* 3.py`, and matching test fixtures) that had been committed to the repository alongside their canonical counterparts.
- Added an MIT `LICENSE` and declared it in `pyproject.toml` and `web/package.json`.
- Added a Dependabot configuration (`.github/dependabot.yml`) that keeps the Python, npm, and GitHub Actions dependencies updated weekly.

## [0.4.0] - 2026-06-14

### Added

- Damage calculator: a standard Generation 9 damage engine (`pokemon_team_analyzer/damage.py`) fed Champions stat values, modeling STAB/Adaptability, full type effectiveness, defender type-immunity abilities, sun/rain weather, doubles spread, critical hits, stat stages, burn, screens, and the common power items/abilities (with anything unmodeled reported back rather than silently ignored). A curated OHKO/2HKO grid (`pokemon_team_analyzer/damage_benchmarks.py`) ships in every analysis as `damage_matchups` with the assumed build disclosed per row, and an interactive calculator is available via `POST /api/damage` and the web "Damage calc" section.
- Preview-trainer mode: paste an opponent's six to get a recommended bring-four and lead, justified with real speed and KO math against your roster (`pokemon_team_analyzer/preview.py`, `POST /api/preview`, and the web "Preview trainer" section).
- Usage-weighted speed coverage: for each member, the usage-weighted share of the most-used meta Pokemon it moves before at +0, under your Tailwind, and under your Trick Room (`speed_profile.coverage` and the web "Meta speed coverage" panel).
- Slot doctor: diagnoses Trick Room, Tailwind, setup, and defensive-type gaps and suggests Regulation M-A-legal move swaps and replacements, every suggestion legality-checked (`pokemon_team_analyzer/slot_doctor.py`, `POST /api/slot-doctor`, and the web "Slot doctor" section).
- Plain-language onboarding: a shared glossary and templated team summary (`pokemon_team_analyzer/glossary.py`) embedded in the analysis as `glossary` and `plain_summary`; the web adds inline term tooltips, an "In plain terms" summary, and a score-anchoring legend so unanchored numbers read clearly.
- A searchable species picker that replaces the long flat dropdown, plus one-click archetype starter templates in the team builder.
- New CLI commands `--damage-json`, `--preview-json`, and `--slot-doctor-json` mirroring the new API endpoints.

### Changed

- Extracted the type-effectiveness chart into `pokemon_team_analyzer/typechart.py`, shared by the analyzer and the damage engine so the two can never drift.
- Responsive pass across the web workspace so the new panels render cleanly on phones: wide tables scroll instead of overflowing, term tooltips reveal in-flow rather than as clipped popovers, and charts scale fluidly.
- Bumped the package version to 0.4.0.

### Fixed

- Added the mobile viewport meta (`width=device-width, initial-scale=1, viewport-fit=cover`) via a Next `viewport` export. Without it the site fell back to a ~980px desktop layout viewport on phones, so it loaded zoomed-out, was hard to navigate, and showed dark borders around the page; it now renders at 1x device width. Also added `overflow-x: clip` on `html` as a sticky-safe guard against stray horizontal overflow.
- Fixed a horizontal overflow on mobile where the new damage, speed-coverage, and preview tables widened the whole page (causing a right-side dark border and zoom-out) because their `lg:grid-cols-2` containers used an implicit auto-sized base track. The base grids are now `grid-cols-1` (`minmax(0,1fr)`) with `min-w-0` scroll wrappers, so wide tables scroll inside their own container instead of expanding the viewport.

## [0.3.1] - 2026-06-13

### Added

- Public-facing copy polish across the web workspace, including account messaging, builder guidance, and preview empty states.
- Release-ready fallback changelog text for deployments that rely on the bundled site documents.
- A single shared `compute_stat()` Champions stat formula in `pokemon_team_analyzer/stats.py`, used by both the analyzer and the speed benchmark catalog so the two layers can never drift.
- Champions base-stat overrides in `pokemon_team_analyzer/champions_m_a_stats.py` so rebalanced species (for example Alakazam and Gengar) use their Champions stat lines instead of mainline PokeAPI values.

### Changed

- Speed benchmark catalogs are now generated by calling `compute_stat()` on declared reference sets rather than hand-entered integers, so benchmark speeds always match the engine.
- Discovered shells that carry two or more mega stones are now recognized as dual-mode teams (only one mega is legal per battle): they are tagged `dual_mode` and each mega anchors its own core with its top support, instead of one mega being paired with supports while the second is dropped from the cores entirely.
- Team meta standing now combines the relative matchup scores with an absolute team-soundness term, and the grade bands were retuned, so "solid" and "strong" reflect genuine field positioning rather than being the default outcome.

### Fixed

- Fixed the Champions stat formula to apply the nature multiplier after Stat Points are added, matching the game (for example Jolly Aerodactyl with 32 Speed Stat Points is now 200, not 197); this corrects every nature-boosted invested stat and the speed comparisons that depend on them. The web builder live-stat preview was corrected to match.
- Fixed legality for genderless gender-form species given by their bare name (for example Basculegion): these now resolve to their default form instead of being rejected as ineligible.
- Fixed over-generous meta standings where structurally weak teams could grade as favorable into the field. The new absolute soundness penalty is dominated by stacked shared weaknesses (one well-picked attacker threatening most of the roster at once), so a mono-type build such as a mono-grass team now grades as a clear liability instead of "solid".
- Gated matchup and builder reason strings on the roster's actual moves, so explainers no longer cite tools the team does not run (for example Encore, Fake Out, or item control).
- Removed internal deployment copy (environment variable names and infrastructure details) from user-facing error and notice messages.

### Repo

- Stopped tracking the generated `build/` and `*.egg-info/` artifacts, removed coding-session scratch scripts and duplicate analysis dumps from the repository, and bumped the package version to 0.3.1 so deploys are traceable to the changelog.

## [0.3.0] - 2026-06-13

### Added

- An automated, usage-based meta board built from real Regulation M-A tournament results: a new `pokemon_team_analyzer/meta_ingest/` pipeline ingests grassroots (Limitless) and official (limitlessvgc.com Regionals, Internationals, Special Events, and Worlds) results, infers each team's modes and cores from its structured decklist, and a daily GitHub Action publishes the ranked board to the runtime meta-snapshot feed.
- Multi-source reconciliation that cross-checks the weighted usage (base-species normalized) against secondary sources such as Pikalytics, recording disagreements and unavailable sources in the published notes so the board never aborts on a single source being down.
- Provenance stamping on the meta board: every meta panel now carries an as-of date, source links, and a methodology note, with a visible "stale" badge in the web UI once the board ages past a threshold.

### Changed

- The meta board and common-Pokemon list are now ranked by weighted real-world usage, with official events and deeper top-cut runs counting for more than online events, replacing the previous request-path scraping with an offline ingest-and-publish pipeline.

### Removed

- Removed the legacy in-request `/api/meta-snapshot/refresh` and `/api/meta-snapshot/deep-refresh` routes and the request-path scraping module that backed them; all ingestion now runs in the scheduled GitHub Action, and the hosted app only serves (`GET /api/meta-snapshot`) and stores (`POST /api/meta-snapshot/publish`) the published board.

## [0.2.2] - 2026-06-03

### Added

- A top-navbar Changelog popup in the hosted web app.
- A top-navbar Play Guide popup in the hosted web app with a complete-beginner explanation of what VGC is, what happens before turn one, what you choose each turn, and how doubles battles are won.
- Bundled frontend fallback document content so the web app can still render the changelog and beginner guide modal content when the root changelog file is not available at runtime.
- Shared `target_summary` and `interaction_summary` payloads on each `meta_analysis.tournament_rows` entry, so board rows now expose dual-type anchor pressure plus interaction tags such as redirection counterplay, setup denial, spread counterplay, and ability-aware counterplay.
- Live-board context is now folded into the existing benchmark and team-note payloads, so the web app can surface broader matchup cues and meta-Pokemon interactions inside Benchmark notes and Team Notes instead of only inside the meta board.
- Matchup-specific preview cards in the web app now show their `recommended_into` targets directly.

### Changed

- Deepened tournament-row contextual scoring so current board teams are evaluated not just by type pressure, but also by broader interaction context like redirection support, setup branches, spread-damage shells, and key ability clauses such as Armor Tail.
- Team-preview alternate plans now attach to the best matching current board shell for the relevant mode, and their summaries can reference that concrete team instead of only the generic mode label.
- Matchup-specific preview selection and per-member reasoning now reuse the board-anchor context, so the chosen four and their explanations are more specific than the generic mode matchup alone.

### Fixed

- Fixed Champions species normalization so generic Showdown gender suffixes like `Tinkaton (F)` and `Tinkaton (M)` now resolve to the correct legal species, real gendered forms like Meowstic still keep their canonical form handling, and gender-suffixed Mega imports still upgrade to the correct Mega species.
- Fixed Palafin Hero form handling in the builder, roster, and web UI so Hero-form imports, including `Palafin (Hero Form)` and `Palafin-Hero`, load the correct Palafin stat data, restore roster stat bars, and render the Hero-form sprite.
- Fixed benchmark-note live-field wording so the added meta context now uses broader `teams with ...` style phrasing instead of explicit board shell names.

## [0.2.1] - 2026-06-01

### Added

- A dedicated hosted `GET /api/meta-snapshot/deep-refresh` route plus a second Vercel cron so deep export and article discovery now runs automatically without blocking the normal daily refresh.
- Article-roster extractors for supported guide and gallery pages, plus source-level and page-level discovery diagnostics that are written into the published snapshot notes.

### Changed

- Split automatic meta publishing into two stages: the default hosted refresh keeps the smaller, reliable source set, while the separate deep-refresh job starts from the current published board and runs the heavier discovery sources on its own schedule.
- Updated the root and web READMEs so the deployment, cron, deep-discovery, and release documentation matches the shipped automatic meta-refresh pipeline.

### Fixed

- Fixed the hosted meta refresh regression where deep discovery on the request-path refresh could push the Vercel function over its runtime budget.

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