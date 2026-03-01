#!/usr/bin/env python3
"""
Search for job opportunities across the web using the Firecrawl API.

Uses Firecrawl search to find job postings, then optionally scrapes top results
to extract contact emails. Part of the WAT framework (ai-opportunity-radar).

Usage:
    python tools/search_opportunities.py --role "Product Manager" --location "San Francisco"
    python tools/search_opportunities.py --role "Engineer" --location "Remote" --skills "Python,React"

Outputs:
    Returns list of opportunity dicts (job_title, company, location, url, description, posted_date, emails)
    When run as CLI: writes to .tmp/opportunities_raw.json

Requires:
    FIRECRAWL_API_KEY in .env (loaded from project root, two levels up from tools/)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
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

FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v1/search"
FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"

# Rate limiting and retries
REQUEST_DELAY_SEC = 2.0  # Sleep between requests to avoid rate limits
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # Exponential backoff base (seconds)
TOP_N_FOR_EMAIL_SCRAPE = 10  # Only scrape top N opportunities for email extraction

# Regex for email extraction (RFC 5322 simplified - avoids common false positives)
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)
# Exclude common non-contact emails (images, placeholders, etc.)
EMAIL_EXCLUDE_PATTERNS = (
    r"example\.com",
    r"domain\.com",
    r"email\.com",
    r"test@",
    r"@.*\.(png|jpg|gif|svg|webp)",
    r"noreply@",
    r"no-reply@",
    r"donotreply@",
    r"@wix\.com",
    r"@sentry\.io",
    r"@gravatar\.com",
    r"@github\.com",
    r"@linkedin\.com",
)


def _get_api_key() -> str:
    """Load Firecrawl API key from environment."""
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key or not key.strip():
        raise ValueError(
            "FIRECRAWL_API_KEY not found in .env. "
            "Add it to the project root .env file."
        )
    return key.strip()


def _get_headers(api_key: str) -> dict[str, str]:
    """Build request headers for Firecrawl API."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _build_search_queries(
    role: str,
    location: str,
    skills: list[str],
    experience_level: str,
) -> list[str]:
    """Build smart search query variations."""
    role_clean = role.strip()
    location_clean = location.strip()
    skills_str = ", ".join(s[:50] for s in skills[:5]) if skills else ""

    queries = [
        f"{role_clean} jobs in {location_clean}",
        f"{role_clean} {location_clean} hiring",
        f"{role_clean} remote {location_clean} opportunities",
    ]

    if skills_str:
        queries.append(f"{role_clean} {skills_str} {location_clean}")

    # Job board specific
    queries.extend([
        f"site:linkedin.com/jobs {role_clean} {location_clean}",
        f"site:indeed.com {role_clean} {location_clean}",
    ])

    # Experience level modifier for some queries
    if experience_level and experience_level.lower() in ("senior", "lead", "principal"):
        queries.append(f"{experience_level} {role_clean} {location_clean}")

    return queries


def _firecrawl_search(
    api_key: str,
    query: str,
    limit: int = 5,
) -> list[dict]:
    """Call Firecrawl search API with retries and rate limiting."""
    headers = _get_headers(api_key)
    payload = {
        "query": query,
        "limit": limit,
        "scrapeOptions": {
            "formats": ["markdown"],
            "onlyMainContent": True,
        },
    }

    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY_SEC)
            resp = requests.post(
                FIRECRAWL_SEARCH_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()

            if not data.get("success"):
                logger.warning(
                    "Firecrawl search returned success=false for query: %s",
                    query[:80],
                )
                return []

            results = data.get("data") or []
            logger.info("Search '%s' returned %d results", query[:50], len(results))
            return results

        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                logger.warning(
                    "Rate limited (429). Waiting %ds before retry %d/%d",
                    wait,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(wait)
            else:
                logger.error("Firecrawl search HTTP error: %s", e)
                raise
        except requests.exceptions.RequestException as e:
            logger.error("Firecrawl search request failed: %s", e)
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                time.sleep(wait)
            else:
                raise

    return []


def _firecrawl_scrape(api_key: str, url: str) -> str | None:
    """Scrape a single URL via Firecrawl. Returns markdown content or None."""
    headers = _get_headers(api_key)
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }

    try:
        time.sleep(REQUEST_DELAY_SEC)
        resp = requests.post(
            FIRECRAWL_SCRAPE_URL,
            headers=headers,
            json=payload,
            timeout=45,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success"):
            return None

        content = data.get("data", {})
        return content.get("markdown") or ""
    except requests.exceptions.RequestException as e:
        logger.warning("Scrape failed for %s: %s", url[:60], e)
        return None


def _extract_emails(text: str) -> list[str]:
    """Extract valid contact emails from text, excluding common non-contact patterns."""
    if not text:
        return []
    found = set(EMAIL_PATTERN.findall(text))
    result = []
    for email in found:
        email_lower = email.lower()
        if any(re.search(p, email_lower) for p in EMAIL_EXCLUDE_PATTERNS):
            continue
        result.append(email)
    return list(dict.fromkeys(result))  # Preserve order, remove dupes


def _parse_search_result(item: dict) -> dict:
    """Parse a Firecrawl search result into a structured opportunity dict."""
    url = item.get("url") or ""
    title = item.get("title") or item.get("metadata", {}).get("title") or ""
    if isinstance(title, list):
        title = title[0] if title else ""
    description = item.get("description") or ""
    markdown = item.get("markdown") or ""

    # Use first ~300 chars of description or markdown as snippet
    snippet = description[:300] if description else (markdown[:300] if markdown else "")

    # Try to infer company from URL or title (e.g., "Company - Job Title" or domain)
    company = ""
    if " - " in title:
        parts = title.split(" - ", 1)
        company = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else title
    elif url:
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            company = domain.replace("www.", "").split(".")[0] if domain else ""
        except Exception:
            pass

    # Posted date - often in metadata or markdown; we don't have a standard field
    posted_date = ""

    return {
        "job_title": title.strip() or "Unknown",
        "company": company or "Unknown",
        "location": "",
        "url": url,
        "description": snippet.strip(),
        "posted_date": posted_date,
        "emails": [],
    }


def _deduplicate_by_url(opportunities: list[dict]) -> list[dict]:
    """Deduplicate opportunities by URL, keeping first occurrence."""
    seen: set[str] = set()
    result = []
    for opp in opportunities:
        url = (opp.get("url") or "").strip().rstrip("/")
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(opp)
    return result


def search_opportunities(
    role: str,
    location: str,
    skills: list[str],
    experience_level: str = "mid",
) -> list[dict]:
    """
    Search for job opportunities using Firecrawl.

    Args:
        role: Target job title/role (e.g., "Product Manager")
        location: Preferred location (e.g., "San Francisco", "Remote")
        skills: List of key skills to include in search
        experience_level: Experience level hint ("junior", "mid", "senior", "lead")

    Returns:
        List of opportunity dicts with keys: job_title, company, location, url,
        description, posted_date, emails. Deduplicated by URL.
    """
    api_key = _get_api_key()
    queries = _build_search_queries(role, location, skills, experience_level)

    all_results: list[dict] = []
    for query in queries:
        try:
            raw = _firecrawl_search(api_key, query, limit=5)
            for item in raw:
                opp = _parse_search_result(item)
                if opp.get("url"):
                    all_results.append(opp)
        except Exception as e:
            logger.error("Search failed for query '%s': %s", query[:50], e)
            continue

    opportunities = _deduplicate_by_url(all_results)
    logger.info("Found %d unique opportunities after deduplication", len(opportunities))

    # Scrape top N for email extraction
    to_scrape = opportunities[:TOP_N_FOR_EMAIL_SCRAPE]
    for i, opp in enumerate(to_scrape):
        url = opp.get("url")
        if not url:
            continue
        logger.info("Scraping for emails (%d/%d): %s", i + 1, len(to_scrape), url[:60])
        content = _firecrawl_scrape(api_key, url)
        if content:
            emails = _extract_emails(content)
            if emails:
                opp["emails"] = emails
                logger.info("  Found %d email(s): %s", len(emails), ", ".join(emails[:3]))

    return opportunities


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search for job opportunities via Firecrawl"
    )
    parser.add_argument("--role", required=True, help="Target job title/role")
    parser.add_argument("--location", required=True, help="Preferred location")
    parser.add_argument(
        "--skills",
        default="",
        help="Comma-separated skills (e.g., 'Python,React,SQL')",
    )
    parser.add_argument(
        "--experience",
        default="mid",
        choices=["junior", "mid", "senior", "lead", "principal"],
        help="Experience level hint",
    )
    parser.add_argument(
        "--output",
        default=".tmp/opportunities_raw.json",
        help="Output JSON file path",
    )
    args = parser.parse_args()

    skills_list = [s.strip() for s in args.skills.split(",") if s.strip()]

    logger.info(
        "Searching: role=%s, location=%s, skills=%s",
        args.role,
        args.location,
        skills_list or "(none)",
    )

    opportunities = search_opportunities(
        role=args.role,
        location=args.location,
        skills=skills_list,
        experience_level=args.experience,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(opportunities, indent=2), encoding="utf-8")

    logger.info("Wrote %d opportunities to %s", len(opportunities), out_path)


if __name__ == "__main__":
    main()
