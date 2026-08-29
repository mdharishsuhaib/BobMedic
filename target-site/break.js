// break.js — NovaCorp portal break injector.
// Reads the break flags written by break.html and mutates the DOM on load.
// This exists only so the BotMedic demo can break the site on demand;
// a real target application would break itself on its own release schedule.

(function () {
  var STORAGE_KEY = "botmedic_breaks";

  function readBreaks() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch (e) {
      return {};
    }
  }

  var breaks = readBreaks();

  // ── Break 1: rename the login button id ─────────────────────────
  if (breaks.rename_login_id) {
    var loginBtn = document.getElementById("btn-login");
    if (loginBtn) loginBtn.id = "auth-submit-v2";
  }

  // ── Break 2: move the login button into a different container ───
  if (breaks.move_login_button) {
    var btn = document.querySelector("#btn-login, #auth-submit-v2");
    var host = document.getElementById("login-footer");
    if (btn && host) {
      var shell = document.createElement("div");
      shell.className = "footer-actions";
      shell.appendChild(btn);
      host.appendChild(shell);
    }
  }

  // ── Break 3: change the login button visible text ───────────────
  if (breaks.change_login_text) {
    var textBtn = document.querySelector("#btn-login, #auth-submit-v2");
    if (textBtn) textBtn.textContent = "Login";
  }

  // ── Break 4: rename the export button id ────────────────────────
  if (breaks.rename_export_id) {
    var exportBtn = document.getElementById("btn-export");
    if (exportBtn) exportBtn.id = "export-data-btn";
  }

  // Expose the active break set for the break panel banner.
  window.__NOVACORP_BREAKS__ = breaks;

  var activeCount = Object.keys(breaks).filter(function (k) { return breaks[k]; }).length;
  if (activeCount > 0) {
    document.addEventListener("DOMContentLoaded", function () {
      var flag = document.createElement("div");
      flag.className = "break-flag";
      flag.textContent = activeCount + " UI change(s) active";
      document.body.appendChild(flag);
    });
  }
})();


