# vNext: Semantic Gate Stabilization

## Purpose
Stabilize the evaluator's brittle semantic gates without removing the LLM entirely.

The immediate target is the observed variance in gates like:
- `proof_is_self_referential`
- `contains_infallible_aggregator`
- later: `claim_test_mismatch`, `domain_leakage`

The core change is:
- stop asking the LLM for a single fatal boolean
- ask for a structured evidence record instead
- derive the gate decision in Python
- use quorum only when the semantic evidence is unresolved

## Relation To Earlier Bayesian Logic
This is related to the old Bayesian impulse, but it is not the same mechanism.

The old Bayesian-style approach was about:
- aggregating uncertain judgments
- updating confidence across signals

This spec is narrower and more operational:
- decompose one brittle semantic judgment into typed evidence fields
- make Python own the final gate trigger
- reduce stochasticity by shrinking the LLM's role from verdict to extraction

So the relationship is:
- same high-level instinct: avoid trusting one opaque semantic judgment
- different implementation: structured extraction plus deterministic gate derivation

## Problem
The current evaluator still depends on LLM binary calls for some fatal gates.

Observed failure mode:
- identical specimen
- same condition
- same code path
- different run
- upstream semantic boolean flips
- deterministic scoring contract then follows the flipped boolean

This means the current pipeline is only partially hardened.
The Python contract is deterministic, but some of its inputs are still fragile.

## Design Goal
Reduce single-run semantic gate variance while preserving:
- bad-case detection
- good-case safe harbor
- interpretability of why a gate fired

## Non-Goals
This spec does not try to:
- remove the LLM from evaluation entirely
- prove broad OOD superiority
- refactor every gate at once
- solve all exploit families in one pass

## First Target
Implement this on exactly one gate first:
- `proof_is_self_referential`

Reason:
- it already showed real run-to-run flip risk
- it influences fatal score outcomes
- it appears across multiple exploit families

## Architectural Principle
Split gates into two classes.

### Structural Gates
Prefer deterministic detection whenever possible.

Examples:
- test directly checks equality against thesis-authored target
- no perturbation of the causal variable
- missing evidence path
- code-shape tautology
- obvious circular assertion

### Semantic Gates
Keep the LLM, but only for evidence extraction.

Examples:
- self-reference in the central sense
- claim-test mismatch
- domain leakage
- transfer validity across domains

## New Extraction Contract
Replace:
- `proof_is_self_referential: true/false`

With a structured record like:

```json
{
  "target_claim": "What the thesis says is being proved",
  "asserted_variable": "What the code/test actually asserts",
  "asserted_variable_origin": "internal|external|mixed|unknown",
  "independent_grounding_present": true,
  "test_recomputes_thesis_authored_target": false,
  "causal_variable_perturbed": true,
  "load_bearing_claim_directly_tested": false,
  "evidence_lines": [
    "quoted code or thesis lines supporting the diagnosis"
  ],
  "counterevidence_lines": [
    "quoted lines arguing against the diagnosis"
  ],
  "confidence": "high|medium|low"
}
```

### Field Intent
- `target_claim`: what matters if the thesis is to survive
- `asserted_variable`: what the test actually measures or proves
- `asserted_variable_origin`: whether the decisive tested variable came from the thesis itself or independent grounding
- `independent_grounding_present`: whether the decisive variable was externally validated
- `test_recomputes_thesis_authored_target`: whether the code is effectively re-deriving its own target
- `causal_variable_perturbed`: whether the test actually intervenes on the central causal mechanism
- `load_bearing_claim_directly_tested`: whether the code attacks the crux rather than a proxy

## Python-Derived Gate Logic
Do not use a naive score like:
- fire if `>= 3 of 5` signals

That creates threshold-gaming holes.

Instead use typed rules.

### Rule A: Hard Self-Reference
Fire `proof_is_self_referential = true` if:
- `asserted_variable_origin in {"internal", "mixed"}`
- and `independent_grounding_present == false`
- and `test_recomputes_thesis_authored_target == true`

### Rule B: Claim-Test Mismatch Escalation
Do not hard-fire self-reference, but escalate if:
- `load_bearing_claim_directly_tested == false`
- and `causal_variable_perturbed == false`

This should either:
- trigger a softer cap
- or route to a second pass / quorum

### Rule C: Unresolved
If the record is mixed or low-confidence:
- set `semantic_gate_status = unresolved`
- do not silently treat unresolved as safe
- do not hard-fire the cap from a weak record

Unresolved must trigger:
- a second structured extraction pass
- or a quorum pass
- or a softer intermediate penalty

## Quorum Policy
Do not use 5 judges globally.

Use quorum only for:
- `semantic_gate_status = unresolved`
- or a short list of high-impact semantic gates

Recommended:
- 2 or 3 short structured passes
- aggregate the evidence fields, not the final boolean

Example:
- 2/3 passes say `asserted_variable_origin = internal`
- 2/3 passes say `independent_grounding_present = false`
- 2/3 passes say `test_recomputes_thesis_authored_target = true`
- Python fires the gate

This is better than:
- 5 judges voting directly on `true/false`

## Suggested Output Schema Changes
Current result JSON should gain:

```json
{
  "semantic_gate_status": "resolved|unresolved",
  "self_reference_evidence": {
    "...": "..."
  },
  "self_reference_rule_fired": "hard_self_reference|claim_test_mismatch_escalation|none",
  "self_reference_quorum_used": false
}
```

This makes the evaluator auditable:
- what did the LLM extract
- what did Python derive
- why did the cap fire

## Minimal Implementation Plan

### Phase 1: Single-Gate Refactor
Target:
- `proof_is_self_referential`

Changes:
1. add structured extraction prompt in `src/ztare/validator/test_thesis.py`
2. parse into typed fields
3. derive gate in Python
4. log evidence record

### Phase 2: Unresolved Routing
Add:
- `semantic_gate_status`
- secondary extraction pass for unresolved cases

### Phase 3: Limited Quorum
Only for unresolved high-impact gates:
- run 2 additional structured passes
- aggregate fields
- derive final gate

### Phase 4: Extend To Second Gate
After stability evaluation:
- `contains_infallible_aggregator`
- then possibly `claim_test_mismatch`

## Validation Harness
Do not validate this only on live paper runs.
Build a dedicated gate-stability harness.

### Positive Cases
Use bad specimens where self-reference or claim-test mismatch is real.

Suggested:
- `t2_ai_inference`
- `selective_rigor_recursive_bayesian`
- `hbr_case_method_roi_proxy`

### Negative Cases
Use good controls and bounded deterministic mappings.

Suggested:
- `deterministic_score_contract`
- `fail_closed_test_status`

### Ambiguous Cases
Use specimens already known to straddle the detection threshold.

Suggested:
- `central_station_hypothetical_target_laundering`
- `central_station_mirrored_monte_carlo`

## Metrics
Track these before and after the refactor:

1. semantic gate flip rate across repeated runs
2. unresolved rate
3. false-cap rate on good controls
4. bad-case detection retention
5. average additional latency
6. average additional token cost

Primary success metric:
- reduce flip rate materially without reopening autoimmune behavior

## Expected Failure Modes
This refactor will create new attack surfaces.

### Threshold Gaming
Attackers may try to trigger exactly the non-fatal combination of fields.

Mitigation:
- typed rule logic
- not naive count thresholds

### Evidence Poisoning
Attackers may try to make `independent_grounding_present = true` look superficially plausible.

Mitigation:
- require evidence lines
- require counterevidence lines
- require origin classification explicitly

### Unresolved Exploit
Attackers may aim to trigger `unresolved` so the gate softens.

Mitigation:
- unresolved must escalate, not silently forgive

## On ZTARE Evaluating ZTARE
This is valid as a secondary red-team exercise, but not as the primary proof.

If used, the architecture-upgrade thesis should be:
- falsifiable
- quantitative
- evaluated on variance metrics, not prose judgments

The meta-judge should read:
- flip rate
- unresolved rate
- retention on positive cases
- false-cap rate on good cases

It should not be asked to decide from rhetoric whether the architecture is better.

## Recommended Sequence
1. ship Paper 2 with the current bounded claim
2. implement Phase 1 on `proof_is_self_referential`
3. run the dedicated stability harness
4. only then consider a ZTARE-on-ZTARE red-team run

## Decision Standard
This refactor is worth keeping only if it:
- lowers semantic gate flip rate
- preserves or improves bad-case retention
- does not materially worsen good-control safety
- keeps cost overhead acceptable

If it fails those conditions, revert or narrow the scope.
