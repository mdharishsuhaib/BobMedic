// NovaCorp Finance Portal — app.js
// Synthetic demo data only — no real credentials or client data.

var VALID_CREDENTIALS = { username: "operator", password: "nova2026" };

var INVOICES = [
  { id: "INV-2026-001", client: "Apex Trading LLC",    amount: 42500.00,  due: "2026-08-15", status: "paid"    },
  { id: "INV-2026-002", client: "Crescent Imports",    amount: 18750.50,  due: "2026-08-22", status: "pending" },
  { id: "INV-2026-003", client: "Delta Logistics Co.", amount: 93200.00,  due: "2026-07-30", status: "overdue" },
  { id: "INV-2026-004", client: "Horizon Group",       amount: 7840.00,   due: "2026-09-01", status: "pending" },
  { id: "INV-2026-005", client: "Summit Partners",     amount: 215000.00, due: "2026-08-18", status: "paid"    },
  { id: "INV-2026-006", client: "Riverstone Ltd.",     amount: 31500.00,  due: "2026-08-10", status: "overdue" },
  { id: "INV-2026-007", client: "Kestrel Manufacturing", amount: 64300.75, due: "2026-09-12", status: "pending" },
  { id: "INV-2026-008", client: "Baltic Freight AS",   amount: 12980.20,  due: "2026-08-29", status: "paid"    }
];

// ── Login page ────────────────────────────────────────────────────
var loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", function () {
    var username = document.getElementById("username").value.trim();
    var password = document.getElementById("password").value;
    var errEl    = document.getElementById("error-msg");

    if (username === VALID_CREDENTIALS.username &&
        password === VALID_CREDENTIALS.password) {
      sessionStorage.setItem("nova_user", username);
      window.location.href = "invoices.html";
    } else {
      errEl.style.display = "block";
    }
  });
}

// ── Shared session guard ──────────────────────────────────────────
function requireUser() {
  var user = sessionStorage.getItem("nova_user");
  if (!user) {
    window.location.href = "index.html";
    return null;
  }
  var display = document.getElementById("user-display");
  if (display) display.textContent = "Welcome, " + user;
  return user;
}

function bindLogout() {
  var logout = document.getElementById("btn-logout");
  if (logout) {
    logout.addEventListener("click", function () {
      sessionStorage.removeItem("nova_user");
      window.location.href = "index.html";
    });
  }
}

// ── Invoices page ─────────────────────────────────────────────────
var invoicesBody = document.getElementById("invoices-body");
if (invoicesBody) {
  if (requireUser()) {
    renderInvoices(INVOICES);
    bindLogout();
    bindInvoiceToolbar();
  }
}

function renderInvoices(rows) {
  invoicesBody.innerHTML = "";
  rows.forEach(function (inv) {
    var badgeClass =
      inv.status === "paid"    ? "badge-paid"    :
      inv.status === "pending" ? "badge-pending" : "badge-overdue";

    var row = document.createElement("tr");
    row.setAttribute("data-invoice-id", inv.id);
    row.innerHTML =
      '<td class="mono">' + inv.id + '</td>' +
      '<td>' + inv.client + '</td>' +
      '<td class="mono">$' + inv.amount.toLocaleString("en-US", { minimumFractionDigits: 2 }) + '</td>' +
      '<td class="mono">' + inv.due + '</td>' +
      '<td><span class="badge ' + badgeClass + '">' + inv.status + '</span></td>' +
      '<td class="row-actions">' +
        '<a href="#" class="link-muted row-view" data-id="' + inv.id + '">View</a>' +
        '<button type="button" class="btn tiny row-download" data-id="' + inv.id + '">Download</button>' +
      '</td>';
    invoicesBody.appendChild(row);
  });
}

function bindInvoiceToolbar() {
  var exportBtn = document.getElementById("btn-export");
  if (exportBtn) {
    exportBtn.addEventListener("click", function () {
      var csv = ["invoice,client,amount,due,status"];
      INVOICES.forEach(function (i) {
        csv.push([i.id, i.client, i.amount, i.due, i.status].join(","));
      });
      flash("Exported " + INVOICES.length + " invoices to CSV (demo)");
      window.__LAST_EXPORT__ = csv.join("\n");
    });
  }

  var refresh = document.getElementById("btn-refresh");
  if (refresh) refresh.addEventListener("click", function () { renderInvoices(INVOICES); });

  var print = document.getElementById("btn-print");
  if (print) print.addEventListener("click", function () { flash("Print queued (demo)"); });

  var apply = document.getElementById("btn-apply-filter");
  if (apply) {
    apply.addEventListener("click", function () {
      var status = document.getElementById("filter-status").value;
      var term   = document.getElementById("search-invoices").value.trim().toLowerCase();
      renderInvoices(INVOICES.filter(function (i) {
        var byStatus = status === "all" || i.status === status;
        var byTerm   = !term || i.client.toLowerCase().indexOf(term) > -1 ||
                       i.id.toLowerCase().indexOf(term) > -1;
        return byStatus && byTerm;
      }));
    });
  }

  invoicesBody.addEventListener("click", function (e) {
    if (e.target && e.target.classList.contains("row-download")) {
      flash("Downloading " + e.target.getAttribute("data-id") + " (demo)");
    }
  });
}

// ── Payment page ──────────────────────────────────────────────────
var paymentForm = document.getElementById("payment-form");
if (paymentForm) {
  if (requireUser()) {
    bindLogout();
    paymentForm.addEventListener("submit", function () {
      var recipient = document.getElementById("recipient").value.trim();
      var amount    = document.getElementById("amount").value.trim();
      var result    = document.getElementById("payment-result");

      if (!recipient || !amount) {
        result.className = "payment-result error";
        result.textContent = "Recipient and amount are required.";
        return;
      }
      result.className = "payment-result ok";
      result.textContent = "Payment of $" + amount + " to " + recipient +
                           " submitted (demo — nothing left this machine).";
    });

    var cancel = document.getElementById("btn-cancel-payment");
    if (cancel) {
      cancel.addEventListener("click", function () {
        window.location.href = "invoices.html";
      });
    }
  }
}

// ── Small toast ───────────────────────────────────────────────────
function flash(message) {
  var el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.add("show");
  setTimeout(function () { el.classList.remove("show"); }, 2200);
}
