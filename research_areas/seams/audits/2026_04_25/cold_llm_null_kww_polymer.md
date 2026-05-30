# Cold-LLM null test — KWW polymer relaxation

> **Seam metadata** · `seam_id:` cold_llm_null_kww_polymer · `track:` audits · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Cold-LLM answer

**Proposed model:**

$$
R(t) \;=\; \exp\!\left[-\left(t/\tau\right)^{\beta}\right]
$$

with two parameters: a characteristic relaxation time $\tau > 0$ and a stretching exponent $\beta \in (0,1]$. (A third parameter is not needed for the stylized data described; if a non-unit plateau or amplitude were present one could add a prefactor $A$, but the boundary condition $R(0)=1$ already fixes $A=1$, so $K=2$ suffices.)

**Justification from the listed properties:**

1. **$R(0) = 1$ exactly.** Substituting $t=0$ gives $\exp(0) = 1$. The form satisfies the boundary condition with no extra parameter.

2. **$R(t) \to 0$ as $t \to \infty$.** For any $\beta > 0$ and $\tau$ finite, the argument $(t/\tau)^\beta \to \infty$, so $R \to 0$. Satisfied.

3. **$\log R(t)$ vs $t$ is concave (decay accelerates).** We have $\log R(t) = -(t/\tau)^\beta$. The second derivative with respect to $t$ is
$$
\frac{d^2}{dt^2}\log R = -\beta(\beta-1)\,\tau^{-\beta}\,t^{\beta-2}.
$$
For $0 < \beta < 1$ this is **negative** (since $\beta-1 < 0$ flips the sign once, and $-\beta(\beta-1) > 0$ — wait, let me redo: $\beta(\beta-1)<0$, so $-\beta(\beta-1) > 0$, giving a *positive* second derivative). That would make $\log R$ convex in $t$, not concave. Concave $\log R(t)$ vs $t$ (decay accelerating) actually requires $\beta > 1$ — i.e., a *compressed* exponential, not a stretched one.

   Cross-checking against property (4) below resolves the apparent contradiction: the slope on the Weibull/KWW plot is the exponent $\beta$ itself.

4. **$\log(-\log R(t))$ vs $\log t$ approximately linear with slope $\sim 0.6$.** Taking $-\log R = (t/\tau)^\beta$, then $\log(-\log R) = \beta\,\log t - \beta\,\log\tau$. This is exactly linear in $\log t$ with slope $\beta$ and intercept $-\beta\log\tau$. The reported slope $\approx 0.6$ therefore identifies $\beta \approx 0.6$.

   With $\beta = 0.6 < 1$, property (3) as I read it ("concave, decay accelerates") is inconsistent with the other three properties. I read property (3) as a likely mis-statement — the standard KWW form with $\beta < 1$ gives $\log R$ vs $t$ that is **convex** (decay *decelerates* on a linear-$t$ axis; the curve has a long tail). Properties (1), (2), (4) overdetermine the answer to the **Kohlrausch–Williams–Watts (KWW) stretched exponential** with $\beta \approx 0.6$, $\tau$ set by the intercept on the Weibull plot.

**Parameter interpretation:**
- $\tau$: characteristic relaxation timescale; the time at which $R = 1/e \approx 0.368$.
- $\beta$: stretching exponent; $\beta < 1$ corresponds to a broad distribution of microscopic relaxation times (heterogeneous dynamics, hierarchical traps, glassy modes). $\beta=1$ recovers a single-Debye exponential.

**Final form:** $R(t) = \exp[-(t/\tau)^{0.6}]$ with $\tau$ fit from the Weibull-plot intercept; only one free parameter remains after $\beta$ is read from the slope.

## Self-assessment

1. **Answer:** Kohlrausch–Williams–Watts stretched exponential, $R(t)=\exp[-(t/\tau)^\beta]$, with $\beta \approx 0.6$ read directly from the Weibull-plot slope and $\tau$ from its intercept. $K=2$ parameters.

2. **Confidence:** High on the functional form. The combination of "polymer relaxation," "log(-log R) vs log t linear with sub-unit slope," and "decays from 1 to 0 over many decades" is essentially diagnostic. I flagged an apparent inconsistency in property (3) — KWW with $\beta<1$ gives a convex (not concave) $\log R$ vs $t$; I treated (4) as the decisive constraint.

3. **Source:** Yes, recognized form. Commonly called the **stretched exponential**, **Kohlrausch function**, or **KWW (Kohlrausch–Williams–Watts) function**. Standard in dielectric relaxation, glassy dynamics, polymer rheology, anomalous diffusion. The Weibull-plot trick (log(-log R) vs log t) is the textbook KWW identification method.

4. **Cold-LLM verdict:** Yes — any frontier zero-shot LLM (GPT-5, Opus, Gemini-Pro tier) prompted with these four properties would produce the KWW stretched exponential with $\beta\approx 0.6$. The slope-on-Weibull-plot fingerprint is unambiguous and well-represented in training data. This is a low-novelty, high-consensus answer; it is a reasonable null baseline for any discovery framework claiming to "find" KWW from scratch.
