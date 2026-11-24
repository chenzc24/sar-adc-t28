"use strict";

const movedPage = document.querySelector("#moved-page");
if (movedPage) {
  const target = new URL(movedPage.href);
  target.hash = location.hash || target.hash;
  location.replace(target.href);
}

const switcher = document.querySelector("#language-switch");
if (switcher) {
  const target = new URL(switcher.href);
  target.hash = location.hash;
  switcher.href = target.href;
  window.addEventListener("hashchange", () => {
    target.hash = location.hash;
    switcher.href = target.href;
  });
  const preferenceKey = "sar-adc-t28-language";
  try {
    if (document.documentElement.lang === "en" && localStorage.getItem(preferenceKey) === "zh-CN") {
      location.replace(target.href);
    }
    switcher.addEventListener("click", () => localStorage.setItem(preferenceKey, switcher.hreflang));
  } catch {
    // The switch remains a normal link when browser storage is blocked.
  }
}
