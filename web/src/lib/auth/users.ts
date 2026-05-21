import "server-only";

import { eq, or } from "drizzle-orm";

import { db } from "@/db";
import { users } from "@/db/schema";
import type { AuthSessionUser } from "@/lib/types";
import { buildUsernameCandidate } from "@/lib/auth/usernames";

type UserRow = typeof users.$inferSelect;

export function normalizeEmailInput(email: string) {
  return email.trim().toLowerCase();
}

export function toAuthSessionUser(user: Pick<UserRow, "id" | "username" | "name" | "email" | "image">): AuthSessionUser {
  return {
    id: user.id,
    username: user.username ?? null,
    name: user.name ?? null,
    email: user.email ?? null,
    image: user.image ?? null,
  };
}

export function toAuthProviderUser(user: UserRow) {
  return {
    id: user.id,
    name: user.name ?? user.username ?? null,
    email: user.email,
    image: user.image,
    username: user.username ?? null,
  };
}

export async function findUserById(userId: string) {
  const [user] = await db.select().from(users).where(eq(users.id, userId)).limit(1);
  return user ?? null;
}

export async function findUserByEmail(email: string) {
  const [user] = await db.select().from(users).where(eq(users.email, normalizeEmailInput(email))).limit(1);
  return user ?? null;
}

export async function findUserByUsername(username: string) {
  const [user] = await db.select().from(users).where(eq(users.username, username.trim().toLowerCase())).limit(1);
  return user ?? null;
}

export async function findUserByIdentifier(identifier: string) {
  const normalizedIdentifier = identifier.trim().toLowerCase();
  const [user] = await db
    .select()
    .from(users)
    .where(
      or(
        eq(users.email, normalizedIdentifier),
        eq(users.username, normalizedIdentifier),
      ),
    )
    .limit(1);

  return user ?? null;
}

export async function reserveUniqueUsername(baseInput: string) {
  for (let suffix = 0; suffix < 2000; suffix += 1) {
    const candidate = buildUsernameCandidate(baseInput, suffix);
    const existing = await findUserByUsername(candidate);
    if (!existing) {
      return candidate;
    }
  }

  throw new Error("A unique username could not be reserved.");
}

export async function ensureUserHasUsername(userId: string, preferredSources: Array<string | null | undefined>) {
  const currentUser = await findUserById(userId);
  if (!currentUser) {
    return null;
  }

  if (currentUser.username) {
    return currentUser.username;
  }

  const preferredSource = preferredSources.find((source) => Boolean(source?.trim())) ?? currentUser.email ?? currentUser.name ?? "trainer";
  const username = await reserveUniqueUsername(preferredSource);

  await db
    .update(users)
    .set({
      username,
      updatedAt: new Date(),
    })
    .where(eq(users.id, userId));

  return username;
}

export async function createCredentialsUser({
  username,
  email,
  passwordHash,
}: {
  username: string;
  email: string;
  passwordHash: string;
}) {
  const [user] = await db
    .insert(users)
    .values({
      username,
      name: username,
      email: normalizeEmailInput(email),
      passwordHash,
      updatedAt: new Date(),
    })
    .returning();

  return user;
}

export function isUniqueConstraintError(error: unknown) {
  return Boolean(
    error &&
      typeof error === "object" &&
      "code" in error &&
      (error as { code?: string }).code === "23505",
  );
}
