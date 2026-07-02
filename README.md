# ZTARE

ZTARE helps you decide what you can stand behind.

Bring a project folder, report, source pack, model output, proof note, dataset,
or repo. ZTARE helps you answer the questions that matter before you trust the
work:

- what is the thesis?
- which files support it?
- what is missing or stale?
- what can run next without wasting model spend?
- what changed after review?
- what should be tested next?

ZTARE is the system around that loop. The Project Workbench is the local app
for it. Open a project, inspect the thesis, prepare sources and evidence, check
whether it is ready to run, save review notes, and save a project file you can
inspect later. The CLI exposes the same state for scripts and review packs.

The failure ZTARE targets is a plausible answer with no clean audit trail. That
gets worse when one model both produces the work and grades it. ZTARE keeps
drafting, checking, evidence, report readiness, and review as separate steps. A
model can draft or search; the claim only counts as far as the sources and
checks support it.

Run one command first:

```bash
make hello
```

That command is the smallest decision test in the repo. A plausible overclaim
is narrowed, missing evidence is named, a malformed project-brief file is
blocked before model spend, and the next check is shown. It is offline and
writes no persistent runtime state.

After it runs, you should see the public claim-check path work end to end:
overclaim demotion, project-brief validation, evidence warnings, and a concrete
next step. It does not show hard-research success, external validation, or
broad domain generalization. See
[What ZTARE Does Not Claim](#what-ztare-does-not-claim).

The useful mental model is:

```text
project -> thesis -> local sources -> evidence state -> readiness check / run
-> verdict, support issue, saved review, or next test
```

Code has compilers; reasoning needs similar discipline. The long-term aim is to
turn important thinking into objects you can check, reject, narrow, log,
review, and hand to the next person or agent. The current v1 path is
deliberately focused: local project review over inspectable sources and files.

Then inspect the failure catalog:
[9 ways LLMs game their own evaluations, with code examples and catch
patterns](docs/gaming_behavior_catalog.md#start-here-9-ways-llms-game-their-own-evaluations).

## First value in 5 minutes

For a fresh clone, install and run the offline value check:

```bash
git clone https://github.com/sparckix/ztare && cd ztare
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && pip install -e .
make hello
```

For the full offline public review path, run `make first-run`. It chains the
value demo, gaming catalog audit, benchmark evidence checks, the frozen
evaluator check, public claim-boundary audit, terminology audit, public smoke,
entry-path checks, and docs checks.

To inspect the catalog hook directly, run `make gaming-catalog-audit`. It checks
that the public catalog, live vector registry, promotion evidence, hardening
map, and current executable fixture anchors agree without turning later
registry rows into paper-taxonomy claims.

## Use it when

Use ZTARE when you need to know what you can stand behind after checking the
sources, saved files, and failure modes.

The first users are not one profession. The common pattern is source-backed
work where the answer matters: investment diligence, legal review, scientific
research, product and strategy work, policy analysis, incident review, formal
proof work, and AI-assisted reports that need inspection before they count. See
the [ZTARE use-case guide](docs/guides/ztare_use_cases.md) for concrete
profession-level examples.

Good fits:

- reviewing a claim against local sources, notes, papers, logs, or data
- checking whether a report is backed by current evidence
- testing an evaluator, model workflow, or proof-search workflow for self-grading
  and overclaiming
- preserving failed branches, support issues, and next falsifiers so a later run does
  not start from scratch.

Bad fits:

- a plug-and-play agent framework
- a leaderboard optimizer
- a polished hosted product
- proof of autonomous hard-problem success
- a replacement for domain review.

## Run it on your own work

The `projects/` directory here is a set of illustrative demos, my own runs.
They exist to show the path and give you a shape to copy. They are not the
product, and you do not have to use them.

ZTARE is built to run on whatever you need to stand behind, a compliance rule,
a research claim, a dataset, a repo, a model report. Create your own project
and point it at your own sources:

```bash
ztare project walkthrough     # guided project brief for a new claim and its sources
ztare project new --help      # scaffold a numeric or data project
```

Each project you create gets its own project brief, evidence binding, trace,
and review files under `projects/<your-project>/`. The CLI still names the
brief file `intake` in commands and JSON paths. Copy a demo's structure, swap
in your sources, and run.

## Choose the path

Choose what you are trying to inspect before choosing a model. Most bad runs
start too late in the process: a model is launched before the sources, claim,
evidence, and expected output are clear.

If you are unsure, start with **Project brief**. It is the lowest-cost way to
find missing source files, vague claims, unsupported evidence, or a task that
belongs outside the validation loop for now.

| Route | Use it when | Start here |
|---|---|---|
| **Project brief** | You have a project, source, paper, dataset, repo, or claim that is not yet ready for a run | `ztare project walkthrough` |
| **In-loop autoresearch** | A bounded claim, stable evaluator, rubric, and saved output are ready | `ztare autoresearch trace --brief`, then its `recommended first command` |
| **Out-of-loop research work** | The work is source gathering, proof decomposition, reproduction setup, synthesis, or one-off agent work | `ztare autoresearch route` plus guidance records |
| **Proof work** | The target is Lean formalization, proof search, or proof-credit governance | `ztare leanmill ...` and [leanmill_architecture.md](docs/concepts/leanmill_architecture.md) |
| **Reflexive/ops review** | You want to know whether the system's own routing, forecasts, catches, or instruments are improving | `make first-run`, `ztare autoresearch trace`, and the evidence atlas |

For a local web view over your projects, use the Project Workbench — a React app
backed by a local API. From a fresh clone, one command starts both:

```bash
make forensic-workbench-live
```

This launches the API (`http://127.0.0.1:8765`) and the app
(`http://127.0.0.1:5174`) together, installing the app's web dependencies on the
first run. Open the app URL and pick a project. Requires Python 3 (with the repo
dependencies installed) and Node 18+ / npm.

With the server running, the app lists projects, edits project-brief/source
files, checks run readiness, saves reviews and next steps, saves project files,
and refreshes a project from the repo — without giving the browser raw
filesystem access. It also critiques a project's scoring rubric before you spend
a run on it, answers plain-language questions against the research map (e.g.
"what could falsify the thesis?"), stress-tests a single claim to show how it
could break, and turns a source document into a bounded starting claim. From a
project's **Verdict** you can also export the verified
research graph to an **Obsidian vault** (one linked note per claim, evidence, and
falsifier, weak spots marked) to write from.

Prefer a static offline view? `make forensic-workbench-data
WORKBENCH_PROJECT=<slug>` writes a snapshot the app reads without the server; you
can still download the review JSON and apply it with
`ztare forensic-workbench apply-review`.

The validation engine is appropriate only after the in-loop prerequisites are
ready. Project-brief work and out-of-loop work create or repair the inputs the
loop later consumes. They are not lesser versions of the loop. The commands
below are reference examples. You do not need to read them all before running
`make hello` or `ztare project walkthrough`.

| Need | Command |
|---|---|
| Walk through project-brief setup with prep/trace/in-loop phases | `ztare project walkthrough` |
| Inspect a concrete organizational-diagnosis demo | `ztare project walkthrough --ops-demo` |
| Initialize source-ingest files for a project | `ztare project source-init --project <project> --rubric <rubric>` |
| Check raw source typing before evidence compilation | `ztare project source-check --project <project> --json` |
| Generate a numeric/data project | `ztare project new --help` |
| Prepare or seal that project before the loop | `ztare project prepare --project <project> --rubric <rubric>` · `ztare project seal --project <project> --rubric <rubric>` |
| Create and validate the project-brief JSON | `ztare project intake create ...` · `ztare project intake validate --path <intake.json>` (`--source-preflight` requires local source files) |
| Check the brief's missing-ref falsifier | `ztare project intake falsify --path <intake.json> --remove-ref 'evidence_refs[1]'` |
| Place a source-ready brief in the intake ledger | `ztare project intake enqueue --path <intake.json>` |
| Track missing brief inputs when needed | `ztare project prep-ledger add --task "<prep task>" --kind minimal_reproduction --project <project> --rubric <rubric>` |
| Route and optionally record missing inputs | `ztare autoresearch route --task "<task>" --record-decision-id <id>` |
| Ask whether a task belongs in autoresearch | `ztare autoresearch route --task "<task>" --project <project> --rubric <rubric>` |
| Inspect project-brief, trace, projection, and local health state | `ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --brief` (`--json` for scripts) |
| Check launch readiness without model calls | `ztare autoresearch run --project <project> --rubric <rubric> --intake <intake.json> --preflight-only` |
| Run the loop | `ztare autoresearch run --project <project> --rubric <rubric> --intake <intake.json>` (`make experiment-loop ...` is the lower-level entry) |
| Use subscription workers for wired call sites | `ztare autoresearch run --project <project> --rubric <rubric> --intake <intake.json> --agent-mutator --agent-judge --agent-committee --agent-inverter --agent-runtime codex` |
| Recommend next project/workbench inputs | `ztare autoresearch workbench-recommend --prompt-only` |
| Compare API and subscription dispatch fixtures | `ztare autoresearch dispatch-parity --json` |
| Check actual API vs subscription run outcomes | `ztare autoresearch subscription-outcomes --json` |
| Check pending advisory eigenquestions | `ztare eigenquestion status --project <project>` |
| Record why agent work stayed outside the loop | `ztare action-intel record-agentic-route --route-json <route.json> --decision-id <id>` |
| Audit stagnant run traces | `ztare autoresearch hillclimb-audit --project <project>` |
| Check first-page autoresearch kernel health | `ztare autoresearch health --project <project> --json` |
| Build the RD operations report | `ztare autoresearch operations-intelligence --out ztare_intel.json --markdown ztare_intel.md` |
| Check primitive catalog and atlas health | `ztare primitive health` |
| Validate dormant in-loop fixtures | `make inloop-fixture-validate` |
| Check dispatch wrapper coverage | `make autoresearch-dispatch-validate` |

## What is actually here

Five tracks compose into the current local review system:

| Track | Maturity | What it does |
|---|---:|---|
| **Validation engine and trusted checks** | stable / evolving | The runnable in-loop validator plus the checks around it: proposal, fit/compression, adversarial review, deterministic checks, projection, and run history. Home of the published [LLM gaming behavior catalog](docs/gaming_behavior_catalog.md). |
| **Project brief and evidence readiness** | release path | Local files, source typing, evidence binding, evidence gaps, claim support, trace readiness, and run readiness before model spend. |
| **Report readiness** | release path | Stops stale or unsupported reports from being promoted. |
| **LeanMill** | active / current frontier | Governed Lean proof search. A deeper evidence track; come to it after the v1 path. |
| **Reflexive layer** | advisory | Mining over forecasts, actions, catches, experiment records, and in-loop/out-of-loop split. It shows stale ledgers, dead instruments, and underused capabilities. |

Terminology in this repo is layered: **workbench** means the user-facing
product, **kernel** means the trusted checks and contracts, **engine** means a
runnable subsystem, and **apparatus** means a historical experiment setup. The
[glossary](docs/concepts/glossary.md#core-concepts) is the reference when docs
use those words.

Typical flow:

```text
local question -> route choice -> project brief / evidence / trace
-> readiness check or project run -> saved review
-> verdict, demotion, support issue, or next check
```

This is a local research workbench currently hardened around single-project
review. Public forkability, hosted collaboration, and multi-user hardening are
roadmap work, still open.

## Design invariants

- **The proposer does not grade itself.** Generation, adversarial review,
  scoring, and deterministic gates are separate actors.
- **A compile is necessary but insufficient.** A proof or program can compile
  while laundering the target through a hypothesis, citation, vacuous premise,
  or hidden oracle. Governance checks those cases separately.
- **Failures are first-class evidence.** Nulls, refusals, residuals, failed
  branches, and instrument failures are recorded because they change the next
  experiment.
- **Worker transport is metadata.** API calls, subscription
  CLIs, and local workers can all be used. The typed contract, saved file, and
  check decide whether the result counts.
- **Chat is not the system of record.** Durable files live under
  `projects/`, `research_areas/`, `org/`, `papers/`, and generated analytics.

## Evidence first

Start from the evidence:

- [Live analytics dashboard](https://sparckix.github.io/ztare/): a self-contained view of volume, taste, and compounding metrics, built through a leak-gated pipeline.
- [Evidence atlas](docs/evidence_atlas/README.md): a crosswalk from public claims to summaries, experiments, runnable checks, and caveats.
- [Public claim register](docs/public_claim_register.md): claim by claim, with scope, evidence, non-claims, and next falsifiers.
- [Executable review pack](docs/evidence_atlas/executable_review_pack.md): commands a reviewer can run.
- [LLM gaming behavior catalog](docs/gaming_behavior_catalog.md) and [gaming-catalog review file](docs/evidence_atlas/packets/gaming_catalog.md): self-certifying code strategies plus mined cross-domain vectors, tied to registry/gate evidence and executable anchors by `make gaming-catalog-audit`.
- [`research_areas/EXPERIMENT_TRACK_RECORD.md`](research_areas/EXPERIMENT_TRACK_RECORD.md) and [`research_areas/insights_ledger.md`](research_areas/insights_ledger.md): the durable experiment and finding record.

Scale is tracked as an internal health signal only: file
volume, in-loop versus out-of-loop work, ratified catches, and insight-density
changes are mined by the reflexive dashboard.

## How to judge the current release

Do not judge ZTARE by repo size. Judge it by whether you can inspect the path
from a source file to a claim boundary.

Start with five questions:

1. Did a command catch a weak or unsupported claim?
2. Can you find the source or saved file behind the verdict?
3. Can you see what the result does not prove?
4. Can you see the next check that would change the answer?
5. Can you reproduce the path without trusting a chat transcript?

Run `make hello`, then `make first-run`, and watch whether the path holds:
every verdict points back to a source file, a check you can re-run, and an
explicit list of what it does not prove. External review is still sparse, so
read each claim at the evidence level its own files support.

## Command cheat sheet

After the install block above, these are the public commands worth trying first:

```bash
make help
make first-run     # full offline public first-run path
make hello         # offline: project-brief falsifier + overclaim demotion
make demo          # offline, no live model calls
make smoke-public  # offline
ztare --help       # human-facing CLI: project / autoresearch / action-intel / forecast / bundle / other commands
```

Add keys only for an LLM-backed loop. Supported API-provider keys are
`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`,
`KIMI_API_KEY` or `MOONSHOT_API_KEY`, and `XAI_API_KEY` or `GROK_API_KEY`.
Subscription-CLI dispatch is also supported for wired call sites. See
[`docs/reference/model_aliases.md`](docs/reference/model_aliases.md) before
choosing a mutator/judge pair. After project-brief validation and trace readiness, run
the guarded CLI entry. It blocks before the first model call unless the project brief,
source/evidence inputs, and launcher readiness check agree:

```bash
ztare autoresearch trace --project <project> --rubric <rubric> --intake <project>_intake.json --json
ztare autoresearch run --project <project> --rubric <rubric> --intake <project>_intake.json --preflight-only
ztare autoresearch run --project <project> --rubric <rubric> \
    --intake <project>_intake.json --iters 10 \
    --mutator "$ZTARE_WORKBENCH_RUN_MUTATOR_MODEL" \
    --judge "$ZTARE_WORKBENCH_RUN_JUDGE_MODEL" \
    --inverter "$ZTARE_WORKBENCH_RUN_INVERTER_MODEL"
```

For serious runs, choose two model families deliberately and set them through
the workbench Settings page or environment variables. Use `CROSS_FAMILY=1`
when the run should fail before any model call if the pair shares a provider
family.

Before using a persistent agent outside the loop, ask whether the task belongs
in autoresearch. If the task needs project files or data first, create or
prepare them before run readiness. Before trusting a run, inspect the trace:

```bash
ztare project source-init --project <project> --rubric <rubric>
ztare project source-check --project <project> --json
ztare project walkthrough --project <project> --rubric <rubric> --task "<bounded task>" --bounded-claim "<bounded claim>" --source-ref "<source-file>" --evidence-ref "<evidence-file>" --non-claim "<non-claim>" --next-falsifier "<falsifier>" --intake-out <project>_intake.json --json
ztare project new --help
ztare project prepare --project <project> --rubric <rubric>
ztare project intake create --path <project>_intake.json --project <project> --rubric <rubric> --task "<bounded task>" --bounded-claim "<bounded claim>" --source-ref "<source-file>" --evidence-ref "<evidence-file>" --non-claim "<non-claim>" --next-falsifier "<falsifier>" --expected-command "ztare autoresearch route --task '<bounded task>' --project <project> --rubric <rubric>"
ztare project intake validate --path <project>_intake.json
ztare project intake validate --path <project>_intake.json --source-preflight
ztare project intake enqueue --path <project>_intake.json
ztare autoresearch route --task "<task>" --project <project> --rubric <rubric>
ztare autoresearch trace --project <project> --rubric <rubric> --intake <project>_intake.json --json
ztare autoresearch health --project <project> --rubric <rubric> --json
```

The public path is deliberately short:

```text
project brief -> autoresearch trace -> readiness check -> project run -> report readiness / project file
```

`autoresearch trace` is the read-before-run view. Use
`plan_preview.recommended_first_command`: when run readiness is blocked, it is
the first repair command; before a fresh run-readiness check, it is the
model-free readiness command; after the current project brief and run-readiness
bytes are admitted, it advances to the project run. Re-run the readiness check
when the project brief, source/evidence state, or launch contract changes.

`project intake enqueue` is stricter than shape validation: it requires the
local project source files to pass the offline source check. If source files,
source typing, or evidence files are still missing, record that work in the
prep ledger first. In user-facing prose, call the input a project brief; in
commands, keep using the `intake` flag and subcommand.

`source-init` creates `projects/<project>/raw/`,
`projects/<project>/workspace/`, and `raw/source_type_map.json`. It does not
write `evidence.txt` or start a run. Raw source documents must be typed with
`source_type` frontmatter or the source-type map. `make evidence-prepare`
runs `source-check` before the source-to-evidence compiler path. Run
`source-check` standalone when you want the offline readiness report without a
model-backed compile.

Use `--intake` for the project-brief JSON. That is different from a review file
or evidence bundle. Use `ztare project prep-ledger ...` only when the brief is
blocked on concrete prep work such as a missing source, evidence file,
reproduction step, or cost estimate. It is an append-only prep ledger for
tracking that blocked work.
For ready and malformed project-bundle examples, see
[examples/project_packets/](examples/project_packets/).

Walkthrough + CLI tour: [docs/guides/quickstart.md](docs/guides/quickstart.md) · [docs/guides/cli.md](docs/guides/cli.md). LeanMill architecture: [docs/concepts/leanmill_architecture.md](docs/concepts/leanmill_architecture.md).

## Go deeper

| If you want to… | Start at |
|---|---|
| See the current capability inventory in two minutes | [docs/concepts/capabilities.md](docs/concepts/capabilities.md) |
| Review the evidence graph before trusting anything | [docs/evidence_atlas/README.md](docs/evidence_atlas/README.md) |
| Understand the governed proof-search workflow | [docs/concepts/leanmill_architecture.md](docs/concepts/leanmill_architecture.md) |
| Understand the validator architecture | [docs/concepts/architecture.md](docs/concepts/architecture.md) |
| Understand proof execution + governance gate + residual compiler | [docs/concepts/closure_claim_governance.md](docs/concepts/closure_claim_governance.md) |
| See why claim review runs as a constraint stack, and what a chat loop misses | [docs/concepts/cognitive_gym.md](docs/concepts/cognitive_gym.md) |
| Read the "why" behind the architecture (the three legs) | [research_areas/philosophy/three_legs_of_ztare.md](research_areas/philosophy/three_legs_of_ztare.md) |
| See how a new primitive becomes discoverable before you rebuild it | [docs/concepts/primitive_surfacing.md](docs/concepts/primitive_surfacing.md) |
| Read the papers | [papers/README.md](papers/README.md) |
| Work inside the repo as an agent | [AGENTS.md](AGENTS.md) (the repo constitution) |

### What can transfer

If you want to reuse the ideas without adopting the whole repo, start with the
pieces that solve ordinary AI-system problems:

- [Agentic engineering patterns](docs/concepts/agentic_engineering_patterns.md):
  replay tests, readiness checks, provenance fields, fail-closed routes, and
  result-bound success claims.
- [Reflexive primitives](docs/concepts/reflexive_engineering.md): ways to turn
  a repeated failure into a check, queue item, route, or record that a later run
  must consume.
- [Epistemic principles](docs/concepts/epistemic_principles.md): the rule that
  a proposer does not grade itself, plus failure catalogs and evidence levels.
- Research traces: attempts, critiques, source-readiness labels, demotions,
  nulls, and next falsifiers that can become training or evaluation material.

## Repository map

| Path | Purpose |
|---|---|
| `src/ztare/` | Implementation: validator, fit/MDL/BIC primitives, gates, the leanmill solver + governance kernel, orchestration. |
| `projects/` | Illustrative demo projects (create your own alongside them): evidence, workspaces, validator files, scientific sandboxes, and proof work. |
| `docs/` | Architecture, guides, concepts, evidence atlas. |
| `papers/` | Public manuscript sources + replication packages. |
| `ztare_proofs/` | Lean proof sources. |
| `research_areas/` | Experiment track record, seams, specs, debates, research logs. |
| `org/` | Roles, mandates, tasks, channels, runtime state (cognitive-firm tenant overlay). |

Public by default: the workbench source, validators, governance checks, Lean modules, public docs, and papers.
Local/gitignored: active strategy, sealed pre-registrations, credentials, and in-flight tactics. The
instrument is inspectable, while live experiments keep sealed envelopes so later results stay
interpretable.

## Papers

The papers explain why the workbench exists. The repo is the stronger evidence:
commands, source files, review files, demotions, and checks.

- [Specification Gaming in LLM-Generated Code](papers/cognitive-camouflage/draft.md):
  nine benchmarked strategies a model uses to self-certify code, caught by adversarial execution · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960)
- [Hardening an Adversarial Evaluator with Mined Constraints and Contract-Gated Recursive Improvement](papers/governed-evaluator-hardening/draft.md):
  mined failure constraints plus deterministic promotion contracts (merges the earlier precedent-memory and contract-governance papers) · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598)
- [The Cognitive Firm](papers/cognitive-firm/draft.md):
  a multidivisional-form architecture that separates role and authority for recursive AI governance · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019)
- [The Limits of Audit for Self-Evaluating AI](papers/audit-limits/draft.md):
  why authority and correlated error sit beyond what a non-gameable check can settle
- [When a Consciousness Verdict Cannot Be Earned](papers/consciousness-admissibility/draft.md):
  a descent-theoretic admissibility criterion for when a property cannot be recovered from the evidence · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6702939)

In revision: [Epistemic Verification](papers/epistemic-verification/draft.md)
(how professional judgment decomposes into auditable operations) and
[Epistemic Generation](papers/epistemic-generation/draft.md) (a corpus study of
research-move vocabularies).

Read science case studies through their experiment records and public claim
boundaries, which bound what they prove.

## What ZTARE does not claim

ZTARE improves claim discipline. It does not guarantee truth.

Do not read the repo as claiming that:

- a high score proves a discovery
- a compile proves the statement was the right one
- a calibration recovery is new science
- one cold model answer is a controlled baseline unless model, date, and prompt
  are recorded
- the current gates catch every failure mode
- "works across domains" means no domain-specific evidence work remains.

If a result matters, it needs saved files, checks, review records, non-claims,
and a next falsifier. Named personas in synthetic review panels are shorthand
for reasoning styles loosely inspired by public work. They are not the named
individuals' views, and no affiliation is implied
(`src/ztare/personas/registry.py`).

## Why it is built this way

The short version is: compress the claim, invert the failure, and design the
environment around the model. The longer version lives in
[The Three Legs of ZTARE](research_areas/philosophy/three_legs_of_ztare.md),
the [philosophy folder](research_areas/philosophy/), and
[epistemic_principles.md](docs/concepts/epistemic_principles.md).

The design draws on a few established lines of thought:

- **Falsification and research programmes.** Popper (cheap refutation over persuasive confirmation);
  Lakatos (judge a programme by whether it predicts novel facts, not by how well it protects a core);
  Munger's inversion and checklists (name what would make success uninterpretable before celebrating it).
- **Measurement under optimization pressure.** Goodhart's law (a metric under pressure stops measuring
  what it measured); agency problems under delegated authority; Holmström's informativeness principle (score on the
  signal that actually carries outcome information). This is why proposing is separated from grading.
- **Organization and management.** Chandler's managerial capitalism and the M-form (the cognitive-firm
  runtime is role / mandate / gate separation); Williamson's transaction-cost economics (where to put a
  boundary); Ostrom on governing a shared resource; Taylor's scientific management; Simon's bounded
  rationality and near-decomposability.
- **Systems and cybernetics.** Ashby's requisite variety (a controller needs at least as much variety as
  what it regulates); Hofstadter's strange loops (*Gödel, Escher, Bach*) for the reflexive structure that
  reasons about its own reasoning.
- **The scaling stance.** Taken in deliberate tension with Sutton's "bitter lesson": ZTARE grants that
  models keep scaling (you swap the leaf), but bets that an individual researcher's near-term leverage is
  the environment around a frozen model, not a bigger model. Karpathy's LLM-wiki pattern seeds the
  source-memory layer upstream of the validator.

These are influences, not endorsements; none of the authors are affiliated with the project.

## License & citation

MIT. The governance/orchestration code (`org/`, `supervisor/`, `orbit/`, `deploy/`, and
`src/ztare/{orchestration,supervisor,sessions,signals,notifications}/`) is a tenant-overlay integration of
the upstream [cognitive-firm](https://github.com/sparckix/cognitive-firm) kernel. Gitignored files are not
part of the public grant until promoted. Map: [LICENSES.md](LICENSES.md) · [LICENSE](LICENSE) ·
[NOTICE.md](NOTICE.md). Cite the specific paper or file you use.
The repository-level `CITATION.cff` exists for tooling that requires one citation target.
