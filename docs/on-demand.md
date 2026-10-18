# Strict on-demand MCP activation — Codex, Claude Code, OpenCode

**Release 0.2.0.** The AgentCraft installer no longer registers *any* ArtCraft MCP server in the host client's MCP configuration. This is intentional. Native clients may initialize enabled MCPs at startup; deferring tool definitions is not the same as deferring process startup. A direct AgentCraft command/skill invocation uses the CLI to start **one authenticated temporary native MCP subprocess**, call its actual advertised tools repeatedly within one stateful session, and stop that subprocess when finished.

| Host | Explicit entry point | Idle ArtCraft MCP processes after migration and restart |
|---|---|---|
| OpenCode | `/agentcraft-pdfcraft` or `/agentcraft-<app>` | 0 |
| Claude Code | `/agentcraft-pdfcraft` or `/agentcraft-<app>` | 0 |
| Codex | `$agentcraft-pdfcraft` or `$agentcraft-<app>` (native skill invocation, **not** `/agentcraft-*`) | 0 |

The tool lists shown to a model may still contain **skill metadata or slash commands**. Those are prompt instructions, not running MCP servers. This design does not implement native dynamic registration of MCP tools into a running host client; agents interact through their supported shell tools. The host may not autonomously execute shell commands without user approval, and a model's choice to follow skill instructions cannot be guaranteed by a Markdown file. The absence of host MCP registrations **does** remove the default process-startup path for these 13 servers within managed configs.

## Migrate the prior eager registration

```bash
cd ~/BIG/agentcraft-mcp-suite
source .venv/bin/activate
# Update the checkout and editable Python package
# git pull --ff-only && python -m pip install -e .
agentcraft install --scope project --target . --apps all --client all --bin-dir "$HOME/.local/bin"
agentcraft audit --target .
```

Installer cleanup removes **only recognizably AgentCraft-generated ArtCraft MCP entries** from `.mcp.json`, `opencode.json`, and `.codex/config.toml`, retaining unrelated services and custom configuration. The project installer also updates the 14 skills and commands. If a colliding but unrecognized ArtCraft MCP entry exists, installation refuses to claim success; inspect the file and disable/remove the conflicting registration. The audit checks project and common home-level settings, including Claude Code's user/project config file, but cannot detect every externally managed configuration or inspect a client process already running. Restart the agent clients after migration to unload previously initialized servers.

**Important:** The `--target` directory determines where project commands/skills are installed. Configure each workspace where you want slash commands available, or use global scope. This is not the same as installing a Python package and does not install the 13 native ArtCraft applications.

## Lifecycle — one selected app, no eager host registrations

Inside an explicit `/agentcraft-pdfcraft` request, the agent runs these **shell commands**:

```bash
# 1. Start only PdfCraft, return JSON {"session":"<SID>",...}
agentcraft session start pdfcraft --bin-dir "$HOME/.local/bin" --workspace-root "$PWD"

# 2. Inspect the dynamic tool catalog and schemas
agentcraft session tools <SID> --filter doc_create --details

# 3. Reuse the same MCP subprocess through an entire document-editing workflow
agentcraft session call <SID> doc_create --arguments '{...}' --allow-write
agentcraft session call <SID> doc_save --arguments '{...}' --allow-write
agentcraft session call <SID> render_preview --arguments '{...}' --output preview-response.json

# 4. Stop it even after an error
agentcraft session stop <SID>
```

Replace `<SID>`, tool names and arguments with the **values returned by the installed native server**. Prefer JSON `--args-file` for large or complex payloads. Discovery should be in-session, and document IDs returned from one tool call may be required by subsequent tools. Do not use `agentcraft call` repeatedly for a stateful workflow: it starts a new MCP server per call.

After `session start`, `agentcraft session status <SID>` reports the process PID and selected app. `agentcraft session tools <SID> --details` exposes live schemas. `agentcraft session call` refuses mutating or unannotated tools unless `--allow-write` is supplied. `--output <file>` writes the full result to a file when tool output is very large. The session auto-expires after **10 minutes of inactivity** by default; `--idle-seconds` may adjust that value, with a minimum of 30 seconds. An active tool call, including a long render, is not interrupted by the idle watcher.

Security: a session listens **only on 127.0.0.1**, requires a randomly generated 256-bit bearer token, and stores its metadata under a private `~/.cache/agentcraft/sessions/` directory (0700, per-file 0600 on Unix). The credential is never included in process command-line arguments. Tokens are still accessible to the same OS user and should not be printed in logs or committed. The temporary server inherits the shell user's filesystem permissions unless workspace scoping is supported and enabled. The on-demand bridge is designed for a trusted local developer environment, not multi-tenant remote hosting.

## Native MCP vs on-demand bridge

In 0.1.x, `agentcraft install` wrote native host MCP configurations that could initialize **all 13 ArtCraft processes on startup**. In 0.2.0 it **does not**; only the explicit command/skill's shell workflow can start a selected subprocess. This trades host-native MCP tool invocation for startup isolation; the underlying operations still use the genuine upstream MCP `initialize`, `tools/list`, `tools/call`, and `resources/*` protocol, **not** a mock or invented API.

For users who intentionally want host-native MCP tools to appear automatically, they would need to configure such servers themselves outside AgentCraft; that setup does **not** meet the strict on-demand requirement and is not supported by the 0.2.0 installer.

## Verify

```bash
agentcraft audit --target .
# no ArtCraft MCP processes should be running after restarting host clients:
pgrep -af '[a-z]craft-cli mcp' || true

# Start ONLY when testing an explicit command or the session API:
agentcraft session start pdfcraft --bin-dir "$HOME/.local/bin"
# inspect status and stop with the returned SID
```

The automated tests use a synthetic MCP server for the session lifecycle, registration migration and CLI routing. Verify real `/agentcraft-pdfcraft` tasks separately on the user's WSL2 OpenCode, Claude Code and Codex installations. Visual PDF output and full client-command execution are **not** claimed certified until observed.
