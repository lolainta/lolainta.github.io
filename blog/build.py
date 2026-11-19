#!/usr/bin/env python3
"""Build the blog: posts/*.md -> blog/<slug>/index.html, blog/index.html, blog/feed.xml.

Also rewrites sitemap.xml and the recent-posts strip in index.html (between the
<!-- recent-posts --> markers). Python 3 stdlib only; run from anywhere:

    python3 blog/build.py
"""
import sys
import datetime as dt
import email.utils
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS, OUT = ROOT / "posts", ROOT / "blog"
SITE = "https://lolainta.tw"


# ---- front matter ---------------------------------------------------------
# ponytail: flat "key: value" YAML subset (strings, [a, b] lists, true/false); posts need nothing more

def parse_post(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SystemExit(f"{path}: missing front matter")
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
        elif val in ("true", "false"):
            val = val == "true"
        else:
            val = val.strip("\"'")
        meta[key.strip()] = val
    for k in ("title", "date"):
        if k not in meta:
            raise SystemExit(f"{path}: front matter needs '{k}'")
    meta["date"] = dt.date.fromisoformat(str(meta["date"]))
    meta.setdefault("tags", [])
    meta["draft"] = meta.get("draft") is True
    meta["slug"] = path.stem
    meta["body"] = md_to_html(text[m.end():])
    return meta


# ---- markdown -------------------------------------------------------------
# ponytail: tiny converter for what the posts use: headings, paragraphs, one-level lists,
# links, images, inline code, bold/italic, code fences, tables, blockquotes. No nesting beyond that.

def attr(s):
    return s.replace('"', "&quot;")  # text is already escaped (quote=False); only quotes remain


def inline(s):
    parts = re.split(r"(`[^`]+`)", s)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append("<code>" + html.escape(p[1:-1]) + "</code>")
            continue
        p = html.escape(p, quote=False)
        p = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                   lambda m: f'<img src="{attr(m[2])}" alt="{attr(m[1])}" loading="lazy">', p)
        p = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{attr(m[2])}">{m[1]}</a>', p)
        p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
        p = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", p)
        out.append(p)
    return "".join(out)


LIST_RE = re.compile(r"^([-*]|\d+\.)\s+")


def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def md_to_html(text):
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("```"):
            lang = line[3:].strip()
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            cls = f' class="language-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1
        elif m := re.match(r"(#{1,6})\s+(.*)", line):
            n = len(m[1])
            out.append(f"<h{n}>{inline(m[2].strip())}</h{n}>")
            i += 1
        elif line.startswith(">"):
            j = i
            while j < len(lines) and lines[j].startswith(">"):
                j += 1
            inner = "\n".join(re.sub(r"^> ?", "", l) for l in lines[i:j])
            out.append("<blockquote>" + md_to_html(inner) + "</blockquote>")
            i = j
        elif line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            head = cells(line)
            j, rows = i + 2, []
            while j < len(lines) and lines[j].startswith("|"):
                rows.append(cells(lines[j]))
                j += 1
            t = ["<div class=\"table\"><table><thead><tr>"]
            t += [f"<th>{inline(c)}</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            i = j
        elif m := LIST_RE.match(line):
            tag = "ol" if m[1][0].isdigit() else "ul"
            items = []
            while i < len(lines) and lines[i].strip():
                if LIST_RE.match(lines[i]):
                    items.append(LIST_RE.sub("", lines[i]))
                elif items:
                    items[-1] += " " + lines[i].strip()  # indented continuation line
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
        else:
            j = i
            while j < len(lines) and lines[j].strip() and not re.match(r"(```|#{1,6}\s|>|\|)", lines[j]) \
                    and not LIST_RE.match(lines[j]):
                j += 1
            out.append("<p>" + inline("\n".join(lines[i:j])) + "</p>")
            i = j
    return "\n".join(out)


# ---- templates ------------------------------------------------------------

def t(en, zh):
    """A label that follows the site's EN / 中文 toggle."""
    return f'<span class="t" lang="en">{en}</span><span class="t" lang="zh-Hant">{zh}</span>'


DRAFT = '<span class="draft">草稿</span>'

HEAD = """<!doctype html>
<html lang="zh-Hant" data-lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
{robots}<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{site}/avatar.jpg">
<meta property="og:type" content="{ogtype}">
<link rel="alternate" type="application/rss+xml" title="LolaInTa 的文章" href="/blog/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;700;800&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/blog/blog.css">
<script>
// same language pick as the home page: ?lang=, then the last choice, then the browser
(() => {{ let l = new URLSearchParams(location.search).get('lang');
  if (l !== 'zh' && l !== 'en') {{ l = null; try {{ l = localStorage.getItem('lang'); }} catch {{}} }}
  l = l || (navigator.language.startsWith('zh') ? 'zh' : 'en');
  document.documentElement.dataset.lang = l; document.documentElement.lang = l === 'zh' ? 'zh-Hant' : 'en'; }})();
</script>
</head>
<body>
<button class="lang" id="lang" type="button" aria-label="Switch language / 切換語言"><span class="l-en">EN</span><span class="l-zh">中文</span></button>
<div class="wrap">
<header class="top">
  <a class="home" href="/"><img src="/avatar.jpg" width="40" height="40" alt="">Cheng-Liang Chi<span class="zh-name">紀政良</span></a>
  <nav class="site" aria-label="Site">
    <a href="/">{home}</a>
    <a href="/blog/"{posts_on}>{posts}</a>
    <!-- ponytail: hidden until /world/ is deployed; uncomment then <a href="/world/">{world}</a> -->
  </nav>
</header>
<main>
"""

FOOT = """</main>
<footer>© {year} Cheng-Liang Chi · <a href="/blog/feed.xml">RSS</a></footer>
</div>
<script>
// ponytail: same two-language toggle as the home page
const root = document.documentElement;
document.getElementById('lang').onclick = () => {
  const l = root.dataset.lang === 'zh' ? 'en' : 'zh';
  root.dataset.lang = l; root.lang = l === 'zh' ? 'zh-Hant' : 'en';
  try { localStorage.setItem('lang', l); } catch {}
  const u = new URL(location.href); u.searchParams.set('lang', l); history.replaceState(null, '', u);
};
</script>
</body>
</html>
"""


def page(title, desc, url, body, ogtype="website", noindex=False, posts_on=False):
    head = HEAD.format(
        title=html.escape(title), desc=html.escape(desc), url=url, site=SITE, ogtype=ogtype,
        robots='<meta name="robots" content="noindex">\n' if noindex else "",
        home=t("Home", "首頁"), posts=t("Posts", "文章"), world=t("World", "世界"),
        posts_on=' aria-current="page"' if posts_on else "")
    return head + body + FOOT.replace("{year}", str(dt.date.today().year))


def tag_list(p):
    return "".join(f"<li>{html.escape(x)}</li>" for x in p["tags"])


def render_post(p):
    meta = f'<time datetime="{p["date"]}">{p["date"]}</time>' + (DRAFT if p["draft"] else "")
    body = (f'<article class="post" lang="zh-Hant">\n<header>\n<h1>{html.escape(p["title"])}</h1>\n'
            f'<div class="meta">{meta}</div>\n<ul class="pills">{tag_list(p)}</ul>\n</header>\n'
            f'{p["body"]}\n</article>\n'
            f'<p class="back"><a href="/blog/">← {t("All posts", "所有文章")}</a></p>\n')
    return page(p["title"] + " · LolaInTa", p.get("summary", ""), f'{SITE}/blog/{p["slug"]}/',
                body, ogtype="article", noindex=p["draft"])


def render_index(posts):
    items = []
    for p in posts:
        items.append(
            f'<li class="entry"><div class="when"><time datetime="{p["date"]}">{p["date"]}</time></div><div>'
            f'<h3><a href="/blog/{p["slug"]}/">{html.escape(p["title"])}</a>{DRAFT if p["draft"] else ""}</h3>'
            f'<p lang="zh-Hant">{html.escape(p.get("summary", ""))}</p>'
            f'<ul class="pills">{tag_list(p)}</ul></div></li>')
    body = (f'<h1 class="list-title">{t("Posts", "文章")}</h1>\n'
            f'<p class="lede">{t("Notes on things I build and run. Mostly in Traditional Chinese.", "做過、維運過的東西的紀錄。")}</p>\n'
            f'<ol class="entries">\n' + "\n".join(items) + "\n</ol>\n")
    return page("文章 · LolaInTa", "Cheng-Liang Chi（紀政良）的文章", f"{SITE}/blog/", body, posts_on=True)


def render_feed(posts):
    items = []
    for p in posts:
        if p["draft"]:
            continue  # drafts are built for preview but not syndicated
        when = dt.datetime.combine(p["date"], dt.time(12), dt.timezone(dt.timedelta(hours=8)))
        url = f'{SITE}/blog/{p["slug"]}/'
        items.append(f"""  <item>
    <title>{html.escape(p["title"])}</title>
    <link>{url}</link>
    <guid>{url}</guid>
    <pubDate>{email.utils.format_datetime(when)}</pubDate>
    <description>{html.escape(p.get("summary", ""))}</description>
  </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>LolaInTa 的文章</title>
  <link>{SITE}/blog/</link>
  <description>Cheng-Liang Chi（紀政良）的文章</description>
  <language>zh-TW</language>
{chr(10).join(items)}
</channel>
</rss>
"""


def render_sitemap(posts):
    urls = [f"{SITE}/", f"{SITE}/blog/"] + [f'{SITE}/blog/{p["slug"]}/' for p in posts if not p["draft"]]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>\n")


def update_home(posts):
    path = ROOT / "index.html"
    src = path.read_text(encoding="utf-8")
    start, end = "<!-- recent-posts -->", "<!-- /recent-posts -->"
    if start not in src or end not in src:
        raise SystemExit("index.html: recent-posts markers not found")
    lis = "".join(
        f'<li><a href="/blog/{p["slug"]}/">{html.escape(p["title"])}</a>{DRAFT if p["draft"] else ""}'
        f' <span class="when">{p["date"]}</span></li>' for p in posts[:3])
    block = (f'{start}\n  <div class="recent">\n    <h3><span lang="en">Recent posts</span><span lang="zh-Hant">最近文章</span></h3>\n'
             f'    <ul>{lis}</ul>\n  </div>\n  {end}')
    a, b = src.index(start), src.index(end) + len(end)
    path.write_text(src[:a] + block + src[b:], encoding="utf-8")


def main():
    posts = sorted((parse_post(f) for f in POSTS.glob("*.md")), key=lambda p: (p["date"], p["slug"]), reverse=True)
    if "--drafts" not in sys.argv:  # drafts are local-preview only; nothing published links to them
        posts = [p for p in posts if not p["draft"]]
    for p in posts:
        d = OUT / p["slug"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(render_post(p), encoding="utf-8")
    (OUT / "index.html").write_text(render_index(posts), encoding="utf-8")
    (OUT / "feed.xml").write_text(render_feed(posts), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(render_sitemap(posts), encoding="utf-8")
    update_home(posts)
    drafts = sum(p["draft"] for p in posts)
    print(f"built {len(posts)} post(s) ({drafts} draft) -> blog/")


if __name__ == "__main__":
    main()
