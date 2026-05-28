import "dotenv/config";

import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import { defineConfig } from "drizzle-kit";

function readEnvFileValue(filePath: string, key: string) {
  if (!existsSync(filePath)) {
    return undefined;
  }

  const contents = readFileSync(filePath, "utf8");
  const line = contents
    .split(/\r?\n/)
    .find((entry) => entry.startsWith(`${key}=`));

  if (!line) {
    return undefined;
  }

  return line.slice(`${key}=`.length).trim().replace(/^"|"$/g, "");
}

const databaseUrl =
  process.env.DATABASE_URL ??
  readEnvFileValue(path.resolve(process.cwd(), ".env.local"), "DATABASE_URL");

if (!databaseUrl) {
  throw new Error("DATABASE_URL is required to run Drizzle commands.");
}

export default defineConfig({
  schema: "./src/db/schema.ts",
  out: "./drizzle",
  dialect: "postgresql",
  dbCredentials: {
    url: databaseUrl,
  },
  strict: true,
  verbose: true,
});
