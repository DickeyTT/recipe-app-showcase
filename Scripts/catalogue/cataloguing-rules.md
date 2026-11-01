# Cataloguing rules

These rules are bundled into every work batch by `catalogue_export.py prepare` and checked by `catalogue_export.py validate`. The tool reads the section between the next heading and "Mac app changes:", so keep both markers.

### 4.1 AI cataloguing before import

Purpose: the exported notebooks are inconsistent, so recipes need a proper catalogue before import. AI is used only for cataloguing. It must not rewrite recipe text or extract quantities.

Design:

- A standalone tool, `Scripts/catalogue/catalogue_export.py`, run manually on the Mac before import. It is not part of the app.
- Input: a copy of the export folder (the script refuses to write inside the protected source export path).
- **No paid API calls.** The tool makes no network requests at all. An AI coding assistant reads the batches and writes the sidecars directly:
  1. `catalogue_export.py prepare` copies the export and writes work batches (about 10 recipes each) to `working/catalogue/<notebook>/batches/`, each containing the recipe text (images excluded), the rules in this section, `categories.json` and `tags.json`.
  2. The assistant reads each batch and writes one `.catalogue.json` sidecar per recipe, following the rules. Work one notebook at a time and record progress, so the job can be stopped and resumed.
  3. `catalogue_export.py validate` checks every sidecar against the schema, the category and tag lists and the limits, drops anything invalid with a note, and writes `catalogue-report.csv`.
- The assistant must stop and ask if it is about to use any API key or paid service.
- Output: one sidecar file per recipe, `<recipe name>.catalogue.json`, next to the copied Markdown, plus a `catalogue-report.csv` summary. Schema:

```json
{
  "schemaVersion": 1,
  "sourceFile": "Fish Recipes/Baked_piri-piri_Cod.md",
  "isRecipe": true,
  "cleanTitle": "Baked piri-piri cod",
  "categories": ["spanish-portuguese", "fish", "main-dishes"],
  "cuisine": "spanish-portuguese",
  "mainIngredient": "cod",
  "ingredients": ["cod", "red pepper", "garlic", "lemon", "olive oil", "chilli"],
  "tags": ["#weeknight", "#traybake"],
  "likelyDuplicateOf": null,
  "confidence": 0.86,
  "notes": "Optional short reason when uncertain"
}
```

- `ingredients` holds canonical ingredient names only: no quantities, no units, singular, lower case, British names (aubergine, courgette, coriander, prawn).
- Categories come from the fixed list in `Scripts/catalogue/categories.json`. Choose only ids from this file and never invent categories.
- A recipe has **several categories**: normally one cuisine (if clear), one main ingredient (fish, meat or vegetarian, if clear) and one or more dish types. Example: a Thai fish curry is `thai`, `fish`, `curries-stews`.
- `cuisine` in the sidecar repeats the single best cuisine id (or `null`); `mainIngredient` stays a free canonical ingredient name such as `cod`.
- Groups: `asian` is a group containing korean, japanese, chinese, thai, vietnamese and indian. Store only the child id. The app treats the parent as implied, so a Korean recipe also appears under Asian, and `category:asian` finds all six.
- If a recipe is Asian but not one of the six child cuisines (for example Sri Lankan), use `asian` itself. Do not add more countries.

Rules added after a pilot review:

- **Dish types:** at most two per recipe, most specific first. Use `main-dishes` only when no more specific dish type fits (in the pilot it was on 70 of 97 recipes, which made it useless as a filter).
- **Vegetarian:** only if the recipe as written contains no meat, poultry, fish or seafood, and none of fish sauce, shrimp paste, dried shrimp, anchovy stock, oyster sauce or meat stock. Kimchi counts as vegetarian, but fish sauce, shrimp and so on elsewhere in the recipe still make it not vegetarian. A recipe that is easily made vegetarian is not `vegetarian`; give it the `veggie-option` tag instead. If unsure, omit the main-ingredient category and lower the confidence.
- **Main ingredient field:** the principal protein or vegetable the dish is built around (for example `cod`, `chicken thigh`, `aubergine`), never a sauce base, oil, spice or seasoning (not `coconut milk`, `chilli flakes`, `gochujang`). Leave empty for sauces and condiments.
- **Tags:** choose only from `Scripts/catalogue/tags.json`, at most 5 per recipe. Tags never name ingredients, cuisines, categories or websites (the pilot produced 241 different tags). Map aliases to the canonical tag, for example `one-pan` to `one-pot`. Free tags can still be added by hand in the app.
- **veggie-option:** only when the recipe itself gives a vegetarian or vegan version or substitution. Do not add it just because a substitution is possible.
- **Titles:** `cleanTitle` is the recipe name only. Never put status into the title (not "Incomplete Clipping"); put that in `notes` and set `isRecipe` or a low confidence instead.
- **Main ingredient with meat or fish:** if the recipe is in `meat` or `fish`, the main ingredient is that meat or fish (Kimchi Mandu is `pork`, not `tofu`).
- Validate every sidecar: drop unknown category ids and tags, enforce the limits, and log what was dropped in the `notes` column.
- Category names may be edited in the file; ids must stay stable.
- `isRecipe: false` flags notes that are not recipes; these are imported but shown separately.
- The process must be resumable (skip recipes that already have a valid sidecar), log failures and never stop the whole run because of one bad file.
- Before a full run, process one notebook as a pilot and review the CSV.

Mac app changes: not part of the cataloguing rules.
