"use strict";
for (const button of document.querySelectorAll(".password-toggle")) {
  button.addEventListener("click", () => {
    const input = document.getElementById(button.getAttribute("aria-controls"));
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    button.textContent = show ? "Verbergen" : "Anzeigen";
    button.setAttribute("aria-pressed", String(show));
  });
}
const errorSummary = document.querySelector(".form-error-summary[tabindex]");
if (errorSummary) {
  for (const field of document.querySelectorAll('.has-error')) {
    for (let parent = field.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
  }
  errorSummary.focus();
}
function revealSection() {
  const section = document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (section && section.tagName === 'DETAILS') section.open = true;
}
window.addEventListener('hashchange', revealSection);
revealSection();
if (document.querySelector('link[rel="manifest"]') && "serviceWorker" in navigator && window.isSecureContext) {
  navigator.serviceWorker.register("/sw.js").catch(() => {
    // Die Anwendung bleibt auch ohne Installationsunterstützung voll bedienbar.
  });
}
