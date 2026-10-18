"""Upstream app registry. App-specific flags are sourced from upstream MCP docs."""
from dataclasses import dataclass

@dataclass(frozen=True)
class CraftApp:
    name: str
    description: str
    upstream_doc: str
    desktop_flag: str | None
    desktop_address: str | None
    headless_args: tuple[str, ...] = ("mcp",)

    @property
    def binary(self) -> str:
        return f"{self.name}-cli"

    @property
    def repository(self) -> str:
        return f"https://github.com/storytold/{self.name}"

    @property
    def mcp_docs(self) -> str:
        return f"{self.repository}/blob/main/{self.upstream_doc}"

    def args(self, mode: str = "headless") -> list[str]:
        if mode == "headless":
            return list(self.headless_args)
        if mode == "desktop":
            if not self.desktop_flag or not self.desktop_address:
                raise ValueError(f"Desktop MCP bridge not documented for {self.name}")
            return ["mcp", self.desktop_flag, self.desktop_address]
        raise ValueError(f"Unsupported mode: {mode}")

APPS = {
    a.name: a for a in [
        CraftApp("photocraft", "Raster editor, layers, masks, PSD", "docs/mcp.md", "--bridge", "127.0.0.1:7878"),
        CraftApp("vectorcraft", "Vector drawing, SVG, shapes, paths", "docs/mcp.md", "--connect", "127.0.0.1:7979", ("mcp", "--headless")),
        CraftApp("filmcraft", "Timeline video editing and export", "docs/agents.md", "--bridge", "127.0.0.1:9876"),
        CraftApp("lightcraft", "RAW photos, catalog, development", "docs/mcp.md", "--connect", "127.0.0.1:7980"),
        CraftApp("pdfcraft", "PDF viewing, arranging, conversion", "docs/mcp.md", None, None),
        CraftApp("effectcraft", "Motion graphics, VFX, keyframes", "docs/agents.md", "--bridge", "9877"),
        CraftApp("designcraft", "Page layout, print publishing", "docs/mcp.md", "--connect", "7979"),
        CraftApp("figcraft", "Product UI design and prototyping", "docs/mcp.md", "--attach", "7979"),
        CraftApp("wordcraft", "Rich text, DOCX, PDF documents", "docs/mcp.md", "--connect", "127.0.0.1:7981"),
        CraftApp("soundcraft", "Multitrack digital audio, MIDI", "docs/mcp.md", "--connect", "7801"),
        CraftApp("deckcraft", "Presentation design and export", "docs/mcp.md", "--connect", "7979"),
        CraftApp("cadcraft", "2D CAD and technical drafting", "docs/mcp.md", "--connect", "127.0.0.1:7979"),
        CraftApp("gridcraft", "Spreadsheets, formulas, charts", "docs/mcp.md", "--connect", "7979"),
    ]
}
