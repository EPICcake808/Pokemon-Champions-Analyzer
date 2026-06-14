"use client";

import { useState } from "react";

import type { PreviewResponse } from "@/lib/types";

type Props = {
  myTeamText: string;
  regulationId: string;
};

function MemberChip({ name, isLead }: { name: string; isLead: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm ${
        isLead
          ? "border-[var(--accent)] text-white"
          : "border-[var(--line)] text-white/80"
      }`}
    >
      {isLead ? <span className="text-[0.6rem] font-semibold uppercase tracking-wide text-[var(--accent)]">Lead</span> : null}
      {name}
    </span>
  );
}

export function PreviewTrainer({ myTeamText, regulationId }: Props) {
  const [opponentText, setOpponentText] = useState("");
  const [result, setResult] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function scout() {
    if (!myTeamText.trim()) {
      setError("Build your own team in the builder above first.");
      return;
    }
    if (!opponentText.trim()) {
      setError("Paste the opponent's team to scout the matchup.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ myTeamText, opponentTeamText: opponentText, regulationId }),
      });
      const payload = (await response.json()) as PreviewResponse & { message?: string };
      if (!response.ok) {
        throw new Error(payload.message || "The preview request failed.");
      }
      setResult(payload);
    } catch (caught) {
      setResult(null);
      setError(caught instanceof Error ? caught.message : "The preview request failed.");
    } finally {
      setIsLoading(false);
    }
  }

  const bring = result?.recommended_bring;
  const leadSet = new Set(bring?.lead ?? []);

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <label className="block space-y-2">
          <span className="text-xs uppercase tracking-wide text-white/45">Opponent&apos;s six (Showdown paste)</span>
          <textarea
            value={opponentText}
            onChange={(event) => setOpponentText(event.target.value)}
            placeholder={"Paste the opponent's team export here…"}
            className="h-44 w-full resize-y border border-[var(--line)] bg-black/20 px-3 py-3 font-mono text-xs leading-5 text-white/85 outline-none focus:border-white/45"
          />
        </label>
        <button
          type="button"
          onClick={scout}
          disabled={isLoading}
          className="rounded border border-white/25 bg-white/5 px-4 py-2 text-sm font-medium text-white/90 transition hover:border-white/50 disabled:opacity-40"
        >
          {isLoading ? "Scouting…" : "Scout matchup"}
        </button>
        {error ? <p className="text-xs text-[var(--negative)]">{error}</p> : null}
      </div>

      {bring ? (
        <div className="space-y-6">
          <div className="space-y-3 rounded-lg border border-[var(--line)] p-4 sm:p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h4 className="text-sm font-semibold text-white/85">Recommended bring</h4>
              <span className="text-xs text-[var(--fg-muted)]">
                Covers {bring.covers}/{bring.opponent_count} offensively
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {bring.members.map((name) => (
                <MemberChip key={name} name={name} isLead={leadSet.has(name)} />
              ))}
            </div>
            <ul className="space-y-1.5 text-sm leading-6 text-white/75">
              {bring.reasons.map((reason) => (
                <li key={reason}>• {reason}</li>
              ))}
            </ul>
          </div>

          {result?.matchups?.length ? (
            <div className="-mx-2 overflow-x-auto">
              <table className="w-full min-w-[34rem] border-collapse text-left text-xs">
                <thead className="text-white/45">
                  <tr>
                    <th className="px-2 py-1 font-medium">Your Pokemon</th>
                    <th className="px-2 py-1 text-right font-medium">Speed</th>
                    <th className="px-2 py-1 text-right font-medium">Outspeeds</th>
                    <th className="px-2 py-1 font-medium">Reliably KOs</th>
                    <th className="px-2 py-1 font-medium">Threatened by</th>
                  </tr>
                </thead>
                <tbody>
                  {result.matchups.map((record) => (
                    <tr key={record.member} className="border-t border-[var(--line)] align-top">
                      <td className="px-2 py-1.5 text-white/85">
                        {bring.members.includes(record.member) ? (
                          <span className="font-medium text-white">{record.member}</span>
                        ) : (
                          <span className="text-white/55">{record.member}</span>
                        )}
                      </td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums text-white/70">{record.speed}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums text-white/70">
                        {record.outspeeds}/{record.opponent_count}
                      </td>
                      <td className="px-2 py-1.5 text-[var(--positive)]">
                        {record.ko_targets.length ? record.ko_targets.join(", ") : "—"}
                      </td>
                      <td className="px-2 py-1.5 text-[var(--negative)]">
                        {record.threatened_by.length ? record.threatened_by.join(", ") : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {result?.alternatives?.length ? (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-white/85">Alternative brings</h4>
              <ul className="space-y-1 text-sm text-white/70">
                {result.alternatives.map((alt) => (
                  <li key={alt.members.join("-")}>
                    {alt.members.join(", ")} <span className="text-white/40">— lead {alt.lead.join(" + ")}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
