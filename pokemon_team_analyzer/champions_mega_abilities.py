"""Champions Mega-Evolution abilities that PokeAPI does not carry.

PokeAPI serves several Champions-original Mega forms (e.g. ``staraptor-mega``,
``scolipede-mega``, ``pyroar-mega``) with an empty ``abilities`` list, so the analyzer would
otherwise show no ability for them. This table fills that gap with the Champions ability each
Mega grants, keyed by the PokeAPI form slug (``api_name``) and written in PokeAPI ability-slug
form. It is applied *only* when PokeAPI returns no abilities, so any ability PokeAPI does provide
(e.g. ``raichu-mega-x`` -> ``electric-surge``) always wins.

Values are verified against Serebii's Champions dex and corroborating coverage. ``fire-mane``
(Mega Pyroar) and ``elevate`` (Mega Eelektross) are abilities new to the series.
"""
from __future__ import annotations


CHAMPIONS_MEGA_ABILITY_OVERRIDES: dict[str, tuple[str, ...]] = {
    # Regulation M-B Champions-original Megas.
    "staraptor-mega": ("contrary",),
    "scolipede-mega": ("shell-armor",),
    "scrafty-mega": ("intimidate",),
    "eelektross-mega": ("elevate",),
    "pyroar-mega": ("fire-mane",),
    "malamar-mega": ("contrary",),
    "barbaracle-mega": ("tough-claws",),
    "dragalge-mega": ("regenerator",),
    "falinks-mega": ("defiant",),
    "raichu-mega-x": ("electric-surge",),
    "raichu-mega-y": ("no-guard",),
}


def champions_mega_ability_overrides(api_name: str | None) -> tuple[str, ...]:
    """Return the Champions ability override for a Mega form slug, or an empty tuple."""
    if not api_name:
        return ()
    return CHAMPIONS_MEGA_ABILITY_OVERRIDES.get(api_name.strip().lower(), ())
