from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ztare.common.control_state_machine import (
    ControlMorphism,
    control_receipt_rows,
    executed_morphism_ids_from_receipts,
)
from ztare.common.leaf_workbench_contract import (
    leaf_workbench_action_request_object,
    render_leaf_workbench_control_rules,
)
from ztare.common.patch_base_identity import resolve_repair_frontier
from ztare.common.retry_prompt_assembly import (
    candidate_memory_refs_for_retry,
    packed_control_receipts,
    render_retry_pack_lines,
)
from ztare.common.science_output_policy import SCIENCE_OUTPUT_POLICY
from ztare.common.sealed_boundary_cegar import (
    boundary_cegar_candidate_delta_lowerability,
    boundary_cegar_refutation_scopes,
    render_boundary_cegar_retry_surface,
)
from ztare.common.strategy_card_roles import (
    META_HARDENING_LANE,
    SKILL_ACQUISITION_LANE,
    strategy_card_blocks_context,
    strategy_card_role,
)
from ztare.orchestrator.retry_contract import (
    RetryContractSurface,
    render_retry_contract_surface,
)
from ztare.validator.core.strategy_card_gate import admissible_no_attempt_blocker_kinds
from ztare.worldmodel.patch_carrier_contract import (
    patch_base_declaration,
    patch_carrier_brief_line,
    patch_delta_signature,
)


_CANDIDATE_BOUND_RECEIPT_RE = re.compile(
    r"candidate-bearing\s+receipt\s+`([^`]+)`"
)


def _patch_base_context_for_retry(
    project_dir: str | Path | None,
    *,
    max_chars: int = 30000,
) -> str:
    """Attach the authoritative patch-base reference for retry composition."""
    if project_dir is None:
        return ""
    project = Path(project_dir)
    best: dict[str, Any] = {}
    source_ref = ""
    sha = ""
    try:
        regression_payload = json.loads(
            (project / "workspace" / "latest_patch_base_regression.json").read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        regression_payload = {}
    regression = (
        regression_payload.get("candidate_regression_receipt")
        if isinstance(regression_payload, dict)
        else None
    )
    if isinstance(regression, dict):
        try:
            resolved = resolve_repair_frontier(project, regression)
            source_ref = resolved["source_ref"]
            sha = resolved["sha256"]
            best = {
                "visible_exact_rows": regression.get(
                    "best_prior_exact_rows"
                    if resolved["role"] == "best_admissible_prior"
                    else "candidate_exact_rows"
                ),
                "visible_checked_rows": (
                    (regression_payload.get("counterexample_trace") or {}).get("checked_rows")
                ),
            }
        except (OSError, ValueError):
            source_ref = ""
    if not source_ref:
        try:
            payload = json.loads(
                (project / "workspace" / "candidate_memory.json").read_text(
                    encoding="utf-8",
                )
            )
        except Exception:
            return ""
        records = [
            rec
            for rec in (payload.get("records") or [])
            if isinstance(rec, dict)
            and str(rec.get("submission") or "").strip().startswith(
                "workspace/submissions/"
            )
        ] if isinstance(payload, dict) else []
        if not records:
            return ""

        def _rank(rec: dict[str, Any]) -> tuple[int, int, int, float, int]:
            return (
                1 if rec.get("source_type") == "full_survivor" else 0,
                int(rec.get("visible_exact_rows") or 0),
                int(rec.get("holdout_depth") or 0),
                float(rec.get("gate_score") or 0.0),
                -int(rec.get("visible_wrong_cells") or 0),
            )

        best = max(records, key=_rank)
        refs = candidate_memory_refs_for_retry(project)
        source_ref = refs[0] if refs else str(best.get("submission") or "").strip()
        source_path = (project / source_ref).resolve()
        if not source_path.exists() or not source_path.is_file():
            return ""
        sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    patch_base_decl = patch_base_declaration(source_ref, sha)
    return (
        "\nAUTHORITATIVE PATCH BASE REFERENCE (compose by hash; do not copy "
        "or reconstruct the carrier source):\n"
        f"- patch_base_ref: {source_ref}\n"
        f"- patch_base_sha: {sha}\n"
        f"- visible_exact_rows: {best.get('visible_exact_rows')}/{best.get('visible_checked_rows')}\n"
        "- use this exact declaration in `test_model_py`, then define only "
        f"the minimal `{patch_delta_signature()}`:\n"
        f"  `{patch_base_decl}`\n"
    )


def _counterexample_context_for_retry(project_dir: str | Path | None) -> str:
    """Return compact context from the latest producer-issued quotient receipt."""
    if project_dir is None:
        return ""
    try:
        from ztare.worldmodel.leaf_workbench import (
            run_worldmodel_counterexample_context_probe,
        )

        summary = run_worldmodel_counterexample_context_probe(project_dir)
    except Exception:
        return ""
    if not summary.strip():
        return ""
    compact = _compressed_counterexample_context_payload(summary)
    rendered = (
        json.dumps(compact, sort_keys=True, separators=(",", ":"), default=str)
        if compact
        else summary.strip()
    )
    return (
        "\nFRESH COUNTEREXAMPLE CONTEXT (from latest patch-base regression receipt; "
        "use as typed evidence, not as authority over the gate):\n"
        f"{rendered}\n\n"
    )


def _latest_workbench_task_morphism(
    project_dir: str | Path | None,
    *,
    executed_caps: list[str] | None = None,
    allow_candidate_rebind: bool = False,
    allow_input_rebind_caps: set[str] | None = None,
) -> ControlMorphism | None:
    """Return the next workbench action named by the latest weakness receipt."""
    if project_dir is None:
        return None
    try:
        payload = json.loads(
            (Path(project_dir) / "workspace" / "latest_harness_weakness.json").read_text(
                encoding="utf-8",
            )
        )
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    task = payload.get("workbench_task")
    task = task if isinstance(task, dict) else {}
    caps = task.get("morphism_sequence") or task.get("admissible_capability_ids")
    if not isinstance(caps, list):
        caps = []
    recommended = str(payload.get("recommended_capability_id") or "").strip()
    ordered = [str(cap).strip() for cap in caps if str(cap).strip()]
    if recommended and recommended not in ordered:
        ordered.insert(0, recommended)
    executed = set(executed_caps or [])
    allow_input_rebind_caps = allow_input_rebind_caps or set()
    cap = next(
        (
            row
            for row in ordered
            if row and (
                row not in executed
                or (allow_candidate_rebind and row == "run_strategy_required_gate")
                or row in allow_input_rebind_caps
            )
        ),
        "",
    )
    if not cap:
        return None
    artifacts = [
        str(ref)
        for ref in (task.get("visible_artifact_refs") or [])
        if str(ref).strip()
    ]
    input_refs = _workbench_input_refs_for_capability(cap, artifacts, project_dir=project_dir)
    return ControlMorphism(
        capability_id=cap,
        input_refs=input_refs,
        claim_bindings=[
            str(task.get("objective") or payload.get("recommended_route") or cap).strip()
            or cap
        ],
    )


def _open_strategy_receipt_morphism(
    project_dir: str | Path | None,
    *,
    executed_caps: list[str] | None = None,
    allow_input_rebind_caps: set[str] | None = None,
) -> ControlMorphism | None:
    """Return a producer-receipt diagnostic selected by an open Strategy card."""

    if project_dir is None:
        return None
    cap = "mine_worldmodel_global_carrier_selectors_from_observable_context"
    executed = set(executed_caps or [])
    allow_input_rebind_caps = allow_input_rebind_caps or set()
    if cap in executed and cap not in allow_input_rebind_caps:
        return None
    project = Path(project_dir)
    if not (project / "workspace" / "latest_level_transfer_probe.json").exists():
        return None
    try:
        from ztare.common.strategy_card_roles import active_strategy_cards

        cards = active_strategy_cards(
            project / "workspace" / "strategy_experiments.jsonl"
        )
    except Exception:  # noqa: BLE001
        return None
    for card in cards:
        if not isinstance(card, dict):
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        if str(plan.get("source_receipt") or "") != "workspace/latest_level_transfer_probe.json":
            continue
        return ControlMorphism(
            capability_id=cap,
            input_refs={
                "strategy_gate_receipt_ref": "workspace/latest_level_transfer_probe.json",
                "source_card_sha": str(card.get("failure_family_sha") or ""),
            },
            claim_bindings=[
                "mine lowerable carrier selectors for the open Strategy repair residue",
            ],
        )
    return None


def _workbench_input_refs_for_capability(
    capability_id: str,
    artifact_refs: list[str],
    *,
    project_dir: str | Path | None = None,
) -> dict[str, Any]:
    from ztare.worldmodel.leaf_workbench import (
        worldmodel_workbench_input_refs_for_capability,
    )

    return worldmodel_workbench_input_refs_for_capability(
        capability_id,
        artifact_refs,
        project_dir=project_dir,
    )


def _candidate_bound_capability_from_r1_error(r1_error: str) -> str:
    text = str(r1_error or "")
    if "LEAF_WORKBENCH_RECEIPT_PROVENANCE_PRECHECK" not in text:
        return ""
    match = _CANDIDATE_BOUND_RECEIPT_RE.search(text)
    if not match:
        return ""
    return str(match.group(1) or "").strip()


def _candidate_bound_retry_morphism(capability_id: str) -> ControlMorphism:
    return ControlMorphism(
        capability_id=capability_id,
        input_refs=_workbench_input_refs_for_capability(capability_id, []),
        claim_bindings=[f"bind {capability_id} to current candidate"],
    )


def _current_artifact_hashes(
    project_dir: str | Path | None,
    artifact_refs: list[str],
) -> dict[str, str]:
    if project_dir is None:
        return {}
    project = Path(project_dir)
    hashes: dict[str, str] = {}
    for ref in artifact_refs:
        ref = str(ref or "").strip()
        if not ref or ":" in ref:
            continue
        path = project / ref
        try:
            if path.is_file():
                hashes[ref] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
    return hashes


def _workbench_receipt_artifact_hashes(
    retry_state_text: str,
    *,
    capability_id: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in _workbench_receipt_rows_for_retry(retry_state_text):
        payload = row.get("payload") if isinstance(row, dict) else None
        if not isinstance(payload, dict):
            continue
        if str(payload.get("capability_id") or "").strip() != capability_id:
            continue
        input_hashes = payload.get("input_hashes")
        if not isinstance(input_hashes, dict):
            continue
        artifact_hashes = input_hashes.get("artifact_hashes")
        if not isinstance(artifact_hashes, dict):
            continue
        normalized = {
            str(ref): str(digest)
            for ref, digest in artifact_hashes.items()
            if str(ref).strip() and str(digest).strip()
        }
        if normalized:
            rows.append(normalized)
    return rows


def _workbench_inputs_changed_since_receipt(
    project_dir: str | Path | None,
    retry_state_text: str,
    *,
    capability_id: str,
    artifact_refs: list[str],
) -> bool:
    current = _current_artifact_hashes(project_dir, artifact_refs)
    if not current:
        return False
    prior_rows = _workbench_receipt_artifact_hashes(
        retry_state_text,
        capability_id=capability_id,
    )
    if not prior_rows:
        return False
    for prior in prior_rows:
        for ref, digest in current.items():
            if prior.get(ref) != digest:
                return True
    return False


def _ready_receipts_json_for_retry(
    retry_state_text: str,
    *,
    exclude_candidate_bound_capability: str = "",
) -> str:
    rows = _workbench_receipt_rows_for_retry(retry_state_text)
    if exclude_candidate_bound_capability:
        rows = [
            row
            for row in rows
            if not (
                isinstance(row.get("payload"), dict)
                and str(row["payload"].get("capability_id") or "").strip()
                == exclude_candidate_bound_capability
            )
        ]
    return json.dumps(rows, sort_keys=True, separators=(",", ":"), default=str) if rows else ""


def _workbench_receipt_rows_for_retry(retry_state_text: str) -> list[dict[str, Any]]:
    return [
        row for row in control_receipt_rows(retry_state_text or "")
        if str(row.get("type") or "") in {"LEAF_WORKBENCH_RECEIPT", "VISIBLE_WORKBENCH_DIAGNOSTIC"}
    ]


def _ready_receipt_facts_for_retry(
    retry_state_text: str,
    *,
    exclude_candidate_bound_capability: str = "",
    max_predicates: int = 4,
    project_dir: str | Path | None = None,
) -> str:
    rows = _workbench_receipt_rows_for_retry(retry_state_text)
    facts: list[dict[str, object]] = []
    for row in rows:
        payload = row.get("payload") if isinstance(row, dict) else None
        if not isinstance(payload, dict):
            continue
        cap = str(payload.get("capability_id") or "").strip()
        if exclude_candidate_bound_capability and cap == exclude_candidate_bound_capability:
            continue
        input_hashes = payload.get("input_hashes") if isinstance(payload.get("input_hashes"), dict) else {}
        summary = _parse_jsonish(payload.get("output_summary"))
        fact: dict[str, object] = {
            "capability_id": cap,
            "output_ref": payload.get("output_ref") or input_hashes.get("receipt_ref") or "",
            "kernel_receipt_ref": input_hashes.get("kernel_receipt_ref") or "",
            "source_ref": (
                input_hashes.get("strategy_gate_receipt_ref")
                or input_hashes.get("source_ref")
                or input_hashes.get("receipt_ref")
                or ""
            ),
        }
        if isinstance(summary, dict):
            for key in (
                "status",
                "command",
                "exact_steps",
                "steps_tested",
                "local_residue_status",
                "local_residue_class_count",
                "lowerability_status",
                "admissibility_scope",
                "candidate_family_id",
                "candidate_family_admissible",
                "candidate_delta_admissible",
                "candidate_label_coverage",
                "forbidden_feature_classes",
                "executable_delta_hint",
                "top_local_residue_class",
            ):
                if key in summary:
                    fact[key] = summary[key]
            if summary.get("schema") == "ztare-counterexample-context-observation-v1":
                behavioral_fiber = summary.get("behavioral_fiber")
                if isinstance(behavioral_fiber, dict):
                    fact["behavioral_fiber"] = _compact_behavioral_fiber(
                        behavioral_fiber
                    )
                chain_effects = summary.get("patch_base_chain_effects")
                if isinstance(chain_effects, dict):
                    fact["patch_base_chain_effects"] = (
                        _compact_patch_base_chain_effects(chain_effects)
                    )
                transports = summary.get("commuting_transports")
                if isinstance(transports, list) and transports:
                    fact["commuting_transports"] = [
                        _compact_commuting_transport(row)
                        for row in transports[:4]
                        if isinstance(row, dict)
                    ]
                observation = summary.get("counterexample_observation")
                observation_sha = str(summary.get("observation_sha256") or "").strip()
                if isinstance(observation, dict) and observation_sha:
                    fact["observation_sha256"] = observation_sha
                    fact["counterexample_observation"] = (
                        _compact_counterexample_observation(observation)
                    )
                    fact["diagnostic_summary"] = str(
                        summary.get("diagnostic_summary") or ""
                    )[:1600]
                event_candidates = summary.get("catalog_residual_event_candidates")
                if isinstance(event_candidates, list) and event_candidates:
                    fact["catalog_residual_event_candidates"] = [
                        compact_catalog_residual_event_candidate(row)
                        for row in event_candidates[:2]
                        if isinstance(row, dict)
                    ]
            predicates = summary.get("candidate_predicates")
            if isinstance(predicates, list) and predicates:
                fact["candidate_predicates"] = predicates[:max_predicates]
            near = summary.get("near_miss_predicates")
            if isinstance(near, list) and near:
                fact["near_miss_predicates"] = near[:2]
        else:
            text = str(payload.get("output_summary") or "").strip()
            if text:
                fact["output_summary"] = text[:900]
        facts.append({k: v for k, v in fact.items() if v not in ("", None, [], {})})
    if not facts:
        return ""
    return (
        "CARRIED RECEIPT FACTS (compressed; not receipt objects to copy):\n"
        + json.dumps(facts, sort_keys=True, separators=(",", ":"), default=str)
        + "\n\n"
    )


def _parse_jsonish(value: object) -> object | None:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return json.loads(value, strict=False)
    except json.JSONDecodeError:
        return None


def _compact_commuting_transport(transport: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "schema",
        "authority",
        "source_row",
        "target_row",
        "intervention",
        "time_translation",
        "lifecycle_compatibility",
        "operation",
        "source_operation",
        "consequence_operation",
        "transport_kind",
        "observed_relation",
        "operation_identity_sha256",
        "exact_lowering_variants",
        "source_exact_lowering_variants",
        "consequence_exact_lowering_variants",
        "component_selector_presentations",
        "component_identity_status",
        "observed_commutation",
        "global_equivariance_authorized",
        "quotient_authorized",
        "carrier_promotion_authorized",
        "square_identity_sha256",
    )
    return {
        key: transport[key]
        for key in keep
        if key in transport
    }


def _compact_behavioral_fiber(fiber: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "schema",
        "authority",
        "representative_row",
        "intervention",
        "law_coordinate",
        "member_count",
        "member_rows",
        "distinct_source_states",
        "shared_observed_consequence_sha256",
        "observed_relation",
        "equality_contract",
        "global_equivariance_authorized",
        "quotient_authorized",
        "carrier_promotion_authorized",
        "distinguishing_obligation",
        "fiber_identity_sha256",
    )
    compact = {key: fiber[key] for key in keep if key in fiber}
    members = fiber.get("members")
    if isinstance(members, list):
        member_keys = (
            "row",
            "representative",
            "source_state_sha256",
            "source_operations_to_representative",
            "component_selector_presentations",
        )
        compact["members"] = [
            {key: member[key] for key in member_keys if key in member}
            for member in members[:16]
            if isinstance(member, dict)
        ]
    return compact


def _compact_patch_base_chain_effects(
    effects: dict[str, Any],
) -> dict[str, Any]:
    """Preserve layer consequences while dropping prediction fingerprints."""

    keep = (
        "schema",
        "authority",
        "frontier_role",
        "frontier_sha256",
        "behavioral_fiber_identity_sha256",
        "member_rows",
        "chain_order",
        "layer_count",
        "additive_layer_count",
        "distinct_rows_added_across_layers",
        "observed_chain_relation",
        "global_operation_identity_authorized",
        "carrier_promotion_authorized",
        "chain_effect_identity_sha256",
    )
    compact = {key: effects[key] for key in keep if key in effects}
    layers = effects.get("layers")
    if isinstance(layers, list):
        layer_keys = (
            "depth_from_root",
            "carrier_ref",
            "carrier_sha256",
            "correct_member_rows",
            "wrong_member_rows",
            "added_correct_member_rows",
            "lost_correct_member_rows",
            "evaluation_error_rows",
            "observed_delta_relation",
        )
        compact["layers"] = [
            {key: layer[key] for key in layer_keys if key in layer}
            for layer in layers[:16]
            if isinstance(layer, dict)
        ]
    return compact


def _compact_counterexample_observation(
    observation: dict[str, Any],
    *,
    max_residual_runs: int = 128,
) -> dict[str, Any]:
    """Lower a chart packet to its identity plus program-readable residual."""
    objects = observation.get("objects") if isinstance(observation.get("objects"), dict) else {}

    def windows(kind: str) -> dict[tuple[int, int, int, int], list[list[Any]]]:
        projected = objects.get(kind) if isinstance(objects.get(kind), dict) else {}
        rows = projected.get("windows") if isinstance(projected.get("windows"), list) else []
        out: dict[tuple[int, int, int, int], list[list[Any]]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            bbox = row.get("bbox")
            values = row.get("values")
            if not isinstance(bbox, list) or len(bbox) != 4 or not isinstance(values, list):
                continue
            try:
                key = tuple(int(value) for value in bbox)
            except (TypeError, ValueError):
                continue
            out[key] = values
        return out

    source = windows("source_observation")
    proposed = windows("proposed_consequence")
    observed = windows("observed_consequence")
    triples_by_coordinate: dict[tuple[int, int], dict[str, Any]] = {}
    overlap_conflicts: list[dict[str, Any]] = []
    for bbox, pred_values in proposed.items():
        obs_values = observed.get(bbox)
        if obs_values is None:
            continue
        source_values = source.get(bbox) or []
        r0, c0, _r1, _c1 = bbox
        for rr in range(min(len(pred_values), len(obs_values))):
            pred_row = pred_values[rr]
            obs_row = obs_values[rr]
            if not isinstance(pred_row, list) or not isinstance(obs_row, list):
                continue
            for cc in range(min(len(pred_row), len(obs_row))):
                source_value = None
                if rr < len(source_values) and isinstance(source_values[rr], list):
                    if cc < len(source_values[rr]):
                        source_value = source_values[rr][cc]
                triple = {
                    "coordinate": [r0 + rr, c0 + cc],
                    "source": source_value,
                    "proposed": pred_row[cc],
                    "observed": obs_row[cc],
                }
                coordinate = (r0 + rr, c0 + cc)
                prior = triples_by_coordinate.get(coordinate)
                if prior is None:
                    triples_by_coordinate[coordinate] = triple
                elif any(
                    prior[key] != triple[key]
                    for key in ("source", "proposed", "observed")
                ):
                    overlap_conflicts.append(
                        {
                            "coordinate": list(coordinate),
                            "first": {
                                key: prior[key]
                                for key in ("source", "proposed", "observed")
                            },
                            "second": {
                                key: triple[key]
                                for key in ("source", "proposed", "observed")
                            },
                        }
                    )

    triples = list(triples_by_coordinate.values())

    def relation_runs(
        rows: list[dict[str, Any]],
        value_keys: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        for row in sorted(rows, key=lambda item: tuple(item["coordinate"])):
            rr, cc = row["coordinate"]
            values = tuple(row[key] for key in value_keys)
            if runs:
                prior = runs[-1]
                prior_values = tuple(prior[key] for key in value_keys)
                if (
                    prior["row"] == rr
                    and prior["col_end"] + 1 == cc
                    and prior_values == values
                ):
                    prior["col_end"] = cc
                    continue
            runs.append(
                {
                    "row": rr,
                    "col_start": cc,
                    "col_end": cc,
                    **{key: row[key] for key in value_keys},
                }
            )
        return runs

    residual_rows = [
        row for row in triples if row["proposed"] != row["observed"]
    ]
    state_change_rows = [
        row
        for row in triples
        if row["source"] is not None and row["source"] != row["observed"]
    ]
    residual_runs = relation_runs(
        residual_rows,
        ("source", "proposed", "observed"),
    )
    state_change_runs = relation_runs(
        state_change_rows,
        ("source", "observed"),
    )
    chart = observation.get("observation_chart")
    chart = chart if isinstance(chart, dict) else {}
    compact = {
        "schema": observation.get("schema"),
        "observation_ref": observation.get("observation_ref"),
        "proposal_identity": observation.get("proposal_identity"),
        "intervention": observation.get("intervention"),
        "transition_identity": observation.get("transition_identity"),
        "observation_chart": {
            key: chart.get(key)
            for key in ("chart_id", "chart_version", "packet_schema_id", "authority")
            if chart.get(key) is not None
        },
        "residual_runs": residual_runs[:max_residual_runs],
        "residual_cell_count": len(residual_rows),
        "residual_run_count": len(residual_runs),
        "residual_truncated": len(residual_runs) > max_residual_runs,
        "state_change_runs": state_change_runs[:max_residual_runs],
        "state_change_cell_count": len(state_change_rows),
        "state_change_run_count": len(state_change_runs),
        "state_change_truncated": len(state_change_runs) > max_residual_runs,
        "chart_overlap_conflicts": overlap_conflicts[:8],
        "chart_overlap_conflict_count": len(overlap_conflicts),
    }
    return {key: value for key, value in compact.items() if value not in (None, "", [], {})}


def _compressed_counterexample_context_payload(value: object) -> dict[str, Any]:
    summary = _parse_jsonish(value)
    if not isinstance(summary, dict):
        return {}
    out: dict[str, Any] = {
        "schema": summary.get("schema"),
        "diagnostic_summary": str(summary.get("diagnostic_summary") or "")[:1800],
    }
    observation_sha = str(summary.get("observation_sha256") or "").strip()
    observation = summary.get("counterexample_observation")
    if observation_sha:
        out["observation_sha256"] = observation_sha
    if isinstance(observation, dict):
        out["counterexample_observation"] = _compact_counterexample_observation(
            observation
        )
    event_candidates = summary.get("catalog_residual_event_candidates")
    if isinstance(event_candidates, list) and event_candidates:
        out["catalog_residual_event_candidates"] = [
            compact_catalog_residual_event_candidate(row)
            for row in event_candidates[:2]
            if isinstance(row, dict)
        ]
    behavioral_fiber = summary.get("behavioral_fiber")
    if isinstance(behavioral_fiber, dict):
        out["behavioral_fiber"] = _compact_behavioral_fiber(behavioral_fiber)
    transports = summary.get("commuting_transports")
    if isinstance(transports, list) and transports:
        out["commuting_transports"] = [
            _compact_commuting_transport(row)
            for row in transports[:4]
            if isinstance(row, dict)
        ]
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def compact_catalog_residual_event_candidate(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Keep operation identity and executable lowering without raw-grid bulk."""
    lowering = candidate.get("lowering")
    lowering = lowering if isinstance(lowering, dict) else {}
    writes = lowering.get("writes") if isinstance(lowering.get("writes"), list) else []
    compact_writes = []
    for value, coordinates in writes:
        if not isinstance(coordinates, list):
            continue
        by_row: dict[int, list[int]] = {}
        for coordinate in coordinates:
            if not isinstance(coordinate, (list, tuple)) or len(coordinate) != 2:
                continue
            by_row.setdefault(int(coordinate[0]), []).append(int(coordinate[1]))
        runs = []
        for row, columns in sorted(by_row.items()):
            columns = sorted(set(columns))
            if not columns:
                continue
            start = end = columns[0]
            for column in columns[1:]:
                if column == end + 1:
                    end = column
                else:
                    runs.append([row, start, end])
                    start = end = column
            runs.append([row, start, end])
        compact_writes.append({"value": value, "row_col_runs": runs})
    return {
        "schema": candidate.get("schema"),
        "authority": candidate.get("authority"),
        "operation_identity": candidate.get("operation_identity"),
        "operation_identity_sha256": candidate.get("operation_identity_sha256"),
        "role_evidence": candidate.get("role_evidence"),
        "boundary_evidence": candidate.get("boundary_evidence"),
        "identity_status": candidate.get("identity_status"),
        "lowering": {
            key: lowering.get(key)
            for key in ("op", "mover_colors", "rect", "edge")
            if lowering.get(key) is not None
        }
        | {"writes": compact_writes},
        "lowering_sha256": candidate.get("lowering_sha256"),
        "promotion_authorized": candidate.get("promotion_authorized"),
    }


def _commuting_transports_from_receipts(
    retry_state_text: str,
) -> list[dict[str, Any]]:
    """Read finite transport witnesses already delivered to candidate synthesis."""
    found: list[dict[str, Any]] = []
    for row in _workbench_receipt_rows_for_retry(retry_state_text):
        payload = row.get("payload") if isinstance(row, dict) else None
        if not isinstance(payload, dict):
            continue
        if str(payload.get("capability_id") or "") != "inspect_worldmodel_counterexample_context":
            continue
        summary = _parse_jsonish(payload.get("output_summary"))
        if not isinstance(summary, dict):
            continue
        transports = summary.get("commuting_transports")
        if not isinstance(transports, list):
            continue
        found.extend(
            transport
            for transport in transports
            if isinstance(transport, dict)
            and transport.get("observed_commutation") is True
            and transport.get("authority") == "diagnostic_finite_witness"
        )
    return found


def _outstanding_obligation_context_for_retry(
    project_dir: str | Path | None,
    *,
    max_cards: int = 4,
    action_request_already_executed: bool = False,
    suppress_action_request_skeleton: bool = False,
) -> str:
    """Return compact obligations that must survive every same-iter retry.

    R1 fixes are local compiler/contract repairs. They must not erase other
    open control obligations from the payload while fixing the latest error.
    This function is a substrate adapter surface: today it harvests Strategy
    Office cards from the standard ledger, and future substrates can add their
    own typed obligation rows here without changing the retry loop.
    """
    if project_dir is None:
        return ""
    project = Path(project_dir)
    try:
        from ztare.common.strategy_card_roles import active_strategy_cards

        cards = active_strategy_cards(
            project / "workspace" / "strategy_experiments.jsonl"
        )
    except Exception:
        cards = []
    if not cards:
        return ""
    skill_cards = [card for card in cards if strategy_card_blocks_context(card)]
    meta_cards = [card for card in cards if strategy_card_role(card).lane == META_HARDENING_LANE]
    lines = [
        "OPEN STRATEGY CARD REFS:",
        "- Skill-acquisition cards are active evidence refs and gateable obligations.",
        "- Meta-hardening cards are queued apparatus work; do not let them block an executable candidate unless this task is explicitly meta-hardening.",
        "- If the retry is a control move, discharge/block each listed skill-acquisition card with STRATEGY_CARD_DISCHARGE.",
        "- If the retry submits executable code, cite the relevant card refs in thesis_markdown; gates still decide.",
    ]
    for card in skill_cards[:max_cards]:
        if not isinstance(card, dict):
            continue
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
        residue = plan.get("residue_quotient") if isinstance(plan.get("residue_quotient"), dict) else {}
        seed = plan.get("seed_prerequisite") if isinstance(plan.get("seed_prerequisite"), dict) else {}
        sha = str(card.get("failure_family_sha") or "").strip()
        kind = str(card.get("kind") or "").strip()
        no_attempt = admissible_no_attempt_blocker_kinds(card)
        lines.append(
            "- "
            + json.dumps(
                {
                    "failure_family_sha": sha,
                    "kind": kind,
                    "lane": SKILL_ACQUISITION_LANE,
                    "residue": residue.get("residue_class") or "",
                    "seed": seed.get("seed_path") or seed.get("status") or "",
                    "next_gate": {
                        "command": gate.get("command") or "",
                        "success_status": gate.get("success_status") or "",
                    },
                    "admissible_no_attempt_blockers": no_attempt,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        if (
            sha
            and gate.get("command")
            and not action_request_already_executed
            and not suppress_action_request_skeleton
        ):
            request = leaf_workbench_action_request_object(
                capability_id="run_strategy_required_gate",
                input_refs={
                    "failure_family_sha": sha,
                    "command": gate.get("command"),
                    "candidate_path": "test_model.py",
                },
                claim_bindings=[f"run required Strategy gate {gate.get('command')}"],
            )
            lines.append(
                "- optional action_request skeleton when the declared gate is the next "
                "needed discriminator: "
                + json.dumps(request, sort_keys=True, separators=(",", ":"), default=str)
            )
    if meta_cards:
        lines.append("- queued_meta_hardening_cards:")
        for card in meta_cards[: max(1, max_cards - len(skill_cards[:max_cards]))]:
            if not isinstance(card, dict):
                continue
            plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
            gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
            lines.append(
                "- "
                + json.dumps(
                    {
                        "failure_family_sha": str(card.get("failure_family_sha") or "").strip(),
                        "kind": str(card.get("kind") or "").strip(),
                        "lane": META_HARDENING_LANE,
                        "target_artifact": plan.get("target_artifact") or "",
                        "next_gate": {
                            "command": gate.get("command") or "",
                            "success_status": gate.get("success_status") or "",
                        },
                        "candidate_blocking": False,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
    return "\n".join(lines) + "\n\n"


def _compact_worldmodel_r1_error(text: str, *, limit: int = 900) -> str:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return ""
    receipt_idx = cleaned.find("LEAF_WORKBENCH_RECEIPT:")
    if receipt_idx >= 0:
        cleaned = cleaned[:receipt_idx].rstrip() + " [receipt objects elided; use compact receipt facts/artifact refs below]"
    if len(cleaned) > limit:
        cleaned = cleaned[:limit].rstrip() + "..."
    return cleaned


def _compact_worldmodel_prior_submission(text: str, *, max_code_chars: int = 6000) -> str:
    raw = str(text or "").strip()
    if not raw:
        return "<empty prior submission>"
    try:
        payload = json.loads(raw)
    except Exception:
        payload = None
    if isinstance(payload, dict):
        code = ""
        for key in ("test_model_py", "python_code", "code", "source"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                code = value
                break
        thesis = payload.get("thesis_markdown")
        receipts = payload.get("control_receipts")
        lines = [
            "prior_payload_summary:",
            f"- control_receipts_count: {len(receipts) if isinstance(receipts, list) else 0}",
        ]
        if isinstance(thesis, str) and thesis.strip():
            excerpt = " ".join(thesis.split())[:1000]
            lines.append(f"- thesis_excerpt: {excerpt}")
        if code.strip():
            lines.append("- test_model_py_excerpt:")
            lines.append("```python")
            lines.append(code[:max_code_chars])
            lines.append("```")
        else:
            lines.append("- test_model_py_excerpt: <empty>")
        return "\n".join(lines)
    if len(raw) > max_code_chars:
        return raw[:max_code_chars].rstrip() + "\n...[prior submission elided]"
    return raw


def format_worldmodel_retry_skeleton(
    r1_error: str,
    prior_content: str,
    *,
    max_prior_chars: int,
    retry_error_history: list[str] | None = None,
    project_dir: str | Path | None = None,
) -> str:
    retry_state_text = "\n".join(
        [str(r1_error or "")]
        + [str(row or "") for row in (retry_error_history or [])]
    )
    action_request_already_executed = (
        "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK: executed" in retry_state_text
    )
    current_candidate_bound_capability = _candidate_bound_capability_from_r1_error(
        r1_error or ""
    )
    current_requests_counterexample_context = (
        "`inspect_worldmodel_counterexample_context`" in (r1_error or "")
    )
    current_requests_visible_probe = "`run_visible_json_probe`" in (r1_error or "")
    named_current_morphism = (
        current_candidate_bound_capability
        or ("inspect_worldmodel_counterexample_context" if current_requests_counterexample_context else "")
        or ("run_visible_json_probe" if current_requests_visible_probe else "")
    )
    initial_next_morphism: ControlMorphism | None = None
    if not action_request_already_executed and not current_candidate_bound_capability:
        initial_next_morphism = _latest_workbench_task_morphism(
            project_dir,
            executed_caps=[],
        )
        if not named_current_morphism and initial_next_morphism is not None:
            named_current_morphism = initial_next_morphism.capability_id
    candidate_binding_refresh = (
        "predates content-addressed candidate binding" in (r1_error or "")
    )
    no_delta_no_improvement = _is_no_delta_patch_base_no_improvement(r1_error or "")
    patch_base_context = (
        _patch_base_context_for_retry(project_dir)
        if (
            not no_delta_no_improvement
            and (
                "PATCH_BASE_REGRESSION_PRECHECK" in (r1_error or "")
                or "PATCH_BASE_IMPROVEMENT_PRECHECK" in (r1_error or "")
            )
        )
        else ""
    )
    counterexample_context = (
        _counterexample_context_for_retry(project_dir)
        if (
            "PATCH_BASE_IMPROVEMENT_PRECHECK" in (r1_error or "")
            and not no_delta_no_improvement
        )
        else ""
    )
    obligation_context = _outstanding_obligation_context_for_retry(
        project_dir,
        action_request_already_executed=action_request_already_executed,
        suppress_action_request_skeleton=(
            bool(named_current_morphism)
            and named_current_morphism != "run_strategy_required_gate"
        ),
    )
    action_request_section = ""
    executed_caps: list[str] = []
    input_rebind_caps: set[str] = set()
    candidate_delta_lowerability: bool | None = None
    suppress_candidate_carrier_surface = False
    commuting_transports: list[dict[str, Any]] = []
    if action_request_already_executed:
        ready_receipts = _ready_receipts_json_for_retry(
            retry_state_text,
            exclude_candidate_bound_capability=(
                current_candidate_bound_capability
                if candidate_binding_refresh
                else ""
            ),
        )
        ready_receipt_facts_section = _ready_receipt_facts_for_retry(
            retry_state_text,
            exclude_candidate_bound_capability=(
                current_candidate_bound_capability
                if candidate_binding_refresh
                else ""
            ),
            project_dir=project_dir,
        )
        executed_caps = executed_morphism_ids_from_receipts(retry_state_text)
        commuting_transports = _commuting_transports_from_receipts(retry_state_text)
        if _workbench_inputs_changed_since_receipt(
            project_dir,
            retry_state_text,
            capability_id="run_visible_json_probe",
            artifact_refs=["workspace/latest_patch_base_regression.json"],
        ):
            input_rebind_caps.add("run_visible_json_probe")
        if _workbench_inputs_changed_since_receipt(
            project_dir,
            retry_state_text,
            capability_id="mine_worldmodel_lowerable_selectors",
            artifact_refs=["workspace/latest_patch_base_regression.json"],
        ):
            input_rebind_caps.add("mine_worldmodel_lowerable_selectors")
        if _workbench_inputs_changed_since_receipt(
            project_dir,
            retry_state_text,
            capability_id="mine_worldmodel_global_carrier_selectors_from_observable_context",
            artifact_refs=["workspace/latest_level_transfer_probe.json"],
        ):
            input_rebind_caps.add("mine_worldmodel_global_carrier_selectors_from_observable_context")
        if _workbench_inputs_changed_since_receipt(
            project_dir,
            retry_state_text,
            capability_id="cell_local_lowerable_carrier_selector_miner",
            artifact_refs=["workspace/latest_level_transfer_probe.json"],
        ):
            input_rebind_caps.add("cell_local_lowerable_carrier_selector_miner")
        candidate_delta_lowerability = boundary_cegar_candidate_delta_lowerability(
            ready_receipts
        )
        refuted_scopes = boundary_cegar_refutation_scopes(ready_receipts)
        selector_family_refuted = any(
            row.get("scope_kind") == "candidate_family" for row in refuted_scopes
        )
        needs_lowerable_selector = (
            not commuting_transports
            and "inspect_worldmodel_counterexample_context" in executed_caps
            and (
                "mine_worldmodel_lowerable_selectors" not in executed_caps
                or "mine_worldmodel_lowerable_selectors" in input_rebind_caps
            )
        )
        needs_cell_local_selector = (
            "mine_worldmodel_global_carrier_selectors_from_observable_context" in executed_caps
            and (
                "cell_local_lowerable_carrier_selector_miner" not in executed_caps
                or "cell_local_lowerable_carrier_selector_miner" in input_rebind_caps
            )
        )
        if current_candidate_bound_capability:
            action_request_section = render_boundary_cegar_retry_surface(
                state="candidate_binding_open",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    _candidate_bound_retry_morphism(current_candidate_bound_capability)
                ],
            )
        elif (
            current_requests_counterexample_context
            and "inspect_worldmodel_counterexample_context" not in executed_caps
        ):
            action_request_section = render_boundary_cegar_retry_surface(
                state="counterexample_open",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    ControlMorphism(
                        capability_id="inspect_worldmodel_counterexample_context",
                        input_refs=_workbench_input_refs_for_capability(
                            "inspect_worldmodel_counterexample_context",
                            [],
                            project_dir=project_dir,
                        ),
                        claim_bindings=["separate latest counterexample quotient by typed context"],
                    )
                ],
            )
        elif needs_lowerable_selector:
            action_request_section = render_boundary_cegar_retry_surface(
                state="observation_receipt_available",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    ControlMorphism(
                        capability_id="mine_worldmodel_lowerable_selectors",
                        input_refs=_workbench_input_refs_for_capability(
                            "mine_worldmodel_lowerable_selectors",
                            ["workspace/latest_patch_base_regression.json"],
                            project_dir=project_dir,
                        ),
                        claim_bindings=[
                            "try to lower the chart-only counterexample separator into a visible carrier selector",
                        ],
                    )
                ],
            )
        elif needs_cell_local_selector:
            action_request_section = render_boundary_cegar_retry_surface(
                state="observation_receipt_available",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    ControlMorphism(
                        capability_id="cell_local_lowerable_carrier_selector_miner",
                        input_refs={
                            "strategy_gate_receipt_ref": "workspace/latest_level_transfer_probe.json",
                        },
                        claim_bindings=[
                            "refine the no-lowerable selector receipt with per-cell component topology",
                        ],
                    )
                ],
            )
        elif not commuting_transports and selector_family_refuted and (
            "mine_worldmodel_lowerable_selectors" in executed_caps
            or "cell_local_lowerable_carrier_selector_miner" in executed_caps
            or "mine_worldmodel_global_carrier_selectors_from_observable_context" in executed_caps
        ):
            action_request_section = render_boundary_cegar_retry_surface(
                state="observation_receipt_available",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=None,
            )
        elif candidate_delta_lowerability is True:
            action_request_section = render_boundary_cegar_retry_surface(
                state="observation_receipt_available",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=None,
                no_next_morphism_policy=(
                    "submit a candidate delta that cites the lowerability "
                    "receipt, or block/refute the card with a typed reason."
                ),
            )
        elif current_requests_visible_probe and (
            "run_visible_json_probe" not in executed_caps
            or "run_visible_json_probe" in input_rebind_caps
        ):
            action_request_section = render_boundary_cegar_retry_surface(
                state="counterexample_open",
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[
                    ControlMorphism(
                        capability_id="run_visible_json_probe",
                        input_refs={
                            "artifact_refs": ["workspace/latest_patch_base_regression.json"],
                        },
                        claim_bindings=["separate latest counterexample quotient"],
                    )
                ],
            )
        else:
            next_morphism = _latest_workbench_task_morphism(
                project_dir,
                executed_caps=executed_caps,
                allow_candidate_rebind=candidate_binding_refresh,
                allow_input_rebind_caps=input_rebind_caps,
            )
            if (
                commuting_transports
                and next_morphism is not None
                and next_morphism.capability_id in {
                    "mine_worldmodel_separating_features",
                    "mine_worldmodel_lowerable_selectors",
                }
            ):
                next_morphism = None
            next_morphism = (
                _open_strategy_receipt_morphism(
                    project_dir,
                    executed_caps=executed_caps,
                    allow_input_rebind_caps=input_rebind_caps,
                )
                or next_morphism
            )
            action_request_section = render_boundary_cegar_retry_surface(
                state=(
                    "counterexample_open"
                    if candidate_binding_refresh or input_rebind_caps
                    else ("observation_receipt_available" if executed_caps else "counterexample_open")
                ),
                executed_morphisms=executed_caps,
                carried_receipts_json=ready_receipts,
                admissible_next=[next_morphism] if next_morphism is not None else None,
            )
    else:
        ready_receipt_facts_section = ""
        next_morphism = (
            _candidate_bound_retry_morphism(current_candidate_bound_capability)
            if current_candidate_bound_capability
            else (
                _open_strategy_receipt_morphism(project_dir, executed_caps=[])
                or initial_next_morphism
            )
        )
        action_request_section = render_leaf_workbench_control_rules(
            action_request=(
                next_morphism.request_object() if next_morphism is not None else None
            )
        ) + "\n\n"
        if next_morphism is not None:
            action_request_section += render_boundary_cegar_retry_surface(
                state="counterexample_open",
                executed_morphisms=[],
                admissible_next=[next_morphism],
            )
        else:
            action_request_section += (
                "Submit `control_receipts: []` when no workbench action is needed.\n\n"
            )
    if suppress_candidate_carrier_surface:
        patch_base_context = ""
    carrier_guidance_section = (
        "A finite commuting transport through a registered adapter operation is "
        "present in CARRIED RECEIPT FACTS. This closes the automatic selector-search "
        "branch. Candidate synthesis receives the operation witness, unresolved "
        "selector presentations, and authority limits as typed evidence. The witness "
        "grants no global equivariance, quotient, or promotion authority.\n\n"
        if commuting_transports
        else
        "Current receipts do not yet expose a lowerability witness. If visible "
        "evidence still lets you express a transportable law, submit the candidate "
        "and let the gate decide. Otherwise submit LOWERABILITY_BLOCKED with "
        "attempted tools, candidate family, evidence refs, and evidence_statuses. "
        + SCIENCE_OUTPUT_POLICY.tool_gap_text()
        + "\n\n"
        if candidate_delta_lowerability is False
        else (
            SCIENCE_OUTPUT_POLICY.local_stopping_text()
            + "\n\n"
            + (
                "Submit an executable carrier from another hypothesis family when "
                "visible evidence permits, or request another registered observation. "
                "\n\n"
            if suppress_candidate_carrier_surface
            else (
                "If this retry submits a candidate delta, choose the narrowest carrier "
                "that expresses your law:\n"
                "  - Direct executable carrier: define `step(grid, action, t)`, "
                "`PROGRAM = ...`, or another accepted predictor surface.\n"
                "  - Patch-base carrier only when an authoritative patch_base_ref "
                "and full patch_base_sha are shown in this prompt; never invent "
                f"base identity: {patch_carrier_brief_line()}\n"
                "  - Catalog spec only if lowerable: `WORLD_MODEL_SPEC = {\"actions\":{\"0\":[{\"op\":\"identity\"}]}}`\n"
                "  - Sealed grid_dsl AST: `PROGRAM = [...]`\n"
                "Do not include identity fallback code for a control-only move.\n\n"
            )
            )
        )
    )
    control_rules_section = (
        render_leaf_workbench_control_rules()
        + "\n"
        if action_request_already_executed
        else ""
    )
    retry_pack_section = render_retry_pack_lines(
        receipts_text=retry_state_text,
        candidate_memory_refs=(
            candidate_memory_refs_for_retry(project_dir) if project_dir else ()
        ),
        heading="CARRIED RECEIPT FACTS",
    )
    body = (
        "This substrate is evaluated by deterministic grid replay and held-out "
        "rollout. Thesis prose and assertion tests are advisory only. Candidate "
        "submissions need an executable transition carrier. Omit carrier code "
        "only for a registered workbench action request that can add runtime "
        "information or `LOWERABILITY_BLOCKED` carrying evidence that no "
        "gamma-lowerable candidate is currently justified. "
        + SCIENCE_OUTPUT_POLICY.blocker_text()
        + "\n\n"
        f"{SCIENCE_OUTPUT_POLICY.final_contract_text()}\n"
        "Put new Strategy discharges, workbench action requests, tool-gap "
        "observations, or LOWERABILITY_BLOCKED in `control_receipts`. "
        "Kernel-produced observation receipts are not authored by the model; when "
        "compact receipt facts are shown, cite their refs/facts instead of pasting "
        "summaries as new receipts.\n\n"
        f"{retry_pack_section}"
        f"{control_rules_section}"
        f"{action_request_section}"
        f"{ready_receipt_facts_section}"
        f"{carrier_guidance_section}"
        "Rules:\n"
        "  - do not put `control_receipts`, `LEAF_WORKBENCH_RECEIPT`, or "
        "`STRATEGY_CARD_DISCHARGE` inside `test_model_py`\n"
        "  - do not submit only qualitative tests; they cannot satisfy replay/rollout\n"
        "  - do not declare PARAMETRIC_FORM, LAGRANGIAN, MODEL_PARAMS, PARAMETER_NAMES, or INIT_RANGE\n"
        "  - keep imports stdlib-only and keep module import side-effect free\n"
        "  - if proposing a new operator, use EXTENSIONS_SRC plus a PROGRAM that calls it\n\n"
        f"{obligation_context}"
        f"{counterexample_context}"
        f"{patch_base_context}"
    )
    missing_block_note = ""
    try:
        from ztare.fit.mutation_suite_guard import is_missing_block_error as _imb
        if _imb(r1_error or ""):
            missing_block_note = (
                "VIOLATED REQUIREMENT (verbatim): \"Missing required Python "
                "falsification suite block; reject candidate before evaluation.\"\n"
                "Your response MUST carry the complete falsification suite as "
                "runnable Python: either a non-empty `test_model_py` field in the "
                "JSON payload containing the FULL contents of test_model.py, or a "
                "fenced ```python code block with that full suite. Prose, receipts, "
                "or a suite left only in the workbench without either carrier does "
                "not satisfy the extractor.\n\n"
            )
    except Exception:
        pass
    return render_retry_contract_surface(
        RetryContractSurface(
            rejected_subject="ARC/world-model submission",
            scientific_failure_phrase=(
                "rejected by the R1 or pre-judge gate contract"
            ),
            error_text=_compact_worldmodel_r1_error(r1_error),
            error_history=format_retry_error_history(retry_error_history),
            body=missing_block_note + body,
            resubmit_instruction="RESUBMIT THE COMPLETE RAW JSON PAYLOAD.",
            prior_heading="Prior submission summary:",
            prior_content=_compact_worldmodel_prior_submission(
                prior_content,
                max_code_chars=min(max_prior_chars, 5000),
            ),
            prior_mode="summary",
        )
    )


def _ready_worldmodel_control_receipts_json(retry_state_text: str) -> str:
    return packed_control_receipts(retry_state_text)


def _executed_workbench_capabilities(retry_state_text: str) -> list[str]:
    return executed_morphism_ids_from_receipts(retry_state_text)


def _is_no_delta_patch_base_no_improvement(r1_error: str) -> bool:
    text = str(r1_error or "")
    return (
        "PATCH_BASE_IMPROVEMENT_PRECHECK" in text
        and "relation=no_strict_improvement" in text
        and "wrong_cells 0 vs 0" in text
        and "quotient_relation=unclassified" in text
        and "candidate_top={'bbox': []" in text
        and "best_prior_top={'bbox': []" in text
    )


def format_retry_error_history(errors: list[str] | None) -> str:
    if not errors:
        return ""
    cleaned: list[str] = []
    for raw in errors:
        text = " ".join(str(raw or "").split())
        if not text:
            continue
        if cleaned and cleaned[-1] == text:
            continue
        cleaned.append(text)
    if len(cleaned) <= 1:
        return ""
    lines = [
        "Same-iteration R1 strike history:",
    ]
    for idx, err in enumerate(cleaned[-3:], start=max(1, len(cleaned) - 2)):
        tail = _compact_worldmodel_r1_error(err, limit=260)
        lines.append(f"  {idx}. {tail}")
    lines.extend(
        [
            "",
            "The next submission must satisfy the current error without reintroducing",
            "any earlier strike in this list.",
            "",
        ]
    )
    return "\n".join(lines)
