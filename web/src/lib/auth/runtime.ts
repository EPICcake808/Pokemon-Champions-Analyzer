import "server-only";

export function isAuthConfigured() {
  return Boolean(process.env.DATABASE_URL && process.env.AUTH_SECRET);
}

export function isGoogleAuthConfigured() {
  return Boolean(isAuthConfigured() && process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET);
}

export function getAuthSecret() {
  return process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET ?? "local-development-only-secret-change-me";
}
