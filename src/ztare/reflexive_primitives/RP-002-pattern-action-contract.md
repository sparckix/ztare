---
id: RP-002
name: pattern_action_contract
version: 1
status: active
leg_applied: "Compress + Adversarial Disagreement"
target: "Research Director pattern consumption and tick evidence path"
verdict: "B (PARTIALLY NOVEL)"
dependencies:
  - org/patterns/
  - org/anti-patterns/
  - org/menu/orchestration_menu.yaml
  - workingpapers/epistemic-generation/research_log.md
  - src/ztare/research_director/pattern_action_contract.py
falsifier:
  test: "Across the next 10 depth-sensitive RD closes, fewer than 7 close payloads include a pattern_action_contract and filled required carrier_artifacts, or contract-bearing closes have the same tool-underuse catch rate as the 10 prior comparable closes."
  monitoring_artifact: "analytics/public/queries/rd_pattern_action_contract.json plus official tick_close exports"
  period: "2026-05-20 .. 2026-06-20"
anti_laundering_commitments:
  - "Do not claim the pattern catalogue improves solver quality from this primitive."
  - "Measure filled evidence carriers and changed artifacts, not mentions of pattern names."
  - "If passive labels outperform the contract in a future sealed run, demote this entry."
---

# RP-002 — Pattern Action Contract

## What It Is

`pattern_action_contract.py` turns the architecture's own pattern,
anti-pattern, and menu layer into a structured action contract for RD ticks.
It maps the current problem surface to:

- pattern chain;
- anti-pattern guards;
- route tests;
- required evidence-carrier artifact slots;
- stop and decision rules.

The close client then requires depth-sensitive `research_done.json` payloads to
include the contract artifact and to fill the required carrier slots. This makes
"used a pattern" mean "produced the evidence path the pattern requires," not
"mentioned the pattern in prose."

## Why This Is Reflexive

The architecture is using its own pattern catalogue and empirical
epistemic-generation evidence to govern its own next research action. That is
self-referential architectural context, which belongs in the reflexive
primitive registry rather than only in `org/patterns/`.

## Evidence Basis

The operational evidence comes from
`workingpapers/epistemic-generation/research_log.md`:

- passive primitive labels and operator prose often changed rationale
  vocabulary without changing route choice;
- schema-matched generic baselines often matched or beat primitive prose;
- the stronger residual hypothesis is evidence-carrier forcing: route the work
  to a concrete next question, evidence carrier, gate, breaker, defer, or kill
  decision, then check the downstream artifact.

This primitive implements that narrower lesson. It is not a paper-grade claim
that primitives improve agents; it is a workflow change justified by the best
current internal evidence.

## Boundary

This is a dynamic JSON/data-contract carrier, not a static Ada-style type
system and not a Lean proof object. It is typed in the practical sense:
structured dataclasses, local artifact refs, required slots, and close-time
validation. AST-level checks remain in lower-level gates when the object being
checked is code, Lean, or an algebraic expression.
