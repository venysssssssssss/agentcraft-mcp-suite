---
name: agentcraft
description: Route creative production tasks across the thirteen Storytold Crafting Apps via live MCP tools. Use to orchestrate design-to-video, PDF-to-deck, photo-to-publication and multimodal projects.
metadata:
  opencode/slash: "true"
---

# AgentCraft — cross-app orchestrator

Choose the appropriate `agentcraft-<app>` skill for each stage. Apps available:

- `photocraft`: Raster editor, layers, masks, PSD.
- `vectorcraft`: Vector drawing, SVG, shapes, paths.
- `filmcraft`: Timeline video editing and export.
- `lightcraft`: RAW photos, catalog, development.
- `pdfcraft`: PDF viewing, arranging, conversion.
- `effectcraft`: Motion graphics, VFX, keyframes.
- `designcraft`: Page layout, print publishing.
- `figcraft`: Product UI design and prototyping.
- `wordcraft`: Rich text, DOCX, PDF documents.
- `soundcraft`: Multitrack digital audio, MIDI.
- `deckcraft`: Presentation design and export.
- `cadcraft`: 2D CAD and technical drafting.
- `gridcraft`: Spreadsheets, formulas, charts.

## Operating procedure

1. Establish deliverables, target applications, canvas/page/frame dimensions, framerate and acceptable formats.
2. Decompose pipeline into discrete independent artifacts (for example: VectorCraft SVG -> EffectCraft composition -> FilmCraft rendered video).
3. For every app, read its own `agentcraft-<app>` skill **and** current MCP tool catalog. Use `python -m agentcraft catalog --apps APP` if CLI available.
4. Validate each stage's exported artifact before importing into the next. Document provenance and exact input/output paths.
5. Save working projects in addition to exports. Where possible, preserve editability, fonts, color space, resolution and assets.
6. Report tool errors and unsupported operations; never simulate success. Do not fabricate engine command ids.
7. Confirm before overwrites, deletions, public distribution, external file access or irreversible transforms.

## MCP transport and documentation

`python -m agentcraft doctor --apps all` performs read-only connection tests. `python -m agentcraft catalog --apps all --out docs/generated` produces full live tool names and JSON schemas, plus prompts and resource templates. These are **runtime-authoritative**. Each project's upstream `docs/mcp.md` or `docs/agents.md` is reference material, not a substitute for `tools/list` in the installed version.

## Cross-app example

**Motion campaign:** FigCraft for design system -> VectorCraft for assets -> PhotoCraft for composites -> EffectCraft for keyframe animation -> SoundCraft for soundtrack -> FilmCraft for timeline/final delivery. At each stage inspect, preview, export, then reopen/verify. Do not assume inter-app binary formats are mutually compatible; prefer documented SVG, PNG, WAV, video and PDF handoffs.
