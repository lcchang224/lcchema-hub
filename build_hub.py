#!/usr/bin/env python3
"""
build_hub.py
============
Fetch latest.json from digest.lcchema.cc and report.lcchema.cc,
render public/index.html — the lcchema.cc landing page.

If a manifest fetch fails, fall back to public/cache/<name>.json from
the previous successful build so the page never goes blank.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"
CACHE = PUBLIC / "cache"
PUBLIC.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)

GH_OWNER = "lcchang224"
SOURCES = {
    "digest": f"https://raw.githubusercontent.com/{GH_OWNER}/hema-onc-digest/main/manifests/latest.json",
    "report": f"https://raw.githubusercontent.com/{GH_OWNER}/hematology-uptodate/main/manifests/latest.json",
}


def fetch(name: str, url: str) -> dict:
    """Fetch manifest from raw.githubusercontent.com. No retry needed — raw.gh
    reflects the latest commit instantly, so there's no CF-Pages build lag.
    Falls back to cached copy if the request fails."""
    cache_path = CACHE / f"{name}.json"
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True)
        r.raise_for_status()
        data = r.json()
        cache_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [ok]   {name}: fetched + cached")
        return data
    except Exception as exc:
        print(f"  [warn] {name}: fetch failed ({exc}); using cache")
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))
        return {}


def render_digest_card(item: dict) -> str:
    date = item.get("date", "")
    url = item.get("url", "#")
    return f'<a class="card" href="{url}"><span class="card-date">{date}</span><span class="card-arrow">→</span></a>'


def render_report_card(week: dict) -> str:
    w = week.get("week", "")
    mal = week.get("malignant_url", "")
    ben = week.get("benign_url", "")
    return (
        f'<div class="card-week">'
        f'<span class="card-date">{w}</span>'
        f'<div class="card-links">'
        f'<a class="track malignant" href="{mal}">Malignant</a>'
        f'<a class="track benign" href="{ben}">Benign</a>'
        f'</div></div>'
    )


def render_index(digest_data: dict, report_data: dict) -> str:
    digests = digest_data.get("items", [])[:5]
    weeks = report_data.get("weeks", [])[:3]
    digest_html = "".join(render_digest_card(i) for i in digests) or '<p class="empty">No digests yet.</p>'
    report_html = "".join(render_report_card(w) for w in weeks) or '<p class="empty">No reports yet.</p>'

    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    css = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#fafafa;--surface:#fff;--border:#e0e0e0;--text:#212121;--muted:#757575;
--accent:#37474f;--accent2:#00838f;--mal:#1a237e;--mal-a:#b71c1c;
--ben:#1b5e20;--ben-a:#e65100;--dig:#a04a1c;--dig-a:#bf6433;--radius:10px}
@media (prefers-color-scheme:dark){:root{--bg:#121212;--surface:#1e1e1e;--border:#333;
--text:#e0e0e0;--muted:#9e9e9e;--accent:#90a4ae;--accent2:#4dd0e1;
--mal:#7986cb;--mal-a:#ef5350;--ben:#81c784;--ben-a:#ffb74d;--dig:#d49374;--dig-a:#bf8362}}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
background:var(--bg);color:var(--text);line-height:1.6;font-size:16px;min-height:100vh}
.wrap{max-width:780px;margin:0 auto;padding:2.5rem 1.25rem 3rem}
header{margin-bottom:2.5rem;text-align:center}
header h1{font-size:1.6rem;font-weight:700;letter-spacing:-.01em;color:var(--accent)}
header p{color:var(--muted);font-size:.9rem;margin-top:.4rem}
section{margin-bottom:2.25rem}
.section-head{display:flex;align-items:baseline;gap:.6rem;margin-bottom:.9rem;
padding-bottom:.4rem;border-bottom:2px solid var(--accent2)}
.section-head h2{font-size:1.05rem;font-weight:700;color:var(--accent)}
.section-head .sub{font-size:.78rem;color:var(--muted)}
.cards{display:flex;flex-direction:column;gap:.55rem}
.card,.card-week{background:var(--surface);border:1px solid var(--border);
border-radius:var(--radius);padding:.85rem 1rem;display:flex;align-items:center;
justify-content:space-between;text-decoration:none;color:var(--text);
transition:transform .12s,box-shadow .12s,border-color .12s}
.card:hover{border-color:var(--dig);transform:translateY(-1px);
box-shadow:0 2px 8px rgba(0,0,0,.06)}
.card-date{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
font-weight:600;font-size:.95rem;color:var(--dig)}
section.reports .card-date{color:var(--accent)}
.card-arrow{color:var(--muted);font-size:1.1rem}
.card-links{display:flex;gap:.5rem}
.track{font-size:.82rem;font-weight:600;padding:.3rem .7rem;border-radius:6px;
text-decoration:none;border:1px solid;transition:background .12s}
.track.malignant{color:var(--mal);border-color:var(--mal)}
.track.malignant:hover{background:var(--mal);color:#fff}
.track.benign{color:var(--ben);border-color:var(--ben)}
.track.benign:hover{background:var(--ben);color:#fff}
.empty{color:var(--muted);font-style:italic;font-size:.9rem;padding:.5rem 0}
footer{margin-top:3rem;text-align:center;color:var(--muted);font-size:.75rem}
footer a{color:var(--accent2);text-decoration:none}
footer a:hover{text-decoration:underline}
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>lcchema.cc — Hematology Hub</title>
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🩸 Hematology Hub</h1>
    <p>Daily digest &middot; Weekly reports &middot; NCKUH Hematology</p>
  </header>

  <section class="digests">
    <div class="section-head">
      <h2>📰 Daily Digest</h2>
      <span class="sub">latest 5</span>
    </div>
    <div class="cards">{digest_html}</div>
  </section>

  <section class="reports">
    <div class="section-head">
      <h2>📋 Weekly Report</h2>
      <span class="sub">latest 3 weeks &middot; malignant &amp; benign tracks</span>
    </div>
    <div class="cards">{report_html}</div>
  </section>

  <footer>
    Built {built} &middot;
    <a href="https://digest.lcchema.cc">digest archive</a> &middot;
    <a href="https://report.lcchema.cc">report archive</a>
  </footer>
</div>
</body>
</html>"""


def main():
    print("Fetching source manifests:")
    digest_data = fetch("digest", SOURCES["digest"])
    report_data = fetch("report", SOURCES["report"])

    html = render_index(digest_data, report_data)
    (PUBLIC / "index.html").write_text(html, encoding="utf-8")
    n_d = len(digest_data.get("items", []))
    n_r = len(report_data.get("weeks", []))
    print(f"\nWrote public/index.html  (digests: {n_d}, report weeks: {n_r})")


if __name__ == "__main__":
    main()
