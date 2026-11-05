# RecipeApp Clipper (Chrome)

A Chrome extension that captures the recipe on the current web page and saves it
as a Markdown-plus-images bundle that the RecipeApp Mac app imports as-is.

## How it works

- Reads the page's schema.org/Recipe **structured data** (title, ingredients,
  method, image, source URL, times). If a site has none, it falls back to a
  rougher page scan, which is why there is an editable preview before saving.
- Has two modes, chosen in the preview (your last choice is remembered):
  - **Basic**: title, hero image, ingredients and method only.
  - **Full**: also the card **notes**, the **article prose** (intro, tips,
    storing, FAQs, serving) and the **step/process photos**, each placed in the
    text where it appears in the how-to. These land in an editable
    "Notes & extra text" box; step photos show as removable `![[image N]]` lines,
    so deleting a line drops that photo. Boilerplate (recipe card, related posts,
    comments, ads) is stripped.
- Writes each clip to its own folder `~/Downloads/RecipeClips/<name>/`:
  - `<name>.md` — the recipe in the app's Markdown format
  - `<name>.jpg` (or .png/.webp) — the hero image, downloaded locally
  - `<name>.catalogue.json` — a small sidecar
  - in Full mode, `<name>-img-1.jpg`, `-img-2.jpg` … — the step photos
  - `notebook-labels.json` — maps the folder to the collection
- In the preview you choose the **notebook** (collection), and confirm the
  **categories** and **tags** (pre-filled from the page, mapped to the app's fixed
  lists). These drive browsing and search, so a clip is findable straight away.
  The chosen notebook is written into `notebook-labels.json`, which the importer
  honours instead of naming the collection after the folder.
- If you pick at least one category the clip counts as catalogued and skips
  **Needs review**; otherwise it still lands there.
- Images are local and referenced by relative path, so they display offline. The
  app never fetches remote image URLs.
- The sidecar sets `confidence: 0`, so clips land in the Mac app's **Needs review**
  list for categories and tags to be added. Ingredients and cuisine carry across,
  so ingredient search works straight away.

Nothing calls a paid API. Full cataloguing (categories, tags) stays a manual step
in the Mac app, by design.

## Load it in Chrome (unpacked, for personal use)

1. Open `chrome://extensions`.
2. Turn on **Developer mode** (top right).
3. Click **Load unpacked** and choose this `chrome-clipper/` folder.
4. The RecipeApp Clipper icon appears in the toolbar. Pin it if you like.

Tip: in Chrome Settings ▸ Downloads, turn **off** "Ask where to save each file",
or each clip prompts three times (one per file).

## Clip a recipe

1. On a recipe page, click the clipper icon. A panel opens on the right of the
   window (click the icon again, or the ✕, to close it). Click **Clip this recipe**.
2. A short four-step flow opens:
   - **Recipe clipped** — a confirmation with the title, counts and photo, plus a
     **Basic / Full** choice. Everything editable (title, photo, ingredients,
     method, notes with step photos) is behind **Edit details ›**.
   - **Which notebook?** — tap one collection, or add a new one.
   - **Categories** — tap chips; the page's best guesses are pre-ticked.
   - **Tags** — tap chips, up to five.
3. Click **Save to library**. The files land in `~/Downloads/RecipeClips/<name>/`.
   Full mode saves more files (one per step photo), so leaving "Ask where to save
   each file" off really helps.

Basic saves the title, photo, ingredients and method; Full adds the notes, page
prose and step photos.

## Import into the Mac app

1. In the Mac app: **File ▸ Import**, choose `~/Downloads/RecipeClips` (or a single
   recipe's folder).
2. Each recipe appears in the notebook you chose, with its categories and tags, so
   search and filters find it. If you left all categories unticked, it appears in
   **Needs review** instead.
3. Review anything in Needs review, then mark it reviewed.

## Keeping the category and tag lists in sync

The clipper's `vocab/categories.json` and `vocab/tags.json` are copies of the app's
canonical lists in `Scripts/catalogue/`. `Scripts/build-mac.sh` refreshes them on
every Mac build (or run `Scripts/sync-clipper-vocab.sh` by hand), so the clipper
always offers the same categories and tags as the app.

Re-importing the same folder is safe: already-imported clips are skipped by
content fingerprint.

## Tested

`Tests/RecipeCoreTests/ClipperImportTests.swift` imports a bundle shaped exactly
as this extension produces and checks it comes through as a recipe, with its
image, in the RecipeClips collection, flagged for review.
