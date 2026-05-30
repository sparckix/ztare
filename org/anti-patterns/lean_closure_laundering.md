---
id: ANTI-PATTERN-013
name: lean_closure_laundering
status: active
discovered: 2026-05-15
cluster_size: 5
discovered_reason: |
  The v22-v30 GP-225 chain + tick541/carleman NS case repeatedly shipped
  "moat-grade closures" that compiled cleanly and passed GP-211
  lean_proof_gate (compile + axiom-audit + forbidden-token) yet were NOT
  novel closures. GP-211 catches hallucinated lemmas and standalone
  axioms; it does NOT catch a proof that compiles, has no extra axioms,
  no sorry — and is still vacuous / verbatim / trivially-automatable.
  These five false-closure sub-modes were caught only by offline GPT-5.5
  or post-hoc Meta-Darwin until the v33 organs mechanized them.
triggers:
  lexical: [moat-grade, closure, "compiled clean", sorry-free, "exact?", "fun_prop", "simp", vacuous]
  structural:
    - lean_proof compiled AND axiom_audit_passed AND no forbidden tokens
    - claim of novel/moat-grade closure on the compiled proof
sub_modes:
  - vacuous_or_trivial: hypothesis literally `True` / trivially-inhabited `∃ x:T, <triviality>` / conclusion `∃ _ : Prop, _` — the proof closes an empty set (tick541, carleman backward_uniqueness_from_carleman).
  - gold_name_verbatim: proof is a single REAL Mathlib lemma + trivial glue (obtain/exact/⟨⟩); the "closure" IS that existing lemma (v28-v29 retraction class; H12 intermediate_value_Ioo).
  - single_lemma_exact: Lean's own `exact?` closes the goal with one library lemma — not a novel closure (v26/v27 moat-surface class).
  - simp_set_indirect_leakage / fun_prop_indirect_leakage: closes via bare `simp`/`fun_prop`/`aesop` where the GLOBAL @[simp]/@[fun_prop] set silently carries the gold lemma; goal fails trivial-floor but the global set closes it with zero explicit citation.
  - scalar_wrapper_currency_mismatch: a SCALAR (ℝ/ℝ≥0/ENNReal) relation presented as discharging a FIELD/VECTOR obligation it does not typecheck as.
detected_by: >
  v33 governance organs (deterministic primitives, leakage-independent —
  Lean's own tactics / Mathlib's own corpus, ZERO audit verdict):
  scripts/public/control/v33_preflight_risk_detector.py (vacuity),
  v33_paraphrase_gate.py (gold_name_verbatim),
  v33_single_lemma_exact_gate.py (single_lemma_exact),
  v33_indirect_leakage_gate.py (simp/fun_prop leakage),
  v33_currency_mismatch_gate.py (scalar-wrapper).
  Wired in-loop via src/ztare/gates/lean_proof_gate.py
  `_run_v33_anti_laundering` (enforce_anti_laundering=True default;
  deep_verify opt-in). Mirrors how G-CIRC (circularity_gate) mechanizes
  SB-1.
mitigated_by: >
  A CONFIRMED sub-mode flips lean_proof_gate `gate_passed` to False
  (the "closure" is rejected before it can be scored moat-grade).
  Shape-suspect-only flags are surfaced advisory, non-blocking.
  Fail-open on organ crash (never blocks the loop on an organ bug).
falsifiable_test: >
  For any compiled lean_proof claiming closure: run the five v33
  primitives. Anti-pattern fires iff ≥1 sub-mode returns *confirmed*
  (not merely shape-suspect). Each confirmation is leakage-independent:
  vacuity via Lean trivial-cascade probe; gold-name via Mathlib node
  index; single-lemma via Lean `exact?`; indirect-leakage via
  floor-fails-but-global-set-closes (2 Lean compiles); currency via
  Lean kernel type-slot rejection. Validated on documented ground truth
  (carleman pre-fix, H07, H12, fun_prop continuity, scalar/Prop slot).
references:
  - src/ztare/gates/lean_proof_gate.py (GP-211, enriched 2026-05-15)
  - scripts/public/control/v33_*_gate.py / v33_preflight_risk_detector.py
  - ~/.claude/.../memory/project_meta_solver_terminal_verdict_2026_05_15.md
notes: >
  PRIMITIVE vs PATTERN: the five v33 organs are PRIMITIVES (deterministic
  executable gates), not patterns. They mechanize detection of this L3
  anti-pattern, exactly as circularity_gate (primitive) mechanizes the
  SB-1 circularity anti-pattern. They are NOT org/patterns/ entries.
  General currency-mismatch (arbitrary wrong-norm/units) beyond the
  scalar-wrapper subcase remains a flagged, unbuilt design (needs typed-
  companion / dimensional analysis).
