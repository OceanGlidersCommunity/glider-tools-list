#!/usr/bin/env python3
"""Update README's "last update" column for GitHub-linked tools, from each
repo's most recent push. Dry run by default; pass --write to apply."""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime

README = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
ROW_RE = re.compile(r"^\[[^\]]+\]\(https?://github\.com/([^/\s]+)/([^/\s#?]+)[^)]*\)\s*\|")


def fetch_pushed_at(owner, repo, token=None):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "glider-tools-list-update-script",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    return datetime.strptime(data["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%B %Y")


def process(lines, token=None):
    updated, failed = [], []
    for i, line in enumerate(lines):
        m = ROW_RE.match(line)
        if not m:
            continue
        owner, repo = m.groups()
        cols = line.split("|")
        try:
            new_text = fetch_pushed_at(owner, repo, token=token)
        except Exception as e:
            failed.append((f"{owner}/{repo}", str(e)))
            continue
        old_text = cols[2].strip()
        if old_text != new_text:
            cols[2] = f" {new_text} "
            lines[i] = "|".join(cols)
            updated.append((f"{owner}/{repo}", old_text, new_text))
    return updated, failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Rewrite README.md in place")
    parser.add_argument("--file", default=README)
    args = parser.parse_args()

    with open(args.file) as f:
        lines = f.readlines()

    updated, failed = process(lines, token=os.environ.get("GITHUB_TOKEN"))

    print(f"checked {len(updated) + len(failed)} GitHub-linked rows: {len(updated)} updated, {len(failed)} failed\n")
    for repo, old, new in updated:
        print(f"  {repo}: '{old}' -> '{new}'")
    for repo, err in failed:
        print(f"  FAILED {repo}: {err}")

    if args.write and updated:
        with open(args.file, "w") as f:
            f.writelines(lines)
        print(f"\nwrote {len(updated)} change(s) to {args.file}")
    elif not args.write:
        print("\ndry run only, pass --write to apply")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
