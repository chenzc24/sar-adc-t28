"use strict";

// Open the folded record that holds a linked marker, so map and chain links land on visible text.
function revealTarget() {
  const id = decodeURIComponent(location.hash.slice(1));
  const target = id && document.getElementById(id);
  if (!target) return;
  let opened = false;
  for (let node = target; node; node = node.parentElement) {
    if (node.tagName === "DETAILS" && !node.open) {
      node.open = true;
      opened = true;
    }
  }
  if (opened) target.scrollIntoView();
}

window.addEventListener("hashchange", revealTarget);
document.addEventListener("click", (event) => {
  const link = event.target.closest("a");
  if (link && (link.getAttribute("href") || "").startsWith("#")) setTimeout(revealTarget);
});
revealTarget();
