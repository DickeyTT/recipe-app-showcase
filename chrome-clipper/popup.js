// Popup controller. After capture, the recipe is filed through a short wizard:
// clip (confirm, with Edit details behind a link) -> collection -> categories ->
// tags -> save. Chips and a single-select list replace the long checkbox forms.
const FOLDER = "RecipeClips";

const el = (id) => document.getElementById(id);
const captureView = el("capture-view");
const wizard = el("wizard");
const status = el("status");
const wBody = el("w-body");
const wStep = el("w-step");
const wTitle = el("w-title");
const wStatus = el("w-status");
const backBtn = el("w-back");
const nextBtn = el("w-next");
const backX = el("w-backx");
const wRt = el("w-rt");
const scrollEl = el("scroll");
const barEl = el("bar");
const footEl = el("foot");

el("w-close").addEventListener("click", () => window.parent.postMessage({ type: "recipeclip-close" }, "*"));

const DEFAULT_NOTEBOOKS = [
  "Asian Cooking", "Bread Baking", "Cooking", "Desserts",
  "Ferment Preserves and Pickles", "Fish Recipes", "Jams and Chutney",
  "Lunches", "Mexican Dishes", "Pasta Dishes", "Pumpkin Recipes", "Salads",
  "Snacks and Dips", "Soups", "Vegetarian Recipes", "Web Clips",
];
let vocab = null;
let captured = null;
let draft = null;
const STEPS = ["clip", "collection", "categories", "tags"];
let view = "clip";

function notebooks() {
  try {
    const saved = JSON.parse(localStorage.getItem("clipNotebooks") || "null");
    if (Array.isArray(saved) && saved.length) return saved;
  } catch { /* ignore */ }
  return DEFAULT_NOTEBOOKS;
}
function persistNotebook(name) {
  try {
    localStorage.setItem("clipNotebook", name);
    const list = notebooks();
    if (!list.includes(name)) { list.push(name); list.sort(); localStorage.setItem("clipNotebooks", JSON.stringify(list)); }
  } catch { /* ignore */ }
}
function lastNotebook() {
  try { return localStorage.getItem("clipNotebook") || "Web Clips"; } catch { return "Web Clips"; }
}
function lastMode() {
  try { return localStorage.getItem("clipMode") === "basic" ? "basic" : "full"; } catch { return "full"; }
}

// The extractor runs in the page and returns the recipe as its last expression.
async function capture() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) throw new Error("No active tab.");
  const [injection] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["lib/extract.js"] });
  return injection?.result ?? null;
}

function buildDraft(recipe) {
  const notesParts = [];
  if (recipe.notes) notesParts.push("## Notes", "", recipe.notes, "");
  if (recipe.body) notesParts.push(recipe.body);
  return {
    title: recipe.title || "",
    ingredients: recipe.ingredients || [],
    steps: recipe.steps || [],
    notes: notesParts.join("\n").trim(),
    bodyImages: recipe.bodyImages || [],
    heroUrl: (recipe.images && recipe.images[0]) || null,
    includeImage: Boolean(recipe.images && recipe.images[0]),
    // Nothing is pre-selected: the user picks the collection, categories and tags
    // each time. (Auto-guessing and remembering the last collection were unwanted.)
    categories: new Set(),
    tags: new Set(),
    notebook: "",
    mode: lastMode(),
    source: recipe.source,
  };
}

const linesOf = (text) => text.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
const TITLES = {
  clip: "Recipe clipped", edit: "Edit details", collection: "Which collection?",
  categories: "Categories", tags: "Tags",
};

function setView(next) {
  view = next;
  const idx = STEPS.indexOf(view === "edit" ? "clip" : view);
  document.querySelectorAll(".seg").forEach((s, n) => s.classList.toggle("on", n <= idx));
  wStep.textContent = view === "edit" ? "Step 1 · details" : `Step ${idx + 1} of 4`;
  wTitle.textContent = TITLES[view];
  wStatus.textContent = "";
  wBody.innerHTML = "";
  RENDER[view]();
  // Always start each step at the top, even if the previous one was scrolled.
  scrollEl.scrollTop = 0;
  if (view === "edit") {
    backX.classList.remove("hidden");
    backBtn.classList.add("hidden");
    nextBtn.textContent = "Done";
    nextBtn.disabled = false;
  } else {
    backX.classList.add("hidden");
    backBtn.classList.toggle("hidden", idx === 0);
    nextBtn.textContent = idx === STEPS.length - 1 ? "Save to library" : "Next";
    nextBtn.disabled = false;
  }
}

const RENDER = {
  clip() {
    const modes = document.createElement("div");
    modes.className = "modes";
    modes.innerHTML =
      `<button data-mode="basic" aria-pressed="${draft.mode === "basic"}">Basic</button>` +
      `<button data-mode="full" aria-pressed="${draft.mode === "full"}">Full</button>`;
    modes.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      draft.mode = b.dataset.mode;
      try { localStorage.setItem("clipMode", draft.mode); } catch { /* ignore */ }
      modes.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.mode === draft.mode)));
    }));
    wBody.appendChild(modes);

    const card = document.createElement("div");
    card.className = "clipcard";
    const photos = (draft.bodyImages || []).length;
    const bits = [`${draft.ingredients.length} ingredients`, `${draft.steps.length} steps`];
    if (draft.includeImage) bits.push("photo");
    card.innerHTML =
      (draft.heroUrl ? `<img class="thumb" src="${draft.heroUrl}" alt="">` : `<div class="thumb"></div>`) +
      `<div><div class="title">${draft.title || "Untitled recipe"}</div><div class="meta">${bits.join(" · ")}</div></div>`;
    wBody.appendChild(card);

    const link = document.createElement("button");
    link.className = "link";
    link.innerHTML = `<span>Edit details<br><span class="d">title, photo, ingredients, method${draft.mode === "full" ? ", notes" : ""}</span></span><span class="chev">›</span>`;
    link.addEventListener("click", () => setView("edit"));
    wBody.appendChild(link);

    if (draft.mode === "full" && photos) {
      const hint = document.createElement("p");
      hint.className = "hint";
      hint.style.marginTop = "10px";
      hint.textContent = `${photos} step photo${photos === 1 ? "" : "s"} included. Trim them under Edit details.`;
      wBody.appendChild(hint);
    }
  },

  edit() {
    const field = (labelText, value, tag, oninput) => {
      const label = document.createElement("label");
      label.className = "f";
      label.textContent = labelText;
      const input = document.createElement(tag);
      input.className = "f-input";
      if (tag === "input") input.type = "text";
      input.value = value;
      input.addEventListener("input", () => oninput(input.value));
      wBody.appendChild(label);
      wBody.appendChild(input);
    };
    field("Title", draft.title, "input", (v) => { draft.title = v; wRt.textContent = v; });

    const photoLabel = document.createElement("label");
    photoLabel.className = "f";
    photoLabel.textContent = "Photo";
    wBody.appendChild(photoLabel);
    const imgrow = document.createElement("div");
    imgrow.className = "imgrow";
    if (draft.heroUrl) {
      imgrow.innerHTML = `<img src="${draft.heroUrl}" alt=""><label><input type="checkbox" ${draft.includeImage ? "checked" : ""}> Include photo</label>`;
      imgrow.querySelector("input").addEventListener("change", (e) => { draft.includeImage = e.target.checked; });
    } else {
      imgrow.innerHTML = `<span class="hint">No photo found on this page.</span>`;
    }
    wBody.appendChild(imgrow);

    field("Ingredients", draft.ingredients.join("\n"), "textarea", (v) => { draft.ingredients = linesOf(v); });
    field("Method", draft.steps.join("\n"), "textarea", (v) => { draft.steps = linesOf(v); });
    if (draft.mode === "full") {
      const l = document.createElement("label"); l.className = "f"; l.textContent = "Notes & extra text";
      wBody.appendChild(l);
      const t = document.createElement("textarea"); t.style.minHeight = "110px"; t.value = draft.notes;
      t.addEventListener("input", () => { draft.notes = t.value; });
      wBody.appendChild(t);
      const h = document.createElement("p"); h.className = "hint"; h.style.marginTop = "6px";
      h.textContent = "Step photos appear as ![[image N]] lines; delete a line to drop one.";
      wBody.appendChild(h);
    }
  },

  collection() {
    const list = document.createElement("div");
    // The collection is just where it's filed; it does not pre-tick categories
    // (those come only from the page text).
    const choose = (name, node) => {
      draft.notebook = name;
      list.querySelectorAll(".row").forEach((r) => r.classList.remove("on"));
      node.classList.add("on");
    };
    notebooks().forEach((name) => {
      const row = document.createElement("div");
      row.className = "row" + (name === draft.notebook ? " on" : "");
      row.innerHTML = `<span class="rc"></span>${name}`;
      row.addEventListener("click", () => choose(name, row));
      list.appendChild(row);
    });
    const newRow = document.createElement("div");
    newRow.className = "row";
    newRow.innerHTML = `<span class="rc"></span>+ New collection`;
    const newInput = document.createElement("input");
    newInput.id = "notebook-new"; newInput.type = "text"; newInput.placeholder = "New collection name";
    newInput.className = "hidden"; newInput.style.marginTop = "2px";
    newRow.addEventListener("click", () => {
      list.querySelectorAll(".row").forEach((r) => r.classList.remove("on"));
      newRow.classList.add("on"); newInput.classList.remove("hidden"); newInput.focus();
      draft.notebook = "";
    });
    newInput.addEventListener("input", () => { draft.notebook = newInput.value.trim(); });
    list.appendChild(newRow);
    wBody.appendChild(list);
    wBody.appendChild(newInput);
  },

  categories() {
    const intro = document.createElement("p");
    intro.className = "hint"; intro.style.margin = "0 0 10px";
    intro.textContent = "Tap the categories for browsing and search.";
    wBody.appendChild(intro);
    if (!vocab) return;
    const sections = [...new Set(vocab.categories.filter((c) => c.section !== "Other").map((c) => c.section))];
    sections.forEach((section) => {
      const g = document.createElement("div"); g.className = "grp"; g.textContent = section;
      wBody.appendChild(g);
      const chips = document.createElement("div"); chips.className = "chips";
      vocab.categories.filter((c) => c.section === section).forEach((c) => {
        const chip = document.createElement("span");
        chip.className = "chip" + (draft.categories.has(c.id) ? " on" : "");
        chip.textContent = c.name;
        chip.addEventListener("click", () => {
          if (draft.categories.has(c.id)) draft.categories.delete(c.id); else draft.categories.add(c.id);
          chip.classList.toggle("on");
        });
        chips.appendChild(chip);
      });
      wBody.appendChild(chips);
    });
  },

  tags() {
    if (!vocab) return;
    const max = vocab.maxTags || 5;
    const intro = document.createElement("p");
    intro.className = "hint"; intro.style.margin = "0 0 10px";
    const counter = document.createElement("span");
    intro.append("Up to five, for search. ", counter);
    wBody.appendChild(intro);
    const chipEls = [];
    const refresh = () => {
      counter.textContent = `${draft.tags.size} of ${max} chosen`;
      chipEls.forEach((c) => c.classList.toggle("dim", draft.tags.size >= max && !draft.tags.has(c.dataset.tag)));
    };
    const groups = [...new Set(vocab.tags.map((t) => t.group))];
    groups.forEach((group) => {
      const g = document.createElement("div"); g.className = "grp"; g.textContent = group;
      wBody.appendChild(g);
      const chips = document.createElement("div"); chips.className = "chips";
      vocab.tags.filter((t) => t.group === group).forEach((t) => {
        const chip = document.createElement("span");
        chip.className = "chip" + (draft.tags.has(t.tag) ? " on" : "");
        chip.dataset.tag = t.tag; chip.textContent = t.tag;
        chip.addEventListener("click", () => {
          if (draft.tags.has(t.tag)) draft.tags.delete(t.tag);
          else { if (draft.tags.size >= max) return; draft.tags.add(t.tag); }
          chip.classList.toggle("on", draft.tags.has(t.tag));
          refresh();
        });
        chips.appendChild(chip); chipEls.push(chip);
      });
      wBody.appendChild(chips);
    });
    refresh();
  },
};

function download(url, path) {
  return chrome.downloads.download({ url, filename: path, conflictAction: "uniquify", saveAs: false });
}

async function save() {
  const full = draft.mode === "full";
  const recipe = {
    ...captured,
    title: draft.title.trim() || "Untitled recipe",
    ingredients: draft.ingredients,
    steps: draft.steps,
    extra: full ? draft.notes.trim() : "",
    categories: [...draft.categories],
    tags: [...draft.tags],
    images: draft.includeImage && draft.heroUrl ? [draft.heroUrl] : [],
  };
  const base = `${clipSlug(recipe.title)}-${clipStamp()}`;
  const dir = `${FOLDER}/${base}`;

  let imageFilename = null;
  if (recipe.images[0]) {
    imageFilename = `${base}.${imageExtension(recipe.images[0])}`;
    await download(recipe.images[0], `${dir}/${imageFilename}`);
  }
  let stepImages = 0;
  if (full) {
    const wanted = (draft.bodyImages || []).filter((im) => recipe.extra.includes(`![[${im.token}]]`));
    for (let i = 0; i < wanted.length; i++) {
      const im = wanted[i];
      const name = `${base}-img-${i + 1}.${imageExtension(im.url)}`;
      await download(im.url, `${dir}/${name}`);
      recipe.extra = recipe.extra.split(`![[${im.token}]]`).join(`![[${name}]]`);
      stepImages++;
    }
  }
  const notebook = draft.notebook || "Web Clips";
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
    setTimeout(() => blobUrls.forEach(URL.revokeObjectURL), 10000);
  }
  persistNotebook(notebook);
  return { base, notebook, savedImage: Boolean(imageFilename), stepImages };
}

// Capture as soon as the panel opens, then go straight into the wizard.
async function init() {
  try {
    const [v, cap] = await Promise.all([loadCatalogueVocab(), capture()]);
    vocab = v;
    captured = cap;
    if (!captured || !captured.ok) {
      status.textContent = "No recipe found on this page. Open a recipe, then click the clipper again.";
      return;
    }
    draft = buildDraft(captured);
    wRt.textContent = draft.title;
    captureView.classList.add("hidden");
    wizard.classList.remove("hidden");
    barEl.classList.remove("hidden");
    footEl.classList.remove("hidden");
    setView("clip");
  } catch (error) {
    status.textContent = `Could not read the page: ${error.message}`;
  }
}
init();

function currentIndex() { return STEPS.indexOf(view === "edit" ? "clip" : view); }
backBtn.addEventListener("click", () => setView(STEPS[currentIndex() - 1]));
backX.addEventListener("click", () => setView("clip"));
nextBtn.addEventListener("click", async () => {
  if (view === "edit") { setView("clip"); return; }
  const idx = currentIndex();
  if (idx < STEPS.length - 1) { setView(STEPS[idx + 1]); return; }
  nextBtn.disabled = true;
  wStatus.textContent = "Saving…";
  try {
    const { base, notebook, savedImage, stepImages } = await save();
    const bits = [savedImage ? "photo" : null, stepImages ? `${stepImages} step photos` : null].filter(Boolean);
    wStatus.textContent = [
      `Saved to ${notebook} (Downloads/${FOLDER}/${base}/).`,
      bits.length ? `With ${bits.join(" and ")}.` : "",
      `Import the ${FOLDER} folder in the Mac app.`,
    ].filter(Boolean).join("\n");
    nextBtn.textContent = "Saved ✓";
  } catch (error) {
    wStatus.textContent = `Could not save: ${error.message}`;
    nextBtn.disabled = false;
  }
});
