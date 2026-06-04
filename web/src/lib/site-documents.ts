export const BUNDLED_CHANGELOG_CONTENT = `# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, with release sections grouped by what changed for the analyzer, API, and web app.

## [Unreleased]

## [0.2.2] - 2026-06-01

### Added

- A top-navbar Changelog popup in the hosted web app.
- A top-navbar Play Guide popup in the hosted web app with a complete-beginner explanation of what VGC is, what happens before turn one, what you choose each turn, and how doubles battles are won.
- Bundled frontend fallback document content so the web app can still render the changelog and beginner guide modal content when the root changelog file is not available at runtime.
- Shared \`target_summary\` and \`interaction_summary\` payloads on each \`meta_analysis.tournament_rows\` entry, so board rows now expose dual-type anchor pressure plus interaction tags such as redirection counterplay, setup denial, spread counterplay, and ability-aware counterplay.
- Live-board context is now folded into the existing benchmark and team-note payloads, so the web app can surface broader matchup cues and meta-Pokemon interactions inside Benchmark notes and Team Notes instead of only inside the meta board.
- Matchup-specific preview cards in the web app now show their \`recommended_into\` targets directly.

### Changed

- Deepened tournament-row contextual scoring so current board teams are evaluated not just by type pressure, but also by broader interaction context like redirection support, setup branches, spread-damage shells, and key ability clauses such as Armor Tail.
- Team-preview alternate plans now attach to the best matching current board shell for the relevant mode, and their summaries can reference that concrete team instead of only the generic mode label.
- Matchup-specific preview selection and per-member reasoning now reuse the board-anchor context, so the chosen four and their explanations are more specific than the generic mode matchup alone.

## [0.2.1] - 2026-06-01

### Added

- A dedicated hosted \`GET /api/meta-snapshot/deep-refresh\` route plus a second Vercel cron so deep export and article discovery now runs automatically without blocking the normal daily refresh.
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

- Initial split Vercel deployment shape: FastAPI analyzer API at the repository root and a separate Next.js frontend under \`web/\`.
- Hosted analyzer and frontend deployment documentation for the two-project Vercel setup.
- Root Docker runtime that can build and serve the analyzer and frontend together.`;

export const PLAY_GUIDE_CONTENT = `# Beginner VGC Play Guide

If you are completely new, think of VGC as a series of short two-on-two turns. You do not send out all six Pokemon at once. You build a team of six, choose four for each match, and then try to knock out the opponent's four before they knock out yours.

## What VGC is

- VGC is official doubles Pokemon. Each player brings six Pokemon to team preview.
- Before the battle starts, each player secretly chooses four of those six to use in that game.
- The match begins with two active Pokemon on your side and two active Pokemon on the opponent's side.
- You win when all four of the opponent's chosen Pokemon faint.

## What happens before turn one

- First, look at both teams of six during team preview.
- Choose the four Pokemon you want to bring into the battle.
- Pick which two will lead, meaning which two start on the field.
- The other two stay in the back and can switch in later when a Pokemon faints or when you manually switch.

If you are brand new, your easiest starting rule is this: bring Pokemon that seem useful into the matchup, then lead with the two that can do something immediately instead of waiting around.

## What you do on every turn

Each turn, you choose one action for each of your two active Pokemon.

- Use a move.
- Switch out.
- Use Protect if that Pokemon has Protect.
- Terastallize if you want to change that Pokemon's type for the turn and the rest of the game.

After both players lock in their choices, the turn plays out automatically. Faster Pokemon usually move first, but priority moves and some field effects can change the order.

## How attacking works in doubles

- Most moves need a target. You usually choose which opposing Pokemon you want to hit.
- Some moves hit both opponents at once. These are called spread moves.
- Some moves target your partner, yourself, or the whole field instead of the opponent.
- If a Pokemon faints before it gets to move, it usually loses that action for the turn.

This matters a lot in doubles. You are not just asking which move does the most damage. You are also asking which target matters most right now.

## How switching works

- Instead of attacking, a Pokemon can switch out and be replaced by one of your two benched Pokemon.
- Switching is useful when your active Pokemon is in danger, has a bad matchup, or when you want to bring in a better answer.
- If one of your Pokemon faints, you must send in another one from the back before the next turn can begin.

You only have four Pokemon in the match, so every switch matters.

## What Protect does

- Protect usually blocks most direct attacks for one turn.
- It is one of the most important moves in doubles because it can keep a Pokemon alive while its partner attacks.
- It also helps you stall out field effects like Tailwind or Trick Room for a turn.

If you are unsure what to click, Protect is often safer than making a reckless attack with a Pokemon that might get knocked out.

## What Terastallization does

- Terastallization changes a Pokemon into its Tera type.
- It can make a Pokemon stronger on offense, safer on defense, or both.
- You only get to Terastallize once per battle, so do not feel forced to use it on turn one.

Beginners should treat Tera like an emergency tool or a finishing tool: use it either to save an important Pokemon or to secure a key knockout.

## What you should pay attention to during the battle

- Which Pokemon on each side are low on HP.
- Which opposing Pokemon are the biggest threats right now.
- Which side is faster.
- Whether Trick Room, Tailwind, weather, terrain, or other effects are active.
- Which Pokemon are still in the back.

If you lose track of speed or forget what is still unrevealed, turns start feeling random even when they are not.

## A very simple way to play your turns

- Ask which opposing Pokemon is the biggest immediate threat.
- Ask whether one of your Pokemon needs to Protect or switch to stay alive.
- Attack the threat if you can remove it safely.
- If you cannot remove it, make the board safer for next turn instead of forcing a bad attack.

That is the core loop of VGC: keep improving the board state until the opponent runs out of safe options.

## Example of one turn

- Your two active Pokemon are on the field.
- You think one of them might get knocked out, so you choose Protect with it.
- Your other Pokemon uses an attack into the opponent's more dangerous slot.
- The opponent attacks into your Protect, wasting that hit.
- Your partner lands damage or gets a knockout.
- The turn ends, you look at the new board, and then you choose two actions again.

That is what playing VGC literally is: read the field, choose two actions, watch the turn resolve, then repeat.

## Common beginner mistakes

- Bringing four Pokemon without thinking about how they work together.
- Attacking every turn even when a switch or Protect is safer.
- Ignoring which Pokemon is faster.
- Forgetting that you can target either opposing Pokemon.
- Using Terastallization too early with no clear reason.

## Best way to improve at the start

- Focus on learning turn flow before trying to memorize advanced strategy.
- After each game, ask why a Pokemon fainted and whether Protect or a switch would have helped.
- Try to understand why you won or lost the speed race on important turns.
- Learn a few common moves first: Protect, Fake Out, Tailwind, Trick Room, Helping Hand, and spread attacks.

Once the basic loop feels natural, strategy guides will make much more sense because you will already understand what the buttons in a VGC turn are actually doing.`;