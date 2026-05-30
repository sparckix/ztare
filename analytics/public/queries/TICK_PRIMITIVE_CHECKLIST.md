# TICK PRIMITIVE CHECKLIST — read THIS, not the print wall
scope: NS_track_b, PDE_estimate, harmonic_analysis, lean_substrate, proof_compile_check, pre_lean_preflight, dimensional_check, endpoint_check, CAS_verification, sympy, graph_mining, closure_attempt, typed_endpoint, gowers_first, formalization_sequence, theorem_surface, carrier_observable  | index rows: 230 | ok: True

TOP PRIMITIVES (impact-ranked — USE the relevant one or record in the F-row why not):
1. NS-GRAPH-TICK-PRECHECK [primitive] score=104.5 — matched NS_track_b, lean_substrate, graph_mining, closure_attempt, typed_endpoint; bucket pde_ns_lean, graph_m  → src/ztare/research_director/ns_graph_tick.py
2. PATTERN-025-GOWERS-FIRST-FORMALIZE-SECOND [pattern] score=101 — matched NS_track_b, pre_lean_preflight, gowers_first, formalization_sequence, theorem_surface; bucket pde_ns_l  → org/patterns/gowers_first_formalize_second.md
3. LEAN-PROOF-GATE [gate] score=92.25 — matched lean_substrate, proof_compile_check, pre_lean_preflight, closure_attempt; bucket pde_ns_lean, graph_mi  → src/ztare/gates/lean_proof_gate.py
4. V33-PREFLIGHT-RISK-DETECTOR [gate] score=89 — matched lean_substrate, pre_lean_preflight, closure_attempt; bucket pde_ns_lean, sympy_cas, graph_mining; impa  → scripts/public/control/v33_preflight_risk_detector.py
5. CAS-W6-VERIFICATION [script] score=87 — matched harmonic_analysis, CAS_verification; bucket pde_ns_lean, sympy_cas; impact 5; graph_bonus 2  → scripts/projects/ns/CAS_W6_verification.py

FORCING GATES that may apply THIS tick:
- PDE estimate/inequality claim ⇒ RUN pde_estimate_workbench (dimensional/endpoint hard-block) + §3b adversarial-survival (math soundness) — pass BOTH
- terminus/kill/reversal verdict ⇒ §3b [MD-SURVIVED counter=… test=… ran=…] block (post_tick hard-fail else)
- ≥3rd recurrence of a manifest node ⇒ void-mining negative_result_object_discovery chain (positive recast BLOCKED)
