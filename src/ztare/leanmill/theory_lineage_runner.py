"""Host-isolated conjectural lineages over one frozen theory context."""
from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ztare.leanmill.frontier_blueprint import (
    FrontierTheoryBlueprint,
    navigator_selection_mode,
)
from ztare.leanmill.theory_campaign_journal import IdempotentReplayJournal
from ztare.leanmill.theory_context import TheoryLandscapeContext
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.exploration_budget import BudgetExceeded
from ztare.leanmill.theory_lineage_synthesis import formula_lineage_request_id
from ztare.leanmill.theory_navigator import (
    NavigatorAgent,
    _receipted_reject_all,
    run_interactive_theory_navigator,
)
from ztare.leanmill.theory_program import (
    TheoryProgram,
    compare_host_isolated_theory_programs,
    derive_context_lineage_id,
)


class _ReplayReservation:
    def __init__(self, action_id: str) -> None:
        self.reservation_id = "replayed:" + action_id
        self.action_id = action_id
        self.phase = "navigation"
        self.resources: dict[str, int] = {}


class _LineageBudgetView:
    """Share hard caps while resetting only a sibling's soft-stop window."""

    def __init__(self, ledger: Any, *, replayed_turns: int = 0) -> None:
        self._ledger = ledger
        self._replayed_turns = replayed_turns
        self._information_start = len(ledger.state()["information"])
        self.budget = ledger.budget

    @staticmethod
    def _round(action_id: str) -> int | None:
        parts = str(action_id).split(":", 2)
        return int(parts[1]) if len(parts) > 1 and parts[0] == "navigator" and parts[1].isdigit() else None

    def _is_replayed_action(self, action_id: str) -> bool:
        round_index = self._round(action_id)
        return round_index is not None and round_index < self._replayed_turns

    def reserve(self, action_id: str, phase: str, resources: Mapping[str, int]):
        if self._is_replayed_action(action_id):
            return _ReplayReservation(action_id)
        return self._ledger.reserve(action_id, phase, resources)

    def commit(self, reservation: Any, actual_resources: Mapping[str, int] | None = None) -> None:
        if str(getattr(reservation, "reservation_id", "")).startswith("replayed:"):
            return
        self._ledger.commit(reservation, actual_resources)

    def release(self, reservation: Any, *, reason: str) -> None:
        if str(getattr(reservation, "reservation_id", "")).startswith("replayed:"):
            return
        self._ledger.release(reservation, reason=reason)

    def observe_information(self, *, action_id: str, **values: Any) -> None:
        if self._is_replayed_action(action_id):
            return
        self._ledger.observe_information(action_id=action_id, **values)

    def soft_stop_reason(self, *, allow_coverage_target: bool = True) -> str | None:
        return self._ledger.soft_stop_reason(
            information_start_index=self._information_start,
            allow_coverage_target=allow_coverage_target,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ledger, name)


def _durable_decision_count(agent: NavigatorAgent) -> int:
    directory = getattr(agent, "artifact_dir", None)
    if directory is None:
        return 0
    count = 0
    for call_path in sorted(Path(directory).glob("*.call.json")):
        try:
            call = json.loads(call_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        prefix = call_path.name.split(".", 1)[0]
        if int(call.get("returncode", 1)) == 0 and (
            call_path.parent / f"{prefix}.result.json"
        ).is_file():
            count += 1
    return count


def _agent_identity(agent: NavigatorAgent, index: int) -> str:
    role = getattr(agent, "call_role", None)
    return str(
        getattr(role, "agent_id", None)
        or getattr(agent, "agent_id", None)
        or f"isolated-callable:{index}"
    )


def _budget_exhausted_navigation(
    context: TheoryLandscapeContext,
    *,
    lineage_id: str,
    epoch: int,
    reason: str,
    provider_calls: int,
) -> dict[str, Any]:
    core = {
        "schema": "leanmill.host_isolated_lineage_exhaustion.v1",
        "context_hash": context.context_hash,
        "context_epoch": epoch,
        "lineage_id": lineage_id,
        "reason": reason,
        "claim_boundary": (
            "this lineage received no further navigation capacity; it contributes "
            "no candidate, rejection, or scientific negative"
        ),
        "authority": "host_budget_ledger",
    }
    receipt = {**core, "receipt_sha256": content_hash(core)}
    return {
        "schema": "leanmill.interactive_theory_navigator.v1",
        "context_hash": context.context_hash,
        "context_epoch": epoch,
        "finalist_node_ids": [],
        "finalists": [],
        "trace": [
            {
                "decision": "budget_stop",
                "reason": reason,
                "lineage_id": lineage_id,
            }
        ],
        "navigation_exhausted_receipt": receipt,
        "provider_calls": provider_calls,
        "cold_view": True,
    }


def aggregate_host_isolated_theory_lineages(
    context: TheoryLandscapeContext,
    lineage_rows: Sequence[Mapping[str, Any]],
    *,
    epoch: int,
) -> dict[str, Any]:
    """Project sealed lineage results without reopening their traces."""

    rows = [dict(row) for row in lineage_rows]
    if not rows:
        raise ValueError("host-isolated aggregation requires a lineage result")
    programs: list[TheoryProgram] = []
    expansions: list[dict[str, Any]] = []
    languages: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reject_receipts: list[dict[str, Any]] = []
    exhaustion_receipts: list[dict[str, Any]] = []
    pending_decisions: list[dict[str, Any]] = []
    for row in rows:
        lineage_id = str(row.get("lineage_id") or "")
        navigation = row.get("navigation")
        if not lineage_id or not isinstance(navigation, Mapping):
            raise ValueError("host-isolated lineage result is malformed")
        if navigation.get("context_hash") != context.context_hash:
            raise ValueError("host-isolated lineage returned another context")
        for finalist in navigation.get("finalists") or ():
            if not isinstance(finalist, Mapping):
                raise ValueError("host-isolated lineage returned a malformed finalist")
            program = TheoryProgram.from_json(finalist.get("theory_program"))
            if program.lineage_id != lineage_id:
                raise ValueError("host-isolated lineage changed its host identity")
            programs.append(program)
        proposal = navigation.get("expansion_proposal")
        if isinstance(proposal, Mapping):
            request = {"lineage_id": lineage_id, "proposal": dict(proposal)}
            expansions.append(
                {**request, "request_id": formula_lineage_request_id(request)}
            )
        language = navigation.get("language_expansion_request")
        if isinstance(language, Mapping):
            languages.append(
                {
                    "lineage_id": lineage_id,
                    "request_id": str(language["request_id"]),
                    "request": dict(language),
                }
            )
        refusal = navigation.get("reject_all_receipt")
        if isinstance(refusal, Mapping):
            reject_receipts.append(dict(refusal))
            rejected.extend(
                dict(candidate)
                for candidate in refusal.get("rejected_candidates") or ()
            )
        exhaustion = navigation.get("navigation_exhausted_receipt")
        if isinstance(exhaustion, Mapping):
            exhaustion_receipts.append(dict(exhaustion))
        pending = navigation.get("pending_leaf_decision")
        if isinstance(pending, Mapping):
            pending_decisions.append(dict(pending))

    comparisons = [
        compare_host_isolated_theory_programs((left, right))
        for left, right in combinations(programs, 2)
        if left.lineage_id != right.lineage_id
    ]
    aggregate_reject = (
        _receipted_reject_all(
            context,
            rejected,
            reason="all_host_isolated_lineages_exhausted_residual_predictions",
        )
        if not programs
        and not expansions
        and not languages
        and rejected
        and len(reject_receipts) == len(rows)
        and not exhaustion_receipts
        else None
    )
    aggregate_exhaustion = None
    if not programs and not expansions and not languages and not pending_decisions and (
        exhaustion_receipts or reject_receipts
    ) and aggregate_reject is None:
        core = {
            "schema": "leanmill.host_isolated_navigation_exhausted.v1",
            "context_hash": context.context_hash,
            "context_epoch": epoch,
            "lineage_count": len(rows),
            "exhausted_lineage_receipts": [
                str(receipt.get("receipt_sha256") or "")
                for receipt in exhaustion_receipts
            ],
            "refused_lineage_receipts": [
                str(receipt.get("receipt_id") or "")
                for receipt in reject_receipts
            ],
            "claim_boundary": (
                "at least one lineage ended without a scientific rejection; "
                "no aggregate reject-all"
            ),
            "authority": "host_lifecycle_receipt",
        }
        aggregate_exhaustion = {**core, "receipt_sha256": content_hash(core)}
    status = (
        "mixed_frozen_outputs"
        if programs and (expansions or languages)
        else "programs_frozen"
        if programs
        else "language_expansion_requested"
        if expansions or languages
        else "pending_leaf_decision"
        if pending_decisions
        else "navigation_exhausted"
        if aggregate_exhaustion is not None
        else "no_candidate"
    )
    lineage_ids = [str(row["lineage_id"]) for row in rows]
    identities = [str(row.get("agent_identity") or "") for row in rows]
    isolation_core = {
        "schema": "leanmill.theory_lineage_isolation.v1",
        "context_hash": context.context_hash,
        "context_epoch": epoch,
        "lineage_ids": lineage_ids,
        "agent_identities": identities,
        "shared_input_classes": [
            "frozen_blueprint",
            "frozen_context",
            "host_receipted_prior_conflicts",
        ],
        "withheld_between_lineages": [
            "action_trace",
            "candidate_presentations",
            "formula_or_language_requests",
            "navigator_rationales",
        ],
        "claim_boundary": (
            "host orchestration noninterference only; no claim of distinct model "
            "priors or statistical independence"
        ),
        "authority": "deterministic_host_orchestration",
    }
    isolation = {
        **isolation_core,
        "receipt_sha256": content_hash(isolation_core),
    }
    core: dict[str, Any] = {
        "schema": "leanmill.host_isolated_theory_lineages.v1",
        "status": status,
        "context_hash": context.context_hash,
        "context_epoch": epoch,
        "lineage_count": len(rows),
        "lineages": rows,
        "finalist_node_ids": [
            str(finalist.get("node_id"))
            for row in rows
            for finalist in row["navigation"].get("finalists") or ()
        ],
        "finalists": [
            dict(finalist)
            for row in rows
            for finalist in row["navigation"].get("finalists") or ()
        ],
        "theory_program_ids": [program.program_id for program in programs],
        "host_isolated_program_comparisons": comparisons,
        "expansion_proposals": expansions,
        "theory_language_expansion_requests": languages,
        "reject_all_receipt": aggregate_reject,
        "navigation_exhausted_receipt": aggregate_exhaustion,
        "pending_leaf_decisions": pending_decisions,
        "isolation_receipt": isolation,
        "provider_calls": sum(
            int(row["navigation"].get("provider_calls", 0)) for row in rows
        ),
        "cold_view": True,
    }
    return {**core, "result_sha256": content_hash(core)}


def run_host_isolated_theory_lineages(
    context: TheoryLandscapeContext,
    blueprint: FrontierTheoryBlueprint,
    *,
    agent_fns: Sequence[NavigatorAgent],
    journal_root: str | Path,
    attempt_id: str,
    campaign_id: str,
    max_rounds: int | Sequence[int],
    max_finalists_per_lineage: int = 2,
    budget_ledger: Any | None = None,
    epoch: int = 0,
    prior_conflict_rows: Sequence[Mapping[str, Any]] = (),
    initial_trace: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Run sealed traces, then compare their frozen outputs.

    This supplies orchestration noninterference: sibling traces and outputs are
    not inputs to another lineage. It does not claim distinct model priors or
    statistical independence merely because calls were separated.
    """

    if navigator_selection_mode(blueprint) != "theory_program":
        raise ValueError("host-isolated lineages require theory_program mode")
    agents = tuple(agent_fns)
    if len(agents) < 2:
        raise ValueError("host-isolated comparison requires at least two lineages")
    rounds_by_lineage = (
        (max_rounds,) * len(agents)
        if isinstance(max_rounds, int)
        else tuple(int(value) for value in max_rounds)
    )
    if len(rounds_by_lineage) != len(agents):
        raise ValueError("lineage round budgets must match the lineage count")
    if min(rounds_by_lineage, default=0) < 1 or max_finalists_per_lineage < 1:
        raise ValueError("lineage budgets must be positive")
    identities = tuple(_agent_identity(agent, index) for index, agent in enumerate(agents))
    explicit_identities = tuple(
        identity for identity in identities if not identity.startswith("isolated-callable:")
    )
    if len(set(explicit_identities)) != len(explicit_identities):
        raise ValueError("host-isolated lineages require distinct agent identities")

    root = Path(journal_root)
    navigations: list[dict[str, Any]] = []
    for index, agent in enumerate(agents):
        lineage_id = derive_context_lineage_id(
            campaign_id=campaign_id,
            attempt_id=attempt_id,
            context_epoch=epoch,
            branch=index,
        )
        lineage_budget = (
            _LineageBudgetView(
                budget_ledger,
                replayed_turns=_durable_decision_count(agent),
            )
            if budget_ledger is not None
            else None
        )
        try:
            navigation = run_interactive_theory_navigator(
                context,
                blueprint,
                IdempotentReplayJournal(
                    root / f"lineage-{index:03d}.events.jsonl"
                ),
                agent_fn=agent,
                attempt_id=f"{attempt_id}:lineage:{index}",
                campaign_id=campaign_id,
                max_rounds=rounds_by_lineage[index],
                max_finalists=max_finalists_per_lineage,
                budget_ledger=lineage_budget,
                epoch=epoch,
                lineage_id=lineage_id,
                prior_conflict_rows=tuple(prior_conflict_rows),
                initial_trace=tuple(initial_trace),
            )
        except BudgetExceeded as exc:
            navigation = _budget_exhausted_navigation(
                context,
                lineage_id=lineage_id,
                epoch=epoch,
                reason=exc.reason,
                provider_calls=_durable_decision_count(agent),
            )
        navigations.append(
            {
                "lineage_id": lineage_id,
                "agent_identity": identities[index],
                "navigation": navigation,
            }
        )
    return aggregate_host_isolated_theory_lineages(
        context, navigations, epoch=epoch
    )


__all__ = ["run_host_isolated_theory_lineages"]
