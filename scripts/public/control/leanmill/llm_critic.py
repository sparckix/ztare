#!/usr/bin/env python3
"""LLM-assisted LeanMill local-optimum critic.

Deterministic scripts are good at counting queues. They are weak at noticing
that the mill is optimizing the wrong thing. This script prepares a compact,
file-backed state packet and prompt for a fast model to critique the operating
system: bottlenecks, local optima, false progress, and the next highest-yield
interventions.

The script is deliberately read-only. It may optionally invoke `codex exec`,
but it never runs Lean, mutates official records, or changes mill state.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import textwrap
import time
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "src").exists() and (parent / "analytics/public/leanmill").exists():
            return parent
    raise RuntimeError(f"could not find repo root from {here}")


REPO = _repo_root()
DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_AXES_JSON = f"{DEFAULT_DATA_DIR}/critic_axes.json"


def _canonical_axes_sha256(obj: dict[str, Any]) -> str:
    """Canonical hash of the critic-axes JSON, computed with the axes_sha256
    field set to empty string. This is the same scheme the operator uses at
    pin-time, so verification re-does the same normalisation and compares to
    the stored pin."""
    import hashlib
    obj_for_hash = dict(obj)
    obj_for_hash["axes_sha256"] = ""
    canonical = json.dumps(obj_for_hash, sort_keys=True, indent=2)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# 2026-05-23: the canonical axis list now lives in
# ``analytics/public/leanmill/dashboard_data/critic_axes.json``
# with an axes_sha256 pin (mirroring the Evaluation Harness contract). The
# Python fallback below is kept for environments where the JSON is unreachable
# (self-test, isolated import); the JSON wins when both are present.

# Fallback axis list — MUST stay in sync with critic_axes.json. If the JSON
# is missing or its SHA does not verify, the critic will use this list and
# emit a warning in the run output so operators can reconcile.
_FALLBACK_MANDATORY_AXES = [
    "objective_function_and_science_yield",
    "source_generation_and_lead_quality",
    "source_qualification_and_canary_readiness",
    "source_action_fit",
    "proof_execution_runtime_and_batch_size",
    "governance_gate_capacity_and_false_positive_controls",
    "residual_classification_and_post_probe_triage_conversion",
    "repair_family_specs_and_registry_evidence",
    "heldout_promotion_readiness_and_family_registry_health",
    "infra_freeze_gate_and_pre_registration_compliance",
    "evaluation_harness_readiness_and_benchmark_gating",
    "telemetry_dashboard_and_operator_visibility",
    "local_remote_utilization_and_concurrency",
    "novelty_tautology_and_credit_assignment",
]


def _load_critic_axes(path: str | Path | None = None) -> tuple[list[str], dict[str, Any]]:
    """Load the mandatory critic axis list from the versioned JSON, verifying
    its SHA against the pinned ``axes_sha256``. Returns (axes_list, receipt)
    where receipt records whether the JSON was found and whether the pin
    verified.

    Falls back to the in-module ``_FALLBACK_MANDATORY_AXES`` if the JSON is
    missing or unreadable. The receipt always tells the caller which source
    was used.
    """
    p = Path(path) if path else Path(REPO) / DEFAULT_AXES_JSON
    if not p.exists() or not p.is_file():
        return list(_FALLBACK_MANDATORY_AXES), {
            "source": "fallback",
            "reason": "critic_axes.json missing",
            "path": str(p),
        }
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError as exc:
        return list(_FALLBACK_MANDATORY_AXES), {
            "source": "fallback",
            "reason": f"critic_axes.json unreadable: {exc}",
            "path": str(p),
        }
    if not isinstance(obj, dict):
        return list(_FALLBACK_MANDATORY_AXES), {
            "source": "fallback",
            "reason": "critic_axes.json is not a JSON object",
            "path": str(p),
        }
    pinned = str(obj.get("axes_sha256") or "")
    actual = _canonical_axes_sha256(obj) if pinned else ""
    axes_field = obj.get("axes") or []
    names = [str(item.get("name")) for item in axes_field if isinstance(item, dict) and item.get("name")]
    if not names:
        return list(_FALLBACK_MANDATORY_AXES), {
            "source": "fallback",
            "reason": "critic_axes.json has no axes",
            "path": str(p),
        }
    receipt = {
        "source": "critic_axes.json",
        "path": str(p),
        "schema": obj.get("schema"),
        "axes_sha256_pinned": pinned,
        "axes_sha256_actual": actual,
        "axes_sha256_verified": bool(pinned) and pinned == actual,
        "axis_count": len(names),
    }
    return names, receipt


MANDATORY_AXES, _AXES_RECEIPT = _load_critic_axes()


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {"missing": str(path)}
    try:
        return json.loads(path.read_text(errors="ignore"))
    except json.JSONDecodeError as exc:
        return {"unreadable": str(path), "error": str(exc)}


def _read_text_tail(path: Path, chars: int = 4000) -> str:
    if not path.exists():
        return f"MISSING {path}"
    text = path.read_text(errors="ignore")
    return text[-chars:]


def _mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return None


def _compact(obj: Any, max_chars: int) -> str:
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
    if len(text) <= max_chars:
        return text
    return text[: max_chars // 2] + "\n...TRUNCATED...\n" + text[-max_chars // 2 :]


def _top_items(items: Any, n: int = 8) -> list[Any]:
    if not isinstance(items, list):
        return []
    return items[:n]


def _source_quality_summary(data: dict[str, Any], path: Path) -> dict[str, Any]:
    rows = data.get("rows") if isinstance(data, dict) else []
    ready_rows = [r for r in rows or [] if isinstance(r, dict) and r.get("canary_ready")]
    blockers: dict[str, int] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        for reason, count in row.get("top_reject_reasons") or []:
            blockers[str(reason)] = blockers.get(str(reason), 0) + int(count or 0)
    return {
        "artifact": str(path),
        "mtime": _mtime(path),
        "label": data.get("label"),
        "bottleneck": data.get("bottleneck"),
        "rates": data.get("rates"),
        "row_stage_counts": data.get("row_stage_counts"),
        "ready_row_count": len(ready_rows),
        "sample_ready_rows": [r.get("row_id") for r in ready_rows[:10]],
        "top_reject_reasons": sorted(blockers.items(), key=lambda x: x[1], reverse=True)[:8],
        "interpretation": data.get("interpretation"),
    }


def _residual_family_summary(data: dict[str, Any], path: Path) -> dict[str, Any]:
    packets = data.get("packets") if isinstance(data, dict) else []
    out = []
    for p in packets or []:
        if not isinstance(p, dict):
            continue
        out.append({
            "repair_family": p.get("repair_family"),
            "state": p.get("state"),
            "lead_count": p.get("lead_count"),
            "row_count": p.get("row_count"),
            "next_action": p.get("next_action"),
            "rows": _top_items(p.get("rows") or [r.get("row_id") for r in p.get("selected_rows") or [] if isinstance(r, dict)], 6),
            "top_candidates": _top_items([
                {
                    "row_id": lead.get("row_id"),
                    "candidate_name": lead.get("candidate_name"),
                    "score": lead.get("score"),
                }
                for lead in p.get("top_leads") or []
                if isinstance(lead, dict)
            ], 6),
        })
    return {
        "artifact": str(path),
        "mtime": _mtime(path),
        "family_count": data.get("family_count") or data.get("packet_count"),
        "ready_packet_count": data.get("ready_packet_count"),
        "families_with_leads": data.get("families_with_leads"),
        "packets": out,
    }


def _ops_timeseries_summary(data: dict[str, Any], path: Path) -> dict[str, Any]:
    buckets = data.get("buckets") if isinstance(data, dict) else []
    return {
        "artifact": str(path),
        "mtime": _mtime(path),
        "summary": data.get("summary"),
        "time_window": data.get("time_window"),
        "bucket_count": len(buckets or []),
        "last_buckets": _top_items((buckets or [])[-5:], 5),
        "lanes": _top_items(data.get("lanes"), 12),
        "intake_snapshot": data.get("intake_snapshot"),
    }


def _artifact(path: Path, data: Any, summary: Any | None = None) -> dict[str, Any]:
    return {
        "artifact": str(path),
        "mtime": _mtime(path),
        "content": summary if summary is not None else data,
    }


def _curated_dashboard(data_dir: Path) -> dict[str, Any]:
    def j(name: str) -> tuple[Path, Any]:
        p = data_dir / name
        return p, _read_json(p)

    status_p, status = j("status_final.json")
    p0_p, p0 = j("p0_rollup_final.json")
    live_p, live = j("factory_live_state.json")
    insights_p, insights = j("ops_insights.json")
    ts_p, timeseries = j("ops_timeseries.json")
    score_p, scoreboard = j("scoreboard_final.json")
    source_status_p, source_status = j("source_conveyor_status.json")
    mcb_p, mcb_status = j("mcb_expansion_status.json")
    current_p, current_run = j("current_leanmill_run.json")
    source_files = sorted(data_dir.glob("source_quality*.json"))

    return {
        "status": _artifact(status_p, status),
        "p0_rollup": _artifact(p0_p, p0),
        "live_state": _artifact(live_p, live),
        "ops_insights": _artifact(insights_p, insights),
        "ops_timeseries_summary": _ops_timeseries_summary(timeseries if isinstance(timeseries, dict) else {}, ts_p),
        "scoreboard": _artifact(score_p, scoreboard, {
            "totals": scoreboard.get("totals") if isinstance(scoreboard, dict) else None,
            "notes": scoreboard.get("notes") if isinstance(scoreboard, dict) else None,
            "lanes": _top_items(scoreboard.get("lanes") if isinstance(scoreboard, dict) else [], 12),
        }),
        "source_conveyor_status": _artifact(source_status_p, source_status),
        "mcb_expansion_status": _artifact(mcb_p, mcb_status),
        "current_leanmill_run": _artifact(current_p, current_run),
        "source_quality": [
            _source_quality_summary(_read_json(p), p)
            for p in source_files
        ],
        "residual_family_source_plan": _residual_family_summary(
            _read_json(data_dir / "residual_family_source_plan.json"),
            data_dir / "residual_family_source_plan.json",
        ),
        "residual_family_canary_packets": _residual_family_summary(
            _read_json(data_dir / "residual_family_canary_packets.json"),
            data_dir / "residual_family_canary_packets.json",
        ),
        "residual_plan": _artifact(data_dir / "residual_plan_final.json", _read_json(data_dir / "residual_plan_final.json")),
    }


def _parse_extra(items: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit("--extra-json must be LABEL=PATH")
        label, path_s = item.split("=", 1)
        out[label] = _read_json(Path(path_s))
    return out


def deterministic_hints(packet: dict[str, Any]) -> dict[str, Any]:
    dashboard = packet.get("dashboard") or {}
    p0 = (dashboard.get("p0_rollup") or {}).get("content") or {}
    status = (dashboard.get("status") or {}).get("content") or {}
    live = (dashboard.get("live_state") or {}).get("content") or {}
    residual_plan = (dashboard.get("residual_plan") or {}).get("content") or {}
    source_quality = (packet.get("extra") or {}).get("source_quality") or {}
    if not source_quality and (dashboard.get("source_quality") or []):
        source_quality = (dashboard.get("source_quality") or [])[-1]
    microbatch = (packet.get("extra") or {}).get("microbatch_summary") or {}

    headline = p0.get("headline") or {}
    bottleneck = status.get("bottleneck") or {}
    source_totals = source_quality.get("totals") or {}
    micro_summary = microbatch.get("summary") or {}
    active = live.get("active_work") or []
    verified = int(headline.get("verified_value_rows") or 0)
    residual = int(headline.get("path_c_learning_rows") or 0)
    pending = int(headline.get("pending_governance") or 0)
    ready = int((bottleneck.get("ready_wip") or 0))

    risks: list[dict[str, str]] = []
    if residual > verified and not pending:
        risks.append({
            "risk": "residual_inventory_local_optimum",
            "evidence": f"{residual} residual rows vs {verified} verified rows and no governance backlog",
            "action": "promote residual families into executable canaries; do not celebrate residual count",
        })
    if int(micro_summary.get("intake_ready_total") or 0) > 0 and ready == 0:
        risks.append({
            "risk": "dashboard_or_root_staleness",
            "evidence": "microbatch has ready intake but status root may not point at it",
            "action": "critic should reason over explicit extra microbatch artifacts, not only stale dashboard root",
        })
    if int(source_totals.get("canary_ready_rows") or 0) == 0 and int(source_totals.get("source_safe_sources") or 0) > 100:
        risks.append({
            "risk": "lead_volume_without_qualified_opportunities",
            "evidence": "many source-safe leads but no canary-ready rows",
            "action": "optimize source qualification and row-context fallback, not proof workers",
        })
    if active and any("dashboard" in str(x).lower() for x in risks):
        pass

    axis_hints: list[dict[str, str]] = []
    if pending == 0:
        axis_hints.append({
            "axis": "governance_gate",
            "read": "not_current_bottleneck",
            "evidence": "pending governance queue is zero in the latest headline/status packet",
        })
    if int(micro_summary.get("intake_ready_total") or 0) > 0:
        axis_hints.append({
            "axis": "source_to_intake",
            "read": "qualified_buffer_exists",
            "evidence": f"microbatch_ready_intake={int(micro_summary.get('intake_ready_total') or 0)}",
        })
    if residual > verified:
        axis_hints.append({
            "axis": "learning_loop",
            "read": "inventory_exceeds_value",
            "evidence": f"path_c_learning_rows={residual}, verified_value_rows={verified}",
        })
    if ready == 0 and int(micro_summary.get("intake_ready_total") or 0) == 0:
        axis_hints.append({
            "axis": "entrance_buffer",
            "read": "starvation_risk",
            "evidence": "no ready WIP in dashboard root and no explicit microbatch ready intake",
        })

    suggested_next = []
    if int(micro_summary.get("intake_ready_total") or 0) > 0:
        suggested_next.append("Run scored proof/action smoke on microbatch ready rows; require positive source-action delta before broad templates.")
    if residual_plan.get("packets"):
        suggested_next.append("Drain executable repair-canary packets with negative controls; score only ratified closures or tested reusable lanes.")
    if not suggested_next:
        suggested_next.append("Acquire or qualify a small source microbatch before proof execution.")

    return {
        "obvious_station_bottleneck": bottleneck.get("current_bottleneck"),
        "known_queue_state": {
            "verified_value_rows": verified,
            "path_c_learning_rows": residual,
            "pending_governance": pending,
            "ready_wip_from_status_root": ready,
            "live_active_work_count": len(active),
            "microbatch_ready_intake": int(micro_summary.get("intake_ready_total") or 0),
        },
        "axis_hints": axis_hints,
        "local_optimum_risks": risks,
        "deterministic_next_action_hints": suggested_next,
        "limits": "These are shallow queue/ratio checks; the LLM critic must judge whether we are optimizing the wrong objective.",
    }


def build_packet(args: argparse.Namespace) -> dict[str, Any]:
    data = Path(args.data_dir)
    packet = {
        "schema": "leanmill-llm-critic-state-v1",
        "generated_at_epoch": int(time.time()),
        "objective": "maximize qualified scientific yield per wall-clock hour without false positives or false progress",
        "value_outputs": [
            "Path-B-ratified proof closure",
            "formal exact gap",
            "valid falsifier",
            "tested reusable repair lane",
            "tested retire decision",
        ],
        "non_value_outputs": [
            "raw source volume",
            "raw residual volume",
            "compile-only closure before governance",
            "dashboard/status churn",
            "repair canary using local sibling counted as source credit",
        ],
        "mandatory_review_axes": MANDATORY_AXES,
        "dashboard": _curated_dashboard(data),
        "extra": _parse_extra(args.extra_json or []),
        "summary_tail": _read_text_tail(Path(args.summary), args.summary_chars),
    }
    packet["deterministic_hints"] = deterministic_hints(packet)
    return packet


def build_prompt(packet: dict[str, Any], max_chars: int) -> str:
    state = _compact(packet, max_chars)
    return textwrap.dedent(f"""
    You are an adversarial operations-science and formal-methods reviewer for LeanMill.

    Mission: maximize qualified scientific yield per wall-clock hour without compromising validity.
    Do not optimize vanity throughput. Do not count residual volume, source volume, dashboard churn,
    or compile-only closure as value.

    Depth requirement: this is not a queue-summary task. Criticize the entire mill as a production
    research system. You must explicitly inspect each mandatory_review_axis in the state packet and
    identify local optima, hidden bottlenecks, weak interfaces, missing controls, and opportunities to
    increase time-to-insight. A generic answer like "source_action_fit is the bottleneck" is invalid
    unless it includes concrete evidence, the mechanism that creates the bottleneck, and the highest-ROI
    intervention that changes the mechanism.

    ROI discipline: rank interventions by expected scientific-yield gain per implementation hour, not
    by aesthetic cleanliness. Prefer small changes that create discriminating evidence. Every proposed
    action must name a validity guard so the mill does not create false positives, false negatives, or
    tautological progress.

    Anti-bullshit checks:
    - If an item is already implemented or already known from the state, do not present it as new.
    - If an intervention only improves visibility, label it visibility-only unless it directly changes
      scientific decisions.
    - If adding workers would not improve the constrained station, say so and name the constrained station.
    - If more data would only create more residual inventory, say so and specify the qualification gate.
    - If the dashboard state may be stale relative to explicit extra artifacts, say which artifact wins.

    Analyze the state packet below and return STRICT JSON with this schema:
    {{
      "current_local_optimum_risk": "low|medium|high",
      "main_wrong_objective_risk": "...",
      "state_packet_adequacy": {{
        "adequate_for_decision": true,
        "missing_evidence": ["..."],
        "stale_or_conflicting_artifacts": ["..."],
        "artifact_precedence_rule": "..."
      }},
      "axis_reviews_by_axis": {{
        "objective_function_and_science_yield": {{
          "status": "healthy|watch|bottleneck|confounded|unknown",
          "evidence_artifacts": ["artifact path or state field"],
          "mechanism": "...",
          "decision_implication": "...",
          "confidence": "low|medium|high",
          "unknowns": ["..."],
          "best_intervention": "...",
          "why_not_surface_level": "..."
        }},
        "... every other mandatory_review_axis key exactly once ...": {{}}
      }},
      "non_obvious_findings": [
        {{
          "finding": "...",
          "why_it_is_not_already_in_deterministic_hints": "...",
          "decision_that_would_be_wrong_without_it": "..."
        }}
      ],
      "true_current_bottleneck": "source_generation|source_qualification|source_action_fit|proof_execution|governance|residual_compiler|human_template_taste|other",
      "bottleneck_mechanism": "...",
      "stop_doing_now": ["..."],
      "highest_yield_next_actions": [
        {{
          "rank": 1,
          "action": "...",
          "roi_class": "very_high|high|medium|low",
          "why_it_10x_time_to_insight": "...",
          "validity_guard": "...",
          "expected_time_to_signal": "...",
          "files_or_artifacts_to_touch": ["..."],
          "success_signal": "...",
          "kill_or_pivot_signal": "..."
        }}
      ],
      "batch_size_and_concurrency_recommendation": {{
        "local": "...",
        "remote": "...",
        "safe_worker_count": "...",
        "reason": "..."
      }},
      "swarm_plan": [
        {{
          "lane": "...",
          "owner_type": "main|subagent|remote_compute|llm_critic",
          "non_overlap_boundary": "...",
          "done_signal": "..."
        }}
      ],
      "confounders_to_kill_before_claim": ["..."],
      "metrics_that_matter_next": ["..."],
      "metrics_to_ignore_or_demote": ["..."],
      "what_would_change_your_mind": "...",
      "decision": "continue_current_line|change_batch_size|pause_proof_execution|promote_repair_canaries|source_more|retire_current_line|other",
      "one_sentence_operator_read": "..."
    }}

    State packet:
    {state}
    """).strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise ValueError("no JSON object found")


def validate_critic_output(text: str) -> dict[str, Any]:
    errors: list[str] = []
    try:
        obj = _extract_json_object(text)
    except Exception as exc:
        return {"ok": False, "errors": [f"json_parse_failed: {exc}"]}

    axes = obj.get("axis_reviews_by_axis")
    if not isinstance(axes, dict):
        errors.append("missing axis_reviews_by_axis object")
        axes = {}
    missing = [axis for axis in MANDATORY_AXES if axis not in axes]
    extra = [axis for axis in axes if axis not in MANDATORY_AXES]
    if missing:
        errors.append(f"missing_axes: {missing}")
    if extra:
        errors.append(f"unknown_axes: {extra}")
    for axis in MANDATORY_AXES:
        review = axes.get(axis)
        if not isinstance(review, dict):
            continue
        for field in ["status", "evidence_artifacts", "mechanism", "decision_implication", "best_intervention"]:
            value = review.get(field)
            if value in (None, "", [], {}):
                errors.append(f"{axis}: empty {field}")
        if isinstance(review.get("evidence_artifacts"), list) and any(str(x).strip() in {"...", "artifact path or state field"} for x in review["evidence_artifacts"]):
            errors.append(f"{axis}: placeholder evidence_artifacts")
    if not obj.get("non_obvious_findings"):
        errors.append("missing non_obvious_findings")
    if not isinstance(obj.get("highest_yield_next_actions"), list) or not obj.get("highest_yield_next_actions"):
        errors.append("missing highest_yield_next_actions")
    return {
        "ok": not errors,
        "errors": errors,
        "axis_count": len(axes),
        "parsed_decision": obj.get("decision"),
        "parsed_bottleneck": obj.get("true_current_bottleneck"),
    }


def run_codex(prompt: str, args: argparse.Namespace) -> dict[str, Any]:
    out_path = Path(args.codex_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "-C",
        str(REPO),
        "-m",
        args.model,
        "-c",
        f'model_reasoning_effort="{args.reasoning_effort}"',
        "-s",
        "read-only",
        "-o",
        str(out_path),
        prompt,
    ]
    start = time.time()
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=args.timeout)
    out_text = _read_text_tail(out_path, 20000) if out_path.exists() else ""
    return {
        "cmd": cmd[:10] + ["...prompt"],
        "returncode": proc.returncode,
        "seconds": round(time.time() - start, 3),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "codex_out": str(out_path),
        "codex_out_tail": out_text[-8000:],
        "validation": validate_critic_output(out_text) if proc.returncode == 0 else {"ok": False, "errors": ["codex_returncode_nonzero"]},
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    packet = build_packet(args)
    prompt = build_prompt(packet, args.prompt_state_chars)
    if args.packet_out:
        Path(args.packet_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.packet_out).write_text(json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    if args.prompt_out:
        Path(args.prompt_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.prompt_out).write_text(prompt + "\n")
    result = {
        "schema": "leanmill-llm-critic-run-v1",
        "packet_out": args.packet_out,
        "prompt_out": args.prompt_out,
        "model": args.model,
        "ran_codex": bool(args.run_codex),
    }
    if args.run_codex:
        result["codex"] = run_codex(prompt, args)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return result


def _self_test() -> int:
    packet = {
        "schema": "x",
        "dashboard": {"status": {"bottleneck": {"current_bottleneck": "source_intake"}}},
        "summary_tail": "test",
    }
    prompt = build_prompt(packet, 1000)
    assert "STRICT JSON" in prompt
    assert "source_intake" in prompt
    assert "axis_reviews_by_axis" in prompt
    hints = deterministic_hints({
        "dashboard": {"p0_rollup": {"content": {"headline": {"verified_value_rows": 1, "path_c_learning_rows": 3, "pending_governance": 0}}}},
        "extra": {},
    })
    assert hints["local_optimum_risks"][0]["risk"] == "residual_inventory_local_optimum"
    good = {
        "axis_reviews_by_axis": {
            axis: {
                "status": "watch",
                "evidence_artifacts": ["x"],
                "mechanism": "m",
                "decision_implication": "d",
                "best_intervention": "b",
            }
            for axis in MANDATORY_AXES
        },
        "non_obvious_findings": [{"finding": "x"}],
        "highest_yield_next_actions": [{"rank": 1}],
        "decision": "promote_repair_canaries",
        "true_current_bottleneck": "residual_compiler",
    }
    assert validate_critic_output(json.dumps(good))["ok"]
    bad = {"axis_reviews_by_axis": {}, "highest_yield_next_actions": []}
    assert not validate_critic_output(json.dumps(bad))["ok"]
    print("leanmill_llm_critic self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--summary", default="analytics/public/leanmill/research_log.md")
    ap.add_argument("--summary-chars", type=int, default=12000)
    ap.add_argument("--extra-json", action="append", default=[], help="LABEL=PATH JSON artifact to include.")
    ap.add_argument("--packet-out", default="/tmp/rung1/leanmill_llm_critic_packet.json")
    ap.add_argument("--prompt-out", default="/tmp/rung1/leanmill_llm_critic_prompt.txt")
    ap.add_argument("--out", default="/tmp/rung1/leanmill_llm_critic_run.json")
    ap.add_argument("--prompt-state-chars", type=int, default=140000)
    ap.add_argument("--model", default="gpt-5.4-mini")
    ap.add_argument("--reasoning-effort", default="medium", choices=["low", "medium", "high", "xhigh"])
    ap.add_argument("--run-codex", action="store_true")
    ap.add_argument("--codex-out", default="/tmp/rung1/leanmill_llm_critic_codex.txt")
    ap.add_argument("--timeout", type=int, default=360)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    print(json.dumps(run(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
