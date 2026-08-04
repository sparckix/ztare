# H97 pre-live criticality correction

**Status:** frozen before H97 controller or environment contact

The first H97 JSON spec used
`response_reproduction_number_greater_than_1` as the value of
`critical_boundary`. That label conflicts with the executable estimator and
the registered hypothesis:

- `R_response < 1`: subcritical
- `R_response = 1`: critical
- `R_response > 1`: supercritical

Revision 2 changes that label and adds the explicit supercritical boundary.
It also closes a controller-identity omission found while constructing the
live harness. H96 used a subscription controller transport; H97 uses a stored
Responses API controller. The live scope therefore remints
`controller_sha256` while preserving task, context, choice set, and action
vocabulary. The causal residual renderer and its true non-target,
byte-matched control are frozen at the same time.

The hypothesis, sample count, action budget, success criterion, kill
conditions, and claim boundary are unchanged. No H97 controller or
environment contact occurred before these corrections.
