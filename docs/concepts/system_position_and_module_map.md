---
description: "How ZTARE positions itself among related AI research systems and how its major modules compose."
---
# System Position And Module Map

> **Up:** [Documentation map](../README.md)

ZTARE is a socio-technical research system for AI-assisted scientific work.
The technical machinery matters, but it is not the whole object. The system is
the combination of a human principal, agentic operators, role offices, source
boundaries, verification tools, governance gates, public/private membranes,
ledgers, and publication discipline.

It is therefore not only a theorem prover, not only a symbolic-regression
loop, not only an agent dashboard, and not only a set of papers. The core
object is the full research trace: sources, proposals, tests, failures,
demotions, forecasts, proof attempts, claims, non-claims, next falsifiers, and
the authority path that decides what those artifacts are allowed to mean.

The shortest accurate summary is:

```text
ZTARE turns human-agent research activity into auditable claims.
```

That means the repo has several modules that look different on the surface but
serve one architecture: make research moves explicit enough that another
agentic operator, the human operator, or a future model can inspect, reuse,
refute, or demote them.

## System Position

ZTARE sits at the intersection of six related system families:

- **Socio-technical research organizations:** systems that coordinate human
  judgment, agentic labor, evidence, authority, and publication boundaries.
- **AI research assistants and co-scientists:** systems that help propose,
  critique, test, and refine scientific ideas.
- **Formal proof and theorem-workbench systems:** systems that search,
  repair, verify, or triage formal mathematical artifacts.
- **Agent workbenches and control planes:** systems that let tool-using agents
  operate on real files, processes, tickets, gates, and runtime state.
- **Evaluation and governance systems:** systems that harden claims through
  rubrics, adversaries, deterministic checks, provenance, and audit trails.
- **Research-operations systems:** systems that allocate attention, forecast
  branch value, track outcomes, and learn from organizational behavior.

ZTARE is not trying to reduce itself to any one of those categories. It is
trying to compose them into one auditable research institution. The
distinctive object is the **claim lifecycle**, not any single model call,
tool invocation, dashboard, or proof script:

```text
source -> attempt -> critique -> executable check -> forecast / gate
-> promote, demote, null, defer, or source-block
-> ledger -> mined learning -> next route
```

The question ZTARE asks is not only "can an agent solve the problem?" It also
asks:

- what evidence licensed the attempt;
- which source boundary was active;
- which verifier or gate actually fired;
- whether the result is a claim, null, demotion, or source-blocked residue;
- which next falsifier would change the decision;
- whether the organization learned how to route the next attempt better.

That is why ZTARE keeps so much filesystem state. The value is not only the
answer. The value is the labeled path by which the answer, non-answer, or
demotion was produced.

## Related Systems

Related systems should be mentioned as orientation, not treated as targets to
beat unless there is a current external benchmark. The point is to locate
ZTARE in the system landscape, not to center any one adjacent project.

**AI Co-Mathematician.** Google DeepMind's
[AI Co-Mathematician](https://arxiv.org/abs/2605.06651) is a math-focused
agentic workbench for interactive mathematical discovery. ZTARE overlaps only
where ZTARE is doing proof/search work: theorem nomination, Lean checking,
proof-search triage, graph diagnostics, novelty filters, and closure-utility
tests. That is a related-system pointer, not the central comparison. ZTARE
should not use AI Co-Mathematician as the public yardstick for the repo; the
repo's center of gravity is the broader socio-technical claim lifecycle.

**AI co-scientist and automated-research systems.** ZTARE is closer in spirit
to systems that generate hypotheses, design experiments, criticize claims, and
iterate on evidence. The difference is its insistence on a filesystem-backed
institution: claims must land in source packets, public registers, ledgers,
gates, forecasts, or demotion records before they count as durable knowledge.

**Formal proof factories.** ZTARE has a formal/proof module, but this is one
subsystem inside the larger workbench. It includes Lean sources, proof gates,
LeanSearch-style queues, GNN/graph diagnostics, closure-utility tests, and
internal-for-now LeanMill work. The LeanMill engine's importable kernel lives
at [`src/ztare/leanmill/`](../../src/ztare/leanmill/README.md) (work queue,
paths, policy, common helpers, source-query contract); operator scripts under
`scripts/public/control/leanmill_*` are thin shims that re-export from the
kernel. LeanMill should be described publicly only at the architectural level:
a source-qualified proof-factory line for turning candidate proof rows into
intake queues, source-quality decisions, repair canaries, and status packets.
Do not make public performance claims about LeanMill, or link internal
operating surfaces as evidence, until its benchmark, source boundary, and
leakage controls are separately written up.
The public proof-search loop is summarized in
[closure_claim_governance.md](closure_claim_governance.md): Proof Execution,
Governance Gate, Residual Compiler, and the closure-credit boundary.

**Socio-technical research infrastructure.** ZTARE also belongs next to
systems that are not "AI models" in the narrow sense: lab notebooks, issue
trackers, review boards, experiment registries, provenance systems,
forecasting processes, and release governance. The claim is that AI-assisted
science needs all of those functions in one inspectable loop. Without the
social and institutional layer, a powerful model can still produce persuasive
unreviewed artifacts; without the technical layer, the institution cannot
scale evidence, replay, or verification.

**Agent workbenches.** Codex, Claude Code, and similar tool-using agents are
agentic operators inside the ZTARE workbench. ZTARE adds the governance layer
around them: role mandates, filesystem gates, public/private boundaries,
source-readiness labels, and claim ledgers.

**Prediction markets and research-ops systems.** The forecast pool and
prediction ledger make research allocation explicit. They do not replace
scientific judgment; they record what was expected before resolution and
whether that expectation changed what the organization did.

**Eval and model-governance systems.** ZTARE shares concerns with evaluation
harnesses, red-team systems, and AI governance stacks, but it is narrower and
more operational: the unit is a concrete research claim moving through
evidence, adversaries, gates, ledgers, and publication boundaries.

## The Workbench Layer

The workbench is the surface a human or agent uses to operate the research
system. It includes:

- [Orbit](../../orbit/README.md), a browser projection over governance state;
- [supervisor](../../supervisor/USER_MANUAL.md), typed program routing,
  revision checks, human gates, and commit control;
- [operator console](../guides/operator_console.md), the direct
  human-agent collaboration rail;
- [`ztare` CLI](../guides/cli.md), the single command entry point
  (`ztare forecast`, `ztare leanmill`, `ztare bundle`, `ztare doctor`,
  `ztare version`, `ztare completion`, …) that wraps the underlying
  control scripts;
- `ztare_workspace/gates/`, the filesystem executive inbox;
- `org/`, the ZTARE tenant overlay for roles, mandates, preferences,
  objectives, tasks, channels, controls, and sessions;
- `projects/*/workspace/`, the live project work surface;
- `analytics/public/`, the derived audit and intelligence surface.

These are not separate products glued together. They are different views of
the same control principle:

```text
many projections, one filesystem-backed source of truth
```

Orbit can make state legible. The supervisor can route bounded programs. The
operator console can handle live ambiguity. The validator can attack a bounded
claim. None of those surfaces is allowed to become the whole system.

This doc uses **operator** in two distinct senses:

- **Human operator / principal:** the accountable person who sets priorities,
  accepts risk, decides what can be public, and supplies taste or direction
  when the substrate is ambiguous.
- **Agentic operator:** a tool-using AI agent, such as Codex, Claude Code, or a
  role-bound Research Director, that can inspect files, run probes, edit
  artifacts, and leave a trace.

Both can operate the workbench. They do not have the same authority. An
agentic operator can execute and recommend; the human operator owns final
accountability for public claims, budget/risk acceptance, and strategic
direction unless a specific role mandate says otherwise.

## Module Families

### 1. Evidence And Claim Kernel

The evidence kernel owns bounded source material and claim discipline:

- [workflow.md](../guides/workflow.md)
- [rubric_specification.md](rubric_specification.md)
- [harness_specification.md](harness_specification.md)
- [public_claim_register.md](../public_claim_register.md)
- [epistemic_principles.md](epistemic_principles.md)

Its job is to stop memory, persuasive prose, or private context from becoming
public truth without a bounded evidence packet.

### 2. In-Loop Validator

The validator is the original ZTARE engine: mutator, adversarial panel, fitter
or executor, judge, deterministic gates, telemetry, and synthesis.

Key code and docs:

- [architecture.md](architecture.md)
- [cognitive_gym.md](cognitive_gym.md)
- [src/ztare/validator/README.md](../../src/ztare/validator/README.md)
- [src/ztare/gates/README.md](../../src/ztare/gates/README.md)
- [scripts/public/control/current_engine_demo.py](../../scripts/public/control/current_engine_demo.py)

This is where bounded claims get attacked under declared constraints.

### 3. Formal Proof And Automated Proof Search

The proof layer includes Lean sources, theorem-writing loops, proof gates,
typed endpoint packs, LeanSearch-style adapters, and source-quality checks.

Key surfaces:

- [ztare_proofs/README.md](../../ztare_proofs/README.md)
- [closed_loop_theorem_writer_workflow.md](closed_loop_theorem_writer_workflow.md)
- [closure_utility_test_workflow.md](closure_utility_test_workflow.md)
- [closure_claim_governance.md](closure_claim_governance.md)
- [scripts/public/lean/README.md](../../scripts/public/lean/README.md)

Its honest role is not "automatic theorem solving." Its role is to turn proof
attempts into typed artifacts: verified fragments, failed fragments,
unresolved identifiers, missing primitives, and closure-utility evidence.

### 4. Graph, GNN, And Novelty Diagnostics

The graph/GNN layer asks whether structural predictions actually help closure
work. It includes constraint graphs, GNN link-prediction experiments, Adamic-
Adar baselines, novelty filters, and Codex-marked closure-utility panels.

Key surfaces:

- [graph_diagnostic_belief_update_pattern.md](graph_diagnostic_belief_update_pattern.md)
- [closure_utility_test_workflow.md](closure_utility_test_workflow.md)
- [scripts/public/models/gnn_link_predict_score_v3.py](../../scripts/public/models/gnn_link_predict_score_v3.py)
- [scripts/public/models/gnn_novelty_filter.py](../../scripts/public/models/gnn_novelty_filter.py)

This module is a good example of ZTARE's non-hype discipline: a GNN can predict
structurally likely edges and still fail to produce closure utility. Predictive
accuracy is not the same as research value.

### 5. Forecast Pool And Prediction Markets

The forecast layer prices research bets before resolution. It records odds,
effort, cost, expected brittleness, and decision use, then scores calibration
after outcomes land.

Key surfaces:

- [prediction_ledger_pattern.md](prediction_ledger_pattern.md)
- [agentic_engineering_patterns.md](agentic_engineering_patterns.md)
- [scripts/public/control/forecast/pool.py](../../scripts/public/control/forecast/pool.py)
- `analytics/public/ledgers/prediction/`

This is not decorative forecasting. It is a way to make branch selection,
effort estimates, and action externalities auditable.

### 6. Org Runtime And Supervisor

The organization layer gives agents offices rather than treating every LLM
call as a peer. A role has a mandate, scope, budget, inbox, refusal channel,
and transition obligations.

Key surfaces:

- [organizational_primitives.md](organizational_primitives.md)
- [ztare_research_company_architecture.md](ztare_research_company_architecture.md)
- [org_runtime_quickstart.md](../guides/org_runtime_quickstart.md)
- [supervisor/USER_MANUAL.md](../../supervisor/USER_MANUAL.md)
- [org/README.md](../../org/README.md)

This is where the "workbench" becomes operational. The research system can run
through direct operator work, bounded supervisor programs, or persistent
role-daemon work without losing the source-of-truth boundary.

### 7. Reflexive Mining And Organizational Learning

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
  one-shot ticket analyses (GP-148/149 weakest-link, closure/process miners,
  substrate audits) that are not on the weekly path.
- [scripts/public/mining/mine_recursive_gain_candidates.py](../../scripts/public/mining/mine_recursive_gain_candidates.py)

This is the core difference between a one-off agent session and a research
institution. Work compounds only if the artifact trail is mined back into
future choices.

### 8. Scientific Campaigns And Public Claim Layer

The rowdy projects are not the system's only purpose, but they are the hardest
stress tests: Navier-Stokes, modified gravity, consciousness governance,
neural scaling, experimental mathematics, and evaluation-design failures.

Key surfaces:

- [public_claim_register.md](../public_claim_register.md)
- [multi_substrate_validation.md](../multi_substrate_validation.md)
- [research_areas/EXPERIMENT_TRACK_RECORD.md](../../research_areas/EXPERIMENT_TRACK_RECORD.md)
- [papers/README.md](../../papers/README.md)
- [papers/case_studies/README.md](../../papers/case_studies/README.md)

The right public posture is claim-by-claim: scope, evidence, non-claim, and
next falsifier. A campaign can be impressive as a stress test while still not
licensing a domain-breakthrough claim.

## How To Explain The Whole Repo

Use this if someone asks what ZTARE is:

```text
ZTARE is a public, filesystem-first research workbench for AI-assisted science.
It combines adversarial validation, proof/search tooling, role-bound agents,
forecast markets, graph diagnostics, and reflexive mining so that research
claims can be promoted, demoted, or blocked with an auditable trace.
```

Use this if someone asks how it relates to math-agent systems:

```text
ZTARE overlaps with AI math workbenches in its proof-search and theorem-writing
modules, but its larger contribution is the governance layer around research:
evidence boundaries, non-claims, demotions, forecasts, source readiness, and
organizational learning across domains.
```

Use this if someone asks whether it is a technical tool or an organization:

```text
It is both. ZTARE's technical modules matter because they make evidence,
verification, proof attempts, forecasts, and ledgers executable. Its
organizational layer matters because it decides authority: what can be acted
on, what can be published, what must be demoted, and what remains private or
source-blocked.
```
