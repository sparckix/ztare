# GP-190 Post-Run Discriminator Queue + Briefing Budget Spec

## Status

Active — opened 2026-04-30 12:38:12 EDT after ex-post implementation made the
feature heavier than the original seam.

## Scope

This spec governs two related apparatus changes:

- post-run discriminator queue generation from meta-audits, cold shots, and
  deterministic artifact replay;
- meta-cold-shot frontier script scaffolding, because recent gp163d/NS progress
  repeatedly required narrow Python runners chosen from reusable script
  families before GPU/API budget was spent;
- configurable research-taste opportunity cards, because attention routing can
  be partly mechanized without becoming truth scoring;
- mutator briefing tiering/budgeting, because prompt mass is the main runtime
  and quality risk in the current ZTARE loop.

This spec does not govern:

- scientific validity of gp163d/NS results;
- GPU-run orchestration;
- full supervisor closure automation;
- changing the mutator/judge scoring contract.

## Eigenquestion

Can ZTARE recover the operator's next-discriminator discipline without turning
each iteration into a slow, over-briefed bureaucracy?

The smallest discriminating question is:

> Does the loop produce a concise, promotion-safe next-test queue and a bounded
> mutator prompt packet, while preserving enough signal to reduce R1 retries and
> avoid repeating already-falsified directions?

## Why This Exists

Recent gp163d and NS progress happened largely outside the core iterative
ZTARE loop: operator/Codex chose tests, ran GPU jobs, interpreted failures, and
updated ledgers. That is not a failure by itself; it is a source of primitives.

The engineering risk is different:

- if we wire all operator intuition into the loop as always-on prose, iteration
  time and prompt entropy explode;
- if we do not wire any of it, ZTARE stays slower and less capable than the
  manual cold-shot + scipy/GPU workflow;
- if we let weak post-run tests promote claims, the apparatus gains ceremony
  without epistemic force.

Therefore the implementation must be ex-post, opt-in, typed, and measured.

## Implemented Interfaces

### Discriminator Queue

Files:

- `src/ztare/orchestrator/discriminator_queue.py`
- `src/ztare/orchestrator/operator_replay_audit.py`
- `src/ztare/orchestrator/cold_shot_discriminator.py`
- `src/ztare/orchestrator/promotion_guard.py`

Artifacts:

- `projects/<slug>/workspace/next_discriminator_queue.jsonl`
- `projects/<slug>/workspace/next_discriminator_queue.replay.jsonl`
- `projects/<slug>/workspace/background_debt_ladder_<label>.json`

Rules:

- queue rows are schema v2;
- `can_support_promotion=true` only when `license_stage="commit"` and
  `severity_level >= 4`;
- meta-audit detector proposals default to L2 and cannot promote findings;
- cross-domain analogy may remain `scratchpad`; promotion requires a transfer
  license;
- queue closure is explicit via `mark-status`, with evidence artifacts.

### Autoresearch Wire-In

File:

- `src/ztare/validator/autoresearch_loop.py`

Flags:

- `enable_post_run_meta_audit=true` calls the existing LLM meta-audit and then
  appends typed queue proposals.
- `enable_post_run_discriminator_queue=true` runs deterministic replay over
  durable artifacts and writes `.replay.jsonl`.
- `post_run_discriminator_sources=[...]` optionally overrides replay sources.

Default:

- both features remain opt-in;
- no post-run discriminator hook changes champion selection or loop control.

### Meta-Cold-Shot Frontier Script Scaffold

File:

- `src/ztare/orchestrator/frontier_script_scaffold.py`

Purpose:

- convert the repeated manual pattern "what Python should Codex write next?"
  into a strict, reviewable object;
- select a script family and existing template before proposing code;
- force the proposed script to declare the eigenquestion, hypothesis, inputs,
  outputs, smoke test, abort conditions, and safety notes.

Rules:

- the scaffold is a prompt/parser/validator, not an LLM caller and not a
  runner;
- `script_family` and `template_script_path` are required so the apparatus
  reuses known patterns such as
  `run_cold_shot_cone_mass_anti_cancellation.py` instead of freelancing;
- `code_edit_mode` is one of `new_file_from_template`, `patch_existing`,
  `no_code_needed`, or `unsafe`;
- proposed code is rejected if it uses absolute/parent paths, non-`.py`
  targets, network/SSH/destructive imports or calls, banned shell patterns, or
  lacks an `if __name__ == "__main__"` guard;
- command and smoke-test proposal strings are rejected if they contain obvious
  shell/destructive/network patterns or do not start with a Python interpreter;
- artifact packets are bounded to declared allowed roots before file contents
  are sent to a model;
- invalid model output is not cached before strict JSON parsing and validation
  succeed;
- a blank `code` field is admissible only for `no_code_needed` or `unsafe`.

### Research Taste Opportunity Cards

Files:

- `org/preferences/daniel_alami.yaml`
- `src/ztare/orchestrator/research_taste.py`

Purpose:

- make the principal's attention-routing preferences explicit and auditable;
- rank candidate next moves by vector fit to declared preferences;
- preserve the boundary that preference priority cannot promote epistemic
  confidence.

Current axes:

- unresolved/outstanding problem resolution;
- prize, money, publication, IP, or funding potential;
- solvability with current ZTARE/Codex architecture plus bounded extensions;
- contribution to self-recursive governance.

Rules:

- output is an opportunity card, not a finding;
- `advisory_sort_score` may sort the queue, but cannot affect judge scores,
  champion selection, promotion readiness, or public-claim language;
- each card carries anti-Goodhart checks, including whether a cheapest
  discriminator and kill condition exist;
- `operator_decision` defaults to `unset` and remains first-class data.

### Mutator Briefing Budget

File:

- `src/ztare/orchestrator/mutator_briefing.py`

Rules:

- T0/T1/T2 providers render by default;
- T3 renders after `stagnation_count > 2`;
- T4 renders after `stagnation_count > 4`;
- T5 hibernates unless forced;
- `briefing_budget_chars` defaults to 12000;
- budget trimming applies only to T3+ providers;
- `briefing_tiered_disable=true` restores legacy all-provider behavior.

Audit fields now persisted in `workspace/mutator_briefing_iter_NNN.md`:

- active providers;
- briefing chars and budget;
- tier-gated providers;
- budget-trimmed providers;
- render time;
- per-provider render times.

## Acceptance Criteria

### Mechanical Acceptance

Already satisfied:

- `discriminator_queue_fixture_regression`: pass;
- `cold_shot_discriminator_fixture_regression`: pass;
- `frontier_script_scaffold_fixture_regression`: pass;
- `frontier_script_scaffold_runner_fixture_regression`: pass;
- `operator_replay_audit_fixture_regression`: pass;
- `promotion_guard_fixture_regression`: pass;
- `research_taste_fixture_regression`: pass;
- `mutator_briefing_fixture_regression`: pass;
- `scripts.validate_autoresearch_arch_map ex-post`: pass.

### Runtime Acceptance

Before enabling broadly, run at least one low-cost one-iteration smoke on a
closed project with:

- `enable_post_run_discriminator_queue=true`;
- tiering enabled;
- `briefing_budget_chars=12000`;
- no expensive post-run LLM meta-audit.

Pass if:

- wall-clock overhead excluding the mutator/judge LLM calls is under 10 seconds;
- mutator briefing injected chars are under budget unless T0/T1/T2 alone exceed
  it;
- `workspace/mutator_briefing_iter_001.md` records timing diagnostics;
- replay queue is written without crashing.

### Quality Acceptance

The tiered briefing is mechanically correct, but not yet proven better.

To call it good as a mutator-quality improvement, run an A/B on a closed
substrate that previously suffered R1 retries:

- A: tiering enabled, default budget;
- B: `briefing_tiered_disable=true`;
- same project, same model pair, one to three iterations each.

Pass if A has:

- fewer R1 retries or no increase;
- lower prompt/input tokens;
- no worse final score or information-yield classification;
- no missing decisive provider in the saved briefing audit.

If A is faster but loses decisive signal, demote the tier table and tune
provider classifications rather than declaring success.

## Bear Cases

### Bureaucratic Drag

The queue can become a second task manager. Mitigation: post-run replay is
opt-in and typed; promotion guard reads status, it does not dispatch work.

### Unsafe Script Autonomy

The manual frontier loop benefits from quickly writing one-off `.py` files,
but arbitrary LLM-generated scripts are an unacceptable execution surface.
Mitigation: the scaffold mechanizes script-family selection and static
rejection only. Codex/operator still applies patches, runs smoke tests, and
decides whether GPU/API execution is warranted.

### Weak Inquisitor

A weak discriminator can rubber-stamp a claim. Mitigation: only closed/passed
L4/L5 commit-stage rows with evidence artifacts support F/INS promotion. This
guard is necessary but not sufficient: the Director must still state why the
row is relevant to the claim and why the discriminator is hostile rather than
ceremonial.

### Preference Goodhart

Money/prize potential and principal preference are attention-routing variables,
not truth variables. Mitigation: research-taste cards cannot mark a finding
promotion-ready and cannot weaken the GP-190 promotion guard.

### Prompt Entropy

Briefing providers can make the mutator slower and less decisive. Mitigation:
tiered fade-in, budget trimming for T3+, and persisted prompt-mass telemetry.

### PDE Overfit

Operator replay templates were first extracted from gp163d and NS. Mitigation:
generic non-PDE templates now cover farther-tail drift, retrieval traps,
complexity laundering, distribution shift, and transfer licensing.

## Next Verification Slice

Run the cheapest closed-project smoke:

```bash
python3 -m src.ztare.orchestrator.mutator_briefing_fixture_regression
python3 -m src.ztare.orchestrator.operator_replay_audit_fixture_regression
python3 -m src.ztare.orchestrator.promotion_guard_fixture_regression
```

Then run one real `autoresearch_loop` iteration on a closed/non-frontier
substrate with `enable_post_run_discriminator_queue=true` and no live
meta-audit. Record wall-clock, input tokens, R1 strikes, briefing chars, and
queue row count.

For the meta-cold-shot script scaffold, replay one closed frontier decision:
feed the scaffold a packet containing
`run_cold_shot_cone_mass_anti_cancellation.py` and verify that it chooses a
template fork or no-code diagnostic, not an unbounded bespoke runner.

For research taste, rank a closed queue and compare the top cards against the
principal's actual choices. Use the comparison to calibrate attention routing,
not to optimize for more F-rows.

## Verdict

The implementation is acceptable as opt-in instrumentation. It is not yet
accepted as default always-on ZTARE behavior. The next decision is empirical:
does tiered briefing reduce prompt mass/R1 retries without suppressing the
signal that actually changes the next move?
