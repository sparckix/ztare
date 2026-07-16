import ZtareProofs.AxiomPackOrbitAction

/-!
The first finalist pair from the elementary-tetrahedron campaign forces the
structural hypotheses used by `AxiomPackOrbitAction` once middle slices are
represented as permutations.

The finite campaign reaches this surface because injective endomaps of a
finite carrier are permutations.  Finiteness itself is not used below.
-/

namespace AxiomPackFinalistOneBridge

universe u

variable {X : Type u}

theorem finalistOne_source_fixed_of_middle_injective
    (T : X → X → X → X)
    (tetrahedron : ∀ x y z t p q,
      T (T x y z) (T x t p) q = T x (T y t q) (T z p q))
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z))
    (diagonal_inverse : ∀ x y, T x y (T x x x) = y)
    (cross_diagonal : ∀ x y, T x x y = T y x y) :
    ∀ x z, T x x z = x := by
  have diagonal_id : ∀ x a, T x a x = a := by
    intro x a
    let d := T x x x
    have hfix : T x d x = d := by
      have htet := tetrahedron x x x x x x
      have hdx : T d d x = d := by
        simpa [d, diagonal_inverse] using htet
      calc
        T x d x = T d d x := by
          simpa using (cross_diagonal d x).symm
        _ = d := hdx
    have hd : d = x := by
      apply middle_injective x x
      simpa [d] using hfix
    simpa [d, hd] using diagonal_inverse x a
  intro x z
  calc
    T x x z = T z x z := cross_diagonal x z
    _ = x := diagonal_id z x

theorem finalistOne_right_constant_of_middle_injective
    (T : X → X → X → X)
    (tetrahedron : ∀ x y z t p q,
      T (T x y z) (T x t p) q = T x (T y t q) (T z p q))
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z))
    (diagonal_inverse : ∀ x y, T x y (T x x x) = y)
    (cross_diagonal : ∀ x y, T x x y = T y x y) :
    ∀ x z q p a, T x a (T z p q) = T x a p := by
  have source_fixed : ∀ x z, T x x z = x :=
    finalistOne_source_fixed_of_middle_injective T tetrahedron middle_injective
      diagonal_inverse cross_diagonal
  have diagonal_id : ∀ x a, T x a x = a := by
    intro x a
    simpa [source_fixed] using diagonal_inverse x a
  have common_first : ∀ x p q a,
      T x (T x a p) q = T x (T x a q) p := by
    intro x p q a
    simpa [source_fixed, diagonal_id] using tetrahedron x x q a p q
  intro x z q p a
  apply middle_injective x q
  calc
    T x (T x a (T z p q)) q =
        T x (T x a q) (T z p q) := common_first x (T z p q) q a
    _ = T x (T x a p) q := by
      simpa [source_fixed] using (tetrahedron x x z a p q).symm

theorem finalistOne_commute_of_middle_injective
    (T : X → X → X → X)
    (tetrahedron : ∀ x y z t p q,
      T (T x y z) (T x t p) q = T x (T y t q) (T z p q))
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z))
    (diagonal_inverse : ∀ x y, T x y (T x x x) = y)
    (cross_diagonal : ∀ x y, T x x y = T y x y) :
    ∀ x z u v a, T x (T u a v) z = T u (T x a z) v := by
  have source_fixed : ∀ x z, T x x z = x :=
    finalistOne_source_fixed_of_middle_injective T tetrahedron middle_injective
      diagonal_inverse cross_diagonal
  have diagonal_id : ∀ x a, T x a x = a := by
    intro x a
    simpa [source_fixed] using diagonal_inverse x a
  have right_constant : ∀ x z q p a,
      T x a (T z p q) = T x a p := by
    exact finalistOne_right_constant_of_middle_injective T tetrahedron
      middle_injective diagonal_inverse cross_diagonal
  intro x z u v a
  simpa [diagonal_id, right_constant] using (tetrahedron x u x a z v).symm

/-- In the middle-injective finalist-one class, reconstruction through one
basepoint is possible exactly for the middle projection.  This statement is
independent of finiteness and of the orbit-action representation. -/
theorem finalistOne_reconstruction_iff_middle_projection
    (T : X → X → X → X)
    (tetrahedron : ∀ x y z t p q,
      T (T x y z) (T x t p) q = T x (T y t q) (T z p q))
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z))
    (diagonal_inverse : ∀ x y, T x y (T x x x) = y)
    (cross_diagonal : ∀ x y, T x x y = T y x y)
    (c : X) :
    (∀ x y z, T x y z = T x (T c y z) c) ↔
      ∀ x y z, T x y z = y := by
  have source_fixed : ∀ x z, T x x z = x :=
    finalistOne_source_fixed_of_middle_injective T tetrahedron middle_injective
      diagonal_inverse cross_diagonal
  have diagonal_id : ∀ x y, T x y x = y := by
    intro x y
    simpa [source_fixed] using diagonal_inverse x y
  constructor
  · intro reconstructs
    have base_projection : ∀ y z, T c y z = y := by
      intro y z
      apply middle_injective y c
      calc
        T y (T c y z) c = T y y z := (reconstructs y y z).symm
        _ = y := source_fixed y z
        _ = T y y c := (source_fixed y c).symm
    intro x y z
    calc
      T x y z = T x (T c y z) c := reconstructs x y z
      _ = T x y c := by rw [base_projection y z]
      _ = T x y x := by
        simpa only [base_projection] using (reconstructs x y x).symm
      _ = y := diagonal_id x y
  · intro projection x y z
    rw [projection x y z, projection c y z, projection x y c]

theorem finalistOne_source_fixed
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (diagonal_inverse : ∀ x y,
      translation x (translation x x x) y = y)
    (cross_diagonal : ∀ x y,
      translation x y x = translation y y x) :
    ∀ x z, translation x z x = x := by
  exact finalistOne_source_fixed_of_middle_injective
    (fun x y z => translation x z y) tetrahedron
    (fun x z => (translation x z).injective) diagonal_inverse cross_diagonal

theorem finalistOne_commute
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (diagonal_inverse : ∀ x y,
      translation x (translation x x x) y = y)
    (cross_diagonal : ∀ x y,
      translation x y x = translation y y x) :
    ∀ x z u v a,
      translation x z (translation u v a) =
        translation u v (translation x z a) := by
  exact finalistOne_commute_of_middle_injective
    (fun x y z => translation x z y) tetrahedron
    (fun x z => (translation x z).injective) diagonal_inverse cross_diagonal

theorem finalistOne_orbit_action_representation
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (diagonal_inverse : ∀ x y,
      translation x (translation x x x) y = y)
    (cross_diagonal : ∀ x y,
      translation x y x = translation y y x) :
    ∃ label : AxiomPackOrbitAction.TranslationOrbit translation →
        AxiomPackOrbitAction.TranslationOrbit translation →
          AxiomPackOrbitAction.translationSubgroup translation,
      (∀ x z,
        (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) =
          translation x z) ∧
      (∀ x y z,
        translation x z y =
          (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) y) := by
  exact AxiomPackOrbitAction.commutingTranslations_orbit_action_representation
    translation tetrahedron
    (finalistOne_source_fixed translation tetrahedron diagonal_inverse cross_diagonal)
    (finalistOne_commute translation tetrahedron diagonal_inverse cross_diagonal)

end AxiomPackFinalistOneBridge
