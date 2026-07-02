/-
LeanMill campaign provenance — restricted_payments_permission_safety_invariants
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=restricted_payments_covenant_v1) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms [propext, Classical.choice, Quot.sound]
  domain      : formalization-compliance
  time        : wall 508.95s launch→close = formalize 211.67s (theory+statement+firewall) + prove 297.28s (proof search) · prove p50 297.28s p95 297.28s
  compute     : cost-to-closure 264.24s mean · 264.24s total
  yield       : 1/5 attempts closed (3 failed)
  phases      : 146.6s leaf.dispatch · 95.3s formalize · 29.9s pool · 13.5s native · 0.1s govern.mnc
  reuse       : cited 0 banked rung(s)
  moves       : native_hammer×3 · proposer_pool×1 · claude_warm×1
-/
import Mathlib

theorem restricted_payments_permission_safety_invariants : ∀ {State RP : Type*}
    [Nonempty State] [Nonempty RP]
    (NoDefault : State → Prop) (FCCRTestPasses : State → Prop)
    (builderBasket cumulativeRP : State → ℝ) (amount : RP → ℝ)
    (Permitted : State → RP → Prop)
    (hPermitted : ∀ s rp,
      Permitted s rp ↔
        NoDefault s ∧ FCCRTestPasses s ∧
          (cumulativeRP s + amount rp < builderBasket s)), (∀ s rp, ¬ NoDefault s → ¬ Permitted s rp) ∧
      (∀ s rp, builderBasket s ≤ cumulativeRP s → 0 < amount rp →
        ¬ Permitted s rp) := by
  intro State RP _ _ NoDefault FCCRTestPasses builderBasket cumulativeRP amount Permitted hPermitted
  constructor
  · intro s rp hNoDefault hPerm
    exact hNoDefault (((hPermitted s rp).mp hPerm).1)
  · intro s rp hBasket hAmount hPerm
    have hStrict : cumulativeRP s + amount rp < builderBasket s :=
      ((hPermitted s rp).mp hPerm).2.2
    linarith

#print axioms restricted_payments_permission_safety_invariants
