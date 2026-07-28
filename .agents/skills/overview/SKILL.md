---
name: overview
description: Generate a researched Hugo tech overview post for this repository, using Draw.io for architecture or flow diagrams and including demos only with user approval. Use when the user asks for an overview, introduction, deep dive, study guide, or explainer post about a technology topic such as a protocol, open source project, infrastructure domain, troubleshooting method, hardware component, or system component.
---

# Overview

Generate a concise, technically accurate overview post under `content/posts/` for a user-provided topic.

## Workflow

1. Identify the topic from the user prompt, for example `$overview websocket` or "generate an overview post about Kafka".
2. Classify the topic using the category templates below.
3. Inspect existing posts under `content/posts/` to avoid duplicates and match local style. Read one or two related posts when available.
4. Research the topic before writing when facts may be current, niche, version-specific, or externally sourced. Prefer official documentation, RFCs, standards, project docs, design docs, papers, and source repositories. If web access is unavailable, say so and continue only with local context.
5. Obtain an explicit decision about a hands-on quickstart or code/config demo before including one. If the user has not already requested or rejected one, ask whether the post should include a demo or stay conceptual, then wait for the answer.
6. Present an outline in chat and ask the user to approve it before creating or editing the post.
7. After approval, write the Markdown file and report the path plus a short coverage summary.

Do not write the post before the user approves the outline unless the user explicitly asks to skip outline approval. Do not treat outline approval alone as consent for a demo that was not explicitly offered and accepted.

## Category Templates

### Network Protocol

Use for TCP, WebSocket, HTTP/2, gRPC, QUIC, DNS, TLS, and similar protocols.

Sections:

- Background and Motivation: why it exists, prior limitations, design goals.
- What It Is and How It Works: definition, mental model, core mechanisms.
- Protocol Details: handshake, packet/frame format, state transitions, headers, key mechanisms. Use Draw.io diagrams when a visual materially improves the explanation.
- Usage and Trade-offs: when to use it, when not to use it, alternatives. Use comparison tables.
- Optional Hands-on Demo: include only after explicit user opt-in; prefer a minimal runnable example in Go or with shell tools such as `curl`, `tcpdump`, `nc`, or protocol-specific CLIs.
- References: RFCs, specs, official docs, authoritative posts.

### Open Source Project

Use for Kafka, Kubernetes, Prometheus, Nginx, Redis, PostgreSQL, VictoriaMetrics, and similar projects.

Sections:

- Background and Motivation: problem solved, what existed before, why it was insufficient.
- What It Is: high-level definition, positioning, value proposition.
- Architecture: Draw.io architecture diagram, components, data flow.
- Core Concepts: concepts users must understand.
- Key Features and Internals: mechanisms, design choices, trade-offs.
- Optional Getting Started or Demo: include only after explicit user opt-in; use a minimal setup or commands, preferably Docker Compose or shell.
- References: official docs, GitHub repo, design docs, papers.

### Tech Domain or Troubleshooting

Use for network troubleshooting, Linux performance, observability, storage debugging, JVM tuning, and similar domains.

Sections:

- Overview: scope and boundaries.
- Key Concepts: required foundations.
- Methodology or Framework: systematic approach, decision tree, or flowchart.
- Tools and Commands: practical commands and comparison table.
- Common Scenarios: two or three realistic diagnosis walkthroughs.
- Optional Lab or Demo: include runnable troubleshooting exercises only after explicit user opt-in.
- References: official docs, books, cheat sheets, high-quality technical references.

### Hardware or System Component

Use for CPU, GPU, SSD, memory, NIC, kernel scheduler, file system, and similar components.

Sections:

- Background and Motivation: why it matters and where it fits.
- What It Is: definition and system role.
- Architecture and Internals: internal structure, sub-components, Draw.io diagrams.
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
- Optional Hands-on Demo, only after explicit user opt-in
- References

## Diagram Workflow

- Verify that `drawio-skill` appears in the session's available skills before planning diagram work.
- If it is missing, tell the user: "This overview workflow uses Agents365 `drawio-skill`, but it is not installed in this session. Please install it before I generate the diagrams." Link to [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill), and offer to use `skill-installer` if available. Do not install it without the user's explicit request.
- Ask whether to wait for installation or continue with diagrams omitted. Do not substitute ASCII art while the skill is unavailable.
- Invoke `drawio-skill` from [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill) for every planned architecture, component, sequence, decision, or data-flow diagram. Do not use ASCII-art diagrams as a substitute.
- Follow the Draw.io skill's complete workflow, including preset and CLI detection, the relevant diagram-type guidance, structural validation, a PNG preview without embedded XML, visual self-check, and final editable export.
- Read the Draw.io skill's XML-authoring reference before hand-writing XML. Prefer its bundled generators or auto-layout tools when they fit the diagram.
- Save the editable source as `static/images/<post-slug>-<diagram>.drawio`.
- Export the final Hugo asset as an editable SVG with embedded diagram XML at `static/images/<post-slug>-<diagram>.drawio.svg`, then embed it with `![alt text](/images/<post-slug>-<diagram>.drawio.svg)`.
- Check the rendered preview for clipped labels, overlaps, edge crossings, stacked edges, and off-canvas elements. Fix issues before embedding the diagram.
- If Draw.io export is unavailable, follow the Draw.io skill's fallback chain and report the limitation. Do not silently fall back to ASCII art.

## Demo and Quickstart Gate

- Treat installation walkthroughs, quickstarts, Docker Compose files, runnable code, and runnable configuration examples as demos.
- Include a demo only when the user explicitly opts in. An explicit request in the original prompt counts as opt-in; otherwise ask before presenting the outline.
- If the user opts out, omit setup and runnable demo sections and keep the post focused on concepts, architecture, internals, trade-offs, and operations.
- Allow short non-runnable syntax or data-format fragments when essential to explain the topic, but identify them in the outline.
- When the user opts in, keep the demo minimal, complete, and runnable, and verify it when practical.

## Outline Approval

Before writing the file, send the user an outline containing:

- Detected category.
- Proposed file path under `content/posts/`.
- Proposed title, tags, and description.
- Section outline with one or two bullets per section.
- Planned Draw.io diagrams and output paths, tables, and commands.
- Demo decision: explicitly state whether a quickstart or code/config demo is included or omitted based on the user's choice.
- Key sources or source types to use.

Ask: "Does this outline look good? I can proceed or revise it." Wait for approval or requested changes.

## Writing Rules

- Use Hugo frontmatter with `title`, `date`, `tags`, `description`, and `draft: true`.
- Get the exact date with `date +%Y-%m-%dT%H:%M:%S%z` immediately before writing.
- Place the file under an existing relevant `content/posts/` subdirectory when possible; create a new subdirectory only when clearly warranted.
- Use `drawio-skill` and editable Draw.io SVG assets for architecture and flows.
- Use tables for comparisons, component lists, and trade-offs.
- Prefer concrete examples, numbers, commands, packet fields, or data flow over vague descriptions.
- Specify language identifiers on code blocks, such as `shell`, `go`, `yaml`, or `text`.
- Keep prose scannable: short paragraphs, bullets, code, tables, and diagrams.
- Add quickstart, demo code, and runnable configuration only after explicit user opt-in.
- Add comments in code only where non-obvious.
- Keep references at the end with direct links to the sources used.

## Final Response

After writing, tell the user:

- The created or updated file path.
- The detected category.
- A short summary of the main coverage.
- Whether the user-approved demo decision was followed.
- The `.drawio` source and editable SVG paths for each generated diagram.
- Any verification or source limitations, especially if web access was unavailable.
