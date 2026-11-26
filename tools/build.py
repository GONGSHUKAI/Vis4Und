#!/usr/bin/env python3
"""Build the Vis4Und site from catalog.json.

  python3 tools/build.py              # whole site: every page + index.html + README list + link check
  python3 tools/build.py --page SLUG  # only pages/SLUG/index.html (safe while others edit their own pages)

For each page it fills three marker blocks (never hand-edit their contents):
  <!-- v4u:head --> ... <!-- /v4u:head -->   shared <head>: fonts, KaTeX, assets/v4u.css, assets/v4u.js
  <!-- v4u:nav -->  ... <!-- /v4u:nav -->    top strip: home / section / sibling pages / theme toggle
  <!-- v4u:foot --> ... <!-- /v4u:foot -->   previous / next page in catalog order
It also sets <html data-sec="..."> from the catalog. Files are only rewritten when their content changes.
"""
import hashlib
import html
import json
import os
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist"
FONTS = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;700"
    "&family=Inter+Tight:wght@700&family=JetBrains+Mono:wght@400;700"
    "&family=Noto+Sans+SC:wght@400;700&display=swap"
)
problems = []


def esc(s):
    return html.escape(str(s), quote=True)


def ver(rel):
    with open(os.path.join(ROOT, rel), "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:8]


def load():
    with open(os.path.join(ROOT, "catalog.json"), encoding="utf-8") as f:
        cat = json.load(f)
    secs = {s["id"]: s for s in cat["sections"]}
    seen = set()
    for p in cat["pages"]:
        if p["slug"] in seen:
            problems.append(f"catalog: duplicate slug {p['slug']}")
        seen.add(p["slug"])
        if p["section"] not in secs:
            problems.append(f"catalog: {p['slug']} has unknown section {p['section']}")
    return cat, secs


def label(p):
    return "补充" if p.get("extra") else f"({p['no']})"


def head_block(rel):
    return (
        "<!-- v4u:head -->\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<link rel="icon" href="data:,">\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link rel="stylesheet" href="{FONTS}">\n'
        f'<link rel="stylesheet" href="{KATEX}/katex.min.css">\n'
        f'<link rel="stylesheet" href="{rel}assets/v4u.css?v={ver("assets/v4u.css")}">\n'
        f'<script defer src="{KATEX}/katex.min.js"></script>\n'
        f'<script defer src="{KATEX}/contrib/auto-render.min.js"></script>\n'
        f'<script src="{rel}assets/v4u.js?v={ver("assets/v4u.js")}"></script>\n'
        "<!-- /v4u:head -->"
    )


def nav_block(cat, secs, p):
    s = secs[p["section"]]
    sib = [q for q in cat["pages"] if q["section"] == p["section"]]
    links = []
    for q in sib:
        cur = ' aria-current="page"' if q["slug"] == p["slug"] else ""
        links.append(f'<a href="../{esc(q["slug"])}/"{cur}>{esc(label(q))} {esc(q["short"])}</a>')
    return (
        "<!-- v4u:nav -->\n"
        '<nav class="v4u-nav" aria-label="站点导航"><div class="v4u-nav-in">'
        '<span class="v4u-crumb"><a href="../../"><b>Vis4Und</b></a><span class="v4u-sep">/</span>'
        f'<a href="../../#{esc(s["id"])}">({esc(s["no"])}) {esc(s["title"])}</a></span>'
        f'<span class="v4u-links">{"".join(links)}'
        '<button type="button" class="v4u-theme" aria-label="切换深浅色">深色</button></span>'
        "</div></nav>\n<!-- /v4u:nav -->"
    )


def foot_block(cat, secs, p):
    ps = cat["pages"]
    i = next(k for k, q in enumerate(ps) if q["slug"] == p["slug"])
    parts = []
    if i > 0:
        q = ps[i - 1]
        parts.append(f'<a class="pv" href="../{esc(q["slug"])}/"><span>上一篇</span>{esc(q["title"])}</a>')
    if i + 1 < len(ps):
        q = ps[i + 1]
        parts.append(f'<a class="nx" href="../{esc(q["slug"])}/"><span>下一篇</span>{esc(q["title"])}</a>')
    return (
        "<!-- v4u:foot -->\n"
        f'<footer class="v4u-foot"><div class="v4u-foot-in">{"".join(parts)}</div></footer>\n'
        "<!-- /v4u:foot -->"
    )


def put(text, name, block, path):
    rx = re.compile(rf"<!-- v4u:{name} -->.*?<!-- /v4u:{name} -->", re.S)
    if not rx.search(text):
        problems.append(f"{path}: missing <!-- v4u:{name} --> markers")
        return text
    return rx.sub(lambda m: block, text, count=1)


def write_if_changed(path, text):
    old = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return True
    return False


PAGE_ONLY = False


def check_refs(path, text):
    base = os.path.dirname(path)
    ids = set(re.findall(r'\bid="([^"]+)"', text))
    for ref in re.findall(r'(?:href|src)="([^"]+)"', text):
        if ref.startswith(("http://", "https://", "data:", "mailto:", "javascript:")):
            continue
        u = urlsplit(ref)
        if not u.path:
            if u.fragment and u.fragment not in ids:
                problems.append(f"{os.path.relpath(path, ROOT)}: anchor #{u.fragment} not found")
            continue
        tgt = os.path.normpath(os.path.join(base, unquote(u.path)))
        if os.path.isdir(tgt):
            tgt = os.path.join(tgt, "index.html")
        if not os.path.exists(tgt):
            if PAGE_ONLY and (ref.startswith("../") and ref.count("/") <= 2 or ref.startswith("../../")):
                continue  # sibling page or home not written yet; the full build checks these
            problems.append(f"{os.path.relpath(path, ROOT)}: broken link {ref}")


def build_page(cat, secs, p):
    path = os.path.join(ROOT, "pages", p["slug"], "index.html")
    if not os.path.isfile(path):
        problems.append(f"missing page: pages/{p['slug']}/index.html")
        return None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = put(text, "head", head_block("../../"), path)
    text = put(text, "nav", nav_block(cat, secs, p), path)
    text = put(text, "foot", foot_block(cat, secs, p), path)
    text = re.sub(r"<html\b[^>]*>", f'<html lang="zh-CN" data-sec="{p["section"]}">', text, count=1)
    changed = write_if_changed(path, text)
    check_refs(path, text)
    return changed


def build_home(cat, secs):
    with open(os.path.join(ROOT, "tools", "home.template.html"), encoding="utf-8") as f:
        tpl = f.read()
    blocks = []
    for s in cat["sections"]:
        rows = []
        for p in [q for q in cat["pages"] if q["section"] == s["id"]]:
            tag = '<span class="tag">补充</span>' if p.get("extra") else ""
            rows.append(
                f'<li><a href="pages/{esc(p["slug"])}/">'
                f'<span class="no">{esc(label(p))}</span>'
                f'<span class="body"><b>{esc(p["title"])}</b>{tag}<i>{esc(p["en"])}</i>'
                f'<span class="sum">{esc(p["summary"])}</span></span></a></li>'
            )
        blocks.append(
            f'<section class="sec" id="{esc(s["id"])}" data-sec="{esc(s["id"])}">'
            f'<div class="sec-h"><span class="sec-no">({esc(s["no"])})</span>'
            f'<h2>{esc(s["title"])}</h2><span class="sec-en">{esc(s["en"])}</span></div>'
            f'<p class="sec-sum">{esc(s["summary"])}</p>'
            f'<ul class="list">{"".join(rows)}</ul></section>'
        )
    n = len(cat["pages"])
    out = tpl.replace("{{HEAD}}", head_block("")).replace("{{SECTIONS}}", "\n".join(blocks))
    out = out.replace("{{COUNT}}", f"{len(cat['sections'])} 个方向 · {n} 个专题")
    path = os.path.join(ROOT, "index.html")
    changed = write_if_changed(path, out)
    check_refs(path, out)
    return changed


README_RE = re.compile(r"(<!-- catalog:start -->\n).*?(<!-- catalog:end -->)", re.S)


def build_readme(cat, secs):
    path = os.path.join(ROOT, "README.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = []
    for s in cat["sections"]:
        lines.append(f"### ({s['no']}) {s['title']}\n")
        for p in [q for q in cat["pages"] if q["section"] == s["id"]]:
            url = f"{cat['site_url']}pages/{p['slug']}/"
            lines.append(f"- {label(p)} [{p['title']}]({url}) — {p['summary']}")
        lines.append("")
    body = "\n".join(lines)
    if not README_RE.search(text):
        problems.append("README.md: missing catalog markers")
        return False
    return write_if_changed(path, README_RE.sub(lambda m: m.group(1) + body + m.group(2), text))


def main():
    cat, secs = load()
    args = sys.argv[1:]
    changed = []
    if args[:1] == ["--page"]:
        global PAGE_ONLY
        PAGE_ONLY = True
        slug = args[1]
        p = next((q for q in cat["pages"] if q["slug"] == slug), None)
        if not p:
            sys.exit(f"unknown slug {slug}")
        if build_page(cat, secs, p):
            changed.append(f"pages/{slug}/index.html")
    else:
        if build_home(cat, secs):  # first, so the pages' links to the home page resolve
            changed.append("index.html")
        for p in cat["pages"]:
            if build_page(cat, secs, p):
                changed.append(f"pages/{p['slug']}/index.html")
        if build_readme(cat, secs):
            changed.append("README.md")
    for c in changed:
        print("wrote", c)
    if problems:
        print("\n".join("PROBLEM: " + x for x in problems))
        sys.exit(1)
    print("ok")


if __name__ == "__main__":
    main()
