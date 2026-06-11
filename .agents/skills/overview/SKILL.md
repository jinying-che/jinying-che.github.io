---
name: overview
description: Generate a Hugo tech overview post for this repository. Use when the user asks for an overview, introduction, deep dive, study guide, or explainer post about a technology topic such as a protocol, open source project, infrastructure domain, troubleshooting method, hardware component, or system component.
---

# Overview

Generate a concise, technically accurate overview post under `content/posts/` for a user-provided topic.

## Workflow

1. Identify the topic from the user prompt, for example `$overview websocket` or "generate an overview post about Kafka".
2. Classify the topic using the category templates below.
3. Inspect existing posts under `content/posts/` to avoid duplicates and match local style. Read one or two related posts when available.
4. Research the topic before writing when facts may be current, niche, version-specific, or externally sourced. Prefer official documentation, RFCs, standards, project docs, design docs, papers, and source repositories. If web access is unavailable, say so and continue only with local context.
5. Present an outline in chat and ask the user to approve it before creating or editing the post.
6. After approval, write the Markdown file and report the path plus a short coverage summary.

Do not write the post before the user approves the outline unless the user explicitly asks to skip outline approval.

## Category Templates

### Network Protocol

Use for TCP, WebSocket, HTTP/2, gRPC, QUIC, DNS, TLS, and similar protocols.

Sections:

- Background and Motivation: why it exists, prior limitations, design goals.
- What It Is and How It Works: definition, mental model, core mechanisms.
- Protocol Details: handshake, packet/frame format, state transitions, headers, key mechanisms. Use ASCII diagrams.
- Usage and Trade-offs: when to use it, when not to use it, alternatives. Use comparison tables.
- Hands-on Demo: minimal runnable example, preferably Go or shell tools such as `curl`, `tcpdump`, `nc`, or protocol-specific CLIs.
- References: RFCs, specs, official docs, authoritative posts.

### Open Source Project

Use for Kafka, Kubernetes, Prometheus, Nginx, Redis, PostgreSQL, VictoriaMetrics, and similar projects.

Sections:

- Background and Motivation: problem solved, what existed before, why it was insufficient.
- What It Is: high-level definition, positioning, value proposition.
- Architecture: ASCII architecture diagram, components, data flow.
- Core Concepts: concepts users must understand.
- Key Features and Internals: mechanisms, design choices, trade-offs.
- Getting Started or Demo: minimal setup or commands, preferably `docker-compose` or shell.
- References: official docs, GitHub repo, design docs, papers.

### Tech Domain or Troubleshooting

Use for network troubleshooting, Linux performance, observability, storage debugging, JVM tuning, and similar domains.

Sections:

- Overview: scope and boundaries.
- Key Concepts: required foundations.
- Methodology or Framework: systematic approach, decision tree, or flowchart.
- Tools and Commands: practical commands and comparison table.
- Common Scenarios: two or three realistic diagnosis walkthroughs.
- References: official docs, books, cheat sheets, high-quality technical references.

### Hardware or System Component

Use for CPU, GPU, SSD, memory, NIC, kernel scheduler, file system, and similar components.

Sections:

- Background and Motivation: why it matters and where it fits.
- What It Is: definition and system role.
- Architecture and Internals: internal structure, sub-components, ASCII diagrams.
- How It Works: step-by-step operation with concrete examples and numbers.
- Key Metrics and Observability: what to monitor and which tools to use.
- References: datasheets, official docs, classic references.

### General

Use this fallback only when no specific template fits.

Sections:

- Background and Motivation
- What It Is
- Core Concepts
- How It Works
- Hands-on Demo
- References

## Outline Approval

Before writing the file, send the user an outline containing:

- Detected category.
- Proposed file path under `content/posts/`.
- Proposed title, tags, and description.
- Section outline with one or two bullets per section.
- Planned diagrams, tables, demos, or commands.
- Key sources or source types to use.

Ask: "Does this outline look good? I can proceed or revise it." Wait for approval or requested changes.

## Writing Rules

- Use Hugo frontmatter with `title`, `date`, `tags`, `description`, and `draft: true`.
- Get the exact date with `date +%Y-%m-%dT%H:%M:%S%z` immediately before writing.
- Place the file under an existing relevant `content/posts/` subdirectory when possible; create a new subdirectory only when clearly warranted.
- Use ASCII diagrams for architecture and flows.
- Use tables for comparisons, component lists, and trade-offs.
- Prefer concrete examples, numbers, commands, packet fields, or data flow over vague descriptions.
- Specify language identifiers on code blocks, such as `shell`, `go`, `yaml`, or `text`.
- Keep prose scannable: short paragraphs, bullets, code, tables, and diagrams.
- Demo code must be minimal, complete, and runnable when possible.
- Add comments in code only where non-obvious.
- Keep references at the end with direct links to the sources used.

## Final Response

After writing, tell the user:

- The created or updated file path.
- The detected category.
- A short summary of the main coverage.
- Any verification or source limitations, especially if web access was unavailable.
