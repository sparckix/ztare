#!/usr/bin/env python3
"""Curriculum generator — produce toy-case variants of obligations.

Borrowed from RL theorem provers (AlphaProof, DeepSeek-Prover): generate
easier sub-problems, solve them, mine the solution patterns as primitives
for the harder original problem.

# Substrate-agnostic transformation rules

For any open obligation, apply ONE of N "complexity reductions":

  DIMENSION_REDUCE   3D → 1D version (NS → Burgers; PDE → ODE)
  LINEARIZE          drop nonlinear term (NS → Stokes; nonlinear elliptic → linear)
  TIME_FINITE        infinite-time → finite-time bound
  SPATIAL_PERIODIC   whole-space → periodic torus
  SCALAR_RESTRICT    vector-valued → scalar
  SYMMETRY           drop generality, restrict to radial / axisymmetric
  DISCRETE           continuous → finite-difference / dyadic
  REGULAR            distributional → smooth

Each transformation produces a NEW typed-endpoint target the apparatus
can attempt. Verified patches on toy cases become primitives Codex
mines for the original.

# Pipeline

  1. Read workmap target's structure source from Lean spine
  2. Apply chosen transformation (template-based, regex-driven)
  3. Output a new candidate structure + obligation as Lean source
  4. Hand to typed_endpoint_pack as a NEW target

# Reuse

  - Workmap target loading (`typed_endpoint_pack.load_workmap_target`)
  - Lean source slicing (`typed_patch_proposer.load_obligation_source_file`)
  - typed_endpoint_pack as the downstream solver

# Honest scope

  - Transformations are template-based, not Lean-elaborator-aware.
    Generated variants may be ill-typed; treat as proposals to be
    Codex-validated before sending to typed_endpoint_pack.
  - The "primitive mining" step (extract solution patterns from solved
    toy cases for the harder original) is NOT yet automated; it's a
    manual Codex step.

Usage:
    python scripts/public/utilities/curriculum_generator.py \\
        --target TrackBProfileLipschitzControlObligation \\
        --transform DIMENSION_REDUCE
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

LEAN_DIR = REPO / "ztare_proofs" / "ZtareProofs"


TRANSFORMATIONS = {
    "DIMENSION_REDUCE": {
        "description": "drop spatial dimensions (3D → 1D)",
        "name_suffix": "_OneD",
        "templates": {
            "type_replacements": [
                ("Fin 3", "Fin 1"),
                ("ℝ³", "ℝ"),
                ("PiLp 2 (.* Fin 3)", r"\1"),
            ],
            "field_filters": ["all_components", "vector_field"],
        },
    },
    "LINEARIZE": {
        "description": "drop nonlinear term (NS → Stokes)",
        "name_suffix": "_Linear",
        "templates": {
            "type_replacements": [
                ("nonlinear", "linear"),
            ],
            "field_filters": ["nonlinear_term", "convection"],
        },
    },
    "TIME_FINITE": {
        "description": "infinite-time → finite-time bound",
        "name_suffix": "_FiniteTime",
        "templates": {
            "type_replacements": [
                ("∀ (n : ℕ)", "∀ (n : ℕ) (h : n ≤ N)"),
                ("∀ t", "∀ t ≤ T"),
            ],
            "field_filters": ["limit", "asymptotic", "infinite"],
        },
    },
    "SPATIAL_PERIODIC": {
        "description": "whole-space → periodic torus",
        "name_suffix": "_Periodic",
        "templates": {
            "type_replacements": [
                ("ℝ³", "(Fin 3 → ℝ ⧸ ZSpan)"),
                ("Real", "TorusReal"),
            ],
            "field_filters": ["whole_space", "decay_at_infinity"],
        },
    },
    "SCALAR_RESTRICT": {
        "description": "vector-valued → scalar",
        "name_suffix": "_Scalar",
        "templates": {
            "type_replacements": [
                ("Fin 3 → ℝ", "ℝ"),
                ("VectorField", "ScalarField"),
                ("Vector ", "Scalar "),
            ],
            "field_filters": ["divergence_free", "vorticity"],
        },
    },
    "SYMMETRY": {
        "description": "drop generality, restrict to radial / axisymmetric",
        "name_suffix": "_Radial",
        "templates": {
            "type_replacements": [],
            "field_filters": [],
            "add_hypotheses": ["radially_symmetric"],
        },
    },
    "DISCRETE": {
        "description": "continuous → finite-difference / dyadic",
        "name_suffix": "_Dyadic",
        "templates": {
            "type_replacements": [
                ("Real", "DyadicReal"),
                ("ℝ", "ℤ × ℝ"),  # dyadic: (scale, value)
            ],
            "field_filters": ["continuous", "smooth"],
        },
    },
    "REGULAR": {
        "description": "distributional → smooth",
        "name_suffix": "_Smooth",
        "templates": {
            "type_replacements": [
                ("Distribution", "ContDiff ℝ ⊤"),
                ("WeakSolution", "SmoothSolution"),
            ],
            "field_filters": [],
        },
    },
}


def load_workmap_target(name: str) -> dict | None:
    workmap_path = (
        REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
        / "ns_trackb_instantiation_workmap.json"
    )
    if not workmap_path.exists():
        return None
    w = json.loads(workmap_path.read_text())
    items = w if isinstance(w, list) else w.get("structures", [])
    for ob in items:
        if ob.get("name") == name or ob.get("structure") == name:
            return ob
    return None


def load_obligation_source(target: dict, max_chars: int = 6000) -> str:
    file_stem = target.get("file", "")
    if not file_stem:
        return ""
    path = LEAN_DIR / f"{file_stem}.lean"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    name = target.get("name") or target.get("structure", "")
    if name:
        decl_pat = re.compile(
            rf"(?m)^(structure|class|def|theorem|lemma|abbrev)\s+"
            rf"{re.escape(name)}\b"
        )
        match = decl_pat.search(text)
        if match:
            idx = match.start()
            doc_start = text.rfind("\n/--", 0, idx)
            line_start = text.rfind("\n", 0, idx)
            start = doc_start + 1 if doc_start != -1 else max(0, line_start + 1)
            next_doc = text.find("\n/--", idx + len(name))
            next_decl = re.search(
                r"(?m)^(structure|class|def|theorem|lemma|abbrev)\s+",
                text[idx + len(name):],
            )
            candidates = []
            if next_doc != -1:
                candidates.append(next_doc)
            if next_decl:
                candidates.append(idx + len(name) + next_decl.start())
            end = min(candidates) if candidates else min(len(text), idx + max_chars)
            return text[start:end]
        if name in text:
            idx = text.find(name)
            line_start = text.rfind("\n", 0, idx)
            start = max(0, line_start + 1)
            end = min(len(text), idx + max_chars)
            return text[start:end]
    return text[:max_chars]


def apply_transformation(source: str, target_name: str,
                          transform: str) -> dict:
    """Apply a transformation to the source. Returns generated variant info."""
    if transform not in TRANSFORMATIONS:
        return {"error": f"unknown transform {transform}"}
    info = TRANSFORMATIONS[transform]
    new_name = target_name + info["name_suffix"]
    transformed = source

    # Apply type replacements
    for pat, repl in info["templates"].get("type_replacements", []):
        transformed = re.sub(pat, repl, transformed)

    # Rename the structure itself
    transformed = transformed.replace(target_name, new_name)

    # Filter out fields matching field_filters (best-effort regex)
    field_filters = info["templates"].get("field_filters", [])
    for pattern in field_filters:
        # remove lines mentioning the filter term
        transformed = re.sub(
            rf"\n\s+\w*{pattern}\w*\s*:.+", "", transformed, flags=re.IGNORECASE)

    return {
        "transform": transform,
        "transform_description": info["description"],
        "new_target_name": new_name,
        "transformed_source": transformed,
        "name_suffix": info["name_suffix"],
        "honest_caveat": ("Template-based transformation; the generated "
                           "variant may be ill-typed. Codex must validate "
                           "before sending to typed_endpoint_pack."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True,
                    help="workmap target name to generate curriculum for")
    ap.add_argument("--transform", required=True,
                    choices=list(TRANSFORMATIONS.keys()),
                    help="complexity-reduction transformation to apply")
    ap.add_argument("--list-transforms", action="store_true")
    ap.add_argument("--out-dir", type=Path,
                    default=REPO / "analytics" / "public" / "queries" / "curriculum_variants")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.list_transforms:
        for tname, tinfo in TRANSFORMATIONS.items():
            print(f"  {tname}: {tinfo['description']}")
        return 0

    print(f"=== curriculum generator ===")
    print(f"  target: {args.target}")
    print(f"  transform: {args.transform}")

    target = load_workmap_target(args.target)
    if not target:
        print(f"  target not in workmap")
        return 1

    source = load_obligation_source(target)
    if not source:
        print(f"  could not load source for target")
        return 1
    print(f"  loaded {len(source)} chars of source from {target.get('file', '?')}.lean")

    result = apply_transformation(source, args.target, args.transform)
    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return 1

    out_path = (args.out_dir
                / f"{args.target}_{args.transform.lower()}.json")
    out_path.write_text(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "original_target": args.target,
        "original_file": target.get("file", ""),
        **result,
    }, indent=2))

    # Also write a .lean file Codex can inspect
    lean_path = out_path.with_suffix(".lean")
    original_file = target.get("file", "")
    import_line = (
        f"import ZtareProofs.{original_file}\n\n"
        if original_file else ""
    )
    namespace_open = "namespace ZtareProofs.NS\n\n" if original_file else ""
    namespace_close = "\n\nend ZtareProofs.NS\n" if original_file else ""
    lean_path.write_text(
        f"-- Curriculum variant: {args.target} → {result['new_target_name']}\n"
        f"-- Transform: {args.transform} ({result['transform_description']})\n"
        f"-- HONEST CAVEAT: template-based; may be ill-typed.\n"
        f"-- Codex must validate before sending to typed_endpoint_pack.\n\n"
        f"{import_line}"
        f"{namespace_open}"
        + result["transformed_source"]
        + namespace_close
    )

    print(f"\n  generated variant: {result['new_target_name']}")
    print(f"  json: {out_path}")
    print(f"  lean: {lean_path}")
    print(f"\n  caveat: {result['honest_caveat']}")
    print(f"\n  next step: Codex inspects {lean_path}, fixes type errors, "
          f"sends to typed_endpoint_pack as a NEW target")
    return 0


if __name__ == "__main__":
    sys.exit(main())
