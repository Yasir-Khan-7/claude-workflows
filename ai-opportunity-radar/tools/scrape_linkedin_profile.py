#!/usr/bin/env python3
"""
Scrape a LinkedIn profile using the Firecrawl API and extract structured data.

Uses the Firecrawl REST API directly. If direct scraping fails (e.g., LinkedIn blocks),
falls back to Firecrawl search API to find cached/indexed profile data.

Usage:
    python tools/scrape_linkedin_profile.py --linkedin-url "https://www.linkedin.com/in/username/"

Requires:
    FIRECRAWL_API_KEY in .env (loaded from project root, two levels up from tools/)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from project root (Claude Workflows/, two levels up from tools/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"
FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v1/search"
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0
BACKOFF_MULTIPLIER = 2.0


def _get_api_key() -> str:
    """Get Firecrawl API key from environment."""
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "FIRECRAWL_API_KEY not found. Set it in .env at the project root."
        )
    return api_key.strip()


def _get_headers(api_key: str) -> dict[str, str]:
    """Build request headers for Firecrawl API."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _scrape_url(api_key: str, url: str) -> str | None:
    """
    Call Firecrawl scrape API and return markdown content.
    Returns None on failure.
    """
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                FIRECRAWL_SCRAPE_URL,
                headers=_get_headers(api_key),
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("success") and data.get("data"):
                markdown = data["data"].get("markdown")
                if markdown:
                    return markdown
                logger.warning("Scrape succeeded but no markdown in response")
            else:
                logger.warning(
                    "Scrape API returned success=false or missing data: %s",
                    data.get("error", "unknown"),
                )
        except requests.RequestException as e:
            logger.warning("Scrape attempt %d failed: %s", attempt + 1, e)
        except (KeyError, TypeError) as e:
            logger.warning("Unexpected response structure: %s", e)

        if attempt < MAX_RETRIES - 1:
            backoff = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER**attempt)
            logger.info("Retrying in %.1fs...", backoff)
            time.sleep(backoff)

    return None


def _search_fallback(api_key: str, query: str) -> str | None:
    """
    Use Firecrawl search API to find profile-related content.
    Returns combined markdown from scraped results, or None.
    """
    payload = {
        "query": query,
        "limit": 3,
        "scrapeOptions": {
            "formats": ["markdown"],
            "onlyMainContent": True,
        },
    }
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                FIRECRAWL_SEARCH_URL,
                headers=_get_headers(api_key),
                json=payload,
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                logger.warning("Search API returned success=false")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(INITIAL_BACKOFF * (BACKOFF_MULTIPLIER**attempt))
                continue

            results = data.get("data", data)
            if isinstance(results, dict):
                results = results.get("data", results.get("results", []))
            if not isinstance(results, list):
                results = [results] if results else []

            markdown_parts = []
            for r in results:
                if isinstance(r, dict):
                    md = r.get("markdown") or r.get("content") or r.get("text")
                    if md:
                        markdown_parts.append(md)
                elif isinstance(r, str):
                    markdown_parts.append(r)

            if markdown_parts:
                return "\n\n---\n\n".join(markdown_parts)

        except requests.RequestException as e:
            logger.warning("Search attempt %d failed: %s", attempt + 1, e)
        except (KeyError, TypeError) as e:
            logger.warning("Unexpected search response: %s", e)

        if attempt < MAX_RETRIES - 1:
            backoff = INITIAL_BACKOFF * (BACKOFF_MULTIPLIER**attempt)
            time.sleep(backoff)

    return None


def _extract_name_from_url(linkedin_url: str) -> str:
    """Extract display-name-style string from LinkedIn URL for search fallback."""
    match = re.search(r"linkedin\.com/in/([^/?]+)", linkedin_url, re.I)
    if match:
        slug = match.group(1).strip("/")
        name = re.sub(r"-\d+$", "", slug).replace("-", " ")
        return name.strip() or "unknown"
    return "unknown"


def _extract_section(markdown: str, section_names: list[str]) -> str:
    """Extract content between a section header and the next ## or ###."""
    for name in section_names:
        pattern = rf"(?:^|\n)#+\s*{re.escape(name)}\s*[#\n]*([\s\S]*?)(?=\n#+\s|\n\n\n|\Z)"
        m = re.search(pattern, markdown, re.I)
        if m:
            return m.group(1).strip()
        pattern2 = rf"(?:^|\n){re.escape(name)}\s*[#\n]*([\s\S]*?)(?=\n[A-Z][a-z]+.*\n|\n\n\n|\Z)"
        m2 = re.search(pattern2, markdown, re.I)
        if m2:
            return m2.group(1).strip()
    return ""


def _parse_list_items(text: str) -> list[str]:
    """Parse bullet points or numbered items into a list of strings."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[\*\-\•\d.]+\s*", "", line)
        line = line.strip()
        if len(line) > 2:
            items.append(line)
    return items[:20]


def _parse_linkedin_markdown(markdown: str) -> dict:
    """
    Parse markdown content from a LinkedIn profile page into structured fields.
    Uses heuristics since LinkedIn's rendered structure varies.
    """
    result: dict = {
        "name": "",
        "headline": "",
        "current_role": "",
        "company": "",
        "location": "",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
    }

    if not markdown or not isinstance(markdown, str):
        return result

    lines = [ln.strip() for ln in markdown.split("\n") if ln.strip()]
    if not lines:
        return result

    if not result["name"] and lines:
        result["name"] = lines[0].strip("#* ")

    for line in lines[1:5]:
        if not result["headline"] and len(line) > 3 and "|" not in line[:20]:
            if not re.match(r"^[-=*#]+$", line) and "linkedin.com" not in line.lower():
                result["headline"] = line.strip("#* ")
                break

    location_patterns = [
        r"(?:^|\n)\s*([A-Za-z\s,]+(?:,\s*[A-Za-z\s]+)*)\s*(?:\d{5})?",
        r"📍\s*(.+)",
        r"Location[:\s]+(.+)",
        r"Based in[:\s]+(.+)",
    ]
    for pat in location_patterns:
        m = re.search(pat, markdown, re.I | re.M)
        if m and m.group(1).strip() and len(m.group(1)) < 100:
            result["location"] = m.group(1).strip()
            break

    exp_section = _extract_section(
        markdown, ["Experience", "Work Experience", "Employment"]
    )
    if exp_section:
        result["experience"] = _parse_list_items(exp_section)
        if result["experience"]:
            first = result["experience"][0]
            if " at " in first:
                parts = first.split(" at ", 1)
                result["current_role"] = parts[0].strip()
                result["company"] = parts[1].strip()
            else:
                result["current_role"] = first

    edu_section = _extract_section(markdown, ["Education", "Academic"])
    if edu_section:
        result["education"] = _parse_list_items(edu_section)

    skills_section = _extract_section(
        markdown, ["Skills", "Top skills", "Expertise"]
    )
    if skills_section:
        skills = re.findall(r"[\w\s&+.-]+", skills_section)
        result["skills"] = [
            s.strip()
            for s in skills
            if len(s.strip()) > 1 and len(s.strip()) < 50
        ][:50]

    cert_section = _extract_section(
        markdown,
        ["Certifications", "Licenses", "Licenses & certifications"],
    )
    if cert_section:
        result["certifications"] = _parse_list_items(cert_section)

    if not result["current_role"] and result["headline"]:
        if " at " in result["headline"]:
            parts = result["headline"].split(" at ", 1)
            result["current_role"] = parts[0].strip()
            result["company"] = parts[1].strip()
        else:
            result["current_role"] = result["headline"]

    return result


def scrape_linkedin_profile(linkedin_url: str) -> dict:
    """
    Scrape a LinkedIn profile and return structured data.

    Args:
        linkedin_url: Full LinkedIn profile URL (e.g. https://www.linkedin.com/in/username/)

    Returns:
        Dict with keys: name, headline, current_role, company, location,
        skills, experience, education, certifications, source, raw_preview.
        All values are empty/default if extraction fails.
    """
    api_key = _get_api_key()
    markdown = _scrape_url(api_key, linkedin_url)

    if not markdown:
        logger.info("Direct scrape failed, trying search fallback...")
        name_hint = _extract_name_from_url(linkedin_url)
        search_query = f"{name_hint} LinkedIn profile"
        markdown = _search_fallback(api_key, search_query)

    if not markdown:
        logger.error("No content could be retrieved from LinkedIn or search")
        return {
            "name": "",
            "headline": "",
            "current_role": "",
            "company": "",
            "location": "",
            "skills": [],
            "experience": [],
            "education": [],
            "certifications": [],
            "source": "none",
            "raw_preview": "",
        }

    result = _parse_linkedin_markdown(markdown)
    result["source"] = (
        "scrape" if "linkedin.com" in (markdown[:500] or "") else "search"
    )
    result["raw_preview"] = (
        markdown[:500] + "..." if len(markdown) > 500 else markdown
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape a LinkedIn profile using Firecrawl API"
    )
    parser.add_argument(
        "--linkedin-url",
        required=True,
        help="Full LinkedIn profile URL (e.g. https://www.linkedin.com/in/username/)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON only (no pretty print)",
    )
    args = parser.parse_args()

    try:
        data = scrape_linkedin_profile(args.linkedin_url)
        if args.json:
            print(json.dumps(data, ensure_ascii=False))
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    except ValueError as e:
        logger.error("%s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
