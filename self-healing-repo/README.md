# Self-Healing Repository

An AI-powered GitHub automation system that detects, fixes, and improves code automatically — without waiting for a developer to intervene.

Instead of just reviewing pull requests, it **actively repairs them**.

## What It Does

When triggered on a PR, the system:

- **Fixes lint and formatting issues** — trailing whitespace, inconsistent style
- **Removes debug artifacts** — `console.log`, `print()`, `debugger` statements
- **Detects security risks** — hardcoded secrets, SQL injection, unsafe eval
- **Catches bugs** — bare exception handlers, null reference chains, resource leaks
- **Flags code smells** — god functions, deep nesting, magic numbers
- **Identifies missing tests** — new files without corresponding test files
- **Suggests improvements** — performance patterns, documentation gaps

## Architecture: The WAT Framework

This project uses the **WAT (Workflows, Agents, Tools)** architecture — a pattern that separates AI reasoning from deterministic execution.

```
┌─────────────────────────────────────────┐
│  Layer 1: Workflows (Instructions)      │
│  Markdown SOPs in workflows/            │
├─────────────────────────────────────────┤
│  Layer 2: Agent (Decision-Maker)        │
│  AI reads workflow, orchestrates tools  │
├─────────────────────────────────────────┤
│  Layer 3: Tools (Execution)             │
│  Python scripts in tools/               │
└─────────────────────────────────────────┘
```

**Why this matters:** When AI handles every step directly, accuracy compounds downward (90% per step = 59% after 5 steps). By offloading execution to deterministic scripts, the AI stays focused on orchestration and decision-making.

## Project Structure

```
.
├── CLAUDE.md              # Agent instructions (WAT framework config)
├── workflows/
│   └── heal_pr.md         # Step-by-step SOP for PR review & healing
├── tools/
│   ├── gh_fetch_pr.py     # Fetch PR metadata, diff, clone branch
│   ├── analyze_diff.py    # Run all analysis checks on changed files
│   ├── apply_fixes.py     # Auto-fix lint, dead code, formatting
│   └── gh_post_review.py  # Post review comments / push fix commits
├── .tmp/                  # Temporary processing files (gitignored)
├── .env                   # GitHub token (gitignored)
├── .env.example           # Template for .env
└── requirements.txt       # Python dependencies
```

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Yasir-Khan-7/self-healing-repo.git
cd self-healing-repo
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your GitHub Personal Access Token
# Token needs: repo scope (classic) or Pull requests + Issues read/write (fine-grained)
```

### 3. Run on a PR

```bash
# Step 1: Fetch the PR
python tools/gh_fetch_pr.py --repo owner/repo --pr 42

# Step 2: Analyze
python tools/analyze_diff.py --pr-dir .tmp/pr-42

# Step 3: Auto-fix (optional)
python tools/apply_fixes.py --pr-dir .tmp/pr-42 --analysis .tmp/pr-42/analysis.json --categories P2,P3

# Step 4: Post review
python tools/gh_post_review.py --repo owner/repo --pr 42 --analysis .tmp/pr-42/analysis.json
```

Or with an AI agent (Cursor, Claude Code, etc.), just say:

> "Review PR #42 on owner/repo"

The agent reads `workflows/heal_pr.md` and runs the full pipeline automatically.

## Analysis Categories

| Priority | Category | What It Catches |
|----------|----------|-----------------|
| **P0** | Security | Hardcoded secrets, SQL injection, unsafe eval/exec, pickle |
| **P1** | Bugs | Bare excepts, null ref chains, missing error handling |
| **P2** | Lint | Trailing whitespace, mixed indentation |
| **P3** | Dead Code | `console.log`, `print()`, `debugger`, unused imports, commented-out code |
| **P4** | Code Smells | Functions >50 lines, nesting >4 levels, magic numbers |
| **P5** | Performance | Inefficient patterns (flagged for review) |
| **P6** | Tests | New files without corresponding test files |
| **P7** | Docs | Missing/outdated documentation |

**Auto-fixable:** P2 and P3 can be automatically fixed. P0-P1 are flagged as critical. P4-P7 are suggestions.

## Supported Languages

Python, JavaScript, TypeScript, Go, Java, Ruby, Rust, C/C++, Shell, YAML/JSON configs.

## How the Review Looks

When posted on a PR, the review follows this format:

```
## Self-Healing PR Review

Status: NEEDS_ATTENTION
Files Analyzed: 5
Issues Found: 3 (1 auto-fixed, 2 remaining)

### Critical (P0-P1)
- 🟠 [Bugs] `src/api.py` L42: Broad exception catch

### Auto-Fixed
- `src/utils.js`: debug_logs_removed (3 instances)

### Suggestions
- 🔵 [Code Smells] `src/handler.py` L15: Function is 67 lines long
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. We welcome:

- New analysis patterns (security, performance, language-specific)
- Support for additional languages
- New auto-fix capabilities
- Workflow improvements
- Documentation

## License

MIT License — see [LICENSE](LICENSE) for details.

## Credits

Built by [@Yasir-Khan-7](https://github.com/Yasir-Khan-7) using the WAT (Workflows, Agents, Tools) framework.
