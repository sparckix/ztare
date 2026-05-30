# Cold-LLM null test — Arnold Cat Map Lyapunov

> **Seam metadata** · `seam_id:` cold_llm_null_arnold_cat_map · `track:` audits · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Cold-LLM answer

The map T(x, y) = (2x + y mod 1, x + y mod 1) is the Arnold cat map on the torus T². Because the modular reduction is piecewise-linear and the linear part is constant, the dynamics on the universal cover are governed by the matrix

    A = [[2, 1],
         [1, 1]].

Derivation (≤ 10 lines):

1. The Jacobian DT(x,y) = A everywhere (mod 1 is locally a translation, derivative 1).
2. Tangent vectors evolve as v_n = A^n v_0, so ‖v_n‖ ~ |μ_max|^n where μ_max is the spectral radius of A.
3. det(A) = 2·1 − 1·1 = 1, tr(A) = 3, so eigenvalues solve μ² − 3μ + 1 = 0.
4. Hence μ± = (3 ± √5)/2; the larger is μ₊ = (3 + √5)/2.
5. Note (3 + √5)/2 = φ², where φ = (1+√5)/2 is the golden ratio (since φ² = φ + 1 = (3+√5)/2).
6. The maximum Lyapunov exponent is λ₁ = lim (1/n) log ‖A^n v‖ = log μ₊ = log((3+√5)/2) = 2 log φ.
7. This holds for Lebesgue-a.e. initial condition by Oseledets, since A is hyperbolic (no eigenvalue on the unit circle) and the map is ergodic w.r.t. Lebesgue measure.

Closed form:  λ₁ = log((3 + √5)/2) = 2 log φ,  with φ = (1+√5)/2.

Numerical value: φ = 1.6180339887…, φ² = 2.6180339887…,
    λ₁ = ln(2.6180339887…) ≈ 0.962424 (to 6 decimal places: **0.962424**).

(Cross-check: 2·ln(1.6180339887) = 2·0.4812118250 = 0.9624236501, which rounds to 0.962424.)

## Self-assessment

1. **Answer.** Closed form λ₁ = log((3+√5)/2) = 2 log φ. Numerical value 0.962424.

2. **Confidence.** Very high. The derivation is elementary linear algebra (eigenvalues of a 2×2 integer matrix) plus the standard fact that for a uniformly hyperbolic toral automorphism the top Lyapunov exponent equals log of the spectral radius. I am not guessing.

3. **Source.** Yes — this is a textbook object. The map is the **Arnold cat map** (Arnold and Avez, 1968), one of the canonical examples in ergodic theory and smooth dynamics. The exponent log((3+√5)/2) = 2 log φ is widely quoted (e.g., Katok–Hasselblatt, Devaney) and the connection to the golden ratio (eigenvalues φ², −φ⁻²) is a standard remark.

4. **Cold-LLM verdict.** Yes — a fresh zero-shot LLM at GPT-5 / Opus / Gemini-Pro level should produce this same answer essentially verbatim. The map is recognizable on sight from the matrix [[2,1],[1,1]], and the derivation is short and standard. I would expect >95% of competent frontier models to give λ₁ = log((3+√5)/2) ≈ 0.962424. This is not a discriminating test of apparatus over a strong cold baseline.
