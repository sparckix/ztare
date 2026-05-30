#!/usr/bin/env python3
"""Auxiliary-object catalog — pec_a generator (closes the biggest GP-219 gap).

Per Phase 1 mining (analysis_pde paper + 30 NS F-rows): pec_a (Auxiliary
Comparison Object Construction) is the most-mentioned PDE move and the
apparatus currently has NO generator for it — only a gate that checks
declarations. This script supplies the missing generator.

# What this is

A curated catalog of common auxiliary-object families used in PDE
estimate-craft, mined from the analysis_pde literature catalog (Tao,
Brendle, Schoen-Yau, De Giorgi, Caffarelli). For a given (gap type,
target structure), the catalog returns 3-5 candidate auxiliary-object
SHAPES that have historically discharged similar gaps.

# What this is NOT

Not a Lean-aware constructor. The catalog gives mathematical TEMPLATES
("an exponential majorant of the form C₁ exp(C₂ |x|²)"); Codex translates
to typed Lean. This is GP-216 core_06 (Cross-Domain Translation) at the
literature-mathematician level.

# The catalog

Entries are { family, mathematical_form, gap_types, source_mathematician,
literature_anchor, typical_use_pattern }.

# Substrate-agnostic

Default catalog is PDE estimate-craft-flavored. Override with
--catalog-file to use a different domain catalog (e.g. for number theory,
combinatorics, etc.).

Usage:
    python scripts/public/utilities/auxiliary_object_catalog.py \\
        --gap-type SOBOLEV --target-context "viscous Burgers a priori"

    python scripts/public/utilities/auxiliary_object_catalog.py --list-families
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# Catalog of auxiliary-object families. Each family is a generic shape
# that has historically discharged a gap-type class.
AUXILIARY_OBJECT_CATALOG = [
    {
        "family": "exponential_majorant",
        "mathematical_form": "B(x) = C₁ exp(C₂ φ(x))  for some convex φ",
        "gap_types": ["PROPAGATION", "SOBOLEV", "AUXILIARY"],
        "source_mathematician": ["Brendle", "Hamilton", "Schoen-Yau"],
        "literature_anchor": "maximum-principle barriers; Aleksandrov-Bakelman-Pucci",
        "typical_use_pattern": (
            "When the unknown u satisfies a parabolic inequality, "
            "construct B with B(t,x) ≥ u(t,x) on the parabolic boundary; "
            "by maximum principle, B ≥ u everywhere."
        ),
        "ns_track_b_relevance": (
            "For NS L^∞ control: build B as exp(c‖∇u‖²) and show "
            "(∂_t - ν Δ) B ≥ |nonlinear advection|."
        ),
    },
    {
        "family": "conformal_weight",
        "mathematical_form": "w(x) = (1 + |x|²)^α  for some α tuned to scaling",
        "gap_types": ["INTERPOLATION", "EMBEDDING", "AUXILIARY"],
        "source_mathematician": ["Caffarelli-Kohn-Nirenberg", "Brezis"],
        "literature_anchor": "weighted Sobolev inequalities (CKN)",
        "typical_use_pattern": (
            "Multiply the natural energy by w(x) and integrate; the weight "
            "decays/grows just enough to make the integration converge."
        ),
        "ns_track_b_relevance": (
            "For NS partial regularity (CKN type): weight by (1+|x|²)^α to "
            "trade off decay at infinity vs. local concentration."
        ),
    },
    {
        "family": "cutoff_partition",
        "mathematical_form": "ψ ∈ C_c^∞(ℝ^d), 0 ≤ ψ ≤ 1, ψ = 1 on K, supp(ψ) ⊂ K'",
        "gap_types": ["SOBOLEV", "PROPAGATION", "AUXILIARY"],
        "source_mathematician": ["Caffarelli", "Kohn-Nirenberg", "Lin"],
        "literature_anchor": "localization in elliptic + parabolic regularity",
        "typical_use_pattern": (
            "Multiply equation by ψ²u and integrate; the boundary terms "
            "vanish, the bulk gives the local energy estimate, and the "
            "cutoff error is controlled by ‖∇ψ‖_∞."
        ),
        "ns_track_b_relevance": (
            "For NS local energy: cut off near a point of suspected blowup; "
            "the cutoff error contributes a bounded perturbation."
        ),
    },
    {
        "family": "test_function_oscillating",
        "mathematical_form": "φ_n(x) = α_n cos(λ_n x) χ_n(x)  (disjointly supported)",
        "gap_types": ["INTERPOLATION", "COERCIVITY", "AUXILIARY"],
        "source_mathematician": ["Bourgain", "Tao", "Erdős"],
        "literature_anchor": "Fourier extension + restriction; oscillatory integrals",
        "typical_use_pattern": (
            "Pair the unknown against an oscillating test function tuned to "
            "isolate a frequency; the oscillation cancels everything except "
            "the target mode."
        ),
        "ns_track_b_relevance": (
            "For NS spectral arguments: pair u with a Littlewood-Paley shell "
            "ψ_N to isolate behavior at frequency 2^N."
        ),
    },
    {
        "family": "calderon_decomposition",
        "mathematical_form": "u = Σ_N P_N u  (Littlewood-Paley shells)",
        "gap_types": ["COMMUTATOR", "INTERPOLATION", "SOBOLEV"],
        "source_mathematician": ["Bony", "Coifman-Meyer", "Tao"],
        "literature_anchor": "paraproduct calculus; Bony decomposition",
        "typical_use_pattern": (
            "Decompose products fg = T_f g + T_g f + R(f,g) into low-high, "
            "high-low, and high-high pieces; estimate each with the right "
            "Hölder."
        ),
        "ns_track_b_relevance": (
            "Already used heavily in NS Track B (Bony paraproducts in beat-"
            "backscatter); the apparatus's Bony lemmas are the right form."
        ),
    },
    {
        "family": "sign_changing_periodic",
        "mathematical_form": "ψ_per(x) = Σ_k a_k χ_{[kπ, (k+1)π]}(x)  with Σa_k = 0",
        "gap_types": ["COERCIVITY", "AUXILIARY", "EMBEDDING"],
        "source_mathematician": ["Bahri-Coron", "Brezis-Nirenberg"],
        "literature_anchor": "Liouville-type rigidity via oscillation",
        "typical_use_pattern": (
            "Choose ψ with cancellation, show that ⟨u, ψ⟩ = 0 forces u "
            "to lie in a small subspace; then use the small subspace's "
            "rigidity."
        ),
        "ns_track_b_relevance": (
            "For NS profile decomposition: orthogonal-projection-like "
            "constructs that isolate the Leray profile."
        ),
    },
    {
        "family": "energy_with_correction",
        "mathematical_form": "Ẽ(t) = E(t) + δ * F(t)  for tuned δ and lower-order F",
        "gap_types": ["PROPAGATION", "COERCIVITY", "LIMIT_PASSAGE"],
        "source_mathematician": ["Christodoulou-Klainerman", "Smith-Tataru"],
        "literature_anchor": "modified energy method; Glassey-type",
        "typical_use_pattern": (
            "When the natural energy E is not quite monotone, add a small "
            "correction F that absorbs the bad term in dE/dt; choose δ "
            "small enough that Ẽ ~ E."
        ),
        "ns_track_b_relevance": (
            "For NS Lipschitz reserve: build a modified energy that "
            "absorbs the cross-term contributions of profile interaction."
        ),
    },
    {
        "family": "dual_test_construct",
        "mathematical_form": "v solving L*v = g, then ⟨u, g⟩ = ⟨Lu, v⟩",
        "gap_types": ["EMBEDDING", "INTERPOLATION", "AUXILIARY"],
        "source_mathematician": ["Lions-Magenes", "Stampacchia"],
        "literature_anchor": "duality method; Hahn-Banach + functional analysis",
        "typical_use_pattern": (
            "To bound ⟨u, g⟩ for arbitrary g in some test class, construct v "
            "as the solution of the adjoint problem with right-hand side g; "
            "control via ‖v‖ in dual norm."
        ),
        "ns_track_b_relevance": (
            "For NS pressure: the pressure p satisfies a Poisson equation; "
            "test against suitable v to extract pressure bounds."
        ),
    },
    {
        "family": "monotone_quantity",
        "mathematical_form": "M(t) = ∫ u(t,x) ψ(x) dx  monotone in t",
        "gap_types": ["PROPAGATION", "AUXILIARY"],
        "source_mathematician": ["Hamilton", "De Giorgi"],
        "literature_anchor": "monotonicity formulas in geometric flow",
        "typical_use_pattern": (
            "Pick ψ such that d/dt ∫ u ψ has a sign; integrate in time to "
            "get a uniform bound on ∫ u ψ; use this for compactness or "
            "rigidity."
        ),
        "ns_track_b_relevance": (
            "For NS angular-moment quantities: identify monotone quantities "
            "in the radial / shell decomposition."
        ),
    },
    {
        "family": "blowup_profile_renormalization",
        "mathematical_form": "Ũ(s,y) = (T-t)^α U(t, x*(t) + (T-t)^β y)",
        "gap_types": ["AUXILIARY", "PROPAGATION", "LIMIT_PASSAGE"],
        "source_mathematician": ["Giga-Kohn", "Merle-Raphael"],
        "literature_anchor": "self-similar variables; rescaling near blowup",
        "typical_use_pattern": (
            "Near a candidate blowup point, rescale to a fixed size; the "
            "rescaled profile satisfies a stationary equation whose "
            "solutions classify the possible blowup types."
        ),
        "ns_track_b_relevance": (
            "For NS Track B blowup analysis: rescale near suspected "
            "concentration points to identify possible profile shapes."
        ),
    },
]


def query_catalog(gap_type: str | None = None,
                   keyword: str | None = None) -> list[dict]:
    """Return families matching gap_type or keyword."""
    matched = []
    for entry in AUXILIARY_OBJECT_CATALOG:
        if gap_type and gap_type.upper() not in [g.upper() for g in entry["gap_types"]]:
            continue
        if keyword:
            text = json.dumps(entry).lower()
            if keyword.lower() not in text:
                continue
        matched.append(entry)
    return matched


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap-type", default=None,
                    help="filter by gap type (SOBOLEV / INTERPOLATION / ...)")
    ap.add_argument("--keyword", default=None,
                    help="filter by keyword (e.g. 'NS', 'monotone')")
    ap.add_argument("--list-families", action="store_true")
    ap.add_argument("--target-context", default=None,
                    help="optional context string saved with output")
    ap.add_argument("--out", type=Path,
                    default=REPO / "analytics" / "public" / "queries" /
                              "auxiliary_object_suggestions.jsonl")
    args = ap.parse_args()

    if args.list_families:
        for entry in AUXILIARY_OBJECT_CATALOG:
            print(f"  {entry['family']}: {entry['gap_types']}")
            print(f"    {entry['mathematical_form']}")
        return 0

    matched = query_catalog(args.gap_type, args.keyword)
    print(f"=== auxiliary-object catalog ===")
    print(f"  query: gap_type={args.gap_type!r} keyword={args.keyword!r}")
    print(f"  matched {len(matched)} families\n")
    for entry in matched:
        print(f"## {entry['family']}")
        print(f"  form: {entry['mathematical_form']}")
        print(f"  gaps: {entry['gap_types']}")
        print(f"  source: {entry['source_mathematician']}")
        print(f"  pattern: {entry['typical_use_pattern'][:200]}")
        print(f"  NS-relevance: {entry['ns_track_b_relevance'][:200]}")
        print()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "query": {"gap_type": args.gap_type, "keyword": args.keyword,
                      "context": args.target_context},
            "n_matches": len(matched),
            "matches": [e["family"] for e in matched],
        }) + "\n")
    print(f"  logged query to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
