#!/usr/bin/env python3
"""archetype_classifier.py — predict L4 Lean tactic archetype + L2 op + L3 flags.

Reads `v30_layer4_archetype_catalog.json` (v1 or later) as the rules table.
Given a Lean goal text (signature + local context), outputs:
  - predicted_L4_archetype (from ARCH-001..008)
  - predicted_L2_structural_ops (cross-map)
  - predicted_L3_anti_pattern_flags (cross-map)
  - confidence (heuristic)
  - recommended_tactic_sequence (from archetype's common_tactics)

Heuristic classifier — uses goal SHAPE features (∀∃ patterns, =/≤/</‖·‖, Nat/Real/ℝ,
Measurable/Continuous, etc.) plus presence keywords. NOT learned. Foundation for v31
learned policy.

Usage:
  archetype_classifier.py --goal-file <path>    # parses Lean file with example/theorem
  archetype_classifier.py --goal-text "<text>"  # direct goal text input
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
DEFAULT_CATALOG = ROOT / "analytics/public/leanmill/results/v30_layer4_archetype_catalog.json"


def parse_lean_goal(text: str) -> dict:
    """Extract goal signature + local context from a Lean file's example/theorem."""
    # Find example/theorem with signature
    m = re.search(r"(example|theorem|lemma)\s+(?:[A-Za-z_][\w'.]*)?\s*((?:.|\n)+?):= by", text, re.DOTALL)
    if not m:
        m = re.search(r"(example|theorem|lemma)\s+(?:[A-Za-z_][\w'.]*)?\s*((?:.|\n)+?):=", text, re.DOTALL)
    sig = m.group(2).strip() if m else ""

    # Local context: variable/open lines BEFORE the example
    ctx = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("variable ", "open ", "namespace ", "import ")):
            ctx.append(stripped)
    return {"goal_signature": sig, "local_context": ctx}


def classify_by_goal_shape_topk(goal_sig: str, local_ctx: list[str], k: int = 3) -> list[dict]:
    """Top-K version: returns the top-k archetypes ranked by feature scores.

    Each entry: {predicted_L4_archetype, confidence, rules_fired}. Ordered
    by descending confidence. The full ARCH-001..008 catalog is scored, then
    truncated to top-k.

    Use this when Mode D should try tactic packs from multiple archetypes
    (precision-recall tradeoff: lose top-1 precision, gain coverage).
    """
    sig_low = goal_sig.lower()
    full_text = (goal_sig + "\n" + "\n".join(local_ctx)).lower()
    features = {
        "has_inequality": any(op in goal_sig for op in ("≤", "≥", "<", ">")),
        "has_equality": "=" in goal_sig and not any(op in goal_sig for op in ("≤", "≥", "≠")),
        "has_iff": "↔" in goal_sig,
        "has_and": "∧" in goal_sig,
        "has_or": "∨" in goal_sig,
        "has_exists": "∃" in goal_sig,
        "has_forall_unbounded": "∀ " in goal_sig and "∀ n" not in goal_sig and "∀ k" not in goal_sig,
        "has_norm": any(s in goal_sig for s in ("‖", "norm_", "dist ")),
        "has_inner_product": "⟪" in goal_sig or "inner" in goal_sig.lower(),
        "has_Lp_norm": "eLpNorm" in goal_sig or "Lp" in goal_sig or "‖·‖_" in goal_sig,
        "has_measurable": "Measurable" in goal_sig or "AEMeasurable" in goal_sig or "Continuous" in goal_sig,
        "has_integral": "∫" in goal_sig or "lintegral" in goal_sig,
        "has_nat_arith": any(s in goal_sig for s in ("ℕ", "Nat.", " n :")),
        "has_real_arith": "ℝ" in goal_sig or "Real." in goal_sig,
        "has_choose": ".choose" in goal_sig,
        "has_holder_dual": any(s in full_text for s in ("hölder", "holder", "cauchy-schwarz", "lp_mul_lq", "conjugate")),
        "has_induction_target": any(s in sig_low for s in ("∀ n", "∀ k", "list", "finset", "n : ℕ", "k : ℕ")),
        "has_struct_decomp": any(s in goal_sig for s in ("⟨", "And ", "Or ", "Iff ")),
        "has_summable": "Summable" in goal_sig or "summable" in sig_low,
        "has_short_signature": len(goal_sig) < 200,  # short sig → likely direct cite
    }
    # Score each archetype on a [0..1] scale based on feature matches.
    scores = {
        "ARCH-001_direct_library_chain": 0.30,  # always a fallback
        "ARCH-002_calc_inequality_chain": 0.0,
        "ARCH-003_normalization_first": 0.0,
        "ARCH-004_constructor_refine_decomposition": 0.0,
        "ARCH-005_induction_recursion": 0.0,
        "ARCH-006_monotonicity_gcongr_chain": 0.0,
        "ARCH-007_duality_holder_cs_route": 0.0,
        "ARCH-008_measure_measurability_automation": 0.0,
    }
    if features["has_measurable"]:
        scores["ARCH-008_measure_measurability_automation"] += 0.7
        scores["ARCH-001_direct_library_chain"] += 0.25  # could still be direct
    if features["has_holder_dual"] or features["has_Lp_norm"] or features["has_inner_product"]:
        scores["ARCH-007_duality_holder_cs_route"] += 0.5
        scores["ARCH-001_direct_library_chain"] += 0.40  # often a direct cite to a named Hölder lemma
        scores["ARCH-002_calc_inequality_chain"] += 0.2
    if features["has_induction_target"] and features["has_nat_arith"] and not features["has_norm"]:
        scores["ARCH-005_induction_recursion"] += 0.6
        scores["ARCH-001_direct_library_chain"] += 0.20
    if features["has_struct_decomp"] or features["has_and"] or features["has_iff"] or features["has_exists"]:
        scores["ARCH-004_constructor_refine_decomposition"] += 0.55
        scores["ARCH-001_direct_library_chain"] += 0.15
    if features["has_inequality"] and (features["has_norm"] or features["has_real_arith"]):
        scores["ARCH-002_calc_inequality_chain"] += 0.50
        scores["ARCH-006_monotonicity_gcongr_chain"] += 0.30
        scores["ARCH-001_direct_library_chain"] += 0.20
    if features["has_inequality"] and features["has_nat_arith"]:
        scores["ARCH-006_monotonicity_gcongr_chain"] += 0.45
        scores["ARCH-002_calc_inequality_chain"] += 0.30
    if features["has_equality"] and features["has_real_arith"]:
        scores["ARCH-003_normalization_first"] += 0.55
        scores["ARCH-001_direct_library_chain"] += 0.20
    if features["has_summable"] or features["has_short_signature"]:
        scores["ARCH-001_direct_library_chain"] += 0.20
    # Top-K with rules fired (just list features that fired)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:k]
    rules_fired = [name for name, v in features.items() if v]
    return [
        {"predicted_L4_archetype": a, "confidence": round(s, 3), "rules_fired": rules_fired}
        for a, s in ranked if s > 0
    ]


def classify_by_goal_shape(goal_sig: str, local_ctx: list[str]) -> dict:
    """Heuristic shape-based classification (top-1 — kept for backward compat)."""
    sig_low = goal_sig.lower()
    full_text = (goal_sig + "\n" + "\n".join(local_ctx)).lower()

    features = {
        "has_inequality": any(op in goal_sig for op in ("≤", "≥", "<", ">")),
        "has_equality": "=" in goal_sig and not any(op in goal_sig for op in ("≤", "≥", "≠")),
        "has_iff": "↔" in goal_sig,
        "has_and": "∧" in goal_sig,
        "has_or": "∨" in goal_sig,
        "has_exists": "∃" in goal_sig,
        "has_forall_unbounded": "∀ " in goal_sig and "∀ n" not in goal_sig and "∀ k" not in goal_sig,
        "has_norm": any(s in goal_sig for s in ("‖", "norm_", "dist ")),
        "has_inner_product": "⟪" in goal_sig or "inner" in goal_sig.lower(),
        "has_Lp_norm": "eLpNorm" in goal_sig or "Lp" in goal_sig or "‖·‖_" in goal_sig,
        "has_measurable": "Measurable" in goal_sig or "AEMeasurable" in goal_sig or "Continuous" in goal_sig,
        "has_integral": "∫" in goal_sig or "lintegral" in goal_sig,
        "has_nat_arith": any(s in goal_sig for s in ("ℕ", "Nat.", " n :")),
        "has_real_arith": "ℝ" in goal_sig or "Real." in goal_sig,
        "has_choose": ".choose" in goal_sig,
        "has_holder_dual": any(s in full_text for s in ("hölder", "holder", "cauchy-schwarz", "lp_mul_lq", "conjugate")),
        "has_induction_target": any(s in sig_low for s in ("∀ n", "∀ k", "list", "finset", "n : ℕ", "k : ℕ")),
        "has_struct_decomp": any(s in goal_sig for s in ("⟨", "And ", "Or ", "Iff ")),
    }

    # Classification rules (ordered by specificity)
    if features["has_measurable"]:
        return {
            "predicted_L4_archetype": "ARCH-008_measure_measurability_automation",
            "confidence": 0.7,
            "rules_fired": ["has_measurable"],
        }
    if features["has_holder_dual"] or features["has_Lp_norm"] or features["has_inner_product"]:
        return {
            "predicted_L4_archetype": "ARCH-007_duality_holder_cs_route",
            "confidence": 0.75,
            "rules_fired": ["has_inner_product or holder/Lp"],
        }
    if features["has_induction_target"] and features["has_nat_arith"] and not features["has_norm"]:
        return {
            "predicted_L4_archetype": "ARCH-005_induction_recursion",
            "confidence": 0.6,
            "rules_fired": ["has_induction_target + has_nat_arith"],
        }
    if features["has_struct_decomp"] or features["has_and"] or features["has_iff"] or features["has_exists"]:
        return {
            "predicted_L4_archetype": "ARCH-004_constructor_refine_decomposition",
            "confidence": 0.65,
            "rules_fired": ["has_struct_decomp / has_and / has_iff / has_exists"],
        }
    if features["has_inequality"] and (features["has_norm"] or features["has_real_arith"]):
        return {
            "predicted_L4_archetype": "ARCH-002_calc_inequality_chain",
            "confidence": 0.7,
            "rules_fired": ["has_inequality + (norm or real)"],
        }
    if features["has_inequality"] and features["has_nat_arith"]:
        # Could be ARCH-002 or ARCH-006 (monotonicity); default to A06 if `≤ ` chain
        return {
            "predicted_L4_archetype": "ARCH-006_monotonicity_gcongr_chain",
            "confidence": 0.55,
            "rules_fired": ["has_inequality + has_nat_arith"],
        }
    if features["has_equality"] and features["has_real_arith"]:
        return {
            "predicted_L4_archetype": "ARCH-003_normalization_first",
            "confidence": 0.7,
            "rules_fired": ["has_equality + has_real_arith → ring/ring_nf"],
        }
    if features["has_equality"]:
        return {
            "predicted_L4_archetype": "ARCH-003_normalization_first",
            "confidence": 0.55,
            "rules_fired": ["has_equality → normalization"],
        }
    return {
        "predicted_L4_archetype": "ARCH-001_direct_library_chain",
        "confidence": 0.4,
        "rules_fired": ["fallback default"],
    }


# Cross-map from L4 archetype to L2 + L3 (per reviewer's specs)
L4_TO_L2 = {
    "ARCH-001_direct_library_chain": ["core_01_reduction", "core_06_transfer"],
    "ARCH-002_calc_inequality_chain": ["broad_01_estimate_chain", "broad_08_constraint_propagation"],
    "ARCH-003_normalization_first": ["core_05_canonical_form_invariance"],
    "ARCH-004_constructor_refine_decomposition": ["core_03_decomposition_recomposition", "core_04_local_to_global"],
    "ARCH-005_induction_recursion": ["broad_02_recursive_decomposition"],
    "ARCH-006_monotonicity_gcongr_chain": ["broad_01_iterative_estimate_chain"],
    "ARCH-007_duality_holder_cs_route": ["broad_03_duality"],
    "ARCH-008_measure_measurability_automation": ["core_04_local_to_global", "core_06_transfer"],
}

L4_TO_L3 = {
    "ARCH-001_direct_library_chain": ["gold_name_verbatim", "tautological_apply", "endpoint_echo", "wrong_carrier"],
    "ARCH-002_calc_inequality_chain": ["wrong_direction", "missing_nonnegativity", "gcongr_floor_satisfiable", "budget_reuse"],
    "ARCH-003_normalization_first": ["simp_no_progress", "simp_set_indirect_leakage", "floor_satisfiable_by_ring", "rewrite_no_occurrence"],
    "ARCH-004_constructor_refine_decomposition": ["sort_closure", "unused_have", "wrong_field_target"],
    "ARCH-005_induction_recursion": ["wrong_induction_variable", "too_weak_induction_hypothesis"],
    "ARCH-006_monotonicity_gcongr_chain": ["gcongr_floor_satisfiable", "missing_side_condition", "wrong_order"],
    "ARCH-007_duality_holder_cs_route": ["wrong_conjugate_direction", "wrong_measure_carrier"],
    "ARCH-008_measure_measurability_automation": ["fun_prop_indirect_leakage", "measurability_typeclass_search_leakage", "wrong_sigma_algebra"],
}

L4_TO_RECOMMENDED_TACTICS = {
    "ARCH-001_direct_library_chain": ["exact ?lemma", "apply ?lemma", "simpa using ?lemma", "exact_mod_cast ?lemma"],
    "ARCH-002_calc_inequality_chain": ["calc ... ≤ ... := by ...", "nlinarith [sq_nonneg ?]", "linarith [...]", "gcongr"],
    "ARCH-003_normalization_first": ["ring", "ring_nf", "simp [...]", "field_simp; ring", "norm_num"],
    "ARCH-004_constructor_refine_decomposition": ["constructor; ⟨..., ...⟩", "refine ⟨?_, ?_⟩", "use ?witness", "exact ⟨..., ...⟩"],
    "ARCH-005_induction_recursion": ["induction n with | zero => ... | succ k ih => ...", "Nat.le_induction"],
    "ARCH-006_monotonicity_gcongr_chain": ["gcongr", "apply monotonicity_lemma", "nlinarith"],
    "ARCH-007_duality_holder_cs_route": ["apply inner_mul_le_norm_mul_norm", "apply ENNReal.lintegral_mul_le_Lp_mul_Lq", "calc chain via Hölder"],
    "ARCH-008_measure_measurability_automation": ["measurability", "fun_prop", "exact measurable_*", "simp [Measurable.X]"],
}


def classify(text: str) -> dict:
    parsed = parse_lean_goal(text)
    pred = classify_by_goal_shape(parsed["goal_signature"], parsed["local_context"])
    arch = pred["predicted_L4_archetype"]
    return {
        "input_goal_signature": parsed["goal_signature"][:300],
        "input_local_context_size": len(parsed["local_context"]),
        **pred,
        "predicted_L2_structural_ops": L4_TO_L2.get(arch, []),
        "predicted_L3_anti_pattern_flags": L4_TO_L3.get(arch, []),
        "recommended_tactic_sequence": L4_TO_RECOMMENDED_TACTICS.get(arch, []),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal-file", default=None)
    ap.add_argument("--goal-text", default=None)
    args = ap.parse_args()
    if args.goal_file:
        text = Path(args.goal_file).read_text()
    elif args.goal_text:
        text = args.goal_text
    else:
        print("Need --goal-file or --goal-text")
        return 1
    result = classify(text)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
