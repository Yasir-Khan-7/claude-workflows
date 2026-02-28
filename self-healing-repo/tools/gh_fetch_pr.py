#!/usr/bin/env python3
"""
Fetch a GitHub PR's metadata, diff, and clone the PR branch locally.

Usage:
    python tools/gh_fetch_pr.py --repo owner/repo --pr 42

Outputs:
    .tmp/pr-{number}/metadata.json    - PR metadata (title, author, state, base, head)
    .tmp/pr-{number}/diff.patch       - Raw unified diff
    .tmp/pr-{number}/changed_files.json - List of changed file paths with status
    .tmp/pr-{number}/repo/            - Shallow clone of the PR branch

Requires:
    GITHUB_TOKEN in .env with repo scope
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_API = "https://api.github.com"


def get_headers():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not found in .env", file=sys.stderr)
        sys.exit(1)
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def fetch_pr_metadata(repo: str, pr_number: int) -> dict:
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=get_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()

    return {
        "number": data["number"],
        "title": data["title"],
        "state": data["state"],
        "merged": data.get("merged", False),
        "mergeable": data.get("mergeable"),
        "author": data["user"]["login"],
        "base_branch": data["base"]["ref"],
        "head_branch": data["head"]["ref"],
        "head_sha": data["head"]["sha"],
        "head_repo_clone_url": data["head"]["repo"]["clone_url"] if data["head"]["repo"] else None,
        "base_repo_clone_url": data["base"]["repo"]["clone_url"],
        "changed_files_count": data["changed_files"],
        "additions": data["additions"],
        "deletions": data["deletions"],
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
        "html_url": data["html_url"],
    }


def fetch_pr_diff(repo: str, pr_number: int) -> str:
    url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}"
    headers = get_headers()
    headers["Accept"] = "application/vnd.github.v3.diff"
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.text


def fetch_changed_files(repo: str, pr_number: int) -> list:
    files = []
    page = 1
    while True:
        url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/files"
        resp = requests.get(
            url,
            headers=get_headers(),
            params={"per_page": 100, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for f in batch:
            files.append({
                "filename": f["filename"],
                "status": f["status"],  # added, removed, modified, renamed
                "additions": f["additions"],
                "deletions": f["deletions"],
                "changes": f["changes"],
                "patch": f.get("patch", ""),
            })
        page += 1
    return files


def clone_pr_branch(metadata: dict, dest: Path):
    clone_url = metadata["head_repo_clone_url"] or metadata["base_repo_clone_url"]
    branch = metadata["head_branch"]

    token = os.getenv("GITHUB_TOKEN")
    authed_url = clone_url.replace("https://", f"https://x-access-token:{token}@")

    if dest.exists():
        shutil.rmtree(dest)

    subprocess.run(
        [
            "git", "clone",
            "--depth", "1",
            "--branch", branch,
            "--single-branch",
            authed_url,
            str(dest),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    print(f"Cloned {branch} into {dest}")


def main():
    parser = argparse.ArgumentParser(description="Fetch a GitHub PR for analysis")
    parser.add_argument("--repo", required=True, help="owner/repo format")
    parser.add_argument("--pr", required=True, type=int, help="PR number")
    args = parser.parse_args()

    pr_dir = Path(f".tmp/pr-{args.pr}")
    pr_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching PR #{args.pr} from {args.repo}...")

    metadata = fetch_pr_metadata(args.repo, args.pr)

    if metadata["state"] == "closed" and metadata["merged"]:
        print("WARNING: This PR is already merged. Analysis will be report-only.")
    elif metadata["state"] == "closed":
        print("WARNING: This PR is closed (not merged).")

    (pr_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"  Metadata saved to {pr_dir}/metadata.json")

    diff = fetch_pr_diff(args.repo, args.pr)
    (pr_dir / "diff.patch").write_text(diff)
    print(f"  Diff saved to {pr_dir}/diff.patch ({len(diff)} bytes)")

    changed_files = fetch_changed_files(args.repo, args.pr)
    (pr_dir / "changed_files.json").write_text(json.dumps(changed_files, indent=2))
    print(f"  {len(changed_files)} changed files saved to {pr_dir}/changed_files.json")

    if metadata["head_repo_clone_url"]:
        clone_pr_branch(metadata, pr_dir / "repo")
    else:
        print("  WARNING: Head repo not available (deleted fork?). Skipping clone.")
        print("  Analysis will use diff/patch data only.")

    print(f"\nDone. PR data is in {pr_dir}/")
    print(f"  Title: {metadata['title']}")
    print(f"  Author: {metadata['author']}")
    print(f"  Changes: +{metadata['additions']} -{metadata['deletions']} across {metadata['changed_files_count']} files")


if __name__ == "__main__":
    main()
