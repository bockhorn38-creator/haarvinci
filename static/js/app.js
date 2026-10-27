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
const appointmentForm = document.querySelector('.appointment-form');
if (appointmentForm) {
  let durationTimer;
  const fields = ['day', 'begin', 'finish', 'end_day'];
  const refreshDuration = () => {
    clearTimeout(durationTimer);
    durationTimer = setTimeout(async () => {
      const params = new URLSearchParams({datum: appointmentForm.elements.day.value, beginn: appointmentForm.elements.begin.value, ende: appointmentForm.elements.finish.value, enddatum: appointmentForm.elements.end_day.value});
      try {
        const response = await fetch(appointmentForm.dataset.durationUrl + '?' + params);
        const data = await response.json();
        document.getElementById('duration-preview').textContent = response.ok ? data.minutes + ' Minuten' : data.error;
      } catch (_) { document.getElementById('duration-preview').textContent = 'Wird beim Speichern berechnet'; }
    }, 200);
  };
  fields.forEach(name => appointmentForm.elements[name].addEventListener('input', refreshDuration));
  refreshDuration();
}
