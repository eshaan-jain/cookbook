# Our Recipe Book

A recipe book that lives in a GitHub repo and publishes itself as a website.

- `recipes/` — one Markdown file per recipe (this is your data)
- `images/` — photos, named after the recipe (`lemon-bars.jpg`)
- `site.json` — site title, tagline, and your repo name
- `site/` — styles and scripts for the website
- `scripts/build.py` — turns recipes into the website (no dependencies)
- `scripts/issue_to_recipe.py` — turns a friend's form submission into a recipe file
- `.github/` — the submission form and the automation
- `skill/recipe-book/` — a Claude skill for adding recipes from text, links and photos

## Preview locally

```
python scripts/build.py
python -m http.server -d dist 8000   # then open http://localhost:8000
```

## One-time setup

1. Create a **public** repo on GitHub and push this folder to it.
2. Edit `site.json` and set `"repo": "your-username/your-repo"` so the "+ Add a recipe" button works.
3. Repo **Settings → Pages → Source: GitHub Actions**.
4. Repo **Settings → Actions → General → Workflow permissions**: choose *Read and write permissions* and tick *Allow GitHub Actions to create and approve pull requests*.
5. Push to `main`. After a minute the site is at `https://your-username.github.io/your-repo/`.

## How friends add a recipe

They open the site, click **+ Add a recipe**, fill in the form (photo can be dragged in), and submit. A pull request appears for you to review. Merge it and the recipe is live.

## Adding a recipe yourself

Drop a new `.md` file in `recipes/` (copy an existing one) and push. Or use the `recipe-book` Claude skill and just give it the text, link or a photo of the recipe.
