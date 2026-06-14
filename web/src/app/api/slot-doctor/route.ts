import { NextResponse } from "next/server";

import { runSlotDoctor } from "@/lib/python-analyzer";
import type { SlotDoctorRequest } from "@/lib/types";

export const runtime = "nodejs";

export async function POST(request: Request) {
  let body: SlotDoctorRequest;
  try {
    body = (await request.json()) as SlotDoctorRequest;
  } catch {
    return NextResponse.json({ message: "Invalid request body." }, { status: 400 });
  }

  if (!body?.teamText?.trim()) {
    return NextResponse.json({ message: "Build a team before running the slot doctor." }, { status: 400 });
  }

  try {
    const payload = await runSlotDoctor(body);
    return NextResponse.json(payload);
  } catch (error) {
    return NextResponse.json(
      {
        message: error instanceof Error ? error.message : "The slot doctor request failed.",
      },
      { status: 400 },
    );
  }
}
