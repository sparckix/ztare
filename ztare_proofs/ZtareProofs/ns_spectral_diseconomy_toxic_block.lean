import Mathlib.Tactic
import ZtareProofs.ns_sos_certificate_bridge

/-!
# Spectral diseconomy bridge for toxic-block certificates

This file records the current "tiny to whole" compression from Phase 5BO/5BP.

The reduced certificate found in Phase 5BO is a local `2x2` amplitude-block
receipt.  By itself, it is not global: a rival can try to avoid the concrete
mode `20`.  The portable object is instead a spectral diseconomy condition:

* stealth requires a nonzero cancellation direction;
* moving that direction to higher frequency does not remove cost;
* the viscous Laplacian contributes a quadratic-in-frequency block;
* the stretching/production part is controlled by a lower-order coupling;
* once the quadratic viscous margin dominates, the same square-completion
  certificate exists for the substituted block.

The theorem below is intentionally abstract.  It is the Lean shape that a
future analytic/spectral estimate or exact SOS receipt must instantiate.
-/

namespace ZtareProofs.NS

noncomputable section

/-- A reduced two-coordinate toxic block.

The block represents the gap quadratic in coordinates `(x, y)`:

`a*x^2 + 2*b*x*y + c*y^2`.
-/
structure ToxicBlock where
  a : ℝ
  b : ℝ
  c : ℝ

/-- Schur slack for square completion of a `2x2` block. -/
def ToxicBlock.schurSlack (B : ToxicBlock) : ℝ :=
  B.c - B.b * B.b / B.a

/-- Quadratic form of a reduced toxic block. -/
def ToxicBlock.qform (B : ToxicBlock) (x y : ℝ) : ℝ :=
  B.a * x * x + 2 * B.b * x * y + B.c * y * y

/--
Square-completion identity for a reduced toxic block.

This is the exact algebraic receipt shape emitted by Phase 5BO:

`qform = a * (x + (b/a)y)^2 + schurSlack * y^2`.
-/
theorem toxicBlock_square_completion
    (B : ToxicBlock) (x y : ℝ) (ha : B.a ≠ 0) :
    B.qform x y =
      B.a * (x + (B.b / B.a) * y) * (x + (B.b / B.a) * y)
        + B.schurSlack * y * y := by
  unfold ToxicBlock.qform ToxicBlock.schurSlack
  field_simp [ha]
  ring

/--
Positive Schur slack certifies positivity of the reduced quadratic block.
-/
theorem toxicBlock_positive_of_schur
    (B : ToxicBlock)
    (ha : 0 < B.a)
    (hschur : 0 < B.schurSlack)
    (x y : ℝ)
    (hnonzero : x ≠ 0 ∨ y ≠ 0) :
    0 < B.qform x y := by
  have haneq : B.a ≠ 0 := ne_of_gt ha
  rw [toxicBlock_square_completion B x y haneq]
  have hsq1 : 0 ≤ (x + (B.b / B.a) * y) * (x + (B.b / B.a) * y) :=
    mul_self_nonneg _
  have hsq2 : 0 ≤ y * y := mul_self_nonneg y
  have hterm1_nonneg : 0 ≤ B.a * ((x + (B.b / B.a) * y) * (x + (B.b / B.a) * y)) :=
    mul_nonneg (le_of_lt ha) hsq1
  have hterm1_nonneg' : 0 ≤ B.a * (x + B.b / B.a * y) * (x + B.b / B.a * y) := by
    simpa [mul_assoc] using hterm1_nonneg
  have hterm2_nonneg : 0 ≤ B.schurSlack * (y * y) :=
    mul_nonneg (le_of_lt hschur) hsq2
  by_cases hy : y = 0
  · subst y
    have hx : x ≠ 0 := by
      cases hnonzero with
      | inl hx => exact hx
      | inr hzero => exact False.elim (hzero rfl)
    have hx2pos : 0 < x * x := mul_self_pos.mpr hx
    have hterm1_pos : 0 < B.a * (x * x) := mul_pos ha hx2pos
    have hterm1_pos' : 0 < B.a * x * x := by
      simpa [mul_assoc] using hterm1_pos
    simpa using add_pos_of_pos_of_nonneg hterm1_pos' hterm2_nonneg
  · have hy2pos : 0 < y * y := mul_self_pos.mpr hy
    have hterm2_pos : 0 < B.schurSlack * (y * y) := mul_pos hschur hy2pos
    have hterm2_pos' : 0 < B.schurSlack * y * y := by
      simpa [mul_assoc] using hterm2_pos
    exact add_pos_of_nonneg_of_pos hterm1_nonneg' hterm2_pos'

/--
Abstract spectral diseconomy condition for a substituted cancellation block.

`viscousScale` is the quadratic Laplacian contribution, while `couplingScale`
is the maximum production/cross-coupling that can erode the diagonal margin.
The theorem says: if the remaining block coefficients satisfy the Schur
certificate, the reduced block is strictly gap-positive.  Future PDE work must
instantiate the inequalities `0 < a` and `0 < schurSlack` from frequency
scaling rather than from a concrete mode number.
-/
theorem spectral_diseconomy_certifies_toxic_block
    (B : ToxicBlock) (viscousScale couplingScale margin : ℝ)
    (hmargin : 0 < margin)
    (ha_from_scale : margin ≤ viscousScale - couplingScale)
    (ha : viscousScale - couplingScale ≤ B.a)
    (hschur : 0 < B.schurSlack)
    (x y : ℝ)
    (hnonzero : x ≠ 0 ∨ y ≠ 0) :
    0 < B.qform x y := by
  have ha_pos : 0 < B.a := by linarith
  exact toxicBlock_positive_of_schur B ha_pos hschur x y hnonzero

end

end ZtareProofs.NS
