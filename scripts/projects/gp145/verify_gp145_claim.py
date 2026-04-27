"""Post-hoc verifier for gp145_saw_mu_square claims.

Audits any PSLQ-derived closed-form claim for mu_sq (the 2D square-lattice SAW
connective constant) in a gp145 iteration's thesis against G2
pslq_falsity_audit_gate.

Protocol:
  1. Read a gp145 current_iteration.md (or arbitrary .md supplied with --file).
  2. Search for a fenced JSON block tagged `pslq_claim` containing a structured
     relation (see SCHEMA below).
  3. If found: recompute sha256 of the claim payload (sans commitment field),
     run G2 gate, print verdict.
  4. If not found: report "no verifiable claim found" — the thesis proposed
     no structured PSLQ relation the verifier can audit. This is
     pedagogically important: it tells the operator whether the mutator
     actually emitted a testable claim vs. prose-only speculation.

SCHEMA for a pslq_claim block (inside a ```pslq_claim ...``` fence):
  {
    "claim_id": "<string>",
    "target_constant": "mu_sq_2d_saw",
    "target_numerical": 2.638158530031,
    "target_precision_digits": 30,
    "relation": "mu_sq - A*sqrt(2) - B*pi = 0",    # human-readable
    "relation_coefficients": [1, -A, -B, ...],      # integer coefficients
    "constant_names": ["mu_sq", "sqrt_2", "pi", ...],
    "constant_values": [2.638158530031, 1.41421..., 3.14159..., ...],
    "sha256_commitment": "<hex, optional; verifier recomputes>"
  }

Usage:
  python3 scripts/verify_gp145_claim.py --file projects/gp145_saw_mu_square/current_iteration.md
  python3 scripts/verify_gp145_claim.py --iter <timestamp>    # look up by iter_ts

Exit codes:
  0 = verification ran (pass or fail reported)
  1 = no claim found / schema invalid / input error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.ztare.gates.pslq_falsity_audit_gate import (  # noqa: E402
    filter_per_claim_for_mutator_prompt,
    required_precision_bits,
    run_gate,
)

PROJECT_DIR = REPO / "projects" / "gp145_saw_mu_square"
CANONICAL_DICTIONARY_Δ1 = [
    "1", "pi", "e", "ln_2", "ln_3", "ln_5", "sqrt_2", "sqrt_3", "sqrt_5",
    "zeta_3", "catalan", "euler_gamma",
    "gamma_1_3", "gamma_1_4", "gamma_2_3",
    "K_1_sqrt2",           # elliptic K(1/√2)
    "pi_sq_over_6",        # ζ(2) = π²/6
    "e_to_pi_over_4",
    "ln_10",
    "sqrt_2_plus_sqrt_2",  # the hexagonal witness: μ_hex = √(2+√2)
]


def _canonical_payload_for_hash(claim: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in claim.items() if k != "sha256_commitment"}


def _recompute_sha256(claim: dict[str, Any]) -> str:
    payload = _canonical_payload_for_hash(claim)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def _extract_pslq_claims(md_text: str) -> list[dict[str, Any]]:
    """Extract all `pslq_claim` JSON blocks from a markdown document.

    Accepts two fence forms:
        ```pslq_claim
        {...}
        ```
    and
        ```json
        {
          "claim_id": ...,
          "target_constant": "mu_sq_2d_saw",
          ...
        }
        ```
    The second form is accepted only if the JSON contains a
    "target_constant" field.
    """
    claims: list[dict[str, Any]] = []
    # Form 1: explicit pslq_claim fence
    for match in re.finditer(
        r"```pslq_claim\s*\n(.*?)\n```", md_text, re.DOTALL
    ):
        try:
            claims.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass
    # Form 2: ```json fence containing a target_constant
    for match in re.finditer(r"```(?:json)?\s*\n(\{.*?\})\n```", md_text, re.DOTALL):
        try:
            obj = json.loads(match.group(1))
            if isinstance(obj, dict) and obj.get("target_constant"):
                claims.append(obj)
        except json.JSONDecodeError:
            pass
    return claims


def _read_iteration_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{path} does not exist")
    return path.read_text(encoding="utf-8", errors="ignore")


def _find_by_iter_timestamp(ts: int) -> Path | None:
    candidate = PROJECT_DIR / f"debate_log_iter_{ts}.md"
    if candidate.is_file():
        return candidate
    hist = PROJECT_DIR / "history"
    if hist.is_dir():
        matches = list(hist.glob(f"{ts}_*.md"))
        if matches:
            return matches[0]
    return None


def run_verification(md_path: Path, rubric_params: dict[str, Any] | None = None) -> int:
    """Returns exit code (0 = verification ran, 1 = no claim / error)."""
    md = _read_iteration_file(md_path)
    claims = _extract_pslq_claims(md)
    if not claims:
        print(f"🟡 No verifiable claim found in {md_path.name}")
        print("   The thesis did not emit a structured pslq_claim JSON block.")
        print("   Prose-only closed-form proposals cannot be automatically audited.")
        print()
        print("   To become auditable, the thesis must include a fenced block like:")
        print("   ```pslq_claim")
        print('   {"claim_id": "...", "target_constant": "mu_sq_2d_saw",')
        print('    "target_numerical": 2.638158530031, ...}')
        print("   ```")
        return 1

    rubric_params = rubric_params or {
        "declared_precision_bits": 100,
        "safety_margin_bits": 20,
        "perturbation_sigma": 1e-20,
        "perturbation_trials": 5,
        "max_coefficient": 10_000,
    }

    any_passed = False
    for i, claim in enumerate(claims, 1):
        print(f"=== Claim {i}: {claim.get('claim_id', '(unnamed)')} ===")
        # Auto-add sha256_commitment if the mutator didn't compute it
        if "sha256_commitment" not in claim:
            claim = {**claim, "sha256_commitment": _recompute_sha256(claim)}
            print("   (auto-computed sha256_commitment)")

        # Validate schema fields
        required = {"relation_coefficients", "constant_names", "constant_values",
                    "target_numerical"}
        missing = required - claim.keys()
        if missing:
            print(f"🔴 SCHEMA: missing fields {missing}")
            continue

        # Check lengths match
        n_coef = len(claim["relation_coefficients"])
        n_names = len(claim["constant_names"])
        n_vals = len(claim["constant_values"])
        if not (n_coef == n_names == n_vals):
            print(f"🔴 SCHEMA: length mismatch coef={n_coef} names={n_names} vals={n_vals}")
            continue

        # Dim / dict_size / bit budget
        dim = sum(1 for c in claim["relation_coefficients"] if int(c) != 0)
        dict_size = len(claim["constant_names"])
        needed_bits = required_precision_bits(dim, dict_size, rubric_params["safety_margin_bits"])
        print(f"   dim={dim}  dict_size={dict_size}  "
              f"required_bits={needed_bits:.1f}  "
              f"declared_bits={rubric_params['declared_precision_bits']}")

        # Run G2
        result = run_gate(claim, rubric_params)
        verdict = "✅ PASS" if result["passed"] else "🔴 FAIL"
        print(f"{verdict}  reason: {result['reason']}")
        if result.get("extra", {}).get("relation_evaluation"):
            re_eval = result["extra"]["relation_evaluation"]
            print(f"   residual = {re_eval.get('residual')}")
            print(f"   residual_log2 ≈ {re_eval.get('residual_log2')}")
        pert = result.get("extra", {}).get("perturbation", {})
        if pert:
            print(f"   perturbation: stable={pert.get('stable')}  "
                  f"matching={pert.get('trials_matching_claimed_relation')}/"
                  f"{pert.get('trials_run')}")
        abl = result.get("extra", {}).get("ablation", {})
        if abl:
            print(f"   ablation: clean={abl.get('ablation_clean')}  "
                  f"suspicious={abl.get('suspicious_rewrites')}")
        print()
        if result["passed"]:
            any_passed = True

    if any_passed:
        print("🟢 At least one claim passed G2. Next step: GP-122 Lean verification.")
    else:
        print("🟡 No claim passed G2. This is the expected default outcome per")
        print("    gp145 pre-registered prior (P_null ≈ 65%, P_garbage ≈ 15%).")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", type=str, help="Path to a markdown file to audit")
    parser.add_argument("--iter", type=int, help="Iteration timestamp (unix seconds)")
    parser.add_argument("--precision-bits", type=int, default=100,
                        help="Declared precision budget for G2 (default: 100)")
    parser.add_argument("--safety-margin-bits", type=int, default=20)
    parser.add_argument("--perturbation-sigma", type=float, default=1e-20)
    parser.add_argument("--perturbation-trials", type=int, default=5)
    parser.add_argument("--max-coefficient", type=int, default=10_000)
    args = parser.parse_args()

    if args.file:
        md_path = Path(args.file)
    elif args.iter:
        found = _find_by_iter_timestamp(args.iter)
        if not found:
            print(f"🔴 No iteration file for timestamp {args.iter}", file=sys.stderr)
            sys.exit(1)
        md_path = found
    else:
        # Default: audit current_iteration.md
        md_path = PROJECT_DIR / "current_iteration.md"

    rubric_params = {
        "declared_precision_bits": args.precision_bits,
        "safety_margin_bits": args.safety_margin_bits,
        "perturbation_sigma": args.perturbation_sigma,
        "perturbation_trials": args.perturbation_trials,
        "max_coefficient": args.max_coefficient,
    }
    exit_code = run_verification(md_path, rubric_params)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
