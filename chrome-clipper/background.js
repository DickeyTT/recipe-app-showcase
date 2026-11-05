// Toolbar icon toggles the floating panel on the current page. The panel is a
// content-script iframe (content.js), not a toolbar popup, so it floats on the
// right of the window like a proper side panel.
chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id) return;
  try {
    // Already injected: ask the existing instance to toggle.
    await chrome.tabs.sendMessage(tab.id, { type: "recipeclip-toggle" });
  } catch {
    // Not injected yet: inject it, which opens the panel.
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
  }
});
