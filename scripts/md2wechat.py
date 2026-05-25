#!/usr/bin/env python3
"""Convert a Hugo Chinese Markdown post to WeChat-friendly inline-styled HTML.

Implements rules from .github/skills/md2wechat/SKILL.md.

Usage:
    python3 scripts/md2wechat.py INPUT.zh.md [-o OUTPUT.html] [--theme green|blue|orange|purple]
    python3 scripts/md2wechat.py --all  # convert every *.zh.md in content/posts/

Outputs to static/tools/md2wechat/output/<slug>.html (or -o path).
Images referenced as /images/... are rewritten to absolute https://yaooqinn.github.io/images/...
so the WeChat editor can fetch and host them on upload (no manual re-upload needed).
External hyperlinks are converted to numbered footnote citations.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.stderr.write("ERROR: pip install markdown\n")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_BASE = "https://yaooqinn.github.io"

THEMES = {
    "green":  {"primary": "#07c160", "primaryLight": "#e8f7ef", "secondary": "#576b95", "codeText": "#c7254e"},
    "blue":   {"primary": "#1890ff", "primaryLight": "#e6f7ff", "secondary": "#722ed1", "codeText": "#d4380d"},
    "orange": {"primary": "#fa8c16", "primaryLight": "#fff7e6", "secondary": "#eb2f96", "codeText": "#d4380d"},
    "purple": {"primary": "#722ed1", "primaryLight": "#f9f0ff", "secondary": "#13c2c2", "codeText": "#531dab"},
}


def strip_front_matter(text: str) -> tuple[str, dict]:
    """Strip YAML front matter and return (body, meta)."""
    meta: dict = {}
    if not text.startswith("---"):
        return text, meta
    end = text.find("\n---", 3)
    if end == -1:
        return text, meta
    front = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    for line in front.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return body, meta


def rewrite_image_paths(html: str) -> str:
    """Make /images/... absolute so WeChat can fetch them."""
    return re.sub(
        r'<img([^>]*?)\ssrc="(/[^"]+)"',
        lambda m: f'<img{m.group(1)} src="{SITE_BASE}{m.group(2)}"',
        html,
    )


def collect_and_footnote_links(html: str) -> tuple[str, list[str]]:
    """Replace <a href="URL">text</a> with text[N] and return ([html_without_links], [urls])."""
    urls: list[str] = []
    seen: dict[str, int] = {}

    def repl(m: re.Match) -> str:
        url = m.group("url")
        text = m.group("text")
        # Leave anchors / relative links alone — they're internal
        if url.startswith("#") or url.startswith("/"):
            return text
        if url not in seen:
            urls.append(url)
            seen[url] = len(urls)
        return f"{text}<sup>[{seen[url]}]</sup>"

    html = re.sub(
        r'<a\s+[^>]*?href="(?P<url>[^"]+)"[^>]*>(?P<text>.*?)</a>',
        repl,
        html,
        flags=re.DOTALL,
    )
    return html, urls


def apply_inline_styles(html: str, theme: dict) -> str:
    """Substitute every tag we care about with style= variant."""
    p, pl, sec, ct = theme["primary"], theme["primaryLight"], theme["secondary"], theme["codeText"]

    rules: list[tuple[str, str]] = [
        # Headings
        (r"<h1>",
         f'<h1 style="font-size:24px;font-weight:bold;color:#1a1a1a;border-bottom:3px solid {p};padding-bottom:10px;margin:30px 0 20px 0;">'),
        (r"<h2>",
         f'<h2 style="font-size:20px;font-weight:bold;color:{p};border-left:4px solid {p};padding:10px 12px;margin:25px 0 15px 0;background:{pl};border-radius:0 4px 4px 0;">'),
        (r"<h3>",
         '<h3 style="font-size:18px;font-weight:bold;color:#1a1a1a;margin:20px 0 12px 0;">'),
        (r"<h4>",
         '<h4 style="font-size:16px;font-weight:bold;color:#1a1a1a;margin:16px 0 10px 0;">'),
        # Paragraphs
        (r"<p>",
         '<p style="margin:12px 0;text-align:justify;line-height:1.8;font-size:16px;color:#333;">'),
        # Emphasis
        (r"<strong>", f'<strong style="color:{p};font-weight:bold;">'),
        (r"<em>",     f'<em style="font-style:italic;color:{sec};">'),
        # Inline code
        (r"<code>",
         f'<code style="background:#f8f8f8;color:{ct};padding:2px 6px;border-radius:3px;font-family:Monaco,Menlo,Consolas,monospace;font-size:14px;">'),
        # Pre (code block)
        (r"<pre>",
         '<pre style="background:#1e1e1e;color:#d4d4d4;padding:15px;border-radius:8px;overflow-x:auto;margin:15px 0;font-size:13px;line-height:1.5;">'),
        # Code inside pre — reset
        (r'<pre style="[^"]*"><code[^>]*>',
         '<pre style="background:#1e1e1e;color:#d4d4d4;padding:15px;border-radius:8px;overflow-x:auto;margin:15px 0;font-size:13px;line-height:1.5;"><code style="background:transparent;color:inherit;padding:0;font-size:13px;">'),
        # Blockquote
        (r"<blockquote>",
         f'<blockquote style="border-left:4px solid {p};background:{pl};padding:12px 15px;margin:15px 0;border-radius:0 8px 8px 0;color:#666;">'),
        # Lists
        (r"<ul>", '<ul style="padding-left:25px;margin:12px 0;">'),
        (r"<ol>", '<ol style="padding-left:25px;margin:12px 0;">'),
        (r"<li>", '<li style="margin:8px 0;line-height:1.8;">'),
        # Tables
        (r"<table>",
         '<table style="width:100%;border-collapse:collapse;margin:15px 0;font-size:14px;">'),
        (r"<thead>", "<thead>"),
        (r"<th>",
         f'<th style="background:{p};color:#fff;padding:10px 8px;text-align:left;font-weight:bold;border:1px solid #e8e8e8;">'),
        (r"<td>", '<td style="padding:8px;border:1px solid #e8e8e8;">'),
        # HR
        (r"<hr\s*/?>",
         f'<hr style="border:none;height:1px;background:linear-gradient(to right,transparent,{p},transparent);margin:25px 0;"/>'),
        # Image — preserve src, just add style
        (r"<img\s",
         '<img style="max-width:100%;border-radius:8px;margin:15px 0;display:block;" '),
    ]
    for pattern, replacement in rules:
        html = re.sub(pattern, replacement, html)

    # Alternate-row background for tables (simple post-process)
    def stripe_tr(match: re.Match) -> str:
        rows = re.findall(r"<tr>.*?</tr>", match.group(0), flags=re.DOTALL)
        out = []
        for i, row in enumerate(rows):
            if i % 2 == 1:
                row = row.replace("<tr>", '<tr style="background:#f9f9f9;">', 1)
            out.append(row)
        return "<tbody>" + "".join(out) + "</tbody>"

    html = re.sub(r"<tbody>(.*?)</tbody>", stripe_tr, html, flags=re.DOTALL)
    return html


def build_footer(urls: list[str]) -> str:
    if not urls:
        return ""
    items = "\n".join(
        f'  <p style="margin:6px 0;word-break:break-all;">[{i + 1}] {u}</p>'
        for i, u in enumerate(urls)
    )
    return (
        '\n<section style="margin-top:30px;padding-top:20px;border-top:1px solid #eee;'
        'font-size:14px;color:#999;">\n'
        '  <p style="font-weight:bold;color:#666;">参考链接</p>\n'
        f"{items}\n"
        "</section>\n"
    )


def wrap_document(title: str, body: str, cover: str = "") -> str:
    title_block = (
        f'<h1 style="font-size:24px;font-weight:bold;color:#1a1a1a;'
        f'line-height:1.4;margin:0 0 16px 0;padding:0;">{title}</h1>\n'
    )
    cover_block = ""
    if cover:
        cover_block = (
            f'<img src="{cover}" alt="cover" '
            f'style="width:100%;max-width:100%;border-radius:8px;'
            f'margin:0 0 20px 0;display:block;"/>\n'
        )
    return (
        '<!doctype html>\n<html lang="zh-cn">\n<head>\n<meta charset="utf-8"/>\n'
        f"<title>{title}</title>\n</head>\n"
        '<body style="max-width:677px;margin:0 auto;padding:20px;'
        'font-family:-apple-system,BlinkMacSystemFont,\'Helvetica Neue\',sans-serif;">\n'
        f"{title_block}{cover_block}{body}\n</body>\n</html>\n"
    )


def convert(src: Path, theme_name: str = "green") -> tuple[str, dict]:
    raw = src.read_text(encoding="utf-8")
    body_md, meta = strip_front_matter(raw)
    title = meta.get("title", src.stem)
    cover = meta.get("cover", "")
    if cover.startswith("/"):
        cover = SITE_BASE + cover

    html_core = markdown.markdown(
        body_md,
        extensions=["fenced_code", "tables", "footnotes", "toc", "sane_lists"],
        output_format="html",
    )
    html_core = rewrite_image_paths(html_core)
    html_core, urls = collect_and_footnote_links(html_core)
    html_core = apply_inline_styles(html_core, THEMES[theme_name])
    html_core += build_footer(urls)

    return wrap_document(title, html_core, cover), {
        "title": title,
        "links_count": len(urls),
        "theme": theme_name,
        "slug": src.stem.removesuffix(".zh"),
        "cover": cover,
    }


def out_path(slug: str) -> Path:
    p = REPO_ROOT / "static" / "wechat" / f"{slug}.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", help="Path to a *.zh.md file")
    ap.add_argument("-o", "--output", help="Output HTML path (default: static/tools/md2wechat/output/<slug>.html)")
    ap.add_argument("--theme", default="green", choices=list(THEMES.keys()))
    ap.add_argument("--all", action="store_true", help="Convert every *.zh.md under content/posts/")
    args = ap.parse_args()

    targets: list[Path] = []
    if args.all:
        targets = sorted(
            p for p in (REPO_ROOT / "content" / "posts").rglob("*.zh.md")
            if p.name != "_index.zh.md"
        )
    elif args.input:
        targets = [Path(args.input).resolve()]
    else:
        ap.error("provide an input file or --all")

    if not targets:
        print("No *.zh.md files matched.", file=sys.stderr)
        return 1

    for src in targets:
        html, info = convert(src, args.theme)
        dest = Path(args.output) if args.output else out_path(info["slug"])
        dest.write_text(html, encoding="utf-8")
        print(f"✅ {src.relative_to(REPO_ROOT) if src.is_relative_to(REPO_ROOT) else src}")
        print(f"   → {dest.relative_to(REPO_ROOT) if dest.is_relative_to(REPO_ROOT) else dest}")
        print(f"   title='{info['title']}' theme={info['theme']} links={info['links_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
