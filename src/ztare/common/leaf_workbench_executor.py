from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import Any, Callable

from ztare.common.artifact_refs import (
    collect_artifact_refs,
    collect_artifact_refs_from_text,
    project_ref_requires_resolution,
    resolve_project_artifact_ref,
)
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

_TASK_SCOPE_EXEMPT_ACTIONS = frozenset(
    {
        "check_worldmodel_carrier_contract",
        "check_receipt_compatibility",
        "score_worldmodel_candidate_delta",
        "route_action",
        "rank_next_morphisms",
    }
)


def _handler_implementation_sha256(handler: Callable[..., Any] | None) -> str:
    """Content identity for a registered action implementation.

    Kernel receipts are execution caches as well as evidence.  Binding only
    the request and action name lets a receipt survive a repaired handler and
    silently suppress its first fire.  Hash the owning module bytes when they
    are visible; source text is the fallback for dynamically defined tests.
    """

    if handler is None:
        return ""
    try:
        module = inspect.getmodule(handler)
        module_path = Path(str(getattr(module, "__file__", "") or ""))
        if module_path.is_file():
            return hashlib.sha256(module_path.read_bytes()).hexdigest()
    except (OSError, TypeError, ValueError):
        pass
    try:
        source = inspect.getsource(handler)
    except (OSError, TypeError):
        source = repr(handler)
    return hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest()


def _input_artifact_bindings_are_current(
    project_dir: str | Path,
    input_hashes: dict[str, Any],
) -> bool:
    """Whether a cached receipt still names the bytes its producer consumed.

    Handlers already emit ``*_ref``/``*_sha256`` pairs.  Reuse must respect
    those identities: a task and handler can remain unchanged while an episode,
    proof, dataset, or prose artifact grows.  The common executor understands
    only project artifact bindings; substrate interpretation stays in handlers.
    """

    for ref_key, ref in input_hashes.items():
        if not str(ref_key).endswith("_ref"):
            continue
        sha_key = str(ref_key)[:-4] + "_sha256"
        expected = str(input_hashes.get(sha_key) or "").strip().lower()
        if not expected or not project_ref_requires_resolution(ref):
            continue
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            return False
        path = resolve_project_artifact_ref(project_dir, ref)
        try:
            if path is None or not path.is_file():
                return False
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                return False
        except OSError:
            return False
    return True


def workbench_task_operational_exit_capability_ids() -> frozenset[str]:
    """Actions that validate or submit work without acquiring sibling evidence."""

    return _TASK_SCOPE_EXEMPT_ACTIONS


def candidate_bound_leaf_actions() -> frozenset[str]:
    try:
        from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment

        env = resolve_leaf_workbench_environment("worldmodel")
        return frozenset(str(item) for item in (env.get("candidate_bound_actions") or ()) if str(item))
    except Exception:  # noqa: BLE001
        return _DEFAULT_CANDIDATE_BOUND_LEAF_ACTIONS


def active_workbench_task_capability_scope(
    project_dir: str | Path,
    *,
    adapter_id: str = "worldmodel",
) -> tuple[frozenset[str], dict[str, Any]]:
    """Return the identity-bound evidence-action scope for the active task.

    Candidate syntax checks, receipt checks, and aggregate scoring remain
    available as operational exits.  Evidence acquisition is restricted to
    the task-declared capability set only while the task's carrier digest still
    identifies a visible source.
    """

    project = Path(project_dir)
    payload = _latest_workbench_weakness_payload(project)
    if not payload:
        return frozenset(), {}
    task = payload.get("workbench_task")
    if not isinstance(task, dict):
        return frozenset(), {}
    caps = frozenset(
        str(cap).strip()
        for cap in (task.get("admissible_capability_ids") or [])
        if str(cap).strip()
    )
    if not caps:
        return frozenset(), {}

    frontier = payload.get("active_frontier")
    frontier = frontier if isinstance(frontier, dict) else {}
    bound_sha = str(
        task.get("source_sha256")
        or frontier.get("candidate_sha")
        or payload.get("candidate_sha")
        or ""
    ).strip().lower()
    source_refs = [
        str(task.get("source_ref") or "").strip(),
        str(frontier.get("source_ref") or "").strip(),
    ]
    visible_digests: list[str] = []
    for ref in source_refs:
        if not ref:
            continue
        try:
            path = resolve_project_artifact_ref(project, ref)
            if path is not None and path.is_file():
                visible_digests.append(hashlib.sha256(path.read_bytes()).hexdigest())
        except (OSError, ValueError):
            continue
    if bound_sha:
        if len(bound_sha) != 64 or bound_sha not in visible_digests:
            return frozenset(), {}
    elif not visible_digests:
        return frozenset(), {}

    # Task lifecycle is adapter-owned because "successor" means something
    # different for executable carriers, proof objects, prose artifacts, and
    # other substrates.  The common door owns only the task/capability
    # identity.  An adapter may close that scope only from an identity-bearing
    # consequence (for world models: validated carrier ancestry plus a
    # promotion receipt), never from a mutable status field.
    try:
        from ztare.common.leaf_workbench_environment import (
            resolve_leaf_workbench_environment,
        )

        environment = resolve_leaf_workbench_environment(adapter_id)
        identity_status_fn = environment.get("task_identity_status_fn")
        if callable(identity_status_fn):
            status = identity_status_fn(project, payload, task)
            if isinstance(status, dict) and status.get("active") is False:
                return frozenset(), {}
    except Exception:  # noqa: BLE001
        # Adapter lifecycle failure cannot authorize continued forcing.  The
        # visible receipt remains evidence, but no action is compulsory until
        # its owner can re-establish that the task identity is active.
        return frozenset(), {}
    return caps, task


def active_workbench_task_scope_error(
    project_dir: str | Path,
    capability_id: str,
) -> str | None:
    """Return a structural route error for an out-of-scope evidence action."""

    cap = str(capability_id or "").strip()
    scope, task = active_workbench_task_capability_scope(project_dir)
    if not scope or cap in scope or cap in _TASK_SCOPE_EXEMPT_ACTIONS:
        return None
    allowed = ",".join(sorted(scope))
    return (
        f"active workbench task {task.get('task_id') or '<unidentified>'} "
        f"admits evidence actions [{allowed}]; requested {cap!r} is outside "
        "that task scope. Execute an admitted action, then use carrier/receipt "
        "checks or aggregate scoring as needed."
    )


def active_workbench_task_first_fire_receipt(
    project_dir: str | Path,
    *,
    adapter_id: str = "worldmodel",
    materialize: bool = False,
) -> dict[str, Any] | None:
    """Compatibility view of the first transition in the task program."""

    cached = active_workbench_task_receipt_family(
        project_dir,
        adapter_id=adapter_id,
        materialize=False,
    )
    if not cached and materialize:
        cached = active_workbench_task_receipt_family(
            project_dir,
            adapter_id=adapter_id,
            materialize=True,
            max_steps=1,
        )
    return next(iter(cached.values()), None)


def active_workbench_task_receipt_family(
    project_dir: str | Path,
    *,
    adapter_id: str = "worldmodel",
    materialize: bool = False,
    max_steps: int | None = None,
) -> dict[str, dict[str, Any]]:
    """Return the ordered, implementation-current receipt family for a task.

    A multi-stage CEGAR route is one program, not several unrelated cached
    diagnostics.  This door resumes from current task-bound receipts, threads
    their refs into later morphisms, and exposes the resulting family to a
    deterministic compiler without asking the model to serialize it again.
    """

    project = Path(project_dir)
    scope, task = active_workbench_task_capability_scope(
        project,
        adapter_id=adapter_id,
    )
    task_id = str(task.get("task_id") or "").strip()
    if not scope or not task_id:
        return {}
    sequence = [
        str(capability_id).strip()
        for capability_id in (task.get("morphism_sequence") or [])
        if str(capability_id).strip() in scope
    ] or sorted(scope)

    def current() -> dict[str, dict[str, Any]]:
        family: dict[str, dict[str, Any]] = {}
        required_upstream_refs: list[str] = []
        for capability_id in sequence:
            receipt = _task_bound_kernel_receipt(
                project,
                task_id=task_id,
                capability_id=capability_id,
                adapter_id=adapter_id,
            )
            if receipt is None:
                break
            input_hashes = receipt.get("input_hashes")
            input_hashes = input_hashes if isinstance(input_hashes, dict) else {}
            carried_upstream_refs = {
                str(ref).strip()
                for ref in (input_hashes.get("upstream_receipt_refs") or [])
                if str(ref).strip()
            }
            if required_upstream_refs and not set(required_upstream_refs).issubset(
                carried_upstream_refs
            ):
                break
            family[capability_id] = receipt
            kernel_ref = str(input_hashes.get("kernel_receipt_ref") or "").strip()
            if kernel_ref:
                required_upstream_refs.append(kernel_ref)
        return family

    receipts = current()
    if not materialize or len(receipts) == len(sequence):
        return receipts
    state_text = "\n".join(
        "LEAF_WORKBENCH_RECEIPT: "
        + json.dumps(receipts[capability_id], sort_keys=True, separators=(",", ":"))
        for capability_id in sequence
        if capability_id in receipts
    )
    try:
        from ztare.common.leaf_workbench_environment import (
            resolve_leaf_workbench_environment,
        )

        environment = resolve_leaf_workbench_environment(adapter_id)
        execute_unique_boundary_morphism_chain(
            project_dir=project,
            thesis_text=state_text,
            contract=environment["contract"],
            records_fn=environment["records_fn"],
            action_handlers=environment.get("action_handlers") or {},
            stateless_actions=(
                environment.get("stateless_actions")
                or _DEFAULT_STATELESS_LEAF_ACTIONS
            ),
            max_steps=max(1, min(len(sequence), max_steps or len(sequence))),
        )
    except Exception:  # noqa: BLE001
        return current()
    return current()


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
        scope_error = active_workbench_task_scope_error(project_dir, cap)
        if scope_error:
            return "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: " + scope_error
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
            input_hashes = receipt.setdefault("input_hashes", {})
            if not isinstance(input_hashes, dict):
                input_hashes = {}
                receipt["input_hashes"] = input_hashes
            input_hashes["handler_implementation_sha256"] = (
                _handler_implementation_sha256(handler)
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
        route_production = receipt.pop("_route_production", None)
        receipt.setdefault("capability_id", cap)
        receipt.setdefault("claim_bindings", req.get("claim_bindings") or [f"requested {cap}"])
        receipt.setdefault("contract_sha256", contract.fingerprint())
        kernel_ref, kernel_sha = _stamp_leaf_workbench_action_receipt(
            project_dir, cap, req, receipt, contract
        )
        if isinstance(route_production, dict):
            _admit_task_bound_route_production(
                project_dir=project_dir,
                capability_id=cap,
                request=req,
                production=route_production,
                kernel_receipt_ref=kernel_ref,
                kernel_receipt_sha256=kernel_sha,
            )
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
        from ztare.common.sealed_boundary_cegar import boundary_cegar_refutation_scopes

        refuted_scopes = boundary_cegar_refutation_scopes(ready_receipts)
        if any(row.get("scope_kind") == "candidate_family" for row in refuted_scopes):
            return (
                "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed requested "
                "registered workbench action(s). WORKBENCH_OBSERVATION_YIELD_EXHAUSTED: "
                "the named diagnostic family produced no admissible member and no "
                "deterministic follow-up morphism is available. "
                + SCIENCE_OUTPUT_POLICY.local_stopping_text()
                + "\n"
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
        has_kernel_refs, kernel_ref_error = _referenced_workbench_receipt_error(
            project_dir=project_dir,
            thesis_text=thesis_text,
            candidate_source=candidate_source,
        )
        if kernel_ref_error is not None:
            return kernel_ref_error
        if has_kernel_refs:
            return None

    markers = tuple(str(marker).lower() for marker in fact_markers if str(marker).strip())
    if not markers:
        return None
    lower = str(thesis_text or "").lower()
    hits = [marker for marker in markers if marker in lower]
    if not hits:
        return None
    return (
        "LEAF_WORKBENCH_RECEIPT_PRECHECK: candidate uses workbench-backed "
        f"facts {hits} but includes no parent-verifiable workbench receipt. Free-form "
        "hypotheses are allowed, but patch-base, residual-quotient, replay-probe, "
        "Strategy-receipt, and candidate-delta claims must cite a typed "
        "LEAF_WORKBENCH_RECEIPT/VISIBLE_WORKBENCH_DIAGNOSTIC or a kernel-retained "
        "receipt artifact through structured evidence refs. If the "
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
            # The selected morphism reached its executor but failed before it
            # could mint a receipt.  Preserve that failure as the free-retry
            # consequence; returning None would accept the original block and
            # erase the parent action's result.
            return message
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


def blocked_control_receipts_want_boundary_morphism(
    receipts: list[dict[str, Any]],
    *,
    admitted_capability_ids: frozenset[str] = frozenset(),
) -> bool:
    """Return whether a typed control block selects an available morphism."""

    if selected_control_boundary_morphism(
        receipts,
        admitted_capability_ids=admitted_capability_ids,
    ) is not None:
        return True

    for receipt in receipts:
        if str(receipt.get("blocker_kind") or "").strip() == "missing_evidence":
            return True
        next_action = receipt.get("next_action")
        text = json.dumps(next_action, sort_keys=True, default=str) if isinstance(next_action, (dict, list)) else str(next_action or "")
        lowered = text.lower()
        if "boundary" in lowered or "workbench" in lowered or "morphism" in lowered:
            return True
    return False


def selected_control_boundary_morphism(
    receipts: list[dict[str, Any]],
    *,
    admitted_capability_ids: frozenset[str],
) -> str | None:
    """Return the unique admitted capability explicitly selected by a block.

    The active task may admit several actions.  A block's ``next_action`` is a
    control decision over that set; discarding it and falling back to a
    singleton-set heuristic erases the selected morphism precisely when the
    task exposes a useful multi-step workbench.
    """

    selected: set[str] = set()
    for receipt in receipts:
        next_action = receipt.get("next_action")
        text = (
            json.dumps(next_action, sort_keys=True, default=str)
            if isinstance(next_action, (dict, list))
            else str(next_action or "")
        )
        selected.update(
            capability_id
            for capability_id in admitted_capability_ids
            if capability_id and capability_id in text
        )
    if len(selected) != 1:
        return None
    return next(iter(selected))


def next_strategy_boundary_morphism(project_dir: str | Path, thesis_text: str) -> dict[str, Any] | None:
    executed = executed_morphism_ids_from_receipts(thesis_text or "")
    ready_receipts_json = _workbench_evidence_receipts_json(thesis_text or "")
    ready_receipts = _leaf_workbench_receipt_payloads(thesis_text or "")
    upstream_receipt_refs: list[str] = []
    for receipt in ready_receipts:
        if not isinstance(receipt, dict):
            continue
        input_hashes = receipt.get("input_hashes")
        if not isinstance(input_hashes, dict):
            continue
        ref = str(input_hashes.get("kernel_receipt_ref") or "").strip()
        if ref and ref not in upstream_receipt_refs:
            upstream_receipt_refs.append(ref)
    lowerable = boundary_cegar_candidate_delta_lowerability(ready_receipts_json)
    task = latest_workbench_task(project_dir)
    caps = [str(row).strip() for row in (task.get("admissible_capability_ids") or []) if str(row).strip()]
    sequence = [
        str(row).strip()
        for row in (task.get("morphism_sequence") or [])
        if str(row).strip()
    ]
    # A declared task program owns its lifecycle through the final consumer.
    # An intermediate receipt may already describe a lowerable conjecture, but
    # that property cannot substitute for the remaining typed transition.
    if sequence:
        for cap in sequence:
            if cap not in executed:
                input_refs: dict[str, Any] = {
                    "task_ref": "workspace/latest_harness_weakness.json:workbench_task",
                    "task_id": str(task.get("task_id") or ""),
                }
                if upstream_receipt_refs:
                    input_refs["upstream_receipt_refs"] = upstream_receipt_refs
                if cap in candidate_bound_leaf_actions():
                    input_refs["candidate_path"] = "test_model.py"
                return {
                    "capability_id": cap,
                    "input_refs": input_refs,
                    "claim_bindings": [
                        str(task.get("objective") or f"run registered {cap}")
                    ],
                }
        return None
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
            "claim_bindings": ["refine the no-lowerable selector receipt with adapter-local structural context"],
        }
    if (
        "run_strategy_required_gate" in executed
        and "mine_worldmodel_global_carrier_selectors_from_observable_context" not in executed
    ):
        strategy = _open_strategy_receipt_morphism(project_dir)
        if strategy is not None:
            return strategy

    unique_caps = sorted(set(cap for cap in caps if cap not in set(executed)))
    if len(unique_caps) != 1:
        return None
    cap = unique_caps[0]
    input_refs: dict[str, Any] = {
        "task_ref": "workspace/latest_harness_weakness.json:workbench_task",
        "task_id": str(task.get("task_id") or ""),
    }
    if upstream_receipt_refs:
        input_refs["upstream_receipt_refs"] = upstream_receipt_refs
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


def required_active_task_action_error(
    *,
    project_dir: str | Path,
    thesis_text: str,
    candidate_source: str = "",
) -> str | None:
    """Require one task-admitted evidence receipt before candidate evaluation."""

    if not str(candidate_source or "").strip():
        return None
    scope, task = active_workbench_task_capability_scope(project_dir)
    if not scope:
        return None
    carried = executed_morphism_ids_from_receipts(
        f"{thesis_text or ''}\n{candidate_source or ''}"
    )
    if scope.intersection(carried):
        return None
    if active_workbench_task_first_fire_receipt(project_dir) is not None:
        return None

    # A candidate can improve during an R1 compiler bounce.  That transition
    # changes the content-addressed repair frontier and therefore creates a new
    # evidence-task identity after the iteration-entry first-fire has already
    # run.  Execute the task's selected morphism here, through the same parent
    # action door, and reject the pre-receipt candidate once.  Asking the leaf
    # to restate this deterministic control transition wastes a model call and
    # lets a field-name typo erase the producer -> consumer edge.
    first_fire = active_workbench_task_first_fire_receipt(
        project_dir,
        materialize=True,
    )
    if first_fire is not None:
        return (
            "LEAF_WORKBENCH_RECEIPT_PRECHECK: active evidence task "
            f"{task.get('task_id') or '<unidentified>'} changed with the repair "
            "frontier; the parent kernel first-fired its selected registered "
            "morphism. The current pre-receipt candidate is rejected. Free retry "
            "with the kernel-retained receipt below; do not re-request the same "
            "action unless its task or inputs change.\n"
            "LEAF_WORKBENCH_RECEIPT: "
            + json.dumps(first_fire, sort_keys=True, separators=(",", ":"))
        )
    requests = json_objects_after_marker(
        thesis_text or "",
        "LEAF_WORKBENCH_ACTION_REQUEST:",
    )
    requested = {
        str(row.get("capability_id") or "").strip()
        for row in requests
        if isinstance(row, dict)
    }
    if scope.intersection(requested):
        return None

    allowed = sorted(scope)
    suffix = ""
    if len(allowed) == 1:
        action_request = leaf_workbench_action_request_object(
            capability_id=allowed[0],
            input_refs={
                "task_ref": "workspace/latest_harness_weakness.json:workbench_task"
            },
            claim_bindings=[
                str(task.get("objective") or f"run registered {allowed[0]}")
            ],
        )
        suffix = " " + render_leaf_workbench_control_rules(
            action_request=action_request
        )
    return (
        "LEAF_WORKBENCH_RECEIPT_PRECHECK: active evidence task "
        f"{task.get('task_id') or '<unidentified>'} requires a kernel receipt "
        f"from one admitted capability {allowed} before candidate evaluation. "
        "Carrier and receipt checks may follow the evidence action; they do not "
        "substitute for it."
        + suffix
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
        if not _has_valid_receipt_artifact_binding(
            project_dir,
            receipt=receipt,
            input_hashes=input_hashes,
        ):
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


def _has_valid_receipt_artifact_binding(
    project_dir: str | Path,
    *,
    receipt: dict[str, Any],
    input_hashes: dict[str, Any],
) -> bool:
    key_pairs = (
        ("kernel_receipt_ref", "kernel_receipt_sha256"),
        ("receipt_ref", "receipt_sha256"),
        ("output_ref", "output_sha256"),
    )
    root = Path(project_dir).resolve()
    for ref_key, sha_key in key_pairs:
        ref = str(input_hashes.get(ref_key) or receipt.get(ref_key) or "").strip()
        expected = str(
            input_hashes.get(sha_key) or receipt.get(sha_key) or ""
        ).strip().lower()
        if not ref or not expected:
            continue
        if not ref.startswith(
            (
                "workspace/leaf_workbench_action_receipts/",
                "workspace/visible_cli_receipts/",
            )
        ):
            continue
        path = (root / ref).resolve()
        try:
            if path != root and root not in path.parents:
                continue
            if not path.is_file():
                continue
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest().lower() != expected:
                continue
            artifact = json.loads(raw)
            artifact_capability = str(
                artifact.get("capability_id")
                or (artifact.get("receipt") or {}).get("capability_id")
                or ""
            ).strip()
            if artifact_capability != str(receipt.get("capability_id") or "").strip():
                continue
            return True
        except Exception:
            continue
    return False


def _referenced_workbench_receipt_error(
    *,
    project_dir: str | Path,
    thesis_text: str,
    candidate_source: str,
) -> tuple[bool, str | None]:
    """Verify parent-retained receipts cited by a structured control row."""

    refs: list[str] = []
    for row in control_receipt_rows(thesis_text or ""):
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        refs.extend(
            ref
            for ref in collect_artifact_refs(payload)
            if ref.startswith(
                (
                    "workspace/visible_cli_receipts/",
                    "workspace/leaf_workbench_action_receipts/",
                )
            )
        )
    refs.extend(collect_artifact_refs_from_text(f"{thesis_text}\n{candidate_source}"))
    refs = [
        ref
        for ref in refs
        if ref.startswith(
            (
                "workspace/visible_cli_receipts/",
                "workspace/leaf_workbench_action_receipts/",
            )
        )
    ]
    refs = list(dict.fromkeys(refs))
    if not refs:
        return False, None

    current_sha = hashlib.sha256(candidate_source.encode("utf-8")).hexdigest()
    for ref in refs:
        path = resolve_project_artifact_ref(project_dir, ref)
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (AttributeError, OSError, json.JSONDecodeError):
            return True, _incompatible_receipt_ref_message(ref, "missing_or_invalid")
        schema = str(artifact.get("schema") or "")
        receipt_row = artifact.get("receipt")
        receipt = (
            receipt_row.get("payload")
            if schema == "ztare-visible-workbench-cli-receipt-v1"
            and isinstance(receipt_row, dict)
            else receipt_row
            if schema == "ztare-leaf-workbench-kernel-receipt-v1"
            else None
        )
        if not isinstance(receipt, dict):
            return True, _incompatible_receipt_ref_message(ref, "unsupported_or_missing_receipt")
        capability_id = str(receipt.get("capability_id") or artifact.get("capability_id") or "")
        if capability_id not in candidate_bound_leaf_actions():
            continue
        input_hashes = receipt.get("input_hashes") or {}
        receipt_candidate_sha = str(
            input_hashes.get("candidate_sha256")
            or input_hashes.get("candidate_sha")
            or input_hashes.get("candidate_identity_sha256")
            or input_hashes.get("source_sha256")
            or input_hashes.get("source_sha")
            or ""
        ).strip()
        if receipt_candidate_sha != current_sha:
            return True, _incompatible_receipt_ref_message(ref, "candidate_identity_mismatch")
    return True, None


def _incompatible_receipt_ref_message(ref: str, cause: str) -> str:
    return (
        "LEAF_WORKBENCH_RECEIPT_PROVENANCE_PRECHECK: cited kernel-retained "
        "workbench receipt is incompatible with the current carrier; "
        f"failure={ref}:{cause}. Re-run the registered diagnostic for the "
        "current carrier or cite the matching receipt ref."
    )


def latest_workbench_task(project_dir: str | Path) -> dict[str, Any]:
    payload = _latest_workbench_weakness_payload(project_dir)
    task = payload.get("workbench_task")
    return task if isinstance(task, dict) else {}


def _task_bound_kernel_receipt(
    project_dir: str | Path,
    *,
    task_id: str,
    capability_id: str,
    adapter_id: str = "worldmodel",
) -> dict[str, Any] | None:
    expected_handler_sha = ""
    try:
        from ztare.common.leaf_workbench_environment import (
            resolve_leaf_workbench_environment,
        )

        environment = resolve_leaf_workbench_environment(adapter_id)
        handlers = environment.get("action_handlers") or {}
        expected_handler_sha = _handler_implementation_sha256(
            handlers.get(capability_id)
        )
    except Exception:  # noqa: BLE001
        expected_handler_sha = ""
    receipt_dir = Path(project_dir) / "workspace" / "leaf_workbench_action_receipts"
    try:
        paths = sorted(
            (path for path in receipt_dir.glob("*.json") if path.is_file()),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
    except OSError:
        return None
    for path in paths:
        try:
            raw = path.read_bytes()
            artifact = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(artifact, dict):
            continue
        request = artifact.get("request")
        refs = request.get("input_refs") if isinstance(request, dict) else None
        artifact_capability_id = str(
            artifact.get("capability_id") or ""
        ).strip()
        if (
            artifact_capability_id != capability_id
            or not isinstance(refs, dict)
            or str(refs.get("task_id") or "").strip() != task_id
        ):
            continue
        receipt = artifact.get("receipt")
        if not isinstance(receipt, dict):
            continue
        carried = dict(receipt)
        input_hashes = carried.get("input_hashes")
        input_hashes = dict(input_hashes) if isinstance(input_hashes, dict) else {}
        carried_handler_sha = str(
            input_hashes.get("handler_implementation_sha256") or ""
        ).strip()
        if expected_handler_sha and carried_handler_sha != expected_handler_sha:
            continue
        if not _input_artifact_bindings_are_current(project_dir, input_hashes):
            continue
        input_hashes["kernel_receipt_ref"] = str(path.relative_to(project_dir))
        input_hashes["kernel_receipt_sha256"] = hashlib.sha256(raw).hexdigest()
        input_hashes["task_id"] = task_id
        carried["input_hashes"] = input_hashes
        return carried
    return None


def _latest_workbench_weakness_payload(
    project_dir: str | Path,
) -> dict[str, Any]:
    try:
        payload = json.loads((Path(project_dir) / "workspace" / "latest_harness_weakness.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


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
        from ztare.common.strategy_card_roles import active_strategy_cards

        cards = active_strategy_cards(
            project / "workspace" / "strategy_experiments.jsonl"
        )
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


def _stamp_leaf_workbench_action_receipt(
    project_dir: str | Path,
    capability_id: str,
    request: dict[str, Any],
    receipt: dict[str, Any],
    contract: Any,
) -> tuple[str, str]:
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
    return str(rel), digest


def _admit_task_bound_route_production(
    *,
    project_dir: str | Path,
    capability_id: str,
    request: dict[str, Any],
    production: dict[str, Any],
    kernel_receipt_ref: str,
    kernel_receipt_sha256: str,
) -> bool:
    """Admit an adapter production only under the active task lifecycle.

    A diagnostic action can always return a receipt.  Operational authority is
    narrower: the request must name the current task, the action must belong to
    that task, and the immutable parent receipt must already exist.  This is
    the only action-to-schema-route admission door.
    """

    refs = request.get("input_refs")
    refs = refs if isinstance(refs, dict) else {}
    requested_task_id = str(refs.get("task_id") or "").strip()
    scope, task = active_workbench_task_capability_scope(project_dir)
    active_task_id = str(task.get("task_id") or "").strip()
    if (
        not requested_task_id
        or requested_task_id != active_task_id
        or capability_id not in scope
    ):
        return False

    schema_id = str(production.get("schema_id") or "").strip()
    event = str(production.get("event") or "").strip()
    join_values = production.get("join_values")
    payload = production.get("payload")
    if not schema_id or not event or not isinstance(join_values, dict):
        raise ValueError("task-bound route production is incomplete")
    joined = dict(join_values)
    joined["task_id"] = active_task_id
    admitted_payload = dict(payload) if isinstance(payload, dict) else {}
    admitted_payload.update(
        {
            "capability_id": capability_id,
            "kernel_receipt_ref": kernel_receipt_ref,
            "kernel_receipt_sha256": kernel_receipt_sha256,
        }
    )
    from ztare.common.schema_routes import append_schema_route_event

    append_schema_route_event(
        project_dir,
        schema_id=schema_id,
        event=event,
        join_values=joined,
        payload=admitted_payload,
    )
    return True


def _current_leaf_action_ids(records: list[dict[str, object]]) -> list[str]:
    return sorted({str(row.get("capability_id") or "").strip() for row in records if str(row.get("capability_id") or "").strip()})


def _short_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)[:500]
