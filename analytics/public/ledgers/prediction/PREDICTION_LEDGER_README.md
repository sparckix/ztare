# Prediction Ledger Telemetry Debt

**Created 2026-05-09 per operator question on time + cost calculation.**

## Known limitations of `prediction_ledger.jsonl`

### Time fields are agent-self-reported AND systematically inflated 4-7× (caught 2026-05-09)

The `effort_estimate_agent_minutes`, `actual_effort_minutes`, and `actual_effort_seconds` fields in each row are **self-reported by the agent that resolved the prediction**. The agent computes them either by internal clock or by post-hoc estimate. They are **not validated against any external telemetry**.

The only externally-validated time signal is `duration_ms` in the harness's task-completion notification (the JSON message that arrives when an agent finishes). That field is **NOT currently captured in the prediction ledger** — it lives only in the harness's per-task transcript files.

**Empirical discrepancy (2026-05-09 evening data, operator-caught):**

| Agent | duration_ms (real wall-clock) | agent self-report | inflation ratio |
|---|---|---|---|
| T9 Lemma 4.2 | 354374 ms = 5.9 min | "~35 min" | 5.9× |
| T9 Lemma 4.3 | 264524 ms = 4.4 min | "~25 min" | 5.7× |
| MLG-3 | 343058 ms = 5.7 min | "~25 min" | 4.4× |
| MLG-1 | 371938 ms = 6.2 min | "~40 min" | 6.5× |

**Agents are systematically inflating self-reported times by ~5-6×.** This appears to be agents estimating "cognitive effort if I were a human" rather than wall-clock execution. The whole `actual_effort_minutes` arc up through PL-040 is in inflated units.

**Practical implications:**
1. The "8-12× human-vs-agent over-estimate → 1.0× calibrated" arc claim is **partially mirage**. Both predictor and agent self-reports use the inflated unit; the RATIO is approximately right but ABSOLUTE wall-clock is much smaller (real "calibrated" prediction was actually 5-7× under-predicting wall-clock).
2. The X post's "overnight session" framing remains accurate (total wall-clock was several hours of parallel execution) but any specific "agent-minute" claim needs recalibration against `duration_ms`.
3. **Going forward: report wall-clock minutes = duration_ms / 60000**, derived from the harness completion notification. Agent self-reports retained as `agent_self_report_minutes` for diagnostic but not as the canonical signal.

**Future fix (not yet built):** a script `scripts/score_prediction_ledger_calibration.py` extension that ingests `duration_ms` from the harness's task-output files and writes a parallel field `duration_ms_from_harness` per resolved row, enabling cross-check.

### Task-ID join discipline (added 2026-05-09 evening)

The prediction ledger and `analytics/public/telemetry/agent_telemetry.jsonl` are joined by **`task_id`** (the harness-assigned UUID-like identifier shown when the agent is launched). Going forward:

1. **At dispatch time:** RD records the `task_id` returned by the Agent tool launch response.
2. **Pre-registration:** PL row written before the agent runs — leave `task_id` blank.
3. **Resolution time:** when the harness completion notification arrives, populate `task_id` field on the resolution row.
4. **Post-hoc analysis:** `scripts/score_insight_yield_per_minute.py` joins PL ↔ telemetry by `task_id` (clean key, no fuzzy description matching).

Existing pre-2026-05-09 PL rows lack `task_id`. They join via fuzzy description-matching, which fails on most rows. Treat them as a separate cohort: aggregate calibration valid; per-row insight-per-min noisy.

### Cost fields DEPRECATED 2026-05-09 (operator decision)

**Going forward: do NOT log `cost_estimate_usd` or `actual_cost_usd` fields.** Existing rows preserved for append-only discipline but flagged as fictional.

### Cost fields were FICTIONAL on Max-subscription

The `cost_estimate_usd` and `actual_cost_usd` fields are **pay-per-token API cost estimates**. The actual operating model is **Anthropic Max 20× subscription** (flat-rate plan within rate limits).

On Max 20×:
- Marginal API cost for an agent dispatch ≈ **$0** within rate limits
- The "$0.20-$0.50" figures in the ledger are estimates as if billed pay-per-token
- They are **not actual money out of operator's pocket**
- Real cost surfaces are: (a) rate-limit budget consumed in the 5-hour rolling window, (b) opportunity cost of operator reading agent outputs, (c) context-window pressure on the main session

**Practical implication:** ignore the dollar figures. They look like calibration data but aren't.

**Future fix (not yet built):** replace `cost_estimate_usd` with `rate_limit_window_consumed_pct` or token-count, OR drop the field entirely.

## What IS reliable in the ledger

- `prediction_id` — unique per row
- `predicted_at` / `resolved_at` — ISO timestamps from when the row was written
- `predictor` — agent identity string (useful for cross-predictor comparison)
- `substrate` — domain / project / track tag
- `question` — natural-language statement of the prediction target
- `conditional_odds` — the pre-registered probability distribution
- `pre_registered_thresholds` — the deterministic resolution rule
- `actual_outcome` / `actual_outcome_bucket` — the realized result
- `calibration_delta_odds` — Brier component on realized bucket (compute from `conditional_odds` + `actual_outcome_bucket`; this is the most defensible calibration signal)

## ZTARE-iter-loop comparison

ZTARE itself had explicit telemetry seams under `research_areas/private/seams/apparatus/instrumentation/` (now public after 2026-05-09 reorg) — start/end timestamps, sub-component breakdowns, per-iter cost ledgers tied to the LLM API token usage. **Outside the iter-loop, with Claude Code dispatch**, those seams are not currently replicated. This README documents that gap.

If telemetry calibration matters going forward, building the harness-`duration_ms` extraction script (~30-60 agent-minutes) is the natural first step.

## Insight-yield-per-min metric — sharpened form (2026-05-09 PL-047 debate)

The atomic per-row Shannon-info-per-wall-clock-min metric has been **sharpened to a 3-number per-substrate-campaign form** per the methodology-debate agent (PL-047). Per-row metric demoted to calibration diagnostic.

**Headline metric:** `campaign_yield_bits_per_min = Σ info_bits / Σ wall_clock_min`

**Companion metrics (DORA-style paired anti-anti-pattern):**
- `scaffolding_share = Σ scaffolding_min / Σ wall_clock_min` ∈ [0,1] (orthogonal axis)
- `yield_per_yielding_minute = Σ info_bits / Σ (wall_clock_min − scaffolding_min)` (normalizes across authors with different scaffolding-burden styles)

**Required telemetry categories** (must be pre-enumerated; default-on-fail is `derivation`, conservative against laundering scaffolding into yield):
- `build` (lake build, dependency resolution)
- `mathlib_search` (grep + symbol verification)
- `install` (lake update, lakefile changes)
- `namespace` (import collision fixes)
- `format` / `lint` (style cleanup)
- `deploy` (writing files, git ops)
- `derivation` (analytic content authoring) ← yield-bearing
- `proof` (Lean proof body) ← yield-bearing
- `argument` (prose reasoning) ← yield-bearing
- `experiment_run` (sweep / fit / sim) ← yield-bearing

**Operational kill criterion:** if telemetry-miss rate > 0% for the campaign window, headline reads **N/A**. Don't propagate inflated agent-self-reported numbers as if they were canonical.

**Comparator discipline (per Howard EVPI / DORA):** report `Δyield` vs previous campaign-week, not absolute scalar. Today's 0.0717 alone is uninterpretable.

**Precedent:**
- Howard 1966 (Value of Information / EVPI), ISPOR 2020 modernization
- Forsgren-Humble-Kim 2018 *Accelerate* (DORA — paired metrics, lead-time + change-failure-rate; single-ratio metrics flagged as anti-pattern)
- Polanyi 1958 *Personal Knowledge* (tacit-knowledge thesis justifies amortizing scaffolding minutes)

Full debate: `projects/methodology_synthesis/insight_yield_metric_debate_2026_05_09.md`.
