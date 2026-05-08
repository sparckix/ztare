---
id: ANTI-PATTERN-007
name: charity_grade_inflation
version: 1
status: active
discovered: 2026-05-08
parent: ANTI-PATTERN-005  # narrative_inflation (sub-mode promoted to first-class entry; see catch #31)
triggers:
  lexical: ["STRONG WEAK PASS", "GENUINE PARTIAL", "PROVISIONAL PASS", "WEAK PASS with caveat", "PARTIAL-PARTIAL", "STRONG PARTIAL", "passes-with-displacement"]
  structural:
    - verdict_label_not_in_pre_registration_alphabet
    - hybrid_label_combining_two_alphabet_entries
    - charity_grade_invented_during_scoring
    - arbiter_extended_alphabet_without_new_pre_spec
  problem_classes: [apparatus_self_audit]
detection_protocol:
  primary: PATTERN-001  # friction_debate (rule_7_verdict_alphabet_locked)
  secondary: PATTERN-002  # darwin_idea_killer (kill-bias on own positive verdict)
  rule:
    - "Look up the deployment's `pre_spec_sha`. Read the verdict alphabet at that commit. Cross-check every verdict label in the deployment's joint verdict against that alphabet."
    - "If the joint verdict contains a compound qualifier (two alphabet entries adjacent: 'STRONG WEAK PASS', 'GENUINE PARTIAL') the anti-pattern fires."
    - "If the joint verdict contains a label not in the alphabet at all ('passes-with-displacement', 'CHARITY PASS') the anti-pattern fires."
    - "Even if the new label is logically defensible, fire — the alphabet is locked at pre_spec_sha; extension requires a new deployment, not a mid-scoring patch."
mitigation:
  - "Demote every off-alphabet label to INSUFFICIENT_EVIDENCE for the affected criterion (per PATTERN-001 rule 7). The verdict cannot be repaired in place."
  - "Record the firing as a catalog-level catch under ANTI-PATTERN-007 in the deployment's F-row."
  - "If the underlying evidence genuinely sat between two alphabet entries, the honest answer was PARTIAL; substitute PARTIAL going forward. If it lay outside {PASS, FAIL, PARTIAL}, the honest answer was INSUFFICIENT_EVIDENCE."
  - "Do NOT extend the alphabet retroactively. The fixed alphabet `{PASS, FAIL, PARTIAL, INSUFFICIENT_EVIDENCE}` is load-bearing precisely because it cannot be widened mid-scoring."
examples:
  - id: catch_30
    summary: "Pincer 'STRONG WEAK PASS' — hybrid grade combining STRONG and WEAK PASS adjacent to make the joint verdict appear stronger than the alphabet allowed. Fired on first audit; revised to PARTIAL/PROVISIONAL."
    file: projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md
  - id: catch_31
    summary: "Re-audit found this catch was not addressed by the META-DARWIN fix-dispatch (the dispatch shipped Lean code; charity-grade is a process failure, not a code failure). Promotion of this sub-mode to ANTI-PATTERN-007 is the structural fix."
    file: projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_re_audit_2026_05_08.md
falsifiable_test:
  description: "For every joint verdict produced by a Pattern-001 deployment, every label assigned to a criterion must be in the alphabet committed at the deployment's pre_spec_sha. The anti-pattern fires iff at least one label is off-alphabet OR the alphabet at pre_spec_sha differs from the locked default `{PASS, FAIL, PARTIAL, INSUFFICIENT_EVIDENCE}` without a documented amendment commit."
  binary_check: "all(label in alphabet_at(pre_spec_sha) for label in joint_verdict.labels) AND alphabet_at(pre_spec_sha) == {PASS, FAIL, PARTIAL, INSUFFICIENT_EVIDENCE} — firing iff False."
  not_trivial: "Returns 'not firing' on any deployment whose joint verdict contains only labels from the locked alphabet — including PARTIAL, which is a real allowed verdict and not a charity grade. Catch #30's 'STRONG WEAK PASS' returns firing (off-alphabet); a deployment that returns PARTIAL on the same evidence returns not-firing. The test discriminates. NOT True := by trivial."
chain_position: post  # runs AFTER any Pattern-001 joint verdict
references:
  - "PATTERN-001 friction_debate (rule_7_verdict_alphabet_locked)"
  - "ANTI-PATTERN-005 narrative_inflation (parent family)"
  - "projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md"
  - "projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_re_audit_2026_05_08.md"
---

# ANTI-PATTERN-007 — Charity-Grade Qualifier Inflation

## What it is

A verdict label that is NOT in the pre-registration's verdict
alphabet — typically a compound qualifier ("STRONG WEAK PASS",
"GENUINE PARTIAL", "PROVISIONAL PASS") or a newly-coined grade
("CHARITY PASS", "passes-with-displacement") — invented during
scoring to make a joint verdict read more favorably than the
alphabet allows.

This is a sub-mode of ANTI-PATTERN-005 (narrative_inflation)
promoted to a first-class entry because catch #31 (META-DARWIN
re-audit, 2026-05-08) found that the original META-DARWIN fix
dispatch addressed code-output failures but left this process-only
failure unaddressed. The promotion is the structural fix.

## Why it appears

Self-grading combined with a fixed alphabet that the operator
internally feels is "too coarse" for the evidence at hand. The
natural pull is to invent a finer label. The fixed alphabet is
load-bearing precisely because that pull exists.

## Detection protocol

1. Look up the deployment's `pre_spec_sha`.
2. Read the verdict alphabet at that commit.
3. Cross-check every label in the joint verdict against the
   alphabet.
4. Any compound qualifier or new label fires the anti-pattern,
   regardless of whether the new label is logically defensible.

## Mitigation when detected

- Demote every off-alphabet label to INSUFFICIENT_EVIDENCE for
  the affected criterion.
- Re-issue the joint verdict using only alphabet entries.
- Record the firing as a catalog-level catch.
- Do NOT extend the alphabet retroactively. The fixed alphabet
  is the discipline.

## Falsifiable test (catalog-level)

`all_labels_in_locked_alphabet(joint_verdict, pre_spec_sha)`.
Firing iff False.

NOT trivially True: catch #30's "STRONG WEAK PASS" returns firing
(off-alphabet); a deployment that returns PARTIAL on the same
evidence returns not-firing. The test discriminates between
honest PARTIAL verdicts (allowed) and charity grades (forbidden).
NOT `True := by trivial`.

## Cross-references

- PATTERN-001 (`org/patterns/pattern_1_friction_debate.md`,
  rule_7_verdict_alphabet_locked)
- ANTI-PATTERN-005 (`org/anti-patterns/narrative_inflation.md`)
- `projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md`
- `projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_re_audit_2026_05_08.md`
