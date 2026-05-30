import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Function.UnifTight
import Mathlib.MeasureTheory.Function.LpSpace.Basic
import Mathlib.MeasureTheory.Function.LpSpace.Complete
import Mathlib.MeasureTheory.Function.ConvergenceInMeasure
import Mathlib.Topology.MetricSpace.Sequences
import ZtareProofs.ns_trackb_aubin_lions_stub

-- ============================================================================
-- TODO companion-file imports (workstream pieces 1, 2, 3).
--
-- These three files are being authored concurrently by sibling agents. They
-- are not yet present on disk; this assembly file is the architectural
-- composition target where they land. Each commented import names the
-- public lemma this file consumes from that piece.
--
-- import ZtareProofs.ns_trackb_krf_mollifier_rate
--   -- exposes: `krf_mollifier_l2_rate` :
--   --   under `KolmogorovRieszFrechetData`, for every ε > 0 there exists δ > 0
--   --   such that the L² distance between `u_n` and its δ-mollification
--   --   `ρ_δ * u_n` is < ε for ALL n.
--
-- import ZtareProofs.ns_trackb_krf_arzela_ascoli_step
--   -- exposes: `krf_arzela_ascoli_uniform_subseq` :
--   --   given `KolmogorovRieszFrechetData` and a fixed mollifier scale δ > 0,
--   --   on each compact set `K ⊂ ℝⁿ` the mollified family
--   --   `(ρ_δ * u_n)|_K` is equicontinuous + uniformly bounded, so by
--   --   Arzelà–Ascoli admits a subsequence converging uniformly on K.
--
-- import ZtareProofs.ns_trackb_krf_cantor_diagonal
--   -- exposes: `krf_cantor_diagonal_extraction` :
--   --   given a doubly-indexed family of subsequences (one per scale-δ_k)
--   --   each a sub-subsequence of the previous, produce a single diagonal
--   --   subsequence of `u_n` that is L²-Cauchy on every compact and at every
--   --   scale; combine with the mollifier rate to get a global L²-Cauchy
--   --   subsequence of the original `u_n`, hence convergent (`Lp.completeSpace`).
-- ============================================================================

/-!
# KRF master compactness assembly (NS Track B residual void closer)

This file assembles the **Kolmogorov–Riesz–Fréchet (KRF) compactness theorem**
from three concurrently-authored workstream pieces:

  1. `ns_trackb_krf_mollifier_rate` — mollifier-rate estimate.
  2. `ns_trackb_krf_arzela_ascoli_step` — Arzelà–Ascoli on mollified sequences.
  3. `ns_trackb_krf_cantor_diagonal` — Cantor diagonal extraction.

Composition strategy (classical, Brezis FA Ch. 4 / Hanche-Olsen–Holden 2010):

  (S0) Cover `ℝⁿ` (or here, `[0,T]` for the time-only specialization used
       inside `KolmogorovRieszFrechetData` from `ns_trackb_aubin_lions_stub`)
       with countably many compact sets `K_j ↑ ℝⁿ`.

  (S1) For each scale `δ_k = 1/k`, apply the **mollifier-rate** estimate
       (piece 1) to bound `‖ρ_{δ_k} * u_n − u_n‖_{L²} < 1/k` uniformly in n.

  (S2) For each scale `δ_k` and each compact `K_j`, apply
       **Arzelà–Ascoli** (piece 2) to extract a uniformly-convergent
       sub-subsequence of `(ρ_{δ_k} * u_n)|_{K_j}`.

  (S3) **Cantor diagonal** (piece 3) across `(j, k) → ∞` combines the
       (S2) family into a single subsequence `u_{φ(n)}` that is L²-Cauchy
       on every compact at every scale.

  (S4) The mollifier rate (piece 1) plus tightness (KRF2 in the data)
       upgrades L²-Cauchy-on-compacts-at-scale to L²-Cauchy globally,
       hence convergent in L² (`Lp.completeSpace`).

  (S5) Mathlib's `MeasureTheory.tendstoInMeasure_of_tendsto_eLpNorm`
       plus `MeasureTheory.TendstoInMeasure.exists_seq_tendsto_ae`
       upgrades L²-convergence-along-a-subseq to a.e. convergence
       along a further sub-subsequence.

The a.e. output matches the named sorry `krf_subseq_ae_of_translation` in
`ns_trackb_aubin_lions_stub.lean`, but it is not a consequence of the current
integral-form KRF surface alone.  Mathlib's available route consumes
`eLpNorm` convergence plus the corresponding measurability/integrability
evidence; the current `CantorDiagonalOutput` still needs a source-shape bridge
to the positive `CantorDiagonalELpNormOutput` contract below.  The sibling
`vitali_to_integral` sorry in the stub is also source-shape work, not blind
plumbing.

## Status

This file is the SKELETON of the assembly. It compiles in
Mathlib v4.30.0-rc2 with named sorries for the three KRF pieces and one
source-shape conversion into the `eLpNorm` currency consumed by Mathlib's
convergence-in-measure route. When pieces 1/2/3 land, their imports are local
rewrites; the a.e. theorem additionally needs the source-shape bridge.

## Sorry inventory (this file)

  S-PIECE-1  : depends on `ns_trackb_krf_mollifier_rate`  (workstream 1)
  S-PIECE-2  : depends on `ns_trackb_krf_arzela_ascoli_step` (workstream 2)
  S-PIECE-3  : depends on `ns_trackb_krf_cantor_diagonal` (workstream 3)
  S-COMPOSE  : the composition glue tying S-PIECE-{1,2,3} into the final
               a.e. convergence statement; not blocked on any external
               theorem, closes by `obtain` chaining once 1/2/3 land.
-/

namespace ZtareProofs.NS.KRFMaster

noncomputable section

universe v

open MeasureTheory Filter Topology
open scoped ENNReal

open ZtareProofs.NS.AubinLions

/-! ## §1. Companion abbreviations for the three workstream outputs.

We declare the EXPECTED public signature each workstream piece will land
with, as `Prop` aliases. When pieces 1/2/3 import-replace these aliases,
the assembly proof closes mechanically. -/

/-- **Workstream 1 (mollifier rate) — expected output signature.**

For every `ε > 0` there is a mollification scale `δ > 0` such that
the L² distance between `u_n` and `u_n` smoothed at scale `δ` is < ε
UNIFORMLY in n.

(In the time-only specialization used by `KolmogorovRieszFrechetData`,
the "mollification" is convolution against a smooth bump in the time
variable; the rate ω(δ) is driven by `_D.unif_translation`.) -/
def MollifierRateOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∀ ε : ℝ, 0 < ε → ∃ δ : ℝ, 0 < δ ∧
    ∀ n : ℕ,
      -- |‖ρ_δ * u_n − u_n‖_{L²([0,T])}|² < ε
      -- expressed via the integral form to match `KRFConclusion`
      ∃ smoothed : ℝ → B,
        StronglyMeasurable smoothed ∧
        ∫ t in Set.Icc 0 T, ‖smoothed t - u n t‖^2 < ε

/-- **Workstream 2 (Arzelà–Ascoli at fixed scale) — expected output.**

At every fixed mollifier scale `δ > 0`, the family `(ρ_δ * u_n)`
restricted to a compact `K ⊂ [0,T]` admits a sub-subsequence converging
uniformly on K. -/
def ArzelaAscoliOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∀ δ : ℝ, 0 < δ →
    ∀ (K : Set ℝ), IsCompact K → K ⊆ Set.Icc 0 T →
      ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
        ∃ (gK : ℝ → B),
          TendstoUniformlyOn (fun n t => u (ψ n) t) gK atTop K

/-- **Workstream 3 (Cantor diagonal) — expected output.**

Given a chain of nested sub-subsequences (one per pair `(j,k)` of
compact-and-scale indices), the diagonal subsequence converges
uniformly on every compact at every scale, AND when combined with the
mollifier rate it converges in L² globally. -/
def CantorDiagonalOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∃ (φ : ℕ → ℕ), StrictMono φ ∧
  ∃ (uInf : ℝ → B),
    StronglyMeasurable uInf ∧
    Tendsto
      (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖^2)
      atTop (𝓝 0)

/-- Source shape needed by Mathlib's convergence-in-measure route.

This is the same KRF/Cantor output surface as `CantorDiagonalOutput`, but
stated in the `eLpNorm` currency consumed by
`MeasureTheory.tendstoInMeasure_of_tendsto_eLpNorm`.  It is intentionally a
separate positive target rather than a weakening of the existing integral
surface: the remaining analytic work is the source-shape bridge from the
current integral output to this form, or a direct KRF construction of this
form. -/
def CantorDiagonalELpNormOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∃ (φ : ℕ → ℕ), StrictMono φ ∧
  ∃ (uInf : ℝ → B),
    StronglyMeasurable uInf ∧
    Tendsto
      (fun n =>
        eLpNorm
          (fun t => u (φ n) t - uInf t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
      atTop (𝓝 0)

/-- Tail-finite KRF/Cantor source contract.

This is the same diagonal output as `CantorDiagonalOutput`, augmented with the
exact finite-energy witness needed to identify the real integral convergence
with Mathlib's `eLpNorm` convergence on a tail.  The tail shape is deliberate:
finite prefixes do not affect the convergence target consumed by the row-20
a.e. extraction. -/
def CantorDiagonalTailFiniteEnergyOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∃ (φ : ℕ → ℕ), StrictMono φ ∧
  ∃ (uInf : ℝ → B),
    StronglyMeasurable uInf ∧
    Tendsto
      (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖^2)
      atTop (𝓝 0) ∧
    ∀ᶠ n in atTop,
      (∫⁻ t,
        (‖u (φ n) t - uInf t‖ₑ) ^ ((2 : ENNReal).toReal)
          ∂(MeasureTheory.volume.restrict (Set.Icc 0 T))) < ∞

/-! ## §2. Three named-sorry hypotheses, one per workstream piece.

Each is a Prop that the corresponding sibling-agent file will provide
(under the same hypothesis bundle `KolmogorovRieszFrechetData`). When
the workstream files land, each `axiom` here is replaced by the
imported theorem from that file. -/

/-- **S-PIECE-1.** Workstream 1 will provide this from
`ns_trackb_krf_mollifier_rate`.

When piece 1 lands, replace the body of this theorem with
`exact ZtareProofs.NS.KRFMollifier.krf_mollifier_l2_rate D` (or
the name the sibling agent ships). -/
theorem mollifier_rate_from_piece1
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (_D : KolmogorovRieszFrechetData B T u) :
    MollifierRateOutput T u := by
  -- BLOCKED on workstream 1 (`ns_trackb_krf_mollifier_rate`).
  -- The mollifier-rate estimate `‖ρ_δ * u_n - u_n‖_{L²} ≤ ω(δ)` driven
  -- by `_D.unif_translation`. Standard Brezis FA Prop. 4.21 argument.
  sorry

/-- **S-PIECE-2.** Workstream 2 will provide this from
`ns_trackb_krf_arzela_ascoli_step`.

When piece 2 lands, replace the body of this theorem with
`exact ZtareProofs.NS.KRFArzelaAscoli.krf_arzela_ascoli_uniform_subseq D`. -/
theorem arzela_ascoli_from_piece2
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (_D : KolmogorovRieszFrechetData B T u) :
    ArzelaAscoliOutput T u := by
  -- BLOCKED on workstream 2 (`ns_trackb_krf_arzela_ascoli_step`).
  -- For each fixed scale δ > 0, the mollified family `(ρ_δ * u_n)` is
  -- equicontinuous (modulus from `ρ_δ`'s gradient) + uniformly bounded
  -- (from `_D.unif_l2_bound` + Cauchy–Schwarz against `ρ_δ`); on each
  -- compact `K`, Arzelà–Ascoli (`isCompact_iff_totallyBounded_isComplete`
  -- + `Mathlib.Topology.UniformSpace.Compact`) supplies a uniformly
  -- convergent sub-subsequence.
  sorry

/-- **S-PIECE-3.** Workstream 3 will provide this from
`ns_trackb_krf_cantor_diagonal`.

When piece 3 lands, replace the body of this theorem with
`exact ZtareProofs.NS.KRFCantorDiagonal.krf_cantor_diagonal_extraction
   D (mollifier_rate_from_piece1 D) (arzela_ascoli_from_piece2 D)`. -/
theorem cantor_diagonal_from_piece3
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (_D : KolmogorovRieszFrechetData B T u)
    (_rate : MollifierRateOutput T u)
    (_aa : ArzelaAscoliOutput T u) :
    CantorDiagonalOutput T u := by
  -- BLOCKED on workstream 3 (`ns_trackb_krf_cantor_diagonal`).
  -- Cover `[0,T]` by an exhausting sequence of compacts (here trivially
  -- `[0,T]` itself, so the "Cantor across compacts" axis collapses; the
  -- Cantor across scales `δ_k = 1/k` is nontrivial). Diagonalize in k
  -- to produce a single subsequence `φ` such that `(ρ_{δ_k} * u_{φ(n)})`
  -- converges uniformly for every k. The mollifier rate `_rate` then
  -- upgrades uniform-on-compact convergence to L²-Cauchy of `u_{φ(n)}`
  -- itself; `Lp.completeSpace` produces the limit `uInf`.
  sorry

/-! ## §3. Master KRF assembly theorem.

Composes pieces 1, 2, 3 into the conclusion `KRFConclusion T u`.

This is the master statement promised by the workstream charter. It
is a strict generalization of `kolmogorov_riesz_frechet_compactness`
in `ns_trackb_aubin_lions_stub.lean` (same conclusion, same hypotheses). -/

/-- **Master KRF compactness, integral form.**

From a `KolmogorovRieszFrechetData` bundle (KRF1 uniform L² bound +
KRF2 uniform tightness + KRF3 uniform translation continuity), there
is a subsequence `u_{φ(n)}` and a limit `uInf ∈ L²([0,T]; B)` such
that `∫ ‖u_{φ(n)} − uInf‖² → 0`.

Closes by composing the three workstream pieces. -/
theorem krf_master_compactness
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u) :
    KRFConclusion T u := by
  -- (S1) mollifier rate (workstream 1)
  have hRate : MollifierRateOutput T u := mollifier_rate_from_piece1 D
  -- (S2) Arzelà–Ascoli at fixed scale (workstream 2)
  have hAA : ArzelaAscoliOutput T u := arzela_ascoli_from_piece2 D
  -- (S3) Cantor diagonal across scales (workstream 3)
  have hDiag : CantorDiagonalOutput T u :=
    cantor_diagonal_from_piece3 D hRate hAA
  -- (S4) Repackage the diagonal output as `KRFConclusion`.
  obtain ⟨φ, hφ_mono, uInf, _hMeas, hConv⟩ := hDiag
  exact ⟨φ, hφ_mono, uInf, hConv⟩

/--
If the KRF extraction source is stated in the currency Mathlib consumes,
namely `eLpNorm` convergence on the restricted interval measure, then the
a.e. subsequence conclusion is immediate by convergence in measure plus the
standard subsequence extraction theorem.

This theorem is the source-shape repair target for the row-20 `sorry`: the
open work is not the final a.e. extraction, but producing this `eLpNorm`
convergence (or an equivalent `MemLp` bridge) upstream.
-/
theorem ae_subsequence_of_eLpNorm_convergence
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ_mono : StrictMono φ) (uInf : ℝ → B)
    (hMeas_u : ∀ n, StronglyMeasurable (u n))
    (hMeas_inf : StronglyMeasurable uInf)
    (hLp :
      Tendsto
        (fun n =>
          eLpNorm
            (fun t => u (φ n) t - uInf t)
            2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
        atTop (𝓝 0)) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf' : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf' t)) := by
  let μ := MeasureTheory.volume.restrict (Set.Icc 0 T)
  have hf_meas : ∀ n, AEStronglyMeasurable (fun t => u (φ n) t) μ := by
    intro n
    exact (hMeas_u (φ n)).aestronglyMeasurable
  have hg_meas : AEStronglyMeasurable uInf μ :=
    hMeas_inf.aestronglyMeasurable
  have hInMeasure :
      TendstoInMeasure μ (fun n t => u (φ n) t) atTop uInf := by
    have hp : (2 : ENNReal) ≠ 0 := by norm_num
    exact tendstoInMeasure_of_tendsto_eLpNorm hp hf_meas hg_meas hLp
  obtain ⟨χ, hχ_mono, hχ_ae⟩ := hInMeasure.exists_seq_tendsto_ae
  refine ⟨φ ∘ χ, hφ_mono.comp hχ_mono, uInf, ?_⟩
  exact hχ_ae

/-- The positive KRF/Cantor source contract is already sufficient for the
row-20 a.e.-subsequence extraction.  The remaining work is therefore upstream:
produce `CantorDiagonalELpNormOutput`, or prove a source-shape theorem from the
current integral-form output to this form under the needed `MemLp` evidence. -/
theorem ae_subsequence_of_cantor_eLpNorm_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalELpNormOutput T u) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) := by
  rcases hOut with ⟨φ, hφ_mono, uInf, hMeas, hLp⟩
  exact ae_subsequence_of_eLpNorm_convergence
    φ hφ_mono uInf D.meas_u hMeas hLp

/-- Integral-form KRF convergence converts to Mathlib's `eLpNorm` currency
once the missing `MemLp` evidence for each difference is explicit.

This theorem isolates the remaining source-shape debt precisely: the bridge
from `∫ ‖u (φ n) - uInf‖² → 0` to `eLpNorm → 0` is not the obstruction;
the obstruction is producing `MemLp (u (φ n) - uInf) 2` on the restricted
interval measure from the upstream KRF/Cantor construction. -/
theorem eLpNorm_convergence_of_integral_convergence_with_memLp
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (uInf : ℝ → B)
    (hMem :
      ∀ n,
        MemLp
          (fun t => u (φ n) t - uInf t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hIntegral :
      Tendsto
        (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
        atTop (𝓝 0)) :
    Tendsto
      (fun n =>
        eLpNorm
          (fun t => u (φ n) t - uInf t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
      atTop (𝓝 0) := by
  have hp0 : (2 : ENNReal) ≠ 0 := by norm_num
  have hpInf : (2 : ENNReal) ≠ ⊤ := by norm_num
  have hEq :
      (fun n =>
        eLpNorm
          (fun t => u (φ n) t - uInf t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
      =
      (fun n =>
        ENNReal.ofReal
          ((∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ (2 : ℝ))
            ^ ((1 : ℝ) / 2))) := by
    funext n
    rw [MemLp.eLpNorm_eq_integral_rpow_norm hp0 hpInf (hMem n)]
    norm_num
  rw [hEq]
  have hPow :
      Tendsto
        (fun n =>
          (∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ (2 : ℝ))
            ^ ((1 : ℝ) / 2))
        atTop (𝓝 0) := by
    simpa using
      ((continuousAt_id.rpow_const
          (Or.inr (by positivity : (0 : ℝ) ≤ (1 / 2 : ℝ)))).tendsto.comp
        hIntegral)
  simpa using (ENNReal.continuous_ofReal.tendsto 0).comp hPow

/-- The integral-to-`eLpNorm` bridge only needs `MemLp` on a tail of the
selected subsequence, since `Tendsto` ignores finite prefixes. -/
theorem eLpNorm_convergence_of_integral_convergence_eventually_memLp
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (uInf : ℝ → B)
    (hMem :
      ∀ᶠ n in atTop,
        MemLp
          (fun t => u (φ n) t - uInf t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hIntegral :
      Tendsto
        (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
        atTop (𝓝 0)) :
    Tendsto
      (fun n =>
        eLpNorm
          (fun t => u (φ n) t - uInf t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
      atTop (𝓝 0) := by
  have hp0 : (2 : ENNReal) ≠ 0 := by norm_num
  have hpInf : (2 : ENNReal) ≠ ⊤ := by norm_num
  have hPow :
      Tendsto
        (fun n =>
          (∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ (2 : ℝ))
            ^ ((1 : ℝ) / 2))
        atTop (𝓝 0) := by
    simpa using
      ((continuousAt_id.rpow_const
          (Or.inr (by positivity : (0 : ℝ) ≤ (1 / 2 : ℝ)))).tendsto.comp
        hIntegral)
  have hRhs :
      Tendsto
        (fun n =>
          ENNReal.ofReal
            ((∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ (2 : ℝ))
              ^ ((1 : ℝ) / 2)))
        atTop (𝓝 0) := by
    simpa using (ENNReal.continuous_ofReal.tendsto 0).comp hPow
  refine hRhs.congr' ?_
  filter_upwards [hMem] with n hn
  rw [MemLp.eLpNorm_eq_integral_rpow_norm hp0 hpInf hn]
  norm_num

/-- A finite `lintegral` square-norm witness is exactly enough to build the
`MemLp 2` evidence needed by the `eLpNorm` bridge.

This isolates the next upstream KRF/Cantor obligation in a Mathlib-native
form: provide a.e. strong measurability of the difference and finiteness of
the squared-enorm `lintegral` on the restricted interval measure. -/
theorem memLp_two_of_aestronglyMeasurable_lintegral_enorm_sq_lt_top
    {α : Type*} [MeasurableSpace α]
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    {μ : Measure α} {f : α → B}
    (hf : AEStronglyMeasurable f μ)
    (hFinite : (∫⁻ t, (‖f t‖ₑ) ^ ((2 : ENNReal).toReal) ∂μ) < ∞) :
    MemLp f 2 μ := by
  refine ⟨hf, ?_⟩
  exact (eLpNorm_lt_top_iff_lintegral_rpow_enorm_lt_top
    (by norm_num : (2 : ENNReal) ≠ 0)
    (by norm_num : (2 : ENNReal) ≠ ⊤)).2 hFinite

/-- The current integral-form Cantor output upgrades to the positive
`eLpNorm` source contract as soon as the KRF construction supplies the missing
`MemLp` evidence for the difference sequence.

The hypothesis is deliberately explicit rather than hidden in an axiom: it is
the exact witness the upstream KRF/Cantor source must produce next. -/
theorem cantor_integral_output_to_eLpNorm_output_with_memLp
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : CantorDiagonalOutput T u)
    (hMem :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ n,
          MemLp
            (fun t => u (φ n) t - uInf t)
            2 (MeasureTheory.volume.restrict (Set.Icc 0 T))) :
    CantorDiagonalELpNormOutput T u := by
  rcases hOut with ⟨φ, hφ, uInf, hMeas, hIntegral⟩
  refine ⟨φ, hφ, uInf, hMeas, ?_⟩
  exact eLpNorm_convergence_of_integral_convergence_with_memLp
    φ uInf (hMem φ uInf hφ hMeas hIntegral) hIntegral

/-- The same upgrade stated one layer closer to the analytic source:
`CantorDiagonalOutput` plus a.e. strong measurability and finite squared-enorm
`lintegral` witnesses for each difference gives the `eLpNorm` output.

This is the bridge to target before attempting the row-20 `sorry` again. -/
theorem cantor_integral_output_to_eLpNorm_output_with_lintegral_witness
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : CantorDiagonalOutput T u)
    (hAEMeas :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ n,
          AEStronglyMeasurable
            (fun t => u (φ n) t - uInf t)
            (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hFinite :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ n,
          (∫⁻ t,
            (‖u (φ n) t - uInf t‖ₑ) ^ ((2 : ENNReal).toReal)
              ∂(MeasureTheory.volume.restrict (Set.Icc 0 T))) < ∞) :
    CantorDiagonalELpNormOutput T u := by
  refine cantor_integral_output_to_eLpNorm_output_with_memLp hOut ?_
  intro φ uInf hφ hMeas hIntegral n
  exact memLp_two_of_aestronglyMeasurable_lintegral_enorm_sq_lt_top
    (hAEMeas φ uInf hφ hMeas hIntegral n)
    (hFinite φ uInf hφ hMeas hIntegral n)

/-- Under the existing KRF measurability hypotheses, the `lintegral` witness is
the only remaining source datum needed to upgrade the current integral-form
Cantor output to the `eLpNorm` source contract.

The a.e. strong measurability of each difference follows from `D.meas_u` and
the `StronglyMeasurable uInf` field already present in `CantorDiagonalOutput`.
-/
theorem cantor_integral_output_to_eLpNorm_output_with_lintegral_finite_witness
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hFinite :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ n,
          (∫⁻ t,
            (‖u (φ n) t - uInf t‖ₑ) ^ ((2 : ENNReal).toReal)
              ∂(MeasureTheory.volume.restrict (Set.Icc 0 T))) < ∞) :
    CantorDiagonalELpNormOutput T u := by
  refine cantor_integral_output_to_eLpNorm_output_with_lintegral_witness hOut ?_ hFinite
  intro φ uInf _hφ hMeas _hIntegral n
  exact ((D.meas_u (φ n)).sub hMeas).aestronglyMeasurable

/-- Tail-finite version of the source bridge.  The upstream construction only
has to supply finite squared-enorm `lintegral` witnesses eventually along the
selected subsequence; finite prefixes are irrelevant to the target `Tendsto`. -/
theorem cantor_integral_output_to_eLpNorm_output_with_eventually_lintegral_finite_witness
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hFinite :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ᶠ n in atTop,
          (∫⁻ t,
            (‖u (φ n) t - uInf t‖ₑ) ^ ((2 : ENNReal).toReal)
              ∂(MeasureTheory.volume.restrict (Set.Icc 0 T))) < ∞) :
    CantorDiagonalELpNormOutput T u := by
  rcases hOut with ⟨φ, hφ, uInf, hMeas, hIntegral⟩
  refine ⟨φ, hφ, uInf, hMeas, ?_⟩
  refine eLpNorm_convergence_of_integral_convergence_eventually_memLp φ uInf ?_ hIntegral
  filter_upwards [hFinite φ uInf hφ hMeas hIntegral] with n hn
  exact memLp_two_of_aestronglyMeasurable_lintegral_enorm_sq_lt_top
    (((D.meas_u (φ n)).sub hMeas).aestronglyMeasurable)
    hn

/-- The named tail-finite KRF/Cantor source contract upgrades directly to the
`eLpNorm` source contract consumed by Mathlib's convergence-in-measure route.

This is the current positive row-20 closure interface: the upstream workstream
can target `CantorDiagonalTailFiniteEnergyOutput` and then reuse the checked
downstream extraction without restating the `MemLp`/`lintegral` plumbing. -/
theorem cantor_tail_finite_energy_output_to_eLpNorm_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalTailFiniteEnergyOutput T u) :
    CantorDiagonalELpNormOutput T u := by
  rcases hOut with ⟨φ, hφ, uInf, hMeas, hIntegral, hFinite⟩
  refine ⟨φ, hφ, uInf, hMeas, ?_⟩
  refine eLpNorm_convergence_of_integral_convergence_eventually_memLp φ uInf ?_ hIntegral
  filter_upwards [hFinite] with n hn
  exact memLp_two_of_aestronglyMeasurable_lintegral_enorm_sq_lt_top
    (((D.meas_u (φ n)).sub hMeas).aestronglyMeasurable)
    hn

/-- A standard `MemLp` source surface is enough to build the tail-finite
energy Cantor contract.

This moves the upstream row-20 obligation one step closer to the classical
KRF proof: show the selected functions are in `L²` on the restricted interval
and reconstruct the diagonal limit as an `L²` function, then the finite
squared-enorm `lintegral` witness for the difference follows by `MemLp.sub`.
-/
theorem cantor_integral_output_to_tail_finite_energy_output_with_memLp_sources
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : CantorDiagonalOutput T u)
    (hMem_u :
      ∀ n,
        MemLp (u n) 2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hMem_inf :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        MemLp uInf 2 (MeasureTheory.volume.restrict (Set.Icc 0 T))) :
    CantorDiagonalTailFiniteEnergyOutput T u := by
  rcases hOut with ⟨φ, hφ, uInf, hMeas, hIntegral⟩
  refine ⟨φ, hφ, uInf, hMeas, hIntegral, ?_⟩
  have hInf : MemLp uInf 2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) :=
    hMem_inf φ uInf hφ hMeas hIntegral
  filter_upwards with n
  have hDiff :
      MemLp
        (fun t => u (φ n) t - uInf t)
        2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) :=
    (hMem_u (φ n)).sub hInf
  exact (eLpNorm_lt_top_iff_lintegral_rpow_enorm_lt_top
    (by norm_num : (2 : ENNReal) ≠ 0)
    (by norm_num : (2 : ENNReal) ≠ ⊤)).1 hDiff.2

/-- If the indicator-restricted function is in `L²` over the ambient measure,
then the original function is in `L²` over the restricted measure. -/
theorem memLp_restrict_of_indicator_memLp
    {α : Type*} [MeasurableSpace α]
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {μ : Measure α} {s : Set α} (hs : MeasurableSet s) {f : α → B}
    (hf : MemLp (s.indicator f) 2 μ) :
    MemLp f 2 (μ.restrict s) :=
  MemLp.ae_eq (indicator_ae_eq_restrict hs) (hf.restrict s)

/-- A `UniformIntegrable` indicator source supplies the sequence-side `MemLp`
evidence needed by the tail-finite energy bridge.

The current KRF data carries `UnifIntegrable`; this theorem records the precise
positive strengthening that would discharge the selected-function half of the
row-20 source contract without touching the limit-side Fatou reconstruction. -/
theorem restricted_memLp_of_uniformIntegrable_indicator
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hUI :
      UniformIntegrable
        (fun n => Set.indicator (Set.Icc 0 T) (u n))
        2 MeasureTheory.volume) :
    ∀ n, MemLp (u n) 2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) := by
  intro n
  exact memLp_restrict_of_indicator_memLp (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))
    (hUI.memLp n)

/-- Limit-side `MemLp` reconstruction from a.e. convergence plus an eventual
`eLpNorm` bound.

This is the Fatou/Vitali-shaped source theorem surfaced by the PDE workbench:
to prove the diagonal limit belongs to `L²`, it is enough to show that the
candidate limit is the a.e. limit of the selected family and that the selected
family has an eventually finite `eLpNorm` bound. -/
theorem memLp_limit_of_ae_tendsto_eLpNorm_bound
    {α : Type*} [MeasurableSpace α]
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {μ : Measure α} {ι : Type*} {l : Filter ι} [NeBot l] [IsCountablyGenerated l]
    {f : ι → α → B} {g : α → B} {C : ℝ≥0∞}
    (hg : AEStronglyMeasurable g μ)
    (hBound : ∀ᶠ n in l, eLpNorm (f n) 2 μ ≤ C)
    (hC : C < ∞)
    (hf : ∀ n, AEStronglyMeasurable (f n) μ)
    (hTendsto : ∀ᵐ x ∂μ, Tendsto (fun n => f n x) l (𝓝 (g x))) :
    MemLp g 2 μ :=
  ⟨hg, lt_of_le_of_lt (Lp.eLpNorm_le_of_ae_tendsto hBound hf hTendsto) hC⟩

/-- With a `UniformIntegrable` indicator source, the row-20 source contract is
reduced to the limit-side `MemLp` reconstruction. -/
theorem cantor_integral_output_to_tail_finite_energy_output_with_uniformIntegrable_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : CantorDiagonalOutput T u)
    (hUI :
      UniformIntegrable
        (fun n => Set.indicator (Set.Icc 0 T) (u n))
        2 MeasureTheory.volume)
    (hMem_inf :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        MemLp uInf 2 (MeasureTheory.volume.restrict (Set.Icc 0 T))) :
    CantorDiagonalTailFiniteEnergyOutput T u :=
  cantor_integral_output_to_tail_finite_energy_output_with_memLp_sources
    hOut (restricted_memLp_of_uniformIntegrable_indicator hUI) hMem_inf

/-- Once the upstream diagonal construction supplies the tail-finite energy
source contract, the row-20 a.e.-subsequence conclusion follows by the checked
`eLpNorm` bridge and Mathlib's convergence-in-measure subsequence extraction. -/
theorem ae_subsequence_of_cantor_tail_finite_energy_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalTailFiniteEnergyOutput T u) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_cantor_eLpNorm_output D
    (cantor_tail_finite_energy_output_to_eLpNorm_output D hOut)

/-! ## §4. A.e.-flavor master assembly (matches the stub's named sorry).

The `aubin_lions_stub` file states its blocking sorry in a.e. form:
`krf_subseq_ae_of_translation`. The downstream extraction is now isolated in
`ae_subsequence_of_eLpNorm_convergence`; this theorem still needs the upstream
KRF/Cantor source to expose `eLpNorm` convergence or the exact `MemLp` bridge. -/

/-- **Master KRF compactness, a.e. form.**

This is exactly the conclusion shape of
`ZtareProofs.NS.AubinLions.krf_subseq_ae_of_translation`. Once the KRF pieces
and the `eLpNorm` source-shape bridge land, this theorem closes that named
sorry directly. -/
theorem krf_master_compactness_ae
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u) :
    ∃ (φ : ℕ → ℕ), StrictMono φ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (φ n) t) atTop (𝓝 (uInf t)) := by
  -- Step A. Apply the master integral-form KRF.
  obtain ⟨φ, hφ_mono, uInf, _hConv⟩ := krf_master_compactness D
  -- Step B. Convert L²-integral convergence to convergence in measure
  --   (`MeasureTheory.tendstoInMeasure_of_tendsto_eLpNorm`,
  --    Mathlib/MeasureTheory/Function/ConvergenceInMeasure.lean:39).
  -- Step C. Extract a.e.-convergent further sub-subsequence
  --   (`MeasureTheory.TendstoInMeasure.exists_seq_tendsto_ae`,
  --    Mathlib/MeasureTheory/Function/ConvergenceInMeasure.lean:277).
  --
  -- This step is NOT a one-line projection from the current source.
  -- The Mathlib convergence-in-measure lemmas are present, but they
  -- consume `eLpNorm` convergence.  The current `CantorDiagonalOutput`
  -- exposes only real-integral convergence plus strong measurability of
  -- `uInf`; it does not expose the `MemLp`/finite-integral witness needed
  -- to identify that integral with `eLpNorm`.  The correct closure is to
  -- strengthen the upstream KRF/Cantor output with an `eLpNorm` convergence
  -- or `MemLp` bridge, then apply the Mathlib lemmas here.
  --
  -- S-COMPOSE: blocked on source-shape repair, not on a classical theorem.
  sorry

/-! ## §5. Bridge to the stub's named sorry.

The stub file `ns_trackb_aubin_lions_stub.lean` ships
`krf_subseq_ae_of_translation` as a `sorry`-bodied theorem. This
section provides the closing theorem. When pieces 1/2/3 land + the
S-COMPOSE plumbing is filled, the stub's sorry can be discharged by
`exact krf_master_compactness_ae D`.

Because Lean does not allow rewriting an existing `sorry`-theorem from
another file at the source level (only re-statement), we expose a
WITNESS theorem here that the stub maintainer can swap in. -/

/-- **Witness for the stub's named sorry.** This theorem has the
*exact* statement of `ZtareProofs.NS.AubinLions.krf_subseq_ae_of_translation`
and discharges from `krf_master_compactness_ae` once it is sorry-free. -/
theorem stub_named_sorry_discharge
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u) :
    ∃ (φ : ℕ → ℕ), StrictMono φ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (φ n) t) atTop (𝓝 (uInf t)) :=
  krf_master_compactness_ae D

/-! ## §6. Sorry/dependency table

| Sorry tag    | Theorem                          | Depends on workstream |
|--------------|----------------------------------|-----------------------|
| S-PIECE-1    | `mollifier_rate_from_piece1`     | 1 (mollifier rate)    |
| S-PIECE-2    | `arzela_ascoli_from_piece2`      | 2 (Arzelà–Ascoli)     |
| S-PIECE-3    | `cantor_diagonal_from_piece3`    | 3 (Cantor diagonal)   |
| S-COMPOSE    | `krf_master_compactness_ae` (B)  | eLpNorm/MemLp source-shape bridge |

`krf_master_compactness` (integral form) is sorry-free conditional
on S-PIECE-{1,2,3}; the only `sorry` along its main proof path is
inside the three named-piece theorems.

`krf_master_compactness_ae` adds one extra sorry (S-COMPOSE) for the
integral → a.e. conversion. The downstream extraction from `eLpNorm`
convergence is now proved by `ae_subsequence_of_eLpNorm_convergence`; the
remaining work is to produce `CantorDiagonalELpNormOutput` or the exact
`MemLp`/finite-integral bridge from `CantorDiagonalOutput`. The two PRESENT
Mathlib lemmas consumed by the proved downstream theorem are
  * `MeasureTheory.tendstoInMeasure_of_tendsto_eLpNorm`
  * `MeasureTheory.TendstoInMeasure.exists_seq_tendsto_ae`

Total sorries in this file: **4**.
- 3 BLOCKED on sibling workstreams (each: 1-line discharge once import lands)
- 1 BLOCKED on source-shape repair (S-COMPOSE; downstream extraction already
  proved once `eLpNorm` convergence is supplied)

When all four close, the stub's `krf_subseq_ae_of_translation` sorry
is dischargeable by `exact krf_master_compactness_ae D`, which in
turn collapses the second sorry chain in the stub
(`kolmogorov_riesz_frechet_compactness` keeps only `vitali_to_integral`,
itself requiring the related indicator/restrict and `MemLp` source shape).

Net architectural effect: **the SOLE blocking classical theorem in
the entire NS Track B architecture is reduced to three sibling
workstream files plus ~200 LoC of Mathlib plumbing.**
-/

end

end ZtareProofs.NS.KRFMaster
