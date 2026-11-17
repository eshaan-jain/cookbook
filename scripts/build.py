#!/usr/bin/env python3
"""Build the static recipe site from recipes/*.md into dist/.

Standard library only, so it runs anywhere with Python 3.9+:
    python scripts/build.py
"""
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECIPES = ROOT / "recipes"
IMAGES = ROOT / "images"
SITE = ROOT / "site"
DIST = ROOT / "dist"
# Changes whenever a site file changes, so browsers never keep serving stale CSS/JS.
ASSET_VERSION = hashlib.md5(b"".join(
    f.read_bytes() for f in sorted(SITE.glob("*")) if f.suffix in (".css", ".js")
)).hexdigest()[:8]

# Soft gradient pairs for recipes that don't have a photo yet.
GRADIENTS = [
    ("#f4c9a8", "#e59a76"),
    ("#cfdcc0", "#9db38a"),
    ("#f1dfa6", "#e3b857"),
    ("#e8c3c3", "#d08f8f"),
    ("#c8d6e2", "#93acc4"),
    ("#dccbe0", "#b399bb"),
]


# ---------- parsing ----------

def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("missing --- frontmatter block")
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key.strip()] = [v.strip().strip("\"'") for v in value[1:-1].split(",") if v.strip()]
        else:
            meta[key.strip()] = value.strip("\"'")
    return meta, m.group(2)


def parse_sections(body):
    sections, current = {}, None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def parse_ingredients(lines):
    groups = [{"heading": None, "items": []}]
    for line in lines:
        s = line.strip()
        if s.startswith("### "):
            groups.append({"heading": s[4:].strip(), "items": []})
        elif s.startswith(("- ", "* ")):
            groups[-1]["items"].append(s[2:].strip())
    return [g for g in groups if g["items"]]


def parse_steps(lines):
    steps = []
    for line in lines:
        m = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if m:
            steps.append(m.group(1).strip())
        elif line.strip() and steps and line.startswith((" ", "\t")):
            steps[-1] += " " + line.strip()
    return steps


def inline(text):
    """Escape HTML, then support **bold**, *italic* and [links](https://...)."""
    s = html.escape(text, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" rel="noopener">\1</a>', s)
    return s


def notes_html(lines):
    out, para, bullets = [], [], []

    def flush():
        nonlocal para, bullets
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
        if bullets:
            out.append("<ul>" + "".join(f"<li>{inline(b)}</li>" for b in bullets) + "</ul>")
        para, bullets = [], []

    for line in lines:
        s = line.strip()
        if not s:
            flush()
        elif s.startswith(("- ", "* ")):
            if para:
                flush()
            bullets.append(s[2:].strip())
        else:
            if bullets:
                flush()
            para.append(s)
    flush()
    return "\n".join(out)


def load_recipe(path):
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    if not meta.get("title"):
        raise ValueError("missing title")
    sections = parse_sections(body)
    ingredients = parse_ingredients(sections.get("ingredients", []))
    steps = parse_steps(sections.get("steps", []))
    if not ingredients or not steps:
        raise ValueError("needs both an Ingredients and a Steps section")
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    servings = re.match(r"\d+", str(meta.get("servings", "")))
    return {
        "slug": path.stem,
        "title": meta["title"],
        "description": meta.get("description", ""),
        "servings": int(servings.group()) if servings else None,
        "prep_time": meta.get("prep_time", ""),
        "cook_time": meta.get("cook_time", ""),
        "tags": [t.lower() for t in tags],
        "source": meta.get("source", ""),
        "source_name": meta.get("source_name", ""),
        "author": meta.get("author", ""),
        "image": meta.get("image", ""),
        "ingredients": ingredients,
        "steps": steps,
        "notes": notes_html(sections.get("notes", [])),
    }


# ---------- rendering ----------

def esc(s):
    return html.escape(str(s), quote=True)


def gradient_for(slug):
    idx = int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(GRADIENTS)
    a, b = GRADIENTS[idx]
    return f"linear-gradient(135deg, {a}, {b})"


def media(recipe, prefix, cls):
    img = recipe["image"]
    if img and (ROOT / img).exists():
        return f'<img class="{cls}" src="{prefix}{esc(img)}" alt="{esc(recipe["title"])}" loading="lazy">'
    initial = esc(recipe["title"][:1].upper())
    return (f'<div class="{cls} placeholder" style="background:{gradient_for(recipe["slug"])}" '
            f'aria-hidden="true"><span>{initial}</span></div>')


def time_summary(r):
    parts = []
    if r["prep_time"]:
        parts.append(f'Prep {esc(r["prep_time"])}')
    if r["cook_time"]:
        parts.append(f'Cook {esc(r["cook_time"])}')
    return " · ".join(parts)


def head(config, title, prefix, description=""):
    desc = f'<meta name="description" content="{esc(description)}">' if description else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
{desc}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}style.css?v={ASSET_VERSION}">
</head>"""


def header(config, prefix):
    form_url = config.get("google_form_url", "").strip()
    add = ""
    if form_url:
        add = f'<a class="btn" href="{esc(form_url)}" target="_blank" rel="noopener">+ Add a recipe</a>'
    return f"""<header class="site-header">
  <a class="brand" href="{prefix or './'}">{esc(config.get("title", "Recipe Book"))}</a>
  {add}
</header>"""


def group_tags(config, all_tags):
    """Return [(label, [tags])] following site.json's tag_groups; leftovers go to "Other"."""
    configured = config.get("tag_groups") or {}
    if not configured:
        return [("", list(all_tags))]
    groups, used = [], set()
    for label, members in configured.items():
        present = [t for t in members if t in all_tags]
        used.update(present)
        if present:
            groups.append((label, present))
    leftovers = [t for t in all_tags if t not in used]
    if leftovers:
        groups.append(("Other", leftovers))
    return groups


def render_index(config, recipes):
    all_tags = sorted({t for r in recipes for t in r["tags"]})
    chips = ""
    for label, tags_in_group in group_tags(config, all_tags):
        buttons = "".join(f'<button class="chip" data-tag="{esc(t)}">{esc(t)}</button>' for t in tags_in_group)
        name = f'<span class="chip-label">{esc(label)}</span>' if label else ""
        chips += f'<div class="chip-group">{name}<div class="chip-row">{buttons}</div></div>'
    cards = []
    for r in recipes:
        search = " ".join([r["title"], r["description"], " ".join(r["tags"]),
                           " ".join(i for g in r["ingredients"] for i in g["items"])]).lower()
        tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in r["tags"][:3])
        cards.append(f"""<a class="card" href="recipes/{esc(r['slug'])}/" data-tags="{esc('|'.join(r['tags']))}" data-search="{esc(search)}">
  {media(r, "", "card-media")}
  <div class="card-body">
    <h2>{esc(r['title'])}</h2>
    <p>{esc(r['description'])}</p>
    <div class="card-meta">{time_summary(r)}</div>
    <div class="tags">{tags}</div>
  </div>
</a>""")
    return f"""{head(config, config.get("title", "Recipe Book"), "", config.get("tagline", ""))}
<body>
{header(config, "")}
<main class="wrap">
  <section class="hero">
    <h1>{esc(config.get("title", "Recipe Book"))}</h1>
    <p>{esc(config.get("tagline", ""))}</p>
    <input id="search" type="search" placeholder="Search recipes or ingredients…" aria-label="Search recipes">
    <div class="chips" id="chips">{chips}</div>
  </section>
  <p class="count" id="count">{len(recipes)} recipes</p>
  <div class="grid" id="grid">
{chr(10).join(cards)}
  </div>
  <p class="empty" id="empty" hidden>No matches. Try a different word or clear the filter.</p>
</main>
<footer class="site-footer">{esc(config.get("footer", ""))}</footer>
<script src="index.js?v={ASSET_VERSION}"></script>
</body>
</html>"""


def render_recipe(config, r, all_tags):
    prefix = "../../"
    groups = ""
    for g in r["ingredients"]:
        if g["heading"]:
            groups += f'<h3>{esc(g["heading"])}</h3>'
        groups += "<ul class=\"ingredients\">" + "".join(
            f'<li data-raw="{esc(i)}">{inline(i)}</li>' for i in g["items"]) + "</ul>"
    steps = "".join(f"<li>{inline(s)}</li>" for s in r["steps"])
    tags = "".join(f'<a class="tag" href="{prefix}?tag={esc(t)}">{esc(t)}</a>' for t in r["tags"])
    credit = []
    if r["author"]:
        credit.append(f'From {esc(r["author"])}')
    if r["source"]:
        label = esc(r["source_name"] or r["source"])
        credit.append(f'Adapted from <a href="{esc(r["source"])}" rel="noopener">{label}</a>')
    servings_ctl = ""
    if r["servings"]:
        servings_ctl = f"""<div class="servings" data-base="{r['servings']}">
      <span>Servings</span>
      <button type="button" id="minus" aria-label="Fewer servings">−</button>
      <output id="servings-out">{r['servings']}</output>
      <button type="button" id="plus" aria-label="More servings">+</button>
    </div>"""
    notes = f'<section class="notes"><h2>Notes</h2>{r["notes"]}</section>' if r["notes"] else ""
    tag_data = json.dumps({
        "slug": r["slug"],
        "title": r["title"],
        "repo": config.get("repo", "").strip(),
        "tags": r["tags"],
        "allTags": all_tags,
    }).replace("</", "<\\/")
    return f"""{head(config, r['title'] + " · " + config.get("title", "Recipe Book"), prefix, r['description'])}
<body class="recipe-page">
{header(config, prefix)}
<main class="wrap narrow">
  <a class="back" href="{prefix}">← All recipes</a>
  {media(r, prefix, "hero-media")}
  <h1>{esc(r['title'])}</h1>
  <p class="lede">{esc(r['description'])}</p>
  <div class="meta-row">
    <span>{time_summary(r)}</span>
    <div class="tag-area">
      <div class="tags" id="tag-list">{tags}</div>
      <button type="button" class="icon-btn" id="edit-tags" aria-label="Edit tags" title="Edit tags">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
      </button>
    </div>
  </div>
  <div class="tag-editor" id="tag-editor" hidden></div>
  <p class="tag-notice" id="tag-notice" role="status" hidden></p>
  <script type="application/json" id="tag-data">{tag_data}</script>
  <div class="toolbar">
    {servings_ctl}
    <span class="tip">
      <button type="button" class="btn ghost" id="cook-mode" aria-pressed="false" aria-describedby="cook-tip">Cook mode</button>
      <span class="tip-text" id="cook-tip" role="tooltip">Keeps your screen awake and hides everything except the ingredients and steps, so you can cook without tapping your phone with messy hands.</span>
    </span>
  </div>
  <div class="columns">
    <section class="ingredients-col">
      <h2>Ingredients</h2>
      {groups}
    </section>
    <section class="steps-col">
      <h2>Steps</h2>
      <ol class="steps">{steps}</ol>
    </section>
  </div>
  {notes}
  <p class="credit">{" · ".join(credit)}</p>
</main>
<script src="{prefix}recipe.js?v={ASSET_VERSION}"></script>
</body>
</html>"""


# ---------- main ----------

def main():
    config = {}
    cfg_path = ROOT / "site.json"
    if cfg_path.exists():
        config = json.loads(cfg_path.read_text(encoding="utf-8"))

    recipes, errors = [], []
    for path in sorted(RECIPES.glob("*.md")):
        try:
            recipes.append(load_recipe(path))
        except Exception as exc:  # report every broken file, not just the first
            errors.append(f"{path.name}: {exc}")
    if errors:
        print("Could not build. Fix these recipe files:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    recipes.sort(key=lambda r: r["title"].lower())

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for asset in SITE.iterdir():
        shutil.copy(asset, DIST / asset.name)
    if IMAGES.exists():
        shutil.copytree(IMAGES, DIST / "images")
    (DIST / ".nojekyll").write_text("")

    (DIST / "index.html").write_text(render_index(config, recipes), encoding="utf-8")
    all_tags = sorted({t for r in recipes for t in r["tags"]})
    for r in recipes:
        out = DIST / "recipes" / r["slug"]
        out.mkdir(parents=True)
        (out / "index.html").write_text(render_recipe(config, r, all_tags), encoding="utf-8")
        if r["image"] and not (ROOT / r["image"]).exists():
            print(f"note: {r['slug']} points at {r['image']} which doesn't exist yet (using a placeholder)")

    print(f"Built {len(recipes)} recipes into {DIST}")


if __name__ == "__main__":
    main()
