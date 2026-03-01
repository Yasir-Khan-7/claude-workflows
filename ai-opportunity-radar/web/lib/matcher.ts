import type { Profile, Opportunity, ScoredOpportunity } from "@/types";
import { chatCompletion } from "./groq";

const BATCH_SIZE = 5;

function buildProfileSummary(profile: Profile): string {
  const parts: string[] = [];
  if (profile.name) parts.push(`Name: ${profile.name}`);
  if (profile.headline) parts.push(`Headline: ${profile.headline}`);
  if (profile.skills.length) parts.push(`Skills: ${profile.skills.join(", ")}`);
  if (profile.experience.length)
    parts.push(`Experience: ${profile.experience.slice(0, 5).join("; ")}`);
  if (profile.education.length)
    parts.push(`Education: ${profile.education.slice(0, 3).join("; ")}`);
  return parts.join("\n") || "No profile data.";
}

function buildOppsJson(batch: Opportunity[]): string {
  return JSON.stringify(
    batch.map((o, i) => ({
      index: i,
      title: o.jobTitle,
      company: o.company,
      location: o.location,
      description: o.description,
      url: o.url,
    })),
    null,
    2
  );
}

function parseLlmResponse(
  content: string
): Record<number, { matchScore: number; matchExplanation: string; applicationTips: string; contactEmail: string; hiringManager: string }> {
  const jsonMatch = content.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
  const jsonStr = jsonMatch ? jsonMatch[1] : content;

  let parsed: unknown[];
  try {
    parsed = JSON.parse(jsonStr.trim());
  } catch {
    const arrayMatch = content.match(/\[\s*\{[\s\S]*\}\s*\]/);
    if (arrayMatch) {
      try {
        parsed = JSON.parse(arrayMatch[0]);
      } catch {
        parsed = [];
      }
    } else {
      parsed = [];
    }
  }

  if (!Array.isArray(parsed)) parsed = [parsed];

  const results: Record<number, { matchScore: number; matchExplanation: string; applicationTips: string; contactEmail: string; hiringManager: string }> = {};
  for (const item of parsed) {
    const obj = item as Record<string, unknown>;
    const idx = (obj.index ?? obj.opportunity_index ?? Object.keys(results).length) as number;
    results[idx] = {
      matchScore: Math.max(0, Math.min(100, Number(obj.match_score ?? obj.matchScore ?? 0))),
      matchExplanation: String(obj.match_explanation ?? obj.matchExplanation ?? ""),
      applicationTips: String(obj.application_tips ?? obj.applicationTips ?? ""),
      contactEmail: String(obj.contact_email ?? obj.contactEmail ?? ""),
      hiringManager: String(obj.hiring_manager ?? obj.hiringManager ?? ""),
    };
  }
  return results;
}

export async function analyzeAndMatch(
  profile: Profile,
  opportunities: Opportunity[]
): Promise<ScoredOpportunity[]> {
  const profileSummary = buildProfileSummary(profile);
  const enriched: ScoredOpportunity[] = [];

  for (let start = 0; start < opportunities.length; start += BATCH_SIZE) {
    const batch = opportunities.slice(start, start + BATCH_SIZE);

    const systemPrompt = `You are an expert career advisor. Analyze job opportunities against a candidate's profile and return ONLY a JSON array.

For each opportunity provide:
- index: 0-based index in the batch
- match_score: integer 0-100 (skills alignment, experience, location fit)
- match_explanation: 1-2 sentences why it's a good/bad match
- application_tips: 1-2 specific suggestions to tailor the application
- contact_email: any email found in posting, or ""
- hiring_manager: any name mentioned, or ""

Return ONLY a JSON array, no other text.`;

    const userPrompt = `Candidate profile:\n${profileSummary}\n\nOpportunities:\n${buildOppsJson(batch)}`;

    try {
      const content = await chatCompletion(systemPrompt, userPrompt);
      const results = parseLlmResponse(content);

      for (let i = 0; i < batch.length; i++) {
        const analysis = results[i] || {
          matchScore: 0,
          matchExplanation: "",
          applicationTips: "",
          contactEmail: "",
          hiringManager: "",
        };
        enriched.push({ ...batch[i], ...analysis });
      }
    } catch {
      for (const opp of batch) {
        enriched.push({
          ...opp,
          matchScore: 0,
          matchExplanation: "Analysis failed",
          applicationTips: "",
          contactEmail: "",
          hiringManager: "",
        });
      }
    }

    if (start + BATCH_SIZE < opportunities.length) {
      await new Promise((r) => setTimeout(r, 1000));
    }
  }

  enriched.sort((a, b) => b.matchScore - a.matchScore);
  return enriched;
}
