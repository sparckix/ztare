#!/usr/bin/env python3
"""Compact operator contracts for LeanMill worker lanes.

The epistemic-generation H34-H55 result is that labels and long prompts are
weak execution carriers. A worker should receive a compact checked contract:
accepted class, source-cue status, action program, current instruction pointer,
required next action, and deterministic stop/repair rules.
"""
from __future__ import annotations

import json
from typing import Any

import leanmill_action_card_contract as action_cards


C_SUPPLY_CLASS = "c_supply_template_backfill"
FAMILY_BIRTH_CLASS = "family_birth_candidate"
C_SUPPLY_ACTION_PROGRAM = [
    "inspect_source_declarations",
    "construct_positive_from_smaller_helpers",
    "construct_matched_negative_control",
    "edit_target_family_yaml_only",
    "emit_terminal_json",
]
C_SUPPLY_ANTI_PATTERN_ACTION_PROGRAM = [
    "check_no_placeholder_holes",
    "check_target_self_reference",
    "check_positive_negative_pair_substance",
    "check_source_specific_confusers",
    "proceed_to_yaml_edit_or_operator_required",
]
FAMILY_BIRTH_ACTION_PROGRAM = [
    "inspect_cluster_source_declarations",
    "infer_reusable_residual_signature",
    "construct_cluster_positive_negative_pairs",
    "edit_new_family_yaml_only",
    "emit_terminal_json",
]
FAMILY_BIRTH_ANTI_PATTERN_ACTION_PROGRAM = [
    "check_cluster_is_not_single_row_or_token_accident",
    "check_no_placeholder_holes",
    "check_target_self_reference",
    "check_positive_negative_pair_substance",
    "proceed_to_candidate_yaml_or_retire",
]


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _parse_int(value: Any) -> tuple[bool, int]:
    try:
        return True, int(value)
    except (TypeError, ValueError):
        return False, 0


def _norm_route(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def c_supply_template_backfill_contract(
    *,
    family: str,
    candidate_rows: list[dict[str, Any]],
    target_path: str,
    source_demand: dict[str, Any],
    contract_id: str,
) -> dict[str, Any]:
    """Build the compact contract for a C-supply template conversion task."""
    cue_failures: list[dict[str, Any]] = []
    candidates = []
    for row in candidate_rows:
        row_id = str(row.get("row_id") or "")
        source_file = str(row.get("source_file") or "")
        target_theorem_name = str(row.get("target_theorem_name") or "")
        if not row_id:
            cue_failures.append({"failure": "candidate_missing_row_id"})
        if not source_file:
            cue_failures.append({"failure": "candidate_missing_source_file", "row_id": row_id})
        if not target_theorem_name:
            cue_failures.append({"failure": "candidate_missing_target_theorem_name", "row_id": row_id})
        candidates.append({
            "row_id": row_id,
            "source_file": source_file,
            "target_theorem_name": target_theorem_name,
            "matched_features": list(row.get("matched_features") or []),
            "template_design_rows": list(row.get("template_design_rows") or []),
            "static_exit": str(row.get("static_exit") or ""),
        })
    return {
        "schema": "leanmill-operator-contract-v1",
        "contract_id": contract_id,
        "accepted_residual_class": C_SUPPLY_CLASS,
        "source_cue_check_status": "pass" if not cue_failures else "fail",
        "source_cue_failures": cue_failures,
        "target_family": family,
        "target_path": target_path,
        "candidate_rows": candidates,
        "source_demand": {
            "family": str(source_demand.get("family") or ""),
            "recommended_action": str(source_demand.get("recommended_action") or ""),
            "source_query_intent": str(source_demand.get("source_query_intent") or ""),
            "recent_probe_feedback": list(source_demand.get("recent_probe_feedback") or []),
        },
        "path_c_memory_action_card": {
            "schema": "leanmill-path-c-memory-action-card-v1",
            "memory_unit": "repair_family_templates",
            "family": family,
            "candidate_row_count": len(candidates),
            "matched_features_by_row": {
                str(row.get("row_id") or ""): list(row.get("matched_features") or [])
                for row in candidate_rows
                if str(row.get("row_id") or "")
            },
            "template_design_rows_by_row": {
                str(row.get("row_id") or ""): list(row.get("template_design_rows") or [])
                for row in candidate_rows
                if str(row.get("row_id") or "")
            },
            "required_use": [
                "infer the reusable family-specific bridge from existing family templates before editing",
                "compile the bridge into one positive template and one matched negative_control for a candidate row",
                "make the negative_control test the same family ingredient rather than syntax failure",
                "emit operator_required only after the action_program attempts have concrete failed routes",
            ],
            "forbidden_shortcuts": [
                "calling the candidate target theorem",
                "copying a positive body into the negative_control",
                "using static failure as proof value",
                "editing any non-target artifact",
            ],
        },
        "anti_pattern_action_card": action_cards.build_action_card(
            card_type="c_supply_template_backfill_guard",
            failure_family="c_supply_template_laundering",
            preventive_gate="family_template_pair_substance_gate",
            missing_or_paid_preventive_receipt="positive_negative_substance_receipt",
            source_specific_false_reading_confuser=[
                "static no-signal plus family match means proof value",
                "a negative_control that fails from malformed syntax is a valid canary",
                "a source theorem with the same target name is a helper rather than the target itself",
                "a template containing a placeholder hole is a bounded route attempt rather than a candidate",
                "a positive/negative pair whose negative fails from syntax or elaboration shape is a valid matched canary",
            ],
            nearest_confuser_rejection=[
                "eligibility is not closure",
                "syntax failure is not family-ingredient failure",
                "self-reference is not source reuse",
                "a placeholder hole is not partial proof value",
                "Lean syntax/elaboration failure is not matched negative-control evidence",
            ],
            clean_proceed_condition=(
                "Proceed only when the candidate row has a positive template, a matched negative_control "
                "that removes or reverses the family-specific ingredient and fails for that ingredient rather than syntax, "
                "no placeholder holes, no target-theorem self-reference, and strict C-slice conversion can recognize the row."
            ),
            action_program=C_SUPPLY_ANTI_PATTERN_ACTION_PROGRAM,
            program_counter_rule="pay each preventive check before editing; on failure emit operator_required with attempted_routes and blocked_edge",
            evidence_basis="epistemic-generation V70/V72/H20/H25-H30: use residual-to-check/card IR, confuser rejection, preventive receipt, feedback trace, and program-counter checks",
        ),
        "action_program": list(C_SUPPLY_ACTION_PROGRAM),
        "current_action_index": 0,
        "required_next_action": C_SUPPLY_ACTION_PROGRAM[0],
        "program_counter_rule": "execute actions in order; do not skip directly to operator_required before bounded route attempts",
        "entry_conditions": [
            "public/static tools produced tested_no_positive_signal",
            "the row has a repair-family signature match with existing negative-control style",
            "target theorem name is known or inferred from the source declaration",
            "the target family YAML is the only edit scope",
        ],
        "required_evidence": [
            "source declaration for each candidate row",
            "the inferred target theorem name for each candidate row",
            "positive template built from smaller proven helpers or explicit construction",
            "matched negative-control template that removes or reverses the family-specific ingredient",
            "terminal JSON with changed_paths and validation_command when editing",
        ],
        "failure_conditions": [
            "positive template calls the target theorem being converted",
            "positive or negative template contains a placeholder hole",
            "negative control fails only because it is malformed, notation-invalid, or under-applied",
            "edit touches non-target YAML, Python, registry, scoreboard, or research log",
            "row lacks target theorem/source cues needed to audit self-reference",
        ],
        "revision_rules": [
            "if the candidate proof calls the target theorem, reject it and search for smaller source-local helpers",
            "if one helper route fails, try a second distinct bridge before terminal operator_required",
            "if no clean positive+negative pair is found, emit operator_required with attempted_routes and blocked_edge",
        ],
        "min_non_tautological_routes_before_operator_required": 2,
        "scope_boundary": "no proof credit; only the target repair-family YAML may change, and governance/probe lanes decide value later",
        "nearest_confuser_disambiguators": [
            "sibling theorem with the same target name is not a helper",
            "static no-signal row is not a closure",
            "family match is eligibility, not evidence of proof value",
            "negative control must test the family ingredient, not Lean syntax/elaboration failure",
            "placeholder holes are route failures, not YAML candidates",
        ],
    }


def family_birth_candidate_contract(
    *,
    family: str,
    cluster_rows: list[dict[str, Any]],
    target_path: str,
    cluster: dict[str, Any],
    contract_id: str,
) -> dict[str, Any]:
    """Build the compact contract for a new repair-family candidate task."""
    cue_failures: list[dict[str, Any]] = []
    rows = []
    for row in cluster_rows:
        row_id = str(row.get("row_id") or "")
        source_file = str(row.get("source_file") or "")
        target_theorem_name = str(row.get("target_theorem_name") or "")
        if not row_id:
            cue_failures.append({"failure": "candidate_missing_row_id"})
        if not source_file:
            cue_failures.append({"failure": "candidate_missing_source_file", "row_id": row_id})
        rows.append({
            "row_id": row_id,
            "source_file": source_file,
            "target_theorem_name": target_theorem_name,
            "token_hits": list(row.get("token_hits") or []),
        })
    signature_tokens = [str(x) for x in (cluster.get("signature_tokens") or []) if str(x)]
    min_rows = int((cluster.get("required_birth_receipt") or {}).get("min_rows") or 3)
    return {
        "schema": "leanmill-operator-contract-v1",
        "contract_id": contract_id,
        "accepted_residual_class": FAMILY_BIRTH_CLASS,
        "source_cue_check_status": "pass" if not cue_failures else "fail",
        "source_cue_failures": cue_failures,
        "target_family": family,
        "target_path": target_path,
        "candidate_rows": rows,
        "family_birth_cluster": {
            "proposed_family": str(cluster.get("proposed_family") or family),
            "signature_tokens": signature_tokens,
            "row_count": int(cluster.get("row_count") or len(rows)),
            "min_rows": min_rows,
        },
        "path_c_memory_action_card": {
            "schema": "leanmill-path-c-memory-action-card-v1",
            "memory_unit": "repair_family_birth",
            "family": family,
            "candidate_row_count": len(rows),
            "signature_tokens": signature_tokens,
            "required_use": [
                "infer a reusable residual signature shared by multiple cluster rows",
                "compile the signature into positive templates and matched negative controls",
                "mark the new spec seed_only or candidate_family with source and clean-solver credit false",
                "retire rather than create a one-row or token-accident family",
            ],
            "forbidden_shortcuts": [
                "creating a family from a single row",
                "calling the candidate target theorem",
                "using static failure as proof value",
                "creating negative controls that fail only by malformed syntax",
                "editing any artifact other than the target YAML",
            ],
        },
        "anti_pattern_action_card": action_cards.build_action_card(
            card_type="family_birth_candidate_guard",
            failure_family="family_birth_overfit_or_laundering",
            preventive_gate="family_birth_pair_and_scope_gate",
            missing_or_paid_preventive_receipt="cluster_positive_negative_substance_receipt",
            source_specific_false_reading_confuser=[
                "shared tokens alone define a reusable family",
                "static no-signal is proof value",
                "a new YAML file is a promoted family",
                "a syntax-failing negative control is a matched canary",
            ],
            nearest_confuser_rejection=[
                "cluster membership is hypothesis, not credit",
                "candidate_family is not validated_family",
                "source failure is not family evidence",
                "template quantity is not useful outcome",
            ],
            clean_proceed_condition=(
                "Proceed only if at least the required number of cluster rows receive clean positive "
                "and matched negative-control templates under one reusable residual signature."
            ),
            action_program=FAMILY_BIRTH_ANTI_PATTERN_ACTION_PROGRAM,
            program_counter_rule="pay the cluster/scope/pair checks before writing YAML; retire if the cluster is weak",
            evidence_basis="LeanMill Path-C supply RCA: new-family birth must convert repeated strict-static failures into governed candidate memory without proof credit.",
        ),
        "action_program": list(FAMILY_BIRTH_ACTION_PROGRAM),
        "current_action_index": 0,
        "required_next_action": FAMILY_BIRTH_ACTION_PROGRAM[0],
        "program_counter_rule": "execute actions in order; do not skip directly to operator_required before inspecting cluster evidence",
        "entry_conditions": [
            "public/static tools produced tested_no_positive_signal for candidate rows",
            "existing repair-family match is absent or below policy threshold",
            "cluster rows share distinctive source/declaration signals",
            "the target family YAML is the only edit scope",
        ],
        "required_evidence": [
            "source declaration for each included row",
            "the reusable signature tying the rows together",
            "positive template and matched negative_control for each included row, encoded as top-level templates[] entries",
            "integer version and explicit no-credit boundary",
            "terminal JSON with changed_paths and validation_command when editing",
        ],
        "family_spec_yaml_schema_contract": {
            "required_top_level_keys": ["family", "version", "status", "credit", "residual_match", "templates"],
            "version_must_be_integer": True,
            "credit_required": {
                "source_credit_eligible": False,
                "clean_solver_credit_eligible": False,
            },
            "templates_shape": "top_level_list_not_nested_rows",
            "row_pair_rule": "each included row must have one templates[] item with test_kind=positive and one with test_kind=negative_control",
            "exemplar_instruction": "inspect existing repair_families/*.yaml and mirror that schema before editing",
            "validation_command_required": "scripts/public/control/leanmill/family_spec_gate.py",
        },
        "failure_conditions": [
            "cluster has fewer rows than the required birth threshold",
            "YAML uses nested rows as the template carrier instead of top-level templates[]",
            "YAML lacks integer version or explicit credit false/false boundary",
            "positive template calls the target theorem being converted",
            "positive or negative template contains a placeholder hole",
            "negative control fails only because it is malformed, notation-invalid, or under-applied",
            "edit touches non-target YAML, Python, registry, scoreboard, or research log",
        ],
        "revision_rules": [
            "if the signature is only a shared filename/token accident, retire",
            "if one row cannot support a clean pair, use a different cluster row before terminal handoff",
            "if fewer than the required rows support clean pairs, emit retired or operator_required with blocked_edge",
        ],
        "min_non_tautological_routes_before_operator_required": 2,
        "scope_boundary": "no proof credit; the born family is only a seed/candidate until governance/probe lanes ratify later value",
        "nearest_confuser_disambiguators": [
            "new YAML is not a closure",
            "candidate_family is not validated_family",
            "static no-signal row is not evidence of usefulness",
            "negative control must test the family ingredient, not Lean syntax/elaboration failure",
        ],
    }


def validate_operator_contract(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate a worker payload's compact operator contract."""
    failures: list[dict[str, Any]] = []
    contract = payload.get("operator_contract")
    if not isinstance(contract, dict):
        return {
            "schema": "leanmill-operator-contract-validation-v1",
            "status": "fail",
            "failure_count": 1,
            "failures": [{"failure": "missing_operator_contract"}],
        }
    if contract.get("schema") != "leanmill-operator-contract-v1":
        failures.append({"failure": "invalid_operator_contract_schema", "schema": contract.get("schema")})
    patch_mode = str(payload.get("family_spec_patch_mode") or "")
    expected_class = FAMILY_BIRTH_CLASS if patch_mode == FAMILY_BIRTH_CLASS else C_SUPPLY_CLASS
    expected_program = FAMILY_BIRTH_ACTION_PROGRAM if expected_class == FAMILY_BIRTH_CLASS else C_SUPPLY_ACTION_PROGRAM
    expected_anti_program = FAMILY_BIRTH_ANTI_PATTERN_ACTION_PROGRAM if expected_class == FAMILY_BIRTH_CLASS else C_SUPPLY_ANTI_PATTERN_ACTION_PROGRAM
    expected_card_type = "family_birth_candidate_guard" if expected_class == FAMILY_BIRTH_CLASS else "c_supply_template_backfill_guard"
    if str(contract.get("accepted_residual_class") or "") != expected_class:
        failures.append({
            "failure": "invalid_accepted_residual_class",
            "expected_residual_class": expected_class,
            "accepted_residual_class": contract.get("accepted_residual_class"),
        })
    if str(contract.get("source_cue_check_status") or "") != "pass":
        failures.append({
            "failure": "source_cue_check_not_pass",
            "source_cue_check_status": contract.get("source_cue_check_status"),
            "source_cue_failures": contract.get("source_cue_failures") or [],
        })
    if str(contract.get("target_family") or "") != str(payload.get("family") or ""):
        failures.append({
            "failure": "operator_contract_family_mismatch",
            "contract_family": contract.get("target_family"),
            "payload_family": payload.get("family"),
        })
    action_program = contract.get("action_program")
    if action_program != expected_program:
        failures.append({"failure": "operator_contract_action_program_mismatch", "action_program": action_program})
    if contract.get("required_next_action") != expected_program[0]:
        failures.append({"failure": "operator_contract_required_next_action_mismatch", "required_next_action": contract.get("required_next_action")})
    current_action_index = contract.get("current_action_index")
    current_ok, current_idx = _parse_int(current_action_index)
    if not current_ok or current_idx != 0:
        failures.append({"failure": "operator_contract_current_action_index_mismatch", "current_action_index": current_action_index})
    for key in ("program_counter_rule", "entry_conditions", "required_evidence", "failure_conditions", "revision_rules", "scope_boundary", "path_c_memory_action_card", "anti_pattern_action_card"):
        if not _nonempty(contract.get(key)):
            failures.append({"failure": f"operator_contract_missing_{key}"})
    action_card = contract.get("path_c_memory_action_card") if isinstance(contract.get("path_c_memory_action_card"), dict) else {}
    if action_card.get("schema") != "leanmill-path-c-memory-action-card-v1":
        failures.append({"failure": "operator_contract_invalid_path_c_memory_action_card_schema"})
    if str(action_card.get("family") or "") != str(payload.get("family") or ""):
        failures.append({
            "failure": "operator_contract_path_c_action_card_family_mismatch",
            "card_family": action_card.get("family"),
            "payload_family": payload.get("family"),
        })
    if not _nonempty(action_card.get("required_use")) or not _nonempty(action_card.get("forbidden_shortcuts")):
        failures.append({"failure": "operator_contract_path_c_action_card_missing_required_use_or_forbidden_shortcuts"})
    anti_card = contract.get("anti_pattern_action_card") if isinstance(contract.get("anti_pattern_action_card"), dict) else {}
    anti_receipt = action_cards.validate_action_card(
        anti_card,
        expected_card_type=expected_card_type,
        expected_action_program=expected_anti_program,
    )
    if anti_receipt["status"] != "pass":
        failures.append({
            "failure": "operator_contract_invalid_anti_pattern_action_card",
            "anti_pattern_action_card_receipt": anti_receipt,
        })
    floor_ok, floor_value = _parse_int(contract.get("min_non_tautological_routes_before_operator_required"))
    if not floor_ok or floor_value < 2:
        failures.append({"failure": "operator_contract_attempt_floor_too_low"})
    row_key = "family_birth_candidate_rows" if expected_class == FAMILY_BIRTH_CLASS else "c_supply_candidate_rows"
    payload_rows = {str(row) for row in (payload.get(row_key) or []) if str(row)}
    contract_rows = {
        str(row.get("row_id") or "")
        for row in (contract.get("candidate_rows") or [])
        if isinstance(row, dict) and str(row.get("row_id") or "")
    }
    if not payload_rows:
        failures.append({"failure": f"payload_missing_{row_key}"})
    if payload_rows != contract_rows:
        failures.append({
            "failure": "operator_contract_candidate_rows_mismatch",
            "payload_rows": sorted(payload_rows),
            "contract_rows": sorted(contract_rows),
        })
    missing_targets = [
        str(row.get("row_id") or "")
        for row in (contract.get("candidate_rows") or [])
        if isinstance(row, dict) and not str(row.get("target_theorem_name") or "")
    ]
    if expected_class == C_SUPPLY_CLASS and missing_targets:
        failures.append({"failure": "operator_contract_candidate_missing_target_theorem_name", "rows": missing_targets})
    return {
        "schema": "leanmill-operator-contract-validation-v1",
        "status": "pass" if not failures else "fail",
        "failure_count": len(failures),
        "failures": failures,
    }


def operator_required_attempt_lint(payload: dict[str, Any], stdout_json: dict[str, Any]) -> dict[str, Any]:
    """Require bounded attempted routes before terminal operator handoff."""
    contract = payload.get("operator_contract") if isinstance(payload.get("operator_contract"), dict) else {}
    exit_kind = str(stdout_json.get("exit_kind") or "")
    if exit_kind not in {"operator_required", "retired"}:
        return {
            "schema": "leanmill-operator-required-attempt-lint-v1",
            "status": "pass",
            "failure_count": 0,
            "failures": [],
        }
    floor_ok, floor = _parse_int(contract.get("min_non_tautological_routes_before_operator_required"))
    if not floor_ok:
        floor = 2
    attempted = stdout_json.get("attempted_routes") or []
    if isinstance(attempted, str):
        attempted = [attempted]
    normalized = [_norm_route(route) for route in attempted if str(route).strip()]
    unique = sorted({route for route in normalized if route})
    weak_routes = [route for route in unique if len(route) < 12 or route in {"tried", "failed", "not found", "route a", "route b"}]
    failures: list[dict[str, Any]] = []
    if floor and len(unique) < floor:
        failures.append({
            "failure": "operator_required_without_attempt_floor",
            "attempted_route_count": len(unique),
            "required_attempted_route_count": floor,
        })
    if weak_routes:
        failures.append({"failure": "operator_required_attempted_routes_too_weak", "weak_routes": weak_routes[:5]})
    if not str(stdout_json.get("blocked_edge") or ""):
        failures.append({"failure": "operator_required_missing_blocked_edge"})
    return {
        "schema": "leanmill-operator-required-attempt-lint-v1",
        "status": "pass" if not failures else "fail",
        "failure_count": len(failures),
        "failures": failures,
    }


def render_contract_for_prompt(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True)


def _self_test() -> int:
    contract = c_supply_template_backfill_contract(
        family="fam",
        candidate_rows=[{
            "row_id": "r1",
            "source_file": "/tmp/r1.lean",
            "target_theorem_name": "target_r1",
            "matched_features": ["Ioo", "Ioc"],
            "static_exit": "tested_no_positive_signal",
        }],
        target_path="analytics/public/leanmill/repair_families/fam.yaml",
        source_demand={"family": "fam", "recommended_action": "source_similar_static_fail_rows"},
        contract_id="cid",
    )
    payload = {
        "family": "fam",
        "c_supply_candidate_rows": ["r1"],
        "operator_contract": contract,
    }
    ok = validate_operator_contract(payload)
    assert ok["status"] == "pass", ok
    missing = dict(payload)
    missing["operator_contract"] = c_supply_template_backfill_contract(
        family="fam",
        candidate_rows=[{"row_id": "r1", "source_file": "/tmp/r1.lean"}],
        target_path="x",
        source_demand={},
        contract_id="bad",
    )
    bad = validate_operator_contract(missing)
    assert bad["status"] == "fail", bad
    missing_card = dict(contract)
    missing_card.pop("path_c_memory_action_card", None)
    bad_card = validate_operator_contract({**payload, "operator_contract": missing_card})
    assert bad_card["status"] == "fail", bad_card
    assert any(f.get("failure") == "operator_contract_missing_path_c_memory_action_card" for f in bad_card["failures"]), bad_card
    missing_anti = dict(contract)
    missing_anti.pop("anti_pattern_action_card", None)
    bad_anti = validate_operator_contract({**payload, "operator_contract": missing_anti})
    assert bad_anti["status"] == "fail", bad_anti
    assert any(f.get("failure") == "operator_contract_missing_anti_pattern_action_card" for f in bad_anti["failures"]), bad_anti
    malformed = dict(contract)
    malformed["current_action_index"] = "not-an-int"
    malformed["min_non_tautological_routes_before_operator_required"] = "nan"
    bad_numeric = validate_operator_contract({**payload, "operator_contract": malformed})
    assert bad_numeric["status"] == "fail", bad_numeric
    terminal_bad = operator_required_attempt_lint(payload, {"exit_kind": "operator_required", "blocked_edge": "helper_missing", "attempted_routes": ["direct helper"]})
    assert terminal_bad["status"] == "fail", terminal_bad
    terminal_ok = operator_required_attempt_lint(payload, {"exit_kind": "operator_required", "blocked_edge": "helper_missing", "attempted_routes": ["Ioo to Ioc helper bridge failed", "endpoint arithmetic bound route failed"]})
    assert terminal_ok["status"] == "pass", terminal_ok
    birth = family_birth_candidate_contract(
        family="born",
        cluster_rows=[{"row_id": "r1", "source_file": "/tmp/r1.lean"}, {"row_id": "r2", "source_file": "/tmp/r2.lean"}, {"row_id": "r3", "source_file": "/tmp/r3.lean"}],
        target_path="analytics/public/leanmill/repair_families/born.yaml",
        cluster={"signature_tokens": ["mellin", "convergent"], "row_count": 3, "required_birth_receipt": {"min_rows": 3}},
        contract_id="birth",
    )
    birth_ok = validate_operator_contract({"family": "born", "family_spec_patch_mode": "family_birth_candidate", "family_birth_candidate_rows": ["r1", "r2", "r3"], "operator_contract": birth})
    assert birth_ok["status"] == "pass", birth_ok
    print("leanmill_operator_contracts self-test PASS")
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
