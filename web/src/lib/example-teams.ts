import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

import { DEFAULT_REGULATION_ID } from "@/lib/python-analyzer";
import { resolveRepositoryRoot } from "@/lib/runtime-paths";
import type { ExampleTeam } from "@/lib/types";

const REPO_ROOT = resolveRepositoryRoot();
const EXAMPLES_DIR = path.join(REPO_ROOT, "examples");

const FEATURED_EXAMPLES: Array<Omit<ExampleTeam, "teamText"> & { fileName: string }> = [
  {
    slug: "sample-team",
    fileName: "sample_team.txt",
    title: "Curated Sample",
    note: "Rain Tailwind shell with layered support turns and flexible speed control.",
    regulationId: DEFAULT_REGULATION_ID,
  },
  {
    slug: "hyper-offense",
    fileName: "realistic_hyper_offense_team.txt",
    title: "Hyper Offense",
    note: "Fast hazard pressure built to win short damage races.",
    regulationId: DEFAULT_REGULATION_ID,
  },
  {
    slug: "trick-room",
    fileName: "realistic_trick_room_team.txt",
    title: "Trick Room",
    note: "Slow-mode pressure calibrated to current Regulation M-A Trick Room shells.",
    regulationId: DEFAULT_REGULATION_ID,
  },
  {
    slug: "perish-trap",
    fileName: "realistic_perish_trap_team.txt",
    title: "Perish Trap",
    note: "Trap-centric routing built around forced endgames and protected clocks.",
    regulationId: DEFAULT_REGULATION_ID,
  },
  {
    slug: "master-ball",
    fileName: "championsmeta_master_ball_ready_team.txt",
    title: "Master Ball Ready",
    note: "Tournament hybrid pulled from live Regulation M-A play with mixed speed modes.",
    regulationId: DEFAULT_REGULATION_ID,
  },
  {
    slug: "mega-scizor",
    fileName: "championsmeta_mega_scizor_team.txt",
    title: "Mega Scizor",
    note: "Modern balance shell with Tailwind support, priority, and mode-flex lines.",
    regulationId: DEFAULT_REGULATION_ID,
  },
];

export async function getFeaturedExampleTeams(): Promise<ExampleTeam[]> {
  return Promise.all(
    FEATURED_EXAMPLES.map(async ({ fileName, ...example }) => ({
      ...example,
      teamText: await readFile(path.join(EXAMPLES_DIR, fileName), "utf8"),
    })),
  );
}
