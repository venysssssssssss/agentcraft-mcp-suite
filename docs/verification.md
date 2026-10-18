# Verification matrix

| Layer | Evidence | Status |
|---|---|---|
| 13 named skills | Files exist, frontmatter checked by unit tests | Automated |
| Claude Code commands | Files exist with `/agentcraft-*` routes | Generated; host runtime untested |
| OpenCode commands | Files exist with `/agentcraft-*` routes | Generated; host runtime untested |
| Codex Skills | `SKILL.md` in `.agents/skills` and TOML registration | Generated; host runtime untested |
| OpenCode MCP registration | `mcp.<app>` JSON schema (flat `command`, integer `timeout`) | Unit-tested, including migration from 0.1.0 |
| MCP JSON-RPC transport | mock `initialize`, `tools/list` pagination and missing method | Unit-tested |
| Live binary handshake | `agentcraft doctor` against each installed CLI | **Requires target machines** |
| Exhaustive MCP tool catalog | Dynamic `tools/list` pagination, JSON schemas | Tooling implemented; live output pending |
| Engine command list | Optional `--engine`, where read-only listing tool exists | Tooling implemented; coverage app-dependent |
| GUI bridges | Vary per app and control-port/token setup | **Not tested** |
| Render, export, round-trip fidelity | Real projects/formats and visual QC | **Not tested** |
| Security and confinement | Explicit flags supported by each upstream | **Requires per-app audit** |

## Acceptance plan for v1.0

For each app and release: verify binary checksums and version, test MCP `initialize`, paginate `tools/list`, run a benign create/edit action, preview/render, export to temp folder, reopen and inspect artifact, record tool latency, assess permission controls and output corruption/overwrite scenarios. Generate a JSON schema snapshot and keep source commit SHA. Run on Windows native + Linux; WSL must use its own installed Linux binary or a deliberately configured Windows `.exe` bridge. The acceptance gate is **13/13 reproducible native edit-and-export workflows**. No success declaration without that evidence.
