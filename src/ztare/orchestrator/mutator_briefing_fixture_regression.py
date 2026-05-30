from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
    MutatorBriefing,
)


class StaticProvider(BriefingProvider):
    def __init__(self, name: str, tier: int, text: str, priority: int = 500) -> None:
        self.name = name
        self.tier = tier
        self.priority = priority
        self._text = text

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        return self._text


def _render(tmp: Path, *, stagnation: int, rubric: dict) -> tuple[str, dict]:
    briefing = MutatorBriefing()
    briefing.register(StaticProvider("contract", 0, "CONTRACT\n", priority=10))
    briefing.register(StaticProvider("light", 2, "LIGHT\n", priority=20))
    briefing.register(StaticProvider("regime", 3, "REGIME-" + ("x" * 80) + "\n", priority=30))
    briefing.register(StaticProvider("reframe", 4, "REFRAME\n", priority=40))
    briefing.register(StaticProvider("sleeping", 5, "SLEEPING\n", priority=50))
    ctx = BriefingContext(
        project_dir=tmp,
        workspace_dir=tmp / "workspace",
        iter_index=1,
        rubric=rubric,
        stagnation_count=stagnation,
    )
    body = briefing.render(ctx)
    return body, getattr(briefing, "_last_render_diagnostics", {})


def run_fixture_regression() -> dict[str, object]:
    cases = []
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)

        body, diag = _render(tmp, stagnation=0, rubric={"briefing_budget_chars": 1000})
        cases.append({
            "case_id": "early_iter_renders_only_t0_to_t2",
            "passed": (
                "CONTRACT" in body
                and "LIGHT" in body
                and "REGIME" not in body
                and "REFRAME" not in body
                and "SLEEPING" not in body
                and "regime(T3)" in diag["tier_gated"]
                and "reframe(T4)" in diag["tier_gated"]
                and "sleeping(T5)" in diag["tier_gated"]
            ),
            "diag": diag,
        })

        body, diag = _render(tmp, stagnation=3, rubric={"briefing_budget_chars": 1000})
        cases.append({
            "case_id": "stagnation_opens_t3_but_not_t4_or_t5",
            "passed": (
                "REGIME" in body
                and "REFRAME" not in body
                and "SLEEPING" not in body
                and "reframe(T4)" in diag["tier_gated"]
                and "sleeping(T5)" in diag["tier_gated"]
            ),
            "diag": diag,
        })

        body, diag = _render(tmp, stagnation=3, rubric={"briefing_budget_chars": 20})
        cases.append({
            "case_id": "budget_trims_t3_without_dropping_t0_t2",
            "passed": (
                "CONTRACT" in body
                and "LIGHT" in body
                and "REGIME" not in body
                and any(item.startswith("regime(T3,") for item in diag["budget_trimmed"])
            ),
            "diag": diag,
        })

        body, diag = _render(
            tmp,
            stagnation=0,
            rubric={
                "briefing_budget_chars": 20,
                "briefing_force_show_sleeping": True,
                "briefing_tiered_disable": True,
            },
        )
        cases.append({
            "case_id": "tiering_disable_restores_legacy_all_provider_mode",
            "passed": (
                "REGIME" in body
                and "REFRAME" in body
                and "SLEEPING" in body
                and not diag["tier_gated"]
                and not diag["budget_trimmed"]
            ),
            "diag": diag,
        })

        audit = tmp / "workspace" / "mutator_briefing_iter_001.md"
        audit_text = audit.read_text(encoding="utf-8")
        cases.append({
            "case_id": "audit_records_timing_and_budget_diagnostics",
            "passed": (
                "Render ms:" in audit_text
                and "Provider timings ms:" in audit_text
                and "Tier-gated" in audit_text
                and "Budget-trimmed" in audit_text
            ),
            "audit_excerpt": audit_text.splitlines()[:8],
        })

    return {
        "suite": "mutator_briefing_fixture_regression",
        "all_passed": all(bool(c["passed"]) for c in cases),
        "num_cases": len(cases),
        "num_passed": sum(1 for c in cases if c["passed"]),
        "results": cases,
    }


def main() -> int:
    summary = run_fixture_regression()
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
