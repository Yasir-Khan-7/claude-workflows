import type { Profile } from "@/types";
import { chatCompletion } from "./groq";

export async function extractProfileFromText(
  rawText: string,
  source: "portfolio" | "pdf"
): Promise<Profile> {
  const systemPrompt = `You are an expert resume/profile parser. Extract structured profile information from the provided text and return ONLY valid JSON with no other text.

Return this exact JSON structure:
{
  "name": "Full Name",
  "headline": "Professional headline or title",
  "currentRole": "Current job title",
  "company": "Current company name",
  "location": "Location",
  "skills": ["skill1", "skill2", ...],
  "experience": ["Role at Company - brief description", ...],
  "education": ["Degree at University", ...],
  "certifications": ["Certification name", ...]
}

Extract as much as possible. For skills, include both technical and soft skills. For arrays, if nothing found, use empty array [].`;

  const userPrompt = `Extract the structured profile from this ${source === "pdf" ? "resume/CV" : "portfolio website"} content:\n\n${rawText.slice(0, 8000)}`;

  const response = await chatCompletion(systemPrompt, userPrompt, 0.1);

  try {
    const jsonMatch = response.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    const jsonStr = jsonMatch ? jsonMatch[1] : response;
    const parsed = JSON.parse(jsonStr.trim());

    return {
      name: parsed.name || "",
      headline: parsed.headline || "",
      currentRole: parsed.currentRole || parsed.current_role || "",
      company: parsed.company || "",
      location: parsed.location || "",
      skills: Array.isArray(parsed.skills) ? parsed.skills : [],
      experience: Array.isArray(parsed.experience) ? parsed.experience : [],
      education: Array.isArray(parsed.education) ? parsed.education : [],
      certifications: Array.isArray(parsed.certifications) ? parsed.certifications : [],
      source,
    };
  } catch {
    return {
      name: "",
      headline: "",
      currentRole: "",
      company: "",
      location: "",
      skills: [],
      experience: [],
      education: [],
      certifications: [],
      source,
    };
  }
}
