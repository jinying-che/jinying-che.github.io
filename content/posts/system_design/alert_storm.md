---
title: "Handling Alert Storms"
date: "2026-03-24T15:00:00+08:00"
tags: ["system_design", "monitor", "alerting"]
description: "Strategies for handling alert storms in monitoring systems — grouping, inhibition, deduplication, topology-based RCA, and LLM enrichment"
draft: true
---

## The Problem

A single root cause (e.g., server down) triggers cascading failures across dependent services. Each service has its own alerting rules, resulting in a massive volume of alerts — **an alert storm**. Oncall gets flooded and struggles to identify the root cause.

```
        ┌──────────┐
        │    LB    │ ← alert: 5xx spike
        └────┬─────┘
             │
     ┌───────┴───────┐
     ▼               ▼
┌─────────┐    ┌─────────┐
│  App-1  │    │  App-2  │ ← alert: unhealthy
└────┬────┘    └────┬────┘
     └──────┬───────┘
            ▼
      ┌──────────┐
      │    DB    │ ← alert: connection failure
      └────┬─────┘
           ▼
      ┌──────────┐
      │   Disk   │ ← alert: IO error (ROOT CAUSE)
      └──────────┘
```

**Result**: 5 alerts for 1 root cause.

---

## Solution Overview

| Strategy | What It Solves | Complexity |
|---|---|---|
| Grouping | Many alerts → one notification | Low |
| Deduplication | Same alert fired multiple times | Low |
| Inhibition | Suppress symptoms when root cause known | Low |
| Severity Routing | Reduce noise from low-priority alerts | Low |
| Flap Detection | Unstable checks spamming on/off | Medium |
| Topology-based RCA | Identify root cause from dependency graph | Medium–High |
| LLM Enrichment | Summarize, correlate unstructured context | Medium |

---

## 1. Alert Grouping

Bundle related alerts into a single notification based on shared attributes within a time window.

**How**: Group by common labels like `cluster`, `node`, `region`, or `service`.

Alertmanager example:
```yaml
route:
  group_by: ['cluster', 'alertname']
  group_wait: 30s       # wait before sending first notification
  group_interval: 5m    # wait before sending updates
```

500 alerts from one dead node → 1 grouped notification.

---

## 2. Alert Deduplication

Identical alerts (same source, same rule) within a time window are collapsed into one using a **dedup key** (usually a hash of alert labels).

Most alert systems (PagerDuty, OpsGenie, Alertmanager) do this natively.

---

## 3. Alert Inhibition

Suppress downstream alerts when a root-cause alert is already firing.

| Root Alert | Suppressed Alerts |
|---|---|
| `NodeDown` | All `ServiceDown` on that node |
| `NetworkUnreachable` | All timeout/connection alerts in that zone |

Alertmanager example:
```yaml
inhibit_rules:
  - source_matchers:
      - alertname="NodeDown"
    target_matchers:
      - severity="warning"
    equal: ['instance']
```

**Limitation**: Requires manually defining known cause-symptom pairs. Does not handle unknown or complex cascades.

---

## 4. Severity-Based Routing & Throttling

Route alerts differently based on severity:

- **Critical** → page immediately (with dedup)
- **Warning** → batch into digest every 5–15 min
- **Info** → dashboard only, no notification

Prevents low-severity noise from burying the real signal.

---

## 5. Flap Detection

If an alert fires → resolves → fires repeatedly, mark it as **flapping** and suppress until stable.

Avoids notification spam from unstable health checks or metrics hovering at threshold boundaries.

---

## 6. Topology-Based Root Cause Analysis (RCA)

Model the system as a dependency graph, then walk the graph to find the **deepest failing node** — that's the root cause. Everything above it is a symptom.

### How It Works

**Step 1 — Build the dependency model**

Sources for dependency data:
- **Static config** — manually defined topology (CMDB, service catalog)
- **Auto-discovery** — derived from service mesh (Istio/Envoy), Kubernetes, or tracing data (OpenTelemetry)

```yaml
services:
  load-balancer:
    depends_on: [app-1, app-2]
  app-1:
    depends_on: [database]
  app-2:
    depends_on: [database]
  database:
    depends_on: [disk]
```

**Step 2 — Correlate incoming alerts**

When alerts arrive within a time window:

1. Map each alert to a node in the graph
2. Walk **downstream** (toward dependencies) to find the deepest failing node
3. Mark that as **root cause**, everything upstream as **symptom**

```
Alert: LB_5xx_spike        → node: LB         → symptom
Alert: App1_unhealthy      → node: App-1      → symptom
Alert: App2_unhealthy      → node: App-2      → symptom
Alert: DB_connection_fail  → node: DB         → symptom
Alert: Disk_IO_error       → node: Disk       → ROOT CAUSE
```

**Step 3 — Notify only the root cause**

Symptoms are either suppressed or attached as context to the root cause alert.

### The Hard Part

The algorithm is simple (graph traversal). **Keeping the dependency graph accurate is the hard part** — services get added/removed, infra changes constantly.

Best approach: use **distributed tracing** (OpenTelemetry) to auto-derive dependencies. The trace data already encodes the call graph and stays current automatically.

### When to Invest

| Scale | Approach |
|---|---|
| < 20 services | Manual inhibition rules are sufficient |
| 20–100 services | Static dependency graph + simple correlation |
| 100+ services | Auto-discovery (tracing, service mesh) becomes necessary |

---

## 7. LLM as an Enrichment Layer

LLMs are **not** a replacement for traditional alert correlation — they complement it.

### What LLMs Do Well

**Summarize alert storms** — Turn 200 grouped alerts into a human-readable incident summary:

> "DB primary disk full on node-3. Impact: 12 services degraded. Suggested action: run disk cleanup runbook."

**Correlate unstructured data** — Connect alerts with context that rule-based systems cannot:
- Recent deploy changelogs / git commits
- Log messages around the alert time
- Past incident postmortems

```
Alert:    App-1 latency spike at 14:03
Deploy:   "Updated connection pool config" merged at 13:58
Past RCA: "Connection pool misconfiguration caused similar spike in Jan"

LLM:  "Likely caused by the connection pool config change
       deployed 5 minutes ago. Similar incident on 2026-01-15."
```

**Suggest runbooks** — RAG over internal runbooks and postmortems to recommend remediation steps.

### What LLMs Are Bad At (Today)

| Problem | Why |
|---|---|
| Hallucination | May confidently blame the wrong component |
| Latency | Adds seconds; alert correlation needs sub-second |
| Non-determinism | Same storm → different analysis each time |
| Cost | Feeding 1000s of alerts/min into LLM is expensive |

### Production Architecture

```
Alerts ──► Dedup / Group / Inhibit (Alertmanager)      ← deterministic, fast
                │
                ▼
           Correlation Engine (topology graph)           ← structured RCA
                │
                ▼
           LLM Enrichment (async, non-blocking)          ← best-effort
             • Summarize the incident
             • Search past incidents for similar patterns
             • Correlate with recent deploys/changes
             • Suggest runbook / remediation
                │
                ▼
           Oncall (PagerDuty / Slack)
```

Key design choices:
- LLM is **async and non-blocking** — alert delivery doesn't wait for it
- LLM output is **advisory, not authoritative** — oncall still decides
- LLM uses **RAG over runbooks + postmortems** — grounded in actual docs to reduce hallucination

### Commercial Products

- **PagerDuty AIOps** — ML grouping + generative AI for incident summaries
- **Datadog Bits AI** — LLM that explains alerts using logs/traces/metrics
- **Grafana AI assistant** — suggests investigation paths from dashboard context

---

## Putting It All Together

The strategies are **layered**, not mutually exclusive:

```
            Raw Alerts (1000s)
                  │
                  ▼
         ┌────────────────┐
         │  Deduplication  │  ← collapse identical alerts
         └───────┬────────┘
                 ▼
         ┌────────────────┐
         │    Grouping     │  ← bundle by common labels
         └───────┬────────┘
                 ▼
         ┌────────────────┐
         │   Inhibition    │  ← suppress known symptoms
         └───────┬────────┘
                 ▼
         ┌────────────────┐
         │  Topology RCA   │  ← find root cause via dependency graph
         └───────┬────────┘
                 ▼
         ┌────────────────┐
         │ LLM Enrichment  │  ← summarize, add context, suggest fix
         └───────┬────────┘
                 ▼
          Oncall gets: 1 actionable alert
          with root cause + context + suggested runbook
```
