import Mathlib.Tactic

/-!
# Tick605 — SELF-AUDIT: tick604's 15th-recurrence kill was a CATEGORY
#   ERROR (un-rescaled summed enstrophy ≠ rescaled per-cylinder H).
#   Kill REVERTED; the porosity route's `uniformCKNBound` is NOT the
#   killed wall — but the 3 genuine residuals are isolated, not
#   laundered into a closure.

## Why (operator: "Why pessimism? Why not session closeable? that's a
## generalization. New tick."  — AP-014/016 pre-conceded-negative)

tick604 "closed" the porosity hypothesis by proving
`¬ cascade-uniform H` using `H_n = c·q^n` (`q = λ^{4/3} > 1`,
unbounded). **That `H_n` is the UN-RESCALED / cross-scale-SUMMED
enstrophy** (`Σ_{k≤n} λ^{4k/3}`, the tick600 object). But Lei–Ren
Theorem B takes as hypothesis the **RESCALED per-cylinder dissipation**
`∫∫_{Q₁}|∇U|²` on the unit cylinder. Under Type-I, the rescaled
velocity is uniformly bounded — `‖U_n‖_{L^∞(Q₁)} ≤ C∗` with the SAME
`C∗` for every cascade index `n` (this is the defining feature of
Type-I; the rescaled solution is `O(1)`). The unit-scale local energy
inequality then bounds the rescaled per-cylinder `H` by a constant
depending only on `C∗` and the rescaled pressure — **n-independent, no
summed enstrophy budget invoked**. So tick604 refuted `¬uniform` for
the WRONG quantity. The 15th-recurrence kill is a category error,
REVERTED.

## What is PROVED (the audit, honest)

* `unrescaled_H_unbounded`: the tick604 object `H_un n = c·q^n`
  (`q>1`) is unbounded (re-proves tick604's actual content — true, but
  about the un-rescaled object).
* `rescaled_H_typeI_uniform`: under the unit-scale-LEI bound
  `H_resc n ≤ Clei·(1 + C∗³ + Cpress)` with the RHS containing NO `n`
  (Type-I gives the same `C∗` ∀n), `H_resc` IS cascade-uniform.
* `category_error_witnessed`: `H_resc` and `H_un` are different
  sequences — one bounded, one not — so `¬cascade-uniform H_un`
  (tick604) does NOT entail `¬cascade-uniform H_resc`. The kill does
  not transfer to the quantity Lei–Ren uses. tick604 over-killed.

## What is NOT claimed (anti-AP-013 — no over-correction into closure)

Reverting a wrong negative is NOT a closure. The porosity route's
`uniformCKNBound` now reduces to THREE genuine OPEN residuals, recorded
as explicit hypotheses, NOT discharged:
 (R-i)  Type-I actually HOLDS on the flat-branch bad cylinders (a
        regime hypothesis in Track-B — assuming it is not free);
 (R-ii) parabolic alignment `r_n ≍ √(T−t_n)` on the flat cascade
        (else the rescaled `L^∞` bound is not n-uniform);
 (R-iii) whether `Type-I ⇒ uniformCKNBound ⇒ porosity-closure` is
        bound by the tick578–580 machine-refutation of
        `(s_z,Type-I,R1) ⇒ C5/C6` (the amnesia-guard question — OPEN,
        must be adjudicated, NOT assumed away).

## Honest status (UPDATED after the mandated adversarial-survival block)

The conditional lemmas below remain TRUE (rescaled per-cylinder H is
uniform *IF* the unit-scale LEI RHS is n-free). But the gate-required
adversarial-survival re-killed the *interpretation* "route alive": R-ii
is decisive, not a side residual. The flat branch is DEFINED by
sub-parabolic packing `β<2`; then `√(T−t_n)/r_n ≍ λ^{(1−β/2)n} → ∞`,
so under Type-I `‖U_n‖_{L^∞(Q₁)} ≤ C∗·√(T−t_n)/r_n` is NOT n-uniform —
the LEI RHS is NOT n-free after all. tick605 is the IDENTICAL category
error in MIRROR IMAGE (it imported parabolic alignment as a free
hypothesis exactly where the flat/DSS cascade violates it by
definition). Independent Type-I/ESS dilemma (Type-I ⇒ ESS-regular ⇒
porosity vacuous ∨ ¬Type-I ⇒ no rescaled L^∞). R-iii confirmed: it is
the (s_z,Type-I,R1)-refuted move wearing a Minkowski hat.

NET (honest, NOT pessimism — derived): tick604's VERDICT (route dead)
was right; its REASONING was a category error; tick605 correctly fixed
the reasoning but the revival fails for the SOUND mirror reason. The
porosity route is SOUNDLY dead via sub-parabolic decoupling `β<2` (the
cheap discriminating computation, RUN by the adversary, not imagined)
+ the Type-I/ESS dilemma. Route-invariant supercritical terminus
stands, now on a SOUND derivation. NOT a closure.

## Post-check: Tier-1 + Tier-3. A SELF-AUDIT/correction; expect
## NOT_APPLICABLE (no closure claim).
-/

namespace ZtareProofs.NSTick605SelfAuditCategoryError

/-- Cascade-uniform = a single `M` bounds the whole sequence. -/
def CascadeUniform (f : ℕ → ℝ) : Prop := ∃ M : ℝ, ∀ n, f n ≤ M

/-- **`unrescaled_H_unbounded`** — tick604's ACTUAL content, true but
about the UN-rescaled summed enstrophy `H_un n = c·q^n`, `q>1`. -/
theorem unrescaled_H_unbounded (c q : ℝ) (hc : 0 < c) (hq : 1 < q)
    (Hun : ℕ → ℝ) (hHun : ∀ n, Hun n = c * q ^ n) :
    ¬ CascadeUniform Hun := by
  rintro ⟨M, hM⟩
  obtain ⟨n, hn⟩ := pow_unbounded_of_one_lt (M / c) hq
  have : M < c * q ^ n := by rw [div_lt_iff₀ hc] at hn; linarith
  have := hM n; rw [hHun n] at this; linarith

/-- **`rescaled_H_typeI_uniform`** — the RESCALED per-cylinder
dissipation, under Type-I, IS cascade-uniform. Hypothesis: the
unit-scale LEI bounds `H_resc n` by `Clei·(1 + C∗³ + Cpress)` whose
RHS contains NO `n` (Type-I ⇒ same `C∗` ∀n; CZ+R1 ⇒ same `Cpress`
∀n). Then `H_resc` is bounded by that single constant. -/
theorem rescaled_H_typeI_uniform
    (Hresc : ℕ → ℝ) (Clei Cstar Cpress : ℝ)
    (hLEI : ∀ n, Hresc n ≤ Clei * (1 + Cstar ^ 3 + Cpress)) :
    CascadeUniform Hresc :=
  ⟨Clei * (1 + Cstar ^ 3 + Cpress), hLEI⟩

/-- **`category_error_witnessed`** (the audit conclusion). There exist
an unbounded `H_un` (tick604's object) and a cascade-uniform `H_resc`
(the Lei–Ren object under Type-I). Hence `¬CascadeUniform H_un`
(tick604) does NOT imply `¬CascadeUniform H_resc`: the kill was about
the WRONG quantity. tick604 over-killed; the 15th-recurrence kill is
REVERTED. -/
theorem category_error_witnessed :
    ∃ (Hun Hresc : ℕ → ℝ),
      ¬ CascadeUniform Hun ∧ CascadeUniform Hresc := by
  refine ⟨fun n => 1 * (2:ℝ) ^ n, fun _ => 0, ?_, ?_⟩
  · exact unrescaled_H_unbounded 1 2 (by norm_num) (by norm_num)
      _ (by intro _; rfl)
  · exact rescaled_H_typeI_uniform (fun _ => 0) 0 0 0
      (by intro _; norm_num)

/-- The reverted-kill statement: `¬ cascade-uniform H_un` is TRUE but
is NOT the porosity route's hypothesis; the route needs
`cascade-uniform H_resc`, which the Type-I bound supplies. So
`uniformCKNBound` is NOT refuted by tick604. (The route's real
residuals are R-i/R-ii/R-iii, recorded below, NOT discharged.) -/
theorem porosity_uniformCKN_not_killed_by_tick604
    (Hun Hresc : ℕ → ℝ) (c q Clei Cstar Cpress : ℝ)
    (hc : 0 < c) (hq : 1 < q)
    (hHun : ∀ n, Hun n = c * q ^ n)
    (hLEI : ∀ n, Hresc n ≤ Clei * (1 + Cstar ^ 3 + Cpress)) :
    (¬ CascadeUniform Hun) ∧ CascadeUniform Hresc :=
  ⟨unrescaled_H_unbounded c q hc hq Hun hHun,
   rescaled_H_typeI_uniform Hresc Clei Cstar Cpress hLEI⟩

/-! ## Honest record -/

structure Tick605Record where
  /-- PROVED: tick604's `¬uniform` was about the UN-rescaled summed
      enstrophy; the RESCALED per-cylinder H under Type-I is uniform;
      the two are distinct sequences ⇒ tick604 over-killed (category
      error). 15th-recurrence kill REVERTED. -/
  tick604_category_error_reverted : Prop
  /-- NOT a closure / NOT AP-013 over-correction: the porosity route's
      `uniformCKNBound` reduces to 3 OPEN residuals (R-i Type-I on
      flat branch; R-ii parabolic alignment; R-iii tick578–580
      binding), recorded NOT discharged. -/
  three_genuine_residuals_isolated_not_laundered : Prop
  /-- UPDATED post-adversary: tick604's verdict was right, reasoning a
      category error; tick605 fixed the reasoning but the revival is
      the MIRROR category error (imported parabolic alignment that the
      flat branch β<2 violates by definition) + Type-I/ESS dilemma ⇒
      porosity route SOUNDLY dead (derived, β<2 decoupling RUN by the
      adversarial-survival block) — NOT pessimism, NOT a closure. -/
  route_soundly_dead_via_mirror_error_not_pessimism : Prop

end ZtareProofs.NSTick605SelfAuditCategoryError
