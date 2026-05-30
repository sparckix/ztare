# GP-038 Tail Cycle-Time Instrumentation Seam

> **Seam metadata** · `seam_id:` GP-038 · `track:` apparatus · `status:` `verified` (Slice 1 + Slice 2 shipped and live-verified 2026 · `last_updated:` 2026-05-08


**Track:** findings
**Status:** `verified` (Slice 1 + Slice 2 shipped and live-verified 2026-04-12; no open engineering work — see Turn 6. Residual: Slice 3 not planned for GP-038; tail-distribution replay across 3+ experiments is the next natural use of the existing reporter.)
**Origin:** GP-032 operational analysis (2026-04-12)
**Trigger:** GP-032 Turn 1 identified that cycle time in this system is a heavy-tailed distribution, and that optimizations aimed at mean CT can hurt tail CT on decisive claims

---

## Problem Snapshot

ZTARE's per-iteration latency is roughly constant (LLM call latency is narrow). But iterations-to-convergence has heavy tails: an easy curve-fit may take 12 iterations; a hard case-study-grade project takes 80+ with long stagnation plateaus.

The draft in GP-032 treated cycle time as a single number (iterations x per-iter latency) and proposed optimizing the mean. GP-032 Turn 1 rejected this: the decisive quantity is *tail cycle time on claims the deterministic gates flag as binding*. A project that converges at median speed but whose highest-score champion hides a charter-violating thesis is the GP-023 Phase 1 pathology — and nothing in a mean-CT optimization would have caught it.

**Why this matters operationally:**
- Model tiering aimed at mean CT (small models for "easy" checks) can directly degrade tail CT on the trajectories that most need frontier reasoning
- Without measuring the distribution, we cannot distinguish "the system is fast" from "the system is fast on easy problems and slow on the ones that matter"
- Paper 4 §7.6 now names this as a future-work instrumentation direction

## What Would Ship

A per-run and per-claim instrumentation pass that:

1. Records iteration count per finding/convergence event
2. Tags each iteration's claims by whether deterministic gates flagged them as binding
3. Computes the tail distribution (p90, p95, p99) of iterations-to-resolution on gate-flagged claims separately from the overall distribution
4. Writes the result to a workspace artifact (e.g., `workspace/cycle_time_distribution.json`)

## Dependencies

- Deterministic gates (GP-030) must be shipping and tagging claims as gate-flagged. **Status: closed, shipping.**
- `autoresearch_loop.py` must expose per-iteration gate results in a structured form. Currently gate results are in debate logs but not in a machine-readable per-iteration artifact.

## Promotion Criteria

This is `note` at n=1. Promote to `active` if:
- A second project's run produces a case where mean CT looked fine but tail CT on a gate-flagged claim was 5x+ the mean, OR
- The operator decides to implement for instrumentation hygiene independent of a second occurrence

## Debate Log

(No turns yet — `note` status, awaiting promotion or second occurrence.)

### Turn 1 — Codex (2026-04-12 11:42:05 EDT) — Real seam, wrong first detector, instrument episodes not just findings

The seam is real, but the current framing is too narrow in one place and too eager in another.

**What is right:**

- mean cycle time is the wrong primary quantity
- heavy tails are the real operational story
- optimizing median / mean latency can hurt the exact trajectories that matter

**What is wrong or premature:**

1. **"claims the deterministic gates flag as binding" is too narrow a detector for decisive work.**

   That is only one subclass of important trajectories:

   - hard-science gate failures
   - visible residual failures
   - hidden-slice generalization failures

   But some of the most expensive and important paths in this system are not gate-flagged at all:

   - self-reference escalations
   - underidentified exits
   - findings-birth episodes
   - soft-domain runs where GP-030 is intentionally inert

   So if this seam instruments only "gate-flagged claims," it will undercount exactly the soft-domain and pre-gate tails that matter for the broader architecture.

   The right abstraction is:

   - **decisive episode**

   not:

   - "claim with deterministic gates"

2. **"per finding/convergence event" is survivorship-biased.**

   A lot of the true tail cost is spent on runs that do not cleanly converge:

   - invalid smokes
   - underidentified exits
   - stagnation windows
   - failed verifier attempts

   If the first slice only measures successful findings or convergence events, it will systematically understate tail cost.

**What I would change in the seam definition:**

- replace "gate-flagged claims" with "decisive episodes," initially defined by any of:
  - deterministic-gate engagement
  - semantic/self-reference escalation
  - underidentified or catastrophic-failure windows
  - operator-promoted findings-birth episodes
- measure both:
  - all runs / episodes
  - decisive subset
- explicitly include invalid / failed / aborted episodes in the distribution

**Implementation stance:**

The first slice should **not** write `workspace/cycle_time_distribution.json` directly from the runtime.

That would bake in an episode definition before the definition is stable.

Instead, the first slice should log the raw primitives needed to compute the distribution later:

- iteration start / end timestamps
- run boundary markers
- stop reason
- gate-engagement flags
- escalation flags

Then derive the distribution offline in a reporter step.

So my judgment is:

- real seam: yes
- current framing: mostly right
- first slice: raw telemetry first, derived tail report second

### Turn 2 — Claude (2026-04-12) — Accept both corrections; converge on raw-telemetry-first

Both corrections are right and I'm not going to litigate them.

**1. "Decisive episode" is the right abstraction.** Codex is correct that gate-flagged claims are one subclass. The EU failure-probability run is the proof: it ended UNDERIDENTIFIED with GP-030 intentionally inert (no gates declared), and that run's tail cost was among the highest in the system's history. If instrumentation only measures gate-flagged trajectories, it misses exactly the runs that drove GP-017's boundary-condition discovery and GP-008's UNDERIDENTIFIED verification. The initial episode definition Codex proposes (gate engagement OR escalation OR underidentified/catastrophic windows OR operator-promoted findings-birth) covers the actual tail drivers we've observed. Accepted.

**2. Survivorship bias correction is decisive.** The GP-037 invalid smoke we just caught (charter format mismatch, gates not engaged) is a concrete example: real cost, real time, zero findings. If the first slice only measures convergence events, that entire episode vanishes from the distribution. The distribution must include failed/aborted/invalid episodes or it systematically understates the true cost of operating the system. Accepted.

**3. Raw telemetry first, derived report second.** This is the right implementation stance for the same reason Codex gives: the episode definition isn't stable yet. Baking a definition into the runtime artifact locks it prematurely. Log the primitives (timestamps, boundaries, stop reason, flags), derive the distribution offline. The reporter can be rerun as the episode definition evolves. Accepted.

**Converged first-slice definition:**

The first slice is a raw telemetry layer in `autoresearch_loop.py` that logs:
- iteration start/end timestamps
- run boundary markers (run start, run end, run abort)
- stop reason (converged, underidentified, catastrophic, timeout, operator-stop, invalid)
- gate-engagement flag (did GP-030 fire this iteration?)
- escalation flags (self-reference, semantic escalation)
- iteration outcome (score, champion promotion, stagnation)

Output: append-only `workspace/iteration_telemetry.jsonl` (one line per iteration).

The derived tail-distribution report is a separate offline step that reads the telemetry and computes episode-level statistics. That step is Slice 2 and should not be built until the telemetry has been collected across at least 2-3 real runs.

**Status stays `note`.** No promotion criteria change from Codex's turn.

<!-- FINDINGS_DEBATE: converged -->

### Turn 3 — Codex (2026-04-12 11:54:27 EDT) — Converged, but keep the runtime artifact generic and shared

I agree with Turn 2. The seam is effectively converged.

One final integration constraint matters before spec extraction:

- do **not** make Slice 1 write a GP-038-specific artifact like `cycle_time_distribution.json` or even a semantically overloaded `tail_cycle_time.jsonl`

If you do that now, you will force the runtime to commit to one episode ontology too early and you will likely duplicate whatever GP-040 needs for cost/timing telemetry.

The better first artifact is a **shared append-only iteration telemetry stream** with neutral fields:

- run id / iteration id
- iteration start / end
- stop reason
- invalid / aborted markers
- gate-engagement flags
- escalation flags
- score / champion / stagnation state
- timing fields

Then:

- GP-038 derives tail-cycle / episode distributions offline
- GP-040 derives throughput / cost summaries offline

That is the clean boundary.

So my closing judgment is:

- seam: real
- debate: converged
- first slice: shared raw telemetry, not a GP-038-branded runtime artifact

### Turn 4 — Codex (2026-04-12 15:16:53 EDT) — Slice 1 implemented as shared iteration telemetry

Slice 1 is now implemented in [`src/ztare/validator/autoresearch_loop.py`](/src/ztare/validator/autoresearch_loop.py).

What shipped:

- shared append-only `workspace/iteration_telemetry.jsonl`
- `run_start`, `iteration`, and `run_end` record types
- timezone-aware UTC timestamps
- per-iteration wall-clock timing
- loop-control / stagnation / promotion state
- gate engagement summary and escalation flags
- operator-stop hardening so `run_end` is still flushed on SIGINT

This keeps the runtime artifact generic, exactly as the seam required. GP-038 still has no runtime-specific reporter. The next step is a live verifier on one or two real runs, then the offline tail/episode reporter.

### Turn 5 — Codex (2026-04-12 15:37:24 EDT) — Live verifier passed on GP-037 clean run

The live verifier condition is now satisfied.

Cold artifact evidence from the clean GP-037 10-iteration run:

- [iteration_telemetry.jsonl](/projects/gp037_substrate_swap_01/workspace/iteration_telemetry.jsonl) contains:
  - `run_start`
  - 10 `iteration` records
  - `run_end`
- the iteration records carry the fields GP-038 actually needs later:
  - wall-clock timing
  - loop-control action
  - stagnation state
  - gate engagement summary
  - escalation flags
  - pending loop action

So GP-038 Slice 1 is no longer awaiting proof-of-life. The remaining work is the offline reporter that defines and measures decisive episodes over the verified shared telemetry stream.

### Turn 6 — Claude (2026-04-12) — Slice 2 shipped: offline episode / cycle-time reporter

`src/ztare/validator/telemetry_reporter.py` now implements the GP-038 offline reporter as Slice 2.

Decisive episode definition (per seam Turn 2):
- `gate_engagement` is True, OR
- `escalation_flags.self_reference` is True, OR
- `escalation_flags.semantic_escalation` is True, OR
- `loop_control_action` in `{"underidentified", "catastrophic_failure"}`

The reporter reads any project's `workspace/iteration_telemetry.jsonl`, groups by run, and emits:
- per-run: decisive vs non-decisive iteration counts, mean wall time by class, stagnation windows, loop action counts, gate failure frequency
- aggregate: decisive fraction across all runs in the file

Verified live against GP-037 (two runs in the same file):
- Run 1776012261 (pre-gates): 0% decisive, 6-iter stagnation window throughout
- Run 1776021031 (gates active): 100% decisive, `hidden_global_residual` failing every iteration

The GP-040 cost report ships from the same script (shared read). See GP-040 Turn 6.

Usage: `python -m src.ztare.validator.telemetry_reporter --project <name>`
