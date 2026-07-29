"""Resume Guide-selected target conjectures through the canonical Lean solver.

Repository-imported conjectures have a different identity from isolated formal
tasks.  They retain their declared source context and therefore cannot enter
the formal-task executor's Mathlib-only proof world.  This module freezes that
source-adjacent category, then delegates proof and refutation work to
``solver_core.solve_adhoc``.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Callable, Mapping

from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.control_plane import StatementId, Verdict, VerdictKind
from ztare.leanmill.target_curriculum import (
    LEGACY_TARGET_CONJECTURE_WAVE_SCHEMA,
    TARGET_CONJECTURE_WAVE_SCHEMA,
    render_target_candidate_source,
    validate_target_conjecture_admission,
    validate_target_statement_elaboration,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.solver.closed_artifact import finalized_ratification_eligible


SOURCE_ADJACENT_TASK_SCHEMA = "leanmill.source_adjacent_candidate_task.v1"
SOURCE_ADJACENT_QUEUE_SCHEMA = "leanmill.source_adjacent_candidate_queue.v1"
SOURCE_ADJACENT_ATTEMPT_SCHEMA = (
    "leanmill.source_adjacent_candidate_adjudication_attempt.v1"
)
TARGET_CONTINUATION_SCHEMA = "leanmill.target_conjecture_continuation.v1"
SOURCE_ADJACENT_SOLVER_OWNER = "ztare.leanmill.solver.solver_core:solve_adhoc"
SOURCE_ADJACENT_NATIVE_OWNER = (
    "ztare.leanmill.target_curriculum_adjudication:"
    "provider_free_native_adjudicate"
)
_TERMINAL = {"proved", "refuted"}


class CumulativeProviderBudgetNotDelegated(RuntimeError):
    """Refuse inference-producing adjudication before solver initialization."""


def _budget_not_delegated(*_args, **_kwargs):
    raise CumulativeProviderBudgetNotDelegated(
        "source-adjacent task is frozen and resumable; no provider budget "
        "was delegated"
    )


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")[-100:]


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def provider_free_native_adjudicate(
    target_name: str,
    source_text: str,
    goal: str,
    *,
    timeout_s: int,
    substrate: str | Path,
    notes: str | None = None,
    require_positive_axiom_receipt: bool = True,
) -> dict[str, Any]:
    """Try deterministic tactics, then govern only an already-found proof.

    The generic ad-hoc solver owns provider-producing pool, strategy, and
    falsifier branches.  A revision epoch with no delegated provider budget
    must not initialize those branches.  This entry calls only its existing
    deterministic native probe.  A hit crosses into ``solve_adhoc`` solely via
    its bounded ``preverified_only`` ratification lifecycle; a miss remains a
    typed, resumable capability outcome.
    """

    del goal, notes
    lean_root = Path(substrate)
    probe_path = lean_root / (
        "__target_curriculum_native_"
        + content_hash({"target": target_name, "source": source_text})[:20]
        + ".lean"
    )
    try:
        probe_path.write_text(source_text, encoding="utf-8")
        from ztare.leanmill.solver.solver_core import (
            _native_hammer_probe,
            solve_adhoc,
        )

        row = {
            "row_id": f"source-adjacent-native::{target_name}",
            "target_theorem_name": target_name,
            "source_file": str(probe_path),
            "sorried_file": str(probe_path),
            "goal": "",
        }
        native = _native_hammer_probe(row, lean_root, timeout_s)
        if not native.closed or not str(native.proof).strip():
            unavailable = not native.available
            return {
                "results": [{
                    "row_id": row["row_id"],
                    "target_theorem_name": target_name,
                    "outcome": (
                        "provider_free_native_unavailable"
                        if unavailable
                        else "provider_free_native_exhausted"
                    ),
                    "native_transcript": " ".join(
                        str(native.transcript).split()
                    )[-600:],
                    "native_available": native.available,
                    "admissible_negative": native.admissible_negative,
                }],
                "source_adjacent_unavailable_reason": (
                    "provider_free_native_unavailable"
                    if unavailable
                    else "provider_free_native_exhausted"
                ),
                "provider_calls_charged": 0,
                "native_owner": SOURCE_ADJACENT_NATIVE_OWNER,
            }
        governed = solve_adhoc(
            target_name,
            source_text,
            "",
            timeout_s=timeout_s,
            substrate=lean_root,
            preverified_proof=str(native.proof),
            preverified_provider="native_hammer",
            preverified_only=True,
            require_positive_axiom_receipt=require_positive_axiom_receipt,
        )
        governed["provider_calls_charged"] = 0
        governed["native_owner"] = SOURCE_ADJACENT_NATIVE_OWNER
        return governed
    except Exception as exc:  # noqa: BLE001 - typed capability outcome
        return {
            "results": [],
            "source_adjacent_unavailable_reason": (
                "provider_free_native_backend_unavailable:"
                + type(exc).__name__
            ),
            "provider_calls_charged": 0,
            "native_owner": SOURCE_ADJACENT_NATIVE_OWNER,
        }
    finally:
        probe_path.unlink(missing_ok=True)


def build_source_adjacent_candidate_queue(
    wave: Mapping[str, Any],
    statement_elaboration_receipt: Mapping[str, Any],
    guide_receipt: Mapping[str, Any] | None,
    admission: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze executable statements without crossing the formal-task firewall."""

    validate_target_conjecture_admission(
        wave, statement_elaboration_receipt, guide_receipt, admission
    )
    elaboration_rows = validate_target_statement_elaboration(
        wave, statement_elaboration_receipt
    )
    candidates = {
        str(row.get("candidate_id") or ""): row
        for row in wave.get("candidates") or ()
        if isinstance(row, Mapping)
    }
    tasks: list[dict[str, Any]] = []
    not_routed: list[dict[str, str]] = []
    for candidate_id in admission.get("selected_candidate_ids") or ():
        candidate = candidates[str(candidate_id)]
        elaboration = elaboration_rows[str(candidate_id)]
        if elaboration["status"] != "elaborated":
            not_routed.append({
                "candidate_id": str(candidate_id),
                "reason_code": "selected_candidate_has_no_elaborated_statement",
            })
            continue
        target_stem = (
            "targetCurriculumCandidate_"
            + str(candidate["candidate_sha256"])[:20]
        )
        source, target_selector = render_target_candidate_source(
            candidate,
            target_name=target_stem,
            require_formal_context=(
                wave.get("schema") == TARGET_CONJECTURE_WAVE_SCHEMA
            ),
        )
        if content_hash(source) != elaboration["probe_source_sha256"]:
            # The preflight target name is intentionally different.  Bind the
            # statement/context pair directly; theorem naming is host identity.
            preflight_source, _ = render_target_candidate_source(
                candidate,
                target_name="targetConditionedStatementPreflight",
                require_formal_context=(
                    wave.get("schema") == TARGET_CONJECTURE_WAVE_SCHEMA
                ),
            )
            if content_hash(preflight_source) != elaboration["probe_source_sha256"]:
                raise ValueError("source-adjacent task changed its elaborated statement")
        task_core = {
            "schema": SOURCE_ADJACENT_TASK_SCHEMA,
            "task_category": "repo_imported_lean_statement_extension",
            "candidate_id": str(candidate_id),
            "candidate_sha256": str(candidate["candidate_sha256"]),
            "wave_sha256": str(wave["wave_sha256"]),
            "statement_elaboration_receipt_sha256": str(
                statement_elaboration_receipt["receipt_sha256"]
            ),
            "statement_elaboration_row_sha256": str(elaboration["row_sha256"]),
            "admission_receipt_sha256": str(admission["receipt_sha256"]),
            "guide_receipt_sha256": str(admission["guide_receipt_sha256"]),
            "target_name": target_selector,
            "source_text": source,
            "source_sha256": content_hash(source),
            "signature_sha256": str(elaboration["signature_sha256"]),
            "formal_context": dict(candidate.get("formal_context") or {}),
            "mathematical_statement": str(candidate["mathematical_statement"]),
            "falsification_plan": str(candidate["falsification_plan"]),
            "solver_owner": SOURCE_ADJACENT_SOLVER_OWNER,
            "authority": "source_adjacent_existing_solver_only",
        }
        tasks.append({**task_core, "task_sha256": content_hash(task_core)})
    queue_core = {
        "schema": SOURCE_ADJACENT_QUEUE_SCHEMA,
        "wave_schema": str(wave.get("schema") or ""),
        "wave_sha256": str(wave["wave_sha256"]),
        "statement_elaboration_receipt_sha256": str(
            statement_elaboration_receipt["receipt_sha256"]
        ),
        "admission_receipt_sha256": str(admission["receipt_sha256"]),
        "task_count": len(tasks),
        "tasks": tasks,
        "rejected_candidate_ids": [
            str(value)
            for value in statement_elaboration_receipt.get(
                "rejected_candidate_ids"
            ) or ()
        ],
        "not_routed_selected_candidates": not_routed,
        "formal_task_firewall": "preserved_mathlib_only",
        "solver_owner": SOURCE_ADJACENT_SOLVER_OWNER,
        "authority": "source_adjacent_task_freeze_no_theorem_content_added",
    }
    return {**queue_core, "queue_sha256": content_hash(queue_core)}


def _validate_attempt(task_by_id: Mapping[str, Mapping[str, Any]], row: Mapping[str, Any]) -> None:
    core = {key: value for key, value in row.items() if key != "attempt_sha256"}
    candidate_id = str(row.get("candidate_id") or "")
    task = task_by_id.get(candidate_id)
    if (
        row.get("schema") != SOURCE_ADJACENT_ATTEMPT_SCHEMA
        or row.get("attempt_sha256") != content_hash(core)
        or task is None
        or row.get("task_sha256") != task.get("task_sha256")
        or row.get("candidate_sha256") != task.get("candidate_sha256")
        or row.get("wave_sha256") != task.get("wave_sha256")
        or row.get("admission_receipt_sha256")
        != task.get("admission_receipt_sha256")
        or row.get("status") not in {"proved", "refuted", "unavailable"}
        or row.get("solver_owner") != SOURCE_ADJACENT_SOLVER_OWNER
    ):
        raise ValueError("source-adjacent attempt changed task identity")
    verdict = Verdict.from_json(row.get("verdict") or {})
    expected = StatementId.from_parts(
        target_name=str(task["target_name"]),
        source_text=str(task["source_text"]),
        closed_prop=str(task["source_text"]),
    )
    if verdict.statement_id.target_name != expected.target_name or (
        verdict.statement_id.target_source_hash != expected.target_source_hash
    ):
        raise ValueError("source-adjacent verdict crossed statement identity")


def _governed_closure(raw: Mapping[str, Any], primary: Mapping[str, Any]) -> bool:
    validation = primary.get("contract_validation")
    receipts = (
        validation.get("receipts")
        if isinstance(validation, Mapping)
        else None
    )
    if not isinstance(receipts, Mapping):
        return False
    kernel = receipts.get("kernel_compile_receipt")
    mnc = receipts.get("matched_negative_control_receipt")
    axioms = receipts.get("axiom_allowlist_receipt")
    try:
        from ztare.leanmill.solver.solver_core import (
            _governance_ratification_eligible,
        )

        governance_ok = _governance_ratification_eligible(raw.get("governance"))
    except Exception:  # noqa: BLE001 - missing trust owner cannot mint proof credit
        governance_ok = False
    return bool(
        primary.get("outcome") == "closed"
        and str(primary.get("proof_text") or "").strip()
        and finalized_ratification_eligible(dict(validation))
        and validation.get("positive_axiom_receipt_required") is True
        and isinstance(kernel, Mapping) and kernel.get("passed") is True
        and isinstance(mnc, Mapping)
        and mnc.get("passed") is True
        and isinstance(axioms, Mapping) and axioms.get("passed") is True
        and governance_ok
        and str(raw.get("closure_certificate") or "")
        and raw.get("env_parity_retracted") is not True
    )


def _refutation_verdict(
    raw: Mapping[str, Any], task: Mapping[str, Any]
) -> Verdict | None:
    if raw.get("statement_false_verified") is not True:
        return None
    value = raw.get("control_verdict")
    if not isinstance(value, Mapping):
        return None
    try:
        verdict = Verdict.from_json(value)
    except (TypeError, ValueError):
        return None
    expected = StatementId.from_parts(
        target_name=str(task["target_name"]),
        source_text=str(task["source_text"]),
        closed_prop=str(task["source_text"]),
    )
    if (
        verdict.kind is not VerdictKind.REFUTED
        or verdict.statement_id.target_name != expected.target_name
        or verdict.statement_id.target_source_hash != expected.target_source_hash
        or not verdict.kernel_refutation_source()
    ):
        return None
    return verdict


def _run_attempt(
    task: Mapping[str, Any],
    *,
    attempt_index: int,
    lean_root: Path,
    timeout_s: int,
    solve_fn: Callable[..., Mapping[str, Any]],
    artifact_dir: Path | None,
    previous_attempt_sha256: str,
) -> dict[str, Any]:
    raw: dict[str, Any]
    error_type = ""
    try:
        value = solve_fn(
            str(task["target_name"]),
            str(task["source_text"]),
            "",
            timeout_s=timeout_s,
            substrate=lean_root,
            notes=str(task["falsification_plan"]),
            require_positive_axiom_receipt=True,
        )
        if not isinstance(value, Mapping):
            raise TypeError("solver result is not an object")
        raw = dict(_json_safe(value))
    except Exception as exc:  # noqa: BLE001 - typed resumable outcome
        raw = {"results": [], "exception_type": type(exc).__name__}
        error_type = type(exc).__name__
    solver_ref = ""
    if artifact_dir is not None:
        relative = Path("solver_results") / _slug(str(task["candidate_id"])) / (
            f"attempt_{attempt_index}.json"
        )
        write_json_atomic(artifact_dir / relative, raw)
        solver_ref = str(relative)
    primary = (
        dict(raw["results"][0])
        if isinstance(raw.get("results"), list)
        and raw["results"]
        and isinstance(raw["results"][0], Mapping)
        else {}
    )
    refutation = _refutation_verdict(raw, task)
    statement_id = StatementId.from_parts(
        target_name=str(task["target_name"]),
        source_text=str(task["source_text"]),
        closed_prop=str(task["source_text"]),
    )
    if refutation is not None:
        status = "refuted"
        reason_code = "kernel_verified_negation"
        verdict = refutation
    elif _governed_closure(raw, primary):
        status = "proved"
        reason_code = "governed_kernel_closure"
        verdict = Verdict(
            kind=VerdictKind.CLOSED,
            statement_id=statement_id,
            provenance=SOURCE_ADJACENT_SOLVER_OWNER,
            detail="governed source-adjacent closure",
            artifacts={
                "closure_certificate": str(raw.get("closure_certificate") or ""),
                "closure_lean": str(raw.get("closure_lean") or ""),
            },
        )
    else:
        status = "unavailable"
        if error_type:
            reason_code = f"solver_unavailable:{error_type}"
            kind = VerdictKind.SUBSTRATE_UNAVAILABLE
        elif primary.get("outcome") == "closed":
            reason_code = "closure_lacks_governed_kernel_receipts"
            kind = VerdictKind.REJECTED_BY_GOVERNANCE
        elif raw.get("statement_false_verified") is True:
            reason_code = "refutation_lacks_bound_kernel_verdict"
            kind = VerdictKind.UNVERIFIED
        else:
            reason_code = str(
                raw.get("source_adjacent_unavailable_reason")
                or "proof_and_refutation_not_obtained"
            )
            kind = VerdictKind.UNVERIFIED
        verdict = Verdict(
            kind=kind,
            statement_id=statement_id,
            provenance=SOURCE_ADJACENT_SOLVER_OWNER,
            detail=reason_code,
        )
    core = {
        "schema": SOURCE_ADJACENT_ATTEMPT_SCHEMA,
        "candidate_id": str(task["candidate_id"]),
        "candidate_sha256": str(task["candidate_sha256"]),
        "wave_sha256": str(task["wave_sha256"]),
        "admission_receipt_sha256": str(task["admission_receipt_sha256"]),
        "task_sha256": str(task["task_sha256"]),
        "attempt_index": attempt_index,
        "previous_attempt_sha256": previous_attempt_sha256,
        "status": status,
        "reason_code": reason_code,
        "solver_result_sha256": content_hash(raw),
        "solver_result_ref": solver_ref,
        "solver_outcome": str(primary.get("outcome") or ""),
        "verdict": verdict.to_json(),
        "solver_owner": SOURCE_ADJACENT_SOLVER_OWNER,
        "authority": "existing_solver_governance_feedback",
    }
    return {**core, "attempt_sha256": content_hash(core)}


def _continuation_receipt(
    queue: Mapping[str, Any], attempts: list[dict[str, Any]]
) -> dict[str, Any]:
    task_ids = [str(row["candidate_id"]) for row in queue["tasks"]]
    latest: dict[str, dict[str, Any]] = {}
    for row in attempts:
        latest[str(row["candidate_id"])] = row
    resumable = [
        candidate_id for candidate_id in task_ids
        if candidate_id not in latest or latest[candidate_id]["status"] == "unavailable"
    ]
    terminal = [
        candidate_id for candidate_id in task_ids
        if candidate_id in latest and latest[candidate_id]["status"] in _TERMINAL
    ]
    rejected_candidate_ids = [
        str(value) for value in queue.get("rejected_candidate_ids") or ()
    ]
    status = (
        "revision_required"
        if not task_ids and rejected_candidate_ids
        else "complete_no_executable_selection"
        if not task_ids
        else "adjudicated"
        if len(terminal) == len(task_ids)
        else "resumable"
    )
    core = {
        "schema": TARGET_CONTINUATION_SCHEMA,
        "queue_sha256": str(queue["queue_sha256"]),
        "wave_sha256": str(queue["wave_sha256"]),
        "admission_receipt_sha256": str(queue["admission_receipt_sha256"]),
        "attempts": attempts,
        "latest_attempt_sha256_by_candidate": {
            candidate_id: str(latest[candidate_id]["attempt_sha256"])
            for candidate_id in task_ids if candidate_id in latest
        },
        "proved_candidate_ids": [
            candidate_id for candidate_id in task_ids
            if candidate_id in latest and latest[candidate_id]["status"] == "proved"
        ],
        "refuted_candidate_ids": [
            candidate_id for candidate_id in task_ids
            if candidate_id in latest and latest[candidate_id]["status"] == "refuted"
        ],
        "resumable_candidate_ids": resumable,
        "rejected_candidate_ids": rejected_candidate_ids,
        "status": status,
        "next_authority": (
            "source_adjacent_candidate_adjudication_resume"
            if resumable
            else "target_conjecture_author_revision"
            if rejected_candidate_ids
            else "target_navigation_with_typed_feedback"
        ),
        "solver_owner": SOURCE_ADJACENT_SOLVER_OWNER,
        "authority": "resumable_finite_or_kernel_feedback_join",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def continue_target_conjecture_admission(
    wave: Mapping[str, Any],
    statement_elaboration_receipt: Mapping[str, Any],
    guide_receipt: Mapping[str, Any] | None,
    admission: Mapping[str, Any],
    *,
    lean_root: str | Path,
    artifact_dir: str | Path | None = None,
    timeout_s: int = 500,
    solve_fn: Callable[..., Mapping[str, Any]] | None = None,
    prior_continuation: Mapping[str, Any] | None = None,
    retry_unavailable: bool = True,
    provider_mode: str = "delegated_solver",
    provider_call_budget_delegated: bool | None = None,
) -> dict[str, Any]:
    """Run or resume every frozen executable candidate through one solver door."""

    queue = build_source_adjacent_candidate_queue(
        wave, statement_elaboration_receipt, guide_receipt, admission
    )
    out_dir = Path(artifact_dir) if artifact_dir is not None else None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(out_dir / "source_adjacent_tasks.json", queue)
    task_by_id = {
        str(row["candidate_id"]): row for row in queue["tasks"]
    }
    attempts: list[dict[str, Any]] = []
    if prior_continuation is not None:
        prior_core = {
            key: value for key, value in prior_continuation.items()
            if key != "receipt_sha256"
        }
        if (
            prior_continuation.get("schema") != TARGET_CONTINUATION_SCHEMA
            or prior_continuation.get("queue_sha256") != queue["queue_sha256"]
            or prior_continuation.get("receipt_sha256") != content_hash(prior_core)
        ):
            raise ValueError("prior target continuation changed queue identity")
        attempts = [dict(row) for row in prior_continuation.get("attempts") or ()]
        for row in attempts:
            _validate_attempt(task_by_id, row)
    if provider_mode not in {"delegated_solver", "provider_free_native"}:
        raise ValueError("unknown source-adjacent provider mode")
    if (
        provider_mode == "delegated_solver"
        and provider_call_budget_delegated is False
    ):
        # This branch precedes the lazy solver import below.  An injected
        # solve function cannot bypass the campaign's cumulative budget owner.
        solve_fn = _budget_not_delegated
    elif solve_fn is None:
        if provider_mode == "provider_free_native":
            solve_fn = provider_free_native_adjudicate
        else:
            from ztare.leanmill.solver.solver_core import solve_adhoc

            solve_fn = solve_adhoc
    latest = {str(row["candidate_id"]): row for row in attempts}
    for task in queue["tasks"]:
        candidate_id = str(task["candidate_id"])
        prior = latest.get(candidate_id)
        if prior is not None and (
            prior["status"] in _TERMINAL
            or prior["status"] == "unavailable" and not retry_unavailable
        ):
            continue
        attempt = _run_attempt(
            task,
            attempt_index=(int(prior["attempt_index"]) + 1 if prior else 1),
            lean_root=Path(lean_root),
            timeout_s=timeout_s,
            solve_fn=solve_fn,
            artifact_dir=out_dir,
            previous_attempt_sha256=(str(prior["attempt_sha256"]) if prior else ""),
        )
        attempts.append(attempt)
        latest[candidate_id] = attempt
        receipt = _continuation_receipt(queue, attempts)
        if out_dir is not None:
            write_json_atomic(out_dir / "continuation.json", receipt)
    receipt = _continuation_receipt(queue, attempts)
    if out_dir is not None:
        write_json_atomic(out_dir / "continuation.json", receipt)
    return receipt


__all__ = [
    "SOURCE_ADJACENT_ATTEMPT_SCHEMA",
    "SOURCE_ADJACENT_QUEUE_SCHEMA",
    "SOURCE_ADJACENT_SOLVER_OWNER",
    "SOURCE_ADJACENT_NATIVE_OWNER",
    "SOURCE_ADJACENT_TASK_SCHEMA",
    "TARGET_CONTINUATION_SCHEMA",
    "CumulativeProviderBudgetNotDelegated",
    "build_source_adjacent_candidate_queue",
    "continue_target_conjecture_admission",
    "provider_free_native_adjudicate",
]
