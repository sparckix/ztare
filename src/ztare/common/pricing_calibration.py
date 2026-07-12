"""Pricing calibration wrapper for information-yield identification bits.

This module is a WRAPPER around ``identification_bits`` from
``ztare.common.information_yield_pricing`` — one door preserved.  It does not
reimplement entropy; it adds three production corrections:

1. **Deduplication** — ``dedup_predictive_mass`` collapses behaviorally-identical
   committee members before the entropy call.  Enumerator duplication (e.g. a
   population generator that emits the same fingerprint twice) inflates the
   apparent partition count and therefore inflates quoted bits.  Dedup removes
   that artifact before pricing.

2. **Unknown-model mass** — ``unknown_model_mass`` (default: env
   ``ZTARE_UNKNOWN_MODEL_MASS``, fallback 0.2) reserves probability mass for
   unrepresented models.  Quoted bits are scaled by ``(1 - mass)`` so the caller
   never claims full identification while unknown models still carry mass.

3. **Calibration ledger** — ``record_calibration`` appends a row to
   ``workspace/pricing_calibration.jsonl`` comparing quoted bits with the
   realized survivor-reduction fraction from the same run.  ``calibration_report``
   reads the ledger and prints the quoted-vs-realized comparison.  Both functions
   are honest on a tiny corpus: they surface the gap rather than hiding it.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Hashable, Sequence

from ztare.common.information_yield_pricing import identification_bits  # noqa: F401 — re-exported


_DEFAULT_UNKNOWN_MASS = 0.2
_LEDGER_NAME = "pricing_calibration.jsonl"


# ---------------------------------------------------------------------------
# (a) dedup_predictive_mass
# ---------------------------------------------------------------------------

def dedup_predictive_mass(
    survivor_predictions: Sequence[tuple[Any, Hashable]],
) -> list[tuple[Any, Hashable]]:
    """Collapse behaviorally-identical committee members before entropy.

    ``survivor_predictions`` is a sequence of ``(member, prediction)`` pairs
    where ``prediction`` is the member's prediction for the experiment at hand
    (any Hashable).  Members that share the same prediction fingerprint count as
    one representative; the others are dropped.

    This guards against enumerator duplication: if the population generator
    emits the same behavioral fingerprint twice, the raw partition entropy is
    inflated because both copies are in the same cell but the denominator is
    doubled.  After dedup the denominator equals the number of *distinct*
    behavioral classes, and entropy is over that collapsed partition.

    Returns a list of ``(member, prediction)`` pairs with one representative per
    unique prediction value.  The representative is the first occurrence.
    """
    seen: dict[Hashable, Any] = {}
    result: list[tuple[Any, Hashable]] = []
    for member, pred in survivor_predictions:
        key = _stable_key(pred)
        if key not in seen:
            seen[key] = member
            result.append((member, pred))
    return result


def _stable_key(pred: Any) -> Hashable:
    """Return a stable, hashable key for a prediction value.

    Lists/dicts are JSON-serialized so nested structures dedup correctly.
    """
    if isinstance(pred, (str, int, float, bool, type(None))):
        return pred
    try:
        return hashlib.md5(json.dumps(pred, sort_keys=True, default=str).encode()).hexdigest()
    except Exception:
        return repr(pred)


# ---------------------------------------------------------------------------
# (b) unknown_model_mass scaling
# ---------------------------------------------------------------------------

def _get_unknown_mass() -> float:
    raw = os.environ.get("ZTARE_UNKNOWN_MODEL_MASS", "")
    if raw.strip():
        try:
            v = float(raw)
            if 0.0 <= v < 1.0:
                return v
        except ValueError:
            pass
    return _DEFAULT_UNKNOWN_MASS


def quoted_bits(
    cells: "dict[Hashable, list]",
    committee_size: int,
    unknown_model_mass: float | None = None,
) -> float:
    """Identification bits scaled by ``(1 - unknown_model_mass)``.

    Args:
        cells: Partition of dedup'd committee members by prediction value.
        committee_size: Number of dedup'd members (``len`` of the flattened cells).
        unknown_model_mass: Fraction of probability reserved for unrepresented
            models.  ``None`` reads ``ZTARE_UNKNOWN_MODEL_MASS`` env var,
            falling back to 0.2.

    Returns:
        Scaled bits in ``[0, log2(committee_size) * (1 - mass)]``.
    """
    mass = unknown_model_mass if unknown_model_mass is not None else _get_unknown_mass()
    raw_bits = identification_bits(cells, committee_size)
    return raw_bits * (1.0 - mass)


# ---------------------------------------------------------------------------
# (c) calibration ledger
# ---------------------------------------------------------------------------

def record_calibration(
    project_dir: str | Path,
    quoted_bits_value: float,
    realized_survivor_reduction: float,
) -> None:
    """Append a calibration row to ``workspace/pricing_calibration.jsonl``.

    Args:
        project_dir: Path to the project root (e.g. ``projects/arc3_ls20_gov``).
        quoted_bits_value: The ``quoted_bits()`` value used for this pricing call.
        realized_survivor_reduction: Fraction of committee members eliminated by
            the experiment (``1 - |survivors| / |prior_committee|``).  Must be
            in ``[0, 1]``.
    """
    workspace = Path(project_dir) / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    ledger = workspace / _LEDGER_NAME
    row = {
        "quoted_bits": round(float(quoted_bits_value), 8),
        "realized_survivor_reduction": round(float(realized_survivor_reduction), 8),
        # ponytail: no timestamp — callers who need it can add; avoids import
    }
    with ledger.open("a") as f:
        f.write(json.dumps(row) + "\n")


def calibration_report(project_dir: str | Path) -> dict[str, object]:
    """Compare quoted bits vs realized survivor reduction across all ledger rows.

    Returns a dict with:
        ``n_rows``: number of calibration rows,
        ``mean_quoted_bits``: arithmetic mean of quoted bits,
        ``mean_realized_reduction``: arithmetic mean of realized reductions,
        ``overquote_fraction``: fraction of rows where quoted > realized
          (positive means the pricing is systematically optimistic; expected
          on a tiny corpus),
        ``honest_note``: plain-English caveat about corpus size.

    Honest on a tiny corpus: the report surfaces the gap rather than hiding it.
    """
    ledger = Path(project_dir) / "workspace" / _LEDGER_NAME
    if not ledger.exists():
        return {"n_rows": 0, "honest_note": "no calibration rows recorded yet"}

    rows: list[dict] = []
    with ledger.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    if not rows:
        return {"n_rows": 0, "honest_note": "ledger exists but contains no valid rows"}

    n = len(rows)
    mean_q = sum(r["quoted_bits"] for r in rows) / n
    mean_r = sum(r["realized_survivor_reduction"] for r in rows) / n
    overquote = sum(1 for r in rows if r["quoted_bits"] > r["realized_survivor_reduction"]) / n

    note = (
        f"calibrated on {n} row(s) — "
        + ("statistically thin; treat as directional only" if n < 30 else "reasonable sample")
    )
    return {
        "n_rows": n,
        "mean_quoted_bits": round(mean_q, 6),
        "mean_realized_reduction": round(mean_r, 6),
        "overquote_fraction": round(overquote, 4),
        "honest_note": note,
    }
