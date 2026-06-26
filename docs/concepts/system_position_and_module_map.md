---
description: "How ZTARE positions itself among related AI research systems and how its major modules compose."
---
# System position and module map

> Up: [Documentation map](../README.md)

ZTARE is a local workbench for checking reasoning before it becomes a claim.
It turns sources, code, proofs, data, model outputs, checks, failures,
forecasts, reports, and review decisions into claim states a reviewer can
inspect.

The technical machinery matters, but it is not the whole object. The workbench
also includes a human reviewer, agentic workers, role offices, source
boundaries, verification tools, governance gates, public/private boundaries,
ledgers, and publication discipline.

The repo contains theorem-proving, symbolic-regression, agent-dashboard, and
paper surfaces, but those are components of a larger research trace: sources,
proposals, tests, failures, demotions, forecasts, proof attempts, claims,
non-claims, next falsifiers, and the authority path that decides what those
artifacts are allowed to mean.

The shortest accurate summary is:

```text
ZTARE turns sources, artifacts, and agent work into claim states a reviewer can
inspect.
```

Term boundaries matter here:

- Workbench is the user-facing product: repo, CLI, docs, review surfaces,
  and D4.
- Kernel is the trusted boundary: checks, contracts, demotions, source
  readiness, and ledger/read-model rules.
- Engine is runnable machinery: validation, proof search, evidence
  compile/fetch, report export, mining, routing, or materialization.
- Apparatus is an experiment setup: prompts, rubrics, agents, datasets,
  scripts, costs, and records from a run.

The long-term idea is simple: code has compilers, and reasoning needs similar
discipline. A code compiler does not make a program useful. It gives source
code a form that other tools can parse, check, reject, and inspect. ZTARE
borrows that shape for reasoning work: proposals become bounded claims,
source/evidence objects, checks, receipts, demotions, reports, and next
falsifiers. This is a design direction, not a claim that the current repo
compiles all reasoning.

## Product boundary

Existing AI systems cover important parts of the workflow. ChatGPT, Claude,
Codex, Claude Code, Kimi-style swarms, LangSmith, AI co-scientist systems, and
formal proof tools all matter here. ZTARE should be compared against them at
the right boundary.

The boundary is the durable claim lifecycle. A chat or agent product can
generate, edit, search, code, summarize, or run tools. An observability system
can trace an application. A proof assistant can check a formal artifact. ZTARE
owns the local state that decides what a claim is allowed to mean after those
systems have acted:

```text
bounded claim -> source intake -> attempt -> adversarial check
-> deterministic or evidence-backed gate -> verdict / demotion / next falsifier
-> ledgered state that the next run must inherit
```

This makes outside models and agent products workers, judges, or input
channels inside the workbench. They are useful when they produce files,
proposals, critiques, traces, forecasts, proof fragments, or source summaries
that ZTARE can bind to a claim and inspect. They are insufficient when the
project needs a defensible record of what was checked, what failed, what was
demoted, and what the next run is forbidden to forget.

The practical test for positioning is simple:

- If the user wants a fluent answer, use a model interface.
- If the user wants a coding task executed in a repository, use a coding
  agent.
- If the user wants traces and evaluations for an LLM application, use an
  observability/eval platform.
- If the user wants to stand behind a bounded claim using local sources,
  explicit weakest links, replayable checks, demotions, and next falsifiers,
  ZTARE is the workbench.

That means the repo has several modules that look different on the surface but
serve one architecture: make research moves explicit enough that another
agentic worker, the human reviewer, or a future model can inspect, reuse,
refute, or demote them.

## Neuro-symbolic boundary

ZTARE can be described as neuro-symbolic, but the useful split is operational:

- Neural systems propose, search, summarize, critique, rank, translate, and
  route work.
- Symbolic and file-backed systems define the objects that survive a run:
  bounded claims, source references, intake files, evidence hashes, gates,
  receipts, forecasts, ledgers, verdicts, demotions, and next falsifiers.
- The human reviewer owns public accountability and strategic risk.

No layer self-certifies. A model-produced sentence is not a claim until it is
bound to sources and checked. A gate result is not a user-facing answer until
its claim boundary, non-claims, and next falsifier are visible. A forecast or
action recommendation is not control authority until decision-use and outcome
evidence justify that promotion.

For a claim-first review path, use the
[evidence atlas](../evidence_atlas/README.md), which links public claims and reusable primitives to evidence
levels, source artifacts, runnable checks, and non-claims.

## System position

ZTARE sits at the intersection of six related system families:

- Socio-technical research organizations: systems that coordinate human
  judgment, agentic labor, evidence, authority, and publication boundaries.
- AI research assistants and co-scientists: systems that help propose,
  critique, test, and refine scientific ideas.
- Formal proof and theorem-workbench systems: systems that search,
  repair, verify, or triage formal mathematical artifacts.
- Agent workbenches and control planes: systems that let tool-using agents
  operate on real files, processes, tickets, gates, and runtime state.
- Evaluation and governance systems: systems that harden claims through
  rubrics, adversaries, deterministic checks, provenance, and audit trails.
- Research-operations systems: systems that allocate attention, forecast
  branch value, track outcomes, and learn from organizational behavior.

ZTARE is not trying to reduce itself to any one of those categories. It
composes them around one public object: the claim lifecycle, which spans more than a single model call,
tool invocation, dashboard, or proof script:

```text
source -> attempt -> critique -> executable check -> forecast / gate
-> promote, demote, null, defer, or source-block
-> ledger -> mined learning -> next route
```

ZTARE asks "can an agent solve the problem?" and then a wider set of
questions:

- what evidence licensed the attempt
- which source boundary was active
- which verifier or gate actually fired
- whether the result is a claim, null, demotion, or source-blocked residue
- which next falsifier would change the decision
- whether the organization learned how to route the next attempt better

That is why ZTARE keeps so much filesystem state. The value extends past the
answer to the labeled path by which the answer, non-answer, or
demotion was produced.

## Related systems

Related systems are mentioned as orientation. The point is to locate
ZTARE in the system landscape. A current external benchmark would be needed before treating any as a target to beat.

*AI Co-Mathematician.* Google DeepMind's
[AI Co-Mathematician](https://arxiv.org/abs/2605.06651) is a math-focused
agentic workbench for interactive mathematical discovery. ZTARE overlaps only
where ZTARE is doing proof/search work: theorem nomination, Lean checking,
proof-search triage, graph diagnostics, novelty filters, and closure-utility
tests. That is a related-system pointer. ZTARE
should not use AI Co-Mathematician as the public yardstick for the repo. The
repo's center of gravity is the wider socio-technical claim lifecycle.

*AI co-scientist and automated-research systems.* ZTARE is closer in spirit
to systems that generate hypotheses, design experiments, criticize claims, and
iterate on evidence. The difference is its insistence on a filesystem-backed
institution: claims must land in project-intake files, review artifacts, public
registers, ledgers, gates, forecasts, or demotion records before they count as
durable knowledge.

*Formal proof factories.* ZTARE has a formal/proof subsystem inside the
larger workbench. This map records the public interface only:
source-qualified proof workflows, candidate proof rows, source-quality
decisions, governed receipts, and benchmark artifacts. The detailed LeanMill
design lives in [leanmill_architecture.md](leanmill_architecture.md), which owns
proof-search policy, queue topology, worker stations, move catalogs, benchmark
contracts, and proof-credit mechanics. Public performance claims belong in
evidence-backed LeanMill docs and review artifacts (outside this orientation map).
The public proof-search loop is summarized in
[closure_claim_governance.md](closure_claim_governance.md): Proof Execution,
Governance Gate, Residual Compiler, and the closure-credit boundary.

*Socio-technical research infrastructure.* ZTARE also belongs next to
systems that are not "AI models" in the narrow sense: lab notebooks, issue
trackers, review boards, experiment registries, provenance systems,
forecasting processes, and release governance. The claim is that AI-assisted
science needs all of those functions in one inspectable loop. Without the
social and institutional layer, a powerful model can still produce persuasive
unreviewed artifacts. Without the technical layer, the institution cannot
scale evidence, replay, or verification.

*Agent workbenches.* Codex, Claude Code, and similar tool-using agents are
agentic workers inside the ZTARE workbench. ZTARE adds the governance layer
around them: role mandates, filesystem gates, public/private boundaries,
source-readiness labels, and claim ledgers.

*Prediction markets and research-ops systems.* The forecast pool and
prediction ledger make research allocation explicit. They do not replace
scientific judgment. They record what was expected before resolution and
whether that expectation changed what the organization did.

*Eval and model-governance systems.* ZTARE shares concerns with evaluation
harnesses, red-team systems, and AI governance stacks, but it is narrower and
more operational: the unit is a concrete research claim moving through
evidence, adversaries, gates, ledgers, and publication boundaries.

## The workbench layer

The workbench is the surface a human or agent uses to operate the research
system. It includes:

- [Orbit](../../orbit/README.md), a browser projection over governance state
  for the wider cognitive-firm style control plane
- [supervisor](../../supervisor/USER_MANUAL.md), typed program routing,
  revision checks, human gates, and commit control
- [manual console](../guides/workflow.md), the direct live
  human-agent collaboration rail
- [`ztare` CLI](../guides/cli.md), the single command entry point
  (`ztare project`, `ztare autoresearch`, `ztare forecast`, `ztare leanmill`,
  `ztare bundle`, `ztare doctor`, `ztare version`, `ztare completion`, …) that wraps the underlying
  control scripts
- `ztare_workspace/gates/`, the filesystem executive inbox;
- `org/`, the ZTARE tenant overlay for roles, mandates, preferences,
  objectives, tasks, channels, controls, and sessions;
- `projects/*/workspace/`, the live project work surface;
- `analytics/public/`, the derived audit and intelligence surface.

The deferred local ZTARE workbench UI, if built, should sit over the in-loop
claim/evidence path: project intake, trace readiness, run-readiness contracts,
loop admission, run history, verdict/demotion, and review artifacts. It should
not absorb the org/task-management control plane.

The composition rule is simple:

```text
many projections, one filesystem-backed source of truth
```

Orbit makes governance state legible. The supervisor routes bounded programs.
The console session handles live ambiguity. The validator attacks a bounded
claim. Each surface must point back to the files, commands, receipts, or ledgers
that own the state it displays.

This doc uses two research-actor classes:

- Human reviewer: the accountable person who sets priorities,
  accepts risk, decides what can be public, and supplies taste or direction
  when the project surface is ambiguous.
- Agentic worker: a tool-using AI agent, such as Codex, Claude Code, or a
  role-bound Research Director, that can inspect files, run probes, edit
  artifacts, and leave a trace.

Both can operate the workbench. They do not have the same authority. An
agentic worker can execute and recommend. The human reviewer owns final
accountability for public claims, budget/risk acceptance, and strategic
direction unless a specific role mandate says otherwise.

## Module families

### 1. Evidence and claim kernel

The claim-governance kernel owns bounded source material and claim discipline:

- [workflow.md](../guides/workflow.md)
- [rubric_specification.md](rubric_specification.md)
- [harness_specification.md](harness_specification.md)
- [public_claim_register.md](../public_claim_register.md)
- [epistemic_principles.md](epistemic_principles.md)

Its job is to stop memory, persuasive prose, or private context from becoming
public truth without a bounded intake and evidence surface.

### 2. In-loop validator

The validator is the original ZTARE engine: mutator, adversarial panel, fitter
or executor, judge, deterministic gates, telemetry, and synthesis.

Key code and docs:

- [architecture.md](architecture.md)
- [cognitive_gym.md](cognitive_gym.md)
- [src/ztare/validator/README.md](../../src/ztare/validator/README.md)
- [src/ztare/gates/README.md](../../src/ztare/gates/README.md)
- [scripts/public/control/claim_discipline_demo.py](../../scripts/public/control/claim_discipline_demo.py)

This is where bounded claims get attacked under declared constraints.

### 3. Formal proof and automated proof search

This is a routing index for proof work inside the larger ZTARE
architecture. LeanMill owns the proof-engine architecture, and this map only names
the surfaces that other ZTARE layers need to call or inspect.

Key surfaces:

- [leanmill_architecture.md](leanmill_architecture.md), the proof-engine
  boundary, governed closure model, and current proof-search policy
  ([governed DAG proof-search seam](../../research_areas/seams/engine/lean/GP-246_governed_dag_proof_search_seam.md))
- [ztare_proofs/README.md](../../ztare_proofs/README.md)
- [closed_loop_theorem_writer_workflow.md](closed_loop_theorem_writer_workflow.md)
- [closure_utility_test_workflow.md](closure_utility_test_workflow.md)
- [closure_claim_governance.md](closure_claim_governance.md)
- [scripts/public/lean/README.md](../../scripts/public/lean/README.md)

The cross-system contract is typed proof evidence: verified fragments, failed
fragments, unresolved identifiers, missing primitives, closure-utility results,
and proof-credit receipts. Queue design, worker specialization, move selection,
and benchmark policy remain in the LeanMill architecture document.

### 4. Graph, GNN, and novelty diagnostics

The graph/GNN layer asks whether structural predictions actually help closure
work. It includes constraint graphs, GNN link-prediction experiments, Adamic-
Adar baselines, novelty filters, and Codex-marked closure-utility panels.

Key surfaces:

- [graph_diagnostic_belief_update_pattern.md](graph_diagnostic_belief_update_pattern.md)
- [closure_utility_test_workflow.md](closure_utility_test_workflow.md)
- [scripts/public/models/gnn_link_predict_score_v3.py](../../scripts/public/models/gnn_link_predict_score_v3.py)
- [scripts/public/models/gnn_novelty_filter.py](../../scripts/public/models/gnn_novelty_filter.py)

A GNN can predict structurally likely edges and still fail to produce closure
utility. Predictive accuracy is not the same as research value.

### 5. Forecast pool and prediction markets

The forecast layer prices research bets before resolution. It records odds,
effort, cost, expected brittleness, and decision use, then scores calibration
after outcomes land.

Key surfaces:

- [prediction_ledger_pattern.md](prediction_ledger_pattern.md)
- [agentic_engineering_patterns.md](agentic_engineering_patterns.md)
- [scripts/public/control/forecast/pool.py](../../scripts/public/control/forecast/pool.py)
- `analytics/public/ledgers/prediction/`

It makes branch selection, effort estimates, and action externalities
auditable.

### 6. Org runtime and supervisor

The organization layer gives agents offices: each LLM call answers to a
role with a mandate, scope, budget, inbox, refusal channel,
and transition obligations.

Key surfaces:

- [organizational_primitives.md](organizational_primitives.md)
- [ztare_research_company_architecture.md](ztare_research_company_architecture.md)
- [org_runtime_quickstart.md](../guides/org_runtime_quickstart.md)
- [supervisor/USER_MANUAL.md](../../supervisor/USER_MANUAL.md)
- [org/README.md](../../org/README.md)

This is where the "workbench" becomes operational. The research system can run
through direct human review work, bounded supervisor programs, or persistent
role-daemon work without losing the source-of-truth boundary.

### 7. Reflexive mining and organizational learning

The reflexive layer mines the repo's own artifacts: trajectories, catches,
forecast outcomes, action-impact rows, proof failures, and project workspaces.
It turns "what happened" into future routing and hardening pressure.

Key surfaces:

- [reflexive_engineering.md](reflexive_engineering.md)
- [agent_agnostic_recursive_gain.md](agent_agnostic_recursive_gain.md)
- [reflexive_audit_workflow.md](../guides/reflexive_audit_workflow.md)
- [scripts/public/mining/README.md](../../scripts/public/mining/README.md) —
  canonical weekly pipeline at the top level;
  [`research_mode/`](../../scripts/public/mining/research_mode/) holds the
  one-shot ticket analyses, including the
  [void-mining seam](../../research_areas/seams/engine/discovery/GP-148_void_mining_seam.md),
  weakest-link refreshes, closure/process miners, and domain audits that are
  not on the weekly path.
- [scripts/public/mining/mine_recursive_gain_candidates.py](../../scripts/public/mining/mine_recursive_gain_candidates.py)

This is the core difference between a one-off agent session and a research
institution. Work compounds only if the artifact trail is mined back into
future choices.

### 8. Scientific campaigns and public claim layer

The scientific campaigns are not the system's only purpose, but they are the
hardest stress tests: Navier-Stokes, modified gravity, consciousness governance,
neural scaling, experimental mathematics, and evaluation-design failures.

Key surfaces:

- [public_claim_register.md](../public_claim_register.md)
- [multi_substrate_validation.md](../multi_substrate_validation.md)
- [research_areas/EXPERIMENT_TRACK_RECORD.md](../../research_areas/EXPERIMENT_TRACK_RECORD.md)
- [papers/README.md](../../papers/README.md)
- [papers/case_studies/README.md](../../papers/case_studies/README.md)

The right public posture is claim-by-claim: scope, evidence, non-claim, and
next falsifier. A campaign can be impressive as a stress test while still not
licensing a domain-level claim.

## How to explain the whole repo

Use this if someone asks what ZTARE is:

```text
ZTARE is a local workbench for checking high-stakes reasoning before it becomes
a claim.
It binds sources, code, proofs, data, model outputs, agent work, checks,
forecasts, reports, and review decisions into claim states a reviewer can
inspect: promoted, demoted, blocked, deferred, or ready for the next falsifier.
```

Use this if someone asks how it relates to math-agent systems:

```text
ZTARE overlaps with AI math workbenches when proof-search or theorem-writing
is the active project surface.
The wider contribution is the governance layer around claims: source
readiness, evidence boundaries, non-claims, demotions, forecasts, report
support contracts, and reusable lessons across domains.
```

Use this if someone asks whether it is a technical tool or an organization:

```text
ZTARE is a technical stack with an organizational layer.
The technical modules make source intake, verification, proof attempts,
forecasts, reports, and ledgers executable.
The organizational layer decides authority: what can be acted on, what can be
published, what must be demoted, and what remains private or source-blocked.
```
