---
id: ANTI-PATTERN-002
name: sorry_obligation_laundering
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: ["sorry-free", "moved to caller", "the obligation is now", "_h_X is bound with underscore", "STRONG WEAK PASS", "PASS-with-displacement"]
  structural:
    - hypothesis_renamed_A_to_B_with_claim_B_is_more_elementary
    - upstream_constructors_still_consume_A_equivalent_hypotheses
    - underscore_bound_parameter_never_consumed_in_body
    - sorry_count_decreased_but_caller_obligation_count_unchanged
    - composition_layer_sorry_free_only_because_only_one_sub_lemma_invoked
  problem_classes: [apparatus_self_audit, hard_mathematical_residual]
detection_protocol:
  primary: PATTERN-007  # smuggling_audit (central-step enumeration)
  secondary: PATTERN-002  # darwin_idea_killer
  rule:
    - "When a refactor proposes hypothesis A → hypothesis B with claim B is at a lower analytic level, ENUMERATE the upstream constructors that produce B. If every such constructor still consumes A-equivalent hypotheses, refactor is vocabulary-laundering."
    - "When a constructor binds a hypothesis parameter with underscore (never consumed in body), the obligation has NOT been discharged, it has been MOVED to the caller's M structure or to a transitive callee."
    - "When a composition theorem is sorry-free 'only because step 4 is the only step invoked', and steps 2-3 are sorry-bearing transitive dependencies of step 4, the composition is sorry-free-modulo-its-named-callees, which is sorry-bearing in substance."
mitigation:
  - "Require at least ONE new upstream constructor whose hypothesis is classically discharged at a strictly weaker level than A, without it, the refactor is vocabulary, not analytic."
  - "Document underscore-bound parameters explicitly: 'recorded as input parameter, NOT consumed inside this constructor's body'. Treat the witness Prop as caller-burden tracker, not discharge."
  - "When evaluating sorry counts, count obligations at the leaf-Prop boundary, not at the composition theorem boundary. Sorry-free composition over sorry-bearing leaves is bookkeeping, not closure."
  - "Honest verdict labels: 'PASS-with-displacement' or 'WEAK PASS', not 'STRONG PASS'. Hybrid grades like 'STRONG WEAK PASS' that don't appear in the pre-registration's verdict alphabet are inflation."
examples:
  - id: catch_21e
    summary: "Atom 8 defect-positivity smuggling, three positivity floors disjuncted in a witness Prop. Refusing to ship a sorry-laden bridge that would smuggle small-divisor / open analytic content through a positivity certificate."
    file: atom8_defect_positivity_clay_level_open_2026_05_08.md
  - id: catch_26
    summary: "_of_liminf_eq refactor framed as 'Onsager-1/3-open → weak-L² LSC of dissipation (uncontroversial)'. Mechanical plumbing real; semantic claim laundered: obligation moved to selfTax_liminf_eq_relaxed; both upstream constructors of that field still take Tendsto / monotone-iSup."
    file: anti_laundering_catch_26_vocabulary_relabel_refactor_2026_05_08.md
  - id: catch_30
    summary: "Pincer GENUINE verdict, `_h_weak_l2_lsc` parameter underscore-bound; analytic obligation displaced to caller's M structure. T9_closure_attempt sorry-free at composition layer only because its only invoked step is sorry-free; transitive dependencies sorry-bearing."
    file: pincer_meta_darwin_audit_2026_05_08.md
falsifiable_test:
  description: "For each refactor that claims an analytic reduction, enumerate the upstream constructors of the renamed structure field. The anti-pattern is firing iff every constructor still requires hypotheses analytically equivalent to the original."
  binary_check: "exists_constructor_with_strictly_weaker_hypothesis(field), firing iff False."
  not_trivial: "Returns 'not firing' (True) when a genuine bucket-1 constructor exists (e.g. Lions tightness Prop has Mathlib IsTightMeasureSet path with Prokhorov closure, bucket-1 reachable per catch #27 note). Therefore the test is NOT True := by trivial."
chain_position: post  # runs AFTER any refactor or sorry-elimination claim
references:
  - "PATTERN-007 smuggling_audit"
  - "anti_laundering_catch_26_vocabulary_relabel_refactor_2026_05_08.md"
  - "atom8_defect_positivity_clay_level_open_2026_05_08.md"
  - "pincer_meta_darwin_audit_2026_05_08.md"
---

# ANTI-PATTERN-002, Sorry-Obligation Laundering

## What it is

A claimed reduction in proof obligation (sorry-elimination, hypothesis
weakening, "now uncontroversial") that did not actually discharge the
obligation. Three sub-modes:

1. **Field-renaming displacement** (catch #26): hypothesis A renamed
   to hypothesis B at the constructor signature; B's upstream
   constructors still consume A-equivalent hypotheses, so the
   obligation just moved to a different boundary.
2. **Underscore-binding** (catch #30): a hypothesis parameter is
   bound with `_h_...` and never consumed in the body; the
   constructor's own docstring admits this; the analytic burden
   lives in producing the M whose alignment hypotheses match.
3. **Composition over sorry-bearing leaves** (catch #30): the
   composition theorem is sorry-free at the top, but only one sub-
   lemma is actually invoked, and that sub-lemma's transitive
   dependencies are themselves sorry-bearing.
4. **Refusal-with-receipts is a valid output** (catch #21e): the
   correct response when an atom would smuggle open analytic content
   is a refusal note, NOT a sorry-laden bridge file that would
   compile but launder.

## Why it appears

Sorry-counting is a central metric in Lean projects, and the
incentive to "make sorry count go down" is strong. The cheap path
is to refactor the obligation into a different position rather
than discharge it. Without explicit boundary-counting, the metric
gets gamed.

## Why it matters

A "sorry-free" Lean file whose obligations have been displaced to
caller-side data structures is theatrical closure. Reviewers (and
future agents) reading the file see green; the actual analytic
content is hidden in the M-producing constructors that no one is
auditing.

## Detection protocol

Apply PATTERN-007 (smuggling_audit) on every claimed refactor:

1. List the central steps in the new structure's signature.
2. For each step, identify what fact it requires.
3. Is that fact equivalent to the obligation the refactor was
   supposed to lower?
4. Cross-reference: does any concrete upstream constructor produce
   the new field at a strictly weaker analytic level? If not,
   refactor is vocabulary.

For composition theorems: walk every named callee. If any callee
in the transitive graph is sorry-bearing, the composition is
sorry-free-modulo-callees, not sorry-free in substance.

## Mitigation when detected

- Honest framing in docstring: "MECHANICAL plumbing reduction;
  SEMANTIC framing was vocabulary-laundering, obligation moved
  to field X, upstream constructors still consume A-equivalent."
- Demand at least one new upstream constructor at a strictly
  weaker analytic level.
- Reject hybrid verdict labels not in the pre-registration alphabet
  ("STRONG WEAK PASS" → demote to honest "WEAK PASS" or
  "PASS-with-displacement").

## Falsifiable test (catalog-level)

`exists_constructor_with_strictly_weaker_hypothesis(field)`. The
anti-pattern fires iff this is False, every constructor still
takes A-equivalent.

NOT trivially True: catch #27's downgrade path documents a real
bucket-3 → bucket-1 gradient (IsTightMeasureSet + Prokhorov). The
Lions tightness Prop has a genuine constructor at strictly weaker
analytic level. The DiPerna-Majda Prop does not. The test
discriminates.

## Cross-references

- PATTERN-007 (`org/patterns/smuggling_audit.md`)
- PATTERN-002 (`org/patterns/darwin_idea_killer.md`)
- `projects/ns_millennium_hunt/workspace/research_notes/anti_laundering_catch_26_vocabulary_relabel_refactor_2026_05_08.md`
- `projects/ns_millennium_hunt/workspace/research_notes/atom8_defect_positivity_clay_level_open_2026_05_08.md`
- `projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md`
