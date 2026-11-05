// Injects the clipper as a floating panel (an isolated iframe) pinned to the top
// right of the page, and toggles it. Re-injection is safe: the toggle is stashed
// on window so a second click reuses the existing instance.
(() => {
  if (window.__recipeClipToggle) { window.__recipeClipToggle(); return; }

  const ID = "recipeapp-clipper-panel";
  const panel = () => document.getElementById(ID);

  const open = () => {
    if (panel()) return;
    const frame = document.createElement("iframe");
    frame.id = ID;
    frame.src = chrome.runtime.getURL("popup.html");
    frame.setAttribute("allow", "clipboard-read; clipboard-write");
    Object.assign(frame.style, {
      position: "fixed", top: "16px", right: "16px",
      width: "368px", height: "min(760px, calc(100vh - 32px))",
      border: "0", borderRadius: "16px",
      boxShadow: "0 12px 44px rgba(40,30,20,0.20), 0 2px 10px rgba(40,30,20,0.10)",
      zIndex: "2147483647", colorScheme: "light", background: "transparent",
    });
    document.documentElement.appendChild(frame);
  };
  const close = () => { const p = panel(); if (p) p.remove(); };
  const toggle = () => (panel() ? close() : open());

  window.__recipeClipToggle = toggle;
  chrome.runtime.onMessage.addListener((m) => { if (m.type === "recipeclip-toggle") toggle(); });
  // The panel asks to close itself through the header ✕.
  window.addEventListener("message", (e) => { if (e.data && e.data.type === "recipeclip-close") close(); });

  open();
})();
