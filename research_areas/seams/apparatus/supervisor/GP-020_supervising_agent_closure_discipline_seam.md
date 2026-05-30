# GP-020 Supervising-Agent Closure Discipline Seam

> **Seam metadata** · `seam_id:` GP-020 · `track:` apparatus · `status:` Closed, 2026-04-14. Supervisor loop closed Turn 55 with full · `last_updated:` 2026-05-17


## Problem Snapshot

ZTARE's supervising-agent stop/close recommendations are still too narrative.

The system can now:

- score theses under hard gates
- separate latest vs champion artifacts
- type forecasts
- emit evidence gaps
- emit derived constraints

but it still lacks a hardened mechanism for saying:

- this search space is locally stalled but not globally exhausted
- this work should remain artisanal
- this work is now ready for supervisor execution
- this supervisor run is evidence of recursive self-improvement rather than just packet execution

That gap showed up repeatedly in operator-assisted work:

- premature stop advice
- overconfident exhaustion claims
- ambiguous handoff boundaries between artisanal and supervisor modes

## Current State

This seam is now concrete enough to track separately from philosophy.

New evidence from the recent operator / Claude / Codex discussion:

- the supervisor is a project runner, not just an execution wrapper
- current project types are still mostly execution-shaped
- artisanal work is generating the labeled catches needed to build the missing self-review project type

So the seam is no longer “should GP-020 exist?”

It is:

- what contract turns closure judgment into a typed surface?
- when does artisanal work hand off to supervisor work?
- what evidence is strong enough to say the supervisor can now run recursive self-review projects rather than only bounded packets?

## Debate Log

### Turn 1, Historical failure pattern

The EU `0 -> 83` episode showed the original closure failure clearly:

- a single local crater was treated as proof of exhaustion
- the operator overruled it
- the loop found a real basin

This established the primary GP-020 rule:

- narrative impossibility claims from the supervising agent are not enough

### Turn 2, Claude / operator reflection

Claude framed the recent work as a two-mode system:

- artisanal mode for topology discovery and pre-registration
- supervisor mode for contractual execution after the spec freezes

This was directionally right, but too narrow.

### Turn 3, Operator correction

The operator correctly pushed back:

- the whole point of the supervisor was not just packet execution
- it was also meant to run recursive self-improvement projects on ZTARE's own artifacts

This corrected the scope boundary. The supervisor is not merely an execution layer. It is a project runner whose current project types are narrower than the architecture's intended scope.

### Turn 4, Independent synthesis

My read is:

- “pre-registration as the switch” is mostly right, but incomplete
- a frozen spec is enough for execution-style projects
- self-review projects need one more prerequisite:
  - the failure-family taxonomy and catch logic must also be explicit enough to score mechanically

That means the artisanal thread has been doing two things at once:

- generating paper-4-style evidence of recursive epistemic gain
- generating labeled catches for GP-020 itself

### Turn 5, Concrete labeled failures from this phase

This session produced at least four GP-020-relevant labeled failures:

1. local failure mistaken for global exhaustion
2. confident pessimism framed as humility
3. profile-dependent architectural claim presented as unconditional
4. optimization overshoot that removed decisive capability

These are not abstract lessons. They are training examples for the future self-review project type.

### Turn 6, Current conclusion

The artisanal work was not a detour from the supervisor architecture.

It was the hand-run prototype of the missing supervisor project class:

- recursive self-review of ZTARE's own claims and artifacts

So GP-020 is the seam that connects:

- paper 4's strongest evidence
- supervisor project typing
- eventual automation of operator-style catch patterns

### Turn 7, Phase 1 first slice landed

Phase 1 of the spec calls for freezing the labeled failure families
from recent artisanal threads before any typed closure surface can
be designed. The first slice of that work is now on disk, kept
separate from this seam so it can grow without churning the framing:

- `research_areas/catch_grammar/corpus.md`, schema plus four labeled
  entries drawn from the recent operator / Claude / Codex thread:
  - defining_yourself_into_victory (philosophical form)
  - confident_pessimism_as_humility
  - profile_dependent_claim_as_unconditional
  - optimization_overshoot
  Each entry carries `failure_family`, `trigger_condition`,
  `evidence_shape`, `counter_move`, `verification_check`,
  `false_positive_mode`, and `provenance`.
- `research_areas/catch_grammar/probes/probe_01_gp023_seam.md`, 
  first probe design. Runs the four `verification_check` rules by
  hand against the GP-023 seam, with operator-graded success
  criteria. GP-023 is the target because it already contains a
  known profile-dependence catch and its Phase 0 is frozen at
  pre-registration, so the probe cannot contaminate the
  experiment.

This first slice is deliberately not a frozen grammar. It is the
seed dataset the spec's Phase 1 asks for. The closure-category /
reason-class work still has to wait on the verifiers for GP-017,
GP-021, and GP-022 to land, the corpus is only the labeled-catch
half of Phase 1.

The operator framing question, "how to enact the first
self-recursive improvement project, more upleveled than stage2", 
is answered by Phase A here: run the hand probe on an existing
seam, use the operator as the grader, and let that result
determine whether the grammar is specific enough to carry any
supervisor weight in Phase B. No supervisor code changes are
required for Phase A.

### Turn 8, Sequencing decision (2026-04-10)

Discussion point: does GP-020 self-audit block Planck (GP-023)?

Gemini argued yes: if the grammar cannot catch arrogance in a
static seam, it cannot catch subtler arrogance in a 100-iteration
starvation run. Codex argued partly no: provider fallback is the
actual Planck prerequisite, and paper 4's current missing
section is still backed by an existing stage2 supervised build
run, not a self-audit. Operator sided with Codex on sequencing.

Agreed sequence (decisive for paper 4 + Planck):

1. Provider fallback / failover policy lands first (Codex owns).
   - why: a 503 at iteration 92 destroys starvation momentum and
     burns the run.
   - scope: detect provider-side error in `autoresearch_loop.py`,
     hot-swap to a secondary provider, preserve iteration state
     across the swap.
2. Run `supervisor/program_manifests/stage2_derivation_seam_hardening.json`
   through the supervisor (Codex owns).
   - why: paper 4 Section 5.6 still needs a real supervised
     build-pipeline run with telemetry. The existing stage2
     manifest is the correct project for that, not a self-audit.
   - this is the existing execution-shaped project type working
     as intended, not a new project class.
3. Run GP-020 Phase A probes by hand (Claude owns).
   - why: test whether the catch grammar is specific enough to
     audit a real seam at all. This is the cheap falsification
     move. If the grammar is too vague to execute, no scripted
     audit is worth building.
   - scope: probe 01 against GP-023, optionally probe 02 against
     GP-017 / GP-021 / GP-022 if probe 01 is useful.
   - grader: operator.
4. Open the first real GP-020 self-audit supervisor project
   (operator-commanded, API-executed).
   - why: Phase B. Only possible after Phase A proves the
     grammar can discriminate. This defines a new supervisor
     project type where the input is seams/specs rather than
     code and the output is structured catch findings rather
     than diffs.
   - scope TBD after Phase A result.
5. Run Planck (GP-023 starvation run).
   - prerequisite: step 1 (fallback) must land first.
   - step 4 is a better and more upleveled supervisor story,
     but it is NOT a Planck prerequisite.

Role clarification:

- GP-020 is about the missing self-review project type.
- The probes (catch_grammar/probes/) are Phase A: test whether
  the catch grammar is specific enough to audit a real seam by
  hand.
- If Phase A works, Phase B opens: supervisor self-audit of
  ZTARE's own seams/specs as a new project class.
- Paper 4 Section 5.6 uses the existing stage2 supervisor run,
  not any of the above. Step 2 is what fills that gap.
- The next upleveled supervisor story (for a later section or a
  future paper) is the GP-020 self-audit. It does not backfill
  Section 5.6.

### Turn 9, Provider fallback prerequisite landed

The provider-fallback prerequisite from Turn 8 is now implemented in
the shared runtime rather than as a one-off loop patch:

- `src/ztare/common/llm_runtime.py` now retries the requested model and,
  after persistent transient failures, hot-swaps to a configured
  secondary provider/model.
- fallback is provider-agnostic and therefore applies to validator,
  compiler, synthesis, and workspace flows rather than only
  `autoresearch_loop.py`.
- evaluator artifacts now record the effective judge models used during
  the run, and the score-regime fingerprint changes when a fallback
  model participates.

Why this matters for the GP-020 discussion:

- it closes the operational prerequisite for Planck without pretending
  mixed-provider evaluation is directly comparable to single-provider
  evaluation
- it strengthens paper 4's "bounded execution under contract" story,
  because the runtime now preserves program continuity under provider
  instability without laundering regime changes

What it does **not** resolve:

- GP-020 Phase A probe design is still the next self-audit step
- paper 4 Section 5.6 still needs the real stage2 supervised run
- fallback hardening is execution infrastructure, not the self-review
  project type itself

What this resolves:

- Self-audit before Planck is no longer framed as a hard block.
  It is framed as the correct next supervisor project type, but
  its cost is not paid out of the Planck timeline.
- Phase A still has to run, because it is the only honest way
  to know whether Phase B is even buildable. But Phase A runs
  in parallel with Codex's stage2 work, not as a gate in front
  of Planck.

## Status

Closed, 2026-04-14. Supervisor loop closed Turn 55 with full M-form architecture (write-scope guard, backlog, proposal, manifest, usage ledger). Closure discipline rules are now operational. Stale-active status corrected on visibility audit.
