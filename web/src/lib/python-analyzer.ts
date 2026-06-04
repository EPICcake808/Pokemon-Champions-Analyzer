import "server-only";

import { execFile } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";

import { resolvePythonExecutable, resolveRepositoryRoot } from "@/lib/runtime-paths";
import type {
  AnalyzeRoutePayload,
  BuilderMoveDetails,
  BuilderSpeciesOptions,
  ChangelogRoutePayload,
  PokemonTeamAnalysis,
  RegulationCatalogPayload,
} from "@/lib/types";

const execFileAsync = promisify(execFile);

export const DEFAULT_REGULATION_ID = "champions_regulation_m_a";

const REPO_ROOT = resolveRepositoryRoot();
const PYTHON_EXECUTABLE = resolvePythonExecutable();
const ANALYZER_API_BASE_URL = process.env.POKEMON_ANALYZER_API_BASE_URL?.trim() || null;
const FORCE_REMOTE_ANALYZER_API = process.env.POKEMON_ANALYZER_FORCE_REMOTE_API?.trim() === "1";

function shouldUseRemoteAnalyzerApi() {
  if (!ANALYZER_API_BASE_URL) {
    return false;
  }

  return process.env.NODE_ENV === "production" || FORCE_REMOTE_ANALYZER_API;
}

function buildAnalyzerApiUrl(pathname: string, searchParams?: Record<string, string | boolean | undefined>) {
  const baseUrl = ANALYZER_API_BASE_URL;
  if (!baseUrl || !shouldUseRemoteAnalyzerApi()) {
    return null;
  }

  const normalizedBaseUrl = baseUrl.endsWith("/")
    ? baseUrl
    : `${baseUrl}/`;
  const url = new URL(pathname.replace(/^\//, ""), normalizedBaseUrl);
  for (const [key, value] of Object.entries(searchParams ?? {})) {
    if (value === undefined) {
      continue;
    }

    url.searchParams.set(key, typeof value === "boolean" ? String(value) : value);
  }
  return url;
}

async function fetchAnalyzerApi<T>(
  pathname: string,
  init?: RequestInit,
  searchParams?: Record<string, string | boolean | undefined>,
): Promise<{ payload: T; response: Response }> {
  const url = buildAnalyzerApiUrl(pathname, searchParams);
  if (!url) {
    throw new Error("The analyzer API base URL is not configured.");
  }

  const response = await fetch(url, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const payload = (await response.json()) as T;
  return {
    payload,
    response,
  };
}

async function runPythonCli(args: string[]): Promise<string> {
  const { stdout } = await execFileAsync(
    PYTHON_EXECUTABLE,
    ["-m", "pokemon_team_analyzer", ...args],
    {
      cwd: REPO_ROOT,
      maxBuffer: 12 * 1024 * 1024,
    },
  );

  return stdout;
}

function parseAnalyzerPayload(stdout: string): AnalyzeRoutePayload {
  const parsed = JSON.parse(stdout) as PokemonTeamAnalysis & {
    error?: string;
    legality?: AnalyzeRoutePayload extends { legality?: infer T } ? T : never;
  };

  if (typeof parsed.error === "string") {
    return {
      ok: false,
      message: parsed.error,
      legality: parsed.legality,
    };
  }

  return {
    ok: true,
    analysis: parsed,
  };
}

export async function runPokemonAnalyzer(
  teamText: string,
  regulationId = DEFAULT_REGULATION_ID,
): Promise<AnalyzeRoutePayload> {
  if (!teamText.trim()) {
    return {
      ok: false,
      message: "Paste a Pokemon Showdown import before running the analyzer.",
    };
  }

  if (shouldUseRemoteAnalyzerApi()) {
    try {
      const { payload, response } = await fetchAnalyzerApi<AnalyzeRoutePayload>("/api/analyze", {
        method: "POST",
        body: JSON.stringify({
          teamText,
          regulationId,
        }),
      });

      if (!response.ok && payload.ok) {
        return {
          ok: false,
          message: "The analyzer API returned an unexpected response.",
        };
      }

      return payload;
    } catch {
      return {
        ok: false,
        message:
          "The Next.js app could not reach the analyzer API. Set POKEMON_ANALYZER_API_BASE_URL to the deployed Python analyzer service URL.",
      };
    }
  }

  const tempDir = await mkdtemp(path.join(tmpdir(), "pokemon-champions-analyzer-"));
  const tempFile = path.join(tempDir, "team.txt");

  try {
    await writeFile(tempFile, teamText, "utf8");

    const stdout = await runPythonCli([tempFile, "--json", "--regulation", regulationId]);

    return parseAnalyzerPayload(stdout);
  } catch (error) {
    const executionError = error as Error & { stdout?: string };
    if (executionError.stdout) {
      try {
        return parseAnalyzerPayload(executionError.stdout);
      } catch {
        // Fall through to the generic error below.
      }
    }

    return {
      ok: false,
      message:
        "The Next.js app could not reach the local Python analyzer. Make sure the repo root is available, `python3` exists, or set POKEMON_ANALYZER_REPO_ROOT and POKEMON_ANALYZER_PYTHON explicitly.",
    };
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }
}

export async function getRegulationCatalog(): Promise<RegulationCatalogPayload> {
  if (shouldUseRemoteAnalyzerApi()) {
    const { payload, response } = await fetchAnalyzerApi<RegulationCatalogPayload>("/api/catalog", undefined, {
      includeRules: true,
    });
    if (!response.ok) {
      throw new Error("The analyzer API could not return the regulation catalog.");
    }
    return payload;
  }

  const stdout = await runPythonCli(["--catalog-json", "--include-rules"]);
  return JSON.parse(stdout) as RegulationCatalogPayload;
}

export async function getHostedChangelog(): Promise<string | null> {
  if (!ANALYZER_API_BASE_URL) {
    if (process.env.NODE_ENV === "production") {
      return "# Changelog\n\nThe hosted web app is missing POKEMON_ANALYZER_API_BASE_URL, so it cannot load the live changelog from the analyzer service.";
    }

    return null;
  }

  if (!shouldUseRemoteAnalyzerApi()) {
    return null;
  }

  try {
    const { payload, response } = await fetchAnalyzerApi<ChangelogRoutePayload & { detail?: string }>("/api/changelog");
    if (!response.ok || typeof payload.content !== "string" || !payload.content.trim()) {
      throw new Error(payload.detail ?? "The analyzer API returned an invalid changelog response.");
    }

    return payload.content;
  } catch {
    return "# Changelog\n\nThe hosted web app could not load the latest changelog from the analyzer service right now. Retry in a moment.";
  }
}

function parseBuilderSpeciesPayload(stdout: string): BuilderSpeciesOptions {
  const parsed = JSON.parse(stdout) as BuilderSpeciesOptions & { error?: string };
  if (typeof parsed.error === "string") {
    throw new Error(parsed.error);
  }

  return parsed;
}

function parseBuilderMovePayload(stdout: string): BuilderMoveDetails {
  const parsed = JSON.parse(stdout) as BuilderMoveDetails & { error?: string };
  if (typeof parsed.error === "string") {
    throw new Error(parsed.error);
  }

  return parsed;
}

export async function getBuilderSpeciesOptions(
  speciesName: string,
  regulationId = DEFAULT_REGULATION_ID,
): Promise<BuilderSpeciesOptions> {
  if (shouldUseRemoteAnalyzerApi()) {
    const { payload, response } = await fetchAnalyzerApi<BuilderSpeciesOptions & { detail?: string }>(
      "/api/builder-species",
      undefined,
      {
        species: speciesName,
        regulationId,
      },
    );
    if (!response.ok) {
      throw new Error(payload.detail || "The builder species request failed.");
    }
    return payload;
  }

  try {
    const stdout = await runPythonCli(["--builder-species-json", speciesName, "--regulation", regulationId]);
    return parseBuilderSpeciesPayload(stdout);
  } catch (error) {
    const executionError = error as Error & { stdout?: string };
    if (executionError.stdout) {
      return parseBuilderSpeciesPayload(executionError.stdout);
    }
    throw error;
  }
}

export async function getBuilderMoveDetails(moveName: string): Promise<BuilderMoveDetails> {
  if (shouldUseRemoteAnalyzerApi()) {
    const { payload, response } = await fetchAnalyzerApi<BuilderMoveDetails & { detail?: string }>(
      "/api/builder-move",
      undefined,
      {
        move: moveName,
      },
    );
    if (!response.ok) {
      throw new Error(payload.detail || "The builder move request failed.");
    }
    return payload;
  }

  try {
    const stdout = await runPythonCli(["--builder-move-json", moveName]);
    return parseBuilderMovePayload(stdout);
  } catch (error) {
    const executionError = error as Error & { stdout?: string };
    if (executionError.stdout) {
      return parseBuilderMovePayload(executionError.stdout);
    }
    throw error;
  }
}
