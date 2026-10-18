# EffectCraft — real H.264 render via MCP (manual E2E)

This example is **not yet certified** on a real ArtCraft build. It is based on the runtime command catalog shared from EffectCraft 0.11.1 and the [upstream MCP](https://github.com/storytold/effectcraft/blob/main/docs/mcp.md) and [agent](https://github.com/storytold/effectcraft/blob/main/docs/agents.md) documentation.

## Preconditions

- Linux/WSL2 `effectcraft-cli` release is installed (default `~/.local/bin/effectcraft-cli`).
- Python 3.11+ with `agentcraft-mcp-suite` installed (virtualenv, pipx, etc.).
- `ffprobe` on PATH (`sudo apt install ffmpeg` on Ubuntu).
- A saved EffectCraft project containing a composition named `AgentCraft Smoke Test` exists at `~/BIG/agentcraft-smoke/effectcraft-smoke.ecproj`. This is the output of the previous create/save/preview smoke test.

## Execute

```bash
python examples/effectcraft_render_e2e.py
```

By default, this opens the **existing** project, selects the composition, queues the first **1 second** as H.264, waits for rendering, then verifies the output with FFprobe:

```text
~/BIG/agentcraft-smoke/effectcraft-smoke.mp4
```

Override paths and duration for your environment:

```bash
python examples/effectcraft_render_e2e.py \
  --project /abs/path/project.ecproj \
  --comp 'AgentCraft Smoke Test' \
  --output /abs/path/output.mp4 \
  --seconds 1 \
  --timeout 1800
```

An existing MP4 will not be overwritten unless `--overwrite` is explicitly provided. The script does not delete projects or modify your saved composition. However, it adds a render queue item to the *in-memory* session.

## Workflow

1. Start `effectcraft-cli mcp --project /abs/path/file.ecproj` in a single subprocess session.
2. Check `tools/list` includes `command_run`.
3. Run `comp.open {"comp":"AgentCraft Smoke Test"}`.
4. Run `renderQueue.add` with `format=h264`, an absolute output path, and `timeSpan=custom`.
5. Inspect `renderQueue.list`.
6. Call `renderQueue.render {"wait":true}` in **the same MCP process**. The underlying render may be slower on WSL2/CPU.
7. Inspect queue status, check output existence/size and validate the H.264 stream, duration and resolution with `ffprobe`.

`agentcraft call` is not suitable for multiple dependent editing steps because it starts a fresh MCP session per invocation. `--timeout` governs **each request**, not a global time budget; if it expires, inspect the output before retrying, as the render may have started.

## Expected acceptance evidence

- `command_run` reports no errors for open, queue, render and queue inspection.
- MP4 file exists and is nonempty.
- FFprobe reports a video stream with `codec_name=h264` and positive duration; script prints width, height and file size.

A passing result proves one end-to-end render for this app/version/configuration. It does **not** establish coverage for the other 12 apps or every render format. Keep `docs/verification.md` updated only after a real successful run.
