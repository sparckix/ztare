"""Live-champion briefing provider.

Reads workspace/champion_materialization.jsonl (written by
validator/core/champion_materialization.py) and surfaces the promoted
champion's identity as an UNMISSABLE directive for science-leaf agents.

Without this provider the leaf cannot identify the champion to patch,
reinvents from scratch, regresses, and gets blocked.

Priority 18 — renders before contract_rules (20) so the champion identity
is the very first thing the leaf sees. Tier 0 (always; a champion receipt
is not advisory).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class LiveChampionProvider(BriefingProvider):
    name = "live_champion"
    priority = 18
    tier = 0

    def __init__(self, project_dir: str | Path | None = None) -> None:
        # Allow direct construction with a project dir for testing/CLI use.
        self._project_dir_override = Path(project_dir) if project_dir is not None else None

    def _project(self, ctx: BriefingContext) -> Path:
        if self._project_dir_override is not None:
            return self._project_dir_override
        return Path(ctx.project_dir)

    def _newest_receipt(self, project: Path) -> dict[str, Any] | None:
        ledger = project / "workspace" / "champion_materialization.jsonl"
        if not ledger.is_file():
            return None
        best: dict[str, Any] | None = None
        try:
            for line in ledger.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and row.get("result") == "promoted":
                    best = row  # last promoted row wins (append order = chronological)
        except OSError:
            return None
        return best

    def applies(self, ctx: BriefingContext) -> bool:
        project = self._project(ctx)
        receipt = self._newest_receipt(project)
        if receipt is not None:
            return True
        # Fallback: test_model.py exists but no receipt
        return (project / "test_model.py").is_file()

    def fragment(self, ctx: BriefingContext) -> str:
        project = self._project(ctx)
        receipt = self._newest_receipt(project)
        if receipt is not None:
            return self._render_from_receipt(receipt)
        # Fallback: test_model exists but no promotion receipt
        if (project / "test_model.py").is_file():
            return (
                "\n## Live Champion\n"
                "- LIVE CHAMPION: `test_model.py` — no promotion receipt found; metrics unavailable.\n"
            )
        return ""

    def _render_from_receipt(self, receipt: dict[str, Any]) -> str:
        from_ref = str(receipt.get("from_ref") or "test_model.py")
        promoted_sha = str(receipt.get("promoted_sha") or "")
        ts = str(receipt.get("ts") or "")
        gate_after = receipt.get("gate_summary_after") or {}
        harness_ok = gate_after.get("harness_ok")
        score = gate_after.get("score")
        dominance = receipt.get("dominance_receipt") or {}
        rank_after = dominance.get("rank_after")
        rank_before = dominance.get("rank_before")

        metrics_parts: list[str] = []
        if harness_ok is not None:
            metrics_parts.append(f"harness_ok={harness_ok}")
        if score is not None:
            metrics_parts.append(f"score={score}")
        if rank_after is not None:
            metrics_parts.append(f"rank_after={rank_after}")
        if rank_before is not None:
            metrics_parts.append(f"rank_before={rank_before}")
        metrics_str = ", ".join(metrics_parts) if metrics_parts else "(see receipt)"
        sha_suffix = f" sha={promoted_sha}" if promoted_sha else ""
        ts_suffix = f" ts={ts}" if ts else ""

        return (
            "\n## Live Champion (Patch Base)\n"
            f"- MANDATORY: `{from_ref}`{sha_suffix}{ts_suffix} is the LIVE CHAMPION.\n"
            f"  Gate summary after promotion: {metrics_str}.\n"
            "  Preserve its behavior. Modify ONLY where held-out evidence diverges.\n"
            "  Authoring from scratch regresses this champion and will be blocked by "
            "the pre-judge gate.\n"
        )

    def structured_records(self, ctx: BriefingContext) -> list[dict[str, Any]]:
        project = self._project(ctx)
        receipt = self._newest_receipt(project)
        if receipt is None:
            return []
        return [{
            "provider": self.name,
            "source_type": "live_champion_receipt",
            "from_ref": receipt.get("from_ref"),
            "promoted_sha": receipt.get("promoted_sha"),
            "result": receipt.get("result"),
            "ts": receipt.get("ts"),
            "gate_summary_after": receipt.get("gate_summary_after"),
        }]

    def render(self) -> str:
        """Convenience method for direct instantiation (testing / CLI probe)."""
        from ztare.orchestrator.mutator_briefing import BriefingContext
        from pathlib import Path
        if self._project_dir_override is None:
            return "(no project_dir set)"
        ctx = BriefingContext(
            project_dir=self._project_dir_override,
            iter_index=0,
            rubric={},
        )
        return self.fragment(ctx)
