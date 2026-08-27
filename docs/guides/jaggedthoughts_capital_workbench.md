---
description: "Operate the JaggedThoughts Capital Workbench from public sources through paper-policy activation, portfolio assembly, model diagnostics, and later settlement."
---

# JaggedThoughts Capital Workbench

> Up: [`docs/README.md`](../README.md) · Concepts: [JaggedThoughts Investment Workbench](../concepts/jaggedthoughts_investment_workbench.md) · [Institutional Learning](../concepts/jaggedthoughts_institutional_learning.md)

This is the supported local workflow for the paper-only investment workspace.
It can ingest public data, compile research objects and bounded policies,
assemble a paper portfolio, and score later outcomes. It cannot submit orders.

In user terms: describe an opportunity, let the workbench find public funds and
companies, decompose factor exposure, test price-implied expectations and
earnings durability, inspect feasible strategic choices, then track the
survivors in a constrained paper book. The combined method is an edge
hypothesis until prospective settlements support it.

## Start the interface

The workbench ships with an application-level SEC identity, so no user setting
is required. `ZTARE_SEC_USER_AGENT` is an optional override:

```bash
export PYTHONPATH=src

./venv/bin/python scripts/public/control/forensic_workbench_server.py \
  --host 127.0.0.1 --port 8080
```

The SEC source requirement card reports `uses_builtin_default=true` when the
override is absent. Provider failures still mark the affected deep candidate
as stale for that cycle.

Open:

```text
http://127.0.0.1:8080/?workspace=investment&section=Overview
http://127.0.0.1:8080/?workspace=investment&section=Portfolio
http://127.0.0.1:8080/?workspace=investment&section=World%20models
```

In **Portfolio**, tune the household horizon, contribution, reserve, risk, and
tax-drag assumptions. The screen recomputes the sleeve frontier and shows exact
paper amounts for the broad-proxy control and every distinct admitted-security
challenger. Debt paydown remains a separate rival, and ranked opportunities
without instrument admission are shown at zero weight.

The initial scenario comes from the backend read model, so headless callers and
the screen start from the same inputs. Its chart shows the selected allocation's
median and tenth-percentile paths from the same public return, covariance,
haircut, and simulation-draw basis; there is no independent return assumption in
the primary chart. The **One answer matters most** card enumerates only the
declared horizon/contribution ranges, groups identical sleeve decisions, and
names the unresolved input that most reduces the remaining decision ambiguity.
Its finite-design percentages are not odds and do not activate a policy.

In **Overview**, `active paper` means a candidate-bound watch still owes the
shared admission transition. `Portfolio candidate` means that transition has
compiled against the current candidate and its public factor, covariance,
downside, fee, liquidity, and cost evidence; it still has zero weight until a
displayed household rival is selected.
The **Decision today** card names those current implementation candidates and
states the cash posture without requiring the detailed memo to be expanded.
The adjacent automatic-work card shows the currently leased research subject
when one exists. A waiting queue instead shows the next ranked candidate, the
number of candidate jobs still waiting, and the exact UTC budget reset. Only an
empty candidate lane falls back to the next scheduled source cycle. Equivalent
requests over one candidate and source-material basis are completed without a
subscription call; their queue history remains inspectable.

In the Portfolio implementation table, the candidate rules now answer three
different questions: what happens if every admitted security receives the same
satellite cap; which securities have a positive zero-alpha factor-return spread
over their own broad sleeve; and which have a positive cash-flow-implied return
spread over that sleeve. The latter two are selection hypotheses with no
realized-return claim. The table groups rules that currently produce identical
weights, while the frozen comparison retains every named rule for learning over
future candidate sets. Freeze it to test the complete policies against the
broad-sleeve control on later prices.

The first screen initializes the workspace if needed. The default path is
`projects/jaggedthoughts_capital/workspace/investment`; set
`ZTARE_INVESTMENT_WORKSPACE` to keep operator state elsewhere.

For the normal macOS setup, install the same foreground server as a login
service. It restarts after failure and owns the three scheduled workers:

```bash
./venv/bin/python scripts/public/control/jaggedthoughts_workbench_service.py install
./venv/bin/python scripts/public/control/jaggedthoughts_workbench_service.py status
tail -f ~/Library/Logs/JaggedThoughtsCapital/workbench.out.log
```

The launch agent receives the signed-in `codex` executable on `PATH`; it does
not configure an API key. Remove it with the same command and `uninstall`.

## The scheduled loop

1. **Scout broadly.** In Opportunities, ask for a market, fund, theme, or
   ticker. The workbench refreshes a broad equity/ETF catalog as needed,
   displays the compiled intent, evaluates every catalog identity, and returns
   a bounded enrichment queue. Select **Enrich** to add an equity to SEC and
   valuation analysis or a fund to price/factor analysis. Use **Edit recurring
   intents** to inspect `research_jobs/intents.yaml`.
2. **Let the due checkers run.** Starting the local server starts discovery,
   subscription research, and capital-cycle services. Discovery runs enabled
   broad scouts and compiles a diverse batch
   under the budgets in `research_jobs/enrichment_policy.yaml`, leases those
   jobs, enrolls the selected identities, and refreshes only the required
   public sources. Remaining call budget maintains unresolved request entities;
   sources outside the current bounded refresh retain their last admissible
   observations under the typed age gates. A failed dependency blocks its
   candidate. **Run
   enrichment cycle** is the explicit override.
3. **Inspect acquisition before underwriting.** The leaf-subscribed research funnel
   shows the pool, selected equities and funds, public-source calls, estimated
   research minutes, score components, diversity increment, rejection reasons,
   queue state, and typed blocks. Acquisition priority orders research spend;
   it does not estimate expected return.
4. **Inspect Opportunities.** The panels distinguish catalog eligibility from
   deep discovery status. They show schedule state, declared-scope
   closure, ranked equity/fund candidates, failed gates, valuation artifacts,
   and every automatic, requested, operator, or unavailable activation point.
5. **Research an evidence-ready request.** When `agent_research.enabled` is
   true, the server also starts a separate subscription consumer. It leases the
   highest-priority request, gathers public evidence through a web-only agent,
   and submits the strict dossier through the kernel. Use
   `$jaggedthoughts-capital-research` with a request path or candidate leaf for
   an explicit interactive run. Monitor equities and funds stop at
   `researched`. Only a qualified public equity may continue to
   `draft-candidate`.
   The current operator policy permits up to eight signed-in Codex attempts per
   day, runs one lease at a time, and requires a typed dossier or typed failure;
   it uses no OpenAI API key.
   The Prospective learning panel then joins the frozen acquisition score and
   cost to this transition. Pending requests remain censored; policy refitting
   stays disabled until the settled-pair gate is met.
   Future bounded enrichment cycles also pair coverage-first and
   disagreement-first research questions under the same dossier schema. The
   request records the assignment; the panel exposes complete dossier and
   economic pairs. This changes research order only and uses no API key.
   Accepted dossiers also create material-source monitor subscriptions. A later
   changed SEC Company Facts or configured issuer-fundamentals digest creates a
   dossier-local reassessment job in the same consumer. The Compounding
   research memory panel shows subscriptions, source-change events, reopen
   requests, and completed reassessments.
   For funds, inspect **Comparable-substitute frontier** in Opportunities. It
   displays non-dominated choices, factor-near substitutes, the current
   holdings overlap, constituent-evidence coverage, and links to normalized
   holdings and accepted review packets. **Acquire best cross-fund issuers** is
   the explicit override for the same transition now owned by the discovery
   service. On each due cadence it spends at most the `fund_lookthrough` limit
   in `research_jobs/enrichment_policy.yaml`, executes the exact displayed plan,
   records the SEC source-run and receipt hashes, and recompiles observed
   company-quality coverage. A same-day manual run makes the recurring owner
   wait rather than repeat the calls. Metric-repair cases stay visible and do
   not block the next new-issuer batch. A fund review stops at `researched` and
   cannot enter the equity draft lifecycle.
6. **Compile company strategy where evidence permits.** The research skill can
   author the typed industry/option profile and run `strategy-frontier`. Inspect
   global and local frontiers in the Strategy frontier view.
7. **Run a valuation execution tournament.** In World Models, select **Run live
   valuation tournament**. The latest operator decision supplies one frozen
   implied-growth task. Inspect the interpreter, direct reasoning, authored
   program, and verified-hybrid receipts; the authored program must pass three
   cases generated after the model responds.
8. **Create an explicit operator draft when needed.** Enter a ticker, company name, and initial
   thesis. An unconfigured ticker is resolved through the SEC registry and its
   public-source bundle is enrolled automatically.
9. **Edit the draft.** Review `profiles/drafts/<ticker>.yaml` and its source
   memo. Replace provisional beta, growth, rival mechanism, falsifiers, and
   decisive observation where the evidence warrants it.
10. **Activate for paper tracking.** Activation creates a separate active
   profile and decision identity, archives the draft, recompiles the bounded
   policy population, and routes compatible decisions into the portfolio
   frontier.
11. **Monitor the Shadow book.** The frozen decision remains pending until its
   horizon or falsifier matures.
12. **Settle from later prices.** Enter asset and benchmark prices, timestamps,
   and a cached receipt or archived export reference. The workbench creates the
   bound outcome, benchmark and no-action scorecard, and settlement transition.
13. **Inspect institutional learning.** In World Models, refresh the law state.
   The panel shows phenotype and outcome counts, the typed metric vocabulary,
   recursively enumerated program count and depth, dominance witnesses,
   strategy-to-return mechanism links, and the exact settled-block activation
   floor. Edit `institutional_learning/laws.yaml` to add a source-testable seed;
   generated candidates remain future-dated shadows.
14. **Inspect the capital cycle.** Overview shows the current opportunity book,
   underwriting/research/repair counts, paper posture, due forecast windows,
   learned-law influence, process owner, and exact next action. Only an eligible
   prospectively settled law can change research order; a counterexample removes
   that influence on the next cycle. The same server thread opens due
   90-day and one-year market-state blocks and refreshes their narrow public
   source bundle when issuance or settlement is due. Discovery rank orders
   research; only an active operator decision can carry paper weight.
   The same cycle freezes one 90-day complete-policy block whenever no compatible
   block is pending. World Models compares cash, equal weight, discovery rank,
   learned-law rank, and reviewed operator weights on the same future returns.
15. **Repeat.** A later source epoch creates new observations and screens. A
   changed subscribed material source also creates an evidence-delta
   reassessment; neither path rewrites the frozen dossier or decision.

The Capital UI reads the last atomically compiled `state/read_model.json`
immediately. Source refreshes and workspace transitions replace that projection
after they finish. Use **Refresh** or **Build** after editing workspace files
outside the workbench.

During source refresh, the disposable observation index is built on the
candidate stream before the canonical CSV is swapped. The prior read model
continues serving until a matching new source epoch is published. A strict
append may preserve the prior pointer only when its full published byte prefix
still hashes identically.

## CLI equivalents

### Refresh and review a fund

The scheduled discovery transaction refreshes every configured evidence source
for an admitted fund entity, including an issuer holdings adapter when one is
available. The explicit path is:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  --path projects/jaggedthoughts_capital/workspace/investment \
  discover --force

PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  --path projects/jaggedthoughts_capital/workspace/investment \
  submit-dossier research/dossiers/FNK-REQUEST_HASH.json

PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  --path projects/jaggedthoughts_capital/workspace/investment \
  capital-cycle --force
```

The first command emits the exact current request identity. The dossier must
bind that request and candidate leaf; a prior epoch is rejected. The resulting
opportunity book may say `fund_review_ready`. Once its exact candidate-bound
dossier is accepted, compile the inactive zero-weight proposal:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  --path projects/jaggedthoughts_capital/workspace/investment \
  fund-proposals
```

This writes `paper_proposals/funds/latest.json`. It retains cash and requires a
separate operator confirmation; portfolio admission and order routing remain
disabled.

Initialize, refresh, and inspect:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace init
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace universe-refresh
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  scout 'Identify mid-cap value funds for factor and earnings-power analysis'
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  scout-scheduled
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace refresh
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace enrichment-run
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace hydrate-strategy-cohort
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace capital-cycle --force
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace institutional-learning
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace market-state-cycle --refresh-sources
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace execution-market
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace status
```

For an unfamiliar theme, let the research agent author explicit catalog match
terms rather than extending kernel vocabulary. For example, save this JSON:

```json
{
  "entity_kinds": ["public_equity"],
  "capitalization": "mid",
  "theme_terms": ["aerospace", "defense"],
  "ranking_objectives": [
    "earnings_durability",
    "low_implied_growth",
    "industry_structure"
  ]
}
```

Then compile it through the same scout contract:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  scout 'Find US mid-cap aerospace and defense companies' \
  --intent-overrides /path/to/intent-overrides.json
```

The structured terms take precedence over convenience aliases. The resulting
receipt preserves the translation, evaluated population, rejection counts,
and excluded claims.

Run one due check or maintain the service outside the web server:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  discovery-service --once

PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  discovery-service --poll-seconds 300

PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  capital-cycle-service --once

PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  capital-cycle-service --poll-seconds 300
```

The discovery-service heartbeat includes `fund_lookthrough.status`, its exact
current plan hash, selected issuers, and next due time. `not_due`,
`source_budget_unavailable`, and `coverage_queue_exhausted` perform no source
calls. Portfolio and capital authority remain false.

Inspect or run the subscribed dossier consumer outside the server:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  research-agent-status

PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  research-agent --once

PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  research-agent --once --work-id WORK_ID

PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  research-agent --poll-seconds 60
```

The due checkers and research consumer are children of the workbench server.
Their SQLite queues and immutable artifacts survive process failure. The macOS
launch agent above keeps their owning server running while the UI is closed.
`--work-id` consumes one named queued item through the normal lease, capability,
attempt, and daily-budget checks. It is available only with `--once` and does not
bypass queue authority.

Submit every request-bound dossier so the job, request, candidate, and dossier
lineage becomes immutable:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  submit-dossier research/dossiers/TICKER-EPOCH.json
```

For a qualified public-equity leaf, turn that submitted dossier into an
inactive draft:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  draft-candidate CANDIDATE_LEAF_SHA \
  --dossier research/dossiers/TICKER-EPOCH.json
```

Enroll and draft a company:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  enroll-equity MSFT

PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  seed-equity MSFT 'Microsoft Corporation' \
  --thesis 'State the source-testable mechanism and price-implied disagreement.'
```

Enroll a fund from the scout queue and compile its factor watchlist row:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  enroll-fund AVMV 'Avantis U.S. Mid Cap Value ETF' \
  --category 'US mid-cap value'
```

Compile a source-authored company option space:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  strategy-frontier strategy_frontiers/mrvl-options.yaml
```

The seed receipt returns the exact `profile_id`. Use that value in the explicit
activation confirmation:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  activate jaggedthoughts.public-equity.msft \
  --confirmation 'activate jaggedthoughts.public-equity.msft for paper tracking'
```

Settle a matured paper decision without hand-editing its hash:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  settle-prices DECISION_ID \
  --observed-at 2027-08-09T20:00:00Z \
  --available-at 2027-08-09T21:00:00Z \
  --price MSFT=500 --price SPY=700 \
  --source-ref sources/raw/archived-price-receipt.json
```

Verify the golden store:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli store \
  --path projects/jaggedthoughts_capital/workspace/investment/state/golden_store.sqlite3 \
  verify
```

## Capability-adaptive valuation execution

The execution-market command invokes the current subscription runtime with no
separate API credential. It records runtime version, model selector, reasoning
effort, prompt-contract hash, source/evidence hashes, outputs, residuals,
latency, and provider artifacts. The current default uses the account-selected
Codex model at high reasoning effort.

Promotion is scoped to one task family and capability epoch. It requires 20
verified attempts over at least five distinct tasks at a 98% observed pass
rate. Set an explicit operational epoch only when you need to separate a known
runtime deployment:

```bash
export ZTARE_INVESTMENT_EXECUTION_CAPABILITY_EPOCH=2026-08-runtime-a
```

Changing the runtime/model/prompt contract changes the hashed executor identity
even when this label stays constant. One provider call supplies the direct,
authored-program, and hybrid modes; the receipt records that shared provenance.
Every result remains an analytical shadow and cannot alter paper or capital
state.

## Closed-book forecast blocks

Open a 90-day block from the latest operator decision:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  closed-book-open --horizon-days 90
```

The action freezes the source packet and zero-edge, momentum, valuation-policy,
and tool-sealed frontier forecasts before the end date. Repeating it for the
same entity, decision, issue date, and horizon returns the same episode.
Different entities issued on the same date against the same benchmark
and horizon share an inference block.

After a window ends, refresh public prices and settle every due block:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace sources
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  closed-book-settle
```

The World Models view shows the pending block and later scoreboard. Web-off
means the frontier call cannot retrieve fresh evidence; it does not erase facts
inside model parameters. Treat historical frontier replay as diagnostic and
use prospective settlements to judge the complete engine.

The primary ticker-level policy score is target paper weight multiplied by
benchmark-relative return, less frozen transaction cost. Full-book excess
return remains a comparison field. The separate complete-policy tournament
scores cash, equal-weight, discovery-priority, law-adjusted, and reviewed
operator weight vectors across one common universe; identical vectors count as
one trial.

Complete-policy settlements also reconcile each security's frozen weight delta
to its later benchmark-relative contribution. Cash and discovery compare with
equal weight; learned-law and reviewed-operator policies compare with
discovery. Follow the candidate and source references to see which question,
score, or eligible law caused the policy difference. Treat that as provenance
until another frozen policy varies the input independently.

For the market-wide ERP × term-spread lane, the explicit override is:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  market-state-cycle --refresh-sources
```

The command downloads current NYU ERP, a bounded no-key FRED CSV containing
T10Y3M/DGS3MO/DGS1/DFII10/T10YIE, and SPY adjusted prices. It emits a horizon only when due;
`--force` creates a new versioned shadow block for an intentional policy or
model comparison. Ordinary operation needs no command while the port-8080
server remains up. In **World models → ERP × term-spread state ledger**, inspect
the source epoch, joint forecast vector, shadow weight, unavailable challengers,
due-check state, and immutable run artifact.

The panel keeps several return notions separate. Cash-flow ERP is the index IRR
implied by price, payout, and growth minus a matched Treasury. Trailing E/P
minus TIPS, forward E/P minus nominal Treasuries, and dividend yield minus TIPS
are rival valuation diagnostics. Use the former as the primary total-return
expectation and the latter as interpretable state coordinates; later 90-day and
one-year settlements determine whether any deserves forecasting influence.

## Experimental model families

World-model tournaments compare frozen candidates on the same episodes through
the shared `ztare.worldmodel` interface. The probability-current/Lagrangian
adapter is deliberately outside the opportunity funnel:

```bash
PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace \
  market-flow
```

The default profile is a retrieval-history diagnostic. It can reject or narrow
a model family but cannot qualify one for paper use. Qualification requires a
distinct point-in-time profile, prospectively collected episodes, control
advantage after costs, linked-observable advantage, and later tournament
settlement.

## Public-data policy

- SEC filing facts use filing dates as availability boundaries.
- Nasdaq catalog fields are retrieval-time evidence. They support identity and
  coarse screening, not historical classification or valuation claims.
- FRED should use its vintage/realtime fields for historical work. The current
  market-state lane instead gives old CSV rows retrieval-time availability and
  uses them only prospectively.
- Current implied ERP and Yahoo chart history are retrieval-time sources; old
  rows are unavailable before the recorded retrieval.
- The market-state lane needs no provider key. Alpha Vantage and the separate
  FRED API adapter retain optional environment settings for other profiles.
- The observation CSV is append-only across refresh epochs. SQLite owns typed
  leaves and lineage; JSON and Markdown files are projections.
- A company screen does not establish competitive advantage, management
  quality, or normalized segment economics. Those remain explicit residuals.
- A factor candidate is not labelled undervalued until holdings-level or
  aggregate valuation evidence is present.

## Readiness interpretation

The Overview readiness cards report source consumption, active and draft
counts, fund and company screens, paper portfolio state, pending settlements,
experimental leaves, and store verification. `capital_authority` remains
`false` throughout this workflow.

## Freeze a household paper comparison

In **Portfolio → What could the investable portfolio reach?**, run the desired
scenario and inspect the complete paper implementations. Select **Freeze
one-year paper comparison** only when those displayed assumptions are the ones
you want the institution to remember. The response shows the immutable run ID
and horizon date. Later capital cycles bind the first common post-seal prices
and settle the rivals automatically; the button never sends an order.
