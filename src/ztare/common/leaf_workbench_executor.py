from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

from ztare.common.control_state_machine import (
    control_receipt_payloads,
    control_receipt_rows,
    executed_morphism_ids_from_receipts,
)
from ztare.common.leaf_workbench_contract import (
    leaf_workbench_action_request_object,
    render_leaf_workbench_control_rules,
    validate_leaf_workbench_action_request,
)
from ztare.common.science_output_policy import SCIENCE_OUTPUT_POLICY
from ztare.common.sealed_boundary_cegar import boundary_cegar_candidate_delta_lowerability
from ztare.common.structured_blocks import json_objects_after_marker
from ztare.common.visible_workbench_actions import is_visible_workbench_local_diagnostic_receipt


_DEFAULT_STATELESS_LEAF_ACTIONS = frozenset(
    {
        "check_worldmodel_carrier_contract",
        "run_visible_json_probe",
        "run_strategy_required_gate",
        "run_structural_isomorphism",
    }
)

_DEFAULT_CANDIDATE_BOUND_LEAF_ACTIONS = frozenset(
    {
        "check_worldmodel_carrier_contract",
        "run_strategy_required_gate",
        "score_worldmodel_candidate_delta",
    }
)


def candidate_bound_leaf_actions() -> frozenset[str]:
    try:
        from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment

        env = resolve_leaf_workbench_environment("worldmodel")
        return frozenset(str(item) for item in (env.get("candidate_bound_actions") or ()) if str(item))
    except Exception:  # noqa: BLE001
        return _DEFAULT_CANDIDATE_BOUND_LEAF_ACTIONS


def leaf_workbench_action_request_retry_message(
    *,
    enabled: bool,
    project_dir: str | Path,
    thesis_text: str,
    candidate_source: str = "",
    contract: Any | None = None,
    records_fn: Callable[[str | Path], list[dict[str, Any]]] | None = None,
    action_handlers: dict[str, Callable[[str | Path, dict[str, Any], dict[str, Any] | None, Any], dict[str, Any]]] | None = None,
    stateless_actions: set[str] | frozenset[str] | None = None,
    chain_followups: bool = True,
) -> str | None:
    """Execute registered workbench action requests under the parent kernel."""

    if not enabled:
        return None
    requests = json_objects_after_marker(thesis_text or "", "LEAF_WORKBENCH_ACTION_REQUEST:")
    if not requests:
        return None
    if contract is None or records_fn is None:
        try:
            from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment

            env = resolve_leaf_workbench_environment("worldmodel")
            contract = contract or env["contract"]
            records_fn = records_fn or env["records_fn"]
            action_handlers = action_handlers or env.get("action_handlers") or {}
            stateless_actions = stateless_actions or env.get("stateless_actions") or _DEFAULT_STATELESS_LEAF_ACTIONS
        except Exception:
            return None
    action_handlers = action_handlers or {}
    stateless_actions = stateless_actions or _DEFAULT_STATELESS_LEAF_ACTIONS
    records = records_fn(project_dir)
    current_action_ids = _current_leaf_action_ids(records)
    receipt_lines: list[str] = []
    for raw in requests:
        req = validate_leaf_workbench_action_request(raw, contract)
        req = _bind_current_candidate_to_leaf_action_request(
            project_dir=project_dir,
            request=req,
            candidate_source=candidate_source,
        )
        cap = str(req.get("capability_id") or "")
        row = next((r for r in records if r.get("capability_id") == cap), None)
        if cap not in stateless_actions and row is None:
            return leaf_action_not_current_message(cap, current_action_ids)
        handler = action_handlers.get(cap)
        if handler is not None:
            try:
                receipt = handler(project_dir, req, row, contract)
            except Exception as exc:  # noqa: BLE001
                return (
                    "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: "
                    f"{cap} failed before candidate evaluation: {exc}. "
                    "Return a corrected action request, consume a matching cached "
                    "receipt, or emit LOWERABILITY_BLOCKED if this observation "
                    "surface is insufficient."
                )
        else:
            if row is None:
                return leaf_action_not_current_message(cap, current_action_ids)
            receipt = {
                "capability_id": cap,
                "input_hashes": {
                    "source_ref": str(row.get("source_ref") or ""),
                    "source_sha": str(row.get("source_sha") or ""),
                    "request": _short_json(req),
                },
                "output_summary": str(row.get("summary") or ""),
                "claim_bindings": req.get("claim_bindings") or [f"requested {cap}"],
                "contract_sha256": contract.fingerprint(),
            }
        receipt.setdefault("capability_id", cap)
        receipt.setdefault("claim_bindings", req.get("claim_bindings") or [f"requested {cap}"])
        receipt.setdefault("contract_sha256", contract.fingerprint())
        _stamp_leaf_workbench_action_receipt(project_dir, cap, req, receipt, contract)
        receipt_lines.append(
            "LEAF_WORKBENCH_RECEIPT: "
            + json.dumps(receipt, sort_keys=True, separators=(",", ":"))
        )
    if chain_followups and receipt_lines:
        chain = execute_unique_boundary_morphism_chain(
            project_dir=project_dir,
            thesis_text=(thesis_text or "") + "\n" + "\n".join(receipt_lines),
            candidate_source=candidate_source,
            contract=contract,
            records_fn=records_fn,
            action_handlers=action_handlers,
            stateless_actions=stateless_actions,
        )
        if chain is not None:
            receipt_lines.extend(leaf_workbench_receipt_lines(chain))
            return (
                "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested "
                "registered workbench action(s) and unique boundary follow-up "
                "morphism(s). Free retry after kernel-retained receipt(s); "
                "submit a candidate only if the receipt family admits lowering.\n"
                + "\n".join(receipt_lines)
            )
    if receipt_lines:
        ready_receipts = _workbench_evidence_receipts_json("\n".join(receipt_lines))
        if boundary_cegar_candidate_delta_lowerability(ready_receipts) is False:
            return (
                "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested "
                "registered workbench action(s). WORKBENCH_OBSERVATION_YIELD_EXHAUSTED: "
                "the receipt family still exposes no gamma-lowerable candidate "
                "and no deterministic follow-up morphism is available. Free retry: "
                "submit LOWERABILITY_BLOCKED with visible_capabilities_attempted, "
                "candidate_family_attempted, obstruction, missing_witness_or_sensor, "
                "next_action, and evidence_refs; do not request another observation "
                "for the same boundary unless a new receipt changes lowerability "
                "state or label coverage.\n"
                + "\n".join(receipt_lines)
            )
    return (
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested registered "
        "workbench action(s). Free retry after kernel-retained receipt(s); do "
        "not re-request the same action unless the candidate/evidence changed.\n"
        + "\n".join(receipt_lines)
    )


def leaf_workbench_receipt_preflight_message(
    *,
    project_dir: str | Path | None,
    thesis_text: str,
    candidate_source: str = "",
    fact_markers: tuple[str, ...] = (),
    contract: Any | None = None,
    records_fn: Callable[[str | Path], list[dict[str, Any]]] | None = None,
    action_handlers: dict[str, Callable[[str | Path, dict[str, Any], dict[str, Any] | None, Any], dict[str, Any]]] | None = None,
    stateless_actions: set[str] | frozenset[str] | None = None,
) -> str | None:
    """Check workbench receipt binding without owning candidate authority."""

    combined = f"{thesis_text}\n{candidate_source}"
    typed_rows = control_receipt_rows(combined)
    has_typed_control = any(
        str(row.get("type") or "") in {
            "LEAF_WORKBENCH_RECEIPT",
            "VISIBLE_WORKBENCH_DIAGNOSTIC",
            "LEAF_WORKBENCH_CAPABILITY_PROPOSAL",
        }
        for row in typed_rows
    )
    if project_dir is not None and has_typed_control:
        provenance_error = _leaf_workbench_receipt_provenance_error(
            project_dir=project_dir,
            thesis_text=combined,
            current_submits_candidate=bool(str(candidate_source or "").strip()),
            candidate_source=candidate_source,
            contract=contract,
            records_fn=records_fn,
            action_handlers=action_handlers,
            stateless_actions=stateless_actions,
        )
        return provenance_error
    if has_typed_control:
        return None

    if (
        "LEAF_WORKBENCH_RECEIPT" in combined
        or "VISIBLE_WORKBENCH_DIAGNOSTIC" in combined
        or "LEAF_WORKBENCH_CAPABILITY_PROPOSAL" in combined
    ):
        return (
            "LEAF_WORKBENCH_RECEIPT_PRECHECK: workbench receipts must be emitted "
            "through typed JSON `control_receipts`, not prose, YAML, or Python "
            "variables inside `test_model_py`. "
            + render_leaf_workbench_control_rules(include_capability_proposal_rule=True)
        )

    if project_dir is not None and str(candidate_source or "").strip():
        receipt_refs = referenced_workbench_receipt_identities(
            project_dir=project_dir,
            thesis_text=thesis_text,
        )
        if receipt_refs:
            return (
                "LEAF_WORKBENCH_RECEIPT_PRECHECK: candidate cites stored "
                f"workbench receipt identity {receipt_refs[:4]} but carries no "
                "typed workbench evidence receipt. A stored diagnostic receipt "
                "may guide a hypothesis only when the submission carries the "
                "typed receipt object in `control_receipts`; otherwise the "
                "claim is unbound prose."
            )

    markers = tuple(str(marker).lower() for marker in fact_markers if str(marker).strip())
    if not markers:
        return None
    lower = str(thesis_text or "").lower()
    hits = [marker for marker in markers if marker in lower]
    if not hits:
        return None
    return (
        "LEAF_WORKBENCH_RECEIPT_PRECHECK: candidate uses workbench-backed "
        f"facts {hits} but includes no typed workbench evidence receipt. Free-form "
        "hypotheses are allowed, but patch-base, residual-quotient, replay-probe, "
        "Strategy-receipt, and candidate-delta claims must cite a typed "
        "LEAF_WORKBENCH_RECEIPT or VISIBLE_WORKBENCH_DIAGNOSTIC in "
        "`control_receipts` with capability_id, input_hashes, output_summary "
        "or output_ref, and claim_bindings. If the "
        "needed action is missing, emit LOWERABILITY_BLOCKED. "
        + SCIENCE_OUTPUT_POLICY.tool_gap_text()
    )


def execute_unique_boundary_morphism_chain(
    *,
    project_dir: str | Path,
    thesis_text: str,
    candidate_source: str = "",
    contract: Any | None = None,
    records_fn: Callable[[str | Path], list[dict[str, Any]]] | None = None,
    action_handlers: dict[str, Callable[[str | Path, dict[str, Any], dict[str, Any] | None, Any], dict[str, Any]]] | None = None,
    stateless_actions: set[str] | frozenset[str] | None = None,
    max_steps: int = 4,
) -> str | None:
    state_text = thesis_text or ""
    messages: list[str] = []
    for _ in range(max_steps):
        if boundary_cegar_candidate_delta_lowerability(_workbench_evidence_receipts_json(state_text)) is True:
            break
        morphism = next_strategy_boundary_morphism(project_dir, state_text)
        if morphism is None:
            break
        message = _execute_boundary_morphism_once(
            project_dir=project_dir,
            morphism=morphism,
            candidate_source=candidate_source,
            contract=contract,
            records_fn=records_fn,
            action_handlers=action_handlers,
            stateless_actions=stateless_actions,
        )
        if message is None:
            break
        receipt_lines = leaf_workbench_receipt_lines(message)
        if not receipt_lines:
            break
        messages.append(message)
        state_text += "\n" + message
    if not messages:
        return None
    return (
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed unique boundary "
        "morphism chain. Free retry after kernel-retained receipt(s); submit a "
        "candidate only if the receipt family admits lowering.\n"
        + "\n".join(
            line for message in messages for line in leaf_workbench_receipt_lines(message)
        )
    )


def blocked_strategy_discharge_wants_boundary_morphism(receipts: list[dict[str, Any]]) -> bool:
    """Return whether a blocked Strategy receipt should compile to a workbench morphism."""

    for receipt in receipts:
        if str(receipt.get("blocker_kind") or "").strip() == "missing_evidence":
            return True
        next_action = receipt.get("next_action")
        text = json.dumps(next_action, sort_keys=True, default=str) if isinstance(next_action, (dict, list)) else str(next_action or "")
        lowered = text.lower()
        if "boundary" in lowered or "workbench" in lowered or "morphism" in lowered:
            return True
    return False


def next_strategy_boundary_morphism(project_dir: str | Path, thesis_text: str) -> dict[str, Any] | None:
    executed = executed_morphism_ids_from_receipts(thesis_text or "")
    ready_receipts = _workbench_evidence_receipts_json(thesis_text or "")
    lowerable = boundary_cegar_candidate_delta_lowerability(ready_receipts)
    if lowerable is True:
        return None
    if (
        lowerable is False
        and "mine_worldmodel_global_carrier_selectors_from_observable_context" in executed
        and "cell_local_lowerable_carrier_selector_miner" not in executed
    ):
        return {
            "capability_id": "cell_local_lowerable_carrier_selector_miner",
            "input_refs": {"strategy_gate_receipt_ref": "workspace/latest_level_transfer_probe.json"},
            "claim_bindings": ["refine the no-lowerable selector receipt with per-cell component topology"],
        }
    if (
        "run_strategy_required_gate" in executed
        and "mine_worldmodel_global_carrier_selectors_from_observable_context" not in executed
    ):
        strategy = _open_strategy_receipt_morphism(project_dir)
        if strategy is not None:
            return strategy

    task = latest_workbench_task(project_dir)
    caps = [str(row).strip() for row in (task.get("admissible_capability_ids") or []) if str(row).strip()]
    unique_caps = sorted(set(cap for cap in caps if cap not in set(executed)))
    if len(unique_caps) != 1:
        return None
    cap = unique_caps[0]
    input_refs: dict[str, Any] = {"task_ref": "workspace/latest_harness_weakness.json:workbench_task"}
    if cap in candidate_bound_leaf_actions():
        input_refs["candidate_path"] = "test_model.py"
    return {
        "capability_id": cap,
        "input_refs": input_refs,
        "claim_bindings": [str(task.get("objective") or f"run registered {cap}")],
    }


def required_candidate_bound_action_error(
    *,
    project_dir: str | Path,
    thesis_text: str,
    candidate_source: str = "",
    carrier_is_executable: bool,
) -> str | None:
    if carrier_is_executable:
        return None
    task = latest_workbench_task(project_dir)
    caps = task.get("admissible_capability_ids")
    if not isinstance(caps, list):
        return None
    required = next((str(cap).strip() for cap in caps if str(cap).strip() in candidate_bound_leaf_actions()), "")
    if not required:
        return None
    requests = json_objects_after_marker(thesis_text or "", "LEAF_WORKBENCH_ACTION_REQUEST:")
    requested_caps = {str(row.get("capability_id") or "").strip() for row in requests if isinstance(row, dict)}
    if required in requested_caps:
        return None
    action_request = leaf_workbench_action_request_object(
        capability_id=required,
        input_refs={
            "task_ref": "workspace/latest_harness_weakness.json:workbench_task",
            "candidate_path": "test_model.py",
        },
        claim_bindings=[str(task.get("objective") or f"run required {required}")],
    )
    return (
        "LEAF_WORKBENCH_RECEIPT_PRECHECK: current boundary requires a "
        f"candidate-bound workbench action `{required}` before carrier "
        "evaluation. Submit the typed action request first; the kernel will "
        "bind it to the current carrier bytes and return a receipt on the free "
        "retry. "
        + render_leaf_workbench_control_rules(action_request=action_request)
    )


def replay_candidate_bound_leaf_receipt_for_current_candidate(
    *,
    project_dir: str | Path,
    receipt: dict[str, Any],
    input_hashes: dict[str, Any],
    candidate_source: str,
    contract: Any | None = None,
    records_fn: Callable[[str | Path], list[dict[str, Any]]] | None = None,
    action_handlers: dict[str, Callable[[str | Path, dict[str, Any], dict[str, Any] | None, Any], dict[str, Any]]] | None = None,
    stateless_actions: set[str] | frozenset[str] | None = None,
) -> str | None:
    cap = str(receipt.get("capability_id") or "").strip()
    if cap not in candidate_bound_leaf_actions() or not str(candidate_source or "").strip():
        return None
    request = candidate_bound_receipt_request_object(receipt, input_hashes)
    if request is None:
        return None
    refs = request.get("input_refs") if isinstance(request.get("input_refs"), dict) else {}
    current_refs = dict(refs)
    for key in ("candidate_identity", "candidate_sha256", "candidate_ref", "requested_candidate_refs"):
        current_refs.pop(key, None)
    current_refs["candidate_path"] = "test_model.py"
    current_request = dict(request)
    current_request["capability_id"] = cap
    current_request["input_refs"] = current_refs
    claim_bindings = current_request.get("claim_bindings")
    if not isinstance(claim_bindings, list) or not claim_bindings:
        current_request["claim_bindings"] = receipt.get("claim_bindings") or [f"replay {cap} for current candidate"]
    message = leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project_dir,
        thesis_text="LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(
            current_request,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ),
        candidate_source=candidate_source,
        contract=contract,
        records_fn=records_fn,
        action_handlers=action_handlers,
        stateless_actions=stateless_actions,
        chain_followups=True,
    )
    if message is None:
        return None
    return message.replace(
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK:",
        "LEAF_WORKBENCH_RECEIPT_PROVENANCE_PRECHECK: stale candidate-bound "
        "receipt normalized; predates content-addressed candidate binding; "
        "replayed the registered action against the current carrier.",
        1,
    )


def candidate_bound_receipt_request_object(receipt: dict[str, Any], input_hashes: dict[str, Any]) -> dict[str, Any] | None:
    request_raw = input_hashes.get("request")
    request: object | None = None
    if isinstance(request_raw, str) and request_raw.strip() and not request_raw.endswith("..."):
        try:
            request = json.loads(request_raw)
        except json.JSONDecodeError:
            request = None
    if isinstance(request, dict) and isinstance(request.get("payload"), dict):
        request = request["payload"]
    if _candidate_bound_request_is_superseded(receipt, input_hashes, request):
        return None
    if isinstance(request, dict):
        return dict(request)
    cap = str(receipt.get("capability_id") or "").strip()
    if not cap:
        return None
    return {
        "capability_id": cap,
        "input_refs": {"candidate_path": "test_model.py"},
        "claim_bindings": receipt.get("claim_bindings") or [f"replay {cap}"],
    }


def _candidate_bound_request_is_superseded(
    receipt: dict[str, Any],
    input_hashes: dict[str, Any],
    request: object | None,
) -> bool:
    """Reject replay of a stale candidate-bound receipt when a newer file exists."""

    receipt_ref = str(input_hashes.get("receipt_ref") or "").strip()
    if not receipt_ref:
        return False
    if not receipt_ref.startswith("workspace/visible_cli_receipts/"):
        return False
    cap = str(receipt.get("capability_id") or "").strip()
    if not cap:
        return False
    candidate_ref = str((request or {}).get("input_refs", {}).get("candidate_path") if isinstance(request, dict) else "").strip()  # type: ignore[union-attr]
    if candidate_ref and candidate_ref != "test_model.py":
        return False
    try:
        path = Path(receipt_ref)
    except Exception:
        return False
    if not path.exists() or not path.is_file():
        return False
    parent = path.parent
    prefix = f"{cap}_"
    matches = sorted(
        [p for p in parent.glob(f"{prefix}*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        return False
    return matches[0].resolve() != path.resolve()


def _leaf_workbench_receipt_provenance_error(
    *,
    project_dir: str | Path,
    thesis_text: str,
    current_submits_candidate: bool,
    candidate_source: str,
    contract: Any | None = None,
    records_fn: Callable[[str | Path], list[dict[str, Any]]] | None = None,
    action_handlers: dict[str, Callable[[str | Path, dict[str, Any], dict[str, Any] | None, Any], dict[str, Any]]] | None = None,
    stateless_actions: set[str] | frozenset[str] | None = None,
) -> str | None:
    receipts = _leaf_workbench_receipt_payloads(thesis_text)
    if not receipts:
        return None
    current_sha = hashlib.sha256(candidate_source.encode("utf-8")).hexdigest()
    for receipt in receipts:
        if is_visible_workbench_local_diagnostic_receipt(receipt):
            continue
        cap = str(receipt.get("capability_id") or "").strip()
        input_hashes = receipt.get("input_hashes") if isinstance(receipt.get("input_hashes"), dict) else {}
        if not _has_valid_receipt_artifact_binding(project_dir, input_hashes):
            if not current_submits_candidate or cap not in candidate_bound_leaf_actions():
                return (
                    "LEAF_WORKBENCH_RECEIPT_PROVENANCE_PRECHECK: self-authored "
                    f"receipt `{cap or '<unknown>'}` is not bound to a kernel "
                    "receipt artifact. request the action through "
                    "LEAF_WORKBENCH_ACTION_REQUEST so the kernel can emit the "
                    "receipt, or cite a hash-bound existing receipt artifact."
                )
        if not current_submits_candidate or not str(candidate_source or "").strip():
            continue
        if cap not in candidate_bound_leaf_actions():
            continue
        candidate_sha = str(
            input_hashes.get("candidate_sha256")
            or input_hashes.get("candidate_sha")
            or input_hashes.get("candidate_identity_sha256")
            or ""
        ).strip()
        if candidate_sha == current_sha:
            continue
        request = candidate_bound_receipt_request_object(receipt, input_hashes)
        request_refs = request.get("input_refs") if isinstance(request, dict) and isinstance(request.get("input_refs"), dict) else {}
        if str(request_refs.get("candidate_identity") or "").strip() == "current_submission":
            continue
        replay = replay_candidate_bound_leaf_receipt_for_current_candidate(
            project_dir=project_dir,
            receipt=receipt,
            input_hashes=input_hashes,
            candidate_source=candidate_source,
            contract=contract,
            records_fn=records_fn,
            action_handlers=action_handlers,
            stateless_actions=stateless_actions,
        )
        if replay is not None:
            return replay
        return (
            "LEAF_WORKBENCH_RECEIPT_PROVENANCE_PRECHECK: candidate-bound "
            f"receipt `{cap}` is not bound to the current carrier bytes. "
            "Run the registered workbench action against the current candidate "
            "or omit the stale receipt before candidate evaluation."
        )
    return None


def _leaf_workbench_receipt_payloads(text: str) -> list[dict[str, Any]]:
    return control_receipt_payloads(
        text or "",
        receipt_types=("LEAF_WORKBENCH_RECEIPT", "VISIBLE_WORKBENCH_DIAGNOSTIC"),
    )


def _workbench_evidence_receipts_json(text: str) -> str:
    rows = [
        row for row in control_receipt_rows(text or "")
        if str(row.get("type") or "") in {"LEAF_WORKBENCH_RECEIPT", "VISIBLE_WORKBENCH_DIAGNOSTIC"}
    ]
    return json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str) if rows else ""


def _has_valid_receipt_artifact_binding(project_dir: str | Path, input_hashes: dict[str, Any]) -> bool:
    key_pairs = (
        ("kernel_receipt_ref", "kernel_receipt_sha256"),
        ("receipt_ref", "receipt_sha256"),
        ("output_ref", "output_sha256"),
    )
    root = Path(project_dir).resolve()
    for ref_key, sha_key in key_pairs:
        ref = str(input_hashes.get(ref_key) or "").strip()
        expected = str(input_hashes.get(sha_key) or "").strip().lower()
        if not ref or not expected:
            continue
        path = (root / ref).resolve()
        try:
            if path != root and root not in path.parents:
                continue
            if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest().lower() == expected:
                return True
        except Exception:
            continue
    return False


def referenced_workbench_receipt_identities(
    *,
    project_dir: str | Path,
    thesis_text: str,
) -> list[str]:
    """Return stored workbench receipt identities cited outside typed receipts."""

    text = str(thesis_text or "")
    if not text.strip():
        return []
    workspace = Path(project_dir) / "workspace" / "leaf_workbench_action_receipts"
    if not workspace.is_dir():
        return []
    lower = text.lower()
    mentioned: list[str] = []
    if "workspace/leaf_workbench_action_receipts/" in lower:
        mentioned.append("workspace/leaf_workbench_action_receipts/")
    hex_tokens = set(re.findall(r"\b[0-9a-fA-F]{64}\b", text))
    if hex_tokens:
        receipt_stems = {
            path.stem for path in workspace.glob("*.json") if len(path.stem) == 64
        }
        mentioned.extend(sorted(hex_tokens & receipt_stems))
    return mentioned


def latest_workbench_task(project_dir: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads((Path(project_dir) / "workspace" / "latest_harness_weakness.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    task = payload.get("workbench_task")
    return task if isinstance(task, dict) else {}


def leaf_workbench_receipt_lines(message: str) -> list[str]:
    return [line for line in str(message or "").splitlines() if line.startswith("LEAF_WORKBENCH_RECEIPT:")]


def leaf_action_not_current_message(capability_id: str, current_action_ids: list[str]) -> str:
    actions = ", ".join(current_action_ids) if current_action_ids else "<none>"
    return (
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: registered_but_not_applicable: "
        f"capability {capability_id!r} is registered in the workbench contract, "
        "but the current project state does not expose a backing artifact or "
        "applicability witness for it. Current applicable action_ids: "
        f"{actions}. Request an applicable action, or emit LOWERABILITY_BLOCKED "
        "if the present residue needs a new observation/action surface."
    )


def _execute_boundary_morphism_once(
    *,
    project_dir: str | Path,
    morphism: dict[str, Any],
    candidate_source: str = "",
    contract: Any | None = None,
    records_fn: Callable[[str | Path], list[dict[str, Any]]] | None = None,
    action_handlers: dict[str, Callable[[str | Path, dict[str, Any], dict[str, Any] | None, Any], dict[str, Any]]] | None = None,
    stateless_actions: set[str] | frozenset[str] | None = None,
) -> str | None:
    action_request = leaf_workbench_action_request_object(
        capability_id=morphism["capability_id"],
        input_refs=morphism["input_refs"],
        claim_bindings=morphism["claim_bindings"],
    )
    action_payload = action_request.get("payload") if isinstance(action_request.get("payload"), dict) else action_request
    return leaf_workbench_action_request_retry_message(
        enabled=True,
        project_dir=project_dir,
        thesis_text="LEAF_WORKBENCH_ACTION_REQUEST: " + json.dumps(action_payload, sort_keys=True, separators=(",", ":"), default=str),
        candidate_source=candidate_source,
        contract=contract,
        records_fn=records_fn,
        action_handlers=action_handlers,
        stateless_actions=stateless_actions,
        chain_followups=False,
    )


def _open_strategy_receipt_morphism(project_dir: str | Path) -> dict[str, Any] | None:
    project = Path(project_dir)
    if not (project / "workspace" / "latest_level_transfer_probe.json").exists():
        return None
    try:
        from ztare.common.operator_proposal_contract import open_cards

        cards = open_cards(project / "workspace" / "strategy_experiments.jsonl")
    except Exception:  # noqa: BLE001
        return None
    matching = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        if str(plan.get("source_receipt") or "") == "workspace/latest_level_transfer_probe.json":
            matching.append(card)
    if len(matching) != 1:
        return None
    return {
        "capability_id": "mine_worldmodel_global_carrier_selectors_from_observable_context",
        "input_refs": {
            "strategy_gate_receipt_ref": "workspace/latest_level_transfer_probe.json",
            "source_card_sha": str(matching[0].get("failure_family_sha") or ""),
        },
        "claim_bindings": ["mine lowerable carrier selectors for the open Strategy repair residue"],
    }


def _bind_current_candidate_to_leaf_action_request(*, project_dir: str | Path, request: dict[str, Any], candidate_source: str) -> dict[str, Any]:
    source = (candidate_source or "").strip()
    if not source:
        return request
    input_refs = request.get("input_refs")
    if not isinstance(input_refs, dict):
        return request
    requested_refs = {key: str(input_refs.get(key) or "").strip() for key in ("candidate_path", "candidate_ref") if str(input_refs.get(key) or "").strip()}
    if not requested_refs:
        return request
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    rel = Path("workspace") / "leaf_workbench_action_candidates" / f"{digest}.py"
    path = Path(project_dir) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        path.write_text(source, encoding="utf-8")
    bound = dict(request)
    bound_refs = dict(input_refs)
    bound_refs.setdefault("requested_candidate_refs", requested_refs)
    bound_refs["candidate_path"] = str(rel)
    bound_refs["candidate_ref"] = str(rel)
    bound_refs["candidate_sha256"] = digest
    bound_refs["candidate_identity"] = "current_submission"
    bound["input_refs"] = bound_refs
    return bound


def _stamp_leaf_workbench_action_receipt(project_dir: str | Path, capability_id: str, request: dict[str, Any], receipt: dict[str, Any], contract: Any) -> None:
    input_hashes = receipt.setdefault("input_hashes", {})
    if not isinstance(input_hashes, dict):
        input_hashes = {}
        receipt["input_hashes"] = input_hashes
    canonical = {
        "schema": "ztare-leaf-workbench-kernel-receipt-v1",
        "capability_id": capability_id,
        "contract_sha256": contract.fingerprint(),
        "request": request,
        "receipt": receipt,
    }
    data = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    rel = Path("workspace") / "leaf_workbench_action_receipts" / f"{digest}.json"
    path = Path(project_dir) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    input_hashes["kernel_receipt_ref"] = str(rel)
    input_hashes["kernel_receipt_sha256"] = digest


def _current_leaf_action_ids(records: list[dict[str, object]]) -> list[str]:
    return sorted({str(row.get("capability_id") or "").strip() for row in records if str(row.get("capability_id") or "").strip()})


def _short_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)[:500]
