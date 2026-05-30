---
id: PATTERN-026
name: primitive_before_architecture_gate
version: 1
status: active
discovered: 2026-05-15
triggers:
  lexical: ["multi-layer architecture", "Layer 2a / Layer 2b / Layer N", "first pass is crude", "research thread", "deferred to future work", "TBD", "Layer N retrieves the gap"]
  structural:
    - architecture_spec_contains_unvalidated_layer
    - layer_marked_deferred_or_TBD_inside_architecture_doc
    - layer_admits_crude_first_pass_in_same_doc
    - architecture_proposes_composition_before_primitives_pass_gates
  problem_classes: [apparatus_self_audit, architecture_design]
spawn:
  mode: output_gate  # pre-acceptance enforcement gate
  subagents: []
output_schema: primitive_validation_verdict_v1
fallback: PATTERN-002  # darwin_idea_killer (if architecture ships anyway, kill it post-hoc)
preconditions:
  - artifact_claims_to_be_architecture: yes
  - architecture_has_multiple_named_layers: yes
chain_position: pre  # runs BEFORE accepting architecture as ready-to-ship
related_patterns:
  - PATTERN-005 (falsifiable_asymmetry — sibling: claim-level falsifier requirement; this pattern is the architecture-level analog)
  - PATTERN-002 (darwin_idea_killer — fallback if architecture ships without primitive validation)
  - ANTI-PATTERN-008 (deployment_time_pre_spec_laundering — sibling at the deployment-timing level)
references:
  - GP-233 §7 (DEMOTED 2026-05-15) — the failure that motivated this pattern
  - GP-235 (DAG fingerprint primitive validation seam) — the corrective application
falsifiable_test: |
  Once wired as the pre-acceptance gate, over N>=15 multi-layer architecture
  artifacts passed through the gate, architectures that PASS (every layer cites
  artifact + pass-gate + measurement) must be subsequently demolished as
  ARCHITECTURE-IS-FACADE by a PATTERN-002 Meta-Darwin audit in <=10% of cases, AND
  this PASS-then-facade rate must be at least 50 percentage points below the
  pre-gate baseline facade rate (the GP-233 §7 class: facade confirmed on the
  un-gated architectures audited in the 2026-05-15 window). If gate-passed
  architectures still collapse as facade at >10%, or the gate does not cut the
  facade rate by >=50 points, demote.
  metric_source: primitive_validation_verdict_v1 records (gate_outcome) joined to
  subsequent PATTERN-002 audit verdicts (KILL/WEAK-KILL counts) on the same
  architecture artifact; dispatches tagged PATTERN-026.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# Pattern 26 — Primitive-Before-Architecture Gate

## Problem

Multi-layer architectures fail when written on top of unvalidated primitives. The author names layers (Layer 1, Layer 2a, Layer 2b, …), describes how they compose, and ships the composition as architecture — while one or more layers is admittedly "TBD," "first pass is crude," "research thread," or "deferred to future work."

The failure mode: the architecture's plausibility depends on every layer behaving as specified, but at least one layer doesn't yet exist as a validated component. The architecture looks central on paper while resting on a primitive that hasn't passed any test. When the unvalidated primitive turns out to be broken (which it usually is — that's why it was deferred), the whole architecture collapses, but the author has already published the "architecture" framing and accumulated downstream commitments (pass-gate definitions, ablation row plans, dispatch contracts) that now have to be retracted.

This is a specific failure mode of *composition*, distinct from claim-level falsifiability (PATTERN-005) and deployment-timing pre-registration (ANTI-PATTERN-008). It happens at architecture-design time, before any deployment, before any claim is shipped to a reviewer.

## Pattern

**Before any multi-layer architecture is accepted as architecture, every layer must independently pass:**

1. **Implemented:** the layer has a concrete artifact (code, schema, prompt template, decision rule). Not a name with a paragraph of prose.
2. **Measured:** the layer has been run on representative input and produced numeric output that can be compared against expected behavior.
3. **Within pass-gate range:** the numeric output meets pre-registered pass-gates. Pass-gates are committed BEFORE the layer is run.

If any layer fails one of (1)/(2)/(3), the architecture is DEMOTED to "exploration notes" and each unvalidated layer is split into its own primitive-validation seam with its own pass-gates. Only after every primitive validates may the architecture be re-proposed in a fresh seam.

## Definition of "layer" (added 2026-05-15 per Meta-Darwin v2 REVISE)

A **layer** is any named component of an architecture spec such that *the failure of that component would cause architecture-level claim retraction*. This is the operational test, not a positional or naming criterion:

- A component named "Layer 2b" qualifies if §7 claims about Route C would be retracted should 2b fail.
- A subsection labeled "Helper X" qualifies if architecture's success depends on X behaving as described.
- A "fallback" or "graceful degradation" path qualifies if the architecture promises it as a deliverable.

This definition prevents gaming the ∀-test by merging two layers into one (the merged component still has the same retraction-dependency) or splitting one layer into many (each sub-component must independently support the architecture's claim).

## Detection — structural, not lexical (revised 2026-05-15)

The original v1 of this pattern listed lexical markers ("first pass is crude" / "TBD" / "research thread") as detection triggers. Meta-Darwin v2 correctly observed these are paraphrase-launderable (an author can write "v1 implementation is approximate" and pass the grep). Detection is now **structural**:

**Primary structural test:** for each component identified per the layer definition above:

1. **Does the component have an artifact citation?** (Code file path, schema, prompt template, decision rule with concrete inputs/outputs.) If the section describing the component does not point to a concrete artifact, the component is unvalidated.
2. **Does the component have a pass-gate defined?** (Numeric threshold, expected output behavior, or pre-registered acceptance criterion.) If the section describes behavior but does not commit to a pass condition, the component is unvalidated.
3. **Has the component been measured?** (Numeric output against the pass-gate.) If no measurement is reported in the seam OR cited from a prior seam, the component is unvalidated.

Any (1)/(2)/(3) failing for any layer triggers this gate. The check is mechanical — does the architecture's section for component X cite a concrete artifact, a pass-gate, and a measurement?

**Secondary structural test:** layer self-falsification. If the document contains *both* "Component X works as follows: …" *and* a reported measurement of X performing below the architecture's implicit pass-gate (e.g., "X accuracy is 25%" when architecture assumes X works), the architecture is internally inconsistent. This test is purely numeric — find the measurement, find the pass-gate, compare.

**Tertiary test (audit calibration):** apply this pattern to 5 historical seams in the repo. If "what counts as a layer" requires case-by-case judgment for >2 of 5, the pattern's layer-definition is too vague and must be refined further. Pre-registered audit targets:
- GP-225 v22 through v30 chain
- GP-191 Stage 2 tenant overlay
- GP-216 theory-building ops
- GP-168 OKR addendum
- GP-156 fit_primitive_features

## Mitigation

Two artifacts in this order:

1. **Primitive validation seam(s)** — one per unvalidated layer. Each seam defines the primitive concretely, builds it, runs it on representative input, measures, and reports against pre-registered pass-gates. The seam terminates with PASS or FAIL.
2. **Architecture seam** — written ONLY after every required primitive's validation seam has shipped PASS. References each primitive validation seam by ID. Cannot be drafted before primitives validate.

If a primitive's validation seam reports FAIL, the architecture seam cannot be written and the approach must be re-thought (or dropped).

## Example (the GP-233 §7 failure)

GP-233 §7 was written as "5-layer Route C architecture" with named layers 2a/2b/2c/2d/3.5. Layer 2a was claimed to be a heuristic operation-type classifier. In §7.6.5 of the same seam, Layer 2a's accuracy was reported at 25% top-1 (with the architecture's implicit pass-gate ≥80%). Layer 2b was claimed to be a content-axis gap retriever, with the same seam noting "first pass is crude" and "this is the hardest step" and "its own research thread." Both layers were architecturally central for Layer 2c's "decompositional + structured rejection feedback" claim.

Result (validated 2026-05-15):
- External Meta-Darwin (PATTERN-002) verdict: ARCHITECTURE-IS-FACADE. 6 KILL / 3 WEAK-KILL across 10 audit axes.
- Concurrent 10-row ablation: Mode D archetype routing produced 0 distinct closures over Mode A baseline (3/10 in both, SAME tactics on all 3).
- Both lines of evidence converged on the same finding: the architecture's claims were unsupportable.

The corrective: demote §7, write GP-235 as a primitive-validation seam for the DAG fingerprint primitive (the new central component), pre-register pass-gates, validate FIRST, and only then propose a follow-on architecture seam (GP-236) if the primitive validates.

## Falsifiable test

A multi-layer architecture passes this gate iff:

```
∀ component L matching the layer definition:
    L.has_concrete_artifact_citation == True
  ∧ L.has_pass_gate_defined == True
  ∧ L.has_been_measured_against_pass_gate == True
  ∧ L.measured_output >= pass_gate_threshold == True
```

The gate fires (architecture is rejected) iff any (component, condition) pair fails. The check is mechanical and structural:

1. Identify components by the layer definition (anything whose failure would retract architecture-level claims).
2. For each, locate the artifact citation. If absent → fire.
3. For each, locate the pass-gate. If absent → fire.
4. For each, locate the measurement. If absent → fire.
5. For each, compare measurement to pass-gate. If below → fire.

Architecture remains rejected until every layer passes a separate primitive-validation seam (per `mitigation` above) and that seam's PASS outcome is cited in the architecture seam.

## MECE clarification with ANTI-PATTERN-008 (added 2026-05-15)

Meta-Darwin v2 correctly observed the original MECE-with-ANTI-PATTERN-008 distinction was rhetorical ("temporal hair-split"). The structural distinction:

- **ANTI-PATTERN-008** fires on *time-stamp* of pre-spec vs *time-stamp* of deployment. Mechanical check: `commit_time(pre_spec) < commit_time(first_dispatch_log)`. Concerns: pre-deployment paperwork ordering.
- **PATTERN-026** fires on *artifact-citation* and *measurement* of components vs *claims* in architecture. Mechanical check: `∀ component: artifact ∧ pass-gate ∧ measurement ∧ pass`. Concerns: composition of unvalidated components into architecture-level claims.

Both can fire on the same artifact (e.g., an architecture seam written before its primitive validation AND its pre-spec not committed before agents dispatched) but they fire on different mechanical signals. A seam could pass ANTI-PATTERN-008 (proper pre-spec timing) while failing PATTERN-026 (components not validated), or vice versa.

## What this pattern does NOT replace

- It does NOT replace PATTERN-005 (falsifiable_asymmetry) — that operates on individual CLAIMS, not on layered architectures. Both can fire on the same artifact.
- It does NOT replace ANTI-PATTERN-008 (deployment_time_pre_spec_laundering) — that operates on the TIMING of pre-registration vs deployment. Both can fire on the same artifact.
- It does NOT prohibit exploration of architectural ideas. It only prohibits SHIPPING those ideas as "architecture" before primitives validate. Exploration notes / draft documents are fine; they just cannot be cited as central architecture.

## Related anti-patterns this defends against

- `deployment_time_pre_spec_laundering` (ANTI-PATTERN-008)
- `criterion_selection_rigging` — picking the metric to suit the answer (architecture redefines its own success criterion)
- `vocabulary_smuggling` + `vocabulary_chain_laundering` — layered jargon (Layer 2a/2b/2c) gives illusion of structural completeness while standing in for unsolved problems

The combined hit on these anti-patterns inside a single architecture spec is the diagnostic signal that this gate should fire.
