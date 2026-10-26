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
if (errorSummary) errorSummary.focus();
if (document.querySelector('link[rel="manifest"]') && "serviceWorker" in navigator && window.isSecureContext) {
  navigator.serviceWorker.register("/sw.js").catch(() => {
    // Die Anwendung bleibt auch ohne Installationsunterstützung voll bedienbar.
  });
}
