import "server-only";

import { formatLabel, parseShowdownTeam } from "@/lib/showdown";
import type { PublishedMetaSnapshotDocument } from "@/lib/meta-snapshots";
import type { AnalyzeRoutePayload, PokemonTeamAnalysis } from "@/lib/types";

type LiveSourceKind = "rss" | "youtube-search" | "html-page" | "reddit-search";

type LiveSourceDefinition = {
  id: string;
  label: string;
  kind: LiveSourceKind;
  url: string;
  weight: number;
  maxItems?: number;
  requiresDeepDiscovery?: boolean;
};

type LiveEvidenceItem = {
  sourceId: string;
  sourceLabel: string;
  title: string;
  snippet: string;
  url: string;
  publisher: string;
  publishedAt: string | null;
  weight: number;
};

type CandidateExportPage = {
  item: LiveEvidenceItem;
  url: string;
  body: string;
};

type DiscoveredTeamExport = {
  sourceItem: LiveEvidenceItem;
  teamText: string;
  analysis: PokemonTeamAnalysis;
};

type LiveIngestionFailure = {
  label: string;
  reason: string;
};

type LiveEvidenceCollection = {
  items: LiveEvidenceItem[];
  succeededSources: string[];
  failedSourceCount: number;
  failedSources: LiveIngestionFailure[];
};

type SnapshotDescriptor = {
  snapshot: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number];
  labelPhrase: string;
  keyCorePhrases: string[];
  pokemonPhrases: string[];
};

type SpeciesPhraseIndexEntry = {
  token: string;
  phrase: string;
};

type ArticleRosterSection = {
  label: string;
  text: string;
};

type ExtractedArticleRoster = {
  sourceItem: LiveEvidenceItem;
  label: string;
  speciesTokens: string[];
  sourceText: string;
};

type LiveDiscoveryDiagnostics = {
  skippedReason: string | null;
  candidatePagesFetched: string[];
  candidatePageFailures: LiveIngestionFailure[];
  exportPages: string[];
  rosterPages: string[];
  analyzerFailures: LiveIngestionFailure[];
};

type LiveDiscoveryResult = {
  discoveredSnapshots: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"];
  rosterSnapshots: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"];
  rosterEvidenceItems: LiveEvidenceItem[];
  diagnostics: LiveDiscoveryDiagnostics;
};

type AnalyzeTeamExportResult = {
  analysis: PokemonTeamAnalysis | null;
  reason: string | null;
};

type LiveEvidenceSourceMode = "default" | "deep-only" | "all";

type LiveSignalEnrichmentOptions = {
  deepDiscoveryEnabled?: boolean;
  sourceMode?: LiveEvidenceSourceMode;
  runtimeBudgetMs?: number;
};

type AutomatedMetaSnapshotBuildOptions = {
  sourceMode?: LiveEvidenceSourceMode;
  runtimeBudgetMs?: number;
  regulationId?: string;
  seedDocuments?: PublishedMetaSnapshotDocument[];
};

type AutomatedSnapshotCandidate = {
  snapshot: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number];
  sourceItem: LiveEvidenceItem;
  sourceText: string;
  kind: "export" | "roster";
};

const LIVE_SOURCE_HEADERS = {
  Accept: "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
  "User-Agent": "pokemon-champions-analyzer-live-ingestion/0.2.1",
};

const LIVE_SOURCE_TIMEOUT_MS = 7_000;
const EXPORT_PAGE_TIMEOUT_MS = 2_500;
const ANALYZE_EXPORT_TIMEOUT_MS = 18_000;
const LIVE_SOURCE_LABEL = "Pokemon Champions Analyzer live-source Regulation M-A meta board";
const MAX_EXPORT_SOURCE_PAGES = 10;
const MAX_EXTRACTED_TEAMS = 4;
const MAX_DIAGNOSTIC_ITEMS = 3;
const NOTE_MAX_LENGTH = 400;
const DISCOVERY_RUNTIME_BUDGET_MS = 20_000;
const BROAD_MIX_KEYS = ["hyper_offense", "bulky_offense", "balance", "semi_stall", "stall", "trick_room"] as const;
const EXPORT_LINK_PATTERN = /https?:\/\/(?:www\.)?pokepast\.es\/[A-Za-z0-9]+(?:\/raw)?/gi;
const RESULT_SIGNAL_TERMS = [
  "winner",
  "won",
  "champion",
  "championship",
  "top cut",
  "top 8",
  "top 16",
  "top 32",
  "finalist",
  "runner up",
  "semifinal",
  "quarterfinal",
  "results",
  "standings",
  "team report",
  "tournament report",
  "regional",
  "nationals",
  "international",
  "qualifier",
  "invitational",
  "deep run",
  "tournament",
];
const GUIDE_PUBLISHER_TERMS = [
  "gamesradar",
  "keengamer",
  "phrasemaker",
  "thegamer",
  "ign",
  "operation sports",
  "pocket tactics",
  "nintendo everything",
];
const GUIDE_NOISE_TERMS = [
  " guide ",
  " how to ",
  " starter team",
  " starter teams",
  " all starter teams",
  " all pokemon list",
  " pokemon list",
  " replica team",
  " replica teams",
  " all codes",
  " recruit first",
  " victory points",
  " leaked ",
];

const GENERIC_SEARCH_TERMS = new Set([
  "balance",
  "bulky offense",
  "hyper offense",
  "pokemon champions",
  "regulation m-a",
  "regulation m a",
  "current meta",
  "the current meta",
]);

const DEEP_DISCOVERY_TERMS = [
  "team",
  "teams",
  "replica",
  "gallery",
  "roster",
  "code",
  "rental",
  "sample",
  "build",
  "report",
  "recap",
  "featured",
  "pokepast",
  "paste",
  "showdown",
];

const ARTICLE_ROSTER_MIN_SPECIES_COUNT = 5;
const MAX_AUTOMATED_SNAPSHOTS = 12;
const MIN_AUTOMATED_SNAPSHOTS_FOR_REBUILD = 3;
export const AUTOMATED_META_SOURCE_LABEL = "Pokemon Champions Analyzer automated live-source Regulation M-A meta board";
export const AUTOMATED_META_SOURCE_URL = "live-ingestion://automated-meta-snapshot";

const DEFAULT_LIVE_SOURCES: LiveSourceDefinition[] = [
  {
    id: "google-news-first-tournament",
    label: "Google News: Pokemon Champions first tournament",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=%22Pokemon+Champions%22+%22first+tournament%22",
    weight: 1,
    maxItems: 12,
  },
  {
    id: "google-news-most-used",
    label: "Google News: Pokemon Champions most used",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=%22Pokemon+Champions%22+%22most+used%22",
    weight: 0.98,
    maxItems: 12,
  },
  {
    id: "google-news-tournament-results",
    label: "Google News: Pokemon Champions tournament results",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=%22Pokemon+Champions%22+%22tournament+results%22",
    weight: 0.96,
    maxItems: 12,
  },
  {
    id: "google-news-team-reports",
    label: "Google News: Pokemon Champions team reports",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=%22Pokemon+Champions%22+%22team+report%22",
    weight: 0.94,
    maxItems: 12,
    requiresDeepDiscovery: true,
  },
  {
    id: "google-news-tournament-reports",
    label: "Google News: Pokemon Champions tournament reports",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=%22Pokemon+Champions%22+%22tournament+report%22",
    weight: 0.94,
    maxItems: 12,
    requiresDeepDiscovery: true,
  },
  {
    id: "google-news-most-used-tournament",
    label: "Google News: Pokemon Champions most used tournament",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=%22Pokemon+Champions%22+%22most-used%22+%22tournament%22",
    weight: 0.92,
    maxItems: 12,
    requiresDeepDiscovery: true,
  },
];

function decodeHtmlEntities(value: string) {
  return value
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&#x([\da-f]+);/gi, (_match, hex) => String.fromCodePoint(Number.parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_match, dec) => String.fromCodePoint(Number.parseInt(dec, 10)))
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&nbsp;/g, " ");
}

function stripHtml(value: string) {
  return decodeHtmlEntities(value).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function normalizeSearchText(value: string) {
  return stripHtml(value)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9+ ]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function hasChampionsContext(text: string) {
  const normalizedText = normalizeSearchText(text);
  return normalizedText.includes("pokemon champions") || normalizedText.includes("regulation m a");
}

function hasTournamentResultSignal(text: string) {
  const normalizedText = normalizeSearchText(text);
  return hasChampionsContext(normalizedText)
    && RESULT_SIGNAL_TERMS.some((term) => normalizedText.includes(term));
}

function isGuidePublisher(item: LiveEvidenceItem) {
  const publisherText = normalizeSearchText(`${item.publisher} ${hostnameForUrl(item.url)}`);
  return GUIDE_PUBLISHER_TERMS.some((term) => publisherText.includes(term));
}

function hasGuideNoise(text: string) {
  const paddedText = ` ${normalizeSearchText(text)} `;
  return GUIDE_NOISE_TERMS.some((term) => paddedText.includes(term));
}

function isTournamentEvidenceItem(item: LiveEvidenceItem) {
  const text = buildEvidenceText(item);
  return hasTournamentResultSignal(text)
    && !isGuidePublisher(item)
    && !hasGuideNoise(`${item.title} ${item.snippet}`);
}

function decodeJsonEscapes(value: string) {
  return value
    .replace(/\\u([\da-fA-F]{4})/g, (_match, hex) => String.fromCharCode(Number.parseInt(hex, 16)))
    .replace(/\\n/g, " ")
    .replace(/\\\//g, "/")
    .replace(/\\"/g, '"')
    .replace(/\\&/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeFetchedPageBody(body: string) {
  return body.includes("\\u003c") || body.includes("\\u003e") ? decodeJsonEscapes(body) : body;
}

function extractTagText(payload: string, tagName: string) {
  const match = payload.match(new RegExp(`<${tagName}\\b[^>]*>([\\s\\S]*?)</${tagName}>`, "i"));
  return match ? stripHtml(match[1]) : "";
}

function extractMetaContent(payload: string, metaName: string) {
  const directMatch = payload.match(
    new RegExp(
      `<meta[^>]+(?:name|property)=["']${metaName}["'][^>]+content=["']([^"']+)["'][^>]*>`,
      "i",
    ),
  );
  if (directMatch) {
    return stripHtml(directMatch[1]);
  }

  const reverseMatch = payload.match(
    new RegExp(
      `<meta[^>]+content=["']([^"']+)["'][^>]+(?:name|property)=["']${metaName}["'][^>]*>`,
      "i",
    ),
  );
  return reverseMatch ? stripHtml(reverseMatch[1]) : "";
}

function renderSpeciesToken(speciesToken: string) {
  if (speciesToken.endsWith("-mega-x")) {
    return `Mega ${speciesToken.slice(0, -"-mega-x".length).replaceAll("-", " ")} X`;
  }
  if (speciesToken.endsWith("-mega-y")) {
    return `Mega ${speciesToken.slice(0, -"-mega-y".length).replaceAll("-", " ")} Y`;
  }
  if (speciesToken.endsWith("-mega")) {
    return `Mega ${speciesToken.slice(0, -"-mega".length).replaceAll("-", " ")}`;
  }
  if (speciesToken.endsWith("-male")) {
    return `${speciesToken.slice(0, -"-male".length).replaceAll("-", " ")} M`;
  }
  if (speciesToken.endsWith("-female")) {
    return `${speciesToken.slice(0, -"-female".length).replaceAll("-", " ")} F`;
  }
  if (speciesToken.endsWith("-alola")) {
    return `Alolan ${speciesToken.slice(0, -"-alola".length).replaceAll("-", " ")}`;
  }
  if (speciesToken.endsWith("-hisui")) {
    return `Hisuian ${speciesToken.slice(0, -"-hisui".length).replaceAll("-", " ")}`;
  }
  return speciesToken.replaceAll("-", " ");
}

function baseSpeciesPhrase(speciesToken: string) {
  return speciesToken
    .replace(/-mega(?:-[xy])?$/, "")
    .replace(/-(male|female|alola|hisui)$/, "")
    .replaceAll("-", " ");
}

function uniqueStrings(values: string[]) {
  return [...new Set(values.filter(Boolean))];
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function truncateNote(note: string) {
  const trimmed = note.trim();
  if (trimmed.length <= NOTE_MAX_LENGTH) {
    return trimmed;
  }
  return `${trimmed.slice(0, NOTE_MAX_LENGTH - 1).trimEnd()}…`;
}

function hostnameForUrl(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./i, "");
  } catch {
    return "";
  }
}

function extractNearestHeadingLabel(body: string, beforeIndex: number) {
  const prefix = body.slice(Math.max(0, beforeIndex - 700), beforeIndex);
  const headingMatches = [...prefix.matchAll(/<h[1-4][^>]*>([\s\S]*?)<\/h[1-4]>/gi)];
  if (!headingMatches.length) {
    return "";
  }
  const nearestHeading = headingMatches[headingMatches.length - 1];
  return stripHtml(nearestHeading[1]);
}

function buildSpeciesPhraseIndex(speciesTokens: string[]) {
  return uniqueStrings(speciesTokens)
    .flatMap((token) => {
      const phrases = uniqueStrings([
        normalizeSearchText(renderSpeciesToken(token)),
        normalizeSearchText(baseSpeciesPhrase(token)),
      ]).filter((phrase) => phrase.length >= 4 && !GENERIC_SEARCH_TERMS.has(phrase));
      return phrases.map((phrase) => ({ token, phrase }));
    })
    .sort((left, right) => right.phrase.length - left.phrase.length);
}

function buildDocumentSpeciesPhraseIndex(document: PublishedMetaSnapshotDocument): SpeciesPhraseIndexEntry[] {
  const speciesTokens = uniqueStrings(document.tournamentTeamSnapshots.flatMap((snapshot) => snapshot.key_pokemon));
  return buildSpeciesPhraseIndex(speciesTokens);
}

async function fetchRegulationSpeciesPhraseIndex(regulationId: string) {
  const analyzerApiBaseUrl = resolveAnalyzerApiBaseUrl();
  if (!analyzerApiBaseUrl) {
    return [] as SpeciesPhraseIndexEntry[];
  }

  const response = await fetch(`${analyzerApiBaseUrl}/api/catalog?includeRules=true`, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "User-Agent": LIVE_SOURCE_HEADERS["User-Agent"],
    },
    signal: AbortSignal.timeout(LIVE_SOURCE_TIMEOUT_MS),
  });
  if (!response.ok) {
    return [] as SpeciesPhraseIndexEntry[];
  }

  const payload = await response.json() as {
    default_regulation_id?: string;
    regulations?: Array<{
      id?: string;
      eligible_species?: string[];
      allowed_mega_evolutions?: string[];
    }>;
  };
  const resolvedRegulationId = regulationId || payload.default_regulation_id || "champions_regulation_m_a";
  const regulation = payload.regulations?.find((entry) => entry.id === resolvedRegulationId);
  if (!regulation) {
    return [] as SpeciesPhraseIndexEntry[];
  }

  const speciesTokens = uniqueStrings([
    ...(regulation.eligible_species ?? []),
    ...(regulation.allowed_mega_evolutions ?? []),
  ].map((speciesName) => normalizeSpeciesToken(speciesName)).filter(Boolean));
  return buildSpeciesPhraseIndex(speciesTokens);
}

function inferRosterSectionSignal(text: string) {
  const normalizedText = normalizeSearchText(text);
  return hasTournamentResultSignal(normalizedText)
    && DEEP_DISCOVERY_TERMS.some((term) => normalizedText.includes(term));
}

function inferModesFromText(text: string) {
  const normalizedText = normalizeSearchText(text);
  const inferredModes: string[] = [];

  const pushMode = (modeName: string) => {
    if (!inferredModes.includes(modeName)) {
      inferredModes.push(modeName);
    }
  };

  if (normalizedText.includes("rain") && normalizedText.includes("tailwind")) {
    pushMode("rain_tailwind");
  }
  if (normalizedText.includes("sun") && normalizedText.includes("tailwind")) {
    pushMode("sun_tailwind");
  }
  if (normalizedText.includes("sand") && normalizedText.includes("tailwind")) {
    pushMode("sand_tailwind");
  }
  if (normalizedText.includes("snow") && normalizedText.includes("tailwind")) {
    pushMode("snow_tailwind");
  }
  if (normalizedText.includes("tailwind")) {
    pushMode("tailwind");
  }
  if (normalizedText.includes("trick room") || normalizedText.includes("room")) {
    pushMode("trick_room");
  }
  if (normalizedText.includes("rain")) {
    pushMode("rain");
  }
  if (normalizedText.includes("sun")) {
    pushMode("sun");
  }
  if (normalizedText.includes("sand")) {
    pushMode("sand");
  }
  if (normalizedText.includes("snow")) {
    pushMode("snow");
  }
  if (normalizedText.includes("electric terrain")) {
    pushMode("electric_terrain");
  }
  if (normalizedText.includes("grassy terrain")) {
    pushMode("grassy_terrain");
  }
  if (normalizedText.includes("misty terrain")) {
    pushMode("misty_terrain");
  }
  if (normalizedText.includes("psychic terrain")) {
    pushMode("psychic_terrain");
  }

  return inferredModes.length ? inferredModes : ["dual_mode"];
}

function inferBroadMixFromModes(modes: string[]): Record<string, number> {
  if (modes.includes("trick_room")) {
    return { trick_room: 1 };
  }
  if (modes.some((mode) => mode.includes("tailwind"))) {
    return { hyper_offense: 0.55, bulky_offense: 0.3, balance: 0.15 };
  }
  if (modes.some((mode) => ["rain", "sun", "sand", "snow"].includes(mode))) {
    return { bulky_offense: 0.45, balance: 0.35, hyper_offense: 0.2 };
  }
  return { balance: 0.5, bulky_offense: 0.3, hyper_offense: 0.2 };
}

function strongestResultBoost(sourceText: string) {
  if (sourceText.includes("winner") || sourceText.includes("champion") || sourceText.includes("championship") || sourceText.includes("won")) {
    return 0.25;
  }
  if (sourceText.includes("top 8") || sourceText.includes("top 16") || sourceText.includes("top 32") || sourceText.includes("top cut") || sourceText.includes("finalist") || sourceText.includes("runner up")) {
    return 0.18;
  }
  if (sourceText.includes("regional") || sourceText.includes("nationals") || sourceText.includes("international") || sourceText.includes("qualifier") || sourceText.includes("invitational")) {
    return 0.14;
  }
  return 0.08;
}

function extractSpeciesTokensFromText(text: string, phraseIndex: SpeciesPhraseIndexEntry[]) {
  const normalizedText = normalizeSearchText(text);
  if (!normalizedText) {
    return [] as string[];
  }

  const matches: Array<{ token: string; index: number; length: number }> = [];
  for (const entry of phraseIndex) {
    const pattern = new RegExp(`(^| )${escapeRegExp(entry.phrase)}(?= |$)`, "g");
    for (const match of normalizedText.matchAll(pattern)) {
      matches.push({
        token: entry.token,
        index: match.index ?? 0,
        length: entry.phrase.length,
      });
    }
  }

  const consumedRanges: Array<{ start: number; end: number }> = [];
  const tokens: string[] = [];
  const seenTokens = new Set<string>();
  for (const match of matches.sort((left, right) => left.index - right.index || right.length - left.length)) {
    if (seenTokens.has(match.token)) {
      continue;
    }

    const start = match.index;
    const end = match.index + match.length;
    const overlapsExistingRange = consumedRanges.some((range) => start < range.end && end > range.start);
    if (overlapsExistingRange) {
      continue;
    }

    consumedRanges.push({ start, end });
    seenTokens.add(match.token);
    tokens.push(match.token);
  }

  return tokens;
}

function extractArticleRosterSections(body: string) {
  const listSections = [...body.matchAll(/<(?:ul|ol)[^>]*>([\s\S]*?)<\/(?:ul|ol)>/gi)]
    .map((match) => {
      const items = [...match[1].matchAll(/<li[^>]*>([\s\S]*?)<\/li>/gi)]
        .map((itemMatch) => stripHtml(itemMatch[1]))
        .filter((item) => item.length >= 3);
      return {
        label: extractNearestHeadingLabel(body, match.index ?? 0),
        text: items.join("\n"),
      } satisfies ArticleRosterSection;
    })
    .filter((section) => section.text.length >= 12);

  const headingSections = [...body.matchAll(/<h[1-4][^>]*>([\s\S]*?)<\/h[1-4]>([\s\S]*?)(?=<h[1-4]\b|$)/gi)]
    .map((match) => ({
      label: stripHtml(match[1]),
      text: htmlToTextWithLineBreaks(match[2]),
    }))
    .filter((section) => section.label.length >= 3 || section.text.length >= 20);

  const tableSections = [...body.matchAll(/<table\b[^>]*>([\s\S]*?)<\/table>/gi)]
    .flatMap((tableMatch) => [...tableMatch[1].matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)]
      .map((rowMatch) => {
        const cells = [...rowMatch[1].matchAll(/<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]>/gi)]
          .map((cellMatch) => htmlToTextWithLineBreaks(cellMatch[1]).trim())
          .filter(Boolean);
        const [label = "", ...details] = cells;
        return {
          label,
          text: details.join("\n").trim(),
        } satisfies ArticleRosterSection;
      })
      .filter((section) => section.label.length >= 3 && section.text.length >= 20));

  const paragraphSections = htmlToTextWithLineBreaks(body)
    .split(/\n{2,}/g)
    .map((paragraph) => ({
      label: "",
      text: paragraph.trim(),
    }))
    .filter((section) => section.text.length >= 24 && section.text.length <= 900);

  return [...new Map([...listSections, ...headingSections, ...tableSections, ...paragraphSections].map((section) => [
    `${normalizeSearchText(section.label)}|${normalizeSearchText(section.text).slice(0, 160)}`,
    section,
  ])).values()];
}

function extractArticleRosters(
  page: CandidateExportPage,
  phraseIndex: SpeciesPhraseIndexEntry[],
): ExtractedArticleRoster[] {
  if (!phraseIndex.length) {
    return [];
  }

  const sectionCandidates = extractArticleRosterSections(page.body).filter((section) =>
    inferRosterSectionSignal(`${page.item.title} ${section.label} ${section.text.slice(0, 280)}`),
  );

  const rosters = new Map<string, ExtractedArticleRoster>();
  for (const section of sectionCandidates) {
    const sectionBlocks = uniqueStrings([section.text, ...section.text.split(/\n{2,}/g)]);
    for (const block of sectionBlocks) {
      const speciesTokens = extractSpeciesTokensFromText(block, phraseIndex);
      if (speciesTokens.length < ARTICLE_ROSTER_MIN_SPECIES_COUNT || speciesTokens.length > 6) {
        continue;
      }

      const rosterKey = speciesTokens.slice().sort().join("|");
      if (rosters.has(rosterKey)) {
        continue;
      }

      rosters.set(rosterKey, {
        sourceItem: page.item,
        label: section.label || page.item.title,
        speciesTokens,
        sourceText: normalizeSearchText(`${page.item.title} ${section.label} ${block}`),
      });
    }
  }

  return [...rosters.values()].slice(0, 3);
}

function buildRosterEvidenceItem(roster: ExtractedArticleRoster): LiveEvidenceItem {
  const renderedSpecies = roster.speciesTokens.map((token) => formatLabel(token)).join(", ");
  return {
    sourceId: `${roster.sourceItem.sourceId}-roster`,
    sourceLabel: `${roster.sourceItem.sourceLabel} roster`,
    title: roster.label,
    snippet: `Article roster: ${renderedSpecies}`,
    url: roster.sourceItem.url,
    publisher: roster.sourceItem.publisher,
    publishedAt: roster.sourceItem.publishedAt,
    weight: roundToTwo(clamp(roster.sourceItem.weight * 0.92, 0, 2)),
  };
}

function buildRosterSnapshot(roster: ExtractedArticleRoster): PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number] {
  const baseSignal = buildSignalStrength(roster.sourceItem);
  const resultBoost = strongestResultBoost(roster.sourceText);
  const modes = inferModesFromText(roster.sourceText);
  const { modes: normalizedModes, modeWeights } = normalizeModeWeights(
    Object.fromEntries(modes.map((modeName, index) => [modeName, Math.max(0.2, 1 - index * 0.15)])),
    modes,
  );
  const labelSpecies = roster.speciesTokens.slice(0, 2).map((token) => formatLabel(token)).join(" ");
  const primaryMode = normalizedModes[0] ?? "dual_mode";
  const label = `${labelSpecies} ${renderModeLabel(primaryMode)}`.trim();

  const broadMix: Record<string, number> = inferBroadMixFromModes(normalizedModes);

  return {
    slug: `auto-${slugify(`${label}-${roster.sourceItem.publisher}`)}`,
    label,
    source: `${roster.sourceItem.publisher}: ${roster.sourceItem.title}`.slice(0, 240),
    result_label: deriveResultLabel(roster.sourceItem),
    field_relevance: roundToTwo(clamp(0.44 + baseSignal * 0.24 + resultBoost, 0, 2)),
    popularity_weight: roundToTwo(clamp(0.38 + baseSignal * 0.28, 0, 2)),
    result_weight: roundToTwo(clamp(0.42 + baseSignal * 0.18 + resultBoost, 0, 2)),
    modes: normalizedModes,
    mode_weights: modeWeights,
    broad_mix: broadMix,
    key_pokemon: roster.speciesTokens,
    key_cores: uniqueStrings([
      roster.speciesTokens.slice(0, 2).map((token) => formatLabel(token)).join(" + "),
      roster.speciesTokens.slice(1, 3).map((token) => formatLabel(token)).join(" + "),
    ]).filter(Boolean),
  };
}

function formatDiagnosticList(values: string[]) {
  const selectedValues = values.slice(0, MAX_DIAGNOSTIC_ITEMS);
  if (!selectedValues.length) {
    return "none";
  }

  const suffix = values.length > selectedValues.length ? ` (+${values.length - selectedValues.length} more)` : "";
  return `${selectedValues.join("; ")}${suffix}`;
}

function summarizeFailureReason(reason: string) {
  const normalizedReason = reason.replace(/\s+/g, " ").trim();
  const statusMatch = normalizedReason.match(/responded with (\d+)/i);
  if (statusMatch) {
    return statusMatch[1];
  }
  if (/timeout/i.test(normalizedReason)) {
    return "timeout";
  }
  return normalizedReason.slice(0, 24);
}

function formatFailureList(failures: LiveIngestionFailure[]) {
  return formatDiagnosticList(
    failures.map((failure) => `${failure.label} (${summarizeFailureReason(failure.reason)})`),
  );
}

function formatPageDiagnosticLabel(title: string, url: string) {
  const hostname = hostnameForUrl(url) || "page";
  return `${hostname}: ${title.replace(/\s+/g, " ").trim()}`.slice(0, 120);
}

function buildSnapshotDescriptor(
  snapshot: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number],
): SnapshotDescriptor {
  const keyCorePhrases = uniqueStrings(
    snapshot.key_cores.flatMap((core) => {
      const normalizedCore = normalizeSearchText(core);
      return uniqueStrings([
        normalizedCore,
        ...core.split("+").map((part) => normalizeSearchText(part)),
      ]).filter((value) => value.length >= 4 && !GENERIC_SEARCH_TERMS.has(value));
    }),
  );

  const pokemonPhrases = uniqueStrings(
    snapshot.key_pokemon.flatMap((speciesToken) => {
      return uniqueStrings([
        normalizeSearchText(renderSpeciesToken(speciesToken)),
        normalizeSearchText(baseSpeciesPhrase(speciesToken)),
      ]).filter((value) => value.length >= 4);
    }),
  );

  return {
    snapshot,
    labelPhrase: normalizeSearchText(snapshot.label),
    keyCorePhrases,
    pokemonPhrases,
  };
}

function buildEvidenceText(item: LiveEvidenceItem) {
  return normalizeSearchText(`${item.title} ${item.snippet} ${item.publisher}`);
}

function buildSignalStrength(item: LiveEvidenceItem) {
  return item.weight * recencyWeight(item.publishedAt);
}

function recencyWeight(publishedAt: string | null) {
  if (!publishedAt) {
    return 0.85;
  }

  const parsed = Date.parse(publishedAt);
  if (Number.isNaN(parsed)) {
    return 0.85;
  }

  const ageInDays = Math.max(0, (Date.now() - parsed) / 86_400_000);
  return Math.max(0.45, Math.min(1.1, 1.1 - ageInDays / 120));
}

function scoreEvidenceItem(item: LiveEvidenceItem, descriptor: SnapshotDescriptor) {
  const text = buildEvidenceText(item);
  if (!isTournamentEvidenceItem(item)) {
    return {
      visibility: 0,
      result: 0,
      matched: false,
    };
  }

  let visibilityScore = 0;
  let resultScore = 0;
  let pokemonMatches = 0;
  let strongMatches = 0;

  if (descriptor.labelPhrase && text.includes(descriptor.labelPhrase)) {
    visibilityScore += 5.2;
    strongMatches += 1;
  }

  for (const corePhrase of descriptor.keyCorePhrases) {
    if (text.includes(corePhrase)) {
      visibilityScore += 2.8;
      strongMatches += 1;
    }
  }

  for (const pokemonPhrase of descriptor.pokemonPhrases) {
    if (text.includes(pokemonPhrase)) {
      visibilityScore += pokemonPhrase.includes(" ") ? 1.4 : 0.85;
      pokemonMatches += 1;
    }
  }

  if (pokemonMatches >= 2) {
    visibilityScore += 2.2;
  }

  const hasResultSignal = hasTournamentResultSignal(text);
  if (hasResultSignal && (strongMatches > 0 || pokemonMatches >= 2)) {
    resultScore += 1.4 + visibilityScore * 0.32;
  }

  const weight = item.weight * recencyWeight(item.publishedAt);
  return {
    visibility: visibilityScore * weight,
    result: resultScore * weight,
    matched: visibilityScore > 0,
  };
}

async function fetchSourceBody(source: LiveSourceDefinition) {
  const response = await fetch(source.url, {
    cache: "no-store",
    headers: LIVE_SOURCE_HEADERS,
    signal: AbortSignal.timeout(LIVE_SOURCE_TIMEOUT_MS),
  });

  if (!response.ok) {
    throw new Error(`${source.label} responded with ${response.status}.`);
  }

  return response.text();
}

async function fetchRawPageBody(url: string) {
  const response = await fetch(url, {
    cache: "no-store",
    headers: LIVE_SOURCE_HEADERS,
    signal: AbortSignal.timeout(EXPORT_PAGE_TIMEOUT_MS),
  });
  if (!response.ok) {
    throw new Error(`Page responded with ${response.status}.`);
  }

  return {
    url: response.url,
    body: normalizeFetchedPageBody(await response.text()),
  };
}

async function resolveGoogleNewsArticleUrl(url: string, body: string) {
  const hostname = hostnameForUrl(url);
  if (hostname !== "news.google.com") {
    return null;
  }

  const articleId = body.match(/data-n-a-id="([^"]+)"/i)?.[1] ?? "";
  const timestamp = body.match(/data-n-a-ts="([^"]+)"/i)?.[1] ?? "";
  const signature = body.match(/data-n-a-sg="([^"]+)"/i)?.[1] ?? "";
  if (!articleId || !timestamp || !signature) {
    return null;
  }

  const requestBody = new URLSearchParams({
    "f.req": JSON.stringify([
      [
        [
          "Fbv4je",
          JSON.stringify([
            "garturlreq",
            [
              [
                "en-US",
                "US",
                ["FINANCE_TOP_INDICES", "WEB_TEST_1_0_0"],
                null,
                null,
                1,
                1,
                "US:en",
                null,
                180,
                null,
                null,
                null,
                null,
                null,
                0,
                null,
                null,
                [1608992183, 723341000],
              ],
              "en-US",
              "US",
              1,
              [2, 3, 4, 8],
              1,
              0,
              "655000234",
              0,
              0,
              null,
              0,
            ],
            articleId,
            timestamp,
            signature,
          ]),
          null,
          "generic",
        ],
      ],
    ]),
  });
  const response = await fetch("https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je", {
    method: "POST",
    cache: "no-store",
    headers: {
      ...LIVE_SOURCE_HEADERS,
      "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    },
    body: requestBody.toString(),
    signal: AbortSignal.timeout(EXPORT_PAGE_TIMEOUT_MS),
  });
  if (!response.ok) {
    return null;
  }

  const responseText = await response.text();
  const payloadLine = responseText
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line.startsWith("[["));
  if (!payloadLine) {
    return null;
  }

  try {
    const payload = JSON.parse(payloadLine) as unknown[];
    const encodedResult = payload.find((entry) => Array.isArray(entry) && entry[0] === "wrb.fr" && entry[1] === "Fbv4je");
    if (!Array.isArray(encodedResult) || typeof encodedResult[2] !== "string") {
      return null;
    }

    const resultPayload = JSON.parse(encodedResult[2]) as unknown[];
    return typeof resultPayload[1] === "string" ? resultPayload[1] : null;
  } catch {
    return null;
  }
}

function parseRssItems(source: LiveSourceDefinition, body: string): LiveEvidenceItem[] {
  const rawItems = body.match(/<item\b[\s\S]*?<\/item>/gi) ?? [];
  return rawItems.slice(0, source.maxItems ?? 12).flatMap((rawItem) => {
    const title = extractTagText(rawItem, "title");
    if (!title) {
      return [];
    }

    const snippet = extractTagText(rawItem, "description");
    const url = extractTagText(rawItem, "link") || source.url;
    const publishedAt = extractTagText(rawItem, "pubDate") || null;
    const sourceMatch = rawItem.match(/<source\b[^>]*>([\s\S]*?)<\/source>/i);
    const publisher = sourceMatch ? stripHtml(sourceMatch[1]) : source.label;

    return [
      {
        sourceId: source.id,
        sourceLabel: source.label,
        title,
        snippet,
        url,
        publisher,
        publishedAt,
        weight: source.weight,
      },
    ];
  });
}

function parseYouTubeItems(source: LiveSourceDefinition, body: string): LiveEvidenceItem[] {
  const rawTitles = [...body.matchAll(/\\"title\\":\{\\"runs\\":\[\{\\"text\\":\\"([^\"]+?)\\"/g)]
    .map((match) => decodeJsonEscapes(match[1]))
    .filter((title) => title.length >= 12 && !title.startsWith("Home") && !title.startsWith("Shorts"));

  return uniqueStrings(rawTitles)
    .slice(0, source.maxItems ?? 10)
    .map((title) => ({
      sourceId: source.id,
      sourceLabel: source.label,
      title,
      snippet: "Live YouTube search result",
      url: source.url,
      publisher: "YouTube",
      publishedAt: null,
      weight: source.weight,
    }));
}

function parseRedditSearchItems(source: LiveSourceDefinition, body: string): LiveEvidenceItem[] {
  const rawBlocks = body.split('<div class=" search-result search-result-link').slice(1);
  return rawBlocks.slice(0, source.maxItems ?? 10).flatMap((rawBlock) => {
    const titleMatch = rawBlock.match(/<a href="([^"]+)" class="search-title may-blank"[^>]*>([\s\S]*?)<\/a>/i);
    if (!titleMatch) {
      return [];
    }

    const snippetMatch = rawBlock.match(/<div class="md"><p>([\s\S]*?)<\/p>/i);
    const timeMatch = rawBlock.match(/<time[^>]+datetime="([^"]+)"/i);
    const subredditMatch = rawBlock.match(/class="search-subreddit-link may-blank"[^>]*>([\s\S]*?)<\/a>/i);
    const rawUrl = titleMatch[1].startsWith("http") ? titleMatch[1] : `https://old.reddit.com${titleMatch[1]}`;

    return [
      {
        sourceId: source.id,
        sourceLabel: source.label,
        title: stripHtml(titleMatch[2]),
        snippet: snippetMatch ? stripHtml(snippetMatch[1]) : "Live old Reddit search result",
        url: rawUrl,
        publisher: subredditMatch ? stripHtml(subredditMatch[1]) : "old Reddit",
        publishedAt: timeMatch?.[1] ?? null,
        weight: source.weight,
      },
    ];
  });
}

function parseHtmlPageItems(source: LiveSourceDefinition, body: string): LiveEvidenceItem[] {
  const title = extractTagText(body, "title");
  const metaDescription = extractMetaContent(body, "description") || extractMetaContent(body, "og:description");
  const headings = uniqueStrings(
    [...body.matchAll(/<h[12][^>]*>([\s\S]*?)<\/h[12]>/gi)]
      .map((match) => stripHtml(match[1]))
      .filter((heading) => heading.length >= 6),
  ).slice(0, 3);

  if (!title && !metaDescription && headings.length === 0) {
    return [];
  }

  return [
    {
      sourceId: source.id,
      sourceLabel: source.label,
      title: title || source.label,
      snippet: [metaDescription, ...headings].filter(Boolean).join(" "),
      url: source.url,
      publisher: source.label,
      publishedAt: null,
      weight: source.weight,
    },
  ];
}

function resolveAnalyzerApiBaseUrl() {
  const configuredBaseUrl = process.env.POKEMON_ANALYZER_API_BASE_URL?.trim();
  if (configuredBaseUrl) {
    return configuredBaseUrl.replace(/\/+$/, "");
  }

  const sourceUrl = process.env.META_SNAPSHOT_SOURCE_URL?.trim();
  if (!sourceUrl) {
    return "";
  }

  try {
    return new URL(sourceUrl).origin;
  } catch {
    return "";
  }
}

function slugify(value: string) {
  return normalizeSearchText(value).replace(/\s+/g, "-").replace(/^-+|-+$/g, "");
}

function renderModeLabel(modeName: string) {
  return formatLabel(modeName);
}

function normalizeSpeciesToken(name: string) {
  const normalized = name.trim().toLowerCase();
  if (!normalized) {
    return "";
  }

  const specialTokens: Record<string, string> = {
    "basculegion (m)": "basculegion",
    "basculegion (male)": "basculegion",
    "basculegion (f)": "basculegion-f",
    "basculegion (female)": "basculegion-f",
    "eternal flower floette": "floette-eternal",
    "mega eternal flower floette": "floette-mega",
  };
  if (specialTokens[normalized]) {
    return specialTokens[normalized];
  }

  if (normalized.startsWith("mega ")) {
    const megaName = normalized.slice("mega ".length).trim();
    if (megaName.endsWith(" x")) {
      return `${megaName.slice(0, -2).trim().replace(/[^a-z0-9]+/g, "-")}-mega-x`;
    }
    if (megaName.endsWith(" y")) {
      return `${megaName.slice(0, -2).trim().replace(/[^a-z0-9]+/g, "-")}-mega-y`;
    }
    return `${megaName.replace(/[^a-z0-9]+/g, "-")}-mega`;
  }

  if (normalized.startsWith("alolan ")) {
    return `${normalized.slice("alolan ".length).replace(/[^a-z0-9]+/g, "-")}-alola`;
  }
  if (normalized.startsWith("hisuian ")) {
    return `${normalized.slice("hisuian ".length).replace(/[^a-z0-9]+/g, "-")}-hisui`;
  }
  if (normalized.endsWith(" (m)")) {
    return `${normalized.slice(0, -4).replace(/[^a-z0-9]+/g, "-")}-male`;
  }
  if (normalized.endsWith(" (male)")) {
    return `${normalized.slice(0, -7).replace(/[^a-z0-9]+/g, "-")}-male`;
  }
  if (normalized.endsWith(" (f)")) {
    return `${normalized.slice(0, -4).replace(/[^a-z0-9]+/g, "-")}-female`;
  }
  if (normalized.endsWith(" (female)")) {
    return `${normalized.slice(0, -9).replace(/[^a-z0-9]+/g, "-")}-female`;
  }

  return normalized.replace(/[^a-z0-9]+/g, "-").replace(/-+/g, "-").replace(/^-+|-+$/g, "");
}

function normalizeModeWeights(modeScores: Record<string, number>, labels: string[]) {
  const selectedLabels = uniqueStrings(labels.length ? labels : ["dual_mode"])
    .map((label) => [label, Math.max(0, modeScores[label] ?? 0)] as const)
    .sort((left, right) => right[1] - left[1])
    .slice(0, 4);

  const weightedLabels = selectedLabels.some((entry) => entry[1] > 0)
    ? selectedLabels.filter((entry) => entry[1] > 0)
    : [[selectedLabels[0]?.[0] ?? "dual_mode", 1] as const];

  const totalWeight = weightedLabels.reduce((sum, entry) => sum + entry[1], 0) || 1;
  return {
    modes: weightedLabels.map((entry) => entry[0]),
    modeWeights: Object.fromEntries(weightedLabels.map(([label, weight]) => [label, roundToTwo(weight / totalWeight)])),
  };
}

function normalizeBroadMix(teamArchetypeScores: Record<string, number>, teamArchetype: string) {
  const weightedEntries = Object.entries(teamArchetypeScores)
    .filter(([label]) => BROAD_MIX_KEYS.includes(label as (typeof BROAD_MIX_KEYS)[number]))
    .map(([label, score]) => [label, Math.max(0, score)] as const)
    .filter((entry) => entry[1] > 0)
    .sort((left, right) => right[1] - left[1])
    .slice(0, 3);

  if (!weightedEntries.length) {
    const fallbackKey = BROAD_MIX_KEYS.includes(teamArchetype as (typeof BROAD_MIX_KEYS)[number]) ? teamArchetype : "balance";
    return { [fallbackKey]: 1 };
  }

  const totalWeight = weightedEntries.reduce((sum, entry) => sum + entry[1], 0) || 1;
  return Object.fromEntries(weightedEntries.map(([label, score]) => [label, roundToTwo(score / totalWeight)]));
}

function deriveResultLabel(item: LiveEvidenceItem) {
  const text = buildEvidenceText(item);
  if (text.includes("winner") || text.includes("champion") || text.includes("championship") || text.includes("won")) {
    return "live tournament winner";
  }
  if (text.includes("top 8") || text.includes("top 16") || text.includes("top 32") || text.includes("top cut") || text.includes("finalist") || text.includes("runner up")) {
    return "live top-cut finish";
  }
  if (text.includes("team report") || text.includes("tournament report") || text.includes("results") || text.includes("standings")) {
    return "live tournament report";
  }
  return "live tournament result";
}

function extractExportLinks(body: string) {
  return uniqueStrings((body.match(EXPORT_LINK_PATTERN) ?? []).map((url) => url.replace(/\/raw$/, "")));
}

function htmlToTextWithLineBreaks(body: string) {
  return decodeHtmlEntities(
    body
      .replace(/<script\b[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[\s\S]*?<\/style>/gi, " ")
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/(?:p|div|section|article|li|ul|ol|pre|code|blockquote|h1|h2|h3|h4|h5|h6)>/gi, "\n")
      .replace(/<[^>]+>/g, " "),
  )
    .replace(/\r/g, "")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function normalizeExtractedTeamText(teamText: string) {
  return teamText
    .replace(/\r/g, "")
    .replace(/[ \t]+$/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function isLikelyShowdownTeamText(teamText: string) {
  const normalized = normalizeExtractedTeamText(teamText);
  if (!normalized.includes("Ability:")) {
    return false;
  }
  if ((normalized.match(/^- /gm) ?? []).length < 12) {
    return false;
  }
  const parsedMembers = parseShowdownTeam(normalized);
  if (parsedMembers.length < 4 || parsedMembers.length > 6) {
    return false;
  }
  return parsedMembers.every((member) => member.ability && member.moves.length >= 2);
}

function extractShowdownTeamBlocks(body: string) {
  const rawCodeBlocks = [
    ...body.matchAll(/<(?:pre|code)[^>]*>([\s\S]*?)<\/(?:pre|code)>/gi),
  ].map((match) => normalizeExtractedTeamText(htmlToTextWithLineBreaks(match[1])));
  const rawParagraphBlocks = htmlToTextWithLineBreaks(body).split(/\n{2,}/g);

  return uniqueStrings([...rawCodeBlocks, ...rawParagraphBlocks].map(normalizeExtractedTeamText)).filter(isLikelyShowdownTeamText);
}

async function fetchPageBody(url: string) {
  const initialPage = await fetchRawPageBody(url);
  const unwrappedUrl = await resolveGoogleNewsArticleUrl(initialPage.url, initialPage.body);
  if (!unwrappedUrl || unwrappedUrl === initialPage.url) {
    return initialPage;
  }

  return fetchRawPageBody(unwrappedUrl);
}

async function fetchPokepasteTeamText(url: string) {
  const normalizedUrl = url.replace(/\/raw$/, "").replace(/\/$/, "");
  const rawUrl = `${normalizedUrl}/raw`;
  const response = await fetch(rawUrl, {
    cache: "no-store",
    headers: LIVE_SOURCE_HEADERS,
    signal: AbortSignal.timeout(EXPORT_PAGE_TIMEOUT_MS),
  });

  if (response.ok) {
    const body = normalizeExtractedTeamText(await response.text());
    if (isLikelyShowdownTeamText(body)) {
      return body;
    }
  }

  const page = await fetchPageBody(normalizedUrl);
  const blocks = extractShowdownTeamBlocks(page.body);
  return blocks[0] ?? null;
}

function supportsExportDiscovery(item: LiveEvidenceItem) {
  return !item.sourceId.startsWith("youtube-") && !item.url.includes("/results?search_query=");
}

function isLikelyDeepDiscoveryTarget(item: LiveEvidenceItem) {
  if (item.url.includes("pokepast.es/")) {
    return true;
  }

  if (!isTournamentEvidenceItem(item)) {
    return false;
  }

  const text = buildEvidenceText(item);
  return DEEP_DISCOVERY_TERMS.some((term) => text.includes(term));
}

async function collectCandidateExportPages(
  liveItems: LiveEvidenceItem[],
  diagnostics: LiveDiscoveryDiagnostics,
) {
  const candidateItems = liveItems
    .filter((item) => supportsExportDiscovery(item) && isLikelyDeepDiscoveryTarget(item))
    .sort((left, right) => buildSignalStrength(right) - buildSignalStrength(left))
    .slice(0, MAX_EXPORT_SOURCE_PAGES);

  const pageResults = await Promise.allSettled(
    candidateItems.map(async (item) => {
      const page = await fetchPageBody(item.url);
      diagnostics.candidatePagesFetched.push(formatPageDiagnosticLabel(item.title, page.url));
      return {
        item,
        url: page.url,
        body: page.body,
      } satisfies CandidateExportPage;
    }),
  );

  for (let index = 0; index < pageResults.length; index += 1) {
    const result = pageResults[index];
    if (result.status === "fulfilled") {
      continue;
    }

    diagnostics.candidatePageFailures.push({
      label: candidateItems[index]?.title ?? candidateItems[index]?.sourceLabel ?? "Candidate page",
      reason: result.reason instanceof Error ? result.reason.message : "Unknown candidate page failure.",
    });
  }

  return pageResults.flatMap((result) => (result.status === "fulfilled" ? [result.value] : []));
}

async function analyzeTeamExport(teamText: string): Promise<AnalyzeTeamExportResult> {
  const analyzerApiBaseUrl = resolveAnalyzerApiBaseUrl();
  if (!analyzerApiBaseUrl) {
    return {
      analysis: null,
      reason: "POKEMON_ANALYZER_API_BASE_URL is not configured.",
    };
  }

  const response = await fetch(`${analyzerApiBaseUrl}/api/analyze`, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "User-Agent": LIVE_SOURCE_HEADERS["User-Agent"],
    },
    body: JSON.stringify({
      teamText,
      regulationId: "champions_regulation_m_a",
    }),
    signal: AbortSignal.timeout(ANALYZE_EXPORT_TIMEOUT_MS),
  });

  if (!response.ok) {
    return {
      analysis: null,
      reason: `Analyzer API responded with ${response.status}.`,
    };
  }

  const payload = (await response.json()) as AnalyzeRoutePayload;
  if (!payload.ok) {
    return {
      analysis: null,
      reason: payload.message,
    };
  }

  return {
    analysis: payload.analysis,
    reason: null,
  };
}

function looksLikeTrackedSnapshot(
  candidateKeyPokemon: string[],
  candidateModes: string[],
  trackedSnapshot: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number],
) {
  const trackedKeyPokemon = new Set(trackedSnapshot.key_pokemon);
  const speciesOverlap = candidateKeyPokemon.filter((speciesToken) => trackedKeyPokemon.has(speciesToken)).length;
  const hasModeOverlap = candidateModes.some((modeName) => trackedSnapshot.modes.includes(modeName));
  return speciesOverlap >= 4 && hasModeOverlap;
}

function buildDiscoveredSnapshot(
  discoveredTeam: DiscoveredTeamExport,
): PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number] {
  const parsedMembers = parseShowdownTeam(discoveredTeam.teamText);
  const keyPokemon = uniqueStrings(
    Object.keys(discoveredTeam.analysis.member_roles).map(normalizeSpeciesToken).filter(Boolean),
  ).slice(0, 6);
  const previewPlan = discoveredTeam.analysis.team_preview.bring_plans[0];
  const leadCore = previewPlan?.leads.slice(0, 2) ?? [];
  const labelPair = (leadCore.length >= 2 ? leadCore : parsedMembers.slice(0, 2).map((member) => member.species))
    .map((name) => formatLabel(normalizeSpeciesToken(name) || name))
    .slice(0, 2);
  const primaryMode = discoveredTeam.analysis.team_package_profile.modes.labels[0] || discoveredTeam.analysis.team_archetype || "dual_mode";
  const label = `${labelPair.join(" ")} ${renderModeLabel(primaryMode)}`.trim();
  const { modes, modeWeights } = normalizeModeWeights(
    discoveredTeam.analysis.team_package_profile.modes.scores,
    discoveredTeam.analysis.team_package_profile.modes.labels.length
      ? discoveredTeam.analysis.team_package_profile.modes.labels
      : [primaryMode],
  );
  const broadMix = normalizeBroadMix(discoveredTeam.analysis.team_archetype_scores, discoveredTeam.analysis.team_archetype);
  const baseSignal = buildSignalStrength(discoveredTeam.sourceItem);
  const resultText = buildEvidenceText(discoveredTeam.sourceItem);
  const resultBoost = strongestResultBoost(resultText);

  return {
    slug: `live-${slugify(label)}`,
    label,
    source: `${discoveredTeam.sourceItem.publisher}: ${discoveredTeam.sourceItem.title}`.slice(0, 240),
    result_label: deriveResultLabel(discoveredTeam.sourceItem),
    field_relevance: roundToTwo(clamp(0.5 + baseSignal * 0.28 + resultBoost, 0, 2)),
    popularity_weight: roundToTwo(clamp(0.48 + baseSignal * 0.36, 0, 2)),
    result_weight: roundToTwo(clamp(0.52 + baseSignal * 0.22 + resultBoost, 0, 2)),
    modes,
    mode_weights: modeWeights,
    broad_mix: broadMix,
    key_pokemon: keyPokemon,
    key_cores: uniqueStrings([
      leadCore.length >= 2 ? leadCore.map((name) => formatLabel(normalizeSpeciesToken(name) || name)).join(" + ") : "",
      previewPlan?.pick_four.slice(0, 2).map((name) => formatLabel(normalizeSpeciesToken(name) || name)).join(" + ") ?? "",
      keyPokemon.slice(0, 2).map((token) => formatLabel(token)).join(" + "),
    ]).slice(0, 3),
  };
}

async function discoverLiveTournamentSnapshots(
  document: PublishedMetaSnapshotDocument,
  liveItems: LiveEvidenceItem[],
  options?: { skipReason?: string; phraseIndex?: SpeciesPhraseIndexEntry[] },
): Promise<LiveDiscoveryResult> {
  const diagnostics: LiveDiscoveryDiagnostics = {
    skippedReason: options?.skipReason ?? null,
    candidatePagesFetched: [],
    candidatePageFailures: [],
    exportPages: [],
    rosterPages: [],
    analyzerFailures: [],
  };

  if (document.regulationId !== "champions_regulation_m_a") {
    return {
      discoveredSnapshots: [],
      rosterSnapshots: [],
      rosterEvidenceItems: [],
      diagnostics,
    };
  }

  if (diagnostics.skippedReason) {
    return {
      discoveredSnapshots: [],
      rosterSnapshots: [],
      rosterEvidenceItems: [],
      diagnostics,
    };
  }

  const candidatePages = await collectCandidateExportPages(liveItems, diagnostics);
  const discoveredTeams = new Map<string, DiscoveredTeamExport>();
  const rosterEvidenceItems: LiveEvidenceItem[] = [];
  const rosterSnapshots = new Map<string, PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number]>();
  const seenRosterKeys = new Set<string>();
  const phraseIndex = options?.phraseIndex?.length ? options.phraseIndex : buildDocumentSpeciesPhraseIndex(document);

  for (const page of candidatePages) {
    for (const roster of extractArticleRosters(page, phraseIndex)) {
      const rosterKey = roster.speciesTokens.slice().sort().join("|");
      if (seenRosterKeys.has(rosterKey)) {
        continue;
      }

      seenRosterKeys.add(rosterKey);
      rosterEvidenceItems.push(buildRosterEvidenceItem(roster));
      rosterSnapshots.set(rosterKey, buildRosterSnapshot(roster));
      diagnostics.rosterPages.push(
        `${formatPageDiagnosticLabel(roster.label, page.url)} -> ${roster.speciesTokens.slice(0, 4).map((token) => formatLabel(token)).join(" / ")}`.slice(0, 180),
      );
    }

    const discoveredTeamTexts: string[] = [];
    for (const link of extractExportLinks(page.body).slice(0, 2)) {
      try {
        const pokepasteTeamText = await fetchPokepasteTeamText(link);
        if (pokepasteTeamText) {
          discoveredTeamTexts.push(pokepasteTeamText);
          diagnostics.exportPages.push(formatPageDiagnosticLabel(page.item.title, link));
        }
      } catch {
        continue;
      }
    }

    for (const teamBlock of extractShowdownTeamBlocks(page.body).slice(0, 2)) {
      discoveredTeamTexts.push(teamBlock);
      diagnostics.exportPages.push(formatPageDiagnosticLabel(page.item.title, page.url));
    }

    for (const teamText of uniqueStrings(discoveredTeamTexts.map(normalizeExtractedTeamText)).slice(0, 2)) {
      if (discoveredTeams.size >= MAX_EXTRACTED_TEAMS) {
        break;
      }

      const parsedMembers = parseShowdownTeam(teamText);
      if (parsedMembers.length < 4 || parsedMembers.length > 6) {
        continue;
      }

      const speciesKey = parsedMembers.map((member) => normalizeSpeciesToken(member.species)).filter(Boolean).sort().join("|");
      if (!speciesKey || discoveredTeams.has(speciesKey)) {
        continue;
      }

      try {
        const analysisResult = await analyzeTeamExport(teamText);
        if (!analysisResult.analysis) {
          diagnostics.analyzerFailures.push({
            label: page.item.title,
            reason: analysisResult.reason ?? "Unknown analyzer failure.",
          });
          continue;
        }

        discoveredTeams.set(speciesKey, {
          sourceItem: page.item,
          teamText,
          analysis: analysisResult.analysis,
        });
      } catch (error) {
        diagnostics.analyzerFailures.push({
          label: page.item.title,
          reason: error instanceof Error ? error.message : "Unknown analyzer failure.",
        });
        continue;
      }
    }

    if (discoveredTeams.size >= MAX_EXTRACTED_TEAMS) {
      break;
    }
  }

  const dedupedExportSnapshots = [...discoveredTeams.values()]
    .map(buildDiscoveredSnapshot)
    .filter((candidateSnapshot) =>
      !document.tournamentTeamSnapshots.some((trackedSnapshot) =>
        looksLikeTrackedSnapshot(candidateSnapshot.key_pokemon, candidateSnapshot.modes, trackedSnapshot),
      ),
    )
    .slice(0, MAX_EXTRACTED_TEAMS);
  const dedupedRosterSnapshots = [...rosterSnapshots.values()]
    .filter((candidateSnapshot) =>
      !document.tournamentTeamSnapshots.some((trackedSnapshot) =>
        looksLikeTrackedSnapshot(candidateSnapshot.key_pokemon, candidateSnapshot.modes, trackedSnapshot),
      ),
    )
    .filter((candidateSnapshot) =>
      !dedupedExportSnapshots.some((trackedSnapshot) =>
        looksLikeTrackedSnapshot(candidateSnapshot.key_pokemon, candidateSnapshot.modes, trackedSnapshot),
      ),
    )
    .slice(0, MAX_AUTOMATED_SNAPSHOTS);

  return {
    discoveredSnapshots: dedupedExportSnapshots,
    rosterSnapshots: dedupedRosterSnapshots,
    rosterEvidenceItems: [...new Map(rosterEvidenceItems.map((item) => [`${normalizeSearchText(item.title)}|${item.snippet}`, item])).values()],
    diagnostics: {
      skippedReason: diagnostics.skippedReason,
      candidatePagesFetched: uniqueStrings(diagnostics.candidatePagesFetched),
      candidatePageFailures: diagnostics.candidatePageFailures,
      exportPages: uniqueStrings(diagnostics.exportPages),
      rosterPages: uniqueStrings(diagnostics.rosterPages),
      analyzerFailures: diagnostics.analyzerFailures,
    },
  };
}

async function collectLiveEvidenceItems(options?: { sourceMode?: LiveEvidenceSourceMode }): Promise<LiveEvidenceCollection> {
  const sourceMode = options?.sourceMode ?? "default";
  const activeSources = DEFAULT_LIVE_SOURCES.filter((source) => {
    if (sourceMode === "all") {
      return true;
    }
    if (sourceMode === "deep-only") {
      return true;
    }
    return !source.requiresDeepDiscovery;
  });
  const results = await Promise.allSettled(
    activeSources.map(async (source) => {
      const body = await fetchSourceBody(source);
      switch (source.kind) {
        case "rss":
          return parseRssItems(source, body);
        case "youtube-search":
          return parseYouTubeItems(source, body);
        case "reddit-search":
          return parseRedditSearchItems(source, body);
        case "html-page":
          return parseHtmlPageItems(source, body);
      }
    }),
  );

  const items: LiveEvidenceItem[] = [];
  const succeededSources: string[] = [];
  let failedSourceCount = 0;
  const failedSources: LiveIngestionFailure[] = [];

  for (let index = 0; index < results.length; index += 1) {
    const result = results[index];
    const source = activeSources[index];
    if (result.status === "fulfilled") {
      succeededSources.push(source.label);
      items.push(...result.value);
      continue;
    }
    failedSourceCount += 1;
    failedSources.push({
      label: source.label,
      reason: result.reason instanceof Error ? result.reason.message : "Unknown source failure.",
    });
  }

  const dedupedItems = [...new Map(items.map((item) => [`${normalizeSearchText(item.title)}|${item.publisher}`, item])).values()]
    .filter((item) => isTournamentEvidenceItem(item));
  return {
    items: dedupedItems,
    succeededSources,
    failedSourceCount,
    failedSources,
  };
}

function buildAutomatedCandidateSignal(candidate: AutomatedSnapshotCandidate) {
  return Math.max(0.18, buildSignalStrength(candidate.sourceItem));
}

function snapshotsLookRelated(
  left: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number],
  right: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number],
) {
  return looksLikeTrackedSnapshot(left.key_pokemon, left.modes, right)
    || looksLikeTrackedSnapshot(right.key_pokemon, right.modes, left);
}

function aggregateAutomatedSnapshotCandidates(candidates: AutomatedSnapshotCandidate[]) {
  const sortedCandidates = [...candidates].sort(
    (left, right) => buildAutomatedCandidateSignal(right) - buildAutomatedCandidateSignal(left),
  );
  const groups: AutomatedSnapshotCandidate[][] = [];

  for (const candidate of sortedCandidates) {
    const matchingGroup = groups.find((group) =>
      group.some((existingCandidate) => snapshotsLookRelated(existingCandidate.snapshot, candidate.snapshot)),
    );
    if (matchingGroup) {
      matchingGroup.push(candidate);
      continue;
    }
    groups.push([candidate]);
  }

  return groups
    .map((group) => {
      const leadCandidate = [...group].sort(
        (left, right) => buildAutomatedCandidateSignal(right) - buildAutomatedCandidateSignal(left),
      )[0];
      const speciesScores = new Map<string, number>();
      const modeScores = new Map<string, number>();
      const broadMixScores = new Map<string, number>();
      const coreScores = new Map<string, number>();
      const labelScores = new Map<string, number>();
      const publisherScores = new Map<string, number>();
      let totalSignal = 0;
      let weightedFieldRelevance = 0;
      let weightedPopularity = 0;
      let weightedResult = 0;
      let strongestResultBoostValue = 0;

      for (const candidate of group) {
        const signal = buildAutomatedCandidateSignal(candidate);
        totalSignal += signal;
        weightedFieldRelevance += candidate.snapshot.field_relevance * signal;
        weightedPopularity += candidate.snapshot.popularity_weight * signal;
        weightedResult += candidate.snapshot.result_weight * signal;
        strongestResultBoostValue = Math.max(strongestResultBoostValue, strongestResultBoost(candidate.sourceText));
        labelScores.set(candidate.snapshot.label, (labelScores.get(candidate.snapshot.label) ?? 0) + signal);
        publisherScores.set(candidate.sourceItem.publisher, (publisherScores.get(candidate.sourceItem.publisher) ?? 0) + signal);

        for (const speciesToken of candidate.snapshot.key_pokemon) {
          speciesScores.set(speciesToken, (speciesScores.get(speciesToken) ?? 0) + signal);
        }
        for (const core of candidate.snapshot.key_cores) {
          coreScores.set(core, (coreScores.get(core) ?? 0) + signal);
        }
        for (const [modeName, weight] of Object.entries(candidate.snapshot.mode_weights)) {
          modeScores.set(modeName, (modeScores.get(modeName) ?? 0) + signal * weight);
        }
        for (const [mixName, weight] of Object.entries(candidate.snapshot.broad_mix)) {
          broadMixScores.set(mixName, (broadMixScores.get(mixName) ?? 0) + signal * weight);
        }
      }

      const averageFieldRelevance = totalSignal > 0 ? weightedFieldRelevance / totalSignal : leadCandidate.snapshot.field_relevance;
      const averagePopularity = totalSignal > 0 ? weightedPopularity / totalSignal : leadCandidate.snapshot.popularity_weight;
      const averageResult = totalSignal > 0 ? weightedResult / totalSignal : leadCandidate.snapshot.result_weight;
      const clusterBoost = Math.min(0.32, Math.max(0, group.length - 1) * 0.07);
      const fieldRelevance = roundToTwo(clamp(averageFieldRelevance * 0.6 + Math.min(0.95, totalSignal * 0.22) + clusterBoost, 0, 2));
      const popularityWeight = roundToTwo(clamp(averagePopularity * 0.52 + Math.min(1.0, totalSignal * 0.3) + clusterBoost, 0, 2));
      const resultWeight = roundToTwo(clamp(averageResult * 0.62 + Math.min(0.88, totalSignal * 0.2) + strongestResultBoostValue, 0, 2));
      const rankedModes = [...modeScores.entries()].sort((left, right) => right[1] - left[1]).slice(0, 4);
      const modeLabels = rankedModes.length ? rankedModes.map(([modeName]) => modeName) : leadCandidate.snapshot.modes;
      const { modes, modeWeights } = normalizeModeWeights(Object.fromEntries(rankedModes), modeLabels);
      const rankedBroadMix = [...broadMixScores.entries()].sort((left, right) => right[1] - left[1]).slice(0, 3);
      const broadMix: Record<string, number> = rankedBroadMix.length
        ? Object.fromEntries(rankedBroadMix.map(([mixName, score]) => [mixName, roundToTwo(score / (rankedBroadMix.reduce((sum, [, value]) => sum + value, 0) || 1))]))
        : inferBroadMixFromModes(modes);
      const keyPokemon = [...speciesScores.entries()]
        .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
        .slice(0, 6)
        .map(([speciesToken]) => speciesToken);
      const keyCores = [...coreScores.entries()]
        .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
        .slice(0, 3)
        .map(([core]) => core)
        .filter(Boolean);
      const bestLabel = [...labelScores.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))[0]?.[0]
        ?? `${keyPokemon.slice(0, 2).map((speciesToken) => formatLabel(speciesToken)).join(" ")} ${renderModeLabel(modes[0] ?? "dual_mode")}`.trim();
      const publishers = [...publisherScores.entries()]
        .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
        .slice(0, 2)
        .map(([publisher]) => publisher);

      return {
        slug: `auto-${slugify(bestLabel)}`,
        label: bestLabel,
        source: `Automated live discovery across ${publishers.join(", ") || leadCandidate.sourceItem.publisher}`.slice(0, 240),
        result_label: deriveResultLabel(leadCandidate.sourceItem),
        field_relevance: fieldRelevance,
        popularity_weight: popularityWeight,
        result_weight: resultWeight,
        modes,
        mode_weights: modeWeights,
        broad_mix: broadMix,
        key_pokemon: keyPokemon,
        key_cores: keyCores.length ? keyCores : leadCandidate.snapshot.key_cores,
      } satisfies PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number];
    })
    .sort((left, right) => buildSnapshotRank(right) - buildSnapshotRank(left) || left.label.localeCompare(right.label))
    .slice(0, MAX_AUTOMATED_SNAPSHOTS);
}

function createAutomationSeedDocument(regulationId: string) {
  return {
    regulationId,
    updatedAt: new Date().toISOString(),
    sourceLabel: AUTOMATED_META_SOURCE_LABEL,
    notes: [
      "Generated automatically from live-source discovery, extracted rosters, and export-backed teams.",
      "This board does not use the analyzer's hand-authored tournament shell catalog as an input source.",
    ],
    commonMetaPokemon: [],
    tournamentTeamSnapshots: [],
  } satisfies PublishedMetaSnapshotDocument;
}

export async function buildAutomatedMetaSnapshotDocuments(options?: AutomatedMetaSnapshotBuildOptions) {
  const automationStartedAt = Date.now();
  const regulationId = options?.regulationId ?? "champions_regulation_m_a";
  const runtimeBudgetMs = options?.runtimeBudgetMs ?? DISCOVERY_RUNTIME_BUDGET_MS;
  const liveEvidence = await collectLiveEvidenceItems({ sourceMode: options?.sourceMode ?? "all" });
  const phraseIndex = await fetchRegulationSpeciesPhraseIndex(regulationId);
  const automationSeed = createAutomationSeedDocument(regulationId);
  const discoveryResult = await discoverLiveTournamentSnapshots(automationSeed, liveEvidence.items, {
    phraseIndex,
    skipReason: Date.now() - automationStartedAt > runtimeBudgetMs
      ? "runtime budget was exhausted before automated discovery could begin"
      : undefined,
  });
  const automatedCandidates: AutomatedSnapshotCandidate[] = [
    ...discoveryResult.discoveredSnapshots.map((snapshot, index) => ({
      snapshot,
      sourceItem: {
        sourceId: `auto-export-${snapshot.slug}-${index}`,
        sourceLabel: AUTOMATED_META_SOURCE_LABEL,
        title: snapshot.label,
        snippet: snapshot.source,
        url: AUTOMATED_META_SOURCE_URL,
        publisher: snapshot.source,
        publishedAt: null,
        weight: snapshot.popularity_weight,
      },
      sourceText: normalizeSearchText(`${snapshot.label} ${snapshot.source} ${snapshot.result_label}`),
      kind: "export" as const,
    })),
    ...discoveryResult.rosterSnapshots.map((snapshot, index) => ({
      snapshot,
      sourceItem: discoveryResult.rosterEvidenceItems[index] ?? {
        sourceId: `auto-roster-${snapshot.slug}-${index}`,
        sourceLabel: AUTOMATED_META_SOURCE_LABEL,
        title: snapshot.label,
        snippet: snapshot.source,
        url: AUTOMATED_META_SOURCE_URL,
        publisher: snapshot.source,
        publishedAt: null,
        weight: snapshot.popularity_weight,
      },
      sourceText: normalizeSearchText(`${snapshot.label} ${snapshot.source} ${snapshot.result_label}`),
      kind: "roster" as const,
    })),
  ];
  const automatedSnapshots = aggregateAutomatedSnapshotCandidates(automatedCandidates);
  const hasInsufficientAutomatedCoverage = automatedSnapshots.length > 0
    && automatedSnapshots.length < MIN_AUTOMATED_SNAPSHOTS_FOR_REBUILD;

  if (!automatedSnapshots.length || hasInsufficientAutomatedCoverage) {
    if (options?.seedDocuments?.length) {
      const fallbackNote = !automatedSnapshots.length
        ? "No tournament-result snapshot rebuild was strong enough, so the published board was re-ranked from the existing board using the narrower result-and-popularity evidence set."
        : `Only ${automatedSnapshots.length} tournament-result snapshots were discovered, so the published board was re-ranked from the existing board instead of collapsing to a thin rebuild.`;
      return Promise.all(options.seedDocuments.map(async (document) =>
        enrichMetaSnapshotDocument(
          {
            ...document,
            sourceLabel: AUTOMATED_META_SOURCE_LABEL,
            commonMetaPokemon: [],
            notes: appendNotes(document.notes, [fallbackNote]),
          },
          [...liveEvidence.items, ...discoveryResult.rosterEvidenceItems],
          liveEvidence.succeededSources,
          liveEvidence.failedSourceCount,
          liveEvidence.failedSources,
          [],
          discoveryResult.diagnostics,
        ),
      ));
    }

    if (hasInsufficientAutomatedCoverage) {
      throw new Error(`Only ${automatedSnapshots.length} tournament-result snapshots were discovered, which is below the minimum rebuild threshold of ${MIN_AUTOMATED_SNAPSHOTS_FOR_REBUILD}.`);
    }

    throw new Error("No automated meta snapshots could be generated from the current live sources.");
  }

  const baseDocument = {
    ...automationSeed,
    tournamentTeamSnapshots: automatedSnapshots,
  } satisfies PublishedMetaSnapshotDocument;

  return [
    enrichMetaSnapshotDocument(
      baseDocument,
      [...liveEvidence.items, ...discoveryResult.rosterEvidenceItems],
      liveEvidence.succeededSources,
      liveEvidence.failedSourceCount,
      liveEvidence.failedSources,
      [],
      discoveryResult.diagnostics,
    ),
  ];
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}

function roundToTwo(value: number) {
  return Number(value.toFixed(2));
}

function buildSnapshotRank(snapshot: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"][number]) {
  return (0.68 * snapshot.popularity_weight + 0.32 * snapshot.result_weight) * snapshot.field_relevance;
}

function appendNotes(existingNotes: string[], newNotes: string[]) {
  return [...existingNotes, ...newNotes.map(truncateNote).filter(Boolean)].slice(-20);
}

function enrichMetaSnapshotDocument(
  document: PublishedMetaSnapshotDocument,
  liveItems: LiveEvidenceItem[],
  succeededSources: string[],
  failedSourceCount: number,
  failedSources: LiveIngestionFailure[],
  discoveredSnapshots: PublishedMetaSnapshotDocument["tournamentTeamSnapshots"],
  diagnostics: LiveDiscoveryDiagnostics,
): PublishedMetaSnapshotDocument {
  if (document.regulationId !== "champions_regulation_m_a") {
    return document;
  }

  const trackedSnapshots = [...document.tournamentTeamSnapshots, ...discoveredSnapshots].sort((left, right) => {
    const rankDifference = buildSnapshotRank(right) - buildSnapshotRank(left);
    if (Math.abs(rankDifference) > 0.001) {
      return rankDifference;
    }
    return left.label.localeCompare(right.label);
  });
  const descriptors = trackedSnapshots.map(buildSnapshotDescriptor);
  const visibilityScores = new Map<string, number>();
  const resultScores = new Map<string, number>();
  const mentionCounts = new Map<string, number>();

  for (const descriptor of descriptors) {
    visibilityScores.set(descriptor.snapshot.slug, 0);
    resultScores.set(descriptor.snapshot.slug, 0);
    mentionCounts.set(descriptor.snapshot.slug, 0);
  }

  for (const item of liveItems) {
    for (const descriptor of descriptors) {
      const score = scoreEvidenceItem(item, descriptor);
      if (!score.matched) {
        continue;
      }

      const slug = descriptor.snapshot.slug;
      visibilityScores.set(slug, (visibilityScores.get(slug) ?? 0) + score.visibility);
      resultScores.set(slug, (resultScores.get(slug) ?? 0) + score.result);
      mentionCounts.set(slug, (mentionCounts.get(slug) ?? 0) + 1);
    }
  }

  const maxVisibility = Math.max(...visibilityScores.values(), 0);
  const maxResult = Math.max(...resultScores.values(), 0);
  const matchedShellCount = [...mentionCounts.values()].filter((count) => count > 0).length;
  const discoveryNote = discoveredSnapshots.length
    ? `Discovered ${discoveredSnapshots.length} new export-backed shells from live sources: ${discoveredSnapshots.map((snapshot) => snapshot.label).join(", ")}.`
    : "No new export-backed shells were discovered during this live-source pass.";
  const skipNote = diagnostics.skippedReason ? `Deep discovery skipped: ${diagnostics.skippedReason}.` : "";
  const diagnosticsNote = `Discovery diagnostics: fetched ${diagnostics.candidatePagesFetched.length} candidate pages; page failures ${diagnostics.candidatePageFailures.length}; export pages ${diagnostics.exportPages.length}; roster pages ${diagnostics.rosterPages.length}; analyzer failures ${diagnostics.analyzerFailures.length}.`;
  const sourceFailureNote = failedSources.length ? `Source failures: ${formatFailureList(failedSources)}.` : "";
  const extractionOutcomeParts = [
    diagnostics.candidatePageFailures.length
      ? `page failures ${formatFailureList(diagnostics.candidatePageFailures)}`
      : "",
    diagnostics.exportPages.length ? `export pages ${formatDiagnosticList(diagnostics.exportPages)}` : "",
    diagnostics.rosterPages.length ? `roster pages ${formatDiagnosticList(diagnostics.rosterPages)}` : "",
    diagnostics.analyzerFailures.length ? `analyzer failures ${formatFailureList(diagnostics.analyzerFailures)}` : "",
  ].filter(Boolean);
  const extractionOutcomeNote = extractionOutcomeParts.length
    ? `Extraction highlights: ${extractionOutcomeParts.join("; ")}.`
    : "";
  const supplementalNotes = [
    skipNote,
    diagnosticsNote,
    sourceFailureNote,
    extractionOutcomeNote,
  ].filter(Boolean);

  if (maxVisibility <= 0) {
    return {
      ...document,
      updatedAt: new Date().toISOString(),
      sourceLabel: document.sourceLabel ?? LIVE_SOURCE_LABEL,
      commonMetaPokemon: [],
      notes: appendNotes(document.notes, [
        `Live-source ingestion monitored ${liveItems.length} evidence items across ${succeededSources.length} successful sources${failedSourceCount ? `; ${failedSourceCount} sources failed.` : "."}`,
        discoveryNote,
        ...supplementalNotes,
      ]),
      tournamentTeamSnapshots: trackedSnapshots,
    };
  }

  const updatedSnapshots = trackedSnapshots
    .map((snapshot) => {
      const slug = snapshot.slug;
      const scaledVisibility = (visibilityScores.get(slug) ?? 0) / maxVisibility;
      const scaledResult = maxResult > 0 ? (resultScores.get(slug) ?? 0) / maxResult : 0;
      const mentionCount = mentionCounts.get(slug) ?? 0;

      const fieldRelevance = clamp(
        snapshot.field_relevance * 0.9 + 0.26 * scaledVisibility + Math.min(0.12, mentionCount * 0.02),
        0,
        2,
      );
      const popularityWeight = clamp(
        snapshot.popularity_weight * 0.88 + 0.34 * scaledVisibility + Math.min(0.1, mentionCount * 0.015),
        0,
        2,
      );
      const resultWeight = clamp(snapshot.result_weight * 0.92 + 0.26 * scaledResult, 0, 2);

      return {
        ...snapshot,
        field_relevance: roundToTwo(fieldRelevance),
        popularity_weight: roundToTwo(popularityWeight),
        result_weight: roundToTwo(resultWeight),
      };
    })
    .sort((left, right) => {
      const rankDifference = buildSnapshotRank(right) - buildSnapshotRank(left);
      if (Math.abs(rankDifference) > 0.001) {
        return rankDifference;
      }
      return left.label.localeCompare(right.label);
    });

  const strongestLifts = [...updatedSnapshots]
    .filter((snapshot) => (mentionCounts.get(snapshot.slug) ?? 0) > 0)
    .slice(0, 3)
    .map((snapshot) => snapshot.label);

  return {
    ...document,
    updatedAt: new Date().toISOString(),
    sourceLabel: document.sourceLabel ?? LIVE_SOURCE_LABEL,
    commonMetaPokemon: [],
    notes: appendNotes(document.notes, [
      `Live-source ingestion analyzed ${liveItems.length} evidence items across ${succeededSources.length} successful sources${failedSourceCount ? `; ${failedSourceCount} sources failed.` : "."}`,
      `Signals blended from ${succeededSources.join(", ")}.`,
      `Shells with the strongest live-source lift right now: ${strongestLifts.join(", ") || "none"}. ${matchedShellCount} tracked shells received direct evidence hits.`,
      discoveryNote,
      ...supplementalNotes,
    ]),
    tournamentTeamSnapshots: updatedSnapshots,
  };
}

export async function enrichMetaSnapshotDocumentsWithLiveSignals(
  documents: PublishedMetaSnapshotDocument[],
  options?: LiveSignalEnrichmentOptions,
) {
  const enrichmentStartedAt = Date.now();
  const deepDiscoveryEnabled = options?.deepDiscoveryEnabled
    ?? (process.env.POKEMON_ANALYZER_ENABLE_DEEP_DISCOVERY?.trim() === "1" || !process.env.VERCEL);
  const sourceMode = options?.sourceMode ?? (deepDiscoveryEnabled ? "all" : "default");
  const liveEvidence = await collectLiveEvidenceItems({ sourceMode });
  if (!liveEvidence.items.length && !liveEvidence.failedSourceCount) {
    return documents;
  }

  const runtimeBudgetMs = options?.runtimeBudgetMs ?? DISCOVERY_RUNTIME_BUDGET_MS;
  const skipReason = process.env.VERCEL && !deepDiscoveryEnabled
    ? "handled by the dedicated deep-refresh route on Vercel; set POKEMON_ANALYZER_ENABLE_DEEP_DISCOVERY=1 to force it on this route"
    : Date.now() - enrichmentStartedAt > runtimeBudgetMs
      ? "runtime budget was exhausted by base live-source collection"
      : undefined;

  return Promise.all(
    documents.map(async (document) => {
      const discoveryResult = await discoverLiveTournamentSnapshots(document, liveEvidence.items, { skipReason });
      return enrichMetaSnapshotDocument(
        document,
        [...liveEvidence.items, ...discoveryResult.rosterEvidenceItems],
        liveEvidence.succeededSources,
        liveEvidence.failedSourceCount,
        liveEvidence.failedSources,
        discoveryResult.discoveredSnapshots,
        discoveryResult.diagnostics,
      );
    }),
  );
}