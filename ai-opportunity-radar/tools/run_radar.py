#!/usr/bin/env python3
"""
AI Opportunity Radar — Orchestrator

Runs the full pipeline: profile scraping → opportunity search → AI matching → report.

Usage:
    python tools/run_radar.py \
        --linkedin "https://www.linkedin.com/in/username/" \
        --role "Senior Product Manager" \
        --location "San Francisco, Remote"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
_RADAR_ROOT = _TOOLS_DIR.parent
_PROJECT_ROOT = _RADAR_ROOT.parent

sys.path.insert(0, str(_RADAR_ROOT))

from tools.scrape_linkedin_profile import scrape_linkedin_profile
from tools.search_opportunities import search_opportunities
from tools.analyze_and_match import analyze_and_match
from tools.generate_report import generate_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_radar")

TMP_DIR = _PROJECT_ROOT / ".tmp"


def _save_json(data: dict | list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved: %s", path)


def run_radar(linkedin_url: str, role: str, location: str) -> str:
    """
    Execute the full AI Opportunity Radar pipeline.

    Returns:
        Path to the generated report file.
    """
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Step 1: Profile Analysis ──────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 1/4: Scraping LinkedIn profile...")
    logger.info("=" * 60)

    profile = scrape_linkedin_profile(linkedin_url)
    profile_path = TMP_DIR / f"profile_{timestamp}.json"
    _save_json(profile, profile_path)

    if not profile.get("name") and not profile.get("headline"):
        logger.warning(
            "Profile scrape returned minimal data. "
            "LinkedIn may have blocked access. Continuing with available data."
        )

    skills = profile.get("skills", [])
    logger.info(
        "Profile: %s | %s | Skills: %d",
        profile.get("name", "Unknown"),
        profile.get("headline", "N/A"),
        len(skills),
    )

    # ── Step 2: Opportunity Search ────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 2/4: Searching for opportunities...")
    logger.info("  Role: %s", role)
    logger.info("  Location: %s", location)
    logger.info("=" * 60)

    experience_level = "mid"
    headline = (profile.get("headline") or "").lower()
    for level in ("principal", "lead", "senior", "junior", "intern"):
        if level in headline:
            experience_level = level
            break

    opportunities = search_opportunities(
        role=role,
        location=location,
        skills=skills[:10],
        experience_level=experience_level,
    )

    raw_path = TMP_DIR / f"opportunities_raw_{timestamp}.json"
    _save_json(opportunities, raw_path)
    logger.info("Found %d unique opportunities", len(opportunities))

    if not opportunities:
        logger.warning("No opportunities found. Generating empty report.")
        report_path = generate_report(profile, [], role, location)
        elapsed = time.time() - start_time
        logger.info("Pipeline completed in %.1fs (no opportunities)", elapsed)
        return report_path

    # ── Step 3: AI Matching & Enrichment ──────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 3/4: Analyzing %d opportunities with AI...", len(opportunities))
    logger.info("=" * 60)

    scored = analyze_and_match(profile, opportunities)
    scored_path = TMP_DIR / f"opportunities_scored_{timestamp}.json"
    _save_json(scored, scored_path)

    top_score = scored[0].get("match_score", 0) if scored else 0
    logger.info("Top match score: %d/100", top_score)

    # ── Step 4: Report Generation ─────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 4/4: Generating report...")
    logger.info("=" * 60)

    report_path = generate_report(profile, scored, role, location)

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("  Time: %.1fs", elapsed)
    logger.info("  Opportunities: %d", len(scored))
    logger.info("  Report: %s", report_path)
    logger.info("=" * 60)

    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Opportunity Radar — Find jobs matching your LinkedIn profile"
    )
    parser.add_argument(
        "--linkedin",
        required=True,
        help="LinkedIn profile URL (e.g. https://www.linkedin.com/in/username/)",
    )
    parser.add_argument(
        "--role",
        required=True,
        help="Target job title/role (e.g. 'Senior Product Manager')",
    )
    parser.add_argument(
        "--location",
        required=True,
        help="Preferred location(s) (e.g. 'San Francisco, Remote')",
    )
    args = parser.parse_args()

    try:
        report_path = run_radar(args.linkedin, args.role, args.location)
        print(f"\nReport saved to: {report_path}")
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
