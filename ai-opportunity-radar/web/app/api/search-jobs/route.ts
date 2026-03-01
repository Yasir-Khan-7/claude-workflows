import { NextRequest, NextResponse } from "next/server";
import { searchOpportunities } from "@/lib/job-searcher";

export const maxDuration = 60;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { role, location, skills } = body as {
      role: string;
      location: string;
      skills: string[];
    };

    if (!role || !location) {
      return NextResponse.json(
        { error: "role and location are required" },
        { status: 400 }
      );
    }

    const opportunities = await searchOpportunities(role, location, skills || []);
    return NextResponse.json({ opportunities });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Job search failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
