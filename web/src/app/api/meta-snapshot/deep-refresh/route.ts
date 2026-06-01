import { NextResponse } from "next/server";

import { isDatabaseConfigured } from "@/db";
import { enrichMetaSnapshotDocumentsWithLiveSignals } from "@/lib/live-meta-ingestion";
import {
  fetchMetaSnapshotSource,
  getPublishedMetaSnapshot,
  isMetaSnapshotRefreshAuthorized,
  type PublishedMetaSnapshotDocument,
  upsertPublishedMetaSnapshot,
} from "@/lib/meta-snapshots";

export const runtime = "nodejs";
export const maxDuration = 60;

function resolveMetaSnapshotSourceUrl() {
  const configuredSourceUrl = process.env.META_SNAPSHOT_SOURCE_URL?.trim() || "";
  if (configuredSourceUrl) {
    return configuredSourceUrl;
  }

  const analyzerApiBaseUrl = process.env.POKEMON_ANALYZER_API_BASE_URL?.trim() || "";
  if (!analyzerApiBaseUrl) {
    return "";
  }

  return `${analyzerApiBaseUrl.replace(/\/+$/, "")}/api/meta-snapshot-source`;
}

function toPublishedSnapshotDocument(
  snapshot: Awaited<ReturnType<typeof getPublishedMetaSnapshot>>,
): PublishedMetaSnapshotDocument | null {
  if (!snapshot) {
    return null;
  }

  return {
    regulationId: snapshot.regulationId,
    updatedAt: snapshot.updatedAt,
    sourceLabel: snapshot.sourceLabel,
    notes: snapshot.notes,
    commonMetaPokemon: snapshot.commonMetaPokemon,
    tournamentTeamSnapshots: snapshot.tournamentTeamSnapshots,
  };
}

async function loadDeepRefreshBaseDocuments(sourceUrl: string) {
  const sourceDocuments = await fetchMetaSnapshotSource(sourceUrl);
  return Promise.all(
    sourceDocuments.map(async (sourceDocument) => {
      const publishedSnapshot = await getPublishedMetaSnapshot(sourceDocument.regulationId);
      return toPublishedSnapshotDocument(publishedSnapshot) ?? sourceDocument;
    }),
  );
}

async function refreshDeepMetaSnapshots(request: Request) {
  if (!isMetaSnapshotRefreshAuthorized(request)) {
    return NextResponse.json(
      {
        message: "The deep meta snapshot refresh request is not authorized.",
      },
      { status: 401 },
    );
  }

  if (!isDatabaseConfigured()) {
    return NextResponse.json(
      {
        message: "Meta snapshot storage is not configured yet.",
      },
      { status: 503 },
    );
  }

  const sourceUrl = resolveMetaSnapshotSourceUrl();
  if (!sourceUrl) {
    return NextResponse.json(
      {
        message: "Neither META_SNAPSHOT_SOURCE_URL nor POKEMON_ANALYZER_API_BASE_URL is configured.",
      },
      { status: 503 },
    );
  }

  try {
    const baseDocuments = await loadDeepRefreshBaseDocuments(sourceUrl);
    const documents = await enrichMetaSnapshotDocumentsWithLiveSignals(baseDocuments, {
      deepDiscoveryEnabled: true,
      sourceMode: "deep-only",
      runtimeBudgetMs: 45_000,
    });
    const refreshedSnapshots = [];

    for (const document of documents) {
      const refreshedSnapshot = await upsertPublishedMetaSnapshot({
        document,
        sourceUrl,
      });
      refreshedSnapshots.push({
        regulationId: refreshedSnapshot.regulationId,
        sourceLabel: refreshedSnapshot.sourceLabel ?? null,
        refreshedAt: refreshedSnapshot.refreshedAt,
      });
    }

    return NextResponse.json({
      refreshed: refreshedSnapshots,
      count: refreshedSnapshots.length,
      deepDiscovery: true,
    });
  } catch (error) {
    return NextResponse.json(
      {
        message: error instanceof Error ? error.message : "The deep meta snapshot refresh failed.",
      },
      { status: 502 },
    );
  }
}

export async function GET(request: Request) {
  return refreshDeepMetaSnapshots(request);
}

export async function POST(request: Request) {
  return refreshDeepMetaSnapshots(request);
}