# Publish Markdown blog posts

## Authorization and destination

Requests to create or update a blog post include publishing it, unless the user
asks for a draft, preview, or local-only change. Explicit publication requests
also authorize committing and pushing. Complete the checks below, then publish
without asking for another confirmation.

Keep posts under `content/posts/` and reuse an existing post's path when updating
it. Preserve its original publication date unless a date change is requested.
Use Hugo front matter for the title, date, description, and relevant tags. Keep
assets under `static/` and reusable rendering helpers under `layouts/shortcodes/`.
Do not change the production `/tech/` baseURL.

## Validation before publishing

1. Read the complete post. Check technical accuracy, command prerequisites and
   effects, code fences, headings, tables, and front matter. Verify referenced
   local assets and internal links exist; check new external references when
   accessible. Do not execute illustrative administrative commands on the host.
2. Run `make build` and inspect the generated post. Confirm it is not excluded
   by draft status or a future publication date, its URL is correct, and Hugo
   renders shortcodes, diagrams, syntax highlighting, and asset paths properly.
3. For visual changes, follow the frontend verification in `AGENTS.md`: inspect
   the rendered page at 390 × 844, 768 × 1024, and 1440 × 900. Check wrapping,
   overflow, spacing, alignment, diagram labels, readability, and applicable
   interactions. A successful build alone does not establish visual correctness.
   Report browser verification as unavailable if it cannot be performed.
4. Run `git diff --check` and review the complete intended diff and `git status`.
   Fetch latest `main` and integrate any upstream changes without discarding
   unrelated work. Rerun affected validation if source or dependencies change.

## Publish and verify

1. Stage only named files belonging to the request, including required assets
   and shortcodes. Commit the exact verified source and push to `main` without
   another confirmation. Never force-push. Resolve a rejected push before retrying.
2. The existing **Deploy Hugo to VPS** workflow (`.github/workflows/vps.yml`)
   builds and deploys the site. Check the run for the pushed commit; a successful
   push does not mean deployment succeeded. Do not upload into the live release
   directory or manually deploy an older revision over a newer one.
3. Verify the public URL, such as `https://chejinying.com/tech/posts/ssh/`, after
   deployment. Confirm the updated content and referenced assets are served.
   Report deployment status separately from public URL verification, and state
   any failures or checks that could not be completed.

To roll back, revert the dedicated publication commit and push through the same
workflow. Preserve unrelated subsequent changes.
