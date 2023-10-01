---
title: "SLA vs SLO vs SLI"
date: "2023-09-09T16:58:58+08:00"
tags: ["sre"]
description: "What's the difference?"
---

To dive into the terms throughly, it's better to read [Google SRE Book](https://sre.google/sre-book/service-level-objectives/). This post is just a glance.

## TL;DR
SLIs drive SLOs which inform SLAs. (From Google SRE Team)

## SLA: Service Level Agreements
An SLA is an agreement between provider and client about measurable metrics like uptime, responsiveness, and responsibilities. 
> SRE doesn’t typically get involved in constructing SLAs, because SLAs are closely tied to business and product decisions.

e.g. *Service credit if 95th percentile homepage SLI succeeds less than 99.5% over tailing year*


## SLO: Service Level Objectives
An SLO is an agreement within an SLA about a specific metric like uptime or response time.

Choosing an appropriate SLO is complex.

e.g. *95th percentile homepage SLI will succeed 99.9% over trailing year*

## SLI: Service Level Indicator
An SLI measures compliance with an SLO (service level objective).

Most services consider request latency—how long it takes to return a response to a request—as a key SLI. Other common SLIs include the error rate, often expressed as a fraction of all requests received, and system throughput, typically measured in requests per second.

e.g. *95th percentile latency of homepage requests over past 5 minutes < 300ms* 

## Teams Cooperation
![sla_vs_slo_sli](/images/sla_vs_slo_vs_sli.png)

## Reference
- https://www.atlassian.com/incident-management/kpis/sla-vs-slo-vs-sli
- https://www.youtube.com/watch?v=tEylFyxbDLE
- https://cloud.google.com/blog/products/devops-sre/sre-fundamentals-slis-slas-and-slos
