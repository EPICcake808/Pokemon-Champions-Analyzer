"""Preview-trainer mode: paste an opponent's six, get a recommended bring-four + lead.

Both teams are fully known (pasted decklists), so the recommendation is grounded in real
numbers: the :mod:`damage` engine drives every KO call and the shared stat formula drives
the speed reads. The analyzer's member-resolution and combatant helpers are reused so the
math matches the rest of the app exactly.
"""

from __future__ import annotations

from itertools import combinations

from .analyzer import _combatant_from_member, _normalized_member_stats, _resolve_members
from .damage import DamageResult, FieldConditions, compute_damage
from .data import CachedPokeApiClient, MetadataProvider
from .models import TeamMember
from .regulations import DEFAULT_REGULATION_ID
from .showdown import parse_showdown_team


_FAKE_OUT = "fake-out"
_TAILWIND = "tailwind"
_TRICK_ROOM = "trick-room"
_REDIRECTION_MOVES = {"follow-me", "rage-powder"}
_BRING_SIZE = 4


def _best_damage(attacker: TeamMember, defender: TeamMember) -> DamageResult | None:
    """Highest single-target roll from any of the attacker's damaging moves."""
    attacker_combatant = _combatant_from_member(attacker)
    defender_combatant = _combatant_from_member(defender)
    best: DamageResult | None = None
    for move in attacker.move_data:
        result = compute_damage(attacker_combatant, defender_combatant, move, FieldConditions())
        if result is None:
            continue
        if best is None or result.max_percent > best.max_percent:
            best = result
    return best


def _speed(member: TeamMember) -> int:
    return _normalized_member_stats(member)["speed"]


def _support_tags(member: TeamMember) -> set[str]:
    tags: set[str] = set()
    for move in member.move_data:
        api_name = move.api_name
        if api_name == _FAKE_OUT:
            tags.add("fake_out")
        elif api_name == _TAILWIND:
            tags.add("tailwind")
        elif api_name == _TRICK_ROOM:
            tags.add("trick_room")
        elif api_name in _REDIRECTION_MOVES:
            tags.add("redirection")
        elif move.priority > 0 and move.damage_class != "status":
            tags.add("priority")
    return tags


def _line_payload(result: DamageResult | None) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "move": result.move,
        "min_percent": result.min_percent,
        "max_percent": result.max_percent,
        "summary": result.summary,
        "guaranteed_ohko": result.guaranteed_ohko,
        "guaranteed_2hko": result.guaranteed_2hko,
    }


def analyze_preview(
    my_team_text: str,
    opponent_team_text: str,
    metadata_provider: MetadataProvider | None = None,
    regulation_id: str | None = DEFAULT_REGULATION_ID,
) -> dict[str, object]:
    provider = metadata_provider or CachedPokeApiClient()
    my_sets = parse_showdown_team(my_team_text)
    opponent_sets = parse_showdown_team(opponent_team_text)
    if not my_sets:
        raise ValueError("Paste your own team before running the preview trainer.")
    if not opponent_sets:
        raise ValueError("Paste the opponent's team to scout the matchup.")

    my_members = _resolve_members(my_sets, provider, regulation_id=regulation_id)
    opponent_members = _resolve_members(opponent_sets, provider, regulation_id=regulation_id)
    opponent_count = len(opponent_members)
    opponent_has_trick_room = any(
        move.api_name == _TRICK_ROOM for member in opponent_members for move in member.move_data
    )

    records: list[dict[str, object]] = []
    net_by_member: dict[str, float] = {}
    ko_targets_by_member: dict[str, set[str]] = {}
    outspeed_frac_by_member: dict[str, float] = {}
    support_by_member: dict[str, set[str]] = {}

    for member in my_members:
        name = member.pokemon_set.display_name
        my_speed = _speed(member)
        support = _support_tags(member)
        support_by_member[name] = support

        outspeeds: list[str] = []
        ko_targets: list[str] = []
        ohko_targets: list[str] = []
        threatened_by: list[str] = []
        ohko_threats: list[str] = []
        lines: dict[str, dict[str, object]] = {}

        for opponent in opponent_members:
            opponent_name = opponent.pokemon_set.display_name
            if my_speed > _speed(opponent):
                outspeeds.append(opponent_name)
            outgoing = _best_damage(member, opponent)
            incoming = _best_damage(opponent, member)
            if outgoing is not None and outgoing.guaranteed_ohko:
                ohko_targets.append(opponent_name)
            if outgoing is not None and outgoing.guaranteed_2hko:
                ko_targets.append(opponent_name)
            if incoming is not None and incoming.guaranteed_ohko:
                ohko_threats.append(opponent_name)
            if incoming is not None and incoming.guaranteed_2hko:
                threatened_by.append(opponent_name)
            lines[opponent_name] = {
                "out": _line_payload(outgoing),
                "in": _line_payload(incoming),
            }

        outspeed_frac = len(outspeeds) / opponent_count if opponent_count else 0.0
        outspeed_frac_by_member[name] = outspeed_frac
        ko_targets_by_member[name] = set(ko_targets)
        # OHKOs count double; getting reliably KO'd is the main liability.
        net = (
            len(ko_targets)
            + len(ohko_targets)
            - len(threatened_by)
            - len(ohko_threats)
            + 0.5 * outspeed_frac
        )
        net_by_member[name] = net

        records.append(
            {
                "member": name,
                "speed": my_speed,
                "outspeeds": len(outspeeds),
                "opponent_count": opponent_count,
                "ko_targets": ko_targets,
                "ohko_targets": ohko_targets,
                "threatened_by": threatened_by,
                "ohko_threats": ohko_threats,
                "support": sorted(support),
                "lines": lines,
            }
        )

    bring_size = min(_BRING_SIZE, len(my_members))
    member_names = [member.pokemon_set.display_name for member in my_members]

    def _combo_score(combo: tuple[str, ...]) -> tuple[float, int]:
        base = sum(net_by_member[name] for name in combo)
        covered = set().union(*(ko_targets_by_member[name] for name in combo)) if combo else set()
        support_bonus = 0.5 * len({tag for name in combo for tag in support_by_member[name]})
        return base + len(covered) + support_bonus, len(covered)

    combos = list(combinations(member_names, bring_size)) or [tuple(member_names)]
    scored_combos = sorted(combos, key=lambda combo: _combo_score(combo)[0], reverse=True)
    best_combo = scored_combos[0]
    best_score, covered_count = _combo_score(best_combo)

    def _lead_pair(combo: tuple[str, ...]) -> list[str]:
        if len(combo) < 2:
            return list(combo)
        support_weight = {"fake_out": 1.0, "tailwind": 1.0, "redirection": 0.8, "priority": 0.4, "trick_room": 0.6}

        def _lead_value(name: str) -> float:
            tags = support_by_member[name]
            return net_by_member[name] + outspeed_frac_by_member[name] + sum(support_weight.get(tag, 0.0) for tag in tags)

        pair = max(combinations(combo, 2), key=lambda p: _lead_value(p[0]) + _lead_value(p[1]))
        return sorted(pair, key=_lead_value, reverse=True)

    lead = _lead_pair(best_combo)

    reasons = _build_reasons(
        best_combo,
        lead,
        records,
        opponent_members,
        opponent_count,
        covered_count,
        outspeed_frac_by_member,
        opponent_has_trick_room,
    )

    alternatives = [
        {"members": list(combo), "lead": _lead_pair(combo)}
        for combo in scored_combos[1:3]
    ]

    return {
        "ok": True,
        "opponent": [member.pokemon_set.display_name for member in opponent_members],
        "opponent_has_trick_room": opponent_has_trick_room,
        "recommended_bring": {
            "members": list(best_combo),
            "lead": lead,
            "score": round(best_score, 2),
            "covers": covered_count,
            "opponent_count": opponent_count,
            "reasons": reasons,
        },
        "alternatives": alternatives,
        "matchups": records,
    }


def _build_reasons(
    combo: tuple[str, ...],
    lead: list[str],
    records: list[dict[str, object]],
    opponent_members: list[TeamMember],
    opponent_count: int,
    covered_count: int,
    outspeed_frac_by_member: dict[str, float],
    opponent_has_trick_room: bool,
) -> list[str]:
    reasons: list[str] = []
    record_by_name = {record["member"]: record for record in records}

    reasons.append(
        f"Bring {', '.join(combo)} — collectively reliably KOs {covered_count} of their {opponent_count}."
    )

    if lead:
        lead_record = record_by_name.get(lead[0], {})
        outsped = lead_record.get("outspeeds", 0)
        support = lead_record.get("support", [])
        support_note = f" with {', '.join(support)}" if support else ""
        reasons.append(
            f"Lead {' + '.join(lead)}: {lead[0]} outspeeds {outsped}/{opponent_count} of their team{support_note}."
        )

    # Their scariest mon vs your bring: which opponent KOs the most of your picks.
    threat_counts: list[tuple[str, int]] = []
    for opponent in opponent_members:
        opponent_name = opponent.pokemon_set.display_name
        hit = sum(
            1
            for name in combo
            if opponent_name in record_by_name[name]["threatened_by"]
            or opponent_name in record_by_name[name]["ohko_threats"]
        )
        if hit:
            threat_counts.append((opponent_name, hit))
    for opponent_name, hit in sorted(threat_counts, key=lambda item: item[1], reverse=True)[:2]:
        reasons.append(f"Watch their {opponent_name}: reliably KOs {hit} of your bring.")

    # A concrete KO highlight from the bring.
    for name in combo:
        ohko = record_by_name[name]["ohko_targets"]
        if ohko:
            reasons.append(f"{name} OHKOs their {ohko[0]}.")
            break

    if opponent_has_trick_room:
        reasons.append(
            "Opponent carries Trick Room — your speed edge can invert; value bulk, Taunt, or slower picks."
        )

    return reasons
