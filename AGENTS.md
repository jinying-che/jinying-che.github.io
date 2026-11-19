# Project Instructions

## Standalone HTML publishing

- Follow `docs/html-publishing.md` when generating or publishing standalone HTML.
- Use `static/x/<slug>/index.html`, with lowercase hyphenated slugs. Prefer a single self-contained HTML file with inline CSS/JavaScript and embedded SVG.
- Before publishing, provide the actual HTML file for phone review. Preserve the reviewed file; do not regenerate it during publication. If the phone viewer cannot run its JavaScript, use a browser-accessible preview and disclose the limitation.
- After the user approves the page for publication, commit only the intended files and push directly to `main`; no pull request is required for this workflow. Never include unrelated working-tree changes or force-push.
- The existing VPS workflow publishes these files automatically. Do not upload directly into the live release directory or change the blog's `/tech/` baseURL.
- Report deployment status separately from public URL verification. `/x/<slug>/` requires the owner's Nginx mapping.

## Frontend verification

- After any CSS or frontend UI change, visually verify the rendered site at phone, tablet, and desktop viewport widths.
- Use representative viewports such as 390 × 844, 768 × 1024, and 1440 × 900.
- Check layout, wrapping, overflow, spacing, alignment, readability, and interactive states at each size.
- A successful build or inspection of generated HTML/CSS does not replace viewport-level visual verification.
- If browser-based verification is unavailable, state that clearly and do not claim that visual verification passed.
