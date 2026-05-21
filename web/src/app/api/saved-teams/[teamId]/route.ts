import { NextResponse } from "next/server";
import { z } from "zod";

import { auth } from "@/auth";
import { isAuthConfigured } from "@/lib/auth/runtime";
import { deleteSavedTeamForUser, updateSavedTeamForUser } from "@/lib/saved-teams";

export const runtime = "nodejs";

const savedTeamSchema = z.object({
  name: z.string().trim().min(1, "Saved teams need a name.").max(80, "Saved team names must be 80 characters or fewer."),
  teamText: z.string().trim().min(1, "Build a roster before saving.").max(12000, "Team exports are too large to save."),
  regulationId: z.string().trim().min(1, "A regulation is required.").max(120),
});

type SavedTeamRouteContext = {
  params: Promise<{
    teamId: string;
  }>;
};

export async function PATCH(request: Request, { params }: SavedTeamRouteContext) {
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
        message: "Sign in to update saved teams.",
      },
      { status: 401 },
    );
  }

  try {
    const { teamId } = await params;
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

    const savedTeam = await updateSavedTeamForUser({
      teamId,
      userId,
      name: parsedPayload.data.name,
      teamText: parsedPayload.data.teamText,
      regulationId: parsedPayload.data.regulationId,
    });

    if (!savedTeam) {
      return NextResponse.json(
        {
          message: "That saved team could not be found.",
        },
        { status: 404 },
      );
    }

    return NextResponse.json({ team: savedTeam });
  } catch (error) {
    return NextResponse.json(
      {
        message: error instanceof Error ? error.message : "The saved team update failed.",
      },
      { status: 400 },
    );
  }
}

export async function DELETE(_: Request, { params }: SavedTeamRouteContext) {
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
        message: "Sign in to delete saved teams.",
      },
      { status: 401 },
    );
  }

  const { teamId } = await params;
  const deleted = await deleteSavedTeamForUser(teamId, userId);
  if (!deleted) {
    return NextResponse.json(
      {
        message: "That saved team could not be found.",
      },
      { status: 404 },
    );
  }

  return NextResponse.json({ ok: true });
}
