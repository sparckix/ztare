"""GP-125: Constant Recognition via PSLQ and mpmath.identify.

After operator search converges, the fitted coefficients are floats.
This module attempts to identify them as algebraic combinations of
known mathematical constants (π, e, γ, ln2, √2, ζ(3), etc.).

THE PRECISION TRAP (Gemini Pro, 2026-04-22):
  AdamW converges to ~7 stable digits. PSLQ needs 15-20 digits to
  avoid the "Law of Small Numbers" — where a spurious fraction like
  43π/211 fits 7 digits perfectly but diverges at digit 8.

  This module REFUSES to run on low-precision inputs. The caller
  must first run precision_polish() to grind coefficients to ≥15
  stable digits via L-BFGS in float64.

Pipeline:
  1. AdamW convergence → ~7 digits (operator_backend.py)
  2. precision_polish() → ≥15 digits (L-BFGS, float64)
  3. recognize_constants() → algebraic identifications

Usage:
    from ztare.fit.constant_recognition import (
        precision_polish, recognize_constants, full_pipeline,
    )
    # After AdamW fit:
    polished = precision_polish(adam_params, ops, terms, target, n_matrix)
    identities = recognize_constants(polished.params)

    # Or all at once:
    result = full_pipeline(adam_params, ops, terms, target, n_matrix)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import torch


# ---------------------------------------------------------------------------
# Constants basis for PSLQ
# ---------------------------------------------------------------------------

def _build_constants_basis() -> dict[str, object]:
    """Build the basis of mathematical constants for PSLQ probing.

    Returns mpmath high-precision values keyed by LaTeX-style names.
    """
    from mpmath import mp, mpf, pi, euler, log, sqrt, zeta, catalan

    return {
        "1": mpf(1),
        "pi": pi,
        "pi^2": pi ** 2,
        "1/pi": 1 / pi,
        "e": mp.e,
        "1/e": 1 / mp.e,
        "gamma": euler,         # Euler-Mascheroni
        "ln2": log(2),
        "ln(pi)": log(pi),
        "sqrt2": sqrt(2),
        "sqrt3": sqrt(3),
        "sqrt5": sqrt(5),
        "1/sqrt(2pi)": 1 / sqrt(2 * pi),
        "zeta3": zeta(3),       # Apéry's constant
        "catalan": catalan,     # Catalan's constant
        "1/(2pi)": 1 / (2 * pi),
        "2pi": 2 * pi,
        "pi/2": pi / 2,
        "pi/4": pi / 4,
        "sqrt(2pi)": sqrt(2 * pi),
        "ln(2pi)": log(2 * pi),
    }


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PolishResult:
    """Result of L-BFGS precision polishing."""
    params: dict[str, float]
    loss_before: float
    loss_after: float
    stable_digits: int
    n_steps: int
    time_seconds: float


@dataclass
class ConstantID:
    """A single constant identification attempt."""
    param_name: str
    value: float
    identity: str | None          # e.g., "sqrt(2)*pi/3"
    relation: list[int] | None    # PSLQ integer relation
    basis_used: list[str] | None  # which constants in the relation
    confidence: str               # "high", "medium", "low", "none"
    stable_digits: int
    note: str = ""


@dataclass
class RecognitionResult:
    """Full constant recognition result."""
    identifications: list[ConstantID] = field(default_factory=list)
    precision_sufficient: bool = False
    min_stable_digits: int = 0
    time_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Precision polish (L-BFGS in float64)
# ---------------------------------------------------------------------------

def precision_polish(
    params_init: dict[str, float] | torch.Tensor,
    make_hamiltonian_fn,
    ops: dict[str, torch.Tensor],
    terms: list[str],
    target: torch.Tensor | list[float],
    n_steps: int = 2000,
    verbose: bool = True,
) -> PolishResult:
    """Grind AdamW-converged params to ≥15 stable digits via L-BFGS.

    L-BFGS is a quasi-Newton method — it uses curvature information
    (approximate Hessian) instead of just gradients. Near a minimum,
    it converges quadratically vs AdamW's linear convergence.

    Args:
        params_init: Initial params from AdamW (dict or tensor).
        make_hamiltonian_fn: Function(params, ops, terms) → H matrix.
        ops: Operator basis dict from build_operators().
        terms: List of term names.
        target: Target spectrum tensor.
        n_steps: Max L-BFGS iterations (usually converges in <500).
        verbose: Print progress.
    """
    device = ops[terms[0]].device
    dtype = torch.float64  # Always float64 for polish

    # Convert ops to float64 if needed
    ops_64 = {k: v.to(dtype=dtype) for k, v in ops.items()}

    # Convert target
    if isinstance(target, list):
        target_64 = torch.tensor(target, device=device, dtype=dtype)
    else:
        target_64 = target.to(dtype=dtype)
    n_match = len(target_64)

    # Initialize from AdamW result
    if isinstance(params_init, dict):
        p_vals = [params_init[t] for t in terms]
    elif isinstance(params_init, torch.Tensor):
        p_vals = params_init.tolist()
    else:
        p_vals = list(params_init)

    params = torch.tensor(p_vals, device=device, dtype=dtype, requires_grad=True)

    # Compute initial loss
    with torch.no_grad():
        H0 = make_hamiltonian_fn(params, ops_64, terms)
        eigs0, _ = torch.linalg.eigh(H0)
        loss_before = float(torch.mean((eigs0[:n_match] - target_64) ** 2))

    if verbose:
        print(f"  Polish: {len(terms)} params, loss_before={loss_before:.10f}")

    t0 = time.time()

    # L-BFGS closure
    optimizer = torch.optim.LBFGS(
        [params],
        lr=1.0,
        max_iter=20,
        line_search_fn="strong_wolfe",
        tolerance_grad=1e-15,
        tolerance_change=1e-16,
    )

    best_loss = loss_before
    best_params = params.detach().clone()
    loss_history = []

    for epoch in range(n_steps // 20):
        def closure():
            optimizer.zero_grad()
            H = make_hamiltonian_fn(params, ops_64, terms)
            eigs, _ = torch.linalg.eigh(H)
            pred = eigs[:n_match]
            loss = torch.mean((pred - target_64) ** 2)

            # Light Coulomb repulsion (less aggressive than AdamW phase)
            n_rep = min(2 * n_match, H.shape[0])
            diffs = eigs[:n_rep].unsqueeze(0) - eigs[:n_rep].unsqueeze(1)
            mask = 1.0 - torch.eye(n_rep, device=device, dtype=dtype)
            repulsion = torch.sum(mask / (diffs.abs() + 1e-8)) * 1e-10
            total = loss + repulsion

            if not torch.isnan(total):
                total.backward()
            return total

        loss_val = optimizer.step(closure)

        if loss_val is not None and not torch.isnan(loss_val):
            lv = float(loss_val)
            loss_history.append(lv)
            if lv < best_loss:
                best_loss = lv
                best_params = params.detach().clone()

        # Convergence check: if loss hasn't improved in 10 epochs, stop
        if len(loss_history) > 10:
            recent = loss_history[-10:]
            if max(recent) - min(recent) < 1e-15:
                if verbose:
                    print(f"  Polish converged at epoch {epoch}")
                break

        if verbose and epoch % 10 == 0:
            print(f"  Polish epoch {epoch}: loss={best_loss:.15e}")

    elapsed = time.time() - t0

    # Estimate stable digits by comparing to loss_before
    if best_loss > 0:
        stable_digits = max(0, int(-np.log10(best_loss + 1e-30)))
    else:
        stable_digits = 16  # float64 limit

    result_params = {terms[i]: float(best_params[i]) for i in range(len(terms))}

    if verbose:
        print(f"  Polish done: loss={best_loss:.15e}, "
              f"~{stable_digits} stable digits, {elapsed:.1f}s")
        for t in terms:
            print(f"    {t:>8} = {result_params[t]:.15f}")

    return PolishResult(
        params=result_params,
        loss_before=loss_before,
        loss_after=best_loss,
        stable_digits=stable_digits,
        n_steps=epoch + 1 if 'epoch' in dir() else n_steps,
        time_seconds=round(elapsed, 1),
    )


# ---------------------------------------------------------------------------
# Constant recognition
# ---------------------------------------------------------------------------

def _estimate_stable_digits(value: float, loss: float) -> int:
    """Estimate how many digits of a coefficient are meaningful.

    Heuristic: if MSE loss is L, each coefficient is known to
    roughly -log10(sqrt(L)) digits, clamped to float64 range.
    """
    if loss <= 0:
        return 15
    digits = max(0, int(-0.5 * np.log10(loss + 1e-30)))
    return min(digits, 15)


def recognize_single(
    value: float,
    stable_digits: int,
    constants_basis: dict | None = None,
    maxcoeff: int = 1000,
    verbose: bool = False,
) -> ConstantID:
    """Attempt to identify a single float as a constant expression.

    Uses two strategies:
    1. mpmath.identify() — pattern matching against known forms
    2. PSLQ — integer relation detection against constants basis

    Args:
        value: The coefficient to identify.
        stable_digits: How many digits are reliable.
        constants_basis: Dict of name → mpmath value. Defaults to standard basis.
        maxcoeff: Maximum integer coefficient for PSLQ relations.
        verbose: Print details.
    """
    from mpmath import mp, mpf, pslq, identify

    # Precision trap guard
    if stable_digits < 8:
        return ConstantID(
            param_name="",
            value=value,
            identity=None,
            relation=None,
            basis_used=None,
            confidence="none",
            stable_digits=stable_digits,
            note=f"Only {stable_digits} stable digits — below PSLQ minimum (8). "
                 "Run precision_polish() first.",
        )

    # Set mpmath precision based on available digits
    mp.dps = max(stable_digits + 10, 30)

    x = mpf(value)

    if constants_basis is None:
        constants_basis = _build_constants_basis()

    # --- Strategy 1: mpmath.identify() ---
    # identify() evals constant names in mpmath namespace,
    # so pass names that mpmath can resolve
    identify_constants = ["pi", "euler", "log(2)", "catalan"]

    identify_result = identify(
        x,
        constants=identify_constants,
        tol=mpf(10) ** (-(stable_digits - 2)),
        maxcoeff=maxcoeff,
        full=True,
    )

    best_identify = None
    if identify_result:
        # Pick simplest (shortest string) match
        best_identify = min(identify_result, key=len)
        if verbose:
            print(f"  identify({value:.10f}) = {best_identify}")

    # --- Strategy 2: PSLQ against constant basis ---
    # Try progressively larger subsets of the basis
    pslq_result = None
    pslq_basis_names = None

    # Core basis: the most common constants
    basis_groups = [
        ["1", "pi", "e", "gamma", "ln2"],
        ["1", "pi", "pi^2", "sqrt2", "sqrt3"],
        ["1", "pi", "e", "gamma", "ln2", "sqrt2", "zeta3"],
        ["1", "pi", "pi^2", "1/pi", "e", "gamma", "ln2",
         "sqrt2", "sqrt3", "sqrt5", "zeta3", "catalan"],
    ]

    for group in basis_groups:
        basis_vals = [constants_basis[name] for name in group]
        vec = [x] + basis_vals

        rel = pslq(vec, maxcoeff=maxcoeff, tol=mpf(10) ** (-(stable_digits - 3)))

        if rel is not None:
            # rel[0]*x + rel[1]*c1 + rel[2]*c2 + ... = 0
            # So x = -(rel[1]*c1 + rel[2]*c2 + ...) / rel[0]
            if rel[0] != 0:
                pslq_result = rel
                pslq_basis_names = ["x"] + group
                if verbose:
                    terms_str = " + ".join(
                        f"{c}*{n}" for c, n in zip(rel, pslq_basis_names)
                        if c != 0
                    )
                    print(f"  PSLQ: {terms_str} = 0")
                break

    # --- Scoring: Occam's razor via description length ---
    # Score both strategies independently, pick the one with shortest
    # description length. PSLQ's "(1/4)*pi" and identify's "pi/4" agree;
    # PSLQ's "0.073*1 + 0.218*pi - 0.155*e + ..." loses to identify's
    # "sqrt(2)" because the latter is shorter (simpler).
    pslq_confidence = "none"
    pslq_identity = None
    identify_confidence = "none"
    identify_identity = None

    if pslq_result is not None:
        c0 = pslq_result[0]
        expr_parts = []
        for i, name in enumerate(pslq_basis_names[1:], 1):
            ci = pslq_result[i]
            if ci == 0:
                continue
            coeff = -ci / c0 if c0 != 0 else ci
            if coeff == 1:
                expr_parts.append(name)
            elif coeff == -1:
                expr_parts.append(f"-{name}")
            elif coeff == int(coeff):
                expr_parts.append(f"{int(coeff)}*{name}")
            else:
                from fractions import Fraction
                frac = Fraction(int(-ci), int(c0)).limit_denominator(10000)
                expr_parts.append(f"({frac})*{name}")

        pslq_identity = " + ".join(expr_parts) if expr_parts else None

        max_c = max(abs(c) for c in pslq_result)
        n_nonzero = sum(1 for c in pslq_result if c != 0)

        if max_c <= 10 and n_nonzero <= 3 and stable_digits >= 12:
            pslq_confidence = "high"
        elif max_c <= 50 and n_nonzero <= 4 and stable_digits >= 10:
            pslq_confidence = "medium"
        elif stable_digits >= 8:
            pslq_confidence = "low"

    if best_identify is not None:
        identify_identity = best_identify
        if stable_digits >= 12:
            identify_confidence = "medium"
        elif stable_digits >= 8:
            identify_confidence = "low"

    # Occam selection: among candidates with confidence >= "low",
    # pick the one with shorter description length (simpler expression).
    # If tied on length, prefer higher confidence.
    candidates = []
    if pslq_identity and pslq_confidence != "none":
        candidates.append(("pslq", pslq_identity, pslq_confidence))
    if identify_identity and identify_confidence != "none":
        candidates.append(("identify", identify_identity, identify_confidence))

    rank = {"high": 3, "medium": 2, "low": 1, "none": 0}

    if candidates:
        # Sort by: description length ASC, then confidence DESC
        candidates.sort(key=lambda c: (len(c[1]), -rank[c[2]]))
        _, identity_str, confidence = candidates[0]
    else:
        identity_str = None
        confidence = "none"

    return ConstantID(
        param_name="",
        value=value,
        identity=identity_str,
        relation=pslq_result,
        basis_used=pslq_basis_names,
        confidence=confidence,
        stable_digits=stable_digits,
    )


def recognize_constants(
    params: dict[str, float],
    loss: float = 0.0,
    stable_digits_override: int | None = None,
    verbose: bool = True,
) -> RecognitionResult:
    """Recognize algebraic constants in a dict of fitted parameters.

    Args:
        params: Dict of param_name → float value.
        loss: The MSE loss at convergence (used to estimate precision).
        stable_digits_override: Override automatic digit estimation.
        verbose: Print results.
    """
    t0 = time.time()

    constants_basis = _build_constants_basis()

    identifications = []
    min_digits = 99

    for name, value in params.items():
        if stable_digits_override is not None:
            digits = stable_digits_override
        else:
            digits = _estimate_stable_digits(value, loss)

        min_digits = min(min_digits, digits)

        if verbose:
            print(f"\n  Recognizing {name} = {value:.15f} ({digits} stable digits)")

        cid = recognize_single(
            value=value,
            stable_digits=digits,
            constants_basis=constants_basis,
            verbose=verbose,
        )
        cid.param_name = name
        identifications.append(cid)

        if verbose:
            if cid.identity:
                print(f"    => {cid.identity} (confidence: {cid.confidence})")
            else:
                print(f"    => no identification (confidence: {cid.confidence})")

    elapsed = time.time() - t0

    return RecognitionResult(
        identifications=identifications,
        precision_sufficient=min_digits >= 8,
        min_stable_digits=min_digits,
        time_seconds=round(elapsed, 1),
    )


# ---------------------------------------------------------------------------
# Full pipeline: polish + recognize
# ---------------------------------------------------------------------------

def full_pipeline(
    params_init: dict[str, float] | torch.Tensor,
    make_hamiltonian_fn,
    ops: dict[str, torch.Tensor],
    terms: list[str],
    target: torch.Tensor | list[float],
    polish_steps: int = 2000,
    verbose: bool = True,
) -> tuple[PolishResult, RecognitionResult]:
    """Run precision polish then constant recognition.

    This is the recommended entry point. It:
    1. Takes AdamW-converged params (~7 digits)
    2. Runs L-BFGS polish in float64 (~15 digits)
    3. Runs PSLQ + identify on polished params
    4. Returns both results

    Args:
        params_init: AdamW-converged params.
        make_hamiltonian_fn: Function(params, ops, terms) → H.
        ops: Operator basis dict.
        terms: Term names.
        target: Target spectrum.
        polish_steps: Max L-BFGS iterations.
        verbose: Print progress.
    """
    if verbose:
        print("=" * 60)
        print("GP-125 Constant Recognition Pipeline")
        print("=" * 60)

    # Stage 1: Precision polish
    if verbose:
        print("\n--- Stage 1: L-BFGS Precision Polish (float64) ---")

    polish = precision_polish(
        params_init=params_init,
        make_hamiltonian_fn=make_hamiltonian_fn,
        ops=ops,
        terms=terms,
        target=target,
        n_steps=polish_steps,
        verbose=verbose,
    )

    # Stage 2: Constant recognition
    if verbose:
        print("\n--- Stage 2: PSLQ + identify ---")

    recognition = recognize_constants(
        params=polish.params,
        loss=polish.loss_after,
        verbose=verbose,
    )

    # Summary
    if verbose:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print(f"  Polish: {polish.loss_before:.6e} → {polish.loss_after:.6e} "
              f"(~{polish.stable_digits} digits)")
        print(f"  Precision sufficient: {recognition.precision_sufficient}")
        n_found = sum(1 for c in recognition.identifications if c.identity)
        n_high = sum(1 for c in recognition.identifications
                     if c.confidence == "high")
        print(f"  Identifications: {n_found}/{len(recognition.identifications)} "
              f"({n_high} high-confidence)")
        for cid in recognition.identifications:
            if cid.identity:
                print(f"    {cid.param_name} = {cid.identity} "
                      f"[{cid.confidence}]")
        print("=" * 60)

    return polish, recognition
