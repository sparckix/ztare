# GP-233 Research Yield Decomposition Seam

> **Seam metadata** · `seam_id:` GP-233 · `track:` apparatus · `status:` `v1-open` - opened 2026-05-13 as a general-purpose instrumen · `last_updated:` 2026-05-13


## Status

`v1-open` - opened 2026-05-13 as a general-purpose instrumentation and orchestration seam.

GP-231 was already assigned to `research_areas/seams/mission/org/GP-231_mcp_third_party_app_bridge_seam.md`; GP-232 was also assigned. This seam therefore uses GP-233.

This seam records a contract. It names the minimum field set that lets an orchestration tick explain why a research process produced usable scientific yield, where yield was lost, and what lever should be pulled next. No code ships directly from this seam until one consumer needs a validator, indexer, or dashboard slice.

## Eigenquestion

When a research process consumes candidates, verifier time, and agent attention, can the apparatus decompose scientific yield into enough factors to say whether the next lever is more supply, better eligibility, faster verification, stronger residual labeling, or a different decision policy?

## Framing

Throughput is a coefficient in scientific yield. The remaining factors decide whether speed becomes usable science or merely faster motion.

A fast process that creates many unverifiable candidates has low scientific yield. A slow process that creates a small number of decision-changing verified residuals can have high scientific yield. The seam therefore records throughput alongside the factors that make throughput meaningful:

```
scientific_yield_signal =
  candidate_supply
  * eligibility_rate
  * verification_compile_rate
  * residual_or_closure_rate
  * decision_impact
  / wall_time_or_cost
```

This formula is an orientation device, not a single scalar KPI. `decision_impact`, `current_bottleneck`, and `next_lever` remain typed fields because collapsing them into one score would hide the reason the next move changed.

## Contract

Every artifact or orchestration tick that claims a research lane is ready, blocked, saturated, underpowered, worth scaling, worth killing, or worth dispatching should attach a `research_yield_decomposition` object.

Required properties:

1. It must preserve the funnel: raw candidates -> eligible candidates -> verifier-compiled rows -> residual or closure rows -> decision.
2. It must name the current bottleneck and next lever in operational vocabulary.
3. It must distinguish "not run yet" from zero. A static prefilter with no compile run uses an explicit sentinel such as `not_run_static_prefilter`, not `0`.
4. It must cite the source artifact and prediction row when the decomposition gates a decision.
5. It must be cheap enough to emit in ordinary artifacts, not only in large reports.

## Field Schema

```json
{
  "research_yield_decomposition": {
    "candidate_supply": 0,
    "eligibility_rate": 0.0,
    "verification_compile_rate": 0.0,
    "residual_or_closure_rate": 0.0,
    "verified_residual_labels": 0,
    "audited_true_false_accepts": 0,
    "wall_seconds": 0.0,
    "cost_units": null,
    "verified_residual_labels_per_minute": 0.0,
    "decision_impact": "typed_decision_summary",
    "current_bottleneck": "typed_bottleneck",
    "next_lever": "typed_next_action"
  }
}
```

### Required Fields

| Field | Meaning | Validation rule |
|---|---|---|
| `candidate_supply` | Count of raw candidates considered by the lane after initial source selection. | Non-negative integer; denominator for `eligibility_rate`. |
| `eligibility_rate` | Fraction of candidates that pass context, format, source, or task eligibility filters. | `eligible_count / candidate_supply`, or explicit sentinel if not applicable. |
| `verification_compile_rate` | Fraction of eligible rows that pass the verifier or compile check. | `verified_or_compiled_count / eligible_count`; never use for unrun static filters. |
| `residual_or_closure_rate` | Fraction of compiled rows that become action-unique residual labels, closure labels, or equivalent scientific objects. | Must state denominator in artifact prose if denominator is not compiled rows. |
| `verified_residual_labels` | Count of verified labels that survived the lane's false-accept audit. | Integer or explicit sentinel. |
| `audited_true_false_accepts` | Count of false accepts found by the audit. | Integer or explicit sentinel; `0` means audited and none found. |
| `wall_seconds` | Wall time consumed by the measured lane. | Number; `0` only if no runtime verifier ran. |
| `verified_residual_labels_per_minute` | Throughput coefficient after verification and audit. | Derived from labels and wall time, or explicit sentinel. |
| `decision_impact` | What decision changed because of the decomposition. | Short typed string, not narrative prose. |
| `current_bottleneck` | The factor currently limiting scientific yield. | One of the local controlled terms or a documented extension. |
| `next_lever` | The next action implied by the bottleneck. | Must be actionable by an orchestrator tick or human operator. |

Optional but recommended fields:

| Field | Meaning |
|---|---|
| `cost_units` | Agent-minutes, GPU-minutes, API dollars, context-window budget, or other cost denominator when wall time is not the scarce resource. |
| `source_artifact` | Path to the artifact that emitted the decomposition. |
| `prediction_id` | Prediction-ledger row that priced the decision before resolution. |
| `lane_id` | Stable lane name such as `public_trace_prefiltered_replay`, `source_body_harvester`, or `proof_repair_dispatch`. |
| `measurement_scope` | `static_prefilter`, `compile_verifier`, `human_audit`, `orchestration_tick`, or equivalent. |

## Bottleneck Vocabulary

Start with this controlled vocabulary and extend only when needed:

| Bottleneck | Meaning | Typical next lever |
|---|---|---|
| `candidate_supply` | Too few raw candidates to support a downstream decision. | Expand source harvest, broaden source family, import another dataset. |
| `candidate_eligibility_supply` | Enough raw candidates exist, but too few survive eligibility filters. | Improve context harvesting, repair parser/source-body extraction. |
| `verification_compile` | Eligible candidates do not compile or verify often enough. | Repair harness, add deterministic wrappers, reduce target mismatch. |
| `residual_label_quality` | Compiled rows do not produce enough usable residual or closure labels. | Tighten label taxonomy, add stronger decoys, audit label semantics. |
| `false_accept_audit` | False accepts contaminate the apparent yield. | Strengthen decoy audit, freeze normalizer, inspect accepted rows. |
| `decision_policy` | Metrics are adequate but do not map to a clear next decision. | Write decision thresholds before running the next lane. |
| `wall_time_or_cost` | Yield is adequate but too slow or expensive. | Parallelize, cache, lower model tier only after quality gate holds. |

## Integration Points

### Prediction Ledger

Use PATTERN-012 when the decomposition gates a typed action:

- Before dispatch, scale-up, train-now, kill, or route-change: log expected values for the fields that matter.
- After the lane resolves: attach actual `research_yield_decomposition` and resolve the prediction row.
- Use agent-minutes or explicit cost units, not human-hour guesses, when estimating effort.

The decomposition supplies the resolver with concrete outcomes rather than free-form "worked / did not work" prose.

### Orchestration Ticks

Every orchestration tick that summarizes a research lane should carry:

- `prediction_id` when one exists.
- `candidate_supply`, `eligibility_rate`, `verification_compile_rate`, and `residual_or_closure_rate`.
- `current_bottleneck`.
- `next_lever`.
- a typed decision such as `train_cross_encoder_or_gnn_now: false`, `scale_source_body_eligible_harvesting_next: true`, or `repair_context_harvester_next: true`.

The orchestrator should prefer the next lever named by the bottleneck unless a higher-priority constraint overrides it. If the tick ignores the named lever, it should state why.

### Experiment Track Record

When an E-row closes a run that used this seam, include the decomposition object or a pointer to it. Write an F-row only when the decomposition changes what to believe or build next, for example "candidate eligibility, not verifier speed, is the limiting factor."

### Dashboard / Mining

A future dashboard or mining pass can aggregate these objects across lanes to answer:

- which factor most often binds across substrates,
- which levers actually improve downstream yield,
- whether throughput improvements are increasing verified residual labels or only moving more bad candidates through the system,
- whether prediction-ledger estimates are calibrated on yield factors, not just binary outcomes.

## Evidence Pointers

The GP-225 v18.49-v18.51 sequence is the motivating exemplar.

### GP-225 v18.49

Artifact: `analytics/public/leanmill/results/v1849_public_trace_prefiltered_parallel_replay_scale.{md,json}`

Observed decomposition:

- `candidate_supply`: 30
- `eligibility_rate`: 0.7667
- `verification_compile_rate`: 0.7826
- `residual_or_closure_rate`: 0.9444
- `verified_residual_labels`: 17
- `audited_true_false_accepts`: 0
- `wall_seconds`: 232.964
- `verified_residual_labels_per_minute`: 4.3784
- `decision_impact`: `underpowered_clean_packet_prefiltered_scale_did_not_clear_size_gate`
- `current_bottleneck`: `candidate_eligibility_supply`
- `next_lever`: `increase source-body eligible public-trace supply before training`

Read: throughput was usable, false accepts were clean, and residual rate was high. The decision still blocked training because supply after eligibility was underpowered.

### GP-225 v18.50

Artifact: `analytics/public/leanmill/results/v1850_verified_transition_micro_baseline_ladder.{md,json}`

The same decomposition supported a different decision: `micro_baseline_survives_authorizes_more_eligible_harvesting`.

Read: v18.50 did not claim the lane was training-ready. It used the decomposition to justify the next lever: scale source-body eligible harvesting. This is the intended use of the seam.

### GP-225 v18.51

Artifact: `analytics/public/leanmill/results/v1851_public_trace_source_body_eligible_harvester.{md,json}`

Observed decomposition:

- `candidate_supply`: 65
- `eligibility_rate`: 0.7538
- `verification_compile_rate`: `not_run_static_prefilter`
- `residual_or_closure_rate`: 0.4694
- `verified_residual_labels`: `not_run_static_prefilter`
- `audited_true_false_accepts`: `not_run_static_prefilter`
- `wall_seconds`: 0
- `decision_impact`: `scale_stratified_parallel_verifier`
- `current_bottleneck`: `compile_verification_next`
- `next_lever`: `stratified_parallel_replay_verification`

Read: the harvester improved supply and preserved eligibility, but the next bottleneck moved to compile verification. The explicit sentinel fields prevent a static prefilter from masquerading as a failed verifier.

## Debate Transcript / Outcome

Disclaimer: the following voices are simulated analytic personas used to pressure-test the seam. They are not external authorities, and their names do not imply endorsement by the historical figures or any institution.

### Popper Lens

The seam is useful only if each field can be falsified by a later artifact. `eligibility_rate` must resolve against counted eligible rows. `verification_compile_rate` must resolve against compile logs. `decision_impact` must resolve against an actual next action. A decomposition that cannot be contradicted is narrative, not instrumentation.

Verdict: accept, with strict source pointers and denominator checks.

### Lakatos Lens

The primitive is progressive if it predicts where the next research move should go and the next move actually increases usable scientific yield. It is degenerative if it becomes a post-hoc explanation for whatever the operator already wanted to do.

Verdict: accept only when paired with prediction-ledger rows for typed decisions.

### Kuhn Lens

The value is vocabulary stabilization. Without a shared field set, each substrate invents its own story about "progress." The seam gives anomalies a common surface: supply shortage, eligibility loss, verifier failure, residual weakness, false-accept contamination, cost drag, or policy ambiguity.

Verdict: accept as a normal-science instrument, not as a theory of discovery.

### Peirce Lens

The decomposition is abductive bookkeeping. It turns surprise into a next hypothesis: if supply is high but eligibility is low, inspect filters; if eligibility is high but compile is low, inspect verifier contracts; if compile is high but decision impact is low, inspect policy thresholds.

Verdict: accept because it forces the next inquiry to be specific.

### Operations / Queueing Lens

Throughput by itself is a station metric. Scientific yield is a system metric. A local speedup at candidate generation can worsen the system if it floods the verifier with ineligible work. The seam should therefore report bottleneck movement, not just rate increases.

Verdict: accept, but keep `current_bottleneck` and `next_lever` mandatory.

### Outcome

Converged v1 contract:

- Throughput is retained as `verified_residual_labels_per_minute` or another explicit cost-normalized coefficient.
- The primitive must decompose the full funnel before claiming a lane is good or bad.
- Decision-changing uses must connect to PATTERN-012 prediction ledger or an equivalent pre-action forecast.
- Static prefilters must use explicit sentinels for unrun verifier fields.
- The immediate exemplar is GP-225 v18.49-v18.51; the seam generalizes beyond lemma relevance only after at least one non-GP-225 consumer emits the same object.

## Anti-patterns

| Anti-pattern | Failure | Guard |
|---|---|---|
| Throughput-only victory | A faster lane is declared better even though verified residual yield or decision impact did not improve. | Require full decomposition and decision field. |
| Denominator drift | `residual_or_closure_rate` silently changes denominator across artifacts. | State denominator or enforce schema metadata. |
| Static-prefilter laundering | A static filter emits `0` for verifier fields, making "not run" look like failure or success. | Use explicit sentinels. |
| Decision laundering | A lane metric is reported after the next action was already chosen. | Prediction row before typed action. |
| False-accept blindness | High compile rate hides contaminated labels. | Require `audited_true_false_accepts`. |
| Scalar collapse | All fields are compressed into one yield score that hides the bottleneck. | Keep bottleneck and next lever as first-class fields. |
| Substrate overfit | GP-225 field names become Lean-only concepts. | Keep schema general and put substrate-specific details in source artifact prose. |

## Validation Criteria

The v1 seam is validated when three conditions hold:

1. **Schema completeness:** at least three artifacts emit the required object with source pointers, including explicit sentinels where a stage was not run.
2. **Decision traceability:** at least two typed orchestration decisions can be traced from prediction row -> decomposition -> next lever -> follow-up artifact.
3. **Cross-substrate sanity:** at least one non-GP-225 research lane emits the object without changing the core field names.

Promotion from `v1-open` to `converged` requires:

- no unresolved denominator drift across the first three consumers,
- no false use of `0` where a sentinel is required,
- evidence that the decomposition changed at least one next action rather than merely documenting an action after the fact.

## Non-goals

- Do not optimize to a single global scientific-yield score in v1.
- Do not auto-kill lanes based on one decomposition row.
- Do not make wall time the universal cost denominator; use the scarce resource for the lane.
- Do not turn the seam into a dashboard before the contract has at least three clean consumers.

## Minimal Consumer Template

```markdown
## Research Yield Decomposition

- `candidate_supply`: ...
- `eligibility_rate`: ...
- `verification_compile_rate`: ...
- `residual_or_closure_rate`: ...
- `verified_residual_labels`: ...
- `audited_true_false_accepts`: ...
- `wall_seconds`: ...
- `verified_residual_labels_per_minute`: ...
- `decision_impact`: ...
- `current_bottleneck`: ...
- `next_lever`: ...
```

## Next Action

First practical next step: require this block on new GP-225 lemma-relevance artifacts that gate training, scale-up, or route change. The second consumer should be deliberately outside GP-225 so the primitive proves it is general-purpose instrumentation rather than local reporting style.
