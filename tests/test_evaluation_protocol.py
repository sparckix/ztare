"""Tests for ztare.worldmodel.evaluation_protocol (cold-review findings 2/3/5)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ztare.worldmodel.evaluation_protocol import (
    assert_untainted_chooser,
    eval_plan,
    is_tainted,
    mark_taint,
    record_attempt,
    register_evaluation,
    reserve_audit_slice,
    validate_slice,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _ledger_rows(project_dir, filename="eval_protocol.jsonl"):
    p = Path(project_dir) / "workspace" / filename
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


# ---------------------------------------------------------------------------
# Finding 2: budget + attempt recording
# ---------------------------------------------------------------------------

def test_register_succeeds_within_budget(tmp_path):
    row = register_evaluation(tmp_path, "sha-001", lineage_id="lin-A", budget=3)
    assert row["status"] == "registered"
    assert row["attempts_used"] == 0


def test_budget_refusal_after_n_attempts(tmp_path):
    # Use up budget=2 via record_attempt
    register_evaluation(tmp_path, "sha-001", lineage_id="lin-B", budget=2)
    record_attempt(tmp_path, "sha-001", lineage_id="lin-B", slice_ref="s1", outcome="fail", stopping_rule="any")
    record_attempt(tmp_path, "sha-001", lineage_id="lin-B", slice_ref="s2", outcome="fail", stopping_rule="any")
    # Now register a second candidate — should be refused
    refused = register_evaluation(tmp_path, "sha-002", lineage_id="lin-B", budget=2)
    assert refused["status"] == "refused_budget_exhausted"


def test_refused_row_written_to_ledger(tmp_path):
    register_evaluation(tmp_path, "sha-X", lineage_id="lin-C", budget=0)
    rows = _ledger_rows(tmp_path)
    assert any(r["status"] == "refused_budget_exhausted" for r in rows)


def test_every_attempt_recorded_including_failures(tmp_path):
    register_evaluation(tmp_path, "sha-A", lineage_id="lin-D", budget=5)
    record_attempt(tmp_path, "sha-A", lineage_id="lin-D", slice_ref="s1", outcome="fail", stopping_rule="r1")
    record_attempt(tmp_path, "sha-A", lineage_id="lin-D", slice_ref="s2", outcome="pass", stopping_rule="r2")
    attempts = [r for r in _ledger_rows(tmp_path) if r.get("record_type") == "attempt"]
    assert len(attempts) == 2
    outcomes = {r["outcome"] for r in attempts}
    assert outcomes == {"fail", "pass"}


def test_attempt_row_joins_candidate_hash_slice_outcome_stopping_rule(tmp_path):
    register_evaluation(tmp_path, "sha-Z", lineage_id="lin-E", budget=5)
    record_attempt(
        tmp_path, "sha-Z", lineage_id="lin-E",
        slice_ref="probe-slice-7", outcome="pass", stopping_rule="holdout_depth_eq_total"
    )
    attempts = [r for r in _ledger_rows(tmp_path) if r.get("record_type") == "attempt"]
    assert len(attempts) == 1
    a = attempts[0]
    assert a["candidate_sha"] == "sha-Z"
    assert a["slice_ref"] == "probe-slice-7"
    assert a["outcome"] == "pass"
    assert a["stopping_rule"] == "holdout_depth_eq_total"


# ---------------------------------------------------------------------------
# Audit slice reserve + refusal
# ---------------------------------------------------------------------------

def test_reserve_audit_slice_marks_as_reserved(tmp_path):
    reserve_audit_slice(tmp_path, "slice-audit-1")
    rows = _ledger_rows(tmp_path, "audit_slices.jsonl")
    assert any(r.get("slice_ref") == "slice-audit-1" for r in rows)


def test_attempt_against_reserved_slice_is_refused(tmp_path):
    reserve_audit_slice(tmp_path, "slice-reserved")
    register_evaluation(tmp_path, "sha-R", lineage_id="lin-F", budget=5)
    result = record_attempt(
        tmp_path, "sha-R", lineage_id="lin-F",
        slice_ref="slice-reserved", outcome="pass", stopping_rule="any"
    )
    assert result["status"] == "refused_reserved_slice"


def test_refused_reserved_slice_still_written_to_ledger(tmp_path):
    reserve_audit_slice(tmp_path, "slice-locked")
    register_evaluation(tmp_path, "sha-Q", lineage_id="lin-G", budget=5)
    record_attempt(
        tmp_path, "sha-Q", lineage_id="lin-G",
        slice_ref="slice-locked", outcome="fail", stopping_rule="any"
    )
    attempts = [r for r in _ledger_rows(tmp_path) if r.get("record_type") == "attempt"]
    assert len(attempts) == 1
    assert attempts[0]["status"] == "refused_reserved_slice"


# ---------------------------------------------------------------------------
# Finding 3: eval plan + validate_slice
# ---------------------------------------------------------------------------

def test_eval_plan_returns_required_interventions(tmp_path):
    # Seed a disagreements file with unresolved targets
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "version_space_disagreements.jsonl").write_text(
        json.dumps({
            "schema": "ztare.vs_disagreements.v1",
            "required_probe_targets": ["probe-A", "probe-B"],
        }) + "\n"
    )
    plan = eval_plan(tmp_path, "lin-H")
    assert set(plan["required_interventions"]) == {"probe-A", "probe-B"}


def test_eval_plan_excludes_resolved_rows(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "version_space_disagreements.jsonl").write_text(
        json.dumps({"required_probe_targets": ["probe-C"], "resolved": True}) + "\n" +
        json.dumps({"required_probe_targets": ["probe-D"]}) + "\n"
    )
    plan = eval_plan(tmp_path, "lin-I")
    assert "probe-C" not in plan["required_interventions"]
    assert "probe-D" in plan["required_interventions"]


def test_validate_slice_fails_when_interventions_missing(tmp_path):
    plan = {"required_interventions": ["probe-X", "probe-Y"]}
    slice_rows = [{"probe_target_id": "probe-X"}]  # probe-Y missing
    result = validate_slice(slice_rows, plan)
    assert result["valid"] is False
    assert "probe-Y" in result["missing_interventions"]


def test_validate_slice_passes_when_all_present(tmp_path):
    plan = {"required_interventions": ["probe-X", "probe-Y"]}
    slice_rows = [
        {"probe_target_id": "probe-X"},
        {"intervention_id": "probe-Y"},
    ]
    result = validate_slice(slice_rows, plan)
    assert result["valid"] is True
    assert result["missing_interventions"] == []


def test_validate_slice_passes_with_empty_requirements(tmp_path):
    plan = {"required_interventions": []}
    result = validate_slice([], plan)
    assert result["valid"] is True


# ---------------------------------------------------------------------------
# Finding 5: taint lineage
# ---------------------------------------------------------------------------

def test_mark_taint_and_is_tainted_direct(tmp_path):
    mark_taint(tmp_path, "sha-tainted", source="holdout_conditioned")
    assert is_tainted(tmp_path, "sha-tainted") is True


def test_untainted_sha_is_not_tainted(tmp_path):
    mark_taint(tmp_path, "sha-tainted", source="holdout_conditioned")
    assert is_tainted(tmp_path, "sha-clean") is False


def test_taint_propagation_through_parents(tmp_path):
    mark_taint(tmp_path, "sha-root", source="holdout_conditioned")
    mark_taint(tmp_path, "sha-child", source="derived", parents=["sha-root"])
    mark_taint(tmp_path, "sha-grandchild", source="derived", parents=["sha-child"])
    assert is_tainted(tmp_path, "sha-grandchild") is True


def test_taint_does_not_propagate_to_unrelated(tmp_path):
    mark_taint(tmp_path, "sha-evil", source="holdout_conditioned")
    # sha-sibling shares no lineage
    assert is_tainted(tmp_path, "sha-sibling") is False


def test_assert_untainted_chooser_passes_for_clean(tmp_path):
    # Should not raise
    assert_untainted_chooser(tmp_path, "chooser-clean")


def test_assert_untainted_chooser_raises_for_tainted(tmp_path):
    mark_taint(tmp_path, "chooser-bad", source="holdout_conditioned")
    with pytest.raises(AssertionError, match="Tainted chooser"):
        assert_untainted_chooser(tmp_path, "chooser-bad")


def test_assert_untainted_chooser_raises_for_tainted_via_parent(tmp_path):
    mark_taint(tmp_path, "sha-bad-root", source="holdout_conditioned")
    mark_taint(tmp_path, "chooser-derived", source="derived", parents=["sha-bad-root"])
    with pytest.raises(AssertionError):
        assert_untainted_chooser(tmp_path, "chooser-derived")


# ---------------------------------------------------------------------------
# FIX D: validate_slice accepts target_id as primary key (real schema rows)
# ---------------------------------------------------------------------------

def test_validate_slice_passes_with_target_id(tmp_path):
    """Real-schema rows use target_id; validate_slice must accept it."""
    plan = {"required_interventions": ["probe-A", "probe-B"]}
    slice_rows = [
        {"target_id": "probe-A"},   # real executor schema
        {"target_id": "probe-B"},
    ]
    result = validate_slice(slice_rows, plan)
    assert result["valid"] is True
    assert result["missing_interventions"] == []


def test_validate_slice_target_id_takes_priority_over_legacy(tmp_path):
    """target_id preferred; mixed schema rows still covered."""
    plan = {"required_interventions": ["probe-X", "probe-Y", "probe-Z"]}
    slice_rows = [
        {"target_id": "probe-X"},            # real schema
        {"probe_target_id": "probe-Y"},      # legacy name 1
        {"intervention_id": "probe-Z"},      # legacy name 2
    ]
    result = validate_slice(slice_rows, plan)
    assert result["valid"] is True
    assert result["missing_interventions"] == []


def test_validate_slice_missing_when_only_wrong_key(tmp_path):
    """Rows with no matching key → interventions missing."""
    plan = {"required_interventions": ["probe-M"]}
    slice_rows = [{"some_other_field": "probe-M"}]
    result = validate_slice(slice_rows, plan)
    assert result["valid"] is False
    assert "probe-M" in result["missing_interventions"]
