"""
Bob Session Report Exporter
Generates a clean HTML report from ~/.bob/db/bob.db
Usage: python export-bob-report.py [--project "BotMedic"]
"""

import sqlite3
import json
import os
import sys
import re
import argparse
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.expanduser("~"), ".bob", "db", "bob.db")

def ts_to_str(ts_ms):
    if not ts_ms:
        return "—"
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def extract_text(data_json):
    """Extract plain text content from a message data JSON blob."""
    try:
        obj = json.loads(data_json)
        content = obj.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(item.get("text", ""))
                    elif item.get("type") == "tool_use":
                        parts.append(f"[Tool: {item.get('name','')}]")
                    elif item.get("type") == "tool_result":
                        inner = item.get("content", "")
                        if isinstance(inner, list):
                            for i in inner:
                                if isinstance(i, dict) and i.get("type") == "text":
                                    parts.append(f"[Result: {i.get('text','')[:200]}]")
                        else:
                            parts.append(f"[Result: {str(inner)[:200]}]")
            return "\n".join(parts)
        return str(content)
    except Exception:
        return str(data_json)[:300]

def extract_spend(data_json):
    """Extract token spend from assistant message metadata."""
    try:
        obj = json.loads(data_json)
        meta = obj.get("_meta", {})
        spend = meta.get("spend", {})
        if spend:
            inp = spend.get("input", 0)
            out = spend.get("output", 0)
            return inp, out
    except Exception:
        pass
    return 0, 0

def escape_html(text):
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

def load_tasks(conn, project_filter=None):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, status, directory, created_at, updated_at, costs
        FROM tasks
        ORDER BY created_at ASC
    """)
    tasks = []
    for row in cur.fetchall():
        tid, title, status, directory, created_at, updated_at, costs = row
        if project_filter:
            combined = (title or "") + (directory or "")
            if project_filter.lower() not in combined.lower():
                continue
        tasks.append({
            "id": tid,
            "title": title or "(untitled)",
            "status": status,
            "directory": directory or "",
            "created_at": created_at,
            "updated_at": updated_at,
            "costs": costs,
        })
    return tasks

def load_messages(conn, task_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT role, data, created_at
        FROM messages
        WHERE task_id = ?
        ORDER BY created_at ASC
    """, (task_id,))
    msgs = []
    for role, data, created_at in cur.fetchall():
        if role == "system":
            continue
        text = extract_text(data)
        in_tok, out_tok = (0, 0)
        if role == "assistant":
            in_tok, out_tok = extract_spend(data)
        msgs.append({
            "role": role,
            "text": text,
            "created_at": created_at,
            "in_tok": in_tok,
            "out_tok": out_tok,
        })
    return msgs

def build_html(tasks, conn, project_name):
    total_tasks = len(tasks)
    total_in = 0
    total_out = 0
    all_task_html = []

    for task in tasks:
        msgs = load_messages(conn, task["id"])
        msg_count = len(msgs)
        task_in = sum(m["in_tok"] for m in msgs)
        task_out = sum(m["out_tok"] for m in msgs)
        total_in += task_in
        total_out += task_out

        msgs_html = []
        for m in msgs:
            role = m["role"]
            role_label = "You" if role == "user" else "Bob"
            role_class = "msg-user" if role == "user" else "msg-assistant"
            text = escape_html(m["text"])
            # simple code block formatting
            text = re.sub(r'```([^`]*?)```', r'<pre><code>\1</code></pre>', text, flags=re.DOTALL)
            text = text.replace("\n", "<br>")
            time_str = ts_to_str(m["created_at"])
            tok_str = ""
            if role == "assistant" and (m["in_tok"] or m["out_tok"]):
                tok_str = f'<span class="tokens">{m["in_tok"]:,} in / {m["out_tok"]:,} out</span>'
            msgs_html.append(f"""
            <div class="message {role_class}">
              <div class="msg-header">
                <span class="role-label">{role_label}</span>
                <span class="msg-time">{time_str}</span>
                {tok_str}
              </div>
              <div class="msg-body">{text}</div>
            </div>""")

        status_class = {
            "running": "status-running",
            "active": "status-active",
            "completed": "status-completed",
        }.get(task["status"], "status-other")

        tok_summary = f"{task_in:,} in / {task_out:,} out" if (task_in or task_out) else "—"

        all_task_html.append(f"""
      <details class="task-block" open>
        <summary class="task-summary">
          <span class="task-title">{escape_html(task['title'])}</span>
          <span class="task-meta">
            <span class="status-badge {status_class}">{task['status']}</span>
            <span>{msg_count} messages</span>
            <span>{tok_summary} tokens</span>
            <span>{ts_to_str(task['created_at'])}</span>
          </span>
        </summary>
        <div class="task-dir">📁 {escape_html(task['directory'])}</div>
        <div class="messages-list">
          {''.join(msgs_html) if msgs_html else '<p class="empty">No messages.</p>'}
        </div>
      </details>""")

    generated_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IBM Bob Session Report — {escape_html(project_name)}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system,"Segoe UI",system-ui,sans-serif; font-size:14px;
         line-height:1.6; background:#f7f8fa; color:#1f2328; }}
  .page {{ max-width:860px; margin:0 auto; padding:32px 16px 64px; }}

  /* Header */
  .report-header {{ background:#fff; border:1px solid #e5e7eb; border-radius:8px;
                    padding:24px 28px; margin-bottom:24px; }}
  .report-header h1 {{ font-size:20px; font-weight:700; color:#1f2328; }}
  .report-header .subtitle {{ color:#57606a; font-size:13px; margin-top:4px; }}
  .stats-row {{ display:flex; gap:24px; margin-top:16px; flex-wrap:wrap; }}
  .stat {{ background:#f7f8fa; border:1px solid #e5e7eb; border-radius:6px;
           padding:10px 16px; min-width:120px; }}
  .stat-val {{ font-size:22px; font-weight:700; color:#3b82d4; }}
  .stat-lbl {{ font-size:11px; color:#57606a; text-transform:uppercase; letter-spacing:.5px; }}

  /* Task block */
  .task-block {{ background:#fff; border:1px solid #e5e7eb; border-radius:8px;
                 margin-bottom:16px; overflow:hidden; }}
  .task-summary {{ display:flex; justify-content:space-between; align-items:center;
                   padding:14px 20px; cursor:pointer; list-style:none; flex-wrap:wrap; gap:8px; }}
  .task-summary::-webkit-details-marker {{ display:none; }}
  .task-summary::before {{ content:"▶"; font-size:10px; color:#57606a; margin-right:8px;
                            transition:transform .15s; }}
  details[open] > .task-summary::before {{ transform:rotate(90deg); }}
  .task-title {{ font-weight:600; font-size:14px; flex:1; min-width:180px; }}
  .task-meta {{ display:flex; gap:12px; align-items:center; flex-wrap:wrap;
                font-size:12px; color:#57606a; }}
  .task-dir {{ padding:6px 20px; font-size:11px; color:#57606a;
               background:#f7f8fa; border-top:1px solid #e5e7eb; border-bottom:1px solid #e5e7eb; }}

  /* Status badges */
  .status-badge {{ padding:2px 8px; border-radius:99px; font-size:11px; font-weight:600; }}
  .status-running  {{ background:#dbeafe; color:#1d4ed8; }}
  .status-active   {{ background:#dcfce7; color:#15803d; }}
  .status-completed{{ background:#f3f4f6; color:#374151; }}
  .status-other    {{ background:#fef9c3; color:#854d0e; }}

  /* Messages */
  .messages-list {{ padding:16px 20px; display:flex; flex-direction:column; gap:12px; }}
  .message {{ border-radius:6px; padding:12px 14px; font-size:13px; }}
  .msg-user      {{ background:#f0f4ff; border:1px solid #dbeafe; }}
  .msg-assistant {{ background:#f7f8fa; border:1px solid #e5e7eb; }}
  .msg-header {{ display:flex; gap:10px; align-items:center; margin-bottom:6px;
                 flex-wrap:wrap; }}
  .role-label {{ font-weight:700; font-size:12px; color:#1f2328; }}
  .msg-time {{ font-size:11px; color:#57606a; }}
  .tokens {{ font-size:11px; color:#7c5cd8; margin-left:auto; }}
  .msg-body {{ color:#1f2328; word-break:break-word; }}
  .msg-body pre {{ background:#1f2328; color:#e6edf3; padding:10px 12px;
                   border-radius:4px; overflow-x:auto; font-size:12px;
                   margin:8px 0; white-space:pre-wrap; }}
  .empty {{ color:#57606a; font-size:12px; font-style:italic; }}

  /* Footer */
  .footer {{ text-align:center; margin-top:40px; padding-top:16px;
             border-top:1px solid #e5e7eb; color:#57606a; font-size:12px; }}
</style>
</head>
<body>
<div class="page">

  <div class="report-header">
    <h1>IBM Bob Session Report</h1>
    <div class="subtitle">Project: <strong>{escape_html(project_name)}</strong> &nbsp;·&nbsp; Generated: {generated_at}</div>
    <div class="stats-row">
      <div class="stat"><div class="stat-val">{total_tasks}</div><div class="stat-lbl">Tasks</div></div>
      <div class="stat"><div class="stat-val">{total_in:,}</div><div class="stat-lbl">Input tokens</div></div>
      <div class="stat"><div class="stat-val">{total_out:,}</div><div class="stat-lbl">Output tokens</div></div>
    </div>
  </div>

  {''.join(all_task_html) if all_task_html else '<p style="color:#57606a">No tasks found for this project.</p>'}

  <div class="footer">Made with IBM Bob &nbsp;·&nbsp; IBM TechXchange 2026 Hackathon Submission</div>
</div>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Export IBM Bob session report to HTML")
    parser.add_argument("--project", default="BotMedic",
                        help="Filter tasks by project name (matches title or directory)")
    parser.add_argument("--all", action="store_true",
                        help="Include all tasks, no filter")
    parser.add_argument("--out", default="bob-session-report.html",
                        help="Output HTML file path")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Bob database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    project_filter = None if args.all else args.project
    tasks = load_tasks(conn, project_filter)

    if not tasks:
        print(f"No tasks found for filter: '{project_filter}'")
        print("Tip: use --all to include all tasks, or --project 'keyword' to filter differently")
        conn.close()
        sys.exit(0)

    print(f"Found {len(tasks)} task(s):")
    for t in tasks:
        print(f"  [{t['status']}] {t['title'][:60]} — {ts_to_str(t['created_at'])}")

    html = build_html(tasks, conn, args.project if not args.all else "All Projects")
    conn.close()

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ Report saved to: {os.path.abspath(args.out)}")
    print(f"   Open in browser to review, then include in your submission repository.")


if __name__ == "__main__":
    main()
