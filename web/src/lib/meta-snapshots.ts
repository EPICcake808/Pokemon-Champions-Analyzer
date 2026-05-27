import "server-only";

import { eq } from "drizzle-orm";
import { z } from "zod";

import { db } from "@/db";
import { publishedMetaSnapshots } from "@/db/schema";

const snapshotString = z.string().trim().min(1);

export const tournamentTeamSnapshotSchema = z
  .object({
    slug: snapshotString.max(120),
    label: snapshotString.max(120),
    source: snapshotString.max(240),
    result_label: snapshotString.max(120),
    field_relevance: z.number().min(0).max(2),
    popularity_weight: z.number().min(0).max(2),
    result_weight: z.number().min(0).max(2),
    modes: z.array(snapshotString.max(80)).min(1).max(8),
    mode_weights: z.record(z.string(), z.number().min(0).max(4)),
    broad_mix: z.record(z.string(), z.number().min(0).max(4)),
    key_pokemon: z.array(snapshotString.max(80)).min(1).max(12),
    key_cores: z.array(snapshotString.max(160)).min(1).max(8),
  })
  .superRefine((snapshot, context) => {
    for (const mode of snapshot.modes) {
      if (!(mode in snapshot.mode_weights)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: `mode_weights is missing an entry for ${mode}.`,
          path: ["mode_weights", mode],
        });
      }
    }
  });

export const publishedMetaSnapshotDocumentSchema = z.object({
  regulationId: snapshotString.max(120),
  updatedAt: z.string().datetime().optional(),
  sourceLabel: snapshotString.max(240).optional(),
  notes: z.array(snapshotString.max(400)).max(20).default([]),
  tournamentTeamSnapshots: z.array(tournamentTeamSnapshotSchema).min(1).max(64),
});

export const metaSnapshotFeedSchema = z.object({
  version: z.literal(1),
  generatedAt: z.string().datetime().optional(),
  regulations: z.array(publishedMetaSnapshotDocumentSchema).min(1).max(16),
});

export type PublishedMetaSnapshotDocument = z.infer<typeof publishedMetaSnapshotDocumentSchema>;

export type PublishedMetaSnapshotResponse = PublishedMetaSnapshotDocument & {
  refreshedAt: string;
  sourceUrl: string | null;
};

function serializePublishedMetaSnapshot(
  row: typeof publishedMetaSnapshots.$inferSelect,
): PublishedMetaSnapshotResponse {
  const payload = publishedMetaSnapshotDocumentSchema.parse(row.payload);
  return {
    ...payload,
    refreshedAt: row.refreshedAt.toISOString(),
    sourceUrl: row.sourceUrl,
  };
}

export async function getPublishedMetaSnapshot(regulationId: string) {
  const [row] = await db
    .select()
    .from(publishedMetaSnapshots)
    .where(eq(publishedMetaSnapshots.regulationId, regulationId))
    .limit(1);

  return row ? serializePublishedMetaSnapshot(row) : null;
}

export async function upsertPublishedMetaSnapshot({
  document,
  sourceUrl,
}: {
  document: PublishedMetaSnapshotDocument;
  sourceUrl: string | null;
}) {
  const now = new Date();
  const [row] = await db
    .insert(publishedMetaSnapshots)
    .values({
      regulationId: document.regulationId,
      payload: document,
      sourceUrl,
      refreshedAt: now,
      createdAt: now,
      updatedAt: now,
    })
    .onConflictDoUpdate({
      target: publishedMetaSnapshots.regulationId,
      set: {
        payload: document,
        sourceUrl,
        refreshedAt: now,
        updatedAt: now,
      },
    })
    .returning();

  return serializePublishedMetaSnapshot(row);
}

export async function fetchMetaSnapshotSource(sourceUrl: string) {
  const response = await fetch(sourceUrl, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "User-Agent": "pokemon-champions-analyzer-meta-refresh/0.1",
    },
  });

  if (!response.ok) {
    throw new Error(`The meta snapshot source responded with ${response.status}.`);
  }

  const parsedPayload = metaSnapshotFeedSchema.safeParse(await response.json());
  if (!parsedPayload.success) {
    throw new Error(parsedPayload.error.issues[0]?.message ?? "The meta snapshot source payload is invalid.");
  }

  return parsedPayload.data.regulations;
}

export function isMetaSnapshotRefreshAuthorized(request: Request) {
  const expectedSecret =
    process.env.META_SNAPSHOT_REFRESH_SECRET?.trim() || process.env.CRON_SECRET?.trim() || "";
  if (!expectedSecret) {
    return false;
  }

  const authorization = request.headers.get("authorization")?.trim();
  return authorization === `Bearer ${expectedSecret}`;
}