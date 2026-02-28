#!/usr/bin/env python3
"""
Apply automatic fixes to code based on the analysis report.

Usage:
    python tools/apply_fixes.py --pr-dir .tmp/pr-42 --analysis .tmp/pr-42/analysis.json --categories P2,P3

Only modifies files within the PR's changed files list.
Only applies fixes for the specified priority categories.

Outputs:
    .tmp/pr-{number}/fixes_applied.json - What was fixed and what was skipped
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone


def fix_trailing_whitespace(content: str) -> tuple[str, int]:
    lines = content.splitlines(keepends=True)
    fixed = []
    count = 0
    for line in lines:
        stripped = line.rstrip() + ("\n" if line.endswith("\n") else "")
        if stripped != line:
            count += 1
        fixed.append(stripped)
    return "".join(fixed), count


def fix_debug_prints_python(content: str) -> tuple[str, int]:
    lines = content.splitlines(keepends=True)
    fixed = []
    count = 0
    skip_patterns = [
        re.compile(r"^\s*print\s*\("),
        re.compile(r"^\s*pdb\.set_trace\(\)"),
        re.compile(r"^\s*breakpoint\(\)"),
        re.compile(r"^\s*import\s+pdb\s*$"),
    ]
    for line in lines:
        is_debug = any(p.search(line) for p in skip_patterns)
        if is_debug:
            count += 1
            continue
        fixed.append(line)
    return "".join(fixed), count


def fix_debug_prints_js(content: str) -> tuple[str, int]:
    lines = content.splitlines(keepends=True)
    fixed = []
    count = 0
    skip_patterns = [
        re.compile(r"^\s*console\.log\s*\("),
        re.compile(r"^\s*console\.debug\s*\("),
        re.compile(r"^\s*debugger\s*;?\s*$"),
    ]
    for line in lines:
        is_debug = any(p.search(line) for p in skip_patterns)
        if is_debug:
            count += 1
            continue
        fixed.append(line)
    return "".join(fixed), count


def fix_unused_imports_python(content: str) -> tuple[str, int]:
    """Remove imports that are never referenced elsewhere in the file."""
    lines = content.splitlines(keepends=True)
    import_pattern = re.compile(r"^\s*(?:from\s+\S+\s+)?import\s+(.+)")
    body_without_imports = []
    import_lines = {}

    for i, line in enumerate(lines):
        match = import_pattern.match(line)
        if match:
            imported = match.group(1).strip()
            names = [n.strip().split(" as ")[-1].strip() for n in imported.split(",")]
            for name in names:
                if name and name != "*":
                    import_lines.setdefault(i, []).append(name)
        else:
            body_without_imports.append(line)

    body_text = "".join(body_without_imports)
    lines_to_remove = set()
    for line_idx, names in import_lines.items():
        all_unused = all(
            not re.search(r"\b" + re.escape(name) + r"\b", body_text)
            for name in names
        )
        if all_unused:
            lines_to_remove.add(line_idx)

    if not lines_to_remove:
        return content, 0

    fixed = [line for i, line in enumerate(lines) if i not in lines_to_remove]
    return "".join(fixed), len(lines_to_remove)


def fix_commented_code(content: str, lang: str) -> tuple[str, int]:
    lines = content.splitlines(keepends=True)
    fixed = []
    count = 0
    code_keywords = {"if", "for", "while", "def", "func", "class", "return", "import"}

    if lang == "python":
        comment_char = "#"
    elif lang in ("javascript", "typescript", "go", "java", "rust", "c", "cpp"):
        comment_char = "//"
    else:
        return content, 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(comment_char):
            after_comment = stripped[len(comment_char):].strip()
            first_word = after_comment.split("(")[0].split(" ")[0].lower()
            if first_word in code_keywords:
                count += 1
                continue
        fixed.append(line)
    return "".join(fixed), count


FIXERS = {
    "P2": {
        "trailing_whitespace": fix_trailing_whitespace,
    },
    "P3": {
        "debug_logs_python": fix_debug_prints_python,
        "debug_logs_js": fix_debug_prints_js,
        "unused_imports_python": fix_unused_imports_python,
        "commented_code": fix_commented_code,
    },
}

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


def detect_language(filepath: str) -> str | None:
    ext = Path(filepath).suffix.lower()
    return LANGUAGE_EXTENSIONS.get(ext)


def apply_fixes_to_file(filepath: Path, content: str, language: str, categories: set) -> tuple[str, list]:
    fixes = []
    current = content

    if "P2" in categories:
        current, count = fix_trailing_whitespace(current)
        if count > 0:
            fixes.append({"fix": "trailing_whitespace", "category": "P2", "count": count})

    if "P3" in categories:
        if language == "python":
            current, count = fix_debug_prints_python(current)
            if count > 0:
                fixes.append({"fix": "debug_prints_removed", "category": "P3", "count": count})

            current, count = fix_unused_imports_python(current)
            if count > 0:
                fixes.append({"fix": "unused_imports_removed", "category": "P3", "count": count})

        elif language in ("javascript", "typescript"):
            current, count = fix_debug_prints_js(current)
            if count > 0:
                fixes.append({"fix": "debug_logs_removed", "category": "P3", "count": count})

        current, count = fix_commented_code(current, language)
        if count > 0:
            fixes.append({"fix": "commented_code_removed", "category": "P3", "count": count})

    return current, fixes


def main():
    parser = argparse.ArgumentParser(description="Apply auto-fixes to PR code")
    parser.add_argument("--pr-dir", required=True, help="Path to PR directory (.tmp/pr-N)")
    parser.add_argument("--analysis", required=True, help="Path to analysis.json")
    parser.add_argument("--categories", default="P2,P3", help="Comma-separated priority categories to fix")
    args = parser.parse_args()

    pr_dir = Path(args.pr_dir)
    repo_path = pr_dir / "repo"
    categories = set(args.categories.upper().split(","))

    analysis_path = Path(args.analysis)
    if not analysis_path.exists():
        print(f"ERROR: {analysis_path} not found. Run analyze_diff.py first.", file=sys.stderr)
        sys.exit(1)

    analysis = json.loads(analysis_path.read_text())

    if not repo_path.exists():
        print("ERROR: Repo clone not found. Cannot apply fixes without local files.", file=sys.stderr)
        sys.exit(1)

    changed_files_path = pr_dir / "changed_files.json"
    changed_files = json.loads(changed_files_path.read_text())
    changed_filenames = {f["filename"] for f in changed_files if f["status"] != "removed"}

    print(f"Applying fixes for categories: {', '.join(sorted(categories))}")
    print(f"Files eligible: {len(changed_filenames)}")

    all_fixes = []
    files_modified = 0

    for filename in sorted(changed_filenames):
        language = detect_language(filename)
        if not language:
            continue

        file_path = repo_path / filename
        if not file_path.exists():
            continue

        original = file_path.read_text(errors="replace")
        fixed, fixes = apply_fixes_to_file(file_path, original, language, categories)

        if fixes:
            file_path.write_text(fixed)
            files_modified += 1
            for fix in fixes:
                fix["file"] = filename
                all_fixes.append(fix)
            print(f"  Fixed: {filename} ({len(fixes)} fix(es))")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "categories_applied": sorted(categories),
        "files_modified": files_modified,
        "total_fixes": len(all_fixes),
        "fixes": all_fixes,
    }

    output_path = pr_dir / "fixes_applied.json"
    output_path.write_text(json.dumps(report, indent=2))

    print(f"\nFixes applied:")
    print(f"  Files modified: {files_modified}")
    print(f"  Total fixes:    {len(all_fixes)}")
    print(f"  Report saved to {output_path}")


if __name__ == "__main__":
    main()
