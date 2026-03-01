import { NextRequest, NextResponse } from "next/server";
import { scrapeUrl } from "@/lib/firecrawl";
import { extractTextFromPdf } from "@/lib/pdf-parser";
import { extractProfileFromText } from "@/lib/profile-extractor";

export const maxDuration = 60;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { portfolioUrl, pdfBase64 } = body as {
      portfolioUrl?: string;
      pdfBase64?: string;
    };

    let rawText = "";
    let source: "portfolio" | "pdf" = "portfolio";

    if (portfolioUrl) {
      const markdown = await scrapeUrl(portfolioUrl);
      if (!markdown) {
        return NextResponse.json(
          { error: "Could not scrape portfolio URL. Check the URL and try again." },
          { status: 400 }
        );
      }
      rawText = markdown;
      source = "portfolio";
    } else if (pdfBase64) {
      const buffer = Buffer.from(pdfBase64, "base64");
      rawText = await extractTextFromPdf(buffer);
      if (!rawText.trim()) {
        return NextResponse.json(
          { error: "Could not extract text from PDF. Make sure the PDF contains readable text." },
          { status: 400 }
        );
      }
      source = "pdf";
    } else {
      return NextResponse.json(
        { error: "Provide either portfolioUrl or pdfBase64" },
        { status: 400 }
      );
    }

    const profile = await extractProfileFromText(rawText, source);
    return NextResponse.json({ profile });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Profile extraction failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
