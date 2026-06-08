import Mathlib.Topology.UniformSpace.Ascoli
import Mathlib.Topology.UniformSpace.Equicontinuity
import Mathlib.Topology.UniformSpace.CompactConvergence
import Mathlib.Topology.MetricSpace.UniformConvergence
import Mathlib.Topology.ContinuousMap.Basic
import Mathlib.Topology.ContinuousMap.Bounded.Basic

/-!
# KRF compactness, step 2: the Arzelà–Ascoli extraction

This file is the **second piece** of the KRF compactness chain on Track-B.

**Classical statement.** Let `{u_n} ⊂ L²(ℝᵈ)` be a sequence which is

* uniformly L²-bounded:  `‖u_n‖₂ ≤ M`,
* tight:  for every `ε > 0` there is `R > 0` with
  `∫_{|x|>R} |u_n|² < ε` uniformly in `n`.

Fix `δ > 0` and let `ρ_δ` be a standard smooth mollifier of scale `δ`.
Then the mollified family

`f_n := ρ_δ * u_n`

is smooth and **uniformly bounded in `C¹`** (because `‖∂(ρ_δ * u_n)‖_∞ ≤
‖∂ρ_δ‖_∞ · ‖u_n‖_{L²} · ‖ρ_δ‖_{L²}^{0}` after Cauchy–Schwarz, with the
explicit constants depending only on `δ`).  A `C¹`-bounded family is
**equicontinuous** on every compact set, and pointwise-bounded.  The
Arzelà–Ascoli theorem then yields a subsequence that converges
**uniformly on compact subsets** of `ℝᵈ`.

This is exactly the abstract content of
`ArzelaAscoli.isCompact_closure_of_isClosedEmbedding` in Mathlib.

## What this file does

The full analytic facts (Cauchy–Schwarz on convolutions, smoothness of
`ρ_δ * u_n`, the explicit `C¹` bound) live in the *first* step of the
chain (`ns_trackb_krf_mollifier_rate.lean`).  Here we package the
**Arzelà–Ascoli step** in a form that is reusable, compositional with the
mollifier-rate step, and Mathlib-faithful.

We do this in two stages:

1. **`MollifiedFamilyHypotheses`** — a structure that records the three
   analytic outputs of the mollifier step:  continuity of each `f_n`,
   equicontinuity on every compact set, and a uniform pointwise bound.

2. **`arzelaAscoli_uniform_on_compacts_subseq`** — the conclusion: the
   sequence has a subsequence which converges in the topology of
   uniform convergence on compact sets, equivalently, the closure of
   the family is **compact** in `C(X, ℝ)` with the compact-open
   topology.  This is the form Mathlib actually proves; the
   "subsequence" form follows for a sequentially compact T₂ space.

A *fully discharged* version would import the rate step and feed its
output directly into stage (2).  Since the rate step is still in
progress, we leave the `MollifiedFamilyHypotheses` as the contract; the
file compiles unconditionally and exposes the precise `sorry`-free
Arzelà–Ascoli reduction.

## How this composes with the mollifier-rate step

Track B (`ns_trackb_krf_*`) is structured as:

```
[step 1] mollifier-rate:
  uniform L² bound + tightness + δ > 0
    ⟹  ρ_δ * u_n is C¹-bounded uniformly in n   (analytic content)

[step 2] this file (Arzelà–Ascoli):
  C¹-bounded uniformly + pointwise bounded
    ⟹  uniformly-convergent-on-compacts subsequence

[step 3] (future) limit identification:
  the limit is the KRF candidate; pass δ → 0 with the rate from step 1.
```

The interface between the steps is `MollifiedFamilyHypotheses`: step 1
produces it, this file consumes it.
-/

namespace ZtareProofs
namespace KRFArzelaAscoliStep

open Set Filter Topology UniformConvergence Function

universe u v

variable {X : Type u} [TopologicalSpace X]

/-- The analytic output of the **mollifier-rate step** that drives
Arzelà–Ascoli.

Given a sequence `f : ℕ → X → ℝ` (think `f n = ρ_δ * u_n` for the fixed
`δ`), we record exactly what is needed for the abstract
Arzelà–Ascoli extraction:

* `continuous`     — each member of the family is continuous;
* `equicontinuous` — the family is equicontinuous on every compact `K`;
* `pointwiseBdd`   — for every `x` the orbit `{f n x}` lies in a fixed
                     compact set (a uniform pointwise bound).

Both `equicontinuous` and `pointwiseBdd` are consequences of the
`C¹`-bound `‖∇ f n‖_∞ ≤ C(δ) M`, but we abstract over the proof
mechanism so that the Arzelà–Ascoli step does not depend on the precise
analytic packaging chosen by the rate step. -/
structure MollifiedFamilyHypotheses (f : ℕ → X → ℝ) : Prop where
  continuous     : ∀ n, Continuous (f n)
  equicontinuous : ∀ K : Set X, IsCompact K → EquicontinuousOn f K
  pointwiseBdd   : ∀ x : X, ∃ Q : Set ℝ, IsCompact Q ∧ ∀ n, f n x ∈ Q

/-- Build `MollifiedFamilyHypotheses` from the usual scalar pointwise
absolute-value bound.

The compact-range part of Arzelà-Ascoli is often produced analytically as
`∀ x, ∃ C, ∀ n, |f n x| ≤ C`.  This lemma packages that bound as the compact
interval `[-C, C]`, leaving continuity and compact-wise equicontinuity as the
only remaining analytic inputs. -/
theorem mollifiedFamilyHypotheses_of_pointwise_abs_bound
    {f : ℕ → X → ℝ}
    (hcont : ∀ n, Continuous (f n))
    (heq : ∀ K : Set X, IsCompact K → EquicontinuousOn f K)
    (hbound : ∀ x : X, ∃ C : ℝ, ∀ n, |f n x| ≤ C) :
    MollifiedFamilyHypotheses f := by
  refine ⟨hcont, heq, ?_⟩
  intro x
  rcases hbound x with ⟨C, hC⟩
  refine ⟨Set.Icc (-C) C, isCompact_Icc, ?_⟩
  intro n
  exact abs_le.mp (hC n)

/-- Build `MollifiedFamilyHypotheses` from compact-wise uniform Lipschitz
bounds and scalar pointwise bounds.

This is the formal shape expected from the mollifier step: a C¹ or convolution
estimate supplies, for each compact `K`, a common Lipschitz constant for all
members of the family on `K`; Mathlib turns that into uniform
equicontinuity, hence equicontinuity on `K`. -/
theorem mollifiedFamilyHypotheses_of_lipschitzOnWith_pointwise_abs_bound
    {Y : Type u} [PseudoMetricSpace Y]
    {f : ℕ → Y → ℝ}
    (hcont : ∀ n, Continuous (f n))
    (hlip :
      ∀ K : Set Y, IsCompact K →
        ∃ C : NNReal, ∀ n, LipschitzOnWith C (f n) K)
    (hbound : ∀ x : Y, ∃ C : ℝ, ∀ n, |f n x| ≤ C) :
    MollifiedFamilyHypotheses f :=
  mollifiedFamilyHypotheses_of_pointwise_abs_bound hcont
    (by
      intro K hK
      rcases hlip K hK with ⟨C, hC⟩
      exact (LipschitzOnWith.uniformEquicontinuousOn f C hC).equicontinuousOn)
    hbound

/-- The collection of compact sets used as the *covering family* for the
Arzelà–Ascoli theorem.  We take **all** compact subsets of `X`; this is
the natural choice for "uniform convergence on compact sets". -/
def 𝔖compact (X : Type u) [TopologicalSpace X] : Set (Set X) :=
  {K | IsCompact K}

lemma compact_of_mem_𝔖compact {K : Set X} (hK : K ∈ 𝔖compact X) :
    IsCompact K := hK

/-- **Arzelà–Ascoli step for the mollified KRF family.**

If `f : ℕ → X → ℝ` is continuous, equicontinuous on every compact set,
and pointwise contained in a fixed compact, then the family is
equicontinuous on every member of the covering family `𝔖compact X` and
the pointwise-bound hypothesis required by
`ArzelaAscoli.compactSpace_of_closed_inducing'` is satisfied.

This lemma packages the *input data* the Arzelà–Ascoli theorem
consumes; the actual extraction of a uniformly-convergent-on-compacts
subsequence is then a direct invocation of Mathlib. -/
theorem mollified_family_satisfies_ascoli_inputs
    {f : ℕ → X → ℝ} (H : MollifiedFamilyHypotheses f) :
    (∀ K ∈ 𝔖compact X, IsCompact K) ∧
    (∀ K ∈ 𝔖compact X, EquicontinuousOn f K) ∧
    (∀ K ∈ 𝔖compact X, ∀ x ∈ K, ∃ Q : Set ℝ, IsCompact Q ∧ ∀ n, f n x ∈ Q) := by
  refine ⟨?_, ?_, ?_⟩
  · intro K hK; exact hK
  · intro K hK; exact H.equicontinuous K hK
  · intro K _ x _; exact H.pointwiseBdd x

/--
**Conditional Arzelà–Ascoli extraction (subsequence form).**

This is the form most directly usable by the Track-B chain.

Given the analytic outputs of the mollifier-rate step, plus the
*pre-compactness conduit* `prec` that converts "equicontinuous +
pointwise-bounded" into "the family has a subsequence converging
uniformly on every compact set", we conclude the subsequence
extraction.

The conduit `prec` is supplied externally because the precise statement
of "uniform convergence on compact sets" depends on the type of the
codomain.  For `ℝ` and a metrizable `X`, the conduit is
`ArzelaAscoli.isCompact_closure_of_isClosedEmbedding` together with
sequential compactness of the closure; for the abstract
`X →ᵤ[𝔖compact X] ℝ` the conduit is the closed-embedding form.  We
abstract over this so that the lemma is **agnostic** to which Mathlib
packaging is in use.

When the rate step is finalized, the conduit is discharged once and for
all, and this lemma becomes the single black box that Track-B step 3
consumes.
-/
theorem arzelaAscoli_uniform_on_compacts_subseq
    {f : ℕ → X → ℝ} (H : MollifiedFamilyHypotheses f)
    (prec :
      (∀ K ∈ 𝔖compact X, EquicontinuousOn f K) →
      (∀ K ∈ 𝔖compact X, ∀ x ∈ K, ∃ Q : Set ℝ, IsCompact Q ∧ ∀ n, f n x ∈ Q) →
      ∃ (φ : ℕ → ℕ) (g : X → ℝ),
        StrictMono φ ∧ Continuous g ∧
        ∀ K : Set X, IsCompact K →
          TendstoUniformlyOn (fun n x => f (φ n) x) g atTop K) :
    ∃ (φ : ℕ → ℕ) (g : X → ℝ),
      StrictMono φ ∧ Continuous g ∧
      ∀ K : Set X, IsCompact K →
        TendstoUniformlyOn (fun n x => f (φ n) x) g atTop K := by
  obtain ⟨_, hEq, hPt⟩ := mollified_family_satisfies_ascoli_inputs H
  exact prec hEq hPt

/-- Compact closure of a sequence of continuous maps gives a subsequence that
converges uniformly on every compact set.

This discharges the purely sequential part of the Arzelà conduit: once Ascoli
has produced compactness of the closure in `C(X, ℝ)`, and once the compact-open
space is first-countable, the desired subsequence follows from
`IsCompact.tendsto_subseq'` and Mathlib's compact-open convergence bridge. -/
theorem continuousMap_subseq_tendstoUniformlyOn_of_compact_closure
    (F : ℕ → C(X, ℝ))
    [FirstCountableTopology C(X, ℝ)]
    (hcomp : IsCompact (closure (Set.range F))) :
    ∃ (φ : ℕ → ℕ) (g : X → ℝ),
      StrictMono φ ∧ Continuous g ∧
      ∀ K : Set X, IsCompact K →
        TendstoUniformlyOn (fun n x => F (φ n) x) g atTop K := by
  have hx : ∃ᶠ n in atTop, F n ∈ closure (Set.range F) := by
    exact Frequently.of_forall fun n => subset_closure ⟨n, rfl⟩
  rcases hcomp.tendsto_subseq' hx with ⟨g, _hg_mem, φ, hφ, hφ_tendsto⟩
  refine ⟨φ, g, hφ, g.continuous, ?_⟩
  exact (ContinuousMap.tendsto_iff_forall_isCompact_tendstoUniformlyOn.mp
    hφ_tendsto)

/-- A `MollifiedFamilyHypotheses` family has a uniformly-on-compacts
convergent subsequence once its continuous-map image has compact closure.

This is the source-shape form needed by the KRF files: the analytic work can
target compact closure of the actual mollified family in `C(X, ℝ)`, while this
bridge handles the sequence extraction and compact-open-to-uniform-on-compacts
conversion. -/
theorem mollifiedFamily_subseq_tendstoUniformlyOn_of_compact_closure
    {f : ℕ → X → ℝ} (H : MollifiedFamilyHypotheses f)
    [FirstCountableTopology C(X, ℝ)]
    (hcomp :
      IsCompact
        (closure
          (Set.range (fun n : ℕ =>
            ({ toFun := f n, continuous_toFun := H.continuous n } :
              C(X, ℝ)))))) :
    ∃ (φ : ℕ → ℕ) (g : X → ℝ),
      StrictMono φ ∧ Continuous g ∧
      ∀ K : Set X, IsCompact K →
        TendstoUniformlyOn (fun n x => f (φ n) x) g atTop K :=
  continuousMap_subseq_tendstoUniformlyOn_of_compact_closure
    (fun n : ℕ =>
      ({ toFun := f n, continuous_toFun := H.continuous n } : C(X, ℝ)))
    hcomp

/-- The bundled continuous-map embedding into the compact-convergence
`UniformOnFun` space is closed when the domain is compactly coherent. -/
theorem continuousMap_toUniformOnFunIsCompact_isClosedEmbedding
    [CompactlyCoherentSpace X] :
    IsClosedEmbedding
      (ContinuousMap.toUniformOnFunIsCompact :
        C(X, ℝ) → X →ᵤ[{K | IsCompact K}] ℝ) := by
  refine ⟨ContinuousMap.isUniformEmbedding_toUniformOnFunIsCompact.isEmbedding, ?_⟩
  rw [ContinuousMap.range_toUniformOnFunIsCompact]
  exact UniformOnFun.isClosed_setOf_continuous
    CompactlyCoherentSpace.isCoherentWith

/-- Mathlib's Arzelà-Ascoli theorem supplies compact closure for a
`MollifiedFamilyHypotheses` family on a compactly coherent domain.

This closes the abstract Ascoli compactness side of the KRF step.  The
concrete KRF file still has to prove that its actual mollified family satisfies
`MollifiedFamilyHypotheses`, and that the relevant continuous-map space is
first-countable when a sequence is extracted. -/
theorem mollifiedFamily_compact_closure_of_ascoli
    [CompactlyCoherentSpace X]
    {f : ℕ → X → ℝ} (H : MollifiedFamilyHypotheses f) :
    IsCompact
      (closure
        (Set.range (fun n : ℕ =>
          ({ toFun := f n, continuous_toFun := H.continuous n } :
            C(X, ℝ))))) := by
  let F : C(X, ℝ) → X → ℝ := fun g x => g x
  let s : Set C(X, ℝ) :=
    Set.range (fun n : ℕ =>
      ({ toFun := f n, continuous_toFun := H.continuous n } : C(X, ℝ)))
  have hcompact : ∀ K ∈ 𝔖compact X, IsCompact K := by
    intro K hK
    exact hK
  have hclemb :
      IsClosedEmbedding (UniformOnFun.ofFun (𝔖compact X) ∘ F) := by
    simpa [F, 𝔖compact, ContinuousMap.toUniformOnFunIsCompact] using
      (continuousMap_toUniformOnFunIsCompact_isClosedEmbedding (X := X))
  have heq :
      ∀ K ∈ 𝔖compact X,
        EquicontinuousOn (F ∘ ((↑) : s → C(X, ℝ))) K := by
    intro K hK
    let u : s → ℕ := fun i => Classical.choose i.property
    have hfamily : F ∘ ((↑) : s → C(X, ℝ)) = f ∘ u := by
      funext i x
      dsimp [F, u, s]
      have hi := Classical.choose_spec i.property
      have hfun :
          (({ toFun := f (Classical.choose i.property),
              continuous_toFun := H.continuous (Classical.choose i.property) } :
              C(X, ℝ)) : X → ℝ) = (i : C(X, ℝ)) :=
        congrArg DFunLike.coe hi
      exact (congrFun hfun x).symm
    rw [hfamily]
    exact (H.equicontinuous K hK).comp u
  have hpt :
      ∀ K ∈ 𝔖compact X, ∀ x ∈ K,
        ∃ Q, IsCompact Q ∧ ∀ i ∈ s, F i x ∈ Q := by
    intro K _ x _
    rcases H.pointwiseBdd x with ⟨Q, hQ, hQi⟩
    refine ⟨Q, hQ, ?_⟩
    intro i hi
    rcases hi with ⟨n, rfl⟩
    exact hQi n
  simpa [s] using
    (ArzelaAscoli.isCompact_closure_of_isClosedEmbedding
      (F := F) (𝔖 := 𝔖compact X) hcompact hclemb
      (s := s) heq hpt)

/-- Abstract Arzelà-Ascoli subsequence source from `MollifiedFamilyHypotheses`.

This combines Mathlib's Ascoli compact-closure theorem with the sequential
compact-open extraction bridge above.  The hypotheses are exactly the remaining
topological side conditions: compact coherence for closedness of the continuous
map embedding, and first-countability of `C(X, ℝ)` for subsequence extraction. -/
theorem mollifiedFamily_subseq_tendstoUniformlyOn_of_ascoli
    [CompactlyCoherentSpace X] [FirstCountableTopology C(X, ℝ)]
    {f : ℕ → X → ℝ} (H : MollifiedFamilyHypotheses f) :
    ∃ (φ : ℕ → ℕ) (g : X → ℝ),
      StrictMono φ ∧ Continuous g ∧
      ∀ K : Set X, IsCompact K →
        TendstoUniformlyOn (fun n x => f (φ n) x) g atTop K :=
  mollifiedFamily_subseq_tendstoUniformlyOn_of_compact_closure H
    (mollifiedFamily_compact_closure_of_ascoli H)

/-- **Specialization to ℝᵈ via Mathlib's Arzelà–Ascoli.**

For the actual Track-B substrate `X = EuclideanSpace ℝ (Fin d)` (or any
`σ`-compact metrizable space), the conduit `prec` of
`arzelaAscoli_uniform_on_compacts_subseq` is **not an axiom**: it is
proved by combining

* `ArzelaAscoli.isCompact_closure_of_isClosedEmbedding`
  (`Mathlib.Topology.UniformSpace.Ascoli`, line 471), giving compactness
  of the closure of `{f n}` in `X →ᵤ[𝔖] ℝ`;
* metrizability of that closure (since `X` is `σ`-compact and `ℝ` is
  metrizable, the compact-open topology on `C(X, ℝ)` is metrizable);
* `IsCompact.isSeqCompact` to extract a subsequence;
* the equivalence of convergence in `X →ᵤ[𝔖compact X] ℝ` with uniform
  convergence on every compact set.

The discharge of `prec` is the technical content of the upcoming
sub-step `ns_trackb_krf_arzela_ascoli_metrization.lean`; once shipped,
the call site below becomes a one-liner.

Until then, this corollary is stated **conditionally** on `prec`. -/
theorem krf_arzelaAscoli_step
    {f : ℕ → X → ℝ} (H : MollifiedFamilyHypotheses f)
    (prec :
      (∀ K ∈ 𝔖compact X, EquicontinuousOn f K) →
      (∀ K ∈ 𝔖compact X, ∀ x ∈ K, ∃ Q : Set ℝ, IsCompact Q ∧ ∀ n, f n x ∈ Q) →
      ∃ (φ : ℕ → ℕ) (g : X → ℝ),
        StrictMono φ ∧ Continuous g ∧
        ∀ K : Set X, IsCompact K →
          TendstoUniformlyOn (fun n x => f (φ n) x) g atTop K) :
    ∃ (φ : ℕ → ℕ) (g : X → ℝ),
      StrictMono φ ∧ Continuous g ∧
      ∀ K : Set X, IsCompact K →
        TendstoUniformlyOn (fun n x => f (φ n) x) g atTop K :=
  arzelaAscoli_uniform_on_compacts_subseq H prec

/-!
## Sorry inventory and missing-Mathlib-lemma map

This file is fully `sorry`-free.  Two named gaps remain on the *consumer*
side, both of which discharge to existing Mathlib content:

* **GAP-A: mollifier C¹ bound ⟹ `MollifiedFamilyHypotheses`.**
  Produced by step 1 of the chain (`ns_trackb_krf_mollifier_rate.lean`).
  The Mathlib bricks are
  `MeasureTheory.convolution`, `ContDiffBump`, and
  `ContDiff.lipschitzOnWith` for the equicontinuity reduction.

* **GAP-B: discharge of the conduit `prec` for `X = EuclideanSpace ℝ d`.**
  Mathlib bricks:
    - `ArzelaAscoli.isCompact_closure_of_isClosedEmbedding`
      (`Mathlib.Topology.UniformSpace.Ascoli` :471),
    - `ContinuousMap.isCompact_iff_seqCompact` (the compact-open topology
      on `C(X,ℝ)` is metrizable when `X` is `σ`-compact),
    - `tendstoUniformlyOn_iff_tendsto` (for translating
      `X →ᵤ[𝔖] ℝ`-convergence to `TendstoUniformlyOn`).

Once GAP-B is shipped, `krf_arzelaAscoli_step` becomes
*unconditional* on `EuclideanSpace ℝ d`; once GAP-A is shipped, the full
KRF compactness statement follows by composition with this file. -/

end KRFArzelaAscoliStep
end ZtareProofs
