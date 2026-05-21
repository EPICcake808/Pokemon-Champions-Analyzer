import { NextResponse } from "next/server";

import { getBuilderMoveDetails } from "@/lib/python-analyzer";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const move = searchParams.get("move")?.trim();

  if (!move) {
    return NextResponse.json(
      {
        message: "A move name is required.",
      },
      { status: 400 },
    );
  }

  try {
    const payload = await getBuilderMoveDetails(move);
    return NextResponse.json(payload);
  } catch (error) {
    return NextResponse.json(
      {
        message: error instanceof Error ? error.message : "The builder move request failed.",
      },
      { status: 400 },
    );
  }
}
