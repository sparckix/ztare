"""GP-144 Gate G2 — PSLQ False-Positive Audit.

Claim-pipeline gate that audits a proposed PSLQ-derived integer-relation
closed-form claim BEFORE it is promoted to a Lean theorem. PSLQ has a
non-zero false-positive rate that scales with (precision_bits, dictionary
size, relation dimension); insufficient bit budget + large dictionaries
produce spurious integer relations with probability approaching 1.

This gate enforces three deterministic checks:

  1. Bit-budget compliance (decision-critical):
       precision_bits >= dim * log2(dict_size) + safety_margin
     Refuses any claim whose declared precision is below this bound.

  2. Perturbation stability:
       Inject Gaussian noise at the rubric-declared margin_of_safety
       envelope. Re-run PSLQ. If the identified relation CHANGES under
       noise within the declared envelope, the relation is not robust
       to measurement uncertainty and is rejected.

  3. Dictionary ablation:
       Re-run PSLQ with each subset-of-one constant dropped from the
       candidate dictionary. A real relation collapses cleanly to a
       minimal subset. A false positive appears only when the maximal
       dictionary is used.

Registration per GP-086: this gate is in src/ztare/gates/, not embedded
in any solver. Callable from the Phase-D INV-3 writer when assembling
test_model.py for a conjecture-refinement substrate, OR directly from
any script that wants to audit a PSLQ-derived closed form.

Return shape matches src/ztare/gates/global_gates._gate convention: dict
with name / passed / actual / threshold / reason / extra. Mutator-view
filter strips raw metric values per GP-144 mutator-visibility boundary.

Dependencies: mpmath (arbitrary-precision arithmetic + PSLQ), numpy.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Optional


GATE_ID = "pslq_falsity_audit"
PRODUCER = "GP-144.G2"
DEFAULT_SAFETY_MARGIN_BITS = 20
DEFAULT_PERTURBATION_TRIALS = 5


# ---------------------------------------------------------------------------
# Bit-budget compliance (decision-critical)
# ---------------------------------------------------------------------------

def required_precision_bits(
    dim: int,
    dict_size: int,
    safety_margin_bits: int = DEFAULT_SAFETY_MARGIN_BITS,
) -> float:
    """Minimum precision bits required to keep PSLQ's intrinsic false-positive
    rate below 2^-safety_margin_bits.

    The false-positive heuristic: for an integer relation of dimension `dim`
    searched against a dictionary of `dict_size` real constants, a random
    floating-point vector will find a spurious relation with probability
    approximately (dict_size^dim) / 2^precision_bits. Setting this below
    2^-safety_margin_bits gives:

        precision_bits >= dim * log2(dict_size) + safety_margin_bits
    """
    return float(dim) * math.log2(max(dict_size, 2)) + float(safety_margin_bits)


def bit_budget_compliant(
    precision_bits: float,
    dim: int,
    dict_size: int,
    safety_margin_bits: int = DEFAULT_SAFETY_MARGIN_BITS,
) -> bool:
    return precision_bits >= required_precision_bits(
        dim, dict_size, safety_margin_bits
    )


# ---------------------------------------------------------------------------
# Hash-commitment verification (shared pattern with wasserstein_persistence)
# ---------------------------------------------------------------------------

def _verify_hash_commitment(claim: dict[str, Any]) -> bool:
    committed = claim.get("sha256_commitment")
    if not committed:
        return False
    payload = {k: v for k, v in claim.items() if k != "sha256_commitment"}
    computed = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    return computed == committed


# ---------------------------------------------------------------------------
# PSLQ re-verification at rubric-declared precision
# ---------------------------------------------------------------------------

def evaluate_relation_at_precision(
    relation_coefficients: list[int],
    constant_values: list[float],
    precision_bits: int,
) -> dict[str, Any]:
    """Evaluate sum(c_i * k_i) under declared precision. Returns the residual
    magnitude in the same precision regime. A real integer relation has
    residual near zero; a spurious relation has residual at the noise floor.
    """
    import mpmath as mp
    mp.mp.prec = int(precision_bits)
    if len(relation_coefficients) != len(constant_values):
        return {
            "residual": None,
            "error": "relation / constants length mismatch",
        }
    total = mp.mpf(0)
    for c, k in zip(relation_coefficients, constant_values):
        total += mp.mpf(int(c)) * mp.mpf(str(k))
    residual_mag = abs(float(total))
    return {
        "residual": residual_mag,
        "residual_log2": (math.log2(residual_mag) if residual_mag > 0 else float("-inf")),
        "precision_bits": int(precision_bits),
    }


# ---------------------------------------------------------------------------
# Perturbation stability test
# ---------------------------------------------------------------------------

def perturbation_stability_test(
    relation_coefficients: list[int],
    constant_values: list[float],
    perturbation_sigma: float,
    precision_bits: int,
    n_trials: int = DEFAULT_PERTURBATION_TRIALS,
    max_coefficient: int = 10_000,
) -> dict[str, Any]:
    """Inject Gaussian noise at perturbation_sigma to each constant, re-run
    PSLQ at declared precision, check whether the identified relation is the
    same as the claimed one (or a rational multiple of it).

    Returns {trials_run, trials_matching_claimed_relation, stable:bool}.
    Stable = claimed relation recovered on ALL trials.
    """
    import mpmath as mp
    import numpy as np
    mp.mp.prec = int(precision_bits)
    rng = np.random.default_rng(seed=17)  # deterministic; same noise pattern across gate runs
    claimed_tuple = tuple(int(c) for c in relation_coefficients)
    matches = 0
    sample_results: list[list[int]] = []

    for trial in range(n_trials):
        perturbed = [
            float(k) + float(rng.normal(0, perturbation_sigma))
            for k in constant_values
        ]
        mp_vec = [mp.mpf(str(v)) for v in perturbed]
        try:
            pslq_result = mp.pslq(mp_vec, tol=mp.mpf(2) ** (-int(precision_bits * 0.6)),
                                  maxcoeff=max_coefficient, maxsteps=100)
        except Exception:
            pslq_result = None
        if pslq_result is None:
            sample_results.append([])
            continue
        result_tuple = tuple(int(c) for c in pslq_result)
        sample_results.append(list(result_tuple))
        if result_tuple == claimed_tuple or result_tuple == tuple(-c for c in claimed_tuple):
            matches += 1

    return {
        "trials_run": n_trials,
        "trials_matching_claimed_relation": matches,
        "stable": matches == n_trials,
        "sample_results": sample_results[:3],  # keep small; first 3 for debugging
    }


# ---------------------------------------------------------------------------
# Dictionary ablation test
# ---------------------------------------------------------------------------

def dictionary_ablation_test(
    relation_coefficients: list[int],
    constant_values: list[float],
    constant_names: list[str],
    precision_bits: int,
    max_coefficient: int = 10_000,
) -> dict[str, Any]:
    """For each single-constant drop, re-run PSLQ on the reduced dictionary.
    A real relation either collapses (some coefficients drop to 0 when a
    non-decision-critical constant is removed) OR fails cleanly (no relation
    found when a decision-critical constant is removed). A false positive often
    persists with a different, arbitrary coefficient pattern.

    Returns per-drop: {dropped_constant, relation_found, coefficients_if_found,
    classified_as}. classified_as in:
      - "consistent_collapse" — decision-critical constant dropped; no relation
        found OR relation collapses to the reduced natural form.
      - "consistent_preserved" — non-decision-critical constant dropped; original
        relation's non-dropped coefficients unchanged (zero for the dropped
        slot implied).
      - "suspicious_rewrite" — relation found with DIFFERENT coefficient
        pattern. Suggests false-positive: the original relation was
        coincidental.
    """
    import mpmath as mp
    mp.mp.prec = int(precision_bits)
    results = []
    suspicious = 0
    for drop_idx, drop_name in enumerate(constant_names):
        reduced_values = [v for i, v in enumerate(constant_values) if i != drop_idx]
        original_nonzero_at_dropped = int(relation_coefficients[drop_idx]) != 0
        mp_vec = [mp.mpf(str(v)) for v in reduced_values]
        try:
            pslq_result = mp.pslq(mp_vec, tol=mp.mpf(2) ** (-int(precision_bits * 0.6)),
                                  maxcoeff=max_coefficient, maxsteps=100)
        except Exception:
            pslq_result = None
        if pslq_result is None:
            classification = "consistent_collapse" if original_nonzero_at_dropped else "no_relation_after_drop"
            coef_found = None
        else:
            coef_found = [int(c) for c in pslq_result]
            if original_nonzero_at_dropped:
                # Original had a non-zero coefficient at dropped_idx; now a new
                # relation exists on the reduced dict. Is it the same up to
                # dropping the dropped slot?
                expected = [
                    int(c) for i, c in enumerate(relation_coefficients)
                    if i != drop_idx
                ]
                if tuple(coef_found) == tuple(expected) or tuple(coef_found) == tuple(-c for c in expected):
                    classification = "suspicious_rewrite"  # original needed dropped constant yet a relation persists
                    suspicious += 1
                else:
                    classification = "consistent_rewrite_with_different_coefs"
                    suspicious += 1
            else:
                # Dropped a constant NOT used in original relation → expect
                # original relation recovers on reduced dict
                expected = [
                    int(c) for i, c in enumerate(relation_coefficients)
                    if i != drop_idx
                ]
                if tuple(coef_found) == tuple(expected) or tuple(coef_found) == tuple(-c for c in expected):
                    classification = "consistent_preserved"
                else:
                    classification = "rewrite_without_dropped_constant"
                    suspicious += 1
        results.append({
            "dropped_constant": drop_name,
            "relation_found": coef_found is not None,
            "coefficients_if_found": coef_found,
            "classification": classification,
        })
    return {
        "per_drop": results,
        "suspicious_rewrites": suspicious,
        "ablation_clean": suspicious == 0,
    }


# ---------------------------------------------------------------------------
# Public gate entry
# ---------------------------------------------------------------------------

def run_gate(
    claim: dict[str, Any],
    rubric_params: dict[str, Any],
) -> dict[str, Any]:
    """Run the G2 PSLQ false-positive audit on a claim.

    `claim` schema:
        {
            "claim_id": "<uuid>",
            "numerical_target": <float>,      # the constant being closed-form'd
            "target_precision_digits": <int>, # digits of confidence in target
            "relation_coefficients": [int,...],
            "constant_names": ["1","pi","ln_2","sqrt_2",...],
            "constant_values": [float,...],    # numerical evaluations
            "sha256_commitment": "<hex>",
        }

    `rubric_params` schema (rubric_data["pslq_falsity_audit"]):
        {
            "safety_margin_bits": <int, default 20>,
            "declared_precision_bits": <int>,  # what the solver ran at
            "perturbation_sigma": <float>,     # margin_of_safety envelope
            "perturbation_trials": <int, default 5>,
            "max_coefficient": <int, default 10000>
        }

    Returns the standard gate dict shape.
    """
    # ------------- hash commitment verification first -------------
    if not _verify_hash_commitment(claim):
        return {
            "name": GATE_ID,
            "passed": False,
            "actual": None,
            "threshold": None,
            "reason": "hash_commitment_violation",
            "penalty": 1,
            "hard_fail": True,
            "source": PRODUCER,
            "extra": {"hash_commitment_verified": False},
        }

    # ------------- bit-budget check -------------
    dim = len([c for c in claim["relation_coefficients"] if int(c) != 0])
    dict_size = len(claim["constant_names"])
    declared_bits = float(rubric_params.get("declared_precision_bits", 53))  # float64 default
    safety_margin = int(rubric_params.get("safety_margin_bits", DEFAULT_SAFETY_MARGIN_BITS))
    required_bits = required_precision_bits(dim, dict_size, safety_margin)
    budget_ok = declared_bits >= required_bits

    if not budget_ok:
        return {
            "name": GATE_ID,
            "passed": False,
            "actual": declared_bits,
            "threshold": required_bits,
            "reason": (f"bit_budget_violation: declared {declared_bits:.1f} bits "
                       f"< required {required_bits:.1f} (dim={dim}, "
                       f"dict_size={dict_size}, safety_margin={safety_margin})"),
            "penalty": 1,
            "hard_fail": True,
            "source": PRODUCER,
            "extra": {
                "dim": dim,
                "dict_size": dict_size,
                "declared_precision_bits": declared_bits,
                "required_precision_bits": required_bits,
                "safety_margin_bits": safety_margin,
            },
        }

    # ------------- relation evaluation at declared precision -------------
    eval_result = evaluate_relation_at_precision(
        claim["relation_coefficients"],
        claim["constant_values"],
        int(declared_bits),
    )

    # ------------- perturbation stability -------------
    pert_sigma = float(rubric_params.get("perturbation_sigma", 1e-20))
    pert_trials = int(rubric_params.get("perturbation_trials", DEFAULT_PERTURBATION_TRIALS))
    max_coef = int(rubric_params.get("max_coefficient", 10_000))
    pert_result = perturbation_stability_test(
        claim["relation_coefficients"],
        claim["constant_values"],
        pert_sigma,
        int(declared_bits),
        n_trials=pert_trials,
        max_coefficient=max_coef,
    )

    # ------------- dictionary ablation -------------
    abl_result = dictionary_ablation_test(
        claim["relation_coefficients"],
        claim["constant_values"],
        claim["constant_names"],
        int(declared_bits),
        max_coefficient=max_coef,
    )

    all_pass = budget_ok and pert_result["stable"] and abl_result["ablation_clean"]
    reasons = []
    if budget_ok:
        reasons.append("bit_budget_compliant")
    if pert_result["stable"]:
        reasons.append("perturbation_stable")
    else:
        reasons.append(f"perturbation_unstable({pert_result['trials_matching_claimed_relation']}/{pert_trials})")
    if abl_result["ablation_clean"]:
        reasons.append("ablation_clean")
    else:
        reasons.append(f"ablation_suspicious({abl_result['suspicious_rewrites']})")

    return {
        "name": GATE_ID,
        "passed": all_pass,
        "actual": eval_result.get("residual"),
        "threshold": 2 ** -int(declared_bits * 0.6),
        "reason": "; ".join(reasons),
        "penalty": 0 if all_pass else 1,
        "hard_fail": False,
        "source": PRODUCER,
        "extra": {
            "bit_budget": {
                "dim": dim,
                "dict_size": dict_size,
                "declared_precision_bits": declared_bits,
                "required_precision_bits": required_bits,
                "compliant": budget_ok,
            },
            "relation_evaluation": eval_result,
            "perturbation": pert_result,
            "ablation": abl_result,
        },
    }


def filter_per_claim_for_mutator_prompt(gate_result: dict[str, Any]) -> dict[str, Any]:
    """Return a gate-result view safe for mutator injection.

    Mutator sees pass/fail + bit-budget pass/fail + rationale categories.
    Mutator does NOT see: raw residual magnitude, per-trial perturbation
    results, per-drop ablation coefficients. (Per GP-144 mutator-visibility
    boundary.)
    """
    filtered = {k: v for k, v in gate_result.items() if k not in ("extra",)}
    extra = gate_result.get("extra", {})
    filtered["extra"] = {
        "bit_budget_compliant": extra.get("bit_budget", {}).get("compliant"),
        "dim": extra.get("bit_budget", {}).get("dim"),
        "dict_size": extra.get("bit_budget", {}).get("dict_size"),
        "perturbation_stable": extra.get("perturbation", {}).get("stable"),
        "ablation_clean": extra.get("ablation", {}).get("ablation_clean"),
    }
    return filtered
