"use strict";

const frame = document.querySelector('iframe[name="rnl-frame"]');
const viewerOrigin = new URL(frame.src).origin;
let loaded = false;

window.addEventListener("message", event => {
  if (event.origin !== viewerOrigin || event.source !== frame.contentWindow || event.data?.rnl !== 1) return;
  if (event.data.type === "loaded") loaded = true;
});

document.querySelector(".schematic-links").addEventListener("click", event => {
  const link = event.target.closest("a[data-level]");
  if (!loaded || !link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  frame.contentWindow.postMessage({ rnl: 1, type: "level", name: link.dataset.level }, viewerOrigin);
});
