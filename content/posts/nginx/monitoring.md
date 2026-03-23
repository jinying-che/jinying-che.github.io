---
title: "How to Monitor Nginx?"
date: "2026-03-16T10:00:00+08:00"
tags: ["nginx"]
description: "The best practices to monitor nginx with VictoriaMetrics and Grafana"
---

## Architecture

```
Nginx :8080/nginx_status
    ↓  scrape
nginx-prometheus-exporter :9113/metrics   [systemd]
    ↓  scrape
vmagent :8429                             [systemd, already running]
    ↓  remote_write
vminsert :8480  →  vmstorage :8400        [systemd, already running]

Grafana :3000  →  vmselect :8481          [already running]
```

Prerequisites: VictoriaMetrics cluster (vmstorage, vminsert, vmselect, vmagent) and Grafana are already running. See [VictoriaMetrics Cluster Setup](/posts/vm/vm_setup/).

---

## Step 1 — Enable nginx stub_status

Add a dedicated server block that only exposes the status endpoint on localhost:

```nginx
# /etc/nginx/conf.d/stub_status.conf
server {
    listen 8080;
    server_name localhost;

    location /nginx_status {
        stub_status;
        allow 127.0.0.1;
        deny all;
    }
}
```

```bash
sudo nginx -t && systemctl reload nginx
```

Verify:

```bash
curl http://localhost:8080/nginx_status
# Active connections: 3
# server accepts handled requests
#  10 10 15
# Reading: 0 Writing: 1 Waiting: 2
```

| Field | Meaning |
|---|---|
| `Active connections` | currently open client connections |
| `accepts` | total accepted connections (lifetime counter) |
| `handled` | total handled connections — drops = accepts − handled |
| `requests` | total HTTP requests (lifetime counter) |
| `Reading` | workers reading request headers |
| `Writing` | workers writing response to client |
| `Waiting` | keep-alive idle connections |

---

## Step 2 — Install nginx-prometheus-exporter

The exporter translates the stub_status plaintext into Prometheus-format metrics at `:9113/metrics`.

**Check OS architecture:**

```bash
uname -m
# x86_64   → linux_amd64
# aarch64  → linux_arm64
# armv7l   → linux_armv7
```

**Download binary:**

```bash
ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/;s/armv7l/armv7/')
VER=$(curl -s https://api.github.com/repos/nginx/nginx-prometheus-exporter/releases/latest | grep -Po '"tag_name": "v\K[^"]+')
wget "https://github.com/nginx/nginx-prometheus-exporter/releases/download/v${VER}/nginx-prometheus-exporter_${VER}_linux_${ARCH}.tar.gz"
tar xzf nginx-prometheus-exporter_${VER}_linux_${ARCH}.tar.gz
sudo install -m 755 nginx-prometheus-exporter /usr/local/bin/nginx-prometheus-exporter
```

**Create systemd service:**

```ini
# /etc/systemd/system/nginx-prometheus-exporter.service
[Unit]
Description=Nginx Prometheus Exporter
After=network.target

[Service]
Type=simple
User=victoriametrics
Group=victoriametrics
ExecStart=/usr/local/bin/nginx-prometheus-exporter \
    --nginx.scrape-uri=http://localhost:8080/nginx_status \
    --web.listen-address=:9113
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nginx-prometheus-exporter
```

Verify metrics:

```bash
curl -s http://localhost:9113/metrics | grep nginx
# nginx_connections_active 3
# nginx_connections_reading 0
# nginx_connections_waiting 2
# nginx_connections_writing 1
# nginx_http_requests_total 15
# nginx_up 1
```

**Metrics exposed:**

| Metric | Type | Description |
|---|---|---|
| `nginx_up` | Gauge | 1 if nginx is reachable |
| `nginx_connections_active` | Gauge | currently active connections |
| `nginx_connections_accepted_total` | Counter | total accepted connections |
| `nginx_connections_handled_total` | Counter | total handled connections |
| `nginx_connections_reading` | Gauge | reading request headers |
| `nginx_connections_writing` | Gauge | writing response |
| `nginx_connections_waiting` | Gauge | keep-alive idle |
| `nginx_http_requests_total` | Counter | total HTTP requests |

---

## Step 3 — Add nginx job to vmagent scrape config

Add the nginx exporter as a scrape target in `/etc/vmagent/scrape.yml`:

```yaml
scrape_configs:
  # ... existing jobs (vmstorage, vminsert, vmselect, vmagent) ...

  - job_name: nginx
    static_configs:
      - targets: ['localhost:9113']
```

Reload vmagent to pick up the new config (sends SIGHUP):

```bash
sudo systemctl reload vmagent
```

Verify vmagent is scraping nginx:

```bash
# Check target status
curl -s http://localhost:8429/targets | grep nginx
```

Or open `http://localhost:8429/targets` in a browser — the nginx job should show `state: up`.

---

## References

- [nginx-prometheus-exporter](https://github.com/nginx/nginx-prometheus-exporter)
- [ngx_http_stub_status_module](https://nginx.org/en/docs/http/ngx_http_stub_status_module.html)
- [Grafana Dashboard 12708](https://grafana.com/grafana/dashboards/12708)
- [VictoriaMetrics Cluster Setup](/posts/vm/vm_setup/)
