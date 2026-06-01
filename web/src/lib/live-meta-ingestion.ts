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

type ArticleRosterExtractor = {
  id: string;
  hostPattern: RegExp;
  sectionTerms: string[];
  minSpeciesCount: number;
};

type ExtractedArticleRoster = {
  sourceItem: LiveEvidenceItem;
  extractorId: string;
  label: string;
  speciesTokens: string[];
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

const LIVE_SOURCE_HEADERS = {
  Accept: "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
  "User-Agent": "pokemon-champions-analyzer-live-ingestion/0.2.1",
};

const LIVE_SOURCE_TIMEOUT_MS = 7_000;
const EXPORT_PAGE_TIMEOUT_MS = 2_500;
const ANALYZE_EXPORT_TIMEOUT_MS = 18_000;
const LIVE_SOURCE_LABEL = "Pokemon Champions Analyzer live-source Regulation M-A meta board";
const MAX_EXPORT_SOURCE_PAGES = 4;
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
  "top cut",
  "top 8",
  "top 16",
  "finalist",
  "deep run",
  "rank one",
  "rank 1",
  "metagame",
  "meta",
  "tournament",
  "analysis",
  "guide",
  "recap",
  "report",
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

const ARTICLE_ROSTER_EXTRACTORS: ArticleRosterExtractor[] = [
  {
    id: "pokemon-gallery",
    hostPattern: /(^|\.)pokemon\.com$/i,
    sectionTerms: ["team", "gallery", "replica", "rental", "code"],
    minSpeciesCount: 5,
  },
  {
    id: "guide-sites",
    hostPattern: /(^|\.)(insider-gaming\.com|games\.gg|ign\.com|esports\.gg|dotesports\.com|game8\.co|gamewith\.net|nintendolife\.com|screenrant\.com|thegamer\.com)$/i,
    sectionTerms: ["team", "replica", "best", "code", "guide", "rental", "sample", "build", "report"],
    minSpeciesCount: 5,
  },
];

const DEFAULT_LIVE_SOURCES: LiveSourceDefinition[] = [
  {
    id: "google-news-regulation",
    label: "Google News: Regulation M-A",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=Pokemon+Champions+Regulation+M-A",
    weight: 1,
    maxItems: 12,
  },
  {
    id: "google-news-meta",
    label: "Google News: Pokemon Champions meta",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=Pokemon+Champions+meta",
    weight: 0.95,
    maxItems: 12,
  },
  {
    id: "google-news-tournaments",
    label: "Google News: Pokemon Champions tournaments",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=Pokemon+Champions+tournament",
    weight: 0.95,
    maxItems: 12,
  },
  {
    id: "youtube-regulation",
    label: "YouTube search: Regulation M-A",
    kind: "youtube-search",
    url: "https://www.youtube.com/results?search_query=Pokemon+Champions+Regulation+M-A",
    weight: 0.85,
    maxItems: 10,
  },
  {
    id: "youtube-meta",
    label: "YouTube search: Pokemon Champions meta",
    kind: "youtube-search",
    url: "https://www.youtube.com/results?search_query=Pokemon+Champions+meta",
    weight: 0.82,
    maxItems: 10,
  },
  {
    id: "reddit-meta",
    label: "old Reddit search: Pokemon Champions meta",
    kind: "reddit-search",
    url: "https://old.reddit.com/search/?q=Pokemon+Champions+meta&sort=new&type=link",
    weight: 0.78,
    maxItems: 10,
  },
  {
    id: "reddit-tournaments",
    label: "old Reddit search: Pokemon Champions tournaments",
    kind: "reddit-search",
    url: "https://old.reddit.com/search/?q=Pokemon+Champions+tournament&sort=new&type=link",
    weight: 0.78,
    maxItems: 10,
  },
  {
    id: "reddit-pokepast",
    label: "old Reddit search: Pokepaste Pokemon Champions",
    kind: "reddit-search",
    url: "https://old.reddit.com/search/?q=pokepast+%22Pokemon+Champions%22&sort=new&type=link",
    weight: 0.84,
    maxItems: 10,
    requiresDeepDiscovery: true,
  },
  {
    id: "reddit-showdown-export",
    label: "old Reddit search: Pokemon Champions Ability exports",
    kind: "reddit-search",
    url: "https://old.reddit.com/search/?q=%22Pokemon+Champions%22+%22Ability%3A%22&sort=new&type=link",
    weight: 0.8,
    maxItems: 10,
    requiresDeepDiscovery: true,
  },
  {
    id: "google-news-pokepast",
    label: "Google News: Pokepaste Pokemon Champions",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=pokepast+%22Pokemon+Champions%22",
    weight: 0.8,
    maxItems: 12,
    requiresDeepDiscovery: true,
  },
  {
    id: "google-news-rental-codes",
    label: "Google News: Pokemon Champions rental codes",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=%22Pokemon+Champions%22+%22rental+code%22",
    weight: 0.8,
    maxItems: 12,
    requiresDeepDiscovery: true,
  },
  {
    id: "google-news-best-teams",
    label: "Google News: Pokemon Champions best teams",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=%22Pokemon+Champions%22+%22best+team%22",
    weight: 0.78,
    maxItems: 12,
    requiresDeepDiscovery: true,
  },
  {
    id: "google-news-team-reports",
    label: "Google News: Pokemon Champions team reports",
    kind: "rss",
    url: "https://news.google.com/rss/search?q=%22Pokemon+Champions%22+%22team+report%22",
    weight: 0.79,
    maxItems: 12,
    requiresDeepDiscovery: true,
  },
  {
    id: "youtube-rental-codes",
    label: "YouTube search: Pokemon Champions rental codes",
    kind: "youtube-search",
    url: "https://www.youtube.com/results?search_query=Pokemon+Champions+rental+code",
    weight: 0.76,
    maxItems: 10,
    requiresDeepDiscovery: true,
  },
  {
    id: "youtube-best-teams",
    label: "YouTube search: Pokemon Champions best teams",
    kind: "youtube-search",
    url: "https://www.youtube.com/results?search_query=Pokemon+Champions+best+team",
    weight: 0.75,
    maxItems: 10,
    requiresDeepDiscovery: true,
  },
  {
    id: "youtube-team-reports",
    label: "YouTube search: Pokemon Champions team reports",
    kind: "youtube-search",
    url: "https://www.youtube.com/results?search_query=Pokemon+Champions+team+report",
    weight: 0.74,
    maxItems: 10,
    requiresDeepDiscovery: true,
  },
  {
    id: "serebii-champions",
    label: "Serebii Pokemon Champions page",
    kind: "html-page",
    url: "https://www.serebii.net/pokemonchampions/",
    weight: 0.6,
    maxItems: 1,
  },
  {
    id: "pokemon-home-regulation",
    label: "Pokemon HOME Regulation Set M-A page",
    kind: "html-page",
    url: "https://news.pokemon-home.com/en/page/751.html",
    weight: 0.5,
    maxItems: 1,
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

function findArticleRosterExtractor(url: string) {
  const hostname = hostnameForUrl(url);
  return ARTICLE_ROSTER_EXTRACTORS.find((extractor) => extractor.hostPattern.test(hostname)) ?? null;
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

function buildDocumentSpeciesPhraseIndex(document: PublishedMetaSnapshotDocument): SpeciesPhraseIndexEntry[] {
  const speciesTokens = uniqueStrings(document.tournamentTeamSnapshots.flatMap((snapshot) => snapshot.key_pokemon));
  return speciesTokens
    .flatMap((token) => {
      const phrases = uniqueStrings([
        normalizeSearchText(renderSpeciesToken(token)),
        normalizeSearchText(baseSpeciesPhrase(token)),
      ]).filter((phrase) => phrase.length >= 4 && !GENERIC_SEARCH_TERMS.has(phrase));
      return phrases.map((phrase) => ({ token, phrase }));
    })
    .sort((left, right) => right.phrase.length - left.phrase.length);
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

  const paragraphSections = htmlToTextWithLineBreaks(body)
    .split(/\n{2,}/g)
    .map((paragraph) => ({
      label: "",
      text: paragraph.trim(),
    }))
    .filter((section) => section.text.length >= 24 && section.text.length <= 900);

  return [...new Map([...listSections, ...headingSections, ...paragraphSections].map((section) => [
    `${normalizeSearchText(section.label)}|${normalizeSearchText(section.text).slice(0, 160)}`,
    section,
  ])).values()];
}

function extractArticleRosters(
  page: CandidateExportPage,
  document: PublishedMetaSnapshotDocument,
): ExtractedArticleRoster[] {
  const extractor = findArticleRosterExtractor(page.url);
  if (!extractor) {
    return [];
  }

  const phraseIndex = buildDocumentSpeciesPhraseIndex(document);
  const sectionCandidates = extractArticleRosterSections(page.body).filter((section) => {
    const text = normalizeSearchText(`${page.item.title} ${section.label}`);
    return extractor.sectionTerms.some((term) => text.includes(term));
  });

  const rosters = new Map<string, ExtractedArticleRoster>();
  for (const section of sectionCandidates) {
    const sectionBlocks = uniqueStrings([section.text, ...section.text.split(/\n{2,}/g)]);
    for (const block of sectionBlocks) {
      const speciesTokens = extractSpeciesTokensFromText(block, phraseIndex);
      if (speciesTokens.length < extractor.minSpeciesCount || speciesTokens.length > 6) {
        continue;
      }

      const rosterKey = speciesTokens.slice().sort().join("|");
      if (rosters.has(rosterKey)) {
        continue;
      }

      rosters.set(rosterKey, {
        sourceItem: page.item,
        extractorId: extractor.id,
        label: section.label || page.item.title,
        speciesTokens,
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

  const hasResultSignal = RESULT_SIGNAL_TERMS.some((term) => text.includes(term));
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
  if (text.includes("winner") || text.includes("champion") || text.includes("won")) {
    return "live winner signal";
  }
  if (text.includes("top 8") || text.includes("top cut") || text.includes("finalist")) {
    return "live top-cut export";
  }
  if (text.includes("rank one") || text.includes("rank 1")) {
    return "live high-ladder export";
  }
  if (text.includes("guide") || text.includes("featured") || text.includes("replica")) {
    return "live featured export";
  }
  return "live export discovery";
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
    body: await response.text(),
  };
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

  if (findArticleRosterExtractor(item.url)) {
    return true;
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
  const resultBoost = resultText.includes("winner") || resultText.includes("champion")
    ? 0.25
    : resultText.includes("top 8") || resultText.includes("top cut") || resultText.includes("finalist")
      ? 0.18
      : resultText.includes("rank one") || resultText.includes("rank 1")
        ? 0.14
        : 0.08;

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
  options?: { skipReason?: string },
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
      rosterEvidenceItems: [],
      diagnostics,
    };
  }

  if (diagnostics.skippedReason) {
    return {
      discoveredSnapshots: [],
      rosterEvidenceItems: [],
      diagnostics,
    };
  }

  const candidatePages = await collectCandidateExportPages(liveItems, diagnostics);
  const discoveredTeams = new Map<string, DiscoveredTeamExport>();
  const rosterEvidenceItems: LiveEvidenceItem[] = [];
  const seenRosterKeys = new Set<string>();

  for (const page of candidatePages) {
    for (const roster of extractArticleRosters(page, document)) {
      const rosterKey = roster.speciesTokens.slice().sort().join("|");
      if (seenRosterKeys.has(rosterKey)) {
        continue;
      }

      seenRosterKeys.add(rosterKey);
      rosterEvidenceItems.push(buildRosterEvidenceItem(roster));
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

  return {
    discoveredSnapshots: [...discoveredTeams.values()]
      .map(buildDiscoveredSnapshot)
      .filter((candidateSnapshot) =>
        !document.tournamentTeamSnapshots.some((trackedSnapshot) =>
          looksLikeTrackedSnapshot(candidateSnapshot.key_pokemon, candidateSnapshot.modes, trackedSnapshot),
        ),
      )
      .slice(0, MAX_EXTRACTED_TEAMS),
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
      return source.requiresDeepDiscovery;
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

  const dedupedItems = [...new Map(items.map((item) => [`${normalizeSearchText(item.title)}|${item.publisher}`, item])).values()];
  return {
    items: dedupedItems,
    succeededSources,
    failedSourceCount,
    failedSources,
  };
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
      sourceLabel: LIVE_SOURCE_LABEL,
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
    sourceLabel: LIVE_SOURCE_LABEL,
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