# Anti-Pattern Catalog Index

**Discovered**: 2026-05-08 from 20 anti-laundering catches in one
extended session. Each entry clusters ≥2 instances; singletons are
noted at the bottom.

**Architectural rule**: future sessions should run their proposed
work through anti-pattern detection FIRST (cheap precondition)
before deployment, parallel to running through `org/patterns/`
detection (expensive but generative).

Catalog format mirrors `org/patterns/*.md` (SKILL.md format —
YAML frontmatter + markdown body). Each entry is `ANTI-PATTERN-XXX`
with `triggers`, `detection_protocol`, `mitigation`, `examples`,
`falsifiable_test`.

## Entries

| ID | Name | One-line summary | Detected by | Mitigated by |
|---|---|---|---|---|
| ANTI-PATTERN-001 | citation_laundering | Load-bearing literature citation does not point at the cited result (misattribution / sub-label mismatch / verification gap / fabrication). | PATTERN-002 darwin_idea_killer + PATTERN-009 independent_cas_verification | substitute primary source / soften qualifier / remove + downgrade |
| ANTI-PATTERN-002 | sorry_obligation_laundering | Claimed reduction in proof obligation that displaced rather than discharged the obligation (field renaming / underscore-binding / composition over sorry-bearing leaves). | PATTERN-007 smuggling_audit + PATTERN-002 darwin_idea_killer | require strictly weaker upstream constructor / honest displacement docstring |
| ANTI-PATTERN-003 | vocabulary_smuggling | Architectural progress claimed via vocabulary-mediated rediscovery or rigged splits (rigged-quartet / rename-as-analytic-claim / charity-grade qualifier). | PATTERN-003 reducer + PATTERN-006 tautology_trap_detector | withdraw promotion evidence / honest grade label / non-rigging check |
| ANTI-PATTERN-004 | pattern_1_rabbit_hole | Generative pattern applied recursively to its own residual without orthogonal pressure (theorem-level or IDE/tactic-level). | PATTERN-001 friction_debate (deployment-rule audit) + PATTERN-011 swarm_dispatch | STOP recursive deployment / fresh-context agent / 10x criteria gate |
| ANTI-PATTERN-005 | narrative_inflation | Verdict labels, completion claims, or catch counts inflated above load-bearing evidence (charity-grade hybrid / catch count inflation / completion-language overclaim). | PATTERN-002 darwin_idea_killer (kill-bias) + PATTERN-005 falsifiable_asymmetry | demote to pre-registration alphabet / scaffold framing / re-audit ledger |
| ANTI-PATTERN-006 | cross_agent_monoculture | Single-family Claude Code Agent swarm claimed as "cross-family validation" (AGENT-FAMILY-LAUNDERING). | PATTERN-011 swarm_dispatch (anti-pattern section) + PATTERN-002 darwin_idea_killer | re-label single-family / escalate to PY LLM-based swarm |
| ANTI-PATTERN-007 | charity_grade_inflation | Verdict label not in pre-registration's locked alphabet (compound qualifiers, mid-scoring grade invention — sub-mode of 005 promoted to first-class entry per catch #31). | PATTERN-001 friction_debate (rule_7_verdict_alphabet_locked) + PATTERN-002 darwin_idea_killer | demote off-alphabet labels to INSUFFICIENT_EVIDENCE / record catalog-level catch / no retroactive alphabet extension |
| ANTI-PATTERN-008 | deployment_time_pre_spec_laundering | Pre-registration file authored, finalized, or amended AFTER first agent dispatch — pre-spec is task-conditional, not pre- to anything. | PATTERN-001 friction_debate (rule_6_pre_spec_locked_before_deployment) + PATTERN-005 falsifiable_asymmetry | orchestration runner refuses round_1.json without pre_spec_sha / deployment is INSUFFICIENT_EVIDENCE / re-deploy fresh task_id |
| ANTI-PATTERN-009 | criterion_selection_rigging | Criteria set selected, refined, or curated DURING deployment with visibility into agent attack vectors — cross-vocabulary mode picks criterion phrasings to match outputs already seen. | PATTERN-001 friction_debate (rule_8_criteria_locked_before_dispatch) + PATTERN-003 reducer (P13) | added criteria → INSUFFICIENT_EVIDENCE + close deployment / removed criteria → INSUFFICIENT_EVIDENCE in record / refined criteria → signed diff or treat as removal+addition |

## Cross-reference map (anti-pattern ↔ detection pattern)

```
ANTI-PATTERN-001 citation_laundering          ↔ PATTERN-002 darwin_idea_killer
                                              ↔ PATTERN-009 independent_cas_verification
ANTI-PATTERN-002 sorry_obligation_laundering  ↔ PATTERN-007 smuggling_audit
                                              ↔ PATTERN-002 darwin_idea_killer
ANTI-PATTERN-003 vocabulary_smuggling         ↔ PATTERN-003 reducer
                                              ↔ PATTERN-006 tautology_trap_detector
ANTI-PATTERN-004 pattern_1_rabbit_hole        ↔ PATTERN-001 friction_debate (deployment rules)
                                              ↔ PATTERN-011 swarm_dispatch
ANTI-PATTERN-005 narrative_inflation          ↔ PATTERN-002 darwin_idea_killer (kill-bias)
                                              ↔ PATTERN-005 falsifiable_asymmetry
ANTI-PATTERN-006 cross_agent_monoculture      ↔ PATTERN-011 swarm_dispatch (anti-pattern §)
                                              ↔ PATTERN-002 darwin_idea_killer
ANTI-PATTERN-007 charity_grade_inflation      ↔ PATTERN-001 friction_debate (rule 7)
                                              ↔ PATTERN-002 darwin_idea_killer
ANTI-PATTERN-008 deployment_time_pre_spec_laundering
                                              ↔ PATTERN-001 friction_debate (rule 6)
                                              ↔ PATTERN-005 falsifiable_asymmetry
ANTI-PATTERN-009 criterion_selection_rigging  ↔ PATTERN-001 friction_debate (rule 8)
                                              ↔ PATTERN-003 reducer (P13)
```

## META-EPISTEMIC quartet (added 2026-05-08 per catch #31)

ANTI-PATTERN-005 (narrative_inflation, parent) +
ANTI-PATTERN-007 (charity_grade_inflation) +
ANTI-PATTERN-008 (deployment_time_pre_spec_laundering) +
ANTI-PATTERN-009 (criterion_selection_rigging)

These four sit at the META-EPISTEMIC level for Pattern-001
deployments. They are PROCESS failure modes (verdicts, pre-spec
timing, criteria content, narrative framing) — distinct from the
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
| #10 Rank-r-closed-aliasing redundant with T9 | ANTI-PATTERN-003 (vocabulary smuggling — cosmetic-rank relabeling) — fits via Reducer P13 |
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
| #34 T9 user-visible-sorry-free claim launders carrier-identification gap when circulated without §2 honesty paragraph (PATTERN-008 three-leg verification fired 2.5/3 legs; scaffold-shipped, not proof-shipped) | ANTI-PATTERN-005 (narrative_inflation; scope_overstatement) — see `projects/ns_millennium_hunt/workspace/research_notes/T9_three_leg_verification_2026_05_08.md` |
| #35 W6 misattribution: `ns_trackb_W6_sharp_conditional.lean` cites the small-divisor wall as "Lerner-2026 Bohr-side transcription" when the load-bearing technique is Bourgain–Kuksin small-divisor / KAM-with-reducibility (Bourgain GAFA 1995; Kuksin–Eliasson reducibility); Lerner 2026 is decaying-class only and does NOT cover the Bohr-AP small-divisor regime — citation needs softening + attribution patch | ANTI-PATTERN-001 (citation_laundering — sub-label mismatch) — see `projects/ns_millennium_hunt/workspace/research_notes/W6_anti_symmetry_forcing_attempt_2026_05_08.md` (catch #32 trigger) and `W6_construction_attempt_2026_05_08.md` |

## Singletons (catches that did NOT cluster into a family)

Per the anti-laundering vigilance rule, only families with ≥2
instances were promoted. The following catches are documented as
singletons; if a 2nd instance surfaces in a future session, they
become candidates for new anti-pattern entries:

- **catch #1 Helicity-IBP Beltrami-only** — substrate-specific
  (NS regularity); detected via SymPy + PATTERN-009.
- **catch #2 De Giorgi exact-zero too strong** — substrate-
  specific; counterexample-driven.
- **catch #3 Carleman empty-box** — substrate-specific.
- **catch #4 Sum-free shear apparent-counterexample** — substrate-
  specific.
- **catch #6 Liouville-orbit-collapse signature mismatch** —
  substrate-specific intra-file Lean signature mismatch.
- **catch #7 T13 GIMS-collapse** — substrate-specific.
- **catch #8 Time-Dependent Rank-1 weak-strong fix** — substrate-
  specific; uniqueness-citation precision.
- **catch #11 Pattern 1 #7 over-claim (pressure term skipped)** —
  arguably an instance of ANTI-PATTERN-005 (over-claim), but the
  load-bearing failure mode was substrate-specific (energy estimate
  skipped a term), so kept as singleton.
- **catches #12-14 OCCT/FDOS/VBNS-PT LAUNDERED** — these are the
  canonical examples for PATTERN-003 (Reducer) itself; treated as
  pattern-confirmation, not new anti-patterns.
- **catch #15 Mungerian fallback smuggling** — canonical example
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

- `org/patterns/INDEX.md` (sister pattern index) — bidirectional
  cross-link.
- `src/ztare/reflexive_primitives/INDEX.md` (third-class sibling, added
  2026-05-08) — load-bearing self-referential architectural
  components (Verdict-B partially-novel constructs that use the
  architecture's own infrastructure as load-bearing context).
- `AGENTS.md` §6m — one-line reference appended to the orchestration
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
