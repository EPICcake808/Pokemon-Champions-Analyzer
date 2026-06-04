from __future__ import annotations

from dataclasses import dataclass


CHAMPIONS_FIXED_IV = 31
CHAMPIONS_TOTAL_SPS = 66


@dataclass(frozen=True)
class SpeedBenchmark:
    slug: str
    label: str
    target_speed: int
    source: str


@dataclass(frozen=True)
class SpeedBenchmarkGroup:
    slug: str
    label: str
    benchmarks: tuple[SpeedBenchmark, ...]
    comparison: str = "faster"


@dataclass(frozen=True)
class RegulationSpeedBenchmarkCatalog:
    regulation_id: str
    display_name: str
    notes: str
    groups: tuple[SpeedBenchmarkGroup, ...]


def _level_50_speed(base_speed: int, *, ev: int = CHAMPIONS_TOTAL_SPS, positive_nature: bool = True) -> int:
    base_component = ((2 * base_speed + CHAMPIONS_FIXED_IV) * 50) // 100
    stat = base_component + 5
    if positive_nature:
        return stat * 11 // 10 + ev
    return stat + ev


def _choice_scarf_speed(speed: int) -> int:
    return speed * 3 // 2


def _minimum_level_50_speed(base_speed: int) -> int:
    base_component = ((2 * base_speed + CHAMPIONS_FIXED_IV) * 50) // 100
    return (base_component + 5) * 9 // 10


_REGULATION_SPEED_BENCHMARKS = {
    "champions_regulation_m_a": RegulationSpeedBenchmarkCatalog(
        regulation_id="champions_regulation_m_a",
        display_name="Pokemon Champions Regulation M-A Speed Benchmarks",
        notes=(
            "Curated from repeated Regulation M-A tournament fast-mode shells and common max-Speed "
            "reference points. These are qualitative benchmark tiers, not exhaustive usage stats."
        ),
        groups=(
            SpeedBenchmarkGroup(
                slug="natural",
                label="Natural Speed",
                benchmarks=(
                    SpeedBenchmark(
                        slug="jolly_garchomp",
                        label="Max-Speed Jolly Garchomp",
                        target_speed=_level_50_speed(102),
                        source="Common M-A fast physical cleaner",
                    ),
                    SpeedBenchmark(
                        slug="timid_whimsicott",
                        label="Max-Speed Timid Whimsicott",
                        target_speed=_level_50_speed(116),
                        source="Common M-A Tailwind setter reference",
                    ),
                    SpeedBenchmark(
                        slug="jolly_sneasler",
                        label="Max-Speed Jolly Sneasler",
                        target_speed=_level_50_speed(120),
                        source="Common M-A high-end unboosted speed threat",
                    ),
                    SpeedBenchmark(
                        slug="timid_dragapult",
                        label="Max-Speed Timid Dragapult",
                        target_speed=_level_50_speed(142),
                        source="Top-end unboosted speed ceiling",
                    ),
                ),
            ),
            SpeedBenchmarkGroup(
                slug="tailwind",
                label="Tailwind Speed",
                benchmarks=(
                    SpeedBenchmark(
                        slug="tailwind_garchomp",
                        label="Tailwind Max-Speed Jolly Garchomp",
                        target_speed=_level_50_speed(102) * 2,
                        source="Common Tailwind offense floor",
                    ),
                    SpeedBenchmark(
                        slug="tailwind_sneasler",
                        label="Tailwind Max-Speed Jolly Sneasler",
                        target_speed=_level_50_speed(120) * 2,
                        source="Common Tailwind high-end pressure line",
                    ),
                    SpeedBenchmark(
                        slug="tailwind_dragapult",
                        label="Tailwind Max-Speed Timid Dragapult",
                        target_speed=_level_50_speed(142) * 2,
                        source="Top-end Tailwind ceiling",
                    ),
                ),
            ),
            SpeedBenchmarkGroup(
                slug="choice_scarf",
                label="Choice Scarf Speed",
                benchmarks=(
                    SpeedBenchmark(
                        slug="choice_scarf_basculegion",
                        label="Max-Speed Choice Scarf Jolly Basculegion",
                        target_speed=_choice_scarf_speed(_level_50_speed(78)),
                        source="Common M-A rain and Tailwind Scarf reference",
                    ),
                    SpeedBenchmark(
                        slug="choice_scarf_garchomp",
                        label="Max-Speed Choice Scarf Jolly Garchomp",
                        target_speed=_choice_scarf_speed(_level_50_speed(102)),
                        source="Common M-A generic Scarf speed ceiling",
                    ),
                ),
            ),
            SpeedBenchmarkGroup(
                slug="trick_room",
                label="Trick Room Underspeed",
                comparison="slower",
                benchmarks=(
                    SpeedBenchmark(
                        slug="min_speed_torkoal",
                        label="Min-Speed Torkoal",
                        target_speed=_minimum_level_50_speed(20),
                        source="Common dedicated Trick Room floor",
                    ),
                    SpeedBenchmark(
                        slug="min_speed_amoonguss",
                        label="Min-Speed Amoonguss",
                        target_speed=_minimum_level_50_speed(30),
                        source="Common slow redirection reference",
                    ),
                    SpeedBenchmark(
                        slug="min_speed_kingambit",
                        label="Min-Speed Kingambit",
                        target_speed=_minimum_level_50_speed(50),
                        source="Common mid-slow Trick Room breaker reference",
                    ),
                    SpeedBenchmark(
                        slug="min_speed_farigiraf",
                        label="Min-Speed Farigiraf",
                        target_speed=_minimum_level_50_speed(60),
                        source="Common Trick Room setter benchmark",
                    ),
                    SpeedBenchmark(
                        slug="min_speed_sinistcha",
                        label="Min-Speed Sinistcha",
                        target_speed=_minimum_level_50_speed(70),
                        source="Common M-A Trick Room support benchmark",
                    ),
                ),
            ),
        ),
    ),
}


def get_speed_benchmark_catalog(regulation_id: str | None) -> RegulationSpeedBenchmarkCatalog | None:
    if regulation_id is None:
        return None
    return _REGULATION_SPEED_BENCHMARKS.get(regulation_id)