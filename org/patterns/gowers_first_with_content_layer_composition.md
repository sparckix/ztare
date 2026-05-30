---
id: META-PATTERN-022
name: gowers_first_with_content_layer_composition
version: 1
status: active
discovered: 2026-05-15
discovered_reason: |
  NS Clay closure session (ticks 495-508) repeatedly fired ANTI-PATTERN-012
  (vocabulary_chain_laundering) — 5 sessional catches at severity 7-9 — while
  nominally running PATTERN-025 (gowers_first_formalize_second). Operator
  meta-question 2026-05-15: "this seems in itself a composition pattern of
  patterns. I fail to see how the orchestration menu and the language JSONL
  are related."

  Investigation revealed: PATTERN-025 specifies the WORKFLOW SEQUENCE
  (informal-before-formal); the universal-language catalog
  (`docs/reference/structural_language_catalog.json`)
  specifies the MATHEMATICAL CONTENT (Problem Reformulation, Auxiliary Comparison
  Object, Limit-Passage Property Inheritance, Sharpness/Failure-Witness
  Construction, etc.). These two catalogs are at DIFFERENT abstraction layers
  (research-process vs mathematical-content) but they MUST COMPOSE for Gowers-
  style PDE attacks to be sound.

  Running PATTERN-025 with EMPTY content (no explicit universal-language ops
  enumerated) is exactly the failure pattern caught 5 times this session:
  vocabulary-chain laundering. The composition was previously undocumented in
  any catalog — operator surfaced the gap. This META-PATTERN names the
  composition explicitly so future sessions can compose all three layers from
  the start.

triggers:
  lexical:
    - gowers_first
    - redescribe_and_replace
    - informal_before_lean
    - PDE_residual_attack
    - theorem_surface
    - countermodel_construction
    - vocabulary_association  # warning sign — likely scaffold-without-content
  structural:
    - PATTERN_025_invoked_without_content_layer_enumeration
    - multi_step_PDE_chain_constructed_without_per_step_explicit_verification
    - universal_language_catalog_NOT_consulted_during_attack
    - operator_must_prompt_to_get_content_layer_used
  problem_classes:
    - hard_mathematical_residual
    - PDE_chain_closure
    - formal_verification

composition_layers:
  scaffold:
    pattern: PATTERN-025
    role: workflow_sequencing
    content: |
      Workflow scaffold (when to redescribe-and-replace, when to formalize,
      when to introduce countermodel, when to ship Lean).
  content:
    catalog: docs/reference/structural_language_catalog.json
    role: mathematical_moves
    content: |
      Specific mathematical content moves applied at each scaffold step:
        - PDE estimate craft ops (7): Auxiliary Comparison Object Construction,
          Regime/Class Scoping, Quantitative Threshold Dichotomy, Limit-Passage
          Property Inheritance, Sharpness/Failure-Witness Construction,
          Proof-Surface Compression, Distribution/Tail Upgrade; plus Candidate G
          Representation/Coordinate Reformulation.
        - Universal v5 ops (18): Problem Reformulation & Reduction, Generalization
          & Abstraction, Decomposition & Recomposition, Local-to-Global Assembly,
          Canonical Form & Invariance, Cross-Domain Translation, Iterative
          Refinement, Recursive Decomposition, Duality & Adversarial Framing,
          Layered Approximation & Convergence, Extremal Method, Probabilistic
          & Stochastic Methods, Dimensional & Structural Lifting, Constraint
          Imposition & Propagation, Characterization by Obstruction,
          Internalization & Self-Reference, Axiomatization & Foundational Repair,
          Controlled Universe Extension.
        - Op tiers (12) and two-cultures pairs (4) provide additional
          structural orientation.
  failure_check:
    anti_pattern: ANTI-PATTERN-012
    role: per_step_verification_gate
    content: |
      Vocabulary-chain laundering check per transition: 6-point verification
      of form / direction / quantifier / domain / dimension / inclusion before
      moving to the next step in the chain.

binding_rule: |
  Every invocation of PATTERN-025 MUST:
    1. Begin by enumerating which universal-language ops will be applied
       (treat structural_language_catalog as a CHECKLIST, not optional reference).
    2. Per-step apply the ANTI-PATTERN-012 6-point verification gate.
    3. Document the recursive application of ops on any open sub-theorem that
       arises (the catalog is recursively usable on its own output).

chain_position: precondition  # runs BEFORE any Gowers-first PDE attempt is executed

sessional_catches:
  - tick495_variation_charge_resolution
  - tick496_minkowski_content_reduction
  - tick498_serrin_5_4_exponent_miscalc
  - tick501_helicity_pigeonhole_nested_disjoint
  - tick504_frobenius_2foliation_dual_confusion

references:
  - PATTERN-025 gowers_first_formalize_second
  - ANTI-PATTERN-012 vocabulary_chain_laundering
  - META-PATTERN-021 cross_layer_alignment_failure  # sibling meta-pattern
  - docs/reference/structural_language_catalog.json
  - docs/concepts/anti_pattern_catalog.md (SB-4 parallel human-readable entry)
  - feedback_be_meta_darwin_to_self_2026_05_14.md (central user-memory)
falsifiable_test: |
  Once wired as a precondition on Gowers-first PDE attacks, over N>=20 PATTERN-025
  invocations, artifacts that explicitly enumerate the applied universal-language
  ops by catalog name must fire ANTI-PATTERN-012 (vocabulary_chain_laundering) at a
  per-artifact rate at least 60% LOWER than artifacts produced without
  op-enumeration (the pre-wiring baseline: 5 of 7 tick495-507 attempts fired
  ANTI-PATTERN-012; tick508, which enumerated 4 ops, did not). If op-enumerated
  artifacts launder at a rate within 60% of empty-scaffold artifacts, the
  content-layer composition prevents nothing and demotes.
  metric_source: pattern_deployment_ledger.jsonl (universal_ops_enumerated flag per
  PATTERN-025 artifact) joined to ANTI-PATTERN-012 firing events in
  catch_ledger.jsonl (vocabulary_chain_laundering category, per-artifact).
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# META-PATTERN-022 — Gowers-First with Content-Layer Composition

## What it is

A composition meta-pattern naming the structural relationship between
three previously-independent catalogs:

| Layer | Catalog | Role |
|---|---|---|
| Scaffold | `org/patterns/gowers_first_formalize_second.md` (PATTERN-025) | workflow sequencing |
| Content | local structural-language catalog artifact | mathematical moves |
| Failure-check | `org/anti-patterns/vocabulary_chain_laundering.md` (ANTI-PATTERN-012) | per-step verification |

The composition must run SIMULTANEOUSLY. Running any layer in isolation
produces a known failure mode (see Sessional catches above).

## Why it appears

The two source catalogs were built independently:
- `org/patterns/*.md` (2026-05-08 mining pass): research-process discipline.
- `structural_language_catalog_20260514.json` (2026-05-14): mathematical-content
  discipline.

Their composition relationship was not documented anywhere until this
meta-pattern. Sessions consuming PATTERN-025 by reading its scaffold
without ALSO consulting the universal-language catalog produced empty-
scaffold Gowers attacks — every transition was justified by vocabulary
association rather than by an explicit op from the catalog, firing
ANTI-PATTERN-012 repeatedly.

## How to apply

For any PDE residual / formal-verification target where Gowers-first
sequencing is appropriate (statement_stability_unknown, carrier_or_
observable_identity_uncertain, etc. — see PATTERN-025 triggers):

1. **Open the scaffold**: invoke PATTERN-025's workflow sequence.
2. **Load the content catalog**: open
   `docs/reference/structural_language_catalog.json`.
   Skim the 7 PDE craft ops, Candidate G, 18 universal v5 ops, and 12 op tiers.
3. **Enumerate ops to apply**: for the specific residual, identify which
   3-5 ops are most relevant (e.g., for a weak-limit defect question:
   Problem Reformulation + Auxiliary Comparison Object + Limit-Passage
   Property Inheritance + Sharpness/Failure-Witness Construction).
4. **Apply ops one at a time**: at each step, name the op being applied;
   run the 6-point ANTI-PATTERN-012 verification on the transition.
5. **Recursively apply**: when a sub-theorem or lemma surfaces, re-open
   the catalog and re-enumerate ops. The catalog is recursively usable.
6. **Encode in Lean ONLY IF the recursive ops have stabilized**: per
   PATTERN-025's binding rule, formalize after the informal redescribe-
   and-replace converges.

## Why composition is non-trivial

Each layer fills a gap the other layers cannot:
- The scaffold (PATTERN-025) cannot specify which mathematical moves to
  apply — that's content-level, not workflow-level.
- The content catalog cannot specify when to formalize vs when to keep
  informal — that's workflow-level, not content-level.
- The failure-check (ANTI-PATTERN-012) cannot guide what to do, only
  catch what went wrong — it's gate-level, not generative.

Only the composition of all three is generative AND safe.

## Cross-link

This meta-pattern is the named answer to the operator's 2026-05-15
question: "the orchestration menu and the language JSONL — how are they
related?" Answer: at different abstraction layers (process vs content),
composed via META-PATTERN-022.
