# AGENTS.md

## Project Overview

**yaooqinn.github.io** is Kent Yao's personal website and blog, built with Hugo and the PaperMod theme. It supports English and Chinese (简体中文).

## Repository Structure

```
yaooqinn.github.io/
├── content/
│   ├── about.{en,zh}.md          # About page (roles, open source journey)
│   ├── projects.{en,zh}.md       # Projects page
│   ├── search.{en,zh}.md         # Search page
│   └── posts/
│       ├── _index.{en,zh}.md     # Blog listing
│       └── spark/                # Blog posts (*.en.md + *.zh.md)
├── static/
│   └── images/spark-ui/          # Self-hosted blog screenshots
├── layouts/
│   └── partials/
│       └── extend_head.html      # GoatCounter analytics
├── themes/PaperMod/              # Git submodule
├── hugo.toml                     # Site config (i18n, menus, theme)
├── .github/
│   ├── workflows/static.yml      # Hugo build + GitHub Pages deploy
│   └── skills/md2wechat/         # Agent skill for WeChat formatting
└── archetypes/default.md         # New post template
```

## Key Development Guidelines

- **Hugo extended** required (install via `winget install Hugo.Hugo.Extended`)
- Preview: `hugo server -D`
- Build: `hugo --gc --minify`
- Deploy: automatic on push to `main` via GitHub Actions

## Writing Blog Posts

### Create a new post
1. Create `content/posts/{topic}/{slug}.en.md` with YAML front matter
2. Create matching `.zh.md` for Chinese translation
3. Front matter must include: `title`, `date`, `tags`, `categories`, `summary`, `showToc: true`

### Images
- Store in `static/images/{topic}/`
- Reference as `/images/{topic}/filename.png` in Markdown
- Don't use external image URLs (self-host for reliability)

### Multi-language
- English is default (no URL prefix)
- Chinese pages are at `/zh/` prefix
- Every content file needs both `.en.md` and `.zh.md` variants

## Agent Skills

### md2wechat (`.github/skills/md2wechat/SKILL.md`)
Converts Markdown blog posts to WeChat Official Account (微信公众号) formatted HTML with inline styles, footnote citations for links, and front matter stripping. Trigger: "公众号", "wechat", "微信排版".

## Analytics

GoatCounter at https://yaooqinn.goatcounter.com (snippet in `layouts/partials/extend_head.html`).

## Commit Style

Use conventional prefixes: `feat:`, `blog:`, `chore:`, `assets:`, `ci:`.
