---
title: "relabel_config vs metric_relabel_config"
date: "2025-09-17T16:13:56+08:00"
tags: ["monitor", "prometheus"]
description: "Comprehensive guide to understanding and using Prometheus relabel_config and metric_relabel_config"
draft: true
---

# Prometheus Relabeling: Complete Guide

Relabeling in Prometheus is a powerful feature that allows you to transform labels and metrics during the scraping process. This guide covers both `relabel_config` and `metric_relabel_config` with practical examples and best practices.

## Table of Contents
- [Overview](#overview)
- [Key Differences](#key-differences)
- [relabel_config - Target Relabeling](#relabel_config---target-relabeling)
- [metric_relabel_config - Metric Relabeling](#metric_relabel_config---metric-relabeling)
- [Advanced Examples](#advanced-examples)
- [Best Practices](#best-practices)
- [Common Use Cases](#common-use-cases)
- [Debugging Tips](#debugging-tips)

## Overview

Prometheus supports two main types of relabeling:

1. **`relabel_config`** - Applied to target labels before scraping
2. **`metric_relabel_config`** - Applied to metric labels after scraping

Both use the same configuration format but operate at different stages of the scraping pipeline.

## Key Differences

| Aspect | `relabel_config` | `metric_relabel_config` |
|--------|------------------|-------------------------|
| **When Applied** | Before scraping the target | After scraping, before storage |
| **What It Affects** | Target labels (service discovery) | Metric labels and metric names |
| **Purpose** | Modify how targets are discovered and scraped | Filter/modify metrics and their labels |
| **Can Drop Targets** | Yes (by setting `action: drop`) | No (targets already scraped) |
| **Can Drop Metrics** | No | Yes (by setting `action: drop`) |
| **Performance Impact** | Affects scraping efficiency | Affects storage and query performance |

## relabel_config - Target Relabeling

Applied during service discovery and before scraping. Used to:

- Modify target labels
- Drop unwanted targets
- Add/modify labels from service discovery
- Change scrape parameters

### Available Actions

1. **`replace`** (default) - Replace label values
2. **`keep`** - Keep targets matching regex
3. **`drop`** - Drop targets matching regex
4. **`hashmod`** - Distribute targets across multiple Prometheus instances
5. **`labelmap`** - Rename labels using regex
6. **`labeldrop`** - Remove labels matching regex
7. **`labelkeep`** - Keep only labels matching regex

### Configuration Parameters

- `source_labels`: List of source labels to use
- `separator`: Separator for concatenating source labels (default: `;`)
- `target_label`: Target label to write to
- `regex`: Regular expression to match against
- `replacement`: Replacement string (supports regex groups)
- `action`: Action to perform
- `modulus`: Modulus for hashmod action

### Example Configuration

```yaml
scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      # Keep only pods with specific annotation
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      
      # Replace the job name
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_job]
        action: replace
        target_label: job
        regex: (.+)
      
      # Add environment label
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: environment
        regex: (.+)
      
      # Drop targets in test namespace
      - source_labels: [__meta_kubernetes_namespace]
        action: drop
        regex: test
      
      # Modify scrape path
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      
      # Modify scrape interval
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape_interval]
        action: replace
        target_label: __scrape_interval__
        regex: (.+)
```

## metric_relabel_config - Metric Relabeling

Applied after scraping but before storing metrics. Used to:

- Filter out unwanted metrics
- Modify metric names
- Add/remove/modify metric labels
- Drop high-cardinality metrics

### Example Configuration

```yaml
scrape_configs:
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
    metric_relabel_configs:
      # Drop metrics with high cardinality
      - source_labels: [__name__]
        action: drop
        regex: 'go_gc_duration_seconds.*'
      
      # Rename metric
      - source_labels: [__name__]
        action: replace
        target_label: __name__
        regex: 'node_memory_MemTotal_bytes'
        replacement: 'node_memory_total_bytes'
      
      # Add custom label
      - source_labels: [instance]
        action: replace
        target_label: datacenter
        replacement: 'us-east-1'
      
      # Drop metrics without specific label
      - source_labels: [job]
        action: drop
        regex: ''
      
      # Keep only specific metrics
      - source_labels: [__name__]
        action: keep
        regex: 'node_cpu_seconds_total|node_memory_.*|node_filesystem_.*'
      
      # Extract version from label
      - source_labels: [version]
        action: replace
        target_label: major_version
        regex: 'v(\d+)\..*'
        replacement: '${1}'
```

## Advanced Examples

### 1. Hashmod for High Availability Setup

Distribute targets across multiple Prometheus instances:

```yaml
relabel_configs:
  - source_labels: [__address__]
    action: hashmod
    target_label: __tmp_hash
    modulus: 2
  - source_labels: [__tmp_hash]
    action: keep
    regex: 0  # This Prometheus instance scrapes targets with hash 0
```

### 2. Dynamic Scrape Configuration

```yaml
relabel_configs:
  # Dynamic scrape interval
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape_interval]
    action: replace
    target_label: __scrape_interval__
    regex: (.+)
  
  # Dynamic scrape timeout
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape_timeout]
    action: replace
    target_label: __scrape_timeout__
    regex: (.+)
  
  # Dynamic metrics path
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
    action: replace
    target_label: __metrics_path__
    regex: (.+)
```

### 3. Metric Name Transformation

```yaml
metric_relabel_configs:
  # Convert histogram to summary-like naming
  - source_labels: [__name__]
    action: replace
    target_label: __name__
    regex: 'http_request_duration_seconds_bucket'
    replacement: 'http_request_duration_seconds'
  
  # Standardize metric names
  - source_labels: [__name__]
    action: replace
    target_label: __name__
    regex: 'http_requests_total'
    replacement: 'http_requests'
```

### 4. Label Value Extraction and Transformation

```yaml
metric_relabel_configs:
  # Extract major version from version label
  - source_labels: [version]
    action: replace
    target_label: major_version
    regex: 'v(\d+)\..*'
    replacement: '${1}'
  
  # Extract environment from instance
  - source_labels: [instance]
    action: replace
    target_label: environment
    regex: '([^.]+)\..*'
    replacement: '${1}'
  
  # Normalize label values
  - source_labels: [status]
    action: replace
    target_label: status
    regex: '2\d\d'
    replacement: 'success'
```

### 5. Cardinality Control

```yaml
metric_relabel_configs:
  # Drop high-cardinality metrics
  - source_labels: [__name__]
    action: drop
    regex: '.*_bucket$'
  
  # Keep only essential metrics
  - source_labels: [__name__]
    action: keep
    regex: 'http_requests_total|http_request_duration_seconds|cpu_usage_percent'
  
  # Drop metrics with too many unique label combinations
  - source_labels: [__name__, instance, job]
    action: drop
    regex: 'go_gc_duration_seconds.*'
```

## Best Practices

### 1. Use relabel_config for:
- Service discovery filtering
- Target selection and routing
- Adding metadata labels
- Modifying scrape parameters
- Implementing HA strategies

### 2. Use metric_relabel_config for:
- Metric filtering and selection
- Label standardization
- High-cardinality prevention
- Metric name normalization
- Data quality control

### 3. Performance Considerations:
- Apply filters early to reduce processing overhead
- Use specific regex patterns instead of broad ones
- Avoid complex regex in high-volume scenarios
- Test configurations with `promtool`

### 4. Order Matters:
- Relabeling rules are applied in order
- Place most restrictive rules first
- Use `keep` before `drop` when possible

### 5. Testing and Validation:
```bash
# Test configuration
promtool check config prometheus.yml

# Validate relabeling rules
promtool test rules test.yml
```

## Common Use Cases

### 1. Kubernetes Integration

```yaml
relabel_configs:
  # Only scrape annotated pods
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
    action: keep
    regex: true
  
  # Use custom job name
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_job]
    action: replace
    target_label: job
    regex: (.+)
  
  # Add namespace as environment
  - source_labels: [__meta_kubernetes_namespace]
    action: replace
    target_label: environment
    regex: (.+)
```

### 2. Multi-tenant Setup

```yaml
metric_relabel_configs:
  # Filter by tenant
  - source_labels: [tenant]
    action: keep
    regex: 'production|staging'
  
  # Add tenant-specific labels
  - source_labels: [__meta_kubernetes_namespace]
    action: replace
    target_label: tenant
    regex: '([^-]+)-.*'
    replacement: '${1}'
```

### 3. Cardinality Control

```yaml
metric_relabel_configs:
  # Drop histogram buckets to reduce cardinality
  - source_labels: [__name__]
    action: drop
    regex: '.*_bucket$'
  
  # Keep only essential metrics
  - source_labels: [__name__]
    action: keep
    regex: 'http_requests_total|http_request_duration_seconds_sum|http_request_duration_seconds_count'
```

### 4. Environment Standardization

```yaml
metric_relabel_configs:
  # Standardize environment labels
  - source_labels: [environment]
    action: replace
    target_label: env
    regex: 'prod|production'
    replacement: 'production'
  
  - source_labels: [environment]
    action: replace
    target_label: env
    regex: 'dev|development'
    replacement: 'development'
```

## Debugging Tips

### 1. Check Target Labels
Visit `/targets` endpoint to see the result of `relabel_config`:
```
http://prometheus:9090/targets
```

### 2. Verify Metric Labels
Check `/metrics` endpoint to see the result of `metric_relabel_config`:
```
http://prometheus:9090/metrics
```

### 3. Use Promtool
```bash
# Check configuration syntax
promtool check config prometheus.yml

# Test rules
promtool test rules rules.yml
```

### 4. Common Debugging Queries
```promql
# Check if targets are being discovered
up{job="your-job-name"}

# Verify label values
group by (instance, job) (up)

# Check metric cardinality
count by (__name__) ({__name__=~".+"})
```

### 5. Temporary Debugging
Add temporary labels to track relabeling:
```yaml
metric_relabel_configs:
  - source_labels: [__name__]
    action: replace
    target_label: debug_original_name
    regex: (.+)
    replacement: '${1}'
```

## Special Labels

Prometheus provides several special labels that can be used in relabeling:

- `__name__`: The metric name
- `__address__`: The target address
- `__metrics_path__`: The metrics path
- `__scheme__`: The scheme (http/https)
- `__scrape_interval__`: The scrape interval
- `__scrape_timeout__`: The scrape timeout
- `__param_<name>`: URL parameters

## Conclusion

Relabeling is a powerful feature that makes Prometheus flexible and adaptable to various monitoring scenarios. Understanding when and how to use `relabel_config` vs `metric_relabel_config` is crucial for building effective monitoring setups.

Key takeaways:
- Use `relabel_config` for target-level transformations
- Use `metric_relabel_config` for metric-level transformations
- Always test configurations before deploying
- Monitor cardinality and performance impact
- Follow best practices for maintainable configurations

## References

- [Prometheus Relabeling Documentation](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#relabel_config)
- [Prometheus Service Discovery](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#kubernetes_sd_config)
- [Promtool Documentation](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#promtool)
