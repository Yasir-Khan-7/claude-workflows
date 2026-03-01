#!/usr/bin/env python3
"""
Analyze and match a user's profile against found opportunities using Groq Cloud LLM API.
Uses REST API directly (not the groq SDK).
"""

import json
import logging
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from project root (two levels up from tools/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
BATCH_SIZE = 5
MAX_RETRIES = 3
RETRY_DELAY_SEC = 2


def _build_profile_summary(profile: dict) -> str:
    """Build a concise profile summary for the prompt."""
    parts = []
    if profile.get("name"):
        parts.append(f"Name: {profile['name']}")
    if profile.get("headline"):
        parts.append(f"Headline: {profile['headline']}")
    if profile.get("summary"):
        parts.append(f"Summary: {profile['summary']}")
    if profile.get("skills"):
        skills = profile["skills"] if isinstance(profile["skills"], list) else [profile["skills"]]
        parts.append(f"Skills: {', '.join(skills)}")
    if profile.get("experience"):
        exp = profile["experience"]
        if isinstance(exp, list):
            exp_str = "; ".join(exp[:5]) if exp else "N/A"
        else:
            exp_str = str(exp)
        parts.append(f"Experience: {exp_str}")
    if profile.get("education"):
        edu = profile["education"]
        if isinstance(edu, list):
            edu_str = "; ".join(edu[:3]) if edu else "N/A"
        else:
            edu_str = str(edu)
        parts.append(f"Education: {edu_str}")
    return "\n".join(parts) if parts else "No profile provided."


def _build_opportunities_json(opportunities: list[dict]) -> str:
    """Build JSON string of opportunities for the prompt."""
    simplified = []
    for i, opp in enumerate(opportunities):
        item = {
            "index": i,
            "title": opp.get("title") or opp.get("job_title") or "Unknown",
            "company": opp.get("company") or opp.get("employer") or "Unknown",
            "location": opp.get("location") or opp.get("job_location") or "Unknown",
            "description": opp.get("description") or opp.get("snippet") or opp.get("body") or "",
            "url": opp.get("url") or opp.get("link") or "",
        }
        simplified.append(item)
    return json.dumps(simplified, indent=2)


def _call_groq_api(api_key: str, system_prompt: str, user_prompt: str) -> str:
    """Call Groq API with retries and error handling."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                raise ValueError("Empty response from Groq API")
            return content
        except requests.exceptions.RequestException as e:
            logger.warning("Groq API request failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SEC * (attempt + 1))
            else:
                raise
        except (KeyError, IndexError) as e:
            logger.warning("Unexpected Groq API response structure (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SEC * (attempt + 1))
            else:
                raise


def _parse_llm_response(content: str, batch: list[dict]) -> list[dict]:
    """Parse LLM JSON response with fallback handling."""
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if json_match:
        content = json_match.group(1).strip()

    # Try raw JSON parse
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Try to find a JSON array in the text
        array_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", content)
        if array_match:
            try:
                parsed = json.loads(array_match.group(0))
            except json.JSONDecodeError:
                parsed = []
        else:
            parsed = []

    if not isinstance(parsed, list):
        parsed = [parsed] if isinstance(parsed, dict) else []

    # Map parsed results back to opportunities by index
    results_by_index: dict[int, dict] = {}
    for item in parsed:
        idx = item.get("index", item.get("opportunity_index", len(results_by_index)))
        results_by_index[idx] = {
            "match_score": item.get("match_score", item.get("score", 0)),
            "match_explanation": item.get("match_explanation", item.get("explanation", "")),
            "application_tips": item.get("application_tips", item.get("tips", "")),
            "contact_email": item.get("contact_email", item.get("email", "")),
            "hiring_manager": item.get("hiring_manager", ""),
        }

    return results_by_index


def _enrich_opportunity(opp: dict, analysis: dict) -> dict:
    """Merge analysis results into an opportunity dict."""
    enriched = dict(opp)
    enriched["match_score"] = analysis.get("match_score", 0)
    enriched["match_explanation"] = analysis.get("match_explanation", "")
    enriched["application_tips"] = analysis.get("application_tips", "")
    enriched["contact_email"] = analysis.get("contact_email", "")
    enriched["hiring_manager"] = analysis.get("hiring_manager", "")
    return enriched


def analyze_and_match(profile: dict, opportunities: list[dict]) -> list[dict]:
    """
    Analyze and match a user's profile against found opportunities using Groq LLM.

    Args:
        profile: User profile dict with keys like name, headline, skills, experience, education.
        opportunities: List of opportunity dicts with title, company, location, description, url.

    Returns:
        Enriched opportunity list sorted by match score (highest first).
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in environment. Add it to .env")

    profile_summary = _build_profile_summary(profile)
    enriched: list[dict] = []

    for batch_start in range(0, len(opportunities), BATCH_SIZE):
        batch = opportunities[batch_start : batch_start + BATCH_SIZE]
        batch_indices = list(range(batch_start, min(batch_start + BATCH_SIZE, len(opportunities))))

        system_prompt = """You are an expert career advisor and recruiter. Analyze job opportunities against a candidate's profile and return structured JSON.

For each opportunity, provide:
- index: the 0-based index of the opportunity in the batch
- match_score: integer 0-100 based on skills alignment, experience level, and location fit
- match_explanation: 1-2 sentences on why it's a good or bad match
- application_tips: 1-2 specific suggestions to tailor the application for this role
- contact_email: any email address found in the posting (e.g. recruiter@company.com), or empty string if none
- hiring_manager: any hiring manager or recruiter name mentioned, or empty string if none

Return ONLY a JSON array of objects, no other text. Example:
[{"index": 0, "match_score": 85, "match_explanation": "...", "application_tips": "...", "contact_email": "", "hiring_manager": ""}]"""

        user_prompt = f"""Candidate profile:
{profile_summary}

Opportunities to analyze (JSON):
{_build_opportunities_json(batch)}

Return a JSON array with one object per opportunity, using the exact structure specified."""

        logger.info("Analyzing batch %d-%d of %d opportunities", batch_start + 1, batch_start + len(batch), len(opportunities))

        content = _call_groq_api(api_key, system_prompt, user_prompt)
        results = _parse_llm_response(content, batch)

        for i, opp in enumerate(batch):
            idx = batch_start + i
            analysis = results.get(i, results.get(idx, {}))
            if isinstance(analysis.get("match_score"), (int, float)):
                score = int(analysis["match_score"])
            else:
                score = 0
            analysis["match_score"] = max(0, min(100, score))
            enriched.append(_enrich_opportunity(opp, analysis))

        if batch_start + BATCH_SIZE < len(opportunities):
            time.sleep(1)  # Rate limit cushion between batches

    enriched.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    logger.info("Analyzed %d opportunities, sorted by match score", len(enriched))
    return enriched


def main() -> None:
    """CLI entry point for testing and workflow integration."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze and match opportunities against profile using Groq LLM")
    parser.add_argument("--profile", required=True, help="Path to profile JSON file")
    parser.add_argument("--opportunities", required=True, help="Path to opportunities JSON file")
    parser.add_argument("--output", required=True, help="Path to write scored opportunities JSON")
    args = parser.parse_args()

    with open(args.profile, encoding="utf-8") as f:
        profile = json.load(f)
    with open(args.opportunities, encoding="utf-8") as f:
        opportunities = json.load(f)

    if not isinstance(opportunities, list):
        opportunities = opportunities.get("opportunities", opportunities.get("results", []))

    result = analyze_and_match(profile, opportunities)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.info("Wrote %d scored opportunities to %s", len(result), args.output)


if __name__ == "__main__":
    main()
