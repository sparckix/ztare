import Mathlib.Data.ZMod.Basic
import ZtareProofs.AxiomPackOrbitAction
import ZtareProofs.AxiomPackT2ReconstructionCounterexample

/-!
Exact extraction and reconstruction fibers for orbit-action operations.

The first result identifies equality of all four extracted operations, at a
fixed basepoint and with identity brace, with equality of the actions on the
basepoint row and column of the label matrix.  Both label indices range only
over orbit values hit by carrier points, and group elements are compared by
their action on the full carrier.

The second result removes faithfulness from the reconstruction criterion.
Reconstruction holds exactly when the multiplicative factorization defect
acts trivially.  A finite trivial-action witness records why equality of group
labels is stronger than reconstruction for a nonfaithful action.
-/

namespace AxiomPackOrbitActionExtractionFiber

open AxiomPackOrbitAction
open AxiomPackT2ReconstructionCounterexample

universe u v w

variable {G : Type u} {X : Type v} {O : Type w}

/-! ## Action-kernel language -/

/-- Two group elements are observationally equal on the carrier when they
induce the same action on every carrier point. -/
def SameAction [SMul G X] (g h : G) : Prop :=
  ∀ y : X, g • y = h • y

/-- Membership in the kernel of the action, written pointwise. -/
def ActsTrivially [SMul G X] (g : G) : Prop :=
  ∀ y : X, g • y = y

/-- Equality modulo the action kernel is equivalent to the quotient defect
acting trivially.  The order `h⁻¹ * g` corresponds to `g • y = h • y`. -/
theorem sameAction_iff_quotientDefect_actsTrivially
    [Group G] [MulAction G X] (g h : G) :
    SameAction (X := X) g h ↔ ActsTrivially (X := X) (h⁻¹ * g) := by
  constructor
  · intro same y
    calc
      (h⁻¹ * g) • y = h⁻¹ • (g • y) := by rw [mul_smul]
      _ = h⁻¹ • (h • y) := by rw [same y]
      _ = y := by simp
  · intro trivial y
    have acted := congrArg (fun q : X => h • q) (trivial y)
    simpa [mul_smul] using acted

/-! ## Exact equality of the extracted four-operation signature -/

/-- Equality of the four extracted operations for fixed `c` and `brace`. -/
def SameExtractedFourOperations
    (T U : X → X → X → X) (c : X) (brace : X → X) : Prop :=
  extractedStar T c = extractedStar U c ∧
    extractedCircle T c = extractedCircle U c ∧
    extractedLeft T c brace = extractedLeft U c brace ∧
    extractedRight T c brace = extractedRight U c brace

/-- Equality, modulo the action kernel, of the basepoint column and row on
the orbit indices hit by `orbit : X → O`.  The first conjunction ranges over
the hit first index `orbit x`; the second over the hit second index `orbit z`.
-/
def BaseRowColumnActionsAgree
    [SMul G X]
    (orbit : X → O) (label label' : O → O → G) (c : X) : Prop :=
  (∀ x : X,
      SameAction (X := X)
        (label (orbit x) (orbit c))
        (label' (orbit x) (orbit c))) ∧
    (∀ z : X,
      SameAction (X := X)
        (label (orbit c) (orbit z))
        (label' (orbit c) (orbit z)))

@[simp]
theorem orbitAction_extractedStar
    [SMul G X]
    (orbit : X → O) (label : O → O → G) (c x y : X) :
    extractedStar (orbitActionOp orbit label) c x y =
      label (orbit x) (orbit c) • y :=
  rfl

@[simp]
theorem orbitAction_extractedCircle
    [SMul G X]
    (orbit : X → O) (label : O → O → G) (c x z : X) :
    extractedCircle (orbitActionOp orbit label) c x z =
      label (orbit c) (orbit z) • x :=
  rfl

@[simp]
theorem orbitAction_extractedLeft_identity
    [SMul G X]
    (orbit : X → O) (label : O → O → G) (c x z : X) :
    extractedLeft (orbitActionOp orbit label) c (fun y => y) x z =
      label (orbit c) (orbit z) • x :=
  rfl

@[simp]
theorem orbitAction_extractedRight_identity
    [SMul G X]
    (orbit : X → O) (label : O → O → G) (c x y : X) :
    extractedRight (orbitActionOp orbit label) c (fun z => z) x y =
      label (orbit x) (orbit c) • y :=
  rfl

/-- The extracted four-operation signature remembers exactly the actions of
the basepoint row and column on hit orbit indices.  Labels away from that
cross, labels at unused values of `O`, and differences inside the action
kernel are invisible. -/
theorem orbitAction_sameExtractedFourOperations_iff_baseRowColumnActionsAgree
    [SMul G X]
    (orbit : X → O) (label label' : O → O → G) (c : X) :
    SameExtractedFourOperations
        (orbitActionOp orbit label) (orbitActionOp orbit label') c
        (fun x => x) ↔
      BaseRowColumnActionsAgree orbit label label' c := by
  constructor
  · rintro ⟨star, circle, _left, _right⟩
    constructor
    · intro x y
      have h := congrFun (congrFun star x) y
      simpa using h
    · intro z y
      have h := congrFun (congrFun circle y) z
      simpa using h
  · rintro ⟨column, row⟩
    refine ⟨?_, ?_, ?_, ?_⟩
    · funext x y
      simpa using column x y
    · funext x z
      simpa using row z x
    · funext x z
      simpa using row z x
    · funext x y
      simpa using column x y

/-! ## Reconstruction modulo the action kernel -/

/-- The defect between direct and basepoint-factorized labels.  Its
orientation is chosen so that trivial action means
`direct • y = factorized • y`. -/
def basepointFactorizationDefect
    [Group G]
    (orbit : X → O) (label : O → O → G) (c x z : X) : G :=
  (label (orbit x) (orbit c) * label (orbit c) (orbit z))⁻¹ *
    label (orbit x) (orbit z)

@[simp]
theorem orbitAction_reconstructed_identity
    [Monoid G] [MulAction G X]
    (orbit : X → O) (label : O → O → G) (c x y z : X) :
    reconstructed (orbitActionOp orbit label) c (fun q => q) x y z =
      (label (orbit x) (orbit c) * label (orbit c) (orbit z)) • y := by
  simp [reconstructed, extractedRight, extractedCircle, orbitActionOp,
    smul_smul]

/-- Without faithfulness, reconstruction is exactly factorization modulo the
kernel of the action. -/
theorem orbitAction_reconstruction_iff_factorizationDefect_actsTrivially
    [Group G] [MulAction G X]
    (orbit : X → O) (label : O → O → G) (c : X) :
    (∀ x y z : X,
      orbitActionOp orbit label x y z =
        reconstructed (orbitActionOp orbit label) c (fun q => q) x y z) ↔
      ∀ x z : X,
        ActsTrivially (X := X)
          (basepointFactorizationDefect orbit label c x z) := by
  constructor
  · intro reconstructs x z
    apply (sameAction_iff_quotientDefect_actsTrivially
      (label (orbit x) (orbit z))
      (label (orbit x) (orbit c) * label (orbit c) (orbit z))).1
    intro y
    simpa [orbitActionOp] using reconstructs x y z
  · intro defects x y z
    have action_factorization :
        SameAction (X := X)
          (label (orbit x) (orbit z))
          (label (orbit x) (orbit c) * label (orbit c) (orbit z)) :=
      (sameAction_iff_quotientDefect_actsTrivially
        (label (orbit x) (orbit z))
        (label (orbit x) (orbit c) * label (orbit c) (orbit z))).2
        (defects x z)
    simpa [orbitActionOp] using action_factorization y

/-- The generated nested-operation formulation, with its missing closing
delimiter repaired, is the same kernel-defect criterion. -/
theorem orbitAction_nested_reconstruction_iff_factorizationDefect_actsTrivially
    [Group G] [MulAction G X]
    (orbit : X → O) (label : O → O → G) (c : X) :
    (∀ x y z : X,
      orbitActionOp orbit label x y z =
        orbitActionOp orbit label x
          (orbitActionOp orbit label c y z) c) ↔
      ∀ x z y : X,
        basepointFactorizationDefect orbit label c x z • y = y := by
  simpa [reconstructed, extractedRight, extractedCircle] using
    (orbitAction_reconstruction_iff_factorizationDefect_actsTrivially
      orbit label c)

/-! ## Nonfaithful boundary witness -/

/-- A two-element commutative group, written multiplicatively. -/
abbrev KernelWitnessGroup := Multiplicative (ZMod 2)

/-- The trivial action of `KernelWitnessGroup` on `Bool`. -/
@[reducible]
def kernelWitnessMulAction : MulAction KernelWitnessGroup Bool where
  smul := fun _ x => x
  one_smul := by intro x; rfl
  mul_smul := by intro g h x; rfl

local instance kernelWitnessMulActionInstance :
    MulAction KernelWitnessGroup Bool :=
  kernelWitnessMulAction

def kernelWitnessOrbit (_ : Bool) : PUnit := PUnit.unit

/-- The nonidentity group element hidden by the trivial action. -/
def kernelWitnessGenerator : KernelWitnessGroup :=
  Multiplicative.ofAdd (1 : ZMod 2)

/-- The constant nonidentity label. -/
def kernelWitnessLabel (_ _ : PUnit) : KernelWitnessGroup :=
  kernelWitnessGenerator

theorem kernelWitness_generator_ne_one :
    kernelWitnessGenerator ≠ 1 := by
  decide

theorem kernelWitness_action_not_faithful :
    ¬ FaithfulSMul KernelWitnessGroup Bool := by
  intro faithful
  have equal_one : kernelWitnessGenerator = (1 : KernelWitnessGroup) :=
    faithful.eq_of_smul_eq_smul (by intro x; rfl)
  exact kernelWitness_generator_ne_one equal_one

theorem kernelWitness_reconstructs :
    ∀ x y z : Bool,
      orbitActionOp kernelWitnessOrbit kernelWitnessLabel x y z =
        orbitActionOp kernelWitnessOrbit kernelWitnessLabel x
          (orbitActionOp kernelWitnessOrbit kernelWitnessLabel false y z)
          false := by
  intro x y z
  rfl

theorem kernelWitness_group_factorization_fails :
    ¬ ∀ x z : Bool,
      kernelWitnessLabel (kernelWitnessOrbit x) (kernelWitnessOrbit z) =
        kernelWitnessLabel (kernelWitnessOrbit x) (kernelWitnessOrbit false) *
          kernelWitnessLabel (kernelWitnessOrbit false) (kernelWitnessOrbit z) := by
  decide

theorem kernelWitness_defect_actsTrivially :
    ∀ x z : Bool,
      ActsTrivially (X := Bool)
        (basepointFactorizationDefect
          kernelWitnessOrbit kernelWitnessLabel false x z) := by
  intro x z y
  rfl

/-- Reconstruction can hold while group-level factorization fails when the
action has a nontrivial kernel. -/
theorem kernelWitness_reconstruction_without_group_factorization :
    (∀ x y z : Bool,
      orbitActionOp kernelWitnessOrbit kernelWitnessLabel x y z =
        orbitActionOp kernelWitnessOrbit kernelWitnessLabel x
          (orbitActionOp kernelWitnessOrbit kernelWitnessLabel false y z)
          false) ∧
      ¬ ∀ x z : Bool,
        kernelWitnessLabel (kernelWitnessOrbit x) (kernelWitnessOrbit z) =
          kernelWitnessLabel (kernelWitnessOrbit x)
              (kernelWitnessOrbit false) *
            kernelWitnessLabel (kernelWitnessOrbit false)
              (kernelWitnessOrbit z) :=
  ⟨kernelWitness_reconstructs, kernelWitness_group_factorization_fails⟩

end AxiomPackOrbitActionExtractionFiber
