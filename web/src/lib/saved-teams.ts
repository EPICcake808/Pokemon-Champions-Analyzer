import "server-only";

import { and, desc, eq } from "drizzle-orm";

import { db } from "@/db";
import { savedTeams } from "@/db/schema";
import type { SavedTeamRecord } from "@/lib/types";

function serializeSavedTeam(row: typeof savedTeams.$inferSelect): SavedTeamRecord {
  return {
    id: row.id,
    name: row.name,
    teamText: row.teamText,
    regulationId: row.regulationId,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function listSavedTeamsForUser(userId: string) {
  const rows = await db
    .select()
    .from(savedTeams)
    .where(eq(savedTeams.userId, userId))
    .orderBy(desc(savedTeams.updatedAt));

  return rows.map(serializeSavedTeam);
}

export async function createSavedTeamForUser({
  userId,
  name,
  teamText,
  regulationId,
}: {
  userId: string;
  name: string;
  teamText: string;
  regulationId: string;
}) {
  const now = new Date();
  const [savedTeam] = await db
    .insert(savedTeams)
    .values({
      userId,
      name,
      teamText,
      regulationId,
      createdAt: now,
      updatedAt: now,
    })
    .returning();

  return serializeSavedTeam(savedTeam);
}

export async function updateSavedTeamForUser({
  teamId,
  userId,
  name,
  teamText,
  regulationId,
}: {
  teamId: string;
  userId: string;
  name: string;
  teamText: string;
  regulationId: string;
}) {
  const [savedTeam] = await db
    .update(savedTeams)
    .set({
      name,
      teamText,
      regulationId,
      updatedAt: new Date(),
    })
    .where(and(eq(savedTeams.id, teamId), eq(savedTeams.userId, userId)))
    .returning();

  return savedTeam ? serializeSavedTeam(savedTeam) : null;
}

export async function deleteSavedTeamForUser(teamId: string, userId: string) {
  const [deletedTeam] = await db
    .delete(savedTeams)
    .where(and(eq(savedTeams.id, teamId), eq(savedTeams.userId, userId)))
    .returning({ id: savedTeams.id });

  return Boolean(deletedTeam);
}
