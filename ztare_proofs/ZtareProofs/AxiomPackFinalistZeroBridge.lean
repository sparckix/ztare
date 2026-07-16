import ZtareProofs.AxiomPackOrbitAction

/-!
The first frozen AxiomPack finalist for the elementary tetrahedron campaign
forces the source-fixing and commuting-translation invariants used by the
orbit-action representation theorem.  The primary theorem stays at the raw
ternary-operation boundary.  Its proof is purely equational: middle-coordinate
injectivity is part of the campaign's base theory but is not needed here.
-/

namespace AxiomPackFinalistZeroBridge

universe u

variable {X : Type u}

theorem finalistZero_source_fixed
    (op : X → X → X → X)
    (finalistA : ∀ x y z w, op (op x y z) y w = y)
    (finalistB : ∀ x y z, op x y (op z y z) = y) :
    ∀ x z, op x x z = x := by
  intro x z
  have hB := finalistB x x x
  have hA := finalistA x x (op x x x) z
  simpa [hB] using hA

/-- Every nested term in the third label erases to its middle input. -/
theorem finalistZero_right_absorption
    (op : X → X → X → X)
    (tetrahedron : ∀ x y z t p q,
      op (op x y z) (op x t p) q =
        op x (op y t q) (op z p q))
    (finalistA : ∀ x y z w, op (op x y z) y w = y) :
    ∀ x y z w v, op x y (op z w v) = op x y w := by
  intro x y z w v
  have h := tetrahedron x (op x y w) z y w v
  have h' : op x y w = op x y (op z w v) := by
    simpa only [finalistA] using h
  exact h'.symm

/-- Finalist B is self-absorbing, so the middle/third diagonal is fixed. -/
theorem finalistZero_diagonal
    (op : X → X → X → X)
    (finalistB : ∀ x y z, op x y (op z y z) = y) :
    ∀ x y, op x y y = y := by
  intro x y
  let d := op x y x
  have hd : op d y d = y := by
    simpa [d] using finalistB d y x
  have h := finalistB x y d
  simpa [hd] using h

/-- Right absorption removes the nested third coordinate from tetrahedron. -/
theorem finalistZero_tetrahedron_reduced
    (op : X → X → X → X)
    (tetrahedron : ∀ x y z t p q,
      op (op x y z) (op x t p) q =
        op x (op y t q) (op z p q))
    (right_absorption : ∀ x y z w v,
      op x y (op z w v) = op x y w) :
    ∀ x y z t p q,
      op (op x y z) (op x t p) q = op x (op y t q) p := by
  intro x y z t p q
  calc
    op (op x y z) (op x t p) q =
        op x (op y t q) (op z p q) := tetrahedron x y z t p q
    _ = op x (op y t q) p := right_absorption x (op y t q) z p q

/-- A nested middle value is absorbed when reused as the third label. -/
theorem finalistZero_middle_absorption
    (op : X → X → X → X)
    (right_absorption : ∀ x y z w v,
      op x y (op z w v) = op x y w)
    (diagonal : ∀ x y, op x y y = y) :
    ∀ x y z w, op x (op y z w) z = op y z w := by
  intro x y z w
  calc
    op x (op y z w) z = op x (op y z w) (op y z w) :=
      (right_absorption x (op y z w) y z w).symm
    _ = op y z w := diagonal x (op y z w)

/-- The first label of a translation descends along every generated move. -/
theorem finalistZero_left_label_invariant
    (op : X → X → X → X)
    (tetrahedron_reduced : ∀ x y z t p q,
      op (op x y z) (op x t p) q = op x (op y t q) p)
    (diagonal : ∀ x y, op x y y = y)
    (middle_absorption : ∀ x y z w,
      op x (op y z w) z = op y z w) :
    ∀ x y z t q, op (op x y z) t q = op y t q := by
  intro x y z t q
  have h := tetrahedron_reduced x y z t t q
  simpa only [diagonal, middle_absorption] using h

theorem finalistZero_raw_forces_orbit_assumptions
    (op : X → X → X → X)
    (tetrahedron : ∀ x y z t p q,
      op (op x y z) (op x t p) q =
        op x (op y t q) (op z p q))
    (finalistA : ∀ x y z w, op (op x y z) y w = y)
    (finalistB : ∀ x y z, op x y (op z y z) = y) :
    (∀ x z, op x x z = x) ∧
      (∀ x z u v a,
        op x (op u a v) z = op u (op x a z) v) := by
  have hs := finalistZero_source_fixed op finalistA finalistB
  have hr := finalistZero_right_absorption op tetrahedron finalistA
  have hd := finalistZero_diagonal op finalistB
  have ht := finalistZero_tetrahedron_reduced op tetrahedron hr
  have hm := finalistZero_middle_absorption op hr hd
  have hl := finalistZero_left_label_invariant op ht hd hm
  refine ⟨hs, ?_⟩
  intro x z u v a
  calc
    op x (op u a v) z = op (op x u x) (op x a z) v :=
      (ht x u x a z v).symm
    _ = op u (op x a z) v := hl x u x (op x a z) v

theorem finalistZero_forces_orbit_assumptions
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (finalistA : ∀ x y z w,
      translation (translation x z y) w y = y)
    (finalistB : ∀ x y z,
      translation x (translation z z y) y = y) :
    (∀ x z, translation x z x = x) ∧
      (∀ x z u v a,
        translation x z (translation u v a) =
          translation u v (translation x z a)) := by
  exact finalistZero_raw_forces_orbit_assumptions
    (fun x y z ↦ translation x z y)
    tetrahedron finalistA finalistB

theorem finalistZero_orbit_action_representation
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (finalistA : ∀ x y z w,
      translation (translation x z y) w y = y)
    (finalistB : ∀ x y z,
      translation x (translation z z y) y = y) :
    ∃ label : AxiomPackOrbitAction.TranslationOrbit translation →
        AxiomPackOrbitAction.TranslationOrbit translation →
          AxiomPackOrbitAction.translationSubgroup translation,
      (∀ x z,
        (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) =
          translation x z) ∧
      (∀ x y z,
        translation x z y =
          (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) y) := by
  obtain ⟨source_fixed, commute⟩ :=
    finalistZero_forces_orbit_assumptions translation tetrahedron finalistA finalistB
  exact AxiomPackOrbitAction.commutingTranslations_orbit_action_representation
    translation tetrahedron source_fixed commute

end AxiomPackFinalistZeroBridge
