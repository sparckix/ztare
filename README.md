# ZTARE

ZTARE helps you decide what you can safely say from the sources in front of
you.

Give it local files, code, proofs, data, logs, model outputs, reports, or review
notes. It turns them into a bounded claim, names the evidence, blocks missing
inputs, records what the claim does not cover, and shows the next check that
would change the answer.

The risk is a plausible answer with friendly evidence and no clean way to audit
how it got there. ZTARE splits proposal, checking, evidence, report export, and
review into separate steps. A model can help draft or search. The claim only
counts as far as the sources and checks support it.

Run one command first:

```bash
make hello
```

That command is the smallest decision test in the repo. A plausible overclaim
is narrowed, missing evidence is named, a malformed intake file is blocked
before model spend, and the next check is surfaced. It is offline and writes no
persistent runtime state.

After it runs, you should see the public claim-check path work end to end:
overclaim demotion, intake validation, evidence warnings, and a concrete next
step. It does not show hard-research success, external validation, or broad
domain generalization. See
[What ZTARE Does Not Claim](#what-ztare-does-not-claim).

The useful mental model is:

```text
bounded claim -> local sources -> evidence readiness -> trace/preflight
-> verdict, demotion, blocker, or next falsifier
```

The long-term idea is simple: code has compilers; reasoning needs similar
discipline. Informal proposals should become objects you can check, reject,
narrow, log, and review. The current v0.4 slice is smaller: local claim review
over inspectable sources and artifacts.

Then inspect the concrete failure catalog:
[9 ways LLMs game their own evaluations, with code examples and catch
patterns](docs/gaming_behavior_catalog.md#start-here-9-ways-llms-game-their-own-evaluations).

## First Value In 5 Minutes

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

## Use It When

Use ZTARE when you need to know what you can stand behind after checking the
sources, artifacts, and failure modes.

Good fits:

- reviewing a claim against local sources, notes, papers, logs, or data;
- checking whether a report is backed by current evidence;
- testing an evaluator, model workflow, or proof-search surface for self-grading
  and overclaiming;
- preserving failed branches, blockers, and next falsifiers so a later run does
  not start from scratch.

Bad fits:

- a plug-and-play agent framework;
- a leaderboard optimizer;
- a polished hosted product;
- proof of autonomous hard-problem success;
- a replacement for domain review.

## Choose The Path

Choose the route before choosing a model. Most mistakes come from launching the
loop before the project surface is ready.

| Route | Use it when | First surface |
|---|---|---|
| **Project intake** | You have a project, source, paper, dataset, repo, or claim that is not yet ready for a loop | `ztare project walkthrough` |
| **In-loop autoresearch** | A bounded claim, stable evaluator/gate, rubric, and artifact output are ready | `ztare autoresearch trace --brief`, then its `recommended first command` |
| **Out-of-loop research operations** | The work is source gathering, proof decomposition, reproduction setup, synthesis, or one-off agent work | `ztare autoresearch route` plus action-intelligence rows |
| **Proof work** | The target is Lean formalization, proof search, or proof-credit governance | `ztare leanmill ...` and [leanmill_architecture.md](docs/concepts/leanmill_architecture.md) |
| **Reflexive/ops review** | You want to know whether the system's own routing, forecasts, catches, or instruments are improving | `make first-run`, `ztare autoresearch trace`, and the evidence atlas |

For a local web view over one project, use the forensic workbench:

```bash
make forensic-workbench-data WORKBENCH_PROJECT=ops_root_cause_diagnosis_demo
make forensic-workbench-api
make forensic-workbench-dev
```

The React app reads a generated snapshot in static mode. With the local API
running, it can list available projects and refresh the selected case from the
repo without giving the browser raw filesystem access. Review decisions can be
applied through the local API, which writes the same receipt shape as the CLI.
Static mode still lets you download or copy the review JSON and apply it with
`ztare forensic-workbench apply-review`.

The validation engine is appropriate only after the four prerequisites in the
second row are ready. Project intake and out-of-loop work create or repair the
surfaces the loop later consumes; they are not lesser versions of the loop.
That boundary is inspectable through these commands:

| Need | Command |
|---|---|
| Walk through project-intake setup with prep/trace/in-loop phases | `ztare project walkthrough` |
| Inspect a concrete organizational-diagnosis demo | `ztare project walkthrough --ops-demo` |
| Initialize source-ingest files for a project | `ztare project source-init --project <project> --rubric <rubric>` |
| Check raw source typing before evidence compilation | `ztare project source-check --project <project> --json` |
| Generate a numeric/data project | `ztare project new --help` |
| Prepare or seal that project before the loop | `ztare project prepare --project <project> --rubric <rubric>` · `ztare project seal --project <project> --rubric <rubric>` |
| Create and validate a project-intake file | `ztare project intake create ...` · `ztare project intake validate --path <intake.json>` (`--source-preflight` requires local source files) |
| Check an intake file's missing-ref falsifier | `ztare project intake falsify --path <intake.json> --remove-ref 'evidence_refs[1]'` |
| Place source-ready intake in the intake ledger | `ztare project intake enqueue --path <intake.json>` |
| Track missing intake inputs when needed | `ztare project prep-ledger add --task "<prep task>" --kind minimal_reproduction --project <project> --rubric <rubric>` |
| Route and optionally record missing inputs | `ztare autoresearch route --task "<task>" --record-decision-id <id>` |
| Ask whether a task belongs in autoresearch | `ztare autoresearch route --task "<task>" --project <project> --rubric <rubric>` |
| Inspect intake/trace/projection/local health state | `ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --brief` (`--json` for scripts) |
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

## What Is Actually Here

Five tracks compose into the current claim-governance workbench:

| Track | Maturity | What it does |
|---|---:|---|
| **Validation engine and claim-governance kernel** | stable / evolving | The runnable in-loop validator plus the trusted checks and contracts around it: proposal, fit/compression, adversarial review, deterministic checks, projection, and run history. Home of the published [LLM gaming behavior catalog](docs/gaming_behavior_catalog.md). |
| **Project intake and evidence readiness** | release path | Local files, source typing, evidence binding, evidence gaps, claim support, trace readiness, and preflight admission before model spend. |
| **Report/export contract** | release path | Blocks stale or unsupported reports before model-written QA can promote them. |
| **LeanMill** | active / current frontier | Governed Lean proof search. Treat it as a deeper evidence track, not the first v0.4 adoption surface. |
| **Reflexive layer** | advisory | Mining over forecasts, actions, catches, experiment records, and in-loop/out-of-loop split. It surfaces stale ledgers, dead instruments, and underused capabilities. |

Terminology in this repo is layered: **workbench** means the user-facing
product, **kernel** means the trusted checks and contracts, **engine** means a
runnable subsystem, and **apparatus** means a historical experiment setup. The
[glossary](docs/concepts/glossary.md#core-concepts) is the reference when docs
use those words.

Typical flow:

```text
local question -> route choice -> intake/evidence/trace
-> preflight or bounded run -> review artifact
-> verdict, demotion, blocker, or next check
```

This is a local research workbench currently hardened around one human
reviewer's workflow. Public forkability, hosted collaboration, and multi-user
hardening are roadmap work, not completed claims.

## Design Invariants

- **The proposer does not grade itself.** Generation, adversarial review,
  scoring, and deterministic gates are separate actors.
- **A compile is necessary but insufficient.** A proof or program can compile
  while laundering the target through a hypothesis, citation, vacuous premise,
  or hidden oracle. Governance checks those cases separately.
- **Failures are first-class evidence.** Nulls, refusals, residuals, failed
  branches, and instrument failures are recorded because they change the next
  experiment.
- **Worker transport is metadata, not epistemology.** API calls, subscription
  CLIs, and local workers can all be used; the typed contract, artifact, and
  gate decide whether the result counts.
- **Chat is not the system of record.** Durable artifacts live under
  `projects/`, `research_areas/`, `org/`, `papers/`, and generated analytics.

## Evidence First

Start from the artifacts:

- [Live analytics dashboard](https://sparckix.github.io/ztare/) — a self-contained view of volume, taste, and compounding metrics, built through a leak-gated pipeline.
- [Evidence atlas](docs/evidence_atlas/README.md) — crosswalk from public claims to summaries, experiments, runnable checks, and caveats.
- [Public claim register](docs/public_claim_register.md) — claim by claim: scope, evidence, non-claims, next falsifiers.
- [Executable review pack](docs/evidence_atlas/executable_review_pack.md) — commands a reviewer can run.
- [LLM gaming behavior catalog](docs/gaming_behavior_catalog.md) and [gaming-catalog review artifact](docs/evidence_atlas/packets/gaming_catalog.md) — self-certifying code strategies plus mined cross-domain vectors, tied to registry/gate evidence and executable anchors by `make gaming-catalog-audit`.
- [`research_areas/EXPERIMENT_TRACK_RECORD.md`](research_areas/EXPERIMENT_TRACK_RECORD.md) and [`research_areas/insights_ledger.md`](research_areas/insights_ledger.md) — the durable experiment and finding record.

Scale is tracked as an internal health signal, not a benchmark: artifact
volume, in-loop versus out-of-loop work, ratified catches, and insight-density
changes are mined by the reflexive dashboard.

## How To Judge The Current Release

Do not judge ZTARE by repo size. Judge it by whether you can inspect the path
from a source file to a claim boundary.

Start with five questions:

1. Did a command catch a weak or unsupported claim?
2. Can you find the source or artifact behind the verdict?
3. Can you see what the result does not prove?
4. Can you see the next check that would change the answer?
5. Can you reproduce the path without trusting a chat transcript?

Use the [public claim register](docs/public_claim_register.md) and the
[evidence atlas](docs/evidence_atlas/README.md) to answer those questions.
Some claims already have project summaries, review artifacts, benchmark
evidence, runnable checks, demotions, and explicit non-claims. External review
is still sparse, and not every claim has the same review artifact shape. Treat
each claim at the evidence level its artifacts support.

## Command cheat sheet

After the install block above, these are the public commands worth trying first:

```bash
make help
make first-run     # full offline public first-run path
make hello         # offline: intake falsifier + overclaim demotion
make demo          # offline, no live model calls
make smoke-public  # offline
ztare --help       # human-facing CLI: project / autoresearch / action-intel / forecast / bundle / other commands
```

Add keys only for an LLM-backed loop. Supported API-provider keys are
`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`,
`KIMI_API_KEY` or `MOONSHOT_API_KEY`, and `XAI_API_KEY` or `GROK_API_KEY`;
subscription-CLI dispatch is also supported for wired call sites. See
[`docs/reference/model_aliases.md`](docs/reference/model_aliases.md) before
choosing a mutator/judge pair. After project-intake validation and trace readiness, run
the guarded CLI entry. It blocks before the first model call unless the intake file,
source/evidence inputs, and launcher preflight agree:

```bash
ztare autoresearch trace --project <project> --rubric <rubric> --intake <project>_intake.json --json
ztare autoresearch run --project <project> --rubric <rubric> --intake <project>_intake.json --preflight-only
ztare autoresearch run --project <project> --rubric <rubric> \
    --intake <project>_intake.json --iters 10 \
    --mutator kimi --judge gpt4.1
```

For serious runs, prefer cross-family pairs such as `kimi` + `gpt4.1`,
`grok` + `gemini-pro`, or `gemini-pro` + `gpt4.1`; use `CROSS_FAMILY=1`
when the run should fail before any model call if the pair shares a provider
family.

Before using a persistent agent outside the loop, ask whether the task belongs
in autoresearch. If the task needs project files or data first, create or
prepare them before run readiness; before trusting a run, inspect the trace:

```bash
ztare project source-init --project <project> --rubric <rubric>
ztare project source-check --project <project> --json
ztare project walkthrough --project <project> --rubric <rubric> --task "<bounded task>" --bounded-claim "<bounded claim>" --source-ref "<source>" --evidence-ref "<artifact>" --non-claim "<non-claim>" --next-falsifier "<falsifier>" --intake-out <project>_intake.json --json
ztare project new --help
ztare project prepare --project <project> --rubric <rubric>
ztare project intake create --path <project>_intake.json --project <project> --rubric <rubric> --task "<bounded task>" --bounded-claim "<bounded claim>" --source-ref "<source>" --evidence-ref "<artifact>" --non-claim "<non-claim>" --next-falsifier "<falsifier>" --expected-command "ztare autoresearch route --task '<bounded task>' --project <project> --rubric <rubric>"
ztare project intake validate --path <project>_intake.json
ztare project intake validate --path <project>_intake.json --source-preflight
ztare project intake enqueue --path <project>_intake.json
ztare autoresearch route --task "<task>" --project <project> --rubric <rubric>
ztare autoresearch trace --project <project> --rubric <rubric> --intake <project>_intake.json --json
ztare autoresearch health --project <project> --rubric <rubric> --json
```

The public path is deliberately short:

```text
project intake -> autoresearch trace -> preflight when needed -> bounded run -> report/export
```

`autoresearch trace` is the read-before-run surface. Use
`plan_preview.recommended_first_command`: before a fresh admission it is the
model-free preflight; after the current intake and run-readiness bytes are
admitted, it advances to the bounded run. Re-run preflight when the intake,
source/evidence surface, or launch contract changes.

`project intake enqueue` is stricter than shape validation: it requires the
local project source files to pass the offline source preflight. If source
files, source typing, or evidence artifacts are still missing, record that work
in the prep ledger first. Use `intake` for new commands and docs.

`source-init` creates `projects/<project>/raw/`,
`projects/<project>/workspace/`, and `raw/source_type_map.json`. It does not
write `evidence.txt` or start a run. Raw source documents must be typed with
`source_type` frontmatter or the source-type map. `make evidence-prepare`
runs `source-check` before the source-to-evidence compiler path; run
`source-check` standalone when you want the offline readiness report without a
model-backed compile.

Use `--intake` for the project-intake JSON. That is different from a review
artifact or evidence bundle. Use `ztare project prep-ledger ...` only when intake
is blocked on concrete prep work such as a missing source, artifact,
reproduction step, or cost estimate. It is an append-only prep ledger, not an
autoresearch scheduler.
For ready and malformed intake fixtures, see
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
| See why a claim-review constraint stack is used instead of a chat loop | [docs/concepts/cognitive_gym.md](docs/concepts/cognitive_gym.md) |
| Read the "why" behind the architecture (the three legs) | [research_areas/philosophy/three_legs_of_ztare.md](research_areas/philosophy/three_legs_of_ztare.md) |
| See how a new primitive is surfaced (anti-amnesia) | [docs/concepts/primitive_surfacing.md](docs/concepts/primitive_surfacing.md) |
| Read the papers | [papers/README.md](papers/README.md) |
| Work inside the repo as an agent | [AGENTS.md](AGENTS.md) (the repo constitution) |

### What Can Transfer

If you want to reuse the ideas without adopting the whole repo, start with the
pieces that solve ordinary AI-system problems:

- [Agentic engineering patterns](docs/concepts/agentic_engineering_patterns.md):
  replay tests, preflight checks, provenance fields, fail-closed routes, and
  result-bound success claims.
- [Reflexive primitives](docs/concepts/reflexive_engineering.md): ways to turn
  a repeated failure into a check, queue row, route, or record that a later run
  must consume.
- [Epistemic principles](docs/concepts/epistemic_principles.md): the rule that
  a proposer does not grade itself, plus failure catalogs and evidence levels.
- Research traces: attempts, critiques, source-readiness labels, demotions,
  nulls, and next falsifiers that can become training or evaluation material.

## Repository map

| Path | Purpose |
|---|---|
| `src/ztare/` | Implementation: validator, fit/MDL/BIC primitives, gates, the leanmill solver + governance kernel, orchestration. |
| `projects/` | Domain projects, evidence, workspaces, validator artifacts, scientific sandboxes, and proof surfaces. |
| `docs/` | Architecture, guides, concepts, evidence atlas. |
| `papers/` | Public manuscript sources + replication packages. |
| `ztare_proofs/` | Lean proof sources. |
| `research_areas/` | Experiment track record, seams, specs, debates, research logs. |
| `org/` | Roles, mandates, tasks, channels, runtime state (cognitive-firm tenant overlay). |

Public by default: the workbench source, validators, governance gates, Lean modules, public docs, and papers.
Local/gitignored: active strategy, sealed pre-registrations, credentials, and in-flight tactics — the
instrument is inspectable, while live experiments keep sealed envelopes so later results stay
interpretable.

## Papers

The papers explain why the workbench exists. The repo is the stronger evidence:
commands, source files, review artifacts, demotions, and checks.

- [Specification Gaming in LLM-Generated Code](papers/cognitive-camouflage/draft.md):
  nine benchmarked strategies for self-certifying code outputs · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960)
- [Adversarial Precedent Memory](papers/adversarial-precedent-memory/draft.md):
  hardening evaluators through mined failure constraints · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598)
- [Contract-Governed Hardening](papers/contract-governed-hardening/draft.md):
  staged promotion contracts for recursive hardening · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998)
- [Cognitive Firm](papers/cognitive-firm/draft.md):
  role and authority separation for AI work · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019)
- [Epistemic Verification](papers/epistemic-verification/draft.md):
  manuscript in revision.

Read science case studies through their experiment records and public claim
boundaries, not as free-standing proof of broad discovery performance.

## What ZTARE Does Not Claim

ZTARE improves claim discipline. It does not guarantee truth.

Do not read the repo as claiming that:

- a high score proves a discovery;
- a compile proves the statement was the right one;
- a calibration recovery is new science;
- one cold model answer is a controlled baseline unless model, date, and prompt
  are recorded;
- the current gates catch every failure mode;
- "works across domains" means no domain-specific evidence work remains.

If a result matters, it needs artifacts, checks, review records, non-claims,
and a next falsifier. Named personas in synthetic review panels are shorthand
for reasoning styles loosely inspired by public work; they are not the named
individuals' views, and no affiliation is implied
(`src/ztare/personas/registry.py`).

## Why It Is Built This Way

The short version is: compress the claim, invert the failure, and design the
environment around the model. The longer version lives in
[The Three Legs of ZTARE](research_areas/philosophy/three_legs_of_ztare.md),
the [philosophy folder](research_areas/philosophy/), and
[epistemic_principles.md](docs/concepts/epistemic_principles.md).

The design draws on a few established lines of thought:

- **Falsification and research programmes** — Popper (cheap refutation over persuasive confirmation);
  Lakatos (judge a programme by whether it predicts novel facts, not by how well it protects a core);
  Munger's inversion and checklists (name what would make success uninterpretable before celebrating it).
- **Measurement under optimization pressure** — Goodhart's law (a metric under pressure stops measuring
  what it measured); agency problems under delegated authority; Holmström's informativeness principle (score on the
  signal that actually carries outcome information). This is why proposing is separated from grading.
- **Organization and management** — Chandler's managerial capitalism and the M-form (the cognitive-firm
  runtime is role / mandate / gate separation); Williamson's transaction-cost economics (where to put a
  boundary); Ostrom on governing a shared resource; Taylor's scientific management; Simon's bounded
  rationality and near-decomposability.
- **Systems and cybernetics** — Ashby's requisite variety (a controller needs at least as much variety as
  what it regulates); Hofstadter's strange loops (*Gödel, Escher, Bach*) for the reflexive structure that
  reasons about its own reasoning.
- **The scaling stance** — taken in deliberate tension with Sutton's "bitter lesson": ZTARE grants that
  models keep scaling (you swap the leaf), but bets that an individual researcher's near-term leverage is
  the environment around a frozen model, not a bigger model. Karpathy's LLM-wiki pattern seeds the
  source-memory layer upstream of the validator.

These are influences, not endorsements; none of the authors are affiliated with the project.

## License & citation

MIT. The governance/orchestration code (`org/`, `supervisor/`, `orbit/`, `deploy/`, and
`src/ztare/{orchestration,supervisor,sessions,signals,notifications}/`) is a tenant-overlay integration of
the upstream [cognitive-firm](https://github.com/sparckix/cognitive-firm) kernel. Gitignored files are not
part of the public grant until promoted. Map: [LICENSES.md](LICENSES.md) · [LICENSE](LICENSE) ·
[NOTICE.md](NOTICE.md). Cite the specific paper or artifact you use, not the repository as a monolith;
the repository-level `CITATION.cff` exists for tooling that requires one citation target.
