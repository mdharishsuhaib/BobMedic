// mockData.js - a frozen copy of a real engine feed.
//
// Used only when neither the control API nor dashboard/public/incidents.json
// is reachable, so the dashboard still renders during a cold demo. The shape
// is identical to the live feed: one binding, three sources.

export const MOCK_FEED = {
  "generated_at": "2026-08-29T18:00:00+00:00",
  "thresholds": {
    "confident": 0.85,
    "ambiguous": 0.55
  },
  "summary": {
    "incidents": 4,
    "healed": 1,
    "awaiting_approval": 1,
    "escalated": 2,
    "avg_manual_min": 46.0,
    "avg_auto_sec": 26.7,
    "bob_calls": 0
  },
  "bots": [
    {
      "bot_id": "invoice-extract",
      "bot_name": "NorthShore Invoice Exporter",
      "risk_tier": "read_only",
      "description": "Signs in and downloads the invoice CSV export. Reads only.",
      "wal": "rpa-bots/invoice-extract.wal"
    },
    {
      "bot_id": "invoice-entry",
      "bot_name": "NorthShore Invoice Filter Entry",
      "risk_tier": "reversible_write",
      "description": "Signs in and enters filter criteria. Writes draft state a human can undo.",
      "wal": "rpa-bots/invoice-entry.wal"
    },
    {
      "bot_id": "payment-submit",
      "bot_name": "NorthShore Payment Batch Submitter",
      "risk_tier": "irreversible",
      "description": "Signs in and submits a payment. Money leaves the ledger — never auto-patched.",
      "wal": "rpa-bots/payment-submit.wal"
    }
  ],
  "incidents": [
    {
      "id": "run-0004",
      "bot_id": "invoice-extract",
      "bot_name": "NorthShore Invoice Exporter",
      "wal_file": "rpa-bots/invoice-extract.wal",
      "risk_tier": "read_only",
      "failed_step": "login_submit",
      "error": "ElementNotFound",
      "detected_at": "2026-08-29T19:05:12.986520+00:00",
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
          "score": 0.1442,
          "signals": {
            "text": 0.1935,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.5743,
            "tag": 0.0
          }
        },
        {
          "tag": "a",
          "text": "Contact IT support",
          "attrs": {
            "href": "#"
          },
          "dom_path": "main > div.login-card > div.login-footer > a",
          "score": 0.1365,
          "signals": {
            "text": 0.24,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.4302,
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
      "mttr_auto_sec": 16.6,
      "proposal": {
        "run_id": "run-0004",
        "diagnosis": "Scoring was ambiguous and Bob declined to pick a candidate: Bob Shell executable 'bob' not found on PATH.",
        "script_line": 8,
        "old_selector": "button[type='submit']:has-text('Sign in')",
        "new_selector": null,
        "confidence": 0.7667,
        "resolved_by": null,
        "verified": false,
        "action": "escalated_no_fix"
      },
      "diagnosis": "Scoring was ambiguous and Bob declined to pick a candidate: Bob Shell executable 'bob' not found on PATH.",
      "script_line": 8,
      "old_selector": "button[type='submit']:has-text('Sign in')",
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
      "bot_name": "NorthShore Payment Batch Submitter",
      "wal_file": "rpa-bots/payment-submit.wal",
      "risk_tier": "irreversible",
      "failed_step": "login_submit",
      "error": "ElementNotFound",
      "detected_at": "2026-08-29T19:04:52.253853+00:00",
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
          "score": 0.1442,
          "signals": {
            "text": 0.1935,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.5743,
            "tag": 0.0
          }
        },
        {
          "tag": "a",
          "text": "Contact IT support",
          "attrs": {
            "href": "#"
          },
          "dom_path": "main > div.login-card > div.login-footer > a",
          "score": 0.1365,
          "signals": {
            "text": 0.24,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.4302,
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
      "bot_name": "NorthShore Invoice Filter Entry",
      "wal_file": "rpa-bots/invoice-entry.wal",
      "risk_tier": "reversible_write",
      "failed_step": "login_submit",
      "error": "ElementNotFound",
      "detected_at": "2026-08-29T19:04:17.557720+00:00",
      "page_html_ref": "snapshots/run-0002.html",
      "status": "awaiting_approval",
      "diff": [
        {
          "line_number": 9,
          "original": "webClick --selector \"CssSelector\" --css \"#btn-login\"",
          "patched": "webClick --selector \"CssSelector\" --css \"button[type='submit']:has-text('Sign in')\""
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
          "score": 0.1442,
          "signals": {
            "text": 0.1935,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.5743,
            "tag": 0.0
          }
        },
        {
          "tag": "a",
          "text": "Contact IT support",
          "attrs": {
            "href": "#"
          },
          "dom_path": "main > div.login-card > div.login-footer > a",
          "score": 0.1365,
          "signals": {
            "text": 0.24,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.4302,
            "tag": 0.0
          }
        }
      ],
      "run_result": {
        "success": true,
        "duration_sec": 7.92,
        "steps_run": 9,
        "failed_step": null,
        "error": null
      },
      "bob_response": null,
      "mttr_manual_min": 38,
      "mttr_auto_sec": 31.4,
      "proposal": {
        "run_id": "run-0002",
        "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
        "script_line": 9,
        "old_selector": "#btn-login",
        "new_selector": "button[type='submit']:has-text('Sign in')",
        "confidence": 0.9167,
        "resolved_by": "deterministic",
        "verified": true,
        "action": "await_approval"
      },
      "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
      "script_line": 9,
      "old_selector": "#btn-login",
      "new_selector": "button[type='submit']:has-text('Sign in')",
      "confidence": 0.9167,
      "resolved_by": "deterministic",
      "verified": true,
      "action": "await_approval",
      "selector_basis": "visible text plus element type — survives an id rename",
      "patched_wal": "patch-candidates/run-0002.invoice-entry.wal",
      "verification_attempts": 1,
      "breaks": {
        "break_login_id": true
      }
    },
    {
      "id": "run-0001",
      "bot_id": "invoice-extract",
      "bot_name": "NorthShore Invoice Exporter",
      "wal_file": "rpa-bots/invoice-extract.wal",
      "risk_tier": "read_only",
      "failed_step": "login_submit",
      "error": "ElementNotFound",
      "detected_at": "2026-08-29T19:03:42.699479+00:00",
      "page_html_ref": "snapshots/run-0001.html",
      "status": "healed",
      "diff": [
        {
          "line_number": 8,
          "original": "webClick --selector \"CssSelector\" --css \"#btn-login\"",
          "patched": "webClick --selector \"CssSelector\" --css \"button[type='submit']:has-text('Sign in')\""
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
          "score": 0.1442,
          "signals": {
            "text": 0.1935,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.5743,
            "tag": 0.0
          }
        },
        {
          "tag": "a",
          "text": "Contact IT support",
          "attrs": {
            "href": "#"
          },
          "dom_path": "main > div.login-card > div.login-footer > a",
          "score": 0.1365,
          "signals": {
            "text": 0.24,
            "attrs": 0.0,
            "dom_path": 0.0,
            "geometry": 0.4302,
            "tag": 0.0
          }
        }
      ],
      "run_result": {
        "success": true,
        "duration_sec": 8.48,
        "steps_run": 8,
        "failed_step": null,
        "error": null
      },
      "bob_response": null,
      "mttr_manual_min": 47,
      "mttr_auto_sec": 32.0,
      "proposal": {
        "run_id": "run-0001",
        "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
        "script_line": 8,
        "old_selector": "#btn-login",
        "new_selector": "button[type='submit']:has-text('Sign in')",
        "confidence": 0.9167,
        "resolved_by": "deterministic",
        "verified": true,
        "action": "auto_applied"
      },
      "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'; attributes were refactored. Stable signals: text, dom_path, geometry, tag.",
      "script_line": 8,
      "old_selector": "#btn-login",
      "new_selector": "button[type='submit']:has-text('Sign in')",
      "confidence": 0.9167,
      "resolved_by": "deterministic",
      "verified": true,
      "action": "auto_applied",
      "selector_basis": "visible text plus element type — survives an id rename",
      "patched_wal": "patch-candidates/run-0001.invoice-extract.wal",
      "verification_attempts": 1,
      "breaks": {
        "break_login_id": true
      }
    }
  ]
}
