"use client";

import { useMemo, useState } from "react";

import { formatLabel } from "@/lib/showdown";
import type {
  DamageCalcResponse,
  DamageMatchupRow,
  EffortValueStat,
  ParsedTeamMember,
  PokemonTeamAnalysis,
} from "@/lib/types";

const EV_KEY_BY_STAT: Record<EffortValueStat, string> = {
  hp: "HP",
  attack: "Atk",
  defense: "Def",
  special_attack: "SpA",
  special_defense: "SpD",
  speed: "Spe",
};

type Props = {
  analysis: PokemonTeamAnalysis;
  members: ParsedTeamMember[];
  regulationId: string;
};

function toEvTokens(evs: ParsedTeamMember["evs"]): Record<string, number> {
  const result: Record<string, number> = {};
  for (const [stat, value] of Object.entries(evs ?? {})) {
    if (typeof value === "number" && value > 0) {
      result[EV_KEY_BY_STAT[stat as EffortValueStat] ?? stat] = value;
    }
  }
  return result;
}

function severityColor(maxPercent: number): string {
  if (maxPercent >= 100) return "var(--negative)";
  if (maxPercent >= 50) return "var(--accent)";
  return "var(--fg-muted)";
}

function MatchupTable({
  heading,
  caption,
  rows,
  benchmarkSide,
}: {
  heading: string;
  caption: string;
  rows: DamageMatchupRow[];
  benchmarkSide: "attacker" | "defender";
}) {
  if (!rows.length) {
    return (
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-white/85">{heading}</h4>
        <p className="text-xs leading-5 text-[var(--fg-muted)]">
          No curated lines available — re-run the analyzer with the live data source connected.
        </p>
      </div>
    );
  }

  return (
    <div className="min-w-0 space-y-3">
      <div>
        <h4 className="text-sm font-semibold text-white/85">{heading}</h4>
        <p className="text-xs leading-5 text-[var(--fg-muted)]">{caption}</p>
      </div>
      <div className="-mx-2 min-w-0 overflow-x-auto">
        <table className="w-full min-w-[34rem] border-collapse text-left text-xs">
          <thead className="text-white/45">
            <tr>
              <th className="px-2 py-1 font-medium">Attacker</th>
              <th className="px-2 py-1 font-medium">Move</th>
              <th className="px-2 py-1 font-medium">Defender</th>
              <th className="px-2 py-1 text-right font-medium">Damage</th>
              <th className="px-2 py-1 font-medium">Result</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.attacker}-${row.move}-${row.defender}-${index}`} className="border-t border-[var(--line)]">
                <td className="px-2 py-1.5 text-white/80">
                  {row.attacker}
                  {benchmarkSide === "attacker" ? (
                    <span className="block text-[0.68rem] leading-4 text-white/40">{row.benchmark_set}</span>
                  ) : null}
                </td>
                <td className="px-2 py-1.5 text-white/65">{row.move}</td>
                <td className="px-2 py-1.5 text-white/80">
                  {row.defender}
                  {benchmarkSide === "defender" ? (
                    <span className="block text-[0.68rem] leading-4 text-white/40">{row.benchmark_set}</span>
                  ) : null}
                </td>
                <td
                  className="px-2 py-1.5 text-right font-mono tabular-nums"
                  style={{ color: severityColor(row.max_percent) }}
                >
                  {row.min_percent}–{row.max_percent}%
                </td>
                <td className="px-2 py-1.5 text-white/65">{row.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function DamageCalculator({ analysis, members, regulationId }: Props) {
  const namedMembers = useMemo(
    () => members.filter((member) => member.species.trim()),
    [members],
  );

  const [attackerIndex, setAttackerIndex] = useState(0);
  const [moveName, setMoveName] = useState("");
  const [defenderIndex, setDefenderIndex] = useState(namedMembers.length > 1 ? 1 : 0);
  const [customDefender, setCustomDefender] = useState("");
  const [weather, setWeather] = useState<"" | "sun" | "rain">("");
  const [spread, setSpread] = useState(false);
  const [crit, setCrit] = useState(false);
  const [attackerBurned, setBurned] = useState(false);
  const [result, setResult] = useState<DamageCalcResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const attacker = namedMembers[attackerIndex];
  const defender = namedMembers[defenderIndex];
  const attackerMoves = attacker?.moves.filter((move) => move.trim()) ?? [];
  const grid = analysis.damage_matchups;

  async function calculate() {
    if (!attacker) {
      setError("Add at least one Pokemon to the builder to calculate damage.");
      return;
    }
    const selectedMove = moveName || attackerMoves[0];
    if (!selectedMove) {
      setError("This attacker has no moves to calculate with.");
      return;
    }

    const defenderSide = customDefender.trim()
      ? { species: customDefender.trim() }
      : defender
        ? {
            species: defender.species,
            ability: defender.ability,
            item: defender.item,
            nature: defender.nature,
            evs: toEvTokens(defender.evs),
          }
        : null;

    if (!defenderSide) {
      setError("Pick a defender or type a species.");
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/damage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          attacker: {
            species: attacker.species,
            move: selectedMove,
            ability: attacker.ability,
            item: attacker.item,
            nature: attacker.nature,
            evs: toEvTokens(attacker.evs),
          },
          defender: defenderSide,
          field: { weather: weather || null, spread, crit, attackerBurned },
          regulationId,
        }),
      });
      const payload = (await response.json()) as DamageCalcResponse & { message?: string };
      if (!response.ok) {
        throw new Error(payload.message || "The damage calculation failed.");
      }
      setResult(payload);
    } catch (caught) {
      setResult(null);
      setError(caught instanceof Error ? caught.message : "The damage calculation failed.");
    } finally {
      setIsLoading(false);
    }
  }

  const roll = result?.result ?? null;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <MatchupTable
          heading="Incoming threats"
          caption="How the meta's defining nukes hit your team (assumed build shown under each)."
          rows={grid?.incoming ?? []}
          benchmarkSide="attacker"
        />
        <MatchupTable
          heading="Your offense vs common walls"
          caption="Whether your attackers break the format's bulky pivots (assumed build shown under each)."
          rows={grid?.outgoing ?? []}
          benchmarkSide="defender"
        />
      </div>

      <div className="rounded-lg border border-[var(--line)] p-4 sm:p-5">
        <h4 className="text-sm font-semibold text-white/85">Interactive calculator</h4>
        <p className="mt-1 text-xs leading-5 text-[var(--fg-muted)]">
          Uses the standard Gen 9 formula on Champions stats. Defender defaults to a teammate; type any species to test
          a custom target at neutral investment.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="space-y-1 text-xs text-white/55">
            <span>Attacker</span>
            <select
              value={attackerIndex}
              onChange={(event) => {
                setAttackerIndex(Number(event.target.value));
                setMoveName("");
              }}
              className="w-full border border-[var(--line)] bg-black/20 px-2 py-2 text-sm text-white/85 outline-none focus:border-white/45"
            >
              {namedMembers.map((member, index) => (
                <option key={member.displayName} value={index} className="bg-[#090b10]">
                  {member.species}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1 text-xs text-white/55">
            <span>Move</span>
            <select
              value={moveName || attackerMoves[0] || ""}
              onChange={(event) => setMoveName(event.target.value)}
              className="w-full border border-[var(--line)] bg-black/20 px-2 py-2 text-sm text-white/85 outline-none focus:border-white/45"
            >
              {attackerMoves.map((move) => (
                <option key={move} value={move} className="bg-[#090b10]">
                  {move}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1 text-xs text-white/55">
            <span>Defender</span>
            <select
              value={defenderIndex}
              onChange={(event) => setDefenderIndex(Number(event.target.value))}
              disabled={Boolean(customDefender.trim())}
              className="w-full border border-[var(--line)] bg-black/20 px-2 py-2 text-sm text-white/85 outline-none focus:border-white/45 disabled:opacity-40"
            >
              {namedMembers.map((member, index) => (
                <option key={member.displayName} value={index} className="bg-[#090b10]">
                  {member.species}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1 text-xs text-white/55">
            <span>Or custom defender</span>
            <input
              value={customDefender}
              onChange={(event) => setCustomDefender(event.target.value)}
              placeholder="e.g. Amoonguss"
              className="w-full border border-[var(--line)] bg-black/20 px-2 py-2 text-sm text-white/85 outline-none focus:border-white/45"
            />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-white/70">
          <label className="flex items-center gap-1.5">
            <span>Weather</span>
            <select
              value={weather}
              onChange={(event) => setWeather(event.target.value as "" | "sun" | "rain")}
              className="border border-[var(--line)] bg-black/20 px-2 py-1 text-sm text-white/85 outline-none focus:border-white/45"
            >
              <option value="" className="bg-[#090b10]">None</option>
              <option value="sun" className="bg-[#090b10]">Sun</option>
              <option value="rain" className="bg-[#090b10]">Rain</option>
            </select>
          </label>
          <label className="flex items-center gap-1.5">
            <input type="checkbox" checked={spread} onChange={(event) => setSpread(event.target.checked)} />
            <span>Spread move</span>
          </label>
          <label className="flex items-center gap-1.5">
            <input type="checkbox" checked={crit} onChange={(event) => setCrit(event.target.checked)} />
            <span>Critical hit</span>
          </label>
          <label className="flex items-center gap-1.5">
            <input type="checkbox" checked={attackerBurned} onChange={(event) => setBurned(event.target.checked)} />
            <span>Attacker burned</span>
          </label>
          <button
            type="button"
            onClick={calculate}
            disabled={isLoading || !attacker}
            className="ml-auto rounded border border-white/25 bg-white/5 px-4 py-1.5 text-sm font-medium text-white/90 transition hover:border-white/50 disabled:opacity-40"
          >
            {isLoading ? "Calculating…" : "Calculate"}
          </button>
        </div>

        {error ? <p className="mt-3 text-xs text-[var(--negative)]">{error}</p> : null}

        {result ? (
          roll ? (
            <div className="mt-4 space-y-2 border-t border-[var(--line)] pt-4">
              <p className="text-sm text-white/90">
                <span className="font-semibold">{result.attacker.species}</span> {result.move.name} →{" "}
                <span className="font-semibold">{result.defender.species}</span>
              </p>
              <p className="font-mono text-lg tabular-nums" style={{ color: severityColor(roll.max_percent) }}>
                {roll.min_percent}–{roll.max_percent}%
                <span className="ml-3 text-sm text-white/70">{roll.summary}</span>
              </p>
              <p className="text-xs text-[var(--fg-muted)]">
                {roll.min_damage}–{roll.max_damage} of {roll.defender_hp} HP · type ×{roll.type_multiplier} · STAB{" "}
                {roll.stab}
              </p>
              {roll.unmodeled.length ? (
                <p className="text-xs text-[var(--accent)]">
                  Not modeled: {roll.unmodeled.map((item) => formatLabel(item)).join(", ")}
                </p>
              ) : null}
            </div>
          ) : (
            <p className="mt-4 border-t border-[var(--line)] pt-4 text-xs text-[var(--fg-muted)]">
              {result.move.name} is a status move — it deals no direct damage.
            </p>
          )
        ) : null}
      </div>

      {grid?.notes?.length ? (
        <ul className="space-y-1 text-xs leading-5 text-white/40">
          {grid.notes.map((note) => (
            <li key={note}>• {note}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
