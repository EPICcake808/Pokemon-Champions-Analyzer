import { NextResponse } from "next/server";

import { runDamageCalc } from "@/lib/python-analyzer";
import type { DamageCalcRequest } from "@/lib/types";

export const runtime = "nodejs";

export async function POST(request: Request) {
  let body: DamageCalcRequest;
  try {
    body = (await request.json()) as DamageCalcRequest;
  } catch {
    return NextResponse.json({ message: "Invalid request body." }, { status: 400 });
  }

  if (!body?.attacker?.species || !body?.defender?.species) {
    return NextResponse.json(
      { message: "An attacker and defender species are required." },
      { status: 400 },
    );
  }

  if (!body.attacker.move) {
    return NextResponse.json(
      { message: "Select an attacking move to calculate damage." },
      { status: 400 },
    );
  }

  try {
    const payload = await runDamageCalc(body);
    return NextResponse.json(payload);
  } catch (error) {
    return NextResponse.json(
      {
        message: error instanceof Error ? error.message : "The damage calculation request failed.",
      },
      { status: 400 },
    );
  }
}
