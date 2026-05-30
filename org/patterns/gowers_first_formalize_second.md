---
id: PATTERN-025
name: gowers_first_formalize_second
version: 1
status: candidate
discovered: 2026-05-14
discovered_reason: |
  NS route-1 ticks 353-356 showed a repeated discovery sequence: informal
  theorem-surface audit found the wrong observable before Lean formalization
  could.  Lean then served as verifier, memory, and anti-smuggling guard for
  the corrected primitive.  The pattern is sequencing-specific and therefore
  distinct from PATTERN-007 smuggling_audit and PATTERN-002 darwin_idea_killer.
triggers:
  lexical:
    - lean_first
    - formalize_first
    - theorem_surface
    - carrier
    - observable
    - positive_flux
    - signed_flux
    - countermodel
    - no_go
    - same_carrier
    - pressure_l2
    - duchon_robert
  structural:
    - statement_stability_unknown
    - carrier_or_observable_identity_uncertain
    - sign_scale_telescope_or_multiplicity_unknown
    - residual_is_theorem_or_domain_gap
    - single_interface_source_would_not_close_next_dependency
    - upstream_branch_dominance_unknown
    - proposed_formal_field_resembles_target_conclusion
    - recent_no_go_changed_the_theorem_surface
    - informal_countermodel_can_be_written_before_formal_proof
  problem_classes:
    - hard_mathematical_residual
    - too_complex_direct_attack
composition:
  precedes:
    - PATTERN-002  # darwin_idea_killer: attack the informal surface.
    - PATTERN-007  # smuggling_audit: audit the survivor before encoding.
    - PATTERN-008  # three_leg_verification: check paper proof / scout / Lean.
  complements:
    - PATTERN-024  # scientific_amnesia_precheck: check prior basin first.
    - PATTERN-012  # prediction_ledger: price the branch before formal work.
  not_a_replacement_for:
    - PATTERN-006  # tautology_trap_detector: still needed after a surface exists.
    - PATTERN-009  # independent_cas_verification: still needed for numerical/CAS claims.
spawn:
  mode: deterministic_pre_tick
  cli:
    generic: scripts/public/control/formalization_sequence_classifier.py
  output_schema: formalization_sequence_report_v1
  storage_path: analytics/public/queries/formalization_sequence/latest.json
chain_position: pre
content_layer: docs/reference/structural_language_catalog.json
content_layer_note: |
  This pattern is the WORKFLOW SCAFFOLD (when to run informal redescribe-and-replace
  before Lean formalization). The actual MATHEMATICAL CONTENT — the redescribe-and-
  replace moves themselves — lives in the universal-language catalog:
    - PDE estimate craft ops (7): Auxiliary Comparison Object Construction, Regime/
      Class Scoping, Quantitative Threshold Dichotomy, Limit-Passage Property
      Inheritance, Sharpness/Failure-Witness Construction, Proof-Surface Compression,
      Distribution/Tail Upgrade; plus Candidate G Representation/Coordinate Reformulation.
    - Universal v5 ops (18): Problem Reformulation & Reduction, Generalization &
      Abstraction, Decomposition & Recomposition, Local-to-Global Assembly, etc.
  Running this pattern WITHOUT consulting the content layer is a recurring meta-failure
  (sessional catches 2026-05-15: 5 instances of ANTI-PATTERN-012 vocabulary_chain_laundering
  while running PATTERN-025 with empty content scaffold). MITIGATION: every Gowers-first
  invocation MUST enumerate which universal-language ops are being applied, treating
  the JSONL as a checklist not optional reference.
references:
  - scripts/public/control/formalization_sequence_classifier.py
  - src/ztare/research_director/formalization_sequence.py
  - analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md
  - research_areas/EXPERIMENT_TRACK_RECORD.md#F-GP225-NS-TRANSPORT-FUNCTIONAL-MISMATCH-IS-THE-LIVE-OBSTRUCTION-20260514-354
  - research_areas/EXPERIMENT_TRACK_RECORD.md#F-GP225-NS-POSITIVE-CUTOFF-FLUX-RECEIPT-IS-CONDITIONAL-NOT-PROOF-20260514-355
  - docs/reference/structural_language_catalog.json
  - org/anti-patterns/vocabulary_chain_laundering.md
  - META-PATTERN-022 (gowers_first_with_content_layer_composition)
falsifiable_test: |
  Once routed as a pre-tick gate on unstable-carrier proof branches, over N>=15
  dispatches classified gowers_first_required, at least 60% must yield a concrete
  payoff — a smaller formal primitive than the original target, a no-go guard
  blocking a prior shortcut, or a named missing hypothesis that changes the next
  branch choice — AND for theorem/domain residuals a 5+ node dependency DAG must
  name the first unproved estimate. This 60% payoff rate must exceed the payoff
  rate of matched Lean-first dispatches on comparably unstable branches by >=20
  percentage points. If the payoff rate is below 60% or within 20 points of
  Lean-first, the informal-first sequencing earns nothing and demotes.
  metric_source: formalization_sequence_report_v1 outputs and downstream F-rows;
  PATTERN-025 dispatches tagged in pattern_deployment_ledger.jsonl, payoff
  classified from the F-row (primitive size / no-go guard / named hypothesis
  fields).
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-025 — Gowers-First, Formalize-Second

## Problem

At a proof frontier, the main uncertainty is often not a missing formal
lemma.  It is whether the proposed theorem is measuring the right object.
Formalizing too early can turn that uncertainty into a polished conditional
structure whose decisive field is the original PDE problem in disguise.

This is most common when the bridge involves:

- carrier identity;
- sign or positive-part extraction;
- scale power;
- telescoping;
- bounded multiplicity;
- pressure, commutator, or boundary terms that can cancel;
- a receipt or visibility object whose definition might be chosen after the
  target is known.

## Pattern

Before writing Lean or another formal interface, run a short informal proof
or countermodel pass:

1. State the intended theorem in ordinary mathematical language.
2. Name the observable, carrier, sign convention, scale, and telescope.
3. Write a 10-30 line proof sketch.
4. Try to falsify it with the smallest packet, tree, shear, cancellation, or
   boundary model.
5. Classify the result:
   - `PROOF_ROUTE`: exact primitive and proof skeleton survive.
   - `NO_GO`: first illegal inference and countermodel are identified.
   - `MISSING_HYPOTHESIS`: the smallest non-tautological extra input is named.
6. If the residual is still theorem/domain-level, traverse the dependency DAG
   before formalizing:
   - list at least five downstream/upstream nodes from current hinge to the
     intended closure;
   - mark each node as already mechanized, proof-route, missing hypothesis,
     or no-go;
   - identify the first unproved PDE/domain estimate and the first upstream
     branch-dominance hinge;
   - formalize only the node that changes the next action, not the whole DAG.
7. Formalize only the survivor: corrected primitive, route consequence, and
   no-go guard against the dead shortcut.

Lean remains essential, but its role is verifier, memory, and anti-smuggling
guard after the theorem surface stabilizes.

## Dependency DAG Traversal Addendum

When a proof tick produces a useful local source but the residual remains a
theorem/domain gap, do not stop at the first formal interface.  Run a
dependency-DAG traversal in prose first.  The required output is:

- current hinge;
- 5+ dependency nodes to closure, including both downstream scalar consumers
  and upstream branch conditions;
- status of each node: `mechanized`, `proof_route`, `missing_hypothesis`,
  `no_go`;
- first illegal inference if the current local source is overpromoted;
- next PDE/domain estimate to attack;
- next branch-dominance or exhaustion theorem, if any.

The traversal is successful if it changes the next action from "add another
wrapper/source field" to a sharper proof node, countermodel, or branch split.
It fails if it merely restates the same local bridge in more words.

## MECE Boundary

- **PATTERN-025** decides sequencing: informal theorem-surface discovery before
  formal encoding when the statement is unstable.
- **PATTERN-007** checks an already proposed route for hidden reintroduction of
  the old obstruction.
- **PATTERN-006** catches definitions or fields that are the conclusion in
  disguise.
- **PATTERN-022** bundles deterministic gates once the artifact contract is
  already stable.

If the theorem is already known and the uncertainty is only formal proof
mechanics, use Lean-first directly.  PATTERN-025 should not slow routine
formalization.

## Vocabulary Fingerprint

This pattern is not outside the existing GP-216 vocabulary; it composes it in
a specific order.

- **Universal research ops:** `core_03` canonical decomposition for splitting
  carrier/observable/sign/scale; `core_05` extremal or countermodel analysis;
  `core_07` framework generalization only after the survivor is stable.
- **Theory-building ops:** `tb_06` tacit pattern formalization, but delayed
  until after the informal surface audit; `tb_LAK2` proof-analysis under
  counter-example when a packet or shear model kills the old statement.
- **Problem-solving ops:** `ps_06` proof by estimate chaining once the right
  observable is fixed.
- **PDE estimate-craft ops:** `pec_a` auxiliary comparison object, `pec_c`
  channel/threshold split, `pec_e` sharpness witness, `pec_h` distribution/tail
  upgrade, and `cand_g` observable reformulation.

The mechanized classifier emits this fingerprint so RD ticks can cite the
universal/theory-builder/problem-solver vocabulary instead of treating this as
a one-off NS trick.

## NS Instance

The route-1 transport branch showed the pattern:

- Old target: prove normalized transport leakage is paid by a DR/pressure
  transport receipt.
- Informal no-go: coherent shear/material transport can have positive cutoff
  leakage while pressure-`l = 2` and DR charges vanish.
- Corrected primitive: same-carrier positive cutoff-flux receipt, or a
  visible/invisible split routing the unpaid part to commutator,
  local-quadratic, or no-invisible-profile machinery.
- Formalization: Lean encoded the corrected receipt, the no-go guards, and the
  scalar route consequence.

The mathematical progress came from identifying the wrong observable before
formal work.  The formal work made that insight durable.

The later route-1 tail-square branch added the DAG-traversal variant:

- Immediate local hinge: `X_tail`/`tailSquareFunction` needed control by the
  finite active-tail budget.
- Active-only no-go: passive fresh-frequency packet mass can persist with
  small active same-cutoff leakage.
- Corrected object: active-or-passive lineage schedule carrying active source,
  passive caloric persistence, same-lineage Duhamel recharge, and
  cutoff/commutator residuals.
- Dependency DAG: fresh-frequency persistence → finite lineage schedule budget
  → same-carrier tail control → finite-tail prefix strictness → route failure
  requires nonsummable mass → route-1 closure → upstream branch dominance.

This prevented the tick from stopping at a single Lean source and exposed the
next live PDE estimate: fresh-frequency persistence from the localized
frequency energy identity.

## Falsifiable Test

The pattern is working iff, on a hard proof branch with unstable carrier or
observable, it produces at least one of:

- a smaller formal primitive than the original target;
- a no-go guard that blocks an old shortcut;
- a named missing hypothesis that changes the next branch choice.

It is not working if it only produces a longer prose preamble before encoding
the same wrapper field.

For theorem/domain residuals, add a stricter test: the pattern is not complete
until a 5+ node dependency DAG names the first unproved estimate and the first
upstream branch-dominance hinge.

## Mechanized Precheck

Run:

```bash
./venv/bin/python scripts/public/control/formalization_sequence_classifier.py --branch-text "..."
```

The classifier returns `gowers_first_required`, `lean_first_ok`, or
`mixed_sequence`, plus the exact trigger terms.  It is a cheap gate, not a
semantic oracle.  The RD still owns the final sequencing decision.
