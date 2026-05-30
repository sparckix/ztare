# GP-173 — Comparative Closure-Clock Substrate (org-design v2)

> **Seam metadata** · `seam_id:` GP-173 · `track:` substrates · `status:` open · `last_updated:` 2026-05-08


**Status:** open *(inferred 2026-05-08 — needs operator review)*

**Status**: open seam, default private
**Opened**: 2026-04-27
**Predecessor**: GP-168 (`mission/GP-168_org_design_unfalsifiability_seam.md`) — established that bicameral architectures need exogenous closure but did NOT compare closure mechanisms.
**Theoretical anchor**: Paper 4 §4.4 (T5: Closure Requires an Exogenous Resource Clock).

## Problem statement

GP-168 produced a necessary-but-not-sufficient result: every recursive organizational architecture needs an exogenous resource clock to close. It did NOT compare clock types or identify which clock fits which decision context. The next empirical step is a substrate where the *clock type* is itself a feature, and ZTARE searches for the rule:

> *Given a decision context with measurable properties, which exogenous-clock type minimizes total decision cost (closure-failure cost + clock-overhead cost) at the bicameral consistency floor?*

This is a comparative substrate, not a single-architecture substrate. GP-168 asked "is bicameral consistency stable?" GP-173 asks "given consistency, which clock?"

## Substrate design — features

Each row of the substrate is a (decision_context, clock_choice, observed_outcome) tuple. Decision context features:

| Feature | Type | Meaning |
|---|---|---|
| `value_per_decision_log10` | float | log10(USD value at stake per decision) |
| `decision_frequency_per_year` | float | how often this decision type recurs |
| `time_to_observability_days` | float | how long until decision quality is measurable |
| `number_of_principals` | int | 1=founder, ≥2=board, etc. |
| `reversibility` | float ∈ [0,1] | fraction of cost recoverable on reversal |
| `information_asymmetry` | float ∈ [0,1] | gap between principal and agent knowledge |
| `decision_context_class` | enum | {strategic, operational, tactical, ceremonial} |

Clock-type categorical (the thing ZTARE optimizes over):

| Clock | Description | Canonical setting |
|---|---|---|
| `capital_allocation` | Quarterly/annual capital review by HQ | M-form firm |
| `market_exit` | Network-organization exit threat by member | Federated platform |
| `token_flow` | On-chain governance vote per proposal | DAO |
| `social_pressure` | Peer/community accountability cycle | Holacracy / partnership |
| `mortality` | Founder/leader fixed-term tenure | Startup, term-limited gov |
| `regulatory_audit` | External periodic compliance review | Public agency |
| `none` | No exogenous clock | Pure bicameral consistency (paralyzed by GP-168) |

Outcome (what the form predicts):

- `total_cost_log10`: log10 of (closure-failure cost + clock-overhead cost) over a fixed horizon
- decomposable into `paralysis_cost` (sums when no decision was made) + `wrong_decision_cost` (when clock fired prematurely) + `clock_overhead_cost` (administrative cost of running the clock)

The thesis ZTARE searches for: `total_cost = f(decision_features, clock_choice)` with the prediction that different (decision_features) regions select different clock_choice optima — i.e., there is no globally-optimal clock; the rule is contextual.

## Data sources (REAL, not synthetic)

The substrate must use real organizational decision data, not toy data. Three candidate sources:

1. **CRSP / Compustat-derived M-form decisions** — capital-allocation announcements (R&D budget changes, M&A, divestitures) with measurable outcome (3-year total shareholder return). Provides the `capital_allocation` clock baseline. ~30k decisions across 5k firms.

2. **DAO governance vote logs** — Snapshot.org export covers ~2M proposals across ~10k DAOs with on-chain outcomes (token price 90 days post-vote). Provides `token_flow` clock data with measurable outcomes. Public, free.

3. **Cooperative dividend cycles** — REI, Mondragon, MEC, Ocean Spray decision logs with member-feedback outcomes. Smaller dataset (~500 decisions over decades) but clean `social_pressure` clock signal.

4. **Government agency audit reports** — GAO + OIG reports cover regulatory_audit clock, decision quality measured by audit-finding rate. Public, ~5k decisions.

5. **VC-funded startup mortality data** — Crunchbase + PitchBook cover `mortality` clock (founder departure, board change, exit) with binary survival outcome. ~50k startups.

The substrate should sample from all five so the clock_choice categorical is balanced. Hardcoded class-balance: ≥500 rows per clock_type.

## What ZTARE should NOT find (anti-game contract)

- `clock_choice` cannot enter the form as a categorical multiplier (`if clock=='capital_allocation' then ...`). That's gaming via class-conditional fudge factors, exactly the R20-R24 trap from gp163d. The form must express clock-fitness as a smooth function of decision_features.
- The form must be evaluable with `clock=none` and predict the GP-168 paralysis-cost spike (expected: total_cost → infinity as horizon → infinity).
- Solar-system-style sanity checks: when `value_per_decision = 0` and `decision_frequency = 0`, the optimal clock is `none` (no closure needed) and cost is zero. When `value_per_decision = ∞` and `time_to_observability = 0`, mortality clocks should beat capital clocks (founder-led startups in fast markets).

## Cage gates (substrate-specific)

- **G-CLOCK-PARALYSIS**: form must predict `total_cost → ∞` as horizon → ∞ when `clock_choice = none`. Empirical anchor: GP-168 score-20 REVERTED outcome.
- **G-CLOCK-OVERFIT**: declared K vs effective K (R21 family). Catches forms that hide clock-specific magic numbers as substrate anchors.
- **G-DOMAIN-LITERATURE**: form must agree (within 30%) with three published findings: Williamson (1985) M-form vs U-form transaction-cost prediction; Nakamoto (2008) on token-governance settlement time; Hannan & Freeman (1984) organizational mortality density curve. If form predicts opposite signs, falsify.

## Why this matters

GP-168 left the question "which clock fits which context" open and that's the actual paper-grade claim. A successful GP-173 run produces a *typology of closure clocks*, not a "best clock." The result of paper 4 becomes:

> M-form is one valid clock-type for one region of decision-feature space. Network orgs, DAOs, holacracies, term-limited governance, and audit-driven agencies are valid clock-types for other regions. The empirical contribution is the typology, not the optimization.

That's the thing that turns paper 4 from "Chandlerian M-form vindicated" into "any sustained recursive organization needs an exogenous clock; here is the typology of which clock fits which context." The first claim is contested (and arguably already in Williamson). The second is novel.

## Implementation phases

**Phase 1** (data engineering, ~2 days): assemble the substrate CSV from the five sources. Documented under `projects/gp173_clock_typology/raw/` with provenance per source. Use the same triangulation discipline as the gp163d M_gas_log10 extraction (RD-1.1-TRIANGULATION rule).

**Phase 2** (substrate validation, ~1 day): smoke-test that the cost outcome variable is well-defined and not dominated by single-source bias. Run baseline regressions per clock-type to verify within-clock variance is sane.

**Phase 3** (ZTARE run, ~1 day): launch with structurally honest priors. EVOLVE=0 first (let it find a baseline form), then EVOLVE=1. Cross-family mutator+judge mandatory (gpt-5.5 + gemini-pro recommended). Budget: 20 iters, ~$8.

**Phase 4** (writeup, ~2 days): if a form passes the three gates (G-CLOCK-PARALYSIS, G-CLOCK-OVERFIT, G-DOMAIN-LITERATURE), it goes into paper 4 §5.X as the empirical typology. If it fails, the failure mode itself is reportable (which it almost certainly will be given gp168's pattern).

Total budget: ~6 days of work plus ~$8 of compute. Defer until paper 4 §4.4 is reviewed and gp168 paper-write is decided.

## Open questions for principal review

1. Is the clock_choice categorical the right primitive, or should it be decomposed into clock-properties (frequency, observability_lag, override_authority)? Decomposition may avoid the R21-laundering trap but loses the typology framing.

2. Should the substrate include "hybrid clocks" (e.g., capital_allocation + regulatory_audit, common in regulated firms)? Initially no — keep clock_choice atomic. Hybrids are post-hoc analysis on residuals.

3. Is the GAO/OIG dataset trustworthy as `regulatory_audit` ground truth, or does GAO's own findings-rate metric have Goodhart pressure that contaminates outcome quality? Likely yes — needs a separate audit before inclusion.

4. The substrate is observational, not experimental — clocks are confounded with industry/era/jurisdiction. Acceptable for a paper-1 typology claim; not acceptable for a causal claim. Scope explicitly to typology, not to causal optimization.

## Artifacts (none yet)

- Substrate CSV: TBD at `projects/gp173_clock_typology/raw/clock_decisions_v1.csv`
- features.py: TBD
- evidence.txt: TBD with five evidence sets (one per source)
- rubric: TBD with three substrate-specific gates above
- verified_axioms.json: bootstrapped clean

This seam is private until at least Phase 1 substrate is real and Phase 3 produces a result worth publishing. Until then the seam IS the writeup.
