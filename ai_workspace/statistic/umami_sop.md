# Umami Rollout SOP (Phased)

This is the execution SOP for `umami_proposal.md`. It breaks the rollout into phases so a minimal,
working analytics setup can ship quickly, with heavier integrations deferred deliberately.

## Phase overview

| Phase | Goal | Status |
|---|---|---|
| 1 | Launch native Umami analytics (pageviews, referrers, devices, countries) | **This document — do this now** |
| 2 | Per-post reading analytics (custom events + reporting worker) | Not started — next, after phase 1 is stable |
| 3 | Grafana integration on reporting tables | **On hold** |
| 4 | VictoriaMetrics export and optional public counters | **On hold** |

Phases 3 and 4 are intentionally out of scope for this SOP; see the one-paragraph placeholders at the
bottom. Only phase 1 is detailed below.

## Actual topology for this rollout

Umami + PostgreSQL run on the **Raspberry Pi's existing Kubernetes cluster**, not on the VPS. The VPS
only serves the static Hugo site and terminates public HTTPS/Nginx, same as today. The VPS reaches the
Pi over an **existing VPS↔Pi tunnel** (already set up, outside this SOP's scope). Umami is published at
a subpath of the main domain, `chejinying.com/umami/`, not a separate subdomain — so no new DNS record
is needed.

```text
Browser --GET /----------------------> VPS Nginx --> Hugo static files
Browser --GET/POST /umami/*----------> VPS Nginx --(existing tunnel)--> Pi k8s: Umami (BASE_PATH=/umami) -> PostgreSQL (PVC)
```

---

## Phase 1: Launch native Umami analytics

### 0. Prerequisites checklist

Confirm these before starting — none of them are new infrastructure, just verifying what already exists:

- [ ] `kubectl` access to the Pi's Kubernetes cluster from wherever you'll run the apply commands.
- [ ] The Pi cluster has a default `StorageClass` available for a PostgreSQL PVC (`kubectl get storageclass`).
- [ ] The existing VPS↔Pi tunnel is up and you know the address the VPS uses to reach the Pi (call it
      `PI_TUNNEL_ADDR` below — fill in the real value when you execute this).
- [ ] SSH/config access to the VPS's Nginx configuration (this lives on the VPS host directly, **not**
      in this git repo — `vps.yml` only ever rsyncs `public/`, so Nginx vhost changes are a manual,
      out-of-band step).
- [ ] `chejinying.com` DNS already points at the VPS — no new DNS record needed since we're using a
      subpath, not a subdomain.

### 1. Generate secrets

Do this on a trusted machine, not committed anywhere:

```bash
openssl rand -hex 32   # -> APP_SECRET
openssl rand -hex 24   # -> POSTGRES_PASSWORD
```

Create a Kubernetes Secret imperatively (never as a plaintext manifest in git):

```bash
kubectl create namespace umami
kubectl -n umami create secret generic umami-secrets \
  --from-literal=app-secret='<APP_SECRET>' \
  --from-literal=postgres-password='<POSTGRES_PASSWORD>'
```

### 2. PostgreSQL manifest (Pi cluster)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: umami-postgres-data
  namespace: umami
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 5Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: umami-postgres
  namespace: umami
spec:
  replicas: 1
  strategy: { type: Recreate }
  selector: { matchLabels: { app: umami-postgres } }
  template:
    metadata: { labels: { app: umami-postgres } }
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine   # pin this exact tag; do not track a floating major-only tag
          env:
            - name: POSTGRES_DB
              value: umami
            - name: POSTGRES_USER
              value: umami
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef: { name: umami-secrets, key: postgres-password }
          ports:
            - containerPort: 5432
          volumeMounts:
            - { name: data, mountPath: /var/lib/postgresql/data, subPath: pgdata }
      volumes:
        - name: data
          persistentVolumeClaim: { claimName: umami-postgres-data }
---
apiVersion: v1
kind: Service
metadata:
  name: umami-postgres
  namespace: umami
spec:
  selector: { app: umami-postgres }
  ports:
    - { port: 5432, targetPort: 5432 }
```

### 3. Umami manifest (Pi cluster)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: umami
  namespace: umami
spec:
  replicas: 1
  selector: { matchLabels: { app: umami } }
  template:
    metadata: { labels: { app: umami } }
    spec:
      containers:
        - name: umami
          image: docker.umami.is/umami-software/umami:postgresql-latest   # pin to a tested release tag before launch, not `latest`
          env:
            - name: DATABASE_URL
              value: postgresql://umami:$(POSTGRES_PASSWORD)@umami-postgres:5432/umami
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef: { name: umami-secrets, key: postgres-password }
            - name: APP_SECRET
              valueFrom:
                secretKeyRef: { name: umami-secrets, key: app-secret }
            - name: BASE_PATH
              value: /umami
            - name: DISABLE_TELEMETRY
              value: "1"
          ports:
            - containerPort: 3000
---
apiVersion: v1
kind: Service
metadata:
  name: umami
  namespace: umami
spec:
  type: NodePort
  selector: { app: umami }
  ports:
    - port: 3000
      targetPort: 3000
      nodePort: 30090   # arbitrary; must be reachable from the VPS across the existing tunnel
```

Notes:

- `BASE_PATH=/umami` makes Umami generate correct asset/script/API URLs for the subpath it's proxied
  under — required since we're not using a dedicated subdomain.
- `NodePort` is the simplest way to reach the Pi from the VPS over the existing tunnel without needing
  an Ingress controller. **Caveat:** a NodePort is bound on all node interfaces by default. If the Pi's
  node has any interface beyond the tunnel that could reach it (e.g. exposed on the home LAN or router),
  firewall port `30090` to accept connections only from the tunnel peer. If the cluster already has an
  Ingress controller, prefer routing through that instead and drop the NodePort.

### 4. Apply and smoke-test on the Pi

```bash
kubectl apply -f postgres.yaml
kubectl apply -f umami.yaml
kubectl -n umami get pods -w
# once ready, verify from the Pi/cluster node itself:
curl -i http://localhost:30090/umami/api/heartbeat
```

### 5. Wire up the VPS Nginx reverse proxy

On the VPS (manual, out-of-band edit — not part of this repo's release pipeline):

```nginx
upstream umami_pi {
    server PI_TUNNEL_ADDR:30090;
    keepalive 16;
}

location /umami/ {
    proxy_pass         http://umami_pi/umami/;
    proxy_http_version 1.1;
    proxy_set_header   Connection        "";
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;

    # basic abuse protection on the collection endpoint
    limit_req zone=umami_zone burst=20 nodelay;
}
```

The `upstream { keepalive }` block reuses connections to the Pi across requests instead of paying a
fresh tunnel connection-setup cost on every single pageview — `proxy_http_version 1.1` and the empty
`Connection` header are required for keepalive to actually apply. Add the matching `limit_req_zone` in
the `http {}` block, e.g. `limit_req_zone $binary_remote_addr zone=umami_zone:10m rate=5r/s;`. Reload
Nginx after editing (`sudo systemctl reload nginx`). Do not expose the Pi's NodePort directly — the VPS
is the only public entry point.

**Reliability caveat:** both `script.js` and the event-collection endpoint are served across the
VPS↔Pi tunnel, so their availability is tied to the Pi's uptime and home network/ISP — not the VPS's.
This is a deliberate tradeoff, not a performance problem: request volume at blog scale is trivial for
any of Nginx, the tunnel, or the Pi. If the Pi or tunnel is down, the tracker fails to load or send
silently (per the fail-open rule below) and you simply lose analytics coverage for that window — the
blog itself is unaffected since it's served entirely from the VPS. Accept this for a personal blog;
don't extrapolate this topology to anything needing production-grade analytics availability.

### 6. Create the Umami site and get the website ID

1. Visit `https://chejinying.com/umami/` and log in with the Umami default admin credentials.
2. **Immediately** change the admin password — this is a public URL now.
3. Create a new site, e.g. name `chejinying-blog`, domain `chejinying.com`.
4. Copy the generated **Website ID** (public, non-secret config — safe to put in `hugo.toml`).

### 7. Add the Hugo tracker (proposed diff — do not apply without confirming)

Add to `hugo.toml` under `[params]`:

```toml
[params.umami]
  websiteId = "<WEBSITE_ID_FROM_STEP_6>"
```

New partial `layouts/partials/umami-tracker.html`:

```html
{{ if hugo.IsProduction }}
{{ with .Site.Params.umami.websiteId }}
<script defer
  src="/umami/script.js"
  data-website-id="{{ . }}"
  data-host-url="https://chejinying.com/umami"
  data-domains="chejinying.com"></script>
{{ end }}
{{ end }}
```

Include it from `layouts/partials/extended_head.html` (append at the end):

```html
{{ partial "umami-tracker.html" . }}
```

`hugo.IsProduction` is true for a plain `hugo` build (what `vps.yml` runs) and false under
`hugo server`, so local previews are excluded automatically without an extra flag. No CSP is currently
configured on this site, so there's nothing to update there for phase 1.

**Per this repo's CLAUDE.md, show this diff and wait for confirmation before actually editing these
files** — the snippets above are the proposal; nothing has been applied to `hugo.toml`,
`extended_head.html`, or a new partial yet.

### 8. Verify end-to-end

- [ ] `hugo server` locally → confirm the tracker script is **not** present in rendered HTML.
- [ ] Push to `main`, let `vps.yml` deploy as usual.
- [ ] Open `https://chejinying.com/` in an incognito window; in DevTools Network tab confirm
      `script.js` loads from `/umami/script.js` (200) and a request to `/umami/api/send` (or the
      tracker's configured endpoint) returns 200.
- [ ] Umami dashboard at `https://chejinying.com/umami/` shows the pageview in real time.
- [ ] Disable JavaScript / block the request and confirm the blog still renders and navigates fine
      (tracker failure must never break the site).
- [ ] Visit a few different post paths and confirm they group correctly as distinct pages in Umami.

### 9. Minimal ops hygiene for phase 1 (not deferrable)

- [ ] Admin password changed from default (step 6).
- [ ] `DISABLE_TELEMETRY=1` set (already in the manifest above).
- [ ] A basic PostgreSQL backup exists — minimally, a daily `CronJob` running `pg_dump` to a separate
      PVC or off-Pi location, retaining ~7 days. Full retention-policy design, encryption, and
      off-host copies are real requirements from `umami_proposal.md`'s "Self-hosting and operational
      practices" section, but are **not** a phase-1 blocker — track them as immediate phase-1.5
      follow-up, not something to skip indefinitely.
- [ ] NodePort exposure reviewed per the caveat in step 3.

### Acceptance gate for phase 1

Matches `umami_proposal.md`'s phase-1 row: one native pageview per navigation, correct post-path
grouping, referrer/device/country checks look sane, local previews excluded, dashboard reachable only
to the authenticated owner, and the tracker never blocks page rendering when blocked or offline.

---

## Phase 2: Reading analytics — planned next, not detailed here

Custom `reading_start`/`reading_checkpoint` events, the article tracker scoped to `.post-content`, and
the idempotent reporting worker described in `umami_proposal.md`'s "Per-post reading measurement"
section. Start this only once phase 1 has run cleanly for a while and tracking coverage looks healthy.
Deserves its own SOP once phase 1 is live — not drafted yet.

## Phase 3: Grafana integration — ON HOLD

Read-only reporting datasource and per-post dashboard, per `umami_proposal.md`. Deliberately deferred;
revisit after phase 2 ships reporting tables to query against.

## Phase 4: VictoriaMetrics export and public publishing — ON HOLD

Exporter snapshots into the existing VictoriaMetrics stack, and/or cached public pageview counters.
Deliberately deferred; lowest priority of the four phases.
