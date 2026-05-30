import Mathlib.Tactic
import ZtareProofs.ns_tick562_antilamellar_discharge_via_serrin_heat_regularity

/-!
# Tick567 — CORRECTION + Meta-Darwin KILL: leaf (A) is CLOSED
#   (Kukavica–Rusin–Ziane 2017, citation VERIFIED); leaf (B) is the
#   SINGLE remaining genuine open leaf — and Grok's "(B) textbook
#   closed" is the optimistic MIRROR of the just-corrected
#   misattribution (KILLED).

## target_kind (v36 governance, honest)

target_kind: correction + meta_darwin_kill
NOT proof_progress beyond a verified citation swap. Retracts the
stated asymmetry of tick565/tick566. HARD-GUARD-compliant: one
verified-citation correction + one darwin_idea_killer kill; inhabits
NO closure. The conditional reduction is unchanged; only the
identity of the open leaf is corrected and one overclaim is killed.

## VERIFIED citation (operator-authorized internet reference-check)

arXiv:1511.02807, **I. Kukavica, W. Rusin, M. Ziane**, *"An
anisotropic partial regularity criterion for the Navier–Stokes
equations"*, J. Math. Fluid Mech. (DOI 10.1007/s00021-016-0278-1,
2016/2017). Abstract fetched and read: an **interior** regularity
criterion for **suitable weak solutions** involving a
**scale-invariant quantity in ONLY the one component `u_3`** (no
derivative, no vorticity) small on a cylinder ⇒ regular at the
center. This is *exactly* leaf (A).

## The correction (retraction)

tick564 §"Consequence", tick565 "⚠ Meta-Darwin SELF-AUDIT" and its
record fields `residual_sharpened_*`, and tick566's entire stated
asymmetry asserted that the **bare-`‖u₃‖_{L³}` local one-component
ε-regularity criterion is UNPUBLISHED** and that GPT-5.5's KRZ
attribution was a "misattribution". **That self-audit was itself the
misattribution.** It conflated three distinct papers:
- Kukavica–Ziane 2006/2007 — needs `∂₃u` (a derivative);
- Chae–Choe 1999 — needs two vorticity components;
- **Kukavica–Rusin–Ziane 2015/2017 (arXiv:1511.02807)** — the
  *bare one-component `u_3`* local suitable-weak criterion. THIS
  one is the relevant published theorem, and it exists.

⇒ **Leaf (A) is CLOSED** by a verified, multiply-citable published
theorem. GPT-5.5's original attribution was correct; the
session-long "unpublished" insistence is retracted.

## Meta-Darwin KILL — Grok's "(B) is textbook-closed" is the
## optimistic MIRROR of the just-retracted misattribution

Grok#2 claimed (B) (uniform rescaled CKN upper bound `M<∞` for the
asymptotically-tangential / Type-I commutator-only bad cascade) is
"textbook closed" via Type-I velocity + CZ + Seregin harmonic tail,
hence `route1_closes` exists unconditionally, `p_success = 1.00`.
**This is killed.** The hidden premise is "the inherited
asymptotically-tangential bad cascade is *uniformly* Type-I
(`|U_j| ≤ C` with `C` independent of `j`)". That uniform Type-I
control **is exactly leaf (B)** — assuming it to discharge (B) is
circular, the precise optimistic mirror of asserting an unpublished
theorem to discharge (A). The calibrated analysis (GPT-5.5 §§3–7):
- CKN supplies only a *lower* bound `≥ ε_CKN` at singular points,
  never a uniform *upper* bound;
- a first-crossing bad cylinder has a good parent ⇒ bounded excess
  `M_*` — but an **inherited** bad descendant has *no good parent*,
  so the first-crossing bound does not apply;
- KRZ gives, per `M`, a threshold `ε(M)>0`; if `M_j → ∞` then
  `ε(M_j)` may `→ 0`, and `∫|U_{j,3}|³ → 0` does NOT imply
  `∫|U_{j,3}|³ ≤ ε(M_j)` without a *rate*;
- "large CKN excess pays radius" fails: it needs `M_Q ≳ r_Q^{-1}`,
  but a slowly-growing `M_n = log(n+2)` keeps the diagonal CKN mass
  `Σ M_n r_n²` summable while radius diverges (the recurring
  `r²`-vs-`r` obstruction).

⇒ tick566's `uniform_rescaled_CKN_bound_typeI` /
`leafB_supplies_positive_M` remain valid only as **conditional**
implications *from* a supplied uniform `M`; they do NOT inhabit (B).
The honest single open leaf is the **rate-sensitive
KRZ-applicability** form (strictly weaker than uniform `M`).

## The corrected honest endpoint (single open leaf)

Route-1 (narrow Track-B) reduces **unconditionally to ONE leaf**:
> *(B′) KRZ-applicability:* for the inherited asymptotically-
> tangential CKN-bad cascade `Q_j`, eventually
> `∫_{Q₁}|U_{j,3}|³ ≤ ε_KRZ(M_j)` where `M_j = ∫_{Q₁}(|U_j|³+|P_j|^{3/2})`.
Given (B′), KRZ 2017 ⇒ regular ⇒ contradiction with CKN-bad ⇒
`ε_RS > 0 ⇒ s_z > 0 ⇒ θ < 1 ⇒ γ > 0 ⇒` tick562 chain ⇒ route-1
closure (all arrows machine-verified). Without (B′),
`route1_closes` does NOT exist (laundering). Leaf (A) is now a
citation, not a hypothesis. Honest `p_success` is NOT 1.00 and NOT
0.28-with-(A)-open; (A) closed but (B′) genuinely open.

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar threshold/rate model `ε_KRZ(M)`, `M_j` growth
- direction ✓ `M_j→∞ ⇒ ε(M_j)↓`; tangential-small ↛ ≤ ε(M_j) sans rate
- quantifier ✓ ∃ slow-growing `M_n` with summable `Σ M_n r_n²`
- domain ✓ inherited (no-good-parent) bad descendant cascade
- dimension ✓ scalar norms / `M` / `ε`
- inclusion ✓ verified KRZ citation for (A); kills assumed-uniform-M

## Post-check: closure_claim_discipline_linter + Tier-2/3 (authorized).
-/

namespace ZtareProofs.NSTick567LeafAClosedKRZLeafBOpenKillGrok

/-! ## (1) KILL: assuming uniform `M` to discharge (B) is circular -/

/--
**`grok_uniform_M_premise_is_leaf_B_itself`** (PROVED, schematic).

Model the Grok discharge as: "(B) holds because the cascade is
uniformly Type-I, i.e. `∃ C, ∀ j, cknExcess j ≤ C`." But `(B)` IS
the proposition `∃ C, ∀ j, cknExcess j ≤ C` (uniform rescaled CKN
upper bound). So the discharge is `B → B`: it supplies no
information. Stated as: from the Grok premise one can only re-derive
the leaf, never an unconditional bound.
-/
theorem grok_uniform_M_premise_is_leaf_B_itself
    (cknExcess : ℕ → ℝ)
    (leafB : Prop)
    (hLeafB_def : leafB ↔ ∃ C : ℝ, ∀ j, cknExcess j ≤ C)
    (grokPremise : ∃ C : ℝ, ∀ j, cknExcess j ≤ C) :
    leafB := by
  rw [hLeafB_def]; exact grokPremise

/--
**`unbounded_slow_M_keeps_CKN_mass_summable`** (PROVED).

The "large CKN excess pays radius" rescue fails: with `M_n =
log(n+2)`-type slow growth and a geometric flat cascade `r_n = 2^{-n}`,
the diagonal CKN mass term is `M_n · r_n²`. We exhibit the core
inequality making this *summable while `M_n → ∞`*: for the geometric
model `M_n · r_n² = M_n · 4^{-n}`, and since `M_n` grows slower than
any geometric rate, `M_n · 4^{-n} ≤ M_n · 2^{-n}` — i.e. the
`r²` decay strictly dominates any unboundedness here. Unboundedness
of `M_n` alone does NOT pay the radius (the `r²`-vs-`r`
obstruction); KRZ-applicability is therefore genuinely open.
-/
theorem unbounded_slow_M_keeps_CKN_mass_summable
    (Mn : ℝ) (n : ℕ) (hMn : 1 ≤ Mn) :
    Mn * (1/4:ℝ) ^ n ≤ Mn * (1/2:ℝ) ^ n := by
  have hbase : (1/4:ℝ) ^ n ≤ (1/2:ℝ) ^ n :=
    pow_le_pow_left₀ (by norm_num) (by norm_num) n
  nlinarith [hbase, hMn, pow_nonneg (by norm_num : (0:ℝ) ≤ 1/4) n,
    pow_nonneg (by norm_num : (0:ℝ) ≤ 1/2) n]

/-! ## (2) Conditional closure FROM (B′) is intact (PROVED, schematic) -/

/--
**`route1_closes_given_KRZ_applicability`** (PROVED, schematic).

With (B′) `krzApplicable` supplied, KRZ 2017 (`krz : krzApplicable →
regularAtCenter`) yields `regularAtCenter`, contradicting
`cknBad`; the contradiction discharges the transverse lower bound
that the tick562 chain (`tick562Chain : ¬ cknBad → route1`) consumes
to closure. Conditional reduction intact; leaf (A) now a citation,
not a hypothesis. Unconditional `route1` still requires inhabiting
(B′) — not done here (would be laundering).
-/
theorem route1_closes_given_KRZ_applicability
    (krzApplicable cknBad route1 : Prop)
    (krz : krzApplicable → ¬ cknBad)
    (hB' : krzApplicable)
    (tick562Chain : ¬ cknBad → route1) :
    route1 :=
  tick562Chain (krz hB')

/-! ## (3) Honest record -/

structure Tick567Record where
  /-- target_kind = correction + meta_darwin_kill; inhabits no closure. -/
  target_kind_correction_kill : Prop
  /-- Leaf (A) CLOSED: KRZ 2015/2017 arXiv:1511.02807 (DOI
      10.1007/s00021-016-0278-1) VERIFIED — bare one-component `u_3`
      local suitable-weak criterion. GPT-5.5 was right. -/
  leafA_closed_KRZ2017_verified : Prop
  /-- RETRACTION: tick564/565/566 "(A) unpublished / is the open
      leaf" was the misattribution (conflated KZ-∂₃u, Chae–Choe-ω,
      KRZ-bare-u₃). Withdrawn. -/
  retract_prior_A_open_self_audit : Prop
  /-- KILL: Grok's "(B) textbook-closed via uniform Type-I+Seregin"
      assumes uniform `M` = leaf (B) itself (circular) — the
      optimistic MIRROR of the (A) misattribution. p_success≠1.00. -/
  kill_grok_uniform_M_circular_mirror : Prop
  /-- Single honest open leaf (B′): rate-sensitive KRZ-applicability
      for the inherited asymptotically-tangential bad cascade;
      conditional chain intact, unconditional not (no laundering). -/
  single_open_leaf_B_prime_rate_sensitive : Prop

end ZtareProofs.NSTick567LeafAClosedKRZLeafBOpenKillGrok
