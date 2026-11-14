"""Generate docs/index.html: a professional, self-contained static dashboard."""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Embedded SW Job Tracker — Israel</title>
<style>
 :root {{
   --bg: #0f172a; --panel: #1e293b; --panel-hover: #263449; --border: #334155;
   --text: #f1f5f9; --muted: #94a3b8; --accent: #38bdf8; --accent-soft: rgba(56,189,248,.14);
   --green: #22c55e; --green-soft: rgba(34,197,94,.16);
   --amber: #f59e0b; --amber-soft: rgba(245,158,11,.16);
   --purple: #a855f7; --purple-soft: rgba(168,85,247,.16);
 }}
 * {{ box-sizing: border-box; }}
 body {{
   margin: 0; font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
   background: var(--bg); color: var(--text); line-height: 1.5;
 }}
 .wrap {{ max-width: 1280px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }}
 header {{
   display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end;
   gap: 1rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border);
 }}
 h1 {{ margin: 0; font-size: 1.65rem; font-weight: 700; letter-spacing: -0.02em; }}
 .subtitle {{ color: var(--muted); font-size: .92rem; margin-top: .25rem; }}
 .updated {{
   background: var(--panel); border: 1px solid var(--border); padding: .45rem .85rem;
   border-radius: 999px; font-size: .82rem; color: var(--muted);
 }}
 .kpis {{
   display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
   gap: 1rem; margin: 1.5rem 0;
 }}
 .kpi {{
   background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
   padding: 1rem 1.2rem;
 }}
 .kpi .label {{ color: var(--muted); font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; }}
 .kpi .val {{ font-size: 1.8rem; font-weight: 700; margin-top: .2rem; }}
 .kpi.green .val {{ color: var(--green); }}
 .kpi.amber .val {{ color: var(--amber); }}
 .kpi.accent .val {{ color: var(--accent); }}

 .toolbar {{
   display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; justify-content: space-between;
   background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
   padding: .85rem 1rem; margin-bottom: 1.25rem;
 }}
 .tabs {{ display: flex; gap: .4rem; flex-wrap: wrap; }}
 .tab {{
   background: transparent; color: var(--muted); border: 1px solid var(--border);
   padding: .45rem .9rem; border-radius: 8px; cursor: pointer; font-size: .88rem; font-weight: 600;
   transition: all .15s;
 }}
 .tab:hover {{ color: var(--text); border-color: var(--accent); }}
 .tab.active {{ background: var(--accent-soft); color: var(--accent); border-color: var(--accent); }}
 .controls {{ display: flex; gap: .6rem; flex-wrap: wrap; align-items: center; flex: 1; justify-content: flex-end; }}
 input[type="search"], select {{
   background: var(--bg); color: var(--text); border: 1px solid var(--border);
   padding: .5rem .85rem; border-radius: 8px; font-size: .88rem; outline: none;
 }}
 input[type="search"] {{ min-width: 260px; }}
 input[type="search"]:focus, select:focus {{ border-color: var(--accent); }}

 .table-wrap {{
   background: var(--panel); border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
 }}
 table {{ border-collapse: collapse; width: 100%; }}
 th, td {{ padding: .85rem 1rem; text-align: left; vertical-align: top; border-bottom: 1px solid var(--border); }}
 th {{
   background: rgba(15,23,42,.55); color: var(--muted); font-size: .78rem;
   text-transform: uppercase; letter-spacing: .06em; cursor: pointer; user-select: none;
   white-space: nowrap;
 }}
 th:hover {{ color: var(--text); }}
 tbody tr {{ transition: background .12s; }}
 tbody tr:hover {{ background: var(--panel-hover); }}
 tbody tr:last-child td {{ border-bottom: none; }}

 .score {{
   display: inline-flex; align-items: center; justify-content: center;
   min-width: 44px; padding: .25rem .55rem; border-radius: 8px; font-weight: 700; font-size: .9rem;
 }}
 .score.high {{ background: var(--green-soft); color: var(--green); border: 1px solid rgba(34,197,94,.35); }}
 .score.mid {{ background: var(--accent-soft); color: var(--accent); border: 1px solid rgba(56,189,248,.35); }}
 .score.low {{ background: var(--amber-soft); color: var(--amber); border: 1px solid rgba(245,158,11,.35); }}

 .job-title {{
   color: var(--text); font-weight: 600; font-size: .98rem; text-decoration: none;
 }}
 .job-title:hover {{ color: var(--accent); text-decoration: underline; }}
 .badge-new {{
   display: inline-block; margin-left: .45rem; padding: .1rem .45rem; border-radius: 999px;
   font-size: .7rem; font-weight: 700; background: var(--green-soft); color: var(--green);
   border: 1px solid rgba(34,197,94,.4); vertical-align: middle;
 }}
 .badge-status {{
   display: inline-block; margin-left: .4rem; padding: .1rem .45rem; border-radius: 999px;
   font-size: .7rem; font-weight: 600; background: var(--amber-soft); color: var(--amber);
   vertical-align: middle;
 }}
 .chips {{ display: flex; flex-wrap: wrap; gap: .3rem; margin-top: .45rem; }}
 .chip {{
   font-size: .74rem; padding: .12rem .5rem; border-radius: 6px;
   background: rgba(148,163,184,.12); color: var(--muted); border: 1px solid rgba(148,163,184,.2);
 }}
 .chip.skill {{ background: var(--accent-soft); color: var(--accent); border-color: rgba(56,189,248,.28); }}
 .chip.title-kw {{ background: var(--purple-soft); color: #d8b4fe; border-color: rgba(168,85,247,.3); }}
 .company {{ font-weight: 600; color: var(--text); }}
 .source-tag {{
   display: inline-block; margin-top: .25rem; font-size: .72rem; color: var(--muted);
   background: rgba(15,23,42,.6); padding: .1rem .45rem; border-radius: 4px; text-transform: uppercase;
 }}
 .loc {{ color: var(--text); font-size: .9rem; }}
 .date {{ color: var(--muted); font-size: .85rem; white-space: nowrap; }}
 .apply-btn {{
   display: inline-block; padding: .38rem .75rem; border-radius: 7px; font-size: .82rem;
   font-weight: 600; color: var(--accent); background: var(--accent-soft);
   border: 1px solid rgba(56,189,248,.3); text-decoration: none; white-space: nowrap;
 }}
 .apply-btn:hover {{ background: var(--accent); color: #0f172a; }}
 .empty {{ text-align: center; padding: 3rem; color: var(--muted); }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Embedded &amp; Real-Time Job Tracker</h1>
      <div class="subtitle">Tel Aviv &amp; Israel · C / C++ / RTOS / Firmware / Avionics · Mid-Level (3–6 yrs)</div>
    </div>
    <div class="updated">Last checked: <b>{updated}</b></div>
  </header>

  <section class="kpis">
    <div class="kpi green"><div class="label">Strong Matches (≥50)</div><div class="val">{match_count}</div></div>
    <div class="kpi accent"><div class="label">New This Run</div><div class="val">{new_count}</div></div>
    <div class="kpi amber"><div class="label">Borderline (30–49)</div><div class="val">{border_count}</div></div>
    <div class="kpi"><div class="label">Total Active Scanned</div><div class="val">{total_scanned}</div></div>
  </section>

  <div class="toolbar">
    <div class="tabs">
      <button class="tab active" onclick="setTab('match', this)">Matches ({match_count})</button>
      <button class="tab" onclick="setTab('borderline', this)">Borderline ({border_count})</button>
      <button class="tab" onclick="setTab('all', this)">All ({all_count})</button>
    </div>
    <div class="controls">
      <select id="companyFilter" onchange="applyFilters()">
        <option value="">All companies</option>
        {company_options}
      </select>
      <input type="search" id="q" placeholder="Search title, skill (VxWorks, RTOS, C++), city..." oninput="applyFilters()">
    </div>
  </div>

  <div class="table-wrap">
    <table id="t">
      <thead>
        <tr>
          <th onclick="sortTable(0, true)">Score ↕</th>
          <th onclick="sortTable(1, false)">Role &amp; Matched Signals ↕</th>
          <th onclick="sortTable(2, false)">Company ↕</th>
          <th onclick="sortTable(3, false)">Location ↕</th>
          <th onclick="sortTable(4, false)">First Seen ↕</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>
</div>

<script>
let currentTab = 'match';
function setTab(tab, btn) {{
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}
function applyFilters() {{
  const q = document.getElementById('q').value.toLowerCase();
  const comp = document.getElementById('companyFilter').value.toLowerCase();
  for (const r of document.querySelectorAll('#t tbody tr[data-status]')) {{
    const st = r.getAttribute('data-status');
    const rc = r.getAttribute('data-company');
    const tabOk = (currentTab === 'all') || (st === currentTab);
    const compOk = !comp || rc === comp;
    const textOk = !q || r.innerText.toLowerCase().includes(q);
    r.style.display = (tabOk && compOk && textOk) ? '' : 'none';
  }}
}}
let dir = -1;
function sortTable(c, num) {{
  const b = document.querySelector('#t tbody');
  dir = -dir;
  [...b.querySelectorAll('tr[data-status]')].sort((a, z) => {{
    let x = a.cells[c].innerText.trim(), y = z.cells[c].innerText.trim();
    return (num ? (parseFloat(x) - parseFloat(y)) : x.localeCompare(y)) * dir;
  }}).forEach(r => b.appendChild(r));
}}
applyFilters();
</script>
</body>
</html>
"""


def _chips(reasons_str: str) -> str:
    e = html.escape
    out = []
    for part in (reasons_str or "").split("; "):
        if part.startswith("title: "):
            for kw in part[7:].split(", "):
                out.append(f'<span class="chip title-kw">{e(kw)}</span>')
        elif part.startswith("skills: "):
            for kw in part[8:].split(", "):
                out.append(f'<span class="chip skill">{e(kw)}</span>')
        elif part:
            out.append(f'<span class="chip">{e(part)}</span>')
    return "".join(out)


def _row(m, new_ids: set[str]) -> str:
    e = html.escape
    score = int(m["score"] or 0)
    tier = "high" if score >= 70 else ("mid" if score >= 50 else "low")
    status = m["status"] or "match"
    badge_new = '<span class="badge-new">NEW</span>' if m["id"] in new_ids else ""
    badge_border = '<span class="badge-status">BORDERLINE</span>' if status == "borderline" else ""
    url = e(m["url"] or "#", quote=True)
    comp = m["company"] or ""
    return (
        f'<tr data-status="{e(status)}" data-company="{e(comp.lower())}">'
        f'<td><span class="score {tier}">{score}</span></td>'
        f'<td><a class="job-title" href="{url}" target="_blank" rel="noopener">{e(m["title"] or "")}</a>'
        f'{badge_new}{badge_border}'
        f'<div class="chips">{_chips(m["reasons"] or "")}</div></td>'
        f'<td><div class="company">{e(comp)}</div><span class="source-tag">{e(m["source"] or "")}</span></td>'
        f'<td class="loc">{e(m["location"] or "")}</td>'
        f'<td class="date">{e((m["first_seen"] or "")[:10])}</td>'
        f'<td><a class="apply-btn" href="{url}" target="_blank" rel="noopener">Open ↗</a></td>'
        f'</tr>'
    )


def render(matches, new_ids: set[str] | None = None, borderline=None, total_scanned: int = 0) -> str:
    new_ids = new_ids or set()
    borderline = list(borderline or [])
    matches = list(matches or [])
    all_items = matches + borderline
    companies = sorted({(m["company"] or "") for m in all_items if m["company"]})
    company_options = "\n".join(
        f'<option value="{html.escape(c.lower())}">{html.escape(c)}</option>' for c in companies
    )
    rows = "\n".join(_row(m, new_ids) for m in all_items)
    if not rows:
        rows = '<tr><td colspan="6" class="empty">No matching jobs yet.</td></tr>'
    return TEMPLATE.format(
        updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        match_count=len(matches),
        new_count=len(new_ids),
        border_count=len(borderline),
        all_count=len(all_items),
        total_scanned=total_scanned or len(all_items),
        company_options=company_options,
        rows=rows,
    )


def write(path: Path, matches, new_ids: set[str] | None = None, borderline=None, total_scanned: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(matches, new_ids, borderline, total_scanned), encoding="utf-8")
