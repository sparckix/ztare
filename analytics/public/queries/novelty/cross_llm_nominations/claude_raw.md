# Theorem Nominations for Track B Closure

## Signal Synthesis

**Robust load-bearing core (Diagnostics 1+4):** `leraySelfTaxLimitPrice`, `sharpTarget`, `gap`, `B.gamma`, `B.selfTax`, plus the entire `branchA/B/mixedC/crossAB/crossAC/crossBC/threeProfileAssembledTax/threeProfilePositiveCoherencePrice` cluster (Cluster 2: k_core=1.00, all 100% robust). This 8-member maximal k-core is the structural skeleton — every closure must route through it.

**Authority cluster (Cluster 3):** `gap`, `sumSquares`, `pricingSumSquares` carry auth=0.75 — they are *targets* of inequalities, not sources. Closures should terminate here.

**Disagreement flag:** `S.payoffLimit` is rank-1 by hyperedge membership (16 occurrences) but only 20% robust under edge dropout. Treat as a *naming* hub, not a load-bearing inequality node — do **not** nominate theorems centered on it.

---

## Nomination 1: bridge the three-profile assembly to the limit price

```lean
theorem threeProfileAssembledTax_le_leraySelfTaxLimitPrice
    (B : Profile) :
    threeProfileAssembledTax B.branchA B.branchB B.mixedC
      B.crossAB B.crossAC B.crossBC
    ≤ leraySelfTaxLimitPrice B.gamma B.selfTax
```

**Justification:** Cluster 2 (k_core=1.00, 100% robust across all 8 members) forms a closed combinatorial unit assembling `threeProfileAssembledTax`. Cluster 0 contains the *limit* quantities (`leraySelfTaxLimitPrice`, `B.gamma`, `sharpTarget`) with high PR+betweenness. **No edge currently bridges Cluster 2 → Cluster 0**, yet the proof spine clearly needs the assembled three-profile tax to dominate the Leray limit. This is the missing inter-cluster bound. Should be `le_trans` through `threeProfilePositiveCoherencePrice`.

---

## Nomination 2: close the coreFloor / shell / nu / epsilon quadrangle

```lean
theorem coreFloor_le_epsilon_mul_shell
    (nu epsilon : ℝ) (hnu : 0 < nu) (hε : 0 < epsilon) :
    coreFloor nu epsilon ≤ epsilon * shell nu
```

**Justification:** Diagnostic 2 link prediction shows **four of the top-6 missing edges** form a tight quadrangle: `nu—shell`, `coreFloor—epsilon`, `coreFloor—fraction`, `coreFloor—shell` (all AA=4.328, CN=3, tied for #1). Adamic-Adar this high with no current edge is a strong "missing inequality" signal — these four nodes co-occupy a neighborhood with no bridging bound. The most natural single inequality that explains all four absences is a product bound `coreFloor ≤ ε · shell` (which forces co-occurrence of all four through one signature).

---

## Nomination 3: terminate authority cluster via norm_num-discharged sum-of-squares

```lean
theorem gap_le_pricingSumSquares_of_sumSquares
    (xs : Fin n → ℝ) :
    gap xs ≤ pricingSumSquares xs ∧ pricingSumSquares xs ≤ sumSquares xs
```

**Justification:** Cluster 3 has auth=0.75 (very high) and contains `gap, norm_num, unfold, sumSquares, pricingSumSquares` — this is a *tactical* termination cluster: `gap` is rank-3 composite with auth=0.107, and `norm_num`/`unfold` co-occurring as authorities means the closure pattern is "rewrite to sum-of-squares, discharge by `norm_num`." Diagnostic 5 also shows `unfold—norm_num` as AA=2.687 missing edge. The conjunctive form lets `le_trans` chain `gap ≤ pricingSumSquares ≤ sumSquares` to whatever upstream bound the spine provides.

---

## Confidence ranking

1. **Nomination 1** — highest confidence. Cluster 2 → Cluster 0 bridge is structurally forced by k_core=1.00 isolation of the three-profile cluster.
2. **Nomination 3** — high confidence. Authority cluster + `norm_num` co-occurrence is a recognizable Lean closure idiom.
3. **Nomination 2** — moderate confidence. AA signal is strong but the specific *form* (product vs. sum vs. ratio) is guessed; if Codex fails on `≤ ε · shell`, try `coreFloor ≤ shell - epsilon` or `coreFloor ≤ shell / (1+ε)`.

## Explicitly NOT nominated

- Anything centered on `S.payoffLimit`, `continuumGlobalSelfTaxTarget`, `R.gramianConstant` — Diagnostic 4 shows these are noise-sensitive (≤20% robust). The hyperedge-membership rank-1 status of `S.payoffLimit` is a naming artifact.
- `xs`-centered theorems — rank-4 composite but it's a bound variable, not a quantity.