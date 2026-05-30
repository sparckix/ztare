---
id: PATTERN-023
name: anti_rename_charter_gate
version: 1
status: active
discovered: 2026-05-09
triggers:
  lexical: [novel closure, novel theorem, new admissibility, breakthrough, cornered]
  structural: [closure_attempt_proposed, charter_draft_pending, pre_lean_port]
  problem_classes: [hard_mathematical_residual, novel_content_claim]
spawn:
  mode: pre_charter_self_audit
  subagents:
    - role: literature_collision_detector
      description: Internal Claude lit-grep on Step-4 pre-flight; blinded to repo charter prose
      tools: [read]
output_schema: anti_rename_gate_verdict_v1
fallback: PATTERN-002 (darwin_idea_killer if Step 4 returns ambiguous)
preconditions:
  - candidate_theorem_in_minimal_form: present (Step 1 output)
  - target_admissibility_class_named: present
chain_position: pre_charter  # gate runs BEFORE any Lean port or full charter
related_patterns:
  - PATTERN-002 (darwin_idea_killer, chained AFTER if Step 4 ambiguous)
  - PATTERN-014 (cold_shot_dispatch, used for Step 4 pre-flight if internal Claude isn't sufficient)
references:
  - C-2026-05-09-98 (μ[u] / Duchon-Robert RENAME)
  - C-2026-05-09-103 (defect-calc / CKN-Lin RENAME)
  - C-2026-05-09-104 (VBNS-PT / Bohr-mean energy identity RENAME)
  - PL-105 mm_01 ACR Q1-Q5 self-check
  - PL-106 Q3-binary literature-check protocol
falsifiable_test: |
  Over N>=10 closure-attempt charters passed through the gate, charters that PASS
  (gate_outcome=PASS_proceed_to_lean) must subsequently be demolished as RENAME by
  a post-Lean cold-shot or audit in <=10% of cases, AND this PASS-then-RENAME rate
  must be lower than the pre-gate baseline RENAME rate (empirically 3-of-3 = 100%
  in the 2026-05-09 window) by >=50 percentage points. If gate-passed charters are
  still demolished as RENAME at >10%, or the gate does not cut the RENAME rate by
  >=50 points versus the pre-gate baseline, demote.
  metric_source: anti_rename_gate_verdict_v1 records (gate_outcome) joined to the
  catch ledger for subsequent RENAME catches (C-98/C-103/C-104-class); charters
  tracked by charter_path.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-023, anti-RENAME charter gate

## Problem (empirically motivated 2026-05-09)

Three closure-attempts in 24 hours independently demolished as RENAME of
existing-2026 literature:

- **C-98** μ[u] := w*-lim Π_ℓ[u] defect-measure construction →
  re-derivation of Duchon-Robert (Nonlinearity 13, 2000) §2 in 3D
  Leray-Hopf via Ladyzhenskaya. Caught by second cold-shot.
- **C-103** Defect-calc rigidity (R) → standard CKN-Lin ε-regularity
  for suitable weak solutions. Caught by mm_01 Q3-binary +
  GPT-5 PL-106 + internal Claude lit-grep agent.
- **C-104** VBNS-PT finite-Σ stationary closure → one-line Bohr-mean
  energy identity (M[∂_j F] = 0 trivially for finite trig polys).
  Caught by GPT-5.5-Pro 11-min cold-shot on operator interface.

mm_01 ACR detector (PL-105, PRE-WARRANT) predicted RENAME would be
the dominant failure mode at the closure-attempt stage. **Empirical
3-of-3 in one window confirms the prediction at the charter-time
stage specifically**, not as a whole-apparatus indictment, but as a
specific failure mode the apparatus systematically lands on.

This pattern mechanizes the gate that catches RENAMEs at charter time,
BEFORE any Lean port or 5-file shipment.

## Pattern (5 steps, MECHANICAL)

### Step 1, Minimal-form statement
State the candidate closure theorem as: "for class X, conclusion Y
follows from mechanism Z." STRIP elite nouns (no VBNS-PT / Liouvillian-Σ
/ OCCT-style branding). The minimal form must fit in 2-3 sentences and
be parseable by someone who has not seen the apparatus's vocabulary.

### Step 2, mm_01 ACR Q1-Q5 self-check
Per `src/ztare/research_director/universal_research_ops.py::META_META_VOCABULARY[mm_01]`,
answer in writing:

  - **Q1** What admissibility-criterion is being rebased? (objects,
    proofs, solutions, states, which boundary moves?)
  - **Q2** Is this rebasing already executed in the literature?
    (Cite ≥3 candidate prior executions; if ZERO candidates, the
    apparatus has likely overlooked something.)
  - **Q3** What is the genuinely-NEW move beyond known rebasings?
    (1-2 sentences. If empty, target is core_07 generalization or
    rename, NOT mm_01 ACR.)
  - **Q4** What concrete strengthening of the conclusion would
    require the proposed move ESSENTIALLY (not as free-strengthening
    of input)?
  - **Q5** Charter-prose RENAME-drift detector: does proposed prose
    contain "we generalize / extend / adapt / port" → RENAME-drift
    suspected? Or "the joint admissibility class IS new" → mm_01-aligned?

### Step 3, Q3-binary literature-collision check
Per the `mm_01_self_check` discipline first applied at
`projects/ns_defect_calculus_pivot/DRAFT_charter.md` Q1-Q5: state the
binary

  *"Does the proof reduce to {standard tool A} + {standard tool B} +
  {viscous correction / interface step}, or does it require a specific
  non-standard ingredient that lives only in published 2026
  mathematics?"*

Answer requires identifying tools A, B by NAME with arXiv anchors
(PATTERN-014). If the answer is "reduces to standard tools", STOP,
the closure is a RENAME of those tools. If the answer is "requires
specific non-standard ingredient X", proceed to Step 4.

### Step 4, Pre-flight cold-shot (CHEAP)
BEFORE any Lean port or charter ratification:
  - Internal-Claude lit-grep agent (free): "is theorem T already
    known? cite ≥3 candidate adjacent results."
  - OR cheap external cold-shot ($0.20-0.40 cap): "is theorem T
    (a) RENAME of theorem U, (b) genuinely novel, (c) false, (d)
    open?", same prompt template as Q3-binary above.
  - Time-box: ≤30 min wall clock total.

### Step 5, Charter prose RENAME-drift detector
After charter draft is written but BEFORE ratification:
  - Read every paragraph; if contains drift indicator
    ("we generalize / extend / adapt / strengthen") → REWRITE
    using mm_01-aligned framing or DEMOTE the claim.
  - Specifically: if the charter cannot be rewritten without using
    drift indicators, the underlying theorem is likely a RENAME and
    Step 4 missed it.

## Output schema (anti_rename_gate_verdict_v1)

```
charter_path: <markdown path>
target_minimal_form: <2-3 sentences>
step_1_pass: bool
step_2_q1_admissibility_rebased: <text>
step_2_q2_prior_executions: [arxiv_id, ...]
step_2_q3_genuinely_new_move: <text or "EMPTY → RENAME-risk">
step_2_q5_drift_detected: bool
step_3_binary_verdict: "reduces_to_standard" | "requires_non_standard" | "indeterminate"
step_3_standard_tools_A_B: [<tool_with_arxiv>, ...]
step_4_pre_flight_run: bool
step_4_pre_flight_verdict: "rename" | "novel" | "false" | "open" | "skipped"
step_4_pre_flight_evidence: <link to agent transcript or cold-shot response>
step_5_charter_prose_drift_detected: bool
gate_outcome: "PASS_proceed_to_lean" | "REFUSE_charter_rename" | "REFUSE_charter_drift" | "INDETERMINATE_iterate"
catches_referenced: [C-id, ...]
```

## Why it works

- Step 1 strips elite-noun laundering (catch #23 op-catalog rigging
  defense).
- Step 2 forces explicit mm_01 ACR self-check; empty Q3 = RENAME-risk
  flag at writing time.
- Step 3 forces literature collision check at the proof-mechanism
  level; standard-tools-only verdict = abort.
- Step 4 pre-flight is the CHEAP version of what got us C-98 / C-103 /
  C-104, done at charter time, not after weeks of work.
- Step 5 closes the loop on charter prose drift.

## When to deploy

- ANY new closure-attempt charter (RD-B*, future)
- Any "we have a novel theorem" claim before Lean port
- Any minted PATTERN / ANTI-PATTERN claiming META-status

## When NOT to deploy

- Pure infrastructure work (mollifier API, type classes, weak-limit
  lemmas), these don't claim novel closure
- Routine sorry-closure on existing typed scaffolds
- Mining / analytics pipelines

## Empirical first-fire data (this gate's own validation)

The gate was retroactively applied to C-98 / C-103 / C-104:
- All three would have been caught at Step 3 (literature-collision
  check) had it been applied at charter-time.
- Saved cost: ~6 weeks of Lean work that would have been into
  RENAMEs of Duchon-Robert / CKN-Lin / Bohr-mean energy identity.
- Empirical first-fire 2026-05-09 ~23:30 UTC on PL-104 → caught
  defect-calc charter as RENAME pre-Lean.
