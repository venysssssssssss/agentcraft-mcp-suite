---
description: Explicitly start a temporary deckcraft MCP session only for this slash command
---

**EXPLICIT ON-DEMAND ACTIVATION:** The user directly invoked `/agentcraft-deckcraft` with: `$ARGUMENTS`.

Load `agentcraft-deckcraft` skill instructions for capabilities. Use shell commands (not host-registered MCP tools) to:

1. Resolve the CLI (`agentcraft` on PATH or `./.venv/bin/agentcraft` in the AgentCraft checkout).
2. Start exactly one authenticated native MCP session with `agentcraft session start deckcraft --bin-dir "$HOME/.local/bin"` (add `--workspace-root "$PWD"` if supported and the task needs restricted file access). Capture the JSON `session` value as SID.
3. Discover tools via `agentcraft session tools SID --details` and inspect their actual schemas. Then call them via `agentcraft session call SID TOOL --arguments '{...}'`, adding `--allow-write` only for explicitly intended mutations. Multiple calls with the same SID preserve editing state. For large responses, use `--output /some/controlled/file.json`.
4. Validate outputs using the native MCP and appropriate independent inspections; do not fabricate success, tools or parameters.
5. **Always** run `agentcraft session stop SID` in a cleanup/finally step, including after a failure. Idle expiry is the safety fallback.

Do not register, enable, reload or start *any other* MCP server. Do not invoke this workflow from unrelated prompts or silently enable servers at agent startup. If the CLI/native binary/shell execution is unavailable, explain the limitation rather than falling back to eager host registration.
