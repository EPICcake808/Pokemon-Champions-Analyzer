import "server-only";

import { existsSync } from "node:fs";
import path from "node:path";

function isRepositoryRoot(candidatePath: string): boolean {
  return (
    existsSync(path.join(candidatePath, "examples"))
    && existsSync(path.join(candidatePath, "web"))
  );
}

export function resolveRepositoryRoot(): string {
  const configuredRoot = process.env.POKEMON_ANALYZER_REPO_ROOT;
  const currentWorkingDirectory = process.cwd();
  const candidates = [
    configuredRoot,
    currentWorkingDirectory,
    path.resolve(currentWorkingDirectory, ".."),
    path.resolve(currentWorkingDirectory, "../.."),
  ]
    .filter((candidate): candidate is string => Boolean(candidate))
    .map((candidate) => path.resolve(candidate));

  for (const candidate of new Set(candidates)) {
    if (isRepositoryRoot(candidate)) {
      return candidate;
    }
  }

  return path.resolve(currentWorkingDirectory, "..");
}

export function resolvePythonExecutable(): string {
  return process.env.POKEMON_ANALYZER_PYTHON?.trim() || "python3";
}
