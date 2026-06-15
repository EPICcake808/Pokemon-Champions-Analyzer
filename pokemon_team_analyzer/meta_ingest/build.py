"""Orchestrate ingestion into a validated meta-snapshot feed + reconciliation report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..analyzer import COMMON_META_POKEMON_CONTEXT, _render_series, _render_species_token
from . import DEFAULT_FORMAT_CODE, DEFAULT_REGULATION_ID
from .discover import DiscoveryResult, discover_shells
from .reconcile import ReconcileReport, reconcile
from .schema import validate_feed
from .sources import SourceUsage
from .sources import limitless, limitlessvgc, pikalytics, pokemon_zone
from .usage import UsageReport, compute_usage

SOURCE_LABEL = "Pokemon Champions Analyzer automated multi-source Regulation M-A meta board"
MAX_COMMON_META_POKEMON = 10
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_PATH = _REPO_ROOT / "build" / "meta-snapshots.json"
PUBLISH_OUT_PATH = _REPO_ROOT / "web" / "public" / "meta-snapshots.json"


@dataclass
class IngestResult:
    feed: dict[str, object]
    usage: UsageReport
    discovery: DiscoveryResult
    reconcile_report: ReconcileReport
    warnings: list[str]


def _iso_now() -> str:
    # Zod's z.string().datetime() requires a trailing "Z" (UTC) and rejects
    # numeric offsets, so emit the same form the rest of the app uses.
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _build_common_meta_pokemon(
    usage: UsageReport, snapshots: list[dict[str, object]]
) -> list[dict[str, object]]:
    featured_by_token: dict[str, list[str]] = {}
    for snapshot in snapshots:
        label = str(snapshot["label"])
        for token in snapshot["key_pokemon"]:  # type: ignore[union-attr]
            featured_by_token.setdefault(str(token), [])
            if label not in featured_by_token[str(token)]:
                featured_by_token[str(token)].append(label)

    common: list[dict[str, object]] = []
    for entry in usage.top(MAX_COMMON_META_POKEMON):
        species = _render_species_token(entry.token)
        context = COMMON_META_POKEMON_CONTEXT.get(entry.token)
        featured = featured_by_token.get(entry.token, [])[:3]
        if context is None:
            featured_text = _render_series(featured[:2]) if featured else ""
            if featured_text:
                why_used = (
                    f"{species} runs on {entry.raw_usage_pct:.1f}% of sampled Regulation M-A teams, "
                    f"turning up in shells like {featured_text}. That much usage across different "
                    f"team styles is what lands it on the meta board."
                )
            else:
                why_used = (
                    f"{species} runs on {entry.raw_usage_pct:.1f}% of sampled Regulation M-A teams, "
                    f"spread across a range of team styles rather than tied to one shell — enough usage "
                    f"to land it on the meta board."
                )
            what_it_does = (
                "Its spot here comes from broad usage across the sampled teams rather than one "
                "signature role; teams reach for it in both offensive and supportive builds."
            )
        else:
            why_used = context["why_used"]
            what_it_does = context["what_it_does"]

        common.append(
            {
                "species": species,
                # Headline ranking metric: weighted by tournament prestige + top-cut runs.
                "metaShare": entry.weighted_usage_pct,
                "whyUsed": why_used[:400],
                "whatItDoes": what_it_does[:400],
                "featuredTeams": featured,
                # Extra provenance (tolerated by the web schema; surfaced in a later pass).
                "weightedUsagePercent": entry.weighted_usage_pct,
                "usagePercent": entry.raw_usage_pct,
                "teamCount": entry.team_count,
                "sampleSize": usage.sample_size,
            }
        )
    return common


def build_feed(
    *,
    since_days: int = 30,
    officials_since_days: int = 60,
    format_code: str = DEFAULT_FORMAT_CODE,
    min_players: int = 8,
    max_tournaments: int = 60,
    max_teams_analyzed: int = 150,
    regulation_id: str = DEFAULT_REGULATION_ID,
    include_secondary: bool = True,
    include_officials: bool = True,
    on_progress=None,
) -> IngestResult:
    # Grassroots platform rosters: full decklists -> used for BOTH usage and shell discovery.
    platform_rosters, tournaments, warnings = limitless.collect_rosters(
        since_days=since_days,
        format_code=format_code,
        min_players=min_players,
        max_tournaments=max_tournaments,
        on_progress=on_progress,
    )
    if not platform_rosters:
        raise RuntimeError(
            "No rosters were collected from Limitless (the authoritative source). "
            "Widen --since, lower --min-players, or check connectivity."
        )

    # Official-event rosters (Regionals/Internationals/Specials/Worlds): species only,
    # so they feed the weighted usage ranking but not shell discovery.
    official_rosters: list = []
    official_tournaments: list = []
    if include_officials:
        official_rosters, official_tournaments, official_warnings = limitlessvgc.collect_official_rosters(
            since_days=officials_since_days
        )
        warnings.extend(official_warnings)

    all_rosters = platform_rosters + official_rosters
    usage = compute_usage(
        all_rosters,
        tournament_count=len(tournaments) + len(official_tournaments),
        since_days=since_days,
    )
    # Discovery needs move data: grassroots rosters (all have decklists) plus the official
    # top-cut teams enriched with full decklists. The weighting inside discovery makes those
    # official deep runs dominate the teams list.
    discovery_rosters = platform_rosters + [r for r in official_rosters if r.decklist]
    discovery = discover_shells(discovery_rosters, regulation_id=regulation_id, max_teams_analyzed=max_teams_analyzed)
    warnings.extend(discovery.warnings)
    if not discovery.snapshots:
        raise RuntimeError("Discovery produced no team shells; cannot build a valid board.")

    secondary_sources: list[SourceUsage] = []
    if include_secondary:
        secondary_sources = [pikalytics.fetch_usage(), pokemon_zone.fetch_usage()]
    reconcile_report = reconcile(usage, secondary_sources)

    generated_at = _iso_now()
    common_meta = _build_common_meta_pokemon(usage, discovery.snapshots)

    official_summary = (
        ", ".join(f"{t.name} ({t.tier.replace('_', ' ')}, {t.players})" for t in official_tournaments[:4])
        or "none in window"
    )
    notes = [
        f"Automated multi-source ingest: {usage.sample_size} teams across {usage.tournament_count} "
        f"tournaments (grassroots last {since_days}d + officials last {officials_since_days}d).",
        "The meta list is ranked by USAGE WEIGHTED toward the biggest, most official events "
        "(Regionals/Internationals/Special Events/Worlds) and the deepest top-cut runs; raw share-of-teams "
        "is retained for transparency.",
        f"Official events weighted in: {official_summary}.",
        f"Discovered {len(discovery.snapshots)} representative shells from {discovery.teams_analyzed} "
        f"analyzed grassroots teams ({discovery.clusters_formed} clusters).",
        *reconcile_report.to_notes(),
        "Provenance: limitlessvgc.com (official results) + Limitless tournament API (grassroots), "
        "cross-checked against Pikalytics and Pokémon Zone.",
    ]

    document = {
        "regulationId": regulation_id,
        "updatedAt": generated_at,
        "sourceLabel": SOURCE_LABEL,
        "notes": [note[:400] for note in notes][:20],
        "commonMetaPokemon": common_meta,
        "tournamentTeamSnapshots": discovery.snapshots,
        # Extra provenance block (tolerated by the web schema today).
        "provenance": {
            "generatedAt": generated_at,
            "windowDays": since_days,
            "officialsWindowDays": officials_since_days,
            "sampleSize": usage.sample_size,
            "tournamentCount": usage.tournament_count,
            "officialEventCount": usage.official_count,
            "tierBreakdown": usage.tier_breakdown,
            "officialEvents": [
                {"name": t.name, "tier": t.tier, "players": t.players, "url": t.url}
                for t in official_tournaments
            ],
            "sources": reconcile_report.sources,
            "authoritativeSource": {
                "name": "limitlessvgc.com (official results)",
                "url": "https://limitlessvgc.com/tournaments",
            },
        },
    }

    feed = {
        "version": 1,
        "generatedAt": generated_at,
        "regulations": [document],
    }
    validate_feed(feed)

    return IngestResult(
        feed=feed,
        usage=usage,
        discovery=discovery,
        reconcile_report=reconcile_report,
        warnings=warnings,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m pokemon_team_analyzer.meta_ingest",
        description="Build the Champions Regulation M-A meta-snapshot feed from real tournament data.",
    )
    parser.add_argument("--since", type=int, default=30, help="Grassroots lookback window in days (default 30).")
    parser.add_argument(
        "--officials-since", type=int, default=60,
        help="Official-event (limitlessvgc) lookback window in days (default 60; officials are sparser).",
    )
    parser.add_argument(
        "--format-code", default=DEFAULT_FORMAT_CODE, help="Limitless format code to match (default 'M-A')."
    )
    parser.add_argument("--min-players", type=int, default=8, help="Skip grassroots tournaments below this size.")
    parser.add_argument("--max-tournaments", type=int, default=60, help="Cap on grassroots tournaments sampled.")
    parser.add_argument("--max-teams", type=int, default=150, help="Cap on unique teams analyzed for discovery.")
    parser.add_argument("--no-officials", action="store_true", help="Skip the limitlessvgc official-events source.")
    parser.add_argument("--no-secondary", action="store_true", help="Skip Pikalytics/Pokémon Zone cross-checks.")
    parser.add_argument("--out", type=Path, default=None, help="Output path (default build/meta-snapshots.json).")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write to web/public/meta-snapshots.json (the served artifact) instead of the scratch path.",
    )
    parser.add_argument(
        "--publish-url",
        default=os.getenv("META_SNAPSHOT_PUBLISH_URL", "").strip() or None,
        help="POST the validated feed to this /api/meta-snapshot/publish URL "
        "(auth via META_SNAPSHOT_REFRESH_SECRET or CRON_SECRET). "
        "Defaults to the META_SNAPSHOT_PUBLISH_URL env var.",
    )
    parser.add_argument("--report", action="store_true", help="Print the full reconciliation report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    def progress(index: int, total: int, tournament, roster_count: int) -> None:
        print(f"  [{index}/{total}] {tournament.name[:48]:48s} -> {roster_count} teams", file=sys.stderr)

    print(
        f"Collecting Limitless Reg {args.format_code} tournaments (last {args.since}d, "
        f"min {args.min_players} players, up to {args.max_tournaments})...",
        file=sys.stderr,
    )
    try:
        result = build_feed(
            since_days=args.since,
            officials_since_days=args.officials_since,
            format_code=args.format_code,
            min_players=args.min_players,
            max_tournaments=args.max_tournaments,
            max_teams_analyzed=args.max_teams,
            include_secondary=not args.no_secondary,
            include_officials=not args.no_officials,
            on_progress=progress,
        )
    except Exception as error:  # noqa: BLE001 - CLI boundary: report and exit nonzero
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    usage = result.usage
    print(
        f"\nSampled {usage.sample_size} teams across {usage.tournament_count} tournaments "
        f"({usage.official_count} official); tiers: {usage.tier_breakdown}.",
        file=sys.stderr,
    )
    print("Top meta (weighted by tournament prestige + top-cut runs | raw share):", file=sys.stderr)
    for entry in usage.top(10):
        print(
            f"  {_render_species_token(entry.token):24s} {entry.weighted_usage_pct:5.1f}%  "
            f"(raw {entry.raw_usage_pct:4.1f}%, {entry.team_count} teams)",
            file=sys.stderr,
        )
    print(f"\nDiscovered {len(result.discovery.snapshots)} shells.", file=sys.stderr)
    for snapshot in result.discovery.snapshots[:8]:
        print(f"  {str(snapshot['label'])[:46]:46s} fr={snapshot['field_relevance']}", file=sys.stderr)

    if args.report:
        print("\n" + result.reconcile_report.render_text(), file=sys.stderr)
    if result.warnings:
        print(f"\n{len(result.warnings)} warning(s); first few:", file=sys.stderr)
        for warning in result.warnings[:5]:
            print(f"  - {warning}", file=sys.stderr)

    out_path = args.out or (PUBLISH_OUT_PATH if args.write else DEFAULT_OUT_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result.feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote validated feed -> {out_path}", file=sys.stderr)

    # Publish to the DB-backed route (the file is already written, so a publish failure
    # never costs the repo-commit half of the pipeline).
    if args.publish_url:
        from .publish import publish_feed

        try:
            response = publish_feed(result.feed, args.publish_url)
            print(f"Published to {args.publish_url} -> {json.dumps(response)[:200]}", file=sys.stderr)
        except Exception as error:  # noqa: BLE001 - CLI boundary: report and exit nonzero
            print(f"ERROR publishing to {args.publish_url}: {error}", file=sys.stderr)
            return 1

    return 0
