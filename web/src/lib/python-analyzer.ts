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
  DamageCalcRequest,
  DamageCalcResponse,
  PokemonTeamAnalysis,
  PreviewRequest,
  PreviewResponse,
  RegulationCatalogPayload,
  SlotDoctorRequest,
  SlotDoctorResponse,
} from "@/lib/types";

const execFileAsync = promisify(execFile);

// Engine fallback regulation (mirrors the Python DEFAULT_REGULATION_ID): used when a
// request omits a regulation. The regulation the UI loads first is the catalog's
// default_regulation_id (CATALOG_DEFAULT_REGULATION_ID below), not this.
export const DEFAULT_REGULATION_ID = "champions_regulation_m_a";

// The regulation the web app loads first (current official format). Kept in sync with the
// Python CATALOG_DEFAULT_REGULATION_ID and surfaced by the catalog's default_regulation_id.
export const CATALOG_DEFAULT_REGULATION_ID = "champions_regulation_m_b";

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
          "The analyzer service is temporarily unavailable. Please try again in a moment.",
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
        "The analyzer service is temporarily unavailable. Please try again in a moment.",
    };
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }
}

function parseDamagePayload(stdout: string): DamageCalcResponse {
  const parsed = JSON.parse(stdout) as DamageCalcResponse & { error?: string };
  if (typeof parsed.error === "string") {
    throw new Error(parsed.error);
  }
  return parsed;
}

export async function runDamageCalc(request: DamageCalcRequest): Promise<DamageCalcResponse> {
  const body: DamageCalcRequest = {
    ...request,
    regulationId: request.regulationId ?? DEFAULT_REGULATION_ID,
  };

  if (shouldUseRemoteAnalyzerApi()) {
    const { payload, response } = await fetchAnalyzerApi<DamageCalcResponse & { detail?: string }>(
      "/api/damage",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    );
    if (!response.ok) {
      throw new Error(payload.detail || "The damage calculation request failed.");
    }
    return payload;
  }

  try {
    const stdout = await runPythonCli(["--damage-json", JSON.stringify(body)]);
    return parseDamagePayload(stdout);
  } catch (error) {
    const executionError = error as Error & { stdout?: string };
    if (executionError.stdout) {
      return parseDamagePayload(executionError.stdout);
    }
    throw error;
  }
}

function parsePreviewPayload(stdout: string): PreviewResponse {
  const parsed = JSON.parse(stdout) as PreviewResponse & { error?: string };
  if (typeof parsed.error === "string") {
    throw new Error(parsed.error);
  }
  return parsed;
}

export async function runPreview(request: PreviewRequest): Promise<PreviewResponse> {
  const body: PreviewRequest = {
    ...request,
    regulationId: request.regulationId ?? DEFAULT_REGULATION_ID,
  };

  if (shouldUseRemoteAnalyzerApi()) {
    const { payload, response } = await fetchAnalyzerApi<PreviewResponse & { detail?: string }>(
      "/api/preview",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    );
    if (!response.ok) {
      throw new Error(payload.detail || "The preview request failed.");
    }
    return payload;
  }

  try {
    const stdout = await runPythonCli(["--preview-json", JSON.stringify(body)]);
    return parsePreviewPayload(stdout);
  } catch (error) {
    const executionError = error as Error & { stdout?: string };
    if (executionError.stdout) {
      return parsePreviewPayload(executionError.stdout);
    }
    throw error;
  }
}

function parseSlotDoctorPayload(stdout: string): SlotDoctorResponse {
  const parsed = JSON.parse(stdout) as SlotDoctorResponse & { error?: string };
  if (typeof parsed.error === "string") {
    throw new Error(parsed.error);
  }
  return parsed;
}

export async function runSlotDoctor(request: SlotDoctorRequest): Promise<SlotDoctorResponse> {
  const body: SlotDoctorRequest = {
    ...request,
    regulationId: request.regulationId ?? DEFAULT_REGULATION_ID,
  };

  if (shouldUseRemoteAnalyzerApi()) {
    const { payload, response } = await fetchAnalyzerApi<SlotDoctorResponse & { detail?: string }>(
      "/api/slot-doctor",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    );
    if (!response.ok) {
      throw new Error(payload.detail || "The slot doctor request failed.");
    }
    return payload;
  }

  try {
    const stdout = await runPythonCli(["--slot-doctor-json", JSON.stringify(body)]);
    return parseSlotDoctorPayload(stdout);
  } catch (error) {
    const executionError = error as Error & { stdout?: string };
    if (executionError.stdout) {
      return parseSlotDoctorPayload(executionError.stdout);
    }
    throw error;
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
      return "# Changelog\n\nThe release notes are temporarily unavailable. Please check back later.";
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
