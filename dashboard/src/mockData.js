// mockData.js - a frozen copy of a real engine feed.
//
// Used only when neither the control API nor dashboard/public/incidents.json
// is reachable, so the dashboard still renders during a cold demo. The shape
// is identical to the live feed: one binding, three sources.

export const MOCK_FEED = {
  "generated_at": "2026-08-30T09:00:00+00:00",
  "thresholds": {
    "confident": 0.85,
    "ambiguous": 0.55
  },
  "summary": {
    "incidents": 6,
    "healed": 3,
    "awaiting_approval": 1,
    "escalated": 2,
    "avg_manual_min": 46.3,
    "avg_auto_sec": 45.5,
    "bob_calls": 0
  },
  "bots": [
    {
      "bot_id": "bobmedic-login",
      "bot_name": "Portal Login Bot",
      "risk_tier": "read_only",
      "description": "Signs in using id-based selector #btn-login. The demo bot — breaks when the button id changes.",
      "wal": "BobMedic.wal"
    },
    {
      "bot_id": "invoice-extract",
      "bot_name": "Invoice Exporter",
      "risk_tier": "read_only",
      "description": "Signs in and downloads the invoice CSV export. Reads only.",
      "wal": "rpa-bots/invoice-extract.wal"
    },
    {
      "bot_id": "invoice-entry",
      "bot_name": "Invoice Filter Entry",
      "risk_tier": "reversible_write",
      "description": "Signs in and enters filter criteria. Writes draft state a human can undo.",
      "wal": "rpa-bots/invoice-entry.wal"
    },
    {
      "bot_id": "payment-submit",
      "bot_name": "Payment Batch Submitter",
      "risk_tier": "irreversible",
      "description": "Signs in and submits a payment. Money leaves the ledger — never auto-patched.",
      "wal": "rpa-bots/payment-submit.wal"
    }
  ],
  "incidents": [
    {
      "id": "run-0006",
      "bot_id": "bobmedic-login",
      "bot_name": "Portal Login Bot",
      "wal_file": "BobMedic.wal",
      "risk_tier": "read_only",
      "failed_step": "login_wait",
      "error": "ElementNotFound",
      "detected_at": "2026-08-30T01:59:24.166498+00:00",
      "page_html_ref": "snapshots/run-0006.html",
      "status": "healed",
      "diff": [
        {
          "line_number": 10,
          "original": "webWaitElement --selector \"CssSelector\" --css \"#btn-login\" --timeout \"00:00:03\" loginButtom=value\r",
          "patched": "webWaitElement --selector \"CssSelector\" --css \"button.btn.primary[type='submit']\" --timeout \"00:00:03\" loginButtom=value\r"
        },
        {
          "line_number": 11,
          "original": "webClick --selector \"CssSelector\" --css \"#btn-login\"\r",
          "patched": "webClick --selector \"CssSelector\" --css \"button.btn.primary[type='submit']\"\r"
        }
      ],
      "candidates": [
        {
          "tag": "button",
          "text": "Sign in",
          "attrs": {
            "id": "auth-submit-v2",
            "class": "btn primary",
            "type": "submit"
          },
          "dom_path": "div#btn-container-default > button.btn.primary",
          "score": 0.9167,
          "signals": {
            "text": 1.0,
            "attrs": 0.6667,
            "dom_path": 1.0,
            "geometry": 1.0,
            "tag": 1.0
          }
        },
        {
          "tag": "input",
          "text": "e.g. j.smith@company.com",
          "attrs": {
            "id": "username",
            "type": "text",
            "name": "username",
            "placeholder": "e.g. j.smith@company.com"
          },
          "dom_path": "form#login-form > div.form-group > input",
          "score": 0.1431,
          "signals": {
            "text": 0.1935,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.5672,
            "tag": 0.0
          }
        },
        {
          "tag": "a",
          "text": "Contact IT support",
          "attrs": {
            "href": "#"
          },
          "dom_path": "div.auth > main.auth-form > div.login-card > div.login-footer > a",
          "score": 0.1349,
          "signals": {
            "text": 0.24,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.4196,
            "tag": 0.0
          }
        }
      ],
      "run_result": {
        "success": true,
        "duration_sec": 32.54,
        "steps_run": 7,
        "failed_step": null,
        "error": null
      },
      "bob_response": null,
      "mttr_manual_min": 47,
      "mttr_auto_sec": 81.6,
      "proposal": {
        "run_id": "run-0006",
        "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
        "script_line": 10,
        "old_selector": "#btn-login",
        "new_selector": "button.btn.primary[type='submit']",
        "confidence": 0.9167,
        "resolved_by": "deterministic",
        "verified": true,
        "action": "auto_applied"
      },
      "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
      "script_line": 10,
      "old_selector": "#btn-login",
      "new_selector": "button.btn.primary[type='submit']",
      "confidence": 0.9167,
      "resolved_by": "deterministic",
      "verified": true,
      "action": "auto_applied",
      "selector_basis": "element type and class — valid CSS, not tied to the id",
      "patched_wal": "patch-candidates/run-0006.BobMedic.wal",
      "verification_attempts": 1,
      "breaks": {}
    },
    {
      "id": "run-0005",
      "bot_id": "invoice-extract",
      "bot_name": "Invoice Exporter",
      "wal_file": "rpa-bots/invoice-extract.wal",
      "risk_tier": "read_only",
      "failed_step": "export_csv",
      "error": "ElementNotFound",
      "detected_at": "2026-08-30T01:53:22.481802+00:00",
      "page_html_ref": "snapshots/run-0005.html",
      "status": "healed",
      "diff": [
        {
          "line_number": 10,
          "original": "webClick --selector \"CssSelector\" --css \"#btn-export\"",
          "patched": "webClick --selector \"CssSelector\" --css \"#export-data-btn\""
        }
      ],
      "candidates": [
        {
          "tag": "button",
          "text": "Download CSV",
          "attrs": {
            "id": "export-data-btn",
            "class": "btn secondary",
            "type": "button"
          },
          "dom_path": "div#toolbar > button.btn.secondary",
          "score": 0.9162,
          "signals": {
            "text": 1.0,
            "attrs": 0.6667,
            "dom_path": 1.0,
            "geometry": 0.997,
            "tag": 1.0
          }
        },
        {
          "tag": "button",
          "text": "Bulk actions ▾",
          "attrs": {
            "class": "btn secondary ghost",
            "type": "button"
          },
          "dom_path": "div#toolbar > button.btn.secondary",
          "score": 0.5957,
          "signals": {
            "text": 0.2308,
            "attrs": 0.5556,
            "dom_path": 1.0,
            "geometry": 0.5835,
            "tag": 1.0
          }
        },
        {
          "tag": "button",
          "text": "Apply",
          "attrs": {
            "class": "btn ghost",
            "type": "button"
          },
          "dom_path": "div.page-wrap > div.filter-bar > button.btn.ghost",
          "score": 0.3234,
          "signals": {
            "text": 0.1176,
            "attrs": 0.4444,
            "dom_path": 0.0,
            "geometry": 0.5136,
            "tag": 1.0
          }
        }
      ],
      "run_result": {
        "success": true,
        "duration_sec": 15.51,
        "steps_run": 8,
        "failed_step": null,
        "error": null
      },
      "bob_response": null,
      "mttr_manual_min": 47,
      "mttr_auto_sec": 45.5,
      "proposal": {
        "run_id": "run-0005",
        "diagnosis": "Id changed from 'btn-export' to 'export-data-btn'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
        "script_line": 10,
        "old_selector": "#btn-export",
        "new_selector": "#export-data-btn",
        "confidence": 0.9162,
        "resolved_by": "deterministic",
        "verified": true,
        "action": "auto_applied"
      },
      "diagnosis": "Id changed from 'btn-export' to 'export-data-btn'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
      "script_line": 10,
      "old_selector": "#btn-export",
      "new_selector": "#export-data-btn",
      "confidence": 0.9162,
      "resolved_by": "deterministic",
      "verified": true,
      "action": "auto_applied",
      "selector_basis": "the new element id — last resort; it may change again",
      "patched_wal": "patch-candidates/run-0005.invoice-extract.wal",
      "verification_attempts": 1,
      "breaks": {
        "break_export_id": true
      }
    },
    {
      "id": "run-0004",
      "bot_id": "invoice-extract",
      "bot_name": "Invoice Exporter",
      "wal_file": "rpa-bots/invoice-extract.wal",
      "risk_tier": "read_only",
      "failed_step": "login_submit",
      "error": "ElementNotFound",
      "detected_at": "2026-08-30T01:52:50.763281+00:00",
      "page_html_ref": "snapshots/run-0004.html",
      "status": "escalated",
      "diff": [],
      "candidates": [
        {
          "tag": "button",
          "text": "Login",
          "attrs": {
            "id": "auth-submit-v2",
            "class": "btn primary",
            "type": "submit"
          },
          "dom_path": "div#btn-container-default > button.btn.primary",
          "score": 0.7667,
          "signals": {
            "text": 0.5,
            "attrs": 0.6667,
            "dom_path": 1.0,
            "geometry": 1.0,
            "tag": 1.0
          }
        },
        {
          "tag": "input",
          "text": "e.g. j.smith@company.com",
          "attrs": {
            "id": "username",
            "type": "text",
            "name": "username",
            "placeholder": "e.g. j.smith@company.com"
          },
          "dom_path": "form#login-form > div.form-group > input",
          "score": 0.1431,
          "signals": {
            "text": 0.1935,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.5672,
            "tag": 0.0
          }
        },
        {
          "tag": "a",
          "text": "Contact IT support",
          "attrs": {
            "href": "#"
          },
          "dom_path": "div.auth > main.auth-form > div.login-card > div.login-footer > a",
          "score": 0.1349,
          "signals": {
            "text": 0.24,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.4196,
            "tag": 0.0
          }
        }
      ],
      "run_result": null,
      "bob_response": {
        "selected_candidate_index": -1,
        "confidence": 0.0,
        "reasoning": "Bob Shell executable 'bob' not found on PATH.",
        "risk_note": "Escalated to a human instead of guessing.",
        "available": false
      },
      "mttr_manual_min": 47,
      "mttr_auto_sec": 22.8,
      "proposal": {
        "run_id": "run-0004",
        "diagnosis": "Scoring was ambiguous and Bob declined to pick a candidate: Bob Shell executable 'bob' not found on PATH.",
        "script_line": 8,
        "old_selector": "#btn-login",
        "new_selector": null,
        "confidence": 0.7667,
        "resolved_by": null,
        "verified": false,
        "action": "escalated_no_fix"
      },
      "diagnosis": "Scoring was ambiguous and Bob declined to pick a candidate: Bob Shell executable 'bob' not found on PATH.",
      "script_line": 8,
      "old_selector": "#btn-login",
      "new_selector": null,
      "confidence": 0.7667,
      "resolved_by": null,
      "verified": false,
      "action": "escalated_no_fix",
      "breaks": {
        "break_login_id": true,
        "break_login_text": true
      }
    },
    {
      "id": "run-0003",
      "bot_id": "payment-submit",
      "bot_name": "Payment Batch Submitter",
      "wal_file": "rpa-bots/payment-submit.wal",
      "risk_tier": "irreversible",
      "failed_step": "login_submit",
      "error": "ElementNotFound",
      "detected_at": "2026-08-30T01:52:22.249919+00:00",
      "page_html_ref": "snapshots/run-0003.html",
      "status": "escalated",
      "diff": [],
      "candidates": [
        {
          "tag": "button",
          "text": "Sign in",
          "attrs": {
            "id": "auth-submit-v2",
            "class": "btn primary",
            "type": "submit"
          },
          "dom_path": "div#btn-container-default > button.btn.primary",
          "score": 0.9167,
          "signals": {
            "text": 1.0,
            "attrs": 0.6667,
            "dom_path": 1.0,
            "geometry": 1.0,
            "tag": 1.0
          }
        },
        {
          "tag": "input",
          "text": "e.g. j.smith@company.com",
          "attrs": {
            "id": "username",
            "type": "text",
            "name": "username",
            "placeholder": "e.g. j.smith@company.com"
          },
          "dom_path": "form#login-form > div.form-group > input",
          "score": 0.1431,
          "signals": {
            "text": 0.1935,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.5672,
            "tag": 0.0
          }
        },
        {
          "tag": "a",
          "text": "Contact IT support",
          "attrs": {
            "href": "#"
          },
          "dom_path": "div.auth > main.auth-form > div.login-card > div.login-footer > a",
          "score": 0.1349,
          "signals": {
            "text": 0.24,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.4196,
            "tag": 0.0
          }
        }
      ],
      "run_result": null,
      "bob_response": null,
      "mttr_manual_min": 52,
      "mttr_auto_sec": null,
      "proposal": {
        "run_id": "run-0003",
        "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag. This bot is classed irreversible, so no patch was written, verified, or applied — the break is reported to an operator instead.",
        "script_line": 10,
        "old_selector": "#btn-login",
        "new_selector": null,
        "confidence": 0.9167,
        "resolved_by": null,
        "verified": false,
        "action": "blocked_risk_tier"
      },
      "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag. This bot is classed irreversible, so no patch was written, verified, or applied — the break is reported to an operator instead.",
      "script_line": 10,
      "old_selector": "#btn-login",
      "new_selector": null,
      "confidence": 0.9167,
      "resolved_by": null,
      "verified": false,
      "action": "blocked_risk_tier",
      "withheld_candidate": {
        "tag": "button",
        "text": "Sign in",
        "attrs": {
          "id": "auth-submit-v2",
          "class": "btn primary",
          "type": "submit"
        },
        "score": 0.9167
      },
      "breaks": {
        "break_login_id": true
      }
    },
    {
      "id": "run-0002",
      "bot_id": "invoice-entry",
      "bot_name": "Invoice Filter Entry",
      "wal_file": "rpa-bots/invoice-entry.wal",
      "risk_tier": "reversible_write",
      "failed_step": "login_submit",
      "error": "ElementNotFound",
      "detected_at": "2026-08-30T01:51:35.962590+00:00",
      "page_html_ref": "snapshots/run-0002.html",
      "status": "awaiting_approval",
      "diff": [
        {
          "line_number": 9,
          "original": "webClick --selector \"CssSelector\" --css \"#btn-login\"",
          "patched": "webClick --selector \"CssSelector\" --css \"button.btn.primary[type='submit']\""
        }
      ],
      "candidates": [
        {
          "tag": "button",
          "text": "Sign in",
          "attrs": {
            "id": "auth-submit-v2",
            "class": "btn primary",
            "type": "submit"
          },
          "dom_path": "div#btn-container-default > button.btn.primary",
          "score": 0.9167,
          "signals": {
            "text": 1.0,
            "attrs": 0.6667,
            "dom_path": 1.0,
            "geometry": 1.0,
            "tag": 1.0
          }
        },
        {
          "tag": "input",
          "text": "e.g. j.smith@company.com",
          "attrs": {
            "id": "username",
            "type": "text",
            "name": "username",
            "placeholder": "e.g. j.smith@company.com"
          },
          "dom_path": "form#login-form > div.form-group > input",
          "score": 0.1431,
          "signals": {
            "text": 0.1935,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.5672,
            "tag": 0.0
          }
        },
        {
          "tag": "a",
          "text": "Contact IT support",
          "attrs": {
            "href": "#"
          },
          "dom_path": "div.auth > main.auth-form > div.login-card > div.login-footer > a",
          "score": 0.1349,
          "signals": {
            "text": 0.24,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.4196,
            "tag": 0.0
          }
        }
      ],
      "run_result": {
        "success": true,
        "duration_sec": 11.9,
        "steps_run": 9,
        "failed_step": null,
        "error": null
      },
      "bob_response": null,
      "mttr_manual_min": 38,
      "mttr_auto_sec": 37.1,
      "proposal": {
        "run_id": "run-0002",
        "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
        "script_line": 9,
        "old_selector": "#btn-login",
        "new_selector": "button.btn.primary[type='submit']",
        "confidence": 0.9167,
        "resolved_by": "deterministic",
        "verified": true,
        "action": "await_approval"
      },
      "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
      "script_line": 9,
      "old_selector": "#btn-login",
      "new_selector": "button.btn.primary[type='submit']",
      "confidence": 0.9167,
      "resolved_by": "deterministic",
      "verified": true,
      "action": "await_approval",
      "selector_basis": "element type and class — valid CSS, not tied to the id",
      "patched_wal": "patch-candidates/run-0002.invoice-entry.wal",
      "verification_attempts": 1,
      "breaks": {
        "break_login_id": true
      }
    },
    {
      "id": "run-0001",
      "bot_id": "bobmedic-login",
      "bot_name": "Portal Login Bot",
      "wal_file": "BobMedic.wal",
      "risk_tier": "read_only",
      "failed_step": "login_wait",
      "error": "ElementNotFound",
      "detected_at": "2026-08-30T01:50:47.016654+00:00",
      "page_html_ref": "snapshots/run-0001.html",
      "status": "healed",
      "diff": [
        {
          "line_number": 10,
          "original": "webWaitElement --selector \"CssSelector\" --css \"#btn-login\" --timeout \"00:00:03\" loginButtom=value\r",
          "patched": "webWaitElement --selector \"CssSelector\" --css \"button.btn.primary[type='submit']\" --timeout \"00:00:03\" loginButtom=value\r"
        },
        {
          "line_number": 11,
          "original": "webClick --selector \"CssSelector\" --css \"#btn-login\"\r",
          "patched": "webClick --selector \"CssSelector\" --css \"button.btn.primary[type='submit']\"\r"
        }
      ],
      "candidates": [
        {
          "tag": "button",
          "text": "Sign in",
          "attrs": {
            "id": "auth-submit-v2",
            "class": "btn primary",
            "type": "submit"
          },
          "dom_path": "div#btn-container-default > button.btn.primary",
          "score": 0.9167,
          "signals": {
            "text": 1.0,
            "attrs": 0.6667,
            "dom_path": 1.0,
            "geometry": 1.0,
            "tag": 1.0
          }
        },
        {
          "tag": "input",
          "text": "e.g. j.smith@company.com",
          "attrs": {
            "id": "username",
            "type": "text",
            "name": "username",
            "placeholder": "e.g. j.smith@company.com"
          },
          "dom_path": "form#login-form > div.form-group > input",
          "score": 0.1431,
          "signals": {
            "text": 0.1935,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.5672,
            "tag": 0.0
          }
        },
        {
          "tag": "a",
          "text": "Contact IT support",
          "attrs": {
            "href": "#"
          },
          "dom_path": "div.auth > main.auth-form > div.login-card > div.login-footer > a",
          "score": 0.1349,
          "signals": {
            "text": 0.24,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.4196,
            "tag": 0.0
          }
        }
      ],
      "run_result": {
        "success": true,
        "duration_sec": 9.45,
        "steps_run": 7,
        "failed_step": null,
        "error": null
      },
      "bob_response": null,
      "mttr_manual_min": 47,
      "mttr_auto_sec": 40.5,
      "proposal": {
        "run_id": "run-0001",
        "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
        "script_line": 10,
        "old_selector": "#btn-login",
        "new_selector": "button.btn.primary[type='submit']",
        "confidence": 0.9167,
        "resolved_by": "deterministic",
        "verified": true,
        "action": "auto_applied"
      },
      "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
      "script_line": 10,
      "old_selector": "#btn-login",
      "new_selector": "button.btn.primary[type='submit']",
      "confidence": 0.9167,
      "resolved_by": "deterministic",
      "verified": true,
      "action": "auto_applied",
      "selector_basis": "element type and class — valid CSS, not tied to the id",
      "patched_wal": "patch-candidates/run-0001.BobMedic.wal",
      "verification_attempts": 1,
      "breaks": {
        "break_login_id": true
      }
    }
  ]
}
