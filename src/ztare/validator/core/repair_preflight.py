from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

from ztare.common.leaf_workbench_executor import (
    blocked_strategy_discharge_wants_boundary_morphism,
    execute_unique_boundary_morphism_chain,
    leaf_workbench_action_request_retry_message,
    leaf_workbench_receipt_preflight_message,
    replay_candidate_bound_leaf_receipt_for_current_candidate,
    required_candidate_bound_action_error,
)
from ztare.common.worldmodel_carrier_purity import carrier_contract_error
from ztare.common.control_state_machine import control_receipt_rows
from ztare.common.sealed_boundary_cegar import (
    boundary_cegar_candidate_delta_lowerability,
)
from ztare.common.strategy_card_roles import (
    META_HARDENING_LANE,
    SKILL_ACQUISITION_LANE,
    strategy_card_blocks_context,
    strategy_card_role,
)
from ztare.common.structured_blocks import json_objects_after_marker
from ztare.validator.core.pre_judge_gate import (
    _append_gate_receipt,
    detect_patch_base_regression_preflight,
)
from ztare.validator.core.strategy_card_gate import (
    evaluate_strategy_card_gate,
    extract_strategy_card_discharges,
    persist_strategy_card_discharges,
)


_AMBIENT_DEPENDENCY_MARKERS = (
    "__file__",
    "importlib.util.spec_from_file_location",
    ".exec_module(",
)

def ambient_carrier_dependency_retry_message(
    *,
    enabled: bool,
    candidate_source: str,
) -> str | None:
    """Return an R1 retry message for non-self-contained carriers.

    Pre-judge harnesses execute submitted candidates as sealed carriers. They
    may be parsed, snapshotted, or exec'd outside normal importlib module
    semantics, so ambient filesystem anchors such as ``__file__`` are not part
    of the contract. This is an interface check only; the deterministic gates
    still decide candidate quality.
    """
    if not enabled:
        return None
    hits = [marker for marker in _AMBIENT_DEPENDENCY_MARKERS if marker in candidate_source]
    if not hits:
        return None
    return (
        "AMBIENT_CARRIER_DEPENDENCY_PRECHECK: submitted candidate must be a "
        "self-contained executable carrier under the deterministic gate runtime. "
        f"Remove ambient filesystem/import hooks {hits}; do not rely on "
        "`__file__`, importlib loading of prior submissions, cwd-specific paths, "
        "or workspace reads. If preserving a patch base is required, inline the "
        "base logic or emit a valid patch-style carrier accepted by the contract; "
        "then rerun the same replay/holdout gates."
    )


def strategy_card_retry_message(
    *,
    project_dir: str | Path,
    thesis_text: str,
    candidate_source: str = "",
) -> str | None:
    """Return an R1 retry message for missing or malformed card receipts."""
    if _looks_like_executable_worldmodel_carrier(candidate_source):
        return None
    result = evaluate_strategy_card_gate(
        project_dir=project_dir,
        thesis_text=thesis_text,
        candidate_source=candidate_source,
        semantic_status=False,
    )
    if result.passed:
        # FIX 4: persist validated discharge receipts so candidate-discharge
        # receipts can close strategy cards as accepted (zero-caller → wired).
        try:
            persist_strategy_card_discharges(
                project_dir=project_dir,
                thesis_text=thesis_text,
                candidate_source=candidate_source,
                semantic_status=False,
            )
        except Exception:  # noqa: BLE001 — persist must not block the caller
            pass
        return None
    payload_verdict = result.payload.get("verdict") if isinstance(result.payload, dict) else None
    if payload_verdict == "no_blocking_cards":
        # Not-applicable is not a failure: with zero open cards there is
        # nothing to discharge and no strike to hand out.
        return None
    invalid = result.payload.get("invalid") if isinstance(result.payload, dict) else None
    missing = result.payload.get("missing") if isinstance(result.payload, dict) else None
    card_context = _strategy_card_retry_context(project_dir)
    return (
        "STRATEGY_CARD_RECEIPT_PRECHECK: blocking skill-acquisition Strategy "
        "Office cards require a valid typed discharge before candidate evaluation. "
        f"{result.message}; missing={missing or []}; invalid={invalid or []}. "
        "Use marker STRATEGY_CARD_DISCHARGE or STRATEGY_CARD_RECEIPT with "
        "outcome satisfied|refuted|blocked. Include evidence_refs; for "
        "repair-card blocked receipts, new_evidence_refs may carry the "
        "evidence support when paired with blocker_kind and next_action."
        f"{card_context}"
    )


def _looks_like_executable_worldmodel_carrier(candidate_source: str) -> bool:
    """Return true when the candidate should reach deterministic replay first."""

    source = str(candidate_source or "").strip()
    return bool(source) and carrier_contract_error(source) is None


def _strategy_card_retry_context(project_dir: str | Path) -> str:
    try:
        from ztare.common.operator_proposal_contract import open_cards
        from ztare.validator.core.strategy_card_gate import (
            admissible_no_attempt_blocker_kinds,
        )

        all_cards = open_cards(Path(project_dir) / "workspace" / "strategy_experiments.jsonl")
        cards = [
            card for card in all_cards
            if strategy_card_blocks_context(card)
        ]
        meta_count = sum(
            1 for card in all_cards
            if strategy_card_role(card).lane == META_HARDENING_LANE
        )
    except Exception:  # noqa: BLE001
        return ""
    bits: list[str] = []
    for card in cards[:4]:
        if not isinstance(card, dict):
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
        residue = plan.get("residue_quotient") if isinstance(plan.get("residue_quotient"), dict) else {}
        seed = plan.get("seed_prerequisite") if isinstance(plan.get("seed_prerequisite"), dict) else {}
        no_attempt = admissible_no_attempt_blocker_kinds(card)
        bits.append(
            "card("
            f"sha={card.get('failure_family_sha') or '?'}; "
            f"lane={SKILL_ACQUISITION_LANE}; "
            f"kind={card.get('kind') or '?'}; "
            f"residue={residue.get('residue_class') or '?'}; "
            f"next_gate={gate.get('command') or '?'}:{gate.get('success_status') or '?'}; "
            f"no_attempt_blockers={no_attempt}; "
            f"seed={seed.get('seed_path') or seed.get('status') or '?'}; "
            f"prediction={card.get('falsifiable_prediction') or ''}"
            ")"
        )
    if meta_count:
        bits.append(f"meta_hardening_cards(count={meta_count}; candidate_blocking=False)")
    if not bits:
        return ""
    return " Open card context: " + " ".join(bits)


def leaf_workbench_retry_message(
    *,
    enabled: bool,
    thesis_text: str,
    candidate_source: str = "",
    fact_markers: tuple[str, ...] = (),
    project_dir: str | Path | None = None,
    contract: Any | None = None,
    records_fn: Callable[[str | Path], list[dict[str, Any]]] | None = None,
    action_handlers: dict[str, Callable[[str | Path, dict[str, Any], dict[str, Any] | None, Any], dict[str, Any]]] | None = None,
    stateless_actions: set[str] | frozenset[str] | None = None,
) -> str | None:
    """Require receipt binding when a candidate uses leaf-workbench facts."""
    if not enabled:
        return None
    combined = f"{thesis_text}\n{candidate_source}"
    if "LEAF_WORKBENCH_ACTION_REQUEST:" in combined and project_dir is not None:
        return leaf_workbench_action_request_retry_message(
            enabled=True,
            project_dir=project_dir,
            thesis_text=thesis_text,
            candidate_source=candidate_source,
            contract=contract,
            records_fn=records_fn,
            action_handlers=action_handlers,
            stateless_actions=stateless_actions,
        )
    if candidate_source.strip() and project_dir is not None:
        missing_action_error = required_candidate_bound_action_error(
            project_dir=project_dir,
            thesis_text=combined,
            candidate_source=candidate_source,
            carrier_is_executable=_looks_like_executable_worldmodel_carrier(candidate_source),
        )
        if missing_action_error is not None:
            return missing_action_error
    return leaf_workbench_receipt_preflight_message(
        project_dir=project_dir,
        thesis_text=thesis_text,
        candidate_source=candidate_source,
        fact_markers=fact_markers,
        contract=contract,
        records_fn=records_fn,
        action_handlers=action_handlers,
        stateless_actions=stateless_actions,
    )


def boundary_cegar_ready_delta_retry_message(
    *,
    enabled: bool,
    thesis_text: str,
    candidate_source: str = "",
) -> str | None:
    """Reject receipt-only boundary states after receipts admit lowering.

    Workbench observations are control-state transitions, not candidate
    evaluations. Once the carried receipt family supplies a gamma-lowerable
    witness, a no-carrier submission would only consume an iteration on copied
    state. The next object-level move must be an executable delta, unless a
    new typed receipt refutes that lowerability.
    """

    if not enabled or str(candidate_source or "").strip():
        return None
    receipts = json.dumps(
        [
            row for row in control_receipt_rows(thesis_text or "")
            if str(row.get("type") or "") in {"LEAF_WORKBENCH_RECEIPT", "VISIBLE_WORKBENCH_DIAGNOSTIC"}
        ],
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    if not receipts:
        return None
    try:
        lowerable = boundary_cegar_candidate_delta_lowerability(receipts)
    except Exception:  # noqa: BLE001 - malformed receipts are handled by receipt validation.
        return None
    if lowerable is not True:
        return None
    return (
        "BOUNDARY_CEGAR_READY_FOR_DELTA: carried workbench receipt family "
        "admits candidate lowering, but this submission contains no executable "
        "carrier. Free retry: submit a candidate delta that cites receipt refs/facts, "
        "or add a typed receipt/proposal that refutes lowerability. Do not spend "
        "the iteration by copying receipt state alone."
    )


def strategy_discharge_missing_evidence_action_retry_message(
    *,
    enabled: bool,
    project_dir: str | Path,
    thesis_text: str,
    candidate_source: str = "",
    contract: Any | None = None,
    records_fn: Callable[[str | Path], list[dict[str, Any]]] | None = None,
    action_handlers: dict[str, Callable[[str | Path, dict[str, Any], dict[str, Any] | None, Any], dict[str, Any]]] | None = None,
    stateless_actions: set[str] | frozenset[str] | None = None,
) -> str | None:
    """Run the current workbench action for a typed blocked Strategy receipt.

    A Strategy-card discharge may lawfully say "blocked: missing_evidence".
    When the current boundary already exposes exactly the needed registered
    workbench morphism, consuming the iteration would only measure plumbing.
    Compile that typed block into the same action-request executor used for
    explicit ``LEAF_WORKBENCH_ACTION_REQUEST`` rows.
    """
    if not enabled:
        return None
    receipts = extract_strategy_card_discharges(thesis_text or "")
    if not blocked_strategy_discharge_wants_boundary_morphism(receipts):
        return None
    return execute_unique_boundary_morphism_chain(
        project_dir=project_dir,
        thesis_text=thesis_text,
        candidate_source=candidate_source,
        contract=contract,
        records_fn=records_fn,
        action_handlers=action_handlers,
        stateless_actions=stateless_actions,
    )


def _visible_counterexample_exhausted(trace: object, failed_gates: list[str]) -> bool:
    if not isinstance(trace, dict):
        return False
    try:
        checked = int(trace.get("checked_rows") or 0)
        exact = int(trace.get("exact_rows") or -1)
        wrong = int(trace.get("wrong_cell_count") or 0)
    except Exception:
        return False
    if not checked or exact != checked or wrong != 0:
        return False
    labels = " ".join(str(label).lower() for label in failed_gates)
    return any(token in labels for token in ("holdout", "transfer", "terminal"))


def _strategy_gate_action_summary(payload: object) -> str:
    if not isinstance(payload, dict):
        return _short_json(payload)
    result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
    bits = [
        f"command={payload.get('command') or result.get('command')}",
        f"status={payload.get('status') or result.get('status')}",
        f"receipt_ref={payload.get('receipt_ref') or result.get('receipt_ref')}",
    ]
    for key in (
        "exact_actions",
        "exact_steps",
        "steps_tested",
        "first_failed_after_first_step_repair",
        "local_residue_status",
        "local_residue_class_count",
    ):
        if key in result:
            bits.append(f"{key}={result.get(key)}")
    top = result.get("top_local_residue_class")
    if isinstance(top, dict) and top:
        bits.append(
            "top_local_residue="
            + json.dumps(top, sort_keys=True, separators=(",", ":"), default=str)[:700]
        )
    return "; ".join(bits)


def _structural_isomorphism_summary(payload: object) -> str:
    if not isinstance(payload, dict):
        return _short_json(payload)
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    bits = [
        f"mode={payload.get('mode')}",
        f"status={payload.get('status')}",
        f"receipt_ref={payload.get('receipt_ref')}",
    ]
    if "candidate_count" in result:
        bits.append(f"candidate_count={result.get('candidate_count')}")
    prescription = result.get("prescription") if isinstance(result.get("prescription"), dict) else {}
    if prescription:
        bits.append(f"source_field={prescription.get('source_field')}")
        bits.append(f"source_theorem={prescription.get('source_theorem')}")
    conjectures = result.get("conjectures") if isinstance(result.get("conjectures"), list) else []
    if conjectures:
        first = conjectures[0] if isinstance(conjectures[0], dict) else {}
        bits.append(f"mother_structure={first.get('mother_structure')}")
        cards = first.get("prediction_cards")
        if isinstance(cards, list):
            bits.append(f"prediction_cards={len(cards)}")
    return "; ".join(str(bit) for bit in bits if str(bit))


def patch_base_regression_retry_message(
    *,
    enabled: bool,
    project_dir: str | Path,
    candidate_source: str,
    python_executable: str = sys.executable,
) -> str | None:
    """Return an R1 retry message when a repair candidate loses its patch base.

    This module owns the temp-file gate probe and the retry wording so the main
    autoresearch loop stays orchestration-only.
    """
    if not enabled:
        return None
    project_path = Path(project_dir)
    probe_path = project_path / "workspace" / "_pre_judge_probe_test_model.py"
    try:
        probe_path.parent.mkdir(parents=True, exist_ok=True)
        probe_path.write_text(candidate_source, encoding="utf-8")
        try:
            regression = detect_patch_base_regression_preflight(
                enabled=True,
                project_dir=project_path,
                candidate_path=probe_path,
                python_executable=python_executable,
            )
        except Exception as exc:  # noqa: BLE001
            # Fail open WITH a receipt: a broken probe must not silently skip
            # every downstream preflight rule via the caller's blanket except.
            _append_gate_receipt(project_path, {
                "site": "repair_preflight.py:patch_base_regression_retry_message",
                "fallback_taken": "probe_error",
                "cause": repr(exc),
            })
            return None
        if regression is None:
            return None
        receipt = regression.regression_receipt
        trace = regression.counterexample_trace
        receipt_payload = {
            "schema": "ztare-latest-patch-base-regression-v1",
            "candidate_regression_receipt": receipt,
            "counterexample_trace": trace,
        }
        try:
            (project_path / "workspace" / "latest_patch_base_regression.json").write_text(
                json.dumps(receipt_payload, sort_keys=True, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception:
            pass
        weakness_receipt: dict[str, object] | None = None
        try:
            from ztare.common.harness_weakness import write_harness_weakness_receipt

            weakness_receipt = write_harness_weakness_receipt(
                project_dir=project_path,
                source_ref="workspace/latest_patch_base_regression.json",
                regression_receipt=receipt,
                counterexample_trace=trace,
            )
        except Exception:
            weakness_receipt = None
        weakness_line = ""
        if isinstance(weakness_receipt, dict):
            weakness_line = (
                "\nHARNESS_WEAKNESS_RECEIPT: "
                + json.dumps(
                    {
                        "schema": weakness_receipt.get("schema"),
                        "weakness_class": weakness_receipt.get("weakness_class"),
                        "recommended_route": weakness_receipt.get("recommended_route"),
                        "recommended_capability_id": weakness_receipt.get("recommended_capability_id"),
                        "source_ref": "workspace/latest_harness_weakness.json",
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        relation = str(receipt.get("candidate_relation") or "regression")
        comparison = receipt.get("quotient_comparison")
        quotient_relation = ""
        quotient_receipt = ""
        if isinstance(comparison, dict):
            quotient_json = json.dumps(
                comparison,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            quotient_relation = (
                f"; quotient_relation={comparison.get('relation')}; "
                f"candidate_top={comparison.get('candidate_top_quotient')}; "
                f"best_prior_top={comparison.get('best_prior_top_quotient')}"
            )
            quotient_receipt = (
                "\nPATCH_BASE_QUOTIENT_RECEIPT: "
                f"{quotient_json}"
            )
        if relation == "hard_gate_failure":
            if _visible_counterexample_exhausted(trace, regression.failed_gates):
                return (
                    "PATCH_BASE_IMPROVEMENT_PRECHECK: candidate has no visible "
                    "replay counterexample left, but a boundary gate failed "
                    f"(relation=hard_gate_failure). failed_gates={regression.failed_gates}. "
                    "This is a substrate-boundary/evidence-acquisition state, "
                    "not another visible residual repair. Preserve the candidate "
                    "as a system-2 artifact, request `run_strategy_required_gate` "
                    "when a Strategy gate is listed, or return LOWERABILITY_BLOCKED "
                    "if no gamma-lowerable candidate exists. Do not request "
                    "another visible-artifact probe unless a new visible "
                    "mismatch appears. "
                    f"gated_sha={receipt.get('candidate_sha')}; visible_exact="
                    f"{trace.get('exact_rows')}/{trace.get('checked_rows')}; "
                    f"wrong_cells={trace.get('wrong_cell_count')}"
                    f"{quotient_receipt}"
                    f"{weakness_line}"
                )
            rec_cap = ""
            if isinstance(weakness_receipt, dict):
                rec_cap = str(weakness_receipt.get("recommended_capability_id") or "").strip()
            if rec_cap:
                observation_instruction = (
                    f"Request the registered capability `{rec_cap}` and use its "
                    "typed observation to name the missing observable distinction "
                    "before proposing a new delta."
                )
            else:
                observation_instruction = (
                    "Request a registered visible workbench observation when one "
                    "is listed; if none can expose the needed distinction, report "
                    "the missing witness/sensor inside LOWERABILITY_BLOCKED instead "
                    "of guessing."
                )
            return (
                "PATCH_BASE_IMPROVEMENT_PRECHECK: candidate failed the "
                "deterministic pre-judge gate before a comparable replay "
                "quotient was available (relation=hard_gate_failure). "
                f"failed_gates={regression.failed_gates}. "
                "Do not retreat to an identity PATCH_DELTA over the same "
                "patch base: that preserves the same failed quotient. "
                f"{observation_instruction} If the current "
                "workbench lacks a typed reader that can expose the needed "
                "distinction, use a stateless probe or report the missing "
                "witness/sensor inside LOWERABILITY_BLOCKED. "
                f"gated_sha={receipt.get('candidate_sha')}; "
                f"first={str(trace.get('first_mismatch') or '')[:260]}"
                f"{quotient_receipt}"
                f"{weakness_line}"
            )
        best_prior = str(receipt.get("best_prior_submission") or "")
        best_prior_id = (
            f"{best_prior} sha={receipt.get('best_prior_sha')}"
            if best_prior else f"sha={receipt.get('best_prior_sha')}"
        )
        return (
            "PATCH_BASE_IMPROVEMENT_PRECHECK: candidate must strictly improve "
            f"the best deterministic near-miss before spending an iteration "
            f"(relation={relation}). "
            "Preserve the content-addressed best prior "
            f"({best_prior_id}) as the PATCH_BASE identity and make a minimal "
            "repair, or explicitly declare a full-rewrite rationale that beats "
            "it under the deterministic gate. "
            f"exact_rows {receipt.get('candidate_exact_rows')} vs "
            f"{receipt.get('best_prior_exact_rows')}; wrong_cells "
            f"{receipt.get('candidate_wrong_cells')} vs "
            f"{receipt.get('best_prior_wrong_cells')}; holdout "
            f"{receipt.get('candidate_holdout_depth')} vs "
            f"{receipt.get('best_prior_holdout_depth')}; first="
            f"{str(trace.get('first_mismatch') or '')[:260]}"
            f"{quotient_relation}"
            f"{quotient_receipt}"
            f"{weakness_line}"
        )
    finally:
        try:
            probe_path.unlink(missing_ok=True)
        except Exception:
            pass
