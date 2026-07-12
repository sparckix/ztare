"""markdown — the reference Renderer. Emits a verdict as a portable Markdown summary (no external deps; the
workbench / obsidian / pdf renderers are future plug-ins over the same contract)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ztare.scenarios.protocols import RenderResult
from ztare.scenarios.registry import capability


@capability("renderer", "markdown")
class MarkdownRenderer:
    name = "markdown"

    def render(self, result: "dict[str, Any]", *, dest: str = "") -> RenderResult:
        lines = [f"# {result.get('title', 'ZTARE verdict')}", ""]
        if "verdict" in result:
            lines += [f"**Verdict:** {result['verdict']}", ""]
        if "score" in result:
            lines += [f"**Score:** {result['score']}", ""]
        for k, v in result.items():
            if k in ("title", "verdict", "score"):
                continue
            lines.append(f"- **{k}:** {v}")
        text = "\n".join(lines) + "\n"
        if dest:
            Path(dest).write_text(text, encoding="utf-8")
        return RenderResult(path=dest, text=text, kind="markdown")
