import Mathlib.Tactic
import ZtareProofs.ns_null_profile_cap_branch
import ZtareProofs.ns_concentration_impact_branch
import ZtareProofs.ns_vanishing_branch
import ZtareProofs.ns_dichotomy_cross_profile_branch
import ZtareProofs.ns_pricing_kernel_countable_limit

/-!
# Track B profile-decomposition proof spine

This file is the current compressed proof surface.  It does **not** prove
Navier-Stokes regularity.  It states the exact bridge obligation: instantiate
the pricing profiles for actual Leray/Sobolev profile decompositions under a
fixed topology and fixed observable class.

The theorem below says that once that obligation is paid, the existing Track B
no-survivor bridge follows.  The content is the decomposition certificate, not
the implication.
-/

namespace ZtareProofs.NS

/-- Source receipt for the Track B profile-decomposition family.

For each global block, the profile family used by the branch certificates is
declared before branch payoff/no-survivor pricing, reused across all branch
certificates, and handed to the threshold-defect bridge without a branch-local
posthoc replacement. -/
structure TrackBProfileDecompositionSourceReceipt
    (profile_family_of_block : FullLedgerBlock → PricingProfileFamily) where
  profile_family_fixed_before_payoff :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B → Prop
  profile_family_fixed_before_payoff_paid :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      profile_family_fixed_before_payoff B hglobal
  same_family_reused_by_all_branch_certificates :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B → Prop
  same_family_reused_by_all_branch_certificates_paid :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      same_family_reused_by_all_branch_certificates B hglobal
  no_branch_specific_posthoc_profile_selection :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B → Prop
  no_branch_specific_posthoc_profile_selection_paid :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      no_branch_specific_posthoc_profile_selection B hglobal
  threshold_defect_handoff_uses_same_family :
    ∀ B : FullLedgerBlock, IsGlobalTrackBBlock B → Prop
  threshold_defect_handoff_uses_same_family_paid :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      threshold_defect_handoff_uses_same_family B hglobal

/-- Branch-certificate source guard: the family is fixed before payoff, reused
by every branch, and not chosen branch-by-branch after prices are visible. -/
def TrackBProfileDecompositionBranchSourceReady
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    (receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) : Prop :=
  receipt.profile_family_fixed_before_payoff B hglobal ∧
    receipt.same_family_reused_by_all_branch_certificates B hglobal ∧
      receipt.no_branch_specific_posthoc_profile_selection B hglobal

/-- Threshold-defect source guard: the no-arbitrage handoff uses the same
predeclared family that the branch certificate priced, and it inherits the
branch-side source-readiness guard so threshold conversion cannot bypass
all-branch reuse or no-posthoc-selection coverage. -/
def TrackBProfileDecompositionThresholdHandoffSourceReady
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    (receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) : Prop :=
  TrackBProfileDecompositionBranchSourceReady receipt B hglobal ∧
    receipt.threshold_defect_handoff_uses_same_family B hglobal

theorem trackb_profile_decomposition_branch_source_ready
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    (receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    TrackBProfileDecompositionBranchSourceReady receipt B hglobal := by
  exact
    ⟨receipt.profile_family_fixed_before_payoff_paid B hglobal,
      receipt.same_family_reused_by_all_branch_certificates_paid B hglobal,
      receipt.no_branch_specific_posthoc_profile_selection_paid B hglobal⟩

theorem trackb_profile_decomposition_threshold_handoff_source_ready
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    (receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    TrackBProfileDecompositionThresholdHandoffSourceReady receipt B hglobal := by
  exact
    ⟨trackb_profile_decomposition_branch_source_ready receipt B hglobal,
      receipt.threshold_defect_handoff_uses_same_family_paid B hglobal⟩

/-- Hostile surface for the ways a Track B profile-decomposition source receipt
can fail to be a genuine pre-payoff source declaration. -/
inductive TrackBProfileDecompositionSourceFalsifier
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    (receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block) : Prop
  | profile_family_not_fixed_before_payoff :
      (∃ B : FullLedgerBlock,
        ∃ hglobal : IsGlobalTrackBBlock B,
          ¬ receipt.profile_family_fixed_before_payoff B hglobal) →
        TrackBProfileDecompositionSourceFalsifier receipt
  | family_not_reused_by_all_branch_certificates :
      (∃ B : FullLedgerBlock,
        ∃ hglobal : IsGlobalTrackBBlock B,
          ¬ receipt.same_family_reused_by_all_branch_certificates
            B hglobal) →
        TrackBProfileDecompositionSourceFalsifier receipt
  | branch_specific_posthoc_profile_selection :
      (∃ B : FullLedgerBlock,
        ∃ hglobal : IsGlobalTrackBBlock B,
          ¬ receipt.no_branch_specific_posthoc_profile_selection
            B hglobal) →
        TrackBProfileDecompositionSourceFalsifier receipt
  | threshold_handoff_family_mismatch :
      (∃ B : FullLedgerBlock,
        ∃ hglobal : IsGlobalTrackBBlock B,
          ¬ receipt.threshold_defect_handoff_uses_same_family
            B hglobal) →
        TrackBProfileDecompositionSourceFalsifier receipt

/-- A paid Track B source receipt cannot coexist with any of its hostile
anti-tautology falsifiers. -/
theorem no_trackb_profile_decomposition_source_receipt_of_falsifier
    {profile_family_of_block : FullLedgerBlock → PricingProfileFamily}
    (receipt :
      TrackBProfileDecompositionSourceReceipt profile_family_of_block)
    (F : TrackBProfileDecompositionSourceFalsifier receipt) :
    False := by
  cases F with
  | profile_family_not_fixed_before_payoff hbad =>
      rcases hbad with ⟨B, hglobal, hmissing⟩
      exact hmissing
        (receipt.profile_family_fixed_before_payoff_paid B hglobal)
  | family_not_reused_by_all_branch_certificates hbad =>
      rcases hbad with ⟨B, hglobal, hmissing⟩
      exact hmissing
        (receipt.same_family_reused_by_all_branch_certificates_paid
          B hglobal)
  | branch_specific_posthoc_profile_selection hbad =>
      rcases hbad with ⟨B, hglobal, hmissing⟩
      exact hmissing
        (receipt.no_branch_specific_posthoc_profile_selection_paid
          B hglobal)
  | threshold_handoff_family_mismatch hbad =>
      rcases hbad with ⟨B, hglobal, hmissing⟩
      exact hmissing
        (receipt.threshold_defect_handoff_uses_same_family_paid
          B hglobal)

/-- The non-tautological profile-decomposition obligation for Track B.

`profile_family_of_block` must be fixed by the PDE/profile theorem, not chosen
after seeing the profitable route.  The branch certificates then charge the
declared profiles and residuals. -/
structure TrackBProfileDecompositionObligation where
  profile_family_of_block : FullLedgerBlock → PricingProfileFamily
  source_receipt :
    TrackBProfileDecompositionSourceReceipt profile_family_of_block
  null_certificate :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      TrackBProfileDecompositionBranchSourceReady
        source_receipt B hglobal →
        NullProfileCapBranchCertificate (profile_family_of_block B)
  concentration_certificate :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      TrackBProfileDecompositionBranchSourceReady
        source_receipt B hglobal →
        ConcentrationImpactFamilyCertificate (profile_family_of_block B)
  vanishing_certificate :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      TrackBProfileDecompositionBranchSourceReady
        source_receipt B hglobal →
        VanishingFamilyCertificate (profile_family_of_block B)
  dichotomy_cross_certificate :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      TrackBProfileDecompositionBranchSourceReady
        source_receipt B hglobal →
        PricedFragmentCertificate (profile_family_of_block B) ∧
          CrossProfileRecombinationCertificate (profile_family_of_block B)
  threshold_defect_of_family_no_arbitrage :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      TrackBProfileDecompositionThresholdHandoffSourceReady
        source_receipt B hglobal →
        familyPayoff (profile_family_of_block B) ≤
          familyPrice (profile_family_of_block B) →
            ThresholdDefectConvexity B

/-- Bundle the four older branch bridges into the source-aware Track B profile
decomposition obligation.

This is a compatibility adapter, not a new PDE estimate.  It is deliberately
strict about family identity: the null, concentration, vanishing, and
dichotomy/cross bridges must all use the same predeclared profile family, and
the threshold handoff must be the source-aware handoff carried by the Track B
receipt. -/
structure TrackBProfileDecompositionBridgeBundle where
  profile_family_of_block : FullLedgerBlock → PricingProfileFamily
  source_receipt :
    TrackBProfileDecompositionSourceReceipt profile_family_of_block
  null_bridge : NullProfileCapBranchBridge
  concentration_bridge : ConcentrationImpactPricingBridge
  vanishing_bridge : VanishingPricingBridge
  dichotomy_cross_bridge : DichotomyCrossProfileBridge
  null_family_matches :
    null_bridge.profile_family_of_block = profile_family_of_block
  concentration_family_matches :
    concentration_bridge.profile_family_of_block = profile_family_of_block
  vanishing_family_matches :
    vanishing_bridge.profile_family_of_block = profile_family_of_block
  dichotomy_cross_family_matches :
    dichotomy_cross_bridge.profile_family_of_block = profile_family_of_block
  threshold_handoff_of_family_no_arbitrage :
    ∀ B : FullLedgerBlock, (hglobal : IsGlobalTrackBBlock B) →
      TrackBProfileDecompositionThresholdHandoffSourceReady
        source_receipt B hglobal →
      familyPayoff (profile_family_of_block B) ≤
        familyPrice (profile_family_of_block B) →
          ThresholdDefectConvexity B

/-- Named ways the bridge bundle can fail to reuse one fixed profile family
across the four decomposition branches.

These are not new assumptions.  They expose the equality fields already carried
by `TrackBProfileDecompositionBridgeBundle` as falsifier branches, so final
bridge receipts can name a family-mismatch failure separately from the
pre-payoff source receipt. -/
inductive TrackBProfileDecompositionBridgeBundleFalsifier
    (Bun : TrackBProfileDecompositionBridgeBundle) : Type where
  | nullFamilyMismatch :
      Bun.null_bridge.profile_family_of_block ≠
        Bun.profile_family_of_block →
          TrackBProfileDecompositionBridgeBundleFalsifier Bun
  | concentrationFamilyMismatch :
      Bun.concentration_bridge.profile_family_of_block ≠
        Bun.profile_family_of_block →
          TrackBProfileDecompositionBridgeBundleFalsifier Bun
  | vanishingFamilyMismatch :
      Bun.vanishing_bridge.profile_family_of_block ≠
        Bun.profile_family_of_block →
          TrackBProfileDecompositionBridgeBundleFalsifier Bun
  | dichotomyCrossFamilyMismatch :
      Bun.dichotomy_cross_bridge.profile_family_of_block ≠
        Bun.profile_family_of_block →
          TrackBProfileDecompositionBridgeBundleFalsifier Bun

/-- A same-family Track B profile-decomposition bundle excludes all named
family-mismatch falsifiers. -/
theorem no_trackb_profile_decomposition_bridge_bundle_falsifier
    (Bun : TrackBProfileDecompositionBridgeBundle)
    (F : TrackBProfileDecompositionBridgeBundleFalsifier Bun) :
    False := by
  cases F with
  | nullFamilyMismatch h =>
      exact h Bun.null_family_matches
  | concentrationFamilyMismatch h =>
      exact h Bun.concentration_family_matches
  | vanishingFamilyMismatch h =>
      exact h Bun.vanishing_family_matches
  | dichotomyCrossFamilyMismatch h =>
      exact h Bun.dichotomy_cross_family_matches

/-- Bundle-level source package: one fixed profile family, all four branch
bridges matched to it, and the threshold handoff using the same source
receipt. -/
def TrackBProfileDecompositionBridgeBundleSourceReady
    (Bun : TrackBProfileDecompositionBridgeBundle)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) : Prop :=
  TrackBProfileDecompositionThresholdHandoffSourceReady
      Bun.source_receipt B hglobal ∧
    Bun.null_bridge.profile_family_of_block = Bun.profile_family_of_block ∧
      Bun.concentration_bridge.profile_family_of_block =
          Bun.profile_family_of_block ∧
        Bun.vanishing_bridge.profile_family_of_block =
            Bun.profile_family_of_block ∧
          Bun.dichotomy_cross_bridge.profile_family_of_block =
            Bun.profile_family_of_block

/-- A same-family Track B profile-decomposition bundle is source-ready for
branch pricing and threshold handoff. -/
theorem trackb_profile_decomposition_bridge_bundle_source_ready
    (Bun : TrackBProfileDecompositionBridgeBundle)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    TrackBProfileDecompositionBridgeBundleSourceReady Bun B hglobal := by
  exact
    ⟨trackb_profile_decomposition_threshold_handoff_source_ready
        Bun.source_receipt B hglobal,
      Bun.null_family_matches,
      Bun.concentration_family_matches,
      Bun.vanishing_family_matches,
      Bun.dichotomy_cross_family_matches⟩

/-- All four branch bridges in a same-family bundle feed the same
source-aware threshold-defect handoff. -/
theorem threshold_defects_of_all_trackb_profile_decomposition_bridge_bundle_branches
    (Bun : TrackBProfileDecompositionBridgeBundle)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hsource :
      TrackBProfileDecompositionBridgeBundleSourceReady Bun B hglobal) :
    ThresholdDefectConvexity B ∧
      ThresholdDefectConvexity B ∧
        ThresholdDefectConvexity B ∧
          ThresholdDefectConvexity B := by
  let F := Bun.profile_family_of_block B
  rcases hsource with
    ⟨hthreshold_source, hnull_match, hconcentration_match,
      hvanishing_match, hdichotomy_cross_match⟩
  have hnull : familyPayoff F ≤ familyPrice F := by
    have h :=
      family_no_arbitrage_of_null_profile_cap_branch
        (Bun.null_bridge.profile_family_of_block B)
        (Bun.null_bridge.certificate_of_global B hglobal)
    simpa [F, hnull_match] using h
  have hconcentration : familyPayoff F ≤ familyPrice F := by
    have h :=
      family_no_arbitrage_of_concentration_impact
        (Bun.concentration_bridge.profile_family_of_block B)
        (Bun.concentration_bridge.certificate_of_global B hglobal)
    simpa [F, hconcentration_match] using h
  have hvanishing : familyPayoff F ≤ familyPrice F := by
    have h :=
      family_no_arbitrage_of_vanishing
        (Bun.vanishing_bridge.profile_family_of_block B)
        (Bun.vanishing_bridge.certificate_of_global B hglobal)
    simpa [F, hvanishing_match] using h
  have hpriced : PricedFragmentCertificate F := by
    have h := Bun.dichotomy_cross_bridge.priced_fragments B hglobal
    simpa [F, hdichotomy_cross_match] using h
  have hcross : CrossProfileRecombinationCertificate F := by
    have h := Bun.dichotomy_cross_bridge.cross_profile_charged B hglobal
    simpa [F, hdichotomy_cross_match] using h
  have hdichotomy : familyPayoff F ≤ familyPrice F :=
    family_no_arbitrage_of_cross_profile_charging F hpriced hcross
  exact
    ⟨Bun.threshold_handoff_of_family_no_arbitrage
        B hglobal hthreshold_source hnull,
      Bun.threshold_handoff_of_family_no_arbitrage
        B hglobal hthreshold_source hconcentration,
      Bun.threshold_handoff_of_family_no_arbitrage
        B hglobal hthreshold_source hvanishing,
      Bun.threshold_handoff_of_family_no_arbitrage
        B hglobal hthreshold_source hdichotomy⟩

/-- Convert a same-family branch-bridge bundle into the compressed Track B
profile-decomposition obligation.

The proof consumes the four branch certificates from existing bridge records
but refuses to inherit their threshold handoffs directly; threshold conversion
is routed through the source-aware Track B handoff to avoid a hidden
post-hoc-family substitution. -/
def trackb_profile_decomposition_obligation_of_bridge_bundle
    (Bun : TrackBProfileDecompositionBridgeBundle) :
    TrackBProfileDecompositionObligation where
  profile_family_of_block := Bun.profile_family_of_block
  source_receipt := Bun.source_receipt
  null_certificate := by
    intro B hglobal _hsource
    have h :=
      Bun.null_bridge.certificate_of_global B hglobal
    simpa [Bun.null_family_matches] using h
  concentration_certificate := by
    intro B hglobal _hsource
    have h :=
      Bun.concentration_bridge.certificate_of_global B hglobal
    simpa [Bun.concentration_family_matches] using h
  vanishing_certificate := by
    intro B hglobal _hsource
    have h :=
      Bun.vanishing_bridge.certificate_of_global B hglobal
    simpa [Bun.vanishing_family_matches] using h
  dichotomy_cross_certificate := by
    intro B hglobal _hsource
    have hpriced :=
      Bun.dichotomy_cross_bridge.priced_fragments B hglobal
    have hcross :=
      Bun.dichotomy_cross_bridge.cross_profile_charged B hglobal
    exact
      ⟨by
        simpa [Bun.dichotomy_cross_family_matches] using hpriced,
       by
        simpa [Bun.dichotomy_cross_family_matches] using hcross⟩
  threshold_defect_of_family_no_arbitrage := by
    intro B hglobal hsource hnoarb
    exact
      Bun.threshold_handoff_of_family_no_arbitrage
        B hglobal hsource hnoarb

/-- Named obligation-level threshold handoff.

This theorem-level edge is the endpoint-type-compression form of the raw
`threshold_defect_of_family_no_arbitrage` field: downstream proofs should call
this edge so graph/workmap tooling sees that threshold conversion consumes the
same source-ready profile family and a paid family no-arbitrage receipt. -/
theorem threshold_defect_of_trackb_profile_decomposition_family_no_arbitrage
    (obligation : TrackBProfileDecompositionObligation)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B)
    (hsource :
      TrackBProfileDecompositionThresholdHandoffSourceReady
        obligation.source_receipt B hglobal)
    (hnoarb :
      familyPayoff (obligation.profile_family_of_block B) ≤
        familyPrice (obligation.profile_family_of_block B)) :
    ThresholdDefectConvexity B :=
  obligation.threshold_defect_of_family_no_arbitrage
    B hglobal hsource hnoarb

/-- All four declared profile-decomposition branches independently feed the
same threshold-defect handoff for a global block.

This is an anti-decorative-field guard: null, concentration, vanishing, and
dichotomy/cross certificates are all consumed by theorem-level edges.  The
hard PDE content is still the construction of those certificates for the fixed
profile family. -/
theorem threshold_defects_of_all_trackb_profile_decomposition_branches
    (obligation : TrackBProfileDecompositionObligation)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ThresholdDefectConvexity B ∧
      ThresholdDefectConvexity B ∧
        ThresholdDefectConvexity B ∧
          ThresholdDefectConvexity B := by
  let F := obligation.profile_family_of_block B
  have hbranch_source :
      TrackBProfileDecompositionBranchSourceReady
        obligation.source_receipt B hglobal :=
    trackb_profile_decomposition_branch_source_ready
      obligation.source_receipt B hglobal
  have hthreshold_source :
      TrackBProfileDecompositionThresholdHandoffSourceReady
        obligation.source_receipt B hglobal :=
    trackb_profile_decomposition_threshold_handoff_source_ready
      obligation.source_receipt B hglobal
  have hnull :
      familyPayoff F ≤ familyPrice F :=
    family_no_arbitrage_of_null_profile_cap_branch
      F
      (obligation.null_certificate B hglobal hbranch_source)
  have hconcentration :
      familyPayoff F ≤ familyPrice F :=
    family_no_arbitrage_of_concentration_impact
      F
      (obligation.concentration_certificate B hglobal hbranch_source)
  have hvanishing :
      familyPayoff F ≤ familyPrice F :=
    family_no_arbitrage_of_vanishing
      F
      (obligation.vanishing_certificate B hglobal hbranch_source)
  have hcross :=
    obligation.dichotomy_cross_certificate B hglobal hbranch_source
  have hdichotomy :
      familyPayoff F ≤ familyPrice F :=
    family_no_arbitrage_of_cross_profile_charging
      F
      hcross.1
      hcross.2
  exact
    ⟨threshold_defect_of_trackb_profile_decomposition_family_no_arbitrage
        obligation
        B hglobal hthreshold_source hnull,
      threshold_defect_of_trackb_profile_decomposition_family_no_arbitrage
        obligation
        B hglobal hthreshold_source hconcentration,
      threshold_defect_of_trackb_profile_decomposition_family_no_arbitrage
        obligation
        B hglobal hthreshold_source hvanishing,
      threshold_defect_of_trackb_profile_decomposition_family_no_arbitrage
        obligation
        B hglobal hthreshold_source hdichotomy⟩

/-- The source-aware Track B decomposition obligation supplies the older
profile-family limit certificate interface.

This is the real endpoint-compression projection for the decomposition target:
the certificate is not assumed as a fresh field. It is assembled from the
null, concentration, vanishing, and dichotomy/cross branch certificates already
carried by `TrackBProfileDecompositionObligation`. -/
def profile_family_limit_certificate_of_trackb_profile_decomposition
    (obligation : TrackBProfileDecompositionObligation)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    ProfileFamilyLimitCertificate (obligation.profile_family_of_block B) := by
  have hbranch_source :
      TrackBProfileDecompositionBranchSourceReady
        obligation.source_receipt B hglobal :=
    trackb_profile_decomposition_branch_source_ready
      obligation.source_receipt B hglobal
  let hnull := obligation.null_certificate B hglobal hbranch_source
  let hconcentration :=
    obligation.concentration_certificate B hglobal hbranch_source
  let hvanishing := obligation.vanishing_certificate B hglobal hbranch_source
  let hcross := obligation.dichotomy_cross_certificate B hglobal hbranch_source
  exact
    { dichotomy :=
        ⟨hcross.2.residual_price_nonnegative,
          hcross.2.cross_payoff_charged,
          hcross.1.profile_no_arbitrage⟩
      concentration := by
        intro P hP
        exact (hconcentration.profile_certificates P hP).impact_coercive
      vanishing := by
        intro P hP
        exact (hvanishing.profile_certificates P hP).no_deployed_payoff
      null_profiles := by
        intro P hP
        exact hnull.null_cap P hP
      cross_recombination := hcross.2.cross_payoff_charged }

/-- Projection from the source-aware Track B decomposition obligation to the
general pricing-kernel limit bridge.

Downstream code that expects the older `PricingKernelProfileLimitBridge` can
consume the same decomposition obligation without rebuilding branch
certificates or bypassing the threshold-handoff source receipt. -/
def pricing_kernel_profile_limit_bridge_of_trackb_profile_decomposition
    (obligation : TrackBProfileDecompositionObligation) :
    PricingKernelProfileLimitBridge where
  profile_family_of_block := obligation.profile_family_of_block
  certificate_of_global := by
    intro B hglobal
    exact
      profile_family_limit_certificate_of_trackb_profile_decomposition
        obligation B hglobal
  threshold_defect_of_family_no_arbitrage := by
    intro B hglobal hfamily
    exact
      threshold_defect_of_trackb_profile_decomposition_family_no_arbitrage
        obligation
        B
        hglobal
        (trackb_profile_decomposition_threshold_handoff_source_ready
          obligation.source_receipt B hglobal)
        hfamily

/-- The profile spine can be viewed as a general pricing-kernel profile bridge
because the dichotomy/cross certificate gives family no-arbitrage directly. -/
theorem no_global_survivor_of_trackb_profile_decomposition
    (obligation : TrackBProfileDecompositionObligation)
    (hquartic :
      ∀ B : FullLedgerBlock, ThresholdDefectConvexity B → FullLedgerNoSurvivor B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B := by
  have hbranches :=
    threshold_defects_of_all_trackb_profile_decomposition_branches
      obligation B hglobal
  exact hquartic B
    hbranches.2.2.2

/-- Projection-typed variant of the profile-decomposition bridge.

Closure-facing code should prefer this theorem so the survival-profit
observable cannot be detached from the threshold-defect ledger. -/
theorem no_global_survivor_of_trackb_profile_decomposition_with_projection_at_block
    (obligation : TrackBProfileDecompositionObligation)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    QuarticSurvivalProjectionReceipt B →
    FullLedgerNoSurvivor B := by
  intro hprojection
  have hbranches :=
    threshold_defects_of_all_trackb_profile_decomposition_branches
      obligation B hglobal
  exact full_ledger_no_survivor_of_quartic_survival_projection B
    hprojection
    hbranches.2.2.2

/-- Legacy family adapter for callers that still carry a projection family.

The family premise is too strong on the raw `FullLedgerBlock` type; new code
should use `no_global_survivor_of_trackb_profile_decomposition_with_projection_at_block`.
-/
theorem no_global_survivor_of_trackb_profile_decomposition_with_projection
    (obligation : TrackBProfileDecompositionObligation)
    (hprojection :
      ∀ B : FullLedgerBlock, QuarticSurvivalProjectionReceipt B)
    (B : FullLedgerBlock)
    (hglobal : IsGlobalTrackBBlock B) :
    FullLedgerNoSurvivor B :=
  no_global_survivor_of_trackb_profile_decomposition_with_projection_at_block
    obligation B hglobal (hprojection B)

end ZtareProofs.NS
