"""Per-iteration + run-boundary telemetry helpers (Phase 4g, 2026-05-06).

Extracted from autoresearch_loop.py lines ~644-977. These ten helpers
cluster cleanly: pure dict transformations on usage / eval payloads,
plus two jsonl-emit functions for run-boundary and per-iteration rows.
Moving them out of the engine entry point shrinks the iter-loop body
and makes the telemetry surface independently testable.

Behaviour preserved verbatim from the prior inline implementation
(autoresearch_loop.py, 2026-05-05 git history). Public-facing names
drop the leading underscore; autoresearch_loop re-aliases them as
private to keep call sites unchanged during the migration window.

The ``cap_kind`` classification import in ``append_iteration_telemetry``
is lazy-imported (per the original inline code) so this module can
be loaded by tests without pulling cap_kind's transitive deps.

Sibling modules:
  - ``orchestrator/telemetry.py`` (Phase 4b, Cage engagement records)
  - ``orchestrator/r1_retry.py`` (Phase 4g, R1 logging + tracker)
  - ``orchestrator/state.py`` (Phase 4c, runtime resolution)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Pure helpers — no apparatus state, no module globals
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    """Current ISO-8601 UTC timestamp with explicit timezone offset.

    Delegates to the shared `common.telemetry` core so autoresearch + leanmill share ONE canonical timestamp
    (re-export shim; behavior unchanged)."""
    from ztare.common.telemetry import utc_now_iso as _shared
    return _shared()


def usage_bucket_snapshot(bucket: dict) -> dict:
    """Snapshot a SESSION_*_USAGE bucket into a dict with stable keys.

    The autoresearch_loop accumulates per-call usage into module-level
    dicts (SESSION_MUTATOR_USAGE, SESSION_JUDGE_USAGE). This helper
    normalises a snapshot of one such bucket — int coercion on token
    counters, float on cost, bool on cost_known. Used at iter
    boundaries to capture before/after state for ``usage_delta``.
    """
    return {
        "input_tokens": int(bucket.get("input_tokens", 0) or 0),
        "output_tokens": int(bucket.get("output_tokens", 0) or 0),
        "cache_creation_input_tokens": int(bucket.get("cache_creation_input_tokens", 0) or 0),
        "cache_read_input_tokens": int(bucket.get("cache_read_input_tokens", 0) or 0),
        "thinking_tokens": int(bucket.get("thinking_tokens", 0) or 0),
        "estimated_cost_usd": float(bucket.get("estimated_cost_usd", 0.0) or 0.0),
        "cost_known": bool(bucket.get("cost_known", False)),
    }


def usage_delta(before: dict, after: dict) -> dict:
    """Compute the per-iter delta between two usage snapshots.

    Returns ``has_usage`` False when no token counters moved (signals
    that no LLM call happened on this iter — e.g., a cached / replayed
    iter). When ``has_usage`` is True but ``cost_known`` is False
    (model didn't return billed-cost info) the cost field is None.
    """
    input_tokens = max(0, int(after["input_tokens"]) - int(before["input_tokens"]))
    output_tokens = max(0, int(after["output_tokens"]) - int(before["output_tokens"]))
    cache_read_tokens = max(
        0,
        int(after["cache_read_input_tokens"]) - int(before["cache_read_input_tokens"]),
    )
    cache_write_tokens = max(
        0,
        int(after["cache_creation_input_tokens"]) - int(before["cache_creation_input_tokens"]),
    )
    thinking_tokens = max(
        0,
        int(after.get("thinking_tokens", 0)) - int(before.get("thinking_tokens", 0)),
    )
    has_usage = any(
        value > 0
        for value in (
            input_tokens,
            output_tokens,
            cache_read_tokens,
            cache_write_tokens,
            thinking_tokens,
        )
    )
    cost_known = True if not has_usage else bool(after.get("cost_known", False))
    estimated_cost_usd = (
        round(
            max(
                0.0,
                float(after["estimated_cost_usd"]) - float(before["estimated_cost_usd"]),
            ),
            6,
        )
        if has_usage and cost_known
        else 0.0 if not has_usage else None
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "thinking_tokens": thinking_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "cost_known": cost_known,
        "has_usage": has_usage,
    }


def combined_iteration_cost_usd(mutator_usage: dict, judge_usage: dict) -> float | None:
    """Sum two per-call usage deltas into a single iter cost.

    Returns None if either side reports usage but unknown cost — the
    apparatus must not silently default to 0.0 when a stealth-bill
    estimate would be more honest.
    """
    total = 0.0
    for usage in (mutator_usage, judge_usage):
        if not usage.get("has_usage", False):
            continue
        if not usage.get("cost_known", False):
            return None
        total += float(usage.get("estimated_cost_usd", 0.0) or 0.0)
    return round(total, 6)


def collect_compression_progress_inputs(workspace_dir: Path) -> dict[str, Any]:
    """Read lower-is-better compression proxies from current workspace files.

    The values are advisory telemetry for later replay. BIC and negated MDL gain
    are separate families because their numeric scales are not interchangeable.
    """

    candidates: list[dict[str, Any]] = []
    fit = _read_json_dict(workspace_dir / "fit_features_result.json")
    fit_source = "fit_features_result.json"
    if not fit:
        fit = _read_json_dict(workspace_dir / "fit_result.json")
        fit_source = "fit_result.json"
    if fit:
        bic = _fit_bic_proxy(fit)
        if bic is not None:
            candidates.append({
                "family": "fit_bic",
                "complexity": bic,
                "source": fit_source,
                "field": "bic" if _finite_float(fit.get("bic")) is not None else "rmse_k_n_bic_proxy",
                "lower_is_better": True,
                "k_params": _safe_int_or_none(fit.get("k_params")),
                "n_fit_rows": _safe_int_or_none(fit.get("n_fit_rows")),
                "fit_success": bool(fit.get("success", True)),
            })

    framing = _read_json_dict(workspace_dir / "framing_report.json")
    if framing:
        mdl_gain = _finite_float(framing.get("MDL_gain_bits"))
        if mdl_gain is not None:
            candidates.append({
                "family": "framer_mdl_gain_bits",
                "complexity": -mdl_gain,
                "source": "framing_report.json",
                "field": "MDL_gain_bits",
                "raw_mdl_gain_bits": mdl_gain,
                "lower_is_better": True,
                "framer_engaged": bool(framing.get("framer_engaged")),
            })

    # Universal fallback: the champion probability DAG's two-part MDL. Every project has a probability DAG, so
    # compression progress works beyond the fit/framer domains. Lowest priority — fit/framer win when present.
    if not candidates:
        from ztare.validator.core.compression_progress import dag_description_length
        project_dir = workspace_dir.parent
        dag = _read_json_dict(project_dir / "champion_probability_dag.json") or _read_json_dict(project_dir / "latest_probability_dag.json")
        dl = dag_description_length(dag) if dag else None
        if dl is not None:
            candidates.append({
                "family": "dag_mdl",
                "complexity": dl,
                "source": "champion_probability_dag.json",
                "field": "two_part_mdl_bits",
                "lower_is_better": True,
                "n_nodes": len(dag.get("nodes") or []),
                "n_edges": len(dag.get("edges") or []),
            })

    selected = candidates[0] if candidates else None
    return {
        "schema": "ztare-compression-progress-inputs-v1",
        "status": "available" if selected else "no_signal",
        "family": str(selected.get("family")) if selected else "",
        "complexity": selected.get("complexity") if selected else None,
        "source": str(selected.get("source")) if selected else "",
        "candidates": candidates,
        "rationale": (
            "Lower complexity means the current run made the project simpler to defend."
            if selected
            else "No BIC/MDL-style compression proxy was written for this iteration."
        ),
    }


def compression_progress_advice_for_iteration(
    workspace_dir: Path,
    current_payload: dict[str, Any],
) -> dict[str, Any]:
    """Replay compression-progress advice through the current iteration.

    This is telemetry, not loop control. The loop still acts on information
    yield; this records whether the simpler-explanation signal agreed at the
    point the iteration closed.
    """

    try:
        from ztare.validator.core.compression_progress import (
            evaluate_compression_progress,
            observations_from_rows,
        )
    except ImportError:
        return {
            "schema": "ztare-compression-progress-advice-v1",
            "status": "unavailable",
            "recommendation": "no_signal",
            "rationale": "Compression-progress evaluator could not be imported.",
        }

    rows = [
        row
        for row in _read_jsonl_dicts(workspace_dir / "iteration_telemetry.jsonl")
        if row.get("record_type") == "iteration"
    ]
    rows.append(current_payload)
    decision = evaluate_compression_progress(observations_from_rows(rows))
    return {
        "schema": "ztare-compression-progress-advice-v1",
        "status": "available" if decision.usable_observations >= 2 else "no_signal",
        "recommendation": decision.recommendation,
        "rationale": decision.rationale,
        "usable_observations": decision.usable_observations,
        "family": decision.family,
        "best_complexity": decision.best_complexity,
        "latest_complexity": decision.latest_complexity,
        "last_drop_iteration": decision.last_drop_iteration,
        "stagnation_length": decision.stagnation_length,
        "compression_drop_count": decision.compression_drop_count,
        "future_progress_weight": decision.future_progress_weight,
        "best_effort": decision.best_effort,
        "latest_effort": decision.latest_effort,
        "effort_unit": decision.effort_unit,
    }


def extract_iteration_gate_metrics(evaluation: dict | None) -> tuple[bool, int, list[str]]:
    """Pull (gate_engaged, failure_count, failed_gate_ids) from an eval.

    Reads ``score_contract.deterministic_charter_gates`` (preferred) or
    the legacy top-level ``deterministic_charter_gates`` key. Returns
    ``(False, 0, [])`` for malformed payloads — telemetry must never
    crash the iter loop.
    """
    if not isinstance(evaluation, dict):
        return False, 0, []
    score_contract = evaluation.get("score_contract")
    if not isinstance(score_contract, dict):
        score_contract = {}
    payload = score_contract.get("deterministic_charter_gates", evaluation.get("deterministic_charter_gates"))
    if not isinstance(payload, dict):
        return False, 0, []

    declared = payload.get("declared", [])
    results = payload.get("results", [])
    gate_engagement = bool(payload.get("harness_invoked", False)) or bool(declared)
    failed_gate_ids: list[str] = []
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict) and not bool(item.get("passed", False)):
                name = item.get("name")
                if isinstance(name, str) and name:
                    failed_gate_ids.append(name)
    failure_count = int(payload.get("failure_count", len(failed_gate_ids)) or 0)
    if failed_gate_ids:
        failure_count = len(failed_gate_ids)
    return gate_engagement, failure_count, failed_gate_ids


def extract_iteration_escalation_flags(evaluation: dict | None) -> dict:
    """Read the two escalation flags an iter can carry.

    ``self_reference``: any ``self_reference_rule_fired`` on the eval
    or score_contract (mutator referenced the rubric/charter).
    ``semantic_escalation``: claim-test-mismatch escalation OR an
    unresolved semantic-gate diagnosis surfaced by the judge.
    """
    if not isinstance(evaluation, dict):
        return {"self_reference": False, "semantic_escalation": False}
    score_contract = evaluation.get("score_contract")
    if not isinstance(score_contract, dict):
        score_contract = {}
    rule = str(
        evaluation.get("self_reference_rule_fired")
        or score_contract.get("self_reference_rule_fired")
        or ""
    )
    unresolved_diagnosis = str(evaluation.get("semantic_gate_unresolved_diagnosis") or "")
    return {
        "self_reference": "self_reference" in rule,
        "semantic_escalation": (
            rule == "claim_test_mismatch_escalation" or bool(unresolved_diagnosis)
        ),
    }


def fallback_weakest_point_from_eval(evaluation: dict | None) -> str:
    """Reconstruct a weakest_point string when the judge omitted one.

    Combines gap_type / target / description / producer fields when
    present. Used by ``normalize_eval_payload`` so the apparatus never
    has a None weakest_point downstream.
    """
    if not isinstance(evaluation, dict):
        return "Malformed judge response: evaluation payload is not a dict"
    parts: list[str] = []
    gap_type = str(evaluation.get("gap_type") or "").strip()
    target = str(evaluation.get("target") or "").strip()
    description = str(evaluation.get("description") or "").strip()
    producer = str(evaluation.get("producer") or "").strip()
    if gap_type:
        parts.append(f"Judge gap type: {gap_type}")
    if target:
        parts.append(f"target={target}")
    if description:
        parts.append(description)
    if producer:
        parts.append(f"producer={producer}")
    if parts:
        return " | ".join(parts)
    return "Malformed judge response: missing weakest_point"


def normalize_eval_payload(
    evaluation: dict | None,
    *,
    context_label: str,
) -> dict:
    """Coerce a judge eval payload into the canonical shape consumers expect.

    Guarantees on the returned dict:
      - ``score`` is not None (defaults to 0)
      - ``score_contract`` is a dict
      - ``verified_axioms`` / ``retired_axioms_approved`` /
        ``evidence_gaps`` / ``derived_constraints`` / ``logic_gaps``
        are lists
      - ``weakest_point`` is a non-empty string
    """
    if not isinstance(evaluation, dict):
        return {
            "score": 0,
            "weakest_point": f"Malformed judge response in {context_label}: non-dict payload",
            "score_contract": {},
            "verified_axioms": [],
            "retired_axioms_approved": [],
            "evidence_gaps": [],
            "derived_constraints": [],
            "logic_gaps": [],
        }

    normalized = dict(evaluation)
    if normalized.get("score") is None:
        normalized["score"] = 0
    score_contract = normalized.get("score_contract")
    if not isinstance(score_contract, dict):
        normalized["score_contract"] = {}
    for key in ("verified_axioms", "retired_axioms_approved", "evidence_gaps", "derived_constraints", "logic_gaps"):
        value = normalized.get(key)
        if not isinstance(value, list):
            normalized[key] = []
    weakest_point = normalized.get("weakest_point")
    if not isinstance(weakest_point, str) or not weakest_point.strip():
        normalized["weakest_point"] = fallback_weakest_point_from_eval(normalized)
    return normalized


# ---------------------------------------------------------------------------
# JSONL-emit helpers
# ---------------------------------------------------------------------------


def _append_json_dict(path: Path, payload: dict) -> None:
    """Internal: append one dict to ``path`` as one JSON line.

    Delegates to the canonical `common.file_io.append_jsonl` — the SINGLE dict→JSONL primitive (this was one of
    four siblings; now shared across autoresearch + leanmill). Behavior preserved exactly: parent-dir auto-create
    + ``json.dumps`` (ensure_ascii default True) + trailing newline.
    """
    from ztare.common.file_io import append_jsonl as _shared
    _shared(path, payload)


def _read_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl_dicts(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        candidate = float(value)
    elif isinstance(value, str):
        try:
            candidate = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if candidate != candidate or candidate in (float("inf"), float("-inf")):
        return None
    return candidate


def _safe_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def _fit_bic_proxy(payload: dict[str, Any]) -> float | None:
    direct = _finite_float(payload.get("bic"))
    if direct is not None:
        return direct
    rmse = _finite_float(payload.get("rmse"))
    if rmse is None or rmse <= 0:
        return None
    residual_map = payload.get("residual_map")
    n_rows = _safe_int_or_none(payload.get("n_fit_rows"))
    if n_rows is None and isinstance(residual_map, list):
        n_rows = len(residual_map)
    params = payload.get("parameter_names")
    k_params = _safe_int_or_none(payload.get("k_params"))
    if k_params is None and isinstance(params, list):
        k_params = len(params)
    if n_rows is None or n_rows < 2 or k_params is None:
        return None
    import math

    return float(n_rows) * math.log(rmse * rmse) + float(k_params) * math.log(float(n_rows))


def append_run_boundary_telemetry(
    workspace_dir: Path,
    payload: dict,
) -> None:
    """Append a run-boundary record to ``iteration_telemetry.jsonl``.

    Run-boundary records are emitted at run start and run end with
    ``record_type`` ∈ {"run_start", "run_end"}. They share the same
    file as iteration records so a postmortem analyzer reads one stream.
    """
    _append_json_dict(workspace_dir / "iteration_telemetry.jsonl", payload)


def append_iteration_telemetry(
    workspace_dir: Path,
    *,
    run_id: int,
    iteration_index: int,
    iteration_start_utc: str,
    loop_control_action: str,
    score: int | None,
    score_improved: bool,
    champion_promoted: bool,
    stagnation_count: int,
    gate_engagement: bool,
    gate_failure_count: int,
    failed_gate_ids: list[str],
    escalation_flags: dict,
    falsification_mode: str,
    mutator_model_id: str,
    judge_model_id: str,
    mutator_usage: dict,
    judge_usage: dict,
    pending_loop_action: str,
    information_yield_rationale: str | None = None,
    raw_judge_score: int | None = None,
    score_cap_reason: str | None = None,
    score_cap_source: str | None = None,
    mutator_effective_model_ids: list[str] | None = None,
    mutator_fallback_events: list[dict[str, str]] | None = None,
    gp180_telemetry: dict | None = None,
) -> None:
    """Append one per-iteration record to ``iteration_telemetry.jsonl``
    + persist a structured per-iter ``cap_kind_iter_NNN.json`` artifact
    (GP-183 phase A5).

    Note on the ``run_id`` parameter: this used to read a module-level
    ``RUN_ID`` global from autoresearch_loop. Phase 4g extraction lifts
    it to an explicit kwarg so the function is no longer coupled to
    autoresearch_loop's import-time state. The autoresearch_loop call
    sites pass ``run_id=RUN_ID`` from the same enclosing scope.
    """
    iteration_end_utc = utc_now_iso()

    # If caller didn't pass GP-180 telemetry, read the per-iter artifact
    # the dispatch wrote. Keeps the call sites simple — the dispatch
    # writes once, every telemetry call site reads if not overridden.
    if gp180_telemetry is None:
        _gp180_artifact = workspace_dir / "gp180_telemetry_latest.json"
        if _gp180_artifact.exists():
            try:
                gp180_telemetry = json.loads(_gp180_artifact.read_text())
            except (OSError, json.JSONDecodeError):
                gp180_telemetry = None

    compression_progress = collect_compression_progress_inputs(workspace_dir)
    payload = {
        "record_type": "iteration",
        "run_id": run_id,
        "iteration_index": iteration_index,
        "iteration_start_utc": iteration_start_utc,
        "iteration_end_utc": iteration_end_utc,
        "wall_clock_seconds": round(
            max(
                0.0,
                datetime.fromisoformat(iteration_end_utc).timestamp()
                - datetime.fromisoformat(iteration_start_utc).timestamp(),
            ),
            6,
        ),
        "loop_control_action": loop_control_action,
        "score": score,
        "raw_judge_score": raw_judge_score,
        "score_cap_reason": score_cap_reason,
        "score_cap_source": score_cap_source or "",
        # GP-183 phase A5: cap-kind classification (gaming /
        # physics_violation / generalization_gap / holdout_miss /
        # numerical_failure / none / unknown). Computed inline so
        # post-run analysis can filter iters by cap kind without
        # re-parsing the cap_reason prose every time.
        "cap_kind": (
            (
                lambda: __import__(
                    "src.ztare.orchestrator.cap_kind",
                    fromlist=["classify_cap_kind"],
                ).classify_cap_kind(score_cap_reason)
            )()
            if score_cap_reason
            else "none"
        ),
        "score_improved": score_improved,
        "champion_promoted": champion_promoted,
        "stagnation_count": stagnation_count,
        "gate_engagement": gate_engagement,
        "gate_failure_count": gate_failure_count,
        "failed_gate_ids": failed_gate_ids,
        "escalation_flags": escalation_flags,
        "falsification_mode": falsification_mode,
        "mutator_model_id": mutator_model_id,
        "mutator_effective_model_ids": list(mutator_effective_model_ids or []),
        "mutator_fallback_events": list(mutator_fallback_events or []),
        "judge_model_id": judge_model_id,
        "mutator_usage": {
            "input_tokens": mutator_usage["input_tokens"],
            "output_tokens": mutator_usage["output_tokens"],
            "cache_read_tokens": mutator_usage["cache_read_tokens"],
            "cache_write_tokens": mutator_usage["cache_write_tokens"],
            "thinking_tokens": mutator_usage.get("thinking_tokens", 0),
        },
        "judge_usage": {
            "input_tokens": judge_usage["input_tokens"],
            "output_tokens": judge_usage["output_tokens"],
            "cache_read_tokens": judge_usage["cache_read_tokens"],
            "cache_write_tokens": judge_usage["cache_write_tokens"],
            "thinking_tokens": judge_usage.get("thinking_tokens", 0),
        },
        "estimated_cost_usd": combined_iteration_cost_usd(mutator_usage, judge_usage),
        "pending_loop_action": pending_loop_action,
        "information_yield_rationale": information_yield_rationale or "",
        "compression_progress": compression_progress,
        # GP-180 declaration-adoption telemetry (2026-04-28). Tracks whether
        # the mutator engaged the Lagrangian declaration on this
        # iter and how the apparatus processed it. Used by the
        # Noether-gaming-streak detector and by post-run analysis.
        "gp180": gp180_telemetry
        or {
            "lagrangian_declared": False,
            "derivation_success": False,
            "noether_kept": 0,
            "noether_dropped_degenerate": 0,
            "noether_weak": 0,
        },
    }
    payload["compression_progress_advice"] = compression_progress_advice_for_iteration(
        workspace_dir,
        payload,
    )
    _append_json_dict(workspace_dir / "iteration_telemetry.jsonl", payload)
    # GP-183 phase A5: persist per-iter cap-kind as a structured JSON
    # alongside the telemetry append so external tools (Research
    # Director scripts, paper draft generators) can read it without
    # re-parsing JSONL.
    try:
        cap_kind_artifact = {
            "iteration_index": iteration_index,
            "score": score,
            "raw_judge_score": raw_judge_score,
            "score_cap_reason": score_cap_reason,
            "score_cap_source": score_cap_source or "",
            "cap_kind": payload.get("cap_kind"),
            "champion_promoted": champion_promoted,
            "score_improved": score_improved,
        }
        (workspace_dir / f"cap_kind_iter_{iteration_index:03d}.json").write_text(
            json.dumps(cap_kind_artifact, indent=2, default=str)
        )
    except OSError:
        pass
