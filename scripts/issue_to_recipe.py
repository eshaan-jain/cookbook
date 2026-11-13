#!/usr/bin/env python3
"""Turn a GitHub issue-form submission into recipes/<slug>.md (+ images/<slug>.jpg).

Inputs come from environment variables, never from shell interpolation:
    ISSUE_BODY, ISSUE_NUMBER, ISSUE_AUTHOR
Requires Pillow for photo resizing (pip install pillow).
"""
import io
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NO_RESPONSE = "_No response_"

# Only fetch photos that GitHub itself hosts for issue attachments.
ALLOWED_PHOTO = re.compile(
    r"https://(?:github\.com/user-attachments/(?:assets|files)/[\w./-]+"
    r"|user-images\.githubusercontent\.com/[\w./-]+"
    r"|private-user-images\.githubusercontent\.com/[\w./?=&%-]+)"
)


def parse_form(body):
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


def one_line(value, limit=300):
    value = re.sub(r"\s+", " ", value).strip()
    value = value.replace("---", "-").lstrip("[").rstrip("]")
    return value[:limit]


def slugify(title):
    slug = re.sub(r"[^a-z0-9]+", "-", re.sub(r"['’`]", "", title.lower())).strip("-")
    return slug[:60] or "recipe"


def list_lines(text, numbered=False):
    out = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^(?:[-*•]\s+|\d+[.)]\s+)", "", line)
        out.append(line)
    if numbered:
        return [f"{i}. {line}" for i, line in enumerate(out, 1)]
    return [f"- {line}" for line in out]


def fetch_photo(text, dest):
    m = re.search(r'(?:!\[[^\]]*\]\(|src=")?(https://[^\s)"\']+)', text)
    if not m:
        return False
    url = m.group(1)
    if not ALLOWED_PHOTO.match(url):
        print(f"skipping photo from untrusted host: {url}", file=sys.stderr)
        return False
    try:
        from PIL import Image, ImageOps

        req = urllib.request.Request(url, headers={"User-Agent": "recipe-book-bot"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read(15 * 1024 * 1024)
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        img.thumbnail((1400, 1400))
        dest.parent.mkdir(exist_ok=True)
        img.save(dest, "JPEG", quality=82, optimize=True)
        return True
    except Exception as exc:  # a missing photo shouldn't block the recipe
        print(f"could not process photo: {exc}", file=sys.stderr)
        return False


def main():
    form = parse_form(os.environ.get("ISSUE_BODY", ""))
    title = one_line(form.get("recipe name", ""), 120)
    if not title:
        print("No recipe name found in the issue.", file=sys.stderr)
        sys.exit(1)

    recipes = ROOT / "recipes"
    recipes.mkdir(exist_ok=True)
    base = slugify(title)
    slug, n = base, 2
    while (recipes / f"{slug}.md").exists():
        slug, n = f"{base}-{n}", n + 1

    servings = re.match(r"\d+", form.get("servings", ""))
    tags = [one_line(t, 30).lower() for t in form.get("tags", "").split(",") if t.strip()][:8]
    author = one_line(form.get("your name", "")) or os.environ.get("ISSUE_AUTHOR", "")
    source = one_line(form.get("original source link (if you adapted it from a website)", ""), 500)
    if source and not source.startswith(("http://", "https://")):
        source = ""

    has_photo = fetch_photo(form.get("photo", ""), ROOT / "images" / f"{slug}.jpg")

    front = ["---", f"title: {title}"]
    if form.get("short description"):
        front.append(f"description: {one_line(form['short description'])}")
    if servings:
        front.append(f"servings: {servings.group()}")
    if form.get("prep time"):
        front.append(f"prep_time: {one_line(form['prep time'], 40)}")
    if form.get("cook time"):
        front.append(f"cook_time: {one_line(form['cook time'], 40)}")
    if tags:
        front.append("tags: [" + ", ".join(t.replace(",", "") for t in tags) + "]")
    if author:
        front.append(f"author: {one_line(author, 60)}")
    if source:
        front.append(f"source: {source}")
    if has_photo:
        front.append(f"image: images/{slug}.jpg")
    front.append("---")

    notes = form.get("notes", "").replace("\r", "").strip()
    body = ["", "## Ingredients", ""] + list_lines(form.get("ingredients", ""))
    body += ["", "## Steps", ""] + list_lines(form.get("steps", ""), numbered=True)
    if notes:
        body += ["", "## Notes", "", notes]

    (recipes / f"{slug}.md").write_text("\n".join(front + body) + "\n", encoding="utf-8")
    print(f"Wrote recipes/{slug}.md")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"slug={slug}\n")
            fh.write(f"title={title}\n")


if __name__ == "__main__":
    main()
