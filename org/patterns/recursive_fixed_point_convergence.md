---
id: META-PATTERN-024
name: recursive_fixed_point_convergence
version: 1
status: active
discovered: 2026-05-15
triggers:
  lexical: [same atom again, re-vocabularied, every route collapses, strange loop, fractal, keeps coming back, fixed point, criticality]
  structural:
    - N>=3 recursive reformulations (incl. cross-field isomorphisms) each Meta-Darwin-collapse to the SAME residual
    - each reformulation provably degree-0 / scaling-critical (no free sub-critical gain)
    - operator says "don't stop / don't strawman" yet new ticks keep re-deriving one atom
  problem_classes: [hard_mathematical_residual, pure_analysis_drift, apparatus_self_audit]
spawn:
  mode: convergence_audit
  subagents:
    - role: fixed_point_invariance_prover
      tools: [read, bash]
output_schema: fixed_point_convergence_report_v1
fallback: PATTERN-020  # meta_arc_stall_resolution (weaker: stall, not fixed-point)
preconditions:
  - at least 3 distinct reformulations attempted and Meta-Darwin-killed
  - amnesia precheck (PATTERN-024) run before each reformulation
chain_position: post
composes:
  - PATTERN-024 (scientific_amnesia_precheck — run before EVERY iterate)
  - PATTERN-018 (structural_residual_analogy — the cross-field isomorphism iterates)
  - darwin_idea_killer (the recursive MD-kill of each iterate)
  - META-PATTERN-022 (gowers_first + content composition — each iterate is pencil-first)
  - META-PATTERN-023 (multi_scope — each iterate verified at 4 scopes)
  - PATTERN-005 (falsifiable_asymmetry — the transverse escape must be falsifiable)
  - PATTERN-008 (three_leg_verification — LEG1/2/3 on the fixed-point claim)
  - PATTERN-012 (prediction_ledger — contract each iterate; calibration converges)
related_patterns:
  - PATTERN-020 (meta_arc_stall_resolution — weaker predecessor: detects stall, not the structural cause)
falsifiable_test: |
  Once wired as a post-position convergence audit, over N>=8 residuals that hit the
  trigger (>=3 distinct reformulations each Meta-Darwin-collapsing to the same
  residual), firing the pattern must produce a proved Phi-invariance theorem PLUS a
  finite enumerated transverse-channel set in >=75% of cases, AND must cut the
  number of subsequent same-axis reformulation ticks on that residual to <=0.3x the
  count observed on matched pre-wiring residuals (the NS strict-margin baseline:
  ~10 reformulations / >=4 vocabulary drifts on one atom before the loop was
  named). If firing the pattern does not yield a proved fixed point in >=75% of
  triggered cases, or does not cut same-axis reformulation ticks to at most 0.3x
  baseline, it neither stops the laundering loop nor distinguishes it from a stall,
  and demotes.
  metric_source: fixed_point_convergence_report_v1 outputs (Phi-invariance proof
  present, transverse-channel enumeration) joined to per-residual
  reformulation-tick counts from pattern_deployment_ledger.jsonl /
  EXPERIMENT_TRACK_RECORD.md; matched pre-wiring residuals as control.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# META-PATTERN-024 — Recursive Fixed-Point Convergence Detector

## Problem

A hard residual is attacked recursively: each pass applies a fresh
reformulation (channel-shift, scale-separation, cross-field
isomorphism, new physical vocabulary) and a Meta-Darwin kill. Without
this pattern, the agent either (a) keeps spawning reformulations
forever — each "new" one re-deriving the same atom under drifting
vocabulary (the documented NS amnesia loop: ≥4 vocabularies for one
2026-05-12 atom), mistaking motion for progress; or (b) declares a
false "terminus" and stops (the pessimism/strawman failure the
operator repeatedly flags).

PATTERN-020 (meta_arc_stall_resolution) detects that an arc has
stalled but not *why*; it does not distinguish "stuck, reframe" from
"converged to an invariant fixed point — stop iterating, change axis".

## Pattern

When **N ≥ 3** distinct reformulations (including at least one
cross-field isomorphism) each Meta-Darwin-collapse to the **same
residual**, AND each reformulation is provably degree-0 /
scaling-critical (no free sub-critical gain — verify, e.g. by a
homogeneity/trilinear-criticality argument):

1. **Declare a strange-loop FIXED POINT, not vocabulary noise.** The
   residual is Φ-invariant where Φ = (the reformulation map). Prove
   the invariance explicitly (channel-invariance + scale-invariance
   ⇒ self-similar/fractal). This is *progress* — it converts an open
   problem into a proved structural fact.
2. **Stop generating Φ-iterates.** Any further same-axis reformulation
   is provably futile (it lands on the fixed point). Continuing is
   the laundering loop; declaring terminus is the strawman. Neither —
   change axis.
3. **Isolate the UNIQUE transverse escape.** The only productive
   direction is an object *outside* the function-space Φ acts on —
   typically a genuine extra-scaling sub-critical input imported from
   another field by language-isomorphism (PATTERN-018). Enumerate
   candidate channels; MD-kill each; the survivors are the real open
   problem.
4. **Gate-bind every candidate with proved automatic retraction.**
   Name-the-limitation is face-saving (PATTERN-026 / Tier-3 catch).
   Bind each surviving channel to a DECIDABLE numeric pass-gate with
   a *proved* retraction theorem (commit-to-retract). Pre-flight the
   gate BEFORE the artifact is central.
5. **Tier-3 cross-provider audit each artifact.** Single-model
   Tier-2 misses the no-pass-gate face-saving sub-pattern;
   2/3-provider Tier-3 catches it. Re-audit after the fix.
6. **Amnesia-precheck (PATTERN-024) before EVERY iterate** — the
   fixed point is usually already named in the ledger under an older
   vocabulary; surfacing it early collapses the loop faster.

## Why it works

- Converts "endless reformulation" into a proved invariance theorem +
  a finite enumerated set of transverse channels — bounded, honest.
- Distinguishes the two failure modes the operator names: laundering
  loop (keep iterating) vs strawman terminus (stop). The correct
  third option is "prove the fixed point, change axis".
- The transverse channels, being from other fields, are the only
  place a genuine new idea can enter (PATTERN-018 isomorphism).

## Worked example (canonical)

NS Clay strict-margin arc, 2026-05-15 (ticks 544–556). ~10
reformulations + cross-field isomorphisms (heat-kernel off-diagonal,
elastostatics virial/mean-stress, Besicovitch/Vitali, Łojasiewicz–
Simon, Coifman–Rochberg) each MD-collapsed to one atom: a strictly
sub-critical exponent/ratio/gain, provably Φ-invariant because every
reformulation is NS-scaling-critical (tick545 trilinear-criticality
generalizes). The pattern: proved the fixed point (tick548/549),
stopped Φ-iterates, isolated transverse channels (Besicovitch β=5^-d
— falsifier fired; Coifman–Rochberg δ<1 — collapsed to the atom at
the δ=1 endpoint; Łojasiewicz–Simon γ>0 — unique survivor),
gate-bound with retraction (tick555 after Tier-3 3/3
PARTIAL_LAUNDERING → 2/3 PASS; tick556 proactive-gate → 3/3 PASS).

## HARD GUARD (refinement, 2026-05-16 — Tier-3 3/3 methodology catch)

Steps 3–4 ("isolate the transverse escape, gate-bind it") **must NOT
emit further conditional-reduction Lean artifacts**. Tier-3
cross-provider (3/3 on tick561) established: *naming an OPEN input as
a `Prop` placeholder + proving a conditional implication FROM it +
"forwarding" it is itself the PATTERN-026 face-saving sub-pattern,
no matter how honestly labeled* ("gate" → "conditional reduction" →
"isolated open link" are all paraphrase-laundered deferrals of
decidability). Once the transverse escape is isolated, the ONLY
non-laundering outputs are:

1. an **actual measurement / discharge** of the open input (real
   computation or proof), OR
2. a **single flat prose declaration**: "this is the open problem;
   the analytic recursion made no proof progress on it; here is the
   precise reduction; full stop" — with NO new Lean structure that
   re-performs name-and-defer, OR
3. **external dispatch** of the open input as a genuine PDE question
   to a strong prover (not a self-referential internal artifact).

Emitting tick(N+1) "honest-reframe" after a Tier-3 face-saving
verdict is the laundering loop this guard forbids. Stop iterating;
report or dispatch.

## Failure modes if skipped

- Vocabulary-drift amnesia loop (ANTI-PATTERN: same atom rediscovered
  ≥4× — see `project_strict_margin_perennial_atom`).
- False terminus / pessimism strawman.
- Face-saving "named but unbound" open links (PATTERN-026).
