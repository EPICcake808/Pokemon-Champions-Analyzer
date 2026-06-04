import { NextResponse } from "next/server";

import { isDatabaseConfigured } from "@/db";
import {
  AUTOMATED_META_SOURCE_URL,
  buildAutomatedMetaSnapshotDocuments,
} from "@/lib/live-meta-ingestion";
import {
  fetchMetaSnapshotSource,
  getPublishedMetaSnapshot,
  isMetaSnapshotRefreshAuthorized,
  type PublishedMetaSnapshotDocument,
  upsertPublishedMetaSnapshot,
} from "@/lib/meta-snapshots";

export const runtime = "nodejs";
export const maxDuration = 60;

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

async function getSeedDocuments() {
  const sourceUrl = process.env.META_SNAPSHOT_SOURCE_URL?.trim();
  if (sourceUrl) {
    try {
      const sourceDocuments = await fetchMetaSnapshotSource(sourceUrl);
      const regulationDocument = sourceDocuments.find((document) => document.regulationId === "champions_regulation_m_a");
      if (regulationDocument) {
        return [regulationDocument];
      }
    } catch {
      // Fall through to the currently published board if the source feed is temporarily unavailable.
    }
  }

  const publishedSnapshot = await getPublishedMetaSnapshot("champions_regulation_m_a");
  return publishedSnapshot ? [toPublishedSnapshotDocument(publishedSnapshot)!] : [];
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

  try {
    const seedDocuments = await getSeedDocuments();
    const documents = await buildAutomatedMetaSnapshotDocuments({
      sourceMode: "deep-only",
      runtimeBudgetMs: 45_000,
      seedDocuments,
    });
    const refreshedSnapshots = [];

    for (const document of documents) {
      const refreshedSnapshot = await upsertPublishedMetaSnapshot({
        document,
        sourceUrl: AUTOMATED_META_SOURCE_URL,
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