#!/usr/bin/env python3
"""Build the static GitHub Pages site for the archive.

Renders README.md as the landing page and appends a browsable index of
every file in the repository. Files are linked to their copies on GitHub,
so the ~1 GB archive is not duplicated into the Pages artifact.
"""

import html
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

import markdown

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "_site"
REPO = os.environ.get("GITHUB_REPOSITORY", "felixgenicio/dev-palmos")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
# HTML documentation published as-is on the site, at the same relative path.
PUBLISHED = [
    ("The Zen of Palm", "palmos-doc/!zen_of_palm/index.html"),
    ("Palm OS User Interface Guidelines", "palmos-doc/!ui_guidelines/index.html"),
    ("Palm OS 3.5 Include File Changes", "palmos-doc/palmos-3_5/IncsFileChanges.html"),
]
PUBLISHED_DIRS = ["palmos-doc/!zen_of_palm", "palmos-doc/!ui_guidelines"]
SKIP = {".git", ".github", "_site", "images", "README.md", ".gitignore"}


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def url(kind, rel):
    return f"https://github.com/{REPO}/{kind}/{BRANCH}/{quote(rel.as_posix())}"


def dir_size(path):
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def is_published(rel):
    rel = rel.as_posix()
    return any(rel == f for _, f in PUBLISHED) or any(rel.startswith(d + "/") for d in PUBLISHED_DIRS)


def docs_section():
    links = "".join(
        f'<li><a href="{quote(path)}">{html.escape(title)}</a></li>' for title, path in PUBLISHED
    )
    return (
        '<section class="docs"><h3 id="online-documentation">Online Documentation</h3>'
        "<p>Original HTML documentation from the archive, readable directly in the browser:</p>"
        f"<ul>{links}</ul></section>"
    )


def tree(path):
    entries = sorted(
        (p for p in path.iterdir() if p.name not in SKIP and not p.name.startswith(".")),
        key=lambda p: (p.is_file(), p.name.lower()),
    )
    items = []
    for p in entries:
        rel = p.relative_to(ROOT)
        name = html.escape(p.name)
        if p.is_dir():
            count = sum(1 for f in p.rglob("*") if f.is_file())
            items.append(
                f'<li><details>'
                f'<summary><span class="dir">{name}/</span>'
                f'<span class="meta">{count} files · {human(dir_size(p))}</span></summary>'
                f'{tree(p)}</details></li>'
            )
        elif p.suffix.lower() in (".html", ".htm") and is_published(rel):
            items.append(
                f'<li class="file"><a href="{quote(rel.as_posix())}">{name}</a>'
                f'<span class="meta">{human(p.stat().st_size)} · '
                f'<a href="{url("blob", rel)}">source</a></span></li>'
            )
        else:
            items.append(
                f'<li class="file"><a href="{url("blob", rel)}">{name}</a>'
                f'<span class="meta">{human(p.stat().st_size)} · '
                f'<a href="{url("raw", rel)}">download</a></span></li>'
            )
    return f'<ul>{"".join(items)}</ul>'


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Palm OS Developer Archive</title>
<meta name="description" content="Preserving the tools, knowledge, and history of Palm OS development.">
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6b6a65; --accent:#2f5d8a; --line:#e3e0d8; --card:#ffffff; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#161614; --fg:#e8e6e1; --muted:#9a978f; --accent:#8ab4e0; --line:#2e2d2a; --card:#1e1e1b; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
main {{ max-width:860px; margin:0 auto; padding:32px 16px 64px; }}
a {{ color:var(--accent); }}
h1 {{ font-size:2.2rem; line-height:1.2; text-align:center; }}
h2 {{ margin-top:2.5rem; padding-bottom:.3rem; border-bottom:1px solid var(--line); }}
img {{ max-width:100%; height:auto; }}
hr {{ border:0; border-top:1px solid var(--line); }}
nav {{ text-align:center; margin:-8px 0 24px; }}
nav a {{ margin:0 10px; }}
.browse ul {{ list-style:none; margin:0; padding-left:18px; }}
.browse > ul {{ padding:12px 16px; background:var(--card); border:1px solid var(--line); border-radius:8px; }}
.browse li {{ padding:2px 0; overflow-wrap:anywhere; }}
.browse summary {{ cursor:pointer; }}
.dir {{ font-weight:600; }}
.meta {{ color:var(--muted); font-size:.85em; margin-left:8px; white-space:nowrap; }}
.docs {{ margin:24px 0 32px; padding:4px 20px 8px; background:var(--card); border:1px solid var(--line); border-radius:8px; }}
.docs h3 {{ margin:14px 0 4px; }}
.docs p {{ margin:0 0 6px; color:var(--muted); }}
footer {{ margin-top:48px; color:var(--muted); font-size:.9em; text-align:center; }}
</style>
</head>
<body>
<main>
{readme}
<nav><a href="#browse-the-archive">Browse the archive</a><a href="https://github.com/{repo}">View on GitHub</a></nav>
<section class="browse">
<h2 id="browse-the-archive">Browse the Archive</h2>
<p>Every file is hosted in the <a href="https://github.com/{repo}">GitHub repository</a>.
Click a file name to view it on GitHub, or <em>download</em> to fetch it directly.</p>
{tree}
</section>
<footer>Palm OS Developer Archive · <a href="https://github.com/{repo}">github.com/{repo}</a></footer>
</main>
</body>
</html>
"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "images", OUT / "images")
    for d in PUBLISHED_DIRS:
        shutil.copytree(ROOT / d, OUT / d)
    for _, f in PUBLISHED:
        if not (OUT / f).exists():
            (OUT / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / f, OUT / f)
    readme = markdown.markdown((ROOT / "README.md").read_text(encoding="utf-8"), extensions=["extra"])
    # Show the online documentation links right after the README's tagline.
    tagline_end = readme.index("</p>", readme.index("<strong>")) + len("</p>")
    readme = readme[:tagline_end] + docs_section() + readme[tagline_end:]
    page = TEMPLATE.format(readme=readme, tree=tree(ROOT), repo=REPO)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    (OUT / ".nojekyll").touch()
    print(f"Wrote {OUT / 'index.html'} ({len(page) // 1024} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
