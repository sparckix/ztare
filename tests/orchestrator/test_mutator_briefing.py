from __future__ import annotations

from pathlib import Path

from ztare.orchestrator import mutator_briefing
from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
    MutatorBriefing,
    render_default_briefing_context,
)


class RaisingProvider(BriefingProvider):
    name = "raising_provider"
    priority = 10
    tier = 0

    def applies(self, ctx: BriefingContext) -> bool:
        raise RuntimeError("fixture applies failure")

    def fragment(self, ctx: BriefingContext) -> str:
        return "unreachable\n"


class StaticProvider(BriefingProvider):
    name = "static_provider"
    priority = 20
    tier = 0

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        return "STATIC\n"


def test_render_default_briefing_context_does_not_reapply_failed_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    briefing = MutatorBriefing()
    briefing.register(RaisingProvider())
    briefing.register(StaticProvider())
    monkeypatch.setattr(mutator_briefing, "default_briefing", lambda: briefing)
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=tmp_path / "workspace",
        iter_index=1,
        rubric={},
    )

    rendered = render_default_briefing_context(ctx)

    assert "fixture applies failure" in rendered["body"]
    assert "STATIC" in rendered["body"]
    assert rendered["active_providers"] == ["raising_provider", "static_provider"]
    assert rendered["diagnostics"]["active_providers"] == [
        "raising_provider",
        "static_provider",
    ]
