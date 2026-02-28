#!/usr/bin/env python3
"""
Analyze changed files from a PR for code quality issues.

Usage:
    python tools/analyze_diff.py --pr-dir .tmp/pr-42

Outputs:
    .tmp/pr-{number}/analysis.json - Structured analysis report

Reads:
    .tmp/pr-{number}/changed_files.json - List of changed files
    .tmp/pr-{number}/repo/              - Cloned repository

Categories:
    P0: Security    - Hardcoded secrets, injection, unsafe patterns
    P1: Bugs        - Null refs, missing error handling, resource leaks
    P2: Lint        - Style issues, formatting, import ordering
    P3: Dead Code   - Debug logs, unused imports, commented-out code
    P4: Code Smells - Long functions, deep nesting, magic numbers
    P5: Performance - Inefficient patterns, N+1, unnecessary work
    P6: Tests       - Missing coverage for new public functions
    P7: Docs        - Missing/outdated docstrings
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".sh": "shell",
    ".bash": "shell",
}

CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"}


# --- Pattern Definitions ---

SECURITY_PATTERNS = {
    "hardcoded_secret": [
        (r"""(?:password|secret|api_key|apikey|token|private_key)\s*[=:]\s*['\"][^'\"]{8,}['\"]""", "Possible hardcoded secret"),
        (r"""(?:AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY)\s*[=:]\s*['\"][^'\"]+['\"]""", "AWS credential in code"),
    ],
    "sql_injection": [
        (r"""(?:execute|cursor\.execute|query)\s*\(\s*(?:f['\"]|['\"].*%s|['\"].*\+)""", "Possible SQL injection via string interpolation"),
    ],
    "unsafe_eval": [
        (r"""\beval\s*\(""", "Use of eval() — potential code injection"),
        (r"""\bexec\s*\(""", "Use of exec() — potential code injection"),
    ],
    "unsafe_deserialization": [
        (r"""pickle\.loads?\(""", "Unsafe pickle deserialization"),
        (r"""yaml\.load\s*\((?!.*Loader)""", "Unsafe YAML load without safe Loader"),
    ],
}

BUG_PATTERNS = {
    "missing_error_handling": [
        (r"""except\s*:""", "Bare except clause — catches everything including KeyboardInterrupt"),
        (r"""except\s+Exception\s*:""", "Broad exception catch — consider catching specific exceptions"),
    ],
    "null_check": [
        (r"""\.get\([^)]+\)\.[a-zA-Z]""", "Chained access after .get() without null check"),
    ],
}

LINT_PATTERNS = {
    "trailing_whitespace": [
        (r"""[ \t]+$""", "Trailing whitespace"),
    ],
    "mixed_indentation": [
        (r"""^\t+ """, "Mixed tabs and spaces"),
        (r"""^ +\t""", "Mixed spaces and tabs"),
    ],
}

DEAD_CODE_PATTERNS = {
    "debug_logs": {
        "python": [
            (r"""^\s*print\s*\(""", "Debug print() statement"),
            (r"""^\s*pdb\.set_trace\(\)""", "Debugger breakpoint left in code"),
            (r"""^\s*breakpoint\(\)""", "Debugger breakpoint left in code"),
            (r"""^\s*import\s+pdb""", "Debug import left in code"),
        ],
        "javascript": [
            (r"""^\s*console\.log\s*\(""", "Debug console.log() statement"),
            (r"""^\s*console\.debug\s*\(""", "Debug console.debug() statement"),
            (r"""^\s*debugger\b""", "Debugger statement left in code"),
        ],
        "typescript": [
            (r"""^\s*console\.log\s*\(""", "Debug console.log() statement"),
            (r"""^\s*console\.debug\s*\(""", "Debug console.debug() statement"),
            (r"""^\s*debugger\b""", "Debugger statement left in code"),
        ],
        "go": [
            (r"""^\s*fmt\.Println\(""", "Debug fmt.Println() — consider structured logging"),
        ],
    },
    "commented_code": [
        (r"""^\s*(?://|#)\s*(?:if|for|while|def|func|class|return|import)\b""", "Commented-out code block"),
    ],
}

CODE_SMELL_PATTERNS = {
    "magic_numbers": [
        (r"""(?<![\w.])\b(?!0\b|1\b|2\b|100\b)\d{3,}\b(?!\.\d)""", "Magic number — consider extracting to a named constant"),
    ],
    "todo_fixme": [
        (r"""(?:TODO|FIXME|HACK|XXX|WORKAROUND)\b""", "TODO/FIXME marker found"),
    ],
}


def detect_language(filepath: str) -> str | None:
    ext = Path(filepath).suffix.lower()
    return LANGUAGE_EXTENSIONS.get(ext)


def is_config_file(filepath: str) -> bool:
    return Path(filepath).suffix.lower() in CONFIG_EXTENSIONS


def run_pattern_checks(content: str, patterns: list, filepath: str, category: str, subcategory: str) -> list:
    issues = []
    for line_num, line in enumerate(content.splitlines(), 1):
        for pattern, message in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append({
                    "file": filepath,
                    "line": line_num,
                    "category": category,
                    "subcategory": subcategory,
                    "message": message,
                    "severity": category,
                    "line_content": line.rstrip(),
                    "auto_fixable": category in ("P2", "P3"),
                })
    return issues


def analyze_function_length(content: str, filepath: str, language: str) -> list:
    issues = []
    if language == "python":
        func_pattern = re.compile(r"^(\s*)(def|async\s+def)\s+(\w+)")
    elif language in ("javascript", "typescript"):
        func_pattern = re.compile(r"^(\s*)(?:(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(?)")
    else:
        return issues

    lines = content.splitlines()
    current_func = None
    func_start = 0
    func_indent = 0

    for i, line in enumerate(lines):
        match = func_pattern.match(line)
        if match:
            if current_func and (i - func_start) > 50:
                issues.append({
                    "file": filepath,
                    "line": func_start + 1,
                    "category": "P4",
                    "subcategory": "long_function",
                    "message": f"Function `{current_func}` is {i - func_start} lines long (>50 line threshold)",
                    "severity": "P4",
                    "line_content": lines[func_start].rstrip(),
                    "auto_fixable": False,
                })
            current_func = match.group(3) if match.lastindex >= 3 and match.group(3) else match.group(2) if match.lastindex >= 2 else "anonymous"
            func_start = i
            func_indent = len(match.group(1))

    if current_func and (len(lines) - func_start) > 50:
        issues.append({
            "file": filepath,
            "line": func_start + 1,
            "category": "P4",
            "subcategory": "long_function",
            "message": f"Function `{current_func}` is {len(lines) - func_start} lines long (>50 line threshold)",
            "severity": "P4",
            "line_content": lines[func_start].rstrip(),
            "auto_fixable": False,
        })

    return issues


def analyze_nesting_depth(content: str, filepath: str, language: str) -> list:
    issues = []
    if language not in ("python", "javascript", "typescript"):
        return issues

    lines = content.splitlines()
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*")):
            continue

        if language == "python":
            indent = len(line) - len(stripped)
            depth = indent // 4
        else:
            depth = 0
            for ch in line:
                if ch in (" ", "\t"):
                    depth += 1
                else:
                    break
            depth = depth // 4 if depth > 0 else 0

        if depth > 4:
            issues.append({
                "file": filepath,
                "line": i + 1,
                "category": "P4",
                "subcategory": "deep_nesting",
                "message": f"Nesting depth of {depth} levels — consider extracting to a helper function",
                "severity": "P4",
                "line_content": line.rstrip(),
                "auto_fixable": False,
            })

    return issues


def check_missing_tests(changed_files: list, repo_path: Path) -> list:
    issues = []
    new_files = [f for f in changed_files if f["status"] == "added"]

    for f in new_files:
        filepath = f["filename"]
        lang = detect_language(filepath)
        if not lang or is_config_file(filepath):
            continue

        if "test" in filepath.lower() or "spec" in filepath.lower():
            continue

        has_test = False
        name = Path(filepath).stem
        test_patterns = [
            f"test_{name}",
            f"{name}_test",
            f"{name}.test",
            f"{name}.spec",
        ]

        for cf in changed_files:
            cf_stem = Path(cf["filename"]).stem.lower()
            if any(p.lower() == cf_stem for p in test_patterns):
                has_test = True
                break

        if not has_test:
            issues.append({
                "file": filepath,
                "line": 1,
                "category": "P6",
                "subcategory": "missing_tests",
                "message": f"New file `{filepath}` has no corresponding test file in this PR",
                "severity": "P6",
                "line_content": "",
                "auto_fixable": False,
            })

    return issues


def analyze_file(filepath: str, content: str, language: str) -> list:
    issues = []

    for subcat, patterns in SECURITY_PATTERNS.items():
        issues.extend(run_pattern_checks(content, patterns, filepath, "P0", subcat))

    for subcat, patterns in BUG_PATTERNS.items():
        issues.extend(run_pattern_checks(content, patterns, filepath, "P1", subcat))

    for subcat, patterns in LINT_PATTERNS.items():
        issues.extend(run_pattern_checks(content, patterns, filepath, "P2", subcat))

    for subcat, patterns_by_lang in DEAD_CODE_PATTERNS.items():
        if isinstance(patterns_by_lang, dict):
            lang_patterns = patterns_by_lang.get(language, [])
            issues.extend(run_pattern_checks(content, lang_patterns, filepath, "P3", subcat))
        else:
            issues.extend(run_pattern_checks(content, patterns_by_lang, filepath, "P3", subcat))

    for subcat, patterns in CODE_SMELL_PATTERNS.items():
        issues.extend(run_pattern_checks(content, patterns, filepath, "P4", subcat))

    issues.extend(analyze_function_length(content, filepath, language))
    issues.extend(analyze_nesting_depth(content, filepath, language))

    return issues


def main():
    parser = argparse.ArgumentParser(description="Analyze PR diff for code quality issues")
    parser.add_argument("--pr-dir", required=True, help="Path to PR directory (.tmp/pr-N)")
    args = parser.parse_args()

    pr_dir = Path(args.pr_dir)
    changed_files_path = pr_dir / "changed_files.json"
    repo_path = pr_dir / "repo"

    if not changed_files_path.exists():
        print(f"ERROR: {changed_files_path} not found. Run gh_fetch_pr.py first.", file=sys.stderr)
        sys.exit(1)

    changed_files = json.loads(changed_files_path.read_text())
    print(f"Analyzing {len(changed_files)} changed files...")

    all_issues = []
    files_analyzed = 0
    files_skipped = 0

    for cf in changed_files:
        filepath = cf["filename"]

        if cf["status"] == "removed":
            continue

        language = detect_language(filepath)
        if not language and not is_config_file(filepath):
            files_skipped += 1
            continue

        file_path = repo_path / filepath
        if file_path.exists():
            content = file_path.read_text(errors="replace")
        elif cf.get("patch"):
            added_lines = []
            for line in cf["patch"].splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    added_lines.append(line[1:])
            content = "\n".join(added_lines)
        else:
            files_skipped += 1
            continue

        if language:
            file_issues = analyze_file(filepath, content, language)
            all_issues.extend(file_issues)
        files_analyzed += 1

    all_issues.extend(check_missing_tests(changed_files, repo_path))

    summary = {
        "P0": len([i for i in all_issues if i["category"] == "P0"]),
        "P1": len([i for i in all_issues if i["category"] == "P1"]),
        "P2": len([i for i in all_issues if i["category"] == "P2"]),
        "P3": len([i for i in all_issues if i["category"] == "P3"]),
        "P4": len([i for i in all_issues if i["category"] == "P4"]),
        "P5": len([i for i in all_issues if i["category"] == "P5"]),
        "P6": len([i for i in all_issues if i["category"] == "P6"]),
        "P7": len([i for i in all_issues if i["category"] == "P7"]),
    }

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pr_dir": str(pr_dir),
        "files_analyzed": files_analyzed,
        "files_skipped": files_skipped,
        "total_issues": len(all_issues),
        "auto_fixable": len([i for i in all_issues if i["auto_fixable"]]),
        "summary": summary,
        "issues": sorted(all_issues, key=lambda x: x["category"]),
    }

    output_path = pr_dir / "analysis.json"
    output_path.write_text(json.dumps(report, indent=2))

    print(f"\nAnalysis complete:")
    print(f"  Files analyzed: {files_analyzed}")
    print(f"  Files skipped:  {files_skipped}")
    print(f"  Total issues:   {len(all_issues)}")
    print(f"  Auto-fixable:   {report['auto_fixable']}")
    print(f"\n  Breakdown:")
    labels = {
        "P0": "Security", "P1": "Bugs", "P2": "Lint", "P3": "Dead Code",
        "P4": "Smells", "P5": "Performance", "P6": "Tests", "P7": "Docs",
    }
    for key, count in summary.items():
        if count > 0:
            print(f"    {key} ({labels[key]}): {count}")

    print(f"\nReport saved to {output_path}")


if __name__ == "__main__":
    main()
