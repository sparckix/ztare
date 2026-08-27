---
name: jaggedthoughts-capital-research
description: Scout broad public-equity or ETF universes from natural-language market requests, deepen a JaggedThoughts Capital candidate with current primary-source evidence, compile company strategy-option frontiers, write typed research dossiers, and submit eligible public-equity candidates as inactive underwriting drafts. Use for market opportunity searches, fund comparisons, ticker underwriting, industry and strategy-choice analysis, rival theses, or converting a ranked discovery result into a paper-review draft. Do not use for order execution or paper activation.
---

# JaggedThoughts Capital Research

Use the typed scout or candidate leaf as the quantitative boundary. The kernel owns identity, point-in-time data, factor estimates, valuation programs, recursive strategy programs, ranking, lineage, and lifecycle transitions. This skill translates open-ended language, gathers qualitative evidence, and submits typed artifacts back through the kernel.

## Intake branch

- For a broad request such as “find mid-cap value funds” or “screen durable software companies,” run:

  `PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace --path <workspace> scout "<request>" --refresh-catalog --max-results 50`

  Inspect `intent` before research. State any translation that would materially change the universe. Treat catalog rows as an enrichment queue, not as opportunities.
- The natural-language compiler covers common capitalization, style, security-kind, and catalog aliases. For an unfamiliar industry or thematic request, do not add a domain label to kernel code. Write a small JSON object containing open `theme_terms` and, where needed, explicit `entity_kinds`, `countries`, or `ranking_objectives`; rerun the scout with `--intent-overrides <json-path>`. The resulting intent receipt is the audit surface for the agent's translation.
- Recurring searches belong in `<workspace>/research_jobs/intents.yaml`. The discovery service executes enabled entries on their declared cadence. The autonomous enrichment cycle then selects a diverse, budget-feasible subset, enrolls public sources, runs discovery, and emits immutable research requests. Edit policy for a new recurring mandate; do not make it an implicit skill default.
- When `agent_research.enabled` is true in the enrichment policy, each evidence-ready request leaf is subscribed into a separate leased queue. The process-local consumer invokes this dossier contract through the configured subscription CLI and submits the result through the kernel. `workspace research-agent-status` exposes its process owner, daily budget, queue, and last action. Manual invocation remains valid and converges on the same request/dossier identity.
- Before an activation-research browsing call, the consumer runs a separate web-disabled subscription role that freezes the complete thesis × rival × null by frontier-program response matrix. A frozen execution assignment then names either the incumbent or matrix-selected program. Treat both artifacts as immutable, copy `response_matrix_execution` exactly, and return outcomes only for its executed atoms; never revise forecasts after browsing or call uniform disagreement a posterior probability. The kernel owns assignment, pricing, settlement, and policy learning.
- If a frozen committee assigns exactly zero predictive mass to its later
  source-bound response, the consumer may open a new hypothesis-set epoch. The
  successor must change at least one mechanism, freeze another complete response
  matrix without web access, and queue only the matrix-selected program for public
  evidence. Research every declared atom exactly once and do not browse a different
  question. Another zero-mass response may repeat this transition up to depth three;
  a compatible response schedules the next posterior-ranked unobserved program until
  the declared frontier is exhausted. The chain never grants paper-policy,
  portfolio, or capital authority.
- The same consumer automatically queues a matured strategy-outcome contract as a distinct high-priority job. It may retrieve the later primary documents, but it cannot alter the frozen move, metric, unit, horizon, or comparator; success converges on `workspace strategy-outcome`.
- Every accepted dossier whose exact request is a qualified public equity, or a
  monitor-state public equity explicitly routed as `strategy_learning`, also
  activates a separate `jaggedthoughts_strategy_frontier_research` job. This
  synthesis has web access disabled and may cite only source ids already admitted
  by the dossier. It proposes the existing strategy-option YAML AST; the kernel
  enforces company/dossier/evidence identity, typed mechanisms, ordinal generated
  effects, source closure, bounds, and a residual representation audit before the
  existing Z3 compiler may enlarge the move library. Do not create another
  strategy ontology or bypass a schema failure with a permissive adapter. When
  the request carries `prior_representation`, preserve option ids for unchanged
  business choices and explain any rename, split, merge, addition, or removal in
  the representation residuals. The prior is a stability aid, never a source.
  A strategy-learning frontier cannot create a draft or position. When the source
  request carries `strategy_event_trigger`, return the required move-bound event
  assessment described in [references/dossier_contract.md](references/dossier_contract.md).
  The option compiler must map it to at most one exact implementation event or
  retain `strategy_event_unmapped:<move_sha256>` in representation residuals. Its
  bound operating and return forecast hashes are evaluation lineage only; never use
  their predictions or later outcomes to author the thesis or scenario effects.
- Exact strategy adoptions also compile a market-cap-neighbour peer plan inside the same industry. Run `workspace hydrate-strategy-cohort` to enroll the selected peers and acquire SEC Company Facts histories. The subscription consumer then separates exact-phenotype adoption, broader-family treatment, bounded no-family observation, and source gaps. A family-only event is excluded from the focal panel but cannot serve as a control; a bounded negative search is only a provisional not-yet-treated classification.
- For a named ticker that is absent from the workspace, run `workspace enroll-equity <TICKER>`. The built-in SEC application identity is sufficient; do not ask the user for `ZTARE_SEC_USER_AGENT`. Then run `workspace discover --force`.
- For a named discovery leaf or ranked candidate, continue at step 2 below.

## Workflow

1. Resolve the investment workspace. Default to `projects/jaggedthoughts_capital/workspace/investment`, or honor `ZTARE_INVESTMENT_WORKSPACE` / the user's explicit path.
2. If the user did not name a leaf, run `PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace --path <workspace> status`. Prefer the highest-priority row in `research_requests` whose `lifecycle_stage` is `evidence_ready`; it already binds the selection score, source budget, job lease, candidate leaf, and requested measurements. Skip `covered_by_prior_dossier` rows: the kernel has already bridged their qualitative evidence under current material-source hashes. Skip `awaiting_source_reassessment` rows until the local delta job settles. If no request exists, select only from `discovery.latest_run.candidates` and retrieve its leaf SHA from `discovery.latest_record.candidate_leaves`. State the quantitative gates and evidence gaps that determine the selection; catalog order and acquisition priority are not expected-return estimates.
3. Read the exact leaf with `PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli store --path <workspace>/state/golden_store.sqlite3 show <leaf_sha256>`. Stop if it is not a `discovery_candidate`, is not a public equity, or its epoch differs from the current source epoch.
4. Treat the leaf's metrics and valuation envelope as frozen calculations. Do not replace them with arithmetic in prose. Inspect `valuation.artifact_path` and source receipts when a numeric result needs explanation.
5. Honor `research_policy_assignment` and `research_question_frontier` when present. The latter is a frozen typed program selected from a scope-closed question frontier; follow its selected question and source plan in the declared order. Coverage-first and thesis/rival disagreement-first may order the same probes differently, but neither arm may remove a dossier section or change the quantitative boundary. Requests outside the prospective comparison still use the common contract.
6. Browse current evidence because filings, management, industry structure, and price-sensitive context change. Prefer primary sources: SEC filings, company investor materials, regulator or government datasets, contractual disclosures, and issuer documents. Use academic or institutional research for methods. Record title, URL, publication date, accessed time, evidence role, and the claim supported. Distinguish retrieved fact from inference.
7. Build a choice-system analysis: industry boundary and customer need; customers, suppliers, rivals, entrants, substitutes, and complements; profit-pool distribution; changes in these forces; choices, tradeoffs, reinforcing edges, likely responses, and local moves that could change the earnings frontier. Every reinforcing edge must use exact ids declared in `strategy.choices`; do not put prose labels in `from` or `to`. Keep the graph at eight choices or fewer so the kernel can canonicalize it up to node naming. Separate measured accounting durability from competitive durability.
   Record a feasibility constraint only when an opened primary source explicitly supports mutual exclusion, a prerequisite, or a numeric common-unit resource bound. Put `strategy_constraint:<constraint_id>` in each cited source's `supports`; qualitative tension remains a tradeoff rather than a solver predicate.
8. If at least two evidence-backed strategic responses can be expressed with scenario consequences, write a strategy-option YAML following [references/strategy_options_contract.md](references/strategy_options_contract.md), then compile it:

   `PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace --path <workspace> strategy-frontier <workspace-relative-profile>`

   When a proposed bundle is rejected or its compatibility is unclear, invoke
   `workspace strategy-explain <compiled-frontier.json> <option-id>...` and
   report the exact violated predicate IDs and operands. Do not reinterpret a
   solver rejection in prose or treat feasibility as evidence that the authored
   option effects describe the business.

   Optionally compile one commitment-plus-recourse policy only when the frozen
   dossier supplies an irreversible commitment, a public numeric trigger and
   clock, a labelled threshold basis, and at least two feasible final bundles.
   Otherwise omit it; never create a contingent policy merely to exercise Z3.

   When `recourse_not_before` has passed and every exact metric is available,
   put the point-in-time observations in the typed recourse-request shape and
   invoke `workspace strategy-recourse <request.json>`. This selects one
   already-certified branch and records policy/selection lineage; it does not
   authorize an operating action or capital allocation. Do not invoke it with
   forecasts, incomplete metrics, revised units, or observations unavailable at
   the stated decision time.

   Report global-frontier programs, local-only peaks, force coverage, constraint witnesses, and representation residuals. Add a typed mechanism only when its action, economic bridge, implementation conditions, and break conditions are evidenced; retain the company-specific object outside the reusable signature. Add an implementation event only when a public source dates execution; preserve first public observation as interval-censored timing rather than calling it the adoption date. The autonomous event-refinement leaf may later search filings and issuer materials for an exact operational or completion date; its separate receipt supplements causal timing without rewriting the authored move. When a move has publicly measurable operating consequences at independent clocks, add separate `leading_operating` and `terminal_operating` contracts with exact metric, unit, direction, materiality threshold, horizon, comparator, acquisition mode, and sources. Use `point_in_time_observation` for typed public metrics already acquired by the source engine and `subscription_primary_document` for a later bounded filing retrieval. A leading contract cannot settle terminal earnings, security return, or causal credit. Leave contracts absent and name the measurement gap when segment or product disclosure cannot settle them. Never invent consequence deltas or outcome metrics to make the compiler run. When a frozen horizon has elapsed and the named public evidence is available, submit the JSON outcome through `workspace strategy-outcome <workspace-relative-outcome-path>`. The kernel rejects early observations, unit drift, unbound moves, and undeclared comparators, then rebuilds the move library and golden-store projection.
9. Ensure `<workspace>/research/dossiers/` exists, then write a JSON dossier there following [references/dossier_contract.md](references/dossier_contract.md). Bind `request_id`, `request_sha256`, `candidate_leaf`, `candidate_sha256`, `entity_id`, and `as_of` exactly when the work began from an agent request. Include a thesis, strongest rival view, decisive observation, falsifiers, catalysts, strategy map, industry analysis, valuation assumptions, sources, and the strategy-frontier artifact when one was compiled.
   When the immutable request contains `strategy_event_trigger`, include exactly one
   `strategy_event_assessment` with the trigger's move and event-request hashes. Cite
   only opened sources whose `supports` contains
   `strategy_event:<move_observation_sha256>`. Keep the event as research context;
   do not alter rank, candidate state, or authority.
   Inspect `strategy_event_learning_units` before reporting progress. It is the
   canonical event clock across discovery, request currency, dossier, formal
   frontier, operating settlement, and return settlement. A superseded request
   means no current research exists; use only the exact-current successor emitted
   by the ordinary compiler. The unit does not score itself: its aggregate
   tournament references retain inference and promotion ownership.
10. Submit every request-bound dossier through the kernel so its bytes, request lineage, and `researched` transition are recorded:

   `PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace --path <workspace> submit-dossier <workspace-relative-dossier-path>`

   Submission also advances the prospective acquisition-learning row for that exact request. Pending requests remain censored, and the skill cannot authorize a score-policy refit.

   For a monitor, blocked, or fund candidate, stop after this transition and report the failed gates; the dossier may inform a later source epoch but cannot relabel the candidate.
11. For a qualified public-equity candidate only, create the inactive underwriting draft:

   `PYTHONPATH=src ./venv/bin/python -m ztare.investment.cli workspace --path <workspace> draft-candidate <leaf_sha256> --dossier <workspace-relative-dossier-path>`

12. Verify that the result contains `candidate_lineage_edge`, `decision_leaf`, `stage: draft`, and `required_operator_transition: review_and_activate`. Report the profile and memo paths. Do not invoke `workspace activate`.

## Research standard

- The thesis must specify the causal bridge from strategic choices to durable owner earnings and from market expectations to prospective return.
- The rival view must explain the same observations with a different mechanism.
- A decisive observation must discriminate between the thesis and rival within a stated horizon.
- Falsifiers must be observable and time-bounded.
- State where the formal valuation frontier is sensitive to beta, growth, terminal growth, earnings normalization, debt, or share count.
- For a monitor or blocked candidate, research the named evidence gap; do not upgrade its status in prose.
- The result is decision support. Never claim brokerage or capital authority.

## Institutional learning contribution

When the research question is meant to transfer across companies, funds, or
industries, inspect `<workspace>/institutional_learning/laws.yaml` and the
current `institutional_learning/latest.json` before proposing another rule.

- Reuse an existing law when its mechanism, outcome, entity kind, horizon, and
  cohort match. Add a new version only when one of those identities changes.
- A predictive law needs an executable signal AST over registered or
  point-in-time phenotype metrics. A causal law needs source-bound panel rows
  with schema `jaggedthoughts-causal-panel-row-v2`; every treated row binds an
  exact implementation-event hash, adoption period, metric, source observation,
  and availability time. Never convert an analyst narrative into treatment
  labels without dated evidence.
- Inspect `institutional_learning/strategy_cohorts/latest.json` and
  `panel-readiness.json` before adding controls by hand. The cohort compiler
  groups focal moves by mechanism phenotype × industry, acquires selected peer
  histories, and writes the filing-bounded durability panel automatically.
  Exact phenotype requires the same strategy form, addressed-actor profile,
  implementation mode, and operating-object scope. A commitment or still-
  executing program is not an operational treatment date. Subscription
  classifications may feed the diagnostic panel, while law promotion and
  capital authority remain disabled.
- State antecedent and consequence concepts so the mechanism graph can connect
  strategy-choice consequences to earnings, return, and paper-policy inputs.
- Inspect `research_memory.strategy_phenotypes` before proposing a cross-company
  mechanism. A repeated topology is a challenger prompt only: identify the
  source-bound semantic mechanism and a later earnings consequence that would
  distinguish transfer from superficial graph resemblance.
- Inspect `strategy_move_learning.moves`, `mechanism_phenotypes`, and
  `move_families` before naming a reusable strategy move. Families generate
  transfer questions; phenotypes select comparable histories; exact moves own
  company object, conditions, break cases, event, and sources. An operating-
  outcome episode evaluates the business move; the closed-book security return
  evaluates the investment. Do not infer one from the other.
- When multiple recursive programs share at least two exact option events, the
  kernel queues a distinct integrated-program adoption request. Treat the option
  events as anchors only. Exact program adoption requires an exact operational or
  completed event for every constituent and an opened primary source linking the
  choices as one coordinated program. A program-adoption result still cannot claim
  program success, security return, portfolio weight, or capital authority. An exact
  result automatically freezes only the operating-contract signatures already shared
  by at least two constituent moves; do not propose a new metric or backdate its
  measurement clock. The resulting readout is descriptive until comparison and
  transfer evidence earn stronger credit.
- Exact implemented phenotypes lower automatically into versioned causal-law
  candidates through `workspace institutional-learning`. Inspect their generation
  receipts and evaluation rather than hand-authoring a duplicate strategy law.
  A mechanism-graph path through `earnings_durability` is a test sequence, not
  evidence that either the business move or later return law is supported.
- Run `workspace institutional-learning` after an authorized catalog or panel
  edit. Report its phenotype count, inference-block count, counterexamples,
  recursive search scope, and next activation.
- Do not hand-score a current candidate from a learned law. The capital-cycle
  compiler re-executes only promotion-eligible association ASTs, bounds their
  research-priority influence, and withdraws it after a counterexample. It
  cannot change screen state, weight, or capital authority.
- A generated formula begins after the sample that selected it. The skill may
  propose the conjecture and gather the next evidence; it cannot mark the law
  supported or change portfolio authority.
- A complete-policy settlement may trace a frozen weight delta back to this
  request, its sources, question, and eligible laws. Treat the contribution as
  decision-path accounting. Do not assign causal research or source credit
  unless a matched prospective policy varied that input separately.

## Market return and ERP boundary

When comparing market valuation or hurdle rates, name the object. Use the
cash-flow-implied index IRR minus a matched Treasury as the primary expected
total-return ERP. Keep trailing E/P minus TIPS, forward E/P minus nominal
Treasuries, and dividend yield minus TIPS as separate diagnostics because they
omit different growth, payout, buyback, and terminal-value components. Preserve
all methods in a prospective market-state block when the question is which one
forecasts later excess return.

## Model research activation branch

When `market_state.model_research_activations` is nonempty, consume the exact
`activation_sha256`; never infer an activation from a chart or a rejected
project alone. Verify that no successor or retirement artifact already names
that activation.

- For `successor_research_due`, author a new evidence-project identity whose
  charter binds `parent_model_identity_sha256`, the activation and tournament
  hashes, the prediction-changing restriction, the same-information rival, and
  the prospective target. Reusing a model id or changing only its prose is not
  a successor.
- For `retire_research_due`, write a retirement proposal for the exact model
  identity and activation. Do not delete its project, results, forecasts, or
  settlements.
- A Lagrangian successor must expose an executable stationary response and
  action derivative. Its deterministic harness checks stationarity, declared
  convexity, mass/positivity, and equality between the action-derived response
  and the prediction. It must also face a fitted monotone odd calibration of
  the same current; a physics label cannot earn incremental credit.
- Both routes remain research proposals. They cannot mutate an incumbent model,
  alter a settled outcome, activate a paper policy, or obtain capital authority.

## Fund boundary

Fund candidates support broad catalog discovery plus configured factor and aggregate-valuation screening. Compare exposure, benchmark fit, fees, liquidity, rebalance mechanics, holdings concentration, tax fit, and portfolio valuation from issuer or regulatory evidence. Do not send a fund leaf to `draft-candidate`; produce a research dossier against its exact request and candidate identities.

After submitting an exact qualified-fund dossier, run `workspace fund-proposals`.
The kernel joins the current candidate, watchlist, factor analysis, holdings
graph, and dossier into an inactive cash-only zero-weight proposal, or reports
the exact missing/stale identity. Stop there: do not invoke fund activation,
portfolio admission, or order execution. Do not interpret trailing return or
residual alpha as valuation.
