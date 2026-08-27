"""Join source-backed strategy programs to persistent company-state transitions."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .company_state_flow import COMPANY_STATE_FLOW_EVIDENCE_SCHEMA
from .strategy_learning import STRATEGY_MOVE_LIBRARY_SCHEMA


STRATEGY_STATE_TRANSITION_JOIN_SCHEMA = "jaggedthoughts-strategy-state-transition-join-v1"
MIN_FIT_ISSUERS = 8
MIN_UNSEEN_ISSUERS = 8
MIN_PRE_TRANSITIONS = 4
MIN_POST_TRANSITIONS = 2
MIN_TWO_STEP_PATHS = 4


def _two_step_paths(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: (str(row["source_epoch"]), str(row["target_epoch"])))
    paths = []
    for left, right in zip(ordered, ordered[1:]):
        if (
            left["target_epoch"] != right["source_epoch"]
            or left.get("target_state") != right.get("source_state")
        ):
            continue
        body = {
            "entity_id": str(left["entity_id"]),
            "source_epoch": str(left["source_epoch"]),
            "intermediate_epoch": str(left["target_epoch"]),
            "terminal_epoch": str(right["target_epoch"]),
            "source_state": str(left["source_state"]),
            "intermediate_state": str(left["target_state"]),
            "terminal_state": str(right["target_state"]),
            "source_evidence_sha256": str(left.get("source_evidence_sha256") or ""),
            "intermediate_evidence_sha256": str(left.get("target_evidence_sha256") or ""),
            "terminal_evidence_sha256": str(right.get("target_evidence_sha256") or ""),
            "source_refs": sorted(set(map(str, (
                *(left.get("source_refs") or ()), *(right.get("source_refs") or ()),
            )))),
        }
        paths.append({**body, "path_sha256": stable_sha256(body)})
    return paths


def _checked(row: Mapping[str, Any], schema: str, hash_field: str, label: str) -> str:
    if row.get("schema") != schema:
        raise ValueError(f"{label} schema mismatch")
    body = dict(row)
    declared = str(body.pop(hash_field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{label} content hash mismatch")
    return declared


def compile_strategy_state_transition_join(
    flow: Mapping[str, Any], move_library: Mapping[str, Any],
    unexposed_coverage: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Measure point-in-time support before fitting any strategy-conditioned law."""
    flow_sha = _checked(
        flow, COMPANY_STATE_FLOW_EVIDENCE_SCHEMA, "evidence_sha256", "company-state flow",
    )
    library_sha = _checked(
        move_library, STRATEGY_MOVE_LIBRARY_SCHEMA, "library_sha256", "strategy move library",
    )
    transitions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for block in flow.get("transition_blocks") or ():
        for raw in block.get("rows") or ():
            transitions[str(raw["entity_id"])].append({
                "source_epoch": str(block["source_epoch"]),
                "target_epoch": str(block["target_epoch"]),
                **dict(raw),
            })

    events = {}
    event_features: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for move in move_library.get("moves") or ():
        event = dict(move.get("implementation_event") or {})
        event_sha = str(event.get("implementation_event_sha256") or "")
        entity_id = str(move.get("entity_id") or "")
        if (
            not event_sha or entity_id not in transitions
            or move.get("causal_panel_status") != "treatment_event_ready"
            or event.get("treatment_timing_status") != "exact_adoption_event"
        ):
            continue
        events.setdefault(event_sha, {
            "entity_id": entity_id,
            "event_sha256": event_sha,
            "occurred_at": str(event["occurred_at"]),
            "available_at": str(event["available_at"]),
            "mechanism_phenotype_sha256": str(move["mechanism_phenotype_sha256"]),
            "move_sha256": str(move["move_sha256"]),
        })
        attribution = dict(move.get("strategy_program_attribution") or {})
        event_features[event_sha].append({
            "move_sha256": str(move["move_sha256"]),
            "mechanism_phenotype_sha256": str(move["mechanism_phenotype_sha256"]),
            "environment_sha256": str(move.get("environment_sha256") or ""),
            "recursive_frontier_credit_eligible": bool(
                attribution.get("recursive_frontier_credit_eligible")
            ),
            "integrated_program_ids": sorted(map(str, attribution.get("frontier_program_ids") or ())),
        })

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events.values():
        grouped[(event["entity_id"], event["event_sha256"])].append(event)
    next_known_at = {}
    for entity_id in transitions:
        ordered_events = sorted(
            (event for event in events.values() if event["entity_id"] == entity_id),
            key=lambda event: (event["available_at"], event["occurred_at"], event["event_sha256"]),
        )
        for event, successor in zip(ordered_events, ordered_events[1:]):
            next_known_at[event["event_sha256"]] = successor["available_at"]
    bundles = []
    exposed_path_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for (entity_id, event_sha), rows in sorted(grouped.items()):
        known_at = max(row["available_at"] for row in rows)
        occurred_at = max(row["occurred_at"] for row in rows)
        censor_at = next_known_at.get(event_sha)
        paths = transitions[entity_id]
        pre = [row for row in paths if row["target_epoch"] < occurred_at[:10]]
        observable_post = [
            row for row in paths
            if row["source_epoch"] >= known_at[:10]
            and (not censor_at or row["target_epoch"] < censor_at[:10])
        ]
        straddling = [
            row for row in paths
            if row not in pre and row not in observable_post
        ]
        bundle = {
            "entity_id": entity_id,
            "event_month": occurred_at[:7],
            "occurred_at": occurred_at,
            "known_at": known_at,
            "censored_at_next_known_event": censor_at,
            "event_sha256s": sorted(row["event_sha256"] for row in rows),
            "move_sha256s": sorted(row["move_sha256"] for row in rows),
            "mechanism_phenotype_sha256s": sorted({
                row["mechanism_phenotype_sha256"] for row in rows
            }),
            "pre_transition_count": len(pre),
            "observable_post_transition_count": len(observable_post),
            "straddling_or_not_yet_observable_count": len(straddling),
            "pre_transition_sha256s": sorted(stable_sha256(row) for row in pre),
            "observable_post_transition_sha256s": sorted(
                stable_sha256(row) for row in observable_post
            ),
        }
        features = {
            stable_sha256(row): row
            for event in rows for row in event_features[event["event_sha256"]]
        }
        bundle["mechanism_phenotype_sha256s"] = sorted({
            row["mechanism_phenotype_sha256"] for row in features.values()
        })
        bundle["environment_sha256s"] = sorted({
            row["environment_sha256"] for row in features.values() if row["environment_sha256"]
        })
        bundle["recursive_frontier_credit_eligible"] = False
        bundle["integrated_program_ids"] = []
        bundle_sha = stable_sha256(bundle)
        bundles.append({**bundle, "bundle_sha256": bundle_sha})
        if len(bundle["mechanism_phenotype_sha256s"]) != 1:
            continue
        phenotype_sha = bundle["mechanism_phenotype_sha256s"][0]
        for path in _two_step_paths(observable_post):
            identity = {
                **path,
                "event_bundle_sha256": bundle_sha,
                "implementation_event_sha256": event_sha,
                "event_occurred_at": occurred_at,
                "event_available_at": known_at,
                "strategy_exposure": "exposed",
                "mechanism_phenotype_sha256": phenotype_sha,
                "environment_sha256s": bundle["environment_sha256s"],
                "recursive_program_credit": "option_event_only",
                "integrated_program_ids": [],
                "conditioning_status": "single_phenotype",
            }
            model_row = {**identity, "model_row_sha256": stable_sha256(identity)}
            key = (phenotype_sha, entity_id, path["path_sha256"])
            prior = exposed_path_rows.get(key)
            if prior is None or str(prior["event_available_at"]) < known_at:
                exposed_path_rows[key] = model_row

    model_path_rows = list(exposed_path_rows.values())

    for raw in unexposed_coverage:
        coverage = dict(raw)
        entity_id = str(coverage.get("entity_id") or "")
        phenotype_sha = str(coverage.get("mechanism_phenotype_sha256") or "")
        coverage_sha = str(coverage.get("monitoring_coverage_sha256") or "")
        if (
            entity_id not in transitions or len(phenotype_sha) != 64
            or len(coverage_sha) != 64
        ):
            continue
        for path in _two_step_paths(transitions[entity_id]):
            if not (
                str(coverage.get("covered_from") or "")[:10] <= path["source_epoch"]
                and path["terminal_epoch"] <= str(coverage.get("covered_through") or "")[:10]
            ):
                continue
            identity = {
                **path,
                "event_bundle_sha256": None,
                "implementation_event_sha256": None,
                "event_occurred_at": None,
                "event_available_at": None,
                "strategy_exposure": "unexposed",
                "mechanism_phenotype_sha256": phenotype_sha,
                "environment_sha256s": [],
                "monitoring_coverage_sha256": coverage_sha,
                "recursive_program_credit": "none",
                "integrated_program_ids": [],
                "conditioning_status": "single_phenotype",
            }
            model_path_rows.append({**identity, "model_row_sha256": stable_sha256(identity)})
    model_path_rows = list({
        row["model_row_sha256"]: row for row in model_path_rows
    }.values())

    post_issuers = sorted({
        row["entity_id"] for row in model_path_rows if row["strategy_exposure"] == "exposed"
    })
    phenotype_support = []
    for phenotype_sha in sorted({
        str(row["mechanism_phenotype_sha256"]) for row in model_path_rows
    }):
        phenotype_rows = [
            row for row in model_path_rows
            if row["mechanism_phenotype_sha256"] == phenotype_sha
        ]
        exposed_counts = defaultdict(int)
        unexposed_counts = defaultdict(int)
        for row in phenotype_rows:
            target = exposed_counts if row["strategy_exposure"] == "exposed" else unexposed_counts
            target[str(row["entity_id"])] += 1
        eligible_exposed = sorted(
            entity for entity, count in exposed_counts.items() if count >= MIN_TWO_STEP_PATHS
        )
        eligible_unexposed = sorted(
            entity for entity, count in unexposed_counts.items() if count >= MIN_TWO_STEP_PATHS
        )
        phenotype_support.append({
            "mechanism_phenotype_sha256": phenotype_sha,
            "exposed_issuer_ids": eligible_exposed,
            "unexposed_issuer_ids": eligible_unexposed,
            "exposed_issuer_count": len(eligible_exposed),
            "unexposed_issuer_count": len(eligible_unexposed),
            "fit_support_available": (
                len(eligible_exposed) >= MIN_FIT_ISSUERS + MIN_UNSEEN_ISSUERS
                and len(eligible_unexposed) >= MIN_FIT_ISSUERS + MIN_UNSEEN_ISSUERS
            ),
        })
    fit_support = next(
        (row for row in phenotype_support if row["fit_support_available"]), None,
    )
    fit_issuers = sorted(
        set((fit_support or {}).get("exposed_issuer_ids") or ())
        | set((fit_support or {}).get("unexposed_issuer_ids") or ())
    )
    missing_inputs = [
        *(["observable_post_two_step_paths"] if not any(
            row["strategy_exposure"] == "exposed" for row in model_path_rows
        ) else []),
        *(["certified_unexposed_monitored_paths"] if not any(
            row["strategy_exposure"] == "unexposed" for row in model_path_rows
        ) else []),
    ]
    path_input_body = {
        "schema": "jaggedthoughts-strategy-conditioned-path-input-v1",
        "company_state_flow_evidence_sha256": flow_sha,
        "strategy_move_library_sha256": library_sha,
        "row_count": len(model_path_rows),
        "single_phenotype_row_count": sum(
            row["conditioning_status"] == "single_phenotype" for row in model_path_rows
        ),
        "rows": model_path_rows,
        "missing_inputs": missing_inputs,
        "authority": "future_tournament_input_only",
        "capital_authority": False,
    }
    path_input = {**path_input_body, "input_sha256": stable_sha256(path_input_body)}
    body = {
        "schema": STRATEGY_STATE_TRANSITION_JOIN_SCHEMA,
        "as_of": flow["as_of"],
        "company_state_flow_evidence_sha256": flow_sha,
        "strategy_move_library_sha256": library_sha,
        "transition_episode_count": sum(len(rows) for rows in transitions.values()),
        "overlap_entity_ids": sorted(set(transitions) & {
            str(move.get("entity_id") or "") for move in move_library.get("moves") or ()
        }),
        "exact_event_bundle_count": len(bundles),
        "exact_event_issuer_count": len({row["entity_id"] for row in bundles}),
        "observable_post_event_issuer_count": len(post_issuers),
        "observable_post_event_issuer_ids": post_issuers,
        "fit_qualified_issuer_count": len(fit_issuers),
        "fit_qualified_issuer_ids": fit_issuers,
        "fit_support_floor": {
            "independent_issuers_per_exposure_class": MIN_FIT_ISSUERS,
            "unseen_issuers_per_exposure_class": MIN_UNSEEN_ISSUERS,
            "pre_transitions_per_issuer": MIN_PRE_TRANSITIONS,
            "observable_post_transitions_per_issuer": MIN_POST_TRANSITIONS,
            "two_step_paths_per_issuer": MIN_TWO_STEP_PATHS,
        },
        "phenotype_path_support": phenotype_support,
        "event_bundles": bundles,
        "strategy_conditioned_path_input": path_input,
        "status": (
            "fit_support_available" if fit_support
            else "collecting_post_event_paths"
        ),
        "next_activation": (
            "Freeze a chronological strategy-conditioned Markov/current tournament."
            if fit_support else
            "Acquire exact-timed exposed paths and source-complete no-family-adoption controls; do not fit before one phenotype has eight fit and eight unseen issuers per exposure class, each with four two-step paths."
        ),
        "causal_authority": False,
        "signal_authority": False,
        "capital_authority": False,
    }
    return {**body, "join_sha256": stable_sha256(body)}


def compile_workspace_strategy_state_transition_join(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    summary = json.loads((
        root / "experiments/results/company-state-probability-current.json"
    ).read_text(encoding="utf-8"))
    flow = json.loads((root / str(summary["artifact_path"])).read_text(encoding="utf-8"))
    moves = json.loads((
        root / "institutional_learning/strategy_moves/latest.json"
    ).read_text(encoding="utf-8"))
    monitors = {}
    for path in sorted((
        root / "institutional_learning/strategy_cohorts/monitors"
    ).glob("*.json")):
        monitor = json.loads(path.read_text(encoding="utf-8"))
        body = {key: value for key, value in monitor.items() if key != "monitor_sha256"}
        if monitor.get("monitor_sha256") == stable_sha256(body):
            monitors[(monitor.get("request_sha256"), monitor.get("result_sha256"))] = monitor
    coverage = []
    for path in sorted((
        root / "institutional_learning/strategy_cohorts/results"
    ).glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        body = {key: value for key, value in row.items() if key != "result_sha256"}
        monitor = monitors.get((row.get("request_sha256"), row.get("result_sha256")))
        span = row.get("coverage") or {}
        if (
            row.get("result_sha256") != stable_sha256(body)
            or not monitor
            or row.get("classification") != "no_family_adoption_found"
            or not span.get("sec_filings_searched")
            or not span.get("issuer_materials_searched")
        ):
            continue
        coverage_body = {
            "entity_id": str(row.get("peer_entity_id") or ""),
            "mechanism_phenotype_sha256": str(
                row.get("mechanism_phenotype_sha256") or ""
            ),
            "covered_from": str(span.get("search_start_at") or ""),
            "covered_through": min(
                str(span.get("search_end_at") or ""), str(monitor.get("covered_through") or ""),
            ),
            "result_sha256": str(row["result_sha256"]),
            "monitor_sha256": str(monitor["monitor_sha256"]),
        }
        coverage.append({
            **coverage_body,
            "monitoring_coverage_sha256": stable_sha256(coverage_body),
        })
    result = compile_strategy_state_transition_join(flow, moves, coverage)
    destination = root / "experiments/results/strategy-state-transition-join.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return result


__all__ = [
    "STRATEGY_STATE_TRANSITION_JOIN_SCHEMA",
    "MIN_FIT_ISSUERS",
    "MIN_POST_TRANSITIONS",
    "MIN_PRE_TRANSITIONS",
    "MIN_TWO_STEP_PATHS",
    "MIN_UNSEEN_ISSUERS",
    "compile_strategy_state_transition_join",
    "compile_workspace_strategy_state_transition_join",
]
