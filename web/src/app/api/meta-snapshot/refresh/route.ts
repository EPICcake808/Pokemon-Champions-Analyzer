import { NextResponse } from "next/server";

import { isDatabaseConfigured } from "@/db";
import {
  AUTOMATED_META_SOURCE_URL,
  buildAutomatedMetaSnapshotDocuments,
} from "@/lib/live-meta-ingestion";
import {
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

async function refreshMetaSnapshots(request: Request) {
  if (!isMetaSnapshotRefreshAuthorized(request)) {
    return NextResponse.json(
      {
        message: "The meta snapshot refresh request is not authorized.",
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
    const publishedSnapshot = await getPublishedMetaSnapshot("champions_regulation_m_a");
    const documents = await buildAutomatedMetaSnapshotDocuments({
      sourceMode: "default",
      seedDocuments: publishedSnapshot ? [toPublishedSnapshotDocument(publishedSnapshot)!] : [],
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
    });
  } catch (error) {
    return NextResponse.json(
      {
        message: error instanceof Error ? error.message : "The meta snapshot refresh failed.",
      },
      { status: 502 },
    );
  }
}

export async function GET(request: Request) {
  return refreshMetaSnapshots(request);
}

export async function POST(request: Request) {
  return refreshMetaSnapshots(request);
}