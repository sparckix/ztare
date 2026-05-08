---
id: ANTI-PATTERN-003
name: vocabulary_smuggling
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: ["newly-surfaced architecture-level dichotomy", "the 4-vocabulary translation reveals", "framework convergence", "STRONG WEAK PASS", "1960s textbook taxonomy in 2026 vocabulary"]
  structural:
    - vocabulary_outputs_pre_disjoint_by_op_definitional_scope
    - rediscovers_existing_catalog_entries_in_new_vocabulary
    - hybrid_verdict_grade_not_in_pre_registration_alphabet
    - n_chosen_vocabularies_collude_to_produce_n_axes_split
  problem_classes: [pre_category_emergence, apparatus_self_audit]
detection_protocol:
  primary: PATTERN-003  # reducer (P13) — strip elite vocab, see what remains
  secondary: PATTERN-006  # tautology_trap_detector
  rule:
    - "When N vocabularies produce a (k, N-k) split that gets framed as 'newly-surfaced axis', verify the vocabularies' output spaces are NOT pre-disjoint. Swap one for a different op; if the split flips, the axis was rigged."
    - "Search the architecture's prior catalog (12-op registry, prior wall lists, prior dichotomies) for the 'newly-surfaced' axis. If pre-existing under different vocabulary, the discovery is rebranding."
    - "Apply Reducer P13: strip future-vocabulary nouns, ask what 2026 statement remains. If the stripped statement is textbook taxonomy (Siegel/Kolmogorov/Bourgain 1960s), the framing is laundered."
mitigation:
  - "Withdraw promotion evidence when rigged-quartet detected (e.g. PATTERN-012 N=2 → reverted to N=1 after catch #23)."
  - "Substitute honest grade label from the pre-registration alphabet (WEAK PASS, not STRONG WEAK PASS)."
  - "Document the laundered framing in the file's docstring; retain the file as scaffold but mark NOT a foundational primitive."
  - "Externalize the splitting outside the architecture's own vocabulary: cite a prior literature dichotomy with non-overlapping hypotheses (e.g. Bourgain-Goldstein-Schlag 2002 vs Eliasson-Kuksin) — if the architecture's split aligns, the dichotomy is real; if not, it is vocabulary-internal."
examples:
  - id: catch_23
    summary: "Rigged-Quartet — 4-vocabulary translation produced 2-2 split framed as PATTERN-012 N=2 evidence. V4 (pec_b) and V3 (core_07) had pre-disjoint output spaces by op definition. Swap V4 for cand_g → 1-3 split; the 'axis' flipped. Plus pre-existing articulation 3 days earlier."
    file: anti_laundering_catch_23_rigged_quartet_2026_05_08.md
  - id: catch_26
    summary: "Vocabulary-rename of Tendsto → liminf_eq framed as analytic reduction (Onsager-1/3-open → uncontroversial). Strip-vocab: same hypothesis at different name."
    file: anti_laundering_catch_26_vocabulary_relabel_refactor_2026_05_08.md
  - id: catch_30
    summary: "Pincer 'STRONG WEAK PASS' — hybrid grade not in pre-registration's verdict alphabet. Retrofitted to inflate a joint verdict. Also: criterion-selection step not pre-registered (chosen during deployment, knowing each agent's attack vector)."
    file: pincer_meta_darwin_audit_2026_05_08.md
falsifiable_test:
  description: "For an N-vocabulary split claimed as architecturally informative, swap one of the N vocabularies for a different op in the SAME catalog (e.g. swap pec_b for cand_g). The anti-pattern fires iff the split structure changes — meaning the 'axis' was an artifact of op selection."
  binary_check: "split_is_robust_under_one_op_swap(vocabularies, alternative_ops) — firing iff False."
  not_trivial: "Returns 'not firing' (True) when the N vocabularies have non-disjoint output spaces and produce the same split structure under at least one swap. Empirically the test discriminates: catch #23's split flipped on swap; the falsifiable comparison test (Bourgain-Goldstein-Schlag vs Eliasson-Kuksin) was non-pre-disjoint and gave a robust signal. NOT True := by trivial."
chain_position: post  # runs AFTER any naming-sprint, multi-vocabulary translation, or hybrid-grade verdict
references:
  - "PATTERN-003 reducer"
  - "PATTERN-006 tautology_trap_detector"
  - "anti_laundering_catch_23_rigged_quartet_2026_05_08.md"
  - "anti_laundering_catch_26_vocabulary_relabel_refactor_2026_05_08.md"
  - "pincer_meta_darwin_audit_2026_05_08.md"
---

# ANTI-PATTERN-003 — Vocabulary Smuggling

## What it is

Architectural progress claimed via vocabulary-mediated rediscovery
or rigged splits. Three sub-modes observed tonight:

1. **Rigged-quartet** (catch #23): N vocabularies translated onto a
   problem produce a (k, N-k) split that gets framed as a newly-
   surfaced architectural axis. The vocabularies' output spaces
   were pre-disjoint by definitional scope; the split was guaranteed
   by op selection.
2. **Vocabulary-rename → analytic claim** (catch #26): rename a
   hypothesis (Tendsto → liminf_eq) and assert the renamed form
   sits at a more elementary analytic level WITHOUT proving any
   callsite discharges via the easier path.
3. **Charity-grade qualifier inflation** (catch #30): a hybrid
   verdict label ("STRONG WEAK PASS") not in the pre-registration's
   verdict alphabet, retrofitted to make a joint verdict look
   stronger than the pre-registration's grading rule allows.

## Why it appears

Multi-vocabulary translation is a real generative tool (PATTERN-012
N=1 evidence is genuine). The failure mode is when the operator-
catalog of vocabularies is selected with knowledge of which split
will be informative. Op selection becomes the launderer; the split
is a foregone conclusion.

Charity grades appear when the operator-author is grading their own
deployment after seeing the agents' outputs and wants the verdict
to read favorably.

## Why it matters

Tonight's PATTERN-012 N=2 promotion was withdrawn after catch #23.
A rigged-quartet that survives review feeds laundered evidence
into the architecture's pattern catalog. False N=2 leads to false
N=3, false promotion to peer pattern.

## Detection protocol

Apply PATTERN-003 (Reducer) with vocabulary-rigging sub-mode:

1. For each of the N vocabularies, look up its op-catalog definition.
   Is its output space pre-constrained to one side of the proposed
   split?
2. Swap one vocabulary for a different op in the same catalog. Does
   the split structure change?
3. Search the architecture's prior catalogs for the "axis" under
   different names. If pre-existing, the discovery is rebranding.
4. Apply Reducer P13: strip the elite vocabulary; ask what 2026
   statement remains. If the stripped statement is 1960s textbook
   taxonomy, the framing is laundered.

For verdict labels: cross-check against the pre-registration's
verdict alphabet. Reject any label not in the alphabet.

## Mitigation when detected

- Withdraw the promotion evidence (e.g. PATTERN-012 N=2 → N=1).
- Substitute the honest grade label from the alphabet.
- Add a "vocabulary-non-rigging check" to future deployments: any
  PATTERN-012 deployment must verify chosen vocabularies' output
  spaces are NOT pre-disjoint.
- Externalize the splitting test outside the architecture's own
  vocabulary: cite a prior literature dichotomy.

## Falsifiable test (catalog-level)

`split_is_robust_under_one_op_swap(vocabularies, alternative_ops)`.
The anti-pattern fires iff False.

NOT trivially True: catch #23's split flipped under swap (firing);
the externally-corroborated Bourgain-Goldstein-Schlag vs
Eliasson-Kuksin comparison was non-disjoint and produced a robust
signal (not firing). The test discriminates.

## Cross-references

- PATTERN-003 (`org/patterns/reducer.md`)
- PATTERN-006 (`org/patterns/tautology_trap.md`)
- `projects/ns_millennium_hunt/workspace/research_notes/anti_laundering_catch_23_rigged_quartet_2026_05_08.md`
- `projects/ns_millennium_hunt/workspace/research_notes/anti_laundering_catch_26_vocabulary_relabel_refactor_2026_05_08.md`
- `projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md`
