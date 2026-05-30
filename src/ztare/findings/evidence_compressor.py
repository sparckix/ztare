"""GP-098 Evidence Compressor: Variance-Stabilizing Transform Enumeration.

Enumerates three exact-inverse transforms on evidence Z values:
  1. identity  — Z' = Z           (inverse: Z = Z')
  2. log       — Z' = log(Z)      (inverse: Z = exp(Z'))
  3. sqrt      — Z' = sqrt(Z)     (inverse: Z = Z'**2)

Each transform has a domain guard; transforms that violate the guard are
skipped (not shifted).  The holdout adjudicates which transform produces
the best candidate in *original* coordinates.

Spec: GP-098 (internal seam)
Seam: GP-098 (internal seam)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Minimum Z for the log transform.  log(1e-10) = -23, which distorts
# curve_fit initialisation (default p0 = [1, 1, ...]).
Z_FLOOR: float = 1e-6


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass
class TransformedEvidence:
    """Evidence after applying a VST."""

    transform_name: str  # "identity" | "log" | "sqrt"
    evidence: list[tuple]  # transformed (X1, ..., Z') tuples
    original_evidence: list[tuple]  # original (X1, ..., Z) tuples
    inverse_fn: Callable[[float], float]  # Z' -> Z
    forward_fn: Callable[[float], float]  # Z -> Z'


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

_TRANSFORMS: list[
    tuple[str, Callable[[float], float], Callable[[float], float]]
] = [
    ("identity", lambda z: z, lambda z_prime: z_prime),
    ("log", lambda z: math.log(z), lambda z_prime: math.exp(z_prime)),
    ("sqrt", lambda z: math.sqrt(z), lambda z_prime: z_prime ** 2),
]


def _domain_ok(name: str, z_values: list[float]) -> bool:
    """Check whether all Z values satisfy the transform's domain guard."""
    if name == "identity":
        return True
    if name == "log":
        return all(z > Z_FLOOR for z in z_values)
    if name == "sqrt":
        return all(z >= 0 for z in z_values)
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def enumerate_transforms(
    evidence: list[tuple],
    *,
    verbose: bool = True,
) -> list[TransformedEvidence]:
    """Return a list of TransformedEvidence for each valid transform.

    Args:
        evidence: List of tuples (x1, x2, ..., z).  Z is always last.
        verbose: Print progress.

    Returns:
        List of TransformedEvidence objects (1-3 entries).  Identity is
        always first.

    Note:
        This function deliberately does NOT accept variable names or any
        domain metadata.  Conditioning transforms on variable names would
        be oracle contamination (e.g. skipping log because a variable is
        named "concentration").
    """
    if not evidence:
        return [
            TransformedEvidence(
                transform_name="identity",
                evidence=[],
                original_evidence=[],
                inverse_fn=lambda z: z,
                forward_fn=lambda z: z,
            )
        ]

    z_values = [float(e[-1]) for e in evidence]
    results: list[TransformedEvidence] = []

    for name, forward_fn, inverse_fn in _TRANSFORMS:
        if not _domain_ok(name, z_values):
            if verbose:
                print(f"    GP-098: skipping {name} transform (domain guard)")
            continue

        transformed = []
        valid = True
        for point in evidence:
            z = float(point[-1])
            try:
                z_prime = forward_fn(z)
            except (ValueError, ArithmeticError):
                valid = False
                break
            if not math.isfinite(z_prime):
                valid = False
                break
            transformed.append(tuple(list(point[:-1]) + [z_prime]))

        if not valid:
            if verbose:
                print(
                    f"    GP-098: skipping {name} transform "
                    f"(non-finite Z' produced)"
                )
            continue

        results.append(
            TransformedEvidence(
                transform_name=name,
                evidence=transformed,
                original_evidence=list(evidence),
                inverse_fn=inverse_fn,
                forward_fn=forward_fn,
            )
        )
        if verbose:
            z_primes = [float(t[-1]) for t in transformed]
            print(
                f"    GP-098: {name} transform OK "
                f"(Z' range [{min(z_primes):.4f}, {max(z_primes):.4f}])"
            )

    return results


def inverse_transform_predictions(
    predictions: list[float],
    transform: TransformedEvidence,
    *,
    verbose: bool = False,
) -> list[float]:
    """Apply the inverse transform to a list of Z' predictions.

    Returns Z values in original coordinates.
    """
    result = []
    neg_count = 0
    for z_prime in predictions:
        if transform.transform_name == "sqrt" and z_prime < 0:
            neg_count += 1
        z = transform.inverse_fn(z_prime)
        result.append(z)
    if neg_count > 0 and verbose:
        print(
            f"    GP-098 WARNING: sqrt inverse applied to {neg_count} "
            f"negative Z' values — squaring loses sign information"
        )
    return result


def evaluate_holdout_in_original(
    predictions_transformed: list[float],
    holdout_z_original: list[float],
    transform: TransformedEvidence,
) -> float:
    """Evaluate predictions against holdout in original coordinates.

    Args:
        predictions_transformed: Z' values predicted by the engine.
        holdout_z_original: Z values from the holdout (original coords).
        transform: The TransformedEvidence used.

    Returns:
        Max absolute residual in original coordinates.
    """
    if len(predictions_transformed) != len(holdout_z_original):
        return float("inf")

    z_pred = inverse_transform_predictions(predictions_transformed, transform)
    max_res = 0.0
    for pred, obs in zip(z_pred, holdout_z_original):
        if not math.isfinite(pred):
            return float("inf")
        max_res = max(max_res, abs(pred - obs))
    return max_res
