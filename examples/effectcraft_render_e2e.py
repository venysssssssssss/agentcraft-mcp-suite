#!/usr/bin/env python3
"""Render an existing EffectCraft project to H.264 MP4 in one MCP session.

Uses upstream-exposed command IDs; fails closed if a step reports an MCP error.
Requires an EffectCraft CLI release and ffprobe for media validation.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from agentcraft.mcp import MCPError, MCPProcess


def command(mcp: MCPProcess, command_id: str, params: dict) -> dict:
    print(f"MCP command: {command_id}", flush=True)
    result = mcp.request("tools/call", {
        "name": "command_run", "arguments": {"id": command_id, "params": params},
    })
    if result.get("isError"):
        details = "\n".join(str(part.get("text", "")) for part in result.get("content", []) if isinstance(part, dict))
        raise RuntimeError(f"{command_id} failed: {details[:3500] or result}")
    return result


def summary(result: dict, limit: int = 1400) -> str:
    parts = [str(p.get("text", "")) for p in result.get("content", []) if isinstance(p, dict) and p.get("type") == "text"]
    return "\n".join(parts)[:limit] or "(no text response)"


def verify_media(video: Path, ffprobe_bin: str) -> dict:
    if not video.is_file() or video.stat().st_size <= 0:
        raise RuntimeError(f"Render finished but output is missing or empty: {video}")
    result = subprocess.run([
        ffprobe_bin, "-v", "error", "-show_entries",
        "format=duration,size:stream=index,codec_name,codec_type,width,height,avg_frame_rate",
        "-of", "json", str(video),
    ], capture_output=True, text=True, check=False, timeout=120)
    if result.returncode:
        raise RuntimeError(f"ffprobe failed ({result.returncode}): {result.stderr[:1500]}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe output is not JSON: {result.stdout[:700]}") from exc
    streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    if not streams or streams[0].get("codec_name") != "h264":
        raise RuntimeError(f"Expected H.264 video; got streams={streams}")
    duration = float(data.get("format", {}).get("duration", "0"))
    if duration <= 0:
        raise RuntimeError(f"Invalid media duration: {duration}")
    return {"codec": streams[0]["codec_name"], "width": streams[0].get("width"),
            "height": streams[0].get("height"), "duration_seconds": duration,
            "size_bytes": video.stat().st_size, "ffprobe": data}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", type=Path, default=Path.home()/"BIG/agentcraft-smoke/effectcraft-smoke.ecproj")
    p.add_argument("--output", type=Path, default=Path.home()/"BIG/agentcraft-smoke/effectcraft-smoke.mp4")
    p.add_argument("--comp", default="AgentCraft Smoke Test", help="existing composition name (case-sensitive)")
    p.add_argument("--seconds", type=float, default=1.0, help="render from 0 to N seconds")
    p.add_argument("--binary", type=Path, default=Path.home()/".local/bin/effectcraft-cli")
    p.add_argument("--timeout", type=float, default=1800.0, help="MCP request deadline; CPU renders can be slow")
    p.add_argument("--overwrite", action="store_true", help="allow replacing an existing output file")
    args = p.parse_args(argv)
    project, output, binary = (x.expanduser().resolve() for x in (args.project, args.output, args.binary))
    if not project.is_file():
        p.error(f"project not found: {project} (create the project with the earlier smoke test)")
    if not binary.is_file():
        p.error(f"EffectCraft CLI not found: {binary}")
    if args.seconds <= 0 or args.seconds > 30:
        p.error("--seconds must be greater than 0 and at most 30 for this smoke test")
    if args.timeout <= 1:
        p.error("--timeout must be greater than 1 second")
    if output.exists() and not args.overwrite:
        p.error(f"output already exists: {output}; use --overwrite only after reviewing it")
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin:
        p.error("ffprobe not found: install with `sudo apt install ffmpeg` before running")
    output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Input: {project}\nOutput: {output}\nComposition: {args.comp}\nDuration: {args.seconds}s", flush=True)
    try:
        with MCPProcess([str(binary), "mcp", "--project", str(project)], timeout=args.timeout) as mcp:
            available = {tool.get("name") for tool in mcp.list_paginated("tools/list", "tools")}
            needed = {"command_run"}
            if not needed <= available:
                raise RuntimeError(f"Missing MCP tools: {sorted(needed-available)}")
            command(mcp, "comp.open", {"comp": args.comp})
            queued = command(mcp, "renderQueue.add", {
                "comp": args.comp,
                "format": "h264",
                "output": str(output),
                "timeSpan": "custom",
                "start": 0.0,
                "end": args.seconds,
                "audio": "off",
            })
            print("Queued:", summary(queued), flush=True)
            before = command(mcp, "renderQueue.list", {})
            print("Queue before render:", summary(before), flush=True)
            rendered = command(mcp, "renderQueue.render", {"wait": True})
            print("Render response:", summary(rendered), flush=True)
            after = command(mcp, "renderQueue.list", {})
            print("Queue after render:", summary(after), flush=True)
        media = verify_media(output, ffprobe_bin)
        print("PASS: MP4 file validated", flush=True)
        print(json.dumps({k: v for k, v in media.items() if k != "ffprobe"}, indent=2), flush=True)
        return 0
    except (MCPError, OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: {exc}", file=sys.stderr, flush=True)
        print("If MCP render times out, inspect the output and queue state before retrying;", file=sys.stderr)
        print("a timeout is not proof that the engine did not finish the render.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
