---
id: META-PATTERN-023
name: multi_scope_pattern_application
version: 1
status: active
discovered: 2026-05-15
discovered_reason: |
  NS Clay closure session 2026-05-15: after operator-prompted minting of
  META-PATTERN-022 (gowers_first_with_content_layer_composition fixing the
  tool-not-consulted laundering between org/patterns and universal-language
  JSONL), the operator forwarded GPT-5.5's parallel A/B attack on the same
  PDE residual.

  GPT-5.5 produced FOUR substantive catches I had missed despite having access
  to the same catalogs:
    1. Premature Reynolds-defect framing-kill (META-PATTERN-021 catch at
       CHAIN scope: L₁ "approximating sequence Reynolds defect" ≠ L₂
       "blowup weak limit Reynolds defect").
    2. Wrong local norm (parabolic L^3 vs spatial L^3 for Kim-Kozono
       threshold comparison — chain-scope norm choice, not local-scope
       dimension check).
    3. Strategic pivot from "FullInvisibilityForcesRegularity" to
       "LocalL3LargeTypeIForcesVisibility" — Proof-Surface Compression
       at GLOBAL proof-obligation scope.
    4. Premature Lean encoding (tick508/509 shipped before recursion
       stabilized — META-PATTERN-022 binding rule violated at recursive
       scope).

  Diagnosis: I was applying META-PATTERN-022's composition only at LOCAL
  step scope. Every catch GPT-5.5 made was REACHABLE via the same catalog
  but lives at chain / recursive / meta scope. Composing the two catalogs
  is necessary but not sufficient; the composition must run at every scope
  of the proof structure.

  Operator: "maybe this deserves a meta pattern as well". Minted as
  META-PATTERN-023 to crystallize the multi-scope application discipline.

triggers:
  lexical:
    - applied_pattern_at_one_scope_only
    - per_step_verified_but_chain_not_verified
    - recursion_did_not_stabilize_but_encoded
    - sub_chain_not_audited_with_same_patterns
  structural:
    - META_PATTERN_022_composition_applied_at_local_scope_only
    - chain_level_load_bearing_piece_unaudited
    - recursive_sub_chain_pattern_application_skipped
    - meta_scope_failure_modes_not_examined
  problem_classes:
    - hard_mathematical_residual
    - pde_chain_closure
    - recursive_proof_obligation_audit

application_scopes:
  local:
    description: |
      Each transition step in a multi-step argument. ANTI-PATTERN-012's
      6-point per-step verification (form / direction / quantifier /
      domain / dimension / inclusion). The smallest scope; necessary
      but not sufficient.
    pattern_examples:
      - ANTI-PATTERN-012 per-step verification
      - Universal-language ops at single derivation step
  chain:
    description: |
      The OVERALL chain structure. Questions at this scope: is this the
      right chain to be running? what's the chain's central piece?
      do all links use the SAME interpretation of key objects (avoiding
      META-PATTERN-021 cross-layer drift)?
    pattern_examples:
      - META-PATTERN-021 applied to chain-internal layer drift
      - Proof-Surface Compression at full-chain scope
      - PATTERN-007 smuggling_audit on the chain's vocabulary as a whole
  recursive:
    description: |
      When sub-chains or sub-obligations arise (e.g., the chain
      decomposes into a tree of nested obligations). At this scope:
      apply the SAME patterns to each sub-chain; check the recursion has
      STABILIZED before encoding in Lean (per META-PATTERN-022 binding
      rule). Encoding before stabilization produces premature scaffolds.
    pattern_examples:
      - META-PATTERN-022 reapplied on each sub-chain
      - PATTERN-024 scientific_amnesia_precheck on sub-obligation
      - Recursive depth budget + stabilization criterion
  meta:
    description: |
      Failure modes that only appear when applying patterns across
      scopes. Examples: a META-PATTERN-021 cross-layer mismatch between
      sub-chain and parent-chain interpretations of an object; a
      vocabulary smuggle that's invisible at local scope but visible
      at chain scope.
    pattern_examples:
      - cross-scope META-PATTERN-021 (sub-chain L₁ vs chain L₂)
      - tool-not-consulted laundering at recursive scope (consulting
        catalog at local steps only, skipping at chain reformulation)
      - this META-PATTERN-023 itself (a meta-scope catch about the
        scope-application discipline)

binding_rule: |
  Every non-trivial PDE chain MUST be audited at all four scopes
  before shipping a closure claim or Lean encoding:
    1. Local scope:  ANTI-PATTERN-012 6-point per-step verification.
    2. Chain scope:  is this chain the right one? central piece
                     named explicitly? cross-layer alignment checked
                     for all key objects?
    3. Recursive scope:  has the recursion stabilized? are sub-chains
                         independently audited at the chain scope?
    4. Meta scope:  any cross-scope failure modes (e.g., sub-chain
                    cross-layer drift) examined?

  Failing any single scope is sufficient to invalidate the closure
  claim, even if the other scopes pass.

chain_position: precondition  # runs BEFORE any closure-claim artifact is shipped

sessional_catches:
  - tick508_premature_lean_scaffolding_before_recursion_stabilized
  - tick509_parabolic_vs_spatial_L3_norm_choice_unaudited_at_chain_scope
  - route_A_premature_framing_kill_aubin_lions_at_chain_scope
  - missing_strategic_pivot_to_visibility_completeness_at_global_scope

GPT55_comparison_evidence: |
  In a controlled comparison (same PDE residual, same catalog access, same
  session time-budget), GPT-5.5 produced 4 catches I missed. All 4 were
  reachable via the catalog I had; all 4 lived at chain / recursive /
  meta scope where I had applied patterns only at local scope. This is
  empirical evidence for the meta-pattern's discriminating value.

references:
  - META-PATTERN-022 gowers_first_with_content_layer_composition (composition of two catalogs)
  - META-PATTERN-021 cross_layer_alignment_failure (sibling: cross-layer at single scope)
  - ANTI-PATTERN-012 vocabulary_chain_laundering (local-scope per-step verification)
  - feedback_be_meta_darwin_to_self_2026_05_14.md (central user-memory — multi-scope rule added 2026-05-15)
  - docs/reference/structural_language_catalog.json (content layer)
falsifiable_test: |
  Once wired as a precondition on closure-claim artifacts, over N>=15 closure
  claims, artifacts carrying documented verification at all four scopes (local /
  chain / recursive / meta) must be subsequently overturned by a cold-shot or
  Meta-Darwin audit in <=15% of cases, versus a matched baseline of closure claims
  verified at local scope only; the four-scope overturn rate must be at least 30
  percentage points below the local-only baseline (motivated by the 2026-05-15 A/B
  comparison where GPT-5.5 produced 4 chain/recursive/meta-scope catches the
  local-only pass missed). If four-scope-verified closures are overturned at >15%,
  or within 30 points of the local-only baseline, the extra scopes catch nothing
  and the meta-pattern demotes.
  metric_source: closure-claim artifacts (F-rows / Lean files) with four-scope
  verification notes, joined to subsequent overturn events in
  external_prover_ledger.jsonl and catch_ledger.jsonl; matched local-only controls
  from pre-wiring closure claims.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# META-PATTERN-023 — Multi-Scope Pattern Application

## What it is

A meta-pattern naming the discipline that patterns/ops must be applied
at FOUR distinct scopes of any non-trivial proof chain:

1. **Local scope** (per-step): each transition in a chain.
2. **Chain scope**: the overall chain's structure and central piece.
3. **Recursive scope**: sub-chains arising during recursion.
4. **Meta scope**: cross-scope failure modes.

Applying patterns at one scope only — even with full catalog composition
per META-PATTERN-022 — is INSUFFICIENT. Every scope must be explicitly
verified before shipping a closure claim or Lean encoding.

## Distinction from META-PATTERN-022

META-PATTERN-022 specifies WHICH catalogs to compose (org/patterns +
universal-language JSONL + ANTI-PATTERN-012 failure check). It answers
"what to consult."

META-PATTERN-023 specifies WHERE in the proof structure to apply the
composition (local / chain / recursive / meta scopes). It answers "where
to apply what you consulted."

You can satisfy META-PATTERN-022 (consult all three catalogs) while
violating META-PATTERN-023 (apply only at local scope, miss chain-scope
catches). This is exactly what happened in the NS Clay session prior to
this meta-pattern minting.

## Distinction from META-PATTERN-021

META-PATTERN-021 names a specific FAILURE MODE (cross-layer alignment
failure at a single scope). META-PATTERN-023 names a DISCIPLINE for
APPLYING patterns across scopes. The two compose: META-PATTERN-021 can
fire at any scope, and META-PATTERN-023 prescribes checking for it at
all scopes.

## How to apply

For any closure-claim artifact (markdown note, Lean file, F-row, etc.):

1. **Local scope checkpoint**: enumerate ANTI-PATTERN-012 6-point
   verification at each transition step.
2. **Chain scope checkpoint**: name the chain's central piece;
   confirm no cross-layer drift between chain endpoints (META-PATTERN-021).
3. **Recursive scope checkpoint**: if sub-chains arise, recursively apply
   steps 1-2 to each. Confirm recursion has stabilized before any Lean
   encoding (per META-PATTERN-022 binding rule).
4. **Meta scope checkpoint**: examine cross-scope failure modes — does
   the sub-chain interpretation align with the parent chain's? Is the
   strategic framing the best one (Proof-Surface Compression at GLOBAL
   scope)?

If any checkpoint cannot be completed, downgrade the closure claim to
PARTIAL or INSUFFICIENT_EVIDENCE per the substrate's verdict alphabet
(PATTERN-001 rule 7).

## Why composition is non-trivial

Each scope catches different failure modes:
- Local scope misses: dimension-flips at single steps.
- Chain scope misses: strategic framing errors, cross-layer drift across the chain.
- Recursive scope misses: premature encoding before sub-chains stabilize.
- Meta scope misses: cross-scope drift, tool-not-consulted at higher levels.

A closure claim that passes local but fails chain is unsound. A claim
that passes local+chain but fails recursive ships premature scaffold.
A claim that passes local+chain+recursive but fails meta misses the
strategic best framing.

## Empirical motivation

In the 2026-05-15 NS Clay session, GPT-5.5 produced 4 catches I had
missed despite using the same catalogs. Diagnostic comparison (in
`feedback_be_meta_darwin_to_self_2026_05_14.md` "Multi-scope pattern
application discipline" entry):
- I applied patterns at LOCAL scope (per-step ANTI-PATTERN-012 checks).
- I did NOT apply at CHAIN scope (missed Aubin-Lions framing reset).
- I did NOT apply at RECURSIVE scope (encoded tick508/509 before recursion stabilized).
- I did NOT apply at META scope (missed strategic pivot from new-regularity to visibility-completeness).

GPT-5.5 applied at CHAIN + RECURSIVE + META scopes naturally; the
discipline gap was scope, not catalog.

## Cross-link

This meta-pattern is the named answer to the operator's 2026-05-15
question: "why is GPT-5.5 better than you?" Answer: not categorically
better; ran the same patterns at more scopes. META-PATTERN-023
crystallizes the missing scope discipline.
