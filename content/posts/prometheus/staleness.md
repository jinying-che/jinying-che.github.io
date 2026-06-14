---
title: "Prometheus Staleness"
date: "2026-06-12T00:02:29+0800"
tags: ["prometheus"]
description: "How Prometheus decides when a time series becomes stale, when stale markers are written, and how they interact with the 5-minute lookback window."
---

## Overview

Prometheus staleness is the mechanism that tells PromQL: **this time series used to exist, but it should no longer be returned as an active series**.

This matters because PromQL does not evaluate only at timestamps where samples exist. A graph query might evaluate every 30 seconds, while a target is scraped every 15 seconds, 30 seconds, or 1 minute. At each evaluation timestamp, Prometheus must decide which sample represents each series.

The basic rule is:

- For an instant vector selector, Prometheus returns the newest sample at or before the evaluation timestamp.
- That sample must be within the lookback period.
- The default lookback period is `5m`.
- If the series has a stale marker before the evaluation timestamp, Prometheus stops returning the old value.

Staleness is not the same as the `up` metric. `up = 0` means the target still exists but the scrape failed. On that failed scrape, Prometheus treats the target as returning no metrics, so previously scraped series from that target can receive stale markers.

## Why Staleness Exists

Without staleness, Prometheus could accidentally keep old values alive.

Imagine a Kubernetes pod exports this series:

```text
http_requests_total{pod="api-123"} 1000
```

Then the pod is deleted and replaced:

```text
http_requests_total{pod="api-456"} 10
```

If Prometheus kept returning the old `api-123` value forever, this query would overcount:

```promql
sum(http_requests_total)
```

The old pod is gone. It should not continue contributing to aggregations, dashboards, or alerts. Staleness lets Prometheus draw a boundary between "last known value" and "series no longer exists".

The same problem appears whenever labels churn: pods restart, containers exit, targets leave service discovery, or an exporter stops exposing a specific metric.

## Lookback Delta

PromQL instant vector selectors use lookback because query timestamps and scrape timestamps usually do not line up exactly.

Example with a 1-minute scrape interval:

```text
10:00:00  queue_depth = 7
10:01:00  queue_depth = 8
10:02:00  scrape delayed
10:03:00  queue_depth = 9
```

If a query evaluates at `10:02:30`, there is no exact sample at that timestamp. Prometheus looks backward and uses the newest sample within the lookback period:

```text
query: queue_depth @ 10:02:30
result: 8
```

The default maximum lookback is `5m`, controlled by:

```shell
prometheus --query.lookback-delta=5m
```

The value is a compromise:

- Too small: graphs get artificial gaps from normal scrape jitter.
- Too large: old values can remain visible for too long when stale markers are unavailable.

Lookback is a query-time tolerance window. It is not a guarantee that the value is fresh.

## Stale Markers

When a target scrape or rule evaluation no longer returns a series that was previously present, Prometheus marks that series as stale.

Conceptually:

```text
10:00  my_counter_total = 8
10:01  my_counter_total = 10
10:02  metric disappears from scrape response
10:02  Prometheus records a stale marker
```

After the stale marker, instant vector queries stop returning that series:

```text
query time          result
--------------------------
10:01:30            10
10:02:30            no series
10:07:00            no series
```

The important rule:

```text
lookback does not cross a stale marker
```

Even though `10` is still within 5 minutes at `10:02:30`, Prometheus knows the series ended.

## When Stale Markers Are Written

There is no separate "metric delay threshold" for stale markers. The threshold is the scrape result:

- If the scrape succeeds and the metric is present, no stale marker is written.
- If the scrape succeeds but a previously present metric is missing, that missing series is marked stale.
- If the scrape fails or times out, Prometheus treats it like an empty scrape and can mark previously scraped series stale.
- If the target is removed from service discovery, Prometheus waits a little over two scrape intervals before writing stale markers.

By default:

```yaml
global:
  scrape_interval: 1m
  scrape_timeout: 10s
```

So a target that responds after `3s` is just a delayed successful scrape:

```text
10:00:00  scrape starts
10:00:03  response arrives with my_counter_total
10:00:03  scrape succeeds
10:00:00  sample is appended at the scheduled scrape timestamp
```

No stale marker is written because the metric was present in the completed scrape.

But a target that responds after the timeout is different:

```text
10:00:00  scrape starts
10:00:10  scrape timeout
10:00:10  Prometheus treats this as an empty scrape
10:00:10  previous series can receive stale markers
```

Source-code flow:

```text
scrape with timeout
  -> parse response if successful
  -> track current series in scrape cache
  -> compare previous scrape vs current scrape
  -> append StaleNaN for series missing from current scrape
```

For a failed scrape, Prometheus intentionally takes the empty-scrape path:

```text
failed scrape -> empty scrape -> update stale markers
```

## Timeline Examples

### Case 1: Series Disappears and Prometheus Writes a Stale Marker

Assume the last real sample is at `10:01`, then the metric disappears at `10:02`.

```text
time      event
------------------------------------------------
10:00     my_counter_total = 8
10:01     my_counter_total = 10
10:02     stale marker
10:03     query my_counter_total -> no series
10:07     query my_counter_total -> no series
```

The stale marker ends the series immediately for future instant queries.

### Case 2: No Stale Marker, Only Lookback

Sometimes Prometheus cannot rely on a stale marker. Then the fallback behavior is the lookback period.

```text
time      event
------------------------------------------------
10:00     my_counter_total = 8
10:01     my_counter_total = 10
10:02     no new sample, no stale marker
10:05     query my_counter_total -> 10
10:06:01  query my_counter_total -> no series
10:07     query my_counter_total -> no series
```

With the default `5m` lookback, the sample at `10:01` can be selected until it is too old. At `10:07`, it is outside the 5-minute lookback window, so the series is not returned.

### Case 3: Counter Value `10` Disappears at `10:02`

This is the common mental model question:

```text
10:01  requests_total = 10
10:02  requests_total disappears
```

Can you still see `requests_total = 10` at `10:07`?

Usually no.

| Condition | `requests_total @ 10:07` |
|:----------|:--------------------------|
| Stale marker was written at `10:02` | No series |
| No stale marker, last sample at `10:01`, default lookback | No series |
| No stale marker, last sample at `10:02`, exactly at boundary | Depends on exact timestamp and query engine boundary |
| Lookback changed to `10m`, no stale marker | `10` may still be returned |

For normal Prometheus-scraped series, expect the stale marker to stop the old value before the 5-minute fallback matters.

## Explicit Timestamps

Some exporters attach their own timestamps to samples. Prometheus documents a different behavior for these: if the series stops being exported, the last value can remain visible for the lookback period before disappearing.

The `track_timestamps_staleness` setting changes this behavior.

For most application exporters, avoid setting explicit sample timestamps unless you have a strong reason. Let Prometheus timestamp the scrape.

## Summary

Rules of thumb:

- Staleness means a previously active series should no longer be returned.
- Default lookback is `5m`, but stale markers stop old values earlier.
- A delayed scrape does not create stale markers if it finishes before `scrape_timeout` and still includes the metric.
- A scrape timeout or failed scrape is treated like an empty scrape and can create stale markers.
- `up = 0` means scrape failure; other series from that failed scrape can become stale.
- Lookback handles scrape jitter; it is not a freshness guarantee.
- Stale markers keep aggregations and alerts from using dead series.
- If no stale marker exists, the last sample can remain visible until it falls outside the lookback window.

## References

- [Prometheus Querying Basics: Staleness](https://prometheus.io/docs/prometheus/latest/querying/basics/#staleness)
- [Prometheus Configuration: `scrape_interval`, `scrape_timeout`, `track_timestamps_staleness`](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Prometheus Command-Line Flags: `--query.lookback-delta`](https://prometheus.io/docs/prometheus/latest/command-line/prometheus/)
- [Prometheus scrape loop source code](https://github.com/prometheus/prometheus/blob/main/scrape/scrape.go)
