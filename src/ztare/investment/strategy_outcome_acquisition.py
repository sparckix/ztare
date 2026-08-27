"""Settle strategy-outcome contracts from admitted point-in-time observations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .compiler import load_point_in_time_snapshot
from .contracts import MetricObservation, PointInTimeSnapshot, canonical_timestamp, timestamp_key
from .sources import PUBLIC_SOURCE_MANIFEST_SCHEMA, SOURCE_RUN_SCHEMA
from .strategy_learning import (
    STRATEGY_MOVE_LIBRARY_SCHEMA,
    STRATEGY_MOVE_OUTCOME_SCHEMA,
    compile_workspace_strategy_move_library,
    due_strategy_outcome_requests,
)
from .strategy_transfer_acquisition import STRATEGY_PROGRAM_CONTROL_ACQUISITION_SCHEMA


STRATEGY_OUTCOME_ACQUISITION_SCHEMA = "jaggedthoughts-strategy-outcome-acquisition-v1"
STRATEGY_OUTCOME_SOURCE_PLAN_SCHEMA = "jaggedthoughts-strategy-outcome-source-plan-v1"
STRATEGY_PROGRAM_OUTCOME_ACQUISITION_SCHEMA = (
    "jaggedthoughts-strategy-program-outcome-acquisition-v1"
)
STRATEGY_PROGRAM_OUTCOME_EPISODE_SCHEMA = "jaggedthoughts-strategy-program-outcome-v1"
STRATEGY_PROGRAM_CONTROL_OUTCOME_ACQUISITION_SCHEMA = (
    "jaggedthoughts-strategy-program-control-outcome-acquisition-v1"
)
STRATEGY_PROGRAM_CONTROL_OUTCOME_EPISODE_SCHEMA = (
    "jaggedthoughts-strategy-program-control-outcome-v1"
)


def compile_strategy_outcome_source_plan(
    library: Mapping[str, Any], manifest: Mapping[str, Any], *, as_of: str,
) -> dict[str, Any]:
    """Select only company-facts sources needed by due point-in-time contracts."""
    if manifest.get("schema") != PUBLIC_SOURCE_MANIFEST_SCHEMA:
        raise ValueError(f"strategy outcome source plan requires {PUBLIC_SOURCE_MANIFEST_SCHEMA}")
    requests = [
        row for row in due_strategy_outcome_requests(library, as_of=as_of)
        if row.get("acquisition_mode") == "point_in_time_observation"
    ]
    sources_by_entity: dict[str, list[str]] = {}
    for source in manifest.get("sources") or ():
        if (
            isinstance(source, Mapping)
            and source.get("adapter") == "sec_companyfacts"
            and source.get("enabled", True) is not False
        ):
            sources_by_entity.setdefault(
                str(source.get("entity_id") or "").upper(), [],
            ).append(str(source.get("id") or ""))
    source_ids = sorted({
        source_id for request in requests
        for source_id in sources_by_entity.get(str(request["entity_id"]).upper(), ())
        if source_id
    })
    missing = sorted({
        str(request["entity_id"]).upper() for request in requests
        if not sources_by_entity.get(str(request["entity_id"]).upper())
    })
    body = {
        "schema": STRATEGY_OUTCOME_SOURCE_PLAN_SCHEMA,
        "as_of": canonical_timestamp(as_of, "strategy outcome source plan as_of"),
        "due_point_in_time_contract_count": len(requests),
        "source_ids": source_ids,
        "missing_source_entity_ids": missing,
        "next_activation": (
            "Refresh the selected SEC company-facts sources and derive typed metrics."
            if source_ids else
            "Enroll the missing SEC company-facts sources."
            if missing else
            "Wait for a point-in-time operating contract to become due."
        ),
        "capital_authority": False,
    }
    return {**body, "source_plan_sha256": stable_sha256(body)}


def _source_bindings(source_run: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    if source_run.get("schema") != SOURCE_RUN_SCHEMA:
        raise ValueError(f"strategy outcome acquisition requires {SOURCE_RUN_SCHEMA}")
    direct = {
        str(row["source_id"]): (str(row["source_id"]),)
        for row in source_run.get("source_receipts") or ()
        if isinstance(row, Mapping) and row.get("source_id")
    }
    bindings = dict(direct)
    for receipt in source_run.get("signal_receipts") or ():
        if not isinstance(receipt, Mapping):
            continue
        observation = receipt.get("observation") or {}
        source_ref = str(observation.get("source_ref") or "")
        inputs = tuple(sorted({str(value) for value in receipt.get("input_source_refs") or ()}))
        if source_ref and inputs and all(value in direct for value in inputs):
            bindings[source_ref] = inputs
    return bindings


def _one_period(
    rows: Iterable[MetricObservation], *, period: str, choose: str,
) -> dict[str, Any] | None:
    grouped: dict[str, list[MetricObservation]] = {}
    for row in rows:
        grouped.setdefault(row.observed_at, []).append(row)
    if not grouped:
        return None
    observed_at = (max if choose == "latest" else min)(grouped)
    selected = grouped[observed_at]
    values = {(row.value, row.unit) for row in selected}
    if len(values) != 1:
        raise ValueError(f"conflicting {period} observations at {observed_at}")
    value, unit = next(iter(values))
    return {
        "value": value, "unit": unit, "observed_at": observed_at,
        "available_at": max(row.available_at for row in selected),
        "observation_ids": sorted(row.observation_id for row in selected),
        "source_refs": sorted({row.source_ref for row in selected}),
    }


def compile_strategy_outcome_acquisition(
    library: Mapping[str, Any], snapshot: PointInTimeSnapshot,
    source_run: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile observation-backed payloads for the existing outcome validator."""
    if library.get("schema") != STRATEGY_MOVE_LIBRARY_SCHEMA:
        raise ValueError(f"strategy outcome acquisition requires {STRATEGY_MOVE_LIBRARY_SCHEMA}")
    source_as_of = canonical_timestamp(source_run.get("as_of"), "source run as_of")
    if timestamp_key(snapshot.as_of) > timestamp_key(source_as_of):
        raise ValueError("outcome snapshot cannot be later than its source run")
    bindings = _source_bindings(source_run)
    requests = due_strategy_outcome_requests(library, as_of=snapshot.as_of)
    observations: dict[tuple[str, str, str], list[MetricObservation]] = {}
    for row in snapshot.observations:
        observations.setdefault((row.entity_id, row.metric_id, row.unit), []).append(row)

    eligible, blocks = [], []
    for request in requests:
        identity = (str(request["entity_id"]), str(request["metric_id"]), str(request["unit"]))
        rows = observations.get(identity, [])
        admitted = [row for row in rows if row.source_ref in bindings]
        baseline_rows = [
            row for row in admitted
            if timestamp_key(row.observed_at) <= timestamp_key(str(request["measurement_start_at"]))
        ]
        outcome_rows = [
            row for row in admitted
            if timestamp_key(row.observed_at) >= timestamp_key(str(request["due_at"]))
        ]
        reason = None
        if request["comparator"] != "pre_move_baseline":
            reason = "comparator_requires_declared_unit_mapping"
        elif not rows:
            reason = "exact_metric_unit_absent"
        elif not admitted:
            reason = "metric_observations_lack_current_source_receipts"
        elif not baseline_rows:
            reason = "baseline_observation_absent"
        elif not outcome_rows:
            reason = "post_horizon_observation_absent"
        if reason:
            blocks.append({
                "request_sha256": request["request_sha256"], "entity_id": request["entity_id"],
                "metric_id": request["metric_id"], "unit": request["unit"], "reason": reason,
                "next_activation": (
                    "Admit a public-source observation with the exact frozen metric and unit."
                    if reason in {"exact_metric_unit_absent", "metric_observations_lack_current_source_receipts"}
                    else "Refresh admitted sources after the frozen horizon reports."
                    if reason == "post_horizon_observation_absent"
                    else "Provide a typed comparator-to-observation mapping; no comparator is inferred."
                    if reason == "comparator_requires_declared_unit_mapping"
                    else "Admit the exact pre-move baseline observation."
                ),
            })
            continue
        baseline = _one_period(baseline_rows, period="baseline", choose="latest")
        outcome = _one_period(outcome_rows, period="outcome", choose="earliest")
        assert baseline is not None and outcome is not None
        public_refs = sorted({
            source_id
            for source_ref in baseline["source_refs"] + outcome["source_refs"]
            for source_id in bindings[source_ref]
        })
        payload = {
            "schema": STRATEGY_MOVE_OUTCOME_SCHEMA,
            "move_sha256": request["move_sha256"],
            "contract_sha256": request["contract_sha256"],
            "observed_at": outcome["observed_at"],
            "available_at": max(baseline["available_at"], outcome["available_at"]),
            "unit": request["unit"],
            "baseline_value": baseline["value"], "outcome_value": outcome["value"],
            "comparator_baseline_value": None, "comparator_outcome_value": None,
            "source_refs": public_refs,
            "point_in_time_evidence": {
                "source_run_sha256": source_run.get("run_sha256"),
                "snapshot_sha256": snapshot.snapshot_sha256,
                "baseline_observation_ids": baseline["observation_ids"],
                "outcome_observation_ids": outcome["observation_ids"],
            },
        }
        receipt = {
            "request_sha256": request["request_sha256"], "outcome": payload,
            "baseline_observation_ids": baseline["observation_ids"],
            "outcome_observation_ids": outcome["observation_ids"],
            "source_run_sha256": source_run.get("run_sha256"),
            "snapshot_sha256": snapshot.snapshot_sha256,
            "selection_rule": "latest pre-start baseline and earliest post-horizon period",
            "capital_authority": False,
        }
        eligible.append({**receipt, "acquisition_receipt_sha256": stable_sha256(receipt)})

    contracts = [
        contract for move in library.get("moves") or ()
        for contract in move.get("outcome_contracts") or ()
        if str(contract.get("contract_sha256")) not in {
            str(episode.get("contract_sha256")) for episode in move.get("outcome_episodes") or ()
        }
    ]
    next_due = min((str(row["due_at"]) for row in contracts), default=None)
    body = {
        "schema": STRATEGY_OUTCOME_ACQUISITION_SCHEMA,
        "as_of": snapshot.as_of, "source_run_sha256": source_run.get("run_sha256"),
        "snapshot_sha256": snapshot.snapshot_sha256,
        "unsettled_contract_count": len(contracts), "due_contract_count": len(requests),
        "eligible_outcome_count": len(eligible), "blocked_due_contract_count": len(blocks),
        "eligible_outcomes": eligible, "blocks": blocks, "next_due_at": next_due,
        "next_activation": (
            "Submit eligible payloads through workspace strategy-outcome."
            if eligible else
            blocks[0]["next_activation"] if blocks else
            f"Refresh public sources at or after {next_due}." if next_due else
            "Declare a measurable outcome contract on an exact strategy move."
        ),
        "authority": "source_bound_outcome_proposal_only", "capital_authority": False,
    }
    return {**body, "acquisition_sha256": stable_sha256(body)}


def compile_strategy_program_outcome_acquisition(
    plans: Iterable[Mapping[str, Any]], existing_episodes: Iterable[Mapping[str, Any]],
    snapshot: PointInTimeSnapshot, source_run: Mapping[str, Any],
) -> dict[str, Any]:
    """Settle matured program readouts with deterministic period selection."""
    source_as_of = canonical_timestamp(source_run.get("as_of"), "source run as_of")
    if timestamp_key(snapshot.as_of) > timestamp_key(source_as_of):
        raise ValueError("program outcome snapshot cannot be later than its source run")
    bindings = _source_bindings(source_run)
    plan_rows = [dict(row) for row in plans if isinstance(row, Mapping)]
    readout_owner = {
        str(readout.get("readout_sha256")): str(plan.get("plan_sha256"))
        for plan in plan_rows for readout in plan.get("readouts") or ()
        if readout.get("readout_sha256") and plan.get("plan_sha256")
    }
    settled = {
        str(row.get("readout_sha256")) for row in existing_episodes
        if isinstance(row, Mapping)
        and row.get("schema") == STRATEGY_PROGRAM_OUTCOME_EPISODE_SCHEMA
        and row.get("episode_sha256") == stable_sha256({
            key: value for key, value in row.items() if key != "episode_sha256"
        })
        and str(row.get("plan_sha256") or "")
        == readout_owner.get(str(row.get("readout_sha256") or ""))
    }
    observations: dict[tuple[str, str, str], list[MetricObservation]] = {}
    for row in snapshot.observations:
        observations.setdefault((row.entity_id, row.metric_id, row.unit), []).append(row)

    due_count, pending_count, eligible, blocks = 0, 0, [], []
    for plan in plan_rows:
        if plan.get("schema") != "jaggedthoughts-strategy-program-outcome-plan-v1":
            continue
        if plan.get("plan_sha256") != stable_sha256({
            key: value for key, value in plan.items() if key != "plan_sha256"
        }):
            continue
        for readout in plan.get("readouts") or ():
            readout_sha = str(readout.get("readout_sha256") or "")
            if readout_sha in settled:
                continue
            pending_count += 1
            if timestamp_key(str(readout["due_at"])) > timestamp_key(snapshot.as_of):
                continue
            due_count += 1
            identity = (str(plan["entity_id"]), str(readout["metric_id"]), str(readout["unit"]))
            rows = observations.get(identity, [])
            admitted = [row for row in rows if row.source_ref in bindings]
            baseline_rows = [
                row for row in admitted if timestamp_key(row.observed_at)
                <= timestamp_key(str(readout["measurement_start_at"]))
            ]
            outcome_rows = [
                row for row in admitted if timestamp_key(row.observed_at)
                >= timestamp_key(str(readout["due_at"]))
            ]
            reason = (
                "exact_metric_unit_absent" if not rows else
                "metric_observations_lack_current_source_receipts" if not admitted else
                "baseline_observation_absent" if not baseline_rows else
                "post_horizon_observation_absent" if not outcome_rows else None
            )
            if reason:
                blocks.append({
                    "plan_sha256": plan["plan_sha256"], "readout_sha256": readout_sha,
                    "entity_id": plan["entity_id"], "metric_id": readout["metric_id"],
                    "unit": readout["unit"], "reason": reason,
                })
                continue
            baseline = _one_period(baseline_rows, period="baseline", choose="latest")
            outcome = _one_period(outcome_rows, period="outcome", choose="earliest")
            assert baseline is not None and outcome is not None
            effect = float(outcome["value"]) - float(baseline["value"])
            signed_effect = effect if readout["direction"] == "increase" else -effect
            threshold = float(readout["minimum_effect"])
            assessment = (
                "supports" if signed_effect >= threshold else
                "contradicts" if signed_effect <= -threshold else "inconclusive"
            )
            public_refs = sorted({
                source_id
                for source_ref in baseline["source_refs"] + outcome["source_refs"]
                for source_id in bindings[source_ref]
            })
            body = {
                "schema": STRATEGY_PROGRAM_OUTCOME_EPISODE_SCHEMA,
                "plan_sha256": plan["plan_sha256"],
                "result_sha256": plan["result_sha256"],
                "readout_sha256": readout_sha, "entity_id": plan["entity_id"],
                "program_id": plan["program_id"], "metric_id": readout["metric_id"],
                "unit": readout["unit"], "direction": readout["direction"],
                "minimum_effect": threshold,
                "horizon_days": readout["horizon_days"],
                "outcome_role": readout.get("outcome_role", "terminal_operating"),
                "acquisition_mode": readout.get(
                    "acquisition_mode", "subscription_primary_document",
                ),
                "source_definition_sha256": readout.get("source_definition_sha256"),
                "measurement_start_at": readout["measurement_start_at"],
                "due_at": readout["due_at"], "observed_at": outcome["observed_at"],
                "available_at": max(baseline["available_at"], outcome["available_at"]),
                "baseline_value": baseline["value"], "outcome_value": outcome["value"],
                "observed_effect": effect, "assessment": assessment,
                "source_refs": public_refs,
                "point_in_time_evidence": {
                    "source_run_sha256": source_run.get("run_sha256"),
                    "snapshot_sha256": snapshot.snapshot_sha256,
                    "baseline_observation_ids": baseline["observation_ids"],
                    "outcome_observation_ids": outcome["observation_ids"],
                    "selection_rule": "latest pre-assessment baseline and earliest post-horizon period",
                },
                "causal_program_credit_eligible": False,
                "portfolio_weight": 0.0, "capital_authority": False,
            }
            eligible.append({**body, "episode_sha256": stable_sha256(body)})
    body = {
        "schema": STRATEGY_PROGRAM_OUTCOME_ACQUISITION_SCHEMA,
        "as_of": snapshot.as_of, "source_run_sha256": source_run.get("run_sha256"),
        "snapshot_sha256": snapshot.snapshot_sha256,
        "unsettled_readout_count": pending_count, "due_readout_count": due_count,
        "eligible_episode_count": len(eligible), "blocked_due_readout_count": len(blocks),
        "eligible_episodes": eligible, "blocks": blocks,
        "next_activation": (
            "Persist the eligible program outcome episodes." if eligible else
            "Refresh admitted public observations after the next frozen program horizon."
        ),
        "causal_program_credit": False, "capital_authority": False,
    }
    return {**body, "acquisition_sha256": stable_sha256(body)}


def compile_strategy_program_control_outcome_acquisition(
    acquisition: Mapping[str, Any], existing_episodes: Iterable[Mapping[str, Any]],
    snapshot: PointInTimeSnapshot, source_run: Mapping[str, Any],
) -> dict[str, Any]:
    """Settle matched program-control readouts on their own frozen clock."""
    if acquisition.get("schema") != STRATEGY_PROGRAM_CONTROL_ACQUISITION_SCHEMA:
        raise ValueError(
            "program control outcomes require a program-control acquisition"
        )
    declared_acquisition = str(acquisition.get("acquisition_sha256") or "")
    if declared_acquisition != stable_sha256({
        key: value for key, value in acquisition.items() if key != "acquisition_sha256"
    }):
        raise ValueError("program control acquisition content hash mismatch")
    source_as_of = canonical_timestamp(source_run.get("as_of"), "source run as_of")
    if timestamp_key(snapshot.as_of) > timestamp_key(source_as_of):
        raise ValueError("program control snapshot cannot be later than its source run")
    bindings = _source_bindings(source_run)
    settled = {
        str(row.get("control_plan_sha256"))
        for row in existing_episodes
        if isinstance(row, Mapping)
        and row.get("schema") == STRATEGY_PROGRAM_CONTROL_OUTCOME_EPISODE_SCHEMA
        and row.get("episode_sha256") == stable_sha256({
            key: value for key, value in row.items() if key != "episode_sha256"
        })
        and row.get("program_control_acquisition_sha256") == declared_acquisition
    }
    observations: dict[tuple[str, str, str], list[MetricObservation]] = {}
    for row in snapshot.observations:
        observations.setdefault((row.entity_id, row.metric_id, row.unit), []).append(row)

    pending_count, due_count, eligible, blocks = 0, 0, [], []
    for card in acquisition.get("cards") or ():
        if not isinstance(card, Mapping):
            continue
        card_sha = str(card.get("acquisition_card_sha256") or "")
        if card_sha != stable_sha256({
            key: value for key, value in card.items()
            if key != "acquisition_card_sha256"
        }):
            raise ValueError("program control acquisition card hash mismatch")
        for target in card.get("admitted_source_controls") or ():
            if not isinstance(target, Mapping):
                continue
            readout = dict(target.get("control_readout") or {})
            readout_sha = str(readout.get("control_plan_sha256") or "")
            if not readout_sha or readout_sha in settled:
                continue
            if readout_sha != stable_sha256({
                key: value for key, value in readout.items()
                if key != "control_plan_sha256"
            }):
                raise ValueError("program control readout content hash mismatch")
            pending_count += 1
            if timestamp_key(str(readout["due_at"])) > timestamp_key(snapshot.as_of):
                continue
            due_count += 1
            identity = (
                str(readout["entity_id"]), str(readout["metric_id"]),
                str(readout["unit"]),
            )
            rows = observations.get(identity, [])
            admitted = [row for row in rows if row.source_ref in bindings]
            baseline_rows = [
                row for row in admitted if timestamp_key(row.observed_at)
                <= timestamp_key(str(readout["measurement_start_at"]))
            ]
            outcome_rows = [
                row for row in admitted if timestamp_key(row.observed_at)
                >= timestamp_key(str(readout["due_at"]))
            ]
            reason = (
                "exact_metric_unit_absent" if not rows else
                "metric_observations_lack_current_source_receipts" if not admitted else
                "baseline_observation_absent" if not baseline_rows else
                "post_horizon_observation_absent" if not outcome_rows else None
            )
            if reason:
                blocks.append({
                    "control_plan_sha256": readout_sha,
                    "entity_id": readout["entity_id"],
                    "metric_id": readout["metric_id"], "unit": readout["unit"],
                    "reason": reason,
                })
                continue
            baseline = _one_period(baseline_rows, period="baseline", choose="latest")
            outcome = _one_period(outcome_rows, period="outcome", choose="earliest")
            assert baseline is not None and outcome is not None
            effect = float(outcome["value"]) - float(baseline["value"])
            signed_effect = effect if readout["direction"] == "increase" else -effect
            threshold = float(readout["minimum_effect"])
            assessment = (
                "supports" if signed_effect >= threshold else
                "contradicts" if signed_effect <= -threshold else "inconclusive"
            )
            public_refs = sorted({
                source_id
                for source_ref in baseline["source_refs"] + outcome["source_refs"]
                for source_id in bindings[source_ref]
            })
            body = {
                "schema": STRATEGY_PROGRAM_CONTROL_OUTCOME_EPISODE_SCHEMA,
                "program_control_acquisition_sha256": declared_acquisition,
                "acquisition_card_sha256": card_sha,
                "transfer_card_sha256": card.get("transfer_card_sha256"),
                "control_plan_sha256": readout_sha,
                "request_sha256": readout["request_sha256"],
                "result_sha256": readout["result_sha256"],
                "entity_id": readout["entity_id"], "program_id": readout["program_id"],
                "control_identity": readout["control_identity"],
                "environment_boundaries": list(readout["environment_boundaries"]),
                "metric_id": readout["metric_id"], "unit": readout["unit"],
                "direction": readout["direction"],
                "minimum_effect": threshold,
                "horizon_days": readout["horizon_days"],
                "outcome_role": readout.get("outcome_role", "terminal_operating"),
                "acquisition_mode": readout.get(
                    "acquisition_mode", "subscription_primary_document",
                ),
                "source_definition_sha256": readout.get("source_definition_sha256"),
                "measurement_start_at": readout["measurement_start_at"],
                "due_at": readout["due_at"], "observed_at": outcome["observed_at"],
                "available_at": max(baseline["available_at"], outcome["available_at"]),
                "baseline_value": baseline["value"], "outcome_value": outcome["value"],
                "observed_effect": effect, "assessment": assessment,
                "source_refs": public_refs,
                "point_in_time_evidence": {
                    "source_run_sha256": source_run.get("run_sha256"),
                    "snapshot_sha256": snapshot.snapshot_sha256,
                    "baseline_observation_ids": baseline["observation_ids"],
                    "outcome_observation_ids": outcome["observation_ids"],
                    "selection_rule": readout["selection_rule"],
                },
                "causal_program_credit_eligible": False,
                "portfolio_weight": 0.0, "capital_authority": False,
            }
            eligible.append({**body, "episode_sha256": stable_sha256(body)})
    body = {
        "schema": STRATEGY_PROGRAM_CONTROL_OUTCOME_ACQUISITION_SCHEMA,
        "as_of": snapshot.as_of,
        "program_control_acquisition_sha256": declared_acquisition,
        "source_run_sha256": source_run.get("run_sha256"),
        "snapshot_sha256": snapshot.snapshot_sha256,
        "unsettled_readout_count": pending_count, "due_readout_count": due_count,
        "eligible_episode_count": len(eligible),
        "blocked_due_readout_count": len(blocks),
        "eligible_episodes": eligible, "blocks": blocks,
        "next_activation": (
            "Persist eligible matched-control outcomes." if eligible else
            "Refresh admitted public observations after the next frozen control horizon."
        ),
        "causal_program_credit": False, "capital_authority": False,
    }
    return {**body, "acquisition_sha256": stable_sha256(body)}


def compile_workspace_strategy_outcome_acquisition(
    workspace: str | Path, *, as_of: str | None = None,
) -> dict[str, Any]:
    """Read one workspace and verify every eligible payload with its existing compiler."""
    root = Path(workspace).expanduser().resolve()
    source_run_path = root / "data" / "latest_source_run.json"
    source_run = json.loads(source_run_path.read_text(encoding="utf-8"))
    epoch = canonical_timestamp(as_of or source_run.get("as_of"), "outcome acquisition as_of")
    library = compile_workspace_strategy_move_library(root)
    due = due_strategy_outcome_requests(library, as_of=epoch)
    snapshot = load_point_in_time_snapshot(
        root / "data" / "observations.csv", as_of=epoch,
        snapshot_id=f"strategy-outcomes@{epoch}", display_path="data/observations.csv",
        entity_ids={str(row["entity_id"]) for row in due},
        metric_ids={str(row["metric_id"]) for row in due},
    )
    acquisition = compile_strategy_outcome_acquisition(library, snapshot, source_run)
    verified = []
    for row in acquisition["eligible_outcomes"]:
        compiled = compile_workspace_strategy_move_library(root, extra_outcomes=(row["outcome"],))
        episodes = [
            episode for move in compiled["moves"] for episode in move["outcome_episodes"]
            if episode["move_sha256"] == row["outcome"]["move_sha256"]
            and episode["contract_sha256"] == row["outcome"]["contract_sha256"]
        ]
        if len(episodes) != 1:
            raise ValueError("observation-backed outcome did not compile to exactly one episode")
        verified.append({**row, "candidate_episode": episodes[0]})
    body = {
        **{key: value for key, value in acquisition.items() if key != "acquisition_sha256"},
        "eligible_outcomes": verified, "existing_compiler_verified_count": len(verified),
    }
    return {**body, "acquisition_sha256": stable_sha256(body)}


def compile_workspace_strategy_program_outcome_acquisition(
    workspace: str | Path, *, as_of: str | None = None,
) -> dict[str, Any]:
    """Compile due integrated-program readouts from one workspace snapshot."""
    root = Path(workspace).expanduser().resolve()
    source_run = json.loads((root / "data" / "latest_source_run.json").read_text(encoding="utf-8"))
    epoch = canonical_timestamp(as_of or source_run.get("as_of"), "program outcome acquisition as_of")
    plans = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "institutional_learning" / "strategy_programs" / "outcome-plans").glob("*.json"))
    ]
    episodes = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "institutional_learning" / "strategy_programs" / "outcomes").glob("*.json"))
    ]
    readouts = [row for plan in plans for row in plan.get("readouts") or ()]
    snapshot = load_point_in_time_snapshot(
        root / "data" / "observations.csv", as_of=epoch,
        snapshot_id=f"strategy-program-outcomes@{epoch}", display_path="data/observations.csv",
        entity_ids={str(plan["entity_id"]) for plan in plans},
        metric_ids={str(row["metric_id"]) for row in readouts},
    )
    return compile_strategy_program_outcome_acquisition(plans, episodes, snapshot, source_run)


def compile_workspace_strategy_program_control_outcome_acquisition(
    workspace: str | Path, *, as_of: str | None = None,
) -> dict[str, Any]:
    """Compile due matched-control readouts from one workspace snapshot."""
    root = Path(workspace).expanduser().resolve()
    source_run = json.loads((root / "data" / "latest_source_run.json").read_text(encoding="utf-8"))
    epoch = canonical_timestamp(
        as_of or source_run.get("as_of"), "program control outcome acquisition as_of",
    )
    acquisition = json.loads((
        root / "institutional_learning" / "strategy_programs"
        / "control-acquisition-latest.json"
    ).read_text(encoding="utf-8"))
    episodes = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((
            root / "institutional_learning" / "strategy_programs" / "control-outcomes"
        ).glob("*.json"))
    ]
    readouts = [
        dict(target.get("control_readout") or {})
        for card in acquisition.get("cards") or ()
        for target in card.get("admitted_source_controls") or ()
        if target.get("control_readout")
    ]
    snapshot = load_point_in_time_snapshot(
        root / "data" / "observations.csv", as_of=epoch,
        snapshot_id=f"strategy-program-control-outcomes@{epoch}",
        display_path="data/observations.csv",
        entity_ids={str(row["entity_id"]) for row in readouts},
        metric_ids={str(row["metric_id"]) for row in readouts},
    )
    return compile_strategy_program_control_outcome_acquisition(
        acquisition, episodes, snapshot, source_run,
    )


def submit_workspace_program_observation_outcomes(
    workspace: str | Path, *, as_of: str | None = None,
) -> dict[str, Any]:
    """Persist every newly eligible program episode with its immutable identity."""
    root = Path(workspace).expanduser().resolve()
    acquisition = compile_workspace_strategy_program_outcome_acquisition(root, as_of=as_of)
    directory = root / "institutional_learning" / "strategy_programs" / "outcomes"
    directory.mkdir(parents=True, exist_ok=True)
    for episode in acquisition["eligible_episodes"]:
        destination = directory / f"{episode['readout_sha256']}.json"
        if destination.is_file():
            continue
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, delete=False,
        ) as handle:
            json.dump(episode, handle, sort_keys=True)
            handle.write("\n")
            temporary = Path(handle.name)
        temporary.replace(destination)
    return {
        **acquisition,
        "submitted_count": len(acquisition["eligible_episodes"]),
    }


def submit_workspace_program_control_observation_outcomes(
    workspace: str | Path, *, as_of: str | None = None,
) -> dict[str, Any]:
    """Persist newly eligible matched-control episodes without rewriting prior clocks."""
    root = Path(workspace).expanduser().resolve()
    acquisition = compile_workspace_strategy_program_control_outcome_acquisition(
        root, as_of=as_of,
    )
    directory = (
        root / "institutional_learning" / "strategy_programs" / "control-outcomes"
    )
    directory.mkdir(parents=True, exist_ok=True)
    submitted = 0
    for episode in acquisition["eligible_episodes"]:
        destination = directory / f"{episode['control_plan_sha256']}.json"
        if destination.is_file():
            continue
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, delete=False,
        ) as handle:
            json.dump(episode, handle, sort_keys=True)
            handle.write("\n")
            temporary = Path(handle.name)
        temporary.replace(destination)
        submitted += 1
    return {**acquisition, "submitted_count": submitted}


def submit_workspace_observation_outcomes(
    workspace: str | Path, *, as_of: str | None = None,
) -> dict[str, Any]:
    """Submit eligible payloads through the existing workspace/golden-store boundary."""
    from .workspace import submit_workspace_strategy_outcome

    root = Path(workspace).expanduser().resolve()
    acquisition = compile_workspace_strategy_outcome_acquisition(root, as_of=as_of)
    submissions = []
    with tempfile.TemporaryDirectory(prefix="jaggedthoughts-strategy-outcomes-") as directory:
        for index, row in enumerate(acquisition["eligible_outcomes"]):
            path = Path(directory) / f"outcome-{index}.json"
            path.write_text(json.dumps(row["outcome"], sort_keys=True) + "\n", encoding="utf-8")
            submissions.append(submit_workspace_strategy_outcome(path, root))
    return {
        "schema": "jaggedthoughts-strategy-observation-outcome-submission-v1",
        "acquisition_sha256": acquisition["acquisition_sha256"],
        "unsettled_contract_count": acquisition["unsettled_contract_count"],
        "due_contract_count": acquisition["due_contract_count"],
        "eligible_outcome_count": acquisition["eligible_outcome_count"],
        "blocked_due_contract_count": acquisition["blocked_due_contract_count"],
        "next_due_at": acquisition["next_due_at"],
        "submitted_count": len(submissions), "submissions": submissions,
        "capital_authority": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    parser.add_argument("--as-of")
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args(argv)
    result = (
        submit_workspace_observation_outcomes(args.workspace, as_of=args.as_of)
        if args.submit else
        compile_workspace_strategy_outcome_acquisition(args.workspace, as_of=args.as_of)
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "STRATEGY_OUTCOME_ACQUISITION_SCHEMA",
    "STRATEGY_PROGRAM_CONTROL_OUTCOME_ACQUISITION_SCHEMA",
    "STRATEGY_PROGRAM_CONTROL_OUTCOME_EPISODE_SCHEMA",
    "STRATEGY_PROGRAM_OUTCOME_ACQUISITION_SCHEMA",
    "STRATEGY_PROGRAM_OUTCOME_EPISODE_SCHEMA",
    "compile_strategy_outcome_acquisition",
    "compile_strategy_outcome_source_plan",
    "compile_strategy_program_control_outcome_acquisition",
    "compile_strategy_program_outcome_acquisition",
    "compile_workspace_strategy_program_control_outcome_acquisition",
    "compile_workspace_strategy_outcome_acquisition",
    "compile_workspace_strategy_program_outcome_acquisition",
    "submit_workspace_observation_outcomes",
    "submit_workspace_program_control_observation_outcomes",
    "submit_workspace_program_observation_outcomes",
]
