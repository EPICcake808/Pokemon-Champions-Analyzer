import { NextResponse } from "next/server";

import { isDatabaseConfigured } from "@/db";
import {
  isMetaSnapshotRefreshAuthorized,
  metaSnapshotFeedSchema,
  upsertPublishedMetaSnapshot,
} from "@/lib/meta-snapshots";

export const runtime = "nodejs";
export const maxDuration = 60;

// Source marker for boards published by the external (GitHub Actions) ingestion job.
const PUBLISH_SOURCE_URL = "github-actions://meta-ingest";

/**
 * Inverted-pipeline publish endpoint.
 *
 * The heavy ingestion (scraping, usage stats, discovery, reconciliation) runs in a
 * scheduled GitHub Action with a full Python runtime — NOT in this request path. That
 * job POSTs the already-built, already-validated feed here; this route only authorizes,
 * re-validates against the canonical schema, and upserts it into the published board.
 */
async function publishMetaSnapshots(request: Request) {
  if (!isMetaSnapshotRefreshAuthorized(request)) {
    return NextResponse.json(
      { message: "The meta snapshot publish request is not authorized." },
      { status: 401 },
    );
  }

  if (!isDatabaseConfigured()) {
    return NextResponse.json(
      { message: "Meta snapshot storage is not configured yet." },
      { status: 503 },
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ message: "Request body must be valid JSON." }, { status: 400 });
  }

  const parsed = metaSnapshotFeedSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      {
        message: "The posted meta snapshot feed is invalid.",
        issues: parsed.error.issues.slice(0, 10),
      },
      { status: 422 },
    );
  }

  try {
    const published = [];
    for (const document of parsed.data.regulations) {
      const snapshot = await upsertPublishedMetaSnapshot({
        document,
        sourceUrl: PUBLISH_SOURCE_URL,
      });
      published.push({
        regulationId: snapshot.regulationId,
        sourceLabel: snapshot.sourceLabel ?? null,
        refreshedAt: snapshot.refreshedAt,
      });
    }

    return NextResponse.json({ published, count: published.length });
  } catch (error) {
    return NextResponse.json(
      { message: error instanceof Error ? error.message : "The meta snapshot publish failed." },
      { status: 502 },
    );
  }
}

export async function POST(request: Request) {
  return publishMetaSnapshots(request);
}
