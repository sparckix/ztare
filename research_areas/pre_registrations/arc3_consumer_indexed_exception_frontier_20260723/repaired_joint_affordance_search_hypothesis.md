# Repaired joint-affordance search

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-REPAIRED-JOINT-AFFORDANCE-SEARCH-20260726-35`  
Status: preregistered

## Eigenquestion

After restoring recoverable mechanism states, can the general target consumer
compose the H30-selected orientation with the evidence-derived destination?

## Hypothesis

The repaired `CompiledFiberSearchProblem` will recover both the observed H29
positive control and the H30 selected target within the original H31 bounds.
The selected route's pre-terminal state will recompute joint code
`c1968343…`.

## Fixed test

- rerun the H31 audit unchanged except for consuming the repaired core class;
- same trace/start time, carrier, target base, operation, single admitted raw
  selected configuration, depth 180, state cap 20,000, and four interventions;
- require the observed target first;
- replay selected routes through the carrier and recompute target factors,
  budget, and shared-D4 joint code;
- no environment contact and no further search override.

## Success criterion

- positive control and selected target both return `edge_found`;
- no projection counterexample;
- selected replay reaches configuration `4dd96788…`, target controlled base,
  and joint code `c1968343…`;
- selected route differs from the known non-discharge route.

## Kill conditions

Reject on calibration regression, exhaustion, noncommutation, factor/joint-code
mismatch, route collapse, additional consumer alteration, or environment
contact.

## Claim boundary

A pass yields a calibrated offline route proposal to the selected joint
affordance. It does not authorize execution or establish external completion.
