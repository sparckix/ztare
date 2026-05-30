# Cold-LLM null test — SAW PSLQ kappa-bound argument

> **Seam metadata** · `seam_id:` cold_llm_null_saw_pslq_bound · `track:` audits · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Cold-LLM answer

### Setup and what PSLQ actually guarantees

PSLQ (Ferguson–Bailey–Arno 1999, building on Ferguson–Bailey 1992) is a constructive integer-relation algorithm with the following guarantee, which is the only piece of "first-principles" machinery I can lean on here:

**Theorem (Bailey–Ferguson, restated).** Let x ∈ ℝᵈ have an integer relation m ∈ ℤᵈ \ {0}, and let M = ‖m‖₂ be the 2-norm of the smallest such relation. If PSLQ is run with working precision P decimal digits, then PSLQ is guaranteed to terminate with a relation of norm ≤ γ^(d−1) · M provided

  P ≥ c₁ · d · log₁₀(γ^(d−1) · M · κ₂(B)) + c₂,

where γ ≥ √(4/3) is the PSLQ parameter, κ₂(B) is the worst-case 2-norm condition number of the integer matrix B maintained by the algorithm along the trajectory, and c₁, c₂ are small explicit constants (c₁ ≈ 1, c₂ a small additive term). Conversely, if PSLQ terminates declaring NO RELATION at precision P, then **any** integer relation must satisfy

  log₁₀ M ≥ P / (c₁ d) − log₁₀ κ₂(B) − (d−1) log₁₀ γ − c₂/(c₁ d). (★)

This is the only direction of the theorem we can use as a lower bound on the height of an undetected relation.

### Condition X (explicit)

For each of the six runs i = 1,…,6, with dictionary Δ₁ of size d ≤ 5, working precision Pᵢ ∈ [100, 500] decimal digits, and observed (or assumed) PSLQ trajectory condition number κ₂⁽ⁱ⁾, define

  Mᵢ_min := 10^( Pᵢ/(c₁ d) − log₁₀ κ₂⁽ⁱ⁾ − (d−1) log₁₀ γ − c₂/(c₁ d) ).

**Condition X.** For each run i, the PSLQ trajectory satisfies (a) no numerical breakdown (no precision exhaustion before termination), (b) κ₂⁽ⁱ⁾ ≤ K for a stated K, and (c) the input vector xᵢ is the exact-arithmetic embedding of (μ, Δ₁) to precision Pᵢ ≥ P*, where P* is large enough that (★) is non-vacuous.

Under X, **any integer relation among (μ, Δ₁) must have height H ≥ M* := minᵢ Mᵢ_min.**

This is a deterministic certificate, not a probabilistic one. To get an ε we need a prior over the unknown true relation.

### Where the probability has to come from

PSLQ does not randomize, and the six runs share the same input vector up to precision; they are not independent samples. So the only honest way to produce a probability bound is to put a prior π on candidate relations m ∈ ℤᵈ and compute

  ε = π({m : ‖m‖∞ ≤ H_user_cap and (★) is consistent with m existing undetected}).

Given the user's cap H ≤ 10⁸ and dictionary size d ≤ 5, the relevant counting set is {m ∈ ℤᵈ : ‖m‖∞ ≤ 10⁸}, which has cardinality (2·10⁸+1)^5 ≈ 3.2 · 10⁴¹. Under (★) with P = 100, d = 5, γ = √(4/3), κ₂ = K, c₁ ≈ 1, the lower bound on log₁₀ M from a single run is roughly

  log₁₀ M ≥ 100/5 − log₁₀ K − 4 · 0.0625 ≈ 19.75 − log₁₀ K.

So for K ≤ 10¹⁰ (a typical empirical PSLQ trajectory condition number at moderate precision), undetected relations must have ‖m‖₂ ≥ 10^(9.75) ≈ 5.6 · 10⁹, which **already exceeds the user's height cap H ≤ 10⁸.** A single 100-digit run, under condition X with κ₂ ≤ 10¹⁰, deterministically rules out any relation of height ≤ 10⁸. The six runs are redundant for this conclusion; they buy robustness against violations of (a)–(c), not extra log-factors.

### A defensible probabilistic statement

If we adopt a uniform prior on m over the box ‖m‖∞ ≤ H_max for some H_max ≫ 10⁸ (say H_max = 10²⁰, motivated by "any relation a working mathematician would care about"), and we treat the event "condition X fails on run i" as independent across runs with per-run failure probability q (precision-exhaustion or κ-blowup), then

  ε ≤ q⁶ + 𝟙[ M* ≤ H_max ] · (fraction of box with ‖m‖₂ ≥ M*).

For P_min = 100, d = 5, K = 10¹⁰: M* ≈ 10^(9.75). For H_max = 10²⁰ this fraction is ≈ 1 − (M*/H_max)⁵ ≈ 1, which is useless — the prior is doing all the work. For H_max = 10⁸ (user's stated cap), the fraction is **0**, and ε ≤ q⁶. With a generous q = 0.1 per run (κ-blowup or silent precision loss), **ε ≤ 10⁻⁶**.

So the cleanest statement I can give is:

**Theorem (provisional, cold).** Under condition X with K = 10¹⁰ and per-run condition-X-failure probability q ≤ 0.1, the probability that an integer relation of height ≤ 10⁸ exists among (μ, Δ₁) but was missed by all six runs is bounded by ε ≤ q⁶ ≤ **10⁻⁶**.

The deterministic content (no relation of height ≤ 10⁸ exists, conditional on X) comes entirely from Bailey–Ferguson via (★). The six-run redundancy only buys robustness to X-failure.

### Honesty about gaps

1. **q is not derivable from first principles.** It requires either empirical data on PSLQ trajectory behavior on this specific input or a worst-case bound on κ₂ that the operator can certify. I have asserted q ≤ 0.1 without justification.
2. **κ₂(B) is not free.** Bailey–Ferguson's bound is in terms of the trajectory condition number; bounding it a priori for a specific input is open in general. Operators usually report it post-hoc.
3. **The "probabilistic" framing is partly cosmetic.** The real content is the deterministic height lower bound (★). Calling the residual a "probability" requires a prior, and the prior is doing visible work.
4. **Six independent runs at the same precision on the same input are not statistically independent;** they will fail or succeed together if the input is pathological. The factor q⁶ assumes independence of failure modes (e.g., different precisions, different LLL-reduction seeds, different γ), which the prompt does not establish.
5. The construction is **feasible** as a height certificate; it is **only weakly feasible** as a probability bound, and the bound's epistemic force is roughly that of the height certificate plus a hand-set q.

### Bottom line

Partial. The deterministic part — "no relation of height ≤ 10⁸ exists, conditional on κ₂ ≤ 10¹⁰ and clean termination at P ≥ 100" — is rigorous and follows from the Bailey–Ferguson precision lemma. The probabilistic dressing requires either (i) empirical κ₂ trajectory data from the actual six runs, or (ii) a stated prior over candidate relations. Without those, ε is a placeholder, not a derived number.

## Self-assessment

1. **Answer.** Partial reasoning. The deterministic height lower bound from Bailey–Ferguson (★) is real and gives a clean certificate against relations of height ≤ 10⁸ at P ≥ 100, d ≤ 5, κ₂ ≤ 10¹⁰. The probabilistic ε ≤ q⁶ ≤ 10⁻⁶ is honest only under a stipulated per-run X-failure rate q; it is not derived from PSLQ internals. Full rigor requires the actual κ₂ trajectory data from the six runs.

2. **Confidence.** Medium on the deterministic height bound (the Bailey–Ferguson form is standard, my constants c₁, c₂ are schematic). Low on the specific numerical ε — q is asserted, not earned.

3. **Source.** Bailey–Ferguson 1992 / Ferguson–Bailey–Arno 1999 are in training data as the PSLQ guarantee. I have **not** seen a published "probabilistic null-result theorem" combining Bailey–Ferguson with a κ-bound and a multi-run failure-rate model. The construction here is assembled, not recalled.

4. **Cold-LLM verdict.** A fresh GPT-5 / Opus / Gemini-Pro would likely produce the same skeleton: cite Bailey–Ferguson, write (★), notice the prior is doing the work, and concede the probability dressing is partly cosmetic. Numerical constants would vary. Convergent partial answer, not convergent clean theorem.
