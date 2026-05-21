import { NextResponse } from "next/server";
import { z } from "zod";

import { auth } from "@/auth";
import { isAuthConfigured } from "@/lib/auth/runtime";
import { createSavedTeamForUser, listSavedTeamsForUser } from "@/lib/saved-teams";

export const runtime = "nodejs";

const savedTeamSchema = z.object({
  name: z.string().trim().min(1, "Saved teams need a name.").max(80, "Saved team names must be 80 characters or fewer."),
  teamText: z.string().trim().min(1, "Build a roster before saving.").max(12000, "Team exports are too large to save."),
  regulationId: z.string().trim().min(1, "A regulation is required.").max(120),
});

export async function GET() {
  if (!isAuthConfigured()) {
    return NextResponse.json(
      {
        message: "Account features are not configured yet.",
      },
      { status: 503 },
    );
  }

  const session = await auth();
  const userId = session?.user?.id;
  if (!userId) {
    return NextResponse.json(
      {
        message: "Sign in to load saved teams.",
      },
      { status: 401 },
    );
  }

  const teams = await listSavedTeamsForUser(userId);
  return NextResponse.json({ teams });
}

export async function POST(request: Request) {
  if (!isAuthConfigured()) {
    return NextResponse.json(
      {
        message: "Account features are not configured yet.",
      },
      { status: 503 },
    );
  }

  const session = await auth();
  const userId = session?.user?.id;
  if (!userId) {
    return NextResponse.json(
      {
        message: "Sign in to save teams.",
      },
      { status: 401 },
    );
  }

  try {
    const rawPayload = (await request.json()) as Record<string, unknown>;
    const parsedPayload = savedTeamSchema.safeParse(rawPayload);
    if (!parsedPayload.success) {
      return NextResponse.json(
        {
          message: parsedPayload.error.issues[0]?.message ?? "The saved team payload is invalid.",
        },
        { status: 400 },
      );
    }

    const savedTeam = await createSavedTeamForUser({
      userId,
      name: parsedPayload.data.name,
      teamText: parsedPayload.data.teamText,
      regulationId: parsedPayload.data.regulationId,
    });

    return NextResponse.json({ team: savedTeam }, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      {
        message: error instanceof Error ? error.message : "The saved team request failed.",
      },
      { status: 400 },
    );
  }
}
