# Open-Source Website Statistics Solution Comparison

## Function coverage

| Function | Plausible CE | Umami | GoatCounter | Matomo Core | Custom Victoria stack |
|---|---|---|---|---|---|
| Pageviews | Native | Native | Native | Native | Custom |
| Unique visitors | Native | Native | Native | Native | Custom |
| Sessions | Native | Native | Basic | Native | Custom |
| Country/region | Native | Native | Native | Native | Custom GeoIP |
| Referrers/UTM | Native | Native | Native | Native | Custom |
| Device/browser/OS | Native | Native | Native | Native | Custom parsing |
| Per-post read time | **Native** | Custom event | No | Heartbeat | Custom |
| Scroll depth | **Native** | Custom event | No | Custom | Custom |
| Completion rate | Native goal | Custom event | No | Custom goal | Custom |
| Returning readers | Native | Native | Limited | Native | Custom |
| Custom interactions | Native events | Native events | Basic events | Native events | Custom |
| Public dashboard | Native | Native board | Limited | Custom/API | Grafana |
| Nginx log import | No | No | Native | Native | Native pipeline |
| VictoriaMetrics integration | Optional export | API export | Custom export | API export | Native |
| Privacy-friendly default | Strong | Strong | **Strongest** | Configurable | Entirely custom |

## Deployment and operational comparison

| Solution | Open-source license | Architecture | Database | Relative footprint | Custom development | Best suited for |
|---|---|---|---|---|---|---|
| **Plausible CE** | AGPL-3.0 | Hugo -> Nginx -> Plausible CE -> PostgreSQL + ClickHouse | PostgreSQL and ClickHouse | Medium | Low | Blog analytics with native read time and scroll depth |
| **Umami** | MIT | Hugo -> Nginx -> Umami -> PostgreSQL | PostgreSQL | Low | Medium: reading tracker | Simple self-hosting with custom engagement events |
| **GoatCounter** | EUPL-1.2 | Hugo or Nginx logs -> GoatCounter -> SQLite | SQLite or PostgreSQL | **Very low** | High for engagement | Privacy-first pageviews and basic traffic statistics |
| **Matomo Core** | GPL-3.0+ | Hugo -> Nginx -> PHP-FPM/Matomo -> MariaDB | MySQL or MariaDB | High | Low to medium | Comprehensive analytics and segmentation |
| **Custom Victoria stack** | Multiple OSS licenses | Hugo -> custom collector -> VictoriaLogs/VM -> Grafana | VictoriaLogs and VictoriaMetrics | Existing stack plus collector | **Very high** | Full control or an analytics engineering project |

## Recommendation by priority

| Priority | Recommended solution | Reason |
|---|---|---|
| Accurate post views, read time and completion | **Plausible CE** | Required engagement metrics are native and open source |
| Simplest capable self-hosted platform | **Umami** | Only PostgreSQL is required; reading events need a small Hugo script |
| Minimum resource usage | **GoatCounter** | Single binary with SQLite, but lacks reading analytics |
| Maximum analytical depth | **Matomo Core** | Comprehensive, but heavier than a personal blog needs |
| Maximum reuse of the existing VM stack | **Custom Victoria stack** | Reuses existing services but requires building an analytics product |

## Final recommendation

Use **Plausible Community Edition** for visitor and content analytics, while retaining VictoriaMetrics, VictoriaLogs, and Grafana for Nginx and infrastructure monitoring.

```text
Behavior analytics:
Hugo -> Plausible CE -> PostgreSQL + ClickHouse

Operational analytics:
Nginx -> VictoriaLogs/VictoriaMetrics -> Grafana

Public presentation:
Hugo /statistics/ -> restricted Plausible public dashboard
```
