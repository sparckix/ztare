import os
import json
import importlib
import importlib.util
import subprocess
import time
import shutil
import ast
import atexit
import signal
from pathlib import Path
import argparse
import sys
from datetime import datetime, timezone
import concurrent.futures
from google.genai import types
from src.ztare.common import utils
from src.ztare.common.llm_runtime import (
    LLMRuntime,
    PRODUCTION_CALL_RETRIES,
    resolve_model_id,
    resolve_director_model_id,
    pricing_model_name,
)
from src.ztare.common.paths import PROJECTS_DIR, RUBRICS_DIR
import re
from src.ztare.primitives.primitive_library import format_transfer_hypotheses, retrieve_primitives
from src.ztare.validator.mutation_contract import (
    MutationMismatchCode,
    approved_primitive_keys,
    evaluate_mutation_declaration,
    parse_mutation_declaration,
)
from src.ztare.validator.runner_selection import CandidateScopeVerdict, evaluate_candidate_selection
from src.ztare.validator.v4_family import is_v4_family_project
from src.ztare.validator.information_yield import (
    IterationSignal,
    LoopControlAction,
    apply_latent_motion_veto,
    evaluate_information_yield,
)
from src.ztare.validator.pivot_heuristics import select_pivot_profile
from src.ztare.catch_grammar.rule_3_profile_check import check_profile_contains
from src.ztare.gates.structural_constraint_extractor import (
    run_structural_extractor,
)
from src.ztare.motion.trajectory_thrash_detector import (
    run_trajectory_thrash_detector,
)
from src.ztare.gates.negative_space_extractor import (
    run_negative_space_extractor,
)
from src.ztare.gates.derived_constraints import (
    render_confirmed_constraints_prompt_section,
    sanitize_constraint_proposals,
    update_derived_constraints_ledger,
    write_derived_constraints_brief,
)
from src.ztare.fit.mutation_suite_guard import validate_python_suite_candidate
from src.ztare.validator.charter_parsing import (
    extract_anchor_proxies_from_charter,
    extract_forecast_type_from_charter,
)
from src.ztare.supervisor.supervisor_usage import estimate_cost_usd, load_model_pricing
from src.ztare.validator.champion_artifacts import (
    artifact_regime_fingerprint,
    build_champion_eval_from_saved_best,
    build_champion_gap_payload_from_saved_best,
    champion_artifacts_out_of_sync_with_saved_best,
    set_artifact_role,
)
from src.ztare.motion.latent_distance import (
    record_latent_distance,
    summarize_recent_latent_motion,
)
from src.ztare.fit.fit_primitive import (
    FitDeclaration,
    FitFailure,
    FitSuccess,
    diagnose_residual_pattern,
    fit_parameters,
    fit_result_to_json,
    format_diagnostic_for_prompt,
    format_residual_map_for_prompt,
    format_residual_surface_for_prompt,
    parse_fit_declaration,
    substitute_fitted_params,
)
from src.ztare.composition.structural_memory import (
    detect_additive_composite_opportunity,
    generate_additive_composite_seeds,
    render_structural_memory_prompt_section,
    update_structural_memory,
)
from src.ztare.composition.topology_synthesizer import (
    detect_feynman_wall,
    run_composition_loop,
)
from src.ztare.fit.fit_declaration_retry import (
    validate_and_retry_fit_declaration,
)
from src.ztare.reports.gp048_feedback import (
    render_farther_tail_veto_prompt_section,
    render_primitive_cohort_prompt_section,
    write_telemetry_line,
)
from src.ztare.motion.residual_analyzer import (
    ShapeDescriptor,
    analyze_residual,
    format_descriptor_for_prompt,
    reset_stagnation_on_holdout_pass,
)
from src.ztare.gates.corrector_library import filter_by_descriptor
from src.ztare.validator.predictive_divergence_sweep import (
    run_sweep as run_divergence_sweep,
)
from src.ztare.rubrics.review_rubric import review_exit_code, run_rubric_review
from src.ztare.gates.global_gates import run_global_gates, merge_into_score_contract

SESSION_TOKENS = 0
SESSION_MUTATOR_USAGE = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "thinking_tokens": 0,
    "estimated_cost_usd": 0.0,
    "cost_known": False,
}
SESSION_MUTATOR_MODELS_USED: set[str] = set()
SESSION_MUTATOR_FALLBACK_EVENTS: list[dict[str, str]] = []
SESSION_JUDGE_USAGE = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "thinking_tokens": 0,
    "estimated_cost_usd": 0.0,
    "cost_known": False,
}

# 1. Setup CLI Arguments
parser = argparse.ArgumentParser()
parser.add_argument("--project", required=True)
parser.add_argument("--rubric", required=True)
parser.add_argument("--dynamic", action="store_true")
parser.add_argument("--iters", type=int, default=10, help="Number of iterations to run")
parser.add_argument(
    "--disable_attacker_tools",
    action="store_true",
    help=(
        "Forward --disable_attacker_tools to test_thesis.py. Disables Gemini "
        "automatic function calling in the single-attacker fallback path and "
        "prevents attacker-authored python from running under any tool-use "
        "config. Belt-and-suspenders alongside the hardened execute_python_code "
        "sandbox. Phase-2 paired A/B runs should always set this."
    ),
)
parser.add_argument(
    "--disable-negative-space-extractor",
    action="store_true",
    help=(
        "GP-061.B live-harvest discipline: skip Component B (negative space extractor) "
        "post-eval hook entirely. Used during cold-harvest runs where Component B output "
        "must not contaminate derived_constraints.json while a corpus of failed families "
        "is being gathered for a separate cold test. See "
        "research_areas/private/specs/active/GP-061_component_b_generalization_target_spec.md."
    ),
)
parser.add_argument(
    "--auto-evolve",
    action="store_true",
    help="Level 5: AI autonomously rewrites its rubric upon reaching a high score.",
)
parser.add_argument(
    "--mutator_model",
    type=str,
    default="gemini",
    choices=["gemini", "gemini-lite", "gemini-pro", "claude", "claude-opus", "gpt4o", "gpt4.1", "gpt4.1-mini"],
    help="Model family to use as Mutator.",
)
parser.add_argument(
    "--judge_model",
    type=str,
    default="gemini",
    choices=["gemini", "gemini-lite", "gemini-pro", "claude", "claude-opus", "gpt4o", "gpt4.1", "gpt4.1-mini"],
    help="Model family to use as Firing Squad and Meta-Judge.",
)
parser.add_argument(
    "--use_primitives",
    action="store_true",
    help="Retrieve approved adversarial precedents for attacker/judge prompts.",
)
parser.add_argument(
    "--use_mutator_primitives",
    action="store_true",
    help="Also expose retrieved transfer hypotheses to the mutator. Off by default.",
)
parser.add_argument(
    "--use_transfer_hypotheses",
    action="store_true",
    help="Alias for --use_mutator_primitives. Expose retrieved transfer hypotheses to the mutator.",
)
parser.add_argument(
    "--primitive_top_k",
    type=int,
    default=3,
    help="Maximum number of approved primitives to retrieve when primitive support is enabled.",
)
parser.add_argument(
    "--deterministic_score_gates",
    action="store_true",
    help="Use Python-enforced hard score gates in test_thesis.py instead of trusting raw LLM scores.",
)
parser.add_argument(
    "--runner_r1_contract",
    action="store_true",
    help="Require a declaration-first MutationDeclaration header before each mutator thesis body.",
)
parser.add_argument(
    "--no_model_fallback",
    action="store_true",
    help=(
        "Hard-lock the runtime model family: disable all cross-provider "
        "fallback in llm_runtime.call_text. On primary-model failure the "
        "run will raise instead of silently switching to another family. "
        "Required for pre-registered experiments where runtime family is sealed."
    ),
)
parser.add_argument(
    "--underidentified_after",
    type=int,
    default=None,
    help=(
        "Minimum catastrophic-streak length (in iterations) before the "
        "UNDERIDENTIFIED exit fires in bounded_discriminator mode. Defaults "
        "to pivot_after=3 (legacy behavior). Set higher for pre-registered "
        "experiments that require sustained starvation before UNDERIDENTIFIED "
        "is a valid conclusion — otherwise the exit fires before the pivot has "
        "had any chance to produce structural moves."
    ),
)
parser.add_argument(
    "--run-mode",
    type=str,
    default="factory",
    dest="run_mode",
    help=(
        "Declared operating mode for this run: 'factory' (tight rubric, GP-054 pre-run, "
        "short iteration budget) or 'honeypot' (loose rubric, no pre-run, long iteration "
        "budget for discovery). Written to run_start telemetry. Accepts any string so "
        "future modes (e.g. 'sandbox') work without code changes."
    ),
)
parser.add_argument(
    "--rubric_review_before_run",
    action="store_true",
    help=(
        "Run GP-054 pre-run rubric review before iteration 1 and abort the loop "
        "if scenario validity fails or any structural rubric checks fail."
    ),
)
args = parser.parse_args()
if args.no_model_fallback:
    os.environ["ZTARE_DISABLE_MODEL_FALLBACK"] = "1"
    print(
        "🔒 Model fallback DISABLED (--no_model_fallback). "
        "Runtime will fail loudly on primary-model errors rather than "
        "switch families. This is the correct mode for sealed pre-registered runs."
    )
if getattr(args, "use_transfer_hypotheses", False):
    args.use_mutator_primitives = True
if args.use_mutator_primitives:
    args.use_primitives = True
if is_v4_family_project(args.project) and not args.deterministic_score_gates:
    args.deterministic_score_gates = True
    print(f"INFO: Enforcing --deterministic_score_gates for V4-family project [{args.project}].")
if is_v4_family_project(args.project) and not args.runner_r1_contract:
    args.runner_r1_contract = True
    print(f"INFO: Enforcing --runner_r1_contract for V4-family project [{args.project}].")

RUNTIME = LLMRuntime()

# Keep legacy `client` pointing to Gemini — Firing Squad and Meta-Judge always use it
client = RUNTIME.require_gemini_client()


def _load_v4_stage_index() -> int | None:
    if not is_v4_family_project(args.project):
        return None
    state_path = Path("projects") / args.project / "meta_runner_state.json"
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text()).get("current_stage")
    except Exception:
        return None

ITERATIONS = args.iters

# Resolve Mutator model ID from --mutator_model flag
MUTATOR_MODEL_ID = resolve_model_id(args.mutator_model)
JUDGE_MODEL_ID = resolve_model_id(args.judge_model)
# Escalation model follows the mutator family
DIRECTOR_MODEL_ID = resolve_director_model_id(args.mutator_model)

print(f"🧠 Mutator: {MUTATOR_MODEL_ID} | Judge: {JUDGE_MODEL_ID}")

# Paths
PROJECT_DIR = str(PROJECTS_DIR / args.project)
HISTORY_DIR = f"{PROJECT_DIR}/history"
THESIS_PATH = f"{PROJECT_DIR}/thesis.md"
WORKING_PATH = f"{PROJECT_DIR}/current_iteration.md"
EVIDENCE_PATH = f"{PROJECT_DIR}/evidence.txt"
AXIOM_PATH = f"{PROJECT_DIR}/verified_axioms.json"
PROJECT_CHARTER_PATH = f"{PROJECT_DIR}/project_charter.md"
LATEST_EVAL_RESULTS_PATH = f"{PROJECT_DIR}/latest_eval_results.json"
CHAMPION_EVAL_RESULTS_PATH = f"{PROJECT_DIR}/champion_eval_results.json"
LATEST_PROBABILITY_DAG_PATH = f"{PROJECT_DIR}/latest_probability_dag.json"
CHAMPION_PROBABILITY_DAG_PATH = f"{PROJECT_DIR}/champion_probability_dag.json"
LATEST_EVIDENCE_GAPS_PATH = f"{PROJECT_DIR}/workspace/latest_evidence_gaps.json"
CHAMPION_EVIDENCE_GAPS_PATH = f"{PROJECT_DIR}/workspace/champion_evidence_gaps.json"
LATEST_CONSTRAINT_PROPOSALS_PATH = f"{PROJECT_DIR}/workspace/latest_constraint_proposals.json"
DERIVED_CONSTRAINTS_PATH = f"{PROJECT_DIR}/workspace/derived_constraints.json"
DERIVED_CONSTRAINTS_BRIEF_PATH = f"{PROJECT_DIR}/workspace/derived_constraints_brief.md"
MAIN_RUBRIC_PATH = RUBRICS_DIR / f"{args.rubric}.json"
BEST_ITERATION_RE = re.compile(r"best_iteration:\s*([A-Za-z0-9_.-]+)")
HISTORY_SCORE_RE = re.compile(r"_score_(\d+)_")

def read_file(filepath):
    with open(filepath, "r") as f:
        return f.read()


def write_file(filepath, content):
    with open(filepath, "w") as f:
        f.write(content)


def read_json(filepath: str) -> dict | None:
    path = Path(filepath)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def write_json(filepath: str, payload: dict) -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(filepath: str, payload: dict) -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _pop_seed_queue(workspace_dir: Path, injected: bool) -> None:
    """Pop the front of the Component D seed queue after a failed iteration.

    Called from every early-exit path (R1 exception, R1 mismatch, R3 rejection,
    subprocess crash) to prevent infinite retry of a crashing candidate.
    On success the queue is cleared entirely (handled separately).
    """
    if not injected:
        return
    _seed_file = workspace_dir / "composition_seed.json"
    if not _seed_file.exists():
        return
    try:
        _q = json.loads(_seed_file.read_text())
        if isinstance(_q, list) and len(_q) > 1:
            _q.pop(0)
            _seed_file.write_text(json.dumps(_q, indent=2) + "\n")
            print(f"    🧬 Seed queue: popped failed candidate, {len(_q)} remaining")
        else:
            _seed_file.unlink()
            print("    🧬 Seed queue exhausted (all candidates tested)")
    except Exception:
        _seed_file.unlink()


def _format_sweep_context(sweep_state: dict) -> str:
    """Format GP-076 sweep state for mutator prompt injection."""
    if not sweep_state:
        return ""
    parts: list[str] = []
    if sweep_state.get("library_exhausted"):
        parts.append(
            "GP-076 DIVERGENCE SWEEP — LIBRARY EXHAUSTED:\n"
            "The deterministic corrector library has been fully searched. "
            "No library form survived the holdout gate. You must propose a "
            "NOVEL functional form for the corrector — do not reuse any "
            "standard form (step, heaviside, round, floor, ceil, etc.).\n"
        )
    query_history = sweep_state.get("query_history", [])
    if query_history:
        parts.append("GP-076 DIVERGENCE QUERY OBSERVATIONS (verified data points):")
        # Accumulate surviving forms across all queries (intersection)
        all_surviving: list[str] | None = None
        for q in query_history:
            surviving = q.get("surviving_forms", [])
            k_vals = q.get("surviving_k_values", {})
            k_str = ""
            if k_vals:
                k_str = "  fitted k: " + ", ".join(
                    f"{form}→k={k:.4f}" for form, k in k_vals.items()
                )
            parts.append(
                f"  corrector(v={q['query_v']}) = {q['observed']}  "
                f"[eliminated {len(q.get('eliminated', []))} candidates, "
                f"{q.get('survivors_after', '?')} remain: {surviving}]{k_str}"
            )
            if all_surviving is None:
                all_surviving = list(surviving)
            else:
                all_surviving = [s for s in all_surviving if s in surviving]
        parts.append(
            "These observations are confirmed experimental results. "
            "Your proposed corrector MUST match these values exactly.\n"
        )
        if all_surviving:
            parts.append(
                "SURVIVING LIBRARY FORMS (consistent with all query observations):\n"
                + "\n".join(f"  - {f}" for f in all_surviving)
                + "\n\nDIRECT INSTRUCTION: Fit the surviving form(s) above to the visible "
                "corrector data to find the best free parameter k. Do NOT invent a new "
                "topology — use one of the surviving forms exactly. Show your derivation "
                "of k from visible (v, corrector) pairs and verify it matches all query "
                "observations before writing the final expression.\n"
            )
    return "\n".join(parts)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _usage_bucket_snapshot(bucket: dict) -> dict:
    return {
        "input_tokens": int(bucket.get("input_tokens", 0) or 0),
        "output_tokens": int(bucket.get("output_tokens", 0) or 0),
        "cache_creation_input_tokens": int(bucket.get("cache_creation_input_tokens", 0) or 0),
        "cache_read_input_tokens": int(bucket.get("cache_read_input_tokens", 0) or 0),
        "thinking_tokens": int(bucket.get("thinking_tokens", 0) or 0),
        "estimated_cost_usd": float(bucket.get("estimated_cost_usd", 0.0) or 0.0),
        "cost_known": bool(bucket.get("cost_known", False)),
    }


def _usage_delta(before: dict, after: dict) -> dict:
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


def _combined_iteration_cost_usd(mutator_usage: dict, judge_usage: dict) -> float | None:
    total = 0.0
    for usage in (mutator_usage, judge_usage):
        if not usage.get("has_usage", False):
            continue
        if not usage.get("cost_known", False):
            return None
        total += float(usage.get("estimated_cost_usd", 0.0) or 0.0)
    return round(total, 6)


def _extract_iteration_gate_metrics(evaluation: dict | None) -> tuple[bool, int, list[str]]:
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


def _extract_iteration_escalation_flags(evaluation: dict | None) -> dict:
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


def _current_loop_control_action(
    *,
    pending_loop_action,
    dynamic_enabled: bool,
    is_v4_project: bool,
    stagnation_count: int,
) -> str:
    if dynamic_enabled and pending_loop_action in {
        LoopControlAction.REFRESH_SPECIALISTS,
        LoopControlAction.PIVOT_REQUIRED,
    }:
        return "refresh_specialists"
    if is_v4_project and stagnation_count >= 3:
        return "stagnation_pivot"
    if stagnation_count >= 4:
        return "emergency_pivot"
    if stagnation_count >= 3:
        return "stagnation_pivot"
    return "normal"


def _append_run_boundary_telemetry(
    workspace_dir: Path,
    payload: dict,
) -> None:
    append_jsonl(str(workspace_dir / "iteration_telemetry.jsonl"), payload)


def _append_iteration_telemetry(
    workspace_dir: Path,
    *,
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
) -> None:
    iteration_end_utc = _utc_now_iso()
    payload = {
        "record_type": "iteration",
        "run_id": RUN_ID,
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
        "score_improved": score_improved,
        "champion_promoted": champion_promoted,
        "stagnation_count": stagnation_count,
        "gate_engagement": gate_engagement,
        "gate_failure_count": gate_failure_count,
        "failed_gate_ids": failed_gate_ids,
        "escalation_flags": escalation_flags,
        "falsification_mode": falsification_mode,
        "mutator_model_id": mutator_model_id,
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
        "estimated_cost_usd": _combined_iteration_cost_usd(mutator_usage, judge_usage),
        "pending_loop_action": pending_loop_action,
    }
    append_jsonl(str(workspace_dir / "iteration_telemetry.jsonl"), payload)


def _strip_best_iteration_marker(text: str) -> str:
    cleaned = re.sub(r"\n\n<!--\s*best_iteration:\s*[A-Za-z0-9_.-]+\s*-->\s*$", "", text)
    return cleaned.rstrip()


def _current_saved_best_stem() -> str | None:
    if not os.path.exists(THESIS_PATH):
        return None
    match = BEST_ITERATION_RE.search(read_file(THESIS_PATH))
    if not match:
        return None
    return match.group(1)


def _current_saved_best_score() -> int | None:
    history_stem = _current_saved_best_stem()
    if not history_stem:
        return None
    meta_path = Path(HISTORY_DIR) / f"{history_stem}_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(read_file(str(meta_path)))
            score = meta.get("score")
            return int(score) if score is not None else None
        except Exception:
            pass
    match = HISTORY_SCORE_RE.search(history_stem)
    if not match:
        return None
    return int(match.group(1))


def _current_saved_best_meta() -> dict | None:
    history_stem = _current_saved_best_stem()
    if not history_stem:
        return None
    meta_path = Path(HISTORY_DIR) / f"{history_stem}_meta.json"
    if not meta_path.exists():
        return None
    try:
        payload = json.loads(read_file(str(meta_path)))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _score_regime_fingerprint_from_score_contract(score_contract) -> str | None:
    if not isinstance(score_contract, dict):
        return None
    fingerprint = score_contract.get("regime_fingerprint")
    if isinstance(fingerprint, str) and fingerprint.strip():
        return fingerprint.strip()
    return None


def _score_regime_fingerprint_from_meta(meta: dict | None) -> str | None:
    if not isinstance(meta, dict):
        return None
    fingerprint = meta.get("score_regime_fingerprint")
    if isinstance(fingerprint, str) and fingerprint.strip():
        return fingerprint.strip()
    score_contract = meta.get("score_contract")
    return _score_regime_fingerprint_from_score_contract(score_contract)


def _saved_best_comparison_anchor(current_eval: dict) -> dict:
    raw_saved_score = _current_saved_best_score()
    if raw_saved_score is None:
        return {
            "compare_score": None,
            "raw_saved_score": None,
            "status": "none",
            "label": "none",
        }

    current_fingerprint = _score_regime_fingerprint_from_score_contract(
        current_eval.get("score_contract")
    )
    if current_fingerprint is None:
        return {
            "compare_score": raw_saved_score,
            "raw_saved_score": raw_saved_score,
            "status": "current_regime_unknown",
            "label": str(raw_saved_score),
        }

    saved_meta = _current_saved_best_meta()
    if saved_meta is None:
        return {
            "compare_score": None,
            "raw_saved_score": raw_saved_score,
            "status": "legacy_missing_meta",
            "label": f"legacy_missing_meta:{raw_saved_score}",
        }

    saved_fingerprint = _score_regime_fingerprint_from_meta(saved_meta)
    if saved_fingerprint is None:
        return {
            "compare_score": None,
            "raw_saved_score": raw_saved_score,
            "status": "legacy_missing_regime",
            "label": f"legacy_missing_regime:{raw_saved_score}",
        }

    if saved_fingerprint != current_fingerprint:
        return {
            "compare_score": None,
            "raw_saved_score": raw_saved_score,
            "status": "regime_mismatch",
            "label": f"regime_mismatch:{raw_saved_score}",
        }

    return {
        "compare_score": raw_saved_score,
        "raw_saved_score": raw_saved_score,
        "status": "compatible",
        "label": str(raw_saved_score),
    }


def _persist_best_candidate(
    thesis_content: str,
    *,
    score: int,
    weakest_point: str,
    iteration: int,
    run_id: int,
    mutator_model_id: str,
    judge_model_id: str,
    score_contract: dict | None = None,
) -> str:
    clean_content = _strip_best_iteration_marker(thesis_content)
    history_stem = f"{run_id}_iter{iteration}_score_{score}_{args.rubric}"
    write_file(f"{HISTORY_DIR}/{history_stem}.md", clean_content)
    thesis_with_marker = clean_content + f"\n\n<!-- best_iteration: {history_stem} -->"
    write_file(THESIS_PATH, thesis_with_marker)
    write_file(WORKING_PATH, thesis_with_marker)

    meta = {
        "run_id": run_id,
        "iteration": iteration,
        "score": score,
        "rubric": args.rubric,
        "dynamic": args.dynamic,
        "mutator_model": mutator_model_id,
        "judge_model": judge_model_id,
        "effective_mutator_models": sorted(SESSION_MUTATOR_MODELS_USED) or [mutator_model_id],
        "mutator_fallback_used": bool(SESSION_MUTATOR_FALLBACK_EVENTS),
        "effective_judge_models": list((score_contract or {}).get("effective_judge_models", [judge_model_id])),
        "judge_fallback_used": bool((score_contract or {}).get("judge_fallback_used", False)),
        "weakest_point": weakest_point,
        "timestamp": datetime.now().isoformat(),
        "score_contract": score_contract or {},
        "score_regime_fingerprint": _score_regime_fingerprint_from_score_contract(score_contract),
    }
    write_file(
        f"{HISTORY_DIR}/{history_stem}_meta.json",
        json.dumps(meta, indent=2),
    )

    dag_src = LATEST_PROBABILITY_DAG_PATH
    if os.path.exists(dag_src):
        shutil.copy(dag_src, f"{HISTORY_DIR}/{history_stem}_dag.json")

    return history_stem


def _project_state_paths(project_dir: str) -> tuple[str, ...]:
    return (
        THESIS_PATH,
        WORKING_PATH,
        f"{project_dir}/test_model.py",
        EVIDENCE_PATH,
        f"{project_dir}/workspace/fit_result.json",
    )


def _capture_project_state(paths: tuple[str, ...]) -> dict[str, str | None]:
    snapshot: dict[str, str | None] = {}
    for path in paths:
        snapshot[path] = read_file(path) if os.path.exists(path) else None
    return snapshot


def _restore_project_state(snapshot: dict[str, str | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            if os.path.exists(path):
                os.remove(path)
            continue
        write_file(path, content)


def _latest_debate_log_text(project_dir: str) -> str:
    project_path = Path(project_dir)
    candidates = sorted(project_path.glob("debate_log_iter_*.md"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        return ""
    return candidates[-1].read_text()


def _champion_eval_payload() -> dict | None:
    return read_json(CHAMPION_EVAL_RESULTS_PATH)


def _saved_best_history_payload() -> tuple[str | None, dict | None]:
    history_stem = _current_saved_best_stem()
    if not history_stem:
        return None, None
    meta_path = Path(HISTORY_DIR) / f"{history_stem}_meta.json"
    if not meta_path.exists():
        return history_stem, None
    return history_stem, read_json(str(meta_path))


def _reconstruct_champion_artifacts_from_saved_best() -> dict:
    history_stem, meta = _saved_best_history_payload()
    if not history_stem or not isinstance(meta, dict):
        return {
            "reconstructed": False,
            "reason": "saved_best_missing",
            "regime_fingerprint": None,
        }

    champion_eval = build_champion_eval_from_saved_best(
        meta,
        history_stem,
        project_rubric=args.rubric,
        project_dynamic=args.dynamic,
        project_mutator_model_id=MUTATOR_MODEL_ID,
        project_judge_model_id=JUDGE_MODEL_ID,
        score_regime_fingerprint_from_meta=_score_regime_fingerprint_from_meta,
        score_regime_fingerprint_from_score_contract=_score_regime_fingerprint_from_score_contract,
    )
    write_json(CHAMPION_EVAL_RESULTS_PATH, champion_eval)

    history_dag_path = Path(HISTORY_DIR) / f"{history_stem}_dag.json"
    if history_dag_path.exists():
        shutil.copy(history_dag_path, CHAMPION_PROBABILITY_DAG_PATH)

    champion_gap_payload = build_champion_gap_payload_from_saved_best(
        meta,
        project_name=args.project,
        score_regime_fingerprint_from_meta=_score_regime_fingerprint_from_meta,
        score_regime_fingerprint_from_score_contract=_score_regime_fingerprint_from_score_contract,
    )
    write_json(CHAMPION_EVIDENCE_GAPS_PATH, champion_gap_payload)

    return {
        "reconstructed": True,
        "reason": "saved_best_history",
        "regime_fingerprint": artifact_regime_fingerprint(
            champion_eval,
            score_regime_fingerprint_from_score_contract=_score_regime_fingerprint_from_score_contract,
        ),
    }


def _champion_artifacts_out_of_sync_with_saved_best() -> bool:
    champion_eval = _champion_eval_payload()
    history_stem, saved_meta = _saved_best_history_payload()
    return champion_artifacts_out_of_sync_with_saved_best(
        champion_eval,
        history_stem=history_stem,
        saved_meta=saved_meta,
        score_regime_fingerprint_from_meta=_score_regime_fingerprint_from_meta,
        score_regime_fingerprint_from_score_contract=_score_regime_fingerprint_from_score_contract,
    )


def _promote_latest_artifacts_to_champion() -> dict:
    latest_eval = read_json(LATEST_EVAL_RESULTS_PATH)
    champion_eval = None
    regime_fingerprint = None
    if latest_eval is not None:
        champion_eval = set_artifact_role(
            latest_eval,
            "champion",
            score_regime_fingerprint_from_score_contract=_score_regime_fingerprint_from_score_contract,
        )
        write_json(CHAMPION_EVAL_RESULTS_PATH, champion_eval)
        regime_fingerprint = artifact_regime_fingerprint(
            champion_eval,
            score_regime_fingerprint_from_score_contract=_score_regime_fingerprint_from_score_contract,
        )

    if os.path.exists(LATEST_PROBABILITY_DAG_PATH):
        shutil.copy(LATEST_PROBABILITY_DAG_PATH, CHAMPION_PROBABILITY_DAG_PATH)

    latest_gaps = read_json(LATEST_EVIDENCE_GAPS_PATH)
    if latest_gaps is not None:
        champion_gaps = set_artifact_role(
            latest_gaps,
            "champion",
            score_regime_fingerprint_from_score_contract=_score_regime_fingerprint_from_score_contract,
        )
        write_json(CHAMPION_EVIDENCE_GAPS_PATH, champion_gaps)

    return {
        "regime_fingerprint": regime_fingerprint,
        "champion_eval_written": champion_eval is not None,
        "champion_gap_written": latest_gaps is not None,
        "champion_dag_written": os.path.exists(CHAMPION_PROBABILITY_DAG_PATH),
    }


def _format_gate_surface_for_prompt(eval_payload: dict) -> str:
    """Format latest gate surface for cold successor prompting."""
    score_contract = eval_payload.get("score_contract", {}) if isinstance(eval_payload, dict) else {}
    det = score_contract.get("deterministic_charter_gates", {})
    results = det.get("results", [])
    lines = ["LATEST GATE SURFACE:"]
    if results:
        for item in results:
            name = item.get("name", "unknown")
            passed = bool(item.get("passed", False))
            status = "PASS" if passed else "FAIL"
            lines.append(f"  - {name}: {status}")
            reason = str(item.get("reason", "") or "")
            if reason:
                lines.append(f"    reason: {reason}")
    else:
        hard_fail_reasons = score_contract.get("hard_fail_reasons", [])
        soft_caps = score_contract.get("soft_score_caps", [])
        if hard_fail_reasons:
            lines.append("  Hard fail reasons:")
            for reason in hard_fail_reasons:
                lines.append(f"    - {reason}")
        if soft_caps:
            lines.append("  Soft caps:")
            for cap in soft_caps:
                lines.append(f"    - cap={cap.get('cap')}: {cap.get('reason', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GP-087 Slim: Residual-driven primitive injection
# ---------------------------------------------------------------------------

# Primitives that produce a correction term decaying toward zero at large u.
# These are candidates when the farther-tail gate fails because the model
# overshoots or undershoots the true asymptote.
# Parameter prefix "tail_" avoids collision with Component D's "d2_" prefix.
# The champion expression may already contain d2_a, d2_b, d2_c from a prior
# depth-2 composition — reusing those names would create duplicate assignments
# in test_model.py and break the fit.
_GP087_TAIL_CORRECTION_PRIMITIVES: list[tuple[str, str, list[str]]] = [
    ("reciprocal",      "tail_a / {var} + tail_b",                       ["tail_a", "tail_b"]),
    ("harmonic",        "tail_a / {var} + tail_b / {var}**2 + tail_c",   ["tail_a", "tail_b", "tail_c"]),
    ("log_reciprocal",  "tail_a * math.log({var}) / {var} + tail_b",     ["tail_a", "tail_b"]),
    ("sqrt_reciprocal", "tail_a / math.sqrt({var}) + tail_b",            ["tail_a", "tail_b"]),
    ("exp_decay",       "tail_a * math.exp(-tail_b * {var}) + tail_c",   ["tail_a", "tail_b", "tail_c"]),
]


def _gp087_propose_tail_correction_seeds(
    eval_results: dict,
    workspace_dir: Path,
    rubric_data: dict,
    iteration_index: int,
    stagnation_count: int = 0,
) -> list[dict] | None:
    """GP-087 Slim: when farther-tail gate fails, propose composition seeds
    from the tail-correction primitive library.

    Returns a list of seed candidates (same format as composition_seed.json)
    or None if GP-087 does not fire.

    Information boundary: emits only primitive names + expressions.
    No farther-tail residual values leak into the seed.

    Two firing modes:
    1. Gate mode: a deterministic_charter_gates result with "farther_tail" in
       its name is present and failed. This is the standard path for rubrics
       with explicit farther-tail hard gates.
    2. Contract-stagnation mode: rubric declares farther_tail_contract: True
       (no explicit gate) and the eval score is < 100 and stagnation_count >= 1.
       This covers rubrics that use gp048_farther_tail_veto_mode (prompt-level)
       instead of a deterministic gate — the judge's weakest_point reflects the
       farther-tail failure but it never appears in deterministic_charter_gates.
    """
    score_contract = eval_results.get("score_contract", {})
    if not isinstance(score_contract, dict):
        return None

    det = score_contract.get("deterministic_charter_gates", {})
    if not isinstance(det, dict):
        return None

    results = det.get("results", [])
    if not isinstance(results, list):
        return None

    # Mode 1: Check if any farther-tail gate explicitly failed
    farther_tail_failed = False
    for item in results:
        name = str(item.get("name", ""))
        if "farther_tail" in name and not bool(item.get("passed", False)):
            farther_tail_failed = True
            break

    # Mode 2: Contract-stagnation fallback — fires when the rubric declares a
    # farther_tail_contract but has NO explicit farther-tail gate (veto-mode
    # rubrics where the judge's weakest_point is the only signal).
    # Must NOT fire when an explicit farther_tail gate already exists in
    # deterministic_charter_gates — Mode 1 is the authoritative path for those.
    if not farther_tail_failed and rubric_data.get("farther_tail_contract"):
        explicit_tail_gate_exists = any(
            "farther_tail" in str(item.get("name", ""))
            for item in results
        )
        if not explicit_tail_gate_exists:
            current_score = eval_results.get("score", 100)
            if (
                isinstance(current_score, (int, float))
                and current_score < 100
                and stagnation_count >= 1
            ):
                farther_tail_failed = True
                print(
                    f"    >> GP-087: farther_tail_contract active, score={current_score}, "
                    f"stagnation={stagnation_count} — contract-stagnation mode"
                )

    if not farther_tail_failed:
        return None

    # Read the current best expression from fit_result.json
    fit_result_path = workspace_dir / "fit_result.json"
    if not fit_result_path.exists():
        return None

    try:
        fit_result = json.loads(fit_result_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    champion_expr = fit_result.get("expression", "")
    champion_params = list(fit_result.get("fitted_params", {}).keys())
    if not champion_expr:
        return None

    # Build the variable name from rubric
    ind_vars: list[str] = rubric_data.get("fit_required_vars", ["n"])
    var_name: str = ind_vars[0] if ind_vars else "n"

    # Grammar filter
    grammar = str(rubric_data.get("fit_expression_grammar", "") or "").strip().lower()
    forbidden_re = None
    if grammar == "math_exp_only":
        forbidden_re = re.compile(
            r"math\.(sin|cos|tan|sinh|cosh|tanh|asin|acos|atan)"
        )

    # Compose each tail-correction primitive with the champion expression
    seeds: list[dict] = []
    for prim_name, prim_template, prim_params in _GP087_TAIL_CORRECTION_PRIMITIVES:
        correction_expr = prim_template.format(var=var_name)

        # Grammar check
        if forbidden_re and forbidden_re.search(correction_expr):
            continue

        # Skip if the correction primitive's params are already present in the
        # champion expression — prevents double-composition when GP-087 runs
        # against a champion that was itself a prior GP-087 tail-corrected seed.
        if any(p in champion_params for p in prim_params):
            continue

        composed_expr = f"({champion_expr}) + ({correction_expr})"
        all_params = champion_params + prim_params

        seeds.append({
            "source": "gp087_residual_driven",
            "expression": composed_expr,
            "independent_vars": ind_vars,
            "parameter_names": all_params,
            "correction_primitive": prim_name,
            "iteration_synthesized": iteration_index,
            "round": f"gp087_tail_correction/{prim_name}/+",
        })

    return seeds if seeds else None


def _print_latest_artifact_status(payload: dict, previous_champion_fingerprint: str | None) -> None:
    latest_fingerprint = artifact_regime_fingerprint(
        payload,
        score_regime_fingerprint_from_score_contract=_score_regime_fingerprint_from_score_contract,
    )
    shifted = (
        latest_fingerprint is not None
        and previous_champion_fingerprint is not None
        and latest_fingerprint != previous_champion_fingerprint
    )
    shifted_label = "n/a" if previous_champion_fingerprint is None else ("yes" if shifted else "no")
    fingerprint_label = latest_fingerprint or "unknown"
    print(
        f"🧾 LATEST artifacts updated: latest_eval_results / latest_probability_dag / latest_evidence_gaps "
        f"(regime fingerprint: {fingerprint_label}; shifted vs champion: {shifted_label})"
    )


def _print_champion_artifact_status(previous_champion_fingerprint: str | None, new_champion_fingerprint: str | None) -> None:
    shifted = (
        new_champion_fingerprint is not None
        and previous_champion_fingerprint is not None
        and new_champion_fingerprint != previous_champion_fingerprint
    )
    shifted_label = "n/a" if previous_champion_fingerprint is None else ("yes" if shifted else "no")
    fingerprint_label = new_champion_fingerprint or "unknown"
    print(
        f"🏆 CHAMPION artifacts updated: champion_eval_results / champion_probability_dag / champion_evidence_gaps "
        f"(regime fingerprint: {fingerprint_label}; shifted vs previous champion: {shifted_label})"
    )


def _print_champion_reconstruction_status(previous_champion_fingerprint: str | None, new_champion_fingerprint: str | None) -> None:
    shifted = (
        new_champion_fingerprint is not None
        and previous_champion_fingerprint is not None
        and new_champion_fingerprint != previous_champion_fingerprint
    )
    shifted_label = "n/a" if previous_champion_fingerprint is None else ("yes" if shifted else "no")
    fingerprint_label = new_champion_fingerprint or "unknown"
    print(
        f"🛠️ CHAMPION artifacts reconstructed from saved best history "
        f"(regime fingerprint: {fingerprint_label}; shifted vs previous champion: {shifted_label})"
    )


def _refresh_derived_constraints_from_eval(
    evaluation: dict,
    *,
    run_id: int,
    iteration_index: int,
    artifact_role: str = "latest",
) -> None:
    proposals = sanitize_constraint_proposals(evaluation.get("derived_constraints"))
    ledger = update_derived_constraints_ledger(
        project=args.project,
        ledger_path=Path(DERIVED_CONSTRAINTS_PATH),
        proposals=proposals,
        run_id=run_id,
        iteration_index=iteration_index,
        source_score=evaluation.get("score"),
        weakest_point=str(evaluation.get("weakest_point", "") or ""),
        score_regime_fingerprint=_score_regime_fingerprint_from_score_contract(
            evaluation.get("score_contract")
        ),
        artifact_role=artifact_role,
    )
    write_derived_constraints_brief(ledger, Path(DERIVED_CONSTRAINTS_BRIEF_PATH))
    print(
        "🧷 Derived constraints updated: "
        f"{ledger.get('confirmed_constraint_count', 0)} confirmed / "
        f"{ledger.get('provisional_constraint_count', 0)} provisional"
    )

    # GP-061 Component A: structural constraint extractor.
    # Reads workspace/structural_memory.json, looks for a skeleton shared by
    # all failed families, emits a have-to-believe constraint into the ledger.
    try:
        _, _, structural_proposal = run_structural_extractor(
            project_dir=Path(PROJECT_DIR),
            run_id=run_id,
            iteration_index=iteration_index,
        )
    except Exception as exc:  # pragma: no cover - extractor is best-effort
        print(f"⚠️  structural_extractor skipped: {exc}")
        structural_proposal = None

    if structural_proposal is not None:
        ledger = update_derived_constraints_ledger(
            project=args.project,
            ledger_path=Path(DERIVED_CONSTRAINTS_PATH),
            proposals=[structural_proposal],
            run_id=run_id,
            iteration_index=iteration_index,
            source_score=evaluation.get("score"),
            weakest_point="structural_extractor: cross-family invariant in structural_memory",
            score_regime_fingerprint=_score_regime_fingerprint_from_score_contract(
                evaluation.get("score_contract")
            ),
            artifact_role=artifact_role,
        )
        write_derived_constraints_brief(ledger, Path(DERIVED_CONSTRAINTS_BRIEF_PATH))
        print(
            "🧭 structural_extractor emitted have-to-believe constraint "
            f"(coupling={structural_proposal.get('failure_family','?')})"
        )

    # GP-062: trajectory thrash detector. Reads latent_distance.jsonl +
    # structural_memory.json for the same-run trajectory signal and emits a
    # constraint naming preserved skeleton features when the mutator rewrites
    # semantic surface while keeping the outer skeleton. Same provisional gate
    # as GP-061 — two distinct runs required before confirmed injection.
    try:
        _, thrash_proposal = run_trajectory_thrash_detector(
            project_dir=Path(PROJECT_DIR),
        )
    except Exception as exc:  # pragma: no cover - detector is best-effort
        print(f"⚠️  trajectory_thrash_detector skipped: {exc}")
        thrash_proposal = None

    if thrash_proposal is not None:
        ledger = update_derived_constraints_ledger(
            project=args.project,
            ledger_path=Path(DERIVED_CONSTRAINTS_PATH),
            proposals=[thrash_proposal],
            run_id=run_id,
            iteration_index=iteration_index,
            source_score=evaluation.get("score"),
            weakest_point="trajectory_extractor: semantic-high / structural-zero thrash across iterations",
            score_regime_fingerprint=_score_regime_fingerprint_from_score_contract(
                evaluation.get("score_contract")
            ),
            artifact_role=artifact_role,
        )
        write_derived_constraints_brief(ledger, Path(DERIVED_CONSTRAINTS_BRIEF_PATH))
        print(
            "🧭 trajectory_extractor emitted thrash constraint "
            f"(preserved_features_count={len(thrash_proposal.get('constraint','').split(':')[-1].split(','))})"
        )

    # GP-061.B: negative-space extractor. Reads structural_memory.json via the
    # generalized AST feature matrix and emits a constraint listing (function
    # × arg_pos × operator) slots that every failed family left empty. Same
    # provisional gate as Component A — stays in the provisional bucket until
    # a second distinct run confirms the surfaced voids.
    if getattr(args, "disable_negative_space_extractor", False):
        print(
            "🚫 negative_space_extractor disabled via --disable-negative-space-extractor "
            "(GP-061.B cold-harvest discipline)"
        )
        void_proposal = None
    else:
        try:
            _, void_proposal = run_negative_space_extractor(
                project_dir=Path(PROJECT_DIR),
            )
        except Exception as exc:  # pragma: no cover - detector is best-effort
            print(f"⚠️  negative_space_extractor skipped: {exc}")
            void_proposal = None

    if void_proposal is not None:
        ledger = update_derived_constraints_ledger(
            project=args.project,
            ledger_path=Path(DERIVED_CONSTRAINTS_PATH),
            proposals=[void_proposal],
            run_id=run_id,
            iteration_index=iteration_index,
            source_score=evaluation.get("score"),
            weakest_point="negative_space_extractor: unexplored structural slots across failed families",
            score_regime_fingerprint=_score_regime_fingerprint_from_score_contract(
                evaluation.get("score_contract")
            ),
            artifact_role=artifact_role,
        )
        write_derived_constraints_brief(ledger, Path(DERIVED_CONSTRAINTS_BRIEF_PATH))
        print(
            "🧭 negative_space_extractor emitted void constraint "
            f"(void_count={void_proposal.get('constraint','').count(chr(10) + '  - ')})"
        )


def _dynamic_rubric_path(project: str) -> Path:
    return RUBRICS_DIR / f"dynamic_{project}.json"


def _load_current_committee_digest(project: str) -> str:
    rubric_path = _dynamic_rubric_path(project)
    if not rubric_path.exists():
        return ""
    try:
        payload = json.loads(rubric_path.read_text())
    except Exception:
        return ""
    metadata = payload.get("metadata", {})
    instantiation_record = metadata.get("instantiation_record", {})
    digest = instantiation_record.get("committee_digest", "")
    return digest if isinstance(digest, str) else ""


def _is_catastrophic_failure(candidate_score: int, best_score_before: int) -> bool:
    if candidate_score <= 0:
        return True
    if best_score_before > 0 and candidate_score < (best_score_before * 0.5):
        return True
    return False


def _write_latest_information_yield(
    workspace_dir: Path,
    *,
    signal: IterationSignal,
    decision,
    latent_motion_summary: dict | None = None,
) -> None:
    payload = {
        "signal": {
            "iteration_index": signal.iteration_index,
            "score": signal.score,
            "weakest_point": signal.weakest_point,
            "score_improved": signal.score_improved,
            "runtime_failure": signal.runtime_failure,
            "catastrophic_failure": signal.catastrophic_failure,
            "novel_attack_ids": list(signal.novel_attack_ids),
            "novel_hinge_ids": list(signal.novel_hinge_ids),
            "novel_primitive_ids": list(signal.novel_primitive_ids),
            "verified_axioms_added": signal.verified_axioms_added,
            "falsification_mode": signal.falsification_mode,
            "mutation_r1_mismatch": signal.mutation_r1_mismatch,
            "claim_delta_type": signal.claim_delta_type,
            "committee_digest": signal.committee_digest,
            "prior_committee_digest": signal.prior_committee_digest,
        },
        "decision": {
            "action": decision.action.value,
            "stagnant_window": decision.stagnant_window,
            "rationale": decision.rationale,
        },
    }
    if latent_motion_summary is not None:
        payload["latent_motion_summary"] = latent_motion_summary
    write_file(
        str(workspace_dir / "latest_information_yield.json"),
        json.dumps(
            payload,
            indent=2,
        ),
    )


def _evaluate_post_eval_loop_control(
    workspace_dir: Path,
    *,
    signal: IterationSignal,
) -> tuple[object, dict | None]:
    raw_decision = evaluate_information_yield(
        iteration_history,
        underidentified_after=args.underidentified_after,
    )
    latent_motion_payload: dict | None = None
    final_decision = raw_decision
    if (signal.falsification_mode or "").strip().lower() == "bounded_discriminator":
        latent_motion = summarize_recent_latent_motion(project_dir=Path(PROJECT_DIR))
        if latent_motion is not None:
            final_decision = apply_latent_motion_veto(
                raw_decision,
                records_considered=latent_motion.records_considered,
                mean_max_set_distance=latent_motion.mean_max_set_distance,
                threshold=latent_motion.threshold,
            )
            latent_motion_payload = {
                "records_considered": latent_motion.records_considered,
                "window_size": latent_motion.window_size,
                "mean_max_set_distance": latent_motion.mean_max_set_distance,
                "structural_move_count": latent_motion.structural_move_count,
                "motion_classes": list(latent_motion.motion_classes),
                "threshold": latent_motion.threshold,
                "veto_applied": final_decision.action != raw_decision.action,
                "base_action": raw_decision.action.value,
                "final_action": final_decision.action.value,
            }
    _write_latest_information_yield(
        workspace_dir,
        signal=signal,
        decision=final_decision,
        latent_motion_summary=latent_motion_payload,
    )
    return final_decision, latent_motion_payload


def _record_loop_event(
    workspace_dir: Path,
    *,
    event_type: str,
    iteration_index: int,
    stagnation_count: int,
    falsification_mode: str,
    is_v4_project: bool,
    pivot_profile,
    pending_loop_action: str,
    mutator_model_id: str,
    judge_model_id: str,
) -> None:
    profile_name = pivot_profile.name if pivot_profile else None
    profile_modules = list(pivot_profile.modules) if pivot_profile else []
    payload = {
        "run_id": RUN_ID,
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "project": args.project,
        "iteration_index": iteration_index,
        "stagnation_count": stagnation_count,
        "falsification_mode": falsification_mode,
        "is_v4_project": is_v4_project,
        "pivot_profile": profile_name,
        "pivot_modules": profile_modules,
        "pending_loop_action": pending_loop_action,
        "mutator_model_id": mutator_model_id,
        "judge_model_id": judge_model_id,
    }
    write_json(str(workspace_dir / "latest_loop_event.json"), payload)
    append_jsonl(str(workspace_dir / "loop_events.jsonl"), payload)


def _latest_low_yield_tail(history: list[IterationSignal]) -> list[IterationSignal]:
    tail: list[IterationSignal] = []
    for item in reversed(history):
        if item.score_improved or item.has_novelty():
            break
        tail.append(item)
    tail.reverse()
    return tail


def _write_underidentification_verdict(
    workspace_dir: Path,
    *,
    history: list[IterationSignal],
    falsification_mode: str,
) -> None:
    tail = _latest_low_yield_tail(history)
    payload = {
        "verdict": "UNDERIDENTIFIED",
        "falsification_mode": falsification_mode,
        "catastrophic_streak": sum(1 for item in tail if item.catastrophic_failure),
        "weakest_point_sequence": [item.weakest_point for item in tail],
        "operator_options": [
            "evidence_hardening: collect more evidence before further mutation",
            "claim_narrowing: reduce thesis ambition to match current evidence boundary",
            "freeze: declare project as successful exposing testbed",
        ],
        "timestamp": datetime.now().isoformat(),
    }
    write_file(
        str(workspace_dir / "underidentification_verdict.json"),
        json.dumps(payload, indent=2),
    )


def _extract_mutation_declaration(raw_text: str):
    match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if not match:
        return None, raw_text
    declaration_payload = utils.parse_llm_json(match.group(1))
    declaration = parse_mutation_declaration(declaration_payload)
    remaining = (raw_text[: match.start()] + raw_text[match.end() :]).strip()
    return declaration, remaining


def _validate_bounded_discriminator_suite(python_code: str) -> None:
    """GP-007: bounded-discriminator suites must be portable in the runner env."""
    try:
        tree = ast.parse(python_code)
    except SyntaxError as exc:
        raise ValueError(f"Bounded-discriminator suite has invalid Python syntax: {exc}") from exc

    stdlib_modules = getattr(sys, "stdlib_module_names", frozenset())
    disallowed: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                raise ValueError(
                    "Bounded-discriminator suite cannot use relative imports; it must be standalone."
                )
            if node.module is None:
                continue
            names = [node.module.split(".")[0]]
        else:
            continue

        for name in names:
            if name == "__future__":
                continue
            if name not in stdlib_modules:
                disallowed.append(name)

    if disallowed:
        unique = ", ".join(sorted(set(disallowed)))
        raise ValueError(
            "Bounded-discriminator suite imports non-standard dependencies "
            f"({unique}). Use standard-library-only Python and plain `assert` statements."
        )


def _prepare_mutation_candidate(
    *,
    raw_text: str,
    current_thesis: str,
    current_test_model: str,
    falsification_mode: str | None = None,
):
    declaration = None
    working_text = raw_text
    if args.runner_r1_contract:
        declaration, working_text = _extract_mutation_declaration(raw_text)
        if declaration is None:
            raise ValueError("Missing required `MutationDeclaration` JSON header.")

    code_match = re.search(r"```python\n(.*?)\n```", working_text, re.DOTALL)
    python_code = code_match.group(1) if code_match else None
    clean_thesis = (
        working_text.replace(code_match.group(0), "").strip()
        if code_match
        else working_text.strip()
    )

    validate_python_suite_candidate(python_code)

    if (
        python_code is not None
        and (falsification_mode or "numerical_proof").strip().lower() == "bounded_discriminator"
    ):
        _validate_bounded_discriminator_suite(python_code)

    validation_record = None
    if declaration is not None:
        changed_paths: list[str] = []
        if clean_thesis.strip() != current_thesis.strip():
            changed_paths.append(f"projects/{args.project}/thesis.md")
        if python_code is not None and python_code.strip() != current_test_model.strip():
            changed_paths.append(f"projects/{args.project}/test_model.py")
        validation_record = evaluate_mutation_declaration(
            declaration,
            tuple(changed_paths),
            before_text=current_thesis,
            after_text=clean_thesis,
            approved_primitive_keys=approved_primitive_keys(),
        )

    return declaration, validation_record, clean_thesis, python_code, working_text

def _accumulate_usage(
    bucket,
    *,
    model_name,
    input_tokens,
    output_tokens,
    cache_creation_input_tokens=0,
    cache_read_input_tokens=0,
    thinking_tokens=0,
    direct_cost_usd=None,
):
    global SESSION_TOKENS

    input_tokens = int(input_tokens or 0)
    output_tokens = int(output_tokens or 0)
    cache_creation_input_tokens = int(cache_creation_input_tokens or 0)
    cache_read_input_tokens = int(cache_read_input_tokens or 0)
    thinking_tokens = int(thinking_tokens or 0)

    bucket["input_tokens"] += input_tokens
    bucket["output_tokens"] += output_tokens
    bucket["cache_creation_input_tokens"] += cache_creation_input_tokens
    bucket["cache_read_input_tokens"] += cache_read_input_tokens
    bucket["thinking_tokens"] += thinking_tokens
    SESSION_TOKENS += (
        input_tokens
        + output_tokens
        + cache_creation_input_tokens
        + cache_read_input_tokens
        + thinking_tokens
    )

    pricing = load_model_pricing()
    estimated_cost = (
        float(direct_cost_usd)
        if direct_cost_usd is not None
        else estimate_cost_usd(
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
            thinking_tokens=thinking_tokens,
        )
    )
    bucket["estimated_cost_usd"] += estimated_cost
    normalized_model_name = pricing_model_name(model_name)
    if direct_cost_usd is not None or (normalized_model_name is not None and normalized_model_name in pricing):
        bucket["cost_known"] = True


def _format_cost_label(bucket) -> str:
    if bucket["cost_known"]:
        return f"${bucket['estimated_cost_usd']:.4f}"
    return "unavailable (pricing disabled or unknown model)"


def safe_mutate(prompt, config=None, model_id=MUTATOR_MODEL_ID):
    with open(f"{PROJECT_DIR}/last_prompt_debug.txt", "w") as f:
        f.write(f"MODEL USED: {model_id}\n")
        f.write("=" * 30 + "\n")
        f.write(prompt)
    response = RUNTIME.call_text(
        prompt,
        model_id=model_id,
        config=config,
        retries=PRODUCTION_CALL_RETRIES,
        timeout_seconds=600,
        request_label="Mutator request",
        progress_printer=print,
        transient_wait_seconds=20,
        timeout_wait_seconds=15,
    )
    effective_model_name = response.usage.model_name or response.effective_model_id or model_id
    canonical_effective_model = pricing_model_name(effective_model_name) or effective_model_name
    SESSION_MUTATOR_MODELS_USED.add(canonical_effective_model)
    if response.fallback_from_model_id:
        fallback_event = {
            "from": response.fallback_from_model_id,
            "to": canonical_effective_model,
        }
        if fallback_event not in SESSION_MUTATOR_FALLBACK_EVENTS:
            SESSION_MUTATOR_FALLBACK_EVENTS.append(fallback_event)
    _accumulate_usage(
        SESSION_MUTATOR_USAGE,
        model_name=response.usage.model_name or model_id,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cache_creation_input_tokens=response.usage.cache_creation_input_tokens,
        cache_read_input_tokens=response.usage.cache_read_input_tokens,
        thinking_tokens=response.usage.thinking_tokens,
        direct_cost_usd=response.usage.direct_cost_usd,
    )
    if response.fallback_from_model_id:
        print(
            "🔁 Provider fallback preserved mutation continuity: "
            f"{response.fallback_from_model_id} -> {canonical_effective_model}"
        )
    return response.text


# --- CHANGED: Added model_id to the signature ---
def mutate_thesis(
    current_content,
    current_test_model,
    weakest_point,
    evidence,
    persona,
    stagnation_count,
    model_id=MUTATOR_MODEL_ID,
    failure_log=None,
    falsification_mode=None,
    fit_primitive_enabled=False,
    fit_context="",
    structural_memory_context="",
    cold_residual_mode=False,
    residual_mode_context="",
    gp048_cohort_context="",
    farther_tail_veto_context="",
    component_c_context="",
    divergence_sweep_context="",
):
    task_header = "TASK: Resolve the following Systemic Inconsistency:"
    pivot_instruction = ""
    primitive_context = ""
    constraint_context = ""
    axioms = []
    project_charter = read_file(PROJECT_CHARTER_PATH) if os.path.exists(PROJECT_CHARTER_PATH) else ""
    anchor_proxies = extract_anchor_proxies_from_charter(project_charter)
    forecast_type = extract_forecast_type_from_charter(project_charter)
    confirmed_constraint_context = render_confirmed_constraints_prompt_section(
        Path(DERIVED_CONSTRAINTS_PATH)
    )
    if os.path.exists(AXIOM_PATH):
        with open(AXIOM_PATH, "r") as f:
            axioms = json.load(f)

    axiom_str = "\n".join([f"- {a}" for a in axioms]) if axioms else "None yet."
    is_v4_project = is_v4_family_project(args.project)
    v4_stage_index = _load_v4_stage_index()
    pivot_profile = select_pivot_profile(
        is_v4_project=is_v4_project,
        falsification_mode=falsification_mode,
        stagnation_count=stagnation_count,
    )
    style_guide = ""
    output_requirements = ""
    grounding_heading = "GROUNDING DATA (IMMUTABLE CONSTANTS):"
    grounding_payload = evidence

    # --- DYNAMIC CONTEXT MANAGEMENT ---
    if is_v4_project:
        document_context = f"### CURRENT SYSTEM STATE (FOR ANALYSIS ONLY)\n{current_content}"
        if stagnation_count >= 3:
            profile_summary = ", ".join(pivot_profile.modules) if pivot_profile else "none"
            print(
                "🚨 V4 bounded mutation override injected "
                f"(profile={pivot_profile.name if pivot_profile else 'none'}; "
                f"modules=[{profile_summary}]; "
                f"stagnation_count={stagnation_count}; generic topological pivot disabled)."
            )
            task_header = "🚨 V4 DISCIPLINE OVERRIDE: BOUNDED KERNEL MUTATION 🚨"
            pivot_instruction = """
                ### V4 MUTATION DISCIPLINE
        The run is stagnating, but you are NOT allowed to execute a generic topological pivot.
        You must remain inside the active V4 target: semantic-gate stabilization.

        Allowed mutation surface:
        1. Refine typed semantic evidence fields.
        2. Refine Python-derived gate logic (`clear`, `fatal`, `unresolved`).
        3. Refine unresolved-handling rules.
        4. Preserve `HingeObject` and `ExploitFamilyTag` as interface stubs only.

        Forbidden mutation surface:
        - Do not invent a new grand architecture, marketplace, protocol layer, entropy engine, dispute engine, or governance economy.
        - Do not solve V4 by introducing a new abstract proxy variable detached from benchmark measurement.
        - Do not claim to fix `B`'s systematic misses in general.
        - Do not collapse systematic failure and semantic variance into one scalar notion of improvement.
        - Do not use blank-slate resets, domain shifts, symbolic theater, or laws-of-physics framing.

        Required orientation:
        - Stay close to the frozen Paper 2 benchmark obligations.
        - Prefer narrower, more auditable logic over elegant global pivots.
        - If the current mechanism fails, mutate the gate contract, not the ontology of the whole project.
        """
            if pivot_profile:
                pivot_instruction += "\n" + pivot_profile.instruction
        else:
            task_header = "TASK: Resolve the following Systemic Inconsistency:"

        style_guide = """
    V4 STYLE GUIDE:
        - NO METAPHORS.
        - NO generic topological pivots.
        - NO symbolic-mapping theater like forcing $Z = f(X, Y)$.
        - Keep the object of improvement narrow: semantic-gate stabilization only.
        - Quantitative claims must map to benchmark-visible outputs such as:
          * semantic gate flip rate
          * stable bad-case retention
          * good-control false-reject behavior
          * separated `t2_ai_inference` failure reporting
        - If you introduce a new structure, specify:
          * the typed fields
          * the Python decision rule
          * the exact failure mode it addresses
        - Maximize auditability, not conceptual grandeur.
        """
        if v4_stage_index == 3:
            style_guide += """
    STAGE 4 SCOPE ENFORCEMENT:
        - This stage is ONLY about Shadow Board behavior.
        - Score-bearing mutation surface is limited to:
          * fixed role catalog
          * role assignment behavior
          * arbiter activation semantics
          * typed-handoff recording / consumption behavior
        - If you notice upstream semantic-gate, whitelist, or quote-validation weaknesses, you may mention them only as logged architectural debt.
        - Those upstream findings are OUT OF SCOPE for this stage and must not be presented as the core fix.
        - Do not propose semantic-gate hardening, whitelist expansion, quote-validation changes, or any stage-1/2/3 mechanism edits.
        """
        output_requirements = """
    V4 OUTPUT REQUIREMENTS:
        - Provide exactly one Python code block for `test_model.py`.
        - The Python block should be a minimal architectural harness, not a fake full-benchmark simulator.
        - The harness should prove only deterministic gate derivation or interface behavior relevant to this seed.
        - Your prose should stay close to this structure:
          * Weakest Link
          * Core Claim
          * Minimal Mechanism
          * Interface Discipline
          * Falsifiable Prediction
          * Failure Condition
        """
        if v4_stage_index == 3:
            output_requirements += """
    STAGE 4 OUTPUT BOUNDARY:
        - The thesis must only make claims about board composition, assignment, arbiter behavior, or typed-handoff recording.
        - Do NOT claim stable adversarial coverage, whole-system robustness, or upstream trust repair.
        - Any upstream-stage weakness must be labeled `OUT-OF-SCOPE DEBT` and must not be the main thesis target.
        """
    elif stagnation_count >= 4:
        print("🚨 EMERGENCY MANDATE: EXECUTING TOPOLOGICAL PIVOT 🚨")
        if pivot_profile:
            profile_summary = ", ".join(pivot_profile.modules)
            print(
                "🚨 Emergency pivot profile injected "
                f"(profile={pivot_profile.name}; modules=[{profile_summary}]; "
                f"stagnation_count={stagnation_count})."
            )
        print("🧹 Purging toxic axioms to allow true architectural reset...")
        
        if os.path.exists(AXIOM_PATH):
            shutil.copy(AXIOM_PATH, f"{AXIOM_PATH}.bak")
            os.remove(AXIOM_PATH) # Hide from test_thesis.py            
        axiom_str = "NONE. (Previous axioms purged due to topological pivot)."
        document_context = "🚨 [SYSTEM STATE PURGED]: Your previous logic was fundamentally and repeatedly rejected by the Auditor. You are starting from a BLANK SLATE. You must derive a new architecture using ONLY the Grounding Data and First Principles. Do NOT iterative-fix; RE-ENGINEER. 🚨"
        task_header = "🚨 EMERGENCY MANDATE: EXECUTE TOPOLOGICAL PIVOT 🚨"
    elif stagnation_count >= 3:
        profile_summary = ", ".join(pivot_profile.modules) if pivot_profile else "none"
        print(
            "🚨 Topological pivot profile injected "
            f"(profile={pivot_profile.name if pivot_profile else 'none'}; "
            f"modules=[{profile_summary}]; stagnation_count={stagnation_count})."
        )
        document_context = "🚨 [SYSTEM STATE PURGED]: Current logic has reached a terminal friction point. You must derive a NEW Transformation Function. 🚨"
        task_header = "🚨 EMERGENCY MANDATE: EXECUTE TOPOLOGICAL PIVOT 🚨"
    else:
        document_context = (
            f"### CURRENT SYSTEM STATE (FOR ANALYSIS ONLY)\n{current_content}"
        )

    if not is_v4_project and pivot_profile:
        pivot_instruction = pivot_profile.instruction
    if not is_v4_project:
        # GP-003: branch on falsification_mode from rubric.
        # Absent or "numerical_proof" -> legacy behavior unchanged (Paper 1 safe).
        # "bounded_discriminator" -> discriminator-mode prompt for causal/historical theses.
        _fmode = (falsification_mode or "numerical_proof").strip().lower()
        if _fmode == "bounded_discriminator":
            style_guide = """
    STYLE GUIDE — BOUNDED DISCRIMINATOR MODE:
        - CAUSAL MECHANISM (MANDATORY): State the core claim as a conditional:
          "If [condition P] then [outcome Q] under [scope conditions C]."
          Do NOT map to a symbolic equation ($Z = f(X, Y)$) unless the evidence directly supports one.
        - RIVAL HYPOTHESIS (MANDATORY): Name the strongest alternative explanation.
          State explicitly why your thesis predicts a different observable than the rival does.
        - NAMED DISCRIMINATOR (MANDATORY): Define the one observable condition or evidence pattern
          that separates your thesis from the rival. The discriminator must be evaluable against
          evidence that exists or could be collected, not against a number you invented.
        - OBSERVABLE PROXY (MANDATORY): For each decisive variable in your discriminator,
          you must do one of exactly three things:
          (A) CURRENT OBSERVABLE: A measurable quantity or documented event evaluable against
              the evidence in `evidence.txt` now. State what value range or pattern confirms
              your thesis vs. the rival.
          (B) FORWARD OBSERVABLE: A measurement protocol that will be evaluable in future but
              is not yet resolved. Must specify all three:
                1. WHAT will be measured (concrete variable or documented event, not a latent construct)
                2. WHEN it will be evaluable (time horizon, e.g. "within 10 years", "at next recession")
                3. DIRECTION: what outcome confirms the thesis vs. the rival
              The Python suite must assert the logical structure of the forward prediction:
              if the antecedent condition is met, the thesis predicts X and the rival predicts Y.
              Do NOT assert a current resolution — assert the conditional structure.
          (C) UNRESOLVED: The variable has no measurement protocol now or in future. Declare:
              "UNRESOLVED: [variable name] — no measurement protocol available. Excluded from
              scoring." This variable cannot appear as decisive anywhere in the thesis.
          A discriminator that uses decisive variables without satisfying (A), (B), or (C) will be
          failed by the Auditor regardless of logical coherence.
          NOTE: A forward observable (B) is NOT the same as a latent variable. Latent variables
          lack a measurement protocol entirely. Forward observables have a clear protocol and
          timeline — the thesis is making a testable prediction about future evidence.
        - LOAD-BEARING VARIABLES (MANDATORY): Where thresholds or comparisons appear, derive them
          from cited evidence ranges. If no evidence supports a specific threshold, use a
          comparative form (A > B under condition C) rather than an absolute scalar.
        - NO METAPHORS: Strictly forbidden.
        - ARITHMETIC TRANSPARENCY: All quantitative claims must be supported by evidence-grounded equations.
        - GATEKEEPER REALITY: Identify the entity with the Absolute Veto. Define the leverage required to force a state-change.
        """
            output_requirements = """
    CRITICAL OUTPUT REQUIREMENT (THE LOGIC DAG):
        - You must output a "Logic DAG" in markdown at the bottom.
        - [Axiom 1] -> [Discriminator condition] -> [Rival ruled out] -> [Conclusion]
        - Any leap-of-faith node will be failed by the Auditor.

    FORMATTING:
        - MANDATORY: You must provide exactly one Python code block (```python) for `test_model.py`.
        - DISCRIMINATOR TEST (MANDATORY): The Python block must assert the discriminator structure —
          e.g., that rival predictions diverge from your thesis predictions under specified conditions,
          or that your named observable holds in the cited evidence range.
          Do NOT assert a single hardcoded scalar threshold unless it is explicitly evidence-derived.
        - Each CURRENT OBSERVABLE proxy must have a corresponding assert in `test_model.py`
          checking the value or pattern against current evidence.
        - Each FORWARD OBSERVABLE must have a corresponding assert in `test_model.py` encoding
          the LOGICAL STRUCTURE of the prediction: assert that if antecedent X holds, the thesis
          predicts Y and the rival predicts Z (use conditional logic, not current data resolution).
        - `UNRESOLVED:` declarations must appear as comments only, never as asserts.
        - PORTABILITY REQUIREMENT (MANDATORY): `test_model.py` must be standalone and use
          standard-library-only Python. Do NOT import `pytest`, `numpy`, `pandas`, `scipy`,
          `requests`, `pint`, or any other third-party package. Use plain `assert` statements.
        - UNRESOLVED BOUNDARY (MANDATORY): Include a clearly labeled section titled
          "WHAT THIS THESIS DOES NOT CURRENTLY PROVE" listing at least one open causal question
          your discriminator cannot resolve with current evidence. Forward observables (B) are
          NOT entries in this section — they are predictions, not gaps. Only UNRESOLVED (C)
          variables and genuinely open causal questions belong here.
        - Maximize information-to-word ratio. Scannable, scientific, scrupulous.
        """
        else:
            # Default: numerical_proof mode — legacy behavior, Paper 1 safe.
            style_guide = """
    STRICT STYLE GUIDE & LAWS OF PHYSICS:
        - SYMBOLIC MAPPING: You must map the core problem to the equation $Z = f(X, Y)$. Explicitly define $X$ (the blocked variable) and $Y$ (the leverage variable).
        - ARITHMETIC TRANSPARENCY: All quantitative claims must be supported by a balanced equation.
        - LOAD-BEARING VARIABLES (MANDATORY): Before your Python block, you MUST provide a markdown table titled "LOAD-BEARING VARIABLES". List every physical constant, financial metric, or baseline assumption you use, and state its exact real-world value. The Attackers will Google these values to verify them. NO HALLUCINATED ENTITY CONSTANTS.
        - STRUCTURAL ARBITRAGE: You are REQUIRED to introduce systemic bypasses, reciprocal leverage points, or category shifts to resolve the Auditor's critique.
        - CONSERVATION OF TRADE-OFFS: A system cannot increase Velocity ($V$) without a proportional increase in Energy ($E$) or decrease in Mass ($M$). You must explicitly state the new operational drag introduced by the pivot.
        - GATEKEEPER REALITY: Identify the entity with the Absolute Veto (The Bottleneck). Define the Asymmetric Leverage required to force a state-change.

        - NO METAPHORS: You are strictly FORBIDDEN from using metaphorical framing (e.g., "The universe is a compiler" or "The company is a ship").
        - FALSIFIABILITY: You MUST output a specific, numerical, and testable prediction.
          * For Science: Predict a specific laboratory result or numerical variance in a physical constant.
          * For Business: Predict a specific financial metric (e.g., EBITDA margin, $t$-month payback, or churn rate) under a defined shock.
        - UNIT TEST REQUIREMENT: Your `test_model.py` must contain 'assert' statements that would FAIL if this prediction is not met.
        TERMINAL MATH PROTOCOL:
        - If your previous Python execution returned `NaN`, `inf`, or a `DimensionalityError`, your core equation ($Z = f(X, Y)$) is mathematically insolvent. You are FORBIDDEN from attempting to patch it using Python `try/except` blocks or `float64` limits. You must discard the mathematical relationship entirely, identify a different limiting constraint (e.g., thermal limits instead of spatial limits, or liquidity constraints instead of TAM), and derive a fundamentally new equation.
        """
            output_requirements = """
    CRITICAL OUTPUT REQUIREMENT (THE LOGIC DAG):
        - You must output a "Logic DAG" (Directed Acyclic Graph) at the bottom of your response in markdown format.
        - List your Axioms (Premises) and show exactly how they link to your Conclusion.
        - Format example:
        - [Axiom 1: Existing constraint] -> [Axiom 2: New leverage point] -> [Conclusion: Resultant state Z]
        - If any node in your graph requires a leap of faith, the Auditor will fail you.


    FORMATTING:
        - MANDATORY: You must provide exactly one Python code block (wrapped in ```python) that constitutes the test_model.py script. This script must be standalone and execute all necessary assertions.
        - QUANTITATIVE GUARDRAIL (MANDATORY): Your `test_model.py` MUST strictly enforce mathematical reality based on the domain:
          * FOR PHYSICS/SCIENCE: You must use the `pint` library (`from pint import UnitRegistry`) to assign dimensions to all physical variables. Any Category Error (e.g., adding bits to watts) must throw a `DimensionalityError`.
          * FOR BUSINESS/FINANCE/STRATEGY: You must use strict financial logic (e.g., NPV, IRR, ROI). You must explicitly define your cell-logic and assumptions. If the math relies on infinite TAM, ignores the cost of capital, or contains unit mismatches, the `assert` statements must auto-fail. Do not use `pint` for finance.
        - Maximize Information-to-Word ratio. Scannable, scientific, scrupulous.
        - Direct Answers -> Symbolic Proof -> Quantitative Comparison.
        """

    failure_context = ""
    if failure_log:
        failure_context = f"### ⚠️ RECENT FAILURE ANALYSIS\nYour last attempt failed. The Auditor's critique was: {failure_log}\nDo NOT repeat this mistake."

    if args.use_mutator_primitives:
        transfer_candidates = retrieve_primitives(
            "\n".join(
                [
                    weakest_point or "",
                    evidence[:6000],
                    current_content[:4000],
                    persona[:1500],
                ]
            ),
            top_k=args.primitive_top_k,
        )
        if transfer_candidates:
            primitive_context = (
                format_transfer_hypotheses(transfer_candidates)
                + "\n\nTRANSFER RULES:\n"
                + "- These hypotheses are not evidence and not axioms.\n"
                + "- Use them only if you can justify domain fit in the thesis text.\n"
                + "- If you use one, include a short section titled 'TRANSFER JUSTIFICATION'.\n"
                + "- Your falsification suite must explicitly test the transfer condition you rely on.\n"
            )

    charter_context = ""
    if project_charter:
        charter_context = f"""
    PROJECT CHARTER (MANDATORY CONTEXT):
    {project_charter}
    """
        if forecast_type:
            charter_context += f"""

    FORECAST TYPE CONTRACT (MANDATORY):
    - This charter declares `{forecast_type}`.
"""
            if forecast_type == "directional_forecast":
                charter_context += """
    - Keep any forecast claim bounded to directional tilt language unless the project is explicitly re-chartered.
    - Do NOT convert this project into a point-probability forecast project by smuggling in percentages.
    - A probability DAG may still express confidence structure, but it does not authorize a `%` forecast claim by itself.
"""
            elif forecast_type == "probabilistic_forecast":
                charter_context += """
    - Point probabilities are allowed only if the thesis makes the target event, horizon, and modeling basis explicit.
    - Do NOT emit a naked percentage without clear event semantics and a testable probabilistic object.
"""
    if anchor_proxies:
            anchor_lines = "\n".join([f"    - {name}" for name in anchor_proxies])
            charter_context += f"""

    ANCHOR PROXY PRESERVATION (MANDATORY):
    - This project declares Anchor Proxies. The scorer computes deterministic coverage of these exact names.
    - If your new `test_model.py` drops below 50% anchor coverage, the candidate will be hard-capped at 50.
    - Preserve the anchor set by editing the current harness in place, not by replacing it with a new naming scheme.
    - Do NOT satisfy anchors with dead imports, dead code, comments, or wrappers that hide the names.
    - Keep anchored `test:*` items as executable top-level `test_...` functions. Do NOT convert them into class methods.
    - Keep anchored `proxy:*` items as executable top-level helper functions that are actually used by the asserts.
    - Unless you are intentionally accepting a capped basin-jump, keep these exact anchors alive:
{anchor_lines}

    CURRENT ANCHORED TEST HARNESS:
    ```python
    {current_test_model}
    ```
    """

    if confirmed_constraint_context:
        constraint_context = f"""
    CONFIRMED DERIVED CONSTRAINTS (READ-ONLY):
    {confirmed_constraint_context}
    """

    # GP-035: fit primitive prompt contract (opt-in via rubric)
    fit_primitive_context = ""
    fit_declaration_reminder = ""
    structural_memory_prompt = ""
    residual_mode_prompt = ""
    if fit_primitive_enabled:
        fit_expression_grammar = str(rubric_data.get("fit_expression_grammar", "") or "").strip().lower()
        fit_primitive_context = """
    ### GP-035 FIT PRIMITIVE CONTRACT

    This project uses a post-LLM numerical fitting step (Layer 3 Mandatory).

    **Your role:** You are a TOPOLOGY GENERATOR only. You propose the
    mathematical form; the system handles everything else. You MUST include a
    ```fit_declaration block in your response — a JSON object with:

    Required fields:
    - "expression": math expression using your independent variables and named
      free parameters. Only arithmetic (+, -, *, /, **) and math.* functions allowed.
    - "independent_vars": list of independent variable names
    - "parameter_names": list of free parameter names in the expression

    Optional fields:
    - "initial_guesses": dict of parameter name to initial guess (default: 1.0)
    - "bounds": dict of parameter name to [lower, upper] bounds

    **IMPORTANT — Layer 3 Mandatory:**
    - The system builds `test_model.py` deterministically from your
      fit_declaration + SciPy-fitted parameters. You do NOT write `def f()`
      or `MODEL_PARAMS` — the system does that for you.
    - If you include a Python code block, it is IGNORED for test_model.py.
    - Your only job is to propose the right mathematical expression and
      declare its variables and parameters in the fit_declaration block.
    - Omitting the fit_declaration block is recorded as a fit failure.
    """
        _fit_score_mode_prompt = str(rubric_data.get("fit_score_mode", "continuous_l2")).strip().lower()
        _fit_vars = rubric_data.get("fit_required_vars")
        if _fit_vars and isinstance(_fit_vars, list):
            _var_sig = ", ".join(_fit_vars)
        else:
            _var_sig = "n"
        if _fit_score_mode_prompt == "discrete_exact":
            if not _fit_vars or not isinstance(_fit_vars, list):
                raise ValueError(
                    "Rubric has fit_score_mode=discrete_exact but no fit_required_vars list. "
                    "Add e.g. \"fit_required_vars\": [\"u\", \"v\"] to the rubric."
                )
            fit_primitive_context += f"""

    ### DISCRETE EXACT-MATCH CONTRACT

    The gate harness evaluates your model by calling `f({_var_sig})` from
    `test_model.py`. The system builds this file deterministically from your
    fit_declaration — you do NOT write `def f()` or `test_model.py` yourself.

    The function must accept integer arguments and return an integer.

    Your fit_declaration `expression` field is the body of `def f({_var_sig})`.
    Make sure it evaluates to an integer for integer inputs.
    """
        else:
            fit_primitive_context += f"""

    ### CONTINUOUS MODEL CONTRACT

    The gate harness evaluates your model by calling `f({_var_sig})` from
    `test_model.py`. The system builds this file deterministically from your
    fit_declaration + SciPy-fitted parameters — you do NOT write `def f()`
    or `MODEL_PARAMS` yourself.

    The function must accept float arguments and return a float.

    Your fit_declaration `expression` field is the body of `def f({_var_sig})`.
    Use your declared parameter names as free symbols — SciPy will fit them
    and the system will substitute the optimized values.
    """
        if fit_expression_grammar == "eml_only":
            fit_primitive_context += """

    ### SANDBOX 07 EML-ONLY GRAMMAR

    This project restricts nonlinear structure to the direct primitive:
    - `eml(x, y)` defined as `exp(x) - ln(y)`

    Enforcement:
    - Your `expression` may use arithmetic scaffolding (`+`, `-`, `*`, `/`, `**`)
      and declared variables / parameters.
    - You may NOT call `math.exp`, `math.log`, or any other `math.*` nonlinear
      function directly.
    - The only allowed nonlinear call in `expression` is direct `eml(...)`.
    - Any other direct call or `math.*` call will be rejected as a fit-grammar failure.
    """
        elif fit_expression_grammar == "math_exp_only":
            fit_primitive_context += """

    ### SANDBOX 09 MATH-EXP-ONLY GRAMMAR

    This project restricts the nonlinear vocabulary of your `fit_declaration`
    expression to the following `math.*` attributes only:
    - `math.exp`, `math.log`, `math.sqrt`
    - constants `math.e`, `math.pi`

    Enforcement:
    - Your `expression` may use arithmetic scaffolding (`+`, `-`, `*`, `/`, `**`)
      and declared variables / parameters.
    - You may call `math.exp(...)`, `math.log(...)`, `math.sqrt(...)` directly.
    - You may NOT call `eml(...)`, `math.sin`, `math.cos`, `math.tan`, `math.sinh`,
      `math.cosh`, `math.tanh`, `math.pow`, `math.fabs`, `math.ceil`, `math.floor`,
      or any other function not in the allowed list.
    - Any forbidden call will be rejected as a fit-grammar failure.
    """
        # Also append to output_requirements so it survives pivot-mode attention hijack
        output_requirements += """
    FIT DECLARATION (MANDATORY — DO NOT OMIT):
        - You MUST include a ```fit_declaration block in your response (see GP-035 FIT PRIMITIVE CONTRACT above).
        - Omitting it will be treated as a fit failure and your candidate will not be optimized.
    """
        # Trailing reminder — last line the model reads before generating
        fit_declaration_reminder = "REMINDER: Your response MUST include a fenced ```fit_declaration block. If it is absent, your candidate will be recorded as a fit failure and will not be numerically optimized."
        if fit_context:
            fit_primitive_context += f"""

    ### PREVIOUS ITERATION FIT RESULT
    {fit_context}
    """
        if structural_memory_context:
            structural_memory_prompt = f"""

    {structural_memory_context}
    """
    if cold_residual_mode and residual_mode_context:
        grounding_heading = "COLD SUCCESSOR ARTIFACTS (PRIMARY SEARCH OBJECT):"
        grounding_payload = residual_mode_context
        residual_mode_prompt = """
    ### GP-045 COLD RESIDUAL SUCCESSOR MODE

    Treat the current fitted family as a base approximation only, not as the final law.
    Your primary search object is the cold artifact surface below:
    - full visible-slice residual matrix
    - latest gate pass/fail surface
    - structural memory from families already discovered by the system
    - generic residual diagnostics already emitted by the kernel

    Constraints:
    - Do NOT assume a named repair axis.
    - Do NOT assume any fixed recombination rule such as addition.
    - If you preserve, transform, replace, or combine the current family with a new term,
      you must choose and express that relation explicitly in your candidate.
    - Original visible evidence values are intentionally not the primary object in this mode.
      Work from the residual geometry unless your candidate itself requires the broader harness context.
    """

    base_prompt = f"""{persona}

    AXIOMS (PREVIOUSLY VERIFIED TRUTHS):
    {axiom_str}

    CRITICAL CONSTRAINT (THE AXIOMATIC GATE):
    The axioms above have been verified by the Firing Squad and the Meta-Judge.
    You are FORBIDDEN from contradicting them within their original domain.
    HOWEVER, if you are executing a TOPOLOGICAL PIVOT, you are granted 'Axiom Retirement' authority. If an axiom is mathematically true but structurally irrelevant to the new domain (e.g., applying Black Hole limits to a biological brain), you must explicitly drop it by writing: "RETIRED AXIOM: [Axiom Concept] - [Reason it does not apply to this scale/domain]."

    {grounding_heading}
    {grounding_payload}

    {charter_context}
    {constraint_context}
    {document_context}
    {failure_context}
    {primitive_context}

    ---

    ### {task_header}

    "THIS IS THE WEAKEST LINK IN THE CURRENT LOGIC CHAIN: {weakest_point}"

    {residual_mode_prompt}
    {fit_primitive_context}
    {structural_memory_prompt}
    {gp048_cohort_context}
    {farther_tail_veto_context}
    {component_c_context}
    {divergence_sweep_context}
    {style_guide}
    {output_requirements}
    {pivot_instruction}
    {fit_declaration_reminder}
    """
    if args.runner_r1_contract:
        declaration_prompt = base_prompt + """
RUNNER R1 DECLARATION PHASE (MANDATORY):
- Return ONLY a single raw JSON object.
- Do NOT wrap it in markdown fences.
- Do NOT include any thesis prose, commentary, or Python.
- Commit the mutation declaration before the payload exists.

Required keys:
- `scope_delta`
- `claim_delta_type`
- `primitive_invoked`
- `touched_artifacts`

Allowed `scope_delta` values:
- `THESIS_ONLY`
- `TEST_HARNESS`
- `EVIDENCE_BOUNDARY`
- `RUBRIC_INTERFACE`
- `MULTI_ARTIFACT`

Allowed `claim_delta_type` values:
- `NARROWING`
- `WIDENING`
- `REFRAMING`

Allowed `touched_artifacts` values:
- `thesis.md`
- `current_iteration.md`
- `test_model.py`
- `evidence.txt`
- `rubric.json`
- `runner_runtime`
- `other`

`primitive_invoked` must be `null` or an approved primitive key if explicitly relied on.
"""
        declaration_text = safe_mutate(declaration_prompt, model_id=model_id)
        declaration_payload = utils.parse_llm_json(declaration_text)
        declaration = parse_mutation_declaration(declaration_payload)
        declaration_json = json.dumps(
            {
                "scope_delta": declaration.scope_delta.value,
                "claim_delta_type": declaration.claim_delta_type.value,
                "primitive_invoked": declaration.primitive_invoked,
                "touched_artifacts": [item.value for item in declaration.touched_artifacts],
            },
            indent=2,
        )
        payload_prompt = base_prompt + f"""
RUNNER R1 PAYLOAD PHASE:
- The declaration below is already committed and will be validated before the kernel sees your payload.
- You must honor it exactly.
- Do NOT output another JSON declaration block.
- Output only the thesis / harness payload.

COMMITTED DECLARATION:
```json
{declaration_json}
```
"""
        payload_text = safe_mutate(payload_prompt, model_id=model_id)
        return f"```json\n{declaration_json}\n```\n\n{payload_text.strip()}"

    prompt = base_prompt
    if args.runner_r1_contract:
        prompt += """

RUNNER R1 DECLARATION CONTRACT (MANDATORY):
- Your response must begin with exactly one ```json code block before any thesis prose.
- That JSON block must contain exactly these keys:
  - `scope_delta`
  - `claim_delta_type`
  - `primitive_invoked`
  - `touched_artifacts`
- Allowed `scope_delta` values:
  - `THESIS_ONLY`
  - `TEST_HARNESS`
  - `EVIDENCE_BOUNDARY`
  - `RUBRIC_INTERFACE`
  - `MULTI_ARTIFACT`
- Allowed `claim_delta_type` values:
  - `NARROWING`
  - `WIDENING`
  - `REFRAMING`
- Allowed `touched_artifacts` values:
  - `thesis.md`
  - `current_iteration.md`
  - `test_model.py`
  - `evidence.txt`
  - `rubric.json`
  - `runner_runtime`
  - `other`
- `primitive_invoked` must be `null` or an approved primitive key if you are explicitly relying on one.
- This declaration is a prior commitment. Do not generate the thesis first and then rationalize the declaration after the fact.
"""
    # --- CHANGED: Passing model_id through to safe_mutate ---
    return safe_mutate(prompt, model_id=model_id)


def evolve_rubric(current_rubric_data, winning_thesis):
    """Monotonic Constraint Ratcheting using Pro model."""
    prompt = f"""
    You are a superintelligence monitoring an epistemic optimization loop. 
    The system has successfully solved the current rubric:
    {json.dumps(current_rubric_data, indent=2)}
    
    WINNING THESIS:
    {winning_thesis}
    
    MANDATE (MONOTONIC RATCHETING):
    You must evolve the rubric to the next level of complexity.
    1. Apply Jacobi Inversion: What is the single largest unaddressed second-order consequence, biological reality, or edge-case created by this winning thesis?
    2. Write a NEW rubric. You MUST retain the ruthless spirit of the old criteria, but append ONE brutal new criterion targeting this specific vulnerability.
    3. DO NOT make the rubric easier. Do not allow 'Reward Hacking'.
    
    OUTPUT FORMAT:
    You must return a valid JSON object with exactly two keys:
    - "persona": A string detailing the adversarial persona.
    - "criteria": A JSON object containing key-value string pairs of the grading rules.
    """

    config = types.GenerateContentConfig(
        response_mime_type="application/json"
    )

    print("\n" + "·" * 40)
    print("🧠 DIRECTOR (PRO): EVOLVING RUBRIC...")
    response_text = safe_mutate(prompt, config=config, model_id=DIRECTOR_MODEL_ID)
    print("·" * 40 + "\n")
    return utils.parse_llm_json(response_text)


def _validate_eml_helper_body(eml_def: ast.FunctionDef) -> str | None:
    """Verify that an ``eml`` FunctionDef is the pristine Odrzywołek primitive.

    Required shape (rejects anything else):

        def eml(x, y):
            return math.exp(x) - math.log(y)

    - Must take exactly two positional parameters (no defaults, *args, **kwargs).
    - Body must be a single ``Return`` whose value is the BinOp
      ``math.exp(<arg0>) - math.log(<arg1>)``, with each call passing
      exactly the corresponding parameter by name.
    - No other statements, no nested helpers, no default values.

    Returns an error string on violation, ``None`` on success.
    """

    args = eml_def.args
    if (
        args.vararg is not None
        or args.kwarg is not None
        or args.kwonlyargs
        or args.posonlyargs
        or args.defaults
        or args.kw_defaults
    ):
        return "EML-only grammar violation: eml(x, y) must take exactly two positional parameters with no defaults."
    if len(args.args) != 2:
        return "EML-only grammar violation: eml helper must have signature eml(x, y)."
    param0_name = args.args[0].arg
    param1_name = args.args[1].arg

    body = list(eml_def.body)
    # Allow a leading docstring; everything after must be a single Return.
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return "EML-only grammar violation: eml helper body must be exactly `return math.exp(x) - math.log(y)` (docstring optional)."
    ret_value = body[0].value
    if ret_value is None:
        return "EML-only grammar violation: eml helper return statement is empty."

    if not (isinstance(ret_value, ast.BinOp) and isinstance(ret_value.op, ast.Sub)):
        return "EML-only grammar violation: eml body must be `math.exp(x) - math.log(y)` (subtraction form)."

    def _is_math_call(node: ast.AST, func_name: str, expected_arg: str) -> bool:
        if not isinstance(node, ast.Call):
            return False
        if node.keywords:
            return False
        if len(node.args) != 1:
            return False
        func = node.func
        if not isinstance(func, ast.Attribute):
            return False
        if not (isinstance(func.value, ast.Name) and func.value.id == "math"):
            return False
        if func.attr != func_name:
            return False
        arg = node.args[0]
        return isinstance(arg, ast.Name) and arg.id == expected_arg

    if not _is_math_call(ret_value.left, "exp", param0_name):
        return (
            "EML-only grammar violation: left side of eml body must be "
            f"`math.exp({param0_name})`."
        )
    if not _is_math_call(ret_value.right, "log", param1_name):
        return (
            "EML-only grammar violation: right side of eml body must be "
            f"`math.log({param1_name})`."
        )
    return None


_MATH_EXP_ONLY_MODEL_ATTRS = frozenset({"e", "pi", "exp", "log", "sqrt"})


def _validate_math_exp_only_python_model(tree: ast.AST) -> str | None:
    """GP-061 sandbox_09 ``math_exp_only`` grammar for the Python model body.

    Contract:
    - Must define a top-level ``I_model`` function (any positional signature).
    - Inside ``I_model``: direct ``Name`` calls are forbidden (no ``eml(...)``,
      no re-imported helpers). Only ``math.exp``, ``math.log``, ``math.sqrt``
      attribute calls are permitted, and ``math.*`` attribute access is
      restricted to ``{e, pi, exp, log, sqrt}``. Any other ``math.*`` reference
      (e.g. ``math.sin``) or any non-``math`` attribute call is rejected.
    """

    i_model: ast.FunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "I_model":
            i_model = node
            break
    if i_model is None:
        return "math_exp_only grammar requires a top-level I_model(...) function."

    for node in ast.walk(i_model):
        if isinstance(node, ast.Attribute):
            if not (isinstance(node.value, ast.Name) and node.value.id == "math"):
                return (
                    "math_exp_only grammar violation in I_model: attribute access "
                    "only allowed on the 'math' module."
                )
            if node.attr not in _MATH_EXP_ONLY_MODEL_ATTRS:
                return (
                    f"math_exp_only grammar violation in I_model: math.{node.attr} "
                    "is not in the allowed set {e, pi, exp, log, sqrt}."
                )
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                return (
                    f"math_exp_only grammar violation in I_model: direct call "
                    f"'{func.id}(...)' is not allowed; route nonlinearity through "
                    "math.exp / math.log / math.sqrt."
                )
            if isinstance(func, ast.Attribute):
                # Already validated above by the Attribute branch.
                continue
            return "math_exp_only grammar violation in I_model: unsupported call structure."
    return None


def validate_python_model_grammar(
    python_code: str,
    grammar: str | None,
) -> str | None:
    """Return None when the candidate code satisfies the requested model grammar.

    Current project-specific use:
    - ``eml_only``: inside ``I_model`` the only allowed function call is
      direct ``eml(...)``. The module must also define a pristine ``eml``
      helper whose body is exactly ``return math.exp(x) - math.log(y)`` —
      the mutator writes ``test_model.py`` and could otherwise smuggle
      additional nonlinearity into the helper body.
    """

    normalized = (grammar or "").strip().lower()
    if normalized not in ("eml_only", "math_exp_only"):
        return None

    try:
        tree = ast.parse(python_code)
    except SyntaxError as exc:
        return f"Python model grammar check could not parse candidate code: {exc}"

    if normalized == "math_exp_only":
        return _validate_math_exp_only_python_model(tree)

    i_model = None
    eml_defs: list[ast.FunctionDef] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name == "I_model":
                i_model = node
            elif node.name == "eml":
                eml_defs.append(node)
    if i_model is None:
        return "EML-only grammar requires a top-level I_model(phi, psi, params=...) function."
    if not eml_defs:
        return "EML-only grammar requires a top-level eml(x, y) helper defined as `math.exp(x) - math.log(y)`."
    if len(eml_defs) > 1:
        return "EML-only grammar violation: eml helper must be defined exactly once at module level."
    eml_error = _validate_eml_helper_body(eml_defs[0])
    if eml_error is not None:
        return eml_error

    found_eml = False
    for node in ast.walk(i_model):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            if func.id == "eml":
                found_eml = True
                continue
            return f"EML-only grammar violation in I_model: direct call '{func.id}(...)' is not allowed."
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name) and func.value.id == "math":
                return (
                    "EML-only grammar violation in I_model: direct math.* calls are not allowed; "
                    "route nonlinear structure through eml(...)."
                )
            return "EML-only grammar violation in I_model: attribute call is not allowed."
        return "EML-only grammar violation in I_model: unsupported call structure."

    if not found_eml:
        return "EML-only grammar violation in I_model: model must use at least one direct eml(...) call."
    return None


def build_model_grammar_failure_code(message: str) -> str:
    """Return a fail-closed harness candidate when a model grammar is violated."""

    safe_message = message.replace('"', "'")
    return f'''MODEL_PARAMS = {{}}

def I_model(phi, psi, params=MODEL_PARAMS):
    return float("nan")

def test_model_grammar_contract():
    assert False, "{safe_message}"

if __name__ == "__main__":
    test_model_grammar_contract()
'''


if __name__ == "__main__":
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)

    # Unique ID for this run — prevents cross-run filename collisions
    RUN_ID = int(time.time())

    with open(MAIN_RUBRIC_PATH, "r") as f:
        rubric_data = json.load(f)

    if args.rubric_review_before_run:
        print("🛂 GP-054 preflight: running rubric review before iteration 1...")
        rubric_review_result = run_rubric_review(
            project=args.project,
            rubric=args.rubric,
            model_family=args.judge_model,
        )
        rubric_review_payload = rubric_review_result["review_payload"]
        rubric_review_code = review_exit_code(rubric_review_payload)
        print(
            "🛂 GP-054 preflight result: "
            f"scenario={rubric_review_payload['scenario_validity']['status']} "
            f"checks_failed={len(rubric_review_payload['checks_failed'])}/{len(rubric_review_payload['checks'])}"
        )
        print(f"🧾 Rubric review artifact: {rubric_review_result['review_path']}")
        if rubric_review_result["patch_path"] is not None:
            print(f"🧾 Rubric patch artifact: {rubric_review_result['patch_path']}")
        if rubric_review_code != 0:
            print(
                "🛑 Aborting before iteration 1 because GP-054 rubric review did not pass. "
                "Revise the rubric/charter or rerun without --rubric_review_before_run."
            )
            raise SystemExit(rubric_review_code)

    evidence_text = read_file(EVIDENCE_PATH) if os.path.exists(EVIDENCE_PATH) else ""
    shutil.copy(THESIS_PATH, WORKING_PATH)
    baseline_test_model_path = f"{PROJECT_DIR}/test_model.py"
    if not os.path.exists(baseline_test_model_path):
        write_file(
            baseline_test_model_path,
            "assert False, 'Baseline thesis is missing a falsification suite (test_model.py).'",
        )
        print(
            "⚠️ Baseline thesis has no falsification suite. Forcing a test failure to ensure rigor."
        )
    elif os.path.getmtime(THESIS_PATH) > os.path.getmtime(baseline_test_model_path):
        print(
            "⚠️ Baseline thesis is newer than test_model.py; initial evaluation may use a stale falsification suite."
        )

    test_cmd = [
        sys.executable,
        "-m",
        "src.ztare.validator.test_thesis",
        "--project", args.project,
        "--rubric", args.rubric,
        "--judge_model", args.judge_model,
        "--mutator_model", args.mutator_model,
        "--eval_results_path", LATEST_EVAL_RESULTS_PATH,
    ]
    if args.dynamic:
        test_cmd.append("--dynamic")
    if args.use_primitives:
        test_cmd.append("--use_primitives")
    if args.use_mutator_primitives:
        test_cmd.append("--use_mutator_primitives")
    if args.primitive_top_k:
        test_cmd.extend(["--primitive_top_k", str(args.primitive_top_k)])
    if args.deterministic_score_gates:
        test_cmd.append("--deterministic_score_gates")
    if getattr(args, "disable_attacker_tools", False):
        test_cmd.append("--disable_attacker_tools")

# --- INITIALIZATION ---
if args.dynamic:
    print(
        f"🕵️  INITIALIZING COMMITTEE: Executing generate_committee.py for [{args.project}]..."
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "src.ztare.validator.generate_committee",
            "--project",
            args.project,
            *(["--use_primitives"] if args.use_primitives else []),
            "--primitive_top_k",
            str(args.primitive_top_k),
        ],
        check=True,
    )
subprocess.run(test_cmd, check=True)
with open(LATEST_EVAL_RESULTS_PATH, "r") as f:
    res = json.load(f)
previous_champion_fingerprint = artifact_regime_fingerprint(
    _champion_eval_payload(),
    score_regime_fingerprint_from_score_contract=_score_regime_fingerprint_from_score_contract,
)
if previous_champion_fingerprint is None:
    previous_champion_fingerprint = _score_regime_fingerprint_from_meta(_current_saved_best_meta())
if _champion_artifacts_out_of_sync_with_saved_best():
    reconstructed = _reconstruct_champion_artifacts_from_saved_best()
    if reconstructed.get("reconstructed"):
        _print_champion_reconstruction_status(
            previous_champion_fingerprint,
            reconstructed.get("regime_fingerprint"),
        )
        previous_champion_fingerprint = reconstructed.get("regime_fingerprint") or previous_champion_fingerprint
_print_latest_artifact_status(res, previous_champion_fingerprint)
_refresh_derived_constraints_from_eval(
    res,
    run_id=RUN_ID,
    iteration_index=0,
    artifact_role="latest",
)
judge_usage = res.get("usage_telemetry")
if isinstance(judge_usage, dict):
    _accumulate_usage(
        SESSION_JUDGE_USAGE,
        model_name=judge_usage.get("model_name"),
        input_tokens=judge_usage.get("input_tokens", 0),
        output_tokens=judge_usage.get("output_tokens", 0),
        cache_creation_input_tokens=judge_usage.get("cache_creation_input_tokens", 0),
        cache_read_input_tokens=judge_usage.get("cache_read_input_tokens", 0),
        thinking_tokens=judge_usage.get("thinking_tokens", 0),
        direct_cost_usd=judge_usage.get("estimated_cost_usd") if judge_usage.get("cost_known") else None,
    )

best_score = res["score"]
best_weakest_point = res["weakest_point"]
saved_best_anchor = _saved_best_comparison_anchor(res)
saved_best_score = saved_best_anchor["compare_score"]
if saved_best_anchor["status"] not in {"none", "compatible", "current_regime_unknown"}:
    print(
        "⚠️ Saved best score "
        f"{saved_best_anchor['raw_saved_score']} ignored for baseline comparison "
        f"because the scoring regime is {saved_best_anchor['status']}. Rebaselining under the current regime."
    )
if saved_best_score is None or res["score"] > saved_best_score:
    previous_label = saved_best_anchor["label"]
    _persist_best_candidate(
        read_file(THESIS_PATH),
        score=res["score"],
        weakest_point=res["weakest_point"],
        iteration=0,
        run_id=RUN_ID,
        mutator_model_id=MUTATOR_MODEL_ID,
        judge_model_id=JUDGE_MODEL_ID,
        score_contract=res.get("score_contract"),
    )
    champion_artifacts = _promote_latest_artifacts_to_champion()
    _print_champion_artifact_status(
        previous_champion_fingerprint,
        champion_artifacts.get("regime_fingerprint"),
    )
    print(f"💾 BASELINE PROMOTED: {previous_label} -> {res['score']}")
elif _champion_eval_payload() is None:
    champion_artifacts = _promote_latest_artifacts_to_champion()
    _print_champion_artifact_status(
        previous_champion_fingerprint,
        champion_artifacts.get("regime_fingerprint"),
    )
    print("💾 CHAMPION ARTIFACTS INITIALIZED from the current latest artifacts.")
# GP-002: separate best-state memory from mutator-facing control signal.
# best_weakest_point tracks the critique attached to the retained best state.
# current_target_weakest_point is what we feed to mutate_thesis() every iteration.
current_target_weakest_point = best_weakest_point or ""
# GP-003: read falsification_mode from rubric; absent or "numerical_proof" -> legacy behavior.
rubric_falsification_mode = rubric_data.get("falsification_mode", "numerical_proof")
# GP-020 Amendment 2 / catch grammar rule 3: if this run will use the
# bounded_discriminator pivot profile, refuse to start unless that profile
# still wires the four modules the GP-023 Planck pre-registration assumes.
# This is the non-LLM existence proof the multi-agent scorer contract demands.
if (rubric_falsification_mode or "").strip().lower() == "bounded_discriminator":
    _profile_check = check_profile_contains(
        "bounded_discriminator",
        [
            "state_incompatibility",
            "entropy_stripping",
            "dimensional_shift",
            "interface_discipline",
        ],
    )
    if _profile_check["verdict"] != "pass":
        raise RuntimeError(
            "GP-020 rule 3 pre-run assert failed: "
            + _profile_check["message"]
            + " (see src/ztare/catch_grammar/rule_3_profile_check.py)"
        )
stagnation_count = 0
last_failure_reason = None
# H-GP103-5: track family-pair fingerprints already injected as additive
# composites this run. Prevents re-injection of the same pair after a failed
# seed is popped (Bug 4 guard — without this, the same pair re-fires every
# iteration as long as stagnation_count >= gp103_stagnation_threshold).
_gp103_tried_pairs: set[tuple[str, str]] = set()
iteration_history: list[IterationSignal] = []
pending_loop_action = LoopControlAction.CONTINUE
current_committee_digest = _load_current_committee_digest(args.project) if args.dynamic else ""
workspace_dir = Path(PROJECT_DIR) / "workspace"
workspace_dir.mkdir(parents=True, exist_ok=True)
# GP-087 Snapshot Vacuum fix: ensure fit_result.json exists before the snapshot
# so that _restore_project_state never deletes it. On a fresh/wiped workspace the
# baseline eval does not call the fit engine, leaving fit_result.json absent.
# Every revert would then see None in the snapshot and erase whatever fit was
# written by iteration N, starving GP-087 of the base expression.
if rubric_data.get("enable_fit_primitive", False) and evidence_text:
    _baseline_fit_path = workspace_dir / "fit_result.json"
    if not _baseline_fit_path.exists():
        print("🔧 GP-087 baseline math init: fit_result.json absent — running baseline fit...")
        _baseline_decl = parse_fit_declaration(read_file(THESIS_PATH))
        if _baseline_decl is not None:
            _baseline_fit = fit_parameters(
                _baseline_decl,
                evidence_text,
                score_mode=rubric_data.get("fit_score_mode", "continuous_l2"),
            )
            _baseline_json = fit_result_to_json(_baseline_fit, _baseline_decl)
            _baseline_fit_path.write_text(_baseline_json)
            print("🔧 GP-087 baseline math init: fit_result.json written — snapshot will include it")
        else:
            print("🔧 GP-087 baseline math init: no fit_declaration in baseline thesis — skipping")
best_state = _capture_project_state(_project_state_paths(PROJECT_DIR))
run_exit_reason = "budget_exhausted"
last_completed_iteration = 0
_run_telemetry_state = {"finalized": False}


def _finalize_run_telemetry_once() -> None:
    if _run_telemetry_state["finalized"]:
        return
    _run_telemetry_state["finalized"] = True
    _append_run_boundary_telemetry(
        workspace_dir,
        {
            "record_type": "run_end",
            "run_id": RUN_ID,
            "timestamp_utc": _utc_now_iso(),
            "final_iteration": last_completed_iteration,
            "final_score": best_score,
            "run_exit_reason": run_exit_reason,
        },
    )


_previous_sigint_handler = signal.getsignal(signal.SIGINT)


def _handle_sigint(signum, frame):
    global run_exit_reason
    run_exit_reason = "operator_stop"
    _finalize_run_telemetry_once()
    if callable(_previous_sigint_handler):
        _previous_sigint_handler(signum, frame)
    raise KeyboardInterrupt


atexit.register(_finalize_run_telemetry_once)
signal.signal(signal.SIGINT, _handle_sigint)
_append_run_boundary_telemetry(
    workspace_dir,
    {
        "record_type": "run_start",
        "run_id": RUN_ID,
        "project": args.project,
        "timestamp_utc": _utc_now_iso(),
        "rubric": args.rubric,
        "run_mode": args.run_mode,
        "iteration_budget": ITERATIONS,
        "mutator_model": MUTATOR_MODEL_ID,
        "judge_model": JUDGE_MODEL_ID,
    },
)

for i in range(ITERATIONS):
    print(
        f"\n--- Iteration {i + 1} (Score: {best_score} | Stagnation: {stagnation_count}) ---"
    )
    iteration_start_utc = _utc_now_iso()
    iteration_mutator_usage_before = _usage_bucket_snapshot(SESSION_MUTATOR_USAGE)
    iteration_judge_usage_before = _usage_bucket_snapshot(SESSION_JUDGE_USAGE)
    current_thesis = read_file(WORKING_PATH)
    current_mutator = MUTATOR_MODEL_ID
    iteration_prior_committee_digest = current_committee_digest
    if pending_loop_action == LoopControlAction.PIVOT_REQUIRED:
        print(
            "🚀 R4 PIVOT REQUIRED: Boosting Mutator to PRO..."
        )
        current_mutator = DIRECTOR_MODEL_ID

    if args.dynamic and pending_loop_action in {
        LoopControlAction.REFRESH_SPECIALISTS,
        LoopControlAction.PIVOT_REQUIRED,
    }:
        print(
            f"🚨 R4 ACTION {pending_loop_action.value}: Refreshing Specialized Firing Squad..."
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "src.ztare.validator.generate_committee",
                "--project",
                args.project,
                *(["--use_primitives"] if args.use_primitives else []),
                "--primitive_top_k",
                str(args.primitive_top_k),
            ],
            check=True,
        )
        current_committee_digest = _load_current_committee_digest(args.project)

    current_test_model = read_file(f"{PROJECT_DIR}/test_model.py") if os.path.exists(f"{PROJECT_DIR}/test_model.py") else ""
    current_falsification_mode = (rubric_falsification_mode or "numerical_proof").strip().lower()
    current_is_v4_project = is_v4_family_project(args.project)
    current_loop_control_action = _current_loop_control_action(
        pending_loop_action=pending_loop_action,
        dynamic_enabled=args.dynamic,
        is_v4_project=current_is_v4_project,
        stagnation_count=stagnation_count,
    )
    current_pivot_profile = select_pivot_profile(
        is_v4_project=current_is_v4_project,
        falsification_mode=current_falsification_mode,
        stagnation_count=stagnation_count,
    )
    if pending_loop_action == LoopControlAction.UNDERIDENTIFIED:
        print("🛑 R4 ACTION UNDERIDENTIFIED: bounded-discriminator search exhausted.")
        run_exit_reason = "underidentified"
        _write_underidentification_verdict(
            workspace_dir,
            history=iteration_history,
            falsification_mode=rubric_falsification_mode,
        )
        print(
            "   Options: evidence_hardening | claim_narrowing | freeze"
        )
        break
    if current_is_v4_project and stagnation_count >= 3:
        _record_loop_event(
            workspace_dir,
            event_type="v4_bounded_mutation_override",
            iteration_index=i + 1,
            stagnation_count=stagnation_count,
            falsification_mode=current_falsification_mode,
            is_v4_project=current_is_v4_project,
            pivot_profile=current_pivot_profile,
            pending_loop_action=pending_loop_action.value,
            mutator_model_id=current_mutator,
            judge_model_id=JUDGE_MODEL_ID,
        )
    elif stagnation_count >= 4:
        _record_loop_event(
            workspace_dir,
            event_type="topological_pivot_emergency",
            iteration_index=i + 1,
            stagnation_count=stagnation_count,
            falsification_mode=current_falsification_mode,
            is_v4_project=current_is_v4_project,
            pivot_profile=current_pivot_profile,
            pending_loop_action=pending_loop_action.value,
            mutator_model_id=current_mutator,
            judge_model_id=JUDGE_MODEL_ID,
        )
    elif stagnation_count >= 3:
        _record_loop_event(
            workspace_dir,
            event_type="topological_pivot_profile_injected",
            iteration_index=i + 1,
            stagnation_count=stagnation_count,
            falsification_mode=current_falsification_mode,
            is_v4_project=current_is_v4_project,
            pivot_profile=current_pivot_profile,
            pending_loop_action=pending_loop_action.value,
            mutator_model_id=current_mutator,
            judge_model_id=JUDGE_MODEL_ID,
        )
    # GP-035: load previous iteration's fit result for prompt injection
    _fit_ctx = ""
    _structural_memory_ctx = ""
    _residual_mode_ctx = ""
    _cold_residual_mode = bool(rubric_data.get("cold_residual_successor_mode", False))
    if rubric_data.get("enable_fit_primitive", False):
        _fit_result_path = workspace_dir / "fit_result.json"
        if _fit_result_path.exists():
            try:
                _prev_fit = json.loads(_fit_result_path.read_text())
                if _prev_fit.get("status") == "success":
                    _fr = FitSuccess(
                        fitted_params=_prev_fit["fitted_params"],
                        max_abs_residual=_prev_fit["max_abs_residual"],
                        mean_abs_residual=_prev_fit["mean_abs_residual"],
                        rmse=_prev_fit["rmse"],
                        residual_map=_prev_fit["residual_map"],
                    )
                    _fit_ctx = format_residual_map_for_prompt(_fr)
                    if _cold_residual_mode:
                        _residual_mode_parts = [
                            "BASE FITTED FAMILY (READ-ONLY):",
                            f"  expression: {_prev_fit.get('expression', '')}",
                            f"  fitted_params: {_prev_fit.get('fitted_params', {})}",
                            "",
                            format_residual_surface_for_prompt(_fr),
                        ]
                        _latest_eval_payload = read_json(LATEST_EVAL_RESULTS_PATH)
                        if _latest_eval_payload is not None:
                            _residual_mode_parts.extend(
                                ["", _format_gate_surface_for_prompt(_latest_eval_payload)]
                            )
                        _residual_mode_ctx = "\n".join(_residual_mode_parts)
                    # GP-037 finding: structural residual diagnostic
                    # Only inject when the fit materially fails (residual >> gate threshold)
                    _indep_vars = _prev_fit.get("independent_vars", [])
                    _gate_threshold = rubric_data.get("gate_residual_threshold", 0.05)
                    if _indep_vars and _fr.max_abs_residual > _gate_threshold * 2:
                        _diag = diagnose_residual_pattern(_fr, _indep_vars)
                        if _diag.classification != "parametric_noise":
                            _fit_ctx += "\n\n" + format_diagnostic_for_prompt(_diag)
                else:
                    _fit_ctx = (
                        f"PREVIOUS ITERATION FIT RESULT: FAILURE\n"
                        f"  Class: {_prev_fit.get('failure_class', 'unknown')}\n"
                        f"  Diagnostics: {_prev_fit.get('solver_diagnostics', '')[:200]}"
                    )
            except (json.JSONDecodeError, KeyError):
                pass
        _structural_memory_ctx = render_structural_memory_prompt_section(
            workspace_dir,
            complexity_penalty_enabled=bool(
                rubric_data.get("complexity_penalty_enabled", False)
            ),
        )

    # GP-048 apparatus-feedback surfaces (all flag-gated, independent).
    # Rubric key contract (source of truth — these match the sandbox_04 rubric):
    #   gp048_telemetry                    : bool
    #   gp048_stagnation_injection_mode    : "primitive_cone" | "off" | absent
    #   gp048_farther_tail_veto_mode       : "sanitized"      | "off" | absent
    _gp048_cohort_ctx = ""
    _farther_tail_veto_ctx = ""
    _cone_mode = str(rubric_data.get("gp048_stagnation_injection_mode", "") or "").lower()
    if _cone_mode == "primitive_cone" and stagnation_count >= 3:
        try:
            _gp048_cohort_ctx = render_primitive_cohort_prompt_section(workspace_dir)
        except Exception as _cohort_exc:
            print(f"🔧 GP-048 cohort injection: error — {_cohort_exc}")
            _gp048_cohort_ctx = ""
    _veto_mode = str(rubric_data.get("gp048_farther_tail_veto_mode", "") or "").lower()
    if _veto_mode == "sanitized":
        try:
            _veto_payload = read_json(LATEST_EVAL_RESULTS_PATH)
            # Renderer self-extracts visible_threshold from the payload's
            # hidden_global_residual gate. No hardcoded fallback — if the
            # threshold is not discoverable, the renderer returns "" and
            # the block is silently skipped rather than rendered with a lie.
            _farther_tail_veto_ctx = render_farther_tail_veto_prompt_section(
                _veto_payload,
                workspace_dir=workspace_dir,
                iteration=i + 1,
            )
        except Exception as _veto_exc:
            print(f"🔧 GP-048 farther-tail veto: error — {_veto_exc}")
            _farther_tail_veto_ctx = ""

    # GP-074 Component C: load residual fingerprint for prompt injection
    _component_c_ctx = ""
    if rubric_data.get("enable_component_c", False):
        _fp_path = workspace_dir / "residual_fingerprint.json"
        if _fp_path.exists():
            try:
                _fp = json.loads(_fp_path.read_text())
                if _fp.get("status") == "emitted" and _fp.get("descriptor"):
                    _component_c_ctx = format_descriptor_for_prompt(
                        ShapeDescriptor(**_fp["descriptor"])
                    )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    # GP-076: Load sweep state for mutator prompt injection
    _divergence_sweep_ctx = ""
    if rubric_data.get("enable_component_c", False):
        _sweep_path = workspace_dir / "sweep_state.json"
        if _sweep_path.exists():
            try:
                _sweep_state = json.loads(_sweep_path.read_text())
                _divergence_sweep_ctx = _format_sweep_context(_sweep_state)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    try:
        # GP-078 Fix B v2: Topological Beam Search — read first
        # candidate from the seed queue.  The queue is a list of
        # candidates sorted saturating-first.  On failure the first
        # item is popped; on success the queue is cleared.
        _comp_seed_path = workspace_dir / "composition_seed.json"
        _comp_seed_injected = False
        if _comp_seed_path.exists():
            try:
                _seed_raw = json.loads(_comp_seed_path.read_text())
                # Backward compat: accept single dict or list
                if isinstance(_seed_raw, dict):
                    _seed_data = _seed_raw
                elif isinstance(_seed_raw, list) and _seed_raw:
                    _seed_data = _seed_raw[0]
                else:
                    _seed_data = {}
                _seed_expr = _seed_data.get("expression", "")
                _seed_vars = _seed_data.get("independent_vars", ["n"])
                _seed_params = _seed_data.get("parameter_names", [])
                _queue_len = len(_seed_raw) if isinstance(_seed_raw, list) else 1
                if _seed_expr and _seed_params:
                    print(
                        f"🧬 Component D beam injection [{1}/{_queue_len}]: "
                        f"{_seed_expr[:70]} "
                        f"(from iter {_seed_data.get('iteration_synthesized', '?')})"
                    )
                    _seed_fd_block = json.dumps({
                        "expression": _seed_expr,
                        "independent_vars": _seed_vars,
                        "parameter_names": _seed_params,
                    }, indent=2)
                    # Strip any existing fit_declaration blocks from the
                    # current thesis to avoid the Stale Block Bug: if the
                    # old thesis contains a fit_declaration, parse_fit_declaration
                    # grabs the first one it finds, ignoring our injected seed.
                    import re as _re_mod
                    _clean_thesis = _re_mod.sub(
                        r"```fit_declaration.*?```",
                        "",
                        current_thesis,
                        flags=_re_mod.DOTALL,
                    )
                    new_content = (
                        _clean_thesis.rstrip() + "\n\n"
                        "--- Component D Topological Synthesis ---\n\n"
                        "This candidate was deterministically synthesized by Component D "
                        "via depth-2 AST composition to correct systematic failures of "
                        "prior additive models. The topology was discovered by composing "
                        "existing primitives, not by LLM free-form generation.\n\n"
                        f"```fit_declaration\n{_seed_fd_block}\n```\n"
                    )
                    _comp_seed_injected = True
                    # GP-100 Heterogeneous Pipeline (opt-in via rubric).
                    # Gemini generates topologies, GPT-4.1 writes the thesis.
                    # Only fires when rubric declares epistemic_alignment: true.
                    # Intended for "new science" track where overclaiming
                    # from finite-window data is a false-discovery risk.
                    # The alignment
                    # pass rewrites ONLY the prose; the fit_declaration
                    # block is immutable.
                    if rubric_data.get("epistemic_alignment", False):
                        _thesis_writer = resolve_model_id("gpt4.1")
                        print(f"🧬 Epistemic alignment via {_thesis_writer} (heterogeneous pipeline)")
                        _confirmed_ctx = render_confirmed_constraints_prompt_section(
                            Path(DERIVED_CONSTRAINTS_PATH)
                        )
                        _alignment_prompt = (
                            "You are an epistemic alignment filter for a scientific thesis.\n\n"
                            "CONTEXT:\n"
                            f"- Persona: {rubric_data['persona'][:2000]}\n\n"
                            f"- Evidence (first 4000 chars):\n{evidence_text[:4000]}\n\n"
                            f"- Prior weakest point: {current_target_weakest_point}\n\n"
                        )
                        if _confirmed_ctx:
                            _alignment_prompt += (
                                f"- Confirmed constraints (must not violate):\n{_confirmed_ctx}\n\n"
                            )
                        if _structural_memory_ctx:
                            _alignment_prompt += (
                                f"- Structural memory:\n{_structural_memory_ctx[:2000]}\n\n"
                            )
                        _alignment_prompt += (
                            "THESIS TO ALIGN:\n"
                            f"{new_content}\n\n"
                            "TASK: Rewrite the prose surrounding the ```fit_declaration``` code block "
                            "to perfectly support the mathematical topology it declares. Requirements:\n"
                            "1. DO NOT alter a single character inside the ```fit_declaration``` block.\n"
                            "2. Be epistemically modest. In a finite observation window, exact tail "
                            "behavior (polynomial vs slow exponential) cannot be strictly falsified. "
                            "Frame claims as 'consistent with' not 'proven by' the evidence.\n"
                            "3. Decompose the curve into at least two regimes with specific u-ranges "
                            "anchored to values read directly from the evidence.\n"
                            "4. Name the strongest rival functional form and state why the data "
                            "does not yet rule it out (epistemic honesty).\n"
                            "5. Provide at least one numerical anchor proxy read from the evidence.\n"
                            "6. Show at least three explicit intermediate reasoning steps referencing "
                            "the variable u, deriving the functional form without unexplained leaps.\n"
                            "7. Do NOT import any named model, formula, or phenomenon from physics, "
                            "chemistry, biology, or engineering.\n"
                            "8. Your output must include the original ```fit_declaration``` block "
                            "verbatim. Reproduce it exactly.\n"
                            "9. Do NOT include a ```python code block. The system builds "
                            "test_model.py deterministically from the fit_declaration.\n\n"
                            "OUTPUT: The complete rewritten thesis with the fit_declaration preserved."
                        )
                        # Preserve the existing python block from new_content
                        # (carried forward from the prior thesis). The alignment
                        # pass rewrites prose only; the python block is re-injected
                        # after so _prepare_mutation_candidate finds it.
                        _existing_py = re.search(
                            r"```python\n.*?\n```", new_content, re.DOTALL
                        )
                        _aligned = safe_mutate(_alignment_prompt, model_id=_thesis_writer)
                        # Safety check: verify the full fit_declaration survived
                        if _seed_fd_block in _aligned:
                            # Re-inject the existing python block if the alignment
                            # pass dropped it (expected, since we told it not to
                            # include one).
                            if _existing_py and "```python" not in _aligned:
                                _aligned = _aligned.rstrip() + "\n\n" + _existing_py.group(0) + "\n"
                            new_content = _aligned
                        else:
                            print(
                                "    ⚠️ Alignment pass dropped fit_declaration — "
                                "falling back to unaligned injection"
                            )
                    # Seed is consumed after the iteration completes
                    # successfully (see cleanup below).  Not deleted here
                    # so a mid-iteration exception preserves the seed for
                    # retry on the next iteration.
            except Exception as _seed_exc:
                print(f"🧬 Component D seed: error — {_seed_exc}")

        if not _comp_seed_injected:
            new_content = mutate_thesis(
                current_thesis,
                current_test_model,
                current_target_weakest_point,  # GP-002: use current evaluated target, not best-state memory
                evidence_text,
                rubric_data["persona"],
                stagnation_count,
                model_id=current_mutator,
                failure_log=last_failure_reason,
                falsification_mode=rubric_falsification_mode,  # GP-003: pass rubric mode
                fit_primitive_enabled=rubric_data.get("enable_fit_primitive", False),
                fit_context=_fit_ctx,
                structural_memory_context=_structural_memory_ctx,
                cold_residual_mode=_cold_residual_mode,
                residual_mode_context=_residual_mode_ctx,
                gp048_cohort_context=_gp048_cohort_ctx,
                farther_tail_veto_context=_farther_tail_veto_ctx,
                component_c_context=_component_c_ctx,
                divergence_sweep_context=_divergence_sweep_ctx,
            )
        mutation_declaration, mutation_validation, clean_thesis, python_code, full_candidate = _prepare_mutation_candidate(
            raw_text=new_content,
            current_thesis=current_thesis,
            current_test_model=current_test_model,
            falsification_mode=rubric_falsification_mode,
        )
        _python_model_grammar = rubric_data.get("python_model_grammar")
        if python_code and _python_model_grammar:
            _grammar_error = validate_python_model_grammar(
                python_code,
                _python_model_grammar,
            )
            if _grammar_error:
                print(f"🧱 Model grammar violation: {_grammar_error}")
                python_code = build_model_grammar_failure_code(_grammar_error)
        # GP-035: post-LLM fit primitive (opt-in via rubric)
        if rubric_data.get("enable_fit_primitive", False) and evidence_text:
            # Reset per-iteration fit state — prevents stale _fit_decl /
            # _fit_result from a prior iteration leaking into Layer 3
            # builder if this iteration's parse or fit throws.
            _fit_decl = None
            _fit_result = None
            # GP-035 Turn 10: FIT_DECLARATION drought retry — one targeted
            # retry if the mutator emitted a response without a parseable
            # fit_declaration block. Splices the retry block into
            # new_content so downstream parsing is unchanged.
            try:
                _drought_outcome = validate_and_retry_fit_declaration(
                    raw_response=new_content,
                    model_id=current_mutator,
                    parse_fn=parse_fit_declaration,
                    mutator_callable=safe_mutate,
                )
                if _drought_outcome.fired:
                    if _drought_outcome.recovered:
                        print(f"🔧 GP-035 drought retry: recovered ({_drought_outcome.reason})")
                        new_content = _drought_outcome.spliced_content
                    else:
                        print(f"🔧 GP-035 drought retry: unresolved ({_drought_outcome.reason})")
            except Exception as _retry_exc:
                print(f"🔧 GP-035 drought retry: error — {_retry_exc}")
            try:
                _fit_decl = parse_fit_declaration(new_content)
                if _fit_decl is not None:
                    _fit_dimensionality = rubric_data.get("fit_required_dimensionality")
                    _fit_expression_grammar = rubric_data.get("fit_expression_grammar")
                    _diag_classification = ""
                    _fit_score_mode = rubric_data.get("fit_score_mode", "continuous_l2")
                    # GP-095: multi-start fitting. Default 1 start;
                    # escalate to 3 starts when stagnation_count >= 3.
                    _n_starts = 3 if stagnation_count >= 3 else 1
                    _gate_thr_for_fit = float(rubric_data.get("gate_residual_threshold", 0.05))
                    _fit_result = fit_parameters(
                        _fit_decl, evidence_text,
                        required_dimensionality=_fit_dimensionality,
                        expression_grammar=_fit_expression_grammar,
                        score_mode=_fit_score_mode,
                        n_starts=_n_starts,
                        gate_threshold=_gate_thr_for_fit,
                    )
                    if isinstance(_fit_result, FitSuccess):
                        if python_code is not None:
                            python_code = substitute_fitted_params(python_code, _fit_result.fitted_params)
                        _conv_tag = ""
                        if _fit_result.convergence_classification:
                            _conv_tag = f", classification={_fit_result.convergence_classification}"
                        print(
                            f"🔧 GP-035 fit: SUCCESS "
                            f"(max |res|={_fit_result.max_abs_residual:.5f}, "
                            f"starts={_fit_result.n_starts_converged}/{_fit_result.n_starts_attempted}"
                            f"{_conv_tag}, "
                            f"params={_fit_result.fitted_params})"
                        )
                        _diag_indep = _fit_decl.independent_vars if _fit_decl else []
                        _gate_thr = rubric_data.get("gate_residual_threshold", 0.05)
                        if _diag_indep and _fit_result.max_abs_residual > _gate_thr * 2:
                            _diag = diagnose_residual_pattern(_fit_result, _diag_indep)
                            _diag_classification = _diag.classification
                            if _diag.classification != "parametric_noise":
                                print(f"🔧 GP-035 residual diagnostic: {_diag.classification}")
                                print(format_diagnostic_for_prompt(_diag))
                        update_structural_memory(
                            workspace_dir=workspace_dir,
                            declaration=_fit_decl,
                            fit_result=_fit_result,
                            iteration_index=i + 1,
                            diagnostic_classification=_diag_classification,
                            convergence_classification=getattr(
                                _fit_result, "convergence_classification", ""
                            ),
                        )
                        # GP-048 Mode 1: append telemetry line (flag-gated, non-fatal).
                        if rubric_data.get("gp048_telemetry", False):
                            try:
                                write_telemetry_line(
                                    workspace_dir,
                                    iteration=i + 1,
                                    fit_result_data={
                                        "expression": _fit_decl.expression,
                                        "independent_vars": list(_fit_decl.independent_vars),
                                        "parameter_names": list(_fit_decl.parameter_names),
                                        "status": "success",
                                    },
                                )
                            except Exception as _tel_exc:
                                print(f"🔧 GP-048 telemetry: error — {_tel_exc}")
                    else:
                        print(
                            f"🔧 GP-035 fit: FAILURE "
                            f"({_fit_result.failure_class}: "
                            f"{_fit_result.solver_diagnostics[:80]})"
                        )
                    _fit_json = fit_result_to_json(_fit_result, _fit_decl)
                    (workspace_dir / "fit_result.json").write_text(_fit_json)
                    (workspace_dir / f"fit_result_iter_{i+1:03d}.json").write_text(_fit_json)
                else:
                    print("🔧 GP-035 fit: FAILURE — no FIT_DECLARATION block found")
                    _missing = json.dumps({"status": "failure", "failure_class": "missing_declaration",
                                           "attempted_template": "", "solver_diagnostics": "No FIT_DECLARATION block."}, indent=2)
                    (workspace_dir / "fit_result.json").write_text(_missing)
                    (workspace_dir / f"fit_result_iter_{i+1:03d}.json").write_text(_missing)
            except Exception as fit_exc:
                print(f"🔧 GP-035 fit: error — {fit_exc}")
    except Exception as exc:
        print(f"⚠️ Runner R1 rejection: {exc}")
        signal = IterationSignal(
            iteration_index=i + 1,
            score=best_score,
            weakest_point=f"Runner R1 rejection: {exc}",
            mutation_r1_mismatch=True,
            falsification_mode=rubric_falsification_mode,
            committee_digest=current_committee_digest,
            prior_committee_digest=iteration_prior_committee_digest,
        )
        iteration_history.append(signal)
        yield_decision = evaluate_information_yield(iteration_history, underidentified_after=args.underidentified_after)
        _write_latest_information_yield(workspace_dir, signal=signal, decision=yield_decision)
        last_failure_reason = f"Runner R1 rejection: {exc}"
        stagnation_count = yield_decision.stagnant_window
        pending_loop_action = yield_decision.action
        _append_iteration_telemetry(
            workspace_dir,
            iteration_index=i + 1,
            iteration_start_utc=iteration_start_utc,
            loop_control_action=current_loop_control_action,
            score=None,
            score_improved=False,
            champion_promoted=False,
            stagnation_count=stagnation_count,
            gate_engagement=False,
            gate_failure_count=0,
            failed_gate_ids=[],
            escalation_flags={"self_reference": False, "semantic_escalation": False},
            falsification_mode=rubric_falsification_mode,
            mutator_model_id=current_mutator,
            judge_model_id=JUDGE_MODEL_ID,
            mutator_usage=_usage_delta(
                iteration_mutator_usage_before,
                _usage_bucket_snapshot(SESSION_MUTATOR_USAGE),
            ),
            judge_usage=_usage_delta(
                iteration_judge_usage_before,
                _usage_bucket_snapshot(SESSION_JUDGE_USAGE),
            ),
            pending_loop_action=pending_loop_action.value,
        )
        last_completed_iteration = i + 1
        _pop_seed_queue(workspace_dir, _comp_seed_injected)
        _restore_project_state(best_state)
        time.sleep(1)
        continue

    if mutation_declaration is not None:
        write_file(
            str(workspace_dir / "latest_mutation_declaration.json"),
            json.dumps(
                {
                    "scope_delta": mutation_declaration.scope_delta.value,
                    "claim_delta_type": mutation_declaration.claim_delta_type.value,
                    "primitive_invoked": mutation_declaration.primitive_invoked,
                    "touched_artifacts": [item.value for item in mutation_declaration.touched_artifacts],
                },
                indent=2,
            ),
        )
    if mutation_validation is not None:
        write_file(
            str(workspace_dir / "latest_mutation_validation.json"),
            json.dumps(
                {
                    "mismatch_code": mutation_validation.mismatch_code.value,
                    "declared_scope_delta": mutation_validation.declared_scope_delta.value,
                    "declared_claim_delta_type": mutation_validation.declared_claim_delta_type.value,
                    "declared_primitive_invoked": mutation_validation.declared_primitive_invoked,
                    "declared_touched_artifacts": [item.value for item in mutation_validation.declared_touched_artifacts],
                    "actual_touched_artifacts": [item.value for item in mutation_validation.actual_touched_artifacts],
                    "breadth_delta": mutation_validation.breadth_delta,
                    "rationale": mutation_validation.rationale,
                },
                indent=2,
            ),
        )

    if (
        mutation_validation is not None
        and mutation_validation.mismatch_code != MutationMismatchCode.CLEAN
    ):
        print(
            "⚠️ Runner R1 rejection: "
            f"{mutation_validation.mismatch_code.value} — {mutation_validation.rationale}"
        )
        signal = IterationSignal(
            iteration_index=i + 1,
            score=best_score,
            weakest_point=(
                f"Runner R1 mismatch {mutation_validation.mismatch_code.value}: "
                f"{mutation_validation.rationale}"
            ),
            mutation_r1_mismatch=True,
            falsification_mode=rubric_falsification_mode,
            claim_delta_type=mutation_declaration.claim_delta_type.value if mutation_declaration is not None else "",
            committee_digest=current_committee_digest,
            prior_committee_digest=iteration_prior_committee_digest,
        )
        iteration_history.append(signal)
        yield_decision = evaluate_information_yield(iteration_history, underidentified_after=args.underidentified_after)
        _write_latest_information_yield(workspace_dir, signal=signal, decision=yield_decision)
        last_failure_reason = (
            f"Runner R1 mismatch {mutation_validation.mismatch_code.value}: "
            f"{mutation_validation.rationale}"
        )
        stagnation_count = yield_decision.stagnant_window
        pending_loop_action = yield_decision.action
        _append_iteration_telemetry(
            workspace_dir,
            iteration_index=i + 1,
            iteration_start_utc=iteration_start_utc,
            loop_control_action=current_loop_control_action,
            score=None,
            score_improved=False,
            champion_promoted=False,
            stagnation_count=stagnation_count,
            gate_engagement=False,
            gate_failure_count=0,
            failed_gate_ids=[],
            escalation_flags={"self_reference": False, "semantic_escalation": False},
            falsification_mode=rubric_falsification_mode,
            mutator_model_id=current_mutator,
            judge_model_id=JUDGE_MODEL_ID,
            mutator_usage=_usage_delta(
                iteration_mutator_usage_before,
                _usage_bucket_snapshot(SESSION_MUTATOR_USAGE),
            ),
            judge_usage=_usage_delta(
                iteration_judge_usage_before,
                _usage_bucket_snapshot(SESSION_JUDGE_USAGE),
            ),
            pending_loop_action=pending_loop_action.value,
        )
        last_completed_iteration = i + 1
        _pop_seed_queue(workspace_dir, _comp_seed_injected)
        _restore_project_state(best_state)
        time.sleep(1)
        continue

    write_file(WORKING_PATH, full_candidate)

    # --- NEW: LEVEL 3 CODE EXTRACTION ---
    # Extract the python code block for the Falsification Suite
    test_model_path = f"{PROJECT_DIR}/test_model.py"

    def _ensure_canonical_model_aliases(code: str) -> str:
        """Guarantee that test_model.py always exposes both ``f`` and ``model``
        as top-level names, regardless of which path wrote the file.

        Rules (applied in order):
        1. If ``f`` is defined and ``model`` is not → append ``model = f``
        2. If ``model`` is defined and ``f`` is not → append ``f = model``
        3. If neither is defined → find the first non-test callable, alias
           both ``f`` and ``model`` to it.
        4. If both are already defined → no-op.
        5. On SyntaxError → return code unchanged (don't make it worse).
        """
        import ast as _ast
        try:
            tree = _ast.parse(code)
        except SyntaxError:
            return code

        top_level_names = {
            node.name
            for node in tree.body
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef))
        }
        # Also include simple assignments like ``model = f``
        for node in tree.body:
            if isinstance(node, _ast.Assign):
                for t in node.targets:
                    if isinstance(t, _ast.Name):
                        top_level_names.add(t.id)

        has_f = "f" in top_level_names
        has_model = "model" in top_level_names

        if has_f and has_model:
            return code  # already canonical

        suffix = "\n# Canonical aliases — gate harnesses may call either f() or model()\n"
        if has_f and not has_model:
            return code.rstrip() + "\n" + suffix + "model = f\n"
        if has_model and not has_f:
            return code.rstrip() + "\n" + suffix + "f = model\n"

        # Neither defined — find first model-like callable
        _skip = ("test", "assert", "check", "verify", "_")
        for node in tree.body:
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                if not any(node.name.startswith(p) for p in _skip):
                    fn = node.name
                    return (
                        code.rstrip()
                        + "\n"
                        + suffix
                        + f"f = {fn}\nmodel = {fn}\n"
                    )
        return code  # nothing to alias

    # Layer 3 Mandatory (Odrzywołek Inversion, GP-035 extension):
    # The LLM is a pure topology generator.  test_model.py is ALWAYS built
    # deterministically from fit_declaration + fitted_params when the fit
    # primitive is active.  The LLM never writes def f().
    # When the fit primitive is NOT active (legacy / non-fit substrates),
    # the old LLM-python path runs unchanged.
    # Mutable flag — list so a nested function can set it without nonlocal
    # (this code runs at module scope where nonlocal is a SyntaxError).
    _layer3_built = [False]
    _fit_primitive_active = rubric_data.get("enable_fit_primitive", False)

    if _fit_primitive_active:
        def _write_layer3_stub(reason: str) -> None:
            """Write a loud-fail stub — every path through Layer 3 mandatory
            must either build a working f() or write this stub.  No silent
            fallback to LLM python is permitted."""
            _stub = (
                f"import math\n\n"
                f"# Layer 3 Mandatory: loud-fail stub — {reason}\n"
                f"def f(*args):\n"
                f"    raise RuntimeError("
                f"'Layer 3 Mandatory: {reason} — no callable built')\n"
            )
            write_file(test_model_path, _ensure_canonical_model_aliases(_stub))
            _layer3_built[0] = True
            print(f"🔧 Layer 3 Mandatory: STUB (loud-fail) — {reason}")

        try:
            _has_fit = (
                "_fit_decl" in dir()
                and "_fit_result" in dir()
                and _fit_decl is not None
                and isinstance(_fit_result, FitSuccess)
            )
            if _has_fit:
                _f_vars = list(_fit_decl.independent_vars)
                _f_sig = ", ".join(_f_vars)
                _f_param_lines = "\n".join(
                    f"    {k} = {v}" for k, v in _fit_result.fitted_params.items()
                )
                # Grammar-aware preamble: define helper functions that the
                # expression may reference (e.g. eml for eml_only grammar).
                _grammar = str(rubric_data.get("fit_expression_grammar", "") or "").strip().lower()
                _helpers = ""
                if _grammar == "eml_only" or "eml(" in _fit_decl.expression:
                    _helpers = "\ndef eml(x, y):\n    return math.exp(x) - math.log(y)\n\n"
                _deterministic_code = (
                    f"import math\n{_helpers}"
                    f"# Layer 3 Mandatory: deterministic f() from fit_declaration + fitted params\n"
                    f"def f({_f_sig}):\n"
                    f"{_f_param_lines}\n"
                    f"    return {_fit_decl.expression}\n"
                )
                write_file(test_model_path, _ensure_canonical_model_aliases(_deterministic_code))
                _layer3_built[0] = True
                print(
                    f"🔧 Layer 3 Mandatory: deterministic f() built "
                    f"(expression={_fit_decl.expression}, "
                    f"params={_fit_result.fitted_params})"
                )
            else:
                _fail_reason = (
                    "no fit_declaration parsed"
                    if not ("_fit_decl" in dir() and _fit_decl is not None)
                    else f"fit failed ({getattr(_fit_result, 'failure_class', 'unknown')})"
                )
                _write_layer3_stub(_fail_reason)
        except Exception as _l3_exc:
            # Build error MUST still produce a loud-fail stub — never fall
            # through to legacy LLM python when fit primitive is active.
            _write_layer3_stub(f"build error: {_l3_exc}")

    if not _layer3_built[0]:
        # Legacy path: fit primitive not active.
        # Use LLM-written python as before.
        if python_code is not None:
            write_file(test_model_path, _ensure_canonical_model_aliases(python_code))

    # Clean the markdown so the code doesn't clutter the thesis text
    write_file(WORKING_PATH, clean_thesis)
    print(f"💾 Falsification Suite saved to: {test_model_path}")

    try:
        subprocess.run(test_cmd, check=True)
        with open(LATEST_EVAL_RESULTS_PATH, "r") as f:
            new_eval = json.load(f)
        # GP-086 — engine-level behavioral gates (evidence_fit + uniqueness_gap +
        # parsimony_violation + named_import_check + extrapolation_gap).
        # These fire on every iteration regardless of substrate; per-project
        # gate_harness.py is unchanged.  Hard-fail gates zero new_eval["score"];
        # soft penalties are subtracted from it (floor 0).
        try:
            _global_gate_payload = run_global_gates(
                project_dir=Path(PROJECT_DIR),
                rubric_data=rubric_data,
                thesis_text=read_file(WORKING_PATH) if os.path.exists(WORKING_PATH) else None,
                evidence_text=read_file(EVIDENCE_PATH) if os.path.exists(EVIDENCE_PATH) else None,
                fit_declaration=new_eval.get("fit_declaration"),
                score_contract=new_eval.get("score_contract"),
            )
            if new_eval.get("score_contract") is not None:
                new_eval["score_contract"] = merge_into_score_contract(
                    new_eval["score_contract"], _global_gate_payload
                )
            else:
                new_eval["global_gate_payload"] = _global_gate_payload
            if _global_gate_payload.get("any_hard_fail"):
                print(
                    f"🚨 Global gate HARD FAIL: {_global_gate_payload['failed_gate_ids']}"
                )
                # Hard fail zeros the score — the gate overrides test_thesis.py output
                new_eval["score"] = 0
                # Append blind gate failure to the judge's critique (do NOT replace it).
                # The mutator needs: (1) the judge's scientific reasoning, (2) that the
                # system zeroed its score for a gate violation — but NOT which specific
                # terms triggered the gate (revealing that enables cognitive camouflage).
                _original_weakest = new_eval.get("weakest_point", "")
                _gate_fail_str = (
                    f"SYSTEM OVERRIDE: Score zeroed due to Global Gate Hard Fail: "
                    f"{', '.join(_global_gate_payload['failed_gate_ids'])}"
                )
                new_eval["weakest_point"] = (
                    f"{_original_weakest}\n\n🚨 {_gate_fail_str}"
                    if _original_weakest
                    else f"🚨 {_gate_fail_str}"
                )
            elif _global_gate_payload.get("failure_count", 0) > 0:
                _penalty = _global_gate_payload.get("total_penalty", 0)
                print(
                    f"⚠️  Global gate soft fail/penalty: {_global_gate_payload['failed_gate_ids']} "
                    f"penalty={_penalty}"
                )
                # Apply soft penalty to the eval score (floor at 0)
                if _penalty != 0:
                    new_eval["score"] = max(0, int(new_eval.get("score", 0)) + _penalty)
        except Exception as _gg_exc:
            print(f"⚠️  Global gates error (non-fatal): {_gg_exc}")
        champion_fingerprint_before_iteration = artifact_regime_fingerprint(
            _champion_eval_payload(),
            score_regime_fingerprint_from_score_contract=_score_regime_fingerprint_from_score_contract,
        )
        _print_latest_artifact_status(new_eval, champion_fingerprint_before_iteration)
        _refresh_derived_constraints_from_eval(
            new_eval,
            run_id=RUN_ID,
            iteration_index=i + 1,
            artifact_role="latest",
        )
        judge_usage = new_eval.get("usage_telemetry")
        if isinstance(judge_usage, dict):
            _accumulate_usage(
                SESSION_JUDGE_USAGE,
                model_name=judge_usage.get("model_name"),
                input_tokens=judge_usage.get("input_tokens", 0),
                output_tokens=judge_usage.get("output_tokens", 0),
                cache_creation_input_tokens=judge_usage.get("cache_creation_input_tokens", 0),
                cache_read_input_tokens=judge_usage.get("cache_read_input_tokens", 0),
                thinking_tokens=judge_usage.get("thinking_tokens", 0),
                direct_cost_usd=judge_usage.get("estimated_cost_usd") if judge_usage.get("cost_known") else None,
            )

        selection_record = evaluate_candidate_selection(
            candidate_score=new_eval["score"],
            best_score_before=best_score,
            mutation_validation=mutation_validation,
            scope_verdict=CandidateScopeVerdict.IN_SCOPE,
            scope_signals=(),
            dynamic=args.dynamic,
            debate_log_text=_latest_debate_log_text(PROJECT_DIR),
        )
        write_file(
            str(workspace_dir / "latest_candidate_selection.json"),
            json.dumps(
                {
                    "scope_verdict": selection_record.scope_verdict.value,
                    "candidate_admissible": selection_record.candidate_admissible,
                    "minority_attack_preserved": selection_record.minority_attack_preserved,
                    "keep_best_in_scope": selection_record.keep_best_in_scope,
                    "selected_as_best": selection_record.selected_as_best,
                    "candidate_score": selection_record.candidate_score,
                    "best_score_before": selection_record.best_score_before,
                    "scope_signals": list(selection_record.scope_signals),
                    "attacker_headers_seen": list(selection_record.attacker_headers_seen),
                    "rationale": selection_record.rationale,
                },
                indent=2,
            ),
        )

        # GP-102 — persist slim eval record for Kaizen cron audit.
        # Append-only; never read by score path or loop control.
        try:
            _eval_hist_path = workspace_dir / "eval_history.jsonl"
            _sc = new_eval.get("score_contract") or {}
            _dcg = _sc.get("deterministic_charter_gates", {}).get("results", {})
            _gate_verdicts = {g: r.get("passed", None) for g, r in _dcg.items()} if isinstance(_dcg, dict) else {}
            _eval_hist_path.open("a").write(
                json.dumps({
                    "iteration": i + 1,
                    "score": new_eval.get("score"),
                    "weakest_point": (new_eval.get("weakest_point") or "")[:200],
                    "gate_verdicts": _gate_verdicts,
                    "timestamp": datetime.now().isoformat(),
                }) + "\n"
            )
        except Exception:
            pass  # fail-silent telemetry

        # GP-029 first slice — passive latent-distance observability.
        # Fires for every iter, including rejected candidates, because the
        # score trace can't see motion through rejected candidates but
        # GP-029 should. Writes to workspace/latent_distance.jsonl. Never
        # read by score path, mutation path, or loop control. Fail-silent.
        record_latent_distance(
            project_dir=Path(PROJECT_DIR),
            iteration_index=i + 1,
            score=new_eval.get("score"),
        )
        gate_engagement, gate_failure_count, failed_gate_ids = _extract_iteration_gate_metrics(new_eval)
        escalation_flags = _extract_iteration_escalation_flags(new_eval)

        if not selection_record.candidate_admissible:
            print(f"⚠️ Runner R3 rejection: {selection_record.rationale}")
            signal = IterationSignal(
                iteration_index=i + 1,
                score=new_eval["score"],
                weakest_point=f"Runner R3 rejection: {selection_record.rationale}",
                falsification_mode=rubric_falsification_mode,
                claim_delta_type=mutation_declaration.claim_delta_type.value if mutation_declaration is not None else "",
                committee_digest=current_committee_digest,
                prior_committee_digest=iteration_prior_committee_digest,
            )
            iteration_history.append(signal)
            yield_decision, _ = _evaluate_post_eval_loop_control(
                workspace_dir,
                signal=signal,
            )
            last_failure_reason = f"Runner R3 rejection: {selection_record.rationale}"
            stagnation_count = yield_decision.stagnant_window
            pending_loop_action = yield_decision.action
            _append_iteration_telemetry(
                workspace_dir,
                iteration_index=i + 1,
                iteration_start_utc=iteration_start_utc,
                loop_control_action=current_loop_control_action,
                score=new_eval["score"],
                score_improved=False,
                champion_promoted=False,
                stagnation_count=stagnation_count,
                gate_engagement=gate_engagement,
                gate_failure_count=gate_failure_count,
                failed_gate_ids=failed_gate_ids,
                escalation_flags=escalation_flags,
                falsification_mode=rubric_falsification_mode,
                mutator_model_id=current_mutator,
                judge_model_id=JUDGE_MODEL_ID,
                mutator_usage=_usage_delta(
                    iteration_mutator_usage_before,
                    _usage_bucket_snapshot(SESSION_MUTATOR_USAGE),
                ),
                judge_usage=_usage_delta(
                    iteration_judge_usage_before,
                    _usage_bucket_snapshot(SESSION_JUDGE_USAGE),
                ),
                pending_loop_action=pending_loop_action.value,
            )
            last_completed_iteration = i + 1
            _pop_seed_queue(workspace_dir, _comp_seed_injected)
            _restore_project_state(best_state)
            time.sleep(1)
            continue

        signal = IterationSignal(
            iteration_index=i + 1,
            score=new_eval["score"],
            weakest_point=new_eval["weakest_point"],
            score_improved=new_eval["score"] > best_score,
            catastrophic_failure=_is_catastrophic_failure(new_eval["score"], best_score),
            falsification_mode=rubric_falsification_mode,
            claim_delta_type=mutation_declaration.claim_delta_type.value if mutation_declaration is not None else "",
            committee_digest=current_committee_digest,
            prior_committee_digest=iteration_prior_committee_digest,
            verified_axioms_added=len(new_eval.get("verified_axioms", [])),
        )
        iteration_history.append(signal)
        yield_decision, _ = _evaluate_post_eval_loop_control(
            workspace_dir,
            signal=signal,
        )

        if new_eval["score"] > best_score:
            print(f"✅ IMPROVEMENT: {best_score} -> {new_eval['score']}")
            print(f"Targeting New Weakest Link: {new_eval['weakest_point']}")
            if rubric_data.get("enable_component_c", False):
                try:
                    reset_stagnation_on_holdout_pass(workspace_dir)
                except Exception as _cc_exc:
                    print(f"🔧 GP-074 Component C reset: error — {_cc_exc}")
            best_score = new_eval["score"]
            best_weakest_point = new_eval["weakest_point"]  # GP-002: best-state memory
            current_target_weakest_point = new_eval["weakest_point"]  # GP-002: control signal
            stagnation_count = yield_decision.stagnant_window
            last_failure_reason = None
            pending_loop_action = yield_decision.action

            _persist_best_candidate(
                new_content,
                score=best_score,
                weakest_point=best_weakest_point,
                iteration=i + 1,
                run_id=RUN_ID,
                mutator_model_id=current_mutator,
                judge_model_id=JUDGE_MODEL_ID,
                score_contract=new_eval.get("score_contract"),
            )
            champion_artifacts = _promote_latest_artifacts_to_champion()
            _print_champion_artifact_status(
                champion_fingerprint_before_iteration,
                champion_artifacts.get("regime_fingerprint"),
            )

            new_axioms = new_eval.get("verified_axioms", [])
            approved_retirements = new_eval.get("retired_axioms_approved", [])
            if os.path.exists(AXIOM_PATH):
                with open(AXIOM_PATH, "r") as f:
                    _raw_axioms = json.load(f)
                # Support both plain list and {"axioms": [...]} dict formats
                if isinstance(_raw_axioms, dict):
                    current_axioms = _raw_axioms.get("axioms", [])
                else:
                    current_axioms = _raw_axioms if isinstance(_raw_axioms, list) else []
            else:
                current_axioms = []
            # Apply Judge's Veto: Filter out the approved retirements
            if approved_retirements:
                print(
                    f"🗑️ Judge Approved {len(approved_retirements)} Axiom Retirements."
                )
                current_axioms = [
                    ax
                    for ax in current_axioms
                    if not any(
                        ret.lower() in ax.lower() for ret in approved_retirements
                    )
                ]

            if new_axioms:
                print("\n" + "📜" * 20)
                print(f"NEW AXIOMS VERIFIED (ITER {i + 1}):")
                for a in new_axioms:
                    print(f"  • {a}")
                print("📜" * 20 + "\n")

            # --- THE FIX: Clean up duplicates effectively by ignoring backticks/punctuation
            def normalize(text):
                return re.sub(r'[^a-zA-Z0-9]', '', text).lower()
            
            updated_axioms = []
            seen_axioms = set()
            for ax in current_axioms + new_axioms:
                norm = normalize(ax)
                if norm not in seen_axioms:
                    seen_axioms.add(norm)
                    updated_axioms.append(ax)
                    
            with open(AXIOM_PATH, "w") as f:
                json.dump(updated_axioms, f, indent=2)

            best_state = _capture_project_state(_project_state_paths(PROJECT_DIR))

            # Clean up the backup file if the pivot was successful
            if os.path.exists(f"{AXIOM_PATH}.bak"):
                os.remove(f"{AXIOM_PATH}.bak")

            if best_score >= 85 and getattr(args, "auto_evolve", False):
                rubric_data = evolve_rubric(rubric_data, new_content)
                # Overwrite the same rubric file so future runs pick up the evolution automatically
                new_rubric_name = args.rubric
                with open(RUBRICS_DIR / f"{new_rubric_name}.json", "w") as f:
                    json.dump(rubric_data, f, indent=2)

                test_cmd = [
                    sys.executable,
                    "-m",
                    "src.ztare.validator.test_thesis",
                    "--project",
                    args.project,
                    "--rubric",
                    new_rubric_name,
                    "--judge_model", args.judge_model,
                    "--mutator_model", args.mutator_model,
                    "--eval_results_path", LATEST_EVAL_RESULTS_PATH,
                ]
                if args.dynamic:
                    test_cmd.append("--dynamic")
                if args.use_primitives:
                    test_cmd.append("--use_primitives")
                if args.use_mutator_primitives:
                    test_cmd.append("--use_mutator_primitives")
                if args.primitive_top_k:
                    test_cmd.extend(["--primitive_top_k", str(args.primitive_top_k)])
                if args.deterministic_score_gates:
                    test_cmd.append("--deterministic_score_gates")
                best_score = 20

            _append_iteration_telemetry(
                workspace_dir,
                iteration_index=i + 1,
                iteration_start_utc=iteration_start_utc,
                loop_control_action=current_loop_control_action,
                score=new_eval["score"],
                score_improved=True,
                champion_promoted=True,
                stagnation_count=stagnation_count,
                gate_engagement=gate_engagement,
                gate_failure_count=gate_failure_count,
                failed_gate_ids=failed_gate_ids,
                escalation_flags=escalation_flags,
                falsification_mode=rubric_falsification_mode,
                mutator_model_id=current_mutator,
                judge_model_id=JUDGE_MODEL_ID,
                mutator_usage=_usage_delta(
                    iteration_mutator_usage_before,
                    _usage_bucket_snapshot(SESSION_MUTATOR_USAGE),
                ),
                judge_usage=_usage_delta(
                    iteration_judge_usage_before,
                    _usage_bucket_snapshot(SESSION_JUDGE_USAGE),
                ),
                pending_loop_action=pending_loop_action.value,
            )
            last_completed_iteration = i + 1
            # GP-078 Fix B v2: on success, clear the entire seed queue.
            # The winning candidate passed the holdout — no need to test
            # the remaining candidates.
            if _comp_seed_injected:
                _consumed_seed = workspace_dir / "composition_seed.json"
                if _consumed_seed.exists():
                    _consumed_seed.unlink()
                    print("    🧬 Seed queue cleared (candidate promoted to champion)")

        else:
            print(f"❌ REVERTED: {new_eval['score']} <= {best_score}")
            print(f"Failed to Resolve: {new_eval['weakest_point']}")
            stagnation_count = yield_decision.stagnant_window
            last_failure_reason = new_eval["weakest_point"]
            current_target_weakest_point = new_eval["weakest_point"]  # GP-002: update targeting even on non-improving iterations
            pending_loop_action = yield_decision.action
            _append_iteration_telemetry(
                workspace_dir,
                iteration_index=i + 1,
                iteration_start_utc=iteration_start_utc,
                loop_control_action=current_loop_control_action,
                score=new_eval["score"],
                score_improved=False,
                champion_promoted=False,
                stagnation_count=stagnation_count,
                gate_engagement=gate_engagement,
                gate_failure_count=gate_failure_count,
                failed_gate_ids=failed_gate_ids,
                escalation_flags=escalation_flags,
                falsification_mode=rubric_falsification_mode,
                mutator_model_id=current_mutator,
                judge_model_id=JUDGE_MODEL_ID,
                mutator_usage=_usage_delta(
                    iteration_mutator_usage_before,
                    _usage_bucket_snapshot(SESSION_MUTATOR_USAGE),
                ),
                judge_usage=_usage_delta(
                    iteration_judge_usage_before,
                    _usage_bucket_snapshot(SESSION_JUDGE_USAGE),
                ),
                pending_loop_action=pending_loop_action.value,
            )
            last_completed_iteration = i + 1
            _pop_seed_queue(workspace_dir, _comp_seed_injected)
            # GP-074 Component C: fire analyzer on stagnation with degenerate fit
            if rubric_data.get("enable_component_c", False):
                _cc_gt_module = rubric_data.get("component_c_gt_module")
                _cc_fit_path = workspace_dir / "fit_result.json"
                if _cc_gt_module and _cc_fit_path.exists():
                    try:
                        _cc_fit = json.loads(_cc_fit_path.read_text())
                        _cc_max_res = _cc_fit.get("max_abs_residual", 1.0)
                        _cc_mod = importlib.import_module(_cc_gt_module)
                        if not hasattr(_cc_mod, "f_true"):
                            raise AttributeError(f"GT module '{_cc_gt_module}' does not expose f_true()")
                        if not hasattr(_cc_mod, "f_dominant"):
                            raise AttributeError(f"GT module '{_cc_gt_module}' does not expose f_dominant()")
                        _cc_f_true = _cc_mod.f_true
                        _cc_f_dominant = _cc_mod.f_dominant
                        _cc_test_model_path = Path(f"{PROJECT_DIR}/test_model.py")
                        _cc_spec = importlib.util.spec_from_file_location("_cc_test_model", _cc_test_model_path)
                        if _cc_spec is None or _cc_spec.loader is None:
                            raise ImportError(f"cannot build spec for {_cc_test_model_path}")
                        _cc_test_mod = importlib.util.module_from_spec(_cc_spec)
                        _cc_spec.loader.exec_module(_cc_test_mod)
                        if not hasattr(_cc_test_mod, "f"):
                            raise AttributeError("test_model.py does not expose f() — Component C skipped")
                        _cc_f_model = _cc_test_mod.f
                        _cc_evidence = []
                        if evidence_text:
                            for _cc_line in evidence_text.strip().splitlines():
                                _cc_line = _cc_line.strip()
                                if not _cc_line or _cc_line.startswith("#"):
                                    continue
                                _cc_parts = _cc_line.split()
                                if len(_cc_parts) >= 3:
                                    try:
                                        _cc_evidence.append((float(_cc_parts[0]), float(_cc_parts[1]), float(_cc_parts[2])))
                                    except ValueError:
                                        continue
                        if _cc_evidence:
                            _cc_stagnation_k = rubric_data.get("component_c_stagnation_k", 3)
                            _cc_result = analyze_residual(
                                workspace_dir=workspace_dir,
                                iteration_index=i + 1,
                                f_model=_cc_f_model,
                                f_true=_cc_f_true,
                                f_dominant=_cc_f_dominant,
                                evidence_triples=_cc_evidence,
                                max_abs_residual=float(_cc_max_res),
                                substrate_id=args.project,
                                stagnation_k=_cc_stagnation_k,
                            )
                            print(f"🔧 GP-074 Component C: {_cc_result.status} "
                                  f"(stag={_cc_result.stagnation_count}, "
                                  f"probes={_cc_result.probe_count})")
                            if _cc_result.descriptor:
                                print(f"    descriptor: {_cc_result.descriptor.continuity}/{_cc_result.descriptor.monotonicity} "
                                      f"(candidates={_cc_result.candidate_count})")

                            # GP-076: Predictive Divergence Sweep
                            # Uses outer loop stagnation_count, not _cc_result.stagnation_count —
                            # Component C resets its counter to 0 on every emission, so
                            # _cc_result.stagnation_count is always 0 when a descriptor is present.
                            # Threshold mirrors component_c_stagnation_k so both fire together.
                            #
                            # PERSISTENCE FIX: Component C only emits on its own stagnation
                            # schedule (every K inner iterations). On non-emission iterations,
                            # _cc_result.descriptor is None even though a prior descriptor was
                            # persisted to residual_fingerprint.json. Fall back to the persisted
                            # descriptor so the sweep can fire on any iteration where outer
                            # stagnation >= threshold, not only on Component C emission iterations.
                            _cc_active_descriptor = _cc_result.descriptor
                            if not _cc_active_descriptor:
                                _fp_persisted = workspace_dir / "residual_fingerprint.json"
                                if _fp_persisted.exists():
                                    try:
                                        _fp_data = json.loads(_fp_persisted.read_text())
                                        if _fp_data.get("status") == "emitted" and _fp_data.get("descriptor"):
                                            from src.ztare.validator.information_yield import ShapeDescriptor
                                            _cc_active_descriptor = ShapeDescriptor(**_fp_data["descriptor"])
                                    except Exception:
                                        pass
                            if (_cc_active_descriptor
                                    and stagnation_count >= _cc_stagnation_k
                                    and float(_cc_max_res) < 1.0):
                                try:
                                    # Corrector isolation: f_true(u,v) - f_dominant(u,v)
                                    # for ALL evidence triples. Average per-v across
                                    # u-values to detect v-only vs u-dependent correctors.
                                    _sweep_v_residuals: dict[int, list[float]] = {}
                                    for _eu, _ev, _ in _cc_evidence:
                                        _cr = float(_cc_f_true(_eu, _ev) - _cc_f_dominant(_eu, _ev))
                                        _sweep_v_residuals.setdefault(_ev, []).append(_cr)
                                    _sweep_corrector_data = [
                                        (v, sum(rs) / len(rs))
                                        for v, rs in sorted(_sweep_v_residuals.items())
                                    ]
                                    # Check if corrector varies with u (would mean
                                    # 1D library forms cannot capture it)
                                    _sweep_u_dependent = any(
                                        max(rs) - min(rs) > 0.5
                                        for rs in _sweep_v_residuals.values()
                                        if len(rs) > 1
                                    )
                                    if _sweep_u_dependent:
                                        print("🔬 GP-076 sweep: corrector varies with u — 1D library insufficient")

                                    _sweep_descriptor_forms = filter_by_descriptor(
                                        is_smooth=(_cc_active_descriptor.continuity == "smooth"),
                                        is_monotone=(_cc_active_descriptor.monotonicity == "monotone"),
                                    )
                                    # Use u=1 slice for the single-point query (the
                                    # query returns one observation at one v regardless)
                                    _sweep_ref_u = min(u for u, _, _ in _cc_evidence)

                                    def _sweep_gt_corrector(v: int) -> float:
                                        return float(_cc_f_true(_sweep_ref_u, v) - _cc_f_dominant(_sweep_ref_u, v))

                                    _sweep_result = run_divergence_sweep(
                                        corrector_data=_sweep_corrector_data,
                                        f_true_corrector=_sweep_gt_corrector,
                                        descriptor_forms=_sweep_descriptor_forms,
                                        v_max_visible=max(_sweep_v_residuals.keys()),
                                        stagnation_count=stagnation_count,
                                        run_length=ITERATIONS,
                                        workspace_dir=workspace_dir,
                                    )
                                    print(f"🔬 GP-076 sweep: {_sweep_result.status} — {_sweep_result.message}")
                                    if _sweep_result.survivors:
                                        _survivor_names = [s.form.name for s in _sweep_result.survivors]
                                        print(f"    survivors: {_survivor_names}")
                                    if _sweep_result.library_exhausted:
                                        print("    >> FEYNMAN WALL: library exhausted — LLM topology proposal mode")
                                except Exception as _sweep_exc:
                                    print(f"🔬 GP-076 sweep: error — {_sweep_exc}")
                    except Exception as _cc_exc:
                        print(f"🔧 GP-074 Component C: error — {_cc_exc}")
            _restore_project_state(best_state)
            if os.path.exists(f"{AXIOM_PATH}.bak"):
                shutil.copy(f"{AXIOM_PATH}.bak", AXIOM_PATH)

    except subprocess.CalledProcessError:
        print("⚠️ Auditor Subprocess Crashed. Logging stagnation...")
        signal = IterationSignal(
            iteration_index=i + 1,
            score=best_score,
            weakest_point="Auditor subprocess crashed",
            runtime_failure=True,
            catastrophic_failure=True,
            falsification_mode=rubric_falsification_mode,
            claim_delta_type=mutation_declaration.claim_delta_type.value if mutation_declaration is not None else "",
            committee_digest=current_committee_digest,
            prior_committee_digest=iteration_prior_committee_digest,
        )
        iteration_history.append(signal)
        yield_decision = evaluate_information_yield(iteration_history, underidentified_after=args.underidentified_after)
        _write_latest_information_yield(workspace_dir, signal=signal, decision=yield_decision)
        stagnation_count = yield_decision.stagnant_window
        pending_loop_action = yield_decision.action
        _append_iteration_telemetry(
            workspace_dir,
            iteration_index=i + 1,
            iteration_start_utc=iteration_start_utc,
            loop_control_action=current_loop_control_action,
            score=None,
            score_improved=False,
            champion_promoted=False,
            stagnation_count=stagnation_count,
            gate_engagement=False,
            gate_failure_count=0,
            failed_gate_ids=[],
            escalation_flags={"self_reference": False, "semantic_escalation": False},
            falsification_mode=rubric_falsification_mode,
            mutator_model_id=current_mutator,
            judge_model_id=JUDGE_MODEL_ID,
            mutator_usage=_usage_delta(
                iteration_mutator_usage_before,
                _usage_bucket_snapshot(SESSION_MUTATOR_USAGE),
            ),
            judge_usage=_usage_delta(
                iteration_judge_usage_before,
                _usage_bucket_snapshot(SESSION_JUDGE_USAGE),
            ),
            pending_loop_action=pending_loop_action.value,
        )
        last_completed_iteration = i + 1
        _pop_seed_queue(workspace_dir, _comp_seed_injected)
        _restore_project_state(best_state)
        time.sleep(5)

    # GP-087 Slim: Residual-driven primitive injection.
    # When the farther-tail gate fails, propose tail-correction seeds
    # from the primitive library. Takes priority over Component D —
    # if GP-087 injects seeds, skip the regular composition loop.
    # Information boundary: only primitive names reach the seed queue,
    # no farther-tail residual values leak to the mutator.
    #
    # Short-circuit fix (2026-04-19): Component D was clobbering GP-087
    # seeds because the old guard (`not seed_path.exists()`) prevented
    # GP-087 from firing whenever Component D had already written its
    # own candidates to composition_seed.json. The fix: check the *source*
    # field of existing seeds. If they are component_d_autonomous, GP-087
    # may overwrite them. If they are already gp087_residual_driven, block
    # Component D but do not re-inject (seeds are already queued).
    _gp087_injected = False
    if rubric_data.get("enable_fit_primitive", False):
        _seed_path_087 = workspace_dir / "composition_seed.json"
        # Only fire GP-087 when new_eval has fresh gate data (not after crash)
        _gp087_eval = new_eval if isinstance(new_eval, dict) and "score_contract" in new_eval else None

        # Check whether existing seed file already contains GP-087 seeds.
        _existing_gp087_queued = False
        if _seed_path_087.exists():
            try:
                _existing_q = json.loads(_seed_path_087.read_text())
                if isinstance(_existing_q, list):
                    _existing_gp087_queued = any(
                        s.get("source") == "gp087_residual_driven" for s in _existing_q
                    )
            except Exception:
                pass

        if _existing_gp087_queued:
            # Tail-correction seeds are already in queue. Block Component D
            # from overwriting them; they will be consumed next iteration.
            _gp087_injected = True
            print("    >> GP-087: tail-correction seeds already queued — Component D blocked")
        elif _gp087_eval is not None:
            # Seed file is absent or contains only component_d_autonomous
            # candidates — GP-087 may overwrite.
            _gp087_seeds = _gp087_propose_tail_correction_seeds(
                _gp087_eval,
                workspace_dir,
                rubric_data,
                iteration_index=i + 1,
                stagnation_count=stagnation_count,
            )
            if _gp087_seeds:
                _seed_path_087.write_text(json.dumps(_gp087_seeds, indent=2) + "\n")
                _gp087_injected = True
                print(
                    f"    >> GP-087: farther-tail gate failed — injected {len(_gp087_seeds)} "
                    f"tail-correction seeds (overwrote component_d queue)"
                )
                for _qi, _qs in enumerate(_gp087_seeds[:3]):
                    print(
                        f"       [{_qi+1}] +{_qs.get('correction_primitive','?')} "
                        f"(round={_qs.get('round','')})"
                    )

    # H-GP103-5 Compositional Hypothesis Generator.
    # Fires when GP-087 has NOT injected seeds and ≥2 structurally distinct
    # families show regime-separated visible residuals (one family dramatically
    # better than another at visible, signalling different gate failure layers).
    # Proposes additive two-regime composites of the top-performing failed
    # families.  Takes priority over Component D — if additive seeds are
    # injected, Component D is skipped so seeds are not overwritten.
    # Information boundary: reads only visible residuals and example expressions
    # from structural_memory.json — no holdout / farther-tail values reach seeds.
    _gp103_injected = False
    _gp103_stagnation_k = int(rubric_data.get("gp103_stagnation_threshold", 1))
    # H-GP103-5: GP-087 and H-GP103-5 are NOT mutually exclusive.
    # GP-087 injects tail-correction seeds; H-GP103-5 injects additive composite seeds.
    # They address orthogonal failure modes and can co-fire in the same iteration.
    # The prior `and not _gp087_injected` mutex caused a deadlock: whenever GP-087
    # fired (far-tail failure → stagnation), H-GP103-5 was blocked, preventing it
    # from ever accumulating the ≥2 failed-family pairs it requires.
    if (
        rubric_data.get("enable_fit_primitive", False)
        and stagnation_count >= _gp103_stagnation_k
    ):
        try:
            _comp_ind_vars_103: list[str] = rubric_data.get("fit_required_vars", ["u"])
            _gate_thr_103 = float(rubric_data.get("gate_residual_threshold", 0.08))
            _fam_a, _fam_b = detect_additive_composite_opportunity(
                workspace_dir,
                gate_threshold=_gate_thr_103,
                stagnation_count=stagnation_count,
            )
            if _fam_a is not None and _fam_b is not None:
                # Only inject if no gp103_additive_composite seed is already queued.
                _seed_path_103 = workspace_dir / "composition_seed.json"
                _existing_gp103_queued = False
                if _seed_path_103.exists():
                    try:
                        _existing_q103 = json.loads(_seed_path_103.read_text())
                        if isinstance(_existing_q103, list):
                            _existing_gp103_queued = any(
                                s.get("source") == "gp103_additive_composite"
                                for s in _existing_q103
                            )
                    except Exception:
                        pass
                _gp103_pair = (
                    str(_fam_a.get("fingerprint", "")),
                    str(_fam_b.get("fingerprint", "")),
                )
                if not _existing_gp103_queued and _gp103_pair not in _gp103_tried_pairs:
                    _gp103_seeds = generate_additive_composite_seeds(
                        _fam_a,
                        _fam_b,
                        _comp_ind_vars_103,
                        iteration_index=i + 1,
                    )
                    if _gp103_seeds:
                        _seed_path_103.write_text(json.dumps(_gp103_seeds, indent=2) + "\n")
                        _gp103_injected = True
                        _gp103_tried_pairs.add(_gp103_pair)
                        print(
                            f"    >> H-GP103-5: regime-separated families detected — "
                            f"injected {len(_gp103_seeds)} additive composite seeds"
                        )
                        print(
                            f"       family_a: res={_fam_a.get('best_visible_max_abs_residual'):.4f} "
                            f"({_fam_a.get('family_label','')[:50]})"
                        )
                        print(
                            f"       family_b: res={_fam_b.get('best_visible_max_abs_residual'):.4f} "
                            f"({_fam_b.get('family_label','')[:50]})"
                        )
                elif _existing_gp103_queued:
                    print(f"    >> H-GP103-5: skipped — composite seed already queued")
                elif _gp103_pair in _gp103_tried_pairs:
                    print(f"    >> H-GP103-5: skipped — pair already tried this run")
            else:
                # Explain why no pair was found
                print(f"    >> H-GP103-5: checked (stag={stagnation_count}) — no regime-separated pair found (guard blocked or <2 families)")
        except Exception as _gp103_exc:
            print(f"    >> H-GP103-5: error — {_gp103_exc}")

    # GP-078 Component D: Universal Feynman Wall check.
    # Fires at the end of every iteration, substrate-agnostic.
    # Reads structural_memory.json — if library exhaustion is detected,
    # runs the composition loop to bootstrap new primitives.
    # GP-087: skip if residual-driven seeds were already injected.
    # H-GP103-5: also skip if additive composite seeds were injected.
    if rubric_data.get("enable_fit_primitive", False) and not _gp087_injected and not _gp103_injected:
        try:
            _comp_budget = int(rubric_data.get("composition_budget", 20))
            _comp_stagnation_k = int(rubric_data.get("composition_stagnation_threshold", 3))
            _comp_min_families = int(rubric_data.get("composition_min_families", 6))
            if detect_feynman_wall(
                workspace_dir,
                stagnation_count,
                min_families=_comp_min_families,
                stagnation_threshold=_comp_stagnation_k,
            ):
                print("    >> FEYNMAN WALL: library exhausted — Component D composition mode")
                # Parse visible evidence preserving all columns (supports nD substrates).
                # Each row becomes a tuple of floats: (x1, [x2, ...], z).
                _comp_evidence: list[tuple[float, ...]] = []
                if evidence_text:
                    for _comp_line in evidence_text.strip().splitlines():
                        _comp_line = _comp_line.strip()
                        if not _comp_line or _comp_line.startswith("#"):
                            continue
                        _comp_parts = _comp_line.split()
                        if len(_comp_parts) >= 2:
                            try:
                                _comp_evidence.append(
                                    tuple(float(x) for x in _comp_parts)
                                )
                            except ValueError:
                                continue
                if _comp_evidence:
                    _comp_ind_vars: list[str] = rubric_data.get("fit_required_vars", ["n"])
                    _comp_var_name: str = _comp_ind_vars[0] if _comp_ind_vars else "n"
                    _comp_result = run_composition_loop(
                        workspace_dir,
                        _comp_evidence,
                        model_id=resolve_model_id(args.mutator_model),
                        budget=_comp_budget,
                        iteration_index=i + 1,
                        var_name=_comp_var_name,
                        ind_vars=_comp_ind_vars,
                    )
                    print(
                        f"    >> Component D: {_comp_result.get('wall_exit_code')} "
                        f"({_comp_result.get('successes', 0)} fits in "
                        f"{_comp_result.get('rounds', 0)} rounds)"
                    )
                    # GP-078 Fix B v2: Topological Beam Search.
                    # Component D is blind to the holdout — it cannot know
                    # which candidate has the correct asymptotic behavior.
                    # Instead of picking one winner, write a queue of top-K
                    # candidates.  The judge falsifies them one per iteration
                    # until the correct physics survives.
                    #
                    # Saturating-first sort: depth-2 corrections that saturate
                    # (exp_decay, reciprocal, tanh) are tested before those
                    # that diverge (linear, power, polynomial).  This is a
                    # physical prior (macroscopic values rarely diverge to
                    # infinity), not an overfit to any specific substrate.
                    _SATURATING_BASES = frozenset([
                        "exp_decay", "reciprocal", "tanh", "logistic",
                        "rational", "sqrt_reciprocal", "log_reciprocal",
                    ])
                    _comp_rounds = _comp_result.get("round_results", [])
                    if _comp_rounds:
                        _successes = [r for r in _comp_rounds if r.get("status") == "fit_success"]

                        def _asymptotic_sort_key(r: dict) -> tuple:
                            """Sort saturating corrections and ratio probes
                            before diverging ones, then by residual."""
                            _round_label = str(r.get("round", ""))
                            # Ratio probes (cosh/sinh, exp/exp_decay, …) are
                            # pure rational/hyperbolic symmetries — saturating
                            # by definition.
                            _is_ratio = r.get("probe_type") == "ratio"
                            _is_saturating = _is_ratio or any(
                                base in _round_label for base in _SATURATING_BASES
                            )
                            # Priority: 0 = saturating/ratio, 1 = diverging
                            _priority = 0 if _is_saturating else 1
                            _res = float(r.get("visible_max_abs_residual", 999))
                            return (_priority, _res)

                        _successes.sort(key=_asymptotic_sort_key)

                        # Grammar filter: remove candidates that use
                        # functions forbidden by the rubric grammar.
                        # Without this, grammar-illegal candidates
                        # (e.g. sinh/cosh under math_exp_only) fill
                        # the queue and get rejected every iteration,
                        # creating an infinite burn loop.
                        _grammar = str(rubric_data.get("fit_expression_grammar", "") or "").strip().lower()
                        if _grammar == "math_exp_only":
                            _FORBIDDEN_MATH = re.compile(
                                r"math\.(sin|cos|tan|sinh|cosh|tanh|asin|acos|atan)"
                            )
                            _before = len(_successes)
                            _successes = [
                                s for s in _successes
                                if not _FORBIDDEN_MATH.search(s.get("expression", ""))
                            ]
                            _filtered = _before - len(_successes)
                            if _filtered:
                                print(
                                    f"    >> Grammar filter: removed {_filtered} "
                                    f"math_exp_only violations from seed queue"
                                )

                        _top_k = _successes[:5]

                        if _top_k:
                            _seeds = []
                            for _comp in _top_k:
                                _seeds.append({
                                    "source": "component_d_autonomous",
                                    "expression": _comp.get("expression", ""),
                                    "independent_vars": _comp_ind_vars,
                                    "parameter_names": _comp.get("parameter_names", []),
                                    "visible_max_abs_residual": _comp.get("visible_max_abs_residual"),
                                    "iteration_synthesized": i + 1,
                                    "round": _comp.get("round", ""),
                                })
                            _seed_path = workspace_dir / "composition_seed.json"
                            _seed_path.write_text(json.dumps(_seeds, indent=2) + "\n")
                            print(
                                f"    >> Component D seed queue: {len(_seeds)} candidates "
                                f"({sum(1 for s in _top_k if any(b in str(s.get('round','')) for b in _SATURATING_BASES))} saturating-first)"
                            )
                            for _qi, _qs in enumerate(_seeds[:3]):
                                print(
                                    f"       [{_qi+1}] {_qs['expression'][:70]} "
                                    f"(max|res|={_qs.get('visible_max_abs_residual', '?')})"
                                )
        except Exception as _comp_exc:
            print(f"    >> Component D: error — {_comp_exc}")

    time.sleep(1)

# End of loop
_finalize_run_telemetry_once()
print("\n" + "=" * 50)
print("🏁 OPTIMIZATION LOOP COMPLETE")
print(f"Final Score: {best_score}")
print(
    "Mutator Usage: "
    f"input={SESSION_MUTATOR_USAGE['input_tokens']:,} "
    f"output={SESSION_MUTATOR_USAGE['output_tokens']:,} "
    f"thinking={SESSION_MUTATOR_USAGE['thinking_tokens']:,} "
    f"cache_read={SESSION_MUTATOR_USAGE['cache_read_input_tokens']:,}"
)
print(f"Estimated Mutator Cost: {_format_cost_label(SESSION_MUTATOR_USAGE)}")
print(
    "Judge Usage: "
    f"input={SESSION_JUDGE_USAGE['input_tokens']:,} "
    f"output={SESSION_JUDGE_USAGE['output_tokens']:,} "
    f"thinking={SESSION_JUDGE_USAGE['thinking_tokens']:,} "
    f"cache_read={SESSION_JUDGE_USAGE['cache_read_input_tokens']:,}"
)
print(f"Estimated Judge Cost: {_format_cost_label(SESSION_JUDGE_USAGE)}")
print("=" * 50 + "\n")
