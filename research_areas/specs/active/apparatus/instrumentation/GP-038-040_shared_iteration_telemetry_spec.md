# GP-038 + GP-040 Shared Iteration Telemetry Spec

## Status

Verified (2026-04-18)

Slices 1+2 shipped and live-verified against GP-037 (2026-04-12). `src/ztare/validator/telemetry_reporter.py` implements the offline cost and episode reporters reading `workspace/iteration_telemetry.jsonl`. GP-038 seam updated to `verified`. GP-040 seam updated to `partially-verified` — Slices 3 (findings provenance) and 4 (operator economics) remain open; these are prerequisites for the full `c_finding` metric in paper5's instrumentation roadmap. No further engineering work needed from this spec.

## Scope

- add a shared append-only iteration telemetry stream to `autoresearch_loop.py`
- covers both GP-038 (tail cycle-time instrumentation) and GP-040 (throughput/cost instrumentation) Slice 1
- raw telemetry only — no derived metrics, no KPI claims, no episode definitions baked in

Does not cover:

- GP-038 Slice 2: offline tail-distribution reporter (requires telemetry from 2-3 real runs first)
- GP-040 Slice 2: findings provenance summary (requires runner exercised on 3+ findings)
- GP-040 Slice 3: human economics study (design task, not engineering)
- GP-039: gate library formalization (separate spec, no runtime code)
- changes to scoring, evaluation, or gate logic
- any cost or throughput claims — this spec produces raw logs, not conclusions

## Decision

Add a single shared append-only telemetry stream (`workspace/iteration_telemetry.jsonl`) that logs per-iteration runtime primitives. GP-038 and GP-040 both derive their downstream analyses from this same stream. No GP-specific runtime artifacts.

## Problem

ZTARE currently has no per-iteration machine telemetry. The supervisor's `TurnUsageTelemetry` tracks token counts per LLM call and the runner tracks `budget_usd`, but neither records the full per-iteration breakdown needed for:

- **tail cycle-time analysis (GP-038):** iterations-to-resolution has heavy tails; optimizing mean CT can hurt the exact trajectories that matter (decisive episodes with gate engagement, escalations, underidentified exits). Without the raw data, we cannot distinguish "the system is fast" from "the system is fast on easy problems and slow on the ones that matter."
- **throughput/cost analysis (GP-040):** per-iteration cost breakdown (LLM spend, wall-clock timing, stop reason) is needed before any honest cost-per-finding number can be quoted. Currently the answer to "what does a finding cost?" is "we haven't measured it."

GP-038 Turn 3 and GP-040 Turn 3 (both Codex) independently converged on the same conclusion: do not build two separate telemetry substrates. One shared stream, two offline reporters.

## Why It Matters

- Without per-iteration telemetry, GP-032's KPI split (runner-touched findings/$ vs. operator-confirmed findings/operator-hour) cannot be computed — the denominators don't exist.
- Without raw timing and stop-reason data, the GP-038 tail-distribution analysis cannot distinguish heavy-tail episodes from normal convergence.
- Building two parallel telemetry artifacts (one for GP-038, one for GP-040) would produce duplicated timestamps, diverging stop-reason vocabularies, and two raw logs that need reconciliation. One stream prevents that.

## Constraints

From converged seam debates (GP-038 Turns 1-3, GP-040 Turns 1-3):

1. **Shared, not GP-branded.** The telemetry stream is a neutral runtime artifact, not a GP-038-specific or GP-040-specific file. Both downstream reporters consume the same stream.
2. **Raw primitives only.** Log the data needed to compute distributions and costs later. Do not bake in episode definitions, KPI formulas, or derived metrics at the runtime level.
3. **Include failed/aborted runs.** The stream must log invalid smokes, underidentified exits, catastrophic failures, and operator-stopped runs. Measuring only successful convergence events systematically understates true cost (GP-038 survivorship bias correction).
4. **Append-only.** One line per iteration, appended. No overwriting, no truncation mid-run.
5. **No new dependencies.** Uses stdlib only (json, time, datetime). No additional packages.

## Options

### Option A — Per-iteration JSONL in workspace

**Description**

Append one JSON line per iteration to `workspace/iteration_telemetry.jsonl` from within the main loop in `autoresearch_loop.py`.

**Pros**

- Simple, no new files or modules needed
- Append-only is naturally safe
- Lives alongside existing workspace artifacts
- Both GP-038 and GP-040 reporters can read the same file

**Cons**

- Couples telemetry emission to the main loop code
- File grows unboundedly across runs (acceptable for now; rotation is a future concern)

**Verdict**

Recommended. Simplest viable approach.

### Option B — Separate telemetry module with structured API

**Description**

Create `src/ztare/common/telemetry.py` with a `TelemetryEmitter` class, context managers for iteration timing, and a structured write API.

**Pros**

- Cleaner separation of concerns
- Easier to extend later

**Cons**

- Cathedral version of a small problem
- Premature abstraction for a raw logging task
- Adds a module that only one consumer (the main loop) calls

**Verdict**

Rejected. Build this only if the inline approach becomes unwieldy.

## Recommendation

Option A. Inline telemetry emission in `autoresearch_loop.py`.

## Implementation Sketch

### Per-iteration telemetry record

Each line in `workspace/iteration_telemetry.jsonl` is a JSON object with these fields:

```json
{
  "record_type": "iteration",
  "run_id": "int — the run's unique ID",
  "iteration_index": "int",
  "iteration_start_utc": "ISO 8601 timestamp (timezone-aware UTC)",
  "iteration_end_utc": "ISO 8601 timestamp (timezone-aware UTC)",
  "wall_clock_seconds": "float",
  "loop_control_action": "normal | stagnation_pivot | refresh_specialists | emergency_pivot",
  "score": "float or null",
  "score_improved": "bool",
  "champion_promoted": "bool",
  "stagnation_count": "int",
  "gate_engagement": "bool — did GP-030 deterministic gates fire this iteration?",
  "gate_failure_count": "int",
  "failed_gate_ids": ["list of gate IDs that failed"],
  "escalation_flags": {
    "self_reference": "bool",
    "semantic_escalation": "bool"
  },
  "falsification_mode": "string — the active falsification profile",
  "mutator_model_id": "string",
  "judge_model_id": "string",
  "mutator_usage": {"input_tokens": "int", "output_tokens": "int", "cache_read_tokens": "int", "cache_write_tokens": "int"},
  "judge_usage": {"input_tokens": "int", "output_tokens": "int", "cache_read_tokens": "int", "cache_write_tokens": "int"},
  "estimated_cost_usd": "float or null — combined mutator+judge for this iteration",
  "pending_loop_action": "string — next loop action (CONTINUE, REFRESH_SPECIALISTS, PIVOT_REQUIRED, UNDERIDENTIFIED)"
}
```

All timestamps must use timezone-aware UTC: `datetime.now(timezone.utc)` (not naive `datetime.utcnow()`).

### Run boundary records

Two additional record types for run start/end:

```json
{"record_type": "run_start", "run_id": "...", "project": "...", "timestamp_utc": "...", "rubric": "...", "iteration_budget": "int", "mutator_model": "...", "judge_model": "..."}
```

```json
{"record_type": "run_end", "run_id": "...", "timestamp_utc": "...", "final_iteration": "int", "final_score": "float or null", "run_exit_reason": "converged | budget_exhausted | operator_stop | catastrophic | underidentified"}
```

### Integration points in autoresearch_loop.py

1. **Run start:** After run initialization, before first iteration, append `run_start` record.
2. **Per iteration:** At the end of each iteration (after scoring, after champion promotion decision), append the iteration record. Capture `iteration_start_utc` at the top of the iteration body and `iteration_end_utc` at the bottom.
3. **Run end:** After the loop exits (normal or exception), append `run_end` record. Use a `try/finally` to ensure this fires even on crashes.

### What this does NOT do

- Does not compute tail distributions (GP-038 Slice 2 — offline reporter)
- Does not compute cost rollups or per-finding cost (GP-040 Slice 2 — offline reporter)
- Does not track findings provenance (GP-040 Slice 2 — requires runner)
- Does not track operator hours (GP-040 Slice 3 — study design, not engineering)
- Does not define "decisive episode" (GP-038 — the definition is not stable yet; the raw data lets it be defined later)

## Run Close-Out Procedure (GP-040 Slice 2 — implemented 2026-04-18)

After any autoresearch loop run that produces findings or is cited in an INS entry,
the operator must run the offline reporter before sealing `run_summary.json`.

### Required steps

**Step 1 — Run the reporter:**
```
python -m src.ztare.validator.telemetry_reporter \
    --project <project_name> \
    --write-cost-summary \
    --update-run-summary
```
This writes `projects/<name>/workspace/cost_summary.json` and merges a `cost_telemetry`
key into `projects/<name>/run_summary.json`.

**Step 2 — Verify the figure:**
Open `workspace/cost_summary.json`. Confirm `total_cost_usd` is plausible for the model
pair and iteration count. If it differs by more than 5% from any operator-reported terminal
total in the same run artifacts, add a `reconciliation_note` to `run_summary.json` explaining
the delta before sealing.

**Step 3 — Cite in the INS ledger:**
When opening or updating an INS entry for this run, use the standard `cost_usd` field format:

```
- **Cost:** total_cost_usd=$X.XXXX  cost_per_iter=$X.XXXXX  cost_per_score_point=$X.XXXXX
  wall_clock=Xm  iterations=N  final_score=N  run_id=XXXXXXXXXX
  models: mutator=<model-id> / judge=<model-id>
  source: `projects/<name>/workspace/cost_summary.json` (machine-recorded per-call)
```

For insights spanning multiple runs, list each run and sum:
```
- **Cost:** run_A $X.XXXX (N iters, score S) + run_B $X.XXXX (N iters, score S) = combined $X.XXXX
  source: workspace/cost_summary.json for each project
```

Do not paste operator-reported terminal totals when machine-recorded telemetry exists.

**Step 4 — Seal:**
Add `"sealed_at_utc"` to `run_summary.json` only after steps 1–3 are complete.

### Applicability

Required for all new runs (post-GP-038/040 Slice 1, verified 2026-04-12).
Applied retroactively to `gp023_crucial_01` and `gp023_crucial_02` on 2026-04-18.

### What this does NOT do

- Does not retroactively cover runs before Slice 1 telemetry existed.
- Does not compute operator hours or fully amortised cost (GP-040 Slice 4 — deferred).
- Does not update the INS ledger automatically — operator pastes the cost block.

---

## Open Questions

1. Should the telemetry file rotate per-run (one file per run_id) or stay as a single append-only file across all runs? Single file is simpler; per-run is easier to manage at scale. Default to single file, revisit if file size becomes a problem.
2. Should `estimated_cost_usd` be computed inline or left null until `supervisor/model_pricing.json` is populated? Default to: compute if pricing is available, null otherwise.
3. ~~Should the telemetry record include the full `gate_results` object?~~ Resolved: do NOT duplicate the full gate payload into the shared telemetry stream. The per-iteration record carries `gate_engagement`, `gate_failure_count`, and `failed_gate_ids` only. The authoritative gate payload already lives in `latest_eval_results.json`. (Codex re-check 2026-04-12.)

## Review Notes

### 2026-04-12 12:04:43 EDT — Codex

The shared-substrate decision is right, but the current schema still has three decisive problems:

1. **`stop_reason` is overloading different concepts.** The current field mixes run-terminal states (`underidentified`, `operator_stop`, `invalid`) with iteration-local control states (`stagnation_pivot`) and even a placeholder state (`in_progress`). That will create ambiguous telemetry immediately. Split this into:
   - `run_exit_reason` on `run_end`
   - `loop_control_action` on iteration records
   - `iteration_status` only if you truly need it

2. **The token/cost fields are too lossy for GP-040.** `mutator_tokens` and `judge_tokens` as aggregate ints are not enough if this artifact is supposed to support later cost analysis. Keep the raw buckets:
   - input
   - output
   - cache_read / cache_write if available
   - estimated_cost_usd per model call-family
   Otherwise the first slice destroys the detail the later reporter needs.

3. **Embedding the full `gate_results` object is too much schema commitment at slice 1.** That payload already exists in `latest_eval_results.json` and is likely to drift as GP-030 evolves. The shared telemetry stream should log:
   - `gate_engagement`
   - `gate_failure_count`
   - `failed_gate_ids`
   - optionally an artifact reference
   not a second authoritative copy of the full gate payload.

Two smaller corrections:

- add `record_type: iteration` to the per-iteration record for symmetry with `run_start` / `run_end`
- capture `pending_loop_action` if the goal is to understand GP-038 tails; otherwise you lose exactly the `REFRESH_SPECIALISTS` / pivot signal that distinguishes semantic traversal from operator-style disturbance

So my judgment is:

- architecture: right
- first slice: right
- schema: tighten before implementation

### 2026-04-12 12:49:59 EDT — Codex

Re-checking after the live runtime warning: one additional requirement should be made explicit here.

4. **All telemetry timestamps must be timezone-aware UTC.**
   Do not use naive UTC helpers. The spec should explicitly require:
   - `datetime.now(datetime.UTC)` on 3.11+
   - or `datetime.now(timezone.utc)` if you want broader compatibility

The warning that surfaced during the live run is a reminder that this is no longer style-only. If GP-038/040 is going to be the canonical telemetry substrate, it should not bake deprecated timestamp patterns into the first slice.

Also, the earlier three schema issues are still unresolved in the body of the spec:

- `stop_reason` is still overloaded
- token/cost fields are still too lossy
- `gate_results` is still duplicated into the stream

So my state remains:

- concept: converged
- implementation contract: still not clean enough to ship unchanged

### 2026-04-12 13:13:41 EDT — Codex

Re-check after revision:

- The main schema fixes are now in place:
  - `record_type` exists
  - iteration-local `loop_control_action` is split from run-terminal `run_exit_reason`
  - raw mutator/judge token buckets are preserved
  - the per-iteration schema no longer duplicates full `gate_results`
  - timezone-aware UTC is now explicit

One inconsistency still remains:

1. **Open Question 3 still contradicts the implementation sketch.**
   The body of the spec correctly narrowed the runtime record to:
   - `gate_engagement`
   - `gate_failure_count`
   - `failed_gate_ids`

   But Open Question 3 still says “Include both — the object is small and the detail is useful,” which would reintroduce full `gate_results` duplication. The open question should be resolved in favor of the body: do **not** duplicate the full gate payload into the shared telemetry stream in slice 1.

So my updated state is:

- concept: converged
- schema: almost clean
- remaining blocker: remove the stale Open Question 3 contradiction before implementation

### 2026-04-12 15:16:53 EDT — Codex

Slice 1 is now implemented in [`src/ztare/validator/autoresearch_loop.py`](/src/ztare/validator/autoresearch_loop.py).

What landed:

- shared append-only `workspace/iteration_telemetry.jsonl`
- `run_start`, `iteration`, and `run_end` record types
- timezone-aware UTC timestamps
- split `loop_control_action` vs `run_exit_reason`
- raw mutator/judge token buckets plus per-iteration estimated cost
- gate engagement summary fields (`gate_engagement`, `gate_failure_count`, `failed_gate_ids`)
- escalation flags and `pending_loop_action`
- run-end flush on normal completion plus operator-stop hardening via a SIGINT finalizer

The remaining work is verification, not design:

- confirm one live run writes `run_start` + `run_end` correctly
- confirm deterministic-gate projects populate gate fields as expected
- only then build the offline GP-038 / GP-040 reporters

### 2026-04-12 15:37:24 EDT — Codex

The live verifier has now passed on the clean GP-037 10-iteration run.

Confirmed on disk:

- [`iteration_telemetry.jsonl`](/projects/gp037_substrate_swap_01/workspace/iteration_telemetry.jsonl) contains `run_start`, 10 `iteration` records, and `run_end`
- the records include populated gate summary fields on a deterministic-gate project
- per-iteration token/cost buckets and loop-control fields are present

So this spec's slice-1 contract is no longer blocked on proof-of-life. The next work is downstream reporting, not more telemetry substrate design.
