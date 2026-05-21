import "server-only";

export const USERNAME_PATTERN = /^[a-z0-9_]{3,24}$/;

export function normalizeUsernameInput(username: string) {
  return username.trim().toLowerCase();
}

export function sanitizeUsernameCandidate(input: string) {
  const asciiInput = input.normalize("NFKD").replace(/[^\x00-\x7F]/g, "");
  const normalized = asciiInput
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");

  if (!normalized) {
    return "trainer";
  }

  if (normalized.length >= 3) {
    return normalized.slice(0, 24);
  }

  return `${normalized}${"trainer".slice(0, 3 - normalized.length)}`;
}

export function isValidUsername(username: string) {
  return USERNAME_PATTERN.test(normalizeUsernameInput(username));
}

export function buildUsernameCandidate(baseInput: string, suffix: number) {
  const base = sanitizeUsernameCandidate(baseInput);
  if (suffix <= 0) {
    return base;
  }

  const suffixText = String(suffix);
  const maxBaseLength = Math.max(3, 24 - suffixText.length);
  return `${base.slice(0, maxBaseLength)}${suffixText}`;
}
