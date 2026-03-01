# Workflow: Find Job Opportunities

## Objective
Find relevant job opportunities based on a user's LinkedIn profile, target role, and preferred location. The workflow scrapes the profile, searches job boards, scores matches using AI, and produces a structured report.

## When to Use
- When a user wants to discover job opportunities aligned with their background
- When exploring career options in a new role or location
- As a periodic scan to surface new postings matching the user's profile

## Required Inputs

| Input | Source | Example |
|-------|--------|---------|
| LinkedIn profile URL | User provides | `https://www.linkedin.com/in/username/` |
| Target role / job title | User provides | `Senior Product Manager` |
| Preferred location(s) | User provides | `San Francisco, Remote` |
| `FIRECRAWL_API_KEY` | `.env` | `fc-xxxxxxxxxxxx` |
| `GROQ_API_KEY` | `.env` | `gsk_xxxxxxxxxxxx` |

## Tools Used

| Tool | Purpose |
|------|---------|
| `tools/scrape_linkedin_profile.py` | Scrape LinkedIn profile via Firecrawl; extract skills, experience, education |
| `tools/search_opportunities.py` | Search job boards via Firecrawl web search for matching postings |
| `tools/analyze_and_match.py` | Score opportunities against profile using Groq LLM; extract emails/contacts if available |
| `tools/generate_report.py` | Compile findings into a structured markdown report |

## Procedure

### Step 1: Profile Analysis

```bash
python tools/scrape_linkedin_profile.py --url "https://www.linkedin.com/in/username/"
```

- Uses Firecrawl to scrape the LinkedIn profile
- Extracts: key skills, work experience, education, headline, summary
- Outputs structured profile data to `.tmp/profile_{username}.json`

**If this fails:** See [Edge Cases: LinkedIn profile may be private](#edge-cases).

### Step 2: Opportunity Search

```bash
python tools/search_opportunities.py --role "Senior Product Manager" --location "San Francisco, Remote" --profile .tmp/profile_username.json
```

- Uses Firecrawl web search to find job postings across job boards (LinkedIn, Indeed, company career pages, etc.)
- Searches for roles matching the target title and location
- Optionally uses profile skills to refine search queries
- Outputs raw search results to `.tmp/opportunities_raw.json`

**If this fails:** See [Edge Cases: Rate limits](#edge-cases) and [No opportunities found](#edge-cases).

### Step 3: AI Matching & Enrichment

```bash
python tools/analyze_and_match.py --profile .tmp/profile_username.json --opportunities .tmp/opportunities_raw.json --output .tmp/opportunities_scored.json
```

- Uses Groq LLM to score each opportunity against the profile (0–100)
- Generates match reasoning (e.g., "Strong alignment with 5+ years PM experience")
- Attempts to extract email addresses or contact info from job postings where available
- Outputs enrichment results to `.tmp/opportunities_scored.json`

**If this fails:** Check that `GROQ_API_KEY` is set in `.env`. If email extraction fails, the tool marks contacts as "not found" and continues.

### Step 4: Report Generation

```bash
python tools/generate_report.py --input .tmp/opportunities_scored.json --output .tmp/opportunity_report_YYYY-MM-DD.md
```

- Compiles scored opportunities into a markdown report
- Sorts by match score (highest first)
- Includes: role, company, link, match score, reasoning, contact info (if found)
- Outputs a structured report to `.tmp/opportunity_report_YYYY-MM-DD.md`

## Expected Outputs

| Output | Location |
|--------|----------|
| Profile data | `.tmp/profile_{username}.json` |
| Raw opportunities | `.tmp/opportunities_raw.json` |
| Scored opportunities | `.tmp/opportunities_scored.json` |
| **Final report** | `.tmp/opportunity_report_YYYY-MM-DD.md` |

## Report Format

The markdown report includes:

- **Header**: Date, target role, location, profile summary
- **Opportunities table**: Role, company, link, match score, contact info
- **Match reasoning**: Per-opportunity explanation of fit
- **Summary stats**: Total opportunities, average score, top matches

## Edge Cases

| Situation | How to Handle |
|-----------|---------------|
| **LinkedIn profile may be private** | Use Firecrawl with stealth proxy (`proxy: "stealth"`). If profile is still inaccessible, fall back to manual input: ask user to provide skills, experience, and education in a JSON file; use that as `profile_input.json` instead. |
| **Rate limits on Firecrawl** | Tools have built-in retry with exponential backoff. If rate limit persists, reduce search scope (fewer locations, fewer queries) or wait and retry. Document rate limit in workflow if recurring. |
| **No opportunities found** | Broaden search terms: try related roles (e.g., "Product Manager" if "Senior Product Manager" returns nothing), add nearby cities, use broader location terms (e.g., "California" instead of "San Francisco"). |
| **Email extraction may fail** | Mark as "not found" in the report. Suggest alternate contact methods: LinkedIn InMail, company careers page, or generic contact forms. |
| **Profile scrape returns empty** | Verify URL format; ensure profile is public. If private, use manual input fallback. |
| **Groq API returns errors** | Check API key validity and quota. Consider batching or reducing request size if hitting limits. |

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `FIRECRAWL_API_KEY` | Yes | Web scraping and search via Firecrawl |
| `GROQ_API_KEY` | Yes | LLM analysis and matching via Groq |

## Orchestration

For a single end-to-end run, use the orchestrator:

```bash
python tools/run_radar.py --linkedin "https://www.linkedin.com/in/username/" --role "Senior Product Manager" --location "San Francisco, Remote"
```

This runs all four steps in sequence and produces the final report.

## Lessons Learned

<!-- Update this section as you discover quirks, rate limits, or failure patterns -->
- (none yet — this is a new workflow)
