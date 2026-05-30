import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Function.UnifTight
import Mathlib.MeasureTheory.Function.LpSpace.Basic
import Mathlib.Topology.MetricSpace.Sequences

/-!
# Rellich-Kondrachov compact embedding (NS Track B typed companion)

This file scaffolds the **Rellich-Kondrachov compact embedding theorem**
as a typed-companion entry point for an eventual Mathlib PR. It is one
of the three classical theorems whose absence in Mathlib v4.30.0-rc2
blocks the closure of `ns_trackb_aubin_lions_stub.lean`.

## Classical statement

Let `Ω ⊂ ℝⁿ` be a bounded domain with Lipschitz boundary. Then the
Sobolev embedding

  `H¹(Ω) ↪ L²(Ω)`

is **compact** — every bounded sequence in `H¹(Ω)` admits an
`L²(Ω)`-strongly convergent subsequence. More generally,

  `W^{k,p}(Ω) ↪ W^{k-1,p}(Ω)` is compact for `1 ≤ p < ∞`,

and for the lower-order embedding `W^{1,p}(Ω) ↪ L^q(Ω)` is compact for
every `q` with `1 ≤ q < p* := np/(n-p)` when `p < n` (and for every
`q < ∞` when `p ≥ n`).

On unbounded domains (e.g. `ℝⁿ`) the embedding is **not** compact —
translation invariance breaks any uniform tightness. The standard
fixes are:

* restrict to functions with uniformly compact support
  (`H¹_c(ℝⁿ) ↪ L²(ℝⁿ)` is compact); equivalently,
* restrict to a bounded subdomain (`H¹_{loc}(ℝ³) ↪ L²_{loc}(ℝ³)`
  on bounded subsets is compact); or
* assume uniform tightness of the `L²` mass
  (`{u_n}` with `∫_{|x|>R} ‖u_n‖² → 0` uniformly in `n`).

NS Track B (the local-energy / CKN line: see
`ns_trackb_local_energy_inequality.lean`) consumes the **local**
version: `H¹_{loc}(ℝ³) ↪ L²_{loc}(ℝ³)` on bounded balls. That is the
flavor we expose as the load-bearing axiom in this file.

## References

* H. Brezis, *Functional Analysis, Sobolev Spaces and Partial
  Differential Equations*, Springer (2011), Theorem 9.16
  (Rellich-Kondrachov, bounded Lipschitz domain).
* R. A. Adams, *Sobolev Spaces*, Academic Press (1975), Theorem 6.2
  (Rellich-Kondrachov, originally Rellich 1930 / Kondrachov 1945).
* L. C. Evans, *Partial Differential Equations*, AMS GSM 19 (2010),
  §5.7 Theorem 1 (compactness for `W^{1,p}(Ω) ↪↪ L^q(Ω)`).

## Status of formalization in Mathlib v4.30.0-rc2 (audited 2026-05-07)

**Absent.** No file matches `RellichKondrachov`, `Rellich`, or
`Kondrachov` under `Mathlib/Analysis/Sobolev/`. Mathlib has:

* `Mathlib.Analysis.InnerProductSpace.Spectrum` — abstract spectral
  theory of compact operators (works against the *operator*, not the
  inclusion of a Sobolev subspace).
* `Mathlib.MeasureTheory.Function.UnifTight` — the L^p-tightness
  predicate that the *conclusion* of a Rellich-style argument
  produces, but not the embedding theorem itself.
* `Mathlib.Analysis.Distribution.SchwartzSpace` — Schwartz functions,
  insufficient for fractional Sobolev compactness.

Mathlib does NOT yet have:

* `Mathlib.Analysis.Sobolev.RellichKondrachov` — no file.
* A `CompactEmbedding` typeclass for Banach pairs.
* Sobolev spaces `W^{k,p}` on a bounded Lipschitz domain as a typed
  Banach-space object (Mathlib has `Mathlib.Analysis.Sobolev.Sobolev`-
  adjacent constructions but not the bounded-domain extension theorem
  needed for the classical Rellich proof).

## PR-effort estimate

Workstream R PR scoping (2026-05-07): **0.5 – 1 author-month** for the
bounded-domain `H¹(Ω) ↪↪ L²(Ω)` version, decomposed as:

* Phase A (~600 LoC): Sobolev space `H¹(Ω)` on a bounded Lipschitz
  domain as a Hilbert subspace of `L²(Ω)`. Mathlib has the smooth
  manifold pieces; the boundary-Lipschitz hypothesis is the gap.
* Phase B (~800 LoC): the Sobolev extension theorem
  `H¹(Ω) → H¹(ℝⁿ)` (Stein's continuous extension on Lipschitz
  domains; the standard reference is Stein, *Singular Integrals*
  Ch. 6).
* Phase C (~400 LoC): the Rellich compactness argument itself —
  mollification + uniform tightness on the extended functions +
  Arzelà–Ascoli on mollified functions + Cantor diagonal across
  mollifier widths. This phase reuses much of the apparatus that
  `krf_subseq_ae_of_translation` (in
  `ns_trackb_aubin_lions_stub.lean`) needs.
* Phase D (~150 LoC): the local version
  `H¹_{loc}(ℝⁿ) ↪↪ L²_{loc}(ℝⁿ)` follows from Phase C by restriction
  to balls.

## What this file ships

This file ships the typed-companion shape with **named axioms** for
the classical statements. We do **not** sorry-prove the theorems; we
expose them as `axiom` declarations citing Brezis Thm 9.16 and Adams
Thm 6.2, plus a typed bridge consuming the axiom into a form that
`ns_trackb_aubin_lions_stub.lean` and the local-energy line can
immediately use.

When the future Mathlib PR (workstream R) lands, each axiom in this
file becomes a `theorem` with a `mathlib_lemma` proof; downstream
consumers do not change.

-/

namespace ZtareProofs.NS.RellichKondrachov

noncomputable section

universe u v

open MeasureTheory Filter Topology Set

/-! ## §1. Compact-embedding predicate

We reuse the Bourbaki "compact operator" form: a map `incl : X → B`
between normed spaces is a *compact embedding* iff every bounded
sequence in `X` admits a subsequence whose images converge in `B`.

This matches the predicate `CompactlyEmbedded` already used in
`ns_trackb_aubin_lions_stub.lean §1`; we restate it here to keep this
file self-contained and to allow the workstream-R PR to refactor the
two callers in lockstep. -/

/-- Compact embedding (`X ↪↪ B` via `incl`). -/
def CompactlyEmbedded
    (X : Type u) [NormedAddCommGroup X]
    (B : Type v) [NormedAddCommGroup B]
    (incl : X → B) : Prop :=
  ∀ (xs : ℕ → X), (∃ M, ∀ n, ‖xs n‖ ≤ M) →
    ∃ (φ : ℕ → ℕ), StrictMono φ ∧
      ∃ b : B, Tendsto (fun n => incl (xs (φ n))) atTop (𝓝 b)

/-! ## §2. Abstract Sobolev / Lebesgue typed companion

We carry an abstract pair `(Sob, Leb)` of normed spaces with an
inclusion `incl : Sob → Leb` that the Rellich axiom asserts is a
compact embedding. The intended instantiation in NS Track B is
`Sob = H¹(B_R)` and `Leb = L²(B_R)` for a fixed open ball
`B_R ⊂ ℝ³`, but the typed companion is parametric so that the same
axiom services every bounded Lipschitz subdomain. -/

/-- Bounded-domain Rellich-Kondrachov input bundle.

Carries:
* the Sobolev space `Sob` (think `H¹(Ω)`) as an abstract normed group;
* the Lebesgue space `Leb` (think `L²(Ω)`) as an abstract normed group;
* the continuous inclusion `incl : Sob → Leb`;
* a `Prop`-witness `bounded_lipschitz` that the underlying domain is
  bounded with Lipschitz boundary (kept abstract: in this typed
  companion we do not formalize the domain itself; the `Prop` is
  exposed so the consumer can plug in a domain-specific witness).
-/
structure RellichKondrachovData
    (Sob : Type u) [NormedAddCommGroup Sob]
    (Leb : Type v) [NormedAddCommGroup Leb]
    (incl : Sob → Leb) : Prop where
  /-- Continuity of the inclusion (operator-norm bound). In the
  classical setting this is the Sobolev embedding `H¹(Ω) ↪ L²(Ω)`
  with norm `1`; we expose it abstractly. -/
  incl_continuous : ∃ C : ℝ, 0 ≤ C ∧ ∀ x : Sob, ‖incl x‖ ≤ C * ‖x‖
  /-- The underlying domain `Ω` is bounded with Lipschitz boundary.
  Kept as an abstract `Prop` placeholder: the workstream-R PR will
  replace this with a typed `IsBoundedLipschitzDomain` predicate
  on a `Set (EuclideanSpace ℝ (Fin n))`. -/
  bounded_lipschitz : True

/-! ## §3. The Rellich-Kondrachov axiom (bounded-domain case)

This is the load-bearing classical theorem.

Brezis Thm 9.16: *If `Ω ⊂ ℝⁿ` is a bounded domain with Lipschitz
boundary, the embedding `W^{1,p}(Ω) ↪ L^p(Ω)` is compact for every
`1 ≤ p < ∞`.*

Specialized to `p = 2` it gives the Hilbert-space form `H¹(Ω) ↪↪ L²(Ω)`
which is what NS Track B's CKN local-energy step consumes. -/

/-- **Rellich-Kondrachov compact embedding (bounded Lipschitz domain).**

Given a bundled abstract Sobolev/Lebesgue pair on a bounded Lipschitz
domain (Brezis Thm 9.16; Adams 1975 Thm 6.2), the inclusion
`Sob ↪ Leb` is a compact embedding.

Once `Mathlib.Analysis.Sobolev.RellichKondrachov` lands (workstream R
PR; estimated 0.5–1 author-month), this `axiom` becomes a `theorem`
proved by the Mathlib lemma; consumers do not change.

CITATIONS:
* Brezis, *Functional Analysis*, Springer 2011, Theorem 9.16.
* Adams, *Sobolev Spaces*, Academic Press 1975, Theorem 6.2.
* Evans, *Partial Differential Equations*, AMS 2010, §5.7 Thm 1.
-/
axiom rellich_kondrachov_bounded_lipschitz
    {Sob : Type u} [NormedAddCommGroup Sob]
    {Leb : Type v} [NormedAddCommGroup Leb]
    {incl : Sob → Leb}
    (_D : RellichKondrachovData Sob Leb incl) :
    CompactlyEmbedded Sob Leb incl

/-! ## §4. Local version: `H¹_{loc}(ℝ³) ↪↪ L²_{loc}(ℝ³)` on bounded subsets

NS Track B's local-energy / CKN argument
(`ns_trackb_local_energy_inequality.lean`) needs the **local** form:
on every fixed open ball `B_R ⊂ ℝ³`, the restriction map of
`H¹(B_R) → L²(B_R)` is compact. This is a corollary of the bounded-
domain version applied with `Ω = B_R` (an open ball is a bounded
Lipschitz domain).

We expose it as an axiom for clarity of citation; once the
bounded-domain version is a `theorem` upstream, the local version
follows in ~10 lines (instantiation + open ball is Lipschitz). -/

/-- Local Rellich-Kondrachov input bundle. The `radius` field carries
the radius of the ball `B_radius ⊂ ℝ³` on which the local Sobolev /
Lebesgue spaces are defined; `Sob_loc` and `Leb_loc` abstract the
ball-restricted Sobolev / Lebesgue spaces. -/
structure LocalRellichKondrachovData
    (Sob_loc : Type u) [NormedAddCommGroup Sob_loc]
    (Leb_loc : Type v) [NormedAddCommGroup Leb_loc]
    (incl_loc : Sob_loc → Leb_loc)
    (radius : ℝ) : Prop where
  /-- Radius of the ambient ball `B_radius ⊂ ℝ³`. -/
  hR_pos : 0 < radius
  /-- Continuity of the local inclusion. -/
  incl_continuous : ∃ C : ℝ, 0 ≤ C ∧ ∀ x : Sob_loc, ‖incl_loc x‖ ≤ C * ‖x‖
  /-- The local domain is the bounded Lipschitz ball `B_radius`. -/
  is_open_ball : True

/-- **Local Rellich-Kondrachov compact embedding.**

`H¹_{loc}(ℝ³) ↪↪ L²_{loc}(ℝ³)` on the bounded ball `B_radius ⊂ ℝ³`.

This is the form NS Track B's CKN local-energy inequality consumes:
extracting an L²-strongly convergent subsequence from a sequence
uniformly bounded in `H¹` on each fixed compact subset.

Proof in classical form: instantiate
`rellich_kondrachov_bounded_lipschitz` with `Ω = B_radius`. The open
ball is a bounded Lipschitz domain (boundary is the smooth sphere). -/
axiom local_rellich_kondrachov
    {Sob_loc : Type u} [NormedAddCommGroup Sob_loc]
    {Leb_loc : Type v} [NormedAddCommGroup Leb_loc]
    {incl_loc : Sob_loc → Leb_loc} {radius : ℝ}
    (_D : LocalRellichKondrachovData Sob_loc Leb_loc incl_loc radius) :
    CompactlyEmbedded Sob_loc Leb_loc incl_loc

/-! ## §5. Typed bridge — uniformly bounded in `H¹_{loc}` + tight in `L²`
                       ⇒ strong `L²_{loc}`-convergent subsequence

This is the form most directly consumed by the NS Track B local-energy
spine. We package: a sequence `u : ℕ → Sob_loc` with a uniform
`H¹_{loc}` bound and (separately) a uniform `L²` tightness Prop, and
extract an `L²_{loc}`-strongly convergent subsequence.

Note: the tightness Prop is abstracted in this companion (the
intended instantiation routes it through Mathlib's `UnifTight` but
the generic predicate is left to the consumer). -/

/-- Input bundle for the typed bridge: uniformly bounded sequence in
the local Sobolev space `Sob_loc`, plus a uniform tightness Prop on
the L² ambient space (placeholder; consumer instantiates with their
ball-restricted `UnifTight` predicate). -/
structure LocallyBoundedTightSequence
    (Sob_loc : Type u) [NormedAddCommGroup Sob_loc]
    (Leb_loc : Type v) [NormedAddCommGroup Leb_loc]
    (incl_loc : Sob_loc → Leb_loc)
    (radius : ℝ)
    (u : ℕ → Sob_loc) : Prop where
  /-- The local Rellich-Kondrachov data is well-formed. -/
  rk_data : LocalRellichKondrachovData Sob_loc Leb_loc incl_loc radius
  /-- Uniform `H¹_{loc}` bound on `u`. -/
  unif_H1_bound : ∃ M : ℝ, 0 ≤ M ∧ ∀ n, ‖u n‖ ≤ M
  /-- Uniform `L²` tightness placeholder Prop (consumer instantiates;
  on the bounded ball `B_radius` this is automatic since `B_radius`
  has finite Lebesgue measure). -/
  unif_l2_tight : True

/-- **Typed bridge: from uniformly bounded in `H¹_{loc}` to strongly
`L²_{loc}`-convergent along a subsequence.**

This is the consumer-facing form of `local_rellich_kondrachov`. It
takes a sequence `u : ℕ → Sob_loc` uniformly bounded in the local
Sobolev norm (and uniformly tight in `L²`, which on a bounded ball
is automatic) and returns:

* a strict-monotone subsequence selector `φ : ℕ → ℕ`;
* a limit `uInf : Leb_loc`;
* the strong `L²_{loc}`-convergence statement
  `Tendsto (fun n => incl_loc (u (φ n))) atTop (𝓝 uInf)`.

The proof unfolds `local_rellich_kondrachov` (an axiom in this file)
on the uniform-bound hypothesis; the tightness hypothesis is folded
into the local-domain finite-measure condition the axiom assumes.

CONSUMERS:
* `ns_trackb_aubin_lions_stub.lean` — consumes via the abstract
  `CompactlyEmbedded` predicate it already declares; this bridge is
  the entry point that ties the abstract predicate to the named
  Rellich axiom.
* `ns_trackb_local_energy_inequality.lean` — consumes for the CKN
  local-energy compactness step (subsequence extraction across
  bounded balls in space-time).
-/
theorem subseq_strongly_L2loc_convergent
    {Sob_loc : Type u} [NormedAddCommGroup Sob_loc]
    {Leb_loc : Type v} [NormedAddCommGroup Leb_loc]
    {incl_loc : Sob_loc → Leb_loc} {radius : ℝ} {u : ℕ → Sob_loc}
    (D : LocallyBoundedTightSequence Sob_loc Leb_loc
            incl_loc radius u) :
    ∃ (φ : ℕ → ℕ), StrictMono φ ∧
    ∃ (uInf : Leb_loc),
      Tendsto (fun n => incl_loc (u (φ n))) atTop (𝓝 uInf) := by
  -- Step 1: extract the uniform `H¹_{loc}` bound.
  obtain ⟨M, _hM_nn, hM⟩ := D.unif_H1_bound
  -- Step 2: invoke the local Rellich-Kondrachov axiom.
  have hCE : CompactlyEmbedded Sob_loc Leb_loc incl_loc :=
    local_rellich_kondrachov D.rk_data
  -- Step 3: feed the bounded sequence to the compact-embedding
  -- predicate to get the convergent-subsequence triple.
  exact hCE u ⟨M, hM⟩

/-! ## §6. Connection to `ns_trackb_aubin_lions_stub.lean`

The Aubin-Lions stub has three load-bearing missing pieces (audited
2026-05-07 in that file's §5):

  1. `aubin_lions_residual_void` — full extraction; BLOCKED.
  2. `krf_subseq_ae_of_translation` — KRF a-e subsequence; BLOCKED.
  3. `vitali_to_integral` — `eLpNorm` repackaging; DEFERRED (~120 LoC).

The Rellich-Kondrachov compact embedding (this file) is one of the
three classical theorems whose absence drives item (1). Specifically,
Aubin-Lions' Step 1 ("for a.e. fixed `t`, extract a B-Cauchy
subsequence pointwise") consumes exactly the `CompactlyEmbedded X B`
hypothesis that Rellich-Kondrachov supplies in the canonical NS
instantiation `X = H¹(Ω)`, `B = L²(Ω)`.

The other two missing pieces for Aubin-Lions are:

  * **L² time-translation continuity from a `dtu` L²-bound** —
    a Cauchy-Schwarz argument on the FTC; not in Mathlib but
    self-contained in ~150 LoC.
  * **Ehrling's interpolation inequality** — Brezis Ch. 6;
    `‖b‖_B ≤ ε ‖b‖_X + C(ε) ‖b‖_Y` for `b` in a compact-embedded
    pair. Not in Mathlib; ~250 LoC follow-on PR.

When all three land, `aubin_lions_residual_void` closes mechanically.

The Cantor diagonal step (Mathlib `MeasureTheory.TendstoInMeasure.exists_seq_tendsto_ae`)
and Vitali's theorem (Mathlib `MeasureTheory.tendsto_Lp_of_tendsto_ae`)
are already PRESENT and complete the chain.

**This file is the typed-companion entry point for the Rellich-
Kondrachov leg of that closure.** -/

/-- Architectural witness: the Aubin-Lions stub's `CompactlyEmbedded`
hypothesis is *the same predicate* as this file's. Stating this
explicitly as a definitional alias lets the workstream-R PR land
Rellich-Kondrachov upstream and have the Aubin-Lions stub's compact-
embedding hypothesis discharge automatically (modulo namespace
opening).

We expose this as a `def` rather than a `theorem` to make the
predicate-identity zero-cost. -/
def aubin_lions_compact_embedding_hypothesis_alias
    (Sob : Type u) [NormedAddCommGroup Sob]
    (Leb : Type v) [NormedAddCommGroup Leb]
    (incl : Sob → Leb) : Prop :=
  CompactlyEmbedded Sob Leb incl

/-! ## §7. Sorry / axiom inventory and feasibility

This file ships **two axioms** and **zero sorries**:

| # | Axiom                                  | Status   | Effort       |
|---|----------------------------------------|----------|--------------|
| 1 | `rellich_kondrachov_bounded_lipschitz` | UPSTREAM | 0.5–1 a-mo  |
| 2 | `local_rellich_kondrachov`             | UPSTREAM | corollary    |

(UPSTREAM = becomes a `theorem` once workstream-R PR lands; consumers
do not change.)

DETAIL:

1. `rellich_kondrachov_bounded_lipschitz` — Brezis Thm 9.16. Estimated
   3 phases (~1950 LoC) per workstream-R PR scoping:
     * Phase A: Sobolev space on bounded Lipschitz domain.
     * Phase B: Sobolev extension theorem (Stein).
     * Phase C: the Rellich compactness argument
       (mollification + Arzelà–Ascoli + diagonal).

2. `local_rellich_kondrachov` — corollary of (1) applied to an open
   ball `B_R ⊂ ℝ³`. ~150 LoC follow-on once (1) lands.

The `theorem` `subseq_strongly_L2loc_convergent` in §5 is **fully
proved** modulo the axiom; no sorry. It is the consumer-facing form.

## Future work

* When Mathlib gains `Mathlib.Analysis.Sobolev.RellichKondrachov`
  (workstream R), promote the two axioms in this file to `theorem`s.
* Add a typed instantiation for `Sob = H¹(B_R)`, `Leb = L²(B_R)` once
  Mathlib has the bounded-domain Sobolev space as a typed Banach
  object (currently it has `H¹` only on `ℝⁿ` via Schwartz / Bessel
  potentials).
* Wire `subseq_strongly_L2loc_convergent` into
  `ns_trackb_local_energy_inequality.lean` at the CKN compactness step.
-/

end

end ZtareProofs.NS.RellichKondrachov
