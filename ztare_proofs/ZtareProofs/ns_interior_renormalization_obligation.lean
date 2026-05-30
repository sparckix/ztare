import Mathlib.Tactic

namespace ZtareProofs

/-!
Phase 5CG moved the old-branch proof target from raw pointwise peak data to an
interior renormalization obligation.

The empirical result is deliberately narrow:

* full-patch Leray gauges are boundary-coupled;
* strict threshold cores are dx-limited at N384;
* the only live proof-facing object is a boundary-trimmed interior gauge.

This file does not prove a Navier-Stokes theorem.  It names the minimal
dichotomy needed before the old branch can be treated as physics rather than
instrument response.
-/

/-- One sampled local patch after choosing a center and rescaling gauge. -/
structure InteriorRenormSample where
  time : Real
  omegaMax : Real
  interiorScale : Real
  boundaryMass : Real
  profileDrift : Real
  radialDrift : Real
  angularDrift : Real

/-- The scalar Leray invariant used by the Phase 5CG backtest. -/
noncomputable def InteriorRenormSample.scalarInvariant
    (s : InteriorRenormSample) : Real :=
  s.omegaMax * s.interiorScale ^ 2

/-- A finite sampled sequence of interior-renormalized patches. -/
def InteriorRenormSeq := Nat → InteriorRenormSample

/-- The scalar invariant stays within a multiplicative band along a finite window. -/
def scalarInvariantStable
    (S : InteriorRenormSeq) (n0 n1 : Nat) (δ : Real) : Prop :=
  ∀ i j : Nat, n0 ≤ i → i ≤ n1 → n0 ≤ j → j ≤ n1 →
    |(S i).scalarInvariant - (S j).scalarInvariant| ≤
      δ * |(S i).scalarInvariant|

/-- Boundary contamination is uniformly below a declared cutoff on the window. -/
def boundaryControlled
    (S : InteriorRenormSeq) (n0 n1 : Nat) (ε : Real) : Prop :=
  ∀ i : Nat, n0 ≤ i → i ≤ n1 → (S i).boundaryMass ≤ ε

/-- Adjacent rescaled profiles do not drift beyond a declared tolerance. -/
def profileCompact
    (S : InteriorRenormSeq) (n0 n1 : Nat) (η : Real) : Prop :=
  ∀ i : Nat, n0 ≤ i → i + 1 ≤ n1 → (S (i + 1)).profileDrift ≤ η

/-- The interior renormalization candidate has paid all finite-window gates. -/
def interiorRenormalizationCandidate
    (S : InteriorRenormSeq) (n0 n1 : Nat) (δ ε η : Real) : Prop :=
  scalarInvariantStable S n0 n1 δ ∧
    boundaryControlled S n0 n1 ε ∧
    profileCompact S n0 n1 η

/-- Boundary artifact branch: the scalar survives only by depending on boundary mass. -/
def boundaryArtifactCandidate
    (S : InteriorRenormSeq) (n0 n1 : Nat) (ε : Real) : Prop :=
  ∃ i : Nat, n0 ≤ i ∧ i ≤ n1 ∧ ε < (S i).boundaryMass

/-- Profile-gap branch: scalar stability survives, but adjacent profiles drift. -/
def profileGapCandidate
    (S : InteriorRenormSeq) (n0 n1 : Nat) (η : Real) : Prop :=
  ∃ i : Nat, n0 ≤ i ∧ i + 1 ≤ n1 ∧ η < (S (i + 1)).profileDrift

/-- Coarse/radial compactness can survive even when strong profiles drift. -/
def radialCoarseShapeCandidate
    (S : InteriorRenormSeq) (n0 n1 : Nat) (κ : Real) : Prop :=
  ∀ i : Nat, n0 ≤ i → i + 1 ≤ n1 → (S (i + 1)).radialDrift ≤ κ

/-- Angular/vector instability branch: radial shape survives but angular data does not. -/
def angularInstabilityCandidate
    (S : InteriorRenormSeq) (n0 n1 : Nat) (κ η : Real) : Prop :=
  radialCoarseShapeCandidate S n0 n1 κ ∧ profileGapCandidate S n0 n1 η

/--
Phase 5CG proof obligation.

Before the old branch can support a physical self-similarity claim, one must
exhibit a window, a fixed interior scale functional, and constants for which
scalar stability, boundary control, and profile compactness all hold.  If not,
the branch remains in the boundary-artifact or scalar-only/profile-gap branch.
-/
def phase5cgInteriorRenormDichotomy
    (S : InteriorRenormSeq) (n0 n1 : Nat) (δ ε η κ : Real) : Prop :=
  interiorRenormalizationCandidate S n0 n1 δ ε η ∨
    boundaryArtifactCandidate S n0 n1 ε ∨
    angularInstabilityCandidate S n0 n1 κ η ∨
    profileGapCandidate S n0 n1 η

/--
If the interior candidate branch is paid, the dichotomy resolves on that side.
-/
theorem phase5cg_dichotomy_of_interior_candidate
    {S : InteriorRenormSeq} {n0 n1 : Nat} {δ ε η κ : Real}
    (h : interiorRenormalizationCandidate S n0 n1 δ ε η) :
    phase5cgInteriorRenormDichotomy S n0 n1 δ ε η κ := by
  exact Or.inl h

/--
If any sample violates the boundary cutoff, the dichotomy resolves on the
instrument-limited branch.
-/
theorem phase5cg_dichotomy_of_boundary_artifact
    {S : InteriorRenormSeq} {n0 n1 : Nat} {δ ε η κ : Real}
    (h : boundaryArtifactCandidate S n0 n1 ε) :
    phase5cgInteriorRenormDichotomy S n0 n1 δ ε η κ := by
  exact Or.inr (Or.inl h)

/-- Coarse radial compactness with profile drift is its own branch. -/
theorem phase5cg_dichotomy_of_angular_instability
    {S : InteriorRenormSeq} {n0 n1 : Nat} {δ ε η κ : Real}
    (h : angularInstabilityCandidate S n0 n1 κ η) :
    phase5cgInteriorRenormDichotomy S n0 n1 δ ε η κ := by
  exact Or.inr (Or.inr (Or.inl h))

/--
If scalar stability does not come with compact rescaled profiles, the current
object is only scalar-stable, not a self-similar profile candidate.
-/
theorem phase5cg_dichotomy_of_profile_gap
    {S : InteriorRenormSeq} {n0 n1 : Nat} {δ ε η κ : Real}
    (h : profileGapCandidate S n0 n1 η) :
    phase5cgInteriorRenormDichotomy S n0 n1 δ ε η κ := by
  exact Or.inr (Or.inr (Or.inr h))

/--
The current proof target shape.

This theorem is tautological by design: it records the exact obligation the
next data/proof slice must discharge without pretending that the PDE estimate
has already been proved.
-/
theorem phase5cg_interior_renormalization_target_shape
    {S : InteriorRenormSeq} {n0 n1 : Nat} {δ ε η κ : Real}
    (h : phase5cgInteriorRenormDichotomy S n0 n1 δ ε η κ) :
    phase5cgInteriorRenormDichotomy S n0 n1 δ ε η κ := by
  exact h

end ZtareProofs
