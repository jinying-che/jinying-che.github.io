---
title: "How histogram is calculated in Prometheus"
date: "2025-01-16T23:07:11+08:00"
tags: ["Prometheus"]
description: "How p99 and p95 of the http request latency are calculated?"
draft: true
---

> source code in prometheus: [BucketQuantile](https://github.com/prometheus/prometheus/blob/a3c7f72ad09d1ee04ee8c6769e85d31f225f76fa/promql/quantile.go#L107)

Before we dive into the calculation of histogram, let's first understand the metric type in Prometheus. see details in [Metric Type](https://jinying-che.github.io/posts/prometheus/#metric-type)

## Basic Histogram


## Rate of Histogram


## why histogram output the largest histogram bucket (latency spike)?
