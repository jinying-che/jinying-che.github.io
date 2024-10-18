---
title: "rate vs irate"
date: "2024-10-02T09:52:53+08:00"
tags: ["monitor", "prometheus"]
description: "two similar rate functions"
---

![rate_vs_irate](/images/rate_vs_irate.png)

`rate` and `irate` are based on the **counter** type metrics.

`rate(v range-vector)` calculates the per-second average rate of increase of the time series in the **range vector**, for example, `rate(http_request_total{method="post"}[1m])`
1. It's a rate: `total(now) - total(now - 1m) / 60s`
2. It's an average rate: over 1m 
3. Average is calculated over the time range, that's why range vector is required.
4. It provides a **smoother** trend.

`irate(v range-vector)` calculates the per-second instant rate of increase of the time series in the range vector. 

1. similar to `rate`, but it's an **sensitive** rate as it's based on **the last two data points**.
2. why calculate last two points still needs [1m] range? it's for looking back when the data point is missed


## Reference:
- https://www.robustperception.io/how-does-a-prometheus-counter-work/
- https://prometheus.io/docs/prometheus/latest/querying/functions/
