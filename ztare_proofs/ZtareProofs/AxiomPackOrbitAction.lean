import Mathlib.GroupTheory.GroupAction.Defs
import Mathlib.GroupTheory.Subgroup.Centralizer
import Mathlib.Algebra.Group.Action.Faithful

/-!
An AxiomPack finite survivor suggested that the middle coordinate of an
elementary tetrahedron map should be treated as a permutation action rather
than as a raw ternary table.  These statements isolate the representation
theorem without assuming the finite carrier used to discover it.
-/

namespace AxiomPackOrbitAction

universe u v w

variable {G : Type u} {X : Type v} {O : Type w}

def orbitActionOp [CommGroup G] [MulAction G X]
    (orbit : X → O) (label : O → O → G) (x y z : X) : X :=
  label (orbit x) (orbit z) • y

theorem orbitAction_tetrahedron [CommGroup G] [MulAction G X]
    (orbit : X → O) (label : O → O → G)
    (orbit_invariant : ∀ (g : G) (x : X), orbit (g • x) = orbit x) :
    ∀ x y z t p q,
      orbitActionOp orbit label
          (orbitActionOp orbit label x y z)
          (orbitActionOp orbit label x t p) q =
        orbitActionOp orbit label x
          (orbitActionOp orbit label y t q)
          (orbitActionOp orbit label z p q) := by
  intro x y z t p q
  simp [orbitActionOp, orbit_invariant, smul_smul, mul_comm]

theorem orbitAction_normalization [CommGroup G] [MulAction G X]
    (orbit : X → O) (label : O → O → G)
    (diagonal_identity : ∀ a, label a a = 1)
    (source_orbit_fixed : ∀ x z, label (orbit x) (orbit z) • x = x) :
    (∀ x y,
        orbitActionOp orbit label x y
          (orbitActionOp orbit label x x x) = y) ∧
      (∀ x y,
        orbitActionOp orbit label x x y =
          orbitActionOp orbit label y x y) := by
  constructor
  · intro x y
    simp [orbitActionOp, diagonal_identity]
  · intro x y
    simp [orbitActionOp, diagonal_identity, source_orbit_fixed]

/-- Reconstruction through a basepoint composes the two orbit labels along
that basepoint.  This is the obstruction underlying the second-tetrahedral
groupoid reconstruction question. -/
theorem orbitAction_basepoint_reconstruction [CommGroup G] [MulAction G X]
    (orbit : X → O) (label : O → O → G)
    (c x y z : X) :
    orbitActionOp orbit label x
        (orbitActionOp orbit label c y z) c =
      (label (orbit x) (orbit c) * label (orbit c) (orbit z)) • y := by
  simp [orbitActionOp, smul_smul]

/-- At action level, basepoint reconstruction is exactly equality between
each direct label action and the corresponding two-step label action. -/
theorem orbitAction_reconstruction_iff_action_factorization
    [CommGroup G] [MulAction G X]
    (orbit : X → O) (label : O → O → G)
    (c : X) :
    (∀ (x y z : X),
      orbitActionOp orbit label x y z =
        orbitActionOp orbit label x
          (orbitActionOp orbit label c y z) c) ↔
      ∀ (x y z : X),
        label (orbit x) (orbit z) • y =
          (label (orbit x) (orbit c) * label (orbit c) (orbit z)) • y := by
  constructor
  · intro reconstructs x y z
    simpa [orbitActionOp, smul_smul] using reconstructs x y z
  · intro factors x y z
    simpa [orbitActionOp, smul_smul] using factors x y z

/-- For a faithful action, the original operation reconstructs through `c`
if and only if its orbit-label matrix factors multiplicatively through the
orbit of `c`. -/
theorem orbitAction_reconstruction_iff_label_factorization
    [CommGroup G] [MulAction G X] [FaithfulSMul G X]
    (orbit : X → O) (label : O → O → G)
    (c : X) :
    (∀ (x y z : X),
      orbitActionOp orbit label x y z =
        orbitActionOp orbit label x
          (orbitActionOp orbit label c y z) c) ↔
      ∀ (x z : X),
        label (orbit x) (orbit z) =
          label (orbit x) (orbit c) * label (orbit c) (orbit z) := by
  constructor
  · intro reconstructs x z
    apply eq_of_smul_eq_smul (M := G) (α := X)
    intro y
    simpa [orbitActionOp, smul_smul] using reconstructs x y z
  · intro factors x y z
    simp [orbitActionOp, smul_smul, factors x z]

theorem commutingTranslations_factor_through_orbits
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (source_fixed : ∀ x z, translation x z x = x)
    (commute : ∀ x z u v a,
      translation x z (translation u v a) =
        translation u v (translation x z a)) :
    (∀ x z q p,
        translation x (translation z q p) = translation x p) ∧
      (∀ x z y q,
        translation (translation x z y) q = translation y q) := by
  constructor
  · intro x z q p
    ext a
    let b := (translation x q).symm a
    have h := tetrahedron x x z b p q
    have h' :
        translation x p ((translation x q) b) =
          translation x (translation z q p) ((translation x q) b) := by
      simpa [source_fixed, commute] using h
    simpa [b] using h'.symm
  · intro x z y q
    ext a
    let b := (translation x x).symm a
    have h := tetrahedron x y z b x q
    have hfirst :
        translation x (translation z q x) = translation x x := by
      ext c
      let d := (translation x q).symm c
      have h0 := tetrahedron x x z d x q
      have h0' :
          translation x x ((translation x q) d) =
            translation x (translation z q x) ((translation x q) d) := by
        simpa [source_fixed, commute] using h0
      simpa [d] using h0'.symm
    have h' :
        translation (translation x z y) q ((translation x x) b) =
          translation y q ((translation x x) b) := by
      calc
        translation (translation x z y) q ((translation x x) b)
            = translation x (translation z q x) (translation y q b) := by
                simpa [source_fixed] using h
        _ = translation x x (translation y q b) := by rw [hfirst]
        _ = translation y q ((translation x x) b) := by rw [commute]
    simpa [b] using h'

def translationSubgroup (translation : X → X → Equiv.Perm X) : Subgroup (Equiv.Perm X) :=
  Subgroup.closure (Set.range fun xz : X × X => translation xz.1 xz.2)

theorem translationSubgroup_isMulCommutative
    (translation : X → X → Equiv.Perm X)
    (commute : ∀ x z u v a,
      translation x z (translation u v a) =
        translation u v (translation x z a)) :
    IsMulCommutative (translationSubgroup translation) := by
  apply Subgroup.isMulCommutative_closure
  rintro _ ⟨⟨x, z⟩, rfl⟩ _ ⟨⟨u, v⟩, rfl⟩
  ext a
  exact commute x z u v a

theorem translation_in_subgroup
    (translation : X → X → Equiv.Perm X) (x z : X) :
    translation x z ∈ translationSubgroup translation := by
  apply Subgroup.subset_closure
  exact ⟨(x, z), rfl⟩

theorem function_constant_on_generated_translation_orbits
    {Y : Type*}
    (translation : X → X → Equiv.Perm X)
    (f : X → Y)
    (generator_constant : ∀ u v x, f (translation u v x) = f x) :
    ∀ (h : translationSubgroup translation) x, f (h • x) = f x := by
  intro h
  rcases h with ⟨h, hh⟩
  change ∀ x, f (h x) = f x
  induction hh using Subgroup.closure_induction with
  | mem g hg =>
      obtain ⟨⟨u, v⟩, rfl⟩ := hg
      exact generator_constant u v
  | one => simp
  | mul g k hg hk pg pk =>
      intro x
      simp only [Equiv.Perm.coe_mul, Function.comp_apply]
      rw [pg, pk]
  | inv g hg pg =>
      intro x
      have hforward := pg (g⁻¹ x)
      simpa using hforward.symm

theorem translation_constant_on_generated_orbits
    (translation : X → X → Equiv.Perm X)
    (generator_right : ∀ x z q p,
      translation x (translation z q p) = translation x p)
    (generator_left : ∀ x z y q,
      translation (translation x z y) q = translation y q) :
    (∀ (h : translationSubgroup translation) x z,
        translation x (h • z) = translation x z) ∧
      (∀ (h : translationSubgroup translation) x z,
        translation (h • x) z = translation x z) := by
  constructor
  · intro h x
    exact function_constant_on_generated_translation_orbits translation
      (translation x) (generator_right x) h
  · intro h x z
    exact function_constant_on_generated_translation_orbits translation
      (fun y => translation y z) (fun u v y => generator_left u v y z) h x

abbrev TranslationOrbit (translation : X → X → Equiv.Perm X) :=
  MulAction.orbitRel.Quotient (translationSubgroup translation) X

def translationOrbitLabel
    (translation : X → X → Equiv.Perm X)
    (right_constant : ∀ (h : translationSubgroup translation) x z,
      translation x (h • z) = translation x z)
    (left_constant : ∀ (h : translationSubgroup translation) x z,
      translation (h • x) z = translation x z) :
    TranslationOrbit translation →
      TranslationOrbit translation → translationSubgroup translation :=
  fun ox oz => Quotient.liftOn₂' ox oz
    (fun x z => ⟨translation x z, translation_in_subgroup translation x z⟩)
    (by
      intro x z x' z' hx hz
      apply Subtype.ext
      obtain ⟨h, hh⟩ := MulAction.mem_orbit_iff.mp hx
      obtain ⟨k, hk⟩ := MulAction.mem_orbit_iff.mp hz
      rw [← hh, ← hk]
      change translation (h • x') (k • z') = translation x' z'
      rw [left_constant, right_constant])

@[simp]
theorem translationOrbitLabel_mk
    (translation : X → X → Equiv.Perm X)
    (right_constant : ∀ (h : translationSubgroup translation) x z,
      translation x (h • z) = translation x z)
    (left_constant : ∀ (h : translationSubgroup translation) x z,
      translation (h • x) z = translation x z)
    (x z : X) :
    (translationOrbitLabel translation right_constant left_constant
        (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) = translation x z :=
  rfl

theorem translationOrbitLabel_fixes_source_orbit
    (translation : X → X → Equiv.Perm X)
    (right_constant : ∀ (h : translationSubgroup translation) x z,
      translation x (h • z) = translation x z)
    (left_constant : ∀ (h : translationSubgroup translation) x z,
      translation (h • x) z = translation x z)
    (source_fixed : ∀ x z, translation x z x = x) :
    ∀ (h : translationSubgroup translation) x z,
      (translationOrbitLabel translation right_constant left_constant
        (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) (h • x) = h • x := by
  intro h x z
  change translation x z (h • x) = h • x
  rw [← left_constant h x z]
  exact source_fixed (h • x) z

theorem translationOrbitLabel_diagonal_identity
    (translation : X → X → Equiv.Perm X)
    (right_constant : ∀ (h : translationSubgroup translation) x z,
      translation x (h • z) = translation x z)
    (left_constant : ∀ (h : translationSubgroup translation) x z,
      translation (h • x) z = translation x z)
    (source_fixed : ∀ x z, translation x z x = x)
    (normalization : ∀ x y,
      translation x (translation x x x) y = y) :
    ∀ x,
      translationOrbitLabel translation right_constant left_constant
        (Quotient.mk'' x) (Quotient.mk'' x) = 1 := by
  intro x
  apply Subtype.ext
  ext y
  change translation x x y = y
  simpa [source_fixed] using normalization x y

theorem translationOrbitLabel_unique
    (translation : X → X → Equiv.Perm X)
    (right_constant : ∀ (h : translationSubgroup translation) x z,
      translation x (h • z) = translation x z)
    (left_constant : ∀ (h : translationSubgroup translation) x z,
      translation (h • x) z = translation x z)
    (label : TranslationOrbit translation →
      TranslationOrbit translation → translationSubgroup translation)
    (reconstruct : ∀ x z,
      (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) = translation x z) :
    label = translationOrbitLabel translation right_constant left_constant := by
  funext ox oz
  refine Quotient.inductionOn' ox ?_
  intro x
  refine Quotient.inductionOn' oz ?_
  intro z
  apply Subtype.ext
  exact reconstruct x z

theorem commutingTranslations_orbit_action_representation
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (source_fixed : ∀ x z, translation x z x = x)
    (commute : ∀ x z u v a,
      translation x z (translation u v a) =
        translation u v (translation x z a)) :
    ∃ label : TranslationOrbit translation →
        TranslationOrbit translation → translationSubgroup translation,
      (∀ x z,
        (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) =
          translation x z) ∧
      (∀ x y z,
        translation x z y =
          (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) y) := by
  obtain ⟨right_generator, left_generator⟩ :=
    commutingTranslations_factor_through_orbits translation tetrahedron source_fixed commute
  obtain ⟨right_constant, left_constant⟩ :=
    translation_constant_on_generated_orbits translation right_generator left_generator
  refine ⟨translationOrbitLabel translation right_constant left_constant, ?_, ?_⟩
  · intro x z
    rfl
  · intro x y z
    rfl

end AxiomPackOrbitAction
