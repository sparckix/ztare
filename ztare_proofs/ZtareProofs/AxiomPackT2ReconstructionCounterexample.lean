import ZtareProofs.AxiomPackDifferentialModeBridge

/-!
A three-element counterexample to the reconstruction question for elementary
2-solutions and extracted second tetrahedral 4-groupoids.

The definitions below follow preprint Proposition 9.11 and Question 9.12,
published as Proposition 9.68 and Question 9.69, of Bardakov et al.,
*Set-Theoretical Solutions of Simplex Equations*.  Source terminology is
retained here because this is the post-freeze formal artifact, not an input to
anonymous AxiomPack navigation.
-/

namespace AxiomPackT2ReconstructionCounterexample

open AxiomPackFinalistOrbitClassification
open AxiomPackFinalistWitnesses

universe u

variable {X : Type u}

def elementaryMap (T : X → X → X → X) : X × X × X → X × X × X
  | (x, y, z) => (x, T x y z, z)

def ElementaryTwoSolution (T : X → X → X → X) : Prop :=
  TetrahedronEquation T ∧ Function.Bijective (elementaryMap T)

/-- The five axioms of a second tetrahedral 4-groupoid. -/
def T2GroupoidLaws
    (star circle left right : X → X → X) : Prop :=
  (∀ x y z, right x (star y z) = star (right x y) (right x z)) ∧
  (∀ x y z, left (circle x y) z = circle (left x z) (left y z)) ∧
  (∀ x y z w,
    circle (star x y) (star z w) = star (circle x z) (circle y w)) ∧
  (∀ x y z, left (right x y) z = right x (left y z)) ∧
  (∀ x y z, left (star x y) z = right x (circle y z))

/-- Exact hypotheses used to extract the four binary operations from a ternary
elementary 2-solution at a basepoint `c`. -/
def ExtractionHypotheses
    (T : X → X → X → X) (c : X) (brace : X → X) : Prop :=
  T c c c = c ∧
  (∀ x, brace (T c x c) = x) ∧
  (∀ x, T c (brace x) c = x) ∧
  (∀ x y, T (brace x) (brace y) c = brace (T x y c)) ∧
  (∀ x y, T c (brace x) (brace y) = brace (T c x y))

def extractedStar
    (T : X → X → X → X) (c : X) (x y : X) : X :=
  T x y c

def extractedCircle
    (T : X → X → X → X) (c : X) (x y : X) : X :=
  T c x y

def extractedRight
    (T : X → X → X → X) (c : X) (brace : X → X)
    (x y : X) : X :=
  T x (brace y) c

def extractedLeft
    (T : X → X → X → X) (c : X) (brace : X → X)
    (x y : X) : X :=
  T c (brace x) y

def reconstructed
    (T : X → X → X → X) (c : X) (brace : X → X)
    (x y z : X) : X :=
  extractedRight T c brace x (extractedCircle T c y z)

/-- In the middle-injective finalist-one class, the inverse-slice conditions
force the auxiliary unary map to be pointwise identity.  This is the
source-level counterpart of the diagonal-label identity in the orbit
representation. -/
theorem finalistOne_extraction_unary_identity_of_middle_injective
    (T : X → X → X → X)
    (tetrahedron : TetrahedronEquation T)
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z))
    (diagonal_inverse : ∀ x y, T x y (T x x x) = y)
    (cross_diagonal : ∀ x y, T x x y = T y x y)
    (c : X) (brace : X → X)
    (hypotheses : ExtractionHypotheses T c brace) :
    ∀ x, brace x = x := by
  have source_fixed :=
    AxiomPackFinalistOneBridge.finalistOne_source_fixed_of_middle_injective
      T tetrahedron middle_injective diagonal_inverse cross_diagonal
  have diagonal_id : ∀ x y, T x y x = y := by
    intro x y
    simpa [source_fixed] using diagonal_inverse x y
  intro x
  simpa only [diagonal_id] using hypotheses.2.1 x

theorem finalistOne_extraction_unary_eq_identity_of_middle_injective
    (T : X → X → X → X)
    (tetrahedron : TetrahedronEquation T)
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z))
    (diagonal_inverse : ∀ x y, T x y (T x x x) = y)
    (cross_diagonal : ∀ x y, T x x y = T y x y)
    (c : X) (brace : X → X)
    (hypotheses : ExtractionHypotheses T c brace) :
    brace = fun x => x := by
  funext x
  exact finalistOne_extraction_unary_identity_of_middle_injective
    T tetrahedron middle_injective diagonal_inverse cross_diagonal
    c brace hypotheses x

/-- For every admissible extraction in the middle-injective finalist-one
class, the paper's reconstruction holds exactly when the ternary operation is
the middle projection. -/
theorem finalistOne_extracted_reconstruction_iff_middle_projection
    (T : X → X → X → X)
    (tetrahedron : TetrahedronEquation T)
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z))
    (diagonal_inverse : ∀ x y, T x y (T x x x) = y)
    (cross_diagonal : ∀ x y, T x x y = T y x y)
    (c : X) (brace : X → X)
    (hypotheses : ExtractionHypotheses T c brace) :
    (∀ x y z, T x y z = reconstructed T c brace x y z) ↔
      ∀ x y z, T x y z = y := by
  have brace_identity :=
    finalistOne_extraction_unary_identity_of_middle_injective
      T tetrahedron middle_injective diagonal_inverse cross_diagonal
      c brace hypotheses
  have bridge :=
    AxiomPackFinalistOneBridge.finalistOne_reconstruction_iff_middle_projection
      T tetrahedron middle_injective diagonal_inverse cross_diagonal c
  constructor
  · intro reconstructs
    apply bridge.1
    intro x y z
    calc
      T x y z = reconstructed T c brace x y z := reconstructs x y z
      _ = T x (T c y z) c := by
        simp only [reconstructed, extractedRight, extractedCircle,
          brace_identity]
  · intro projection x y z
    calc
      T x y z = T x (T c y z) c := bridge.2 projection x y z
      _ = reconstructed T c brace x y z := by
        simp only [reconstructed, extractedRight, extractedCircle,
          brace_identity]

/-- Every nonprojection member of the middle-injective finalist-one class
fails reconstruction for every basepoint and every admissible unary map. -/
theorem finalistOne_nonprojection_not_reconstructible
    (T : X → X → X → X)
    (tetrahedron : TetrahedronEquation T)
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z))
    (diagonal_inverse : ∀ x y, T x y (T x x x) = y)
    (cross_diagonal : ∀ x y, T x x y = T y x y)
    (nonprojection : ¬ ∀ x y z, T x y z = y) :
    ¬ ∃ (c : X) (brace : X → X),
      ExtractionHypotheses T c brace ∧
        ∀ x y z, T x y z = reconstructed T c brace x y z := by
  rintro ⟨c, brace, hypotheses, reconstructs⟩
  exact nonprojection
    ((finalistOne_extracted_reconstruction_iff_middle_projection
      T tetrahedron middle_injective diagonal_inverse cross_diagonal
      c brace hypotheses).1 reconstructs)

theorem finalistOne_tetrahedron_kernel :
    ∀ x y z t p q,
      finalistOne (finalistOne x y z) (finalistOne x t p) q =
        finalistOne x (finalistOne y t q) (finalistOne z p q) := by
  intro x y z t p q
  fin_cases x <;> fin_cases y <;> fin_cases z <;>
    fin_cases t <;> fin_cases p <;> fin_cases q <;> decide

theorem finalistOne_middle_injective_kernel :
    ∀ x z, Function.Injective (fun y => finalistOne x y z) := by
  intro x z y y' equality
  fin_cases x <;> fin_cases z <;> fin_cases y <;> fin_cases y' <;>
    simp_all [finalistOne, swap01]

theorem finalistOne_first_law_kernel :
    ∀ x y, finalistOne x y (finalistOne x x x) = y := by
  intro x y
  fin_cases x <;> fin_cases y <;> decide

theorem finalistOne_second_law_kernel :
    ∀ x y, finalistOne x x y = finalistOne y x y := by
  intro x y
  fin_cases x <;> fin_cases y <;> decide

theorem finalistOne_diagonal_identity :
    ∀ c x, finalistOne c x c = x := by
  have source_fixed :=
    AxiomPackFinalistOneBridge.finalistOne_source_fixed_of_middle_injective
      finalistOne finalistOne_tetrahedron_kernel
      finalistOne_middle_injective_kernel
      finalistOne_first_law_kernel finalistOne_second_law_kernel
  intro c x
  simpa only [source_fixed] using finalistOne_first_law_kernel c x

theorem finalistOne_identity_extraction_hypotheses :
    ∀ c, ExtractionHypotheses finalistOne c (fun x => x) := by
  intro c
  refine ⟨finalistOne_diagonal_identity c c, ?_, ?_, ?_, ?_⟩
  · intro x
    exact finalistOne_diagonal_identity c x
  · intro x
    exact finalistOne_diagonal_identity c x
  · intro x y
    rfl
  · intro x y
    rfl

theorem finalistOne_elementaryMap_involutive :
    Function.Involutive (elementaryMap finalistOne) := by
  rintro ⟨x, y, z⟩
  fin_cases x <;> fin_cases y <;> fin_cases z <;> rfl

theorem finalistOne_elementaryMap_bijective :
    Function.Bijective (elementaryMap finalistOne) :=
  finalistOne_elementaryMap_involutive.bijective

theorem finalistOne_is_elementaryTwoSolution :
    ElementaryTwoSolution finalistOne :=
  ⟨finalistOne_tetrahedron_kernel, finalistOne_elementaryMap_bijective⟩

theorem finalistOne_extracted_t2_groupoid :
    ∀ c,
      T2GroupoidLaws
        (extractedStar finalistOne c)
        (extractedCircle finalistOne c)
        (extractedLeft finalistOne c (fun x => x))
        (extractedRight finalistOne c (fun x => x)) := by
  intro c
  refine ⟨?_, ?_, ?_, ?_, ?_⟩
  · intro x y z
    fin_cases c <;> fin_cases x <;> fin_cases y <;> fin_cases z <;> decide
  · intro x y z
    fin_cases c <;> fin_cases x <;> fin_cases y <;> fin_cases z <;> decide
  · intro x y z w
    fin_cases c <;> fin_cases x <;> fin_cases y <;> fin_cases z <;>
      fin_cases w <;> decide
  · intro x y z
    fin_cases c <;> fin_cases x <;> fin_cases y <;> fin_cases z <;> decide
  · intro x y z
    fin_cases c <;> fin_cases x <;> fin_cases y <;> fin_cases z <;> decide

/-- The reconstruction fails for each possible basepoint. -/
theorem finalistOne_reconstruction_fails_for_every_basepoint :
    ∀ c, ∃ x y z,
      finalistOne x y z ≠ reconstructed finalistOne c (fun x => x) x y z := by
  intro c
  fin_cases c
  · exact ⟨2, 0, 2, by decide⟩
  · exact ⟨2, 0, 2, by decide⟩
  · exact ⟨0, 0, 0, by decide⟩

/-- Since the basepoint slice is the identity, the extraction hypotheses force
the auxiliary unary map itself to be the identity. -/
theorem finalistOne_extraction_unary_eq_identity
    {c : Carrier} {brace : Carrier → Carrier}
    (hypotheses : ExtractionHypotheses finalistOne c brace) :
    brace = fun x => x := by
  funext x
  simpa only [finalistOne_diagonal_identity] using hypotheses.2.1 x

/-- No basepoint and admissible unary extraction reconstruct finalist one. -/
theorem finalistOne_not_reconstructible_from_extracted_t2_groupoid :
    ¬ ∃ (c : Carrier) (brace : Carrier → Carrier),
      ExtractionHypotheses finalistOne c brace ∧
        ∀ x y z, finalistOne x y z = reconstructed finalistOne c brace x y z := by
  rintro ⟨c, brace, hypotheses, reconstructs⟩
  have brace_identity :=
    finalistOne_extraction_unary_eq_identity hypotheses
  rw [brace_identity] at reconstructs
  obtain ⟨x, y, z, mismatch⟩ :=
    finalistOne_reconstruction_fails_for_every_basepoint c
  exact mismatch (reconstructs x y z)

/-- Complete finite certificate for the counterexample to the displayed
reconstruction question. -/
theorem finalistOne_t2_reconstruction_counterexample :
    ElementaryTwoSolution finalistOne ∧
      (∀ c, ExtractionHypotheses finalistOne c (fun x => x)) ∧
      (∀ c,
        T2GroupoidLaws
          (extractedStar finalistOne c)
          (extractedCircle finalistOne c)
          (extractedLeft finalistOne c (fun x => x))
          (extractedRight finalistOne c (fun x => x))) ∧
      ¬ ∃ (c : Carrier) (brace : Carrier → Carrier),
        ExtractionHypotheses finalistOne c brace ∧
          ∀ x y z,
            finalistOne x y z = reconstructed finalistOne c brace x y z := by
  exact ⟨finalistOne_is_elementaryTwoSolution,
    finalistOne_identity_extraction_hypotheses,
    finalistOne_extracted_t2_groupoid,
    finalistOne_not_reconstructible_from_extracted_t2_groupoid⟩

end AxiomPackT2ReconstructionCounterexample
