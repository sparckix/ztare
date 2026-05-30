import Mathlib.Tactic

open scoped BigOperators

/-!
# Flat-torus Killing Fourier mode lemma

This file pays one concrete algebraic piece of the low-high kinematic
dichotomy.  In a periodic Fourier expansion, a zero-strain mode with nonzero
wave vector has zero amplitude.  Thus a smooth zero-strain periodic field has
only its zero Fourier mode left, i.e. the constant-translation branch.

This is not a full Littlewood-Paley charging theorem.  It is the exact
mode-level obstruction needed by the rotator side of the low-high branch:
nonzero Fourier modes cannot hide in the zero-deformation/Killing class.
-/

namespace ZtareProofs.NS

/-- Squared symmetric-gradient energy of a single Fourier mode.

This is the finite-dimensional deformation cost behind the low-high
Killing/rotator branch.  Constants such as `2π` are irrelevant for the branch
logic and are intentionally omitted. -/
noncomputable def symmetricGradientModeEnergy
    (k a : Fin 3 → Real) : Real :=
  ∑ i : Fin 3, ∑ j : Fin 3, (k i * a j + k j * a i) ^ (2 : Nat)

theorem symmetricGradientModeEnergy_nonnegative
    (k a : Fin 3 → Real) :
    0 ≤ symmetricGradientModeEnergy k a := by
  unfold symmetricGradientModeEnergy
  exact Finset.sum_nonneg
    (by
      intro i _hi
      exact Finset.sum_nonneg
        (by
          intro j _hj
          exact sq_nonneg (k i * a j + k j * a i)))

/-- Symmetric-gradient algebra for one real Fourier mode.

For a nonzero wave vector `k`, if the mode amplitude `a` satisfies
`k_i a_j + k_j a_i = 0` for every pair of coordinates, then `a = 0`.

This is the finite-dimensional core of the flat-torus fact that a periodic
zero-strain vector field has no nonzero Fourier modes. -/
theorem amplitude_zero_of_zero_symmetric_gradient_mode
    (k a : Fin 3 → Real)
    (hk : ∃ i : Fin 3, k i ≠ 0)
    (hstrain : ∀ i j : Fin 3, k i * a j + k j * a i = 0) :
    a = 0 := by
  obtain ⟨i, hki⟩ := hk
  have hai : a i = 0 := by
    have h := hstrain i i
    have hprod : k i * a i = 0 := by
      nlinarith
    exact (mul_eq_zero.mp hprod).resolve_left hki
  funext j
  have hij := hstrain i j
  rw [hai, mul_zero, add_zero] at hij
  exact (mul_eq_zero.mp hij).resolve_left hki

/-- One-mode contrapositive: if a nonzero wave vector has nonzero amplitude,
then its symmetric-gradient tensor cannot vanish identically. -/
theorem nonzero_amplitude_forces_nonzero_symmetric_gradient_mode
    (k a : Fin 3 → Real)
    (hk : ∃ i : Fin 3, k i ≠ 0)
    (ha : a ≠ 0) :
    ∃ i j : Fin 3, k i * a j + k j * a i ≠ 0 := by
  by_contra hnone
  have hstrain : ∀ i j : Fin 3, k i * a j + k j * a i = 0 := by
    intro i j
    exact of_not_not (by
      intro hneq
      exact hnone ⟨i, j, hneq⟩)
  exact ha (amplitude_zero_of_zero_symmetric_gradient_mode k a hk hstrain)

/-- Quantitative finite-mode deformation brick: a nonzero Fourier wave vector
with nonzero amplitude has strictly positive symmetric-gradient energy.

This is the first actual estimate behind the low-high kinematic dichotomy:
the zero-deformation branch cannot contain active nonzero Fourier modes, and
any such active mode pays a positive deformation cost defined before payoff is
scored. -/
theorem positive_symmetricGradientModeEnergy_of_nonzero_amplitude
    (k a : Fin 3 → Real)
    (hk : ∃ i : Fin 3, k i ≠ 0)
    (ha : a ≠ 0) :
    0 < symmetricGradientModeEnergy k a := by
  obtain ⟨i, j, hij⟩ :=
    nonzero_amplitude_forces_nonzero_symmetric_gradient_mode k a hk ha
  have hterm_pos :
      0 < (k i * a j + k j * a i) ^ (2 : Nat) :=
    sq_pos_of_ne_zero hij
  have hinner_nonneg :
      ∀ i' : Fin 3, 0 ≤
        ∑ j' : Fin 3, (k i' * a j' + k j' * a i') ^ (2 : Nat) := by
    intro i'
    exact Finset.sum_nonneg
      (by
        intro j' _hj
        exact sq_nonneg (k i' * a j' + k j' * a i'))
  have hterm_le_inner :
      (k i * a j + k j * a i) ^ (2 : Nat) ≤
        ∑ j' : Fin 3, (k i * a j' + k j' * a i) ^ (2 : Nat) := by
    exact Finset.single_le_sum
      (by
        intro j' _hj
        exact sq_nonneg (k i * a j' + k j' * a i))
      (Finset.mem_univ j)
  have hinner_pos :
      0 <
        ∑ j' : Fin 3, (k i * a j' + k j' * a i) ^ (2 : Nat) :=
    lt_of_lt_of_le hterm_pos hterm_le_inner
  have hinner_le_total :
      (∑ j' : Fin 3, (k i * a j' + k j' * a i) ^ (2 : Nat)) ≤
        symmetricGradientModeEnergy k a := by
    unfold symmetricGradientModeEnergy
    exact Finset.single_le_sum
      (by
        intro i' _hi
        exact hinner_nonneg i')
      (Finset.mem_univ i)
  exact lt_of_lt_of_le hinner_pos hinner_le_total

/-- If the one-mode symmetric-gradient energy is zero, then every coordinate
entry of the symmetric-gradient tensor is zero.  This converts the analytic
energy receipt into the algebraic zero-strain payload used by the Killing
branch. -/
theorem zero_symmetricGradientModeEnergy_forces_zero_strain
    (k a : Fin 3 → Real)
    (henergy : symmetricGradientModeEnergy k a = 0) :
    ∀ i j : Fin 3, k i * a j + k j * a i = 0 := by
  intro i j
  have hterm_nonneg :
      0 ≤ (k i * a j + k j * a i) ^ (2 : Nat) :=
    sq_nonneg (k i * a j + k j * a i)
  have hinner_nonneg :
      ∀ i' : Fin 3, 0 ≤
        ∑ j' : Fin 3, (k i' * a j' + k j' * a i') ^ (2 : Nat) := by
    intro i'
    exact Finset.sum_nonneg
      (by
        intro j' _hj
        exact sq_nonneg (k i' * a j' + k j' * a i'))
  have hterm_le_inner :
      (k i * a j + k j * a i) ^ (2 : Nat) ≤
        ∑ j' : Fin 3, (k i * a j' + k j' * a i) ^ (2 : Nat) := by
    exact Finset.single_le_sum
      (by
        intro j' _hj
        exact sq_nonneg (k i * a j' + k j' * a i))
      (Finset.mem_univ j)
  have hinner_le_total :
      (∑ j' : Fin 3, (k i * a j' + k j' * a i) ^ (2 : Nat)) ≤
        symmetricGradientModeEnergy k a := by
    unfold symmetricGradientModeEnergy
    exact Finset.single_le_sum
      (by
        intro i' _hi
        exact hinner_nonneg i')
      (Finset.mem_univ i)
  have hterm_le_zero :
      (k i * a j + k j * a i) ^ (2 : Nat) ≤ 0 := by
    rw [← henergy]
    exact hterm_le_inner.trans hinner_le_total
  have hsquare_zero :
      (k i * a j + k j * a i) ^ (2 : Nat) = 0 :=
    le_antisymm hterm_le_zero hterm_nonneg
  nlinarith

/-- Energy form of the one-mode Killing obstruction: a nonzero wave vector with
zero symmetric-gradient energy has zero amplitude. -/
theorem amplitude_zero_of_zero_symmetricGradientModeEnergy
    (k a : Fin 3 → Real)
    (hk : ∃ i : Fin 3, k i ≠ 0)
    (henergy : symmetricGradientModeEnergy k a = 0) :
    a = 0 := by
  exact amplitude_zero_of_zero_symmetric_gradient_mode k a hk
    (zero_symmetricGradientModeEnergy_forces_zero_strain k a henergy)

/-- Total finite symmetric-gradient energy across a finite Fourier payload. -/
noncomputable def finiteSymmetricGradientEnergy
    {ι : Type} [Fintype ι]
    (wave amplitude : ι → Fin 3 → Real) : Real :=
  ∑ m : ι, symmetricGradientModeEnergy (wave m) (amplitude m)

theorem finiteSymmetricGradientEnergy_nonnegative
    {ι : Type} [Fintype ι]
    (wave amplitude : ι → Fin 3 → Real) :
    0 ≤ finiteSymmetricGradientEnergy wave amplitude := by
  unfold finiteSymmetricGradientEnergy
  exact Finset.sum_nonneg
    (by
      intro m _hm
      exact symmetricGradientModeEnergy_nonnegative (wave m) (amplitude m))

/-- Finite-packet deformation estimate: if any nonzero Fourier wave has an
active amplitude, the total finite symmetric-gradient energy is strictly
positive. -/
theorem positive_finiteSymmetricGradientEnergy_of_active_mode
    {ι : Type} [Fintype ι]
    (wave amplitude : ι → Fin 3 → Real)
    (nonzero_wave : ∀ m : ι, ∃ i : Fin 3, wave m i ≠ 0)
    (activeMode : ι)
    (activeAmplitude : amplitude activeMode ≠ 0) :
    0 < finiteSymmetricGradientEnergy wave amplitude := by
  have hactive_pos :
      0 < symmetricGradientModeEnergy (wave activeMode) (amplitude activeMode) :=
    positive_symmetricGradientModeEnergy_of_nonzero_amplitude
      (wave activeMode)
      (amplitude activeMode)
      (nonzero_wave activeMode)
      activeAmplitude
  have hterm_le_total :
      symmetricGradientModeEnergy (wave activeMode) (amplitude activeMode) ≤
        finiteSymmetricGradientEnergy wave amplitude := by
    unfold finiteSymmetricGradientEnergy
    exact Finset.single_le_sum
      (by
        intro m _hm
        exact symmetricGradientModeEnergy_nonnegative (wave m) (amplitude m))
      (Finset.mem_univ activeMode)
  exact lt_of_lt_of_le hactive_pos hterm_le_total

/-- If a finite Fourier payload has zero total symmetric-gradient energy, then
every one-mode symmetric-gradient energy is zero. -/
theorem symmetricGradientModeEnergy_zero_of_finite_energy_zero
    {ι : Type} [Fintype ι]
    (wave amplitude : ι → Fin 3 → Real)
    (henergy : finiteSymmetricGradientEnergy wave amplitude = 0)
    (m : ι) :
    symmetricGradientModeEnergy (wave m) (amplitude m) = 0 := by
  have hterm_nonneg :
      0 ≤ symmetricGradientModeEnergy (wave m) (amplitude m) :=
    symmetricGradientModeEnergy_nonnegative (wave m) (amplitude m)
  have hterm_le_total :
      symmetricGradientModeEnergy (wave m) (amplitude m) ≤
        finiteSymmetricGradientEnergy wave amplitude := by
    unfold finiteSymmetricGradientEnergy
    exact Finset.single_le_sum
      (by
        intro m' _hm
        exact symmetricGradientModeEnergy_nonnegative (wave m') (amplitude m'))
      (Finset.mem_univ m)
  have hterm_le_zero :
      symmetricGradientModeEnergy (wave m) (amplitude m) ≤ 0 := by
    rw [← henergy]
    exact hterm_le_total
  exact le_antisymm hterm_le_zero hterm_nonneg

/-- Energy form of the finite Killing obstruction: if the finite symmetric
gradient energy is zero, all active nonzero Fourier amplitudes vanish. -/
theorem amplitudes_zero_of_finiteSymmetricGradientEnergy_zero
    {ι : Type} [Fintype ι]
    (wave amplitude : ι → Fin 3 → Real)
    (nonzero_wave : ∀ m : ι, ∃ i : Fin 3, wave m i ≠ 0)
    (henergy : finiteSymmetricGradientEnergy wave amplitude = 0)
    (m : ι) :
    amplitude m = 0 := by
  exact amplitude_zero_of_zero_symmetricGradientModeEnergy
    (wave m)
    (amplitude m)
    (nonzero_wave m)
    (symmetricGradientModeEnergy_zero_of_finite_energy_zero
      wave amplitude henergy m)

/-- Abstract finite Fourier support payload: every nonzero mode with
zero symmetric gradient has zero amplitude.

The concrete analytic theorem still has to connect this finite-support lemma
to a smooth torus field by Fourier expansion / density. -/
structure FiniteFourierZeroStrainPayload where
  mode : Type
  wave : mode → Fin 3 → Real
  amplitude : mode → Fin 3 → Real
  nonzero_wave : ∀ m : mode, ∃ i : Fin 3, wave m i ≠ 0
  zero_strain :
    ∀ m : mode, ∀ i j : Fin 3,
      wave m i * amplitude m j + wave m j * amplitude m i = 0

/-- Every finite nonzero mode in a zero-strain payload has zero amplitude. -/
theorem finite_zero_strain_payload_amplitudes_zero
    (P : FiniteFourierZeroStrainPayload)
    (m : P.mode) :
    P.amplitude m = 0 := by
  exact amplitude_zero_of_zero_symmetric_gradient_mode
    (P.wave m)
    (P.amplitude m)
    (P.nonzero_wave m)
    (P.zero_strain m)

/-- A finite Fourier rotator falsifier would be a zero-strain payload that still
has an active nonzero Fourier amplitude.  In PDE terms this is the finite-mode
version of the hostile story: "zero deformation, but a nontrivial shell-moving
low field remains." -/
structure FiniteFourierZeroStrainActiveMode where
  payload : FiniteFourierZeroStrainPayload
  activeMode : payload.mode
  activeAmplitudeNonzero : payload.amplitude activeMode ≠ 0

/-- Finite zero-strain rotator falsifiers do not exist: every nonzero Fourier
mode amplitude in the zero-strain payload is forced to vanish. -/
theorem no_finite_zero_strain_active_mode :
    FiniteFourierZeroStrainActiveMode → False := by
  intro H
  exact H.activeAmplitudeNonzero
    (finite_zero_strain_payload_amplitudes_zero H.payload H.activeMode)

/-- Finite-mode shell-transfer rotator falsifier.

This is the flat-torus version of the low-high hostile story: a low-frequency
field has zero deformation but still contains an active nonzero Fourier mode
capable of moving energy between two different shell labels.  The shell labels
are deliberately external data; the algebraic kill is stronger, because the
active nonzero mode itself is impossible under zero strain. -/
structure FiniteFourierShellTransferRotator where
  payload : FiniteFourierZeroStrainPayload
  sourceShell : Nat
  targetShell : Nat
  shellTransfer : sourceShell ≠ targetShell
  activeMode : payload.mode
  activeAmplitudeNonzero : payload.amplitude activeMode ≠ 0

/-- No finite Fourier zero-strain rotator can carry a nontrivial shell-transfer
payload.  Thus, in the finite-support flat-torus model, any nontrivial
shell-transferring catalyst must leave the zero-deformation/Killing branch. -/
theorem no_finite_zero_strain_shell_transfer_rotator :
    FiniteFourierShellTransferRotator → False := by
  intro H
  exact H.activeAmplitudeNonzero
    (finite_zero_strain_payload_amplitudes_zero H.payload H.activeMode)

/-- Contrapositive packaging: a finite shell-transfer rotator, if it exists at
all, must violate the zero-strain payload hypotheses. -/
theorem finite_shell_transfer_forces_nonzero_deformation_payload
    (P : FiniteFourierZeroStrainPayload)
    (sourceShell targetShell : Nat)
    (hmove : sourceShell ≠ targetShell)
    (activeMode : P.mode)
    (hactive : P.amplitude activeMode ≠ 0) :
    False := by
  exact no_finite_zero_strain_shell_transfer_rotator
    { payload := P
      sourceShell := sourceShell
      targetShell := targetShell
      shellTransfer := hmove
      activeMode := activeMode
      activeAmplitudeNonzero := hactive }

/-- This is the specific branch fact supplied by the mode lemma. -/
structure FlatTorusKillingModeConclusion where
  nonzero_modes_zero_amplitude : Prop
  only_zero_mode_can_remain : Prop
  constant_translation_branch : Prop
  shell_transfer_requires_nonzero_strain : Prop

/-- Provenance receipt for the flat-torus Killing-mode conclusion.

The conclusion object intentionally names only the four branch facts.  This
receipt records the proof spine between them: zero-strain Fourier rigidity must
feed the "only zero mode" reduction, the zero-mode reduction must feed the
constant-translation classification, and shell-transfer obstruction must be
derived from that chain.  The last three arrows are still abstract PDE/LP facts;
the finite-mode lemma above only pays the first algebraic obstruction. -/
structure FlatTorusKillingModeProvenance
    (C : FlatTorusKillingModeConclusion) where
  nonzero_modes_zero_amplitude :
    C.nonzero_modes_zero_amplitude
  only_zero_mode_of_nonzero_modes_zero :
    C.nonzero_modes_zero_amplitude → C.only_zero_mode_can_remain
  constant_translation_of_only_zero_mode :
    C.only_zero_mode_can_remain → C.constant_translation_branch
  shell_transfer_obstruction_of_constant_translation :
    C.constant_translation_branch →
      C.shell_transfer_requires_nonzero_strain

/-- The provenance receipt pays the shell-transfer obstruction only by walking
through the declared zero-strain/Killing-field chain. -/
theorem shell_transfer_requires_nonzero_strain_of_killing_mode_provenance
    (C : FlatTorusKillingModeConclusion)
    (R : FlatTorusKillingModeProvenance C) :
    C.shell_transfer_requires_nonzero_strain :=
  R.shell_transfer_obstruction_of_constant_translation
    (R.constant_translation_of_only_zero_mode
      (R.only_zero_mode_of_nonzero_modes_zero
        R.nonzero_modes_zero_amplitude))

/-- Source object for lifting the paid finite Fourier rigidity theorem into the
flat-torus Killing-mode conclusion surface.

The first edge is paid here by `finite_zero_strain_payload_amplitudes_zero`.
The smooth/LP edges remain explicit handoff maps: a caller must still supply
the finite-to-smooth completeness, constant-translation classification, and
shell-obstruction transfer, rather than treating the four conclusion `Prop`s
as self-proving declarations. -/
structure FlatTorusSmoothKillingFourierSource where
  finitePayload : FiniteFourierZeroStrainPayload
  only_zero_mode_can_remain : Prop
  constant_translation_branch : Prop
  shell_transfer_requires_nonzero_strain : Prop
  only_zero_mode_of_finite_nonzero_modes_zero :
    (∀ m : finitePayload.mode, finitePayload.amplitude m = 0) →
      only_zero_mode_can_remain
  constant_translation_of_only_zero_mode :
    only_zero_mode_can_remain → constant_translation_branch
  shell_transfer_obstruction_of_constant_translation :
    constant_translation_branch → shell_transfer_requires_nonzero_strain

/-- Conclusion package derived from a smooth Fourier Killing source. -/
def FlatTorusSmoothKillingFourierSource.toConclusion
    (S : FlatTorusSmoothKillingFourierSource) :
    FlatTorusKillingModeConclusion where
  nonzero_modes_zero_amplitude :=
    ∀ m : S.finitePayload.mode, S.finitePayload.amplitude m = 0
  only_zero_mode_can_remain := S.only_zero_mode_can_remain
  constant_translation_branch := S.constant_translation_branch
  shell_transfer_requires_nonzero_strain :=
    S.shell_transfer_requires_nonzero_strain

/-- Provenance receipt derived from the source. The Fourier-rigidity input is
not assumed: it is proved by the finite zero-strain payload theorem. -/
def FlatTorusSmoothKillingFourierSource.toProvenance
    (S : FlatTorusSmoothKillingFourierSource) :
    FlatTorusKillingModeProvenance S.toConclusion where
  nonzero_modes_zero_amplitude := by
    intro m
    exact finite_zero_strain_payload_amplitudes_zero S.finitePayload m
  only_zero_mode_of_nonzero_modes_zero :=
    S.only_zero_mode_of_finite_nonzero_modes_zero
  constant_translation_of_only_zero_mode :=
    S.constant_translation_of_only_zero_mode
  shell_transfer_obstruction_of_constant_translation :=
    S.shell_transfer_obstruction_of_constant_translation

/-- Direct source-level shell obstruction. Downstream code can consume this
instead of separately reconstructing the conclusion/provenance pair. -/
theorem shell_transfer_requires_nonzero_strain_of_smooth_killing_fourier_source
    (S : FlatTorusSmoothKillingFourierSource) :
    S.toConclusion.shell_transfer_requires_nonzero_strain :=
  shell_transfer_requires_nonzero_strain_of_killing_mode_provenance
    S.toConclusion S.toProvenance

/-- Named ways the flat-torus Killing-mode provenance chain can fail.

This keeps downstream bridges from compressing the torus symmetry-breaker into
one opaque proposition: a hostile branch must say whether Fourier rigidity,
zero-mode reduction, constant-translation classification, or shell obstruction
is the missing link. -/
inductive FlatTorusKillingModeProvenanceFalsifier
    (C : FlatTorusKillingModeConclusion)
    (R : FlatTorusKillingModeProvenance C) : Type where
  | nonzero_modes_zero_amplitude_missing :
      ¬ C.nonzero_modes_zero_amplitude →
        FlatTorusKillingModeProvenanceFalsifier C R
  | zero_mode_reduction_missing :
      ¬ C.only_zero_mode_can_remain →
        FlatTorusKillingModeProvenanceFalsifier C R
  | constant_translation_classification_missing :
      ¬ C.constant_translation_branch →
        FlatTorusKillingModeProvenanceFalsifier C R
  | shell_transfer_obstruction_missing :
      ¬ C.shell_transfer_requires_nonzero_strain →
        FlatTorusKillingModeProvenanceFalsifier C R

/-- A provenance receipt rules out every named failure in its own
zero-strain/Killing chain. -/
theorem no_flat_torus_killing_mode_provenance_falsifier
    (C : FlatTorusKillingModeConclusion)
    (R : FlatTorusKillingModeProvenance C)
    (F : FlatTorusKillingModeProvenanceFalsifier C R) :
    False := by
  cases F with
  | nonzero_modes_zero_amplitude_missing h =>
      exact h R.nonzero_modes_zero_amplitude
  | zero_mode_reduction_missing h =>
      exact h
        (R.only_zero_mode_of_nonzero_modes_zero
          R.nonzero_modes_zero_amplitude)
  | constant_translation_classification_missing h =>
      exact h
        (R.constant_translation_of_only_zero_mode
          (R.only_zero_mode_of_nonzero_modes_zero
            R.nonzero_modes_zero_amplitude))
  | shell_transfer_obstruction_missing h =>
      exact h
        (shell_transfer_requires_nonzero_strain_of_killing_mode_provenance
          C R)

end ZtareProofs.NS
