---
name: md2wechat
description: >
  Converts Markdown blog posts to WeChat Official Account (微信公众号) friendly HTML.
  Strips YAML front matter, applies themed inline styles, converts external links to
  footnote citations, and outputs a single HTML file ready to paste into the WeChat editor.
  Use when user mentions "公众号", "wechat", "md2wechat", "微信排版", or "转换公众号".
---

# Markdown to WeChat (md2wechat)

Convert Markdown files to WeChat Official Account (微信公众号) formatted HTML with inline styles.

## Language

**Match user's language**: Respond in the same language the user uses.

## When to Use

- User wants to publish a blog post to WeChat 公众号
- User asks to convert Markdown to WeChat format
- User mentions "公众号", "微信排版", or "wechat"

## Workflow

### Step 1: Identify the Source File

If the user specifies a file path, use that. Otherwise, look for Chinese `.zh.md` blog posts under `content/posts/`.

```bash
# List available Chinese posts
find content/posts -name "*.zh.md" -type f
```

### Step 2: Read and Clean the Markdown

1. Read the source `.md` file
2. **Strip YAML front matter** (everything between the opening `---` and closing `---`)
3. Extract the `title` from front matter for use as the article title

### Step 3: Convert to WeChat HTML

Transform the cleaned Markdown to HTML with **inline styles** (WeChat strips `<style>` tags and CSS classes). Apply these rules:

#### Theme Colors

Default theme is **green**. User can request: green, blue, orange, or purple.

| Theme  | Primary   | Primary Light | Secondary | Code Text |
|--------|-----------|---------------|-----------|-----------|
| green  | `#07c160` | `#e8f7ef`     | `#576b95` | `#c7254e` |
| blue   | `#1890ff` | `#e6f7ff`     | `#722ed1` | `#d4380d` |
| orange | `#fa8c16` | `#fff7e6`     | `#eb2f96` | `#d4380d` |
| purple | `#722ed1` | `#f9f0ff`     | `#13c2c2` | `#531dab` |

#### Inline Style Rules

Apply styles directly via `style=""` attribute on each element. **Do NOT use CSS classes or `<style>` tags** — WeChat strips them.

**Headings:**
- `<h1>`: `font-size: 24px; font-weight: bold; color: #1a1a1a; border-bottom: 3px solid {primary}; padding-bottom: 10px; margin: 30px 0 20px 0;`
- `<h2>`: `font-size: 20px; font-weight: bold; color: {primary}; border-left: 4px solid {primary}; padding: 10px 12px; margin: 25px 0 15px 0; background: {primaryLight}; border-radius: 0 4px 4px 0;`
- `<h3>`: `font-size: 18px; font-weight: bold; color: #1a1a1a; margin: 20px 0 12px 0;`

**Text:**
- `<p>`: `margin: 12px 0; text-align: justify; line-height: 1.8; font-size: 16px; color: #333;`
- `<strong>`: `color: {primary}; font-weight: bold;`
- `<em>`: `font-style: italic; color: {secondary};`

**Code:**
- Inline `<code>`: `background: #f8f8f8; color: {codeText}; padding: 2px 6px; border-radius: 3px; font-family: Monaco, Menlo, Consolas, monospace; font-size: 14px;`
- `<pre>`: `background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 8px; overflow-x: auto; margin: 15px 0; font-size: 13px; line-height: 1.5;`
- `<code>` inside `<pre>`: `background: transparent; color: inherit; padding: 0; font-size: 13px;`

**Blockquote:**
- `<blockquote>`: `border-left: 4px solid {primary}; background: {primaryLight}; padding: 12px 15px; margin: 15px 0; border-radius: 0 8px 8px 0; color: #666;`

**Lists:**
- `<ul>`, `<ol>`: `padding-left: 25px; margin: 12px 0;`
- `<li>`: `margin: 8px 0; line-height: 1.8;`

**Tables:**
- `<table>`: `width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 14px;`
- `<th>`: `background: {primary}; color: #fff; padding: 10px 8px; text-align: left; font-weight: bold; border: 1px solid #e8e8e8;`
- `<td>`: `padding: 8px; border: 1px solid #e8e8e8;`
- Even `<tr>`: add `background: #f9f9f9;`

**Links:**
- `<a>`: `color: {secondary}; text-decoration: none; border-bottom: 1px dashed {secondary};`

**Horizontal rule:**
- `<hr>`: `border: none; height: 1px; background: linear-gradient(to right, transparent, {primary}, transparent); margin: 25px 0;`

**Images:**
- `<img>`: `max-width: 100%; border-radius: 8px; margin: 15px 0;`
- ⚠️ Add a comment: `<!-- 请在公众号编辑器中手动上传此图片 -->`

### Step 4: Convert External Links to Footnote Citations

WeChat does not support clickable hyperlinks in articles. Convert all external links to footnote-style citations:

1. Replace `<a href="URL">text</a>` with `text[N]` where N is the footnote number
2. At the end of the article, add a "参考链接" (References) section:

```html
<section style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 14px; color: #999;">
  <p style="font-weight: bold; color: #666;">参考链接</p>
  <p>[1] URL</p>
  <p>[2] URL</p>
</section>
```

Exception: Do NOT convert image `src` URLs — those are handled by WeChat's image uploader.

### Step 5: Output the Result

1. Save the HTML file to `static/tools/md2wechat/output/` with a descriptive name:
   ```
   static/tools/md2wechat/output/{slug}.html
   ```

2. Report to the user:
   ```
   ✅ WeChat HTML generated!

   Source: {source_file}
   Output: {output_file}
   Theme:  {theme_name}
   Links:  {N} external links converted to footnotes

   Next steps:
   1. Open the HTML file in a browser
   2. Select all (Ctrl+A) and copy (Ctrl+C)
   3. Paste (Ctrl+V) in the WeChat 公众号 editor
   4. Upload images manually in the editor (WeChat doesn't support external URLs)
   ```

## Example Usage

```
User: 帮我把 dark-mode-spark-ui.zh.md 转换为公众号格式
Agent: Reads file → strips front matter → converts to inline-styled HTML → saves output → reports
```

```
User: Convert my Chinese blog post about SQL plan visualization to WeChat format, use blue theme
Agent: Finds sql-plan-visualization.zh.md → applies blue theme → converts → saves → reports
```
