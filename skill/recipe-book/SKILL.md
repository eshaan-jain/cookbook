---
name: recipe-book
description: Add recipes to the user's GitHub-hosted recipe book (from text, a URL, a screenshot or a photo of a recipe card), and rebuild or preview the recipe website. Use when the user wants to save, add, clean up or publish a recipe.
---

# Recipe book

The recipe book is a git repo. Recipes are Markdown files in `recipes/`, photos live in `images/`, and `python scripts/build.py` turns them into a static site in `dist/`. Pushing to `main` deploys it to GitHub Pages.

## Adding a recipe

1. Get the recipe from whatever the user gives you: pasted text, a URL (fetch the page), a screenshot, or a photo of a handwritten card (read the image).
2. Write `recipes/<slug>.md`. The slug is the title in lowercase with hyphens, e.g. `lemon-bars`. Use exactly this format:

```
---
title: Lemon Bars
description: One sentence that makes you want to cook it.
servings: 12
prep_time: 15 min
cook_time: 35 min
tags: [dessert, baking]
author: Name            # optional, shown as "From Name"
source: https://...     # optional, link to the original
source_name: Site name  # optional
image: images/lemon-bars.jpg   # always include
---

## Ingredients

### Fridge

- 1 cup butter
- 2 eggs

### Pantry

- 2 cups flour
- 1 tsp vanilla extract

### Counter

- 2 ripe bananas

## Steps

1. First step.
2. Second step.

## Notes

Tips, substitutions, storage.
```

Rules:
- `servings` is a plain number, because the site scales quantities from it. Put the amount first on every ingredient line ("2 cups flour"). Write amounts as numbers or fractions (1 ½, 3/4).
- Group ingredients by where they live in the kitchen, with `### ` headings in this order, skipping any that would be empty: `### Fridge`, `### Freezer`, `### Pantry`, `### Counter`. Fridge: eggs, dairy and plant milks, fresh meat and fish, fresh herbs, bell peppers, cucumbers, ginger, opened sauces like mayo. Freezer: anything the source says is frozen. Pantry: dry goods, oils, vinegars, canned goods, spices, sweeteners, soy sauce, broth, rice, oats. Counter: bananas, onions, garlic, potatoes, tomatoes, avocados, citrus. Keep each line's amount and wording as written, and mark optional extras with "(optional)" instead of making a separate toppings group. Put an item where most people keep it and don't agonize over edge cases.
- Tags are lowercase, 2 to 5 per recipe, and reuse existing tags where they fit (check other files in `recipes/`).
- Ingredient lists are fine to copy as facts. For recipes from websites, rewrite the steps and notes in your own words, set `source`, and never copy their photos. Ask the user for their own photo instead.
- For the user's own or a friend's recipe, keep their wording and voice. Fix only obvious typos.
- Don't invent quantities or times that the source doesn't give. Leave a field out instead, and tell the user what was missing.

3. Always include the `image:` line, set to `images/<slug>.jpg`, even when there is no photo yet. The site shows a placeholder until a file with that name is added to `images/`, and the owner uploads it later. Never leave the line out and never point it at a source site's photo.
   If the user supplies a photo, resize it to at most 1400px on the long side, save it as `images/<slug>.jpg` (JPEG, quality about 82) and set `image:`.
4. Run `python scripts/build.py`. Fix any error it reports (it names the bad file).
5. Show the user the new recipe page (open `dist/recipes/<slug>/index.html`) before committing.
6. Commit with a message like `Add recipe: Lemon Bars` and push if the user wants it live.

## Reviewing a friend's submission

Friends submit through the "Submit a recipe" issue form. A GitHub Action opens a pull request with a draft file. When asked to review one, check that the quantities and steps make sense, tidy the tags, and fix wording. Don't merge unless the user says so. Regroup the ingredients by kitchen location if the submission lists them in one flat list.

## Changing the look

Edit `site/style.css` (colors are variables at the top), `site.json` (title, tagline, footer, `repo` as `owner/name`) or the templates in `scripts/build.py`.
