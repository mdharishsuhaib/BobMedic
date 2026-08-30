import sys
sys.path.insert(0, '.')
from serve import ensure_server, write_break_state, read_break_state, BREAK_KEYS

# Step 1: reset
write_break_state({k: False for k in BREAK_KEYS})
ensure_server()

# Step 2: baseline
from watcher import record_baseline
record_baseline('bobmedic-login', headless=True)
print('After baseline, state:', read_break_state())

# Step 3: set break
write_break_state({'break_login_id': True})
print('After break set, state:', read_break_state())

# Step 4: what does run_wal see?
from parser import parse_wal
from registry import get_bot, step_names
bot = get_bot('bobmedic-login')
import time
from playwright.sync_api import sync_playwright
from runner import _break_script
from serve import read_break_state as rbs

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context()
    current_state = rbs()
    print('State at Playwright launch:', current_state)
    ctx.add_init_script(_break_script(current_state))
    page = ctx.new_page()
    page.goto('http://127.0.0.1:8000/index.html', wait_until='domcontentloaded')
    btn_id = page.evaluate('() => { const b = document.querySelector("button[type=submit]"); return b ? b.id : "NOT_FOUND"; }')
    print('Button id Playwright sees:', btn_id)
    browser.close()
