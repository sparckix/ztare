import os
import json
import importlib
import importlib.util
import math
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
    get_model_family,
)
from src.ztare.common.paths import DOCS_DIR, PROJECTS_DIR, REPO_ROOT, RUBRICS_DIR
from src.ztare.validator.mform_alignment_audit import (
    apply_mform_pending,
    maybe_fire_mform_audit,
)
import re
from src.ztare.primitives.primitive_library import format_transfer_hypotheses, retrieve_primitives
from src.ztare.validator.core.mutation_contract import (
    MutationMismatchCode,
    approved_primitive_keys,
    evaluate_mutation_declaration,
    parse_mutation_declaration,
)
from src.ztare.validator.core.runner_selection import CandidateScopeVerdict, evaluate_candidate_selection
from src.ztare.validator.utilities.v4_family import is_v4_family_project
from src.ztare.validator.core.information_yield import (
    IterationSignal,
    LoopControlAction,
    apply_latent_motion_veto,
    evaluate_information_yield,
)
from src.ztare.validator.utilities.pivot_heuristics import (
    resolve_stagnation_pivot_state,
)
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
from src.ztare.fit.mutation_suite_guard import (
    validate_python_suite_candidate,
    validate_python_suite_imports,
    attest_visible_mre,
)
from src.ztare.validator.core.charter_parsing import (
    extract_anchor_proxies_from_charter,
    extract_forecast_type_from_charter,
)
from src.ztare.supervisor.supervisor_usage import estimate_cost_usd, load_model_pricing
from src.ztare.validator.utilities.champion_artifacts import (
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

# GP-157 v5.0 Phase 3b — Cage observe-mode wire-in (2026-04-25 night).
# ADDITIVE ONLY: Cage runs alongside existing dispatch logic, logs
# engagement decisions to workspace/cage_engagement.jsonl, and NEVER
# replaces existing flow. Activated per-rubric via `cage_observe_mode: true`.
# Without that flag, this import is unused and Cage is dormant.
# Phase 3c (later) will replace existing dispatch with Cage when
# observe-mode validates parity across substrates.
try:
    from src.ztare.gates.registry import get_default_cage as _v5_get_default_cage
    _V5_CAGE_AVAILABLE = True
except Exception:  # noqa: BLE001
    _V5_CAGE_AVAILABLE = False

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
parser.add_argument("--rubric", default=None, help="Rubric name (defaults to --project value)")
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
    choices=["gemini", "gemini-lite", "gemini-pro", "claude", "claude-opus", "gpt4o", "gpt4.1", "gpt4.1-mini", "gpt5.5", "o1", "o3", "o3-mini", "o3-pro", "o4-mini"],
    help="Model family to use as Mutator.",
)
parser.add_argument(
    "--judge_model",
    type=str,
    default="gemini",
    choices=["gemini", "gemini-lite", "gemini-pro", "claude", "claude-opus", "gpt4o", "gpt4.1", "gpt4.1-mini", "gpt5.5", "o1", "o3", "o3-mini", "o3-pro", "o4-mini"],
    help="Model family to use as Verification Panel and Meta-Judge.",
)
parser.add_argument(
    "--committee_model",
    type=str,
    default=None,
    choices=[None, "gemini", "gemini-lite", "gemini-pro", "claude", "claude-opus", "gpt4o", "gpt4.1", "gpt4.1-mini", "gpt5.5", "o1", "o3", "o3-mini", "o3-pro", "o4-mini"],
    help=(
        "Model family for committee (--dynamic) generation. Defaults "
        "to --judge_model when --dynamic is set; ignored when --dynamic "
        "is not set. Useful when the committee generator should match "
        "the judge model rather than hardcoding gemini-2.5-flash."
    ),
)
parser.add_argument(
    "--require_cross_family",
    action="store_true",
    help=(
        "Enforce epistemic airgap: error if mutator and judge models are "
        "from the same provider family (OpenAI/Anthropic/Google). "
        "Reduces shared-blind-spot risk in adversarial evaluation."
    ),
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
if args.rubric is None:
    args.rubric = args.project
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

# Keep legacy `client` pointing to Gemini — Verification Panel and Meta-Judge always use it
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

# ── Epistemic Airgap check ──────────────────────────────────────────
_mutator_family = get_model_family(MUTATOR_MODEL_ID)
_judge_family = get_model_family(JUDGE_MODEL_ID)
if _mutator_family == _judge_family:
    _airgap_msg = (
        f"Mutator ({MUTATOR_MODEL_ID}) and Judge ({JUDGE_MODEL_ID}) "
        f"are both from the {_mutator_family} family. "
        "Same-family evaluation increases shared-blind-spot risk."
    )
    if args.require_cross_family:
        raise SystemExit(f"❌ Epistemic Airgap violation: {_airgap_msg}")
    else:
        print(f"⚠️  Epistemic Airgap warning: {_airgap_msg}")

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
    falsification_mode: str | None,
    stagnation_count: int,
    rubric_mode: str | None = None,
    rubric_stagnation_override: int | None = None,
) -> str:
    if dynamic_enabled and pending_loop_action in {
        LoopControlAction.REFRESH_SPECIALISTS,
        LoopControlAction.PIVOT_REQUIRED,
    }:
        return "refresh_specialists"
    return resolve_stagnation_pivot_state(
        is_v4_project=is_v4_project,
        falsification_mode=falsification_mode,
        stagnation_count=stagnation_count,
        rubric_mode=rubric_mode,
        rubric_stagnation_override=rubric_stagnation_override,
    ).loop_control_action


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
    raw_judge_score: int | None = None,
    score_cap_reason: str | None = None,
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
        "raw_judge_score": raw_judge_score,
        "score_cap_reason": score_cap_reason,
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
        # GP-167 fix (2026-04-25 night, panel-revealed): previous behavior
        # returned compare_score=None, which made the caller treat the saved
        # baseline as if it never existed and silently promote any new
        # score (even 0) over a previously-saved 50. That destroyed the
        # operator's accumulated work whenever the rubric was edited mid-run.
        # Now: keep the raw saved score as the comparison anchor so the new
        # candidate must actually beat it; flag status as "regime_mismatch"
        # so the caller can choose to demote rather than discard.
        return {
            "compare_score": raw_saved_score,
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
        # 2026-04-27 hotfix (WAR-T17): AXIOM_PATH was missing from this tuple,
        # which meant `_capture_project_state(...)` snapshots never included
        # verified_axioms.json. Subsequent `_restore_project_state(snapshot)`
        # calls (on iter rollback / failed promotion) couldn't restore it,
        # leaving the file at whatever the merge code wrote (often `[]`).
        # Including it here ensures operator-curated bridge axioms +
        # successor_lock survive iter rollbacks.
        AXIOM_PATH,
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


def _refresh_latest_evidence_gaps_from_eval(evaluation: dict, artifact_role: str = "latest") -> None:
    """Write evidence gaps from the current eval result to latest_evidence_gaps.json.

    Fixes: LATEST_EVIDENCE_GAPS_PATH was never written by the loop — only by rubric-review.
    This meant evidence-fetch always saw stale gaps from the last manual rubric-review run.
    """
    gaps = evaluation.get("evidence_gaps")
    if not gaps:
        return
    score_contract = evaluation.get("score_contract") or {}
    payload = {
        "project": args.project,
        "judge_model": score_contract.get("judge_model", ""),
        "generated_on": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "artifact_role": artifact_role,
        "describes_baseline": artifact_role,
        "score": evaluation.get("score"),
        "weakest_point": evaluation.get("weakest_point", ""),
        "evidence_boundary_ceiling_detected": score_contract.get("evidence_boundary_ceiling_detected", False),
        "cap_reason": score_contract.get("evidence_boundary_detail", ""),
        "cap_reason_detail": "",
        "score_regime_fingerprint": _score_regime_fingerprint_from_score_contract(evaluation.get("score_contract")),
        "evidence_gaps": gaps,
    }
    write_json(LATEST_EVIDENCE_GAPS_PATH, payload)


def _refresh_derived_constraints_from_eval(
    evaluation: dict,
    *,
    run_id: int,
    iteration_index: int,
    artifact_role: str = "latest",
) -> None:
    proposals = sanitize_constraint_proposals(evaluation.get("derived_constraints"))
    confirmation_threshold = int(rubric_data.get("confirmation_threshold_runs", 2) or 2)
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
        confirmation_threshold_runs=confirmation_threshold,
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


def _stagnation_trigger_mode() -> str:
    """Task 12 rubric flag: 'score' (legacy) | 'new_class' (Gemini Inversion #3).

    When 'new_class', evaluate_information_yield resets stagnation when the
    iteration's weakest-link class has not been seen earlier in the session.
    Champion persistence profile (GP-148) shows 28 iters / 10 distinct classes;
    score-only stagnation prematurely kills class-cycling. Default 'score'.
    """
    try:
        return str(rubric_data.get("stagnation_trigger_mode") or "score").strip().lower()
    except Exception:
        return "score"


def _populate_weakest_class(signal: IterationSignal) -> IterationSignal:
    """Enrich signal.weakest_class via runtime classifier (cheap regex).

    Returns the input unchanged when already populated, classification fails,
    or the weakest_point string is empty. Uses dataclasses.replace since
    IterationSignal is frozen.
    """
    if signal.weakest_class or not signal.weakest_point:
        return signal
    try:
        from src.ztare.validator.weakest_link_classifier import classify_weakest_point
        cls = classify_weakest_point(signal.weakest_point)
    except Exception:
        return signal
    if not cls:
        return signal
    import dataclasses as _dc
    return _dc.replace(signal, weakest_class=cls)


def _evaluate_post_eval_loop_control(
    workspace_dir: Path,
    *,
    signal: IterationSignal,
) -> tuple[object, dict | None]:
    # Task 12: enrich the freshly-appended signal with weakest_class before yield eval.
    if iteration_history and iteration_history[-1] is signal:
        enriched = _populate_weakest_class(signal)
        if enriched is not signal:
            iteration_history[-1] = enriched
            signal = enriched
    _class_mode = _stagnation_trigger_mode() == "new_class"
    raw_decision = evaluate_information_yield(
        iteration_history,
        underidentified_after=args.underidentified_after,
        class_novelty_mode=_class_mode,
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


def _validate_bounded_discriminator_suite(
    python_code: str,
    allowed_extra_imports: tuple[str, ...] | None = None,
    project_dir: str | None = None,
) -> None:
    """GP-007: bounded-discriminator suites must be portable in the runner env.

    GP-134 extension (2026-04-23): rubrics may declare a
    `runner_allowed_imports` field that extends the allowlist beyond
    stdlib. This is required for discrete number-theoretic substrates
    (py_exec grammar) where stdlib has no primality / factorization
    primitives and sympy is the canonical choice. The runner venv must
    have these installed; the rubric's `runner_allowed_imports`
    declaration is the documented contract.

    GP-166 contract-collision fix (2026-04-25 night): N-D feature-dict
    substrates expose canonical data accessors via `features.py` in
    the project directory. The R1 stdlib-only rule was designed to
    prevent apparatus-import bypass (`from src.ztare.* import …`), not
    to forbid project-local substrate adapters. When `project_dir`
    contains a `features.py`, allow `from features import …` in the
    falsification suite. This eliminates the gp159 / gp163d collision
    where the mutator was forced to inline data, which then triggered
    the "module-level I_model calls" R1 strike on the next attempt
    (because inline data was indistinguishable from import-time
    evaluation). With features import allowed, the mutator can write
    `from features import VISIBLE_ROWS; for row in VISIBLE_ROWS: ...`
    directly — no inlining, no module-level call ambiguity.
    """
    try:
        tree = ast.parse(python_code)
    except SyntaxError as exc:
        raise ValueError(f"Bounded-discriminator suite has invalid Python syntax: {exc}") from exc

    stdlib_modules = getattr(sys, "stdlib_module_names", frozenset())
    extra_allowed = set(allowed_extra_imports or ())

    # Auto-extend allowlist with project-local substrate adapter modules.
    # `features.py` is the canonical N-D feature-dict adapter; auto-allow
    # when present so the mutator can use real data in the suite.
    if project_dir:
        try:
            _proj = Path(project_dir)
            if (_proj / "features.py").exists():
                extra_allowed.add("features")
        except Exception:
            pass  # never let allowlist extension break the validator
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
            if name in stdlib_modules or name in extra_allowed:
                continue
            disallowed.append(name)

    if disallowed:
        unique = ", ".join(sorted(set(disallowed)))
        allowed_hint = (
            f" Allowed extras for this rubric: {sorted(extra_allowed)}."
            if extra_allowed
            else ""
        )
        raise ValueError(
            "Bounded-discriminator suite imports non-standard dependencies "
            f"({unique}). Use standard-library-only Python and plain `assert` statements."
            + allowed_hint
        )


def _prepare_mutation_candidate(
    *,
    raw_text: str,
    current_thesis: str,
    current_test_model: str,
    falsification_mode: str | None = None,
    runner_allowed_imports: tuple[str, ...] | None = None,
    project_dir: str | None = None,
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
        _validate_bounded_discriminator_suite(
            python_code,
            allowed_extra_imports=runner_allowed_imports,
            project_dir=project_dir,
        )

    # GP-156 R1 hardening (2026-04-25): import-time exec dry-run.
    # Catches the iter-3 / gp155-iter-1 failure mode where the mutator
    # emits a thesis whose top-level code raises TypeError / AttributeError
    # / NameError / ImportError on module load. The harness would
    # otherwise discover this only at gate_harness.py time, wasting the
    # iteration on a contract failure. By rejecting at R1, the mutator
    # gets sharper feedback and the iteration is re-prompted instead of
    # consumed.
    if python_code is not None:
        try:
            _r1_project_dir = str(Path(PROJECT_DIR).resolve()) if "PROJECT_DIR" in globals() else None
        except Exception:
            _r1_project_dir = None
        # GP-156 fix (2026-04-25): substrate-class-aware I_model requirement.
        # Audit/meta substrates (gp156-style) don't have an I_model contract;
        # opt out via rubric.require_i_model_in_submission=false. Default true
        # for back-compat with predictor substrates.
        _require_i_model = bool(rubric_data.get("require_i_model_in_submission", True))
        # GP-156 force-opt-in (2026-04-25): when the rubric explicitly enables
        # the feature-vector fit primitive, the substrate was designed for
        # apparatus-fit constants. Mutators must declare PARAMETRIC_FORM +
        # PARAMETER_NAMES; opting out is gaming, not a valid escape from K_law.
        _require_pform = bool(rubric_data.get("enable_fit_primitive_features", False))
        validate_python_suite_imports(
            python_code,
            project_dir=_r1_project_dir,
            require_i_model=_require_i_model,
            require_parametric_form=_require_pform,
        )

        # GP-156 Proposal 2 (2026-04-25): visible-MRE attestation.
        # If the thesis prose claims a numerical visible-MRE, compute
        # the actual visible-MRE from the candidate's I_model and
        # compare. Discrepancy beyond tolerance → R1 reject so the
        # mutator must fix the prose-vs-code gap before consuming an
        # iteration. No-op on substrates without VISIBLE_SET (gp146,
        # gp145b) and on theses that make no MRE claim.
        try:
            attest_visible_mre(python_code, clean_thesis, project_dir=_r1_project_dir)
        except ValueError:
            # Re-raise: ValueError surfaces as Runner R1 rejection upstream.
            raise

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
def compute_dag_steering_context(
    project_dir: "str | Path",
    rubric_data: dict,
    workspace_dir: "str | Path",
) -> str:
    """GP-134 / Gemini-Pro DAG-steering primitive.

    If rubric declares `enable_dag_steering: true`, parse the project's
    latest_probability_dag.json, compute per-node urgency = edge_weight
    × node_probability, and return a prompt fragment naming the
    highest-urgency node's watch_signal. Hysteresis: if the same node
    has been #1 for 3+ iters, bump to #2. If 5+ iters stuck, emit a
    damage signal of kind `dag_stagnation`.

    Returns empty string when steering is disabled, DAG is missing/
    malformed, or no actionable node exists. Per-iter steering
    decisions logged to workspace/dag_steering_log.jsonl for audit.
    """
    if not rubric_data.get("enable_dag_steering"):
        return ""

    project_dir = Path(project_dir)
    workspace_dir = Path(workspace_dir)
    dag_path = project_dir / "latest_probability_dag.json"
    if not dag_path.exists():
        return ""

    try:
        dag = json.loads(dag_path.read_text(encoding="utf-8"))
    except Exception as exc:                                     # noqa: BLE001
        print(f"[dag-steering] malformed DAG, skipping: {exc}")
        return ""

    nodes = dag.get("nodes") or []
    edges = dag.get("edges") or []
    if not nodes or not edges:
        return ""

    # Node probabilities + edges keyed by from-node
    node_by_id = {n.get("id"): n for n in nodes if n.get("id")}
    outgoing = {}
    for e in edges:
        src = e.get("from")
        if src not in outgoing or (e.get("weight", 0) or 0) > outgoing[src].get("weight", 0):
            outgoing[src] = e

    scored = []
    for nid, n in node_by_id.items():
        p = float(n.get("probability", 0.0) or 0.0)
        edge = outgoing.get(nid)
        if edge is None:
            continue
        w = float(edge.get("weight", 0.0) or 0.0)
        urgency = w * p
        scored.append((urgency, nid, n))
    if not scored:
        return ""

    # Sort by urgency desc, then by node_id for deterministic ties
    scored.sort(key=lambda t: (-t[0], t[1]))

    # Hysteresis: read the last 3 steering-log entries. If same top node,
    # bump to #2. If 5+ consecutive at top, emit damage signal.
    log_path = workspace_dir / "dag_steering_log.jsonl"
    recent_top: list[str] = []
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            for line in lines[-5:]:
                try:
                    rec = json.loads(line)
                    recent_top.append(rec.get("selected_node_id", ""))
                except Exception:                                # noqa: BLE001
                    continue
        except Exception:                                        # noqa: BLE001
            pass

    pick = scored[0]
    if len(scored) >= 2 and len(recent_top) >= 3 and all(t == scored[0][1] for t in recent_top[-3:]):
        pick = scored[1]
        hysteresis_bumped = True
    else:
        hysteresis_bumped = False

    if len(recent_top) >= 5 and all(t == scored[0][1] for t in recent_top[-5:]):
        try:
            from src.ztare.signals import damage as _damage
            _damage.emit(
                source=f"dag_steering:{Path(project_dir).name}",
                kind="dag_stagnation",
                detail=(
                    f"DAG node {scored[0][1]!r} has been top-urgency for 5+ iters; "
                    f"mutator may be unable to resolve within current grammar. "
                    f"Consider rubric/charter revision or scope change."
                ),
                severity="warn",
            )
        except Exception as exc:                                 # noqa: BLE001
            print(f"[dag-steering] damage-signal emit failed: {exc}")

    urgency, nid, node = pick
    watch = node.get("watch_signal", "").strip()
    label = node.get("label", "").strip()

    steering_block = (
        "\n\n--- GP-134 / DAG STEERING (priority focus) ---\n"
        f"The Bayesian DAG currently identifies node {nid!r} as highest-urgency "
        f"(urgency={urgency:.3f}, probability={node.get('probability')}, "
        f"edge_weight={outgoing[nid].get('weight')}"
        f"{'; hysteresis-bumped from #1 to #2 due to 3 consecutive iters at same top' if hysteresis_bumped else ''}).\n"
        f"Node label: {label}\n"
        f"Watch signal: {watch}\n"
        "Weight ~50% of your mutation effort on resolving this specific watch signal. "
        "You may pursue other improvements in parallel, but the next iteration's thesis "
        "should produce specific progress on the named node. "
        "Do NOT treat this as an exclusive override — continue addressing other gaps.\n"
        "--- END DAG STEERING ---\n"
    )

    # Log the decision
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "selected_node_id": nid,
            "selected_urgency": urgency,
            "selected_probability": node.get("probability"),
            "selected_edge_weight": outgoing[nid].get("weight"),
            "hysteresis_bumped": hysteresis_bumped,
            "all_scored": [(u, i) for (u, i, _) in scored],
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as exc:                                     # noqa: BLE001
        print(f"[dag-steering] log write failed: {exc}")

    return steering_block


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
    fit_primitive_features_enabled=False,
    fit_primitive_features_k_max=8,
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

    # GP-134 DAG steering: if rubric has enable_dag_steering=true, compute
    # the highest-urgency node in latest_probability_dag.json and inject
    # its watch_signal into the mutator prompt. Opt-in, no-op otherwise.
    try:
        _dag_steering_context = compute_dag_steering_context(
            project_dir=PROJECT_DIR,
            rubric_data=rubric_data,
            workspace_dir=Path(PROJECT_DIR) / "workspace",
        )
    except Exception as _exc:                                    # noqa: BLE001
        print(f"[dag-steering] compute failed, skipping: {_exc}")
        _dag_steering_context = ""
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
    _rubric_stag = rubric_data.get("composition_stagnation_threshold")
    pivot_state = resolve_stagnation_pivot_state(
        is_v4_project=is_v4_project,
        falsification_mode=falsification_mode,
        stagnation_count=stagnation_count,
        rubric_mode=rubric_data.get("rubric_mode"),
        rubric_stagnation_override=int(_rubric_stag) if _rubric_stag is not None else None,
    )
    pivot_profile = pivot_state.profile
    style_guide = ""
    output_requirements = ""
    grounding_heading = "GROUNDING DATA (IMMUTABLE CONSTANTS):"
    grounding_payload = evidence

    # GP-149 I-1: optional anti-pattern catalog injection.
    # Rubric flag `inject_antipattern_catalog` accepts:
    #   false / not-set  -> no injection (default)
    #   "hardkill"       -> inject ONLY Part 1 (cross-judge-validated structural blockers)
    #   "ceilingbreaker" -> inject ONLY Part 2 (judge-specific; only if judge family
    #                        matches where the ceiling-breaker lifts were mined)
    #   "both" or true   -> inject both parts (legacy behavior)
    # Split added 2026-04-24 per GP-149 §8a stratified mining: structural blockers
    # have lift 0.00 under ALL judge families (safe universal default); ceiling-breakers
    # show direction flips (missing_mechanism 0.84 gpt-4.1 vs 2.43 o3) — NOT universal.
    try:
        _catalog_mode_raw = rubric_data.get("inject_antipattern_catalog", False)
    except Exception:
        _catalog_mode_raw = False
    # Normalize to "off" / "hardkill" / "ceilingbreaker" / "both"
    if _catalog_mode_raw is True:
        _catalog_mode = "both"
    elif _catalog_mode_raw is False or _catalog_mode_raw is None:
        _catalog_mode = "off"
    elif isinstance(_catalog_mode_raw, str):
        _c_lower = _catalog_mode_raw.lower().strip()
        _catalog_mode = _c_lower if _c_lower in ("hardkill", "ceilingbreaker", "both", "off") else "off"
    else:
        _catalog_mode = "off"

    # GP-151 / Task 22: when structural_blocker_enforcement='gate', the
    # deterministic post-champion gates (G-CIRC + G-FALSIFY) replace the
    # prompt-injection layer entirely for Part 1 (structural blockers).
    # Suppress the hardkill injection in that case to avoid double-defense
    # and to keep the mutator prompt clean. Part 2 (ceiling-breakers) is
    # not affected — those remain in the catalog injection path under their
    # own opt-in mode.
    _sbe_for_catalog = str(rubric_data.get("structural_blocker_enforcement") or "prompt").lower().strip()
    if _sbe_for_catalog == "gate" and _catalog_mode == "hardkill":
        print(
            "  📋 GP-151 hardkill retirement: structural_blocker_enforcement='gate' "
            "active — deterministic G-CIRC + G-FALSIFY post-champion gates replace "
            "the Part 1 catalog injection. Skipping hardkill injection."
        )
        _catalog_mode = "off"

    if _catalog_mode in ("ceilingbreaker", "both"):
        print(
            f"  ⚠️  GP-149 cross-LLM WARNING: inject_antipattern_catalog='{_catalog_mode}' "
            f"injects PART 2 (ceiling-breakers). Per 2026-04-24 cross-provider "
            f"classifier audit (gpt-4.1-mini / claude-haiku / gemini-flash-lite, 100 records), "
            f"three-way agreement is 48% (κ≈0.57) — BELOW the 0.60 cross-LLM validation "
            f"threshold. PART 2 class labels are LLM-aesthetic-specific, not structural. "
            f"Consider 'hardkill' mode for cross-LLM-validated injection. Proceeding."
        )
    if _catalog_mode != "off":
        try:
            _catalog_path = DOCS_DIR / "concepts" / "anti_pattern_catalog.md"
            if _catalog_path.is_file():
                _catalog_text = _catalog_path.read_text(encoding="utf-8", errors="ignore")
                # Slice by PART markers. File structure: free-text preamble, then
                # "## PART 1 — Structural Blockers", then "## PART 2 — Ceiling-Breakers",
                # then "## PART 3 — Usage". Extract by headings.
                _p1_start = _catalog_text.find("## PART 1")
                _p2_start = _catalog_text.find("## PART 2")
                _p3_start = _catalog_text.find("## PART 3")
                _p1 = _catalog_text[_p1_start:_p2_start] if _p1_start >= 0 and _p2_start >= 0 else ""
                _p2 = _catalog_text[_p2_start:_p3_start] if _p2_start >= 0 and _p3_start >= 0 else ""
                if _catalog_mode == "hardkill":
                    _injected = _p1
                    _header = ("MINING-DERIVED STRUCTURAL BLOCKERS — cross-judge validated.\n"
                               "The three classes below appear with lift ≈ 0.00 across every\n"
                               "tested judge family. If you write these, your thesis scores near\n"
                               "zero regardless of other strengths. AVOID absolutely.\n\n")
                elif _catalog_mode == "ceilingbreaker":
                    _injected = _p2
                    _header = ("MINING-DERIVED CEILING-BREAKERS — judge-specific; at high scores\n"
                               "the judge WILL flag these. ENGAGE them head-on, don't hide.\n\n")
                else:  # "both"
                    _injected = _p1 + "\n\n" + _p2
                    _header = ("MINING-DERIVED FAILURE-CLASS CATALOG (GP-149 I-1, both parts):\n"
                               "PART 1 = structural blockers (AVOID; cross-judge validated).\n"
                               "PART 2 = ceiling-breakers (ENGAGE; judge-specific — trust for this\n"
                               "project's declared judge family).\n\n")
                if _injected:
                    grounding_payload = (
                        grounding_payload + "\n\n---\n\n" + _header + _injected
                    )
                    print(f"  📋 GP-149 I-1: anti-pattern catalog injected in mode='{_catalog_mode}' "
                          f"({len(_injected)} chars)")
        except Exception as _cat_err:
            print(f"  ⚠️  GP-149 I-1: anti-pattern catalog injection failed: {_cat_err}")

    # --- DYNAMIC CONTEXT MANAGEMENT ---
    if is_v4_project:
        document_context = f"### CURRENT SYSTEM STATE (FOR ANALYSIS ONLY)\n{current_content}"
        if pivot_state.event_type == "v4_bounded_mutation_override":
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
    elif pivot_state.loop_control_action == "emergency_pivot":
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
    elif pivot_state.loop_control_action == "stagnation_pivot":
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
          EXCEPTION 1: if the rubric declares `runner_allowed_imports`, those specific packages
          are available in the runner env and MAY be imported (e.g., for number-theoretic
          substrates `sympy` is commonly declared so the discriminator suite can use
          `sympy.isprime`, `sympy.factorint`, `sympy.primefactors`, `sympy.divisors`).
          EXCEPTION 2 (GP-166, 2026-04-25 night): if the project directory contains
          `features.py` (the canonical N-D substrate adapter), `from features import …`
          is allowed. Use it to access real visible / holdout / farther-tail rows in your
          falsification suite — e.g.,
              `from features import visible_rows`
              `for row_id, y, feat in visible_rows()[:5]: ...`
          This eliminates the need to inline data via dict/list literals and avoids the
          R1 ↔ "module-level I_model call" double bind. Do NOT import any other
          project-local module — only `features.py` is auto-allowed.
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

    # GP-123: DAG steering context — read the probability DAG and inject
    # the weakest nodes so the mutator knows WHERE to improve
    dag_steering_context = ""
    try:
        _dag_path = Path(PROJECT_DIR) / "latest_probability_dag.json"
        if _dag_path.exists():
            _dag = json.loads(_dag_path.read_text())
            _dag_nodes = _dag.get("nodes", [])
            if _dag_nodes:
                _dag_nodes_sorted = sorted(_dag_nodes, key=lambda n: n.get("probability", 1.0))
                _dag_outcome = _dag.get("outcome", {})
                _lines = [
                    "### PROBABILITY DAG — YOUR THESIS'S VULNERABLE ASSUMPTIONS",
                    f"Overall outcome probability: {_dag_outcome.get('probability', '?')}",
                    "Nodes ranked by vulnerability (WEAKEST FIRST):",
                ]
                for _dn in _dag_nodes_sorted[:3]:  # top 3 weakest
                    _lines.append(
                        f"  - {_dn.get('id', '?')}: \"{_dn.get('label', '?')}\" "
                        f"(p={_dn.get('probability', '?')}) "
                        f"— watch: {_dn.get('watch_signal', 'none')}"
                    )
                _lines.append("Your next thesis MUST strengthen the weakest node above.")
                dag_steering_context = "\n".join(_lines)
    except Exception:
        pass

    # GP-035: fit primitive prompt contract (opt-in via rubric)
    fit_primitive_context = ""
    fit_primitive_features_context = ""
    fit_declaration_reminder = ""
    structural_memory_prompt = ""
    residual_mode_prompt = ""

    if fit_primitive_features_enabled:
        # 2026-04-26 (Mutator Briefing refactor): the legacy inline
        # _prior_fit_diag_block + _near_miss_block computations have
        # been migrated to BriefingProvider classes under
        # src/ztare/orchestrator/briefing_providers/. The MutatorBriefing
        # registry produces the same output PLUS three new providers
        # (iter_trajectory, row_outliers, asymptote_deviation). Adding
        # a future provider is a 1-line registration in
        # `default_briefing()`, no edit to this prompt-assembly code.
        # The legacy inline blocks below are KEPT as a defensive
        # fallback in case the briefing module fails to import; they
        # produce a strict subset of the briefing's content.
        _briefing_block = ""
        try:
            from src.ztare.orchestrator.mutator_briefing import (
                BriefingContext,
                default_briefing,
            )
            _briefing_ctx = BriefingContext(
                project_dir=Path(PROJECT_DIR),
                iter_index=i + 1,
                rubric=rubric_data,
                workspace_dir=Path(PROJECT_DIR) / "workspace",
                mutator_model_id=MUTATOR_MODEL_ID,
            )
            _briefing_obj = default_briefing()
            _briefing_block = _briefing_obj.render(_briefing_ctx)
            _active = [p.name for p in sorted(_briefing_obj.providers, key=lambda p: (p.priority, p.name)) if p.applies(_briefing_ctx)]
            print(f"📋 MutatorBriefing: {len(_active)} providers active ({', '.join(_active) if _active else 'none'}) | {len(_briefing_block)} chars injected")
        except Exception as _briefing_exc:
            print(f"⚠️ MutatorBriefing render failed: {_briefing_exc} (using legacy inline fallback)")
            _briefing_block = ""

        # Legacy inline path (defensive fallback only — only fires if
        # _briefing_block is empty). Kept for backward compatibility
        # during the briefing-refactor transition.
        _prior_fit_diag_block = ""
        try:
            _prior_fit_path = Path(PROJECT_DIR) / "workspace" / "fit_features_result.json"
            if _prior_fit_path.exists():
                _prior = json.loads(_prior_fit_path.read_text())
                if _prior.get("success"):
                    # 2026-04-26 audit fix: surface ALL fit-side telemetry
                    # the mutator was previously blind to. Pathology, convergence
                    # classification, fitted params, sparse categories, BIC.
                    # Each block printed only when present + non-trivial.
                    _ext_lines = []
                    _conv = _prior.get("classification", "")
                    if _conv:
                        _ext_lines.append(f"    convergence_classification: {_conv}")
                    _fp = _prior.get("fitted_params") or {}
                    if _fp:
                        _fp_summary = ", ".join(
                            f"{k}={v:.5g}" if isinstance(v, (int, float)) else f"{k}={v}"
                            for k, v in _fp.items()
                        )
                        _ext_lines.append(f"    fitted_params: {{{_fp_summary}}}")
                    _bic = _prior.get("bic")
                    _k = _prior.get("k_params")
                    _n_fit = _prior.get("n_fit_rows")
                    if _bic is not None and isinstance(_bic, (int, float)) and _bic == _bic:  # not NaN
                        _ext_lines.append(f"    BIC: {_bic:.2f} (K={_k}, N={_n_fit}) — lower = better-justified K")
                    if _prior.get("pathological") and _prior.get("pathology_reason"):
                        _ext_lines.append(
                            "\n    ⚠️ PATHOLOGICAL FIT FLAG (apparatus diagnostic):\n    "
                            + _prior["pathology_reason"].replace("\n", "\n    ")
                        )
                    _fvc = _prior.get("feature_value_counts") or {}
                    _sparse = []
                    for fk, vc in _fvc.items():
                        for v, c in (vc or {}).items():
                            if c < 3:
                                _sparse.append(f"{fk}='{v}' (n={c})")
                    if _sparse:
                        _ext_lines.append(
                            "    ⚠️ SPARSE CATEGORIES (<3 rows): "
                            + ", ".join(_sparse[:6])
                            + (" …" if len(_sparse) > 6 else "")
                        )
                    _residual_block = ""
                    if _prior.get("residual_diagnostic"):
                        _residual_block = (
                            "\n    Per-categorical-group residual diagnostic (groups whose "
                            "mean residual exceeds 1.5× the overall mean):\n\n    "
                            + _prior["residual_diagnostic"].replace("\n", "\n    ")
                        )
                    if _ext_lines or _residual_block:
                        _prior_fit_diag_block = (
                            "\n    ### PRIOR FIT TELEMETRY (from last iter — read before refining)\n\n"
                            + "\n".join(_ext_lines)
                            + ("\n" if _ext_lines else "")
                            + _residual_block
                            + "\n"
                        )
                elif not _prior.get("success") and _prior.get("error_message"):
                    # Bug #32 (2026-04-25 evening): full enriched Bug #29
                    # diagnostic must reach the mutator. Was truncated to
                    # 300 chars — cut off mid-sentence, mutator never saw
                    # the 6 specific anti-pattern hints. Bumped to 1500.
                    _err_full = _prior['error_message']
                    _err_text = _err_full if len(_err_full) <= 1500 else _err_full[:1500] + "...[truncated]"
                    _prior_fit_diag_block = (
                        "\n    ### PRIOR FIT FAILURE (from last iter) — READ THIS BEFORE WRITING\n\n"
                        f"    Your previous iter's fit FAILED. The apparatus diagnostic was:\n\n"
                        f"    {_err_text.replace(chr(10), chr(10) + '    ')}\n\n"
                        "    Fix the form grammar (PARAMETRIC_FORM must be a single Python "
                        "expression with `features[...]` and `params[...]` subscripts). "
                        "If the diagnostic above mentions specific anti-patterns (Greek "
                        "letters, statement blocks, bare identifiers, pseudocode 'when'/"
                        "'where'), translate every one of them to valid Python BEFORE "
                        "submitting. Do not regress to pseudocode.\n"
                    )
        except Exception:
            pass  # missing/corrupt prior fit JSON is non-fatal

        # 2026-04-26: NEAR-MISS DIAGNOSTIC (substrate-agnostic gradient
        # feedback). When prior-iter gates ran but score=0 due to
        # threshold breach, surface the ACTUAL numerical gap per gate
        # so the mutator has a precise gradient — not just "you failed."
        # Identifies the dominant gap (which gate is most over-threshold)
        # and a generic structural-vs-extrapolation hint based on which
        # gate dominates. Substrate-agnostic — no hypothesis-specific
        # advice (no "pivot to Hypothesis S" prose); the mutator infers
        # the structural move from the numbers.
        _near_miss_block = ""
        try:
            _prior_eval_path = Path(PROJECT_DIR) / "latest_eval_results.json"
            if _prior_eval_path.exists():
                _prior_eval = json.loads(_prior_eval_path.read_text())
                _gates = []
                _payload = _prior_eval.get("holdout_payload") or {}
                # GP-156 harness shape
                for _gname in ("holdout", "farther_tail"):
                    _g = _payload.get(_gname) if isinstance(_payload, dict) else None
                    if isinstance(_g, dict) and _g.get("mean_relative_error") is not None and _g.get("threshold") is not None:
                        _mre = float(_g["mean_relative_error"])
                        _thr = float(_g["threshold"])
                        _gap_pct = (_mre - _thr) / max(_thr, 1e-12) * 100.0
                        _passed = bool(_g.get("passed"))
                        _gates.append({
                            "name": _gname.upper(),
                            "mre": _mre,
                            "threshold": _thr,
                            "gap_pct": _gap_pct,
                            "passed": _passed,
                        })
                # Legacy: list of gate dicts in evaluation
                if not _gates:
                    for _g in (_prior_eval.get("gate_results") or []):
                        if isinstance(_g, dict) and _g.get("value") is not None and _g.get("threshold") is not None:
                            _mre = float(_g["value"])
                            _thr = float(_g["threshold"])
                            _gap_pct = (_mre - _thr) / max(_thr, 1e-12) * 100.0
                            _gates.append({
                                "name": _g.get("name", "?"),
                                "mre": _mre,
                                "threshold": _thr,
                                "gap_pct": _gap_pct,
                                "passed": bool(_g.get("passed", _g.get("pass", False))),
                            })
                if _gates:
                    # Sort by gap_pct descending (largest failure first)
                    _gates_sorted = sorted(_gates, key=lambda g: g["gap_pct"], reverse=True)
                    _failed = [g for g in _gates_sorted if not g["passed"]]
                    _near_miss = [g for g in _failed if 0 < g["gap_pct"] <= 25]
                    _hard = [g for g in _failed if g["gap_pct"] > 25]
                    if _failed:
                        _lines = ["\n    ### NEAR-MISS GATE DIAGNOSTIC (numerical-gap feedback, prior iter)\n"]
                        _lines.append("    Prior iter's gates produced these per-gate gaps. Use the")
                        _lines.append("    DOMINANT GAP (largest over-threshold) to choose your next")
                        _lines.append("    structural move. Score=0 reflects hard-gate semantics; the")
                        _lines.append("    numerical gradient below shows how close each gate was.\n")
                        for g in _gates_sorted:
                            _tag = ("PASS" if g["passed"]
                                    else ("near-miss" if 0 < g["gap_pct"] <= 25
                                          else "hard-fail"))
                            _lines.append(
                                f"    - {g['name']}: MRE={g['mre']:.4g} vs threshold "
                                f"{g['threshold']:.4g}  (gap {g['gap_pct']:+.1f}%, {_tag})"
                            )
                        if _failed:
                            _dominant = _failed[0]
                            _lines.append(
                                f"\n    DOMINANT GAP: {_dominant['name']} "
                                f"(gap {_dominant['gap_pct']:+.1f}%)."
                            )
                            # Substrate-agnostic structural hint:
                            # if HOLDOUT (in-regime) is the dominant gap → form structurally wrong
                            # if FARTHER_TAIL/FARTHER (extrapolation) → form locally OK, fails extrapolation
                            _dom_name = _dominant["name"].upper()
                            if "HOLDOUT" in _dom_name and "FARTHER" not in _dom_name:
                                _lines.append(
                                    "    The form is failing IN-REGIME (held-out class-A or "
                                    "primary holdout). The structural family or fitted constants "
                                    "are wrong. Reconsider the form's functional class before "
                                    "tuning further; another iteration of the same form will "
                                    "likely converge to the same local minimum."
                                )
                            elif "FARTHER" in _dom_name or "TAIL" in _dom_name:
                                _lines.append(
                                    "    The form fits IN-REGIME but FAILS EXTRAPOLATION. "
                                    "The form's structural capacity does not extend to the "
                                    "held-out tail/class. Consider whether the form needs "
                                    "additional features, class-conditional structure, or a "
                                    "different functional family that respects the asymptotic "
                                    "behavior the charter declares."
                                )
                            else:
                                _lines.append(
                                    f"    Largest deficit at {_dom_name}. Use the gap "
                                    f"sign and magnitude to direct your next structural change."
                                )
                        _near_miss_block = "\n".join(_lines) + "\n"
        except Exception:
            pass  # missing/corrupt prior eval JSON is non-fatal

        # MutatorBriefing block (preferred) replaces _near_miss_block +
        # _prior_fit_diag_block when available; fallback to legacy
        # inline blocks if briefing failed.
        _telemetry_block = _briefing_block if _briefing_block else (_near_miss_block + _prior_fit_diag_block)
        fit_primitive_features_context = f"""{_telemetry_block}
    ### GP-156 FEATURE-VECTOR FIT PRIMITIVE CONTRACT (Proposal 3)

    This substrate exposes a FEATURE DICT to your I_model — `features['key']`
    subscripts, NOT 1D paired (x, y) data. The standard FIT_DECLARATION
    block (1D fit_primitive) does NOT engage on this substrate. Instead,
    you MUST declare a parametric form via three module-level names in
    test_model.py and the apparatus runs scipy.optimize.minimize multi-
    start to fit the constants automatically. This bypasses the LLM's
    known weakness at numerical optimization.

    **REQUIRED — declare these at module level in test_model.py:**

        # CRITICAL: include this import if you reference `features` outside
        # I_model's body (e.g. to inspect feature keys at module load).
        # The substrate's features.py is on sys.path and exports FEATURES,
        # feature_keys(), get_features(id), visible_rows(), etc.
        from features import FEATURES, feature_keys

        PARAMETRIC_FORM = "<your closed-form expression as a Python string>"
        PARAMETER_NAMES = ["a", "b", ...]    # the free parameters
        MODEL_PARAMS = {{}}                   # apparatus fills with fitted values

        def I_model(features, params=MODEL_PARAMS):
            # NOTE: `features` here is a FUNCTION ARGUMENT (one row's dict),
            # NOT the imported module. Inside the function body you can use
            # `features['key']` to access the row's feature value.
            # Example for a 2-param form:
            #   return params["a"] * features["some_key"] + params["b"]
            ...

    **DO NOT reference `features` at module level without importing it first.**
    A common error: writing `PARAMETER_NAMES = list(features.FEATURES.keys())`
    or similar BEFORE the `from features import ...` line. R1 will reject
    with NameError. Either import first OR write your declarations as
    plain string/list literals.

    **COMMON R1 REJECTION PATTERNS — DO NOT EMIT THESE:**

    1. Bare identifier references at module level:
        ❌ WRONG:  PARAMETRIC_FORM = "a if regime_hint == 'X' else b"
                   (this is fine — it's a string. But this is wrong:)
        ❌ WRONG:  if regime_hint == 'X': ...   # bare regime_hint at module level
        ✅ RIGHT:  Inside PARAMETRIC_FORM string, use features['regime_hint'].
                   Outside, only reference features['regime_hint'] inside I_model body.

    2. Calling I_model at module level (e.g. for test asserts):
        ❌ WRONG:  test_val = I_model({{}})            # empty dict → KeyError
        ❌ WRONG:  assert I_model({{'x': 1}}) > 0       # KeyError on missing keys
        ✅ RIGHT:  Don't call I_model at module level. The harness calls it
                   AFTER your apparatus-fitted MODEL_PARAMS substitution. Module-
                   level calls run with MODEL_PARAMS={{}} (empty) and crash.

    3. Indexing `features` (the dict) with keys it doesn't have:
        ❌ WRONG:  PARAMETRIC_FORM = "params['m'] * features['x']"  # 'm' not in PARAMETER_NAMES
        ✅ RIGHT:  Every `params[X]` key must be in PARAMETER_NAMES list.
                   Every `features[X]` key must exist in features.py for ALL rows.
                   Run `python -c "from features import FEATURES; print(list(FEATURES.values())[0].keys())"`
                   in the substrate dir to see valid feature keys.

    4. Importing `features` (or any non-stdlib module) inside the
       FALSIFICATION SUITE (the `if __name__ == "__main__":` block):
        ❌ WRONG:  if __name__ == "__main__":
                       from features import visible_rows  # rejected by R1
                       for rid, y, fd in visible_rows()[:5]:
                           assert math.isfinite(I_model(fd))
        ✅ RIGHT:  if __name__ == "__main__":
                       # Stdlib-only. Construct a minimal feature dict by hand,
                       # using legal feature keys you already cited inside
                       # PARAMETRIC_FORM. Apparatus runs the harness against
                       # real data separately — your suite proves the form
                       # is internally consistent on hand-built inputs.
                       fake = {{"x": 1.0, "system_class": "A"}}
                       assert math.isfinite(I_model(fake))
                       assert I_model({{"x": 1e-12, "system_class": "A"}}) > 0
       The R1 rejection for this pattern is "Bounded-discriminator suite
       imports non-standard dependencies (features). Use standard-library-
       only Python and plain `assert` statements." If you see this on iter 1,
       you triggered Bug C from the gp163d postmortem — fix on first
       attempt; do not burn 3 strikes correcting it iteratively.

    5. Init-range trap on dimensional constants (Bug A from gp163d postmortem):
        When you declare a parameter expected to take a value at a physical
        scale far from order(1) — e.g. an acceleration constant near
        1e-10, a coupling constant near 1e-15, an exchange rate near 1e6 —
        you MUST declare INIT_RANGE so scipy's gradient descent can reach it:
        ❌ WRONG (gp163d, 11 zero-score iters):
                   PARAMETER_NAMES = ['c']
                   # default INIT_RANGE = (-2, 2); scipy converges near 0
                   # because it cannot traverse 10 orders of magnitude
        ✅ RIGHT:  PARAMETER_NAMES = ['c']
                   INIT_RANGE = {{"c": (1e-12, 1e-8)}}   # span the physical scale
        For a parameter expected at scale `S`, use bounds spanning ~3
        decades around S — write OUT the literals, not arithmetic. The
        INIT_RANGE parser accepts only `ast.Constant` and `UnaryOp(USub)`
        (i.e. plain numeric literals, optionally negative). It does NOT
        accept arithmetic expressions like `1e-10*1e-3` — those silently
        get rejected and you fall back to the default (-2, 2). The fit
        primitive will emit a SUB-PHYSICAL-SCALE warning if your fitted
        value is far below the data's |y| — read that warning, do not
        ignore it.

    **AST whitelist for PARAMETRIC_FORM** (anything else is rejected):
    - Arithmetic: + - * / ** % //
    - Functions: sigmoid, exp, log, log10, sin, cos, tan, tanh, sqrt, abs,
      max, min, where, erf, float, int, bool, len, str
    - Conditionals: `a if cond else b`, comparisons (==, !=, <, >, in, not in,
      is, is not), boolean and/or, tuple/list literals (for `in (...)`).
    - Subscript ONLY on `features` (e.g. `features['intrinsic_dim_d']`).

    **NOT in the whitelist (common mistakes — DO NOT emit these):**
    - `pow(x, y)` — use `x**y` instead. The `pow` builtin is rejected.
    - `np.exp` / `numpy.exp` — use bare `exp(x)`. NumPy attribute access is rejected.
    - `math.pi`, `math.e` — write the literal value (3.141592653589793).
    - User-defined helper functions — inline the expression in the form.

    **CONTINUOUS-TRANSITION PRIMITIVES (use these instead of nested ternaries
    when expressing regime crossovers — single expression, no AST drama):**
    - `where(cond, a, b)` — function-call ternary; `np.where` for scalars.
      Chain: `where(c1, A, where(c2, B, C))`. No nested `if/else` parsing.
    - `sigmoid(x, center, width)` — smooth crossover at `x=center`, sharpness
      `1/width`. Three-arg form. Use for continuous regime transitions:
      `sigmoid(features['log10_N_params'], params['c'], params['w'])`.
    - `erf(z)` — error function, for Gaussian-CDF crossovers.

    **CRITICAL — `where(...)` IS EAGER, TERNARY IS LAZY (Bug #39 lesson):**

    Python evaluates ALL function-call arguments before calling the
    function. So `where(cond, A, B)` evaluates BOTH `A` and `B` first,
    THEN the function returns one. This means `where()` is UNSAFE for
    guard-patterns where one branch references a value that may be
    None / undefined / division-by-zero on the other branch.

    The Python ternary `A if cond else B` short-circuits — only the
    selected branch is evaluated. It is SAFE for guard-patterns.

    Use `where()` ONLY when BOTH branches always produce valid output:

        ✅ SAFE for where():
            "where(features['regime']=='A', 1.0, params['fallback'])"
            (both 1.0 and params['fallback'] always evaluate fine)

        ✅ SAFE for where() — sigmoid both branches always defined:
            "where(features['x'] > 0,"
            "      params['a'] * sigmoid(features['x'], 5.0, 1.0),"
            "      params['b'])"

        ❌ UNSAFE for where() — guard pattern:
            "where(features['d'] is not None, 2.0/features['d'], 0.0)"
              ↑ when features['d'] is None, `2.0/None` raises TypeError
              BEFORE where() picks a branch. Result: ~80% of rows crash.

        ✅ Use ternary instead for guard patterns (short-circuits):
            "(2.0/features['d'] if features['d'] is not None else 0.0)"
              ↑ when features['d'] is None, division never executes.

    Mixing is fine — use ternary for the None-guard layer, where() for
    the smooth/categorical branches inside it. Both produce a single
    Python expression evaluable by eval().

    **PERFECT-FORM EXAMPLE (no domain meaning — grammar template):**

        PARAMETRIC_FORM = (
            "where(features['regime_hint'] == 'variance_limited', 1.0, "
            "  params['a'] + params['b'] * sigmoid("
            "    features['log10_N_params'], params['c'], params['w']"
            "  )"
            ")"
        )

    Notice: ZERO if/elif statements, ZERO `=` assignments, ZERO `return`
    keywords, ZERO bare identifiers (every variable is `features['key']` or
    `params['name']`). It is ONE Python expression evaluable by `eval()`.

    **COMMON PSEUDO-CODE → PYTHON TRANSLATIONS (apply BEFORE submitting):**

        ❌ WRONG (English prose):
            "If regime_hint == 'X', return 1.0. Else if d is given, return 2/d."
        ❌ WRONG (statement block):
            "if regime_hint == 'X': y = 1.0\nelif d is not None: y = 2/d\nelse: y = bias"
        ❌ WRONG (f-string macro expansion):
            "alpha = a_mod_{{modality}} + b_arch_{{architecture}}"
        ❌ WRONG (assignment + return):
            "alpha = bias + offset; return alpha"
        ✅ RIGHT (single expression, function-call branching):
            "where(features['regime']=='X', 1.0, "
            "  where(features['d'] is not None, 2.0/features['d'], params['bias']))"
        ✅ RIGHT (chained ternary equivalent):
            "1.0 if features['regime']=='X' else "
            "(2.0/features['d'] if features['d'] is not None else params['bias'])"

    **K_law budget: {fit_primitive_features_k_max} parameters MAX.** Forms with more are
    rejected. Use categorical-conditional + arithmetic to stay within budget.

    **CRITICAL TIMING — DO NOT crash on import:**
    At module-import time, MODEL_PARAMS is the empty dict {{}}. The scipy
    fit runs AFTER import. Therefore:

        - DO NOT put module-level assertions that call I_model (e.g.
          `assert abs(I_model({{...}}) - 1.0) < 0.01`). They fire at
          import-time when MODEL_PARAMS is empty and crash R1.
        - DO NOT hide such asserts in a `_post_fit_sanity()` or similar
          private helper — the apparatus does not invoke that helper, so
          the asserts never run AND I_model goes unverified, scoring zero.
        - Sanity asserts on FORM (callable, parameter count) are fine:
          `assert callable(I_model)` is OK at module scope.
        - Debug prints/asserts that need a real I_model call go inside
          `if __name__ == "__main__":` (apparatus does NOT run that block).

    **DO NOT use FIT_DECLARATION block on this substrate** — the 1D
    fit_primitive does NOT engage on feature-dict substrates. Use only
    PARAMETRIC_FORM + PARAMETER_NAMES + MODEL_PARAMS as documented above.

    **Hand-coding constants reliably MISSES the holdout gate.** Mining
    of prior runs showed mutators who tried to manually fit constants
    landed at MRE ≈ 0.20 vs gate 0.10. Declaring the form and letting
    scipy fit drives MRE to ≈ 0.02. This is not optional — opt in.

    ### G-FALSIFY × R1 — HOW TO SATISFY BOTH (GP-156 Bug #17)

    G-FALSIFY requires `test_model.py` to contain ≥1 numeric-threshold
    assertion. R1 forbids module-level `I_model(...)` calls. The
    intersection is non-empty: numeric asserts that DO NOT call I_model
    with params dependence at module-load time. Canonical patterns
    (copy these — they pass G-FALSIFY AND R1):

        # 1) Structural invariants on the parametric form
        assert isinstance(PARAMETRIC_FORM, str) and len(PARAMETRIC_FORM) > 10
        assert isinstance(PARAMETER_NAMES, list) and 1 <= len(PARAMETER_NAMES) <= 8
        # Forbid DUPLICATE param names (order-agnostic — keep your natural
        # ordering, e.g. ['k1', 'k2', 'm_lang', ...] is fine):
        assert len(PARAMETER_NAMES) == len(set(PARAMETER_NAMES)), "duplicate parameters"
        assert all(isinstance(n, str) and n.isidentifier() for n in PARAMETER_NAMES)

        # 2) Feature-key existence checks (apparatus-fits-time invariants)
        from features import FEATURES, feature_keys
        assert all(k in feature_keys() for k in ['intrinsic_dim_d', 'log10_N_params'])
        assert len(FEATURES) >= 50, f"too few rows: {{len(FEATURES)}}"

        # 3) Math-identity asserts on pure helpers (no params dependence)
        import math
        assert abs(1.0 / (1.0 + math.exp(0)) - 0.5) < 1e-9, "sigmoid(0) must equal 0.5"

        # 4) Form contract — every params[X] in PARAMETRIC_FORM is in PARAMETER_NAMES
        # (catches typos before scipy chews on a misnamed parameter)
        import re
        _ref_params = set(re.findall(r"params\\[['\\\"](\\w+)['\\\"]\\]", PARAMETRIC_FORM))
        assert _ref_params <= set(PARAMETER_NAMES), \\
            f"PARAMETRIC_FORM references undeclared params: {{_ref_params - set(PARAMETER_NAMES)}}"

    These satisfy G-FALSIFY (numeric thresholds, would-fail-on-violation)
    AND R1 (no module-level I_model call). DO NOT write asserts that
    depend on `params` values being present — those will KeyError at
    import time before scipy runs.
    """
        # GP-162 R9: convention-homogeneity prompt injection
        # 2026-04-27 fix: read from cage_meta.target_convention_homogeneity first
        # (where the rubric authoring map puts it), fall back to top-level for
        # legacy rubrics. Prior code only read top-level and silently defaulted
        # to homogeneous when cage_meta-only rubrics were used.
        _convention_hom = str(
            (rubric_data.get("cage_meta") or {}).get("target_convention_homogeneity")
            or rubric_data.get("target_convention_homogeneity", "")
            or ""
        ).strip().lower()
        if _convention_hom == "heterogeneous":
            fit_primitive_features_context += """
    ### GP-162 CONVENTION-HOMOGENEITY CONSTRAINT (R9)

    This substrate is HETEROGENEOUS — rows use DIFFERENT fitting conventions
    (e.g. separable single-variable fits vs joint multi-variable fits). The
    same nominal exponent can disagree by 3-4× between conventions.

    Your PARAMETRIC_FORM MUST reference features['fit_convention'] to handle
    this. Example:

        PARAMETRIC_FORM = (
            "params['a'] / features['intrinsic_dim_d']"
            " if features['fit_convention'] == 'kaplan_separable'"
            " else params['b'] / features['intrinsic_dim_d']"
        )

    If your form ignores fit_convention, the Cage R9 gate will REJECT
    engagement and you will score zero on the fit. Do not pool rows
    across conventions without an explicit correction.
    """
        elif _convention_hom == "homogeneous":
            fit_primitive_features_context += """
    ### GP-162 CONVENTION NOTE

    This substrate is HOMOGENEOUS — all rows use the same fitting convention.
    You do NOT need to reference features['fit_convention'] in your form.
    """
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
        if fit_expression_grammar == "py_exec":
            fit_primitive_context += """

    ### PY_EXEC GRAMMAR — ALGORITHMIC PYTHON EXPRESSIONS

    This project requires discovering a structural law for a discrete integer-valued
    function. The expression grammar is EXTENDED: your `fit_declaration` expression
    may use any Python expression syntax, including:

    - List comprehensions: `[x for x in range(...) if ...]`
    - Generator expressions: `sum(... for ...)`
    - Boolean operators: `and`, `or`, `not`
    - Ternary conditionals: `a if condition else b`
    - Builtins: `range`, `sum`, `len`, `int`, `round`, `all`, `any`, `abs`,
      `min`, `max`, `list`, `sorted`, `enumerate`, `zip`, `bool`, `float`,
      `tuple`, `set`, `divmod`, `pow`
    - Additional primitives (availability depends on rubric; see sandbox
      docs): `isprime`, `factorint`, `primefactors`, `divisors`, `gcd`,
      `prime_vector`, `is_coprime`. Names only — no example expressions
      are provided to preserve the blinded-recovery protocol. If a
      primitive is present in the sandbox but the data does not warrant
      its use, do not use it.
    - `math.*` functions (same as default grammar)

    NOT allowed: `import`, `def`, `class`, assignment (`=`), statements.
    The expression must be a single Python expression that evaluates to a number.

    Syntax example only (neutral — chosen because it touches no specific
    number-theoretic topic; demonstrates list-comprehension form):
    ```
    "expression": "len([k for k in range(1, n + 1) if n % k == 0])"
    ```

    The gate harness converts the result to `int` for exact-match comparison.
    Lookup tables (hard-coded dict literals) score 0 on Parsimony.
    Derive the structural form from the data alone. The grammar admits
    many classes of expression; it does not hint which class fits this
    substrate.
    """
        elif fit_expression_grammar == "eml_only":
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

    # GP-157 v5.0 Phase 4d (2026-04-25 night): substrate-class-aware
    # contract hint. Tells the mutator the I_model OVERRIDE contract when
    # the substrate is custom (cage_meta.class in {nd_features, audit,
    # literature, proof_target}) AND no fit primitive is engaged. Empty
    # string in all other cases, so existing prompts are not perturbed.
    # Surfaced by gp159 mutator-empty-Python failure. See
    # src/ztare/orchestrator/prompt.py for the conditional logic + tests.
    from src.ztare.orchestrator import (
        active_contract_label as _active_contract_label,
        select_substrate_contract_hint as _select_substrate_contract_hint,
    )
    substrate_contract_hint = _select_substrate_contract_hint(
        rubric_data,
        project_dir=Path(PROJECT_DIR),
    )
    # Prompt-engineer panel recommendation (2026-04-25 night): LLMs anchor
    # on first + last sections; surface the active contract at BOTH ends.
    # Top-of-prompt one-liner + terminal-third full block.
    _active_contract_top_label = _active_contract_label(
        rubric_data,
        project_dir=Path(PROJECT_DIR),
    )
    if _active_contract_top_label:
        active_contract_top_line = f"\n    🛑 {_active_contract_top_label} 🛑\n"
    else:
        active_contract_top_line = ""

    base_prompt = f"""{persona}

    AXIOMS (PREVIOUSLY VERIFIED TRUTHS):
    {axiom_str}

    CRITICAL CONSTRAINT (THE AXIOMATIC GATE):
    The axioms above have been verified by the Verification Panel and the Meta-Judge.
    You are FORBIDDEN from contradicting them within their original domain.
    HOWEVER, if you are executing a TOPOLOGICAL PIVOT, you are granted 'Axiom Retirement' authority. If an axiom is mathematically true but structurally irrelevant to the new domain (e.g., applying Black Hole limits to a biological brain), you must explicitly drop it by writing: "RETIRED AXIOM: [Axiom Concept] - [Reason it does not apply to this scale/domain]."

    {grounding_heading}
    {grounding_payload}

    {charter_context}
    {constraint_context}
    {document_context}
    {failure_context}
    {primitive_context}
    {_dag_steering_context}

    ---

    ### {task_header}
    {active_contract_top_line}
    "THIS IS THE WEAKEST LINK IN THE CURRENT LOGIC CHAIN: {weakest_point}"

    {dag_steering_context}

    {residual_mode_prompt}
    {fit_primitive_context}
    {fit_primitive_features_context}
    {structural_memory_prompt}
    {gp048_cohort_context}
    {farther_tail_veto_context}
    {component_c_context}
    {divergence_sweep_context}
    {style_guide}
    {substrate_contract_hint}
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

    # GP-158 fix (2026-04-25 evening): rubric-level override for
    # --underidentified_after. Audit substrates (gp156, gp158) need a
    # longer stagnation window because score swings 0↔70+ as the auditor
    # explores defect-finding strategies. CLI default = pivot_after=3
    # which fires too early on 12-iter audit runs (gp158 froze at iter
    # 4/12). Rubric flag `underidentified_after_override` (int) wins
    # if set AND the user did not pass --underidentified_after on the CLI.
    _ria_override = rubric_data.get("underidentified_after_override")
    if isinstance(_ria_override, int) and args.underidentified_after is None:
        args.underidentified_after = _ria_override
        print(
            f"📋 Rubric override: underidentified_after = {_ria_override} "
            f"(was CLI default — adjusted per audit-substrate stagnation window)."
        )

    # GP-157 v5.0 Phase 3b — Cage observe-mode initialization (2026-04-25 night).
    # Activated when rubric declares `cage_observe_mode: true` AND `cage_meta: {...}`.
    # Observe-mode runs Cage.dispatch alongside the existing per-rubric-flag
    # dispatch logic, logs engagement decisions to workspace/cage_engagement.jsonl,
    # and surfaces R8/R9 diagnostic warnings. NEVER replaces existing flow.
    # When all substrates pass observe-mode parity for ≥1 week, Phase 3c will
    # flip cage_observe_mode → cage_authoritative_mode and remove old dispatch.
    # GP-157 v5.0 Phase 4c: Cage runtime resolution moved to
    # src/ztare/orchestrator/state.py with 13 unit tests. Mode resolution +
    # factory failure handling are now testable in isolation.
    from src.ztare.orchestrator import (
        build_cage_runtime as _build_cage_runtime,
        cage_init_banner as _cage_init_banner,
    )
    _v5_runtime = _build_cage_runtime(
        rubric_data,
        cage_factory=_v5_get_default_cage if _V5_CAGE_AVAILABLE else (lambda: None),
        cage_available=_V5_CAGE_AVAILABLE,
    )
    # Backwards-compat aliases for the rest of the loop body (kept until
    # full Phase 4c migration). These read from _v5_runtime; do NOT
    # reassign them downstream.
    _v5_cage_instance = _v5_runtime.instance
    _v5_cage_substrate_view = _v5_runtime.substrate_view
    _v5_observe_mode = _v5_runtime.is_observe
    _v5_authoritative_mode = _v5_runtime.is_authoritative
    _v5_banner = _cage_init_banner(_v5_runtime)
    if _v5_banner is not None:
        print(_v5_banner)
    elif _v5_runtime.mode != "off" and _V5_CAGE_AVAILABLE and _v5_runtime.instance is None:
        # Mode requested but factory failed — log non-fatal and continue.
        print(f"🦴 GP-157 v5.0 Cage {_v5_runtime.mode} init FAILED (non-fatal): factory returned None")

    # --- GP-133 Round 4: py_exec rubric-loader gates ---
    # Any rubric declaring fit_expression_grammar: "py_exec" MUST also
    # declare py_exec_authorized_by (provenance) and expression_byte_budget
    # (anti-lookup-table defense). Autoresearch loop refuses to launch
    # otherwise. See research_areas/private/seams/mission/GP-133...seam.md#round-4.
    _fit_grammar_check = str(rubric_data.get("fit_expression_grammar", "") or "").strip().lower()
    if _fit_grammar_check == "py_exec":
        _authz = rubric_data.get("py_exec_authorized_by")
        if not _authz or not isinstance(_authz, str) or not _authz.strip():
            raise SystemExit(
                "GP-133 R4 GATE FAIL: rubric has fit_expression_grammar='py_exec' but no "
                "'py_exec_authorized_by' field set (must be a seam id or principal signoff "
                "string). See GP-133 Round 4 convergence for rationale. Refusing to launch."
            )
        _byte_budget = rubric_data.get("expression_byte_budget")
        if _byte_budget is None:
            print(
                "⚠️  GP-133 R4 WARNING: rubric uses py_exec grammar but declares no "
                "'expression_byte_budget'. Defaulting to 200 characters (MDL anti-lookup-table "
                "defense). Set expression_byte_budget explicitly in the rubric to silence."
            )
            rubric_data["expression_byte_budget"] = 200
        elif not isinstance(_byte_budget, int) or _byte_budget <= 0:
            raise SystemExit(
                f"GP-133 R4 GATE FAIL: expression_byte_budget must be a positive integer, "
                f"got {_byte_budget!r}. Refusing to launch."
            )
        print(
            f"🛡️  py_exec gates OK: authorized_by={_authz!r}, "
            f"expression_byte_budget={rubric_data.get('expression_byte_budget')}"
        )
        # GP-134 additional gate (2026-04-23): py_exec opens algorithmic
        # expressiveness (number-theoretic primitives, list comprehensions,
        # boolean logic) that goes beyond what math-only grammars can produce.
        # That expressiveness must be paired with explicit rubric_mode so the
        # run cannot inherit a silent default. gp090_01's original run shipped
        # py_exec without rubric_mode and the judge had no Newton-mode gate;
        # refusing unset-mode prevents that class of accident going forward.
        _rubric_mode_precheck = str(rubric_data.get("rubric_mode", "") or "").strip().lower()
        if not _rubric_mode_precheck:
            raise SystemExit(
                "GP-134 GATE FAIL: rubric uses fit_expression_grammar='py_exec' but does "
                "NOT declare rubric_mode. py_exec is algorithmically expressive; the rubric "
                "MUST explicitly declare rubric_mode ('newton' for discovery substrates, "
                "'kepler' for descriptive fits, 'calibration' for instrument tests). Refusing "
                "to launch rather than inherit silent default discipline. Add:\n"
                "  \"rubric_mode\": \"newton\",\n"
                "  \"rubric_mode_reason\": \"<explain why Newton/Kepler/calibration fits this substrate>\"\n"
                "See docs/concepts/rubric_specification.md § 16-18."
            )
    # --- end GP-133 R4 gates ---

    # --- GP-133 Round 4: rubric_mode governance + enforcement ---
    # rubric_mode is metadata AND a gate: when rubric_mode='newton', the
    # rubric MUST include a dimension whose name contains 'generative yield'
    # (case-insensitive) with weight >= 15. Without this, the Newton-mode
    # label is cosmetic — no enforcement. Fail-closed rather than silently
    # ignoring the discipline the rubric_mode claims to enforce.
    _rubric_mode = str(rubric_data.get("rubric_mode", "") or "").strip().lower()
    if _rubric_mode == "newton":
        _dims = rubric_data.get("dimensions", []) or []
        _has_gy = any(
            isinstance(d, dict)
            and "generative yield" in str(d.get("name", "")).lower()
            and int(d.get("weight", 0)) >= 15
            for d in _dims
        )
        if not _has_gy:
            raise SystemExit(
                "GP-133 R4 GATE FAIL: rubric declares rubric_mode='newton' but does NOT "
                "include a dimension whose name contains 'Generative Yield' with weight "
                ">= 15%. Newton-mode is meaningless without the dimension that enforces "
                "it. Either add the Generative Yield dimension (see docs/concepts/"
                "rubric_specification.md § 18) or downgrade the rubric to "
                "rubric_mode='kepler'. Refusing to launch."
            )
        print(
            "🧭 Newton-mode rubric detected (rubric_mode='newton'). Generative Yield "
            "dimension present. Judge will penalize proposals predicting no secondary "
            "observable beyond the primary fitting target."
        )
    elif _rubric_mode == "kepler":
        print("📐 Kepler-mode rubric (descriptive-fit-only). Generative Yield not enforced.")
    elif _rubric_mode == "calibration":
        print("🔧 Calibration-mode rubric (instrument-characterization). Discovery claims suppressed.")
    elif _rubric_mode:
        # non-empty but not one of the valid values
        raise SystemExit(
            f"GP-133 R4 GATE FAIL: rubric_mode={_rubric_mode!r} is not a recognized value. "
            f"Valid: 'newton', 'kepler', 'calibration'. Refusing to launch."
        )
    # absence of rubric_mode is not fatal — treat as legacy/unspecified
    # --- end rubric_mode handling ---

    # --- Epistemic Airgap: rubric-level override ---
    # Rubric can declare require_cross_family: true to enforce cross-family
    # mutator/judge even if the CLI flag was not passed. CLI flag takes
    # precedence (if set, it's already enforced above at model resolution).
    if not args.require_cross_family:
        _rubric_cross_family = rubric_data.get("require_cross_family", False)
        if _rubric_cross_family and _mutator_family == _judge_family:
            raise SystemExit(
                f"❌ Epistemic Airgap violation (rubric-declared): "
                f"Mutator ({MUTATOR_MODEL_ID}) and Judge ({JUDGE_MODEL_ID}) "
                f"are both {_mutator_family}. Rubric sets require_cross_family=true."
            )
    # --- end Epistemic Airgap ---

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
            "--model",
            (args.committee_model or args.judge_model),
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
_refresh_latest_evidence_gaps_from_eval(res, artifact_role="latest")
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
# WAR-T3 (2026-04-27): Two-tier champion promotion. The capped score
# alone collapses iter-8 raw=100 down to 50 alongside iter-5 raw=50,
# so champion logic cannot tell breakthrough from plateau and the iter-8
# Galaxy-Cluster Bridge form was lost in run_id 1777250273. Track raw
# judge score + gate failure count so the next iter's promotion check
# can use the latent gradient.
_res_cap_meta = res.get("score_cap_applied") or {}
best_raw_score = _res_cap_meta.get("original_judge_score") if isinstance(_res_cap_meta, dict) else None
if best_raw_score is None:
    best_raw_score = res["score"]
_best_gv = ((res.get("score_contract") or {})
            .get("deterministic_charter_gates", {})
            .get("results", {})) or {}
# WAR-T3 hotfix: `results` can be dict OR list shape — handle both.
if isinstance(_best_gv, dict):
    best_gate_failure_count = sum(
        1 for _g, _r in _best_gv.items()
        if isinstance(_r, dict) and _r.get("passed") is False
    )
elif isinstance(_best_gv, list):
    best_gate_failure_count = sum(
        1 for _r in _best_gv
        if isinstance(_r, dict) and _r.get("passed") is False
    )
else:
    best_gate_failure_count = 0
saved_best_anchor = _saved_best_comparison_anchor(res)
saved_best_score = saved_best_anchor["compare_score"]
if saved_best_anchor["status"] not in {"none", "compatible", "current_regime_unknown"}:
    # GP-167 fix: regime_mismatch and legacy_missing_regime no longer
    # discard the saved baseline. The new candidate must still beat
    # the old score to be promoted. The print is informational, not a
    # rebaselining trigger.
    print(
        "⚠️ Saved best score "
        f"{saved_best_anchor['raw_saved_score']} preserved for baseline comparison "
        f"despite scoring regime mismatch ({saved_best_anchor['status']}). "
        f"New candidate must exceed {saved_best_anchor['raw_saved_score']} to be "
        f"promoted; rubric edits do not silently discard prior bests."
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

    # GP-119: Post-champion Inverter review (Munger inversion + Popper tests)
    if res["score"] >= 50:
        try:
            from src.ztare.validator.inverter_agent import run_inverter
            _inverter_result = run_inverter(
                project_dir=Path(PROJECT_DIR),
                champion_thesis=read_file(THESIS_PATH),
                champion_score=res["score"],
                champion_weakest_point=res.get("weakest_point", ""),
                evidence_summary=read_file(EVIDENCE_PATH)[:500] if os.path.exists(EVIDENCE_PATH) else "",
            )
        except Exception as _inv_err:
            print(f"  🔬🔬🔬 GP-119 Inverter FAILED: {_inv_err}")
    else:
        print(f"  🔬 GP-119 Inverter: score {res['score']} < 50, skipped")

    # GP-151 / Task 22: Post-champion deterministic structural-blocker gates.
    # Replaces (or augments) the LLM-taxonomy hardkill catalog injection with
    # deterministic Python detectors: G-CIRC (DAG cycle detection) and
    # G-FALSIFY (test_model.py numeric-assertion + DAG watch_signal + thesis
    # rival check). Gate behind rubric flag `structural_blocker_enforcement`:
    #   "prompt"  — legacy default; only inject_antipattern_catalog runs.
    #   "gate"    — run G-CIRC + G-FALSIFY post-champion; skip catalog injection.
    #   "both"    — both layers active (belt-and-suspenders).
    # Default "prompt" preserves back-compat for in-flight runs (gp145b run-3).
    _sbe_mode = str(rubric_data.get("structural_blocker_enforcement") or "prompt").lower().strip()
    if _sbe_mode in ("gate", "both"):
        try:
            from src.ztare.gates.circularity_gate import run_circularity_gate
            from src.ztare.gates.falsifiability_gate import run_falsifiability_gate

            _dag_path = Path(PROJECT_DIR) / "champion_probability_dag.json"
            _circ = run_circularity_gate(_dag_path)
            print(
                f"  🧭 G-CIRC: {'✅ acyclic' if _circ['passed'] else '❌ CIRCULAR'} "
                f"({_circ.get('node_count', 0)} nodes, {_circ.get('edge_count', 0)} edges)"
            )
            if not _circ["passed"]:
                print(f"      cycle: {_circ.get('cycle')}")
                print(f"      rationale: {_circ.get('rationale', '')}")

            _tm_path = Path(PROJECT_DIR) / "test_model.py"
            _thesis_path = Path(THESIS_PATH)
            _fals = run_falsifiability_gate(_tm_path, _dag_path, _thesis_path)
            print(
                f"  🎯 G-FALSIFY: {'✅' if _fals['passed'] else '❌'} "
                f"strength={_fals.get('strength')} "
                f"asserts={_fals.get('n_numeric_assertions')} "
                f"watch_signals={_fals.get('n_watch_signals')} "
                f"rival={_fals.get('thesis_has_rival')} "
                f"discriminator={_fals.get('thesis_has_discriminator')}"
            )
            if not _fals["passed"]:
                print(f"      rationale: {_fals.get('rationale', '')}")

            # Persist verdicts for downstream telemetry / E-row mining.
            _ws_dir = Path(PROJECT_DIR) / "workspace"
            _ws_dir.mkdir(parents=True, exist_ok=True)
            (_ws_dir / "structural_blocker_gates_latest.json").write_text(json.dumps({
                "mode": _sbe_mode,
                "g_circ": _circ,
                "g_falsify": _fals,
            }, indent=2, default=str))
        except ImportError as _sbe_ie:
            print(f"  🧭 G-CIRC/G-FALSIFY: gate modules not importable: {_sbe_ie}")
        except Exception as _sbe_err:
            print(f"  🧭 G-CIRC/G-FALSIFY dispatch error (non-fatal): {_sbe_err}")
    # --- end Task 22 deterministic structural-blocker gates ---

    # GP-122: Post-champion Lean proof attempt (if compression gates passed)
    if res["score"] >= 70 and rubric_data.get("enable_lean_proof"):
        try:
            from src.ztare.formal.lean_repl import prove_from_compression
            print(f"  📐📐📐 GP-122 Lean REPL: attempting proof...")
            _lean_result = prove_from_compression(
                project_dir=Path(PROJECT_DIR),
                model=rubric_data.get("lean_prover_model", "gpt4.1"),
                max_attempts=5,
            )
            if _lean_result.get("proved"):
                print(f"  📐 ✅ LEAN PROOF VERIFIED in {_lean_result['attempts']} attempts!")
            else:
                print(f"  📐 Lean proof not found ({_lean_result.get('attempts', 0)} attempts)")
        except Exception as _lean_err:
            print(f"  📐📐📐 GP-122 Lean REPL FAILED: {_lean_err}")
    elif res["score"] >= 70:
        print(f"  📐 GP-122 Lean: enable_lean_proof not set in rubric")
    else:
        print(f"  📐 GP-122 Lean: score {res['score']} < 70, skipped")

    # GP-143: Post-champion continuous-chaotic pipeline validation.
    # Fires when rubric declares fit_score_mode: "dynamical_lattice" and the
    # champion score is >= 70. Runs the kernel-promoted solver
    # (src.ztare.fit.continuous_chaotic.run_pipeline) against the holdout
    # trajectory as independent validation of the mutator's thesis. Output
    # certified_subset JSONL is written to workspace for downstream G2 audit
    # and (if enable_lean_proof) GP-122 Lean compilation.
    # Wiring discipline: additive post-champion hook. Does NOT replace
    # fit_parameters call (which is gated by enable_fit_primitive; a
    # dynamical_lattice rubric should have enable_fit_primitive: false).
    # Legacy scalar path unchanged.
    if res["score"] >= 70 and rubric_data.get("fit_score_mode") == "dynamical_lattice":
        try:
            from src.ztare.fit.continuous_chaotic import run_pipeline as _cc_run_pipeline
            cc_params = rubric_data.get("dynamical_lattice") or {}
            _cc_holdout_dir = Path(PROJECT_DIR) / "_holdout_locked"
            _cc_truth_path = _cc_holdout_dir / "truth.json"
            _cc_traj_path = _cc_holdout_dir / "trajectories" / "traj_5.npy"
            if _cc_truth_path.is_file() and _cc_traj_path.is_file():
                import numpy as _cc_np
                _cc_truth = json.loads(_cc_truth_path.read_text())
                _cc_traj = _cc_np.load(_cc_traj_path)
                _cc_dt = float(cc_params.get("observation_dt", _cc_truth.get("dt", 0.01)))
                _cc_ic = _cc_np.array(_cc_truth.get("initial_state", _cc_traj[0]))
                print(f"  🌀🌀🌀 GP-143: continuous-chaotic pipeline running on "
                      f"holdout (shape={_cc_traj.shape}, dt={_cc_dt})...")
                _cc_result = _cc_run_pipeline(
                    trajectory=_cc_traj,
                    dt=_cc_dt,
                    rubric_params=cc_params,
                    initial_state=_cc_ic,
                )
                _cc_out = Path(PROJECT_DIR) / "workspace" / "continuous_chaotic_result.json"
                _cc_out.parent.mkdir(parents=True, exist_ok=True)
                _cc_out.write_text(json.dumps({
                    "tau_decorr": _cc_result.get("tau_decorr"),
                    "method_a_variant": _cc_result.get("method_a_variant"),
                    "n_candidates": len(_cc_result.get("candidates", []) or []),
                    "n_certified": len(_cc_result.get("certified_subset", []) or []),
                    "champion_coefficient_matrix": (
                        _cc_result.get("champion", {}).get("coefficient_matrix")
                        if _cc_result.get("champion") else None
                    ),
                }, indent=2, default=str))
                _n_cert = len(_cc_result.get("certified_subset", []) or [])
                print(f"  🌀 GP-143: {_n_cert} candidates passed Method B certification. "
                      f"Result: {_cc_out}")
            else:
                print(f"  🌀 GP-143: holdout trajectory not found at {_cc_traj_path}; "
                      "skipping continuous-chaotic validation.")
        except ImportError as _cc_ie:
            print(f"  🌀 GP-143: continuous_chaotic kernel not importable: {_cc_ie}")
        except Exception as _cc_err:
            print(f"  🌀🌀🌀 GP-143 continuous-chaotic pipeline FAILED: {_cc_err}")
    elif res["score"] >= 70:
        if rubric_data.get("fit_score_mode") == "dynamical_lattice":
            pass  # already handled above
        # else: rubric doesn't declare dynamical_lattice; no dispatch

    # GP-FOM: Post-champion fractional-operator validation (gp150-derived).
    # Fires when rubric declares enable_fom=true AND champion score >= 70 AND
    # the FOM gate-stack prerequisites are satisfied. Dispatches a heavy-tail
    # discriminator on holdout trajectory: computes fractional derivative at
    # declared α, checks whether the fourth spatial moment signature matches
    # the heavy-tail prediction (divergent under refinement) vs finite-mixture
    # baseline (bounded under refinement).
    # Wiring discipline: STRICTLY OPT-IN. Default off. Gate-stack preconditions
    # checked at runtime (G1 full + GP-146 Arnold cat map validation) — if
    # either precondition fails, dispatch is skipped with a telemetry warning
    # but does NOT fail the champion eval. Operator reads workspace for result.
    if (
        res["score"] >= 70
        and bool(rubric_data.get("enable_fom"))
    ):
        try:
            from src.ztare.fit.continuous_chaotic.fractional_operator import (
                compute_fractional_derivative,
            )
            # Gate-stack precondition check: G1 continuum_limit_gate full impl
            # + GP-146 self-validation pass are BOTH required before live FOM
            # dispatch per GP-144 discipline. We check a sentinel rubric field
            # that the operator sets only after validation is green.
            _fom_gate_cleared = bool(rubric_data.get("fom_gate_stack_validated"))
            if not _fom_gate_cleared:
                print(
                    "  🌊 GP-FOM: enable_fom=true but "
                    "fom_gate_stack_validated=false — dispatch skipped "
                    "(GP-144 discipline: need G1 full + GP-146 pass first). "
                    "Running OBSERVE-only diagnostic instead."
                )
            _fom_params = rubric_data.get("fom") or {}
            _alpha = float(_fom_params.get("alpha", 1.5))
            _n_grid = int(_fom_params.get("n_grid", 1024))
            _length = float(_fom_params.get("length", 20.0))
            import numpy as _np
            x_grid = _np.linspace(-_length / 2.0, _length / 2.0, _n_grid, endpoint=False)
            _dx = float(_length / _n_grid)
            # Heavy-tail diagnostic: initial chi_{[-1,1]} from the 71-thesis spec
            u0 = ((x_grid >= -1.0) & (x_grid <= 1.0)).astype(float)
            # Snapshot of the fractional Laplacian applied once — the operator
            # itself diverges near the step; |k|^α multiplier highlights tail.
            u_alpha = compute_fractional_derivative(u0, _dx, _alpha)
            # Discriminator: fourth-moment (on the derivative) as a tail proxy.
            # Not the full M4 divergence test (requires time-evolution), but a
            # cheap static signature that the thesis's named discriminator form
            # is computable in this environment.
            _m4 = float(_np.sum(_np.abs(x_grid) ** 4 * _np.abs(u_alpha)) * _dx)
            _fom_out = Path(PROJECT_DIR) / "workspace" / "fom_diagnostic.json"
            _fom_out.parent.mkdir(parents=True, exist_ok=True)
            _fom_out.write_text(json.dumps({
                "alpha": _alpha,
                "n_grid": _n_grid,
                "length": _length,
                "m4_fractional_operator_applied_to_chi": _m4,
                "gate_stack_validated": _fom_gate_cleared,
                "mode": "live" if _fom_gate_cleared else "observe",
                "note": (
                    "Cheap static fourth-moment signature on one application "
                    "of |k|^alpha to chi_[-1,1]. Full time-evolution divergence "
                    "test requires heavy-tail subordinator wiring (deferred)."
                ),
            }, indent=2))
            _mode_label = "LIVE" if _fom_gate_cleared else "OBSERVE"
            print(
                f"  🌊 GP-FOM [{_mode_label}]: alpha={_alpha} N={_n_grid} "
                f"M4_signature={_m4:.4e}. Result: {_fom_out}"
            )
        except ImportError as _fom_ie:
            print(f"  🌊 GP-FOM: fractional_operator not importable: {_fom_ie}")
        except Exception as _fom_err:
            print(f"  🌊 GP-FOM diagnostic FAILED: {_fom_err}")

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
# GP-105 M-Form Alignment Audit: counter for audits fired this run.
# Caps at _MAX_AUDITS_PER_RUN (2) per run to prevent SNR degradation.
_mform_audits_this_run: int = 0
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


def _compute_holdout_audit_mre_for_run() -> dict | None:
    """Run-end audit MRE on the champion form against the held-out audit slice.

    Substrate opt-in via rubric.holdout_audit_fraction > 0. The substrate's
    features module is expected to expose `audit_rows()` returning
    [(row_id, y_observed, features_dict), ...] when the audit slice is
    populated. Returns None when audit is disabled, the substrate doesn't
    expose audit_rows(), or no champion is available.

    Fail-graceful: never raises. Diagnostic dict is returned on every
    error path so the run_end record always tells the operator what
    happened.
    """
    try:
        _audit_frac = float(rubric_data.get("holdout_audit_fraction") or 0.0)
    except (TypeError, ValueError):
        _audit_frac = 0.0
    if _audit_frac <= 0.0:
        return None
    try:
        # Import the substrate's features module from the project dir.
        import importlib
        import importlib.util as _ilu
        _features_path = Path(PROJECT_DIR) / "features.py"
        if not _features_path.exists():
            return {"audit_enabled": True, "skipped": "features.py_absent"}
        _spec = _ilu.spec_from_file_location(
            f"_audit_features_{Path(PROJECT_DIR).name}", _features_path
        )
        if _spec is None or _spec.loader is None:
            return {"audit_enabled": True, "skipped": "features_spec_failed"}
        _features_mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_features_mod)  # type: ignore[union-attr]
        if not hasattr(_features_mod, "audit_rows"):
            return {
                "audit_enabled": True,
                "skipped": "features.audit_rows_absent",
                "audit_fraction": _audit_frac,
            }
        _audit_rows = list(_features_mod.audit_rows())
        if not _audit_rows:
            return {
                "audit_enabled": True,
                "skipped": "audit_rows_empty",
                "audit_fraction": _audit_frac,
            }

        # Load the champion's I_model from test_model.py / thesis form.
        # Use the same import pattern: load test_model.py as a module so
        # MODEL_PARAMS + I_model are bound. Fail-graceful when the
        # champion isn't importable.
        _tm_path = Path(PROJECT_DIR) / "test_model.py"
        if not _tm_path.exists():
            return {
                "audit_enabled": True,
                "skipped": "test_model.py_absent",
                "audit_fraction": _audit_frac,
                "n_audit_rows": len(_audit_rows),
            }
        _tm_spec = _ilu.spec_from_file_location(
            f"_audit_tm_{Path(PROJECT_DIR).name}", _tm_path
        )
        if _tm_spec is None or _tm_spec.loader is None:
            return {
                "audit_enabled": True,
                "skipped": "test_model_spec_failed",
                "audit_fraction": _audit_frac,
            }
        _tm_mod = _ilu.module_from_spec(_tm_spec)
        try:
            _tm_spec.loader.exec_module(_tm_mod)  # type: ignore[union-attr]
        except SystemExit:
            # test_model.py often calls sys.exit on assertion failure;
            # it still leaves I_model bound at module top-level if the
            # import reached that point. Tolerate.
            pass
        except Exception as _tm_exc:
            return {
                "audit_enabled": True,
                "skipped": f"test_model_import_error:{type(_tm_exc).__name__}",
                "audit_fraction": _audit_frac,
            }
        _i_model = getattr(_tm_mod, "I_model", None)
        if _i_model is None:
            return {
                "audit_enabled": True,
                "skipped": "I_model_absent",
                "audit_fraction": _audit_frac,
            }

        from src.ztare.orchestrator.holdout_audit import (
            compute_audit_mre as _compute_audit_mre,
        )
        _result = _compute_audit_mre(_audit_rows, _i_model)
        _result["audit_enabled"] = True
        _result["audit_fraction"] = _audit_frac
        return _result
    except Exception as _audit_exc:  # noqa: BLE001
        return {
            "audit_enabled": True,
            "skipped": f"audit_compute_error:{type(_audit_exc).__name__}",
            "detail": str(_audit_exc)[:200],
        }


def _finalize_run_telemetry_once() -> None:
    if _run_telemetry_state["finalized"]:
        return
    _run_telemetry_state["finalized"] = True
    _audit_mre_block = _compute_holdout_audit_mre_for_run()
    _payload = {
        "record_type": "run_end",
        "run_id": RUN_ID,
        "timestamp_utc": _utc_now_iso(),
        "final_iteration": last_completed_iteration,
        "final_score": best_score,
        "run_exit_reason": run_exit_reason,
    }
    if _audit_mre_block is not None:
        _payload["holdout_audit"] = _audit_mre_block
        # Surface to operator console so the audit MRE isn't buried.
        if "mean_relative_error" in _audit_mre_block:
            _amre = _audit_mre_block.get("mean_relative_error")
            print(
                f"🔒 holdout_audit: n={_audit_mre_block.get('n')} "
                f"mre={_amre} fraction={_audit_mre_block.get('audit_fraction')}"
            )
        elif "skipped" in _audit_mre_block:
            print(f"🔒 holdout_audit: skipped — {_audit_mre_block.get('skipped')}")
    _append_run_boundary_telemetry(workspace_dir, _payload)


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

# ── GP-157 §3a backport (Task #151, 2026-04-26) ──
# R13 substrate_critic + R14 noise_profile preflight gates dispatched via
# the Cage. Replaces the legacy direct-wired pre-iter-1 if-blocks. Each
# adapter reads cage_meta + rubric_flags via can_handle, builds artifacts
# under workspace/, and noise_profile auto-routes solver flags
# (operator-set flags always win — auto-route only fills in absent keys).
try:
    from src.ztare.orchestrator.pre_fit_dispatch import (
        dispatch_preflight_cage as _dispatch_preflight,
    )
    _preflight_verdict = _dispatch_preflight(
        cage_runtime=_v5_runtime,
        rubric_data=rubric_data,
        project_dir=Path(PROJECT_DIR),
        workspace_dir=workspace_dir,
        project_name=str(args.project),
    )
    for _ln in _preflight_verdict.log_lines:
        print(_ln)
except ImportError:
    pass
except Exception as _pre_exc:
    # Preflight gates are diagnostic; never fail the run.
    print(f"🦴 preflight Cage dispatch error (non-fatal): {_pre_exc}")

# GP-169 pre-iter-1 cold-LLM Erdős seed dispatch (Phase 4g Torvalds split).
# Runs ONCE before the iter loop starts. Reads rubric flag
# enable_cold_llm_erdos_seed; computes anonymized fingerprint; calls cold
# LLM with explicit forbidden-domain; persists to workspace; the iter-1+
# mutator briefing's ColdLlmSeedBriefingProvider reads the artifact and
# renders MANDATORY-CONSIDER. Future once-per-run hooks register inside
# orchestrator/pre_iter1_dispatch.py — no inline accretion here.
try:
    from src.ztare.orchestrator.pre_iter1_dispatch import (
        dispatch_pre_iter1_cage as _dispatch_pre_iter1,
    )
    _pre_iter1_verdict = _dispatch_pre_iter1(
        project_dir=Path(PROJECT_DIR),
        rubric_data=rubric_data,
        mutator_model_id=MUTATOR_MODEL_ID,
    )
    for _ln in _pre_iter1_verdict.log_lines:
        print(_ln)
except ImportError:
    pass

# META-GATE 2 EGE pre-iter-1 trigger (opt-in via
# rubric.enable_evidence_gap_enrichment_proposals). Fires only when R26 has
# populated `withheld_class_feature_collapses` in substrate_critique.json
# (which the preflight Cage dispatch above writes). Fail-graceful.
if bool(rubric_data.get("enable_evidence_gap_enrichment_proposals", False)):
    try:
        from src.ztare.orchestrator.evidence_gap_enrichment import (
            propose_evidence_gap_enrichment as _propose_ege,
        )
        _ege_verdict = _propose_ege(
            project_dir=Path(PROJECT_DIR),
            rubric_data=rubric_data,
            mutator_model_id=MUTATOR_MODEL_ID,
        )
        print(
            f"🧪 EGE pre-iter-1 trigger: gaps_seen={_ege_verdict.get('n_gaps_seen')} "
            f"model={_ege_verdict.get('model_id_used')} "
            f"artifact={_ege_verdict.get('artifact_path')}"
        )
    except Exception as _ege_exc:  # noqa: BLE001
        print(f"🧪 EGE pre-iter-1 error (non-fatal): {_ege_exc}")

for i in range(ITERATIONS):
    print(
        f"\n--- Iteration {i + 1} (Score: {best_score} | Stagnation: {stagnation_count}) ---"
    )
    iteration_start_utc = _utc_now_iso()
    iteration_mutator_usage_before = _usage_bucket_snapshot(SESSION_MUTATOR_USAGE)
    iteration_judge_usage_before = _usage_bucket_snapshot(SESSION_JUDGE_USAGE)

    # GP-157 v5.0 Phase 4a step 2 — IterContext snapshot (Hickey decomplecting).
    # Populated additively from existing per-iter locals; Phase 3c will switch
    # the Cage dispatch block + future orchestrator/{telemetry,state} extracts
    # to read fields off ctx instead of module-level globals.
    from src.ztare.orchestrator import IterContext as _IterContext
    ctx = _IterContext(
        iteration_index=i,
        run_id=RUN_ID,
        project=args.project,
        workspace_dir=workspace_dir,
        rubric_data=rubric_data,
        cage_observe_mode=bool(_v5_observe_mode),
        cage_meta=rubric_data.get("cage_meta"),
        mutator_model_id=str(MUTATOR_MODEL_ID),
        judge_model_id=str(JUDGE_MODEL_ID),
    )

    # GP-157 v5.0 Phase 3b — Cage observe-mode dispatch (additive only).
    # Runs once per iter against the current substrate view. Logs the
    # engagement matrix to workspace/cage_engagement.jsonl. Does NOT
    # change existing dispatch flow; surfaces R8/R9 advisory diagnostics.
    if _v5_cage_instance is not None and _v5_cage_substrate_view is not None:
        try:
            _v5_candidate_payload = {"iter": i + 1, "thesis_path": THESIS_PATH}
            if _v5_authoritative_mode:
                # Phase 3c: authoritative dispatch — engaged gates run.
                _v5_em, _v5_run_results = _v5_cage_instance.dispatch_and_run(
                    _v5_cage_substrate_view, _v5_candidate_payload
                )
            else:
                _v5_em = _v5_cage_instance.dispatch(
                    _v5_cage_substrate_view, _v5_candidate_payload
                )
                _v5_run_results = {}
            # Phase 4b: emission + summary moved to orchestrator/telemetry.py.
            from src.ztare.orchestrator import (
                emit_cage_engagement as _emit_cage_engagement,
                format_cage_observe_summary as _format_cage_observe_summary,
            )
            _v5_record = _emit_cage_engagement(ctx, utc=iteration_start_utc, engagement_matrix=_v5_em)
            _v5_mode_label = "authoritative" if _v5_authoritative_mode else "observe"
            print(_format_cage_observe_summary(_v5_record, mode=_v5_mode_label))
            # Phase 3c: surface authoritative run errors prominently so a
            # silent gate-run failure cannot masquerade as engagement-only.
            if _v5_authoritative_mode and _v5_run_results:
                _v5_run_errors = {n: r for n, r in _v5_run_results.items() if isinstance(r, dict) and "__error__" in r}
                if _v5_run_errors:
                    print(f"🦴 v5 Cage AUTHORITATIVE: {len(_v5_run_errors)} gate run errors: {list(_v5_run_errors)}")
        except Exception as _v5_dispatch_err:  # noqa: BLE001
            print(f"🦴 v5 Cage observe-mode dispatch error (non-fatal): {_v5_dispatch_err}")

    # GP-105 M-Form: apply any pending General Office finding from previous iteration.
    # Async boundary: audit fires after PHASE_F (end of prev iter), applied here before PHASE_A.
    rubric_data, _mform_applied = apply_mform_pending(
        rubric_data=rubric_data,
        workspace_dir=workspace_dir,
        rubrics_dir=RUBRICS_DIR,
        rubric_name=args.rubric,
    )

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
            f"🚨 R4 ACTION {pending_loop_action.value}: Refreshing Specialized Verification Panel..."
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
    _rubric_stag_override = rubric_data.get("composition_stagnation_threshold")
    if _rubric_stag_override is not None:
        _rubric_stag_override = int(_rubric_stag_override)
    current_loop_control_action = _current_loop_control_action(
        pending_loop_action=pending_loop_action,
        dynamic_enabled=args.dynamic,
        is_v4_project=current_is_v4_project,
        falsification_mode=current_falsification_mode,
        stagnation_count=stagnation_count,
        rubric_mode=rubric_data.get("rubric_mode"),
        rubric_stagnation_override=_rubric_stag_override,
    )
    current_pivot_state = resolve_stagnation_pivot_state(
        is_v4_project=current_is_v4_project,
        falsification_mode=current_falsification_mode,
        stagnation_count=stagnation_count,
        rubric_mode=rubric_data.get("rubric_mode"),
        rubric_stagnation_override=_rubric_stag_override,
    )
    current_pivot_profile = current_pivot_state.profile

    # GP-149 I-2 / I-3: observe-mode telemetry for mining-derived pivot routing.
    # Gated by rubric flags. Default: off. First rollout is OBSERVE-ONLY to
    # collect classifier-accuracy data before any pivot_state mutation.
    # Once operator confirms classifier accuracy on live data, the "suppress"
    # mode can be enabled by changing the rubric flag values.
    try:
        from src.ztare.validator.weakest_link_classifier import (
            classify_weakest_point,
            is_pivot_ineffective_class,
            PIVOT_INEFFECTIVE_CLASSES,
        )
        _current_weakest = ""
        try:
            _current_weakest = (
                iteration_history[-1].get("weakest_point", "")
                if iteration_history else ""
            )
        except Exception:
            _current_weakest = ""
        _wl_class = classify_weakest_point(_current_weakest) if _current_weakest else None

        # I-2: class-aware stagnation observe
        _min_cls_thresh = int(rubric_data.get("min_distinct_weakest_classes_before_stagnation") or 0)
        if _min_cls_thresh > 0:
            # Session-local tracking via a list attached to globals
            global _GP149_SESSION_CLASSES  # noqa: PLW0603 — intentional session tracking
            try:
                _GP149_SESSION_CLASSES
            except NameError:
                _GP149_SESSION_CLASSES = set()
            if _wl_class is not None:
                _GP149_SESSION_CLASSES.add(_wl_class)
            if (current_pivot_state.event_type in ("topological_pivot_emergency", "topological_pivot_profile_injected")
                and len(_GP149_SESSION_CLASSES) < _min_cls_thresh):
                print(
                    f"  📊 GP-149 I-2 observe: pivot would fire but only "
                    f"{len(_GP149_SESSION_CLASSES)} distinct classes seen "
                    f"(threshold {_min_cls_thresh}); would suppress in active mode. "
                    f"Classes: {sorted(_GP149_SESSION_CLASSES)}"
                )

        # I-3: pivot-ineffective-class observe
        _pivot_mode = str(rubric_data.get("pivot_ineffective_class_mode") or "off").lower()
        # GP-151 sensor lockdown (2026-04-24): "suppress" mode requires the
        # operator-set sentinel `classifier_live_routing_validated=true` in the
        # rubric. Otherwise silently downgraded to "observe" with a warning.
        # Rationale: 3-way LLM classifier agreement is 48% fine / 75% super-class,
        # both below the 90% gate. The classifier is a TELEMETRY sensor, not a
        # steering actuator. See GP-151 seam §8.
        if _pivot_mode == "suppress" and not bool(rubric_data.get("classifier_live_routing_validated")):
            print(
                "  🔒 GP-151 sensor lockdown: pivot_ineffective_class_mode='suppress' "
                "requested but classifier_live_routing_validated=false. "
                "Downgrading to 'observe'. (Cross-LLM super-class agreement 75% < 90% gate.)"
            )
            _pivot_mode = "observe"
        if _pivot_mode in ("observe", "suppress"):
            if (current_pivot_state.event_type in ("topological_pivot_emergency", "topological_pivot_profile_injected")
                and is_pivot_ineffective_class(_wl_class)):
                print(
                    f"  📊 GP-149 I-3 {_pivot_mode}: weakest-link class='{_wl_class}' "
                    f"is in PIVOT_INEFFECTIVE_CLASSES={sorted(PIVOT_INEFFECTIVE_CLASSES)}. "
                    f"Data says pivot mean-Δ negative/lukewarm for this class."
                )
                if _pivot_mode == "suppress":
                    # Active mode: downgrade pivot state to no-action (session-specific)
                    # Conservative approach: mark via a side channel rather than
                    # mutating the dataclass. Operator reading loop_events will see
                    # a "pivot_skipped_gp149_i3" event next.
                    _record_loop_event(
                        workspace_dir,
                        event_type="pivot_skipped_gp149_i3",
                        iteration_index=i + 1,
                        stagnation_count=stagnation_count,
                        falsification_mode=current_falsification_mode,
                        is_v4_project=current_is_v4_project,
                        pivot_profile=current_pivot_profile,
                        pending_loop_action=pending_loop_action.value,
                        mutator_model_id=current_mutator,
                        judge_model_id=JUDGE_MODEL_ID,
                    )
    except ImportError:
        pass
    except Exception as _gp149_err:
        print(f"  ⚠️  GP-149 observability error (non-fatal): {_gp149_err}")
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
    if current_pivot_state.event_type == "v4_bounded_mutation_override":
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
    elif current_pivot_state.event_type == "topological_pivot_emergency":
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
    elif current_pivot_state.event_type == "topological_pivot_profile_injected":
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
                    _seed_fd_dict = {
                        "expression": _seed_expr,
                        "independent_vars": _seed_vars,
                        "parameter_names": _seed_params,
                    }
                    if "initial_guesses" in _seed_data:
                        _seed_fd_dict["initial_guesses"] = _seed_data["initial_guesses"]
                    _seed_fd_block = json.dumps(_seed_fd_dict, indent=2)
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
                        f"```fit_declaration\n{_seed_fd_block}\n```\n\n"
                        # Synthetic stub satisfies validate_python_suite_candidate so
                        # _prepare_mutation_candidate passes R1. Layer 3 Mandatory
                        # (fit primitive) fires downstream and overwrites this stub
                        # with the deterministically fitted f() before test_model.py
                        # is written to disk. The stub never executes.
                        "```python\n"
                        "assert False, 'Component D seed — Layer 3 Mandatory will overwrite this stub.'\n"
                        "```\n"
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
                fit_primitive_features_enabled=rubric_data.get("enable_fit_primitive_features", False),
                fit_primitive_features_k_max=int(rubric_data.get("fit_primitive_features_k_max", 8)),
                fit_context=_fit_ctx,
                structural_memory_context=_structural_memory_ctx,
                cold_residual_mode=_cold_residual_mode,
                residual_mode_context=_residual_mode_ctx,
                gp048_cohort_context=_gp048_cohort_ctx,
                farther_tail_veto_context=_farther_tail_veto_ctx,
                component_c_context=_component_c_ctx,
                divergence_sweep_context=_divergence_sweep_ctx,
            )
        _runner_allowed_raw = rubric_data.get("runner_allowed_imports", ()) or ()
        _runner_allowed = tuple(
            str(x).strip() for x in _runner_allowed_raw if isinstance(x, str) and x.strip()
        )

        # GP-157 "Compiler Bounce" — 3-strike free retry for R1 lint-class
        # rejections (2026-04-25). Operator insight: AST/syntax/contract
        # failures shouldn't consume an iteration. They're linter problems,
        # not scientific failures. Same precedent as GP-035 Turn 10
        # FIT_DECLARATION drought retry, but generalized to all R1
        # rejections from `_prepare_mutation_candidate`.
        #
        # Strikes: 0..MAX_R1_RETRIES. On each strike, re-prompt the mutator
        # with the SPECIFIC error from R1 and ask for a corrected
        # submission. After MAX_R1_RETRIES, propagate the final ValueError
        # → iter consumed as catastrophic FAIL_RUNTIME.
        _MAX_R1_RETRIES = 3
        _r1_strike = 0
        _r1_last_error = None
        mutation_declaration = mutation_validation = clean_thesis = None
        python_code = full_candidate = None
        while True:
            try:
                mutation_declaration, mutation_validation, clean_thesis, python_code, full_candidate = _prepare_mutation_candidate(
                    raw_text=new_content,
                    current_thesis=current_thesis,
                    current_test_model=current_test_model,
                    falsification_mode=rubric_falsification_mode,
                    runner_allowed_imports=_runner_allowed,
                    project_dir=PROJECT_DIR,
                )
                # GP-157 v5.0 — apparatus-level adherence reject (2026-04-25
                # night). After R1 contract passes, also check the candidate's
                # test_model.py for active-contract adherence (Contract A/B/C).
                # gp159 empirical evidence: gpt-4.1 satisfies the literal R1
                # constraint by hiding I_model calls in `_post_fit_sanity()`,
                # leaving I_model itself returning NaN. Detect via shared
                # check_contract_adherence; if any BLOCKING violation, raise
                # ValueError so the existing R1 retry path re-prompts the mutator.
                # Free retry, iter not consumed (same as R1 behavior).
                try:
                    from src.ztare.orchestrator.contract_adherence import (
                        check_contract_adherence as _adherence_check,
                        runtime_check_imodel as _runtime_check_imodel,
                    )
                    _adherence_blocking = {
                        "deferred_assert_helper",
                        "missing_imodel_def",
                        "nan_return_literal",
                        "runtime_nan_return",
                        "runtime_import_failure",
                        "runtime_imodel_raises",
                    }
                    # Static check on python_code (pre-write).
                    _static_violations = _adherence_check(
                        python_code or "",
                        rubric_data,
                        Path(PROJECT_DIR),
                    )
                    # Runtime check on the candidate after writing it to a
                    # tmp probe path that mirrors the substrate's neighbors
                    # (features.py etc.). Use a TEMP file so we don't
                    # pollute the substrate's actual test_model.py until
                    # we've decided the candidate is acceptable.
                    _runtime_violations: list[str] = []
                    try:
                        import tempfile as _tempfile
                        _probe_path = Path(PROJECT_DIR) / "_adherence_probe_test_model.py"
                        _probe_path.write_text(_ensure_canonical_model_aliases(python_code or ""), encoding="utf-8")
                        _runtime_violations = _runtime_check_imodel(_probe_path)
                    except Exception:
                        _runtime_violations = []  # probe is best-effort
                    finally:
                        try:
                            _probe_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                    _hits = (set(_static_violations) | set(_runtime_violations)) & _adherence_blocking
                    if _hits:
                        raise ValueError(
                            f"adherence reject: candidate test_model.py violates "
                            f"the active substrate contract — codes={sorted(_hits)}. "
                            f"The apparatus IMPORTS test_model.py at gate-time and "
                            f"calls I_model on each VISIBLE_SET row. Common causes: "
                            f"asserts hidden in non-called helpers (e.g. _post_fit_sanity); "
                            f"I_model returns NaN/inf/None; module-level division by zero; "
                            f"missing def I_model entirely. "
                            f"Define I_model in-place, use p.get(name, default) for every "
                            f"param read so it works pre-fit (MODEL_PARAMS={{}}), guard "
                            f"divisors against zero, return float() of every result, and "
                            f"do NOT defer logic to functions the apparatus never invokes."
                        )
                except ImportError:
                    pass  # adherence module unavailable — degrade gracefully

                # GP-168 AST-distance enforcement (2026-04-26 night).
                # When Forced-REFRAME has fired for the current iter,
                # banning the previous iter's AST family, REJECT submissions
                # whose PARAMETRIC_FORM AST bucket matches the banned bucket.
                # This is the missing teeth behind the "MANDATORY architectural
                # alternatives" briefing block: without enforcement, the
                # mutator just prose-rationalizes ignoring the alternatives
                # and reaches for variants of the banned family. Free retry,
                # iter not consumed (same as R1 behavior).
                try:
                    from src.ztare.orchestrator.forced_reframe import (
                        check_forced_reframe_compliance as _fr_compliance,
                    )
                    # Extract PARAMETRIC_FORM from python_code (string literal).
                    _form_str = ""
                    try:
                        import ast as _ast
                        _tree = _ast.parse(python_code or "")
                        for _node in _ast.walk(_tree):
                            if (isinstance(_node, _ast.Assign)
                                    and len(_node.targets) == 1
                                    and isinstance(_node.targets[0], _ast.Name)
                                    and _node.targets[0].id == "PARAMETRIC_FORM"):
                                try:
                                    _form_str = _ast.literal_eval(_node.value)
                                    if not isinstance(_form_str, str):
                                        _form_str = ""
                                except (ValueError, SyntaxError):
                                    _form_str = ""
                                break
                    except Exception:
                        _form_str = ""
                    if _form_str:
                        _fr_violation = _fr_compliance(
                            workspace_dir=Path(PROJECT_DIR) / "workspace",
                            iter_index=i + 1,
                            submitted_form=_form_str,
                        )
                        if _fr_violation:
                            raise ValueError(_fr_violation)
                except ImportError:
                    pass  # forced_reframe module unavailable — degrade gracefully

                # GP-166 Fix D (2026-04-25 night): pre-submission denylist
                # scan as R1 retry. Without this, the mutator's iter
                # zero-fails on `global_named_import_check` only AFTER the
                # judge has been called and the iter consumed. The denylist
                # gate cannot trigger an R1 retry from inside test_thesis,
                # so the contamination defense was post-hoc. Scanning here
                # — at R1 prep time — gives the mutator a free retry to
                # rewrite without forbidden terms before the judge sees it.
                # The contamination_defense briefing provider still surfaces
                # historical hits to the next iter; this gate is the
                # immediate enforcement.
                _denylist_paths = [
                    Path(PROJECT_DIR) / ".thesis_denylist",
                    Path(PROJECT_DIR) / ".denylist",
                ]
                _denylist_path = next((p for p in _denylist_paths if p.exists()), None)
                if _denylist_path is not None and clean_thesis:
                    try:
                        _denylist_terms = [
                            ln.strip() for ln in _denylist_path.read_text(encoding="utf-8").splitlines()
                            if ln.strip() and not ln.strip().startswith("#")
                        ]
                        _denylist_hits: list[str] = []
                        _ct_lower = clean_thesis.lower()
                        for _term in _denylist_terms:
                            _tl = _term.lower()
                            if " " in _tl or "_" in _tl:
                                _pat = re.escape(_tl)
                            else:
                                _pat = r"\b" + re.escape(_tl) + r"\b"
                            if re.search(_pat, _ct_lower):
                                _denylist_hits.append(_term)
                        if _denylist_hits:
                            raise ValueError(
                                f"Thesis prose contains denylist terms (forbidden in this "
                                f"substrate): {_denylist_hits}. These terms would hard-fail "
                                f"the global_named_import_check gate post-judge. Rewrite the "
                                f"thesis without these terms; the structural argument can be "
                                f"made using only the anonymized features the substrate exposes "
                                f"(see evidence.txt for the canonical feature names). The "
                                f"iteration is NOT consumed by this rejection — it is a free "
                                f"R1 retry."
                            )
                    except ValueError:
                        raise  # propagate to R1 retry handler
                    except Exception:
                        pass  # never let denylist scanning break the apparatus

                # 2026-04-27: pre-flight AST + whitelist validation on
                # PARAMETRIC_FORM. The mutator has been writing forms like
                # `PARAMETRIC_FORM = 'I_model(features, params)'` (self-reference)
                # or pseudo-code with `->` arrows that pass the import-time
                # adherence check (the I_model function body itself imports
                # fine) but die later at fit dispatch when scipy.optimize tries
                # to AST-eval the form against the whitelist. Catching this at
                # R1-time turns the wasted iter into a free retry.
                try:
                    from src.ztare.fit.fit_primitive_features import (
                        extract_form_declaration as _ffp_extract_form,
                        _safe_compile_form as _ffp_safe_compile,
                    )
                    _r1_form_decl = _ffp_extract_form(python_code or "")
                    if _r1_form_decl is not None:
                        _r1_form_str, _r1_pnames, _ = _r1_form_decl
                        if _r1_form_str:
                            try:
                                _ffp_safe_compile(_r1_form_str)
                            except ValueError as _r1_form_exc:
                                raise ValueError(
                                    f"PARAMETRIC_FORM AST/whitelist pre-flight FAILED: "
                                    f"{str(_r1_form_exc)[:1200]}"
                                ) from _r1_form_exc
                except ImportError:
                    pass  # fit primitive unavailable — degrade gracefully
                except ValueError:
                    raise  # propagate to R1 retry handler

                if _r1_strike > 0:
                    print(f"🔁 R1 compiler-bounce: RECOVERED after {_r1_strike} strike(s)")
                break
            except ValueError as _r1_exc:
                _r1_strike += 1
                _r1_last_error = str(_r1_exc)
                if _r1_strike > _MAX_R1_RETRIES:
                    print(
                        f"🚫 R1 compiler-bounce: {_MAX_R1_RETRIES}/{_MAX_R1_RETRIES} "
                        f"strikes exhausted; consuming iteration. Final error: "
                        f"{_r1_last_error[:160]}"
                    )
                    raise
                print(
                    f"🔁 R1 compiler-bounce strike {_r1_strike}/{_MAX_R1_RETRIES} "
                    f"(free retry; iter NOT consumed): {_r1_last_error[:160]}"
                )
                # Build a focused retry prompt — short, points at the
                # specific R1 violation, includes the prior submission
                # so the mutator can correct in-place.
                _retry_prompt = (
                    "Your prior submission was rejected by the R1 lint check (NOT a "
                    "scientific failure — just a contract violation). Specific error:\n\n"
                    f"  {_r1_last_error}\n\n"
                    "Fix this exact issue and resubmit your thesis + Python suite. "
                    "Preserve the rest of your prior submission. The iteration counter "
                    "has NOT advanced; this is a free retry. Do NOT change your thesis "
                    "or scientific approach — only fix the contract violation.\n\n"
                    "Your prior submission was:\n"
                    f"```\n{(new_content or '')[:6000]}\n```\n"
                )
                try:
                    new_content = safe_mutate(_retry_prompt, model_id=current_mutator)
                except Exception as _retry_call_exc:
                    print(
                        f"🚫 R1 compiler-bounce: retry mutator call failed "
                        f"({type(_retry_call_exc).__name__}); consuming iteration."
                    )
                    raise _r1_exc
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
                    # GP-133 R4: expression byte budget enforcement (anti-lookup-table)
                    _byte_budget = rubric_data.get("expression_byte_budget")
                    if _byte_budget and len(_fit_decl.expression.encode("utf-8")) > _byte_budget:
                        print(
                            f"🛡️  GP-133 R4: expression rejected — "
                            f"{len(_fit_decl.expression.encode('utf-8'))} bytes exceeds "
                            f"budget {_byte_budget}. Likely lookup table or ternary chain."
                        )
                        _fit_decl = None
                if _fit_decl is not None:
                    _fit_dimensionality = rubric_data.get("fit_required_dimensionality")
                    _fit_expression_grammar = rubric_data.get("fit_expression_grammar")
                    _diag_classification = ""
                    _fit_score_mode = rubric_data.get("fit_score_mode", "continuous_l2")
                    # GP-095: multi-start fitting. Default 1 start;
                    # escalate to 3 starts when stagnation_count >= 3.
                    _n_starts = 3 if stagnation_count >= 3 else 1
                    _gate_thr_for_fit = float(rubric_data.get("gate_residual_threshold", 0.05))
                    # GP-157 §3a backport (Task #151): R16 1D framer dispatched
                    # via Cage PRE_FIT phase. Replaces the legacy direct-wired
                    # observe-mode block — adapter parses evidence, runs frame(),
                    # writes workspace/framing_report.json. Behavior is identical;
                    # routing now goes through can_handle (rubric.enable_framer +
                    # cage_meta.class) instead of an inline rubric flag check.
                    try:
                        from src.ztare.orchestrator.pre_fit_dispatch import (
                            dispatch_pre_fit_cage as _dispatch_pre_fit,
                        )
                        _pre_fit_verdict = _dispatch_pre_fit(
                            cage_runtime=_v5_runtime,
                            rubric_data=rubric_data,
                            workspace_dir=workspace_dir,
                            iter_index=i,
                            fit_decl=_fit_decl,
                            fit_required_dimensionality=_fit_dimensionality,
                            evidence_text=evidence_text,
                        )
                        for _ln in _pre_fit_verdict.log_lines:
                            print(f"  {_ln}")
                    except ImportError:
                        pass
                    except Exception as _pf_exc:
                        print(f"  🪞 PRE_FIT Cage dispatch error (non-fatal): {_pf_exc}")

                    # GP-157 v5.0 Phase 2 AUTHORITATIVE wire-in (L70, 2026-04-25 night):
                    # The fit dispatch now goes through FitEngine.select_adapter().
                    # The Protocol routes by substrate.meta['class'] — same
                    # rubric/cage_meta the rest of the apparatus reads. The
                    # adapter's `fit()` is a drop-in for the legacy direct
                    # call (returns native FitSuccess|FitFailure for
                    # downstream isinstance checks).
                    #
                    # If select_adapter returns None (no engine matches
                    # the substrate class), fall back to the legacy direct
                    # call as a safety net. After full substrate-class
                    # coverage validates, the fallback is removed.
                    from src.ztare.fit.fit_engine import select_adapter as _select_adapter
                    from types import SimpleNamespace as _SubNS
                    _l70_substrate = _SubNS(meta=rubric_data.get("cage_meta") or {"class": "1d"})
                    # Pass python_code (raw mutator text containing FIT_DECLARATION
                    # block) as the candidate, NOT the parsed _fit_decl object.
                    # OneDFitEngine.can_handle scans for "FIT_DECLARATION" in the
                    # candidate string; passing the parsed object makes can_handle
                    # always return False and L70 silently falls back to legacy.
                    _l70_engine = _select_adapter(_l70_substrate, python_code or "")
                    _l70_log_path = workspace_dir / "fit_engine_dispatch.jsonl"
                    try:
                        _l70_log_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(_l70_log_path, "a", encoding="utf-8") as _l70_lf:
                            _l70_lf.write(json.dumps({
                                "iter": i + 1,
                                "cage_meta_class": (rubric_data.get("cage_meta") or {}).get("class"),
                                "selected_adapter": type(_l70_engine).__name__ if _l70_engine else "None",
                                "authoritative": _l70_engine is not None,
                            }) + "\n")
                    except Exception:
                        pass  # telemetry never blocks

                    if _l70_engine is not None:
                        _fit_result = _l70_engine.fit(
                            _fit_decl, evidence_text,
                            required_dimensionality=_fit_dimensionality,
                            expression_grammar=_fit_expression_grammar,
                            score_mode=_fit_score_mode,
                            n_starts=_n_starts,
                            gate_threshold=_gate_thr_for_fit,
                        )
                    else:
                        # Safety-net fallback for substrate classes without
                        # a registered adapter (e.g. closed_form_constant,
                        # proof_target). Remove once coverage is universal.
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
                            # Bug #37 fix (2026-04-25 night): same gate-time
                            # primitive injection for the legacy 1D path —
                            # if the mutator wrote `where(...)` or `sigmoid(x,c,w)`
                            # in their FIT_DECLARATION expression, gate harness
                            # needs them at module scope too.
                            from src.ztare.fit.fit_primitive_features import (
                                inject_gate_time_primitives as _inject_prims,
                            )
                            python_code = _inject_prims(python_code)
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

        # ── GP-156 Proposal 3: feature-vector fit primitive ──────
        # Engages when:
        #   1. rubric flag enable_fit_primitive_features is True
        #   2. mutator's test_model.py declares PARAMETRIC_FORM +
        #      PARAMETER_NAMES at module level
        #   3. substrate has features.py + canonical VISIBLE_SET
        # Runs scipy.optimize.minimize multi-start over (features,
        # y_observed) pairs to fit the declared form's free
        # parameters; substitutes fitted MODEL_PARAMS dict back into
        # python_code so the harness uses fitted constants.
        # Verbose telemetry banner — always visible regardless of outcome
        # so the operator can audit Proposal 3 engagement at a glance.
        _ffp_flag = rubric_data.get("enable_fit_primitive_features", False)
        # 2026-04-27 fix: cage_meta nesting — same fix as line 3059
        _convention_hom_flag = (
            (rubric_data.get("cage_meta") or {}).get("target_convention_homogeneity")
            or rubric_data.get("target_convention_homogeneity", "")
        )
        print(f"🧮 ─── GP-156 fit_primitive_features dispatch ───")
        print(f"🧮   rubric flag enable_fit_primitive_features: {_ffp_flag}")
        if _convention_hom_flag:
            print(f"🧮   GP-162 target_convention_homogeneity: {_convention_hom_flag}")
        print(f"🧮   python_code present: {python_code is not None} "
              f"({len(python_code) if python_code else 0} chars)")
        if not _ffp_flag:
            print(f"🧮   DECISION: SKIP — rubric flag is False")
        elif python_code is None:
            print(f"🧮   DECISION: SKIP — no python_code from mutator this iter")
        else:
            try:
                from src.ztare.fit.fit_primitive_features import (
                    should_engage as _ffp_should_engage,
                    extract_form_declaration as _ffp_extract,
                    load_visible_from_substrate as _ffp_load_visible,
                    fit_features as _ffp_fit,
                    substitute_fitted_model_params as _ffp_subst,
                    inject_gate_time_primitives as _ffp_inject_primitives,
                )
                # GP-156 critical fix (2026-04-25): pass python_code to
                # should_engage so it checks the IN-MEMORY mutator
                # submission, NOT test_model.py on disk.
                _eng_ok, _eng_reason = _ffp_should_engage(
                    PROJECT_DIR, python_code_override=python_code
                )
                print(f"🧮   should_engage: {_eng_ok}  reason={_eng_reason}")
                if not _eng_ok:
                    print(f"🧮   DECISION: SKIP — predicate False")
                else:
                    _decl = _ffp_extract(python_code)
                    if _decl is None:
                        print(f"🧮   extract_form_declaration: None")
                        print(f"🧮   DECISION: SKIP — submission did not declare "
                              f"both PARAMETRIC_FORM (str) AND PARAMETER_NAMES (list)")
                    else:
                        # GP-156 Bug #5 fix: extract_form_declaration now
                        # returns 3-tuple including optional INIT_RANGE.
                        _form, _names, _init_range = _decl
                        print(f"🧮   PARAMETRIC_FORM = {_form[:120]!r}{'…' if len(_form)>120 else ''}")
                        print(f"🧮   PARAMETER_NAMES = {_names}")
                        if _init_range:
                            print(f"🧮   INIT_RANGE (mutator-declared) = {_init_range}")
                        else:
                            print(f"🧮   INIT_RANGE = default (-2.0, 2.0); auto-escalation enabled")
                        _vis, _vis_err = _ffp_load_visible(PROJECT_DIR)
                        print(f"🧮   load_visible_from_substrate: "
                              f"{'OK ' + str(len(_vis)) + ' rows' if _vis else 'FAILED — ' + str(_vis_err)}")
                        if not _vis:
                            print(f"🧮   DECISION: SKIP — visible data unavailable")
                        else:
                            _ffp_n_starts = 5 if stagnation_count >= 3 else 3
                            _ffp_k_max = int(rubric_data.get("fit_primitive_features_k_max", 8))
                            print(f"🧮   ENGAGING scipy.optimize: n_starts={_ffp_n_starts}, "
                                  f"k_law_max={_ffp_k_max}, parameter count={len(_names)}")
                            # Bug #38: sparse-indicator hard reject configurables
                            _ffp_sparse_min = int(rubric_data.get("sparse_indicator_min_rows", 3))
                            _ffp_sparse_disable = bool(rubric_data.get("disable_sparse_indicator_reject", False))
                            # F6 fix (2026-04-26): relative-residual fit mode for
                            # multi-decade y substrates. Rubric flag fit_relative_residuals
                            # divides each residual by |y_obs| before squaring,
                            # weighting low-y rows equally with high-y. Default
                            # False to preserve compatibility on existing substrates.
                            _ffp_relative = bool(rubric_data.get("fit_relative_residuals", False))
                            # GP-164 wMDL (2026-04-25 night): weighted-χ² fit
                            # for heteroscedastic substrates that expose
                            # per-row σ in the feature dict (e.g. gp163d's
                            # `errV_frac`). Rubric flags:
                            #   fit_weighted_residuals: bool (default False)
                            #   fit_sigma_key: str (default "sigma")
                            # Backward-compat: weighted=False preserves
                            # existing behavior.
                            _ffp_weighted = bool(rubric_data.get("fit_weighted_residuals", False))
                            _ffp_sigma_key = str(rubric_data.get("fit_sigma_key", "sigma"))
                            if _ffp_weighted:
                                print(
                                    f"🧮   weighted χ² ENABLED: σ key='{_ffp_sigma_key}' "
                                    f"(BIC = χ² + K·log N; σ=1 fallback per-row when key missing)"
                                )
                            _ffp_result = _ffp_fit(
                                _form, _names, _vis,
                                n_starts=_ffp_n_starts,
                                k_law_max=_ffp_k_max,
                                init_range=_init_range if _init_range else (-2.0, 2.0),
                                sparse_indicator_min_rows=_ffp_sparse_min,
                                disable_sparse_indicator_reject=_ffp_sparse_disable,
                                relative_residuals=_ffp_relative,
                                weighted_residuals=_ffp_weighted,
                                sigma_key=_ffp_sigma_key,
                            )
                            if _ffp_result.success:
                                # P3 fix (deep audit, 2026-04-25): use %g
                                # not %f so residuals at scale ~1e-11 don't
                                # round to "0.00000". gp163d's c=1.33e-15
                                # fit displayed as max|res|=0.00000 because
                                # %.5f rounded ~1e-11 to zero, masking a
                                # catastrophic fit as "FIT SUCCESS".
                                print(
                                    f"🧮   ✅ FIT SUCCESS: max|res|={_ffp_result.max_abs_residual:.5g}, "
                                    f"mean|res|={_ffp_result.mean_abs_residual:.5g}, "
                                    f"converged={_ffp_result.n_starts_converged}/"
                                    f"{_ffp_result.n_starts_attempted} "
                                    f"({_ffp_result.convergence_classification})"
                                )
                                print(f"🧮   FITTED PARAMS: {_ffp_result.fitted_params}")
                                # GP-156 v2 BIC telemetry (2026-04-25)
                                print(
                                    f"🧮   BIC: {_ffp_result.bic:.3f} (K={_ffp_result.k_params}, "
                                    f"N={_ffp_result.n_fit_rows}, σ̂²={_ffp_result.sigma_sq:.5g}) — "
                                    f"per GP-152 framer spec v2.0; lower BIC = better-justified K"
                                )
                                # Bug #31 (2026-04-25 evening): residual-feedback loop closure.
                                # Print the categorical-residual diagnostic so the operator + judge
                                # see WHICH categories drag the fit. Mutator sees this in next prompt.
                                if _ffp_result.residual_diagnostic:
                                    for _diag_line in _ffp_result.residual_diagnostic.splitlines():
                                        print(f"🧮   {_diag_line}")
                                # GP-156 Bug #26 (2026-04-25): pathology + sparsity telemetry
                                if _ffp_result.pathological:
                                    print(
                                        f"🧮   ⚠️  PATHOLOGICAL FIT: {_ffp_result.pathology_reason}"
                                    )
                                if _ffp_result.feature_value_counts:
                                    _sparse = []
                                    for fk, vc in _ffp_result.feature_value_counts.items():
                                        for v, c in vc.items():
                                            if c < 3:
                                                _sparse.append(f"{fk}='{v}' (n={c})")
                                    if _sparse:
                                        print(
                                            f"🧮   ⚠️  SPARSE CATEGORIES (<3 rows): {', '.join(_sparse[:6])}"
                                            f"{' …' if len(_sparse) > 6 else ''}"
                                        )

                                # GP-166 Fix C (2026-04-25 night): pathology
                                # ENFORCEMENT. The detector caught the
                                # k_m=-1.2M blow-up but then the catastrophic
                                # params got substituted into MODEL_PARAMS and
                                # propagated to the gate harness, causing
                                # underflow on out-of-class predictions and
                                # farther-tail blow-up. Operator override:
                                # `disable_pathology_substitute_block=True` to
                                # restore old (substitute-anyway) behavior.
                                _ffp_block_substitute = (
                                    _ffp_result.pathological
                                    and not bool(rubric_data.get("disable_pathology_substitute_block", False))
                                )
                                if _ffp_block_substitute:
                                    # Replace catastrophic values with safe
                                    # midpoint of declared INIT_RANGE so the
                                    # form remains evaluable but produces
                                    # bounded, non-blow-up output. The
                                    # mutator briefing surfaces the rejection
                                    # so iter+1 sees the structural feedback.
                                    _ffp_safe_params: dict[str, float] = {}
                                    _ffp_extreme = set(_ffp_result.extreme_params.keys())
                                    for _pname, _pval in _ffp_result.fitted_params.items():
                                        if _pname in _ffp_extreme:
                                            # Pick midpoint of declared range, or 0.0 fallback
                                            _r = (_init_range or {}).get(_pname, (-1.0, 1.0)) if isinstance(_init_range, dict) else _init_range
                                            try:
                                                _mid = (float(_r[0]) + float(_r[1])) / 2.0
                                            except Exception:
                                                _mid = 0.0
                                            _ffp_safe_params[_pname] = _mid
                                        else:
                                            _ffp_safe_params[_pname] = _pval
                                    print(
                                        f"🧮   🛑 PATHOLOGY ENFORCEMENT: rejecting catastrophic "
                                        f"params {dict((k, _ffp_result.fitted_params[k]) for k in _ffp_extreme)} → "
                                        f"replaced with init-range midpoints "
                                        f"{dict((k, _ffp_safe_params[k]) for k in _ffp_extreme)}. "
                                        f"Form remains evaluable; mutator must restructure to bound "
                                        f"these params with visible-class data."
                                    )
                                    # Persist the original fitted vs substituted
                                    # so the briefing provider can show both.
                                    _ffp_result_safe_params = dict(_ffp_safe_params)
                                    python_code = _ffp_subst(python_code, _ffp_safe_params)
                                else:
                                    _ffp_result_safe_params = dict(_ffp_result.fitted_params)
                                    python_code = _ffp_subst(python_code, _ffp_result.fitted_params)
                                # Bug #37 fix: ensure where/sigmoid/erf are
                                # in module scope at gate-harness import time.
                                python_code = _ffp_inject_primitives(python_code)
                                (workspace_dir / "fit_features_result.json").write_text(
                                    json.dumps({
                                        "success": True,
                                        "fitted_params": _ffp_result.fitted_params,
                                        "substituted_params": _ffp_result_safe_params,
                                        "pathology_substitute_blocked": bool(_ffp_block_substitute),
                                        "max_abs_residual": _ffp_result.max_abs_residual,
                                        "mean_abs_residual": _ffp_result.mean_abs_residual,
                                        "n_starts_converged": _ffp_result.n_starts_converged,
                                        "n_starts_attempted": _ffp_result.n_starts_attempted,
                                        "classification": _ffp_result.convergence_classification,
                                        "bic": _ffp_result.bic,
                                        "sigma_sq": _ffp_result.sigma_sq,
                                        "n_fit_rows": _ffp_result.n_fit_rows,
                                        "k_params": _ffp_result.k_params,
                                        "pathological": _ffp_result.pathological,
                                        "pathology_reason": _ffp_result.pathology_reason,
                                        "extreme_params": _ffp_result.extreme_params,
                                        "feature_value_counts": _ffp_result.feature_value_counts,
                                        # Bug #31 residual feedback (2026-04-25 evening)
                                        "residual_by_category": _ffp_result.residual_by_category,
                                        "residual_diagnostic": _ffp_result.residual_diagnostic,
                                        "form": _form,
                                        "parameter_names": _names,
                                    }, indent=2)
                                )
                                print(f"🧮   wrote fit_features_result.json (+ MODEL_PARAMS substituted)")

                                # ── GP-157 §3a backport (Task #151): R13/R14/R15 POST_FIT dispatch ──
                                # noise_profile residual classifier + substrate_critic
                                # per-iter refresh + ANALOGY cross-domain query, all
                                # routed through the Cage. Replaces three legacy direct-
                                # wired if-blocks. The dispatcher's candidate context
                                # carries fitted_form / fitted_params / fit_result_json
                                # / visible_pairs so each adapter can compute residuals
                                # without re-loading from disk. Behavior preserved
                                # verbatim by adapter contracts.
                                try:
                                    from src.ztare.orchestrator.post_fit_dispatch import (
                                        dispatch_post_fit_cage as _dispatch_post_fit,
                                    )
                                    _post_fit_fit_json = {
                                        "form": _form,
                                        "fitted_params": _ffp_result.fitted_params,
                                        "success": bool(_ffp_result.success),
                                        "pathological": bool(getattr(_ffp_result, "pathological", False)),
                                    }
                                    _post_fit_verdict = _dispatch_post_fit(
                                        cage_runtime=_v5_runtime,
                                        rubric_data=rubric_data,
                                        project_dir=Path(PROJECT_DIR),
                                        workspace_dir=workspace_dir,
                                        iter_index=i,
                                        visible_pairs=_vis,
                                        fitted_form=_form,
                                        fitted_params=_ffp_result.fitted_params,
                                        fit_result_json=_post_fit_fit_json,
                                        stagnation_count=stagnation_count,
                                        mutator_model_id=str(MUTATOR_MODEL_ID),
                                        runtime=RUNTIME,
                                        project_name=str(args.project),
                                    )
                                    for _ln in _post_fit_verdict.log_lines:
                                        print(_ln)
                                except ImportError:
                                    pass
                                except Exception as _pf2_exc:
                                    print(f"🦴 POST_FIT Cage dispatch error (non-fatal): {_pf2_exc}")

                                # ── GP-152/GP-164 N-D FRAMER hook (2026-04-26) ──
                                # The 1D framer (autoresearch_loop:5038) runs only
                                # for substrates using the 1D fit_primitive path.
                                # N-D feature-dict substrates (gp154/155/156/158/
                                # 163d) have been silently bypassed since v2.0
                                # shipped — `enable_framer=true` had no effect on
                                # them. This hook closes the gap: run the framer
                                # on a 1D projection of visible data along a
                                # primary feature key, write framing_report.json
                                # in OBSERVE mode (telemetry only, no data-flow
                                # modification), and let a BriefingProvider
                                # surface the recommendation to the mutator.
                                #
                                # Active integration (mutator applies the framer's
                                # recommended h_in/h_out to PARAMETRIC_FORM) is
                                # mediated through the briefing layer so the
                                # holdout gate validates the result. Same
                                # separation-of-concerns as 1D.
                                if rubric_data.get("enable_framer", False):
                                    try:
                                        from src.ztare.framer.framer_nd import frame_nd as _fr_nd
                                        _fr_primary = rubric_data.get("framer_primary_feature_key")
                                        # GP-164 wMDL: when the substrate is
                                        # heteroscedastic and the operator
                                        # opted into weighted χ² fitting,
                                        # mirror that into framer_sigma_provided
                                        # so the framer's heteroscedasticity
                                        # auto-disable does not trigger on
                                        # signal that the weighted solver
                                        # already accounts for. Operator can
                                        # override explicitly via
                                        # `framer_sigma_provided` in the rubric.
                                        _fr_rubric = dict(rubric_data)
                                        if (
                                            "framer_sigma_provided" not in _fr_rubric
                                            and _fr_rubric.get("fit_weighted_residuals", False)
                                        ):
                                            _fr_rubric["framer_sigma_provided"] = True
                                        _fr_report, _fr_key = _fr_nd(
                                            _vis,
                                            primary_feature_key=_fr_primary,
                                            meta=_fr_rubric.get("framer_meta") or {},
                                            rubric_data=_fr_rubric,
                                        )
                                        (workspace_dir / "framing_report.json").write_text(
                                            json.dumps(_fr_report, indent=2, default=str)
                                        )
                                        if _fr_report.get("framer_engaged"):
                                            print(
                                                f"  🪞 GP-152 N-D Framer [OBSERVE]: "
                                                f"primary={_fr_key} "
                                                f"h_in={_fr_report.get('h_in')} "
                                                f"h_out={_fr_report.get('h_out')} "
                                                f"MDL_gain={_fr_report.get('MDL_gain_bits', 0):.1f} bits"
                                            )
                                        else:
                                            print(
                                                f"  🪞 GP-152 N-D Framer [DISABLED]: "
                                                f"reason={_fr_report.get('disabled_reason')}"
                                            )
                                    except Exception as _fr_exc:
                                        print(f"  🪞 GP-152 N-D Framer error (non-fatal): {_fr_exc}")
                                # ── end N-D Framer hook ──

                                # GP-164 ANALOGY (R15) is now dispatched as part of
                                # the POST_FIT Cage call above (post_fit_dispatch.py).
                                # The legacy direct-wire block has been removed per
                                # GP-157 §3a backport (Task #151).

                            if not _ffp_result.success:
                                print(f"🧮   ❌ FIT FAILURE: {_ffp_result.error_message}")
                                (workspace_dir / "fit_features_result.json").write_text(
                                    json.dumps({
                                        "success": False,
                                        "error_message": _ffp_result.error_message,
                                        "form": _form,
                                        "parameter_names": _names,
                                    }, indent=2)
                                )
                                # Bug #29 (2026-04-25 evening): when fit fails,
                                # the mutator's I_model body uses params['x']
                                # (bracket access) and MODEL_PARAMS stays {}.
                                # At gate time → KeyError on every row → silent
                                # 100% crash → harness defect (Bug #16 floor).
                                # Replace I_model with a LOUD-FAIL stub so the
                                # harness fails with a SHARP diagnostic naming
                                # the fit failure reason, not a vague KeyError.
                                # GP-157 Bug #34 (2026-04-25 night): the previous
                                # stub-writer corrupted test_model.py whenever
                                # `error_message` was multi-line — only the FIRST
                                # line was `#`-prefixed in the comment header, and
                                # the embedded single-quoted string literal can't
                                # carry raw newlines. Both broke gate_harness
                                # at module-import with IndentationError. Two
                                # fixes: (a) `#`-prefix every line of the comment
                                # header, (b) use `repr()` for the embedded string
                                # literal so newlines/quotes/escapes are handled
                                # correctly by Python's own quoting machinery.
                                # Truncation budget bumped 300→1500 to match the
                                # Bug #32 next-iter prompt budget — the mutator
                                # already sees up to 1500 chars of diagnostic in
                                # its prompt; the stub error should match so the
                                # harness-time RuntimeError doesn't hide context.
                                _err_full = _ffp_result.error_message or "fit failed"
                                _stub_msg = _err_full if len(_err_full) <= 1500 else _err_full[:1500] + "...[truncated]"
                                _stub_msg_commented = "\n".join(
                                    "# " + ln for ln in _stub_msg.splitlines()
                                ) or "# (no message)"
                                _stub_msg_repr = repr(
                                    "fit_features rejected the submission: "
                                    + _stub_msg
                                    + ". MODEL_PARAMS could not be filled; the "
                                    "contract was not honored. See workspace/"
                                    "fit_features_result.json for full diagnostic. "
                                    "Fix PARAMETRIC_FORM grammar before resubmission."
                                )
                                _loud_fail_stub = (
                                    f"# GP-156 Bug #29 loud-fail stub: fit_features rejected this submission.\n"
                                    f"# Reason (multi-line, every line `#`-prefixed):\n"
                                    f"{_stub_msg_commented}\n"
                                    f"def I_model(features, params=None):\n"
                                    f"    raise RuntimeError({_stub_msg_repr})\n"
                                    f"# Canonical aliases\n"
                                    f"f = I_model\n"
                                    f"model = I_model\n"
                                )
                                # Overwrite python_code so the downstream
                                # write_file lands the stub, not the broken
                                # mutator submission with empty MODEL_PARAMS.
                                python_code = _loud_fail_stub
                                print(
                                    f"🧮   🚨 wrote LOUD-FAIL I_model stub (Bug #29) — "
                                    f"harness will get a clear RuntimeError instead "
                                    f"of silent KeyError on params['x']."
                                )
            except Exception as _ffp_exc:
                import traceback as _ffp_tb
                print(f"🧮   ⚠️ DISPATCH EXCEPTION (non-fatal): {type(_ffp_exc).__name__}: {_ffp_exc}")
                print(f"🧮   traceback: {_ffp_tb.format_exc(limit=3)}")
        print(f"🧮 ─── end fit_primitive_features dispatch ───")
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
        yield_decision = evaluate_information_yield(
            iteration_history,
            underidentified_after=args.underidentified_after,
            class_novelty_mode=(_stagnation_trigger_mode() == "new_class"),
        )
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
        yield_decision = evaluate_information_yield(
            iteration_history,
            underidentified_after=args.underidentified_after,
            class_novelty_mode=(_stagnation_trigger_mode() == "new_class"),
        )
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
        """Guarantee that test_model.py exposes ``f``, ``model``, AND ``I_model``
        as top-level names, regardless of which path wrote the file.

        GP-157 v5.0 fix (2026-04-25 night): added I_model as a canonical name
        per Contract C/B requirements. The deterministic-fit-primitive build
        path writes `def f(x)` (legacy convention); gate_harness.py (post-fix)
        imports `I_model`; mutator-prompt Contract C tells mutator to write
        `def I_model(...)`. All three must resolve to the same callable.

        Rules (applied in order):
        1. Find the canonical callable: prefer existing I_model > f > model >
           first non-test top-level def.
        2. Add aliases for all three names {f, model, I_model} not already defined.
        3. On SyntaxError → return code unchanged (don't make it worse).
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
        has_I_model = "I_model" in top_level_names

        if has_f and has_model and has_I_model:
            return code  # already canonical

        # Find the source-of-truth callable: prefer existing canonical name
        # in priority order (I_model first per Contract C/B), else first
        # non-test top-level def.
        canonical_name: str | None = None
        for preferred in ("I_model", "f", "model"):
            if preferred in top_level_names:
                canonical_name = preferred
                break
        if canonical_name is None:
            _skip = ("test", "assert", "check", "verify", "_")
            for node in tree.body:
                if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    if not any(node.name.startswith(p) for p in _skip):
                        canonical_name = node.name
                        break

        if canonical_name is None:
            return code  # nothing to alias against

        suffix_lines = [
            "",
            "# Canonical aliases — gate harnesses may call f(), model(), or I_model()",
        ]
        if not has_f and canonical_name != "f":
            suffix_lines.append(f"f = {canonical_name}")
        if not has_model and canonical_name != "model":
            suffix_lines.append(f"model = {canonical_name}")
        if not has_I_model and canonical_name != "I_model":
            suffix_lines.append(f"I_model = {canonical_name}")
        if len(suffix_lines) <= 2:  # only the header lines, no actual aliases
            return code
        return code.rstrip() + "\n" + "\n".join(suffix_lines) + "\n"

    # Layer 3 Mandatory (Odrzywołek Inversion, GP-035 extension):
    # The LLM is a pure topology generator.  test_model.py is ALWAYS built
    # deterministically from fit_declaration + fitted_params when the fit
    # primitive is active.  The LLM never writes def f().
    # When the fit primitive is NOT active (legacy / non-fit substrates),
    # the old LLM-python path runs unchanged.
    # Mutable flag — list so a nested function can set it without nonlocal
    # (this code runs at module scope where nonlocal is a SyntaxError).
    _layer3_built = [False]

    # GP-157 v5.0 defense-in-depth (2026-04-25 night): mirror Cage's
    # OneDFitEngine.can_handle() at this legacy gate. Logic extracted to
    # src/ztare/fit/legacy_engagement_guard.py with regression tests.
    # Surfaced on gp159 nd_features run by parallel agent: legacy 1D
    # primitive's loud-fail stub overwrote authored test_model.py.
    from src.ztare.fit.legacy_engagement_guard import (
        resolve_layer3_stub_target as _resolve_layer3_stub_target,
        should_engage_legacy_1d_fit_primitive as _should_engage_legacy_1d_fit_primitive,
    )
    _fit_primitive_active, _engage_reason = _should_engage_legacy_1d_fit_primitive(
        enable_fit_primitive_flag=bool(rubric_data.get("enable_fit_primitive", False)),
        cage_meta=rubric_data.get("cage_meta"),
    )
    if rubric_data.get("enable_fit_primitive", False) and not _fit_primitive_active:
        print(f"🦴 GP-157 legacy 1D fit primitive: REFUSING engagement — {_engage_reason}")

    if _fit_primitive_active:
        # GP-157 v5.0 defense-in-depth: if the substrate authored its own
        # test_model.py (signaled by features.py existing alongside it),
        # the loud-fail stub MUST go to a sidecar file. Otherwise the run is
        # irrecoverable: VISIBLE_SET, HOLDOUT_SET, custom I_model, gate-harness
        # logic — all destroyed.
        # test_model_path is a string in this scope (see L5104); coerce to Path.
        _stub_target_path, _stub_clobbers_authored = _resolve_layer3_stub_target(Path(test_model_path))

        def _write_layer3_stub(reason: str) -> None:
            """Write a loud-fail stub — every path through Layer 3 mandatory
            must either build a working f() or write this stub.  No silent
            fallback to LLM python is permitted.

            GP-157 fix: when the substrate authored test_model.py (features.py
            exists), the stub goes to _fit_stub.py instead. The substrate's
            test_model.py is never overwritten."""
            _stub = (
                f"import math\n\n"
                f"# Layer 3 Mandatory: loud-fail stub — {reason}\n"
                f"def f(*args):\n"
                f"    raise RuntimeError("
                f"'Layer 3 Mandatory: {reason} — no callable built')\n"
            )
            write_file(_stub_target_path, _ensure_canonical_model_aliases(_stub))
            # GP-157 fix 2026-04-25 night: when stub goes to sidecar
            # (_fit_stub.py), the apparatus MUST still let the python_code
            # path write test_model.py from the mutator's submission.
            # Setting _layer3_built[0]=True when the stub diverted to a
            # sidecar caused test_model.py to retain the substrate
            # placeholder (NaN-returning) and the gate harness then saw
            # NaN for every visible row → score 0. Only mark layer3 built
            # when the stub actually wrote test_model.py (legacy mode).
            if not _stub_clobbers_authored:
                _layer3_built[0] = True
            _where = "_fit_stub.py (authored substrate preserved; mutator python_code still flows to test_model.py)" if _stub_clobbers_authored else "test_model.py"
            print(f"🔧 Layer 3 Mandatory: STUB (loud-fail) → {_where} — {reason}")

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
                # expression may reference (e.g. eml for eml_only grammar;
                # number-theoretic primitives for py_exec grammar).
                _grammar = str(rubric_data.get("fit_expression_grammar", "") or "").strip().lower()
                _helpers = ""
                if _grammar == "eml_only" or "eml(" in _fit_decl.expression:
                    _helpers = "\ndef eml(x, y):\n    return math.exp(x) - math.log(y)\n\n"
                # GP-135 (2026-04-23): py_exec sandbox primitives live in
                # _PY_EXEC_BUILTINS at fit-eval time but are NOT in scope when
                # the installed test_model.py is imported by the gate harness.
                # Emit stdlib-only trial-division copies matching
                # src/ztare/fit/fit_primitive.py so test_model.py is portable
                # and does not require sympy. The bounded-discriminator suite
                # may still import sympy via rubric's runner_allowed_imports.
                if _grammar == "py_exec" or any(
                    name + "(" in _fit_decl.expression
                    for name in (
                        "isprime", "is_prime", "factorint", "primefactors",
                        "divisors", "gcd", "prime_vector", "is_coprime",
                    )
                ):
                    _helpers = _helpers + (
                        "\n# py_exec sandbox primitives (stdlib-only; match _PY_EXEC_BUILTINS)\n"
                        "def isprime(n):\n"
                        "    n = int(n)\n"
                        "    if n < 2: return False\n"
                        "    if n < 4: return True\n"
                        "    if n % 2 == 0: return False\n"
                        "    r = int(n ** 0.5)\n"
                        "    i = 3\n"
                        "    while i <= r:\n"
                        "        if n % i == 0: return False\n"
                        "        i += 2\n"
                        "    return True\n"
                        "is_prime = isprime\n"
                        "def factorint(n):\n"
                        "    n = int(n)\n"
                        "    if n < 2: return {}\n"
                        "    factors = {}\n"
                        "    while n % 2 == 0:\n"
                        "        factors[2] = factors.get(2, 0) + 1\n"
                        "        n //= 2\n"
                        "    i = 3\n"
                        "    while i * i <= n:\n"
                        "        while n % i == 0:\n"
                        "            factors[i] = factors.get(i, 0) + 1\n"
                        "            n //= i\n"
                        "        i += 2\n"
                        "    if n > 1: factors[n] = factors.get(n, 0) + 1\n"
                        "    return factors\n"
                        "def primefactors(n):\n"
                        "    return sorted(factorint(n).keys())\n"
                        "def divisors(n):\n"
                        "    n = int(n)\n"
                        "    if n < 1: return []\n"
                        "    ds = []\n"
                        "    i = 1\n"
                        "    while i * i <= n:\n"
                        "        if n % i == 0:\n"
                        "            ds.append(i)\n"
                        "            if i != n // i: ds.append(n // i)\n"
                        "        i += 1\n"
                        "    return sorted(ds)\n"
                        "def gcd(a, b):\n"
                        "    a, b = abs(int(a)), abs(int(b))\n"
                        "    while b: a, b = b, a % b\n"
                        "    return a\n"
                        "def prime_vector(n):\n"
                        "    return sorted(factorint(n).items())\n"
                        "def is_coprime(a, b):\n"
                        "    return gcd(a, b) == 1\n\n"
                    )
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

    # GP-157 v5.0 — per-iter mutator submission snapshot (diagnostic).
    # The apparatus may revert test_model.py to baseline on score=0,
    # erasing the mutator's actual submission and leaving us blind on
    # postmortem. Snapshot the python_code + clean_thesis to
    # workspace/submissions/iter_<N>_<utc>.{py,md} so failed iters are
    # always inspectable. No-op when MUTATOR_SUBMISSION_SNAPSHOT=0.
    if os.environ.get("MUTATOR_SUBMISSION_SNAPSHOT", "1") != "0":
        try:
            _submissions_dir = workspace_dir / "submissions"
            _submissions_dir.mkdir(parents=True, exist_ok=True)
            _snap_stem = f"iter_{i + 1:03d}_{iteration_start_utc.replace(':', '').replace('-', '')}"
            (_submissions_dir / f"{_snap_stem}.py").write_text(
                _ensure_canonical_model_aliases(python_code or ""),
                encoding="utf-8",
            )
            if clean_thesis:
                (_submissions_dir / f"{_snap_stem}.md").write_text(clean_thesis, encoding="utf-8")
        except Exception as _snap_err:  # noqa: BLE001
            print(f"📸 mutator submission snapshot error (non-fatal): {_snap_err}")

    # GP-157 v5.0 — substrate-contract adherence telemetry.
    # Logs whether the emitted test_model.py honors the active contract's
    # shape (Contract A/B/C). Operator concern: hint may be ignored amid
    # ~15 prompt sections — empirical signal lives in
    # workspace/contract_violations.jsonl per iter.
    try:
        from src.ztare.orchestrator.contract_adherence import (
            emit_adherence as _emit_adherence,
            format_adherence_summary as _format_adherence_summary,
        )
        # test_model_path is a string in this scope (see L5104); coerce to Path.
        _adherence_path = Path(test_model_path)
        if _adherence_path.exists():
            _adherence_text = _adherence_path.read_text(encoding="utf-8", errors="ignore")
            _adherence_report = _emit_adherence(ctx, _adherence_text)
            _adherence_summary = _format_adherence_summary(_adherence_report)
            if _adherence_summary is not None:
                print(_adherence_summary)
    except Exception as _adherence_err:  # noqa: BLE001
        print(f"📋 contract-adherence telemetry error (non-fatal): {_adherence_err}")

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

            # GP-157 Cage post-harness dispatch (Phase 4g Torvalds split — task #65).
            # All Cage-routed post-harness gates (R10, R11 today; GP-170 symbolic
            # logic cage and GP-168 forced-reframe when implemented) dispatch
            # through a single entry point in the orchestrator. New gates register
            # in src/ztare/orchestrator/post_harness_dispatch.py — autoresearch_loop
            # stays a coordinator, no per-gate if-block accretion.
            try:
                from src.ztare.orchestrator.post_harness_dispatch import (
                    dispatch_post_harness_cage as _dispatch_post_harness,
                    apply_verdict_to_eval as _apply_verdict,
                )
                _verdict = _dispatch_post_harness(
                    project_dir=Path(PROJECT_DIR),
                    rubric_data=rubric_data,
                    iter_index=i + 1,
                )
                for _ln in _verdict.log_lines:
                    print(_ln)
                if _verdict.error:
                    print(f"🦴 Post-harness dispatch note: {_verdict.error}")
                _apply_verdict(_verdict, new_eval)
            except ImportError:
                pass
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
        _refresh_latest_evidence_gaps_from_eval(new_eval, artifact_role="latest")
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

        # Bug #48 (2026-04-25 night, gp160 cross-family run hit this):
        # if the judge response is malformed (e.g., evidence_gap fields
        # leaked to top-level instead of nested under evidence_gaps[]),
        # new_eval may lack "score". Treat missing/None as 0 so the iter
        # records as a non-improving submission rather than crashing the
        # entire run. The FINAL VERDICT print line is unaffected; this
        # only protects the candidate-selection path.
        _candidate_score = new_eval.get("score")
        if _candidate_score is None:
            print(
                "⚠️ Judge response missing 'score' field (likely malformed "
                "judge JSON). Treating as score=0 for candidate selection. "
                "test_model.py and holdout gate verdict are preserved; "
                "see latest_eval_results.json for the full malformed payload."
            )
            _candidate_score = 0
        selection_record = evaluate_candidate_selection(
            candidate_score=_candidate_score,
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
        # 2026-04-27 (WAR-T2): persist parametric_form, raw_judge_score,
        # score_cap_applied at write time so briefing providers do not have
        # to backfill via lossy regex from submission files. The backfill
        # path was the load-bearing bug behind the gp163d v3 phantom-REFRAME
        # cascade in run_id 1777250273.
        try:
            _eval_hist_path = workspace_dir / "eval_history.jsonl"
            _sc = new_eval.get("score_contract") or {}
            _dcg = _sc.get("deterministic_charter_gates", {}).get("results", {})
            _gate_verdicts = {g: r.get("passed", None) for g, r in _dcg.items()} if isinstance(_dcg, dict) else {}
            _form_str = ""
            try:
                from src.ztare.orchestrator.forced_reframe import (
                    extract_parametric_form_from_source as _extract_form,
                )
                _form_str = _extract_form(python_code or "") or ""
            except Exception:
                _form_str = ""
            _cap_meta = new_eval.get("score_cap_applied") or {}
            _raw_judge_score = _cap_meta.get("original_judge_score")
            _eval_hist_path.open("a").write(
                json.dumps({
                    "iteration": i + 1,
                    "score": new_eval.get("score"),
                    "raw_judge_score": _raw_judge_score,
                    "score_cap_reason": _cap_meta.get("reason") if isinstance(_cap_meta, dict) else None,
                    "parametric_form": _form_str,
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

        # WAR-T3 (2026-04-27): Two-tier promotion. Capped score collapses
        # raw=100 down to 50, hiding breakthrough behind plateau. Promote on:
        #   (a) capped strict improvement (existing behavior), OR
        #   (b) capped equal AND raw judge score strictly improves AND
        #       gate failure count does not regress (the latent gradient).
        # See gp163d run 1777250273 iter 8 (raw 100 capped 50, lost in iter 9).
        _new_cap_meta = new_eval.get("score_cap_applied") or {}
        _new_raw_score = (
            _new_cap_meta.get("original_judge_score")
            if isinstance(_new_cap_meta, dict) else None
        )
        if _new_raw_score is None:
            _new_raw_score = new_eval["score"]
        _new_gv = ((new_eval.get("score_contract") or {})
                   .get("deterministic_charter_gates", {})
                   .get("results", {})) or {}
        # WAR-T3 hotfix (2026-04-27): `results` can be a dict {gate_id: {...}}
        # OR a list [{name, passed, ...}, ...] depending on substrate. Handle
        # both shapes; fall through to 0 for any other type.
        if isinstance(_new_gv, dict):
            _new_gate_failure_count = sum(
                1 for _g, _r in _new_gv.items()
                if isinstance(_r, dict) and _r.get("passed") is False
            )
        elif isinstance(_new_gv, list):
            _new_gate_failure_count = sum(
                1 for _r in _new_gv
                if isinstance(_r, dict) and _r.get("passed") is False
            )
        else:
            _new_gate_failure_count = 0
        _capped_strict = new_eval["score"] > best_score
        _capped_equal_raw_better = (
            new_eval["score"] == best_score
            and _new_raw_score > best_raw_score
            and _new_gate_failure_count <= best_gate_failure_count
        )
        _candidate_improved = _capped_strict or _capped_equal_raw_better
        if _capped_equal_raw_better and not _capped_strict:
            print(
                f"🎯 LATENT-GRADIENT promotion: capped {best_score}→{new_eval['score']} "
                f"(unchanged) but raw {best_raw_score}→{_new_raw_score} (+{_new_raw_score - best_raw_score}) "
                f"with gate failures {best_gate_failure_count}→{_new_gate_failure_count}. "
                f"Champion promoted on the raw-score signal hidden behind the per-class cap."
            )
        signal = IterationSignal(
            iteration_index=i + 1,
            score=new_eval["score"],
            weakest_point=new_eval["weakest_point"],
            score_improved=_candidate_improved,
            catastrophic_failure=_is_catastrophic_failure(new_eval["score"], best_score),
            falsification_mode=rubric_falsification_mode,
            claim_delta_type=mutation_declaration.claim_delta_type.value if mutation_declaration is not None else "",
            committee_digest=current_committee_digest,
            prior_committee_digest=iteration_prior_committee_digest,
            # Only count axioms as novelty when the champion is promoted.
            # Reverted iterations discard their axioms — counting them as
            # novelty prevents stagnation from ever accumulating.
            verified_axioms_added=len(new_eval.get("verified_axioms", [])) if _candidate_improved else 0,
        )
        iteration_history.append(signal)
        yield_decision, _ = _evaluate_post_eval_loop_control(
            workspace_dir,
            signal=signal,
        )

        if _candidate_improved:
            print(f"✅ IMPROVEMENT: {best_score} -> {new_eval['score']}")
            print(f"Targeting New Weakest Link: {new_eval['weakest_point']}")
            if rubric_data.get("enable_component_c", False):
                try:
                    reset_stagnation_on_holdout_pass(workspace_dir)
                except Exception as _cc_exc:
                    print(f"🔧 GP-074 Component C reset: error — {_cc_exc}")
            best_score = new_eval["score"]
            # WAR-T3: track raw + gate-failure across champions so the
            # latent-gradient promotion check has live state to compare.
            best_raw_score = _new_raw_score
            best_gate_failure_count = _new_gate_failure_count
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

            # GP-119: Post-champion Inverter (in-loop promotion path)
            if best_score >= 50:
                try:
                    from src.ztare.validator.inverter_agent import run_inverter
                    run_inverter(
                        project_dir=Path(PROJECT_DIR),
                        champion_thesis=new_content,
                        champion_score=best_score,
                        champion_weakest_point=best_weakest_point,
                        evidence_summary=read_file(EVIDENCE_PATH)[:500] if os.path.exists(EVIDENCE_PATH) else "",
                    )
                except Exception as _inv_err:
                    print(f"  🔬🔬🔬 GP-119 Inverter FAILED: {_inv_err}")

            # GP-122: Post-champion Lean proof (in-loop promotion path)
            if best_score >= 70 and rubric_data.get("enable_lean_proof"):
                try:
                    from src.ztare.formal.lean_repl import prove_from_compression
                    print(f"  📐📐📐 GP-122 Lean REPL: attempting proof...")
                    _lean_result = prove_from_compression(
                        project_dir=Path(PROJECT_DIR),
                        model=rubric_data.get("lean_prover_model", "gpt4.1"),
                        max_attempts=3,
                    )
                    if _lean_result.get("proved"):
                        print(f"  📐 ✅ LEAN PROOF VERIFIED in {_lean_result['attempts']} attempts!")
                    else:
                        print(f"  📐 Lean proof not found ({_lean_result.get('attempts', 0)} attempts)")
                except Exception as _lean_err:
                    print(f"  📐📐📐 GP-122 Lean REPL FAILED: {_lean_err}")

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
            # Apply Judge's Veto: Filter out the approved retirements.
            # 2026-04-27 hotfix: handle both string-shaped and dict-shaped axioms.
            if approved_retirements:
                print(
                    f"🗑️ Judge Approved {len(approved_retirements)} Axiom Retirements."
                )
                def _ax_text(ax):
                    if isinstance(ax, dict):
                        return str(
                            ax.get('axiom_id') or ax.get('name')
                            or ax.get('claim') or json.dumps(ax, sort_keys=True)
                        ).lower()
                    return str(ax).lower()
                current_axioms = [
                    ax
                    for ax in current_axioms
                    if not any(
                        ret.lower() in _ax_text(ax) for ret in approved_retirements
                    )
                ]

            if new_axioms:
                print("\n" + "📜" * 20)
                print(f"NEW AXIOMS VERIFIED (ITER {i + 1}):")
                for a in new_axioms:
                    print(f"  • {a}")
                print("📜" * 20 + "\n")

            # --- THE FIX: Clean up duplicates effectively by ignoring backticks/punctuation.
            # 2026-04-27 hotfix: normalize() now handles both string-shaped axioms (legacy
            # judge output: list of axiom-statement strings) AND dict-shaped axioms
            # (operator-curated verified_axioms.json with {axiom_id, name, claim, ...}).
            # Crash before fix: TypeError on `re.sub(..., dict)` when current_axioms came
            # from a dict-shape verified_axioms.json. Iter-1 promotion died here.
            def normalize(text):
                if isinstance(text, dict):
                    # Prefer axiom_id, fall back through name/claim/serialization
                    text = str(
                        text.get('axiom_id')
                        or text.get('name')
                        or text.get('claim')
                        or json.dumps(text, sort_keys=True)
                    )
                elif not isinstance(text, str):
                    text = str(text)
                return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

            updated_axioms = []
            seen_axioms = set()
            for ax in current_axioms + new_axioms:
                norm = normalize(ax)
                if norm not in seen_axioms:
                    seen_axioms.add(norm)
                    updated_axioms.append(ax)

            # 2026-04-27 hotfix: NEVER squash a populated verified_axioms.json
            # to []. The "Hide from test_thesis.py" branch at line 2335-2337
            # removes the file before eval; if no new axioms emerge that iter,
            # the merge produces [] and overwrites operator-curated bridge
            # axioms. Skip the write entirely when both current and new are
            # empty AND a populated file exists from before. Restore from .bak
            # if a populated backup exists.
            try:
                _bak_path = f"{AXIOM_PATH}.bak"
                _has_existing_disk = False
                if os.path.exists(AXIOM_PATH):
                    with open(AXIOM_PATH, "r") as _f_in:
                        _existing = json.load(_f_in)
                    if isinstance(_existing, dict):
                        _has_existing_disk = bool(_existing.get("axioms"))
                    elif isinstance(_existing, list):
                        _has_existing_disk = bool(_existing)
                else:
                    _existing = None
                # If we'd be writing empty list AND a populated backup exists,
                # restore the backup instead of squashing.
                if (not updated_axioms) and os.path.exists(_bak_path):
                    try:
                        with open(_bak_path, "r") as _f_bak:
                            _bak_data = json.load(_f_bak)
                        _bak_populated = (
                            (isinstance(_bak_data, dict) and bool(_bak_data.get("axioms")))
                            or (isinstance(_bak_data, list) and bool(_bak_data))
                        )
                        if _bak_populated:
                            shutil.copy(_bak_path, AXIOM_PATH)
                            print(
                                "🛡️ verified_axioms.json: empty merge would have squashed "
                                "populated backup; restored from .bak instead."
                            )
                            # Skip the regular write — restore is authoritative
                            updated_axioms = None  # type: ignore[assignment]
                    except Exception:
                        pass
                if updated_axioms is not None:
                    if isinstance(_existing, dict):
                        _existing["axioms"] = updated_axioms
                        with open(AXIOM_PATH, "w") as _f_out:
                            json.dump(_existing, _f_out, indent=2)
                    else:
                        with open(AXIOM_PATH, "w") as _f_out:
                            json.dump(updated_axioms, _f_out, indent=2)
            except Exception:
                # Fallback: write flat list (legacy behavior) only if not None
                if updated_axioms is not None:
                    with open(AXIOM_PATH, "w") as _f_out:
                        json.dump(updated_axioms, _f_out, indent=2)

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
                raw_judge_score=_new_raw_score,
                score_cap_reason=(
                    _new_cap_meta.get("reason") if isinstance(_new_cap_meta, dict) else None
                ),
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

            # WAR-T6 (2026-04-27): per-iter EGE trigger. Pre-iter-1 EGE
            # only fires once on a fresh substrate; live-loop knowledge
            # ("class C keeps failing in this specific way") never re-
            # triggered. Now: when a champion promotes near the Newton-
            # step threshold (raw >= 70) and a per-class farther-tail is
            # the binding cap, re-fire EGE so the operator gets fresh
            # literature proposals targeted at the actual binding
            # constraint. Fail-graceful — never blocks the loop.
            if bool(rubric_data.get("enable_evidence_gap_enrichment_proposals", False)):
                try:
                    from src.ztare.orchestrator.evidence_gap_enrichment import (
                        detect_per_iter_ege_trigger as _detect_ege,
                        propose_per_iter_ege as _per_iter_ege,
                    )
                    # build eval_history view from the just-written file
                    _eh_path = workspace_dir / "eval_history.jsonl"
                    _eh_records: list[dict] = []
                    if _eh_path.exists():
                        for _ln in _eh_path.read_text(encoding="utf-8").splitlines():
                            _ln = _ln.strip()
                            if not _ln:
                                continue
                            try:
                                _eh_records.append(json.loads(_ln))
                            except Exception:
                                continue
                    _trigger_ctx = _detect_ege(
                        eval_history=_eh_records,
                        latest_eval=new_eval,
                        iter_index=i + 1,
                    )
                    if _trigger_ctx is not None:
                        _ege_v = _per_iter_ege(
                            project_dir=Path(PROJECT_DIR),
                            trigger_context=_trigger_ctx,
                            iter_index=i + 1,
                            rubric_data=rubric_data,
                            mutator_model_id=MUTATOR_MODEL_ID,
                        )
                        print(
                            f"🧪 EGE per-iter fired ({_trigger_ctx.get('trigger')}): "
                            f"failing_classes={_trigger_ctx.get('failing_classes')} "
                            f"artifact={_ege_v.get('artifact_path')}"
                        )
                except Exception as _per_iter_ege_exc:  # noqa: BLE001
                    print(f"🧪 EGE per-iter error (non-fatal): {_per_iter_ege_exc}")

            # GP-078 Fix B v2: on success, clear the entire seed queue.
            # The winning candidate passed the holdout — no need to test
            # the remaining candidates.
            if _comp_seed_injected:
                _consumed_seed = workspace_dir / "composition_seed.json"
                if _consumed_seed.exists():
                    _consumed_seed.unlink()
                    print("    🧬 Seed queue cleared (candidate promoted to champion)")

            # GP-103 in-loop compression: after champion promotion, check if a
            # simpler form also passes gates. Only fires for science track
            # (enable_fit_primitive) when the champion has many parameters.
            # Modifies test_model.py only; does not touch thesis.md or best_score.
            # The next iteration's _capture_project_state will snapshot the
            # compressed form, and future reverts will restore it.
            if rubric_data.get("enable_fit_primitive", False):
                try:
                    _champion_test = read_file(f"{PROJECT_DIR}/test_model.py")
                    # Count params in current champion (heuristic: count MODEL_PARAMS or assignments)
                    import re as _re_comp
                    _champion_k = len(_re_comp.findall(r'^\s+\w+\s*=\s*[-+]?\d', _champion_test, _re_comp.MULTILINE))
                    if _champion_k >= 3:  # fire on any non-trivial champion; BIC decides
                        from src.ztare.fit.compress_champion import compress_champion as _compress
                        print(f"\n    🔬 GP-103 in-loop compression (champion k={_champion_k})...")
                        _comp_results = _compress(Path(PROJECT_DIR), k_max=_champion_k - 1, verbose=False)
                        _comp_passing = [r for r in _comp_results if r.gates_passed]
                        if _comp_passing:
                            _comp_best = _comp_passing[0]
                            if _comp_best.k < _champion_k:
                                # Install compressed form
                                from src.ztare.fit.compress_champion import _write_test_model as _comp_write
                                # Detect variable from current test_model
                                _var_match = _re_comp.search(r'def f\((\w+)', _champion_test)
                                _comp_var = _var_match.group(1) if _var_match else "n"
                                _comp_write(Path(PROJECT_DIR), _comp_best.expression, _comp_best.params, var_name=_comp_var)
                                print(
                                    f"    🔬 GP-103: compressed {_champion_k}→{_comp_best.k} params"
                                    f" ({_comp_best.name}: {_comp_best.expression[:50]})"
                                    f" BIC={_comp_best.bic:.1f}, all gates pass"
                                )
                            else:
                                print(f"    🔬 GP-103: no simpler gate-passing form found (best k={_comp_best.k})")
                        else:
                            print("    🔬 GP-103: no compressed form passes gates — champion retained")
                except Exception as _comp_exc:
                    print(f"    🔬 GP-103 compression: error — {_comp_exc}")

        else:
            # Task #143: retroactive champion invalidation. If the new iter
            # is evaluated under a tighter gate set than the existing
            # champion (R20-R23 structural anti-pattern flags), and the
            # old champion lacks those telemetry payloads (so we can't
            # know whether it would survive), demote the phantom champion
            # so the new iter can promote on the new gate basis.
            try:
                _sapg_new = new_eval.get("cage_r20_r23", {}) or {}
                if (bool(_sapg_new.get("any_flag")) is False
                        and best_score >= 80
                        and isinstance(current_eval, dict)
                        and "cage_r20_r23" not in (current_eval or {})):
                    print(
                        f"⚖️  Retroactive champion invalidation (task #143): "
                        f"champion (score={best_score}) predates the R20-R23 "
                        f"structural-pattern gate set. Demoting to allow the "
                        f"current gate basis to determine the new champion."
                    )
                    best_score = 0
            except Exception:
                pass
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
                                            from src.ztare.validator.core.information_yield import ShapeDescriptor
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

        # GP-105 M-Form Alignment Audit — fires after PHASE_F (promote or revert).
        # Async: finding written to mform_pending.json; applied at START of next iter.
        # Fail-silent: never raises; loop continues unaffected.
        try:
            _mform_fired = maybe_fire_mform_audit(
                score=float(new_eval.get("score", 0)),
                iteration=i + 1,
                audits_so_far=_mform_audits_this_run,
                rubric_data=rubric_data,
                workspace_dir=workspace_dir,
                project_dir=Path(PROJECT_DIR),
                runtime=RUNTIME,
            )
            if _mform_fired:
                _mform_audits_this_run += 1
        except Exception:
            pass

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
        yield_decision = evaluate_information_yield(
            iteration_history,
            underidentified_after=args.underidentified_after,
            class_novelty_mode=(_stagnation_trigger_mode() == "new_class"),
        )
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

                        # Count visible evidence points for BIC computation.
                        _n_evidence_pts = sum(
                            1 for _line in (evidence_text or "").strip().splitlines()
                            if _line.strip() and not _line.strip().startswith("#")
                        )

                        def _asymptotic_sort_key(r: dict) -> tuple:
                            """Sort saturating corrections and ratio probes
                            before diverging ones, then by BIC (parsimony-aware).

                            GP-088 finding: ranking by visible max_res alone selects
                            overparameterized forms that fit training noise but fail
                            the farther-tail holdout. BIC penalizes extra parameters,
                            preferring simpler forms when the fit is comparable.
                            """
                            _round_label = str(r.get("round", ""))
                            _is_ratio = r.get("probe_type") == "ratio"
                            _is_saturating = _is_ratio or any(
                                base in _round_label for base in _SATURATING_BASES
                            )
                            _priority = 0 if _is_saturating else 1
                            # BIC = n*log(SSE/n) + k*log(n), approximated from
                            # max_abs_residual and parameter count.
                            _res = float(r.get("visible_max_abs_residual", 999))
                            _k = len(r.get("parameter_names", []))
                            _n = max(_n_evidence_pts, 1)
                            # Approximate SSE from max_abs_residual (conservative:
                            # assume mean residual ≈ max/2, SSE ≈ n*(max/2)^2).
                            _sse_approx = _n * (_res / 2.0) ** 2 if _res < 900 else 1e6
                            _sse_safe = max(_sse_approx, 1e-300)
                            _bic = _n * math.log(_sse_safe / _n) + _k * math.log(_n)
                            return (_priority, _bic)

                        _successes.sort(key=_asymptotic_sort_key)

                        # Grammar filter: remove candidates that use
                        # functions forbidden by the rubric grammar.
                        # Without this, grammar-illegal candidates
                        # (e.g. sinh/cosh under math_exp_only) fill
                        # the queue and get rejected every iteration,
                        # creating an infinite burn loop.
                        _grammar = str(rubric_data.get("fit_expression_grammar", "") or "").strip().lower()
                        if _grammar in ("math_exp_only", "math_exp_trig"):
                            # math_exp_only: forbid all trig
                            # math_exp_trig: forbid only hyperbolic trig (sinh/cosh/tanh)
                            _forbidden_pattern = (
                                r"math\.(sin|cos|tan|sinh|cosh|tanh|asin|acos|atan)"
                                if _grammar == "math_exp_only"
                                else r"math\.(sinh|cosh|tanh|asin|acos|atan)"
                            )
                            _FORBIDDEN_MATH = re.compile(_forbidden_pattern)
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

                        # Topology diversification: guarantee the seed queue
                        # contains at least one representative from each structural
                        # class. GP-088 panel verdict: without this, the queue fills
                        # with log-polynomial variants that overfit the visible window,
                        # crowding out power-law forms that would pass the farther-tail
                        # gate. The gate is the correct filter — the seed queue should
                        # be an exploration budget, not a selection filter.
                        def _classify_topology(expr: str) -> str:
                            """Classify expression into topology class by dominant term."""
                            e = expr.lower()
                            has_power = "**" in e and "1/" not in e.split("**")[0][-5:]
                            has_exp = "math.exp" in e
                            has_log = "math.log" in e
                            has_sqrt = "math.sqrt" in e
                            has_ratio = "/" in e and ("(" in e.split("/")[0])
                            if has_exp and has_ratio:
                                return "exponential_rational"
                            if has_exp:
                                return "exponential"
                            if has_power or has_sqrt:
                                return "power_law"
                            if has_log and ("math.log(n)" in e or "math.log(n +" in e.replace(" ", "")):
                                # Check for log^2 (polynomial in log)
                                if "**2" in e or "** 2" in e or "log(n)**" in e.replace(" ", ""):
                                    return "log_polynomial"
                                return "log_simple"
                            if has_ratio:
                                return "rational"
                            return "other"

                        # Group by topology class, take best (already BIC-sorted) from each
                        _by_class: dict[str, list[dict]] = {}
                        for _s in _successes:
                            _cls = _classify_topology(_s.get("expression", ""))
                            _by_class.setdefault(_cls, []).append(_s)

                        # Build diversified queue: one per class, then fill with global best
                        _diverse: list[dict] = []
                        _used_exprs: set[str] = set()
                        for _cls in sorted(_by_class.keys()):
                            _best = _by_class[_cls][0]  # already sorted by BIC
                            _expr = _best.get("expression", "")
                            if _expr not in _used_exprs:
                                _diverse.append(_best)
                                _used_exprs.add(_expr)
                        # Fill remaining slots with global best not already selected
                        for _s in _successes:
                            if len(_diverse) >= 5:
                                break
                            _expr = _s.get("expression", "")
                            if _expr not in _used_exprs:
                                _diverse.append(_s)
                                _used_exprs.add(_expr)

                        _top_k = _diverse[:5]
                        if len(_by_class) > 1:
                            _class_summary = ", ".join(
                                f"{c}({len(v)})" for c, v in sorted(_by_class.items())
                            )
                            print(f"    >> Topology diversification: {_class_summary}")
                            print(f"       Selected {len(_top_k)} seeds from {len(_by_class)} classes")

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
            import traceback as _tb_comp
            print(f"    >> Component D: error — {_comp_exc}")
            _tb_comp.print_exc()

    # Iter-budget checkpoint structure (apparatus-wide, 2026-04-26).
    # Reads rubric.checkpoint_iters = [[iter, condition_name], ...].
    # If the named condition fails at the just-completed iter, abort
    # the loop with run_exit_reason="checkpoint_failure" and emit a
    # checkpoint_evaluation telemetry record. Default empty list →
    # current behavior preserved (no abort).
    _checkpoint_specs = rubric_data.get("checkpoint_iters") or []
    if _checkpoint_specs:
        try:
            from src.ztare.orchestrator.run_checkpoints import (
                evaluate_checkpoints as _evaluate_checkpoints,
            )
            _eh_records_cp: list[dict] = []
            _eh_path_cp = workspace_dir / "eval_history.jsonl"
            if _eh_path_cp.exists():
                for _ln_cp in _eh_path_cp.read_text(encoding="utf-8").splitlines():
                    _ln_cp = _ln_cp.strip()
                    if not _ln_cp:
                        continue
                    try:
                        _eh_records_cp.append(json.loads(_ln_cp))
                    except Exception:
                        continue
            # Only evaluate when this iter matches one of the configured
            # checkpoint iters; the helper returns None otherwise so the
            # telemetry record is only written on actual checkpoint iters.
            _cp_iters_set = set()
            for _cp_spec in _checkpoint_specs:
                try:
                    _cp_iters_set.add(int(_cp_spec[0]))
                except Exception:
                    continue
            if (i + 1) in _cp_iters_set:
                _cp_verdict = _evaluate_checkpoints(
                    eval_history=_eh_records_cp,
                    rubric_checkpoints=_checkpoint_specs,
                    current_iter=i + 1,
                )
                _append_run_boundary_telemetry(
                    workspace_dir,
                    {
                        "record_type": "checkpoint_evaluation",
                        "run_id": RUN_ID,
                        "iteration_index": i + 1,
                        "timestamp_utc": _utc_now_iso(),
                        "checkpoint_specs": [
                            list(_s) for _s in _checkpoint_specs if _s
                        ],
                        "abort": bool(_cp_verdict and _cp_verdict.get("abort")),
                        "verdict": _cp_verdict,
                    },
                )
                if _cp_verdict and _cp_verdict.get("abort"):
                    run_exit_reason = "checkpoint_failure"
                    last_completed_iteration = i + 1
                    print(
                        f"🛑 CHECKPOINT FAILURE @ iter {i + 1}: "
                        f"condition='{_cp_verdict.get('condition')}' "
                        f"detail={_cp_verdict.get('detail')}"
                    )
                    break
        except ImportError:
            pass
        except Exception as _cp_exc:  # noqa: BLE001
            print(f"🛑 checkpoint evaluator error (non-fatal): {_cp_exc}")

    time.sleep(1)

# End of loop
_finalize_run_telemetry_once()

# META-GATE 2C post-run meta-audit (opt-in via rubric.enable_post_run_meta_audit).
# Reads workspace trace + critique, calls a cross-family LLM, writes
# workspace/post_run_meta_audit.{json,md}. Fail-graceful — never fails the run.
if bool(rubric_data.get("enable_post_run_meta_audit", False)):
    try:
        from src.ztare.orchestrator.post_run_meta_audit import run_post_run_meta_audit as _run_meta_audit
        _audit_model_id = str(rubric_data.get("meta_audit_model_id") or "claude-haiku-4-5")
        _audit_verdict = _run_meta_audit(
            project_dir=Path(PROJECT_DIR),
            run_id=str(RUN_ID),
            mutator_model_id=MUTATOR_MODEL_ID,
            judge_model_id=JUDGE_MODEL_ID,
            audit_model_id=_audit_model_id,
        )
        print(
            f"🧭 post-run meta-audit: succeeded={_audit_verdict.get('succeeded')} "
            f"model={_audit_verdict.get('model_id_used')} "
            f"artifact={_audit_verdict.get('artifact_path_md')}"
        )
    except Exception as _audit_exc:  # noqa: BLE001
        print(f"🧭 post-run meta-audit error (non-fatal): {_audit_exc}")

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
