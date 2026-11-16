# Our Recipe Book

A recipe book that lives in a GitHub repo and publishes itself as a website.

- `recipes/` — one Markdown file per recipe (this is your data)
- `images/` — photos, named after the recipe (`lemon-bars.jpg`)
- `site.json` — site title, tagline, and your repo name
- `site/` — styles and scripts for the website
- `scripts/build.py` — turns recipes into the website (no dependencies)
- `scripts/apply_tag_edit.py` — applies a tag change from the pencil editor
- `.github/` — the deploy workflow and the tag-edit automation
- `skill/recipe-book/` — your own Claude skill for adding recipes to the repo

## Preview locally

```
python scripts/build.py
python -m http.server -d dist 8000   # then open http://localhost:8000
```

## One-time setup

1. Create a **public** repo on GitHub and push this folder to it.
2. Edit `site.json` and set `"repo": "your-username/your-repo"` so the tag editor works, and `"google_form_url"` to your Google Form's public link so the "+ Add a recipe" button works.
3. Repo **Settings → Pages → Source: GitHub Actions**.
4. Repo **Settings → Actions → General → Workflow permissions**: choose *Read and write permissions* and tick *Allow GitHub Actions to create and approve pull requests*.
5. Push to `main`. After a minute the site is at `https://your-username.github.io/your-repo/`.

## How friends add a recipe

The **+ Add a recipe** button opens a Google Form (link or recipe text, name, notes). It is the only way to add a recipe. Responses land in a Google Sheet; once a week Claude reads new rows, drafts a recipe file for each with the `recipe-book` skill, and opens a pull request. Merging the pull request is the approval.

To change a recipe's tags, use the pencil icon on its page; that opens a pull request too (`scripts/apply_tag_edit.py`).

## Adding a recipe yourself

Drop a new `.md` file in `recipes/` (copy an existing one) and push. Or use the `recipe-book` Claude skill and just give it the text, link or a photo of the recipe.
