# GP-157 §8.6 — R10-R16 Backport Scoping (2026-05-06)

> **Seam metadata** · `seam_id:` GP-157 · `track:` apparatus · `status:` OPEN. No commitment to a delivery date. Ship when GP-220 aud · `last_updated:` 2026-05-08


**Status:** active *(inferred 2026-05-08 — needs operator review)*

## Why this exists

GP-157 v5.0 spec §8.6 acknowledges a registry leak: R10 and R11
follow the Cage-routed pattern (gate registered with `can_handle`
predicate, dispatched through Cage); R13, R14, R15, R16 were direct-wired
into autoresearch_loop.py instead of going through Cage. The spec
calls this out explicitly: "Existing direct-wired gates are tracked
for backport in §8.6."

The backport hasn't shipped. This doc scopes it.

## What's at stake

The Cage-routed pattern is the v5.0 design intent: every gate
declares `can_handle(substrate, candidate) -> tuple[bool, reason]`,
the Cage dispatcher topo-sorts by declared dependencies and engages
them in order, every engagement gets logged to
`workspace/cage_engagement.jsonl` with deterministic provenance.

Direct-wired gates bypass this: they're called inside
autoresearch_loop conditionally on rubric flags, with bespoke
engagement logging (or none), and no `can_handle` predicate. Effects:

1. **Engagement telemetry is non-uniform.** R10/R11 emit through
   cage_engagement.jsonl; R13-R16 emit through their own per-primitive
   files. The future ROI audit (GP-220) has to special-case each.

2. **Topo ordering is implicit.** R13-R16 fire in autoresearch_loop's
   conditional sequence; if a future R17 needs to run after R14 but
   before R15, the only way to enforce that is to edit
   autoresearch_loop's iter-body. R10/R11 already enforce ordering
   through Cage's DAG.

3. **The R8/R9 carve-out pattern doesn't propagate.** R8/R9 use
   "default ON for matching substrate-class, opt-OUT via rubric flag"
   per the v5.0 design intent. R13-R16 use "opt-IN via rubric flag"
   — the inverse. Because they live in autoresearch_loop instead of
   Cage, the default-on logic would have to be reimplemented per gate.

## What needs to ship

For each of R13, R14, R15, R16: a `can_handle` predicate, a Cage
registration, and removal of the direct-wire from autoresearch_loop.

### R13 — substrate_critic

**Currently:** `src/ztare/diagnostics/substrate_critic.py::register_r13_gate`
exists (per spec) but is direct-wired. The pre-flight + post-fit
calls happen from autoresearch_loop conditionally on rubric class.

**Backport sketch:**

```python
# src/ztare/gates/substrate_critic_gate.py
class SubstrateCriticGate:
    name = "substrate_critic"
    phase = ["PRE_FIT_PREFLIGHT", "POST_FIT"]
    dependencies = []  # no upstream gates required
    
    def can_handle(self, substrate, candidate) -> tuple[bool, str]:
        cls = substrate.cage_meta.get("class")
        if cls not in {"nd_features", "time_series"}:
            return False, f"R13 not applicable to substrate class {cls}"
        if substrate.rubric.get("disable_substrate_critic", False):
            return False, "R13 disabled by rubric flag"
        return True, "R13 applicable"
    
    def engage_pre_fit(self, substrate, candidate, ctx) -> CageEngagementResult:
        ...
    
    def engage_post_fit(self, substrate, candidate, ctx) -> CageEngagementResult:
        ...
```

Effort: 4-6 hours. The body of substrate_critic already exists; the
work is wrapping it in the Cage Protocol + removing the direct
wire-in.

### R14 — noise_profile

**Currently:** `src/ztare/diagnostics/noise_profile.py::register_r14_gate`
exists. Same direct-wire pattern as R13.

**Backport sketch:** symmetric to R13. The `can_handle` checks for
substrate class in `{nd_features, time_series, 1d_curve, 1d}` and the
`disable_noise_profile` opt-OUT flag.

Effort: 3-4 hours.

### R15 — ANALOGY (GP-164 L1)

**Currently:** `src/ztare/fit/analogy.py::register_r15_gate` exists.
Direct-wire dispatches based on `enable_analogy=true` rubric flag and
stagnation predicates.

**Backport sketch:** opt-IN via rubric flag (NOT default-on);
`can_handle` returns False unless `rubric.enable_analogy=True` AND
`should_engage(rubric, fit_result_json, stagnation_count)` returns
True. Phase: `POST_FIT`.

Effort: 2-3 hours (smaller scope; opt-in already encoded in
should_engage).

### R16 — framer (GP-152 v2.0, 1D path)

**Currently:** `src/ztare/framer/active_framer.py::register_r16_gate`
exists. Direct-wire dispatches based on `enable_framer=true` AND
substrate class AND parsed-data length.

**Backport sketch:** `can_handle` enforces all three preconditions
(rubric flag, class, length ≥ 80). Phase: `PRE_FIT`. **The N-D
framer invocation is deferred** per the spec — it requires POST_FIT
dispatcher to pass `_vis` and rubric-mirror context through the
candidate object. That refactor is out of scope here.

Effort: 3-4 hours for the 1D path; N-D path deferred to follow-up.

### Net effort

12-17 hours across the four gates, none of them blocked on each other.
Could be parallelized across two sessions or sub-agents.

## Why ship this now

Two compounding reasons:

1. **GP-220 ROI audit needs uniform telemetry.** The proposed ROI
   scorecard (`reflexive_primitive_roi.json`) reads engagement stats
   per primitive. With direct-wired gates, every primitive needs a
   special-case reader. With Cage-routed gates, one
   `cage_engagement.jsonl` reader covers them all. Backporting first
   makes GP-220 a one-day implementation; without backport, it's
   three-day-plus.

2. **Phase 4g main-loop wrap depends on it.** The future
   `orchestrator/main_loop.py::run_main_loop()` extraction will be
   easier if phase-conditionals on rubric flags are gone. Each
   direct-wired R13-R16 contributes ~50-100 lines of conditional
   code to the iter-body. Backporting them moves that logic into
   gate modules, shrinking the iter-body proportionally.

## What this seam is NOT

- Not a re-design of the gates themselves. Their internals are
  unchanged; only the dispatch wrapping moves.
- Not a backport of R8/R9 (already Cage-routed correctly).
- Not the R10/R11/R12 backport (also already Cage-routed; the spec
  §3a clarification was about the dispatch architecture going forward,
  not retroactive).

## Pointers for the implementer

- `src/ztare/gates/cage.py` — Cage Protocol + dispatch entry points
- `src/ztare/gates/registry.py` — gate registration pattern
  (existing `can_handle` examples for `pec_f_deprecation_guard_gate`,
  `pde_inequality_dimensional_gate`, `g_circ`)
- `src/ztare/gates/cage.py:check_feature_coverage_adequacy` — R8
  reference implementation showing the Cage-routed pattern
- `src/ztare/gates/cross_class_extrapolation_gate.py` — R10/R11
  reference implementation; closest in shape to what R13-R16
  should look like post-backport
- The four direct-wired gate modules: `substrate_critic.py`,
  `noise_profile.py`, `analogy.py`, `active_framer.py` — bodies
  to wrap, not rewrite

## Status

OPEN. No commitment to a delivery date. Ship when GP-220 audit
needs uniform telemetry OR when Phase 4g main-loop wrap starts
needing the iter-body simplified.
