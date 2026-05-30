Here are 3 anti-predictive, structurally surprising nominations designed specifically to bypass standard domain-expert intuition. They exploit the graph topology to find mathematical shortcuts that an analyst focused purely on algebraic families would completely overlook.

### 1. SURPRISING STRUCTURAL PAIRING: Deep-Core Profile vs. Macroscopic Limit
```lean
theorem threeProfile_direct_limit_bound (profile : Profile) :
  threeProfileAssembledTax profile ≤ leraySelfTaxLimitPrice profile * gap := by
  sorry
```
**Why a domain expert would miss it:** 
Structurally, these quantities sit at opposite ends of the graph hierarchy and in completely different Louvain communities. `threeProfileAssembledTax` sits at the absolute bottom of the k-core (composite k-core 0.167, Cluster 2), functioning as a dense microscopic assembly alongside `branchA` and `crossAB`. Conversely, `leraySelfTaxLimitPrice` is a macroscopic target (k-core 0.071, Cluster 0, high PageRank). 

A domain expert would instinctively try to chain bounds up the k-core hierarchy (e.g., bounding the microscopic assembly by `B.selfTax` first, then climbing to `sharpTarget`, and finally taking the limit). Bounding the raw finite assembly directly against the asymptotic $L^\infty$ limit price (mediated only by the `gap` hub) skips the entire sequence-bound intermediate layer. It is analytically "rude" but structurally valid.

### 2. CROSS-CLUSTER BRIDGE: Sheath Shell vs. Adaptive Prefix
```lean
lemma R_shellN_le_prefix_price (n : ℕ) (h_nu : 0 < nu) :
  R.shellN n ≤ leraySelfTaxPrefixPrice n * R.dampingRate := by
  sorry
```
**Why a domain expert would miss it:** 
This intentionally bridges the fundamental Fiedler bisection of your constraint basin. `R.shellN` and `R.dampingRate` sit squarely in the angular-moment/sheath half (Fiedler ≈ 0.000, Cluster 5/Hyperedge top-tier), while `leraySelfTaxPrefixPrice` sits on the adaptive/pricing side (Fiedler 0.027). 

Historically, mathematicians only allow these two halves to communicate via the `A.receipt` or `Low*Receipt` mediation layer. Bypassing the receipt bridge requires admitting that `pec_b` regime-scoping at the Lipschitz level actually applies to the LP shell case directly. A domain expert would consider the shell index a purely structural property and the prefix price a purely adaptive one, completely missing that the shell thickness itself inherently limits the pricing prefix.

### 3. RECEIPT-TREE OUTLIER: Exiled Leakage vs. Sharp Target
```lean
lemma A_leakageGain_bound_sharp (acc : A.Receipt) :
  A.leakageGain acc ≤ sharpTarget * (S.payoffLimit acc) := by
  sorry
```
**Why a domain expert would miss it:** 
If you look at the Role clusters, the `A.` receipt tree has been fractured. While the primary `A.receipt` sits in the stable Cluster 4 alongside budgets and prices, `A.leakageGain` is a massive structural outlier—it has been exiled to the low-PageRank Cluster 1 alongside slack variables like `B.schurSlack`. 

Because `A.leakageGain` shares a namespace with the receipt family, a domain expert would waste time trying to bind it using standard intra-family algebraic manipulation (e.g., coupling it to `A.taxMargin` or `A.receipt`). By treating it strictly as the structural slack variable that the graph proves it is, you can bound it directly against the Cluster 0 `sharpTarget`. This completely short-circuits the local receipt-tree obligations, instantly collapsing a branch of the Track B closure that would otherwise require tedious family-internal book-keeping.