---
description: Generate a tech overview post for a given topic (protocol, project, domain, hardware, etc.)
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebSearch, WebFetch, Agent
user-invocable: true
argument-hint: <topic> e.g. "websocket", "kafka", "cpu", "k8s", "network troubleshooting"
---

# Overview Skill

Generate a comprehensive overview post for the Hugo blog about: **$ARGUMENTS**

## Instructions

1. **Determine the category** of the topic. Common categories and their section templates:

### Category: Network Protocol (e.g. TCP, WebSocket, HTTP/2, gRPC, QUIC)
Sections:
- **Background & Motivation**: Why was this protocol introduced? What problem existed before? What were the limitations of prior solutions?
- **What Is It & How It Works**: Define the protocol. How does it solve the problem? Key concepts and mental model.
- **Protocol Details**: Architecture, packet/frame format and handshake flow (as diagrams, see **Diagrams** below), state machine, header fields, key mechanisms.
- **Usage & Use Cases**: When to use it, when NOT to use it, comparison with alternatives (use tables).
- **Hands-On Demo**: A minimal runnable example (prefer Go, or shell tools like `curl`, `wscat`, `tcpdump`, `nc`) that the reader can copy-paste and run. Include both server and client if applicable.
- **References**: Official RFCs, specs, authoritative docs, good blog posts.

### Category: Open Source Project (e.g. Kafka, K8s, Prometheus, Nginx)
Sections:
- **Background & Motivation**: What problem does this project solve? What existed before and why was it insufficient?
- **What Is It**: High-level definition, positioning, core value proposition.
- **Architecture**: System architecture diagram (see **Diagrams** below). Key components and their roles (use table). Data flow.
- **Core Concepts**: The essential concepts/abstractions a user must understand.
- **Key Features & Internals**: Important internal mechanisms, design decisions, trade-offs.
- **Getting Started / Demo**: Minimal setup or usage example. Prefer docker-compose or shell commands.
- **References**: Official docs, GitHub repo, key design docs/papers.

### Category: Tech Domain / Troubleshooting (e.g. network troubleshooting, Linux performance)
Sections:
- **Overview**: What is this domain about? Scope and boundaries.
- **Key Concepts**: Foundational knowledge needed.
- **Methodology / Framework**: Systematic approach (e.g. USE method, RED method). Decision trees or flowcharts (see **Diagrams** below).
- **Tools & Commands**: Practical tools with examples (use table for comparison, shell examples for usage).
- **Common Scenarios**: Walk through 2-3 real-world scenarios with step-by-step diagnosis.
- **References**: Books, official docs, cheat sheets.

### Category: Hardware / System Component (e.g. CPU, GPU, SSD, Memory)
Sections:
- **Background & Motivation**: Why understand this component? What role does it play?
- **What Is It**: Definition, high-level function, where it sits in the system.
- **Architecture & Internals**: Internal structure diagrams (see **Diagrams** below). Key sub-components (use table).
- **How It Works**: Step-by-step walkthrough of a typical operation. Use concrete examples and numbers.
- **Key Metrics & Observability**: How to monitor, what metrics matter, tools to inspect.
- **References**: Datasheets, official docs, classic references.

### Category: General (fallback for anything else)
Sections:
- **Background & Motivation**
- **What Is It**
- **Core Concepts**
- **How It Works**
- **Hands-On / Demo**
- **References**

2. **Research the topic** thoroughly using WebSearch and WebFetch. Gather accurate, up-to-date technical details. Cross-reference multiple sources.

3. **Check existing posts** in `content/posts/` to avoid duplicating content and to match the blog's style. Read 1-2 existing posts in the same domain for tone/format reference.

4. **Draft outline first** — before writing the full post, present a draft outline to the user in the CLI. The draft should include:
   - Detected category
   - Proposed file path (under `content/posts/`)
   - Proposed title, tags, and description
   - Section outline with 1-2 bullet points per section summarizing what will be covered
   - Any key diagrams or tables planned

   Then use AskUserQuestion to ask the user to review:
   - "Does this outline look good?" with options: "Looks good, proceed", "Needs changes" (user can specify what to adjust)
   - Do NOT write the file until the user approves the outline. If the user requests changes, revise and present the updated outline again.

5. **Write the post** (after outline is approved) following these style rules:
   - Hugo frontmatter: `title`, `date` (RFC3339, use current datetime — run `date +%Y-%m-%dT%H:%M:%S%z` to get the exact time), `tags` (array), `description`, `draft: true`
   - Draw architecture/flow diagrams as images with the `lark-whiteboard` skill (see **Diagrams** below), not ASCII art
   - Use tables for comparisons and component listings
   - Use concrete examples with real numbers/values, not hand-wavy descriptions
   - Code blocks: specify language (`go`, `shell`, `python`, etc.)
   - Keep it concise and scannable — headers, bullets, code, diagrams over walls of text
   - Dry run examples with concrete data when explaining algorithms/protocols
   - Demo code should be minimal but complete and runnable
   - Add comments in code only where non-obvious
   - References: a bulleted list of markdown links (`- [Title](url) — note`), not a table

6. **Diagrams**: generate every diagram with the `lark-whiteboard` skill. Load it first and follow its workflow (as Claude, its routing table sends these diagram types to `routes/svg.md`).
   - **What becomes an image**: architecture, flows, hierarchies, state machines, mappings and timelines. Code, shell commands, YAML, config and pseudo-code stay as fenced code blocks.
   - **Style** (flat Lark style):
     - centred title (22px bold) with a grey subtitle
     - pastel bands with a 1px border and a bold label above-left
     - white cards with a bold title and a grey subtitle
     - key nodes marked by a 1.5px blue border, not a fill
     - thin grey right-angled `<polyline>` connectors with small arrowheads
     - no gradients, heavy shadows or decorations outside the canvas
   - **Text fit**: size boxes for Latin text ≈ 0.6em per character plus padding. The skill's whiteboard renders text in Noto Sans SC, and it may not have some symbols (e.g. ✗); write those as words instead.
   - **Alignment**: when two connected boxes should line up, their centres must be exactly equal on that axis, so the connector is one straight line. Any connector whose ends are 1–20px out of line is a bug; fix the coordinates. Larger offsets are only for intentional fan-in/fan-out buses.
   - **Render & check** for each diagram, using the skill's commands:
     ```shell
     npx -y @larksuite/whiteboard-cli@^0.2.13 -i <dir>/diagram.svg -o <dir>/diagram.png -f svg
     npx -y @larksuite/whiteboard-cli@^0.2.13 -i <dir>/diagram.svg -f svg --check
     ```
     `textOverflow` must be 0. Then open every PNG and fix anything that is overlapping, cut off, off-centre or has a jog in a connector, and re-render.
   - **Facts**: draw what the system really does (e.g. components talk to kube-apiserver, not to etcd). Don't copy a simplification that is wrong.
   - **Output**: keep sources in `./diagrams/<topic>/<name>/diagram.svg`, copy the PNG to `static/images/<topic>_<name>.png`, and embed it with `![alt](/images/<topic>_<name>.png)`.
   - Only write diagrams into a Lark whiteboard (`+update`) if the user asks for it.

7. **File placement**: Determine the appropriate path under `content/posts/`. Use existing directory structure (e.g. `network/`, `db/`, `k8s/`, `java/`) or create a new subdirectory if the topic clearly warrants one.

8. **Output**: Write the markdown file and tell the user the file path and a brief summary of what was covered.
