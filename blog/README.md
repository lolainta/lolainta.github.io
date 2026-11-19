# Blog

Plain static pages, built by a stdlib-only Python script. No dependencies, no pip.

## Add a post

1. Create `posts/<slug>.md`. The file name becomes the URL: `posts/2026-10-foo.md` → `/blog/2026-10-foo/`.
2. Start it with front matter:

   ```yaml
   ---
   title: 文章標題
   date: 2026-10-10
   lang: zh
   tags: [tag one, tag two]
   summary: 一句話摘要，用在文章列表、RSS 和 meta description。
   draft: true
   ---
   ```

3. Write the body in Markdown. Supported: `#` headings, paragraphs, `-` / `1.` lists (one level),
   links, images, inline code, `**bold**`, `*italic*`, fenced code blocks, `|` tables, `>` blockquotes.
   Anything else is passed through as text.
4. Rebuild from the repo root (or anywhere):

   ```sh
   python3 blog/build.py
   ```

5. Preview with `python3 -m http.server` in the repo root and open <http://localhost:8000/blog/>.

## What the build writes

- `blog/<slug>/index.html` for every post, and `blog/index.html` (newest first)
- `blog/feed.xml` (RSS) and `sitemap.xml`
- the "最近文章" strip in `index.html`, between the `<!-- recent-posts -->` markers (3 newest)

## Drafts

`draft: true` posts are skipped by a plain build, so nothing published links to them.
Preview them with `python3 blog/build.py --drafts`: they are then built and listed with a
草稿 badge and `noindex`, and still left out of `feed.xml` and `sitemap.xml`. Run a plain
build again before committing. Set `draft: false` (or delete the line) and rebuild to publish.

Deleting or renaming a post does not remove its old `blog/<slug>/` folder; delete it by hand.

Styles live in `blog/blog.css` (a copy of the home page's colour tokens and type, so the blog
does not depend on `index.html`).
