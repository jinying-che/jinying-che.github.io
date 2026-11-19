# Publish standalone HTML from your phone

## Daily workflow

1. Ask ChatGPT or Codex Cloud to generate a complete, responsive `index.html`.
2. Download/open the actual HTML file on your phone and review it. Request changes
   before publication. Some phone file viewers do not execute JavaScript; for
   interactive pages, check the controls in a browser-accessible preview if the
   file viewer cannot run them. A screenshot alone does not verify interaction.
3. Tell Codex Cloud to publish the approved file in this repository at
   `static/x/<slug>/index.html`, commit it, and push to `main`.
4. The existing **Deploy Hugo to VPS** GitHub Action builds and deploys the site.
5. Open `https://chejinying.com/x/<slug>/` after deployment succeeds and the
   one-time Nginx mapping below is installed.

Use Codex **Cloud**, with access to this GitHub repository, so publishing does
not depend on your laptop being awake. If HTML was generated in another ChatGPT
conversation, download it and attach it to the cloud task. Do not assume separate
conversations share files. Ask for a downloadable HTML attachment, not only a
code block. This repository configuration does not itself enable cloud account
access or provide a hosted preview service.

Example generation request:

> Generate a self-contained, responsive HTML explanation of [topic]. Use inline
> CSS and JavaScript, embedded SVG for diagrams, and no external dependencies or
> private API keys. Include a viewport meta tag. Return index.html for review on
> my phone. Do not publish yet.

Example publication request, after reviewing the file:

> Publish this approved HTML file to jinying-che/jinying-che.github.io at
> static/x/[slug]/index.html. Preserve its contents, check the build and the
> required viewport sizes, commit only the intended files, and push to main.
> Wait for the VPS deployment and report the public URL and verification result.

For a stock report, include source links and an explicit data timestamp. Live
prices and private data APIs require separate data/backend arrangements.

## File and URL convention

```text
static/x/prometheus-staleness/index.html
    -> public/x/prometheus-staleness/index.html
    -> /var/www/site/current/x/prometheus-staleness/index.html
    -> https://chejinying.com/x/prometheus-staleness/
```

Use lowercase letters, digits, and hyphens for slugs. An existing slug updates
the existing page; verify that overwrite is intended. Prefer one HTML file.
If additional assets are necessary, keep them in the same page directory and
use relative links such as `./assets/chart.svg`. Do not use `sandbox:`, `file:`,
localhost URLs, temporary download links, or `/tech/` asset paths in the export.

Hugo copies `static/` files into `public/`; no Markdown conversion or additional
deployment workflow is needed. Standalone HTML bypasses Hugo templates and does
not automatically receive the blog navigation, search, RSS, sitemap entries,
or comments. Keep the existing production `baseURL` unchanged.

## Publication checks

- Preserve the approved HTML bytes when placing it in the repository.
- Follow AGENTS.md: visually check 390 x 844, 768 x 1024, and 1440 x 900; verify
  interactive controls and report any unavailable browser verification.
- Build with `hugo` and confirm `public/x/<slug>/index.html` exists. Compare it
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

To update a page, review and publish a replacement at the same path. To undo a
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
Content-Security-Policy headers must permit the approved page's inline code or
the page should be adapted to that policy. `/x/` shares the site's origin;
publish trusted, reviewed scripts only and keep credentials out of HTML.

Validate with `sudo nginx -t`, then reload Nginx. Once a real page is published:

```bash
curl -I https://chejinying.com/x/example/
curl -I https://chejinying.com/x/example/index.html
curl -I https://chejinying.com/x/does-not-exist/
```

Expect the first two to serve HTML successfully and the missing path to return
404, then open the page on the phone and exercise it. `/x/` itself has no gallery
yet and may return 403 without an index page; that does not prevent slug URLs
from working. Use the trailing-slash page URL when sharing.

## References

- Hugo static files: https://gohugo.io/getting-started/directory-structure/
- Codex Cloud: https://learn.chatgpt.com/docs/cloud
- Nginx root/location: https://nginx.org/en/docs/http/ngx_http_core_module.html
