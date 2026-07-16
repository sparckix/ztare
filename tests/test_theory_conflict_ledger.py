from __future__ import annotations

from itertools import combinations
import json

import pytest

from ztare.common.conflict_ledger import ConflictLedger
from ztare.leanmill.common import read_json
from ztare.leanmill.exploration_budget import ExplorationBudgetLedger, budget_preset
from ztare.leanmill.explore_axiom_space import (
    _freeze_theory_conflict_memory,
    _learn_navigation_conflicts,
    _refresh_theory_conflict_memory_after_wave,
)
from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_table_model_finder import find_finite_countermodel
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.frontier_blueprint import FrontierExplorationBrief
from ztare.leanmill.frontier_blueprint_compiler import compile_structure_first_blueprint
from ztare.leanmill.frontier_boundary import run_frontier_boundaries
from ztare.leanmill.magma_law_universe import (
    anonymous_magma_signature,
    magma_laws_through_order,
)
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal
from ztare.leanmill.theory_conflict_ledger import (
    TheoryConflictLedger,
    open_theory_conflict_ledger,
)
from ztare.leanmill.theory_interest import theory_residual_information_yield


def test_context_conflict_requires_and_replays_witness():
    valid = {("w1", "context-a"), ("w1", "context-b")}
    ledger = TheoryConflictLedger(
        context_hash="context-a",
        replay_witness=lambda payload, context: (payload.get("id"), context) in valid,
    )
    assert isinstance(ledger, ConflictLedger)
    clause = ledger.learn(
        {
            "candidate_signature": "pack:a+b",
            "context_hash": "context-a",
            "witness_ref": "model:1",
            "witness_payload": {"id": "w1"},
            "witness_summary": "model violates target consequence",
        }
    )
    assert ledger.blocks("pack:a+b") == clause
    assert ledger.revive({"context_hash": "context-b"})["retained"] == ["pack:a+b"]


def test_context_projection_drops_nonreplaying_clause_and_hides_sealed_payload():
    ledger = TheoryConflictLedger(
        context_hash="context-a",
        replay_witness=lambda payload, context: payload.get("context") == context,
    )
    ledger.learn(
        {
            "candidate_signature": "pack:x",
            "context_hash": "context-a",
            "witness_ref": "sealed:1",
            "witness_payload": {"context": "context-a", "secret": "hidden"},
            "sealed": True,
        }
    )
    assert "secret" not in str(ledger.navigator_rows())
    result = ledger.revive({"context_hash": "context-b"})
    assert result["dropped"] == ["pack:x"]
    assert ledger.blocks("pack:x") is None


def test_unwitnessed_or_wrong_context_conflict_is_rejected():
    ledger = TheoryConflictLedger(context_hash="a", replay_witness=lambda _p, _c: False)
    with pytest.raises(ValueError, match="does not replay"):
        ledger.learn(
            {
                "candidate_signature": "x",
                "context_hash": "a",
                "witness_ref": "w",
                "witness_payload": {"x": 1},
            }
        )


def test_context_conflicts_persist_and_replay_before_recall(tmp_path):
    path = tmp_path / "theory_conflicts.jsonl"
    replay = lambda payload, context: payload.get("context") == context
    first = TheoryConflictLedger(
        context_hash="context-a", replay_witness=replay, path=path
    )
    first.learn(
        {
            "candidate_signature": "pack:p+q",
            "context_hash": "context-a",
            "witness_ref": "model:7",
            "witness_payload": {
                "kind": "finite_countermodel",
                "context": "context-a",
                "secret_table": [1, 0],
            },
            "witness_summary": "finite model refutes the implication",
        }
    )

    reopened = TheoryConflictLedger(
        context_hash="context-a", replay_witness=replay, path=path
    )
    assert reopened.blocks("pack:p+q") is not None
    assert "secret_table" not in str(reopened.navigator_rows())
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1

    other = TheoryConflictLedger(
        context_hash="context-b", replay_witness=replay, path=path
    )
    assert other.blocks("pack:p+q") is None


def test_corrupt_persistent_conflict_refuses_replay(tmp_path):
    path = tmp_path / "theory_conflicts.jsonl"
    path.write_text(
        json.dumps(
            {
                "schema": "leanmill.theory_conflict.v1",
                "record_sha256": "sha256:wrong",
                "candidate_signature": "pack:x",
                "context_hash": "a",
                "witness_ref": "w",
                "witness_payload": {"id": 1},
                "witness_summary": "x",
                "sealed": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="digest mismatch"):
        TheoryConflictLedger(
            context_hash="a", replay_witness=lambda _payload, _context: True, path=path
        )


def test_agent_refusal_becomes_visible_only_after_completed_wave(tmp_path):
    signature = anonymous_magma_signature()
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in magma_laws_through_order(2)),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )
    formulas = next(
        row
        for row in combinations(context.formula_ids, 2)
        if not (
            signal := theory_residual_information_yield(context, row)
        ).residual_consequence_ids
        and not signal.cheap_baseline_inconclusive_ids
        and signal.coordinates.identification_bits == 0
    )
    directory = tmp_path / "attempt"
    directory.mkdir()
    ledger, visible = _freeze_theory_conflict_memory(context, directory, epoch=0)
    assert visible == ()
    signal = theory_residual_information_yield(context, formulas)
    navigation = {
        "search_wave": 0,
        "trace": [
            {
                "decision": "candidate_rejected",
                "rejection": {
                    "reason": "agent_refused_theory_program",
                    "formula_ids": list(formulas),
                    "selection_receipt_id": "selection:agent-refusal",
                    "residual_yield": signal.coordinates.to_json(),
                },
            }
        ],
    }
    journal = TheoryCampaignJournal(directory / "events.jsonl")

    assert _learn_navigation_conflicts(
        context,
        navigation,
        ledger,
        journal,
        attempt_id="attempt",
        campaign_id="campaign",
        epoch=0,
    ) == 1
    assert read_json(
        directory / "theory_conflict_memory.epoch-000.json", {}
    )["conflict_count"] == 0

    _refresh_theory_conflict_memory_after_wave(
        context, directory, ledger, epoch=0, search_wave=0
    )
    refreshed = read_json(directory / "theory_conflict_memory.epoch-000.json", {})
    assert refreshed["conflict_count"] == 1
    assert refreshed["search_wave"] == 1
    assert len(list(directory.glob("*.before-wave-001.*.json"))) == 1


def test_replayed_finite_countermodel_skips_boundary_spend_across_attempts(tmp_path):
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(1)
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )
    draft = {
        "mode": "anonymous_signature_census",
        "eigenquestion": "Which implication survives a larger carrier?",
        "signature": signature.to_json(),
        "primitive_semantics": {
            "operation_bindings": {"op0": "finite table"},
            "relation_bindings": {},
        },
        "base_axioms": (),
        "base_theory_status": "explicit_empty",
        "adapter_id": "magma_equational.v1",
        "adapter_config": {"max_total_operation_order": 1},
        "formula_grammar": {"max_order": 1},
        "model_or_observation_strata": ({"carrier_size": 2},),
        "pack_arity": 1,
        "collapse_controls": (),
        "visible_evidence_manifest": {},
        "sealed_evidence_manifest_digest": "sha256:" + "0" * 64,
        "deanchoring_policy": {"cold": True},
        "navigator_contract": {},
        "query_budget": {"larger_model_queries": 1},
        "stop_rule": {},
        "verification_plan": {
            "larger_carriers": [2],
            "conditional_lean": False,
            "smt_timeout_ms": 1_000,
        },
        "codec_versions": {},
        "authority_refs": ("authority",),
    }
    blueprint = compile_structure_first_blueprint(
        FrontierExplorationBrief(direction="Explore.", source_mode="structure_first"),
        draft,
    )
    premise, target = laws[0], laws[1]
    navigation = {
        "finalists": [
            {
                "formula_ids": [premise.formula_id],
                "residual_joint_only_consequence_ids": [target.formula_id],
            }
        ]
    }
    shared = tmp_path / "theory_conflicts.jsonl"
    first_budget = ExplorationBudgetLedger(
        tmp_path / "first.budget.jsonl",
        budget_preset("smoke_20m"),
        attempt_id="attempt-first",
    )
    first = run_frontier_boundaries(
        context,
        blueprint,
        navigation,
        TheoryCampaignJournal(tmp_path / "first.events.jsonl"),
        first_budget,
        attempt_id="attempt-first",
        campaign_id="campaign-test",
        countermodel_fn=lambda premises, target_axiom, **kwargs: find_finite_countermodel(
            signature, premises, target_axiom, **kwargs
        ),
        conflict_ledger=open_theory_conflict_ledger(context, shared),
    )
    assert first.query_results[0]["pack_synergy_status"] == "refuted_by_larger_model"
    assert shared.is_file()
    visible_conflict = open_theory_conflict_ledger(context, shared).navigator_rows()[0]
    assert visible_conflict["premise_formula_ids"] == [premise.formula_id]
    assert visible_conflict["target_formula_id"] == target.formula_id
    assert "witness_payload" not in visible_conflict

    second_budget = ExplorationBudgetLedger(
        tmp_path / "second.budget.jsonl",
        budget_preset("smoke_20m"),
        attempt_id="attempt-second",
    )
    second = run_frontier_boundaries(
        context,
        blueprint,
        navigation,
        TheoryCampaignJournal(tmp_path / "second.events.jsonl"),
        second_budget,
        attempt_id="attempt-second",
        campaign_id="campaign-test",
        countermodel_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("replayed countermodel must skip SMT")
        ),
        conflict_ledger=open_theory_conflict_ledger(context, shared),
    )
    row = second.query_results[0]
    assert row["pack_synergy_status"] == "refuted_by_replayed_countermodel"
    assert row["lean"]["status"] == "skipped_replayed_countermodel"
    assert second_budget.state()["usage"]["boundary_queries"] == 0
    assert second_budget.state()["usage"]["smt_calls"] == 0
