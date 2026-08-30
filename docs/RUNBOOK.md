# BotMedic — Runbook

**Team BobVanta**

Everything from a fresh clone to a finished demo. Commands are written for
PowerShell on Windows and run from the `botmedic/` folder.

---

## 1. One-time setup

```powershell
pip install -r requirements.txt
python -m playwright install chromium

cd dashboard
npm install
cd ..
```

`playwright install chromium` downloads the browser the bots actually drive.
Skipping it is the most common first-run failure.

---

## 2. Record the baseline — do this before anything else

```powershell
python src/engine.py baseline
```

Every bot runs against the healthy site while BotMedic fingerprints each
element it touches and saves a DOM snapshot. **Without a baseline there is
nothing to compare a broken page against, and every incident escalates.**

Expected output — four bots, one line each:

```
[BASELINE] bobmedic-login: 3 elements fingerprinted in 10.4s
[BASELINE] invoice-extract: 5 elements fingerprinted in 8.3s
[BASELINE] invoice-entry: 6 elements fingerprinted in 8.0s
[BASELINE] payment-submit: 7 elements fingerprinted in 9.0s
```

Baseline also resets all break flags, so it doubles as "put the site back to
normal".

---

## 3. Start everything

```powershell
python start.py
```

| What | Where |
|---|---|
| Target site (demo application) | http://127.0.0.1:8000 |
| Break control panel | http://127.0.0.1:8000/break.html |
| Control API | http://127.0.0.1:8100/api/feed |
| Dashboard | **http://localhost:3000** |

> The dashboard is served by Vite on `localhost`, not `127.0.0.1`. Use
> `http://localhost:3000` — `http://127.0.0.1:3000` will not connect.

Leave this window running. Ctrl+C stops all three.

---

## 4. The demo

### Path A — from the dashboard (what an audience should see)

1. Open **http://localhost:3000**
2. Pick a bot in the **Bot fleet** row, choose a break scenario, press
   **Break & run**
3. Watch the incident appear in the list. Open it for the diagnosis, the
   candidate scores, and the diff
4. On a `reversible_write` incident, press **Approve & rerun** — the patch is
   written to the real `.wal` and the bot runs again

### Path B — from the command line

```powershell
python src/engine.py demo bobmedic-login  rename-login-id     # heals, auto-applies
python src/engine.py demo invoice-entry   rename-login-id     # heals, waits for approval
python src/engine.py demo payment-submit  rename-login-id     # refuses: irreversible
python src/engine.py demo invoice-extract login-text-change   # ambiguous: asks Bob
python src/engine.py demo invoice-extract rename-export-id    # breaks a second page
```

Add `--show` to any command to watch the browser work:

```powershell
python src/engine.py --show demo bobmedic-login rename-login-id
```

### Path C — break the site by hand, live

This is the most convincing version, because nothing is scripted.

1. Open **http://127.0.0.1:8000/break.html**
2. Flip **Rename login button ID**
3. Open http://127.0.0.1:8000/index.html — the sign-in button is now
   `auth-submit-v2`; the page looks identical to a human
4. Run a bot against the site as it now stands:
   ```powershell
   python src/engine.py run bobmedic-login
   ```
5. The bot fails, BotMedic diagnoses and heals it, and the incident appears in
   the dashboard
6. Press **Reset all faults** in the panel to put the site back

Break state lives in `target-site/break-state.json` on the server, so the
panel, the headless bots and IBM RPA Studio's own Chrome all see the same
broken page.

---

## 5. What each scenario proves

| Scenario | Bot | Tier | Score | Outcome |
|---|---|---|---|---|
| `rename-login-id` | bobmedic-login | `read_only` | 0.92 | verified, applied automatically |
| `rename-login-id` | invoice-entry | `reversible_write` | 0.92 | verified, held for approval |
| `rename-login-id` | payment-submit | `irreversible` | 0.92 | **refused** — match withheld |
| `login-text-change` | invoice-extract | `read_only` | 0.77 | ambiguous band → Bob |
| `rename-export-id` | invoice-extract | `read_only` | 0.92 | heals a different page and step |

0.92 is a plain id rename: text, class, type, DOM path, position and element
type all still match, and only the id moved. It never reaches a model.

---

## 6. Between demo runs

Once a bot has been healed, its script no longer uses the broken id — so
running the same scenario again correctly reports *nothing to heal*. Put the
scripts back first:

```powershell
python src/engine.py restore          # undo applied patches (all bots)
python src/engine.py reset            # clear incidents, snapshots, patch copies
python src/engine.py baseline         # re-record, and clear all break flags
```

Full clean slate, in order: `restore` → `reset` → `baseline`.

---

## 7. Bob at runtime

Bob Shell is called only when scoring lands between 0.55 and 0.85:

```powershell
bob -p "@<prompt file>" --hide-intermediary-output
```

If `bob` is not on the PATH, that band **escalates to a human instead of
guessing** — which is correct behaviour, but it means the ambiguous scenario
shows an escalation rather than a Bob-resolved patch. Check with:

```powershell
Get-Command bob
```

To point at a different binary, or to run the ambiguous path offline with the
clearly labelled test double:

```powershell
$env:BOBMADAK_BOB_CMD = "tools\bob-stub.cmd"
```

To turn model calls off entirely: `$env:BOBMADAK_BOB_DISABLED = "1"`.

---

## 8. Troubleshooting

**"Port already in use" / stale servers from an earlier session**

```powershell
Get-NetTCPConnection -LocalPort 8000,8100,3000 -State Listen |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

**Dashboard shows "Sample data" or "Reading incidents.json"**
The control API is not reachable. The dashboard still renders — it falls back
to the file the engine writes, then to bundled sample data — but Break & run
and Approve will not work. Start `python start.py`.

**Every incident escalates with "no fingerprint on file"**
No baseline was recorded for that bot. Run `python src/engine.py baseline`.

**A demo reports "The bot survived this change"**
The bot was already healed onto a stable selector. Run
`python src/engine.py restore` first. This is the system working, not a bug.

**The bot fails at a step that is not the one you broke**
The site is carrying break flags from an earlier run. `python src/engine.py
baseline` clears them, or press **Reset all faults** in the break panel.

---

## 9. Where things end up

```
fingerprints/<bot>.json         what each element looked like when healthy
snapshots/<run>.html            the DOM at the moment the bot failed
incidents/<run>.failure.json    the failure event (frozen contract)
incidents/<run>.incident.json   the patch proposal plus evidence
patch-candidates/<run>.*.wal    patched copies tried during verification
rpa-bots/*.wal.bak              the script as it was before a patch was applied
dashboard/public/incidents.json the feed the dashboard reads
```

The original `.wal` is only ever overwritten by an explicit commit — an
approval, or an automatic apply on a `read_only` bot — and a `.bak` is written
first every time.

---

## 10. Healing a bot you ran from IBM RPA Studio

The engine can only see bots it launched itself. When the bot is started from
Studio — which is how the demo actually runs — the watcher below supplies the
missing signal.

Studio records every failed element lookup in its own log:

```
2026-08-30T04:34:32 WARN WebClickCommand Studio
Control not found to Click on Css=#btn-login
```

Start the watcher in its own terminal and leave it running:

```powershell
python src/studio_watcher.py --bot bobmedic-login
```

Then run the demo the way an operator would:

1. Open **http://127.0.0.1:8000/break.html** and switch on a fault
2. Run the bot in IBM RPA Studio — it stops, exactly as it would in production
3. The watcher picks the failure out of Studio's log, identifies which scripts
   use that selector, diagnoses, verifies and patches
4. Re-run the bot in Studio. It completes.

Useful flags:

```powershell
python src/studio_watcher.py --replay      # heal from the last failure already logged
python src/studio_watcher.py --from-start  # scan the whole log, not just new entries
python src/studio_watcher.py --log <path>  # non-default Studio.log location
```

Without `--bot`, every registered script that uses the broken selector is
healed — which is correct when a renamed id breaks four bots at once, and each
one is still gated by its own risk tier.

### Why the patch stays openable in Studio

A `.wal` saved by Studio is not plain text. It is a small container:

```
0x12  <varint body length>  <script body>  0x2A 0x09 "23.0.19.0"
```

Patching it as text corrupts the header byte, leaves the length prefix
disagreeing with the body, and drops the version trailer — Studio then rejects
the file with *"Command not found on line 0"*. The patcher therefore edits
bytes, recomputes the length prefix, and preserves the trailer. It also
replaces the selector on **every** line that used it, because a renamed id
breaks each reference, not only the one that happened to fail first.
