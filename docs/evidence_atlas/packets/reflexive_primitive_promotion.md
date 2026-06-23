---
description: "Review packet for a bounded reflexive primitive-promotion claim: repeated agentic workbench route gaps become a typed carrier with deterministic tests."
---

# Reflexive Primitive Promotion Packet

## Scoped Claim

ZTARE can take one repeated operations-intelligence failure class and represent
it as a typed promotion candidate rather than leaving it as an advisory note.

The current bounded example is agentic/autoresearch route accounting:
out-of-loop workbench route rows are missing, sparse, bypassed without reason,
or blocked by missing workbench surfaces. The system now emits a
`ztare_learning_promotion_contract` with:

- nearest existing surface;
- nearest confuser;
- typed carrier name;
- required carrier fields;
- deterministic validator;
- action-intelligence compatibility statement;
- ex-post usage criterion;
- non-claim;
- kill criterion.

Valid route-accounting promotion contracts are also attached back to the
`action_intelligence` source-readiness row, so the source gap has a typed repair
carrier rather than only a prose recommendation.

The carrier keeps worker transport and branch state inspectable through the
existing OP-AWR fields: `worker_metadata`, `route_json_ref`,
`action_impact_ref`, and `workbench_evidence_ref`. The last field is the
run/projection artifact reference used to inspect branch status and admitted or
pruned work without treating the route row as truth evidence.

The route-row source boundary also validates the router JSON before it becomes
an action-intelligence row: missing prerequisite booleans, non-boolean fields,
and inconsistent `invoke_autoresearch` / `prepare_autoresearch_surface` /
`stay_out_of_loop` decisions fail at record time.

The same promotion-contract path also handles a second repeated failure family:
forecast decision-use gaps. Primitive amnesia surfaces the existing prediction
logging discriminator and prediction-ledger pattern, so sparse decision-use
rows are now closed as `close_as_source_repair_not_primitive` with the typed
carrier `forecast_decision_use_source_repair`. That decision keeps the gap
visible in source readiness without pretending it is a new primitive.

Primitive-amnesia miss-queue reviews now have a downstream action-intelligence
consumer as well. Open `primitive-amnesia-promotion-review-v1` rows surface as
diagnostic `trajectory_surfacing` recommendations with the
`primitive_promotion_review` surface kind. If a review is consumed or
suppressed, the same surfacing-event path writes an action-impact row. This
does not promote a primitive; it records whether the review changed a repair
decision, opened a non-promotion review, or was suppressed as low value.

## Evidence Level

L1: deterministic unit evidence over fixed fixtures.

This is a carrier/contract claim, not a production-uplift claim.

## Primary Sources

- Implementation:
  [`learning_promotion_contract.py`](../../../src/ztare/research_director/learning_promotion_contract.py)
- Read-model wiring:
  [`operations_intelligence.py`](../../../src/ztare/reports/operations_intelligence.py)
- Source-contract preflight:
  [`action_intelligence.py`](../../../scripts/public/control/action_intelligence.py)
- Primitive-amnesia review classifier:
  [`primitive_amnesia.py`](../../../src/ztare/research_director/primitive_amnesia.py)
- Tests:
  [`test_operations_intelligence.py`](../../../tests/reports/test_operations_intelligence.py)
  and [`test_action_intelligence.py`](../../../tests/scripts/test_action_intelligence.py)
- Existing move-card surface:
  [`primitive_operator_cards.py`](../../../src/ztare/research_director/primitive_operator_cards.py)

## Runnable Anchor

```bash
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/reports/test_operations_intelligence.py tests/test_pattern_action_contract.py tests/test_hypothesis_projection.py -q
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/scripts/test_action_intelligence.py -q
PYTHONPATH=src:. ./venv/bin/python -m pytest tests/research_director/test_primitive_amnesia_atlas_status.py -q
PYTHONPATH=src:. ./venv/bin/python -m ztare.research_director.primitive_amnesia "promote sparse forecast decision-use logging into a reusable primitive or action-intelligence carrier with deterministic validation"
```

Expected output:

```text
All pytest commands pass.
Relevant extracted primitives ... PREDICTION-LOGGING-DISCRIMINATOR ...
```

## Evidence Summary

The fixture verifies that an agentic workbench candidate with missing route
surface evidence becomes a `promote_to_typed_carrier_candidate` and carries the
`agentic_workbench_route_accounting` typed carrier.

The carrier fixture also checks that worker metadata and workbench evidence
references remain required, so route decisions can be tied back to transport and
branch-state artifacts.

It also verifies the confuser boundary: generic source-health repair candidates
remain `review_only` and do not become promoted primitive candidates.

The operations-intelligence fixture additionally checks that valid promotion
contracts are counted under the `action_intelligence` source-readiness row.
It also checks that forecast decision-use gaps become valid non-promotion
contracts counted under the `gp230_forecast_pool` source-readiness row.

The action-intelligence fixture checks that malformed router JSON fails before
row construction, including missing prerequisite fields and an
`invoke_autoresearch` decision whose artifact surface is absent.

It also checks the primitive-amnesia bridge: an unresolved benchmark target in
the miss queue surfaces as a diagnostic
`surface_primitive_promotion_review` recommendation, and a consumed
`primitive_promotion_review` surfacing event becomes an action-impact row with
the review payload ref, typed carrier, and promotion decision preserved.

## Non-Claims

- No claim that autoresearch output quality improved.
- No claim that agent workers outperform API or subscription workers.
- No claim that the promotion contract is already an authoritative gate.
- No claim that all recursive-improvement candidates are now handled.
- No claim that sparse forecast decision-use rows deserve a new primitive.
- No claim that primitive-amnesia miss rows are promoted automatically.

## Next Falsifier

A later operations-intelligence refresh should show whether the promoted carrier
or primitive-review recommendation was consumed downstream: route/action rows
with source references should resolve the candidate, or the candidate should be
closed as a non-promotion with a durable reason. If candidates keep appearing
without route rows, consumed primitive-review rows, or ex-post usage, this
remains observer-only machinery rather than recursive improvement.

## Missing Upgrade

The next upgrade is a resolved follow-through row: an operations-intelligence
refresh where the route-accounting candidate disappears because route/action
rows exist, or the decision-use gap shrinks because forecast rows are bound to
pre-outcome decisions. Until then, this is bounded contract machinery.
