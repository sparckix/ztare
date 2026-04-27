"""GP-157 v5.0 Gap #3 (panel-recommended) — three-layer substrate identification.

Eliminates the gp159-class wrong-class regression at the substrate-construction
boundary. The router transitions from relying on operator-declared metadata
to "duck-typing the physics" via O(N) structural probes on the visible data.

Three layers per Gemini Pro design:

  1. **Structural probing** (this module): O(N) deterministic statistical
     tests on the target column. Routes by inherent geometry:
       - Discrete: all targets integer → number-theoretic / exact-integer
       - Dynamical/Chaotic: lag-1 autocorrelation high (and survives shuffle test)
       - Scalar-kinematic: continuous floats, IID
  2. **Automated contract generation** (push to generate_substrate.py): the
     ingestion script writes the result back into rubric.json's cage_meta,
     so the human operator's tags are no longer the source of truth.
  3. **Epistemic handshake** (`SubstrateAmbiguityError`): when probes are
     inconclusive, refuse to guess; raise the error to the LLM mutator at
     R1 so the LLM declares the physical class in its PARAMETRIC_FORM.

This module exposes the probes as pure functions + a top-level
`classify_substrate(rows) -> ClassificationResult`. Caller decides how to
act on inconclusive results (raise, log, or manually escalate).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class SubstrateClass(Enum):
    """Auto-detected physical class. Maps to cage_meta.class values
    that the FitInstrument router already understands."""

    DISCRETE = "1d_discrete"
    """All target values are integers. Routes to number-theoretic /
    exact-integer solvers. Continuous SciPy gradient descent forbidden."""

    DYNAMICAL_CHAOTIC = "time_series_chaotic"
    """High lag-1 autocorrelation that SURVIVES row-shuffle. Phase-space
    trajectory or time-series. Routes to SINDy / Chebyshev-bound
    components."""

    SCALAR_KINEMATIC = "1d"
    """Continuous floats, low autocorrelation post-shuffle. Standard
    1D paired (x, y) regression. Routes to scipy.optimize multistart."""

    AMBIGUOUS = "_ambiguous"
    """Probes disagree or signal is below confidence threshold.
    Caller should raise SubstrateAmbiguityError to force LLM
    declaration."""


@dataclass(frozen=True)
class ClassificationResult:
    """Per-substrate auto-classification with provenance.

    Carries enough information for the operator to debug a misclassification
    AND for `verify_class_consistency_with_substrate` to cross-check
    the rubric's declared class against the data's actual shape.
    """
    detected: SubstrateClass
    integer_fraction: float
    autocorrelation_raw: float
    autocorrelation_shuffled: float
    n_rows: int
    confidence: str  # "high" | "medium" | "low"
    diagnostics: list[str]


class SubstrateAmbiguityError(ValueError):
    """Raised when structural probes cannot determine the substrate class.

    The error message is designed to be passed to the LLM mutator's R1
    prompt so the LLM commits to a physical paradigm in its
    PARAMETRIC_FORM declaration. Per panel: 'route the problem back to
    the LLM mutator' rather than guessing."""


# ── Probes ───────────────────────────────────────────────────────────────


def _integer_fraction(targets: Sequence[float]) -> float:
    """Fraction of targets that are exact integers (within 1e-9 tol)."""
    if not targets:
        return 0.0
    int_count = 0
    for y in targets:
        try:
            yf = float(y)
        except (TypeError, ValueError):
            continue
        if abs(yf - round(yf)) < 1e-9:
            int_count += 1
    return int_count / len(targets)


def _lag1_autocorrelation(values: Sequence[float]) -> float:
    """Pearson lag-1 autocorrelation of `values`. Returns 0.0 when
    values has < 3 elements or zero variance."""
    n = len(values)
    if n < 3:
        return 0.0
    try:
        floats = [float(v) for v in values]
    except (TypeError, ValueError):
        return 0.0
    mean = sum(floats) / n
    centered = [v - mean for v in floats]
    var = sum(c * c for c in centered)
    if var <= 0.0:
        return 0.0
    cov = sum(centered[i] * centered[i + 1] for i in range(n - 1))
    return cov / var


def _shuffled_autocorrelation(values: Sequence[float], seed: int = 1729) -> float:
    """Lag-1 autocorrelation of a row-shuffled copy. Per panel design:
    'true dynamical data loses autocorrelation when shuffled; static
    kinematic data already has none either way'. Distinguishes data
    that's REALLY time-series-dependent from data merely sorted by
    independent variable."""
    import random
    floats = list(values)
    if not floats:
        return 0.0
    rng = random.Random(seed)
    rng.shuffle(floats)
    return _lag1_autocorrelation(floats)


# ── Top-level classifier ────────────────────────────────────────────────


# Thresholds — kept conservative. Tunable via ContractSpec extensions later.
# DYNAMICAL detection is intentionally STRICT to default ambiguous cases to
# scalar-kinematic. False positive on dynamical (routing kinematic data to
# SINDy/Chebyshev) is more catastrophic than false negative (routing chaotic
# data to scipy multistart, which then fails informatively). Per panel:
# "rather than guessing, route the problem back to the LLM mutator" via
# SubstrateAmbiguityError when probes are inconclusive.
_INTEGER_FRACTION_DISCRETE = 1.0  # require ALL integers, not just majority
_AUTOCORR_DYNAMICAL_RAW = 0.85    # |corr| > 0.85 (very strong AR(1)-class signal)
_AUTOCORR_DYNAMICAL_SHUFFLED_DELTA = 0.5  # raw must exceed shuffled by ≥ 0.5
_MIN_ROWS_FOR_AUTOCORR = 5


def classify_substrate(targets: Sequence[float]) -> ClassificationResult:
    """Run all three probes on the target column; return classification.

    `targets` is the y-column from VISIBLE_SET (or evidence.txt). The
    function is pure: no I/O, no LLM. Determined entirely by the data's
    statistical shape.

    The returned `detected` is one of SubstrateClass enum values. Caller
    inspects `confidence` and decides whether to act on the result or
    raise `SubstrateAmbiguityError`.
    """
    diagnostics: list[str] = []
    n_rows = len(targets)

    int_frac = _integer_fraction(targets)
    diagnostics.append(f"integer_fraction={int_frac:.3f}")

    autocorr_raw = _lag1_autocorrelation(targets)
    autocorr_shuffled = _shuffled_autocorrelation(targets)
    diagnostics.append(f"autocorr_raw={autocorr_raw:.3f}")
    diagnostics.append(f"autocorr_shuffled={autocorr_shuffled:.3f}")

    # Probe 1: Discrete (integer-only)
    if int_frac >= _INTEGER_FRACTION_DISCRETE and n_rows >= 3:
        diagnostics.append("DECISION: discrete (all targets integer)")
        return ClassificationResult(
            detected=SubstrateClass.DISCRETE,
            integer_fraction=int_frac,
            autocorrelation_raw=autocorr_raw,
            autocorrelation_shuffled=autocorr_shuffled,
            n_rows=n_rows,
            confidence="high",
            diagnostics=diagnostics,
        )

    # Probe 2: Dynamical/chaotic (autocorrelation survives shuffle)
    if n_rows >= _MIN_ROWS_FOR_AUTOCORR:
        autocorr_delta = abs(autocorr_raw) - abs(autocorr_shuffled)
        if abs(autocorr_raw) >= _AUTOCORR_DYNAMICAL_RAW and autocorr_delta >= _AUTOCORR_DYNAMICAL_SHUFFLED_DELTA:
            diagnostics.append(
                f"DECISION: dynamical_chaotic "
                f"(raw - shuffled = {autocorr_delta:.3f}, threshold = {_AUTOCORR_DYNAMICAL_SHUFFLED_DELTA})"
            )
            return ClassificationResult(
                detected=SubstrateClass.DYNAMICAL_CHAOTIC,
                integer_fraction=int_frac,
                autocorrelation_raw=autocorr_raw,
                autocorrelation_shuffled=autocorr_shuffled,
                n_rows=n_rows,
                confidence="high",
                diagnostics=diagnostics,
            )

    # Probe 3: Scalar-kinematic (default for continuous IID-ish or
    # sorted-monotonic data). If raw autocorrelation is high but
    # shuffle-test caused it to drop substantially, it's just sorted
    # kinematic data (e.g. y=f(x) computed on sorted x), NOT a real
    # dynamical/chaotic signal.
    if n_rows >= 3:
        confidence = "high"
        autocorr_delta = abs(autocorr_raw) - abs(autocorr_shuffled)
        if abs(autocorr_raw) >= 0.5 and autocorr_delta >= 0.3:
            # High raw autocorr but shuffle destroyed it → sorted kinematic
            confidence = "medium"
            diagnostics.append(
                "note: high raw autocorrelation but shuffle test destroyed it — "
                "sorted kinematic data, not dynamical"
            )
        diagnostics.append("DECISION: scalar_kinematic (continuous, IID-ish or sorted)")
        return ClassificationResult(
            detected=SubstrateClass.SCALAR_KINEMATIC,
            integer_fraction=int_frac,
            autocorrelation_raw=autocorr_raw,
            autocorrelation_shuffled=autocorr_shuffled,
            n_rows=n_rows,
            confidence=confidence,
            diagnostics=diagnostics,
        )

    # Fallback: too few rows to classify
    diagnostics.append(f"DECISION: ambiguous (n_rows={n_rows} below threshold)")
    return ClassificationResult(
        detected=SubstrateClass.AMBIGUOUS,
        integer_fraction=int_frac,
        autocorrelation_raw=autocorr_raw,
        autocorrelation_shuffled=autocorr_shuffled,
        n_rows=n_rows,
        confidence="low",
        diagnostics=diagnostics,
    )


def verify_class_against_data(
    declared_class: str,
    targets: Sequence[float],
) -> tuple[bool, str]:
    """Cross-check rubric's declared cage_meta.class against the data.

    Returns (consistent, diagnostic). Used by:
      - `make seal` validation
      - `verify_class_consistency_with_substrate` (orchestrator/prompt.py)

    Catches the gp159 wrong-class regression: rubric declared
    `nd_features` while data was actually 1D scalar. Now mechanical."""
    result = classify_substrate(targets)
    declared = (declared_class or "").strip().lower()
    detected = result.detected.value

    if result.detected == SubstrateClass.AMBIGUOUS:
        return True, f"data shape ambiguous (n_rows={result.n_rows}); declared class accepted"

    # nd_features substrates have data lifted into features.py and may
    # not appear in target column directly — caller responsible for
    # excluding nd_features from this check.
    if declared == detected:
        return True, f"declared class={declared} matches detected={detected} ({result.confidence})"

    # Allow some compatibility:
    #   - "1d" (declared) ≡ "1d" or "1d_discrete" (detected, since both are 1D)
    if declared == "1d" and detected in {"1d", "1d_discrete"}:
        return True, f"declared 1d compatible with detected {detected}"

    return False, (
        f"data-shape MISMATCH: declared class={declared!r} but probes detect "
        f"{detected!r} (confidence={result.confidence}). "
        f"Diagnostics: {'; '.join(result.diagnostics)}"
    )
