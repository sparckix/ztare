---
id: ANTI-PATTERN-014
name: premature_settled_negative
status: active
discovered: 2026-05-16
cluster_size: 7
discovered_reason: |
  Operator flagged the SAME failure ≥4× in one thread: the agent
  declared a question "settled / impossible / structurally unobtainable /
  not autonomously sourceable / cannot be a (meta-)solver" and stopped —
  each time the negative was OVERCLAIMED. Meta-Darwin returned OVERCLAIMED
  on "GP-225 cannot be a solver" (category error: conflated retrospective
  mined-prior-impossibility with the WIRED forward generate-and-govern
  loop). Then "not autonomously sourceable" was re-caught: it had only
  checked the in-repo Carleson sandbox; external mining (gh api tree-diff
  vs newer Mathlib tag) trivially produced 184 added files. Pessimism
  hides at every boundary not crossed.
triggers:
  lexical: ["settled", "impossible", "structurally unobtainable", "not sourceable", "cannot be", "no honest path", "dead end", "prover-bound therefore", "out of scope therefore impossible"]
  structural:
    - a negative/closure verdict emitted WITHOUT a dispatched adversarial Meta-Darwin
    - search scoped to one boundary (in-repo only / one corpus) then generalized
    - a proven NARROW negative used to assert a BROAD negative (retrospective ⇒ forward; one regime ⇒ all regimes)
    - "needs a new idea, out of scope" used to mean "impossible" rather than "untested"
    - a terminal/settled verdict emitted while a decisive measurement is still in flight, or extrapolated from n=1 of an n-sample test
    - a settled-negative emitted in the same act as refusing to fabricate a positive under success/Stop-hook pressure (refusal-does-not-license-negation)
sub_modes:
  - boundary_unexhausted: declared not-sourceable/closed after checking only in-repo / one library / one corpus; external (gh api, web, newer-tag delta, adjacent field) never crossed.
  - scope_conflation: a true narrow result (no prior mineable from poisoned history; prover-bound in regime R) laundered into a broad claim (the forward loop is impossible; bound holds in all regimes).
  - audit_as_terminus: a verification/governance artifact treated as proof the generative configuration cannot exist, when only the discriminator half was built and the generator never wired/run.
  - pessimism_in_the_correction: the relapse occurs INSIDE an act of correcting pessimism (e.g. "I concede X, therefore Y is impossible" — Y also unchecked).
  - verdict_scope_conflation: an ARTIFACT-scoped discipline/laundering verdict (Tier-3 PATTERN-026, a governance audit of FRAMING — "is this file face-saving?") is read as a falsification of the underlying SCIENTIFIC IDEA, and the idea is deleted/recorded settled-negative. A genuine-but-unproved idea encoded as decorative theorems and a vacuous/circular idea yield the IDENTICAL discipline verdict; the linter cannot distinguish them, so the worse one must not be assumed. (Empirical signature 2026-05-16: Tier-3 3/3 PARTIAL_LAUNDERING on a Birkhoff–Hilbert Lean tick — correct about the encoding — was conflated into "the idea is mode (c), killed"; a 2nd steelman-first red-team showed 3/4 kill-objections were reviewer error.)
  - single_attack_only_adversary: a settled-negative on a scientific idea rested on ONE dispatched adversary that only attacked (no steelman-first), accepted without independent corroboration. One attack-only adversary technically satisfies "a dispatched Meta-Darwin" yet is itself a noisy diagnostic.
  - in_flight_or_n1_preconclusion: a "terminal/settled-negative" emitted while the decisive measurement that would resolve it is STILL RUNNING, or extrapolated from n=1 of an n-sample test (the first datapoint treated as the ceiling). The in-flight/full result is the only authority; a partial or single observation never settles the question. Mechanism — refusal_does_not_license_negation: correctly refusing to fabricate a POSITIVE under directive / Stop-hook / goal pressure is conflated with license to declare the NEGATIVE settled. These are distinct epistemic acts; integrity about not over-claiming success does NOT transfer to asserting the symmetric failure. (Empirical signature 2026-05-16: after a self-supplied solver run was Meta-Darwin-killed for gaming, a "TERMINAL — world-class not attainable" verdict was written off n=1 of a still-running independent adversary corpus; the completed 10/10 run produced 5 genuine closures + 0 false ratifications — the terminal claim was wrong by a wide margin.)
detected_by: >
  Pre-emission gate: before any settled-negative is stated, REQUIRE
  (a) a dispatched adversarial Meta-Darwin / darwin_idea_killer on the
  negative itself (not in-artifact self-audit — necessary but
  insufficient), (b) an explicit "external sources exhausted" checklist
  (in-repo / gh api / web / newer-version delta / adjacent field), and
  (c) a one-line statement of exactly what WAS proven negative vs what
  was NOT ruled out. Composes PATTERN-002 (darwin_idea_killer) +
  arXiv/cross-field isomorphism poll. Routes under apparatus_self_audit.
  A discipline/laundering verdict (Tier-3 PATTERN-026, closure-claim
  linter) is scoped to ARTIFACT FRAMING ONLY and NEVER adjudicates
  idea validity; the linter now emits `verdict_scope` +
  `disposition` saying exactly this. Deleting a laundering artifact
  is correct; recording the IDEA as settled-negative from that
  verdict is the conflation. A single attack-only adversary is
  insufficient: a scientific settled-negative additionally requires
  a STEELMAN-FIRST review AND (>=2 INDEPENDENT adversaries OR the
  operator inversion-reflex).
mitigated_by: >
  The settled-negative is BLOCKED until the Meta-Darwin verdict + the
  external-exhaustion checklist + the narrow-vs-broad delimitation are
  attached. For an idea flagged only by an ARTIFACT discipline verdict:
  re-encode with genuine content OR route to independent scientific
  review — do NOT infer idea-dead. For a kill resting on adversary
  dispatch: require steelman-first + >=2 independent adversaries (or
  operator inversion) before recording. "Not yet falsified, not yet
  vindicated" is the default honest state for any untested
  discriminating experiment — never "settled". Replace "cannot" with
  the precise gated experiment. NO settled/terminal verdict may be
  emitted while the decisive measurement is in flight or at n=1 — block
  until the run completes / n is adequate; refusing to fabricate a
  positive does not license concluding the negative.
falsifiable_test: >
  Fires iff a settled/negative/impossible claim is emitted and ANY of:
  no Meta-Darwin dispatched on it; search scoped to a single boundary;
  a retrospective/single-regime result generalized; an ARTIFACT
  discipline/laundering verdict treated as idea-falsification; a kill
  resting on a single attack-only adversary with no steelman-first /
  no independent second; the verdict is emitted while the decisive
  measurement is still running or off n=1; the negative is asserted in
  the same act as refusing to fabricate a positive under pressure;
  OR the claim is refuted within the same
  thread by crossing one more boundary (signatures seen 2026-05-16:
  external mine refuted "not autonomously sourceable" in one command;
  a 2nd steelman-first red-team refuted 3/4 objections of a
  single-adversary Birkhoff kill).
references:
  - ~/.claude/.../memory/feedback_solver_pessimism_overclaimed_metadarwin_2026_05_16.md
  - ~/.claude/.../memory/feedback_dont_preconcede_missing_hypothesis_2026_05_15.md
  - ~/.claude/.../memory/feedback_be_meta_darwin_to_self.md
notes: >
  Distinct from ANTI-PATTERN-013 (lean_closure_laundering = false
  POSITIVE). This is the false NEGATIVE / defensive-pessimism dual:
  over-claiming impossibility to stop work. Sessional-friction-grade
  (≥4× in one thread); also belongs in docs/concepts/anti_pattern_catalog.md.

## Causal sub-mode: Consensus Gravity (the Millennium Guardrail)

**Trigger.** The domain is heavily indexed in training data as
"unsolved/impossible/open" (e.g. a Millennium problem). **Mechanism.**
Next-token probability biases hard toward refutation; the agent
hallucinates roadblocks (a fake CZ scale-ε; a Zeno/geometric-series
misread) to force the conversation back into the "it is unsolved"
consensus basin — a statistical immune system against novel proofs.
**This is the dominant CAUSAL TRIGGER of ANTI-PATTERN-014 firings in
famously-open domains** (not a separate pattern — logged here per
MECE audit 2026-05-16). **Defense:** anonymize — strip the famous
domain labels and evaluate the raw logic as an abstract operator
problem (see PATTERN terminal_de_anonymization_reformulation); +
ruthless dis-aggregation (force the exact geometric exchange rate,
not the philosophy).
