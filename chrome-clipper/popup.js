// Popup entry point. Step 4: capture, then show an editable preview (title,
// image, ingredients, method). Save builds the Markdown bundle from the edited
// fields and writes it to ~/Downloads/RecipeClips/.
const FOLDER = "RecipeClips";

const el = (id) => document.getElementById(id);
const captureView = el("capture-view");
const previewView = el("preview-view");
const clipBtn = el("clip");
const status = el("status");
const titleInput = el("title");
const imageRow = el("image-row");
const imagePreview = el("image-preview");
const includeImage = el("include-image");
const ingredientsTa = el("ingredients");
const methodTa = el("method");
const extraTa = el("extra");
const extraSection = el("extra-section");
const imagesHint = el("images-hint");
const modeHint = el("mode-hint");
const modeBasicBtn = el("mode-basic");
const modeFullBtn = el("mode-full");
const notebookSel = el("notebook");
const notebookNew = el("notebook-new");
const categoriesBox = el("categories-box");
const tagsBox = el("tags-box");
const tagsCount = el("tags-count");
const viaLine = el("via");

// The user's notebooks, seeded once and editable; remembered between clips.
const DEFAULT_NOTEBOOKS = [
  "Asian Cooking", "Bread Baking", "Cooking", "Desserts",
  "Ferment Preserves and Pickles", "Fish Recipes", "Jams and Chutney",
  "Lunches", "Mexican Dishes", "Pasta Dishes", "Pumpkin Recipes", "Salads",
  "Snacks and Dips", "Soups", "Vegetarian Recipes", "Web Clips",
];
// A notebook's default category, mirroring the app, pre-ticked on selection.
const NOTEBOOK_CATEGORIES = {
  "Asian Cooking": ["asian"], "Bread Baking": ["bread-baking"], "Cooking": ["meat"],
  "Desserts": ["desserts"], "Ferment Preserves and Pickles": ["ferments-pickles"],
  "Fish Recipes": ["fish"], "Jams and Chutney": ["jams-chutneys"],
  "Lunches": ["lunches-light-meals"], "Mexican Dishes": ["mexican"],
  "Pasta Dishes": ["pasta-noodles"], "Salads": ["salads"],
  "Snacks and Dips": ["starters-snacks", "sauces-dips-condiments"], "Soups": ["soups"],
  "Vegetarian Recipes": ["vegetarian"],
};

let vocab = null;
loadCatalogueVocab().then((v) => {
  vocab = v;
  renderCategories();
  renderTags();
});
const backBtn = el("back");
const saveBtn = el("save");
const saveStatus = el("save-status");

// The recipe as captured; editable fields are read back from the form on save.
let captured = null;

// Basic = title, hero, ingredients, method. Full also saves notes, prose and the
// step photos. The last choice is remembered; first run defaults to Full.
let mode = "full";
try {
  mode = localStorage.getItem("clipMode") === "basic" ? "basic" : "full";
} catch {
  /* private window: keep the default */
}

const linesOf = (text) =>
  text.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);

function applyMode() {
  const full = mode === "full";
  modeFullBtn.setAttribute("aria-pressed", String(full));
  modeBasicBtn.setAttribute("aria-pressed", String(!full));
  extraSection.classList.toggle("hidden", !full);
  modeHint.textContent = full
    ? "Full: notes, page text and step photos included."
    : "Basic: title, image, ingredients and method only.";
  try {
    localStorage.setItem("clipMode", mode);
  } catch {
    /* ignore */
  }
}

function setMode(next) {
  mode = next;
  applyMode();
}

function notebooks() {
  try {
    const saved = JSON.parse(localStorage.getItem("clipNotebooks") || "null");
    if (Array.isArray(saved) && saved.length) return saved;
  } catch {
    /* ignore */
  }
  return DEFAULT_NOTEBOOKS;
}

function renderNotebooks() {
  let last = "Web Clips";
  try {
    last = localStorage.getItem("clipNotebook") || last;
  } catch {
    /* ignore */
  }
  const options = notebooks()
    .map((n) => `<option${n === last ? " selected" : ""}>${n}</option>`)
    .join("");
  notebookSel.innerHTML = `${options}<option value="__new__">New…</option>`;
  notebookNew.classList.add("hidden");
}

function renderCategories() {
  if (!vocab) return;
  let section = "";
  categoriesBox.innerHTML = vocab.categories
    .map((c) => {
      const header = c.section !== section ? ((section = c.section), `<div class="section">${c.section}</div>`) : "";
      const child = c.parentId ? " child" : "";
      return `${header}<label class="cat${child}"><input type="checkbox" value="${c.id}" /> ${c.name}</label>`;
    })
    .join("");
}

function renderTags() {
  if (!vocab) return;
  let group = "";
  tagsBox.innerHTML = vocab.tags
    .map((t) => {
      const header = t.group !== group ? ((group = t.group), `<div class="section">${t.group}</div>`) : "";
      return `${header}<label><input type="checkbox" value="${t.tag}" /> ${t.tag}</label>`;
    })
    .join("");
  tagsBox.addEventListener("change", enforceTagLimit);
}

const checkedValues = (box) =>
  [...box.querySelectorAll("input:checked")].map((i) => i.value);

function enforceTagLimit() {
  const max = (vocab && vocab.maxTags) || 5;
  const checked = checkedValues(tagsBox);
  if (checked.length >= max) {
    tagsBox.querySelectorAll("input:not(:checked)").forEach((i) => (i.disabled = true));
  } else {
    tagsBox.querySelectorAll("input").forEach((i) => (i.disabled = false));
  }
  tagsCount.textContent = `${checked.length} of ${max} chosen`;
}

function tickValues(box, values) {
  const set = new Set(values);
  box.querySelectorAll("input").forEach((i) => (i.checked = set.has(i.value)));
}

// Merge the notebook's default category into the current ticks (does not untick).
function applyNotebookDefault() {
  const defaults = NOTEBOOK_CATEGORIES[notebookSel.value] || [];
  defaults.forEach((id) => {
    const box = categoriesBox.querySelector(`input[value="${id}"]`);
    if (box) box.checked = true;
  });
}

// The extractor runs in the page and returns the recipe as its last expression.
async function capture() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) throw new Error("No active tab.");
  const [injection] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ["lib/extract.js"],
  });
  return injection?.result ?? null;
}

function showPreview(recipe) {
  captured = recipe;
  titleInput.value = recipe.title || "";
  ingredientsTa.value = recipe.ingredients.join("\n");
  methodTa.value = recipe.steps.join("\n");

  // Pre-fill the extra box with the card's notes then the article prose
  // (which already contains the removable `![[image N]]` lines).
  const extraParts = [];
  if (recipe.notes) extraParts.push("## Notes", "", recipe.notes, "");
  if (recipe.body) extraParts.push(recipe.body);
  extraTa.value = extraParts.join("\n").trim();

  const count = (recipe.bodyImages || []).length;
  imagesHint.textContent = count
    ? `${count} step photo${count === 1 ? "" : "s"} in the text as ![[image N]] lines. Delete a line to drop that photo.`
    : "No step photos found on this page.";

  // Notebook, categories and tags, pre-filled from the page for confirmation.
  renderNotebooks();
  const suggestion = vocab
    ? suggestCatalogue(recipe, vocab)
    : { categoryIds: [], tags: [], cuisine: "" };
  tickValues(categoriesBox, suggestion.categoryIds);
  applyNotebookDefault();
  tickValues(tagsBox, suggestion.tags);
  enforceTagLimit();
  applyMode();

  const hero = recipe.images && recipe.images[0];
  if (hero) {
    imagePreview.src = hero;
    includeImage.checked = true;
    imageRow.classList.remove("hidden");
  } else {
    imageRow.classList.add("hidden");
  }

  viaLine.textContent =
    recipe.source === "json-ld"
      ? "Read from the page's structured data."
      : "Read by page heuristic, so check it over.";
  saveStatus.textContent = "";
  captureView.classList.add("hidden");
  previewView.classList.remove("hidden");
}

function showCapture() {
  previewView.classList.add("hidden");
  captureView.classList.remove("hidden");
}

// chrome.downloads saves relative to the Downloads folder; the path is the full
// sub-path. uniquify avoids clobbering, saveAs stays off for one click.
function download(url, path) {
  return chrome.downloads.download({
    url,
    filename: path,
    conflictAction: "uniquify",
    saveAs: false,
  });
}

// Reassemble the recipe from the edited fields, then write images + Markdown.
async function save() {
  const full = mode === "full";
  // Notebook: the dropdown choice, or a typed new name; remembered for next time.
  let notebook = notebookSel.value;
  if (notebook === "__new__") notebook = notebookNew.value.trim() || "Web Clips";
  try {
    localStorage.setItem("clipNotebook", notebook);
    const list = notebooks();
    if (!list.includes(notebook)) {
      list.push(notebook);
      list.sort();
      localStorage.setItem("clipNotebooks", JSON.stringify(list));
    }
  } catch {
    /* ignore */
  }

  const recipe = {
    ...captured,
    title: titleInput.value.trim() || "Untitled recipe",
    ingredients: linesOf(ingredientsTa.value),
    steps: linesOf(methodTa.value),
    extra: full ? extraTa.value.trim() : "",
    categories: checkedValues(categoriesBox),
    tags: checkedValues(tagsBox),
    images:
      includeImage.checked && captured.images && captured.images[0]
        ? [captured.images[0]]
        : [],
  };

  const base = `${clipSlug(recipe.title)}-${clipStamp()}`;
  // Each recipe gets its own folder; files inside reference each other by name.
  const dir = `${FOLDER}/${base}`;

  let imageFilename = null;
  if (recipe.images[0]) {
    imageFilename = `${base}.${imageExtension(recipe.images[0])}`;
    await download(recipe.images[0], `${dir}/${imageFilename}`);
  }

  // Full mode: download each step photo whose `![[image N]]` line was kept, and
  // rewrite that line to the local filename so it displays offline.
  let stepImages = 0;
  if (full) {
    const wanted = (captured.bodyImages || []).filter((im) =>
      recipe.extra.includes(`![[${im.token}]]`)
    );
    for (let i = 0; i < wanted.length; i++) {
      const im = wanted[i];
      const name = `${base}-img-${i + 1}.${imageExtension(im.url)}`;
      await download(im.url, `${dir}/${name}`);
      recipe.extra = recipe.extra.split(`![[${im.token}]]`).join(`![[${name}]]`);
      stepImages++;
    }
  }

  // Markdown, sidecar and a notebook-labels file (so the folder imports under one
  // "Web Clips" collection instead of a notebook named after the recipe).
  const blobUrls = [];
  const writeText = (text, type, name) => {
    const url = URL.createObjectURL(new Blob([text], { type }));
    blobUrls.push(url);
    return download(url, `${dir}/${name}`);
  };
  try {
    await writeText(buildMarkdown(recipe, imageFilename), "text/markdown", `${base}.md`);
    await writeText(buildSidecar(recipe), "application/json", `${base}.catalogue.json`);
    await writeText(JSON.stringify({ [base]: notebook }), "application/json", "notebook-labels.json");
  } finally {
    // Give the downloads time to read the blobs before the popup revokes them.
    setTimeout(() => blobUrls.forEach(URL.revokeObjectURL), 10000);
  }
  return { base, savedImage: Boolean(imageFilename), stepImages, recipe };
}

clipBtn.addEventListener("click", async () => {
  clipBtn.disabled = true;
  status.textContent = "Reading the page…";
  try {
    const recipe = await capture();
    if (!recipe || !recipe.ok) {
      status.textContent =
        "Could not find a recipe on this page. Try a recipe page.";
      return;
    }
    showPreview(recipe);
  } catch (error) {
    status.textContent = `Could not read the page: ${error.message}`;
  } finally {
    clipBtn.disabled = false;
  }
});

backBtn.addEventListener("click", showCapture);
modeBasicBtn.addEventListener("click", () => setMode("basic"));
modeFullBtn.addEventListener("click", () => setMode("full"));
notebookSel.addEventListener("change", () => {
  notebookNew.classList.toggle("hidden", notebookSel.value !== "__new__");
  if (notebookSel.value !== "__new__") applyNotebookDefault();
});

saveBtn.addEventListener("click", async () => {
  saveBtn.disabled = true;
  backBtn.disabled = true;
  saveStatus.textContent = "Saving…";
  try {
    const { base, savedImage, stepImages } = await save();
    const bits = [savedImage ? "hero image" : null, stepImages ? `${stepImages} step photo${stepImages === 1 ? "" : "s"}` : null].filter(Boolean);
    saveStatus.textContent = [
      `Saved ${mode} clip to Downloads/${FOLDER}/${base}/`,
      bits.length ? `With ${bits.join(" and ")}.` : "No images.",
      `Import the ${FOLDER} folder in the Mac app.`,
    ].join("\n");
  } catch (error) {
    saveStatus.textContent = `Could not save: ${error.message}`;
  } finally {
    saveBtn.disabled = false;
    backBtn.disabled = false;
  }
});
