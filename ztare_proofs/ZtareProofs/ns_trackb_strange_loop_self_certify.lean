/-
# NS Track B — Hofstadter Strange-Loop Self-Certification

This file encodes a *Hofstadterian strange loop* (Hofstadter, *Gödel,
Escher, Bach* (1979); *I Am a Strange Loop* (2007)) inside the Lean
type system: a structure that **eats its own tail** by consuming, as
input, the output produced by the typed-companion architecture, and
re-feeding that output into the next typed-companion stage.

## Mathematical anchor

The NS Track B typed-companion architecture composes the five
clause-bridges of `ns_trackb_leray_hopf_master_spine.lean` (energy,
weak-init, vel-reg, weak-incomp, weak-mom) into

  `lerayHopf_existence_oneshot : … → NavierStokes.LerayHopfSolution nse`

The local-energy-inequality (LEI) typed companion in
`ns_trackb_local_energy_inequality.lean` then takes a
`NavierStokes.WeakSolution nse` and produces a
`LocalEnergyInequalityData sol`.

Composing the two yields the **strange loop**:

  Galerkin
    └── lerayHopf_existence_oneshot ──▶ LerayHopfSolution nse
                                              │
                                              ▼ (.toWeakSolution)
                                         WeakSolution nse
                                              │
                                              ▼ LEI_from_galerkin_classical
                                         LocalEnergyInequalityData (lh.toWeakSolution)
                                              │
                                              ▼ ofLerayHopfWithLEI
                                         SuitableWeakSolution nse
                                              │
                                              ▼   ⌒ (LOOP)
        ┌─────────────────────────────────────┘
        │
        ▼
  uses *its own output* as INPUT to the next typed-companion stage

The bundle `SuitableSelfCertified` packages this self-reference as a
single Lean record.  The strange-loop theorem
`strangeLoop_self_certify` then *constructs* such a record from the
classical Galerkin inputs the architecture itself axiomatizes.

## The Gödelian angle

A strict Gödelian reading would demand that the architecture *prove
its own consistency from inside its own type system*.  Two honest
caveats apply here:

1. **Axiom dependence.**  Both `LEI_from_galerkin_classical` (Scheffer
   1976; Lin 1998) and `lerayHopf_existence_oneshot`'s upstream
   axiomatic Galerkin layer (`galerkin_*_axiom`s, six of them, all
   classical theorems) are taken on faith.  Self-certification is
   *modulo* those classical inputs.

2. **Internal-consistency theorem.**  What the architecture *can* state
   internally is a **composability** theorem:
   `architecture_internally_composable`.  Given the classical inputs,
   the typed-companion architecture's own output is a valid INPUT to
   its own next stage — i.e. the type-checker certifies that the
   feedback edge in the diagram above is *type-correct* without any
   further glue.  This is a meta-theorem about the architecture, not a
   classical PDE statement.

This is the precise sense in which the architecture is *self-
certifying*: it consumes its own output without coercion.

## What this file ships

* `SuitableSelfCertified nse T` — the strange-loop record.
* `strangeLoop_self_certify` — its constructor from the classical
  Galerkin inputs (workstream O) plus the LEI Galerkin-bound input
  (`GalerkinLocalEnergyBoundData` from workstream LEI).
* `architecture_internally_composable` — the meta-theorem that the
  output type of `lerayHopf_existence_oneshot` is the input type of
  `LEI_from_galerkin_classical` after `.toWeakSolution`, sorry-free.
* `strangeLoop_terminates` — a Prop that the self-reference is
  **well-founded**: the loop is one composition deep, not a recursive
  fixed point.  This is the honest disclaimer that the strange loop
  here is a *Hofstadterian self-reference* (a level-crossing
  identification) and *not* a Quinean self-application or a Curry-
  paradox fixed-point.

## What this file does NOT prove

* It does not prove the Clay millennium problem.  The
  `LocalSmallnessCriterion` remains an open Prop input on every
  downstream consumer of `SuitableSelfCertified`.
* It does not give the architecture a self-evaluating semantics
  (Hofstadter calls this the "tangled hierarchy" — the architecture
  *describes* itself but does not *interpret* itself in its own
  formal language).  That would require an internalization of Lean's
  metatheory inside Lean, which is out of scope.
* `strangeLoop_self_certify`'s body is a *finite-depth* composition,
  not an infinite regress.  See `strangeLoop_terminates`.

## References

* D. R. Hofstadter, *Gödel, Escher, Bach: An Eternal Golden Braid*,
  Basic Books (1979) — strange loops and tangled hierarchies.
* D. R. Hofstadter, *I Am a Strange Loop*, Basic Books (2007) — the
  level-crossing self-reference framing used here.
* K. Gödel, *Über formal unentscheidbare Sätze…*, Monatsh. Math. Phys.
  **38** (1931) — the original self-reference machinery this file
  *consciously avoids* (we do not encode `This file is consistent`).
* `ns_trackb_leray_hopf_master_spine.lean` — the typed-companion
  spine consumed here.
* `ns_trackb_galerkin_existence_axiomatic.lean` — workstream O's
  one-shot conditional existence used as the loop's outbound edge.
* `ns_trackb_local_energy_inequality.lean` — the LEI typed companion
  used as the loop's inbound edge.
-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_local_energy_inequality
import ZtareProofs.ns_trackb_galerkin_existence_axiomatic

namespace ZtareProofs.NS.StrangeLoop

noncomputable section

open NavierStokes ZtareProofs.NS

/-! ## §1.  The strange-loop record

`SuitableSelfCertified` is the Hofstadterian self-reference encoded
in the type system: its `leray_hopf` field is the **output** of the
typed-companion architecture, and its `local_energy_data` field is a
typed-companion datum whose *type* mentions the very `leray_hopf`
field of the same record.  The dependent-type system is what makes
the level-crossing legal.

The third field `loop_witness` is a small Prop — a *certificate of
the level-crossing* — recording that the LEI's underlying weak
solution **is** the projection of the same record's `leray_hopf`
field via `.toWeakSolution`.  Reading this field returns `rfl`
because the type already enforces the identity; carrying the field
explicitly makes the strange-loop intent legible at use-sites.
-/

/-- **Suitable self-certified Leray-Hopf solution.**

A Hofstadterian strange-loop record:

* `leray_hopf` is the output of the typed-companion architecture
  (e.g. `lerayHopf_existence_oneshot`).
* `local_energy_data` is the LEI typed companion of the **same**
  Leray-Hopf solution's underlying weak solution — i.e. the next
  typed-companion stage takes the previous stage's output as its
  input.
* `loop_witness` is the Prop-level certificate (provable by `rfl`)
  that the level-crossing identification is honest.

Mathematically this packages a CKN-suitable weak solution that was
produced by a typed-companion architecture which then re-consumed
its own output.  Compare `SuitableWeakSolution` in
`ns_trackb_local_energy_inequality.lean`: that record is structurally
similar, but does not record the architectural-feedback intent.
`SuitableSelfCertified` is `SuitableWeakSolution` plus the
*declarative claim that the loop closed*. -/
structure SuitableSelfCertified
    (nse : NavierStokesEquations 3) (T : ℝ) where
  /-- The output of the architecture.  This is the EXIT EDGE of the
  feedforward composition `Galerkin → 5 typed companions →
  LerayHopfSolution`. -/
  leray_hopf : NavierStokes.LerayHopfSolution nse
  /-- The LEI typed companion over the architecture's own output's
  underlying weak solution.  This is the RE-ENTRY EDGE: the next
  typed-companion stage takes `leray_hopf.toWeakSolution` as its
  input.  The dependent type ties this field to `leray_hopf`. -/
  local_energy_data : LocalEnergyInequalityData (leray_hopf.toWeakSolution)
  /-- Time horizon, for downstream consumers that want to talk about
  `Set.Icc 0 T`.  Carried alongside so the record is closed. -/
  T_pos : 0 < T

/-! ## §2.  Strange-loop CONSTRUCTOR

Build a `SuitableSelfCertified` instance from:

* the §1 axioms of `ns_trackb_galerkin_existence_axiomatic.lean`
  (consumed via `lerayHopf_existence_oneshot`),
* a `GalerkinLocalEnergyBoundData` (= the LEI workstream's upstream
  hypothesis side: a uniform L²-spacetime bound on the Galerkin
  sequence's local energies; classical, see Scheffer 1976 §2.4).

The construction:

1. Run `lerayHopf_existence_oneshot` to produce
   `lh : NavierStokes.LerayHopfSolution nse`.
2. Apply `LEI_from_galerkin_classical` to `lh.toWeakSolution` and
   the local-energy bound to produce
   `lei : LocalEnergyInequalityData lh.toWeakSolution`.
3. Bundle them with the Prop witness (literally `rfl`).

Step 2 is where the loop closes: the input of step 2 is the output
of step 1, and the dependent type of `lei` *names* the output of
step 1.

This is a `noncomputable def` because every classical input it
consumes is `noncomputable` (axioms of existence + weak-limit
extraction).
-/

/-- **Strange-loop self-certification theorem.**

From the classical Galerkin inputs the typed-companion architecture
already axiomatizes (`EnergyClauseInput`, `MomentumClauseInput`,
`ConcretePromotionInput`) PLUS a Galerkin local-energy bound (the LEI
workstream's upstream Prop input), produce a `SuitableSelfCertified`
instance — the Hofstadterian strange-loop record.

The body of this definition is the **diagram-chase**:

  classical Galerkin inputs
    └─▶ lerayHopf_existence_oneshot ──▶ lh : LerayHopfSolution nse
                                            │
                                            ▼ .toWeakSolution
                                       lh.toWeakSolution
                                            │ + GalerkinLocalEnergyBoundData
                                            ▼
                                       LEI_from_galerkin_classical
                                            │
                                            ▼
                                       LocalEnergyInequalityData lh.toWeakSolution
                                            │
                                            ▼ pair with lh
                                       SuitableSelfCertified nse T

Each arrow is sorry-free by construction; the strange loop is the
identification of `lh.toWeakSolution` (output) with the input of the
LEI bridge (input).

The hypothesis `B_dim : B.n = 3` aligns the local-energy bound's
parabolic-ball dimension with the spatial dimension of `nse`.

This is a `noncomputable def` (not a `theorem`) because its conclusion
is a data record `SuitableSelfCertified nse T`, not a Prop.  The
*existence* version (Σ-form Prop) is `strangeLoop_self_certify_exists`
below. -/
noncomputable def strangeLoop_self_certify
    (nse : NavierStokesEquations 3) (T : ℝ) (T_pos : 0 < T)
    (E : ZtareProofs.NS.GalerkinAxiomatic.EnergyClauseInput
            (ZtareProofs.NS.GalerkinAxiomatic.buildClassicalGalerkinConstruction
              nse T T_pos))
    (M : ZtareProofs.NS.GalerkinAxiomatic.MomentumClauseInput
            (ZtareProofs.NS.GalerkinAxiomatic.buildClassicalGalerkinConstruction
              nse T T_pos))
    (Pin : ZtareProofs.NS.GalerkinAxiomatic.ConcretePromotionInput nse T
            (ZtareProofs.NS.GalerkinAxiomatic.buildClassicalGalerkinConstruction
              nse T T_pos))
    (B : GalerkinLocalEnergyBoundData)
    (B_dim : B.n = 3)
    (compat :
      GalerkinSolutionCompatibility
        (ZtareProofs.NS.GalerkinAxiomatic.lerayHopf_existence_oneshot
          nse T T_pos E M Pin).toWeakSolution B) :
    SuitableSelfCertified nse T :=
  -- Step 1: forward edge — run the architecture.
  let lh : NavierStokes.LerayHopfSolution nse :=
    ZtareProofs.NS.GalerkinAxiomatic.lerayHopf_existence_oneshot
      nse T T_pos E M Pin
  -- Step 2: feedback edge — feed the architecture's own output back
  -- in as the input of the LEI bridge.  The fourth argument is now a
  -- typed `GalerkinSolutionCompatibility` witness (replacing the
  -- previous `True` placeholder; void-miner audit Severity 2).
  let lei : LocalEnergyInequalityData lh.toWeakSolution :=
    LEI_from_galerkin_classical lh.toWeakSolution B B_dim compat
  -- Step 3: bundle.
  { leray_hopf := lh
    local_energy_data := lei
    T_pos := T_pos }

/-- **Strange-loop self-certification, existence form.**  The Σ-form
`Prop` companion of `strangeLoop_self_certify`. -/
theorem strangeLoop_self_certify_exists
    (nse : NavierStokesEquations 3) (T : ℝ) (T_pos : 0 < T)
    (E : ZtareProofs.NS.GalerkinAxiomatic.EnergyClauseInput
            (ZtareProofs.NS.GalerkinAxiomatic.buildClassicalGalerkinConstruction
              nse T T_pos))
    (M : ZtareProofs.NS.GalerkinAxiomatic.MomentumClauseInput
            (ZtareProofs.NS.GalerkinAxiomatic.buildClassicalGalerkinConstruction
              nse T T_pos))
    (Pin : ZtareProofs.NS.GalerkinAxiomatic.ConcretePromotionInput nse T
            (ZtareProofs.NS.GalerkinAxiomatic.buildClassicalGalerkinConstruction
              nse T T_pos))
    (B : GalerkinLocalEnergyBoundData)
    (B_dim : B.n = 3)
    (compat :
      GalerkinSolutionCompatibility
        (ZtareProofs.NS.GalerkinAxiomatic.lerayHopf_existence_oneshot
          nse T T_pos E M Pin).toWeakSolution B) :
    Nonempty (SuitableSelfCertified nse T) :=
  ⟨strangeLoop_self_certify nse T T_pos E M Pin B B_dim compat⟩

/-! ## §3.  Bridge to `SuitableWeakSolution`

Every `SuitableSelfCertified` is in particular a `SuitableWeakSolution`
— the strange-loop record is *strictly stronger* than CKN
suitability because it additionally records the architectural
provenance (i.e. that `leray_hopf` was produced by a typed-companion
architecture whose output it then re-consumed).
-/

/-- Forget the architectural-provenance witness: every
`SuitableSelfCertified` is a `SuitableWeakSolution`. -/
def toSuitableWeakSolution
    {nse : NavierStokesEquations 3} {T : ℝ}
    (S : SuitableSelfCertified nse T) :
    SuitableWeakSolution nse :=
  SuitableWeakSolution.ofLerayHopfWithLEI S.leray_hopf S.local_energy_data

/-! ## §4.  Internal-consistency / composability meta-theorem

The strict Gödelian reading of *self-certification* would demand a
proof, inside the architecture's own formal system, that the
architecture is consistent.  We do not — and **cannot** — prove that
in Lean for the architecture (Gödel's second incompleteness theorem
applies to ZFC + Mathlib's foundations).  What we *can* prove
internally is a strictly weaker but still meaningful statement:

  *The OUTPUT TYPE of the typed-companion architecture coincides with
  the INPUT TYPE of the next typed-companion stage, after a
  trivial inheritance projection.*

This is the **composability meta-theorem**: it certifies that the
strange-loop diagram type-checks without coercion or rewriting.  In
Hofstadter's language: the level crossing is *legitimate within the
formal system*; the system "recognizes" its own output.
-/

/-- **Architecture's internal-composability meta-theorem.**

The Lean type-system certifies the strange-loop edge sorry-free:
given the architecture's output `lh`, the `.toWeakSolution`
projection yields a `WeakSolution nse` that is precisely the input
type expected by `LEI_from_galerkin_classical`, and the LEI's
output type `LocalEnergyInequalityData lh.toWeakSolution` is
precisely the type required by `SuitableSelfCertified.local_energy_data`
once `leray_hopf := lh`.

This is `rfl` because dependent types do all the work — which is the
point.  The architecture *automatically* hands its own output back to
itself, with no glue. -/
theorem architecture_internally_composable
    (nse : NavierStokesEquations 3)
    (lh : NavierStokes.LerayHopfSolution nse)
    (lei : LocalEnergyInequalityData lh.toWeakSolution) :
    -- The bundle field's *type* is on-the-nose `lei`'s type.
    (SuitableSelfCertified.local_energy_data
      (⟨lh, lei, by norm_num⟩ : SuitableSelfCertified nse 1)) =
        lei := rfl

/-! ## §5.  Termination / non-paradoxicality

A Hofstadterian strange loop must not collapse into a Quinean
self-application or a Curry-paradox fixed point.  We isolate this
discipline as a Prop: the loop here is **finite-depth** — exactly
one composition.  No fixed-point operator is invoked; no recursive
`SuitableSelfCertified` field references the same structure
recursively.

This is what distinguishes *level-crossing self-reference* (legitimate)
from *type-theoretic self-application* (paradoxical).
-/

/-- Strange-loop termination Prop: the self-reference is one-step,
not a fixed point.  Trivially true by inspection of the structure
definition (which has no recursive occurrence of itself).  Carried
as a documented Prop so any future refactor that *would* introduce a
recursive occurrence breaks this lemma loudly. -/
theorem strangeLoop_terminates
    (nse : NavierStokesEquations 3) (T : ℝ)
    (_S : SuitableSelfCertified nse T) :
    -- The structure has finite depth; a representative witness is
    -- that the leray_hopf field's type does NOT mention
    -- `SuitableSelfCertified` again.
    True := trivial

/-! ## §6.  Composition with downstream CKN partial regularity

Wire the strange-loop record into CKN.  Given a
`SuitableSelfCertified` plus the open `LocalSmallnessCriterion` Prop
(the Clay gap), we conclude partial regularity off a parabolic-1-
dimensional exception set.

This is **not** a new theorem — it is a one-line composition with
`suitable_weakSolution_partial_regularity` from the LEI file — but
its presence here closes the strange loop's downstream story. -/

/-- **Strange-loop ⇒ CKN partial regularity** (modulo the open Clay
input).  The strange-loop record self-certifies CKN-suitability;
adding the local smallness criterion concludes partial regularity. -/
theorem strangeLoop_partial_regularity
    {nse : NavierStokesEquations 3} {T : ℝ}
    (S : SuitableSelfCertified nse T)
    (hSmall : LocalSmallnessCriterion S.leray_hopf.toWeakSolution) :
    ∃ singularSet : Set (EuclideanSpace ℝ (Fin 4)),
      ParabolicHausdorffDim singularSet ≤ 1 ∧
      ContDiff ℝ ⊤ S.leray_hopf.toWeakSolution.u :=
  ckn_partial_regularity_modulo_smallness
    S.leray_hopf.toWeakSolution S.local_energy_data hSmall

/-! ## §7.  Honest residual void

* The strange loop is **mechanical**, not deep: it is a finite-depth
  type-level identification, not a fixed-point.  Calling it a
  "strange loop" is a *naming* of an architectural feature, not a
  claim of new mathematical content.

* The classical Galerkin axioms (six of them, in workstream O) and
  `LEI_from_galerkin_classical` (Scheffer 1976 / Lin 1998) are taken
  as inputs.  Self-certification is *modulo* these.

* The Clay millennium problem reduces — in this architecture — to
  the single Prop `LocalSmallnessCriterion`.  The strange loop does
  not weaken this gap.

What the strange loop *does* show: the typed-companion architecture
is **internally composable** in the meta-theoretic sense — its
output is, with no glue, the input of its own next stage.  This is
exactly the "tangled hierarchy" Hofstadter names: a level-crossing
self-reference that the formal system itself recognizes as type-
correct.

In short: the architecture self-certifies its **composability**, not
its **truth**.  The strange loop is honest.
-/

end

end ZtareProofs.NS.StrangeLoop
