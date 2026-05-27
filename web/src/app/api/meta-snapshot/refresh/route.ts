import { NextResponse } from "next/server";

import { isDatabaseConfigured } from "@/db";
import {
  fetchMetaSnapshotSource,
  isMetaSnapshotRefreshAuthorized,
  upsertPublishedMetaSnapshot,
} from "@/lib/meta-snapshots";

export const runtime = "nodejs";

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

  const sourceUrl = process.env.META_SNAPSHOT_SOURCE_URL?.trim() || "";
  if (!sourceUrl) {
    return NextResponse.json(
      {
        message: "META_SNAPSHOT_SOURCE_URL is not configured.",
      },
      { status: 503 },
    );
  }

  try {
    const documents = await fetchMetaSnapshotSource(sourceUrl);
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