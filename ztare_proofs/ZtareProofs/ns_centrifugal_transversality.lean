import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic
import Mathlib.Tactic
import ZtareProofs.ns_signed_escape_coordinate

namespace ZtareProofs

/--
Model centrifugal lower bound suggested by the sampled NS decomposition:
for vorticity magnitude `ω`, misalignment angle `θ`, and eigengap `gap = λ₃ - λ₁`,
the transverse `-Ω²` torque scale is

  ω² sin(2θ) / (2 gap).

This is only a theorem seed definition, not a proved Navier-Stokes law.
-/
noncomputable def centrifugalTorqueLowerBound (ω θ gap : Real) : Real :=
  (ω ^ (2 : Nat)) * Real.sin (2 * θ) / (2 * gap)

/--
Abstract transverse-projection identity:
the signed escape derivative is the sum of a centrifugal term plus the
remaining opposition / support channels.
-/
theorem escape_split_identity
    {dEscape tauOmegaSq tauPressure tauViscous tauOmegaDir : Real}
    (hdecomp : dEscape = tauOmegaSq + tauPressure + tauViscous + tauOmegaDir) :
    dEscape = tauOmegaSq + tauPressure + tauViscous + tauOmegaDir := by
  exact hdecomp

/--
If the centrifugal channel dominates the absolute opposition of the remaining
terms by a margin `γ`, then the signed escape derivative is bounded below by `γ`.

This is the exact abstract implication suggested by Phase 5v/5w:
the proof burden is not "did the trace exit?" but "can one prove a pointwise
margin where the `-Ω²` transverse forcing beats the adverse pressure, viscous,
and omega-direction channels?"
-/
theorem outward_transversality_of_centrifugal_margin
    {dEscape tauOmegaSq tauPressure tauViscous tauOmegaDir γ : Real}
    (hdecomp : dEscape = tauOmegaSq + tauPressure + tauViscous + tauOmegaDir)
    (hmargin : γ ≤ tauOmegaSq - |tauPressure| - |tauViscous| - |tauOmegaDir|) :
    γ ≤ dEscape := by
  have hp : tauPressure ≥ -|tauPressure| := by
    exact neg_abs_le tauPressure
  have hv : tauViscous ≥ -|tauViscous| := by
    exact neg_abs_le tauViscous
  have ho : tauOmegaDir ≥ -|tauOmegaDir| := by
    exact neg_abs_le tauOmegaDir
  have hsum :
      tauOmegaSq - |tauPressure| - |tauViscous| - |tauOmegaDir|
        ≤ tauOmegaSq + tauPressure + tauViscous + tauOmegaDir := by
    linarith
  have : γ ≤ tauOmegaSq + tauPressure + tauViscous + tauOmegaDir := by
    exact le_trans hmargin hsum
  simpa [hdecomp] using this

/--
Pointwise target shape for a future NS premise-lift:
if the analytic centrifugal lower bound itself dominates the other channels by
`γ`, then the signed escape derivative is at least `γ`.
-/
theorem outward_transversality_of_model_centrifugal_bound
    {dEscape ω θ gap tauPressure tauViscous tauOmegaDir γ : Real}
    (_hgap : 0 < gap)
    (hdecomp :
      dEscape =
        centrifugalTorqueLowerBound ω θ gap + tauPressure + tauViscous + tauOmegaDir)
    (hmargin :
      γ ≤ centrifugalTorqueLowerBound ω θ gap - |tauPressure| - |tauViscous| - |tauOmegaDir|) :
    γ ≤ dEscape := by
  have := outward_transversality_of_centrifugal_margin
    (dEscape := dEscape)
    (tauOmegaSq := centrifugalTorqueLowerBound ω θ gap)
    (tauPressure := tauPressure)
    (tauViscous := tauViscous)
    (tauOmegaDir := tauOmegaDir)
    (γ := γ)
    hdecomp
    hmargin
  exact this

/--
If the same centrifugal margin yields a positive lower bound `γ > 0`, then the
danger-state dwell can be capped by the signed-escape lemma already in the
formal stack.
-/
theorem dwell_cap_from_centrifugal_transversality
    {a0 Δ γ dwell : Real}
    (hγ : 0 < γ)
    (ha0 : 0 ≤ a0)
    (ha0_le : a0 ≤ Δ)
    (hband : a0 + γ * dwell ≤ Δ) :
    dwell ≤ (Δ - a0) / γ := by
  exact danger_dwell_le_of_signed_escape hγ ha0 ha0_le hband

end ZtareProofs
