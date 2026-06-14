"use client";

import { useState } from "react";

import type { SlotDoctorGap, SlotDoctorResponse } from "@/lib/types";

type Props = {
  teamText: string;
  regulationId: string;
};

function GapCard({ gap }: { gap: SlotDoctorGap }) {
  return (
    <div className="space-y-3 rounded-lg border border-[var(--line)] p-4 sm:p-5">
      <div>
        <h4 className="text-sm font-semibold text-white/90">{gap.label}</h4>
        <p className="mt-1 text-xs leading-5 text-[var(--fg-muted)]">{gap.problem}</p>
      </div>

      {gap.move_swaps.length ? (
        <div className="space-y-1.5">
          <span className="text-[0.7rem] uppercase tracking-wide text-white/45">Move swaps</span>
          <ul className="space-y-1 text-sm text-white/80">
            {gap.move_swaps.map((swap) => (
              <li key={`${swap.member}-${swap.move}`}>
                <span className="text-[var(--positive)]">+ {swap.move}</span> on{" "}
                <span className="font-medium">{swap.member}</span>{" "}
                <span className="text-white/45">(legal)</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {gap.replacements.length ? (
        <div className="space-y-1.5">
          <span className="text-[0.7rem] uppercase tracking-wide text-white/45">Replacements</span>
          <ul className="space-y-1 text-sm text-white/75">
            {gap.replacements.map((replacement, index) => (
              <li key={`${replacement.species ?? "slot"}-${index}`}>
                {replacement.species ? (
                  <>
                    <span className="font-medium text-white/90">{replacement.species}</span>{" "}
                    <span className="text-white/45">— {replacement.note}</span>
                  </>
                ) : (
                  <span className="text-white/60">{replacement.note}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export function SlotDoctor({ teamText, regulationId }: Props) {
  const [result, setResult] = useState<SlotDoctorResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function diagnose() {
    if (!teamText.trim()) {
      setError("Build a team in the builder above first.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/slot-doctor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ teamText, regulationId }),
      });
      const payload = (await response.json()) as SlotDoctorResponse & { message?: string };
      if (!response.ok) {
        throw new Error(payload.message || "The slot doctor request failed.");
      }
      setResult(payload);
    } catch (caught) {
      setResult(null);
      setError(caught instanceof Error ? caught.message : "The slot doctor request failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <button
        type="button"
        onClick={diagnose}
        disabled={isLoading}
        className="rounded border border-white/25 bg-white/5 px-4 py-2 text-sm font-medium text-white/90 transition hover:border-white/50 disabled:opacity-40"
      >
        {isLoading ? "Diagnosing…" : "Diagnose & suggest fixes"}
      </button>
      {error ? <p className="text-xs text-[var(--negative)]">{error}</p> : null}

      {result ? (
        result.all_clear ? (
          <p className="text-sm text-[var(--positive)]">
            No critical gaps found — the team has answers to Trick Room, speed control, setup, and no glaring type
            hole.
          </p>
        ) : (
          <div className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-2">
              {result.gaps.map((gap) => (
                <GapCard key={gap.id} gap={gap} />
              ))}
            </div>
            <p className="text-xs leading-5 text-white/40">{result.note}</p>
          </div>
        )
      ) : null}
    </div>
  );
}
