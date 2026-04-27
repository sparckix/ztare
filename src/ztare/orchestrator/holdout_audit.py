"""Held-out audit-slice partitioner for substrate-leakage hardening.

Apparatus-wide upgrade (2026-04-26): a 30% audit slice that the mutator
NEVER sees during iteration. Enforces honest extrapolation against
substrate-leakage parameter laundering: any sufficiently flexible
parametric class can fit visible+holdout because both are nominally
available — the audit slice is hash-locked from the mutator and only
computed at run-end.

Substrate-agnostic. Helpers operate on opaque row sequences and a
deterministic seed derived from rubric identity. Substrates opt in by
reading rubric.holdout_audit_fraction in their features module and
calling partition_audit_slice.

Contract:
    - Default off (frac=0.0 → audit slice is empty, visible == input).
    - Deterministic: seed = sha256(rubric_id + "::" + rubric_version).
    - Stable across runs: same rubric → same partition by row identity.
    - The audit slice is NOT exposed during iteration. The substrate's
      farther_tail_rows() returns ONLY the visible portion; the audit
      portion is consumed once at run-end via compute_audit_mre().

References:
    - SR-skeptic panel, 2026-04-26
    - rubric.holdout_audit_fraction (opt-in flag, default 0.0)
"""
from __future__ import annotations

import hashlib
import math
import random
from typing import Any, Callable, Iterable, Sequence


def _seed_from_rubric(rubric_id: str, rubric_version: str | None = None) -> int:
    """Derive a deterministic 64-bit seed from rubric identity.

    rubric_version is optional; absent versions reduce to rubric_id only,
    which is still stable across runs of the same rubric.
    """
    payload = f"{rubric_id}::{rubric_version or ''}"
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    # Fold to 64 bits for Python's PRNG seed.
    return int.from_bytes(digest[:8], "big", signed=False)


def partition_audit_slice(
    rows: Sequence[Any],
    frac: float,
    *,
    rubric_id: str,
    rubric_version: str | None = None,
    row_key: Callable[[Any], Any] | None = None,
) -> tuple[list[Any], list[Any]]:
    """Deterministically partition rows into (visible, audit) sets.

    Args:
        rows: opaque iterable of row records. The substrate decides what
            a row is (dict, tuple, dataclass).
        frac: fraction in [0.0, 1.0] of rows to withhold as audit. 0.0
            returns (rows, []); 1.0 returns ([], rows).
        rubric_id: stable rubric identifier (e.g. rubric file basename).
        rubric_version: optional version string; appended to seed input.
        row_key: optional callable mapping a row to a sort key. When
            provided, rows are sorted by this key before shuffling so
            partition is stable even when the input order varies. When
            absent, input order is the canonical order.

    Returns:
        (visible_rows, audit_rows). Order within visible matches the
        canonical pre-shuffle order; audit rows are returned in their
        post-shuffle order (irrelevant for set-style audit MRE).

    Behavior at edges:
        - frac <= 0.0 → (list(rows), []).
        - frac >= 1.0 → ([], list(rows)).
        - len(rows) == 0 → ([], []).
        - n_audit clamped to [0, len(rows)].

    Determinism guarantee: for a given (rubric_id, rubric_version, frac,
    rows-by-row_key), this function returns identical output across
    Python invocations and platforms.
    """
    rows_list = list(rows)
    n = len(rows_list)
    if n == 0:
        return [], []
    if frac <= 0.0:
        return rows_list, []
    if frac >= 1.0:
        return [], rows_list

    # Canonical ordering: optional sort, then deterministic shuffle.
    if row_key is not None:
        ordered = sorted(rows_list, key=row_key)
    else:
        ordered = list(rows_list)

    seed = _seed_from_rubric(rubric_id, rubric_version)
    rng = random.Random(seed)
    indices = list(range(n))
    rng.shuffle(indices)

    n_audit = max(0, min(n, int(math.floor(n * frac))))
    audit_idx = set(indices[:n_audit])

    visible: list[Any] = []
    audit: list[Any] = []
    for i, row in enumerate(ordered):
        if i in audit_idx:
            audit.append(row)
        else:
            visible.append(row)
    return visible, audit


def compute_audit_mre(
    audit_rows: Sequence[tuple[Any, float, dict]],
    predict_y: Callable[[dict], float],
) -> dict[str, Any]:
    """Compute mean relative error of a champion form against the audit slice.

    Args:
        audit_rows: sequence of (row_id, y_observed, features_dict).
        predict_y: callable(features_dict) -> y_predicted. Typically the
            champion I_model with MODEL_PARAMS bound.

    Returns:
        dict with:
            - n: number of audit rows scored.
            - mean_relative_error: arithmetic mean of |y_pred - y_obs|/|y_obs|.
            - max_relative_error: max of the same series.
            - n_failed: number of rows where prediction raised or returned
              non-finite. These are excluded from MRE statistics.
            - failure_reasons: list of up to 5 stringified failure reasons.

    Guarantees:
        - Never raises. Per-row prediction failures are caught and counted.
        - Returns n=0 / mre=None when audit_rows is empty (audit disabled).
    """
    if not audit_rows:
        return {
            "n": 0,
            "mean_relative_error": None,
            "max_relative_error": None,
            "n_failed": 0,
            "failure_reasons": [],
        }

    rel_errs: list[float] = []
    n_failed = 0
    failure_reasons: list[str] = []

    for row_id, y_obs, features in audit_rows:
        try:
            y_pred = float(predict_y(features))
        except Exception as exc:  # noqa: BLE001
            n_failed += 1
            if len(failure_reasons) < 5:
                failure_reasons.append(f"row={row_id}: {type(exc).__name__}: {exc}")
            continue
        if not math.isfinite(y_pred):
            n_failed += 1
            if len(failure_reasons) < 5:
                failure_reasons.append(f"row={row_id}: non_finite_prediction={y_pred}")
            continue
        denom = abs(float(y_obs))
        if denom == 0.0:
            n_failed += 1
            if len(failure_reasons) < 5:
                failure_reasons.append(f"row={row_id}: y_obs==0")
            continue
        rel_errs.append(abs(y_pred - float(y_obs)) / denom)

    if not rel_errs:
        return {
            "n": 0,
            "mean_relative_error": None,
            "max_relative_error": None,
            "n_failed": n_failed,
            "failure_reasons": failure_reasons,
        }
    return {
        "n": len(rel_errs),
        "mean_relative_error": sum(rel_errs) / len(rel_errs),
        "max_relative_error": max(rel_errs),
        "n_failed": n_failed,
        "failure_reasons": failure_reasons,
    }
