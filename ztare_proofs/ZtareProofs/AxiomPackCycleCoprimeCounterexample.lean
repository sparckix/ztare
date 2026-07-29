import Mathlib

/-!
# A 49-point coprime-cycle counterexample certificate

This file checks the first admissible instance of Cedó--Okniński,
`Simple solutions of the Yang--Baxter equation of cardinality p^n`,
Theorem 4.2 (arXiv:2407.07907), in cycle-set coordinates.

Their YBE action is `sigma`.  The cycle-set left translation is `sigma⁻¹`,
which has the same cycle lengths.  For `p = 7`, `n = 1`, `q = 3`, and
`t(c) = 2c`, the checked operation below has bijective left translations,
satisfies the cycle-set law, is transitive under two left translations, and
contains a 3-cycle although its carrier has cardinality 49.
-/

namespace ZtareProofs.AxiomPackCycleCoprimeCounterexample

abbrev X := Fin 7 × Fin 7

def j : Fin 7 → Fin 7 := ![1, 0, 6, 4, 4, 6, 0]

/-- The inverse of the paper's `sigma_(a,b)` action. -/
def leftTranslation (source target : X) : X :=
  (4 * (target.1 - source.2), 4 * target.2 + j (target.1 - source.1))

/-- The paper's `sigma_(a,b)` action, included to certify bijectivity. -/
def sigma (source target : X) : X :=
  let first := 2 * target.1 + source.2
  (first, 2 * (target.2 - j (first - source.1)))

theorem sigma_leftTranslation_inverse :
    ∀ source target : X,
      sigma source (leftTranslation source target) = target := by
  decide

theorem leftTranslation_sigma_inverse :
    ∀ source target : X,
      leftTranslation source (sigma source target) = target := by
  decide

theorem leftTranslation_bijective (source : X) :
    Function.Bijective (leftTranslation source) := by
  constructor
  · intro first second equalImages
    have mapped := congrArg (sigma source) equalImages
    simpa only [sigma_leftTranslation_inverse] using mapped
  · intro target
    exact ⟨sigma source target, leftTranslation_sigma_inverse source target⟩

set_option maxRecDepth 100000 in
set_option maxHeartbeats 2000000 in
-- Exhaustive kernel reduction checks all 49^3 instances of the cycle-set law.
/-- Rump's cycle-set identity. -/
theorem cycleSetLaw :
    ∀ x y z : X,
      leftTranslation (leftTranslation x y) (leftTranslation x z) =
        leftTranslation (leftTranslation y x) (leftTranslation y z) := by
  decide

/-- Nondegeneracy of the finite cycle set in the diagonal-map convention. -/
def squaringMap (x : X) : X := leftTranslation x x

theorem squaringMap_bijective : Function.Bijective squaringMap := by
  decide

/- The following lookup functions provide a uniform two-step transitivity
certificate.  For `delta = target.2 - 2 * start.2`, `firstJ delta` and
`secondJ delta` solve `4 * firstJ + secondJ = delta` in `Fin 7`.
-/

def firstJ : Fin 7 → Fin 7 := ![0, 0, 4, 1, 0, 1, 0]

def secondJ : Fin 7 → Fin 7 := ![0, 1, 0, 6, 4, 1, 6]

/-- A chosen argument at which `j` takes the requested value. -/
def argumentForJ : Fin 7 → Fin 7 := ![1, 0, 0, 0, 3, 0, 2]

def transitivityDelta (start target : X) : Fin 7 :=
  target.2 - 2 * start.2

def firstSource (start target : X) : X :=
  let delta := transitivityDelta start target
  (start.1 - argumentForJ (firstJ delta), start.1)

def secondSource (start target : X) : X :=
  let delta := transitivityDelta start target
  (-argumentForJ (secondJ delta), -2 * target.1)

theorem twoStepTransitivityFormula :
    ∀ start target : X,
      leftTranslation (secondSource start target)
          (leftTranslation (firstSource start target) start) = target := by
  decide

/-- A stronger, explicit witness than ordinary generated-action transitivity. -/
theorem leftTranslationAction_transitive (start target : X) :
    ∃ first second : X,
      leftTranslation second (leftTranslation first start) = target :=
  ⟨firstSource start target, secondSource start target,
    twoStepTransitivityFormula start target⟩

def point00 : X := (0, 0)
def point01 : X := (0, 1)
def point05 : X := (0, 5)

theorem explicitThreeCycle :
    leftTranslation point00 point00 = point01 ∧
    leftTranslation point00 point01 = point05 ∧
    leftTranslation point00 point05 = point00 := by
  decide

theorem explicitThreeCycle_nontrivial :
    point00 ≠ point01 ∧ point01 ≠ point05 ∧ point05 ≠ point00 := by
  decide

theorem carrierCardinality : Fintype.card X = 49 := by
  decide

theorem three_coprime_to_carrier : Nat.Coprime 3 (Fintype.card X) := by
  decide

/--
The complete finite certificate needed for the Question-30 counterexample:
cycle-set axioms, generated-action transitivity, and a nontrivial cycle whose
length is coprime to the carrier cardinality.
-/
theorem question30CounterexampleCertificate :
    (∀ source : X, Function.Bijective (leftTranslation source)) ∧
    Function.Bijective squaringMap ∧
    (∀ x y z : X,
      leftTranslation (leftTranslation x y) (leftTranslation x z) =
        leftTranslation (leftTranslation y x) (leftTranslation y z)) ∧
    (∀ start target : X, ∃ first second : X,
      leftTranslation second (leftTranslation first start) = target) ∧
    (leftTranslation point00 point00 = point01 ∧
      leftTranslation point00 point01 = point05 ∧
      leftTranslation point00 point05 = point00) ∧
    (point00 ≠ point01 ∧ point01 ≠ point05 ∧ point05 ≠ point00) ∧
    Nat.Coprime 3 (Fintype.card X) := by
  exact ⟨leftTranslation_bijective, squaringMap_bijective, cycleSetLaw,
    leftTranslationAction_transitive, explicitThreeCycle,
    explicitThreeCycle_nontrivial, three_coprime_to_carrier⟩

end ZtareProofs.AxiomPackCycleCoprimeCounterexample
