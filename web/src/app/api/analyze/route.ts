import { NextResponse } from "next/server";

import { DEFAULT_REGULATION_ID, runPokemonAnalyzer } from "@/lib/python-analyzer";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as {
      teamText?: string;
      regulationId?: string;
    };

    const result = await runPokemonAnalyzer(
      payload.teamText ?? "",
      payload.regulationId ?? DEFAULT_REGULATION_ID,
    );

    return NextResponse.json(result, {
      status: result.ok ? 200 : 400,
    });
  } catch {
    return NextResponse.json(
      {
        ok: false,
        message: "The analysis request could not be parsed.",
      },
      { status: 400 },
    );
  }
}
