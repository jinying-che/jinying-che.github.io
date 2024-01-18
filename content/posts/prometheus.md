---
title: "Prometheus"
date: "2023-12-31T09:41:04+08:00"
tags: ["monitor", "prometheus"]
description: "Prometheus Overview"
draft: true
---

## Architecture

![Architecture](/images/prometheus.png)

## Data Model

Every time series is uniquely identified by its **metric name** and optional key-value pairs called **labels**.
- Metric Name
- Metric Label
  - The change of any labels value, including adding or removing labels, will create a new time series.

#### Metric Type
Prometheus supports four types of metrics, which are - Counter - Gauge - Histogram - Summary
- Counter: a metric value that can only increase or reset
  ```shell
  # use a counter to represent the number of requests served, tasks completed, or errors
  - http_requests_total{handler='/get_user_id', method='GET', status='200'}
  - errors_total{type='runtime', severity='critical'}
  ```
- Gauge: a number which can either go up or down
  ```shell
  # used for measured values like temperatures or current memory usage
  - memory_usage_bytes{process_name='web_server', instance='10.0.0.1:8080'}
  - queue_size{queue_name='low_priority', worker_type='background'}
  ```
- Histogram: used for any calculated value which is counted based on bucket values, 
  - **bucket** value determines the ordinate value (y coordinate of a standard two-dimensional graph)
  - **cumulative** counters for the observation buckets, exposed as <basename>_bucket{le="<**upper** inclusive bound>"}
  ```shell
  # usually things like request durations or response sizes
  # le="0.3" means less or equal to 0.3
  http_latency_sum 134420.14452212452
  http_latency_second_bucket{le="0.05"} 11326.0
  http_latency_second_bucket{le="0.1"} 2.284831e+06
  http_latency_second_bucket{le="0.15"} 2.285367e+06
  http_latency_second_bucket{le="0.25"} 2.285592e+06
  http_latency_second_bucket{le="1.0"} 2.285613e+06
  http_latency_second_bucket{le="+Inf"} 2.285619e+06
  http_latency_count 2.285619e+06

  # cumulative means that the count for le=”0.5” bucket also includes the count for le=”0.25” bucket.
  # Consider the following hypothetical distribution of observations for 200 observations.
  ┌─────────────┬──────────────────────┬──────────────────┐
  │ Bucket Size │ Cumulative Frequency │ Upper Bound      │
  │             │ Count                │ Percentile       │
  ├─────────────┼──────────────────────┼──────────────────┤
  │ 50ms        │                   20 │ p10              │
  │ 100ms       │                   70 │ p35              │
  │ 250ms       │                  120 │ p60              │
  │ 500ms       │                  150 │ p75              │
  │ 1000ms      │                  200 │ p100             │
  │ INF         │                  200 │ p100             │
  └─────────────┴──────────────────────┴──────────────────┘
  ```
- Summary: measure events and are an alternative to histograms. They are cheaper but lose more data (it is highly recommended to use histograms over summaries whenever possible.)

## Quick Start

## Reference
- https://prometheus.io/docs/introduction/overview/
