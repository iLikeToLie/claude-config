"""Render a project-overview fact sheet (JSON) into a dated HTML snapshot.

Usage: python render.py facts.json [--no-open]
Writes ~/project-overviews/<project>/<YYYY-MM-DD_HHMM>-<scope>.html and opens it.
Every key except "project" and "answer" is optional; empty sections are skipped.
"""
import html
import json
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

E = html.escape
HERE = Path(__file__).parent
FONTS = ("https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700"
         "&family=Atkinson+Hyperlegible:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap")
DOT = {"done": "✓", "now": "●", "next": ""}
CELL = {"pass": "✓", "short": "✗", "untested": "–"}
RISK = {"block": ("c-risk", "■ Blocked"), "risk": ("c-warn", "▲ Risk"), "inv": ("c-info", "◆ Checking")}
SCRIPT = """<script>
document.querySelectorAll('.opts').forEach(g => g.addEventListener('click', e => {
  const b = e.target.closest('.opt'); if (!b) return;
  const on = b.getAttribute('aria-pressed') !== 'true';
  g.querySelectorAll('.opt').forEach(o => o.setAttribute('aria-pressed', 'false'));
  b.setAttribute('aria-pressed', String(on));
}));
const btn = document.querySelector('.copy');
if (btn) btn.addEventListener('click', () => {
  const lines = [...document.querySelectorAll('[data-q]')].map(d => {
    const p = d.querySelector('.opt[aria-pressed="true"]');
    return p ? d.dataset.q + ' -> ' + p.dataset.v : null;
  }).filter(Boolean);
  const text = lines.length ? 'My choices:\\n' + lines.join('\\n') : '';
  const note = document.querySelector('.copied');
  if (!text) { note.textContent = 'Pick at least one option first.'; return; }
  const fallback = () => { let t = document.querySelector('textarea.fallback');
    if (!t) { t = document.createElement('textarea'); t.className = 'fallback'; t.rows = 4; btn.parentNode.after(t); }
    t.value = text; t.select(); note.textContent = 'Press Ctrl+C, then paste into the chat.'; };
  try { navigator.clipboard.writeText(text).then(() => { note.textContent = 'Copied. Paste it into the chat.'; }, fallback); }
  catch (_) { fallback(); }
});
</script>"""


def head(f, key, label):
    take = f.get("heads", {}).get(key)
    h2 = f"<h2>{E(take)}</h2>" if take else ""
    return f'<div class="sec-head"><span class="caps">{E(label)}</span>{h2}</div>'


def section(f, key, label, body):
    return f"<section>{head(f, key, label)}{body}</section>" if body else ""


def more(text):
    return f'<details class="more"><summary>more</summary><p>{E(text)}</p></details>' if text else ""


def kpis(f):
    out = []
    for k in f.get("kpis", []):
        val, of = k["value"], k.get("of")
        pct = max(0, min(100, 100 * float(val) / float(of))) if of else None
        bar = f'<div class="bar"><i style="width:{pct:.0f}%"></i></div>' if pct is not None else ""
        of_txt = f" <small>/ {E(str(of))}</small>" if of else ""
        out.append(f'<div class="kpi{" key" if k.get("key") else ""}"><span class="caps">{E(k["label"])}</span>'
                   f'<span class="v">{E(str(val))}{E(k.get("unit", ""))}{of_txt}</span>{bar}'
                   f'<span class="n">{E(k.get("note", ""))}</span></div>')
    return f'<div class="kpis">{"".join(out)}</div>' if out else ""


def journey(f):
    steps = []
    for s in f.get("journey", []):
        st = s.get("status", "next")
        here = '<span class="here">YOU ARE HERE</span>' if st == "now" else ""
        steps.append(f'<li class="step {E(st)}"><span class="dot">{DOT.get(st, "")}</span>{here}'
                     f'<span class="label">{E(s["label"])}</span><span class="sub">{E(s.get("sub", ""))}</span></li>')
    if not steps:
        return ""
    parked = f'<p class="parked"><b>On hold:</b> {E(f["parked"])}</p>' if f.get("parked") else ""
    cap = f'<figcaption>{E(f["journey_caption"])}</figcaption>' if f.get("journey_caption") else ""
    return (f'<figure><div class="stage"><ol class="track">{"".join(steps)}</ol></div>{cap}</figure>'
            '<div class="key-row"><span>✓ done</span><span>● in progress</span><span>◌ later</span></div>' + parked)


def branch(f):
    b = f.get("branch")
    if not b:
        return ""
    steps = "".join(f'<li class="{E(s.get("status", "next"))}">{E(s["label"])}</li>' for s in b.get("steps", []))
    wait = (f'<p><span class="chip c-warn">▲ Blocks finishing</span> {E(b["waiting"])}</p>'
            if b.get("waiting") else "")
    meta = " · ".join(E(x) for x in (b.get("name"), b.get("ahead")) if x)
    return (f'<figure><span class="meta">{meta}</span><p>{E(b.get("purpose", ""))}</p>'
            f'<ol class="chain">{steps}</ol></figure>{wait}')


def now(f):
    items = "".join(f'<li><div class="body"><p>{E(x)}</p></div></li>' for x in f.get("now", []))
    return f'<ul class="rows plain">{items}</ul>' if items else ""


def scoreboard(f):
    s = f.get("scoreboard")
    if not s:
        return ""
    cells = "".join(
        f'<div class="cell {E(c.get("status", "untested"))}{" key" if c.get("key") else ""}">'
        f'<span class="h">{E(c["label"])}</span><span class="g">{CELL.get(c.get("status"), "–")}</span>'
        f'<span class="r">{E(c.get("note", c.get("status", "")))}</span></div>' for c in s["cells"])
    axis = f'<span class="axis">{E(s["axis"])}</span>' if s.get("axis") else ""
    return (f'<figure><div class="scroll"><div class="cells">{cells}</div></div>{axis}'
            f'<figcaption>{E(s.get("caption", ""))}</figcaption></figure>')


def decisions(f):
    ds = f.get("decisions")
    if ds is None:
        return ""
    if not ds:
        return "<p>Nothing is waiting on you right now.</p>"
    rows = []
    for n, d in enumerate(ds, 1):
        opts = "".join(
            f'<button type="button" class="opt{" rec" if i == d.get("rec") else ""}" aria-pressed="false" '
            f'data-v="{E(o)}">{E(o)}</button>' for i, o in enumerate(d.get("options", [])))
        rows.append(f'<li data-q="{E(d["q"])}"><span class="chip c-dim">Decision {n}</span><div class="body">'
                    f'<p class="q">{E(d["q"])}</p><p class="why">{E(d.get("why", ""))}</p>'
                    f'<div class="opts">{opts}</div>{more(d.get("more"))}</div></li>')
    return (f'<ol class="rows">{"".join(rows)}</ol><div class="copybar">'
            '<button type="button" class="copy">Copy my choices</button>'
            '<span class="copied">Pick options, then paste them into the chat.</span></div>')


def risks(f):
    rows = []
    for r in f.get("risks", []):
        cls, label = RISK.get(r.get("kind", "risk"), RISK["risk"])
        rows.append(f'<li><span class="chip {cls}">{label}</span><div class="body"><p>{E(r["text"])}</p>'
                    f'{more(r.get("more"))}</div></li>')
    return f'<ul class="rows">{"".join(rows)}</ul>' if rows else ""


def recent(f):
    items = f.get("recent", [])
    if not items:
        return ""
    groups = {}
    for r in items:
        groups.setdefault(r.get("theme", ""), []).append(r)
    out = []
    for theme, rs in groups.items():
        rows = "".join(f'<li><span class="d">{E(r["date"])}</span><div class="body"><p>{E(r["what"])} '
                       f'<span class="o">{E(r.get("outcome", ""))}</span></p></div></li>' for r in rs)
        label = f'<span class="caps">{E(theme)}</span>' if theme else ""
        out.append(f'<div class="tl-group">{label}<ol class="rows">{rows}</ol></div>')
    return "".join(out)


def glossary(f):
    if not f.get("glossary"):
        return ""
    rows = "".join(f"<dt>{E(t)}</dt><dd>{E(m)}</dd>" for t, m in f["glossary"])
    return f'<section><details class="box"><summary>Glossary</summary><dl>{rows}</dl></details></section>'


def sources(f):
    rows = "".join(f"<li>{E(s)}</li>" for s in f.get("sources", []))
    return f'<ul class="sources">{rows}</ul>' if rows else ""


def render(f):
    scope = f.get("scope", "project")
    goal = f'<p class="goal"><b>Goal:</b> {E(f["goal"])}</p>' if f.get("goal") else ""
    sb = f.get("scoreboard", {})
    parts = [
        f'<header><span class="caps">{E(f["project"])} · {E(scope)} overview · {E(f.get("asof", ""))}</span>'
        f'<h1>{E(f["answer"])}</h1>{goal}</header>',
        kpis(f),
        section(f, "journey", "The journey", journey(f)),
        section(f, "branch", "This chat" if scope == "chat" else "This branch", branch(f)),
        section(f, "now", "Right now", now(f)),
        section(f, "scoreboard", sb.get("title", "Scoreboard"), scoreboard(f)),
        section(f, "decisions", "Waiting on you", decisions(f)),
        section(f, "risks", "Blockers & risks", risks(f)),
        section(f, "recent", "Recent activity", recent(f)),
        glossary(f),
        section(f, "sources", "Sources", sources(f)),
    ]
    css = (HERE / "style.css").read_text(encoding="utf-8")
    hue = float(f.get("hue", 200))
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,">'
            f'<title>{E(f["project"])} {E(scope)} overview</title>'
            f'<link rel="stylesheet" href="{FONTS}"><style>:root{{--hue:{hue}}}\n{css}</style></head>'
            f'<body><div class="wrap">{"".join(p for p in parts if p)}</div>{SCRIPT}</body></html>')


if __name__ == "__main__":
    facts = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out = Path.home() / "project-overviews" / facts["project"] / f"{stamp}-{facts.get('scope', 'project')}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(facts), encoding="utf-8")
    print(out)
    if "--no-open" not in sys.argv:
        webbrowser.open(out.as_uri())
