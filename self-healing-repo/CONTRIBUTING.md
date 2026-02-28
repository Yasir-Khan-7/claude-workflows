# Contributing to Self-Healing Repository

Thanks for your interest in contributing! This project uses the **WAT framework** (Workflows, Agents, Tools), so understanding the architecture will help you contribute effectively.

## Architecture Overview

```
workflows/    → Markdown SOPs (what to do, step by step)
tools/        → Python scripts (deterministic execution)
CLAUDE.md     → Agent instructions (how the AI orchestrates)
```

- **Workflows** define the procedure. They never execute code directly.
- **Tools** do the actual work. They're standalone scripts with clear inputs/outputs.
- **The Agent** (AI) reads workflows and runs tools in sequence.

## How to Contribute

### Adding New Analysis Patterns

The easiest way to contribute. Open `tools/analyze_diff.py` and add patterns to the relevant category:

```python
# Example: Add a new security pattern
SECURITY_PATTERNS = {
    "your_new_check": [
        (r"your_regex_pattern", "Description of the issue"),
    ],
    ...
}
```

**Categories:**
- `SECURITY_PATTERNS` → P0 (Critical)
- `BUG_PATTERNS` → P1 (Important)
- `LINT_PATTERNS` → P2 (Auto-fixable)
- `DEAD_CODE_PATTERNS` → P3 (Auto-fixable)
- `CODE_SMELL_PATTERNS` → P4 (Suggestions)

### Adding Language Support

1. Add the file extension to `LANGUAGE_EXTENSIONS` in `tools/analyze_diff.py`
2. Add language-specific patterns to `DEAD_CODE_PATTERNS` (debug statements vary by language)
3. If the language has unique patterns, add them to the relevant category

### Adding New Auto-Fix Capabilities

Open `tools/apply_fixes.py`:

1. Write a fix function: `def fix_something(content: str) -> tuple[str, int]`
2. Return the fixed content and the count of fixes applied
3. Register it in the `FIXERS` dict under the appropriate category
4. Only P2 and P3 should be auto-fixed. Higher severity needs human review.

### Improving the Workflow

Edit `workflows/heal_pr.md` to:
- Add edge cases you've encountered
- Update the "Lessons Learned" section
- Improve the review comment template
- Add new steps to the procedure

## Development Setup

```bash
git clone https://github.com/Yasir-Khan-7/self-healing-repo.git
cd self-healing-repo
pip install -r requirements.txt
cp .env.example .env
# Add your GitHub token to .env
```

## Pull Request Guidelines

1. **One concern per PR** — Don't mix new patterns with refactoring
2. **Test your patterns** — Include example code that triggers the pattern
3. **Update the workflow** — If you add a new tool or change behavior, update `workflows/heal_pr.md`
4. **Don't commit secrets** — Never commit `.env` or tokens

## Code Style

- Python 3.10+ (type hints, f-strings)
- Functions should be focused and under 50 lines (we check for this!)
- No debug prints in committed code (we check for this too!)
- Docstrings on all public functions

## Reporting Issues

When reporting a bug or false positive:
- Include the file type and language
- Include the code snippet that triggered the issue
- Mention which category (P0-P7) was involved
- If it's a false positive, explain why it shouldn't be flagged

## Questions?

Open a GitHub issue or discussion. We're happy to help!
