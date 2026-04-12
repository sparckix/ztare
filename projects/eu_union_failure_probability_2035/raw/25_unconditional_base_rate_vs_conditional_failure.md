---
source_type: source_evidence
---

Title: Lessons from historical monetary unions - is the European monetary union making the same mistakes?
URL: https://link.springer.com/article/10.1007/s10368-018-0416-8
Date: 2018-04-04

Claim / relevance:
- This source helps with the base-rate double-counting problem.
- The latest `%` run is correctly worried that historical failure cases may already be conditioned on severe political or war shocks, which means they should not be imported as an unconditional `base_failure_probability` if a separate stress multiplier is also present.

Key facts / excerpts:
- The paper examines the Latin Monetary Union, Scandinavian Monetary Union, and Austro-Hungarian Monetary Union as historical comparators.
- It argues that these unions were vulnerable because they lacked sufficiently strong common institutions and could not withstand major external shocks, especially World War I.
- The paper explicitly frames the historical cases as lessons rather than as direct one-to-one forecasts for EMU.
- That is important because it means the reference class is informative about conditional fragility under severe stress, but not automatically a clean unconditional hazard rate for the euro area today.

Why this matters for probability:
- It supports the firing squad's complaint that historical monetary-union failure examples are not neutral base-rate draws.
- If the historical reference class is already dominated by severe-shock cases, then using it for `base_failure_probability` and then multiplying again by a `stress_escalation_multiplier` risks counting the same stress channel twice.
- The clean implication is that the model needs either:
  - an unconditional base rate from a calmer reference class, or
  - an explicitly conditional model where the base and stress terms are not pretending to be independent objects.

Supporting references used while extracting:
- Springer article page:
  - https://link.springer.com/article/10.1007/s10368-018-0416-8
- NBER euro breakup prior used elsewhere in the project:
  - https://www.nber.org/papers/w13393

