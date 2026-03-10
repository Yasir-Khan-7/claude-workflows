# Claude Workflows

A collection of AI-powered automation workflows built on the **WAT framework** (Workflows, Agents, Tools).

Each project in this repo is a self-contained automation that an AI agent can orchestrate — reading a workflow SOP, running deterministic tools, and delivering results.

## The WAT Framework

```
┌─────────────────────────────────────────┐
│  Workflows   → What to do (Markdown)    │
│  Agents      → How to decide (AI)       │
│  Tools       → How to execute (Python)  │
└─────────────────────────────────────────┘
```

**Why?** When AI handles every step directly, accuracy compounds downward. By splitting reasoning (AI) from execution (scripts), each part does what it's best at.

See [`CLAUDE.md`](CLAUDE.md) for the full agent instructions.

## Projects

| Project | Description | Status |
|---------|-------------|--------|
| [**Self-Healing Repo**](self-healing-repo/) | AI-powered PR reviewer that detects bugs, security issues, lint problems, and dead code — then posts structured reviews on GitHub | ✅ Live |
| [**AI Opportunity Radar**](ai-opportunity-radar/) | Analyzes your LinkedIn profile and finds matching job opportunities with AI-powered scoring, contact extraction, and detailed reports | ✅ Live |
| [**ML Data Advisor**](ml-data-advisor/) | Analyzes any dataset and recommends ML vs DL, ranks 15+ algorithms by suitability, generates preprocessing pipelines and training plans with code snippets | ✅ Live |

## Quick Start

1. Clone the repo
2. Pick a project folder
3. Follow its `README.md` for setup
4. Or use an AI agent (Cursor, Claude Code) — it reads the workflow and runs everything automatically

```bash
git clone https://github.com/Yasir-Khan-7/claude-workflows.git
cd claude-workflows
```

## Adding a New Workflow

Each project lives in its own folder with this structure:

```
your-project/
├── README.md           # Project overview & quick start
├── CONTRIBUTING.md     # How to contribute
├── requirements.txt    # Dependencies
├── workflows/          # Markdown SOPs
│   └── your_workflow.md
└── tools/              # Python scripts
    └── your_tool.py
```

## License

MIT — see individual project folders for details.

## Author

Built by [@Yasir-Khan-7](https://github.com/Yasir-Khan-7)
