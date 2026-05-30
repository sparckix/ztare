# Cold-LLM null test — Lucky number validity horizon

> **Seam metadata** · `seam_id:` cold_llm_null_lucky_validity_horizon · `track:` audits · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Cold-LLM answer

The sequence described is the **lucky numbers of Euler** (Gardiner, Lazarus, Metropolis, Stein, Ulam, 1956), OEIS A000959: 1, 3, 7, 9, 13, 15, 21, 25, 31, 33, 37, 43, 49, ...

### Question 1 — Asymptotic

The lucky numbers share a striking number of asymptotic features with the primes. The standard conjecture, supported by both heuristic sieve arguments (Hawkins-style random sieves) and extensive numerical work, is

  L(n) ~ n log n   as n → ∞,

with the same leading-order behavior as the prime counting function's inverse p(n) ~ n log n. A more refined form, paralleling the prime number theorem, is

  L(n) = n log n + n log log n − n + o(n),

i.e. the "lucky number theorem" analogue. Equivalently, if π_L(x) counts lucky numbers ≤ x, then π_L(x) ~ x / log x. I would defend the leading-order n log n with high confidence; the lower-order log log n correction I would defend only as a conjecture with strong heuristic support, not as a theorem.

### Question 2 — Validity horizon and correction

I do not know a published, quantitative drift scale for when n log n alone becomes inadequate and the next correction term must be included. Heuristically, because log log n grows extremely slowly, the n log log n correction matters arithmetically even at small n (it is already ~n·1 by n ≈ 10³), but its *relative* importance compared to the leading n log n term grows only like log log n / log n, which is still ≈ 0.3–0.4 in the 10⁴–10⁶ range. So I would expect the bare n log n form to show a systematic, slowly-growing positive bias across the entire computable range, rather than a sharp transition at any particular n. I am not aware of a paper that pins down a specific crossover scale or a fitted correction with empirical residuals. **Honest answer: I don't know the precise drift scale or a numerically calibrated correction term.**

## Self-assessment

1. **Answer.** Leading asymptotic L(n) ~ n log n, with a conjectured Mertens-style refinement L(n) ≈ n log n + n log log n − n. Drift scale: I don't know a specific n at which n log n breaks down — I expect a slowly-growing systematic bias rather than a sharp transition, and I cannot give a calibrated correction term from memory.

2. **Confidence.** High on the sequence identification (lucky numbers, A000959) and on the n log n leading order. Medium on the n log log n refinement (heuristic, prime-analogous, not proven). Low / honest "don't know" on a published validity horizon or numerically fitted correction.

3. **Source.** I recognize the sequence as Euler's lucky numbers from training data (OEIS, Gardiner et al. 1956, Hawkins random sieve literature, Erdős work on lucky numbers). I do **not** recall a paper that publishes a specific finite-n drift scale or fitted correction term for the n log n asymptotic on lucky numbers.

4. **Cold-LLM verdict.** A fresh GPT-5 / Opus / Gemini-Pro-class model would almost certainly identify the sequence as lucky numbers and give n log n as the leading asymptotic — that part is standard. The n log log n refinement would be hit-or-miss across models. The validity-horizon / drift-scale question I expect most cold LLMs to either decline ("I don't know") or hallucinate a plausible-sounding scale; I do not believe a reliable published answer exists in standard training corpora.
