from __future__ import annotations

import json
from pathlib import Path

from ztare.orchestrator.briefing_providers.refuted_families import (
    RefutedFamiliesProvider,
    refresh_refuted_families_ledger,
)
from ztare.orchestrator.mutator_briefing import BriefingContext


def _write_candidate_memory(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"records": records}, indent=2) + "\n", encoding="utf-8")


def test_exhaustion_diagnosis_writes_refuted_family_ledger(tmp_path: Path) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    _write_candidate_memory(
        workspace / "candidate_memory.json",
        [
            {
                "source_type": "deterministic_near_miss",
                "target_residual_class": "replay_mismatch_quotient",
                "repair_class": "action_independent_cell_rewrite",
                "receipt_ref": "workspace/visible_cli_receipts/a.json",
                "diagnosis": "blocked",
            },
            {
                "source_type": "deterministic_near_miss",
                "residual_class": "replay_mismatch_quotient",
                "repair_shape": "action_independent_cell_rewrite",
                "source_ref": "workspace/visible_cli_receipts/b.json",
                "diagnosis": "exhausted",
            },
            {
                "source_type": "full_survivor",
                "residual_class": "other",
                "repair_shape": "different_strategy",
                "receipt_path": "workspace/visible_cli_receipts/c.json",
                "outcome": "pass",
            },
        ],
    )
    ctx = BriefingContext(project_dir=project, workspace_dir=workspace, iter_index=7, rubric={})

    families = refresh_refuted_families_ledger(ctx)

    ledger_path = workspace / "refuted_families.jsonl"
    assert ledger_path.exists()
    assert families[0]["family_signature"] == "replay_mismatch_quotient x action_independent_cell_rewrite"
    assert families[0]["receipts_refs"] == [
        "workspace/visible_cli_receipts/a.json",
        "workspace/visible_cli_receipts/b.json",
    ]
    assert "blocked:1" in families[0]["witness_summary"]
    assert "exhausted:1" in families[0]["witness_summary"]


def test_refuted_families_render_and_revival_card(tmp_path: Path) -> None:
    project = tmp_path / "project"
    workspace = project / "workspace"
    _write_candidate_memory(
        workspace / "candidate_memory.json",
        [
            {
                "source_type": "deterministic_near_miss",
                "residual_class": "replay_mismatch_quotient",
                "repair_class": "action_independent_cell_rewrite",
                "receipt_ref": "workspace/visible_cli_receipts/a.json",
                "diagnosis": "blocked",
            },
            {
                "source_type": "deterministic_near_miss",
                "residual_class": "replay_mismatch_quotient",
                "repair_class": "action_independent_cell_rewrite",
                "receipt_ref": "workspace/visible_cli_receipts/b.json",
                "diagnosis": "blocked",
            },
            {
                "source_type": "deterministic_near_miss",
                "residual_class": "replay_mismatch_quotient",
                "repair_class": "action_independent_cell_rewrite",
                "receipt_ref": "workspace/visible_cli_receipts/c.json",
                "diagnosis": "exhausted",
            },
        ],
    )
    ctx = BriefingContext(project_dir=project, workspace_dir=workspace, iter_index=7, rubric={})
    provider = RefutedFamiliesProvider()

    assert provider.applies(ctx) is True
    fragment = provider.fragment(ctx)
    records = provider.structured_records(ctx)

    assert "## Refuted Families" in fragment
    assert "novelty must leave this class" in fragment
    assert records[0]["family_signature"] == "replay_mismatch_quotient x action_independent_cell_rewrite"

    (workspace / "candidate_memory.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "source_type": "full_survivor",
                        "residual_class": "replay_mismatch_quotient",
                        "repair_class": "action_independent_cell_rewrite",
                        "receipt_ref": "workspace/visible_cli_receipts/new.json",
                        "diagnosis": "card cites new evidence class",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    refresh_refuted_families_ledger(ctx)
    assert provider.applies(ctx) is False


def test_unreadable_candidate_memory_skips_persist_and_banners(tmp_path: Path) -> None:
    import pytest

    from ztare.orchestrator.briefing_providers.refuted_families import (
        LedgerSourceUnreadable,
        RefutedFamiliesProvider,
    )

    project = tmp_path / "project"
    workspace = project / "workspace"

    # seed a real ledger from readable memory
    _write_candidate_memory(
        workspace / "candidate_memory.json",
        [
            {
                "source_type": "deterministic_near_miss",
                "residual_class": "r",
                "repair_class": "s",
                "receipt_ref": "workspace/visible_cli_receipts/a.json",
                "diagnosis": "blocked",
            }
            for _ in range(3)
        ],
    )
    ctx = BriefingContext(project_dir=project, workspace_dir=workspace, iter_index=1, rubric={})
    refresh_refuted_families_ledger(ctx)
    ledger_path = workspace / "refuted_families.jsonl"
    before = ledger_path.read_text(encoding="utf-8")
    assert before.strip()

    # transient corruption of the source must NOT rewrite the ledger
    (workspace / "candidate_memory.json").write_text("{corrupt", encoding="utf-8")
    with pytest.raises(LedgerSourceUnreadable):
        refresh_refuted_families_ledger(ctx)
    assert ledger_path.read_text(encoding="utf-8") == before

    # the existing ledger still serves the section (prior refutations in force)
    provider = RefutedFamiliesProvider()
    assert provider.applies(ctx) is True
    assert "## Refuted Families" in provider.fragment(ctx)

    # with no persisted ledger either, the section renders the UNREADABLE banner
    ledger_path.unlink()
    assert provider.applies(ctx) is True
    fragment = provider.fragment(ctx)
    assert "REFUTED FAMILIES UNREADABLE" in fragment
    assert "prior refutations still in force" in fragment
    records = provider.structured_records(ctx)
    assert records and records[0]["prior_refutations_still_in_force"] is True
