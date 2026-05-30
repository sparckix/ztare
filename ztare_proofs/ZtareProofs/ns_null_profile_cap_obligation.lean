import Mathlib.Tactic
import ZtareProofs.ns_pricing_kernel_limit_passage

/-!
# Null-profile cap branch obligation (NS Track B)

This file is the Lean target for the `ns_proofsearch_null_profile_cap`
substrate. It does **not** prove Navier-Stokes regularity. It declares the
exact obligation a candidate must close to retire the null-profile cap branch
of the seven-branch Track B grid.

The branch's parent obligation is `NullProfileCapped`, defined in
`ns_pricing_kernel_limit_passage.lean`:

```
def NullProfileCapped (P : PricingProfile) : Prop :=
  P.isNull → ProfileNoArbitrage P
```

A successful substrate iteration MUST extend this file with a concrete
instantiation, named below as `null_profile_cap_concrete`, for at least one of:

* shear flows on the flat torus,
* Beltrami flows on the flat torus,
* embedded Euler steady solutions,
* a named Leray-invisible family.

The instantiation must use the `PricingProfile` declared upstream and produce
a closed proof (no `sorry`). A deterministic Python falsifier counts as a
negative-arm closure but does not extend this file.
-/

namespace ZtareProofs.NS.NullProfileCapBranch

open ZtareProofs.NS

/-- A named null class is one whose Leray-projected self-tax vanishes. The
class index records WHICH explicit class is being addressed; this is part of
the substrate's anti-tautology contract: the operator must name the class
before the cap is scored. -/
inductive NullClass where
  | shear
  | beltrami
  | embeddedEuler
  | namedLerayInvisible (slug : String)
deriving Repr

/-- Class-level cap obligation: every PricingProfile in the named class must
satisfy NullProfileCapped under the declared kernel. The substrate's positive
arm must produce a witness. -/
def NullProfileCapForClass (_cls : NullClass) (Class : PricingProfile → Prop) : Prop :=
  ∀ P, Class P → P.isNull → ProfileNoArbitrage P

/-- The structural implication: if the cap holds for one class and a profile
P is in that class and is null, then no-arbitrage holds. Trivial unfolding;
present as a sanity check on the contract. -/
theorem null_profile_cap_implication
    (_cls : NullClass)
    (Class : PricingProfile → Prop)
    (h : NullProfileCapForClass _cls Class) :
    ∀ P, Class P → NullProfileCapped P := by
  intro P hP hN
  exact h P hP hN

/-- Anti-tautology contract for the substrate. The substrate's positive arm
must supply BOTH:
  (a) a `NullClass` value plus its `Class : PricingProfile → Prop` predicate;
  (b) a proof that `NullProfileCapForClass cls Class` holds.
A `sorry` is never a substitute for either component. This struct exists so
the substrate output can be lifted into a single dependent record. -/
structure ClosedBranchPositive where
  cls : NullClass
  Class : PricingProfile → Prop
  closure : NullProfileCapForClass cls Class

/-- Anti-tautology contract for the negative arm. The substrate's negative
arm must supply a concrete `PricingProfile` plus a proof that its payoff
exceeds its price (and that it is null). This would falsify the cap predicate
for the declared kernel. -/
structure ClosedBranchNegative where
  P : PricingProfile
  isNull : P.isNull
  arbitrage : P.price < P.payoff

/-- Branch outcome envelope. The substrate must produce one or the other. -/
inductive BranchOutcome where
  | positive (closure : ClosedBranchPositive)
  | negative (counterexample : ClosedBranchNegative)

end ZtareProofs.NS.NullProfileCapBranch
