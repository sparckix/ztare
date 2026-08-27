"""Bind the shortest evidence path to a successor strategy-state experiment."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue

from .contracts import canonical_timestamp, timestamp_key
from .strategy_control_eligibility import STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA
from .strategy_learning import STRATEGY_COHORT_PLAN_SCHEMA
from .strategy_state_experiment import STRATEGY_STATE_EXPERIMENT_SCHEMA


STRATEGY_STATE_SUCCESSOR_READINESS_SCHEMA = (
    "jaggedthoughts-strategy-state-successor-readiness-v1"
)
_COHORT_KIND = "jaggedthoughts_strategy_cohort_research"


def _checked_hash(row: Mapping[str, Any], field: str, label: str) -> str:
    body = dict(row)
    declared = str(body.pop(field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{label} content hash mismatch")
    return declared


def compile_strategy_state_successor_readiness(
    *, predecessor: Mapping[str, Any], plan: Mapping[str, Any],
    control_frontier: Mapping[str, Any], path_run: Mapping[str, Any],
    queue_jobs: Iterable[Mapping[str, Any]], as_of: str,
) -> dict[str, Any]:
    """Select only unresolved peers that can change the frozen successor design."""
    if predecessor.get("schema") != STRATEGY_STATE_EXPERIMENT_SCHEMA:
        raise ValueError("strategy-state successor requires a predecessor experiment")
    if plan.get("schema") != STRATEGY_COHORT_PLAN_SCHEMA:
        raise ValueError("strategy-state successor requires a cohort plan")
    if control_frontier.get("schema") != STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA:
        raise ValueError("strategy-state successor requires a control frontier")
    predecessor_sha = _checked_hash(
        predecessor, "experiment_sha256", "predecessor strategy-state experiment",
    )
    plan_sha = _checked_hash(plan, "plan_sha256", "strategy cohort plan")
    frontier_sha = _checked_hash(
        control_frontier, "control_frontier_sha256", "strategy control frontier",
    )
    if control_frontier.get("plan_sha256") != plan_sha:
        raise ValueError("strategy-state successor plan and control frontier differ")
    if plan_sha == (predecessor.get("input_identity") or {}).get("cohort_plan_sha256"):
        raise ValueError("strategy-state successor requires a later cohort plan")
    if any(predecessor.get(key) is not False for key in (
        "signal_authority", "paper_policy_authority", "capital_authority",
    )):
        raise ValueError("predecessor strategy-state experiment carries forbidden authority")

    path_body = dict(path_run)
    path_sha = str(path_body.pop("run_sha256", ""))
    if path_sha != stable_sha256(path_body):
        raise ValueError("strategy-state successor path run content hash mismatch")
    if path_sha != (predecessor.get("input_identity") or {}).get("path_run_sha256"):
        raise ValueError("strategy-state successor changed the state-path identity")
    contracts = {str(row.get("leg")): row for row in path_run.get("outcome_contracts") or ()}
    if set(contracts) != {"intermediate", "terminal"}:
        raise ValueError("strategy-state successor requires both state-path horizons")
    compiled_at = canonical_timestamp(as_of, "strategy-state successor as_of")
    cutoff = canonical_timestamp(
        contracts["intermediate"].get("settlement_not_before"),
        "strategy-state successor cutoff",
    )

    phenotype_sha = str(
        (predecessor.get("strategy_action") or {}).get("mechanism_phenotype_sha256") or ""
    )
    industry_id = next((
        str(row.get("industry_id") or "")
        for row in predecessor.get("controls") or ()
        if row.get("control_id") == "industry_state_markov"
    ), "")
    if not phenotype_sha or not industry_id:
        raise ValueError("predecessor lacks the successor environment identity")

    matching = [
        dict(row) for row in control_frontier.get("peer_eligibility") or ()
        if (row.get("environment") or {}).get("mechanism_phenotype_sha256") == phenotype_sha
        and (row.get("environment") or {}).get("industry_id") == industry_id
    ]
    if not matching:
        raise ValueError("successor cohort has no same-environment peers")
    request_shas = {str(row.get("request_sha256") or "") for row in matching}
    queue_by_request = {
        str((row.get("payload") or {}).get("request_sha256") or ""): dict(row)
        for row in queue_jobs
        if row.get("kind") == _COHORT_KIND
        and row.get("status") in {"queued", "claimed"}
        and str((row.get("payload") or {}).get("request_sha256") or "") in request_shas
    }
    pending, clean, contaminated = [], [], []
    for peer in sorted(matching, key=lambda row: str(row.get("peer_entity_id") or "")):
        classification = str(peer.get("classification") or "pending")
        row = {
            "peer_entity_id": peer.get("peer_entity_id"),
            "request_sha256": peer.get("request_sha256"),
            "classification": classification,
            "kill_reasons": list(peer.get("kill_reasons") or ()),
        }
        if classification in {"family_adoption_only", "phenotype_adoption_found"}:
            contaminated.append(row)
        elif classification == "no_family_adoption_found":
            clean.append(row)
        elif classification in {"pending", "terminal_source_gap"}:
            job = queue_by_request.get(str(peer.get("request_sha256") or ""))
            row.update({
                "work_id": job.get("work_id") if job else None,
                "queue_status": job.get("status") if job else "missing",
            })
            pending.append(row)

    candidates = [
        {
            **row,
            "selection_rank": rank,
            "frozen_chain_priority": 1_029_900 - rank,
        }
        for rank, row in enumerate(pending, start=1)
        if row.get("work_id")
    ]
    source_entities = {
        str(row.get("entity_id") or "")
        for row in (path_run.get("source_snapshot") or {}).get("assignments") or ()
    }
    same_environment_entities = {
        str(row.get("peer_entity_id") or "") for row in matching
    }
    panel_overlap = sorted(source_entities & same_environment_entities)
    cutoff_open = timestamp_key(compiled_at) < timestamp_key(cutoff)
    status = (
        "state_horizon_expired" if not cutoff_open else
        "peer_control_ready" if clean else
        "awaiting_fixed_peer_classification" if candidates else
        "same_environment_candidate_set_exhausted"
    )
    body = {
        "schema": STRATEGY_STATE_SUCCESSOR_READINESS_SCHEMA,
        "compiled_at": compiled_at,
        "status": status,
        "predecessor_experiment_sha256": predecessor_sha,
        "successor_input_identity": {
            "cohort_plan_sha256": plan_sha,
            "control_frontier_sha256": frontier_sha,
            "path_run_sha256": path_sha,
            "mechanism_phenotype_sha256": phenotype_sha,
            "industry_id": industry_id,
        },
        "fixed_candidate_set_sha256": stable_sha256(sorted(request_shas)),
        "state_horizon": {
            "successor_must_open_before": cutoff,
            "open_window": cutoff_open,
        },
        "peer_control_frontier": {
            "same_environment_count": len(matching),
            "clean_count": len(clean),
            "pending_count": len(pending),
            "contaminated_count": len(contaminated),
            "clean": clean,
            "pending": pending,
            "contaminated": contaminated,
        },
        "industry_state_control": {
            "current_path_peer_overlap_count": len(panel_overlap),
            "current_path_peer_entity_ids": panel_overlap,
            "status": (
                "source_path_contains_same_environment_peers"
                if panel_overlap else "requires_new_industry_conditioned_state_panel"
            ),
        },
        "selected_dependencies": candidates,
        "next_activation": (
            {
                "transition": "classify_fixed_same_environment_peer",
                **candidates[0],
            }
            if candidates else
            {"transition": "compile_successor_strategy_state_experiment"}
            if clean and cutoff_open else None
        ),
        "use_boundary": (
            "The candidate set is fixed by the later cohort plan and the predecessor's exact "
            "phenotype plus industry. Family adopters remain contaminated. A clean peer only "
            "opens a successor design; it does not repair or rewrite the predecessor."
        ),
        "signal_authority": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "readiness_sha256": stable_sha256(body)}


def bind_workspace_strategy_state_successor(workspace: str | Path, *, as_of: str) -> dict[str, Any]:
    """Compile readiness, then attach its exact dependencies to queued cohort jobs."""
    root = Path(workspace).expanduser().resolve()
    predecessor = json.loads(
        (root / "experiments/results/strategy-state-experiment.json").read_text()
    )
    plan = json.loads(
        (root / "institutional_learning/strategy_cohorts/latest.json").read_text()
    )
    frontier = json.loads(
        (root / "institutional_learning/strategy_cohorts/control-eligibility-frontier.json").read_text()
    )
    summary = json.loads(
        (root / "experiments/results/company-state-two-quarter-path-action.json").read_text()
    )
    path_run = json.loads((root / str(summary["artifact_path"])).read_text())
    connection = work_queue.connect(str(root / "state/research_jobs.sqlite3"))
    try:
        rows = work_queue.list_items(connection, limit=10_000)
        readiness = compile_strategy_state_successor_readiness(
            predecessor=predecessor, plan=plan, control_frontier=frontier,
            path_run=path_run, queue_jobs=rows, as_of=as_of,
        )
        updated = []
        for dependency in readiness["selected_dependencies"]:
            work_id = str(dependency["work_id"])
            prior = next(row for row in rows if row.get("work_id") == work_id)
            body = dict(prior.get("payload") or {})
            body.pop("job_sha256", None)
            body.update({
                "frozen_chain_priority": dependency["frozen_chain_priority"],
                "successor_readiness_sha256": readiness["readiness_sha256"],
                "successor_predecessor_experiment_sha256": readiness[
                    "predecessor_experiment_sha256"
                ],
            })
            payload = {**body, "job_sha256": stable_sha256(body)}
            cursor = connection.execute(
                "UPDATE work_items SET priority=?, payload_json=?, updated_at=? "
                "WHERE work_id=? AND kind=? AND status='queued'",
                (
                    int(dependency["frozen_chain_priority"]),
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    int(time.time()), work_id, _COHORT_KIND,
                ),
            )
            if cursor.rowcount == 1:
                updated.append(work_id)
        connection.commit()
    finally:
        connection.close()
    receipt = {**readiness, "bound_work_ids": updated}
    destination = root / "experiments/results/strategy-state-successor-readiness.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


__all__ = [
    "STRATEGY_STATE_SUCCESSOR_READINESS_SCHEMA",
    "bind_workspace_strategy_state_successor",
    "compile_strategy_state_successor_readiness",
]
