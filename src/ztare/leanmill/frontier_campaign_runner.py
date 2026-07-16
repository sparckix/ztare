"""Canonical runtime door for one frontier AxiomPack campaign."""
from __future__ import annotations

from contextlib import contextmanager
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
from typing import Any, Callable, Mapping

from ztare.common.subscription_agent_runtime import subscription_dispatch_budget_scope
from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment
from ztare.leanmill import prompts
from ztare.leanmill.axiompack_leaf_workbench import (
    reviewed_axiompack_workbench_successor,
)
from ztare.leanmill.common import (
    read_json,
    sha256_file,
    write_json_atomic,
    write_text_atomic,
)
from ztare.leanmill.explore_axiom_space import (
    _boundary_completion_covers,
    _freeze_theory_conflict_memory,
    _learn_navigation_conflicts,
    _resolve_workbench_evidence_receipts,
    _workbench_evidence_binding,
    admit_frontier_formula_epoch,
    consume_theory_language_compilation,
    drive_frontier_navigation,
    execute_frontier_boundaries,
    explore_axiom_space,
    finish_frontier_navigation,
    freeze_frontier_formula_successor_request,
    lower_theory_language_request,
    packet_for_frontier_context,
)
from ztare.leanmill.exploration_budget import (
    BudgetExceeded,
    BudgetReservation,
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
    cold_navigator_manifest,
    host_isolated_lineage_count,
    frontier_objective_contract,
    navigator_selection_mode,
)
from ztare.leanmill.frontier_blueprint_compiler import (
    compile_language_successor_blueprint,
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
    durable_navigator_turn_count,
    run_host_isolated_theory_lineages,
    theory_search_wave_image_receipt,
)
from ztare.leanmill.theory_lineage_synthesis import (
    build_theory_move_portfolio,
    lineage_request_matches_context,
    lineage_synthesis_input,
    lineage_synthesis_output_schema,
    validate_lineage_synthesis_decision,
    theory_move_consequence_receipt,
)
from ztare.leanmill.theory_program import TheoryProgram, derive_context_lineage_id
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


def _durable_navigator_segment(
    call_dir: Path,
    *,
    receipt_index: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], tuple[dict[str, Any], ...]]:
    """Load one immutable call segment with its causal prompt trace."""

    calls, decisions = _read_durable_navigator_decisions(call_dir)
    if not decisions:
        return calls, decisions, ()
    prompt_path = call_dir / "000.prompt.txt"
    if not prompt_path.is_file():
        return calls, decisions, ()
    marker = "\nCURRENT TRACE:\n"
    prompt = prompt_path.read_text(encoding="utf-8")
    if marker not in prompt:
        raise ValueError("durable navigator prompt has no causal trace")
    trace = json.loads(prompt.rsplit(marker, 1)[1].strip())
    if not isinstance(trace, list) or any(not isinstance(row, dict) for row in trace):
        raise ValueError("durable navigator prompt trace is malformed")
    indexed = receipt_index or {}
    hydrated = []
    for row in trace:
        receipt = row.get("receipt")
        receipt_id = (
            str(receipt.get("receipt_id") or "")
            if isinstance(receipt, Mapping)
            else ""
        )
        hydrated.append(
            {**row, "receipt": dict(indexed[receipt_id])}
            if receipt_id in indexed
            else row
        )
    return calls, decisions, tuple(hydrated)


def _navigator_receipt_index(run: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Index full host receipts retained by the last materialized read model."""

    navigation = run.get("navigation") or {}
    traces = [navigation.get("trace") or ()] + [
        (lineage.get("navigation") or {}).get("trace") or ()
        for lineage in navigation.get("lineages") or ()
        if isinstance(lineage, Mapping)
    ]
    index: dict[str, dict[str, Any]] = {}
    for row in (row for trace in traces for row in trace if isinstance(row, Mapping)):
        receipt = row.get("receipt")
        if not isinstance(receipt, Mapping):
            continue
        receipt_id = str(receipt.get("receipt_id") or "")
        core = {key: value for key, value in receipt.items() if key != "receipt_id"}
        if receipt_id == "sha256:" + content_hash(core):
            index[receipt_id] = dict(receipt)
    return index


def _terminal_navigation(navigation: Mapping[str, Any]) -> bool:
    return bool(
        navigation.get("finalists")
        or navigation.get("reject_all_receipt")
        or navigation.get("expansion_proposal")
        or navigation.get("language_expansion_request")
    )


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
    elif role_name == "external_science_reviewer" and config.runtime == "codex":
        from ztare.leanmill.external_science_admission import (
            external_science_review_output_schema,
        )

        output_schema = external_science_review_output_schema()
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


def _workbench_successor_target(
    source_packet: Mapping[str, Any], target_packet: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate that packet drift is solely one reviewed workbench successor."""

    source_without_workbench = {
        key: value for key, value in source_packet.items()
        if key != "navigator_contract"
    }
    target_without_workbench = {
        key: value for key, value in target_packet.items()
        if key != "navigator_contract"
    }
    if source_without_workbench != target_without_workbench:
        raise ValueError("active campaign packet changed outside the workbench contract")
    source_contract = source_packet.get("navigator_contract")
    target_contract = target_packet.get("navigator_contract")
    if not isinstance(source_contract, Mapping) or not isinstance(
        target_contract, Mapping
    ):
        raise ValueError("campaign packet lacks a workbench contract")
    return reviewed_axiompack_workbench_successor(
        source_contract, target_contract
    )


def _workbench_successor_authorization_required(
    directory: Path,
    *,
    campaign: Mapping[str, Any],
    target_packet: Mapping[str, Any],
    context_epoch: int,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    core = {
        "schema": "leanmill.campaign_workbench_successor_authorization_required.v1",
        "attempt_id": directory.name,
        "campaign_id": str((campaign.get("packet") or {}).get("campaign_id") or ""),
        "context_epoch": context_epoch,
        "source_packet_digest": str(campaign.get("packet_digest") or ""),
        "target_packet_digest": "sha256:" + content_hash(target_packet),
        "policy": dict(policy),
        "status": "authority_required",
        "next_route": "resume_with_workbench_authority_ref",
        "claim_boundary": "no campaign or workbench identity changed",
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(
        directory / "campaign_workbench_successor_authorization_required.json",
        receipt,
    )
    return receipt


def _admit_campaign_workbench_successor(
    directory: Path,
    *,
    campaign: Mapping[str, Any],
    target_packet: Any,
    context_epoch: int,
    authority_ref: str,
) -> Any:
    """Sign and publish one authority-bound campaign workbench successor."""

    source_packet = campaign.get("packet")
    if not isinstance(source_packet, Mapping):
        raise ValueError("campaign workbench successor lacks a source packet")
    target_json = target_packet.to_json()
    policy = _workbench_successor_target(source_packet, target_json)
    authority = str(authority_ref or "").strip()
    if not authority:
        _workbench_successor_authorization_required(
            directory,
            campaign=campaign,
            target_packet=target_json,
            context_epoch=context_epoch,
            policy=policy,
        )
        return None

    source_digest = str(campaign.get("packet_digest") or "")
    target_digest = str(target_packet.digest)
    core = {
        "schema": "leanmill.campaign_workbench_successor_transition.v1",
        "attempt_id": directory.name,
        "campaign_id": str(source_packet.get("campaign_id") or ""),
        "context_hash": str(
            (source_packet.get("visible_context_manifest") or {}).get(
                "context_hash"
            )
            or ""
        ),
        "context_epoch": context_epoch,
        "source_packet_digest": source_digest,
        "target_packet_digest": target_digest,
        "policy": dict(policy),
        "authority_ref": authority,
        "transition": "reviewed_campaign_workbench_successor",
        "claim_boundary": (
            "the semantic context and reviewed blueprint are unchanged; the "
            "execution workbench advances under a named migration policy"
        ),
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    suffix = target_digest.split(":")[-1][:16]
    receipt_path = directory / f"campaign_workbench_successor.{suffix}.json"
    existing_receipt = read_json(receipt_path, None)
    if isinstance(existing_receipt, Mapping):
        if dict(existing_receipt) != receipt:
            raise ValueError("campaign workbench successor receipt conflicts")
    else:
        write_json_atomic(receipt_path, receipt)

    signer_path = directory / "private" / "campaign_signer.pem"
    if not signer_path.is_file():
        raise ValueError("campaign workbench successor cannot locate signer")
    signed = sign_frontier_campaign(
        target_packet,
        private_key_pem=signer_path.read_text(encoding="utf-8"),
        signer_ref=str(campaign.get("signer_ref") or ""),
    ).to_json()
    archive = directory / (
        f"campaign.epoch-{context_epoch:03d}.workbench-{suffix}.json"
    )
    existing_archive = read_json(archive, None)
    if isinstance(existing_archive, Mapping):
        if dict(existing_archive) != signed:
            raise ValueError("campaign workbench successor archive conflicts")
    else:
        write_json_atomic(archive, signed)

    run = read_json(directory / "run.json", None)
    if isinstance(run, Mapping):
        run_archive = directory / f"run.before-workbench-{suffix}.json"
        existing_run_archive = read_json(run_archive, None)
        if isinstance(existing_run_archive, Mapping):
            if dict(existing_run_archive) != dict(run):
                raise ValueError("campaign workbench predecessor run conflicts")
        else:
            write_json_atomic(run_archive, dict(run))

    checkpoint_path = directory / "navigation_epoch_checkpoint.json"
    checkpoint = read_json(checkpoint_path, None)
    if isinstance(checkpoint, Mapping):
        trace = [
            dict(row) for row in checkpoint.get("trace") or ()
            if isinstance(row, Mapping)
        ]
        if not any(
            row.get("decision") == "campaign_workbench_successor_admitted"
            and row.get("receipt_sha256") == receipt["receipt_sha256"]
            for row in trace
        ):
            trace.append(
                {
                    "decision": "campaign_workbench_successor_admitted",
                    "receipt_sha256": receipt["receipt_sha256"],
                    "policy_id": policy["policy_id"],
                    "authority_ref": authority,
                }
            )
            write_json_atomic(
                checkpoint_path, {**dict(checkpoint), "trace": trace}
            )

    write_json_atomic(directory / "campaign.json", signed)
    required = directory / "campaign_workbench_successor_authorization_required.json"
    if required.is_file():
        required.unlink()
    return target_packet


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


@contextmanager
def _initial_frontier_attempt_owner(
    attempt_dir: Path, epoch: int, context_hash: str
):
    """Put initial navigation behind the same queue owner as every continuation."""

    with frontier_attempt_lease(
        attempt_dir, action="initial_frontier_navigation"
    ) as lease:
        lease.bind_epoch(epoch=epoch, context_hash=context_hash)
        yield lease


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
    consequence = navigation.get("adaptive_move_consequence_receipt")
    if isinstance(consequence, Mapping):
        aggregate.append(
            TheoryCampaignEvent(
                attempt_id=attempt_id,
                campaign_id=campaign_id,
                epoch=epoch,
                context_hash=context_hash,
                event_type="navigator_action_executed",
                subject_ids=(str(consequence["receipt_sha256"]),),
                input_refs=(
                    str(consequence["source_synthesis_receipt_sha256"]),
                    str(consequence["planned_continuation_mode"]),
                ),
                output_refs=tuple(
                    str(row) for row in consequence.get("evidence_refs") or ()
                ),
                evidence_status="witnessed",
                authority="host_adaptive_move_observer",
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

    # A search wave can consist only of a late synthesis call (for example,
    # when a carried boundary survivor needs a new disposition but no leaf is
    # queried).  Navigator call directories therefore do not by themselves
    # own the durable wave identity.  Recover from every frozen wave sidecar
    # as well, so a restart cannot reopen and replay an already-consumed
    # synthesis decision.
    persisted_wave_paths = list(
        (directory / "agent_calls").glob("navigator*.wave-*")
    ) + list(directory.glob("*.wave-*.json"))
    search_wave = max(
        [0]
        + [
            int(match.group(1))
            for path in persisted_wave_paths
            if (
                match := re.search(
                    r"\.wave-(\d{3})(?:\.json)?$", path.name
                )
            )
            is not None
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
            preserved_rows = dict(
                getattr(navigator, "preserved_lineage_rows", {})
            )
            active_indices = [
                index for index in range(count) if index not in preserved_rows
            ]
            lineage_budget_phase = (
                "expansion"
                if isinstance(getattr(navigator, "objective_feedback", None), Mapping)
                else "navigation"
            )
            rounds_by_lineage: int | tuple[int, ...] = max(1, total_rounds // count)
            if budget_ledger is not None:
                durable_turns = {
                    index: durable_navigator_turn_count(roles[index])
                    for index in active_indices
                }
                available = min(
                    max(0, total_rounds - sum(durable_turns.values())),
                    budget_ledger.remaining_capacity(
                        lineage_budget_phase, "provider_calls"
                    ),
                    budget_ledger.remaining_capacity(
                        lineage_budget_phase, "agent_turns"
                    ),
                )
                if (
                    available > len(active_indices)
                    and frontier_objective_contract(blueprint) is not None
                ):
                    available -= 1  # late synthesis owns the final disposition
                ordered_indices = sorted(
                    active_indices,
                    key=lambda index: (durable_turns[index], index),
                )
                base, remainder = divmod(
                    max(0, available), max(1, len(ordered_indices))
                )
                allocation = {
                    index: durable_turns.get(index, 0)
                    for index in range(count)
                }
                for position, index in enumerate(ordered_indices):
                    allocation[index] += base + int(position < remainder)
                rounds_by_lineage = tuple(allocation.values())
            common_trace = epoch_seed + (
                ({
                    "decision": "late_objective_review_requested_continuation",
                    "program_ids": list(getattr(navigator, "objective_feedback", {}).get("program_ids", ())),
                    "continuation_mode": str(getattr(navigator, "objective_feedback", {}).get("continuation_mode", "")),
                    "next_discriminator": str(getattr(navigator, "objective_feedback", {}).get("next_discriminator", "")),
                    "kill_condition": str(getattr(navigator, "objective_feedback", {}).get("kill_condition", "")),
                    "source_synthesis_receipt_sha256": str(
                        getattr(navigator, "objective_feedback", {}).get(
                            "receipt_sha256", ""
                        )
                    ),
                    "move_portfolio_receipt_sha256": str(
                        getattr(navigator, "objective_feedback", {}).get(
                            "move_portfolio_receipt_sha256", ""
                        )
                    ),
                    "authority": "late_leaf_choice_host_validated",
                },)
                if isinstance(getattr(navigator, "objective_feedback", None), Mapping)
                else ()
            )
            branch_traces = getattr(navigator, "lineage_initial_traces", None)
            result = run_host_isolated_theory_lineages(
                context,
                blueprint,
                agent_fns=roles,
                journal_root=directory / "lineage_journals",
                attempt_id=attempt_id,
                campaign_id="campaign:" + blueprint.blueprint_id.split(":", 1)[1][:24],
                max_rounds=rounds_by_lineage,
                max_finalists_per_lineage=max(1, total_finalists // count),
                budget_ledger=budget_ledger,
                epoch=epoch,
                prior_conflict_rows=tuple(getattr(navigator, "prior_conflict_rows", ())),
                initial_trace=common_trace,
                initial_traces=branch_traces,
                preserved_lineage_rows=preserved_rows,
                budget_phase=lineage_budget_phase,
            )
            recovered_requests = tuple(
                getattr(navigator, "recovered_lineage_requests", ())
            )
            if recovered_requests:
                existing_ids = {
                    str(row.get("request_id") or "")
                    for row in result.get("expansion_proposals") or ()
                }
                result = {
                    **result,
                    "expansion_proposals": list(
                        result.get("expansion_proposals") or ()
                    ) + [
                        dict(row)
                        for row in recovered_requests
                        if str(row.get("request_id") or "") not in existing_ids
                    ],
                }
        result = {**result, "search_wave": search_wave}
        wave_provider_calls = int(result.get("wave_provider_calls", 0))
        retry_synthesis = bool(getattr(navigator, "retry_synthesis", False))
        final_path = directory / (
            "theory_search_wave_image.final."
            f"epoch-{int(result.get('context_epoch', 0)):03d}."
            f"wave-{search_wave:03d}.json"
        )
        prior_wave_receipts = [
            row
            for path in sorted(
                directory.glob("theory_search_wave_image.final.epoch-*.wave-*.json")
            )
            if path != final_path
            if isinstance((row := read_json(path, None)), Mapping)
            and row.get("context_hash") == context.context_hash
        ]
        if wave_provider_calls:
            wave_image = theory_search_wave_image_receipt(
                result,
                prior_receipts=prior_wave_receipts,
            )
            if result.get("pending_leaf_decisions"):
                result = {**result, "search_wave_image_preview": wave_image}
            else:
                frozen_wave_image = read_json(final_path, None)
                if isinstance(frozen_wave_image, Mapping):
                    if dict(frozen_wave_image) != wave_image:
                        raise ValueError("frozen theory search-wave image changed identity")
                else:
                    write_json_atomic(final_path, wave_image)
                result = {**result, "search_wave_image_receipt": wave_image}
        elif retry_synthesis:
            prior_image = next(
                (
                    row
                    for path in reversed(sorted(directory.glob(
                        "theory_search_wave_image.final.epoch-*.wave-*.json"
                    )))
                    if isinstance((row := read_json(path, None)), Mapping)
                ),
                None,
            )
            if prior_image is not None:
                result = {**result, "search_wave_image_receipt": dict(prior_image)}
        objective_feedback = getattr(navigator, "objective_feedback", None)
        if (
            isinstance(objective_feedback, Mapping)
            and objective_feedback.get("schema")
            == _POST_FREEZE_RESEARCH_DISPOSITION_SCHEMA
        ):
            result = {
                **result,
                "post_freeze_research_disposition": dict(objective_feedback),
            }
        objective_survivors = tuple(
            dict(row)
            for row in getattr(navigator, "objective_survivors", ())
            if isinstance(row, Mapping)
        )
        if objective_survivors:
            result = {
                **result,
                "objective_survivors": list(objective_survivors),
            }
            # A replayed synthesis input is immutable.  On a fresh wave, make
            # the active programs visible to the leaf; on recovery, retain the
            # sidecar and replay the already-authored disposition unchanged.
            wave_suffix = f".wave-{search_wave:03d}" if search_wave else ""
            input_path = directory / (
                "lineage_synthesis_input."
                f"epoch-{int(result.get('context_epoch', 0)):03d}"
                f"{wave_suffix}.json"
            )
            if not input_path.is_file():
                seen_programs = {
                    str(row.get("theory_program_id") or "")
                    for row in result.get("finalists") or ()
                    if isinstance(row, Mapping)
                }
                result = {
                    **result,
                    "finalists": list(result.get("finalists") or ())
                    + [
                        row
                        for row in objective_survivors
                        if str(row.get("theory_program_id") or "")
                        not in seen_programs
                    ],
                }
        if (
            isinstance(objective_feedback, Mapping)
            and objective_feedback.get("schema")
            == "leanmill.lineage_synthesis_decision.v1"
            and objective_feedback.get("continuation_mode")
        ):
            result = {
                **result,
                "adaptive_move_consequence_receipt": (
                    theory_move_consequence_receipt(result, objective_feedback)
                ),
            }
        objective_contract = frontier_objective_contract(blueprint)
        if (
            not result.get("pending_leaf_decisions")
            and (
                wave_provider_calls
                or retry_synthesis
                or result.get("finalists")
                or result.get("expansion_proposals")
                or result.get("theory_language_expansion_requests")
            )
            and (
                result.get("expansion_proposals")
                or result.get("theory_language_expansion_requests")
                or objective_contract is not None
            )
        ):
            wave_suffix = f".wave-{search_wave:03d}" if search_wave else ""
            synthesis_input_path = directory / (
                "lineage_synthesis_input."
                f"epoch-{int(result.get('context_epoch', 0)):03d}"
                f"{wave_suffix}.json"
            )
            prior_synthesis_input = read_json(synthesis_input_path, None)
            if isinstance(prior_synthesis_input, Mapping):
                prior_portfolio = prior_synthesis_input.get(
                    "adaptive_move_portfolio"
                )
                if isinstance(prior_portfolio, Mapping):
                    result = {
                        **result,
                        "adaptive_move_portfolio": dict(prior_portfolio),
                    }
            else:
                result = {
                    **result,
                    "adaptive_move_portfolio": build_theory_move_portfolio(
                        result, objective_contract=objective_contract
                    ),
                }
            if isinstance(prior_synthesis_input, Mapping):
                frozen_core = {
                    key: value
                    for key, value in prior_synthesis_input.items()
                    if key != "input_sha256"
                }
                if (
                    prior_synthesis_input.get("input_sha256")
                    != content_hash(frozen_core)
                    or str(prior_synthesis_input.get("context_hash") or "")
                    != str(result.get("context_hash") or "")
                    or int(prior_synthesis_input.get("context_epoch", -1))
                    != int(result.get("context_epoch", 0))
                ):
                    raise ValueError("frozen lineage synthesis input failed replay")
                # The persisted input, rather than today's projection code, is
                # the authority for a durable authored call.  Read-model
                # evolution may add fields without changing historical bytes.
                synthesis_input = dict(prior_synthesis_input)
            else:
                synthesis_input = lineage_synthesis_input(
                    result, objective_contract=objective_contract
                )
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
                "expansion"
                if isinstance(objective_feedback, Mapping)
                else (
                    "boundary"
                    if objective_contract is not None
                    and not result.get("expansion_proposals")
                    and not result.get("theory_language_expansion_requests")
                    else "navigation"
                )
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

    def clear_transient_lineage_state() -> None:
        for name in (
            "lineage_initial_traces",
            "preserved_lineage_rows",
            "recovered_lineage_requests",
            "retry_synthesis",
        ):
            if hasattr(navigator, name):
                delattr(navigator, name)

    def begin_search_wave() -> None:
        """Open fresh agent-call identities without changing the theory epoch."""

        nonlocal search_wave, single_role, single, synthesis_role
        search_wave += 1
        lineage_roles.clear()
        synthesis_role = None
        clear_transient_lineage_state()
        single_role, single = make_single()
        navigator.search_wave = search_wave  # type: ignore[attr-defined]

    navigator.begin_search_wave = begin_search_wave  # type: ignore[attr-defined]
    navigator.search_wave = search_wave  # type: ignore[attr-defined]
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
        clear_transient_lineage_state()
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
            # This wrapper is a transparent one-shot prefix.  Once consumed it
            # must forward the complete navigator transition identity; in
            # particular, an admitted successor epoch is meaningless without
            # the host-authored causal trace that opened it.
            for name in (
                "objective_feedback",
                "epoch",
                "initial_trace",
                "prior_conflict_rows",
            ):
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
            navigation_ownership_fn=_initial_frontier_attempt_owner,
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
        host_capability_conformance,
        stage_adapter_forge_workspace,
    )

    definition = load_frontier_campaign_definition(directory / "campaign_definition.yaml")
    gap_row = read_json(directory / "adapter_gap.json", {})
    gap = AdapterGap.from_json(gap_row)
    if "evidence_binding" not in gap.primitive_semantics_contract:
        run = read_json(directory / "run.json", {})
        navigation = dict(run.get("navigation") or {})
        receipts = gap.primitive_semantics_contract.get("evidence_fixtures")
        if not isinstance(receipts, list):
            receipts = _resolve_workbench_evidence_receipts(
                directory, navigation, gap.raw_fixture_refs
            )
        contract = {
            **{
                key: value
                for key, value in gap.primitive_semantics_contract.items()
                if key != "evidence_fixtures"
            },
            "evidence_binding": _workbench_evidence_binding(receipts),
        }
        gap = replace(gap, primitive_semantics_contract=contract)
        write_json_atomic(directory / "adapter_gap.json", gap.to_json())
        navigation["adapter_gap"] = gap.to_json()
        run_core = {
            **{key: value for key, value in run.items() if key != "run_digest"},
            "adapter_gap": gap.to_json(),
            "navigation": navigation,
        }
        write_json_atomic(
            directory / "run.json",
            {**run_core, "run_digest": content_hash(run_core)},
        )
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

    recovered_review = None
    for result_path in sorted(
        (directory / "agent_calls").glob("adapter_reviewer*/000.result.json"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    ):
        call = read_json(result_path.with_name("000.call.json"), {})
        candidate = read_json(result_path, {})
        if (
            int(call.get("returncode", 1)) == 0
            and isinstance(candidate, Mapping)
            and type(candidate.get("accepted")) is bool
        ):
            recovered_review = dict(candidate)
            break

    def recovered_reviewing(_packet: Mapping[str, Any]) -> Mapping[str, Any]:
        assert recovered_review is not None
        return recovered_review

    recovered_reviewing.provider_call_count = 0  # type: ignore[attr-defined]
    recovered_reviewing.recovered_review = True  # type: ignore[attr-defined]

    def conformance(proposal: Mapping[str, Any], typed_gap: AdapterGap) -> Mapping[str, Any]:
        if content_hash({"bytes": registry_path.read_text(encoding="utf-8")}) != registry_digest:
            raise ValueError("AdapterForge changed the live adapter registry")
        if typed_gap.gap_kind != "capability_missing":
            raise ValueError("full adapter conformance is not executable in this campaign")
        result = host_capability_conformance(
            proposal,
            typed_gap,
            workspace=workspace,
            output_path=directory / "theory_language_coordinates.json",
        )
        write_json_atomic(directory / "adapter_forge_host_conformance.json", result)
        return result

    completion = execute_adapter_forge_attempt(
        directory,
        coding_agent_fn=recovered_coding if recovered_proposal is not None else coding,
        host_conformance_fn=conformance,
        independent_review_fn=(
            recovered_reviewing
            if recovered_review is not None
            else make_subscription_adapter_reviewer(review)
        ),
    )
    return completion


def _approved_functor_application(
    directory: Path, completion: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Verify that host conformance and independent review approve one local image."""

    completion_core = {
        key: value for key, value in completion.items() if key != "completion_sha256"
    }
    if (
        completion.get("schema") != "leanmill.adapter_forge_completion.v1"
        or completion.get("completion_sha256") != content_hash(completion_core)
    ):
        raise ValueError("AdapterForge completion does not replay")
    receipt = completion.get("quarantine_receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("AdapterForge completion lacks its quarantine receipt")
    receipt_core = {
        key: value for key, value in receipt.items() if key != "receipt_sha256"
    }
    review = receipt.get("independent_review")
    conformance = receipt.get("host_conformance")
    if (
        receipt.get("receipt_sha256") != content_hash(receipt_core)
        or receipt.get("status") != "quarantined_registry_proposal"
        or receipt.get("live_registry_mutated") is not False
        or not isinstance(review, Mapping)
        or review.get("accepted") is not True
        or not isinstance(conformance, Mapping)
        or conformance.get("ok") is not True
    ):
        raise ValueError("campaign-local functor image lacks accepted host review")
    conformance_core = {
        key: value for key, value in conformance.items() if key != "receipt_sha256"
    }
    if conformance.get("receipt_sha256") != content_hash(conformance_core):
        raise ValueError("AdapterForge host conformance digest mismatch")
    generative_receipt = conformance.get("candidate_receipt_sha256")
    if generative_receipt:
        from ztare.leanmill.finite_theory_context import load_formal_theory_context
        from ztare.leanmill.generative_representation import (
            CANDIDATE_SCHEMA,
            admit_materialized_generative_representation,
        )

        if conformance.get("interface") != CANDIDATE_SCHEMA:
            raise ValueError("generative candidate crossed its Forge interface")
        candidate = read_json(
            directory / "theory_language_generative_candidate.json", None
        )
        if (
            not isinstance(candidate, Mapping)
            or candidate.get("receipt_sha256") != generative_receipt
            or candidate.get("gap_id") != completion.get("gap_id")
        ):
            raise ValueError("reviewed generative candidate artifact is missing")
        source_context = load_formal_theory_context(directory / "formal_context.json")
        _reviewed, application = admit_materialized_generative_representation(
            candidate,
            source_context=source_context,
            host_conformance=conformance,
            independent_review=review,
        )
        write_json_atomic(
            directory / "theory_language_generative_application.json", application
        )
        return application, dict(receipt)
    application = read_json(directory / "theory_language_functor_image.json", None)
    if not isinstance(application, Mapping):
        if not conformance.get("functor_image_receipt_sha256"):
            return None, dict(receipt)
        raise ValueError("reviewed functor application artifact is missing")
    application_core = {
        key: value for key, value in application.items() if key != "receipt_sha256"
    }
    if (
        application.get("receipt_sha256") != content_hash(application_core)
        or application.get("receipt_sha256")
        != conformance.get("functor_image_receipt_sha256")
        or application.get("gap_id") != completion.get("gap_id")
    ):
        raise ValueError("campaign-local functor application is not review-bound")
    return dict(application), dict(receipt)


def _language_request_from_run(run: Mapping[str, Any]) -> TheoryLanguageExpansionRequest:
    navigation = run.get("navigation")
    if not isinstance(navigation, Mapping):
        raise ValueError("language continuation lacks frozen navigation")
    row = navigation.get("language_expansion_request")
    if isinstance(row, Mapping):
        return TheoryLanguageExpansionRequest.from_json(row)
    synthesis = navigation.get("lineage_synthesis")
    selected = synthesis.get("selected_requests") if isinstance(synthesis, Mapping) else None
    if isinstance(selected, list) and len(selected) == 1 and isinstance(
        selected[0], Mapping
    ) and isinstance(selected[0].get("request"), Mapping):
        return TheoryLanguageExpansionRequest.from_json(selected[0]["request"])
    gap = run.get("adapter_gap")
    contract = gap.get("primitive_semantics_contract") if isinstance(gap, Mapping) else None
    request = contract.get("theory_language_request") if isinstance(contract, Mapping) else None
    if isinstance(request, Mapping):
        return TheoryLanguageExpansionRequest.from_json(request)
    raise ValueError("language continuation has no typed request")


def _stale_boundary_disposition_needs_fresh_wave(
    run: Mapping[str, Any],
) -> bool:
    """Recognize a pre-fix status projection without inventing a request.

    Older runs could project deferred language requests as an active language
    transition after replaying a synthesis-only ``proceed_boundary`` wave.
    The carried objective survivor, rather than any deferred request, owns the
    next transition in that state.
    """

    if run.get("status") != "frontier_language_expansion_requested":
        return False
    navigation = run.get("navigation")
    if not isinstance(navigation, Mapping):
        return False
    synthesis = navigation.get("lineage_synthesis")
    return bool(
        isinstance(synthesis, Mapping)
        and synthesis.get("route") == "proceed_boundary"
        and not navigation.get("finalists")
        and navigation.get("objective_survivors")
        and not navigation.get("language_expansion_request")
        and not synthesis.get("selected_requests")
    )


def _repair_stale_boundary_disposition_status(
    directory: Path,
    run: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    """Return a misprojected durable run to objective navigation."""

    if not isinstance(run, Mapping) or not _stale_boundary_disposition_needs_fresh_wave(
        run
    ):
        return run
    core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "status": "frontier_objective_unmet",
    }
    repaired = {**core, "run_digest": content_hash(core)}
    write_json_atomic(directory / "run.json", repaired)
    return repaired


def _restore_nested_objective_feedback_history(
    directory: Path,
    run: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    """Promote carried candidate feedback back into the navigation history.

    Boundary survivors retain their exact feedback receipt inside the candidate
    row.  A pre-fix resume could lose the corresponding top-level history row
    while projecting the next run.  Recovering that existing receipt preserves
    the causal input for later epochs without manufacturing new evidence.
    """

    if not isinstance(run, Mapping):
        return run
    navigation_row = run.get("navigation")
    if not isinstance(navigation_row, Mapping):
        return run
    navigation = dict(navigation_row)
    history = [
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
    ]
    seen = {
        str(row.get("receipt_sha256") or content_hash(row)) for row in history
    }
    changed = False
    for survivor in navigation.get("objective_survivors") or ():
        feedback = (
            survivor.get("objective_feedback")
            if isinstance(survivor, Mapping)
            else None
        )
        if not isinstance(feedback, Mapping):
            continue
        feedback_core = {
            key: value for key, value in feedback.items() if key != "receipt_sha256"
        }
        receipt = str(feedback.get("receipt_sha256") or "")
        if not receipt or receipt != content_hash(feedback_core):
            raise ValueError("nested objective feedback receipt does not replay")
        if receipt in seen:
            continue
        history.append(dict(feedback))
        seen.add(receipt)
        changed = True
    if not changed:
        return run
    navigation["objective_review_history"] = history
    core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "navigation": navigation,
    }
    repaired = {**core, "run_digest": content_hash(core)}
    write_json_atomic(directory / "run.json", repaired)
    return repaired


def _language_outcome_feedback(
    directory: Path,
    run: Mapping[str, Any],
    *,
    outcome: str,
    reason: str,
    evidence_refs: tuple[str, ...],
) -> dict[str, Any]:
    """Return rejected/unavailable compiler outcomes to the navigator."""

    if outcome not in {"rejected", "unavailable"}:
        raise ValueError("unknown language compilation feedback outcome")
    navigation = dict(run.get("navigation") or {})
    request = _language_request_from_run(run)
    core = {
        "schema": "leanmill.theory_language_compilation_feedback.v1",
        "context_hash": str(run.get("context_hash") or ""),
        "request_id": request.request_id,
        "outcome": outcome,
        "reason": reason,
        "evidence_refs": list(evidence_refs),
        "route": "continue_search",
        "program_ids": [],
        "repeat_requires_new_evidence": True,
        "authority": "host_language_compiler",
    }
    feedback = {**core, "receipt_sha256": content_hash(core)}
    history = list(navigation.get("objective_review_history") or ())
    history.append(feedback)
    navigation["objective_review_history"] = history
    for stale in (
        "adapter_gap",
        "language_expansion_request",
        "theory_language_expansion_requests",
        "lineage_synthesis",
    ):
        navigation.pop(stale, None)
    run_core = {
        **{
            key: value
            for key, value in run.items()
            if key not in {"run_digest", "adapter_gap"}
        },
        "status": "frontier_objective_unmet",
        "navigation": navigation,
        "adapter_gap": None,
    }
    write_json_atomic(
        directory / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    write_json_atomic(directory / "theory_language_compilation_feedback.json", feedback)
    return feedback


def _admit_language_successor(
    directory: Path,
    *,
    run: Mapping[str, Any],
    blueprint: FrontierTheoryBlueprint,
    campaign: Mapping[str, Any],
    source_context: Any,
    source_epoch: int,
    request: TheoryLanguageExpansionRequest,
    lowered: Mapping[str, Any],
    admission_receipt_sha256: str,
    admission_review: Mapping[str, Any],
    resume_fn: Callable[..., Any] | None,
    attempt_lease: _FrontierAttemptLease,
) -> dict[str, Any]:
    """Commit one compiled language chart as the next campaign epoch."""

    target_context = lowered["context"]
    transition = lowered["context_transition"]
    target_blueprint = compile_language_successor_blueprint(
        blueprint,
        request_id=request.request_id,
        target_context=target_context,
        transition=transition,
        adapter_id=str(lowered["adapter_id"]),
        admission_receipt_sha256=admission_receipt_sha256,
        admission_review=admission_review,
    )
    target_epoch = source_epoch + 1
    source_run_path = directory / f"run.epoch-{source_epoch:03d}.json"
    if source_run_path.is_file() and read_json(source_run_path, {}) != dict(run):
        raise ValueError("source language epoch archive conflicts with active run")
    if not source_run_path.is_file():
        write_json_atomic(source_run_path, dict(run))
    blueprint_archive = directory / f"blueprint.epoch-{source_epoch:03d}.json"
    if not blueprint_archive.is_file():
        write_json_atomic(blueprint_archive, blueprint.to_json())
    from ztare.leanmill.finite_theory_context import save_formal_theory_context

    save_formal_theory_context(target_context, directory / "formal_context.json")
    save_formal_theory_context(
        target_context, directory / f"formal_context.epoch-{target_epoch:03d}.json"
    )
    write_json_atomic(directory / "blueprint.json", target_blueprint.to_json())
    write_json_atomic(
        directory / f"blueprint.epoch-{target_epoch:03d}.json",
        target_blueprint.to_json(),
    )
    write_json_atomic(
        directory / "cold_navigator_manifest.json",
        cold_navigator_manifest(target_blueprint),
    )
    packet = packet_for_frontier_context(
        target_blueprint,
        target_context,
        campaign_id=str((campaign.get("packet") or {})["campaign_id"]),
        context_epoch=target_epoch,
    )
    signer_path = directory / "private" / "campaign_signer.pem"
    signed = sign_frontier_campaign(
        packet,
        private_key_pem=signer_path.read_text(encoding="utf-8"),
        signer_ref=str(campaign.get("signer_ref") or "axiompack-campaign-authority"),
    ).to_json()
    write_json_atomic(directory / f"campaign.epoch-{target_epoch:03d}.json", signed)
    write_json_atomic(directory / "campaign.json", signed)
    attempt_lease.bind_epoch(epoch=target_epoch, context_hash=target_context.context_hash)
    checkpoint = {
        "schema": "leanmill.frontier_navigation_epoch_checkpoint.v1",
        "context_hash": target_context.context_hash,
        "context_epoch": target_epoch,
        "trace": [
            {
                "decision": "language_successor_admitted",
                "request_id": request.request_id,
                "admission_receipt_sha256": admission_receipt_sha256,
                "transition_receipt_sha256": transition["receipt_sha256"],
            }
        ],
        "provider_calls": 0,
        "typed_formula_proposal_sha256s": [],
    }
    write_json_atomic(directory / "navigation_epoch_checkpoint.json", checkpoint)
    calls = directory / "agent_calls" / "navigator"
    archived_calls = directory / "agent_calls" / f"navigator.epoch-{source_epoch:03d}"
    if calls.exists():
        if archived_calls.exists():
            raise ValueError("source language navigator archive already exists")
        os.replace(calls, archived_calls)
    consumption_core = {
        "schema": "leanmill.theory_language_successor_consumption.v1",
        "request_id": request.request_id,
        "source_context_hash": source_context.context_hash,
        "target_context_hash": target_context.context_hash,
        "source_epoch": source_epoch,
        "target_epoch": target_epoch,
        "source_blueprint_id": blueprint.blueprint_id,
        "target_blueprint_id": target_blueprint.blueprint_id,
        "admission_receipt_sha256": admission_receipt_sha256,
        "transition_receipt_sha256": transition["receipt_sha256"],
        "global_registry_mutated": False,
        "status": "successor_epoch_admitted",
    }
    consumption = {
        **consumption_core,
        "receipt_sha256": content_hash(consumption_core),
    }
    write_json_atomic(
        directory / f"theory_language_successor_consumption.epoch-{target_epoch:03d}.json",
        consumption,
    )
    consume_theory_language_compilation(
        directory,
        lowered,
        evidence_refs=(consumption["receipt_sha256"],),
    )
    from ztare.common.schema_routes import audit_project_schema_routes

    route_audit = next(
        row
        for row in audit_project_schema_routes(directory)["routes"]
        if row["route_id"] == "theory_language_compilation_outcome_totality.v1"
    )
    if route_audit["unconsumed_count"]:
        raise ValueError("language successor has an unconsumed compiler outcome")
    commit_core = {
        "schema": "leanmill.theory_language_successor_commit.v1",
        "status": "successor_epoch_admitted",
        "source_run_digest": str(run.get("run_digest") or ""),
        "source_epoch": source_epoch,
        "target_epoch": target_epoch,
        "target_context_hash": target_context.context_hash,
        "target_blueprint_id": target_blueprint.blueprint_id,
        "target_campaign_sha256": content_hash(signed),
        "consumption_receipt_sha256": consumption["receipt_sha256"],
        "compiler_outcomes_produced": route_audit["produced_count"],
        "compiler_outcomes_consumed": route_audit["consumed_count"],
    }
    commit = {**commit_core, "receipt_sha256": content_hash(commit_core)}
    write_json_atomic(
        directory / f"theory_language_successor_commit.epoch-{target_epoch:03d}.json",
        commit,
    )
    write_json_atomic(directory / "theory_language_successor_commit.json", commit)
    (directory / "replay.json").unlink(missing_ok=True)
    (directory / "run.json").unlink(missing_ok=True)
    if resume_fn is not None:
        resume_fn(directory, _attempt_lease=attempt_lease)
        (directory / "theory_language_successor_commit.json").unlink()
    return {
        "schema": "leanmill.theory_language_advancement.v1",
        "status": "successor_epoch_admitted",
        "attempt_dir": str(directory),
        "source_epoch": source_epoch,
        "target_epoch": target_epoch,
        "target_context_hash": target_context.context_hash,
        "consumption_receipt_sha256": consumption["receipt_sha256"],
        "commit_receipt_sha256": commit["receipt_sha256"],
    }


def _recover_language_successor_commit(
    directory: Path,
    *,
    resume_fn: Callable[..., Any] | None,
    attempt_lease: _FrontierAttemptLease,
) -> dict[str, Any] | None:
    """Finish a committed successor after interruption between commit and resume."""

    commit = read_json(directory / "theory_language_successor_commit.json", None)
    if not isinstance(commit, Mapping):
        return None
    core = {key: value for key, value in commit.items() if key != "receipt_sha256"}
    if (
        commit.get("schema") != "leanmill.theory_language_successor_commit.v1"
        or commit.get("receipt_sha256") != content_hash(core)
        or commit.get("status") != "successor_epoch_admitted"
    ):
        raise ValueError("language successor commit does not replay")
    target_epoch = int(commit["target_epoch"])
    from ztare.leanmill.finite_theory_context import load_formal_theory_context

    target_context = load_formal_theory_context(
        directory / f"formal_context.epoch-{target_epoch:03d}.json"
    )
    target_blueprint = FrontierTheoryBlueprint.from_json(
        read_json(directory / f"blueprint.epoch-{target_epoch:03d}.json", {})
    )
    target_campaign = read_json(
        directory / f"campaign.epoch-{target_epoch:03d}.json", {}
    )
    consumption = read_json(
        directory
        / f"theory_language_successor_consumption.epoch-{target_epoch:03d}.json",
        {},
    )
    consumption_core = {
        key: value for key, value in consumption.items() if key != "receipt_sha256"
    }
    if (
        target_context.context_hash != commit.get("target_context_hash")
        or target_blueprint.blueprint_id != commit.get("target_blueprint_id")
        or content_hash(target_campaign) != commit.get("target_campaign_sha256")
        or consumption.get("receipt_sha256") != content_hash(consumption_core)
        or consumption.get("receipt_sha256")
        != commit.get("consumption_receipt_sha256")
    ):
        raise ValueError("language successor commit views do not replay")
    active_run = read_json(directory / "run.json", None)
    if isinstance(active_run, Mapping):
        if active_run.get("context_hash") == target_context.context_hash:
            (directory / "theory_language_successor_commit.json").unlink()
            return {
                "schema": "leanmill.theory_language_advancement.v1",
                "status": "successor_epoch_already_resumed",
                "attempt_dir": str(directory),
                "target_epoch": target_epoch,
                "target_context_hash": target_context.context_hash,
                "commit_receipt_sha256": commit["receipt_sha256"],
            }
        if active_run.get("run_digest") != commit.get("source_run_digest"):
            raise ValueError("language successor commit conflicts with active run")
        (directory / "run.json").unlink()
    (directory / "replay.json").unlink(missing_ok=True)
    attempt_lease.bind_epoch(
        epoch=target_epoch, context_hash=target_context.context_hash
    )
    if resume_fn is not None:
        resume_fn(directory, _attempt_lease=attempt_lease)
        (directory / "theory_language_successor_commit.json").unlink()
    return {
        "schema": "leanmill.theory_language_advancement.v1",
        "status": "successor_epoch_admitted",
        "recovered": True,
        "attempt_dir": str(directory),
        "target_epoch": target_epoch,
        "target_context_hash": target_context.context_hash,
        "consumption_receipt_sha256": commit["consumption_receipt_sha256"],
        "commit_receipt_sha256": commit["receipt_sha256"],
    }


def advance_frontier_language_expansion(
    attempt_dir: str | Path,
    *,
    forge_fn: Callable[..., Mapping[str, Any]] | None = None,
    resume_fn: Callable[..., Any] | None = None,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> dict[str, Any]:
    """Advance request→compiler/gap→review→successor as one resumable state machine."""

    directory = Path(attempt_dir)
    if _attempt_lease is None:
        with frontier_attempt_lease(directory, action="advance_language") as lease:
            return advance_frontier_language_expansion(
                directory,
                forge_fn=forge_fn,
                resume_fn=resume_fn,
                _attempt_lease=lease,
            )
    recovered = _recover_language_successor_commit(
        directory,
        resume_fn=resume_fn,
        attempt_lease=_attempt_lease,
    )
    if recovered is not None:
        return recovered
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("language advancement requires an active run")
    _definition, blueprint, _budget, campaign, context = _load_campaign_attempt(directory)
    navigation = dict(run.get("navigation") or {})
    context_epoch = int(
        navigation.get(
            "context_epoch", (run.get("context_summary") or {}).get("context_epoch", 0)
        )
    )
    request = _language_request_from_run(run)
    if run.get("status") == "frontier_language_expansion_requested":
        lowered = lower_theory_language_request(
            request,
            context,
            blueprint,
            context_epoch=context_epoch,
            directory=directory,
            navigation=navigation,
        )
        if lowered["status"] == "compiled":
            transition = lowered["context_transition"]
            admission_core = {
                "schema": "leanmill.registered_language_compiler_admission.v1",
                "request_id": request.request_id,
                "source_context_hash": context.context_hash,
                "target_context_hash": lowered["context"].context_hash,
                "adapter_id": str(lowered["adapter_id"]),
                "transition_receipt_sha256": transition["receipt_sha256"],
                "evidence_binding_receipt_sha256": str(
                    lowered["evidence_binding"]["receipt_sha256"]
                ),
                "authority": "leanmill.theory_adapter_registry",
            }
            admission = {
                **admission_core,
                "receipt_sha256": content_hash(admission_core),
            }
            write_json_atomic(
                directory / "registered_language_compiler_admission.json", admission
            )
            return _admit_language_successor(
                directory,
                run=run,
                blueprint=blueprint,
                campaign=campaign,
                source_context=context,
                source_epoch=context_epoch,
                request=request,
                lowered=lowered,
                admission_receipt_sha256=admission["receipt_sha256"],
                admission_review={
                    "accepted": True,
                    "reviewer_ref": "leanmill.theory_adapter_registry",
                    "rationale": (
                        "The registered compiler produced a content-bound successor "
                        "chart from the frozen request and evidence receipts."
                    ),
                    "evidence_refs": [admission["receipt_sha256"]],
                    "binding_authority": "registered_adapter_language_compiler",
                },
                resume_fn=resume_fn,
                attempt_lease=_attempt_lease,
            )
        if lowered["status"] == "rejected":
            feedback = _language_outcome_feedback(
                directory,
                run,
                outcome="rejected",
                reason=str(lowered.get("reason") or "adapter_compiler_rejected"),
                evidence_refs=(str(lowered["evidence_binding"]["receipt_sha256"]),),
            )
            consume_theory_language_compilation(
                directory, lowered, evidence_refs=(feedback["receipt_sha256"],)
            )
            if resume_fn is not None:
                resume_fn(directory, _attempt_lease=_attempt_lease)
            return {
                "schema": "leanmill.theory_language_advancement.v1",
                "status": "rejected",
                "feedback_receipt_sha256": feedback["receipt_sha256"],
                "attempt_dir": str(directory),
            }
        if lowered["status"] != "adapter_gap":
            raise ValueError("language compiler outcome escaped its closed algebra")
        gap = lowered["adapter_gap"]
        write_json_atomic(directory / "adapter_gap.json", gap.to_json())
        navigation["adapter_gap"] = gap.to_json()
        run_core = {
            **{
                key: value
                for key, value in run.items()
                if key not in {"run_digest", "adapter_gap"}
            },
            "status": "blocked_adapter_gap",
            "navigation": navigation,
            "adapter_gap": gap.to_json(),
        }
        run = {**run_core, "run_digest": content_hash(run_core)}
        write_json_atomic(directory / "run.json", run)
        consume_theory_language_compilation(
            directory, lowered, evidence_refs=(gap.gap_id,)
        )
    elif run.get("status") != "blocked_adapter_gap":
        return {
            "schema": "leanmill.theory_language_advancement.v1",
            "status": "unavailable",
            "reason": "campaign_not_waiting_on_language_expansion",
            "attempt_dir": str(directory),
        }

    completion = read_json(directory / "adapter_forge_completion.json", None)
    if not isinstance(completion, Mapping):
        if forge_fn is None:
            return {
                "schema": "leanmill.theory_language_advancement.v1",
                "status": "adapter_forge_required",
                "gap_id": str((run.get("adapter_gap") or {}).get("gap_id") or ""),
                "attempt_dir": str(directory),
            }
        completion = forge_fn(directory, _attempt_lease=_attempt_lease)
    if not isinstance(completion, Mapping):
        raise ValueError("language advancement forge returned no typed outcome")
    if completion.get("status") in {
        "adapter_proposal_rejected_return_to_search",
        "frontier_objective_unmet",
        "unavailable",
    }:
        if read_json(directory / "run.json", {}).get("status") == "blocked_adapter_gap":
            reason = str(completion.get("reason") or completion.get("status") or "")
            _language_outcome_feedback(
                directory,
                run,
                outcome=(
                    "unavailable"
                    if completion.get("status") == "unavailable"
                    else "rejected"
                ),
                reason=reason,
                evidence_refs=tuple(
                    str(row) for row in completion.get("evidence_refs") or ()
                ),
            )
        if resume_fn is not None:
            resume_fn(directory, _attempt_lease=_attempt_lease)
        return {
            "schema": "leanmill.theory_language_advancement.v1",
            "status": str(completion.get("status") or "frontier_objective_unmet"),
            "attempt_dir": str(directory),
        }

    application, forge_receipt = _approved_functor_application(directory, completion)
    if application is None:
        feedback = _language_outcome_feedback(
            directory,
            run,
            outcome="unavailable",
            reason="reviewed_coordinate_has_no_automatic_successor_consumer",
            evidence_refs=(str(forge_receipt["receipt_sha256"]),),
        )
        if resume_fn is not None:
            resume_fn(directory, _attempt_lease=_attempt_lease)
        return {
            "schema": "leanmill.theory_language_advancement.v1",
            "status": "unavailable",
            "feedback_receipt_sha256": feedback["receipt_sha256"],
            "attempt_dir": str(directory),
        }
    lowered = lower_theory_language_request(
        request,
        context,
        blueprint,
        context_epoch=context_epoch,
        directory=directory,
        navigation=navigation,
        approved_application=application,
    )
    if lowered["status"] != "compiled":
        feedback = _language_outcome_feedback(
            directory,
            run,
            outcome=str(lowered["status"]),
            reason=str(lowered.get("reason") or "compiler did not admit successor"),
            evidence_refs=(str(forge_receipt["receipt_sha256"]),),
        )
        consume_theory_language_compilation(
            directory,
            lowered,
            evidence_refs=(feedback["receipt_sha256"],),
        )
        if resume_fn is not None:
            resume_fn(directory, _attempt_lease=_attempt_lease)
        return {
            "schema": "leanmill.theory_language_advancement.v1",
            "status": str(lowered["status"]),
            "feedback_receipt_sha256": feedback["receipt_sha256"],
            "attempt_dir": str(directory),
        }

    review = forge_receipt["independent_review"]
    return _admit_language_successor(
        directory,
        run=run,
        blueprint=blueprint,
        campaign=campaign,
        source_context=context,
        source_epoch=context_epoch,
        request=request,
        lowered=lowered,
        admission_receipt_sha256=str(forge_receipt["receipt_sha256"]),
        admission_review={
            **dict(review),
            "binding_authority": "campaign_local_functor_image",
        },
        resume_fn=resume_fn,
        attempt_lease=_attempt_lease,
    )


_BOUNDARY_FAILURE_STATUSES = {
    "inadmissible_logical_product_coordinate",
    "refuted_in_seed_context",
    "refuted_by_replayed_countermodel",
    "source_known_single_premise_consequence",
    "refuted_by_larger_model",
    "refuted_by_kernel",
}


def _consume_theory_task_discharge(
    directory: Path,
    run: Mapping[str, Any],
    completion: Mapping[str, Any],
) -> dict[str, Any]:
    """Consume the adapter's closed task outcome algebra into campaign state."""

    from ztare.common.schema_routes import append_consequence_event
    from ztare.common.task_discharge import bind_task_discharge_receipt
    from ztare.leanmill.theory_program import TheoryProgram

    boundary = completion.get("boundary_result")
    if not isinstance(boundary, Mapping):
        raise ValueError("theory-task discharge requires its boundary result")
    boundary_core = {
        key: value for key, value in boundary.items() if key != "result_sha256"
    }
    boundary_ref = str(boundary.get("result_sha256") or "")
    if not boundary_ref or boundary_ref != content_hash(boundary_core):
        raise ValueError("theory-task discharge boundary changed identity")
    bundle = completion.get("theory_task_discharge")
    if not isinstance(bundle, Mapping):
        return dict(run)
    bundle_core = {
        key: value for key, value in bundle.items() if key != "receipt_sha256"
    }
    bundle_ref = str(bundle.get("receipt_sha256") or "")
    if (
        bundle.get("schema") != "leanmill.theory_task_discharge.v1"
        or not bundle_ref
        or bundle_ref != content_hash(bundle_core)
        or bundle.get("boundary_result_sha256") != boundary_ref
    ):
        raise ValueError("theory-task discharge bundle does not replay")

    navigation = dict(run.get("navigation") or {})
    expected: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
    for finalist in navigation.get("finalists") or ():
        if not isinstance(finalist, Mapping) or not isinstance(
            finalist.get("theory_program"), Mapping
        ):
            continue
        program = TheoryProgram.from_json(finalist["theory_program"])
        if finalist.get("theory_program_id") not in {None, program.program_id}:
            raise ValueError("frozen finalist changed its theory-program identity")
        explicit_hashes = {
            contract.sha256 for contract in program.task_discharge_contracts
        }
        for contract in program.executable_task_contracts():
            key = (program.program_id, contract.sha256)
            if key in expected:
                raise ValueError("frozen theory programs duplicate a task identity")
            expected[key] = (
                "explicit_task"
                if contract.sha256 in explicit_hashes
                else "legacy_prediction",
                contract.to_dict(),
            )

    explicit: dict[str, list[str]] = {}
    verified_rows: list[dict[str, Any]] = []
    observed: set[tuple[str, str]] = set()
    for raw in bundle.get("rows") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("theory-task discharge row is malformed")
        row_core = {key: value for key, value in raw.items() if key != "receipt_sha256"}
        if raw.get("receipt_sha256") != content_hash(row_core):
            raise ValueError("theory-task discharge row digest mismatch")
        contract, receipt = bind_task_discharge_receipt(
            raw.get("contract") or {}, raw.get("receipt") or {}
        )
        if (
            raw.get("contract_sha256") != contract.sha256
            or raw.get("source") not in {"legacy_prediction", "explicit_task"}
        ):
            raise ValueError("theory-task discharge row changed identity")
        program_id = str(raw.get("program_id") or "")
        if not program_id:
            raise ValueError("theory-task discharge row lacks its program")
        key = (program_id, contract.sha256)
        expected_row = expected.get(key)
        if (
            expected_row is None
            or key in observed
            or raw.get("source") != expected_row[0]
            or contract.to_dict() != expected_row[1]
        ):
            raise ValueError("theory-task discharge row is not a frozen program output")
        observed.add(key)
        if raw.get("source") == "explicit_task":
            explicit.setdefault(program_id, []).append(receipt.status)
        verified_rows.append(dict(raw))
    if observed != set(expected):
        raise ValueError("theory-task discharge did not cover every frozen program output")

    outcomes = {
        program_id: (
            "discharged"
            if all(status == "discharged" for status in statuses)
            else "unavailable"
            if any(status == "unavailable" for status in statuses)
            else "open"
        )
        for program_id, statuses in explicit.items()
    }
    declared = list(outcomes.values())
    program_status = (
        "not_declared"
        if not declared
        else "discharged"
        if "discharged" in declared
        else "unavailable"
        if all(status == "unavailable" for status in declared)
        else "open"
    )
    supplied_outcomes = {
        key: value
        for key, value in dict(bundle.get("program_outcomes") or {}).items()
        if value != "not_declared"
    }
    if (
        outcomes != supplied_outcomes
        or program_status != bundle.get("explicit_program_status")
    ):
        raise ValueError("theory-task aggregate does not follow its task receipts")

    synthesis = navigation.get("lineage_synthesis")
    objective_contract = (
        synthesis.get("objective_contract")
        if isinstance(synthesis, Mapping)
        and synthesis.get("route") == "proceed_boundary"
        else None
    )
    authorized_ids = {
        str(value) for value in synthesis.get("program_ids") or ()
    } if isinstance(objective_contract, Mapping) else set()
    authorized_outcomes = [
        status for program_id, status in outcomes.items()
        if program_id in authorized_ids
    ]
    objective_status = (
        "not_declared"
        if not isinstance(objective_contract, Mapping)
        else "not_typed"
        if not authorized_outcomes
        else "discharged"
        if "discharged" in authorized_outcomes
        else "unavailable"
        if all(status == "unavailable" for status in authorized_outcomes)
        else "open"
    )

    consumption_core = {
        "schema": "leanmill.theory_task_discharge_consumption.v1",
        "bundle_receipt_sha256": bundle_ref,
        "explicit_program_status": program_status,
        "objective_status": objective_status,
        "objective_contract": (
            dict(objective_contract)
            if isinstance(objective_contract, Mapping)
            else None
        ),
        "authorized_program_ids": sorted(authorized_ids),
        "consumed_task_count": len(verified_rows),
        "authority": "frontier_campaign_state_machine",
    }
    consumption = {
        **consumption_core,
        "receipt_sha256": content_hash(consumption_core),
    }
    consumption_path = directory / "theory_task_discharge_consumption.json"
    prior_consumption = read_json(consumption_path, None)
    if isinstance(prior_consumption, Mapping):
        if dict(prior_consumption) != consumption:
            raise ValueError("theory-task consumption changed after first fire")
    else:
        for row in verified_rows:
            append_consequence_event(
                directory,
                contract_id="theory_program_task_outcome_totality.v1",
                subject_id=f"{row['program_id']}:{row['contract_sha256']}",
                outcome=str((row["receipt"] or {}).get("status") or ""),
                event="consumed",
                evidence_refs=(str(row["receipt_sha256"]), bundle_ref),
            )
        write_json_atomic(consumption_path, consumption)

    # A proved finite witness carries an unbounded residual by declaration,
    # even when its fresh adjudicator is unavailable.  Project that scope at
    # consumption time so the terminal gate cannot pass by seeing an empty
    # residual list.  Only a discharged campaign-owned counterexample task may
    # mint the matching refutation adjudication.
    from ztare.leanmill.campaign_closure_gate import (
        build_generalization_residual_receipt,
        generalization_adjudication_from_task_discharge,
    )
    from ztare.leanmill.formal_task_boundary import formal_task_parameters

    objective_programs: dict[str, TheoryProgram] = {}
    for candidate in _objective_candidate_lineages(navigation):
        representative = candidate.get("representative") or {}
        program_row = representative.get("theory_program")
        if isinstance(program_row, Mapping):
            program = TheoryProgram.from_json(program_row)
            objective_programs[program.program_id] = program

    for row in verified_rows:
        if row.get("source") != "explicit_task":
            continue
        contract, task_receipt = bind_task_discharge_receipt(
            row.get("contract") or {}, row.get("receipt") or {}
        )
        try:
            task_parameters = formal_task_parameters(contract)
        except (KeyError, TypeError, ValueError):
            continue
        declared_residual = task_parameters.get("generalization_residual")
        if not isinstance(declared_residual, Mapping):
            continue
        residual = build_generalization_residual_receipt(
            context_hash=str(task_parameters["context_hash"]),
            lineage_id=str(contract.owner),
            witness_id=str(declared_residual["witness_id"]),
            claim_id=str(declared_residual["claim_id"]),
            evidence_refs=tuple(
                str(value) for value in declared_residual["evidence_refs"]
            )
            + (contract.sha256,),
        )
        _persist_terminal_obligation_receipt(
            directory,
            prefix="generalization_residual",
            identity=str(residual["residual_id"]),
            receipt=residual,
        )
        if task_receipt.status != "discharged":
            continue
        program = objective_programs.get(str(row.get("program_id") or ""))
        if program is None:
            raise ValueError("formal residual discharge lacks its frozen program")
        adjudication = generalization_adjudication_from_task_discharge(
            residual,
            theory_program=program.to_json(),
            discharge_bundle=bundle,
            discharge_consumption=consumption,
            boundary_result=boundary,
        )
        _persist_terminal_obligation_receipt(
            directory,
            prefix="generalization_adjudication",
            identity=str(residual["residual_id"]),
            receipt=adjudication,
        )
    navigation["theory_task_discharge"] = consumption
    run_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "status": (
            "frontier_objective_discharged"
            if objective_status == "discharged"
            else str(run.get("status") or "")
        ),
        "navigation": navigation,
    }
    updated = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(directory / "run.json", updated)
    if objective_status == "discharged":
        from ztare.leanmill.campaign_closure_gate import (
            lineage_disposition_from_task_discharge,
        )

        for candidate in _objective_candidate_lineages(navigation):
            representative = candidate.get("representative") or {}
            program_row = representative.get("theory_program")
            if not isinstance(program_row, Mapping):
                continue
            program = TheoryProgram.from_json(program_row)
            if (
                program.program_id not in authorized_ids
                or outcomes.get(program.program_id) != "discharged"
            ):
                continue
            disposition = lineage_disposition_from_task_discharge(
                theory_program=program.to_json(),
                discharge_bundle=bundle,
                discharge_consumption=consumption,
                boundary_result=boundary,
            )
            _persist_terminal_obligation_receipt(
                directory,
                prefix="lineage_disposition",
                identity=str(disposition["lineage_id"]),
                receipt=disposition,
            )
    return updated


def _restore_durable_search_transition(
    directory: Path, run: Any
) -> dict[str, Any] | Any:
    """Project durable search events over stale or contradictory run materialization."""

    paths = sorted(directory.glob("adapter_rejection_feedback.wave-*.json"))
    if not isinstance(run, Mapping):
        return run
    navigation = dict(run.get("navigation") or {})
    adapter_rejected = (
        run.get("status") == "blocked_adapter_gap"
        and not (directory / "adapter_gap.json").is_file()
        and bool(paths)
    )
    sieve_pending_without_receipt = (
        run.get("status") == "frontier_leaf_decision_pending"
        and not isinstance(navigation.get("pending_leaf_decision"), Mapping)
        and int(
            (navigation.get("compound_implication_sieve") or {}).get(
                "survivor_count", 0
            )
        ) > 0
    )
    if not adapter_rejected and not sieve_pending_without_receipt:
        return run
    if adapter_rejected:
        feedback = read_json(paths[-1], {})
        if feedback.get("context_hash") != run.get("context_hash"):
            raise ValueError("adapter rejection transition crossed contexts")
        history = [
            row
            for row in navigation.get("objective_review_history") or ()
            if isinstance(row, Mapping)
        ]
        if not any(
            row.get("receipt_sha256") == feedback.get("receipt_sha256")
            for row in history
        ):
            history.append(feedback)
        navigation["objective_review_history"] = history
        for stale in (
            "adapter_gap",
            "language_expansion_request",
            "theory_language_expansion_requests",
            "lineage_synthesis",
        ):
            navigation.pop(stale, None)
    core = {
        **{key: value for key, value in run.items() if key not in {"run_digest", "adapter_gap"}},
        "status": "frontier_objective_unmet",
        "navigation": navigation,
        "adapter_gap": None,
    }
    restored = {**core, "run_digest": content_hash(core)}
    write_json_atomic(directory / "run.json", restored)
    return restored


def _candidate_matches_context(
    candidate: Mapping[str, Any],
    *,
    context_hash: str,
    context_epoch: int,
) -> bool:
    """Check explicit candidate/program ownership without guessing legacy identity."""

    bindings: list[tuple[str, int]] = []
    row_hash = str(candidate.get("context_hash") or "")
    row_epoch = candidate.get("context_epoch")
    if row_hash and type(row_epoch) is int:
        bindings.append((row_hash, row_epoch))
    program_row = candidate.get("theory_program")
    if isinstance(program_row, Mapping):
        try:
            program = TheoryProgram.from_json(program_row)
        except (TypeError, ValueError):
            return False
        bindings.append((program.context_hash, program.context_epoch))
    # Historical compact finalists may lack an explicit binding.  Their
    # existing deterministic replay remains the compatibility gate.
    return not bindings or all(
        bound_hash == context_hash and bound_epoch == context_epoch
        for bound_hash, bound_epoch in bindings
    )


def _archive_cross_context_active_candidates(
    directory: Path,
    run: Any,
) -> dict[str, Any] | Any:
    """Demote source-epoch candidates before any target-epoch boundary action."""

    if not isinstance(run, Mapping) or not isinstance(run.get("navigation"), Mapping):
        return run
    context_hash = str(run.get("context_hash") or "")
    navigation = dict(run["navigation"])
    context_epoch = int(
        navigation.get(
            "context_epoch",
            (run.get("context_summary") or {}).get("context_epoch", 0),
        )
    )
    archived: list[dict[str, Any]] = []
    for field in ("finalists", "objective_survivors"):
        rows = navigation.get(field)
        if not isinstance(rows, (list, tuple)):
            continue
        current: list[dict[str, Any]] = []
        for raw in rows:
            if not isinstance(raw, Mapping):
                continue
            row = dict(raw)
            if _candidate_matches_context(
                row,
                context_hash=context_hash,
                context_epoch=context_epoch,
            ):
                current.append(row)
                continue
            program_row = row.get("theory_program")
            source_hash = str(row.get("context_hash") or "")
            source_epoch = row.get("context_epoch")
            if isinstance(program_row, Mapping):
                try:
                    source_program = TheoryProgram.from_json(program_row)
                except (TypeError, ValueError):
                    source_program = None
                if source_program is not None:
                    source_hash = source_hash or source_program.context_hash
                    if type(source_epoch) is not int:
                        source_epoch = source_program.context_epoch
            archived.append(
                {
                    "collection": field,
                    "node_id": str(row.get("node_id") or ""),
                    "theory_program_id": str(row.get("theory_program_id") or ""),
                    "source_context_hash": source_hash,
                    "source_context_epoch": source_epoch,
                }
            )
        navigation[field] = current
    if not archived:
        return run
    archive_core = {
        "schema": "leanmill.cross_context_candidate_archive.v1",
        "status": "archived_source_epoch_only",
        "target_context_hash": context_hash,
        "target_context_epoch": context_epoch,
        "archived_candidates": archived,
        "route": "continue_search",
        "authority": "host_context_identity_transition",
    }
    archive = {**archive_core, "receipt_sha256": content_hash(archive_core)}
    archive_path = directory / (
        f"cross_context_candidate_archive.epoch-{context_epoch:03d}.json"
    )
    prior = read_json(archive_path, None)
    if isinstance(prior, Mapping) and dict(prior) != archive:
        raise ValueError("cross-context candidate archive changed identity")
    if not isinstance(prior, Mapping):
        write_json_atomic(archive_path, archive)
    history = [
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
    ]
    if not any(
        row.get("receipt_sha256") == archive["receipt_sha256"] for row in history
    ):
        history.append(archive)
    navigation["objective_review_history"] = history
    navigation.pop("lineage_synthesis", None)
    run_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "status": "frontier_objective_unmet",
        "navigation": navigation,
    }
    updated = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(directory / "run.json", updated)
    return updated


def execute_frontier_compound_sieve(
    attempt_dir: str | Path,
    *,
    max_queries: int = 0,
    stratum_index: int = 0,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> dict[str, Any]:
    """Apply each larger-model witness to the whole compound survivor pool."""

    directory = Path(attempt_dir)
    if max_queries < 0 or stratum_index < 0:
        raise ValueError("compound sieve bounds must be nonnegative")
    if _attempt_lease is None:
        with frontier_attempt_lease(directory, action="compound_implication_sieve") as lease:
            return execute_frontier_compound_sieve(
                directory,
                max_queries=max_queries,
                stratum_index=stratum_index,
                _attempt_lease=lease,
            )
    _definition, blueprint, budget_row, _campaign, context = _load_campaign_attempt(
        directory
    )
    run = read_json(directory / "run.json", {})
    if run.get("status") != "frontier_objective_unmet":
        raise ValueError("compound sieve requires an unresolved search wave")

    from ztare.leanmill.compound_implication_sieve import (
        enumerate_compound_implications,
        run_compound_implication_sieve,
    )
    from ztare.leanmill.finite_model import FiniteModel
    from ztare.leanmill.frontier_boundary import larger_model_strata
    from ztare.leanmill.theory_adapter_registry import (
        materialize_theory_adapter_capability,
    )

    strata = larger_model_strata(context.signature, blueprint.verification_plan)
    if stratum_index >= len(strata):
        raise ValueError("compound sieve stratum is outside the verification plan")
    sort_sizes = dict(strata[stratum_index])
    state_path = directory / f"compound_implication_sieve.stratum-{stratum_index:02d}.json"
    prior = read_json(state_path, None)
    candidate_ids = None
    if stratum_index:
        predecessor = read_json(
            directory
            / f"compound_implication_sieve.stratum-{stratum_index - 1:02d}.json",
            {},
        )
        candidate_ids = tuple(predecessor.get("fixed_size_survivor_ids") or ())
        if not candidate_ids:
            raise ValueError("no fixed-size survivors earned the next stratum")

    seeds: dict[str, FiniteModel] = {}
    seed_refs: dict[str, str] = {}
    receipts_by_witness: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("boundary_result*.json")):
        boundary = read_json(path, {})
        for row in boundary.get("query_results") or ():
            if not isinstance(row, Mapping):
                continue
            for receipt in row.get("countermodel_searches") or ():
                if (
                    not isinstance(receipt, Mapping)
                    or receipt.get("status") != "countermodel_found"
                    or dict(receipt.get("sort_sizes") or {}) != sort_sizes
                    or not isinstance(receipt.get("witness"), Mapping)
                ):
                    continue
                receipt_core = {
                    key: value
                    for key, value in receipt.items()
                    if key != "receipt_sha256"
                }
                if receipt.get("receipt_sha256") != content_hash(receipt_core):
                    raise ValueError("archived boundary countermodel digest mismatch")
                model = FiniteModel.from_json(receipt["witness"])
                witness_id = content_hash(model.to_json())
                seeds[witness_id] = model
                seed_refs[witness_id] = str(receipt["receipt_sha256"])
                receipts_by_witness[witness_id] = dict(receipt)

    budget = ExplorationBudget.from_json(budget_row)
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl", budget, attempt_id=directory.name
    )
    ledger.recover_interrupted_wall_clock()
    ledger.recover_interrupted_reservations()
    ledger.resume_wall_clock()
    timeout_ms = int(blueprint.verification_plan.get("smt_timeout_ms", 30_000))
    representation_search = isinstance(
        blueprint.adapter_config.get("generative_representation"), Mapping
    )
    capacities = [
        max_queries,
        ledger.remaining_capacity("boundary", "boundary_queries"),
    ]
    if not representation_search:
        capacities.extend(
            (
                ledger.remaining_capacity("boundary", "smt_calls"),
                ledger.remaining_capacity("boundary", "smt_millis") // timeout_ms,
            )
        )
    available_queries = min(capacities)
    finder = materialize_theory_adapter_capability(
        blueprint.adapter_id,
        "fixed_size_countermodel_finder",
        signature=context.signature,
        adapter_config=blueprint.adapter_config,
    )
    query_index = 0

    def budgeted_countermodel(
        signature: Any, premises: Any, target: Any, **kwargs: Any
    ) -> Any:
        nonlocal query_index
        if signature.content_hash != context.signature.content_hash:
            raise ValueError("compound sieve query crossed signatures")
        query_index += 1
        resources = {"boundary_queries": 1}
        if not representation_search:
            resources.update({"smt_calls": 1, "smt_millis": timeout_ms})
        reservation = ledger.reserve(
            f"compound-sieve:{stratum_index}:{query_index}",
            "boundary",
            resources,
        )
        try:
            receipt = finder(premises, target, **kwargs)
        except Exception:
            ledger.release(reservation, reason="compound_sieve_query_failed")
            raise
        ledger.commit(reservation)
        receipt_json = receipt.to_json()
        if isinstance(receipt_json.get("witness"), Mapping):
            witness = FiniteModel.from_json(receipt_json["witness"])
            receipts_by_witness[content_hash(witness.to_json())] = receipt_json
        return receipt

    prior_eliminated = len((prior or {}).get("eliminated_candidate_ids") or ())
    prior_effects = len((prior or {}).get("witness_effects") or ())
    prior_queries = len((prior or {}).get("query_receipts") or ())
    try:
        result = run_compound_implication_sieve(
            context,
            sort_sizes=sort_sizes,
            max_solver_queries=available_queries,
            timeout_ms=timeout_ms,
            maximum_presentation_size=min(2, blueprint.pack_arity),
            candidate_ids=candidate_ids,
            seed_witnesses=tuple(seeds.values()),
            prior_state=prior,
            countermodel_fn=budgeted_countermodel,
        )
        from ztare.leanmill.theory_conflict_ledger import (
            finite_countermodel_conflict_receipt,
            open_theory_conflict_ledger,
        )

        candidates = {
            row.candidate_id: row
            for row in enumerate_compound_implications(
                context,
                maximum_presentation_size=min(2, blueprint.pack_arity),
            )
        }
        conflict_ledger = open_theory_conflict_ledger(
            context, directory.parent / "theory_conflicts.jsonl"
        )
        conflict_count_before = len(conflict_ledger.open_clauses())
        for effect in result["witness_effects"]:
            receipt = receipts_by_witness.get(str(effect.get("witness_sha256") or ""))
            if receipt is None:
                continue
            for candidate_id in effect.get("refuted_candidate_ids") or ():
                candidate = candidates.get(str(candidate_id))
                if candidate is None:
                    raise ValueError("compound sieve effect names an unknown implication")
                conflict_ledger.learn(
                    finite_countermodel_conflict_receipt(
                        context,
                        candidate.premise_formula_ids,
                        candidate.target_formula_id,
                        receipt,
                    )
                )
        conflicts_learned = (
            len(conflict_ledger.open_clauses()) - conflict_count_before
        )
        write_json_atomic(state_path, result)
        eliminated_now = len(result["eliminated_candidate_ids"]) - prior_eliminated
        ledger.observe_information(
            action_id=f"compound-sieve:{stratum_index}",
            marginal_information_per_cost_ppm=min(
                1_000_000,
                eliminated_now * 1_000_000 // max(1, result["candidate_count"]),
            ),
            coverage_ppm=(
                len(result["eliminated_candidate_ids"])
                * 1_000_000
                // max(1, result["candidate_count"])
            ),
            evidence_refs=(str(result["receipt_sha256"]),),
        )
    finally:
        ledger.freeze_wall_clock(reason="compound_implication_sieve_exit")

    feedback_core = {
        "schema": "leanmill.compound_implication_sieve_feedback.v1",
        "context_hash": context.context_hash,
        "stratum_index": stratum_index,
        "sort_sizes": sort_sizes,
        "sieve_receipt": result["receipt_sha256"],
        "candidate_count": result["candidate_count"],
        "eliminated_count": len(result["eliminated_candidate_ids"]),
        "survivor_count": len(result["surviving_candidate_ids"]),
        "queries_used_this_call": result["queries_used_this_call"],
        "witnesses_added_this_call": len(result["witness_effects"]) - prior_effects,
        "conflicts_learned_this_call": conflicts_learned,
        "next_query_frontier": result["next_query_frontier"],
        "selection_policy": result["selection_policy"],
        "claim_boundary": result["claim_boundary"],
        "route": "continue_search",
        "authority": "host_batch_cegis",
    }
    feedback = {**feedback_core, "receipt_sha256": content_hash(feedback_core)}
    navigation = dict(run.get("navigation") or {})
    history = [
        row
        for row in navigation.get("objective_review_history") or ()
        if not (
            isinstance(row, Mapping)
            and row.get("schema") == feedback["schema"]
            and row.get("stratum_index") == stratum_index
        )
    ]
    history.append(feedback)
    navigation["objective_review_history"] = history
    navigation["compound_implication_sieve"] = feedback
    run_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "navigation": navigation,
    }
    write_json_atomic(
        directory / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    completion_core = {
        "schema": "leanmill.compound_implication_sieve_completion.v1",
        "status": result["status"],
        "attempt_dir": str(directory),
        "state_ref": state_path.name,
        "sieve_receipt": result["receipt_sha256"],
        "feedback_receipt": feedback["receipt_sha256"],
        "seed_witness_receipts": [seed_refs[key] for key in sorted(seed_refs)],
        "candidate_count": result["candidate_count"],
        "eliminated_count": len(result["eliminated_candidate_ids"]),
        "new_eliminated_count": (
            len(result["eliminated_candidate_ids"]) - prior_eliminated
        ),
        "conflicts_learned": conflicts_learned,
        "survivor_count": len(result["surviving_candidate_ids"]),
        "fixed_size_survivor_count": len(result["fixed_size_survivor_ids"]),
        "vacuous_count": len(result["vacuous_candidate_ids"]),
        "unknown_count": len(result["unknown_candidate_ids"]),
        "query_status_counts": {},
        "queries_requested": max_queries,
        "queries_admitted": available_queries,
        "queries_used": result["queries_used_this_call"],
    }
    for row in result["query_receipts"][prior_queries:]:
        status = str((row.get("search") or {}).get("status") or "unknown")
        completion_core["query_status_counts"][status] = (
            completion_core["query_status_counts"].get(status, 0) + 1
        )
    completion = {
        **completion_core,
        "completion_sha256": content_hash(completion_core),
    }
    write_json_atomic(
        directory / f"compound_implication_sieve_completion.stratum-{stratum_index:02d}.json",
        completion,
    )
    return completion


def _boundary_search_feedback(
    run: Any, completion: Any
) -> dict[str, Any] | None:
    """Return compact boundary evidence owed to the next objective review."""

    if not isinstance(run, Mapping) or not isinstance(completion, Mapping):
        return None
    boundary = completion.get("boundary_result")
    rows = boundary.get("query_results") if isinstance(boundary, Mapping) else None
    if (
        isinstance(boundary, Mapping)
        and str(boundary.get("stop_reason") or "").startswith(
            "blocked_before_action"
        )
    ):
        return None
    navigation = run.get("navigation") or {}
    synthesis = navigation.get("lineage_synthesis") or {}
    objective_contract = (
        synthesis.get("objective_contract")
        if isinstance(synthesis, Mapping)
        else None
    )
    task_discharge = completion.get("theory_task_discharge")
    task_consumption = navigation.get("theory_task_discharge")
    objective_task_status = str(
        task_consumption.get("objective_status") or "not_declared"
    ) if isinstance(task_consumption, Mapping) else "not_declared"
    typed_task_pending = objective_task_status in {"open", "unavailable"}
    has_theory_rows = any(
        isinstance(row, Mapping) and row.get("candidate_kind") == "theory_program"
        for row in rows or ()
    )
    failed = any(
        isinstance(row, Mapping)
        and row.get("candidate_kind") == "theory_program"
        and row.get("program_prediction_status") in _BOUNDARY_FAILURE_STATUSES
        for row in rows or ()
    )
    if (
        run.get("status") != "frontier_candidates_frozen_awaiting_boundary_approval"
        or not isinstance(rows, list)
        or (not has_theory_rows and not typed_task_pending)
        or (
            not failed
            and not typed_task_pending
            and not isinstance(objective_contract, Mapping)
        )
    ):
        return None

    def evidence_refs(row: Mapping[str, Any]) -> list[str]:
        refs = [
            str(receipt.get("receipt_sha256") or "")
            for receipt in row.get("countermodel_searches") or ()
            if isinstance(receipt, Mapping) and receipt.get("receipt_sha256")
        ]
        for envelope, child in (
            (row.get("raw_boundary"), None),
            (row.get("lean"), "governed_attempt"),
            (row.get("isabelle"), "attempt"),
        ):
            if not isinstance(envelope, Mapping):
                continue
            receipt = envelope.get(child) if child is not None else envelope
            if isinstance(receipt, Mapping) and receipt.get("receipt_sha256"):
                refs.append(str(receipt["receipt_sha256"]))
        return [value for value in dict.fromkeys(refs) if value]

    program_bindings: dict[tuple[tuple[str, ...], str], set[str]] = {}
    for finalist in navigation.get("finalists") or ():
        if not isinstance(finalist, Mapping):
            continue
        premises = tuple(str(value) for value in finalist.get("formula_ids") or ())
        program_id = str(finalist.get("theory_program_id") or "")
        for target in finalist.get("boundary_target_ids") or ():
            program_bindings.setdefault((premises, str(target)), set()).add(program_id)

    prediction_outcomes = []
    observed: set[tuple[tuple[str, ...], str]] = set()
    for row in rows:
        if not isinstance(row, Mapping) or row.get("candidate_kind") != "theory_program":
            continue
        premises = tuple(str(value) for value in row.get("premise_formula_ids") or ())
        target = str(row.get("target_formula_id") or "")
        key = (premises, target)
        observed.add(key)
        prediction_outcomes.append({
            "premise_formula_ids": list(row.get("premise_formula_ids") or ()),
            "target_formula_id": target,
            "status": str(row.get("program_prediction_status") or ""),
            "program_ids": sorted(value for value in program_bindings.get(key, ()) if value),
            "evidence_refs": evidence_refs(row),
        })
        batch = row.get("countermodel_batch_replay")
        if not isinstance(batch, Mapping):
            continue
        witness_ref = str(batch.get("witness_ref") or "")
        for batch_target in batch.get("refuted_target_formula_ids") or ():
            batch_key = (premises, str(batch_target))
            if batch_key in observed:
                continue
            observed.add(batch_key)
            prediction_outcomes.append({
                "premise_formula_ids": list(premises),
                "target_formula_id": str(batch_target),
                "status": "refuted_by_larger_model",
                "program_ids": sorted(
                    value for value in program_bindings.get(batch_key, ()) if value
                ),
                "evidence_refs": [witness_ref] if witness_ref else [],
            })
    for (premises, target), program_ids in sorted(program_bindings.items()):
        if (premises, target) not in observed:
            prediction_outcomes.append({
                "premise_formula_ids": list(premises),
                "target_formula_id": target,
                "status": "not_tested_after_program_refutation",
                "program_ids": sorted(value for value in program_ids if value),
                "evidence_refs": [],
            })
    failures = [
        row for row in prediction_outcomes
        if row["status"] in _BOUNDARY_FAILURE_STATUSES
    ]
    core = {
        "schema": "leanmill.boundary_search_feedback.v1",
        "context_hash": str(run.get("context_hash") or ""),
        "context_epoch": int(
            navigation.get(
                "context_epoch",
                (run.get("context_summary") or {}).get("context_epoch", 0),
            )
        ),
        "source_run_digest": str(run.get("run_digest") or ""),
        "boundary_result_sha256": str(boundary.get("result_sha256") or ""),
        "program_ids": [
            str(row.get("theory_program_id") or "")
            for row in navigation.get("finalists") or ()
            if isinstance(row, Mapping) and row.get("theory_program_id")
        ],
        "prediction_outcomes": prediction_outcomes,
        "failed_predictions": failures,
        "objective_contract": (
            dict(objective_contract)
            if isinstance(objective_contract, Mapping)
            else None
        ),
        "theory_task_discharge": (
            dict(task_discharge) if typed_task_pending else None
        ),
        "nonfailed_predictions": [
            row for row in prediction_outcomes
            if row["status"] not in _BOUNDARY_FAILURE_STATUSES
        ],
        "route": "continue_search",
        "next_discriminator": (
            "Escalate to a registered task adjudicator or revise the authored "
            "experiment without changing its stopping identity."
            if objective_task_status == "unavailable"
            else
            "Preserve discharged task coordinates while changing the open "
            "construction, classification, or obstruction experiment."
            if objective_task_status == "open"
            else
            "Preserve nonfailed predictions while using replayed boundary "
            "countermodels to change the candidate theory or representation."
            if failures
            else
            "Treat boundary survival as evidence, then test whether the program "
            "discharges the outer representation, classification, or construction "
            "objective; otherwise change representation or stop unresolved."
        ),
        "kill_condition": (
            "Do not treat an unavailable adjudicator as a negative scientific result."
            if objective_task_status == "unavailable"
            else
            "Do not renominate an implication whose witnessed conflict replays."
            if failures
            else
            "Do not equate formal survival of a consequence with discharge of the "
            "outer campaign objective."
        ),
        "authority": "host_boundary_outcome_replay",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _active_objective_finalists(
    navigation: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Project boundary-surviving programs from the existing campaign record.

    Search waves are observations, not candidate identities.  A frozen program
    therefore remains available after a wave boundary until witnessed feedback
    refutes one of its advertised predictions.  The journal/run snapshots stay
    the durable store; this function is only their active read model.
    """

    candidates = _objective_candidate_lineages(navigation)
    if not candidates:
        return ()
    feedback_rows = tuple(
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
        and row.get("schema")
        in {
            "leanmill.boundary_search_feedback.v1",
            "leanmill.post_freeze_mechanism_feedback.v1",
            "leanmill.post_freeze_research_disposition.v1",
            "leanmill.terminal_obligation_feedback.v1",
        }
    )
    active: list[dict[str, Any]] = []
    for candidate in candidates:
        finalist = dict(candidate["representative"])
        program_id = str(candidate["program_id"])
        lineage_id = str(candidate["lineage_id"])
        program_aliases = set(candidate["program_ids"])

        def binds(row: Mapping[str, Any]) -> bool:
            schema = str(row.get("schema") or "")
            row_program_ids = {
                str(value) for value in row.get("program_ids") or ()
            }
            if schema == "leanmill.boundary_search_feedback.v1":
                return bool(program_aliases & row_program_ids)
            if "lineage_ids" in row:
                row_lineage_ids = row.get("lineage_ids")
                if not isinstance(row_lineage_ids, (list, tuple)):
                    return False
                return bool(lineage_id) and lineage_id in {
                    str(value) for value in row_lineage_ids
                }
            # Historical v1 post-freeze receipts predate lineage binding.  They
            # replay only against the exact representative program they named;
            # they cannot migrate to a refined program by inference.
            return program_id in row_program_ids

        feedback = next(
            (
                row
                for row in reversed(feedback_rows)
                if binds(row)
            ),
            None,
        )
        if feedback is None:
            continue
        failed = (
            feedback.get("schema") == "leanmill.boundary_search_feedback.v1"
            and any(
                bool(
                    program_aliases
                    & {
                        str(value)
                        for value in row.get("program_ids") or ()
                    }
                )
                and str(row.get("status") or "")
                in _BOUNDARY_FAILURE_STATUSES
                for row in feedback.get("prediction_outcomes") or ()
                if isinstance(row, Mapping)
            )
        )
        if failed:
            continue
        finalist["objective_feedback"] = dict(feedback)
        active.append(finalist)
    return tuple(active)


def _objective_candidate_lineages(
    navigation: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Read current candidate representatives at the lineage identity boundary.

    A program may change after an objective wave while its lineage remains the
    same.  Frozen finalists establish the identity history; later provisional
    survivors replace only the current representative of that same lineage.
    Rows without a parseable lineage retain exact-program compatibility for
    historical campaign records.
    """

    records: dict[tuple[str, str], dict[str, Any]] = {}
    for field in ("finalists", "objective_survivors"):
        rows = navigation.get(field)
        if not isinstance(rows, (list, tuple)):
            continue
        for raw in rows:
            if not isinstance(raw, Mapping):
                continue
            row = dict(raw)
            raw_program = row.get("theory_program")
            program: TheoryProgram | None = None
            if isinstance(raw_program, Mapping):
                try:
                    program = TheoryProgram.from_json(raw_program)
                except (TypeError, ValueError):
                    continue
            elif raw_program is not None:
                continue
            program_id = str(
                row.get("theory_program_id")
                or (program.program_id if program is not None else "")
            )
            if not program_id:
                continue
            if program is not None and program_id != program.program_id:
                continue
            lineage_id = program.lineage_id if program is not None else ""
            key = (
                ("lineage", lineage_id)
                if lineage_id
                else ("program", program_id)
            )
            record = records.setdefault(
                key,
                {
                    "lineage_id": lineage_id,
                    "program_ids": [],
                    "presentations": [],
                },
            )
            if program_id not in record["program_ids"]:
                record["program_ids"].append(program_id)
            if program is not None:
                presentation = tuple(sorted(program.presentation_formula_ids))
                if presentation not in record["presentations"]:
                    record["presentations"].append(presentation)
            record["program_id"] = program_id
            record["representative"] = row
    return tuple(
        {
            **record,
            "program_ids": tuple(record["program_ids"]),
            "presentations": tuple(record["presentations"]),
        }
        for record in records.values()
        if record.get("representative") is not None
    )


def _objective_navigation_phase(run: Mapping[str, Any] | None) -> str:
    """Choose the campaign allocation owned by the active search obligation."""

    navigation = (run or {}).get("navigation") or {}
    return (
        "expansion"
        if navigation.get("objective_review_history")
        else "navigation"
    )


def _lineage_synthesis_retry_required(run: Mapping[str, Any] | None) -> bool:
    """A frozen synthesis input remains the next job until it is disposed."""

    navigation = (run or {}).get("navigation") or {}
    return bool(
        (run or {}).get("status") == "frontier_objective_unmet"
        and isinstance(
            navigation.get("lineage_synthesis_budget_stop"), Mapping
        )
    )


def _objective_synthesis_budget_exhausted(
    directory: Path, run: Mapping[str, Any]
) -> bool:
    """Whether the frozen synthesis job has no allocation left to retry."""

    if not _lineage_synthesis_retry_required(run):
        return False
    budget_row = read_json(directory / "budget.json", None)
    if not isinstance(budget_row, Mapping):
        return False
    budget = ExplorationBudget.from_json(budget_row)
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    phase = _objective_navigation_phase(run)
    return min(
        ledger.remaining_capacity(phase, "provider_calls"),
        ledger.remaining_capacity(phase, "agent_turns"),
    ) == 0


def _archive_json_once(source: Path, target: Path) -> None:
    row = read_json(source, None)
    if not isinstance(row, Mapping):
        return
    prior = read_json(target, None)
    if isinstance(prior, Mapping) and dict(prior) != dict(row):
        raise ValueError(f"boundary archive conflicts with {target.name}")
    if prior is None:
        write_json_atomic(target, dict(row))


def _archive_boundary_json(source: Path, target: Path) -> Path:
    """Archive repeated boundary attempts without changing prior evidence."""

    row = read_json(source, None)
    if not isinstance(row, Mapping):
        return target
    prior = read_json(target, None)
    if isinstance(prior, Mapping) and dict(prior) != dict(row):
        digest = content_hash(row)[:16]
        target = target.with_name(f"{target.stem}.{digest}{target.suffix}")
    _archive_json_once(source, target)
    return target


def _open_boundary_feedback_wave(
    directory: Path,
    run: Mapping[str, Any],
    feedback: Mapping[str, Any],
) -> dict[str, Any]:
    """Atomically make completed boundary evidence input to a fresh search wave."""

    navigation = dict(run.get("navigation") or {})
    wave = int(navigation.get("search_wave", 0))
    suffix = f"wave-{wave:03d}.json"
    for name in (
        "run", "boundary_result", "boundary_completion",
        "boundary_governance_recheck", "budget_stop_receipt",
        "theory_task_discharge", "theory_task_discharge_consumption",
    ):
        _archive_boundary_json(
            directory / f"{name}.json",
            directory / f"{name}.{suffix}",
        )
    feedback_path = directory / f"boundary_search_feedback.{suffix}"
    prior_feedback = read_json(feedback_path, None)
    if isinstance(prior_feedback, Mapping) and dict(prior_feedback) != dict(feedback):
        feedback_path = feedback_path.with_name(
            f"{feedback_path.stem}.{content_hash(feedback)[:16]}"
            f"{feedback_path.suffix}"
        )
        prior_feedback = read_json(feedback_path, None)
    if prior_feedback is None:
        write_json_atomic(feedback_path, dict(feedback))
    history = list(navigation.get("objective_review_history") or ())
    if not any(
        isinstance(row, Mapping)
        and row.get("receipt_sha256") == feedback.get("receipt_sha256")
        for row in history
    ):
        history.append(dict(feedback))
    navigation["objective_review_history"] = history
    core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "status": "frontier_objective_unmet",
        "navigation": navigation,
    }
    updated = {**core, "run_digest": content_hash(core)}
    write_json_atomic(directory / "run.json", updated)
    return updated


def _clear_active_boundary_artifacts_after_feedback(
    directory: Path, run: Any
) -> None:
    if not isinstance(run, Mapping) or run.get("status") != "frontier_objective_unmet":
        return
    navigation = run.get("navigation") or {}
    history = navigation.get("objective_review_history") or ()
    if not any(
        isinstance(row, Mapping)
        and row.get("schema") == "leanmill.boundary_search_feedback.v1"
        for row in history
    ):
        return
    for name in (
        "boundary_result.json", "boundary_completion.json",
        "boundary_governance_recheck.json", "budget_stop_receipt.json",
        "theory_task_discharge.json", "theory_task_discharge_consumption.json",
    ):
        (directory / name).unlink(missing_ok=True)


def _refresh_conflict_memory_after_feedback(
    directory: Path, run: Mapping[str, Any] | None
) -> None:
    # A context epoch may be checkpointed before the terminal run projection
    # exists.  Resume uses that checkpoint directly; there is no objective or
    # boundary feedback to refresh in this lifecycle state.
    if not isinstance(run, Mapping):
        return
    navigation = run.get("navigation") or {}
    feedback = next(
        (
            row
            for row in reversed(navigation.get("objective_review_history") or ())
            if isinstance(row, Mapping)
            and row.get("schema")
            in {
                "leanmill.boundary_search_feedback.v1",
                "leanmill.compound_implication_sieve_feedback.v1",
            }
        ),
        None,
    )
    if feedback is None:
        return
    if (
        feedback.get("schema") == "leanmill.boundary_search_feedback.v1"
        and not feedback.get("failed_predictions")
    ):
        return
    feedback_id = str(feedback.get("receipt_sha256") or "")
    marker = directory / f"theory_conflict_memory_refresh.{feedback_id[:16]}.json"
    if marker.is_file():
        return
    epoch = int(
        navigation.get(
            "context_epoch",
            (run.get("context_summary") or {}).get("context_epoch", 0),
        )
    )
    source = directory / f"theory_conflict_memory.epoch-{epoch:03d}.json"
    archived = directory / (
        f"theory_conflict_memory.epoch-{epoch:03d}.before-{feedback_id[:16]}.json"
    )
    _archive_json_once(source, archived)
    source.unlink(missing_ok=True)
    core = {
        "schema": "leanmill.theory_conflict_memory_refresh.v1",
        "context_hash": str(run.get("context_hash") or ""),
        "context_epoch": epoch,
        "feedback_schema": str(feedback.get("schema") or ""),
        "feedback_receipt": feedback_id,
        "prior_snapshot": archived.name if archived.is_file() else "",
        "authority": "host_conflict_transition",
    }
    write_json_atomic(marker, {**core, "receipt_sha256": content_hash(core)})


def resume_frontier_campaign_navigation(
    attempt_dir: str | Path,
    *,
    repo: Path | None = None,
    workbench_authority_ref: str = "",
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> Path:
    """Continue an interrupted navigator from immutable durable role calls."""

    directory = Path(attempt_dir)
    existing = _restore_durable_search_transition(
        directory, read_json(directory / "run.json", None)
    )
    existing = _archive_cross_context_active_candidates(directory, existing)
    existing = _restore_nested_objective_feedback_history(directory, existing)
    existing = _repair_stale_boundary_disposition_status(directory, existing)
    boundary_completion = read_json(directory / "boundary_completion.json", None)
    boundary_feedback = _boundary_search_feedback(existing, boundary_completion)
    pending_external_science = _pending_external_science_admission(
        directory, existing if isinstance(existing, Mapping) else None
    )
    pending_external_science_negative = (
        _pending_external_science_negative_disposition(
            directory, existing if isinstance(existing, Mapping) else None
        )
    )
    if (
        pending_external_science is not None
        and pending_external_science_negative is not None
    ):
        raise ValueError("conflicting external science recovery outcomes are pending")
    if (
        isinstance(existing, dict)
        and existing.get("status")
        in {
            "frontier_candidates_frozen_awaiting_boundary_approval",
            "frontier_no_candidate",
            "frontier_navigation_exhausted",
            "frontier_language_expansion_requested",
            "frontier_objective_discharged",
            "budget_stopped",
        }
        and boundary_feedback is None
        and pending_external_science is None
        and pending_external_science_negative is None
    ):
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
                workbench_authority_ref=workbench_authority_ref,
                _attempt_lease=lease,
            )

    definition, blueprint, budget_row, campaign_row, context = (
        _load_campaign_attempt(directory)
    )
    if pending_external_science is not None:
        deliver_external_science_resume_context(
            directory,
            pending_external_science,
            _attempt_lease=_attempt_lease,
        )
        existing = read_json(directory / "run.json", None)
        if not isinstance(existing, Mapping):
            raise ValueError("external science delivery lost the campaign run")
    if pending_external_science_negative is not None:
        deliver_external_science_negative_disposition(
            directory,
            pending_external_science_negative,
            _attempt_lease=_attempt_lease,
        )
        existing = read_json(directory / "run.json", None)
        if not isinstance(existing, Mapping):
            raise ValueError("external science negative delivery lost the campaign run")
    deliver_post_freeze_mechanism_feedback(
        directory, existing or {}, context_hash=context.context_hash
    )

    budget = ExplorationBudget.from_json(budget_row)
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    ledger.recover_interrupted_wall_clock()
    ledger.recover_interrupted_reservations()
    ledger.resume_wall_clock()
    if boundary_feedback is not None:
        if frontier_objective_contract(blueprint) is None:
            ledger.freeze_wall_clock(reason="boundary_feedback_has_no_search_capacity")
            return directory
        existing = _open_boundary_feedback_wave(
            directory, existing, boundary_feedback
        )
        _refresh_conflict_memory_after_feedback(directory, existing)
        search_phase = _objective_navigation_phase(existing)
        if min(
            ledger.remaining_capacity(search_phase, "provider_calls"),
            ledger.remaining_capacity(search_phase, "agent_turns"),
        ) == 0:
            ledger.freeze_wall_clock(reason="boundary_feedback_has_no_search_capacity")
            return directory
    _refresh_conflict_memory_after_feedback(directory, existing)
    _clear_active_boundary_artifacts_after_feedback(directory, existing)
    # Boundary opening and external-science delivery can append review rows
    # after the resume entry snapshot was read.  Carry the transitioned run's
    # history into the terminal projection; otherwise the survivor remains
    # nested in its candidate row but disappears from the active read model on
    # the following restart.
    carried_objective_history = [
        dict(row)
        for row in ((existing.get("navigation") or {}).get(
            "objective_review_history"
        ) if isinstance(existing, Mapping) else ()) or ()
        if isinstance(row, Mapping)
    ]
    if (
        isinstance(existing, Mapping)
        and existing.get("status") == "frontier_leaf_decision_pending"
        and min(
            ledger.remaining_capacity(
                _objective_navigation_phase(existing), "provider_calls"
            ),
            ledger.remaining_capacity(
                _objective_navigation_phase(existing), "agent_turns"
            ),
        ) == 0
    ):
        ledger.freeze_wall_clock(reason="pending_leaf_has_no_search_capacity")
        return directory
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
    if isinstance(checkpoint, Mapping):
        if checkpoint.get("context_hash") != context.context_hash:
            raise ValueError("navigation epoch checkpoint targets a stale context")
        context_epoch = int(checkpoint.get("context_epoch", 0))
        formula_hashes = [
            str(row)
            for row in checkpoint.get("typed_formula_proposal_sha256s") or ()
        ]

    lineage_count = host_isolated_lineage_count(blueprint)
    if lineage_count > 1:
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
            seed = (
                []
                if existing.get("status") == "frontier_objective_unmet"
                else list(getattr(navigator, "initial_trace", ()))
            )
            prior_navigation = existing.get("navigation") or {}
            history = prior_navigation.get("objective_review_history") or ()
            objective_survivors = tuple(
                row
                for row in _active_objective_finalists(prior_navigation)
                if _candidate_matches_context(
                    row,
                    context_hash=context.context_hash,
                    context_epoch=context_epoch,
                )
            )
            if objective_survivors:
                navigator.objective_survivors = objective_survivors  # type: ignore[attr-defined]
            if history and isinstance(history[-1], Mapping):
                latest_feedback = dict(history[-1])
                if not any(
                    row.get("decision") == "objective_feedback"
                    and row.get("receipt") == latest_feedback
                    for row in seed
                    if isinstance(row, Mapping)
                ):
                    seed.append(
                        {
                            "decision": "objective_feedback",
                            "receipt": latest_feedback,
                            "host_finalized": True,
                        }
                    )
                navigator.objective_feedback = latest_feedback  # type: ignore[attr-defined]
            unmaterialized_wave = int(
                getattr(navigator, "search_wave", 0)
            ) > int(prior_navigation.get("search_wave", 0))
            opened_wave = False
            retry_synthesis = _lineage_synthesis_retry_required(existing)
            if retry_synthesis:
                rows = list(prior_navigation.get("lineages") or ())
                navigator.preserved_lineage_rows = {  # type: ignore[attr-defined]
                    index: dict(row) for index, row in enumerate(rows)
                }
                navigator.recovered_lineage_requests = tuple(  # type: ignore[attr-defined]
                    dict(row)
                    for row in prior_navigation.get("expansion_proposals") or ()
                    if isinstance(row, Mapping)
                )
                navigator.retry_synthesis = True  # type: ignore[attr-defined]
            elif existing.get("status") == "frontier_leaf_decision_pending":
                if not unmaterialized_wave:
                    navigator.begin_search_wave()  # type: ignore[attr-defined]
                opened_wave = True
                recovered = read_json(
                    directory
                    / f"isolated_lineage_language_requests.epoch-{context_epoch:03d}.json",
                    {},
                )
                disposed_request_ids = {
                    str(request_id)
                    for path in directory.glob("lineage_synthesis.epoch-*.json")
                    for field in ("selected_request_ids", "deferred_request_ids")
                    for request_id in read_json(path, {}).get(field) or ()
                }
                navigator.recovered_lineage_requests = tuple(  # type: ignore[attr-defined]
                    dict(row)
                    for row in recovered.get("formula_requests") or ()
                    if isinstance(row, Mapping)
                    and str(row.get("request_id") or "")
                    not in disposed_request_ids
                )
                prior_lineages = {
                    int(row.get("branch_index", position)): str(
                        row.get("lineage_id") or ""
                    )
                    for position, row in enumerate(
                        prior_navigation.get("lineages") or ()
                    )
                    if isinstance(row, Mapping)
                }
                current_program_ids = {
                    str(candidate.get("lineage_id") or ""): str(
                        candidate.get("program_id") or ""
                    )
                    for candidate in _objective_candidate_lineages(prior_navigation)
                    if candidate.get("lineage_id") and candidate.get("program_id")
                }
                branch_traces: list[tuple[dict[str, Any], ...]] = []
                for index in range(lineage_count):
                    branch_lineage = prior_lineages.get(index) or derive_context_lineage_id(
                        campaign_id=campaign_id,
                        attempt_id=directory.name,
                        context_epoch=context_epoch,
                        branch=index,
                    )
                    branch_traces.append(
                        tuple(
                            row
                            for row in seed
                            if _external_science_trace_is_for_lineage(
                                row,
                                branch_lineage,
                                current_program_ids.get(branch_lineage, ""),
                            )
                        )
                    )
                preserved_rows: dict[int, dict[str, Any]] = {}
                same_materialized_context = (
                    prior_navigation.get("context_hash") == context.context_hash
                    and int(prior_navigation.get("context_epoch", -1))
                    == context_epoch
                    and not unmaterialized_wave
                )
                if same_materialized_context:
                    for position, lineage in enumerate(
                        prior_navigation.get("lineages") or ()
                    ):
                        index = int(lineage.get("branch_index", position))
                        if not 0 <= index < lineage_count:
                            raise ValueError("recovered lineage branch is outside the campaign")
                        trace = (lineage.get("navigation") or {}).get("trace") or ()
                        pending = (lineage.get("navigation") or {}).get(
                            "pending_leaf_decision"
                        )
                        if isinstance(pending, Mapping):
                            request = next(
                                (
                                    dict(row)
                                    for row in reversed(trace)
                                    if isinstance(row, Mapping)
                                    and row.get("decision") == "request"
                                ),
                                None,
                            )
                            branch_traces[index] = tuple(
                                seed + ([request] if request is not None else [])
                            )
                        else:
                            preserved_rows[index] = dict(lineage)
                navigator.lineage_initial_traces = tuple(branch_traces)  # type: ignore[attr-defined]
                navigator.preserved_lineage_rows = preserved_rows  # type: ignore[attr-defined]
            else:
                current_synthesis = prior_navigation.get("lineage_synthesis")
                deferred_ids = {
                    str(request_id)
                    for request_id in (
                        current_synthesis.get("deferred_request_ids") or ()
                    )
                } if isinstance(current_synthesis, Mapping) else set()
                stale_deferred_request_ids: set[str] = set()
                for path in directory.glob(
                    "isolated_lineage_language_requests.epoch-*.json"
                ):
                    requests = read_json(path, {})
                    for row in (
                        list(requests.get("formula_requests") or ())
                        + list(requests.get("theory_language_requests") or ())
                    ):
                        request_id = str(row.get("request_id") or "")
                        if request_id not in deferred_ids:
                            continue
                        if not lineage_request_matches_context(
                            row,
                            context_hash=context.context_hash,
                            context_epoch=context_epoch,
                        ):
                            stale_deferred_request_ids.add(request_id)
                            continue
                        if request_id:
                            seed.append(
                                {
                                    "decision": "deferred_request_reactivated",
                                    "request": dict(row),
                                    "authority": "host_receipt_replay",
                                }
                            )
                if stale_deferred_request_ids:
                    archive_core = {
                        "schema": "leanmill.stale_deferred_request_archive.v1",
                        "context_hash": context.context_hash,
                        "context_epoch": context_epoch,
                        "request_ids": sorted(stale_deferred_request_ids),
                        "status": "archived_source_epoch_only",
                        "authority": "host_context_identity_transition",
                    }
                    archive = {
                        **archive_core,
                        "receipt_sha256": content_hash(archive_core),
                    }
                    archive_path = directory / (
                        "stale_deferred_request_archive."
                        f"epoch-{context_epoch:03d}.json"
                    )
                    prior_archive = read_json(archive_path, None)
                    if isinstance(prior_archive, Mapping):
                        if dict(prior_archive) != archive:
                            raise ValueError(
                                "stale deferred-request archive changed identity"
                            )
                    else:
                        write_json_atomic(archive_path, archive)
                    seed.append({
                        "decision": "stale_deferred_requests_archived",
                        "receipt": archive,
                        "host_finalized": True,
                    })
            navigator.initial_trace = tuple(seed)  # type: ignore[attr-defined]
            if not retry_synthesis and not opened_wave and not unmaterialized_wave:
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
        packet = _admit_campaign_workbench_successor(
            directory,
            campaign=campaign_row,
            target_packet=packet,
            context_epoch=context_epoch,
            authority_ref=workbench_authority_ref,
        )
        if packet is None:
            ledger.freeze_wall_clock(
                reason="campaign_workbench_successor_authority_required"
            )
            return directory
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
            prior_navigation = (
                (existing.get("navigation") or {})
                if isinstance(existing, Mapping)
                else {}
            )
            has_dispositive_feedback = any(
                isinstance(row, Mapping)
                and row.get("schema")
                in {
                    "leanmill.boundary_search_feedback.v1",
                    "leanmill.adapter_rejection_search_feedback.v1",
                    _POST_FREEZE_RESEARCH_DISPOSITION_SCHEMA,
                }
                for row in prior_navigation.get("objective_review_history") or ()
            )
            reason = exc.reason
            if not has_dispositive_feedback and recoverable.intersection(
                {
                    "finalist_frozen",
                    "theory_presentation_rejected",
                    "theory_program_refused",
                    "navigator_reject_all",
                }
            ):
                reason = None
            return materialize_frontier_navigation_from_journal(
                directory,
                budget_stop_reason=reason,
                _attempt_lease=_attempt_lease,
            )

        navigation = dict(driven.navigation)
        merged_history: list[dict[str, Any]] = []
        seen_history: set[str] = set()
        for row in carried_objective_history + [
            dict(item)
            for item in navigation.get("objective_review_history") or ()
            if isinstance(item, Mapping)
        ]:
            identity = str(row.get("receipt_sha256") or content_hash(row))
            if identity not in seen_history:
                seen_history.add(identity)
                merged_history.append(row)
        if merged_history:
            navigation["objective_review_history"] = merged_history
        prior_navigation = (
            (existing.get("navigation") or {})
            if isinstance(existing, Mapping)
            else {}
        )
        for key in (
            "external_science_resume_context_by_lineage",
            "external_science_negative_dispositions",
        ):
            if key in prior_navigation and key not in navigation:
                navigation[key] = prior_navigation[key]

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
            navigation=navigation,
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
        ledger.recover_interrupted_reservations()
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
    prior_run = read_json(directory / "run.json", {})
    receipt_index = _navigator_receipt_index(prior_run)
    disposed_program_ids = {
        str(program_id)
        for row in (prior_run.get("navigation") or {}).get(
            "objective_review_history", ()
        )
        if isinstance(row, Mapping)
        and row.get("schema") == "leanmill.boundary_search_feedback.v1"
        for program_id in row.get("program_ids") or ()
    }

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
            lineage_id = derive_context_lineage_id(
                campaign_id=campaign_id,
                attempt_id=directory.name,
                context_epoch=epoch,
                branch=branch,
            )
            base_name = f"navigator.lineage-{branch:03d}"
            call_dirs = sorted(
                path
                for path in (directory / "agent_calls").glob(base_name + "*")
                if path.is_dir()
                and (path.name == base_name or path.name.startswith(base_name + ".wave-"))
            )
            replayed_segments: list[tuple[Path, dict[str, Any]]] = []
            for call_dir in call_dirs:
                branch_calls, decisions, initial_trace = _durable_navigator_segment(
                    call_dir,
                    receipt_index=receipt_index,
                )
                calls.extend(branch_calls)
                if not decisions:
                    continue
                replayed_segments.append(
                    (
                        call_dir,
                        _replay_navigator_decisions(
                            context,
                            blueprint,
                            decisions,
                            IdempotentReplayJournal(
                                directory
                                / "lineage_journals"
                                / f"recovery-{call_dir.name}.events.jsonl"
                            ),
                            attempt_id=f"{directory.name}:lineage:{branch}",
                            campaign_id=campaign_id,
                            epoch=epoch,
                            lineage_id=lineage_id,
                            max_finalists=per_lineage_finalists,
                            prior_conflict_rows=prior_conflicts,
                            initial_trace=initial_trace,
                        ),
                    )
                )
            if not replayed_segments:
                continue
            eligible_segments = [
                row
                for row in replayed_segments
                if not (
                    _terminal_navigation(row[1])
                    and any(
                        str(finalist.get("theory_program_id") or "")
                        in disposed_program_ids
                        for finalist in row[1].get("finalists") or ()
                        if isinstance(finalist, Mapping)
                    )
                )
            ]
            if not eligible_segments:
                continue
            call_dir, branch_navigation = next(
                (
                    row
                    for row in reversed(eligible_segments)
                    if _terminal_navigation(row[1])
                ),
                eligible_segments[-1],
            )
            rows.append(
                {
                    "branch_index": branch,
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
        prior_run = read_json(directory / "run.json", {})
        prior_core = {
            key: value for key, value in prior_run.items() if key != "run_digest"
        }
        prior_navigation = prior_run.get("navigation")
        if (
            prior_run.get("run_digest") == content_hash(prior_core)
            and prior_run.get("context_hash") == context.context_hash
            and isinstance(prior_navigation, Mapping)
            and not disposed_program_ids
        ):
            navigation = dict(prior_navigation)
        elif budget_stop_reason is None:
            raise ValueError("navigation has no durable decision and no budget stop")
        else:
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

    wave_images = sorted(
        directory.glob(
            f"theory_search_wave_image.final.epoch-{epoch:03d}.wave-*.json"
        )
    )
    if wave_images:
        navigation["search_wave_image_receipt"] = read_json(wave_images[-1], {})
    frozen_requests = read_json(
        directory / f"isolated_lineage_language_requests.epoch-{epoch:03d}.json",
        {},
    )
    if not navigation.get("expansion_proposals"):
        navigation["expansion_proposals"] = list(
            frozen_requests.get("formula_requests") or ()
        )
    if not navigation.get("theory_language_expansion_requests"):
        navigation["theory_language_expansion_requests"] = list(
            frozen_requests.get("theory_language_requests") or ()
        )
    objective = frontier_objective_contract(blueprint)
    for synthesis_path in reversed(
        sorted(directory.glob(f"lineage_synthesis.epoch-{epoch:03d}*.json"))
    ):
        synthesis = read_json(synthesis_path, {})
        synthesis_core = {
            key: value for key, value in synthesis.items() if key != "receipt_sha256"
        }
        if synthesis.get("receipt_sha256") != content_hash(synthesis_core):
            continue
        replay_input = lineage_synthesis_input(
            navigation, objective_contract=objective
        )
        if synthesis.get("input_sha256") != replay_input.get("input_sha256"):
            continue
        navigation["lineage_synthesis"] = synthesis
        if synthesis.get("route") == "continue_search":
            navigation["objective_review_history"] = [synthesis]
        break

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
    if budget_stop_reason is not None and (not terminal or objective is not None):
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

def _registered_formal_task_executor_required(
    navigation: Mapping[str, Any],
) -> bool:
    """Whether a frozen program owns an executable formal-task adjudicator.

    Prediction-level Lean checks remain controlled by the blueprint's
    ``conditional_lean`` flag.  A leaf-authored task contract is a different
    lifecycle object: once frozen, its registered adjudicator must be
    available even when the original prediction plan did not request Lean.
    """

    from ztare.leanmill.formal_task_boundary import (
        GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
    )

    for candidate in _objective_candidate_lineages(navigation):
        representative = candidate.get("representative") or {}
        program_row = representative.get("theory_program")
        if not isinstance(program_row, Mapping):
            continue
        program = TheoryProgram.from_json(program_row)
        if any(
            contract.adjudicator_id
            == GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR
            for contract in program.task_discharge_contracts
        ):
            return True
    return False


def execute_frontier_campaign_verification(
    attempt_dir: str | Path,
    *,
    with_lean: bool = False,
    with_isabelle: bool = False,
    lean_root: str | Path | None = None,
    resume_search: bool = True,
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
                resume_search=resume_search,
                _attempt_lease=lease,
            )
    _bind_active_attempt_epoch(_attempt_lease, directory)
    activation_run = read_json(directory / "run.json", None)
    activation_navigation = (
        activation_run.get("navigation")
        if isinstance(activation_run, Mapping)
        and isinstance(activation_run.get("navigation"), Mapping)
        else {}
    )
    formal_task_requested = _registered_formal_task_executor_required(
        activation_navigation
    )
    lean_executor = None
    isabelle_executor = None
    theory_task_executor = None
    governance_root: Path | None = None
    governance_timeout_s = 0
    if with_isabelle:
        from ztare.leanmill.solver.sledgehammer import (
            execute_isabelle_theory_task,
        )

        def isabelle_executor(task, *, timeout_s):
            return execute_isabelle_theory_task(
                task,
                timeout_s=int(timeout_s),
            ).to_json()

    if with_lean or formal_task_requested:
        root = (
            Path(lean_root)
            if lean_root is not None
            else Path(__file__).resolve().parents[3] / "ztare_proofs"
        )
        definition, blueprint, _budget_row, _campaign_row, _context = (
            _load_campaign_attempt(directory)
        )
        solver_role = frontier_agent_role(
            definition,
            role_name="lean_solver",
            repo=Path.cwd(),
            artifact_dir=directory / "agent_calls",
        )
        config = solver_role.config
        formalizer_role = frontier_agent_role(
            definition,
            role_name="formalizer",
            repo=Path.cwd(),
            artifact_dir=directory / "agent_calls",
        )
        faithfulness_reviewer_role = frontier_agent_role(
            definition,
            role_name="faithfulness_reviewer",
            repo=Path.cwd(),
            artifact_dir=directory / "agent_calls",
        )
        timeout_s = min(
            definition.budget.wall_clock_s,
            config.timeout_seconds,
            max(
                1,
                int(blueprint.verification_plan.get("lean_timeout_ms", 180_000))
                // 1_000,
            ),
        )
        governance_root = root
        governance_timeout_s = timeout_s

        def record_solver_run(
            task: Any,
            *,
            run_tag: str,
            status: str,
            governed_status: str = "",
            error: str = "",
        ) -> None:
            core: dict[str, Any] = {
                "schema": "leanmill.frontier_solver_run.v1",
                "task_id": str(task.task_id),
                "target_name": str(task.target_name),
                "run_tag": run_tag,
                "status": status,
                "governed_status": governed_status,
                "error": error,
            }
            if status != "running":
                try:
                    from ztare.leanmill.phase_timing import summarize_phase_timings
                    from ztare.leanmill.run_diagnostics import summarize_run

                    core["diagnostics"] = summarize_run(
                        run_tag=run_tag, lean_root=root
                    )
                    core["phase_timing"] = summarize_phase_timings(run_tag=run_tag)
                except Exception as exc:  # read-model failure cannot change proof work
                    core["observability_error"] = type(exc).__name__
            write_json_atomic(
                directory
                / "solver_runs"
                / f"{task.task_id.rsplit(':', 1)[-1]}.json",
                core,
            )

        def compile_fn(source: str):
            from ztare.gates.v33_preflight_risk_detector import _compile_probe

            return _compile_probe(
                source,
                root,
                "AxiomPackBoundaryAttribution",
                timeout_s,
            )

        def lean_executor(task, *, budget_ledger):
            run_tag = (
                f"{directory.name}-boundary-"
                f"{task.task_id.rsplit(':', 1)[-1][:16]}"
            )
            def before_dispatch(runtime, _command):
                return budget_ledger.reserve(
                    f"boundary:{task.task_id}:{runtime}",
                    "boundary",
                    {"provider_calls": 1, "agent_turns": 1},
                )

            def after_dispatch(reservation):
                budget_ledger.commit(reservation)

            record_solver_run(task, run_tag=run_tag, status="running")
            try:
                with scoped_frontier_agent_environment(
                    config, solver_run_tag=run_tag
                ), subscription_dispatch_budget_scope(
                    before_dispatch=before_dispatch,
                    after_dispatch=after_dispatch,
                ):
                    result = execute_governed_lean_consequence(
                        task,
                        substrate=root,
                        timeout_s=timeout_s,
                        compile_fn=compile_fn,
                    ).to_json()
            except Exception as exc:
                record_solver_run(
                    task,
                    run_tag=run_tag,
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}"[-400:],
                )
                raise
            record_solver_run(
                task,
                run_tag=run_tag,
                status="completed",
                governed_status=str(result.get("status") or ""),
            )
            return result

        def theory_task_executor(
            contract,
            *,
            context,
            verification_plan,
            budget_ledger,
        ):
            """Use the existing formalize/firewall/solve lane for a frozen task."""

            from ztare.leanmill.formal_task_campaign_executor import (
                build_formal_task_role_registry_receipt,
                make_formalization_campaign_task_executor,
            )
            from ztare.leanmill.formalization_admission import formalize_only
            from ztare.leanmill.solver.solver_core import solve_adhoc

            task_tag = contract.sha256[:16]
            run_tag = f"{directory.name}-theory-task-{task_tag}"

            def before_dispatch(runtime, _command):
                return budget_ledger.reserve(
                    f"boundary:theory-task:{task_tag}:{runtime}",
                    "boundary",
                    {"provider_calls": 1, "agent_turns": 1},
                )

            def after_dispatch(reservation):
                budget_ledger.commit(reservation)

            def settle_dispatch(reservation, result):
                from ztare.leanmill.frontier_agent_runtime import (
                    _provider_call_charge,
                )

                charged = bool(
                    result is not None and _provider_call_charge(result) >= 1
                )
                if charged:
                    budget_ledger.commit(reservation)
                else:
                    budget_ledger.release(
                        reservation,
                        reason="formal_task_dispatch_not_charged",
                    )
                return charged

            @contextmanager
            def reviewer_environment():
                from ztare.common.llm_runtime import subscription_reasoning_effort

                reviewer_effort = subscription_reasoning_effort(
                    faithfulness_reviewer_role.config.runtime,
                    faithfulness_reviewer_role.config.reasoning_effort,
                    model=faithfulness_reviewer_role.config.model,
                )
                if reviewer_effort is None:
                    raise ValueError(
                        "formal-task faithfulness reviewer effort is unsupported"
                    )
                bindings = {
                    "ZTARE_LEANMILL_ROUNDTRIP_MODEL": (
                        faithfulness_reviewer_role.config.runtime
                    ),
                    "ZTARE_LEANMILL_ROUNDTRIP_AGENT_MODEL": (
                        faithfulness_reviewer_role.config.model
                    ),
                    "ZTARE_LEANMILL_ROUNDTRIP_AGENT_REASONING_EFFORT": (
                        reviewer_effort
                    ),
                    "ZTARE_LEANMILL_ROUNDTRIP_AGENT_ID": (
                        faithfulness_reviewer_role.agent_id
                    ),
                    "ZTARE_LEANMILL_ROUNDTRIP_CONFIG_SHA256": str(
                        role_registry["roles"]["faithfulness_reviewer"][
                            "config_sha256"
                        ]
                    ),
                    "ZTARE_LEANMILL_ROUNDTRIP_RUN_TAG": (
                        f"{directory.name}:theory-task:faithfulness_reviewer:"
                        f"{contract.sha256[:16]}"
                    ),
                    "ZTARE_LEANMILL_ROUNDTRIP_TIMEOUT_S": str(
                        faithfulness_reviewer_role.config.timeout_seconds
                    ),
                    "ZTARE_LEANMILL_ROUNDTRIP_API_FALLBACK": "0",
                    "ZTARE_LEANMILL_FORMALIZE_API_FALLBACK": "0",
                }
                prior = {key: os.environ.get(key) for key in bindings}
                os.environ.update(bindings)
                try:
                    yield
                finally:
                    for key, value in prior.items():
                        if value is None:
                            os.environ.pop(key, None)
                        else:
                            os.environ[key] = value

            def admit(*args, **kwargs):
                with scoped_frontier_agent_environment(
                    formalizer_role.config,
                    solver_run_tag=run_tag + "-formalize",
                ), reviewer_environment():
                    return formalize_only(*args, **kwargs)

            def solve(*args, **kwargs):
                with scoped_frontier_agent_environment(
                    solver_role.config,
                    solver_run_tag=run_tag + "-solve",
                ):
                    return solve_adhoc(*args, **kwargs)

            campaign_id = str(_campaign_row["packet"]["campaign_id"])
            role_registry = build_formal_task_role_registry_receipt(
                attempt_id=directory.name,
                campaign_id=campaign_id,
                formalizer_role=formalizer_role,
                faithfulness_reviewer_role=faithfulness_reviewer_role,
                lean_solver_role=solver_role,
            )
            executor = make_formalization_campaign_task_executor(
                attempt_id=directory.name,
                campaign_id=campaign_id,
                sandbox=root,
                substrate=root,
                compile_fn=compile_fn,
                timeout_s=timeout_s,
                role_registry_receipt=role_registry,
                formalization_admission_fn=admit,
                admitted_solver_fn=solve,
            )
            with subscription_dispatch_budget_scope(
                before_dispatch=before_dispatch,
                after_dispatch=after_dispatch,
                settle_dispatch=settle_dispatch,
            ):
                return executor(
                    contract,
                    context=context,
                    verification_plan=verification_plan,
                    budget_ledger=budget_ledger,
                )

    # Do not widen an optional prediction-level referee merely because a
    # distinct task adjudicator needed the same Lean runtime.
    if not with_lean:
        lean_executor = None
    if not formal_task_requested:
        theory_task_executor = None

    budget_row = read_json(directory / "budget.json", None)
    ledger = None
    if isinstance(budget_row, dict):
        ledger = ExplorationBudgetLedger(
            directory / "budget.events.jsonl",
            ExplorationBudget.from_json(budget_row),
            attempt_id=directory.name,
        )
        ledger.recover_interrupted_wall_clock()
        ledger.recover_interrupted_reservations()
        ledger.resume_wall_clock()
    try:
        completion = execute_frontier_boundaries(
            directory,
            lean_executor_fn=lean_executor,
            isabelle_executor_fn=isabelle_executor,
            theory_task_executor_fn=theory_task_executor,
        )
    finally:
        if ledger is not None:
            ledger.freeze_wall_clock(reason="boundary_runner_exit")
    boundary_rows = (completion.get("boundary_result") or {}).get(
        "query_results"
    ) or ()
    saved_lean_proof = any(
        str(
            (((row.get("lean") or {}).get("governed_attempt") or {}).get(
                "proof_text"
            ) or "")
        ).strip()
        for row in boundary_rows
        if isinstance(row, Mapping)
    )
    if saved_lean_proof and governance_root is not None:
        recheck_frontier_boundary_governance(
            directory,
            lean_root=governance_root,
            timeout_s=governance_timeout_s,
        )
    source_run = read_json(directory / "run.json", None)
    if isinstance(source_run, Mapping):
        source_run = _consume_theory_task_discharge(
            directory, source_run, completion
        )
    feedback = _boundary_search_feedback(source_run, completion)
    if feedback is not None and resume_search:
        resume_frontier_campaign_navigation(
            directory,
            _attempt_lease=_attempt_lease,
        )
        resumed = read_json(directory / "run.json", None)
        if (
            isinstance(resumed, Mapping)
            and isinstance(source_run, Mapping)
            and resumed.get("run_digest") != source_run.get("run_digest")
        ):
            return {
                "schema": "leanmill.boundary_search_continuation.v1",
                "status": str(resumed.get("status") or ""),
                "attempt_dir": str(directory),
                "context_hash": str(resumed.get("context_hash") or ""),
                "boundary_feedback_receipt": feedback["receipt_sha256"],
                "run_digest": str(resumed.get("run_digest") or ""),
            }
    return completion


def recheck_frontier_boundary_governance(
    attempt_dir: str | Path,
    *,
    lean_root: str | Path,
    timeout_s: int = 180,
    proof_candidates: Mapping[str, str] | None = None,
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

    candidates = {
        str(target): str(proof)
        for target, proof in dict(proof_candidates or {}).items()
        if str(proof).strip()
    }
    used_candidates: set[str] = set()
    rows: list[dict[str, Any]] = []
    for query in boundary.get("query_results") or ():
        if not isinstance(query, Mapping):
            continue
        lean = query.get("lean") or {}
        governed = lean.get("governed_attempt") if isinstance(lean, Mapping) else None
        governed = governed if isinstance(governed, Mapping) else {}
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
        proof = str(governed.get("proof_text") or "").strip()
        proof_source = "boundary_result"
        if not proof and target_id in candidates:
            proof = candidates[target_id].strip()
            proof_source = "explicit_recovery_candidate"
            used_candidates.add(target_id)
        if not proof:
            continue
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
                "proof_source": proof_source,
                "proof_digest": content_hash({"proof_text": proof}),
                "recheck": result,
            }
        )
    unused_candidates = set(candidates) - used_candidates
    if unused_candidates:
        raise ValueError(
            "proof candidates do not match unresolved boundary targets: "
            + ", ".join(sorted(unused_candidates))
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


_POST_FREEZE_MECHANISM_FEEDBACK_SCHEMA = (
    "leanmill.post_freeze_mechanism_feedback.v1"
)
_POST_FREEZE_RESEARCH_DISPOSITION_SCHEMA = (
    "leanmill.post_freeze_research_disposition.v1"
)
_POST_FREEZE_FEEDBACK_SCHEMAS = frozenset(
    {
        _POST_FREEZE_MECHANISM_FEEDBACK_SCHEMA,
        _POST_FREEZE_RESEARCH_DISPOSITION_SCHEMA,
    }
)


def _post_freeze_reviewed_presentation(
    interpretation: Mapping[str, Any],
) -> tuple[str, ...]:
    """Recover the exact premise identity reviewed by the interpretation."""

    operational = interpretation.get("operational_characterization")
    if not isinstance(operational, Mapping):
        raise ValueError("post-freeze interpretation lacks operational formulas")
    formulas = operational.get("formulas")
    if not isinstance(formulas, list) or any(
        not isinstance(row, Mapping) for row in formulas
    ):
        raise ValueError("post-freeze operational formulas are malformed")
    premise_ids = [
        str(row.get("formula_id") or "")
        for row in formulas
        if isinstance(row, Mapping) and row.get("role") == "premise"
    ]
    if (
        not premise_ids
        or any(not value for value in premise_ids)
        or len(set(premise_ids)) != len(premise_ids)
    ):
        raise ValueError("post-freeze reviewed presentation is malformed")
    return tuple(sorted(premise_ids))


def _post_freeze_lineage_binding(
    navigation: Mapping[str, Any],
    interpretation: Mapping[str, Any],
    *,
    context_hash: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Bind a reviewed presentation to current representatives of its lineages."""

    reviewed = _post_freeze_reviewed_presentation(interpretation)
    lineage_ids: list[str] = []
    program_ids: list[str] = []
    for candidate in _objective_candidate_lineages(navigation):
        lineage_id = str(candidate.get("lineage_id") or "")
        if not lineage_id or reviewed not in candidate.get("presentations", ()):
            continue
        representative = candidate.get("representative")
        raw_program = (
            representative.get("theory_program")
            if isinstance(representative, Mapping)
            else None
        )
        try:
            program = TheoryProgram.from_json(raw_program)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "post-freeze lineage representative is not a frozen theory program"
            ) from exc
        if (
            program.lineage_id != lineage_id
            or program.context_hash != context_hash
            or program.program_id != candidate.get("program_id")
        ):
            raise ValueError("post-freeze lineage representative changed identity")
        lineage_ids.append(lineage_id)
        program_ids.append(program.program_id)
    if not lineage_ids:
        raise ValueError(
            "post-freeze reviewed presentation matches no frozen theory lineage"
        )
    return reviewed, tuple(lineage_ids), tuple(program_ids)


def _post_freeze_feedback_artifact_path(
    directory: Path, feedback: Mapping[str, Any]
) -> Path:
    interpretation_sha = str(feedback.get("interpretation_sha256") or "")
    prefix = (
        "post_freeze_research_disposition"
        if feedback.get("schema") == _POST_FREEZE_RESEARCH_DISPOSITION_SCHEMA
        else "post_freeze_mechanism_feedback"
    )
    return directory / f"{prefix}.{interpretation_sha[:16]}.json"


def _post_freeze_research_disposition(
    literature_receipt: Mapping[str, Any],
    interpretation: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Project source review and deterministic recurrence without source identity."""

    alignment = interpretation.get("external_alignment")
    if not isinstance(alignment, Mapping):
        return None
    review = literature_receipt.get("review")
    if not isinstance(review, Mapping):
        raise ValueError("post-freeze alignment lacks its source review")
    external_status_by_assessment = {
        "known_implication": "catalogued",
        "likely_elementary_or_known": "likely_catalogued",
        "not_located_in_bounded_review": "unresolved",
        "conflicting_evidence": "conflicting",
    }
    external_status = str(alignment.get("status") or "unavailable")
    expected_external_status = external_status_by_assessment.get(
        str(review.get("novelty_assessment") or ""), "unavailable"
    )
    if external_status != expected_external_status:
        raise ValueError("post-freeze source disposition changed after interpretation")

    literature_checks = {
        str(row.get("receipt_sha256") or ""): dict(row)
        for row in literature_receipt.get("finite_witness_host_checks") or ()
        if isinstance(row, Mapping) and row.get("receipt_sha256")
    }
    recurrence = alignment.get("structural_recurrence")
    recurrence = dict(recurrence) if isinstance(recurrence, Mapping) else {}
    verified_relations: list[dict[str, Any]] = []
    for raw in recurrence.get("checks") or ():
        if not isinstance(raw, Mapping) or raw.get("status") != "verified":
            continue
        check = dict(raw)
        check_core = {
            key: value for key, value in check.items() if key != "receipt_sha256"
        }
        check_sha = str(check.get("receipt_sha256") or "")
        equivalence = check.get("equivalence_receipt")
        if (
            not check_sha
            or check_sha != content_hash(check_core)
            or literature_checks.get(check_sha) != check
            or check.get("authority") != "deterministic_host_table_replay"
            or not isinstance(equivalence, Mapping)
        ):
            raise ValueError("post-freeze recurrence check does not replay")
        equivalence_core = {
            key: value
            for key, value in equivalence.items()
            if key != "receipt_sha256"
        }
        relation = str(check.get("computed_relation") or "")
        if (
            equivalence.get("receipt_sha256") != content_hash(equivalence_core)
            or equivalence.get("status") != "completed"
            or equivalence.get("scope") != "finite_witness_only"
            or equivalence.get("relation") != relation
        ):
            raise ValueError("post-freeze recurrence equivalence does not replay")
        if relation in {"", "unmatched", "unavailable_bounds"}:
            continue
        verified_relations.append(
            {
                "check_receipt_sha256": check_sha,
                "equivalence_receipt_sha256": str(
                    equivalence.get("receipt_sha256") or ""
                ),
                "relation": relation,
                "scope": "finite_witness_only",
                "carrier_size": int(equivalence.get("carrier_size", 0)),
                "operation_arity": int(equivalence.get("operation_arity", 0)),
                "max_term_depth": int(equivalence.get("max_term_depth", 0)),
            }
        )
    expected_recurrence_status = (
        "verified_finite_recurrence" if verified_relations else "none_verified"
    )
    if str(recurrence.get("status") or "none_verified") != expected_recurrence_status:
        raise ValueError("post-freeze recurrence disposition is inconsistent")

    recorded_components = bool(
        review.get("implication_prior_art")
        or review.get("recognized_theory_connections")
        or verified_relations
        or any(
            isinstance(row, Mapping)
            and row.get("match_status") in {"exact", "equivalent"}
            for row in review.get("formula_matches") or ()
        )
    )
    expected_origin = (
        "catalogued_recovery"
        if external_status == "catalogued"
        else "likely_routine_reconstruction"
        if external_status == "likely_catalogued"
        else "recorded_components_unmapped_recombination"
        if external_status == "unresolved" and recorded_components
        else "unmapped_candidate"
        if external_status == "unresolved"
        else "unresolved"
    )
    origin_disposition = str(alignment.get("origin_disposition") or "")
    if origin_disposition != expected_origin:
        raise ValueError("post-freeze origin disposition changed after interpretation")

    if external_status == "catalogued":
        residual = "distinguish_from_catalogued_result_or_change_objective"
    elif external_status == "likely_catalogued":
        residual = "adjudicate_likely_recurrence_before_terminal_credit"
    elif verified_relations:
        residual = "separate_unmapped_implication_from_recurrent_finite_structure"
    else:
        residual = "transport_grounded_mechanism_under_destination_replay"
    recurrence_pressure = bool(
        external_status in {"catalogued", "likely_catalogued"}
        or verified_relations
    )
    return {
        "source_alignment": {
            "status": external_status,
            "origin_disposition": origin_disposition,
            "authority": "content_bound_post_freeze_source_review",
            "claim_boundary": str(alignment.get("origin_claim_boundary") or ""),
        },
        "structural_recurrence": {
            "status": expected_recurrence_status,
            "verified_relations": verified_relations,
            "authority": (
                "deterministic_host_table_replay"
                if verified_relations
                else "no_verified_structural_match"
            ),
            "claim_boundary": str(recurrence.get("claim_boundary") or ""),
        },
        "typed_residual": residual,
        "recurrence_pressure": recurrence_pressure,
        "outer_objective_credit": (
            "withheld_pending_distinct_residual"
            if recurrence_pressure
            else "unchanged_pending_destination_replay"
        ),
        "current_program_policy": (
            "preserve_as_context_no_terminal_credit"
            if recurrence_pressure
            else "eligible_for_distinct_replayed_prediction"
        ),
        "source_identity_visibility": "withheld",
    }


def _post_freeze_mechanism_route_event(
    directory: str | Path, feedback: Mapping[str, Any], event: str
) -> None:
    from ztare.common.schema_routes import append_schema_route_event

    append_schema_route_event(
        directory,
        schema_id=str(feedback.get("schema") or ""),
        event=event,
        join_values={
            "context_hash": feedback["context_hash"],
            "interpretation_sha256": feedback["interpretation_sha256"],
        },
        payload={"feedback_receipt_sha256": feedback["receipt_sha256"]},
    )


def consume_post_freeze_interpretation_for_search(
    attempt_dir: str | Path,
    literature_receipt: Mapping[str, Any],
    interpretation: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Expose grounded mechanism/recurrence pressure without choosing a move."""

    directory = Path(attempt_dir)
    interpretation_core = {
        key: value for key, value in interpretation.items() if key != "receipt_sha256"
    }
    interpretation_sha = str(interpretation.get("receipt_sha256") or "")
    literature_core = {
        key: value for key, value in literature_receipt.items()
        if key != "receipt_sha256"
    }
    if (
        not interpretation_sha
        or interpretation_sha != content_hash(interpretation_core)
        or literature_receipt.get("receipt_sha256") != content_hash(literature_core)
        or interpretation.get("literature_receipt_sha256")
        != literature_receipt.get("receipt_sha256")
    ):
        raise ValueError("post-freeze mechanism inputs do not replay")
    mechanism = interpretation.get("mechanism_characterization")
    mechanism = dict(mechanism) if isinstance(mechanism, Mapping) else {}
    transport = mechanism.get("transportable_constraint")
    grounded_mechanism = bool(
        mechanism.get("status") == "proposed_grounded"
        and isinstance(transport, Mapping)
        and str(transport.get("abstract_form") or "").strip()
    )
    research_disposition = _post_freeze_research_disposition(
        literature_receipt, interpretation
    )
    if not grounded_mechanism and not (
        research_disposition and research_disposition["recurrence_pressure"]
    ):
        return None

    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        return None
    run_core = {key: value for key, value in run.items() if key != "run_digest"}
    if run.get("run_digest") != content_hash(run_core):
        raise ValueError("post-freeze source run does not replay")
    if run.get("status") == "frontier_objective_discharged":
        return None
    context_hash = str(run.get("context_hash") or "")
    if not context_hash or interpretation.get("context_hash") != context_hash:
        return None
    navigation = dict(run.get("navigation") or {})
    existing_feedback = next(
        (
            dict(row)
            for row in reversed(navigation.get("objective_review_history") or ())
            if isinstance(row, Mapping)
            and row.get("schema") in _POST_FREEZE_FEEDBACK_SCHEMAS
            and row.get("interpretation_sha256") == interpretation_sha
        ),
        None,
    )
    if existing_feedback is not None:
        if read_json(
            _post_freeze_feedback_artifact_path(directory, existing_feedback), None
        ) != existing_feedback:
            raise ValueError("post-freeze mechanism feedback artifact changed")
        _post_freeze_mechanism_route_event(
            directory, existing_feedback, "materialized"
        )
        return existing_feedback
    if not _objective_candidate_lineages(navigation):
        return None
    blueprint = FrontierTheoryBlueprint.from_json(
        read_json(directory / "blueprint.json", {})
    )
    objective = frontier_objective_contract(blueprint)
    if objective is None:
        return None
    reviewed_presentation, lineage_ids, program_ids = (
        _post_freeze_lineage_binding(
            navigation,
            interpretation,
            context_hash=context_hash,
        )
    )
    context_epoch = int(
        navigation.get(
            "context_epoch", (run.get("context_summary") or {}).get("context_epoch", 0)
        )
    )
    projection = (
        {
            "constraint_class": str(transport.get("constraint_class") or ""),
            "abstract_form": str(transport.get("abstract_form") or ""),
            "invariants": dict(transport.get("invariants") or {}),
            "premise_roles": [
                dict(row) for row in mechanism.get("premise_roles") or ()
                if isinstance(row, Mapping)
            ],
            "verifier_evidence_refs": [
                str(row) for row in mechanism.get("evidence_refs") or ()
            ],
            "claim_boundary": str(mechanism.get("claim_boundary") or ""),
            "transport_authority": str(
                mechanism.get("transport_authority") or ""
            ),
        }
        if grounded_mechanism
        else None
    )
    feedback_schema = (
        _POST_FREEZE_RESEARCH_DISPOSITION_SCHEMA
        if research_disposition is not None
        else _POST_FREEZE_MECHANISM_FEEDBACK_SCHEMA
    )
    typed_residual = (
        str(research_disposition["typed_residual"])
        if research_disposition is not None
        else "transport_grounded_mechanism_under_destination_replay"
    )
    next_discriminator = {
        "distinguish_from_catalogued_result_or_change_objective": (
            "Test a distinction beyond the mapped result, request stronger source "
            "adjudication, or change the outer objective."
        ),
        "adjudicate_likely_recurrence_before_terminal_credit": (
            "Adjudicate the likely recurrence or select a prediction whose identity "
            "does not depend on it."
        ),
        "separate_unmapped_implication_from_recurrent_finite_structure": (
            "Test the universal implication or representation residual that the "
            "verified finite relation cannot establish."
        ),
        "transport_grounded_mechanism_under_destination_replay": (
            "Choose whether the domain-stripped mechanism warrants a typed formula, "
            "a theory-language request, another boundary experiment, or abandonment."
        ),
    }[typed_residual]
    core = {
        "schema": feedback_schema,
        "context_hash": context_hash,
        "context_epoch": context_epoch,
        "source_run_digest": str(run.get("run_digest") or ""),
        "literature_receipt_sha256": str(literature_receipt["receipt_sha256"]),
        "interpretation_sha256": interpretation_sha,
        "lineage_ids": list(lineage_ids),
        "program_ids": list(program_ids),
        "reviewed_presentation_formula_ids": list(reviewed_presentation),
        "mechanism_projection": projection,
        **(
            {"research_disposition": research_disposition}
            if research_disposition is not None
            else {}
        ),
        "objective_contract": dict(objective),
        "route": "continue_search",
        "next_discriminator": next_discriminator,
        "kill_condition": (
            "Finite recurrence grants no theory or variety equivalence, and source "
            "alignment grants no terminal credit. The next move must earn a distinct "
            "typed admission and replayed consequence."
            if research_disposition is not None
            and research_disposition["recurrence_pressure"]
            else
            "Do not carry the interpretation as an axiom or theorem; the next move "
            "must earn its own typed admission and replayed consequence."
        ),
        "visibility": (
            "domain_stripped_mechanism_and_typed_recurrence_no_source_identity"
            if research_disposition is not None
            else "post_freeze_mechanism_only_no_external_alignment"
        ),
        "authority": "host_transport_of_agent_authored_proposal_only",
    }
    feedback = {**core, "receipt_sha256": content_hash(core)}
    feedback_path = _post_freeze_feedback_artifact_path(directory, feedback)
    prior = read_json(feedback_path, None)
    if isinstance(prior, Mapping) and dict(prior) != feedback:
        raise ValueError("post-freeze mechanism feedback conflicts with its source epoch")
    if prior is None:
        write_json_atomic(feedback_path, feedback)

    history = list(navigation.get("objective_review_history") or ())
    if not any(
        isinstance(row, Mapping)
        and row.get("receipt_sha256") == feedback["receipt_sha256"]
        for row in history
    ):
        history.append(feedback)
    navigation["objective_review_history"] = history
    navigation[
        "post_freeze_research_disposition"
        if feedback_schema == _POST_FREEZE_RESEARCH_DISPOSITION_SCHEMA
        else "post_freeze_mechanism_feedback"
    ] = feedback
    wave = int(navigation.get("search_wave", 0))
    suffix = f"post-freeze-wave-{wave:03d}.json"
    for name in (
        "boundary_result", "boundary_completion", "boundary_governance_recheck",
        "budget_stop_receipt", "theory_task_discharge",
        "theory_task_discharge_consumption",
    ):
        source = directory / f"{name}.json"
        if source.is_file():
            _archive_boundary_json(source, directory / f"{name}.{suffix}")
            source.unlink()

    if host_isolated_lineage_count(blueprint) == 1:
        calls = directory / "agent_calls" / "navigator"
        archived = directory / "agent_calls" / f"navigator.{suffix[:-5]}"
        if calls.exists():
            if archived.exists():
                raise ValueError("post-freeze navigator wave archive already exists")
            os.replace(calls, archived)
    checkpoint = read_json(directory / "navigation_epoch_checkpoint.json", {})
    proposal_hashes = [
        str(row)
        for row in checkpoint.get("typed_formula_proposal_sha256s") or ()
    ] if isinstance(checkpoint, Mapping) else []
    if not proposal_hashes:
        proposal_hashes = [
            TypedAxiomProposal.from_json(read_json(path, {})).content_hash
            for path in sorted(directory.glob("typed_formula_proposal.epoch-*.json"))
        ]
    checkpoint = {
        "schema": "leanmill.frontier_navigation_epoch_checkpoint.v1",
        "context_hash": context_hash,
        "context_epoch": context_epoch,
        "trace": [{
            "decision": "objective_feedback",
            "receipt": feedback,
            "host_finalized": True,
        }],
        "provider_calls": 0,
        "typed_formula_proposal_sha256s": proposal_hashes,
    }
    write_json_atomic(directory / "navigation_epoch_checkpoint.json", checkpoint)
    updated_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "status": "frontier_objective_unmet",
        "navigation": navigation,
    }
    write_json_atomic(
        directory / "run.json",
        {**updated_core, "run_digest": content_hash(updated_core)},
    )
    _post_freeze_mechanism_route_event(directory, feedback, "materialized")
    return feedback


def deliver_post_freeze_mechanism_feedback(
    attempt_dir: str | Path,
    run: Mapping[str, Any],
    *,
    context_hash: str,
) -> dict[str, Any] | None:
    """First-fire receipt for post-freeze search feedback consumption."""

    navigation = run.get("navigation")
    if not isinstance(navigation, Mapping):
        return None
    feedback = next(
        (
            dict(row)
            for row in reversed(navigation.get("objective_review_history") or ())
            if isinstance(row, Mapping)
            and row.get("schema") in _POST_FREEZE_FEEDBACK_SCHEMAS
        ),
        None,
    )
    if feedback is None:
        return None
    core = {key: value for key, value in feedback.items() if key != "receipt_sha256"}
    artifact = read_json(
        _post_freeze_feedback_artifact_path(Path(attempt_dir), feedback), None
    )
    if (
        feedback.get("receipt_sha256") != content_hash(core)
        or artifact != feedback
        or feedback.get("context_hash") != context_hash
    ):
        raise ValueError("post-freeze mechanism feedback does not replay at navigation")
    checkpoint = read_json(Path(attempt_dir) / "navigation_epoch_checkpoint.json", {})
    if not any(
        isinstance(row, Mapping)
        and row.get("decision") == "objective_feedback"
        and (row.get("receipt") or {}).get("receipt_sha256")
        == feedback["receipt_sha256"]
        for row in checkpoint.get("trace") or ()
    ):
        raise ValueError("post-freeze mechanism was not delivered to the navigator trace")
    _post_freeze_mechanism_route_event(attempt_dir, feedback, "first_fire")
    return feedback


def _external_science_trace_is_for_lineage(
    row: Mapping[str, Any], lineage_id: str, theory_program_id: str
) -> bool:
    if row.get("decision") not in {
        "external_science_resume_context",
        "external_science_negative_disposition",
    }:
        return True
    receipt = row.get("receipt")
    return (
        isinstance(receipt, Mapping)
        and receipt.get("lineage_id") == lineage_id
        and receipt.get("theory_program_id") == theory_program_id
    )


def _external_science_route_first_fired(
    directory: Path,
    *,
    artifact_name: str,
    schema: str,
    join_values: Mapping[str, str],
) -> bool:
    path = directory / "workspace" / artifact_name
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(row, Mapping)
            and row.get("schema") == schema
            and row.get("event") == "first_fire"
            and all(row.get(key) == value for key, value in join_values.items())
        ):
            return True
    return False


def _pending_external_science_admission(
    directory: Path, run: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    from ztare.leanmill.external_science_admission import (
        validate_consumed_external_science_resume_context,
        validate_delivered_external_science_resume_context,
    )

    navigation = run.get("navigation") if isinstance(run, Mapping) else None
    navigation = navigation if isinstance(navigation, Mapping) else {}
    delivered = navigation.get("external_science_resume_context_by_lineage")
    delivered = delivered if isinstance(delivered, Mapping) else {}
    pending: list[dict[str, Any]] = []
    for path in sorted(directory.glob("external_science_resume_admission.*.json")):
        row = read_json(path, None)
        if not isinstance(row, Mapping):
            continue
        lineage_id = str(row.get("lineage_id") or "")
        current = delivered.get(lineage_id)
        first_fired = _external_science_route_first_fired(
            directory,
            artifact_name="external_science_resume_context_routes.jsonl",
            schema="leanmill.external_science_resume_context.v1",
            join_values={
                "context_hash": str(row.get("context_hash") or ""),
                "admission_sha256": str(row.get("admission_sha256") or ""),
            },
        )
        if first_fired:
            resume = read_json(
                directory
                / (
                    "external_science_resume_context."
                    + str(row.get("admission_sha256") or "")[:16]
                    + ".json"
                ),
                None,
            )
            if not isinstance(resume, Mapping):
                raise ValueError(
                    "first-fired external science admission lost its resume context"
                )
            validate_consumed_external_science_resume_context(
                directory,
                admission=row,
                resume_context=resume,
            )
            continue
        if (
            isinstance(current, Mapping)
            and current.get("formal_statement_sha256")
            == row.get("formal_statement_sha256")
            and current.get("semantic_projection_sha256")
            == row.get("semantic_projection_sha256")
            and current.get("theory_program_id") == row.get("theory_program_id")
        ):
            # Materialization without first-fire remains pending.
            pass
        pending.append(dict(row))
    if len(pending) > 1:
        raise ValueError(
            "multiple external science admissions require an explicit batch transition"
        )
    return pending[0] if pending else None


def _pending_external_science_negative_disposition(
    directory: Path, run: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    from ztare.leanmill.external_science_admission import (
        external_science_negative_disposition_is_superseded,
        reconcile_external_science_review_supersessions,
    )

    reconcile_external_science_review_supersessions(directory)

    navigation = run.get("navigation") if isinstance(run, Mapping) else None
    navigation = navigation if isinstance(navigation, Mapping) else {}
    delivered = {
        str(row.get("receipt_sha256") or "")
        for row in navigation.get("external_science_negative_dispositions") or ()
        if isinstance(row, Mapping)
    }
    pending: list[dict[str, Any]] = []
    for path in sorted(
        directory.glob("external_science_negative_disposition.*.json")
    ):
        row = read_json(path, None)
        if not isinstance(row, Mapping) or external_science_negative_disposition_is_superseded(
            directory, row
        ):
            continue
        first_fired = _external_science_route_first_fired(
            directory,
            artifact_name="external_science_negative_disposition_routes.jsonl",
            schema="leanmill.external_science_negative_disposition.v1",
            join_values={
                "context_hash": str(row.get("context_hash") or ""),
                "receipt_sha256": str(row.get("receipt_sha256") or ""),
            },
        )
        if first_fired:
            from ztare.leanmill.external_science_admission import (
                validate_external_science_negative_disposition,
            )

            validate_external_science_negative_disposition(directory, row)
            continue
        if (
            str(row.get("receipt_sha256") or "") not in delivered
        ):
            pending.append(dict(row))
    if len(pending) > 1:
        raise ValueError(
            "multiple external science negative dispositions require batch delivery"
        )
    return pending[0] if pending else None


def deliver_external_science_negative_disposition(
    attempt_dir: str | Path,
    disposition: Mapping[str, Any],
    *,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> dict[str, Any]:
    """Insert one no-credit recovery rejection or outage into navigation."""

    directory = Path(attempt_dir).resolve()
    if _attempt_lease is None:
        with frontier_attempt_lease(
            directory, action="deliver_external_science_negative_disposition"
        ) as lease:
            return deliver_external_science_negative_disposition(
                directory, disposition, _attempt_lease=lease
            )
    from ztare.leanmill.external_science_admission import (
        mark_external_science_negative_disposition_first_fire,
        validate_external_science_negative_disposition,
    )

    run = validate_external_science_negative_disposition(directory, disposition)
    navigation = dict(run.get("navigation") or {})
    delivered = [
        dict(row)
        for row in navigation.get("external_science_negative_dispositions") or ()
        if isinstance(row, Mapping)
    ]
    if not any(
        row.get("receipt_sha256") == disposition.get("receipt_sha256")
        for row in delivered
    ):
        delivered.append(dict(disposition))
        navigation["external_science_negative_dispositions"] = delivered
        checkpoint_path = directory / "navigation_epoch_checkpoint.json"
        checkpoint = read_json(checkpoint_path, None)
        if isinstance(checkpoint, Mapping):
            if (
                checkpoint.get("context_hash") != disposition["context_hash"]
                or int(checkpoint.get("context_epoch", -1))
                != int(disposition["context_epoch"])
            ):
                raise ValueError(
                    "external science negative disposition targets a stale checkpoint"
                )
            checkpoint = dict(checkpoint)
        else:
            checkpoint = {
                "schema": "leanmill.frontier_navigation_epoch_checkpoint.v1",
                "context_hash": disposition["context_hash"],
                "context_epoch": disposition["context_epoch"],
                "provider_calls": 0,
                "typed_formula_proposal_sha256s": [
                    TypedAxiomProposal.from_json(read_json(path, {})).content_hash
                    for path in sorted(
                        directory.glob("typed_formula_proposal.epoch-*.json")
                    )
                ],
                "trace": [],
            }
        trace = [
            dict(row)
            for row in checkpoint.get("trace") or ()
            if isinstance(row, Mapping)
        ]
        if not any(
            row.get("decision") == "external_science_negative_disposition"
            and (row.get("receipt") or {}).get("receipt_sha256")
            == disposition.get("receipt_sha256")
            for row in trace
        ):
            trace.append(
                {
                    "decision": "external_science_negative_disposition",
                    "receipt": dict(disposition),
                    "host_finalized": True,
                }
            )
        checkpoint["trace"] = trace
        write_json_atomic(checkpoint_path, checkpoint)
        run_core = {
            **{key: value for key, value in run.items() if key != "run_digest"},
            "status": "frontier_leaf_decision_pending",
            "navigation": navigation,
        }
        write_json_atomic(
            directory / "run.json",
            {**run_core, "run_digest": content_hash(run_core)},
        )
        _attempt_lease.bind_epoch(
            epoch=int(disposition["context_epoch"]),
            context_hash=str(disposition["context_hash"]),
        )
    checkpoint = read_json(directory / "navigation_epoch_checkpoint.json", {})
    if not any(
        isinstance(row, Mapping)
        and row.get("decision") == "external_science_negative_disposition"
        and (row.get("receipt") or {}).get("receipt_sha256")
        == disposition.get("receipt_sha256")
        for row in checkpoint.get("trace") or ()
    ):
        raise ValueError("external science negative disposition missed navigation")
    mark_external_science_negative_disposition_first_fire(directory, disposition)
    return dict(disposition)


def deliver_external_science_resume_context(
    attempt_dir: str | Path,
    admission: Mapping[str, Any],
    *,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> dict[str, Any]:
    """Insert one reviewed recovery context into the navigator causal trace.

    This is the sole first-fire consumer.  It opens a navigation wave and never
    mutates objective credit, task-discharge, or campaign-completion state.
    """

    directory = Path(attempt_dir).resolve()
    if _attempt_lease is None:
        with frontier_attempt_lease(
            directory, action="deliver_external_science_resume_context"
        ) as lease:
            return deliver_external_science_resume_context(
                directory, admission, _attempt_lease=lease
            )
    from ztare.leanmill.external_science_admission import (
        mark_external_science_resume_context_first_fire,
        materialize_external_science_resume_context,
        validate_delivered_external_science_resume_context,
    )

    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("external science delivery requires a campaign run")
    navigation = run.get("navigation")
    if not isinstance(navigation, Mapping):
        raise ValueError("external science delivery requires navigation state")
    lineage_id = str(admission.get("lineage_id") or "")
    delivered = navigation.get("external_science_resume_context_by_lineage")
    delivered = delivered if isinstance(delivered, Mapping) else {}
    existing = delivered.get(lineage_id)
    if isinstance(existing, Mapping):
        validate_delivered_external_science_resume_context(
            directory, admission=admission, resume_context=existing
        )
        resume = dict(existing)
    else:
        resume = materialize_external_science_resume_context(
            directory, admission, _attempt_lease_token=_attempt_lease
        )
        navigation = dict(navigation)
        delivered = dict(delivered)
        delivered[lineage_id] = resume
        navigation["external_science_resume_context_by_lineage"] = delivered

        checkpoint_path = directory / "navigation_epoch_checkpoint.json"
        checkpoint = read_json(checkpoint_path, None)
        if isinstance(checkpoint, Mapping):
            if (
                checkpoint.get("context_hash") != resume["context_hash"]
                or int(checkpoint.get("context_epoch", -1))
                != int(resume["context_epoch"])
            ):
                raise ValueError(
                    "external science delivery targets a stale navigation checkpoint"
                )
            checkpoint = dict(checkpoint)
        else:
            proposal_hashes = [
                TypedAxiomProposal.from_json(read_json(path, {})).content_hash
                for path in sorted(
                    directory.glob("typed_formula_proposal.epoch-*.json")
                )
            ]
            checkpoint = {
                "schema": "leanmill.frontier_navigation_epoch_checkpoint.v1",
                "context_hash": resume["context_hash"],
                "context_epoch": resume["context_epoch"],
                "provider_calls": 0,
                "typed_formula_proposal_sha256s": proposal_hashes,
                "trace": [],
            }
        trace = [
            dict(row)
            for row in checkpoint.get("trace") or ()
            if isinstance(row, Mapping)
        ]
        if not any(
            row.get("decision") == "external_science_resume_context"
            and row.get("receipt") == resume
            for row in trace
        ):
            trace.append(
                {
                    "decision": "external_science_resume_context",
                    "receipt": resume,
                    "host_finalized": True,
                }
            )
        checkpoint["trace"] = trace
        write_json_atomic(checkpoint_path, checkpoint)
        run_core = {
            **{key: value for key, value in run.items() if key != "run_digest"},
            "status": "frontier_leaf_decision_pending",
            "navigation": navigation,
        }
        write_json_atomic(
            directory / "run.json",
            {**run_core, "run_digest": content_hash(run_core)},
        )
        _attempt_lease.bind_epoch(
            epoch=int(resume["context_epoch"]),
            context_hash=str(resume["context_hash"]),
        )

    checkpoint = read_json(directory / "navigation_epoch_checkpoint.json", {})
    if not any(
        isinstance(row, Mapping)
        and row.get("decision") == "external_science_resume_context"
        and row.get("receipt") == resume
        for row in checkpoint.get("trace") or ()
    ):
        raise ValueError("external science context was not inserted into the navigator trace")
    mark_external_science_resume_context_first_fire(
        directory,
        admission_sha256=str(admission.get("admission_sha256") or ""),
        resume_context=resume,
    )
    return resume


def run_external_science_recovery_admission(
    attempt_dir: str | Path,
    *,
    source_path: str | Path,
    theorem_target: str,
    finite_witness_model_id: str,
    literature_audit_path: str | Path,
    lineage_id: str = "",
    submitted_by: str = "external-science-recovery",
    closure_ledger_path: str | Path | None = None,
    kernel_parity_ledger_path: str | Path | None = None,
    model: str = "gpt-5.5",
    reasoning_effort: str = "medium",
    repo: str | Path | None = None,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> dict[str, Any]:
    """Export, independently review, admit, and deliver recovered science."""

    directory = Path(attempt_dir).resolve()
    repository = Path.cwd().resolve() if repo is None else Path(repo).resolve()

    def artifact_ref(path_value: str | Path) -> dict[str, str]:
        path = Path(path_value).resolve()
        roots = (("attempt", directory), ("repo", repository))
        for root_name, root in roots:
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            digest = sha256_file(path)
            if digest is None:
                break
            return {
                "root": root_name,
                "path": relative.as_posix(),
                "sha256": digest,
            }
        raise ValueError("external science artifact is outside the attempt and repository")

    def resolve_ref(ref: Any) -> Path:
        if not isinstance(ref, Mapping):
            raise ValueError("external science replay lost an artifact reference")
        root = {"attempt": directory, "repo": repository}.get(str(ref.get("root")))
        relative = str(ref.get("path") or "")
        if root is None or not relative:
            raise ValueError("external science replay has an invalid artifact reference")
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("external science replay artifact escaped its root") from exc
        if sha256_file(path) != ref.get("sha256"):
            raise ValueError("external science replay artifact changed identity")
        return path

    def completion_receipt(
        admission: Mapping[str, Any],
        resume: Mapping[str, Any],
        *,
        provider_calls: int,
        replayed: bool,
    ) -> dict[str, Any]:
        core = {
            "schema": "leanmill.external_science_recovery_completion.v1",
            "admission_sha256": str(admission["admission_sha256"]),
            "resume_context_id": str(resume["resume_context_id"]),
            "review_provider_calls": int(provider_calls),
            "replayed": bool(replayed),
        }
        receipt = {**core, "receipt_sha256": content_hash(core)}
        write_json_atomic(
            directory
            / f"external_science_recovery_completion.{receipt['receipt_sha256'][:16]}.json",
            receipt,
        )
        return receipt

    def negative_completion_receipt(
        disposition: Mapping[str, Any],
        *,
        provider_calls: int,
        replayed: bool,
    ) -> dict[str, Any]:
        core = {
            "schema": "leanmill.external_science_recovery_negative_completion.v1",
            "outcome": str(disposition["outcome"]),
            "disposition_sha256": str(disposition["receipt_sha256"]),
            "review_provider_calls": int(provider_calls),
            "replayed": bool(replayed),
        }
        receipt = {**core, "receipt_sha256": content_hash(core)}
        write_json_atomic(
            directory
            / f"external_science_recovery_negative_completion.{receipt['receipt_sha256'][:16]}.json",
            receipt,
        )
        return receipt

    if _attempt_lease is None:
        with frontier_attempt_lease(
            directory, action="external_science_recovery_admission"
        ) as lease:
            return run_external_science_recovery_admission(
                directory,
                source_path=source_path,
                theorem_target=theorem_target,
                finite_witness_model_id=finite_witness_model_id,
                literature_audit_path=literature_audit_path,
                lineage_id=lineage_id,
                submitted_by=submitted_by,
                closure_ledger_path=closure_ledger_path,
                kernel_parity_ledger_path=kernel_parity_ledger_path,
                model=model,
                reasoning_effort=reasoning_effort,
                repo=repository,
                _attempt_lease=lease,
            )
    existing_admissions = [
        read_json(path, None)
        for path in sorted(
            directory.glob("external_science_resume_admission.*.json")
        )
    ]
    target_existing = [
        row
        for row in existing_admissions
        if isinstance(row, Mapping)
        and row.get("theorem_target") == theorem_target
        and (not lineage_id or row.get("lineage_id") == lineage_id)
    ]
    if len(target_existing) > 1:
        raise ValueError("external science recovery has multiple matching admissions")
    if target_existing:
        admission = dict(target_existing[0])
        request_sha = str(admission.get("request_sha256") or "")
        request = read_json(
            directory
            / f"external_science_recovery_request.{request_sha[:16]}.json",
            None,
        )
        formal_ref = (request or {}).get("formal_artifact")
        formal = read_json(resolve_ref(formal_ref), None)
        expected_source_ref = artifact_ref(source_path)
        expected_literature_ref = artifact_ref(literature_audit_path)
        if (
            not isinstance(request, Mapping)
            or not isinstance(formal, Mapping)
            or admission.get("finite_witness_model_id")
            != str(finite_witness_model_id)
            or formal.get("source") != expected_source_ref
            or request.get("literature_audit") != expected_literature_ref
            or request.get("submitted_by") != str(submitted_by).strip()
        ):
            raise ValueError(
                "existing external science admission does not match requested artifact identity"
            )
        resume = deliver_external_science_resume_context(
            directory, admission, _attempt_lease=_attempt_lease
        )
        return completion_receipt(
            admission, resume, provider_calls=0, replayed=True
        )

    definition, _blueprint, budget_row, campaign, context = _load_campaign_attempt(
        directory
    )
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping) or not isinstance(run.get("navigation"), Mapping):
        raise ValueError("external science recovery requires a campaign run")
    navigation = run["navigation"]
    current_programs: dict[str, TheoryProgram] = {}
    for collection in ("finalists", "objective_survivors"):
        for candidate in navigation.get(collection) or ():
            if not isinstance(candidate, Mapping):
                continue
            try:
                program = TheoryProgram.from_json(candidate.get("theory_program"))
            except (TypeError, ValueError):
                continue
            current_programs[program.lineage_id] = program
    selected_lineage = str(lineage_id).strip()
    if selected_lineage:
        program = current_programs.get(selected_lineage)
    elif len(current_programs) == 1:
        program = next(iter(current_programs.values()))
        selected_lineage = program.lineage_id
    else:
        program = None
    if program is None:
        raise ValueError("external science recovery requires one current theory lineage")

    models = {
        str(record.model_id): record
        for record in getattr(getattr(context, "universe", None), "models", ())
    }
    model_record = models.get(str(finite_witness_model_id))
    if model_record is None:
        raise ValueError("external science recovery witness is outside the context")

    from ztare.leanmill.external_science_admission import (
        EXTERNAL_SCIENCE_REQUEST_SCHEMA,
        _formal_statement,
        _mapping_audit_context,
        admit_external_science_recovery,
        external_science_review_prompt,
        materialize_external_science_formal_evidence,
        materialize_external_science_review_execution,
        persist_external_science_review_request_core,
        record_external_science_review_rejection,
        record_external_science_reviewer_unavailability,
    )

    source = Path(source_path).resolve()
    literature = Path(literature_audit_path).resolve()
    closure_ledger = (
        repository / "analytics/public/queries/adhoc_closure_certificates.jsonl"
        if closure_ledger_path is None
        else Path(closure_ledger_path).resolve()
    )
    parity_ledger = (
        repository / "analytics/public/queries/kernel_parity.jsonl"
        if kernel_parity_ledger_path is None
        else Path(kernel_parity_ledger_path).resolve()
    )
    formal_ref = materialize_external_science_formal_evidence(
        directory,
        source_path=source,
        theorem_target=theorem_target,
        closure_ledger_path=closure_ledger,
        kernel_parity_ledger_path=parity_ledger,
        repo_root=repository,
        _attempt_lease_token=_attempt_lease,
    )
    source_text = source.read_text(encoding="utf-8")
    statement = _formal_statement(source_text, theorem_target)
    statement_sha = content_hash({"formal_statement": statement})
    role = frontier_agent_role(
        definition,
        role_name="external_science_reviewer",
        repo=repository,
        artifact_dir=directory / "agent_calls",
    )
    mapping_audit = _mapping_audit_context(
        context=context,
        reviewed_presentation_formula_ids=list(program.presentation_formula_ids),
        source_text=source_text,
        theorem_target=theorem_target,
        formal_statement=statement,
    )
    request_core = {
        "schema": EXTERNAL_SCIENCE_REQUEST_SCHEMA,
        "attempt_id": directory.name,
        "campaign_id": str((campaign.get("packet") or {}).get("campaign_id") or ""),
        "campaign_packet_digest": str(campaign.get("packet_digest") or ""),
        "run_digest": str(run.get("run_digest") or ""),
        "context_hash": str(run.get("context_hash") or ""),
        "context_epoch": int(navigation.get("context_epoch", 0)),
        "lineage_id": selected_lineage,
        "theory_program_id": program.program_id,
        "reviewed_presentation_formula_ids": list(program.presentation_formula_ids),
        "finite_witness": {
            "model_id": model_record.model_id,
            "model_table_sha256": content_hash(model_record.model.to_json()),
        },
        "formal_artifact": formal_ref,
        "literature_audit": artifact_ref(literature),
        "submitted_by": str(submitted_by).strip(),
        "reviewer_ref": role.agent_id,
    }
    prompt = external_science_review_prompt(
        request_core_sha256=content_hash(request_core),
        formal_statement=statement,
        formal_statement_sha256=statement_sha,
        reviewed_presentation_formula_ids=list(program.presentation_formula_ids),
        anonymous_witness=model_record.model.to_json(),
        submitted_by=request_core["submitted_by"],
        reviewer_ref=role.agent_id,
        mapping_audit_context=mapping_audit,
    )
    from ztare.common.llm_runtime import subscription_model_route

    resolved_runtime, resolved_model = subscription_model_route(
        model, requested_runtime=role.config.runtime
    )
    role.config = replace(
        role.config,
        runtime=resolved_runtime,
        model=resolved_model,
        reasoning_effort=reasoning_effort,
        visible_workbench=False,
        web_research=False,
        governed_pool=False,
        allow_subscription_failover=False,
    )
    prompt_digest = content_hash({"prompt": prompt})

    budget = ExplorationBudget.from_json(budget_row)
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl", budget, attempt_id=directory.name
    )
    request_core_sha = persist_external_science_review_request_core(
        directory, request_core
    )
    action_base = "external_science_review:" + request_core_sha[:16]

    def budget_rows() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        path = directory / "budget.events.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, Mapping):
                rows.append(dict(event))
        return rows

    def lifecycle_event_shas(action_id: str, reservation_id: str) -> list[str]:
        return [
            str(row["event_sha256"])
            for row in budget_rows()
            if (
                row.get("event_type") == "resources_reserved"
                and row.get("action_id") == action_id
                and row.get("reservation_id") == reservation_id
            )
            or (
                row.get("event_type")
                in {"reservation_committed", "reservation_released"}
                and row.get("reservation_id") == reservation_id
            )
        ]

    ledger.recover_interrupted_wall_clock()
    interrupted_execution_ref: Mapping[str, Any] | None = None
    for outstanding in tuple(ledger.state()["reservations"].values()):
        interrupted_action = str(outstanding.get("action_id") or "")
        if not interrupted_action.startswith(action_base + ":"):
            continue
        suffix = interrupted_action.rsplit(":", 1)[-1]
        if not suffix.isdigit():
            continue
        prefix = role.artifact_dir / suffix
        reservation = BudgetReservation(
            reservation_id=str(outstanding["reservation_id"]),
            action_id=interrupted_action,
            phase=str(outstanding["phase"]),
            resources=dict(outstanding.get("resources") or {}),
        )
        dispatch_path = prefix.with_suffix(".dispatch.json")
        call_path = prefix.with_suffix(".call.json")
        if not dispatch_path.is_file():
            ledger.release(
                reservation, reason="interrupted_before_owned_dispatch"
            )
            continue
        call = read_json(call_path, None)
        if isinstance(call, Mapping):
            charged = int(call.get("provider_call_charge", 1)) >= 1
            if charged:
                ledger.commit(
                    reservation, {"provider_calls": 1, "agent_turns": 1}
                )
            else:
                ledger.release(
                    reservation, reason="interrupted_provider_free_dispatch"
                )
            continue
        from ztare.common.subscription_agent_runtime import (
            cancel_owned_dispatch_receipt,
        )

        cancel_owned_dispatch_receipt(dispatch_path)
        ledger.commit(reservation, {"provider_calls": 1, "agent_turns": 1})
        interrupted_execution_ref = materialize_external_science_review_execution(
            directory,
            request_core=request_core,
            reviewer_ref=role.agent_id,
            prompt_digest=prompt_digest,
            action_id=interrupted_action,
            outcome="reviewer_transport_unavailable",
            role_call_path=None,
            owned_dispatch_path=dispatch_path,
            transport_provenance_path=None,
            budget_reservation_id=reservation.reservation_id,
            budget_event_sha256s=lifecycle_event_shas(
                interrupted_action, reservation.reservation_id
            ),
        )
        break
    ledger.recover_interrupted_reservations()
    ledger.resume_wall_clock()
    role.budget_ledger = ledger
    usage_before = int(ledger.state()["usage"]["provider_calls"])
    review_result: Mapping[str, Any] | None = None
    unavailable_outcome = ""
    unavailable_error: BudgetExceeded | None = None
    dispatch_reservations: dict[str, BudgetReservation] = {}
    dispatch_calls: list[dict[str, Any]] = []

    def before_dispatch(_runtime: str, _command: tuple[str, ...]):
        index = len(role.calls)
        action_id = f"{action_base}:{index:03d}"
        reservation = ledger.reserve(
            action_id,
            "interpretation",
            {"provider_calls": 1, "agent_turns": 1},
        )
        dispatch_reservations[action_id] = reservation
        return reservation

    def unused_after_dispatch(_reservation: Any) -> None:
        raise RuntimeError("external science dispatch requires result-aware settlement")

    def settle_dispatch(reservation: BudgetReservation, result: Any) -> bool:
        from ztare.leanmill.frontier_agent_runtime import _provider_call_charge

        charged = bool(result is not None and _provider_call_charge(result) >= 1)
        if charged:
            ledger.commit(
                reservation, {"provider_calls": 1, "agent_turns": 1}
            )
        else:
            ledger.release(reservation, reason="reviewer_dispatch_not_charged")
        return charged

    if interrupted_execution_ref is not None:
        unavailable_outcome = "reviewer_transport_unavailable"
    try:
        if interrupted_execution_ref is None:
            from ztare.common.llm_runtime import subscription_reasoning_effort
            from ztare.common.subscription_agent_runtime import (
                subscription_dispatch_provenance_scope,
            )

            native_effort = subscription_reasoning_effort(
                role.config.runtime,
                role.config.reasoning_effort,
                model=role.config.model,
            )
            if native_effort is None:
                raise ValueError("external science reviewer effort is unsupported")
            config_sha = content_hash(
                {
                    "runtime": role.config.runtime,
                    "model": role.config.model,
                    "reasoning_effort": role.config.reasoning_effort,
                    "timeout_seconds": role.config.timeout_seconds,
                    "visible_workbench": role.config.visible_workbench,
                    "web_research": role.config.web_research,
                    "governed_pool": role.config.governed_pool,
                    "allow_subscription_failover": role.config.allow_subscription_failover,
                }
            )
            with subscription_dispatch_provenance_scope(
                artifact_dir=role.artifact_dir / "transport",
                role="external_science_reviewer",
                agent_id=role.agent_id,
                run_tag=f"{directory.name}:{action_base}",
                runtime=role.config.runtime,
                model=role.config.model,
                reasoning_effort=native_effort,
                config_sha256=config_sha,
            ) as dispatch_calls, subscription_dispatch_budget_scope(
                before_dispatch=before_dispatch,
                after_dispatch=unused_after_dispatch,
                settle_dispatch=settle_dispatch,
            ):
                compatible_call = getattr(
                    role, "call_with_compatible_prompts", None
                )
                review_result = (
                    compatible_call(prompt, ())
                    if callable(compatible_call)
                    else role(prompt)
                )
    except BudgetExceeded as exc:
        unavailable_outcome = "reviewer_budget_unavailable"
        unavailable_error = exc
    except RuntimeError:
        unavailable_outcome = "reviewer_transport_unavailable"
    finally:
        ledger.freeze_wall_clock(reason="external_science_review_exit")
    provider_calls_used = max(
        0, int(ledger.state()["usage"]["provider_calls"]) - usage_before
    )
    if unavailable_outcome:
        execution_ref = interrupted_execution_ref
        if execution_ref is None and unavailable_outcome == "reviewer_budget_unavailable":
            reason = (
                unavailable_error.reason
                if unavailable_error is not None
                else "blocked_before_action:provider_calls"
            )
            stop = ledger.stop_receipt(reason, context_hash=str(run["context_hash"]))
            stop_event = next(
                row
                for row in reversed(budget_rows())
                if row.get("event_type") == "budget_stopped"
                and (row.get("receipt") or {}).get("receipt_sha256")
                == stop.to_json()["receipt_sha256"]
            )
            execution_ref = materialize_external_science_review_execution(
                directory,
                request_core=request_core,
                reviewer_ref=role.agent_id,
                prompt_digest=prompt_digest,
                action_id=f"{action_base}:{len(role.calls):03d}",
                outcome=unavailable_outcome,
                role_call_path=None,
                owned_dispatch_path=None,
                transport_provenance_path=None,
                budget_reservation_id="",
                budget_event_sha256s=[str(stop_event["event_sha256"])],
            )
        elif execution_ref is None:
            failed_paths = [
                path
                for path in sorted(role.artifact_dir.glob("*.call.json"))
                if (read_json(path, {}) or {}).get("prompt_digest") == prompt_digest
            ]
            if not failed_paths:
                raise ValueError("reviewer transport failure lacks a durable role call")
            failed_call_path = failed_paths[-1]
            failed_index = failed_call_path.stem.split(".", 1)[0]
            failed_action = f"{action_base}:{failed_index}"
            failed_call = read_json(failed_call_path, {})
            matching_reservation = next(
                (
                    row
                    for row in budget_rows()
                    if row.get("event_type") == "resources_reserved"
                    and row.get("action_id") == failed_action
                ),
                None,
            )
            if not isinstance(matching_reservation, Mapping):
                raise ValueError("reviewer transport failure lacks a reservation")
            provenance_path = next(
                (
                    Path(str(row.get("artifact_path") or ""))
                    for row in dispatch_calls
                    if row.get("reservation_action_id") == failed_action
                    and row.get("returncode") == failed_call.get("returncode")
                ),
                None,
            )
            if provenance_path is None:
                raise ValueError("reviewer transport failure lacks process provenance")
            reservation_id = str(matching_reservation["reservation_id"])
            execution_ref = materialize_external_science_review_execution(
                directory,
                request_core=request_core,
                reviewer_ref=role.agent_id,
                prompt_digest=prompt_digest,
                action_id=failed_action,
                outcome=unavailable_outcome,
                role_call_path=failed_call_path,
                owned_dispatch_path=(
                    failed_call_path.parent / f"{failed_index}.dispatch.json"
                ),
                transport_provenance_path=provenance_path,
                budget_reservation_id=reservation_id,
                budget_event_sha256s=lifecycle_event_shas(
                    failed_action, reservation_id
                ),
            )
        disposition = record_external_science_reviewer_unavailability(
            directory,
            review_execution=execution_ref,
            _attempt_lease_token=_attempt_lease,
        )
        delivered_negative = deliver_external_science_negative_disposition(
            directory, disposition, _attempt_lease=_attempt_lease
        )
        return negative_completion_receipt(
            delivered_negative,
            provider_calls=provider_calls_used,
            replayed=False,
        )
    if not isinstance(review_result, Mapping):
        raise ValueError("external science reviewer returned no typed result")
    successful_call_paths = []
    for candidate in sorted(role.artifact_dir.glob("*.call.json")):
        call = read_json(candidate, None)
        if (
            isinstance(call, Mapping)
            and call.get("role") == "external_science_reviewer"
            and call.get("prompt_digest") == prompt_digest
            and call.get("returncode") == 0
            and type(call.get("provider_call_charge")) is int
            and int(call["provider_call_charge"]) >= 1
        ):
            successful_call_paths.append(candidate)
    if len(successful_call_paths) != 1:
        raise ValueError(
            "external science review requires one durable successful reviewer call"
        )
    call_path = successful_call_paths[0]
    review_ref = artifact_ref(call_path)
    call_index = call_path.stem.split(".", 1)[0]
    successful_action = f"{action_base}:{call_index}"
    provenance_rows = list(dispatch_calls)
    for path in sorted((role.artifact_dir / "transport").glob("*.json")):
        row = read_json(path, None)
        if isinstance(row, Mapping) and not any(
            existing.get("receipt_sha256") == row.get("receipt_sha256")
            for existing in provenance_rows
        ):
            provenance_rows.append(dict(row))
    provenance_path = next(
        (
            Path(str(row.get("artifact_path") or ""))
            for row in provenance_rows
            if row.get("reservation_action_id") == successful_action
            and row.get("returncode") == 0
        ),
        None,
    )
    if provenance_path is None:
        raise ValueError("external science review lacks process provenance")
    provenance = read_json(provenance_path, None)
    reservation_id = str((provenance or {}).get("reservation_id") or "")
    reserve_event = next(
        (
            row
            for row in budget_rows()
            if row.get("event_type") == "resources_reserved"
            and row.get("action_id") == successful_action
            and row.get("reservation_id") == reservation_id
        ),
        None,
    )
    if not isinstance(reserve_event, Mapping):
        raise ValueError("external science review lacks its budget reservation")
    execution_ref = materialize_external_science_review_execution(
        directory,
        request_core=request_core,
        reviewer_ref=role.agent_id,
        prompt_digest=prompt_digest,
        action_id=successful_action,
        outcome="review_completed",
        role_call_path=call_path,
        owned_dispatch_path=call_path.parent / f"{call_index}.dispatch.json",
        transport_provenance_path=provenance_path,
        budget_reservation_id=reservation_id,
        budget_event_sha256s=lifecycle_event_shas(
            successful_action, reservation_id
        ),
    )
    request_without_digest = {
        **request_core,
        "independent_review": review_ref,
        "independent_review_execution": execution_ref,
    }
    request = {
        **request_without_digest,
        "request_sha256": content_hash(request_without_digest),
    }
    if (
        review_result.get("decision") != "admit_for_resume_context"
        or review_result.get("finite_witness_relevance")
        != "statement_reviewed_against_preserved_witness"
    ):
        disposition = record_external_science_review_rejection(
            directory,
            request,
            repo_root=repository,
            _attempt_lease_token=_attempt_lease,
        )
        delivered_negative = deliver_external_science_negative_disposition(
            directory, disposition, _attempt_lease=_attempt_lease
        )
        return negative_completion_receipt(
            delivered_negative,
            provider_calls=provider_calls_used,
            replayed=False,
        )
    admission = admit_external_science_recovery(
        directory,
        request,
        repo_root=repository,
        _attempt_lease_token=_attempt_lease,
    )
    resume = deliver_external_science_resume_context(
        directory, admission, _attempt_lease=_attempt_lease
    )
    return completion_receipt(
        admission,
        resume,
        provider_calls=provider_calls_used,
        replayed=False,
    )


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
    current_boundary = read_json(directory / "boundary_result.json", {})
    current_recheck = read_json(directory / "boundary_governance_recheck.json", {})
    current_boundary_sha = str(
        current_boundary.get("result_sha256") or ""
        if isinstance(current_boundary, Mapping)
        else ""
    )
    current_governance_sha = (
        str(current_recheck.get("receipt_sha256") or "") or None
        if isinstance(current_recheck, Mapping)
        else None
    )
    verifier_evidence_available = bool(current_boundary_sha)
    if latest is not None:
        inconclusive = (latest.get("review") or {}).get("status") == "inconclusive"
        verifier_evidence_advanced = verifier_evidence_available and (
            latest.get("boundary_result_sha256") != current_boundary_sha
            or latest.get("governance_recheck_sha256") != current_governance_sha
        )
        if not verifier_evidence_advanced and not (
            retry_inconclusive and inconclusive
        ):
            from ztare.leanmill.theory_interpretation import (
                compose_theory_interpretation,
            )
            packet = read_json(directory / "post_freeze_result_packet.json", None)
            if isinstance(packet, Mapping) and packet.get("packet_sha256") == latest.get(
                "packet_sha256"
            ):
                try:
                    interpretation = compose_theory_interpretation(packet, latest)
                except ValueError:
                    pass
                else:
                    write_json_atomic(
                        directory / "theory_interpretation.json", interpretation
                    )
                    consume_post_freeze_interpretation_for_search(
                        directory, latest, interpretation
                    )
                    return latest
    attempt_index = len(existing_rows)
    output_path = (
        directory / "post_freeze_interpretation.json"
        if attempt_index == 0
        else directory / f"post_freeze_interpretation.{attempt_index:03d}.json"
    )

    from ztare.leanmill.frontier_interpretation import (
        POST_FREEZE_RESULT_PACKET_SCHEMA,
        build_post_freeze_result_packet,
        post_freeze_literature_output_schema,
        validate_post_freeze_finite_witness_matches,
    )

    packet_path = directory / "post_freeze_result_packet.json"
    packet = read_json(packet_path, None)
    packet_matches_verifier = (
        isinstance(packet, Mapping)
        and packet
        and packet.get("schema") == POST_FREEZE_RESULT_PACKET_SCHEMA
        and (
            not verifier_evidence_available
            or (
                packet.get("boundary_result_sha256") == current_boundary_sha
                and packet.get("governance_recheck_sha256")
                == current_governance_sha
            )
        )
    )
    if packet_matches_verifier:
        packet_core = {
            key: value for key, value in packet.items() if key != "packet_sha256"
        }
        if packet.get("packet_sha256") != content_hash(packet_core):
            raise ValueError("post-freeze result packet digest mismatch")
        packet = dict(packet)
    else:
        if isinstance(packet, Mapping) and packet.get("packet_sha256"):
            write_json_atomic(
                directory
                / (
                    "post_freeze_result_packet.evidence-"
                    f"{str(packet['packet_sha256'])[:16]}.json"
                ),
                dict(packet),
            )
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
        formula_count=len(packet["formulas"]),
        premise_formula_ids=tuple(
            str(row["formula_id"])
            for row in packet["formulas"]
            if row.get("role") == "premise"
        ),
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
    ledger.recover_interrupted_reservations()
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
                    "equivalence_kind": "none",
                    "coordinate_variant_id": None,
                }
                for row in packet.get("formulas") or ()
                if isinstance(row, Mapping)
            ],
            "implication_prior_art": [],
            "recognized_theory_connections": [],
            "finite_witness_matches": [],
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
    from ztare.leanmill.theory_interpretation import compose_theory_interpretation

    def receipt_for(
        review: Mapping[str, Any],
        finite_witness_host_checks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        core = {
            "schema": "leanmill.post_freeze_interpretation.v1",
            "status": (
                "interpretation_completed"
                if review.get("status") == "completed"
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
            "finite_witness_host_checks": finite_witness_host_checks,
            "review": dict(review),
        }
        return {**core, "receipt_sha256": content_hash(core)}

    finite_witness_host_checks = validate_post_freeze_finite_witness_matches(
        packet, result
    )
    receipt = receipt_for(result, finite_witness_host_checks)
    try:
        interpretation = compose_theory_interpretation(packet, receipt)
    except ValueError as exc:
        write_json_atomic(
            directory / f"post_freeze_interpretation.rejected.{attempt_index:03d}.json",
            receipt,
        )
        receipt = receipt_for(
            unavailable_review(f"semantic contract rejected: {exc}"), []
        )
        interpretation = compose_theory_interpretation(packet, receipt)
    write_json_atomic(output_path, receipt)
    write_json_atomic(directory / "theory_interpretation.json", interpretation)
    consume_post_freeze_interpretation_for_search(
        directory, receipt, interpretation
    )
    return receipt


def _current_post_freeze_interpretation(
    directory: Path,
    run: Mapping[str, Any],
    blueprint: FrontierTheoryBlueprint,
) -> bool:
    """Whether the current boundary was interpreted and its feedback routed."""

    boundary = read_json(directory / "boundary_result.json", {})
    boundary_sha = str(boundary.get("result_sha256") or "")
    if not boundary_sha:
        return False
    governance = read_json(directory / "boundary_governance_recheck.json", {})
    governance_sha = str(governance.get("receipt_sha256") or "") or None
    paths = [directory / "post_freeze_interpretation.json"] + sorted(
        directory.glob("post_freeze_interpretation.[0-9][0-9][0-9].json")
    )
    receipt = next(
        (
            row
            for path in reversed(paths)
            if isinstance((row := read_json(path, None)), Mapping)
            and row.get("boundary_result_sha256") == boundary_sha
            and row.get("governance_recheck_sha256") == governance_sha
        ),
        None,
    )
    if receipt is None:
        return False
    receipt_core = {
        key: value for key, value in receipt.items() if key != "receipt_sha256"
    }
    if receipt.get("receipt_sha256") != content_hash(receipt_core):
        raise ValueError("post-freeze interpretation receipt digest mismatch")
    interpretation = read_json(directory / "theory_interpretation.json", None)
    if not isinstance(interpretation, Mapping):
        return False
    interpretation_core = {
        key: value
        for key, value in interpretation.items()
        if key != "receipt_sha256"
    }
    if (
        interpretation.get("receipt_sha256") != content_hash(interpretation_core)
        or interpretation.get("literature_receipt_sha256")
        != receipt.get("receipt_sha256")
    ):
        raise ValueError("theory interpretation does not replay")
    mechanism = interpretation.get("mechanism_characterization")
    mechanism = dict(mechanism) if isinstance(mechanism, Mapping) else {}
    transport = mechanism.get("transportable_constraint")
    grounded_mechanism = bool(
        mechanism.get("status") == "proposed_grounded"
        and isinstance(transport, Mapping)
        and str(transport.get("abstract_form") or "").strip()
    )
    research_disposition = _post_freeze_research_disposition(
        receipt, interpretation
    )
    feedback_required = grounded_mechanism or bool(
        research_disposition and research_disposition["recurrence_pressure"]
    )
    if (
        feedback_required
        and frontier_objective_contract(blueprint) is not None
        and run.get("status") != "frontier_objective_discharged"
    ):
        interpretation_sha = str(interpretation["receipt_sha256"])
        history = (run.get("navigation") or {}).get("objective_review_history") or ()
        return any(
            isinstance(row, Mapping)
            and row.get("schema") in _POST_FREEZE_FEEDBACK_SCHEMAS
            and row.get("interpretation_sha256") == interpretation_sha
            for row in history
        )
    return True


def _persist_terminal_obligation_receipt(
    directory: Path,
    *,
    prefix: str,
    identity: str,
    receipt: Mapping[str, Any],
) -> Path:
    """Persist one immutable obligation receipt under a stable identity path."""

    suffix = content_hash({"identity": str(identity)})[:20]
    path = directory / f"{prefix}.{suffix}.json"
    prior = read_json(path, None)
    if isinstance(prior, Mapping):
        if dict(prior) != dict(receipt):
            raise ValueError(f"{prefix} changed after first fire")
    else:
        write_json_atomic(path, dict(receipt))
    return path


def _terminal_obligation_rows(
    directory: Path, *, prefix: str, schema: str
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob(f"{prefix}.*.json")):
        row = read_json(path, None)
        if not isinstance(row, Mapping) or row.get("schema") != schema:
            raise ValueError(f"{prefix} artifact has the wrong schema")
        rows.append(dict(row))
    return tuple(rows)


def _frozen_terminal_lineage_ids(
    navigation: Mapping[str, Any],
) -> tuple[str, ...]:
    return tuple(
        str(
            candidate.get("lineage_id")
            or "legacy-program:" + candidate["program_id"]
        )
        for candidate in _objective_candidate_lineages(navigation)
    )


def _materialize_leaf_terminal_dispositions(
    directory: Path,
    run: Mapping[str, Any],
) -> None:
    """Project registered leaf disposition actions into terminal receipts.

    The host validates identity and cited receipts.  The terminal state itself
    remains the leaf's explicit choice.  Supersession additionally requires a
    terminal receipt for another lineage, preventing a sibling from being
    silently discarded merely because one objective happened to close first.
    """

    from ztare.leanmill.campaign_closure_gate import (
        LINEAGE_DISPOSITION_SCHEMA,
        build_leaf_disposition_authority_receipt,
        build_lineage_disposition_receipt,
    )

    context_hash = str(run.get("context_hash") or "")
    navigation = run.get("navigation") or {}
    frozen = set(_frozen_terminal_lineage_ids(navigation))
    if not frozen:
        return
    existing_rows = _terminal_obligation_rows(
        directory,
        prefix="lineage_disposition",
        schema=LINEAGE_DISPOSITION_SCHEMA,
    )
    existing_by_lineage = {
        str(row["lineage_id"]): dict(row) for row in existing_rows
    }
    known_refs = {
        str(row["receipt_sha256"]) for row in existing_rows
    }
    for artifact_name in (
        "run.json",
        "boundary_completion.json",
        "boundary_result.json",
        "theory_interpretation.json",
        "post_freeze_literature_receipt.json",
        "external_science_admission.json",
    ):
        artifact = read_json(directory / artifact_name, None)
        stack = [artifact]
        while stack:
            value = stack.pop()
            if isinstance(value, Mapping):
                for key, item in value.items():
                    if (
                        isinstance(item, str)
                        and (
                            key.endswith("sha256")
                            or key.endswith("receipt_id")
                            or key.endswith("evidence_ref")
                        )
                    ):
                        known_refs.add(item)
                    else:
                        stack.append(item)
            elif isinstance(value, (list, tuple)):
                stack.extend(value)

    traces = [navigation.get("trace") or ()] + [
        (lineage.get("navigation") or {}).get("trace") or ()
        for lineage in navigation.get("lineages") or ()
        if isinstance(lineage, Mapping)
    ]
    for turn in (
        row for trace in traces for row in trace if isinstance(row, Mapping)
    ):
        receipt = turn.get("receipt")
        if not isinstance(receipt, Mapping):
            continue
        if receipt.get("capability_id") != "propose_lineage_disposition":
            continue
        receipt_core = {
            key: value for key, value in receipt.items() if key != "receipt_id"
        }
        receipt_id = str(receipt.get("receipt_id") or "")
        summary = receipt.get("output_summary")
        input_hashes = receipt.get("input_hashes")
        if (
            receipt.get("schema") != "leanmill.axiompack_workbench_receipt.v1"
            or receipt.get("context_hash") != context_hash
            or receipt.get("authority") != "deterministic_host"
            or receipt_id != "sha256:" + content_hash(receipt_core)
            or not isinstance(summary, Mapping)
            or not isinstance(input_hashes, Mapping)
            or set(input_hashes)
            != {"terminal_state", "reason", "evidence_refs"}
            or summary.get("status")
            != "terminal_lineage_disposition_proposed"
            or summary.get("reason_sha256")
            != input_hashes.get("reason")
            or input_hashes.get("terminal_state")
            != "sha256:" + content_hash(summary.get("terminal_state"))
            or input_hashes.get("evidence_refs")
            != "sha256:" + content_hash(summary.get("evidence_refs"))
        ):
            raise ValueError("leaf terminal-disposition receipt changed identity")
        lineage_id = str(summary.get("lineage_id") or "")
        terminal_state = str(summary.get("terminal_state") or "")
        evidence_refs = tuple(
            str(value) for value in summary.get("evidence_refs") or ()
        )
        if lineage_id not in frozen or terminal_state not in {
            "rejected",
            "superseded",
        }:
            raise ValueError("leaf disposition crossed the frozen lineage set")
        if not evidence_refs or not set(evidence_refs) <= known_refs:
            raise ValueError("leaf disposition cites unrecognized campaign evidence")
        if terminal_state == "superseded" and not any(
            other_lineage != lineage_id
            and str(other["receipt_sha256"]) in set(evidence_refs)
            for other_lineage, other in existing_by_lineage.items()
        ):
            raise ValueError(
                "leaf supersession requires another lineage's terminal receipt"
            )
        authority_receipt = build_leaf_disposition_authority_receipt(receipt)
        disposition = build_lineage_disposition_receipt(
            context_hash=context_hash,
            lineage_id=lineage_id,
            terminal_state=terminal_state,
            evidence_refs=(*evidence_refs, receipt_id),
            authority="leaf_authored_workbench_disposition_host_validated",
            authority_receipt=authority_receipt,
        )
        _persist_terminal_obligation_receipt(
            directory,
            prefix="lineage_disposition",
            identity=lineage_id,
            receipt=disposition,
        )
        existing_by_lineage[lineage_id] = disposition
        known_refs.add(str(disposition["receipt_sha256"]))


def _materialize_declared_generalization_residuals(
    directory: Path,
    run: Mapping[str, Any],
) -> None:
    """Recover finite-witness obligations directly from frozen task contracts."""

    from ztare.leanmill.campaign_closure_gate import (
        GENERALIZATION_RESIDUAL_SCHEMA,
        build_generalization_residual_receipt,
    )
    from ztare.leanmill.formal_task_boundary import formal_task_parameters

    existing = {
        str(row["residual_id"])
        for row in _terminal_obligation_rows(
            directory,
            prefix="generalization_residual",
            schema=GENERALIZATION_RESIDUAL_SCHEMA,
        )
    }
    navigation = run.get("navigation") or {}
    for candidate in _objective_candidate_lineages(navigation):
        representative = candidate.get("representative") or {}
        program_row = representative.get("theory_program")
        if not isinstance(program_row, Mapping):
            continue
        program = TheoryProgram.from_json(program_row)
        for contract in program.task_discharge_contracts:
            try:
                parameters = formal_task_parameters(contract)
            except (KeyError, TypeError, ValueError):
                continue
            declared = parameters.get("generalization_residual")
            if not isinstance(declared, Mapping):
                continue
            residual = build_generalization_residual_receipt(
                context_hash=str(parameters["context_hash"]),
                lineage_id=program.lineage_id,
                witness_id=str(declared["witness_id"]),
                claim_id=str(declared["claim_id"]),
                evidence_refs=tuple(
                    str(value) for value in declared["evidence_refs"]
                )
                + (contract.sha256,),
            )
            if residual["residual_id"] in existing:
                continue
            _persist_terminal_obligation_receipt(
                directory,
                prefix="generalization_residual",
                identity=str(residual["residual_id"]),
                receipt=residual,
            )
            existing.add(str(residual["residual_id"]))


def _materialize_unresolved_terminal_dispositions(
    directory: Path,
    run: Mapping[str, Any],
    *,
    evidence: Mapping[str, Any],
) -> None:
    """Turn an authoritative budget/retirement stop into unresolved dispositions."""

    from ztare.leanmill.campaign_closure_gate import (
        LINEAGE_DISPOSITION_SCHEMA,
        lineage_disposition_from_terminal_transition,
    )

    lineages = _frozen_terminal_lineage_ids(run.get("navigation") or {})
    if not lineages:
        return
    existing = {
        str(row["lineage_id"])
        for row in _terminal_obligation_rows(
            directory,
            prefix="lineage_disposition",
            schema=LINEAGE_DISPOSITION_SCHEMA,
        )
    }
    for lineage_id in lineages:
        if lineage_id in existing:
            continue
        try:
            receipt = lineage_disposition_from_terminal_transition(
                context_hash=str(run.get("context_hash") or ""),
                lineage_id=lineage_id,
                transition_receipt=evidence,
            )
        except ValueError:
            # A mutable run snapshot is not a retirement authority.  Leave the
            # obligation open until a registered stop receipt exists.
            return
        _persist_terminal_obligation_receipt(
            directory,
            prefix="lineage_disposition",
            identity=lineage_id,
            receipt=receipt,
        )


def _campaign_terminal_obligation_gate(
    directory: Path, run: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Materialize the gate used by every candidate-bearing stop transition."""

    from ztare.leanmill.campaign_closure_gate import (
        GENERALIZATION_ADJUDICATION_SCHEMA,
        GENERALIZATION_RESIDUAL_SCHEMA,
        LINEAGE_DISPOSITION_SCHEMA,
        campaign_closure_gate,
    )

    lineages = _frozen_terminal_lineage_ids(run.get("navigation") or {})
    if not lineages:
        return None
    _materialize_declared_generalization_residuals(directory, run)
    _materialize_leaf_terminal_dispositions(directory, run)
    receipt = campaign_closure_gate(
        context_hash=str(run.get("context_hash") or ""),
        frozen_lineage_ids=lineages,
        lineage_dispositions=_terminal_obligation_rows(
            directory,
            prefix="lineage_disposition",
            schema=LINEAGE_DISPOSITION_SCHEMA,
        ),
        generalization_residuals=_terminal_obligation_rows(
            directory,
            prefix="generalization_residual",
            schema=GENERALIZATION_RESIDUAL_SCHEMA,
        ),
        generalization_adjudications=_terminal_obligation_rows(
            directory,
            prefix="generalization_adjudication",
            schema=GENERALIZATION_ADJUDICATION_SCHEMA,
        ),
    )
    write_json_atomic(directory / "campaign_closure_gate.json", receipt)
    return receipt


def _open_terminal_obligation_feedback(
    directory: Path, run: Mapping[str, Any]
) -> dict[str, Any]:
    """Return missing terminal receipts to navigation as typed input."""

    gate = _campaign_terminal_obligation_gate(directory, run)
    if not isinstance(gate, Mapping) or gate.get("ready") is True:
        return dict(run)
    from ztare.leanmill.campaign_closure_gate import LINEAGE_DISPOSITION_SCHEMA

    existing_dispositions = [
        {
            "lineage_id": str(row["lineage_id"]),
            "terminal_state": str(row["terminal_state"]),
            "receipt_sha256": str(row["receipt_sha256"]),
            "authority": str(row["authority"]),
        }
        for row in _terminal_obligation_rows(
            directory,
            prefix="lineage_disposition",
            schema=LINEAGE_DISPOSITION_SCHEMA,
        )
    ]
    navigation = dict(run.get("navigation") or {})
    core = {
        "schema": "leanmill.terminal_obligation_feedback.v1",
        "context_hash": str(run.get("context_hash") or ""),
        "lineage_ids": list(gate["frozen_lineage_ids"]),
        "campaign_closure_gate_sha256": str(gate["receipt_sha256"]),
        "missing_lineage_disposition_ids": list(
            gate["missing_lineage_disposition_ids"]
        ),
        "existing_lineage_dispositions": existing_dispositions,
        "unadjudicated_generalization_residual_ids": list(
            gate["unadjudicated_generalization_residual_ids"]
        ),
        "continuation_mode": "author_or_adjudicate_terminal_obligations",
        "claim_boundary": (
            "terminal credit is withheld; choose a registered scientific task, "
            "reject or retire the lineage with evidence, or adjudicate the residual"
        ),
        "authority": "deterministic_campaign_terminal_obligation_gate",
    }
    feedback = {**core, "receipt_sha256": content_hash(core)}
    _persist_terminal_obligation_receipt(
        directory,
        prefix="terminal_obligation_feedback",
        identity=str(feedback["receipt_sha256"]),
        receipt=feedback,
    )
    history = [
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
    ]
    if not any(
        row.get("receipt_sha256") == feedback["receipt_sha256"]
        for row in history
    ):
        history.append(feedback)
    navigation["objective_review_history"] = history
    run_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "status": "frontier_objective_unmet",
        "navigation": navigation,
    }
    updated = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(directory / "run.json", updated)
    return updated


def next_frontier_campaign_action(attempt_dir: str | Path) -> str:
    """Select the next action from authoritative attempt state."""

    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("frontier lifecycle requires an active run")
    run_core = {key: value for key, value in run.items() if key != "run_digest"}
    if run.get("run_digest") != content_hash(run_core):
        raise ValueError("frontier lifecycle run digest mismatch")
    retirement = read_json(directory / "retirement.json", None)
    if isinstance(retirement, Mapping):
        _materialize_unresolved_terminal_dispositions(
            directory, run, evidence=retirement
        )
        terminal = _campaign_terminal_obligation_gate(directory, run)
        return (
            "complete"
            if not isinstance(terminal, Mapping) or terminal.get("ready") is True
            else "terminal_obligations_blocked"
        )
    pending_external_science = _pending_external_science_admission(directory, run)
    pending_external_science_negative = (
        _pending_external_science_negative_disposition(directory, run)
    )
    if (
        pending_external_science is not None
        and pending_external_science_negative is not None
    ):
        raise ValueError("conflicting external science recovery outcomes are pending")
    if (
        pending_external_science is not None
        or pending_external_science_negative is not None
    ):
        return "resume_navigation"
    status = str(run.get("status") or "")
    if status in {"frontier_leaf_decision_pending", "frontier_objective_unmet"}:
        if (
            status == "frontier_objective_unmet"
            and _objective_synthesis_budget_exhausted(directory, run)
        ):
            return "finalize_budget_stop"
        return "resume_navigation"
    if status in {
        "frontier_language_expansion_requested",
        "blocked_adapter_gap",
    }:
        if (
            status == "frontier_language_expansion_requested"
            and _stale_boundary_disposition_needs_fresh_wave(run)
        ):
            return "resume_navigation"
        return "advance_language"
    completion = read_json(directory / "boundary_completion.json", {})
    if status == "frontier_no_candidate":
        return (
            "complete"
            if completion.get("status") == "campaign_completed_no_candidate"
            else "verify_boundary"
        )
    if status in {"frontier_navigation_exhausted", "budget_stopped"}:
        stop_evidence = read_json(directory / "budget_stop_receipt.json", None)
        _materialize_unresolved_terminal_dispositions(
            directory,
            run,
            evidence=(
                stop_evidence
                if isinstance(stop_evidence, Mapping)
                else {"run_digest": str(run["run_digest"]), "status": status}
            ),
        )
        terminal = _campaign_terminal_obligation_gate(directory, run)
        return (
            "complete"
            if not isinstance(terminal, Mapping) or terminal.get("ready") is True
            else "terminal_obligations_blocked"
        )
    if status not in {
        "frontier_candidates_frozen_awaiting_boundary_approval",
        "frontier_objective_discharged",
    }:
        raise ValueError(f"frontier lifecycle has unknown run status: {status}")
    navigation = run.get("navigation") or {}
    epoch_transition = navigation.get("epoch_transition") or {}
    if (
        status == "frontier_candidates_frozen_awaiting_boundary_approval"
        and epoch_transition.get("status") == "successor_epoch_required"
    ):
        return "continue_epoch"
    blueprint = FrontierTheoryBlueprint.from_json(
        read_json(directory / "blueprint.json", {})
    )
    plan = blueprint.verification_plan
    if not _boundary_completion_covers(
        completion,
        plan,
        navigation,
        lean_requested=plan.get("conditional_lean") is True,
        isabelle_requested=plan.get("conditional_isabelle") is True,
        theory_task_requested=_registered_formal_task_executor_required(
            navigation
        ),
    ):
        return "verify_boundary"
    boundary_rows = (completion.get("boundary_result") or {}).get(
        "query_results"
    ) or ()
    if (
        boundary_rows
        and plan.get("post_freeze_interpretation") is True
        and not _current_post_freeze_interpretation(directory, run, blueprint)
    ):
        return "interpret_boundary"
    if (
        status != "frontier_objective_discharged"
        and _boundary_search_feedback(run, completion) is not None
    ):
        return "resume_navigation"
    terminal = _campaign_terminal_obligation_gate(directory, run)
    if isinstance(terminal, Mapping) and terminal.get("ready") is not True:
        return "resolve_terminal_obligations"
    return "complete"


def _frontier_lifecycle_marker(directory: Path, action: str) -> str:
    """Content marker for fixed-point detection; wall time is deliberately absent."""

    paths = [
        directory / name
        for name in (
            "run.json",
            "navigation_epoch_checkpoint.json",
            "boundary_result.json",
            "boundary_completion.json",
            "boundary_governance_recheck.json",
            "theory_interpretation.json",
            "adapter_forge_completion.json",
            "theory_language_successor_commit.json",
            "budget_stop_receipt.json",
            "campaign_closure_gate.json",
            "campaign_workbench_successor_authorization_required.json",
        )
    ]
    for pattern in (
        "external_science_resume_admission.*.json",
        "external_science_negative_disposition.*.json",
        "lineage_disposition.*.json",
        "generalization_residual.*.json",
        "generalization_adjudication.*.json",
        "terminal_obligation_feedback.*.json",
        "campaign_workbench_successor.*.json",
    ):
        paths.extend(directory.glob(pattern))
    paths.extend(
        directory.glob("post_freeze_interpretation.[0-9][0-9][0-9].json")
    )
    first_interpretation = directory / "post_freeze_interpretation.json"
    if first_interpretation.is_file():
        paths.append(first_interpretation)
    paths.extend(directory.glob("agent_calls/**/*.call.json"))
    state = [
        (
            str(path.relative_to(directory)),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in sorted(set(paths))
        if path.is_file()
    ]
    return content_hash({"action": action, "state": state})


def drive_frontier_campaign(
    attempt_dir: str | Path,
    *,
    model: str = "",
    lean_root: str | Path | None = None,
    workbench_authority_ref: str = "",
) -> Path:
    """Advance a campaign until a terminal state or semantic fixed point."""

    directory = Path(attempt_dir)
    seen: set[str] = set()
    while True:
        run = read_json(directory / "run.json", None)
        if isinstance(run, Mapping) and isinstance(run.get("navigation"), Mapping):
            navigation = run["navigation"]
            context_hash = str(run.get("context_hash") or "")
            context_epoch = int(
                navigation.get(
                    "context_epoch",
                    (run.get("context_summary") or {}).get("context_epoch", 0),
                )
            )
            candidates = [
                row
                for field in ("finalists", "objective_survivors")
                for row in navigation.get(field) or ()
                if isinstance(row, Mapping)
            ]
            if any(
                not _candidate_matches_context(
                    row,
                    context_hash=context_hash,
                    context_epoch=context_epoch,
                )
                for row in candidates
            ):
                with frontier_attempt_lease(
                    directory, action="archive_cross_context_candidates"
                ):
                    _archive_cross_context_active_candidates(
                        directory,
                        read_json(directory / "run.json", None),
                    )
                continue
        action = next_frontier_campaign_action(directory)
        marker = _frontier_lifecycle_marker(directory, action)
        if action in {"complete", "terminal_obligations_blocked"} or marker in seen:
            return directory
        seen.add(marker)
        if action == "resume_navigation":
            directory = resume_frontier_campaign_navigation(
                directory,
                workbench_authority_ref=workbench_authority_ref,
            )
        elif action == "advance_language":
            advance_frontier_language_expansion(
                directory,
                forge_fn=lambda path, _attempt_lease: execute_frontier_adapter_forge(
                    path,
                    model=model,
                    _attempt_lease=_attempt_lease,
                ),
                resume_fn=lambda path, _attempt_lease: (
                    resume_frontier_campaign_navigation(
                        path,
                        workbench_authority_ref=workbench_authority_ref,
                        _attempt_lease=_attempt_lease,
                    )
                ),
            )
        elif action == "continue_epoch":
            directory = continue_frontier_campaign_epoch(directory)
        elif action == "finalize_budget_stop":
            stop = (read_json(directory / "run.json", {}).get("navigation") or {}).get(
                "lineage_synthesis_budget_stop"
            ) or {}
            reason = str(stop.get("reason") or "blocked_before_action:provider_calls")
            directory = materialize_frontier_navigation_from_journal(
                directory,
                budget_stop_reason=reason,
            )
        elif action == "verify_boundary":
            blueprint = FrontierTheoryBlueprint.from_json(
                read_json(directory / "blueprint.json", {})
            )
            execute_frontier_campaign_verification(
                directory,
                with_lean=blueprint.verification_plan.get("conditional_lean") is True,
                with_isabelle=(
                    blueprint.verification_plan.get("conditional_isabelle") is True
                ),
                lean_root=lean_root,
                resume_search=False,
            )
        elif action == "interpret_boundary":
            definition = load_frontier_campaign_definition(
                directory / "campaign_definition.yaml"
            )
            role = frontier_agent_role(
                definition,
                role_name="post_freeze_interpreter",
                repo=Path.cwd(),
                artifact_dir=directory / "agent_calls",
            )
            run_post_freeze_literature_review(
                directory,
                model=model or role.config.model,
                reasoning_effort=role.config.reasoning_effort,
            )
        elif action == "resolve_terminal_obligations":
            run = read_json(directory / "run.json", None)
            if not isinstance(run, Mapping):
                raise ValueError("terminal-obligation feedback requires an active run")
            _open_terminal_obligation_feedback(directory, run)
        else:  # pragma: no cover - the action algebra above is closed
            raise ValueError(f"unknown frontier lifecycle action: {action}")


__all__ = [
    "FrontierAttemptLeaseBusy",
    "FrontierAttemptLeaseLost",
    "advance_frontier_language_expansion",
    "attempt_lease_status",
    "consume_post_freeze_interpretation_for_search",
    "deliver_external_science_resume_context",
    "deliver_external_science_negative_disposition",
    "deliver_post_freeze_mechanism_feedback",
    "drive_frontier_campaign",
    "execute_frontier_adapter_forge",
    "execute_frontier_campaign_verification",
    "frontier_agent_role",
    "frontier_attempt_lease",
    "frontier_attempt_work_id",
    "materialize_frontier_navigation_from_journal",
    "next_frontier_campaign_action",
    "recheck_frontier_boundary_governance",
    "run_post_freeze_literature_review",
    "run_external_science_recovery_admission",
    "resume_frontier_campaign_navigation",
    "run_frontier_campaign_definition",
]
