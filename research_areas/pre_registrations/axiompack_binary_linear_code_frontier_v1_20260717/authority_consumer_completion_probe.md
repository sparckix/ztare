---
description: "Pre-registered completion probe for composite, falsifier, and certificate consumers."
status: closed_pass
date: 2026-07-18
---

# Authority-consumer completion probe

## Eigenquestion

Can any non-root producer or downstream consumer mint mathematical credit from
an omitted authority field, an unbound theorem selector, an inconclusive axiom
audit, or a statement match that ignores binders?

## Hypothesis

Three remaining routes can: composite assembly Boolean-coerces a kernel result
and accepts an inconclusive axiom audit; the falsifier discovers its target by
first-match suffix; and certificate consumers do not all bind the target
signature. Requiring explicit availability, a positive axiom receipt, the
host-owned refutation name, and full target-signature identity will close the
routes without changing proof search.

## Discriminating controls

- unavailable composite kernel and inconclusive composite axiom audit remain
  open;
- a same-conclusion chain with changed binders is rejected;
- a helper ending in `_refute` cannot displace the host-owned refutation;
- a certificate with a changed or missing target-signature binding cannot be
  selected or consumed;
- existing explicit-positive controls still pass.

## Kill conditions

- a repair prescribes proof strategy rather than verification;
- a domain-specific branch enters common authority code;
- a runtime fault is converted into mathematical counterevidence.

## Result

Passed. Composite assembly now requires explicit positive kernel and axiom
receipts and compares the full normalized target type, including binders and
hypotheses. The falsifier receives the exact host-owned refutation theorem
name. Closure certificates and parity records carry target-signature hashes
and the final roster digest.

Campaign admission, external-science admission, result cards, curriculum
adjudication, consequence bridging, and solver banking all call the common
`finalized_ratification_eligible` predicate. External-science materialization
selects a closure/parity pair only after matching record hash, target, job,
run, goal, source, probe, target signatures, and authority policy. A new
crossed-pair control shows that two independently valid but differently bound
rows cannot be combined.

The composite/falsifier controls are in `tests/test_ratification_route.py`;
the closed-artifact and consumer controls are in
`tests/test_closed_artifact_finalizer.py`, `tests/test_result_cards.py`,
`tests/test_target_curriculum_adjudication.py`,
`tests/test_lean_consequence_bridge.py`,
`tests/test_generic_fol_task_discharge.py`, and
`tests/test_external_science_admission.py`.
