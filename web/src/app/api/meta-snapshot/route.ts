import { NextResponse } from "next/server";

import { isDatabaseConfigured } from "@/db";
import { getPublishedMetaSnapshot } from "@/lib/meta-snapshots";
import { DEFAULT_REGULATION_ID } from "@/lib/python-analyzer";

export const runtime = "nodejs";

export async function GET(request: Request) {
  if (!isDatabaseConfigured()) {
    return NextResponse.json(
      {
        message: "Meta snapshot storage is not configured yet.",
      },
      { status: 503 },
    );
  }

  const regulationId = new URL(request.url).searchParams.get("regulationId")?.trim() || DEFAULT_REGULATION_ID;
  const snapshot = await getPublishedMetaSnapshot(regulationId);

  if (!snapshot) {
    return NextResponse.json(
      {
        message: `No published meta snapshot exists for ${regulationId}.`,
      },
      { status: 404 },
    );
  }

  return NextResponse.json(snapshot, {
    headers: {
      "Cache-Control": "public, s-maxage=300, stale-while-revalidate=600",
    },
  });
}