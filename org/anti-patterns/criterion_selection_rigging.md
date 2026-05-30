---
id: ANTI-PATTERN-009
name: criterion_selection_rigging
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: ["we tightened the criteria after seeing", "added a 6th criterion to capture", "removed criterion 3 because it was too strict", "the criteria evolved during deployment", "we refined the wording to better fit"]
  structural:
    - criterion_added_after_first_dispatch
    - criterion_removed_after_first_dispatch
    - criterion_wording_changed_after_first_dispatch_in_evidence_changing_way
    - criteria_count_in_joint_verdict_differs_from_count_in_pre_spec_sha
    - criteria_drift_correlates_with_agent_attack_vectors_already_seen
  problem_classes: [apparatus_self_audit, pre_category_emergence]
detection_protocol:
  primary: PATTERN-001  # friction_debate (rule_8_criteria_locked_before_dispatch)
  secondary: PATTERN-003  # reducer (P13, strip the new criterion's elite vocab; does the residual track an attack vector?)
  rule:
    - "Read the criteria list at `pre_spec_sha`. Read the criteria list in the joint verdict. Compute the symmetric difference."
    - "If the symmetric difference is non-empty, fire on every member of the symmetric difference."
    - "For criteria whose wording changed (same id, different text), apply Reducer P13: strip elite vocabulary; does the change alter which evidence counts? If yes, treat as removal+addition (both fire)."
    - "Cross-vocabulary check: for each added/refined criterion, ask whether its wording is correlated with an attack vector already visible in dispatch logs. If yes, the rigging is cross-vocabulary (the criterion was selected to match an output, not the converse)."
mitigation:
  - "Per PATTERN-001 rule 8: every added criterion is automatic INSUFFICIENT_EVIDENCE on that criterion AND closes the current deployment id. A new deployment id + new pre_spec_sha is required to score the added criterion."
  - "Every removed criterion is recorded as INSUFFICIENT_EVIDENCE in the joint verdict (not deleted from the record). The criterion is part of the deployment's history regardless of whether it was scored."
  - "Refined criteria (wording-only, evidence-set unchanged) require a documented diff in the orchestration_state log, signed by the operator. Refined criteria (evidence-set changed) are removal+addition."
  - "Do NOT 'tighten' criteria mid-deployment. The honest move is to close the deployment, ship a re-audit note, and re-deploy with the tightened set under a new pre_spec_sha."
examples:
  - id: catch_30
    summary: "Pincer META-DARWIN deployment, the 5 criteria were chosen DURING deployment, with operator visibility into each agent's attack vector. The 'criteria set' is post-hoc curation framed as pre-registration. Disjointness audit found ~3 effective axes (not 5) because criteria collapsed onto shared DARWIN catches."
    file: projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md
  - id: catch_31
    summary: "Re-audit confirmed this failure mode is process-only and was not addressed by any code-output fix. Promotion to ANTI-PATTERN-009 + PATTERN-001 rule_8 is the structural fix. Cross-vocabulary criterion selection (the operator picked criterion phrasings that matched specific agent outputs already seen) is the dominant mode."
    file: projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_re_audit_2026_05_08.md
falsifiable_test:
  description: "For every Pattern-001 deployment, the criteria list in the joint verdict must be set-equal to the criteria list at pre_spec_sha (modulo wording-only refinements documented and signed in orchestration_state). The anti-pattern fires iff the symmetric difference is non-empty OR if any wording change altered the evidence set without an explicit removal+addition record."
  binary_check: "set(criteria_in_joint_verdict) == set(criteria_at_pre_spec_sha) AND no_evidence_set_changing_wording_diffs, firing iff False."
  not_trivial: "Returns 'not firing' for any deployment that scored exactly the criteria committed at pre_spec_sha. Catch #30's pincer deployment returns firing (criteria selected during dispatch). A future deployment that locks 5 criteria pre-dispatch and scores those 5 returns not-firing. The test reduces to a set-equality check on criterion ids. NOT True := by trivial."
chain_position: post  # runs at joint-verdict write time; verifies criteria didn't drift
references:
  - "PATTERN-001 friction_debate (rule_8_criteria_locked_before_dispatch)"
  - "PATTERN-003 reducer (P13)"
  - "ANTI-PATTERN-003 vocabulary_smuggling (sister mode, vocabulary-rigged splits)"
  - "ANTI-PATTERN-008 deployment_time_pre_spec_laundering (sister mode, pre-spec timing)"
  - "projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md"
  - "projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_re_audit_2026_05_08.md"
---

# ANTI-PATTERN-009, Cross-Vocabulary Criterion-Selection Rigging

## What it is

The criteria set for a Pattern-001 deployment is selected,
refined, or curated DURING deployment with knowledge of agent
attack vectors. The post-hoc criteria appear to confirm a pre-
registered structure but were chosen to match outputs the
operator had already seen.

The "cross-vocabulary" qualifier names the dominant mode: the
operator picks criterion phrasings drawn from the vocabulary of
specific agents' partial outputs, then frames the resulting
agreement as a multi-axis convergence. The criteria are not
independent axes; they are projections of attack vectors already
in hand.

## Why it appears

Operator-side selection bias. After seeing what each agent
produces in its first round, the path of least resistance is to
phrase the criteria so the cleanest outputs score highest. The
verdict then reads as a strong multi-axis pass when in fact the
"axes" were selected to align with the outputs.

## Why it matters

Pattern-001's joint-verdict authority depends on the criteria
being independent of the agents' outputs. Criterion drift
collapses the effective sample size: 5 criteria selected after
seeing 5 attack vectors carry the information of perhaps 1-2
independent axes. Inflating effective sample size is the
mechanism by which charity-grade and narrative-inflation patterns
get cover.

## Detection protocol

1. Read criteria list at `pre_spec_sha`. Read criteria list in
   joint verdict. Compute symmetric difference.
2. Fire on every member of the symmetric difference.
3. For criteria whose wording changed: apply Reducer P13, strip
   elite vocabulary, ask whether the change alters which
   evidence counts. If yes, treat as removal+addition.
4. Cross-vocabulary audit: for each added/refined criterion,
   ask whether its wording is correlated with an attack vector
   visible in the dispatch logs at the time of the change. If
   yes, the rigging is cross-vocabulary.

## Mitigation when detected

- Added criteria: INSUFFICIENT_EVIDENCE + close current
  deployment + new pre_spec_sha for re-deployment.
- Removed criteria: INSUFFICIENT_EVIDENCE in the joint verdict
  (recorded, not deleted).
- Refined criteria: wording-only refinement requires a signed
  diff; evidence-set-changing refinement is removal+addition.
- The honest workflow is: close the deployment, ship a re-audit
  note, re-deploy with the tightened criteria set under a fresh
  pre_spec_sha.

## Distinction from sister anti-patterns

- ANTI-PATTERN-003 (vocabulary_smuggling) catches rigged-quartet
  splits where the vocabularies' output spaces are pre-disjoint.
  ANTI-PATTERN-009 catches the criteria-level analog: the
  criteria themselves are post-hoc curated.
- ANTI-PATTERN-008 (deployment_time_pre_spec_laundering) catches
  the timing of the pre-spec file. ANTI-PATTERN-009 catches the
  content drift even when the pre-spec was committed pre-
  dispatch (a pre-spec can exist on time and still be amended
  later with criterion drift).

The three anti-patterns (007, 008, 009) plus their parent
ANTI-PATTERN-005 form the META-EPISTEMIC quartet for Pattern-001
deployments, verdicts (007), pre-spec timing (008), criteria
content (009), and overall narrative inflation (005).

## Falsifiable test (catalog-level)

`set(criteria_in_joint_verdict) == set(criteria_at_pre_spec_sha)`.
Firing iff False.

NOT trivially True: catch #30 fires (criteria selected during
dispatch); a deployment that scores exactly the pre-committed
criteria returns not-firing. The test reduces to a set-equality
check on criterion ids, binary, machine-checkable, no
appeal-to-judgment. NOT `True := by trivial`.

## Cross-references

- PATTERN-001 (`org/patterns/pattern_1_friction_debate.md`,
  rule_8_criteria_locked_before_dispatch)
- PATTERN-003 (`org/patterns/reducer.md`, P13)
- ANTI-PATTERN-003 (`org/anti-patterns/vocabulary_smuggling.md`)
- ANTI-PATTERN-008 (`org/anti-patterns/deployment_time_pre_spec_laundering.md`)
- `projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_audit_2026_05_08.md`
- `projects/ns_millennium_hunt/workspace/research_notes/pincer_meta_darwin_re_audit_2026_05_08.md`
