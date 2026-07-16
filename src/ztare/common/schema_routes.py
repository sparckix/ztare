"""Explicit producer/consumer routes for consequence-bearing typed schemas.

Filename co-occurrence cannot establish that a write affects an active loop.
This registry records the category and downstream callable for schemas that
claim an operational consequence.  Cold proposals and terminal telemetry are
different lifecycle identities: they may be intentionally unread in the
current phase, but they cannot be counted as active capability or adapter-width
reduction.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
from pathlib import Path
from typing import Any, Literal, Mapping


RouteCategory = Literal[
    "operational_carrier",
    "cold_proposal",
    "terminal_telemetry",
    "cache_projection",
]


class OperationalRouteObstruction(RuntimeError):
    """An active producer output lacks its declared downstream consequence."""

    def __init__(self, audit: Mapping[str, Any]) -> None:
        self.audit = dict(audit)
        errors = list(self.audit.get("errors") or [])
        summary = "; ".join(
            f"{row.get('kind')}:{row.get('route_id') or row.get('contract_id')}"
            for row in errors[:4]
            if isinstance(row, Mapping)
        )
        super().__init__(
            "OPERATIONAL_ROUTE_HALT: consequence-bearing producer output is "
            "unconsumed" + (f" ({summary})" if summary else "")
        )


@dataclass(frozen=True)
class GoverningIdentity:
    """Category preflight required before a schema may claim consequence."""

    job: str
    owner: str
    lifecycle: str
    authority: str
    equality_relation: str
    compatibility_relation: str

    def __post_init__(self) -> None:
        for label, value in (
            ("job", self.job),
            ("owner", self.owner),
            ("lifecycle", self.lifecycle),
            ("authority", self.authority),
            ("equality_relation", self.equality_relation),
            ("compatibility_relation", self.compatibility_relation),
        ):
            if not str(value).strip():
                raise ValueError(f"schema governing identity requires {label}")

    def to_dict(self) -> dict[str, str]:
        return {
            "job": self.job,
            "owner": self.owner,
            "lifecycle": self.lifecycle,
            "authority": self.authority,
            "equality_relation": self.equality_relation,
            "compatibility_relation": self.compatibility_relation,
        }


@dataclass(frozen=True)
class SchemaRoute:
    route_id: str
    schema_id: str
    category: RouteCategory
    producer_symbol: str
    consumer_symbols: tuple[str, ...]
    active_phases: tuple[str, ...]
    identity: GoverningIdentity
    join_fields: tuple[str, ...] = ()
    producer_event: str = ""
    consumer_event: str = ""
    transport_events: tuple[str, ...] = ()
    artifact_name: str = ""
    external_producer: bool = False
    note: str = ""

    @property
    def consumer_required_now(self) -> bool:
        return self.category == "operational_carrier"


@dataclass(frozen=True)
class OutcomeTransition:
    """One member of a producer's closed outcome algebra."""

    outcome: str
    consumer_symbol: str
    target_state: str

    def __post_init__(self) -> None:
        for label, value in (
            ("outcome", self.outcome),
            ("consumer_symbol", self.consumer_symbol),
            ("target_state", self.target_state),
        ):
            if not str(value).strip():
                raise ValueError(f"outcome transition requires {label}")


@dataclass(frozen=True)
class ConsequenceContract:
    """Total producer-to-state-transition contract over declared outcomes."""

    contract_id: str
    producer_symbol: str
    outcomes: tuple[OutcomeTransition, ...]
    identity: GoverningIdentity
    artifact_name: str = "consequence_delivery.jsonl"

    def transition_for(self, outcome: str) -> OutcomeTransition:
        matches = [row for row in self.outcomes if row.outcome == str(outcome)]
        if len(matches) != 1:
            raise ValueError(
                f"{self.contract_id} has no unique transition for outcome={outcome!r}"
            )
        return matches[0]


SCHEMA_ROUTES: tuple[SchemaRoute, ...] = (
    SchemaRoute(
        route_id="deterministic_candidate_to_project_gate.v1",
        schema_id="ztare-deterministic-candidate-producer-receipt-v1",
        category="operational_carrier",
        producer_symbol=(
            "ztare.worldmodel.deterministic_candidate_producers:"
            "_catalog_operation_patch_compiler"
        ),
        consumer_symbols=(
            "ztare.worldmodel.deterministic_candidate_producers:evaluate_configured_candidates",
        ),
        active_phases=("checkpoint_identification",),
        identity=GoverningIdentity(
            job="carry a deterministic candidate into the project authority gate",
            owner="worldmodel candidate producer registry",
            lifecycle="one checkpoint-identification attempt",
            authority="project replay and holdout gate",
            equality_relation="candidate content SHA plus producer and phase",
            compatibility_relation="carrier contract and configured project-gate profile",
        ),
        join_fields=("candidate_sha256", "phase", "producer_id"),
        producer_event="materialized",
        consumer_event="consumed_by_project_gate",
        artifact_name="deterministic_candidate_producer_receipts.jsonl",
        note="proposal object is consumed in memory; paired events prove the gate consequence",
    ),
    SchemaRoute(
        route_id="chart_transport_to_episode_identity.v1",
        schema_id="ztare-chart-transport-morphism-v1",
        category="operational_carrier",
        producer_symbol="episode_collector:observation_chart_transport",
        consumer_symbols=("ztare.worldmodel.episode_log:_apply_identity_sidecar",),
        active_phases=("evidence_migration", "gate_load"),
        identity=GoverningIdentity(
            job="transport one observation packet between declared coordinate charts",
            owner="episode collector",
            lifecycle="one evidence migration between governed runs",
            authority="pointwise transport certificate over the declared witness bank",
            equality_relation="content SHA of source chart, target chart, morphism, and domain bank",
            compatibility_relation="exact commuting packet identity in the destination chart",
        ),
        external_producer=True,
        artifact_name="episode_001.identity.json",
        note="collector-authored chart migration is certified while loading the bank",
    ),
    SchemaRoute(
        route_id="evidence_epoch_to_prejudge_pin.v1",
        schema_id="ztare-evidence-epoch-snapshot-v1",
        category="operational_carrier",
        producer_symbol="ztare.common.observation_chart:capture_project_evidence_epoch",
        consumer_symbols=(
            "ztare.common.observation_chart:assert_project_evidence_epoch",
            "ztare.validator.core.pre_judge_gate:run_pre_judge_gate_harness",
        ),
        active_phases=("governed_run", "pre_judge"),
        identity=GoverningIdentity(
            job="freeze the active verifier footprint for one scientific search run",
            owner="governed autoresearch lifecycle",
            lifecycle="from baseline gate through the last candidate gate",
            authority="content hashes of selected evidence and chart sidecars",
            equality_relation="equal artifact path-to-content-digest map",
            compatibility_relation="no artifact identity change inside the active run",
        ),
        note="one evidence/chart epoch is pinned for the full scientific CEGAR run",
    ),
    SchemaRoute(
        route_id="counterexample_observation_to_domain_refinement.v1",
        schema_id="ztare-counterexample-observation-triple-v1",
        category="operational_carrier",
        producer_symbol=(
            "ztare.worldmodel.leaf_workbench:_active_frontier_observation_triple"
        ),
        consumer_symbols=(
            "ztare.worldmodel.leaf_workbench:run_worldmodel_lowerable_selector_miner",
        ),
        active_phases=("governed_run", "candidate_retry"),
        identity=GoverningIdentity(
            job=(
                "carry one falsifying source/proposal/consequence relation into "
                "operation-domain refinement"
            ),
            owner="governed counterexample workbench",
            lifecycle="one evidence epoch and proposal identity",
            authority="evidence collector plus deterministic proposal execution",
            equality_relation=(
                "semantic SHA of the chart-bound relation; storage locators and "
                "carrier lifecycle provenance are excluded"
            ),
            compatibility_relation=(
                "domain refinement receives the same observation and proposal "
                "identities before choosing compilation or acquisition"
            ),
        ),
        join_fields=("observation_sha256", "task_id"),
        producer_event="materialized",
        consumer_event="first_fire",
        transport_events=("delivered_to_synthesis_prompt",),
        artifact_name="counterexample_observation_routes.jsonl",
        note=(
            "adapter localization is presentation metadata; the refinement outcome "
            "then branches to deterministic compilation or factored acquisition"
        ),
    ),
    SchemaRoute(
        route_id="task_discharge_to_play_lifecycle.v1",
        schema_id="ztare-task-discharge-contract-v1",
        category="operational_carrier",
        producer_symbol="project_profile:task_discharge",
        consumer_symbols=("ztare.common.task_discharge:task_discharge_from_profile",),
        active_phases=("live_play", "sprint"),
        identity=GoverningIdentity(
            job="declare which authority can discharge the task lifecycle",
            owner="project task profile",
            lifecycle="declared task scope",
            authority="registered substrate adjudicator receipt",
            equality_relation="task-discharge contract content SHA",
            compatibility_relation="adapter supports the declared adjudicator id",
        ),
        external_producer=True,
        artifact_name="play_config.json",
    ),
    SchemaRoute(
        route_id="compiled_factors_to_planner.v1",
        schema_id="ztare-factored-planning-projection-v1",
        category="operational_carrier",
        producer_symbol=(
            "ztare.worldmodel.compiled_fiber_planning:append_projection_receipt"
        ),
        consumer_symbols=("ztare.common.factored_search:search_factored",),
        active_phases=("live_play", "self_play"),
        identity=GoverningIdentity(
            job="carry an accepted transition factorization into bounded search",
            owner="consumer-indexed planning projection",
            lifecycle="one carrier, evidence epoch, and terminal-edge hypothesis",
            authority="accepted carrier receipts plus adapter-attested edge witnesses",
            equality_relation="declared dominance key with ordered feasibility vector",
            compatibility_relation=(
                "projected transition images commute or emit a projection counterexample"
            ),
        ),
        join_fields=("projection_sha256", "problem_id"),
        producer_event="compiled",
        consumer_event="first_fire",
        artifact_name="factored_planning_projection.jsonl",
        note="allocation only; substrate adjudicator retains task-discharge authority",
    ),
    SchemaRoute(
        route_id="leaf_capability_proposal_to_strategy_review.v1",
        schema_id="ztare-leaf-workbench-capability-proposal-card-v1",
        category="cold_proposal",
        producer_symbol=(
            "ztare.common.leaf_workbench_proposals:sync_leaf_workbench_capability_proposals"
        ),
        consumer_symbols=(
            "ztare.common.leaf_workbench_proposals:review_leaf_workbench_capability_proposals",
        ),
        active_phases=("strategy_review",),
        identity=GoverningIdentity(
            job="queue a proposed capability for separate strategy review",
            owner="Strategy Office proposal ledger",
            lifecycle="cold until accepted, rejected, or superseded",
            authority="strategy decision membrane",
            equality_relation="proposal content identity and evidence bindings",
            compatibility_relation="paired lowerability obstruction or recurrence evidence",
        ),
        artifact_name="leaf_workbench_capability_proposals.jsonl",
        note="queued proposal has no current-candidate authority",
    ),
    SchemaRoute(
        route_id="post_freeze_mechanism_to_theory_navigation.v1",
        schema_id="leanmill.post_freeze_mechanism_feedback.v1",
        category="operational_carrier",
        producer_symbol=(
            "ztare.leanmill.frontier_campaign_runner:"
            "consume_post_freeze_interpretation_for_search"
        ),
        consumer_symbols=(
            "ztare.leanmill.frontier_campaign_runner:"
            "deliver_post_freeze_mechanism_feedback",
        ),
        active_phases=("navigation", "expansion"),
        identity=GoverningIdentity(
            job=(
                "carry one verifier-bound post-freeze mechanism into a fresh "
                "theory-search wave"
            ),
            owner="AxiomPack context lineage",
            lifecycle="one frozen context epoch and interpretation receipt",
            authority="proposal pressure only; the navigator authors the next move",
            equality_relation="context hash plus interpretation receipt SHA",
            compatibility_relation=(
                "the destination wave retains the same context epoch until a typed "
                "formula or language successor is separately admitted"
            ),
        ),
        join_fields=("context_hash", "interpretation_sha256"),
        producer_event="materialized",
        consumer_event="first_fire",
        artifact_name="post_freeze_mechanism_routes.jsonl",
        note=(
            "external source alignment remains hidden; only the mechanism proposal "
            "and verifier evidence enter navigation"
        ),
    ),
    SchemaRoute(
        route_id="post_freeze_research_disposition_to_theory_navigation.v1",
        schema_id="leanmill.post_freeze_research_disposition.v1",
        category="operational_carrier",
        producer_symbol=(
            "ztare.leanmill.frontier_campaign_runner:"
            "consume_post_freeze_interpretation_for_search"
        ),
        consumer_symbols=(
            "ztare.leanmill.frontier_campaign_runner:"
            "deliver_post_freeze_mechanism_feedback",
        ),
        active_phases=("navigation", "expansion"),
        identity=GoverningIdentity(
            job=(
                "carry one verifier-bound mechanism and source-independent "
                "recurrence disposition into a fresh theory-search wave"
            ),
            owner="AxiomPack context lineage",
            lifecycle="one frozen context epoch and interpretation receipt",
            authority=(
                "host-checked finite recurrence plus source-review pressure; "
                "the navigator authors the next move"
            ),
            equality_relation="context hash plus interpretation receipt SHA",
            compatibility_relation=(
                "source identities remain post-freeze while the destination "
                "receives only typed relation scope and residual disposition"
            ),
        ),
        join_fields=("context_hash", "interpretation_sha256"),
        producer_event="materialized",
        consumer_event="first_fire",
        artifact_name="post_freeze_research_disposition_routes.jsonl",
        note=(
            "source titles, URLs, and prose remain hidden; deterministic relation "
            "receipts and the bounded claim boundary shape the next discriminator"
        ),
    ),
    SchemaRoute(
        route_id="external_science_admission_to_resume_projection.v1",
        schema_id="leanmill.external_science_resume_admission.v1",
        category="operational_carrier",
        producer_symbol=(
            "ztare.leanmill.external_science_admission:"
            "admit_external_science_recovery"
        ),
        consumer_symbols=(
            "ztare.leanmill.external_science_admission:"
            "materialize_external_science_resume_context",
        ),
        active_phases=("crash_recovery", "navigation"),
        identity=GoverningIdentity(
            job=(
                "project one independently reviewed crash-recovery admission into "
                "a source-free navigator object"
            ),
            owner="AxiomPack crash-recovery admission gate",
            lifecycle="one frozen campaign attempt, context epoch, and theory lineage",
            authority=(
                "resume-context pressure only; no objective, task-discharge, or "
                "campaign-closing authority"
            ),
            equality_relation=(
                "campaign packet, run, context, lineage, evidence, and independent "
                "review content digests"
            ),
            compatibility_relation=(
                "navigation receives only the reviewed abstract projection while "
                "model, source, theorem, and artifact identities remain in the "
                "admission audit"
            ),
        ),
        join_fields=("context_hash", "admission_sha256"),
        producer_event="admitted",
        consumer_event="projected",
        artifact_name="external_science_admission_routes.jsonl",
        note=(
            "a validated admission remains visible route debt until its sensitive "
            "bindings are stripped by the registered projection"
        ),
    ),
    SchemaRoute(
        route_id="external_science_resume_context_to_navigation.v1",
        schema_id="leanmill.external_science_resume_context.v1",
        category="operational_carrier",
        producer_symbol=(
            "ztare.leanmill.external_science_admission:"
            "materialize_external_science_resume_context"
        ),
        consumer_symbols=(
            "ztare.leanmill.frontier_campaign_runner:"
            "deliver_external_science_resume_context",
        ),
        active_phases=("navigation", "expansion"),
        identity=GoverningIdentity(
            job="carry one source-free recovered-science projection into navigation",
            owner="AxiomPack crash-recovery admission gate",
            lifecycle="one admitted recovery result and first destination wave",
            authority=(
                "resume-context pressure only; no objective, task-discharge, or "
                "campaign-closing authority"
            ),
            equality_relation="context hash plus external-science admission digest",
            compatibility_relation=(
                "first fire preserves the reviewed abstract projection and excludes "
                "every audit-only identity"
            ),
        ),
        join_fields=("context_hash", "admission_sha256"),
        producer_event="materialized",
        consumer_event="first_fire",
        artifact_name="external_science_resume_context_routes.jsonl",
        note=(
            "distinct from post-freeze interpretation; recovered evidence can "
            "resume search but cannot certify the campaign's own work"
        ),
    ),
    SchemaRoute(
        route_id="external_science_negative_disposition_to_navigation.v1",
        schema_id="leanmill.external_science_negative_disposition.v1",
        category="operational_carrier",
        producer_symbol=(
            "ztare.leanmill.external_science_admission:"
            "_persist_negative_disposition"
        ),
        consumer_symbols=(
            "ztare.leanmill.frontier_campaign_runner:"
            "deliver_external_science_negative_disposition",
        ),
        active_phases=("crash_recovery", "navigation"),
        identity=GoverningIdentity(
            job=(
                "carry a reviewed non-admission or reviewer outage into the "
                "affected theory lineage as a typed retry residual"
            ),
            owner="AxiomPack crash-recovery admission gate",
            lifecycle="one recovery request and one destination navigation wave",
            authority=(
                "retry or revise recovery only; no negative scientific verdict, "
                "objective credit, task discharge, or campaign-closing authority"
            ),
            equality_relation="context hash plus negative-disposition receipt digest",
            compatibility_relation=(
                "review rejection carries only its source-free projection; runtime "
                "unavailability carries no mathematical projection"
            ),
        ),
        join_fields=("context_hash", "receipt_sha256"),
        producer_event="materialized",
        consumer_event="first_fire",
        artifact_name="external_science_negative_disposition_routes.jsonl",
        note=(
            "unavailability and mapping rejection remain resumable inputs and cannot "
            "be interpreted as theorem falsification"
        ),
    ),
)


CONSEQUENCE_CONTRACTS: tuple[ConsequenceContract, ...] = (
    ConsequenceContract(
        contract_id="factored_search_outcome_totality.v1",
        producer_symbol="ztare.common.factored_search:search_factored",
        outcomes=(
            OutcomeTransition(
                "edge_found",
                "ztare.worldmodel.planner:pursue_goal",
                "plan_ready",
            ),
            OutcomeTransition(
                "state_found",
                "ztare.worldmodel.planner:pursue_goal",
                "acquisition_plan_ready",
            ),
            OutcomeTransition(
                "projection_noncommuting",
                "ztare.worldmodel.planner:pursue_goal",
                "projection_refinement_required",
            ),
            OutcomeTransition(
                "start_outside_feasibility_domain",
                "ztare.worldmodel.planner:pursue_goal",
                "projection_inapplicable_fallback",
            ),
            OutcomeTransition(
                "search_budget_exhausted",
                "ztare.worldmodel.planner:pursue_goal",
                "bounded_search_fallback",
            ),
            OutcomeTransition(
                "projected_frontier_exhausted",
                "ztare.worldmodel.planner:pursue_goal",
                "projection_frontier_exhausted_fallback",
            ),
        ),
        identity=GoverningIdentity(
            job="deliver every projected-search outcome into planner control state",
            owner="worldmodel planning integration",
            lifecycle="one projected search invocation",
            authority="declared search result algebra plus live planner caller",
            equality_relation="contract, problem, and outcome identity",
            compatibility_relation="every produced outcome has one declared target state",
        ),
    ),
    ConsequenceContract(
        contract_id="lean_consequence_outcome_totality.v1",
        producer_symbol=(
            "ztare.leanmill.lean_consequence_bridge:"
            "execute_governed_lean_consequence"
        ),
        outcomes=tuple(
            OutcomeTransition(
                outcome,
                "ztare.leanmill.frontier_boundary:run_frontier_boundaries",
                target_state,
            )
            for outcome, target_state in (
                ("proved_attributed", "prediction_verified"),
                ("proved_unattributed", "attribution_diagnostic"),
                ("refuted_by_kernel", "counterexample_feedback"),
                ("rejected_by_governance", "governance_diagnostic"),
                ("unavailable", "instrument_unavailable"),
                ("unresolved", "proof_gap"),
                ("invalid", "invalid_proof_diagnostic"),
            )
        ),
        identity=GoverningIdentity(
            job="deliver every governed Lean consequence outcome into theory-search state",
            owner="LeanMill frontier boundary",
            lifecycle="one nominated conditional consequence",
            authority="governed Lean receipt and boundary transition",
            equality_relation="task id, governed receipt, and outcome",
            compatibility_relation="every outcome reaches search feedback or an explicit diagnostic state",
        ),
    ),
    ConsequenceContract(
        contract_id="theory_language_compilation_outcome_totality.v1",
        producer_symbol=(
            "ztare.leanmill.explore_axiom_space:lower_theory_language_request"
        ),
        outcomes=tuple(
            OutcomeTransition(
                outcome,
                "ztare.leanmill.frontier_campaign_runner:"
                "advance_frontier_language_expansion",
                target_state,
            )
            for outcome, target_state in (
                ("compiled", "successor_context"),
                ("rejected", "navigator_feedback"),
                ("unavailable", "adapter_gap"),
            )
        ),
        identity=GoverningIdentity(
            job="deliver every theory-language compiler outcome into campaign state",
            owner="AxiomPack language-successor lifecycle",
            lifecycle="one immutable request and source context epoch",
            authority="registered adapter compiler plus host campaign state machine",
            equality_relation="request id, source context hash, and compiler outcome",
            compatibility_relation=(
                "compiled reaches a successor context, rejected reaches feedback, "
                "and unavailable reaches a typed adapter gap"
            ),
        ),
    ),
    ConsequenceContract(
        contract_id="theory_program_task_outcome_totality.v1",
        producer_symbol=(
            "ztare.leanmill.theory_adapter_registry:"
            "adjudicate_theory_adapter_task"
        ),
        outcomes=tuple(
            OutcomeTransition(
                outcome,
                "ztare.leanmill.frontier_campaign_runner:"
                "_consume_theory_task_discharge",
                target_state,
            )
            for outcome, target_state in (
                ("open", "theory_task_open"),
                ("discharged", "theory_task_discharged"),
                ("unavailable", "theory_task_unavailable"),
            )
        ),
        identity=GoverningIdentity(
            job="deliver every typed theory-program task into campaign state",
            owner="AxiomPack frontier campaign",
            lifecycle="one frozen theory program and immutable boundary result",
            authority="registered theory adapter task-discharge receipt",
            equality_relation="task contract hash and adjudicator outcome",
            compatibility_relation=(
                "every task outcome reaches success, continued search, or an "
                "explicit adapter diagnostic"
            ),
        ),
    ),
)


def route_for_schema(schema_id: str) -> SchemaRoute | None:
    return next((route for route in SCHEMA_ROUTES if route.schema_id == schema_id), None)


def consequence_contract(contract_id: str) -> ConsequenceContract:
    matches = [
        contract for contract in CONSEQUENCE_CONTRACTS
        if contract.contract_id == str(contract_id)
    ]
    if len(matches) != 1:
        raise ValueError(f"unknown or duplicate consequence contract: {contract_id}")
    return matches[0]


def _resolve_symbol(reference: str) -> Any:
    module_name, separator, attribute_path = reference.partition(":")
    if not separator:
        raise ValueError(f"symbol reference needs module:attribute: {reference}")
    value: Any = importlib.import_module(module_name)
    for part in attribute_path.split("."):
        value = getattr(value, part)
    return value


def validate_schema_route_registry() -> tuple[dict[str, Any], ...]:
    """Statically resolve every code-owned producer and declared consumer."""
    failures: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_schemas: set[str] = set()
    for route in SCHEMA_ROUTES:
        if route.route_id in seen_ids or route.schema_id in seen_schemas:
            failures.append(
                {
                    "kind": "duplicate_route_identity",
                    "route_id": route.route_id,
                    "schema_id": route.schema_id,
                }
            )
        seen_ids.add(route.route_id)
        seen_schemas.add(route.schema_id)
        if route.consumer_required_now and not route.consumer_symbols:
            failures.append(
                {
                    "kind": "operational_schema_without_consumer",
                    "route_id": route.route_id,
                }
            )
        declared_events = (
            route.producer_event,
            route.consumer_event,
            *route.transport_events,
        )
        nonempty_events = tuple(event for event in declared_events if event)
        if len(nonempty_events) != len(set(nonempty_events)):
            failures.append(
                {
                    "kind": "route_event_identity_collision",
                    "route_id": route.route_id,
                    "events": list(nonempty_events),
                }
            )
        references = list(route.consumer_symbols)
        if not route.external_producer:
            references.append(route.producer_symbol)
        for reference in references:
            try:
                value = _resolve_symbol(reference)
            except Exception as exc:  # noqa: BLE001 - typed audit row
                failures.append(
                    {
                        "kind": "unresolvable_route_symbol",
                        "route_id": route.route_id,
                        "symbol": reference,
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )
                continue
            if not callable(value):
                failures.append(
                    {
                        "kind": "route_symbol_not_callable",
                        "route_id": route.route_id,
                        "symbol": reference,
                    }
                )
    consequence_ids: set[str] = set()
    for contract in CONSEQUENCE_CONTRACTS:
        if contract.contract_id in consequence_ids:
            failures.append({
                "kind": "duplicate_consequence_contract",
                "contract_id": contract.contract_id,
            })
        consequence_ids.add(contract.contract_id)
        outcome_names = [row.outcome for row in contract.outcomes]
        if not outcome_names or len(set(outcome_names)) != len(outcome_names):
            failures.append({
                "kind": "invalid_consequence_outcome_algebra",
                "contract_id": contract.contract_id,
                "outcomes": outcome_names,
            })
        references = [
            contract.producer_symbol,
            *(row.consumer_symbol for row in contract.outcomes),
        ]
        for reference in dict.fromkeys(references):
            try:
                value = _resolve_symbol(reference)
            except Exception as exc:  # noqa: BLE001 - typed audit row
                failures.append({
                    "kind": "unresolvable_consequence_symbol",
                    "contract_id": contract.contract_id,
                    "symbol": reference,
                    "error": f"{type(exc).__name__}:{exc}",
                })
                continue
            if not callable(value):
                failures.append({
                    "kind": "consequence_symbol_not_callable",
                    "contract_id": contract.contract_id,
                    "symbol": reference,
                })
    return tuple(failures)


def append_consequence_event(
    receipts_dir: str | Path,
    *,
    contract_id: str,
    subject_id: str,
    outcome: str,
    event: Literal["produced", "consumed"],
    evidence_refs: tuple[str, ...] = (),
    idempotent: bool = False,
) -> Path:
    """Append one side of a produced-to-consumed outcome transition."""
    contract = consequence_contract(contract_id)
    transition = contract.transition_for(outcome)
    if not str(subject_id).strip():
        raise ValueError("consequence delivery requires subject identity")
    row = {
        "schema": "ztare-consequence-delivery-v1",
        "contract_id": contract.contract_id,
        "subject_id": str(subject_id),
        "outcome": transition.outcome,
        "event": event,
        "producer_symbol": contract.producer_symbol,
        "consumer_symbol": transition.consumer_symbol,
        "target_state": transition.target_state,
        "evidence_refs": [str(ref) for ref in evidence_refs],
    }
    path = Path(receipts_dir) / contract.artifact_name
    path.parent.mkdir(parents=True, exist_ok=True)
    if idempotent and any(
        existing.get("contract_id") == contract.contract_id
        and existing.get("subject_id") == str(subject_id)
        and existing.get("outcome") == transition.outcome
        and existing.get("event") == event
        for existing in _read_jsonl(path)
    ):
        return path
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def _audit_consequence_rows(
    contract: ConsequenceContract,
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    pending: dict[tuple[str, str], list[dict[str, Any]]] = {}
    counts = {"produced": 0, "consumed": 0}
    errors: list[dict[str, Any]] = []
    for row in rows:
        if (
            row.get("schema") != "ztare-consequence-delivery-v1"
            or row.get("contract_id") != contract.contract_id
        ):
            continue
        outcome = str(row.get("outcome") or "")
        try:
            transition = contract.transition_for(outcome)
        except ValueError:
            errors.append({
                "kind": "undeclared_consequence_outcome",
                "contract_id": contract.contract_id,
                "row": row,
            })
            continue
        if (
            row.get("consumer_symbol") != transition.consumer_symbol
            or row.get("target_state") != transition.target_state
        ):
            errors.append({
                "kind": "consequence_transition_identity_mismatch",
                "contract_id": contract.contract_id,
                "row": row,
            })
            continue
        key = (str(row.get("subject_id") or ""), outcome)
        event = row.get("event")
        if event == "produced":
            counts["produced"] += 1
            pending.setdefault(key, []).append(row)
        elif event == "consumed":
            counts["consumed"] += 1
            if pending.get(key):
                pending[key].pop(0)
            else:
                errors.append({
                    "kind": "consequence_consume_without_produce",
                    "contract_id": contract.contract_id,
                    "row": row,
                })
        else:
            errors.append({
                "kind": "invalid_consequence_event",
                "contract_id": contract.contract_id,
                "row": row,
            })
    orphaned = [row for open_rows in pending.values() for row in open_rows]
    if orphaned:
        errors.append({
            "kind": "produced_outcome_without_state_transition",
            "contract_id": contract.contract_id,
            "count": len(orphaned),
            "examples": orphaned[:3],
        })
    return errors, counts


def assert_schema_route(schema_id: str, *, category: RouteCategory) -> SchemaRoute:
    """Writer-side preflight: consequence category must already have a route."""
    route = route_for_schema(schema_id)
    if route is None:
        raise ValueError(f"typed schema has no registered route: {schema_id}")
    if route.category != category:
        raise ValueError(
            f"schema route category mismatch for {schema_id}: "
            f"registered={route.category}, attempted={category}"
        )
    if route.consumer_required_now and not route.consumer_symbols:
        raise ValueError(f"operational schema has no registered consumer: {schema_id}")
    return route


def append_schema_route_event(
    project_dir: str | Path,
    *,
    schema_id: str,
    event: str,
    join_values: Mapping[str, Any],
    payload: Mapping[str, Any] | None = None,
) -> Path:
    """Append one idempotent producer/consumer event for an operational route."""

    route = assert_schema_route(schema_id, category="operational_carrier")
    allowed_events = {
        route.producer_event,
        route.consumer_event,
        *route.transport_events,
    }
    if not event or event not in allowed_events:
        raise ValueError(
            f"event {event!r} is outside route {route.route_id}: {sorted(allowed_events)}"
        )
    missing = [field for field in route.join_fields if join_values.get(field) in (None, "")]
    if missing:
        raise ValueError(f"schema route event is missing join fields: {missing}")
    if not route.artifact_name:
        raise ValueError(f"schema route {route.route_id} has no event artifact")
    path = Path(project_dir) / "workspace" / route.artifact_name
    row = {
        "schema": route.schema_id,
        "route_id": route.route_id,
        "event": event,
        **{field: join_values[field] for field in route.join_fields},
    }
    if payload:
        row["payload"] = dict(payload)
    existing = _read_jsonl(path)
    if any(
        prior.get("schema") == route.schema_id
        and prior.get("event") == event
        and all(prior.get(field) == row.get(field) for field in route.join_fields)
        for prior in existing
    ):
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _unconsumed_operational_rows(route: SchemaRoute, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match idempotent producer/consumer events by governing identity."""
    if not route.producer_event or not route.consumer_event:
        return []
    produced: dict[tuple[Any, ...], dict[str, Any]] = {}
    consumed: set[tuple[Any, ...]] = set()
    for row in rows:
        if row.get("schema") != route.schema_id:
            continue
        key = tuple(row.get(field) for field in route.join_fields)
        event = row.get("event")
        if event == route.producer_event:
            produced.setdefault(key, row)
        elif event == route.consumer_event:
            consumed.add(key)
    return [row for key, row in produced.items() if key not in consumed]


def audit_project_schema_routes(
    project_dir: str | Path,
    *,
    entering_phase: str = "",
) -> dict[str, Any]:
    """Audit registered routes plus instance-level operational consumption.

    At a phase-entry boundary, an open edge owned by that phase is pending
    work, rather than an orphan.  The same edge remains fatal at every exit
    boundary, so ``active_phases`` cannot become a permanent exemption.
    """
    project = Path(project_dir)
    workspace = project / "workspace"
    errors = list(validate_schema_route_registry())
    warnings: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for route in SCHEMA_ROUTES:
        artifact = workspace / route.artifact_name if route.artifact_name else None
        if route.artifact_name == "episode_001.identity.json":
            artifact = project / "raw" / "episodes" / route.artifact_name
        elif route.artifact_name == "play_config.json":
            artifact = project / route.artifact_name
        exists = bool(artifact and artifact.is_file())
        row = {
            "route_id": route.route_id,
            "schema_id": route.schema_id,
            "category": route.category,
            "artifact": str(artifact) if artifact else None,
            "artifact_exists": exists,
            "consumer_symbols": list(route.consumer_symbols),
            "governing_identity": route.identity.to_dict(),
        }
        if exists and route.category == "operational_carrier" and route.producer_event:
            pending = _unconsumed_operational_rows(route, _read_jsonl(artifact))
            row["unconsumed_count"] = len(pending)
            if pending:
                if entering_phase and entering_phase in route.active_phases:
                    row["pending_for_entering_phase"] = entering_phase
                else:
                    errors.append(
                        {
                            "kind": "operational_write_without_downstream_consume",
                            "route_id": route.route_id,
                            "count": len(pending),
                            "examples": pending[:3],
                        }
                    )
        rows.append(row)
    for contract in CONSEQUENCE_CONTRACTS:
        artifact = workspace / contract.artifact_name
        delivery_rows = _read_jsonl(artifact)
        consequence_errors, counts = _audit_consequence_rows(contract, delivery_rows)
        errors.extend(consequence_errors)
        rows.append({
            "route_id": contract.contract_id,
            "schema_id": "ztare-consequence-delivery-v1",
            "category": "operational_carrier",
            "artifact": str(artifact),
            "artifact_exists": artifact.is_file(),
            "producer_symbol": contract.producer_symbol,
            "consumer_symbols": sorted({
                transition.consumer_symbol for transition in contract.outcomes
            }),
            "governing_identity": contract.identity.to_dict(),
            "declared_outcomes": [transition.outcome for transition in contract.outcomes],
            "produced_count": counts["produced"],
            "consumed_count": counts["consumed"],
            "unconsumed_count": max(0, counts["produced"] - counts["consumed"]),
        })
    return {
        "schema": "ztare-schema-route-audit-v1",
        "status": "fail" if errors else ("debt" if warnings else "pass"),
        "halt_required": bool(errors),
        "errors": errors,
        "warnings": warnings,
        "routes": rows,
    }


def assert_operational_routes_ready(
    project_dir: str | Path,
    *,
    entering_phase: str = "",
) -> dict[str, Any]:
    """Fence mutation while an operational producer-to-consumer route is open.

    The audit already distinguishes operational carriers from cold proposals,
    terminal telemetry, and caches.  This function gives that distinction a
    control consequence before another scientific mutation is generated.  A
    named entry phase may accept only the edges whose registered lifecycle
    includes that phase; callers must run the strict form at the phase exit.
    """

    audit = audit_project_schema_routes(project_dir, entering_phase=entering_phase)
    if audit.get("halt_required"):
        raise OperationalRouteObstruction(audit)
    return audit


def observe_dispatched_schema_route_delivery(
    project_dir: str | Path,
    *,
    records: list[dict[str, Any]],
    rendered_text: str,
    consumer: str,
    attempt_id: str,
) -> tuple[str, ...]:
    """Record that a typed route envelope reached a synthesis prompt.

    Delivery is transport evidence only.  It never emits the route's consumer
    event and therefore cannot discharge a producer-to-consequence edge.  The
    registered executable consumer must emit ``first_fire`` after it changes
    the candidate/action surface.  Producer vocabulary remains opaque.
    """

    delivered: list[str] = []
    text = str(rendered_text or "")
    consumer_id = str(consumer or "").strip()
    synthesis_attempt_id = str(attempt_id or "").strip()
    if not consumer_id or not synthesis_attempt_id:
        raise ValueError("schema route delivery requires consumer and attempt identity")
    for record in records:
        envelope = record.get("route_delivery") if isinstance(record, dict) else None
        if not isinstance(envelope, Mapping):
            continue
        schema_id = str(envelope.get("schema_id") or "").strip()
        event = str(envelope.get("event") or "").strip()
        join_values = envelope.get("join_values")
        anchors = envelope.get("render_anchors")
        if not schema_id or not event or not isinstance(join_values, Mapping):
            raise ValueError("route delivery envelope is incomplete")
        if not isinstance(anchors, (list, tuple)) or not anchors:
            raise ValueError("route consumption envelope requires render anchors")
        normalized_anchors = tuple(str(anchor) for anchor in anchors if str(anchor))
        if len(normalized_anchors) != len(anchors):
            raise ValueError("route consumption envelope has an empty render anchor")
        if not all(anchor in text for anchor in normalized_anchors):
            continue
        route = assert_schema_route(schema_id, category="operational_carrier")
        if event not in route.transport_events:
            raise ValueError(
                "prompt delivery may emit only a registered transport event"
            )
        append_schema_route_event(
            project_dir,
            schema_id=schema_id,
            event=event,
            join_values=join_values,
            payload={
                "consumer": consumer_id,
                "synthesis_attempt_id": synthesis_attempt_id,
            },
        )
        delivered.append(route.route_id)
    return tuple(dict.fromkeys(delivered))
