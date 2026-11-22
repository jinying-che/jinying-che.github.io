# Project Instructions

## Markdown publishing

- Follow `docs/markdown-publishing.md` when creating, updating, or publishing Markdown blog posts.
- A request to create or update a blog post authorizes publication unless the user explicitly asks for a draft, preview, or local-only change. After validation, commit the intended files and push directly to `main` without asking for another confirmation. An explicit publish request also authorizes the commit and push.
- Before publishing, review the complete post, validate front matter, links, commands, code blocks, shortcodes, and referenced assets, and run `make build`. Verify the generated post at its intended `/tech/` URL path. For visual changes, complete the frontend verification below before pushing.
- Publish the exact source and assets that passed validation. Stage named files only, fetch latest `main`, preserve unrelated work, and never force-push. Rerun affected checks after resolving conflicts or changing the verified content.
- Use the existing VPS deployment workflow; do not change the production `/tech/` baseURL or upload directly to the live release directory. Check the deployment for the pushed commit and separately verify the public post and its assets. Report any unavailable checks accurately.

## Standalone HTML publishing

- Follow `docs/html-publishing.md` when generating or publishing standalone HTML.
- Use `static/x/<slug>/index.html`, with lowercase hyphenated slugs. Prefer a single self-contained HTML file with inline CSS/JavaScript and embedded SVG.
- Keep URLs in English and free of dates, including year-only suffixes. Put report and publication dates in page content or metadata. Reuse the stable topic slug for updates. `make build` rejects dated page paths; legacy URLs are generated redirects only and must not appear in the notebook.
- Write a descriptive document `<title>` without appending a publication or report date. The notebook reads this title and displays the publication date on its own line.
- Read the complete page and write a one- or two-sentence summary in the page's language. Cover the main subject and takeaway in `<meta name="description" content="…">` in the HTML head. Jinying’s Notebook shows this summary below the page title. Update it when the page's main takeaway changes.
- When the page has clear topics, add a few comma-separated tags in `<meta name="keywords" content="…">` in the HTML head. The notebook uses them as filters.
- Verify material factual claims and figures against sources and list direct references in the standalone HTML. Cite primary sources where available, date time-sensitive figures, and follow the research and chart checks in `docs/html-publishing.md`.
- A request to publish authorizes both the commit and the push. After the build and frontend checks, commit only the intended files and push directly to `main`. Preserve the exact HTML that passed verification. Never include unrelated working-tree changes or force-push.
- Provide the actual HTML file or a browser preview when the user requests a draft or preview.
- The existing VPS workflow publishes these files automatically. Do not upload directly into the live release directory or change the blog's `/tech/` baseURL.
- Report deployment status separately from public URL verification. `/x/<slug>/` requires the owner's Nginx mapping.

## Frontend verification

- After any CSS or frontend UI change, visually verify the rendered site at phone, tablet, and desktop viewport widths.
- Use representative viewports such as 390 × 844, 768 × 1024, and 1440 × 900.
- Check layout, wrapping, overflow, spacing, alignment, readability, and interactive states at each size.
- A successful build or inspection of generated HTML/CSS does not replace viewport-level visual verification.
- If browser-based verification is unavailable, state that clearly and do not claim that visual verification passed.
