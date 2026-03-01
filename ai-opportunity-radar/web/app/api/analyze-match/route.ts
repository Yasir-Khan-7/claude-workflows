import { NextRequest, NextResponse } from "next/server";
import { analyzeAndMatch } from "@/lib/matcher";
import type { Profile, Opportunity } from "@/types";

export const maxDuration = 60;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { profile, opportunities } = body as {
      profile: Profile;
      opportunities: Opportunity[];
    };

    if (!profile || !opportunities?.length) {
      return NextResponse.json(
        { error: "profile and opportunities are required" },
        { status: 400 }
      );
    }

    const scored = await analyzeAndMatch(profile, opportunities);
    return NextResponse.json({ scored });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Analysis failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
