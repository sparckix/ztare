# Three Surprise Nominations for NS Track B Clay Closure

I'm holding a hard line on the surprise bar. Here are three that survive it.

---

## Nomination 1: `R.viscosity` ↔ `sharpTarget` (Lipschitz-in-viscosity at the target level)

```lean
theorem sharpTarget_lipschitz_viscosity
    (R R' : Receipt) (hR : R.viscosity > 0) (hR' : R'.viscosity > 0) :
    |sharpTarget R - sharpTarget R'| ≤
      C_sharp * |R.viscosity - R'.viscosity| := by
  sorry
```

**Why a domain expert misses this:**
`R.viscosity` shows up in the hypergraph top-10 (6 hyperedges) but is **completely absent from both the composite top-25 and the robustness list**. That's the structural tell: it's load-bearing in declaration scope but invisible to centrality, because its edges all go *into* receipt-internal lemmas, not outward to `sharpTarget`. A domain expert reads `sharpTarget` as a *target-side* quantity (cluster 0, high-PR sink) and `R.viscosity` as a *receipt-side* parameter (cluster 4/5, structural input) — they are mentally on opposite sides of the closure. The Lipschitz dependence of `sharpTarget` on viscosity is exactly the kind of obligation one assumes is "obviously already discharged by monotonicity in the receipt" — but the graph says no edge currently mediates it. Closing this directly would let viscosity perturbations propagate to the target without going through the full receipt-tree.

---

## Nomination 2: `R.angleConstant` ↔ `R.kNorm` (cross-cluster bridge, sheath ↔ pricing)

```lean
theorem angleConstant_kNorm_bridge
    (R : Receipt) :
    R.angleConstant ≤ κ_bridge * R.kNorm ^ 2 := by
  sorry
```

**Why a domain expert misses this:**
This one is flagged by link-prediction (AA=3.507, rank 7–8) but the surprise is *why* it's missing. Both quantities live in cluster 5 (high out-degree, k_core=0.29) but `R.angleConstant` belongs structurally to the **angular-moment/sheath half** of the Fiedler bisection while `R.kNorm` is consumed downstream by the **pricing/adaptive half** (it feeds `pricingSumSquares` / `sumSquares` in cluster 3). A domain expert treats `kNorm` as a pricing-shell normalization and `angleConstant` as a geometric sheath constant — they look dimensionally and semantically incompatible. But the AA score says they share three common neighbors that *aren't* currently routed through `Low*Receipt`. The reason this is missed: admitting the bridge requires conceding that the angular constant has a pricing-shell interpretation (or symmetrically, that `kNorm` carries angular content), which crosses a conceptual boundary most domain experts maintain on autopilot.

---

## Nomination 3: `B.selfTax` ↔ `threeProfileAssembledTax` (receipt-tree outlier across the cluster-2 wall)

```lean
theorem selfTax_dominates_assembled_three_profile
    (B : Bundle) :
    threeProfileAssembledTax B ≤ 3 * B.selfTax + slack_three :=  by
  sorry
```

**Why a domain expert misses this:**
`B.selfTax` and `threeProfileAssembledTax` are **both 100%-robust** (10/10 runs) and both load-bearing — but they sit in different clusters (`B.selfTax` in cluster 4, the receipt-leaf cluster; `threeProfileAssembledTax` in cluster 2, the maximally cored "branch/cross" cluster at k_core=1.00). Cluster 2 is a dense clique of 8 quantities (`branchA/B`, `crossAB/AC/BC`, `mixedC`, `threeProfile*`) that the structural diagnostics show as a self-contained module — domain experts treat it as an **internally closed combinatorial accounting block**, where the assembled tax is a sum-of-crosses identity, not something you'd bound by a single receipt-level quantity like `B.selfTax`. The receipt-tree adjacency suggests `B.selfTax` is one hop from this clique via shared profile structure, but no edge currently crosses the cluster-2 wall to a non-cluster-2 quantity *other than through the threeProfilePositiveCoherencePrice route*. A direct `selfTax → assembledTax` bound would collapse the three-profile assembly cost into the per-bundle self-tax budget, shortcutting the entire `crossAB/AC/BC` expansion that closure currently has to traverse. The expert blind spot is exactly the high k_core: clique-internal lemmas feel "complete," so external dominators are not searched for.

---

**Held back:** I considered `nu — shell` (link-prediction rank 1, AA=4.328) and `coreFloor — epsilon/fraction` (ranks 2–5), but those are exactly the kind of high-AA-because-same-neighborhood signals that domain experts in this position *do* see — they're predictively accurate but, as you noted, often re-discoveries of edges already covered. Not promoting them.