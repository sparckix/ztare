---
id: GP-157
status: active
summary: Compressed super-arch map per GP-101 self-model spec; v5.0 grounding
---

# Cage v5.0 Super Architecture Map — compressed integration evidence

```
purpose:    grounded evidence for v5.0 Cage Orchestrator design (GP-158 audit)
            and for any session reasoning about cross-cutting integration
audience:   token-optimized for agents (per GP-101 self-model spec)
read_pre:   any v5.0 Cage proposal / any cross-component refactor
update_post: when seam is opened/closed or integration point changes shape
verifier:   none yet (could be added: assert files exist + grep entry hints)
discipline: NEVER claim integration without verifying current code shape
```

## SEAM INDEX (active + load-bearing for v5.0)

```
seam: GP-101  agent_native_self_model_format    open    (this map's format)
seam: GP-102  reflexive_primitive_discovery     open    (R1-R4 in gp158 evidence)
seam: GP-152  framer_architecture_v2            shipped (BIC, raw-coord MDL)
seam: GP-156  apparatus_hardening_proposal      shipped (R1, attest, fit_features)
seam: GP-157  cage_orchestrator_substrate_dispatch  open  (this audit's target)
seam: GP-148  void_mining                        shipped (mining apparatus)
seam: GP-098  evidence_compressor                shipped (preprocess pipeline)
seam: GP-097  manifold_compressor               shipped (N-D→1D pivot)
```

## INTEGRATION POINT INDEX (call-site → consumer; verified 2026-04-25)

```
ip: rubric.enable_fit_primitive
    site: autoresearch_loop.py rubric_preflight (~L3327-3421)
    gates: 1D fit_primitive engagement
    spec:  GP-035 + GP-088
    note:  legacy 1D paired (x, y) substrates only

ip: rubric.enable_fit_primitive_features
    site: autoresearch_loop.py main_loop (~L4669 dispatch banner)
    gates: N-D fit_primitive_features engagement (Proposal 3)
    spec:  GP-156 + GP-152 v2.0 BIC philosophy (K_law=8 → 10 per substrate)
    note:  feature-dict substrates (gp154, gp155); SIBLING block to 1D
    invariant: must NOT be nested under enable_fit_primitive flag (Bug #11)

ip: rubric.enable_framer
    site: autoresearch_loop.py main_loop (post-fit hook)
    gates: framer observe-mode (h_in / h_out transforms)
    spec:  GP-152 v2.0 (active_framer.py + 4 components A-F + 3 gates)
    note:  framing in transformed coords, MDL eval in raw coords
    KNOWN BLIND SPOT: assumes NDArray[(N, 2), float] 1D scalar input —
                      does NOT engage on feature-dict substrates (gp154/155)

ip: rubric.holdout_hard_gate
    site: test_thesis.py:2335-2470
    gates: post-judge HOLDOUT MRE → score floor (Bug #21 near-miss respect)
    spec:  GP-073 + GP-156 Bug #21 amendment
    schema: parses JSON {harness_ok, gates: [...]} legacy OR
            {holdout, farther_tail, all_gates_pass, any_near_miss} GP-156-shape
    invariant: HOLDOUT pass + non-blocking gate fail → keep judge score
               HOLDOUT near-miss → floor=30
               HOLDOUT hard-miss → score=0

ip: rubric.require_i_model_in_submission (default: true)
    site: autoresearch_loop.py:_prepare_mutation_candidate (~L1748)
    gates: validate_python_suite_imports.require_i_model
    spec:  GP-156 Proposal 1
    note:  audit substrates (gp156, gp158) set false; predictor substrates
           (gp154, gp155, gp146, gp077) require I_model

ip: rubric.enable_fit_primitive_features (force-opt-in side effect)
    site: autoresearch_loop.py:_prepare_mutation_candidate (~L1752)
    gates: validate_python_suite_imports.require_parametric_form
    spec:  GP-156 Proposal 3 + Bug #19 sequel
    invariant: when true, R1 rejects submissions missing PARAMETRIC_FORM/
               PARAMETER_NAMES — closes opt-out reflex

ip: G-CIRC + G-FALSIFY (structural blocker gates)
    site: autoresearch_loop.py main_loop post-thesis save
    gates: DAG acyclicity, ≥1 numeric assertion in test_model.py
    spec:  GP-138 + GP-141 (retired hardkill injection class)
    schema: workspace/structural_blocker_gates_latest.json

ip: G-INVERTER (gate-stack certification)
    site: autoresearch_loop.py main_loop post-judge (~L3597 + ~L5456)
    gates: GP-119 inverter rejects pre-conjecture if score < 50
    spec:  GP-146 inverter-plant rejection verifier
    note:  skipped if score < 50 threshold

ip: GP-122 Lean (proof-shortness)
    site: autoresearch_loop.py main_loop post-judge (~L3658-3673)
    gates: post-conjecture proof shortness via Lean REPL
    spec:  GP-139 lean_hardening + GP-144 G4 backbone
    note:  skipped if score < 70 threshold

ip: GP-149 anti-pattern catalog
    site: autoresearch_loop.py main_loop pre-mutator (~L2093-2179)
    gates: hardkill mode injection of RH-13/14/15/17 anti-patterns
    spec:  GP-149 mining findings
    schema: docs/concepts/anti_pattern_catalog.md

ip: R4 UNDERIDENTIFIED stagnation pivot
    site: autoresearch_loop.py main_loop (~L4086)
    gates: bounded-discriminator search exhausted decision
    spec:  GP-156 Bug #30 (rubric-level underidentified_after_override)
    note:  CLI default = pivot_after=3; rubric override allowed for audit
           substrates that score-swing 0↔70+ (gp156, gp158)

ip: rubric.fit_primitive_features_k_max (BIC-justified K budget)
    site: autoresearch_loop.py rubric handling (~L2038)
    gates: K_law cap for fit_primitive_features
    spec:  GP-156 Amendment + GP-152 v2.0 BIC philosophy
    note:  default 8; gp154 rubric overrides to 10 per heterogeneity

ip: GP-072 General Office (M-form audit)
    site: autoresearch_loop.py mform_alignment_audit
    gates: dimension-charter alignment audit
    spec:  GP-072 7-phase + GP-105 General Office
    note:  enable_mform_audit=true gates per-iter audit
```

## FIT PRIMITIVE FAMILY (1D + N-D — sibling, not nested)

```
fit_primitive (1D)              fit_primitive_features (N-D)
─────────────────────           ─────────────────────────────
input: paired (x, y)            input: (features_dict, y)
parse: FIT_DECLARATION block    parse: PARAMETRIC_FORM (str) + PARAMETER_NAMES
engine: scipy curve_fit         engine: scipy.optimize.minimize Nelder-Mead
multi-start: 3 → 5 (stagnation) multi-start: 3 → 5 (stagnation, same rule)
K budget: K_law (flat 5)        K budget: K_law (8/10) + BIC justification
AST whitelist: math grammar     AST whitelist: features+params subscripts,
                                              math.X attr, IfExp, Compare,
                                              float/int/bool coercion
substitute: regex into thesis   substitute: regex into MODEL_PARAMS={} (Bug #11/#21)
post-fit:                       post-fit:
  - residual diagnostic         - PATHOLOGY check (|param| > 10×max(|y|))
  - residual surface            - per-cat row counts (Bug #26)
  - format_for_prompt           - BIC = N·log(σ̂²) + K·log(N)
  - exponent grid search        - (no exponent grid — overkill for sigmoid)
                                - flat-desert detection
                                - feature-key cross-check
🧮 banner: NO                   🧮 banner: YES (verbose every iter)
output: workspace/fit_result.json   output: workspace/fit_features_result.json

PARITY GAP: residual diagnostic feedback to mutator next prompt is in 1D
but NOT in N-D. v5.0 should consolidate into FitEngine Protocol.
```

## SUBSTRATE TAXONOMY (current substrates classified by shape)

```
class: 1D_paired_evidence       — (x, y) rows; uses fit_primitive
  substrates: gp077 (OEIS), gp145 (SAW), gp146 (cat-map),
              gp150 (boundary), monotone_decay_01

class: N-D_feature_dict         — (features_dict, y) rows; uses fit_primitive_features
  substrates: gp154 (real-world scaling laws), gp155 (synth dense)
  invariant: features.py exposes visible_rows() / holdout_rows() / farther_tail_rows()

class: time_series              — trajectory data; uses continuous_chaotic kernels
  substrates: gp143 (Wasserstein-persistence), gp146 (cat-map),
              gp150 (heavy-tail), gp140 (Lorenz)

class: audit_substrate          — design/code review, no I_model
  substrates: gp156 (apparatus hardening), gp158 (Cage v5.0 audit),
              gp152/153 (framer audit)
  invariant: rubric.require_i_model_in_submission=false
  invariant: thesis = adversarial defect identification, not predictor

class: literature_review        — text-based, no fit
  substrates: gp081 (literature), gp149 (mining post-mortem)
```

## FAILURE-MODE TAXONOMY (24+2 bugs from 2026-04-25 session)

```
class A: reachability        bugs #11, #15, #21
class B: silent failure      bugs #16, #17/#23, #18
class C: contract gaming     bugs #14, #19, #20, #22, #24
class D: substitution        bugs #13, #25, MODEL_PARAMS-disappear
class E: magic numbers       K_law=5, near_miss=1.5, crash=0.5
class F: fit pathology       bug #26 — sparse-category overfitting (NEW 2026-04-25 eve)

invariant: each class is structural; v5.0 must close at root, not
           relocate to a new layer (Bug #11 was relocation of an
           older Wire-In class)
```

## GEMINI'S 1D-CLEAN-ROOM FAILURE-MODE INVERSION (gp158 audit anchor)

```
observation: GP-152 v2.0 spec assumes NDArray[(N, 2), float] —
             1D continuous scalar-kinematic data ONLY
consequence: spec validated against pristine synthetic math
             (y = exp(x²) / (1 + log x)) and never crashed
             ∴ panel debated theoretical purity (Newton/Einstein/Heisenberg)
             ∴ no one tested dict-shaped features or categorical strings
             ∴ Bug #14, #19, #20, #22, #24 (Class C contract gaming)
                were ALL invisible to v2.0 spec because spec assumed
                clean float input
classification: epistemic blind spot of LLM-vs-LLM debate —
                two LLMs optimizing for "philosophy of science" naturally
                miss "software integration" failure modes

INVERT FOR CAGE v5.0:
  R-rule R5 (NEW): every Cage Protocol method must be tested against
                   ≥1 substrate from EACH class in the substrate taxonomy
                   (1D, N-D, time_series, audit, literature) before
                   shipping. Pristine-math test cases do NOT count.
  R-rule R6 (NEW): every Cage integration point must have at least one
                   "messy" smoke test using REAL files from a current
                   project, not synthetic NDArray. Test the dict iteration,
                   the categorical-string handling, the missing-key path.
  R-rule R7 (NEW): every Cage panel transcript must include at least one
                   "Software Integration Engineer" turn that pressure-tests
                   AST handling, dict iteration, missing-key paths,
                   Unicode arrows, multi-line forms — NOT just MDL formula
                   purity. The Newton/Einstein/Munger panel naturally
                   debates physics; add a debugger persona.
```

## CAGE v5.0 INTEGRATION POINTS (proposed; must be reflexively verified)

```
component: Cage.dispatch(substrate, candidate) -> gate_engagements
  current call sites it must subsume:
    - autoresearch_loop.py:4581 (fit_primitive_features dispatch)
    - autoresearch_loop.py:~4255 (fit_primitive 1D dispatch — line est)
    - autoresearch_loop.py:~4360 (framer observe-mode hook)
    - test_thesis.py:2335-2470 (holdout_hard_gate parser)
  reflexive check (R2): proposed Protocol must accept current call shapes

component: FitEngine Protocol (1D + N-D unified)
  current Protocol candidates:
    - fit_primitive.fit_parameters(declaration, evidence)
    - fit_primitive_features.fit_features(form, names, visible)
  reflexive check (R2): proposed Protocol must accept BOTH input shapes;
                         OR migration sketch for breaking callers
  KNOWN GAP: 1D primitive's residual diagnostic API has no N-D equivalent.
             v5.0 must specify which adapter holds it.

component: substrate_evaluation utility (gate harness consolidation)
  current per-project gate_harness.py files this must subsume:
    - projects/gp154_scaling_law_exponents/gate_harness.py
    - projects/gp155_synthetic_dense_d_N_substrate/gate_harness.py
    - projects/gp146_arnold_cat_map_validation/gate_harness.py (1D)
  reflexive check (R3): canonical schema must cover ALL three shapes;
                         in-flight translator must handle GP-156-shape
                         AND legacy {harness_ok, gates: [...]} shape

component: can_handle(substrate, candidate) -> tuple[bool, str]
  reflexive check (R4): MUST correctly route substrates from each class
                         in the taxonomy (1D, N-D, time_series, audit, lit)
  KNOWN BLIND SPOT (per Gemini): if can_handle is debated by LLM panel
                                  in pristine-math terms, it will miss
                                  dict-iteration / missing-key / Unicode
                                  failure modes. Software Integration
                                  Engineer turn is mandatory.
```

## EDIT-INTENT LOOKUP TABLE

```
intent                                  → read first
─────────────────────────────────────────────────────────────────
"hook a new gate into Cage"             → this map (Integration Points)
                                          + GP-157 seam
                                          + autoresearch_loop_arch_map
"add new fit primitive class"           → fit_primitive_features.py
                                          + this map (Fit Primitive Family)
                                          + GP-156 spec
"new substrate of unknown class"        → this map (Substrate Taxonomy)
                                          + R1-R7 rules in gp158 evidence
"audit a new design proposal"           → gp158 charter + this map
                                          (esp. Failure-Mode Inversion)
"verify integration claim is grounded"  → R1-R4 in gp158 evidence
                                          + arch map line ranges
                                          + grep current code
"BIC field semantics"                   → GP-152 framer spec v2.0 §2
                                          + GP-156 Amendment §K_law
"K_law budget per substrate"            → GP-156 Amendment K_law section
                                          + rubric.fit_primitive_features_k_max
"pathology / sparse-category"           → Bug #26 (this map class F)
                                          + fit_features_result.json
                                          fields: pathological,
                                          extreme_params,
                                          feature_value_counts
```

## REFLEXIVE CONSISTENCY INVARIANT

```
assert: every claim in this map about a line range or function name
        was verified against current code state at last edit (timestamp
        in commit log). Stale-by-default; re-verify before relying.
why:    Bug #11 was a "spec said L4255 implementer wrote child branch
        nested at L4538" failure. Maps drift; code moves; verifier required.
trap:   if you cite this map's line range without re-grepping, you are
        doing the same Bug #11 pattern at a different layer. Always
        verify with grep before claiming.
```
