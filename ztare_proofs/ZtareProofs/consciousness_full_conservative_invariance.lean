/-
Paper 8 GP-211: full categorical Conservative Invariance.

Statements proved:

* `conservative_invariance_full` — for a categorical equivalence
  `e : C ≌ D` between sites whose functors are continuous in BOTH
  directions, a presheaf `P` on `C` is a sheaf for `J` iff its
  pullback `e.inverse.op ⋙ P` is a sheaf for `K`.

* `conservative_invariance_full_symm` — symmetric form: a presheaf
  `Q` on `D` is a sheaf for `K` iff its pullback `e.functor.op ⋙ Q`
  is a sheaf for `J`. Together with the forward form, this means
  the equivalence transports sheaf-ness in both directions.

Both theorems compose Mathlib's `Functor.op_comp_isSheaf_of_isSheaf`
(SGA 4 III 1.5, in Sites/Continuous.lean) with the equivalence's
unit/counit isos. The full categorical equivalence of sheaf categories
is provided directly by Mathlib's `Equivalence.sheafCongr`
(Sites/Equivalence.lean) and is not re-proved here.
-/

import Mathlib.CategoryTheory.Sites.Continuous
import Mathlib.CategoryTheory.Equivalence

namespace ZtareProofs.Paper8.Full

open CategoryTheory Functor

universe v u w

variable {C : Type u} [Category.{v} C]
variable {D : Type u} [Category.{v} D]

theorem conservative_invariance_full
    (J : GrothendieckTopology C) (K : GrothendieckTopology D)
    (e : C ≌ D)
    [Functor.IsContinuous e.functor J K]
    [Functor.IsContinuous e.inverse K J]
    (P : Cᵒᵖ ⥤ Type w) :
    Presheaf.IsSheaf J P ↔ Presheaf.IsSheaf K (e.inverse.op ⋙ P) := by
  refine ⟨e.inverse.op_comp_isSheaf_of_isSheaf K J P, fun h => ?_⟩
  have h1 : Presheaf.IsSheaf J (e.functor.op ⋙ e.inverse.op ⋙ P) :=
    e.functor.op_comp_isSheaf_of_isSheaf J K (e.inverse.op ⋙ P) h
  have iso : (e.functor.op ⋙ e.inverse.op) ⋙ P ≅ P :=
    isoWhiskerRight e.op.unitIso.symm P ≪≫ P.leftUnitor
  exact (Presheaf.isSheaf_of_iso_iff iso).mp h1

/-- Symmetric form: a presheaf on `D` is a sheaf for `K` iff its
pullback along `e.functor.op` is a sheaf for `J`. -/
theorem conservative_invariance_full_symm
    (J : GrothendieckTopology C) (K : GrothendieckTopology D)
    (e : C ≌ D)
    [Functor.IsContinuous e.functor J K]
    [Functor.IsContinuous e.inverse K J]
    (Q : Dᵒᵖ ⥤ Type w) :
    Presheaf.IsSheaf K Q ↔ Presheaf.IsSheaf J (e.functor.op ⋙ Q) := by
  refine ⟨e.functor.op_comp_isSheaf_of_isSheaf J K Q, fun h => ?_⟩
  have h1 : Presheaf.IsSheaf K (e.inverse.op ⋙ e.functor.op ⋙ Q) :=
    e.inverse.op_comp_isSheaf_of_isSheaf K J (e.functor.op ⋙ Q) h
  have iso : (e.inverse.op ⋙ e.functor.op) ⋙ Q ≅ Q :=
    isoWhiskerRight e.op.counitIso Q ≪≫ Q.leftUnitor
  exact (Presheaf.isSheaf_of_iso_iff iso).mp h1

end ZtareProofs.Paper8.Full
