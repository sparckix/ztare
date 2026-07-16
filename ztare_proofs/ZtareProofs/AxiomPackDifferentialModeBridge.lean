import ZtareProofs.AxiomPackFinalistOrbitClassification
import ZtareProofs.AxiomPackFinalistWitnesses

/-!
The elementary-tetrahedron operation becomes a ternary differential-mode
operation after exchanging its first two coordinates:

  `F a b c = T b a c`.

This file records the exact boundary.  Differential-mode laws imply the
elementary tetrahedron equation without any cancellativity assumption.  In the
reverse direction, permutation middle slices, source fixing, and commuting
middle translations imply the differential-mode laws.

Under the same exchange, finalist zero is precisely the familiar
hemisemiprojection specialization `(xxy) = (xyx) = x`.  Finalist one supplies
`(xxy) = (xyy) = x`; it need not satisfy `(xyx) = x`, so it is not in general a
semiprojection.
-/

namespace AxiomPackDifferentialModeBridge

open AxiomPackFinalistOrbitClassification
open AxiomPackOrbitAction

universe u

variable {X : Type u}

def fromTetrahedron (T : X → X → X → X) (a b c : X) : X :=
  T b a c

def toTetrahedron (F : X → X → X → X) (x y z : X) : X :=
  F y x z

@[simp]
theorem fromTetrahedron_toTetrahedron (F : X → X → X → X) :
    fromTetrahedron (toTetrahedron F) = F := by
  rfl

@[simp]
theorem toTetrahedron_fromTetrahedron (T : X → X → X → X) :
    toTetrahedron (fromTetrahedron T) = T := by
  rfl

def DifferentialIdempotent (F : X → X → X → X) : Prop :=
  ∀ x, F x x x = x

def DifferentialLeftNormal (F : X → X → X → X) : Prop :=
  ∀ x y₁ y₂ z₁ z₂,
    F (F x y₁ y₂) z₁ z₂ = F (F x z₁ z₂) y₁ y₂

def DifferentialLeftReductive (F : X → X → X → X) : Prop :=
  ∀ x y₁ y₂ z₁ z₂ t₁ t₂,
    F x (F y₁ z₁ z₂) (F y₂ t₁ t₂) = F x y₁ y₂

def DifferentialModeLaws (F : X → X → X → X) : Prop :=
  DifferentialIdempotent F ∧
    DifferentialLeftNormal F ∧ DifferentialLeftReductive F

/-- Stronger than differential idempotence: every right translation indexed
by `(x,z)` fixes `x`. -/
def DifferentialSourceFixed (F : X → X → X → X) : Prop :=
  ∀ x z, F x x z = x

/-- The defining differential-mode laws imply the elementary tetrahedron
equation after exchanging the first two coordinates. -/
theorem differentialMode_implies_tetrahedron
    (F : X → X → X → X)
    (idempotent : DifferentialIdempotent F)
    (left_normal : DifferentialLeftNormal F)
    (left_reductive : DifferentialLeftReductive F) :
    TetrahedronEquation (toTetrahedron F) := by
  intro x y z t p q
  change F (F t x p) (F y x z) q =
    F (F t y q) x (F p z q)
  calc
    F (F t x p) (F y x z) q = F (F t x p) y q := by
      simpa [DifferentialIdempotent, idempotent q] using
        left_reductive (F t x p) y q x z q q
    _ = F (F t y q) x p := left_normal t x p y q
    _ = F (F t y q) x (F p z q) := by
      simpa [DifferentialIdempotent, idempotent x] using
        (left_reductive (F t y q) x p x x z q).symm

def permutationDifferentialOp
    (translation : X → X → Equiv.Perm X) (a b c : X) : X :=
  translation b c a

def permutationTetrahedronOp
    (translation : X → X → Equiv.Perm X) (x y z : X) : X :=
  translation x z y

@[simp]
theorem permutation_coordinate_exchange
    (translation : X → X → Equiv.Perm X) :
    fromTetrahedron (permutationTetrahedronOp translation) =
      permutationDifferentialOp translation := by
  rfl

/-- With permutation slices, tetrahedron coherence plus the two structural
translation laws is exactly a differential mode with the stronger source-fix
law. -/
theorem permutationSlices_structural_iff_strongDifferentialMode
    (translation : X → X → Equiv.Perm X) :
    (TetrahedronEquation (permutationTetrahedronOp translation) ∧
        (∀ x z, translation x z x = x) ∧
        (∀ x z u v a,
          translation x z (translation u v a) =
            translation u v (translation x z a))) ↔
      (DifferentialModeLaws (permutationDifferentialOp translation) ∧
        DifferentialSourceFixed (permutationDifferentialOp translation)) := by
  constructor
  · rintro ⟨tetrahedron, source_fixed, commute⟩
    have tetrahedron' : ∀ x y z t p q,
        translation (translation x z y) q (translation x p t) =
          translation x (translation z q p) (translation y q t) :=
      tetrahedron
    obtain ⟨right_generator, left_generator⟩ :=
      commutingTranslations_factor_through_orbits
        translation tetrahedron' source_fixed commute
    refine ⟨⟨?_, ?_, ?_⟩, ?_⟩
    · intro x
      exact source_fixed x x
    · intro a b c d e
      exact commute d e b c a
    · intro a b c d e f g
      change translation (translation d e b) (translation f g c) a =
        translation b c a
      rw [left_generator, right_generator]
    · exact source_fixed
  · rintro ⟨⟨idempotent, left_normal, left_reductive⟩, source_fixed⟩
    refine ⟨?_, source_fixed, ?_⟩
    · simpa [permutationDifferentialOp, permutationTetrahedronOp] using
        differentialMode_implies_tetrahedron
          (permutationDifferentialOp translation)
          idempotent left_normal left_reductive
    · intro x z u v a
      exact left_normal a u v x z

/-! ### Exact finalist coordinates -/

def DifferentialFinalistZeroLaws (F : X → X → X → X) : Prop :=
  (∀ a b c d, F a (F a b c) d = a) ∧
    (∀ a b c, F a b (F a c c) = a)

def DifferentialFinalistOneLaws (F : X → X → X → X) : Prop :=
  (∀ a b, F a b (F b b b) = a) ∧
    (∀ a b, F a a b = F a b b)

theorem finalistZero_coordinate_iff (T : X → X → X → X) :
    FinalistZeroLaws T ↔
      DifferentialFinalistZeroLaws (fromTetrahedron T) := by
  constructor
  · rintro ⟨first_law, second_law⟩
    constructor
    · intro a b c d
      exact first_law b a c d
    · intro a b c
      exact second_law b a c
  · rintro ⟨first_law, second_law⟩
    constructor
    · intro x y z w
      exact first_law y x z w
    · intro x y z
      exact second_law y x z

theorem finalistOne_coordinate_iff (T : X → X → X → X) :
    FinalistOneLaws T ↔
      DifferentialFinalistOneLaws (fromTetrahedron T) := by
  constructor
  · rintro ⟨first_law, second_law⟩
    constructor
    · intro a b
      exact first_law b a
    · intro a b
      exact second_law a b
  · rintro ⟨first_law, second_law⟩
    constructor
    · intro x y
      exact first_law y x
    · intro x y
      exact second_law x y

/-- Standard differential-mode terminology: `(xxy) = (xyx) = x`. -/
def HemisemiprojectionLaws (F : X → X → X → X) : Prop :=
  (∀ x y, F x x y = x) ∧ (∀ x y, F x y x = x)

/-- Standard first-coordinate ternary semiprojection laws. -/
def SemiprojectionLaws (F : X → X → X → X) : Prop :=
  HemisemiprojectionLaws F ∧ (∀ x y, F x y y = x)

def LastPairProjection (F : X → X → X → X) : Prop :=
  ∀ x y, F x y y = x

/-- Inside the strong differential-mode boundary, finalist zero is exactly
the known hemisemiprojection specialization. -/
theorem differentialFinalistZero_iff_hemisemiprojection
    (F : X → X → X → X)
    (idempotent : DifferentialIdempotent F)
    (left_reductive : DifferentialLeftReductive F)
    (source_fixed : DifferentialSourceFixed F) :
    DifferentialFinalistZeroLaws F ↔ HemisemiprojectionLaws F := by
  constructor
  · rintro ⟨_, second_law⟩
    refine ⟨source_fixed, ?_⟩
    intro a b
    simpa [DifferentialIdempotent, idempotent a] using second_law a b a
  · rintro ⟨_, outer_diagonal⟩
    constructor
    · intro a b c d
      simpa [DifferentialIdempotent, idempotent d, source_fixed a d] using
        left_reductive a a d b c d d
    · intro a b c
      simpa [DifferentialIdempotent, idempotent b, outer_diagonal a b] using
        left_reductive a b a b b c c

/-- Finalist one instead supplies the last-pair projection identity. -/
theorem differentialFinalistOne_iff_lastPairProjection
    (F : X → X → X → X)
    (idempotent : DifferentialIdempotent F)
    (source_fixed : DifferentialSourceFixed F) :
    DifferentialFinalistOneLaws F ↔ LastPairProjection F := by
  constructor
  · rintro ⟨first_law, _⟩
    intro a b
    simpa [DifferentialIdempotent, idempotent b] using first_law a b
  · intro last_pair
    constructor
    · intro a b
      simpa [DifferentialIdempotent, idempotent b] using last_pair a b
    · intro a b
      rw [source_fixed, last_pair]

/-! ### Raw cross-theory bridge

These theorems stay at the arbitrary ternary-operation boundary.  The first
uses no cancellation hypothesis.  The second uses exactly middle-slice
injectivity and never upgrades it to surjectivity or a permutation action.
-/

/-- The tetrahedron equation plus finalist zero is exactly the
hemisemiprojection differential-mode specialization after coordinate exchange,
for an arbitrary ternary operation. -/
theorem finalistZero_raw_iff_hemisemiprojectionDifferential
    (T : X → X → X → X) :
    (TetrahedronEquation T ∧ FinalistZeroLaws T) ↔
      (DifferentialModeLaws (fromTetrahedron T) ∧
        HemisemiprojectionLaws (fromTetrahedron T)) := by
  constructor
  · rintro ⟨tetrahedron, finalist⟩
    obtain ⟨source_fixed, commute⟩ :=
      AxiomPackFinalistZeroBridge.finalistZero_raw_forces_orbit_assumptions
        T tetrahedron finalist.1 finalist.2
    have right_absorption :=
      AxiomPackFinalistZeroBridge.finalistZero_right_absorption
        T tetrahedron finalist.1
    have diagonal :=
      AxiomPackFinalistZeroBridge.finalistZero_diagonal T finalist.2
    have tetrahedron_reduced :=
      AxiomPackFinalistZeroBridge.finalistZero_tetrahedron_reduced
        T tetrahedron right_absorption
    have middle_absorption :=
      AxiomPackFinalistZeroBridge.finalistZero_middle_absorption
        T right_absorption diagonal
    have left_label_invariant :=
      AxiomPackFinalistZeroBridge.finalistZero_left_label_invariant
        T tetrahedron_reduced diagonal middle_absorption
    have differential : DifferentialModeLaws (fromTetrahedron T) := by
      refine ⟨?_, ?_, ?_⟩
      · intro x
        exact source_fixed x x
      · intro x y₁ y₂ z₁ z₂
        change T z₁ (T y₁ x y₂) z₂ = T y₁ (T z₁ x z₂) y₂
        exact commute z₁ z₂ y₁ y₂ x
      · intro x y₁ y₂ z₁ z₂ t₁ t₂
        change T (T z₁ y₁ z₂) x (T t₁ y₂ t₂) = T y₁ x y₂
        calc
          T (T z₁ y₁ z₂) x (T t₁ y₂ t₂) =
              T (T z₁ y₁ z₂) x y₂ :=
            right_absorption (T z₁ y₁ z₂) x t₁ y₂ t₂
          _ = T y₁ x y₂ := left_label_invariant z₁ y₁ z₂ x y₂
    have source_fixed' : DifferentialSourceFixed (fromTetrahedron T) := by
      intro x z
      exact source_fixed x z
    refine ⟨differential, ?_⟩
    apply (differentialFinalistZero_iff_hemisemiprojection
      (fromTetrahedron T) differential.1 differential.2.2 source_fixed').1
    exact (finalistZero_coordinate_iff T).1 finalist
  · rintro ⟨differential, hemisemiprojection⟩
    have source_fixed : DifferentialSourceFixed (fromTetrahedron T) :=
      hemisemiprojection.1
    have coordinate_finalist :
        DifferentialFinalistZeroLaws (fromTetrahedron T) :=
      (differentialFinalistZero_iff_hemisemiprojection
        (fromTetrahedron T) differential.1 differential.2.2 source_fixed).2
          hemisemiprojection
    constructor
    · have tetrahedron := differentialMode_implies_tetrahedron
        (fromTetrahedron T) differential.1 differential.2.1 differential.2.2
      simpa only [toTetrahedron_fromTetrahedron] using tetrahedron
    · exact (finalistZero_coordinate_iff T).2 coordinate_finalist

/-- With middle-injective slices fixed as a hypothesis, finalist one is
exactly the source-fixed, last-pair differential-mode specialization. -/
theorem finalistOne_raw_iff_lastPairDifferential
    (T : X → X → X → X)
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z)) :
    (TetrahedronEquation T ∧ FinalistOneLaws T) ↔
      (DifferentialModeLaws (fromTetrahedron T) ∧
        DifferentialSourceFixed (fromTetrahedron T) ∧
        LastPairProjection (fromTetrahedron T)) := by
  constructor
  · rintro ⟨tetrahedron, finalist⟩
    have source_fixed :=
      AxiomPackFinalistOneBridge.finalistOne_source_fixed_of_middle_injective
        T tetrahedron middle_injective finalist.1 finalist.2
    have commute :=
      AxiomPackFinalistOneBridge.finalistOne_commute_of_middle_injective
        T tetrahedron middle_injective finalist.1 finalist.2
    have right_constant :=
      AxiomPackFinalistOneBridge.finalistOne_right_constant_of_middle_injective
        T tetrahedron middle_injective finalist.1 finalist.2
    have diagonal_id : ∀ x a, T x a x = a := by
      intro x a
      simpa [source_fixed] using finalist.1 x a
    have left_label_invariant :
        ∀ x y z t q, T (T x y z) t q = T y t q := by
      intro x y z t q
      have h := tetrahedron x y z t x q
      simpa only [diagonal_id, right_constant] using h
    have differential : DifferentialModeLaws (fromTetrahedron T) := by
      refine ⟨?_, ?_, ?_⟩
      · intro x
        exact source_fixed x x
      · intro x y₁ y₂ z₁ z₂
        change T z₁ (T y₁ x y₂) z₂ = T y₁ (T z₁ x z₂) y₂
        exact commute z₁ z₂ y₁ y₂ x
      · intro x y₁ y₂ z₁ z₂ t₁ t₂
        change T (T z₁ y₁ z₂) x (T t₁ y₂ t₂) = T y₁ x y₂
        calc
          T (T z₁ y₁ z₂) x (T t₁ y₂ t₂) =
              T (T z₁ y₁ z₂) x y₂ :=
            right_constant (T z₁ y₁ z₂) t₁ t₂ y₂ x
          _ = T y₁ x y₂ := left_label_invariant z₁ y₁ z₂ x y₂
    have source_fixed' : DifferentialSourceFixed (fromTetrahedron T) := by
      intro x z
      exact source_fixed x z
    refine ⟨differential, source_fixed', ?_⟩
    apply (differentialFinalistOne_iff_lastPairProjection
      (fromTetrahedron T) differential.1 source_fixed').1
    exact (finalistOne_coordinate_iff T).1 finalist
  · rintro ⟨differential, source_fixed, last_pair⟩
    have coordinate_finalist :
        DifferentialFinalistOneLaws (fromTetrahedron T) :=
      (differentialFinalistOne_iff_lastPairProjection
        (fromTetrahedron T) differential.1 source_fixed).2 last_pair
    constructor
    · have tetrahedron := differentialMode_implies_tetrahedron
        (fromTetrahedron T) differential.1 differential.2.1 differential.2.2
      simpa only [toTetrahedron_fromTetrahedron] using tetrahedron
    · exact (finalistOne_coordinate_iff T).2 coordinate_finalist

theorem finalistZero_permutationSlices_is_hemisemiprojection
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (finalistA : ∀ x y z w,
      translation (translation x z y) w y = y)
    (finalistB : ∀ x y z,
      translation x (translation z z y) y = y) :
    DifferentialModeLaws (permutationDifferentialOp translation) ∧
      HemisemiprojectionLaws (permutationDifferentialOp translation) := by
  obtain ⟨source_fixed, commute⟩ :=
    AxiomPackFinalistZeroBridge.finalistZero_forces_orbit_assumptions
      translation tetrahedron finalistA finalistB
  have strong :=
    (permutationSlices_structural_iff_strongDifferentialMode translation).1
      ⟨tetrahedron, source_fixed, commute⟩
  refine ⟨strong.1, ?_⟩
  apply (differentialFinalistZero_iff_hemisemiprojection
    (permutationDifferentialOp translation) strong.1.1 strong.1.2.2 strong.2).1
  exact (finalistZero_coordinate_iff
    (permutationTetrahedronOp translation)).1 ⟨finalistA, finalistB⟩

theorem finalistOne_permutationSlices_is_lastPairDifferential
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (diagonal_inverse : ∀ x y,
      translation x (translation x x x) y = y)
    (cross_diagonal : ∀ x y,
      translation x y x = translation y y x) :
    DifferentialModeLaws (permutationDifferentialOp translation) ∧
      DifferentialSourceFixed (permutationDifferentialOp translation) ∧
      LastPairProjection (permutationDifferentialOp translation) := by
  have source_fixed :=
    AxiomPackFinalistOneBridge.finalistOne_source_fixed
      translation tetrahedron diagonal_inverse cross_diagonal
  have commute :=
    AxiomPackFinalistOneBridge.finalistOne_commute
      translation tetrahedron diagonal_inverse cross_diagonal
  have strong :=
    (permutationSlices_structural_iff_strongDifferentialMode translation).1
      ⟨tetrahedron, source_fixed, commute⟩
  refine ⟨strong.1, strong.2, ?_⟩
  apply (differentialFinalistOne_iff_lastPairProjection
    (permutationDifferentialOp translation) strong.1.1 strong.2).1
  exact (finalistOne_coordinate_iff
    (permutationTetrahedronOp translation)).1
      ⟨diagonal_inverse, cross_diagonal⟩

/-! ### The finite finalist witnesses -/

open AxiomPackFinalistWitnesses

def finalistZeroDifferentialWitness (a b c : Carrier) : Carrier :=
  fromTetrahedron finalistZero a b c

def finalistOneDifferentialWitness (a b c : Carrier) : Carrier :=
  fromTetrahedron finalistOne a b c

theorem finalistZeroWitness_is_hemisemiprojection :
    HemisemiprojectionLaws finalistZeroDifferentialWitness := by
  change
    (∀ x y : Carrier, finalistZeroDifferentialWitness x x y = x) ∧
      (∀ x y : Carrier, finalistZeroDifferentialWitness x y x = x)
  native_decide

theorem finalistZeroWitness_not_semiprojection :
    ¬ SemiprojectionLaws finalistZeroDifferentialWitness := by
  change ¬ (
    ((∀ x y : Carrier, finalistZeroDifferentialWitness x x y = x) ∧
      (∀ x y : Carrier, finalistZeroDifferentialWitness x y x = x)) ∧
        (∀ x y : Carrier, finalistZeroDifferentialWitness x y y = x))
  native_decide

theorem finalistOneWitness_has_source_and_lastPair :
    DifferentialSourceFixed finalistOneDifferentialWitness ∧
      LastPairProjection finalistOneDifferentialWitness := by
  change
    (∀ x z : Carrier, finalistOneDifferentialWitness x x z = x) ∧
      (∀ x y : Carrier, finalistOneDifferentialWitness x y y = x)
  native_decide

/-- The missing equality pattern is explicit: the first and third inputs agree,
but the operation does not return that common value. -/
theorem finalistOneWitness_missing_outer_diagonal :
    finalistOneDifferentialWitness 0 2 0 ≠ 0 := by
  native_decide

theorem finalistOneWitness_not_semiprojection :
    ¬ SemiprojectionLaws finalistOneDifferentialWitness := by
  intro semiprojection
  exact finalistOneWitness_missing_outer_diagonal
    (semiprojection.1.2 0 2)

/-- Relabeling `0 ↦ 0`, `1 ↦ 2`, `2 ↦ 1`. -/
def relabel12 (x : Carrier) : Carrier :=
  if x = 0 then 0 else if x = 1 then 2 else 1

def publishedSwap02 (x : Carrier) : Carrier :=
  if x = 0 then 2 else if x = 2 then 0 else 1

/-- The three-element differential mode traditionally written
`f(a,b,c) = 2-a` when `b=c=1`, and `a` otherwise. -/
def publishedThreeElementMode (a b c : Carrier) : Carrier :=
  if b = 1 ∧ c = 1 then publishedSwap02 a else a

/-- The finalist-zero witness is exactly the standard three-element example,
up to the displayed relabeling and the `T ↔ F` coordinate exchange. -/
theorem finalistZeroWitness_is_publishedThreeElementMode :
    ∀ a b c,
      relabel12 (finalistZeroDifferentialWitness a b c) =
        publishedThreeElementMode (relabel12 a) (relabel12 b) (relabel12 c) := by
  native_decide

/-- The published example in the carrier labels where its nonidentity right
translation is `swap01` at the index pair `(2,2)`. -/
def relabeledPublishedThreeElementMode (a b c : Carrier) : Carrier :=
  relabel12
    (publishedThreeElementMode (relabel12 a) (relabel12 b) (relabel12 c))

/-- Finalist one is not a coordinate permutation of the published example, but
it is a depth-two term of that example on the same relabeled carrier. -/
theorem finalistOneWitness_from_publishedTerm :
    ∀ a b c,
      finalistOneDifferentialWitness a b c =
        relabeledPublishedThreeElementMode
          (relabeledPublishedThreeElementMode a b b) b c := by
  native_decide

/-- The converse depth-two interpretation: the relabeled published example is
a term operation of finalist one.  Together with the preceding theorem this is
an explicit mutual term-interpretation certificate, stronger than a
coordinate-permutation fingerprint and weaker than operation isomorphism. -/
theorem publishedTerm_from_finalistOneWitness :
    ∀ a b c,
      relabeledPublishedThreeElementMode a b c =
        finalistOneDifferentialWitness
          (finalistOneDifferentialWitness a b a) b c := by
  native_decide

end AxiomPackDifferentialModeBridge
