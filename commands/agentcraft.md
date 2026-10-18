---
description: Explicit cross-app AgentCraft orchestration; start native MCPs only as required
---

Direct invocation of `/agentcraft`: `$ARGUMENTS`.

Load the `agentcraft` skill. Never register host MCPs. Plan the workflow first, then start **only the one needed app** with `agentcraft session start APP`, interact with `agentcraft session tools/call` using its SID, validate and stop it. Move to a second app only if needed, through a documented interchange format. Stop every session in cleanup, even after errors. Codex equivalent: `$agentcraft`.
