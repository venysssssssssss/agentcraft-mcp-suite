# Verification matrix

| Layer | Evidence | Status |
|---|---|---|
| 13 named skills | Files exist, frontmatter checked by unit tests | Automated |
| Claude Code commands | Files exist with `/agentcraft-*` routes | Generated; host runtime untested |
| OpenCode commands | Files exist with `/agentcraft-*` routes | Generated; host runtime untested |
| Codex Skills | `SKILL.md` in `.agents/skills` and TOML registration | Generated; host runtime untested |
| OpenCode MCP registration | `mcp.<app>` JSON schema (flat `command`, integer `timeout`) | Unit-tested, including migration from 0.1.0 |
| MCP JSON-RPC transport | mock `initialize`, `tools/list` pagination and missing method | Unit-tested |
| Live binary handshake | User-provided WSL2 output (2026-10-18): `agentcraft doctor --apps all` returned OK for 13/13 installed CLIs | **Confirmed by user log; not reproduced in CI** |
| Exhaustive MCP tool catalog | Dynamic `tools/list` pagination, JSON schemas | Tooling implemented; user reported live discovery; versioned snapshots not independently audited |
| Engine command list | Optional `--engine`, where read-only listing tool exists | Tooling implemented; coverage app-dependent |
| GUI bridges | Vary per app and control-port/token setup | **Not tested** |
| EffectCraft project create/save/preview | User-provided WSL2 log: created 1920x1080 project, text layer, saved `.ecproj`, preview included image and text | **User-run success; EffectCraft 0.11.1 only** |
| EffectCraft H.264 export | User-executed WSL2 run (2026-10-18): `effectcraft_render_e2e.py` completed 30-frame queue render, 0 failures; FFprobe verified `h264`, 1920×1080, 1.0 s and 32,388 bytes | **User-run real E2E success on EffectCraft 0.11.1; not reproduced in CI** |
| Animated-frame difference / motion and visual fidelity | Motion-keyframe scene, frame checksums, manual visual inspection | **Not yet tested** |
| Render, export, round-trip fidelity across 13 apps | Real projects/formats and visual QC | **EffectCraft: H.264 encoding smoke passed; full cross-app validation pending** |
| Security and confinement | Explicit flags supported by each upstream | **Requires per-app audit** |

## Acceptance plan for v1.0

For each app and release: verify binary checksums and version, test MCP `initialize`, paginate `tools/list`, run a benign create/edit action, preview/render, export to temp folder, reopen and inspect artifact, record tool latency, assess permission controls and output corruption/overwrite scenarios. Generate a JSON schema snapshot and keep source commit SHA. Run on Windows native + Linux; WSL must use its own installed Linux binary or a deliberately configured Windows `.exe` bridge. The acceptance gate is **13/13 reproducible native edit-and-export workflows**. No success declaration without that evidence.
