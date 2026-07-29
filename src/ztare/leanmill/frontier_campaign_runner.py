"""Canonical runtime door for one frontier AxiomPack campaign."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import threading
import time
import uuid
from typing import Any, Callable, Mapping, Sequence

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
    _registered_boundary_task_contracts,
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
    BudgetLedgerResourceUnavailable,
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
    make_subscription_witness_constructor,
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
    audit_lean_consequence_axioms,
    execute_governed_lean_consequence,
    recheck_governed_lean_consequence,
    render_lean_consequence_task,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_interest import CHEAP_CONSEQUENCE_EVALUATOR_REF
from ztare.leanmill.theory_language import TheoryLanguageExpansionRequest
from ztare.leanmill.theory_lineage_runner import (
    aggregate_host_isolated_theory_lineages,
    durable_navigator_turn_count,
    run_host_isolated_theory_lineages,
    theory_search_wave_image_receipt,
)
from ztare.leanmill.theory_lineage_synthesis import (
    build_theory_move_portfolio,
    compose_selected_language_expansion,
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
from ztare.leanmill.reviewed_construction_campaign import (
    ReviewedConstructionHooks,
    advance_reviewed_construction_campaign,
    bind_recovered_boundary_artifact_feedback as _bind_recovered_boundary_artifact_feedback,
    pending_cold_witness_boundary_recovery,
    recovered_boundary_feedback_disposition_program_id,
    recover_cold_witness_boundary,
)


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
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    tuple[dict[str, Any], ...],
    int,
    int,
]:
    """Load the smallest causally complete suffix of one immutable segment.

    Prompt traces are compact views: a later freeze may name a compiled task
    whose full contract existed in the host trace but was deliberately
    truncated before the next model call.  Replaying every decision from the
    first prompt loses that contract.  Start instead at the last task request
    needed by the terminal decision, then replay its suffix so the host
    deterministically reconstructs every full receipt.
    """

    calls, decisions = _read_durable_navigator_decisions(call_dir)
    if not decisions:
        return calls, decisions, (), 0, 0
    successful_calls = [
        call for call in calls if int(call.get("returncode", 1)) == 0
    ]
    if len(successful_calls) != len(decisions):
        raise ValueError("durable navigator calls and decisions lost alignment")

    start = len(decisions) - 1
    terminal = decisions[-1]
    task_ids = terminal.get("task_contract_ids")
    if terminal.get("decision") == "freeze" and isinstance(task_ids, list) and task_ids:
        start = next(
            (
                index
                for index in range(len(decisions) - 2, -1, -1)
                if decisions[index].get("decision") == "request"
                and str(decisions[index].get("capability_id") or "").split(
                    "@", 1
                )[0]
                == "propose_theory_task"
            ),
            start,
        )

    call_index = int(successful_calls[start]["artifact_index"])
    prompt_path = call_dir / f"{call_index:03d}.prompt.txt"
    if not prompt_path.is_file():
        # Compatibility for old synthetic call archives that predate frozen
        # prompts. They can replay only from the beginning of the segment.
        return calls, decisions, (), 0, 0
    marker = "\nCURRENT TRACE:\n"
    prompt = prompt_path.read_text(encoding="utf-8")
    prompt_digest = str(successful_calls[start].get("prompt_digest") or "")
    if prompt_digest and prompt_digest != content_hash({"prompt": prompt}):
        raise ValueError("durable navigator prompt digest mismatch")
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
    round_offset = max(
        (
            int(row["round"]) + 1
            for row in hydrated
            if type(row.get("round")) is int
        ),
        default=start,
    )
    return (
        calls,
        decisions[start:],
        tuple(hydrated),
        start,
        round_offset,
    )


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
    witness_constructor_fn: Any | None = None,
    candidate_outcome_memory: Mapping[str, Any] | None = None,
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
        witness_constructor_fn=witness_constructor_fn,
        candidate_outcome_memory=candidate_outcome_memory,
    )


def _durable_witness_constructor_for_navigator_segment(
    definition: FrontierCampaignDefinition,
    directory: Path,
    call_dir: Path,
) -> Any | None:
    """Rebind one completed sibling constructor to deterministic recovery.

    Directory proximity is only a discovery aid.  The subscription role and
    constructor wrapper still verify the frozen prompt, result digest, role,
    agent identity, request identity, and output schema before returning the
    authored artifact.
    """

    name = call_dir.name
    if name == "navigator":
        instance_id = ""
    elif name.startswith("navigator."):
        instance_id = name.removeprefix("navigator.")
    else:
        return None
    sibling_name = (
        "witness_constructor"
        if not instance_id
        else f"witness_constructor.{instance_id}"
    )
    sibling = directory / "agent_calls" / sibling_name
    completed: list[tuple[int, dict[str, Any]]] = []
    for index in range(1_000):
        prefix = sibling / f"{index:03d}"
        call = read_json(prefix.with_suffix(".call.json"), None)
        if not isinstance(call, Mapping):
            break
        if (
            int(call.get("returncode", 1)) == 0
            and prefix.with_suffix(".prompt.txt").is_file()
            and prefix.with_suffix(".stdout.txt").is_file()
            and prefix.with_suffix(".result.json").is_file()
        ):
            completed.append((index, dict(call)))
    if not completed:
        return None
    role = frontier_agent_role(
        definition,
        role_name="witness_constructor",
        repo=directory,
        artifact_dir=directory / "agent_calls",
        instance_id=instance_id,
    )
    constructor = make_subscription_witness_constructor(role)
    consumed: set[int] = set()

    def prompt_indexed_replay(request: Mapping[str, Any]) -> Mapping[str, Any]:
        from ztare.leanmill.witness_construction_boundary import (
            validate_witness_constructor_request,
        )

        frozen = validate_witness_constructor_request(request)
        prompt = prompts.AXIOMPACK_WITNESS_CONSTRUCTOR_PROMPT.format(
            construction_request_json=json.dumps(
                frozen, sort_keys=True, separators=(",", ":")
            )
        )
        prompt_digest = content_hash({"prompt": prompt})
        target = next(
            (
                index
                for index, call in completed
                if index not in consumed
                and call.get("prompt_digest") == prompt_digest
            ),
            None,
        )
        if target is None:
            raise ValueError(
                "durable witness constructor has no exact prompt-bound result"
            )
        if target < len(role.calls):
            raise ValueError("durable witness constructor replay order changed")
        while len(role.calls) < target:
            skipped_index = len(role.calls)
            skipped = read_json(
                sibling / f"{skipped_index:03d}.call.json", {}
            )
            role.calls.append(
                {
                    **dict(skipped),
                    "replayed": True,
                    "skipped_by_prompt_indexed_recovery": True,
                }
            )
        output = constructor(frozen)
        consumed.add(target)
        return output

    prompt_indexed_replay.call_role = role  # type: ignore[attr-defined]
    return prompt_indexed_replay


def _navigator_recovery_journal(
    directory: Path,
    call_dir: Path,
    *,
    epoch: int,
    context_hash: str,
) -> IdempotentReplayJournal:
    """Return the context-owned journal for one derived navigation replay.

    Durable call artifacts authorize reconstruction, but the events emitted
    while replaying them are a projection rather than campaign history. A
    context-scoped owner prevents a sparse set of replayed epochs from being
    mistaken for one contiguous authoritative lineage journal.
    """

    return IdempotentReplayJournal(
        directory
        / "recovery_journals"
        / (
            f"{call_dir.name}.epoch-{epoch:03d}."
            f"{context_hash[:16]}.causal-v2.events.jsonl"
        )
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
        visible_workbench=bool(
            values.get(
                "visible_workbench",
                role_name == "witness_constructor",
            )
        ),
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


def _campaign_construction_candidate_memory(
    directory: Path,
    blueprint: FrontierTheoryBlueprint,
) -> dict[str, Any] | None:
    """Project all prior exact construction outcomes for the active interface."""

    from ztare.leanmill.theory_adapter_registry import (
        theory_task_capability_catalog,
    )
    from ztare.leanmill.witness_construction_boundary import (
        GOVERNED_WITNESS_CONSTRUCTION_CAPABILITY,
        GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
        WitnessConstructionCandidateEnvelope,
        build_witness_candidate_outcome_memory,
        validate_governed_witness_construction_task_receipt,
        validate_witness_construction_interface,
        witness_construction_parameters,
    )

    interfaces = [
        row.get("interface")
        for row in theory_task_capability_catalog(
            blueprint.adapter_id,
            adapter_config=dict(blueprint.adapter_config or {}),
        )
        if row.get("capability_id")
        == GOVERNED_WITNESS_CONSTRUCTION_CAPABILITY
        and isinstance(row.get("interface"), Mapping)
    ]
    if not interfaces:
        return None
    if len(interfaces) != 1:
        raise ValueError("active adapter has ambiguous construction interfaces")
    interface = validate_witness_construction_interface(interfaces[0])

    paths = {
        path
        for path in directory.glob("theory_task_discharge*.json")
        if "consumption" not in path.name
    }
    paths.update(
        directory.glob("boundary_attempts/*/theory_task_discharge.json")
    )
    outcomes: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(paths):
        bundle = read_json(path, None)
        if not isinstance(bundle, Mapping):
            continue
        bundle_core = {
            key: item for key, item in bundle.items() if key != "receipt_sha256"
        }
        if (
            bundle.get("schema") != "leanmill.theory_task_discharge.v1"
            or bundle.get("authority")
            != "registered_adapter_receipts_host_aggregation"
            or bundle.get("receipt_sha256") != content_hash(bundle_core)
            or not isinstance(bundle.get("rows"), list)
        ):
            raise ValueError("construction outcome source bundle failed replay")
        for raw in bundle["rows"]:
            row = dict(raw)
            row_core = {
                key: item for key, item in row.items() if key != "receipt_sha256"
            }
            if row.get("receipt_sha256") != content_hash(row_core):
                raise ValueError("construction outcome row failed replay")
            contract, receipt = validate_governed_witness_construction_task_receipt(
                row.get("contract") or {}, row.get("receipt") or {}
            )
            if (
                row.get("source") != "explicit_task"
                or row.get("contract_sha256") != contract.sha256
                or contract.adjudicator_id
                != GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR
            ):
                continue
            parameters = witness_construction_parameters(contract)
            candidate = WitnessConstructionCandidateEnvelope.from_json(
                parameters["candidate_envelope"]
            )
            candidate_row = candidate.to_json()
            if (
                candidate.adapter_id != blueprint.adapter_id
                or candidate.interface_sha256 != interface["interface_sha256"]
                or candidate.target_config_sha256
                != interface["target_config_sha256"]
                or candidate_row["predicate_sha256"]
                != content_hash(interface["predicate_ir"])
            ):
                continue
            observed = receipt.observed
            verifier = (
                observed.get("verifier_observed")
                if isinstance(observed, Mapping)
                else None
            )
            status = str(
                observed.get("boundary_status")
                if isinstance(observed, Mapping)
                else ""
            )
            if status not in {
                "witness_rejected",
                "witness_verified",
                "witness_unavailable",
            }:
                continue
            if not isinstance(verifier, Mapping):
                raise ValueError("construction outcome lost verifier observations")
            outcome = {
                "source_artifact_sha256": candidate_row["artifact_sha256"],
                "normalized_artifact_sha256": str(
                    observed.get("normalized_artifact_sha256") or ""
                ),
                "boundary_status": status,
                "verifier_status": str(verifier.get("status") or ""),
                "observed": dict(verifier),
                "evidence_refs": list(
                    dict.fromkeys((contract.sha256, receipt.sha256, *receipt.evidence_refs))
                ),
            }
            key = (
                outcome["source_artifact_sha256"],
                outcome["normalized_artifact_sha256"],
            )
            prior = outcomes.get(key)
            if prior is not None:
                if (
                    prior["boundary_status"] != outcome["boundary_status"]
                    or prior["observed"] != outcome["observed"]
                ):
                    raise ValueError("construction artifact has conflicting outcomes")
                prior["evidence_refs"] = list(
                    dict.fromkeys(prior["evidence_refs"] + outcome["evidence_refs"])
                )
            else:
                outcomes[key] = outcome
    memory = build_witness_candidate_outcome_memory(
        adapter_id=blueprint.adapter_id,
        construction_interface=interface,
        outcomes=tuple(outcomes.values()),
    )
    if not memory["outcomes"]:
        return None
    path = directory / (
        "witness_candidate_outcome_memory."
        f"{memory['receipt_sha256'][:16]}.json"
    )
    prior = read_json(path, None)
    if isinstance(prior, Mapping):
        if dict(prior) != memory:
            raise ValueError("construction candidate memory changed after first fire")
    else:
        write_json_atomic(path, memory)
    return memory


def _make_campaign_theory_navigator(
    definition: FrontierCampaignDefinition,
    *,
    directory: Path,
    repo: Path,
    attempt_id: str,
) -> Any:
    """Bind either one warm trace or explicitly host-isolated lineages."""

    active_campaign = read_json(directory / "campaign.json", None)
    stable_campaign_id = (
        str((active_campaign.get("packet") or {}).get("campaign_id") or "")
        if isinstance(active_campaign, Mapping)
        else ""
    )
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
        constructor_role = frontier_agent_role(
            definition,
            role_name="witness_constructor",
            repo=directory,
            artifact_dir=directory / "agent_calls",
            instance_id=wave_instance(),
        )
        constructor = make_subscription_witness_constructor(constructor_role)
        return role, make_subscription_theory_navigator(
            role,
            attempt_id=attempt_id,
            campaign_id=stable_campaign_id,
            witness_constructor_fn=constructor,
        )

    single_role, single = make_single()
    lineage_roles: dict[int, SubscriptionJSONRole] = {}
    witness_constructor_roles: dict[int, SubscriptionJSONRole] = {}
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
        candidate_outcome_memory = _campaign_construction_candidate_memory(
            directory, blueprint
        )
        if count == 1:
            for name in (
                "initial_trace",
                "prior_agent_turns",
                "round_offset",
                "epoch",
                "prior_conflict_rows",
                "replay_decisions",
            ):
                if hasattr(navigator, name):
                    setattr(single, name, getattr(navigator, name))
            single.candidate_outcome_memory = candidate_outcome_memory  # type: ignore[attr-defined]
            result = single(
                context,
                blueprint,
                journal,
                budget_ledger=budget_ledger,
            )
            return {**dict(result), "search_wave": search_wave}
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
        if (
            reactivated
            and not reactivated_consumed
            and not isinstance(
                getattr(navigator, "objective_feedback", None), Mapping
            )
        ):
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
            witness_constructors: list[Any] = []
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
                constructor_role = witness_constructor_roles.get(index)
                if constructor_role is None:
                    constructor_role = frontier_agent_role(
                        definition,
                        role_name="witness_constructor",
                        repo=directory,
                        artifact_dir=directory / "agent_calls",
                        instance_id=wave_instance(f"lineage-{index:03d}"),
                    )
                    witness_constructor_roles[index] = constructor_role
                constructor_role.budget_ledger = budget_ledger
                witness_constructors.append(
                    make_subscription_witness_constructor(constructor_role)
                )
            preserved_rows = dict(
                getattr(navigator, "preserved_lineage_rows", {})
            )
            active_indices = [
                index for index in range(count) if index not in preserved_rows
            ]
            lineage_budget_phase = (
                _objective_feedback_search_phase(
                    getattr(navigator, "objective_feedback", None)
                )
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
                campaign_id=(
                    stable_campaign_id
                    or "campaign:"
                    + blueprint.blueprint_id.split(":", 1)[1][:24]
                ),
                max_rounds=rounds_by_lineage,
                max_finalists_per_lineage=max(1, total_finalists // count),
                budget_ledger=budget_ledger,
                epoch=epoch,
                prior_conflict_rows=tuple(getattr(navigator, "prior_conflict_rows", ())),
                initial_trace=common_trace,
                initial_traces=branch_traces,
                preserved_lineage_rows=preserved_rows,
                budget_phase=lineage_budget_phase,
                witness_constructor_fns=witness_constructors,
                candidate_outcome_memory=candidate_outcome_memory,
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
            _persist_bounded_reviewed_construction_artifact(
                _lineage_synthesis_input_owner_path(
                    directory, synthesis_input.get("input_sha256")
                ),
                synthesis_input,
                label="lineage synthesis input",
            )
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
                _objective_feedback_search_phase(objective_feedback)
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
                    **{
                        key: value
                        for key, value in result.items()
                        if key
                        not in {
                            "lineage_synthesis_budget_stop",
                            "lineage_synthesis_failure",
                        }
                    },
                    "lineage_synthesis": synthesis,
                    "lineage_synthesis_search_wave": search_wave,
                    "lineage_synthesis_frozen_program_ids": [
                        str(row.get("program_id") or "")
                        for row in synthesis_input.get("frozen_programs") or ()
                        if isinstance(row, Mapping) and row.get("program_id")
                    ],
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
        witness_constructor_roles.clear()
        synthesis_role = None
        clear_transient_lineage_state()
        single_role, single = make_single()
        navigator.call_role = single_role  # type: ignore[attr-defined]
        navigator.search_wave = search_wave  # type: ignore[attr-defined]

    navigator.begin_search_wave = begin_search_wave  # type: ignore[attr-defined]
    navigator.search_wave = search_wave  # type: ignore[attr-defined]
    navigator.search_wave = search_wave  # type: ignore[attr-defined]

    def begin_context_epoch(*, source_epoch: int, target_epoch: int) -> None:
        nonlocal search_wave, single_role, single, synthesis_role
        if target_epoch != source_epoch + 1:
            raise ValueError("navigator context epochs must advance by one")
        single_constructor = getattr(single, "witness_constructor_fn", None)
        single_constructor_role = getattr(single_constructor, "call_role", None)
        roles = [
            single_role,
            *(
                [single_constructor_role]
                if single_constructor_role is not None
                else []
            ),
            *lineage_roles.values(),
            *witness_constructor_roles.values(),
        ]
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
        witness_constructor_roles.clear()
        synthesis_role = None
        clear_transient_lineage_state()
        single_role, single = make_single()
        navigator.call_role = single_role  # type: ignore[attr-defined]
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
            "carried_evidence_receipts": list(
                synthesis_input.get("carried_evidence_receipts") or ()
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

    def initialize_attempt_signer(attempt: Path) -> None:
        """Persist recovery authority before any campaign artifact or call."""

        _write_secret(attempt / "private" / "campaign_signer.pem", private)
        write_text_atomic(attempt / "campaign_signer_public.pem", public)

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
            attempt_initializer=initialize_attempt_signer,
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


def _validated_adapter_forge_completion_row(
    value: Mapping[str, Any], *, gap_id: str
) -> dict[str, Any]:
    """Replay one base or subordinate Forge completion."""

    from ztare.leanmill.adapter_forge import (
        ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT,
        ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        _validated_adapter_forge_completion,
    )

    row = dict(value)
    host_contract = str(row.get("host_conformance_contract") or "")
    if "recovery_attempt_index" not in row:
        if host_contract not in {
            ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
            ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT,
        }:
            raise ValueError("AdapterForge completion has an unknown host contract")
        return _validated_adapter_forge_completion(
            row,
            gap_id=gap_id,
            host_conformance_contract=host_contract,
        )
    core = {
        key: item for key, item in row.items() if key != "completion_sha256"
    }
    if (
        row.get("schema") != "leanmill.adapter_forge_completion.v1"
        or row.get("gap_id") != gap_id
        or host_contract != ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT
        or row.get("completion_sha256") != content_hash(core)
    ):
        raise ValueError("AdapterForge recovery completion crossed gap identity")
    return row


def _adapter_forge_recovery_root(directory: Path, gap_id: str) -> Path:
    from ztare.leanmill.adapter_forge import adapter_forge_attempt_directory

    return adapter_forge_attempt_directory(directory, gap_id) / "recovery_attempts"


def _read_adapter_forge_lifecycle_completion(
    directory: Path,
    gap: Any,
    *,
    migrate_legacy: bool = False,
) -> dict[str, Any] | None:
    """Read the latest causally chained completion for one gap.

    The AdapterForge module owns the base gap/host-contract evaluation.  The
    campaign runner owns subordinate recovery attempts because their identity
    also includes the source epoch, workspace policy, and agent-session policy.
    """

    from ztare.leanmill.adapter_forge import read_adapter_forge_completion

    current = read_adapter_forge_completion(
        directory, gap, migrate_legacy=migrate_legacy
    )
    root = _adapter_forge_recovery_root(directory, gap.gap_id)
    candidates: dict[
        int, tuple[Path, dict[str, Any], dict[str, Any] | None]
    ] = {}
    recovery_read_budget = {"files": 0, "bytes": 0}
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    try:
        root_fd = os.open(root, directory_flags)
    except FileNotFoundError:
        root_fd = None
    except OSError as exc:
        raise ValueError("AdapterForge recovery root is unavailable") from exc
    if root_fd is not None:
        try:
            visited = 0
            with os.scandir(root_fd) as entries:
                for entry in entries:
                    visited += 1
                    if visited > _MAX_REVIEWED_CONSTRUCTION_DIRECTORY_ENTRIES:
                        raise ValueError(
                            "AdapterForge recovery directory-entry ceiling exceeded"
                        )
                    match = re.fullmatch(r"attempt-(\d+)", entry.name)
                    if match is None:
                        continue
                    if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                        raise ValueError(
                            "AdapterForge recovery owner is not a directory"
                        )
                    if (
                        len(candidates)
                        >= _MAX_REVIEWED_CONSTRUCTION_LEGACY_CANDIDATES
                    ):
                        raise ValueError(
                            "AdapterForge recovery candidate ceiling exceeded"
                        )
                    try:
                        attempt_fd = os.open(
                            entry.name,
                            directory_flags,
                            dir_fd=root_fd,
                        )
                    except OSError as exc:
                        raise ValueError(
                            "AdapterForge recovery owner is unavailable"
                        ) from exc
                    try:
                        row = _read_bounded_reviewed_construction_artifact_at(
                            attempt_fd,
                            "adapter_forge_completion.json",
                            label="AdapterForge recovery completion",
                            aggregate_budget=recovery_read_budget,
                        )
                        transition = _read_bounded_reviewed_construction_artifact_at(
                            attempt_fd,
                            "adapter_forge_recovery_transition.json",
                            label="AdapterForge recovery transition",
                            aggregate_budget=recovery_read_budget,
                        )
                    finally:
                        os.close(attempt_fd)
                    if row is None:
                        continue
                    completion = _validated_adapter_forge_completion_row(
                        row, gap_id=gap.gap_id
                    )
                    index = int(match.group(1))
                    if int(completion.get("recovery_attempt_index", -1)) != index:
                        raise ValueError(
                            "AdapterForge recovery index changed identity"
                        )
                    path = root / entry.name / "adapter_forge_completion.json"
                    owner = str(completion.get("artifact_owner") or "")
                    if owner != str(path.parent.relative_to(directory)):
                        raise ValueError(
                            "AdapterForge recovery artifact owner changed"
                        )
                    if index in candidates:
                        raise ValueError(
                            "AdapterForge recovery attempt index is ambiguous"
                        )
                    candidates[index] = (path, completion, transition)
        finally:
            os.close(root_fd)
    if current is None:
        if candidates:
            raise ValueError("AdapterForge recovery completion has no base attempt")
        return None
    current = _validated_adapter_forge_completion_row(
        current, gap_id=gap.gap_id
    )
    remaining = dict(candidates)
    while True:
        successors = [
            (index, path, candidate, transition)
            for index, (path, candidate, transition) in remaining.items()
            if candidate.get("predecessor_completion_sha256")
            == current.get("completion_sha256")
        ]
        if len(successors) > 1:
            raise ValueError("AdapterForge recovery predecessor has multiple successors")
        if not successors:
            break
        index, path, candidate, transition = successors[0]
        owner = path.parent
        if not isinstance(transition, Mapping):
            raise ValueError("AdapterForge recovery transition is missing")
        transition, _workspace = _validate_adapter_forge_recovery_transition(
            directory,
            owner=owner,
            transition=transition,
            gap=gap,
            predecessor=current,
            recovery_attempt_index=index,
            require_workspace=False,
        )
        if (
            candidate.get("recovery_transition_receipt_sha256")
            != transition.get("receipt_sha256")
            or candidate.get("recovery_transition") != transition
        ):
            raise ValueError("AdapterForge recovery transition does not replay")
        recovery_input = candidate.get("recovery_input")
        if not isinstance(recovery_input, Mapping):
            raise ValueError("AdapterForge recovery input is missing")
        input_core = {
            key: item
            for key, item in recovery_input.items()
            if key != "receipt_sha256"
        }
        if (
            recovery_input.get("receipt_sha256") != content_hash(input_core)
            or recovery_input.get("gap_id") != gap.gap_id
            or recovery_input.get("recovery_transition_receipt_sha256")
            != transition.get("receipt_sha256")
        ):
            raise ValueError("AdapterForge recovery input does not replay")
        current = candidate
        remaining.pop(index)
    return current


def _adapter_forge_artifact_owner(
    directory: Path, completion: Mapping[str, Any]
) -> Path:
    """Resolve the immutable artifact owner named by one Forge completion."""

    from ztare.leanmill.adapter_forge import adapter_forge_attempt_directory

    gap_id = str(completion.get("gap_id") or "")
    host_contract = str(completion.get("host_conformance_contract") or "")
    base = adapter_forge_attempt_directory(
        directory,
        gap_id,
        host_conformance_contract=host_contract,
    ).resolve()
    supplied = str(completion.get("artifact_owner") or "")
    if not supplied:
        return base
    owner = (directory / supplied).resolve()
    recovery_root = (base / "recovery_attempts").resolve()
    if not owner.is_relative_to(recovery_root):
        raise ValueError("AdapterForge artifact owner escaped its gap attempt")
    persisted = _read_bounded_reviewed_construction_artifact(
        owner / "adapter_forge_completion.json",
        label="AdapterForge artifact-owner completion",
    )
    if persisted is None or persisted != dict(completion):
        raise ValueError("AdapterForge artifact owner lacks the exact completion")
    return owner


def _adapter_workspace_input_manifest(workspace: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(workspace.rglob("*")):
        if path.is_symlink():
            raise ValueError("AdapterForge recovery workspace contains a symlink")
        if not path.is_file():
            continue
        rows.append(
            {
                "path": str(path.relative_to(workspace)),
                "bytes_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return rows


def _adapter_forge_frozen_input_manifest(
    workspace: Path,
) -> list[dict[str, Any]]:
    """Bind host-owned staged inputs that a coding leaf may only read."""

    frozen_names = {
        "adapter_gap.json",
        "blueprint.json",
        "context_fixture.json",
        "evidence_context.json",
        "evidence_materialization.json",
        "formal_context.json",
    }

    def is_host_contract(label: str) -> bool:
        path = Path(label)
        return (
            len(path.parts) == 1
            and path.name.endswith(("_contract.json", "_interface.json"))
        )

    return [
        row
        for row in _adapter_workspace_input_manifest(workspace)
        if (
            row["path"] in frozen_names
            or str(row["path"]).startswith("evidence/")
            or is_host_contract(str(row["path"]))
        )
    ]


def _verify_adapter_forge_frozen_inputs(
    workspace: Path, manifest: Sequence[Mapping[str, Any]]
) -> None:
    expected = {
        str(row.get("path") or ""): str(row.get("bytes_sha256") or "")
        for row in manifest
        if isinstance(row, Mapping)
    }
    if not expected:
        raise ValueError("AdapterForge frozen input manifest is empty")
    observed: dict[str, str] = {}
    for label in expected:
        candidate = workspace / label
        path = candidate.resolve()
        if (
            Path(label).is_absolute()
            or ".." in Path(label).parts
            or candidate.is_symlink()
            or not path.is_relative_to(workspace.resolve())
            or not path.is_file()
        ):
            raise ValueError("AdapterForge frozen input escaped or disappeared")
        observed[label] = hashlib.sha256(path.read_bytes()).hexdigest()
    if observed != expected:
        raise ValueError("AdapterForge coding leaf changed a frozen host input")


def _copy_adapter_workspace(source: Path, target: Path) -> None:
    """Copy an allowed workspace snapshot without carrying filesystem links."""

    if not source.is_dir():
        raise ValueError("AdapterForge structural repair workspace is absent")
    if target.exists() and any(target.iterdir()):
        raise ValueError("AdapterForge recovery workspace is already populated")
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("AdapterForge source workspace contains a symlink")
        destination = target / path.relative_to(source)
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)


def _next_adapter_forge_agent_instance(directory: Path) -> str:
    indices = []
    for role in ("adapter_forge", "adapter_reviewer"):
        for path in (directory / "agent_calls").glob(f"{role}.attempt-*"):
            suffix = path.name.rsplit("-", 1)[-1]
            if suffix.isdigit():
                indices.append(int(suffix))
    return f"attempt-{1 + max(indices, default=0):03d}"


def _adapter_forge_rejection_receipt(
    completion: Mapping[str, Any],
) -> dict[str, Any] | None:
    receipt = completion.get("quarantine_receipt")
    if not isinstance(receipt, Mapping):
        return None
    receipt_core = {
        key: item for key, item in receipt.items() if key != "receipt_sha256"
    }
    host = receipt.get("host_conformance")
    if (
        receipt.get("receipt_sha256") != content_hash(receipt_core)
        or not isinstance(host, Mapping)
        or host.get("ok") is not False
    ):
        return None
    host_core = {
        key: item for key, item in host.items() if key != "receipt_sha256"
    }
    if host.get("receipt_sha256") != content_hash(host_core):
        raise ValueError("AdapterForge host rejection receipt changed")
    return dict(host)


def _validate_adapter_forge_recovery_transition(
    directory: Path,
    *,
    owner: Path,
    transition: Mapping[str, Any],
    gap: Any,
    predecessor: Mapping[str, Any],
    recovery_attempt_index: int,
    require_workspace: bool = True,
) -> tuple[dict[str, Any], Path]:
    """Replay the gap/epoch, workspace, and session policy of one transition."""

    from ztare.leanmill.adapter_forge import (
        ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE,
        ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
    )

    rejection = _adapter_forge_rejection_receipt(predecessor)
    if rejection is None:
        raise ValueError("AdapterForge recovery predecessor is not a host rejection")
    rejection_class = str(rejection.get("rejection_class") or "")
    if rejection_class == ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE:
        recovery_mode = "fresh_cold_reauthor"
        prior_workspace_reused = False
    elif rejection_class == ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT:
        recovery_mode = "typed_structural_repair"
        prior_workspace_reused = True
    else:
        raise ValueError("AdapterForge rejection has no automatic recovery route")
    row = dict(transition)
    core = {key: item for key, item in row.items() if key != "receipt_sha256"}
    request = gap.primitive_semantics_contract.get("theory_language_request") or {}
    workspace_label = str(row.get("workspace") or "")
    workspace = (directory / workspace_label).resolve()
    owner_resolved = owner.resolve()
    def valid_manifest(value: Any) -> bool:
        valid = isinstance(value, list) and bool(value)
        seen: set[str] = set()
        for artifact in value if isinstance(value, list) else ():
            if not isinstance(artifact, Mapping):
                valid = False
                break
            label = str(artifact.get("path") or "")
            digest = str(artifact.get("bytes_sha256") or "")
            if (
                not label
                or label in seen
                or Path(label).is_absolute()
                or ".." in Path(label).parts
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            ):
                valid = False
                break
            seen.add(label)
        return valid

    manifest = row.get("workspace_input_manifest")
    frozen_manifest = row.get("frozen_input_manifest")
    manifest_ok = valid_manifest(manifest)
    frozen_manifest_ok = valid_manifest(frozen_manifest) and {
        (str(item["path"]), str(item["bytes_sha256"]))
        for item in frozen_manifest
    }.issubset(
        {
            (str(item["path"]), str(item["bytes_sha256"]))
            for item in manifest
        }
        if isinstance(manifest, list)
        else set()
    )
    if (
        row.get("schema") != "leanmill.adapter_forge_recovery_transition.v1"
        or row.get("receipt_sha256") != content_hash(core)
        or row.get("gap_id") != gap.gap_id
        or row.get("request_id") != str(request.get("request_id") or "")
        or row.get("context_hash")
        != str(request.get("source_context_hash") or "")
        or int(row.get("source_epoch", -1))
        != int(request.get("source_epoch", 0))
        or row.get("predecessor_completion_sha256")
        != predecessor.get("completion_sha256")
        or row.get("host_rejection_receipt_sha256")
        != rejection.get("receipt_sha256")
        or row.get("rejection_class") != rejection_class
        or row.get("recovery_mode") != recovery_mode
        or int(row.get("recovery_attempt_index", -1))
        != int(recovery_attempt_index)
        or not workspace_label
        or not workspace.is_relative_to(owner_resolved)
        or (require_workspace and not workspace.is_dir())
        or row.get("prior_proposal_bytes_available")
        is not prior_workspace_reused
        or row.get("prior_proposal_resubmission_allowed") is not False
        or row.get("prior_workspace_reused") is not prior_workspace_reused
        or row.get("prior_agent_identity_reused") is not False
        or row.get("prior_agent_calls_replayed") is not False
        or re.fullmatch(r"attempt-\d+", str(row.get("agent_instance_id") or ""))
        is None
        or row.get("budget_phase") != "expansion"
        or row.get("authority") != "deterministic_campaign_lifecycle"
        or not manifest_ok
        or not frozen_manifest_ok
        or (
            require_workspace
            and frozen_manifest != _adapter_forge_frozen_input_manifest(workspace)
        )
    ):
        raise ValueError("AdapterForge recovery transition changed identity")
    return row, workspace


def _adapter_forge_completion_from_receipt(
    *,
    directory: Path,
    gap_id: str,
    receipt: Mapping[str, Any],
    provider_calls: int,
    artifact_owner: Path,
    recovery_attempt_index: int,
    predecessor_completion_sha256: str,
    recovery_transition: Mapping[str, Any],
    recovery_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize a subordinate completion using the base completion algebra."""

    from ztare.leanmill.adapter_forge import (
        ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
    )

    host = receipt.get("host_conformance") or {}
    review = receipt.get("independent_review") or {}
    host_unavailable = bool(
        isinstance(host, Mapping)
        and host.get("ok") is False
        and host.get("outcome") == "unavailable"
    )
    if host_unavailable:
        reason = "host_capability_unavailable:" + str(
            host.get("reason_code") or "unspecified_host_resource"
        )
    elif isinstance(host, Mapping) and host.get("ok") is False:
        reason = "host_conformance_rejected:" + str(
            host.get("reason") or "unspecified_host_rejection"
        )
    elif isinstance(review, Mapping) and review.get("outcome") == "unavailable":
        reason = "independent_review_capability_unavailable:" + str(
            review.get("reason_code") or "unspecified_review_failure"
        )
    elif isinstance(review, Mapping) and review.get("accepted") is False:
        reason = "independent_review_rejected:" + str(
            review.get("rationale") or "unspecified_review_rejection"
        )
    else:
        reason = str(
            (review.get("rationale") if isinstance(review, Mapping) else "")
            or receipt.get("status")
            or ""
        )
    accepted = receipt.get("status") == "quarantined_registry_proposal"
    next_step = str(receipt.get("next_step") or "")
    status = (
        "unavailable"
        if receipt.get("status") == "quarantined_capability_unavailable"
        else "reviewed_campaign_local_construction_parameterization_available"
        if accepted and next_step == "execute_reviewed_construction_parameterization"
        else "reviewed_campaign_local_finite_family_available"
        if accepted and next_step == "execute_reviewed_finite_construction_family"
        else "reviewed_campaign_local_functor_image_available"
        if accepted and next_step == "compile_campaign_local_functor_image_successor"
        else "quarantined_adapter_proposal_requires_authority_and_new_attempt"
        if accepted
        else "adapter_proposal_rejected_return_to_search"
    )
    core = {
        "schema": "leanmill.adapter_forge_completion.v1",
        "status": status,
        "attempt_dir": str(directory),
        "gap_id": gap_id,
        "host_conformance_contract": ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        "quarantine_receipt": dict(receipt),
        "reason": reason,
        "rejection_class": (
            str(host.get("rejection_class") or "")
            if isinstance(host, Mapping) and host.get("ok") is False
            else ""
        ),
        "recovery_route": (
            next_step
            if receipt.get("status") in {
                "quarantined_capability_rejected",
                "quarantined_capability_unavailable",
            }
            else ""
        ),
        "evidence_refs": [
            str(receipt["receipt_sha256"]),
            str(recovery_transition["receipt_sha256"]),
            str(recovery_input["receipt_sha256"]),
        ],
        "provider_calls": int(provider_calls),
        "artifact_owner": str(artifact_owner.relative_to(directory)),
        "recovery_attempt_index": int(recovery_attempt_index),
        "predecessor_completion_sha256": predecessor_completion_sha256,
        "recovery_transition_receipt_sha256": str(
            recovery_transition["receipt_sha256"]
        ),
        "recovery_transition": dict(recovery_transition),
        "recovery_input": dict(recovery_input),
    }
    return {**core, "completion_sha256": content_hash(core)}


def _execute_frontier_adapter_forge_recovery(
    directory: Path,
    *,
    definition: FrontierCampaignDefinition,
    gap: Any,
    predecessor: Mapping[str, Any],
    source_repo: Path,
    model: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    """Execute one receipt-authorized subordinate Forge attempt."""

    from ztare.leanmill.adapter_forge import (
        ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE,
        ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT,
        adapter_forge_agent_output_schema,
        adapter_forge_gap_directory,
        adapter_review_output_schema,
        bind_adapter_review_evidence,
        host_capability_conformance,
        run_adapter_forge,
        stage_adapter_forge_workspace,
    )

    rejection = _adapter_forge_rejection_receipt(predecessor)
    if rejection is None:
        return dict(predecessor)
    rejection_class = str(rejection.get("rejection_class") or "")
    if rejection_class == ADAPTER_FORGE_REJECTION_PRE_REVIEW_LEAKAGE:
        if (
            rejection.get("same_agent_repair_allowed") is not False
            or rejection.get("workspace_reuse_allowed") is not False
            or rejection.get("recovery_route")
            != "reauthor_in_fresh_cold_workspace_with_new_agent_identity"
        ):
            raise ValueError("AdapterForge leakage receipt permits forbidden reuse")
        recovery_mode = "fresh_cold_reauthor"
    elif rejection_class == ADAPTER_FORGE_REJECTION_REPAIRABLE_CONTRACT:
        if (
            rejection.get("same_agent_repair_allowed") is not True
            or rejection.get("workspace_reuse_allowed") is not True
            or rejection.get("recovery_route")
            != "return_typed_structural_repair_to_campaign"
        ):
            raise ValueError("AdapterForge structural repair lacks reuse authority")
        recovery_mode = "typed_structural_repair"
    else:
        return dict(predecessor)

    recovery_root = _adapter_forge_recovery_root(directory, gap.gap_id)
    recovery_root.mkdir(parents=True, exist_ok=True)
    pending: list[tuple[Path, dict[str, Any]]] = []
    occupied_indices: list[int] = []
    for path in sorted(recovery_root.glob("attempt-*")):
        match = re.fullmatch(r"attempt-(\d+)", path.name)
        if match is None or not path.is_dir():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(
            recovery_root.resolve()
        ):
            raise ValueError("AdapterForge recovery owner escaped its gap")
        index = int(match.group(1))
        occupied_indices.append(index)
        transition = read_json(
            path / "adapter_forge_recovery_transition.json", None
        )
        completion = read_json(path / "adapter_forge_completion.json", None)
        if (
            isinstance(transition, Mapping)
            and not isinstance(completion, Mapping)
            and transition.get("predecessor_completion_sha256")
            == predecessor.get("completion_sha256")
        ):
            pending.append((path, dict(transition)))
    if len(pending) > 1:
        raise ValueError("AdapterForge has multiple pending recovery attempts")

    if pending:
        owner, transition = pending[0]
        match = re.fullmatch(r"attempt-(\d+)", owner.name)
        if match is None:
            raise ValueError("AdapterForge recovery owner has no attempt identity")
        index = int(match.group(1))
        transition, workspace = _validate_adapter_forge_recovery_transition(
            directory,
            owner=owner,
            transition=transition,
            gap=gap,
            predecessor=predecessor,
            recovery_attempt_index=index,
        )
        instance_id = str(transition["agent_instance_id"])
    else:
        index = 1 + max(occupied_indices, default=0)
        owner = recovery_root / f"attempt-{index:03d}"
        owner.mkdir(parents=True, exist_ok=False)
        instance_id = _next_adapter_forge_agent_instance(directory)
        if recovery_mode == "fresh_cold_reauthor":
            cold_input = owner / "cold_input_attempt"
            cold_input.mkdir(parents=True)
            for name in (
                "campaign_manifest.json",
                "formal_context.json",
                "evidence_context.json",
                "blueprint.json",
            ):
                source = directory / name
                if source.is_file():
                    shutil.copy2(source, cold_input / name)
            workspace = stage_adapter_forge_workspace(
                cold_input, gap, source_repo=source_repo
            )
            prior_workspace_reused = False
        else:
            workspace = owner / "workspace"
            _copy_adapter_workspace(
                adapter_forge_gap_directory(directory, gap.gap_id) / "workspace",
                workspace,
            )
            prior_workspace_reused = True
        request = gap.primitive_semantics_contract.get(
            "theory_language_request"
        ) or {}
        transition_core = {
            "schema": "leanmill.adapter_forge_recovery_transition.v1",
            "gap_id": gap.gap_id,
            "request_id": str(request.get("request_id") or ""),
            "context_hash": str(request.get("source_context_hash") or ""),
            "source_epoch": int(request.get("source_epoch", 0)),
            "predecessor_completion_sha256": str(
                predecessor["completion_sha256"]
            ),
            "host_rejection_receipt_sha256": str(
                rejection["receipt_sha256"]
            ),
            "rejection_class": rejection_class,
            "recovery_mode": recovery_mode,
            "recovery_attempt_index": index,
            "workspace": str(workspace.relative_to(directory)),
            "workspace_input_manifest": _adapter_workspace_input_manifest(
                workspace
            ),
            "frozen_input_manifest": _adapter_forge_frozen_input_manifest(
                workspace
            ),
            "prior_proposal_bytes_available": prior_workspace_reused,
            "prior_proposal_resubmission_allowed": False,
            "prior_workspace_reused": prior_workspace_reused,
            "prior_agent_identity_reused": False,
            "prior_agent_calls_replayed": False,
            "agent_instance_id": instance_id,
            "budget_phase": "expansion",
            "authority": "deterministic_campaign_lifecycle",
            "claim_boundary": (
                "authorizes one bounded conformance attempt and grants no "
                "adapter, registry, review, or exactness authority"
            ),
        }
        transition = {
            **transition_core,
            "receipt_sha256": content_hash(transition_core),
        }
        write_json_atomic(
            owner / "adapter_forge_recovery_transition.json", transition
        )

    transition, workspace = _validate_adapter_forge_recovery_transition(
        directory,
        owner=owner,
        transition=transition,
        gap=gap,
        predecessor=predecessor,
        recovery_attempt_index=index,
    )
    if recovery_mode == "typed_structural_repair":
        repair_core = {
            "schema": "leanmill.adapter_forge_structural_repair_input.v1",
            "gap_id": gap.gap_id,
            "recovery_transition_receipt_sha256": str(
                transition["receipt_sha256"]
            ),
            "host_rejection_receipt_sha256": str(
                rejection["receipt_sha256"]
            ),
            "forbidden_proposal_digest": str(
                (predecessor.get("quarantine_receipt") or {}).get(
                    "proposal_digest"
                )
                or ""
            ),
            "violations": [dict(row) for row in rejection.get("violations") or ()],
            "allowed_reuse": {
                "workspace_snapshot": True,
                "agent_identity": False,
                "prior_proposal_as_output": False,
                "prior_review": False,
            },
            "required_output": "new_proposal_bytes_under_the_frozen_gap",
            "authority": "repair_input_only",
            "claim_boundary": "carries host defects and grants no capability authority",
        }
        repair = {**repair_core, "receipt_sha256": content_hash(repair_core)}
        repair_path = workspace / "adapter_forge_structural_repair_input.json"
        prior_repair = read_json(repair_path, None)
        if isinstance(prior_repair, Mapping) and dict(prior_repair) != repair:
            raise ValueError("AdapterForge structural repair input changed")
        if not isinstance(prior_repair, Mapping):
            write_json_atomic(repair_path, repair)
        recovery_input = repair
        recovery_instruction = (
            "\n\nTYPED STRUCTURAL REPAIR INPUT:\n"
            + json.dumps(repair, sort_keys=True, separators=(",", ":"))
            + "\nReturn newly authored proposal bytes. The prior proposal has no authority."
        )
    else:
        cold_core = {
            "schema": "leanmill.adapter_forge_cold_reauthor_input.v1",
            "gap_id": gap.gap_id,
            "recovery_transition_receipt_sha256": str(
                transition["receipt_sha256"]
            ),
            "prior_proposal_available": False,
            "prior_workspace_available": False,
            "prior_agent_session_available": False,
            "required_order": (
                "author construction bytes and construction-only self-checks "
                "before host target evaluation and independent review"
            ),
            "authority": "cold_input_only",
        }
        cold = {**cold_core, "receipt_sha256": content_hash(cold_core)}
        cold_path = workspace / "adapter_forge_cold_reauthor_input.json"
        prior_cold = read_json(cold_path, None)
        if isinstance(prior_cold, Mapping) and dict(prior_cold) != cold:
            raise ValueError("AdapterForge cold reauthor input changed")
        if not isinstance(prior_cold, Mapping):
            write_json_atomic(cold_path, cold)
        recovery_input = cold
        recovery_instruction = (
            "\n\nFRESH COLD REAUTHOR INPUT:\n"
            + json.dumps(cold, sort_keys=True, separators=(",", ":"))
            + "\nDo not seek or reconstruct any prior proposal, workspace, or session."
        )

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
        (coding, adapter_forge_agent_output_schema(), True),
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

    def coding_with_recovery(prompt: str) -> Mapping[str, Any]:
        return coding(prompt + recovery_instruction)

    coding_with_recovery.call_role = coding  # type: ignore[attr-defined]

    def has_durable_success(role: Any) -> bool:
        for call_path in sorted(role.artifact_dir.glob("*.call.json")):
            prefix = call_path.name.removesuffix(".call.json")
            call = read_json(call_path, None)
            if (
                isinstance(call, Mapping)
                and int(call.get("returncode", 1)) == 0
                and (role.artifact_dir / f"{prefix}.stdout.txt").is_file()
                and (
                    role.config.runtime != "codex"
                    or (role.artifact_dir / f"{prefix}.result.json").is_file()
                )
            ):
                return True
        return False

    if (
        pending
        and has_durable_success(coding)
    ):
        # This replays only the current subordinate attempt. The predecessor
        # agent directory has a different transition-bound instance identity.
        coding_with_recovery.recovered_proposal = True  # type: ignore[attr-defined]

    live_reviewing = make_subscription_adapter_reviewer(review)
    recovered_reviews: list[dict[str, Any]] = []
    if pending:
        for result_path in sorted(review.artifact_dir.glob("*.result.json")):
            call = read_json(
                result_path.with_name(
                    result_path.name.removesuffix(".result.json") + ".call.json"
                ),
                None,
            )
            candidate = read_json(result_path, None)
            if (
                isinstance(call, Mapping)
                and int(call.get("returncode", 1)) == 0
                and isinstance(candidate, Mapping)
                and type(candidate.get("accepted")) is bool
            ):
                recovered_reviews.append(dict(candidate))

    def recover_review_for_host(
        host_receipt: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        for candidate in recovered_reviews:
            try:
                bind_adapter_review_evidence(candidate, host_receipt)
            except ValueError:
                continue
            return candidate
        return None

    live_reviewing.recover_for_host_receipt = (  # type: ignore[attr-defined]
        recover_review_for_host
    )
    if pending and has_durable_success(review):
        live_reviewing.recovered_review = True  # type: ignore[attr-defined]

    registry_path = source_repo / "src/ztare/leanmill/theory_adapter_registry.py"
    registry_digest = content_hash(
        {"bytes": registry_path.read_text(encoding="utf-8")}
    )

    def conformance(
        proposal: Mapping[str, Any], typed_gap: Any
    ) -> Mapping[str, Any]:
        _verify_adapter_forge_frozen_inputs(
            workspace, transition["frozen_input_manifest"]
        )
        if (
            content_hash({"bytes": registry_path.read_text(encoding="utf-8")})
            != registry_digest
        ):
            raise ValueError("AdapterForge changed the live adapter registry")
        if typed_gap.gap_id != gap.gap_id:
            raise ValueError("AdapterForge recovery crossed the active gap")
        result = host_capability_conformance(
            proposal,
            typed_gap,
            workspace=workspace,
            output_path=owner / "theory_language_coordinates.json",
        )
        write_json_atomic(owner / "adapter_forge_host_conformance.json", result)
        return result

    budget = ExplorationBudget.from_json(read_json(directory / "budget.json", {}))
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        budget,
        attempt_id=directory.name,
    )
    ledger.recover_interrupted_wall_clock()
    ledger.recover_interrupted_reservations()
    ledger.resume_wall_clock()
    try:
        receipt = run_adapter_forge(
            gap,
            coding_agent_fn=coding_with_recovery,
            host_conformance_fn=conformance,
            independent_review_fn=live_reviewing,
            budget_ledger=ledger,
        )
    except BudgetExceeded as exc:
        unavailable_receipt_core = {
            "schema": "leanmill.adapter_forge_recovery_unavailable.v1",
            "gap_id": gap.gap_id,
            "recovery_attempt_index": index,
            "recovery_transition_receipt_sha256": str(
                transition["receipt_sha256"]
            ),
            "reason": "adapter_forge_recovery_budget_unavailable:" + exc.reason,
            "authority": "exploration_budget_ledger",
        }
        unavailable_receipt = {
            **unavailable_receipt_core,
            "receipt_sha256": content_hash(unavailable_receipt_core),
        }
        unavailable = {
            "schema": "leanmill.adapter_forge_recovery_outcome.v1",
            "status": "unavailable",
            "gap_id": gap.gap_id,
            "reason": unavailable_receipt["reason"],
            "evidence_refs": [
                str(transition["receipt_sha256"]),
                str(unavailable_receipt["receipt_sha256"]),
                str(recovery_input["receipt_sha256"]),
            ],
            "unavailability_receipt": unavailable_receipt,
            "recovery_transition": dict(transition),
            "recovery_input": dict(recovery_input),
        }
        write_json_atomic(
            owner / "adapter_forge_recovery_unavailable.json", unavailable
        )
        return unavailable
    finally:
        ledger.freeze_wall_clock(reason="adapter_forge_recovery_exit")

    if (
        content_hash({"bytes": registry_path.read_text(encoding="utf-8")})
        != registry_digest
    ):
        raise ValueError("AdapterForge changed the live adapter registry")
    write_json_atomic(owner / "adapter_forge_receipt.json", receipt)
    completion = _adapter_forge_completion_from_receipt(
        directory=directory,
        gap_id=gap.gap_id,
        receipt=receipt,
        provider_calls=(
            int(ledger.state()["usage"]["provider_calls"])
            + int(
                read_json(directory / "run.json", {}).get(
                    "preparation_provider_calls", 0
                )
            )
        ),
        artifact_owner=owner,
        recovery_attempt_index=index,
        predecessor_completion_sha256=str(predecessor["completion_sha256"]),
        recovery_transition=transition,
        recovery_input=recovery_input,
    )
    write_json_atomic(owner / "adapter_forge_completion.json", completion)
    return completion


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
        adapter_forge_agent_output_schema,
        adapter_forge_attempt_directory,
        adapter_review_output_schema,
        bind_adapter_review_evidence,
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
    source_repo = Path.cwd() if repo is None else Path(repo)
    forge_owner = adapter_forge_attempt_directory(
        directory, gap.gap_id, create=True
    )
    latest = _read_adapter_forge_lifecycle_completion(
        directory, gap, migrate_legacy=True
    )
    if latest is not None:
        rejection = _adapter_forge_rejection_receipt(latest)
        if rejection is None:
            return latest
        recovered = _execute_frontier_adapter_forge_recovery(
            directory,
            definition=definition,
            gap=gap,
            predecessor=latest,
            source_repo=source_repo,
            model=model,
            reasoning_effort=reasoning_effort,
        )
        if recovered != latest:
            return recovered
        return latest
    workspace = stage_adapter_forge_workspace(
        directory, gap, source_repo=source_repo
    )
    frozen_input_manifest = _adapter_forge_frozen_input_manifest(workspace)
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
        (coding, adapter_forge_agent_output_schema(), True),
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

    recovered_reviews: list[dict[str, Any]] = []
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
            recovered_reviews.append(dict(candidate))

    live_reviewing = make_subscription_adapter_reviewer(review)

    def recover_for_host_receipt(
        host_receipt: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        for candidate in recovered_reviews:
            try:
                bind_adapter_review_evidence(candidate, host_receipt)
            except ValueError:
                continue
            return candidate
        return None

    live_reviewing.recover_for_host_receipt = (  # type: ignore[attr-defined]
        recover_for_host_receipt
    )

    def conformance(proposal: Mapping[str, Any], typed_gap: AdapterGap) -> Mapping[str, Any]:
        _verify_adapter_forge_frozen_inputs(workspace, frozen_input_manifest)
        if content_hash({"bytes": registry_path.read_text(encoding="utf-8")}) != registry_digest:
            raise ValueError("AdapterForge changed the live adapter registry")
        if typed_gap.gap_kind != "capability_missing":
            raise ValueError("full adapter conformance is not executable in this campaign")
        result = host_capability_conformance(
            proposal,
            typed_gap,
            workspace=workspace,
            output_path=forge_owner / "theory_language_coordinates.json",
        )
        write_json_atomic(forge_owner / "adapter_forge_host_conformance.json", result)
        return result

    completion = execute_adapter_forge_attempt(
        directory,
        coding_agent_fn=recovered_coding if recovered_proposal is not None else coding,
        host_conformance_fn=conformance,
        independent_review_fn=live_reviewing,
    )
    if (
        content_hash({"bytes": registry_path.read_text(encoding="utf-8")})
        != registry_digest
    ):
        raise ValueError("AdapterForge changed the live adapter registry")
    rejection = _adapter_forge_rejection_receipt(completion)
    if rejection is None:
        return completion
    recovered = _execute_frontier_adapter_forge_recovery(
        directory,
        definition=definition,
        gap=gap,
        predecessor=completion,
        source_repo=source_repo,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    return recovered


def _approved_finite_family_candidate(
    directory: Path, completion: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Admit one reviewed family after schema checks and before any outcomes."""

    from ztare.leanmill.finite_construction_family import (
        FINITE_CONSTRUCTION_FAMILY_SCHEMA,
        construction_witness_interface,
        validate_finite_construction_family,
    )
    completion = _validated_adapter_forge_completion_row(
        completion, gap_id=str(completion.get("gap_id") or "")
    )
    receipt = completion.get("quarantine_receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("AdapterForge completion lacks its quarantine receipt")
    conformance = receipt.get("host_conformance")
    if not isinstance(conformance, Mapping) or conformance.get(
        "interface"
    ) != FINITE_CONSTRUCTION_FAMILY_SCHEMA:
        return None, None
    receipt_core = {
        key: value for key, value in receipt.items() if key != "receipt_sha256"
    }
    review = receipt.get("independent_review")
    conformance_core = {
        key: value for key, value in conformance.items() if key != "receipt_sha256"
    }
    if (
        completion.get("status")
        != "reviewed_campaign_local_finite_family_available"
        or receipt.get("receipt_sha256") != content_hash(receipt_core)
        or receipt.get("status") != "quarantined_registry_proposal"
        or receipt.get("live_registry_mutated") is not False
        or not isinstance(review, Mapping)
        or review.get("accepted") is not True
        or conformance.get("ok") is not True
        or conformance.get("outcomes_evaluated") is not False
        or conformance.get("receipt_sha256") != content_hash(conformance_core)
    ):
        raise ValueError("campaign-local finite family lacks accepted pre-outcome review")
    owner = _adapter_forge_artifact_owner(directory, completion)
    candidate = _read_bounded_reviewed_construction_artifact(
        owner / "theory_language_finite_family_candidate.json",
        label="reviewed finite family candidate",
    )
    blueprint = _read_bounded_reviewed_construction_artifact(
        directory / "blueprint.json",
        label="reviewed finite family blueprint",
    )
    if candidate is None or blueprint is None:
        raise ValueError("reviewed finite family artifact is missing")
    interface = construction_witness_interface(
        str(blueprint.get("adapter_id") or ""),
        dict(blueprint.get("adapter_config") or {}),
    )
    gap_row = _read_bounded_reviewed_construction_artifact(
        directory / "adapter_gap.json",
        label="reviewed finite family adapter gap",
    )
    if gap_row is None:
        raise ValueError("reviewed finite family adapter gap is missing")
    family = validate_finite_construction_family(
        candidate,
        request_id=str(
            gap_row.get("primitive_semantics_contract", {})
            .get("theory_language_request", {})
            .get("request_id", "")
        ),
        gap_id=str(completion.get("gap_id") or ""),
        context_hash=str(conformance.get("context_hash") or ""),
        adapter_id=str(blueprint.get("adapter_id") or ""),
        witness_interface=interface,
    )
    if family["receipt_sha256"] != conformance.get(
        "finite_family_receipt_sha256"
    ):
        raise ValueError("reviewed finite family crossed host conformance")
    return family, dict(receipt)


def _approved_construction_parameterization_candidate(
    directory: Path, completion: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Recover one AdapterForge-reviewed data-only construction problem."""

    from ztare.leanmill.adapter_forge import (
        validate_reviewed_construction_parameterization_authority,
    )
    from ztare.leanmill.construction_parameterization import (
        CONSTRUCTION_PARAMETERIZATION_SCHEMA,
    )
    from ztare.leanmill.finite_construction_family import (
        construction_witness_interface,
    )

    receipt = completion.get("quarantine_receipt")
    host = receipt.get("host_conformance") if isinstance(receipt, Mapping) else None
    if not isinstance(host, Mapping) or host.get("interface") != (
        CONSTRUCTION_PARAMETERIZATION_SCHEMA
    ):
        return None, None
    completion = _validated_adapter_forge_completion_row(
        completion, gap_id=str(completion.get("gap_id") or "")
    )
    if (
        completion.get("status")
        != "reviewed_campaign_local_construction_parameterization_available"
    ):
        raise ValueError("construction AdapterForge completion does not replay")
    owner = _adapter_forge_artifact_owner(directory, completion)
    candidate = _read_bounded_reviewed_construction_artifact(
        owner / "theory_language_construction_parameterization_candidate.json",
        label="reviewed construction parameterization candidate",
    )
    blueprint = _read_bounded_reviewed_construction_artifact(
        directory / "blueprint.json",
        label="reviewed construction parameterization blueprint",
    )
    if candidate is None or blueprint is None:
        raise ValueError("reviewed construction parameterization is missing")
    interface = construction_witness_interface(
        str(blueprint.get("adapter_id") or ""),
        dict(blueprint.get("adapter_config") or {}),
    )
    frozen, forge = validate_reviewed_construction_parameterization_authority(
        candidate,
        receipt,
        witness_interface=interface,
    )
    return frozen, forge


def _persist_reviewed_family_member_ratification_admissions(
    directory: Path,
    *,
    family: Mapping[str, Any],
    execution: Mapping[str, Any],
    forge_quarantine_receipt: Mapping[str, Any],
    witness_interface: Mapping[str, Any],
    construction_origin: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Freeze one formal-ratification admission per distinct verified artifact."""

    from ztare.leanmill.finite_construction_family import (
        validate_finite_construction_family_execution,
    )
    from ztare.leanmill.reviewed_family_member_ratification import (
        build_reviewed_family_member_ratification_admission,
    )

    result = validate_finite_construction_family_execution(
        execution,
        family=family,
        witness_interface=witness_interface,
        construction_origin=construction_origin,
    )
    if result.get("status") != "witness_found":
        raise ValueError("family ratification admission requires a verified member")
    first_parameter_by_normalized_artifact: dict[str, str] = {}
    for member in result.get("member_results") or ():
        registered = (
            member.get("registered_witness_execution")
            if isinstance(member, Mapping)
            else None
        )
        if not isinstance(registered, Mapping) or registered.get("status") != "verified":
            continue
        normalized_sha = str(registered.get("normalized_artifact_sha256") or "")
        if not normalized_sha:
            raise ValueError("verified family member lacks normalized identity")
        first_parameter_by_normalized_artifact.setdefault(
            normalized_sha, str(member.get("parameter_id") or "")
        )
    if not first_parameter_by_normalized_artifact:
        raise ValueError("witness-found family execution has no verified member")

    admissions: list[dict[str, Any]] = []
    for parameter_id in first_parameter_by_normalized_artifact.values():
        admission = build_reviewed_family_member_ratification_admission(
            family=family,
            family_execution=result,
            forge_quarantine_receipt=forge_quarantine_receipt,
            witness_interface=witness_interface,
            parameter_id=parameter_id,
            construction_origin=construction_origin,
        )
        path = directory / (
            "reviewed_family_member_ratification_admission."
            + str(admission["receipt_sha256"])[:16]
            + ".json"
        )
        existing = read_json(path, None)
        if isinstance(existing, Mapping) and dict(existing) != admission:
            raise ValueError("family-member ratification admission path conflicts")
        if existing is None:
            write_json_atomic(path, admission)
        admissions.append(admission)
    return tuple(admissions)


def _replay_reviewed_family_member_ratification_admissions(
    directory: Path,
    *,
    execution: Mapping[str, Any],
    request: TheoryLanguageExpansionRequest,
    witness_interface: Mapping[str, Any],
    admissions: Sequence[Mapping[str, Any]],
    budget_ledger: ExplorationBudgetLedger,
) -> tuple[dict[str, Any], ...]:
    """Rebuild persisted admissions from their family and Forge authorities."""

    from ztare.leanmill.adapter_forge import (
        ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT,
        ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        adapter_forge_attempt_directory,
        read_scoped_adapter_forge_completion,
    )
    from ztare.leanmill.finite_construction_family import (
        FiniteConstructionFamilyResourceUnavailable,
        execute_finite_construction_family,
        validate_finite_construction_family,
        validate_finite_construction_family_execution,
    )
    from ztare.leanmill.reviewed_family_member_ratification import (
        build_reviewed_family_member_ratification_admission,
        validate_reviewed_family_member_ratification_admission,
    )

    result = validate_finite_construction_family_execution(execution)
    origin_hashes = result["construction_origin_sha256s"]
    parameterized = bool(origin_hashes["parameterization_sha256"])
    host_contract = (
        ADAPTER_FORGE_CONSTRUCTION_HOST_CONFORMANCE_CONTRACT
        if parameterized
        else ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT
    )
    expected_forge_refs = {
        str(row.get("forge_quarantine_receipt_sha256") or "")
        for row in admissions
    }
    if len(expected_forge_refs) != 1 or "" in expected_forge_refs:
        raise ValueError("family ratification recovery has ambiguous Forge authority")
    expected_forge_ref = next(iter(expected_forge_refs))
    completion = read_scoped_adapter_forge_completion(
        directory,
        gap_id=str(result["gap_id"]),
        host_conformance_contract=host_contract,
        quarantine_receipt_sha256=expected_forge_ref,
    )
    if not isinstance(completion, Mapping):
        raise ValueError("family ratification recovery lost its scoped Forge completion")
    expected_completion_status = (
        "reviewed_campaign_local_construction_parameterization_available"
        if parameterized
        else "reviewed_campaign_local_finite_family_available"
    )
    if completion.get("status") != expected_completion_status:
        raise ValueError("family ratification recovery crossed Forge outcome")
    receipt = completion.get("quarantine_receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("family ratification recovery lost its Forge receipt")
    forge_rows = {expected_forge_ref: dict(receipt)}

    raw_families: dict[str, dict[str, Any]] = {}
    family_ref = str(result["family_receipt_sha256"])
    forge_owner = adapter_forge_attempt_directory(
        directory,
        str(result["gap_id"]),
        host_conformance_contract=host_contract,
    )
    family_paths = (
        directory / ("finite_construction_family." + family_ref[:16] + ".json"),
        forge_owner / "theory_language_finite_family_candidate.json",
    )
    family_read_budget = {"files": 0, "bytes": 0}
    for path in family_paths:
        raw = _read_bounded_reviewed_construction_artifact(
            path,
            label="family ratification source",
            aggregate_budget=family_read_budget,
        )
        if raw is None:
            continue
        if raw.get("receipt_sha256") != family_ref:
            raise ValueError("family ratification source slot crossed identity")
        raw_families[content_hash(dict(raw))] = dict(raw)
    if len(raw_families) != 1:
        raise ValueError("family ratification recovery lost its authored family")
    raw_family = next(iter(raw_families.values()))

    construction_origin = None
    if origin_hashes["parameterization_sha256"]:
        forge = forge_rows.get(
            str(origin_hashes["adapter_forge_quarantine_receipt_sha256"])
        )
        if forge is None:
            raise ValueError("family ratification recovery lost construction origin")
        from ztare.leanmill.reviewed_construction_campaign import (
            admit_persisted_construction_origin_for_campaign,
        )

        construction_origin = admit_persisted_construction_origin_for_campaign(
            directory,
            parameterization_sha256=str(
                origin_hashes["parameterization_sha256"]
            ),
            parameterization_execution_sha256=str(
                origin_hashes["parameterization_execution_sha256"]
            ),
            forge_quarantine_receipt=forge,
            witness_interface=witness_interface,
            budget_ledger=budget_ledger,
        )
    family = validate_finite_construction_family(
        raw_family,
        request_id=request.request_id,
        gap_id=str(result["gap_id"]),
        context_hash=str(result["context_hash"]),
        adapter_id=str(result["adapter_id"]),
        witness_interface=witness_interface,
        construction_origin=construction_origin,
    )

    def capability(*, descriptor, **kwargs):
        from ztare.leanmill.theory_adapter_registry import (
            materialize_theory_adapter_capability,
        )

        return materialize_theory_adapter_capability(
            str(descriptor["adapter_id"]),
            str(descriptor["capability_id"]),
            descriptor=dict(descriptor),
            **kwargs,
        )

    family_action_id = "finite-family:" + str(family["receipt_sha256"])
    expected_queries = int(result["unique_source_artifact_count"])
    family_already_charged = budget_ledger.has_committed_action_resources(
        family_action_id,
        phase="boundary",
        minimum_resources={"boundary_queries": expected_queries},
    )
    family_reservation = (
        None
        if family_already_charged
        else budget_ledger.reserve(
            family_action_id,
            "boundary",
            {"boundary_queries": expected_queries},
        )
    )
    try:
        replayed_execution = execute_finite_construction_family(
            family,
            witness_interface=witness_interface,
            capability_fn=capability,
            construction_origin=construction_origin,
        )
    except FiniteConstructionFamilyResourceUnavailable as exc:
        if family_reservation is not None:
            attempted_artifacts = {
                str(member.get("artifact_sha256") or "")
                for member in list(family.get("members") or ())[
                    : int(exc.attempted_members)
                ]
                if isinstance(member, Mapping)
            }
            budget_ledger.commit(
                family_reservation,
                {"boundary_queries": len(attempted_artifacts)},
            )
        raise
    except Exception:
        if family_reservation is not None:
            budget_ledger.commit(
                family_reservation,
                {"boundary_queries": expected_queries},
            )
        raise
    else:
        if family_reservation is not None:
            budget_ledger.commit(
                family_reservation,
                {"boundary_queries": expected_queries},
            )
    if replayed_execution != result:
        raise ValueError("persisted family execution changed registered outcomes")
    result = validate_finite_construction_family_execution(
        result,
        family=family,
        witness_interface=witness_interface,
        construction_origin=construction_origin,
    )

    replayed: list[dict[str, Any]] = []
    for raw in admissions:
        admission = validate_reviewed_family_member_ratification_admission(raw)
        rebuilt = build_reviewed_family_member_ratification_admission(
            family=family,
            family_execution=result,
            forge_quarantine_receipt=forge_rows[
                str(admission["forge_quarantine_receipt_sha256"])
            ],
            witness_interface=witness_interface,
            parameter_id=str(admission["primary_parameter_id"]),
            construction_origin=construction_origin,
        )
        if rebuilt != admission:
            raise ValueError("family ratification admission does not rebuild")
        replayed.append(rebuilt)
    return tuple(replayed)


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
    forge_owner = _adapter_forge_artifact_owner(directory, completion)
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
        from ztare.leanmill.adapter_forge import (
            ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        )

        if conformance.get("interface") != CANDIDATE_SCHEMA:
            raise ValueError("generative candidate crossed its Forge interface")
        candidate = read_json(
            forge_owner / "theory_language_generative_candidate.json", None
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
            host_conformance_contract=ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        )
        write_json_atomic(
            forge_owner / "theory_language_generative_application.json", application
        )
        return application, dict(receipt)
    application = read_json(forge_owner / "theory_language_functor_image.json", None)
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
    if isinstance(selected, list) and selected:
        request, _composition = compose_selected_language_expansion(synthesis)
        return request
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
    evidence_receipts: tuple[Mapping[str, Any], ...] = (),
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
    navigation["carried_evidence_receipts"] = _merge_carried_evidence_receipts(
        navigation.get("carried_evidence_receipts") or (),
        tuple(
            {
                "evidence_ref": _content_bound_receipt_ref(receipt),
                "receipt": dict(receipt),
            }
            for receipt in evidence_receipts
        ),
    )
    if any(
        str(row["evidence_ref"]) not in evidence_refs
        for row in navigation["carried_evidence_receipts"]
        if row["receipt"] in evidence_receipts
    ):
        raise ValueError("language feedback carried evidence outside its refs")
    for stale in (
        "adapter_gap",
        "language_expansion_request",
        "theory_language_expansion_requests",
        "lineage_synthesis",
        "finite_construction_family_execution",
        "reviewed_family_member_ratification_admission_sha256s",
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


def _content_bound_receipt_ref(receipt: Mapping[str, Any]) -> str:
    """Return the verified identity of one inert campaign evidence receipt."""

    row = dict(receipt)
    receipt_id = str(row.get("receipt_id") or "")
    receipt_sha = str(row.get("receipt_sha256") or "")
    if receipt_id:
        core = {key: value for key, value in row.items() if key != "receipt_id"}
        if receipt_id != "sha256:" + content_hash(core):
            raise ValueError("carried evidence receipt_id does not replay")
        return receipt_id
    if receipt_sha:
        core = {
            key: value for key, value in row.items() if key != "receipt_sha256"
        }
        if receipt_sha != content_hash(core):
            raise ValueError("carried evidence receipt_sha256 does not replay")
        return receipt_sha
    raise ValueError("carried evidence has no content identity")


def _merge_carried_evidence_receipts(
    *groups: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Merge receipt transport without changing identity or masking conflict."""

    merged: list[dict[str, Any]] = []
    by_ref: dict[str, dict[str, Any]] = {}
    for group in groups:
        for carried in group:
            if not isinstance(carried, Mapping) or not isinstance(
                carried.get("receipt"), Mapping
            ):
                raise ValueError("carried language evidence is malformed")
            row = {
                "evidence_ref": str(carried.get("evidence_ref") or ""),
                "receipt": dict(carried["receipt"]),
            }
            verified_ref = _content_bound_receipt_ref(row["receipt"])
            if not row["evidence_ref"] or row["evidence_ref"] != verified_ref:
                raise ValueError("carried language evidence changed identity")
            prior = by_ref.get(verified_ref)
            if prior is not None:
                if prior != row:
                    raise ValueError("carried language evidence conflicts")
                continue
            by_ref[verified_ref] = row
            merged.append(row)
    return merged


def _is_language_execution_feedback(
    feedback: Mapping[str, Any],
    *,
    context_hash: str,
) -> bool:
    """Recognize the shared causal contract of language/execution feedback."""

    if (
        feedback.get("route") != "continue_search"
        or feedback.get("repeat_requires_new_evidence") is not True
        or not str(feedback.get("request_id") or "")
    ):
        return False
    core = {
        key: item for key, item in feedback.items() if key != "receipt_sha256"
    }
    evidence_refs = feedback.get("evidence_refs")
    if (
        not str(feedback.get("schema") or "").startswith("leanmill.")
        or "feedback" not in str(feedback.get("schema") or "")
        or feedback.get("receipt_sha256") != content_hash(core)
        or feedback.get("context_hash") != context_hash
        or not isinstance(evidence_refs, list)
        or any(not isinstance(ref, str) or not ref for ref in evidence_refs)
        or len(set(evidence_refs)) != len(evidence_refs)
        or not str(feedback.get("authority") or "")
    ):
        raise ValueError("language/execution feedback changed causal identity")
    return True


def _objective_feedback_trace_rows(
    navigation: Mapping[str, Any],
    feedback: Mapping[str, Any],
    *,
    context_hash: str,
) -> tuple[dict[str, Any], ...]:
    """Materialize one feedback receipt and its carried typed evidence for a leaf."""

    rows: list[dict[str, Any]] = [
        {
            "decision": "objective_feedback",
            "receipt": dict(feedback),
            "host_finalized": True,
        }
    ]
    if not _is_language_execution_feedback(
        feedback, context_hash=context_hash
    ):
        return tuple(rows)
    admitted_refs = {str(ref) for ref in feedback.get("evidence_refs") or ()}
    carried = _merge_carried_evidence_receipts(
        navigation.get("carried_evidence_receipts") or ()
    )
    for item in carried:
        if item["evidence_ref"] not in admitted_refs:
            continue
        rows.append(
            {
                "decision": "objective_feedback_evidence",
                "evidence_ref": item["evidence_ref"],
                "receipt": dict(item["receipt"]),
                "source_feedback_receipt_sha256": str(
                    feedback["receipt_sha256"]
                ),
                "host_finalized": True,
            }
        )
    return tuple(rows)


def _language_feedback_wave_binding(
    directory: Path,
    feedback: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Resolve the immutable search-wave consumer of one language outcome."""

    feedback_ref = str(feedback.get("receipt_sha256") or "")
    rows = []
    for path in directory.glob(
        f"theory_language_feedback_wave_binding.{feedback_ref[:16]}.wave-*.json"
    ):
        row = read_json(path, None)
        if not isinstance(row, Mapping):
            continue
        core = {
            key: item for key, item in row.items() if key != "receipt_sha256"
        }
        if (
            row.get("schema")
            != "leanmill.theory_language_feedback_wave_binding.v1"
            or row.get("feedback_receipt_sha256") != feedback_ref
            or row.get("receipt_sha256") != content_hash(core)
        ):
            raise ValueError("language-feedback wave binding changed identity")
        rows.append(dict(row))
    if not rows:
        return None
    return max(rows, key=lambda row: int(row.get("search_wave", -1)))


def _bind_language_feedback_to_search_wave(
    directory: Path,
    *,
    feedback: Mapping[str, Any],
    context_hash: str,
    context_epoch: int,
    search_wave: int,
) -> dict[str, Any]:
    """Freeze the causal input identity of a newly opened search wave."""

    try:
        admissible = _is_language_execution_feedback(
            feedback, context_hash=context_hash
        )
    except ValueError as exc:
        raise ValueError(
            "language feedback cannot bind this search wave"
        ) from exc
    if not admissible or search_wave < 1:
        raise ValueError("language feedback cannot bind this search wave")
    core = {
        "schema": "leanmill.theory_language_feedback_wave_binding.v1",
        "context_hash": context_hash,
        "context_epoch": context_epoch,
        "request_id": str(feedback.get("request_id") or ""),
        "feedback_receipt_sha256": str(feedback["receipt_sha256"]),
        "search_wave": search_wave,
        "authority": "deterministic_campaign_lifecycle",
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    path = directory / (
        "theory_language_feedback_wave_binding."
        f"{str(feedback['receipt_sha256'])[:16]}.wave-{search_wave:03d}.json"
    )
    existing = read_json(path, None)
    if isinstance(existing, Mapping) and dict(existing) != receipt:
        raise ValueError("language-feedback wave binding changed identity")
    if not isinstance(existing, Mapping):
        write_json_atomic(path, receipt)
    return receipt


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
    from ztare.leanmill.evidence_theory_context import (
        EvidenceTheoryContext,
        load_evidence_theory_context,
        save_evidence_theory_context,
    )
    from ztare.leanmill.finite_theory_context import (
        FormalTheoryContext,
        load_formal_theory_context,
        save_formal_theory_context,
    )

    if isinstance(source_context, FormalTheoryContext):
        source_context_archive = (
            directory / f"formal_context.epoch-{source_epoch:03d}.json"
        )
        source_context_payload = source_context.to_json()
        if source_context_archive.is_file():
            if (
                load_formal_theory_context(source_context_archive).to_json()
                != source_context_payload
            ):
                raise ValueError(
                    "source formal-context epoch archive conflicts"
                )
        else:
            save_formal_theory_context(
                source_context, source_context_archive
            )
    elif isinstance(source_context, EvidenceTheoryContext):
        source_context_archive = (
            directory / f"evidence_context.epoch-{source_epoch:03d}.json"
        )
        source_context_payload = source_context.to_json()
        if source_context_archive.is_file():
            if (
                load_evidence_theory_context(source_context_archive).to_json()
                != source_context_payload
            ):
                raise ValueError(
                    "source evidence-context epoch archive conflicts"
                )
        else:
            save_evidence_theory_context(
                source_context, source_context_archive
            )
    else:
        raise ValueError("source language context category is unsupported")

    save_formal_theory_context(target_context, directory / "formal_context.json")
    save_formal_theory_context(
        target_context, directory / f"formal_context.epoch-{target_epoch:03d}.json"
    )
    if isinstance(source_context, EvidenceTheoryContext):
        (directory / "evidence_context.json").unlink(missing_ok=True)
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
    _archive_navigation_agent_calls_for_epoch(
        directory, source_epoch=source_epoch
    )
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
    _archive_navigation_agent_calls_for_epoch(
        directory, source_epoch=int(commit["source_epoch"])
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


def _archive_navigation_agent_calls_for_epoch(
    directory: Path,
    *,
    source_epoch: int,
) -> None:
    """Move every context-bound navigation role out of the successor namespace."""

    root = directory / "agent_calls"
    if not root.is_dir():
        return
    suffix = f".epoch-{source_epoch:03d}"
    prefixes = ("navigator", "witness_constructor", "lineage_synthesizer")
    for source in sorted(root.iterdir()):
        if (
            source.is_symlink()
            or not source.is_dir()
            or source.name.endswith(suffix)
            or not source.name.startswith(prefixes)
        ):
            continue
        target = source.with_name(source.name + suffix)
        if target.exists():
            raise ValueError(
                "source language navigation archive already exists"
            )
        os.replace(source, target)


def _adapter_gap_request_id(value: Mapping[str, Any]) -> str:
    contract = value.get("primitive_semantics_contract") or {}
    request = contract.get("theory_language_request") or {}
    return str(request.get("request_id") or "")


def _phase_extensions_after_stop(
    directory: Path,
    run: Mapping[str, Any],
    *,
    phase: str,
) -> tuple[dict[str, Any], ...]:
    """Return every validated phase grant after this run's stop."""

    stop = run.get("budget_stop_receipt")
    if not isinstance(stop, Mapping):
        stop = read_json(directory / "budget_stop_receipt.json", None)
    if not isinstance(stop, Mapping):
        return ()
    stop_core = {
        key: value for key, value in stop.items() if key != "receipt_sha256"
    }
    if stop.get("receipt_sha256") != content_hash(stop_core):
        return ()
    rows = []
    path = directory / "budget.events.jsonl"
    for line in (
        path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if path.is_file()
        else ()
    ):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, Mapping):
            continue
        core = {key: value for key, value in row.items() if key != "event_sha256"}
        if (
            row.get("event_sha256") == content_hash(core)
            and row.get("attempt_id") == stop.get("attempt_id")
            and row.get("budget_digest") == stop.get("budget_digest")
        ):
            rows.append(dict(row))
    stop_indices = [
        index
        for index, row in enumerate(rows)
        if row.get("event_type") == "budget_stopped"
        and (row.get("receipt") or {}).get("receipt_sha256")
        == stop.get("receipt_sha256")
    ]
    if not stop_indices:
        return ()
    blocked_resource = str(stop.get("reason") or "").rsplit(":", maxsplit=1)[-1]
    extensions = []
    for row in rows[stop_indices[-1] + 1 :]:
        resources = row.get("resources")
        if (
            row.get("event_type") == "resources_extended"
            and row.get("phase") == phase
            and str(row.get("authority_ref") or "").strip()
            and str(row.get("reason") or "").strip()
            and isinstance(resources, Mapping)
            and int(resources.get(blocked_resource, 0)) > 0
        ):
            extensions.append(row)
    return tuple(extensions)


def _phase_extension_after_stop(
    directory: Path,
    run: Mapping[str, Any],
    *,
    phase: str,
) -> dict[str, Any] | None:
    """Return the latest validated phase grant after this run's stop."""

    extensions = _phase_extensions_after_stop(directory, run, phase=phase)
    return extensions[-1] if extensions else None


def _pending_extended_adapter_gap(
    directory: Path,
    run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Find an unconsumed gap made runnable by a later resource grant."""

    extension = _phase_extension_after_stop(
        directory, run, phase="expansion"
    )
    gap_row = read_json(directory / "adapter_gap.json", None)
    if extension is None or not isinstance(gap_row, Mapping):
        return None
    from ztare.leanmill.adapter_forge import (
        AdapterGap,
        read_adapter_forge_completion,
    )

    try:
        gap = AdapterGap.from_json(gap_row)
    except (KeyError, TypeError, ValueError):
        return None
    request = (gap.primitive_semantics_contract.get("theory_language_request") or {})
    if (
        str(request.get("source_context_hash") or "")
        != str(run.get("context_hash") or "")
        or read_adapter_forge_completion(directory, gap) is not None
    ):
        return None
    return {"gap": gap.to_json(), "extension": extension}


def _unconsumed_expansion_extension(
    directory: Path,
    *,
    resource: str,
) -> dict[str, Any] | None:
    """Return a runnable, authority-receipted grant for one expansion resource."""

    consumed = {
        str(row.get("extension_event_sha256") or "")
        for path in directory.glob(
            "adapter_forge_recovery_budget_extension_reopen.*.json"
        )
        for row in (read_json(path, None),)
        if isinstance(row, Mapping)
    }
    candidates: list[dict[str, Any]] = []
    events_path = directory / "budget.events.jsonl"
    for line in (
        events_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if events_path.is_file()
        else ()
    ):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, Mapping):
            continue
        core = {
            key: value for key, value in row.items() if key != "event_sha256"
        }
        resources = row.get("resources")
        if (
            row.get("event_sha256") == content_hash(core)
            and row.get("event_type") == "resources_extended"
            and row.get("phase") == "expansion"
            and str(row.get("authority_ref") or "").strip()
            and str(row.get("reason") or "").strip()
            and isinstance(resources, Mapping)
            and int(resources.get(resource, 0)) > 0
            and row.get("event_sha256") not in consumed
        ):
            candidates.append(dict(row))
    if not candidates:
        return None
    budget_row = read_json(directory / "budget.json", None)
    if not isinstance(budget_row, Mapping):
        return None
    ledger = ExplorationBudgetLedger(
        directory / "budget.events.jsonl",
        ExplorationBudget.from_json(budget_row),
        attempt_id=directory.name,
    )
    if ledger.remaining_capacity("expansion", resource) <= 0:
        return None
    return candidates[-1]


def _pending_extended_adapter_recovery(
    directory: Path,
    run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Find a typed Forge recovery made runnable by a later budget grant."""

    if str(run.get("status") or "") not in {
        "frontier_objective_unmet",
        "frontier_leaf_decision_pending",
    }:
        return None
    from ztare.leanmill.adapter_forge import AdapterGap

    gap_row = read_json(directory / "adapter_gap.json", None)
    navigation = run.get("navigation")
    if not isinstance(gap_row, Mapping) or not isinstance(navigation, Mapping):
        return None
    try:
        gap = AdapterGap.from_json(gap_row)
    except (KeyError, TypeError, ValueError):
        return None
    request = gap.primitive_semantics_contract.get(
        "theory_language_request"
    )
    if (
        not isinstance(request, Mapping)
        or str(request.get("source_context_hash") or "")
        != str(run.get("context_hash") or "")
    ):
        return None
    feedback = next(
        (
            dict(row)
            for row in reversed(
                navigation.get("objective_review_history") or ()
            )
            if isinstance(row, Mapping)
            and row.get("schema")
            == "leanmill.theory_language_compilation_feedback.v1"
            and row.get("request_id") == request.get("request_id")
            and str(row.get("reason") or "").startswith(
                "adapter_forge_recovery_budget_unavailable:"
            )
        ),
        None,
    )
    if feedback is None:
        return None
    evidence_refs = {
        str(row) for row in feedback.get("evidence_refs") or ()
    }
    carried = {
        str(row.get("evidence_ref") or ""): dict(row.get("receipt") or {})
        for row in navigation.get("carried_evidence_receipts") or ()
        if isinstance(row, Mapping)
        and isinstance(row.get("receipt"), Mapping)
    }
    receipts = [carried.get(ref) for ref in evidence_refs]
    if any(not isinstance(row, Mapping) for row in receipts):
        return None
    for receipt in receipts:
        core = {
            key: value
            for key, value in receipt.items()
            if key != "receipt_sha256"
        }
        if receipt.get("receipt_sha256") != content_hash(core):
            return None
    unavailable = next(
        (
            dict(row)
            for row in receipts
            if row.get("schema")
            == "leanmill.adapter_forge_recovery_unavailable.v1"
        ),
        None,
    )
    transition = next(
        (
            dict(row)
            for row in receipts
            if row.get("schema")
            == "leanmill.adapter_forge_recovery_transition.v1"
        ),
        None,
    )
    if (
        unavailable is None
        or transition is None
        or unavailable.get("gap_id") != gap.gap_id
        or transition.get("gap_id") != gap.gap_id
        or unavailable.get("recovery_transition_receipt_sha256")
        != transition.get("receipt_sha256")
        or transition.get("request_id") != request.get("request_id")
        or transition.get("context_hash") != run.get("context_hash")
    ):
        return None
    reason = str(unavailable.get("reason") or "")
    resource = reason.rsplit(":", maxsplit=1)[-1]
    extension = _unconsumed_expansion_extension(
        directory, resource=resource
    )
    if extension is None:
        return None
    completion = _read_adapter_forge_lifecycle_completion(directory, gap)
    if (
        not isinstance(completion, Mapping)
        or completion.get("completion_sha256")
        != transition.get("predecessor_completion_sha256")
    ):
        return None
    return {
        "gap": gap.to_json(),
        "feedback": feedback,
        "unavailability": unavailable,
        "transition": transition,
        "extension": extension,
        "predecessor": dict(completion),
    }


def _active_reopened_adapter_recovery(
    run: Mapping[str, Any],
    *,
    gap_id: str,
    predecessor_completion_sha256: str,
) -> dict[str, Any] | None:
    navigation = run.get("navigation")
    if not isinstance(navigation, Mapping):
        return None
    return next(
        (
            dict(row)
            for row in reversed(
                navigation.get("objective_review_history") or ()
            )
            if isinstance(row, Mapping)
            and row.get("schema")
            == "leanmill.adapter_forge_recovery_budget_extension_reopen.v1"
            and row.get("gap_id") == gap_id
            and row.get("predecessor_completion_sha256")
            == predecessor_completion_sha256
        ),
        None,
    )


def _reopen_extended_adapter_recovery(attempt_dir: str | Path) -> Path:
    """Restore a budget-blocked subordinate Forge recovery to its gap state."""

    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("adapter recovery reopen requires an active run")
    pending = _pending_extended_adapter_recovery(directory, run)
    if pending is None:
        return directory
    gap = pending["gap"]
    transition = pending["transition"]
    unavailable = pending["unavailability"]
    extension = pending["extension"]
    core = {
        "schema": (
            "leanmill.adapter_forge_recovery_budget_extension_reopen.v1"
        ),
        "context_hash": str(run.get("context_hash") or ""),
        "gap_id": str(gap["gap_id"]),
        "request_id": _adapter_gap_request_id(gap),
        "prior_run_digest": str(run.get("run_digest") or ""),
        "predecessor_completion_sha256": str(
            transition["predecessor_completion_sha256"]
        ),
        "recovery_transition_receipt_sha256": str(
            transition["receipt_sha256"]
        ),
        "unavailability_receipt_sha256": str(
            unavailable["receipt_sha256"]
        ),
        "extension_event_sha256": str(extension["event_sha256"]),
        "authority": "deterministic_campaign_lifecycle",
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(
        directory
        / (
            "adapter_forge_recovery_budget_extension_reopen."
            f"{receipt['receipt_sha256'][:16]}.json"
        ),
        receipt,
    )
    navigation = dict(run.get("navigation") or {})
    history = [
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
    ]
    history.append(receipt)
    navigation["objective_review_history"] = history
    navigation["adapter_gap"] = gap
    run_core = {
        **{
            key: value
            for key, value in run.items()
            if key not in {"run_digest", "adapter_gap"}
        },
        "status": "blocked_adapter_gap",
        "navigation": navigation,
        "adapter_gap": gap,
    }
    write_json_atomic(
        directory / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    return directory


def _pending_adapter_gap_conformance_supersession(
    directory: Path,
    run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Find a gap whose rejection belongs to an older host contract."""

    if str(run.get("status") or "") != "frontier_objective_unmet":
        return None
    from ztare.leanmill.adapter_forge import (
        ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT,
        AdapterGap,
        _validated_adapter_forge_completion,
        adapter_forge_gap_directory,
        read_adapter_forge_completion,
    )

    gap_row = read_json(directory / "adapter_gap.json", None)
    feedback = read_json(directory / "theory_language_compilation_feedback.json", None)
    if not isinstance(gap_row, Mapping) or not isinstance(feedback, Mapping):
        return None
    try:
        gap = AdapterGap.from_json(gap_row)
    except (KeyError, TypeError, ValueError):
        return None
    request = gap.primitive_semantics_contract.get("theory_language_request") or {}
    feedback_core = {
        key: item for key, item in feedback.items() if key != "receipt_sha256"
    }
    if (
        str(request.get("source_context_hash") or "")
        != str(run.get("context_hash") or "")
        or feedback.get("schema")
        != "leanmill.theory_language_compilation_feedback.v1"
        or feedback.get("receipt_sha256") != content_hash(feedback_core)
        or feedback.get("outcome") != "rejected"
        or feedback.get("request_id") != request.get("request_id")
        or read_adapter_forge_completion(directory, gap) is not None
    ):
        return None
    evidence_refs = {str(row) for row in feedback.get("evidence_refs") or ()}
    gap_owner = adapter_forge_gap_directory(directory, gap.gap_id)
    if gap_owner.is_symlink():
        raise ValueError("historical AdapterForge gap owner is a symlink")
    candidate_paths: list[Path] = [
        gap_owner / "adapter_forge_completion.json",
        directory / "adapter_forge_completion.json",
    ]
    conformance_root = gap_owner / "conformance_attempts"
    if conformance_root.is_symlink():
        raise ValueError("historical AdapterForge conformance root is a symlink")
    if conformance_root.is_dir():
        visited = 0
        with os.scandir(conformance_root) as entries:
            for entry in entries:
                visited += 1
                if visited > _MAX_REVIEWED_CONSTRUCTION_DIRECTORY_ENTRIES:
                    raise ValueError(
                        "historical AdapterForge directory-entry ceiling exceeded"
                    )
                if entry.is_symlink():
                    raise ValueError(
                        "historical AdapterForge conformance owner is a symlink"
                    )
                if not entry.is_dir(follow_symlinks=False):
                    continue
                candidate_paths.append(
                    Path(entry.path) / "adapter_forge_completion.json"
                )
                if (
                    len(candidate_paths)
                    > _MAX_REVIEWED_CONSTRUCTION_LEGACY_CANDIDATES
                ):
                    raise ValueError(
                        "historical AdapterForge candidate ceiling exceeded"
                    )
    read_budget = {"files": 0, "bytes": 0}
    for path in candidate_paths:
        completion = _read_bounded_reviewed_construction_artifact(
            path,
            label="historical AdapterForge completion",
            aggregate_budget=read_budget,
        )
        if completion is None:
            continue
        historical_contract = str(
            completion.get("host_conformance_contract") or ""
        )
        completion = _validated_adapter_forge_completion(
            completion,
            gap_id=gap.gap_id,
            host_conformance_contract=historical_contract,
        )
        if (
            historical_contract == ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT
            or not evidence_refs.intersection(
                str(row) for row in completion.get("evidence_refs") or ()
            )
        ):
            continue
        return {
            "gap": gap.to_json(),
            "feedback": dict(feedback),
            "historical_completion": dict(completion),
            "historical_completion_path": str(path.relative_to(directory)),
            "current_host_conformance_contract": (
                ADAPTER_FORGE_HOST_CONFORMANCE_CONTRACT
            ),
        }
    return None


def _reopen_superseded_adapter_gap(attempt_dir: str | Path) -> Path:
    """Restore a gap after its prior host verdict loses compatibility."""

    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("adapter-gap supersession requires an active run")
    pending = _pending_adapter_gap_conformance_supersession(directory, run)
    if pending is None:
        return directory
    gap = pending["gap"]
    feedback = pending["feedback"]
    historical = pending["historical_completion"]
    core = {
        "schema": "leanmill.adapter_forge_host_contract_supersession.v1",
        "context_hash": str(run.get("context_hash") or ""),
        "gap_id": str(gap["gap_id"]),
        "request_id": _adapter_gap_request_id(gap),
        "prior_run_digest": str(run.get("run_digest") or ""),
        "prior_feedback_receipt_sha256": str(feedback["receipt_sha256"]),
        "historical_completion_sha256": str(
            historical["completion_sha256"]
        ),
        "historical_completion_path": pending["historical_completion_path"],
        "historical_host_conformance_contract": str(
            historical.get("host_conformance_contract") or "unversioned_v1"
        ),
        "current_host_conformance_contract": pending[
            "current_host_conformance_contract"
        ],
        "authority": "deterministic_campaign_lifecycle",
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(
        directory
        / f"adapter_forge_host_contract_supersession.{receipt['receipt_sha256'][:16]}.json",
        receipt,
    )
    navigation = dict(run.get("navigation") or {})
    history = [
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
    ]
    history.append(receipt)
    navigation["objective_review_history"] = history
    navigation["adapter_gap"] = gap
    run_core = {
        **{
            key: value
            for key, value in run.items()
            if key not in {"run_digest", "adapter_gap"}
        },
        "status": "blocked_adapter_gap",
        "navigation": navigation,
        "adapter_gap": gap,
    }
    write_json_atomic(
        directory / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    return directory


def _reopen_extended_adapter_gap(attempt_dir: str | Path) -> Path:
    """Project a validated resource grant back onto its pending gap."""

    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("adapter-gap reopen requires an active run")
    pending = _pending_extended_adapter_gap(directory, run)
    if pending is None:
        return directory
    gap = pending["gap"]
    extension = pending["extension"]
    stop = run.get("budget_stop_receipt")
    if not isinstance(stop, Mapping):
        stop = read_json(directory / "budget_stop_receipt.json", None)
    if not isinstance(stop, Mapping):
        raise ValueError("adapter-gap reopen lost its budget-stop identity")
    core = {
        "schema": "leanmill.budget_extension_pending_action_reopen.v1",
        "context_hash": str(run.get("context_hash") or ""),
        "gap_id": str(gap["gap_id"]),
        "request_id": _adapter_gap_request_id(gap),
        "prior_run_digest": str(run.get("run_digest") or ""),
        "superseded_budget_stop_receipt": dict(stop),
        "extension_event_sha256": str(extension["event_sha256"]),
        "authority": "deterministic_campaign_lifecycle",
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(
        directory / f"budget_extension_reopen.{receipt['receipt_sha256'][:16]}.json",
        receipt,
    )
    navigation = dict(run.get("navigation") or {})
    history = [
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
    ]
    history.append(receipt)
    navigation["objective_review_history"] = history
    navigation["adapter_gap"] = gap
    run_core = {
        **{
            key: value
            for key, value in run.items()
            if key not in {"run_digest", "adapter_gap", "budget_stop_receipt"}
        },
        "status": "blocked_adapter_gap",
        "navigation": navigation,
        "adapter_gap": gap,
        "budget_stop_receipt": None,
    }
    write_json_atomic(
        directory / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    return directory


def _boundary_hard_stop_reason(completion: Any) -> str:
    """Return a typed terminal resource stop from one boundary completion."""

    if not isinstance(completion, Mapping):
        return ""
    completion_core = {
        key: value
        for key, value in completion.items()
        if key != "completion_sha256"
    }
    boundary = completion.get("boundary_result")
    stop = completion.get("budget_stop_receipt")
    if (
        completion.get("completion_sha256") != content_hash(completion_core)
        or not isinstance(boundary, Mapping)
        or not isinstance(stop, Mapping)
    ):
        return ""
    boundary_core = {
        key: value for key, value in boundary.items() if key != "result_sha256"
    }
    stop_core = {
        key: value for key, value in stop.items() if key != "receipt_sha256"
    }
    reason = str(boundary.get("stop_reason") or "")
    if (
        boundary.get("result_sha256") != content_hash(boundary_core)
        or stop.get("receipt_sha256") != content_hash(stop_core)
        or str(stop.get("reason") or "") != reason
        or not reason.startswith((
            "blocked_before_action",
            "hard_cap_reached",
            "user_stop",
            "operator_stop",
        ))
    ):
        return ""
    return reason


def _materialize_boundary_budget_stop(
    directory: Path,
    run: Mapping[str, Any],
    completion: Mapping[str, Any],
) -> dict[str, Any]:
    """Turn a partial boundary hard stop into a resumable campaign state."""

    reason = _boundary_hard_stop_reason(completion)
    if not reason:
        raise ValueError("boundary budget-stop transition lacks a hard stop")
    if run.get("status") not in {
        "frontier_candidates_frozen_awaiting_boundary_approval",
        "frontier_objective_discharged",
    }:
        raise ValueError("boundary budget-stop transition crossed run state")
    boundary = dict(completion["boundary_result"])
    stop = dict(completion["budget_stop_receipt"])
    if str(run.get("context_hash") or "") != str(
        boundary.get("context_hash") or ""
    ):
        raise ValueError("boundary budget stop crossed context identity")
    transition_core = {
        "schema": "leanmill.boundary_budget_stop_transition.v1",
        "context_hash": str(run.get("context_hash") or ""),
        "source_run_digest": str(run.get("run_digest") or ""),
        "boundary_result_sha256": str(boundary["result_sha256"]),
        "boundary_completion_sha256": str(completion["completion_sha256"]),
        "budget_stop_receipt_sha256": str(stop["receipt_sha256"]),
        "reason": reason,
        "authority": "boundary_resource_lifecycle",
    }
    transition = {
        **transition_core,
        "receipt_sha256": content_hash(transition_core),
    }
    transition_path = directory / (
        "boundary_budget_stop_transition."
        + str(transition["receipt_sha256"])[:16]
        + ".json"
    )
    prior = read_json(transition_path, None)
    if isinstance(prior, Mapping) and dict(prior) != transition:
        raise ValueError("boundary budget-stop transition changed identity")
    if prior is None:
        write_json_atomic(transition_path, transition)
    navigation = dict(run.get("navigation") or {})
    navigation["boundary_budget_stop_transition"] = transition
    run_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "status": "budget_stopped",
        "navigation": navigation,
        "budget_stop_receipt": stop,
    }
    updated = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(directory / "run.json", updated)
    return updated


def _pending_extended_boundary(
    directory: Path,
    run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Find a stopped frozen boundary made runnable by a resource grant."""

    if run.get("status") != "budget_stopped":
        return None
    navigation = run.get("navigation")
    completion = read_json(directory / "boundary_completion.json", None)
    if (
        not isinstance(navigation, Mapping)
        or not navigation.get("finalists")
        or not _boundary_hard_stop_reason(completion)
    ):
        return None
    extension = _phase_extension_after_stop(
        directory, run, phase="boundary"
    )
    return (
        {"completion": dict(completion), "extension": extension}
        if extension is not None
        else None
    )


def _pending_extended_navigation(
    directory: Path,
    run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Find a stopped navigator made runnable by a later resource grant."""

    if run.get("status") != "budget_stopped":
        return None
    stop = run.get("budget_stop_receipt")
    if not isinstance(stop, Mapping):
        stop = read_json(directory / "budget_stop_receipt.json", None)
    if (
        not isinstance(stop, Mapping)
        or not str(stop.get("reason") or "").startswith(
            "blocked_before_action:navigation:"
        )
        or stop.get("context_hash") != run.get("context_hash")
    ):
        return None
    extension = _phase_extension_after_stop(
        directory, run, phase="navigation"
    )
    return (
        {"stop": dict(stop), "extension": extension}
        if extension is not None
        else None
    )


def _reopen_extended_navigation(attempt_dir: str | Path) -> Path:
    """Restore the active context after its navigation resource is extended."""

    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("navigation reopen requires an active run")
    pending = _pending_extended_navigation(directory, run)
    if pending is None:
        return directory
    stop = pending["stop"]
    extension = pending["extension"]
    core = {
        "schema": "leanmill.navigation_budget_extension_reopen.v1",
        "context_hash": str(run.get("context_hash") or ""),
        "prior_run_digest": str(run.get("run_digest") or ""),
        "superseded_budget_stop_receipt": stop,
        "extension_event_sha256": str(extension["event_sha256"]),
        "authority": "deterministic_campaign_lifecycle",
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(
        directory
        / (
            "navigation_budget_extension_reopen."
            f"{receipt['receipt_sha256'][:16]}.json"
        ),
        receipt,
    )
    navigation = dict(run.get("navigation") or {})
    navigation["navigation_budget_extension_reopen"] = receipt
    run_core = {
        **{
            key: value
            for key, value in run.items()
            if key not in {"run_digest", "budget_stop_receipt"}
        },
        "status": "frontier_objective_unmet",
        "navigation": navigation,
        "budget_stop_receipt": None,
    }
    write_json_atomic(
        directory / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    return directory


def _reopen_extended_boundary(attempt_dir: str | Path) -> Path:
    """Restore a frozen boundary after its blocked resource is extended."""

    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("boundary reopen requires an active run")
    pending = _pending_extended_boundary(directory, run)
    if pending is None:
        return directory
    completion = pending["completion"]
    extension = pending["extension"]
    stop = run.get("budget_stop_receipt")
    if not isinstance(stop, Mapping):
        stop = read_json(directory / "budget_stop_receipt.json", None)
    if not isinstance(stop, Mapping):
        raise ValueError("boundary reopen lost its budget-stop identity")
    core = {
        "schema": "leanmill.boundary_budget_extension_reopen.v1",
        "context_hash": str(run.get("context_hash") or ""),
        "prior_run_digest": str(run.get("run_digest") or ""),
        "boundary_completion_sha256": str(completion["completion_sha256"]),
        "superseded_budget_stop_receipt": dict(stop),
        "extension_event_sha256": str(extension["event_sha256"]),
        "authority": "deterministic_campaign_lifecycle",
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(
        directory
        / f"boundary_budget_extension_reopen.{receipt['receipt_sha256'][:16]}.json",
        receipt,
    )
    navigation = dict(run.get("navigation") or {})
    navigation["boundary_budget_extension_reopen"] = receipt
    run_core = {
        **{
            key: value
            for key, value in run.items()
            if key not in {"run_digest", "budget_stop_receipt"}
        },
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "navigation": navigation,
        "budget_stop_receipt": None,
    }
    write_json_atomic(
        directory / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    return directory


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

    from ztare.leanmill.adapter_forge import AdapterGap

    active_gap = AdapterGap.from_json(
        run.get("adapter_gap") or read_json(directory / "adapter_gap.json", {})
    )
    completion = _read_adapter_forge_lifecycle_completion(
        directory, active_gap, migrate_legacy=True
    )
    recovery_reopened = (
        _active_reopened_adapter_recovery(
            run,
            gap_id=active_gap.gap_id,
            predecessor_completion_sha256=str(
                completion.get("completion_sha256") or ""
            ),
        )
        if isinstance(completion, Mapping)
        else None
    )
    if completion is None or recovery_reopened is not None:
        if forge_fn is None:
            return {
                "schema": "leanmill.theory_language_advancement.v1",
                "status": "adapter_forge_required",
                "gap_id": active_gap.gap_id,
                "attempt_dir": str(directory),
            }
        try:
            completion = forge_fn(directory, _attempt_lease=_attempt_lease)
        except BudgetExceeded as exc:
            feedback = _language_outcome_feedback(
                directory,
                run,
                outcome="unavailable",
                reason="adapter_forge_budget_unavailable:" + exc.reason,
                evidence_refs=(),
            )
            if resume_fn is not None:
                resume_fn(directory, _attempt_lease=_attempt_lease)
            return {
                "schema": "leanmill.theory_language_advancement.v1",
                "status": "unavailable",
                "feedback_receipt_sha256": feedback["receipt_sha256"],
                "attempt_dir": str(directory),
            }
    if not isinstance(completion, Mapping):
        raise ValueError("language advancement forge returned no typed outcome")
    if (
        completion.get("schema") == "leanmill.adapter_forge_completion.v1"
        and str(completion.get("gap_id") or "") != active_gap.gap_id
    ):
        raise ValueError("adapter forge completion crossed gap identity")
    if completion.get("status") in {
        "adapter_proposal_rejected_return_to_search",
        "frontier_objective_unmet",
        "unavailable",
    }:
        if read_json(directory / "run.json", {}).get("status") == "blocked_adapter_gap":
            reason = str(completion.get("reason") or completion.get("status") or "")
            quarantine = completion.get("quarantine_receipt")
            unavailable = completion.get("unavailability_receipt")
            recovery_transition = completion.get("recovery_transition")
            recovery_input = completion.get("recovery_input")
            evidence_receipts = tuple(
                dict(row)
                for row in (
                    quarantine,
                    unavailable,
                    recovery_transition,
                    recovery_input,
                )
                if isinstance(row, Mapping)
            )
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
                evidence_receipts=evidence_receipts,
            )
        if resume_fn is not None:
            resume_fn(directory, _attempt_lease=_attempt_lease)
        return {
            "schema": "leanmill.theory_language_advancement.v1",
            "status": str(completion.get("status") or "frontier_objective_unmet"),
            "attempt_dir": str(directory),
        }

    construction_result = advance_reviewed_construction_campaign(
        directory,
        completion=completion,
        run=run,
        blueprint=blueprint,
        resume_fn=resume_fn,
        _attempt_lease=_attempt_lease,
        hooks=ReviewedConstructionHooks(
            approved_parameterization=(
                _approved_construction_parameterization_candidate
            ),
            language_outcome_feedback=_language_outcome_feedback,
            approved_family=_approved_finite_family_candidate,
            persist_ratification_admissions=(
                _persist_reviewed_family_member_ratification_admissions
            ),
            family_synthesis_provenance=(
                _reviewed_family_synthesis_provenance
            ),
            frozen_terminal_lineage_ids=_frozen_terminal_lineage_ids,
            language_request_from_run=_language_request_from_run,
            current_family_exhaustion_discharge=(
                _current_reviewed_family_exhaustion_discharge
            ),
        ),
    )
    if construction_result is not None:
        return construction_result
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
    "proof_rejected_by_governance",
}


def _boundary_governance_recheck_state(
    completion: Mapping[str, Any],
    recheck: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Bind saved proof bytes to their deterministic governance replay."""

    boundary = completion.get("boundary_result")
    if not isinstance(boundary, Mapping):
        return {"required": False, "complete": True, "statuses": {}}
    expected: dict[tuple[tuple[str, ...], str], str] = {}
    for row in boundary.get("query_results") or ():
        if not isinstance(row, Mapping):
            continue
        lean = row.get("lean")
        governed = lean.get("governed_attempt") if isinstance(lean, Mapping) else None
        proof = str(
            governed.get("proof_text") if isinstance(governed, Mapping) else ""
        ).strip()
        if not proof:
            continue
        key = (
            tuple(str(value) for value in row.get("premise_formula_ids") or ()),
            str(row.get("target_formula_id") or ""),
        )
        if key in expected:
            raise ValueError("saved Lean proof identity is duplicated")
        expected[key] = content_hash({"proof_text": proof})
    if not expected:
        return {"required": False, "complete": True, "statuses": {}}
    if not isinstance(recheck, Mapping):
        return {"required": True, "complete": False, "statuses": {}}

    core = {
        key: value for key, value in recheck.items() if key != "receipt_sha256"
    }
    boundary_core = {
        key: value for key, value in boundary.items() if key != "result_sha256"
    }
    if (
        recheck.get("schema")
        != "leanmill.frontier_boundary_governance_recheck.v1"
        or recheck.get("receipt_sha256") != content_hash(core)
        or boundary.get("result_sha256") != content_hash(boundary_core)
        or recheck.get("boundary_result_sha256")
        != boundary.get("result_sha256")
    ):
        raise ValueError("boundary governance recheck crossed boundary identity")
    statuses: dict[tuple[tuple[str, ...], str], str] = {}
    for raw in recheck.get("query_rechecks") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("boundary governance recheck row is malformed")
        key = (
            tuple(str(value) for value in raw.get("premise_formula_ids") or ()),
            str(raw.get("target_formula_id") or ""),
        )
        governed = raw.get("recheck")
        governed_core = {
            name: value
            for name, value in dict(governed or {}).items()
            if name != "receipt_sha256"
        }
        if (
            key not in expected
            or key in statuses
            or raw.get("proof_digest") != expected[key]
            or not isinstance(governed, Mapping)
            or governed.get("schema")
            != "leanmill.governed_consequence_attempt.v1"
            or governed.get("receipt_sha256") != content_hash(governed_core)
        ):
            raise ValueError("boundary governance recheck row changed proof identity")
        statuses[key] = str(governed.get("status") or "unresolved")
    if set(statuses) != set(expected):
        raise ValueError("boundary governance recheck omitted a saved proof")
    return {
        "required": True,
        "complete": True,
        "statuses": statuses,
        "receipt_sha256": str(recheck["receipt_sha256"]),
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
    from ztare.leanmill.theory_task_discharge_successor import (
        CONSTRUCTION_RATIFICATION_TRANSITION_KEY,
        construction_ratification_predecessor_ref,
        validate_construction_ratification_successor_bundle,
    )

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

    predecessor_bundle_ref = construction_ratification_predecessor_ref(bundle)
    if CONSTRUCTION_RATIFICATION_TRANSITION_KEY in bundle:
        bundle = validate_construction_ratification_successor_bundle(
            bundle, boundary
        )

    navigation = dict(run.get("navigation") or {})
    current_consumption = navigation.get("theory_task_discharge")
    current_bundle_ref = (
        str(current_consumption.get("bundle_receipt_sha256") or "")
        if isinstance(current_consumption, Mapping)
        else ""
    )
    if current_bundle_ref and current_bundle_ref != bundle_ref:
        current_predecessor_ref = str(
            current_consumption.get("predecessor_bundle_receipt_sha256") or ""
        )
        if current_predecessor_ref == bundle_ref:
            # A stale replay of the immutable predecessor cannot move campaign
            # state backward after its successor has already been consumed.
            return dict(run)
        if predecessor_bundle_ref != current_bundle_ref:
            raise ValueError("theory-task discharge successor crossed state history")
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
        **(
            {
                "predecessor_bundle_receipt_sha256": predecessor_bundle_ref,
                "successor_task_discharge": dict(bundle),
            }
            if predecessor_bundle_ref
            else {}
        ),
    }
    consumption = {
        **consumption_core,
        "receipt_sha256": content_hash(consumption_core),
    }
    canonical_consumption_path = (
        directory / "theory_task_discharge_consumption.json"
    )
    canonical_consumption = read_json(canonical_consumption_path, None)
    consumption_path = (
        canonical_consumption_path
        if not isinstance(canonical_consumption, Mapping)
        or dict(canonical_consumption) == consumption
        else directory
        / f"theory_task_discharge_consumption.{bundle_ref[:16]}.json"
    )
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
                identity=_lineage_disposition_storage_identity(disposition),
                receipt=disposition,
            )
    return updated


def _pending_reviewed_family_member_ratifications(
    directory: Path,
    run: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Read immutable family-origin admissions owned by the active run."""

    from ztare.leanmill.finite_construction_family import (
        validate_finite_construction_family_execution,
    )
    from ztare.leanmill.reviewed_family_member_ratification import (
        validate_reviewed_family_member_ratification_admission,
    )

    if run.get("status") != "frontier_objective_witness_found_pending_ratification":
        return ()
    navigation = run.get("navigation")
    if not isinstance(navigation, Mapping):
        raise ValueError("family ratification run lacks frozen navigation")
    refs = navigation.get(
        "reviewed_family_member_ratification_admission_sha256s"
    )
    if not isinstance(refs, list) or not refs or any(
        not isinstance(ref, str) or not ref for ref in refs
    ) or len(refs) != len(set(refs)):
        raise ValueError("family ratification run lacks exact admission identities")
    execution_raw = navigation.get("finite_construction_family_execution")
    if not isinstance(execution_raw, Mapping):
        raise ValueError("family ratification run lacks its family execution")
    execution = validate_finite_construction_family_execution(execution_raw)
    if execution.get("status") != "witness_found":
        raise ValueError("family ratification run carries no verified witness")
    request = _language_request_from_run(run)
    blueprint = FrontierTheoryBlueprint.from_json(
        read_json(directory / "blueprint.json", {})
    )
    from ztare.leanmill.finite_construction_family import (
        construction_witness_interface,
    )

    interface = construction_witness_interface(
        blueprint.adapter_id, dict(blueprint.adapter_config)
    )
    if (
        execution.get("context_hash") != run.get("context_hash")
        or execution.get("request_id") != request.request_id
        or execution.get("adapter_id") != blueprint.adapter_id
        or execution.get("target_interface_sha256")
        != interface.get("interface_sha256")
    ):
        raise ValueError("family ratification execution crossed campaign identity")

    by_ref: dict[str, dict[str, Any]] = {}
    for ref in refs:
        if re.fullmatch(r"[0-9a-f]{64}", ref) is None:
            raise ValueError("family ratification admission identity is malformed")
        path = directory / (
            "reviewed_family_member_ratification_admission."
            + ref[:16]
            + ".json"
        )
        raw = _read_bounded_reviewed_construction_artifact(
            path,
            label="family ratification admission",
        )
        if raw is None:
            raise ValueError("family ratification admission artifact is missing")
        admission = validate_reviewed_family_member_ratification_admission(raw)
        if admission["receipt_sha256"] != ref:
            raise ValueError("family ratification admission slot crossed identity")
        by_ref[ref] = admission
    admissions = tuple(by_ref[ref] for ref in refs)
    for admission in admissions:
        if (
            admission.get("request_id") != request.request_id
            or admission.get("context_hash") != run.get("context_hash")
            or admission.get("family_execution_receipt_sha256")
            != execution.get("receipt_sha256")
            or admission.get("family_receipt_sha256")
            != execution.get("family_receipt_sha256")
            or admission.get("adapter_id") != execution.get("adapter_id")
            or admission.get("interface_sha256")
            != execution.get("target_interface_sha256")
        ):
            raise ValueError("family ratification admission crossed active execution")
    # Action selection is structural and read-only.  Backend admission and
    # target replay belong to the leased ratification execution below.
    return admissions


_MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES = 64_000_000
_MAX_REVIEWED_CONSTRUCTION_LEGACY_TOTAL_BYTES = 128_000_000
_MAX_REVIEWED_CONSTRUCTION_LEGACY_CANDIDATES = 64
_MAX_REVIEWED_CONSTRUCTION_DIRECTORY_ENTRIES = 20_000


def _reviewed_construction_identity(value: Any, *, label: str) -> str:
    identity = str(value or "")
    if re.fullmatch(r"[0-9a-f]{64}", identity) is None:
        raise ValueError(f"{label} identity is malformed")
    return identity


def _read_bounded_reviewed_construction_artifact(
    path: Path,
    *,
    label: str,
    aggregate_budget: dict[str, int] | None = None,
) -> dict[str, Any] | None:
    """Read one exact authority slot without following links or over-reading."""

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ValueError(f"{label} authority slot is unavailable") from exc
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{label} authority slot is not a regular file")
        if metadata.st_size > _MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES:
            raise ValueError(f"{label} exceeds its byte ceiling")
        chunks: list[bytes] = []
        observed = 0
        while True:
            chunk = os.read(
                fd,
                min(
                    1_048_576,
                    _MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES + 1 - observed,
                ),
            )
            if not chunk:
                break
            chunks.append(chunk)
            observed += len(chunk)
            if observed > _MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES:
                raise ValueError(f"{label} exceeds its byte ceiling")
        if aggregate_budget is not None:
            files = int(aggregate_budget.get("files", 0)) + 1
            total_bytes = int(aggregate_budget.get("bytes", 0)) + observed
            if files > _MAX_REVIEWED_CONSTRUCTION_LEGACY_CANDIDATES:
                raise ValueError(f"{label} candidate ceiling exceeded")
            if total_bytes > _MAX_REVIEWED_CONSTRUCTION_LEGACY_TOTAL_BYTES:
                raise ValueError(f"{label} aggregate byte ceiling exceeded")
            aggregate_budget["files"] = files
            aggregate_budget["bytes"] = total_bytes
        try:
            raw = json.loads(b"".join(chunks))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{label} is malformed") from exc
        if not isinstance(raw, Mapping):
            raise ValueError(f"{label} is not an object")
        return dict(raw)
    finally:
        os.close(fd)


def _read_bounded_reviewed_construction_artifact_at(
    directory_fd: int,
    filename: str,
    *,
    label: str,
    aggregate_budget: dict[str, int] | None = None,
) -> dict[str, Any] | None:
    """Read one frozen child of an already-open authority directory."""

    if Path(filename).name != filename or filename in {"", ".", ".."}:
        raise ValueError(f"{label} filename is malformed")
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(filename, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ValueError(f"{label} authority slot is unavailable") from exc
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{label} authority slot is not a regular file")
        if metadata.st_size > _MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES:
            raise ValueError(f"{label} exceeds its byte ceiling")
        chunks: list[bytes] = []
        observed = 0
        while True:
            chunk = os.read(
                fd,
                min(
                    1_048_576,
                    _MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES + 1 - observed,
                ),
            )
            if not chunk:
                break
            chunks.append(chunk)
            observed += len(chunk)
            if observed > _MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES:
                raise ValueError(f"{label} exceeds its byte ceiling")
        if aggregate_budget is not None:
            files = int(aggregate_budget.get("files", 0)) + 1
            total_bytes = int(aggregate_budget.get("bytes", 0)) + observed
            if files > _MAX_REVIEWED_CONSTRUCTION_LEGACY_CANDIDATES:
                raise ValueError(f"{label} candidate ceiling exceeded")
            if total_bytes > _MAX_REVIEWED_CONSTRUCTION_LEGACY_TOTAL_BYTES:
                raise ValueError(f"{label} aggregate byte ceiling exceeded")
            aggregate_budget["files"] = files
            aggregate_budget["bytes"] = total_bytes
        try:
            raw = json.loads(b"".join(chunks))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{label} is malformed") from exc
        if not isinstance(raw, Mapping):
            raise ValueError(f"{label} is not an object")
        return dict(raw)
    finally:
        os.close(fd)


def _bounded_reviewed_construction_legacy_paths(
    directory: Path,
    *,
    filename_pattern: re.Pattern[str],
    label: str,
) -> tuple[Path, ...]:
    """Enumerate only a bounded flat set of pre-owner-slot artifacts."""

    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f"{label} campaign directory is unavailable")
    paths: list[Path] = []
    total_bytes = 0
    visited = 0
    with os.scandir(directory) as entries:
        for entry in entries:
            visited += 1
            if visited > _MAX_REVIEWED_CONSTRUCTION_DIRECTORY_ENTRIES:
                raise ValueError(f"{label} directory-entry ceiling exceeded")
            if filename_pattern.fullmatch(entry.name) is None:
                continue
            if entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                raise ValueError(f"{label} legacy artifact is not a regular file")
            size = int(entry.stat(follow_symlinks=False).st_size)
            if size > _MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES:
                raise ValueError(f"{label} legacy artifact exceeds its byte ceiling")
            total_bytes += size
            if total_bytes > _MAX_REVIEWED_CONSTRUCTION_LEGACY_TOTAL_BYTES:
                raise ValueError(f"{label} legacy aggregate byte ceiling exceeded")
            paths.append(Path(entry.path))
            if len(paths) > _MAX_REVIEWED_CONSTRUCTION_LEGACY_CANDIDATES:
                raise ValueError(f"{label} legacy candidate ceiling exceeded")
    return tuple(sorted(paths))


def _persist_bounded_reviewed_construction_artifact(
    path: Path,
    row: Mapping[str, Any],
    *,
    label: str,
) -> None:
    existing = _read_bounded_reviewed_construction_artifact(path, label=label)
    if existing is not None and existing != dict(row):
        raise ValueError(f"{label} authority slot conflicts")
    if existing is None:
        payload = json.dumps(dict(row), indent=2, sort_keys=True) + "\n"
        if len(payload.encode("utf-8")) > _MAX_REVIEWED_CONSTRUCTION_ARTIFACT_BYTES:
            raise ValueError(f"{label} exceeds its byte ceiling")
        write_json_atomic(path, dict(row))


def _lineage_synthesis_input_owner_path(
    directory: Path,
    input_sha256: Any,
) -> Path:
    identity = _reviewed_construction_identity(
        input_sha256, label="lineage synthesis input"
    )
    return directory / f"lineage_synthesis_input.by-digest.{identity}.json"


def _family_member_ratification_owner_path(
    directory: Path,
    admission_sha256: Any,
) -> Path:
    identity = _reviewed_construction_identity(
        admission_sha256, label="family-member ratification admission"
    )
    return directory / (
        f"reviewed_family_member_ratification.by-admission.{identity}.json"
    )


def _family_exhaustion_observation_owner_path(
    directory: Path,
    execution_sha256: Any,
) -> Path:
    identity = _reviewed_construction_identity(
        execution_sha256, label="family exhaustion execution"
    )
    return directory / (
        f"reviewed_family_exhaustion_observation.by-family-execution.{identity}.json"
    )


def _construction_ratification_owner_path(
    directory: Path,
    *,
    contract: Any,
    boundary: Mapping[str, Any],
    prior_open_receipt: Any,
) -> Path:
    owner_identity = content_hash(
        {
            "schema": "leanmill.construction_ratification_owner.v1",
            "task_contract_sha256": str(contract.sha256),
            "outer_boundary_result_sha256": str(
                boundary.get("result_sha256") or ""
            ),
            "prior_open_receipt_sha256": content_hash(
                prior_open_receipt.to_dict()
            ),
        }
    )
    return directory / (
        f"construction_artifact_ratification.by-action.{owner_identity}.json"
    )


def _reviewed_family_synthesis_provenance(
    directory: Path,
    run: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Resolve the exact persisted synthesis input for the active request."""

    navigation = run.get("navigation")
    if not isinstance(navigation, Mapping):
        raise ValueError("family discharge has no frozen navigation")
    raw_decision = navigation.get("lineage_synthesis")
    if not isinstance(raw_decision, Mapping):
        return None
    decision = dict(raw_decision)
    if (
        decision.get("schema") != "leanmill.lineage_synthesis_decision.v1"
        or decision.get("route") != "escalate_language"
    ):
        return None
    input_ref = str(decision.get("input_sha256") or "")
    if not input_ref:
        return None
    input_ref = _reviewed_construction_identity(
        input_ref, label="family discharge synthesis input"
    )
    matches: dict[str, dict[str, Any]] = {}
    owner_path = _lineage_synthesis_input_owner_path(directory, input_ref)
    owner = _read_bounded_reviewed_construction_artifact(
        owner_path, label="family discharge synthesis input"
    )
    candidate_rows: list[tuple[Path, dict[str, Any]]] = []
    if owner is not None:
        candidate_rows.append((owner_path, owner))
    else:
        epoch = int(decision.get("context_epoch", -1))
        if epoch < 0:
            raise ValueError("family discharge synthesis epoch is malformed")
        legacy_pattern = re.compile(
            rf"lineage_synthesis_input\.epoch-{epoch:03d}"
            rf"(?:\.wave-[0-9]{{3}})?\.json"
        )
        for path in _bounded_reviewed_construction_legacy_paths(
            directory,
            filename_pattern=legacy_pattern,
            label="family discharge synthesis input",
        ):
            raw = _read_bounded_reviewed_construction_artifact(
                path, label="family discharge synthesis input"
            )
            if raw is not None and raw.get("input_sha256") == input_ref:
                candidate_rows.append((path, raw))
    for _path, row in candidate_rows:
        core = {key: value for key, value in row.items() if key != "input_sha256"}
        if (
            row.get("schema") != "leanmill.lineage_synthesis_input.v1"
            or row.get("input_sha256") != content_hash(core)
        ):
            raise ValueError("family discharge synthesis input changed identity")
        matches[content_hash(row)] = row
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("family discharge synthesis input has conflicting copies")
    synthesis_input = next(iter(matches.values()))
    _persist_bounded_reviewed_construction_artifact(
        owner_path,
        synthesis_input,
        label="family discharge synthesis input",
    )
    return synthesis_input, decision


def _existing_reviewed_family_member_ratification_aggregate(
    directory: Path,
    admission: Mapping[str, Any],
) -> dict[str, Any] | None:
    from ztare.leanmill.reviewed_family_member_ratification import (
        validate_reviewed_family_member_ratification_aggregate,
    )

    admission_ref = _reviewed_construction_identity(
        admission.get("receipt_sha256"),
        label="family-member ratification admission",
    )
    matches: dict[str, dict[str, Any]] = {}
    owner_path = _family_member_ratification_owner_path(directory, admission_ref)
    owner = _read_bounded_reviewed_construction_artifact(
        owner_path, label="family-member ratification aggregate"
    )
    candidates: list[dict[str, Any]] = []
    if owner is not None:
        candidates.append(owner)
    else:
        legacy_pattern = re.compile(
            r"reviewed_family_member_ratification\.[0-9a-f]{16}\.json"
        )
        for path in _bounded_reviewed_construction_legacy_paths(
            directory,
            filename_pattern=legacy_pattern,
            label="family-member ratification aggregate",
        ):
            raw = _read_bounded_reviewed_construction_artifact(
                path, label="family-member ratification aggregate"
            )
            if raw is not None and raw.get("admission_sha256") == admission_ref:
                candidates.append(raw)
    for raw in candidates:
        if raw.get("admission_sha256") != admission_ref:
            raise ValueError("family-member ratification owner crossed admission")
        if not isinstance(raw, Mapping):
            continue
        aggregate = validate_reviewed_family_member_ratification_aggregate(raw)
        matches[str(aggregate["aggregate_sha256"])] = aggregate
    if len(matches) > 1:
        raise ValueError("family-member ratification has conflicting first fires")
    aggregate = next(iter(matches.values()), None)
    if aggregate is not None:
        _persist_bounded_reviewed_construction_artifact(
            owner_path,
            aggregate,
            label="family-member ratification aggregate",
        )
    return aggregate


def _current_reviewed_family_objective_discharge(
    directory: Path,
    run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Replay the family-origin terminal transition from its immutable inputs."""

    navigation = run.get("navigation")
    raw = (
        navigation.get("reviewed_family_objective_discharge")
        if isinstance(navigation, Mapping)
        else None
    )
    if not isinstance(raw, Mapping):
        return None
    blueprint = FrontierTheoryBlueprint.from_json(
        read_json(directory / "blueprint.json", {})
    )
    from ztare.leanmill.reviewed_family_objective_discharge import (
        validate_reviewed_family_objective_discharge,
    )

    discharge = validate_reviewed_family_objective_discharge(
        raw, current_blueprint=blueprint
    )
    if discharge.get("source_run_digest") == run.get("run_digest"):
        raise ValueError("terminal family run replaced its pending source digest")
    expected_path = directory / (
        "reviewed_family_objective_discharge."
        + str(discharge["receipt_sha256"])[:16]
        + ".json"
    )
    persisted = _read_bounded_reviewed_construction_artifact(
        expected_path,
        label="family objective discharge",
    )
    if persisted != discharge:
        raise ValueError("family objective discharge lost its immutable artifact")
    return discharge


def _pending_reviewed_family_exhaustion_observation(
    directory: Path,
    *,
    current_blueprint: FrontierTheoryBlueprint | None = None,
    execution_refs: Sequence[str] = (),
) -> tuple[dict[str, Any], ...]:
    """Read immutable family-null observations owned by the current blueprint."""

    from ztare.leanmill.reviewed_family_exhaustion_discharge import (
        validate_reviewed_family_exhaustion_observation,
    )

    exact_refs = tuple(
        sorted(
            {
                str(ref)
                for ref in execution_refs
                if re.fullmatch(r"[0-9a-f]{64}", str(ref)) is not None
            }
        )
    )
    if len(exact_refs) > _MAX_REVIEWED_CONSTRUCTION_LEGACY_CANDIDATES:
        raise ValueError("family exhaustion execution-reference ceiling exceeded")
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for execution_ref in exact_refs:
        path = _family_exhaustion_observation_owner_path(
            directory, execution_ref
        )
        raw = _read_bounded_reviewed_construction_artifact(
            path, label="family exhaustion observation"
        )
        if raw is not None:
            candidates.append((path, raw))
    if not candidates:
        legacy_pattern = re.compile(
            r"reviewed_family_exhaustion_observation\.[0-9a-f]{16}\.json"
        )
        for path in _bounded_reviewed_construction_legacy_paths(
            directory,
            filename_pattern=legacy_pattern,
            label="family exhaustion observation",
        ):
            raw = _read_bounded_reviewed_construction_artifact(
                path, label="family exhaustion observation"
            )
            if raw is not None:
                candidates.append((path, raw))

    rows: dict[str, dict[str, Any]] = {}
    for _path, raw in candidates:
        row = validate_reviewed_family_exhaustion_observation(raw)
        execution_ref = _reviewed_construction_identity(
            row.get("finite_family_execution_sha256"),
            label="family exhaustion execution",
        )
        if exact_refs and execution_ref not in set(exact_refs):
            continue
        if (
            current_blueprint is not None
            and row.get("blueprint_id") != current_blueprint.blueprint_id
        ):
            continue
        _persist_bounded_reviewed_construction_artifact(
            _family_exhaustion_observation_owner_path(directory, execution_ref),
            row,
            label="family exhaustion observation",
        )
        rows[str(row["receipt_sha256"])] = row
    return tuple(rows[key] for key in sorted(rows))


def _current_reviewed_family_exhaustion_discharge(
    directory: Path,
    run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Replay a completed family-null transition from its immutable artifact."""

    navigation = run.get("navigation")
    raw = (
        navigation.get("reviewed_family_exhaustion_discharge")
        if isinstance(navigation, Mapping)
        else None
    )
    if not isinstance(raw, Mapping):
        return None
    blueprint = FrontierTheoryBlueprint.from_json(
        read_json(directory / "blueprint.json", {})
    )
    from ztare.leanmill.reviewed_family_exhaustion_discharge import (
        validate_reviewed_family_exhaustion_discharge,
    )

    discharge = validate_reviewed_family_exhaustion_discharge(
        raw, current_blueprint=blueprint
    )
    if discharge.get("next_representation_run_digest") == run.get("run_digest"):
        raise ValueError("terminal family-null run replaced its successor source")
    path = directory / (
        "reviewed_family_exhaustion_discharge."
        + str(discharge["receipt_sha256"])[:16]
        + ".json"
    )
    persisted = _read_bounded_reviewed_construction_artifact(
        path,
        label="family exhaustion discharge",
    )
    if persisted != discharge:
        raise ValueError("family exhaustion discharge lost its immutable artifact")
    return discharge


def _maybe_finalize_reviewed_family_exhaustion(
    directory: Path,
    *,
    blueprint: FrontierTheoryBlueprint,
) -> dict[str, Any] | None:
    """Close only after a later leaf authors an execution-bound representation."""

    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        return None
    if _current_reviewed_family_exhaustion_discharge(directory, run) is not None:
        return dict(run)
    navigation = run.get("navigation")
    if (
        run.get("status") != "frontier_language_expansion_requested"
        or not isinstance(navigation, Mapping)
        or not isinstance(navigation.get("language_expansion_request"), Mapping)
        or not isinstance(navigation.get("lineage_synthesis"), Mapping)
    ):
        return None
    next_request = TheoryLanguageExpansionRequest.from_json(
        navigation["language_expansion_request"]
    )
    observations = tuple(
        row
        for row in _pending_reviewed_family_exhaustion_observation(
            directory,
            current_blueprint=blueprint,
            execution_refs=tuple(str(ref) for ref in next_request.evidence_refs),
        )
        if row["finite_family_execution_sha256"]
        in set(next_request.evidence_refs)
    )
    if not observations:
        return None
    if len(observations) != 1:
        raise ValueError(
            "next representation ambiguously cites multiple exhausted families"
        )
    observation = observations[0]
    feedback_matches = [
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
        and row.get("schema")
        == "leanmill.theory_language_compilation_feedback.v1"
        and row.get("request_id") == observation["language_request_id"]
        and observation["finite_family_execution_sha256"]
        in set(row.get("evidence_refs") or ())
    ]
    if len(feedback_matches) != 1:
        return None
    feedback = feedback_matches[0]
    wave = _language_feedback_wave_binding(directory, feedback)
    if wave is None:
        return None
    required_refs = {
        str(observation["finite_family_execution_sha256"]),
        str(feedback["receipt_sha256"]),
    }
    if not required_refs <= set(next_request.evidence_refs):
        return None

    from ztare.leanmill.reviewed_family_exhaustion_discharge import (
        build_reviewed_family_exhaustion_discharge,
    )

    discharge = build_reviewed_family_exhaustion_discharge(
        observation=observation,
        feedback=feedback,
        feedback_wave_binding=wave,
        next_representation_run=run,
    )
    path = directory / (
        "reviewed_family_exhaustion_discharge."
        + str(discharge["receipt_sha256"])[:16]
        + ".json"
    )
    _persist_bounded_reviewed_construction_artifact(
        path,
        discharge,
        label="family exhaustion discharge",
    )

    from ztare.leanmill.campaign_closure_gate import (
        lineage_dispositions_from_reviewed_family_exhaustion_discharge,
    )

    dispositions = lineage_dispositions_from_reviewed_family_exhaustion_discharge(
        discharge, current_blueprint=blueprint
    )
    for disposition in dispositions:
        _persist_terminal_obligation_receipt(
            directory,
            prefix="lineage_disposition",
            identity=_lineage_disposition_storage_identity(disposition),
            receipt=disposition,
        )
    terminal_navigation = dict(navigation)
    terminal_navigation["reviewed_family_exhaustion_discharge"] = discharge
    core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "status": "frontier_objective_discharged",
        "navigation": terminal_navigation,
    }
    updated = {**core, "run_digest": content_hash(core)}
    write_json_atomic(directory / "run.json", updated)
    return updated


def _pending_construction_artifact_ratifications(
    directory: Path,
    run: Mapping[str, Any],
    completion: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Read construction obligations whose intermediate bundle was consumed."""

    from ztare.common.task_discharge import bind_task_discharge_receipt
    from ztare.leanmill.construction_artifact_ratification import (
        CONSTRUCTION_ARTIFACT_RATIFICATION_CAPABILITY,
    )
    from ztare.leanmill.theory_task_discharge_successor import (
        CONSTRUCTION_RATIFICATION_TRANSITION_KEY,
    )

    completion = (
        dict(completion)
        if isinstance(completion, Mapping)
        else read_json(directory / "boundary_completion.json", None)
    )
    if not isinstance(completion, Mapping):
        return ()
    if not completion:
        # The lifecycle reader uses an empty mapping to represent an absent
        # boundary completion.  Only non-empty, signed rows enter replay.
        return ()
    completion_core = {
        key: item for key, item in completion.items() if key != "completion_sha256"
    }
    if completion.get("completion_sha256") != content_hash(completion_core):
        raise ValueError("construction ratification completion digest mismatch")
    boundary = completion.get("boundary_result")
    bundle = completion.get("theory_task_discharge")
    if not isinstance(boundary, Mapping) or not isinstance(bundle, Mapping):
        return ()
    boundary_core = {
        key: item for key, item in boundary.items() if key != "result_sha256"
    }
    bundle_core = {
        key: item for key, item in bundle.items() if key != "receipt_sha256"
    }
    boundary_ref = str(boundary.get("result_sha256") or "")
    bundle_ref = str(bundle.get("receipt_sha256") or "")
    if (
        boundary_ref != content_hash(boundary_core)
        or bundle_ref != content_hash(bundle_core)
        or bundle.get("boundary_result_sha256") != boundary_ref
        or CONSTRUCTION_RATIFICATION_TRANSITION_KEY in bundle
    ):
        raise ValueError("construction ratification predecessor does not replay")
    navigation = run.get("navigation")
    consumption = (
        navigation.get("theory_task_discharge")
        if isinstance(navigation, Mapping)
        else None
    )
    if (
        not isinstance(consumption, Mapping)
        or consumption.get("bundle_receipt_sha256") != bundle_ref
    ):
        return ()

    pending: list[dict[str, Any]] = []
    for raw in bundle.get("rows") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("construction ratification predecessor row is malformed")
        row = dict(raw)
        row_core = {
            key: item for key, item in row.items() if key != "receipt_sha256"
        }
        contract, receipt = bind_task_discharge_receipt(
            row.get("contract") or {}, row.get("receipt") or {}
        )
        observed = receipt.observed if isinstance(receipt.observed, Mapping) else {}
        if (
            row.get("receipt_sha256") != content_hash(row_core)
            or row.get("contract_sha256") != contract.sha256
        ):
            raise ValueError("construction ratification predecessor row changed")
        if (
            row.get("source") == "explicit_task"
            and receipt.status == "open"
            and observed.get("next_obligation")
            == CONSTRUCTION_ARTIFACT_RATIFICATION_CAPABILITY
        ):
            pending.append(
                {
                    "program_id": str(row.get("program_id") or ""),
                    "contract": contract,
                    "prior_open_receipt": receipt,
                    "predecessor_row_receipt_sha256": str(
                        row["receipt_sha256"]
                    ),
                }
            )
    return tuple(pending)


def _existing_construction_ratification_aggregate(
    directory: Path,
    *,
    contract: Any,
    boundary: Mapping[str, Any],
    prior_open_receipt: Any,
) -> dict[str, Any] | None:
    from ztare.leanmill.construction_artifact_ratification import (
        validate_construction_artifact_ratification_aggregate,
    )

    owner_path = _construction_ratification_owner_path(
        directory,
        contract=contract,
        boundary=boundary,
        prior_open_receipt=prior_open_receipt,
    )
    owner = _read_bounded_reviewed_construction_artifact(
        owner_path, label="construction ratification aggregate"
    )
    matches: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    if owner is not None:
        candidates.append(owner)
    else:
        legacy_pattern = re.compile(
            r"construction_artifact_ratification\.[0-9a-f]{16}\.json"
        )
        for path in _bounded_reviewed_construction_legacy_paths(
            directory,
            filename_pattern=legacy_pattern,
            label="construction ratification aggregate",
        ):
            raw = _read_bounded_reviewed_construction_artifact(
                path, label="construction ratification aggregate"
            )
            if raw is not None:
                candidates.append(raw)
    for raw in candidates:
        if raw.get("task_contract_sha256") != contract.sha256:
            if owner is not None:
                raise ValueError("construction ratification owner crossed task")
            continue
        formal_input = (raw.get("ratification_result") or {}).get("formal_input")
        if (
            not isinstance(formal_input, Mapping)
            or formal_input.get("outer_boundary_result_sha256")
            != boundary.get("result_sha256")
        ):
            if owner is not None:
                raise ValueError("construction ratification owner crossed boundary")
            continue
        aggregate = validate_construction_artifact_ratification_aggregate(
            contract, boundary, prior_open_receipt, raw
        )
        matches[str(aggregate["aggregate_sha256"])] = aggregate
    if len(matches) > 1:
        raise ValueError("construction ratification action has conflicting first fires")
    aggregate = next(iter(matches.values()), None)
    if aggregate is not None:
        _persist_bounded_reviewed_construction_artifact(
            owner_path,
            aggregate,
            label="construction ratification aggregate",
        )
    return aggregate


def _classified_reviewed_family_unavailability(exc: Exception) -> dict[str, Any]:
    """Project one typed execution failure without discarding its coordinates."""

    from ztare.leanmill.construction_parameterization import (
        ConstructionBackendCapabilityUnavailable,
        ConstructionResourceCeilingExceeded,
    )
    from ztare.leanmill.finite_construction_family import (
        FiniteConstructionFamilyResourceUnavailable,
    )

    row: dict[str, Any] = {
        "reason_code": str(getattr(exc, "reason_code", str(exc))),
        "error_type": type(exc).__name__,
    }
    if isinstance(exc, ConstructionResourceCeilingExceeded):
        row.update(
            {
                "resource": str(exc.resource),
                "observed": int(exc.observed),
                "ceiling": int(exc.ceiling),
                "counters": dict(exc.counters),
                "certified_assignment_count": int(
                    exc.certified_assignment_count
                ),
                "attempted_assignment_count": int(
                    exc.attempted_assignment_count
                ),
            }
        )
    elif isinstance(exc, ConstructionBackendCapabilityUnavailable):
        row.update(
            {
                "operation": str(exc.operation),
                "adapter_id": str(exc.adapter_id),
                "capability_id": str(exc.capability_id),
                "cause_error_type": str(exc.error_type),
                "certified_assignment_count": int(
                    exc.certified_assignment_count
                ),
                "attempted_assignment_count": int(
                    exc.attempted_assignment_count
                ),
            }
        )
    elif isinstance(exc, FiniteConstructionFamilyResourceUnavailable):
        row.update(
            {
                "resource": "finite_construction_family_execution_bytes",
                "observed": int(exc.observed),
                "ceiling": int(exc.ceiling),
                "counters": {
                    "completed_members": int(exc.completed_members),
                    "attempted_members": int(exc.attempted_members),
                },
            }
        )
    elif isinstance(exc, BudgetLedgerResourceUnavailable):
        row.update(
            {
                "resource": "exploration_budget_ledger_bytes",
                "observed": int(exc.observed),
                "ceiling": int(exc.ceiling),
                "counters": {},
            }
        )
    return row


def _execute_reviewed_family_member_ratifications(
    directory: Path,
    run: Mapping[str, Any],
    admissions: Sequence[Mapping[str, Any]],
    *,
    lean_root: str | Path | None,
    timeout_s: int | None,
    ratify_fn: Callable[..., Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Advance family-origin verified artifacts without relabeling authorship."""

    from ztare.leanmill.finite_construction_family import (
        FiniteConstructionFamilyResourceUnavailable,
        construction_witness_interface,
        validate_finite_construction_family_execution,
    )
    from ztare.leanmill.construction_parameterization import (
        ConstructionBackendCapabilityUnavailable,
        ConstructionResourceCeilingExceeded,
    )
    from ztare.leanmill.reviewed_family_member_ratification import (
        ratify_reviewed_family_member_action,
        validate_reviewed_family_member_ratification_aggregate,
    )

    navigation = run.get("navigation")
    if not isinstance(navigation, Mapping):
        raise ValueError("family ratification requires frozen navigation")
    execution = validate_finite_construction_family_execution(
        navigation.get("finite_construction_family_execution") or {}
    )
    blueprint = FrontierTheoryBlueprint.from_json(
        read_json(directory / "blueprint.json", {})
    )
    request = _language_request_from_run(run)
    witness_interface = construction_witness_interface(
        blueprint.adapter_id, dict(blueprint.adapter_config)
    )
    root = (
        Path(lean_root)
        if lean_root is not None
        else Path(__file__).resolve().parents[3] / "ztare_proofs"
    )
    selected_timeout_s = (
        int(timeout_s)
        if timeout_s is not None
        else max(
            1,
            int(
                blueprint.verification_plan.get(
                    "formal_task_timeout_ms",
                    blueprint.verification_plan.get("lean_timeout_ms", 500_000),
                )
            )
            // 1_000,
        )
    )
    if selected_timeout_s < 1:
        raise ValueError("family construction ratification timeout must be positive")
    family_ratifier = ratify_fn or ratify_reviewed_family_member_action

    budget_row = read_json(directory / "budget.json", None)
    ledger = None
    ledger_open_error: BudgetLedgerResourceUnavailable | None = None
    if isinstance(budget_row, Mapping):
        try:
            ledger = ExplorationBudgetLedger(
                directory / "budget.events.jsonl",
                ExplorationBudget.from_json(budget_row),
                attempt_id=directory.name,
            )
            ledger.recover_interrupted_wall_clock()
            ledger.recover_interrupted_reservations()
            ledger.resume_wall_clock()
        except BudgetLedgerResourceUnavailable as exc:
            ledger_open_error = exc
            ledger = None

    aggregates: list[dict[str, Any]] = []
    budget_error: BudgetExceeded | None = None
    cold_replay_error: dict[str, Any] | None = None
    formal_stage_error: dict[str, Any] | None = None
    replay_stage = "cold_replay"
    provider_calls_before = (
        int(ledger.state()["usage"]["provider_calls"])
        if ledger is not None
        else 0
    )
    try:
        if ledger_open_error is not None:
            raise ledger_open_error
        if ledger is None:
            raise BudgetExceeded("missing_exploration_budget")
        admissions = _replay_reviewed_family_member_ratification_admissions(
            directory,
            execution=execution,
            request=request,
            witness_interface=witness_interface,
            admissions=admissions,
            budget_ledger=ledger,
        )
        replay_stage = "formal_ratification"
        for admission in admissions:
            aggregate = _existing_reviewed_family_member_ratification_aggregate(
                directory, admission
            )
            if aggregate is None:
                admission_ref = str(admission.get("receipt_sha256") or "")
                reservation = (
                    ledger.reserve(
                        f"boundary:family-construction-ratification:{admission_ref}",
                        "boundary",
                        {
                            "lean_attempts": 1,
                            "lean_millis": selected_timeout_s * 1_000,
                        },
                    )
                    if ledger is not None
                    else None
                )
                started_ns = time.monotonic_ns()
                try:
                    aggregate = validate_reviewed_family_member_ratification_aggregate(
                        dict(
                            family_ratifier(
                                admission,
                                substrate=root,
                                timeout_s=selected_timeout_s,
                            )
                        )
                    )
                except Exception:
                    if ledger is not None and reservation is not None:
                        ledger.commit(reservation)
                    raise
                result = aggregate["ratification_result"]
                if ledger is not None and reservation is not None:
                    if result.get("stage") in {"formal_interface", "formal_certificate"}:
                        ledger.release(
                            reservation,
                            reason="family_construction_ratification_pre_kernel_unavailable",
                        )
                    else:
                        elapsed_ms = max(
                            1, (time.monotonic_ns() - started_ns) // 1_000_000
                        )
                        ledger.commit(
                            reservation,
                            {
                                "lean_attempts": 1,
                                "lean_millis": min(
                                    selected_timeout_s * 1_000, elapsed_ms
                                ),
                            },
                        )
                aggregate_path = _family_member_ratification_owner_path(
                    directory,
                    admission_ref,
                )
                _persist_bounded_reviewed_construction_artifact(
                    aggregate_path,
                    aggregate,
                    label="family-member ratification aggregate",
                )
            else:
                aggregate = validate_reviewed_family_member_ratification_aggregate(
                    aggregate
                )
            aggregates.append(aggregate)
            if aggregate.get("status") == "ratified":
                break
    except BudgetExceeded as exc:
        if replay_stage == "cold_replay":
            cold_replay_error = {
                "reason_code": exc.reason,
                "error_type": type(exc).__name__,
            }
        else:
            budget_error = exc
    except BudgetLedgerResourceUnavailable as exc:
        classified = _classified_reviewed_family_unavailability(exc)
        if replay_stage == "cold_replay":
            cold_replay_error = classified
        else:
            formal_stage_error = classified
    except (
        ConstructionBackendCapabilityUnavailable,
        ConstructionResourceCeilingExceeded,
        FiniteConstructionFamilyResourceUnavailable,
    ) as exc:
        cold_replay_error = _classified_reviewed_family_unavailability(exc)
    finally:
        if ledger is not None:
            provider_calls_changed = (
                int(ledger.state()["usage"]["provider_calls"])
                != provider_calls_before
            )
            ledger.freeze_wall_clock(reason="family_construction_ratification_runner_exit")
            if provider_calls_changed:
                raise ValueError("family cold replay consumed provider calls")

    attempted_refs = [str(row["aggregate_sha256"]) for row in aggregates]
    ratified = next(
        (row for row in aggregates if row.get("status") == "ratified"), None
    )
    feedback_override: tuple[str, str] | None = None
    cold_replay_receipt: dict[str, Any] | None = None
    formal_stage_receipt: dict[str, Any] | None = None
    if cold_replay_error is not None:
        reason_code = str(cold_replay_error["reason_code"])
        replay_core = {
            "schema": "leanmill.reviewed_family_cold_replay_unavailable.v1",
            "family_execution_receipt_sha256": str(execution["receipt_sha256"]),
            "family_receipt_sha256": str(execution["family_receipt_sha256"]),
            "context_hash": str(execution["context_hash"]),
            "adapter_id": str(execution["adapter_id"]),
            "stage": "cold_replay",
            **cold_replay_error,
            "provider_calls_before": provider_calls_before,
            "provider_calls_after": (
                int(ledger.state()["usage"]["provider_calls"])
                if ledger is not None
                else 0
            ),
            "outcome": "unavailable",
            "authority": "frontier_campaign_state_machine",
        }
        cold_replay_receipt = {
            **replay_core,
            "receipt_sha256": content_hash(replay_core),
        }
        replay_path = directory / (
            "reviewed_family_cold_replay_unavailable."
            + cold_replay_receipt["receipt_sha256"][:16]
            + ".json"
        )
        _persist_bounded_reviewed_construction_artifact(
            replay_path,
            cold_replay_receipt,
            label="family cold-replay unavailable receipt",
        )
        feedback_override = (
            "unavailable",
            "reviewed_family_cold_replay_unavailable:" + reason_code,
        )
    if budget_error is not None:
        feedback_override = (
            "unavailable",
            "reviewed_family_member_ratification_budget_unavailable:"
            + budget_error.reason,
        )
    if formal_stage_error is not None:
        reason_code = str(formal_stage_error["reason_code"])
        formal_core = {
            "schema": "leanmill.reviewed_family_formal_stage_unavailable.v1",
            "family_execution_receipt_sha256": str(execution["receipt_sha256"]),
            "family_receipt_sha256": str(execution["family_receipt_sha256"]),
            "context_hash": str(execution["context_hash"]),
            "adapter_id": str(execution["adapter_id"]),
            "stage": "formal_ratification",
            **formal_stage_error,
            "provider_calls_before": provider_calls_before,
            "provider_calls_after": (
                int(ledger.state()["usage"]["provider_calls"])
                if ledger is not None
                else 0
            ),
            "outcome": "unavailable",
            "authority": "frontier_campaign_state_machine",
        }
        formal_stage_receipt = {
            **formal_core,
            "receipt_sha256": content_hash(formal_core),
        }
        _persist_bounded_reviewed_construction_artifact(
            directory
            / (
                "reviewed_family_formal_stage_unavailable."
                + formal_stage_receipt["receipt_sha256"][:16]
                + ".json"
            ),
            formal_stage_receipt,
            label="family formal-stage unavailable receipt",
        )
        feedback_override = (
            "unavailable",
            "reviewed_family_formal_stage_unavailable:" + reason_code,
        )
    if ratified is not None and feedback_override is None:
        admission_by_ref = {
            str(row.get("receipt_sha256") or ""): dict(row) for row in admissions
        }
        ratified_admission = admission_by_ref.get(
            str(ratified.get("admission_sha256") or "")
        )
        if ratified_admission is None:
            raise ValueError("ratified family aggregate lost its admission")
        request = _language_request_from_run(run)
        provenance = _reviewed_family_synthesis_provenance(directory, run)
        frozen_lineages = _frozen_terminal_lineage_ids(navigation)
        if provenance is None or not frozen_lineages:
            feedback_override = (
                "unavailable",
                "reviewed_family_objective_discharge_provenance_unavailable",
            )
        else:
            synthesis_input, synthesis_decision = provenance
            from ztare.leanmill.reviewed_family_objective_discharge import (
                build_reviewed_family_objective_discharge,
            )

            discharge = build_reviewed_family_objective_discharge(
                source_pending_run=run,
                blueprint=blueprint,
                active_request=request,
                synthesis_input=synthesis_input,
                synthesis_decision=synthesis_decision,
                family_execution=execution,
                admission=ratified_admission,
                ratification_aggregate=ratified,
                attempted_ratification_aggregate_sha256s=attempted_refs,
                frozen_lineage_ids=frozen_lineages,
            )
    if ratified is not None and feedback_override is None:
        discharge_path = directory / (
            "reviewed_family_objective_discharge."
            + str(discharge["receipt_sha256"])[:16]
            + ".json"
        )
        _persist_bounded_reviewed_construction_artifact(
            discharge_path,
            discharge,
            label="family objective discharge",
        )
        from ztare.leanmill.campaign_closure_gate import (
            lineage_dispositions_from_reviewed_family_objective_discharge,
        )

        dispositions = lineage_dispositions_from_reviewed_family_objective_discharge(
            discharge, current_blueprint=blueprint
        )
        for disposition in dispositions:
            _persist_terminal_obligation_receipt(
                directory,
                prefix="lineage_disposition",
                identity=_lineage_disposition_storage_identity(disposition),
                receipt=disposition,
            )
        current_navigation = dict(navigation)
        current_navigation["reviewed_family_objective_discharge"] = discharge
        current_navigation["reviewed_family_member_ratification_aggregate_sha256s"] = (
            attempted_refs
        )
        run_core = {
            **{key: value for key, value in run.items() if key != "run_digest"},
            "status": "frontier_objective_discharged",
            "navigation": current_navigation,
        }
        updated = {**run_core, "run_digest": content_hash(run_core)}
        write_json_atomic(directory / "run.json", updated)
        completion_status = "objective_discharged"
        feedback_ref = ""
    else:
        results = [dict(row["ratification_result"]) for row in aggregates]
        unavailable = (
            feedback_override is not None and feedback_override[0] == "unavailable"
        ) or (
            bool(results)
            and all(row.get("status") == "unavailable" for row in results)
        )
        reason = (
            feedback_override[1]
            if feedback_override is not None
            else ";".join(
                dict.fromkeys(str(row.get("reason_code") or "") for row in results)
            )
            or "family_ratification_returned_no_result"
        )
        evidence_receipts: tuple[Mapping[str, Any], ...] = (
            execution,
            *tuple(dict(row) for row in admissions),
            *tuple(results),
            *((cold_replay_receipt,) if cold_replay_receipt is not None else ()),
            *((formal_stage_receipt,) if formal_stage_receipt is not None else ()),
        )
        evidence_refs = tuple(
            dict.fromkeys(
                [
                    str(execution["receipt_sha256"]),
                    *[str(row["receipt_sha256"]) for row in admissions],
                    *[str(row["receipt_sha256"]) for row in results],
                    *attempted_refs,
                    *(
                        [str(cold_replay_receipt["receipt_sha256"])]
                        if cold_replay_receipt is not None
                        else []
                    ),
                    *(
                        [str(formal_stage_receipt["receipt_sha256"])]
                        if formal_stage_receipt is not None
                        else []
                    ),
                ]
            )
        )
        feedback = _language_outcome_feedback(
            directory,
            run,
            outcome="unavailable" if unavailable else "rejected",
            reason=(
                reason
                if feedback_override is not None
                else "reviewed_family_member_ratification:" + reason
            ),
            evidence_refs=evidence_refs,
            evidence_receipts=evidence_receipts,
        )
        updated = read_json(directory / "run.json", {})
        completion_status = "returned_to_navigation"
        feedback_ref = str(feedback["receipt_sha256"])

    core = {
        "schema": "leanmill.reviewed_family_member_ratification_completion.v1",
        "status": completion_status,
        "attempt_dir": str(directory),
        "family_execution_receipt_sha256": str(execution["receipt_sha256"]),
        "admission_sha256s": [
            str(row.get("receipt_sha256") or "") for row in admissions
        ],
        "aggregate_sha256s": attempted_refs,
        "feedback_receipt_sha256": feedback_ref,
        "run_digest": str(updated.get("run_digest") or ""),
        "authority": "frontier_campaign_state_machine",
    }
    completion = {**core, "receipt_sha256": content_hash(core)}
    path = directory / (
        "reviewed_family_member_ratification_completion."
        + str(completion["receipt_sha256"])[:16]
        + ".json"
    )
    existing = read_json(path, None)
    if isinstance(existing, Mapping) and dict(existing) != completion:
        raise ValueError("family ratification completion path conflicts")
    if existing is None:
        write_json_atomic(path, completion)
    return completion


def execute_frontier_construction_artifact_ratification(
    attempt_dir: str | Path,
    *,
    lean_root: str | Path | None = None,
    timeout_s: int | None = None,
    ratify_fn: Callable[..., Mapping[str, Any]] | None = None,
    family_ratify_fn: Callable[..., Mapping[str, Any]] | None = None,
    _attempt_lease: _FrontierAttemptLease | None = None,
) -> dict[str, Any]:
    """Advance verified construction tasks through provider-free governance."""

    directory = Path(attempt_dir)
    if _attempt_lease is None:
        with frontier_attempt_lease(
            directory, action="construction_artifact_ratification"
        ) as lease:
            return execute_frontier_construction_artifact_ratification(
                directory,
                lean_root=lean_root,
                timeout_s=timeout_s,
                ratify_fn=ratify_fn,
                family_ratify_fn=family_ratify_fn,
                _attempt_lease=lease,
            )
    _bind_active_attempt_epoch(_attempt_lease, directory)
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("construction ratification requires an active run")
    family_pending = _pending_reviewed_family_member_ratifications(
        directory, run
    )
    if family_pending:
        return _execute_reviewed_family_member_ratifications(
            directory,
            run,
            family_pending,
            lean_root=lean_root,
            timeout_s=timeout_s,
            ratify_fn=family_ratify_fn,
        )
    if _current_reviewed_family_objective_discharge(directory, run) is not None:
        return {
            "schema": "leanmill.construction_artifact_ratification_completion.v1",
            "status": "no_pending_construction_ratification",
            "attempt_dir": str(directory),
            "run_digest": str(run.get("run_digest") or ""),
        }
    completion = read_json(directory / "boundary_completion.json", None)
    if not isinstance(completion, Mapping):
        raise ValueError("construction ratification requires a completed boundary")
    pending = _pending_construction_artifact_ratifications(
        directory, run, completion
    )
    if not pending:
        return {
            "schema": "leanmill.construction_artifact_ratification_completion.v1",
            "status": "no_pending_construction_ratification",
            "attempt_dir": str(directory),
            "run_digest": str(run.get("run_digest") or ""),
        }

    boundary = dict(completion["boundary_result"])
    predecessor = dict(completion["theory_task_discharge"])
    root = (
        Path(lean_root)
        if lean_root is not None
        else Path(__file__).resolve().parents[3] / "ztare_proofs"
    )
    blueprint = FrontierTheoryBlueprint.from_json(
        read_json(directory / "blueprint.json", {})
    )
    selected_timeout_s = (
        int(timeout_s)
        if timeout_s is not None
        else max(
            1,
            int(
                blueprint.verification_plan.get(
                    "formal_task_timeout_ms",
                    blueprint.verification_plan.get("lean_timeout_ms", 500_000),
                )
            )
            // 1_000,
        )
    )
    if selected_timeout_s < 1:
        raise ValueError("construction ratification timeout must be positive")
    if ratify_fn is None:
        from ztare.leanmill.construction_artifact_ratification import (
            ratify_construction_artifact_action,
        )

        ratify_fn = ratify_construction_artifact_action

    budget_row = read_json(directory / "budget.json", None)
    ledger = None
    if isinstance(budget_row, Mapping):
        ledger = ExplorationBudgetLedger(
            directory / "budget.events.jsonl",
            ExplorationBudget.from_json(budget_row),
            attempt_id=directory.name,
        )
        ledger.recover_interrupted_wall_clock()
        ledger.recover_interrupted_reservations()
        ledger.resume_wall_clock()

    replacements: list[dict[str, Any]] = []
    aggregate_refs: list[str] = []
    try:
        for row in pending:
            contract = row["contract"]
            prior = row["prior_open_receipt"]
            aggregate = _existing_construction_ratification_aggregate(
                directory,
                contract=contract,
                boundary=boundary,
                prior_open_receipt=prior,
            )
            if aggregate is None:
                from ztare.leanmill.construction_artifact_ratification import (
                    validate_construction_artifact_ratification_aggregate,
                )

                reservation = (
                    ledger.reserve(
                        f"boundary:construction-ratification:{contract.sha256}",
                        "boundary",
                        {
                            "lean_attempts": 1,
                            "lean_millis": selected_timeout_s * 1_000,
                        },
                    )
                    if ledger is not None
                    else None
                )
                started_ns = time.monotonic_ns()
                try:
                    aggregate = validate_construction_artifact_ratification_aggregate(
                        contract,
                        boundary,
                        prior,
                        dict(
                            ratify_fn(
                                contract,
                                boundary,
                                prior,
                                substrate=root,
                                timeout_s=selected_timeout_s,
                            )
                        )
                    )
                except Exception:
                    if ledger is not None and reservation is not None:
                        ledger.commit(reservation)
                    raise
                result = aggregate.get("ratification_result") or {}
                stage = str(result.get("stage") or "")
                if ledger is not None and reservation is not None:
                    if stage in {"formal_interface", "formal_certificate"}:
                        ledger.release(
                            reservation,
                            reason="construction_ratification_pre_kernel_unavailable",
                        )
                    else:
                        elapsed_ms = max(
                            1, (time.monotonic_ns() - started_ns) // 1_000_000
                        )
                        ledger.commit(
                            reservation,
                            {
                                "lean_attempts": 1,
                                "lean_millis": min(
                                    selected_timeout_s * 1_000, elapsed_ms
                                ),
                            },
                        )
                aggregate_path = _construction_ratification_owner_path(
                    directory,
                    contract=contract,
                    boundary=boundary,
                    prior_open_receipt=prior,
                )
                _persist_bounded_reviewed_construction_artifact(
                    aggregate_path,
                    aggregate,
                    label="construction ratification aggregate",
                )
            replacements.append(
                {
                    "program_id": row["program_id"],
                    "task_contract_sha256": contract.sha256,
                    "aggregate": aggregate,
                }
            )
            aggregate_refs.append(str(aggregate["aggregate_sha256"]))
    finally:
        if ledger is not None:
            ledger.freeze_wall_clock(reason="construction_ratification_runner_exit")

    from ztare.leanmill.theory_task_discharge_successor import (
        build_construction_ratification_successor_bundle,
    )

    successor = build_construction_ratification_successor_bundle(
        predecessor, boundary, replacements
    )
    successor_path = directory / (
        "theory_task_discharge."
        + str(successor["receipt_sha256"])[:16]
        + ".json"
    )
    existing_successor = read_json(successor_path, None)
    if isinstance(existing_successor, Mapping) and dict(existing_successor) != successor:
        raise ValueError("construction ratification successor path conflicts")
    if existing_successor is None:
        write_json_atomic(successor_path, successor)

    updated = _consume_theory_task_discharge(
        directory,
        read_json(directory / "run.json", run),
        {"boundary_result": boundary, "theory_task_discharge": successor},
    )
    core = {
        "schema": "leanmill.construction_artifact_ratification_completion.v1",
        "status": (
            "objective_discharged"
            if updated.get("status") == "frontier_objective_discharged"
            else "successor_consumed_open"
        ),
        "attempt_dir": str(directory),
        "predecessor_bundle_receipt_sha256": str(predecessor["receipt_sha256"]),
        "successor_bundle_receipt_sha256": str(successor["receipt_sha256"]),
        "aggregate_sha256s": sorted(aggregate_refs),
        "run_digest": str(updated.get("run_digest") or ""),
        "authority": "frontier_campaign_state_machine",
    }
    result = {**core, "receipt_sha256": content_hash(core)}
    result_path = directory / (
        "construction_artifact_ratification_completion."
        + str(result["receipt_sha256"])[:16]
        + ".json"
    )
    existing_result = read_json(result_path, None)
    if isinstance(existing_result, Mapping) and dict(existing_result) != result:
        raise ValueError("construction ratification completion path conflicts")
    if existing_result is None:
        write_json_atomic(result_path, result)
    return result


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


def _candidate_matches_evaluation_contract(candidate: Mapping[str, Any]) -> bool:
    """Bind active theory programs to the evaluator that certified residuality."""

    if not isinstance(candidate.get("theory_program"), Mapping):
        # Historical compact packs have no executable program identity.  Their
        # deterministic replay remains the compatibility boundary.
        return True
    if (
        str(candidate.get("baseline_evaluator_ref") or "")
        != CHEAP_CONSEQUENCE_EVALUATOR_REF
    ):
        return False
    targets = {
        str(row) for row in candidate.get("boundary_target_ids") or ()
    }
    residual_targets = {
        str(row)
        for row in candidate.get("residual_prediction_formula_ids") or ()
    }
    return not targets or targets <= residual_targets


def _archive_stale_evaluation_candidates(
    directory: Path,
    run: Any,
) -> dict[str, Any] | Any:
    """Demote programs selected under a superseded consequence evaluator."""

    if not isinstance(run, Mapping) or not isinstance(run.get("navigation"), Mapping):
        return run
    navigation = dict(run["navigation"])
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
            if _candidate_matches_evaluation_contract(row):
                current.append(row)
                continue
            residual = row.get("residual_information_yield")
            archived.append(
                {
                    "collection": field,
                    "node_id": str(row.get("node_id") or ""),
                    "theory_program_id": str(row.get("theory_program_id") or ""),
                    "source_evaluator_ref": str(
                        row.get("baseline_evaluator_ref") or "legacy_unbound"
                    ),
                    "source_baseline_ref": str(
                        residual.get("baseline_ref")
                        if isinstance(residual, Mapping)
                        else ""
                    ),
                }
            )
        navigation[field] = current
    if not archived:
        return run
    archive_core = {
        "schema": "leanmill.candidate_evaluation_contract_supersession.v1",
        "status": "archived_superseded_evaluation_only",
        "current_evaluator_ref": CHEAP_CONSEQUENCE_EVALUATOR_REF,
        "context_hash": str(run.get("context_hash") or ""),
        "context_epoch": int(
            navigation.get(
                "context_epoch",
                (run.get("context_summary") or {}).get("context_epoch", 0),
            )
        ),
        "archived_candidates": archived,
        "route": "continue_search",
        "continuation_budget_phase": "navigation",
        "authority": "host_evaluation_identity_transition",
    }
    archive = {**archive_core, "receipt_sha256": content_hash(archive_core)}
    archive_path = directory / (
        "candidate_evaluation_contract_supersession."
        + str(archive["receipt_sha256"])[:16]
        + ".json"
    )
    prior = read_json(archive_path, None)
    if isinstance(prior, Mapping) and dict(prior) != archive:
        raise ValueError("candidate evaluation supersession changed identity")
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
    navigation.pop("pending_leaf_decision", None)
    run_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "status": "frontier_objective_unmet",
        "navigation": navigation,
    }
    updated = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(directory / "run.json", updated)
    return updated


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
    run: Any,
    completion: Any,
    *,
    governance_recheck: Mapping[str, Any] | None = None,
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
    if (
        isinstance(task_consumption, Mapping)
        and isinstance(task_consumption.get("successor_task_discharge"), Mapping)
    ):
        task_discharge = task_consumption["successor_task_discharge"]
    objective_task_status = str(
        task_consumption.get("objective_status") or "not_declared"
    ) if isinstance(task_consumption, Mapping) else "not_declared"
    typed_task_pending = objective_task_status in {"open", "unavailable"}
    governance_state = _boundary_governance_recheck_state(
        completion, governance_recheck
    )
    governance_statuses = governance_state["statuses"]

    def effective_status(row: Mapping[str, Any]) -> str:
        key = (
            tuple(str(value) for value in row.get("premise_formula_ids") or ()),
            str(row.get("target_formula_id") or ""),
        )
        replayed = governance_statuses.get(key)
        if (
            str(row.get("program_prediction_status") or "")
            == "kernel_verified_attributed"
            and replayed is not None
            and replayed != "proved_attributed"
        ):
            return "proof_rejected_by_governance"
        return str(row.get("program_prediction_status") or "")

    has_theory_rows = any(
        isinstance(row, Mapping) and row.get("candidate_kind") == "theory_program"
        for row in rows or ()
    )
    failed = any(
        isinstance(row, Mapping)
        and row.get("candidate_kind") == "theory_program"
        and effective_status(row) in _BOUNDARY_FAILURE_STATUSES
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
        key = (
            tuple(str(value) for value in row.get("premise_formula_ids") or ()),
            str(row.get("target_formula_id") or ""),
        )
        if key in governance_statuses and governance_state.get("receipt_sha256"):
            refs.append(str(governance_state["receipt_sha256"]))
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
            "status": effective_status(row),
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
        and type(row.get("schema")) is str
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
    history = navigation.get("objective_review_history") or ()
    latest = history[-1] if history and isinstance(history[-1], Mapping) else None
    return _objective_feedback_search_phase(latest)


def _objective_feedback_search_phase(feedback: Any) -> str:
    """Route continuation budget by the typed feedback transition."""

    if not isinstance(feedback, Mapping):
        return "navigation"
    declared = str(feedback.get("continuation_budget_phase") or "")
    if declared in {"navigation", "expansion"}:
        return declared
    if (
        feedback.get("schema")
        == "leanmill.candidate_evaluation_contract_supersession.v1"
    ):
        # Compatibility for receipts minted before the phase became explicit.
        return "navigation"
    return "expansion"


def _objective_resume_has_turn_capacity(
    ledger: ExplorationBudgetLedger,
    run: Mapping[str, Any] | None,
) -> bool:
    """Whether opening another objective search wave can fund one leaf turn."""

    if not isinstance(run, Mapping) or run.get("status") != "frontier_objective_unmet":
        return True
    phase = _objective_navigation_phase(run)
    return min(
        ledger.remaining_capacity(phase, "provider_calls"),
        ledger.remaining_capacity(phase, "agent_turns"),
    ) > 0


def _lineage_synthesis_retry_required(
    directory: Path,
    run: Mapping[str, Any] | None,
) -> bool:
    """A frozen synthesis input remains the next job until it is disposed."""

    navigation = (run or {}).get("navigation") or {}
    return bool(
        not isinstance(navigation.get("lineage_synthesis"), Mapping)
        and (
            (
                (run or {}).get("status") == "frontier_objective_unmet"
                and isinstance(
                    navigation.get("lineage_synthesis_budget_stop"), Mapping
                )
            )
            or _recovered_lineage_synthesis_required(directory, run)
        )
    )


def _recovered_lineage_synthesis_required(
    directory: Path,
    run: Mapping[str, Any] | None,
) -> bool:
    """Whether a recovered finalist still lacks a dispositive boundary row."""

    navigation = (run or {}).get("navigation") or {}
    if (
        (run or {}).get("status") != "budget_stopped"
        or navigation.get("recovered_from_durable_results") is not True
        or isinstance(navigation.get("lineage_synthesis"), Mapping)
    ):
        return False
    finalist_program_ids = {
        str(row.get("theory_program_id") or "")
        for row in navigation.get("finalists") or ()
        if isinstance(row, Mapping)
        and str(row.get("theory_program_id") or "")
    }
    if not finalist_program_ids:
        return False
    context_hash = str((run or {}).get("context_hash") or "")
    disposition_program_ids = [
        program_id
        for row in navigation.get("objective_review_history") or ()
        for program_id in [
            recovered_boundary_feedback_disposition_program_id(
                directory,
                row,
                context_hash=context_hash,
            )
        ]
        if program_id in finalist_program_ids
    ]
    disposed_program_ids = {
        program_id
        for program_id in finalist_program_ids
        if disposition_program_ids.count(program_id) == 1
    }
    return bool(finalist_program_ids - disposed_program_ids)


def _durable_synthesis_search_wave(path: Path) -> int:
    match = re.search(r"\.wave-(\d+)\.json$", path.name)
    return int(match.group(1)) if match else 0


def _empty_capacity_wave_projection(navigation: Mapping[str, Any]) -> bool:
    """Whether a read model contains only unfunded lineage placeholders."""

    lineages = navigation.get("lineages") or ()
    if not isinstance(lineages, (list, tuple)) or not lineages:
        return False
    if any(
        navigation.get(field)
        for field in (
            "finalists",
            "objective_survivors",
            "expansion_proposals",
            "theory_language_expansion_requests",
            "pending_leaf_decisions",
        )
    ):
        return False
    if int(navigation.get("wave_provider_calls", 0) or 0) != 0:
        return False
    return all(
        isinstance(row, Mapping)
        and isinstance(row.get("navigation"), Mapping)
        and (
            row["navigation"].get("navigation_exhausted_receipt") or {}
        ).get("reason")
        == "host_fair_share_has_no_turn_capacity"
        for row in lineages
    )


def _durable_synthesis_decision_for_input(
    directory: Path,
    input_path: Path,
    synthesis_input: Mapping[str, Any],
) -> tuple[dict[str, Any], Path] | None:
    """Revalidate a completed synthesis call against its immutable input."""

    wave = _durable_synthesis_search_wave(input_path)
    call_dir = directory / "agent_calls" / f"lineage_synthesizer.wave-{wave:03d}"
    expected_prompt = prompts.AXIOMPACK_LINEAGE_SYNTHESIS_PROMPT.format(
        synthesis_input_json=json.dumps(
            synthesis_input,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    expected_prompt_digest = content_hash({"prompt": expected_prompt})
    rows: list[tuple[int, dict[str, Any], Path]] = []
    for call_path in call_dir.glob("*.call.json"):
        try:
            index = int(call_path.name.split(".", 1)[0])
        except ValueError:
            continue
        call = read_json(call_path, None)
        prefix = call_path.with_suffix("").with_suffix("")
        prompt_path = prefix.with_suffix(".prompt.txt")
        result_path = prefix.with_suffix(".result.json")
        schema_path = prefix.with_suffix(".schema.json")
        if (
            not isinstance(call, Mapping)
            or call.get("schema") != "leanmill.frontier_subscription_role_call.v1"
            or call.get("role") != "lineage_synthesizer"
            or int(call.get("returncode", 1)) != 0
            or call.get("prompt_digest") != expected_prompt_digest
            or not prompt_path.is_file()
            or prompt_path.read_text(encoding="utf-8") != expected_prompt
            or not result_path.is_file()
        ):
            continue
        result_text = result_path.read_text(encoding="utf-8")
        if (
            call.get("result_digest")
            and call.get("result_digest")
            != content_hash({"result": result_text})
        ):
            raise ValueError("durable synthesis result digest mismatch")
        if call.get("output_schema_digest"):
            schema = read_json(schema_path, None)
            if (
                not isinstance(schema, Mapping)
                or content_hash(dict(schema)) != call["output_schema_digest"]
            ):
                raise ValueError("durable synthesis schema digest mismatch")
        decision = read_json(result_path, None)
        if not isinstance(decision, Mapping):
            raise ValueError("durable synthesis result is not an object")
        synthesis = validate_lineage_synthesis_decision(
            synthesis_input, decision
        )
        rows.append((index, synthesis, call_path))
    if not rows:
        return None
    _index, synthesis, call_path = max(rows, key=lambda row: row[0])
    return synthesis, call_path


def _latest_durable_synthesis_input(
    directory: Path,
    *,
    context_epoch: int,
    context_hash: str = "",
) -> tuple[int, Path, dict[str, Any]] | None:
    rows: list[tuple[int, Path, dict[str, Any]]] = []
    for input_path in directory.glob(
        f"lineage_synthesis_input.epoch-{context_epoch:03d}.wave-*.json"
    ):
        row = read_json(input_path, None)
        if not isinstance(row, Mapping):
            continue
        core = {
            key: value for key, value in row.items() if key != "input_sha256"
        }
        if (
            row.get("schema") != "leanmill.lineage_synthesis_input.v1"
            or row.get("input_sha256") != content_hash(core)
            or int(row.get("context_epoch", -1)) != context_epoch
            or (
                context_hash
                and str(row.get("context_hash") or "") != context_hash
            )
        ):
            continue
        rows.append(
            (_durable_synthesis_search_wave(input_path), input_path, dict(row))
        )
    return max(rows, key=lambda item: item[0]) if rows else None


def _durable_synthesis_can_project(
    navigation: Mapping[str, Any], synthesis_path: Path
) -> bool:
    """Keep synthesis recovery inside the search wave that owns it."""

    active_search_wave = (
        0
        if _empty_capacity_wave_projection(navigation)
        else int(navigation.get("search_wave", 0) or 0)
    )
    synthesis_search_wave = _durable_synthesis_search_wave(synthesis_path)
    epoch_match = re.search(r"\.epoch-(\d+)\.", synthesis_path.name)
    synthesis_epoch = int(epoch_match.group(1)) if epoch_match else -1
    context_hash = str(navigation.get("context_hash") or "")
    latest_input = (
        _latest_durable_synthesis_input(
            synthesis_path.parent,
            context_epoch=synthesis_epoch,
            context_hash=context_hash,
        )
        if synthesis_epoch >= 0
        else None
    )
    latest_owned_wave = max(
        active_search_wave,
        int(latest_input[0]) if latest_input is not None else 0,
    )
    return not (
        latest_owned_wave > 0
        and synthesis_search_wave > 0
        and synthesis_search_wave < latest_owned_wave
    )


def _pending_durable_lineage_synthesis(
    directory: Path,
    run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Find a validated synthesis successor before consulting a stale stop."""

    if run.get("status") != "frontier_objective_unmet":
        return None
    navigation = run.get("navigation")
    if not isinstance(navigation, Mapping) or isinstance(
        navigation.get("lineage_synthesis"), Mapping
    ):
        return None
    context_hash = str(run.get("context_hash") or "")
    context_epoch = int(
        navigation.get(
            "context_epoch",
            (run.get("context_summary") or {}).get("context_epoch", 0),
        )
    )
    empty_capacity_projection = _empty_capacity_wave_projection(navigation)
    superseded_synthesis_refs = {
        str(row.get("source_synthesis_receipt_sha256") or "")
        for row in (
            list(navigation.get("objective_review_history") or ())
            + [navigation.get("superseded_lineage_synthesis")]
        )
        if isinstance(row, Mapping)
        and row.get("schema")
        == "leanmill.lineage_synthesis_semantic_supersession.v1"
    }
    current_request_ids = {
        str(row.get("request_id") or "")
        for field in (
            "expansion_proposals",
            "theory_language_expansion_requests",
        )
        for row in navigation.get(field) or ()
        if isinstance(row, Mapping) and row.get("request_id")
    }
    candidate_rows = [
        row
        for field in ("finalists", "objective_survivors", "deferred_finalists")
        for row in navigation.get(field) or ()
        if isinstance(row, Mapping)
    ]
    candidate_rows.extend(
        row
        for lineage in navigation.get("lineages") or ()
        if isinstance(lineage, Mapping)
        for row in (lineage.get("navigation") or {}).get("finalists") or ()
        if isinstance(row, Mapping)
    )
    current_program_ids = {
        str(
            row.get("theory_program_id")
            or (row.get("theory_program") or {}).get("program_id")
            or ""
        )
        for row in candidate_rows
    }
    current_program_ids.discard("")
    for synthesis_path in reversed(
        sorted(directory.glob(f"lineage_synthesis.epoch-{context_epoch:03d}*.json"))
    ):
        synthesis = read_json(synthesis_path, None)
        if not isinstance(synthesis, Mapping):
            continue
        synthesis_core = {
            key: value for key, value in synthesis.items() if key != "receipt_sha256"
        }
        if (
            synthesis.get("schema") != "leanmill.lineage_synthesis_decision.v1"
            or synthesis.get("receipt_sha256") != content_hash(synthesis_core)
            or str(synthesis.get("context_hash") or "") != context_hash
            or int(synthesis.get("context_epoch", -1)) != context_epoch
        ):
            continue
        if str(synthesis.get("receipt_sha256") or "") in superseded_synthesis_refs:
            continue
        input_path = directory / synthesis_path.name.replace(
            "lineage_synthesis.", "lineage_synthesis_input.", 1
        )
        synthesis_input = read_json(input_path, None)
        if not isinstance(synthesis_input, Mapping):
            continue
        input_core = {
            key: value
            for key, value in synthesis_input.items()
            if key != "input_sha256"
        }
        if (
            synthesis_input.get("input_sha256") != content_hash(input_core)
            or synthesis.get("input_sha256") != synthesis_input.get("input_sha256")
            or str(synthesis_input.get("context_hash") or "") != context_hash
            or int(synthesis_input.get("context_epoch", -1)) != context_epoch
        ):
            continue
        decision_fields = (
            "route",
            "selected_request_ids",
            "deferred_request_ids",
            "rationale",
            "next_discriminator",
            "kill_condition",
            "program_ids",
            "next_discriminator_request_ids",
        )
        raw_decision = {field: synthesis.get(field) for field in decision_fields}
        if "continuation_mode" in synthesis:
            raw_decision["continuation_mode"] = synthesis.get("continuation_mode")
        if validate_lineage_synthesis_decision(
            synthesis_input, raw_decision
        ) != dict(synthesis):
            raise ValueError("durable lineage synthesis failed semantic replay")
        frozen_request_ids = {
            str(row.get("request_id") or "")
            for field in ("formula_requests", "theory_language_requests")
            for row in synthesis_input.get(field) or ()
            if isinstance(row, Mapping) and row.get("request_id")
        }
        selected_program_ids = {
            str(row) for row in synthesis.get("program_ids") or ()
        }
        if (
            (
                not empty_capacity_projection
                and current_request_ids != frozen_request_ids
            )
            or not selected_program_ids
            or (
                not empty_capacity_projection
                and not selected_program_ids <= current_program_ids
            )
        ):
            continue
        # A later search wave has already consumed or superseded every synthesis
        # decision from an earlier wave.  Recovering one of those decisions can
        # resurrect a boundary finalist after its outcome has been fed back.
        if not _durable_synthesis_can_project(navigation, synthesis_path):
            continue
        return {
            "synthesis": dict(synthesis),
            "synthesis_input": dict(synthesis_input),
            "synthesis_path": synthesis_path,
            "input_path": input_path,
            "search_wave": _durable_synthesis_search_wave(synthesis_path),
        }
    if empty_capacity_projection:
        latest_input = _latest_durable_synthesis_input(
            directory,
            context_epoch=context_epoch,
            context_hash=context_hash,
        )
        if latest_input is not None:
            search_wave, input_path, synthesis_input = latest_input
            failure_path = directory / (
                "lineage_synthesis_failure."
                f"epoch-{context_epoch:03d}.wave-{search_wave:03d}.json"
            )
            failure = read_json(failure_path, None)
            failure_core = {
                key: value
                for key, value in (failure or {}).items()
                if key != "receipt_sha256"
            }
            durable = _durable_synthesis_decision_for_input(
                directory, input_path, synthesis_input
            )
            if (
                isinstance(failure, Mapping)
                and failure.get("schema")
                == "leanmill.lineage_synthesis_failure.v1"
                and failure.get("receipt_sha256") == content_hash(failure_core)
                and durable is not None
            ):
                synthesis, call_path = durable
                synthesis_path = directory / (
                    "lineage_synthesis."
                    f"epoch-{context_epoch:03d}.wave-{search_wave:03d}.json"
                )
                return {
                    "synthesis": synthesis,
                    "synthesis_input": synthesis_input,
                    "synthesis_path": synthesis_path,
                    "input_path": input_path,
                    "search_wave": search_wave,
                    "revalidated_failure": dict(failure),
                    "durable_call_path": call_path,
                }
    return None


def _candidate_rows_from_synthesis_input(
    directory: Path,
    synthesis_input: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Restore boundary candidates from the host-frozen synthesis payload."""

    node_by_program: dict[str, str] = {}
    for journal_path in sorted(
        (directory / "lineage_journals").glob("lineage-*.events.jsonl")
    ):
        for event in TheoryCampaignJournal(journal_path).replay():
            if event.event_type != "finalist_frozen" or len(event.subject_ids) < 2:
                continue
            node_id = str(event.subject_ids[0])
            for program_id in event.subject_ids[1:]:
                prior = node_by_program.setdefault(str(program_id), node_id)
                if prior != node_id:
                    raise ValueError("frozen theory program crossed semantic nodes")

    candidates: list[dict[str, Any]] = []
    for raw in synthesis_input.get("frozen_programs") or ():
        if not isinstance(raw, Mapping):
            raise ValueError("frozen synthesis program is malformed")
        program_fields = {
            "schema",
            "campaign_id",
            "lineage_id",
            "context_hash",
            "context_epoch",
            "presentation_formula_ids",
            "prediction_formula_ids",
            "selection_receipt_id",
            "authority",
            "program_id",
        }
        if raw.get("schema") == "leanmill.theory_program.v2":
            program_fields.add("task_discharge_contracts")
        program_row = {
            key: raw[key] for key in program_fields if key in raw
        }
        program = TheoryProgram.from_json(program_row)
        node_id = node_by_program.get(program.program_id, "")
        if not node_id:
            raise ValueError("frozen synthesis program lacks its journaled node")
        candidates.append(
            {
                "node_id": node_id,
                "candidate_kind": "theory_program",
                "baseline_evaluator_ref": CHEAP_CONSEQUENCE_EVALUATOR_REF,
                "context_hash": program.context_hash,
                "context_epoch": program.context_epoch,
                "formula_ids": list(program.presentation_formula_ids),
                "joint_only_consequence_ids": [],
                "cheap_baseline_consequence_ids": [],
                "residual_joint_only_consequence_ids": [],
                "consequence_formula_ids": [],
                "residual_prediction_formula_ids": list(
                    program.prediction_formula_ids
                ),
                "boundary_target_ids": list(program.prediction_formula_ids),
                "task_contract_ids": [
                    contract.contract_id
                    for contract in program.task_discharge_contracts
                ],
                "boundary_selection_authority": "frozen_synthesis_input_replay",
                "prediction_profile": (
                    dict(raw.get("prediction_profile") or {})
                    if program.prediction_formula_ids
                    else None
                ),
                "residual_information_yield": dict(
                    raw.get("residual_information_yield") or {}
                ),
                "structural_baseline": raw.get("structural_baseline"),
                "navigator_rationale": str(raw.get("navigator_rationale") or ""),
                "selection_receipt_id": program.selection_receipt_id,
                "theory_program": program.to_json(),
                "theory_program_id": program.program_id,
            }
        )
    return candidates


def _recover_durable_lineage_synthesis(
    directory: Path,
    run: Mapping[str, Any],
    pending: Mapping[str, Any],
) -> Path:
    """Project a validated synthesis artifact without replaying navigator turns."""

    definition, blueprint, budget_row, campaign_row, context = (
        _load_campaign_attempt(directory)
    )
    synthesis = dict(pending["synthesis"])
    synthesis_input = dict(pending["synthesis_input"])
    navigation = dict(run.get("navigation") or {})
    if not _durable_synthesis_can_project(
        navigation, Path(pending["synthesis_path"])
    ):
        raise ValueError("durable synthesis crossed its search-wave owner")
    if _empty_capacity_wave_projection(navigation) or navigation.get("schema") == (
        "leanmill.recovered_lineage_synthesis_projection.v1"
    ):
        restored_candidates = _candidate_rows_from_synthesis_input(
            directory, synthesis_input
        )
        navigation = {
            "schema": "leanmill.recovered_lineage_synthesis_projection.v1",
            "status": "programs_frozen",
            "context_hash": str(synthesis_input["context_hash"]),
            "context_epoch": int(synthesis_input["context_epoch"]),
            "search_wave": int(pending["search_wave"]),
            "wave_provider_calls": 0,
            "lineages": [],
            "finalist_node_ids": list(
                dict.fromkeys(str(row["node_id"]) for row in restored_candidates)
            ),
            "finalists": restored_candidates,
            "theory_program_ids": [
                str(row["theory_program_id"]) for row in restored_candidates
            ],
            "host_isolated_program_comparisons": list(
                synthesis_input.get("host_isolated_program_comparisons") or ()
            ),
            "expansion_proposals": list(
                synthesis_input.get("formula_requests") or ()
            ),
            "theory_language_expansion_requests": list(
                synthesis_input.get("theory_language_requests") or ()
            ),
            "objective_review_history": list(
                synthesis_input.get("objective_review_history") or ()
            ),
            "isolation_receipt": dict(
                synthesis_input.get("isolation_receipt") or {}
            ),
            "search_wave_image_receipt": dict(
                synthesis_input.get("search_wave_image_receipt") or {}
            ),
            "adaptive_move_portfolio": dict(
                synthesis_input.get("adaptive_move_portfolio") or {}
            ),
            "provider_calls": int(
                (run.get("navigation") or {}).get("provider_calls", 0) or 0
            ),
            "cold_view": True,
        }
    superseded_stop = navigation.pop("lineage_synthesis_budget_stop", None)
    superseded_failure = navigation.pop("lineage_synthesis_failure", None)
    navigation["lineage_synthesis"] = synthesis
    navigation["lineage_synthesis_search_wave"] = int(pending["search_wave"])
    navigation["lineage_synthesis_frozen_program_ids"] = [
        str(row.get("program_id") or "")
        for row in synthesis_input.get("frozen_programs") or ()
        if isinstance(row, Mapping) and row.get("program_id")
    ]
    synthesis_path = Path(pending["synthesis_path"])
    prior_synthesis = read_json(synthesis_path, None)
    if isinstance(prior_synthesis, Mapping):
        if dict(prior_synthesis) != synthesis:
            raise ValueError("durable synthesis recovery changed its decision")
    else:
        write_json_atomic(synthesis_path, synthesis)
    history = [
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
    ]
    if synthesis.get("route") == "continue_search" and not any(
        row.get("receipt_sha256") == synthesis.get("receipt_sha256")
        for row in history
    ):
        history.append(synthesis)
        navigation["objective_review_history"] = history
    recovery_core = {
        "schema": "leanmill.durable_lineage_synthesis_recovery.v1",
        "context_hash": context.context_hash,
        "context_epoch": int(synthesis["context_epoch"]),
        "search_wave": int(pending["search_wave"]),
        "source_run_digest": str(run.get("run_digest") or ""),
        "synthesis_ref": Path(pending["synthesis_path"]).name,
        "synthesis_receipt_sha256": str(synthesis["receipt_sha256"]),
        "synthesis_input_ref": Path(pending["input_path"]).name,
        "synthesis_input_sha256": str(synthesis_input["input_sha256"]),
        "superseded_stop_receipt_sha256": str(
            (superseded_stop or {}).get("receipt_sha256") or ""
        ),
        "superseded_failure_receipt_sha256": str(
            (
                superseded_failure
                or pending.get("revalidated_failure")
                or {}
            ).get("receipt_sha256")
            or ""
        ),
        "durable_call_ref": (
            Path(pending["durable_call_path"]).relative_to(directory).as_posix()
            if pending.get("durable_call_path")
            else ""
        ),
        "authority": "frozen_input_and_host_validated_decision_replay",
    }
    recovery = {**recovery_core, "receipt_sha256": content_hash(recovery_core)}
    recovery_path = directory / (
        "durable_lineage_synthesis_recovery."
        + str(recovery["receipt_sha256"])[:16]
        + ".json"
    )
    prior_recovery = read_json(recovery_path, None)
    if isinstance(prior_recovery, Mapping) and dict(prior_recovery) != recovery:
        raise ValueError("durable synthesis recovery changed identity")
    if prior_recovery is None:
        write_json_atomic(recovery_path, recovery)
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
    finish_frontier_navigation(
        directory,
        brief_id=definition.to_brief().brief_id,
        blueprint=blueprint,
        context=context,
        context_epoch=int(synthesis["context_epoch"]),
        campaign_id=str(campaign_row["packet"]["campaign_id"]),
        packet_digest=str(
            run.get("packet_digest") or campaign_row.get("packet_digest") or ""
        ),
        navigation=navigation,
        provider_calls=int(usage["provider_calls"]),
        preparation_provider_calls=0,
        budget_digest=budget.digest,
        formula_proposal_count=len(
            tuple(directory.glob("typed_formula_proposal.epoch-*.json"))
        ),
        semantically_new_formula_count=_semantic_profile_admission_count(directory),
        labeled_object_count=int(adapter_preflight.get("labeled_model_count", 0)),
    )
    return directory


def _stale_durable_synthesis_projection(
    directory: Path,
    run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Find an older synthesis decision projected across a newer frozen input."""

    navigation = run.get("navigation")
    if not isinstance(navigation, Mapping):
        return None
    synthesis = navigation.get("lineage_synthesis")
    if not isinstance(synthesis, Mapping):
        return None
    context_hash = str(run.get("context_hash") or "")
    context_epoch = int(
        navigation.get(
            "context_epoch",
            (run.get("context_summary") or {}).get("context_epoch", 0),
        )
    )
    synthesis_ref = str(synthesis.get("receipt_sha256") or "")
    synthesis_rows = []
    for path in directory.glob(
        f"lineage_synthesis.epoch-{context_epoch:03d}.wave-*.json"
    ):
        row = read_json(path, None)
        if isinstance(row, Mapping) and row.get("receipt_sha256") == synthesis_ref:
            synthesis_rows.append(path)
    if not synthesis_rows:
        return None
    synthesis_path = max(
        synthesis_rows, key=_durable_synthesis_search_wave
    )
    if _durable_synthesis_can_project(navigation, synthesis_path):
        return None
    latest_input = _latest_durable_synthesis_input(
        directory,
        context_epoch=context_epoch,
        context_hash=context_hash,
    )
    if latest_input is None:
        return None
    search_wave, input_path, synthesis_input = latest_input
    outcomes: list[tuple[str, Path, dict[str, Any]]] = []
    for field, schema in (
        (
            "lineage_synthesis_budget_stop",
            "leanmill.lineage_synthesis_budget_stop.v1",
        ),
        ("lineage_synthesis_failure", "leanmill.lineage_synthesis_failure.v1"),
    ):
        path = directory / (
            f"{field}.epoch-{context_epoch:03d}.wave-{search_wave:03d}.json"
        )
        row = read_json(path, None)
        if not isinstance(row, Mapping):
            continue
        core = {
            key: value for key, value in row.items() if key != "receipt_sha256"
        }
        if (
            row.get("schema") != schema
            or row.get("receipt_sha256") != content_hash(core)
            or str(row.get("context_hash") or "") != context_hash
            or int(row.get("context_epoch", -1)) != context_epoch
        ):
            raise ValueError("successor synthesis outcome failed replay")
        outcomes.append((field, path, dict(row)))
    if len(outcomes) != 1:
        return None
    outcome_field, outcome_path, outcome = outcomes[0]
    return {
        "synthesis": dict(synthesis),
        "synthesis_path": synthesis_path,
        "synthesis_input": synthesis_input,
        "input_path": input_path,
        "search_wave": search_wave,
        "outcome_field": outcome_field,
        "outcome": outcome,
        "outcome_path": outcome_path,
    }


def _invalid_active_lineage_synthesis(
    directory: Path,
    run: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Detect a projected move invalidated by stronger host semantics."""

    navigation = run.get("navigation")
    synthesis = (
        navigation.get("lineage_synthesis")
        if isinstance(navigation, Mapping)
        else None
    )
    if not isinstance(synthesis, Mapping):
        return None
    input_sha256 = str(synthesis.get("input_sha256") or "")
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in directory.glob("lineage_synthesis_input.epoch-*.json"):
        row = read_json(path, None)
        if isinstance(row, Mapping) and row.get("input_sha256") == input_sha256:
            matches.append((path, dict(row)))
    for path in directory.glob("lineage_synthesis_input.epoch-*.wave-*.json"):
        row = read_json(path, None)
        if isinstance(row, Mapping) and row.get("input_sha256") == input_sha256:
            matches.append((path, dict(row)))
    unique = {
        str(path): (path, row) for path, row in matches
    }
    if len(unique) != 1:
        return None
    input_path, synthesis_input = next(iter(unique.values()))
    input_core = {
        key: value
        for key, value in synthesis_input.items()
        if key != "input_sha256"
    }
    if synthesis_input.get("input_sha256") != content_hash(input_core):
        raise ValueError("active lineage synthesis input digest mismatch")
    decision_fields = {
        "route",
        "continuation_mode",
        "selected_request_ids",
        "deferred_request_ids",
        "rationale",
        "next_discriminator",
        "kill_condition",
        "program_ids",
        "next_discriminator_request_ids",
    }
    raw_decision = {
        key: synthesis[key] for key in decision_fields if key in synthesis
    }
    try:
        replayed = validate_lineage_synthesis_decision(
            synthesis_input, raw_decision
        )
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "synthesis": dict(synthesis),
            "synthesis_input": synthesis_input,
            "input_path": input_path,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    if replayed != dict(synthesis):
        return {
            "synthesis": dict(synthesis),
            "synthesis_input": synthesis_input,
            "input_path": input_path,
            "error_type": "ProjectionMismatch",
            "error": "active lineage synthesis no longer replays byte-for-byte",
        }
    return None


def _unwind_invalid_active_lineage_synthesis(
    attempt_dir: str | Path,
) -> Path:
    """Return a superseded late move to search without replaying inference."""

    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("invalid synthesis unwind requires an active run")
    invalid = _invalid_active_lineage_synthesis(directory, run)
    if invalid is None:
        raise ValueError("active lineage synthesis is still valid")
    navigation = dict(run.get("navigation") or {})
    synthesis = invalid["synthesis"]
    receipt_core = {
        "schema": "leanmill.lineage_synthesis_semantic_supersession.v1",
        "context_hash": str(run.get("context_hash") or ""),
        "context_epoch": int(navigation.get("context_epoch", 0)),
        "source_run_digest": str(run.get("run_digest") or ""),
        "source_synthesis_receipt_sha256": str(
            synthesis.get("receipt_sha256") or ""
        ),
        "source_input_sha256": str(synthesis.get("input_sha256") or ""),
        "source_input_ref": str(Path(invalid["input_path"]).name),
        "error_type": str(invalid["error_type"]),
        "error": str(invalid["error"]),
        "route": "continue_search",
        "authority": "host_semantic_contract_supersession",
        "claim_boundary": (
            "retires one invalid move projection; preserves all authored "
            "programs and boundary evidence"
        ),
    }
    receipt = {
        **receipt_core,
        "receipt_sha256": content_hash(receipt_core),
    }
    path = directory / (
        "lineage_synthesis_semantic_supersession."
        f"{receipt['receipt_sha256'][:16]}.json"
    )
    prior = read_json(path, None)
    if isinstance(prior, Mapping) and dict(prior) != receipt:
        raise ValueError("lineage synthesis supersession changed identity")
    if not isinstance(prior, Mapping):
        write_json_atomic(path, receipt)
    history = [
        dict(row)
        for row in navigation.get("objective_review_history") or ()
        if isinstance(row, Mapping)
    ]
    if not any(
        row.get("receipt_sha256") == receipt["receipt_sha256"]
        for row in history
    ):
        history.append(receipt)
    navigation["objective_review_history"] = history
    for key in (
        "lineage_synthesis",
        "lineage_synthesis_program_selection",
        "lineage_synthesis_frozen_program_ids",
        "lineage_synthesis_search_wave",
    ):
        navigation.pop(key, None)
    navigation["superseded_lineage_synthesis"] = receipt
    run_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "status": "frontier_objective_unmet",
        "navigation": navigation,
        "budget_stop_receipt": None,
    }
    updated = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(directory / "run.json", updated)
    return directory


def _unwind_stale_durable_synthesis_projection(
    attempt_dir: str | Path,
) -> Path:
    """Restore the newer synthesis outcome without replaying provider work."""

    directory = Path(attempt_dir)
    run = read_json(directory / "run.json", None)
    if not isinstance(run, Mapping):
        raise ValueError("stale synthesis unwind requires an active run")
    pending = _stale_durable_synthesis_projection(directory, run)
    if pending is None:
        return directory
    definition, blueprint, budget_row, campaign_row, context = (
        _load_campaign_attempt(directory)
    )
    navigation = dict(run.get("navigation") or {})
    stale_selection = navigation.pop("lineage_synthesis_program_selection", None)
    navigation.pop("lineage_synthesis", None)
    navigation.pop("lineage_synthesis_search_wave", None)
    navigation.pop("lineage_synthesis_frozen_program_ids", None)
    navigation.pop("lineage_synthesis_budget_stop", None)
    navigation.pop("lineage_synthesis_failure", None)
    navigation[pending["outcome_field"]] = dict(pending["outcome"])
    navigation["search_wave"] = max(
        int(navigation.get("search_wave", 0) or 0),
        int(pending["search_wave"]),
    )
    receipt_core = {
        "schema": "leanmill.stale_durable_synthesis_unwind.v1",
        "context_hash": context.context_hash,
        "context_epoch": int(pending["synthesis_input"]["context_epoch"]),
        "search_wave": int(pending["search_wave"]),
        "source_run_digest": str(run.get("run_digest") or ""),
        "stale_synthesis_ref": Path(pending["synthesis_path"]).name,
        "stale_synthesis_receipt_sha256": str(
            pending["synthesis"].get("receipt_sha256") or ""
        ),
        "stale_selection_receipt_sha256": str(
            (stale_selection or {}).get("receipt_sha256") or ""
        ),
        "successor_input_ref": Path(pending["input_path"]).name,
        "successor_input_sha256": str(
            pending["synthesis_input"]["input_sha256"]
        ),
        "successor_outcome_ref": Path(pending["outcome_path"]).name,
        "successor_outcome_receipt_sha256": str(
            pending["outcome"]["receipt_sha256"]
        ),
        "authority": "search_wave_owned_synthesis_recovery",
    }
    receipt = {**receipt_core, "receipt_sha256": content_hash(receipt_core)}
    write_json_atomic(
        directory
        / (
            "stale_durable_synthesis_unwind."
            + str(receipt["receipt_sha256"])[:16]
            + ".json"
        ),
        receipt,
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
    finish_frontier_navigation(
        directory,
        brief_id=definition.to_brief().brief_id,
        blueprint=blueprint,
        context=context,
        context_epoch=int(pending["synthesis_input"]["context_epoch"]),
        campaign_id=str(campaign_row["packet"]["campaign_id"]),
        packet_digest=str(
            run.get("packet_digest") or campaign_row.get("packet_digest") or ""
        ),
        navigation=navigation,
        provider_calls=int(usage["provider_calls"]),
        preparation_provider_calls=0,
        budget_digest=budget.digest,
        formula_proposal_count=len(
            tuple(directory.glob("typed_formula_proposal.epoch-*.json"))
        ),
        semantically_new_formula_count=_semantic_profile_admission_count(directory),
        labeled_object_count=int(adapter_preflight.get("labeled_model_count", 0)),
    )
    return directory


def _objective_continuation_budget_exhausted(
    directory: Path, run: Mapping[str, Any]
) -> bool:
    """Whether an active objective transition has no leaf allocation left."""

    if run.get("status") not in {
        "frontier_leaf_decision_pending",
        "frontier_objective_unmet",
    }:
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
            and type(row.get("schema")) is str
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
    # Reviewed recovery artifacts are bound to the exact current run.  Consume
    # them before any host-side replay, evaluator supersession, or boundary
    # status repair can legitimately advance that run digest.
    existing = read_json(directory / "run.json", None)
    boundary_completion = read_json(directory / "boundary_completion.json", None)
    governance_recheck = read_json(
        directory / "boundary_governance_recheck.json", None
    )
    pre_delivery_boundary_feedback = _boundary_search_feedback(
        existing,
        boundary_completion,
        governance_recheck=(
            governance_recheck
            if isinstance(governance_recheck, Mapping)
            else None
        ),
    )
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
        _attempt_lease is None
        and (
            pending_external_science is not None
            or pending_external_science_negative is not None
        )
    ):
        with frontier_attempt_lease(
            directory, action="resume_frontier_navigation"
        ) as lease:
            return resume_frontier_campaign_navigation(
                directory,
                repo=repo,
                workbench_authority_ref=workbench_authority_ref,
                _attempt_lease=lease,
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

    existing = _restore_durable_search_transition(directory, existing)
    existing = _archive_stale_evaluation_candidates(directory, existing)
    existing = _archive_cross_context_active_candidates(directory, existing)
    existing = _restore_nested_objective_feedback_history(directory, existing)
    existing = _repair_stale_boundary_disposition_status(directory, existing)
    boundary_feedback = (
        pre_delivery_boundary_feedback
        if (
            pending_external_science is not None
            or pending_external_science_negative is not None
        )
        else _boundary_search_feedback(
            existing,
            boundary_completion,
            governance_recheck=(
                governance_recheck
                if isinstance(governance_recheck, Mapping)
                else None
            ),
        )
    )
    if (
        isinstance(existing, Mapping)
        and existing.get("status") == "frontier_language_expansion_requested"
    ):
        frozen_blueprint = FrontierTheoryBlueprint.from_json(
            read_json(directory / "blueprint.json", {})
        )
        finalized_family_null = _maybe_finalize_reviewed_family_exhaustion(
            directory, blueprint=frozen_blueprint
        )
        if finalized_family_null is not None:
            return directory
    if (
        isinstance(existing, dict)
        and existing.get("status")
        in {
            "frontier_candidates_frozen_awaiting_boundary_approval",
            "frontier_no_candidate",
            "frontier_navigation_exhausted",
            "frontier_language_expansion_requested",
            "frontier_objective_witness_found_pending_ratification",
            "frontier_objective_discharged",
            "budget_stopped",
        }
        and not _recovered_lineage_synthesis_required(directory, existing)
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
    if not _objective_resume_has_turn_capacity(ledger, existing):
        # A wave owns an actual allocation, not merely a later sequence number.
        # Keep the last scientific projection active until budget or evidence
        # creates a consuming transition.
        ledger.freeze_wall_clock(reason="objective_unmet_has_no_search_capacity")
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
        recovered_synthesis = _recovered_lineage_synthesis_required(
            directory, existing
        )
        if isinstance(existing, Mapping) and (
            existing.get("status")
            in {
                "frontier_leaf_decision_pending",
                "frontier_objective_unmet",
            }
            or recovered_synthesis
        ):
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
                if _candidate_matches_evaluation_contract(row)
                and _candidate_matches_context(
                    row,
                    context_hash=context.context_hash,
                    context_epoch=context_epoch,
                )
            )
            if objective_survivors:
                navigator.objective_survivors = objective_survivors  # type: ignore[attr-defined]
            opened_wave = False
            latest_feedback: dict[str, Any] | None = None
            actionable_feedback = next(
                (
                    row
                    for row in reversed(history)
                    if isinstance(row, Mapping)
                    and row.get("schema")
                    != "leanmill.lineage_synthesis_semantic_supersession.v1"
                ),
                None,
            )
            if isinstance(actionable_feedback, Mapping):
                latest_feedback = dict(actionable_feedback)
                for feedback_row in _objective_feedback_trace_rows(
                    prior_navigation,
                    latest_feedback,
                    context_hash=context.context_hash,
                ):
                    if feedback_row not in seed:
                        seed.append(feedback_row)
                navigator.objective_feedback = latest_feedback  # type: ignore[attr-defined]
                if (
                    _is_language_execution_feedback(
                        latest_feedback,
                        context_hash=context.context_hash,
                    )
                    and _language_feedback_wave_binding(
                        directory, latest_feedback
                    )
                    is None
                ):
                    navigator.begin_search_wave()  # type: ignore[attr-defined]
                    opened_wave = True
                    _bind_language_feedback_to_search_wave(
                        directory,
                        feedback=latest_feedback,
                        context_hash=context.context_hash,
                        context_epoch=context_epoch,
                        search_wave=int(getattr(navigator, "search_wave", 0)),
                    )
            unmaterialized_wave = int(
                getattr(navigator, "search_wave", 0)
            ) > int(prior_navigation.get("search_wave", 0))
            retry_synthesis = _lineage_synthesis_retry_required(
                directory, existing
            )
            if retry_synthesis:
                if recovered_synthesis:
                    # The recovered candidate set differs from every frozen
                    # historical synthesis input. Give its new late review a
                    # fresh wave identity while preserving every leaf row.
                    navigator.begin_search_wave()  # type: ignore[attr-defined]
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

        navigator = _make_campaign_theory_navigator(
            definition,
            directory=directory,
            repo=repo,
            attempt_id=directory.name,
        )
        navigator.epoch = context_epoch  # type: ignore[attr-defined]
        seed = (
            []
            if isinstance(existing, Mapping)
            and existing.get("status") == "frontier_objective_unmet"
            else list(checkpoint_trace)
        )
        prior_navigation = (
            existing.get("navigation")
            if isinstance(existing, Mapping)
            and isinstance(existing.get("navigation"), Mapping)
            else {}
        )
        if isinstance(existing, Mapping) and existing.get("status") in {
            "frontier_leaf_decision_pending",
            "frontier_objective_unmet",
        }:
            actionable_feedback = next(
                (
                    row
                    for row in reversed(
                        prior_navigation.get("objective_review_history") or ()
                    )
                    if isinstance(row, Mapping)
                    and row.get("schema")
                    != "leanmill.lineage_synthesis_semantic_supersession.v1"
                ),
                None,
            )
            if isinstance(actionable_feedback, Mapping):
                feedback = dict(actionable_feedback)
                for feedback_row in _objective_feedback_trace_rows(
                    prior_navigation,
                    feedback,
                    context_hash=context.context_hash,
                ):
                    if feedback_row not in seed:
                        seed.append(feedback_row)
                navigator.objective_feedback = feedback  # type: ignore[attr-defined]
                if (
                    _is_language_execution_feedback(
                        feedback,
                        context_hash=context.context_hash,
                    )
                    and _language_feedback_wave_binding(directory, feedback)
                    is None
                ):
                    navigator.begin_search_wave()  # type: ignore[attr-defined]
                    _bind_language_feedback_to_search_wave(
                        directory,
                        feedback=feedback,
                        context_hash=context.context_hash,
                        context_epoch=context_epoch,
                        search_wave=int(getattr(navigator, "search_wave", 0)),
                    )
        navigator.initial_trace = tuple(seed)  # type: ignore[attr-defined]
        role = navigator.call_role  # type: ignore[attr-defined]
        base_role_dir = (directory / "agent_calls" / "navigator").resolve()
        checkpoint_calls_for_role = (
            checkpoint_calls
            if role.artifact_dir.resolve() == base_role_dir
            else 0
        )
        prior_calls, durable_decisions = _read_durable_navigator_decisions(
            role.artifact_dir
        )
        replay_decisions = durable_decisions[checkpoint_calls_for_role:]
        role.calls.extend(prior_calls)
        navigator.prior_agent_turns = checkpoint_calls_for_role  # type: ignore[attr-defined]
        navigator.round_offset = checkpoint_calls_for_role  # type: ignore[attr-defined]
        navigator.replay_decisions = tuple(  # type: ignore[attr-defined]
            replay_decisions
        )

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
                and type(row.get("schema")) is str
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
        carried = _merge_carried_evidence_receipts(
            prior_navigation.get("carried_evidence_receipts") or (),
            navigation.get("carried_evidence_receipts") or (),
        )
        if carried:
            navigation["carried_evidence_receipts"] = carried

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
        _maybe_finalize_reviewed_family_exhaustion(
            directory, blueprint=blueprint
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
    candidate_outcome_memory = _campaign_construction_candidate_memory(
        directory, blueprint
    )

    root_journal = TheoryCampaignJournal(directory / "events.jsonl")
    all_events = list(root_journal.replay())
    for path in sorted(
        (directory / "lineage_journals").glob("lineage-*.events.jsonl")
    ):
        all_events.extend(TheoryCampaignJournal(path).replay())
    journal_epoch = max((event.epoch for event in all_events), default=0)
    checkpoint = read_json(
        directory / "navigation_epoch_checkpoint.json", None
    )
    if isinstance(checkpoint, Mapping):
        if checkpoint.get("context_hash") != context.context_hash:
            raise ValueError(
                "navigation epoch checkpoint targets a stale context"
            )
        checkpoint_epoch = int(checkpoint.get("context_epoch", -1))
        if checkpoint_epoch < journal_epoch:
            raise ValueError(
                "navigation epoch checkpoint trails the campaign journal"
            )
        epoch = checkpoint_epoch
    else:
        epoch = journal_epoch
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
        call_dir = directory / "agent_calls" / "navigator"
        calls, decisions = _read_durable_navigator_decisions(call_dir)
        navigation = (
            _replay_navigator_decisions(
                context,
                blueprint,
                decisions,
                _navigator_recovery_journal(
                    directory,
                    directory / "agent_calls" / "navigator",
                    epoch=epoch,
                    context_hash=context.context_hash,
                ),
                attempt_id=directory.name,
                campaign_id=campaign_id,
                epoch=epoch,
                max_finalists=configured_finalists,
                prior_conflict_rows=prior_conflicts,
                witness_constructor_fn=(
                    _durable_witness_constructor_for_navigator_segment(
                        definition, directory, call_dir
                    )
                ),
                candidate_outcome_memory=candidate_outcome_memory,
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
                (
                    branch_calls,
                    decisions,
                    initial_trace,
                    prior_agent_turns,
                    round_offset,
                ) = _durable_navigator_segment(
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
                            _navigator_recovery_journal(
                                directory,
                                call_dir,
                                epoch=epoch,
                                context_hash=context.context_hash,
                            ),
                            attempt_id=f"{directory.name}:lineage:{branch}",
                            campaign_id=campaign_id,
                            epoch=epoch,
                            lineage_id=lineage_id,
                            max_finalists=per_lineage_finalists,
                            prior_conflict_rows=prior_conflicts,
                            initial_trace=initial_trace,
                            prior_agent_turns=prior_agent_turns,
                            round_offset=round_offset,
                            witness_constructor_fn=(
                                _durable_witness_constructor_for_navigator_segment(
                                    definition, directory, call_dir
                                )
                            ),
                            candidate_outcome_memory=candidate_outcome_memory,
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
    navigation = _bind_recovered_boundary_artifact_feedback(
        directory, navigation
    )
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
        if not _durable_synthesis_can_project(navigation, synthesis_path):
            continue
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
        navigation.pop("lineage_synthesis_budget_stop", None)
        navigation.pop("lineage_synthesis_failure", None)
        navigation["lineage_synthesis"] = synthesis
        navigation["lineage_synthesis_search_wave"] = (
            _durable_synthesis_search_wave(synthesis_path)
        )
        navigation["lineage_synthesis_frozen_program_ids"] = [
            str(row.get("program_id") or "")
            for row in replay_input.get("frozen_programs") or ()
            if isinstance(row, Mapping) and row.get("program_id")
        ]
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

def _registered_task_executor_kinds(
    navigation: Mapping[str, Any],
) -> frozenset[str]:
    """Return exact registered executor kinds owned by frozen task contracts.

    Prediction-level Lean checks remain controlled by the blueprint's
    ``conditional_lean`` flag.  A leaf-authored task contract is a different
    lifecycle object and is activated only by its adjudicator's registered
    boundary handler.
    """

    from ztare.leanmill.theory_task_boundary_registry import (
        registered_theory_task_boundary_handler,
    )

    kinds: set[str] = set()
    for candidate in navigation.get("finalists") or ():
        if not isinstance(candidate, Mapping):
            continue
        program_row = candidate.get("theory_program")
        if not isinstance(program_row, Mapping):
            continue
        program = TheoryProgram.from_json(program_row)
        for contract in program.task_discharge_contracts:
            handler = registered_theory_task_boundary_handler(
                contract.adjudicator_id
            )
            if handler is not None:
                kinds.add(handler.executor_kind)
    return frozenset(kinds)


def _registered_formal_task_executor_required(
    navigation: Mapping[str, Any],
) -> bool:
    """Compatibility predicate for the existing formal-task first fire."""

    from ztare.leanmill.theory_task_boundary_registry import (
        FORMALIZATION_CAMPAIGN_EXECUTOR,
    )

    return FORMALIZATION_CAMPAIGN_EXECUTOR in _registered_task_executor_kinds(
        navigation
    )


def _registered_witness_task_executor_required(
    navigation: Mapping[str, Any],
) -> bool:
    from ztare.leanmill.theory_task_boundary_registry import (
        DATA_ONLY_WITNESS_EXECUTOR,
    )

    return DATA_ONLY_WITNESS_EXECUTOR in _registered_task_executor_kinds(
        navigation
    )


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
    task_executor_kinds = _registered_task_executor_kinds(activation_navigation)
    from ztare.leanmill.theory_task_boundary_registry import (
        DATA_ONLY_WITNESS_EXECUTOR,
        FORMALIZATION_CAMPAIGN_EXECUTOR,
    )

    formal_task_requested = FORMALIZATION_CAMPAIGN_EXECUTOR in task_executor_kinds
    witness_task_requested = DATA_ONLY_WITNESS_EXECUTOR in task_executor_kinds
    lean_executor = None
    isabelle_executor = None
    theory_task_executor = None
    formal_theory_task_executor = None
    witness_theory_task_executor = None
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

        def formal_theory_task_executor(
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

    if witness_task_requested:
        _definition, witness_blueprint, _budget, _campaign, _context = (
            _load_campaign_attempt(directory)
        )
        witness_adapter_id = str(witness_blueprint.adapter_id)

        def witness_capability_call(*, descriptor, **kwargs):
            from ztare.leanmill.theory_adapter_registry import (
                materialize_theory_adapter_capability,
                theory_adapter_capabilities,
            )
            from ztare.leanmill.witness_construction_boundary import (
                WitnessConstructionCapabilityUnavailable,
            )

            if (
                not isinstance(descriptor, Mapping)
                or str(descriptor.get("adapter_id") or "")
                != witness_adapter_id
            ):
                raise ValueError(
                    "witness task capability crossed the active adapter"
                )
            capability_id = str(descriptor.get("capability_id") or "")
            capability_contract = descriptor.get("contract")
            if (
                not capability_id
                or not isinstance(capability_contract, Mapping)
                or capability_id
                not in theory_adapter_capabilities(witness_adapter_id)
            ):
                raise WitnessConstructionCapabilityUnavailable(
                    "adapter_capability_unavailable:" + capability_id
                )
            return materialize_theory_adapter_capability(
                witness_adapter_id,
                capability_id,
                descriptor=dict(descriptor),
                **kwargs,
            )

        def witness_theory_task_executor(
            contract,
            *,
            context,
            verification_plan,
            budget_ledger,
        ):
            del verification_plan, budget_ledger
            from ztare.leanmill.witness_construction_boundary import (
                execute_governed_witness_construction_task,
            )

            if getattr(context, "context_hash", None) != contract.parameters.get(
                "context_hash"
            ):
                raise ValueError("witness task executor crossed campaign context")
            return execute_governed_witness_construction_task(
                contract,
                normalizer_fn=witness_capability_call,
                verifier_fn=witness_capability_call,
            )

    if task_executor_kinds:
        from ztare.leanmill.theory_task_boundary_registry import (
            theory_task_executor_kind,
        )

        def theory_task_executor(
            contract,
            *,
            context,
            verification_plan,
            budget_ledger,
        ):
            executor_kind = theory_task_executor_kind(contract)
            executor = (
                formal_theory_task_executor
                if executor_kind == FORMALIZATION_CAMPAIGN_EXECUTOR
                else witness_theory_task_executor
                if executor_kind == DATA_ONLY_WITNESS_EXECUTOR
                else None
            )
            if executor is None:
                raise ValueError(
                    "registered theory-task executor is unavailable: "
                    + executor_kind
                )
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
    if not task_executor_kinds:
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
    if (
        isinstance(source_run, Mapping)
        and _boundary_hard_stop_reason(completion)
    ):
        _materialize_boundary_budget_stop(
            directory, source_run, completion
        )
        return completion
    governance_recheck = read_json(
        directory / "boundary_governance_recheck.json", None
    )
    feedback = _boundary_search_feedback(
        source_run,
        completion,
        governance_recheck=(
            governance_recheck
            if isinstance(governance_recheck, Mapping)
            else None
        ),
    )
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
            axiom_audit_fn=lambda source, target_name: (
                audit_lean_consequence_axioms(
                    source,
                    target_name,
                    lean_root=root,
                    timeout_s=int(timeout_s),
                )
            ),
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
    target_replay = alignment.get("target_predicate_replay")
    literature_target_replay = literature_receipt.get("target_predicate_replay")
    if target_replay != literature_target_replay:
        raise ValueError("post-freeze target replay changed after interpretation")
    target_outcome = (
        str(target_replay.get("outcome") or "")
        if isinstance(target_replay, Mapping)
        else ""
    )
    external_status = str(alignment.get("status") or "unavailable")
    novelty_assessment = str(review.get("novelty_assessment") or "")
    expected_external_status = (
        "target_overlap"
        if target_outcome == "overlap"
        else "unavailable"
        if target_outcome == "unknown"
        and novelty_assessment == "not_located_in_bounded_review"
        else external_status_by_assessment.get(novelty_assessment, "unavailable")
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
        or target_outcome == "overlap"
        or any(
            isinstance(row, Mapping)
            and row.get("match_status") in {"exact", "equivalent"}
            for row in review.get("formula_matches") or ()
        )
    )
    expected_origin = (
        "retrieved_target_overlap"
        if external_status == "target_overlap"
        else "catalogued_recovery"
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

    if external_status == "target_overlap":
        residual = "distinguish_from_retrieved_target_overlap_or_change_objective"
    elif external_status == "catalogued":
        residual = "distinguish_from_catalogued_result_or_change_objective"
    elif external_status == "likely_catalogued":
        residual = "adjudicate_likely_recurrence_before_terminal_credit"
    elif verified_relations:
        residual = "separate_unmapped_implication_from_recurrent_finite_structure"
    else:
        residual = "transport_grounded_mechanism_under_destination_replay"
    recurrence_pressure = bool(
        external_status in {"catalogued", "likely_catalogued", "target_overlap"}
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
            and type(row.get("schema")) is str
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
            and type(row.get("schema")) is str
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
                max_timeout_seconds=role.config.timeout_seconds,
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
        LITERATURE_SEARCH_LEGS,
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
        search_protocol = packet.get("literature_search_protocol")
        search_protocol = (
            dict(search_protocol) if isinstance(search_protocol, Mapping) else {}
        )
        required_search_legs = tuple(
            str(row)
            for row in search_protocol.get("required_search_legs")
            or LITERATURE_SEARCH_LEGS
        )
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
            "search_coverage": {
                "review_as_of_date": str(
                    search_protocol.get("review_as_of_date") or "unavailable"
                ),
                "anchor_sources": [],
                "search_legs": [
                    {
                        "leg_id": leg_id,
                        "status": "unavailable",
                        "queries": [f"unavailable:{leg_id}"],
                        "evidence_urls": [],
                        "limitation": str(reason),
                    }
                    for leg_id in required_search_legs
                ],
                "problem_status": "inconclusive",
                "status_evidence_urls": [],
                "latest_relevant_source_date": None,
                "limitations": [str(reason)],
            },
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
    from ztare.leanmill.target_predicate_replay import (
        replay_review_target_predicates,
    )

    retrieved_target_examples = read_json(
        directory / "retrieved_target_examples.json", None
    )
    retrieved_target_examples = (
        dict(retrieved_target_examples)
        if isinstance(retrieved_target_examples, Mapping)
        else None
    )

    def receipt_for(
        review: Mapping[str, Any],
        finite_witness_host_checks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        target_predicate_replay = replay_review_target_predicates(
            packet,
            review,
            retrieved_target_examples,
            receipts_dir=directory / "workspace",
        )
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
            "target_predicate_replay": target_predicate_replay,
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
            and type(row.get("schema")) is str
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
    directory: Path,
    *,
    prefix: str,
    schema: str,
    context_hash: str | None = None,
    lineage_ids: Sequence[str] | None = None,
) -> tuple[dict[str, Any], ...]:
    lineage_set = (
        {str(value) for value in lineage_ids}
        if lineage_ids is not None
        else None
    )
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob(f"{prefix}.*.json")):
        row = read_json(path, None)
        if not isinstance(row, Mapping) or row.get("schema") != schema:
            raise ValueError(f"{prefix} artifact has the wrong schema")
        core = {
            key: value for key, value in row.items() if key != "receipt_sha256"
        }
        if row.get("receipt_sha256") != content_hash(core):
            raise ValueError(f"{prefix} artifact digest mismatch")
        if context_hash is not None and row.get("context_hash") != context_hash:
            continue
        if lineage_set is not None and str(row.get("lineage_id") or "") not in lineage_set:
            continue
        rows.append(dict(row))
    return tuple(rows)


def _superseded_budget_stop_receipt_refs(
    directory: Path, *, context_hash: str
) -> frozenset[str]:
    """Replay resource-grant reopen receipts that invalidate prior stops."""

    refs: set[str] = set()
    patterns = (
        (
            "budget_extension_reopen.*.json",
            "leanmill.budget_extension_pending_action_reopen.v1",
            "expansion",
        ),
        (
            "boundary_budget_extension_reopen.*.json",
            "leanmill.boundary_budget_extension_reopen.v1",
            "boundary",
        ),
    )
    for pattern, schema, phase in patterns:
        for path in sorted(directory.glob(pattern)):
            row = read_json(path, None)
            if not isinstance(row, Mapping) or row.get("schema") != schema:
                raise ValueError("budget reopen artifact has the wrong schema")
            core = {
                key: value
                for key, value in row.items()
                if key != "receipt_sha256"
            }
            if row.get("receipt_sha256") != content_hash(core):
                raise ValueError("budget reopen artifact digest mismatch")
            # Legacy receipts predate disposition supersession and therefore
            # remain historical only; they cannot silently invalidate a stop.
            stop = row.get("superseded_budget_stop_receipt")
            if not isinstance(stop, Mapping):
                continue
            stop_core = {
                key: value
                for key, value in stop.items()
                if key != "receipt_sha256"
            }
            stop_ref = str(stop.get("receipt_sha256") or "")
            if (
                row.get("context_hash") != context_hash
                or stop.get("schema") != "leanmill.budget_stop_receipt.v1"
                or stop.get("context_hash") != context_hash
                or stop_ref != content_hash(stop_core)
            ):
                raise ValueError("budget reopen crossed its stopped campaign")
            extensions = _phase_extensions_after_stop(
                directory,
                {"budget_stop_receipt": dict(stop)},
                phase=phase,
            )
            if str(row.get("extension_event_sha256") or "") not in {
                str(extension.get("event_sha256") or "")
                for extension in extensions
            }:
                raise ValueError("budget reopen does not replay its resource grant")
            refs.add(stop_ref)
    return frozenset(refs)


def _active_lineage_disposition_rows(
    directory: Path,
    *,
    context_hash: str,
    lineage_ids: Sequence[str],
) -> tuple[dict[str, Any], ...]:
    """Project immutable disposition history into the current frozen set."""

    superseded_stops = _superseded_budget_stop_receipt_refs(
        directory, context_hash=context_hash
    )
    return tuple(
        row
        for row in _terminal_obligation_rows(
            directory,
            prefix="lineage_disposition",
            schema="leanmill.frozen_lineage_disposition.v2",
            context_hash=context_hash,
            lineage_ids=lineage_ids,
        )
        if not (
            row.get("terminal_state") == "retired_unresolved"
            and row.get("authority")
            == "frontier_campaign_budget_or_retirement_transition"
            and superseded_stops.intersection(
                str(value) for value in row.get("evidence_refs") or ()
            )
        )
    )


def _lineage_disposition_storage_identity(
    receipt: Mapping[str, Any],
) -> str:
    """Keep each immutable disposition generation under a distinct path."""

    return (
        str(receipt.get("lineage_id") or "")
        + ":"
        + str(receipt.get("receipt_sha256") or "")
    )


def _frozen_terminal_lineage_ids(
    navigation: Mapping[str, Any],
) -> tuple[str, ...]:
    exhaustion = navigation.get("reviewed_family_exhaustion_discharge")
    if isinstance(exhaustion, Mapping):
        observation = exhaustion.get("observation")
        frozen = (
            observation.get("frozen_lineage_ids")
            if isinstance(observation, Mapping)
            else None
        )
        if isinstance(frozen, list) and frozen and all(
            isinstance(value, str) and value for value in frozen
        ) and len(set(frozen)) == len(frozen):
            return tuple(frozen)
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
    existing_rows = _active_lineage_disposition_rows(
        directory,
        context_hash=context_hash,
        lineage_ids=tuple(frozen),
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
            identity=_lineage_disposition_storage_identity(disposition),
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
            context_hash=str(run.get("context_hash") or ""),
            lineage_ids=_frozen_terminal_lineage_ids(
                (run.get("navigation") or {})
            ),
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
        for row in _active_lineage_disposition_rows(
            directory,
            context_hash=str(run.get("context_hash") or ""),
            lineage_ids=lineages,
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
            identity=_lineage_disposition_storage_identity(receipt),
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
        lineage_dispositions=_active_lineage_disposition_rows(
            directory,
            context_hash=str(run.get("context_hash") or ""),
            lineage_ids=lineages,
        ),
        generalization_residuals=_terminal_obligation_rows(
            directory,
            prefix="generalization_residual",
            schema=GENERALIZATION_RESIDUAL_SCHEMA,
            context_hash=str(run.get("context_hash") or ""),
            lineage_ids=lineages,
        ),
        generalization_adjudications=_terminal_obligation_rows(
            directory,
            prefix="generalization_adjudication",
            schema=GENERALIZATION_ADJUDICATION_SCHEMA,
            context_hash=str(run.get("context_hash") or ""),
            lineage_ids=lineages,
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
        for row in _active_lineage_disposition_rows(
            directory,
            context_hash=str(run.get("context_hash") or ""),
            lineage_ids=_frozen_terminal_lineage_ids(
                (run.get("navigation") or {})
            ),
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
        if (
            directory / "theory_language_successor_commit.json"
        ).is_file():
            return "recover_language_successor"
        raise ValueError("frontier lifecycle requires an active run")
    run_core = {key: value for key, value in run.items() if key != "run_digest"}
    if run.get("run_digest") != content_hash(run_core):
        raise ValueError("frontier lifecycle run digest mismatch")
    cold_construction_recovery = pending_cold_witness_boundary_recovery(
        directory, run
    )
    raw_navigation = run.get("navigation")
    malformed_navigation = (
        raw_navigation is not None
        and bool(raw_navigation)
        and not isinstance(raw_navigation, Mapping)
    )
    raw_history = (
        raw_navigation.get("objective_review_history")
        if isinstance(raw_navigation, Mapping)
        else None
    )
    malformed_history = (
        raw_history is not None
        and bool(raw_history)
        and not isinstance(raw_history, (list, tuple))
    )
    if malformed_navigation or malformed_history:
        if cold_construction_recovery:
            return "recover_construction_boundary"
        raise ValueError(
            "frontier lifecycle navigation control fields are malformed"
        )
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
    if _invalid_active_lineage_synthesis(directory, run) is not None:
        return "unwind_invalid_lineage_synthesis"
    if _stale_durable_synthesis_projection(directory, run) is not None:
        return "unwind_stale_synthesis_projection"
    status = str(run.get("status") or "")
    if cold_construction_recovery:
        return "recover_construction_boundary"
    if _pending_adapter_gap_conformance_supersession(directory, run) is not None:
        return "reopen_superseded_adapter_gap"
    if _pending_extended_adapter_recovery(directory, run) is not None:
        return "reopen_extended_adapter_recovery"
    if status == "budget_stopped" and _pending_extended_adapter_gap(
        directory, run
    ) is not None:
        return "reopen_extended_adapter_gap"
    if status == "budget_stopped" and _pending_extended_navigation(
        directory, run
    ) is not None:
        return "reopen_extended_navigation"
    if status == "budget_stopped" and _pending_extended_boundary(
        directory, run
    ) is not None:
        return "reopen_extended_boundary"
    if status == "frontier_objective_witness_found_pending_ratification":
        if _pending_reviewed_family_member_ratifications(directory, run):
            return "ratify_construction_artifact"
        raise ValueError(
            "family witness is pending ratification without a replayable admission"
        )
    if (
        status == "frontier_objective_discharged"
        and (
            _current_reviewed_family_objective_discharge(directory, run) is not None
            or _current_reviewed_family_exhaustion_discharge(directory, run)
            is not None
        )
    ):
        terminal = _campaign_terminal_obligation_gate(directory, run)
        return (
            "complete"
            if not isinstance(terminal, Mapping) or terminal.get("ready") is True
            else "resolve_terminal_obligations"
        )
    if _recovered_lineage_synthesis_required(directory, run):
        return "resume_navigation"
    if status in {"frontier_leaf_decision_pending", "frontier_objective_unmet"}:
        if _pending_durable_lineage_synthesis(directory, run) is not None:
            return "recover_lineage_synthesis"
        if _objective_continuation_budget_exhausted(directory, run):
            return "finalize_budget_stop"
        return "resume_navigation"
    if status in {
        "frontier_language_expansion_requested",
        "blocked_adapter_gap",
    }:
        gap = run.get("adapter_gap") or read_json(
            directory / "adapter_gap.json", {}
        )
        if (
            status == "blocked_adapter_gap"
            and isinstance(gap, Mapping)
            and gap.get("gap_kind") == "adapter_missing"
            and not str(run.get("blueprint_id") or "")
            and not str(run.get("context_hash") or "")
            and not (directory / "blueprint.json").is_file()
        ):
            # A missing adapter discovered while compiling the campaign has no
            # frozen source context on which capability expansion can operate.
            # The typed gap is the terminal artifact for this attempt; a
            # reviewed adapter identity must enter through a new campaign.
            return "bootstrap_adapter_authority_required"
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
        theory_task_requested=bool(_registered_task_executor_kinds(navigation)),
        theory_task_requested_contracts=_registered_boundary_task_contracts(
            navigation
        ),
    ):
        return "verify_boundary"
    boundary_rows = (completion.get("boundary_result") or {}).get(
        "query_results"
    ) or ()
    governance_recheck = read_json(
        directory / "boundary_governance_recheck.json", None
    )
    governance_state = _boundary_governance_recheck_state(
        completion,
        governance_recheck
        if isinstance(governance_recheck, Mapping)
        else None,
    )
    if governance_state["required"] and not governance_state["complete"]:
        return "verify_boundary"
    if (
        boundary_rows
        and plan.get("post_freeze_interpretation") is True
        and not _current_post_freeze_interpretation(directory, run, blueprint)
    ):
        return "interpret_boundary"
    if _pending_construction_artifact_ratifications(directory, run, completion):
        return "ratify_construction_artifact"
    if (
        status != "frontier_objective_discharged"
        and _boundary_search_feedback(
            run,
            completion,
            governance_recheck=(
                governance_recheck
                if isinstance(governance_recheck, Mapping)
                else None
            ),
        )
        is not None
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
        "budget_extension_reopen.*.json",
        "boundary_budget_stop_transition.*.json",
        "boundary_budget_extension_reopen.*.json",
        "boundary_attempt_supersession.*.json",
        "durable_lineage_synthesis_recovery.*.json",
        "stale_durable_synthesis_unwind.*.json",
        "adapter_forge_attempts/**/*.json",
        "construction_artifact_ratification.*.json",
        "construction_artifact_ratification_completion.*.json",
        "reviewed_family_member_ratification_admission.*.json",
        "reviewed_family_member_ratification.*.json",
        "reviewed_family_member_ratification_completion.*.json",
        "reviewed_family_objective_discharge.*.json",
        "reviewed_family_exhaustion_observation.*.json",
        "reviewed_family_exhaustion_discharge.*.json",
        "theory_task_discharge.*.json",
        "theory_task_discharge_consumption.*.json",
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
    max_transitions: int | None = None,
) -> Path:
    """Advance a campaign until a terminal state or semantic fixed point."""

    directory = Path(attempt_dir)
    if max_transitions is not None and max_transitions < 1:
        raise ValueError("frontier lifecycle transition bound must be positive")
    seen: set[str] = set()
    transitions = 0
    while True:
        run = read_json(directory / "run.json", None)
        if isinstance(run, Mapping) and isinstance(run.get("navigation"), Mapping):
            if any(
                not _candidate_matches_evaluation_contract(row)
                for field in ("finalists", "objective_survivors")
                for row in run["navigation"].get(field) or ()
                if isinstance(row, Mapping)
            ):
                with frontier_attempt_lease(
                    directory, action="archive_stale_evaluation_candidates"
                ):
                    _archive_stale_evaluation_candidates(
                        directory,
                        read_json(directory / "run.json", None),
                    )
                continue
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
        if action in {
            "complete",
            "terminal_obligations_blocked",
            "bootstrap_adapter_authority_required",
        } or marker in seen:
            return directory
        seen.add(marker)
        if action == "resume_navigation":
            directory = resume_frontier_campaign_navigation(
                directory,
                workbench_authority_ref=workbench_authority_ref,
            )
        elif action == "recover_language_successor":
            with frontier_attempt_lease(
                directory, action="recover_language_successor"
            ) as lease:
                recovered = _recover_language_successor_commit(
                    directory,
                    resume_fn=lambda path, _attempt_lease: (
                        resume_frontier_campaign_navigation(
                            path,
                            workbench_authority_ref=(
                                workbench_authority_ref
                            ),
                            _attempt_lease=_attempt_lease,
                        )
                    ),
                    attempt_lease=lease,
                )
                if recovered is None:
                    raise ValueError(
                        "language successor recovery lost its commit"
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
        elif action == "reopen_extended_adapter_gap":
            directory = _reopen_extended_adapter_gap(directory)
        elif action == "reopen_extended_adapter_recovery":
            directory = _reopen_extended_adapter_recovery(directory)
        elif action == "reopen_extended_navigation":
            directory = _reopen_extended_navigation(directory)
        elif action == "reopen_extended_boundary":
            directory = _reopen_extended_boundary(directory)
        elif action == "reopen_superseded_adapter_gap":
            directory = _reopen_superseded_adapter_gap(directory)
        elif action == "continue_epoch":
            directory = continue_frontier_campaign_epoch(directory)
        elif action == "finalize_budget_stop":
            current = read_json(directory / "run.json", {})
            stop = (current.get("navigation") or {}).get(
                "lineage_synthesis_budget_stop"
            ) or {}
            reason = str(
                stop.get("reason")
                or "blocked_before_action:"
                + _objective_navigation_phase(current)
                + ":provider_calls"
            )
            directory = materialize_frontier_navigation_from_journal(
                directory,
                budget_stop_reason=reason,
            )
        elif action == "recover_lineage_synthesis":
            current = read_json(directory / "run.json", {})
            pending = _pending_durable_lineage_synthesis(directory, current)
            if pending is None:
                raise ValueError("durable synthesis recovery lost its input")
            directory = _recover_durable_lineage_synthesis(
                directory, current, pending
            )
        elif action == "unwind_stale_synthesis_projection":
            directory = _unwind_stale_durable_synthesis_projection(directory)
        elif action == "unwind_invalid_lineage_synthesis":
            directory = _unwind_invalid_active_lineage_synthesis(directory)
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
        elif action == "recover_construction_boundary":
            recover_cold_witness_boundary(
                directory,
                materialize_fn=lambda path, reason: (
                    materialize_frontier_navigation_from_journal(
                        path, budget_stop_reason=reason
                    )
                ),
                verify_fn=lambda path: execute_frontier_campaign_verification(
                    path,
                    with_lean=False,
                    with_isabelle=False,
                    resume_search=False,
                ),
            )
        elif action == "ratify_construction_artifact":
            execute_frontier_construction_artifact_ratification(
                directory,
                lean_root=lean_root,
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
        transitions += 1
        if max_transitions is not None and transitions >= max_transitions:
            return directory


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
    "execute_frontier_construction_artifact_ratification",
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
