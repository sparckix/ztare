# Joint-affordance synthetic-target search

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-JOINT-AFFORDANCE-SEARCH-20260726-31`  
Status: preregistered

## Eigenquestion

Can the existing general factored-search consumer compose the evidence-derived
target position with the H30-selected configuration and recover a model route,
or is the current predictive carrier still expressed in coordinates that
cannot transport this relation?

## Hypothesis

The accepted compiled-fiber projection and common `search_factored` kernel can
search for the synthetic terminal key

```text
(H29 target controlled base, H30 selected finite configuration, H29 operation)
```

without adding a substrate rule. The same search must first recover the
observed H29 non-discharging target as a positive control. It will then return
an edge-bearing route to the selected joint-affordance target within the fixed
offline bounds.

## Fixed inputs and lowering

- start observation and time:
  `raw/episodes/eval_slices/eval_20260725T192020752309Z.jsonl#0`, time `64`;
- observed target source: the representative bound by
  `active_affordance_frontier_audit_result.json`;
- selected configuration partition:
  `4dd96788ba556af49abb6b84a143ff58f4e933b8c8c331159017b9c91d77a000`,
  with raw values taken from its admitted H30 evidence witnesses;
- terminal intervention: the operation bound by H29;
- target factors: copy the observed target factors and replace only
  `finite_configuration` with an admitted selected-configuration witness;
- search: existing `CompiledFiberSearchProblem` and `search_factored`, four
  interventions, start time from the trace, depth at most 180, at most 20,000
  generated states;
- prediction: the current accepted carrier, unchanged.

If the selected partition has multiple raw renderings, run the same search for
every distinct raw rendering; no support-based cherry-picking.

## Discriminating test

1. Search the exact observed H29 target key and operation. Require
   `edge_found`; this calibrates the consumer against a route already present
   in the evidence graph.
2. Search every raw configuration rendering in the H30-selected partition
   after composing it with the same target base and operation.
3. Replay each returned route only through the carrier. On the pre-terminal
   predicted state, recompute the shared-D4 joint code and exact terminal
   factors.
4. Report generated/expanded counts, projection counterexamples, raw
   configuration identities, action route, and all source evidence.

## Success criterion

- the observed-target positive control returns `edge_found`;
- at least one and every equivalent raw selected-configuration target returns
  `edge_found` without a projection counterexample;
- replay reaches the target controlled base and selected configuration;
- the final edge recomputes H30 joint code `c1968343…`;
- the route differs from the known non-discharging target route before its
  terminal edge.

## Kill conditions

Reject the hypothesis if the positive control fails, the selected
configuration has no raw witness, a raw-witness variant disagrees, search
exhausts either bound, the projection fails to commute, replay misses the
target factors or joint code, the route collapses to the known-negative route,
or any action is sent to the environment.

## Claim boundary

A pass yields an offline carrier route proposal. It does not establish that
the carrier predicts every concrete image correctly, authorize execution, or
establish task completion. A failure localizes the next repair to predictive
transport or consumer coordinates rather than target identification.
