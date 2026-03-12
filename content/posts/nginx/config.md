---
title: "Learn nginx by configurations"
date: "2026-03-12T10:10:51+08:00"
tags: ["nginx"]
description: "Let's dive into nginx key concepts via configurations."
---

## TL;DR

**Nginx is an event-driven web server.** One worker process per CPU core, each running a single-threaded event loop — handling thousands of connections concurrently without spawning threads or processes per request.

**Config is hierarchical:**
```
main → events → http → server → location
                      → upstream
```

| Context | Purpose |
|---|---|
| `main` | worker processes, global settings |
| `events` | connection handling (max connections, I/O method) |
| `http` | all HTTP settings, shared across servers |
| `upstream` | named group of backend servers (load balancing) |
| `server` | a virtual host — matches by `listen` port + `server_name` |
| `location` | request routing within a server — matches by URI |

**Key capabilities:**

| Feature | How |
|---|---|
| Serve static files | `root` + `location` — uses `sendfile()` zero-copy |
| Reverse proxy | `proxy_pass` forwards requests to backend |
| Load balancing | `upstream` with `least_conn` / `ip_hash` / round-robin |
| SSL termination | `ssl_certificate` + `ssl_certificate_key` in `server` |
| Rate limiting | `limit_req_zone` (define) + `limit_req` (enforce) |
| Caching | `proxy_cache_path` (define) + `proxy_cache` (enable) |
| WebSocket | `Upgrade` + `Connection "upgrade"` headers in `location` |
| Compression | `gzip on` + `gzip_types` |

**`server` vs `upstream`:**
- `server` — nginx **listens** here, faces clients
- `upstream` — nginx **forwards** here, faces backends
- `proxy_pass http://upstream_name` connects the two

---

## The Complete Config

A realistic config for `taskflow.io` — React frontend + Node.js API cluster. Every line maps to a key nginx concept.

```nginx
# /etc/nginx/nginx.conf

worker_processes auto;                        # 1 worker per CPU core

events {
    worker_connections 1024;                  # max connections per worker
}

http {
    # ── Gzip ─────────────────────────────────────────────────────────────
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;

    # ── Rate Limiting ─────────────────────────────────────────────────────
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;

    # ── Proxy Cache ───────────────────────────────────────────────────────
    proxy_cache_path /var/cache/nginx levels=1:2
                     keys_zone=app_cache:10m max_size=1g;

    # ── Upstream: Node.js API cluster ────────────────────────────────────
    upstream nodejs_api {
        least_conn;
        server 127.0.0.1:3001 max_fails=3 fail_timeout=10s;
        server 127.0.0.1:3002 max_fails=3 fail_timeout=10s;
        server 127.0.0.1:3003 backup;
        keepalive 32;
    }

    # ── HTTP → HTTPS redirect ─────────────────────────────────────────────
    server {
        listen 80;
        server_name taskflow.io;
        return 301 https://$host$request_uri;
    }

    # ── Main server ───────────────────────────────────────────────────────
    server {
        listen 443 ssl;
        server_name taskflow.io;

        ssl_certificate     /etc/letsencrypt/live/taskflow.io/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/taskflow.io/privkey.pem;
        ssl_protocols       TLSv1.2 TLSv1.3;

        root /var/www/taskflow/dist;

        # Static assets — cache 1 year in browser
        location ~* \.(js|css|png|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # React SPA — fallback to index.html for client-side routing
        location / {
            try_files $uri $uri/ /index.html;
        }

        # API — proxy to Node.js cluster with rate limiting + cache
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;

            proxy_cache       app_cache;
            proxy_cache_valid 200 30s;
            add_header        X-Cache-Status $upstream_cache_status;

            proxy_pass         http://nodejs_api;
            proxy_http_version 1.1;
            proxy_set_header   Connection "";
            proxy_set_header   Host            $host;
            proxy_set_header   X-Real-IP       $remote_addr;
            proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_connect_timeout 5s;
            proxy_read_timeout    30s;
        }

        # WebSocket — real-time updates
        location /ws/ {
            proxy_pass        http://nodejs_api;
            proxy_http_version 1.1;
            proxy_set_header  Upgrade    $http_upgrade;
            proxy_set_header  Connection "upgrade";
            proxy_read_timeout 3600s;
        }
    }
}
```

## Key Concept Map

```
main          → worker_processes
events        → worker_connections
http          → gzip, limit_req_zone, proxy_cache_path, upstream
  upstream    → load balancing, health check, backup, keepalive
  server (80) → HTTP→HTTPS redirect
  server (443)→ SSL termination, virtual host
    location ~* \.(js|css|png|svg)$  → regex match, static file + browser cache
    location /                       → prefix match, SPA try_files fallback
    location /api/                   → proxy + rate limit + server-side cache
    location /ws/                    → WebSocket (Upgrade header)
```

## Concept Breakdown

### Process Model — `worker_processes` + `events`

Nginx uses one worker process per CPU core. Each worker runs a **single-threaded event loop** handling thousands of connections concurrently via non-blocking I/O — no thread-per-connection overhead.

```nginx
worker_processes auto;       # match CPU core count
events {
    worker_connections 1024; # max simultaneous connections per worker
}
```

Total max connections = `worker_processes × worker_connections`.

---

### Upstream — Load Balancing + Health Check

`upstream` is defined inside `http`, at the same level as `server`. It's a named group of backend servers — does nothing until referenced by `proxy_pass`.

```nginx
upstream nodejs_api {
    least_conn;                                        # route to least busy server
    server 127.0.0.1:3001 max_fails=3 fail_timeout=10s;  # auto health check
    server 127.0.0.1:3002 max_fails=3 fail_timeout=10s;
    server 127.0.0.1:3003 backup;                     # standby if others fail
    keepalive 32;                                      # reuse TCP connections
}
```

| Parameter | Meaning |
|---|---|
| `least_conn` | route to server with fewest active connections |
| `max_fails=3` | mark server down after 3 consecutive failures |
| `fail_timeout=10s` | keep it marked down for 10s, then retry |
| `backup` | only receives traffic when all primary servers are down |
| `keepalive 32` | maintain 32 persistent connections to upstream |

**Load balancing algorithms:**

| Algorithm | Directive | Use case |
|---|---|---|
| Round-robin | _(default)_ | even, stateless workloads |
| Least connections | `least_conn` | uneven request durations |
| Sticky session | `ip_hash` | session-dependent apps |

---

### Virtual Hosting — `server` + `server_name`

Multiple `server` blocks share the same IP. Nginx selects the right one by matching the request's `Host` header against `server_name`.

```nginx
server {
    listen 80;
    server_name taskflow.io;
    return 301 https://$host$request_uri;   # redirect all HTTP to HTTPS
}

server {
    listen 443 ssl;
    server_name taskflow.io;
    # ...
}
```

---

### SSL Termination

Nginx handles TLS, so backend servers receive plain HTTP — no TLS overhead on app servers.

```nginx
ssl_certificate     /etc/letsencrypt/live/taskflow.io/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/taskflow.io/privkey.pem;
ssl_protocols       TLSv1.2 TLSv1.3;
```

---

### Location Matching

Nginx evaluates `location` blocks in priority order:

| Modifier | Type | Priority |
|---|---|---|
| `= /path` | exact match | 1st |
| `^~ /prefix` | preferential prefix | 2nd |
| `~ pattern` | case-sensitive regex | 3rd |
| `~* pattern` | case-insensitive regex | 3rd |
| `/prefix` | longest prefix | 4th |

**Static assets** — regex match, served directly from disk:

```nginx
location ~* \.(js|css|png|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

`~*` = case-insensitive regex. `\.` = literal dot. `$` = end of string.
Tells the browser to cache these files for 1 year — safe because filenames contain a content hash (e.g. `main.a3f9c2.js`).

**SPA fallback** — prefix match, handles client-side routing:

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

`try_files` checks: does the file exist on disk? does the directory exist? If neither, serve `index.html` — letting React Router handle the path.

---

### Reverse Proxy

```nginx
location /api/ {
    proxy_pass         http://nodejs_api;
    proxy_http_version 1.1;
    proxy_set_header   Connection "";             # required for keepalive
    proxy_set_header   Host            $host;
    proxy_set_header   X-Real-IP       $remote_addr;
    proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_connect_timeout 5s;
    proxy_read_timeout    30s;
}
```

`X-Real-IP` and `X-Forwarded-For` pass the original client IP to the backend — otherwise the backend sees only nginx's address.

---

### Rate Limiting

Defined at `http` level, applied inside `location`:

```nginx
# http level: define the zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;

# location level: enforce it
limit_req zone=api_limit burst=20 nodelay;
```

- `10m` — 10MB shared memory, holds ~160k IP addresses
- `rate=20r/s` — steady-state limit per IP
- `burst=20` — allow up to 20 queued requests above the rate
- `nodelay` — process burst requests immediately instead of spacing them out

---

### Proxy Cache

```nginx
# http level: define cache storage
proxy_cache_path /var/cache/nginx levels=1:2
                 keys_zone=app_cache:10m max_size=1g;

# location level: enable it
proxy_cache       app_cache;
proxy_cache_valid 200 30s;
add_header        X-Cache-Status $upstream_cache_status;
```

`X-Cache-Status` exposes `HIT`, `MISS`, or `BYPASS` in the response header — useful for debugging. Cache key defaults to the full URL, so each unique URL is cached separately.

---

### WebSocket

WebSocket requires an HTTP → WS protocol upgrade. Two headers are mandatory:

```nginx
location /ws/ {
    proxy_pass        http://nodejs_api;
    proxy_http_version 1.1;
    proxy_set_header  Upgrade    $http_upgrade;   # signals protocol upgrade
    proxy_set_header  Connection "upgrade";
    proxy_read_timeout 3600s;                     # keep connection alive 1hr
}
```

Without `Upgrade` + `Connection "upgrade"`, nginx closes the connection after the HTTP handshake and the WebSocket never establishes.

---

## References

- [nginx documentation](https://nginx.org/en/docs/)
- [Beginner's Guide](https://nginx.org/en/docs/beginners_guide.html)
- [ngx_http_core_module — `location`](https://nginx.org/en/docs/http/ngx_http_core_module.html#location)
- [ngx_http_upstream_module](https://nginx.org/en/docs/http/ngx_http_upstream_module.html)
- [ngx_http_proxy_module — `proxy_pass`](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [ngx_http_limit_req_module — rate limiting](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- [ngx_http_proxy_module — `proxy_cache`](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache)
- [WebSocket proxying](https://nginx.org/en/docs/http/websocket.html)
