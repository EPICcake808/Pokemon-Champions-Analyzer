import { NextResponse } from "next/server";

import { runPreview } from "@/lib/python-analyzer";
import type { PreviewRequest } from "@/lib/types";

export const runtime = "nodejs";

export async function POST(request: Request) {
  let body: PreviewRequest;
  try {
    body = (await request.json()) as PreviewRequest;
  } catch {
    return NextResponse.json({ message: "Invalid request body." }, { status: 400 });
  }

  if (!body?.myTeamText?.trim()) {
    return NextResponse.json({ message: "Build your own team before scouting." }, { status: 400 });
  }
  if (!body?.opponentTeamText?.trim()) {
    return NextResponse.json({ message: "Paste the opponent's team to scout the matchup." }, { status: 400 });
  }

  try {
    const payload = await runPreview(body);
    return NextResponse.json(payload);
  } catch (error) {
    return NextResponse.json(
      {
        message: error instanceof Error ? error.message : "The preview request failed.",
      },
      { status: 400 },
    );
  }
}
