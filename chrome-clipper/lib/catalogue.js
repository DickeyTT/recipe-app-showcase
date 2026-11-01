// Loads the bundled category and tag lists (synced from the app) and maps a
// captured recipe's own category, cuisine, keywords, diet and time to the app's
// controlled category ids and tags. Rules only, no network or AI; the preview
// shows the result ticked for the user to adjust. Plain globals.

// Phrases in the page's category/cuisine/keywords that imply a category id.
// First match per phrase wins; a recipe can gather several ids.
const CATEGORY_PHRASES = [
  // Cuisine
  ["korean", "korean"], ["japanese", "japanese"], ["chinese", "chinese"],
  ["thai", "thai"], ["vietnamese", "vietnamese"], ["indian", "indian"],
  ["asian", "asian"], ["mexican", "mexican"], ["italian", "italian"],
  ["french", "french"], ["spanish", "spanish-portuguese"],
  ["portuguese", "spanish-portuguese"], ["greek", "greek"],
  ["middle eastern", "middle-eastern"], ["moroccan", "north-african"],
  ["north african", "north-african"], ["caribbean", "caribbean"],
  ["latin", "latin-american"], ["british", "british"],
  // Main ingredient
  ["seafood", "fish"], ["fish", "fish"], ["salmon", "fish"], ["prawn", "fish"],
  ["shrimp", "fish"], ["beef", "meat"], ["pork", "meat"], ["lamb", "meat"],
  ["chicken", "meat"], ["poultry", "meat"], ["vegan", "vegetarian"],
  ["vegetarian", "vegetarian"],
  // Type of dish
  ["breakfast", "breakfast-brunch"], ["brunch", "breakfast-brunch"],
  ["appetizer", "starters-snacks"], ["appetiser", "starters-snacks"],
  ["starter", "starters-snacks"], ["snack", "starters-snacks"],
  ["soup", "soups"], ["salad", "salads"], ["pasta", "pasta-noodles"],
  ["noodle", "pasta-noodles"], ["risotto", "rice-grains"], ["rice", "rice-grains"],
  ["grain", "rice-grains"], ["curry", "curries-stews"], ["stew", "curries-stews"],
  ["casserole", "curries-stews"], ["pickle", "ferments-pickles"],
  ["ferment", "ferments-pickles"], ["kimchi", "ferments-pickles"],
  ["jam", "jams-chutneys"], ["chutney", "jams-chutneys"],
  ["marmalade", "jams-chutneys"], ["sauce", "sauces-dips-condiments"],
  ["dip", "sauces-dips-condiments"], ["condiment", "sauces-dips-condiments"],
  ["dressing", "sauces-dips-condiments"], ["dessert", "desserts"],
  ["cake", "desserts"], ["cookie", "desserts"], ["pudding", "desserts"],
  ["drink", "drinks"], ["cocktail", "drinks"], ["beverage", "drinks"],
  ["smoothie", "drinks"], ["bread", "bread-baking"], ["side dish", "sides"],
  ["main course", "main-dishes"], ["main dish", "main-dishes"],
  ["dinner", "main-dishes"], ["entree", "main-dishes"], ["entrée", "main-dishes"],
  ["lunch", "lunches-light-meals"],
];

async function loadCatalogueVocab() {
  const read = async (name) => {
    try {
      const res = await fetch(chrome.runtime.getURL(`vocab/${name}.json`));
      return await res.json();
    } catch {
      return null;
    }
  };
  const cat = await read("categories");
  const tag = await read("tags");

  const categories = [];
  for (const section of (cat && cat.sections) || []) {
    for (const c of section.categories || []) {
      categories.push({ id: c.id, name: c.name, section: section.name, parentId: null });
      for (const ch of c.children || []) {
        categories.push({ id: ch.id, name: ch.name, section: section.name, parentId: c.id });
      }
    }
  }

  // Canonical tag lookup: the tag itself and each alias map to the tag.
  const tagCanonical = {};
  const tags = [];
  for (const group of (tag && tag.groups) || []) {
    for (const t of group.tags || []) {
      tags.push({ tag: t.tag, group: group.name });
      tagCanonical[t.tag] = t.tag;
      for (const a of t.aliases || []) tagCanonical[a] = t.tag;
    }
  }
  const maxTags = (tag && tag.maxTagsPerRecipe) || 5;
  return { categories, tags, tagCanonical, maxTags };
}

// Normalise a phrase the way the app does for tags: lowercase, hyphen-joined.
function normaliseTag(text) {
  return String(text || "")
    .toLowerCase()
    .trim()
    .replace(/[#]/g, "")
    .split(/\s+/)
    .filter(Boolean)
    .join("-");
}

function parseMinutes(iso) {
  const m = /^P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?/.exec(iso || "");
  if (!m) return null;
  return (parseInt(m[1] || "0", 10) * 60) + parseInt(m[2] || "0", 10);
}

// Suggest category ids and tags from the captured recipe's own metadata.
function suggestCatalogue(recipe, vocab) {
  const phrases = []
    .concat(recipe.category || [])
    .concat(recipe.cuisine || [])
    .concat(recipe.diet || [])
    .concat(recipe.keywords || [])
    .map((s) => String(s).toLowerCase());
  const haystack = phrases.join(" | ");

  const categoryIds = new Set();
  for (const [phrase, id] of CATEGORY_PHRASES) {
    if (haystack.includes(phrase)) categoryIds.add(id);
  }

  const tags = [];
  const addTag = (name) => {
    const canonical = vocab.tagCanonical[name] || vocab.tagCanonical[normaliseTag(name)];
    if (canonical && !tags.includes(canonical) && tags.length < vocab.maxTags) {
      tags.push(canonical);
    }
  };
  const minutes = parseMinutes(recipe.times && recipe.times.total);
  if (minutes && minutes > 0 && minutes <= 30) addTag("quick");
  for (const phrase of phrases) {
    addTag(phrase);
    addTag(normaliseTag(phrase));
  }

  const cuisine =
    (recipe.cuisine && recipe.cuisine[0]) ||
    "";
  return { categoryIds: [...categoryIds], tags, cuisine };
}
