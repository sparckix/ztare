"""Smoke test for GP-144 G2 PSLQ falsity-audit gate.

Three claims:
  1. Known-true relation (trivial): pi = pi at declared precision 200 bits.
     Expected: PASS (real relation, bit-budget compliant, perturbation-stable,
     ablation consistent).
  2. Bit-budget violation: declared 20 bits for dim-3 dict-of-10 search.
     Expected: FAIL with hash_commitment or bit_budget_violation.
  3. Hash-tampered (genuine relation but wrong sha256): should FAIL at hash
     verification before anything else.

Also tests the mutator-visibility filter.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from src.ztare.gates.pslq_falsity_audit_gate import (  # noqa: E402
    GATE_ID,
    filter_per_claim_for_mutator_prompt,
    required_precision_bits,
    run_gate,
)


def _commit(claim: dict) -> dict:
    payload = {k: v for k, v in claim.items() if k != "sha256_commitment"}
    h = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    return {**claim, "sha256_commitment": h}


def main() -> None:
    import mpmath as mp
    mp.mp.prec = 200

    # Numerical values at 60-digit precision
    pi_val = float(mp.pi)
    e_val = float(mp.e)
    log2_val = float(mp.log(2))
    sqrt2_val = float(mp.sqrt(2))
    sqrt3_val = float(mp.sqrt(3))

    # Claim 1: trivial real relation — 1*pi - 1*pi = 0 (demo of structure
    # recovery; real claim would be Machin-like).
    # Actually use a real 2-term identity: log(4) = 2 * log(2).
    # Coefficients over dict ["log_4", "log_2"]: [-1, 2] satisfies -log(4)+2*log(2)=0.
    log4_val = float(mp.log(4))
    claim_true = _commit({
        "claim_id": "known_true_log4_log2",
        "numerical_target": 0.0,
        "target_precision_digits": 30,
        "relation_coefficients": [-1, 2],
        "constant_names": ["log_4", "log_2"],
        "constant_values": [log4_val, log2_val],
    })

    rubric_ok = {
        "declared_precision_bits": 200,
        "safety_margin_bits": 20,
        "perturbation_sigma": 1e-30,
        "perturbation_trials": 3,
        "max_coefficient": 100,
    }

    # Claim 2: bit-budget violation (arbitrary integer "relation" declared at
    # 20 bits for dim-5 dict-of-5 → required ≈ 5*log2(5)+20 = 31.6).
    claim_bitbudget = _commit({
        "claim_id": "bit_budget_too_low",
        "numerical_target": 0.0,
        "target_precision_digits": 6,
        "relation_coefficients": [1, 1, 1, 1, 1],  # dim-5 (all nonzero)
        "constant_names": ["pi", "e", "log_2", "sqrt_2", "sqrt_3"],
        "constant_values": [pi_val, e_val, log2_val, sqrt2_val, sqrt3_val],
    })
    rubric_tight = {
        "declared_precision_bits": 20,  # insufficient
        "safety_margin_bits": 20,
        "perturbation_sigma": 1e-6,
        "perturbation_trials": 3,
        "max_coefficient": 100,
    }

    # Claim 3: hash-tampered — correct log4/log2 relation but WRONG commitment
    tampered = dict(claim_true)
    tampered = {**tampered, "claim_id": "hash_tampered",
                "sha256_commitment": "deadbeef" * 8}

    print(f"=== smoke test: {GATE_ID} ===")
    print(f"required precision for (dim=3, dict=10, margin=20): "
          f"{required_precision_bits(3, 10, 20):.1f} bits")
    print(f"required precision for (dim=5, dict=5, margin=20): "
          f"{required_precision_bits(5, 5, 20):.1f} bits\n")

    # ---------- Claim 1 ----------
    print(f"--- claim 1: {claim_true['claim_id']} ---")
    r = run_gate(claim_true, rubric_ok)
    print(f"passed={r['passed']}  reason={r['reason']}")
    if r['extra'].get('relation_evaluation'):
        re = r['extra']['relation_evaluation']
        print(f"  residual={re.get('residual'):.2e}  precision_bits={re.get('precision_bits')}")
    pert = r['extra'].get('perturbation', {})
    print(f"  perturbation: stable={pert.get('stable')}  "
          f"matching={pert.get('trials_matching_claimed_relation')}/"
          f"{pert.get('trials_run')}")
    abl = r['extra'].get('ablation', {})
    print(f"  ablation: clean={abl.get('ablation_clean')}  "
          f"suspicious={abl.get('suspicious_rewrites')}")
    print()

    # ---------- Claim 2 ----------
    print(f"--- claim 2: {claim_bitbudget['claim_id']} ---")
    r = run_gate(claim_bitbudget, rubric_tight)
    print(f"passed={r['passed']}  reason={r['reason']}")
    print(f"  declared={r['actual']} < required={r['threshold']}")
    print()

    # ---------- Claim 3 ----------
    print(f"--- claim 3: {tampered['claim_id']} ---")
    r = run_gate(tampered, rubric_ok)
    print(f"passed={r['passed']}  reason={r['reason']}")
    print()

    # ---------- Mutator-visibility boundary ----------
    r_full = run_gate(claim_true, rubric_ok)
    filtered = filter_per_claim_for_mutator_prompt(r_full)
    assert "perturbation" not in filtered.get("extra", {}), "perturbation leaked to mutator view"
    assert "ablation" not in filtered.get("extra", {}), "ablation leaked to mutator view"
    assert "relation_evaluation" not in filtered.get("extra", {}), "residual leaked"
    print(f"mutator-view keys: {sorted(filtered.get('extra', {}).keys())}")
    print("mutator-visibility boundary: PASS")


if __name__ == "__main__":
    main()
