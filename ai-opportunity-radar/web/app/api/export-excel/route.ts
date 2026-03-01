import { NextRequest, NextResponse } from "next/server";
import { generateExcel } from "@/lib/excel-generator";
import type { Profile, ScoredOpportunity } from "@/types";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { profile, opportunities, role, location } = body as {
      profile: Profile;
      opportunities: ScoredOpportunity[];
      role: string;
      location: string;
    };

    const buffer = await generateExcel(profile, opportunities, role, location);

    return new NextResponse(buffer, {
      headers: {
        "Content-Type":
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": `attachment; filename="opportunity_report.xlsx"`,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Excel generation failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
