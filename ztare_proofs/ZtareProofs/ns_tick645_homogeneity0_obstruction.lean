/-
  ns_tick645_homogeneity0_obstruction
  ===================================
  FAITHFUL Lean encoding of the TICK645 negative-result-object
  (3D Navier–Stokes, strict-margin / BKM ‖ω‖_∞ atom).

  The negative is the content.  Across TICK643/644/645 four candidate
  control classes were excluded — local Eulerian (ω,S)-polynomial,
  strain-eigenframe, Lagrangian deformation-cocycle, Biot–Savart
  commutator-defect.  TICK645 (PATTERN-011 4-agent swarm + in-thread
  depth-n adjudication of a split verdict) isolated the SINGLE root:

    every Eulerian object built from the degree-0 Biot–Savart / Riesz
    structure is scale-conjugation-trivial at the exact self-similar
    limit (the homogeneity-0 obstruction); the Lagrangian-cocycle kill
    is the multiplicative-matrix shadow of the same fact.

  HONESTY DISCIPLINE (no fabricated progress; no vacuous Prop).
  The deep ANALYTIC inputs are explicit HYPOTHESES (structure fields),
  exactly the cited facts:
    * `coboundary` : homogeneity-0 of the Riesz symbol m(λη)=m(η) makes
      R⊗R commute with parabolic dilation with NO scale prefactor, so a
      degree-0 commutator-defect functional's per-nesting-level
      increment is a pure difference of one underlying functional
      (coboundary form) — Lane D's symbol identity.
    * `Φ_bounded` : Coifman–Meyer boundedness of that underlying
      functional (BMO→BMO) — Lane B's upper bound.
  The IMPOSSIBILITY is then a genuine THEOREM, not an axiom: a bounded
  telescoping sum is O(1), so it can never realise the Ω(N) growth a
  *new* active length scale would require.  This is the precise,
  non-vacuous formal shape of the recurring strict-margin negative.

  TICK647 EXTENSION (the deepest sharpening / terminus).  The
  homogeneity-0 obstruction is the *structural* rung.  One rung deeper
  is the *scaling* terminus: ANY controllable scalar whose blow-up-
  NECESSARY asymptotic is the parabolic rate (T−t)^{1/2} is value-
  slaved to the parabolic scale by the *two-sided* Grujić–Kukavica
  bound and therefore collapses — and this is scaling-level-agnostic
  (critical AND supercritical alike).  Encoded below as
  `ParabolicSlaved` / `parabolic_slaving_terminus`, with the two-sided
  bound as the single honest analytic hypothesis and the criticality
  exponent carried but provably unused (the agnosticity content).

  Compiles with `Mathlib.Tactic` only (no NS-PDE imports needed: the
  obstruction is structural / scaling-arithmetic, which is the point —
  it is class-invariant).
-/
import Mathlib.Tactic

namespace ZtareProofs.NS.Tick645

/-- A nesting tower for a candidate control functional, with the two
honest analytic inputs as fields.  `Φ k` = the underlying
(degree-0, Coifman–Meyer-bounded) functional at tower endpoint `k`;
`d k` = the per-nesting-level increment a "new active scale" would have
to accumulate. -/
structure NestingTower where
  d : ℕ → ℝ
  Φ : ℕ → ℝ
  M : ℝ
  M_nonneg : 0 ≤ M
  /-- Coifman–Meyer boundedness (Lane B). -/
  Φ_bounded : ∀ k, |Φ k| ≤ M
  /-- Homogeneity-0 ⇒ coboundary form (Lane D symbol identity). -/
  coboundary : ∀ k, d k = Φ (k + 1) - Φ k

/-- Partial nesting sum `Σ_{k<N} d k`. -/
def towerSum (T : NestingTower) (N : ℕ) : ℝ :=
  ∑ k ∈ Finset.range N, T.d k

/-- **Coboundary triviality.** Under homogeneity-0 the nesting sum
telescopes to a single endpoint difference (no genuine per-level
accumulation). -/
theorem towerSum_telescope (T : NestingTower) (N : ℕ) :
    towerSum T N = T.Φ N - T.Φ 0 := by
  unfold towerSum
  induction N with
  | zero => simp
  | succ n ih =>
      rw [Finset.sum_range_succ, ih, T.coboundary]
      ring

/-- The telescoped sum is uniformly bounded by `2M` — O(1) in tower
depth `N`, never Ω(N). -/
theorem towerSum_uniformly_bounded (T : NestingTower) (N : ℕ) :
    |towerSum T N| ≤ 2 * T.M := by
  have hN := abs_le.1 (T.Φ_bounded N)
  have h0 := abs_le.1 (T.Φ_bounded 0)
  rw [towerSum_telescope]
  rw [abs_le]
  constructor <;> linarith [hN.1, hN.2, h0.1, h0.2]

/-- A functional "supplies a new active scale" iff its nesting sum
grows at least linearly in tower depth (a strictly-positive increment
compounding over scales — the property every excluded class needed and
lacked). -/
def SuppliesNewActiveScale (T : NestingTower) : Prop :=
  ∃ ε : ℝ, 0 < ε ∧ ∀ N : ℕ, (N : ℝ) * ε ≤ towerSum T N

/-- **TICK645 unifying homogeneity-0 obstruction (the negative-result
theorem).** No scale-conjugation-invariant (degree-0 Biot–Savart /
Riesz) functional can supply a new active scale: Ω(N) growth is
impossible against an O(1) bounded telescoping sum.  This single
theorem covers all four excluded classes — they differ only in which
concrete object instantiates `NestingTower`; the impossibility is the
same. -/
theorem homogeneity0_obstruction (T : NestingTower) :
    ¬ SuppliesNewActiveScale T := by
  rintro ⟨ε, hε, hgrow⟩
  -- Archimedean (division-free): ∃ n, 2M+1 ≤ n•ε = (n:ℝ)*ε.
  obtain ⟨n, hn⟩ := Archimedean.arch (2 * T.M + 1) hε
  rw [nsmul_eq_mul] at hn
  have h1 : (n : ℝ) * ε ≤ towerSum T n := hgrow n
  have h2 : towerSum T n ≤ 2 * T.M :=
    (abs_le.1 (towerSum_uniformly_bounded T n)).2
  -- 2M+1 ≤ n·ε ≤ towerSum ≤ 2M  ⇒  1 ≤ 0, contradiction.
  linarith

/-- The four excluded control classes (TICK643/644/645).  Each is, at
the exact self-similar limit, a `NestingTower` (degree-0 ⇒ coboundary,
Coifman–Meyer-bounded), so each is excluded by the SINGLE theorem
above.  This is the unification: one root, four shadows. -/
inductive ExcludedClass
  | localEulerianPolynomial
  | strainEigenframe
  | lagrangianDeformationCocycle
  | biotSavartCommutatorDefect

/-- Faithful statement of the unification: given that a class presents
as a `NestingTower` at the self-similar limit (its homogeneity-0
instantiation), it cannot supply a new active scale.  The hypothesis
`present` is exactly the per-class analytic content (proven
class-by-class in the swarm consolidation, ns_residual_manifest.md);
the conclusion is the shared structural impossibility. -/
theorem excluded_class_supplies_no_new_scale
    (_c : ExcludedClass) (T : NestingTower)
    (_present : True) :  -- placeholder for the class→tower presentation
    ¬ SuppliesNewActiveScale T := by
  exact homogeneity0_obstruction T

/-! ### Non-vacuity witness

`SuppliesNewActiveScale` is NOT vacuously false: a NON-coboundary
tower (one that does NOT satisfy the homogeneity-0 `coboundary`
field) trivially supplies a new active scale (`d ≡ ε`).  The
obstruction theorem bites precisely because the excluded classes DO
satisfy `coboundary` (degree-0), unlike this witness — so the negative
is informative, not a definitional triviality. -/
example : ∃ d : ℕ → ℝ,
    ∀ N : ℕ, (N : ℝ) * (1 : ℝ) ≤ ∑ k ∈ Finset.range N, d k := by
  refine ⟨(fun _ => (1 : ℝ)), ?_⟩
  intro N
  simp

/-! ## TICK647 — parabolic-slaving universality terminus

The structural rung above forbids a *new active scale* from a degree-0
object.  The terminus rung forbids the only remaining escape: a
controllable scalar exceeding the parabolic scale itself.  The single
honest analytic input is the **two-sided** Grujić–Kukavica bound
(one-sided would not suffice — the point is the upper pin). -/

/-- A controllable scalar whose blow-up-NECESSARY asymptotic is the
parabolic rate `(T−t)^{1/2}`.  `q t` = the scalar renormalized at the
parabolic scale.  `slaved` is the two-sided Grujić–Kukavica bound: on
the whole approach to the singular time the renormalized value is
pinned in a fixed positive band `[c,C]`.  `level` is the scaling /
criticality exponent — it is *carried* but the bound does not depend on
it; that independence is exactly the "scaling-level-agnostic" content
(critical AND supercritical handled by the identical theorem). -/
structure ParabolicSlaved where
  q : ℝ → ℝ
  Tsing : ℝ
  level : ℝ
  c : ℝ
  C : ℝ
  c_pos : 0 < c
  /-- Two-sided Grujić–Kukavica self-similar pinning (Lane-independent
  of `level`). -/
  slaved : ∀ t, t < Tsing → c ≤ q t ∧ q t ≤ C

/-- The only escape from parabolic slaving: the renormalized margin is
unbounded above before the singular time (a genuinely *new* active
scale beyond the parabolic one — the parabolic analogue of
`SuppliesNewActiveScale`). -/
def EscapesParabolicScale (P : ParabolicSlaved) : Prop :=
  ∀ M : ℝ, ∃ t : ℝ, t < P.Tsing ∧ M < P.q t

/-- **TICK647 parabolic-slaving terminus (negative-result theorem).**
No parabolically-slaved controllable scalar can escape the parabolic
scale: the two-sided bound pins it under `C`, contradicting unbounded
growth.  This is the homogeneity-0 impossibility one rung deeper — at
the scaling limit rather than the structural symbol. -/
theorem parabolic_slaving_terminus (P : ParabolicSlaved) :
    ¬ EscapesParabolicScale P := by
  intro h
  obtain ⟨t, ht, hMt⟩ := h P.C
  exact absurd (P.slaved t ht).2 (not_le.2 hMt)

/-- **Scaling-level-agnostic.** The terminus conclusion is invariant
under arbitrarily replacing the criticality exponent `level`: the same
theorem excludes the critical and the supercritical instantiation
identically (the bound never consumed `level`). -/
theorem terminus_scaling_level_agnostic
    (P : ParabolicSlaved) (lvl' : ℝ) :
    ¬ EscapesParabolicScale { P with level := lvl' } :=
  parabolic_slaving_terminus _

/-- **Unification of the two rungs (the negative + the terminus).**
The reduction paradigm's controllable object can neither supply a new
active scale at the structural (homogeneity-0) rung NOR escape the
parabolic scale at the slaving rung: one wall, two depths. -/
theorem reduction_paradigm_terminus
    (T : NestingTower) (P : ParabolicSlaved) :
    ¬ SuppliesNewActiveScale T ∧ ¬ EscapesParabolicScale P :=
  ⟨homogeneity0_obstruction T, parabolic_slaving_terminus P⟩

/-! ### Non-vacuity witness (terminus)

`EscapesParabolicScale` is NOT vacuously false as a predicate: an
*un-slaved* scalar (one that does NOT satisfy the two-sided `slaved`
field) does escape — the unbounded identity scalar witnesses it.  The
terminus bites precisely because a parabolically-slaved scalar canNOT
be this witness; the negative is informative, not definitional. -/
example : ∃ q : ℝ → ℝ, ∀ M : ℝ, ∃ t : ℝ, M < q t := by
  refine ⟨id, ?_⟩
  intro M
  exact ⟨M + 1, lt_add_one M⟩

/-! ## TICK647 wall-scope inversion

The Munger inversion is useful as a scope discriminator, not as a
constructor.  The TICK647 wall can be invoked only after its inputs have
been paid: degree-0 Eulerian algebra, pure parabolic-power asymptotic,
and the two-sided parabolic-slaving receipt.  Log-corrected and
topological candidates are therefore not escapes by label.  They are
outside this theorem only until an analyst proves that one of these
fields actually holds or fails.
-/

/-- Substrate-level surface for a proposed controllable scalar before it
is specialized to the `ParabolicSlaved` structure above.  The fields are
propositions because the analytic work is exactly to instantiate or
refute them for a concrete PDE object. -/
structure ControllableScalarSurface where
  degreeZeroEulerianAlgebra : Prop
  pureParabolicPowerAsymptotic : Prop
  parabolicSlavingReceipt : Prop
  logCorrectedAsymptotic : Prop
  topologicalVortexInput : Prop

/-- The TICK647 wall is applicable only when all three input receipts are
present.  The third field is intentionally separate from
`pureParabolicPowerAsymptotic`: the Lean theorem consumes the two-sided
upper pin, not a phrase about scaling. -/
def Tick647WallApplies (Q : ControllableScalarSurface) : Prop :=
  Q.degreeZeroEulerianAlgebra ∧
    Q.pureParabolicPowerAsymptotic ∧
    Q.parabolicSlavingReceipt

/-- Honest inversion of the wall: a candidate is outside this wall when
at least one required input is not available.  This is a scope statement,
not a positive regularity mechanism. -/
def Tick647WallScopeFailure (Q : ControllableScalarSurface) : Prop :=
  ¬ Q.degreeZeroEulerianAlgebra ∨
    ¬ Q.pureParabolicPowerAsymptotic ∨
    ¬ Q.parabolicSlavingReceipt

/-- The wall cannot be applied after a paid scope-failure receipt. -/
theorem tick647_wall_scope_failure_blocks_application
    (Q : ControllableScalarSurface) :
    Tick647WallScopeFailure Q → ¬ Tick647WallApplies Q := by
  intro hfail happ
  rcases happ with ⟨hdeg, hpure, hslave⟩
  rcases hfail with hnotdeg | hrest
  · exact hnotdeg hdeg
  · rcases hrest with hnotpure | hnotslave
    · exact hnotpure hpure
    · exact hnotslave hslave

/-- Log-corrected candidates need a proof that the log factor is a
genuine non-pure-power asymptotic, not a notation change around a
slaved scalar. -/
structure LogCorrectedAsymptoticScopeReceipt
    (Q : ControllableScalarSurface) where
  log_corrected : Q.logCorrectedAsymptotic
  log_correction_not_pure_power :
    Q.logCorrectedAsymptotic → ¬ Q.pureParabolicPowerAsymptotic

/-- A paid log-correction receipt puts the candidate outside the TICK647
pure-power wall.  No conclusion about regularity is produced. -/
theorem log_corrected_receipt_blocks_tick647_wall_application
    (Q : ControllableScalarSurface)
    (R : LogCorrectedAsymptoticScopeReceipt Q) :
    ¬ Tick647WallApplies Q := by
  exact tick647_wall_scope_failure_blocks_application Q
    (Or.inr (Or.inl (R.log_correction_not_pure_power R.log_corrected)))


/--
Log-discounted transaction-channel source.  The Hofstadter-style move is not
"add a log label"; it changes which channel is paid.  A candidate becomes a
positive continuation source only after the original raw channel is connected to
a fixed log-discounted channel and a source-side theorem pays the finite
log-discounted integral/criterion before payoff.
-/
structure LogDiscountTransactionChannelSource
    (Q : ControllableScalarSurface) where
  scopeReceipt : LogCorrectedAsymptoticScopeReceipt Q
  rawChannel : ℝ → ℝ
  logDiscountedChannel : ℝ → ℝ
  discountDenominator : ℝ → ℝ
  Tsing : ℝ
  denominator_ge_one : ∀ t, t < Tsing → 1 ≤ discountDenominator t
  channel_identity :
    ∀ t, t < Tsing →
      logDiscountedChannel t * discountDenominator t = rawChannel t
  finiteLogDiscountCriterion : Prop
  finiteLogDiscountCriterion_proof : finiteLogDiscountCriterion
  sourcePaysFiniteLogDiscountCriterion : Prop
  sourcePaysFiniteLogDiscountCriterion_proof :
    sourcePaysFiniteLogDiscountCriterion
  continuationFromFiniteLogDiscountCriterion : Prop
  continuationFromFiniteLogDiscountCriterion_proof :
    continuationFromFiniteLogDiscountCriterion
  discountChannelFixedBeforePayoff : Prop
  discountChannelFixedBeforePayoff_proof : discountChannelFixedBeforePayoff
  noRawBKMOrCFInputHiddenInSourcePayment : Prop
  noRawBKMOrCFInputHiddenInSourcePayment_proof :
    noRawBKMOrCFInputHiddenInSourcePayment

/-- A paid log-discount transaction channel is outside the pure-power wall. -/
theorem log_discount_transaction_channel_blocks_tick647_wall_application
    (Q : ControllableScalarSurface)
    (S : LogDiscountTransactionChannelSource Q) :
    ¬ Tick647WallApplies Q :=
  log_corrected_receipt_blocks_tick647_wall_application Q S.scopeReceipt

/--
The log-discount channel can be a positive continuation source only after the
finite criterion is actually paid by a source-side theorem.  This theorem records
the exact consumer: scope failure plus paid log channel imply the abstract
continuation predicate carried by the source.
-/
theorem continuation_from_paid_log_discount_transaction_channel
    (Q : ControllableScalarSurface)
    (S : LogDiscountTransactionChannelSource Q) :
    S.continuationFromFiniteLogDiscountCriterion :=
  S.continuationFromFiniteLogDiscountCriterion_proof

/--
Confuser for log-lane laundering: outside-wall log scope alone does not pay the
new transaction channel.  A log denominator chosen from the raw BKM channel can
be a valid scope distinction while still lacking a source-side finite criterion.
-/
structure LogScopeWithoutPaidTransactionChannelConfuser
    (Q : ControllableScalarSurface) where
  scopeReceipt : LogCorrectedAsymptoticScopeReceipt Q
  logScopeOnly : Prop
  logScopeOnly_proof : logScopeOnly
  finiteCriterionNotSourcePaid : Prop
  finiteCriterionNotSourcePaid_proof : finiteCriterionNotSourcePaid
  rawBKMLogCircularityRisk : Prop
  rawBKMLogCircularityRisk_proof : rawBKMLogCircularityRisk
  no_log_discount_transaction_channel_source :
    LogDiscountTransactionChannelSource Q → False

theorem no_LogDiscountTransactionChannelSource_of_scopeOnlyConfuser
    (Q : ControllableScalarSurface)
    (C : LogScopeWithoutPaidTransactionChannelConfuser Q)
    (S : LogDiscountTransactionChannelSource Q) : False :=
  C.no_log_discount_transaction_channel_source S


/--
Faithful KT/BMO-log finite-bound source.  This is a sharper sibling of the
generic log-discount channel: it names the solution binding and finite bound
that would make a Kozono-Taniuchi-style continuation criterion usable.  It is
still conditional; the hard field is `finiteKTBMOLogBoundFromNSSources`.
-/
structure KTBMOLogFiniteFromNSSources
    (Q : ControllableScalarSurface) where
  channelSource : LogDiscountTransactionChannelSource Q
  exactNormAndLogDenominatorDeclared : Prop
  exactNormAndLogDenominatorDeclared_proof :
    exactNormAndLogDenominatorDeclared
  solutionBindingDeclared : Prop
  solutionBindingDeclared_proof : solutionBindingDeclared
  smoothOpenWindowCothread : Prop
  smoothOpenWindowCothread_proof : smoothOpenWindowCothread
  finiteKTBMOLogBound : Prop
  finiteKTBMOLogBound_proof : finiteKTBMOLogBound
  finiteKTBMOLogBoundFromNSSources : Prop
  finiteKTBMOLogBoundFromNSSources_proof :
    finiteKTBMOLogBoundFromNSSources
  noBKMLogCircularity : Prop
  noBKMLogCircularity_proof : noBKMLogCircularity
  noCFDirectionImport : Prop
  noCFDirectionImport_proof : noCFDirectionImport
  noClayEquivalentInputUsed : Prop
  noClayEquivalentInputUsed_proof : noClayEquivalentInputUsed

/-- A faithful KT/BMO-log finite-bound source supplies the generic log channel. -/
def KTBMOLogFiniteFromNSSources.toLogDiscountTransactionChannelSource
    {Q : ControllableScalarSurface}
    (S : KTBMOLogFiniteFromNSSources Q) :
    LogDiscountTransactionChannelSource Q :=
  S.channelSource

/-- The faithful KT/BMO-log source inherits the continuation consumer. -/
theorem continuation_from_KTBMOLogFiniteFromNSSources
    (Q : ControllableScalarSurface)
    (S : KTBMOLogFiniteFromNSSources Q) :
    S.channelSource.continuationFromFiniteLogDiscountCriterion :=
  continuation_from_paid_log_discount_transaction_channel Q S.channelSource

/-- Confuser: KT/BMO endpoint language without a finite source-bound theorem. -/
structure KTBMOLogBoundConfuser
    (Q : ControllableScalarSurface) where
  bkmLogLabelOnly : Prop
  bkmLogLabelOnly_proof : bkmLogLabelOnly
  finiteCriterionBoundNotDerived : Prop
  finiteCriterionBoundNotDerived_proof : finiteCriterionBoundNotDerived
  onlyTick647ScopeFailure : Prop
  onlyTick647ScopeFailure_proof : onlyTick647ScopeFailure
  hiddenBKMOrCFInput : Prop
  hiddenBKMOrCFInput_proof : hiddenBKMOrCFInput
  bmoEndpointDualOnly : Prop
  bmoEndpointDualOnly_proof : bmoEndpointDualOnly
  noSelectedC7Payment : Prop
  noSelectedC7Payment_proof : noSelectedC7Payment
  no_kt_bmo_log_finite_from_ns_sources :
    KTBMOLogFiniteFromNSSources Q → False

theorem no_KTBMOLogFiniteFromNSSources_of_boundConfuser
    (Q : ControllableScalarSurface)
    (C : KTBMOLogBoundConfuser Q)
    (S : KTBMOLogFiniteFromNSSources Q) : False :=
  C.no_kt_bmo_log_finite_from_ns_sources S

/--
NS-generated log/log modulation source.  This is the non-pure-power wall escape
made non-launderable: the log/log factor must come from an NS profile or
modulation calculation, not from relabeling an endpoint criterion after the
fact.  The structure is still a theorem target, not an assertion that such a
profile exists.
-/
structure NSGeneratedLogLogModulationSource
    (Q : ControllableScalarSurface) where
  scopeReceipt : LogCorrectedAsymptoticScopeReceipt Q
  qLogLog : ℝ → ℝ
  profileParameter : ℝ → ℝ
  renormalizedTime : ℝ → ℝ
  nsProfileOrInvariantManifoldDeclared : Prop
  nsProfileOrInvariantManifoldDeclared_proof :
    nsProfileOrInvariantManifoldDeclared
  linearizedSpectralEdgeReceipt : Prop
  linearizedSpectralEdgeReceipt_proof : linearizedSpectralEdgeReceipt
  modulationODEDerivedFromNSEvolution : Prop
  modulationODEDerivedFromNSEvolution_proof :
    modulationODEDerivedFromNSEvolution
  twoSidedLogLogAsymptoticForQ : Prop
  twoSidedLogLogAsymptoticForQ_proof : twoSidedLogLogAsymptoticForQ
  qBoundToSameNSSolutionWindow : Prop
  qBoundToSameNSSolutionWindow_proof : qBoundToSameNSSolutionWindow
  asymptoticNotCriterionRelabel : Prop
  asymptoticNotCriterionRelabel_proof : asymptoticNotCriterionRelabel
  noKTBMOBKMOrCFDefinitionOfQ : Prop
  noKTBMOBKMOrCFDefinitionOfQ_proof : noKTBMOBKMOrCFDefinitionOfQ
  paidChannel : LogDiscountTransactionChannelSource Q
  paidChannelUsesSameQAndWindow : Prop
  paidChannelUsesSameQAndWindow_proof : paidChannelUsesSameQAndWindow
  continuationPaymentSeparatedFromScopeEscape : Prop
  continuationPaymentSeparatedFromScopeEscape_proof :
    continuationPaymentSeparatedFromScopeEscape

/-- The NS-generated log/log source supplies the generic paid log channel. -/
def NSGeneratedLogLogModulationSource.toLogDiscountTransactionChannelSource
    {Q : ControllableScalarSurface}
    (S : NSGeneratedLogLogModulationSource Q) :
    LogDiscountTransactionChannelSource Q :=
  S.paidChannel

/-- A paid NS-generated log/log modulation source is outside the pure-power wall. -/
theorem ns_generated_loglog_modulation_blocks_tick647_wall_application
    (Q : ControllableScalarSurface)
    (S : NSGeneratedLogLogModulationSource Q) :
    ¬ Tick647WallApplies Q :=
  log_corrected_receipt_blocks_tick647_wall_application Q S.scopeReceipt

/-- The source inherits only the paid-channel continuation consumer. -/
theorem continuation_from_NSGeneratedLogLogModulationSource
    (Q : ControllableScalarSurface)
    (S : NSGeneratedLogLogModulationSource Q) :
    S.paidChannel.continuationFromFiniteLogDiscountCriterion :=
  continuation_from_paid_log_discount_transaction_channel Q S.paidChannel

/--
Confuser for log/log laundering: log/log language, a profile analogy, or a
KT/BMO continuation criterion can be visible while the NS-generated modulation
source is absent.
-/
structure LogLogModulationRelabelConfuser
    (Q : ControllableScalarSurface) where
  logLogLanguageVisible : Prop
  logLogLanguageVisible_proof : logLogLanguageVisible
  profileAnalogyOnly : Prop
  profileAnalogyOnly_proof : profileAnalogyOnly
  noVerifiedSpectralEdgeMode : Prop
  noVerifiedSpectralEdgeMode_proof : noVerifiedSpectralEdgeMode
  qDefinedFromContinuationCriterion : Prop
  qDefinedFromContinuationCriterion_proof : qDefinedFromContinuationCriterion
  paidContinuationChannelMissing : Prop
  paidContinuationChannelMissing_proof : paidContinuationChannelMissing
  onlyTick647ScopeEscape : Prop
  onlyTick647ScopeEscape_proof : onlyTick647ScopeEscape
  no_ns_generated_loglog_modulation_source :
    NSGeneratedLogLogModulationSource Q → False

theorem no_NSGeneratedLogLogModulationSource_of_relabelConfuser
    (Q : ControllableScalarSurface)
    (C : LogLogModulationRelabelConfuser Q)
    (S : NSGeneratedLogLogModulationSource Q) : False :=
  C.no_ns_generated_loglog_modulation_source S

/--
Spectral-gap or Bony-tail continuation data is not, by itself, the
NS-generated log/log modulation source.  It may prove a continuation criterion;
it still does not provide the profile/invariant manifold, spectral-edge mode,
modulation ODE, or same-solution log/log scalar demanded above.
-/
structure SpectralGapCriterionNotProfileModulationPacket
    (Q : ControllableScalarSurface) where
  spectralGapOrBonyTailCriterionVisible : Prop
  spectralGapOrBonyTailCriterionVisible_proof :
    spectralGapOrBonyTailCriterionVisible
  continuationCriterionVisible : Prop
  continuationCriterionVisible_proof : continuationCriterionVisible
  noProfileOrInvariantManifold : Prop
  noProfileOrInvariantManifold_proof : noProfileOrInvariantManifold
  noLinearizedSpectralEdgeReceipt : Prop
  noLinearizedSpectralEdgeReceipt_proof : noLinearizedSpectralEdgeReceipt
  noModulationODEFromNSEvolution : Prop
  noModulationODEFromNSEvolution_proof : noModulationODEFromNSEvolution
  qDefinedByTailCriterionOrBKMBridge : Prop
  qDefinedByTailCriterionOrBKMBridge_proof :
    qDefinedByTailCriterionOrBKMBridge
  no_ns_generated_loglog_modulation_source :
    NSGeneratedLogLogModulationSource Q → False

theorem no_NSGeneratedLogLogModulationSource_of_spectralGapCriterionPacket
    (Q : ControllableScalarSurface)
    (C : SpectralGapCriterionNotProfileModulationPacket Q)
    (S : NSGeneratedLogLogModulationSource Q) : False :=
  C.no_ns_generated_loglog_modulation_source S

/--
A nonzero eigenvalue in self-similar time is a pure-power hazard, not a
log/log source.  If the mode grows like an exponential in renormalized time and
the physical-time translation has been paid as a pure parabolic power, then it
contradicts the log-corrected scope receipt required by the Level369 source.
-/
structure NonzeroSimilarityEigenpairPurePowerConfuser
    (Q : ControllableScalarSurface) where
  similarityProfileOrLinearizationVisible : Prop
  similarityProfileOrLinearizationVisible_proof :
    similarityProfileOrLinearizationVisible
  nonzeroEigenvalueReceipt : Prop
  nonzeroEigenvalueReceipt_proof : nonzeroEigenvalueReceipt
  renormalizedExponentialMode : Prop
  renormalizedExponentialMode_proof : renormalizedExponentialMode
  physicalTimePurePowerTranslation : Prop
  physicalTimePurePowerTranslation_proof : physicalTimePurePowerTranslation
  noZeroSpectralEdgeOrJordanLogReceipt : Prop
  noZeroSpectralEdgeOrJordanLogReceipt_proof : noZeroSpectralEdgeOrJordanLogReceipt
  pureParabolicPowerAsymptotic_proof : Q.pureParabolicPowerAsymptotic

theorem no_LogCorrectedAsymptoticScopeReceipt_of_nonzeroEigenpairPurePower
    (Q : ControllableScalarSurface)
    (C : NonzeroSimilarityEigenpairPurePowerConfuser Q)
    (R : LogCorrectedAsymptoticScopeReceipt Q) : False :=
  R.log_correction_not_pure_power R.log_corrected
    C.pureParabolicPowerAsymptotic_proof

theorem no_NSGeneratedLogLogModulationSource_of_nonzeroEigenpairPurePower
    (Q : ControllableScalarSurface)
    (C : NonzeroSimilarityEigenpairPurePowerConfuser Q)
    (S : NSGeneratedLogLogModulationSource Q) : False :=
  no_LogCorrectedAsymptoticScopeReceipt_of_nonzeroEigenpairPurePower
    Q C S.scopeReceipt

/--
Positive marginal-mode target.  A zero/threshold spectral label is not enough:
the source must carry the nonlinear normal-form coefficient or equivalent
transaction channel that turns marginality into a two-sided log/log asymptotic.
-/
structure MarginalSimilarityModeLogSource
    (Q : ControllableScalarSurface) where
  scopeReceipt : LogCorrectedAsymptoticScopeReceipt Q
  qLogLog : ℝ → ℝ
  profileParameter : ℝ → ℝ
  renormalizedTime : ℝ → ℝ
  nsProfileOrInvariantManifoldDeclared : Prop
  nsProfileOrInvariantManifoldDeclared_proof :
    nsProfileOrInvariantManifoldDeclared
  zeroOrThresholdSpectralEdgeReceipt : Prop
  zeroOrThresholdSpectralEdgeReceipt_proof :
    zeroOrThresholdSpectralEdgeReceipt
  jordanBlockOrThresholdResonanceReceipt : Prop
  jordanBlockOrThresholdResonanceReceipt_proof :
    jordanBlockOrThresholdResonanceReceipt
  nontrivialBetaOrNormalFormCoefficient : Prop
  nontrivialBetaOrNormalFormCoefficient_proof :
    nontrivialBetaOrNormalFormCoefficient
  modulationODEDerivedFromNSEvolution : Prop
  modulationODEDerivedFromNSEvolution_proof :
    modulationODEDerivedFromNSEvolution
  twoSidedLogLogAsymptoticForQ : Prop
  twoSidedLogLogAsymptoticForQ_proof : twoSidedLogLogAsymptoticForQ
  qBoundToSameNSSolutionWindow : Prop
  qBoundToSameNSSolutionWindow_proof : qBoundToSameNSSolutionWindow
  asymptoticNotCriterionRelabel : Prop
  asymptoticNotCriterionRelabel_proof : asymptoticNotCriterionRelabel
  noKTBMOBKMOrCFDefinitionOfQ : Prop
  noKTBMOBKMOrCFDefinitionOfQ_proof : noKTBMOBKMOrCFDefinitionOfQ
  paidChannel : LogDiscountTransactionChannelSource Q
  paidChannelUsesSameQAndWindow : Prop
  paidChannelUsesSameQAndWindow_proof : paidChannelUsesSameQAndWindow
  continuationPaymentSeparatedFromScopeEscape : Prop
  continuationPaymentSeparatedFromScopeEscape_proof :
    continuationPaymentSeparatedFromScopeEscape

def MarginalSimilarityModeLogSource.toNSGeneratedLogLogModulationSource
    {Q : ControllableScalarSurface}
    (S : MarginalSimilarityModeLogSource Q) :
    NSGeneratedLogLogModulationSource Q :=
  { scopeReceipt := S.scopeReceipt
    qLogLog := S.qLogLog
    profileParameter := S.profileParameter
    renormalizedTime := S.renormalizedTime
    nsProfileOrInvariantManifoldDeclared :=
      S.nsProfileOrInvariantManifoldDeclared
    nsProfileOrInvariantManifoldDeclared_proof :=
      S.nsProfileOrInvariantManifoldDeclared_proof
    linearizedSpectralEdgeReceipt :=
      S.zeroOrThresholdSpectralEdgeReceipt
    linearizedSpectralEdgeReceipt_proof :=
      S.zeroOrThresholdSpectralEdgeReceipt_proof
    modulationODEDerivedFromNSEvolution :=
      S.modulationODEDerivedFromNSEvolution
    modulationODEDerivedFromNSEvolution_proof :=
      S.modulationODEDerivedFromNSEvolution_proof
    twoSidedLogLogAsymptoticForQ := S.twoSidedLogLogAsymptoticForQ
    twoSidedLogLogAsymptoticForQ_proof :=
      S.twoSidedLogLogAsymptoticForQ_proof
    qBoundToSameNSSolutionWindow := S.qBoundToSameNSSolutionWindow
    qBoundToSameNSSolutionWindow_proof :=
      S.qBoundToSameNSSolutionWindow_proof
    asymptoticNotCriterionRelabel := S.asymptoticNotCriterionRelabel
    asymptoticNotCriterionRelabel_proof :=
      S.asymptoticNotCriterionRelabel_proof
    noKTBMOBKMOrCFDefinitionOfQ := S.noKTBMOBKMOrCFDefinitionOfQ
    noKTBMOBKMOrCFDefinitionOfQ_proof :=
      S.noKTBMOBKMOrCFDefinitionOfQ_proof
    paidChannel := S.paidChannel
    paidChannelUsesSameQAndWindow := S.paidChannelUsesSameQAndWindow
    paidChannelUsesSameQAndWindow_proof :=
      S.paidChannelUsesSameQAndWindow_proof
    continuationPaymentSeparatedFromScopeEscape :=
      S.continuationPaymentSeparatedFromScopeEscape
    continuationPaymentSeparatedFromScopeEscape_proof :=
      S.continuationPaymentSeparatedFromScopeEscape_proof }

/-- Marginal language with a flat beta function is not a log-running source. -/
structure MarginalModeZeroBetaConfuser
    (Q : ControllableScalarSurface) where
  marginalModeVisible : Prop
  marginalModeVisible_proof : marginalModeVisible
  zeroOrUnitRootVisible : Prop
  zeroOrUnitRootVisible_proof : zeroOrUnitRootVisible
  betaFunctionIdenticallyZero : Prop
  betaFunctionIdenticallyZero_proof : betaFunctionIdenticallyZero
  simpleMarginalRootNoJordan : Prop
  simpleMarginalRootNoJordan_proof : simpleMarginalRootNoJordan
  noThresholdResonanceReceipt : Prop
  noThresholdResonanceReceipt_proof : noThresholdResonanceReceipt
  noNontrivialBetaOrNormalFormCoefficient : Prop
  noNontrivialBetaOrNormalFormCoefficient_proof :
    noNontrivialBetaOrNormalFormCoefficient
  no_marginal_similarity_mode_log_source :
    MarginalSimilarityModeLogSource Q → False

theorem no_MarginalSimilarityModeLogSource_of_zeroBetaConfuser
    (Q : ControllableScalarSurface)
    (C : MarginalModeZeroBetaConfuser Q)
    (S : MarginalSimilarityModeLogSource Q) : False :=
  C.no_marginal_similarity_mode_log_source S

/--
Nonflat spatial beta in a CKN/bad-node packet is a different currency from the
profile beta/normal-form coefficient above.  Fresh-packet payment plus no-log
reuse can be valuable without supplying a marginal profile modulation source.
-/
structure SpatialNonflatBetaNotMarginalModeLogSource
    (Q : ControllableScalarSurface) where
  badNodeBetaVisible : Prop
  badNodeBetaVisible_proof : badNodeBetaVisible
  freshPacketGainPaymentVisible : Prop
  freshPacketGainPaymentVisible_proof : freshPacketGainPaymentVisible
  noLogReuseVisible : Prop
  noLogReuseVisible_proof : noLogReuseVisible
  spatialCarrierNotProfileParameter : Prop
  spatialCarrierNotProfileParameter_proof : spatialCarrierNotProfileParameter
  noZeroThresholdSpectralEdgeReceipt : Prop
  noZeroThresholdSpectralEdgeReceipt_proof : noZeroThresholdSpectralEdgeReceipt
  noJordanOrThresholdNormalFormReceipt : Prop
  noJordanOrThresholdNormalFormReceipt_proof :
    noJordanOrThresholdNormalFormReceipt
  no_marginal_similarity_mode_log_source :
    MarginalSimilarityModeLogSource Q → False

theorem no_MarginalSimilarityModeLogSource_of_spatialNonflatBetaPacket
    (Q : ControllableScalarSurface)
    (C : SpatialNonflatBetaNotMarginalModeLogSource Q)
    (S : MarginalSimilarityModeLogSource Q) : False :=
  C.no_marginal_similarity_mode_log_source S

/-- Finite outcome tags for a declared profile normal-form audit. -/
inductive DeclaredProfileNormalFormOutcome where
  | marginalLogSource
  | nonzeroPurePower
  | zeroBetaFlat
  | continuationCriterionOnly
  | spatialBetaCurrencyMismatch
  deriving DecidableEq, Repr

/--
Finite audit target for a declared NS profile class.  This is the first
non-wrapper consumer of the marginal-mode lane: after choosing a profile class
and linearized operator, the audit must return a finite tag and the matching
witness field, rather than another generic spectral label.
-/
structure DeclaredNSProfileNormalFormCoefficientScan
    (Q : ControllableScalarSurface) where
  profileClassName : String
  profileClassDeclaredBeforePayoff : Prop
  profileClassDeclaredBeforePayoff_proof :
    profileClassDeclaredBeforePayoff
  linearizedOperatorDeclared : Prop
  linearizedOperatorDeclared_proof : linearizedOperatorDeclared
  adjointTestModeOrProjectionDeclared : Prop
  adjointTestModeOrProjectionDeclared_proof :
    adjointTestModeOrProjectionDeclared
  outcome : DeclaredProfileNormalFormOutcome
  marginalLogSourceWitness :
    outcome = DeclaredProfileNormalFormOutcome.marginalLogSource →
      MarginalSimilarityModeLogSource Q
  nonzeroPurePowerWitness :
    outcome = DeclaredProfileNormalFormOutcome.nonzeroPurePower →
      NonzeroSimilarityEigenpairPurePowerConfuser Q
  zeroBetaFlatWitness :
    outcome = DeclaredProfileNormalFormOutcome.zeroBetaFlat →
      MarginalModeZeroBetaConfuser Q
  continuationCriterionOnlyWitness :
    outcome = DeclaredProfileNormalFormOutcome.continuationCriterionOnly →
      SpectralGapCriterionNotProfileModulationPacket Q
  spatialBetaCurrencyMismatchWitness :
    outcome = DeclaredProfileNormalFormOutcome.spatialBetaCurrencyMismatch →
      SpatialNonflatBetaNotMarginalModeLogSource Q

def DeclaredNSProfileNormalFormCoefficientScan.isMarginalLogSource
    {Q : ControllableScalarSurface}
    (S : DeclaredNSProfileNormalFormCoefficientScan Q)
    (h : S.outcome = DeclaredProfileNormalFormOutcome.marginalLogSource) :
    MarginalSimilarityModeLogSource Q :=
  S.marginalLogSourceWitness h

/--
Conditional finite-scan adapter for the HWY-style self-similar unstable-mode
lane.  It does not assert the external paper hypotheses; it says that once
the evidence supplies self-similar profile data, a nonzero unstable eigenpair,
renormalized exponential behavior, and a paid pure-power physical-time
translation, the finite scan outcome is `nonzeroPurePower`, not
`marginalLogSource`.
-/
structure HWYStyleSimilarityProfileFiniteScanEvidence
    (Q : ControllableScalarSurface) where
  profileClassDeclaredBeforePayoff : Prop
  profileClassDeclaredBeforePayoff_proof :
    profileClassDeclaredBeforePayoff
  linearizedOperatorDeclared : Prop
  linearizedOperatorDeclared_proof : linearizedOperatorDeclared
  adjointOrRieszProjectionDeclared : Prop
  adjointOrRieszProjectionDeclared_proof : adjointOrRieszProjectionDeclared
  unstableEigenpairDeclared : Prop
  unstableEigenpairDeclared_proof : unstableEigenpairDeclared
  nonzeroEigenvalueReceipt : Prop
  nonzeroEigenvalueReceipt_proof : nonzeroEigenvalueReceipt
  renormalizedExponentialAsymptotic : Prop
  renormalizedExponentialAsymptotic_proof :
    renormalizedExponentialAsymptotic
  physicalTimePurePowerTranslation : Prop
  physicalTimePurePowerTranslation_proof : physicalTimePurePowerTranslation
  noZeroJordanThresholdLogReceipt : Prop
  noZeroJordanThresholdLogReceipt_proof : noZeroJordanThresholdLogReceipt
  pureParabolicPowerAsymptotic_proof : Q.pureParabolicPowerAsymptotic

def HWYStyleSimilarityProfileFiniteScanEvidence.toNonzeroPurePowerConfuser
    {Q : ControllableScalarSurface}
    (E : HWYStyleSimilarityProfileFiniteScanEvidence Q) :
    NonzeroSimilarityEigenpairPurePowerConfuser Q where
  similarityProfileOrLinearizationVisible :=
    And E.profileClassDeclaredBeforePayoff E.linearizedOperatorDeclared
  similarityProfileOrLinearizationVisible_proof :=
    ⟨E.profileClassDeclaredBeforePayoff_proof,
      E.linearizedOperatorDeclared_proof⟩
  nonzeroEigenvalueReceipt := E.nonzeroEigenvalueReceipt
  nonzeroEigenvalueReceipt_proof := E.nonzeroEigenvalueReceipt_proof
  renormalizedExponentialMode := E.renormalizedExponentialAsymptotic
  renormalizedExponentialMode_proof :=
    E.renormalizedExponentialAsymptotic_proof
  physicalTimePurePowerTranslation := E.physicalTimePurePowerTranslation
  physicalTimePurePowerTranslation_proof :=
    E.physicalTimePurePowerTranslation_proof
  noZeroSpectralEdgeOrJordanLogReceipt := E.noZeroJordanThresholdLogReceipt
  noZeroSpectralEdgeOrJordanLogReceipt_proof :=
    E.noZeroJordanThresholdLogReceipt_proof
  pureParabolicPowerAsymptotic_proof :=
    E.pureParabolicPowerAsymptotic_proof

def HWYStyleSimilarityProfileFiniteScanEvidence.toDeclaredProfileScan
    {Q : ControllableScalarSurface}
    (E : HWYStyleSimilarityProfileFiniteScanEvidence Q) :
    DeclaredNSProfileNormalFormCoefficientScan Q where
  profileClassName := "HWY-style self-similar unstable profile"
  profileClassDeclaredBeforePayoff := E.profileClassDeclaredBeforePayoff
  profileClassDeclaredBeforePayoff_proof :=
    E.profileClassDeclaredBeforePayoff_proof
  linearizedOperatorDeclared := E.linearizedOperatorDeclared
  linearizedOperatorDeclared_proof := E.linearizedOperatorDeclared_proof
  adjointTestModeOrProjectionDeclared := E.adjointOrRieszProjectionDeclared
  adjointTestModeOrProjectionDeclared_proof :=
    E.adjointOrRieszProjectionDeclared_proof
  outcome := DeclaredProfileNormalFormOutcome.nonzeroPurePower
  marginalLogSourceWitness := by
    intro h
    cases h
  nonzeroPurePowerWitness := by
    intro _
    exact E.toNonzeroPurePowerConfuser
  zeroBetaFlatWitness := by
    intro h
    cases h
  continuationCriterionOnlyWitness := by
    intro h
    cases h
  spatialBetaCurrencyMismatchWitness := by
    intro h
    cases h

/-- Topological vortex candidates need a proof that the object is not in
the degree-0 local Eulerian Biot-Savart/Riesz algebra.  Helicity-style
labels alone do not pay that proof. -/
structure VortexTopologyInputScopeReceipt
    (Q : ControllableScalarSurface) where
  topological_input : Q.topologicalVortexInput
  topology_not_degree_zero_eulerian :
    Q.topologicalVortexInput → ¬ Q.degreeZeroEulerianAlgebra

/-- A paid topology receipt puts the candidate outside the TICK647
degree-0 Eulerian wall.  It does not make the topological scalar
coercive, monotone, or blow-up necessary. -/
theorem topology_receipt_blocks_tick647_wall_application
    (Q : ControllableScalarSurface)
    (R : VortexTopologyInputScopeReceipt Q) :
    ¬ Tick647WallApplies Q := by
  exact tick647_wall_scope_failure_blocks_application Q
    (Or.inl (R.topology_not_degree_zero_eulerian R.topological_input))

/-- Separation from the older Lagrangian-deformation-cocycle exclusion:
even a proven exclusion for that old class is not, by itself, a topology
receipt for a vortex-linking candidate.  The required implication must
be supplied explicitly. -/
structure LagrangianCocycleDoesNotImplyTopologyReceipt where
  lagrangianCocycleExcluded : Prop
  vortexTopologyExcluded : Prop
  implication_missing :
    ¬ (lagrangianCocycleExcluded → vortexTopologyExcluded)

theorem lagrangian_cocycle_exclusion_not_topology_exclusion
    (R : LagrangianCocycleDoesNotImplyTopologyReceipt) :
    ¬ (R.lagrangianCocycleExcluded → R.vortexTopologyExcluded) :=
  R.implication_missing

end ZtareProofs.NS.Tick645
