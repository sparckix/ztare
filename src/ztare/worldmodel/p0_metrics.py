from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from ztare.common.strategy_card_roles import active_strategy_cards
from ztare.worldmodel.carrier_loader import (
    CarrierEvidenceIdentityError,
    require_current_carrier_evidence_binding,
    resolve_current_carrier_evidence_identity,
)


SCHEMA = "ztare-arc3-p0-metrics-v2"


def build_p0_metrics(project: str | Path) -> dict[str, Any]:
    """Build a read-only P0 skill-acquisition metrics receipt.

    P0 metrics are scoreboard/science observables, not promotion authority.
    They summarize transfer, reuse, efficiency, and intervention pressure from
    artifacts that existing producers already write.
    """
    project = Path(project)
    ws = project / "workspace"
    raw_transfer = _read_json(ws / "latest_level_transfer_probe.json")
    transfer: dict[str, Any] = {}
    transfer_binding: dict[str, Any] | None = None
    transfer_identity_status = "missing"
    if raw_transfer:
        try:
            current = resolve_current_carrier_evidence_identity(project)
            transfer_binding = require_current_carrier_evidence_binding(
                raw_transfer, current
            )
            transfer = {
                **raw_transfer,
                "carrier_evidence_identity": transfer_binding,
            }
            transfer_identity_status = "current"
        except (CarrierEvidenceIdentityError, OSError, TypeError, ValueError):
            transfer_identity_status = "historical_or_unbound"
    terminal = _read_json(ws / "terminal_closure_audit.json")
    play = _read_json(ws / "arc3_play_loop_report.json")
    self_play = _read_json(ws / "latest_self_play_probe.json")
    try:
        from ztare.common.candidate_memory import admissible_candidate_memory_records

        active_candidate_records = admissible_candidate_memory_records(project)
    except Exception:  # noqa: BLE001 - observer remains available with missing projection
        active_candidate_records = []
    proposals = _read_jsonl(ws / "operator_proposals.jsonl")
    promotions = _read_jsonl(ws / "grammar_extension_promotion_contracts.jsonl")
    telemetry = _read_jsonl(ws / "iteration_telemetry.jsonl")
    r1_debug_text = _read_r1_debug_text(ws)
    reachability = _latest_reachability_receipt(ws)
    seed_replays = _read_jsonl(ws / "level_boundary_seed_replays.jsonl")

    trials = _verified_skill_trials(play, self_play)
    levels_beaten = _levels_beaten(play, self_play, seed_replays)
    actions = [row["active_interventions"] for row in trials] or _actions_per_level(play)
    catalog_size = _catalog_size()
    catalog_promotions = len(promotions)
    catalog_proposals = len(proposals)
    total_r1 = max(_telemetry_contains(telemetry, "R1"), _text_contains_count(r1_debug_text, "Rejection reason:"))
    temporal_rejections = max(
        _telemetry_contains(telemetry, "temporal admissibility"),
        _text_contains_count(r1_debug_text, "temporal admissibility"),
    )
    action_requests = max(
        _telemetry_contains(telemetry, "LEAF_WORKBENCH_ACTION_REQUEST"),
        _text_contains_count(r1_debug_text, "LEAF_WORKBENCH_ACTION_REQUEST"),
    )
    transfer_steps = _nested_int(transfer, "local_transfer", "steps_tested")
    transfer_exact_after_repair = _nested_int(
        transfer, "local_transfer", "exact_steps_after_first_step_repair"
    )
    reach_states = _reachability_count(reachability, "states_enumerated")
    reach_edges = _reachability_count(reachability, "edges_enumerated")
    return {
        "schema": SCHEMA,
        "project": str(project),
        "source_refs": _existing_refs(
            ws,
            [
                "latest_level_transfer_probe.json",
                "terminal_closure_audit.json",
                "arc3_play_loop_report.json",
                "latest_self_play_probe.json",
                "level_boundary_seed_replays.jsonl",
                "candidate_memory.json",
                "strategy_experiments.jsonl",
                "operator_proposals.jsonl",
                "grammar_extension_promotion_contracts.jsonl",
                "iteration_telemetry.jsonl",
                "r1_debug",
            ],
        ),
        "scoreboard": {
            "levels_beaten": levels_beaten,
            "actions_per_level": actions,
            "verified_skill_trials": trials,
            "relative_human_action_efficiency": _rhae(play, terminal),
            "conductor_interventions": _count_interventions(telemetry),
        },
        "closure_boundaries": _closure_boundaries(terminal),
        "information_theory": {
            "catalog_size": catalog_size,
            "catalog_growth_velocity": None,
            "carrier_fidelity_best": _carrier_fidelity_best(active_candidate_records),
            "operator_reusability_index": None,
            "temporal_admissibility_leakage": _ratio(temporal_rejections, max(1, total_r1)),
        },
        "transfer": {
            "identity_status": transfer_identity_status,
            "carrier_evidence_identity": transfer_binding,
            "historical_receipt_present": bool(raw_transfer and not transfer),
            "post_depth": _get_int(transfer, "post_depth"),
            "exact_actions": _get_int(transfer, "exact_actions"),
            "exact_steps": _nested_int(transfer, "local_transfer", "exact_steps")
            or _get_int(transfer, "exact_steps"),
            "empirical_transfer_depth": transfer_exact_after_repair
            or _nested_int(transfer, "local_transfer", "exact_steps")
            or _get_int(transfer, "exact_steps"),
            "local_steps_tested": transfer_steps,
            "exact_steps_after_first_step_repair": transfer_exact_after_repair,
            "first_step_repair_generalizes_to_depth": _nested_value(
                transfer, "local_transfer", "first_step_repair_generalizes_to_depth"
            ),
            "hypothesis_split_ratio": _hypothesis_split_ratio(transfer),
        },
        "reachability": {
            "abstract_vertices": reach_states,
            "abstract_edges": reach_edges,
            "abstract_entropy_bits": _reachability_entropy(reach_states, reach_edges),
            "status": reachability.get("status"),
            "saturated": reachability.get("saturated"),
        },
        "compression": {
            "catalog_proposals": catalog_proposals,
            "catalog_promotions": catalog_promotions,
            "catalog_growth_rate": None,
            "operator_vocabulary_size": _operator_vocabulary_size(active_candidate_records),
            "operator_reuse_count": None,
            "open_strategy_cards": len(
                active_strategy_cards(ws / "strategy_experiments.jsonl")
            ),
        },
        "kernel_pressure": {
            "temporal_admissibility_failures": temporal_rejections,
            "r1_failures": total_r1,
            "pre_judge_failures": _telemetry_contains(telemetry, "PRE_JUDGE"),
            "tool_action_requests": action_requests,
            "scope": "unscoped_cumulative_history",
        },
        "metric_contracts": _metric_contracts(
            have_trials=bool(trials),
            have_transfer=bool(transfer),
            have_reachability=bool(reachability),
            have_active_candidates=bool(active_candidate_records),
        ),
        "source_manifest": _source_manifest(
            ws,
            [
                "latest_level_transfer_probe.json",
                "terminal_closure_audit.json",
                "arc3_play_loop_report.json",
                "latest_self_play_probe.json",
                "candidate_memory.json",
                "strategy_experiments.jsonl",
                "operator_proposals.jsonl",
                "grammar_extension_promotion_contracts.jsonl",
                "iteration_telemetry.jsonl",
                "level_boundary_seed_replays.jsonl",
            ],
        ),
        "control_readiness": {
            "status": "observer_only",
            "decision_consumer_count": 0,
            "blocking_reasons": [
                *(
                    ["transfer receipt is not bound to the current carrier/evidence identity"]
                    if raw_transfer and not transfer
                    else []
                ),
                "other telemetry populations lack one shared run-and-epoch identity",
                "catalog growth has no before/after population denominator",
                "operator reuse has no cross-context identity ledger",
                "no registered allocator or router consumes this snapshot",
            ],
        },
        "interpretation": (
            "read-only P0 observations; only metrics marked operational have a "
            "compatible evidence population, and none currently steers search"
        ),
    }


def write_p0_metrics(project: str | Path) -> Path:
    project = Path(project)
    out = project / "workspace" / "p0_metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_p0_metrics(project), indent=2, sort_keys=True), encoding="utf-8")
    return out


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _read_r1_debug_text(workspace: Path) -> str:
    debug_dir = workspace / "r1_debug"
    if not debug_dir.exists():
        return ""
    chunks: list[str] = []
    for path in sorted(debug_dir.glob("*_r1_attempts.md")):
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:  # noqa: BLE001
            continue
    return "\n".join(chunks)


def _text_contains_count(text: str, needle: str) -> int:
    if not text:
        return 0
    return text.lower().count(needle.lower())


def _existing_refs(workspace: Path, names: list[str]) -> list[str]:
    return [f"workspace/{name}" for name in names if (workspace / name).exists()]


def _levels_beaten(
    play: dict[str, Any],
    self_play: dict[str, Any] | None = None,
    seed_replays: list[dict[str, Any]] | None = None,
) -> int:
    self_play_levels = 0
    if (self_play or {}).get("schema") == "ztare-arc3-self-play-probe-v1":
        self_play_levels = int((self_play or {}).get("levels_after") or 0)
    confirmed_epochs = [
        self_play_levels,
        *[
            int(row.get("observed_epoch") or 0)
            for row in (seed_replays or [])
            if row.get("status") == "verified"
        ],
    ]
    # A generic task-discharge receipt closes its task contract; it does not
    # attest an adapter progress coordinate. ARC progress comes only from the
    # adapter-owned self-play/seed/play telemetry above and below.
    cycles = play.get("cycles") if isinstance(play.get("cycles"), list) else []
    cycle_total = sum(
        int(row.get("levels_gained") or 0) for row in cycles if isinstance(row, dict)
    )
    confirmed_epochs.append(cycle_total)
    return max(confirmed_epochs, default=0)


def _verified_skill_trials(
    play: dict[str, Any], self_play: dict[str, Any]
) -> list[dict[str, Any]]:
    trials: list[dict[str, Any]] = []
    if self_play.get("schema") == "ztare-arc3-self-play-probe-v1":
        seed = self_play.get("seed_receipt")
        if isinstance(seed, dict):
            target = int(seed.get("observed_progress_after") or 0)
            actions = int(seed.get("interventions_executed") or 0)
            if target > 0 and actions > 0:
                trials.append({
                    "source_epoch": 0,
                    "target_epoch": target,
                    "active_interventions": actions,
                    "evidence_ref": "workspace/latest_self_play_probe.json#seed_receipt",
                    "authority": "environment_observed_epoch_after_seed_replay",
                    "establishes_task_discharge": False,
                })
        gained = int(self_play.get("levels_gained") or 0)
        before = int(self_play.get("levels_before") or 0)
        after = int(self_play.get("levels_after") or 0)
        if self_play.get("status") == "goal_reached" and gained > 0 and after > before:
            trials.append({
                "source_epoch": before,
                "target_epoch": after,
                "active_interventions": int(self_play.get("steps_executed") or 0),
                "replans": int(self_play.get("replans") or 0),
                "evidence_ref": "workspace/latest_self_play_probe.json",
                "authority": "environment_terminal_verifier",
                "establishes_task_discharge": False,
            })
    if trials:
        return sorted(trials, key=lambda row: row["target_epoch"])
    cycles = play.get("cycles") if isinstance(play.get("cycles"), list) else []
    epoch = 0
    for row in cycles:
        if not isinstance(row, dict):
            continue
        gained = int(row.get("levels_gained") or 0)
        if gained <= 0:
            continue
        trials.append({
            "source_epoch": epoch,
            "target_epoch": epoch + gained,
            "active_interventions": int(row.get("steps") or row.get("actions") or 0),
            "evidence_ref": "workspace/arc3_play_loop_report.json",
            "authority": "adapter_progress_telemetry",
            "establishes_task_discharge": False,
        })
        epoch += gained
    return trials


def _actions_per_level(play: dict[str, Any]) -> list[int]:
    cycles = play.get("cycles") if isinstance(play.get("cycles"), list) else []
    return [
        int(row.get("steps") or row.get("actions") or 0)
        for row in cycles
        if isinstance(row, dict) and int(row.get("levels_gained") or 0) > 0
    ]


def _rhae(play: dict[str, Any], terminal: dict[str, Any]) -> float | None:
    for payload in (terminal, play):
        for key in ("rhae", "relative_human_action_efficiency", "action_efficiency"):
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return None


def _closure_boundaries(terminal: dict[str, Any]) -> dict[str, Any]:
    """Project terminal-close claim boundaries into the read-only P0 receipt."""
    if terminal.get("schema") != "ztare-worldmodel-terminal-closure-audit-v1":
        return {
            "task_discharged": False,
            "level_closed": False,
            "level_projection_status": "missing_task_discharge_audit",
            "search_control_closed": False,
            "candidate_promoted_by_terminal": False,
            "candidate_promotion_proven": False,
            "autonomous_completion_proven": False,
            "authority_ladder_ok": None,
            "terminal_witness_sha": "",
        }
    claims = terminal.get("claim_boundaries") if isinstance(terminal.get("claim_boundaries"), dict) else {}
    candidate = claims.get("candidate_promotion") if isinstance(claims.get("candidate_promotion"), dict) else {}
    autonomy = claims.get("autonomous_completion") if isinstance(claims.get("autonomous_completion"), dict) else {}
    authority = terminal.get("authority") if isinstance(terminal.get("authority"), dict) else {}
    report = terminal.get("terminal_report") if isinstance(terminal.get("terminal_report"), dict) else {}
    return {
        "task_discharged": bool(terminal.get("task_discharged")),
        # ``level_closed`` in the generic audit is a deprecated compatibility
        # projection of task discharge. It has no adapter-level authority.
        "level_closed": False,
        "level_projection_status": "adapter_progress_required",
        "search_control_closed": bool(terminal.get("search_control_closed")),
        "candidate_promoted_by_terminal": bool(authority.get("candidate_promotion_used_for_closure")),
        "candidate_promotion_proven": bool(candidate.get("proven")),
        "candidate_promotion_reason": str(candidate.get("reason") or ""),
        "autonomous_completion_proven": bool(autonomy.get("proven")),
        "autonomy_reason": str(autonomy.get("reason") or ""),
        "authority_ladder_ok": authority.get("authority_ladder_ok"),
        "terminal_witness_sha": str(report.get("terminal_witness_sha") or ""),
        "status": str(terminal.get("status") or ""),
        "verification_ok": bool((terminal.get("closure_verification") or {}).get("ok")),
    }


def _count_interventions(rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in rows
        if row.get("record_type") == "conductor_intervention"
        or row.get("operator_intervention") is True
    )


def _operator_vocabulary_size(records: list[dict[str, Any]]) -> int:
    if not isinstance(records, list):
        return 0
    seen: set[str] = set()
    for row in records:
        if not isinstance(row, dict):
            continue
        for key in ("operator", "repair_class", "source_type"):
            value = row.get(key)
            if isinstance(value, str) and value:
                seen.add(value)
    return len(seen)


def _carrier_fidelity_best(records: list[dict[str, Any]]) -> float | None:
    if not isinstance(records, list) or not records:
        return None
    best = 0.0
    for row in records:
        if not isinstance(row, dict):
            continue
        exact = row.get("visible_exact_rows")
        total = row.get("visible_checked_rows")
        if isinstance(exact, (int, float)) and isinstance(total, (int, float)) and total:
            best = max(best, float(exact) / float(total))
    return round(best, 6) if best else None


def _catalog_size() -> int | None:
    try:
        from ztare.worldmodel.spec_catalog import _APPLY  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return None
    return len(_APPLY)


def _latest_reachability_receipt(workspace: Path) -> dict[str, Any]:
    names = [
        "latest_reachability.json",
        "latest_reachability_receipt.json",
        "reachability_receipt.json",
    ]
    for name in names:
        payload = _read_json(workspace / name)
        if payload:
            return payload
    return {}


def _reachability_count(payload: dict[str, Any], key: str) -> int | None:
    aliases = {
        "states_enumerated": ("states_enumerated", "abstract_vertices", "vertices"),
        "edges_enumerated": ("edges_enumerated", "abstract_edges", "edges"),
    }
    for name in aliases.get(key, (key,)):
        value = payload.get(name)
        if isinstance(value, (int, float)):
            return int(value)
    return None


def _reachability_entropy(vertices: int | None, edges: int | None) -> float | None:
    if vertices is None and edges is None:
        return None
    total = max(0, int(vertices or 0)) + max(0, int(edges or 0))
    return round(math.log2(total + 1), 6)


def _hypothesis_split_ratio(transfer: dict[str, Any]) -> float | None:
    # If producers later write explicit version-space counts, prefer them.
    prior = transfer.get("models_prior")
    survive = transfer.get("models_survive")
    if isinstance(prior, (int, float)) and prior:
        if isinstance(survive, (int, float)):
            return round(float(survive) / float(prior), 6)
    return None


def _source_manifest(workspace: Path, names: list[str]) -> list[dict[str, Any]]:
    rows = []
    for name in names:
        path = workspace / name
        if not path.is_file():
            continue
        raw = path.read_bytes()
        rows.append({
            "source_ref": f"workspace/{name}",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "mtime_ns": path.stat().st_mtime_ns,
        })
    return rows


def _metric_contracts(
    *,
    have_trials: bool,
    have_transfer: bool,
    have_reachability: bool,
    have_active_candidates: bool,
) -> dict[str, dict[str, Any]]:
    return {
        "scoreboard.levels_beaten": {
            "identity": "maximum environment-attested epoch reached",
            "status": "operational" if have_trials else "missing_evidence",
        },
        "transfer.empirical_transfer_depth": {
            "identity": "consecutive exact transitions in one declared transfer population",
            "status": "operational" if have_transfer else "missing_evidence",
        },
        "information_theory.carrier_fidelity_best": {
            "identity": (
                "maximum exact-row ratio among admissible carriers on the active "
                "maximum visible evidence epoch"
            ),
            "status": "operational" if have_active_candidates else "missing_evidence",
        },
        "information_theory.catalog_growth_velocity": {
            "identity": "delta promoted vocabulary over delta acquired contexts",
            "status": "not_computable",
            "reason": "current ledgers expose cumulative rows without paired context epochs",
        },
        "information_theory.operator_reusability_index": {
            "identity": "same operator identity reused across distinct context identities",
            "status": "not_computable",
            "reason": "candidate fidelity is not cross-context reuse",
        },
        "information_theory.temporal_admissibility_leakage": {
            "identity": "temporally inadmissible attempts over one scoped R1 population",
            "status": "diagnostic_only",
            "reason": "current numerator and denominator are cumulative and lack shared run identity",
        },
        "transfer.hypothesis_split_ratio": {
            "identity": "surviving hypothesis identities over prior hypothesis identities",
            "status": "operational_when_explicit_counts_present",
            "reason": "residual classes divided by actions are not hypotheses",
        },
        "reachability.abstract_entropy_bits": {
            "identity": "log-size proxy of a declared abstract search graph",
            "status": "diagnostic_only" if have_reachability else "missing_evidence",
            "reason": "log2(vertices+edges+1) is search size, not a state-distribution entropy",
        },
    }


def _telemetry_contains(rows: list[dict[str, Any]], needle: str) -> int:
    needle_l = needle.lower()
    return sum(
        1
        for row in rows
        if needle_l in json.dumps(row, sort_keys=True, default=str).lower()
    )


def _get_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return int(value) if isinstance(value, (int, float)) else None


def _nested_int(payload: dict[str, Any], outer: str, inner: str) -> int | None:
    value = _nested_value(payload, outer, inner)
    return int(value) if isinstance(value, (int, float)) else None


def _nested_value(payload: dict[str, Any], outer: str, inner: str) -> Any:
    node = payload.get(outer)
    return node.get(inner) if isinstance(node, dict) else None


def _ratio(numer: int, denom: int) -> float:
    return round(float(numer) / float(denom), 6)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if args.write:
        path = write_p0_metrics(args.project)
        print(path)
    else:
        print(json.dumps(build_p0_metrics(args.project), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
