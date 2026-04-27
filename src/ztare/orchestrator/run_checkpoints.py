"""Iter-budget checkpoint structure for bounded open-ended runs.

Apparatus-wide upgrade (2026-04-26): rubric.checkpoint_iters allows
operators to short-circuit runaway runs that show no progress. Each
checkpoint is a (iter_number, condition_name) pair evaluated AFTER the
specified iter completes. If the condition fails, the run aborts with
exit reason "checkpoint_failure" and a structured telemetry record is
appended.

Substrate-agnostic. Conditions read only the rolling eval_history list
plus iteration_telemetry rows; no substrate-specific knowledge is hard-
coded here.

Supported conditions:
    - any_pass_l3: at least one iter so far has all gate_verdicts=True
      (a proxy for the "L3 unit tests" — gate_harness.all_gates_pass).
    - any_score_geq_70: at least one iter has raw_judge_score >= 70.
    - raw_score_improved_from_iter_1: best raw_judge_score so far is
      strictly greater than iter-1's raw_judge_score.
    - unique_ast_buckets_geq_N: apparatus has explored at least N
      distinct AST buckets (escape from basin lock). The threshold N
      is parsed from the condition name suffix, e.g.
      "unique_ast_buckets_geq_3".

Default: checkpoint_iters=[] preserves current behavior (no abort).
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Optional


_AST_BUCKET_RE = re.compile(r"^unique_ast_buckets_geq_(\d+)$")


def _coerce_int_score(record: dict) -> Optional[int]:
    val = record.get("raw_judge_score")
    if val is None:
        # fall back to capped score if raw is absent
        val = record.get("score")
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _all_gates_pass(record: dict) -> bool:
    """True iff gate_verdicts is non-empty AND every entry is True.

    Mirrors gate_harness.all_gates_pass for eval_history.jsonl rows
    that persist gate_verdicts as {gate_name: bool}. Empty dict returns
    False (no gates fired = not a pass signal).
    """
    verdicts = record.get("gate_verdicts") or {}
    if not isinstance(verdicts, dict) or not verdicts:
        return False
    return all(bool(v) for v in verdicts.values())


def _ast_bucket(record: dict) -> Optional[str]:
    """Extract a coarse AST bucket label for a record.

    Strategy: prefer an explicit ast_bucket / ast_fingerprint field if
    the substrate persists one; otherwise normalize parametric_form to
    its function-call skeleton (operators + math functions) so two
    semantically equivalent forms with different constants share a bucket.
    Returns None when no signal is available.
    """
    for key in ("ast_bucket", "ast_fingerprint", "parametric_form_bucket"):
        v = record.get(key)
        if v:
            return str(v)
    form = record.get("parametric_form")
    if not form:
        return None
    # Coarse skeleton: strip numeric literals and parameter names, keep
    # operators + math.* function names. Substrate-agnostic; collisions
    # are tolerable (the gate is "have we explored at least N buckets").
    skeleton = re.sub(r"\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b", "#", str(form))
    skeleton = re.sub(r"\bp\.get\([^)]+\)", "P", skeleton)
    skeleton = re.sub(r"\s+", "", skeleton)
    return skeleton or None


def evaluate_checkpoints(
    eval_history: Iterable[dict],
    rubric_checkpoints: Iterable[Any],
    current_iter: int,
) -> Optional[dict]:
    """Decide whether the run should abort at the just-completed iter.

    Args:
        eval_history: iterable of eval-history records (one per iter so
            far). Each record is a dict with at least: iteration, score,
            raw_judge_score, gate_verdicts, parametric_form.
        rubric_checkpoints: iterable of [iter_number, condition_name]
            pairs from rubric.checkpoint_iters. Anything else is ignored.
        current_iter: the 1-indexed iter number that just completed.

    Returns:
        None if no checkpoint applies at this iter or all conditions
        passed. Otherwise a structured abort dict:
            {"abort": True,
             "iter": current_iter,
             "condition": <name>,
             "reason": "checkpoint_failure",
             "detail": <human-readable diagnosis>}
    """
    history = list(eval_history)
    if not rubric_checkpoints:
        return None

    for entry in rubric_checkpoints:
        try:
            cp_iter, cp_name = entry[0], entry[1]
        except (TypeError, IndexError, KeyError):
            continue
        try:
            cp_iter = int(cp_iter)
        except (TypeError, ValueError):
            continue
        cp_name = str(cp_name).strip()
        if cp_iter != current_iter:
            continue

        passed, detail = _evaluate_one(cp_name, history)
        if passed:
            continue
        return {
            "abort": True,
            "iter": current_iter,
            "condition": cp_name,
            "reason": "checkpoint_failure",
            "detail": detail,
        }
    return None


def _evaluate_one(condition: str, history: list[dict]) -> tuple[bool, str]:
    """Return (passed, detail) for one condition.

    Unknown conditions pass with a diagnostic detail string; this is
    fail-graceful — a typo'd checkpoint never aborts the run.
    """
    if condition == "any_pass_l3":
        if any(_all_gates_pass(r) for r in history):
            return True, "at_least_one_iter_passed_all_gates"
        return False, f"no_iter_passed_all_gates_in_{len(history)}_iters"

    if condition == "any_score_geq_70":
        scores = [s for s in (_coerce_int_score(r) for r in history) if s is not None]
        if any(s >= 70 for s in scores):
            return True, f"max_raw_score={max(scores)}"
        max_s = max(scores) if scores else None
        return False, f"no_iter_reached_70 (max_seen={max_s}, n={len(scores)})"

    if condition == "raw_score_improved_from_iter_1":
        if not history:
            return False, "history_empty"
        iter1 = next((r for r in history if r.get("iteration") == 1), None)
        if iter1 is None:
            return False, "iter_1_record_absent"
        s1 = _coerce_int_score(iter1)
        if s1 is None:
            return False, "iter_1_score_unparseable"
        best = max(
            (s for s in (_coerce_int_score(r) for r in history) if s is not None),
            default=None,
        )
        if best is None:
            return False, "no_parseable_scores"
        if best > s1:
            return True, f"best={best} > iter1={s1}"
        return False, f"best={best} <= iter1={s1}"

    m = _AST_BUCKET_RE.match(condition)
    if m:
        threshold = int(m.group(1))
        buckets = {b for b in (_ast_bucket(r) for r in history) if b}
        if len(buckets) >= threshold:
            return True, f"distinct_buckets={len(buckets)}>={threshold}"
        return False, f"distinct_buckets={len(buckets)}<{threshold}"

    return True, f"unknown_condition:{condition}_skipped"
