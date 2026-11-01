// Turns a captured recipe into the Markdown bundle the RecipeApp importer reads:
// YAML front matter (source url, created at), an H1 title, then Ingredients and
// Method as bullets and numbered steps. The hero image is referenced by a local
// relative path so it displays offline. Plain globals, loaded before popup.js.

// A filesystem-safe base name shared by the .md and its image.
function clipSlug(title) {
  const base = (title || "recipe")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 60)
    .replace(/^-|-$/g, "");
  return base || "recipe";
}

// A compact YYYYMMDDHHMM stamp keeps repeated clips from colliding in the folder.
function clipStamp(date = new Date()) {
  const p = (n) => String(n).padStart(2, "0");
  return (
    date.getFullYear() +
    p(date.getMonth() + 1) +
    p(date.getDate()) +
    p(date.getHours()) +
    p(date.getMinutes())
  );
}

function imageExtension(url) {
  try {
    const path = new URL(url).pathname.toLowerCase();
    const match = path.match(/\.(jpe?g|png|heic|webp|gif)$/);
    if (match) return match[1] === "jpeg" ? "jpg" : match[1];
  } catch {
    /* fall through */
  }
  return "jpg";
}

// ISO 8601 durations (PT20M, PT1H30M) made readable; anything else passes through.
function humaniseDuration(value) {
  if (!value) return "";
  const match = /^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?/.exec(value);
  if (!match) return value;
  const [, d, h, m] = match;
  const parts = [];
  if (d) parts.push(`${d} day${d === "1" ? "" : "s"}`);
  if (h) parts.push(`${h} hr`);
  if (m) parts.push(`${m} min`);
  return parts.join(" ");
}

function isoDate(value) {
  const date = value ? new Date(value) : new Date();
  if (isNaN(date.getTime())) return clipStamp().slice(0, 8).replace(/(\d{4})(\d{2})(\d{2})/, "$1-$2-$3");
  const p = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}`;
}

// Builds the Markdown text. imageFilename, when given, is embedded as a local ref.
function buildMarkdown(recipe, imageFilename) {
  const lines = [];
  lines.push("---");
  lines.push(`source url: ${recipe.url || ""}`);
  lines.push(`created at: ${isoDate(recipe.datePublished)}`);
  lines.push("---");
  lines.push("");
  lines.push(`# ${recipe.title || "Untitled recipe"}`);
  lines.push("");

  if (imageFilename) {
    lines.push(`![[${imageFilename}]]`);
    lines.push("");
  }

  if (recipe.description) {
    lines.push(recipe.description);
    lines.push("");
  }

  const meta = [];
  if (recipe.recipeYield) meta.push(`Serves: ${recipe.recipeYield}`);
  const prep = humaniseDuration(recipe.times && recipe.times.prep);
  const cook = humaniseDuration(recipe.times && recipe.times.cook);
  const total = humaniseDuration(recipe.times && recipe.times.total);
  if (prep) meta.push(`Prep: ${prep}`);
  if (cook) meta.push(`Cook: ${cook}`);
  if (total && !prep && !cook) meta.push(`Total: ${total}`);
  if (meta.length) {
    lines.push(meta.join(" · "));
    lines.push("");
  }

  if (recipe.ingredients && recipe.ingredients.length) {
    lines.push("## Ingredients");
    lines.push("");
    recipe.ingredients.forEach((item) => lines.push(`- ${item}`));
    lines.push("");
  }

  if (recipe.steps && recipe.steps.length) {
    lines.push("## Method");
    lines.push("");
    recipe.steps.forEach((step, i) => lines.push(`${i + 1}. ${step}`));
    lines.push("");
  }

  // The edited "extra text" box carries notes, tips, FAQs and the page prose.
  // It is already Markdown (it may hold its own ## headings), so append as-is.
  const extra = (recipe.extra || "").trim();
  if (extra) {
    lines.push(extra);
    lines.push("");
  }

  lines.push("## Source");
  lines.push("");
  if (recipe.author) lines.push(`By ${recipe.author}`);
  lines.push(recipe.url || "");
  lines.push("");

  return lines.join("\n");
}

// A minimal catalogue sidecar. confidence 0 puts the clip in the Mac app's
// Needs review list (categories and tags need a controlled vocabulary the
// clipper does not have), while carrying ingredients and cuisine so ingredient
// search works straight away. isRecipe true, since the user chose to clip it.
function buildSidecar(recipe) {
  // confidence 0 flags the clip for review; once categories are chosen in the
  // preview the clip counts as catalogued, so it skips Needs review.
  const categories = recipe.categories || [];
  const sidecar = { isRecipe: true, confidence: categories.length ? 1 : 0 };
  if (categories.length) sidecar.categories = categories;
  if (recipe.tags && recipe.tags.length) sidecar.tags = recipe.tags;
  if (recipe.ingredients && recipe.ingredients.length) {
    sidecar.ingredients = recipe.ingredients;
  }
  if (recipe.cuisine) {
    sidecar.cuisine = Array.isArray(recipe.cuisine) ? recipe.cuisine[0] : recipe.cuisine;
  }
  if (recipe.url) sidecar.notes = `Clipped from ${recipe.url}`;
  return JSON.stringify(sidecar, null, 2);
}
