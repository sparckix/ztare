# Codex Verdicts on Idea-Feliz Briefs

Recorded: 2026-05-06

Scope: NS Track B proof-spine use. Verdicts are advisory; only typed Lean
patches that survive `lake build` count as proof progress.

| Insight | Verdict | Reason |
|---|---|---|
| Three-profile algebraic completeness | already_have | `ns_gp216_positive_coherence_kernel.lean` already isolates the local scalar algebra: positive-part coherence dominates raw assembled tax and raw-cross shortcuts are refuted. Useful confirmation, not new theorem generation. |
| `S.payoffLimit` fragile bottleneck | worth_translating | Converted into typed Lean by routing GP216 payoff/threshold through `LeraySelfTaxOutputDerivedComponentLimitPassageReceipt`, preserving audited output-source provenance instead of hiding behind the aggregate LSC wrapper. |
| coherence ↔ `positivePart` missing edge | already_have | The correct orientation is already present through `le_positivePart`, `three_profile_tax_le_positive_coherence_price`, and the raw-cross negative theorem. Future nominations in the reverse orientation are wrong. |
| `nu` ↔ shell scaling | right_pattern_wrong_move | The real typed object is not `shell ≤ nu`; it is nondimensional viscous shell tax (`nu * shell^2`) inside low-high reserve/latency receipts. Direct scalar ordering is dimensionally suspect. |

Ex-post utility: 3-5x scout/compression value, not 10-100x theorem generation.
The layer becomes >10x only when coupled to typed endpoint context packs and
compiler/refusal logs.
