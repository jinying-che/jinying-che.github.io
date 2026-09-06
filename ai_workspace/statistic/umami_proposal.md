# Proposal: Self-hosted Umami analytics for the Hugo blog

Status: Draft — researched 2026-09-06. No services deployed or tracking enabled.

## Recommendation

Use **self-hosted Umami with PostgreSQL** for basic website analytics. Add browser-side engagement events and a small reporting worker for per-post active reading time. Keep the existing VictoriaMetrics and Grafana stack for infrastructure monitoring; optionally export selected website aggregates into it.

Umami is MIT-licensed and provides an application, Docker images, and a Compose deployment with PostgreSQL. This proposal requires no Umami Cloud subscription or proprietary analytics plugin. VictoriaMetrics does **not** replace Umami's PostgreSQL database. [Umami source and deployment documentation](https://github.com/umami-software/umami)

The main trade-off: basic traffic analytics are ready-made, but meaningful per-post reading-time reports require both custom collection **and aggregation**, not just inserting the Umami script.

## Scope and key statistics

The objective is to understand aggregate readership, acquisition, and content engagement—not identify readers individually or claim to understand them completely.

| Question | Statistic | Implementation | Important limit |
|---|---|---|---|
| How much traffic does the blog receive? | Pageviews, estimated visitors, visits, trends | Native Umami | Visitors are estimates, not verified people |
| Where are readers from? | Country; optionally region/city | Native geolocation | Approximate; VPNs and proxies affect results |
| How do readers find the blog? | Referrer domain; optional UTM source/campaign | Native, with URL sanitization | Missing referrers remain unattributed; UTM needs retained campaign fields |
| Which posts attract attention? | Pageviews per canonical post path | Native pageview reporting | A view is not proof of reading |
| Which devices should the site support? | Device, browser, OS, language | Native | Broad categories, not detailed personal profiles |
| How long do people read a post? | Average and median observed active seconds | Custom tracker + reporting worker | An engagement estimate, not actual attention |
| How often is a post meaningfully read? | Engaged reads and engagement rate | Custom definition and aggregation | Thresholds must be displayed and versioned |
| Do readers reach the end? | Article progress and completion-proxy rate | Custom tracker + aggregation | Reaching the bottom does not prove comprehension |
| Which links are useful? | Selected outbound/download clicks | Optional custom events | Add only actions with a clear analytical purpose |

Umami documents location, referral, device, campaign, and visitor metrics. Its visitor identifiers rotate; native visit duration is based on event timing rather than foreground reading activity. Do not interpret either as persistent reader identity or active reading time. [Umami metric definitions](https://docs.umami.is/docs/metric-definitions)

Out of scope initially: session replay, heatmaps, advertising attribution, cross-device identity, and long-term individual visitor profiles. Hugo's existing `.ReadingTime` is an estimated article length; keep it distinct from measured engagement.

## Architecture

The browser—not the Hugo build process—sends analytics events. Hugo remains a static site.

**Actual deployment topology (as of this rollout):** Umami and PostgreSQL run on a self-hosted Kubernetes cluster on the author's Raspberry Pi, not on the VPS. The VPS keeps serving the static Hugo site over Nginx and additionally reverse-proxies the path `chejinying.com/umami/` to the Pi over an existing private VPS↔Pi tunnel (already provisioned outside this proposal). There is no separate `analytics.*` subdomain — Umami is reached at a subpath of the main domain.

```text
Browser
  |
  |-- GET /  (static Hugo pages) ------------------------> VPS Nginx --> generated Hugo files
  |
  '-- GET/POST /umami/*  (tracker script + events) ------> VPS Nginx
                                                               |
                                                   existing VPS<->Pi tunnel
                                                               |
                                                               v
                                                 Raspberry Pi Kubernetes cluster
                                                   +-------------------------+
                                                   |  Umami app (BASE_PATH   |
                                                   |  = /umami)              |
                                                   |          |             |
                                                   |          v             |
                                                   |     PostgreSQL         |
                                                   |   (in-cluster, PVC)    |
                                                   +-------------------------+

Owner dashboard: authenticated browser -> VPS Nginx -> tunnel -> Pi -> Umami dashboard

On hold, not deployed yet:
  Umami API -> reporting worker -> reporting schema/cache -----> Grafana (phase 3, on hold)
                                                       \
                                                        '-------> VictoriaMetrics exporter -> vmagent
                                                                    -> VictoriaMetrics -> Grafana (phase 4, on hold)
```

See `umami_sop.md` for the step-by-step rollout of this topology, phased.

| Layer | Proposed components and data flow | Responsibility |
|---|---|---|
| Blog delivery | Browser → VPS Nginx → generated Hugo files | Serve the blog independently of analytics availability |
| Event collection | Browser's Umami script → VPS Nginx (`/umami/` path) → existing VPS↔Pi tunnel → Umami app on the Pi's k8s cluster | Collect pageviews and custom engagement events |
| Primary storage | Umami app → in-cluster PostgreSQL (Pi) | Store analytics events and Umami configuration |
| Owner dashboard | Authenticated browser → VPS Nginx → tunnel → Umami dashboard on the Pi | Explore native traffic statistics |
| Reading reports, phase 2 | Reporting worker → authenticated Umami API; worker → separate reporting schema/cache | Deduplicate reading checkpoints and compute per-post summaries |
| Grafana, on hold | Grafana → read-only reporting tables in PostgreSQL | Query content reports alongside existing monitoring dashboards |
| VictoriaMetrics, on hold | Worker/exporter → private `/metrics`; vmagent scrapes → VictoriaMetrics; Grafana queries VictoriaMetrics | Retain selected low-cardinality metric snapshots |
| Public counters, optional | Worker → sanitized cached JSON → Nginx → Hugo page | Publish only approved aggregate statistics |

Deployment target: one Umami Deployment and one PostgreSQL Deployment (with a PVC) in a dedicated namespace on the Pi's existing Kubernetes cluster, exposed to the VPS only through the already-established private tunnel — never through a publicly routable port on the Pi's own network. The VPS terminates public HTTPS and reverse-proxies `chejinying.com/umami/` across that tunnel; Umami is configured with `BASE_PATH=/umami` to serve correctly under that subpath. Grafana and VictoriaMetrics integration remain on hold per phases 3–4.

Keep Kubernetes manifests, secrets, PostgreSQL PVC contents, and backups **outside the Hugo release directories and outside this git repo's published output**. The existing `.github/workflows/vps.yml` rotates static-site releases on the VPS only; it has no relationship to the Pi cluster, so analytics data is unaffected by Hugo deploys.

The reporting worker is a later custom component, not an Umami dependency. It can use a separate schema/database on the same PostgreSQL instance initially; grant it only the permissions it needs. No Redis, queue, or ClickHouse is proposed for the initial deployment; Kubernetes is already in place on the Pi and is being reused, not newly introduced for this purpose.

## Hugo integration

Use a repository-owned partial included from `layouts/partials/extended_head.html`; no dedicated Hugo plugin is necessary. Load the self-hosted tracker with `defer`, the site's website ID, and an explicit production-domain allowlist. The website ID is public configuration, not an administrative secret.

Enable collection only in production. Keep one automatic pageview per navigation; engagement events must not send another pageview. Use Umami's before-send hook to sanitize URLs and referrers. Exclude fragments; discard query parameters by default, or retain only reviewed UTM fields if campaign reporting is needed. Removing all query parameters also removes the source of UTM attribution. [Tracker configuration](https://docs.umami.is/docs/tracker-configuration)

Use the site's canonical pathname, including its configured deployment prefix, as the post key. Normalize trailing slashes consistently; keep a mapping if published URLs change. Run the reading tracker only on actual post pages, scoped to `.post-content` in `layouts/_default/single.html`, excluding navigation, TOC, pagination, and comments.

Allow the analytics origin in the site's script/connect CSP policies when applicable. Tracker loading or API failures must never prevent article rendering or navigation. Do not put API login credentials, database credentials, or dashboard access tokens into generated HTML or JavaScript.

## Per-post reading measurement

### Proposed definitions

These are project-specific definitions, not built-in Umami metrics. Start with the following tunable defaults:

| Metric | Definition |
|---|---|
| Post views | Native pageview events for canonical post paths, excluding custom events |
| Instrumented views | Distinct per-page-view IDs with a captured `reading_start` event |
| Observed active time | Accumulated seconds while the document is visible, focused, and not idle |
| Idle cutoff | Pause after 60 seconds without interaction; resume when interaction returns |
| Article progress | Maximum fraction of article content reached by the viewport; clamp to 0–100% |
| Engaged read | An instrumented view with at least 30 active seconds and at least 50% article progress |
| Completion proxy | An instrumented view with at least 30 active seconds and at least 90% article progress |
| Engagement/completion rate | Qualifying distinct views divided by instrumented views in the same cohort |
| Average/median active time | Calculated from one deduplicated duration per instrumented view, including zero for starts with no checkpoint |
| Tracking coverage | Instrumented views divided by native post views; expose mismatches as a quality indicator |

The idle cutoff can undercount a reader studying a long paragraph without interacting. Focus checks also need mobile-browser testing. Short articles may fit entirely in the viewport; use the time threshold to avoid calling an immediate load a completed read. These limitations should accompany the report.

### Event contract and aggregation

Umami supports named custom events with structured data through `umami.track(eventName, data)`. The following event names and properties are our proposed contract. [Tracker functions](https://docs.umami.is/docs/tracker-functions)

| Event | When to send | Properties |
|---|---|---|
| `reading_start` | Once when a post view initializes | `post_path`, `view_id`, `schema_version` |
| `reading_checkpoint` | Every 30 accumulated active seconds, when crossing progress milestones, and best-effort on hiding/leaving | `post_path`, `view_id`, `sequence`, `active_seconds`, `max_progress`, `schema_version` |

Generate `view_id` randomly per page view; do not reuse it as a persistent visitor identifier. Each checkpoint contains **cumulative** active seconds and maximum progress. Debounce simultaneous triggers and preserve the same view state across a back/forward-cache restoration; do not register duplicate timers/listeners.

The worker retrieves events through Umami's authenticated event APIs, including paginated event data. Confirm the pinned release exposes the required fields; the documented `event-data-pivot` endpoint is a candidate. Authentication and token renewal stay server-side. [Event APIs](https://docs.umami.is/docs/api/events), [API authentication](https://docs.umami.is/docs/api/authentication)

Aggregation rules:

1. Deduplicate fetched events by Umami event ID; deduplicate/reconcile checkpoints by `(website, view_id, sequence)`.
2. Store one view record with its start timestamp, largest valid cumulative duration, and largest valid progress. **Never sum cumulative checkpoints.**
3. Assign the view to its start-date cohort in the configured reporting timezone; update that record as later checkpoints arrive. Use overlapping fetch windows and idempotent upserts for late arrivals.
4. Compute per-post counts, rates, average, and median from those view records. Retain enough per-view data for arbitrary-period medians; medians of daily medians are not correct.
5. Validate value ranges and implausible durations. Flag incomplete/missing starts instead of silently inventing denominators.

Backgrounding, crashes, blockers, and offline periods can lose events. Send periodic checkpoints rather than relying solely on unload. Verify the pinned tracker's transport behavior; if an exit-delivery adapter is needed, implement and test it against the supported collection API. Neither ordinary tracking nor beacon delivery guarantees capture.

Native event exploration can help debug this instrumentation, but does not automatically produce these deduplicated reading reports. Custom events can also affect event-based native bounce/duration calculations; validate their behavior in the selected release and use our explicitly defined engagement rate for editorial decisions.

## Grafana and VictoriaMetrics integration options

| Option | Architecture | Custom work | Recommendation |
|---|---|---|---|
| Umami dashboard only | Browser → Umami → PostgreSQL | Tracker installation only for basic traffic | Start here to validate collection |
| Grafana with PostgreSQL | Umami API → worker → reporting tables; Grafana reads those tables | Worker, report schema, SQL panels | Preferred for flexible per-post reading reports |
| Grafana with VictoriaMetrics | Umami API/reporting data → exporter → vmagent → VictoriaMetrics → Grafana | Exporter, metric contracts, freshness handling | Add when unified time-series monitoring is useful |

Grafana OSS includes a PostgreSQL data source. Give it a dedicated account with `SELECT` only on approved reporting tables/views, not Umami's application credentials. Direct queries against Umami internals are possible but couple dashboards to its schema; the API-to-reporting-table approach isolates that dependency. [Grafana PostgreSQL configuration](https://grafana.com/docs/grafana/latest/datasources/postgres/configure/)

No official turnkey Umami-to-Prometheus business-metrics exporter was established by this review. Treat the exporter as custom work, not an assumed native `/metrics` feature.

Proposed exporter snapshots, refreshed every five minutes:

| Metric | Type | Meaning |
|---|---|---|
| `blog_pageviews_24h{site,post}` | Gauge | Captured post pageviews in the rolling previous 24 hours |
| `blog_engaged_reads_24h{site,post}` | Gauge | Engaged views in the rolling start-time cohort |
| `blog_active_read_seconds_mean_24h{site,post}` | Gauge | Mean observed active time for that cohort; absent if empty |
| `blog_analytics_last_success_timestamp_seconds{site}` | Gauge | Last successful refresh, for freshness alerts |

Rolling-window totals are **gauges**, not monotonic counters: do not apply `rate()` or `increase()` to them or sum overlapping windows. Keep detailed event data in PostgreSQL. Use only a bounded set of published post paths as labels; never export IPs, visitor/view IDs, arbitrary URLs, or free-form campaign strings as labels. Keep country and post breakdowns separate unless the combined cardinality is explicitly budgeted.

Expose exporter data privately. On a failed refresh, keep the last-success timestamp unchanged and make stale data visible in Grafana; do not silently present old snapshots as current. Existing Nginx/infrastructure metrics remain useful alongside these reports, but are not human readership counts.

## Optional public statistics

Start with a private owner dashboard. If public statistics are wanted later:

| Presentation | Approach | Boundary |
|---|---|---|
| Public traffic dashboard | Umami share URL or selected public board | Review every exposed view and backing API response before sharing |
| Post view count and selected reading aggregates | Worker publishes cached, allowlisted JSON; Hugo fetches it | Only publish aggregate fields; no browser access to authenticated APIs |
| Grafana dashboard | Keep authenticated initially | Do not enable broad anonymous access to private data sources |

Umami supports read-only share URLs and public boards. Read-only does not itself mean every underlying field is suitable for public release. For iframe embedding, the current documentation lists `ALLOWED_FRAME_URLS` as a **build-time** variable, so setting a runtime Compose variable alone may not suffice. A normal dashboard link avoids that embedding configuration. [Public dashboard guide](https://docs.umami.is/docs/guides/create-a-public-dashboard), [Environment variables](https://docs.umami.is/docs/environment-variables)

For public per-post counters, recommend the cached-JSON approach. Include a refresh timestamp, suppress tiny geographic groups, and show an unavailable state if the data is missing—not a fabricated zero. Label counts as pageviews or engaged reads according to their actual definition.

## Self-hosting and operational practices

- Pin a tested Umami release/image and a compatible, supported PostgreSQL version. Record versions and run API/tracker regression checks before upgrades; do not deploy floating `latest` unattended.
- Configure strong application/database secrets, replace installation-default credentials, and keep administration authenticated. Restrict database access to the application and approved reporting clients.
- Set `DISABLE_TELEMETRY=1` if unwanted outbound telemetry should be disabled. Review other optional outbound features and use local GeoIP rather than a hosted geolocation API. [Umami environment variables](https://docs.umami.is/docs/environment-variables)
- Geolocation can use local MaxMind GeoLite data instead of Cloudflare/Vercel headers. Dataset licensing and update/download requirements are separate from Umami's MIT software license; verify them before provisioning. Trust forwarded client-IP headers only from configured proxies. [Location metrics](https://docs.umami.is/docs/metric-definitions)
- Avoid collecting names, emails, persistent custom identities, search text, tokens, or sensitive query/referrer parameters. Umami's statement that it does not store raw IPs does not cover Nginx access logs or other infrastructure logs.
- Define a retention policy before launch—for example, 90 days of detailed events and 13 months of aggregate reports. These are proposed policy values, not claimed Umami defaults; validate supported cleanup procedures and preserve aggregates before deleting source events.
- Back up PostgreSQL and configuration, encrypt off-host backups, and test restoration. A container restart is not a backup, and an application image rollback may not reverse a database migration.
- Monitor database disk usage, application errors, failed collection requests, backup age, and reporting freshness. Apply reasonable collection-endpoint rate/body limits; a public website ID and browser domain allowlist do not prevent forged traffic.

JavaScript blockers and disabled scripts cause undercounting; browser analytics and access-log totals should not be expected to match. Publish a clear tracking notice and assess consent requirements for the actual deployment and audience rather than assuming self-hosting alone resolves them.

## Rollout and acceptance criteria

| Phase | Deliverable | Acceptance gate |
|---|---|---|
| 1: Native analytics | Pinned Umami/PostgreSQL deployment, HTTPS, production-only Hugo tracker | One native pageview per navigation; correct post grouping, referrer/device/country checks; local previews excluded |
| 2: Reading analytics | Article tracker, event contract, idempotent reporting worker | Foreground/background/idle tests, deduplication, accurate synthetic averages/medians and denominators |
| 3: Grafana | Read-only reporting datasource and per-post dashboard | Fixed-period results reconcile with source events; no write privileges or credential leakage |
| 4: Optional publishing/export | Cached public counters and/or VictoriaMetrics exporter | Reviewed public payloads, bounded labels, correct gauge semantics, visible stale-data behavior |

Before production acceptance, also test blocked tracker requests, slow/offline connections, tab close, back/forward-cache restores, short articles, and long reading sessions. The blog must remain usable throughout. For any implemented frontend UI changes, visually verify phone, tablet, and desktop layouts as required by this repository.

This is a documentation-backed feasibility proposal, not a live deployment validation. Server capacity, final hostname, release compatibility, and actual GeoIP behavior still need checking during implementation.

## Decision

**Proceed with Umami for basic self-hosted blog analytics.** Its deployment fits the existing Hugo/Nginx setup without requiring a CMS plugin. Budget separately for the reading tracker and reporting worker if active reading time is required. Prefer PostgreSQL reporting for flexible Grafana analysis, and add VictoriaMetrics export only for selected aggregate trends—not as the primary event store.
