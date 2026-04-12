# Project Charter

## Core Question

What is the most defensible estimate of `P(material_union_failure by 2035-01-01)` under current institutions, and what complementary probability does that imply for continued formal intactness, given explicit event definitions, scenario boundaries, and a stated modeling basis?

## Out Of Scope

- treating the directional forecast DAG from `eu_union_load_bearing_pillars` as a point probability for this project
- emitting a naked `%` without an explicit event ontology, horizon, and model basis
- mixing multiple horizons into one answer
- collapsing `fragile_but_intact` and `durable_equilibrium` into a single "safe" state without saying that the binary event here is only `material_union_failure` vs `formal_intactness`
- claiming certainty or inevitability rather than calibrated probability or bounded range

## End States

### Success

The project cleanly distinguishes:

- `material_union_failure_by_2035`
- `formal_intactness_through_2035`

and provides:

- an explicit event definition for failure
- a justified point estimate or bounded probability range
- a transparent modeling basis for the estimate

### Failure

The project has failed if it drifts into any of the following:

- a directional tilt presented as if it were a calibrated percentage
- a probability claim with no explicit event boundary
- a probability claim with no stated modeling basis or reference class
- a broad EU durability essay rather than a bounded probabilistic forecast object

## Forecast Type

- probabilistic_forecast

## Inheritance

- ../eu_union_load_bearing_pillars/README.md
- ../eu_union_load_bearing_pillars/Report.teaching_note.md
- ../eu_union_load_bearing_pillars/evidence.txt
- ../eu_union_load_bearing_pillars/verified_axioms.json

## Anchor Proxies

- define_failure_event_boundary
- estimate_failure_probability_by_2035
- estimate_formal_intactness_probability_by_2035
- test_probability_target_is_explicit
- test_event_boundary_is_horizon_bounded
- test_failure_and_intactness_are_complements
- test_probability_changes_when_crisis_inputs_change
- test_probability_model_is_not_just_directional_tilt_relabeling
