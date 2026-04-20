"""GP-048 Apparatus-Feedback surfaces.

Implements three independent, flag-gated feedback surfaces designed to test
the apparatus-bottleneck hypotheses in the mission seam's Hypothesis Ledger
(H-GP023-02, H-GP023-03). None of these surfaces changes the mutator model,
the evaluator, or the hidden evidence; they only alter what the mutator
prompt surfaces to the model.

Surfaces:

1. **Telemetry (Mode 1).** Per-iter JSONL record of extracted primitive set
   and tree-edit-distance to prior champion. Read-only; enables post-hoc
   cone-escape attribution without changing any run decisions.

2. **Primitive-cohort stagnation injection (Mode 2).** At stagnation, render
   a prompt block telling the mutator which primitive cohort its recent
   champions share and which primitives it has NOT yet tried. Annotation,
   not instruction — the mutator still chooses.

3. **Farther-tail veto feedback.** When the latest evaluation shows a
   `farther_tail_*` gate failure, render a sanitized veto string that tells
   the mutator the fact of the failure without leaking hidden evidence. The
   point is to close the feedback loop GP-046 deliberately hides, so the
   mutator has a reason to consider a structural change rather than a
   parameter sweep.

All three surfaces are flag-gated in the rubric:
  - `gp048_telemetry: true`                              — enables Mode 1
  - `gp048_stagnation_injection_mode: "primitive_cone"`  — enables Mode 2
  - `gp048_farther_tail_veto_mode: "sanitized"`          — enables farther-tail veto

Any combination of flags is valid. None of them changes the kernel's
scoring surface or the gate evaluator.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ztare.composition.structural_memory import (
    ExpressionParseError,
    PRIMITIVE_LABELS,
    extract_primitives,
    normalize_expression,
    tree_edit_distance,
)


FIT_RESULT_ITER_RE = re.compile(r"fit_result_iter_(\d+)\.json$")

GP048_TELEMETRY_FILENAME = "gp048_telemetry.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_success_records(
    workspace_dir: Path,
    limit: int | None = None,
    exclude_iter: int | None = None,
) -> list[dict[str, Any]]:
    """Return recent successful fit_result_iter_*.json records, most recent first.

    `exclude_iter` skips a specific iteration (used when we want the prior
    champions to the current one).
    """

    records: list[tuple[int, dict[str, Any]]] = []
    for path in workspace_dir.glob("fit_result_iter_*.json"):
        match = FIT_RESULT_ITER_RE.search(path.name)
        if not match:
            continue
        iteration = int(match.group(1))
        if exclude_iter is not None and iteration == exclude_iter:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("status") != "success":
            continue
        records.append((iteration, data))
    records.sort(key=lambda item: item[0], reverse=True)
    if limit is not None:
        records = records[:limit]
    return [data for _, data in records]


def _safe_primitives(data: dict[str, Any]) -> set[str] | None:
    expression = data.get("expression")
    if not isinstance(expression, str):
        return None
    independent_vars = list(data.get("independent_vars", []))
    parameter_names = list(data.get("parameter_names", []))
    try:
        tree = normalize_expression(expression, independent_vars, parameter_names)
    except ExpressionParseError:
        return None
    return extract_primitives(tree)


def _safe_tree(data: dict[str, Any]):
    expression = data.get("expression")
    if not isinstance(expression, str):
        return None
    independent_vars = list(data.get("independent_vars", []))
    parameter_names = list(data.get("parameter_names", []))
    try:
        return normalize_expression(expression, independent_vars, parameter_names)
    except ExpressionParseError:
        return None


# ---------------------------------------------------------------------------
# Mode 1 — Telemetry
# ---------------------------------------------------------------------------


@dataclass
class TelemetryLine:
    iteration: int
    expression: str
    primitives: list[str]
    ted_to_prev: int | None
    new_primitives_vs_prev: list[str]
    new_primitives_vs_run: list[str]


def write_telemetry_line(
    workspace_dir: Path,
    *,
    iteration: int,
    fit_result_data: dict[str, Any],
) -> TelemetryLine | None:
    """Append one telemetry line to gp048_telemetry.jsonl.

    Reads prior champions from the same workspace to compute TED and
    new-primitives deltas. Non-fatal: any failure returns None without
    raising.
    """

    primitives = _safe_primitives(fit_result_data)
    if primitives is None:
        return None
    current_tree = _safe_tree(fit_result_data)
    if current_tree is None:
        return None

    prior_records = _load_success_records(
        workspace_dir, limit=None, exclude_iter=iteration
    )
    prior_tree = None
    prior_primitives: set[str] = set()
    run_primitives: set[str] = set()
    for prior in prior_records:
        prior_prims = _safe_primitives(prior)
        if prior_prims is None:
            continue
        run_primitives.update(prior_prims)
        if prior_tree is None:
            prior_tree = _safe_tree(prior)
            prior_primitives = prior_prims

    try:
        ted_to_prev = (
            tree_edit_distance(current_tree, prior_tree) if prior_tree is not None else None
        )
    except Exception:
        ted_to_prev = None

    new_vs_prev = sorted(primitives - prior_primitives) if prior_tree is not None else sorted(primitives)
    new_vs_run = sorted(primitives - run_primitives)

    line = TelemetryLine(
        iteration=iteration,
        expression=str(fit_result_data.get("expression", "")),
        primitives=sorted(primitives),
        ted_to_prev=ted_to_prev,
        new_primitives_vs_prev=new_vs_prev,
        new_primitives_vs_run=new_vs_run,
    )

    payload = {
        "timestamp_utc": _utc_now_iso(),
        "iteration": line.iteration,
        "expression": line.expression,
        "primitives": line.primitives,
        "ted_to_prev": line.ted_to_prev,
        "new_primitives_vs_prev": line.new_primitives_vs_prev,
        "new_primitives_vs_run": line.new_primitives_vs_run,
    }

    telemetry_path = workspace_dir / GP048_TELEMETRY_FILENAME
    try:
        with telemetry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
    except OSError:
        return None

    return line


# ---------------------------------------------------------------------------
# Mode 2 — Primitive-cohort stagnation injection
# ---------------------------------------------------------------------------


@dataclass
class CohortSummary:
    cohort: set[str]
    missing: set[str]
    last_k: int
    last_k_iterations: list[int]
    is_monopoly: bool  # True iff all last_k records share the same primitive set


def compute_recent_cohort(
    workspace_dir: Path,
    *,
    k: int = 5,
) -> CohortSummary | None:
    """Compute the dominant primitive cohort across the last k successful fits."""

    records_with_iter: list[tuple[int, dict[str, Any]]] = []
    for path in workspace_dir.glob("fit_result_iter_*.json"):
        match = FIT_RESULT_ITER_RE.search(path.name)
        if not match:
            continue
        iteration = int(match.group(1))
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("status") != "success":
            continue
        records_with_iter.append((iteration, data))
    records_with_iter.sort(key=lambda item: item[0], reverse=True)
    records_with_iter = records_with_iter[:k]
    if not records_with_iter:
        return None

    per_iter_prims: list[tuple[int, set[str]]] = []
    for iteration, data in records_with_iter:
        prims = _safe_primitives(data)
        if prims is None:
            continue
        per_iter_prims.append((iteration, prims))
    if not per_iter_prims:
        return None

    first_set = per_iter_prims[0][1]
    is_monopoly = all(prims == first_set for _, prims in per_iter_prims)

    union_cohort: set[str] = set()
    for _, prims in per_iter_prims:
        union_cohort |= prims
    cohort = first_set if is_monopoly else union_cohort
    missing = set(PRIMITIVE_LABELS) - cohort

    return CohortSummary(
        cohort=cohort,
        missing=missing,
        last_k=len(per_iter_prims),
        last_k_iterations=[iter_ for iter_, _ in per_iter_prims],
        is_monopoly=is_monopoly,
    )


def render_primitive_cohort_prompt_section(
    workspace_dir: Path,
    *,
    k: int = 5,
    min_k_to_fire: int = 3,
) -> str:
    """Render a GP-048 Mode 2 annotation. Returns empty string if the cohort
    is too small or too diverse to warrant an annotation.
    """

    summary = compute_recent_cohort(workspace_dir, k=k)
    if summary is None:
        return ""
    if summary.last_k < min_k_to_fire:
        return ""

    cohort_sorted = ", ".join(sorted(summary.cohort)) or "(empty)"
    missing_sorted = ", ".join(sorted(summary.missing)) or "(none — full vocabulary covered)"
    iter_list = ", ".join(str(i) for i in summary.last_k_iterations)
    monopoly_note = (
        "All of them use the SAME primitive set." if summary.is_monopoly
        else "Union across these champions (not all share all primitives)."
    )

    return f"""### GP-048 PRIMITIVE COHORT ANNOTATION (READ-ONLY)

Your last {summary.last_k} successful champion expressions (iters: {iter_list})
share the following AST primitive cohort:

    cohort: {{{cohort_sorted}}}
    note:   {monopoly_note}

Primitives in the full structural vocabulary you have NOT yet used in this run:

    missing: {{{missing_sorted}}}

What this means:
- The cohort above is a structural signature, not an evaluation. Two different
  expressions inside the same cohort can reach the same failing gate for the
  same reason; if a gate is blocking you, a cohort-local parameter edit will
  likely reach the same blocker.
- The missing set lists primitives that would, by construction, place a new
  candidate in a DIFFERENT cohort. That is the structural axis of escape, if
  escape is needed.
- This is an annotation, not an instruction. Staying in the current cohort is
  valid if you have a concrete reason. Exiting it is also valid. The point is
  that the escape axis is structural (which primitives), not parametric (which
  coefficients), and the structural axis is available to you."""


# ---------------------------------------------------------------------------
# Farther-tail veto feedback
# ---------------------------------------------------------------------------


def _extract_gate_results(latest_eval_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return the deterministic gate results list, traversing all known
    payload shapes.

    Supported shapes (in priority order):
      1. Real runner shape:
         ``score_contract.deterministic_charter_gates.results``
      2. Legacy top-level: ``deterministic_gate_results``
      3. Legacy top-level: ``gate_results``
    """

    if not isinstance(latest_eval_payload, dict):
        return []
    score_contract = latest_eval_payload.get("score_contract")
    if isinstance(score_contract, dict):
        dcg = score_contract.get("deterministic_charter_gates")
        if isinstance(dcg, dict):
            results = dcg.get("results")
            if isinstance(results, list):
                return results
    for key in ("deterministic_gate_results", "gate_results"):
        candidate = latest_eval_payload.get(key)
        if isinstance(candidate, list):
            return candidate
    return []


def _failed_farther_tail_gates(latest_eval_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Extract the subset of failing gates whose name starts with 'farther_tail_'."""

    gates = _extract_gate_results(latest_eval_payload)
    if not gates:
        return []
    failed: list[dict[str, Any]] = []
    for entry in gates:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or entry.get("gate") or "")
        if not name.startswith("farther_tail_"):
            continue
        passed = entry.get("passed")
        if passed is True:
            continue
        # Some payloads encode failure as "status": "fail"
        status = str(entry.get("status") or "").lower()
        if passed is False or status in {"fail", "failed", "failing"}:
            failed.append(entry)
    return failed


def _extract_visible_threshold(latest_eval_payload: dict[str, Any] | None) -> float | None:
    """Pull the visible-slice residual threshold from the eval payload.

    The real harness encodes it as the ``threshold`` field of the
    ``hidden_global_residual`` gate (the visible-slice global-residual gate,
    despite the ``hidden_`` prefix on its name). We never hardcode — if we
    cannot find a value, return ``None`` and let the caller skip the block.
    """

    for entry in _extract_gate_results(latest_eval_payload):
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or entry.get("gate") or "")
        if name in {"hidden_global_residual", "visible_global_residual"}:
            threshold = entry.get("threshold")
            if isinstance(threshold, (int, float)):
                return float(threshold)
    return None


_OPAQUE_GATE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

GP048_VETO_MAPPING_FILENAME = "gp048_farther_tail_veto_mapping.jsonl"


def _opaque_label_from_index(index: int) -> str:
    if index < len(_OPAQUE_GATE_ALPHABET):
        return f"farther_tail_gate_{_OPAQUE_GATE_ALPHABET[index]}"
    return f"farther_tail_gate_{index}"


def _load_opaque_mapping(workspace_dir: Path) -> dict[str, str]:
    """Reconstruct true_name -> opaque_label assignments from prior mapping
    records. First-seen wins, so repeated gate failures in later iterations
    retain their original opaque label."""

    mapping: dict[str, str] = {}
    path = workspace_dir / GP048_VETO_MAPPING_FILENAME
    if not path.exists():
        return mapping
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return mapping
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue
        entries = record.get("mapping") or []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            true_name = entry.get("true_name")
            opaque = entry.get("opaque")
            if isinstance(true_name, str) and isinstance(opaque, str):
                mapping.setdefault(true_name, opaque)
    return mapping


def _assign_opaque_label(true_name: str, existing: dict[str, str]) -> str:
    if true_name in existing:
        return existing[true_name]
    used = set(existing.values())
    for idx in range(len(_OPAQUE_GATE_ALPHABET) + 1000):
        candidate = _opaque_label_from_index(idx)
        if candidate not in used:
            existing[true_name] = candidate
            return candidate
    # Fallback — should never hit; explicit so tests fail loudly if it does.
    fallback = f"farther_tail_gate_overflow_{len(existing)}"
    existing[true_name] = fallback
    return fallback


def render_farther_tail_veto_prompt_section(
    latest_eval_payload: dict[str, Any] | None,
    *,
    visible_threshold: float | None = None,
    workspace_dir: Path | None = None,
    iteration: int | None = None,
) -> str:
    """Render a sanitized farther-tail veto prompt block.

    Sanitization rules (hard, enforced by design):
    - No hidden-evidence values leak (no residual magnitudes, point values,
      phi grids).
    - Gate names are masked. The mutator sees only opaque labels
      (``farther_tail_gate_A``, ``_B``, ...) — the true gate identity is
      never rendered into the prompt, so the mutator cannot key off a name
      like ``farther_tail_monotone`` and shortcut the physics.
    - The true-label mapping is written to
      ``gp048_farther_tail_veto_mapping.jsonl`` in the workspace so operators
      can decode failures post-hoc.
    - ``visible_threshold`` must be supplied by the caller from the rubric —
      never hardcoded. The prompt would otherwise lie to the mutator if a
      sweep tightened the threshold.
    - No language enumerating possible asymptotic shapes, no hints about
      which primitives would fix the failure.
    """

    failed = _failed_farther_tail_gates(latest_eval_payload)
    if not failed:
        return ""

    effective_threshold = visible_threshold
    if effective_threshold is None:
        effective_threshold = _extract_visible_threshold(latest_eval_payload)
    if effective_threshold is None:
        # Fail-closed: we will not render a threshold-bearing prompt with an
        # unknown threshold. Skipping is the correct move — the veto block is
        # a punishment signal, not a hedge, and a wrong threshold lies to the
        # mutator.
        return ""

    existing_mapping: dict[str, str] = (
        _load_opaque_mapping(workspace_dir) if workspace_dir is not None else {}
    )

    gate_lines: list[str] = []
    mapping_entries: list[dict[str, Any]] = []
    seen_this_call: set[str] = set()
    for entry in failed:
        true_name = str(entry.get("name") or entry.get("gate") or "unknown")
        opaque = _assign_opaque_label(true_name, existing_mapping)
        if opaque in seen_this_call:
            continue
        seen_this_call.add(opaque)
        gate_lines.append(f"  - {opaque} (FAILED)")
        mapping_entries.append({"opaque": opaque, "true_name": true_name})
    gate_lines.sort()
    gate_block = "\n".join(gate_lines)

    if workspace_dir is not None:
        try:
            mapping_payload = {
                "timestamp_utc": _utc_now_iso(),
                "iteration": iteration,
                "mapping": mapping_entries,
            }
            mapping_path = workspace_dir / GP048_VETO_MAPPING_FILENAME
            with mapping_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(mapping_payload) + "\n")
        except OSError:
            pass

    return f"""### GP-046 FARTHER-TAIL CONTRACT — HIDDEN GATE FEEDBACK

Your most recent candidate passed the visible-slice residual target
(max |residual| on the fit window under {effective_threshold}) but FAILED one
or more deterministic gates evaluated on hidden evidence BEYOND the visible
frontier.

You are not shown the hidden evidence. Gate identities are masked; you are
shown only opaque labels and the fact of failure:

{gate_block}

What this means:
- Your candidate fits the visible data numerically well.
- Your candidate's EXTRAPOLATED behavior beyond the visible window is wrong.
- The rubric's asymptotic-claim contract requires the model to behave
  correctly in the sealed farther-tail region as well as the visible slice.

Constraint implications:
- A purely-parametric adjustment of your current functional family will not
  recover from this failure. If the family's asymptotic shape is wrong,
  better parameters inside the same family will be wrong in the same way.
- If the form's asymptotic shape is wrong, the correct move is a structural
  change (a different composition, a new term, a different functional family)
  rather than a coefficient sweep.

You are NOT told what the correct asymptotic shape is, which gates failed,
or why. Rediscovering all of that is the task. This feedback tells you only
that your current shape is wrong beyond the visible frontier."""
