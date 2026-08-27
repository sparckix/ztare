"""Prospectively sealed probability-current challengers and tournaments."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.evaluation import compile_evaluation_integrity_receipt

from .contracts import require_text, timestamp_key
from .market_flow_panel import (
    CROSS_SECTIONAL_FLOW_SETTLEMENT_SCHEMA,
    CROSS_SECTIONAL_FLOW_SNAPSHOT_SCHEMA,
    compile_cross_sectional_flow_snapshot,
    conservative_density_step,
    settle_cross_sectional_flow_snapshot,
)
from .market_flow_successor import (
    capture_market_flow_project_inputs,
    classify_market_flow_successor,
    enqueue_market_flow_successor,
    freeze_market_flow_model_bundle_capsule,
)
from .tournament import (
    BacktestEpisode,
    ObservableSpec,
    WorldModelCandidate,
    WorldModelForecast,
    evaluate_world_model_tournament,
)


MARKET_FLOW_SHADOW_RUN_SCHEMA = "jaggedthoughts-market-flow-shadow-run-v1"
MARKET_FLOW_SHADOW_TOURNAMENT_SCHEMA = "jaggedthoughts-market-flow-shadow-tournament-v1"
MARKET_FLOW_SHADOW_STATUS_SCHEMA = "jaggedthoughts-market-flow-shadow-status-v1"
MARKET_FLOW_RESEARCH_ACTIVATION_SCHEMA = "jaggedthoughts-model-research-activation-v1"
MARKET_FLOW_RESEARCH_RESIDUAL_SCHEMA = "jaggedthoughts-market-flow-research-residual-v1"
_CANDIDATE_ID = "lagrangian_probability_current_rejected_shadow"
_CONTROL_IDS = (
    "empirical_markov",
    "persistence",
    "monotone_odd_current_calibration",
)


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _verified(payload: Mapping[str, Any], *, schema: str, hash_field: str) -> dict[str, Any]:
    body = dict(payload)
    declared = str(body.pop(hash_field, ""))
    if body.get("schema") != schema or stable_sha256(body) != declared:
        raise ValueError(f"{schema} content identity mismatch")
    return dict(payload)


def _density_return(snapshot: Mapping[str, Any], density: Iterable[float]) -> float:
    return float(snapshot["center"]) + float(snapshot["scale"]) * sum(
        probability * center
        for probability, center in zip(density, snapshot["bin_centers"], strict=True)
    )


def freeze_market_flow_shadow(
    snapshot: Mapping[str, Any], *, project_dir: str | Path,
    candidate_path: str | Path | None = None,
    lineage_source_refs: Iterable[str] = (),
) -> dict[str, Any]:
    """Freeze one project candidate and ordinary rivals before the next outcome."""
    frozen = _verified(
        snapshot, schema=CROSS_SECTIONAL_FLOW_SNAPSHOT_SCHEMA,
        hash_field="snapshot_sha256",
    )
    project = Path(project_dir).expanduser().resolve()
    candidate = Path(candidate_path or project / "test_model.py").expanduser().resolve()
    project_inputs = capture_market_flow_project_inputs(project, candidate)
    harness = _module(project / "gate_harness.py", "jaggedthoughts_market_flow_gate")
    gate = harness.run_gates(candidate)
    if gate.get("harness_ok") is not True:
        raise ValueError("market-flow candidate lacks a complete deterministic gate receipt")
    model = _module(candidate, "jaggedthoughts_market_flow_candidate")
    params = dict(gate["calibrated_params"])
    features = {
        key: frozen[key]
        for key in ("current_mass", "raw_face_current", "bin_centers", "center", "scale")
    }
    candidate_density = list(model.predict_density(features, params))
    face_masses = [
        (float(left) + float(right)) / 2.0
        for left, right in zip(frozen["current_mass"], frozen["current_mass"][1:])
    ]
    responses = [
        float(model.stationary_response(force, mass, params))
        for force, mass in zip(frozen["raw_face_current"], face_masses, strict=True)
    ]
    action_density = list(conservative_density_step(frozen["current_mass"], responses))
    gradients = [
        abs(float(model.action_gradient(response, force, mass, params)))
        for response, force, mass in zip(
            responses, frozen["raw_face_current"], face_masses, strict=True,
        )
    ]
    curvatures = [
        float(model.action_curvature(response, mass, params))
        for response, mass in zip(responses, face_masses, strict=True)
    ]
    action_receipt = {
        "stationary_residual_max": max(gradients),
        "minimum_action_curvature": min(curvatures),
        "prediction_binding_max_error": max(
            abs(left - right) for left, right in zip(
                candidate_density, action_density, strict=True,
            )
        ),
        "mass_error": abs(sum(candidate_density) - 1.0),
        "minimum_probability": min(candidate_density),
    }
    if (
        action_receipt["stationary_residual_max"] > 1e-9
        or action_receipt["minimum_action_curvature"] <= 0
        or action_receipt["prediction_binding_max_error"] > 1e-10
        or action_receipt["mass_error"] > 1e-9
        or action_receipt["minimum_probability"] < -1e-12
    ):
        raise ValueError("market-flow action fails stationarity, convexity, or density binding")

    odd = gate["selected_monotone_odd_calibration"]
    odd_params = (str(odd["family"]), float(odd["scale"]), float(odd["gain"]))
    predictions = {
        _CANDIDATE_ID: candidate_density,
        "empirical_markov": list(frozen["markov_mass"]),
        "persistence": list(frozen["current_mass"]),
        "monotone_odd_current_calibration": list(
            harness._odd_calibration_density(features, odd_params)
        ),
    }
    candidate_provenance = dict(gate["candidate_provenance"])
    generation = (
        "subscription_llm"
        if candidate_provenance.get("status") == "resolved"
        and candidate_provenance.get("origin") == "subscription_newton_submission"
        else "unknown"
    )
    gate_sha = stable_sha256(gate)
    if project_inputs["candidate_source_sha256"] != gate["candidate_sha256"]:
        raise ValueError("market-flow candidate changed while its gate was running")
    trial_family_id = stable_sha256({
        "project": project.name,
        "evidence_receipt_sha256": gate["evidence_receipt_sha256"],
        "candidate_sha256": gate["candidate_sha256"],
        "control_ids": _CONTROL_IDS,
    })
    research_lineage_refs = tuple(sorted({
        require_text(value, "market-flow research lineage ref")
        for value in lineage_source_refs
    }))
    models = {
        _CANDIDATE_ID: {
            "model_family": "lagrangian",
            "generation_process": generation,
            "source_refs": [
                f"candidate:{gate['candidate_sha256']}", f"gate:{gate_sha}",
                *research_lineage_refs,
            ],
        },
        **{
            model_id: {
                "model_family": "statistical_control",
                "generation_process": "deterministic",
                "source_refs": [f"implementation:{model_id}:v1"],
            }
            for model_id in _CONTROL_IDS
        },
    }
    forecasts = {
        model_id: {
            "density": density,
            "equal_weight_mean_return": _density_return(frozen, density),
        }
        for model_id, density in predictions.items()
    }
    body: dict[str, Any] = {
        "schema": MARKET_FLOW_SHADOW_RUN_SCHEMA,
        "experiment_id": f"{frozen['experiment_id']}-prospective-shadow",
        "as_of": frozen["sealed_at"],
        "sealed_at": frozen["sealed_at"],
        "authority": "experiment_only",
        "capital_authority": False,
        "paper_policy_authority": False,
        "estimand": frozen["estimand"],
        "snapshot_sha256": frozen["snapshot_sha256"],
        "snapshot": frozen,
        "project_id": project.name,
        "candidate_path": candidate.relative_to(project).as_posix(),
        "candidate_sha256": gate["candidate_sha256"],
        "candidate_source": project_inputs["candidate_source"],
        "project_input_sha256": project_inputs["project_input_sha256"],
        "candidate_provenance": candidate_provenance,
        "candidate_retrospective_screen_pass": bool(gate["screen_pass"]),
        "prospective_promotion_eligible": bool(gate["screen_pass"] and generation != "unknown"),
        "action_receipt": action_receipt,
        "trial_family_id": trial_family_id,
        "model_bundle_sha256": stable_sha256({"models": models, "params": params, "odd": odd}),
        "models": models,
        "calibrated_params": params,
        "selected_monotone_odd_calibration": odd,
        "forecasts": forecasts,
        "source_refs": sorted({
            *frozen["source_refs"], f"candidate:{gate['candidate_sha256']}", f"gate:{gate_sha}",
            *research_lineage_refs,
        }),
        "research_lineage_refs": list(research_lineage_refs),
        "research_status": (
            "eligible_frozen_challenger" if gate["screen_pass"] and generation != "unknown"
            else "rejected_ancestor_shadow"
        ),
    }
    return {**body, "run_sha256": stable_sha256(body)}


def compile_market_flow_shadow_tournament(
    runs: Iterable[Mapping[str, Any]], settlements: Iterable[Mapping[str, Any]],
    *, owner: str, min_inference_blocks: int = 8,
) -> dict[str, Any]:
    """Score settled frozen runs through the shared block-aware tournament kernel."""
    frozen_runs = [
        _verified(row, schema=MARKET_FLOW_SHADOW_RUN_SCHEMA, hash_field="run_sha256")
        for row in runs
    ]
    settled = {
        str(row["snapshot_sha256"]): _verified(
            row, schema=CROSS_SECTIONAL_FLOW_SETTLEMENT_SCHEMA,
            hash_field="settlement_sha256",
        )
        for row in settlements if row.get("status") == "settled"
    }
    complete = [row for row in frozen_runs if row["snapshot_sha256"] in settled]
    if not complete:
        raise ValueError("market-flow tournament requires a settled frozen run")
    bundle_ids = {str(row["model_bundle_sha256"]) for row in complete}
    if len(bundle_ids) != 1:
        raise ValueError("market-flow tournament cannot mix model bundles")
    model_ids = tuple(complete[0]["forecasts"])
    if any(tuple(row["forecasts"]) != model_ids for row in complete):
        raise ValueError("market-flow tournament model set drifted")
    bin_count = int(complete[0]["snapshot"]["bin_count"])
    observable_ids = tuple(f"density_bin_{index}" for index in range(bin_count))
    observables = tuple(
        ObservableSpec(name, "probability_mass", "squared", 1.0, 0.8 / bin_count)
        for name in observable_ids
    ) + (ObservableSpec(
        "equal_weight_mean_return", "log_return", "absolute", 0.02, 0.2, "linked",
    ),)
    model_specs = complete[0]["models"]
    models = tuple(WorldModelCandidate(
        model_id=model_id,
        version=str(complete[0]["model_bundle_sha256"])[:12],
        model_family=str(model_specs[model_id]["model_family"]),
        trial_family_id=str(complete[0]["trial_family_id"]),
        mechanism_ids=(model_id,),
        linked_observable_ids=("equal_weight_mean_return",),
        source_refs=tuple(model_specs[model_id]["source_refs"]),
        generation_process=str(model_specs[model_id]["generation_process"]),
    ) for model_id in model_ids)
    episodes = []
    forecasts = []
    availability = []
    for run in complete:
        outcome = settled[str(run["snapshot_sha256"])]
        actual_values = {
            **{
                name: float(value)
                for name, value in zip(observable_ids, outcome["actual_next_mass"], strict=True)
            },
            "equal_weight_mean_return": float(outcome["actual_next_mean_return"]),
        }
        episode_id = str(run["run_sha256"])
        episodes.append(BacktestEpisode(
            episode_id=episode_id,
            inference_block_id=str(outcome["outcome_date"]),
            entity_id=str(run["snapshot"]["entity_ids_sha256"]),
            start_at=str(run["sealed_at"]),
            end_at=str(outcome["outcome_observed_at"]),
            outcome_available_at=str(outcome["outcome_available_at"]),
            starting_weight=0.0,
            asset_return=float(outcome["actual_next_mean_return"]),
            benchmark_return=float(outcome["actual_next_mean_return"]),
            cash_return=0.0,
            actual_values=actual_values,
            source_refs=tuple(sorted({*run["source_refs"], *outcome["source_refs"]})),
        ))
        availability.append({
            "source_id": str(run["snapshot"]["feature_observation_ids_sha256"]),
            "available_at": str(run["snapshot"]["feature_available_at"]),
            "as_of": str(run["sealed_at"]),
        })
        for model_id, prediction in run["forecasts"].items():
            predicted_values = {
                **{
                    name: float(value)
                    for name, value in zip(observable_ids, prediction["density"], strict=True)
                },
                "equal_weight_mean_return": float(prediction["equal_weight_mean_return"]),
            }
            forecasts.append(WorldModelForecast(
                model_id=model_id,
                episode_id=episode_id,
                trained_through=str(run["snapshot"]["feature_available_at"]),
                issued_at=str(run["sealed_at"]),
                predicted_values=predicted_values,
                target_weight=0.0,
                source_refs=(
                    f"run:{run['run_sha256']}", f"snapshot:{run['snapshot_sha256']}",
                ),
            ))
    as_of = max(
        str(settled[str(row["snapshot_sha256"])]["outcome_available_at"])
        for row in complete
    )
    result = evaluate_world_model_tournament(
        tournament_id=f"market-flow-shadow::{next(iter(bundle_ids))[:16]}",
        owner=require_text(owner, "market-flow tournament owner"),
        as_of=as_of,
        mode="prospective_shadow",
        baseline_model_id="empirical_markov",
        observables=observables,
        models=models,
        episodes=tuple(episodes),
        forecasts=tuple(forecasts),
        transaction_cost_bps=0.0,
        declared_trial_family_ids=(str(complete[0]["trial_family_id"]),),
        source_refs=tuple(sorted({
            *(f"run:{row['run_sha256']}" for row in complete),
            *(f"settlement:{settled[row['snapshot_sha256']]['settlement_sha256']}" for row in complete),
        })),
        min_inference_blocks=min_inference_blocks,
        periods_per_year=252.0,
        source_availability_rows=tuple(availability),
    )
    candidate_eligible = all(bool(row["prospective_promotion_eligible"]) for row in complete)
    body = dict(result)
    body.pop("tournament_sha256")
    body.update({
        "shadow_adapter_schema": MARKET_FLOW_SHADOW_TOURNAMENT_SCHEMA,
        "estimand": complete[0]["estimand"],
        "candidate_retrospective_screen_eligible": candidate_eligible,
        "research_status": (
            "eligible_for_research_review"
            if candidate_eligible and result["inference_sufficient"]
            and _CANDIDATE_ID in result["survivor_model_ids"]
            else "shadow_only"
        ),
        "paper_policy_authority": False,
        "capital_authority": False,
    })
    return {**body, "tournament_sha256": stable_sha256(body)}


def compile_market_flow_research_activation(
    tournament: Mapping[str, Any], run: Mapping[str, Any],
) -> dict[str, Any]:
    """Turn a sufficient shadow result into one bounded research consequence."""
    tournament_body = dict(tournament)
    tournament_sha = str(tournament_body.pop("tournament_sha256", ""))
    if stable_sha256(tournament_body) != tournament_sha:
        raise ValueError("market-flow tournament content identity mismatch")
    frozen = _verified(
        run, schema=MARKET_FLOW_SHADOW_RUN_SCHEMA, hash_field="run_sha256",
    )
    if not tournament.get("inference_sufficient"):
        raise ValueError("market-flow research activation requires sufficient inference blocks")
    if f"run:{frozen['run_sha256']}" not in set(tournament.get("source_refs") or ()):
        raise ValueError("market-flow tournament is not bound to the supplied frozen run")
    survived = _CANDIDATE_ID in set(tournament.get("survivor_model_ids") or ())
    if not survived:
        action = "retire_research_due"
        reason = "prospective controls dominated the exact market-flow model bundle"
    elif frozen["prospective_promotion_eligible"]:
        action = "research_review_due"
        reason = "an admitted frozen challenger survived the prospective tournament"
    else:
        action = "successor_research_due"
        reason = (
            "a rejected lineage survived prospectively; author a distinct, "
            "evidence-bound successor rather than promoting the ancestor"
        )
    metrics = {
        str(row.get("model_id") or ""): row
        for row in tournament.get("model_metrics") or ()
        if isinstance(row, Mapping)
    }
    candidate_metrics = dict(metrics.get(_CANDIDATE_ID) or {})
    baseline_id = str(tournament.get("baseline_model_id") or "empirical_markov")
    baseline_metrics = dict(metrics.get(baseline_id) or {})

    def metric_mean(row: Mapping[str, Any], key: str) -> float | None:
        value = row.get(key)
        if not isinstance(value, Mapping) or value.get("mean") is None:
            return None
        return float(value["mean"])

    candidate_prediction = metric_mean(candidate_metrics, "prediction_loss")
    baseline_prediction = metric_mean(baseline_metrics, "prediction_loss")
    candidate_linked = metric_mean(candidate_metrics, "linked_loss")
    baseline_linked = metric_mean(baseline_metrics, "linked_loss")
    candidate_return = metric_mean(candidate_metrics, "net_excess_return")
    baseline_return = metric_mean(baseline_metrics, "net_excess_return")
    residual_body = {
        "schema": MARKET_FLOW_RESEARCH_RESIDUAL_SCHEMA,
        "tournament_sha256": tournament_sha,
        "source_run_sha256": frozen["run_sha256"],
        "model_bundle_sha256": frozen["model_bundle_sha256"],
        "candidate_model_id": _CANDIDATE_ID,
        "candidate_sha256": frozen["candidate_sha256"],
        "baseline_model_id": baseline_id,
        "inference_block_count": int(tournament.get("inference_block_count") or 0),
        "min_inference_blocks": int(tournament.get("min_inference_blocks") or 0),
        "candidate_survived": survived,
        "candidate_on_point_estimate_frontier": _CANDIDATE_ID in set(
            tournament.get("point_estimate_frontier_model_ids") or ()
        ),
        "candidate_metrics": candidate_metrics,
        "baseline_metrics": baseline_metrics,
        "candidate_improvement_over_baseline": {
            "prediction_loss": (
                baseline_prediction - candidate_prediction
                if baseline_prediction is not None and candidate_prediction is not None
                else None
            ),
            "linked_loss": (
                baseline_linked - candidate_linked
                if baseline_linked is not None and candidate_linked is not None
                else None
            ),
            "net_excess_return": (
                candidate_return - baseline_return
                if candidate_return is not None and baseline_return is not None
                else None
            ),
        },
        "candidate_pairwise_comparisons": [
            dict(row) for row in tournament.get("paired_comparisons") or ()
            if isinstance(row, Mapping) and _CANDIDATE_ID in {
                str(row.get("left_model_id") or ""),
                str(row.get("right_model_id") or ""),
            }
        ],
        "next_permitted_action": action,
        "search_question": (
            "Which compact mechanism explains the candidate's prospective advantage "
            "without reproducing the rejected ancestor or weakening its controls?"
            if action == "successor_research_due" else
            "Which measured comparison warrants review without changing policy?"
            if action == "research_review_due" else
            "Which exact prospective control comparison retired this model bundle?"
        ),
        "automatic_model_mutation": False,
        "predictive_law_authority": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    research_residual = {
        **residual_body,
        "research_residual_sha256": stable_sha256(residual_body),
    }
    body = {
        "schema": MARKET_FLOW_RESEARCH_ACTIVATION_SCHEMA,
        "project_id": frozen["project_id"],
        "source_run_sha256": frozen["run_sha256"],
        "tournament_sha256": tournament_sha,
        "model_id": _CANDIDATE_ID,
        "model_bundle_sha256": frozen["model_bundle_sha256"],
        "candidate_sha256": frozen["candidate_sha256"],
        "action": action,
        "reason": reason,
        "research_residual": research_residual,
        "agent_authority": "propose_evidence_bound_project_only",
        "automatic_model_mutation": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "activation_sha256": stable_sha256(body)}


def _json_artifacts(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(item.read_text(encoding="utf-8"))
        for item in sorted(path.glob("*.json")) if item.name != "latest.json"
    ]


def _write_json(path: Path, payload: Mapping[str, Any], *, immutable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"
    if immutable and path.exists() and path.read_text(encoding="utf-8") != rendered:
        raise ValueError(f"content-addressed artifact changed: {path.name}")
    path.write_text(rendered, encoding="utf-8")


def _source_date_information_set(snapshot: Mapping[str, Any]) -> tuple[str, str]:
    return (
        require_text(snapshot.get("experiment_id"), "market-flow experiment_id"),
        require_text(snapshot.get("state_date"), "market-flow state_date"),
    )


def _write_settlement_checkpoint(
    output: Path, *, runs: list[dict[str, Any]],
    settled_snapshots: set[str], as_of: str,
) -> dict[str, Any]:
    """Persist settlement progress before opening or scoring can fail."""
    latest = output / "latest.json"
    prior = json.loads(latest.read_text(encoding="utf-8")) if latest.is_file() else {}
    settled_count = sum(
        str(row["snapshot_sha256"]) in settled_snapshots for row in runs
    )
    checkpoint = {
        "as_of": as_of,
        "run_count": len(runs),
        "settled_count": settled_count,
        "pending_count": len(runs) - settled_count,
    }
    status = {
        **prior,
        "schema": MARKET_FLOW_SHADOW_STATUS_SCHEMA,
        **checkpoint,
        "settlement_checkpoint": checkpoint,
        "research_status": prior.get("research_status", "settlements_refreshed"),
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    _write_json(latest, status)
    return checkpoint


def _candidate_control_disagreement(run: Mapping[str, Any]) -> dict[str, Any]:
    candidate = run["forecasts"][_CANDIDATE_ID]
    candidate_return = float(candidate["equal_weight_mean_return"])
    rows = []
    for control_id in _CONTROL_IDS:
        control = run["forecasts"][control_id]
        control_return = float(control["equal_weight_mean_return"])
        rows.append({
            "control_model_id": control_id,
            "density_l1_distance": sum(
                abs(float(left) - float(right))
                for left, right in zip(
                    candidate["density"], control["density"], strict=True,
                )
            ),
            "equal_weight_return_delta": candidate_return - control_return,
            "direction_disagrees": (
                (candidate_return > 0) != (control_return > 0)
                if candidate_return != 0 and control_return != 0 else False
            ),
        })
    strongest = max(rows, key=lambda row: row["density_l1_distance"])
    return {
        "candidate_model_id": _CANDIDATE_ID,
        "comparisons": rows,
        "strongest_density_disagreement_control": strongest["control_model_id"],
        "direction_disagreement_count": sum(row["direction_disagrees"] for row in rows),
        "outcome_used": False,
    }


def run_market_flow_shadow_cycle(
    *,
    profile_path: str | Path,
    workspace: str | Path,
    project_dir: str | Path,
    as_of: str,
    owner: str,
    output_dir: str | Path | None = None,
    min_inference_blocks: int = 8,
    candidate_path: str | Path | None = None,
    lineage_source_refs: Iterable[str] = (),
) -> dict[str, Any]:
    """Settle, open, and score one registered probability-current shadow."""
    project = Path(project_dir).expanduser().resolve()
    output = Path(output_dir or project / "workspace" / "prospective_shadow").resolve()
    investment_workspace = Path(workspace).expanduser().resolve()
    runs = _json_artifacts(output / "runs")
    settlements = _json_artifacts(output / "settlements")
    settled_snapshots = {str(row["snapshot_sha256"]) for row in settlements}
    for run in runs:
        if str(run["snapshot_sha256"]) in settled_snapshots:
            continue
        settlement = settle_cross_sectional_flow_snapshot(
            run["snapshot"], workspace=investment_workspace, evaluated_at=as_of,
        )
        if settlement["status"] != "settled":
            continue
        _write_json(
            output / "settlements" / f"{settlement['settlement_sha256']}.json",
            settlement,
            immutable=True,
        )
        settlements.append(settlement)
        settled_snapshots.add(str(run["snapshot_sha256"]))

    settlement_checkpoint = _write_settlement_checkpoint(
        output, runs=runs, settled_snapshots=settled_snapshots, as_of=as_of,
    )

    snapshot = compile_cross_sectional_flow_snapshot(
        Path(profile_path).expanduser().resolve(),
        workspace=investment_workspace,
        sealed_at=as_of,
    )
    # Re-fetches within one market state do not create independent evidence.
    information_set = _source_date_information_set(snapshot)
    matching_runs = [
        row for row in runs
        if _source_date_information_set(row["snapshot"]) == information_set
    ]
    opened = None
    if not matching_runs:
        opened = freeze_market_flow_shadow(
            snapshot, project_dir=project, candidate_path=candidate_path,
            lineage_source_refs=lineage_source_refs,
        )
        _write_json(
            output / "runs" / f"{opened['run_sha256']}.json", opened, immutable=True,
        )
        runs.append(opened)
        matching_runs.append(opened)

    settlement_by_snapshot = {
        str(row["snapshot_sha256"]): row for row in settlements
        if row.get("status") == "settled"
    }
    capsule_by_bundle: dict[str, dict[str, Any]] = {}
    for run in runs:
        bundle_sha = str(run["model_bundle_sha256"])
        if bundle_sha in capsule_by_bundle:
            continue
        try:
            capsule = freeze_market_flow_model_bundle_capsule(
                run, project_dir=project, output_dir=output,
            )
            capsule_by_bundle[bundle_sha] = {
                "status": "frozen",
                "capsule_sha256": capsule["capsule_sha256"],
            }
        except (KeyError, OSError, TypeError, ValueError) as error:
            capsule_by_bundle[bundle_sha] = {
                "status": "unavailable",
                "reason": f"{type(error).__name__}: {error}"[:500],
            }
    runs_by_bundle: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        runs_by_bundle.setdefault(str(run["model_bundle_sha256"]), []).append(run)
    tournaments: list[dict[str, Any]] = []
    activations: list[dict[str, Any]] = []
    bundle_progress = []
    for bundle_sha, bundle_runs in sorted(runs_by_bundle.items()):
        settled_runs = [
            row for row in bundle_runs
            if str(row["snapshot_sha256"]) in settlement_by_snapshot
        ]
        blocks = {
            str(settlement_by_snapshot[str(row["snapshot_sha256"])]["outcome_date"])
            for row in settled_runs
        }
        tournament = None
        if len(blocks) >= min_inference_blocks:
            tournament = compile_market_flow_shadow_tournament(
                settled_runs,
                tuple(settlement_by_snapshot.values()),
                owner=owner,
                min_inference_blocks=min_inference_blocks,
            )
            _write_json(
                output / "tournaments" / f"{tournament['tournament_sha256']}.json",
                tournament,
                immutable=True,
            )
            tournaments.append(tournament)
            activation = compile_market_flow_research_activation(
                tournament,
                max(settled_runs, key=lambda row: str(row["sealed_at"])),
            )
            _write_json(
                output / "activations" / f"{activation['activation_sha256']}.json",
                activation,
                immutable=True,
            )
            activations.append(activation)
        bundle_progress.append({
            "model_bundle_sha256": bundle_sha,
            "run_count": len(bundle_runs),
            "settled_count": len(settled_runs),
            "inference_block_count": len(blocks),
            "min_inference_blocks": min_inference_blocks,
            "tournament_sha256": (
                tournament["tournament_sha256"] if tournament else None
            ),
            "research_activation_sha256": (
                activation["activation_sha256"] if tournament else None
            ),
            "model_bundle_capsule": capsule_by_bundle.get(bundle_sha),
        })
    latest_tournament = (
        max(tournaments, key=lambda row: str(row["as_of"]))
        if tournaments else None
    )
    if latest_tournament:
        _write_json(output / "tournaments" / "latest.json", latest_tournament)
    latest_activation = (
        next(
            row for row in activations
            if row["tournament_sha256"] == latest_tournament["tournament_sha256"]
        )
        if latest_tournament else None
    )
    if latest_activation:
        _write_json(output / "activations" / "latest.json", latest_activation)

    research_handoffs: list[dict[str, Any]] = []
    tournament_by_sha = {
        str(row["tournament_sha256"]): row for row in tournaments
    }
    for current_activation in activations:
        if current_activation["action"] == "successor_research_due":
            source_run = next(
                row for row in runs
                if row["run_sha256"] == current_activation["source_run_sha256"]
            )
            try:
                handoff = enqueue_market_flow_successor(
                    workspace=investment_workspace,
                    project_dir=project,
                    output_dir=output,
                    run=source_run,
                    tournament=tournament_by_sha[
                        str(current_activation["tournament_sha256"])
                    ],
                    activation=current_activation,
                )
            except (KeyError, OSError, TypeError, ValueError) as error:
                handoff = {
                    "status": "blocked_exact_successor_lineage",
                    "reason": f"{type(error).__name__}: {error}"[:500],
                    "activation_sha256": current_activation["activation_sha256"],
                    "paper_policy_authority": False,
                    "capital_authority": False,
                }
        elif current_activation["action"] == "research_review_due":
            handoff = {
                "status": "paper_research_review_due",
                "activation_sha256": current_activation["activation_sha256"],
                "automatic_model_mutation": False,
                "paper_policy_authority": False,
                "capital_authority": False,
            }
        else:
            handoff = {
                "status": "retirement_review_due",
                "activation_sha256": current_activation["activation_sha256"],
                "automatic_model_mutation": False,
                "paper_policy_authority": False,
                "capital_authority": False,
            }
        research_handoffs.append(handoff)
    classified_handoffs = []
    for handoff in research_handoffs:
        if handoff.get("status") != "queued_distinct_successor":
            classified_handoffs.append(handoff)
            continue
        try:
            classified_handoffs.append(
                classify_market_flow_successor(investment_workspace, handoff)
            )
        except (KeyError, OSError, TypeError, ValueError) as error:
            classified_handoffs.append({
                "status": "blocked_successor_result_integrity",
                "reason": f"{type(error).__name__}: {error}"[:500],
                "activation_sha256": handoff.get("activation_sha256"),
                "successor_project_id": handoff.get("successor_project_id"),
                "paper_policy_authority": False,
                "capital_authority": False,
            })
    research_handoffs = classified_handoffs
    research_handoff = (
        next(
            row for row in research_handoffs
            if row.get("activation_sha256") == latest_activation["activation_sha256"]
        )
        if latest_activation else {
            "status": "not_due",
            "reason": "prospective tournament activation has not matured",
            "capital_authority": False,
        }
    )
    successor_shadows = []
    repo = Path(__file__).resolve().parents[3]
    for handoff in research_handoffs:
        if handoff.get("status") != "admission_candidate":
            continue
        successor_project = repo / "projects" / str(handoff["successor_project_id"])
        archived_candidate = successor_project / str(handoff["candidate_path"])
        if not archived_candidate.is_file() or hashlib.sha256(
            archived_candidate.read_bytes()
        ).hexdigest() != handoff["candidate_sha256"]:
            successor_shadows.append({
                "project_id": handoff["successor_project_id"],
                "source_successor_result_sha256": handoff["successor_result_sha256"],
                "ok": False,
                "status": "blocked_archived_candidate_identity",
                "paper_policy_authority": False,
                "capital_authority": False,
            })
            continue
        source_run_path = investment_workspace / "data" / "latest_source_run.json"
        source_run = (
            json.loads(source_run_path.read_text(encoding="utf-8"))
            if source_run_path.is_file() else {}
        )
        source_retrieved_at = str(source_run.get("retrieved_at") or "")
        completed_at = str(handoff.get("completed_at") or "")
        if not source_retrieved_at or timestamp_key(source_retrieved_at) <= timestamp_key(completed_at):
            successor_shadows.append({
                "project_id": handoff["successor_project_id"],
                "source_successor_result_sha256": handoff["successor_result_sha256"],
                "ok": True,
                "status": "awaiting_post_research_source_refresh",
                "research_completed_at": completed_at,
                "latest_source_retrieved_at": source_retrieved_at or None,
                "next_activation": "refresh_public_sources",
                "paper_policy_authority": False,
                "capital_authority": False,
            })
            continue
        try:
            child_as_of = max((as_of, completed_at, source_retrieved_at), key=timestamp_key)
            child_snapshot = compile_cross_sectional_flow_snapshot(
                Path(profile_path).expanduser().resolve(),
                workspace=investment_workspace,
                sealed_at=child_as_of,
            )
            if timestamp_key(str(child_snapshot["feature_available_at"])) <= timestamp_key(completed_at):
                successor_shadows.append({
                    "project_id": handoff["successor_project_id"],
                    "source_successor_result_sha256": handoff["successor_result_sha256"],
                    "ok": True,
                    "status": "awaiting_post_research_feature_snapshot",
                    "research_completed_at": completed_at,
                    "feature_available_at": child_snapshot["feature_available_at"],
                    "feature_observation_ids_sha256": child_snapshot[
                        "feature_observation_ids_sha256"
                    ],
                    "next_activation": "refresh_public_sources",
                    "paper_policy_authority": False,
                    "capital_authority": False,
                })
                continue
            child = run_market_flow_shadow_cycle(
                profile_path=profile_path,
                workspace=investment_workspace,
                project_dir=successor_project,
                as_of=child_as_of,
                owner=owner,
                min_inference_blocks=min_inference_blocks,
                candidate_path=archived_candidate,
                lineage_source_refs=(
                    f"successor-result:{handoff['successor_result_sha256']}",
                    f"activation:{handoff['activation_sha256']}",
                    f"lineage:{handoff['lineage_sha256']}",
                    f"job-result:{handoff['job_result_sha256']}",
                ),
            )
            successor_shadows.append({
                "project_id": handoff["successor_project_id"],
                "source_successor_result_sha256": handoff["successor_result_sha256"],
                "ok": True,
                **child,
            })
        except (KeyError, OSError, TypeError, ValueError) as error:
            successor_shadows.append({
                "project_id": handoff["successor_project_id"],
                "source_successor_result_sha256": handoff.get("successor_result_sha256"),
                "ok": False,
                "status": "error",
                "error": f"{type(error).__name__}: {error}"[:500],
                "paper_policy_authority": False,
                "capital_authority": False,
            })

    settled_count = sum(
        str(row["snapshot_sha256"]) in settled_snapshots for row in runs
    )
    latest_run = max(runs, key=lambda row: str(row["sealed_at"]))
    latest_settlement = settlement_by_snapshot.get(str(latest_run["snapshot_sha256"]))
    evaluation_integrity = compile_evaluation_integrity_receipt(
        temporal_design="prospective_sealed",
        generation_processes=(
            str(row["generation_process"])
            for row in latest_run["models"].values()
        ),
        source_availability_rows=({
            "source_id": latest_run["snapshot"]["feature_observation_ids_sha256"],
            "available_at": latest_run["snapshot"]["feature_available_at"],
            "as_of": latest_run["sealed_at"],
        },),
        seal_rows=tuple({
            "episode_id": f"{latest_run['run_sha256']}:{model_id}",
            "sealed_at": latest_run["sealed_at"],
            "episode_start_at": latest_run["sealed_at"],
        } for model_id in latest_run["models"]),
        maturity_rows=({
            "episode_id": latest_run["run_sha256"],
            "episode_end_at": latest_settlement["outcome_observed_at"],
            "outcome_available_at": latest_settlement["outcome_available_at"],
            "evaluated_at": as_of,
        },) if latest_settlement else (),
    )
    status = {
        "schema": MARKET_FLOW_SHADOW_STATUS_SCHEMA,
        "as_of": as_of,
        "run_count": len(runs),
        "settled_count": settled_count,
        "pending_count": len(runs) - settled_count,
        "settlement_checkpoint": settlement_checkpoint,
        "opened_run_sha256": opened["run_sha256"] if opened else None,
        "latest_snapshot_sha256": max(
            matching_runs, key=lambda row: str(row["sealed_at"])
        )["snapshot_sha256"],
        "latest_state_date": snapshot["state_date"],
        "bundle_progress": bundle_progress,
        "tournament_sha256": (
            latest_tournament["tournament_sha256"] if latest_tournament else None
        ),
        "research_status": (
            latest_tournament["research_status"]
            if latest_tournament else "collecting_shadow_evidence"
        ),
        "next_research_action": (
            latest_activation["action"]
            if latest_activation else "collect_next_complete_outcome"
        ),
        "research_activation_sha256": (
            latest_activation["activation_sha256"] if latest_activation else None
        ),
        "research_handoff": research_handoff,
        "research_handoffs": research_handoffs,
        "successor_shadows": successor_shadows,
        "candidate_control_disagreement": _candidate_control_disagreement(latest_run),
        "evaluation_integrity": evaluation_integrity,
        "temporal_contamination_control": {
            "design": "prospective_future_outcome",
            "forecast_sealed_at": latest_run["sealed_at"],
            "historical_llm_replay": False,
            "rule": "outcome_observation_must_follow_forecast_seal",
            "evidence_authority": evaluation_integrity["evidence_authority"],
            "evaluation_integrity_sha256": evaluation_integrity[
                "evaluation_integrity_sha256"
            ],
        },
        "next_activation": "refresh_public_prices_after_next_market_session",
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    _write_json(output / "latest.json", status)
    return status


__all__ = [
    "MARKET_FLOW_SHADOW_RUN_SCHEMA",
    "MARKET_FLOW_SHADOW_STATUS_SCHEMA",
    "MARKET_FLOW_SHADOW_TOURNAMENT_SCHEMA",
    "MARKET_FLOW_RESEARCH_ACTIVATION_SCHEMA",
    "MARKET_FLOW_RESEARCH_RESIDUAL_SCHEMA",
    "compile_market_flow_research_activation",
    "compile_market_flow_shadow_tournament",
    "freeze_market_flow_shadow",
    "run_market_flow_shadow_cycle",
]
