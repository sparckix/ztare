---
description: "A source-bound investment kernel that composes valuation programs, recursive policies, world-model tournaments, point-in-time evidence, and economic settlement."
---

# JaggedThoughts Investment Workbench

> Up: [`docs/README.md`](../README.md)

The investment workbench compiles point-in-time evidence into an inspectable
paper-capital decision and later scores that frozen decision against a benchmark
and a no-action book. It is designed for a solo investor who needs many theses
to remain comparable, reproducible, and connected to later outcomes.

## What the outside user gets

The user describes the opportunity they want: a value sleeve, a neglected
industry, a fund substitute, or a company with durable earnings power. The
workbench searches public funds and companies, separates cheap exposure from
factor bets, looks through funds to their underlying businesses, tests whether
earnings power and feasible strategic choices can support the price, and routes
survivors into a constrained watchlist or paper portfolio. Later prices settle
the frozen calls.

The edge hypothesis is the joint view. Price-implied expectations, durable
earnings power, factor/state-pricing decomposition, and strategic option
closure usually live in separate workflows. JaggedThoughts binds them to one
evidence epoch and one later scorecard. This is a candidate selection advantage,
not an established alpha claim; only prospective benchmark-relative outcomes
can promote it.

### Public-data activation

A one-shot language scout can be made recurring without encoding its theme in
Python:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  --path projects/jaggedthoughts_capital/workspace/investment \
  scout "Find profitable small-cap industrial companies" \
  --max-results 50 --subscribe profitable-small-industrials
```

The command freezes the compiled intent and writes the exact query plus typed
overrides to `research_jobs/intents.yaml`. The existing discovery service runs
it on the catalog cadence. The downstream acquisition compiler may fetch SEC,
market-price, factor, or issuer evidence under its call budget, but only where
the current adapters can supply the measurements requested by the next stage.
An ETF without a registered issuer adapter remains in the catalog and scout
receipt as a source-capability gap; it no longer consumes a deep-enrichment
slot that can only obtain price history.

### Ranking and the web-research handoff

The funnel ranks before it browses. A deterministic broad screen first assigns
potential inside comparable lanes: public equities against sector peers and
funds inside implementation sleeves. Equity potential gives one vote to
accounting durability and one to the valuation-and-expectations family; the
three algebraically related price/earnings views are averaged inside that family
before it receives weight. Evidence sufficiency is a gate, not another source of
rank. Fund potential groups gross earnings yield and book-to-price into one
valuation family, then separately weights factor-return/risk and implementation
cost. Factor fit, fee-adjusted earnings yield, and factor-return-after-fee remain
diagnostics or separately identified challenger programs; historical residual
alpha receives zero credit. The declared family weights are fixed before
prospective evaluation, never tuned to preserve today's winners. Ordinal
lane ranks are interleaved only to schedule scarce research, so an equity score
is never compared directly with an international-fund score.

Subscription web research receives the highest-ranked unresolved candidate plus
the formal question program chosen by recursive enumeration and frontier closure.
It may find sources, construct a thesis and rival, and name falsifiers. It cannot
alter the screen, rank, queue priority, portfolio weight, or capital authority.
The kernel validates the returned dossier and keeps mixed or adverse findings.
Kernel-observed acceptance time owns dossier and source-access chronology;
model-authored future timestamps are replaced before content hashing and cannot
enter the golden store or seed a strategy frontier.
Date-only publication evidence keeps day precision and is compared at the start
of its declared UTC day; exact timestamps keep instant precision. A malformed
chronology blocks that candidate's proposal without aborting the rest of the
batch.
The subscription worker now distinguishes that deterministic defect from a
transient provider failure. An unambiguous date is retained as an ISO date; an
ambiguous value such as `undated` or `current data through …` creates a
content-addressed terminal research block, records the raw output hash, admits
no evidence, and consumes no retry. If the malformed value already belongs to
an admitted legacy dossier, an append-only quarantine makes that parent
ineligible before reassessment or activation research can call the provider.
If the current discovery index is missing, internally inconsistent, or cannot
prove the request's current candidate identity, candidate web research and
strategy synthesis stop before the provider boundary. An older request is never
used as a ranking fallback.

Discovery publication carries a small rank-to-research handoff receipt. The
receipt is `preparing` while current candidate leaves are being subscribed to
the durable queue and becomes `complete` only after queue compilation returns.
Provider workers treat a preparing or mismatched epoch as unavailable; the
queue compiler alone may inspect it to create the current bindings. The browser
shows this state beside the Goldilocks split.
An incomplete receipt or discovery-compiler change is itself scheduled work.
The service repairs the current source epoch, recompiles the rank if needed,
rebinds request leaves, and stamps `complete` without waiting for the normal
market-data cadence or fetching a new source epoch.
The queue compiler's own receipt carries that run ID and hash. Cached queue
work is reusable only for the caller's expected epoch, and the completed
handoff refuses a queue receipt from any other run.

That potential order continues through the candidate's first company-strategy
frontier. Accepting a dossier immediately records exact qualitative coverage and
queues the source-bound strategy synthesis one slot behind the candidate's
interleave rank. The institutional-learning queue separately ranks cohort,
outcome, and law work by expected information yield. A durable Goldilocks rule
allows at most three consecutive institutional-learning calls while a candidate
waits; the fourth claim is reserved for the highest-potential candidate. Thus
web search and strategy synthesis cannot quietly replace candidate economics
with language salience, while cross-company learning still receives bounded
service.

The browser overlays a small live queue projection on the cached analytical
model. It reports the claim owned by the current worker, the candidate currently
being served, the next potential-ranked candidate, and the queue clock without
recompiling the full source and Golden Store graph.

Point-in-time candidate leaves remain exact. A separate qualitative-research
basis hashes the candidate category, selected question program, policy arm, and
material source contents. An in-flight dossier may finish across a harmless
candidate refresh only when that basis is unchanged. A filing-content or formal-
question change creates a new basis and forces reassessment. This avoids wasting
long web calls while preserving current valuation, factor, rank, and portfolio
calculations as separate exact-epoch objects.

At the 2026-08-15T03:36:14Z read-model epoch the catalog contains 11,950
listed identities. The source transaction materialized 678,672 point-in-time
observations with zero required-source failures. Broad equity ingress begins
from 5,385 common equities, of which 543 have the complete SEC frame needed for
the current cheapness-and-quality screen; a bounded acquisition policy chooses
the next unenrolled names across size, sector, and geography. The published deep
screen contains 100 ranked candidates: 14 pass, 57 remain monitors, and 29 carry
typed source or input blocks. Eleven passing companies and three passing funds
enter the research queue; none becomes a buy call from that transition.

The current fund comparison contains 28 programs across five implementation
sleeves. Twenty-two share the factor, valuation, risk, fee, and liquidity core
needed for comparison, and 15 appear in the outside-user brief with sleeve-local
ranks. They remain a research shortlist: holdings quality, tax, currency,
current-account, and prospective-policy gates still admit zero fund
implementations. The security learner has 68 open frozen return episodes and
zero settlements. The engine can therefore answer what deserves work now and
which paper comparisons are open. It has not earned a positive active-sleeve
weight or a funded answer to “what should I buy today?”.

The strategy side becomes a compounding **strategy genome**. The system records
which moves a business could make, which it actually began, the mechanism and
conditions that should connect the move to earnings, what happened next, and
whether the same mechanism survived elsewhere. “Proven move” is therefore an
evidence ladder—option only → implementation observed → descriptive outcome →
comparator-adjusted outcome → causal transport support—not a label granted by
an analyst or an LLM. The current library has reached implementation observation,
not causal transport.

In plain language, the machine repeatedly asks four questions: what looks
cheap relative to the expectations in its price; whether the business or fund
can plausibly earn through those expectations; which strategic choices could
change that path; and whether the opportunity improves the whole book after
risk and costs. It freezes several answers before the future price exists,
then learns from which complete answer bundles were less wrong. An LLM searches
and challenges; typed programs calculate; deterministic gates control time,
identity, arithmetic, comparison, and authority.

The current public kernel lives in
[`src/ztare/investment/`](../../src/ztare/investment/). Its reference packet is
[`examples/jaggedthoughts/investment/`](../../examples/jaggedthoughts/investment/).
The compounding law layer is described in
[`JaggedThoughts Institutional Learning`](jaggedthoughts_institutional_learning.md).

The content-bound filing-time replay now covers 437 settled accounting episodes
across 57 companies and 17 fiscal-year blocks. It rejected a tempting
complexity claim: the durability composite's pooled rank correlation with next-
year owner-earnings margin was 0.467, versus 0.781 for simple current-margin
persistence. An expanding-prior-block test also found no incremental durability
information: 14 later blocks averaged rho 0.709 for persistence and 0.620
after adding durability. Each forecast now resolves to a hashed issue packet and
a disjoint settlement packet from 85 archived SEC sources: 874 packet manifests
in total. Provider filing dates pass the future-row guard, but the system-clock
archive was captured after these historical episodes. The result is therefore a
retrospective mechanism diagnostic; current-universe sampling, source revision,
and post-period formula selection prevent prospective or return inference.

### One OS, several capital owners and investment subjects

JaggedThoughts is an investment OS for public and private markets. A household,
an ETA fund-of-funds vehicle, and a portfolio company may reuse evidence,
strategy learning, forecasts, and settlement, but they are not the same object.
The architecture therefore separates:

| Identity | Owns | Must not inherit by analogy |
|---|---|---|
| `CapitalMandate` | goal, horizon, liquidity, liabilities, currencies, taxes, risk budget, and authority | a household balance sheet cannot become a fund mandate through shared fields |
| `PublicSecurity` | ticker/issuer or ETF identity, daily price, filings, factors, market-implied expectations, and tradable capacity | exchange liquidity and mark-to-market price do not transfer to private assets |
| `FundInterest` | manager, vehicle, strategy, fees, NAV, commitments, cash flows, look-through exposures, and liquidity terms | ETF holdings availability does not imply private-fund transparency or redemption |
| `PrivateCompany` | ownership, debt, governance rights, operating state, management choices, and exit paths | a private-company valuation is not a quoted-price signal |
| `PositionPolicy` | mandate × subject eligibility, size corridor, costs, thesis state, and exit/hold conditions | research priority does not grant position or operating authority |

The shared layer is deliberately smaller: source and evidence epochs, business
fingerprints, strategy-option systems, thesis/rival mechanisms, prospective
world-model tickets, outcome episodes, and counterexamples. Subject adapters
own valuation, liquidity, factor exposure, ownership rights, and settlement.
This permits transfer learning without turning a public-market backtest into a
private-market claim.

The current product slice is the household/public-market path. Its private
`HouseholdCapitalMandate` binds assets, liabilities, income/human-capital
assumptions, currencies, liquidity reserve, goal, and time horizon. A public
capital-market basis then supplies source-bound cash and broad-sleeve return
assumptions plus a shrunk covariance estimate. The allocator exhaustively
enumerates a declared weight grid, rejects infeasible policies, and closes the
return × volatility × goal-probability frontier. Fund and company research can
implement a sleeve only after their separate evidence gates. The ETA
fund-of-funds path is a later adapter over the same mandate/subject/policy
seams, not a fork of the OS.

## The transaction

```text
capital mandate + play + investment subject + point-in-time observations
  -> entity fingerprint
  -> market-state and equity-risk-premium committee
  -> valuation-program envelope
  -> thesis and rival mechanisms
  -> recursive position-policy frontier
  -> paper-book action
  -> cross-entity portfolio frontier
  -> append-only decision leaves
  -> later outcome and economic scorecard
```

For the operator's household, a smaller planning loop sits above security
selection:

```text
private balance sheet + cash-flow capacity + goal/horizon
  -> goal-return hurdle surface
  -> broad-sleeve capital-market basis
  -> constrained household allocation frontier
  -> fund/security implementation research
  -> paper portfolio + later settlement
```

The goal surface is tunable. Starting investable capital, annual additions,
target, horizon, risk limits, and tax haircuts compile into an allocation and
its annual median/downside wealth paths. The paths use the same current public
return and covariance basis as the allocation; there is no second return knob
presented as that policy's trajectory. Incomplete tax, liability, property,
retirement-account, or liquidity inputs still block operator-policy activation,
but they do not prevent assumption-labeled planning comparisons.

### Planning scenario, paper policy, and account implementation

The household path has four identities because each answers a different
question and changes on a different clock:

| Identity | Question answered | Owner and authority |
|---|---|---|
| `HouseholdAllocationScenario` | What allocation frontier follows from these displayed assumptions? | The planning compiler; tunable, content-addressed, and non-persistent, with policy, capital, and brokerage authority disabled |
| `HouseholdMandateFrontier` | Which planning decisions survive the declared missing-input ranges, and which answer would distinguish the remainder most? | The planning compiler; finite-design, probability-free, content-addressed, and non-authoritative |
| `OperatorPaperPolicy` | Which reviewed allocation should govern the paper book? | The operator paper membrane; it must bind a completed household mandate, the selected scenario and public-basis identities, and every unresolved policy input; capital authority remains disabled |
| `AccountImplementation` | How could that policy be expressed in the operator's actual accounts? | A separate proposal epoch containing positions, account types, tax lots, currencies, restrictions, and estimated costs; it cannot be inferred from planning aggregates and has no brokerage or order authority |

The implemented scenario binds the private goal-surface hash, current public
capital-market-basis hash, a mandate compiled with purpose
`planning_scenario`, the exact scenario controls, and its own
`scenario_sha256`. It exposes annual contribution, horizon, target, liquidity
reserve, risky-weight and loss ceilings, effective equity exposure, minimum
goal probability, per-sleeve return haircuts, and weight-grid resolution. The
allocator then enumerates the declared grid and returns the selected planning
point, rival policies, debt-paydown frontier, and exact blockers. Changing an
input creates different scenario bytes; it does not amend an operator policy.

The mandate frontier then varies only bounded values already declared in the
goal surface. It currently crosses the horizon and contribution grids under one
common-random-number identity, compiles each world through the same allocator,
and quotients worlds by exact selected sleeve weights. Fixed sleeve weights are
reported as invariant planning actions; all others retain their observed range.
For each unresolved input, the shared information-yield primitive measures how
much knowing its value would reduce decision-class entropy. These are uniform
design weights, not beliefs. A field with no declared range stays unpriced, and
no question or invariant coordinate can activate a paper policy.

The budget source has a separate private evidence identity. The extractor opens
the workbook read-only, hashes the source bytes, admits only its declared
worksheet and component ranges, and emits a second hash over the normalized
receipt. It records reported versus component-recomputed savings and the impact
of detected formula overlaps, while `workbook_totals_admitted=false` and
`operator_confirmed=false`. The private path is absent from the receipt.

A formula defect is therefore quarantined to the derived contribution-capacity
coordinate. The compiler recomputes that coordinate from admitted components;
it does not rewrite the workbook, alter independently sourced balance-sheet
facts, change the public market basis, or acquire paper-policy authority. The
scenario presents the recomputation as a tunable default rather than a promise
of future savings.

Before the receipt can support an operator paper policy, its successor must
also bind an extractor version, an explicit range manifest, an explicit
excluded-sheet manifest, a source `as_of`, confirmation or override provenance,
and any currency/FX transformation applied to budget amounts. Those fields are
currently policy blockers, not silently supplied defaults. Account
implementation remains blocked until a separate current snapshot binds account
inventory, positions, tax lots, restrictions, and estimated trade costs.
Every artifact in this path is decision support; none can move capital.

### Where the formal system helps

The grammar states which questions may be calculated. Recursive enumeration
lists the coherent company choices, contingent investment policies, valuation
programs, and portfolio combinations inside that language. Frontier closure
removes dominated programs and names local traps. Z3 then answers bounded
questions that are easy to state and dangerous to eyeball:

- which nonempty company-option sets satisfy cardinality and incompatibility
  constraints, with one canonical typed AST per associative/commutative bundle;
- can this strategy, policy, or portfolio win under any nonnegative mix of the
  declared priorities;
- which exact priority weights make it win, and which rivals exclude it when
  no such region exists;
- can a proposed paper position fit with the other positions under capital,
  turnover, concentration, downside, maximum-name, and minimum-position
  constraints;
- can it fit declared factor, sector, geography, duration, or other sourced
  linear exposure bands, and what exact exposure range remains attainable;
- which constraints prevent a candidate from entering the book;
- at which exact nominal-versus-mechanism-safe utility weight the preferred
  complete allocation changes;
- is a recursive policy total and deterministic over every feasible cell made
  by its declared state conditions, and which branches are unreachable;
- what partial position sizes remain feasible inside each underwriter's frozen
  current-to-target corridor, including the exact binding constraints.

### Research-grounded 100× directions

The architecture intentionally gives an LLM open-world research work and keeps
financial arithmetic behind typed programs: the public
[FinanceQA benchmark](https://arxiv.org/abs/2501.18062) reports large failure
rates on realistic multi-step financial analysis, especially accounting,
valuation conventions, and incomplete-information assumptions. More agent
autonomy should therefore increase hypothesis and source-search breadth while
leaving content hashes, chronology, accounting identities, valuation math, and
settlement mechanically checked.

The largest scalable opportunity is cross-sectional experiment throughput, not
more indicators per security. The asset-pricing literature warns that large
factor and fund searches create false discoveries; the
[Thousands of Alpha Tests](https://doi.org/10.1093/rfs/hhaa111) framework joins
factor analysis, cross-sectional regression, and false-discovery control. In
JaggedThoughts this maps to trial-family registration, one-component ablations,
non-overlapping return blocks, multiplicity-controlled survivors, and explicit
credit assignment across many companies and funds.

Information-theoretic pricing is a stronger adjacent challenger than treating
price motion alone as a physical fluid. The
[Information-Theoretic Asset Pricing Model](https://doi.org/10.1093/jjfinec/nbae033)
constructs a non-negative minimum-entropy stochastic discount factor in rolling
out-of-sample windows and regularizes high-dimensional moment conditions. A
future JaggedThoughts I-SDF leaf should compete against the existing observable
factor, latent-factor, cash, and simple portfolio controls on public monthly
history. It should enter only after the acquisition layer can support the
declared training length; it does not inherit status from the current
probability-current experiments.

The previously considered
[polynomial-time rescaling algorithm](https://doi.org/10.1007/s10107-007-0095-7)
is an optimization method for linear programs, not a market mechanism or alpha
model. The current HiGHS and Z3 layers already own bounded linear feasibility,
preference regions, and exact combinatorial constraints. Reimplementing that
algorithm would add machinery without changing an investment discriminator.

Policy programs are evaluated across the complete feasible truth partition of
their declared conditions, not just at today's state. Consequence-equivalent
frontier programs are represented by the shallowest, shortest executable
program. A conditional that reduces to the same action everywhere therefore
appears as that action rather than as an ornamental decision tree.

Portfolio construction consumes the selected policy's frozen rollout under
every declared rival mechanism. For each security it retains the lower of the
nominal and mechanism returns, the higher downside, and the lower confidence.
The cross-security uncertainty set is rectangular: every combination of those
per-security worlds is admitted. Discrete admission, continuous sizing, and
objective choice therefore use mechanism-safe coordinates; nominal coordinates
remain visible beside them. The difference between nominal and maximin utility
is recorded as the price of robustness.

### Patient ownership and disciplined rotation

The default portfolio action is now `hold`, independent of how often the
capital-cycle service checks for new evidence. A declared
`PatientCapitalPolicy` permits a reduction in a mechanism-safe incumbent only
when its return or thesis-confidence floor is impaired, or when Z3 can match
every reduced unit to a challenger whose mechanism-safe expected-return edge
clears both proposal costs and the declared opportunity-cost hurdle. A blocked
rotation leaves the incumbent unchanged and reports the exact maximum hurdle
that the best available challenger could clear. Additions funded from cash do
not require an incumbent sale. Taxes are intentionally excluded until the
workspace has an account-specific, source-bound tax contract.

This makes the economic mode patient capital allocation rather than trading on
the five-minute service cadence. The policy still needs prospective comparison
against cash, buy-and-hold, simple value/quality rules, and the complete policy
tournament before any return advantage can be claimed.

The economic prior is grounded but not sufficient. [Frazzini, Kabiller, and
Pedersen](https://www.nber.org/papers/w19681) attribute Berkshire's historical
profile to cheap, safe, quality stock selection plus leverage;
[Novy-Marx](https://www.nber.org/papers/w15940) finds gross profitability adds
substantial cross-sectional information and strengthens value strategies;
and [Gârleanu and Pedersen](https://www.aqr.com/insights/research/journal-article/dynamic-trading-with-predictable-returns-and-transactions-costs)
formalize why a replacement signal must clear risk and transaction costs. These
results support the ingredients, not JaggedThoughts' specific forecasts,
strategy ontology, or implementation edge.

### Strategy moves as the institutional learning unit

Strategy learning now preserves the exact option catalog after recursive
enumeration. One `StrategyMove` binds company, evidence epoch, option version,
move kind, a typed mechanism, industry-pressure environment, frontier
participation, and source references. A separate `StrategyImplementationEvent`
distinguishes an available option from an executed move: it binds event kind,
status after the event, occurred/available times, timing precision, and source
references. Exact dated adoption is panel-ready; a first public observation is
interval-censored and cannot masquerade as the execution date. The mechanism names an action, economic
bridge, company-specific object, implementation conditions, and explicit break
conditions. A separate `StrategyMoveOutcomeEpisode` binds that move to a
predeclared business metric, horizon, effect threshold, comparator, and later
source receipt. Operating outcomes evaluate the business move; security returns
evaluate the investment. A rising price cannot by itself credit management's
strategy.

Move families group by `typed action × economic bridge`; they generate transfer
questions but do not select causal peers. A `StrategyMechanismPhenotype` adds
strategy form, addressed actor kinds, and implementation mode. The company
instance retains its exact object, conditions, break cases, event, and sources.
Repeated before/after observations remain descriptive; matched or industry
comparators still route through the existing causal-learning checks before
policy use. An accepted qualified-equity dossier now activates a distinct
leased strategy-frontier job. The request freezes its dossier hash, evidence
epoch, company and candidate identity, and admissible source ids. A signed-in
subscription agent gets no web access in this step: it proposes an exact YAML
AST from the already accepted dossier. The deterministic validator requires
typed mechanisms, a residual representation boundary, ordinal `{-1, 0, 1}`
scenario effects, and dossier-only references before the existing Z3 compiler
can change the library.

The first autonomous pass compiled EPAM, Genpact, and Range Resources. The
recurring source service then admitted a newer dossier for all three and
automatically compiled their successor epochs. The current live library
therefore contains 62 versioned moves across six companies, 20 broad action ×
bridge families, and 61 mechanism phenotypes. Twelve families span more than one
environment. Six moves have source-observed implementation events; two
acquisitions have exact filed adoption dates and four retain interval-censored
timing. Two SARO operating-margin contracts are first due in April 2027. Zero
operating outcomes have settled, so the cross-environment families are transfer
questions rather than learned strategy rules.

The successor epochs also created the first representation-stability evidence.
Broad mechanism-family Jaccard overlap was 25% for EPAM, 27% for Genpact, and
56% for Range; exact option-id, phenotype, and frontier-bundle overlap was zero.
That is too much ontology churn to ignore. Every future request now carries the
latest earlier option vocabulary and frontier bundles as a stability prior,
while forbidding the prior from acting as evidence. The workbench displays each
adjacent-epoch diff so this correction can be evaluated rather than assumed.
The exact Marvell acquisition bundle first activated an eight-peer semiconductor
cohort plan. ADI, ALAB, AMAT, CBRS, INTC, MPWR, NXPI, and TXN were selected by
same-industry market-cap proximity, enrolled through the public SEC adapter,
and given immutable subscription-research requests. The first broad-family
pass classified every peer as equivalent even though the events spanned analog,
deposition equipment, inference cloud, GPUs, audio DSP, connectivity assets,
and an unclosed transaction. That result falsified family-level cohorting. The
successor contract separates exact-phenotype adoption, related-family
treatment, provisional no-family observation, and source gap. Only an exact
dated operational or completed phenotype event may seed a treated panel;
related-family treatment is excluded and cannot serve as a control.
The completed strict first pass found one exact phenotype adoption (ALAB) and seven
related-family treatments. Adaptive acquisition then widened the plan to 16 peers,
found a second peer adoption (CRDO), and classified the remaining new results as
related-family treatment. The current panel has 12 rows across three treated
companies, 13 related-family exclusions, no admissible controls, and no eligible
group-time cell. A fiscal year containing an adoption is partial exposure; only
the following fully exposed company fiscal year can count as post-treatment.
MCHP remains a dead letter because its returned payload asserted adoption without
an exact event; it is not relabelled as a source gap. The causal result is
`inconclusive_underpowered_panel`; no law or policy
was promoted. All 16 grammar projections were evaluated, with six
nondominated coverage × specificity grains retained for later outcome tests.
The exact phenotype now compiles into a versioned causal-law candidate named
`expand adjacent scope via growth`. Its identity binds the phenotype, two focal
move hashes, two implementation-event hashes, industry, creation epoch, outcome,
and estimator. The institutional learner routes the 12 panel rows to that
candidate rather than treating a generic strategy label as the treatment. The
mechanism graph then exposes two conditional compositions:
`strategy phenotype → earnings durability → value-quality active return` and
`strategy phenotype → earnings durability → low-expectations active return`.
These paths organize future tests; neither downstream link grants support to the
upstream move.
The peer-search state machine expands a settled, control-poor cohort from 8 to 16
and at most 25 names while preserving prior result identities. Terminal evidence
gaps do not freeze expansion. The plan has reached 25; ten current peer queries
await source-bound classification. Expansion stops early once four provisional
controls exist and never reclassifies related-family treatment as a control.

The cohort memory now separates the economic query from its retrieval revision.
A later catalog timestamp or longer search-end clock leaves the query hash
unchanged; a different phenotype, focal implementation event, industry, peer, or
source class changes it. Original requests and results remain immutable, while a
coverage chain carries compatible completed intervals forward. The current rebuild
recovers 15 of 25 classifications, leaves ten questions pending, and admits no
unsupported control.
The mechanism-granularity compiler then enumerates all 16 projections over
strategy form, actor pressures, implementation mode, and operating-object
scope. It closes a coverage × specificity frontier but withholds selection
until post-treatment operating histories can score stability and pre-trends.
`workspace strategy-outcome` rejects an outcome
before its frozen horizon or with a mismatched move, contract, unit, or
comparator, then records the settled episode in the golden store. The existing
subscription worker also compiles every matured, unsettled contract into a
durable high-priority research job. Its web agent may locate and interpret the
public documents; only the same deterministic submission path can settle the
episode. This gives the intended compounding shape:

```text
business state × enumerated option × source-bound implementation event
  -> executed strategic move × implementation conditions
  -> source-bound operating outcome
  -> bounded move-family conjecture
  -> causal or predictive challenge across compatible environments
  -> investment thesis about durability and market expectations
  -> prospective paper return
```

### Dual-outcome strategy episode

One implemented strategy can answer two different questions. The operating
contract asks whether the move changed its declared business metric. The
security contract asks whether the later stock return exceeded its declared
benchmark and, when an estimated point-in-time factor vector exists, the return
implied by those frozen factor betas. JaggedThoughts now freezes both under one
content-addressed episode key before either later outcome is selected.

The existing public-observation runtime settles the operating leg using the
latest eligible pre-start baseline and earliest eligible post-horizon value.
The existing closed-book runtime settles the security leg. A narrow join then
computes the factor-controlled return from the factor definitions and betas
available when the episode opened; it never refits the control after seeing the
outcome. Benchmark-only remains an explicit fallback when no eligible factor
receipt exists.

This object does not score the strategy twice or grant attribution. Business
improvement without security alpha can mean the move was expected; security
alpha without the declared operating improvement can expose a rival mechanism.
Only the existing multiplicity-, power-, holdout-, and promotion-gated law
machinery may turn repeated episodes into a bounded research-order adjustment.
The join itself contributes zero adjustment and has no portfolio authority.

### Complete search census

Recursive search creates a second problem: the engine may evaluate hundreds of
formulas, strategy programs, or world models and remember only the survivor.
JaggedThoughts therefore records an immutable `SearchTrialFamily` before the
first outcome boundary. It binds the research question, model family, selection
unit, exact candidate-set hash, generator receipts, declaration time, and first
time outcomes may be accessed. A workspace census then reconciles every observed
empirical search surface to that registry.

The current workspace exposes 203 candidate instances across twelve search
surfaces. That includes nineteen pending closed-book episodes grouped into six
exact horizon-and-candidate families and one pending complete-policy episode.
The seven pending forecast/policy families and the institutional-law family are
now committed before their outcome boundaries: 32 trials in eight families.
Three older empirical surfaces still lack common-registry coverage. The recursive
strategy frontier is decision search rather than empirical evidence, so it stays
visible without pretending that enumerated programs are independent
discoveries. A covered family becomes eligible for multiplicity analysis only
after its outcomes settle; the census itself establishes neither alpha nor
portfolio authority.

For a covered world-model tournament, the census applies one minimal
selection-bias gate. It chooses the best economic candidate by the recorded mean
net excess return, finds that candidate's paired block-permutation p-value
against the declared baseline, and applies a Bonferroni correction using the
full committed trial count. The current workspace has zero available and zero
passing gates because all 20 prospective episodes are still pending.
Deflated Sharpe and probability-of-backtest-overfitting remain explicitly
uncomputed until their complete return-matrix, distribution, effective-trial,
and partition inputs exist.

This design matches three current strategy-research boundaries. [Can AI Do
Strategy?](https://pubsonline.informs.org/doi/10.1287/stsc.2026.intro.v11.n1)
separates prediction, intervention, cross-context extrapolation, and
model-generative strategy; JaggedThoughts keeps distinct receipts for those
claims instead of treating one fluent synthesis as all four. [Strategy
Experiments in Nonexperimental
Settings](https://pubsonline.informs.org/doi/10.1287/stsc.2024.0164) emphasizes
that strategic acts may be nonrepeatable, jointly produced, and capable of
changing the environment. That is why environments, implementation conditions,
break cases, and dated outcome identities cannot be discarded during transfer.
[Theory-Driven Strategic Management
Decisions](https://pubsonline.informs.org/doi/10.1287/stsc.2024.0173) motivates
search over competing causal theories when data are sparse. Recursive
enumeration supplies that search surface; later evidence decides which bounded
parts survive.

Cross-company adoption is staggered. The causal adapter therefore computes
unadjusted group-time effects against never- or not-yet-treated controls rather
than pooling every event into a two-way fixed-effects coefficient. This follows
the identification warning in [Callaway and Sant'Anna](https://arxiv.org/abs/1803.09015)
and [Sun and Abraham](https://doi.org/10.1016/j.jeconom.2020.09.006): differing
adoption times and heterogeneous effects can contaminate conventional event
study coefficients. Every treated panel row binds the first exact implementation
event, its occurrence and availability times, and the first fully exposed entity
fiscal year. A non-adopter can act as a control only inside a hash-bound search
window whose every source event has been classified, with no target move found,
matching point-in-time industry identity, and complete individual outcome
history. An unknown earlier event is not evidence of non-adoption. The current
adapter is diagnostic: it has
no covariate adjustment and cannot promote a law or change paper policy.

The engine also compiles the nominal optimum and the mechanism-safe optimum as
distinct complete policies. Z3 partitions the closed unit interval between
nominal utility and mechanism-safe utility and returns the exact lower and
upper weight at which each policy can lead. This turns “be more conservative”
into an inspectable switch boundary. Both policies enter the existing
prospective allocation tournament when every positive-weight holding has a
point-in-time price in its frozen universe; otherwise the missing holdings are
named in a policy-exclusion receipt.

[Goldfarb and Iyengar](https://doi.org/10.1287/moor.28.1.1.14260) motivate
portfolio uncertainty structures as protection against parameter and model
error. [Bertsimas and Sim](https://www.mit.edu/~dbertsim/papers/Robust%20Optimization/The%20price%20of%20Robustness.pdf)
show how robustness can be paired with an explicit conservatism cost. This
implementation uses source-authored mechanism committees rather than estimated
confidence regions or a calibrated protection budget. It consequently claims
deterministic coverage of the declared worlds and no violation probability.

The valuation interpreter owns the nonlinear cash-flow calculation. For every
declared cash-flow path it now derives the maximum purchase price at which the
implied total return equals the matched risk-free rate plus the underwriting
hurdle. The lowest such price is the robust buy-below boundary; the full range
shows how much of the answer depends on the cash-flow thesis. This is more useful
than sending discounted cash flow through SMT: the economic operator remains
readable, while the solver certifies the discrete and linear choice boundaries.

The [Dunagan–Vempala rescaling paper](https://doi.org/10.1007/s10107-007-0095-7)
that motivated this audit is relevant as a search pattern:
a greedy feasibility process becomes tractable by repeatedly changing the
geometry after violated inequalities are found. The current Capital problems
are small exact rational systems handled by Z3; adopting the paper's solver
would duplicate that engine. Its violated-constraint → separating-witness →
rescale loop is a useful design analogy for larger recursive strategy searches.
The immediate scaling fix is solver compilation rather than rescaling: the
company-choice adapter now asks Z3 for compatible option sets first and builds
one canonical typed program per set. The four-option reference population falls
from 109 raw trees to 11 semantic bundles without changing its six-member
frontier; a five-option live population falls from 215 raw trees to its bounded
21 compatible bundles while preserving its eight-member frontier.

This is substantial SMT use, but not the end state. Maximum-name,
minimum-position, and source-bound linear exposure mandates now share the same
exact admission, sizing, binding, and unsatisfied-core surface. A
`PortfolioExposureBand` must cover the complete candidate universe and cite the
factor-analysis or classification receipts that supplied its coefficients. Z3
returns exact attainable exposure ranges and witnesses at both limits. When a
band blocks one candidate, the solver forces that candidate accepted, removes
only the named band, holds every other mandate fixed, and returns the exact cap
or floor at which admission first becomes possible. The next
economically useful solver surface is a parametric activation region: the exact
hurdle, downside budget, valuation, confidence, or exposure interval at which a
complete allocation changes. Those are the investment analogues of tier,
boundary, and price derivation. Z3 certifies implications of authored or
estimated inputs; it does not estimate expected returns, cash flows, causal
effects, or probabilities.
The rescaling algorithm becomes operational only when a declared choice
population is too large to enumerate: an unsatisfied core can then select the
next separating coordinate and reshape the search metric.

Each object has an owner, identity, evidence epoch, lifecycle, and compatibility
rule. Later information creates a new artifact rather than changing what was
known at the decision time.

## Operator workbench now available

The kernel is wired into the existing ZTARE web shell as the **JaggedThoughts
Capital Workbench**. It now supports one complete local, paper-only operating
path:

The Overview's `InvestorActionBrief` compresses the current typed state into
five investor questions: what the broad scouts and separate challenger intent
sampled, which companies and funds currently receive research attention, what
clears paper gates, which owner acts next and when, and which evidence would
change that answer. The five broad portfolio basis sleeves (BIL, SPY, VXUS,
BND, and TIP) retain a distinct identity from the within-sleeve value-fund
challenger tournament. This is a read adapter; it adds no ranking, return
forecast, recommendation, weight, or capital authority.

- initialize an editable workspace and visibly labelled reference fixture;
- consume SEC company facts, current implied ERP, FRED/ALFRED, direct issuer
  characteristics from iShares, Vanguard, Harbor, Avantis, and First Trust,
  Yahoo retrieval-time price history, HTTPS CSV, and operator CSV adapters;
- refresh a broad retrieval-time catalog of US-listed equities and ETFs without
  a per-security API call;
- compile natural-language research requests into visible entity-kind,
  capitalization, theme, style, and downstream-measurement fields;
- preserve exact response bytes, source receipts, and append-only normalized
  observation epochs;
- enroll a public ticker through the SEC company registry;
- enroll an ETF into the factor watchlist directly from a scout result;
- compile a filing-bounded durable-earnings screen and a factor-aware public
  fund watchlist;
- normalize complete issuer holdings into one contract, compare funds by
  weighted overlap, and acquire the next holdings-weighted company-fundamental
  slice without a terminal-data dependency;
- register the investment metric universe with semantic type, unit, temporal
  type, producer, and eligible entity kinds, then derive standard metrics with
  the existing signal interpreter;
- create a source-bound draft, review it, and activate a distinct paper-policy
  artifact while archiving the draft;
- route active compatible decisions into exact bounded portfolio assembly;
- project the five public household sleeves into candidate-specific fund
  substitutes, evidence coverage, and exact mandate blockers without copying
  weights or creating capital authority;
- lower exact equity and fund paper-watch decisions into one shared
  `ImplementationCandidate` identity. Admission means the current proposal and
  implementation evidence may enter instrument review; the shared compiler then
  binds current factor, covariance, downside, fee, liquidity, and cost evidence
  into a zero-authority paper-portfolio candidate. Private mandate, book, tax,
  and currency remain account-implementation inputs;
- compare each public fund as a one-for-one normalized sleeve substitute using
  the current factor-implied return less expense, aligned price covariance,
  drawdown, quoted-spread entry-cost proxy, liquidity, and holdings overlap;
  close a risk/cost frontier without choosing cross-sleeve weights, then hand
  only admitted programs to the existing portfolio compiler once a separate
  portfolio mandate and current-book state exist;
- freeze every fund program into one content-addressed
  `FundProgramTournamentInput`; open within-sleeve factor-net-expense and
  aggregate-earnings-power ranking tickets only where at least two programs
  share the same required fields, and score them through the same prospective
  return window as the portfolio-policy tournament. Holdings-weighted quality
  becomes a third ticket only after the declared coverage threshold is met;
  tax, currency, and mandate gaps remain private-implementation blockers rather
  than default assumptions;
- derive cash-flow-path purchase-price boundaries at the declared excess-return
  hurdle;
- close company-option compatibility and bundle size in Z3 before constructing
  canonical recursive choice programs, avoiding associative tree duplication;
- certify portfolio feasibility and per-candidate constraint blockers with Z3,
  including optional maximum-name and minimum-position mandates, while
  preserving the complete bounded combination population;
- derive an exact continuous partial-sizing envelope inside every frozen
  current-to-target corridor, with per-candidate capacity, single-objective
  optima, declared-utility optimum, and binding-constraint witnesses;
- lower each selected policy's nominal state and rival-mechanism terminal
  states into a rectangular portfolio uncertainty set; use return floors,
  downside ceilings, and confidence floors for admission and sizing while
  preserving nominal comparisons and the price of robustness;
- record typed opportunity-funnel transitions from observation through
  settlement;
- capture later asset and benchmark prices without hand-copying the decision
  hash;
- run shared world-model tournaments and isolated experimental model families;
- compile persistent-company valuation × durability states, separate directed
  transition current from its reversible same-information control, and reject
  the carrier when later state and economic gates do not improve;
- run a capability-adaptive valuation market across the typed interpreter,
  direct frontier reasoning, a guarded model-authored program, and their
  agreement-gated hybrid;
- freeze prospective closed-book evidence bundles and compare valuation,
  momentum, no-edge, and sealed frontier forecasts against later public prices;
- admit qualified discovery leaves directly into small, paper-only prospective
  probes without first inventing an operator decision;
- run one recurring capital cycle that settles due forecasts, opens
  non-overlapping prospective windows, and compiles an opportunity book plus
  risk-checked paper posture;
- project settlement readiness at an explicit as-of epoch: issued, settled,
  pending, due, and next-due forecast and complete-policy runs, plus the exact
  strategy-dual issuance blocker. This projection never settles an outcome;
  the current zero-settlement state is expected while horizons are open;
- compile source-authored industry pressures and response options into recursive
  company choice-system frontiers;
- verify every stored leaf and lineage edge.
- register evidence-backed Newton/autoresearch projects in the World Models
  view, while keeping rejected experiments distinct from deployable signals.
- compile company and fund phenotype cohorts, evaluate bounded predictive and
  causal laws, preserve counterexamples, recursively enumerate typed formula
  programs, freeze the training-selected law frontier before holdout scoring,
  and expose its mechanism graph;
- let only prospectively eligible laws apply a bounded, reversible adjustment
  to paper research priority; causal laws additionally require an exact
  candidate × move target, compatible event/environment/metric/unit/horizon,
  and zero training-support overlap; screen state, weights, and capital
  authority stay unchanged.
- turn accepted dossiers into revocable qualitative evidence coverage for later
  candidate epochs, suppressing duplicate full-research calls while exact
  material-source hashes remain covered;
- canonicalize typed strategy-choice graphs up to node naming, surface legacy
  endpoint residuals, and feed the resulting phenotype into later prospective
  cohort analysis as a challenger rather than a score.

The UI read model is a projection, not a second evidence store. Large factor
row-ID vectors are represented by their count and content hash; the complete
vectors remain in the immutable analysis artifacts and golden store. Golden
store verification receipts are reused only while the SQLite database and any
nonempty WAL have the same file-state fingerprint. JSON responses use standard
HTTP gzip when the browser requests it; the current investment projection
transfers at roughly 0.74 MB while complete artifacts remain independently
inspectable. The server reads the atomically compiled projection on entry, so
Capital does not wait for the much broader project-folder inventory or rebuild
the projection on every page load. Every workspace transition replaces the
projection after its writes finish.

The UI lives in
[`forensic-workbench/src/workspaces/investment.jsx`](../../forensic-workbench/src/workspaces/investment.jsx),
while the finance kernel remains independent of React and HTTP. The daily path
is documented in
[`docs/guides/jaggedthoughts_capital_workbench.md`](../guides/jaggedthoughts_capital_workbench.md).

### The capital cycle

The engine now has a single operating object above the component kernels:

```text
new discovery epoch / due forecast / matured outcome
  -> settle admissible closed-book outcomes
  -> open due 21d and 90d entity windows without overlap
  -> join candidates to dossiers, strategy frontiers, and operator decisions
  -> compile underwriting / research / repair queues
  -> derive risk-checked paper posture from active decisions only
  -> write CapitalCycleRun + OpportunityBook golden leaves
  -> freeze one complete-policy block across the qualified universe
  -> later score cash, equal-weight, discovery, learned-law, and operator policies
```

This is where “make money” becomes a testable operating process. It searches
for expectation gaps, spends research effort on named residuals, freezes the
decision and competing forecasts before outcomes, and joins later consequences
back to the producer and acquisition policy. It does not guarantee profitable
opportunities on each cycle. If no candidate passes the underwriting contract,
cash is the output.

The complete-policy block evaluates the machine as a capital allocator rather
than a collection of isolated ticker forecasts. It freezes a common universe,
SPY benchmark, Treasury cash hurdle, costs, and policy weight vectors. Identical
vectors share one representative. Later settlement reports both full portfolio
excess return and security-selection contribution, so cash timing cannot be
mistaken for stock-selection skill.

Every non-reference weight also carries a point-in-time attribution row. It
binds the weight delta to the candidate digest, public-source receipts,
research question, discovery score, and eligible-law contributions. Settlement
reconciles those deltas to the realized selection difference after cost. The
receipt explains which decision path produced the result; it does not split
causal credit among inputs that always traveled together.

Settlement now lowers each complete policy into the substrate-general
world-model evaluation contract on two paired loss coordinates: negative
after-cost portfolio excess return and negative after-cost security-selection
contribution. Reviews are isolated by exact policy trial family, horizon,
benchmark, score contract, and cost contract. The shared survivor compiler
requires a complete policy-by-block matrix, at least eight independent blocks,
paired permutation tests, and Benjamini–Hochberg correction. A single survivor
creates an immutable `portfolio_policy_review` leaf eligible for paper-policy
review. The receipt cannot alter a position automatically.

Ticker-level closed-book settlement uses a narrower score: target paper weight
times benchmark-relative return, less frozen transaction cost. Raw full-book
excess return remains diagnostic; it is not the primary producer-credit
quantity. This prevents a one-name forecast from receiving the return of an
imaginary fully invested portfolio.

The current 2026-08-11 cycle processed 45 candidates. G, EPAM, RRC, FNK, and OVV
passed the numeric screen; G and EPAM entered through the first holdings-driven
issuer slice. FNK retains its validated issuer-bound dossier and complete
225-position snapshot. No active operator decision earned risk, so the paper
book remains 100% cash. A qualified company still requires research and an
operator-created inactive draft; a qualified fund stops at review and cannot
create an equity draft or a paper weight.

### Fund look-through and comparable substitutes

The fund path now keeps five objects separate:

```text
issuer summary bytes
  -> aggregate valuation, fee, assets, spread, and volume observations
full holdings bytes
  -> point-in-time normalized positions and concentration coordinates
normalized comparable holdings
  -> pairwise issuer overlap + disclosed active share
target fund + existing company evidence
  -> non-dominated issuer-acquisition frontier + bounded SEC hydration
valued watchlist
  -> non-dominated fund-choice frontier and factor-near substitutes
```

The frontier maximizes factor-implied return and earnings-power margin, minimizes
implied growth and expense, and prefers shallower drawdown. Historical residual
alpha is excluded. Factor regressions require exact return-interval alignment
and point-in-time availability, and report Newey-West uncertainty. Current
annualized residual-alpha intervals for IWS (-3.54% to 1.77%), FNK (-4.11% to
4.82%), and EPMV (-13.31% to 4.33%) all include zero, so each receives zero
alpha credit. FNK is on the current frontier; IJJ is dominated by IMCV.
FNK's nearest factor substitutes are IJJ, VBR, IVOV, AVMV, and EPSV. The
frontier still refuses to choose because holdings, liquidity, turnover, and tax
coverage are not compatible across every fund.

At the frozen FNK epoch the parser admitted all 225 disclosed positions. It
computed 0.55% holdings HHI, 8.39% top-ten weight, 13.90% sector HHI, and 25.37%
top-sector weight. The issuer summary supplied a 0.74% fee, roughly $231 million
of assets, a 0.13% median spread, and 3,695 shares of 30-day average volume. The
accepted dossier treats these as implementation constraints around an aggregate
11.8 P/E expectations proxy, rather than as a paper recommendation.

Seven issuer sources now produce full normalized holdings snapshots: FNK,
EPMV, EPSV, IVE, IJJ, IMCV, and IWS. Their 21 pairwise comparisons reveal, for
example, 49.32% disclosed-weight overlap between IMCV and IWS and 38.14%
between FNK and IJJ. The first FNK acquisition transition selected ten issuers
from target weight plus cross-fund reuse, enrolled all ten through one SEC
registry pass, and produced seven new sufficient company-quality reports.
FNK company-quality coverage increased from 1.43% to 7.37% of disclosed
weight; the three incomplete issuers remain explicit metric-repair cases. The
next integrated transition acquired OVV, lifted coverage to 8.16%, compiled a
45-candidate discovery run with five numeric qualifiers, and refreshed the
paper opportunity book in the same action.

The current cross-fund planner removes the single-target bias. It normalizes
provider-decorated US issuer identities, so existing quality reports now count
across IJJ, IMCV, IVE, IWD, and IWS as well as FNK. Eight of the ten priced
programs have some observed company-quality coverage, although none reaches the
50% disclosed-weight comparison threshold. Under a ten-call public-source
budget, the next plan spends one shared SEC registry call and nine Company Facts
calls on AAPL, AMZN, MSFT, XOM, JPM, WMT, PSX, JNJ, and BAC. One issuer call is
credited to every member fund; PSX alone covers four programs. Conditional on
sufficient filing histories, summed covered fund weight rises from 25.46% to
71.57% across the ten programs. The observed post-run result is compiled
separately; this potential is not treated as completed coverage.

The same cycle demonstrates why the evidence boundary matters. Primary-source
research on SIRI exposed a semantic debt-tag error: the earlier compiler had
combined stale current/noncurrent concepts into roughly $2.27B of debt, while
the current filing-bound concepts produce roughly $9.46B and −$9.28B of excess
net cash. After repairing alias selection and rerunning the valuation grammar,
SIRI moved from the earlier qualified leaf to `monitor`: its price-implied
excess return remains about 3.63%, but its debt-corrected earnings-power margin
is −41.2%, below the declared −35% floor. Superseded research can no longer
enter a dossier, while the entity may still win a bounded maintenance refresh.

Recursive strategy enumeration contributes at a different boundary. For a
researched company, it maps source-supported choices and interactions into
global frontier programs and neighborhood-relative peaks. The opportunity book
records whether that representation exists. A strategy result influences a
valuation or position only after a typed, source-bound consequence is lowered
into an economic coordinate. The compiler now emits direction and normalized
effect ranges for four such coordinates, but marks each proposal as requiring
source-bound magnitude calibration. The formal system therefore routes the
next measurement without manufacturing growth or margin assumptions.

## Periodic discovery seam

The controlling public contracts are the
[`GP-254 spec`](../../research_areas/specs/active/substrates/investment/GP-254_jaggedthoughts_autonomous_opportunity_funnel_spec.md)
and
[`GP-254 seam`](../../research_areas/seams/substrates/investment/GP-254_jaggedthoughts_autonomous_opportunity_funnel_seam.md).

Discovery has two populations with different identities:

```text
broad catalog (11,990 current listed identities)
  -> typed scout intent
  -> coarse identity/capitalization/theme filter
  -> enrichment queue
  -> selected equity: SEC facts + price + quality + valuation
  -> selected fund: price + factor exposure + issuer/holdings valuation request
  -> configured deep-discovery population
  -> candidate leaves and research activation
```

The catalog transaction is cheap and broad. Its rows are retrieval-time
identities, classifications, prices, and volume fields. A catalog match is not
an investment candidate. The deep population owns point-in-time fundamentals,
valuation, factor analysis, and later qualitative research. This split lets an
operator ask for a theme or style without fetching thousands of SEC histories
on each cycle.

The workbench now owns a scheduled acquisition transaction:

```text
daily due check
  -> read editable research_jobs/intents.yaml
  -> compile each saved request and scan the complete broad catalog
  -> compile one immutable enrichment cycle
  -> rank marginal research value and diversity under explicit budgets
  -> lease the selected equity and fund jobs
  -> batch-enroll selected identities
  -> refresh core, selected-entity, and active-profile sources
  -> use remaining call budget to maintain unresolved request entities
  -> compile company-quality and fund-factor objects
  -> enumerate every configured equity and fund
  -> compile equity valuation-program envelopes
  -> compile fund aggregate earnings-power / implied-growth proxies
  -> rank equities and funds inside their own potential lanes
  -> interleave lane ranks without averaging unlike return concepts
  -> persist one discovery-run leaf plus one leaf per candidate
  -> emit exact candidate-leaf research requests or typed job blocks
  -> freeze a candidate-leaf coverage-first / disagreement-first Bernoulli assignment
  -> subscribe request leaves into a separate research-agent lease lane
  -> web-research agent writes a typed dossier
  -> kernel validates and submits the dossier
  -> accepted dossier creates a falsifier-bearing material-source subscription
  -> changed SEC / issuer-fundamentals digest creates a source-event leaf
  -> reverse edges compile one dossier-local reassessment request
  -> leased agent writes an evidence-bound thesis delta
```

Saved broad searches live in `research_jobs/intents.yaml`; acquisition budgets,
costs, diversity, retries, and selective source refresh live in
`research_jobs/enrichment_policy.yaml`; deep-analysis cadence and gates live in
`discovery.yaml`. Each cycle binds policy and scout hashes, score components,
selection reasons, budget use, jobs, candidate leaves, and requests. A source
outside the current bounded refresh retains its last point-in-time observation
only while the typed input-age gate admits it; a failed dependency blocks the
candidate. The local web server starts three child services: discovery due
checks, the policy-enabled subscription consumer, and the capital-cycle checker.
On macOS the supported launch agent keeps the owning server alive across login
and process failure; SQLite and immutable artifacts preserve their work across
restart. The same operations are
available through `workspace enrichment-run`, `workspace discovery-service`,
`workspace research-agent`, and `workspace capital-cycle-service`.

The discovery-service heartbeat also projects these existing components as one
`periodic_activation` read-model object. It names the last discovery and
completed research job, the exact next leased job or discovery due time, and a
blocked activation with its reason and retry time. The projection binds the
latest discovery hash and candidate-leaf count, declares the signed-in
subscription transport, and retains paper-only authority. Running
`workspace discovery-service --once` twice leaves the discovery identity,
candidate leaves, and queue counts unchanged when nothing is due.
If the subscription child stops updating beyond two poll intervals, the status
becomes `stale` and exposes `workspace research-agent` as the restart command;
the consumer now catches a failed cycle, records its error, and continues
polling instead of exiting with a stale `checking_queue` heartbeat.

The queue now has an institutional-learning scheduler rather than a fixed
job-type ladder. It prices every already-admissible job against the five-law
committee using the shared query-by-committee primitive, missing cohort blocks,
new entity context, and the job's declared decision transition. Diminishing
returns for repeated entity/action work reduce duplication. A bounded action-class
service bonus and a seven-day starvation guard keep a lower-scoring research class
from disappearing while leaving the learning-leverage proxy primary for fresh jobs.
The proxy is explicitly an upper bound, not observed information gain. The result
changes SQLite claim priority only; it cannot score a security or change a paper
position. The scheduler re-evaluates the current queue each cycle: strategy-control
work may lead when it separates several live law hypotheses, while one dispatch in
four is reserved for the highest-ranked unresolved candidate-dossier job.
Strategy-cohort work has an additional exploration firewall: one eligible
dispatch in five is a law-blind environment probe. Its catalog frame and fixed
priority exclude law support, adoption outcomes, cohort gaps, and acquisition
bonuses. This keeps conjecture-directed work from becoming the only source of
future evidence; the blind lane still has research-priority authority only.

The scheduler can also annotate that same admissible queue with household-mandate
relevance. It joins each research subject through the source-bound sleeve-
implementation frontier, then names the exact sleeve-weight decision classes in
which that sleeve is active and the largest declared planning weight it reaches.
An unbound company or fund stays explicitly unpriced; the job payload cannot invent
its sleeve. This coordinate does not alter queue eligibility or the current order.
It is an upper bound on implementation relevance, not expected alpha, a posterior,
or permission to invest.

Queue priority is evaluated only after lifecycle closure. When the current
candidate is already covered by an accepted monitored dossier, both its initial
research job and any candidate-transport activation job settle as
`covered_by_prior_dossier` before claim. This prevents an obsolete web call from
competing with live candidate or institutional-learning work. Activation-request
identity includes the exact source-epoch digest, so concurrent source refreshes
cannot fork one Golden Store object at the same availability time. The live UI names
paper-watch securities separately from their point-in-time decision epochs, so
several frozen epochs for one ticker do not appear to be several holdings.

An accepted dossier also creates a `research_monitor_subscription`. The current
trigger set deliberately excludes daily prices: company subscriptions watch SEC
Company Facts content, and fund subscriptions watch configured issuer
fundamentals. A changed content digest creates immutable
`public_source_change_event` and `research_reopen_request` leaves. Reverse edges
name the prior dossier and its strategy-mechanism claims, so the subscription
worker reassesses that neighborhood without revisiting unrelated candidates.
Repeated checks of the same receipt are idempotent. Broader news and semantic
cross-entity propagation remain separate extensions.

A fetched receipt can be newer than several dossier subscriptions that began
from different source baselines. The change-event identity therefore hashes
source id, prior content, current content, and receipt. This preserves one
event for equal transitions while preventing different baseline-to-current
changes from colliding under the same immutable leaf identity.

The agentic split has three layers. The kernel owns identity, source bytes,
budgets, leases, bounded search declarations, verification, lineage, authority,
and lifecycle transitions. Numeric production can be offered to several
versioned executors under the
[capability-adaptive execution contract](capability_adaptive_execution.md).
Editable policy owns recurring mandates. The repo-scoped
`$jaggedthoughts-capital-research` skill interprets
open-ended requests, gathers current primary-source strategy and industry
evidence, and submits typed dossiers against exact request and candidate
leaves. The automated consumer invokes that contract through the operator's
Codex or Claude subscription, under a daily dispatch budget and a web-only
capability seal. A new theme does not require a kernel vocabulary change. A
monitor dossier stops at `researched`. A qualified fund whose current candidate,
watchlist, factor, holdings-graph, and either exact dossier or covered prior-dossier
leaves join can become a
cash-only, zero-weight inactive proposal. A qualified equity has its separate
inactive-draft contract. Both paths require exact operator confirmation before
paper activation; neither can route an order.

### Capability-adaptive valuation execution

The first numeric task market is available in the World Models view. One
source-bound implied-growth problem is frozen once and offered to four modes:
the valuation interpreter, direct frontier reasoning, a guarded reusable
program written by the frontier model, and a hybrid requiring both neural paths
to pass and agree. Three unseen counterfactual cases are created after the
model responds, so a hard-coded program cannot earn the authored-program
receipt.

The 2026-08-10 IBM acceptance run passed all four modes. The program passed the
primary case and all three unseen cases with maximum relative residual
`6.79e-16`; direct/program agreement was `1.25e-16`. The baseline remains the
primary route because promotion requires 20 verified attempts across at least
five distinct tasks in the same model/runtime epoch. Every receipt is
analytical-shadow only.

Here, **residual** means the difference between the market value implied by a
candidate growth rate and the target market value in the same DCF equation. On
the IBM task, `6.79e-16` is about `$0.00019` against a `$279.29B` target: a
floating-point consistency check, not return error. **Disagreement** means the
distance between the direct and program-produced growth answers. `1.25e-16`
means they returned the same 7.1129% result to about fifteen decimal places.
Neither number measures forecasting skill.

The accepted broad catalog contains 11,990 identities: 6,730 equities and
5,260 exchange-traded funds. Saved mandates matched 911 mid-cap value companies
and 17 mid-cap value funds before queue bounds. An earlier acquisition cycle
scored 67 deduplicated identities and selected three equities plus two funds
under 21 estimated source calls and 170 research minutes. The finalist cycle
uses a 34-call total ceiling, reserves two calls for unresolved candidate
maintenance, refreshed 34 sources, and selected no new acquisition once that
complete bill was known. Direct issuer valuation adapters now cover eleven
configured funds; BSMC and HWSM remain explicit provider residuals. SARO and
VIAV have accepted dossiers and material source subscriptions. VIAV exercised
the subscribed request-to-primary-source dossier path through Codex in 842
seconds; its frozen screen remained `monitor`.

Research-request identity is epoch-specific. Each discovery rerun supersedes
obsolete queued work, rechecks identity immediately before any provider call,
and emits a new request for each current qualified candidate. Evidence
maintenance instead belongs to the candidate entity: a superseded request can
keep a current `monitor` or `stale_evidence` entity eligible for bounded source
refresh without regaining dossier authority. This split prevented both wasted
agent calls and silent reuse of unscheduled sources in the finalist cycle.

Factor leave-one-out diagnostics use the exact OLS PRESS deleted-residual
identity `e_i / (1 - h_ii)`. It is algebraically equivalent to refitting each
omitted row, but reuses one fit and its leverages; the 1,253-observation
candidate pass now takes a fraction of a second rather than performing 1,253
regressions per candidate.

The acquisition-learning projection now joins each frozen routing score and
estimated job cost to dossier submission, draft creation, paper activation,
and any later benchmark-relative scorecard. It currently sees ten requests,
two submitted dossiers, and zero request-bound settled paper outcomes. Pending
rows are censored. The UI therefore shows research yield while keeping policy
refitting disabled; the default economic gate requires at least 20 settled
pairs plus score and outcome-sign variation before review can begin.

New qualified-request batches also create a prospective research-question comparison.
Within each equity or fund stratum, adjacent acquisition ranks form a pair; a
frozen pre-outcome assignment seed chooses which member receives
`coverage_first` and which receives
`disagreement_first`. Both arms must complete the same typed dossier. The frozen
question changes search order only. Source counts and latency are process
observations; no arm can change until at least 20 matched pairs have later
economic consequences with sign variation. Qualified requests created outside
the randomized enrichment path are labelled `common contract` and excluded.

The question itself is now executable structure rather than a prompt label.
For each frozen candidate, `compile_research_question_frontier` creates typed
equity or fund question atoms, recursively enumerates one- and two-probe ASTs,
and closes a Pareto frontier over declared decision-relevance,
rival-discrimination, coverage, and source-efficiency proxies. The assigned arm
selects and orders one frontier program before any source is opened. That exact
program and its source plan enter the immutable agent request. The grammar's
bounded scope can close; the representation remains open because a fixed atom
library may omit the decisive candidate-specific question. The proxy is not
called expected information gain because no evidence-backed hypothesis
committee yet supplies prediction partitions.

The first activated batch contains three `coverage_first` and three
`disagreement_first` requests: two complete equity pairs plus one unmatched
equity and one unmatched fund residual. All six are evidence-ready and queued
for the signed-in subscription worker. They remain process observations until
dossiers and later economic consequences arrive.

## What would have to be true for a 100× system

The subscription worker removes a manual handoff. That alone is a throughput
improvement. The compounding mechanism depends on a
smaller reusable unit: an evidence-backed mechanism claim joined to the
entities, industries, valuation coordinates, rival mechanisms, future
observations, and decisions it affects.

```text
new filing, price state, issuer disclosure, or industry event
  -> content-addressed evidence claim
  -> affected-identity and mechanism edges
  -> reopen only dependent thesis / strategy / valuation neighborhoods
  -> choose the next discriminating acquisition by expected decision value
  -> submit a new typed artifact
  -> later paper consequence joins back to the acquisition and mechanism
```

Seven beliefs must survive measurement:

1. Public filings, issuer materials, market series, and government data cover
   enough of the target public-market questions that terminal-data omissions do
   not dominate the result.
2. Research value is sufficiently predictable from uncertainty, decision
   sensitivity, reuse, freshness, and cost to beat FIFO and simple rank order.
3. Industry and mechanism evidence transfers across companies and funds without
   erasing entity-specific differences.
4. Most new evidence changes a local dependency neighborhood, so incremental
   recomputation is materially cheaper than redoing every dossier.
5. Choice-system consequences can be lowered into explicit growth, margin,
   reinvestment, duration, capital-intensity, or downside coordinates without
   invented deltas.
6. Typed arithmetic verifiers, point-in-time joins, rival views, and
   source-bound validation catch enough producer errors to make the workflow
   decision-useful.
7. Better research selection eventually improves benchmark-relative paper
   consequences after costs, rather than only producing more polished memos.

The measurement surface is therefore decision-changing evidence per research
hour, duplicate source work avoided, time from event to affected-thesis update,
falsifier resolution rate, qualified-candidate yield, and later after-cost
paper consequences. Until those prospective joins accumulate, “100×” is a
design target rather than a performance claim.

The first exact event path is implemented: changed material-source digest →
entity-bound source event → dossier-local reverse closure → leased reassessment.
Qualified discovery leaves now also enter non-overlapping 21- and 90-day
closed-book probes. Forecast learning keys credit to the exact mechanism bundle
and subject kind; it does not assign credit to one component unless a separately
varied episode identifies that component. Cross-entity reuse becomes a transfer
candidate only after the same bundle settles on more than one entity. The
larger claim still depends on cross-entity mechanism retrieval, typed
strategy-to-valuation deltas, and prospective paper consequences.

Fund aggregate valuation is kept separate from company cash-flow valuation.
Direct issuer adapters currently read published characteristics and exact
retrieved bytes from iShares, Vanguard, Harbor, Avantis, and First Trust. Eleven
of the thirteen configured value funds now have an issuer fundamentals
adapter; BSMC and HWSM remain typed provider-coverage residuals. The standard
signal graph derives earnings yield, book-to-price, and fee-adjusted earnings
yield rather than duplicating those formulas inside the watchlist compiler. A
First Trust adapter now converts the exact FNK full-holdings response into a
point-in-time 225-position projection and typed concentration metrics. Broader
issuer holdings ingestion now normalizes four iShares and two Harbor funds into
the same contract. The holdings graph compiles overlap, disclosed active share,
target-fund company-evidence coverage, and a repeatable acquisition queue.
Holdings-weighted aggregate earnings power, the six missing comparable-fund
snapshots, and account-specific portfolio utility remain the deeper
reconstruction path. Web search may locate a
qualitative source, but it is not a numeric data authority and no Tavily-style
dependency is required.

Valued funds now receive an explicit within-sleeve investment-potential rank.
It combines three evidence families once: gross earnings yield plus
book-to-price; factor return per volatility plus drawdown resilience; and fee
efficiency. Factor-fit coverage remains an admission diagnostic, but the same
return panel cannot earn a second additive vote through fit. Expense ratio is
paid once as implementation cost; fee-adjusted earnings yield and
factor-return-after-fee remain diagnostics or separate challenger programs.
Each result carries a hashed evidence-vote receipt naming these carrier
dependencies. Historical residual alpha receives zero credit. Missing
aggregate valuation leaves the fund unranked.
This score orders underwriting attention; it is neither expected alpha nor an
account-specific allocation utility.
When the same implementation sleeve appears in several watchlists, discovery
recomputes those percentiles over one deduplicated union of fund identities.
Watchlist-local percentile scores are evidence inputs, not comparable final
ranks.

Equity and fund scores remain local to their subject-kind lanes. Discovery and
the opportunity book interleave ordinal lane ranks rather than comparing the
native scores. An admitted learned-law adjustment may reorder candidates only
inside its lane; it cannot turn heterogeneous coordinates into one expected-
return number. The durable subscription queue consumes the resulting global
interleave rank, never the native score, so the agent handoff cannot undo the
category boundary.

Discovery compilation is cross-process coalesced by source-run hash, policy
hash, and compiler version. A second periodic owner reuses the completed
candidate leaves and ranked run for that exact identity instead of repeating
the valuation pass. Compilation also holds the source-refresh membrane, so it
cannot combine a published source head with normalized files still being
replaced by a later refresh.
The discovery transaction suppresses the build's intermediate UI projection
and publishes one projection only after the ranked run and research activations
exist.

Source refresh is transactional at workspace scope. Provider capture,
observation merge, derived signals, evidence-vault receipts, and the latest-run
head finish under one lock, so concurrent services cannot publish source epochs
out of order. Downstream compilers admit only observations available by their
declared cutoff. When the time-admission rule changes, the compiler receives a
new identity and availability epoch rather than rewriting a prior result.

The observation stream has a narrower publication membrane inside that
transaction. A refresh builds the disposable query index against a candidate
stream before replacing the canonical CSV. An interrupted index build therefore
leaves the prior published stream readable. A source pointer binds the exact
published bytes; any append or mutation invalidates the epoch and stops
downstream capital compilation.

The current verified workspace retains 626,641 point-in-time observations and
compiles a 32-candidate, 23-qualified public-fund comparison alongside the
broad-equity potential queue. The Golden Store has 9,518 leaves and 8,019 edges;
append-only SQL triggers plus incremental prefix verification avoid rereading
the full store for every UI projection while preserving lineage and dangling
reference checks.

## Typed metric universe and derivation AST

[`metrics.py`](../../src/ztare/investment/metrics.py) is the canonical registry
for 84 currently supported investment metrics. A metric definition names its
semantic type, unit, temporal type, producer, eligible entity kinds, and
meaning. Examples include:

```text
implied_equity_risk_premium : rate[decimal, instant, market]
equity_beta                 : multiple[window, public_equity]
cost_of_equity              : rate[decimal, assumption, public_equity]
portfolio_earnings_yield    : rate[decimal, instant, public_fund]
implied_growth              : rate[decimal, assumption, equity|fund]
```

The registry does not add another evaluator. Standard arithmetic is compiled
to the existing `SignalDefinition` DAG; valuation assumptions and inverse
problems use the existing `OperatorGrammar` and `Program` interpreter. The
recursive signal AST is simply the acyclic dependency graph of named derived
metrics. A metric argument may name another entity, which lets a market
diagnostic bind a public index yield to its exact macro baseline without
copying either observation. ERP therefore has distinct identities: a cash-flow-implied total-return
premium, an earnings-yield spread, a dividend-yield spread, a committee
assumption, and an input to a valuation program. They cannot silently substitute
for one another.

Temporal compatibility is part of the AST contract. `aligned_subtract`, used
for normalized owner earnings, requires operating cash flow and capital
expenditure to have the same `observed_at` fiscal endpoint. A blocked
recomputation also evicts any older derived row for that signal. The first live
audit rejected nine mixed-period derivations; one rejected case had combined
2025 operating cash flow with 2018 capital expenditure. This is a useful role
for the formal layer: prevent an arithmetically valid expression from becoming
an economically invalid observation.

## Why there are three grammars

The company-strategy, valuation, and position-policy languages have different
jobs.

The company-strategy grammar composes responses:

```text
industry pressure -> sourced response option
combine(response, response) -> choice system
choice system x scenario -> earnings durability, growth, capital efficiency,
                            downside resilience, pressure coverage
```

The valuation grammar derives quantities:

```text
cost_of_equity(risk_free, equity_risk_premium, beta) -> discount_rate
present_value(cash_flow_series, discount_rate, terminal_growth) -> equity_value
earnings_power(owner_earnings, discount_rate, net_cash, shares) -> value_per_share
implied_growth(price, owner_earnings, discount_rate, ...) -> growth
implied_return(price, owner_earnings, forecast_growth, ...) -> return
```

The policy grammar chooses an action:

```text
branch(condition, policy_if_true, policy_if_false) -> policy
policy -> watch | start | add | hold | trim | exit | hedge
```

The strategy compiler owns option combination, compatibility witnesses,
reinforcement/tension effects, and local peaks. The valuation language owns the
numeric contract and reference semantics; current-epoch executors may compete
to produce a verified result. The policy grammar owns contingent position
actions. The metric signal DAG upstream of these grammars owns reproducible
arithmetic derivation. Each has a separate scope and evidence epoch.

## What the formal layer buys

A spreadsheet can calculate every formula above. The grammar becomes useful
through the additional contracts:

- every assumption carries an exact unit and source lineage;
- every program has content identity and can be reproduced;
- bounded enumeration states whether the declared specification space was
  exhausted;
- inverse valuation shows what the price requires rather than only what an
  analyst predicts;
- economically equivalent programs can be compressed into consequence classes;
- the policy state consumes derived valuation coordinates, including
  price-implied excess return;
- later settlement can trace a decision back through its policy, valuation,
  thesis, fingerprint, and evidence.

The output is a bounded expectations frontier: the implied-growth curve under
declared discount specifications, the implied-return curve under declared
growth specifications, and the partition of intrinsic-value programs that do
or do not support the observed price.

Formal derivation does not establish that owner earnings were normalized well,
that the model family contains the governing economics, or that the resulting
position will make money. Those remain evidence and model-coverage questions.

Leanmill is a possible verifier for the stable kernel surface, not a market-data
or thesis oracle. Candidate theorems include type preservation for grammar
programs, bounded-enumeration completeness relative to a declared grammar,
closure idempotence and order invariance, valid domination witnesses, and the
impossibility of crossing paper-authority guards. Formalizing those statements
is useful after the executable contracts stop moving; it cannot prove a revenue
forecast, a normalization judgment, or an alpha claim.

## How strategy reaches valuation

Strategy concepts should enter cash flow through typed mechanism effects. A
claim such as pricing power, customer concentration, switching cost, or scale
economy must identify the cash-flow coordinate it changes:

```text
strategy mechanism
  -> revenue growth, margin, reinvestment rate, incremental return on capital,
     advantage duration, downside state, or capital intensity
  -> owner-earnings path
  -> valuation envelope
  -> position-policy state
```

[`strategy_options.py`](../../src/ztare/investment/strategy_options.py) now
implements the first company-choice lowering. A profile states an industry
boundary and customer need, source-bound pressures, response options,
incompatibilities, scenario effects, and reinforcing or adverse interactions.
The shared JaggedThoughts kernel enumerates every program inside the declared
depth and population bounds. The adapter adds compatibility witnesses,
scenario-worst financial coordinates, industry-pressure coverage, a
single-choice-edit neighborhood, global frontier, local peaks, and a separate
representation audit.

The finite language now has an explicit evidence boundary. Dossier research may
propose typed incompatibility, prerequisite, and numeric resource predicates,
but each predicate must be supported by an exact claim token in an opened primary
source. The frozen frontier request copies those candidates byte-for-byte. The
compiler agent cannot add another predicate from prose or from an older frontier;
only the accepted rows lower to Z3. Z3 proves feasibility inside that authored
model, while the source and representation receipts state why the model may still
be incomplete.

Local search includes add, remove, and equal-cardinality substitution moves. This
matters because a bundle dominated after replacing one option is not a meaningful
local peak. The measurement catalog remains narrower: it emits add-one-option
contrasts, where the changed strategic component is unambiguous enough to freeze
an operating-outcome contract.

The first public-company use is MRVL at the 2026-08-09 research epoch. Current
filings support the existence of five choices around custom compute, photonic
fabric, scale-up switching, communications breadth, and advanced-capacity
reservation. The first tree enumerator produced 215 recursive syntax programs and
180 constraint rejections. The current associative/commutative quotient replaces
those duplicates with 21 canonical feasible option sets: five
singletons, ten pairs, and ten triples would make 25 sets, while the one declared
incompatible pair removes itself and the three triples containing it. Z3 returns
the 21 survivors and an UNSAT-core witness for the forbidden pair. The older 215
count describes syntax trees, not distinct strategies. Eight canonical bundles are
on the global frontier and 13 are single-choice local peaks. `scope_closed=true` records
exhaustion of that authored language. `decision_closed=false` preserves the unresolved calibration
of financial effects, customer-program economics, competitor response, and
option representation. The candidate remains `monitor`; the strategy artifact
does not override its valuation gates.

Direction-only strategy proposals remain descriptive. When an exact move
supplies a numeric operating baseline, hurdle, metric, unit, horizon, event, and
valuation coordinate, the existing valuation grammar prices two worlds: no
incremental effect and hurdle achieved. One web-disabled subscription role sees
the business evidence and hurdle, but not the valuation payoff or security
control, and estimates only the hurdle probability. Deterministic code converts
that probability into a conditional expected-return residual. The failure world
currently returns to the value-quality control and has no separate cost/downside
model; the artifact states this rather than hiding it. The resulting number is a
prospective research challenger, not an effect estimate, sizing instruction, or
expected-realized-return claim.

A stronger bridge still requires transported operating evidence for the same
move and environment. Direction-only mappings remain named conjectures with
falsifiers. The five-model prospective tournament determines whether the direct
bridge adds information beyond zero, momentum, valuation, and value-quality
controls; the operating-hurdle Brier score separately identifies probability
error from valuation-translation error.

The candidate payoff forecast is the broader security-level bridge. It freezes
one admitted candidate, its exact valuation and dossier, one benchmark, and an
authored thesis/rival/residual partition. Each world supplies probability and
horizon-return intervals. Deterministic box-simplex optimization returns an
expected active-return interval, an underperformance-probability interval, and
the probability assignment witnessing each extreme. These are forecast claims
that can be settled later; they do not borrow probability meaning from Arrow
prices or turn the discovery rank into expected return.

Market identity and business-evidence identity advance on different clocks.
A new price observation may mint a new candidate leaf without changing the
filings, research question, or strategy evidence. Valuation and return controls
therefore remain exact to the current candidate leaf, while a strategy frontier
may cross that leaf boundary only when the old and current source requests have
the same hash-verified qualitative-research basis. The workbench exposes this
join explicitly. At the current epoch two exact MRVL owner-earnings-margin
events are measurable, but neither has a current or compatible lineage-bound
frontier, so zero is issuance-ready. Their dossier/frontier repair is ranked by
information yield for the next subscription dispatch window.

## The underwriting challenge

Each thesis is paired with a separate challenge object. It states the
outside-view comparison class and base rate, the sequenced failure path, the
required-return hurdle, the next-best use of capital, the strongest rival view,
and the observation that would separate the views. Its action-condition ID must
point to a policy condition applying the same hurdle to price-implied excess
return.

This converts familiar investment-review questions into fields with downstream
consequences. A base rate cannot disappear from the review packet, an
opportunity-cost hurdle cannot drift away from the policy threshold, and a
rival view must name the observation that would distinguish it.

## Current reference result

The fictional value-quality packet currently demonstrates one complete compile:

- one future-dated observation excluded at the point-in-time boundary;
- 14 source-bound valuation assumptions;
- 17 scenario-coherent valuation results and eight rejected cross-scenario
  combinations;
- 887 bounded recursive position policies;
- two robust frontier behaviors;
- a selected `watch` action under the rival mechanism committee;
- nine decision leaves and sixteen lineage edges in the SQLite golden store;
- a successful hash and lineage verification pass.

The companion portfolio profile consumes compatible entity decisions, performs
exact accept-or-decline enumeration inside a declared population bound, applies
capital, candidate-weight, turnover, and weighted-downside constraints, and
records its Pareto frontier and selection as a tenth golden leaf.

An operator may also declare a sourced factor mandate without copying betas:

```yaml
portfolio:
  exposure_bands:
    - id: value-factor-weight
      factor_id: value
      minimum: 0.00
      maximum: 0.20
```

The workspace compiles current watchlist analyses before the portfolio, chooses
each candidate's latest factor receipt available no later than its decision
epoch, and materializes the complete coefficient vector with watchlist and
analysis hashes. Missing or ambiguous candidate coverage blocks compilation;
it is never replaced by zero or a market-default beta. Explicit `coefficients`
plus `source_refs` remain available for another source-bound linear exposure.

## World-model tournament and backtest analysis

A world model is a versioned mechanism candidate that issues a frozen forecast
for every declared episode. The first tournament supports fundamental,
strategy-transition, statistical, symbolic, and Lagrangian-labelled candidates
through one comparison contract:

```text
candidate mechanism + frozen walk-forward forecasts
  -> identical point-in-time episodes and observable contract
  -> primary, linked, and probabilistic forecast losses
  -> target paper weights and after-cost benchmark-relative returns
  -> paired inference over declared time blocks
  -> false-discovery correction across model/dimension comparisons
  -> conservative survivor committee
```

The substrate-invariant contract lives in
[`src/ztare/worldmodel/evaluation.py`](../../src/ztare/worldmodel/evaluation.py).
It owns candidate/forecast/episode views, closed-matrix chronology, and paired
survivor semantics. The investment adapter owns valuation observables, linked
strategy coordinates, Brier-event definitions, paper weights, transaction
costs, and benchmark-relative scoring. This lets the ARC transition learner,
future scientific models, and investment mechanisms share the comparison
membrane without sharing substrate vocabulary.

Chronology and evaluation authority are separate receipts. A deterministic
historical replay may count as point-in-time backtest evidence only when every
input row proves it was available by the replay cutoff. A historical answer
produced with an LLM remains diagnostic because source timestamps cannot reveal
later market history already present in model parameters. A forecast sealed
before a future episode starts becomes the strongest temporal class only after
its outcome is available and scored. Unknown producers, missing source audits,
and broken seals fail to an unverified or diagnostic class. None of these
receipts authorizes a paper policy or capital, and temporal eligibility alone
does not establish alpha.

The inference block is explicit. Several companies observed in one quarter may
share a block, preventing cross-sectional rows from being counted as independent
market histories. A model family carrying a Newton, symbolic-dynamics, or
Lagrangian label must predict at least one linked observable in addition to the
primary investment target.

The tournament records the full candidate set and declared trial families. Its
survivor method is conservative paired false-discovery-rate nondomination. It
does not claim to implement the formal Hansen–Lunde–Nason model confidence set
or White's Reality Check; those remain method extensions. When the inference
sample is too small, no model is eliminated.

Each model scorecard also reports compounded paper and benchmark returns,
annualized active return and volatility, information ratio, active hit rate,
turnover, and maximum paper-book drawdown at the declared periods-per-year
frequency. These are descriptive backtest diagnostics. Deflated Sharpe,
probability-of-overfitting, continuous-distribution scoring, and a formal model
confidence set remain named extensions.

Historical replay can reject or qualify candidates for a prospective shadow
period. The survivor committee becomes an input to robust policy enumeration;
it never selects or executes a position by itself. This distinction makes a
backtest useful without turning the best retrospective path into capital
authority.

### Closed-book prospective blocks

`ztare.investment.closed_book` supplies the evaluation path for the complete
engine. One action freezes the latest operator decision, quality report,
valuation summary, entity and benchmark prices, 21-day and six-month active
returns, observable contract, and exact source identities. Four producers see
the same episode:

```text
zero-active-return control
six-month active-momentum control
JaggedThoughts valuation + frozen position policy
frontier forecast with web, shell, and repository tools disabled
```

The episode identity is one entity, decision hash, issue date, and horizon. A
repeat action returns the existing episode. The inference block is coarser:
episodes sharing issue date, horizon, and benchmark share one market-history
block, so a cross-section cannot inflate the independent sample count. After
the fixed horizon, cached entity and benchmark prices settle active-return
error, underperformance Brier score, and after-cost paper-book return. The
scoreboard remains descriptive and withholds comparison until at least eight
distinct inference blocks exist. Settled cohorts lower
into the shared `ztare.worldmodel` matrix and conservative paired
false-discovery-rate survivor evaluator; horizon and candidate population define
cohort compatibility.

Tool isolation prevents the agent from retrieving later evidence during the
call. It does not remove history already encoded in model parameters. A
historical frontier-model replay therefore remains diagnostic unless a known
training cutoff or matched clean control identifies temporal leakage. A
prospective block avoids that ambiguity because the outcome does not exist at
issue time; parametric memory is recorded as an unmeasured pre-issue prior.

Deterministic program replay has a stronger historical interpretation. The
agent may author and freeze a typed strategy using only a training partition;
the sealed evaluator then executes that unchanged program over point-in-time
holdout rows without calling an agent and reveals labels only at settlement.
That tests the program and kernel without model-memory leakage. Historical
agent judgment remains a separate diagnostic lane; only post-cutoff or
prospectively issued agent forecasts can supply clean full-engine evidence.

The first live block was frozen on 2026-08-10 for IBM versus SPY. The recurring
capital cycle has since opened qualified-discovery blocks without manual
decision creation. The 2026-08-11 cycle opened 21- and 90-day RRC and OVV
episodes from their exact candidate leaves; each contains no-edge, momentum,
discovery-valuation, and sealed frontier forecasts. Eleven blocks are currently
pending and supply no performance conclusion yet.

These counts establish executable coherence for the fixture. They do not
establish investment performance.

### Prospective market-state blocks

`ztare.investment.market_state_forecast` applies the same temporal discipline
to the market rather than one company. A narrow no-key source transaction
freezes three receipts: current NYU implied ERP and its displayed Treasury
rate, one atomic bounded FRED export containing T10Y3M, DGS3MO, DGS1, DFII10,
and T10YIE, and SPY adjusted prices. A fourth optional public receipt adds
trailing earnings and dividend yields plus a dated forward earnings yield.
Each coordinate retains observation time, first-known time, retrieval time,
methodology, content hash, and freshness ceiling.

The primary expected-return surface back-solves a nominal S&amp;P cash-flow IRR,
subtracts the matched nominal Treasury, and converts the same IRR into a real
return and TIPS-relative premium. Simple spreads remain separately named rivals:
trailing E/P minus TIPS, forward E/P minus the synthetic nominal ten-year, and
dividend yield minus TIPS. They omit different combinations of growth, payout,
buybacks, and terminal value, so none may silently replace the cash-flow ERP.

One snapshot may open separate 90-day and 365-day episodes. Issuance is
idempotent within its declared cadence bucket—weekly for the 90-day lane and
every 30 days for the annual lane—so the institution records current forecasts
without waiting an entire horizon. Every candidate emits the same vector:

```text
SPY adjusted total return + change in the exact 10y–3m spread
  -> one shared continuous paper-probe policy
  -> same-receipt return settlement + independent spread settlement
  -> horizon- and candidate-version-specific world-model cohort
```

The ordinary baseline is the frozen unconditional historical return with no
state change. Policy v5 recomposes the matched valuation Treasury rate plus its
implied ERP into the cash-flow required-return challenger; horizon cash is the
economic comparator and probe baseline only. The frozen v4 runs used horizon
cash plus ERP and remain under their original identity. The required-return
quantity is neither a state price nor a risk-neutral expected return. The
all-zero lane is diagnostic. After a second
compatible snapshot exists, the rejected annual Newton project also runs as a
365-day shadow challenger. It predicts return and term-spread change, preserves
its prior rejection, and cannot enter the authority-eligible survivor set. It
is unavailable at 90 days because the archived project was fit to annual
targets; an annual prediction is not silently scaled into a distinct horizon
model.

SPY is an outcome anchor, not a market-state coordinate. At settlement the
engine reads both issue and target adjusted closes from one later Yahoo
receipt, avoiding an adjustment-base mismatch across retrievals. Raw ERP
change is retained as a diagnostic because a current implied-ERP calculation
shares the future equity-price outcome; it earns no linked-mechanism credit.
Only the separately observed term-spread change supplies that credit.

The v4 forecast policy maps excess forecast return over horizon cash
continuously into a 0–25% shadow probe, reaching the cap at an 8% annualized
excess forecast. The mapping and compiler version are part of run identity, so
changing policy cannot silently reinterpret an old block. A model identity also
binds its family, mechanisms, promotion status, and implementation/result hashes.
Within each horizon the engine chooses one global maximal non-overlapping
episode set for inferential scoring even though it preserves every overlapping
forecast for operational calibration. Repeating an issuance bucket reuses its
run. Missing implementation identity, missing observables, changed identity
bytes, or a broken forecast hash produce an explicit invalid-run row instead of
post-settlement attrition. Once eight independent blocks settle, a rejected
shadow that survives produces a typed successor-research activation; a
dominated shadow produces a retirement activation. Either activation lets an
agent propose a separately identified evidence project and grants no automatic
model mutation or capital authority.

The 2026-08-12 receipt-bound snapshot carries a 4.28% nominal cash-flow ERP,
9.02% implied nominal equity return, 4.07% real ERP over TIPS, and a 3.68%–6.25%
cash-flow-method range. Its separately labelled valuation diagnostics are about
+0.93% for trailing E/P minus TIPS, +0.12% for forward E/P minus the synthetic
nominal ten-year, and −1.39% for dividend yield minus TIPS. The 90-day and
one-year blocks remain pending, so these are valuation coordinates rather than
performance evidence.

The local server's existing capital-cycle thread is the activation owner. It
detects a missing horizon or matured state episode, refreshes only these three
sources without recompiling unrelated company metrics, then issues or settles
the due block. The World Models panel shows this schedule state and provides an
explicit override.

### Probability-current and Lagrangian leaf

The first isolated market-flow adapter estimates a one-dimensional
Fokker--Planck probability current from trailing return states, derives a
nonlinear field response through the shared ZTARE action primitive, and compares
the response with linear current, momentum, mean reversion, unconditional
drift, and zero-return controls. A separate continuity observable tests whether
the current estimate predicts the next rolling density change better than a
zero-change control.

The current retrieval-history diagnostic covers 909 held-out episodes. The
nonlinear response reached 54.9% directional accuracy, but its mean after-cost
directional return was negative. The zero-return model had lower absolute
return error, and the zero-density-change model had lower linked-observable
error. The leaf therefore failed all three control gates and has no signal or
policy role.

That result is preserved. A second successor,
[`jaggedthoughts_probability_current_newton`](../../projects/jaggedthoughts_probability_current_newton/),
uses the same-date distribution of standardized returns across a declared
55-instrument public-price universe. Its compiler emits 201 episodes split into
100 visible, 50 holdout, and 51 farther-tail rows. An upwind finite-volume flux
maps current bin mass into a positive, mass-conserving next density; a
same-information empirical Markov transition is the strongest direct rival.
The deterministic gate now binds the exact candidate, evidence receipt, and
all three partition files by SHA-256. It executes the candidate's stationary
response, verifies the action derivative is zero, checks positive curvature,
and reproduces the predicted density from that response. A visible-fit monotone
odd calibration of the same raw current is an explicit isomorphic rival. Each
episode separately hashes feature-window observations and the later price
observations that create the target density.
Structure-preserving finite-volume work treats positivity and conservation as
defining numerical properties rather than later corrections
([Almeida et al.](https://arxiv.org/abs/1803.10629)).

The weak quartic-action seed is rejected. Across the full panel, density mean
absolute error is 0.0715 for persistence, 0.0728 for the raw probability
current, and 0.0556 for empirical Markov. On both hidden partitions the seed
loses the proper density scores, return error, and after-cost comparison; a
visible-fit blend assigns only 25% weight to it. Subscription Newton search has
a sharp task: change the action-owned response and beat Markov without changing
the evidence, controls, or authority boundary. Six subscription iterations
tested quartic action, entropy tilt, curvature/divergence, sign-block exchange,
activation-conditioned flow, and two-current-moment carriers. None survived.
The fitted action coefficient is now also exposed through the stationary
response ABI. Its selected quartic coefficient is zero, so the candidate
reduces exactly to a linear current with scale 0.0625. A separately fitted
monotone-odd same-information control reproduces every candidate metric. Both
incremental-value gates therefore reject it as a reparameterization, even
though its stationarity and convexity checks pass. Workspace projection rejects
any gate output whose candidate, evidence, or partition hash is stale.
The next density-conditioned successor changes mobility by local probability
mass and uses a saturating stationary response. It beats a separately fitted,
three-mass-bucket monotone-odd control on both hidden partitions: cross-entropy
1.8501 versus 1.8897 on holdout (`p=0.0014`) and 1.6301 versus 1.6820 on the
farther tail (`p=0.0008`). Empirical Markov remains much better at 1.3527 and
1.3575. The project therefore records incremental transition structure but
still rejects the candidate for signal or policy use.
The follow-up tests that mobility as a visible-fit prior for sparse empirical
Markov states. It loses to unsmoothed Markov on both hidden partitions
(cross-entropy 1.3612 versus 1.3527, then 1.3654 versus 1.3575) and also loses
on Brier score. The proposed sparse regime is absent: occupied source states
have at least 59 and 94 prior transitions in the two hidden partitions and
sparse-state probability mass is zero.
That transfer is rejected for this evidence identity.
The temporal-integrity receipt makes that authority boundary executable: all
201 historical feature windows were retrieved after their simulated issue
dates. The universe is also selected from today's workspace. The result is
`historical_reconstruction_unverified`; backtest, alpha, paper-policy, and
capital eligibility are false even if a later transform were to pass its score
screen.

The carrier matters more than the physics vocabulary. A same-date return
density does not track persistent probability particles, so its flux can be a
reparameterized transition operator. A company-state path does retain company
identity and is therefore the strongest current use of directed-flow or action
restrictions; a macro regime path can be a risk monitor, while direct price-flow
prediction remains the weakest use. In every lane the current is derived from
transition data and contributes no information by itself. A Lagrangian earns
research value only when its action excludes an ordinary same-information
Markov or calibrated nonlinear map and changes a future prediction. Symbolic
regression, Kepler search, and Newton search generate candidate restrictions;
they do not upgrade evidence.

For strategy-linked company paths, the useful action is path-space relative
entropy. Start from the empirical Markov probability of a two-quarter path and
tilt it only by strategy features frozen before the path. In simple terms, the
model asks: "what is the smallest defensible change to ordinary company-state
dynamics implied by this particular strategy program?" The strategy-blind
Markov answer remains the default. The tilted answer survives only if it assigns
better probabilities to later paths of companies not used to fit it.

This differs from feeding the observed destination into a Schrödinger bridge:
that would reconstruct an outcome already supplied to the solver. JaggedThoughts
forbids realized endpoint marginals in forecasting. It also waits for the typed
support floor rather than fitting the current two-issuer sample. The acquisition
engine therefore prioritizes exact public adoption dates first; later quarterly
filings create the post-event paths; only then does Newton/MaxCal compete with
the controls.

The current cross-sectional harness also makes its paired-loss sign executable:
`candidate_cross_entropy_minus_empirical_markov_cross_entropy`, with lower
better. The latest restored candidate is worse by `+1.2474` on the 50-episode
holdout and `+0.3217` on the 51-episode farther tail (`p=0.0002` in each). This
repairs an earlier reversed display without changing the rejection. New
receipts declare a paired-delta semantics epoch; older search logs and sealed
bundles without explicit order and direction remain diagnostic history.

The next successor changes the object rather than mutating the rejected scalar
density. `company-state-probability-current` retains company identity across 17
quarterly panels and places each eligible company in a relative 2×2 state:
owner-earnings yield × filing-bounded durable-earnings score. Thirty current-
store companies satisfy the source contract; expanding-window fits score 12
later blocks split four/four/four across visible, holdout, and farther-tail
partitions. The directed transition matrix is decomposed into stationary mass
and antisymmetric current. Its strongest control symmetrizes the same transition
counts and is therefore reversible; any incremental result must come from
direction, not extra information.

Direction has not earned use. On holdout, directed cross-entropy is 0.2543
versus 0.2404 for the reversible control, and directed Brier loss is 0.0928
versus 0.0877. On the farther tail direction improves those means slightly, but
wins only half of cross-entropy blocks and produces no incremental economic
ranking. All predictive and economic gates fail. This rules out the current
coarse state/current carrier while preserving the reusable persistent-entity
panel and transition decomposition. Filing availability is enforced;
historical prices and the universe remain retrieval-time/survivorship exposed.

The grammar itself now has a separate expanding-window audit. Before each of 12
next-quarter blocks, the compiler enumerates the four typed valuation ×
durability cross-partitions, closes the support-valid Pareto frontier using prior
panels only, and selects by granularity, transition selectivity, coverage, and
description efficiency. It selected the 2×2 partition in all 12 blocks. The
directed joint transition loss was 0.4043, versus 0.3957 for independently
factorized valuation and durability transitions and 0.3944 for the reversible
joint control. Directed minus reversible loss was +0.0099 (`p=0.0383`). The
current language therefore has neither cross-axis interaction nor directionality
support. This is a representation rejection; the current-store universe and
later historical-price retrieval prevent a positive alpha claim.

The next company-state leaf changes the forecast object from one transition to a
two-quarter path. It freezes the existing six-state valuation × durability
frontier and 29-company source cohort, then enumerates every intermediate and
terminal state pair. A two-step action combines movement cost, path curvature,
and an antisymmetric circulation component. Its frozen comparison set contains
the action-stripped twin, distance-only, uniform-path, and persistence controls.
All 216 source-state paths normalize exactly. The intermediate contract is due
after September 30, 2026 and the terminal contract after December 31, 2026;
multiclass Brier loss is the common settlement rule. The Golden Store leaf has
no signal or capital authority. This is a deterministic prospective seed, not
an autoresearch winner. A Newton successor must be a new project and evidence
identity.

The first subscription-Newton successor passed its visible search screen but
failed the one-shot historical admission. It improved visible cross-entropy
against reversible Markov (0.862 versus 0.898), then lost to first-order Markov
on holdout (1.583 versus 1.551) and farther tail (1.473 versus 1.411), with one
block win out of three in each. Candidate bytes, subscription provenance, and
the evidence receipt were locked before either withheld partition was opened.
World Models retains that rejection; it is ineligible for prospective freezing,
signals, model-fit credit, and portfolio use.

The successor is a distinct
[`jaggedthoughts_market_state_newton`](../../projects/jaggedthoughts_market_state_newton/)
project. A deterministic compiler freezes a public historical implied-ERP table
into 44 visible annual episodes, six holdout episodes, and four farther-tail
episodes. The state is implied ERP × Treasury term spread; the primary outcome
is next-year equity return and the linked outcome is independently observed
term-spread change. Return-orthogonal ERP innovation remains a diagnostic: the
projection is fitted only on the visible partition, but its target still uses
the future return and therefore earns no linked credit. A candidate module must implement `fit_model`, `I_model`, and
`predict_state_change`. Autoresearch proposes the
form, while `fit_model` calibrates its parameters using only the visible rows.
Its return and linked spread forecast face zero,
historical-mean, linear, interaction, shrunken 3×3 Markov, antisymmetric
transition-current, and monotone-shrinkage rivals on identical rows. Paired
year-level losses, leave-one-year-out wins, influential years, the diagnostic
ERP error, and both cross-coordinate response signs remain inspectable. The current source is a
later historical snapshot, so even a survivor would remain diagnostic until
release-vintage or prospective evidence exists.

The first three-iteration subscription campaign produced no survivor. The
proposals either collapsed under shrinkage, lost to same-information controls,
or omitted the linked transition equations. That campaign exposed two apparatus
defects: the generic fit path bypassed an existing typed N-dimensional TSV
parser, and the project ABI was not forced. The typed fitter is now connected;
the project separates the primary fit matrix from the richer transition matrix;
the hard-gate output names holdout, farther-tail, and cross-coordinate gates;
and the calibrated campaign requires all three executable functions. The seed is now
an explicit coupled quadratic action whose stationary response solves `Kq =
F(x)` for the two state coordinates and a return coordinate.

The follow-up campaign ran entirely through the signed-in Codex subscription
runtime and added visible-only deterministic calibration. It explored coupled,
regime-sensitive, and saturation forms. All were rejected: neither chronological
partition passed its return, linked-spread, or after-cost gate; term-spread change
failed throughout; and monotone shrinkage reproduced the candidate response.
Both cross-coordinate derivatives retained their signs. Only the ERP-to-spread
response is a linked structural gate; the return-derived ERP response supplies
no forecast credit. The current
project result therefore has score 20, passes one structural gate, fails both
economic partitions, and remains `screen_rejected`.

Every workspace build lowers the registered project into a content-addressed
`mechanism_research_result` golden leaf. The leaf binds the evidence receipt,
candidate bytes, gate result, evaluation time, controls, authority, and source
references. It receives `experiment_only` authority and no capital authority.
Only a gate survivor on point-in-time evidence can become promotion-eligible for
a later prospective tournament. This is the intended role of the leaf: search
mechanisms and preserve decisive negatives without promoting a physics label.
The current result hash is
`1aafa7e66c3b80e8139d90dffd9eef5d491f73c72fc9fcb60850a894940ca319`;
its golden leaf is `c7adfd896cebd0e346ab8e6fcbef094c71f27429201962b21652c1aa9b8dd16b`.

## Why the golden store uses SQLite

Canonical artifacts are immutable, typed leaves. SQLite supplies atomic leaf
and edge bundles, uniqueness constraints, foreign keys, and point-in-time
queries. JSONL remains useful for export, replication, and recovery. Graph
views, reports, current heads, and embeddings are rebuildable projections.

Leaf bodies larger than 64 KiB are stored as transparently compressed SQLite
BLOBs. Their identities still hash the uncompressed canonical JSON, readers
accept earlier text rows, and full verification streams rows instead of loading
the graph into memory. The store does not rewrite existing leaves: this limits
future growth without changing append-only history or requiring a migration.

An embedding may retrieve a thesis or precedent. It cannot replace the typed
leaf or become evidence authority. Its receipt binds the model, version, task
type, dimensions, and exact content hash.

## The economic capability ladder

| Level | Capability | Current status |
|---|---|---|
| `I0` | Reproduce a point-in-time valuation and paper decision | Implemented in the reference kernel |
| `I1` | Maintain many comparable entity theses, policies, and model tracks | Broad catalog, typed 58-metric registry, saved typed intents, budgeted autonomous enrichment, no-credential SEC enrollment, direct issuer fund characteristics, seven full-holdings snapshots, cross-fund overlap, holdings-weighted issuer acquisition, leased research jobs, immutable candidate/request/dossier lineage, company-strategy option frontiers and direction-only economic proposals, capability-adaptive valuation execution, qualified-discovery prospective probes, evidence-backed Newton projects, equity/fund ranking, typed funnel, exact bounded assembly, UI, outcome capture, and world-model evaluation implemented |
| `I2` | Improve paper decisions versus a memo, spreadsheet, and fixed rule | Requires a sealed prospective comparison |
| `I3` | Support read-only live portfolio decisions | Requires data adapters, reconciliation, monitoring, and evidence from `I2` |
| `I4` | Receive bounded trade authority | Requires sustained after-cost results, risk controls, and operator approval |
| `I5` | Extend selection into private-company operating guidance | Shared contracts are plausible; intervention and attribution evidence pending |

The system can create value before `I4`: it can reduce duplicated research,
surface inconsistent assumptions, preserve decision memory, and direct
attention to the belief most likely to change an action. A claim that it makes
money requires settled prospective comparisons.

## What must be believed

- Point-in-time evidence can be reconstructed without material survivorship or
  availability leakage.
- The play-specific fingerprint captures distinctions that matter for the
  selected horizon.
- Declared valuation and mechanism families contain useful approximations.
- Position-policy actions retain stable meaning across mechanism candidates.
- Costs, constraints, benchmark, and no-action alternative are measured closely
  enough to score decisions.
- Outcome settlement occurs consistently, including abstentions and overrides.
- The operator uses representation residuals to revise the language rather than
  treating bounded closure as universal coverage.

## Ornamentation and economic kill tests

Simplify or remove the formal valuation layer when it only wraps arithmetic,
permits source-free assumptions, produces no useful equivalence or inverse
valuation, or never changes an evidence request, review calculation, or policy
state.

Reject the stronger capital-engine claim when a prospective paper book fails to
improve after-cost decisions versus the declared simple control. A process
improvement may survive that result, but autonomous capital authority does not.

## Run the reference packet

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.cli investment compile \
  examples/jaggedthoughts/investment/value_quality_play.yaml \
  --output projects/jaggedthoughts_capital/workspace/investment/decisions/example-decision.json \
  --report projects/jaggedthoughts_capital/workspace/investment/decisions/example-decision.md \
  --store projects/jaggedthoughts_capital/workspace/investment/jaggedthoughts-capital.sqlite \
  --summary

PYTHONPATH=src ./venv/bin/python -m ztare.cli investment store \
  --path projects/jaggedthoughts_capital/workspace/investment/jaggedthoughts-capital.sqlite verify

PYTHONPATH=src ./venv/bin/python -m ztare.cli investment portfolio \
  examples/jaggedthoughts/investment/portfolio_assembly.yaml \
  --output projects/jaggedthoughts_capital/workspace/investment/portfolio/example-portfolio.json \
  --store projects/jaggedthoughts_capital/workspace/investment/jaggedthoughts-capital.sqlite \
  --summary

PYTHONPATH=src ./venv/bin/python -m ztare.cli investment tournament \
  examples/jaggedthoughts/investment/world_model_tournament.yaml \
  --output projects/jaggedthoughts_capital/workspace/investment/experiments/example-tournament.json \
  --report projects/jaggedthoughts_capital/workspace/investment/experiments/example-tournament.md \
  --store projects/jaggedthoughts_capital/workspace/investment/jaggedthoughts-capital.sqlite \
  --summary
```

The command emits a paper-authority decision only. Settlement is a separate
command consuming a later outcome artifact.

For the source-consuming workspace, run:

```bash
export PYTHONPATH=src

./venv/bin/python -m ztare.investment.cli workspace init
./venv/bin/python -m ztare.investment.cli workspace refresh
./venv/bin/python -m ztare.investment.cli workspace enrichment-run
./venv/bin/python -m ztare.investment.cli workspace execution-market
./venv/bin/python -m ztare.investment.cli workspace closed-book-open --horizon-days 90
./venv/bin/python -m ztare.investment.cli workspace closed-book-settle
./venv/bin/python -m ztare.investment.cli workspace market-state-cycle --refresh-sources
./venv/bin/python -m ztare.investment.cli workspace capital-cycle --force
./venv/bin/python -m ztare.investment.cli workspace strategy-outcome <outcome.json>
./venv/bin/python -m ztare.investment.cli workspace status
```

The browser surface is available at
`http://127.0.0.1:8080/?workspace=investment&section=Opportunities` after starting
the local workbench server described in the operator guide.

The Opportunities view also exposes a payoff-state authoring queue. The current
queue contains 20 evidence-bound equity proposals. A proposal carries candidate,
valuation-envelope, spot-receipt, and scenario identities; it cannot enter the
state-price solver until future payoffs, an exhaustive scope, and a priced
numeraire are declared.

For repeatable comparison, the valuation grammar can also derive a conditional
ten-year payoff grid from the exact source-bound assumptions it already owns. The
current audit compiles 18 grids: nine admit positive Arrow prices and nine generate
model-residual research. Two company valuations cannot supply positive horizon
payoffs. These grids do not estimate physical probabilities or expected returns.
They identify which declared valuation worlds can reconcile with price and which
part of the model should be challenged next. Four single-revision experiments are
waiting for a strictly later common source cohort.

The public catalog contains 10,647 eligible securities, but current deep analysis
covers 80 and the active scout ingress remains materially mid-cap/value concentrated.
The workbench now reports that concentration directly. Until the diverse acquisition
policy replaces that ingress, fund and equity rankings describe the enrolled research
population rather than the full public universe.

The replacement default equity ingress selects across independently capped sourced
market-cap, country, and sector coordinates, reserves explicit unknown-cell capacity,
and excludes already enrolled or current identities. The recurring policy runs that
equity sampler beside the broad-fund cell sampler; narrow operator-authored scouts
remain side searches. The breadth receipt separately reports the declared periodic
policy, the modes and coordinates observed in the latest completed cycle, and the
cumulative-enrolled deep-screen boundary. A newly edited broad policy therefore
cannot make an older narrow cycle appear broad.
The broad-fund compiler separately finds 4,649 eligible funds and lowers the
catalog into exact asset-class × region × size × style × factor cells. Its
comparison plan runs inside the recurring discovery service: each source epoch
recompiles the residual, skips completed cells, reserves the existing
enrichment budget, and uses the shared leased queue. The latest live compile
observes 188 cells; 129 contain at least two funds, four are comparison-ready,
125 remain residual, and 59 are singletons. The latest public-source cycle
archived HSCZ and SCZ, while DMXF/EFA became the newly completed comparison
cell. The next selected cells are SCZ/FDTS and EEMS/FEMS. Narrow saved scouts
remain side searches, and this acquisition lane has no position authority.

Qualified equities can compile into exact evidence-bound paper proposals. They
begin as cash-only, zero-weight, operator-inactive objects. At the current source
epoch RRC and OVV clear the exact dossier and activation-evidence join; G and
EPAM await source-delta reassessment and ACM awaits its first dossier.

The operator's standing paper-book policy now removes a needless pause after
that join. Each capital cycle revalidates the current discovery hash, proposal
audit hash, exact proposal bytes, activation blockers, and zero target weight.
It may then enroll at most four current proposals as zero-weight paper watches.
The receipt records the proposal and policy actor and grants no position,
portfolio, brokerage, or order authority. Enrollment is idempotent by subject ×
candidate leaf × dossier leaf, so recompiling a derived fingerprint does not
create a second active watch over the same evidence epoch. Research
agents author the source-bound dossier and proposal; only the deterministic
compiler can perform this lifecycle transition. The policy has enrolled RRC and
OVV as zero-weight watches; a replay sees both as already enrolled. The paper
book remains 100% cash because neither watch has passed position admission.

The fund path completed that join at a prior evidence epoch. FNK and EFV both
retain primary-source reviews, while the current 2026-08-13 audit admits neither:
each has one exact blocker, `research_coverage:reassessment_required`, because a
monitored issuer source changed. The subscription reassessment worker now records
the source-delta result, recomputes candidate-bound coverage, and immediately
recompiles the inactive fund audit. Accepted, non-invalidating reassessments may
reuse the qualitative review; current factor, valuation, implementation, and
holdings evidence remain candidate-local. A changed watchlist diagnostic graph does
not stale a fund candidate when its factor analysis, valuation, fund evidence, and
screen identity remain unchanged. The Portfolio view
also rejects assemblies owned by the reference fixture, so the current operator book
is empty instead of displaying the fictional ALPHA position.

The fund-to-learning transition no longer waits for a portfolio admission. All
16 configured program identities are preserved in a hashed tournament input.
Ten pass the shared-information core: six US and four developed-ex-US. That
opens four paper-shadow ranking tickets against the common prospective price
window. Zero programs currently pass the 50% disclosed-holdings company-quality
coverage rule, so the look-through durability ticket does not open. Zero carry
the complete tax/currency bundle, so this transition supplies comparative
evidence only; it does not choose a brokerage allocation.

The next look-through transition is also explicit in the operating view. Its
selected issuer rows, fund memberships, observed-versus-potential coverage,
shared-registry and Company Facts call count, metric-repair residuals, unsupported
public-source identities, and budget-deferred issuers are visible before a call.
Selection solves a binary minimum-cover program around the activation boundary:
minimize issuer calls subject to taking at least two funds in one sleeve across
the 50% rule, then maximize cross-fund weight among minimum-call solutions. The
current certificate uses HiGHS through the existing SciPy dependency and reports
the optimality gap; Z3 remains responsible for logical admissibility and
portfolio/strategy counterexamples. This prevents a broad-coverage number from
looking productive while every individual comparison remains blocked.
The current holdings graph projects IWD and IVE as the first reachable pair:
60 issuer calls over seven daily batches, 67 total calls including each batch's
shared registry request. The solver found a zero-gap optimum, so the earlier
greedy projection was already minimum-call rather than wasteful. That is a
conditional acquisition path—failed filing
coverage causes the next observed plan to recompile—rather than a promise that
either fund will pass after seven days.
The discovery service now owns the recurring transition: it uses the discovery
cadence, the enrichment policy's ten-call ceiling, the exact plan hash, and the
existing public-equity enrollment, source-consumption, company-quality, and
discovery owners. A completed receipt delays the next batch until the cadence is
due; an empty marginal queue or unavailable budget stops without a source call.
Likewise, a ready broad-fund peer batch waits for that due epoch. The five-minute
service poll reports readiness but cannot by itself launch the source-heavy
compiler.
The capital-cycle service observes the resulting evidence on its own cadence.

That 16-fund set is a value-oriented challenger cohort, not the allocation
universe. The household basis separately retains broad public proxies for cash,
US equity, international equity, USD bonds, and US inflation-linked bonds. A
value-fund result may replace a same-sleeve implementation only after the
prospective comparison earns that transition; it cannot collapse the broad
multi-sleeve baseline into a mid-cap/value portfolio.

The prospective portfolio-policy family now follows the same identity split.
Its weight-bearing universe is the public-equity satellite; public funds enter
only as within-sleeve ranking tickets. A `fully_gated_equal_weight` challenger
appears only when at least two current equity proposals pass position-admission
gates. Policy v3 also freezes the exact adjusted-price observation tuples and a
25%-diagonally-shrunk covariance matrix, then solves one long-only, capped
minimum-variance control without using a return forecast. On the current six
qualified equities it uses 756 aligned returns and estimates 10.22% annualized
satellite volatility, versus 11.27% for equal weight. The prior v2 block had no
entry binding, so v3 superseded it; a bound block would remain immutable.

The covariance control is diagnostic under the current endpoint-return score
contract. It cannot be recommended until prospective settlement also scores
realized volatility, maximum drawdown, and turnover. Neither policy family
supplies household sleeve weights. Those weights belong to the private mandate
path, whose public basis already supports covariance,
scenario-robust goal simulation, exhaustive constrained enumeration, risk
contributions, and Pareto closure once the missing household inputs are bound.

`HouseholdPaperPolicyPath` is the small adapter that makes this sequence legible
as one policy path. It binds the current public-basis, sleeve, fund-comparison,
patient-capital, portfolio-assembly, state-price, and prospective-tournament
identities into one read-only projection. Public evidence gaps and private
household/current-book inputs are separate lists. In the current workspace the
public basis is ready, SPY has 12 US-equity challengers, VXUS has four
international-equity challengers, the declared patient-owner rule requires a
3% after-cost replacement edge, and one complete-policy experiment is pending.
That pending experiment compares research-security allocations; it is not yet a
household-mandate policy. The private planning scenario is now computable, but
no operator-purpose mandate or current account implementation is bound, so no
household paper weight or replacement is selected.

The scenario can nevertheless compile a decision-shaped paper menu. It keeps
the selected sleeve weights fixed, implements them first with the declared
broad proxies, then compiles distinct admitted-security challengers under the
same sleeve and position caps. Existing portfolio-policy rules supply relative
equity weights; discovery rank only explains research priority. Ranked
securities and funds that have not earned instrument admission appear in an
abstention ledger with zero weight. Each rival carries percentages and amounts
over scenario investable wealth, while cash reserve and debt-paydown comparisons
remain visible beside the portfolio. This shows what current evidence permits
under chosen assumptions while withholding operator-policy and execution
authority. The Portfolio screen now renders this contract directly after every
scenario run: exact positions and amounts first, then debt rivals, then the
ranked zero-weight abstention ledger.

The investor brief presents the same separation in one place. Its planning book
maps positive sleeve weights to the declared broad proxies; its automated shadow
book lists every frozen prospective portfolio method, weight, horizon, and
learning state; its operator book alone owns adopted paper weights. The first two
objects always deny recommendation, paper-policy, brokerage, and capital
authority. This permits the workbench to answer both “what do the displayed
assumptions imply?” and “what is the engine currently testing?” without implying
that either answer is the operator's portfolio.

The fund handoff now carries a hashed
`jaggedthoughts-portfolio-evidence-acquisition-contract-v1`. It is compiled from
the current fund programs and unassigned equities, rather than from a model's
suggested allocation. Each missing field names its affected subjects and
programs, acquisition owner, activation point, and adapter status. Existing
periodic source refresh and fund look-through acquisition are machine-fillable;
tax/currency completion and source-bound company-to-sleeve identity remain
explicit adapter gaps. The mandate and current book stay operator-private. The
same contract reports the covariance, factor, fee, and liquidity evidence the
kernel can already consume, while giving unsupported residual alpha zero
credit. Until an admitted program has complete public evidence and the private
inputs are bound, the handoff remains blocked and emits no portfolio weights.

Research capacity has its own prospective shadow tournament. Each signed
learning schedule freezes the work chosen by current priority, FIFO, decision
proximity, information value per dispatch cost, and—when the exact mandate and
implementation joins exist—mandate decision relevance per cost without changing
the queue.
Later source-bound evidence and downstream decision receipts settle each arm;
missing work remains censored. A scheduler policy can become reviewable only
after eight independent schedule blocks, positive decision impact per cost,
paired inference, and Holm family-wise correction. The current block has 26
eligible jobs, four distinct one-job selections, and zero settled blocks, so it
authorizes no scheduler change.

Decision impact is narrower than artifact completion or the presence of a
decision identifier. A positive `ResearchDecisionImpactReceipt` binds one work
item selected in the frozen research-budget block, the exact later evidence
artifact and digest, a pre-freeze semantic decision snapshot, a later snapshot
on the same decision surface, and the evidence-consumption edge between them.
The decision grammar includes selected identities, weights, disposition, next
transition, and blockers while excluding administrative timestamps from the
value hash. Different wrapper artifacts with the same typed decision therefore
earn research yield but zero decision impact. This prevents a scheduler policy
from winning because its jobs happened to mention downstream decisions.

The loop is automatic for future research blocks. At freeze time the engine
captures the candidate's exact zero-weight paper-watch proposal. After the
dossier settles, it accepts a post-research comparison only when that proposal
names the exact dossier digest. The signed before-state, evidence-consumption
edge, and semantic after-state are then verified together. No decision change
means zero impact credit, and older jobs are not rewritten to manufacture a
history. This makes “which research should we fund next?” learnable without
pretending that the research caused a later market return.

Every completed public-source ingestion now enters a point-in-time evidence
vault. The vault verifies the source-run and receipt hashes, preserves the raw
source identity, writes a content-addressed observation set per source, and
records occurrence, availability, retrieval, and ingestion epochs. The latest
capture publishes its own source and observation counts in the workbench;
earlier captures remain separately addressable instead of being silently merged
into the current information set. An as-of reconstruction verifies every
manifest edge and blob hash. This makes
future sealed replay auditable. It does not control a language model's latent
knowledge, repair older retrieval-time histories, or grant policy authority.
The first source snapshot can be a full-set base. Later snapshots bind that
immutable parent and store only observation upserts and latest-only tombstones.
Replay applies the chain oldest to newest, while a disposable membership index
merely avoids diffing the cumulative archive on each refresh. The index is
rebuilt from GoldenStore leaves on any head mismatch. This keeps point-in-time
identity while making future disk growth proportional to changed evidence; old
full blobs remain readable and are not deleted automatically.
Recent work on
[temporal leakage in LLM backtesting](https://arxiv.org/abs/2608.02985)
argues that a passive retrospective test cannot fully separate model recency
knowledge from leakage and forecasting skill. Historical replay therefore gives
evidence credit to deterministic or explicitly bounded executors; a subscription
model earns transferable credit only on future windows.
Every newly opened closed-book packet resolves the latest pre-issue manifest
that contains its exact price and filing source IDs, includes the content-hashed
reference in the packet, and links the forecast leaf to that manifest. A packet
without compatible coverage stays explicitly unarchived.

The archived accounting lane is executable without network access or provider
credentials:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  --path projects/jaggedthoughts_capital/workspace/investment \
  archived-accounting-replay \
  --output projects/jaggedthoughts_capital/workspace/investment/experiments/runs/archived_accounting_replay/latest.json
```

It reconstructs and verifies the selected content-addressed observation blobs,
filters every forecast input by SEC filing date, scores a fixed margin-persistence
forecast against the next filing, and retains the broader durability-versus-
persistence tournament. `point-in-time-replay --profile …` is the stricter
market-return lane: both issue and outcome source snapshots must already exist
under system-clock capture, so the current same-day archive cannot be used to
manufacture older price episodes.

Broad ETF acquisition rotates over the complete typed catalog surface rather
than the bounded scout sample. Exact asset-class × region × size × style ×
factor cells are completed only when two funds have comparison-ready public
evidence. Completed cells are skipped, future-dated watchlists are ignored, and
the next residual cells are selected by fillable information per bounded source
job. Live coverage and the next selected fund pairs appear in Opportunities;
singleton cells and unsupported adapters stay explicit.

The strategy-learning cycle also compiles the phenotype-projection frontier
into typed law programs. It freezes law selection before outcomes, collapses
observationally equivalent programs, records logical subsumption, and binds
environment-specific difference-in-differences effects only when metric, unit,
environment, cohort, holdout, power, multiplicity, transfer, and moderator
contracts agree. The current six programs are all blocked: none has the four
treated units, four bounded controls, two transfer environments, post-boundary
outcomes, power, or multiplicity evidence required for policy review. Future
counterexamples produce forward-only CEGAR refinements rather than rewriting a
failed law.

Subscription research capacity is now admitted in the same SQLite transaction
that claims a queued job. Its identity is owner × subscription runtime × UTC
day, and every dispatch path reconciles against that ledger. This removes the
race in which concurrent workers could each observe spare capacity and exceed
the shared daily budget.

## Broad potential screen and research allocation

The workbench keeps four orderings separate:

| Ordering | Question answered | Forbidden interpretation |
|---|---|---|
| Acquisition priority | Which missing public inputs should be hydrated under the source budget? | Investment merit |
| Investment potential | Which comparable companies or same-sleeve funds deserve underwriting first? | Cross-kind expected return |
| Research priority | Which surviving evidence residual should the bounded subscription queue resolve next? | Position size or trade signal |
| Portfolio utility | Which fully underwritten exposure fits the account after risk, correlation, liquidity, tax, and horizon constraints? | A restatement of research rank |

The daily broad-equity path begins with a retrieval-time SEC XBRL-frame pass.
It joins the public catalog to current annual accounting facts and computes
within-sector percentiles for cheapness, earnings power, cash/accrual quality,
and balance-sheet risk. Three fixed acquisition proxies rank the same complete
population: value, quality/resilience, and their equal-weight balance. Their
ordinal leaders are interleaved and deduplicated; raw scores from different
proxies are never averaged across programs. Only fully comparable non-financial
companies that pass the declared market-cap and volume floors enter this order.
These are one-frame acquisition proxies, not durability or expected-return
claims. Duplicate share classes, period-misaligned facts, financial business
models, and thin securities are typed exclusions.

Only the top-decile potential residuals enter country × sector × size diversity
closure. Their SEC potential rank and component witness flow into the hydration
candidate and enrichment cycle; a generic coverage or liquidity score cannot
replace them. If a prior hydration was interrupted, the bounded worker resumes
eligible queued jobs in current SEC-potential order, while still respecting
attempt, source-call, research-minute, kind, and sector budgets. One typed
interruption recovery is allowed for a current-potential job, long source/build
transactions renew their leases, and queued identities absent from the current
potential surface are superseded without a provider call. The durable queued
priority is rebased to that current potential rank too, so a generic queue
reader cannot revive an older acquisition-convenience order. Existing enrollment
therefore cannot strand a candidate or revive an obsolete screen epoch.
Fund-source repair registers missing adapters but does not refresh every known
fund; only new, selected, maintenance-due, or baseline sources consume the
current acquisition budget.

Automatic ingress now uses the broad SEC potential screen for equities and the
sleeve-ranked broad-fund compiler for equity ETFs. Natural-language catalog
scouts remain available for an explicit cold start, but they do not participate
in the scheduled loop once a typed potential surface exists. Newly created and
resumed hydration jobs are merged and sorted by the same current potential rank
before any leases are claimed.

The mature discovery rank is computed after hydration. Equities and funds rank
inside separate potential lanes; funds additionally rank only against their
declared implementation sleeve. The compiler preserves an all-candidate
`potential_rank` for audit and prospective rank-program evaluation. After the
final screen status is known, it separately assigns consecutive
`research_rank` values only to qualified survivors, using the same deterministic
cross-lane interleave. Monitor and blocked rows retain their measurements and
potential rank but receive no survivor rank, so evidence repair cannot consume
a better queue position than a qualified opportunity. Durable subscription jobs
bind both identities and route by `research_rank`. Raw acquisition and native
potential scores do not regain control at the queue boundary. The shared
subscription budget permits at most three consecutive non-candidate claims
while a claimable candidate waits; the next claim is restricted to the
highest-ranked qualified survivor.

The live current-lineage epoch is
`discovery-20260814154535-7cdb502d` (`3a1be86b…8427`): 176 declared identities
were screened and 100 were published. The signed pre-truncation input contains
46 eligible equities, six eligible international-equity funds, 12 eligible US-
equity funds, and 14 unbound funds that remain deferred; 12 candidates passed
the current screen thresholds. Ten fund
rows retained from an older watchlist remain visible as
`blocked_watchlist_lineage`; they cannot enter the rank contest, research queue,
or proposal path until a current watchlist leaf exists. Complete equities now
retain three doctrine-local ranks over two orthogonal economic families:
accounting quality only, valuation/expectations only, and a 50/50 balanced arm.
The candidate order interleaves the best ordinal doctrine ranks and preserves
their disagreement. Funds combine valuation (50%), factor return and risk (30%),
implementation cost (10%), and factor fit (10%) inside their implementation
sleeve. These weights route research attention; they are not expected alpha or
portfolio weights. The current qualified-survivor research order is ZD, EFV,
BKNG, HRMY, LZ, EPAM, G, FNK, DBX, OVV, ACM, and FDTS. Their all-candidate and
doctrine-local ranks remain visible; BKNG leads the expectations view, while
EPAM is the first qualified survivor led by the quality view.

The next learning step is paired. Coordinate-equal v4, family-weighted v5,
quality-only v1, expectations-only v1, and quality/expectations-balanced v1
must be frozen on the same pre-truncation equity bytes and settled on the same
later price window. Fund lanes continue to compare only the first two programs.
Historical replays can debug the programs. Only repeated prospective,
overlap-aware settlements can support a rank-policy review, and that review
cannot change capital policy by itself. Reviews are partitioned by exact
program-family identity, entity kind, and horizon, so an older two-program
settlement cannot be pooled into the five-program contest.

Compiler v9 mechanizes that comparison and the separate survivor queue rank.
Each discovery run embeds a signed
rank-program input over the complete pre-top-N population. Eligibility ignores
rank and all thresholds on ranked coordinates: it uses evidence compatibility
and rank-component completeness only. The v3 eligibility policy additionally
requires an exact current watchlist leaf for every fund. Threshold pass remains
an observed label, not an admission rule. Both programs receive candidate
hashes that bind those exact bytes: v4 weights coordinates equally, while v5
weights semantic families. Equity and each fund implementation sleeve remain
separate; thin sleeves are explicitly deferred. Later returns score rank
calibration, top-choice regret, and pairwise ordering, with eight independent
overlap blocks required before an operator review is possible.

Allocation readiness consumes that signed v3 admission decision directly. It
does not re-derive eligibility from a looser underwriting proxy. The current
projection therefore keeps the 46 equity-eligible rows, 18 same-sleeve fund-
eligible rows, 14 deferred unbound funds, and 12 qualified survivors distinct,
and exposes the rank-input digest that binds the distinction.

The rank contest covers every evidence- and component-complete row, including
rows that fail the current screen thresholds. That prevents the tournament from
testing only preselected winners. Fund valuation rank uses gross earnings yield
and book-to-price once each; earnings-power margin and net earnings yield remain
visible but receive no duplicate vote. US funds compare with SPY and
international funds with VXUS.

Investment returns use adjusted close. Spot close still prices the valuation
grammar, while adjusted close owns beta, factor exposure, drawdown, and later
rank outcomes. The public Yahoo response is cached once and projected into both
typed series. The primary rank estimand is a 365-day, cost-adjusted return;
the engine now seals a separate 30-day diagnostic over the same candidate and
program identities. Diagnostic results cannot be pooled into the primary
review, recommend a program, or change portfolio policy.

The current diagnostic is `rank-program-ff9e3a607d949a60e4c2`, scheduled to
end on `2026-09-13T15:50:03Z`. The primary block is
`rank-program-df48850af874070a5786`, scheduled to end on
`2027-08-14T15:50:03Z`. Both bind program family
`bb1962ca…fb6`; the live status reports four bound lane windows and eight that
still await their first common post-seal adjusted-price observation. The next
activation is therefore `bind_next_postseal_common_price`; elapsed calendar
time alone cannot start or settle a return window.

Existing verified Yahoo cache bodies can also be replayed through that parser.
The replay preserves the original source-availability time, verifies both the
source-receipt head and raw-content digest, adds only missing adjusted-price
identities, and emits a typed projection receipt. The current replay added
153,771 observations across 157 verified caches with zero provider calls; 14
unverifiable cache heads remain visible residuals. Repeating the replay added
zero rows.

The active sealed potential-rank tournament covers 46 equities, six international
equity funds, and 12 US equity funds. The complete international input contains
16 funds; ten fail the current v3 admission checks. Its earlier seven-candidate block was
superseded before any entry bound because the verified cache replay strictly
expanded coverage. This escape hatch ends at entry: afterward the frozen block
must settle. Its primary observation window is 365 days, so the current status
is pending evidence rather than support for the weighting policy.

Evidence revocation is append-only. A legacy ZD dossier declared source-access
and generation times after its provider result had already materialized. A
typed quarantine leaf now makes that dossier inadmissible to coverage,
strategy frontiers, proposals, and active paper-watch projection without
rewriting history. Replacement public research is routed from the current
ranked candidate and must pass the ordinary kernel admission checks.

Revocation follows declared research derivations as well. Activation research
cannot reuse a quarantined parent, strategy synthesis cannot compile it, and a
derived dossier carries an explicit parent edge. Queue requests remain
immutable, but compatible successors route by the latest frozen candidate rank.
Changed-source reassessment is maintenance, not a newly discovered opportunity.

First-pass web jobs, candidate-bound activation web jobs, and dossier-bound
company strategy-frontier jobs share that protected lane.
Before every claim the kernel retires superseded candidate epochs, so an old
leaf cannot spend a subscription unit ahead of its current successor. A company
strategy-frontier job retains the candidate's current ordinal routing priority
and requires the strategy-synthesis capability at lease time. It is labelled
separately because it synthesizes the admitted dossier without opening another
web search. Dossier admission closes the leased
provider job before downstream queue, proposal, and UI projection refreshes.
The frontier consumer repeats exact candidate-leaf and hash currentness before
opening the dossier. A fresh priority cannot rehabilitate an older request;
stale frontiers settle without a provider call. Queue startup also restores
legacy capability columns from their typed payloads before leasing.
The other dispatches remain available to globally ranked strategy-law,
reassessment, and outcome work. Subscription web research is limited
to named residuals such as multi-period durability, debt/dilution,
market-implied growth, and strategy evidence. A language result cannot add a
company to the potential set or change capital authority.

Candidate web work is claimable only after its exact deterministic parent is
`done/evidence_ready`. A queued request whose parent is still hydrating carries
an unavailable capability and consumes neither a subscription dispatch nor an
attempt. Dossier submission repeats the parent check before writing golden
evidence or mechanism leaves, so queue readiness and durable research state
cannot diverge across that handoff.

Queue repair is free maintenance. The kernel reconciles stale candidate ranks,
supersedes old routing envelopes, and publishes current queue state before it
checks the daily subscription limit. Once the limit is reached, those repairs
continue while every new provider invocation remains blocked.

### Potential rank and the Goldilocks boundary

The screen answers one narrow question: where should scarce underwriting time
go next? Company potential is computed against comparable companies from
point-in-time public measurements. Fund potential is computed only within a
declared implementation sleeve. The two scores are never treated as one return
forecast. Equities retain named quality-only, expectations-only, and balanced
ranks on the same complete population; the best ordinal ranks are interleaved
without blending doctrine-native scores. Their ordinal lane ranks can share
research capacity, while account-specific portfolio utility remains a later
calculation.

This creates a deliberate split. The kernel scans broadly and cheaply, checks
units, timestamps, completeness, and exact candidate lineage, and emits named
unknowns. Subscription research opens primary public sources only for the
highest-priority qualified survivor whose unresolved question can alter the
underwriting packet. The model may validate or contradict evidence, propose a
rival thesis, enumerate company choices, or force deterministic recomputation;
it cannot silently promote a row into the screen, edit a numeric rank, or
allocate capital. A dossier can therefore admit, quarantine, or reopen a frozen
candidate thesis. Only later sealed tournament outcomes can justify reviewing
the scoring policy.

The acquisition cut spends its known-identity capacity on potential-ranked
companies first, subject to country, sector, and size-sector caps. A separate,
explicit quota may sample companies whose classification is still unknown; it
cannot displace a higher-potential known company from the exploitation budget.
Presentation truncation preserves every qualified survivor before monitor and
blocked rows. The shared scheduler publishes a lane rank and a separate global
service position: cadence arbitrates which lane runs, while potential order
continues to own order inside the candidate lane.

Candidate research has one active primary-work identity per candidate leaf.
Targeted activation research supersedes a generic dossier request for the same
leaf, and equivalent activation requests coalesce on source-content hashes even
when retrieval timestamps or receipt hashes change. Full receipts remain in the
audit snapshot. This prevents administrative refreshes and duplicate prompts
from consuming the bounded subscription budget.

Fund rows need one exact watchlist leaf from the current source build. Cached
rows without it remain visible as historical context but are blocked from the
current rank contest and proposal path. Reviews follow the same rule: a dossier
is labelled current only when its candidate hash matches the displayed
candidate. A source monitor that has never observed a baseline requests fresh
research rather than waiting for a comparison it cannot perform.

Prospective portfolio and rank evidence uses adjusted-price total-return
proxies, a 365-day primary horizon, and costs once. Shorter windows are useful
diagnostics but cannot recommend a policy. This keeps a persuasive present-day
score from silently becoming an investment rule before its frozen contest has
settled.

The forced 2026-08-13 scheduled pass joined 5,375 of 5,386 catalog common
equities to SEC CIKs, ranked 1,329 comparable operating companies, retained 739
after current investability floors, emitted 74 high-potential residuals, and
selected nine non-current diversity-closed acquisition candidates. The same
cycle screened 4,642 funds and retained 48 broad fund candidates. This score
prioritizes underwriting; it is not an expected-return estimate. All frame
facts are usable only from their recorded retrieval time because the bulk
response does not supply a filing-availability history.

The 2026-08-14 post-repair pass screened 5,385 catalog common equities, matched
5,373 to SEC identities, ranked 1,330 fully comparable companies, retained 543
after investability floors, and emitted 55 high-potential residuals. Diversity
closure selected the next bounded acquisition set; the public-data worker
subsequently hydrated LZ and BKNG without a subscription-model call. The current
deep discovery retains 12 qualified survivors in consecutive research order:
ZD, EFV, BKNG, LZ, HRMY, EPAM, FNK, G, DBX, OVV, ACM, and FDTS.

Fund breadth and fund ranking have different populations. The broad catalog
can identify 4,642 eligible funds. Deep equity-ETF analysis now has two policy
identities: a neutral broad-comparison profile and a value-specific challenger
cohort. Broad acquisitions no longer inherit the positive-value-exposure gate.
Only 8 of 129 comparable ETF
cells currently have two comparison-ready funds; 121 remain incomplete and 59
are singletons. A broad-scout or acquisition rank therefore cannot be presented
as fund investment potential. Missing aggregate valuation leaves a deep fund
unranked, and no within-sleeve result supplies cross-sleeve portfolio weights.
Non-equity funds remain acquisition residuals until their own cash-flow and risk
metric grammars exist.

## Current-data publication and the Goldilocks handoff

`data/observations.csv` is the append/merge history. A disposable SQLite index
serves exact entity, metric, and point-in-time reads; deleting it loses no
evidence because it can be rebuilt from the CSV. The current-value boundary is
one content-bound `data/latest_source_epoch.json` pointer published only after
the source run, current projection, receipt heads, evidence capture, and query
index complete. It binds those artifacts plus the source manifest and typed
derivation registry. A capital cycle captures that epoch and checks it again
before publishing, so a concurrent refresh cannot produce a mixed-vintage book.

The same read model carries one backend-owned default allocation scenario and
its mandate frontier. Headless consumers and the Portfolio screen therefore
start from identical typed inputs and decision classes. Editing a control
creates a new non-authoritative scenario; it does not silently change the
operator policy or the persisted finite-design frontier.

Instrument admission is a capital-cycle publication, not a view-time
calculation. The read model reuses the last hash-verified admission head; only
the next capital cycle may reprice covariance, factor assumptions, and cash
hurdles into a new admission epoch. Household FX fallback is cut off at the
capital-market-basis epoch, so a later observation cannot enter an earlier
planning scenario merely because the screen was reopened.

The live 2026-08-14 source pass consumed 80 of 510 configured sources with zero
required-source failures and materialized 3,277,101 observations. The remainder
is chiefly unscheduled capacity, not failed collection. Deterministic derivation
then produced 933 signal observations and a separate standard-metric layer while
retaining typed optional gaps.

Potential order owns the handoff. Broad screens compare all eligible rows for
which the required coordinates exist, preserve typed exclusions, and assign
within-kind or within-sleeve ranks. Diversity closure chooses among ranked
residuals without replacing that order. Subscription research receives the
highest-ranked candidate and its named unknowns; it cannot choose a favorite,
rewrite the numeric screen, or allocate capital. The UI shows the rank,
doctrine disagreement, web-research state, coverage, and exact scheduling
reason separately. A daily research budget may leave work queued; that state is
a visible scheduling constraint rather than a data-availability claim.

The daily budget counts durable subscription dispatch receipts, not queue
claims. A claim is only a concurrency reservation: if currentness,
supersession, coverage, or evidence admissibility settles the job before a
provider launches, the idle queue reconciles the reservation away. A live
claim prevents downward reconciliation. Quarantined dossiers are never valid
parents for activation research; the candidate returns to the fresh,
potential-ranked dossier lane. This keeps scarce web calls attached to
questions the agent can still resolve.

## Research that can earn learning credit

A qualitative dossier now crosses the same identity membrane as a numeric
screen. When a current candidate becomes an active zero-weight paper watch, the
watch—not the earlier raw discovery row—is the next closed-book forecast
subject. Its immutable packet contains the candidate and dossier leaves, thesis,
rival, falsifiers, business-fingerprint residuals, compact valuation/factor
coordinates, and the strategy phenotype visible at issue time. Raw discovery is
suppressed for that entity and horizon. Later settlement can therefore compare
the researched representation with valuation, momentum, and no-edge controls.

Institutional learning resolves strategy metadata at the forecast's opening
cutoff. A dossier, coverage bridge, or quarantine event created later cannot be
joined to an earlier episode. New paper-watch packets carry the frozen phenotype
directly; legacy episodes use the Golden Store's as-of heads. This makes the
question “did company and strategy research improve the forecast?” measurable
without letting subsequent research rewrite the predictor cohort.

Allocation readiness consumes the same current paper-watch identity. Before a
compiled admission exists, a zero-weight watch is shown as `active_paper`, with
its exact position-admission residuals and the next shared admission transition.
The shared compiler joins either a public equity or a public fund to its exact
sleeve, factor, covariance, downside, fee, liquidity, and cost evidence. Once
that candidate-bound artifact exists, readiness shows `portfolio_candidate`,
retains its digest and status, and points to selection among household policy
rivals. It never infers admission from a ticker or lets a stale candidate epoch
cross the boundary. The portfolio-policy tournament verifies the sealed
workspace artifact and consumes its eligible public-equity admissions.
Account mandate, current-book, tax, and currency implementation remain private
inputs at a later transition.

The action surface uses two clocks. An active subscription queue lease wins the
display and names the exact subject being researched. If the queue is waiting,
the live projection names its next candidate, current dispatch-budget blocker,
and exact UTC reset; only an empty candidate lane falls back to the periodic
source or settlement cadence. A future due time therefore cannot hide active or
already-ranked work.

Candidate-level research experiments use a third outcome contract but no new
service. Request issue freezes the typed rank-lane benchmark, day-30 action
cutoff, day-365 terminal, 5% probe, and cost. The existing capital-cycle clock
binds the first post-cutoff common price, freezes the first exact full-research
forecast available by the cutoff, and later settles either its after-cost active
contribution or zero for abstention. The workbench reports these units separately
from 21- and 90-day forecast diagnostics and from zero-weight operator watches.

The queue also closes equivalent activation work before a provider call. Its
identity is candidate leaf × prior dossier × source batch × material source hash
× coordinate set × question-policy contract. Exact duplicates share one owner.
When the question grammar or assignment contract becomes richer, the current
contract replaces queued legacy requests over the same evidence basis; a
claimed request is allowed to finish. The 2026-08-22 migration converted 44
redundant queued activation requests into zero-call completion receipts and
reduced the live candidate lane from 68 to 24 jobs. No history was deleted and
no rank, evidence, paper state, or capital authority changed.

Coverage reuse now runs the dossier validator before a `covered` bridge is
recorded. An ambiguous publication clock appends a quarantine leaf, changes the
candidate coverage state to `research_evidence_quarantined`, and routes a fresh
candidate-bound request; it cannot remain simultaneously “covered” in research
memory and invalid in the proposal compiler. The first repaired path is EFV:
its legacy dossier is preserved, its current rank-2 fund candidate now owns a
new subscription request, and the live action surface schedules that request
at the next dispatch-budget opening.

Household implementation uses the broad proxy inside each sleeve as the
economic comparator. A stock's positive premium over Treasury is compensation
for factor risk, not evidence that it improves on SPY or VXUS. The paper menu
therefore keeps factor-required return and cash-flow-implied return as separate
selection hypotheses, subtracts the matching sleeve assumption, freezes their
signal identities and selected values into the policy and later settlement,
and marks both as non-forecast coordinates. Equal-weight
admission is the control. Prospective settlement can then identify which
selection rule changed the complete household policy and whether that change
helped after costs.

This is a direct use of recursive enumeration plus closure. The compiler keeps
the stable rule programs, including rules whose current action is to remain in
the broad proxy, then quotients them by exact portfolio-weight equality for the
display. The operator sees distinct decisions; the learning ledger keeps all
rule identities. A factor rule that abstains today can therefore be compared
with the same rule when a later candidate set makes it act.

Evidence closure is one candidate lane. A missing or quarantined dossier routes
to fresh research; a material source change routes to reassessment. When that
reassessment directly blocks a current qualified candidate, it inherits the
candidate's research rank and reserved subscription cadence. On admission, the
worker recompiles both equity and fund proposal projections. Reassessments not
bound to a current qualified candidate remain maintenance work.

## Underwriting information and portfolio handoff

The next question is not whether a dossier sounds insightful. It is whether the
incremental information changes a sealed forecast and improves a later outcome.
Each researched paper watch therefore produces three separate forecasts from
strictly nested evidence: typed quantitative inputs; those inputs plus the
business fingerprint; and those inputs plus the full thesis, rival, strategy,
and research program. All three share one episode core and one process identity.
Settlement compares absolute active-return error, underperformance Brier loss,
and after-cost paper active-return contribution. Overlapping return windows count
as one inference block. The comparison remains immature until all three
increments have eight independent blocks and a complete resolved process
identity. The directional hypothesis fails if any higher-information comparison
lacks a positive block-weighted mean on any declared outcome. Positive means
remain descriptive because the current object has no multiplicity-aware
promotion gate.

The packet also lists the availability of each forecast input. A row names the
field path, source, availability time, cutoff, basis, and optional observation
time and content digest. Future-dated fields are rejected. Missing required
paths stay visible as unverified, so `complete=false` cannot be presented as
full source coverage. This controls the recorded information set; it does not
show that a model lacked outcome knowledge from training. Historical LLM market
forecasts therefore remain diagnostic unless no-training-leakage can be
established. Prospective sealed episodes carry the predictive burden.

The shared instrument-admission contract is the bridge from research to a
paper-portfolio candidate. It supports equities and funds without treating
historical fund residual alpha or a factor required return as an expected return.
Factor output is carried as a typed hurdle. A full-research forecast becomes a
separately hashed prospective active-return claim only with its subject,
benchmark, horizon, issue time, forecast, packet, and decision lineage intact.
Identity mismatch, stale
factor evidence, absent covariance membership, or missing implementation
evidence blocks admission. A missing forecast does not block risk or equal-weight
comparisons, but it excludes that security from expected-return policies. The
policy horizon and benchmark must match the claim exactly. With at least two
compatible public-equity claims and positive aggregate active return, the paper
tournament adds two capped rivals: weights proportional to positive active return,
and weights proportional to positive active return divided by downside proxy. The
existing gross and per-position caps apply. These compete against cash,
equal-weight, discovery- and law-priority, factor-implied-return, and minimum-
variance controls. Fund admissions remain same-sleeve comparisons, and private
account implementation remains outside this public-data object.

Portfolio family `v8` enforces this split. The recurring forecast schedule now
contains 21-, 90-, and 365-day lanes, so the one-year allocator can eventually
consume same-horizon claims without converting a shorter prediction into a
different estimand.

Finally, each signed policy settlement reprices the same frozen weights and
gross returns at 0, 5, 10, 25, and 50 basis points. It exposes cost drag,
break-even cost versus benchmark, and whether policy ordering changes. A policy
that wins only under the chosen cost assumption has not passed the robustness
check. A policy that remains ordered across the grid has cleared only that
diagnostic; it has not established predictive performance.

## Method and data anchors

- [Adaptive submodularity](https://arxiv.org/abs/1003.3967), [information-directed sampling](https://arxiv.org/abs/1403.5556), [nonmyopic active search](https://proceedings.mlr.press/v70/jiang17d.html), [diverse active search](https://proceedings.mlr.press/v206/nguyen23d.html), and [multifidelity active search](https://proceedings.mlr.press/v139/nguyen21f.html) bound the acquisition-policy research direction. The current score is an inspectable greedy proxy and claims none of their posterior or approximation guarantees.

- [SEC EDGAR application programming interfaces](https://www.sec.gov/edgar/sec-api-documentation) own company-fact access and filing chronology.
- [SEC Form N-PORT datasets](https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets) establish the public holdings path for registered funds and ETFs.
- [NYU Stern's implied ERP data](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/implpr.html) and [FRED's T10Y3M series](https://fred.stlouisfed.org/series/T10Y3M) anchor the current market-state inputs; the engine records retrieval-time authority rather than treating those pages as historical vintages.
- The [iShares IJJ](https://www.ishares.com/us/products/239764/IJJ), [Vanguard VOE](https://investor.vanguard.com/investment-products/etfs/profile/voe), [Harbor EPMV](https://www.harborcapital.com/etf/epmv/), [Avantis AVMV](https://www.avantisinvestors.com/avantis-investments/avantis-us-mid-cap-value-etf/), and [First Trust FNK](https://www.ftportfolios.com/retail/etf/ETFsummary.aspx?Ticker=FNK) issuer surfaces are the current aggregate-characteristic authorities; exact retrieved payloads remain in the cache.
- Sirius XM's [2026 Q2 filing](https://investor.siriusxm.com/sec-filings/all-sec-filings/content/0000908937-26-000022/siri-20260630.htm) and [2025 annual filing](https://investor.siriusxm.com/sec-filings/all-sec-filings/content/0000908937-26-000006/siri-20251231.htm) are the primary-source authorities used to repair debt concept selection and re-evaluate the candidate.
- [Alpha Vantage ETF profile documentation](https://www.alphavantage.co/documentation/) documents current ETF assets, fees, turnover, holdings, and sector allocations.
- [Kenneth French's research data library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) is the target source for research-factor returns; the current ETF long-short proxies are explicitly labelled operational proxies.
- Ohlson and Juettner-Nauroth's earnings-growth valuation model is a methodological anchor for treating price as an expectations equation; the implemented cash-flow grammar remains its own declared model rather than claiming equivalence.
- [PAL](https://arxiv.org/abs/2211.10435), [LEVER](https://arxiv.org/abs/2302.08468), [RouteLLM](https://arxiv.org/abs/2406.18665), and [Large Language Monkeys](https://arxiv.org/abs/2407.21787) ground the capability-adaptive execution split: models may produce direct or programmatic answers while typed execution receipts and verifiers control routing.
- [Temporal Leakage in LLM Backtesting](https://arxiv.org/abs/2608.02985) shows why a passive historical LLM backtest alone cannot identify skill separately from temporal leakage; the closed-book ledger uses prospective settlement as its full-engine evidence lane.
- [TEMPO](https://arxiv.org/abs/2605.18843) reports that prompt constraints alone do not reliably suppress post-cutoff parametric knowledge, which is why web-disabled historical replay remains diagnostic here.
- [OpenPM](https://arxiv.org/abs/2608.09988) motivates field-level
  point-in-time gating, typed constraints, analyst/constructor separation, and
  turnover-aware cost auditing. Its single frozen-window results do not transfer
  to this engine.
- [The Statistical Limit of Arbitrage](https://www.nber.org/papers/w33070)
  bounds the search ambition: weak, rare pricing signals and estimation error
  can leave a wide gap between a theoretical opportunity and a feasible policy.
- [Large Language Models: An Applied Econometric
  Framework](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5094968)
  motivates treating historical LLM prediction as diagnostic unless the design
  rules out training leakage, and validating LLM-generated measurements before
  downstream inference.
- Hansen, Lunde, and Nason's [model-confidence-set paper](https://www.econstor.eu/bitstream/10419/100950/1/wp2005-07.pdf) and Bailey et al.'s [probability-of-backtest-overfitting paper](https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253) bound the extensions required before model tournaments or market-flow experiments can influence a paper policy.
- [Sequential model confidence sets](https://arxiv.org/abs/2404.18678)
  supply the right target for a continuously observed world-model tournament:
  retain a set of statistically indistinguishable survivors with time-uniform
  control instead of crowning whichever model is currently ahead. The current
  independent-block and multiplicity gates are a narrower precursor, not that
  guarantee.
- Decision-focused portfolio work on [mean-variance
  allocation](https://arxiv.org/abs/2409.09684), [covariance
  estimation](https://arxiv.org/abs/2508.10776), and [sparse tangent
  portfolios](https://arxiv.org/abs/2607.00581) supports scoring a method by the
  downstream constrained portfolio consequence rather than prediction error
  alone. JaggedThoughts therefore requires after-cost policy settlement before
  a model can earn allocation credit; it does not import those models' reported
  portfolio performance.
- [Invariant causal prediction across changing
  environments](https://www.jmlr.org/papers/v21/19-407.html) bounds the strategy
  transfer ambition. A move is reusable only under an exact prior phenotype,
  moderator, environment, metric, source, and chronology match, and even that
  match merely selects a future question until cross-environment outcomes
  support invariance.
- White's [Reality Check for Data Snooping](https://doi.org/10.1111/1468-0262.00152) and Bailey and López de Prado's [Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551) motivate accounting for every tried specification. The implemented trial-count screen is only a conservative Bonferroni consequence and claims neither named method.
- Gu, Kelly, and Xiu's [machine-learning asset-pricing study](https://academic.oup.com/rfs/article/33/5/2223/5758276), Harvey, Liu, and Zhu's [multiple-testing critique of the factor zoo](https://academic.oup.com/rfs/article-abstract/29/1/5/1843824), and the [factor-timing evidence](https://academic.oup.com/rfs/article/33/5/1980/5753962) motivate strong same-information controls, chronological partitions, and restraint around a newly discovered state variable.
- Jensen and Kelly's [implementable-efficient-frontier study](https://academic.oup.com/rfs/advance-article/doi/10.1093/rfs/hhag022/8524346) motivates learning the portfolio objective after turnover and trading costs rather than optimizing a forecast first and applying implementability as an afterthought. This is why research rank cannot flow directly into target weights.
- [Machine Learning Meets Markowitz](https://www.nber.org/papers/w34861)
  motivates selecting covariance regularization against chronological portfolio
  risk rather than treating an in-sample covariance fit as the objective. The
  workbench's ridge challenger is narrower: expanding holdout selection,
  one point-in-time refit, exact long-only caps, and diagnostic status only.
- [Universal Portfolio Shrinkage](https://www.nber.org/papers/w32004) shows a
  richer shrinkage frontier. JaggedThoughts does not import its unconstrained
  long-short factor/SDF assumptions into the household public-equity sleeve;
  that remains a separately identified research extension.

## Current decision-focused challengers

The fund lane now asks a clean invest-versus-cash question without collapsing
all fund selection into one number. A source-hashed public cash hurdle is shared
by sleeve comparison and instrument admission. Fee-adjusted factor return over
that hurdle is one frozen ranking program; the holistic program still combines
valuation, factor return and risk, implementation cost, and fit. Both receive
the same future fund returns. Historical residual alpha has zero credit.

The portfolio risk lane makes a similarly downstream comparison. Expanding-
window validation chooses the ridge covariance penalty before the policy seal.
Later synchronized adjusted prices settle realized volatility, negative maximum
drawdown, round-trip turnover, and after-cost mean-variance utility versus the
fixed-shrinkage minimum-variance arm. The risk-aversion parameter is frozen in
the policy, defaults to 3.0, and is tunable in the capital-cycle profile. Eight
independent blocks are required before a paper review; no result routes an order.
- The current [AI-and-strategy capability/delegation framework](https://pubsonline.informs.org/doi/10.1287/stsc.2026.intro.v11.n1) motivates treating prediction, intervention, transported counterfactuals, and new-frame construction as different task identities. The agent may attempt the broader tasks; evidence and authority remain transition-specific.
- [Structural causal models for managerial interventions](https://pubsonline.informs.org/doi/10.1287/stsc.2022.0169) motivate the explicit strategy move, mediator, comparison, and outcome contracts. The cross-company law layer cannot promote a narrative correlation as an intervention effect.
- [Stochastic Force Inference](https://arxiv.org/abs/1809.09650) and the [probability-current treatment of irreversible dynamics](https://www.nature.com/articles/s41467-019-09631-x) ground current as a state-transition observable. They do not establish that current predicts asset returns; the project must earn that relation against ordinary statistical rivals.

### From a planning menu to institutional memory

The household screen first computes a broad-sleeve control and bounded
admitted-security rivals. Those rows remain disposable while the user changes
assumptions. “Freeze one-year paper comparison” is the membrane: the server
recomputes the screen, checks its content hash, and stores the exact complete
weight vectors plus a linked private scenario snapshot before any later entry
price is selected.

All rivals then enter one synchronized adjusted-price window. At maturity the
engine compares each complete policy with its own broad-sleeve control after
the same cost rule and reconciles the difference by position-weight deltas.
Repeated episodes test stable allocation rules such as equal-weight admitted
satellites; they do not turn whichever ticker was ranked highly into an
expected return. Eight independent one-year blocks are required before a rule
can appear as a statistical survivor for human review. Nothing in this path
places trades or changes the household mandate.

The institution-wide learning view treats the household implementation rule as
its own experimental component. It shows whether an episode is missing, active,
settled but underpowered, or eligible for review; the next-experiment compiler
keeps the broad control, challenger identities, scenario hash, return window,
and remaining independent blocks together. This is the bridge from a portfolio
result to accumulated allocation craft.

The Goldilocks split is explicit. A human starts the comparison because the
goal, contribution, reserve, and risk limits are private policy choices. Once
started, deterministic services own source refresh, point-in-time binding,
maturity, cost accounting, and settlement. Statistical output returns to human
review and cannot revise the mandate by itself.

The browser is a view over this state, not its owner. The complete local read
model stays on disk; each investment tab receives only the content it renders,
with both the underlying read-model hash and a served-projection hash. Switching
tabs fetches the next projection. This keeps the Overview responsive without
weakening the deeper World Models or institutional-learning artifacts.

## Strategy actions as state-path experiments

A management action becomes testable only when four identities meet: the dated
public event, the company state observed after that event, two later state
classifications under the unchanged partition, and an operating metric observed
after the state path. JaggedThoughts now freezes that chain as one research-only
artifact. It asks whether an action phenotype improves persistent-state
prediction beyond directed Markov, reversible Markov, industry-state Markov,
persistence, and clean no-move peers; it does not infer success from a business
description or from the stock price.

The first frozen chain is deliberately blocked from evaluation. Directed and
reversible controls are available from the same archived transition rows, but
industry-conditioned transition counts and eligible no-family peers are not.
Peers with adjacent-family activity are treated units or exclusions, never
controls. This blocked state turns the next work into two exact acquisition jobs
instead of producing a causal-looking number from an inadequate cohort.

Integrated strategy programs have a separate clock. Exact option events first
trigger a source-bound search asking whether management executed the complete
recursive bundle. A confirmed bundle freezes only operating readouts already shared
by its constituent moves. Its composition-control compiler then seeks the same
constituent mechanism phenotypes without joint-program evidence and same-size local
peaks under the identical environment and readout. The estimator is therefore
“joint program minus fragmented ingredients,” not “program companies did well.”
The first MRVL program search is queued; there are no program cards or settled
readouts yet, so this lane contributes no strategy law or security-return credit.
Its subscription completion advances the business clock automatically.

## Strategy understanding to security-return challenge

The operating-outcome learner and the investment learner now meet in a second,
separately scored clock. Each SEC transaction episode keeps its filed strategy
phenotype and future owner-earnings outcome. The new bridge joins that same
episode to a one-year adjusted-price outcome, waits two daily trading sessions
after filing availability, and charges 20 basis points. Admission requires the
filing CIK to equal the configured SEC entity and the filing's own
`dei:TradingSymbol` to equal the configured market series. Reorganizations,
ticker changes, and older filings without a trading-symbol fact remain outside
the isolated-security experiment.

The timing rule follows the central event-study discipline: event time,
pre-event diagnostics, comparison choice, and dynamic outcomes must stay
visible rather than collapsing into one before/after average. See the
[AEA event-study guide](https://www.aeaweb.org/articles?id=10.1257%2Fjep.37.2.203).
The separate announcement belief and later realization clocks are also aligned
with the [Event Long-Short Index](https://pubs.aeaweb.org/doi/10.1257/aeri.20180399).
Acquisition evidence shows why environment belongs in the grammar: market
valuation at the acquisition date can reverse the relation between announcement
response and later operating or stock performance
([Review of Financial Studies](https://academic.oup.com/rfs/article/22/2/633/1594294)).
The two-session delay is deliberately conservative because disclosure-trading
studies find that same-close execution and weak liquidity filters can overstate
profitability ([SSRN study](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3910451)).

The first acquisition exposed a provider-contract failure: `range=max` silently
returned weekly, monthly, or quarterly coordinates even though the manifest
declared daily data. The adapter now requests explicit epoch bounds, rejects a
symbol or granularity mismatch, and compacts rows derived from cached
mis-grained payloads. The repair removed 19,136 mislabeled observations across
the 38 issuer/benchmark sources before the experiment was rerun.

The factor target uses the already declared tradable proxy basis: market
(`SPY`), value (`IWD-IWF`), size (`IJR-SPY`), momentum (`MTUM-SPY`), and quality
(`QUAL-SPY`). Each episode freezes its betas on up to 252 daily returns ending
before the filing, then settles factor-controlled log return over the later
window. This follows the system's existing factor identity while keeping
[Kenneth French's research factors](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_Library.html)
as a future model challenger. Factor-model choice matters; a favorable alpha
under one basis cannot settle the model comparison by itself
([Which Alpha?](https://www.nber.org/papers/w21698)).

The source population contains 67 classified episodes. Exact filing-era identity
now accepts either the event filing or the latest immutable periodic filing
accepted before the event, but only when the SEC CIK and issuer-stated symbol bind
the configured tradable series. This resolves 11 identities without a current-
ticker bridge. Seven renamed or unstated identities remain excluded; factor,
entry-price, and overlap gates bring total coverage gaps to 25. The isolated-move
tournament retains 38 outcomes. For each annual test fold, training admits only
episodes whose one-year return window ended before the earliest event in that
fold. Recursive enumeration compares all 16 transaction-grain programs and
frontier closure selects the next program using earlier scored folds. Four folds
score 25 events.

Those four chronological folds are not four independent experiments. Their
one-year tradable windows overlap transitively into one connected component, but
that component is a dependence diagnostic rather than the inference sample size.
The compiler now forms paired typed-versus-untyped deltas in four event-year
cohorts and applies horizon-matched Newey-West uncertainty with one lag. The
typed policy's forecast-error advantage is -0.91 percentage points with a 95%
interval of [-5.31, 3.50]; its after-cost paper-return increment is +0.62 points
with a 95% interval of [-0.15, 1.39]. Both include zero, and only four of eight
required calendar cohorts exist. Security-alpha, promotion, paper-policy, and
capital authority remain false.

The remaining boundaries are current-retrieval rather than archived issue-time
price vintages, a current configured issuer universe rather than a historical
population census, a representation and sample design chosen after historical
outcomes existed, tradable ETF factors rather than a settled universal factor
basis, and residual industry/event confounding. Only unchanged prospective
cohorts can adjudicate the strategy-security thesis.

That failure now drives a typed representation-repair path. Identity and factor-
history gaps route back to acquisition, while aggregate forecast loss cannot
invent a new grammar axis. The only current representation witness is the five
excluded overlapping events: two connected same-issuer move paths that the
isolated-event grammar cannot encode. They support a test of composition; they
provide no return evidence.

The repair compiler binds three positional, source-bound move terminals and
canonical `compose`, `append`, and `project` path operators, both grammar
digests, ordered path witnesses, selection cutoff, target observable, and frozen
factor-execution contract. Specialized enumeration retains the exact 16
incumbent moderator projections and adds only canonical length-two and
length-three path projections: 18 candidate programs, without repeated or
reordered moderator syntax.

The cross-grammar checker executes those two paths against a frozen probe set.
Positive probes must reconstruct issuer, ordered episode hashes, connected
interval, and phenotype sequence exactly. Reversed, duplicated, cross-issuer,
and disconnected tuples must all be rejected; irrelevant metadata must leave
the output unchanged; all incumbent behaviors must remain identical. The shared
evaluation-surface hash binds the probes, interpreter, objectives, and strict
improvement margin. Both path behaviors improve exact projection rate over the
incumbent and remain nondominated, so state is
`same_epoch_behavior_qualified`. This receipt establishes executable
representation only: it reads no return outcome and grants no rank or policy
credit. The qualified grammar can now be frozen into a complete future-shadow
matrix with power analysis, multiplicity accounting, and at least eight later
independent blocks. A successful future trial may change only the default
grammar for later shadow forecasts.

The prospective carrier is `StrategyPathShadow`. The existing capital-cycle
service owns its clock: once per day it checks the SEC submissions archive,
admits only Item 2.01 filings whose acceptance time is strictly after the
frozen selection cutoff, hydrates the exact queued filing, and types ambiguous
cases through the logged-in Codex subscription runtime. Event equality is
`{reporting CIK, accession number, Item 2.01}`. The mutable submissions-index
hash remains snapshot lineage and cannot redefine the event.

The first archive refresh may scan the complete SEC population. Later archive
epochs compare zip-member CRC and size identities against the prior retained
archive, carry unchanged issuer events into the new source epoch, and reparse
only changed issuer histories. A current-equity population change forces event
rows to be rebound rather than rewriting population metadata alone. The Company
Facts outcome lake applies the same member-identity rule and reparses newly
admitted event issuers even when their archive member itself is unchanged. The
raw archive download, hashing, and member-index scan remain population-scale;
the expensive JSON reparsing and row compilation scale with changed or newly
admitted issuers.

After both current lakes and their lineage hashes validate, local retention keeps
the current and predecessor SEC zips byte-for-byte. Older raw zips are removed
only after a verified reverse delta stores every older member that changed or
disappeared plus the successor-only removal set. That reconstructs the older
logical member snapshot from its successor; it intentionally does not reproduce
the original zip container bytes. A signed retention receipt lists every removed
raw path, byte count, delta path, and digest.

The 2026-08-22 operating pass verified this path against the local public-data
workspace. It compiled 26,165 Item 2.01 events and 912,026 annual Company Facts
observations, rejected SEC facts whose filed date preceded the stated period end,
and routed stale semantic resolutions back to the subscription queue when their
deterministic classification identity changed. The downstream compiler produced
14 bounded effect diagnostics, 13 panel-ready cells, eight frozen child-law
candidates, and 32 source-acquisition frontier items; every output retained zero
allocation authority. Five superseded Company Facts zips were replaced by five
verified logical deltas while the current and predecessor zips remained exact.
Retention receipts are immutable and repeated no-op checks preserve a cumulative
verified delta inventory.

Each admitted move freezes its filing-symbol-to-current-common-equity identity,
classification receipt, occurrence time, availability time, and observer time.
The observer appends moves without refitting. It emits separate length-two and
length-three connected paths, with the terminal move as the forecast target;
earlier moves are context. The three frozen arms are an untyped historical
median, the isolated terminal-move model, and ordered path composition. A path
forecast settles after its declared horizon using the same pre-issue factor fit,
tradable factor basis, entry lag, and costs as the historical challenge. Exact
factor definitions and their digest are frozen at selection and checked again at
settlement.

The primary representation trial remains a 365-day target with eight purged,
non-overlapping two-horizon cohorts. Its earliest review is deliberately slow.
Every forecast therefore also freezes a 90-day diagnostic clock. The diagnostic
annualizes its factor-controlled log-return target only for error comparability,
reports direction and long-or-cash paper economics, and performs no independent-
block inference. It has zero grammar, routing, ranking, paper-policy, or capital
authority.

Settlement lowers the complete three-arm matrix into the shared world-model
tournament. That kernel verifies chronology and matrix completeness, aggregates
only windows contained inside fixed, disjoint two-horizon cohorts, purges windows
that cross cohort boundaries, scores absolute prediction loss and after-cost
long-or-cash returns, and applies its cohort-resampled multiple-comparison rule.
Eight non-overlapping settled cohorts are the minimum review boundary. Representation
credit requires the ordered-path model to be the sole conservative survivor;
positive point estimates cannot pass. Even a pass can only propose a later
grammar-default change; security ranking, paper policy, and capital authority
remain separate decisions.

This deterministic observer is distinct from the existing subscription-agent
underwriting tournament. The observer measures whether the new representation
adds information under a frozen target. The agent tournament supplies richer
valuation, durability, thesis, and rival-mechanism judgments. Their join is a
typed handoff after candidate identity and chronology pass, rather than one
uninspectable forecast.

Probability-current and Lagrangian challengers stay on a separate clock. The
current daily-flow models lost their simpler controls and do not share a state
object or horizon with the one-year strategy experiment. The coherent future
bridge is nested: empirical company-state Markov; Markov conditioned on a
qualified strategy path; then the conditioned model plus an antisymmetric-current
term. State-transition cross-entropy and Brier score come before the separately
settled factor-controlled return. This ordering prevents a physical analogy from
receiving investment credit before it adds predictive information.

The 2026 [Model Discovery Agent preprint](https://arxiv.org/abs/2608.09696)
supports the broader proposer → rival models → predictive check → discriminating
experiment loop. JaggedThoughts already owns deterministic committees, query
selection, counterexample reopening, typed grammar search, and prospective
settlement. It now also owns a small finite-structure belief primitive: callers
freeze model identities, prior or uniform-design weights, and categorical
predictions for a finite question menu; later source-bound observations apply a
normalized likelihood update; remaining questions are ranked by posterior-
predictive mutual information per declared cost unit. The investment adapter versions the
existing thesis/rival/null response matrix and produces every probability vector
in the same closed-book subscription call. The browsing agent receives only the
assigned question and execution hashes. Realized policy value is information bits
per declared source-call unit; actual acquisition-call calibration is absent. A
committee-wide miss scores zero and ends that model-
set epoch. It is paired against the incumbent research question and reviewed at
chronological 20 × 2^k pair counts under geometric alpha spending, a declared
useful-effect threshold, and a look-specific power receipt. It may change only
future evidence order. SMC, SBI, within-model parameter inference, and calibrated
market-model posteriors remain absent. BIC, MDL, or a uniform design cannot be
relabeled as posterior conviction.

The possible systems contribution lies in the combined protocol: a typed
strategy grammar, recursive representation search, separate operating and
security consequences, chronology-valid program selection, and prospective
promotion gates. Event studies and strategy-return prediction already exist.
A paper track becomes warranted only after market-wide coverage, a frozen
classifier, multiple factor and event-control challengers, enough independent
holdout blocks, and prospective comparison show that the combined protocol
improves either forecasting or allocation after costs.

The subscription scheduler now treats activation as its own service lane. A
queued activation must be claimed after at most three completed non-activation
calls, even when newly discovered candidates keep arriving above it. A fresh
activation reserves two daily dispatch units because it first freezes a
closed-book response matrix and then runs the assigned public-source search.
Retries may use fewer calls when the matrix already exists; the queue reconciles
reserved units to durable dispatch receipts when the lease ends. Status exposes
the next activation, its cadence debt, and its two-unit requirement. The current
ZD request passed a no-write structural preflight against its current discovery
identity, golden-store parent, 80-program enumeration, three-program frontier,
complete nine-cell matrix, and single-program browse view. After the next UTC
budget window the periodic service completed it: the balanced assignment chose
the incumbent question while the matrix preferred another program; bounded web
research executed only the assigned incumbent, and the dossier and settlement
preserved the exact assignment and execution hashes. The observed response was
`mixed`; with zero complete matched pairs, future routing remains balanced. The
episode has no allocation authority.

Fund implementation evidence now receives the same kind of bounded service
without being mixed into the equity rank. Each queue refresh keeps only the
current request × prior-evidence identity for each comparison-bound fund and
retires older epochs before they can invoke the subscription runtime. After an
exact frozen successor, at most three calls outside the fund lane may pass while
current fund work waits. The fund leader still comes from its sealed
cross-sleeve potential order; the cadence changes research service, not
investment merit. Status reports the leader, backlog, cadence debt, and bound.

The institutional-credit membrane is executable on three downstream uses. A prior
research-routing winner is ignored unless the current read model contains a
hash-valid `LearningCreditAssignment` for the exact decision and explicitly
admits `future_research_question_routing`; the reusable assignment kernel owns
that check, including for direct callers. The response-matrix winner uses the
same rule with its exact policy-learning hash and
`future_activation_question_routing`. Failure returns either lane to balanced
assignment. Both routes also compare the current research aggregate or
activation eligible-pair-set digest, preventing replay after later settlements.
The underwriting-information selector also remains three-arm
balanced unless a nested same-process ablation earns an exact
`future_underwriting_method_routing` receipt bound to the current ablation
status. This makes the aggregate credit object a consumed authorization receipt
rather than only a dashboard count.
Strategy-law and complete-policy surfaces remain paper challengers or operator-
review inputs.

The automation readout is a pipeline status, not a profitability claim. At the
current epoch the engine discovers, researches, freezes, and queues work
automatically, but it has zero settled production episodes and therefore zero
earned law adjustments. The next informative transitions are the first 21/90-day
security settlements and the first source-bound quarterly business outcomes. The
workbench should show those counts, due dates, and blockers directly.

Limited paper-watch capacity now follows the opportunity book's exact learned
research order across both equities and funds. This chooses what the institution
studies next, not a funded portfolio. Every admitted watch remains zero weight and
paper-only.

## How a failed strategy comparison compounds

The MRVL strategy-state experiment illustrates the learning loop. Its original
cohort was frozen, so later peers cannot be inserted into it. A successor receipt
instead fixes the later cohort's exact semiconductor × move-phenotype set and asks
which unresolved observations could still produce an untreated comparison. The
resolver reuses a prior classification only when its semantic question is identical
and all cited filings, issuer documents, and events predate the frozen source cutoff.

That replay recovered GFS and TSM without new calls. Both had adopted the related
move family. Together with the other classified peers, this left 25 contaminated
same-environment firms, zero untreated controls, and zero unresolved firms. The
matched-peer successor is therefore unavailable. The useful output is the design
boundary: the engine must try a different identified comparison, such as timing,
intensity, active-alternative, or synthetic-control designs with their own assumptions,
instead of turning family adopters into convenient controls. The negative result is
retained in the workbench and prevents the same dead-end search from consuming future
research budget.

## What the Lagrangian lane means now

The useful formulation is not that companies obey mechanics. It is a conservative
probability update over company paths:

`new path odds = ordinary Markov path odds × exp(strategy-linked path feature)`.

The multiplier is a Lagrange multiplier because the model pays relative entropy for
moving away from ordinary transition odds. That structure is useful only if a small,
pre-outcome feature grammar predicts later paths for unseen issuers or environments
better than directed Markov, reversible Markov, second-order logit, survival/dwell,
and same-feature path-logit controls. Maximum caliber is path-entropy inference
([Pressé et al.](https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.85.1115));
under pairwise information it can reduce to ordinary Markov maximum likelihood
([Ge et al.](https://arxiv.org/abs/1106.4212)). The notation itself therefore creates
no edge.

JaggedThoughts now tests whether this family is measurable before fitting it. On the
exact company-path panel, an injected nonzero tilt is recovered with 76.6% sealed
power while the null is falsely promoted 12.5% of the time. The required floors are
80% power and at most 5% false promotion, so the gate blocks a strategy-conditioned
fit. The same-feature offset path-logit reproduces the MaxCal probabilities to machine
precision. This makes the current opportunity clear: MaxCal may become a compact,
stable transfer restriction, but it is not a separate predictive family unless it
excludes and beats same-information controls.

This also explains why the engine is acquiring exact strategy dates and later filing
states instead of searching equations now. The current join has four event bundles,
two issuers with any observable post-event path, and zero fit-qualified issuers. More
independent paths can change the recovery verdict; changing the formula after seeing
the sealed losses cannot.

The readiness surface keeps two evidence lanes separate. RRC exact-event refinement at
learning-schedule rank one can improve the strategy/path join; it cannot change the
recovery score because that score comes from a different frozen company-state
partition bundle. The event consumer refreshes the join after an exact event settles.
The unchanged recovery audit runs again only when that partition bundle changes. A
strategy-conditioned tournament requires both recovery and the eight-issuer support
floor. PYPL's already-open dependency still executes first because acquisition ranking
and executable provider claims have different owners.

The path successor is executable and fail-closed. An adversarial audit removed 471
mislabelled controls: those companies showed family-only or equivalent adoption and
therefore cannot represent non-adoption. The corrected adapter has zero certified
non-adoption paths and zero mature exposed two-step paths. The production activation
emits a content-hashed blocked receipt rather than fitting. When both classes mature,
it will fit one coefficient that asks whether
certified exposure shifts ordinary Markov odds toward sustained durability improvement,
then score later-time and unseen-company partitions. Second-order Markov and a
strategy-blind durability drift can veto it. Calendar shuffles, industry shrinkage,
neighboring state grids, and matched alternative phenotypes remain later vetoes.

This is the division of labor. Recursive enumeration plus Z3 proves which authored
strategy bundles are feasible and that the bounded bundle space was exhausted. The
flat Lagrangian/path-logit still carries no recursive credit. Its executable successor,
`strategy_program_representation_ablation.py`, starts only after primary sources
identify one exact integrated program and every constituent implementation event.
It projects each constituent to a cross-company mechanism phenotype and each authored
interaction to a content-bound interaction phenotype. Using the same empirical Markov
offset, ridge estimator, paths, and chronological partitions, it compares the
integrated choice system with the identical leaf phenotypes flattened into a bag and
with an issuer-clustered shuffle. Future-time and unseen-company losses must improve
on every control by at least 0.001, and the improvement must recur in at least 87.5%
of issuer blocks, before the representation survives. Each partition requires eight
issuers with four independent two-step paths apiece, and every tested interaction must
appear in at least four fit and four unseen issuers. Program-adoption results are
revalidated against their frozen primary-source request; program-definition and
path-row hashes are recomputed at the evaluator boundary. Issuer partitions and the
time cutoff are reused once minted instead of being reselected after later evidence.

This successor tests transfer of a previously observed interaction phenotype to later
periods and unseen issuers. It does not yet test an interaction operator on a novel
composition. The latter needs a shared typed interaction representation that can
evaluate a composition identity absent from fitting data; a one-hot conjunction hash
cannot earn that claim.

The successor deliberately does not test syntax-tree depth. The company-strategy
grammar uses an associative/commutative option-set quotient, so alternative bracketings
have the same meaning. Treating their depth as an empirical variable would reward
syntax with no strategic distinction. At the current workspace epoch the activation
is content-hashed and blocked on measurement recovery plus exact-program path support.
The path model asks whether a source-timed integrated choice system transfers to later
business states. A separate return tournament asks whether any business-state
advantage was mispriced. None of those layers may borrow the conclusion of another.

## Removal trial: can the subscription LLM replace the machinery?

The kernel is removable, not presumed useful. Closed-book episodes should compare four
arms using the same frozen source snapshot, company universe, horizon, model family,
call budget, and paper-position rule:

1. a subscription LLM working directly from the available public-source packet;
2. the same LLM with a fixed investment memo and falsifier checklist;
3. the same LLM proposing a thesis and forecast through typed identity, chronology,
   arithmetic, and freeze/settlement gates;
4. the full typed program, recursive frontier, portfolio, and institutional-learning
   path.

The primary endpoints are benchmark-relative forecast loss, calibration, decision
regret, return after declared costs, drawdown, turnover, and abstention quality.
Secondary endpoints are event grounding, unsupported-claim rate, stale-evidence use,
and transfer to unseen companies and unseen choice compositions. Connected return
windows form inference blocks. A passive historical replay is diagnostic only: the
[temporal-leakage analysis of Zhang and Stadie](https://arxiv.org/abs/2608.02985)
shows that passive LLM backtests cannot separate recency from memorized outcome
knowledge without an external reference. Promotion therefore requires prospective
episodes or a matched clean control.

This contest is not a detour into benchmark production. It is a deletion rule for the
capital-allocation engine. If the direct-LLM arm matches or beats the typed successors
on independent blocks, the dominated machinery loses its routing and policy role. If
typed freeze/settlement helps but recursive structure does not beat the identical-leaf
bag, retain the former and remove recursive predictive credit. Current adjacent work
supports the strength of these controls: [InvestLogicBench](https://arxiv.org/abs/2608.06108)
finds that plausible investment prose and event grounding diverge; [InvestPhilBench](https://arxiv.org/abs/2606.25984)
reports that aggregate prose-oriented scores can saturate while gate reconstruction
still fails; and [InvestorBench](https://aclanthology.org/2025.acl-long.126/) compares
thirteen LLM backbones across stocks, ETFs, and other financial tasks. JaggedThoughts
must beat strong versions of those agent baselines on the operator's settled decisions,
not merely expose a more elaborate trace.

The contest is now executable through the ordinary subscription account runtime:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  --path projects/jaggedthoughts_capital/workspace/investment \
  closed-book-open --paper-watch-decision-id <id> \
  --horizon-days 90 --kernel-removal-trial
```

`kernel_removal_trial.py` compiles four content-addressed, nested packets from one
point-in-time field certificate. The direct arm receives the common public-source
catalog and source-grounded research summary; later arms add a fixed method, typed
calculations and chronology, then the strategy/portfolio context. Each arm receives
one isolated subscription session and the same strict forecast schema and 5% positive-
edge paper probe. `closed_book.py` freezes the four candidates before the return window,
settles all of them on the same later prices, and sends only these four candidates to
the existing world-model tournament with `direct_public_packet` as baseline. Eight
overlap-clustered blocks are required for a retention verdict. The World Models view
shows collection progress. No arm receives paper-policy or capital authority.

The first live block is `closed-book-f7b28bd373d352c118ed`, sealed on Genpact
against a 90-day SPY-relative outcome due after 2026-11-25. All four subscription
calls completed on the declared `gpt-5.6-sol` / medium process. Direct synthesis,
fixed checklist, and typed kernel independently returned +1.5% active return and
46% underperformance probability; the full-OS arm returned +1.2% and 46%. This
agreement is not evidence that any arm predicts well. It is an early diagnostic that
the added machinery changed the narrative more than the numeric forecast on this
episode. The later common outcome and independent blocks decide whether any layer
earns retention.

The capital-cycle policy now owns continuation. It reserves at most one 90-day
paper-watch window while another removal window is open, prefers a new issuer, and
stops after eight non-overlapping blocks. This prevents repeated same-market-window
forecasts from being counted as independent evidence and prevents the four-call trial
from silently consuming every candidate budget.
