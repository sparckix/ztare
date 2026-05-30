import Mathlib.Tactic

namespace ZtareProofs

/-
Phase 5BX records the Kida-Pelz "prison" discriminator as a conditional
dichotomy.  This file intentionally does not claim an exact Kida group
projection or a Navier-Stokes theorem.  It formalizes the proxy experiment's
decision logic so later receipts can plug in without changing the proof spine.
-/

/-- Scalar metrics emitted by the Phase 5BX Fourier-support prison proxy. -/
structure KidaPrisonMetrics where
  naturalLeak : Real
  naturalOmegaGrowthLast : Real
  naturalEnstrophyGrowthLast : Real
  prisonFinalLeak : Real
  prisonOmegaGrowthPeak : Real
  prisonOmegaGrowthLast : Real
  prisonEnstrophyGrowthLast : Real

/-- Symmetry/leakage tolerance used by the proxy classifier. -/
noncomputable def kidaLeakageTol : Real := (1 : Real) / 100000000

/-- The unconstrained arm found an available support-escape channel. -/
def NaturalEscapeAvailable (m : KidaPrisonMetrics) : Prop :=
  kidaLeakageTol < m.naturalLeak

/-- Counterexample-like behavior: growth persists inside the prison. -/
def PrisonGrowthPersists (m : KidaPrisonMetrics) : Prop :=
  (2 : Real) < m.prisonOmegaGrowthPeak ∧
    (3 : Real) / 2 < m.prisonOmegaGrowthLast

/-- Regularity-direction behavior: the prison keeps leakage closed and growth saturates. -/
def PrisonSaturates (m : KidaPrisonMetrics) : Prop :=
  m.prisonOmegaGrowthPeak ≤ (5 : Real) / 4 ∧
    m.prisonFinalLeak ≤ kidaLeakageTol

/--
Outcome C in the 5BX triage: the natural flow can use the escape channel, but
the support-prisoned flow does not compound.  This points to a second
saturation mechanism rather than a symmetry-locked blowup.
-/
def KidaOutcomeC (m : KidaPrisonMetrics) : Prop :=
  NaturalEscapeAvailable m ∧ PrisonSaturates m

/-- Outcome C excludes the counterexample-like "growth persists in prison" branch. -/
theorem kidaOutcomeC_not_prisonGrowthPersists {m : KidaPrisonMetrics}
    (h : KidaOutcomeC m) :
    ¬ PrisonGrowthPersists m := by
  intro hgrowth
  have hpeak : m.prisonOmegaGrowthPeak ≤ (5 : Real) / 4 := h.2.1
  have hgrow : (2 : Real) < m.prisonOmegaGrowthPeak := hgrowth.1
  linarith

/-- Phase 5BX N64 proxy metrics, rounded only toward the classifier margins. -/
noncomputable def phase5bxN64Proxy : KidaPrisonMetrics where
  naturalLeak := (1160942 : Real) / 10000000
  naturalOmegaGrowthLast := (8060815 : Real) / 10000000
  naturalEnstrophyGrowthLast := (10697108 : Real) / 10000000
  prisonFinalLeak := 0
  prisonOmegaGrowthPeak := 1
  prisonOmegaGrowthLast := (9995134 : Real) / 10000000
  prisonEnstrophyGrowthLast := (9990271 : Real) / 10000000

/-- The local N64 proxy receipt satisfies the Outcome C branch of the triage. -/
theorem phase5bxN64Proxy_outcomeC :
    KidaOutcomeC phase5bxN64Proxy := by
  constructor
  · norm_num [NaturalEscapeAvailable, kidaLeakageTol, phase5bxN64Proxy]
  · constructor
    · norm_num [PrisonSaturates, phase5bxN64Proxy]
    · norm_num [kidaLeakageTol, phase5bxN64Proxy]

/-- The local N64 proxy receipt does not satisfy the prison-growth branch. -/
theorem phase5bxN64Proxy_not_prisonGrowthPersists :
    ¬ PrisonGrowthPersists phase5bxN64Proxy :=
  kidaOutcomeC_not_prisonGrowthPersists phase5bxN64Proxy_outcomeC

end ZtareProofs
