# Cold-LLM null test — SAW μ_square closed-form null

> **Seam metadata** · `seam_id:` cold_llm_null_saw_mu_square · `track:` audits · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Cold-LLM answer

**Setup.** We are asked whether μ ≈ 2.638158530031 admits a non-trivial integer relation against the dictionary Δ₀ = {1, π, √2, √3, ln 2} at PSLQ dimension d ≤ 2 with integer-coefficient height H ≤ 10⁸.

By "PSLQ dimension d ≤ 2," I read: we are looking for a relation of the form

  a·μ + b·x = c   (or equivalently a·μ = b·x + c·1)

where x is a single element (or simple product) drawn from Δ₀ ∪ {pairwise products}, and (a, b, c) are integers with max|·| ≤ 10⁸. Equivalently, μ is rationally expressible as (b·x + c)/a for one such x, with a small height.

**(a) Can I propose a relation?** No. I do not recognize μ ≈ 2.6381585300… as a value lying on any rational line through the listed constants at modest height. Quick sanity probes (done mentally, not by PSLQ):

- μ / π ≈ 0.83975…, μ − π ≈ −0.5034…, μ + 1 − π ≈ 0.4965… — no obvious small-rational match.
- μ / √2 ≈ 1.86547…, μ − √2 ≈ 1.22402…, μ / √3 ≈ 1.52315…, μ − √3 ≈ 0.90601… — none coincide with obvious low-height rationals or with ln 2 (≈ 0.6931).
- μ − 2 ≈ 0.638158…, which is suggestive (close to 1/φ² = 0.38197… no; (3−√5)/2 = 0.38197… no; 2−√2 = 0.58578… no; ln 2 = 0.6931… off by ~0.055). Nothing lines up.
- μ² ≈ 6.95987…, μ³ ≈ 18.366…, e^μ ≈ 13.99 — no obvious tie to the dictionary at d ≤ 2.

So I cannot propose a credible closed form at H ≤ 10⁸, d ≤ 2.

**(b) Can I prove a rigorous null result by construction?** Not from the armchair. A rigorous null result here is a *transcendence / linear-independence* statement of the form: for every nonzero integer triple (a, b, c) with max|·| ≤ 10⁸ and every x ∈ Δ₀, a·μ + b·x + c ≠ 0. To prove this *by construction* (without numerical search) one would need either (i) a closed-form characterization of μ that places it inside a known transcendence-theoretic class disjoint from ℚ-affine combinations of {π, √2, √3, ln 2} (e.g., a Schanuel-style or Baker-style independence theorem applicable to μ), or (ii) explicit irrationality-measure / linear-form-in-logs lower bounds that exclude small-height linear hits.

For a generic numerical constant defined only by its decimal expansion, neither is available. Baker's theorem gives effective lower bounds for |a·ln 2 + b·ln p − c| but does not directly bound |a·μ + b·x + c| unless μ itself is known to be a logarithm/period with computable Mahler/height data. π and √2, √3 are algebraically independent of ln 2 in the relevant senses (Lindemann–Weierstrass + standard results on √n), so the *dictionary* is well-behaved, but μ is the unknown.

**Therefore the honest answer is: empirical PSLQ search is required.** The construction-only null is not available without a closed-form description of μ feeding into a transcendence theorem. What *can* be said rigorously, at the armchair level, is the contrapositive: *if* a relation existed at H ≤ 10⁸, d ≤ 2, PSLQ at ~50-digit precision against Δ₀ would find it; absence of a hit at that precision is strong empirical evidence (not proof) of a null. To upgrade to a theorem one needs either:

  1. A definition of μ as a period / logarithm / algebraic-over-transcendental quantity, then invoke Baker / Wüstholz / Nesterenko, or
  2. An irrationality-measure bound for μ specifically, ruling out small-height approximants.

**My answer: punt to empirical search, with a structural reason why pure construction fails.** Without a closed-form generating description of μ, no transcendence theorem in the current literature certifies the null. The right protocol is: PSLQ at precision ≥ (log₁₀ H) · (d+1) + safety margin ≈ 25–40 digits against Δ₀ and its low-degree products; absence of integer relation up to height 10⁸ is then reported as an empirical null with the standard PSLQ guarantee (no relation of that height *exists at the working precision*).

## Self-assessment

1. **Answer.** Punt: I propose neither a relation (I see none) nor a constructive null theorem (none is available without a closed-form description of μ). I argue the null must be established empirically via PSLQ, and I explain why pure construction fails (no transcendence theorem applies to a constant given only by its decimals).

2. **Confidence.** Medium-high on the meta-claim (you can't prove a height-bounded null for a generic decimal from the armchair); medium on "no obvious relation exists" (my mental probes are coarse, not a real PSLQ run).

3. **Source / recognition.** I do *not* confidently recognize μ ≈ 2.638158530031. The value is in the right ballpark for the 2-D self-avoiding-walk connective constant on the square lattice (μ_square ≈ 2.63815853031…), which is a famous open constant; Duminil-Copin–Smirnov proved μ = √(2+√2) on the *honeycomb* lattice, but μ_square has no known closed form. If μ here is μ_square, the expected answer in the literature is precisely "no closed form known; empirical PSLQ searches against natural dictionaries return null."

4. **Cold-LLM verdict.** A fresh GPT-5 / Opus / Gemini-Pro–level model would likely (a) recognize the constant as the 2-D SAW connective constant with high probability (it is well-known in stat-mech), (b) correctly state that no closed form is known, and (c) correctly distinguish empirical PSLQ null from a constructive transcendence theorem. So yes, I expect convergent answers across frontier cold LLMs.
