# Anti-Pattern Catalog Index

**Discovered**: 2026-05-08 from 20 anti-laundering catches in one
extended session. Each entry clusters ≥2 instances; singletons are
noted at the bottom.

**Architectural rule**: future sessions should run their proposed
work through anti-pattern detection FIRST (cheap precondition)
before deployment, parallel to running through `org/patterns/`
detection (expensive but generative).

Catalog format mirrors `org/patterns/*.md` (SKILL.md format, 
YAML frontmatter + markdown body). Each entry is `ANTI-PATTERN-XXX`
with `triggers`, `detection_protocol`, `mitigation`, `examples`,
`falsifiable_test`.

## Entries

Synchronized with the file-backed catalog in `org/anti-patterns/*.md` on
2026-05-23. `ANTI-PATTERN-015` has no file-backed entry in this directory;
keep that identifier unassigned until a dedicated file exists.

| ID | Name | One-line summary | Detected by | Mitigated by |
|---|---|---|---|---|
| ANTI-PATTERN-001 | citation_laundering | Literature citation or precise result label fails source verification. | PATTERN-002 darwin_idea_killer + PATTERN-009 independent_cas_verification | substitute primary source / soften qualifier / remove + downgrade |
| ANTI-PATTERN-002 | sorry_obligation_laundering | Claimed proof-obligation reduction only moves the obligation to another boundary. | PATTERN-007 smuggling_audit + PATTERN-002 darwin_idea_killer | require a strictly weaker upstream constructor / record caller burden |
| ANTI-PATTERN-003 | vocabulary_smuggling | Progress claim depends on vocabulary-mediated rediscovery or rigged category splits. | PATTERN-003 reducer + PATTERN-006 tautology_trap_detector | withdraw promotion evidence / run non-rigging check |
| ANTI-PATTERN-004 | pattern_1_rabbit_hole | Generative pattern recurses on its own residual without orthogonal pressure. | PATTERN-001 friction_debate + PATTERN-011 swarm_dispatch | cap recursion / add orthogonal pressure / use fresh-context dispatch |
| ANTI-PATTERN-005 | narrative_inflation | Verdict labels, catch counts, or completion claims exceed the evidence. | PATTERN-002 darwin_idea_killer + PATTERN-005 falsifiable_asymmetry | demote wording / use pre-registered verdict alphabet / re-audit ledger |
| ANTI-PATTERN-006 | cross_agent_monoculture | Single-family agent swarm is presented as cross-family validation. | PATTERN-011 swarm_dispatch + PATTERN-002 darwin_idea_killer | relabel single-family evidence / dispatch cross-family review |
| ANTI-PATTERN-007 | charity_grade_inflation | Verdict label falls outside the locked pre-registration alphabet. | PATTERN-001 friction_debate + PATTERN-002 darwin_idea_killer | demote off-alphabet labels / block retroactive alphabet growth |
| ANTI-PATTERN-008 | deployment_time_pre_spec_laundering | Pre-spec is authored or amended after dispatch begins. | PATTERN-001 friction_debate + PATTERN-005 falsifiable_asymmetry | refuse deployment evidence / re-deploy under a fresh pre-spec |
| ANTI-PATTERN-009 | criterion_selection_rigging | Criteria are selected or changed after seeing agent attack vectors. | PATTERN-001 friction_debate + PATTERN-003 reducer | freeze criterion ids before dispatch / treat drift as insufficient evidence |
| ANTI-PATTERN-010 | substrate_invariant_target_decoupling | Substrate invariant and target-theory invariant diverge, so serial routes fail for one shared reason. | PATTERN-005 falsifiable_asymmetry + PATTERN-014 cold_shot_dispatch | add invariant-alignment receipt / change substrate or target |
| ANTI-PATTERN-011 | scientific_amnesia | Branch is chosen before checking prior artifacts for the same basin. | PATTERN-024 scientific_amnesia_precheck + PATTERN-017 frontier_state_ledger | classify repeat/reuse/adjacent/no-close-prior before acting |
| ANTI-PATTERN-012 | vocabulary_chain_laundering | Named-result chain skips explicit direction, quantifier, domain, and inclusion checks. | PATTERN-002 darwin_idea_killer + PATTERN-007 smuggling_audit | add per-step verification block / retract unverifiable transition |
| ANTI-PATTERN-013 | lean_closure_laundering | Compiled Lean artifact is over-read despite vacuity, one-lemma exact, tactic leakage, or currency mismatch. | v33 deterministic Lean gates + lean_proof_gate | fail confirmed sub-modes / route shape suspects to review |
| ANTI-PATTERN-014 | premature_settled_negative | Broad negative verdict is emitted before boundary crossing, adversarial review, or sufficient sample size. | PATTERN-002 darwin_idea_killer + external-exhaustion checklist | narrow the negative / run steelman-first and independent adversaries |
| ANTI-PATTERN-016 | premature_heuristic_escape | Local estimate work is abandoned for a broad cross-field heuristic terminus. | local estimate push + terminal de-anonymization | force 2-3 concrete local steps before any heuristic stop |
| ANTI-PATTERN-017 | category_conflation_strawman_shift | Reviewer swaps the object or hypothesis class, then attacks the swapped version. | object-identity check + ANTI-PATTERN-014 objective test | verify the same object appears on both sides of the objection |
| ANTI-PATTERN-018 | tool_underuse_formal_satisficing | Hard residual has available tools/primitives, but the agent moves to formal/code close before tool stress. | PATTERN-028 recursive_tool_depth_loop + PATTERN-025 gowers_first_formalize_second | require orientation -> tool pass -> artifact edit -> stress pass |

## Cross-reference map (anti-pattern -> detection pattern)

```text
ANTI-PATTERN-001 citation_laundering              -> PATTERN-002, PATTERN-009
ANTI-PATTERN-002 sorry_obligation_laundering      -> PATTERN-007, PATTERN-002
ANTI-PATTERN-003 vocabulary_smuggling             -> PATTERN-003, PATTERN-006
ANTI-PATTERN-004 pattern_1_rabbit_hole            -> PATTERN-001, PATTERN-011
ANTI-PATTERN-005 narrative_inflation              -> PATTERN-002, PATTERN-005
ANTI-PATTERN-006 cross_agent_monoculture          -> PATTERN-011, PATTERN-002
ANTI-PATTERN-007 charity_grade_inflation          -> PATTERN-001, PATTERN-002
ANTI-PATTERN-008 deployment_time_pre_spec         -> PATTERN-001, PATTERN-005
ANTI-PATTERN-009 criterion_selection_rigging      -> PATTERN-001, PATTERN-003
ANTI-PATTERN-010 invariant_target_decoupling      -> PATTERN-005, PATTERN-014
ANTI-PATTERN-011 scientific_amnesia               -> PATTERN-024, PATTERN-017
ANTI-PATTERN-012 vocabulary_chain_laundering      -> PATTERN-002, PATTERN-007, PATTERN-006
ANTI-PATTERN-013 lean_closure_laundering          -> v33 Lean gates, lean_proof_gate
ANTI-PATTERN-014 premature_settled_negative       -> PATTERN-002, external-exhaustion checklist
ANTI-PATTERN-016 premature_heuristic_escape       -> local estimate push, terminal de-anonymization
ANTI-PATTERN-017 category_conflation_shift        -> object-identity check, ANTI-PATTERN-014 objective test
ANTI-PATTERN-018 tool_underuse_formal_satisficing -> PATTERN-028, PATTERN-025
```

## META-EPISTEMIC quartet (added 2026-05-08 per catch #31)

ANTI-PATTERN-005 (narrative_inflation, parent) +
ANTI-PATTERN-007 (charity_grade_inflation) +
ANTI-PATTERN-008 (deployment_time_pre_spec_laundering) +
ANTI-PATTERN-009 (criterion_selection_rigging)

These four sit at the META-EPISTEMIC level for Pattern-001
deployments. They are PROCESS failure modes (verdicts, pre-spec
timing, criteria content, narrative framing), distinct from the
substrate-visible failure modes (001-004, 006) which have direct
code/artifact correlates. Catch #31 found that the META-DARWIN
fix dispatch addressed substrate-visible failures via Lean
typed-companion code but left process failures unaddressed; this
quartet is the structural fix at the same architectural level
(catalog-level enforcement) as the substrate-visible entries.

Enforcement boundaries (honest):

- 007 (charity_grade): mechanically enforced by `label ∈ alphabet` check at joint-verdict write time.
- 008 (pre-spec timing): mechanically enforced by orchestration runner refusing `round_1.json` without `pre_spec_sha.txt`. Limit: a sufficiently determined operator can amend git history; the discipline is "honest operator + git log audit", not cryptographic.
- 009 (criteria drift): mechanically enforced by set-equality check on criterion ids at joint-verdict write. Limit: wording-only refinement requires operator-signed diff; this is the residual judgment call.

The enforceable parts are mechanical refusals at well-defined
write boundaries. The aspirational parts (operator honesty about
wording diffs, git history not being amended) are documented as
limits rather than papered over.

## Catch coverage (20 catches → 6 families + singletons)

The 20 anti-laundering catches from the 2026-05-08 session map onto
the 6 families as follows. Catches with overlap are listed under all
applicable families.

| Catch | Family / families |
|---|---|
| #5 Pattern-1 rabbit hole (5/5 → 1.5/5) | ANTI-PATTERN-004 |
| #9 Mathlib-PR file NOT PR-ready | ANTI-PATTERN-005 (completion-language overclaim) |
| #10 Rank-r-closed-aliasing redundant with T9 | ANTI-PATTERN-003 (vocabulary smuggling, cosmetic-rank relabeling), fits via Reducer P13 |
| #15 Mungerian fallback smuggling | (covered by existing PATTERN-007 smuggling_audit; treated as detection-pattern instance, not new anti-pattern) |
| #17 Marchioro-Pulvirenti fabrication | ANTI-PATTERN-001 |
| #21e Atom 8 defect-positivity smuggling | ANTI-PATTERN-002 |
| #21f Atom 8 sibling sub-mode | ANTI-PATTERN-002 |
| #22 Cross-agent monoculture | ANTI-PATTERN-006 |
| #23 Rigged-quartet | ANTI-PATTERN-003 |
| #24 Overclaim (in #25 ledger update) | ANTI-PATTERN-005 |
| #25 Lean elaborator rabbit-hole | ANTI-PATTERN-004 |
| #26 Vocabulary-rename refactor as analytic reduction | ANTI-PATTERN-002 + ANTI-PATTERN-003 |
| #27 Lions 1996 §IV.4 chapter mismatch | ANTI-PATTERN-001 |
| #28 Galdi 2011 OP-9.3 sub-label mismatch | ANTI-PATTERN-001 |
| #29 DiPerna-Majda verification gap | ANTI-PATTERN-001 |
| #30 Pincer "GENUINE" → PARTIAL/PROVISIONAL | ANTI-PATTERN-002 + ANTI-PATTERN-003 + ANTI-PATTERN-005 + ANTI-PATTERN-007 + ANTI-PATTERN-008 + ANTI-PATTERN-009 |
| #31 META-DARWIN re-audit substrate-visibility selection bias | ANTI-PATTERN-007 + ANTI-PATTERN-008 + ANTI-PATTERN-009 (the three META-EPISTEMIC entries are themselves the response to catch #31) |
| #34 T9 user-visible-sorry-free claim launders carrier-identification gap when circulated without §2 honesty paragraph (PATTERN-008 three-leg verification fired 2.5/3 legs; scaffold-shipped, not proof-shipped) | ANTI-PATTERN-005 (narrative_inflation; scope_overstatement), see `projects/ns_millennium_hunt/workspace/research_notes/T9_three_leg_verification_2026_05_08.md` |
| #35 W6 misattribution: `ns_trackb_W6_sharp_conditional.lean` cites the small-divisor wall as "Lerner-2026 Bohr-side transcription" when the critical technique is Bourgain-Kuksin small-divisor / KAM-with-reducibility (Bourgain GAFA 1995; Kuksin-Eliasson reducibility); Lerner 2026 is decaying-class only and does NOT cover the Bohr-AP small-divisor regime, citation needs softening + attribution patch | ANTI-PATTERN-001 (citation_laundering, sub-label mismatch), see `projects/ns_millennium_hunt/workspace/research_notes/W6_anti_symmetry_forcing_attempt_2026_05_08.md` (catch #32 trigger) and `W6_construction_attempt_2026_05_08.md` |

## Singletons (catches that did NOT cluster into a family)

Per the anti-laundering vigilance rule, only families with ≥2
instances were promoted. The following catches are documented as
singletons; if a 2nd instance surfaces in a future session, they
become candidates for new anti-pattern entries:

- **catch #1 Helicity-IBP Beltrami-only**, substrate-specific
  (NS regularity); detected via SymPy + PATTERN-009.
- **catch #2 De Giorgi exact-zero too strong**, substrate-
  specific; counterexample-driven.
- **catch #3 Carleman empty-box**, substrate-specific.
- **catch #4 Sum-free shear apparent-counterexample**, substrate-
  specific.
- **catch #6 Liouville-orbit-collapse signature mismatch**, 
  substrate-specific intra-file Lean signature mismatch.
- **catch #7 T13 GIMS-collapse**, substrate-specific.
- **catch #8 Time-Dependent Rank-1 weak-strong fix**, substrate-
  specific; uniqueness-citation precision.
- **catch #11 Pattern 1 #7 over-claim (pressure term skipped)**, 
  arguably an instance of ANTI-PATTERN-005 (over-claim), but the
  critical failure mode was substrate-specific (energy estimate
  skipped a term), so kept as singleton.
- **catches #12-14 OCCT/FDOS/VBNS-PT LAUNDERED**, these are the
  canonical examples for PATTERN-003 (Reducer) itself; treated as
  pattern-confirmation, not new anti-patterns.
- **catch #15 Mungerian fallback smuggling**, canonical example
  for PATTERN-007 smuggling_audit; treated as pattern-confirmation.

These singletons are honest: not every catch needs its own anti-
pattern. The discipline is to wait for ≥2 instances before
promoting.

## Catalog self-application (PATTERN-005 falsifiable_asymmetry on the catalog)

Per the user's request, the catalog itself must survive its own
falsifiability discipline. Each anti-pattern's `falsifiable_test`
field is a binary check that:

1. Returns `not firing` (False) on at least one real artifact in
   the repo (so the test is NOT `True := by trivial`).
2. Returns `firing` (True) on at least one of tonight's catches
   (so the test catches what it claims to catch).

Verification of each test's discriminative power is documented in
the `not_trivial` field of each entry.

## Discoverability

This catalog is wired into:

- `org/patterns/INDEX.md` (sister pattern index), bidirectional
  cross-link.
- `src/ztare/reflexive_primitives/INDEX.md` (third-class sibling, added
  2026-05-08), critical self-referential architectural
  components (Verdict-B partially-novel constructs that use the
  architecture's own infrastructure as critical context).
- `AGENTS.md` §6m, one-line reference appended to the orchestration
  meta-pattern catalog mention.
- Future: when `org/runtime/pattern_catalog.yaml` is regenerated,
  add an anti-patterns section parallel to the patterns section.

## Catch ledger (SOX/PCAOB AS §1215 + §1220 analog)

The catch ledger lives at `analytics/catch_ledger.jsonl`; validator at
`scripts/validate_catch_ledger.py`. Schema documented in
`analytics/catch_ledger_schema.md`. Future catches MUST be appended here
(structured artifact pointers + concurring-agent gate) to count toward the
architecture's catch tally; narrative-only counts are deprecated.

## Versioning

Each entry has `version: 1` in its frontmatter. Bump on:

- **Patch**: prose-only update, new example added, mitigation
  refined.
- **Minor**: new sub-mode added under an existing family.
- **Major**: family split / merged / superseded.

When a singleton becomes ≥2 instances, promote to a new
ANTI-PATTERN-XXX entry; do NOT shoehorn into existing family.
