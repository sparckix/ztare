from __future__ import annotations

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider
from ztare.worldmodel.leaf_workbench import (
    render_worldmodel_leaf_workbench_fragment,
    worldmodel_leaf_workbench_records,
)


class LeafWorkbenchProvider(BriefingProvider):
    name = "leaf_workbench"
    priority = 82
    tier = 1
    max_fragment_chars = 2200

    def applies(self, ctx: BriefingContext) -> bool:
        return (ctx.rubric or {}).get("fit_expression_grammar") == "grid_dsl"

    def fragment(self, ctx: BriefingContext) -> str:
        return render_worldmodel_leaf_workbench_fragment(ctx.project_dir)

    def structured_records(self, ctx: BriefingContext) -> list[dict]:
        return worldmodel_leaf_workbench_records(ctx.project_dir)
