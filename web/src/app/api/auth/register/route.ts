import { NextResponse } from "next/server";
import { z } from "zod";

import { isAuthConfigured } from "@/lib/auth/runtime";
import { hashPassword } from "@/lib/auth/password";
import { USERNAME_PATTERN } from "@/lib/auth/usernames";
import {
  createCredentialsUser,
  findUserByEmail,
  findUserByUsername,
  isUniqueConstraintError,
  normalizeEmailInput,
  toAuthSessionUser,
} from "@/lib/auth/users";

export const runtime = "nodejs";

const registerSchema = z.object({
  username: z
    .string()
    .trim()
    .min(3, "Usernames must be at least 3 characters.")
    .max(24, "Usernames must be 24 characters or fewer.")
    .regex(USERNAME_PATTERN, "Usernames can only use lowercase letters, numbers, and underscores."),
  email: z.string().trim().email("Enter a valid email address."),
  password: z
    .string()
    .min(8, "Passwords must be at least 8 characters.")
    .max(72, "Passwords must be 72 characters or fewer."),
});

export async function POST(request: Request) {
  if (!isAuthConfigured()) {
    return NextResponse.json(
      {
        message: "Account features are not configured yet.",
      },
      { status: 503 },
    );
  }

  try {
    const rawPayload = (await request.json()) as Record<string, unknown>;
    const parsedPayload = registerSchema.safeParse({
      username: typeof rawPayload.username === "string" ? rawPayload.username.toLowerCase() : rawPayload.username,
      email: rawPayload.email,
      password: rawPayload.password,
    });

    if (!parsedPayload.success) {
      return NextResponse.json(
        {
          message: parsedPayload.error.issues[0]?.message ?? "The sign-up payload is invalid.",
        },
        { status: 400 },
      );
    }

    const username = parsedPayload.data.username;
    const email = normalizeEmailInput(parsedPayload.data.email);

    const [existingUsername, existingEmail] = await Promise.all([
      findUserByUsername(username),
      findUserByEmail(email),
    ]);

    if (existingUsername) {
      return NextResponse.json(
        {
          message: "That username is already taken.",
        },
        { status: 409 },
      );
    }

    if (existingEmail) {
      return NextResponse.json(
        {
          message: "An account with that email already exists.",
        },
        { status: 409 },
      );
    }

    const passwordHash = await hashPassword(parsedPayload.data.password);
    const user = await createCredentialsUser({
      username,
      email,
      passwordHash,
    });

    return NextResponse.json(
      {
        ok: true,
        user: toAuthSessionUser(user),
      },
      { status: 201 },
    );
  } catch (error) {
    if (isUniqueConstraintError(error)) {
      return NextResponse.json(
        {
          message: "That username or email is already in use.",
        },
        { status: 409 },
      );
    }

    return NextResponse.json(
      {
        message: error instanceof Error ? error.message : "The sign-up request failed.",
      },
      { status: 400 },
    );
  }
}
