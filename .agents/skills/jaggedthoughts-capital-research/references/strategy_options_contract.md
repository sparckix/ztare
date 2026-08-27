# Company strategy option profile

Write YAML with schema `jaggedthoughts-company-strategy-options-v1`. Effects are normalized directional scores; larger is preferred. Every numeric effect and industry claim needs an evidence reference.

Required shape:

```yaml
schema: jaggedthoughts-company-strategy-options-v1
evidence_epoch: 2026-08-09T00:00:00Z
company: {id: TICKER, name: Company Name}
industry_state:
  boundary: The chosen economic arena.
  customer_need: The need that defines the arena.
  evidence_refs: [source-id]
  pressures:
  - id: buyer_power
    actor_kind: customer
    description: Evidence-bound mechanism.
    evidence_refs: [source-id]
scenarios:
- id: base
  base: [0.0, 0.0, 0.0, 0.0]
  evidence_refs: [source-id]
options:
- id: response_id
  kind: positioning
  mechanism:
    action: focus_resources
    economic_bridge: growth
    object_id: named_company_capability
    implementation_conditions: [condition_that_must_hold]
    break_conditions: [observable_condition_that_breaks_the_analogy]
    evidence_refs: [source-id]
  implementation_event:
    id: dated-adoption-id
    event_kind: adoption
    implementation_mode: organic_program
    status_after: underway
    occurred_at: 2026-06-01T00:00:00Z
    available_at: 2026-06-02T00:00:00Z
    timing_precision: date
    source_refs: [source-id]
  description: Committed response with a named tradeoff.
  addresses: [buyer_power]
  incompatible_with: []
  claim: Falsifiable capability or response claim.
  claim_status: supported
  evidence_refs: [source-id]
  outcome_contracts:
  - id: response-quarter-test
    metric_id: operating_margin_q
    unit: ratio
    direction: increase
    minimum_effect: 0.005
    horizon_days: 120
    measurement_start_at: 2026-08-09T00:00:00Z
    comparator: pre_move_baseline
    outcome_role: leading_operating
    acquisition_mode: point_in_time_observation
    evidence_refs: [source-id]
  - id: response-margin-test
    metric_id: disclosed_segment_operating_margin
    unit: ratio
    direction: increase
    minimum_effect: 0.01
    horizon_days: 730
    measurement_start_at: 2026-08-09T00:00:00Z
    comparator: pre_move_baseline
    outcome_role: terminal_operating
    acquisition_mode: subscription_primary_document
    evidence_refs: [source-id]
  scenario_effects:
    base: [0.1, 0.1, -0.1, 0.1]
interactions:
- id: reinforcing_pair
  option_ids: [response_id, second_response]
  evidence_refs: [source-id]
  scenario_effects:
    base: [0.1, 0.0, 0.1, 0.1]
contingent_policies:
- id: commit_then_choose_response
  frozen_at: 2026-08-09T00:00:00Z
  commit_option_ids: [response_id]
  commit_not_before: 2026-08-09T00:00:00Z
  recourse_not_before: 2026-11-09T00:00:00Z
  conditions:
  - id: public_metric_clears_hurdle
    coordinate: exact_public_metric_id
    operator: ge
    value: 0.1
    unit: decimal share
    threshold_basis: source_disclosed
    threshold_rationale: The cited source declares this operating threshold.
    evidence_refs: [source-id]
  policy:
    condition_id: public_metric_clears_hurdle
    if_true: {option_ids: [response_id, second_response]}
    if_false: {option_ids: [response_id, fallback_response]}
representation:
  id: TICKER-representation
  status: residual
  residuals: [Material omissions or unresolved boundary choices.]
```

The four authored coordinates are, in order: earnings durability, growth, capital efficiency, and downside resilience. The compiler adds industry-pressure coverage as a fifth objective. Use `unresolved` when evidence does not support an option-effect claim and `refuted` when evidence rejects it. Name incompatibilities explicitly. Keep `status: residual` unless a separate representation audit supports `passed`.

When the frozen frontier request carries a strategy-event assessment, lower it to
at most one option's `implementation_event` only when the event clock and assessment
source ids match exactly. Otherwise put
`strategy_event_unmapped:<move_observation_sha256>` in `representation.residuals`.
Do not silently omit the event. The request may also carry content-addressed
operating and return forecast lineage for later scoring; those predictions and later
settlements are unavailable for authoring scenario effects.

`contingent_policies` is optional. It is the company-level two-stage lowering:
commit one already-feasible option bundle, observe public numeric conditions,
then select among already-feasible final bundles without reversing the
commitment. Every condition operator is one of `eq`, `ne`, `gt`, `ge`, `lt`,
or `le`. Every threshold needs its exact public metric unit, a rationale, and a basis:
`source_disclosed`, explicitly labelled `analyst_hypothesis`, or
`reference_fixture` for fictional examples only. A subscription-authored
profile may use only the first two. Recourse must occur after commitment, at
least two final bundles must differ, and all leaves must retain the committed
options. Z3 certifies declared bundle feasibility, trigger coverage, overlap,
and reachability; it does not validate the metric, threshold, effect, or
profitability. Omit the policy when its public metric, clock, source, or leaf is
missing.

`mechanism.action` uses the kernel vocabulary `commit_capacity`,
`diversify_scope`, `expand_adjacent_scope`, `focus_resources`,
`integrate_value_chain`, `secure_access`, or `secure_supply`.
`economic_bridge` is one of the first four authored coordinates. The action and
bridge define a move-family question; object, environment, implementation
conditions, and break conditions remain exact company context. Do not force an
option into this vocabulary when none fits; leave the mechanism absent and
record the taxonomy gap.

`implementation_event` is optional because an enumerated option is not
necessarily an executed move. Add it only for a dated public event. Its
`event_kind` is `adoption`, `announcement`, `first_public_observation`,
`completion`, or `discontinuation`; `status_after` is `planned`, `underway`,
`completed`, or `discontinued`. `implementation_mode` is `acquisition`,
`capacity_build`, `divestiture`, `organic_program`, `partnership`,
`resource_reallocation`, `supply_commitment`, or `other`. An exact dated adoption may seed a treated
panel. A first public observation is retained as interval-censored adoption
timing; it must not be relabelled as the execution date. Announcement,
completion, and discontinuation do not establish adoption timing.

Exact adoptions activate the comparable-peer acquisition path. The kernel
selects same-industry, market-cap-neighbour peers and freezes one search request
per mechanism phenotype × peer. Run `workspace hydrate-strategy-cohort` to
acquire their SEC histories. The subscription agent must distinguish
`phenotype_adoption_found`, `family_adoption_only`,
`no_family_adoption_found`, and `insufficient_source_coverage`. Family-only
treatment is excluded from the focal phenotype panel and cannot serve as a
control. A negative result requires both source classes and means provisional
not-yet-treated under the frozen search window, never proof of no treatment.
`workspace institutional-learning` then derives filing-bounded durable-earnings
histories into a diagnostic causal panel.

`outcome_contracts` are optional and independent. Add up to three only when later
public evidence can measure each named business result. `outcome_role` is
`leading_operating` or `terminal_operating`; an early rung may challenge a move
but cannot settle its terminal earnings hurdle or security return. Legacy rows
without a role are terminal. `acquisition_mode` is `point_in_time_observation`
for a typed public metric already handled by the source engine or
`subscription_primary_document` when a later filing needs bounded retrieval.
The target date must be after the frontier evidence epoch. `comparator` is one of
`pre_move_baseline`, `matched_peer`, or `industry_baseline`. A before/after
contract is descriptive; matched and industry comparators still require the
causal-learning lane to validate the comparison. The contract never uses stock
return as the operating metric and never grants paper or capital authority.
Anchor `measurement_start_at` to the move's source-observed implementation
window when one exists, not to the later date on which the analyst compiled the
frontier.

At or after `due_at`, submit a JSON object with schema
`jaggedthoughts-strategy-move-outcome-v1`, the exact `move_sha256` and
`contract_sha256` from the compiled library, `observed_at`, `available_at`,
`unit`, baseline and outcome values, and source refs. Matched-peer or industry
contracts also require comparator baseline and outcome values. Run:

`PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace --path <workspace> strategy-outcome <workspace-relative-json>`
