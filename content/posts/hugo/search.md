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

#### 2. Inline Search Bar in Header

Override `layouts/partials/menu.html` to add a search bar right-aligned in the navigation:

```html
<div id="search-wrapper">
  <div id="search-bar">
    <svg>...</svg>
    <input type="text" id="search-input" placeholder="Search posts..." autocomplete="off" />
    <kbd id="search-kbd">/</kbd>
  </div>
</div>
```

The search bar includes:
- A magnifying glass icon on the left
- An input field with placeholder
- A `/` keyboard hint on the right (hidden when typing)

Results appear in a dropdown panel anchored below the search bar.

#### 3. Fuse.js Configuration

```javascript
fuse = new Fuse(data, {
  keys: [
    { name: "title",   weight: 0.5 },  // title matches ranked highest
    { name: "tags",    weight: 0.3 },  // then tags
    { name: "content", weight: 0.2 },  // content matches
  ],
  includeMatches: true,
  minMatchCharLength: 2,
  threshold: 0.5,  // 0 = exact match, 1 = match anything
});
```

- `weight` controls how much each field contributes to the ranking score
- `threshold` controls how fuzzy the matching is — lower means stricter
- The index is lazy-loaded on first focus, not on page load

#### 4. Include in Every Page

Override `layouts/_default/baseof.html` and add the search partial before `</body>`:

```go-html-template
{{ partial "search.html" . }}
</body>
```

Important: the partial must be in `<body>`, not `<head>` — it contains script and style elements that manipulate DOM.

#### 5. Deduplication

Fuse.js can return the same post multiple times when it matches on different keys (title, tags, content). Deduplicate by permalink before rendering:

```javascript
const raw = fuse.search(query);
const seen = new Set();
const results = raw.filter((r) => {
  if (seen.has(r.item.permalink)) return false;
  seen.add(r.item.permalink);
  return true;
});
```

### Trigger Methods

| Method | How |
|---|---|
| Click | Click the search bar in navigation |
| Keyboard | `/` or `Cmd+K` (Mac) / `Ctrl+K` (Windows) to focus |
| Close | `Escape` to blur, or click outside |

### File Structure

```
layouts/
├── _default/
│   ├── baseof.html      # overrides theme, includes search partial
│   └── index.json       # search index template
└── partials/
    ├── menu.html        # overrides theme, adds inline search bar
    └── search.html      # search JS + CSS + results dropdown

config.toml              # JSON output format
```
