/-
LeanMill campaign provenance — corporate_governance_present_basis_two_gate_and_basis_divergence
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=corpgov) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : formalization-nonmath
  time        : wall 1282.3s launch→close = formalize 967.52s (theory+statement+firewall) + prove 314.78s (proof search) · prove p50 263.65s p95 808.09s
  compute     : cost-to-closure 42.08s mean · 180.92s total
  yield       : 5/7 attempts closed (1 failed)
  phases      : 818.6s leaf.dispatch · 346.4s consolidate · 278.5s formalize · 91s pool · 26.9s native · 5.5s govern.mnc
  reuse       : 4 rung(s) banked this run · 0 reused from prior bank
  moves       : native_hammer×5 · proposer_pool×1 · claude_warm×1
  milestone   : campaign family 'corpgov' — 1 run(s) · REAL elapsed (launch→last) 1305.2s (~22 min) = formalize 497.1s + prove/other · active-solve 180.9s · 5 closures [launch→last is the honest wall]
     - corpgov: 5/7 closed · elapsed 1305.2s (~21.8 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/corporate_governance_quorum_supermajority_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

variable {K : Type*} [Field K] [LinearOrder K] [IsStrictOrderedRing K]

structure Tally (K : Type*) [Field K] [LinearOrder K] [IsStrictOrderedRing K] where
  forPower : K
  againstPower : K
  abstainPower : K
  totalPower : K
  for_nonneg : 0 ≤ forPower
  against_nonneg : 0 ≤ againstPower
  abstain_nonneg : 0 ≤ abstainPower
  total_nonneg : 0 ≤ totalPower
  present_le_total : forPower + againstPower + abstainPower ≤ totalPower

/-- Shares present: votes for, votes against, and abstentions. -/

def presentPower (t : Tally K) : K :=
  t.forPower + t.againstPower + t.abstainPower

/-- Shares cast: votes for and against, excluding abstentions. -/

def castPower (t : Tally K) : K :=
  t.forPower + t.againstPower

/-- Charter fractions are strictly positive and at most one. -/

def CharterFraction (x : K) : Prop :=
  0 < x ∧ x ≤ 1

/-- The quorum gate: present voting power is at least `q` times total power. -/

def QuorumMet (q : K) (t : Tally K) : Prop :=
  q * t.totalPower ≤ presentPower t

/-- Present-basis supermajority: abstentions enter the denominator. -/

def SupermajorityPresent (s : K) (t : Tally K) : Prop :=
  s * presentPower t ≤ t.forPower

/-- Cast-basis supermajority: abstentions are excluded from the denominator. -/

def SupermajorityCast (s : K) (t : Tally K) : Prop :=
  s * castPower t ≤ t.forPower

/-- The institutional basis used for the supermajority denominator. -/

inductive SupermajorityBasis where
  | present
  | cast
deriving DecidableEq

/-- Supermajority with an explicit charter basis. -/

def SupermajorityOnBasis (basis : SupermajorityBasis) (s : K) (t : Tally K) : Prop :=
  match basis with
  | SupermajorityBasis.present => SupermajorityPresent s t
  | SupermajorityBasis.cast => SupermajorityCast s t

/-- Adoption under a specified charter basis. -/

def AdoptedOnBasis (basis : SupermajorityBasis) (q s : K) (t : Tally K) : Prop :=
  QuorumMet q t ∧ SupermajorityOnBasis basis s t

/-- The present-basis charter convention used by the campaign target. -/

def AdoptedPresent (q s : K) (t : Tally K) : Prop :=
  AdoptedOnBasis SupermajorityBasis.present q s t

/--
Support has weakly increased while total and present power are held fixed. This
captures converting against-power or abstain-power into for-power without
changing the quorum denominator.
-/

def MoreSupportSamePresent (t u : Tally K) : Prop :=
  t.totalPower = u.totalPower ∧ presentPower t = presentPower u ∧ t.forPower ≤ u.forPower

def zeroTally : Tally K :=
  { forPower := 0
    againstPower := 0
    abstainPower := 0
    totalPower := 0
    for_nonneg := le_rfl
    against_nonneg := le_rfl
    abstain_nonneg := le_rfl
    total_nonneg := le_rfl
    present_le_total := by simp }

def divergenceTallyRat : Tally ℚ :=
  { forPower := 60
    againstPower := 30
    abstainPower := 10
    totalPower := 100
    for_nonneg := by norm_num
    against_nonneg := by norm_num
    abstain_nonneg := by norm_num
    total_nonneg := by norm_num
    present_le_total := by norm_num }

theorem adoptedPresent_monotone_support_holding_present_fixed
    {q s : K} {t u : Tally K}
    (hadopt : AdoptedPresent q s t)
    (hmore : MoreSupportSamePresent t u) :
    AdoptedPresent q s u := by
  rcases hadopt with ⟨hq, hs⟩
  rcases hmore with ⟨htotal, hpresent, hfor⟩
  constructor
  · unfold QuorumMet at hq ⊢
    rw [← htotal, ← hpresent]
    exact hq
  · unfold SupermajorityOnBasis at hs ⊢
    unfold SupermajorityPresent at hs ⊢
    rw [← hpresent]
    exact le_trans hs hfor

theorem present_and_cast_bases_coincide_without_abstention
    {s : K} {t : Tally K} (h : t.abstainPower = 0) :
    SupermajorityPresent s t ↔ SupermajorityCast s t := by
  simp [SupermajorityPresent, SupermajorityCast, presentPower, castPower, h]

theorem exists_present_cast_basis_divergence_rat :
    ∃ t : Tally ℚ,
      CharterFraction (1 / 2 : ℚ) ∧
        CharterFraction (2 / 3 : ℚ) ∧
          0 < t.abstainPower ∧
            QuorumMet (1 / 2 : ℚ) t ∧
              SupermajorityCast (2 / 3 : ℚ) t ∧
                ¬ SupermajorityPresent (2 / 3 : ℚ) t := by
  refine ⟨divergenceTallyRat, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · norm_num [CharterFraction]
  · norm_num [CharterFraction]
  · norm_num [divergenceTallyRat]
  · norm_num [QuorumMet, presentPower, divergenceTallyRat]
  · norm_num [SupermajorityCast, castPower, divergenceTallyRat]
  · norm_num [SupermajorityPresent, presentPower, divergenceTallyRat]

theorem present_basis_sharp_threshold {q s : K} {t : Tally K} :
    (QuorumMet q t ∧ t.forPower = s * presentPower t → AdoptedPresent q s t) ∧
      (t.forPower < s * presentPower t → ¬ SupermajorityPresent s t) := by
  constructor
  · intro h
    constructor
    · exact h.1
    · unfold SupermajorityOnBasis
      unfold SupermajorityPresent
      linarith
  · intro hlt hsup
    unfold SupermajorityPresent at hsup
    linarith

theorem corporate_governance_present_basis_two_gate_and_basis_divergence : ∀ (q s : K) (hq : CharterFraction q) (hs : CharterFraction s) (t : Tally K), (AdoptedPresent q s t ↔ QuorumMet q t ∧ SupermajorityPresent s t) ∧
      (¬ QuorumMet q t → ¬ AdoptedPresent q s t) ∧
        (¬ SupermajorityPresent s t → ¬ AdoptedPresent q s t) ∧
          ∃ u : Tally ℚ,
            CharterFraction (1 / 2 : ℚ) ∧
              CharterFraction (2 / 3 : ℚ) ∧
                presentPower u = u.totalPower ∧
                  0 < u.abstainPower ∧
                    QuorumMet (1 / 2 : ℚ) u ∧
                      SupermajorityCast (2 / 3 : ℚ) u ∧
                        ¬ SupermajorityPresent (2 / 3 : ℚ) u ∧
                          AdoptedOnBasis SupermajorityBasis.cast
                            (1 / 2 : ℚ) (2 / 3 : ℚ) u ∧
                            ¬ AdoptedPresent (1 / 2 : ℚ) (2 / 3 : ℚ) u := by
  intro q s hq hs t
  refine ⟨?_, ?_, ?_, ?_⟩
  · rfl
  · intro hnotq hadopt
    exact hnotq hadopt.1
  · intro hnots hadopt
    exact hnots hadopt.2
  · refine ⟨divergenceTallyRat, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
    · norm_num [CharterFraction]
    · norm_num [CharterFraction]
    · norm_num [presentPower, divergenceTallyRat]
    · norm_num [divergenceTallyRat]
    · norm_num [QuorumMet, presentPower, divergenceTallyRat]
    · norm_num [SupermajorityCast, castPower, divergenceTallyRat]
    · norm_num [SupermajorityPresent, presentPower, divergenceTallyRat]
    · exact ⟨by norm_num [QuorumMet, presentPower, divergenceTallyRat],
        by norm_num [SupermajorityOnBasis, SupermajorityCast, castPower, divergenceTallyRat]⟩
    · intro hadopt
      exact (by
        norm_num [SupermajorityPresent, presentPower, divergenceTallyRat] :
          ¬ SupermajorityPresent (2 / 3 : ℚ) divergenceTallyRat) hadopt.2
