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

## Writing voice — 对外口吻（MANDATORY for any agent drafting posts here）

This site is **Kent Yao's public, signed face** — every post represents the voice of an Apache Spark / Gluten PMC member and Apache Kyuubi VP. Tone matters as much as content.

### Hard rules

1. **Public-facing ≠ internal notes.** Kent maintains a private research repo at `~/repos/ai-research/` where raw research material accumulates (`posts/_drafts/`, `worklog/`, internal Verdict scores, betting memos, §3c anti-hallucination rules, 🪃 backfill blocks, etc.). **Never copy-paste from there.** Treat private drafts as raw material — they must be **rewritten** for this site.
2. **No internal jargon leaks.** Forbidden in public posts:
   - Verdict ratings (💎 GEM / 🟢 SOLID / 🟠 WEAK / 🔴 HYPE)
   - Internal betting language ("Q3 押 Kyuubi plan-tuner", "Kent's edge", "ai-research", "crossover leg")
   - Hermes / cron / digest meta-talk
   - Emoji-coded action verbs (🟢 深读 / 🟣 交叉 / 🔵 存档)
3. **Every claim stands on its own.** Public readers have no shared context. Each technical claim needs:
   - A live link to the primary source (paper / repo / release notes / docs)
   - Concrete numbers with explicit baseline (no "5x faster" without "vs Spark 3.5 default config, TPC-DS SF=1000")
   - Version pins on every named system (`Spark 4.0.0-RC1`, not "latest Spark")
4. **Bilingual parity.** Every post needs both `.en.md` and `.zh.md`. Translate **content and tone** — don't word-for-word a private-voice phrase into the other language. If one side reads stiff, fix both.
5. **Voice register** — what PMC public writing sounds like:
   - **Restrained**, not breathless. Avoid "revolutionary", "game-changing", "this changes everything".
   - **Specific**, not vague. "P90 latency dropped from 412ms to 244ms on TPC-H Q9" not "much faster".
   - **Cite peers properly.** When citing Photon / Velox / DuckDB / ClickHouse work, link the source, name the authors/teams, and represent their claims accurately — these are colleagues and competitors, not strawmen.
   - **Acknowledge limits.** If a benchmark is SF=1, say so. If results depend on configuration, show the config. PMC credibility comes from honest reporting.
   - **Op-ed sparingly.** Strong opinions are fine when clearly framed as opinion and backed with reasoning — but the default register is **observational and technical**, not editorial.
6. **Apache hat awareness.** When writing about Spark / Gluten / Kyuubi: separate factual reporting (community-neutral) from personal opinion. Don't speak *for* the project — speak *about* it as a contributor. Avoid implying official ASF positions.
7. **Drafting workflow** (when an agent is asked to draft a post):
   - Source material may come from `~/repos/ai-research/posts/_drafts/<slug>.md` — read it for **facts and links**, not for prose.
   - Rewrite from scratch in the public voice. Build the argument independently of any internal Verdict.
   - Write `.en.md` first (or `.zh.md` first — but commit them together; never ship single-language).
   - Run `hugo server -D` locally if previewing; ensure both languages render before opening PR.

### When in doubt

Read 2-3 existing posts under `content/posts/spark/` to calibrate tone before drafting anything new. The published Spark series is the canonical voice reference for this site.

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
