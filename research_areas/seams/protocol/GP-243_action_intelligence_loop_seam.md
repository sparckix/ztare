# GP-243, Action Intelligence Loop Seam

> **Seam metadata** · `seam_id:` GP-243 · `track:` protocol · `status:` active - 2026-05-19 · `last_updated:` 2026-05-20

## Status

Active, opened 2026-05-19 14:39:32 EDT

## ID

GP-243

## Eigenquestion

Can ZTARE turn forecasts, trajectory-mining signals, catches, and yield decompositions into a durable action-intelligence loop that improves future allocation decisions without letting a learned policy replace research judgment?

## Problem Statement

ZTARE has several mature measurement surfaces, but no first-class ledger that binds them into an action loop:

```text
context -> candidate actions -> selected action -> forecast/primitive evidence
-> execution outcome -> scientific-yield decomposition -> externalities
-> future routing/surfacing prior
```

The current forecast market can price actions and score outcomes. Trajectory mining can surface recurring primitives and failure patterns. GP-233 can explain scientific yield. The catch ledger can record negative externalities and false positives. But the system does not yet consistently record how these signals changed the next action, whether the change helped, and which future actions should be biased toward or away from the same pattern.

This gap is the missing "intelligence ledger": not another subjective insight file, but a typed action-impact record that makes organizational learning queryable.

## Scope

Covers:

- the glue layer between GP-230 forecast market state, GP-233 yield decomposition, trajectory mining, catch ledger, and RD/pre-tick behavior;
- an action-impact/intelligence ledger schema;
- shadow policy evaluation for forecast operations and trajectory-surfacing choices;
- RD/out-of-loop agent work at the autoresearch boundary, recorded as
  `domain=agentic_workbench` action-impact rows;
- read-only recommendations that can inform RD decisions without taking control of execution.

Does not cover:

- live LMSR market mechanics;
- live in-loop reinforcement learning that autonomously overrides RD choices;
- replacing GP-230 forecasts, GP-233, the catch ledger, or the prediction ledger;
- replacing autoresearch, factory-intelligence read models, or reflexive-mining emitters;
- optimizing a single scalar research reward.

## Existing Surfaces And Use Cases

| Surface | Current role | Action-intelligence use case |
|---|---|---|
| `analytics/public/forecast_pool/contracts/*.json` | GP-230 action contracts | Defines the decision point, layer, resolver, budget, value, risk, baseline action, counterfactual action, and externality hypotheses. |
| `analytics/public/forecast_pool/aggregates/*.json` | Market aggregate | Supplies `p_success`, expected cost, disagreement, failure-mode concentration, expected value, and allocation recommendation. |
| `analytics/public/forecast_pool/scores/*.json` | Proper scoring | Supplies probability calibration, effort error, failure-mode prediction quality, and high-confidence miss incidents. |
| `analytics/public/forecast_pool/decision_use/decision_use_ledger.jsonl` | Forecast consumption record | Should say whether a forecast was used to run, split, ask another independent agent, defer, kill, ignore, or override. Currently the weak link because it is not populated enough. |
| `analytics/public/forecast_pool/market_state/reflexive_insights.json` | Forecast-market read model | Surfaces market-owned nudges: thin independence, score debt, high-confidence misses, externality evidence, decision-use gaps. |
| `analytics/public/ledgers/action_intelligence/surfacing_event_ledger.jsonl` | Trajectory/primitives surfacing exposure and consumption record | Says which pattern, anti-pattern, trajectory cluster, GP-233 lever, or catch preconditioner was shown, and whether it was later consumed or suppressed. |
| `analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md` | Scientific-yield decomposition | Supplies reward-relevant factors: candidate supply, eligibility, verification compile rate, residual/closure rate, false accepts, wall time, current bottleneck, next lever, decision impact. |
| `analytics/public/ledgers/catch/catch_ledger.jsonl` | Ratified catches | Supplies negative externality labels, false-positive classes, missed-preconditioner classes, and mechanism-laundering incidents. |
| `analytics/public/ledgers/prediction/prediction_ledger.jsonl` | Legacy and tiered predictions | Supplies broader prediction history, but effort/cost fields require caution where telemetry is self-reported. |
| `analytics/public/ledgers/trajectory/trajectory_archive.jsonl` and enriched archive | Cross-project trajectory mining corpus | Supplies repeated failure basins, pivot patterns, primitive exposure, stagnation signals, and miner ROI candidates. |
| Factory-intelligence read models | Station/factory observability | Supplies bottlenecks, readiness, queue/source health, and recommendation surfaces for factory-shaped substrates; GP-243 consumes them as evidence, not as copied policy. |
| `domain=agentic_workbench` action-impact rows | RD/out-of-loop agent boundary | Records whether a persistent/subscription agent invoked autoresearch, prepared the missing surface, or bypassed it with a reason. |
| `scripts/public/control/rd_tick_brief.py` | Pre-tick surfacing | Natural place to show action-intelligence recommendations before RD commits to a route. |
| `scripts/public/control/start_tick.py` | Action boundary | Natural place to auto-record forecast decision-use once the key mismatch is corrected. |
| `scripts/public/mining/*` | Primitive and trajectory miners | Candidate source for surfacing arms: which primitive, anti-pattern, miner, or trajectory cue to show next. |
| `src/ztare/validator/core/information_yield.py` | Deterministic in-loop yield control | Source of loop-control state for later offline policy evaluation, not a live RL override. |
| `scripts/public/models/gflownet_data_extract.py` | Existing RL-like proof-search extractor | Evidence that historical action/outcome extraction is feasible, while also documenting small-sample and proxy-state limits. |

## Candidate Action Classes

The first action vocabulary should reuse GP-230's allocation actions:

- `run_now`
- `split_contract`
- `ask_another_independent_agent`
- `defer`
- `kill_branch`

The second vocabulary should cover trajectory/primitives surfacing:

- `surface_pattern`
- `surface_anti_pattern`
- `surface_trajectory_cluster`
- `surface_gp233_next_lever`
- `surface_catch_preconditioner`
- `suppress_surface_as_low_voi`

The third vocabulary should cover the autoresearch/RD boundary:

- `invoke_autoresearch`
- `prepare_autoresearch_surface`
- `run_out_of_loop_agent`
- `stay_out_of_loop`
- `record_negative_constraint`
- `repair_source_emitter`

Domain-specific action classes may be added only when the historical corpus has enough repeated decisions to evaluate them. GP-225-style proof repair/replay tasks are a better early target than NS theorem-frontier route choice because outcomes are more frequent and resolvers are more objective.

## Option Analysis

### Precondition: Not A Patchwork Layer Over Bad Compilation

The action-intelligence layer is justified only if it improves the pressure on
underlying emitters. It is not justified if it becomes a polite wrapper over
incomplete GP-230 decision-use rows, stale trajectory summaries, unstructured
GP-233 markdown, or catch rows that cannot be tied to later decisions.

The layer therefore needs a source-health gate:

- if decision-use rows are missing while forecast aggregates exist, the output
  must say the compilation surface is broken before issuing routing claims;
- if GP-233 rows cannot be matched to tick/project/contract identifiers, the
  output must preserve that as a linkage defect, not infer a reward;
- if trajectory/primitives surfacing cannot show later decision-use, the output
  must call the recommendation diagnostic only;
- if source hygiene is too weak, the correct recommendation is to repair the
  source emitter, not to add a smarter scoring layer.

This is the discrimination criterion: GP-243 is valid when it makes source
compilation defects more visible and cheaper to repair. It is invalid when it
normalizes those defects behind another dashboard.

### Option A: Keep Current Ledgers Separate

Pros: no new artifact, low implementation cost, avoids premature learning machinery.

Cons: preserves the current gap. The apparatus can know that a forecast was scored, a catch was ratified, and a GP-233 row moved a bottleneck, but cannot query whether a decision policy improved because of those signals.

Verdict: insufficient.

### Option B: Add An Action-Impact / Intelligence Ledger

Pros: binds context, candidate actions, selected action, policy source, forecast state, yield outcome, catches, and counterfactual notes. Gives later audits a durable training/evaluation table without changing live behavior.

Cons: another ledger can become bookkeeping unless most rows are produced automatically at action boundaries.

Verdict: recommended.

### Option C: Add Shadow Bandit / Off-Policy Evaluation

Pros: lets ZTARE evaluate whether forecast-operation and surfacing policies would have improved allocation, without letting a model control live RD work. This matches the repeated-decision structure of forecast operations and trajectory surfacing.

Cons: needs careful sample-size gates, confidence intervals, and externality penalties. It is not appropriate as a live optimizer for sparse, delayed, high-stakes NS decisions.

Verdict: recommended after Option B exists.

### Option D: Live Mini-RL In The Research Loop

Pros: could adapt quickly in repeated low-risk micro work.

Cons: high Goodhart risk, unsafe exploration, delayed rewards, nonstationary objectives, and local optimization externalities. It would also blur the RD's accountability boundary.

Verdict: explicitly out of scope for v0.

## Research Grounding

Prediction markets are useful because they aggregate distributed beliefs into scored probabilistic estimates. Wolfers and Zitzewitz summarize the empirical and theoretical case for prediction markets as information aggregation mechanisms: <https://www.nber.org/papers/w12083>.

Bandit methods are useful when the system faces repeated allocation choices with observable outcomes and opportunity cost. Google's online-service bandit experiments are a relevant applied frame: <https://research.google/pubs/multi-armed-bandit-experiments-in-the-online-service-economy/>.

The safety constraint is equally important. Amodei et al. identify side effects, reward hacking, scalable oversight, safe exploration, and distribution shift as core risks for learned optimization systems: <https://arxiv.org/abs/1606.06565>.

Goodhart pressure is directly relevant because any scalar "research yield" proxy can become the target rather than the thing meant to be measured. OpenAI's Goodhart discussion is the relevant caution: <https://openai.com/index/measuring-goodharts-law/>.

The systems constraint is that learned decision layers add hidden dependencies and feedback loops. Sculley et al.'s ML technical debt paper is the relevant warning: <https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf>.

## Recommendation

Open a downstream spec for a conservative v0:

1. Add an action-intelligence ledger/read model that consumes GP-230 decision-use rows, forecast aggregates/scores, GP-233 evidence rows, catch rows, and trajectory-mining summaries.
2. Fix the forecast decision-use capture path before any shadow policy is trusted.
3. Add a `SurfacingEvent` source ledger before claiming trajectory/primitives
   surfacing consumption. Consumed or explicitly suppressed events may derive
   trajectory-surfacing action-impact rows; shown-only events remain exposure
   records.
4. Generate shadow recommendations for two first domains only:
   - forecast operations: whether to run, split, ask another independent agent, defer, or kill;
   - trajectory/primitives surfacing: which pattern, anti-pattern, trajectory cluster, GP-233 lever, or catch preconditioner to surface.
5. Surface recommendations in RD pre-tick briefs as advisory evidence with provenance and confidence, not as execution commands.
6. Add typed `record-agentic-work` and `record-agentic-route` surfaces so
   RD/Codex/Claude labor can be compared later with in-loop autoresearch and
   prepared-but-not-run surfaces. Prefer `record-agentic-route` when the
   router JSON exists, so the row carries the exact route artifact ref instead
   of a reconstructed summary.
7. Keep live bandit/RL control out of scope until the ledger has enough resolved action-impact rows per domain and externality penalties are demonstrably working.

## Open Questions

1. Should the action-intelligence ledger live under `analytics/public/forecast_pool/` because GP-230 owns allocation, or under `analytics/public/ledgers/action_intelligence/` because it binds multiple primitives?
2. Should v0 parse GP-233 evidence from markdown rows, or require future GP-233 emitters to write JSONL alongside the markdown ledger?
3. What minimum sample size should a domain require before a shadow recommendation can be labeled anything stronger than `diagnostic_only`?
4. Should trajectory surfacing arms be hand-authored initially, or inferred from existing miner outputs?

## Debate Log

### Turn 1, Codex (2026-05-19 14:39:32 EDT), Opened action-intelligence loop seam

The immediate finding is that ZTARE does not need a live RL system first. It needs the missing binding object between existing evidence surfaces and future allocation decisions.

The repo already has the components: GP-230 forecasts and scores, GP-233 yield rows, catch ledger rows, trajectory archives, reflexive insights, and pre-tick surfacing. The missing artifact is a typed record of action impact. Without it, each primitive can be locally useful while organizational learning remains hard to query.

The seam therefore recommends a spec for an action-intelligence ledger and shadow policy evaluator. The evaluator should start with forecast operations and trajectory/primitives surfacing because those are repeated, instrumented, and low-risk relative to live NS route selection. Live mini-RL control remains out of scope for v0.

### Turn 2, Codex (2026-05-19 14:49:00 EDT), Anti-patchwork gate added

The principal raised the harder failure mode: an "intelligence layer" can be a
patch over poor compilation rather than an improvement in organizational
learning.

Accepted. GP-243 must not hide bad source hygiene. Its first obligation is to
surface compilation defects: missing decision-use rows, weak GP-233 linkage,
unconsumed primitive surfacing, stale trajectory miner outputs, and catches that
cannot be tied to later action. If those defects dominate, the recommendation is
source-emitter repair, not policy learning.

### Turn 3, Codex cold review (2026-05-19 15:02:00 EDT), Accept with required fixes

Claude CLI review was unavailable in this session because the subscription/API
path failed, so a cold Codex adversarial review was run instead. Verdict:
`ACCEPT_WITH_REQUIRED_FIXES`.

Required fixes accepted before implementation:

1. GP-243 must not reimplement GP-230 allocation. It consumes GP-230
   `allocation_recommendation` and evaluates decision use.
2. The spec needs controlled per-domain action vocabularies and a mapping from
   GP-230 `used_for` values to GP-243 action names.
3. Trajectory/primitives surfacing is diagnostic-only until surfacing
   consumption events exist.
4. GP-233 markdown parsing may only support diagnostic linkage. Non-diagnostic
   claims require structured identifiers.
5. `source_health.json` needs severity, denominator, observed/expected counts,
   freshness, affected domains, and scoped blocking rules.
6. Shadow/off-policy evaluation needs logged-policy metadata before any learned
   policy claims.
7. Hard invariants must forbid GP-243 from writing GP-230 contracts/outcomes/
   scores or changing RD routes.
8. Smoke fixtures must cover missing decision-use, weak GP-233 linkage, stale
   trajectory outputs, unconsumed surfacing, live `shadow_policy` rejection,
   `ignore/override` without reason, and source-health repair recommendations.

Implementation is therefore narrowed: first ship source-health and action-impact
materialization; keep forecast-ops and trajectory-surfacing recommendations
advisory and diagnostic until consumption evidence exists.

### Turn 4, Codex (2026-05-19 15:00:00 EDT), Observer-only v0 implemented

Implemented the narrowed v0:

- `scripts/public/control/action_intelligence.py` materializes source health,
  action-impact rows, and shadow recommendations.
- `scripts/public/control/start_tick.py` now reads
  `allocation_recommendation.action` with legacy fallback to `recommendation`.
- GP-243 writes:
  - `analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl`;
  - `analytics/public/action_intelligence/state/action_intelligence.json`;
  - `analytics/public/action_intelligence/state/shadow_recommendations.json`;
  - `analytics/public/action_intelligence/state/source_health.json`.

No default RD pre-tick disturbance was added. GP-243 remains observer-only until
the action-impact and surfacing-consumption rows prove useful enough to justify
operator/RD opt-in.

Current materialized source-health verdict: diagnostic-only. There are forecast
aggregates but no decision-use rows, so forecast-ops recommendations are capped
behind `repair_source_emitter`. Trajectory/primitives surfacing is also
diagnostic-only because surfacing consumption is not yet instrumented.
