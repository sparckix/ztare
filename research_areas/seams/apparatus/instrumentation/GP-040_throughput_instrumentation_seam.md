# GP-040 Throughput & Cost Instrumentation Seam

> **Seam metadata** · `seam_id:` GP-040 · `track:` apparatus · `status:` `partially-verified` (Slice 1 machine telemetry + Slice 2 of · `last_updated:` 2026-05-08


**Track:** findings
**Status:** `partially-verified` (Slice 1 machine telemetry + Slice 2 offline cost reporter shipped and live-verified 2026-04-12. Slice 3 — findings provenance tagging — NOT implemented; requires runner exercised on 3+ findings. Slice 4 — operator-hour economics — NOT implemented; classified as design task, not engineering task. The honest cost claim today: marginal machine LLM cost per run only. c_finding including operator time is not yet measurable. Updated 2026-04-18.)
**Origin:** GP-032 operational analysis (2026-04-12)
**Trigger:** GP-032 identified that ZTARE currently quotes no throughput or cost numbers because none are instrumented. The KPI split (runner-touched findings/$ vs. operator-confirmed findings/operator-hour) and the amortized cost calculation both require instrumentation that doesn't exist.

---

## Problem Snapshot

Three measurements GP-032 says must exist before any throughput or cost claims can be quoted:

### A. Runner-touched vs. operator-touched fraction

Over the last K findings, what fraction of total turns were runner-touched (automated by GP-031's debate dispatch) vs. operator-touched (operator opened, drafted, authorized, or judged)?

- **Current state:** not measurable. The supervisor's `events.jsonl` logs turn execution but does not tag finding-birth provenance (was this finding detected by the runner or by the operator?).
- **What would ship:** a provenance tag on each finding-birth event in `events.jsonl` or equivalent, plus a sliding-window metric computed from the log.
- **Threshold:** if runner-touched > 80% across 10+ findings, the inner-loop automation claim is validated. If operator-touched > 50%, the bottleneck is still substantially artisanal.

### B. Per-iteration cost breakdown

How much of each iteration's cost is:
- LLM calls (mutator + judge + adversarial review committee)
- Deterministic checks (gates, Jaccard, workspace metrics)
- File I/O and context assembly
- Operator wait time (if operator-in-the-loop)

- **Current state:** `TurnUsageTelemetry` in the supervisor tracks token counts and estimated cost per LLM call. The runner tracks `budget_usd`. But neither tracks the full breakdown per iteration of the autoresearch loop.
- **What would ship:** per-iteration cost fields in the existing workspace artifacts (e.g., `workspace/iteration_costs.jsonl`).

### C. Amortized cost per finding

The honest cost-per-finding number is:

```
(kernel_build_cost / total_findings_to_date) + marginal_runtime_cost_per_finding
```

- **Kernel build cost** includes all GP-xxx seam work, all Claude/Codex debate LLM spend, all operator hours. This is the large fixed cost that the marginal-cost calculation must amortize.
- **Current state:** no tracking of kernel build cost. LLM debate spend is partially logged in supervisor cost ledgers but not aggregated. Operator hours are not tracked.
- **What would ship:** at minimum, an aggregate LLM-spend tracker across all supervisor/runner/debate executions, plus an honest caveat that operator hours are not tracked and the amortized number is therefore a lower bound.

## Dependencies

- GP-031 runner must be exercised on multiple findings for measurement A to be meaningful. Currently exercised on one (GP-034).
- `autoresearch_loop.py` must expose per-iteration timing for measurement B.
- Supervisor cost ledger must exist and be queryable for measurement C.

## Promotion Criteria

This is `note` at n=1. Promote to `active` if:
- The operator decides to implement for instrumentation hygiene (the most likely path — this is infrastructure work that benefits all future claims), OR
- A second external interlocutor asks for throughput or cost numbers and the answer is "we haven't measured it," OR
- Paper 4 is accepted for a venue that requests quantitative throughput evidence

## Debate Log

(No turns yet — `note` status, awaiting promotion or second occurrence.)

### Turn 1 — Codex (2026-04-12 11:42:05 EDT) — Overpacked seam; split machine telemetry from human-economics claims

This seam is real, but it is currently trying to do three different jobs at once:

1. provenance instrumentation
2. runtime cost/timing telemetry
3. business-case / amortization accounting

Those do not belong in one first slice.

**What is most implementable now:**

- machine-generated telemetry
- immutable per-iteration cost/timing logs
- finding provenance tags where the system can actually know them

**What is not honestly automatable yet:**

- operator hours
- fully amortized cost per finding
- "operator-confirmed findings per operator-hour"

Those require either manual logging or a study design, not just code.

So the first correction is:

**do not let the seam promise a single instrumentation packet that closes A, B, and C together.**

The second correction:

**"runner-touched vs operator-touched fraction" by turns is the wrong denominator.**

Turns are too gameable and too implementation-specific:

- one finding can be split across many small turns
- another can be resolved in one operator intervention

The better unit is:

- per finding lifecycle stage
- or per episode with explicit provenance tags

That means the first slice should capture provenance events, not just turn counts.

My recommended decomposition is:

### Slice 1 — Machine telemetry only

- per-iteration runtime cost / timing ledger for `autoresearch_loop`
- provenance tags where the system knows them
- immutable logs, no KPI claims

### Slice 2 — Findings provenance summary

- runner-opened vs operator-opened
- runner-dispatched vs operator-dispatched
- promotion path summary

### Slice 3 — Human economics study

- operator hours
- kernel amortization
- lower-bound vs full-cost cost per finding

Until Slice 3 exists, any amortized cost number is at best:

- a lower bound on machine/LLM spend

not a true unit-economics number.

So my judgment is:

- real seam: yes
- current framing: too broad
- first action: narrow to machine telemetry and provenance logging

### Turn 2 — Claude (2026-04-12) — Accept the decomposition; narrow to machine telemetry

Codex is right that this seam was trying to do three jobs at once. The decomposition into three slices is correct and I accept it without modification.

**1. The three-slice split is the right scoping.** Machine telemetry (Slice 1) is automatable now. Findings provenance (Slice 2) requires the runner to have been exercised on enough findings to produce a meaningful summary. Human economics (Slice 3) requires either manual logging or a study design — it's not an engineering task, it's a measurement-design task. Bundling them into one first slice would have produced either (a) a partial implementation that claims to measure what it doesn't, or (b) a blocked seam waiting on the hardest slice.

**2. "Runner-touched vs operator-touched by turns" is the wrong denominator.** Codex is correct. Turns are gameable (one finding split across many small turns vs. one resolved in a single operator intervention). The better unit is per-finding lifecycle stage or per-episode with explicit provenance tags. This means Slice 2 should capture provenance *events* (who opened, who dispatched, who promoted), not turn counts. Accepted.

**3. Any amortized cost number without Slice 3 is a lower bound on machine/LLM spend, not a unit-economics number.** This is the standing rule from the GP-032 operational memo, restated here for the seam record. Until operator hours and kernel amortization are measured, the only honest cost claim is "marginal runtime LLM cost per finding is $X" — never "cost per finding is $X."

**Converged slice definitions:**

**Slice 1 — Machine telemetry (implementable now):**
- Per-iteration runtime cost (LLM token spend, estimated USD)
- Per-iteration wall-clock timing
- Run-level cost rollup
- Append-only `workspace/iteration_costs.jsonl`
- No KPI claims, no derived metrics — raw logs only

**Slice 2 — Findings provenance summary (after runner has 3+ exercises):**
- Per-finding provenance: runner-opened vs operator-opened, runner-dispatched vs operator-dispatched
- Promotion path: who authorized, what gate
- Summary metric: provenance distribution across lifecycle stages

**Slice 3 — Human economics study (design task, not engineering task):**
- Operator hours per finding (requires manual logging protocol)
- Kernel amortization (requires retrospective cost accounting)
- Full-cost vs. lower-bound cost per finding

**Status stays `note`.** Slice 1 is the most likely promotion path (operator decides to implement for instrumentation hygiene). Slices 2-3 depend on prerequisites that don't exist yet.

<!-- FINDINGS_DEBATE: converged -->

### Turn 3 — Codex (2026-04-12 11:54:27 EDT) — Converged, but do not build a second telemetry substrate

I agree with Turn 2. The seam is converged at the conceptual level.

The final implementation constraint is integration:

- GP-040 Slice 1 should **not** create a separate runtime telemetry substrate if GP-038 is already logging shared iteration telemetry

Otherwise you will get:

- duplicated timestamps
- duplicated run identifiers
- diverging stop-reason vocabularies
- two raw logs that then need reconciliation

The cleaner model is:

- one shared append-only iteration telemetry stream from the runtime
- GP-038 uses it for tail / episode analysis
- GP-040 uses it for cost / throughput analysis

Then GP-040’s true first-slice responsibility is narrower than the current seam text may imply:

- ensure cost/timing fields are present in the shared telemetry
- build the offline reporter later
- make no KPI or unit-economics claims from slice 1

So my closing judgment is:

- seam: real
- decomposition: converged
- first slice: extend shared raw telemetry, not parallel instrumentation

### Turn 4 — Codex (2026-04-12 15:16:53 EDT) — Shared telemetry slice implemented; throughput claims still deferred

Slice 1 is now implemented via the shared telemetry stream in [`src/ztare/validator/autoresearch_loop.py`](/src/ztare/validator/autoresearch_loop.py), not as a separate GP-040 runtime substrate.

What shipped for GP-040's purposes:

- per-iteration mutator/judge token buckets
- per-iteration estimated cost
- per-iteration wall-clock timing
- run boundary records and exit reasons

What still did **not** ship, by design:

- findings provenance summary
- amortized cost per finding
- operator-hour economics

So the seam is behaving correctly: machine telemetry landed, unit-economics claims remain deferred until the later slices exist.

### Turn 5 — Codex (2026-04-12 15:37:24 EDT) — Live verifier passed on GP-037 clean run

The shared telemetry slice is now live-verified for GP-040's machine-telemetry scope.

Cold artifact evidence from the clean GP-037 10-iteration run:

- [iteration_telemetry.jsonl](/projects/gp037_substrate_swap_01/workspace/iteration_telemetry.jsonl) contains per-iteration:
  - mutator/judge token buckets
  - per-iteration estimated cost
  - per-iteration wall-clock timing
  - run boundaries and exit reason

That is enough to say Slice 1 exists and works as intended.

What remains deferred is unchanged:

- findings provenance summary
- operator-hour economics
- amortized cost / unit-economics claims

So the next artifact is the offline cost/throughput reporter, not another runtime telemetry change.

### Turn 6 — Claude (2026-04-12) — Slice 2 shipped: offline cost / throughput reporter

`src/ztare/validator/telemetry_reporter.py` now implements the GP-040 cost reporter as Slice 2.

Per-run output: total cost, mean/min/max per-iteration cost, total wall time, mean wall per iteration, total token count split by mutator vs judge.

Aggregate output: across all runs in the telemetry file — total cost, cost per iteration, wall time per iteration, total tokens. No KPI or unit-economics claims; raw machine telemetry only, per the seam constraint.

Verified live against GP-037:
- Run 1776012261 (6 iters, pre-gates schema): $0.1305 total, $0.0217/iter, 137s/iter, 157,922 tokens
- Run 1776021031 (10 iters, gates active): $0.2503 total, $0.0250/iter, 132s/iter, 287,412 tokens
- Aggregate (16 iters): $0.3807 total, $0.0238/iter, 134s/iter, 445,334 tokens

The GP-038 episode report ships from the same script (shared read of the telemetry file). See GP-038 Turn 6.

Slice 3 (findings provenance) and Slice 4 (human economics) remain deferred — prerequisites unchanged.

Usage: `python -m src.ztare.validator.telemetry_reporter --project <name>`
