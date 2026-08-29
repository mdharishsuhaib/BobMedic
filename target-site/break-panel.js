// break-panel.js — controls for the NovaCorp UI change panel.
// Writes break flags to localStorage; the portal pages read them via break.js.

(function () {
  var STORAGE_KEY = "bob_madak_breaks";

  var BREAKS = [
    {
      key: "rename_login_id",
      title: "Rename the sign-in button id",
      detail: "id=\"btn-login\" becomes id=\"auth-submit-v2\". Text, class and position stay stable.",
      page: "index.html",
    },
    {
      key: "move_login_button",
      title: "Move the sign-in button",
      detail: "The button moves out of div.actions and into the card footer container.",
      page: "index.html",
    },
    {
      key: "change_login_text",
      title: "Change the sign-in button text",
      detail: "Visible text \"Sign in\" becomes \"Login\". Only semantic understanding settles this one.",
      page: "index.html",
    },
    {
      key: "rename_export_id",
      title: "Rename the export button id",
      detail: "id=\"btn-export\" becomes id=\"export-data-btn\" on the invoice page.",
      page: "invoices.html",
    },
  ];

  function readBreaks() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch (e) {
      return {};
    }
  }

  function writeBreaks(state) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    render();
  }

  function render() {
    var state = readBreaks();
    var host = document.getElementById("break-list");
    host.innerHTML = "";

    BREAKS.forEach(function (b) {
      var on = !!state[b.key];

      var row = document.createElement("div");
      row.className = "break-row" + (on ? " on" : "");

      var info = document.createElement("div");
      info.className = "break-info";
      info.innerHTML =
        '<div class="break-title">' + b.title + '</div>' +
        '<div class="break-detail">' + b.detail + '</div>' +
        '<div class="break-page">' + b.page + '</div>';

      var toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "toggle" + (on ? " on" : "");
      toggle.setAttribute("data-key", b.key);
      toggle.textContent = on ? "Active" : "Off";
      toggle.addEventListener("click", function () {
        var s = readBreaks();
        s[b.key] = !s[b.key];
        writeBreaks(s);
      });

      row.appendChild(info);
      row.appendChild(toggle);
      host.appendChild(row);
    });

    document.getElementById("break-json").textContent =
      JSON.stringify(state, null, 2);
  }

  document.getElementById("btn-clear-breaks").addEventListener("click", function () {
    writeBreaks({});
  });

  document.getElementById("btn-break-all").addEventListener("click", function () {
    var s = {};
    BREAKS.forEach(function (b) { s[b.key] = true; });
    writeBreaks(s);
  });

  render();
})();

