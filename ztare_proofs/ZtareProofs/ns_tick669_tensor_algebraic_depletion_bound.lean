import Mathlib.Tactic

/-!
# TICK669 local tensor-algebra check

This file records the algebraic boundary for the proposed
`TensorAlgebraicDepletionBound` route.

Trace-free strain algebra alone does not force vorticity direction away from a
stretching eigendirection.  With only `tr S = 0`, the stretching value is
unbounded by scaling.  On the normalized/eigenaligned local model, the
rotation signal `xi x S xi` vanishes exactly.
-/

namespace ZtareProofs.NS.Tick669TensorAlgebraicDepletionBound

noncomputable section

structure Vec3 where
  x : ℝ
  y : ℝ
  z : ℝ

@[ext]
theorem Vec3.ext {u v : Vec3}
    (hx : u.x = v.x) (hy : u.y = v.y) (hz : u.z = v.z) :
    u = v := by
  cases u
  cases v
  simp_all

def dot (u v : Vec3) : ℝ :=
  u.x * v.x + u.y * v.y + u.z * v.z

def cross (u v : Vec3) : Vec3 where
  x := u.y * v.z - u.z * v.y
  y := u.z * v.x - u.x * v.z
  z := u.x * v.y - u.y * v.x

def zeroVec : Vec3 where
  x := 0
  y := 0
  z := 0

def e1 : Vec3 where
  x := 1
  y := 0
  z := 0

/--
Trace-free diagonal strain with stretching axis `e1`.

The eigenvalues are `(a, -a/2, -a/2)`, so their sum is zero.
-/
def traceFreeDiagStrain (a : ℝ) (v : Vec3) : Vec3 where
  x := a * v.x
  y := (-(a / 2)) * v.y
  z := (-(a / 2)) * v.z

def localStretching (a : ℝ) (xi : Vec3) : ℝ :=
  dot (traceFreeDiagStrain a xi) xi

theorem traceFreeDiagStrain_trace_zero (a : ℝ) :
    a + (-(a / 2)) + (-(a / 2)) = 0 := by
  ring

theorem localStretching_e1 (a : ℝ) :
    localStretching a e1 = a := by
  simp [localStretching, dot, traceFreeDiagStrain, e1]

/--
Trace-free algebra alone has no finite pointwise maximum for stretching:
the diagonal model can make `(S xi) dot xi` exceed any prescribed bound.
-/
theorem no_finite_tensorAlgebraicDepletionBound_from_trace_free_only
    (B : ℝ) :
    ∃ a : ℝ, B < localStretching a e1 := by
  refine ⟨B + 1, ?_⟩
  rw [localStretching_e1]
  linarith

/--
At the aligned stretching eigendirection, the local rotation signal vanishes.

Thus the algebraic maximizer does not itself rotate `xi` away from the
stretching axis; any such rotation must come from an additional dynamical or
nonlocal source theorem.
-/
theorem cross_e1_traceFreeDiagStrain_e1_eq_zero (a : ℝ) :
    cross e1 (traceFreeDiagStrain a e1) = zeroVec := by
  apply Vec3.ext <;> simp [cross, e1, traceFreeDiagStrain, zeroVec]

/--
Positive local stretching can coexist with zero local rotation signal.

This is the minimal counterpacket to the claim that local strain tensor algebra
alone supplies a self-depleting alignment mechanism.
-/
theorem positive_stretching_with_zero_local_rotation :
    ∃ a : ℝ,
      0 < localStretching a e1 ∧
        cross e1 (traceFreeDiagStrain a e1) = zeroVec := by
  refine ⟨1, ?_, ?_⟩
  · rw [localStretching_e1]
    norm_num
  · exact cross_e1_traceFreeDiagStrain_e1_eq_zero 1

end

end ZtareProofs.NS.Tick669TensorAlgebraicDepletionBound
