import ZtareProofs.FormalSubstitutionFlow

/-!
# Proportional-flow endpoint reduction

The analytic trajectory theorem identifies the selected second endpoint with
time `c` in the first flow.  This file is the separate DAG inference: after
that identification, the substitution-flow law reduces either displayed
composition orientation to time one of the `(1+c)` reparameterized flow.
-/

namespace FormalProportionalFlowReduction

open PowerSeries
open FormalSubstitutionFlow

variable {k : Type*} [Field k]

/-- Once two endpoint series have been identified with times `1` and `c` in
one substitution flow, their displayed composition is a single reparameterized
time-one endpoint. -/
theorem identified_endpoints_reduce_to_reparameterized_time_one
    (flow : SubstitutionFlow k) (c : k)
    (firstEndpoint secondEndpoint : k⟦X⟧)
    (hfirst : firstEndpoint = flow.endpoint 1)
    (hsecond : secondEndpoint = flow.endpoint c) :
    firstEndpoint.subst secondEndpoint =
      (flow.reparam (1 + c)).endpoint 1 := by
  rw [hfirst, hsecond]
  exact proportional_composition_as_reparameterized_time_one flow c

/-- The opposite composition orientation has the same one-flow reduction. -/
theorem identified_endpoints_reduce_to_reparameterized_time_one_rev
    (flow : SubstitutionFlow k) (c : k)
    (firstEndpoint secondEndpoint : k⟦X⟧)
    (hfirst : firstEndpoint = flow.endpoint 1)
    (hsecond : secondEndpoint = flow.endpoint c) :
    secondEndpoint.subst firstEndpoint =
      (flow.reparam (1 + c)).endpoint 1 := by
  rw [hfirst, hsecond]
  exact proportional_composition_as_reparameterized_time_one_rev flow c

/-- Aggregated inference certificate used by formal-coverage DAGs.  The
endpoint-identification equalities remain visible as premises because they
belong to the preceding analytic trajectory leaf. -/
theorem proportional_flow_reduction_terminal_certificate :
    (∀ (flow : SubstitutionFlow k) (c : k)
      (firstEndpoint secondEndpoint : k⟦X⟧),
      firstEndpoint = flow.endpoint 1 →
      secondEndpoint = flow.endpoint c →
      firstEndpoint.subst secondEndpoint =
        (flow.reparam (1 + c)).endpoint 1) ∧
    (∀ (flow : SubstitutionFlow k) (c : k)
      (firstEndpoint secondEndpoint : k⟦X⟧),
      firstEndpoint = flow.endpoint 1 →
      secondEndpoint = flow.endpoint c →
      secondEndpoint.subst firstEndpoint =
        (flow.reparam (1 + c)).endpoint 1) := by
  exact ⟨identified_endpoints_reduce_to_reparameterized_time_one,
    identified_endpoints_reduce_to_reparameterized_time_one_rev⟩

end FormalProportionalFlowReduction
