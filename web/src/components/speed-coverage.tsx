"use client";

import type { SpeedCoverage } from "@/lib/types";

function coverageColor(pct: number): string {
  if (pct >= 75) return "var(--positive)";
  if (pct >= 40) return "var(--accent)";
  return "var(--fg-muted)";
}

function Cell({ pct }: { pct: number }) {
  return (
    <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: coverageColor(pct) }}>
      {pct}%
    </td>
  );
}

export function SpeedCoveragePanel({ coverage }: { coverage: SpeedCoverage | undefined }) {
  if (!coverage?.available || !coverage.members.length) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div>
        <h4 className="text-sm font-semibold text-white/85">Meta speed coverage</h4>
        <p className="text-xs leading-5 text-[var(--fg-muted)]">
          Usage-weighted share of the {coverage.sample_species} most-used meta Pokemon each of your members moves before
          — at +0, with your Tailwind up, and under your Trick Room.
        </p>
      </div>
      <div className="-mx-2 overflow-x-auto">
        <table className="w-full min-w-[26rem] border-collapse text-left text-xs">
          <thead className="text-white/45">
            <tr>
              <th className="px-2 py-1 font-medium">Pokemon</th>
              <th className="px-2 py-1 text-right font-medium">Speed</th>
              <th className="px-2 py-1 text-right font-medium">+0</th>
              <th className="px-2 py-1 text-right font-medium">Tailwind</th>
              <th className="px-2 py-1 text-right font-medium">Trick Room</th>
            </tr>
          </thead>
          <tbody>
            {coverage.members.map((member) => (
              <tr key={member.pokemon} className="border-t border-[var(--line)]">
                <td className="px-2 py-1.5 text-white/80">{member.pokemon}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular-nums text-white/60">{member.battle_speed}</td>
                <Cell pct={member.natural_pct} />
                <Cell pct={member.tailwind_pct} />
                <Cell pct={member.trick_room_pct} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs leading-5 text-white/40">{coverage.note}</p>
    </div>
  );
}
