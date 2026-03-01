# AI Opportunity Radar

AI-powered job opportunity finder that analyzes your LinkedIn profile and finds matching opportunities across job boards.

## How It Works

The pipeline runs in four steps:

1. **Profile Analysis** — Scrapes your LinkedIn profile via Firecrawl and extracts key skills, experience, and education.
2. **Opportunity Search** — Searches job boards (LinkedIn, Indeed, company career pages, etc.) using Firecrawl web search for roles matching your target title and location.
3. **AI Matching & Enrichment** — Scores each opportunity against your profile using a Groq LLM, with reasoning for each match. Extracts emails and contact info when available.
4. **Report Generation** — Compiles findings into a structured markdown report with match scores, links, and contact details.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variables

Create a `.env` file in the project root:

```bash
FIRECRAWL_API_KEY=your_firecrawl_api_key
GROQ_API_KEY=your_groq_api_key
```

### 3. Run the radar

```bash
python tools/run_radar.py --linkedin "https://www.linkedin.com/in/yourusername/" --role "Senior Product Manager" --location "San Francisco, Remote"
```

## Example Usage

```bash
python tools/run_radar.py --linkedin "https://www.linkedin.com/in/username/" --role "Role" --location "Location"
```

**Multiple locations:**

```bash
python tools/run_radar.py --linkedin "https://www.linkedin.com/in/username/" --role "Data Engineer" --location "New York, Remote, Austin"
```

## Output Format

The report is saved to `.tmp/opportunity_report_YYYY-MM-DD.md` and includes:

- **Header**: Date, target role, location, profile summary
- **Opportunities table**: Role, company, link, match score (0–100), contact info (if found)
- **Match reasoning**: Per-opportunity explanation of fit
- **Summary stats**: Total opportunities, average score, top matches

## Tech Stack

| Component | Technology |
|-----------|------------|
| Web scraping & search | [Firecrawl](https://firecrawl.dev) |
| LLM analysis & matching | [Groq](https://groq.com) |
| Language | Python |

## Project Structure

```
ai-opportunity-radar/
├── workflows/           # Workflow SOPs
│   └── find_opportunities.md
├── tools/                # Python scripts
│   ├── scrape_linkedin_profile.py
│   ├── search_opportunities.py
│   ├── analyze_and_match.py
│   ├── generate_report.py
│   └── run_radar.py      # Orchestrator
├── .tmp/                 # Intermediates & reports (regenerated)
├── .env                  # API keys (gitignored)
└── README.md
```

## WAT Framework

This project follows the WAT (Workflows, Agents, Tools) architecture:

- **Workflows**: `workflows/find_opportunities.md` defines the SOP
- **Tools**: Python scripts in `tools/` that do the execution
- **Agents**: Coordinate by reading the workflow and running tools in sequence

## License

MIT
