---
id: PATTERN-015
name: eigenquestion_phrasing_discipline
version: 2
status: active
discovered: 2026-05-09
discovered_reason: |
  Operator observation (2026-05-09 evening): GPT-5.5 was producing
  noticeably stronger output than internal Claude agents on the same
  substrate. Diagnosis: not a model gap, a prompt-shape gap. The
  Research Director had been dispatching constructive scoping packs
  (2-3 page prompts) to internal Claude agents, while the operator
  had been relaying 1-2 paragraph eigenquestion-shape prompts to
  GPT-5.5. The framing asymmetry is a real, fixable defect.
triggers:
  lexical: [eigenquestion, falsifiable, sharp, verdict-line, in-standard-form]
  structural:
    - dispatch_prompt_being_authored
    - load_bearing_decision_will_turn_on_dispatch_output
    - audit_or_calibrate_or_falsify_dispatch (NOT for construct/scope)
  problem_classes: [meta-architecture, all]
spawn:
  mode: prompt_review
  subagents: []  # this is a discipline applied to OTHER patterns' dispatch prompts
output_schema: eigenquestion_validated_v1
fallback: null  # if the prompt fails this discipline, REWRITE — do not dispatch
preconditions: []
chain_position: pre  # always runs BEFORE any audit/calibrate/falsify dispatch
related_patterns:
  - id: PATTERN-005
    relation: parent  # falsifiable_asymmetry — eigenquestion phrasing is the discipline that produces falsifiable demands
  - id: PATTERN-014
    relation: required  # cold-shot quality depends entirely on eigenquestion shape
  - id: PATTERN-002
    relation: applied_to  # darwin_idea_killer dispatches benefit
  - id: PATTERN-007
    relation: applied_to  # smuggling_audit dispatches benefit
falsifiable_test: |
  Over N>=20 audit/calibrate/falsify dispatches, prompts that PASS the 9-point
  checklist must have a catch-rate per dispatch >=2x the catch-rate of dispatches
  that fail the checklist (the pattern's own narrative cites an observed ~3.3x
  lift; 2x is the demotion floor). If checklist-passing prompts do not yield at
  least 2x the catch-rate of non-conforming prompts, the discipline adds no
  measurable lift and demotes.
  metric_source: pattern_deployment_ledger.jsonl eigenquestion_shape flag per
  dispatch, joined to catch-ledger catches attributed to each dispatch
  (catches-per-dispatch by eigenquestion_shape true vs false).
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-015 — Eigenquestion Phrasing Discipline

## What this pattern is

A **prompt-shape discipline** applied BEFORE any dispatch whose mode is
`audit | calibrate | falsify` (not `construct | scope`). It transforms a
generic prompt into an **eigenquestion** — a single falsifiable
proposition with explicit verdict-output requirements.

This pattern is **cross-cutting**: it applies to internal Claude agent
dispatches AND external cross-family LLM dispatches AND CAS verification
calls. It does not replace any other pattern; it is a prerequisite
discipline for all of them when the dispatch is in `audit/calibrate/
falsify` mode.

## The 9-point eigenquestion checklist

Before sending an `audit | calibrate | falsify` dispatch, every prompt
MUST satisfy:

1. **Single proposition.** The dispatch asks ONE question with a binary
   or low-cardinality answer. NOT "evaluate the architecture" but
   "is the architecture's core invariant Z preserved by transformation T?"
2. **Falsifiable.** The question states a precondition + a hypothesized
   conclusion such that a counterexample, if it exists, can be exhibited
   in standard form (precondition / hypothesis / quantifier scope /
   conclusion). NOT "is this approach reasonable?" but "does NS substrate
   provide property P? produce a proof or counterexample."
3. **Standard-form output.** The dispatch DEMANDS the answer in a
   structured form: precondition / hypothesis / divergences / verdict.
   Generic prose answers should be rejected (or re-prompted).
4. **Anchored failure modes named.** If the question is being asked
   AFTER a previous attempt failed, list what failed and why. This both
   provides context AND defends against re-deriving the same failure.
5. **Verdict line at the end.** The prompt requires the responder to end
   with: "VERDICT: [yes / no / partially / unknown] — [one-sentence
   rationale]." Hedged unstructured answers fail this.
6. **Citation discipline.** When the question references published
   results, demand arXiv ids + theorem numbers + page numbers. "It is
   well-known that X" without citation is a fail.
7. **Length cap.** Question body ≤ 1500 words. Tight context > long
   context. (Empirical observation 2026-05-09: operator-relayed 1-2
   paragraph GPT-5.5 prompts are demolishing 2-3-page Claude-internal
   dispatch packs at the same job.)

8. **Meta-catch self-application (added 2026-05-09 per catch C-73).**
   When an audit/calibrate/falsify dispatch produces a META-CATCH (a
   catch about catches, a meta-pattern minting, an aggregation of
   sub-findings), the dispatch's OUTPUT must self-apply PATTERN-005
   (falsifiable_asymmetry) + PATTERN-003 (reducer) BEFORE the catch is
   logged or downstream-propagated. Specifically:

   * The catch's `title` + `structural_correction` field MUST state an
     EMPIRICALLY FALSIFIABLE claim, not a metaphor (e.g. "apparatus
     immune system functioning" or "catch chain terminates in
     irreducible-open" are true-by-construction unless the
     falsification base is named).
   * The catch's `fix_artifact` field MUST be a SINGLE CONCRETE
     ACTION (file:line edit, axiom shipping, script run), not a
     branching "IF X then A; IF Y then B" conditional. Conditional
     catches must split into two atomic catches.
   * Metaphysical / immune-system / methodology-reflection language
     is allowed in narrative sections (paper drafts, journey doc) but
     NOT in catch-claim layer.

	   Empirical baseline (2026-05-09 audit on C-58..C-72): external-prover
	   catches scored 6/6 falsifiability + 5/6 reducer-pass; internal-Claude
	   META-LEVEL catches scored 2/4 with narrative-abstraction weakness.
	   The 8th-point self-check closes that quality gap.

9. **Computation-pressure telemetry (added 2026-05-10 from NS L3A
   `CodimFourSublevelVolumeFromExcess`).** Runtime is not evidence of
   correctness and never substitutes for answer checking. But relative
   runtime can be weak telemetry about prompt quality when the same
   model/interface has a stable baseline. If a prompt that usually gets
   a 4-minute template answer instead runs 9+ minutes, the prompt may
   have denied cheap exits and forced work on exponent bookkeeping,
   countermodel search, or theorem-surface selection.

   Log this only as `computation_pressure_observed`, and only when the
   output is later checked against the actual fork. The signal is useful
   iff longer runtime predicts a sharper proof/no-go/partial decision
   with a named first illegal inference or smaller primitive. If it only
   predicts longer prose, ignore it.

   The good pattern:

   * name the decisive primitive;
   * block known laundering routes;
   * provide a countermodel template that must be killed or admitted;
   * require fork choice plus first illegal inference.

## Internal-Claude vs External-cross-family asymmetry catch

The 2026-05-09 framing-asymmetry catch was specifically:
* RD dispatching to internal Claude agents → 2-3 page constructive
  packs → agents return scaffolding work, miss eigenquestion content.
* Operator dispatching to external GPT-5.5 → 1-2 paragraph
  eigenquestion-shape prompts → return sharp falsifiable verdicts that
  demolish RD claims.

The asymmetry is NOT primarily about model capability. It is about
prompt shape. PATTERN-015 closes the gap: when an internal Claude
dispatch is in `audit | calibrate | falsify` mode, apply the same
checklist. When an external cold-shot (PATTERN-014) is being
dispatched, also apply this checklist (cold-shot's 5-bullet discipline
is necessary but not sufficient — eigenquestion phrasing is the
remaining discipline).

## When to relax

For `construct | scope` mode dispatches (close a Lean sorry, scope a
sub-PR, generate candidate constructions), this discipline is overkill.
Constructive scoping benefits from longer-context dispatch packs.
PATTERN-015 fires only on `audit | calibrate | falsify` mode.

## Falsifiable-asymmetry test (per PATTERN-005)

The discipline is "working" iff: prompts that pass the checklist
have a higher catch-rate per dispatch than prompts that don't. The
empirical baseline (2026-05-08/09): 2 operator-relayed eigenquestion-
shape GPT-5.5 dispatches surfaced C-58 + C-59 (2 catches in 2
dispatches → catch rate 1.0). 17 internal Claude dispatches surfaced 5
catches (C-53 to C-57 from cross-vocab audit) → catch rate ~0.3. The
ratio (1.0 / 0.3) ≈ 3.3 is the empirical eigenquestion-phrasing lift.

Secondary telemetry test: for the same model/interface/substrate family,
track `runtime_ratio = prompt_runtime / recent_baseline_runtime`. Runtime
telemetry is useful only if `runtime_ratio >= 2` correlates with higher
decision quality: proof/no-go/partial fork, first illegal inference,
or smaller primitive named. Runtime alone is not a verdict.

## Anti-laundering catches

* **Pseudo-eigenquestion**: a dispatch that looks structured but asks
  multiple questions, has no verdict line, or has no falsifiable
  precondition. Should be caught at the prompt-review step BEFORE
  dispatch.
* **Verdict-line theater**: the prompt demands a verdict line but the
  responder hedges. The discipline must be enforced on the OUTPUT side
  too: hedged outputs should be re-prompted, not accepted as the answer.
* **Length-cap violation laundering**: padding the prompt with
  scaffolding ("here is the surrounding architecture context, here are
  10 prior failed attempts in detail, ...") under the false belief that
  more context produces sharper answers. Empirically false (see above).
