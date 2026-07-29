"""Execute a leaf-authored theory task through the existing formalize lane.

The campaign leaf owns every mathematical sentence in the task specification.
This module only freezes those bytes, routes them through ``formalize_only``
(the established independent faithfulness firewall), runs the admitted target
through the canonical solver, and replays the returned proof against the exact
admitted statement.  It does not synthesize a theorem statement in host code.
"""
from __future__ import annotations

from contextlib import contextmanager
import re
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from ztare.common.task_discharge import TaskDischargeContract
from ztare.leanmill.formal_task_boundary import (
    FORMALIZATION_CAMPAIGN_TASK_BOUNDARY_RESULT_SCHEMA,
    build_formal_task_faithfulness_receipt,
    formal_task_parameters,
)
from ztare.leanmill.formalization_admission import (
    FormalizationAdmission,
    formalize_only,
)
from ztare.leanmill.lean_source import has_sorry, replace_decl_proof
from ztare.leanmill.solver.closed_artifact import (
    finalized_ratification_eligible,
    governance_ratification_eligible,
)
from ztare.leanmill.theory_ir import content_hash


FORMALIZATION_ROLE_RECEIPT_SCHEMA = (
    "leanmill.formal_task_campaign_role_separation.v1"
)
FORMAL_TASK_ROLE_REGISTRY_SCHEMA = "leanmill.formal_task_campaign_role_registry.v1"
FORMAL_TASK_KERNEL_REPLAY_SCHEMA = "leanmill.formal_task_kernel_replay.v1"
FORMAL_TASK_ROLE_CALL_SCHEMA = "leanmill.formal_task_role_call.v1"
FORMAL_TASK_ATTEMPT_OUTCOME_SCHEMA = (
    "leanmill.formal_task_campaign_attempt_outcome.v1"
)
FORMAL_TASK_IMPORT_ALLOWLIST_SCHEMA = (
    "leanmill.formal_task_import_allowlist.v1"
)

_IMPORT_LINE = re.compile(
    r"^\s*import\s+([A-Za-z_][A-Za-z0-9_'.]*)\s*(?:--.*)?$"
)

FormalizationAdmissionFn = Callable[..., FormalizationAdmission | Mapping[str, Any]]
AdmittedSolverFn = Callable[..., Mapping[str, Any]]
CompileFn = Callable[[str], Any]


class FormalTaskAttemptDidNotClose(RuntimeError):
    """A well-formed attempt that produced no discharge evidence."""


def _task_role_run_tag(
    *, attempt_id: str, role: str, contract: TaskDischargeContract
) -> str:
    """Canonical transport identity for one role firing on one frozen task."""

    if role not in {"formalizer", "faithfulness_reviewer", "lean_solver"}:
        raise ValueError("formal-task transport role is unsupported")
    if not str(attempt_id).strip():
        raise ValueError("formal-task transport attempt identity is empty")
    return f"{attempt_id}:theory-task:{role}:{contract.sha256[:16]}"


def _task_attempt_input_sha256(contract: TaskDischargeContract) -> str:
    """Bind an unavailable role attempt to one frozen task input."""

    parameters = formal_task_parameters(contract)
    return content_hash(
        {
            "contract_sha256": contract.sha256,
            "request_id": parameters["request_id"],
            "context_hash": parameters["context_hash"],
            "task_specification": parameters["task_specification"],
        }
    )


def _mathlib_only_import_receipt(
    contract: TaskDischargeContract,
    source_text: str,
    *,
    stage: str,
) -> dict[str, Any]:
    """Fail closed if an admitted task can see a repository-local theorem.

    A fresh theory task may restate definitions from its frozen context, but it
    may not import a prior campaign theorem and rename it.  Lean declarations
    outside Mathlib are therefore absent from this proof world unless the
    formalizer writes their definitions into the admitted source itself.
    """

    imports: list[str] = []
    for line in str(source_text).splitlines():
        if not re.search(r"\bimport\b", line):
            continue
        match = _IMPORT_LINE.fullmatch(line)
        if match is None:
            raise ValueError("formal-task import command is not in the frozen grammar")
        module = match.group(1)
        if module != "Mathlib" and not module.startswith("Mathlib."):
            raise ValueError(
                "formal-task source imports a module outside the Mathlib allowlist"
            )
        imports.append(module)
    parameters = formal_task_parameters(contract)
    core = {
        "schema": FORMAL_TASK_IMPORT_ALLOWLIST_SCHEMA,
        "contract_sha256": contract.sha256,
        "stage": str(stage),
        "source_sha256": content_hash({"lean_source": str(source_text)}),
        "observed_imports": imports,
        "allowed_import_roots": ["Mathlib"],
        "repo_local_imports": [],
        "quarantined_input_evidence_refs": list(
            parameters["input_evidence_refs"]
        ),
        "status": "mathlib_only",
        "authority": "formal_task_isolated_import_firewall",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _validate_import_allowlist_receipt(
    contract: TaskDischargeContract,
    source_text: str,
    value: Mapping[str, Any],
    *,
    stage: str,
) -> dict[str, Any]:
    expected = _mathlib_only_import_receipt(contract, source_text, stage=stage)
    if dict(value) != expected:
        raise ValueError("formal-task import allowlist receipt does not replay")
    return expected


@contextmanager
def _isolated_formal_task_proof_world():
    """Temporarily remove any warm campaign substrate from verifier routing."""

    from ztare.formal.repl_compile import (
        get_campaign_substrate,
        set_campaign_substrate,
    )

    prior = get_campaign_substrate()
    set_campaign_substrate(None)
    try:
        yield
    finally:
        set_campaign_substrate(prior)


def _admission_task_digest(contract: TaskDischargeContract) -> str:
    digest = str(contract.sha256)
    return digest if digest.startswith("sha256:") else "sha256:" + digest


def _role_descriptor(role: Any, expected_role: str) -> dict[str, Any]:
    config = getattr(role, "config", None)
    if (
        getattr(role, "role", None) != expected_role
        or not str(getattr(role, "agent_id", "")).strip()
        or config is None
    ):
        raise ValueError("formal-task role is not a registered campaign role")
    config_row = {
        "runtime": str(getattr(config, "runtime", "")),
        "model": str(getattr(config, "model", "")),
        "reasoning_effort": str(getattr(config, "reasoning_effort", "")),
        "timeout_seconds": int(getattr(config, "timeout_seconds", 0)),
        "visible_workbench": bool(getattr(config, "visible_workbench", False)),
        "web_research": bool(getattr(config, "web_research", False)),
        "governed_pool": bool(getattr(config, "governed_pool", False)),
        "allow_subscription_failover": bool(
            getattr(config, "allow_subscription_failover", False)
        ),
    }
    if not all(config_row[key] for key in ("runtime", "model", "reasoning_effort")):
        raise ValueError("formal-task campaign role configuration is incomplete")
    return {
        "role": expected_role,
        "agent_id": str(role.agent_id),
        "config": config_row,
        "config_sha256": content_hash(config_row),
    }


def build_formal_task_role_registry_receipt(
    *,
    attempt_id: str,
    campaign_id: str,
    formalizer_role: Any,
    faithfulness_reviewer_role: Any,
    lean_solver_role: Any,
) -> dict[str, Any]:
    """Freeze the three roles selected by the campaign runtime registry."""

    roles = {
        "formalizer": _role_descriptor(formalizer_role, "formalizer"),
        "faithfulness_reviewer": _role_descriptor(
            faithfulness_reviewer_role, "faithfulness_reviewer"
        ),
        "lean_solver": _role_descriptor(lean_solver_role, "lean_solver"),
    }
    agent_ids = {row["agent_id"] for row in roles.values()}
    if len(agent_ids) != 3 or not all(
        str(value).strip() for value in (attempt_id, campaign_id)
    ):
        raise ValueError("formal-task campaign roles are not independent")
    core = {
        "schema": FORMAL_TASK_ROLE_REGISTRY_SCHEMA,
        "attempt_id": str(attempt_id),
        "campaign_id": str(campaign_id),
        "roles": roles,
        "authority": "frontier_campaign_runtime_registry",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _validate_role_registry_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(value)
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    roles = row.get("roles")
    if (
        set(row)
        != {"schema", "attempt_id", "campaign_id", "roles", "authority", "receipt_sha256"}
        or row.get("schema") != FORMAL_TASK_ROLE_REGISTRY_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("authority") != "frontier_campaign_runtime_registry"
        or not isinstance(roles, Mapping)
        or set(roles) != {"formalizer", "faithfulness_reviewer", "lean_solver"}
    ):
        raise ValueError("formal-task campaign role registry receipt is malformed")
    agent_ids: set[str] = set()
    for name, descriptor in roles.items():
        if not isinstance(descriptor, Mapping):
            raise ValueError("formal-task campaign role descriptor is malformed")
        config = descriptor.get("config")
        if (
            set(descriptor) != {"role", "agent_id", "config", "config_sha256"}
            or descriptor.get("role") != name
            or not str(descriptor.get("agent_id") or "")
            or not isinstance(config, Mapping)
            or descriptor.get("config_sha256") != content_hash(dict(config))
        ):
            raise ValueError("formal-task campaign role descriptor changed identity")
        agent_ids.add(str(descriptor["agent_id"]))
    if len(agent_ids) != 3:
        raise ValueError("formal-task campaign roles are not independent")
    return row


def render_formal_task_intent(contract: TaskDischargeContract) -> str:
    """Package the three leaf-authored fields verbatim for the formalize lane."""

    specification = formal_task_parameters(contract)["task_specification"]
    return (
        "Formal target requested by the campaign leaf.\n"
        f"Goal (verbatim): {specification['goal']}\n"
        "The formal statement must expose this observable (verbatim): "
        f"{specification['observable']}\n"
        "The result is non-responsive under this kill condition (verbatim): "
        f"{specification['kill_condition']}\n"
    )


def _context_notes(context: Any, contract: TaskDischargeContract) -> str:
    """Render frozen context bytes without adding a mathematical assertion."""

    parameters = formal_task_parameters(contract)
    presentation = set(parameters["presentation_formula_ids"])
    profiles = [
        row.to_json()
        for row in getattr(context, "formula_profiles", ())
        if getattr(row, "formula_id", None) in presentation
    ]
    base_axioms = [
        row.to_json() for row in getattr(context, "base_axioms", ())
    ]
    signature = getattr(context, "signature", None)
    signature_row = signature.to_json() if hasattr(signature, "to_json") else {}
    frozen = {
        "context_hash": parameters["context_hash"],
        "presentation_formula_ids": parameters["presentation_formula_ids"],
        "signature": signature_row,
        "base_axioms": base_axioms,
        "presentation_profiles": profiles,
    }
    return (
        "Frozen campaign context (machine-rendered; do not infer additional "
        "hypotheses):\n" + str(frozen)
    )


def _load_admission(value: FormalizationAdmission | Mapping[str, Any]) -> FormalizationAdmission:
    if isinstance(value, FormalizationAdmission):
        return FormalizationAdmission.from_json(value.to_json())
    if isinstance(value, Mapping):
        return FormalizationAdmission.from_json(value)
    raise TypeError("formalization admission callback returned the wrong type")


def _role_separation_receipt(
    *,
    contract: TaskDischargeContract,
    attempt_id: str,
    campaign_id: str,
    context_hash: str,
    admission: FormalizationAdmission,
    role_registry_receipt: Mapping[str, Any],
    role_execution_receipts: Mapping[str, Any],
) -> dict[str, Any]:
    registry = _validate_role_registry_receipt(role_registry_receipt)
    if (
        registry["attempt_id"] != attempt_id
        or registry["campaign_id"] != campaign_id
    ):
        raise ValueError("formal-task role registry crossed campaign identity")
    role_rows = registry["roles"]
    executions = _validate_role_execution_receipts(
        contract,
        registry,
        role_execution_receipts,
    )
    core = {
        "schema": FORMALIZATION_ROLE_RECEIPT_SCHEMA,
        "attempt_id": str(attempt_id),
        "campaign_id": str(campaign_id),
        "context_hash": str(context_hash),
        "contract_sha256": contract.sha256,
        "formalization_admission_digest": admission.admission_digest,
        "role_registry_receipt": registry,
        "role_execution_receipts": executions,
        "formalizer_ref": str(role_rows["formalizer"]["agent_id"]),
        "faithfulness_reviewer_ref": str(
            role_rows["faithfulness_reviewer"]["agent_id"]
        ),
        "lean_solver_ref": str(role_rows["lean_solver"]["agent_id"]),
        "separate_author_reviewer": True,
        "authority": "existing_formalization_campaign_role_registry",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _role_call_receipt(
    *,
    contract: TaskDischargeContract,
    descriptor: Mapping[str, Any],
    run_tag: str,
    input_sha256: str,
    output_sha256: str,
    output_schema: str,
    outcome: str,
    execution_timeout_s: int,
    dispatch_calls: list[Mapping[str, Any]],
) -> dict[str, Any]:
    calls = [dict(row) for row in dispatch_calls]
    if not calls:
        raise ValueError(
            f"formal-task {descriptor['role']} produced output without call provenance"
        )
    core = {
        "schema": FORMAL_TASK_ROLE_CALL_SCHEMA,
        "role": str(descriptor["role"]),
        "agent_id": str(descriptor["agent_id"]),
        "config_sha256": str(descriptor["config_sha256"]),
        "contract_sha256": contract.sha256,
        "run_tag": str(run_tag),
        "input_sha256": str(input_sha256),
        "output_sha256": str(output_sha256),
        "output_schema": str(output_schema),
        "outcome": str(outcome),
        "execution_timeout_s": int(execution_timeout_s),
        "dispatch_calls": calls,
        "dispatch_calls_sha256": content_hash(calls),
        "authority": "formal_task_transport_provenance_join",
    }
    if (
        any(not str(value).strip() for value in core.values())
        or type(execution_timeout_s) is not int
        or execution_timeout_s < 1
    ):
        raise ValueError("formal-task role call observation is incomplete")
    return {**core, "receipt_sha256": content_hash(core)}


def _build_role_execution_receipts(
    *,
    contract: TaskDischargeContract,
    registry: Mapping[str, Any],
    admission: FormalizationAdmission,
    raw_solver_result: Mapping[str, Any],
    attempt_id: str,
    formalization_timeout_s: int,
    reviewer_timeout_s: int,
    solver_timeout_s: int,
    dispatch_calls: list[Mapping[str, Any]],
) -> dict[str, Any]:
    roles = registry["roles"]
    calls_by_role = {
        role: [
            dict(call)
            for call in dispatch_calls
            if call.get("role") == role
        ]
        for role in ("formalizer", "faithfulness_reviewer", "lean_solver")
    }
    solve_input = admission.solve_input()
    results = raw_solver_result.get("results")
    primary = results[0] if isinstance(results, list) and results else {}
    solver_outcome = (
        str(primary.get("outcome") or "")
        if isinstance(primary, Mapping)
        else ""
    )
    return {
        "formalizer": _role_call_receipt(
            contract=contract,
            descriptor=roles["formalizer"],
            run_tag=_task_role_run_tag(
                attempt_id=attempt_id,
                role="formalizer",
                contract=contract,
            ),
            input_sha256=content_hash(
                {
                    "intent_text": admission.intent_text,
                    "task_digest": admission.task_digest,
                }
            ),
            output_sha256=admission.admission_digest,
            output_schema=admission.schema,
            outcome=admission.status,
            execution_timeout_s=formalization_timeout_s,
            dispatch_calls=calls_by_role["formalizer"],
        ),
        "faithfulness_reviewer": _role_call_receipt(
            contract=contract,
            descriptor=roles["faithfulness_reviewer"],
            run_tag=_task_role_run_tag(
                attempt_id=attempt_id,
                role="faithfulness_reviewer",
                contract=contract,
            ),
            input_sha256=content_hash(
                {
                    "intent_digest": admission.intent_digest,
                    "source_digest": admission.source_digest,
                }
            ),
            output_sha256=content_hash(admission.faithfulness_checks),
            output_schema="leanmill.formalization_faithfulness_checks.v1",
            outcome="faithful" if admission.faithfulness_checks else "missing",
            execution_timeout_s=reviewer_timeout_s,
            dispatch_calls=calls_by_role["faithfulness_reviewer"],
        ),
        "lean_solver": _role_call_receipt(
            contract=contract,
            descriptor=roles["lean_solver"],
            run_tag=_task_role_run_tag(
                attempt_id=attempt_id,
                role="lean_solver",
                contract=contract,
            ),
            input_sha256=content_hash(
                {
                    "target_name": solve_input.target_name,
                    "source_text": solve_input.source_text,
                    "goal": solve_input.goal,
                }
            ),
            output_sha256=content_hash(dict(raw_solver_result)),
            output_schema=str(
                raw_solver_result.get("schema")
                or "leanmill.solve_adhoc_result.v1"
            ),
            outcome=solver_outcome,
            execution_timeout_s=solver_timeout_s,
            dispatch_calls=calls_by_role["lean_solver"],
        ),
    }


def _validate_transport_dispatch_call(
    descriptor: Mapping[str, Any],
    value: Mapping[str, Any],
    *,
    expected_run_tag: str,
) -> dict[str, Any]:
    row = dict(value)
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    required = {
        "schema", "call_id", "role", "agent_id", "transport_agent_id",
        "run_tag", "runtime", "model", "reasoning_effort",
        "config_sha256", "command_sha256", "prompt_sha256",
        "command_model", "command_reasoning_effort",
        "stdout_sha256", "stderr_sha256", "result_sha256", "session_id",
        "returncode", "timeout_seconds", "reservation_id",
        "reservation_action_id", "reservation_phase", "reservation_resources",
        "charged_reservation", "artifact_path", "authority", "receipt_sha256",
    }
    config = descriptor["config"]
    from ztare.common.llm_runtime import subscription_reasoning_effort

    expected_effort = subscription_reasoning_effort(
        str(config["runtime"]),
        str(config["reasoning_effort"]),
        model=str(config["model"]),
    )
    resources = row.get("reservation_resources")
    artifact = Path(str(row.get("artifact_path") or ""))
    try:
        frozen = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("formal-task dispatch provenance artifact is unavailable") from exc
    if (
        set(row) != required
        or row.get("schema") != "ztare.subscription_dispatch_provenance.v1"
        or row.get("receipt_sha256") != content_hash(core)
        or frozen != row
        or row.get("role") != descriptor["role"]
        or row.get("agent_id") != descriptor["agent_id"]
        or row.get("transport_agent_id") != descriptor["agent_id"]
        or row.get("run_tag") != expected_run_tag
        or row.get("runtime") != config["runtime"]
        or row.get("model") != config["model"]
        or row.get("reasoning_effort") != expected_effort
        or row.get("command_model") != config["model"]
        or row.get("command_reasoning_effort") != expected_effort
        or row.get("config_sha256") != descriptor["config_sha256"]
        or row.get("authority")
        != "subscription_transport_post_commit_observation"
        or type(row.get("charged_reservation")) is not bool
        or not str(row.get("reservation_id") or "").startswith("reservation:")
        or row.get("reservation_phase") != "boundary"
        or not isinstance(resources, Mapping)
        or int(resources.get("provider_calls", 0)) < 1
        or int(resources.get("agent_turns", 0)) < 1
        or type(row.get("returncode")) is not int
        or type(row.get("timeout_seconds")) is not int
        or not 1 <= int(row["timeout_seconds"]) <= int(config["timeout_seconds"])
        or any(
            not str(row.get(field) or "").strip()
            for field in (
                "call_id", "run_tag", "command_sha256", "prompt_sha256",
                "stdout_sha256", "stderr_sha256", "result_sha256",
                "reservation_action_id", "artifact_path",
            )
        )
    ):
        raise ValueError("formal-task transport dispatch receipt changed identity")
    return row


def _validate_pre_spawn_failure(
    contract: TaskDischargeContract,
    descriptor: Mapping[str, Any],
    value: Mapping[str, Any],
    *,
    expected_run_tag: str,
) -> dict[str, Any]:
    from ztare.common.llm_runtime import subscription_reasoning_effort
    from ztare.common.subscription_agent_runtime import (
        SUBSCRIPTION_DISPATCH_PRE_SPAWN_FAILURE_SCHEMA,
    )

    row = dict(value)
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    required = {
        "schema", "dispatch_attempt_id", "disposition", "role", "agent_id",
        "requested_transport_agent_id", "run_tag", "runtime", "model",
        "reasoning_effort", "config_sha256", "input_sha256",
        "command_sha256", "prompt_sha256", "failure_type", "failure_sha256",
        "reason_code", "timeout_seconds", "reservation_id",
        "reservation_action_id", "reservation_phase", "reservation_resources",
        "charged_reservation", "reservation_settlement", "artifact_path",
        "authority", "receipt_sha256",
    }
    config = descriptor["config"]
    expected_effort = subscription_reasoning_effort(
        str(config["runtime"]),
        str(config["reasoning_effort"]),
        model=str(config["model"]),
    )
    artifact = Path(str(row.get("artifact_path") or ""))
    try:
        frozen = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("formal-task pre-spawn artifact is unavailable") from exc
    reservation_id = str(row.get("reservation_id") or "")
    resources = row.get("reservation_resources")
    settlement = str(row.get("reservation_settlement") or "")
    charged = row.get("charged_reservation")
    reservation_consistent = (
        bool(reservation_id)
        and reservation_id.startswith("reservation:")
        and row.get("reservation_phase") == "boundary"
        and isinstance(resources, Mapping)
        and int(resources.get("provider_calls", 0)) >= 1
        and int(resources.get("agent_turns", 0)) >= 1
        and settlement in {"released", "committed"}
        and charged is (settlement == "committed")
        and bool(str(row.get("reservation_action_id") or ""))
    ) or (
        not reservation_id
        and row.get("reservation_action_id") == ""
        and row.get("reservation_phase") == ""
        and resources == {}
        and settlement == "not_reserved"
        and charged is False
    )
    sha_ref = re.compile(r"sha256:[0-9a-f]{64}")
    if (
        set(row) != required
        or row.get("schema") != SUBSCRIPTION_DISPATCH_PRE_SPAWN_FAILURE_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or frozen != row
        or row.get("disposition") != "pre_spawn_failure"
        or not str(row.get("dispatch_attempt_id") or "").startswith(
            "dispatch-attempt:"
        )
        or row.get("role") != descriptor["role"]
        or row.get("agent_id") != descriptor["agent_id"]
        or row.get("requested_transport_agent_id") != descriptor["agent_id"]
        or row.get("run_tag") != expected_run_tag
        or row.get("runtime") != config["runtime"]
        or row.get("model") != config["model"]
        or row.get("reasoning_effort") != expected_effort
        or row.get("config_sha256") != descriptor["config_sha256"]
        or row.get("input_sha256") != _task_attempt_input_sha256(contract)
        or row.get("authority")
        != "subscription_transport_pre_spawn_observation"
        or type(row.get("timeout_seconds")) is not int
        or not 0 <= int(row["timeout_seconds"]) <= int(config["timeout_seconds"])
        or not reservation_consistent
        or any(
            not sha_ref.fullmatch(str(row.get(field) or ""))
            for field in (
                "command_sha256", "prompt_sha256", "failure_sha256",
            )
        )
        or any(
            not str(row.get(field) or "").strip()
            for field in (
                "failure_type", "reason_code", "artifact_path",
            )
        )
    ):
        raise ValueError("formal-task pre-spawn receipt changed identity")
    return row


def _validate_dispatch_evidence(
    contract: TaskDischargeContract,
    descriptor: Mapping[str, Any],
    value: Mapping[str, Any],
    *,
    expected_run_tag: str,
) -> dict[str, Any]:
    from ztare.common.subscription_agent_runtime import (
        SUBSCRIPTION_DISPATCH_PRE_SPAWN_FAILURE_SCHEMA,
    )

    if value.get("schema") == SUBSCRIPTION_DISPATCH_PRE_SPAWN_FAILURE_SCHEMA:
        return _validate_pre_spawn_failure(
            contract,
            descriptor,
            value,
            expected_run_tag=expected_run_tag,
        )
    return _validate_transport_dispatch_call(
        descriptor,
        value,
        expected_run_tag=expected_run_tag,
    )


def _build_formal_task_attempt_outcome(
    contract: TaskDischargeContract,
    *,
    attempt_id: str,
    campaign_id: str,
    context_hash: str,
    role_registry_receipt: Mapping[str, Any],
    dispatch_calls: list[Mapping[str, Any]],
    status: str,
    stage: str,
    reason_code: str,
    admission: FormalizationAdmission | None = None,
    raw_solver_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in {
        "formalization_rejected",
        "runtime_unavailable",
        "solver_unclosed",
    } or stage not in {"formalization", "faithfulness_review", "solver", "kernel_replay"}:
        raise ValueError("unsupported formal-task negative outcome")
    registry = _validate_role_registry_receipt(role_registry_receipt)
    if (
        registry["attempt_id"] != attempt_id
        or registry["campaign_id"] != campaign_id
    ):
        raise ValueError("formal-task negative outcome crossed role registry identity")
    calls: list[dict[str, Any]] = []
    for call in dispatch_calls:
        role = str(call.get("role") or "")
        descriptor = (registry.get("roles") or {}).get(role)
        if not isinstance(descriptor, Mapping):
            raise ValueError("formal-task negative outcome cites an unknown role")
        calls.append(
            _validate_dispatch_evidence(
                contract,
                descriptor,
                call,
                expected_run_tag=_task_role_run_tag(
                    attempt_id=attempt_id,
                    role=role,
                    contract=contract,
                ),
            )
        )
    if not calls:
        raise ValueError("formal-task negative outcome lacks call provenance")
    parameters = formal_task_parameters(contract)
    core = {
        "schema": FORMAL_TASK_ATTEMPT_OUTCOME_SCHEMA,
        "candidate_kind": "theory_task",
        "attempt_id": str(attempt_id),
        "campaign_id": str(campaign_id),
        "context_hash": str(context_hash),
        "contract_sha256": contract.sha256,
        "adjudicator_id": contract.adjudicator_id,
        "request_id": str(parameters["request_id"]),
        "status": status,
        "stage": stage,
        "reason_code": str(reason_code),
        "formalization_admission": (
            admission.to_json() if admission is not None else None
        ),
        "solver_result_sha256": (
            content_hash(dict(raw_solver_result))
            if raw_solver_result is not None
            else ""
        ),
        "role_registry_receipt": registry,
        "dispatch_calls": calls,
        "authority": "formal_task_typed_attempt_feedback",
    }
    if not str(reason_code).strip():
        raise ValueError("formal-task negative outcome requires a reason code")
    return {**core, "receipt_sha256": content_hash(core)}


def validate_formal_task_attempt_outcome(
    contract: TaskDischargeContract, value: Mapping[str, Any]
) -> dict[str, Any]:
    row = dict(value)
    if row.get("schema") != FORMAL_TASK_ATTEMPT_OUTCOME_SCHEMA:
        raise ValueError("unsupported formal-task attempt outcome schema")
    admission_value = row.get("formalization_admission")
    admission = (
        FormalizationAdmission.from_json(admission_value)
        if isinstance(admission_value, Mapping)
        else None
    )
    expected = _build_formal_task_attempt_outcome(
        contract,
        attempt_id=str(row.get("attempt_id") or ""),
        campaign_id=str(row.get("campaign_id") or ""),
        context_hash=str(row.get("context_hash") or ""),
        role_registry_receipt=row.get("role_registry_receipt") or {},
        dispatch_calls=(
            list(row.get("dispatch_calls") or ())
            if isinstance(row.get("dispatch_calls"), list)
            else []
        ),
        status=str(row.get("status") or ""),
        stage=str(row.get("stage") or ""),
        reason_code=str(row.get("reason_code") or ""),
        admission=admission,
        raw_solver_result=(
            {"frozen_digest": row.get("solver_result_sha256")}
            if row.get("solver_result_sha256")
            else None
        ),
    )
    # The raw solver payload is intentionally not copied into feedback.  Replay
    # compares every other field and then checks the already-frozen digest.
    expected["solver_result_sha256"] = str(
        row.get("solver_result_sha256") or ""
    )
    expected_core = {
        key: item for key, item in expected.items() if key != "receipt_sha256"
    }
    expected["receipt_sha256"] = content_hash(expected_core)
    parameters = formal_task_parameters(contract)
    if (
        expected != row
        or row.get("campaign_id") != contract.lifecycle_scope
        or row.get("context_hash") != parameters["context_hash"]
        or row.get("adjudicator_id") != contract.adjudicator_id
        or row.get("request_id") != parameters["request_id"]
    ):
        raise ValueError("formal-task attempt outcome crossed its contract")
    if admission is not None and (
        admission.task_digest != _admission_task_digest(contract)
        or admission.intent_text != render_formal_task_intent(contract)
    ):
        raise ValueError("formal-task negative admission crossed task identity")
    return row


def _validate_role_execution_receipts(
    contract: TaskDischargeContract,
    registry: Mapping[str, Any],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    executions = dict(value)
    if set(executions) != {"formalizer", "faithfulness_reviewer", "lean_solver"}:
        raise ValueError("formal-task execution receipts are not role-total")
    run_tags: set[str] = set()
    for role_name, descriptor in registry["roles"].items():
        row = executions.get(role_name)
        if not isinstance(row, Mapping):
            raise ValueError("formal-task role call receipt is malformed")
        row = dict(row)
        expected_run_tag = _task_role_run_tag(
            attempt_id=str(registry["attempt_id"]),
            role=str(role_name),
            contract=contract,
        )
        core = {key: item for key, item in row.items() if key != "receipt_sha256"}
        if (
            set(row)
            != {
                "schema", "role", "agent_id", "config_sha256",
                "contract_sha256", "run_tag", "input_sha256",
                "output_sha256", "output_schema", "outcome", "authority",
                "execution_timeout_s",
                "dispatch_calls", "dispatch_calls_sha256",
                "receipt_sha256",
            }
            or row.get("schema") != FORMAL_TASK_ROLE_CALL_SCHEMA
            or row.get("receipt_sha256") != content_hash(core)
            or row.get("role") != role_name
            or row.get("agent_id") != descriptor["agent_id"]
            or row.get("config_sha256") != descriptor["config_sha256"]
            or row.get("contract_sha256") != contract.sha256
            or row.get("run_tag") != expected_run_tag
            or row.get("authority") != "formal_task_transport_provenance_join"
            or not isinstance(row.get("dispatch_calls"), list)
            or row.get("dispatch_calls_sha256")
            != content_hash(row.get("dispatch_calls"))
            or type(row.get("execution_timeout_s")) is not int
            or not 1 <= int(row["execution_timeout_s"]) <= int(
                descriptor["config"]["timeout_seconds"]
            )
            or any(
                not str(row.get(field) or "").strip()
                for field in (
                    "run_tag", "input_sha256", "output_sha256",
                    "output_schema", "outcome",
                )
            )
        ):
            raise ValueError("formal-task role call receipt changed identity")
        calls = [
            _validate_dispatch_evidence(
                contract,
                descriptor,
                call,
                expected_run_tag=expected_run_tag,
            )
            for call in row["dispatch_calls"]
        ]
        if not calls or not any(
            call.get("schema") == "ztare.subscription_dispatch_provenance.v1"
            and call.get("returncode") == 0
            and call.get("charged_reservation") is True
            for call in calls
        ):
            raise ValueError(
                f"formal-task {role_name} lacks a successful subscription dispatch"
            )
        run_tags.add(str(row["run_tag"]))
        executions[role_name] = row
    if len(run_tags) != 3:
        raise ValueError("formal-task roles did not use distinct call identities")
    return executions


def _kernel_replay_receipt(
    contract: TaskDischargeContract,
    admission: FormalizationAdmission,
    raw_solver_result: Mapping[str, Any],
    *,
    compile_fn: CompileFn,
    attempt_id: str,
    campaign_id: str,
    context_hash: str,
    lean_solver_ref: str,
) -> dict[str, Any]:
    raw = dict(raw_solver_result)
    results = raw.get("results")
    primary = results[0] if isinstance(results, list) and results else None
    if not isinstance(primary, Mapping):
        raise ValueError("formal-task solver returned no typed primary result")
    proof_text = str(primary.get("proof_text") or "").strip()
    validation = primary.get("contract_validation")
    receipts = (
        validation.get("receipts") if isinstance(validation, Mapping) else None
    )
    kernel_receipt = (
        receipts.get("kernel_compile_receipt")
        if isinstance(receipts, Mapping) else None
    )
    mnc_receipt = (
        receipts.get("matched_negative_control_receipt")
        if isinstance(receipts, Mapping) else None
    )
    axiom_receipt = (
        receipts.get("axiom_allowlist_receipt")
        if isinstance(receipts, Mapping) else None
    )
    closure_certificate = raw.get("closure_certificate")
    governance = raw.get("governance")
    if (
        primary.get("outcome") != "closed"
        or not proof_text
        or not isinstance(validation, Mapping)
        or not finalized_ratification_eligible(dict(validation))
        or not isinstance(kernel_receipt, Mapping)
        or kernel_receipt.get("passed") is not True
        or not isinstance(mnc_receipt, Mapping)
        or mnc_receipt.get("passed") is not True
        or not isinstance(axiom_receipt, Mapping)
        or axiom_receipt.get("passed") is not True
        or validation.get("positive_axiom_receipt_required") is not True
        or validation.get("axiom_tier") != "kernel_pure"
        or not closure_certificate
        or not isinstance(governance, Mapping)
        or not governance_ratification_eligible(dict(governance))
    ):
        raise FormalTaskAttemptDidNotClose(
            "solver_result_lacks_ratified_closure_evidence"
        )
    proved_source = replace_decl_proof(
        admission.source_text, admission.target_name, proof_text
    )
    if not proved_source or has_sorry(proved_source):
        raise FormalTaskAttemptDidNotClose(
            "solver_proof_did_not_close_admitted_source"
        )
    import_allowlist = _mathlib_only_import_receipt(
        contract, proved_source, stage="proved_source"
    )
    compile_result = compile_fn(proved_source)
    compile_passed = bool(
        compile_result[0]
        if isinstance(compile_result, tuple) and compile_result
        else compile_result
    )
    if not compile_passed:
        raise FormalTaskAttemptDidNotClose(
            "solver_proof_failed_independent_kernel_replay"
        )
    from ztare.leanmill.solver.statement_integrity import check

    integrity = check(
        admission.source_text, proved_source, admission.target_name
    ).to_dict()
    if integrity.get("ok") is not True:
        raise ValueError("formal-task proof changed the admitted statement")
    core = {
        "schema": FORMAL_TASK_KERNEL_REPLAY_SCHEMA,
        "attempt_id": str(attempt_id),
        "campaign_id": str(campaign_id),
        "context_hash": str(context_hash),
        "contract_sha256": contract.sha256,
        "formalization_admission_digest": admission.admission_digest,
        "formal_target_id": admission.target_name,
        "formal_statement_sha256": admission.target_signature_digest,
        "proof_text": proof_text,
        "proved_source_sha256": content_hash({"lean_source": proved_source}),
        "proved_import_allowlist_receipt": import_allowlist,
        "solver_result_sha256": content_hash(raw),
        "contract_validation": dict(validation),
        "governance": dict(governance),
        "closure_certificate": closure_certificate,
        "independent_compile_passed": True,
        "statement_integrity": integrity,
        "status": "kernel_verified",
        "lean_solver_ref": str(lean_solver_ref),
        "authority": "formalization_campaign_solver_plus_independent_replay",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def build_formalization_campaign_task_boundary_result(
    contract: TaskDischargeContract,
    *,
    admission: FormalizationAdmission,
    role_separation_receipt: Mapping[str, Any],
    faithfulness_receipt: Mapping[str, Any],
    kernel_replay_receipt: Mapping[str, Any],
    admitted_import_allowlist_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Join the existing formalization firewall and solver receipts."""

    parameters = formal_task_parameters(contract)
    roles = _validate_role_receipt(contract, role_separation_receipt)
    kernel = _validate_kernel_receipt(contract, admission, kernel_replay_receipt)
    _validate_role_execution_bindings(roles, admission, kernel)
    admitted_imports = _validate_import_allowlist_receipt(
        contract,
        admission.source_text,
        admitted_import_allowlist_receipt,
        stage="admitted_source",
    )
    # Reuse the common validator by building the receipt through its public
    # constructor and requiring byte identity with the supplied row.
    expected_faithfulness = build_formal_task_faithfulness_receipt(
        contract,
        formal_target_id=admission.target_name,
        formal_statement_sha256=admission.target_signature_digest,
        reviewer_evidence_refs=(
            admission.admission_digest,
            str(roles["receipt_sha256"]),
        ),
        authority=str(roles["faithfulness_reviewer_ref"]),
    )
    if dict(faithfulness_receipt) != expected_faithfulness:
        raise ValueError("formal-task faithfulness receipt does not replay")
    core = {
        "schema": FORMALIZATION_CAMPAIGN_TASK_BOUNDARY_RESULT_SCHEMA,
        "candidate_kind": "theory_task",
        "attempt_id": str(roles["attempt_id"]),
        "campaign_id": str(roles["campaign_id"]),
        "context_hash": str(parameters["context_hash"]),
        "contract_sha256": contract.sha256,
        "adjudicator_id": contract.adjudicator_id,
        "request_id": str(parameters["request_id"]),
        "status": "kernel_verified_independently_reviewed",
        "formal_target_id": admission.target_name,
        "formal_statement_sha256": admission.target_signature_digest,
        "formalization_admission": admission.to_json(),
        "admitted_import_allowlist_receipt": admitted_imports,
        "role_separation_receipt": dict(roles),
        "faithfulness_receipt": expected_faithfulness,
        "kernel_replay_receipt": dict(kernel),
        "authority": "frontier_boundary_formalization_campaign_join",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _validate_role_receipt(
    contract: TaskDischargeContract, value: Mapping[str, Any]
) -> dict[str, Any]:
    row = dict(value)
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    required = {
        "schema", "attempt_id", "campaign_id", "context_hash",
        "contract_sha256", "formalization_admission_digest",
        "role_registry_receipt", "role_execution_receipts",
        "formalizer_ref", "faithfulness_reviewer_ref", "lean_solver_ref",
        "separate_author_reviewer", "authority", "receipt_sha256",
    }
    roles = (
        str(row.get("formalizer_ref") or ""),
        str(row.get("faithfulness_reviewer_ref") or ""),
        str(row.get("lean_solver_ref") or ""),
    )
    registry = row.get("role_registry_receipt")
    try:
        registry_row = _validate_role_registry_receipt(registry or {})
    except (TypeError, ValueError):
        registry_row = {}
    try:
        execution_rows = _validate_role_execution_receipts(
            contract,
            registry_row,
            row.get("role_execution_receipts") or {},
        )
    except (KeyError, TypeError, ValueError):
        execution_rows = {}
    if (
        set(row) != required
        or row.get("schema") != FORMALIZATION_ROLE_RECEIPT_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("contract_sha256") != contract.sha256
        or row.get("campaign_id") != contract.lifecycle_scope
        or registry_row.get("attempt_id") != row.get("attempt_id")
        or registry_row.get("campaign_id") != row.get("campaign_id")
        or row.get("formalizer_ref")
        != ((registry_row.get("roles") or {}).get("formalizer") or {}).get("agent_id")
        or row.get("faithfulness_reviewer_ref")
        != ((registry_row.get("roles") or {}).get("faithfulness_reviewer") or {}).get("agent_id")
        or row.get("lean_solver_ref")
        != ((registry_row.get("roles") or {}).get("lean_solver") or {}).get("agent_id")
        or set(execution_rows)
        != {"formalizer", "faithfulness_reviewer", "lean_solver"}
        or len(set(roles)) != 3
        or any(not value for value in roles)
        or row.get("separate_author_reviewer") is not True
        or row.get("authority")
        != "existing_formalization_campaign_role_registry"
    ):
        raise ValueError("formal-task campaign role receipt changed identity")
    return row


def _validate_role_execution_bindings(
    roles: Mapping[str, Any],
    admission: FormalizationAdmission,
    kernel: Mapping[str, Any],
) -> None:
    executions = roles["role_execution_receipts"]
    solve_input = admission.solve_input()
    expected = {
        "formalizer": {
            "input_sha256": content_hash(
                {
                    "intent_text": admission.intent_text,
                    "task_digest": admission.task_digest,
                }
            ),
            "output_sha256": admission.admission_digest,
            "output_schema": admission.schema,
            "outcome": admission.status,
        },
        "faithfulness_reviewer": {
            "input_sha256": content_hash(
                {
                    "intent_digest": admission.intent_digest,
                    "source_digest": admission.source_digest,
                }
            ),
            "output_sha256": content_hash(admission.faithfulness_checks),
            "output_schema": "leanmill.formalization_faithfulness_checks.v1",
            "outcome": "faithful" if admission.faithfulness_checks else "missing",
        },
        "lean_solver": {
            "input_sha256": content_hash(
                {
                    "target_name": solve_input.target_name,
                    "source_text": solve_input.source_text,
                    "goal": solve_input.goal,
                }
            ),
            "output_sha256": str(kernel["solver_result_sha256"]),
            "output_schema": str(executions["lean_solver"]["output_schema"]),
            "outcome": "closed",
        },
    }
    for role_name, fields in expected.items():
        observed = executions[role_name]
        if any(observed.get(key) != value for key, value in fields.items()):
            raise ValueError(
                f"formal-task {role_name} call receipt is not output-bound"
            )


def _validate_kernel_receipt(
    contract: TaskDischargeContract,
    admission: FormalizationAdmission,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    row = dict(value)
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    required = {
        "schema", "attempt_id", "campaign_id", "context_hash",
        "contract_sha256", "formalization_admission_digest",
        "formal_target_id", "formal_statement_sha256", "proof_text",
        "proved_source_sha256", "proved_import_allowlist_receipt",
        "solver_result_sha256",
        "contract_validation", "governance", "closure_certificate",
        "independent_compile_passed", "statement_integrity", "status",
        "lean_solver_ref", "authority", "receipt_sha256",
    }
    proved_source = replace_decl_proof(
        admission.source_text,
        admission.target_name,
        str(row.get("proof_text") or ""),
    )
    validation = row.get("contract_validation")
    receipts = validation.get("receipts") if isinstance(validation, Mapping) else None
    try:
        proved_imports = _validate_import_allowlist_receipt(
            contract,
            proved_source,
            row.get("proved_import_allowlist_receipt") or {},
            stage="proved_source",
        )
    except (TypeError, ValueError):
        proved_imports = {}
    if (
        set(row) != required
        or row.get("schema") != FORMAL_TASK_KERNEL_REPLAY_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("contract_sha256") != contract.sha256
        or row.get("campaign_id") != contract.lifecycle_scope
        or row.get("formalization_admission_digest")
        != admission.admission_digest
        or row.get("formal_target_id") != admission.target_name
        or row.get("formal_statement_sha256")
        != admission.target_signature_digest
        or not proved_source
        or has_sorry(proved_source)
        or row.get("proved_source_sha256")
        != content_hash({"lean_source": proved_source})
        or proved_imports.get("status") != "mathlib_only"
        or not isinstance(validation, Mapping)
        or not finalized_ratification_eligible(dict(validation))
        or not isinstance(receipts, Mapping)
        or (receipts.get("kernel_compile_receipt") or {}).get("passed") is not True
        or (receipts.get("matched_negative_control_receipt") or {}).get("passed")
        is not True
        or (receipts.get("axiom_allowlist_receipt") or {}).get("passed") is not True
        or validation.get("positive_axiom_receipt_required") is not True
        or validation.get("axiom_tier") != "kernel_pure"
        or row.get("independent_compile_passed") is not True
        or (row.get("statement_integrity") or {}).get("ok") is not True
        or row.get("status") != "kernel_verified"
        or row.get("authority")
        != "formalization_campaign_solver_plus_independent_replay"
    ):
        raise ValueError("formal-task kernel replay receipt changed identity")
    return row


def validate_formalization_campaign_task_boundary_result(
    contract: TaskDischargeContract,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the full campaign-owned task result without provider calls."""

    parameters = formal_task_parameters(contract)
    row = dict(value)
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    required = {
        "schema", "candidate_kind", "attempt_id", "campaign_id",
        "context_hash", "contract_sha256", "adjudicator_id", "request_id",
        "status", "formal_target_id", "formal_statement_sha256",
        "formalization_admission", "admitted_import_allowlist_receipt",
        "role_separation_receipt",
        "faithfulness_receipt", "kernel_replay_receipt", "authority",
        "receipt_sha256",
    }
    if (
        set(row) != required
        or row.get("schema")
        != FORMALIZATION_CAMPAIGN_TASK_BOUNDARY_RESULT_SCHEMA
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("candidate_kind") != "theory_task"
        or row.get("context_hash") != parameters["context_hash"]
        or row.get("contract_sha256") != contract.sha256
        or row.get("adjudicator_id") != contract.adjudicator_id
        or row.get("request_id") != parameters["request_id"]
        or row.get("status") != "kernel_verified_independently_reviewed"
        or row.get("authority")
        != "frontier_boundary_formalization_campaign_join"
    ):
        raise ValueError("formalization-campaign task result crossed its contract")
    admission = FormalizationAdmission.from_json(
        row.get("formalization_admission") or {}
    )
    admitted_imports = _validate_import_allowlist_receipt(
        contract,
        admission.source_text,
        row.get("admitted_import_allowlist_receipt") or {},
        stage="admitted_source",
    )
    roles = _validate_role_receipt(
        contract, row.get("role_separation_receipt") or {}
    )
    if (
        admission.task_digest != _admission_task_digest(contract)
        or admission.intent_text != render_formal_task_intent(contract)
        or not admission.admitted
        or roles["attempt_id"] != row["attempt_id"]
        or roles["campaign_id"] != row["campaign_id"]
        or roles["context_hash"] != row["context_hash"]
        or roles["formalization_admission_digest"] != admission.admission_digest
    ):
        raise ValueError("formalization admission is not bound to this campaign task")
    kernel = _validate_kernel_receipt(
        contract, admission, row.get("kernel_replay_receipt") or {}
    )
    expected = build_formalization_campaign_task_boundary_result(
        contract,
        admission=admission,
        role_separation_receipt=roles,
        faithfulness_receipt=row.get("faithfulness_receipt") or {},
        kernel_replay_receipt=kernel,
        admitted_import_allowlist_receipt=admitted_imports,
    )
    if expected != row:
        raise ValueError("formalization-campaign task result does not replay")
    return row


def make_formalization_campaign_task_executor(
    *,
    attempt_id: str,
    campaign_id: str,
    sandbox: str | Path,
    compile_fn: CompileFn,
    role_registry_receipt: Mapping[str, Any],
    substrate: str | Path | None = None,
    timeout_s: int = 600,
    formalization_timeout_s: int | None = None,
    reviewer_timeout_s: int | None = None,
    solver_timeout_s: int | None = None,
    max_refines: int = 2,
    formalization_admission_fn: FormalizationAdmissionFn | None = None,
    admitted_solver_fn: AdmittedSolverFn | None = None,
) -> Callable[..., dict[str, Any]]:
    """Create the boundary callback; injectable seams make first-fire tests free."""

    if not all(str(value).strip() for value in (attempt_id, campaign_id)):
        raise ValueError("formal-task executor requires campaign and attempt identity")
    registry = _validate_role_registry_receipt(role_registry_receipt)
    if (
        registry["attempt_id"] != attempt_id
        or registry["campaign_id"] != campaign_id
    ):
        raise ValueError("formal-task executor role registry crossed identity")
    role_rows = registry["roles"]
    formalizer_ref = str(role_rows["formalizer"]["agent_id"])
    faithfulness_reviewer_ref = str(
        role_rows["faithfulness_reviewer"]["agent_id"]
    )
    lean_solver_ref = str(role_rows["lean_solver"]["agent_id"])
    formalize_timeout = min(
        int(timeout_s if formalization_timeout_s is None else formalization_timeout_s),
        int(role_rows["formalizer"]["config"]["timeout_seconds"]),
    )
    review_timeout = min(
        int(timeout_s if reviewer_timeout_s is None else reviewer_timeout_s),
        int(role_rows["faithfulness_reviewer"]["config"]["timeout_seconds"]),
    )
    solve_timeout = min(
        int(timeout_s if solver_timeout_s is None else solver_timeout_s),
        int(role_rows["lean_solver"]["config"]["timeout_seconds"]),
    )
    if min(formalize_timeout, review_timeout, solve_timeout) < 1:
        raise ValueError("formal-task role timeout must be positive")
    sandbox_path = Path(sandbox)
    substrate_path = Path(substrate) if substrate is not None else sandbox_path

    from ztare.common.llm_runtime import subscription_reasoning_effort

    role_native_efforts: dict[str, str] = {}
    for role_name, descriptor in role_rows.items():
        config = descriptor["config"]
        native_effort = subscription_reasoning_effort(
            str(config["runtime"]),
            str(config["reasoning_effort"]),
            model=str(config["model"]),
        )
        if native_effort is None:
            raise ValueError(f"formal-task {role_name} effort is unsupported")
        role_native_efforts[role_name] = native_effort

    def executor(
        contract: TaskDischargeContract,
        *,
        context: Any,
        verification_plan: Mapping[str, Any],
        budget_ledger: Any,
    ) -> dict[str, Any]:
        del verification_plan, budget_ledger
        parameters = formal_task_parameters(contract)
        if (
            contract.lifecycle_scope != campaign_id
            or parameters["context_hash"] != getattr(context, "context_hash", None)
        ):
            raise ValueError("formal-task executor crossed campaign or context identity")
        intent = render_formal_task_intent(contract)
        notes = _context_notes(context, contract)
        from ztare.common.subscription_agent_runtime import (
            record_subscription_dispatch_pre_spawn_failure,
            subscription_dispatch_provenance_scope,
            subscription_dispatch_role_scope,
        )

        formalizer_descriptor = role_rows["formalizer"]
        formalizer_config = formalizer_descriptor["config"]
        dispatch_root = (
            sandbox_path
            / ".formal_task_dispatches"
            / attempt_id.replace(":", "_")
            / contract.sha256
        )
        attempt_input_sha256 = _task_attempt_input_sha256(contract)

        def ensure_unavailable_attempt(reason_code: str) -> None:
            if dispatch_calls:
                return
            record_subscription_dispatch_pre_spawn_failure(
                input_sha256=attempt_input_sha256,
                reason_code=reason_code,
                if_role_empty=True,
            )

        with subscription_dispatch_provenance_scope(
            artifact_dir=dispatch_root,
            role="formalizer",
            agent_id=formalizer_ref,
            run_tag=(
                _task_role_run_tag(
                    attempt_id=attempt_id,
                    role="formalizer",
                    contract=contract,
                )
            ),
            runtime=str(formalizer_config["runtime"]),
            model=str(formalizer_config["model"]),
            reasoning_effort=role_native_efforts["formalizer"],
            config_sha256=str(formalizer_descriptor["config_sha256"]),
            max_timeout_seconds=int(formalizer_config["timeout_seconds"]),
            attempt_input_sha256=attempt_input_sha256,
            record_empty_attempt=True,
        ) as dispatch_calls:
            try:
                with _isolated_formal_task_proof_world():
                    if formalization_admission_fn is None:
                        admission_value = formalize_only(
                            intent,
                            task_digest=_admission_task_digest(contract),
                            sandbox=sandbox_path,
                            substrate=substrate_path,
                            timeout_s=formalize_timeout,
                            max_refines=int(max_refines),
                            def_faithfulness=True,
                            notes=notes,
                            shared_context=(
                                f"attempt_id={attempt_id}; campaign_id={campaign_id}; "
                                f"contract_sha256={contract.sha256}"
                            ),
                        )
                    else:
                        admission_value = formalization_admission_fn(
                            intent,
                            task_digest=_admission_task_digest(contract),
                            sandbox=sandbox_path,
                            substrate=substrate_path,
                            timeout_s=formalize_timeout,
                            max_refines=int(max_refines),
                            def_faithfulness=True,
                            notes=notes,
                            shared_context=(
                                f"attempt_id={attempt_id}; campaign_id={campaign_id}; "
                                f"contract_sha256={contract.sha256}"
                            ),
                        )
            except (RuntimeError, TimeoutError, OSError) as exc:
                ensure_unavailable_attempt(type(exc).__name__)
                failed_role = str(
                    (dispatch_calls[-1] if dispatch_calls else {}).get("role") or ""
                )
                return _build_formal_task_attempt_outcome(
                    contract,
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    context_hash=parameters["context_hash"],
                    role_registry_receipt=registry,
                    dispatch_calls=dispatch_calls,
                    status="runtime_unavailable",
                    stage=(
                        "faithfulness_review"
                        if failed_role == "faithfulness_reviewer"
                        else "formalization"
                    ),
                    reason_code=type(exc).__name__,
                )
            admission = _load_admission(admission_value)
            if (
                admission.task_digest != _admission_task_digest(contract)
                or admission.intent_text != intent
            ):
                raise ValueError("formalization campaign crossed the exact leaf task")
            if not admission.admitted or not admission.faithfulness_checks:
                if admission.status == "INADMISSIBLE_PROVIDER_DEAD":
                    ensure_unavailable_attempt(
                        admission.faithfulness_reason
                        or "formalization_provider_unavailable"
                    )
                return _build_formal_task_attempt_outcome(
                    contract,
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    context_hash=parameters["context_hash"],
                    role_registry_receipt=registry,
                    dispatch_calls=dispatch_calls,
                    status=(
                        "runtime_unavailable"
                        if admission.status == "INADMISSIBLE_PROVIDER_DEAD"
                        else "formalization_rejected"
                    ),
                    stage=(
                        "formalization"
                        if admission.status == "INADMISSIBLE_PROVIDER_DEAD"
                        else "faithfulness_review"
                    ),
                    reason_code=(
                        admission.faithfulness_reason
                        or admission.status.lower()
                    ),
                    admission=admission,
                )
            admitted_imports = _mathlib_only_import_receipt(
                contract, admission.source_text, stage="admitted_source"
            )
            solve_input = admission.solve_input()
            solver_descriptor = role_rows["lean_solver"]
            solver_config = solver_descriptor["config"]
            try:
                with subscription_dispatch_role_scope(
                    role="lean_solver",
                    agent_id=lean_solver_ref,
                    run_tag=(
                        _task_role_run_tag(
                            attempt_id=attempt_id,
                            role="lean_solver",
                            contract=contract,
                        )
                    ),
                    runtime=str(solver_config["runtime"]),
                    model=str(solver_config["model"]),
                    reasoning_effort=role_native_efforts["lean_solver"],
                    config_sha256=str(solver_descriptor["config_sha256"]),
                    max_timeout_seconds=int(solver_config["timeout_seconds"]),
                    attempt_input_sha256=attempt_input_sha256,
                    record_empty_attempt=True,
                ), _isolated_formal_task_proof_world():
                    if admitted_solver_fn is None:
                        from ztare.leanmill.solver.solver_core import solve_adhoc

                        raw_solver = solve_adhoc(
                            *solve_input.positional_args(),
                            substrate=substrate_path,
                            timeout_s=solve_timeout,
                            notes=notes,
                            require_positive_axiom_receipt=True,
                        )
                    else:
                        raw_solver = admitted_solver_fn(
                            *solve_input.positional_args(),
                            substrate=substrate_path,
                            timeout_s=solve_timeout,
                            notes=notes,
                            require_positive_axiom_receipt=True,
                        )
            except (RuntimeError, TimeoutError, OSError) as exc:
                return _build_formal_task_attempt_outcome(
                    contract,
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    context_hash=parameters["context_hash"],
                    role_registry_receipt=registry,
                    dispatch_calls=dispatch_calls,
                    status="runtime_unavailable",
                    stage="solver",
                    reason_code=type(exc).__name__,
                    admission=admission,
                )
        if not isinstance(raw_solver, Mapping):
            raise TypeError("formal-task solver callback returned the wrong type")
        solver_results = raw_solver.get("results")
        solver_primary = (
            solver_results[0]
            if isinstance(solver_results, list) and solver_results
            else None
        )
        if not isinstance(solver_primary, Mapping):
            raise ValueError("formal-task solver returned no typed primary result")
        if solver_primary.get("outcome") != "closed":
            outcome = str(solver_primary.get("outcome") or "unclosed")
            solver_transport_observed = any(
                call.get("schema")
                == "ztare.subscription_dispatch_provenance.v1"
                and call.get("role") == "lean_solver"
                for call in dispatch_calls
            )
            return _build_formal_task_attempt_outcome(
                contract,
                attempt_id=attempt_id,
                campaign_id=campaign_id,
                context_hash=parameters["context_hash"],
                role_registry_receipt=registry,
                dispatch_calls=dispatch_calls,
                status=(
                    "runtime_unavailable"
                    if (
                        not solver_transport_observed
                        or "inadmissible" in outcome
                        or "unavailable" in outcome
                    )
                    else "solver_unclosed"
                ),
                stage="solver",
                reason_code=(
                    outcome
                    if solver_transport_observed
                    else "solver_no_transport_observed"
                ),
                admission=admission,
                raw_solver_result=raw_solver,
            )
        execution_receipts = _build_role_execution_receipts(
            contract=contract,
            registry=registry,
            admission=admission,
            raw_solver_result=raw_solver,
            attempt_id=attempt_id,
            formalization_timeout_s=formalize_timeout,
            reviewer_timeout_s=review_timeout,
            solver_timeout_s=solve_timeout,
            dispatch_calls=dispatch_calls,
        )
        roles = _role_separation_receipt(
            contract=contract,
            attempt_id=attempt_id,
            campaign_id=campaign_id,
            context_hash=parameters["context_hash"],
            admission=admission,
            role_registry_receipt=registry,
            role_execution_receipts=execution_receipts,
        )
        faithfulness = build_formal_task_faithfulness_receipt(
            contract,
            formal_target_id=admission.target_name,
            formal_statement_sha256=admission.target_signature_digest,
            reviewer_evidence_refs=(
                admission.admission_digest,
                str(roles["receipt_sha256"]),
            ),
            authority=faithfulness_reviewer_ref,
        )
        try:
            with _isolated_formal_task_proof_world():
                kernel = _kernel_replay_receipt(
                    contract,
                    admission,
                    raw_solver,
                    compile_fn=compile_fn,
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    context_hash=parameters["context_hash"],
                    lean_solver_ref=lean_solver_ref,
                )
        except FormalTaskAttemptDidNotClose as exc:
            return _build_formal_task_attempt_outcome(
                contract,
                attempt_id=attempt_id,
                campaign_id=campaign_id,
                context_hash=parameters["context_hash"],
                role_registry_receipt=registry,
                dispatch_calls=dispatch_calls,
                status="solver_unclosed",
                stage="kernel_replay",
                reason_code=str(exc),
                admission=admission,
                raw_solver_result=raw_solver,
            )
        return build_formalization_campaign_task_boundary_result(
            contract,
            admission=admission,
            role_separation_receipt=roles,
            faithfulness_receipt=faithfulness,
            kernel_replay_receipt=kernel,
            admitted_import_allowlist_receipt=admitted_imports,
        )

    return executor


__all__ = [
    "FORMALIZATION_ROLE_RECEIPT_SCHEMA",
    "FORMAL_TASK_ROLE_REGISTRY_SCHEMA",
    "FORMAL_TASK_ROLE_CALL_SCHEMA",
    "FORMAL_TASK_KERNEL_REPLAY_SCHEMA",
    "FORMAL_TASK_IMPORT_ALLOWLIST_SCHEMA",
    "build_formalization_campaign_task_boundary_result",
    "build_formal_task_role_registry_receipt",
    "make_formalization_campaign_task_executor",
    "render_formal_task_intent",
    "validate_formalization_campaign_task_boundary_result",
]
