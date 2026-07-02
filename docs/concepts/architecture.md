---
description: "The current ZTARE architecture: in-loop validation, out-of-loop research operations, and reflexive intelligence."
---

# ZTARE Architecture

> Up: [Documentation map](../README.md)

ZTARE is a filesystem-first research workbench for bounded claims,
adversarial review, proof work, project evidence, and organizational learning.
That original autoresearch loop still matters: it is the in-loop validator,
testing a bounded claim against bounded evidence. But it is now one plane of
four:

1. Evidence and artifacts: source material, bounded evidence, project
   workspaces, receipts, and review files.
2. In-loop validation: adversarial claim testing under deterministic checks.
3. Out-of-loop research operations: roles, mandates, tasks, checks,
   ledgers, projects, and human-agent work outside a single validator run.
4. Reflexive intelligence: forecasts, action-impact records, trajectory
   mining, experiment ledgers, catch ledgers, and read models that help the
   organization learn from its own behavior.

ZTARE rests on three refusals:

```text
Do not ask an AI to certify its own work.
Do not ask a chat transcript to be organizational state.
Do not let intelligence stay trapped in conversation.
```

ZTARE separates generation, verification, authority, execution, and learning
so that each layer can fail visibly.

If you are reviewing whether the architecture has evidence behind it, start with
the [evidence atlas](../evidence_atlas/README.md): the atlas ties
each piece of machinery to its claim cards, experiments, runnable checks, and
caveats. This page is the machinery itself.

## Contents

Orientation, [Model capability is not the unit](#model-capability-is-not-the-unit-of-analysis) ·
[Research trace flywheel](#research-trace-flywheel) ·
[How next work is chosen](#how-next-work-is-chosen) ·
[Architecture at a glance](#architecture-at-a-glance) ·
[Work item lifecycle](#work-item-lifecycle)

Where things live, [Repository topology](#repository-topology) ·
[Cross-cutting invariants](#cross-cutting-invariants) ·
[The four hard boundaries](#the-four-hard-boundaries)

The four layers, [1 · Evidence & artifacts](#layer-1-project-evidence-and-artifacts) ·
[2 · In-loop validator](#layer-2-the-in-loop-validator) ·
[3 · Out-of-loop research ops](#layer-3-out-of-loop-research-operations) ·
[4 · Reflexive intelligence (capability catalog)](#layer-4-reflexive-intelligence)

Operating model, [Human reviewers & agentic workers](#human-reviewers-and-agentic-workers) ·
[Canonical state vs. projections](#canonical-state-vs-projections) ·
[Public repo boundary](#public-repo-boundary)

Reference, [What to use when](#what-to-use-when) ·
[Failure modes caught](#failure-modes-the-architecture-is-built-to-catch) ·
[Maturity](#current-maturity) · [Documentation map](#documentation-map)

> Deeper maps: this page is the *navigable overview*. For the module-level
> family map see [system_position_and_module_map.md](system_position_and_module_map.md),
> for the LeanMill proof subsystem see [leanmill_architecture.md](leanmill_architecture.md),
> and for the reflexive layer see [reflexive_engineering.md](reflexive_engineering.md).

## Model capability is not the unit of analysis

A stronger model does not buy a stronger result. The same capability that searches
more of the space and proposes a sharper argument will also exploit a weak
evaluation surface, misattribute prior work, or quietly close a branch before
the evidence is in. A better model sharpens both edges at once.

So the model is only half of what produces auditable work. The other half is the
environment it runs inside: bounded evidence, judges it cannot see, deterministic
checks, ledgers that outlive the run, non-claims written down on purpose, and fast demotion of the wrong story. None of that comes from the weights.
It comes from the repository, which is what the rest of this page describes.

## Research trace flywheel

Most research organizations already run fragments of this loop: agents generate
candidate work, tools test it, experts review it, and the traces can feed
evaluation, post-training, or the next model. ZTARE makes the loop explicit and
pins it to a repository so it does not live in anyone's memory.

```text
research act -> artifact -> adversarial review -> check / demotion / null
-> source-readiness and claim ledger -> mined supervision signal
-> better future routing, prompts, checks, rubrics, and training/eval data
```

The transferable lesson is narrow: keep the full trace before it collapses into
a polished answer. The expensive part of research is rarely the answer that
shipped. It is the failed proof attempt, the source-blocked claim, the
attribution that had to be corrected, the causal story that got demoted; the judgments that cost the most and usually get thrown away. As supervision, those
are often worth more than the solution alone.

The use case, then, is to produce labeled traces of that judgment:

- generate hard research attempts under bounded evidence
- force independent critique and deterministic checks where possible
- label outputs as promote, demote, null, source-blocked, or needs-falsifier
- preserve provenance and non-claims alongside the answer
- train or evaluate future systems on those labeled traces and on final
  solutions

This is why a public workbench earns its place even where private labs already
run their own agent loops. A weight update ships the conclusion and hides the
institution that reached it. A filesystem-first repo keeps that institution in
view: the artifacts, the failed claims, the checks, the demotions, the source
gaps, the people who decided.

For plain-language definitions, see [glossary.md](glossary.md).

---

## How next work is chosen

ZTARE does not have one magic score. It combines several measurable signals,
each with a different job:

- **Support state:** source checks, evidence bindings, report-readiness
  contracts, and saved review records decide whether the project is ready for a
  run or needs repair first.
- **Compression quality:** BIC and MDL ask whether a candidate explanation,
  proof helper, route, or reusable artifact explains more with less. Lower BIC
  or MDL is better.
- **Difference from prior work:** overlap, graph-neighborhood, and novelty
  checks ask whether a move is genuinely different from what was already tried.
  Difference alone is not progress.
- **Information yield:** score movement, new attacks, new hinges, new
  primitives, added axioms, crashes, and repeated weak points decide whether the
  loop should continue, refresh, narrow, or pivot.
- **Compression progress:** the new advisory signal tracks when the last
  BIC/MDL-style improvement happened. If the loop keeps producing different
  attempts without making the project simpler to defend, it should narrow the
  evidence boundary or change route.

The compression-progress idea comes from
[Herrmann and Schmidhuber 2026](https://arxiv.org/html/2605.14831v1). Their
formal object is time-bounded Kolmogorov complexity, which is not computable in
ordinary project runs. ZTARE uses a grounded proxy instead: measured BIC, MDL,
or another lower-is-better description-length value already emitted by the run.
The implementation lives in
[`compression_progress.py`](../../src/ztare/validator/core/compression_progress.py).
For v1.1 it is advisory and should be replayed on historical projects before it
changes run admission or pivot timing.

---

## Architecture at a glance

```text
                         human reviewer
                               |
                               v
                    preferences / mandates / checks
                               |
          +--------------------+--------------------+
          |                                         |
          v                                         v
  out-of-loop research org                  in-loop validator
  roles, tasks, channels,                   bounded evidence,
  objectives, projects,                     adversarial agents,
  ledgers, daemons                          deterministic checks
          |                                         |
          +--------------------+--------------------+
                               |
                               v
                    reflexive intelligence layer
                    forecasts, action impact,
                    trajectory mining, catch ledger,
                    experiment ledger, read models
                               |
                               v
                   next action / stop / split / defer
```

The old mental model was:

```text
raw -> evidence -> adversarial loop -> synthesis
```

The current model is wider, though the product path should stay narrow:

```text
project brief -> trace readiness -> readiness check when needed -> bounded run
-> review/report export
```

The Project Workbench is the live projection of that path. It should open a
project folder even when the project brief is missing, then show the repair path
as project state instead of hiding the folder. Its shared project object joins
thesis, assumptions, sources, evidence, source health, run history, learned
constraints, report readiness, saved history, next action, and file-backed write
boundaries. The same object is served by the local workbench server, printed by
`ztare forensic-workbench project-state`, and stamped into saved project files.

Other modules attach to that path as instruments: proof work, graph diagnostics,
forecast rows, synthesis, reflexive mining, and org-runtime handoffs. A new
instrument should either consume an existing object on the path, write a saved
record that trace can read, or replace an older surface. If it creates a second
way to name the same state, it should be folded back before release.

The organizational mental model is:

```text
research organization -> chooses work
work may enter validator, proof, script, panel, or human-agent co-work
outcomes enter ledgers
ledgers update forecasts, routing, primitives, and future work selection
```

## Work item lifecycle

Most ZTARE work crosses the same interfaces even when the destination differs.
Those interfaces are explicit on purpose: a reader can replay a decision without
rerunning it.

```text
intake / source surface
-> route decision
-> bounded execution
-> recorded outcome
-> reflexive update
```

1. Intake names the boundary. A project-intake file or project workspace
   states the claim, sources, evidence references, non-claims, next falsifier,
   and launch command. If the source/evidence surface is not ready, the system
   should say so before any model call.
2. Routing chooses the next instrument. A task may enter the in-loop
   validator, stay in source repair, go to proof work, become a human-agent
   task, or stop. Primitive surfacing asks what code already exists. Move
   cards name the action family and nearest confuser. Pattern contracts name
   the fields that must exist before the route counts.
3. Execution stays bounded. In-loop work runs through mutator, reviewer,
   deterministic checks, and run artifacts. Out-of-loop work runs through role
   mandates, scripts, proof workflows, or explicit human-agent handoffs.
4. Outcomes become durable artifacts. Claims, demotions, source gaps,
   prediction-contract summaries, action-intelligence entries, proof records,
   and saved reviews are written as files or ledgers that can be inspected
   later.
5. The reflexive layer updates future routing. Forecasts, catch ledgers,
   primitive audits, graph diagnostics, and trajectory mining can recommend a
   next action or expose a repeated miss. They do not grant authority by
   themselves.

Two rules keep this lifecycle sane:

- A route entry is not evidence. It is a contract for what evidence or artifact
  must appear next.
- A dashboard or trace is not authority. It is a read model over files, ledgers,
  saved records, and signed store entries.

---

## Repository topology

The system has four kinds of moving parts:

- Kernel code in `src/ztare/`: importable, unit-testable behavior.
- Public control scripts in `scripts/public/`: thin workflow entry points
  over the kernel.
- *Canonical state*: files, ledgers, receipts, project workspaces, and daemon
  stores that can be replayed.
- *Projections*: read models, summaries, UIs, notifications, and reports that
  help people read the state but do not own it.

The generated capability catalog at
`analytics/public/index/architecture_index.jsonl` is the source for current
module counts. The table below is the functional map.

| Layer | Kernel subpackages (`src/ztare/…`) | Role |
|---|---|---|
| Cross-cutting | `gates/`, `common/`, `primitives/`, `notifications/` | deterministic checks, shared primitives, provider adapters, notification hooks |
| L2, Validation | `validator/`, `framer/`, `framer_gates/`, `rubrics/`, `scaffold/` | adversarial claim testing under rubrics |
| L3, Formal/proof | `leanmill/`, `formal/`, `motion/` | proof-work handoff boundary, compile/REPL interfaces, distance metrics; LeanMill internals live in [leanmill_architecture.md](leanmill_architecture.md) |
| L3, Research ops | `research_director/`, `orchestrator/`, `supervisor/`, `orchestration/`, `substrates/`, `roles/`, `sessions/`, `composition/` | mandates, dispatch, role daemons, project and domain plugins |
| L4, Reflexive | `forecasting/`, `fit/`, `synthesis/`, `signals/`, `experiments/`, `findings/` | forecasts, calibration, mining, learning |

Public script families: `scripts/public/control/` for lane workers, daemons,
and runners; `mining/` for reflexive mining; `lean/` for proof
providers/tooling; `validators/` for discipline linters; plus
`analytics_shared/`, `audits/`, and `utilities/`.

> The module-level family map (what each module does, by function) is
> [system_position_and_module_map.md](system_position_and_module_map.md). This table is
> the navigational index into it; that doc is the detail.

## Cross-cutting invariants

Beyond [the four hard boundaries](#the-four-hard-boundaries), four invariants hold across
every layer. They are what keep the system from drifting into the failure modes below.

1. Kernel/script dependency direction is one-way. `src/ztare/` never imports from
   `scripts/`. Durable, domain-neutral logic lives in the kernel (testable in
   isolation). `scripts/public/control/` holds only workflow-specific
   orchestration. A primitive that surfaces a reusable capability belongs in the kernel.

2. Domain-neutral core, project specifics plug in. Shared runners and checks carry
   no NS/Clay/PDE/APN logic. Domain behavior enters via config/registry/plugin
   (`org/structural_anchors/registry.yaml`, policy `domain_atlases`, and the
   project/domain contract), never hardcoded in shared code. The generic organization kernel itself
   lives in [cognitive-firm](https://github.com/sparckix/cognitive-firm). `org/` is the
   ZTARE tenant overlay.

3. Capability discoverability through one catalog. Reusable primitives (checks,
   operations, analytical/statistical utilities) are registered in
   `analytics/public/index/architecture_index.jsonl` and surfaced by
   `primitive_tick_surface.py` into the RD brief, plus a semantic precheck
   (`research_director/primitive_amnesia.py`: Gemini embedding atlas,
   semantic query, category tiers) so a task surfaces the capabilities that
   already exist before an agent rebuilds them. Anti-patterns/patterns surface from the
   [anti-pattern catalog](anti_pattern_catalog.md) via `build_context_primer.py`.

4. One owner for every public read model. Project intake owns the bounded
   pre-kernel handoff. `ztare autoresearch trace` owns the readiness and review
   read model. Synthesis reads trace context for reports and writes a
   deterministic `synthesis/report_support_contract.json` before rendering and
   does not redefine readiness. Projection and carrier replay audit historical
   state and do not launch work. UI and read-model surfaces must display those
   objects, link to the file, command, or saved record underneath, and avoid
   inventing private state.

5. Generation never ratifies itself. Across layers, the actor that proposes
   is never the actor that grants credit. Validator workers face an adversarial
   review panel, proof solvers propose while governance ratifies, and the commit
   membrane is the sole writer of the official store
   ([GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md)).

## LLM transport: the single dispatch door

Every model call in the codebase chooses between two transports through **one** mechanism, so the
choice is uniform across the kernel, the autoresearch loop, synthesis, evidence fetch, and any
auxiliary entry point (including `make synth`). There is no per-call-site bespoke flag.

- **API transport** (default) — the call goes straight to a provider SDK via `LLMRuntime.call_text`
  (Anthropic / OpenAI / Google / DeepSeek / Kimi / Grok), keyed by env API keys.
- **Subscription transport** — the call is routed to a local Codex / Claude CLI worker
  (`common/subscription_agent_runtime.py`), which bills the operator's *subscription* instead of an
  API key. Used when the operator wants to spend a flat subscription, not metered API tokens.

The door is `common/dispatch_model.py`:

- `resolve_dispatch_capability(call_site)` reads policy from the environment and returns `"llm"`
  (API) or `"agent"` (subscription). Policy precedence: a **scoped** env var
  `ZTARE_AGENT_DISPATCH_<CALLSITE>` (e.g. `ZTARE_AGENT_DISPATCH_SYNTHESIS`) wins over the **generic**
  `ZTARE_AGENT_DISPATCH`; unset / `off` ⇒ API.
- `dispatch_call_text(call_site, prompt, llm_response_call=…)` is the drop-in wrapper every site
  uses. On `"llm"` it just calls `llm_response_call` (the site's existing `LLMRuntime.call_text`);
  on `"agent"` it runs the subscription worker and returns a response-shaped wrapper so the site's
  existing text/JSON parser still owns validation. Same return shape either way.

How each layer opts in (all the same door, different call-site keys):
- **Autoresearch loop** — `validator/test_thesis.py`, `generate_committee.py`, `autoresearch_loop.py`
  dispatch the `mutator` / `judge` / `inverter` / `committee` call sites. The workbench's
  `run_transport=subscription` setting sets the `--agent-*` flags that flip these on.
- **Synthesis / report rendering** — `synthesis/synthesize.py` `LLMClient.call` wraps its render and
  refine calls in `dispatch_call_text("synthesis", …)`. So `ztare synth` / `make synth` honor
  `ZTARE_AGENT_DISPATCH[_SYNTHESIS]=agent` with no new flag. Synthesis has no `--agent-*` flag of its
  own, so the workbench mirrors its single transport setting onto the door: `load_workbench_env`
  translates `ZTARE_WORKBENCH_RUN_TRANSPORT=subscription` into `ZTARE_AGENT_DISPATCH_SYNTHESIS=agent`
  for every synth subprocess (an explicit `ZTARE_AGENT_DISPATCH_SYNTHESIS` still wins). The report
  **model** is likewise not hardcoded — `synthesize.py --model` (default `gemini`), driven by the
  workbench `report_model` setting (`ZTARE_WORKBENCH_REPORT_MODEL`). User **direction** for a report
  rides the same path: `synthesize.py --instructions` / `ZTARE_REPORT_INSTRUCTIONS` carries
  plain-language guidance (tone, audience, emphasis) into the render prompt; the workbench's
  report-generation dialog exposes it as a free-text field that sets the env var on the subprocess.
- **Evidence fetch** — `--search-backend {anthropic,openai}` selects the web-search-capable provider
  for fetching; the compile model follows `--model`.
- **On-demand forecast** — `forecast/scratch_elicit.py` (`ztare forecast scratch-elicit`) elicits a
  probability for any question through `dispatch_call_text("forecast_elicit", …)`, then shells out to
  the **sealed** `forecast/pool.py scratch-forecast` to price it (tail-risk + calibration). The pool
  stays isolated (subprocess); only the elicitation is agentic — honoring the pool's "forecasting
  agents attest read-only pricing, execution agents isolated" boundary. `--stub-p` gives a
  deterministic, model-free path for tests.

Invariant: **adding a new model-calling entry point means calling `dispatch_call_text`, never
re-deriving the api-vs-subscription decision locally.** That is what keeps the transport choice a
single switch rather than a scatter of flags.

## The four hard boundaries

ZTARE is mostly boundary discipline. The implementation can change, but these
separations should not.

| Boundary | What it prevents | Canonical surface |
|---|---|---|
| Evidence vs. memory | accumulated notes becoming trusted truth | project `raw/`, workspace, `evidence.txt`, provenance |
| Proposal vs. verification | the generator grading itself | validator, adversarial review panel, deterministic checks; commit-membrane daemon as the sole writer of the official evidence ledger ([GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md)) |
| Authority vs. notification | chat, Orbit, or a phone rail owning state | `ztare_workspace/gates/`, transition log, role mandates |
| Intelligence vs. action | read models and forecasts silently becoming authority | forecast contracts ([GP-230](../../research_areas/seams/mission/org/GP-230_cognitive_firm_absorption_seam.md)), action-impact records ([GP-243](../../research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md)), and the operations-intelligence surface ([GP-244](../../research_areas/seams/apparatus/instrumentation/GP-244_research_operations_intelligence_cockpit_seam.md)) |

A projection can be useful without being authoritative. Orbit is a projection.
A notification provider is a projection. A dashboard is a projection. The
authority lives in files and ledgers that can be replayed.

---

## Layer 1: Project evidence and artifacts

Projects hold domain work. A project can be a validator surface, a Lean
formalization campaign, a scientific experiment, a research paper, or an
out-of-loop human-agent investigation.

Canonical project surfaces:

- `projects/<project>/raw/`: source material when the project is public enough
  to track.
- `projects/<project>/workspace/`: working artifacts, summaries, scripts,
  residuals, handoffs, ledgers, and route-specific state.
- `project_charter.md`: the local question, scope, and success conditions when
  a project is formalized.
- `evidence.txt`: the bounded evidence snapshot for validator runs.
- `compiled_evidence.txt`, `compile_provenance.json`, source-index receipts,
  evidence-output bindings, and evidence-gap resolution receipts: the
  source-to-evidence chain used before a project is allowed into the in-loop
  validator. Source-index and compile-provenance freshness rows also carry a
  `ztare-artifact-source-binding-contract-v1` contract. The old `ok` field only
  means "not proven stale." Run readiness and source-claim graph routing require
  `kernel_entry_ok=true`, which means the artifact is byte/hash-bound to the
  current raw source preflight. The source preflight itself is also part of the
  entry contract: if the checker is unavailable or errors, trace blocks run
  readiness and points back to `ztare project source-check`. Launch preflight uses
  the same rule: projects outside the repo-local `projects/` surface, missing
  launch files, or verifier errors block run readiness as hard blockers.
- `project_intake` JSON: the bounded intake object that records the task,
  source/evidence references, non-claims, next falsifiers, and optional launch
  defaults for a later autoresearch run. Older receipts may still expose the
  same object under an older project object field. New docs and tools should
  use `project_intake`.
- `latest_*` and `champion_*` artifacts: run outputs when the project uses the
  original in-loop validator.

The invariant is that memory can help compile evidence, but evidence must be
bounded when the validator is asked to judge a claim.

---

## Layer 2: The in-loop validator

The in-loop validator is the original ZTARE loop. It exists for cases where a
claim should be attacked under a declared rubric and deterministic checks.

Typical flow:

```text
raw/workspace -> source preflight/index -> evidence/provenance/output receipts
-> project intake JSON -> mutator proposal -> adversarial review
-> deterministic execution/checks -> score/champion -> synthesis or failure report
```

Core responsibilities:

- keep the proposing agent separate from the judging surface
- execute tests against the claim
- use hard checks when a claim has numeric or structural invariants
- preserve run artifacts so later readers can see why a claim survived or died
- stop honestly when the evidence, grammar, or checks cannot support the claim

`ztare autoresearch trace` is the read-side trace chain for this boundary. It
joins project-intake readiness, source preflight, source-index receipts,
compile-provenance freshness, evidence-output binding, active evidence gaps,
launch-preflight receipts, loop admission, mutator-briefing records, prediction
contract summaries, and recent evaluation history. `readiness_canonical` is the
current intake-facing status. Legacy `readiness` ids remain readable for older
receipts. Source-index receipts are only valid while both
`workspace/source_index.json` and `workspace/workspace_meta.json` still exist and
match the frozen hashes. A missing or stale receipt should name the recovery
command when recovery is mechanically available. Otherwise the trace should say
which surface is still unfit for in-loop use.

Evidence gaps use a typed recovery contract at this boundary. A
`public_evidence` row means the next action is out-of-loop source, dataset,
comparator, or threshold recovery. A `local_verification` row means the next
action is a local verifier, fixture, code/log check, preflight, receipt, or
in-loop discriminator. The canonical fields are `recovery_kind`,
`recovery_channel`, `required_surface`, `can_public_fetch`, and
`in_loop_consumable`. Each active row also carries a
`ztare-evidence-gap-recovery-contract-v1` object with the gap hash, active
state, classification source, route booleans, and conflict warnings. Consumers
should take their routing from that contract directly. Older rows are
inferred for compatibility. When that happens the contract marks
`classification_strength=fallback_inference` and sets
`schema_promotion_required`, so the compatibility path stays visible to a reader
and is not mistaken for producer-declared routing. Automated evidence fetch skips
schema-promotion rows by default. `ALLOW_INFERRED_PUBLIC=1` is only for
intentional legacy replay. New producers should emit the
route fields directly. The loop persistence boundary also normalizes newly written
`latest_evidence_gaps.json` rows through the same contract interface before
trace, evidence-fetch, synthesis, or graph routing can consume them.
Hash-bound evidence-gap resolutions are append/replace receipts over the exact
persisted gap row. The project CLI can target the latest, champion, or currently
active gap source, and receipt writes are serialized with a project-local lock
and same-directory atomic replace so parallel prep agents do not drop each
other's rows.
The source-claim graph is a read model over that same contract and over source
preflight. If source-check is unavailable or blocking, graph routing demotes
itself and holds off on selecting a recovery action.

The same trace now emits `plan_preview`, a read-before-run contract over the
route handoff. It is deterministic: no model call, no scheduling, no hidden
worker launch. The preview names the first command to run, dependency order,
worker roles, spend boundary, fallback policy, expected workspace outputs, and
the largest quality risk. If the intake has no fresh admission, the preview
starts with the model-free preflight. Once trace sees a fresh, hash-verified
admission for the current intake and run-readiness bytes, `next_commands`
advances to the bounded run while the dependency order still records preflight
as the completed spend gate. Recent provider telemetry can also change the risk label:
charged input with no model output is treated as a provider/runtime failure,
not as a research result.

Evidence replay is required only when a replay manifest exists or compile
provenance names one. Optional absence is normalized to `not_required` in
human-facing trace and health summaries while the raw carrier status remains
available for audit. Required stale or invalid replay manifests remain
run-readiness blockers.

`ztare autoresearch carrier-replay` is the batch read-side audit for the same
boundary. It replays trace records over selected projects and reports
whether latest-eval state, artifact refs, worker provenance, transport, failure
signatures, and action-intelligence links are still present. The report
separates aggregate historical carrier debt from `current_carrier`, the latest
materialized projection node. A project can therefore show legacy missing
artifact refs while still proving that the current row carries the fields future
replay needs. Its scope is trace integrity: whether the replay fields survive,
not whether the underlying outcome was good.

Project-intake files can also carry an `expected_command`.
`ztare autoresearch run --intake ... --preflight-only` verifies that launch
contract without spending model calls, and a later `run --intake ...` inherits
bounded defaults unless the reviewer explicitly overrides them.

Report generation is a read model over the same boundary. `make synth` /
`src/ztare/synthesis/synthesize.py` writes
`synthesis/report_support_contract.json` before the renderer call. The contract
names supported claims, unsupported or unresolved claims, blockers, runtime
caveats, graph/evidence-gap actions, and next actions. Renderer, refine, and QA
prompts receive that contract, so trace readiness and provider failures stay as
review metadata and never get promoted into substantive evidence. QA blocks
high-severity issues such as unsupported additions, unsupported actions,
distortions, and overclaims. The renderer gets a bounded QA-guided repair loop
before the report fails closed. QA cannot promote a report past a blocked
support contract: blocked evidence readiness, blockers, or stale synthesis
inputs leave only candidate artifacts and QA metadata for inspection. The
support contract also carries
`synthesis_input_binding`: a content digest over the exact artifact files used
to extract the ledger. If the digest is missing or no longer matches the current
artifact set, the report is blocked as stale, so a changed evidence set can never
silently reuse an old model-produced ledger. The support contract also carries
`report_action_authority`: typed `allowed_now`, `conditional`, `deferred`, and
`forbidden_upgrades` rows. That gives renderers and QA a concrete action
boundary they can read directly, with no need to infer authority from narrative
prose. The
cross-project synthesis path now resolves domain buckets from explicit project
metadata, rubric fields, or `project_charter.md` before falling back to slug
heuristics, so example project names do not silently define a promotion
taxonomy. The
separate `post_run_thesis_synthesizer.py` path is still state-changing and can
only promote a candidate thesis through its own audit trail, judge check, and
margin over the full positive-score run baseline. That baseline spans every
positive-score run, including the records that synthesis itself filters out.

This layer is documented in more detail by:

- [cognitive_gym.md](cognitive_gym.md), the constraint-stack theory
- [workflow.md](../guides/workflow.md), the user workflow
- [rubric_specification.md](rubric_specification.md), the validator/rubric
  contract

The validator is one instrument in the wider workbench.

---

## Layer 3: Out-of-loop research operations

Much of ZTARE’s current work does not begin as a validator run. The research
organization needs to decide what to inspect, what to delegate, what to stop,
what to formalize, and when the human must work alongside an agent.

The out-of-loop layer owns:

- roles and mandates under `org/`
- tasks, objectives, key results, preferences, and role channels
- decision files under `ztare_workspace/gates/`
- transition events under `ztare_workspace/transitions.jsonl`
- project-level scripts, proof work, notebooks, handoffs, and research notes
- Research Director utilities under `src/ztare/research_director/` and
  `scripts/public/control/rd_tick_brief.py`
- role daemons and manual-console workflows
- subsystem handoffs for proof work, including the LeanMill boundary

This layer exists because chat is not durable state. A human-agent conversation
may discover a decisive test, but the test only compounds when it becomes a
task, decision file, script, forecast contract, action-impact row, finding, or
paper artifact. The reusable organization-kernel version of the role/mandate/check
model lives in [cognitive-firm](https://github.com/sparckix/cognitive-firm).
In this repo, `org/` is the ZTARE tenant overlay and compatibility surface.

The Research Director utilities are the agent-facing harness for this layer.
They surface reusable primitives, pattern-action contracts, branch grids,
substrate recommendations, graph actions, gap typing, and domain workbenches
before or beside a validator run. They should help a worker choose and record
the next useful move. They should not be confused with the Project Workbench
itself: D4 is the human project surface; RD utilities are route/tool support
for agents and advanced users; the in-loop validator is the stricter checking
lane when a claim or report needs support.

### LeanMill boundary

LeanMill (`src/ztare/leanmill/`) has its own architecture document and is a
subsystem boundary inside the larger ZTARE workbench, with its internals
documented there. Three interfaces matter to the general architecture:

- proof-work handoff: Lean work enters through LeanMill-specific queues
  and receipts
- proof-credit boundary: benchmark and closure credit comes from governed
  receipts, not raw solver output
- orchestration boundary: public scripts can launch LeanMill work while the
  subsystem preserves durable proof-work state and verification interfaces

The detailed LeanMill architecture lives in
[leanmill_architecture.md](leanmill_architecture.md). That doc owns proof-search
policy, station design, worker specialization, move catalogs, proof-credit
mechanics, benchmark contracts, source breadth, family breadth, and bottleneck
analysis. This overview only records the integration boundary.

See:

- [organizational_primitives.md](organizational_primitives.md)
- [ztare_research_company_architecture.md](ztare_research_company_architecture.md)
- [org_runtime_quickstart.md](../guides/org_runtime_quickstart.md)
- [org/README.md](../../org/README.md)

---

## Layer 4: Reflexive intelligence

The reflexive layer asks whether the organization is getting better over time at
choosing work, a question that spans many outputs and runs.

It reads from:

- the experiment track record
- forecast contracts, outcomes, scores, and decision-use rows
  ([GP-230](../../research_areas/seams/mission/org/GP-230_cognitive_firm_absorption_seam.md))
- forecaster-calibration rules and the ex-post tail/abstention/judge-routing
  measurements that justify them
  ([GP-245](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md))
- action-impact records
  ([GP-243](../../research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md))
- research-operations intelligence outputs
  ([GP-244](../../research_areas/seams/apparatus/instrumentation/GP-244_research_operations_intelligence_cockpit_seam.md))
- trajectory-mining artifacts
- catch and anti-pattern ledgers
- LeanMill proof-attempt event rows exposed to the wider workbench
- proof/project residuals and summaries
- decision rows, check results, and transition logs when available

It should answer operational questions:

- Which forecasts changed an actual decision?
- Which actions produced useful scientific or organizational yield?
- Which failure modes recur despite being known?
- Which projects are stuck only because the next test is missing, and so could
  move again once it exists?
- Which read-model signals are informative, and which are activity volume?
- Which primitive should be promoted, demoted, or retired?

The reflexive layer can route attention. It can recommend `run now`, `split`,
`ask another independent agent`, `defer`, or `stop branch`. It does not grant
authority by itself. Authority still runs through roles, mandates, checks,
budgets, and claims.

### Capability catalog and primitive surfacing

A recurring failure of an agent-driven system is capability amnesia: an
agent reinvents a primitive that already exists, or misses the tool that should
have been used first. ZTARE handles this with one catalog and two surfacing
paths.

The catalog is `analytics/public/index/architecture_index.jsonl`. It registers
gates, operations, reflexive primitives, and reusable analytical utilities with
ids, paths, descriptions, applicability tags, and generated taxonomy metadata.
Generated taxonomy code checks that moved modules, duplicate rows, stale atlas
outputs, and parent-family groupings stay coherent.

There are two ways to use the catalog:

- Before work starts: `primitive_tick_surface.py` renders relevant
  primitives into the RD brief. Patterns and anti-patterns surface in parallel
  from the [anti-pattern catalog](anti_pattern_catalog.md).
- On demand: `primitive_amnesia.py` answers "what already exists for this
  task?" using the primitive atlas plus lexical fallback.

The architecture rule is simple: the catalog finds existing capabilities. Route
authority, receipt validation, and project-memory updates belong to their own
contracts.
Measured retrieval quality, miss queues, and parent-family audits belong in
[capabilities.md](capabilities.md) and the primitive audit reports.

### Research move routing: capabilities, cards, contracts

This layer answers a concrete question before a worker starts: **given this
task, what existing capability should be used, what move is owed, and what
record must exist before the move counts?**

The stack is deliberately split so one component cannot invent its own answer.
Capability discovery finds existing code. Move routing chooses an action family.
The contract names the fields that downstream checks expect. The brief renders
the obligation before work begins.

| Layer | Owns | Out of scope |
|---|---|---|
| [`primitive_amnesia.py`](../../src/ztare/research_director/primitive_amnesia.py) / [`primitive_tick_surface.py`](../../src/ztare/research_director/primitive_tick_surface.py) | Capability discovery over `architecture_index.jsonl` + the primitive atlas: "what reusable code/tool already exists for this task?" | Research-route authority, receipt schema truth, or project-memory recurrence decisions |
| [`primitive_catalog_taxonomy.py`](../../src/ztare/research_director/primitive_catalog_taxonomy.py) | Generated full-catalog source categories, semantic families, path normalization, duplicate/staleness health, and catalog parent nodes | Model-invented ontology, manual row ownership, or replacement of the catalog |
| [`primitive_family_registry.py`](../../src/ztare/research_director/primitive_family_registry.py) | Call-site-to-family coverage for LLM-mediated workers and helpers; live-symbol integrity for those cards | Catalog generation, embedding rows, or implementation ownership |
| Move-card routing module | Compact move-card records: problem surface, nearest confuser, next action, required receipt family | Full evidence payloads or close-time validation |
| [`orchestration_menu.yaml`](../../org/menu/orchestration_menu.yaml) + pattern catalog | Coarser research-pattern classes and sequencing options | Evidence that selecting a menu label improves first-action quality |
| [`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py) | Checked action contract: required fields, nearest-confuser rejection, source-cue receipts, action-program fields, and close payload expectations | Claims that pattern prose or labels alone improve outcomes |
| [`rd_tick_brief.py`](../../scripts/public/control/rd_tick_brief.py) | Presentation: render the selected capability, move card, and action contract before work starts | Independent trigger vocabularies or another source of routing truth |

A move card is a small routing record. It should be understandable without
knowing the implementation: "this looks like a PDE estimate task; the nearest
confuser is a generic analogy task; fill the estimate-receipt fields before
claiming progress." Evidence arrives later through the artifact selected by the
contract.

Move-card routing has one job: translate a task surface into the next
owed action. It is not a claim verifier, a benchmark, or a proof of lift. A
good route row says:

- why this action family was selected
- which near-miss route was rejected
- which artifact slot or receipt schema must be filled
- which audit can later show whether the route improved the next decision

The normal path is:

```text
task / project surface
-> primitive surfacing asks what code or tool already exists
-> move card names the action family and nearest confuser
-> action contract materializes the required fields
-> RD brief shows the owed action before work starts
-> trace / close tooling checks whether the fields exist
```

Primitive amnesia may surface `build_pattern_action_contract()` or the legacy
move-card helper as existing tools. Card routing stays in the
card/router layer. The action contract consumes the selected card and checks
the required fields. The brief renders the selection before work starts.

Ownership is intentionally narrow:

- recognition belongs in the card/router or menu layer
- validation belongs in the contract and resulting artifact
- presentation belongs in the brief

If amnesia, cards, contracts, and briefs each maintain their own trigger
phrases, the same task can route differently in different places. Hard-residual
and PDE recognition follow the same rule through `OP-HRD-01` and `OP-PDE-01`;
`pattern_action_contract.py` should not grow local route tables or branch on
move-card matched terms. Matched terms are route provenance. Activation
uses selected card ids, typed receipt fields, and strong semantic receipts only
when the atlas contract is fresh enough to count.

The release check for this boundary is `ztare audit move-card-router --json`
or `make move-card-router-audit`. The older Make target remains a compatibility
alias. The
default path is offline and deterministic over a fixed paraphrase set. The
optional `SEMANTIC=1` path exercises the embedding atlas and reports
`semantic_error_count` if live provider access is unavailable, so fallback
routing surfaces as its own count and never inflates the successful-semantic
total. The
audit also checks the atlas contract offline: embedded row ids must match the
current move-card catalog content hashes and manifest metadata. A stale
atlas is treated as lexical fallback until `make move-card-atlas-build`
refreshes it.

Internal epistemic-generation runs constrain how this layer is used:

- Passive labels, long menus, and free-form human prose were unreliable routing
  mechanisms.
- Correct compact cards can help when the relevant candidate is already surfaced, but
  card selection is not validation.
- The strongest current unit is source-bound action content: required receipts,
  nearest-confuser separation, source-cue checks, and deterministic action-program /
  program-counter fields.
- Free-form program synthesis and unchecked wrong-contract obedience failed. Source
  alignment helps but is not enough without order/stop checks.
- Operational lift must be measured. New enforcement should be preceded by
  shadow logs, miss audits, and held-out or naturalistic checks.

For the autoresearch/RD boundary, `OP-AWR-01` decides whether a bounded task
should use in-loop autoresearch, a subscription worker, or manual RD work.
[`pattern_action_contract.py`](../../src/ztare/research_director/pattern_action_contract.py)
requires the routing fields.
[`rd_tick_brief.py`](../../scripts/public/control/rd_tick_brief.py) renders the
card plus the router decision.
[`action_intelligence.py`](../../scripts/public/control/action_intelligence.py)
records out-of-loop agentic work so bypasses become explicit action evidence on
the record. Aggregate in-loop vs out-of-loop volume is owned by
reflexive mining and the public dashboard (`bifurcation_report.json` folded by
[`build_dashboard_bundle.py`](../../scripts/public/mining/build_dashboard_bundle.py)).
The workbench action rows explain individual route choices under that aggregate.
Route-row coverage gaps, dashboard shares, and portfolio-attention questions
belong to `OP-RMI-01`. `OP-AWR-01` is reserved for bounded-task routing
decisions.

The autoresearch hypothesis projection is read-only accounting over
`eval_history` and steering logs: admitted nodes, pruned nodes, repeated branch
cues, and reusable negative constraints. The loop remains canonical.
The default launch path preserves the requested model family. Cross-model
provider fallback is opt-in and reserved for continuity tests.
The useful feedback path is through the mutator briefing, where repeated failed-branch
constraints are surfaced as externalized memory for the next worker.
The replay audit checks that this read model keeps enough fields to be useful
across projects before any UI or dashboard treats it as a stable surface.

### Graph and prediction read models

Graph diagnostics and forecast scores are read models. They can improve the
next decision, but only after their authority boundary is explicit.

Graph records enter the loop through typed action rows:

- source-claim graph gaps with `recovery_kind=public_evidence` become exact
  gap ids and targets for out-of-loop source repair
- source-claim graph gaps with `recovery_kind=local_verification` become
  in-loop focus receipts for the next mutator
- probability-DAG rows reach the prompt only when the rubric enables DAG
  steering
- a graph diagnostic with no decision effect records `no_strategy_change`,
  keeping a bare metric from standing in as a route

Forecast and prediction rows are stricter. `autoresearch trace` can report
provenance, scoreability, Brier-vs-baseline status, and timing validity. Those
rows do not route autoresearch iterations, allocate workers, or override the
rubric. If a prediction row claims control authority without a validated
forecast lifecycle and downstream decision receipt, readiness blocks it. This
keeps measurement from silently becoming control.

*Canonical embedding engine.* Several subsystems need semantic retrieval:
primitive discovery, proof/source atlases, graph/card routing, and seam/spec
lookup. They share one embedding engine:
[`embeddings.py`](../../src/ztare/common/embeddings.py). Corpus-specific code
harvests rows. The common engine owns client construction, retry behavior,
content-hash caching, atlas manifests, and cosine query. New corpora should
consume this engine and leave provider-call wiring to it.

See:

- [reflexive_engineering.md](reflexive_engineering.md)
- [reflexive_audit_workflow.md](../guides/reflexive_audit_workflow.md)
- `research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md`
- `research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md`
- `research_areas/specs/active/apparatus/instrumentation/GP-244_research_operations_intelligence_cockpit_spec.md`

---

## Human reviewers and agentic workers

ZTARE distinguishes two research actors:

- Human reviewer. The accountable person who sets priorities,
  accepts external risk, decides what can be public, supplies taste, and makes
  strategic calls when the project surface is underdetermined.
- Agentic worker. A tool-using AI agent that can inspect files, run
  probes, write scripts, edit docs, repair proofs, and leave a dense artifact
  trace. Codex-style and Claude Code-style sessions are agentic workers.

The human role is wider than final approval. The human may be the worker, the
source of taste, the experimental reviewer, or the only actor who can choose
among live research bets. An agentic worker is wider than a chat responder.
When a live project surface is underspecified, the useful unit of agency is often a
tool-using session that inspects the filesystem, probes the runtime, repairs
the source/evidence surface, and leaves saved history.

The authority boundary remains different. Agentic workers can execute,
recommend, and close bounded tasks within mandate. The human reviewer owns
public-claim accountability, risk acceptance, strategic direction, and taste
unless a specific role contract delegates a narrower decision.

Codex-style and Claude Code-style sessions do not have to start inside the
in-loop validator. They can be ordinary project work: explore a topic, write
notes, run scripts, produce a plot, draft a report, or try a proof route. ZTARE
should make that work durable by giving it a project folder, a research map,
source/evidence status, run history, report checks, and saved review records.
Only the artifacts that need to survive the session need a typed project role.
Only claims or reports that need support need the stricter validator path.

```text
free agent work -> project artifact
project artifact -> organized map / source status / evidence status
claim or report -> bounded validation / report readiness / saved review
```

The in-loop validator is a strong checking lane, not the whole research
process. The out-of-loop layer is where people and agents explore, prune
branches, build the map, and decide which piece deserves validation.

The architecture supports four human roles:

| Human role | System support |
|---|---|
| Accountable reviewer | preferences, gates, objectives, stop/split/defer authority |
| Collaborator | console session, project notes, human-agent handoff artifacts |
| Source of non-digitized work | explicit receipts, summaries, evidence promotion, action-impact rows |
| Attention bottleneck | closure pressure, forecasts, independent-agent review, unattended in-mandate work |

The target operating model keeps the human accountable for judgment while
moving memory, routing, and closure into durable artifacts.

---

## Canonical state vs. projections

| Surface | Role | Canonical? |
|---|---|---|
| `projects/` | project work and artifacts | yes for project artifacts |
| `research_areas/` | seams, specs, synthesis, experiment record | yes for research governance |
| `org/` | ZTARE tenant roles, tasks, channels, objectives | yes for local org state |
| `ztare_workspace/gates/` | pending/resolved decisions | yes |
| `ztare_workspace/transitions.jsonl` | transition events | yes |
| LeanMill queue + event ledger | proof-attempt bus; subsystem details live in [leanmill_architecture.md](leanmill_architecture.md) | yes |
| `/srv/ztare_official_store/official/` (VPS) | daemon-owned F-row + stamped-transition ledger; commit-membrane provenance in [GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md) | yes; the in-repo `research_areas/EXPERIMENT_TRACK_RECORD.md` is a generated export of this |
| `analytics/public/` | public analytics outputs | derived |
| Orbit | governance UI | projection |
| notification provider | push/ack rail | projection |
| dashboard HTML | human-readable intelligence surface | projection |
| agent chat transcript | context only | not canonical unless summarized into artifacts |

This distinction is the guardrail against accidental architecture drift.

---

## Public repo boundary

ZTARE is a public research repository plus local overlays. Public docs should
describe the reusable architecture without depending on ignored paths,
private tenant repos, or local credentials.

Current boundary:

- Public ZTARE contains the validator, public docs, public papers, public
  scripts, public analytics, and source-visible org primitives.
- `org/` is a ZTARE tenant overlay; the canonical generic kernel lives
  separately (see the cognitive-firm bullet below).
- Tenant notification providers are optional. Filesystem gates and transition
  logs are the public default.
- The generic organizational kernel belongs in
  [cognitive-firm](https://github.com/sparckix/cognitive-firm).

If a doc cannot be understood without private context, it should either be
rewritten as a public abstraction or moved out of the public entry path.

---

## What to use when

| Need | Use |
|---|---|
| Test a bounded claim against evidence | in-loop validator |
| Prove or formalize a theorem fragment | project proof workflow / Lean tooling |
| Schedule and run many Lean proof attempts under a stable contract | LeanMill proof subsystem; see [leanmill_architecture.md](leanmill_architecture.md) |
| Decide which scientific branch deserves attention | forecast contracts plus RD/human review ([GP-230](../../research_areas/seams/mission/org/GP-230_cognitive_firm_absorption_seam.md)) |
| Learn whether an action changed outcomes | action-impact rows ([GP-243](../../research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md)) |
| Inspect operating health across projects | operations-intelligence surface ([GP-244](../../research_areas/seams/apparatus/instrumentation/GP-244_research_operations_intelligence_cockpit_seam.md)) |
| Turn a graph diagnostic into a reviewable action | [graph_interfaces.md](graph_interfaces.md) + `graph_rd_actions[]` in `ztare autoresearch trace` |
| Read forecast/prediction signals without granting authority | `prediction_contract.py` read model + [capabilities.md](capabilities.md#forecast-pool-and-prediction-market) |
| Run persistent role-bound work | org runtime / role daemon |
| Work interactively with a human and agent | console session + project artifacts |
| Extract reusable failure patterns | reflexive audit workflow + anti-pattern catalog |
| Track specification-gaming vectors from incident to runtime gate | [gaming behavior catalog map](gaming_behavior_catalog_map.md), the canonical SOP for gaming-vector files and hardening flow |
| Run bug-bounty / honeypot search for missed autoresearch failures | [make targets](../reference/make_targets.md) + [gaming behavior catalog map](gaming_behavior_catalog_map.md) |

---

## Failure modes the architecture is built to catch

- *Self-certification*: the same model family proposes and validates its own
  success.
- *Specification-gaming recurrence*: a known gaming vector is cataloged but
  never reaches a runtime gate or promotion receipt. See the
  [gaming behavior catalog map](gaming_behavior_catalog_map.md) for the
  incident -> registry -> promotion -> enforcement lifecycle.
- *Narrative inflation*: a plausible story outruns deterministic receipts.
- *Metric theatre*: tasks close while world-measured outcomes do not move.
- *Chat-state loss*: important decisions remain only in conversation.
- *Dashboard authority creep*: a projection starts acting like a control
  plane.
- *Notification-state confusion*: a push rail becomes treated as source of
  truth.
- *Primitive cargo culting*: patterns are surfaced but do not improve
  decisions or outcomes.
- *Local-over-global optimization*: a micro loop improves a local score while
  damaging scientific yield or external validity.

None of this eliminates the failures above, it makes them observable, which is
the difference between a bug you can demote and one that ships.

---

## Current maturity

| Area | Status |
|---|---|
| In-loop validator | usable research instrument, still project/rubric dependent |
| Evidence/rubric workflows | usable, public docs available |
| Org runtime | working prototype, exercised locally |
| Notification abstraction | filesystem default, tenant providers optional |
| Forecast contracts | mechanized contracts, scoring, and decision-use rows; calibration rules are tracked in [GP-245](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md) |
| Graph action interface | live graph-record and decision-receipt interface; source-claim graphs and probability-DAG receipts can lower into `graph_rd_actions[]`; wider graph-algorithm claims require [graph_interfaces.md](graph_interfaces.md), `make graph-capability-audit`, and evidence that a diagnostic changed a route, prep decision, or claim boundary |
| Research move routing | live recognition-to-action interface; a move card names the action family, nearest confuser, artifact slot, and checked receipt fields; deterministic routing is covered by the publish gate; optional semantic routing is provider-backed and must report provider failures; the next maturity step is miss logging plus held-out paraphrases |
| LeanMill proof subsystem | live governed proof subsystem with queues, receipts, and benchmark artifacts; this overview records only the integration boundary, and [leanmill_architecture.md](leanmill_architecture.md) owns the subsystem design |
| Commit-membrane daemon | live on VPS as sole writer of the official store ([GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md)) |
| Action intelligence | early but wired into public smoke checks |
| Research intelligence dashboard | active instrumentation track; public exports stay bounded by claim registers and evidence-atlas artifacts |
| Multi-tenant enterprise control plane | design direction, not the public default |

Today this is a single-maintainer public workbench with enough kernel structure
that a small team could, in principle, pick it up. The honest seam is that the
public validator stack, the generic cognitive-firm kernel, and the tenant
overlays still share too much code to separate cleanly; pulling them apart is the
next real step. Until that happens, "small-team use" is a claim the repository
has not yet had to keep.

---

## Documentation map

This page is the overview. Read next by intent:

| If you want to… | Read |
|---|---|
| See every module by function | [system_position_and_module_map.md](system_position_and_module_map.md) |
| Understand the LeanMill proof subsystem | [leanmill_architecture.md](leanmill_architecture.md) |
| Understand the reflexive/learning layer | [reflexive_engineering.md](reflexive_engineering.md) · [reflexive_mining_methodology.md](reflexive_mining_methodology.md) |
| Understand the validator's theory | [cognitive_gym.md](cognitive_gym.md) · [rubric_specification.md](rubric_specification.md) · [harness_specification.md](harness_specification.md) |
| Understand the epistemic stance | [epistemic_principles.md](epistemic_principles.md) · [goodhart_at_every_layer.md](goodhart_at_every_layer.md) |
| Know what already exists before building | the [capability catalog](#capability-catalog-and-primitive-surfacing) + [anti_pattern_catalog.md](anti_pattern_catalog.md) + [capabilities.md](capabilities.md) |
| See the org/runtime model | [organizational_primitives.md](organizational_primitives.md) · [ztare_research_company_architecture.md](ztare_research_company_architecture.md) |
| Check evidence behind claims | [evidence atlas](../evidence_atlas/README.md) |
| Look up a term | [glossary.md](glossary.md) |

Seams/specs (governance of in-flight work) live under `research_areas/seams/` and
`research_areas/specs/active/`; the canonical experiment record is the [GP-241](../../research_areas/seams/apparatus/cage/GP-241_canonical_membrane_first_opener_spec.md)
daemon-owned store, exported to `research_areas/EXPERIMENT_TRACK_RECORD.md`.

When this overview and a fuller subsystem doc disagree, the subsystem doc wins
for its internals; fix the drift here so the overview stays a trustworthy
map and a reader can rely on it without it drifting into a competing
architecture spec.
