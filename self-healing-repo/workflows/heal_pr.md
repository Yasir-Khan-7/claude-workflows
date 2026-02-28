# Workflow: Self-Healing PR Review

## Objective
Review a GitHub Pull Request, detect code quality issues, automatically fix what can be fixed, and post a clean summary. The goal is to send only clean, production-ready PRs for human review.

## When to Use
- Before requesting a human code review on any PR
- When triggered manually by providing a repo + PR number
- As a pre-review gate to catch issues early

## Required Inputs
| Input | Source | Example |
|-------|--------|---------|
| `GITHUB_TOKEN` | `.env` | `ghp_xxxxxxxxxxxx` |
| `repo` | User provides | `owner/repo-name` |
| `pr_number` | User provides | `42` |
| `auto_fix` | User provides (optional) | `true` or `false` (default: `true`) |
| `push_fixes` | User provides (optional) | `true` or `false` (default: `false`) |

## Tools Used
| Tool | Purpose |
|------|---------|
| `tools/gh_fetch_pr.py` | Fetch PR metadata, diff, and changed files |
| `tools/analyze_diff.py` | Analyze the diff for all issue categories |
| `tools/apply_fixes.py` | Apply automatic fixes to a local clone |
| `tools/gh_post_review.py` | Post review comments or push fix commits |

## Procedure

### Step 1: Fetch the PR
```bash
python tools/gh_fetch_pr.py --repo owner/repo --pr 42
```
- This clones the PR branch locally into `.tmp/pr-{number}/`
- Outputs PR metadata to `.tmp/pr-{number}/metadata.json`
- Outputs the raw diff to `.tmp/pr-{number}/diff.patch`
- Outputs list of changed files to `.tmp/pr-{number}/changed_files.json`

**If this fails:** Check that `GITHUB_TOKEN` is set in `.env` and has `repo` scope. Check the repo name is correct (owner/repo format).

### Step 2: Analyze the Diff
```bash
python tools/analyze_diff.py --pr-dir .tmp/pr-42
```
- Reads the changed files from the local clone
- Runs all analysis checks against changed files only (not the entire repo)
- Outputs a structured report to `.tmp/pr-{number}/analysis.json`

**Analysis categories (in order of severity):**

| Priority | Category | What It Catches |
|----------|----------|-----------------|
| P0 | Security | Hardcoded secrets, SQL injection patterns, unsafe eval, exposed endpoints |
| P1 | Bugs | Obvious null refs, unclosed resources, race conditions, missing error handling |
| P2 | Lint & Formatting | Style violations, inconsistent formatting, import ordering |
| P3 | Dead Code | `console.log`, `print()` debug statements, unused imports, commented-out code |
| P4 | Code Smells | God functions (>50 lines), deep nesting (>3 levels), magic numbers, duplicate blocks |
| P5 | Performance | N+1 queries, unnecessary re-renders, missing indexes, inefficient loops |
| P6 | Tests | Missing test coverage for new public functions/endpoints |
| P7 | Documentation | Missing/outdated docstrings, README not updated for new features |

**If this fails:** Check that the PR was fetched successfully in Step 1. The `.tmp/pr-{number}/` directory must exist with the cloned files.

### Step 3: Decide What to Fix
The agent (you) reviews the analysis report and decides:

- **Auto-fixable issues** (fix without asking): Lint, formatting, debug logs, unused imports, simple missing error handling
- **Needs confirmation** (ask before fixing): Refactoring, adding tests, security patches, performance changes
- **Report only** (never auto-fix): Architectural concerns, major refactors, design pattern issues

**Decision rules:**
1. If `auto_fix` is `false`, skip to Step 5 (report only)
2. If `auto_fix` is `true`, apply fixes for auto-fixable categories (P2, P3)
3. For P0-P1 issues, always flag them prominently but ask before fixing
4. For P4-P7, include suggested fixes in the review comment but don't auto-apply

### Step 4: Apply Fixes (if auto_fix is true)
```bash
python tools/apply_fixes.py --pr-dir .tmp/pr-42 --analysis .tmp/pr-42/analysis.json --categories P2,P3
```
- Reads the analysis report
- Applies fixes only for the specified categories
- Creates a detailed changelog at `.tmp/pr-{number}/fixes_applied.json`
- Does NOT touch files outside the changed files list

**If this fails:** Some fixes may conflict. The tool will skip conflicting fixes and report them. Check `.tmp/pr-{number}/fixes_applied.json` for what was and wasn't applied.

### Step 5: Post the Review
```bash
python tools/gh_post_review.py --repo owner/repo --pr 42 --analysis .tmp/pr-42/analysis.json --fixes .tmp/pr-42/fixes_applied.json --push-fixes {true|false}
```

**Two modes:**

**Mode A: Report Only (`push_fixes=false`)**
- Posts a review comment on the PR with the full analysis
- Uses inline comments for file-specific issues
- Summarizes findings by category with severity labels
- Suggests fixes as code suggestions in GitHub's review format

**Mode B: Fix and Push (`push_fixes=true`)**
- Commits the applied fixes to the PR branch
- Commit message: `fix: auto-heal - {summary of fixes}`
- Posts a review comment summarizing what was fixed and what still needs attention
- Requests changes if P0/P1 issues remain unfixed

**If this fails:** Check GitHub token permissions. For pushing, the token needs write access to the repo. If the PR is from a fork, pushing won't work — fall back to Mode A.

## Expected Outputs
| Output | Location |
|--------|----------|
| PR metadata | `.tmp/pr-{number}/metadata.json` |
| Raw diff | `.tmp/pr-{number}/diff.patch` |
| Analysis report | `.tmp/pr-{number}/analysis.json` |
| Fixes changelog | `.tmp/pr-{number}/fixes_applied.json` |
| GitHub review comment | Posted on the PR |
| Fix commit (optional) | Pushed to PR branch |

## Edge Cases

| Situation | How to Handle |
|-----------|---------------|
| PR has no code changes (docs only) | Run only P7 analysis, skip others |
| PR is already merged | Abort with message, don't post review |
| PR has merge conflicts | Report it, skip fixing, post analysis only |
| Token lacks push permission | Fall back to report-only mode |
| PR has 100+ changed files | Warn the user, ask if they want to proceed (slow) |
| Analysis finds zero issues | Post a clean bill of health comment |
| Language not supported | Skip language-specific checks, run generic ones |

## Review Comment Format

The posted review should follow this template:

```markdown
## Self-Healing PR Review

**Status:** {CLEAN | NEEDS_ATTENTION | CRITICAL}
**Files Analyzed:** {count}
**Issues Found:** {count} ({auto_fixed} auto-fixed, {remaining} remaining)

### Critical (P0-P1)
{list of security/bug issues, or "None found"}

### Auto-Fixed
{list of fixes applied, or "No auto-fixes applied"}

### Suggestions
{list of recommended improvements for P4-P7}

### Summary
{one paragraph assessment of the PR quality}
```

## Supported Languages
- Python (.py)
- JavaScript / TypeScript (.js, .ts, .jsx, .tsx)
- Go (.go)
- Java (.java)
- Ruby (.rb)
- Rust (.rs)
- C/C++ (.c, .cpp, .h)
- Shell (.sh, .bash)
- YAML/JSON config files

## Lessons Learned
<!-- Update this section as you discover quirks, rate limits, or failure patterns -->
- (none yet — this is a new workflow)
