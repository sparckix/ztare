import ZtareProofs.AxiomPackT2ReconstructionCounterexample

/-!
Minimal diagonal criterion for the published extraction/reconstruction map.

This statement was selected by the second target-conditioned self-play wave.
It isolates the reconstruction obstruction from the tetrahedron equation and
from the finalist-specific normalization laws.
-/

namespace AxiomPackT2DiagonalReconstruction

open AxiomPackT2ReconstructionCounterexample

universe u

variable {X : Type u}

/-- Two diagonal laws and middle-slice injectivity already force every
admissibly reconstructible operation to be the middle projection. -/
theorem diagonal_extracted_reconstruction_iff_middle_projection
    (T : X → X → X → X)
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z))
    (left_diagonal : ∀ x z, T x x z = x)
    (right_diagonal : ∀ x y, T x y x = y)
    (c : X) :
    (∃ brace : X → X,
      ExtractionHypotheses T c brace ∧
        ∀ x y z, T x y z = reconstructed T c brace x y z) ↔
      ∀ x y z, T x y z = y := by
  constructor
  · rintro ⟨brace, hextraction, hreconstructs⟩
    have hbrace : ∀ y, brace y = y := by
      intro y
      simpa only [right_diagonal] using hextraction.2.1 y
    have hreconstruction_normal :
        ∀ x y z, T x y z = T x (T c y z) c := by
      intro x y z
      calc
        T x y z = reconstructed T c brace x y z :=
          hreconstructs x y z
        _ = T x (T c y z) c := by
          simp only [reconstructed, extractedRight, extractedCircle, hbrace]
    have hcircle : ∀ y z, T c y z = y := by
      intro y z
      apply middle_injective y c
      calc
        T y (T c y z) c = T y y z :=
          (hreconstruction_normal y y z).symm
        _ = y := left_diagonal y z
        _ = T y y c := (left_diagonal y c).symm
    intro x y z
    calc
      T x y z = T x (T c y z) c := hreconstruction_normal x y z
      _ = T x y c := by rw [hcircle y z]
      _ = T x (T c y x) c := by rw [hcircle y x]
      _ = T x y x := (hreconstruction_normal x y x).symm
      _ = y := right_diagonal x y
  · intro hprojection
    refine ⟨fun x => x, ?_, ?_⟩
    · simp only [ExtractionHypotheses, hprojection]
      simp
    · intro x y z
      simp only [reconstructed, extractedRight, extractedCircle, hprojection]

end AxiomPackT2DiagonalReconstruction
