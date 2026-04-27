"""GP-169 Phase 2 — Cold-LLM Erdős seed re-query on stagnation.

The iter-0 cold-LLM seed (`pre_iter1_dispatch.dispatch_pre_iter1_cage`)
reflects the *baseline* residual fingerprint, computed before any iter
has fitted a form. After 2-3 iters of stagnation the residual fingerprint
has shifted — what's stuck NOW is structurally different from what was
stuck pre-iter-1. Re-querying the cold LLM with the *current* fingerprint
keeps the Erdős seed evidence-driven instead of cold.

Triggers (configurable via rubric, defaults shown):

    rubric.enable_erdos_requery_on_stagnation     (default: True when
                                                   enable_cold_llm_erdos_seed)
    rubric.erdos_requery_stagnation_threshold     (default: 2 zero-score iters)
    rubric.erdos_requery_ast_bucket_threshold     (default: 3 same-AST iters)
    rubric.erdos_requery_max_per_run              (default: 3 — caps cost)

Idempotency: a re-query writes `cold_llm_seed_requery_iter_NNN.json` and
appends to `cold_llm_seed_requery_log.json`. The briefing provider
prefers the most-recent valid requery file when rendering. Each
"stagnation event" (uninterrupted run of zero scores) gets at most one
requery — subsequent iters in the same event reuse the cached one.

Per panel review for Q2: the re-query injects the new candidates via the
existing ColdLlmSeedBriefingProvider, which already lands in the mutator
prompt at autoresearch_loop.py:2802 (`_telemetry_block = _briefing_block`).
No separate plumbing: the same channel that delivered iter-0's seed
delivers the refresh.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ── Stagnation detection ─────────────────────────────────────────────────


@dataclass
class StagnationSignal:
    is_stagnant: bool = False
    reason: Optional[str] = None
    consecutive_zero_iters: int = 0
    consecutive_same_ast_iters: int = 0
    last_form: Optional[str] = None


def _ast_bucket(form: str) -> str:
    """Stable AST-shape hash. Mirrors forced_reframe.parametric_form_ast_bucket
    so the two stagnation detectors agree on what "same family" means."""
    if not form:
        return "empty"
    try:
        tree = ast.parse(form, mode="eval")
    except SyntaxError:
        return "syntax_error"
    parts: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Constant, ast.Name)):
            continue
        if isinstance(node, ast.Subscript):
            parts.append("Subscript")
            continue
        parts.append(type(node).__name__)
    return hashlib.sha1("|".join(sorted(parts)).encode()).hexdigest()[:12]


def detect_stagnation(
    eval_history: list[dict],
    *,
    stagnation_threshold: int = 2,
    ast_bucket_threshold: int = 3,
) -> StagnationSignal:
    """Decide whether to re-query the cold LLM.

    Two independent triggers (re-query fires on either):
      A. ``stagnation_threshold`` consecutive iters at score 0
      B. ``ast_bucket_threshold`` consecutive iters with the same AST bucket
    """
    sig = StagnationSignal()
    if not eval_history:
        return sig

    # Aggregate eval_history by iteration (multiple entries per iter → one per iter)
    # Use the last entry per iteration (typically the final submission)
    iter_entries: dict[int, dict[str, Any]] = {}
    for entry in eval_history:
        iter_idx = entry.get("iteration")
        if iter_idx is not None:
            iter_entries[iter_idx] = entry  # Last entry per iter wins
    
    # Walk backward counting zero-score streak at iter level
    zero_streak = 0
    if iter_entries:
        max_iter = max(iter_entries.keys())
        for iter_num in range(max_iter, 0, -1):
            if iter_num in iter_entries:
                s = iter_entries[iter_num].get("score")
                if s == 0:
                    zero_streak += 1
                else:
                    break
            else:
                break
    sig.consecutive_zero_iters = zero_streak

    # Walk backward counting same-bucket streak at iter level
    if iter_entries:
        max_iter = max(iter_entries.keys())
        last_entry = iter_entries[max_iter]
        if last_entry.get("parametric_form"):
            bucket = _ast_bucket(last_entry.get("parametric_form", ""))
            same_streak = 1
            for iter_num in range(max_iter - 1, 0, -1):
                if iter_num in iter_entries:
                    entry = iter_entries[iter_num]
                    if _ast_bucket(entry.get("parametric_form", "")) == bucket and bucket not in (
                        "empty", "syntax_error"
                    ):
                        same_streak += 1
                    else:
                        break
                else:
                    break
            sig.consecutive_same_ast_iters = same_streak
            sig.last_form = last_entry.get("parametric_form", "")
        else:
            sig.consecutive_same_ast_iters = 0
    else:
        sig.consecutive_same_ast_iters = 0

    if zero_streak >= stagnation_threshold:
        sig.is_stagnant = True
        sig.reason = f"score_streak: {zero_streak} consecutive zero-score iters"
    elif sig.consecutive_same_ast_iters >= ast_bucket_threshold:
        sig.is_stagnant = True
        sig.reason = (
            f"ast_bucket_streak: {sig.consecutive_same_ast_iters} consecutive iters "
            f"with the same PARAMETRIC_FORM AST bucket"
        )
    return sig


# ── Current-iter residual fingerprint ───────────────────────────────────


def build_current_fingerprint(
    workspace_dir: Path,
    rubric_data: dict,
) -> Optional[dict]:
    """Compute a refreshed anonymized fingerprint from per-iter telemetry.

    Reads (in order of preference):
      1. Latest ``noise_profile_post_fit_iter_NNN.json``  — heavy_tail,
         autocorrelation, normality verdicts on residuals
      2. Latest entry in ``analogy_log.jsonl``            — residual_topology
         (regime_break, monotonicity, sign_pattern, kurtosis)
      3. ``substrate_critique.json``                       — heuristic priors

    Falls back to whatever's available; returns None only if NOTHING is.
    The fingerprint goes through the existing ``quantize_fingerprint``
    pass before being shipped (Panel-Blindspot-1 — broad buckets).
    """
    fp: dict[str, Any] = {
        "shape": "monotone_or_unknown",
        "monotonicity": 0.0,
        "regime_break_count": 0,
        "heavy_tail_flag": False,
        "sign_pattern": "positive_only",
        "y_dynamic_range_decades": 0.0,
        "n_visible_classes": 0,
        "n_withheld_classes": 0,
    }

    # 1. Pull latest noise_profile_post_fit
    np_files = sorted(workspace_dir.glob("noise_profile_post_fit_iter_*.json"))
    if np_files:
        try:
            d = json.loads(np_files[-1].read_text(encoding="utf-8"))
            fp["heavy_tail_flag"] = bool(d.get("heavy_tail_flag", False))
        except Exception:
            pass

    # 2. Pull latest analogy_log entry
    al_path = workspace_dir / "analogy_log.jsonl"
    if al_path.exists():
        try:
            for line in reversed(al_path.read_text(encoding="utf-8").splitlines()):
                if not line.strip():
                    continue
                rec = json.loads(line)
                fingerprint_blob = rec.get("fingerprint") or {}
                topo = fingerprint_blob.get("residual_topology") or {}
                if topo:
                    if "shape" in topo:
                        fp["shape"] = topo["shape"]
                    if "monotonicity" in topo:
                        try:
                            fp["monotonicity"] = float(topo.get("spearman_rho_residuals_vs_x", 0.0))
                        except (TypeError, ValueError):
                            pass
                    if topo.get("regime_break_likely"):
                        fp["regime_break_count"] = max(int(fp.get("regime_break_count") or 0), 1)
                    if topo.get("heavy_tail"):
                        fp["heavy_tail_flag"] = True
                    if "sign_pattern" in topo:
                        fp["sign_pattern"] = topo["sign_pattern"]
                ydr = fingerprint_blob.get("y_dynamic_range_decades")
                if ydr is not None:
                    try:
                        fp["y_dynamic_range_decades"] = float(ydr)
                    except (TypeError, ValueError):
                        pass
                break
        except Exception:
            pass

    # 3. Class counts from substrate_critique.json (no precise values)
    sc_path = workspace_dir / "substrate_critique.json"
    if sc_path.exists():
        try:
            d = json.loads(sc_path.read_text(encoding="utf-8"))
            cc = d.get("cross_class_signal") or []
            # Number of classes is rough proxy: count unique class labels
            # the critique reports on.
            classes = {item.get("class") for item in cc if item.get("class")}
            if classes:
                fp["n_visible_classes"] = len(classes)
        except Exception:
            pass

    # Quantize per Panel-Blindspot-1 before shipping to the cold LLM.
    try:
        from src.ztare.fit.cold_llm_erdos_seed import quantize_fingerprint
        return quantize_fingerprint(fp)
    except ImportError:
        return fp


# ── Re-query orchestration ──────────────────────────────────────────────


@dataclass
class RequeryVerdict:
    attempted: bool = False
    succeeded: bool = False
    cached_hit: bool = False
    iter_index: int = 0
    n_valid_candidates: int = 0
    artifact_path: Optional[str] = None
    error: Optional[str] = None
    log_lines: list[str] = field(default_factory=list)


def _requery_log_path(workspace_dir: Path) -> Path:
    return workspace_dir / "cold_llm_seed_requery_log.json"


def _read_requery_log(workspace_dir: Path) -> dict:
    p = _requery_log_path(workspace_dir)
    if not p.exists():
        return {"events": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"events": []}


def _write_requery_log(workspace_dir: Path, log: dict) -> None:
    try:
        _requery_log_path(workspace_dir).write_text(
            json.dumps(log, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _signal_signature(sig: StagnationSignal) -> str:
    """Stable id for a stagnation event so we don't requery N times in a row."""
    return f"zeros={sig.consecutive_zero_iters}|ast_streak={sig.consecutive_same_ast_iters}"


def maybe_requery_cold_seed(
    *,
    project_dir: Path,
    rubric_data: dict,
    iter_index: int,
    eval_history: list[dict],
    workspace_dir: Optional[Path] = None,
    mutator_model_id: Optional[str] = None,
) -> RequeryVerdict:
    """Run a stagnation-driven cold-LLM re-query when warranted.

    Idempotent within a single stagnation event: subsequent calls in
    the same event return ``cached_hit=True`` without making an LLM
    call. The caller's responsibility is to pass the eval history and
    iter index from the briefing context.

    Returns a verdict the briefing provider uses to decide whether to
    swap in the refreshed candidates.
    """
    verdict = RequeryVerdict(iter_index=iter_index)
    workspace_dir = workspace_dir or (project_dir / "workspace")

    if not bool(rubric_data.get("enable_cold_llm_erdos_seed", False)):
        return verdict
    if not bool(rubric_data.get("enable_erdos_requery_on_stagnation", True)):
        return verdict

    stag_thresh = int(rubric_data.get("erdos_requery_stagnation_threshold", 2))
    ast_thresh = int(rubric_data.get("erdos_requery_ast_bucket_threshold", 3))
    max_per_run = int(rubric_data.get("erdos_requery_max_per_run", 3))

    sig = detect_stagnation(
        eval_history,
        stagnation_threshold=stag_thresh,
        ast_bucket_threshold=ast_thresh,
    )
    if not sig.is_stagnant:
        return verdict

    log = _read_requery_log(workspace_dir)
    events: list[dict] = log.get("events") or []
    if len(events) >= max_per_run:
        verdict.log_lines.append(
            f"🔎 GP-169 re-query: budget exhausted ({len(events)}/{max_per_run}); "
            f"reusing prior cached candidates."
        )
        verdict.cached_hit = True
        return verdict

    sig_id = _signal_signature(sig)
    if events and events[-1].get("signature") == sig_id:
        # Same stagnation event — no new query, just signal cached.
        verdict.cached_hit = True
        verdict.log_lines.append(
            f"🔎 GP-169 re-query: same stagnation event ({sig_id}); "
            f"reusing iter-{events[-1].get('iter_index')} requery."
        )
        return verdict

    verdict.attempted = True

    fingerprint = build_current_fingerprint(workspace_dir, rubric_data)
    if fingerprint is None:
        verdict.error = "could not build current fingerprint"
        verdict.log_lines.append(f"🔎 GP-169 re-query: {verdict.error}")
        return verdict

    raw_model_id = str(rubric_data.get("cold_llm_seed_model_id") or "").strip()
    if raw_model_id in ("", "@mutator", "mutator"):
        if not mutator_model_id:
            verdict.error = "cold_llm_seed_model_id is '@mutator' (or blank) but mutator_model_id not supplied"
            verdict.log_lines.append(f"🔎 GP-169 re-query: {verdict.error}")
            return verdict
        model_id = str(mutator_model_id).strip()
    else:
        model_id = raw_model_id

    forbidden_domain = rubric_data.get("cold_llm_seed_forbidden_domain")
    k_law_budget = int(rubric_data.get("cold_llm_seed_k_law_budget", 7))
    timeout_s = float(rubric_data.get("cold_llm_seed_timeout_seconds", 30.0))

    try:
        from src.ztare.fit.cold_llm_erdos_seed import (
            query_cold_llm_erdos_seed,
        )
    except ImportError as exc:
        verdict.error = f"cold_llm_erdos_seed import failed: {exc}"
        verdict.log_lines.append(f"🔎 GP-169 re-query: {verdict.error}")
        return verdict

    response = query_cold_llm_erdos_seed(
        fingerprint=fingerprint,
        model_id=model_id,
        forbidden_domain=forbidden_domain,
        k_law_budget=k_law_budget,
        timeout_seconds=timeout_s,
    )

    n_valid = sum(1 for c in response.candidates if c.valid_python)
    verdict.n_valid_candidates = n_valid

    out_path = workspace_dir / f"cold_llm_seed_requery_iter_{iter_index:03d}.json"
    payload = response.to_dict()
    payload["requery_meta"] = {
        "iter_index": iter_index,
        "stagnation_reason": sig.reason,
        "consecutive_zero_iters": sig.consecutive_zero_iters,
        "consecutive_same_ast_iters": sig.consecutive_same_ast_iters,
        "fingerprint_used": fingerprint,
    }
    try:
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        verdict.artifact_path = str(out_path)
    except Exception as exc:
        verdict.error = f"could not write requery artifact: {exc}"
        verdict.log_lines.append(f"🔎 GP-169 re-query: {verdict.error}")
        return verdict

    if response.error and n_valid == 0:
        verdict.error = response.error
        verdict.log_lines.append(
            f"🔎 GP-169 re-query: cold-LLM error — {response.error}; "
            f"briefing will fall through to iter-0 seed."
        )
        return verdict

    verdict.succeeded = n_valid >= 2
    events.append({
        "iter_index": iter_index,
        "signature": sig_id,
        "n_valid_candidates": n_valid,
        "artifact": out_path.name,
    })
    log["events"] = events
    _write_requery_log(workspace_dir, log)

    verdict.log_lines.append(
        f"🔎 GP-169 re-query: stagnation detected ({sig.reason}); "
        f"refreshed cold-seed candidates (valid={n_valid}); written to {out_path.name}."
    )
    return verdict


def latest_seed_artifact(workspace_dir: Path) -> Optional[Path]:
    """Return the most-recent valid cold-seed file (requery preferred over
    iter-0 baseline). Used by the briefing provider for rendering."""
    requery = sorted(workspace_dir.glob("cold_llm_seed_requery_iter_*.json"))
    for p in reversed(requery):
        # Skip empty / unparseable / 0-valid files: those should fall
        # back to the iter-0 baseline rather than render a degraded view.
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            valid = sum(1 for c in (d.get("candidates") or []) if c.get("valid_python"))
            if valid >= 2:
                return p
        except Exception:
            continue
    iter0 = workspace_dir / "cold_llm_seed_iter0.json"
    return iter0 if iter0.exists() else None
