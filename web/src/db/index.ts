import "server-only";

import { neon } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-http";

import * as schema from "@/db/schema";

const fallbackDatabaseUrl = "postgresql://placeholder:placeholder@localhost:5432/pokemon_champions_analyzer";
const databaseUrl = process.env.DATABASE_URL ?? fallbackDatabaseUrl;

const sql = neon(databaseUrl);

export const db = drizzle({ client: sql, schema });

export function isDatabaseConfigured() {
  return Boolean(process.env.DATABASE_URL);
}
