# Project Charter — GLP-1 Adoption Economics

**Status:** Active — drafted 2026-04-13
**Domain:** Health economics / pharmaceutical markets

---

## Core Question

GLP-1 receptor agonist drugs (Ozempic, Wegovy, Zepbound) have become the fastest-growing drug category in US history. Prescription claim share rose from 6.9% (2023) to 10.5% (2025); Novo Nordisk slashed US prices by up to 70%; and Goldman Sachs projects a 0.4% GDP boost at 30 million users. But the aggregate numbers hide the question that actually determines whether GLP-1 becomes a systemic healthcare cost event:

**What functional model describes GLP-1 adoption diffusion, and at what penetration level does the employer premium impact become system-threatening rather than manageable line-item?**

A model that extrapolates from current claim growth without modeling the price-sensitivity of uptake, the payer coverage gating mechanism, or the access gap by income is not an answer — it is a trend line.

---

## Out Of Scope

- Clinical efficacy or pharmacology
- International markets (this project is US-only)
- Long-run metabolic health outcomes (not the economic question)
- Any model that cannot be grounded in the publicly available evidence: prescription claim data, CMS coverage decisions, employer survey data, and pricing announcements

---

## End States

### Success

A model `adoption_penetration(t, price, coverage_rate)` is proposed such that:

1. It reproduces the observed 2023–2025 trajectory (6.9% → 10.5% claim share) within a credible functional form (logistic, Bass diffusion, or equivalent).
2. It identifies the threshold penetration at which employer premium impact exceeds 10% (the headline Blue Cross estimate) and states this as a forward-checkable prediction.
3. The model's access-gap mechanism is stated explicitly: who can afford access at each price point, and what payer coverage rate changes the slope.
4. At least one anchor proxy (e.g., Medicare Part D enrollment starting 2027, Medicaid state coverage count) is tied to a model prediction that could be confirmed or falsified within 12 months.

### Failure

- Any model that projects 2030 penetration without a coverage-gating mechanism.
- Any model that treats 70% price cut as uniformly increasing access without modeling who the marginal adopter is at $245/month vs. $800/month.
- Any claim that GLP-1s will "save" the healthcare system that does not account for the access gap and the cost of expanded coverage.

---

## Forecast Type

Adoption diffusion model + threshold identification. The core finding is a threshold, not a point estimate.

---

## Anchor Proxies

1. **2025–2026 prescription growth rate:** Does the model reproduce observed claim share trajectory?
2. **Employer premium threshold:** At what penetration does the 14% premium increase (BCBS estimate) materialize?
3. **Medicare Part D 2027 rollout:** What does the model predict for penetration jump when Medicare coverage starts? Forward-checkable within 12 months.
4. **Medicaid access gap:** 13 states cover GLP-1s for obesity as of Jan 2026. Does the model show a two-speed adoption between covered and uncovered states?
5. **Price elasticity test:** 70% price cut → what does the model predict for 2026–2027 volume growth?

---

## Kill Criteria

1. **If adoption curve shows no price elasticity** (uptake doesn't accelerate after 70% price cut), the demand-gating mechanism is wrong.
2. **If employer premium increase attributable to GLP-1 adoption exceeds 14% at less than 12% penetration OR remains below 5% at 20% penetration**, the cost-transmission model is misspecified. This brackets the plausible range: the BCBS threshold should materialize in the 12–18% penetration window — if it fires earlier or not at all by that point, the model is wrong.
3. **If Medicare 2027 rollout produces less than 20% penetration increase**, the coverage-gating mechanism is too weak to be the primary driver.
