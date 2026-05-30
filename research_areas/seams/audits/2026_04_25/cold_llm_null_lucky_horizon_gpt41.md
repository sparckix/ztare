# Cold-LLM null — Lucky number validity horizon, GPT-4.1

> **Seam metadata** · `seam_id:` cold_llm_null_lucky_horizon_gpt41 · `track:` audits · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

**Model:** gpt-4.1, zero-shot, no apparatus
**Tokens:** prompt=272, completion=1311

## Cold response

Let's address each question in turn, with careful attention to what is known and what is conjectural.

---

### Q1: **Best closed-form asymptotic for L(n) as n → ∞ that you can defend.**

The lucky numbers are constructed by a sieve similar to the Sieve of Eratosthenes, but with a different rule. The sequence grows more slowly than the sequence of all odd numbers, but more quickly than the sequence of primes.

**Asymptotic form:**  
The best-defended closed-form asymptotic for the nth lucky number \( L(n) \) is:

\[
L(n) \sim c \, n \log n
\]

where \( c \) is a positive constant.

**Justification:**
- This is analogous to the prime number theorem, where the nth prime \( p_n \sim n \log n \).
- Empirical and heuristic arguments (see Ulam, Gardiner, and others) suggest that the lucky numbers have the same leading-order asymptotic as the primes, i.e., \( L(n) \sim n \log n \).
- The constant \( c \) is not exactly 1, but is close to 1. Some sources suggest \( c \approx 1 \), but it is not rigorously proven to be exactly 1.

**Refinements:**
- There are conjectured lower-order corrections (e.g., terms involving \( n \log\log n \)), but the leading term is \( n \log n \).
- No closed-form for the constant \( c \) is known, but it is empirically close to 1.

**Summary:**  
\[
L(n) \sim c\, n \log n \quad \text{as } n \to \infty
\]
with \( c \approx 1 \).

---

### Q2: **Does the best-fit a-coefficient drift as you extrapolate to n ≤ 5·10^5? At what scale does the n log n approximation begin to break down?**

**Coefficient drift:**
- If you fit \( L(n) \approx a n \log n + b n (\log n)^2 + c n \) to data for \( n \leq 10^4 \), the best-fit value of \( a \) will be close to 1, but **it will drift downward** as you include more data up to \( n \leq 5 \times 10^5 \).
- This is because the true asymptotic is not exactly \( n \log n \), and lower-order terms (like \( n \log\log n \) or even oscillatory terms) become more significant at larger \( n \).
- The drift is a sign that the leading-order fit is not capturing all the structure.

**Breakdown scale:**
- The \( n \log n \) approximation works reasonably well for small \( n \), but **relative residuals** (i.e., the fractional error) start to become noticeable (say, >1%) around \( n \sim 10^4 \) to \( n \sim 10^5 \).
- **Absolute residuals** (the difference \( L(n) - n \log n \)) grow with \( n \), but the relative error is more meaningful.
- For \( n \gtrsim 10^5 \), the fit noticeably worsens unless you include lower-order terms.

**Summary:**  
- The best-fit \( a \) drifts downward as \( n \) increases.
- The \( n \log n \) approximation begins to break down (in relative error) at \( n \sim 10^4 \) to \( 10^5 \).

---

### Q3: **What is the conjectured asymptotic density of lucky numbers compared to primes (Hawkins limit)?**

**Hawkins' conjecture:**
- The **asymptotic density** of lucky numbers among the positive integers is **zero** (just like the primes).
- However, the **relative density** of lucky numbers to primes (i.e., the ratio of the number of lucky numbers ≤ \( x \) to the number of primes ≤ \( x \) as \( x \to \infty \)) is conjectured to approach a constant, known as the **Hawkins constant** or **Hawkins limit**.

**Value:**
- The conjectured value of the Hawkins constant is **1**.
- That is, the number of lucky numbers ≤ \( x \) is asymptotically the same as the number of primes ≤ \( x \):
  \[
  \lim_{x \to \infty} \frac{\#\{\text{lucky numbers} \leq x\}}{\pi(x)} = 1
  \]
  where \( \pi(x) \) is the prime counting function.

**Caveats:**
- This is a conjecture, not a theorem.
- Empirical data supports this, but there is no rigorous proof.

---

## **Summary Table**

| Question | Answer |
|----------|--------|
| Q1 | \( L(n) \sim c\, n \log n \) as \( n \to \infty \), with \( c \approx 1 \) (constant not rigorously known) |
| Q2 | The best-fit \( a \) drifts downward as \( n \) increases; \( n \log n \) fit breaks down (relative error >1%) at \( n \sim 10^4 \)–\( 10^5 \) |
| Q3 | The conjectured asymptotic density of lucky numbers to primes is 1 (Hawkins limit: ratio approaches 1 as \( x \to \infty \)) |

**Uncertainties:**  
- The exact value of the constant \( c \) in Q1 is not rigorously known.
- The precise scale at which the \( n \log n \) fit breaks down in Q2 depends on how you measure error, but it's in the \( 10^4 \)–\( 10^5 \) range.
- The Hawkins limit in Q3 is conjectural, not proven.

If you need more technical references or historical context, let me know!
