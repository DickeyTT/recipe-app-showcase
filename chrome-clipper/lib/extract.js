// Recipe extraction, run inside the page. Prefers schema.org/Recipe JSON-LD,
// which most recipe sites publish, and falls back to a DOM heuristic otherwise.
// Defines a global the popup calls via chrome.scripting; returns a plain object.
(() => {
  const absolute = (url) => {
    if (!url) return null;
    try {
      return new URL(url, document.baseURI).href;
    } catch {
      return null;
    }
  };

  const clean = (value) =>
    typeof value === "string"
      ? value.replace(/\s+/g, " ").trim()
      : "";

  // JSON-LD values are maddeningly varied: strings, arrays, nested objects.
  const asArray = (value) =>
    value == null ? [] : Array.isArray(value) ? value : [value];

  const typeMatches = (node, wanted) =>
    asArray(node && node["@type"]).some(
      (t) => typeof t === "string" && t.toLowerCase() === wanted
    );

  // Walk JSON-LD, including @graph containers, collecting every node.
  const flattenNodes = (root) => {
    const out = [];
    const visit = (node) => {
      if (Array.isArray(node)) {
        node.forEach(visit);
      } else if (node && typeof node === "object") {
        out.push(node);
        if (node["@graph"]) visit(node["@graph"]);
      }
    };
    visit(root);
    return out;
  };

  const findRecipeNode = () => {
    const scripts = document.querySelectorAll(
      'script[type="application/ld+json"]'
    );
    for (const script of scripts) {
      let parsed;
      try {
        parsed = JSON.parse(script.textContent);
      } catch {
        continue;
      }
      const node = flattenNodes(parsed).find((n) => typeMatches(n, "recipe"));
      if (node) return node;
    }
    return null;
  };

  const imagesFrom = (image) => {
    const urls = [];
    for (const item of asArray(image)) {
      if (typeof item === "string") urls.push(item);
      else if (item && typeof item === "object") {
        if (typeof item.url === "string") urls.push(item.url);
        else if (Array.isArray(item.url)) urls.push(...item.url);
      }
    }
    return urls.map(absolute).filter(Boolean);
  };

  const authorFrom = (author) =>
    asArray(author)
      .map((a) => (typeof a === "string" ? a : clean(a && a.name)))
      .filter(Boolean)
      .join(", ");

  // recipeInstructions can be a string, an array of strings, HowToStep objects,
  // or HowToSection objects that themselves hold a list of steps.
  const stepsFrom = (instructions) => {
    const steps = [];
    const pushText = (value) => {
      const text = clean(value);
      if (text) steps.push(text);
    };
    const handle = (item) => {
      if (typeof item === "string") {
        // A single block of text may hold several sentences or newlines.
        item
          .split(/\r?\n+/)
          .map(clean)
          .filter(Boolean)
          .forEach((line) => steps.push(line));
      } else if (item && typeof item === "object") {
        if (typeMatches(item, "howtosection") || item.itemListElement) {
          asArray(item.itemListElement).forEach(handle);
        } else {
          pushText(item.text || item.name);
        }
      }
    };
    asArray(instructions).forEach(handle);
    return steps;
  };

  const fromJsonLd = (node) => ({
    ok: true,
    source: "json-ld",
    title: clean(node.name),
    description: clean(node.description),
    ingredients: asArray(node.recipeIngredient || node.ingredients)
      .map(clean)
      .filter(Boolean),
    steps: stepsFrom(node.recipeInstructions),
    images: imagesFrom(node.image),
    author: authorFrom(node.author),
    datePublished: clean(node.datePublished),
    recipeYield: asArray(node.recipeYield).map(clean).filter(Boolean).join(", "),
    times: {
      prep: clean(node.prepTime),
      cook: clean(node.cookTime),
      total: clean(node.totalTime),
    },
    cuisine: asArray(node.recipeCuisine).map(clean).filter(Boolean),
    category: asArray(node.recipeCategory).map(clean).filter(Boolean),
    // keywords may be a comma-joined string or an array; diet is schema.org URLs.
    keywords: asArray(node.keywords)
      .flatMap((k) => String(k).split(","))
      .map(clean)
      .filter(Boolean),
    diet: asArray(node.suitableForDiet)
      .map((d) => clean(String(d).split(/[/#]/).pop()).replace(/Diet$/i, ""))
      .filter(Boolean),
    url: document.location.href,
  });

  // Heuristic fallback for pages without JSON-LD. Deliberately modest: it finds a
  // title, likely ingredient list items and likely step paragraphs, and the main
  // image, so the clip is editable in the preview rather than perfect.
  const fromHeuristic = () => {
    const title =
      clean(document.querySelector("h1")?.textContent) ||
      clean(document.title);

    const collectList = (selectors) => {
      for (const selector of selectors) {
        const nodes = Array.from(document.querySelectorAll(selector));
        const items = nodes
          .map((n) => clean(n.textContent))
          .filter((t) => t.length > 1);
        if (items.length) return items;
      }
      return [];
    };

    const ingredients = collectList([
      '[class*="ingredient" i] li',
      '[id*="ingredient" i] li',
      'ul[class*="ingredient" i] li',
    ]);

    const steps = collectList([
      '[class*="instruction" i] li',
      '[class*="method" i] li',
      '[class*="direction" i] li',
      '[class*="instruction" i] p',
    ]);

    const ogImage = document
      .querySelector('meta[property="og:image"]')
      ?.getAttribute("content");
    const firstImage = document.querySelector("article img, main img, img")?.src;
    const images = [ogImage, firstImage].map(absolute).filter(Boolean);

    return {
      ok: Boolean(title && (ingredients.length || steps.length)),
      source: "heuristic",
      title,
      description: clean(
        document
          .querySelector('meta[name="description"]')
          ?.getAttribute("content")
      ),
      ingredients,
      steps,
      images: images.slice(0, 1),
      author: "",
      datePublished: "",
      recipeYield: "",
      times: { prep: "", cook: "", total: "" },
      cuisine: [],
      category: [],
      url: document.location.href,
    };
  };

  // The recipe card holds the structured facts; the real extra value is the
  // article prose around it (intro, tips, storing, FAQs, serving). Capture that
  // as Markdown, with boilerplate removed, plus the recipe card's own notes.
  // Images are kept (Full mode uses the step photos); the recipe card, nav, ads,
  // related posts, comments and social widgets are removed.
  const JUNK = [
    "script", "style", "noscript", "iframe", "form", "nav", "aside", "button",
    ".tasty-recipes", ".wprm-recipe-container",
    '[class*="recipe-card"]', '[class*="related"]', '[class*="newsletter"]',
    '[class*="subscribe"]', '[class*="comment"]', '[class*="feedback"]',
    '[class*="social"]', '[class*="share"]', '[class*="jump-"]',
    '[class*="adthrive"]', '[class*="wp-block-latest"]', '[class*="toc"]',
    // Roundup / "you might also like" post-listing widgets (headings + images).
    '[class*="post-summary"]', '[class*="post-listing"]',
    '[id*="comment"]',
  ].join(",");

  // Trailing calls to action, and paragraphs that are mostly links (nav/promo).
  const CTA = /love this recipe|leave a (comment|rating|review|star)|rate (this|the) recipe|please let us know|[★⭐]/i;
  const isPromoParagraph = (el, text) => {
    if (CTA.test(text)) return true;
    const anchors = el.querySelectorAll("a");
    if (!anchors.length) return false;
    const linkLen = [...anchors].reduce((n, a) => n + clean(a.innerText).length, 0);
    return linkLen / Math.max(1, text.length) >= 0.5;
  };

  // Headings at which the article has moved on to promotion, not the recipe.
  const END_HEADING = /^(more\b.*recipes?|related\b|you.?ll also love|reader interactions|comments|primary sidebar|footer)/i;

  // Builds the article Markdown and collects its images. Each image becomes a
  // removable line `![[image N]]` in place, mapped to its URL for Full-mode save.
  const articleMarkdown = (container) => {
    const clone = container.cloneNode(true);
    clone.querySelectorAll(JUNK).forEach((n) => n.remove());

    const out = [];
    const images = [];
    const seen = new Set();
    let stopped = false;
    let skipList = false; // suppress a Table of Contents list after its heading

    const addImage = (img) => {
      if (!img || images.length >= 30) return;
      const src =
        img.currentSrc ||
        img.getAttribute("src") ||
        img.getAttribute("data-src") ||
        img.getAttribute("data-lazy-src") ||
        "";
      const abs = absolute(src);
      if (!abs || abs.startsWith("data:") || /\.svg($|\?)/i.test(abs)) return;
      if (seen.has(abs)) return;
      seen.add(abs);
      const token = `image ${images.length + 1}`;
      images.push({ token, url: abs, caption: clean(img.getAttribute("alt")) });
      out.push(`![[${token}]]`, "");
    };

    const walk = (node) => {
      for (const child of node.children) {
        if (stopped) return;
        const tag = child.tagName.toLowerCase();
        if (tag === "img") {
          addImage(child);
          continue;
        }
        if (tag === "figure") {
          addImage(child.querySelector("img"));
          const caption = clean(child.querySelector("figcaption")?.innerText);
          if (caption) out.push(`*${caption}*`, "");
          continue;
        }
        const text = clean(child.innerText);
        if (!text) {
          // An element with no text may still wrap an image (div/a/p around img).
          if (child.querySelector) addImage(child.querySelector("img"));
          continue;
        }
        if (/^h[2-4]$/.test(tag)) {
          if (END_HEADING.test(text)) {
            stopped = true;
            return;
          }
          if (text.toLowerCase() === "table of contents") {
            skipList = true;
            continue;
          }
          skipList = false;
          // A heading that is only a link is a card/nav title, not a section.
          const link = child.querySelector("a");
          if (link && clean(link.innerText) === text) continue;
          const prefix = tag === "h2" ? "## " : tag === "h3" ? "### " : "#### ";
          out.push("", prefix + text, "");
        } else if (tag === "p") {
          if (isPromoParagraph(child, text)) continue;
          out.push(text, "");
        } else if (tag === "ul" || tag === "ol") {
          if (skipList) {
            skipList = false;
            continue;
          }
          [...child.querySelectorAll(":scope > li")].forEach((li, i) => {
            const t = clean(li.innerText);
            if (t) out.push((tag === "ol" ? `${i + 1}. ` : "- ") + t);
          });
          out.push("");
        } else if (tag === "blockquote") {
          out.push(`> ${text}`, "");
        } else {
          walk(child);
        }
      }
    };
    walk(clone);
    const body = out.join("\n").replace(/\n{3,}/g, "\n\n").trim().slice(0, 12000);
    // Drop images whose line fell past the 12k cap so the map stays accurate.
    const kept = images.filter((im) => body.includes(`![[${im.token}]]`));
    return { body, bodyImages: kept };
  };

  const extractArticle = () => {
    const container = [
      ".entry-content", ".post-content", '[itemprop="articleBody"]',
      "article .post", "main article", "article",
    ]
      .map((s) => document.querySelector(s))
      .find((el) => el && el.innerText && el.innerText.length > 200);

    const notesEl = document.querySelector(
      ".tasty-recipes-notes, .wprm-recipe-notes, .mv-create-notes"
    );
    const notes = clean(notesEl ? notesEl.innerText : "").replace(/^notes[:\s]*/i, "");

    const article = container ? articleMarkdown(container) : { body: "", bodyImages: [] };
    return { body: article.body, bodyImages: article.bodyImages, notes };
  };

  const node = findRecipeNode();
  const result = node ? fromJsonLd(node) : fromHeuristic();
  Object.assign(result, extractArticle());
  // De-duplicate images while preserving order.
  result.images = [...new Set(result.images)];
  return result;
})();
