# ZTARE

**Catch LLMs cheating their own evaluations. Field-documented catalog +
audit patterns + a forecasting finding that decomposes "no signal" into
two opposite signals.**

- [9 ways LLMs cheat their own evaluations →](docs/cheating_catalog.md)
  9 named self-certifying strategies observed under execution-grade audit
  across Claude, Gemini, and GPT-4o, each with a code-level cheat sketch
  and the audit pattern that catches it.
---

A filesystem-first socio-technical research system for testing claims,
surfacing failure modes, and governing AI-assisted research, built by one
human operator and a rotating set of agentic operators over roughly eight
weeks, then pointed at itself.

The core stack has three parts: a zero-trust adversarial validator, an
out-of-loop research organization/runtime, and a reflexive intelligence layer
that learns from forecasts, actions, catches, trajectories, and experiment
records.

The core intuition is not that scaffolding replaces model capability. It is
that model capability is only one input. Like human talent, it compounds or
degrades depending on the environment around it: task framing, evidence
boundaries, role separation, feedback, falsifiers, memory, and accountability.
ZTARE is an attempt to build that environment for scientific generation and
validation.

```text
research org chooses work -> validator/proof/script/panel/human-agent co-work
-> ledgers and outcomes -> forecasts / action impact / trajectory mining
-> next action, split, defer, or kill
```

## What the measurement says (not asserted, mined)

A weekly reflexive audit re-mines every artifact and feeds the result
back. The numbers below were produced by that audit; they are not a
live dashboard. The live record is
[`research_areas/EXPERIMENT_TRACK_RECORD.md`](research_areas/EXPERIMENT_TRACK_RECORD.md)
and `research_areas/insights_ledger.md`. *Snapshot, mid-May 2026:*

- **On the order of 34,000 authored artifacts.** Roughly a quarter are
  ZTARE iteration files; the remainder is out-of-loop agent work, and the
  trailing-window share is even higher. The live substrate is agent
  dispatch + governance + mining.
- **The apparatus falsified its own substrate and recorded it.** A
  28-day, 157-project capability-ROI audit found that of roughly 18
  catalogued primitives, only four were engaged, seven were dead, and
  seven were never instantiated. The evolutionary zoo did not survive
  contact with the work, and the machine said so.
- **Recursive gain was real, then plateaued.** Contextualized insight
  density rose then flattened (a plateau, not an exponential; in-system
  rubric, so reported with that caveat).
- **Triple-digit ratified catches across dozens of categories — self-reported,
  in-system.** This is the apparatus auditing itself, not externally verified.
  The catch ledger's own integrity validator was found dead for weeks and
  resurrected (surfacing ~300 integrity errors to remediate), and a mis-selected
  rater was demoted mid-cycle — both recorded next to the original claims. Treat
  the count as an internal signal, not a validated benchmark.

Single operator, N=1, non-expert. Nothing here claims a solved
Millennium problem, an autonomous research engine, or a general law. The
contribution is the discipline and an honest record of where it broke.

**On named personas.** Synthetic review panels and debate logs use labels
of real individuals (for example Dijkstra, Knuth, Munger). These are
stylistic shorthand for reasoning approaches loosely inspired by published
work. They do not represent the views, endorsements, or actual reasoning
of those individuals, and no affiliation is implied. The full statement is
in `src/ztare/personas/registry.py`.

## The parts that transfer beyond this repo

Most of the value is substrate-independent and reusable without ZTARE:

- **[Agentic engineering patterns](docs/concepts/agentic_engineering_patterns.md)**, 
  practices for pipelines whose internals are LLM calls: stub-replay
  testing, eligibility pre-filters, provenance telemetry, decomposed
  wire-in, cross-reference knowledge graphs.
- **[Reflexive primitives](docs/concepts/reflexive_engineering.md)**, 
  capabilities the architecture runs on its own infrastructure (the
  audit that demoted its own claims is one of them).
- **[Epistemic discipline](docs/concepts/epistemic_principles.md)**, 
  the proposer-doesn't-grade-itself constitution, plus a
  [mining-derived anti-pattern catalog](docs/concepts/anti_pattern_catalog.md)
  and an append-only [catch ledger](LEDGERS.md).
- **The org runtime**, M-form separation (roles, mandates, gates,
  damage signals) used to actually run the project as its own research
  company. The substrate-agnostic kernel is the separate public repo
  **[github.com/sparckix/cognitive-firm](https://github.com/sparckix/cognitive-firm)**;
  this repo carries only a thin *tenant overlay* of it (GP-191, see
  [docs/guides/forking_the_kernel.md](docs/guides/forking_the_kernel.md)
  and [docs/concepts/organizational_primitives.md](docs/concepts/organizational_primitives.md)).
  A fresh public clone here runs kernel-only.
  The `org/` tree in ZTARE is therefore a compatibility and tenant overlay
  surface, not the canonical upstream kernel.
- **Research-supervision traces for frontier labs**, the design pattern of
  preserving attempts, critiques, source-readiness labels, demotions, nulls,
  and next falsifiers as training/eval material rather than keeping only final
  answers. See [architecture.md](docs/concepts/architecture.md) and
  [agent_agnostic_recursive_gain.md](docs/concepts/agent_agnostic_recursive_gain.md).
- **The full workbench/module map**, including how ZTARE relates to adjacent
  systems such as AI Co-Mathematician, and how proof search, GNN novelty,
  forecast markets, org runtime, Orbit, supervisor, and public claims compose
  into a socio-technical research institution.
  See [system_position_and_module_map.md](docs/concepts/system_position_and_module_map.md).

## What This Repo Is

ZTARE has four public tracks.

| Track | Maturity | What it does |
|---|---:|---|
| **Org Runtime Tenant Overlay** | working prototype | ZTARE's applied instance of the reusable cognitive-firm primitives: persistent role offices, mandates, tasks, objectives, key results, gates, preferences, transition logs, damage signals, and operator surfaces. |
| **ZTARE Kernel** | stable / evolving | Turns messy source material into bounded evidence snapshots, then stress-tests claims through mutator, verification panel, judge, hard gates, telemetry, synthesis, and closure. |
| **ZTARE Research Co** | dogfood / active | The repo operating as its own research company: role-bound agents use the org runtime and ZTARE kernel to run programs, close experiments, and update ledgers. |
| **Scientific Case Studies** | experimental / status-labeled | Gravity, neural scaling, Navier-Stokes, transformer-successor, and other bounded campaigns that stress-test the kernel and produce calibrated public artifacts when evidence licenses them. |

The tracks are designed to compose: the org overlay governs who acts in this
repo, the reusable kernel lives upstream in cognitive-firm, the ZTARE kernel
tests claims, ZTARE Research Co dogfoods the operating model, and case studies
supply hard substrates with explicit evidence boundaries.

The original LLM-gaming work is one important subset of the project. It is not
the whole project. The larger object is a disciplined research operating model —
for one operator, not a productized platform: claims move through evidence,
tests, gates, ledgers, and accountable roles.

---

## Core Principles

- **The proposer does not grade itself.** Generation, adversarial review,
  scoring, and deterministic gates are separate.
- **Capability needs an environment.** Stronger models widen the search
  surface, but discipline determines whether that search becomes evidence,
  slop, or premature closure.
- **Prose is not evidence.** A claim must survive executable checks, holdout
  surfaces, or explicit refusal.
- **Memory is allowed; unearned trust is not.** The workspace can accumulate
  sources. The validator starts from a bounded evidence snapshot.
- **Failures are signal.** Nulls, refusals, residual structure, and instrument
  failures are recorded because they change what to build next.
- **Chat is not the system of record.** Durable artifacts live under
  `projects/`, `research_areas/`, `org/`, `ztare_workspace/`, and `papers/`.

---

## Where to go

| If you want to... | Start at |
|---|---|
| Understand the repo layers and doc maturity | [docs/README.md](docs/README.md) |
| Understand how all modules compose | [docs/concepts/system_position_and_module_map.md](docs/concepts/system_position_and_module_map.md) |
| See what the apparatus actually has, in two minutes | [docs/concepts/capabilities.md](docs/concepts/capabilities.md) |
| Evaluate conservative public claims and non-claims | [docs/public_claim_register.md](docs/public_claim_register.md) |
| Understand proof execution, governance gate, and residual compiler | [docs/concepts/closure_claim_governance.md](docs/concepts/closure_claim_governance.md) |
| First 30 minutes in a fresh clone or vault | [docs/guides/first-30-minutes.md](docs/guides/first-30-minutes.md) |
| Run it on your own domain | [docs/guides/quickstart.md](docs/guides/quickstart.md) |
| Operate the engine via the `ztare` CLI | [docs/guides/cli.md](docs/guides/cli.md) |
| See current priorities | [priority_roadmap.md](priority_roadmap.md) |
| See the experiment record | [research_areas/EXPERIMENT_TRACK_RECORD.md](research_areas/EXPERIMENT_TRACK_RECORD.md) |
| Pressure-test a domain thesis | [docs/guides/workflow.md](docs/guides/workflow.md) |
| Understand the validator architecture | [docs/concepts/architecture.md](docs/concepts/architecture.md) |
| Why a constrained loop beats a chat loop | [docs/concepts/cognitive_gym.md](docs/concepts/cognitive_gym.md) |
| Verify the org runtime is sound on your machine in five seconds | [docs/guides/runtime_smoke_test.md](docs/guides/runtime_smoke_test.md) |
| Run or inspect the org runtime | [docs/guides/org_runtime_quickstart.md](docs/guides/org_runtime_quickstart.md) |
| Open a direct Claude/Codex terminal session | [docs/guides/operator_console.md](docs/guides/operator_console.md) |
| Understand persistent roles and agentic primitives | [docs/concepts/organizational_primitives.md](docs/concepts/organizational_primitives.md) |
| Understand the 24×7 research-org reference architecture | [docs/concepts/ztare_research_company_architecture.md](docs/concepts/ztare_research_company_architecture.md) |
| Pitch the org/ kernel to potential adopters | [docs/landings/org_runtime_landing.html](docs/landings/org_runtime_landing.html) |
| See how the kernel runs as a research company | [org/landings/research_company_landing.html](org/landings/research_company_landing.html) |
| Modify the supervisor/control plane | [supervisor/USER_MANUAL.md](supervisor/USER_MANUAL.md) |
| Read the papers | [papers/README.md](papers/README.md) |
| The 8-week build narrative, historical | [docs/sprint_60day_journey.md](docs/sprint_60day_journey.md) |
| Read the Navier-Stokes public journey/status checkpoint | [projects/ns_millennium_hunt/public/JOURNEY.md](projects/ns_millennium_hunt/public/JOURNEY.md) |
| The append-only record layer | [LEDGERS.md](LEDGERS.md) |
| The glossary | [docs/concepts/glossary.md](docs/concepts/glossary.md) |
| Contribute | [CONTRIBUTING.md](CONTRIBUTING.md) |

If you are not sure where to start, use the domain-validation path.

---

## Quickstart

```bash
git clone https://github.com/sparckix/ztare
cd ztare
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .   # registers the `ztare` console script

make help
make demo
make smoke-public

# the apparatus is now callable as a single command:
ztare --help                 # the operator surface
ztare forecast status        # sealed forecast-pool state
ztare leanmill schedule …    # LeanMill orchestration (GP-225)
ztare bundle verify …        # sealed-bundle gate
```

See [`docs/guides/cli.md`](docs/guides/cli.md) for the full subcommand
tour and the engine/governance split between this CLI and
`cognitive-firm-userland`.

`make demo` and `make smoke-public` do not invoke live model calls. Add model
API keys only when you are ready to run an LLM-backed validator loop:

```bash
export GEMINI_API_KEY=your_key_here
# Optional, depending on model pairings:
export ANTHROPIC_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here
```

Run a validator loop on an existing project:

```bash
make experiment-loop PROJECT=<project> RUBRIC=<rubric> ITERS=10 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
```

Run the full evidence workflow:

```bash
make workspace-update PROJECT=<project> MODEL=gemini
make evidence-compile PROJECT=<project> MODEL=gemini
# Review and promote compiled_evidence.txt to evidence.txt when appropriate.
make experiment-loop PROJECT=<project> RUBRIC=<rubric> ITERS=10 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
make synth PROJECT=<project> MODEL=gemini QA_MODEL=claude RENDERER=founder_memo
```

`make experiment-loop` is the safe default for live runs. It disables attacker
tools and activates hard-gate preflights when the rubric declares them. Use
`make loop` only when actively debugging and you understand the safety tradeoff.

---

## Run On A New Domain

```bash
mkdir -p projects/your_domain/raw

python -m src.ztare.common.scaffold_project_charter \
  --project your_domain \
  --mode broad

# Add source files under projects/your_domain/raw/
make workspace-update PROJECT=your_domain MODEL=gemini
make evidence-compile PROJECT=your_domain MODEL=gemini

# After reviewing compiled_evidence.txt, promote it:
cp projects/your_domain/compiled_evidence.txt projects/your_domain/evidence.txt

make experiment-loop PROJECT=your_domain RUBRIC=recursive_bayesian ITERS=10 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
```

The evidence workflow writes structured artifacts under
`projects/<project>/workspace/`: facts, contradictions, open questions,
evidence gaps, derived constraints, compile failures, and validator telemetry.

---

## Science / Discovery Track

The science track treats numerical or scientific substrates as adversarial
discovery problems. The engine proposes candidate laws, fits parameters
deterministically, tests against visible/holdout/farther-tail surfaces,
compresses forms, and records nulls when the substrate is underidentified.

```bash
make discover PROJECT=<project> RUBRIC=<rubric> ITERS=15
make compress PROJECT=<project>
make prove PROJECT=<project>
```

The honest interpretation is scoped:

- calibration recoveries show the instrument can recover known forms under
  cold-variable rigor;
- apparatus-only findings require the run artifacts and gates, not just model
  recall;
- correct refusals are valuable when the data do not license compression;
- new-science claims require stricter external validation than a high score.

For the full workflow and caveats, see [docs/guides/workflow.md](docs/guides/workflow.md)
and [docs/guides/for_researchers.md](docs/guides/for_researchers.md).

---

## Org Runtime / Tenant Overlay

ZTARE contains a local governance overlay for persistent AI research roles,
validated against the project's own work. The reusable, substrate-agnostic
kernel for this layer lives in
[cognitive-firm](https://github.com/sparckix/cognitive-firm); this repo keeps
the ZTARE tenant state, compatibility surfaces, and dogfood deployment.
A role office has a JSON-schema-validated contract (`org/roles/<role>.yaml`),
a mandate, allowed and forbidden paths, budget caps, an inbox, claims,
transition logs, and closure duties.

```text
principal preferences + objectives
-> role mandate
-> task or gate
-> daemon proposal/execution
-> transition log, closure, ledger update
```

The principal can drive the runtime through three rails. They share one source
of truth, the gate and channel JSON files on disk, so a decision made on any
rail is visible from the others within seconds.

| Rail | Best for | Surface |
|---|---|---|
| Executive inbox (filesystem) | source of truth, scriptable from any shell | `ztare_workspace/gates/pending/*.json`, `org/channels/<role>/inbox/` |
| Orbit dashboard (browser) | rich approvals with reasons, send a directive, pause/resume a daemon, OKR tree visual | `cd orbit && npm run sync` and `npm run dev` |
| Notification provider (optional tenant rail) | push notification, tap-to-approve, digest surfaces | filesystem outbox by default; tenant overlays may add Telegram/Slack/etc. |

Local smoke path:

```bash
python scripts/public/control/org_first_run_setup.py --member-id codex --agent-cli codex --agent-adapter codex_exec
```

Docker/daemon path:

```bash
docker compose --env-file .env --profile daemons run --rm research-director-daemon \
  python scripts/public/control/org_role_preflight.py --role research_director

docker compose --env-file .env --profile daemons up research-director-daemon
```

Preflight validates each role yaml against `schemas/role.v1.schema.json` and
runs the bootstrap chain in `org/bootstrap_manifest.yaml` so an agent always
boots from the same set of contracts (AGENTS.md, role yaml, mandate,
preferences, then optional procedural reads).

Docker is a deployment wrapper, not magic authentication. Full execution needs
the chosen agent runtime (`codex`, `claude`, or another adapter) installed and
authenticated inside the container or on the host running the daemon.

The org runtime is currently filesystem-backed. A daemon sees only the
`org/`, `ztare_workspace/`, and project files mounted into its process. For VPS
deployment, either create tasks on the VPS, sync private org state there, or
mount a shared state volume. See
[docs/guides/org_runtime_docker_deploy.md](docs/guides/org_runtime_docker_deploy.md).

Key docs:

- [docs/landings/org_runtime_landing.html](docs/landings/org_runtime_landing.html), adoption-pitch landing for the org/ kernel itself
- [org/landings/research_company_landing.html](org/landings/research_company_landing.html), landing framed as the ZTARE research-company adoption
- [docs/guides/operator_console.md](docs/guides/operator_console.md)
- [docs/guides/org_runtime_quickstart.md](docs/guides/org_runtime_quickstart.md)
- [docs/guides/org_runtime_docker_deploy.md](docs/guides/org_runtime_docker_deploy.md)
- [docs/concepts/organizational_primitives.md](docs/concepts/organizational_primitives.md)
- [docs/concepts/ztare_research_company_architecture.md](docs/concepts/ztare_research_company_architecture.md)
- [org/README.md](org/README.md)
- [org/bootstrap_manifest.yaml](org/bootstrap_manifest.yaml), role bootstrap chain
- [schemas/role.v1.schema.json](schemas/role.v1.schema.json), role contract schema

---

## Public / Private Boundary

ZTARE is intentionally open source, but it is not a raw operations dump. The
release rule is:

```text
ship the scientific instrument and public documentation aggressively;
keep active strategy, sealed pre-registrations, personal context, credentials,
and first-mover-sensitive product tactics private until closure or public
derivative rendering.
```

Public by default:

- research-engine code, validators, gates, fit primitives, and proof tooling;
- Lean verifier modules and exact certificate checkers;
- public docs, papers, rubrics, and calibrated closed artifacts;
- closed seams that pass the visibility rule.

Local / gitignored by default:

- local-only research notes and `.ip_protected/`;
- active strategy seams, sealed GT/pre-registration material, and in-flight
  experiment tactics;
- org-runtime mandates, preferences, channels, directives, sessions, and
  runtime task state;
- credentials, contact channels, API keys, local logs, and cloud/GPU telemetry
  that contains operational context.

The scientific instrument should be inspectable and reproducible. Active
experiments still need sealed envelopes so later results remain interpretable.

---

## What The Adversarial Validator Does

The core loop:

1. **Mutator** proposes a thesis and executable candidate.
2. **Verification panel** attacks weak assumptions.
3. **Fitter/solver** estimates parameters when the substrate is numeric.
4. **Meta-judge** scores execution output rather than persuasive prose.
5. **Hard gates** enforce deterministic pass/fail constraints.
6. **Telemetry and ledgers** preserve what happened, including failures.

This architecture grew out of the Cognitive Camouflage work: LLM-generated
code can pass holistic review while violating the intent of the test. ZTARE's
answer is separation of duties plus executable gates.

Examples of failure modes the system has had to defend against:

| Pattern | Failure |
|---|---|
| Blame shield | Hide one critical unsupported axiom among many harmless ones. |
| Float masking | Round away the precision that would reveal the failure. |
| Fake mechanism | Name a function after a mechanism while hardcoding its output. |
| Cooked RNG | Hardcode improving pseudo-random behavior instead of learning. |
| Assert narrowing | Define tests so narrowly that only the submitted case passes. |
| Unit laundering | Hide an empirical correction as a dimensional factor. |
| Straw-man comparison | Design the rival so the preferred answer wins by construction. |

The gaming paper documents the first version of this problem. The current repo
generalizes the response into a research and governance stack.

---

## Current Capability Map

| Surface | Status | Entry point |
|---|---:|---|
| Domain evidence workspace | usable | `make workspace-update`, `make evidence-compile` |
| Adversarial validator | usable | `make experiment-loop` |
| Synthesis pipeline | usable | `make synth` |
| Science compression / proof stubs | experimental | `make discover`, `make compress`, `make prove` |
| Evaluator hardening / gates | active development | `docs/concepts/architecture.md`, `supervisor/USER_MANUAL.md` |
| Org runtime overlay / role daemons | working today | `docs/guides/org_runtime_quickstart.md` |
| ZTARE Research Co dogfood loop | active | `priority_roadmap.md`, `research_areas/EXPERIMENT_TRACK_RECORD.md`, `research_areas/specs/active/apparatus/instrumentation/GP-244_research_operations_intelligence_cockpit_spec.md` |
| Executive inbox (filesystem rail) | working today | `ztare_workspace/gates/pending/` + `org/channels/` |
| Orbit governance UI (browser rail) | working today | `orbit/` (gate review queue, principal cockpit, OKR tree) |
| Notification provider (optional rail) | tenant-specific | filesystem outbox by default; Telegram/Slack/etc. belong in tenant overlays |

---

## Repository Map

| Path | Purpose |
|---|---|
| `src/ztare/` | Python implementation: validator, fit primitives, gates, synthesis, workspace, orchestration. |
| `projects/` | Domain projects, evidence, workspaces, validator artifacts, scientific sandboxes. |
| `rubrics/` | Scoring rubrics and gate configuration. |
| `docs/` | Architecture, workflow, concepts, product/runtime docs. |
| `papers/` | Public manuscript sources. |
| `ztare_proofs/` | Lean proof sources and formalization experiments; generated `.lake/` build state is ignored. |
| `research_areas/` | Experiment track record, current board, seams, specs, debates, research logs. |
| `org/` | Roles, mandates, preferences, tasks, objectives, channels, runtime state. |
| `supervisor/` | Program registry, manifests, control-plane docs. |
| `orbit/` | Governance UI projection. |
| `ztare_workspace/` | Gates, transition logs, runtime projections. |

Rule of thumb:

- human-readable research prose goes under `research_areas/`;
- supervisor/runtime JSON state goes under `supervisor/`, `org/`, or
  `ztare_workspace/`;
- project evidence and run artifacts stay under `projects/`.

---

## Published Papers And Manuscripts

- [Cognitive Camouflage](papers/cognitive-camouflage/draft.md), specification gaming in LLM-generated code | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960)
- [Adversarial Precedent Memory](papers/adversarial-precedent-memory/draft.md), hardening evaluators through mined failure constraints | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598)
- [Contract-Governed Hardening](papers/contract-governed-hardening/draft.md), stage-gated recursive improvement with typed promotion contracts | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998)
- [Cognitive Firm](papers/cognitive-firm/draft.md), managerial capitalism for artificial intelligence | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019)
- [Epistemic Verification](papers/epistemic-verification/draft.md), manuscript in revision.
- Adversarial Compression, experimental mathematics manuscript (draft not mirrored in this repository).

The papers are best read as a stack:

1. LLMs game underspecified evaluation.
2. Mined precedents and deterministic gates harden evaluators.
3. Typed promotion contracts make recursive hardening safer.
4. Persistent organizational roles govern AI work.
5. Epistemic verification decomposes judgment into repeatable operations plus
   a bounded residual.

The active case-study layer applies this stack across scientific and governance
substrates as falsifier pressure rather than discovery rhetoric. It should be
read through the experiment records and promoted public papers, not through
private working drafts.

---

## Claims To Read Carefully

ZTARE is designed to improve research discipline, not to guarantee truth.

Do not infer:

- that a high score proves a scientific discovery;
- that calibration recoveries are new science;
- that an LLM cold shot is a controlled baseline unless model/date/prompt are
  recorded;
- that hard gates cover every possible failure mode;
- that the org runtime is enterprise-ready merely because the local
  single-team path works;
- that “works on any domain” means no domain-specific evidence engineering is
  needed.

The intended standard is stricter: if a result matters, it needs artifacts,
gates, closure rows, and a clear statement of what would falsify it.

---

## Recommended Agent-Assisted Workflow

This repo is easiest to operate with an agentic coding assistant such as Codex
or Claude Code because the meaningful state is distributed across artifacts.

Useful prompts are collected in [docs/guides/agent-prompts.md](docs/guides/agent-prompts.md).
Start with one of those paste-ready prompts when using a fresh Codex or Claude
session to learn the repo, inspect a project, audit the forecast market, or
work in observer mode on NS.

For agents working inside this repo, [AGENTS.md](AGENTS.md) is the repo-level
constitution.

---

## Intellectual Lineage

ZTARE borrows from several traditions without treating any as decorative:

- Karpathy's LLM wiki pattern for accumulating source memory upstream of the
  validator.
- Popperian falsification: cheap refutation is more valuable than persuasive
  confirmation.
- Mungerian inversion and checklist discipline: name what would make success
  uninterpretable before celebrating it.
- Scientific management, cybernetics, and organizational design: roles,
  handoffs, ledgers, and closure matter when cognition becomes machine-aided.

---

## License

MIT. The governance/orchestration code in `org/`, `supervisor/`, `orbit/`, `deploy/`, and `src/ztare/{orchestration,supervisor,sessions,signals,notifications}/` is ZTARE's tenant-overlay integration of the upstream [cognitive-firm](https://github.com/sparckix/cognitive-firm) kernel; the canonical kernel and its license live in that repository.

Files ignored by the public/private boundary are not part of the public license grant until deliberately promoted.

[LICENSES.md](LICENSES.md) is the file-by-file map; the full text is in [LICENSE](LICENSE). Third-party notices are in [NOTICE.md](NOTICE.md).

---

## Citation

If you cite this work, cite the specific paper or artifact you are using rather
than the repository as a monolith.

```bibtex
@misc{alami2026cognitivecamouflage,
  title = {Cognitive Camouflage: Specification Gaming in LLM-Generated Code Evades Holistic Evaluation but Not Adversarial Execution},
  author = {Alami, Daniel},
  year = {2026},
  note = {SSRN preprint 6512960. Code: github.com/sparckix/ztare},
  url = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960}
}

@misc{alami2026adversarialprecedent,
  title = {Adversarial Precedent Memory: Hardening LLM Evaluators Through Mined Failure Constraints},
  author = {Alami, Daniel},
  year = {2026},
  note = {SSRN preprint 6525598. Code: github.com/sparckix/ztare},
  url = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598}
}

@misc{alami2026contractgoverned,
  title = {Contract-Governed Adversarial Evaluator Hardening: Stage-Gated Recursive Improvement with Typed Promotion Contracts},
  author = {Alami, Daniel},
  year = {2026},
  note = {SSRN preprint 6542998. Code: github.com/sparckix/ztare},
  url = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998}
}

@misc{alami2026cognitivefirm,
  title = {The Cognitive Firm: Managerial Capitalism for Artificial Intelligence},
  author = {Alami, Daniel},
  year = {2026},
  note = {SSRN preprint 6543019. Code: github.com/sparckix/ztare},
  url = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019}
}
```
