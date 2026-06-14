---
title: "OpenClaw Overview"
date: "2026-06-14T18:43:25+0800"
tags: ["llm", "ai-agent", "openclaw"]
description: "OpenClaw architecture, agent loop, skills, security model, and local setup"
draft: true
---

OpenClaw is an open-source personal AI assistant that runs on user-controlled infrastructure. It connects messaging channels, local apps, model providers, tools, memory, and automation into one long-lived assistant process.

The important distinction is that OpenClaw is not only a chat UI. It is closer to a local agent platform:

- A **Gateway** owns channels, sessions, WebSocket clients, tools, events, and control APIs.
- An **agent runtime** assembles context, calls a model, executes tools, streams replies, and persists session state.
- **Skills** and plugins extend what the assistant knows how to do.
- **Nodes** and companion apps expose device capabilities such as voice, canvas, camera, screen, or mobile surfaces.

## Background and Motivation

Most AI assistants fall into one of three shapes:

| Shape | Strength | Weakness |
|---|---|---|
| Hosted chatbot | Easy to start | Limited local access, limited workflow ownership |
| Coding agent | Strong at repository work | Usually scoped to code and terminal tasks |
| Workflow automation | Predictable integrations | Rigid flows, weak natural-language planning |
| Local personal agent | Can combine chat, tools, files, devices, and automation | Requires careful security and operations |

OpenClaw targets the last shape. The goal is a personal assistant that can answer through the communication channels users already use, while also taking real actions through local tools and configured services.

This creates a different design problem from a normal web app. The system must coordinate:

- inbound messages from multiple channels
- long-running agent turns
- model provider credentials
- local filesystem and process tools
- device pairing and remote access
- per-session history and memory
- third-party extensions

OpenClaw's answer is a single Gateway process that acts as the control plane for the assistant.

## What It Is

OpenClaw is a self-hosted personal AI assistant. It can be installed from npm or official install scripts, run as a local daemon, and controlled through CLI, dashboard, messaging channels, or companion apps.

Supported channels listed by the project include WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, IRC, Microsoft Teams, Matrix, Feishu, LINE, Mattermost, Nextcloud Talk, Nostr, Synology Chat, Twitch, Zalo, WeChat, QQ, and WebChat.

At runtime, a user message becomes an agent run. The run can read context, call an LLM, invoke tools, update session state, and stream the reply back to the originating channel.

## Architecture

High-level architecture:

```text
                         model providers
                   +------------------------+
                   | OpenAI / Anthropic /   |
                   | Google / local models  |
                   +-----------^------------+
                               |
                               | model calls
                               |
+--------------+   WS/RPC   +--+----------------+   reads   +----------------+
| CLI / Web UI |----------->| OpenClaw Gateway  |<--------->| agent workspace|
| macOS app    |<-----------|                   |           | AGENTS.md      |
| automations  |            | - channel adapters|           | SOUL.md        |
+--------------+            | - WS API          |           | TOOLS.md       |
                            | - sessions/events |           | skills/        |
+--------------+            | - auth/pairing    |           +----------------+
| messaging    |----------->| - agent runtime   |
| channels     |<-----------| - tool policy     |
| Telegram ... |            +---------+---------+
+--------------+                      |
                                      | node protocol
+--------------+                      |
| nodes        |<---------------------+
| mobile/head- |
| less devices |
+--------------+                      |
                                      | tool calls
                                      v
                            +--------------------+
                            | local tools         |
                            | read/write/edit     |
                            | exec/browser/canvas |
                            | sessions/cron/etc.  |
                            +--------------------+
```

Core components:

| Component | Role |
|---|---|
| Gateway | Long-lived daemon that owns channels, WebSocket API, events, pairing, health, and agent dispatch |
| Agent runtime | Runs the actual agent loop: context, model, tools, streaming, persistence |
| Workspace | Files and directories that define the assistant's working context |
| Sessions | JSONL transcripts and state for conversations |
| Skills | `SKILL.md`-based capability packages loaded into the agent context |
| Nodes | Paired devices or headless clients that expose capabilities to the Gateway |
| Tools | Runtime capabilities such as file operations, shell execution, browser, canvas, cron, and messaging actions |
| Model providers | External or local LLM backends selected by configuration |

The Gateway exposes a WebSocket API. Clients connect, authenticate or pair, send requests, and receive events. A typical local Gateway listens on loopback port `18789`.

## Core Concepts

### Gateway

The Gateway is the control plane. It maintains provider connections, validates WebSocket frames, emits server-push events, and accepts requests such as `health`, `status`, `send`, and `agent`.

The Gateway also serves web surfaces such as the canvas host and control UI. In local-first deployments, it is commonly bound to loopback and accessed directly or through a controlled tunnel.

### Agent Runtime

OpenClaw uses an embedded agent runtime owned by the Gateway. The runtime is responsible for:

- resolving model and auth profile
- loading workspace context and skills
- preparing session state
- calling the model
- executing tools
- streaming assistant and tool events
- writing transcripts

The runtime has a clear operational boundary: OpenClaw owns model discovery, tool wiring, prompt assembly, session management, and channel delivery as one integrated surface.

### Workspace

The workspace is the agent's working directory and the source of persistent user context. Important files include:

| File | Purpose |
|---|---|
| `AGENTS.md` | Operating instructions and memory |
| `SOUL.md` | Persona, boundaries, and tone |
| `TOOLS.md` | User-maintained tool notes and conventions |
| `BOOTSTRAP.md` | First-run setup ritual |
| `IDENTITY.md` | Agent identity |
| `USER.md` | User profile and preferences |
| `skills/` | Workspace-local skill packages |

On a new session, OpenClaw injects relevant workspace files into the system prompt's project context. Large files are trimmed or truncated to keep prompts under model limits.

### Sessions

Sessions keep conversation state stable across messages. OpenClaw serializes runs per session key so two overlapping prompts do not corrupt the same transcript or race over the same tool state.

Conceptually:

```text
channel message
    |
    v
resolve session key
    |
    v
enter session queue
    |
    v
prepare transcript + context
    |
    v
run model/tool loop
    |
    v
persist final state
```

### Skills

Skills are capability packages based on a `SKILL.md` file plus optional scripts, references, and assets. OpenClaw discovers skills from several locations, with workspace skills taking precedence over personal, managed, bundled, and extra skill folders.

Typical install paths:

```shell
# Install a public skill from ClawHub
openclaw skills install <slug>

# Install from a Git repository
openclaw skills install git:owner/repo@ref

# Install a local skill directory
openclaw skills install ./path/to/skill --as my-tool

# Verify a skill trust envelope
openclaw skills verify <slug>
```

Treat third-party skills as code, not as passive documentation. A skill can shape model behavior and may include scripts the agent can run.

## Agent Loop

The agent loop is the path from user message to final reply:

```text
User / channel / CLI
        |
        v
Gateway RPC: agent or agent.wait
        |
        v
validate params and resolve session
        |
        v
queue run per session
        |
        v
load workspace, skills, model config
        |
        v
build prompt and context
        |
        v
LLM inference
        |
        +-- assistant text stream ---------------+
        |                                        |
        +-- tool calls                           |
                |                                |
                v                                |
          tool execution                         |
                |                                |
                v                                |
          tool result into context               |
                |                                |
                +------ repeat until done -------+
        |
        v
persist transcript and emit final reply
```

Key properties:

- Runs are serialized per session to avoid races.
- Transcript writes use locking so session files remain consistent.
- Tool and assistant streams are emitted as Gateway events.
- Auto-compaction can summarize long context and retry a run.
- Timeouts and aborts protect the Gateway from permanently stuck runs.

## Key Features and Internals

### Multi-Channel Inbox

OpenClaw's channel adapters let the assistant answer from messaging systems instead of only from a web chat. This makes it useful for personal operations, reminders, remote control, and lightweight automation.

The trade-off is that inbound messages are untrusted input. A forwarded message, quoted reply, group mention, or unknown DM can influence model context unless policy is configured carefully.

### Tools and Automation

OpenClaw can expose high-authority tools such as shell execution, filesystem editing, browser control, cron jobs, sessions, and messaging sends.

Useful capability comes from combining these:

```text
"Check the build failure and tell the team"
        |
        +-- read repo files
        +-- run test command
        +-- inspect logs
        +-- summarize failure
        +-- send message to channel
```

The same composition also increases blast radius. Tool policy should match the trust level of the channel, sender, and deployment.

### Nodes and Companion Apps

Nodes are paired clients that connect to the Gateway and declare device capabilities. Examples include macOS, iOS, Android, and headless nodes.

Node capabilities can include canvas commands, camera capture, screen recording, location lookup, voice wake, or mobile chat surfaces. Pairing is device-based, and non-local connects require explicit approval.

### Hooks and Plugins

OpenClaw has hook points around the agent and Gateway lifecycle. Examples include:

- before model resolution
- before prompt build
- before or after tool calls
- after agent end
- before installation of staged extension material
- inbound and outbound message hooks

Hooks are useful for policy, routing, observability, context injection, and integration-specific behavior.

## Security Model

OpenClaw's official security guidance assumes a personal assistant deployment: one trusted operator boundary per Gateway. It is not meant to be a hostile multi-tenant security boundary where mutually adversarial users share one agent, host, or configuration.

Practical implications:

| Area | Risk | Safer default |
|---|---|---|
| Gateway exposure | Remote control API reachable by attackers | Bind to loopback; use VPN/Tailscale or SSH tunnel |
| DM access | Unknown senders can trigger the assistant | Pairing policy or strict allowlists |
| Tool authority | Model can invoke filesystem/process tools | Deny risky tool groups by default |
| Shared inbox | Multiple users share one agent authority | Per-peer DM scope and limited tools |
| Third-party skills | Prompt/code injection through extensions | Read and verify skills before enabling |
| Remote nodes | Device capabilities exposed through Gateway | Require pairing and narrow node permissions |

A hardened baseline keeps the Gateway local-only, uses token auth, isolates DMs, and disables broad runtime/filesystem/control-plane tools unless explicitly needed.

Example shape:

```json
{
  "gateway": {
    "mode": "local",
    "bind": "loopback",
    "auth": {
      "mode": "token",
      "token": "replace-with-long-random-token"
    }
  },
  "session": {
    "dmScope": "per-channel-peer"
  },
  "tools": {
    "profile": "messaging",
    "deny": ["group:automation", "group:runtime", "group:fs"],
    "fs": { "workspaceOnly": true },
    "exec": { "security": "deny", "ask": "always" },
    "elevated": { "enabled": false }
  }
}
```

## Getting Started

Requirements:

- Node.js 24 recommended, Node.js 22.19+ supported
- API key or auth profile for a model provider
- A local machine, server, or VPS where the Gateway can run

Quick setup:

```shell
# macOS / Linux
curl -fsSL https://openclaw.ai/install.sh | bash

# Run guided setup and install the Gateway daemon
openclaw onboard --install-daemon

# Check Gateway status
openclaw gateway status

# Open the local dashboard
openclaw dashboard
```

Talk to the assistant from the CLI:

```shell
openclaw agent --message "Summarize my current workspace setup" --thinking high
```

Run the Gateway in foreground for debugging:

```shell
openclaw gateway stop
openclaw gateway --port 18789 --verbose
```

From source:

```shell
git clone https://github.com/openclaw/openclaw.git
cd openclaw

pnpm install
pnpm openclaw setup
pnpm gateway:watch
```

The source checkout uses a pnpm workspace. The official repo notes that plain `npm install` at the repository root is not the supported source-development path.

## When to Use It

OpenClaw is a good fit when:

- you want a local-first personal assistant
- messaging channels are a natural interface for your workflows
- the assistant needs controlled access to tools, files, scripts, or devices
- you are willing to manage model credentials and security policy
- you want extensibility through skills, plugins, and workspace files

It is a poor fit when:

- you only need occasional chat
- you do not want to operate a local daemon
- multiple mutually untrusted users need strong isolation on one shared assistant
- you cannot tolerate the risk of tool-enabled model mistakes
- you need deterministic workflow execution more than flexible agentic behavior

Comparison:

| Option | Best for | Main limitation |
|---|---|---|
| OpenClaw | Local personal assistant with real tools and messaging channels | Operator must own security and setup |
| Hosted chatbot | Simple Q&A and general productivity | Limited local/device control |
| Zapier-style automation | Repeatable SaaS workflows | Harder to handle open-ended tasks |
| Coding agent | Repository and terminal work | Usually not a full personal assistant surface |
| Homegrown bot | Narrow custom integration | Expensive to grow into a general agent platform |

## Operational Checklist

Before exposing OpenClaw beyond local loopback:

- Read the Gateway exposure runbook.
- Keep Gateway auth enabled unless behind a trusted private ingress.
- Prefer VPN, Tailscale, or SSH tunnels over public exposure.
- Use pairing or allowlists for inbound DMs.
- Keep high-authority tools disabled for shared or unknown senders.
- Verify third-party skills before installing.
- Run `openclaw doctor` after configuration changes.
- Back up the agent workspace and state directory if the assistant becomes operationally important.

## References

- [OpenClaw official site](https://openclaw.ai/)
- [OpenClaw GitHub repository](https://github.com/openclaw/openclaw)
- [Getting started](https://docs.openclaw.ai/start/getting-started)
- [Gateway architecture](https://docs.openclaw.ai/concepts/architecture)
- [Agent runtime](https://docs.openclaw.ai/concepts/agent)
- [Agent loop](https://docs.openclaw.ai/concepts/agent-loop)
- [Skills](https://docs.openclaw.ai/tools/skills)
- [Security](https://docs.openclaw.ai/gateway/security)
