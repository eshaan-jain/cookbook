#!/usr/bin/env python3
"""Apply a tag-change issue (from the edit-tags form) to a recipe file.

Input comes from the ISSUE_BODY environment variable. Only the `tags:` line
of an existing recipe in recipes/ is ever changed.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NO_RESPONSE = "_No response_"


def parse_form(body):
    """Split a GitHub issue-form body into {lowercased label: answer}."""
    fields, current = {}, None
    for line in body.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip().lower()
            fields[current] = []
        elif current is not None:
            fields[current].append(line)
    cleaned = {}
    for key, lines in fields.items():
        text = "\n".join(lines).strip()
        cleaned[key] = "" if text == NO_RESPONSE else text
    return cleaned


def clean_tag(raw):
    tag = re.sub(r"[^a-z0-9 -]", "", raw.lower())
    return re.sub(r"\s+", " ", tag).strip()[:30]


def main():
    form = parse_form(os.environ.get("ISSUE_BODY", ""))
    slug = form.get("recipe (file name)", "").strip()
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        print("Invalid recipe name.", file=sys.stderr)
        sys.exit(1)
    path = ROOT / "recipes" / f"{slug}.md"
    if not path.is_file():
        print(f"No recipe named {slug}.", file=sys.stderr)
        sys.exit(1)

    tags = []
    for raw in form.get("new tags", "").split(","):
        tag = clean_tag(raw)
        if tag and tag not in tags:
            tags.append(tag)
    tags = tags[:12]
    new_line = "tags: [" + ", ".join(tags) + "]"

    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        print("Recipe has no frontmatter.", file=sys.stderr)
        sys.exit(1)
    lines = m.group(1).split("\n")
    for i, line in enumerate(lines):
        if line.startswith("tags:"):
            lines[i] = new_line
            break
    else:
        lines.append(new_line)
    title = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("title:")), slug)
    path.write_text("---\n" + "\n".join(lines) + "\n---\n" + text[m.end():], encoding="utf-8")
    print(f"Updated tags for {slug}: {tags}")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"slug={slug}\n")
            fh.write(f"title={title}\n")


if __name__ == "__main__":
    main()
