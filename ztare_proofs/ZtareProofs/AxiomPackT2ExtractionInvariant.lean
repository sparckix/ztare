import ZtareProofs.AxiomPackT2ReconstructionCounterexample

/-!
The reconstructed ternary operation is a complete invariant of the four
binary operations extracted at a fixed basepoint with a fixed auxiliary map.

This theorem was selected by the second target-conditioned self-play wave.
Its proof uses only the inverse-slice clauses of `ExtractionHypotheses`; no
tetrahedron equation, finiteness, or injectivity assumption is needed.
-/

namespace AxiomPackT2ExtractionInvariant

open AxiomPackT2ReconstructionCounterexample

universe u

variable {X : Type u}

theorem extractedCircle_eq_reconstructed
    (T : X → X → X → X) (c : X) (brace : X → X)
    (h : ExtractionHypotheses T c brace) (y z : X) :
    extractedCircle T c y z = reconstructed T c brace c y z := by
  simp only [reconstructed, extractedRight, extractedCircle]
  exact (h.2.2.1 (T c y z)).symm

theorem extractedStar_eq_reconstructed
    (T : X → X → X → X) (c : X) (brace : X → X)
    (h : ExtractionHypotheses T c brace) (x y : X) :
    extractedStar T c x y = reconstructed T c brace x y c := by
  simp only [reconstructed, extractedRight, extractedCircle, extractedStar]
  rw [h.2.1 y]

theorem extractedRight_eq_reconstructed
    (T : X → X → X → X) (c : X) (brace : X → X)
    (h : ExtractionHypotheses T c brace) (x y : X) :
    extractedRight T c brace x y =
      reconstructed T c brace x (brace y) c := by
  simp only [reconstructed, extractedRight, extractedCircle]
  rw [h.2.2.1 y]

theorem extractedLeft_eq_reconstructed
    (T : X → X → X → X) (c : X) (brace : X → X)
    (h : ExtractionHypotheses T c brace) (x y : X) :
    extractedLeft T c brace x y =
      reconstructed T c brace c (brace x) y := by
  exact extractedCircle_eq_reconstructed T c brace h (brace x) y

/-- At fixed extraction coordinates, the reconstructed ternary operation and
the complete four-operation extraction signature determine each other. -/
theorem reconstructed_eq_iff_extracted_operations_eq
    (T U : X → X → X → X) (c : X) (brace : X → X)
    (hT : ExtractionHypotheses T c brace)
    (hU : ExtractionHypotheses U c brace) :
    (∀ x y z,
      reconstructed T c brace x y z = reconstructed U c brace x y z) ↔
      (∀ x y, extractedStar T c x y = extractedStar U c x y) ∧
      (∀ x y, extractedCircle T c x y = extractedCircle U c x y) ∧
      (∀ x y,
        extractedLeft T c brace x y = extractedLeft U c brace x y) ∧
      (∀ x y,
        extractedRight T c brace x y = extractedRight U c brace x y) := by
  constructor
  · intro hreconstructed
    refine ⟨?_, ?_, ?_, ?_⟩
    · intro x y
      calc
        extractedStar T c x y = reconstructed T c brace x y c :=
          extractedStar_eq_reconstructed T c brace hT x y
        _ = reconstructed U c brace x y c := hreconstructed x y c
        _ = extractedStar U c x y :=
          (extractedStar_eq_reconstructed U c brace hU x y).symm
    · intro x y
      calc
        extractedCircle T c x y = reconstructed T c brace c x y :=
          extractedCircle_eq_reconstructed T c brace hT x y
        _ = reconstructed U c brace c x y := hreconstructed c x y
        _ = extractedCircle U c x y :=
          (extractedCircle_eq_reconstructed U c brace hU x y).symm
    · intro x y
      calc
        extractedLeft T c brace x y =
            reconstructed T c brace c (brace x) y :=
          extractedLeft_eq_reconstructed T c brace hT x y
        _ = reconstructed U c brace c (brace x) y :=
          hreconstructed c (brace x) y
        _ = extractedLeft U c brace x y :=
          (extractedLeft_eq_reconstructed U c brace hU x y).symm
    · intro x y
      calc
        extractedRight T c brace x y =
            reconstructed T c brace x (brace y) c :=
          extractedRight_eq_reconstructed T c brace hT x y
        _ = reconstructed U c brace x (brace y) c :=
          hreconstructed x (brace y) c
        _ = extractedRight U c brace x y :=
          (extractedRight_eq_reconstructed U c brace hU x y).symm
  · rintro ⟨_, hcircle, _, hright⟩ x y z
    calc
      reconstructed T c brace x y z =
          extractedRight T c brace x (extractedCircle T c y z) := rfl
      _ = extractedRight U c brace x (extractedCircle T c y z) :=
        hright x (extractedCircle T c y z)
      _ = extractedRight U c brace x (extractedCircle U c y z) := by
        rw [hcircle y z]
      _ = reconstructed U c brace x y z := rfl

end AxiomPackT2ExtractionInvariant
