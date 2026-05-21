import { NextResponse } from "next/server";

import { DEFAULT_REGULATION_ID, getBuilderSpeciesOptions } from "@/lib/python-analyzer";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const species = searchParams.get("species")?.trim();
  const regulationId = searchParams.get("regulationId") ?? DEFAULT_REGULATION_ID;

  if (!species) {
    return NextResponse.json(
      {
        message: "A species name is required.",
      },
      { status: 400 },
    );
  }

  try {
    const payload = await getBuilderSpeciesOptions(species, regulationId);
    return NextResponse.json(payload);
  } catch (error) {
    return NextResponse.json(
      {
        message: error instanceof Error ? error.message : "The builder species request failed.",
      },
      { status: 400 },
    );
  }
}
