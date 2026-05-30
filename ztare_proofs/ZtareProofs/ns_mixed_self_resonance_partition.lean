import Mathlib.Tactic

/-!
# Mixed/self resonance partition

The high-high anti-alignment guard shows that a dangerous survivor needs a
large negative mixed/self cross term.  In Fourier space that cross term can
only be nonzero on output modes shared by the mixed residual and the self
residual.

This file pays the finite-support algebraic partition: if the low-high mixed
output support `high + low` is disjoint from the high-high self output support
`high + high`, then the mixed/self cross sum is exactly zero.  Therefore
negative anti-alignment can only live in the additive-resonant branch

    h + l = h₁ + h₂.

The remaining PDE work is to charge that resonant branch or prove it is
harmless under the declared LP/Bony topology.
-/

namespace ZtareProofs.NS

/-- Modewise real cross contribution: Fourier inner products only pair equal
output modes. -/
def modePairCross {α : Type} [DecidableEq α]
    (mixed self : α → Real) (k l : α) : Real :=
  if k = l then mixed k * self l else 0

/-- Cross sum for one mixed output mode against a self support. -/
def supportCrossOne {α : Type} [DecidableEq α] :
    α → List α → (α → Real) → (α → Real) → Real
  | _k, [], _mixed, _self => 0
  | k, l :: ls, mixed, self =>
      modePairCross mixed self k l + supportCrossOne k ls mixed self

/-- Finite support cross sum between mixed and self residual supports. -/
def supportCrossSum {α : Type} [DecidableEq α] :
    List α → List α → (α → Real) → (α → Real) → Real
  | [], _selfSupport, _mixed, _self => 0
  | k :: ks, selfSupport, mixed, self =>
      supportCrossOne k selfSupport mixed self +
        supportCrossSum ks selfSupport mixed self

/-- A single output mode has zero cross against a disjoint self support. -/
theorem supportCrossOne_zero_of_disjoint
    {α : Type} [DecidableEq α]
    (k : α) (selfSupport : List α)
    (mixed self : α → Real)
    (hdisjoint : ∀ l ∈ selfSupport, k ≠ l) :
    supportCrossOne k selfSupport mixed self = 0 := by
  induction selfSupport with
  | nil =>
      simp [supportCrossOne]
  | cons l ls ih =>
      have hkl : k ≠ l := hdisjoint l (by simp)
      have hrest : supportCrossOne k ls mixed self = 0 := by
        exact ih (by
          intro l' hl'
          exact hdisjoint l' (by simp [hl']))
      simp [supportCrossOne, modePairCross, hkl, hrest]

/-- If the two output supports are disjoint, the mixed/self cross sum vanishes. -/
theorem supportCrossSum_zero_of_disjoint
    {α : Type} [DecidableEq α]
    (mixedSupport selfSupport : List α)
    (mixed self : α → Real)
    (hdisjoint :
      ∀ k ∈ mixedSupport, ∀ l ∈ selfSupport, k ≠ l) :
    supportCrossSum mixedSupport selfSupport mixed self = 0 := by
  induction mixedSupport with
  | nil =>
      simp [supportCrossSum]
  | cons k ks ih =>
      have hkzero :
          supportCrossOne k selfSupport mixed self = 0 := by
        exact supportCrossOne_zero_of_disjoint k selfSupport mixed self
          (by
            intro l hl
            exact hdisjoint k (by simp) l hl)
      have hks :
          supportCrossSum ks selfSupport mixed self = 0 := by
        exact ih (by
          intro k' hk' l hl
          exact hdisjoint k' (by simp [hk']) l hl)
      simp [supportCrossSum, hkzero, hks]

/-- Pairwise sum support `A+B`. -/
def pairSumSupport {α : Type} [Add α] : List α → List α → List α
  | [], _B => []
  | a :: as, B => B.map (fun b => a + b) ++ pairSumSupport as B

lemma mem_pairSumSupport_iff
    {α : Type} [Add α]
    (A B : List α) (x : α) :
    x ∈ pairSumSupport A B ↔
      ∃ a ∈ A, ∃ b ∈ B, a + b = x := by
  induction A with
  | nil =>
      simp [pairSumSupport]
  | cons a as ih =>
      simp [pairSumSupport, ih]

/-- No additive resonance between mixed low-high outputs and self high-high
outputs. -/
def NoMixedSelfResonance {α : Type} [Add α]
    (high low : List α) : Prop :=
  ∀ h ∈ high, ∀ l ∈ low, ∀ h₁ ∈ high, ∀ h₂ ∈ high,
    h + l ≠ h₁ + h₂

/-- No additive resonance means the mixed output support and self output support
are disjoint. -/
theorem pair_sum_supports_disjoint_of_no_resonance
    {α : Type} [Add α]
    (high low : List α)
    (hno : NoMixedSelfResonance high low) :
    ∀ k ∈ pairSumSupport high low,
      ∀ s ∈ pairSumSupport high high, k ≠ s := by
  intro k hk s hs
  rcases (mem_pairSumSupport_iff high low k).1 hk with
    ⟨h, hh, l, hl, hkl⟩
  rcases (mem_pairSumSupport_iff high high s).1 hs with
    ⟨h₁, hh₁, h₂, hh₂, hs12⟩
  intro heq
  exact hno h hh l hl h₁ hh₁ h₂ hh₂ (by
    calc
      h + l = k := hkl
      _ = s := heq
      _ = h₁ + h₂ := hs12.symm)

/-- Finite support theorem for the high-high cross branch: absent additive
resonance, the mixed/self cross term is exactly zero. -/
theorem mixed_self_cross_zero_of_no_resonance
    {α : Type} [Add α] [DecidableEq α]
    (high low : List α)
    (mixed self : α → Real)
    (hno : NoMixedSelfResonance high low) :
    supportCrossSum
        (pairSumSupport high low)
        (pairSumSupport high high)
        mixed self = 0 := by
  exact supportCrossSum_zero_of_disjoint
    (pairSumSupport high low)
    (pairSumSupport high high)
    mixed self
    (pair_sum_supports_disjoint_of_no_resonance high low hno)

/-- Minimal resonant support used as an anti-tautology guard. -/
def resonantToyHigh : List Int := [1]

def resonantToyLow : List Int := [1]

def resonantToyMixed (k : Int) : Real :=
  if k = 2 then 1 else 0

def resonantToySelf (k : Int) : Real :=
  if k = 2 then -1 else 0

/-- The toy support has the additive resonance `1 + 1 = 1 + 1`, so it is not
covered by the nonresonant cross-zero theorem. -/
theorem resonantToy_not_no_resonance :
    ¬ NoMixedSelfResonance resonantToyHigh resonantToyLow := by
  intro hno
  have hbad := hno 1 (by simp [resonantToyHigh]) 1 (by simp [resonantToyLow])
    1 (by simp [resonantToyHigh]) 1 (by simp [resonantToyHigh])
  exact hbad (by norm_num)

/-- In a resonant support, negative mixed/self cross is possible.  This keeps
the partition honest: the nonresonant theorem only removes the cross-zero
branch; the resonant branch still needs the anti-alignment/root-coercivity
estimate. -/
theorem resonantToy_cross_negative :
    supportCrossSum
        (pairSumSupport resonantToyHigh resonantToyLow)
        (pairSumSupport resonantToyHigh resonantToyHigh)
        resonantToyMixed resonantToySelf = -1 := by
  norm_num [
    supportCrossSum,
    supportCrossOne,
    modePairCross,
    pairSumSupport,
    resonantToyHigh,
    resonantToyLow,
    resonantToyMixed,
    resonantToySelf,
  ]

end ZtareProofs.NS
