"""Cross-validate the authoritative Limitless usage against secondary sources.

Limitless (our sampled tournament window) is authoritative. Pikalytics and
Pokémon Zone sample different, usually larger populations, so absolute
percentages will differ — reconciliation therefore checks *directional* agreement
(do the same species dominate?) and flags material disagreements rather than
demanding exact matches. When a secondary source is unavailable the run proceeds
and the gap is recorded honestly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .sources import SourceUsage
from .usage import UsageReport, base_species_token

# A top-of-meta token is "missing" from a secondary source if it doesn't appear in
# the source's leaderboard at all — worth surfacing as a possible sampling gap.
_TOP_N = 12
_LEADERBOARD_DEPTH = 20


@dataclass
class TokenComparison:
    token: str
    limitless_pct: float
    secondary_pct: dict[str, float] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)


@dataclass
class ReconcileReport:
    sources: list[dict[str, object]]
    comparisons: list[TokenComparison]
    summary: list[str]
    top10_overlap: float

    def to_notes(self) -> list[str]:
        """Compact, <=400-char notes embeddable in the published feed."""

        available = [s for s in self.sources if s["available"]]
        unavailable = [s for s in self.sources if not s["available"]]
        notes = [
            "Reconciliation: "
            + (
                "; ".join(f"{s['name']} ({s['rows']} rows)" for s in available) or "no secondary sources available"
            )
            + (
                "; unavailable: " + ", ".join(f"{s['name']} — {s['note']}" for s in unavailable)
                if unavailable
                else ""
            ),
            f"Top-10 usage agreement with cross-checks: {self.top10_overlap:.0%}.",
        ]
        flagged = [c for c in self.comparisons if c.flags]
        if flagged:
            notes.append(
                "Usage disagreements flagged: "
                + "; ".join(f"{c.token} ({'/'.join(c.flags)})" for c in flagged[:6])
                + "."
            )
        return [note[:400] for note in notes]

    def render_text(self) -> str:
        lines = ["Reconciliation report", "=" * 21]
        for source in self.sources:
            status = "ok" if source["available"] else "UNAVAILABLE"
            lines.append(f"  [{status}] {source['name']}: {source['note']} ({source['url']})")
        lines.append("")
        lines.append(f"  Top-10 usage agreement with cross-checks: {self.top10_overlap:.0%}")
        lines.append("")
        header = f"  {'species':24s} {'limitless':>10s}"
        secondary_names = [s["name"] for s in self.sources if s["available"]]
        for name in secondary_names:
            header += f" {name[:12]:>13s}"
        lines.append(header)
        for comparison in self.comparisons:
            row = f"  {comparison.token:24s} {comparison.limitless_pct:>9.1f}%"
            for name in secondary_names:
                value = comparison.secondary_pct.get(name)
                row += f" {value:>12.1f}%" if value is not None else f" {'—':>13s}"
            if comparison.flags:
                row += f"   ⚠ {', '.join(comparison.flags)}"
            lines.append(row)
        return "\n".join(lines)


def _base_normalized_token_pct(source: SourceUsage) -> dict[str, float]:
    """Collapse a secondary source's mega/variant tokens to base species (summing).

    Lets us compare apples-to-apples against our base-normalized raw usage.
    """

    base_pct: dict[str, float] = {}
    for token, pct in source.token_pct.items():
        base = base_species_token(token)
        base_pct[base] = round(base_pct.get(base, 0.0) + pct, 2)
    return base_pct


def reconcile(usage: UsageReport, secondary_sources: list[SourceUsage]) -> ReconcileReport:
    # Reconcile against RAW usage (not the weighted headline): Pikalytics reports a
    # raw share of teams, so weighted usage would diverge by design.
    limitless_top = usage.top(_TOP_N)
    limitless_top10_tokens = {entry.token for entry in usage.top(10)}

    sources_meta: list[dict[str, object]] = [
        {
            "name": source.name,
            "available": source.available,
            "rows": len(source.token_pct),
            "note": source.note,
            "url": source.provenance_url,
        }
        for source in secondary_sources
    ]

    available_sources = [source for source in secondary_sources if source.available]
    base_maps = {source.name: _base_normalized_token_pct(source) for source in available_sources}

    comparisons: list[TokenComparison] = []
    for entry in limitless_top:
        comparison = TokenComparison(token=entry.token, limitless_pct=entry.raw_usage_pct)
        for source in available_sources:
            value = base_maps[source.name].get(entry.token)
            if value is not None:
                comparison.secondary_pct[source.name] = value
            elif entry.token in limitless_top10_tokens:
                comparison.flags.append(f"absent from {source.name}")
        comparisons.append(comparison)

    # Directional agreement: of our top-10, how many also appear in each cross-check?
    overlaps: list[float] = []
    for source in available_sources:
        source_tokens = set(base_maps[source.name])
        if limitless_top10_tokens:
            overlaps.append(len(limitless_top10_tokens & source_tokens) / len(limitless_top10_tokens))
    top10_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0

    summary: list[str] = []
    if not available_sources:
        summary.append("No secondary sources were available; usage rests solely on the Limitless sample.")
    else:
        summary.append(
            f"Cross-checked against {', '.join(source.name for source in available_sources)}; "
            f"top-10 agreement {top10_overlap:.0%}."
        )
    flagged_tokens = [comparison.token for comparison in comparisons if comparison.flags]
    if flagged_tokens:
        summary.append(f"Flagged for review: {', '.join(flagged_tokens)}.")

    return ReconcileReport(
        sources=sources_meta,
        comparisons=comparisons,
        summary=summary,
        top10_overlap=top10_overlap,
    )
