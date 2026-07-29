"""Deterministic terminal-obligation gate for frontier theory campaigns.

The gate owns no mathematical judgement.  It only checks two lifecycle
invariants over content-bound receipts:

* every frozen lineage has one terminal disposition; and
* every residual whose source scope is a proved finite witness has a terminal
  adjudication before the campaign is allowed to stop.

Callers remain responsible for producing the dispositions and adjudications
through their registered scientific authorities.  This module verifies their
identity, totality, and joins.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from ztare.common.schema_routes import GoverningIdentity
from ztare.leanmill.theory_ir import content_hash


LINEAGE_DISPOSITION_SCHEMA = "leanmill.frozen_lineage_disposition.v2"
GENERALIZATION_RESIDUAL_SCHEMA = "leanmill.generalization_residual.v1"
GENERALIZATION_ADJUDICATION_SCHEMA = (
    "leanmill.generalization_residual_adjudication.v2"
)
CAMPAIGN_CLOSURE_GATE_SCHEMA = "leanmill.campaign_closure_gate.v1"
TASK_DISCHARGE_AUTHORITY_RECEIPT_SCHEMA = (
    "leanmill.campaign_closure_task_discharge_authority.v1"
)
LEAF_DISPOSITION_AUTHORITY_RECEIPT_SCHEMA = (
    "leanmill.campaign_closure_leaf_disposition_authority.v1"
)
TERMINAL_TRANSITION_AUTHORITY_RECEIPT_SCHEMA = (
    "leanmill.campaign_closure_terminal_transition_authority.v1"
)
REVIEWED_FAMILY_OBJECTIVE_DISCHARGE_AUTHORITY = (
    "reviewed_family_content_bound_terminal_transition"
)
_REVIEWED_FAMILY_OBJECTIVE_DISCHARGE_SCHEMA = (
    "leanmill.reviewed_family_objective_discharge.v2"
)
REVIEWED_FAMILY_EXHAUSTION_DISCHARGE_AUTHORITY = (
    "reviewed_family_exhaustion_content_bound_terminal_transition"
)
_REVIEWED_FAMILY_EXHAUSTION_DISCHARGE_SCHEMA = (
    "leanmill.reviewed_family_exhaustion_discharge.v1"
)

_TERMINAL_LINEAGE_STATES = frozenset(
    {
        "objective_discharged",
        "rejected",
        "superseded",
        "retired_unresolved",
    }
)
_TERMINAL_GENERALIZATION_STATES = frozenset(
    {
        "proved_general",
        "refuted_general",
        "bounded_only",
        "withdrawn",
    }
)


@dataclass(frozen=True)
class CampaignClosureAuthorityRoute:
    """Registered origin replay for one terminal decision authority."""

    authority: str
    obligation_kind: str
    terminal_states: frozenset[str]
    authority_receipt_schema: str
    identity: GoverningIdentity
    replay: Callable[[Mapping[str, Any], Mapping[str, Any]], tuple[str, ...]]


def _task_discharge_identity() -> GoverningIdentity:
    return GoverningIdentity(
        job="project a discharged frozen theory task into terminal campaign state",
        owner="AxiomPack theory-task consumption state machine",
        lifecycle="one frozen theory program and one immutable boundary result",
        authority="registered task adjudicator replay plus campaign consumption",
        equality_relation=(
            "program, contract, boundary result, discharge bundle, and consumption hashes"
        ),
        compatibility_relation=(
            "the discharged program owns the lineage or finite residual being closed"
        ),
    )


def _leaf_disposition_identity() -> GoverningIdentity:
    return GoverningIdentity(
        job="carry a leaf-authored reject or supersede decision into terminal state",
        owner="AxiomPack leaf workbench",
        lifecycle="one frozen lineage and one immutable navigator turn",
        authority="deterministic host replay of the registered workbench action",
        equality_relation="workbench receipt id and frozen output summary bytes",
        compatibility_relation="the receipt names the same context, lineage, state, and evidence",
    )


def _terminal_transition_identity() -> GoverningIdentity:
    return GoverningIdentity(
        job="retire unresolved lineages after an authoritative campaign stop",
        owner="AxiomPack campaign lifecycle",
        lifecycle="one budget-stop or explicit retirement transition",
        authority="content replay of the registered lifecycle transition receipt",
        equality_relation="transition receipt hash plus campaign context",
        compatibility_relation="only retired_unresolved is projected from a stop transition",
    )


def _reviewed_family_objective_discharge_identity() -> GoverningIdentity:
    return GoverningIdentity(
        job="project a reviewed finite-family witness into terminal campaign state",
        owner="AxiomPack reviewed-family objective transition",
        lifecycle="one frozen construction objective and its governed witness",
        authority="deterministic replay of the typed reviewed-family discharge",
        equality_relation=(
            "blueprint, synthesis, source run, family execution, admission, "
            "and governed ratification hashes"
        ),
        compatibility_relation=(
            "contributing source lineages discharge the objective; other frozen "
            "lineages are superseded by the same exact existential witness"
        ),
    )


def _reviewed_family_exhaustion_discharge_identity() -> GoverningIdentity:
    return GoverningIdentity(
        job="project one reviewed exhausted family and its typed successor",
        owner="AxiomPack reviewed-family exhaustion transition",
        lifecycle="one frozen family execution and its later navigation wave",
        authority="deterministic replay of the typed exhaustion discharge",
        equality_relation=(
            "blueprint, family review, complete rejection execution, feedback, "
            "search wave, and next-request authorship hashes"
        ),
        compatibility_relation=(
            "family-source lineages discharge only under the frozen stop clause; "
            "other frozen lineages retire unresolved"
        ),
    )


def _verify_receipt(
    value: Mapping[str, Any],
    *,
    schema: str,
    required_fields: frozenset[str],
) -> dict[str, Any]:
    row = dict(value)
    if set(row) != set(required_fields) | {"receipt_sha256"}:
        raise ValueError(f"{schema} fields do not match the frozen schema")
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    if row.get("schema") != schema or row.get("receipt_sha256") != content_hash(core):
        raise ValueError(f"{schema} digest mismatch")
    return row


def build_task_discharge_authority_receipt(
    *,
    theory_program: Mapping[str, Any],
    discharge_bundle: Mapping[str, Any],
    discharge_consumption: Mapping[str, Any],
    boundary_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the source chain later replayed by the terminal gate."""

    core = {
        "schema": TASK_DISCHARGE_AUTHORITY_RECEIPT_SCHEMA,
        "theory_program": dict(theory_program),
        "discharge_bundle": dict(discharge_bundle),
        "discharge_consumption": dict(discharge_consumption),
        "boundary_result": dict(boundary_result),
        "authority": "registered_task_adjudicator_replay",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def build_leaf_disposition_authority_receipt(
    workbench_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the exact registered workbench action that chose a disposition."""

    core = {
        "schema": LEAF_DISPOSITION_AUTHORITY_RECEIPT_SCHEMA,
        "workbench_receipt": dict(workbench_receipt),
        "authority": "registered_axiompack_leaf_workbench_replay",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def build_terminal_transition_authority_receipt(
    transition_receipt: Mapping[str, Any], *, context_hash: str
) -> dict[str, Any]:
    """Freeze one budget-stop or explicit-retirement origin."""

    core = {
        "schema": TERMINAL_TRANSITION_AUTHORITY_RECEIPT_SCHEMA,
        "context_hash": str(context_hash),
        "transition_receipt": dict(transition_receipt),
        "authority": "registered_campaign_terminal_transition_replay",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _verify_authority_wrapper(
    value: Mapping[str, Any], *, schema: str, fields: frozenset[str]
) -> dict[str, Any]:
    return _verify_receipt(value, schema=schema, required_fields=fields)


def _replay_task_discharge_authority(
    value: Mapping[str, Any], terminal: Mapping[str, Any]
) -> tuple[str, ...]:
    """Replay the registered task adjudicator from its frozen boundary bytes."""

    from ztare.common.task_discharge import bind_task_discharge_receipt
    from ztare.leanmill.formal_task_boundary import (
        GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
        adjudicate_governed_formal_counterexample_task,
    )
    from ztare.leanmill.theory_adapter_registry import (
        adjudicate_theory_adapter_task,
        registered_theory_adapter_ids,
    )
    from ztare.leanmill.theory_program import TheoryProgram
    from ztare.leanmill.theory_task_discharge_successor import (
        CONSTRUCTION_RATIFICATION_TRANSITION_KEY,
        validate_construction_ratification_successor_bundle,
    )

    origin = _verify_authority_wrapper(
        value,
        schema=TASK_DISCHARGE_AUTHORITY_RECEIPT_SCHEMA,
        fields=frozenset(
            {
                "schema",
                "theory_program",
                "discharge_bundle",
                "discharge_consumption",
                "boundary_result",
                "authority",
            }
        ),
    )
    if origin.get("authority") != "registered_task_adjudicator_replay":
        raise ValueError("task-discharge closure origin has the wrong authority")
    program = TheoryProgram.from_json(origin.get("theory_program") or {})
    bundle = dict(origin.get("discharge_bundle") or {})
    consumption = dict(origin.get("discharge_consumption") or {})
    boundary = dict(origin.get("boundary_result") or {})
    bundle_core = {
        key: item for key, item in bundle.items() if key != "receipt_sha256"
    }
    consumption_core = {
        key: item for key, item in consumption.items()
        if key != "receipt_sha256"
    }
    boundary_core = {
        key: item for key, item in boundary.items() if key != "result_sha256"
    }
    bundle_ref = str(bundle.get("receipt_sha256") or "")
    consumption_ref = str(consumption.get("receipt_sha256") or "")
    boundary_ref = str(boundary.get("result_sha256") or "")
    if (
        terminal.get("context_hash") != program.context_hash
        or terminal.get("lineage_id") != program.lineage_id
        or bundle.get("schema") != "leanmill.theory_task_discharge.v1"
        or bundle.get("adapter_id") not in registered_theory_adapter_ids()
        or bundle.get("authority")
        != "registered_adapter_receipts_host_aggregation"
        or bundle_ref != content_hash(bundle_core)
        or consumption.get("schema")
        != "leanmill.theory_task_discharge_consumption.v1"
        or consumption_ref != content_hash(consumption_core)
        or boundary.get("schema") != "leanmill.frontier_boundary_result.v1"
        or boundary_ref != content_hash(boundary_core)
        or bundle.get("boundary_result_sha256") != boundary_ref
        or consumption.get("bundle_receipt_sha256") != bundle_ref
        or consumption.get("objective_status") != "discharged"
        or program.program_id
        not in set(consumption.get("authorized_program_ids") or ())
        or (bundle.get("program_outcomes") or {}).get(program.program_id)
        != "discharged"
    ):
        raise ValueError("task-discharge closure origin crossed campaign identity")

    transition_rows: dict[tuple[str, str], dict[str, Any]] = {}
    transition_evidence_refs: list[str] = []
    transition = bundle.get(CONSTRUCTION_RATIFICATION_TRANSITION_KEY)
    if transition is not None:
        bundle = validate_construction_ratification_successor_bundle(
            bundle, boundary
        )
        if not isinstance(transition, Mapping):  # validator gives the diagnostic
            raise ValueError("task-discharge successor transition is malformed")
        transition_evidence_refs.append(str(transition["receipt_sha256"]))
        for raw in transition.get("rows") or ():
            if not isinstance(raw, Mapping):
                raise ValueError("task-discharge successor row is malformed")
            key = (
                str(raw.get("program_id") or ""),
                str(raw.get("task_contract_sha256") or ""),
            )
            transition_rows[key] = dict(raw)
            transition_evidence_refs.extend(
                (
                    str(raw.get("receipt_sha256") or ""),
                    str(raw.get("aggregate_sha256") or ""),
                )
            )

    contracts = {
        contract.sha256: contract for contract in program.task_discharge_contracts
    }
    matched_refs: list[str] = []
    observed: set[str] = set()
    for raw in bundle.get("rows") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("task-discharge closure origin has a malformed row")
        row = dict(raw)
        if (
            row.get("program_id") != program.program_id
            or row.get("source") != "explicit_task"
        ):
            continue
        row_core = {
            key: item for key, item in row.items() if key != "receipt_sha256"
        }
        row_ref = str(row.get("receipt_sha256") or "")
        contract, receipt = bind_task_discharge_receipt(
            row.get("contract") or {}, row.get("receipt") or {}
        )
        frozen = contracts.get(contract.sha256)
        if (
            row_ref != content_hash(row_core)
            or row.get("contract_sha256") != contract.sha256
            or frozen is None
            or frozen.to_dict() != contract.to_dict()
            or receipt.status != "discharged"
        ):
            raise ValueError("task-discharge closure row changed identity")
        successor_row = transition_rows.get((program.program_id, contract.sha256))
        if successor_row is not None:
            final_receipt = (
                successor_row.get("aggregate") or {}
            ).get("final_task_discharge_receipt")
            if final_receipt != receipt.to_dict():
                raise ValueError(
                    "task-discharge closure row does not replay its successor"
                )
        else:
            replayed = (
                adjudicate_governed_formal_counterexample_task(
                    contract=contract,
                    boundary_result=boundary,
                )
                if contract.adjudicator_id
                == GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR
                else adjudicate_theory_adapter_task(
                    str(bundle["adapter_id"]),
                    contract,
                    boundary_result=boundary,
                )
            )
            if replayed.to_dict() != receipt.to_dict():
                raise ValueError(
                    "task-discharge closure row does not replay its adjudicator"
                )
        if contract.sha256 in observed:
            raise ValueError("task-discharge closure origin duplicated a task")
        observed.add(contract.sha256)
        matched_refs.append(row_ref)
    if observed != set(contracts):
        raise ValueError("task-discharge closure origin omitted a frozen task")
    residual = terminal.get("residual")
    if isinstance(residual, Mapping):
        from ztare.leanmill.formal_task_boundary import formal_task_parameters

        declared_matches = 0
        for contract in contracts.values():
            try:
                parameters = formal_task_parameters(contract)
            except KeyError:
                continue
            declared = parameters.get("generalization_residual")
            if not isinstance(declared, Mapping):
                continue
            if (
                declared.get("witness_id") == residual.get("witness_id")
                and declared.get("claim_id") == residual.get("claim_id")
                and declared.get("source_scope") == residual.get("source_scope")
                and tuple(str(ref) for ref in declared.get("evidence_refs") or ())
                == tuple(str(ref) for ref in residual.get("evidence_refs") or ())[:-1]
                and str(contract.sha256)
                == str((residual.get("evidence_refs") or [""])[-1])
            ):
                declared_matches += 1
        if declared_matches != 1:
            raise ValueError(
                "generalization closure origin does not own the declared residual"
            )
    return (
        *matched_refs,
        *tuple(ref for ref in transition_evidence_refs if ref),
        bundle_ref,
        consumption_ref,
        boundary_ref,
    )


def _replay_leaf_disposition_authority(
    value: Mapping[str, Any], terminal: Mapping[str, Any]
) -> tuple[str, ...]:
    origin = _verify_authority_wrapper(
        value,
        schema=LEAF_DISPOSITION_AUTHORITY_RECEIPT_SCHEMA,
        fields=frozenset({"schema", "workbench_receipt", "authority"}),
    )
    if origin.get("authority") != "registered_axiompack_leaf_workbench_replay":
        raise ValueError("leaf closure origin has the wrong authority")
    receipt = dict(origin.get("workbench_receipt") or {})
    receipt_core = {
        key: item for key, item in receipt.items() if key != "receipt_id"
    }
    receipt_id = str(receipt.get("receipt_id") or "")
    summary = receipt.get("output_summary")
    input_hashes = receipt.get("input_hashes")
    if (
        receipt.get("schema") != "leanmill.axiompack_workbench_receipt.v1"
        or receipt.get("capability_id") != "propose_lineage_disposition"
        or receipt.get("authority") != "deterministic_host"
        or receipt.get("context_hash") != terminal.get("context_hash")
        or receipt_id != "sha256:" + content_hash(receipt_core)
        or not isinstance(summary, Mapping)
        or not isinstance(input_hashes, Mapping)
        or set(input_hashes) != {"terminal_state", "reason", "evidence_refs"}
        or summary.get("status")
        != "terminal_lineage_disposition_proposed"
        or summary.get("lineage_id") != terminal.get("lineage_id")
        or summary.get("terminal_state") != terminal.get("terminal_state")
        or summary.get("reason_sha256") != input_hashes.get("reason")
        or input_hashes.get("terminal_state")
        != "sha256:" + content_hash(summary.get("terminal_state"))
        or input_hashes.get("evidence_refs")
        != "sha256:" + content_hash(summary.get("evidence_refs"))
        or not isinstance(summary.get("evidence_refs"), list)
        or not summary["evidence_refs"]
    ):
        raise ValueError("leaf closure origin does not replay its workbench action")
    return (*tuple(str(ref) for ref in summary["evidence_refs"]), receipt_id)


def _replay_terminal_transition_authority(
    value: Mapping[str, Any], terminal: Mapping[str, Any]
) -> tuple[str, ...]:
    origin = _verify_authority_wrapper(
        value,
        schema=TERMINAL_TRANSITION_AUTHORITY_RECEIPT_SCHEMA,
        fields=frozenset(
            {"schema", "context_hash", "transition_receipt", "authority"}
        ),
    )
    if (
        origin.get("authority")
        != "registered_campaign_terminal_transition_replay"
        or origin.get("context_hash") != terminal.get("context_hash")
        or terminal.get("terminal_state") != "retired_unresolved"
    ):
        raise ValueError("terminal transition closure origin crossed identity")
    transition = dict(origin.get("transition_receipt") or {})
    core = {
        key: item for key, item in transition.items()
        if key != "receipt_sha256"
    }
    transition_ref = str(transition.get("receipt_sha256") or "")
    schema = transition.get("schema")
    if transition_ref != content_hash(core):
        raise ValueError("terminal transition closure origin digest mismatch")
    if schema == "leanmill.budget_stop_receipt.v1":
        if (
            set(transition)
            != {
                "schema",
                "reason",
                "budget_digest",
                "elapsed_ms",
                "usage",
                "phase_usage",
                "outstanding_reservations",
                "attempt_id",
                "context_hash",
                "last_information_observation",
                "receipt_sha256",
            }
            or transition.get("context_hash") != terminal.get("context_hash")
            or not str(transition.get("reason") or "")
            or not str(transition.get("budget_digest") or "")
            or not str(transition.get("attempt_id") or "")
            or type(transition.get("elapsed_ms")) is not int
            or not isinstance(transition.get("usage"), Mapping)
            or not isinstance(transition.get("phase_usage"), Mapping)
            or not isinstance(transition.get("outstanding_reservations"), list)
        ):
            raise ValueError("budget stop crossed campaign context")
    elif schema == "leanmill.frontier_campaign_retirement.v1":
        if (
            set(transition)
            != {
                "schema",
                "status",
                "attempt_dir",
                "authority_ref",
                "reason",
                "prior_status",
                "receipt_sha256",
            }
            or transition.get("status") != "retired"
            or any(
                not str(transition.get(field) or "")
                for field in (
                    "attempt_dir",
                    "authority_ref",
                    "reason",
                    "prior_status",
                )
            )
        ):
            raise ValueError("campaign retirement origin is not terminal")
    else:
        raise ValueError("terminal transition closure origin is unregistered")
    return (transition_ref,)


def _replay_reviewed_family_objective_discharge_authority(
    value: Mapping[str, Any], terminal: Mapping[str, Any]
) -> tuple[str, ...]:
    """Replay a typed family discharge and its exact lineage projection."""

    from ztare.leanmill.reviewed_family_objective_discharge import (
        validate_reviewed_family_objective_discharge,
    )

    discharge = validate_reviewed_family_objective_discharge(value)
    source_run = discharge["source_pending_run"]
    lineage_id = str(terminal.get("lineage_id") or "")
    source_lineages = frozenset(
        str(value) for value in discharge["source_lineage_ids"]
    )
    frozen_lineages = frozenset(
        str(value) for value in discharge["frozen_lineage_ids"]
    )
    expected_state = (
        "objective_discharged"
        if lineage_id in source_lineages
        else "superseded"
    )
    if (
        terminal.get("context_hash") != source_run.get("context_hash")
        or lineage_id not in frozen_lineages
        or terminal.get("terminal_state") != expected_state
    ):
        raise ValueError(
            "reviewed-family discharge crossed its campaign lineage projection"
        )
    return (
        str(discharge["receipt_sha256"]),
        str(discharge["construction_objective_sha256"]),
        str(discharge["source_run_digest"]),
        str(discharge["lineage_synthesis_decision_sha256"]),
        str(discharge["finite_family_execution_sha256"]),
        str(discharge["admission_sha256"]),
        str(discharge["ratification_aggregate_sha256"]),
        str(discharge["governed_closure_record_sha256"]),
    )


def _replay_reviewed_family_exhaustion_discharge_authority(
    value: Mapping[str, Any], terminal: Mapping[str, Any]
) -> tuple[str, ...]:
    """Replay a family-scoped null and its explicit lineage projection."""

    from ztare.leanmill.reviewed_family_exhaustion_discharge import (
        validate_reviewed_family_exhaustion_discharge,
    )

    discharge = validate_reviewed_family_exhaustion_discharge(value)
    observation = discharge["observation"]
    lineage_id = str(terminal.get("lineage_id") or "")
    source_lineages = frozenset(
        str(item) for item in observation["source_lineage_ids"]
    )
    frozen_lineages = frozenset(
        str(item) for item in observation["frozen_lineage_ids"]
    )
    expected_state = (
        "objective_discharged"
        if lineage_id in source_lineages
        else "retired_unresolved"
    )
    if (
        terminal.get("context_hash")
        != observation["source_family_run"].get("context_hash")
        or lineage_id not in frozen_lineages
        or terminal.get("terminal_state") != expected_state
    ):
        raise ValueError(
            "reviewed family exhaustion crossed its lineage projection"
        )
    return (
        str(discharge["receipt_sha256"]),
        str(observation["receipt_sha256"]),
        str(observation["stop_permission_sha256"]),
        str(observation["finite_family_sha256"]),
        str(observation["forge_quarantine_receipt_sha256"]),
        str(observation["finite_family_execution_sha256"]),
        str(discharge["feedback_sha256"]),
        str(discharge["feedback_wave_binding_sha256"]),
        str(discharge["next_representation_authorship_sha256"]),
        str(discharge["next_representation_request_id"]),
    )


_CLOSURE_AUTHORITY_ROUTES: tuple[CampaignClosureAuthorityRoute, ...] = (
    CampaignClosureAuthorityRoute(
        authority="validated_theory_task_discharge_consumption",
        obligation_kind="lineage_disposition",
        terminal_states=frozenset({"objective_discharged"}),
        authority_receipt_schema=TASK_DISCHARGE_AUTHORITY_RECEIPT_SCHEMA,
        identity=_task_discharge_identity(),
        replay=_replay_task_discharge_authority,
    ),
    CampaignClosureAuthorityRoute(
        authority="campaign_owned_governed_formal_counterexample_adjudicator",
        obligation_kind="generalization_adjudication",
        terminal_states=frozenset({"refuted_general"}),
        authority_receipt_schema=TASK_DISCHARGE_AUTHORITY_RECEIPT_SCHEMA,
        identity=_task_discharge_identity(),
        replay=_replay_task_discharge_authority,
    ),
    CampaignClosureAuthorityRoute(
        authority="leaf_authored_workbench_disposition_host_validated",
        obligation_kind="lineage_disposition",
        terminal_states=frozenset({"rejected", "superseded"}),
        authority_receipt_schema=LEAF_DISPOSITION_AUTHORITY_RECEIPT_SCHEMA,
        identity=_leaf_disposition_identity(),
        replay=_replay_leaf_disposition_authority,
    ),
    CampaignClosureAuthorityRoute(
        authority="frontier_campaign_budget_or_retirement_transition",
        obligation_kind="lineage_disposition",
        terminal_states=frozenset({"retired_unresolved"}),
        authority_receipt_schema=TERMINAL_TRANSITION_AUTHORITY_RECEIPT_SCHEMA,
        identity=_terminal_transition_identity(),
        replay=_replay_terminal_transition_authority,
    ),
    CampaignClosureAuthorityRoute(
        authority=REVIEWED_FAMILY_OBJECTIVE_DISCHARGE_AUTHORITY,
        obligation_kind="lineage_disposition",
        terminal_states=frozenset({"objective_discharged", "superseded"}),
        authority_receipt_schema=_REVIEWED_FAMILY_OBJECTIVE_DISCHARGE_SCHEMA,
        identity=_reviewed_family_objective_discharge_identity(),
        replay=_replay_reviewed_family_objective_discharge_authority,
    ),
    CampaignClosureAuthorityRoute(
        authority=REVIEWED_FAMILY_EXHAUSTION_DISCHARGE_AUTHORITY,
        obligation_kind="lineage_disposition",
        terminal_states=frozenset(
            {"objective_discharged", "retired_unresolved"}
        ),
        authority_receipt_schema=_REVIEWED_FAMILY_EXHAUSTION_DISCHARGE_SCHEMA,
        identity=_reviewed_family_exhaustion_discharge_identity(),
        replay=_replay_reviewed_family_exhaustion_discharge_authority,
    ),
)


def _closure_authority_route(
    authority: str, *, obligation_kind: str
) -> CampaignClosureAuthorityRoute:
    matches = [
        route for route in _CLOSURE_AUTHORITY_ROUTES
        if route.authority == str(authority)
        and route.obligation_kind == obligation_kind
    ]
    if len(matches) != 1:
        raise ValueError("terminal receipt authority is not registered for this obligation")
    return matches[0]


def build_lineage_disposition_receipt(
    *,
    context_hash: str,
    lineage_id: str,
    terminal_state: str,
    evidence_refs: Sequence[str],
    authority: str,
    authority_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one terminal disposition from a registered authority receipt."""

    state = str(terminal_state)
    refs = tuple(str(ref) for ref in evidence_refs if str(ref).strip())
    route = _closure_authority_route(
        str(authority), obligation_kind="lineage_disposition"
    )
    if state not in _TERMINAL_LINEAGE_STATES or state not in route.terminal_states:
        raise ValueError("unsupported frozen-lineage terminal state for authority")
    if not all(str(value).strip() for value in (context_hash, lineage_id)):
        raise ValueError("lineage disposition identity cannot be empty")
    if not refs:
        raise ValueError("lineage disposition requires authority evidence")
    core = {
        "schema": LINEAGE_DISPOSITION_SCHEMA,
        "context_hash": str(context_hash),
        "lineage_id": str(lineage_id),
        "terminal_state": state,
        "evidence_refs": list(refs),
        "authority": str(authority),
        "authority_receipt": dict(authority_receipt),
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    _verify_lineage_disposition(receipt)
    return receipt


def lineage_disposition_from_terminal_transition(
    *,
    context_hash: str,
    lineage_id: str,
    transition_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Project a replayed budget stop or retirement onto one frozen lineage."""

    origin = build_terminal_transition_authority_receipt(
        transition_receipt, context_hash=context_hash
    )
    terminal = {
        "context_hash": str(context_hash),
        "lineage_id": str(lineage_id),
        "terminal_state": "retired_unresolved",
    }
    refs = _replay_terminal_transition_authority(origin, terminal)
    return build_lineage_disposition_receipt(
        **terminal,
        evidence_refs=refs,
        authority="frontier_campaign_budget_or_retirement_transition",
        authority_receipt=origin,
    )


def lineage_disposition_from_task_discharge(
    *,
    theory_program: Mapping[str, Any],
    discharge_bundle: Mapping[str, Any],
    discharge_consumption: Mapping[str, Any],
    boundary_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Project an already-validated task discharge into a lineage disposition."""

    from ztare.common.task_discharge import bind_task_discharge_receipt
    from ztare.leanmill.theory_program import TheoryProgram

    program = TheoryProgram.from_json(theory_program)
    bundle = dict(discharge_bundle)
    bundle_core = {
        key: value for key, value in bundle.items() if key != "receipt_sha256"
    }
    bundle_ref = str(bundle.get("receipt_sha256") or "")
    if (
        bundle.get("schema") != "leanmill.theory_task_discharge.v1"
        or bundle_ref != content_hash(bundle_core)
        or (bundle.get("program_outcomes") or {}).get(program.program_id)
        != "discharged"
    ):
        raise ValueError("task-discharge bundle does not discharge this program")
    consumption = dict(discharge_consumption)
    consumption_core = {
        key: value for key, value in consumption.items()
        if key != "receipt_sha256"
    }
    consumption_ref = str(consumption.get("receipt_sha256") or "")
    if (
        consumption.get("schema")
        != "leanmill.theory_task_discharge_consumption.v1"
        or consumption_ref != content_hash(consumption_core)
        or consumption.get("bundle_receipt_sha256") != bundle_ref
        or consumption.get("objective_status") != "discharged"
        or program.program_id
        not in set(consumption.get("authorized_program_ids") or ())
    ):
        raise ValueError("task-discharge consumption does not authorize this program")
    explicit_rows = [
        dict(row)
        for row in bundle.get("rows") or ()
        if isinstance(row, Mapping)
        and row.get("program_id") == program.program_id
        and row.get("source") == "explicit_task"
    ]
    if not explicit_rows:
        raise ValueError("discharged program has no explicit task receipt")
    row_refs = []
    for row in explicit_rows:
        row_core = {
            key: value for key, value in row.items() if key != "receipt_sha256"
        }
        if row.get("receipt_sha256") != content_hash(row_core):
            raise ValueError("task-discharge row digest mismatch")
        _, receipt = bind_task_discharge_receipt(
            row.get("contract") or {}, row.get("receipt") or {}
        )
        if receipt.status != "discharged":
            raise ValueError("program task receipt is not discharged")
        row_refs.append(str(row["receipt_sha256"]))
    origin = build_task_discharge_authority_receipt(
        theory_program=program.to_json(),
        discharge_bundle=bundle,
        discharge_consumption=consumption,
        boundary_result=boundary_result,
    )
    evidence_refs = _replay_task_discharge_authority(
        origin,
        {
            "context_hash": program.context_hash,
            "lineage_id": program.lineage_id,
            "terminal_state": "objective_discharged",
        },
    )
    return build_lineage_disposition_receipt(
        context_hash=program.context_hash,
        lineage_id=program.lineage_id,
        terminal_state="objective_discharged",
        evidence_refs=evidence_refs,
        authority="validated_theory_task_discharge_consumption",
        authority_receipt=origin,
    )


def lineage_dispositions_from_reviewed_family_objective_discharge(
    objective_discharge: Mapping[str, Any],
    *,
    current_blueprint: Any | None = None,
) -> tuple[dict[str, Any], ...]:
    """Project one exact family witness across its complete frozen lineage set.

    Source lineages authored the selected representation request and receive
    ``objective_discharged``.  Frozen siblings receive ``superseded`` because
    the same construction objective is existential and has already been met.
    Both projections retain the complete typed discharge for terminal replay.
    """

    from ztare.leanmill.reviewed_family_objective_discharge import (
        validate_reviewed_family_objective_discharge,
    )

    discharge = validate_reviewed_family_objective_discharge(
        objective_discharge,
        current_blueprint=current_blueprint,
    )
    context_hash = str(discharge["source_pending_run"]["context_hash"])
    source_lineages = frozenset(
        str(value) for value in discharge["source_lineage_ids"]
    )
    rows: list[dict[str, Any]] = []
    for lineage_id in discharge["frozen_lineage_ids"]:
        terminal = {
            "context_hash": context_hash,
            "lineage_id": str(lineage_id),
            "terminal_state": (
                "objective_discharged"
                if lineage_id in source_lineages
                else "superseded"
            ),
        }
        evidence_refs = _replay_reviewed_family_objective_discharge_authority(
            discharge, terminal
        )
        rows.append(
            build_lineage_disposition_receipt(
                **terminal,
                evidence_refs=evidence_refs,
                authority=REVIEWED_FAMILY_OBJECTIVE_DISCHARGE_AUTHORITY,
                authority_receipt=discharge,
            )
        )
    return tuple(rows)


def lineage_dispositions_from_reviewed_family_exhaustion_discharge(
    exhaustion_discharge: Mapping[str, Any],
    *,
    current_blueprint: Any | None = None,
) -> tuple[dict[str, Any], ...]:
    """Project the permitted family null without discarding sibling science.

    The family-source lineages satisfy the explicitly frozen information-yield
    stop.  Other lineages are terminally retired but remain unresolved; family
    rejection provides no supersession evidence for them.
    """

    from ztare.leanmill.reviewed_family_exhaustion_discharge import (
        validate_reviewed_family_exhaustion_discharge,
    )

    discharge = validate_reviewed_family_exhaustion_discharge(
        exhaustion_discharge, current_blueprint=current_blueprint
    )
    observation = discharge["observation"]
    context_hash = str(observation["source_family_run"]["context_hash"])
    source_lineages = frozenset(
        str(item) for item in observation["source_lineage_ids"]
    )
    rows: list[dict[str, Any]] = []
    for lineage_id in observation["frozen_lineage_ids"]:
        terminal = {
            "context_hash": context_hash,
            "lineage_id": str(lineage_id),
            "terminal_state": (
                "objective_discharged"
                if lineage_id in source_lineages
                else "retired_unresolved"
            ),
        }
        evidence_refs = (
            _replay_reviewed_family_exhaustion_discharge_authority(
                discharge, terminal
            )
        )
        rows.append(
            build_lineage_disposition_receipt(
                **terminal,
                evidence_refs=evidence_refs,
                authority=REVIEWED_FAMILY_EXHAUSTION_DISCHARGE_AUTHORITY,
                authority_receipt=discharge,
            )
        )
    return tuple(rows)


def build_generalization_residual_receipt(
    *,
    context_hash: str,
    lineage_id: str,
    witness_id: str,
    claim_id: str,
    evidence_refs: Sequence[str],
) -> dict[str, Any]:
    """Record the unbounded question exposed by a proved finite witness."""

    refs = tuple(str(ref) for ref in evidence_refs if str(ref).strip())
    if not all(
        str(value).strip()
        for value in (context_hash, lineage_id, witness_id, claim_id)
    ):
        raise ValueError("generalization residual identity cannot be empty")
    if not refs:
        raise ValueError("generalization residual requires finite-witness evidence")
    identity = {
        "context_hash": str(context_hash),
        "lineage_id": str(lineage_id),
        "witness_id": str(witness_id),
        "claim_id": str(claim_id),
    }
    core = {
        "schema": GENERALIZATION_RESIDUAL_SCHEMA,
        **identity,
        "residual_id": "generalization-residual:" + content_hash(identity),
        "source_scope": "proved_finite_witness",
        "evidence_refs": list(refs),
        "authority": "host_claim_scope_boundary",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def build_generalization_adjudication_receipt(
    residual: Mapping[str, Any],
    *,
    terminal_state: str,
    evidence_refs: Sequence[str],
    authority: str,
    authority_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a registered scientific adjudication to one exact residual."""

    residual_row = _verify_generalization_residual(residual)
    state = str(terminal_state)
    refs = tuple(str(ref) for ref in evidence_refs if str(ref).strip())
    route = _closure_authority_route(
        str(authority), obligation_kind="generalization_adjudication"
    )
    if (
        state not in _TERMINAL_GENERALIZATION_STATES
        or state not in route.terminal_states
    ):
        raise ValueError("unsupported generalization terminal state for authority")
    if not refs:
        raise ValueError("generalization adjudication requires authority evidence")
    core = {
        "schema": GENERALIZATION_ADJUDICATION_SCHEMA,
        "context_hash": str(residual_row["context_hash"]),
        "lineage_id": str(residual_row["lineage_id"]),
        "residual_id": str(residual_row["residual_id"]),
        "residual_receipt_sha256": str(residual_row["receipt_sha256"]),
        "terminal_state": state,
        "evidence_refs": list(refs),
        "authority": str(authority),
        "authority_receipt": dict(authority_receipt),
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    _verify_generalization_adjudication(receipt, residual=residual_row)
    return receipt


def generalization_adjudication_from_task_discharge(
    residual: Mapping[str, Any],
    *,
    theory_program: Mapping[str, Any],
    discharge_bundle: Mapping[str, Any],
    discharge_consumption: Mapping[str, Any],
    boundary_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Project a replayed governed counterexample task onto its residual."""

    residual_row = _verify_generalization_residual(residual)
    origin = build_task_discharge_authority_receipt(
        theory_program=theory_program,
        discharge_bundle=discharge_bundle,
        discharge_consumption=discharge_consumption,
        boundary_result=boundary_result,
    )
    refs = _replay_task_discharge_authority(
        origin,
        {
            "context_hash": residual_row["context_hash"],
            "lineage_id": residual_row["lineage_id"],
            "terminal_state": "refuted_general",
            "residual": residual_row,
        },
    )
    return build_generalization_adjudication_receipt(
        residual_row,
        terminal_state="refuted_general",
        evidence_refs=refs,
        authority="campaign_owned_governed_formal_counterexample_adjudicator",
        authority_receipt=origin,
    )


def _verify_lineage_disposition(value: Mapping[str, Any]) -> dict[str, Any]:
    row = _verify_receipt(
        value,
        schema=LINEAGE_DISPOSITION_SCHEMA,
        required_fields=frozenset(
            {
                "schema",
                "context_hash",
                "lineage_id",
                "terminal_state",
                "evidence_refs",
                "authority",
                "authority_receipt",
            }
        ),
    )
    if row["terminal_state"] not in _TERMINAL_LINEAGE_STATES:
        raise ValueError("lineage disposition is not terminal")
    if not isinstance(row["evidence_refs"], list) or not row["evidence_refs"]:
        raise ValueError("lineage disposition has no evidence")
    route = _closure_authority_route(
        str(row["authority"]), obligation_kind="lineage_disposition"
    )
    if row["terminal_state"] not in route.terminal_states:
        raise ValueError("lineage disposition authority cannot choose this state")
    authority_receipt = row.get("authority_receipt")
    if not isinstance(authority_receipt, Mapping):
        raise ValueError("lineage disposition lacks its authority receipt")
    expected_refs = route.replay(authority_receipt, row)
    if tuple(row["evidence_refs"]) != expected_refs:
        raise ValueError("lineage disposition evidence does not replay its origin")
    return row


def _verify_generalization_residual(value: Mapping[str, Any]) -> dict[str, Any]:
    row = _verify_receipt(
        value,
        schema=GENERALIZATION_RESIDUAL_SCHEMA,
        required_fields=frozenset(
            {
                "schema",
                "context_hash",
                "lineage_id",
                "witness_id",
                "claim_id",
                "residual_id",
                "source_scope",
                "evidence_refs",
                "authority",
            }
        ),
    )
    identity = {
        "context_hash": str(row["context_hash"]),
        "lineage_id": str(row["lineage_id"]),
        "witness_id": str(row["witness_id"]),
        "claim_id": str(row["claim_id"]),
    }
    if row["residual_id"] != "generalization-residual:" + content_hash(identity):
        raise ValueError("generalization residual changed identity")
    if row["source_scope"] != "proved_finite_witness":
        raise ValueError("generalization residual has unsupported source scope")
    if row["authority"] != "host_claim_scope_boundary":
        raise ValueError("generalization residual has unsupported authority")
    if not isinstance(row["evidence_refs"], list) or not row["evidence_refs"]:
        raise ValueError("generalization residual has no finite-witness evidence")
    return row


def _verify_generalization_adjudication(
    value: Mapping[str, Any],
    *,
    residual: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = _verify_receipt(
        value,
        schema=GENERALIZATION_ADJUDICATION_SCHEMA,
        required_fields=frozenset(
            {
                "schema",
                "context_hash",
                "lineage_id",
                "residual_id",
                "residual_receipt_sha256",
                "terminal_state",
                "evidence_refs",
                "authority",
                "authority_receipt",
            }
        ),
    )
    if row["terminal_state"] not in _TERMINAL_GENERALIZATION_STATES:
        raise ValueError("generalization adjudication is not terminal")
    if not isinstance(row["evidence_refs"], list) or not row["evidence_refs"]:
        raise ValueError("generalization adjudication has no evidence")
    route = _closure_authority_route(
        str(row["authority"]), obligation_kind="generalization_adjudication"
    )
    if row["terminal_state"] not in route.terminal_states:
        raise ValueError("generalization authority cannot choose this state")
    authority_receipt = row.get("authority_receipt")
    if not isinstance(authority_receipt, Mapping):
        raise ValueError("generalization adjudication lacks its authority receipt")
    terminal = dict(row)
    if residual is not None:
        terminal["witness_id"] = residual.get("witness_id")
        terminal["claim_id"] = residual.get("claim_id")
        terminal["residual"] = dict(residual)
    expected_refs = route.replay(authority_receipt, terminal)
    if tuple(row["evidence_refs"]) != expected_refs:
        raise ValueError("generalization evidence does not replay its origin")
    return row


def campaign_closure_gate(
    *,
    context_hash: str,
    frozen_lineage_ids: Sequence[str],
    lineage_dispositions: Sequence[Mapping[str, Any]],
    generalization_residuals: Sequence[Mapping[str, Any]] = (),
    generalization_adjudications: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Return a content-bound readiness verdict without choosing dispositions."""

    context = str(context_hash)
    lineages = tuple(str(value) for value in frozen_lineage_ids)
    if not context or not lineages or len(set(lineages)) != len(lineages):
        raise ValueError("campaign closure requires unique frozen lineage identities")

    dispositions: dict[str, dict[str, Any]] = {}
    for raw in lineage_dispositions:
        row = _verify_lineage_disposition(raw)
        lineage_id = str(row["lineage_id"])
        if row["context_hash"] != context or lineage_id not in lineages:
            raise ValueError("lineage disposition crossed the frozen campaign")
        if lineage_id in dispositions:
            raise ValueError("frozen lineage has multiple terminal dispositions")
        dispositions[lineage_id] = row

    residuals: dict[str, dict[str, Any]] = {}
    for raw in generalization_residuals:
        row = _verify_generalization_residual(raw)
        residual_id = str(row["residual_id"])
        if row["context_hash"] != context or row["lineage_id"] not in lineages:
            raise ValueError("generalization residual crossed the frozen campaign")
        if residual_id in residuals:
            raise ValueError("generalization residual identity is duplicated")
        residuals[residual_id] = row

    adjudications: dict[str, dict[str, Any]] = {}
    for raw in generalization_adjudications:
        residual_id = str(raw.get("residual_id") or "")
        source = residuals.get(residual_id)
        if source is None:
            raise ValueError("generalization adjudication crossed its residual")
        row = _verify_generalization_adjudication(raw, residual=source)
        if (
            row["context_hash"] != context
            or row["lineage_id"] != source["lineage_id"]
            or row["residual_receipt_sha256"] != source["receipt_sha256"]
        ):
            raise ValueError("generalization adjudication crossed its residual")
        if residual_id in adjudications:
            raise ValueError("generalization residual has multiple adjudications")
        adjudications[residual_id] = row

    missing_lineages = sorted(set(lineages) - set(dispositions))
    open_residuals = sorted(set(residuals) - set(adjudications))
    core = {
        "schema": CAMPAIGN_CLOSURE_GATE_SCHEMA,
        "context_hash": context,
        "frozen_lineage_ids": list(lineages),
        "lineage_disposition_receipt_sha256s": sorted(
            row["receipt_sha256"] for row in dispositions.values()
        ),
        "generalization_residual_receipt_sha256s": sorted(
            row["receipt_sha256"] for row in residuals.values()
        ),
        "generalization_adjudication_receipt_sha256s": sorted(
            row["receipt_sha256"] for row in adjudications.values()
        ),
        "missing_lineage_disposition_ids": missing_lineages,
        "unadjudicated_generalization_residual_ids": open_residuals,
        "ready": not missing_lineages and not open_residuals,
        "authority": "deterministic_campaign_terminal_obligation_gate",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def assert_campaign_closable(**kwargs: Any) -> dict[str, Any]:
    """Raise at the terminal transition if any obligation remains open."""

    receipt = campaign_closure_gate(**kwargs)
    if not receipt["ready"]:
        raise ValueError(
            "campaign terminal obligations remain open: "
            f"lineages={receipt['missing_lineage_disposition_ids']}, "
            "generalization_residuals="
            f"{receipt['unadjudicated_generalization_residual_ids']}"
        )
    return receipt


__all__ = [
    "CAMPAIGN_CLOSURE_GATE_SCHEMA",
    "CampaignClosureAuthorityRoute",
    "GENERALIZATION_ADJUDICATION_SCHEMA",
    "GENERALIZATION_RESIDUAL_SCHEMA",
    "LEAF_DISPOSITION_AUTHORITY_RECEIPT_SCHEMA",
    "LINEAGE_DISPOSITION_SCHEMA",
    "REVIEWED_FAMILY_EXHAUSTION_DISCHARGE_AUTHORITY",
    "REVIEWED_FAMILY_OBJECTIVE_DISCHARGE_AUTHORITY",
    "TASK_DISCHARGE_AUTHORITY_RECEIPT_SCHEMA",
    "TERMINAL_TRANSITION_AUTHORITY_RECEIPT_SCHEMA",
    "assert_campaign_closable",
    "build_generalization_adjudication_receipt",
    "build_generalization_residual_receipt",
    "build_leaf_disposition_authority_receipt",
    "build_lineage_disposition_receipt",
    "build_task_discharge_authority_receipt",
    "build_terminal_transition_authority_receipt",
    "campaign_closure_gate",
    "generalization_adjudication_from_task_discharge",
    "lineage_dispositions_from_reviewed_family_exhaustion_discharge",
    "lineage_dispositions_from_reviewed_family_objective_discharge",
    "lineage_disposition_from_task_discharge",
    "lineage_disposition_from_terminal_transition",
]
