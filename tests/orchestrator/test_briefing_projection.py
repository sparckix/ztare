from __future__ import annotations

from pathlib import Path

from ztare.orchestrator.briefing_projection import build_projection_receipt
from ztare.orchestrator.mutator_briefing import (
    BriefingContext,
    BriefingProvider,
    MutatorBriefing,
)


class AuthorityProvider(BriefingProvider):
    name = "authority_fixture"
    priority = 10
    tier = 0

    def applies(self, ctx: BriefingContext) -> bool:
        return True

    def fragment(self, ctx: BriefingContext) -> str:
        return "## Fixture\nBEST FULL SURVIVOR abc123 workspace/winner.py\n"

    def structured_records(self, ctx: BriefingContext) -> list[dict]:
        return [
            {
                "source_type": "full_survivor",
                "source_ref": "workspace/winner.py",
                "sha": "abc123",
                "summary": "visible 12/12 holdout 10/10",
            }
        ]


def test_projection_receipt_passes_when_authority_anchor_survives() -> None:
    receipt = build_projection_receipt(
        body="BEST FULL SURVIVOR abc123 workspace/winner.py",
        records=[
            {
                "provider": "candidate_memory",
                "source_type": "full_survivor",
                "source_ref": "workspace/winner.py",
                "sha": "abc123",
            }
        ],
        iter_index=2,
    )

    assert receipt["status"] == "pass"
    assert receipt["authority_records"] == 1
    assert receipt["preserved"][0]["source_type"] == "full_survivor"
    assert receipt["missing"] == []


def test_projection_receipt_fails_on_missing_authority_or_demoted_baseline() -> None:
    receipt = build_projection_receipt(
        body="### Mandatory Patch Base\nUse weaker.py as the patch base.",
        records=[
            {
                "provider": "candidate_memory",
                "source_type": "full_survivor",
                "source_ref": "workspace/winner.py",
                "sha": "abc123",
            }
        ],
        iter_index=2,
    )

    assert receipt["status"] == "fail"
    assert "authority_artifact_missing" in receipt["failures"]
    assert "lower_authority_baseline_marker_present" in receipt["failures"]


def test_projection_receipt_treats_strategy_cards_as_authority_work_orders() -> None:
    receipt = build_projection_receipt(
        body="## Strategy Office Experiment Cards\nsha=cardabc; next_gate=probe:pass",
        records=[
            {
                "provider": "strategy_experiments",
                "source_type": "strategy_experiment",
                "source_ref": "workspace/strategy_experiments.jsonl",
                "failure_family_sha": "cardabc",
                "summary": "next_gate=probe:pass",
            }
        ],
        iter_index=3,
    )

    assert receipt["status"] == "pass"
    assert receipt["authority_records"] == 1
    assert receipt["preserved"][0]["source_type"] == "strategy_experiment"

    missing = build_projection_receipt(
        body="### Mandatory Patch Base\nuse base only",
        records=[
            {
                "provider": "strategy_experiments",
                "source_type": "strategy_experiment",
                "source_ref": "workspace/strategy_experiments.jsonl",
                "failure_family_sha": "cardabc",
                "summary": "next_gate=probe:pass",
            }
        ],
        iter_index=3,
    )

    assert missing["status"] == "fail"
    assert "authority_artifact_missing" in missing["failures"]


def test_mutator_briefing_persists_projection_receipt(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    briefing = MutatorBriefing(providers=[AuthorityProvider()])
    ctx = BriefingContext(
        project_dir=tmp_path,
        workspace_dir=ws,
        iter_index=7,
        rubric={"briefing_attention_agenda": False},
    )

    body = briefing.render(ctx)
    diagnostics = getattr(briefing, "_last_render_diagnostics")
    receipt = diagnostics["projection_receipt"]

    assert "BEST FULL SURVIVOR" in body
    assert receipt["status"] == "pass"
    assert (ws / "mutator_briefing_iter_007_projection_receipt.json").exists()
    assert (ws / "mutator_briefing_projection_latest.json").exists()
