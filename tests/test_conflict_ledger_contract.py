from __future__ import annotations

import json
from pathlib import Path

from ztare.common.conflict_ledger import ConflictLedger
from ztare.leanmill.solver.no_good_store import NoGoodStore
from ztare.orchestrator.briefing_providers.refuted_families import (
    RefutedFamiliesLedger,
    refresh_refuted_families_ledger,
)
from ztare.orchestrator.mutator_briefing import BriefingContext
from ztare.research_director.research_isomorphism import RefutedPatternsLedger


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_conflict_ledger_conformance_and_correspondence(tmp_path: Path) -> None:
    # leanmill no_good_store
    no_good_path = tmp_path / "solver_lane_no_good_store.jsonl"
    no_good = NoGoodStore(no_good_path)
    assert isinstance(no_good, ConflictLedger)
    clause = no_good.learn(
            {
                "statement": "theorem t : P := by sorry",
                "failure_class": "vacuous_closure",
                "witness_summary": "vacuous closure",
                "receipts_refs": ["receipt/a.json"],
                "source": "unit",
                "defeasible": True,
            }
        )
    assert no_good.blocks("theorem t : P := by sorry")
    assert clause.signature
    assert no_good.open_clauses()
    assert no_good.revive({"statement": "theorem t : P := by sorry", "failure_class": "other", "witness": "x"})
    assert json.loads(no_good_path.read_text(encoding="utf-8").splitlines()[0])["source"] == "unit"

    # research_isomorphism refuted_patterns
    refuted_path = tmp_path / "research_isomorphism_candidates.jsonl"
    _write_jsonl(
        refuted_path,
        [
            {"theorem": "T", "field": "F", "status": "live"},
            {"theorem": "T", "field": "F", "status": "refuted", "disposition_for": "T|F", "note": "pruned"},
        ],
    )
    refuted = RefutedPatternsLedger(refuted_path)
    assert isinstance(refuted, ConflictLedger)
    learned = refuted.learn({"theorem": "T", "field": "F", "status": "refuted", "note": "pruned"})
    assert learned.signature
    assert refuted.blocks(learned.signature)
    assert refuted.open_clauses()
    assert refuted.revive("evidence") == "evidence"
    assert "pruned" in refuted_path.read_text(encoding="utf-8")

    # worldmodel refuted_families
    project = tmp_path / "project"
    workspace = project / "workspace"
    _write_jsonl(
        workspace / "candidate_memory.json",
        [],
    )
    workspace.joinpath("candidate_memory.json").write_text(
        json.dumps(
            {
                "records": [
                    {
                        "source_type": "deterministic_near_miss",
                        "residual_class": "r",
                        "repair_class": "s",
                        "receipt_ref": "receipt/x.json",
                        "diagnosis": "blocked",
                    },
                    {
                        "source_type": "deterministic_near_miss",
                        "residual_class": "r",
                        "repair_class": "s",
                        "receipt_ref": "receipt/y.json",
                        "diagnosis": "exhausted",
                    },
                    {
                        "source_type": "deterministic_near_miss",
                        "residual_class": "r",
                        "repair_class": "s",
                        "receipt_ref": "receipt/z.json",
                        "diagnosis": "blocked",
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ctx = BriefingContext(project_dir=project, workspace_dir=workspace, iter_index=1, rubric={})
    rows = refresh_refuted_families_ledger(ctx)
    families = RefutedFamiliesLedger(ctx)
    assert isinstance(families, ConflictLedger)
    assert rows[0]["family_signature"] == "r x s"
    assert families.blocks("r x s")
    assert families.open_clauses()
    assert families.revive({"family_signature": "r x s"})["family_signature"] == "r x s"

    # worldmodel refuted_experiments (killed carrier_repair executions)
    from ztare.worldmodel.refuted_experiments import RefutedExperimentsLedger

    _write_jsonl(
        workspace / "strategy_experiment_executions.jsonl",
        [
            {"failure_family_sha": "sha-killed", "kind": "carrier_repair",
             "disposition": "killed", "outcome_sha256": "o1",
             "live_rows": [{"counterexample_trace": {"holdout_witness": {"t": 7}}}]},
            {"failure_family_sha": "sha-survived", "kind": "carrier_repair",
             "disposition": "survived", "outcome_sha256": "o2", "live_rows": []},
        ],
    )
    experiments = RefutedExperimentsLedger(project)
    assert isinstance(experiments, ConflictLedger)
    blocked = experiments.blocks("sha-killed")
    assert blocked and "7" in blocked.witness_summary
    assert experiments.blocks("sha-survived") is None  # only killed refutes
    assert experiments.blocked_signatures() == {"sha-killed"}
    assert experiments.revive("evidence") == "evidence"


def test_blocks_returns_none_when_nothing_matches(tmp_path: Path) -> None:
    no_good = NoGoodStore(tmp_path / "solver_lane_no_good_store.jsonl")
    assert no_good.blocks("theorem unseen : Q := by sorry") is None

    refuted = RefutedPatternsLedger(tmp_path / "missing_candidates.jsonl")
    assert refuted.blocks("anything") is None  # absent ledger: nothing refuted, by design
    assert refuted.open_clauses() == []

    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    ctx = BriefingContext(project_dir=project, workspace_dir=workspace, iter_index=1, rubric={})
    assert RefutedFamiliesLedger(ctx).blocks("never-refuted") is None


def test_corrupt_refuted_patterns_ledger_fails_closed(tmp_path: Path) -> None:
    from ztare.research_director.research_isomorphism import refuted_patterns
    from ztare.common.conflict_ledger import ConflictClause

    path = tmp_path / "research_isomorphism_candidates.jsonl"
    path.write_text("{this is not json\n", encoding="utf-8")
    led = RefutedPatternsLedger(path)

    clause = led.blocks("known-refuted-transport")
    assert isinstance(clause, ConflictClause)
    assert clause.signature == "known-refuted-transport"
    assert "unreadable" in clause.witness_summary

    opened = led.open_clauses()
    assert len(opened) == 1
    assert "unreadable" in opened[0].witness_summary

    sentinel = refuted_patterns(ledger=path)
    assert sentinel and "UNREADABLE" in sentinel[0]
    assert refuted_patterns(ledger=tmp_path / "absent.jsonl") == []


def test_unreadable_candidate_memory_fails_closed(tmp_path: Path) -> None:
    from ztare.common.conflict_ledger import ConflictClause

    project = tmp_path / "project"
    workspace = project / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "candidate_memory.json").write_text("{corrupt", encoding="utf-8")
    ctx = BriefingContext(project_dir=project, workspace_dir=workspace, iter_index=1, rubric={})
    families = RefutedFamiliesLedger(ctx)

    clause = families.blocks("r x s")
    assert isinstance(clause, ConflictClause)
    assert "unreadable" in clause.witness_summary

    opened = families.open_clauses()
    assert len(opened) == 1
    assert "unreadable" in opened[0].witness_summary
