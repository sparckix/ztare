import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Function.UnifTight
import Mathlib.MeasureTheory.Function.LpSpace.Basic
import Mathlib.MeasureTheory.Function.LpSpace.Complete
import Mathlib.MeasureTheory.Function.L2Space
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

/-- Pairwise Cauchy source contract for the KRF/Cantor workstream.

This is the producer-facing form of the piece-3 obligation.  It avoids naming
`Lp` quotient representatives in upstream analytic estimates: the producer
pays selected-family `MemLp` plus pairwise restricted `eLpNorm` Cauchy, and
the checked bridge below converts that to `CantorDiagonalELpNormOutput`. -/
def CantorDiagonalPairwiseELpNormCauchyOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∃ (φ : ℕ → ℕ), StrictMono φ ∧
    (∀ n,
      MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
    Tendsto
      (fun nm : ℕ × ℕ =>
        eLpNorm (fun t => u (φ nm.1) t - u (φ nm.2) t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
      atTop (𝓝 0)

/-- Linked smoothing triangle source contract for piece 3.

This is the producer-facing contract immediately upstream of
`CantorDiagonalPairwiseELpNormCauchyOutput`.  It names the common smoothed
family that the current legacy `MollifierRateOutput`/`ArzelaAscoliOutput`
surfaces fail to share, plus the three metric error channels whose sum is the
uniform pairwise envelope. -/
def LinkedSmoothingTriangleOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∃ (φ : ℕ → ℕ), StrictMono φ ∧
    (∀ n,
      MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
    ∃ (smooth : ℕ → ℝ → B) (a b d c : ℕ × ℕ → ℝ),
      (∀ nm, 0 ≤ a nm) ∧
      (∀ nm, 0 ≤ b nm) ∧
      (∀ nm, 0 ≤ d nm) ∧
      (∀ nm, c nm = a nm + b nm + d nm) ∧
      (∀ nm t, t ∈ Set.Icc 0 T →
        dist (u (φ nm.1) t) (smooth nm.1 t) ≤ a nm) ∧
      (∀ nm t, t ∈ Set.Icc 0 T →
        dist (smooth nm.1 t) (smooth nm.2 t) ≤ b nm) ∧
      (∀ nm t, t ∈ Set.Icc 0 T →
        dist (smooth nm.2 t) (u (φ nm.2) t) ≤ d nm) ∧
      Tendsto
        (fun nm : ℕ × ℕ =>
          ENNReal.ofReal (c nm) *
            (MeasureTheory.volume (Set.Icc 0 T)) ^
              (1 / (2 : ENNReal).toReal))
        atTop (𝓝 0)

/-- Source contract for the two mollifier-approximation sides of the linked
triangle.

This is intentionally weaker than `LinkedSmoothingTriangleOutput`: it pays only
the original-to-smoothed approximation channels and their scaled envelopes for a
fixed selected family and a common smoothed family.  The smoothed-pairwise
channel is a separate source contract below. -/
def LinkedApproximationEnvelopeOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B)
    (φ : ℕ → ℕ) (smooth : ℕ → ℝ → B)
    (a d : ℕ × ℕ → ℝ) : Prop :=
  (∀ nm, 0 ≤ a nm) ∧
  (∀ nm, 0 ≤ d nm) ∧
  (∀ nm t, t ∈ Set.Icc 0 T →
    dist (u (φ nm.1) t) (smooth nm.1 t) ≤ a nm) ∧
  (∀ nm t, t ∈ Set.Icc 0 T →
    dist (smooth nm.2 t) (u (φ nm.2) t) ≤ d nm) ∧
  Tendsto
    (fun nm : ℕ × ℕ =>
      ENNReal.ofReal (a nm) *
        (MeasureTheory.volume (Set.Icc 0 T)) ^
          (1 / (2 : ENNReal).toReal))
    atTop (𝓝 0) ∧
  Tendsto
    (fun nm : ℕ × ℕ =>
      ENNReal.ofReal (d nm) *
        (MeasureTheory.volume (Set.Icc 0 T)) ^
          (1 / (2 : ENNReal).toReal))
    atTop (𝓝 0)

/-- Source contract for the fixed-scale Arzelà-smoothed pairwise channel of
the linked triangle.

This keeps the compactness/Cantor pairwise Cauchy receipt separate from the
mollifier approximation receipt, while forcing both to refer to the same
`smooth` family. -/
def LinkedSmoothedPairwiseEnvelopeOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (smooth : ℕ → ℝ → B)
    (b : ℕ × ℕ → ℝ) : Prop :=
  (∀ nm, 0 ≤ b nm) ∧
  (∀ nm t, t ∈ Set.Icc 0 T →
    dist (smooth nm.1 t) (smooth nm.2 t) ≤ b nm) ∧
  Tendsto
    (fun nm : ℕ × ℕ =>
      ENNReal.ofReal (b nm) *
        (MeasureTheory.volume (Set.Icc 0 T)) ^
          (1 / (2 : ENNReal).toReal))
    atTop (𝓝 0)

/-- Strengthened producer-facing KRF source contract.

The legacy `MollifierRateOutput` and `ArzelaAscoliOutput` do not share a
smoothed family.  This contract names the linked output the real workstreams
must produce: a selected diagonal family with `MemLp`, a common smoothed
family, and the two split envelope receipts that feed row 20. -/
def LinkedKRFProducerOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∃ (φ : ℕ → ℕ), StrictMono φ ∧
    (∀ n,
      MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
    ∃ (smooth : ℕ → ℝ → B) (a b d : ℕ × ℕ → ℝ),
      LinkedApproximationEnvelopeOutput T u φ smooth a d ∧
      LinkedSmoothedPairwiseEnvelopeOutput T smooth b

/-- `eLpNorm`-currency approximation source for the linked KRF producer.

This is the currency the mollifier-rate file naturally exposes.  It avoids the
pointwise-distance envelope required by the uniform-on-compact route and pays
the left/right original-smoothed errors directly in restricted `eLpNorm`. -/
def LinkedApproximationELpNormOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B)
    (φ : ℕ → ℕ) (smooth : ℕ → ℝ → B) : Prop :=
  (∀ nm : ℕ × ℕ,
    AEStronglyMeasurable
      (fun t => u (φ nm.1) t - smooth nm.1 t)
      (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
  (∀ nm : ℕ × ℕ,
    AEStronglyMeasurable
      (fun t => smooth nm.2 t - u (φ nm.2) t)
      (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
  Tendsto
    (fun nm : ℕ × ℕ =>
      eLpNorm (fun t => u (φ nm.1) t - smooth nm.1 t)
        2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    atTop (𝓝 0) ∧
  Tendsto
    (fun nm : ℕ × ℕ =>
      eLpNorm (fun t => smooth nm.2 t - u (φ nm.2) t)
        2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    atTop (𝓝 0)

/-- Unary-rate version of `LinkedApproximationELpNormOutput`.

This is closer to the actual mollifier-rate theorem shape: one selected
family, one common smoothing family, and one rate as the selected index tends
to infinity.  The two-coordinate pairwise contract is then just the product
filter projection of this unary rate. -/
def LinkedApproximationELpNormUnaryOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B)
    (φ : ℕ → ℕ) (smooth : ℕ → ℝ → B) : Prop :=
  (∀ n : ℕ,
    AEStronglyMeasurable
      (fun t => u (φ n) t - smooth n t)
      (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
  (∀ n : ℕ,
    AEStronglyMeasurable
      (fun t => smooth n t - u (φ n) t)
      (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
  Tendsto
    (fun n : ℕ =>
      eLpNorm (fun t => u (φ n) t - smooth n t)
        2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    atTop (𝓝 0) ∧
  Tendsto
    (fun n : ℕ =>
      eLpNorm (fun t => smooth n t - u (φ n) t)
        2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    atTop (𝓝 0)

/-- `eLpNorm`-currency smoothed pairwise source for the linked KRF producer. -/
def LinkedSmoothedPairwiseELpNormOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (smooth : ℕ → ℝ → B) : Prop :=
  (∀ nm : ℕ × ℕ,
    AEStronglyMeasurable
      (fun t => smooth nm.1 t - smooth nm.2 t)
      (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
  Tendsto
    (fun nm : ℕ × ℕ =>
      eLpNorm (fun t => smooth nm.1 t - smooth nm.2 t)
        2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    atTop (𝓝 0)

/-- Limit-form smoothed source for the linked KRF producer.

This is the shape closest to an Arzelà/Cantor extraction once a smoothed
subsequence has a limit: both one-sided differences to the same limit tend to
zero in restricted `eLpNorm`. -/
def LinkedSmoothedLimitELpNormOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (smooth : ℕ → ℝ → B) : Prop :=
  ∃ limit : ℝ → B,
    (∀ n : ℕ,
      AEStronglyMeasurable
        (fun t => smooth n t - limit t)
        (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
    (∀ n : ℕ,
      AEStronglyMeasurable
        (fun t => limit t - smooth n t)
        (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
    Tendsto
      (fun n : ℕ =>
        eLpNorm (fun t => smooth n t - limit t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
      atTop (𝓝 0) ∧
    Tendsto
      (fun n : ℕ =>
        eLpNorm (fun t => limit t - smooth n t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
      atTop (𝓝 0)

/-- Orthogonal scale-space source contract for the KRF row-20 lane.

This is the typed form of the sum-product/wavelet recombination: the selected
family is split into a low carrier and a high carrier.  The low ledger pays
pairwise compactness, the high ledger pays a vanishing tail, and the
reconstruction field is the no-alias certificate that prevents double-billing.

It intentionally targets only the `eLpNorm` pairwise Cauchy source consumed by
row 20.  It does not assert a BKM/Serrin/CF-critical regularity upgrade. -/
def ScaleSpaceSplitELpNormCarrierOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∃ (φ : ℕ → ℕ), StrictMono φ ∧
    (∀ n,
      MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
    ∃ (low high : ℕ → ℝ → B),
      (∀ n,
        AEStronglyMeasurable (fun t => low n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
      (∀ n,
        AEStronglyMeasurable (fun t => high n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
      (∀ n,
        (fun t => u (φ n) t) =ᵐ[MeasureTheory.volume.restrict (Set.Icc 0 T)]
          fun t => low n t + high n t) ∧
      (∀ nm : ℕ × ℕ,
        AEStronglyMeasurable (fun t => low nm.1 t - low nm.2 t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
      Tendsto
        (fun nm : ℕ × ℕ =>
          eLpNorm (fun t => low nm.1 t - low nm.2 t)
            2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
        atTop (𝓝 0) ∧
      Tendsto
        (fun n : ℕ =>
          eLpNorm (fun t => high n t)
            2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
        atTop (𝓝 0)

/-- The scale-space split source emits the pairwise `eLpNorm` Cauchy source
expected by row 20.

The proof is the no-alias estimate: reconstruct each selected field as
`low + high`, use the low pairwise Cauchy ledger, and pay the two high tails
separately.  Any future Littlewood-Paley/wavelet instantiation has to pay
exactly these fields rather than smuggling high-frequency control through KRF
translation compactness. -/
theorem pairwise_cauchy_output_of_scale_space_split_eLpNorm_carrier
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : ScaleSpaceSplitELpNormCarrierOutput T u) :
    CantorDiagonalPairwiseELpNormCauchyOutput T u := by
  rcases hOut with
    ⟨φ, hφ, hMem, low, high, hLowMeas, hHighMeas, hRecon,
      hLowDiffMeas, hLowPair, hHighTail⟩
  refine ⟨φ, hφ, hMem, ?_⟩
  let μ := MeasureTheory.volume.restrict (Set.Icc 0 T)
  have hp : 1 ≤ (2 : ENNReal) := by norm_num
  have hfst :
      Tendsto Prod.fst (atTop : Filter (ℕ × ℕ)) (atTop : Filter ℕ) := by
    rw [← Filter.prod_atTop_atTop_eq]
    exact Filter.tendsto_fst
  have hsnd :
      Tendsto Prod.snd (atTop : Filter (ℕ × ℕ)) (atTop : Filter ℕ) := by
    rw [← Filter.prod_atTop_atTop_eq]
    exact Filter.tendsto_snd
  have hHighLeft :
      Tendsto
        (fun nm : ℕ × ℕ =>
          eLpNorm (fun t => high nm.1 t) 2 μ)
        atTop (𝓝 0) :=
    hHighTail.comp hfst
  have hHighRight :
      Tendsto
        (fun nm : ℕ × ℕ =>
          eLpNorm (fun t => high nm.2 t) 2 μ)
        atTop (𝓝 0) :=
    hHighTail.comp hsnd
  have hUpper :
      Tendsto
        (fun nm : ℕ × ℕ =>
          eLpNorm (fun t => low nm.1 t - low nm.2 t) 2 μ +
            (eLpNorm (fun t => high nm.1 t) 2 μ +
              eLpNorm (fun t => high nm.2 t) 2 μ))
        atTop (𝓝 0) := by
    simpa [add_assoc] using hLowPair.add (hHighLeft.add hHighRight)
  refine tendsto_of_tendsto_of_tendsto_of_le_of_le
    tendsto_const_nhds hUpper (fun nm => zero_le _) ?_
  intro nm
  have hReconLeft := hRecon nm.1
  have hReconRight := hRecon nm.2
  have hTarget :
      eLpNorm (fun t => u (φ nm.1) t - u (φ nm.2) t) 2 μ =
      eLpNorm
        (fun t =>
          (low nm.1 t - low nm.2 t) +
            (high nm.1 t - high nm.2 t))
        2 μ := by
    apply eLpNorm_congr_ae
    filter_upwards [hReconLeft, hReconRight] with t hLeft hRight
    rw [hLeft, hRight]
    abel
  have hHighDiff :
      eLpNorm (fun t => high nm.1 t - high nm.2 t) 2 μ ≤
        eLpNorm (fun t => high nm.1 t) 2 μ +
          eLpNorm (fun t => high nm.2 t) 2 μ := by
    have hAdd :
        eLpNorm (fun t => high nm.1 t + - high nm.2 t) 2 μ ≤
          eLpNorm (fun t => high nm.1 t) 2 μ +
            eLpNorm (fun t => - high nm.2 t) 2 μ :=
      eLpNorm_add_le (hHighMeas nm.1) ((hHighMeas nm.2).neg) hp
    calc
      eLpNorm (fun t => high nm.1 t - high nm.2 t) 2 μ
          = eLpNorm (fun t => high nm.1 t + - high nm.2 t) 2 μ := by
              simp [sub_eq_add_neg]
      _ ≤ eLpNorm (fun t => high nm.1 t) 2 μ +
            eLpNorm (fun t => - high nm.2 t) 2 μ := hAdd
      _ = eLpNorm (fun t => high nm.1 t) 2 μ +
            eLpNorm (fun t => high nm.2 t) 2 μ := by
              congr 1
              change eLpNorm (-(fun t => high nm.2 t)) 2 μ =
                eLpNorm (fun t => high nm.2 t) 2 μ
              rw [eLpNorm_neg]
  have hSplit :
      eLpNorm
        (fun t =>
          (low nm.1 t - low nm.2 t) +
            (high nm.1 t - high nm.2 t))
        2 μ ≤
      eLpNorm (fun t => low nm.1 t - low nm.2 t) 2 μ +
        eLpNorm (fun t => high nm.1 t - high nm.2 t) 2 μ :=
    eLpNorm_add_le (hLowDiffMeas nm)
      ((hHighMeas nm.1).sub (hHighMeas nm.2)) hp
  calc
    eLpNorm (fun t => u (φ nm.1) t - u (φ nm.2) t) 2 μ
        = eLpNorm
          (fun t =>
            (low nm.1 t - low nm.2 t) +
              (high nm.1 t - high nm.2 t))
          2 μ := hTarget
    _ ≤ eLpNorm (fun t => low nm.1 t - low nm.2 t) 2 μ +
          eLpNorm (fun t => high nm.1 t - high nm.2 t) 2 μ := hSplit
    _ ≤ eLpNorm (fun t => low nm.1 t - low nm.2 t) 2 μ +
          (eLpNorm (fun t => high nm.1 t) 2 μ +
            eLpNorm (fun t => high nm.2 t) 2 μ) := by
            exact add_le_add (le_refl _) hHighDiff

/-- Real-epsilon version of the smoothed-limit source.

This is a convenient target for Arzelà/Cantor outputs that estimate the two
restricted `eLpNorm` errors by `ENNReal.ofReal ε`. -/
def LinkedSmoothedLimitELpNormRealOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (smooth : ℕ → ℝ → B) : Prop :=
  ∃ limit : ℝ → B,
    (∀ n : ℕ,
      AEStronglyMeasurable
        (fun t => smooth n t - limit t)
        (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
    (∀ n : ℕ,
      AEStronglyMeasurable
        (fun t => limit t - smooth n t)
        (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
    (∀ ε : ℝ, 0 < ε →
      ∀ᶠ n in atTop,
        eLpNorm (fun t => smooth n t - limit t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
          ENNReal.ofReal ε) ∧
    (∀ ε : ℝ, 0 < ε →
      ∀ᶠ n in atTop,
        eLpNorm (fun t => limit t - smooth n t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
          ENNReal.ofReal ε)

/-- Uniform convergence on the restricted interval, paid as a scalar
pointwise-distance envelope, supplies the real-epsilon smoothed-limit
`eLpNorm` source receipt.

This is the Arzelà/Cantor-facing analogue of the one-sided mollifier-rate
adapter: the companion file can pay a uniform-on-`[0,T]` distance bound to a
limit, and this theorem transports it into the restricted `eLpNorm` currency
used by row 20. -/
theorem LinkedSmoothedLimitELpNormRealOutput_of_uniform_dist_bound
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {smooth : ℕ → ℝ → B} {limit : ℝ → B}
    (hLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smooth n t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smooth n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (c : ℕ → ℝ)
    (hDist :
      ∀ n t, t ∈ Set.Icc 0 T →
        dist (smooth n t) (limit t) ≤ c n)
    (hEnvelope :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ n in atTop,
          ((MeasureTheory.volume.restrict (Set.Icc 0 T)) Set.univ) ^
              (2 : ENNReal).toReal⁻¹ *
            ENNReal.ofReal (c n) <
            ENNReal.ofReal ε) :
    LinkedSmoothedLimitELpNormRealOutput T smooth := by
  let μ := MeasureTheory.volume.restrict (Set.Icc 0 T)
  refine ⟨limit, hLeftMeas, hRightMeas, ?_, ?_⟩
  · intro ε hε
    filter_upwards [hEnvelope ε hε] with n hn
    have hAE :
        ∀ᵐ t ∂μ, ‖smooth n t - limit t‖ ≤ c n := by
      filter_upwards [MeasureTheory.ae_restrict_mem (measurableSet_Icc :
          MeasurableSet (Set.Icc 0 T))] with t ht
      simpa [dist_eq_norm] using hDist n t ht
    exact lt_of_le_of_lt
      (eLpNorm_le_of_ae_bound (μ := μ) (p := (2 : ENNReal)) hAE) hn
  · intro ε hε
    filter_upwards [hEnvelope ε hε] with n hn
    have hAE :
        ∀ᵐ t ∂μ, ‖limit t - smooth n t‖ ≤ c n := by
      filter_upwards [MeasureTheory.ae_restrict_mem (measurableSet_Icc :
          MeasurableSet (Set.Icc 0 T))] with t ht
      calc
        ‖limit t - smooth n t‖ = ‖-(smooth n t - limit t)‖ := by
          congr 1
          abel
        _ = ‖smooth n t - limit t‖ := norm_neg _
        _ ≤ c n := by
          simpa [dist_eq_norm] using hDist n t ht
    exact lt_of_le_of_lt
      (eLpNorm_le_of_ae_bound (μ := μ) (p := (2 : ENNReal)) hAE) hn

/-- Uniform convergence on `[0,T]`, together with an explicit scalar gauge
for the finite restricted measure, supplies the real-epsilon smoothed-limit
`eLpNorm` source receipt.

The scalar gauge is kept as a source hypothesis rather than hidden in this
bridge: Arzelà/Cantor pays the uniform convergence, while the measure-scaling
lemma pays the conversion from a uniform `η`-bound to an `eLpNorm` `ε`-bound. -/
theorem LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {smooth : ℕ → ℝ → B} {limit : ℝ → B}
    (hLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smooth n t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smooth n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hUniform :
      TendstoUniformlyOn (fun n t => smooth n t) limit atTop (Set.Icc 0 T))
    (hScale :
      ∀ ε : ℝ, 0 < ε →
        ∃ η : ℝ, 0 < η ∧
          ((MeasureTheory.volume.restrict (Set.Icc 0 T)) Set.univ) ^
              (2 : ENNReal).toReal⁻¹ *
            ENNReal.ofReal η <
            ENNReal.ofReal ε) :
    LinkedSmoothedLimitELpNormRealOutput T smooth := by
  let μ := MeasureTheory.volume.restrict (Set.Icc 0 T)
  refine ⟨limit, hLeftMeas, hRightMeas, ?_, ?_⟩
  · intro ε hε
    rcases hScale ε hε with ⟨η, hηpos, hη⟩
    have hUniformη :
        ∀ᶠ n in atTop,
          ∀ t ∈ Set.Icc 0 T, dist (limit t) (smooth n t) < η :=
      (Metric.tendstoUniformlyOn_iff.mp hUniform) η hηpos
    filter_upwards [hUniformη] with n hn
    have hAE :
        ∀ᵐ t ∂μ, ‖smooth n t - limit t‖ ≤ η := by
      filter_upwards [MeasureTheory.ae_restrict_mem (measurableSet_Icc :
          MeasurableSet (Set.Icc 0 T))] with t ht
      calc
        ‖smooth n t - limit t‖ = ‖limit t - smooth n t‖ := norm_sub_rev _ _
        _ = dist (limit t) (smooth n t) := by rw [dist_eq_norm]
        _ ≤ η := le_of_lt (hn t ht)
    exact lt_of_le_of_lt
      (eLpNorm_le_of_ae_bound (μ := μ) (p := (2 : ENNReal)) hAE) hη
  · intro ε hε
    rcases hScale ε hε with ⟨η, hηpos, hη⟩
    have hUniformη :
        ∀ᶠ n in atTop,
          ∀ t ∈ Set.Icc 0 T, dist (limit t) (smooth n t) < η :=
      (Metric.tendstoUniformlyOn_iff.mp hUniform) η hηpos
    filter_upwards [hUniformη] with n hn
    have hAE :
        ∀ᵐ t ∂μ, ‖limit t - smooth n t‖ ≤ η := by
      filter_upwards [MeasureTheory.ae_restrict_mem (measurableSet_Icc :
          MeasurableSet (Set.Icc 0 T))] with t ht
      calc
        ‖limit t - smooth n t‖ = dist (limit t) (smooth n t) := by
          rw [dist_eq_norm]
        _ ≤ η := le_of_lt (hn t ht)
    exact lt_of_le_of_lt
      (eLpNorm_le_of_ae_bound (μ := μ) (p := (2 : ENNReal)) hAE) hη

/-- A finite `ENNReal` multiplier can be beaten by choosing a sufficiently
small positive real `η`. -/
theorem ennreal_mul_ofReal_small_of_lt_top {C : ℝ≥0∞} (hC : C < ∞) :
    ∀ ε : ℝ, 0 < ε →
      ∃ η : ℝ, 0 < η ∧ C * ENNReal.ofReal η < ENNReal.ofReal ε := by
  intro ε hε
  let η : ℝ := ε / (2 * (C.toReal + 1))
  have hCnonneg : 0 ≤ C.toReal := ENNReal.toReal_nonneg
  have hdenpos : 0 < 2 * (C.toReal + 1) := by positivity
  refine ⟨η, div_pos hε hdenpos, ?_⟩
  have hCne : C ≠ ∞ := ne_of_lt hC
  have hCeq : C = ENNReal.ofReal C.toReal := by
    exact (ENNReal.ofReal_toReal hCne).symm
  rw [hCeq, ← ENNReal.ofReal_mul hCnonneg]
  rw [ENNReal.ofReal_lt_ofReal_iff hε]
  have hdenpos' : 0 < C.toReal + 1 := by positivity
  calc
    C.toReal * η = ε * (C.toReal / (2 * (C.toReal + 1))) := by
      dsimp [η]
      field_simp [ne_of_gt hdenpos]
    _ < ε * 1 := by
      gcongr
      have hratio : C.toReal / (2 * (C.toReal + 1)) < 1 := by
        rw [div_lt_one hdenpos]
        nlinarith [hCnonneg]
      exact hratio
    _ = ε := by ring

/-- The restricted interval measure factor used by the smoothed-limit
`eLpNorm` bridge admits the scalar gauge required to turn a uniform `η`-bound
into a real-epsilon restricted `eLpNorm` bound. -/
theorem restricted_Icc_volume_l2_scalar_gauge (T : ℝ) :
    ∀ ε : ℝ, 0 < ε →
      ∃ η : ℝ, 0 < η ∧
        ((MeasureTheory.volume.restrict (Set.Icc 0 T)) Set.univ) ^
            (2 : ENNReal).toReal⁻¹ *
          ENNReal.ofReal η <
          ENNReal.ofReal ε := by
  apply ennreal_mul_ofReal_small_of_lt_top
  have hμ : (MeasureTheory.volume.restrict (Set.Icc 0 T)) Set.univ < ∞ := by
    simpa [Measure.restrict_apply, measurableSet_Icc] using
      (isCompact_Icc.measure_lt_top (μ := MeasureTheory.volume) (a := 0) (b := T))
  exact ENNReal.rpow_lt_top_of_nonneg (by positivity) (ne_of_lt hμ)

/-- Uniform convergence on `[0,T]` supplies the real-epsilon smoothed-limit
`eLpNorm` source receipt; the restricted interval scalar gauge is paid by
`restricted_Icc_volume_l2_scalar_gauge`. -/
theorem LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn_Icc
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {smooth : ℕ → ℝ → B} {limit : ℝ → B}
    (hLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smooth n t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smooth n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hUniform :
      TendstoUniformlyOn (fun n t => smooth n t) limit atTop (Set.Icc 0 T)) :
    LinkedSmoothedLimitELpNormRealOutput T smooth :=
  LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn
    hLeftMeas hRightMeas hUniform (restricted_Icc_volume_l2_scalar_gauge T)

/-- An Arzelà/Cantor source that supplies uniform convergence on every compact
set supplies the `[0,T]` smoothed-limit `eLpNorm` receipt by specializing to
`Set.Icc 0 T`.

This theorem does not choose the Arzelà subsequence.  It is intentionally a
source-shape adapter for the already selected smoothed family, so the caller
must still prove that the Arzelà subsequence is the same one used by the
row-20 Phase-A lane. -/
theorem LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn_compacts
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {smooth : ℕ → ℝ → B} {limit : ℝ → B}
    (hLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smooth n t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smooth n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn (fun n t => smooth n t) limit atTop K) :
    LinkedSmoothedLimitELpNormRealOutput T smooth :=
  LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn_Icc
    hLeftMeas hRightMeas (hUniformCompacts (Set.Icc 0 T) isCompact_Icc)

/-- Real-epsilon smoothed-limit output implies the `Tendsto`-based limit
receipt. -/
theorem LinkedSmoothedLimitELpNormOutput_of_real
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {smooth : ℕ → ℝ → B}
    (h : LinkedSmoothedLimitELpNormRealOutput T smooth) :
    LinkedSmoothedLimitELpNormOutput T smooth := by
  rcases h with ⟨limit, hLeftMeas, hRightMeas, hLeft, hRight⟩
  refine ⟨limit, hLeftMeas, hRightMeas, ?_, ?_⟩
  · refine ENNReal.tendsto_nhds_zero.2 ?_
    intro ε hε
    by_cases htop : ε = ∞
    · filter_upwards [hLeft 1 (by norm_num)] with n hn
      simp [htop]
    · have hεne : ε ≠ 0 := ne_of_gt hε
      let δ : ℝ := ε.toReal / 2
      have hδpos : 0 < δ := by
        exact half_pos (ENNReal.toReal_pos hεne htop)
      have hδle : ENNReal.ofReal δ ≤ ε := by
        have hδlt : ENNReal.ofReal δ < ENNReal.ofReal ε.toReal := by
          rw [ENNReal.ofReal_lt_ofReal_iff (ENNReal.toReal_pos hεne htop)]
          exact half_lt_self (ENNReal.toReal_pos hεne htop)
        exact le_of_lt (by simpa [δ, ENNReal.ofReal_toReal htop] using hδlt)
      filter_upwards [hLeft δ hδpos] with n hn
      exact le_of_lt (lt_of_lt_of_le hn hδle)
  · refine ENNReal.tendsto_nhds_zero.2 ?_
    intro ε hε
    by_cases htop : ε = ∞
    · filter_upwards [hRight 1 (by norm_num)] with n hn
      simp [htop]
    · have hεne : ε ≠ 0 := ne_of_gt hε
      let δ : ℝ := ε.toReal / 2
      have hδpos : 0 < δ := by
        exact half_pos (ENNReal.toReal_pos hεne htop)
      have hδle : ENNReal.ofReal δ ≤ ε := by
        have hδlt : ENNReal.ofReal δ < ENNReal.ofReal ε.toReal := by
          rw [ENNReal.ofReal_lt_ofReal_iff (ENNReal.toReal_pos hεne htop)]
          exact half_lt_self (ENNReal.toReal_pos hεne htop)
        exact le_of_lt (by simpa [δ, ENNReal.ofReal_toReal htop] using hδlt)
      filter_upwards [hRight δ hδpos] with n hn
      exact le_of_lt (lt_of_lt_of_le hn hδle)

/-- A unary selected-family approximation rate supplies the two-coordinate
linked approximation contract used by the pairwise KRF producer. -/
theorem linkedApproximationELpNormOutput_of_unary
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B} {φ : ℕ → ℕ} {smooth : ℕ → ℝ → B}
    (h : LinkedApproximationELpNormUnaryOutput T u φ smooth) :
    LinkedApproximationELpNormOutput T u φ smooth := by
  rcases h with ⟨hLeftMeas, hRightMeas, hLeft, hRight⟩
  have hfst :
      Tendsto Prod.fst (atTop : Filter (ℕ × ℕ)) (atTop : Filter ℕ) := by
    rw [← Filter.prod_atTop_atTop_eq]
    exact Filter.tendsto_fst
  have hsnd :
      Tendsto Prod.snd (atTop : Filter (ℕ × ℕ)) (atTop : Filter ℕ) := by
    rw [← Filter.prod_atTop_atTop_eq]
    exact Filter.tendsto_snd
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro nm
    exact hLeftMeas nm.1
  · intro nm
    exact hRightMeas nm.2
  · simpa only [Function.comp_apply] using hLeft.comp hfst
  · simpa only [Function.comp_apply] using hRight.comp hsnd

/-- A smoothed subsequence converging to one restricted `eLpNorm` limit is
pairwise Cauchy in the smoothed-smoothed channel. -/
theorem linkedSmoothedPairwiseELpNormOutput_of_limit
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {smooth : ℕ → ℝ → B}
    (h : LinkedSmoothedLimitELpNormOutput T smooth) :
    LinkedSmoothedPairwiseELpNormOutput T smooth := by
  rcases h with ⟨limit, hLeftMeas, hRightMeas, hLeft, hRight⟩
  let μ := MeasureTheory.volume.restrict (Set.Icc 0 T)
  have hp : 1 ≤ (2 : ENNReal) := by norm_num
  have hfst :
      Tendsto Prod.fst (atTop : Filter (ℕ × ℕ)) (atTop : Filter ℕ) := by
    rw [← Filter.prod_atTop_atTop_eq]
    exact Filter.tendsto_fst
  have hsnd :
      Tendsto Prod.snd (atTop : Filter (ℕ × ℕ)) (atTop : Filter ℕ) := by
    rw [← Filter.prod_atTop_atTop_eq]
    exact Filter.tendsto_snd
  refine ⟨?_, ?_⟩
  · intro nm
    refine ((hLeftMeas nm.1).add (hRightMeas nm.2)).congr ?_
    filter_upwards with t
    change (smooth nm.1 t - limit t) + (limit t - smooth nm.2 t) =
      smooth nm.1 t - smooth nm.2 t
    abel_nf
  · have hUpper :
        Tendsto
          (fun nm : ℕ × ℕ =>
            eLpNorm (fun t => smooth nm.1 t - limit t) 2 μ +
              eLpNorm (fun t => limit t - smooth nm.2 t) 2 μ)
          atTop (𝓝 0) := by
        simpa [Function.comp_apply] using (hLeft.comp hfst).add (hRight.comp hsnd)
    refine tendsto_of_tendsto_of_tendsto_of_le_of_le
      tendsto_const_nhds hUpper (fun nm => zero_le _) ?_
    intro nm
    calc
      eLpNorm (fun t => smooth nm.1 t - smooth nm.2 t) 2 μ
          = eLpNorm
              (fun t =>
                (smooth nm.1 t - limit t) + (limit t - smooth nm.2 t))
              2 μ := by
            refine eLpNorm_congr_ae ?_
            filter_upwards with t
            simp [sub_eq_add_neg, add_assoc, add_left_comm, add_comm]
      _ ≤ eLpNorm (fun t => smooth nm.1 t - limit t) 2 μ +
            eLpNorm (fun t => limit t - smooth nm.2 t) 2 μ := by
            exact eLpNorm_add_le (hLeftMeas nm.1) (hRightMeas nm.2) hp

/-- Strengthened producer output in the source currency paid by the actual
mollifier-rate and Arzelà/Cantor workstreams: restricted `eLpNorm`, not
pointwise distance envelopes. -/
def LinkedKRFELpNormProducerOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∃ (φ : ℕ → ℕ), StrictMono φ ∧
    (∀ n,
      MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
    ∃ (smooth : ℕ → ℝ → B),
      LinkedApproximationELpNormOutput T u φ smooth ∧
      LinkedSmoothedPairwiseELpNormOutput T smooth

/-- Unary approximation plus smoothed-limit receipts assemble the full
eLpNorm-currency linked KRF producer output. -/
theorem linkedKRFELpNormProducerOutput_of_unary_and_smoothed_limit
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smooth : ℕ → ℝ → B)
    (hApprox : LinkedApproximationELpNormUnaryOutput T u φ smooth)
    (hSmooth : LinkedSmoothedLimitELpNormOutput T smooth) :
    LinkedKRFELpNormProducerOutput T u := by
  refine ⟨φ, hφ, hMem, smooth, ?_, ?_⟩
  · exact linkedApproximationELpNormOutput_of_unary hApprox
  · exact linkedSmoothedPairwiseELpNormOutput_of_limit hSmooth

/-- Preferred upstream KRF/Cantor source shape for the row-20 `eLpNorm`
producer.

The companion files should aim at this source contract: one selected
subsequence, finite restricted `MemLp` for the selected family, a unary
mollifier-rate approximation in restricted `eLpNorm`, and a smoothed Arzelà/
Cantor limit in the same currency. -/
def KRFUnarySmoothedLimitSourceOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∃ (φ : ℕ → ℕ), StrictMono φ ∧
    (∀ n,
      MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
    ∃ (smooth : ℕ → ℝ → B),
      LinkedApproximationELpNormUnaryOutput T u φ smooth ∧
      LinkedSmoothedLimitELpNormOutput T smooth

/-- Uniform-in-family scale approximation source.

This is the source currency closest to the actual mollifier-rate theorem:
for all sufficiently small scale indices `k`, every family member is close to
its smoothed version `smoothAt k n` in restricted `eLpNorm`. -/
def UniformScaleApproximationELpNormRealOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B)
    (smoothAt : ℕ → ℕ → ℝ → B) : Prop :=
  (∀ k n : ℕ,
    AEStronglyMeasurable
      (fun t => u n t - smoothAt k n t)
      (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
  (∀ k n : ℕ,
    AEStronglyMeasurable
      (fun t => smoothAt k n t - u n t)
      (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
  (∀ ε : ℝ, 0 < ε →
    ∀ᶠ k in atTop,
      ∀ n,
        eLpNorm (fun t => u n t - smoothAt k n t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
          ENNReal.ofReal ε) ∧
  (∀ ε : ℝ, 0 < ε →
    ∀ᶠ k in atTop,
      ∀ n,
        eLpNorm (fun t => smoothAt k n t - u n t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
          ENNReal.ofReal ε)

def UniformScaleApproximationELpNormOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B)
    (smoothAt : ℕ → ℕ → ℝ → B) : Prop :=
  (∀ k n : ℕ,
    AEStronglyMeasurable
      (fun t => u n t - smoothAt k n t)
      (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
  (∀ k n : ℕ,
    AEStronglyMeasurable
      (fun t => smoothAt k n t - u n t)
      (MeasureTheory.volume.restrict (Set.Icc 0 T))) ∧
  (∀ ε : ℝ≥0∞, 0 < ε →
    ∀ᶠ k in atTop,
      ∀ n,
        eLpNorm (fun t => u n t - smoothAt k n t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) < ε) ∧
  (∀ ε : ℝ≥0∞, 0 < ε →
    ∀ᶠ k in atTop,
      ∀ n,
        eLpNorm (fun t => smoothAt k n t - u n t)
      2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) < ε)

/-- One-sided mollifier-rate output is enough for the two-sided real-epsilon
scale-approximation contract, since the missing orientation has the same
`eLpNorm` by negation. This matches the actual `mollifier_rate_uniform`
orientation. -/
theorem UniformScaleApproximationELpNormRealOutput_of_one_sided
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B} {smoothAt : ℕ → ℕ → ℝ → B}
    (hMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε) :
    UniformScaleApproximationELpNormRealOutput T u smoothAt := by
  let μ := MeasureTheory.volume.restrict (Set.Icc 0 T)
  have hLeftMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable (fun t => u n t - smoothAt k n t) μ := by
    intro k n
    have hneg :
        AEStronglyMeasurable
          (fun t => - (smoothAt k n t - u n t)) μ :=
      (hMeas k n).neg
    refine hneg.congr ?_
    filter_upwards with t
    abel
  have hLeftRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => u n t - smoothAt k n t) 2 μ <
              ENNReal.ofReal ε := by
    intro ε hε
    filter_upwards [hRate ε hε] with k hk n
    have hfun :
        (fun t => u n t - smoothAt k n t) =
          -(fun t => smoothAt k n t - u n t) := by
      funext t
      simp
    rw [hfun, eLpNorm_neg]
    exact hk n
  exact ⟨hLeftMeas, hMeas, hLeftRate, hRate⟩

/-- A one-sided global-volume mollifier-rate estimate restricts to `[0,T]`.
This is the source-currency adapter needed when the upstream approximation
theorem is paid on the ambient measure but row 20 consumes the restricted
interval measure. -/
theorem UniformScaleApproximationELpNormRealOutput_of_one_sided_global_rate
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B} {smoothAt : ℕ → ℕ → ℝ → B}
    (hMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hGlobalRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 MeasureTheory.volume <
              ENNReal.ofReal ε) :
    UniformScaleApproximationELpNormRealOutput T u smoothAt := by
  have hRestrictRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε := by
    intro ε hε
    filter_upwards [hGlobalRate ε hε] with k hk n
    exact lt_of_le_of_lt
      (MeasureTheory.eLpNorm_restrict_le
        (fun t => smoothAt k n t - u n t)
        2 MeasureTheory.volume (Set.Icc 0 T))
      (hk n)
  exact UniformScaleApproximationELpNormRealOutput_of_one_sided
    hMeas hRestrictRate

/-- Real-epsilon scale approximation implies the `ℝ≥0∞` neighbourhood form. -/
theorem UniformScaleApproximationELpNormOutput_of_real
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B} {smoothAt : ℕ → ℕ → ℝ → B}
    (h : UniformScaleApproximationELpNormRealOutput T u smoothAt) :
    UniformScaleApproximationELpNormOutput T u smoothAt := by
  rcases h with ⟨hLeftMeas, hRightMeas, hLeft, hRight⟩
  refine ⟨hLeftMeas, hRightMeas, ?_, ?_⟩
  · intro ε hε
    by_cases htop : ε = ∞
    · filter_upwards [hLeft 1 (by norm_num)] with k hk n
      exact lt_of_lt_of_le (hk n) (by simp [htop])
    · have hεne : ε ≠ 0 := ne_of_gt hε
      let δ : ℝ := ε.toReal / 2
      have hδpos : 0 < δ := by
        exact half_pos (ENNReal.toReal_pos hεne htop)
      have hδle : ENNReal.ofReal δ ≤ ε := by
        have hδlt : ENNReal.ofReal δ < ENNReal.ofReal ε.toReal := by
          rw [ENNReal.ofReal_lt_ofReal_iff (ENNReal.toReal_pos hεne htop)]
          exact half_lt_self (ENNReal.toReal_pos hεne htop)
        exact le_of_lt (by simpa [δ, ENNReal.ofReal_toReal htop] using hδlt)
      filter_upwards [hLeft δ hδpos] with k hk n
      exact lt_of_lt_of_le (hk n) hδle
  · intro ε hε
    by_cases htop : ε = ∞
    · filter_upwards [hRight 1 (by norm_num)] with k hk n
      exact lt_of_lt_of_le (hk n) (by simp [htop])
    · have hεne : ε ≠ 0 := ne_of_gt hε
      let δ : ℝ := ε.toReal / 2
      have hδpos : 0 < δ := by
        exact half_pos (ENNReal.toReal_pos hεne htop)
      have hδle : ENNReal.ofReal δ ≤ ε := by
        have hδlt : ENNReal.ofReal δ < ENNReal.ofReal ε.toReal := by
          rw [ENNReal.ofReal_lt_ofReal_iff (ENNReal.toReal_pos hεne htop)]
          exact half_lt_self (ENNReal.toReal_pos hεne htop)
        exact le_of_lt (by simpa [δ, ENNReal.ofReal_toReal htop] using hδlt)
      filter_upwards [hRight δ hδpos] with k hk n
      exact lt_of_lt_of_le (hk n) hδle

/-- A uniform scale approximation source supplies the selected unary
approximation receipt by choosing scale `k = n` along the selected family. -/
theorem linkedApproximationELpNormUnaryOutput_of_uniform_scale
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B} {φ : ℕ → ℕ}
    {smoothAt : ℕ → ℕ → ℝ → B}
    (h : UniformScaleApproximationELpNormOutput T u smoothAt) :
    LinkedApproximationELpNormUnaryOutput T u φ
      (fun n => smoothAt n (φ n)) := by
  rcases h with ⟨hLeftMeas, hRightMeas, hLeft, hRight⟩
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro n
    exact hLeftMeas n (φ n)
  · intro n
    exact hRightMeas n (φ n)
  · refine ENNReal.tendsto_nhds_zero.2 ?_
    intro ε hε
    exact (hLeft ε hε).mono fun n hn => le_of_lt (hn (φ n))
  · refine ENNReal.tendsto_nhds_zero.2 ?_
    intro ε hε
    exact (hRight ε hε).mono fun n hn => le_of_lt (hn (φ n))

/-- A uniform scale approximation source can be sampled along any scale
selector `κ` tending to infinity.

This is the Phase-A/Arzelà alignment adapter: if an Arzelà extraction forces
the mollifier scale to be `κ n`, the original uniform-in-scale Phase-A receipt
still supplies the selected unary approximation source. -/
theorem linkedApproximationELpNormUnaryOutput_of_uniform_scale_tendsto
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B} {φ κ : ℕ → ℕ}
    {smoothAt : ℕ → ℕ → ℝ → B}
    (hκ : Tendsto κ atTop atTop)
    (h : UniformScaleApproximationELpNormOutput T u smoothAt) :
    LinkedApproximationELpNormUnaryOutput T u φ
      (fun n => smoothAt (κ n) (φ n)) := by
  rcases h with ⟨hLeftMeas, hRightMeas, hLeft, hRight⟩
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro n
    exact hLeftMeas (κ n) (φ n)
  · intro n
    exact hRightMeas (κ n) (φ n)
  · refine ENNReal.tendsto_nhds_zero.2 ?_
    intro ε hε
    exact (hκ.eventually (hLeft ε hε)).mono fun n hn =>
      le_of_lt (hn (φ n))
  · refine ENNReal.tendsto_nhds_zero.2 ?_
    intro ε hε
    exact (hκ.eventually (hRight ε hε)).mono fun n hn =>
      le_of_lt (hn (φ n))

/-- Uniform mollifier-scale approximation plus a smoothed-limit receipt gives
the preferred upstream KRF source output. -/
theorem KRFUnarySmoothedLimitSourceOutput_of_uniform_scale_and_smoothed_limit
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApprox : UniformScaleApproximationELpNormOutput T u smoothAt)
    (hSmooth :
      LinkedSmoothedLimitELpNormOutput T (fun n => smoothAt n (φ n))) :
    KRFUnarySmoothedLimitSourceOutput T u := by
  exact ⟨φ, hφ, hMem, fun n => smoothAt n (φ n),
    linkedApproximationELpNormUnaryOutput_of_uniform_scale hApprox,
    hSmooth⟩

/-- Real-epsilon uniform mollifier-rate output plus a smoothed-limit receipt
gives the preferred upstream KRF source output. -/
theorem KRFUnarySmoothedLimitSourceOutput_of_uniform_scale_real_and_smoothed_limit
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApprox : UniformScaleApproximationELpNormRealOutput T u smoothAt)
    (hSmooth :
      LinkedSmoothedLimitELpNormOutput T (fun n => smoothAt n (φ n))) :
    KRFUnarySmoothedLimitSourceOutput T u :=
  KRFUnarySmoothedLimitSourceOutput_of_uniform_scale_and_smoothed_limit
    φ hφ hMem smoothAt
    (UniformScaleApproximationELpNormOutput_of_real hApprox) hSmooth

/-- Uniform mollifier-scale approximation sampled along a scale selector,
plus a smoothed-limit receipt for that sampled family, gives the preferred
upstream KRF source output. -/
theorem KRFUnarySmoothedLimitSourceOutput_of_uniform_scale_tendsto_and_smoothed_limit
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smoothAt : ℕ → ℕ → ℝ → B)
    (κ : ℕ → ℕ) (hκ : Tendsto κ atTop atTop)
    (hApprox : UniformScaleApproximationELpNormOutput T u smoothAt)
    (hSmooth :
      LinkedSmoothedLimitELpNormOutput T
        (fun n => smoothAt (κ n) (φ n))) :
    KRFUnarySmoothedLimitSourceOutput T u := by
  exact ⟨φ, hφ, hMem, fun n => smoothAt (κ n) (φ n),
    linkedApproximationELpNormUnaryOutput_of_uniform_scale_tendsto
      hκ hApprox,
    hSmooth⟩

/-- Real-epsilon version of the scale-selector KRF source assembler. -/
theorem KRFUnarySmoothedLimitSourceOutput_of_uniform_scale_real_tendsto_and_smoothed_limit
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smoothAt : ℕ → ℕ → ℝ → B)
    (κ : ℕ → ℕ) (hκ : Tendsto κ atTop atTop)
    (hApprox : UniformScaleApproximationELpNormRealOutput T u smoothAt)
    (hSmooth :
      LinkedSmoothedLimitELpNormOutput T
        (fun n => smoothAt (κ n) (φ n))) :
    KRFUnarySmoothedLimitSourceOutput T u :=
  KRFUnarySmoothedLimitSourceOutput_of_uniform_scale_tendsto_and_smoothed_limit
    φ hφ hMem smoothAt κ hκ
    (UniformScaleApproximationELpNormOutput_of_real hApprox) hSmooth

/-- Real-epsilon Phase-A and Arzelà/Cantor source receipts assemble the
preferred upstream KRF source output. -/
theorem KRFUnarySmoothedLimitSourceOutput_of_real_sources
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApprox : UniformScaleApproximationELpNormRealOutput T u smoothAt)
    (hSmooth :
      LinkedSmoothedLimitELpNormRealOutput T (fun n => smoothAt n (φ n))) :
    KRFUnarySmoothedLimitSourceOutput T u :=
  KRFUnarySmoothedLimitSourceOutput_of_uniform_scale_real_and_smoothed_limit
    φ hφ hMem smoothAt hApprox
    (LinkedSmoothedLimitELpNormOutput_of_real hSmooth)

/-- Actual-mollifier-rate orientation plus real-epsilon Arzelà/Cantor source
receipts assemble the preferred upstream KRF source output. -/
theorem KRFUnarySmoothedLimitSourceOutput_of_one_sided_real_sources
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (hSmooth :
      LinkedSmoothedLimitELpNormRealOutput T (fun n => smoothAt n (φ n))) :
    KRFUnarySmoothedLimitSourceOutput T u :=
  KRFUnarySmoothedLimitSourceOutput_of_real_sources φ hφ hMem smoothAt
    (UniformScaleApproximationELpNormRealOutput_of_one_sided
      hApproxMeas hApproxRate)
    hSmooth

/-- The preferred upstream source contract assembles the full linked producer
without using the older pointwise-envelope route. -/
theorem linkedKRFELpNormProducerOutput_of_unary_smoothed_limit_source_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (h : KRFUnarySmoothedLimitSourceOutput T u) :
    LinkedKRFELpNormProducerOutput T u := by
  rcases h with ⟨φ, hφ, hMem, smooth, hApprox, hSmooth⟩
  exact linkedKRFELpNormProducerOutput_of_unary_and_smoothed_limit
    φ hφ hMem smooth hApprox hSmooth

/-- KRF/Cantor source contract in convergence-in-measure currency.

This sits strictly between the current real-integral source and the
`eLpNorm` source contract: it is enough for row-20 once `UniformIntegrable`
supplies the transported `eLpNorm` bound, but it still requires a legitimate
source-currency bridge from the integral-form diagonal output. -/
def CantorDiagonalInMeasureOutput
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    (T : ℝ) (u : ℕ → ℝ → B) : Prop :=
  ∃ (φ : ℕ → ℕ), StrictMono φ ∧
  ∃ (uInf : ℝ → B),
    StronglyMeasurable uInf ∧
    TendstoInMeasure
      (MeasureTheory.volume.restrict (Set.Icc 0 T))
      (fun n t => u (φ n) t) atTop uInf

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

/-- Preferred row-20 handoff for the upstream Cantor workstream.

The intended piece-3 proof narrative already passes through `Lp.completeSpace`;
this alias names the consumer theorem in that same `eLpNorm` currency so the
source workstream can target the strongest useful output directly. -/
theorem ae_subsequence_of_krf_data_eLpNorm_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalELpNormOutput T u) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_cantor_eLpNorm_output D hOut

/-- The preferred `eLpNorm` source output is stronger than the explicit
convergence-in-measure source contract. -/
theorem cantor_eLpNorm_output_to_inMeasure_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalELpNormOutput T u) :
    CantorDiagonalInMeasureOutput T u := by
  rcases hOut with ⟨φ, hφ_mono, uInf, hMeas, hLp⟩
  refine ⟨φ, hφ_mono, uInf, hMeas, ?_⟩
  have hf_meas :
      ∀ n, AEStronglyMeasurable (fun t => u (φ n) t)
        (MeasureTheory.volume.restrict (Set.Icc 0 T)) := by
    intro n
    exact (D.meas_u (φ n)).aestronglyMeasurable
  have hg_meas :
      AEStronglyMeasurable uInf
        (MeasureTheory.volume.restrict (Set.Icc 0 T)) :=
    hMeas.aestronglyMeasurable
  have hp : (2 : ENNReal) ≠ 0 := by norm_num
  exact tendstoInMeasure_of_tendsto_eLpNorm hp hf_meas hg_meas hLp

/-- Pairwise restricted `eLpNorm` Cauchy estimates are exactly the `Lp` Cauchy
source needed by the completion handoff.

This is the preferred upstream contract for the KRF piece-3 source: the
mollifier/Arzelà-Ascoli estimates should produce pairwise `eLpNorm` decay for
the selected diagonal family, while this bridge pays the quotient-space
currency conversion. -/
theorem restricted_Lp_cauchy_of_pairwise_eLpNorm_tendsto
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ)
    (hMem :
      ∀ n, MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hPair :
      Tendsto
        (fun nm : ℕ × ℕ =>
          eLpNorm (fun t => u (φ nm.1) t - u (φ nm.2) t)
            2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
        atTop (𝓝 0)) :
    CauchySeq (fun n => (hMem n).toLp (u (φ n))) := by
  letI : Fact (1 ≤ (2 : ℝ≥0∞)) := ⟨by norm_num⟩
  let μ := MeasureTheory.volume.restrict (Set.Icc 0 T)
  rw [Lp.cauchySeq_Lp_iff_cauchySeq_eLpNorm]
  refine hPair.congr' ?_
  exact Filter.Eventually.of_forall fun nm => by
    apply eLpNorm_congr_ae
    filter_upwards [
      (hMem nm.1).coeFn_toLp,
      (hMem nm.2).coeFn_toLp
    ] with t ht₁ ht₂
    simp [Pi.sub_apply, ht₁, ht₂]

/-- Uniform pairwise pointwise-distance control on the restricted interval,
with a vanishing finite-measure `L²` envelope, supplies the pairwise
restricted `eLpNorm` Cauchy source.

This is a producer-facing Arzelà-Ascoli bridge: fixed-scale uniform Cauchy
control should be paid as a pointwise distance bound, while this theorem
transports that bound into the exact `eLpNorm` currency consumed downstream. -/
theorem pairwise_restricted_eLpNorm_tendsto_of_uniform_dist_bound
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (c : ℕ × ℕ → ℝ)
    (hc_nonneg : ∀ nm, 0 ≤ c nm)
    (hDist :
      ∀ nm t, t ∈ Set.Icc 0 T →
        dist (u (φ nm.1) t) (u (φ nm.2) t) ≤ c nm)
    (hEnvelope :
      Tendsto
        (fun nm : ℕ × ℕ =>
          ENNReal.ofReal (c nm) *
            (MeasureTheory.volume (Set.Icc 0 T)) ^
              (1 / (2 : ENNReal).toReal))
        atTop (𝓝 0)) :
    Tendsto
      (fun nm : ℕ × ℕ =>
        eLpNorm (fun t => u (φ nm.1) t - u (φ nm.2) t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
      atTop (𝓝 0) := by
  have hs : MeasurableSet (Set.Icc 0 T) := measurableSet_Icc
  have hp : (2 : ENNReal) ≠ ∞ := by norm_num
  refine tendsto_of_tendsto_of_tendsto_of_le_of_le tendsto_const_nhds hEnvelope
    (fun nm => zero_le _) ?_
  intro nm
  have hBound :=
    eLpNorm_indicator_sub_le_of_dist_bdd
      (μ := MeasureTheory.volume) (p := (2 : ENNReal))
      hp hs (hc_nonneg nm) (fun t ht => hDist nm t ht)
  rw [eLpNorm_indicator_eq_eLpNorm_restrict hs] at hBound
  simpa [Pi.sub_apply] using hBound

/-- Abstract `Lp.completeSpace` handoff for the upstream Cantor workstream.

This packages the non-diagonal part of the intended piece-3 proof: once the
selected subsequence is Cauchy in the restricted `Lp` space, Mathlib completeness
produces a representative limit and `eLpNorm` convergence to it. The remaining
upstream work is therefore the mollifier/Arzelà-Ascoli proof of this Cauchy
source, not the completion handoff. -/
theorem cantor_eLpNorm_output_of_restricted_Lp_cauchy
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n, MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hCauchy :
      CauchySeq
        (fun n => (hMem n).toLp (u (φ n)))) :
    CantorDiagonalELpNormOutput T u := by
  have hOneLe : Fact (1 ≤ (2 : ℝ≥0∞)) := ⟨by norm_num⟩
  let μ := MeasureTheory.volume.restrict (Set.Icc 0 T)
  obtain ⟨uLp, hTendsto⟩ :
      ∃ uLp : Lp B 2 μ,
        Tendsto (fun n => (hMem n).toLp (u (φ n))) atTop (𝓝 uLp) :=
    CompleteSpace.complete hCauchy
  refine ⟨φ, hφ, (uLp : ℝ → B), Lp.stronglyMeasurable uLp, ?_⟩
  have hToLp :
      (Lp.memLp uLp).toLp (uLp : ℝ → B) = uLp :=
    Lp.toLp_coeFn uLp (Lp.memLp uLp)
  have hTendsto' :
      Tendsto (fun n => (hMem n).toLp (u (φ n))) atTop
        (𝓝 ((Lp.memLp uLp).toLp (uLp : ℝ → B))) := by
    simpa [hToLp] using hTendsto
  exact
    (Lp.tendsto_Lp_iff_tendsto_eLpNorm''
      (f := fun n => u (φ n))
      (f_ℒp := hMem)
      (f_lim := (uLp : ℝ → B))
      (f_lim_ℒp := Lp.memLp uLp)).mp hTendsto'

/-- Pairwise `eLpNorm` Cauchy source plus restricted membership gives the
diagonal `eLpNorm` output consumed by the row-20 compactness bridge. -/
theorem cantor_eLpNorm_output_of_pairwise_eLpNorm_cauchy
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n, MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hPair :
      Tendsto
        (fun nm : ℕ × ℕ =>
          eLpNorm (fun t => u (φ nm.1) t - u (φ nm.2) t)
            2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
        atTop (𝓝 0)) :
    CantorDiagonalELpNormOutput T u :=
  cantor_eLpNorm_output_of_restricted_Lp_cauchy φ hφ hMem
    (restricted_Lp_cauchy_of_pairwise_eLpNorm_tendsto φ hMem hPair)

/-- A selected diagonal subsequence with `MemLp` witnesses and explicit
uniform pairwise distance bounds on `[0,T]` emits the producer-facing pairwise
`eLpNorm` Cauchy contract. -/
theorem pairwise_cauchy_output_of_uniform_dist_bound
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n, MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (c : ℕ × ℕ → ℝ)
    (hc_nonneg : ∀ nm, 0 ≤ c nm)
    (hDist :
      ∀ nm t, t ∈ Set.Icc 0 T →
        dist (u (φ nm.1) t) (u (φ nm.2) t) ≤ c nm)
    (hEnvelope :
      Tendsto
        (fun nm : ℕ × ℕ =>
          ENNReal.ofReal (c nm) *
            (MeasureTheory.volume (Set.Icc 0 T)) ^
              (1 / (2 : ENNReal).toReal))
        atTop (𝓝 0)) :
    CantorDiagonalPairwiseELpNormCauchyOutput T u :=
  ⟨φ, hφ, hMem,
    pairwise_restricted_eLpNorm_tendsto_of_uniform_dist_bound
      φ c hc_nonneg hDist hEnvelope⟩

/-- Linked mollifier/Arzelà triangle source for the pairwise Cauchy producer.

This is the source-shape repair surface for piece 3.  The old
`MollifierRateOutput` only says each `u n` has some good smoothed witness; it
does not identify that witness with the fixed-scale family controlled by
Arzelà-Ascoli.  This theorem states the missing linked handoff explicitly:
once the producer supplies a common smoothed family and the three pointwise
bounds

* original-left to smoothed-left,
* smoothed-left to smoothed-right,
* smoothed-right to original-right,

with a vanishing finite-measure envelope, the already-checked uniform-distance
bridge emits the pairwise `eLpNorm` Cauchy contract. -/
theorem pairwise_cauchy_output_of_linked_uniform_triangle
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n, MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smooth : ℕ → ℝ → B)
    (a b d c : ℕ × ℕ → ℝ)
    (ha_nonneg : ∀ nm, 0 ≤ a nm)
    (hb_nonneg : ∀ nm, 0 ≤ b nm)
    (hd_nonneg : ∀ nm, 0 ≤ d nm)
    (hc_def : ∀ nm, c nm = a nm + b nm + d nm)
    (hLeft :
      ∀ nm t, t ∈ Set.Icc 0 T →
        dist (u (φ nm.1) t) (smooth nm.1 t) ≤ a nm)
    (hMid :
      ∀ nm t, t ∈ Set.Icc 0 T →
        dist (smooth nm.1 t) (smooth nm.2 t) ≤ b nm)
    (hRight :
      ∀ nm t, t ∈ Set.Icc 0 T →
        dist (smooth nm.2 t) (u (φ nm.2) t) ≤ d nm)
    (hEnvelope :
      Tendsto
        (fun nm : ℕ × ℕ =>
          ENNReal.ofReal (c nm) *
            (MeasureTheory.volume (Set.Icc 0 T)) ^
              (1 / (2 : ENNReal).toReal))
        atTop (𝓝 0)) :
    CantorDiagonalPairwiseELpNormCauchyOutput T u := by
  have hc_nonneg : ∀ nm, 0 ≤ c nm := by
    intro nm
    have ha := ha_nonneg nm
    have hb := hb_nonneg nm
    have hd := hd_nonneg nm
    have hc := hc_def nm
    linarith
  have hDist :
      ∀ nm t, t ∈ Set.Icc 0 T →
        dist (u (φ nm.1) t) (u (φ nm.2) t) ≤ c nm := by
    intro nm t ht
    have h₁ :
        dist (u (φ nm.1) t) (u (φ nm.2) t) ≤
          dist (u (φ nm.1) t) (smooth nm.1 t) +
            dist (smooth nm.1 t) (u (φ nm.2) t) :=
      dist_triangle _ _ _
    have h₂ :
        dist (smooth nm.1 t) (u (φ nm.2) t) ≤
          dist (smooth nm.1 t) (smooth nm.2 t) +
            dist (smooth nm.2 t) (u (φ nm.2) t) :=
      dist_triangle _ _ _
    have hL := hLeft nm t ht
    have hM := hMid nm t ht
    have hR := hRight nm t ht
    have hc := hc_def nm
    linarith
  exact
    pairwise_cauchy_output_of_uniform_dist_bound
      φ hφ hMem c hc_nonneg hDist hEnvelope

/-- Named linked-triangle source output consumes to the pairwise `eLpNorm`
Cauchy contract.  This is the clean piece-3 handoff target after repairing the
mollifier-rate/Arzelà-Ascoli outputs to share a smoothing family. -/
theorem pairwise_cauchy_output_of_linked_smoothing_triangle_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : LinkedSmoothingTriangleOutput T u) :
    CantorDiagonalPairwiseELpNormCauchyOutput T u := by
  rcases hOut with
    ⟨φ, hφ, hMem, smooth, a, b, d, c, ha, hb, hd, hc,
      hLeft, hMid, hRight, hEnvelope⟩
  exact
    pairwise_cauchy_output_of_linked_uniform_triangle
      φ hφ hMem smooth a b d c ha hb hd hc hLeft hMid hRight hEnvelope

/-- Build the named linked-triangle source from three separately paid
finite-measure envelopes.

This removes one more hiding place from the producer contract: the combined
envelope `c = a + b + d` need not be assumed directly if each of the three
scaled error channels tends to zero. -/
theorem linked_smoothing_triangle_output_of_component_envelopes
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n, MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smooth : ℕ → ℝ → B)
    (a b d : ℕ × ℕ → ℝ)
    (ha_nonneg : ∀ nm, 0 ≤ a nm)
    (hb_nonneg : ∀ nm, 0 ≤ b nm)
    (hd_nonneg : ∀ nm, 0 ≤ d nm)
    (hLeft :
      ∀ nm t, t ∈ Set.Icc 0 T →
        dist (u (φ nm.1) t) (smooth nm.1 t) ≤ a nm)
    (hMid :
      ∀ nm t, t ∈ Set.Icc 0 T →
        dist (smooth nm.1 t) (smooth nm.2 t) ≤ b nm)
    (hRight :
      ∀ nm t, t ∈ Set.Icc 0 T →
        dist (smooth nm.2 t) (u (φ nm.2) t) ≤ d nm)
    (hA :
      Tendsto
        (fun nm : ℕ × ℕ =>
          ENNReal.ofReal (a nm) *
            (MeasureTheory.volume (Set.Icc 0 T)) ^
              (1 / (2 : ENNReal).toReal))
        atTop (𝓝 0))
    (hB :
      Tendsto
        (fun nm : ℕ × ℕ =>
          ENNReal.ofReal (b nm) *
            (MeasureTheory.volume (Set.Icc 0 T)) ^
              (1 / (2 : ENNReal).toReal))
        atTop (𝓝 0))
    (hD :
      Tendsto
        (fun nm : ℕ × ℕ =>
          ENNReal.ofReal (d nm) *
            (MeasureTheory.volume (Set.Icc 0 T)) ^
              (1 / (2 : ENNReal).toReal))
        atTop (𝓝 0)) :
    LinkedSmoothingTriangleOutput T u := by
  let c : ℕ × ℕ → ℝ := fun nm => a nm + b nm + d nm
  have hEnvelope :
      Tendsto
        (fun nm : ℕ × ℕ =>
          ENNReal.ofReal (c nm) *
            (MeasureTheory.volume (Set.Icc 0 T)) ^
              (1 / (2 : ENNReal).toReal))
        atTop (𝓝 0) := by
    have hSum := (hA.add hB).add hD
    have hSum₀ :
        Tendsto
          (fun nm : ℕ × ℕ =>
            (ENNReal.ofReal (a nm) *
                (MeasureTheory.volume (Set.Icc 0 T)) ^
                  (1 / (2 : ENNReal).toReal) +
              ENNReal.ofReal (b nm) *
                (MeasureTheory.volume (Set.Icc 0 T)) ^
                  (1 / (2 : ENNReal).toReal)) +
              ENNReal.ofReal (d nm) *
                (MeasureTheory.volume (Set.Icc 0 T)) ^
                  (1 / (2 : ENNReal).toReal))
          atTop (𝓝 0) := by
      simpa using hSum
    refine hSum₀.congr' ?_
    exact Filter.Eventually.of_forall fun nm => by
      have ha_b_nonneg : 0 ≤ a nm + b nm :=
        add_nonneg (ha_nonneg nm) (hb_nonneg nm)
      dsimp [c]
      rw [ENNReal.ofReal_add ha_b_nonneg (hd_nonneg nm),
        ENNReal.ofReal_add (ha_nonneg nm) (hb_nonneg nm)]
      simp [add_mul, add_assoc]
  refine ⟨φ, hφ, hMem, smooth, a, b, d, c,
    ha_nonneg, hb_nonneg, hd_nonneg, ?_, hLeft, hMid, hRight, hEnvelope⟩
  intro nm
  rfl

/-- Compose the split producer contracts into the named linked-triangle source.

This is the next upstream handoff surface for piece 1 and piece 2: piece 1
should produce `LinkedApproximationEnvelopeOutput`, piece 2/3 should produce
`LinkedSmoothedPairwiseEnvelopeOutput` for the same `smooth` family, and this
bridge rebuilds the exact downstream contract. -/
theorem linked_smoothing_triangle_output_of_split_envelopes
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n, MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smooth : ℕ → ℝ → B)
    (a b d : ℕ × ℕ → ℝ)
    (hApprox :
      LinkedApproximationEnvelopeOutput T u φ smooth a d)
    (hSmoothed :
      LinkedSmoothedPairwiseEnvelopeOutput T smooth b) :
    LinkedSmoothingTriangleOutput T u := by
  rcases hApprox with
    ⟨ha_nonneg, hd_nonneg, hLeft, hRight, hA, hD⟩
  rcases hSmoothed with ⟨hb_nonneg, hMid, hB⟩
  exact
    linked_smoothing_triangle_output_of_component_envelopes
      φ hφ hMem smooth a b d
      ha_nonneg hb_nonneg hd_nonneg
      hLeft hMid hRight hA hB hD

/-- Direct pairwise-Cauchy consumer for the split producer contracts. -/
theorem pairwise_cauchy_output_of_split_envelopes
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n, MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smooth : ℕ → ℝ → B)
    (a b d : ℕ × ℕ → ℝ)
    (hApprox :
      LinkedApproximationEnvelopeOutput T u φ smooth a d)
    (hSmoothed :
      LinkedSmoothedPairwiseEnvelopeOutput T smooth b) :
    CantorDiagonalPairwiseELpNormCauchyOutput T u :=
  pairwise_cauchy_output_of_linked_smoothing_triangle_output
    (linked_smoothing_triangle_output_of_split_envelopes
      φ hφ hMem smooth a b d hApprox hSmoothed)

/-- Producer-facing pairwise Cauchy contract converts to the `eLpNorm`
diagonal output expected by row 20. -/
theorem cantor_eLpNorm_output_of_pairwise_cauchy_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hPairOut : CantorDiagonalPairwiseELpNormCauchyOutput T u) :
    CantorDiagonalELpNormOutput T u := by
  rcases hPairOut with ⟨φ, hφ, hMem, hPair⟩
  exact cantor_eLpNorm_output_of_pairwise_eLpNorm_cauchy φ hφ hMem hPair

/-- The producer-facing pairwise Cauchy contract is already enough for the
row-20 a.e. subsequence consumer once the ambient space is complete. -/
theorem ae_subsequence_of_krf_data_pairwise_cauchy_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hPairOut : CantorDiagonalPairwiseELpNormCauchyOutput T u) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_eLpNorm_source D
    (cantor_eLpNorm_output_of_pairwise_cauchy_output hPairOut)

/-- Row-20 a.e. consumer for the split producer contracts, conditional only on
the two real upstream receipts and the selected-family `MemLp` source. -/
theorem ae_subsequence_of_krf_data_split_envelopes_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n, MemLp (u (φ n)) 2
        (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smooth : ℕ → ℝ → B)
    (a b d : ℕ × ℕ → ℝ)
    (hApprox :
      LinkedApproximationEnvelopeOutput T u φ smooth a d)
    (hSmoothed :
      LinkedSmoothedPairwiseEnvelopeOutput T smooth b) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_pairwise_cauchy_source D
    (pairwise_cauchy_output_of_split_envelopes
      φ hφ hMem smooth a b d hApprox hSmoothed)

/-- The strengthened linked KRF producer output emits the pairwise `eLpNorm`
Cauchy source expected by piece 3. -/
theorem pairwise_cauchy_output_of_linked_krf_producer_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : LinkedKRFProducerOutput T u) :
    CantorDiagonalPairwiseELpNormCauchyOutput T u := by
  rcases hOut with
    ⟨φ, hφ, hMem, smooth, a, b, d, hApprox, hSmoothed⟩
  exact
    pairwise_cauchy_output_of_split_envelopes
      φ hφ hMem smooth a b d hApprox hSmoothed

/-- Direct row-20 a.e. consumer for the strengthened linked KRF producer
output. -/
theorem ae_subsequence_of_krf_data_linked_producer_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : LinkedKRFProducerOutput T u) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_pairwise_cauchy_source D
    (pairwise_cauchy_output_of_linked_krf_producer_output hOut)

/-- The `eLpNorm`-currency linked producer output emits the pairwise source
without passing through pointwise distance envelopes. -/
theorem pairwise_cauchy_output_of_linked_krf_eLpNorm_producer_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : LinkedKRFELpNormProducerOutput T u) :
    CantorDiagonalPairwiseELpNormCauchyOutput T u := by
  rcases hOut with
    ⟨φ, hφ, hMem, smooth, hApprox, hSmoothed⟩
  rcases hApprox with ⟨hLeftMeas, hRightMeas, hLeft, hRight⟩
  rcases hSmoothed with ⟨hMidMeas, hMid⟩
  refine ⟨φ, hφ, hMem, ?_⟩
  let μ := MeasureTheory.volume.restrict (Set.Icc 0 T)
  have hp : 1 ≤ (2 : ENNReal) := by norm_num
  have hUpper :
      Tendsto
        (fun nm : ℕ × ℕ =>
          (eLpNorm (fun t => u (φ nm.1) t - smooth nm.1 t) 2 μ +
            eLpNorm (fun t => smooth nm.1 t - smooth nm.2 t) 2 μ) +
            eLpNorm (fun t => smooth nm.2 t - u (φ nm.2) t) 2 μ)
        atTop (𝓝 0) := by
    simpa using (hLeft.add hMid).add hRight
  refine tendsto_of_tendsto_of_tendsto_of_le_of_le tendsto_const_nhds hUpper
    (fun nm => zero_le _) ?_
  intro nm
  have hFirst :
      eLpNorm
        (fun t =>
          (u (φ nm.1) t - smooth nm.1 t) +
            (smooth nm.1 t - smooth nm.2 t))
        2 μ ≤
      eLpNorm (fun t => u (φ nm.1) t - smooth nm.1 t) 2 μ +
        eLpNorm (fun t => smooth nm.1 t - smooth nm.2 t) 2 μ :=
    eLpNorm_add_le (hLeftMeas nm) (hMidMeas nm) hp
  have hSecond :
      eLpNorm
        (fun t =>
          ((u (φ nm.1) t - smooth nm.1 t) +
            (smooth nm.1 t - smooth nm.2 t)) +
            (smooth nm.2 t - u (φ nm.2) t))
        2 μ ≤
      eLpNorm
        (fun t =>
          (u (φ nm.1) t - smooth nm.1 t) +
            (smooth nm.1 t - smooth nm.2 t))
        2 μ +
        eLpNorm (fun t => smooth nm.2 t - u (φ nm.2) t) 2 μ :=
    eLpNorm_add_le ((hLeftMeas nm).add (hMidMeas nm))
      (hRightMeas nm) hp
  have hTarget :
      eLpNorm (fun t => u (φ nm.1) t - u (φ nm.2) t) 2 μ =
      eLpNorm
        (fun t =>
          ((u (φ nm.1) t - smooth nm.1 t) +
            (smooth nm.1 t - smooth nm.2 t)) +
            (smooth nm.2 t - u (φ nm.2) t))
        2 μ := by
    apply eLpNorm_congr_ae
    filter_upwards with t
    simp [sub_eq_add_neg, add_assoc, add_left_comm, add_comm]
  calc
    eLpNorm (fun t => u (φ nm.1) t - u (φ nm.2) t) 2 μ
        = eLpNorm
          (fun t =>
            ((u (φ nm.1) t - smooth nm.1 t) +
              (smooth nm.1 t - smooth nm.2 t)) +
              (smooth nm.2 t - u (φ nm.2) t))
          2 μ := hTarget
    _ ≤ eLpNorm
          (fun t =>
            (u (φ nm.1) t - smooth nm.1 t) +
              (smooth nm.1 t - smooth nm.2 t))
          2 μ +
          eLpNorm (fun t => smooth nm.2 t - u (φ nm.2) t) 2 μ := hSecond
    _ ≤ (eLpNorm (fun t => u (φ nm.1) t - smooth nm.1 t) 2 μ +
          eLpNorm (fun t => smooth nm.1 t - smooth nm.2 t) 2 μ) +
          eLpNorm (fun t => smooth nm.2 t - u (φ nm.2) t) 2 μ := by
      simpa [add_comm, add_left_comm, add_assoc] using
        add_le_add_right hFirst
          (eLpNorm (fun t => smooth nm.2 t - u (φ nm.2) t) 2 μ)

/-- Direct row-20 a.e. consumer for the `eLpNorm`-currency linked producer
output. -/
theorem ae_subsequence_of_krf_data_linked_eLpNorm_producer_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : LinkedKRFELpNormProducerOutput T u) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_pairwise_cauchy_source D
    (pairwise_cauchy_output_of_linked_krf_eLpNorm_producer_output hOut)

/-- Lower-level row-20 a.e. consumer for the `eLpNorm`-currency linked
producer.

The usual KRF-data wrapper is only one way to pay measurability of the source
family.  When a caller has already produced the linked `eLpNorm` source and can
pay `StronglyMeasurable` directly, the final a.e. extraction does not need a
fresh `KolmogorovRieszFrechetData` bundle for that exact family. -/
theorem ae_subsequence_of_linked_eLpNorm_producer_source_measurable
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hMeas : ∀ n, StronglyMeasurable (u n))
    (hOut : LinkedKRFELpNormProducerOutput T u) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) := by
  have hPair :
      CantorDiagonalPairwiseELpNormCauchyOutput T u :=
    pairwise_cauchy_output_of_linked_krf_eLpNorm_producer_output hOut
  rcases cantor_eLpNorm_output_of_pairwise_cauchy_output hPair with
    ⟨φ, hφ_mono, uInf, hMeas_inf, hLp⟩
  exact ae_subsequence_of_eLpNorm_convergence
    φ hφ_mono uInf hMeas hMeas_inf hLp

/-- Direct row-20 a.e. consumer for the two natural upstream eLpNorm receipts:
unary mollifier approximation plus smoothed-family convergence to a limit. -/
theorem ae_subsequence_of_krf_data_unary_smoothed_limit_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smooth : ℕ → ℝ → B)
    (hApprox : LinkedApproximationELpNormUnaryOutput T u φ smooth)
    (hSmooth : LinkedSmoothedLimitELpNormOutput T smooth) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_linked_eLpNorm_producer_source D
    (linkedKRFELpNormProducerOutput_of_unary_and_smoothed_limit
      φ hφ hMem smooth hApprox hSmooth)

/-- Direct row-20 a.e. consumer for the preferred upstream KRF/Cantor source
contract. -/
theorem ae_subsequence_of_krf_data_unary_smoothed_limit_source_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (h : KRFUnarySmoothedLimitSourceOutput T u) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_linked_eLpNorm_producer_source D
    (linkedKRFELpNormProducerOutput_of_unary_smoothed_limit_source_output h)

/-- Direct row-20 a.e. consumer for real-epsilon Phase-A and Arzelà/Cantor
source receipts over one common two-index mollified family. -/
theorem ae_subsequence_of_krf_data_real_source_outputs
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApprox : UniformScaleApproximationELpNormRealOutput T u smoothAt)
    (hSmooth :
      LinkedSmoothedLimitELpNormRealOutput T (fun n => smoothAt n (φ n))) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_unary_smoothed_limit_source_output D
    (KRFUnarySmoothedLimitSourceOutput_of_real_sources
      φ hφ hMem smoothAt hApprox hSmooth)

/-- Direct row-20 a.e. consumer for the actual one-sided mollifier-rate
orientation plus real-epsilon Arzelà/Cantor source receipt. -/
theorem ae_subsequence_of_krf_data_one_sided_real_source_outputs
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (hSmooth :
      LinkedSmoothedLimitELpNormRealOutput T (fun n => smoothAt n (φ n))) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_unary_smoothed_limit_source_output D
    (KRFUnarySmoothedLimitSourceOutput_of_one_sided_real_sources
      φ hφ hMem smoothAt hApproxMeas hApproxRate hSmooth)

/-- Direct row-20 a.e. consumer for the actual one-sided mollifier-rate
orientation plus an Arzelà/Cantor uniform-distance envelope for the selected
smoothed family. -/
theorem ae_subsequence_of_krf_data_one_sided_rate_and_uniform_dist_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (hMem :
      ∀ n,
        MemLp (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (limit : ℝ → B)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt n (φ n) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smoothAt n (φ n) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (c : ℕ → ℝ)
    (hSmoothDist :
      ∀ n t, t ∈ Set.Icc 0 T →
        dist (smoothAt n (φ n) t) (limit t) ≤ c n)
    (hSmoothEnvelope :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ n in atTop,
          ((MeasureTheory.volume.restrict (Set.Icc 0 T)) Set.univ) ^
              (2 : ENNReal).toReal⁻¹ *
            ENNReal.ofReal (c n) <
            ENNReal.ofReal ε) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_one_sided_real_source_outputs
    D φ hφ hMem smoothAt hApproxMeas hApproxRate
    (LinkedSmoothedLimitELpNormRealOutput_of_uniform_dist_bound
      hSmoothLeftMeas hSmoothRightMeas c hSmoothDist hSmoothEnvelope)

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

/-- Integral-form KRF convergence gives convergence in measure once the
source supplies the same `MemLp` evidence needed by the `eLpNorm` bridge.

This is the precise non-circular route for row 20: pay the finite-energy /
`MemLp` witness, get `eLpNorm` convergence, then use Mathlib's
`tendstoInMeasure_of_tendsto_eLpNorm`. -/
theorem tendstoInMeasure_of_integral_convergence_with_memLp
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (uInf : ℝ → B)
    (hf :
      ∀ n,
        AEStronglyMeasurable
          (fun t => u (φ n) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hg : AEStronglyMeasurable uInf (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hMem :
      ∀ n,
        MemLp
          (fun t => u (φ n) t - uInf t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hIntegral :
      Tendsto
        (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
        atTop (𝓝 0)) :
    TendstoInMeasure
      (MeasureTheory.volume.restrict (Set.Icc 0 T))
      (fun n t => u (φ n) t) atTop uInf := by
  exact tendstoInMeasure_of_tendsto_eLpNorm
    (by norm_num : (2 : ENNReal) ≠ 0) hf hg
    (eLpNorm_convergence_of_integral_convergence_with_memLp
      φ uInf hMem hIntegral)

/-- Tail version of `tendstoInMeasure_of_integral_convergence_with_memLp`.
Finite bad prefixes do not affect convergence in measure because the
intermediate `eLpNorm` convergence already ignores them. -/
theorem tendstoInMeasure_of_integral_convergence_eventually_memLp
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (φ : ℕ → ℕ) (uInf : ℝ → B)
    (hf :
      ∀ n,
        AEStronglyMeasurable
          (fun t => u (φ n) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hg : AEStronglyMeasurable uInf (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hMem :
      ∀ᶠ n in atTop,
        MemLp
          (fun t => u (φ n) t - uInf t)
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hIntegral :
      Tendsto
        (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
        atTop (𝓝 0)) :
    TendstoInMeasure
      (MeasureTheory.volume.restrict (Set.Icc 0 T))
      (fun n t => u (φ n) t) atTop uInf := by
  exact tendstoInMeasure_of_tendsto_eLpNorm
    (by norm_num : (2 : ENNReal) ≠ 0) hf hg
    (eLpNorm_convergence_of_integral_convergence_eventually_memLp
      φ uInf hMem hIntegral)

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

/-- The current integral-form Cantor output upgrades to convergence-in-measure
currency once the missing difference-`MemLp` evidence is explicit. -/
theorem cantor_integral_output_to_inMeasure_output_with_memLp
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
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
    CantorDiagonalInMeasureOutput T u := by
  rcases hOut with ⟨φ, hφ, uInf, hMeas, hIntegral⟩
  refine ⟨φ, hφ, uInf, hMeas, ?_⟩
  exact tendstoInMeasure_of_integral_convergence_with_memLp
    φ uInf
    (fun n => (D.meas_u (φ n)).aestronglyMeasurable)
    hMeas.aestronglyMeasurable
    (hMem φ uInf hφ hMeas hIntegral)
    hIntegral

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

/-- The named tail-finite KRF/Cantor source contract also upgrades directly to
the convergence-in-measure source contract. -/
theorem cantor_tail_finite_energy_output_to_inMeasure_output
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalTailFiniteEnergyOutput T u) :
    CantorDiagonalInMeasureOutput T u := by
  rcases hOut with ⟨φ, hφ, uInf, hMeas, hIntegral, hFinite⟩
  refine ⟨φ, hφ, uInf, hMeas, ?_⟩
  refine tendstoInMeasure_of_integral_convergence_eventually_memLp
    φ uInf
    (fun n => (D.meas_u (φ n)).aestronglyMeasurable)
    hMeas.aestronglyMeasurable ?_ hIntegral
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

/-- Interval square-integrability gives the ambient indicator `MemLp` witness.

This is the precise missing source-currency bridge below KRF's real `L²`
bound: the bounded set integral is useful only after the source also supplies
actual integrability of the squared norm on the interval. -/
theorem indicator_memLp_two_of_integrableOn_norm_sq
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {f : ℝ → B}
    (hf : StronglyMeasurable f)
    (hInt :
      IntegrableOn (fun t => ‖f t‖ ^ 2) (Set.Icc 0 T) MeasureTheory.volume) :
    MemLp (Set.indicator (Set.Icc 0 T) f) 2 MeasureTheory.volume := by
  have hMeas :
      AEStronglyMeasurable (Set.indicator (Set.Icc 0 T) f) MeasureTheory.volume :=
    (hf.indicator (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))).aestronglyMeasurable
  rw [memLp_two_iff_integrable_sq_norm hMeas]
  have hPoint :
      (fun x => ‖Set.indicator (Set.Icc 0 T) f x‖ ^ 2) =
        Set.indicator (Set.Icc 0 T) (fun x => ‖f x‖ ^ 2) := by
    funext x
    by_cases hx : x ∈ Set.Icc 0 T
    · simp [Set.indicator_of_mem, hx]
    · simp [Set.indicator_of_notMem, hx]
  rw [hPoint]
  exact hInt.integrable_indicator (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))

/-- KRF sequence-side version of
`indicator_memLp_two_of_integrableOn_norm_sq`. -/
theorem indicator_memLp_of_krf_integrableOn_norm_sq
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hInt :
      ∀ n, IntegrableOn (fun t => ‖u n t‖ ^ 2) (Set.Icc 0 T)
        MeasureTheory.volume) :
    ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2 MeasureTheory.volume := by
  intro n
  exact indicator_memLp_two_of_integrableOn_norm_sq (D.meas_u n) (hInt n)

/-- Measure-theory `UnifIntegrable` plus an explicit finite `eLpNorm` bound is
exactly Mathlib's probability-style `UniformIntegrable`.

This wrapper records the missing boundedness receipt separately from the
small-set integrability receipt carried by `KolmogorovRieszFrechetData`. -/
theorem uniformIntegrable_of_unifIntegrable_and_eLpNorm_bound
    {α ι : Type*} [MeasurableSpace α]
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    {μ : Measure α} {p : ℝ≥0∞} {f : ι → α → B}
    (hf : ∀ i, AEStronglyMeasurable (f i) μ)
    (hUI : UnifIntegrable f p μ)
    (hBound : ∃ C : ℝ≥0∞, C < ∞ ∧ ∀ i, eLpNorm (f i) p μ ≤ C) :
    UniformIntegrable f p μ := by
  rcases hBound with ⟨C, hC, hLe⟩
  refine ⟨hf, hUI, ⟨C.toNNReal, fun i => ?_⟩⟩
  calc
    eLpNorm (f i) p μ ≤ C := hLe i
    _ = (C.toNNReal : ℝ≥0∞) := (ENNReal.coe_toNNReal hC.ne).symm

/-- A real interval `L²` bound plus explicit indicator `MemLp` witness gives the
finite uniform indicator `eLpNorm` bound needed to upgrade `UnifIntegrable` to
`UniformIntegrable`.

The `MemLp` hypothesis is intentionally explicit: it is the finite-energy
identification that justifies reading the real set integral as an `eLpNorm`
bound, rather than treating the KRF `unif_l2_bound` field as that bound by
coercion. -/
theorem indicator_eLpNorm_bound_of_setIntegral_bound_memLp
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    {M : ℝ}
    (hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2 MeasureTheory.volume)
    (hBound : ∀ n, ∫ t in Set.Icc 0 T, ‖u n t‖ ^ 2 ≤ M) :
    ∃ C : ℝ≥0∞, C < ∞ ∧
      ∀ n, eLpNorm (Set.indicator (Set.Icc 0 T) (u n)) 2
        MeasureTheory.volume ≤ C := by
  refine ⟨ENNReal.ofReal (M ^ ((1 : ℝ) / 2)), ENNReal.ofReal_lt_top, ?_⟩
  intro n
  have hp0 : (2 : ENNReal) ≠ 0 := by norm_num
  have hpInf : (2 : ENNReal) ≠ ⊤ := by norm_num
  have hIntNonneg : 0 ≤ ∫ t in Set.Icc 0 T, ‖u n t‖ ^ 2 := by
    exact setIntegral_nonneg (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))
      (fun t _ht => by positivity)
  have hPowLe :
      (∫ t in Set.Icc 0 T, ‖u n t‖ ^ 2) ^ ((1 : ℝ) / 2)
        ≤ M ^ ((1 : ℝ) / 2) := by
    exact Real.rpow_le_rpow hIntNonneg (hBound n)
      (by positivity : 0 ≤ ((1 : ℝ) / 2))
  rw [MemLp.eLpNorm_eq_integral_rpow_norm hp0 hpInf (hMem n)]
  norm_num
  have hIndicatorIntegral :
      ∫ x, ‖Set.indicator (Set.Icc 0 T) (u n) x‖ ^ 2 ∂MeasureTheory.volume =
        ∫ x in Set.Icc 0 T, ‖u n x‖ ^ 2 ∂MeasureTheory.volume := by
    have hPoint :
        (fun x => ‖Set.indicator (Set.Icc 0 T) (u n) x‖ ^ 2) =
          Set.indicator (Set.Icc 0 T) (fun x => ‖u n x‖ ^ 2) := by
      funext x
      by_cases hx : x ∈ Set.Icc 0 T
      · simp [Set.indicator_of_mem, hx]
      · simp [Set.indicator_of_notMem, hx]
    rw [hPoint]
    exact integral_indicator (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))
  calc
    ENNReal.ofReal
        ((∫ x, ‖Set.indicator (Set.Icc 0 T) (u n) x‖ ^ 2
            ∂MeasureTheory.volume) ^ ((1 : ℝ) / 2))
        =
        ENNReal.ofReal
          ((∫ x in Set.Icc 0 T, ‖u n x‖ ^ 2
              ∂MeasureTheory.volume) ^ ((1 : ℝ) / 2)) := by
          rw [hIndicatorIntegral]
    _ ≤ ENNReal.ofReal (M ^ ((1 : ℝ) / 2)) :=
      ENNReal.ofReal_le_ofReal hPowLe

/-- KRF's real `unif_l2_bound` supplies the finite indicator `eLpNorm` bound
once the source also supplies indicator `MemLp` for each sequence element. -/
theorem indicator_eLpNorm_bound_of_krf_l2_bound_memLp
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2 MeasureTheory.volume) :
    ∃ C : ℝ≥0∞, C < ∞ ∧
      ∀ n, eLpNorm (Set.indicator (Set.Icc 0 T) (u n)) 2
        MeasureTheory.volume ≤ C := by
  rcases D.unif_l2_bound with ⟨M, _hM_nonneg, hBound⟩
  exact indicator_eLpNorm_bound_of_setIntegral_bound_memLp hMem hBound

/-- KRF's indicator-form `UnifIntegrable` source becomes a
`UniformIntegrable` source when paired with an explicit finite indicator
`eLpNorm` bound.

The existing `unif_l2_bound` field is intentionally not consumed here: in the
current source shape it is a real integral bound, and the missing proof is
precisely the finite-energy/eLpNorm witness needed to make that bound usable. -/
theorem uniformIntegrable_indicator_of_unifIntegrable_bound
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hBound :
      ∃ C : ℝ≥0∞, C < ∞ ∧
        ∀ n, eLpNorm (Set.indicator (Set.Icc 0 T) (u n)) 2
          MeasureTheory.volume ≤ C) :
    UniformIntegrable
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      2 MeasureTheory.volume :=
  uniformIntegrable_of_unifIntegrable_and_eLpNorm_bound
    (fun n => ((D.meas_u n).indicator
      (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))).aestronglyMeasurable)
    D.unif_integrable hBound

/-- KRF's `UnifIntegrable` and real interval `L²` bound produce the stronger
`UniformIntegrable` source once indicator `MemLp` is supplied explicitly. -/
theorem uniformIntegrable_indicator_of_krf_l2_bound_memLp
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2 MeasureTheory.volume) :
    UniformIntegrable
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      2 MeasureTheory.volume :=
  uniformIntegrable_indicator_of_unifIntegrable_bound D
    (indicator_eLpNorm_bound_of_krf_l2_bound_memLp D hMem)

/-- KRF's `UnifIntegrable` and real interval `L²` bound produce the stronger
`UniformIntegrable` source once the source pays interval square-integrability.
-/
theorem uniformIntegrable_indicator_of_krf_l2_bound_integrableOn
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hInt :
      ∀ n, IntegrableOn (fun t => ‖u n t‖ ^ 2) (Set.Icc 0 T)
        MeasureTheory.volume) :
    UniformIntegrable
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      2 MeasureTheory.volume :=
  uniformIntegrable_indicator_of_krf_l2_bound_memLp D
    (indicator_memLp_of_krf_integrableOn_norm_sq D hInt)

/-- With the repaired KRF data contract, the stronger `UniformIntegrable`
indicator source is available directly from `D`. -/
theorem uniformIntegrable_indicator_of_krf_data
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u) :
    UniformIntegrable
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
  2 MeasureTheory.volume :=
  uniformIntegrable_indicator_of_krf_l2_bound_integrableOn D D.integrable_norm_sq

/-- The repaired KRF data contract supplies the sequence-side restricted
`MemLp` witnesses consumed by the row-20 source contracts. -/
theorem restrictedMemLp_of_krf_data
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u) :
    ∀ n, MemLp (u n) 2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) :=
  restricted_memLp_of_uniformIntegrable_indicator
    (uniformIntegrable_indicator_of_krf_data D)

/-- Selected-family form of `restrictedMemLp_of_krf_data`. -/
theorem selectedRestrictedMemLp_of_krf_data
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u) (φ : ℕ → ℕ) :
    ∀ n, MemLp (u (φ n)) 2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) := by
  intro n
  exact restrictedMemLp_of_krf_data D (φ n)

/-- Direct row-20 a.e. consumer for the actual one-sided mollifier-rate
orientation plus an Arzelà/Cantor uniform-distance envelope, with the
selected-family restricted `MemLp` source paid from `KolmogorovRieszFrechetData`.
-/
theorem ae_subsequence_of_krf_data_one_sided_rate_uniform_dist_krf_mem
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (limit : ℝ → B)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt n (φ n) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smoothAt n (φ n) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (c : ℕ → ℝ)
    (hSmoothDist :
      ∀ n t, t ∈ Set.Icc 0 T →
        dist (smoothAt n (φ n) t) (limit t) ≤ c n)
    (hSmoothEnvelope :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ n in atTop,
          ((MeasureTheory.volume.restrict (Set.Icc 0 T)) Set.univ) ^
              (2 : ENNReal).toReal⁻¹ *
            ENNReal.ofReal (c n) <
            ENNReal.ofReal ε) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_one_sided_rate_and_uniform_dist_source
    D φ hφ (selectedRestrictedMemLp_of_krf_data D φ) smoothAt
    hApproxMeas hApproxRate limit hSmoothLeftMeas hSmoothRightMeas
    c hSmoothDist hSmoothEnvelope

/-- Direct row-20 a.e. consumer for the actual one-sided mollifier-rate
orientation plus an Arzelà/Cantor `TendstoUniformlyOn` output on `[0,T]`,
with the selected-family restricted `MemLp` source paid from
`KolmogorovRieszFrechetData`.

The finite-measure scalar conversion remains explicit through `hSmoothScale`;
this keeps the Arzelà source boundary separate from the interval-measure
normalization needed to turn uniform convergence into restricted `eLpNorm`
convergence. -/
theorem ae_subsequence_of_krf_data_one_sided_rate_tendstoUniformlyOn_krf_mem
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (limit : ℝ → B)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt n (φ n) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smoothAt n (φ n) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniform :
      TendstoUniformlyOn
        (fun n t => smoothAt n (φ n) t) limit atTop (Set.Icc 0 T))
    (hSmoothScale :
      ∀ ε : ℝ, 0 < ε →
        ∃ η : ℝ, 0 < η ∧
          ((MeasureTheory.volume.restrict (Set.Icc 0 T)) Set.univ) ^
              (2 : ENNReal).toReal⁻¹ *
            ENNReal.ofReal η <
            ENNReal.ofReal ε) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_one_sided_real_source_outputs
    D φ hφ (selectedRestrictedMemLp_of_krf_data D φ) smoothAt
    hApproxMeas hApproxRate
    (LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn
      hSmoothLeftMeas hSmoothRightMeas hSmoothUniform hSmoothScale)

/-- Direct row-20 a.e. consumer for the actual one-sided mollifier-rate
orientation plus an Arzelà/Cantor `TendstoUniformlyOn` output on `[0,T]`.

Unlike `ae_subsequence_of_krf_data_one_sided_rate_tendstoUniformlyOn_krf_mem`,
this wrapper also pays the restricted interval scalar gauge internally via
`restricted_Icc_volume_l2_scalar_gauge`. -/
theorem ae_subsequence_of_krf_data_one_sided_rate_tendstoUniformlyOn_Icc_krf_mem
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (limit : ℝ → B)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt n (φ n) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smoothAt n (φ n) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniform :
      TendstoUniformlyOn
        (fun n t => smoothAt n (φ n) t) limit atTop (Set.Icc 0 T)) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_one_sided_real_source_outputs
    D φ hφ (selectedRestrictedMemLp_of_krf_data D φ) smoothAt
    hApproxMeas hApproxRate
    (LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn_Icc
      hSmoothLeftMeas hSmoothRightMeas hSmoothUniform)

/-- Direct row-20 a.e. consumer for the actual one-sided mollifier-rate
orientation plus an Arzelà/Cantor source in its all-compact uniform-convergence
shape.

The caller still owns the important alignment fact: the all-compact Arzelà
source must be for the selected smoothed family `fun n => smoothAt n (φ n)`.
-/
theorem ae_subsequence_of_krf_data_one_sided_rate_tendstoUniformlyOn_compacts_krf_mem
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (limit : ℝ → B)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt n (φ n) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smoothAt n (φ n) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t => smoothAt n (φ n) t) limit atTop K) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_one_sided_real_source_outputs
    D φ hφ (selectedRestrictedMemLp_of_krf_data D φ) smoothAt
    hApproxMeas hApproxRate
    (LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn_compacts
      hSmoothLeftMeas hSmoothRightMeas hSmoothUniformCompacts)

/-- Direct row-20 a.e. consumer for the Phase-A scale selected along an
Arzelà/Cantor extraction.

The scale selector `κ` is explicit: Phase-A is still uniform in the mollifier
scale, but the Arzelà smoothed family may be sampled at `smoothAt (κ n) (φ n)`.
-/
theorem ae_subsequence_of_krf_data_one_sided_rate_tendstoUniformlyOn_compacts_reindexed_krf_mem
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ : ℕ → ℕ) (hφ : StrictMono φ)
    (smoothAt : ℕ → ℕ → ℝ → B)
    (κ : ℕ → ℕ) (hκ : Tendsto κ atTop atTop)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (limit : ℝ → B)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt (κ n) (φ n) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smoothAt (κ n) (φ n) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t => smoothAt (κ n) (φ n) t) limit atTop K) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_unary_smoothed_limit_source_output D
    (KRFUnarySmoothedLimitSourceOutput_of_uniform_scale_real_tendsto_and_smoothed_limit
      φ hφ (selectedRestrictedMemLp_of_krf_data D φ)
      smoothAt κ hκ
      (UniformScaleApproximationELpNormRealOutput_of_one_sided
        hApproxMeas hApproxRate)
      (LinkedSmoothedLimitELpNormOutput_of_real
        (LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn_compacts
          hSmoothLeftMeas hSmoothRightMeas hSmoothUniformCompacts)))

/-- Direct row-20 a.e. consumer for an actual Arzelà/Cantor subsequence
selector.

If the Arzelà step extracts `σ`, the row-20 selected family is `φ0 ∘ σ` and
the mollifier scale selector is the same `σ`.  This packages the common
subsequence-alignment instantiation of
`ae_subsequence_of_krf_data_one_sided_rate_tendstoUniformlyOn_compacts_reindexed_krf_mem`.
-/
theorem ae_subsequence_of_krf_data_one_sided_rate_arzela_subseq_krf_mem
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ0 σ : ℕ → ℕ) (hφ0 : StrictMono φ0) (hσ : StrictMono σ)
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm (fun t => smoothAt k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (limit : ℝ → B)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt (σ n) (φ0 (σ n)) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smoothAt (σ n) (φ0 (σ n)) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t => smoothAt (σ n) (φ0 (σ n)) t) limit atTop K) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_one_sided_rate_tendstoUniformlyOn_compacts_reindexed_krf_mem
    D (φ0 ∘ σ) (hφ0.comp hσ) smoothAt σ hσ.tendsto_atTop
    hApproxMeas hApproxRate limit
    hSmoothLeftMeas hSmoothRightMeas hSmoothUniformCompacts

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

/-- Limit-side `MemLp` reconstruction from convergence in measure plus an
eventual `eLpNorm` bound.

This is the convergence-in-measure sibling of
`memLp_limit_of_ae_tendsto_eLpNorm_bound`; it uses Mathlib's
`eLpNorm_le_of_tendstoInMeasure` rather than extracting an a.e. limit first. -/
theorem memLp_limit_of_tendstoInMeasure_eLpNorm_bound
    {α : Type*} [MeasurableSpace α]
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {μ : Measure α} {ι : Type*} {l : Filter ι} [NeBot l] [IsCountablyGenerated l]
    {f : ι → α → B} {g : α → B} {C : ℝ≥0∞}
    (hBound : ∀ᶠ n in l, eLpNorm (f n) 2 μ ≤ C)
    (hC : C < ∞)
    (hf : ∀ n, AEStronglyMeasurable (f n) μ)
    (hTendsto : TendstoInMeasure μ f l g) :
    MemLp g 2 μ :=
  ⟨hTendsto.aestronglyMeasurable hf,
    lt_of_le_of_lt (eLpNorm_le_of_tendstoInMeasure hBound hTendsto hf) hC⟩

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

/-- The exact row-20 upstream source contract after the Fatou/Vitali split:
`UniformIntegrable` supplies the selected-family `MemLp` side, while each
diagonal limit only needs a.e. convergence plus an eventual finite `eLpNorm`
bound to supply the limit-side `MemLp` side. -/
theorem cantor_integral_output_to_tail_finite_energy_output_with_ae_bound_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : CantorDiagonalOutput T u)
    (hUI :
      UniformIntegrable
        (fun n => Set.indicator (Set.Icc 0 T) (u n))
        2 MeasureTheory.volume)
    (hLimit :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        (∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
          Tendsto (fun n => u (φ n) t) atTop (𝓝 (uInf t))) ∧
        ∃ C : ℝ≥0∞, C < ∞ ∧
          ∀ᶠ n in atTop,
            eLpNorm (u (φ n)) 2
              (MeasureTheory.volume.restrict (Set.Icc 0 T)) ≤ C) :
    CantorDiagonalTailFiniteEnergyOutput T u := by
  refine cantor_integral_output_to_tail_finite_energy_output_with_uniformIntegrable_source
    hOut hUI ?_
  intro φ uInf hφ hSM hIntegral
  obtain ⟨hAe, C, hC, hBound⟩ := hLimit φ uInf hφ hSM hIntegral
  exact memLp_limit_of_ae_tendsto_eLpNorm_bound
    hSM.aestronglyMeasurable hBound hC
    (fun n => (restricted_memLp_of_uniformIntegrable_indicator hUI (φ n)).aestronglyMeasurable)
    hAe

/-- The boundedness half of Mathlib's `UniformIntegrable` indicator source
transports to a uniform `eLpNorm` bound over the restricted interval measure. -/
theorem eventually_restricted_eLpNorm_bound_of_uniformIntegrable_indicator
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B} (φ : ℕ → ℕ)
    (hUI :
      UniformIntegrable
        (fun n => Set.indicator (Set.Icc 0 T) (u n))
        2 MeasureTheory.volume) :
    ∃ C : ℝ≥0∞, C < ∞ ∧
      ∀ᶠ n in atTop,
        eLpNorm (u (φ n)) 2
          (MeasureTheory.volume.restrict (Set.Icc 0 T)) ≤ C := by
  obtain ⟨C, hC⟩ := hUI.2.2
  refine ⟨C, ENNReal.coe_lt_top, ?_⟩
  exact Filter.Eventually.of_forall fun n => by
    rw [← eLpNorm_indicator_eq_eLpNorm_restrict
      (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))]
    exact hC (φ n)

/-- With Mathlib's stronger `UniformIntegrable` source, row 20 only needs the
a.e.-convergence half of the upstream KRF/Cantor diagonal output. The eventual
finite `eLpNorm` bound is already part of `UniformIntegrable` and transports
through the indicator/restricted-measure bridge above. -/
theorem cantor_integral_output_to_tail_finite_energy_output_with_ae_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : CantorDiagonalOutput T u)
    (hUI :
      UniformIntegrable
        (fun n => Set.indicator (Set.Icc 0 T) (u n))
        2 MeasureTheory.volume)
    (hAe :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
          Tendsto (fun n => u (φ n) t) atTop (𝓝 (uInf t))) :
    CantorDiagonalTailFiniteEnergyOutput T u := by
  refine cantor_integral_output_to_tail_finite_energy_output_with_ae_bound_source
    hOut hUI ?_
  intro φ uInf hφ hSM hIntegral
  exact ⟨hAe φ uInf hφ hSM hIntegral,
    eventually_restricted_eLpNorm_bound_of_uniformIntegrable_indicator φ hUI⟩

/-- Convergence in measure is now enough for the row-20 source contract: the
limit-side `MemLp` witness follows from `UniformIntegrable`'s transported bound
and `memLp_limit_of_tendstoInMeasure_eLpNorm_bound`. -/
theorem cantor_integral_output_to_tail_finite_energy_output_with_inMeasure_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (hOut : CantorDiagonalOutput T u)
    (hUI :
      UniformIntegrable
        (fun n => Set.indicator (Set.Icc 0 T) (u n))
        2 MeasureTheory.volume)
    (hInMeasure :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        TendstoInMeasure
          (MeasureTheory.volume.restrict (Set.Icc 0 T))
          (fun n t => u (φ n) t) atTop uInf) :
    CantorDiagonalTailFiniteEnergyOutput T u := by
  refine cantor_integral_output_to_tail_finite_energy_output_with_uniformIntegrable_source
    hOut hUI ?_
  intro φ uInf hφ _hSM hIntegral
  obtain ⟨C, hC, hBound⟩ :=
    eventually_restricted_eLpNorm_bound_of_uniformIntegrable_indicator φ hUI
  exact memLp_limit_of_tendstoInMeasure_eLpNorm_bound hBound hC
    (fun n => (restricted_memLp_of_uniformIntegrable_indicator hUI (φ n)).aestronglyMeasurable)
    (hInMeasure φ uInf hφ _hSM hIntegral)

/-- Row-20 source contract stated in the exact currency of
`KolmogorovRieszFrechetData`: its `UnifIntegrable` field is enough once the
upstream proof separately supplies the finite indicator `eLpNorm` bound and the
diagonal convergence-in-measure receipt.

This is one step closer to the actual KRF source than the probability-style
`UniformIntegrable` theorem above. It deliberately keeps the finite bound
explicit, because deriving it from the current real-integral `unif_l2_bound`
would be the same source-currency gap in another form. -/
theorem cantor_tail_finite_of_krf_unif_bound_inMeasure_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hBound :
      ∃ C : ℝ≥0∞, C < ∞ ∧
        ∀ n, eLpNorm (Set.indicator (Set.Icc 0 T) (u n)) 2
          MeasureTheory.volume ≤ C)
    (hInMeasure :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        TendstoInMeasure
          (MeasureTheory.volume.restrict (Set.Icc 0 T))
          (fun n t => u (φ n) t) atTop uInf) :
    CantorDiagonalTailFiniteEnergyOutput T u :=
  cantor_integral_output_to_tail_finite_energy_output_with_inMeasure_source
    hOut (uniformIntegrable_indicator_of_unifIntegrable_bound D hBound) hInMeasure

/-- Row-20 source contract in KRF currency, with the finite indicator bound
derived from `D.unif_l2_bound` once indicator `MemLp` is available. -/
theorem cantor_tail_finite_of_krf_l2_memLp_inMeasure_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2 MeasureTheory.volume)
    (hInMeasure :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        TendstoInMeasure
          (MeasureTheory.volume.restrict (Set.Icc 0 T))
          (fun n t => u (φ n) t) atTop uInf) :
    CantorDiagonalTailFiniteEnergyOutput T u :=
  cantor_integral_output_to_tail_finite_energy_output_with_inMeasure_source
    hOut (uniformIntegrable_indicator_of_krf_l2_bound_memLp D hMem) hInMeasure

/-- KRF row-20 in-measure source contract with the indicator `MemLp` side paid
from interval square-integrability of the source sequence. -/
theorem cantor_tail_finite_of_krf_l2_integrableOn_inMeasure_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hInt :
      ∀ n, IntegrableOn (fun t => ‖u n t‖ ^ 2) (Set.Icc 0 T)
        MeasureTheory.volume)
    (hInMeasure :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        TendstoInMeasure
          (MeasureTheory.volume.restrict (Set.Icc 0 T))
          (fun n t => u (φ n) t) atTop uInf) :
    CantorDiagonalTailFiniteEnergyOutput T u :=
  cantor_integral_output_to_tail_finite_energy_output_with_inMeasure_source
    hOut (uniformIntegrable_indicator_of_krf_l2_bound_integrableOn D hInt)
    hInMeasure

/-- With the repaired KRF data contract, row 20's in-measure source contract
only needs the diagonal output and convergence-in-measure receipt. -/
theorem cantor_tail_finite_of_krf_data_inMeasure_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hInMeasure :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        TendstoInMeasure
          (MeasureTheory.volume.restrict (Set.Icc 0 T))
          (fun n t => u (φ n) t) atTop uInf) :
    CantorDiagonalTailFiniteEnergyOutput T u :=
  cantor_integral_output_to_tail_finite_energy_output_with_inMeasure_source
    hOut (uniformIntegrable_indicator_of_krf_data D) hInMeasure

/-- A.e. version of the same KRF-native source contract.  It is useful when
the upstream Cantor construction pays a.e. convergence directly rather than
first producing convergence in measure. -/
theorem cantor_tail_finite_of_krf_unif_bound_ae_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hBound :
      ∃ C : ℝ≥0∞, C < ∞ ∧
        ∀ n, eLpNorm (Set.indicator (Set.Icc 0 T) (u n)) 2
          MeasureTheory.volume ≤ C)
    (hAe :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
          Tendsto (fun n => u (φ n) t) atTop (𝓝 (uInf t))) :
    CantorDiagonalTailFiniteEnergyOutput T u :=
  cantor_integral_output_to_tail_finite_energy_output_with_ae_source
    hOut (uniformIntegrable_indicator_of_unifIntegrable_bound D hBound) hAe

/-- A.e. source-contract sibling with the finite indicator bound derived from
the KRF real `L²` bound plus explicit indicator `MemLp`. -/
theorem cantor_tail_finite_of_krf_l2_memLp_ae_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2 MeasureTheory.volume)
    (hAe :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
          Tendsto (fun n => u (φ n) t) atTop (𝓝 (uInf t))) :
    CantorDiagonalTailFiniteEnergyOutput T u :=
  cantor_integral_output_to_tail_finite_energy_output_with_ae_source
    hOut (uniformIntegrable_indicator_of_krf_l2_bound_memLp D hMem) hAe

/-- KRF row-20 a.e. source-contract sibling with the indicator `MemLp` side
paid from interval square-integrability of the source sequence. -/
theorem cantor_tail_finite_of_krf_l2_integrableOn_ae_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hInt :
      ∀ n, IntegrableOn (fun t => ‖u n t‖ ^ 2) (Set.Icc 0 T)
        MeasureTheory.volume)
    (hAe :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
          Tendsto (fun n => u (φ n) t) atTop (𝓝 (uInf t))) :
    CantorDiagonalTailFiniteEnergyOutput T u :=
  cantor_integral_output_to_tail_finite_energy_output_with_ae_source
    hOut (uniformIntegrable_indicator_of_krf_l2_bound_integrableOn D hInt) hAe

/-- With the repaired KRF data contract, row 20's a.e. source contract only
needs the diagonal output and a.e. convergence receipt. -/
theorem cantor_tail_finite_of_krf_data_ae_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hAe :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
          Tendsto (fun n => u (φ n) t) atTop (𝓝 (uInf t))) :
    CantorDiagonalTailFiniteEnergyOutput T u :=
  cantor_integral_output_to_tail_finite_energy_output_with_ae_source
    hOut (uniformIntegrable_indicator_of_krf_data D) hAe

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

/-- Row-20 consumer bridge in repaired KRF data currency: once the upstream
Cantor/KRF source pays convergence in measure for the selected diagonal limit,
the checked tail-finite-energy bridge and Mathlib a.e.-subsequence extraction
give the target a.e. compactness conclusion. -/
theorem ae_subsequence_of_krf_data_inMeasure_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hInMeasure :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        TendstoInMeasure
          (MeasureTheory.volume.restrict (Set.Icc 0 T))
          (fun n t => u (φ n) t) atTop uInf) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_cantor_tail_finite_energy_output D
    (cantor_tail_finite_of_krf_data_inMeasure_source D hOut hInMeasure)

/-- A.e.-source sibling of `ae_subsequence_of_krf_data_inMeasure_source`.
This keeps the upstream convergence-source obligation explicit when the
diagonal construction pays a.e. convergence directly. -/
theorem ae_subsequence_of_krf_data_ae_source
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (hOut : CantorDiagonalOutput T u)
    (hAe :
      ∀ (φ : ℕ → ℕ) (uInf : ℝ → B),
        StrictMono φ →
        StronglyMeasurable uInf →
        Tendsto
          (fun n => ∫ t in Set.Icc 0 T, ‖u (φ n) t - uInf t‖ ^ 2)
          atTop (𝓝 0) →
        ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
          Tendsto (fun n => u (φ n) t) atTop (𝓝 (uInf t))) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_cantor_tail_finite_energy_output D
    (cantor_tail_finite_of_krf_data_ae_source D hOut hAe)

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
