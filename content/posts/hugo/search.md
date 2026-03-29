---
title: "Hugo Search with Fuse.js"
date: 2026-03-29T00:00:00+08:00
tags: ["hugo"]
description: "How to add client-side fuzzy search to a Hugo blog using Fuse.js"
draft: false
---

### Why Search Matters for a Static Blog

Hugo generates static HTML — there's no backend to query. Adding search requires either an external service or a client-side solution.

### Search Solutions Comparison

| Solution | Type | Index Size | Setup | Best For |
|---|---|---|---|---|
| **Fuse.js** | Client-side fuzzy | Full JSON in memory | Low | Small-medium blogs |
| **Pagefind** | Client-side chunked | Small binary chunks | Very low (post-build CLI) | Any size |
| **Lunr.js** | Client-side full-text | Medium-large | Medium | Precise text search |
| **Algolia** | Hosted service | Server-side | High (API keys, sync) | Commercial/docs sites |

**Trade-offs of Fuse.js:**
- Pro: no backend, no API keys, no build step, privacy-friendly, fuzzy matching
- Pro: most popular choice in Hugo ecosystem (used by PaperMod, Stack, Blowfish, Congo)
- Con: loads entire index into browser memory — not ideal for 1000+ posts
- Con: fuzzy matching can return less precise results than full-text search

### How It Works

```
Build Time (Hugo)                    Runtime (Browser)
┌──────────────┐                    ┌──────────────────────┐
│ hugo build   │                    │ User opens search    │
│              │                    │        │             │
│ index.json ──┼── static file ───>│ fetch("/index.json") │
│ (all posts)  │    on server      │        │             │
└──────────────┘                    │  Fuse.js builds      │
                                    │  in-memory index     │
                                    │        │             │
                                    │  User types query    │
                                    │        │             │
                                    │  fuse.search("tcp")  │
                                    │        │             │
                                    │  Ranked results      │
                                    │  rendered as HTML    │
                                    └──────────────────────┘
```

Hugo and Fuse.js are completely independent. Hugo generates a JSON file at build time; Fuse.js fetches and searches it at runtime in the browser.

### Implementation

#### 1. Generate JSON Index

Add JSON to Hugo's home output formats in `config.toml`:

```toml
[outputs]
  home = ["HTML", "RSS", "JSON"]
```

Create `layouts/_default/index.json` to define the index schema:

```go-html-template
{{- $.Scratch.Add "index" slice -}}
{{- range .Site.RegularPages -}}
  {{- $.Scratch.Add "index" (dict "title" .Title "tags" .Params.tags "permalink" .Permalink "content" .Plain "date" (.Date.Format "2006-01-02")) -}}
{{- end -}}
{{- $.Scratch.Get "index" | jsonify -}}
```

Hugo automatically generates `public/index.json` on every build — no extra step needed.

#### 2. Search Modal Partial

Create `layouts/partials/search.html` with:
- A fixed overlay + modal UI
- Fuse.js loaded from CDN
- Lazy index loading (fetched only on first search open)

Key Fuse.js configuration:

```javascript
fuse = new Fuse(data, {
  keys: [
    { name: "title",   weight: 0.6 },  // title matches ranked highest
    { name: "tags",    weight: 0.3 },  // then tags
    { name: "content", weight: 0.1 },  // content as tiebreaker
  ],
  includeMatches: true,
  minMatchCharLength: 2,
  threshold: 0.4,  // 0 = exact match, 1 = match anything
});
```

#### 3. Include in Every Page

Override `layouts/_default/baseof.html` and add the partial before `</body>`:

```go-html-template
{{ partial "search.html" . }}
</body>
```

Important: the partial must be in `<body>`, not `<head>` — it contains HTML elements and scripts.

#### 4. Menu Integration

Add a menu item with `#search` as URL (not a real page):

```toml
[[languages.en.menu.main]]
  identifier = "search"
  name = "Search"
  url = "#search"
```

JavaScript intercepts clicks on `a[href="#search"]` to toggle the modal.

### Trigger Methods

| Method | How |
|---|---|
| Menu click | Click "Search" in navigation |
| Keyboard | `Cmd+K` (Mac) / `Ctrl+K` (Windows) |
| Close | `Escape` key or click outside modal |

### File Structure

```
layouts/
├── _default/
│   ├── baseof.html      # overrides theme, includes search partial
│   └── index.json       # search index template
└── partials/
    └── search.html      # modal UI + Fuse.js + CSS

config.toml              # JSON output + search menu item
```
