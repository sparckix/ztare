/-
LeanMill campaign provenance — statePriceVector_exists_of_noArbitrage
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=notes_ftap_hard_blueprint_0702T0623) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : formalization-nonmath
  time        : wall 2824.56s launch→close = formalize 1366.33s (theory+statement+firewall) + prove 1458.23s (proof search) · prove p50 1280.24s p95 2414.42s
  compute     : cost-to-closure 715.21s mean · 1503.89s total
  yield       : 6/13 attempts closed (7 failed)
  phases      : 1916.3s leaf.dispatch · 221.6s pool · 83.6s native · 43.1s formalize · 0.4s govern.mnc · 0s consolidate
  reuse       : cited 0 banked rung(s)
  moves       : native_hammer×6 · claude_warm×6 · proposer_pool×1
  milestone   : campaign family 'notes_ftap_hard_blueprint' — 2 run(s) · REAL elapsed (launch→last) 4814.3s (~80 min) = formalize 840s + prove/other · active-solve 2719.9s · 6 closures [launch→last is the honest wall]
     - notes_ftap_hard_blueprint_0702T0524: 0/7 closed · elapsed 1984.41s (~33.1 min)
     - notes_ftap_hard_blueprint_0702T0623: 6/13 closed · elapsed 2829.86s (~47.2 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/ftap_hard_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.



/-- Cost of portfolio `theta` at prices `p`. -/
def ftapCost {numAssets : ℕ}
    (p : Fin numAssets → ℝ) (theta : Fin numAssets → ℝ) : ℝ :=
  ∑ i : Fin numAssets, theta i * p i

/-- State payoff of portfolio `theta` under payoff matrix `D`. -/
def ftapPayoff {numAssets numStates : ℕ}
    (D : Fin numAssets → Fin numStates → ℝ)
    (theta : Fin numAssets → ℝ) (s : Fin numStates) : ℝ :=
  ∑ i : Fin numAssets, theta i * D i s

/-- Strict positivity for a finite vector. -/
def StrictPositiveVector {ι : Type*} (x : ι → ℝ) : Prop :=
  ∀ i : ι, 0 < x i

/-- The literal no-arbitrage predicate: nonpositive cost, nonnegative payoff in
every state, and strict improvement either at time zero or in some state is
forbidden. -/
def FTAPNoArbitrage {numAssets numStates : ℕ}
    (D : Fin numAssets → Fin numStates → ℝ) (p : Fin numAssets → ℝ) : Prop :=
  ¬ ∃ theta : Fin numAssets → ℝ,
    ftapCost p theta ≤ 0 ∧
    (∀ s : Fin numStates, 0 ≤ ftapPayoff D theta s) ∧
    (ftapCost p theta < 0 ∨
      ∃ s : Fin numStates, 0 < ftapPayoff D theta s)

/-- A strictly positive state-price vector normalized to price assets directly. -/
def StatePriceVector {numAssets numStates : ℕ}
    (D : Fin numAssets → Fin numStates → ℝ) (p : Fin numAssets → ℝ)
    (q : Fin numStates → ℝ) : Prop :=
  StrictPositiveVector q ∧
  ∀ i : Fin numAssets, p i = ∑ s : Fin numStates, q s * D i s

/-- Augmented payoff matrix: row `i` is `(-p i, D i ·)` over `Option (Fin numStates)`. -/
private def ftapAug {numAssets numStates : ℕ}
    (D : Fin numAssets → Fin numStates → ℝ) (p : Fin numAssets → ℝ)
    (i : Fin numAssets) : Option (Fin numStates) → ℝ :=
  fun o => o.elim (-(p i)) (fun s => D i s)

@[simp] private lemma ftapAug_none {numAssets numStates : ℕ}
    (D : Fin numAssets → Fin numStates → ℝ) (p : Fin numAssets → ℝ)
    (i : Fin numAssets) : ftapAug D p i none = -(p i) := rfl

@[simp] private lemma ftapAug_some {numAssets numStates : ℕ}
    (D : Fin numAssets → Fin numStates → ℝ) (p : Fin numAssets → ℝ)
    (i : Fin numAssets) (s : Fin numStates) : ftapAug D p i (some s) = D i s := rfl

private lemma ftapAug_combo_none {numAssets numStates : ℕ}
    (D : Fin numAssets → Fin numStates → ℝ) (p : Fin numAssets → ℝ)
    (theta : Fin numAssets → ℝ) :
    (∑ i, theta i • ftapAug D p i) none = -(ftapCost p theta) := by
  simp [ftapCost, Finset.sum_apply, mul_neg]

private lemma ftapAug_combo_some {numAssets numStates : ℕ}
    (D : Fin numAssets → Fin numStates → ℝ) (p : Fin numAssets → ℝ)
    (theta : Fin numAssets → ℝ) (s : Fin numStates) :
    (∑ i, theta i • ftapAug D p i) (some s) = ftapPayoff D theta s := by
  simp [ftapPayoff, Finset.sum_apply]

/-- Stiemke's lemma: if a subspace of `ℝⁿ` meets the nonnegative orthant only
at `0`, there is a strictly positive vector orthogonal to it. -/
private lemma ftap_stiemke {n : Type*} [Fintype n] (K : Submodule ℝ (n → ℝ))
    (hK : ∀ v ∈ K, (∀ i, 0 ≤ v i) → v = 0) :
    ∃ x : n → ℝ, (∀ i, 0 < x i) ∧ ∀ v ∈ K, ∑ i, v i * x i = 0 := by
  classical
  have hdisj : Disjoint (K : Set (n → ℝ)) (stdSimplex ℝ n) := by
    rw [Set.disjoint_left]
    intro v hvK hvS
    have hv0 : v = 0 := hK v hvK hvS.1
    have hsum := hvS.2
    rw [hv0] at hsum
    simp at hsum
  obtain ⟨f, u, w, hfK, huw, hfS⟩ :=
    geometric_hahn_banach_closed_compact K.convex
      (Submodule.closed_of_finiteDimensional K) (convex_stdSimplex ℝ n)
      (isCompact_stdSimplex (𝕜 := ℝ) n) hdisj
  have hu0 : (0 : ℝ) < u := by simpa using hfK 0 K.zero_mem
  have hfK0 : ∀ v ∈ K, f v = 0 := by
    intro v hv
    by_contra hne
    have h1 := hfK (((u + 1) / f v) • v) (K.smul_mem _ hv)
    rw [map_smul, smul_eq_mul, div_mul_cancel₀ _ hne] at h1
    linarith
  refine ⟨fun j => f (Pi.single j 1), fun j => ?_, fun v hv => ?_⟩
  · have hmem : (Pi.single j 1 : n → ℝ) ∈ stdSimplex ℝ n := by
      refine ⟨fun k => ?_, ?_⟩
      · by_cases hk : k = j
        · subst hk; simp
        · simp [Pi.single_eq_of_ne hk]
      · simp [Finset.sum_pi_single']
    have hb := hfS _ hmem
    linarith
  · show ∑ j : n, v j * f (Pi.single j 1) = 0
    have hsingle : ∀ j : n, (Pi.single j (v j) : n → ℝ) = v j • (Pi.single j 1 : n → ℝ) := by
      intro j
      ext k
      by_cases hk : k = j
      · subst hk; simp
      · simp [Pi.single_eq_of_ne hk]
    calc ∑ j : n, v j * f (Pi.single j 1)
        = ∑ j : n, f (Pi.single j (v j)) := by
          refine Finset.sum_congr rfl fun j _ => ?_
          rw [hsingle j, map_smul, smul_eq_mul]
      _ = f (∑ j : n, Pi.single j (v j)) := (map_sum f _ Finset.univ).symm
      _ = f v := by rw [Finset.univ_sum_single]
      _ = 0 := hfK0 v hv

theorem statePriceVector_exists_of_noArbitrage : ∀ {numAssets numStates : ℕ}
    (D : Fin numAssets → Fin numStates → ℝ) (p : Fin numAssets → ℝ)
    (h_no_arbitrage : FTAPNoArbitrage D p), ∃ q : Fin numStates → ℝ, StatePriceVector D p q := by
  intro numAssets numStates D p hna
  classical
  have hKpos : ∀ v ∈ Submodule.span ℝ (Set.range (ftapAug D p)),
      (∀ o, 0 ≤ v o) → v = 0 := by
    intro v hv hv0
    obtain ⟨theta, htheta⟩ := (Submodule.mem_span_range_iff_exists_fun ℝ).mp hv
    by_contra hvne
    have hcn : v none = -(ftapCost p theta) := by
      rw [← htheta]; exact ftapAug_combo_none D p theta
    have hcs : ∀ s, v (some s) = ftapPayoff D theta s := by
      intro s; rw [← htheta]; exact ftapAug_combo_some D p theta s
    apply hna
    refine ⟨theta, ?_, ?_, ?_⟩
    · have h0 := hv0 none
      rw [hcn] at h0
      linarith
    · intro s
      have h0 := hv0 (some s)
      rwa [hcs s] at h0
    · have hex : ∃ o, v o ≠ 0 := by
        by_contra hall
        push_neg at hall
        exact hvne (funext hall)
      obtain ⟨o, ho⟩ := hex
      have hop : 0 < v o := (hv0 o).lt_of_ne (Ne.symm ho)
      cases o with
      | none =>
          left
          rw [hcn] at hop
          linarith
      | some s =>
          right
          refine ⟨s, ?_⟩
          rw [← hcs s]
          exact hop
  obtain ⟨x, hxpos, hxorth⟩ := ftap_stiemke _ hKpos
  have hxn : x none ≠ 0 := ne_of_gt (hxpos none)
  refine ⟨fun s => x (some s) / x none,
    fun s => div_pos (hxpos (some s)) (hxpos none), fun i => ?_⟩
  have h := hxorth (ftapAug D p i) (Submodule.subset_span ⟨i, rfl⟩)
  rw [Fintype.sum_option] at h
  simp only [ftapAug_none, ftapAug_some] at h
  calc p i = (∑ s : Fin numStates, D i s * x (some s)) / x none := by
        rw [eq_div_iff hxn]
        linear_combination -h
    _ = ∑ s : Fin numStates, x (some s) / x none * D i s := by
        rw [Finset.sum_div]
        exact Finset.sum_congr rfl fun s _ => by ring

#print axioms statePriceVector_exists_of_noArbitrage
