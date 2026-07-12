"""Canonical runtime door for one frontier AxiomPack campaign."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
import uuid
from typing import Any, Mapping

from ztare.common.subscription_agent_runtime import subscription_dispatch_budget_scope
from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment
from ztare.leanmill import prompts
from ztare.leanmill.common import read_json, write_json_atomic, write_text_atomic
from ztare.leanmill.explore_axiom_space import (
    _freeze_theory_conflict_memory,
    _learn_navigation_conflicts,
    admit_frontier_formula_epoch,
    drive_frontier_navigation,
    execute_frontier_boundaries,
    explore_axiom_space,
    finish_frontier_navigation,
    freeze_frontier_formula_successor_request,
    packet_for_frontier_context,
)
from ztare.leanmill.exploration_budget import (
    BudgetExceeded,
    ExplorationBudget,
    ExplorationBudgetLedger,
)
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_agent_runtime import (
    FrontierAgentConfig,
    SubscriptionJSONRole,
    make_subscription_adapter_reviewer,
    make_subscription_frontier_compiler_roles,
    make_subscription_theory_navigator,
    scoped_frontier_agent_environment,
)
from ztare.leanmill.frontier_campaign import (
    sign_frontier_campaign,
    validate_campaign_artifact_binding,
    verify_campaign_artifact_signature,
)
from ztare.leanmill.frontier_campaign_definition import FrontierCampaignDefinition
from ztare.leanmill.frontier_blueprint import (
    FrontierTheoryBlueprint,
    host_isolated_lineage_count,
    frontier_objective_contract,
    navigator_selection_mode,
)
from ztare.leanmill.frontier_campaign_definition import load_frontier_campaign_definition
from ztare.leanmill.lean_consequence_bridge import (
    execute_governed_lean_consequence,
    recheck_governed_lean_consequence,
    render_lean_consequence_task,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_language import TheoryLanguageExpansionRequest
from ztare.leanmill.theory_lineage_runner import (
    aggregate_host_isolated_theory_lineages,
    run_host_isolated_theory_lineages,
)
from ztare.leanmill.theory_lineage_synthesis import (
    lineage_synthesis_input,
    lineage_synthesis_output_schema,
    validate_lineage_synthesis_decision,
)
from ztare.leanmill.theory_program import derive_context_lineage_id
from ztare.leanmill.theory_campaign_journal import (
    IdempotentReplayJournal,
    TheoryCampaignEvent,
    TheoryCampaignJournal,
)
from ztare.leanmill.theory_navigator import run_interactive_theory_navigator
from ztare.leanmill.typed_axiom_proposal import TypedAxiomProposal
from ztare.leanmill import work_queue


def _read_durable_navigator_decisions(
    call_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load contiguous immutable calls, skipping receipted pre-inference failures."""

    calls: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for index in range(1_000):
        prefix = call_dir / f"{index:03d}"
        call = read_json(prefix.with_suffix(".call.json"), None)
        if not isinstance(call, dict):
            break
        calls.append({**call, "replayed": True, "artifact_index": index})
        if int(call.get("returncode", 1)) != 0:
            if int(call.get("provider_call_charge", 1)) == 0:
                continue
            raise ValueError("durable navigator trace contains a charged failed call")
        result_path = prefix.with_suffix(".result.json")
        if not result_path.is_file():
            raise ValueError("successful durable navigator call has no result bytes")
        result_text = result_path.read_text(encoding="utf-8")
        if content_hash({"result": result_text}) != call.get("result_digest"):
            raise ValueError("durable navigator result digest mismatch")
        decision = json.loads(result_text)
        if not isinstance(decision, dict):
            raise ValueError("durable navigator result is not an object")
        decisions.append(decision)
    return calls, decisions


def _durable_navigator_decisions(
    call_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return _read_durable_navigator_decisions(call_dir)


def _replay_navigator_decisions(
    context: Any,
    blueprint: FrontierTheoryBlueprint,
    decisions: list[dict[str, Any]],
    journal: Any,
    *,
    attempt_id: str,
    campaign_id: str,
    epoch: int,
    lineage_id: str = "",
    max_finalists: int | None = None,
    prior_conflict_rows: tuple[Mapping[str, Any], ...] = (),
    initial_trace: tuple[Mapping[str, Any], ...] = (),
    prior_agent_turns: int = 0,
    round_offset: int = 0,
) -> dict[str, Any]:
    if not decisions:
        raise ValueError("durable navigation replay requires a decision")

    return run_interactive_theory_navigator(
        context,
        blueprint,
        journal,
        agent_fn=lambda _prompt: (_ for _ in ()).throw(
            RuntimeError("durable replay attempted a provider call")
        ),
        attempt_id=attempt_id,
        campaign_id=campaign_id,
        max_rounds=round_offset + len(decisions),
        max_finalists=(
            int(blueprint.query_budget.get("max_finalists", 8))
            if max_finalists is None
            else max_finalists
        ),
        epoch=epoch,
        lineage_id=lineage_id,
        prior_conflict_rows=prior_conflict_rows,
        initial_trace=initial_trace,
        prior_agent_turns=prior_agent_turns,
        round_offset=round_offset,
        replay_decisions=tuple(decisions),
    )


def frontier_agent_role(
    definition: FrontierCampaignDefinition,
    *,
    role_name: str,
    repo: Path,
    artifact_dir: Path,
    instance_id: str = "",
) -> SubscriptionJSONRole:
    runtime = dict(definition.runtime)
    values = dict(runtime.get("defaults") or {})
    values.update(dict((runtime.get("role_overrides") or {}).get(role_name) or {}))
    from ztare.common.llm_runtime import subscription_model_route

    requested_model = str(values.get("model") or "gpt-5.4-mini")
    resolved_runtime, resolved_model = subscription_model_route(
        requested_model,
        requested_runtime=str(values.get("runtime") or "codex"),
    )
    config = FrontierAgentConfig(
        runtime=resolved_runtime,
        model=resolved_model,
        reasoning_effort=str(values.get("reasoning_effort") or "low"),
        timeout_seconds=min(
            definition.budget.wall_clock_s,
            int(values.get("timeout_seconds") or 300),
        ),
        visible_workbench=bool(values.get("visible_workbench", False)),
        web_research=bool(
            values.get("web_research", role_name == "post_freeze_interpreter")
        ),
        governed_pool=bool(values.get("governed_pool", False)),
        allow_subscription_failover=bool(
            values.get("allow_subscription_failover", False)
        ),
    )
    output_schema = None
    if role_name == "navigator" and config.runtime == "codex":
        from ztare.leanmill.axiompack_leaf_workbench import (
            navigator_decision_output_schema,
        )

        output_schema = navigator_decision_output_schema()
    elif role_name == "lineage_synthesizer" and config.runtime == "codex":
        output_schema = lineage_synthesis_output_schema()
    instance = str(instance_id).strip()
    artifact_name = role_name if not instance else f"{role_name}.{instance}"
    agent_id = f"axiompack-{role_name}" + (f"-{instance}" if instance else "")
    return SubscriptionJSONRole(
        role=role_name,
        agent_id=agent_id,
        repo=repo,
        artifact_dir=artifact_dir / artifact_name,
        config=config,
        output_schema=output_schema,
    )


def _write_secret(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _semantic_profile_admission_count(directory: Path) -> int:
    count = 0
    for path in directory.glob("frontier_formula_epoch_admission.epoch-*.json"):
        row = read_json(path, {})
        count += row.get(
            "bounded_semantic_coordinate_new",
            row.get("bounded_semantic_profile_new"),
        ) is True
    return count


def _load_campaign_attempt(directory: Path) -> tuple[Any, Any, dict, dict, Any]:
    definition = load_frontier_campaign_definition(
        directory / "campaign_definition.yaml"
    )
    blueprint_row = read_json(directory / "blueprint.json", None)
    budget_row = read_json(directory / "budget.json", None)
    campaign = read_json(directory / "campaign.json", None)
    if not all(isinstance(row, dict) and row for row in (
        blueprint_row, budget_row, campaign
    )):
        raise ValueError("campaign attempt is not compiled and frozen")
    blueprint = FrontierTheoryBlueprint.from_json(blueprint_row)
    formal = directory / "formal_context.json"
    evidence = directory / "evidence_context.json"
    if formal.is_file():
        from ztare.leanmill.finite_theory_context import load_formal_theory_context

        context = load_formal_theory_context(formal)
    elif evidence.is_file():
        from ztare.leanmill.evidence_theory_context import load_evidence_theory_context

        context = load_evidence_theory_context(evidence)
    else:
        raise ValueError("campaign context snapshot is missing")
    validate_campaign_artifact_binding(
        campaign,
        blueprint_id=blueprint.blueprint_id,
        context_hash=context.context_hash,
    )
    public_key = directory / "campaign_signer_public.pem"
    if not public_key.is_file() or not verify_campaign_artifact_signature(
        campaign,
        public_key_pem=public_key.read_text(encoding="utf-8"),
    ):
        raise ValueError("campaign artifact signature does not verify")
    return definition, blueprint, budget_row, campaign, context


# A frontier attempt has one mutable journal and one budget ledger.  Those are
# not CvRDT fact logs, so the attempt—not an individual lineage or epoch—is the
# queue ownership unit.  The root signed packet remains stable while a
# successor context advances the active epoch; the heartbeat carries that
# changing epoch for inspection without making it a second lock key.
_FRONTIER_ATTEMPT_LEASE_KIND = "frontier_attempt_epoch"
_FRONTIER_ATTEMPT_LEASE_SCHEMA = "leanmill.frontier_attempt_lease.v1"
_FRONTIER_ATTEMPT_LEASE_MAX_ATTEMPTS = 1_000_000_000
_DEFAULT_FRONTIER_ATTEMPT_LEASE_S = 900


class FrontierAttemptLeaseBusy(RuntimeError):
    """Raised when another host owns an unexpired mutable frontier attempt."""


class FrontierAttemptLeaseLost(RuntimeError):
    """Raised when a host can no longer renew its frontier attempt lease."""


def _frontier_root_campaign(directory: Path) -> Mapping[str, Any] | None:
    """Return the epoch-zero signed campaign, falling back before its archive exists."""

    archived = directory / "campaign.epoch-000.json"
    row = read_json(
        archived if archived.is_file() else directory / "campaign.json", None
    )
    return row if isinstance(row, Mapping) else None


def _frontier_attempt_binding(directory: Path) -> dict[str, str]:
    """Stable queue identity for one attempt, independent of local filesystem paths."""

    attempt_id = directory.name.strip()
    if not attempt_id:
        raise ValueError("frontier attempt lease requires a named attempt directory")
    campaign = _frontier_root_campaign(directory)
    packet = campaign.get("packet") if isinstance(campaign, Mapping) else None
    if isinstance(packet, Mapping):
        campaign_id = str(packet.get("campaign_id") or "").strip()
        packet_digest = str(campaign.get("packet_digest") or "").strip()
        visible_context = packet.get("visible_context_manifest") or {}
        context_hash = str(
            packet.get("context_hash")
            or (
                visible_context.get("context_hash")
                if isinstance(visible_context, Mapping)
                else ""
            )
            or ""
        ).strip()
        if campaign_id and packet_digest and context_hash:
            return {
                "attempt_id": attempt_id,
                "campaign_id": campaign_id,
                "packet_digest": packet_digest,
                "root_context_hash": context_hash,
            }

    # A stop can arrive while compilation is between its initial budget write
    # and packet signing.  Older local interpretation callers likewise carry
    # only a frozen budget.  This compatibility identity stays content-bound;
    # distributed continuations use the signed branch above.
    brief = read_json(directory / "brief.json", {})
    budget = read_json(directory / "budget.json", {})
    brief_id = str(brief.get("brief_id") or "").strip() if isinstance(brief, Mapping) else ""
    budget_digest = (
        str(budget.get("budget_digest") or "").strip()
        if isinstance(budget, Mapping)
        else ""
    )
    if budget_digest:
        return {
            "attempt_id": attempt_id,
            "campaign_id": f"bootstrap:{brief_id or 'legacy-budget'}",
            "packet_digest": budget_digest,
            "root_context_hash": "bootstrap",
        }
    raise ValueError("frontier attempt has no signed or bootstrap campaign identity")


def frontier_attempt_work_id(attempt_dir: str | Path) -> str:
    """Return the stable work-bus key for an attempt's mutable state."""

    binding = _frontier_attempt_binding(Path(attempt_dir))
    encoded = json.dumps(binding, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "frontier_attempt__" + hashlib.sha256(encoded).hexdigest()[:24]


def _frontier_attempt_queue_db() -> str:
    return str(
        os.environ.get("ZTARE_LEANMILL_QUEUE_DB")
        or os.environ.get("LEANMILL_QUEUE_DB")
        or work_queue.DEFAULT_DB
    )


def _frontier_attempt_lease_seconds() -> int:
    raw = os.environ.get("ZTARE_LEANMILL_FRONTIER_ATTEMPT_LEASE_S", "")
    try:
        return max(30, int(raw)) if raw else _DEFAULT_FRONTIER_ATTEMPT_LEASE_S
    except ValueError:
        return _DEFAULT_FRONTIER_ATTEMPT_LEASE_S


class _FrontierAttemptLease:
    """Host-side lease/renewal around an attempt's mutable transaction state."""

    def __init__(
        self,
        attempt_dir: str | Path,
        *,
        action: str,
        queue_db: str | None = None,
        worker_id: str | None = None,
        lease_s: int | None = None,
        heartbeat_s: float | None = None,
    ) -> None:
        self.directory = Path(attempt_dir)
        self.binding = _frontier_attempt_binding(self.directory)
        self.action = str(action).strip() or "frontier_mutation"
        self.work_id = frontier_attempt_work_id(self.directory)
        self.queue_db = str(queue_db or _frontier_attempt_queue_db())
        self.lease_s = max(1, int(lease_s or _frontier_attempt_lease_seconds()))
        self.worker_id = worker_id or (
            f"axiompack-frontier:{work_queue.node_id()}:{os.getpid()}:"
            f"{uuid.uuid4().hex[:12]}"
        )
        self._payload: dict[str, Any] = {
            "schema": _FRONTIER_ATTEMPT_LEASE_SCHEMA,
            **self.binding,
            "family": "axiompack_frontier",
            "station": "frontier_attempt_lease",
            "action": self.action,
            "epoch": None,
            "context_hash": "",
        }
        self._lock = threading.Lock()
        self._lease = work_queue.QueueLease(
            self.queue_db,
            work_id=self.work_id,
            worker_id=self.worker_id,
            kind=_FRONTIER_ATTEMPT_LEASE_KIND,
            worker_kind="frontier_attempt_lease",
            payload=self._payload,
            max_attempts=_FRONTIER_ATTEMPT_LEASE_MAX_ATTEMPTS,
            lease_s=self.lease_s,
            heartbeat_s=heartbeat_s,
            on_change=self._write_view,
        )

    def __enter__(self) -> "_FrontierAttemptLease":
        try:
            self._lease.__enter__()
        except work_queue.QueueLeaseBusy as exc:
            raise FrontierAttemptLeaseBusy(str(exc)) from exc
        return self

    def __exit__(self, exc_type: Any, _exc: Any, _traceback: Any) -> bool:
        try:
            self._lease.__exit__(exc_type, _exc, _traceback)
        except work_queue.QueueLeaseLost as exc:
            if exc_type is None:
                raise FrontierAttemptLeaseLost(str(exc)) from exc
        return False

    def bind_epoch(self, *, epoch: int, context_hash: str) -> None:
        with self._lock:
            self._payload["epoch"] = int(epoch)
            self._payload["context_hash"] = str(context_hash)
        try:
            self._lease.update(
                {"epoch": self._payload["epoch"], "context_hash": self._payload["context_hash"]}
            )
        except work_queue.QueueLeaseLost as exc:
            raise FrontierAttemptLeaseLost(str(exc)) from exc

    def renew(self) -> None:
        try:
            self._lease.renew()
        except work_queue.QueueLeaseLost as exc:
            raise FrontierAttemptLeaseLost(str(exc)) from exc

    def release(self) -> None:
        try:
            self._lease.release()
        except work_queue.QueueLeaseLost as exc:
            raise FrontierAttemptLeaseLost(str(exc)) from exc

    def _write_view(self) -> None:
        """Project queue state for inspection; the queue remains authoritative."""

        view = {
            **attempt_lease_status(self.directory),
            "derived_at": int(time.time()),
            "view": "queue_heartbeat",
        }
        write_json_atomic(self.directory / "lease.json", view)


def frontier_attempt_lease(
    attempt_dir: str | Path,
    *,
    action: str,
    queue_db: str | None = None,
    worker_id: str | None = None,
    lease_s: int | None = None,
    heartbeat_s: float | None = None,
) -> _FrontierAttemptLease:
    """Acquire host ownership of mutable attempt state until the context exits."""

    return _FrontierAttemptLease(
        attempt_dir,
        action=action,
        queue_db=queue_db,
        worker_id=worker_id,
        lease_s=lease_s,
        heartbeat_s=heartbeat_s,
    )


def attempt_lease_status(attempt_dir: str | Path) -> dict[str, Any]:
    """Read the current ownership state without changing the attempt journal."""

    directory = Path(attempt_dir)
    try:
        binding = _frontier_attempt_binding(directory)
    except ValueError:
        return {
            "schema": _FRONTIER_ATTEMPT_LEASE_SCHEMA,
            "attempt_id": directory.name,
            "active": False,
            "status": "unbound",
        }
    work_id = frontier_attempt_work_id(directory)
    try:
        cx = work_queue.connect(_frontier_attempt_queue_db())
        try:
            row = cx.execute(
                "SELECT status, claimed_by, lease_until, updated_at, payload_json FROM work_items WHERE work_id=?",
                (work_id,),
            ).fetchone()
            heartbeat = (
                cx.execute(
                    "SELECT last_seen_at FROM worker_heartbeats WHERE worker_id=?",
                    (str(row["claimed_by"] or ""),),
                ).fetchone()
                if row is not None and row["claimed_by"]
                else None
            )
        finally:
            cx.close()
    except Exception as exc:
        return {
            "schema": _FRONTIER_ATTEMPT_LEASE_SCHEMA,
            **binding,
            "work_id": work_id,
            "active": False,
            "status": "queue_unavailable",
            "queue_error": str(exc),
        }
    if row is None:
        return {
            "schema": _FRONTIER_ATTEMPT_LEASE_SCHEMA,
            **binding,
            "work_id": work_id,
            "active": False,
            "status": "unseen",
        }
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        payload = {}
    lease_until = int(row["lease_until"] or 0)
    active = bool(
        row["status"] in {"claimed", "running"}
        and lease_until >= int(time.time())
    )
    return {
        "schema": _FRONTIER_ATTEMPT_LEASE_SCHEMA,
        **binding,
        "work_id": work_id,
        "status": str(row["status"]),
        "claimed_by": str(row["claimed_by"] or ""),
        "owner": str(row["claimed_by"] or ""),
        "lease_until": lease_until or None,
        "heartbeat_at": int(heartbeat["last_seen_at"] or 0) if heartbeat else None,
        "queue_updated_at": int(row["updated_at"] or 0),
        "active": active,
        "epoch": payload.get("epoch") if isinstance(payload, Mapping) else None,
        "context_hash": (
            payload.get("context_hash") if isinstance(payload, Mapping) else None
        ),
        "action": payload.get("action") if isinstance(payload, Mapping) else None,
    }


def _bind_active_attempt_epoch(lease: _FrontierAttemptLease, directory: Path) -> None:
    """Attach the current read-model epoch to an already-owned attempt lease."""

    run = read_json(directory / "run.json", {})
    navigation = run.get("navigation") if isinstance(run, Mapping) else None
    summary = run.get("context_summary") if isinstance(run, Mapping) else None
    epoch = int(
        (navigation or {}).get(
            "context_epoch", (summary or {}).get("context_epoch", 0)
        )
    )
    context_hash = str(run.get("context_hash") or "") if isinstance(run, Mapping) else ""
    if not context_hash:
        context_hash = lease.binding["root_context_hash"]
    lease.bind_epoch(epoch=epoch, context_hash=context_hash)


def _record_host_isolated_navigation(
    journal: TheoryCampaignJournal,
    navigation: Mapping[str, Any],
    *,
    attempt_id: str,
    campaign_id: str,
    context_hash: str,
) -> None:
    aggregate = IdempotentReplayJournal(journal)
    epoch = int(navigation.get("context_epoch", 0))
    for finalist in navigation.get("finalists") or ():
        aggregate.append(
            TheoryCampaignEvent(
                attempt_id=attempt_id,
                campaign_id=campaign_id,
                epoch=epoch,
                context_hash=context_hash,
                event_type="finalist_frozen",
                subject_ids=(
                    str(finalist["node_id"]),
                    str(finalist["theory_program_id"]),
                ),
                input_refs=tuple(
                    str(row) for row in finalist.get("formula_ids") or ()
                ),
                output_refs=(str(finalist["selection_receipt_id"]),),
                evidence_status="frozen",
                authority="host_isolated_lineage_aggregation",
            )
        )
    rejection = navigation.get("reject_all_receipt")
    if isinstance(rejection, Mapping):
        aggregate.append(
            TheoryCampaignEvent(
                attempt_id=attempt_id,
                campaign_id=campaign_id,
                epoch=epoch,
                context_hash=context_hash,
                event_type="navigator_reject_all",
                subject_ids=(str(rejection["receipt_id"]),),
                input_refs=tuple(
                    str(row.get("selection_receipt_id") or "")
                    for row in rejection.get("rejected_candidates") or ()
                ),
                output_refs=(str(rejection["receipt_id"]),),
                evidence_status="witnessed",
                authority="host_isolated_lineage_aggregation",
            )
        )


def _make_campaign_theory_navigator(
    definition: FrontierCampaignDefinition,
    *,
    directory: Path,
    repo: Path,
    attempt_id: str,
) -> Any:
    """Bind either one warm trace or explicitly host-isolated lineages."""

    search_wave = max(
        [0]
        + [
            int(match.group(1))
            for path in (directory / "agent_calls").glob("navigator*.wave-*")
            if (match := re.search(r"\.wave-(\d{3})$", path.name)) is not None
        ]
    )

    def wave_instance(base: str = "") -> str:
        suffix = f"wave-{search_wave:03d}" if search_wave else ""
        return ".".join(row for row in (base, suffix) if row)

    def make_single() -> tuple[SubscriptionJSONRole, Any]:
        role = frontier_agent_role(
            definition,
            role_name="navigator",
            repo=repo,
            artifact_dir=directory / "agent_calls",
            instance_id=wave_instance(),
        )
        return role, make_subscription_theory_navigator(
            role,
            attempt_id=attempt_id,
        )

    single_role, single = make_single()
    lineage_roles: dict[int, SubscriptionJSONRole] = {}
    synthesis_role: SubscriptionJSONRole | None = None
    reactivated_consumed = False

    def navigator(
        context: Any,
        blueprint: FrontierTheoryBlueprint,
        journal: TheoryCampaignJournal,
        *,
        budget_ledger: ExplorationBudgetLedger | None = None,
    ) -> Mapping[str, Any]:
        nonlocal synthesis_role, reactivated_consumed
        count = host_isolated_lineage_count(blueprint)
        if count == 1:
            for name in (
                "initial_trace",
                "prior_agent_turns",
                "round_offset",
                "epoch",
                "prior_conflict_rows",
            ):
                if hasattr(navigator, name):
                    setattr(single, name, getattr(navigator, name))
            return single(
                context,
                blueprint,
                journal,
                budget_ledger=budget_ledger,
            )
        if navigator_selection_mode(blueprint) != "theory_program":
            raise ValueError(
                "host-isolated conjectural lineages require theory_program mode"
            )
        total_rounds = int(blueprint.query_budget.get("navigator_rounds", 24))
        total_finalists = min(
            int(blueprint.query_budget.get("max_finalists", 8)),
            (
                budget_ledger.budget.stop_rule.max_finalists
                if budget_ledger is not None
                else 8
            ),
        )
        if total_rounds < count or total_finalists < count:
            raise ValueError(
                "campaign budget must give each host-isolated lineage at least "
                "one navigator turn and one finalist slot"
            )
        epoch = int(getattr(navigator, "epoch", 0))
        epoch_seed = tuple(getattr(navigator, "initial_trace", ()))
        if epoch > 0 and not epoch_seed:
            raise ValueError(
                "successor-context navigation requires its causal epoch receipt"
            )
        reactivated = [
            dict(row["request"])
            for row in epoch_seed
            if row.get("decision") == "deferred_request_reactivated"
            and isinstance(row.get("request"), Mapping)
        ]
        if reactivated and not reactivated_consumed:
            reactivated_consumed = True
            result = {
                "schema": "leanmill.reactivated_lineage_requests.v1",
                "context_hash": context.context_hash,
                "context_epoch": epoch,
                "lineages": [],
                "finalists": [],
                "pending_leaf_decisions": [],
                "expansion_proposals": [
                    row for row in reactivated if not isinstance(row.get("request"), Mapping)
                ],
                "theory_language_expansion_requests": [
                    row for row in reactivated if isinstance(row.get("request"), Mapping)
                ],
                "provider_calls": 0,
                "cold_view": True,
            }
        else:
            roles: list[SubscriptionJSONRole] = []
            for index in range(count):
                role = lineage_roles.get(index)
                if role is None:
                    role = frontier_agent_role(
                        definition,
                        role_name="navigator",
                        repo=repo,
                        artifact_dir=directory / "agent_calls",
                        instance_id=wave_instance(f"lineage-{index:03d}"),
                    )
                    lineage_roles[index] = role
                role.budget_ledger = budget_ledger
                roles.append(role)
            result = run_host_isolated_theory_lineages(
                context,
                blueprint,
                agent_fns=roles,
                journal_root=directory / "lineage_journals",
                attempt_id=attempt_id,
                campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
                max_rounds=max(1, total_rounds // count),
                max_finalists_per_lineage=max(1, total_finalists // count),
                budget_ledger=budget_ledger,
                epoch=epoch,
                prior_conflict_rows=tuple(getattr(navigator, "prior_conflict_rows", ())),
                initial_trace=epoch_seed + (
                    ({
                        "decision": "late_objective_review_requested_continuation",
                        "program_ids": list(getattr(navigator, "objective_feedback", {}).get("program_ids", ())),
                        "next_discriminator": str(getattr(navigator, "objective_feedback", {}).get("next_discriminator", "")),
                        "kill_condition": str(getattr(navigator, "objective_feedback", {}).get("kill_condition", "")),
                        "authority": "late_leaf_choice_host_validated",
                    },)
                    if isinstance(getattr(navigator, "objective_feedback", None), Mapping)
                    else ()
                ),
            )
        result = {**result, "search_wave": search_wave}
        objective_contract = frontier_objective_contract(blueprint)
        if (
            not result.get("pending_leaf_decisions")
            and (
                result.get("expansion_proposals")
                or result.get("theory_language_expansion_requests")
                or objective_contract is not None
            )
        ):
            synthesis_input = lineage_synthesis_input(
                result, objective_contract=objective_contract
            )
            wave_suffix = f".wave-{search_wave:03d}" if search_wave else ""
            synthesis_input_path = directory / (
                "lineage_synthesis_input."
                f"epoch-{int(result.get('context_epoch', 0)):03d}"
                f"{wave_suffix}.json"
            )
            prior_synthesis_input = read_json(synthesis_input_path, None)
            if isinstance(prior_synthesis_input, Mapping):
                if dict(prior_synthesis_input) != synthesis_input:
                    raise ValueError("frozen lineage synthesis input changed identity")
            else:
                write_json_atomic(synthesis_input_path, synthesis_input)
            if synthesis_role is None:
                synthesis_role = frontier_agent_role(
                    definition,
                    role_name="lineage_synthesizer",
                    repo=repo,
                    artifact_dir=directory / "agent_calls",
                    instance_id=wave_instance(),
                )
            synthesis_role.budget_ledger = budget_ledger
            reservation = None
            before_calls = synthesis_role.provider_call_count
            used = 0
            synthesis_phase = (
                "boundary"
                if objective_contract is not None
                and not result.get("expansion_proposals")
                and not result.get("theory_language_expansion_requests")
                else "navigation"
            )
            synthesis_index = len(synthesis_role.calls)
            synthesis_prefix = synthesis_role.artifact_dir / f"{synthesis_index:03d}"
            durable_call = read_json(
                synthesis_prefix.with_suffix(".call.json"), None
            )
            durable_result = synthesis_prefix.with_suffix(".result.json")
            durable_success = bool(
                isinstance(durable_call, Mapping)
                and int(durable_call.get("returncode", 1)) == 0
                and durable_result.is_file()
            )
            synthesis = None
            synthesis_stop = None
            try:
                if budget_ledger is not None and not durable_success:
                    reservation = budget_ledger.reserve(
                        f"lineage-synthesis:{int(result.get('context_epoch', 0))}:"
                        f"wave-{search_wave:03d}",
                        synthesis_phase,
                        {"provider_calls": 1, "agent_turns": 1},
                    )
                decision = synthesis_role(
                    prompts.AXIOMPACK_LINEAGE_SYNTHESIS_PROMPT.format(
                        synthesis_input_json=json.dumps(
                            synthesis_input,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                    )
                )
                synthesis = validate_lineage_synthesis_decision(
                    synthesis_input, decision
                )
            except BudgetExceeded as exc:
                stop_core = {
                    "schema": "leanmill.lineage_synthesis_budget_stop.v1",
                    "context_hash": context.context_hash,
                    "context_epoch": int(result.get("context_epoch", 0)),
                    "reason": exc.reason,
                    "claim_boundary": (
                        "lineage outputs remain receipted; no cross-lineage synthesis "
                        "or formula admission was performed"
                    ),
                    "authority": "host_budget_ledger",
                }
                synthesis_stop = {
                    **stop_core,
                    "receipt_sha256": content_hash(stop_core),
                }
            except (KeyError, TypeError, ValueError, RuntimeError) as exc:
                # A provider/schema/decision failure must remain a typed
                # campaign outcome.  The frozen lineage requests are still
                # usable for recovery; do not discard them by escaping before
                # the run receipt is materialized.
                stop_core = {
                    "schema": "leanmill.lineage_synthesis_failure.v1",
                    "context_hash": context.context_hash,
                    "context_epoch": int(result.get("context_epoch", 0)),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "claim_boundary": (
                        "lineage outputs remain receipted; synthesis did not "
                        "select requests and no formula admission was performed"
                    ),
                    "authority": "deterministic_host",
                }
                synthesis_stop = {
                    **stop_core,
                    "receipt_sha256": content_hash(stop_core),
                }
            finally:
                used = max(
                    0,
                    min(
                        1,
                        synthesis_role.provider_call_count - before_calls,
                    ),
                )
                if reservation is not None:
                    budget_ledger.commit(
                        reservation,
                        {"provider_calls": used, "agent_turns": used},
                    )
            if synthesis is not None:
                write_json_atomic(
                    directory
                    / (
                        "lineage_synthesis."
                        f"epoch-{int(result.get('context_epoch', 0)):03d}"
                        f"{wave_suffix}.json"
                    ),
                    synthesis,
                )
                result = {
                    **result,
                    "lineage_synthesis": synthesis,
                    "provider_calls": int(result.get("provider_calls", 0)) + used,
                }
            else:
                assert synthesis_stop is not None
                stop_stem = (
                    "lineage_synthesis_budget_stop"
                    if synthesis_stop.get("schema")
                    == "leanmill.lineage_synthesis_budget_stop.v1"
                    else "lineage_synthesis_failure"
                )
                write_json_atomic(
                    directory
                    / (
                        f"{stop_stem}.epoch-"
                        f"{int(result.get('context_epoch', 0)):03d}"
                        f"{wave_suffix}.json"
                    ),
                    synthesis_stop,
                )
                result = {
                    **result,
                    (
                        "lineage_synthesis_budget_stop"
                        if stop_stem == "lineage_synthesis_budget_stop"
                        else "lineage_synthesis_failure"
                    ): synthesis_stop,
                }
        campaign_id = "campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24]
        _record_host_isolated_navigation(
            journal,
            result,
            attempt_id=attempt_id,
            campaign_id=campaign_id,
            context_hash=context.context_hash,
        )
        return result

    navigator.call_role = single_role  # type: ignore[attr-defined]
    navigator.accepts_budget_ledger = True  # type: ignore[attr-defined]
    navigator.accepts_theory_conflict_memory = True  # type: ignore[attr-defined]

    def begin_search_wave() -> None:
        """Open fresh agent-call identities without changing the theory epoch."""

        nonlocal search_wave, single_role, single, synthesis_role
        search_wave += 1
        lineage_roles.clear()
        synthesis_role = None
        single_role, single = make_single()
        navigator.search_wave = search_wave  # type: ignore[attr-defined]

    navigator.begin_search_wave = begin_search_wave  # type: ignore[attr-defined]
    navigator.search_wave = search_wave  # type: ignore[attr-defined]

    def begin_context_epoch(*, source_epoch: int, target_epoch: int) -> None:
        nonlocal search_wave, single_role, single, synthesis_role
        if target_epoch != source_epoch + 1:
            raise ValueError("navigator context epochs must advance by one")
        roles = [single_role, *lineage_roles.values()]
        if synthesis_role is not None:
            roles.append(synthesis_role)
        for role in roles:
            source = role.artifact_dir
            if source.exists():
                archive = source.parent / f"{source.name}.epoch-{source_epoch:03d}"
                if archive.exists():
                    raise ValueError("navigator epoch call archive already exists")
                os.replace(source, archive)
            role.calls.clear()
        search_wave += 1
        lineage_roles.clear()
        synthesis_role = None
        single_role, single = make_single()
        navigator.search_wave = search_wave  # type: ignore[attr-defined]
        navigator.epoch = target_epoch  # type: ignore[attr-defined]

    navigator.begin_context_epoch = begin_context_epoch  # type: ignore[attr-defined]
    return navigator


def _load_predecessor_synthesis_input(
    definition: FrontierCampaignDefinition,
    *,
    repo: Path,
) -> dict[str, Any] | None:
    ref = definition.predecessor_synthesis_ref
    if ref is None:
        return None
    path = Path(str(ref["path"]))
    if not path.is_absolute():
        path = repo / path
    row = read_json(path, None)
    if not isinstance(row, Mapping):
        raise ValueError("predecessor synthesis input is missing")
    core = {key: value for key, value in row.items() if key != "input_sha256"}
    if (
        row.get("input_sha256") != content_hash(core)
        or row.get("input_sha256") != ref["input_sha256"]
    ):
        raise ValueError("predecessor synthesis input changed identity")
    if not row.get("formula_requests") and not row.get("theory_language_requests"):
        raise ValueError("predecessor synthesis input has no successor request")
    return dict(row)


def _prepend_predecessor_synthesis(
    navigator: Any,
    *,
    synthesis_input: Mapping[str, Any],
    synthesis_role: SubscriptionJSONRole,
) -> Any:
    consumed = False

    def seeded(
        context: Any,
        blueprint: FrontierTheoryBlueprint,
        journal: TheoryCampaignJournal,
        *,
        budget_ledger: ExplorationBudgetLedger,
    ) -> Mapping[str, Any]:
        nonlocal consumed
        if consumed:
            for name in ("objective_feedback", "epoch", "prior_conflict_rows"):
                if hasattr(seeded, name):
                    setattr(navigator, name, getattr(seeded, name))
            return navigator(
                context, blueprint, journal, budget_ledger=budget_ledger
            )
        if synthesis_input.get("context_hash") != context.context_hash:
            raise ValueError("predecessor synthesis targets another context")
        if int(synthesis_input.get("context_epoch", -1)) != 0:
            raise ValueError("predecessor synthesis must enter at its source epoch")
        synthesis_role.budget_ledger = budget_ledger
        reservation = budget_ledger.reserve(
            "predecessor-synthesis:0",
            "navigation",
            {"provider_calls": 1, "agent_turns": 1},
        )
        before = synthesis_role.provider_call_count
        try:
            decision = synthesis_role(
                prompts.AXIOMPACK_LINEAGE_SYNTHESIS_PROMPT.format(
                    synthesis_input_json=json.dumps(
                        synthesis_input, sort_keys=True, separators=(",", ":")
                    )
                )
            )
            synthesis = validate_lineage_synthesis_decision(
                synthesis_input, decision
            )
        finally:
            used = max(
                0, min(1, synthesis_role.provider_call_count - before)
            )
            budget_ledger.commit(
                reservation, {"provider_calls": used, "agent_turns": used}
            )
        consumed = True
        return {
            "schema": "leanmill.predecessor_synthesis_navigation.v1",
            "context_hash": context.context_hash,
            "context_epoch": 0,
            "finalists": [],
            "finalist_node_ids": [],
            "expansion_proposals": list(
                synthesis_input.get("formula_requests") or ()
            ),
            "theory_language_expansion_requests": list(
                synthesis_input.get("theory_language_requests") or ()
            ),
            "lineage_synthesis": synthesis,
            "provider_calls": used,
            "cold_view": True,
        }

    seeded.accepts_budget_ledger = True  # type: ignore[attr-defined]
    seeded.accepts_theory_conflict_memory = True  # type: ignore[attr-defined]
    seeded.begin_context_epoch = navigator.begin_context_epoch  # type: ignore[attr-defined]
    seeded.begin_search_wave = navigator.begin_search_wave  # type: ignore[attr-defined]
    return seeded


def run_frontier_campaign_definition(
    definition: FrontierCampaignDefinition,
    *,
    output_root: Path,
    typed_draft: Mapping[str, Any] | None = None,
    repo: Path | None = None,
    campaign_manifest: Mapping[str, Any] | None = None,
) -> Path:
    """Compile, freeze, and navigate one definition through the public inlet."""

    attempt_id = "attempt-" + uuid.uuid4().hex
    directory = output_root / attempt_id
    private, public = generate_keypair()
    repo = Path.cwd() if repo is None else Path(repo)
    compiler = frontier_agent_role(
        definition,
        role_name="blueprint_compiler",
        repo=repo,
        artifact_dir=directory / "agent_calls",
    )
    reviewer = frontier_agent_role(
        definition,
        role_name="semantic_reviewer",
        repo=repo,
        artifact_dir=directory / "agent_calls",
    )
    draft_fn, review_fn = make_subscription_frontier_compiler_roles(
        compiler=compiler,
        reviewer=reviewer,
    )
    navigator = _make_campaign_theory_navigator(
        definition,
        directory=directory,
        repo=repo,
        attempt_id=attempt_id,
    )
    predecessor_input = _load_predecessor_synthesis_input(
        definition, repo=repo
    )
    if predecessor_input is not None:
        predecessor_role = frontier_agent_role(
            definition,
            role_name="lineage_synthesizer",
            repo=repo,
            artifact_dir=directory / "agent_calls",
            instance_id="predecessor",
        )
        navigator = _prepend_predecessor_synthesis(
            navigator,
            synthesis_input=predecessor_input,
            synthesis_role=predecessor_role,
        )
    try:
        explore_axiom_space(
            definition,
            attempt_dir=directory,
            typed_draft=typed_draft,
            draft_fn=None if typed_draft is not None else draft_fn,
            semantic_review_fn=None if typed_draft is not None else review_fn,
            compiler_ref=compiler.agent_id,
            reviewer_ref=reviewer.agent_id,
            packet_signer=lambda packet: sign_frontier_campaign(
                packet,
                private_key_pem=private,
                signer_ref="axiompack-campaign-authority",
            ),
            navigator_fn=navigator,
            campaign_manifest=campaign_manifest,
        )
    finally:
        budget_row = read_json(directory / "budget.json", None)
        if isinstance(budget_row, dict):
            ExplorationBudgetLedger(
                directory / "budget.events.jsonl",
                ExplorationBudget.from_json(budget_row),
                attempt_id=attempt_id,
            ).freeze_wall_clock(reason="campaign_runner_exit")
        signer_path = directory / "private" / "campaign_signer.pem"
        if directory.is_dir() and not signer_path.exists():
            _write_secret(signer_path, private)
        public_path = directory / "campaign_signer_public.pem"
        if directory.is_dir() and not public_path.exists():
            write_text_atomic(public_path, public)
    return directory


def execute_frontier_adapter_forge(
    attempt_dir: str | Path,
    *,
    model: str = "",
    reasoning_effort: str = "",
    repo: str | Path | None = None,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> dict[str, Any]:
    """Run a typed adapter/capability gap in a quarantined subscription workspace."""

    directory = Path(attempt_dir)
    if _attempt_lease is None:
        with frontier_attempt_lease(directory, action="adapter_forge") as lease:
            return execute_frontier_adapter_forge(
                directory,
                model=model,
                reasoning_effort=reasoning_effort,
                repo=repo,
                _attempt_lease=lease,
            )
    from ztare.leanmill.adapter_forge import (
        AdapterGap,
        adapter_forge_output_schema,
        adapter_review_output_schema,
        execute_adapter_forge_attempt,
        host_coordinate_conformance,
        stage_adapter_forge_workspace,
    )

    definition = load_frontier_campaign_definition(directory / "campaign_definition.yaml")
    gap = AdapterGap.from_json(read_json(directory / "adapter_gap.json", {}))
    workspace = stage_adapter_forge_workspace(directory, gap)
    source_repo = Path.cwd() if repo is None else Path(repo)
    prior_indices = [
        int(path.name.rsplit("-", 1)[1])
        for role in ("adapter_forge", "adapter_reviewer")
        for path in (directory / "agent_calls").glob(f"{role}.attempt-*")
        if path.name.rsplit("-", 1)[1].isdigit()
    ]
    forge_index = 1 + max(prior_indices, default=0)
    instance_id = f"attempt-{forge_index:03d}"
    coding = frontier_agent_role(
        definition,
        role_name="adapter_forge",
        repo=workspace,
        artifact_dir=directory / "agent_calls",
        instance_id=instance_id,
    )
    review = frontier_agent_role(
        definition,
        role_name="adapter_reviewer",
        repo=workspace,
        artifact_dir=directory / "agent_calls",
        instance_id=instance_id,
    )
    for role, schema, visible in (
        (coding, adapter_forge_output_schema(), True),
        (review, adapter_review_output_schema(), False),
    ):
        role.repo = workspace
        role.output_schema = schema
        role.config = replace(
            role.config,
            model=model or role.config.model,
            reasoning_effort=reasoning_effort or role.config.reasoning_effort,
            visible_workbench=visible,
            web_research=False,
        )
    if (
        sys.platform.startswith("linux")
        and coding.config.runtime == "codex"
        and os.environ.get("ZTARE_CODEX_NESTED_SANDBOX") != "0"
    ):
        raise ValueError(
            "Linux AdapterForge requires the VPS launcher execution boundary"
        )
    registry_path = source_repo / "src/ztare/leanmill/theory_adapter_registry.py"
    registry_digest = content_hash({"bytes": registry_path.read_text(encoding="utf-8")})

    recovered_proposal = None
    for result_path in sorted(
        (directory / "agent_calls").glob("adapter_forge*/000.result.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    ):
        call = read_json(result_path.with_name("000.call.json"), {})
        proposal = read_json(result_path, {})
        if int(call.get("returncode", 1)) != 0 or not isinstance(proposal, Mapping):
            continue
        paths = list(proposal.get("source_paths") or ()) + list(proposal.get("test_paths") or ())
        if paths and all((workspace / str(path)).is_file() for path in paths):
            recovered_proposal = dict(proposal)
            break

    def recovered_coding(_prompt: str) -> Mapping[str, Any]:
        assert recovered_proposal is not None
        return recovered_proposal

    recovered_coding.provider_call_count = 0  # type: ignore[attr-defined]
    recovered_coding.recovered_proposal = True  # type: ignore[attr-defined]

    def conformance(proposal: Mapping[str, Any], typed_gap: AdapterGap) -> Mapping[str, Any]:
        if content_hash({"bytes": registry_path.read_text(encoding="utf-8")}) != registry_digest:
            raise ValueError("AdapterForge changed the live adapter registry")
        if typed_gap.gap_kind != "capability_missing":
            raise ValueError("full adapter conformance is not executable in this campaign")
        return host_coordinate_conformance(
            proposal,
            typed_gap,
            workspace=workspace,
            output_path=directory / "theory_language_coordinates.json",
        )

    return execute_adapter_forge_attempt(
        directory,
        coding_agent_fn=recovered_coding if recovered_proposal is not None else coding,
        host_conformance_fn=conformance,
        independent_review_fn=make_subscription_adapter_reviewer(review),
    )


def resume_frontier_campaign_navigation(
    attempt_dir: str | Path,
    *,
    repo: Path | None = None,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> Path:
    """Continue an interrupted navigator from immutable durable role calls."""

    directory = Path(attempt_dir)
    existing = read_json(directory / "run.json", None)
    if isinstance(existing, dict) and existing.get("status") in {
        "frontier_candidates_frozen_awaiting_boundary_approval",
        "frontier_no_candidate",
        "frontier_navigation_exhausted",
        "frontier_language_expansion_requested",
        "budget_stopped",
    }:
        return directory
    if (directory / "retirement.json").is_file():
        raise ValueError("retired frontier campaign cannot resume")
    if _attempt_lease is None:
        with frontier_attempt_lease(
            directory, action="resume_frontier_navigation"
        ) as lease:
            return resume_frontier_campaign_navigation(
                directory,
                repo=repo,
                _attempt_lease=lease,
            )

    definition, blueprint, budget_row, campaign_row, context = (
        _load_campaign_attempt(directory)
    )

    budget = ExplorationBudget.from_json(budget_row)
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    ledger.recover_interrupted_wall_clock()
    ledger.resume_wall_clock()
    campaign_id = str(campaign_row["packet"]["campaign_id"])
    events = TheoryCampaignJournal(directory / "events.jsonl").replay()
    context_epoch = max((event.epoch for event in events), default=0)
    formula_hashes = [
        TypedAxiomProposal.from_json(read_json(path, {})).content_hash
        for path in sorted(directory.glob("typed_formula_proposal.epoch-*.json"))
    ]
    semantic_count = _semantic_profile_admission_count(directory)
    repo = Path.cwd() if repo is None else Path(repo)
    pending_navigation: Mapping[str, Any] | None = None
    checkpoint = read_json(directory / "navigation_epoch_checkpoint.json", None)

    if host_isolated_lineage_count(blueprint) > 1:
        navigator = _make_campaign_theory_navigator(
            definition,
            directory=directory,
            repo=repo,
            attempt_id=directory.name,
        )
        navigator.epoch = context_epoch  # type: ignore[attr-defined]
        if isinstance(checkpoint, Mapping):
            if checkpoint.get("context_hash") != context.context_hash:
                raise ValueError("navigation epoch checkpoint targets a stale context")
            navigator.initial_trace = tuple(  # type: ignore[attr-defined]
                dict(row)
                for row in checkpoint.get("trace") or ()
                if isinstance(row, Mapping)
            )
        if isinstance(existing, Mapping) and existing.get("status") in {
            "frontier_leaf_decision_pending",
            "frontier_objective_unmet",
        }:
            seed = list(getattr(navigator, "initial_trace", ()))
            prior_navigation = existing.get("navigation") or {}
            if existing.get("status") == "frontier_leaf_decision_pending":
                for lineage in prior_navigation.get("lineages") or ():
                    trace = (lineage.get("navigation") or {}).get("trace") or ()
                    request = next(
                        (
                            dict(row)
                            for row in reversed(trace)
                            if isinstance(row, Mapping)
                            and row.get("decision") == "request"
                        ),
                        None,
                    )
                    if request is not None:
                        seed.append(request)
            else:
                history = prior_navigation.get("objective_review_history") or ()
                if history and isinstance(history[-1], Mapping):
                    seed.append(dict(history[-1]))
                deferred_ids = {
                    str(request_id)
                    for path in directory.glob("lineage_synthesis.epoch-*.json")
                    for request_id in (
                        read_json(path, {}).get("deferred_request_ids") or ()
                    )
                }
                for path in directory.glob(
                    "isolated_lineage_language_requests.epoch-*.json"
                ):
                    requests = read_json(path, {})
                    for row in (
                        list(requests.get("formula_requests") or ())
                        + list(requests.get("theory_language_requests") or ())
                    ):
                        if str(row.get("request_id") or "") in deferred_ids:
                            seed.append(
                                {
                                    "decision": "deferred_request_reactivated",
                                    "request": dict(row),
                                    "authority": "host_receipt_replay",
                                }
                            )
            navigator.initial_trace = tuple(seed)  # type: ignore[attr-defined]
            navigator.begin_search_wave()  # type: ignore[attr-defined]

    else:
        role = frontier_agent_role(
            definition,
            role_name="navigator",
            repo=repo,
            artifact_dir=directory / "agent_calls",
        )
        if isinstance(checkpoint, Mapping):
            if checkpoint.get("context_hash") != context.context_hash:
                raise ValueError(
                    "navigation epoch checkpoint targets a stale context"
                )
            context_epoch = int(checkpoint.get("context_epoch", 0))
            checkpoint_calls = int(checkpoint.get("provider_calls", 0))
            checkpoint_trace = tuple(
                dict(row)
                for row in checkpoint.get("trace") or ()
                if isinstance(row, Mapping)
            )
            formula_hashes = [
                str(row)
                for row in checkpoint.get(
                    "typed_formula_proposal_sha256s"
                )
                or ()
            ]
        else:
            checkpoint_calls = 0
            checkpoint_trace = ()

        prior_calls, durable_decisions = _read_durable_navigator_decisions(
            directory / "agent_calls" / "navigator"
        )
        replay_decisions = durable_decisions[checkpoint_calls:]
        role.calls.extend(prior_calls)
        navigator = make_subscription_theory_navigator(
            role, attempt_id=directory.name
        )
        navigator.initial_trace = checkpoint_trace  # type: ignore[attr-defined]
        navigator.prior_agent_turns = checkpoint_calls  # type: ignore[attr-defined]
        navigator.round_offset = checkpoint_calls  # type: ignore[attr-defined]
        navigator.replay_decisions = tuple(  # type: ignore[attr-defined]
            replay_decisions
        )
        navigator.epoch = context_epoch  # type: ignore[attr-defined]

    _attempt_lease.bind_epoch(
        epoch=context_epoch,
        context_hash=context.context_hash,
    )

    signer_path = directory / "private" / "campaign_signer.pem"
    if not signer_path.is_file():
        raise ValueError("navigation resume cannot locate campaign signer")
    private_key = signer_path.read_text(encoding="utf-8")
    signer_ref = str(
        campaign_row.get("signer_ref") or "axiompack-campaign-authority"
    )

    def packet_signer(packet):
        return sign_frontier_campaign(
            packet,
            private_key_pem=private_key,
            signer_ref=signer_ref,
        )

    packet = packet_for_frontier_context(
        blueprint,
        context,
        campaign_id=campaign_id,
        formula_proposal_hashes=formula_hashes,
        context_epoch=context_epoch,
    )
    if packet.digest != campaign_row.get("packet_digest"):
        raise ValueError("active campaign packet does not replay")
    try:
        try:
            driven = drive_frontier_navigation(
                context,
                blueprint,
                directory=directory,
                campaign_id=campaign_id,
                attempt_id=directory.name,
                journal=TheoryCampaignJournal(directory / "events.jsonl"),
                budget_ledger=ledger,
                navigator_fn=navigator,
                packet_signer=packet_signer,
                packet=packet,
                context_epoch=context_epoch,
                formula_proposal_hashes=formula_hashes,
                semantically_new_formula_count=semantic_count,
                pending_navigation=pending_navigation,
            )
        except BudgetExceeded as exc:
            recoverable = {
                event.event_type
                for event in TheoryCampaignJournal(
                    directory / "events.jsonl"
                ).replay()
                if event.epoch == context_epoch
                and event.context_hash == context.context_hash
            }
            reason = (
                None
                if recoverable.intersection(
                    {
                        "finalist_frozen",
                        "theory_presentation_rejected",
                        "theory_program_refused",
                        "navigator_reject_all",
                    }
                )
                else exc.reason
            )
            return materialize_frontier_navigation_from_journal(
                directory,
                budget_stop_reason=reason,
                _attempt_lease=_attempt_lease,
            )

        usage = ledger.state()["usage"]
        adapter_preflight = dict(
            blueprint.executable_preflight_receipt.get("adapter_preflight")
            or {}
        )
        finish_frontier_navigation(
            directory,
            brief_id=definition.to_brief().brief_id,
            blueprint=blueprint,
            context=driven.context,
            context_epoch=driven.context_epoch,
            campaign_id=campaign_id,
            packet_digest=driven.packet.digest,
            navigation=driven.navigation,
            provider_calls=int(usage["provider_calls"]),
            preparation_provider_calls=0,
            budget_digest=budget.digest,
            formula_proposal_count=len(driven.formula_proposal_hashes),
            semantically_new_formula_count=(
                driven.semantically_new_formula_count
            ),
            labeled_object_count=int(
                adapter_preflight.get("labeled_model_count", 0)
            ),
        )
    finally:
        ledger.freeze_wall_clock(reason="navigation_resume_exit")
    return directory

def continue_frontier_campaign_epoch(
    attempt_dir: str | Path,
    *,
    repo: Path | None = None,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> Path:
    """Consume one frozen successor request without carrying source finalists."""

    directory = Path(attempt_dir)
    if (directory / "retirement.json").is_file():
        raise ValueError("retired frontier campaign cannot continue its epoch")
    if _attempt_lease is None:
        with frontier_attempt_lease(
            directory, action="continue_frontier_epoch"
        ) as lease:
            return continue_frontier_campaign_epoch(
                directory,
                repo=repo,
                _attempt_lease=lease,
            )
    run_row = read_json(directory / "run.json", None)
    if not isinstance(run_row, Mapping):
        if tuple(directory.glob("frontier_formula_successor_consumption.epoch-*.json")):
            return resume_frontier_campaign_navigation(
                directory,
                repo=repo,
                _attempt_lease=_attempt_lease,
            )
        raise ValueError("continue-epoch requires a frozen source-epoch run")
    run_core = {key: value for key, value in run_row.items() if key != "run_digest"}
    if run_row.get("run_digest") != content_hash(run_core):
        raise ValueError("source-epoch run receipt does not replay")
    navigation = run_row.get("navigation")
    if not isinstance(navigation, Mapping) or not navigation.get("finalists"):
        raise ValueError("continue-epoch requires a source-epoch finalist")
    transition = navigation.get("epoch_transition")
    if not isinstance(transition, Mapping) or transition.get("status") != "successor_epoch_required":
        raise ValueError("continue-epoch requires a frozen successor request")
    if (directory / "boundary_completion.json").is_file():
        raise ValueError("archive or finish the source boundary before continuing its epoch")
    request_ref = str(transition.get("request_ref") or "")
    if not request_ref or Path(request_ref).name != request_ref:
        raise ValueError("successor request reference is unsafe")
    request = read_json(directory / request_ref, None)
    if not isinstance(request, Mapping):
        raise ValueError("successor request artifact is missing")
    request_core = {key: value for key, value in request.items() if key != "receipt_sha256"}
    if request.get("receipt_sha256") != content_hash(request_core):
        raise ValueError("successor request receipt does not replay")
    if request.get("receipt_sha256") != transition.get("receipt_sha256"):
        raise ValueError("run transition does not bind the successor request")
    source_epoch = int(request.get("source_epoch", -1))
    target_epoch = int(request.get("target_epoch", -1))
    source_context_hash = str(request.get("source_context_hash") or "")
    if source_epoch < 0 or target_epoch != source_epoch + 1:
        raise ValueError("successor request has an invalid epoch transition")
    if (
        source_context_hash != run_row.get("context_hash")
        or int(navigation.get("context_epoch", -1)) != source_epoch
    ):
        raise ValueError("successor request does not own the source run identity")
    finalist_ids = [str(row.get("node_id") or "") for row in navigation["finalists"]]
    if finalist_ids != list(request.get("source_finalist_node_ids") or ()):
        raise ValueError("successor request does not bind the source finalists")
    expansion = request.get("expansion_proposal")
    if not isinstance(expansion, Mapping):
        raise ValueError("successor request lacks its typed formula proposal")

    definition = load_frontier_campaign_definition(
        directory / "campaign_definition.yaml"
    )
    blueprint = FrontierTheoryBlueprint.from_json(
        read_json(directory / "blueprint.json", {})
    )
    budget = ExplorationBudget.from_json(read_json(directory / "budget.json", {}))
    source_context_path = directory / f"formal_context.epoch-{source_epoch:03d}.json"
    if not source_context_path.is_file():
        raise ValueError("successor transition requires a formal source context snapshot")
    from ztare.leanmill.finite_theory_context import load_formal_theory_context

    source_context = load_formal_theory_context(source_context_path)
    if source_context.context_hash != source_context_hash:
        raise ValueError("successor source context snapshot changed identity")
    _attempt_lease.bind_epoch(
        epoch=source_epoch,
        context_hash=source_context.context_hash,
    )
    source_campaign = read_json(
        directory / f"campaign.epoch-{source_epoch:03d}.json",
        read_json(directory / "campaign.json", {}),
    )
    if not isinstance(source_campaign, Mapping):
        raise ValueError("successor transition lacks its signed source campaign")
    validate_campaign_artifact_binding(
        source_campaign,
        blueprint_id=blueprint.blueprint_id,
        context_hash=source_context_hash,
    )
    campaign_id = str((source_campaign.get("packet") or {}).get("campaign_id") or "")
    if not campaign_id:
        raise ValueError("signed source campaign lacks campaign identity")

    source_archive = directory / f"run.epoch-{source_epoch:03d}.json"
    archived = read_json(source_archive, None)
    if isinstance(archived, Mapping):
        if archived.get("run_digest") != run_row.get("run_digest"):
            raise ValueError("source-epoch archive conflicts with active run")
    else:
        write_json_atomic(source_archive, dict(run_row))

    admission_path = directory / f"frontier_formula_epoch_admission.epoch-{target_epoch:03d}.json"
    admission = read_json(admission_path, None)
    if isinstance(admission, Mapping):
        admission_core = {
            key: value for key, value in admission.items() if key != "receipt_sha256"
        }
        if (
            admission.get("receipt_sha256") != content_hash(admission_core)
            or admission.get("source_context_hash") != source_context_hash
            or int(admission.get("target_epoch", -1)) != target_epoch
        ):
            raise ValueError("existing successor admission does not replay")
        target_context = load_formal_theory_context(
            directory / f"formal_context.epoch-{target_epoch:03d}.json"
        )
    else:
        ledger = ExplorationBudgetLedger(
            directory / "budget.events.jsonl",
            budget,
            attempt_id=directory.name,
        )
        ledger.recover_interrupted_wall_clock()
        ledger.resume_wall_clock()
        try:
            target_context, _proposal, admitted_epoch, admission = admit_frontier_formula_epoch(
                source_context,
                expansion,
                journal=TheoryCampaignJournal(directory / "events.jsonl"),
                budget_ledger=ledger,
                directory=directory,
                campaign_id=campaign_id,
                attempt_id=directory.name,
                current_epoch=source_epoch,
            )
            if admitted_epoch != target_epoch:
                raise ValueError("successor admission minted the wrong epoch")
        finally:
            ledger.freeze_wall_clock(reason="successor_epoch_admission_exit")

    formula_proposal_hashes = [
        TypedAxiomProposal.from_json(read_json(path, {})).content_hash
        for path in sorted(directory.glob("typed_formula_proposal.epoch-*.json"))
    ]
    packet = packet_for_frontier_context(
        blueprint,
        target_context,
        campaign_id=campaign_id,
        formula_proposal_hashes=formula_proposal_hashes,
        context_epoch=target_epoch,
    )
    signer_path = directory / "private" / "campaign_signer.pem"
    if not signer_path.is_file():
        raise ValueError("successor transition cannot locate the campaign signer")
    signed = sign_frontier_campaign(
        packet,
        private_key_pem=signer_path.read_text(encoding="utf-8"),
        signer_ref=str(source_campaign.get("signer_ref") or "axiompack-campaign-authority"),
    ).to_json()
    write_json_atomic(directory / f"campaign.epoch-{target_epoch:03d}.json", signed)
    write_json_atomic(directory / "campaign.json", signed)
    _attempt_lease.bind_epoch(
        epoch=target_epoch,
        context_hash=target_context.context_hash,
    )

    checkpoint = {
        "schema": "leanmill.frontier_navigation_epoch_checkpoint.v1",
        "context_hash": target_context.context_hash,
        "context_epoch": target_epoch,
        "trace": [
            {
                "decision": "successor_epoch_admitted",
                "source_request_receipt": request["receipt_sha256"],
                "admission": dict(admission),
            }
        ],
        "provider_calls": 0,
        "typed_formula_proposal_sha256s": formula_proposal_hashes,
    }
    write_json_atomic(directory / "navigation_epoch_checkpoint.json", checkpoint)

    current_calls = directory / "agent_calls" / "navigator"
    archived_calls = directory / "agent_calls" / f"navigator.epoch-{source_epoch:03d}"
    if current_calls.exists():
        if archived_calls.exists():
            raise ValueError("source navigator call archive already exists")
        os.replace(current_calls, archived_calls)
    current_replay = read_json(directory / "replay.json", None)
    if isinstance(current_replay, Mapping):
        archived_replay = directory / f"replay.epoch-{source_epoch:03d}.json"
        if archived_replay.exists():
            prior = read_json(archived_replay, {})
            if prior.get("receipt_sha256") != current_replay.get("receipt_sha256"):
                raise ValueError("source replay archive already exists with another identity")
        else:
            write_json_atomic(archived_replay, dict(current_replay))
        (directory / "replay.json").unlink(missing_ok=True)

    consumption_core = {
        "schema": "leanmill.frontier_formula_successor_consumption.v1",
        "source_attempt": directory.name,
        "source_epoch": source_epoch,
        "target_epoch": target_epoch,
        "source_context_hash": source_context_hash,
        "target_context_hash": target_context.context_hash,
        "source_run_ref": source_archive.name,
        "successor_request_ref": request_ref,
        "successor_request_receipt": request["receipt_sha256"],
        "admission_receipt": admission["receipt_sha256"],
        "source_finalist_disposition": "archived_source_epoch_only",
        "status": "successor_epoch_admitted",
    }
    write_json_atomic(
        directory / f"frontier_formula_successor_consumption.epoch-{target_epoch:03d}.json",
        {**consumption_core, "receipt_sha256": content_hash(consumption_core)},
    )
    (directory / "run.json").unlink(missing_ok=True)
    return resume_frontier_campaign_navigation(
        directory,
        repo=repo,
        _attempt_lease=_attempt_lease,
    )


def materialize_frontier_navigation_from_journal(
    attempt_dir: str | Path,
    *,
    budget_stop_reason: str | None = None,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> Path:
    """Project durable decisions by replaying the canonical navigator."""

    directory = Path(attempt_dir)
    if (directory / "retirement.json").is_file():
        raise ValueError("retired frontier campaign cannot be recovered")
    if _attempt_lease is None:
        with frontier_attempt_lease(
            directory, action="materialize_frontier_navigation"
        ) as lease:
            return materialize_frontier_navigation_from_journal(
                directory,
                budget_stop_reason=budget_stop_reason,
                _attempt_lease=lease,
            )
    definition, blueprint, budget_row, campaign_row, context = (
        _load_campaign_attempt(directory)
    )

    root_journal = TheoryCampaignJournal(directory / "events.jsonl")
    all_events = list(root_journal.replay())
    for path in sorted(
        (directory / "lineage_journals").glob("*.events.jsonl")
    ):
        all_events.extend(TheoryCampaignJournal(path).replay())
    epoch = max((event.epoch for event in all_events), default=0)
    _attempt_lease.bind_epoch(epoch=epoch, context_hash=context.context_hash)
    campaign_id = str(campaign_row["packet"]["campaign_id"])
    _conflicts, prior_conflicts = _freeze_theory_conflict_memory(
        context, directory, epoch=epoch
    )
    lineage_count = host_isolated_lineage_count(blueprint)
    configured_finalists = int(
        blueprint.query_budget.get("max_finalists", 8)
    )

    if lineage_count == 1:
        calls, decisions = _read_durable_navigator_decisions(
            directory / "agent_calls" / "navigator"
        )
        navigation = (
            _replay_navigator_decisions(
                context,
                blueprint,
                decisions,
                IdempotentReplayJournal(root_journal),
                attempt_id=directory.name,
                campaign_id=campaign_id,
                epoch=epoch,
                max_finalists=configured_finalists,
                prior_conflict_rows=prior_conflicts,
            )
            if decisions
            else None
        )
    else:
        calls = []
        rows: list[dict[str, Any]] = []
        per_lineage_finalists = max(
            1, configured_finalists // lineage_count
        )
        for branch in range(lineage_count):
            call_dir = (
                directory
                / "agent_calls"
                / f"navigator.lineage-{branch:03d}"
            )
            branch_calls, decisions = _read_durable_navigator_decisions(
                call_dir
            )
            calls.extend(branch_calls)
            if not decisions:
                continue
            lineage_id = derive_context_lineage_id(
                campaign_id=campaign_id,
                attempt_id=directory.name,
                context_epoch=epoch,
                branch=branch,
            )
            branch_navigation = _replay_navigator_decisions(
                context,
                blueprint,
                decisions,
                IdempotentReplayJournal(
                    directory
                    / "lineage_journals"
                    / f"lineage-{branch:03d}.events.jsonl"
                ),
                attempt_id=f"{directory.name}:lineage:{branch}",
                campaign_id=campaign_id,
                epoch=epoch,
                lineage_id=lineage_id,
                max_finalists=per_lineage_finalists,
                prior_conflict_rows=prior_conflicts,
            )
            rows.append(
                {
                    "lineage_id": lineage_id,
                    "agent_identity": f"durable:{call_dir.name}",
                    "navigation": branch_navigation,
                }
            )
        navigation = (
            aggregate_host_isolated_theory_lineages(
                context, rows, epoch=epoch
            )
            if rows
            else None
        )
        if navigation is not None:
            _record_host_isolated_navigation(
                root_journal,
                navigation,
                attempt_id=directory.name,
                campaign_id=campaign_id,
                context_hash=context.context_hash,
            )

    if navigation is None:
        if budget_stop_reason is None:
            raise ValueError(
                "navigation has no durable decision and no budget stop"
            )
        navigation = {
            "schema": "leanmill.interactive_theory_navigator.v1",
            "context_hash": context.context_hash,
            "context_epoch": epoch,
            "finalist_node_ids": [],
            "finalists": [],
            "trace": [],
            "provider_calls": 0,
            "cold_view": True,
        }
    navigation = dict(navigation)
    if "result_sha256" in navigation:
        navigation.pop("result_sha256")
        navigation["recovered_from_durable_results"] = True
        navigation["result_sha256"] = content_hash(navigation)
    else:
        navigation["recovered_from_durable_results"] = True

    has_request = bool(
        isinstance(navigation.get("language_expansion_request"), Mapping)
        or navigation.get("expansion_proposals")
        or navigation.get("theory_language_expansion_requests")
    )
    terminal = bool(
        navigation.get("finalists")
        or isinstance(navigation.get("reject_all_receipt"), Mapping)
        or has_request
    )
    budget = ExplorationBudget.from_json(budget_row)
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    usage = ledger.state()["usage"]
    adapter_preflight = dict(
        blueprint.executable_preflight_receipt.get("adapter_preflight") or {}
    )
    stop = None
    if budget_stop_reason is not None and not terminal:
        navigation["trace"] = list(navigation.get("trace") or ()) + [
            {
                "decision": "budget_stop",
                "reason": budget_stop_reason,
                "recovered_from_durable_results": True,
            }
        ]
        stop = ledger.stop_receipt(
            budget_stop_reason,
            context_hash=context.context_hash,
        ).to_json()
        write_json_atomic(directory / "budget_stop_receipt.json", stop)

    finish_frontier_navigation(
        directory,
        brief_id=definition.to_brief().brief_id,
        blueprint=blueprint,
        context=context,
        context_epoch=epoch,
        campaign_id=campaign_id,
        packet_digest=str(campaign_row.get("packet_digest") or ""),
        navigation=navigation,
        provider_calls=int(usage["provider_calls"]),
        preparation_provider_calls=0,
        budget_digest=budget.digest,
        formula_proposal_count=len(
            tuple(directory.glob("typed_formula_proposal.epoch-*.json"))
        ),
        semantically_new_formula_count=(
            _semantic_profile_admission_count(directory)
        ),
        labeled_object_count=int(
            adapter_preflight.get("labeled_model_count", 0)
        ),
        budget_stop_receipt=stop,
    )
    return directory

def execute_frontier_campaign_verification(
    attempt_dir: str | Path,
    *,
    with_lean: bool = False,
    with_isabelle: bool = False,
    lean_root: str | Path | None = None,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> dict[str, Any]:
    """Run approved boundary checks; formal peers remain explicit opt-ins."""

    directory = Path(attempt_dir)
    if (directory / "retirement.json").is_file():
        raise ValueError("retired frontier campaign cannot run boundary verification")
    if _attempt_lease is None:
        with frontier_attempt_lease(
            directory, action="frontier_boundary_verification"
        ) as lease:
            return execute_frontier_campaign_verification(
                directory,
                with_lean=with_lean,
                with_isabelle=with_isabelle,
                lean_root=lean_root,
                _attempt_lease=lease,
            )
    _bind_active_attempt_epoch(_attempt_lease, directory)
    lean_executor = None
    isabelle_executor = None
    if with_isabelle:
        from ztare.leanmill.solver.sledgehammer import (
            execute_isabelle_theory_task,
        )

        def isabelle_executor(task, *, timeout_s):
            return execute_isabelle_theory_task(
                task,
                timeout_s=int(timeout_s),
            ).to_json()

    if with_lean:
        if lean_root is None:
            raise ValueError("Lean boundary verification requires a Lean project root")
        root = Path(lean_root)
        from ztare.leanmill.frontier_campaign_definition import (
            load_frontier_campaign_definition,
        )

        definition = load_frontier_campaign_definition(
            directory / "campaign_definition.yaml"
        )
        config = frontier_agent_role(
            definition,
            role_name="lean_solver",
            repo=Path.cwd(),
            artifact_dir=directory / "agent_calls",
        ).config
        timeout_s = min(definition.budget.wall_clock_s, config.timeout_seconds)

        def compile_fn(source: str):
            from ztare.gates.v33_preflight_risk_detector import _compile_probe

            return _compile_probe(
                source,
                root,
                "AxiomPackBoundaryAttribution",
                timeout_s,
            )

        def lean_executor(task, *, budget_ledger):
            def before_dispatch(runtime, _command):
                return budget_ledger.reserve(
                    f"boundary:{task.task_id}:{runtime}",
                    "boundary",
                    {"provider_calls": 1, "agent_turns": 1},
                )

            def after_dispatch(reservation):
                budget_ledger.commit(reservation)

            with scoped_frontier_agent_environment(
                config
            ), subscription_dispatch_budget_scope(
                before_dispatch=before_dispatch,
                after_dispatch=after_dispatch,
            ):
                return execute_governed_lean_consequence(
                    task,
                    substrate=root,
                    timeout_s=timeout_s,
                    compile_fn=compile_fn,
                ).to_json()

    budget_row = read_json(directory / "budget.json", None)
    ledger = None
    if isinstance(budget_row, dict):
        ledger = ExplorationBudgetLedger(
            directory / "budget.events.jsonl",
            ExplorationBudget.from_json(budget_row),
            attempt_id=directory.name,
        )
        ledger.recover_interrupted_wall_clock()
        ledger.resume_wall_clock()
    try:
        return execute_frontier_boundaries(
            directory,
            lean_executor_fn=lean_executor,
            isabelle_executor_fn=isabelle_executor,
        )
    finally:
        if ledger is not None:
            ledger.freeze_wall_clock(reason="boundary_runner_exit")


def recheck_frontier_boundary_governance(
    attempt_dir: str | Path,
    *,
    lean_root: str | Path,
    timeout_s: int = 180,
) -> dict[str, Any]:
    """Re-govern saved Lean proof bytes without dispatching another agent."""

    directory = Path(attempt_dir)
    output_path = directory / "boundary_governance_recheck.json"
    boundary = read_json(directory / "boundary_result.json", None)
    if not isinstance(boundary, dict) or not boundary:
        raise ValueError("governance recheck requires a completed boundary result")
    boundary_core = {
        key: value for key, value in boundary.items() if key != "result_sha256"
    }
    boundary_digest = content_hash(boundary_core)
    if boundary.get("result_sha256") != boundary_digest:
        raise ValueError("boundary result digest mismatch")

    existing = read_json(output_path, None)
    if isinstance(existing, dict) and existing:
        existing_core = {
            key: value for key, value in existing.items() if key != "receipt_sha256"
        }
        if existing.get("receipt_sha256") != content_hash(existing_core):
            raise ValueError("governance recheck receipt digest mismatch")
        if existing.get("boundary_result_sha256") != boundary_digest:
            raise ValueError("saved governance recheck belongs to another boundary result")
        return existing

    context_path = directory / "formal_context.json"
    if not context_path.is_file():
        raise ValueError("Lean governance recheck requires a formal theory context")
    from ztare.leanmill.finite_theory_context import load_formal_theory_context

    context = load_formal_theory_context(context_path)
    if context.context_hash != boundary.get("context_hash"):
        raise ValueError("boundary result context differs from the frozen context")
    axiom_map = {row.formula_id: row.axiom for row in context.formula_profiles}
    root = Path(lean_root)
    if not root.is_dir():
        raise ValueError("Lean project root does not exist")
    if timeout_s <= 0:
        raise ValueError("Lean recheck timeout must be positive")

    def compile_fn(source: str) -> bool | None:
        from ztare.gates.v33_preflight_risk_detector import _compile_probe

        return _compile_probe(
            source,
            root,
            "AxiomPackBoundaryGovernanceRecheck",
            int(timeout_s),
        )

    rows: list[dict[str, Any]] = []
    for query in boundary.get("query_results") or ():
        if not isinstance(query, Mapping):
            continue
        lean = query.get("lean") or {}
        governed = lean.get("governed_attempt") if isinstance(lean, Mapping) else None
        if not isinstance(governed, Mapping):
            continue
        proof = str(governed.get("proof_text") or "").strip()
        if not proof:
            continue
        premises = tuple(str(value) for value in query.get("premise_formula_ids") or ())
        target_id = str(query.get("target_formula_id") or "")
        if target_id not in axiom_map or any(value not in axiom_map for value in premises):
            raise ValueError("saved Lean query references a formula outside the frozen context")
        task = render_lean_consequence_task(
            context.signature,
            tuple(axiom_map[value] for value in premises),
            axiom_map[target_id],
            base_axioms=context.base_axioms,
        )
        saved_task_id = str(governed.get("task_id") or lean.get("task_id") or "")
        if saved_task_id and saved_task_id != task.task_id:
            raise ValueError("saved Lean proof is bound to another reconstructed task")
        result = recheck_governed_lean_consequence(
            task,
            proof,
            compile_fn=compile_fn,
            generic_solver_outcome=str(governed.get("status") or "unknown"),
        ).to_json()
        rows.append(
            {
                "premise_formula_ids": list(premises),
                "target_formula_id": target_id,
                "previous_status": governed.get("status"),
                "previous_receipt_sha256": governed.get("receipt_sha256"),
                "recheck": result,
            }
        )
    if not rows:
        raise ValueError("boundary result contains no saved Lean proof to recheck")
    core = {
        "schema": "leanmill.frontier_boundary_governance_recheck.v1",
        "status": "recheck_completed",
        "context_hash": context.context_hash,
        "boundary_result_sha256": boundary_digest,
        "provider_calls": 0,
        "query_rechecks": rows,
        "proved_attributed_count": sum(
            row["recheck"]["status"] == "proved_attributed" for row in rows
        ),
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(output_path, receipt)
    return receipt


def run_post_freeze_literature_review(
    attempt_dir: str | Path,
    *,
    model: str = "gpt-5.5",
    reasoning_effort: str = "medium",
    repo: str | Path | None = None,
    retry_inconclusive: bool = False,
    retry_failed: bool = False,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> dict[str, Any]:
    """Run one budgeted, web-enabled interpretation after candidate freeze."""

    if reasoning_effort not in {"low", "medium", "high", "ultra"}:
        raise ValueError("post-freeze literature effort must be low, medium, high, or ultra")
    directory = Path(attempt_dir)
    if (directory / "retirement.json").is_file():
        raise ValueError("retired frontier campaign cannot run interpretation")
    if _attempt_lease is None:
        with frontier_attempt_lease(
            directory, action="post_freeze_interpretation"
        ) as lease:
            return run_post_freeze_literature_review(
                directory,
                model=model,
                reasoning_effort=reasoning_effort,
                repo=repo,
                retry_inconclusive=retry_inconclusive,
                retry_failed=retry_failed,
                _attempt_lease=lease,
            )
    _bind_active_attempt_epoch(_attempt_lease, directory)
    output_paths = [directory / "post_freeze_interpretation.json"] + sorted(
        directory.glob("post_freeze_interpretation.[0-9][0-9][0-9].json")
    )
    existing_rows: list[dict[str, Any]] = []
    for path in output_paths:
        existing = read_json(path, None)
        if not isinstance(existing, dict) or not existing:
            continue
        core = {key: value for key, value in existing.items() if key != "receipt_sha256"}
        if existing.get("receipt_sha256") != content_hash(core):
            raise ValueError("post-freeze interpretation receipt digest mismatch")
        existing_rows.append(existing)
    latest = existing_rows[-1] if existing_rows else None
    if latest is not None:
        inconclusive = (latest.get("review") or {}).get("status") == "inconclusive"
        if not (retry_inconclusive and inconclusive):
            from ztare.leanmill.theory_interpretation import (
                compose_theory_interpretation,
            )
            packet = read_json(directory / "post_freeze_result_packet.json", None)
            if isinstance(packet, Mapping) and packet.get("packet_sha256") == latest.get(
                "packet_sha256"
            ):
                write_json_atomic(
                    directory / "theory_interpretation.json",
                    compose_theory_interpretation(packet, latest),
                )
            return latest
    attempt_index = len(existing_rows)
    output_path = (
        directory / "post_freeze_interpretation.json"
        if attempt_index == 0
        else directory / f"post_freeze_interpretation.{attempt_index:03d}.json"
    )

    from ztare.leanmill.frontier_interpretation import (
        build_post_freeze_result_packet,
        post_freeze_literature_output_schema,
    )

    packet_path = directory / "post_freeze_result_packet.json"
    packet = read_json(packet_path, None)
    if isinstance(packet, Mapping) and packet:
        packet_core = {
            key: value for key, value in packet.items() if key != "packet_sha256"
        }
        if packet.get("packet_sha256") != content_hash(packet_core):
            raise ValueError("post-freeze result packet digest mismatch")
        packet = dict(packet)
    else:
        packet = build_post_freeze_result_packet(directory)
        write_json_atomic(packet_path, packet)
    definition = load_frontier_campaign_definition(
        directory / "campaign_definition.yaml"
    )
    role = frontier_agent_role(
        definition,
        role_name="post_freeze_interpreter",
        repo=Path.cwd() if repo is None else Path(repo),
        artifact_dir=directory / "agent_calls",
    )
    from ztare.common.llm_runtime import subscription_model_route

    resolved_runtime, resolved_model = subscription_model_route(
        model,
        requested_runtime=role.config.runtime,
    )
    role.config = replace(
        role.config,
        runtime=resolved_runtime,
        model=resolved_model,
        reasoning_effort=reasoning_effort,
        visible_workbench=False,
        web_research=True,
        governed_pool=False,
        allow_subscription_failover=False,
    )
    role.output_schema = post_freeze_literature_output_schema(
        formula_count=len(packet["formulas"])
    )
    prior_calls = sorted(
        (directory / "agent_calls" / "post_freeze_interpreter").glob("*.call.json")
    )
    if retry_failed:
        failed_dir = directory / "agent_calls" / "post_freeze_interpreter.failed"
        failed_dir.mkdir(parents=True, exist_ok=True)
        for call_path in prior_calls:
            call = read_json(call_path, {})
            if (
                int(call.get("returncode", 0)) == 0
                and bool(str(call.get("result_digest") or ""))
            ):
                continue
            prefix = call_path.name.split(".", 1)[0]
            for artifact in call_path.parent.glob(f"{prefix}.*"):
                os.replace(artifact, failed_dir / artifact.name)
        prior_calls = sorted(
            (directory / "agent_calls" / "post_freeze_interpreter").glob("*.call.json")
        )
    role.calls = [
        {**read_json(path, {}), "replayed": True}
        for path in prior_calls
    ]
    prompt = prompts.AXIOMPACK_POST_FREEZE_LITERATURE_PROMPT.format(
        result_packet_json=json.dumps(packet, sort_keys=True, separators=(",", ":"))
    )
    budget = ExplorationBudget.from_json(read_json(directory / "budget.json", {}))
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl", budget, attempt_id=directory.name
    )
    ledger.recover_interrupted_wall_clock()
    ledger.resume_wall_clock()
    reservation = None
    def provider_call_count() -> int:
        return int(
            getattr(role, "provider_call_count", getattr(role, "call_count", 0))
        )

    def unavailable_review(reason: str) -> dict[str, Any]:
        return {
            "status": "inconclusive",
            "formula_matches": [
                {
                    "role": str(row.get("role") or "target"),
                    "formula_id": str(row.get("formula_id") or ""),
                    "formula": str(row.get("formula") or ""),
                    "match_status": "not_found",
                    "external_id": None,
                    "source_title": None,
                    "source_url": None,
                    "confidence": "low",
                    "evidence": f"bounded review unavailable: {reason}",
                }
                for row in packet.get("formulas") or ()
                if isinstance(row, Mapping)
            ],
            "implication_prior_art": [],
            "recognized_theory_connections": [],
            "novelty_assessment": "review_unavailable",
            "mechanism_analysis": {
                "key_idea": "",
                "recombination": "",
                "invariant_or_obstruction": "",
                "premise_roles": [],
                "evidence_refs": [],
                "transportable_constraint": {
                    "constraint_class": "",
                    "abstract_form": "",
                    "invariants": [],
                    "home_field": "",
                },
            },
            "summary": "The bounded source review did not complete.",
            "limitations": [str(reason)],
            "next_checks": [
                "Retry the bounded source review from the durable packet."
            ],
        }

    before_calls = provider_call_count()
    try:
        try:
            reservation = ledger.reserve(
                f"interpretation:literature_review:{attempt_index}",
                "interpretation",
                {"provider_calls": 1, "agent_turns": 1},
            )
            result = role(prompt)
        except (KeyError, TypeError, ValueError, RuntimeError) as exc:
            # A charged provider attempt that times out or returns malformed
            # JSON still needs a durable interpretation outcome.  A failure
            # before inference remains an exception so transport setup bugs do
            # not masquerade as a scientific review.
            attempted = provider_call_count() > before_calls or bool(
                list(
                    (
                        directory / "agent_calls" / "post_freeze_interpreter"
                    ).glob("*.call.json")
                )
            )
            if not attempted:
                raise
            result = unavailable_review(str(exc))
        except BudgetExceeded as exc:
            result = unavailable_review(str(exc))
    finally:
        if reservation is not None:
            used = max(0, min(1, provider_call_count() - before_calls))
            ledger.commit(
                reservation,
                {"provider_calls": used, "agent_turns": used},
            )
        ledger.freeze_wall_clock(reason="post_freeze_interpretation_exit")
    call_receipt = read_json(
        directory / "agent_calls" / "post_freeze_interpreter"
        / f"{len(prior_calls):03d}.call.json",
        {},
    )
    core = {
        "schema": "leanmill.post_freeze_interpretation.v1",
        "status": (
            "interpretation_completed"
            if result.get("status") == "completed"
            else "interpretation_inconclusive"
        ),
        "attempt_index": attempt_index,
        "previous_receipt_sha256": (
            latest.get("receipt_sha256") if latest is not None else None
        ),
        "packet_sha256": packet["packet_sha256"],
        "context_hash": packet["context_hash"],
        "boundary_result_sha256": packet["boundary_result_sha256"],
        "governance_recheck_sha256": packet["governance_recheck_sha256"],
        "runtime": role.config.runtime,
        "model": role.config.model,
        "requested_model": model,
        "reasoning_effort": reasoning_effort,
        "provider_calls": max(0, min(1, provider_call_count() - before_calls)),
        "agent_call_receipt": {
            "prompt_digest": call_receipt.get("prompt_digest"),
            "result_digest": call_receipt.get("result_digest"),
            "output_schema_digest": call_receipt.get("output_schema_digest"),
        },
        "review": result,
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(output_path, receipt)
    from ztare.leanmill.theory_interpretation import compose_theory_interpretation

    write_json_atomic(
        directory / "theory_interpretation.json",
        compose_theory_interpretation(packet, receipt),
    )
    return receipt


__all__ = [
    "FrontierAttemptLeaseBusy",
    "FrontierAttemptLeaseLost",
    "attempt_lease_status",
    "execute_frontier_adapter_forge",
    "execute_frontier_campaign_verification",
    "frontier_agent_role",
    "frontier_attempt_lease",
    "frontier_attempt_work_id",
    "materialize_frontier_navigation_from_journal",
    "recheck_frontier_boundary_governance",
    "run_post_freeze_literature_review",
    "resume_frontier_campaign_navigation",
    "run_frontier_campaign_definition",
]
