# Budget-anchored product state result

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-BUDGET-ANCHORED-PRODUCT-STATE-20260726-42`  
Verdict: refuted by selected-search budget; factorization criteria confirmed

The primary scalar supplied one unique depleted anchor (`3`). The inferred
secondary coordinate contains twelve variable cells, four states, and one
deterministic cycle. It separated H35, H38, H39, and H40.

The observed-target calibration returned `edge_found` in 23 actions after 232
generated / 126 expanded states, with no projection counterexample and an
admissible replay. Selected-target search produced no counterexample, reached
depth 33, and exhausted the fixed 20,000-state budget after 13,986 expansions
with 6,015 frontier states remaining.

Thus H42 fails only its selected-edge criterion. The prior abstraction defects
are no longer observed: target search is calibrated and the product coordinate
commutes throughout the bounded run. The returned best continuation has 31
actions. The next test consumes that explicit continuation contract through
bounded receding-horizon composition rather than adding another factor or
raising one monolithic cap.

Evidence:

- `budget_anchored_product_state_audit_result.json`
- `budget_anchored_product_state_audit.py`
