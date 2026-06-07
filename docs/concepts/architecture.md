---
description: "The current ZTARE architecture: in-loop validation, out-of-loop research operations, and reflexive intelligence."
---

# ZTARE Architecture

> **Up:** [Documentation map](../README.md)

ZTARE is no longer only an autoresearch loop. The original loop still matters:
it is the zero-trust validator that tests a bounded claim against bounded
evidence. The current system is larger. It is a research operating stack with
three cooperating layers:

1. **In-loop validation**: adversarial claim testing under deterministic gates.
2. **Out-of-loop research operations**: roles, mandates, tasks, gates,
   ledgers, projects, and human-agent work outside a single validator run.
3. **Reflexive intelligence**: forecasts, action-impact records, trajectory
   mining, experiment ledgers, catch ledgers, and dashboards that help the
   organization learn from its own behavior.

The system thesis is simple:

```text
Do not ask an AI to certify its own work.
Do not ask a chat transcript to be organizational state.
Do not let intelligence stay trapped in conversation.
```

ZTARE separates generation, verification, authority, execution, and learning
so that each layer can fail visibly.

If you are reviewing whether the architecture has evidence behind it, start
with the [evidence atlas](../evidence_atlas/README.md) before reading this
document end-to-end. This page explains the machinery; the atlas links
machinery to claim cards, project summaries, experiments, runnable checks, and
caveats.

## Contents

**Orientation** — [Model capability is not the unit](#model-capability-is-not-the-unit-of-analysis) ·
[Training flywheel](#frontier-labs-and-the-training-flywheel) ·
[Architecture at a glance](#architecture-at-a-glance)

**Where things live** — [Repository topology](#repository-topology) ·
[Cross-cutting invariants](#cross-cutting-invariants) ·
[The four hard boundaries](#the-four-hard-boundaries)

**The four layers** — [1 · Evidence & artifacts](#layer-1-project-evidence-and-artifacts) ·
[2 · In-loop validator](#layer-2-the-in-loop-validator) ·
[3 · Out-of-loop research ops (LeanMill)](#layer-3-out-of-loop-research-operations) ·
[4 · Reflexive intelligence (capability catalog)](#layer-4-reflexive-intelligence)

**Operating model** — [Human & agentic operators](#human-and-agentic-operators) ·
[Canonical state vs. projections](#canonical-state-vs-projections) ·
[Public repo boundary](#public-repo-boundary)

**Reference** — [What to use when](#what-to-use-when) ·
[Failure modes caught](#failure-modes-the-architecture-is-built-to-catch) ·
[Maturity](#current-maturity) · [Documentation map](#documentation-map)

> **Deeper maps:** this page is the *navigable overview*. For the module-level
> family map see [system_position_and_module_map.md](system_position_and_module_map.md);
> for the LeanMill engine see [leanmill_architecture.md](leanmill_architecture.md);
> for the reflexive layer see [reflexive_engineering.md](reflexive_engineering.md).

## Model Capability Is Not The Unit Of Analysis

ZTARE is built around a model-environment thesis. Frontier model capability
matters, but it is not the whole research system. A stronger model can search
more space, generate better analogies, and find sharper candidate arguments.
It can also find more persuasive shortcuts through weak evaluation surfaces,
misattribute prior work, and close too early.

The claim is not anti-scaling. Bigger models help. The claim is that raw
capability becomes durable research progress only when the surrounding
environment is designed well: bounded evidence, separate judges, deterministic
checks, source-readiness gates, persistent ledgers, explicit non-claims, and
fast demotion of attractive wrong stories.

In that sense, ZTARE is the nurture side of AI-assisted research. The model is
the talent; the repository is the training environment, institution, lab
notebook, reviewer pool, and memory system that decides whether that talent
turns into auditable work.

## Frontier Labs And The Training Flywheel

Frontier labs almost certainly run internal versions of parts of this loop:
agents generate candidate work, tools test it, human experts review it, and
the resulting traces can feed evaluation, post-training, or future model
development. ZTARE should not pretend that this idea is unavailable to labs.
The public contribution is different.

ZTARE makes the flywheel explicit at the repository and institution layer:

```text
research act -> artifact -> adversarial review -> gate / demotion / null
-> source-readiness and claim ledger -> mined supervision signal
-> better future routing, prompts, gates, rubrics, and training/eval data
```

For a frontier lab, the useful lesson is not "use ZTARE instead of training."
It is: preserve the full epistemic trace of research work before collapsing it
into model weights. A failed proof attempt, a source-blocked claim, an
attribution correction, a demoted causal story, or a next-falsifier packet is
often more valuable as supervision than a polished final answer.

The lab-facing use case is therefore a trace factory for research judgment:

- generate hard research attempts under bounded evidence;
- force independent critique and deterministic checks where possible;
- label outputs as promote, demote, null, source-blocked, or needs-falsifier;
- preserve provenance and non-claims alongside the answer;
- train or evaluate future systems on those labeled traces, not just on final
  solutions.

This is also why public ZTARE remains useful even if frontier labs already do
the private version. A model weight update hides the institution that produced
the judgment. A filesystem-first repo exposes it: the artifacts, the failed
claims, the gates, the demotions, the source gaps, and the operator decisions
remain inspectable.

For plain-language definitions, see [glossary.md](glossary.md).

---

## Architecture At A Glance

```text
                         human principal
                               |
                               v
                    preferences / mandates / gates
                               |
          +--------------------+--------------------+
          |                                         |
          v                                         v
  out-of-loop research org                  in-loop validator
  roles, tasks, channels,                   bounded evidence,
  objectives, projects,                     adversarial agents,
  ledgers, daemons                          deterministic gates
          |                                         |
          +--------------------+--------------------+
                               |
                               v
                    reflexive intelligence layer
                    forecasts, action impact,
                    trajectory mining, catch ledger,
                    experiment ledger, dashboards
                               |
                               v
                   next action / kill / split / defer
```

The old mental model was:

```text
raw -> evidence -> adversarial loop -> synthesis
```

The current mental model is:

```text
research organization -> chooses work
work may enter validator, proof, script, panel, or human-agent co-work
outcomes enter ledgers
ledgers update forecasts, routing, primitives, and future work selection
```

---

## Repository Topology

The system is a **kernel** (`src/ztare/`, ~30 subpackages, importable and unit-testable)
plus **operator scripts** (`scripts/public/`, thin shims that orchestrate the kernel)
plus **canonical state** (files/ledgers) and **projections** (dashboards/UIs). The kernel
subpackages, grouped by the four layers, with size as a scale signal:

| Layer | Kernel subpackages (`src/ztare/…`) | Role |
|---|---|---|
| Cross-cutting | `gates/` (147), `common/` (9), `primitives/`, `notifications/` | deterministic gates + shared primitives + rails |
| L2 — Validation | `validator/` (28), `framer/` (11), `framer_gates/`, `rubrics/`, `scaffold/` | adversarial claim testing under rubrics |
| L3 — Formal/proof | `leanmill/` (7), `formal/` (10), `motion/` (6) | Lean queue/engine, compile/REPL, distance metrics |
| L3 — Research ops | `research_director/` (45), `orchestrator/` (74), `supervisor/` (48), `orchestration/` (25), `substrates/` (29), `roles/`, `sessions/`, `composition/` | mandates, dispatch, role daemons, substrate plugins |
| L4 — Reflexive | `forecasting/`, `fit/` (25), `synthesis/`, `signals/`, `experiments/`, `findings/` | forecasts, calibration, mining, learning |

Operator scripts: `scripts/public/control/` (303 — lane workers, daemons, runners),
`mining/` (36 — reflexive mining), `lean/` (26 — proof providers/tooling),
`validators/` (14 — discipline linters), `analytics_shared/`, `audits/`, `utilities/`.

> The **module-level** family map (what each module does, by function) is
> [system_position_and_module_map.md](system_position_and_module_map.md). This table is
> the navigational index into it; that doc is the detail.

## Cross-Cutting Invariants

Beyond [the four hard boundaries](#the-four-hard-boundaries), four invariants hold across
every layer. They are what keep the system from drifting into the failure modes below.

1. **Kernel/script dependency direction is one-way.** `src/ztare/` never imports from
   `scripts/`. Durable, substrate-generic logic lives in the kernel (testable in
   isolation); `scripts/public/control/` holds only LeanMill-/operator-specific
   orchestration. A primitive that surfaces a reusable capability belongs in the kernel.

2. **Substrate-agnostic core; substrate specifics plug in.** Shared runners/gates carry
   no NS/Clay/PDE/APN logic. Substrate behavior enters via config/registry/plugin
   (`org/structural_anchors/registry.yaml`, policy `domain_atlases`, the substrate
   `contract`) — never hardcoded in shared code. The generic organization kernel itself
   lives in [cognitive-firm](https://github.com/sparckix/cognitive-firm); `org/` is the
   ZTARE tenant overlay.

3. **Capability discoverability through one catalog.** Reusable primitives (gates,
   operators, analytical/statistical utilities) are registered in
   `analytics/public/index/architecture_index.jsonl` and surfaced by
   `primitive_tick_surface.py` into the RD brief, plus a semantic precheck
   (`research_director/primitive_amnesia.py` — gemini-embedding atlas, vocabulary-invariant
   query, category tiers) so a task surfaces the capabilities that already exist instead of
   reinventing them. Anti-patterns/patterns surface from the
   [anti-pattern catalog](anti_pattern_catalog.md) via `build_context_primer.py`.

4. **Generation never ratifies itself.** Across layers, the actor that proposes is never
   the actor that grants credit (validator firing squad; LeanMill solver proposes /
   governance ratifies; the GP-241 commit membrane as sole writer of the official store).

## The Four Hard Boundaries

ZTARE is mostly boundary discipline. The implementation can change, but these
separations should not.

| Boundary | What it prevents | Canonical surface |
|---|---|---|
| Evidence vs. memory | accumulated notes becoming trusted truth | project `raw/`, workspace, `evidence.txt`, provenance |
| Proposal vs. verification | the generator grading itself | validator, firing squad, deterministic gates; GP-241 commit-membrane daemon as the sole writer of the official evidence ledger |
| Authority vs. notification | chat, Orbit, or a phone rail owning state | `ztare_workspace/gates/`, transition log, role mandates |
| Intelligence vs. action | dashboards and forecasts silently becoming authority | GP-230 forecasts, GP-243 action impact, GP-244 intelligence surface |

A projection can be useful without being authoritative. Orbit is a projection.
A notification provider is a projection. A dashboard is a projection. The
authority lives in files and ledgers that can be replayed.

---

## Layer 1: Project Evidence And Artifacts

Projects hold domain work. A project can be a validator substrate, a Lean
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
- `latest_*` and `champion_*` artifacts: run outputs when the project uses the
  original in-loop validator.

The invariant is that memory can help compile evidence, but evidence must be
bounded when the validator is asked to judge a claim.

---

## Layer 2: The In-Loop Validator

The in-loop validator is the original ZTARE engine. It exists for cases where a
claim should be attacked under a declared rubric and deterministic checks.

Typical flow:

```text
raw/workspace -> evidence snapshot -> mutator proposal
-> adversarial review -> deterministic execution/gates
-> score/champion -> synthesis or failure report
```

Core responsibilities:

- keep the proposing agent separate from the judging surface;
- execute tests rather than trusting prose;
- use hard gates when a claim has numeric or structural invariants;
- preserve run artifacts so later readers can see why a claim survived or died;
- stop honestly when the evidence, grammar, or gates cannot support the claim.

This layer is documented in more detail by:

- [cognitive_gym.md](cognitive_gym.md), the constraint-stack theory;
- [workflow.md](../guides/workflow.md), the user workflow;
- [rubric_specification.md](rubric_specification.md), the substrate/rubric
  contract.

The validator is not the whole organization. It is one instrument.

---

## Layer 3: Out-Of-Loop Research Operations

Much of ZTARE’s current work does not begin as a validator run. The research
organization needs to decide what to inspect, what to delegate, what to kill,
what to formalize, and when the human must work alongside an agent.

The out-of-loop layer owns:

- roles and mandates under `org/`;
- tasks, objectives, key results, preferences, and role channels;
- gates under `ztare_workspace/gates/`;
- transition events under `ztare_workspace/transitions.jsonl`;
- project-level scripts, proof work, notebooks, handoffs, and research notes;
- role daemons and operator-console workflows;
- substrate-specific execution engines, currently dominated by **LeanMill**
  (see below).

This layer exists because chat is not durable state. A human-agent conversation
may discover a decisive test, but the test only compounds when it becomes a
task, gate, script, forecast contract, action-impact row, finding, or paper
artifact.

### LeanMill — the substrate engine for Lean proof work

LeanMill (`src/ztare/leanmill/`) is the apparatus's durable proof-execution
bus, sized for the GP-225 Carleson-premise-selection substrate but reusable
beyond it. It owns a SQLite `WorkItem` queue, an append-only JSONL event
ledger, a typed source-query contract (`schema:
leanmill-source-query-contract-v1`), a folder-local policy loader, and a
canonical set of path constants. The control surface includes station
scheduling, source scouting, family-spec YAML repair, family birth, target
resolution, source materialization, source-mined static candidates,
governed-static confirmation, proof probes, C-supply growth, benchmark prep
and execution, typed exits, and factory intelligence. Worker scripts dispatch
into the queue; the engine is the single source of truth for what each
worker has tried and what each tried-thing returned. LeanMill never imports
from `scripts/` — the dependency direction is fixed so the engine can be
tested in isolation and so operator scripts at the surface remain thin
orchestration shims. Spec and seam live at
`research_areas/seams/engine/lean/GP-225_leanmill_vnext_station_factory_seam.md`
and the matching active spec; the pre-registered four-arm evaluation
harness contract is at
`analytics/public/leanmill/dashboard_data/evaluation_harness_contract.json`.
Operationally, LeanMill is what makes "proof attempt at this lemma" a
first-class artifact rather than a transient subprocess.

The current LeanMill credit boundary is stricter than raw closure count. A
strict C row needs target-safe family-template evidence, completed public and
governed static arms with no positive signal, and a governed family-spec probe
with positive proof-value evidence plus matched negative-control failure. The
policy target is 20 strict C rows, with separate family and source-breadth
diagnostics so repeated variants of one family or one source aperture stay
visible as breadth debt. Source-mined rows now pass through a temporary
candidate selection and governed-static confirmation before template backfill,
and singleton family-token matches remain diagnostics only. This prevents
public-only no-signal evidence or weak family matches from being counted or
silently stranded. Tiny benchmark runs are claim-classified as wiring smokes;
internal or publishable benchmark claims require the policy's completed row
thresholds and clean preflight receipts.

Queue priority and recommendation ordering are policy-owned in
`leanmill_factory_policy.json`. The policy states that higher integer priority
wins, and explains the rationale: credit-integrity, target binding,
governance, and benchmark-readiness blockers outrank throughput because they
can invalidate downstream evidence; supply-generation work outranks advisory
observability only after the credit boundary is safe. Scripts may read policy
values and emit receipts, but proof credit still comes only from governed
receipts.

See the LeanMill-specific architecture note for lane details, handoffs, and
credit boundaries: [leanmill_architecture.md](leanmill_architecture.md). That
note is also the current process-flow view: stations, worker specialization,
queue buffers, bottleneck resources, policy-owned worker counts, and the main
conflict points between source breadth, family breadth, heavy-Lean slots, and
credit governance.

The reusable organization-kernel version of these ideas lives in
[cognitive-firm](https://github.com/sparckix/cognitive-firm). In this repo,
`org/` is the ZTARE tenant overlay and compatibility surface.

See:

- [organizational_primitives.md](organizational_primitives.md);
- [ztare_research_company_architecture.md](ztare_research_company_architecture.md);
- [org_runtime_quickstart.md](../guides/org_runtime_quickstart.md);
- [org/README.md](../../org/README.md).

---

## Layer 4: Reflexive Intelligence

The reflexive layer asks whether the organization is getting better at choosing
work, not only whether any single output looks good.

It reads from:

- the experiment track record;
- GP-230 forecast contracts, outcomes, scores, and decision-use rows;
- GP-245 (a child seam of GP-230) forecaster-calibration rules and the
  ex-post tail/abstention/judge-routing measurements that justify them;
- GP-243 action-impact records;
- GP-244 research-operations intelligence outputs;
- trajectory-mining artifacts;
- catch and anti-pattern ledgers;
- LeanMill event-ledger rows;
- proof/project residuals and summaries;
- decision rows, gates, and transition logs when available.

It should answer operational questions:

- Which forecasts changed an actual decision?
- Which actions produced useful scientific or organizational yield?
- Which failure modes recur despite being known?
- Which projects are stuck because the next test is missing, not because the
  problem is intrinsically blocked?
- Which dashboard signals are informative, and which are activity volume?
- Which primitive should be promoted, demoted, or retired?

The reflexive layer can route attention. It can recommend `run now`, `split`,
`ask another independent agent`, `defer`, or `kill branch`. It does not grant
authority by itself. Authority still runs through roles, mandates, gates,
budgets, and claims.

### Capability catalog and primitive surfacing

A recurring failure of an agent-driven system is **capability amnesia**: an agent
reinvents (or ignores) a primitive that already exists. The reflexive layer counters
this with a single catalog and two surfacing paths:

- **Catalog (single source):** `analytics/public/index/architecture_index.jsonl` —
  every registered gate, operator, reflexive primitive, and reusable analytical/utility
  primitive (id · path · description · `applicability` tags · impact · `category`).
- **Proactive surface:** `primitive_tick_surface.py` scopes the catalog into the RD
  tick brief, so relevant primitives appear *before* work starts. Patterns/anti-patterns
  surface in parallel from the [anti-pattern catalog](anti_pattern_catalog.md) via
  `build_context_primer.py`.
- **Reactive query (semantic):** `research_director/primitive_amnesia.py` answers "what
  exists for *this* task?" over a **gemini-embedding-001 atlas** of the catalog
  (`primitive_atlas_embeddings.json`). Semantic is primary (vocabulary-invariant — "two
  sets overlap" finds `jaccard_distance` with no shared tokens); lexical is a
  parameter-free tiebreaker; a `category` taxonomy makes 500+ primitives navigable.
  `--populate-catalog` registers new primitives; `--build-atlas` re-embeds.

Design honesty: a hand-tuned keyword-alias scheme was tried first and **overfit** (it
surfaced a primitive only for queries phrased in its tuned words); the semantic atlas
replaced it because it generalizes. The retrieval is **measured**, not asserted: on an
18-query held-out benchmark (queries phrased to avoid the alias vocabulary) the
code-aware atlas (gemini-embedding-001, asymmetric `RETRIEVAL_DOCUMENT` /
`CODE_RETRIEVAL_QUERY`, 768-dim) scores **recall@5 = 1.0, MRR = 0.93 vs lexical-only
0.67 / 0.57** (`primitive_amnesia.py --eval`). A noise filter dropped utility/IO helpers
(506 → 315 primitives). Remaining work: usage/impact-weighted ranking (the field exists,
the blend doesn't yet use it) and a larger, less author-written benchmark.

**Canonical embedding engine (2026-06-04).** Embedding atlases proliferated — primitives,
Mathlib, APN, NS, and now seams/specs — each builder copy-pasting the same Gemini embed call,
retry/backoff, content-hash cache, and cosine query. These are now ONE engine,
`src/ztare/common/embeddings.py` (`embed_batch` / `build_atlas` / `query_atlas`), with each
corpus a thin CONSUMER that supplies only its harvest (`[{id, text, …meta}]`) + config
(model / dimensions / output paths) — the engine/consumer invariant (§6n.12) applied to
embeddings. Atlases share the `gemini-embedding-001` space (asymmetric `RETRIEVAL_DOCUMENT`
build / `RETRIEVAL_QUERY` query). To create or maintain an atlas: write a harvest, call
`build_atlas(entries, out_emb, out_manifest, model=…, dimensions=…)` (content-hash cached, so
re-runs only re-embed changed docs); to query, `query_atlas(path, text, k=…)`. New corpora MUST
consume this engine, never re-implement the embed call; the existing per-corpus builders
(`build_apn/mathlib/ns_atlas_embeddings.py`, the primitive atlas) are migrating their local
copies onto it (APN done; the rest incremental, dual-path, regression-checked per §3b). The
**seam/spec atlas** (`scripts/public/mining/build_seam_atlas_embeddings.py` →
`analytics/public/index/seam_atlas_embeddings.json`, queried by
`research_director/seam_semantic.py`) embeds all 336 seams + specs so a capability description
maps SEMANTICALLY to the seam that already owns it — the embedding complement to the structural
seam-interaction map, and the mechanized form of the "find the canonical home before building"
rule (§6n.13).

See:

- [reflexive_engineering.md](reflexive_engineering.md);
- [reflexive_audit_workflow.md](../guides/reflexive_audit_workflow.md);
- `research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md`;
- `research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md`;
- `research_areas/specs/active/apparatus/instrumentation/GP-244_research_operations_intelligence_cockpit_spec.md`.

---

## Human And Agentic Operators

ZTARE should not collapse every use of "operator" into one actor. There are
two operator classes:

- **Human operator / principal.** The accountable person who sets priorities,
  accepts external risk, decides what can be public, supplies taste, and makes
  strategic calls when the substrate is underdetermined.
- **Agentic operator.** A tool-using AI agent that can inspect files, run
  probes, write scripts, edit docs, repair proofs, and leave a dense artifact
  trace. Codex-style and Claude Code-style sessions are agentic operators.

ZTARE does not assume the human is only a gatekeeper. Sometimes the human is
the worker, the source of taste, the experimental operator, or the only actor
who can choose among live research bets. It also does not assume an agentic
operator is merely a chat responder. When a live substrate is underspecified,
an agentic operator may be the correct unit of agency: inspect the filesystem,
probe the runtime, repair the source packet, and leave receipts.

The authority boundary remains different. Agentic operators can execute,
recommend, and close bounded tasks within mandate. The human operator owns
public-claim accountability, risk acceptance, strategic direction, and taste
unless a specific role contract delegates a narrower decision.

The architecture supports four human roles:

| Human role | System support |
|---|---|
| Principal | preferences, gates, objectives, kill/split/defer authority |
| Collaborator | operator console, project notes, human-agent handoff artifacts |
| Source of non-digitized work | explicit receipts, summaries, evidence promotion, action-impact rows |
| Bottleneck to route around | closure pressure, forecasts, independent-agent review, unattended in-mandate work |

The goal is not to remove the human from research. The goal is to stop making
the human the only memory, only router, and only closure mechanism.

---

## Canonical State Vs. Projections

| Surface | Role | Canonical? |
|---|---|---|
| `projects/` | project work and artifacts | yes for project artifacts |
| `research_areas/` | seams, specs, synthesis, experiment record | yes for research governance |
| `org/` | ZTARE tenant roles, tasks, channels, objectives | yes for local org state |
| `ztare_workspace/gates/` | pending/resolved decisions | yes |
| `ztare_workspace/transitions.jsonl` | transition events | yes |
| LeanMill SQLite queue + JSONL event ledger | proof-attempt bus | yes |
| `/srv/ztare_official_store/official/` (VPS) | GP-241 daemon-owned F-row + stamped-transition ledger | yes; the in-repo `research_areas/EXPERIMENT_TRACK_RECORD.md` is a generated export of this |
| `analytics/public/` | public analytics outputs | derived |
| Orbit | governance UI | projection |
| notification provider | push/ack rail | projection |
| dashboard HTML | human-readable intelligence surface | projection |
| agent chat transcript | useful context | not canonical unless summarized into artifacts |

This distinction is the guardrail against accidental architecture drift.

---

## Public Repo Boundary

ZTARE is a public research repository plus local overlays. Public docs should
describe the reusable architecture without depending on ignored paths,
private tenant repos, or local credentials.

Current boundary:

- Public ZTARE contains the validator, public docs, public papers, public
  scripts, public analytics, and source-visible org primitives.
- `org/` is a ZTARE tenant overlay, not the canonical generic kernel.
- Tenant notification providers are optional. Filesystem gates and transition
  logs are the public default.
- The generic organizational kernel belongs in
  [cognitive-firm](https://github.com/sparckix/cognitive-firm).

If a doc cannot be understood without private context, it should either be
rewritten as a public abstraction or moved out of the public entry path.

---

## What To Use When

| Need | Use |
|---|---|
| Test a bounded claim against evidence | in-loop validator |
| Prove or formalize a theorem fragment | project proof workflow / Lean tooling |
| Schedule and run many Lean proof attempts under a stable contract | LeanMill (`src/ztare/leanmill/`) — durable SQLite queue + JSONL event ledger |
| Decide which scientific branch deserves attention | GP-230 forecasts + RD/principal review |
| Learn whether an action changed outcomes | GP-243 action-impact rows |
| Inspect operating health across projects | GP-244 intelligence surface |
| Run persistent role-bound work | org runtime / role daemon |
| Work interactively with a human and agent | operator console + project artifacts |
| Extract reusable failure patterns | reflexive audit workflow + anti-pattern catalog |
| Track specification-gaming vectors from incident to runtime gate | [gaming behavior catalog map](gaming_behavior_catalog_map.md) |
| Run bug-bounty / honeypot search for missed autoresearch failures | [make targets](../reference/make_targets.md) + [gaming behavior catalog map](gaming_behavior_catalog_map.md) |

---

## Failure Modes The Architecture Is Built To Catch

- **Self-certification**: the same model family proposes and validates its own
  success.
- **Specification-gaming recurrence**: a known gaming vector is cataloged but
  never reaches a runtime gate or promotion receipt. See the
  [gaming behavior catalog map](gaming_behavior_catalog_map.md) for the
  incident -> registry -> promotion -> enforcement lifecycle.
- **Narrative inflation**: a plausible story outruns deterministic receipts.
- **Metric theatre**: tasks close while world-measured outcomes do not move.
- **Chat-state loss**: important decisions remain only in conversation.
- **Dashboard authority creep**: a projection starts acting like a control
  plane.
- **Notification-state confusion**: a push rail becomes treated as source of
  truth.
- **Primitive cargo culting**: patterns are surfaced but do not improve
  decisions or outcomes.
- **Local-over-global optimization**: a micro loop improves a local score while
  damaging scientific yield or external validity.

The architecture does not claim to eliminate these failures. It makes them
observable enough to be fought.

---

## Current Maturity

| Area | Status |
|---|---|
| In-loop validator | mature research instrument, still substrate-dependent |
| Evidence/rubric workflows | usable, public docs available |
| Org runtime | working prototype, dogfooded locally |
| Notification abstraction | filesystem default, tenant providers optional |
| Forecast market | mechanized; GP-245 child seam adds calibration rules |
| LeanMill substrate engine | dogfooded on GP-225; queue/policy/contracts and common helpers are kernel-backed, while LeanMill-specific orchestration remains in `scripts/public/control/`; current focus is strict C-supply growth, target-safe benchmarking, and family/source breadth |
| GP-241 commit-membrane daemon | live on VPS as sole writer of the official store |
| Action intelligence | early but wired into public smoke checks |
| Research intelligence dashboard | active private instrumentation track |
| Multi-tenant enterprise control plane | design direction, not the public default |

The honest state is that ZTARE is strongest as a research operating system for
one serious operator and a small set of agents. The direction of travel is a
cleaner separation between the public validator/research stack, the generic
cognitive-firm kernel, and tenant-specific overlays.

---

## Documentation Map

This page is the overview. Read next by intent:

| If you want to… | Read |
|---|---|
| See every module by function | [system_position_and_module_map.md](system_position_and_module_map.md) |
| Understand the LeanMill proof engine | [leanmill_architecture.md](leanmill_architecture.md) |
| Understand the reflexive/learning layer | [reflexive_engineering.md](reflexive_engineering.md) · [reflexive_mining_methodology.md](reflexive_mining_methodology.md) |
| Understand the validator's theory | [cognitive_gym.md](cognitive_gym.md) · [rubric_specification.md](rubric_specification.md) · [harness_specification.md](harness_specification.md) |
| Understand the epistemic stance | [epistemic_principles.md](epistemic_principles.md) · [goodhart_at_every_layer.md](goodhart_at_every_layer.md) |
| Know what already exists before building | the [capability catalog](#capability-catalog-and-primitive-surfacing) + [anti_pattern_catalog.md](anti_pattern_catalog.md) + [capabilities.md](capabilities.md) |
| See the org/runtime model | [organizational_primitives.md](organizational_primitives.md) · [ztare_research_company_architecture.md](ztare_research_company_architecture.md) |
| Check evidence behind claims | [evidence atlas](../evidence_atlas/README.md) |
| Look up a term | [glossary.md](glossary.md) |

Seams/specs (governance of in-flight work) live under `research_areas/seams/` and
`research_areas/specs/active/`; the canonical experiment record is the GP-241
daemon-owned store, exported to `research_areas/EXPERIMENT_TRACK_RECORD.md`.

When this overview and a deeper doc disagree, the deeper doc wins for its subsystem;
fix the drift here so the overview stays trustworthy.
