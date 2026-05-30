---
id: PATTERN-018
name: structural_residual_analogy
version: 1
status: active
discovered: 2026-05-09
discovered_reason: |
  META-DARWIN audit on pattern architecture (2026-05-09 evening) flagged
  src/ztare/fit/analogy.py (GP-164) as a missing pattern. Cross-domain
  transfer mechanism that fires when the operator-curated grammar is
  exhausted (no template passes holdout) AND a non-trivial residual
  fingerprint exists. Distinct from PATTERN-014 (cold-shot is de-
  anchoring; analogy is cross-domain transfer within the same substrate).
triggers:
  lexical: [analogy, isomorphism, cross-domain, structural transfer, residual fingerprint]
  structural:
    - operator-curated grammar exhausted (no template passes holdout)
    - non-trivial residual fingerprint exists
    - light semantic domain hint available (physics / biology / math / social)
    - imported frame can be compiled into a target-side receipt or falsifier
  problem_classes: [grammar_exhaustion, cross_domain_transfer, mutator_priming, receipt_forced_transfer]
spawn:
  mode: kernel_call
  module: src.ztare.fit.analogy
  inputs:
    - residual_fingerprint:
        - regime_break_flag
        - monotonicity_flag
        - heavy_tail_flag
    - light_semantic_domain_hint:  # NOT the answer; only the domain category
        choices: [physics, biology, math, social]
  outputs:
    - candidate_forms_for_compress  # advisory; gates via holdout
    - target_side_receipt_obligation  # theorem/gate/formal field/falsifier, required for hard research use
  default_mode: observe  # active mode requires rubric flag enable_analogy_active=True
related_patterns:
  - id: PATTERN-014
    relation: distinct  # cold-shot is de-anchoring within the question; analogy is cross-domain transfer of TOOLS within a substrate
  - id: PATTERN-019
    relation: feeds  # adaptive eigenquestion generation can use the analogy outputs
  - id: PATTERN-005
    relation: requires  # candidate forms must pass holdout (falsifiable_asymmetry)
references:
  - existing kernel: src/ztare/fit/analogy.py
  - GP-164 cross-domain transfer
falsifiable_test: |
  Over N>=10 analogy deployments, candidate forms produced by the analogy kernel
  must pass the substrate holdout gate (or, for theorem work, force a concrete
  target-side receipt that changes a branch decision) at a rate >=1.5x the
  holdout-pass rate of randomly-sampled domain-template forms tested against the
  same residual. If analogy candidates pass at <1.5x the random-template baseline,
  the cross-domain transfer is noise and demotes.
  metric_source: analogy candidate-form holdout-pass results vs random
  domain-template control runs (COMPRESS-cycle holdout logs); receipt-bearing
  deployments tracked via analogy_mapping_receipt artifacts.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-018 — Structural Residual Analogy

## What this pattern is

A **cross-domain transfer mechanism** for when the operator-curated
grammar exhausts on a substrate (every template fails the holdout
gate) AND a non-trivial residual fingerprint exists. The apparatus
extracts structural topology features (regime-break, monotonicity,
heavy-tail flags) from the residual + an optional light semantic
domain-hint (physics/biology/math/social, NOT the answer), queries a
frontier LLM with ONLY the fingerprint (no variable names, no charter
prose), and treats the response as a HYPOTHESIS subject to holdout
verification.

Output: candidate forms feed the next COMPRESS cycle; the holdout
gate verifies. ADVISORY by default; active mode (rubric flag
`enable_analogy_active=True`) wires candidates into the next-iter
mutator prompt.

For Research Director hard-research use, analogy has a stricter interface:
it is only credited when it produces a target-side receipt obligation. The
artifact must include the source-target mapping, the invariant that must
survive transfer, the target theorem/gate/formal field/falsifier that would
check it, and the decision consequence if that check passes or fails.
Analogy as explanatory vocabulary is not a result.

## Distinct from cold-shot (PATTERN-014)

* **PATTERN-014 (cold_shot_dispatch)**: de-anchors WITHIN the question
  — same substrate, same problem, alien-math-tradition framing
  applied to break attractors.
* **PATTERN-018 (structural_residual_analogy)**: transfers TOOLS
  across substrates — a different tradition's known forms, brought
  into THIS substrate via residual-fingerprint matching.

Both are anti-anchoring; the axes are orthogonal.

## When to deploy

* **Grammar-exhaustion signal**: operator-curated grammar templates
  all fail holdout for K consecutive iters. Default K=3.
* **Non-trivial residual**: the residual has structure (regime break
  / heavy tail / non-monotonicity) that can be pattern-matched cross-
  domain.
* **Pre-cold-shot variant**: if grammar exhaustion is the trigger,
  try analogy first (cheaper, in-domain-tools-from-elsewhere) BEFORE
  paid cold-shot (more expensive, alien-math from scratch).

## Operate-mode discipline

Default `observe` mode: the apparatus runs and logs candidates without
mutating the next-iter mutator prompt. `active` mode requires
`enable_analogy_active=True` in the substrate's rubric. This guards
against "analogy hallucination wrote the next-iter form" laundering.

## Falsifiable-asymmetry test (per PATTERN-005)

The pattern is "working" iff: candidate forms produced by analogy in
observe mode have a higher holdout-pass rate when retrofitted into
COMPRESS than randomly-sampled domain-template forms. Empirically
testable by retrospective compare of analogy candidates vs random
domain-templates against the same residual.

For theorem/frontier work without numeric holdout, replace holdout-pass with
receipt consequence: the analogy must force a concrete next check (formal
field, workbench gate, theorem-applicability receipt, or countermodel) that
changes the branch decision. If it only improves the story, classify it as
vocabulary transfer and stop.

## Anti-laundering catches

* **Variable-name leakage**: passing variable names or charter prose
  to the analogy LLM contaminates the cross-domain query. Mitigation:
  the analogy LLM only sees the fingerprint (numerical structural
  features) + the light semantic-domain hint.
* **Active-mode-by-default laundering**: silently flipping the
  active-mode flag on substrates where the operator hasn't authorized
  it. Mitigation: the flag is required in the rubric and the
  apparatus logs the flag value at every dispatch.
* **Holdout-bypass laundering**: candidate forms wired into the next-
  iter mutator without passing the substrate's holdout gate.
  Mitigation: holdout gate is enforced upstream of the COMPRESS step;
  analogy candidates flow through the same gate.
* **Receipt-free vocabulary transfer**: the agent maps words across fields
  but never creates a target-side theorem, gate, formal field, or falsifier.
  Mitigation: `OP-XFT-01` and `pattern_action_contract.py` require an
  `analogy_mapping_receipt` before analogy can justify another spend.
