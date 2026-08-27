"""Freeze an attributed Newton path candidate into a prospective company-state run."""

from __future__ import annotations

import copy
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
from itertools import product
import json
import math
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .company_state_flow import decompose_transition_counts
from .company_state_path_action import (
    COMPANY_STATE_PATH_ACTION_RUN_SCHEMA,
    COMPANY_STATE_PATH_OUTCOME_CONTRACT_SCHEMA,
    _contract,
    _validate_distributions,
)
from .company_state_path_action_settlement import _validated_run
from .contracts import canonical_timestamp, timestamp_key
from .evidence_vault import evidence_manifest_ref
from .newton_candidate_provenance import resolve_newton_candidate_provenance


COMPANY_STATE_NEWTON_CANDIDATE_FREEZE_SCHEMA = (
    "jaggedthoughts-company-state-newton-candidate-freeze-v1"
)
_PATH_STATUS_SCHEMA = "jaggedthoughts-company-state-path-action-status-v1"
_RESEARCH_RESULT_SCHEMA = "jaggedthoughts-mechanism-research-result-v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_run(source: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(source, Mapping):
        return copy.deepcopy(dict(source))
    return json.loads(Path(source).expanduser().resolve().read_text(encoding="utf-8"))


def _project_root(candidate: Path) -> Path:
    for parent in (candidate.parent, *candidate.parents):
        if (parent / "evidence.txt").is_file() and (parent / "workspace").is_dir():
            return parent
    raise ValueError("candidate is not inside a Newton project with visible evidence")


def _project_evidence_lineage(project: Path) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[3]
    try:
        project_path = project.relative_to(repo).as_posix()
    except ValueError:
        project_path = project.as_posix()
    visible = project / (
        "evidence_state.txt" if (project / "evidence_state.txt").is_file()
        else "evidence.txt"
    )
    paths = {
        "evidence_receipt": project / "evidence_source_receipt.json",
        "historical_admission": project / "workspace" / "historical_admission.json",
        "gate_result": project / "workspace" / "historical_gate_results.json",
        "visible": visible,
        "holdout": project / "evidence_holdout.txt",
        "farther_tail": project / "evidence_farther_tail.txt",
    }
    if any(not path.is_file() for path in paths.values()):
        raise ValueError("Newton project evidence lineage is incomplete")
    receipt = _load_run(paths["evidence_receipt"])
    admission = _load_run(paths["historical_admission"])
    gate = _load_run(paths["gate_result"])
    return {
        "project_id": project.name,
        "project_path": project_path,
        "evidence_receipt_sha256": hashlib.sha256(
            paths["evidence_receipt"].read_bytes()
        ).hexdigest(),
        "historical_admission_sha256": hashlib.sha256(
            paths["historical_admission"].read_bytes()
        ).hexdigest(),
        "gate_result_sha256": hashlib.sha256(paths["gate_result"].read_bytes()).hexdigest(),
        "partition_file_sha256s": {
            name: hashlib.sha256(paths[name].read_bytes()).hexdigest()
            for name in ("visible", "holdout", "farther_tail")
        },
        "source_evidence": {
            key: copy.deepcopy(receipt.get(key)) for key in (
                "schema", "source_run_sha256", "deterministic_seed_run_sha256",
                "evidence_sha256", "partition_sha256", "partition_frontier_sha256",
                "input_file_sha256", "point_in_time_authority",
            )
        },
        "admission": admission,
        "gate": gate,
    }


def _successor_activation(
    source: Mapping[str, Any], status: Mapping[str, Any],
) -> dict[str, Any]:
    body = dict(status)
    status_sha = str(body.pop("status_sha256", ""))
    if status.get("schema") != _PATH_STATUS_SCHEMA or status_sha != stable_sha256(body):
        raise ValueError("Newton successor activation status is invalid")
    activation = dict(status.get("model_research_activation") or {})
    activation_body = dict(activation)
    activation_sha = str(activation_body.pop("activation_sha256", ""))
    terminal_score = dict((status.get("scores") or {}).get("terminal") or {})
    if not (
        status.get("run_sha256") == source.get("run_sha256")
        and status.get("status") == "settled"
        and (status.get("terminal") or {}).get("status") == "settled"
        and status.get("signal_authority") is False
        and status.get("capital_authority") is False
        and activation_sha == stable_sha256(activation_body)
        and activation.get("run_sha256") == source.get("run_sha256")
        and activation.get("terminal_score_sha256") == terminal_score.get("score_sha256")
        and activation.get("status") == "successor_research_due"
        and activation.get("action") == "subscription_newton_successor_project"
        and activation.get("empirical_markov_control_present") is True
        and activation.get("automatic_model_mutation") is False
        and activation.get("capital_authority") is False
        and "empirical_markov_path_control" in {
            str(model.get("model_id")) for model in source.get("models") or ()
        }
    ):
        raise ValueError("Newton successor requires its exact eligible source activation")
    return activation


def _screen_passing_result(
    result: Mapping[str, Any], *, project: Path, candidate_sha: str,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    body = dict(result)
    result_sha = str(body.pop("research_result_sha256", ""))
    declared_project = Path(str(result.get("project_path") or "")).expanduser()
    if not declared_project.is_absolute():
        declared_project = Path(__file__).resolve().parents[3] / declared_project
    lineage = dict(result.get("search_lineage") or {})
    lineage_body = dict(lineage)
    lineage_sha = str(lineage_body.pop("search_lineage_sha256", ""))
    admission = dict(result.get("historical_admission") or {})
    current = _project_evidence_lineage(project)
    current_admission = dict(current["admission"])
    current_gate = dict(current["gate"])
    if not (
        result.get("schema") == _RESEARCH_RESULT_SCHEMA
        and result_sha == stable_sha256(body)
        and result.get("project_id") == current["project_id"]
        and result.get("authority") == "experiment_only"
        and result.get("capital_authority") is False
        and result.get("harness_ok") is True
        and result.get("screen_pass") is True
        and result.get("status") == "diagnostic_survivor"
        and result.get("candidate_sha256") == candidate_sha
        and declared_project.resolve() == project
        and result.get("evidence_receipt_sha256") == current["evidence_receipt_sha256"]
        and result.get("gate_result_sha256") == current["gate_result_sha256"]
        and result.get("partition_file_sha256s") == current["partition_file_sha256s"]
        and result.get("point_in_time_authority")
        == current["source_evidence"]["point_in_time_authority"]
        and lineage_sha == stable_sha256(lineage_body)
        and lineage.get("current_candidate_sha256") == candidate_sha
        and lineage.get("current_candidate_source") == "submission"
        and provenance.get("submission_path") in lineage.get("matching_submission_paths", ())
        and admission.get("status") == "complete"
        and admission.get("screen_pass") is True
        and admission.get("candidate_sha256") == candidate_sha
        and admission.get("candidate_provenance") == provenance
        and current_admission.get("status") == "complete"
        and current_admission.get("capital_authority") is False
        and current_admission.get("candidate_sha256") == candidate_sha
        and current_admission.get("candidate_provenance") == provenance
        and current_admission.get("evidence_receipt_sha256")
        == current["evidence_receipt_sha256"]
        and current_admission.get("gate_result") == current_gate
        and current_gate.get("harness_ok") is True
        and current_gate.get("screen_pass") is True
        and current_gate.get("candidate_sha256") == candidate_sha
        and current_gate.get("candidate_provenance") == provenance
        and current_gate.get("evidence_receipt_sha256")
        == current["evidence_receipt_sha256"]
        and current_gate.get("partition_file_sha256s")
        == current["partition_file_sha256s"]
        and current_gate.get("signal_authority") is False
        and current_gate.get("capital_authority") is False
    ):
        raise ValueError("Newton successor requires its exact screen-passing candidate result")
    return dict(result)


def _candidate_module(path: Path, state_ids: Sequence[str]) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"company_state_newton_{hashlib.sha256(path.read_bytes()).hexdigest()[:12]}", path,
    )
    if spec is None or spec.loader is None:
        raise ValueError("Newton candidate module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("STATE_IDS", "LAGRANGIAN", "fit_model", "path_action", "predict_path_distribution"):
        if not hasattr(module, name):
            raise ValueError(f"Newton candidate lacks required surface: {name}")
    if tuple(map(str, module.STATE_IDS)) != tuple(state_ids):
        raise ValueError("Newton candidate state order differs from the prospective run")
    if not isinstance(module.LAGRANGIAN, str) or not module.LAGRANGIAN.strip():
        raise ValueError("Newton candidate LAGRANGIAN must be a nonempty string")
    return module


def _visible_rows(path: Path, state_ids: Sequence[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        raw = list(csv.DictReader(handle, delimiter="\t"))
    fields = ("source_state_id", "intermediate_state_id", "terminal_state_id")
    states = set(state_ids)
    rows = [{field: str(row[field]) for field in fields} for row in raw]
    if not rows or any(value not in states for row in rows for value in row.values()):
        raise ValueError("visible Newton evidence has no usable path rows or unknown states")
    return rows


def _json_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    payload = dict(value)
    try:
        json.dumps(payload, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be finite JSON") from error
    return payload


def _softmax(actions: Sequence[float]) -> list[float]:
    floor = min(actions)
    weights = [math.exp(-(value - floor)) for value in actions]
    probabilities = [value / math.fsum(weights) for value in weights]
    probabilities[-1] += 1.0 - math.fsum(probabilities)
    return probabilities


def _challenger(
    module: ModuleType, state_ids: Sequence[str], parameters: Mapping[str, Any],
) -> tuple[dict[str, Any], float]:
    paths = tuple(product(state_ids, repeat=2))
    conditionals, maximum_binding_residual = [], 0.0
    for source_id in state_ids:
        actions = [
            float(module.path_action(source_id, intermediate_id, terminal_id, parameters))
            for intermediate_id, terminal_id in paths
        ]
        if any(not math.isfinite(value) for value in actions):
            raise ValueError("Newton candidate path action must be finite")
        probabilities = [float(value) for value in module.predict_path_distribution(source_id, parameters)]
        if (
            len(probabilities) != len(paths)
            or any(not math.isfinite(value) or value < 0.0 for value in probabilities)
            or abs(math.fsum(probabilities) - 1.0) > 1e-12
        ):
            raise ValueError("Newton candidate returned an invalid path distribution")
        expected = _softmax(actions)
        residual = max(abs(left - right) for left, right in zip(probabilities, expected, strict=True))
        maximum_binding_residual = max(maximum_binding_residual, residual)
        if residual > 1e-10:
            raise ValueError("Newton candidate prediction is not bound to its declared action")
        conditionals.append({
            "source_state_id": source_id,
            "paths": [{
                "intermediate_state_id": intermediate_id,
                "terminal_state_id": terminal_id,
                "mathematical_action": action,
                "current_component": None,
                "probability": probability,
            } for (intermediate_id, terminal_id), action, probability in zip(
                paths, actions, probabilities, strict=True,
            )],
        })
    return {
        "model_id": "path_action_current",
        "role": "challenger",
        "parameters": dict(parameters),
        "conditional_path_distributions": conditionals,
        "signal_authority": False,
        "capital_authority": False,
    }, maximum_binding_residual


def _transition_counts(
    rows: Sequence[Mapping[str, str]], state_ids: Sequence[str],
) -> list[list[int]]:
    index = {state_id: offset for offset, state_id in enumerate(state_ids)}
    counts = [[0] * len(state_ids) for _ in state_ids]
    for row in rows:
        for source, target in (
            (row["source_state_id"], row["intermediate_state_id"]),
            (row["intermediate_state_id"], row["terminal_state_id"]),
        ):
            counts[index[source]][index[target]] += 1
    return counts


def _markov_control(
    model_id: str, transition: Sequence[Sequence[float]],
    state_ids: Sequence[str], counts: Sequence[Sequence[int]],
) -> dict[str, Any]:
    conditionals = []
    for source_index, source_id in enumerate(state_ids):
        paths = [{
            "intermediate_state_id": intermediate_id,
            "terminal_state_id": terminal_id,
            "mathematical_action": None,
            "current_component": 0.0,
            "probability": (
                transition[source_index][intermediate_index]
                * transition[intermediate_index][terminal_index]
            ),
        } for intermediate_index, intermediate_id in enumerate(state_ids)
          for terminal_index, terminal_id in enumerate(state_ids)]
        paths[-1]["probability"] += 1.0 - math.fsum(row["probability"] for row in paths)
        conditionals.append({"source_state_id": source_id, "paths": paths})
    return {
        "model_id": model_id,
        "role": "required_control",
        "parameters": {
            "pseudocount": 1.0,
            "transition_counts_sha256": stable_sha256(counts),
            "fit_source": "visible_newton_evidence_only",
        },
        "conditional_path_distributions": conditionals,
        "signal_authority": False,
        "capital_authority": False,
    }


def _new_contracts(
    source_run: Mapping[str, Any], source_contracts: Sequence[Mapping[str, Any]], *,
    opened_at: str, candidate_sha256: str, evidence_ref_sha256: str,
) -> list[dict[str, Any]]:
    by_leg = {str(row["leg"]): dict(row) for row in source_contracts}
    intermediate_base, terminal_base = by_leg["intermediate"], by_leg["terminal"]
    identity = dict(intermediate_base["frontier_evidence_identity"])
    frozen_fields = (
        "partition_sha256", "benchmark_id", "min_years", "source_entity_count",
        "source_entity_ids_sha256", "source_assignments_sha256", "membership_rule",
        "target_threshold_population", "minimum_target_entity_count", "availability_rule",
    )
    common = {key: identity[key] for key in frozen_fields}
    contracts = []
    for leg, base, target_epoch, required_output in (
        (
            "intermediate", intermediate_base, identity["target_epoch"],
            "frozen-cohort intermediate state assignment",
        ),
        (
            "terminal", terminal_base, terminal_base["target_epoch"],
            "frozen-cohort terminal state assignment and complete two-step paths",
        ),
    ):
        seed = {
            "leg": leg,
            "source_path_action_run_sha256": source_run["run_sha256"],
            "source_contract_sha256": base["contract_sha256"],
            "candidate_sha256": candidate_sha256,
            "evidence_manifest_ref_sha256": evidence_ref_sha256,
            "opened_at": opened_at,
            "source_epoch": identity["source_epoch"],
            "target_epoch": target_epoch,
        }
        evidence_id = (
            f"company-state-newton-{leg}:{identity['source_epoch']}:{target_epoch}:"
            f"{stable_sha256(seed)[:16]}"
        )
        body: dict[str, Any] = {
            "schema": COMPANY_STATE_PATH_OUTCOME_CONTRACT_SCHEMA,
            "leg": leg,
            "status": "prospective_shadow_open",
            "opened_at": opened_at,
            "evidence_id": evidence_id,
            "base_evidence_id": base["evidence_id"],
            "source_path_action_run_sha256": source_run["run_sha256"],
            "source_contract_sha256": base["contract_sha256"],
            "candidate_sha256": candidate_sha256,
            "evidence_manifest_ref_sha256": evidence_ref_sha256,
            "source_epoch": identity["source_epoch"],
            "target_epoch": target_epoch,
            "settlement_not_before": base["settlement_not_before"],
            "required_output": required_output,
            **common,
            "signal_authority": False,
            "capital_authority": False,
        }
        if leg == "intermediate":
            body.update({
                "frontier_evidence_sha256": stable_sha256(identity),
                "frontier_evidence_identity": identity,
            })
        else:
            body["intermediate_epoch"] = terminal_base["intermediate_epoch"]
        contracts.append(_contract(body))
    if any(
        new["evidence_id"] == old["evidence_id"]
        or new["contract_sha256"] == old["contract_sha256"]
        for new, old in zip(contracts, (intermediate_base, terminal_base), strict=True)
    ):
        raise ValueError("Newton successor must open new outcome contract identities")
    return contracts


def freeze_company_state_newton_successor(
    workspace: str | Path,
    source_run: Mapping[str, Any] | str | Path,
    candidate_path: str | Path,
    activation_status: Mapping[str, Any] | str | Path,
    research_result: Mapping[str, Any] | str | Path,
    *,
    opened_at: str | None = None,
) -> dict[str, Any]:
    """Fit from visible evidence and freeze a zero-authority prospective successor."""

    root = Path(workspace).expanduser().resolve()
    source = _load_run(source_run)
    source_contracts = _validated_run(source)
    if source.get("status") != "prospective_shadow_open":
        raise ValueError("Newton successor source run must still be prospective")
    activation = _successor_activation(source, _load_run(activation_status))

    candidate = Path(candidate_path).expanduser().resolve()
    project = _project_root(candidate)
    candidate_bytes = candidate.read_bytes()
    candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
    provenance = resolve_newton_candidate_provenance(project, candidate)
    if not (
        provenance.get("status") == "resolved"
        and provenance.get("origin") == "subscription_newton_submission"
        and provenance.get("iteration_index") is not None
        and provenance.get("run_id") is not None
    ):
        raise ValueError("Newton candidate lacks resolved subscription provenance")
    admitted_result = _screen_passing_result(
        _load_run(research_result), project=project, candidate_sha=candidate_sha,
        provenance=provenance,
    )
    project_lineage = _project_evidence_lineage(project)

    frozen_at = canonical_timestamp(opened_at or _utc_now(), "Newton successor opened_at")
    if not (
        timestamp_key(str(source["opened_at"])) <= timestamp_key(frozen_at)
        < timestamp_key(str(source_contracts[0]["settlement_not_before"]))
        < timestamp_key(str(source_contracts[1]["settlement_not_before"]))
    ):
        raise ValueError("Newton successor must freeze before both source outcome horizons")

    state_ids = tuple(map(str, source["state_ids"]))
    visible_path = project / "evidence.txt"
    visible = _visible_rows(visible_path, state_ids)
    visible_sha = hashlib.sha256(visible_path.read_bytes()).hexdigest()
    module = _candidate_module(candidate, state_ids)
    parameters = _json_mapping(module.fit_model(copy.deepcopy(visible)), "Newton fitted parameters")
    if candidate.read_bytes() != candidate_bytes:
        raise ValueError("Newton candidate source changed while it was being frozen")
    challenger, binding_residual = _challenger(module, state_ids, parameters)

    counts = _transition_counts(visible, state_ids)
    decomposition = decompose_transition_counts(counts, pseudocount=1.0)
    controls = [
        copy.deepcopy(model) for model in source["models"]
        if model["role"] == "required_control"
    ]
    control_ids = {str(model["model_id"]) for model in controls}
    for model_id, key in (
        ("empirical_markov_path_control", "directed_transition"),
        ("reversible_markov_path_control", "reversible_transition"),
    ):
        if model_id not in control_ids:
            controls.append(_markov_control(model_id, decomposition[key], state_ids, counts))
            control_ids.add(model_id)
    models = [challenger, *controls]
    checks = _validate_distributions(models, state_ids)
    checks.update({
        "action_prediction_binding_max_abs": binding_residual,
        "action_prediction_binding_pass": True,
        "visible_fit_row_count": len(visible),
    })

    source_refs = sorted({str(value) for value in source.get("source_refs") or ()})
    archive = evidence_manifest_ref(root, as_of=frozen_at, required_source_ids=source_refs)
    archive_body = dict(archive)
    archive_sha = str(archive_body.pop("ref_sha256", ""))
    if archive_sha != stable_sha256(archive_body):
        raise ValueError("point-in-time evidence reference hash mismatch")
    if (
        archive.get("status") != "covered"
        or archive.get("archive_authority") != "point_in_time_archive"
        or archive.get("required_source_ids") != source_refs
    ):
        raise ValueError("source run is not covered by a current point-in-time evidence manifest")

    code = candidate_bytes.decode("utf-8")
    freeze_body = {
        "schema": COMPANY_STATE_NEWTON_CANDIDATE_FREEZE_SCHEMA,
        "frozen_at": frozen_at,
        "candidate_path": candidate.relative_to(project).as_posix(),
        "candidate_sha256": candidate_sha,
        "candidate_code": code,
        "candidate_provenance": provenance,
        "source_activation_sha256": activation["activation_sha256"],
        "research_result_sha256": admitted_result["research_result_sha256"],
        "research_project_lineage": {
            key: copy.deepcopy(project_lineage[key]) for key in (
                "project_id", "project_path", "evidence_receipt_sha256",
                "historical_admission_sha256", "gate_result_sha256",
                "partition_file_sha256s", "source_evidence",
            )
        } | {
            "candidate_sha256": candidate_sha,
            "research_result_sha256": admitted_result["research_result_sha256"],
            "search_lineage_sha256": admitted_result["search_lineage"][
                "search_lineage_sha256"
            ],
            "diagnostic_status": admitted_result["status"],
        },
        "lagrangian": module.LAGRANGIAN,
        "fitted_parameters": parameters,
        "fit_evidence": {
            "path": "evidence.txt",
            "sha256": visible_sha,
            "row_count": len(visible),
            "columns": ["source_state_id", "intermediate_state_id", "terminal_state_id"],
        },
        "action_prediction_binding_max_abs": binding_residual,
        "signal_authority": False,
        "capital_authority": False,
    }
    candidate_freeze = {**freeze_body, "freeze_sha256": stable_sha256(freeze_body)}
    contracts = _new_contracts(
        source, source_contracts, opened_at=frozen_at, candidate_sha256=candidate_sha,
        evidence_ref_sha256=archive_sha,
    )
    source_contract_refs = [{
        "leg": contract["leg"],
        "evidence_id": contract["evidence_id"],
        "contract_sha256": contract["contract_sha256"],
    } for contract in source_contracts]
    body: dict[str, Any] = {
        "schema": COMPANY_STATE_PATH_ACTION_RUN_SCHEMA,
        "experiment_id": f"{source['experiment_id']}-newton-successor",
        "as_of": frozen_at,
        "status": "prospective_shadow_open",
        "authority": "experiment_only",
        "opened_at": frozen_at,
        "generation_mode": "subscription_newton_successor",
        "subscription_newton_searched": True,
        "source_path_action_run_sha256": source["run_sha256"],
        "source_outcome_contract_refs": source_contract_refs,
        "candidate_freeze": candidate_freeze,
        "evidence_manifest_ref": archive,
        "profile_sha256": source["profile_sha256"],
        "partition_frontier_sha256": source["partition_frontier_sha256"],
        "activation_sha256": source["activation_sha256"],
        "partition_sha256": source["partition_sha256"],
        "source_snapshot": copy.deepcopy(source["source_snapshot"]),
        "source_refs": source_refs,
        "source_assignments_sha256": source["source_assignments_sha256"],
        "state_ids": list(state_ids),
        "mathematical_action": {
            "family": "subscription Newton two-step company-state path action",
            "formula": module.LAGRANGIAN,
            "parameters": parameters,
            "parameter_source": "fitted once from the Newton project's visible evidence partition",
            "candidate_sha256": candidate_sha,
        },
        "required_control_ids": [str(model["model_id"]) for model in controls],
        "models": models,
        "structural_checks": checks,
        "outcome_contracts": contracts,
        "settlement_scoring": copy.deepcopy(source["settlement_scoring"]),
        "evaluation_status": "awaiting_both_prospective_outcomes",
        "promotion_rule": (
            "No use beyond research until both new legs settle and the challenger beats every "
            "frozen required control under the declared Brier rule."
        ),
        "signal_authority": False,
        "model_fit_authority": False,
        "capital_authority": False,
        "use_boundary": (
            "This freezes a subscription-generated research candidate; it cannot emit a signal "
            "or allocate capital."
        ),
    }
    body["run_id"] = f"{body['experiment_id']}:{stable_sha256(body)[:20]}"
    result = {**body, "run_sha256": stable_sha256(body)}
    _validated_run(result)
    return result


__all__ = [
    "COMPANY_STATE_NEWTON_CANDIDATE_FREEZE_SCHEMA",
    "freeze_company_state_newton_successor",
]
