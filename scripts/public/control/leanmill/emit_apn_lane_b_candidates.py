"""Emit governance candidates for the 8 APN bare-Mathlib FULL proofs (Lane B).

Lane B is the *audit* lane: take DeepMind's published proofs (the EVOLVE-BLOCK
solutions in apn_repo/APNOutputs/AICollaborator/) and route each through the
LeanMill governance stack (`leanmill_governance_worker.py` + the L1/L2/L3
gates the PR_A1 audit went through). Pass = we certified a frontier proof
under stronger discipline than DeepMind shipped with. Fail = we found a leak /
axiom-smuggle / single-lemma laundering in a published frontier proof.

Each candidate has the shape the governance_worker validates:
  candidate_kind: "closure"
  target_kind:    "apn_alphaproof_nexus_audit"
  artifact_paths: [path/to/full_proof.lean]
  expected_outcome: "closure"

CLI:
  --out-dir <path>   directory for the per-proof candidate JSON files
                     (default: analytics/public/queries/lane_b_apn_candidates/)
  --dry-run          enumerate only

Surfaced through `ztare leanmill apn-candidates`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
APN_ROOT = REPO / "projects/gp_spectral_apn_seed_2026_05_28/apn_repo/APNOutputs/AICollaborator"
DEFAULT_OUT = REPO / "analytics/public/queries/lane_b_apn_candidates"

# Bare-Mathlib proofs (the subset already verified to compile in our v4.30 toolchain
# during the seed gate). Other AICollaborator/Erdős/OEIS subsets require the
# DeepMind formal-conjectures macro package + pinned Lean v4.27.0; see prior recon.
BARE_MATHLIB = [
    ("AlgebraicGeometry/hilbert_functions_1.lean", "P1"),
    ("AlgebraicGeometry/hilbert_functions_2.lean", "P2"),
    ("AlgebraicGeometry/hilbert_functions_3.lean", "P3"),
    ("AlgebraicGeometry/hilbert_functions_4.lean", "P4"),
    ("AlgebraicGeometry/hilbert_functions_5.lean", "P5"),
    ("AlgebraicGeometry/hilbert_functions_7.lean", "P7"),
    ("AlgebraicGeometry/hilbert_functions_8.lean", "P8"),
    ("Graphs/bipartite_graph_reconstruction_conjecture_2.lean", "Conjecture2"),
]


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def emit(out_dir: Path, dry_run: bool) -> int:
    now = datetime.now(timezone.utc).isoformat()
    written: list[str] = []
    for rel, target in BARE_MATHLIB:
        src = APN_ROOT / rel
        if not src.exists():
            print(f"WARN: APN proof missing: {src}", file=sys.stderr)
            continue
        candidate = {
            "schema": "leanmill-governance-candidate-v1",
            "candidate_kind": "closure",
            "target_kind": "apn_alphaproof_nexus_audit",
            "target_name": target,
            "target_source": "github.com/google-deepmind/alphaproof-nexus-results",
            "artifact_paths": [str(src.relative_to(REPO))],
            "expected_outcome": "closure",
            "formal_statement": f"theorem {target} : Problem{target} := <see artifact_paths[0]>",
            "lane": "lane_b_audit",
            "required_capability": "lean_compile",
            "audit_kind": "L1_compile + L2_axiom_allowlist + L3_anti_pattern",
            "audit_invariants": [
                "compile_ok must be true (compiles under v4.30.0-rc2)",
                "axiom_allowlist_ok must be true (only propext + Classical.choice + Quot.sound)",
                "single_lemma_rejected if exact? closes the target — that's not a multi-step closure",
                "matched_negative_control: context-stripped recompilation must NOT also close",
            ],
            "file_sha256": _sha256(src),
            "credit_boundary": "agentic proposal of a pre-cooked public proof for audit. Strict C credit ratified by governance.",
            "lineage": "DeepMind AlphaProof Nexus — published 2026; AICollaborator bare-Mathlib subset previously gated as type-checking in our toolchain",
            "generated_at": now,
        }
        if dry_run:
            print(f"DRY: would write {target} candidate for {src.name}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            outp = out_dir / f"apn_{target.lower()}_candidate.json"
            outp.write_text(json.dumps(candidate, indent=2))
            written.append(str(outp))
            print(f"wrote {outp.name}  target={target}  sha256={candidate['file_sha256'][:16]}")
    if not dry_run:
        manifest = out_dir / "_manifest.json"
        manifest.write_text(json.dumps({
            "schema": "leanmill-lane-b-candidate-manifest-v1",
            "generated_at": now,
            "candidate_count": len(written),
            "candidates": written,
            "lane": "lane_b_audit",
            "next_step": "enqueue each candidate via work_queue with kind=repair_canary_probe + required_capability=lean_compile, then governance_worker drains them under the L1/L2/L3 stack PR_A1 went through.",
        }, indent=2))
        print(f"\nmanifest: {manifest}")
        print(f"candidates ready: {len(written)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return emit(args.out_dir, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
