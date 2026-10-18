# AgentCraft MCP Suite

**Use the 13 Storytold ArtCraft creative applications from Codex, Claude Code, and OpenCode through their native MCP servers.**

One installer. Fourteen reusable Agent Skills (13 specialists + an orchestrator). A CLI to inspect live MCP endpoints and export their schemas. No unofficial endpoints, invented commands, or bundled application binaries.

> [!IMPORTANT]
> **Release 0.2.0:** Strict on-demand startup by default. The user-run WSL2 MCP handshake succeeded for 13/13 native apps and the EffectCraft H.264 smoke test passed; host-command execution and fully creative workflows still require end-to-end testing.

**[Strict on-demand](#strict-on-demand-activation-v020)** · **[Quick start](#quick-start)** · **[Português](docs/quickstart-pt-BR.md)** · **[Applications](#supported-applications)** · **[Client integration](#integrate-with-your-agent)** · **[MCP reference](#discover-every-supported-mcp-endpoint)** · **[Security](#security-model)** · **[Troubleshooting](#troubleshooting)**

## Strict on-demand activation (v0.2.0)

**No ArtCraft MCP servers are registered in Codex, Claude Code, or OpenCode at startup.** Commands and skills remain available as small prompts. The invoked skill uses the AgentCraft CLI to launch exactly one selected native MCP subprocess, retain its editing state across calls, and stop it afterward. The daemon also auto-expires after 10 minutes of inactivity.

**Explicit entry points:** OpenCode and Claude Code: `/agentcraft-pdfcraft`; Codex: `$agentcraft-pdfcraft` (Codex skills use `# AgentCraft MCP Suite

**Use the 13 Storytold ArtCraft creative applications from Codex, Claude Code, and OpenCode through their native MCP servers.**

One installer. Fourteen reusable Agent Skills (13 specialists + an orchestrator). A CLI to inspect live MCP endpoints and export their schemas. No unofficial endpoints, invented commands, or bundled application binaries.

> [!IMPORTANT]
> **Release 0.2.0:** Strict on-demand startup by default. The user-run WSL2 MCP handshake succeeded for 13/13 native apps and the EffectCraft H.264 smoke test passed; host-command execution and fully creative workflows still require end-to-end testing.

**[Strict on-demand](#strict-on-demand-activation-v020)** · **[Quick start](#quick-start)** · **[Português](docs/quickstart-pt-BR.md)** · **[Applications](#supported-applications)** · **[Client integration](#integrate-with-your-agent)** · **[MCP reference](#discover-every-supported-mcp-endpoint)** · **[Security](#security-model)** · **[Troubleshooting](#troubleshooting)**

, not the custom slash command syntax). The same pattern covers all 13 apps.

**Migration of previous eager configs:** from an activated checkout run:

```bash
git pull --ff-only
python -m pip install -e .
agentcraft install --scope project --target . --apps all --client all --bin-dir "$HOME/.local/bin"
agentcraft audit --target .
```

Restart all agent clients afterward: processes initialized under v0.1.1 may remain alive until the clients restart. The installer removes only recognizable AgentCraft registrations and refuses unrecognized collisions; `audit` also checks common global config locations. Other plugins or explicit manual registrations are outside the installer's control.

**Important architecture distinction:** This is real upstream MCP over short-lived local subprocesses, driven by client **shell tools**, not automatic injection of native MCP tools into a running host. A skill cannot force the LLM to obey commands or guarantee that arbitrary shell use happens only after a slash command. The guaranteed property in managed configurations is **zero eager ArtCraft MCP registrations**.

See the complete [on-demand design, session API, migration, security and limitations](docs/on-demand.md).

### Manual session example

```bash
agentcraft session start pdfcraft --bin-dir "$HOME/.local/bin" --workspace-root "$PWD"
# Copy the JSON `session` field into SID:
agentcraft session tools SID --details
agentcraft session call SID doc_inspect --arguments '{}'
agentcraft session stop SID
```

## Quick start

## Quick start

**Requirements:** Python 3.11+, an installed Codex/Claude Code/OpenCode client, and **at least one actual ArtCraft `*-cli` executable** from an [upstream release](https://getartcraft.com/apps) or upstream Rust build. Installing this Python package does **not** install the ArtCraft applications.

### 1. Install AgentCraft

On **Ubuntu / Debian / WSL2** with Python 3.12+, the system Python is often *externally managed* (PEP 668). Do **not** install this CLI into system Python and do **not** use `--break-system-packages`.

**Option A — pipx (recommended for a reusable CLI across projects):**

```bash
git clone https://github.com/venysssssssssss/agentcraft-mcp-suite.git
cd agentcraft-mcp-suite
sudo apt update && sudo apt install -y pipx
pipx ensurepath
pipx install .
~/.local/bin/agentcraft --version
```

Open a fresh terminal after `pipx ensurepath` if `agentcraft` is not on `PATH`. The command installed by pipx is available independently of a Python virtual environment. To reinstall a local modified checkout, use `pipx reinstall agentcraft-mcp-suite` or uninstall and install again.

**Option B — virtual environment (editable checkout / development):**

```bash
git clone https://github.com/venysssssssssss/agentcraft-mcp-suite.git
cd agentcraft-mcp-suite
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
agentcraft --version
```

Keep that environment activated when using the command, or invoke `./.venv/bin/agentcraft` directly. If `venv` fails due to missing `ensurepip`, install `python3-venv` through `apt`. On Windows, activate `.venv\\Scripts\\Activate.ps1` in PowerShell instead.

The examples below assume `agentcraft` is available on your `PATH`. The installer writes skills to the **specified target workspace**; running `--target .` inside this repository configures this repository, not every other project.

### 2. Install the native ArtCraft CLIs (Ubuntu / WSL2)

Installing AgentCraft itself does not install the upstream applications. For Linux x86_64 and aarch64, this repository includes an **optional standalone installer** that downloads the official GitHub Release `.tar.gz` trees and verifies their published SHA-256 digests. It extracts them under `~/.local/share/agentcraft/native`, keeping resource files alongside the binaries, and links the `*-cli` files under `~/.local/bin`. It does not require sudo, Rust builds, or system-wide Python modifications.

Start with just one app and validate its real MCP server:

```bash
# From this repository
bash scripts/install-native-linux.sh effectcraft
agentcraft install --scope project --target . --apps effectcraft --client all --bin-dir "$HOME/.local/bin"
agentcraft doctor --apps effectcraft --bin-dir "$HOME/.local/bin"
```

To install all thirteen *native app release trees* (downloads approximately **938 MiB** for Linux x86_64 as of October 2026, plus extracted size and runtime dependencies), use:

```bash
df -h /
bash scripts/install-native-linux.sh --all
agentcraft install --scope project --target . --apps all --client all --bin-dir "$HOME/.local/bin"
agentcraft doctor --apps all --bin-dir "$HOME/.local/bin"
```

This operation is intentionally opt-in because WSL virtual disks grow with downloaded files. A successful download does **not** guarantee an MCP connection: native shared libraries and application-version differences can still prevent startup. If the doctor reports an ELF/shared-library failure, inspect `ldd ~/.local/bin/effectcraft-cli` and install only the missing system runtime packages after review.

### 3. Install on-demand skills and commands in a working project

```bash
# Linux / macOS / WSL: adapt these paths to your machine.
agentcraft install \
  --scope project \
  --target /path/to/your-workspace \
  --apps effectcraft,filmcraft,vectorcraft \
  --client all
```

`--apps all` installs specialist skills and commands for the 13 apps, but **never registers MCPs at host startup**. `--strict` fails when an app is missing instead of silently skipping its MCP registration.

If executables are not on `PATH`, use `--bin-dir /path/to/cli-directory` if they are together, or define per-app variables such as `AGENTCRAFT_EFFECTCRAFT_CLI=/absolute/path/to/effectcraft-cli`. On Windows use the full `.exe` path.

For **PowerShell**, the same command on one line:

```powershell
agentcraft install --scope project --target C:\Dev\my-project --apps effectcraft,filmcraft,vectorcraft --client all
```

If you run agents in **WSL2**, use Linux-native ArtCraft binaries inside WSL. Installing an `.exe` on Windows does not make its GUI, file paths, sockets, or MCP subprocess lifecycle equivalent to a native WSL process. Run the agent and its MCP binary in the **same OS environment** whenever possible.

### 4. Validate the connection and load commands

```bash
agentcraft doctor --apps effectcraft,filmcraft,vectorcraft
agentcraft catalog --apps effectcraft,filmcraft,vectorcraft --engine --out docs/generated
```

Restart your agent client to pick up the newly installed skills and MCP definitions. The `doctor` command is a **live MCP handshake and discovery test**, not a rendering or functional acceptance test.

## Integrate with your agent

| Host | On-demand command | MCP process started at host startup? |
|---|---|---|
| OpenCode | `/agentcraft-pdfcraft` | **No** |
| Claude Code | `/agentcraft-pdfcraft` | **No** |
| Codex | `$agentcraft-pdfcraft` | **No** |

The slash command (or Codex skill) instructs the model to use its **shell tool** to call `agentcraft session start`, `session tools`, `session call`, and `session stop`. It deliberately does **not** register any native ArtCraft MCP tool with the host. Review [the actual lifecycle](docs/on-demand.md) before relying on it.

**Example test prompt:** `/agentcraft-pdfcraft Create a three-page A4 Nike-inspired black-and-white editorial with lorem ipsum. Use only the PdfCraft native MCP through AgentCraft's temporary session, save ./nike-concept.pdf, verify page count and output, and stop the session.`

## EffectCraft H.264 render smoke test (manual E2E)

After [creating and saving an EffectCraft project](docs/effectcraft-render-e2e.md), run a single-session MCP render of **1 second** to MP4, then verify the encoded video stream with FFprobe:

```bash
# Ubuntu / WSL2 (in your activated AgentCraft venv)
sudo apt install -y ffmpeg
python examples/effectcraft_render_e2e.py
```

This invokes `comp.open` → `renderQueue.add` → `renderQueue.list` → `renderQueue.render` → `renderQueue.list` in the **same** MCP process, avoiding the state loss of repeated `agentcraft call` invocations. It refuses to overwrite an existing MP4 by default.

**Real-world validation (2026-10-18, user-executed WSL2):** EffectCraft 0.11.1 completed the full native MCP render workflow. FFprobe verified a 1.0-second, 1920×1080 H.264 MP4 (32,388 bytes); engine reported 30 frames, 0 failed items and approximately 1.08 seconds of render time. This is evidence from a user-provided local terminal log, **not** a CI run or independent visual/animation quality certification. CI still exercises a simulated MCP server. See the [manual procedure](docs/effectcraft-render-e2e.md) and [verification matrix](docs/verification.md).

## Supported applications

| Skill / MCP server | Primary workflow | Authoritative upstream documentation |
|---|---|---|
| [`photocraft`](skills/agentcraft-photocraft/SKILL.md) | Raster editing, layers, compositing | [PhotoCraft MCP](https://github.com/storytold/photocraft/blob/main/docs/mcp.md) |
| [`vectorcraft`](skills/agentcraft-vectorcraft/SKILL.md) | Vector paths, illustration, SVG | [VectorCraft MCP](https://github.com/storytold/vectorcraft/blob/main/docs/mcp.md) |
| [`filmcraft`](skills/agentcraft-filmcraft/SKILL.md) | Timeline, video editing and output | [FilmCraft agents](https://github.com/storytold/filmcraft/blob/main/docs/agents.md) |
| [`lightcraft`](skills/agentcraft-lightcraft/SKILL.md) | Photography, RAW and grading | [LightCraft MCP](https://github.com/storytold/lightcraft/blob/main/docs/mcp.md) |
| [`pdfcraft`](skills/agentcraft-pdfcraft/SKILL.md) | PDF reading and manipulation | [PdfCraft MCP](https://github.com/storytold/pdfcraft/blob/main/docs/mcp.md) |
| [`effectcraft`](skills/agentcraft-effectcraft/SKILL.md) | Motion graphics and effects | [EffectCraft agents](https://github.com/storytold/effectcraft/blob/main/docs/agents.md) · [MCP](https://github.com/storytold/effectcraft/blob/main/docs/mcp.md) |
| [`designcraft`](skills/agentcraft-designcraft/SKILL.md) | Page and publication design | [DesignCraft MCP](https://github.com/storytold/designcraft/blob/main/docs/mcp.md) |
| [`figcraft`](skills/agentcraft-figcraft/SKILL.md) | UI mockups and product interfaces | [FigCraft MCP](https://github.com/storytold/figcraft/blob/main/docs/mcp.md) |
| [`wordcraft`](skills/agentcraft-wordcraft/SKILL.md) | Rich-text documents | [WordCraft MCP](https://github.com/storytold/wordcraft/blob/main/docs/mcp.md) |
| [`soundcraft`](skills/agentcraft-soundcraft/SKILL.md) | Multitrack audio and MIDI | [SoundCraft MCP](https://github.com/storytold/soundcraft/blob/main/docs/mcp.md) |
| [`deckcraft`](skills/agentcraft-deckcraft/SKILL.md) | Presentation slides | [DeckCraft MCP](https://github.com/storytold/deckcraft/blob/main/docs/mcp.md) |
| [`cadcraft`](skills/agentcraft-cadcraft/SKILL.md) | 2D technical drawing | [CADCraft MCP](https://github.com/storytold/cadcraft/blob/main/docs/mcp.md) |
| [`gridcraft`](skills/agentcraft-gridcraft/SKILL.md) | Spreadsheet models and charts | [GridCraft MCP](https://github.com/storytold/gridcraft/blob/main/docs/mcp.md) |

**Names:** Skill IDs are `agentcraft-<app>`, while MCP server IDs are `<app>`. The additional `agentcraft` orchestrator is a skill, not a fourteenth MCP server.

### Headless vs. desktop control

All 13 upstream projects document headless MCP entrypoints. GUI bridge flags are application-specific:

| Native bridge flag | Applications |
|---|---|
| `--bridge` | PhotoCraft, FilmCraft, EffectCraft |
| `--connect` | VectorCraft, LightCraft, DesignCraft, WordCraft, SoundCraft, DeckCraft, CADCraft, GridCraft |
| `--attach` | FigCraft |
| No documented desktop bridge in AgentCraft registry | PdfCraft |

Example of a temporary desktop session, **after** launching the application's GUI with its control port:

```bash
agentcraft session start effectcraft --mode desktop --bin-dir "$HOME/.local/bin"
```

PhotoCraft requires an additional `--photocraft-token-file` matching the desktop app's control-token file. Desktop bridges may fail unless their GUI is running; they should not be exposed over public network interfaces. See upstream docs before using live control.

## Discover every supported MCP endpoint

Never hard-code presumed MCP tool names or command IDs. Some upstream servers expose generic tools such as `command_list` and `command_run` that in turn expose a **separate internal engine-command catalog**.

```bash
# Runtime MCP endpoints: complete returned JSON schemas, annotations,
# resources/templates and prompts (where implemented).
agentcraft catalog --apps all --out docs/generated

# Also request internal engine commands when upstream exposes discovery.
agentcraft catalog --apps effectcraft --engine --out docs/generated
```

Output: `docs/generated/effectcraft.md` (readable reference) and `effectcraft.json` (machine-readable snapshot), with equivalent files for every responding app. A catalog is specific to the **currently installed version, operating mode, and document state**; rerun it after upgrading the apps.

For direct one-off inspection:

```bash
agentcraft call effectcraft command_list --arguments '{}'
# Only after explicit review of a mutating tool and engine ID:
agentcraft call effectcraft command_run \
  --arguments '{"id":"<id-from-current-command-list>","params":{}}' --allow-write
```

The placeholder ID is intentional; substitute a real ID discovered from your running engine. `call` starts a **fresh MCP process** for each invocation. Use the native MCP connection in your agent for editing that depends on an ongoing in-memory session. Detailed design: [architecture](docs/architecture.md).

## Security model

- **OS authority:** Native MCP servers inherit the privileges of the process running them; they can read/write files according to upstream behavior. A skill is not a sandbox.
- **Scoped filesystem:** For upstream builds with verified `--automation-read-root` / `--automation-write-root`, enable `--file-scope workspace` in **project** scope. Coverage varies; certain scripting/GUI capabilities are deliberately unavailable in confined mode.
- **Mutating operations:** `agentcraft session call` requires `--allow-write` when `annotations.readOnlyHint` is not explicitly true; the agent's native MCP connection still uses its own authorization controls.
- **Secrets:** Do not commit `.mcp.json` containing private tokens, generated agent configuration, credentials or exported client data. Keep GUI control channels on loopback.
- **Source integrity:** Download ArtCraft binaries from upstream and verify platform signatures/checksums when provided. This repository includes original integration code and prompts only.

## Troubleshooting

| Symptom | Action |
|---|---|
| `externally-managed-environment` or `agentcraft: command not found` | On Ubuntu/WSL2, install through `pipx` or an activated `venv` (see Quick start). Never bypass PEP 668 with `--break-system-packages`. |
| `*-cli not found` | Install/build the upstream CLI, add it to PATH, pass `--bin-dir`, or set `AGENTCRAFT_<APP>_CLI`. |
| Skill visible but no tools | A skill is not a server. Run `agentcraft doctor --apps <app>`; reinstall config; restart client. |
| GUI bridge connection refused | Start the desktop app with the documented `--control` port; verify token and flags. |
| Windows CLI and WSL agent cannot connect | Install a native Linux build in WSL, or run the client and CLI together on Windows. |
| OpenCode refuses `mcp.servers` | That was an invalid config emitted in AgentCraft 0.1.0. Run the 0.1.1 installer again to migrate the known legacy shape. |
| Tool missing or parameters rejected | Regenerate `agentcraft catalog --engine`; inspect the exact installed schema and engine command IDs. |
| Export returned success but file is absent | Reopen and validate the artifact; do not treat an MCP acknowledgment as proof of output quality. |
| Large MCP catalogs exhaust context | Enable only the servers needed for the current task; keep generated references on disk. |

## Develop and verify

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q agentcraft
agentcraft doctor --apps effectcraft  # requires effectcraft-cli installed
```

CI tests the installer, migration and on-demand sessions using a simulated MCP server. User-observed native ArtCraft runs and EffectCraft H.264 rendering are separate from CI; client slash-command execution remains unverified. Contributions adding real-bin smoke tests, upstream compatibility checks and verified sample projects are welcome. See [verification](docs/verification.md).

```text
agentcraft/           Python installer, registry, JSON-RPC MCP inspector
skills/               13 app skills plus cross-app orchestrator
commands/             Claude Code and OpenCode command definitions
docs/                 architecture, validation and generated references
scripts/              public-repo publishing helpers
.github/workflows/    unit test CI
```

## License and attribution

The AgentCraft integration code and instruction files are provided under **MIT** ([LICENSE](LICENSE)). The upstream Storytold ArtCraft apps are independent projects subject to their own licenses. **AgentCraft is a community integration, not an official Storytold/ArtCraft product, and is not affiliated with or endorsed by the upstream maintainers.**
