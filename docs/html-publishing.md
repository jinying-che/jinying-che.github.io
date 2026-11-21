# Publish standalone HTML

## Daily workflow

1. Ask Codex Cloud to create or update a complete, responsive page and publish it.
   To publish an existing HTML file, attach it to the request.
2. Codex saves the page at `static/x/<slug>/index.html` and checks the build,
   layout, and interactive controls.
3. The publication request authorizes Codex to commit the verified file and push
   it directly to `main` after the checks.
4. The **Deploy Hugo to VPS** GitHub Action builds and deploys the site. Codex
   checks the workflow result and verifies the page at
   `https://chejinying.com/x/<slug>/`.

Use Codex **Cloud**, with access to this GitHub repository, so publishing does
not depend on your laptop being awake. If HTML was generated in another ChatGPT
conversation, download it and attach it to the cloud task. Do not assume separate
conversations share files. Ask for a downloadable HTML attachment, not only a
code block. This repository configuration does not itself enable cloud account
access or provide a hosted preview service.

Example generation and publication request:

> Generate a self-contained, responsive HTML explanation of [topic]. Use inline
> CSS and JavaScript, embedded SVG for diagrams, and no external dependencies or
> private API keys. Include a viewport meta tag and complete Simplified Chinese
> and English editions with a language switch. Run the publication checks and
> publish it to my website.

Example publication request for an existing file:

> Publish this HTML file to jinying-che/jinying-che.github.io at
> static/x/[slug]/index.html. Preserve its contents, check the build and the
> required viewport sizes, commit only the intended files, and push to main.
> Wait for the VPS deployment and report the public URL and verification result.

To preview a page, request the actual HTML file or a browser-accessible preview.
Some phone file viewers require a browser preview to run JavaScript controls.

For a stock report, include source links and an explicit data timestamp. Live
prices and private data APIs require separate data/backend arrangements.

## Chinese and English editions

- Include complete Simplified Chinese and English editions by default. Follow
  the requested language when the author specifies a single-language page.
- Place a one-click **中文 / English** control at the top of the page. Translate
  the title, section links, body, chart labels, captions, and control labels.
  Keep both editions in the same standalone HTML file.
- Default to Simplified Chinese for first-time readers. Mark both editions with
  the correct HTML language, update the document language when switching, and
  indicate the selected language. Keep at least the default edition readable
  when JavaScript is unavailable. The source title and description should
  describe the default edition for the notebook.
- Before publishing, test switching in both directions, section navigation,
  keyboard interaction, and layout in both languages at the required viewport
  sizes.

## File and URL convention

```text
static/x/prometheus-staleness/index.html
    -> public/x/prometheus-staleness/index.html
    -> /var/www/site/current/x/prometheus-staleness/index.html
    -> https://chejinying.com/x/prometheus-staleness/
```

Use lowercase letters, digits, and hyphens for slugs. An existing slug updates
the existing page; verify that overwrite is intended. Prefer one HTML file.
Use stable English topic names without dates or year suffixes, for example
`cloudflare-net-investment` rather than `cloudflare-net-investment-2026-11-18`.
Keep dates in the report content or publication metadata, and keep the document
title free of appended dates. `make build` validates every standalone page path
for both deployment workflows. When migrating an already-published URL, add its
old slug to `REDIRECTS` in `scripts/build_x_index.py`; the build generates a
compatibility redirect and lists only the new path in the notebook. These
browser redirects preserve query parameters and fragments when JavaScript is
enabled, with a basic redirect and link available without JavaScript.
If additional assets are necessary, keep them in the same page directory and
use relative links such as `./assets/chart.svg`. Do not use `sandbox:`, `file:`,
localhost URLs, temporary download links, or `/tech/` asset paths in the export.

Hugo copies `static/` files into `public/`; no Markdown conversion or additional
deployment workflow is needed. Standalone HTML bypasses Hugo templates and does
not automatically receive the blog navigation, search, RSS, sitemap entries,
or comments. Keep the existing production `baseURL` unchanged.

## HTML archive

The archive at `https://chejinying.com/x/` lists the HTML files under `static/x/`.
It uses the blog's Hugo Terminal theme. Search matches text in each page, its
title, and its path. Pages appear newest first.

Both deployment workflows run `make build`, which rebuilds the archive after
Hugo copies the files. The creation date comes from ISO 8601 publication
metadata, such as `<meta property="article:published_time" content="2026-11-19">`,
or the Git author date when the file was first added. For files without Git
history, it uses the file modification time.

For a local preview, run `make local-build` and then
`python3 -m http.server 8000 --directory public`. Open
`http://localhost:8000/x/` and rebuild after adding or editing a page.

## Publication checks

- Publish the exact HTML that passed verification.
- Follow AGENTS.md: visually check 390 x 844, 768 x 1024, and 1440 x 900; verify
  interactive controls and report any unavailable browser verification.
- Build with `make build` and confirm `public/x/<slug>/index.html` exists. Compare it
  with the source when checking the VPS build; the separate Pages workflow uses
  minification and is not the byte-preservation target.
- Review `git status` and stage named files only. Fetch latest `main`; do not
  force-push or include unrelated local work. Resolve a rejected push before
  retrying and rerun affected checks if the content changes.
- Check the **Deploy Hugo to VPS** run for the pushed commit, then open the
  public page and verify assets/controls. A successful push is not a successful
  deployment. A successful deployment does not prove Nginx exposes `/x/`.

Workflow: `.github/workflows/vps.yml`. Its production concurrency group allows
an active deployment to finish before another switches the live symlink. GitHub
may replace pending runs; a later main revision includes earlier committed pages.
Do not run an older deployment manually over a newer one unless rolling back.

To update a page, verify and publish a replacement at the same path. To undo a
publication, revert its dedicated commit and push to `main`; the normal full
release deployment restores the previous version or removes the new page.

## One-time Nginx requirements (owner-managed)

The VPS workflow uploads Hugo output to `/var/www/site/releases/<commit>/` and
switches `/var/www/site/current` to the new release. Inside the existing HTTPS
server block for `chejinying.com`, merge this location with your configuration:

```nginx
location = /x {
    return 301 /x/;
}

location ^~ /x/ {
    root /var/www/site/current;
    index index.html;
    autoindex off;
    try_files $uri $uri/ =404;
}
```

`root` appends the complete URI: `/x/example/` resolves inside
`/var/www/site/current/x/example/`. Do not set root to `.../current/x`, which
would duplicate the `x` component. Leave your existing `/tech/` location intact.
This assumes there is no server-level rewrite overriding `/x/` and that Nginx
can read/traverse the release directories and follow the current symlink.

Ensure the server's normal MIME types are loaded (typically
`include /etc/nginx/mime.types;` in the http context), HTML is served as
`text/html`, and no inherited attachment header forces downloads. Existing
Content-Security-Policy headers must permit the page's inline code or
the page should be adapted to that policy. `/x/` shares the site's origin;
publish trusted scripts only and keep credentials out of HTML.

Validate with `sudo nginx -t`, then reload Nginx. Once a real page is published:

```bash
curl -I https://chejinying.com/x/example/
curl -I https://chejinying.com/x/example/index.html
curl -I https://chejinying.com/x/does-not-exist/
```

Expect the first two to serve HTML successfully and the missing path to return
404, then open the page on the phone and exercise it. Open
`https://chejinying.com/x/` to verify the archive and its search.
Use the trailing-slash page URL when sharing.

## References

- Hugo static files: https://gohugo.io/getting-started/directory-structure/
- Codex Cloud: https://learn.chatgpt.com/docs/cloud
- Nginx root/location: https://nginx.org/en/docs/http/ngx_http_core_module.html
