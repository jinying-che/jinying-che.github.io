# Giscus Comment System Implementation

Last updated: 2026-08-30

Status: **Implementation is complete. Final manual verification is in
progress.**

## Objective

Add production-ready comments to this Hugo blog using
[giscus](https://giscus.app/) and GitHub Discussions.

The selected architecture stores comments in this repository's GitHub
Discussions rather than in Hugo content, the VPS, or a separate database.
Readers sign in with GitHub and interact with the embedded giscus interface on
post pages.

## Architecture decision

Use hosted giscus with the existing public repository:

```text
jinying-che/jinying-che.github.io
```

Reasons:

- Comments remain visible and manageable in GitHub Discussions.
- No comment database, backup job, or application service is required on the
  VPS.
- Giscus is open source, free, and has no advertising layer.
- The repository already has a Hugo comments partial and per-page
  `hideComments` support.
- A GitHub-only identity model is approved for this technical blog.

Important tradeoff: a reader must have a GitHub account to post a comment.

## Current state

| Area | Status |
|---|---|
| Research and architecture | Complete |
| GitHub Discussions | Enabled |
| Repository and category IDs | Resolved |
| Hugo integration | Manual end-to-end test passed |
| Repository origin policy | Approved |
| Standalone comment policy | Removed by owner decision |
| Production Hugo build | Earlier build passed; final rerun pending |
| Generated HTML checks | Earlier checks passed; final rerun pending |
| giscus GitHub App | Installed for this repository |
| Real comment creation | Passed manually, including reactions and GitHub storage |
| Phone, tablet, and desktop visual QA | Passed manually with light theme |

External changes made so far are enabling GitHub Discussions, installing the
giscus GitHub App for this repository, and renaming the selected category.

## GitHub state

GitHub Discussions was enabled for the repository through the GitHub API.
GitHub created its standard categories. The selected restricted Announcement
category was renamed to `Blog comments` through the GitHub UI.

Current configuration:

```text
Repository ID:
MDEwOlJlcG9zaXRvcnkyOTkwNDc4MjI=

Category name:
Blog comments

Category ID:
DIC_kwDOEdMbjs4DEb4J
```

The Announcement format is intentional: maintainers and giscus can create
top-level threads, while readers can comment and reply. The rename did not
change the category ID.

The giscus GitHub App is installed for only this repository. The owner manually
confirmed that the official configurator reports that the repository meets all
requirements.

## Local changes made

### `config.toml`

Added `[params.comments]` with:

- Global `enabled` feature switch
- Repository name and ID
- Discussion category name and ID
- `pathname` page mapping
- Strict matching
- Reactions enabled
- Comment input above the thread
- `light` theme
- English interface
- Lazy loading
- GitHub Discussions fallback URL

The current site theme is fixed light. The giscus widget therefore uses its
built-in `light` theme. There is no manual light/dark toggle, so runtime theme
synchronization is unnecessary.

### `layouts/partials/comments.html`

Replaced the empty placeholder with a configurable giscus embed.

Behavior:

- Renders only when comments are globally enabled.
- Renders only for the configured post content type.
- Enforces the existing `hideComments = true` front matter inside the partial,
  even if the partial is called from another layout in the future.
- Shows a concise `Comments` heading immediately above the embed.
- Includes a GitHub Discussions fallback when JavaScript is disabled.
- Uses `data-emit-metadata="0"`.
- Uses lazy loading.
- Leaves creation of the `.giscus` render container to the official client.
- Preserves whitespace around the optional `data-loading` attribute so Hugo
  cannot concatenate adjacent HTML attributes.
- Contains public IDs only; it contains no secret.

### `layouts/partials/site-overrides.css`

Added:

- Comment section spacing and divider
- Responsive iframe width constraints
- Overflow prevention
- Reduced phone spacing
- Print exclusion

### `giscus.json`

Added a repository-root giscus policy with these allowed origins:

```text
https://chejinying.com
https://jinying-che.github.io
http://localhost:<port>
http://127.0.0.1:<port>
```

The localhost entries are restricted by a regular expression to numeric ports.
This origin policy becomes effective when the file is present on the
repository's default branch.

The origin policy was reviewed against the current upstream `giscus.json`
schema. The production apex domain and GitHub Pages mirror are allowed.
`www.chejinying.com`, preview deployments, and arbitrary subdomains are
deliberately excluded. Add an exact origin before serving the comment embed
from any new host. The `/tech` deployment prefix is a URL path, not part of the
origin, so it is intentionally absent from this list.

Comments are ordered newest-first by default.

### `.github/workflows/gh-pages.yml`

Removed the `content/**` path restriction. Previously, layout and configuration
changes would not trigger the GitHub Pages workflow.

The current change means every change on `main` triggers GitHub Pages. An
alternative is to restore `paths:` with an explicit list covering content,
layouts, configuration, static assets, modules, and workflow files.

The selected production behavior is to keep the unrestricted `main` trigger.
This matches the existing VPS workflow and ensures that layout, CSS, and
configuration changes always rebuild both deployment targets. The accepted
tradeoff is that documentation-only changes may also trigger a build.

### `readme.md`

Added comment-system setup and maintenance documentation.

## Verification history

An earlier production build completed successfully before the final interface
cleanup:

```text
Pages:            191
Paginator pages:   15
Non-page files:     7
Static files:      72
Aliases:           53
```

That build's generated HTML was checked for:

- Correct repository name
- Correct repository ID
- Correct category name
- Correct category ID
- `pathname` mapping
- Strict matching enabled
- Reactions enabled
- Metadata emission disabled
- Input position set to the top
- Theme attribute (the earlier build used `dark_dimmed`; final generated HTML
  must confirm `light`)
- English interface
- Lazy loading

Additional earlier checks passed:

- `giscus.json` is valid JSON.
- `git diff --check` reports no whitespace errors.
- The production Hugo build completes.

Existing unrelated Hugo warnings remain:

- `languageCode` is deprecated.
- The `pagination` output kind is unknown.
- Raw HTML is omitted in three existing posts.

These warnings existed outside the comment-system change and were not modified.

Because the comment template, theme, and policy-page scope changed afterward,
the production build, generated-HTML inspection, JSON validation, and
whitespace check must be rerun against the final workspace. The owner has
approved proceeding with this final manual check.

## Visual verification history

The project requires visual verification at:

- Phone: 390 x 844
- Tablet: 768 x 1024
- Desktop: 1440 x 900

Earlier automated headless Chrome attempts did not produce valid evidence and
are not counted. The owner subsequently inspected the light-theme widget at
the required phone, tablet, and desktop viewport sizes and reported that all
three passed. The owner also completed end-to-end comment and reaction tests
and confirmed that the resulting data is visible in GitHub Discussions.

## Final manual verification

Run these checks from the repository root. They are intentionally assigned to
the owner rather than the implementation agent.

### 1. Static checks and final production build

```bash
git diff --check
jq empty giscus.json
hugo --environment production --minify \
  --destination /tmp/jinying-giscus-final
```

Expected result: each command exits successfully. Existing unrelated Hugo
warnings about `languageCode`, the `pagination` output kind, and raw HTML may
still appear.

### 2. Generated HTML

Open a generated post under `/tmp/jinying-giscus-final/posts/` and confirm its
giscus script contains:

```text
data-repo="jinying-che/jinying-che.github.io"
data-category="Blog comments"
data-mapping="pathname"
data-strict="1"
data-reactions-enabled="1"
data-emit-metadata="0"
data-input-position="top"
data-theme="light"
data-lang="en"
data-loading="lazy"
```

Also confirm that the home page, tag pages, and other non-post pages do not
contain `https://giscus.app/client.js`.

### 3. Per-post opt-out

Temporarily set `hideComments = true` in one post's front matter, reload that
post, and confirm the entire Comments section is absent. Restore the post
before reviewing the final diff.

### 4. Failure fallbacks

In browser developer tools:

1. Disable JavaScript, reload a post, and confirm the GitHub Discussions
   fallback is visible and usable.
2. Re-enable JavaScript, block `https://giscus.app/client.js`, reload, and
   confirm the article and navigation remain usable even though the widget is
   absent.
3. Remove the block and confirm the light widget returns.

### 5. Final workspace review

```bash
git status --short
git diff -- .github/workflows/gh-pages.yml config.toml \
  layouts/partials/comments.html layouts/partials/site-overrides.css readme.md
```

Review the new `giscus.json` file separately.

## Complete SOP

### Phase A: Review architecture and policy

1. Confirm that comments should use the existing source repository rather than
   a dedicated comments repository.
2. Confirm that commenters must use GitHub accounts.
3. Confirm `pathname` mapping.
4. Keep the comment interface minimal without a separate policy page.
5. Confirm the selected `Blog comments` category and its Announcement format.
6. Decide whether GitHub Pages should trigger on every `main` change or use an
   explicit path allowlist.

### Phase B: Finish GitHub setup

7. Open the
   [giscus GitHub App installation page](https://github.com/apps/giscus/installations/new).
8. Choose **Only select repositories**.
9. Select only `jinying-che/jinying-che.github.io`.
10. Approve the installation.
11. Verify through the official giscus API/configurator that the repository is
    accessible.
12. If the category was renamed, re-read its name and ID and update
    `config.toml` if necessary.

### Phase C: Review local implementation

13. Review the diff for:

    - `config.toml`
    - `layouts/partials/comments.html`
    - `layouts/partials/site-overrides.css`
    - `giscus.json`
    - `.github/workflows/gh-pages.yml`
    - `readme.md`

14. Confirm that no unrelated user changes overlap these files.
15. Re-run `git diff --check`.
16. Re-run a production Hugo build into a temporary destination.
17. Inspect the generated script attributes.
18. Confirm that non-post pages do not include the giscus script.
19. Test a post with `hideComments = true`.

### Phase D: Local functional testing

20. Start Hugo using the development environment on an unused localhost port.
21. Open a representative post at its comments anchor.
22. Confirm that `giscus.app/client.js` loads.
23. Confirm that the iframe loads without repository, category, or origin
    errors.
24. Confirm that the no-JavaScript GitHub fallback is usable.
25. Test with JavaScript disabled.
26. Test with the giscus script blocked or offline; article content and
    navigation must remain usable.

### Phase E: Required viewport QA

27. Capture and inspect the comments section at 390 x 844.
28. Capture and inspect the comments section at 768 x 1024.
29. Capture and inspect the comments section at 1440 x 900.
30. At each size check:

    - Horizontal overflow
    - Text wrapping
    - Section spacing
    - Divider alignment
    - Iframe width
    - Heading readability
    - Widget interactive states
    - Mobile menu interaction near the comments page

31. Do not claim visual verification passed until all three valid captures have
    been opened and inspected.

### Phase F: End-to-end comment workflow

32. Sign in through the embedded giscus interface.
33. Submit a test comment on a representative post.
34. Confirm that giscus creates the corresponding GitHub Discussion.
35. Confirm the Discussion maps to the correct post pathname.
36. Test:

    - New comment
    - Reply
    - Edit
    - Reaction
    - Delete or hide moderation
    - Locked Discussion behavior
    - Per-post `hideComments = true`

37. Remove the test comment or Discussion if it should not remain public.

### Phase G: Production verification

38. Present the final diff and QA results for approval.
39. Monitor both GitHub Pages and VPS deployment workflows.
40. Verify a production post under `https://chejinying.com/tech/`.
41. Verify the GitHub Pages mirror if it remains supported.
42. Confirm the production origin is accepted by `giscus.json`.
43. Confirm that a production comment appears in GitHub Discussions.

### Phase H: Operations

44. Watch or subscribe to the selected Discussion category.
45. Moderate comments through GitHub Discussions.
46. Lock Discussions that become abusive or off-topic.
47. Keep post permalinks stable.
48. When changing a post pathname, migrate or remap its Discussion explicitly.
49. Periodically review the installed giscus App and repository scope.
50. Recheck giscus behavior after major Hugo theme or CSP changes.

## Remaining work

- [x] Review and approve the architecture decisions.
- [x] Install giscus for this repository only.
- [x] Rename `Announcements` to `Blog comments` while retaining its
  Announcement format.
- [x] Re-verify the category name and ID.
- [x] Re-verify giscus configurator access.
- [x] Test a real comment iframe after App installation.
- [ ] Test `hideComments = true` on a post.
- [ ] Test JavaScript-disabled and giscus-unavailable fallbacks.
- [x] Complete and inspect phone viewport QA with the light widget theme.
- [x] Complete and inspect tablet viewport QA with the light widget theme.
- [x] Complete and inspect desktop viewport QA with the light widget theme.
- [x] Create a real test comment, add a reaction, and confirm GitHub storage.
- [ ] Run the final production Hugo build.
- [ ] Inspect the final generated HTML attributes and page scope.
- [ ] Re-run `jq empty giscus.json` and `git diff --check`.
- [ ] Review the final diff.
- [ ] Run production smoke tests.

## Approved decisions

The owner approved these choices during the step-by-step implementation:

1. Store comments in `jinying-che/jinying-che.github.io`.
2. Require GitHub sign-in.
3. Use `pathname` with strict matching.
4. Use the renamed `Blog comments` category with its Announcement format.
5. Trigger GitHub Pages on every `main` change, matching the VPS workflow.
6. Do not include an unlinked standalone comment-policy page.
7. Install giscus for only this repository.

## Rollback

### Before deployment

Disable the feature flag or revert the individual integration files before the
site is deployed.

### After deployment

Set this value to disable the embedded UI quickly:

```toml
[params.comments]
enabled = false
```

This removes comments from rendered pages without deleting existing GitHub
Discussions.

For a full integration rollback:

1. Disable the Hugo feature flag.
2. Revert the comment partial, styles, configuration, origin file,
   documentation, and workflow change.
3. Remove this repository from the giscus App installation if the integration
   will not return.
4. Decide separately whether GitHub Discussions should remain enabled.

Do not delete Discussions as part of a routine UI rollback; they are the
durable comment data.
