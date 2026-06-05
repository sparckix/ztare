# ZTARE

**A filesystem-first research apparatus that turns human-agent research work into
auditable claims, demotions, nulls, and next falsifiers.**

ZTARE has three parts: a zero-trust adversarial validator, an out-of-loop research
runtime that governs persistent AI roles, and a reflexive layer that mines its own
forecasts, actions, catches, trajectories, and experiment records. The point is a
durable evidence trail — claim scope, evidence boundaries, failures, and follow-up
decisions stay inspectable after the conversation ends.

The working premise: scaffolding does not replace model capability, it shapes whether
that capability becomes evidence or slop. Like human talent, a model compounds or
degrades with the environment around it — task framing, evidence boundaries, role
separation, falsifiers, memory, accountability. ZTARE is an attempt to build that
environment.

```text
research org chooses work -> validator / proof / script / panel / human-agent co-work
-> ledgers and outcomes -> forecasts / action impact / trajectory mining
-> next action, split, defer, or kill
```

Built by one operator and a rotating set of agentic operators during a spring-2026
sprint, then pointed at itself. Single operator, N=1, non-expert. Nothing here claims a
solved Millennium problem, an autonomous research engine, or a general law.

## Read it skeptically (evidence first)

- [Evidence atlas](docs/evidence_atlas/README.md) — reviewer crosswalk from public claims to project summaries, experiments, runnable checks, and caveats.
- [Public claim register](docs/public_claim_register.md) — claim-by-claim scope, evidence, non-claims, next falsifiers.
- [Executable review pack](docs/evidence_atlas/executable_review_pack.md) — commands a reviewer can run, plus repo-health caveats.
- [9 ways LLMs cheat their own evaluations](docs/cheating_catalog.md) — named self-certifying strategies seen under execution-grade audit across Claude, Gemini, and GPT-4o, each with the audit pattern that catches it.

## What the measurement says (mined, not asserted)

A weekly reflexive audit re-mines every artifact and feeds the result back. These
numbers come from that audit, not a live dashboard; the live record is
[`research_areas/EXPERIMENT_TRACK_RECORD.md`](research_areas/EXPERIMENT_TRACK_RECORD.md)
and `research_areas/insights_ledger.md`. *Snapshot, mid-May 2026:*

- **~34,000 authored artifacts.** Roughly a quarter are validator iteration files; the
  rest is out-of-loop agent work, and the trailing-window share is higher. The live
  substrate is agent dispatch + governance + mining.
- **The apparatus falsified its own substrate and recorded it.** A 28-day, 157-project
  capability-ROI audit found that of ~18 catalogued primitives, only four were engaged,
  seven were dead, and seven were never instantiated.
- **Recursive gain was real, then plateaued** — contextualized insight density rose then
  flattened (in-system rubric, reported with that caveat).
- **Triple-digit ratified catches across dozens of categories, self-reported and
  in-system.** This is the apparatus auditing itself, not externally verified. The catch
  ledger's own integrity validator was found dead for weeks and resurrected (surfacing
  ~300 integrity errors); a mis-selected rater was demoted mid-cycle. Both are recorded
  next to the original claims. Treat the count as an internal signal, not a benchmark.

**Named personas.** Synthetic review panels use labels of real individuals (Dijkstra,
Knuth, Munger) as shorthand for reasoning styles loosely inspired by published work. They
do not represent those individuals' views and imply no affiliation. Full statement:
`src/ztare/personas/registry.py`.

## What this repo is

Four public tracks, designed to compose:

| Track | Maturity | What it does |
|---|---:|---|
| **ZTARE Kernel** | stable / evolving | Turns messy source material into bounded evidence snapshots, then stress-tests claims through mutator, verification panel, judge, hard gates, telemetry, synthesis, and closure. |
| **Org Runtime (tenant overlay)** | working prototype | Persistent role offices, mandates, tasks, gates, transition logs, damage signals, operator surfaces — ZTARE's applied instance of the reusable [cognitive-firm](https://github.com/sparckix/cognitive-firm) kernel. A fresh public clone runs kernel-only; `org/` here is a thin tenant overlay. |
| **ZTARE Research Co** | dogfood / active | The repo run as its own research company: role-bound agents use the runtime + kernel to run programs, close experiments, update ledgers. |
| **Scientific case studies** | experimental / status-labeled | Gravity, neural scaling, Navier-Stokes, transformer-successor, and other bounded campaigns that stress-test the kernel as falsifier pressure, not discovery rhetoric. |

The original LLM-gaming work is one subset. The larger object is a disciplined research
operating model for one operator — not a productized platform.

## Core principles

- **The proposer does not grade itself.** Generation, adversarial review, scoring, and deterministic gates are separate.
- **Capability needs an environment.** Stronger models widen the search; discipline decides whether it becomes evidence or premature closure.
- **Prose is not evidence.** A claim survives executable checks, holdout surfaces, or explicit refusal.
- **Memory is allowed; unearned trust is not.** The workspace accumulates sources; the validator starts from a bounded evidence snapshot.
- **Failures are signal.** Nulls, refusals, residuals, and instrument failures are recorded — they change what to build next.
- **Chat is not the system of record.** Durable artifacts live under `projects/`, `research_areas/`, `org/`, `ztare_workspace/`, and `papers/`.

## Quickstart

```bash
git clone https://github.com/sparckix/ztare
cd ztare
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e .            # registers the `ztare` console script

make help
make demo                  # no live model calls
make smoke-public          # no live model calls
ztare --help               # the operator surface (forecast / leanmill / bundle subcommands)
```

`make demo`/`smoke-public` run offline. Add keys only for an LLM-backed loop:

```bash
export GEMINI_API_KEY=...   # ANTHROPIC_API_KEY / OPENAI_API_KEY optional, by model pairing
```

Run the validator on a project (the safe default — attacker tools off, hard-gate
preflights on):

```bash
make experiment-loop PROJECT=<project> RUBRIC=<rubric> ITERS=10 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
```

A new domain scaffolds the same way (charter → workspace-update → evidence-compile →
review/promote `compiled_evidence.txt` → loop). Full walkthrough and the CLI tour:
[docs/guides/quickstart.md](docs/guides/quickstart.md) · [docs/guides/cli.md](docs/guides/cli.md).

## What transfers beyond this repo

Most of the value is substrate-independent and reusable without ZTARE:

- **[Agentic engineering patterns](docs/concepts/agentic_engineering_patterns.md)** — practices for pipelines whose internals are LLM calls: stub-replay testing, eligibility pre-filters, provenance telemetry, decomposed wire-in, cross-reference knowledge graphs.
- **[Reflexive primitives](docs/concepts/reflexive_engineering.md)** — capabilities the architecture runs on its own infrastructure (the audit that demoted its own claims is one).
- **[Epistemic discipline](docs/concepts/epistemic_principles.md)** — the proposer-doesn't-grade-itself constitution, a [mined anti-pattern catalog](docs/concepts/anti_pattern_catalog.md), and an append-only [catch ledger](LEDGERS.md).
- **The org runtime** — M-form separation (roles, mandates, gates, damage signals). The reusable kernel is [cognitive-firm](https://github.com/sparckix/cognitive-firm); this repo carries a tenant overlay (see [forking the kernel](docs/guides/forking_the_kernel.md)).
- **Research-supervision traces** — preserving attempts, critiques, source-readiness labels, demotions, nulls, and next falsifiers as training/eval material rather than keeping only final answers (see [architecture.md](docs/concepts/architecture.md)).

## Where to go

| If you want to… | Start at |
|---|---|
| See the repo layers and doc maturity | [docs/README.md](docs/README.md) |
| Review the evidence graph before trusting the architecture | [docs/evidence_atlas/README.md](docs/evidence_atlas/README.md) |
| See what the apparatus actually has, in two minutes | [docs/concepts/capabilities.md](docs/concepts/capabilities.md) |
| Understand how all modules compose | [docs/concepts/system_position_and_module_map.md](docs/concepts/system_position_and_module_map.md) |
| Understand the validator architecture | [docs/concepts/architecture.md](docs/concepts/architecture.md) |
| Why a constrained loop beats a chat loop | [docs/concepts/cognitive_gym.md](docs/concepts/cognitive_gym.md) |
| Run or inspect the org runtime | [docs/guides/org_runtime_quickstart.md](docs/guides/org_runtime_quickstart.md) |
| Understand proof execution, governance gate, residual compiler | [docs/concepts/closure_claim_governance.md](docs/concepts/closure_claim_governance.md) |
| Pressure-test a domain thesis | [docs/guides/workflow.md](docs/guides/workflow.md) |
| First 30 minutes in a fresh clone | [docs/guides/first-30-minutes.md](docs/guides/first-30-minutes.md) |
| Decode recurring terms and evidence levels | [docs/concepts/glossary.md](docs/concepts/glossary.md) |
| Read the Navier-Stokes public journey | [projects/ns_millennium_hunt/public/JOURNEY.md](projects/ns_millennium_hunt/public/JOURNEY.md) |
| Read the papers | [papers/README.md](papers/README.md) |
| Work inside the repo as an agent | [AGENTS.md](AGENTS.md) (the repo constitution) + [agent prompts](docs/guides/agent-prompts.md) |

## Repository map

| Path | Purpose |
|---|---|
| `src/ztare/` | Implementation: validator, fit primitives, gates, synthesis, orchestration, leanmill engine. |
| `projects/` | Domain projects, evidence, workspaces, validator artifacts, scientific sandboxes. |
| `docs/` | Architecture, guides, concepts, evidence atlas. |
| `papers/` | Public manuscript sources + replication packages. |
| `ztare_proofs/` | Lean proof sources (generated `.lake/` ignored). |
| `research_areas/` | Experiment track record, seams, specs, debates, research logs. |
| `org/` | Roles, mandates, preferences, tasks, channels, runtime state (tenant overlay). |
| `supervisor/` · `orbit/` · `ztare_workspace/` | Control-plane registry · governance UI · gates and transition logs. |

Public by default: the research engine, validators, gates, Lean modules, public docs and
papers. Local/gitignored: active strategy, sealed pre-registrations, credentials, and
in-flight tactics — the instrument is inspectable; live experiments keep sealed envelopes
so later results stay interpretable.

## Published papers

- [Cognitive Camouflage](papers/cognitive-camouflage/draft.md) — specification gaming in LLM-generated code · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960)
- [Adversarial Precedent Memory](papers/adversarial-precedent-memory/draft.md) — hardening evaluators through mined failure constraints · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598)
- [Contract-Governed Hardening](papers/contract-governed-hardening/draft.md) — stage-gated recursive improvement with typed promotion contracts · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998)
- [Cognitive Firm](papers/cognitive-firm/draft.md) — managerial capitalism for artificial intelligence · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019)
- [Epistemic Verification](papers/epistemic-verification/draft.md) — manuscript in revision.
- Adversarial Compression — experimental-mathematics manuscript (draft not mirrored here).

Read as a stack: (1) LLMs game underspecified evaluation; (2) mined precedents and gates
harden evaluators; (3) typed promotion contracts make recursive hardening safer; (4)
persistent organizational roles govern AI work; (5) epistemic verification decomposes
judgment into repeatable operations plus a bounded residual. The case-study layer applies
the stack as falsifier pressure — read it through the experiment records, not private
drafts. (Directories were renamed from the old `paperN` scheme to descriptive names.)

## Claims to read carefully

ZTARE improves research discipline; it does not guarantee truth. Do not infer that a high
score proves a discovery, that calibration recoveries are new science, that an LLM cold
shot is a controlled baseline (unless model/date/prompt are recorded), that hard gates
cover every failure mode, that the org runtime is enterprise-ready because the single-team
path works, or that "works on any domain" means no domain-specific evidence engineering.
The standard is stricter: if a result matters, it needs artifacts, gates, closure rows,
and a clear statement of what would falsify it.

## Intellectual lineage

Karpathy's LLM-wiki pattern for source memory upstream of the validator; Popperian
falsification (cheap refutation over persuasive confirmation); Mungerian inversion and
checklists (name what would make success uninterpretable before celebrating it);
Hofstadter's strange loops (*Gödel, Escher, Bach*; *I Am a Strange Loop*) for the reflexive
structure — a system that reasons about its own reasoning: the in-loop/out-of-loop
separation, reflexive primitives, and the meta-level reframe that rewrites what the level
beneath it counts as admissible; scientific management and cybernetics (roles, handoffs,
ledgers, closure).

## License & citation

MIT. The governance/orchestration code in `org/`, `supervisor/`, `orbit/`, `deploy/`, and
`src/ztare/{orchestration,supervisor,sessions,signals,notifications}/` is a tenant-overlay
integration of the upstream [cognitive-firm](https://github.com/sparckix/cognitive-firm)
kernel; the canonical kernel and its license live there. Gitignored files are not part of
the public grant until promoted. File-by-file map: [LICENSES.md](LICENSES.md) · full text:
[LICENSE](LICENSE) · third-party notices: [NOTICE.md](NOTICE.md).

Cite the specific paper or artifact you use, not the repository as a monolith:

```bibtex
@misc{alami2026cognitivecamouflage,
  title = {Cognitive Camouflage: Specification Gaming in LLM-Generated Code Evades Holistic Evaluation but Not Adversarial Execution},
  author = {Alami, Daniel}, year = {2026},
  note = {SSRN preprint 6512960. Code: github.com/sparckix/ztare},
  url = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960}
}
@misc{alami2026adversarialprecedent,
  title = {Adversarial Precedent Memory: Hardening LLM Evaluators Through Mined Failure Constraints},
  author = {Alami, Daniel}, year = {2026},
  note = {SSRN preprint 6525598. Code: github.com/sparckix/ztare},
  url = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598}
}
@misc{alami2026contractgoverned,
  title = {Contract-Governed Adversarial Evaluator Hardening: Stage-Gated Recursive Improvement with Typed Promotion Contracts},
  author = {Alami, Daniel}, year = {2026},
  note = {SSRN preprint 6542998. Code: github.com/sparckix/ztare},
  url = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998}
}
@misc{alami2026cognitivefirm,
  title = {The Cognitive Firm: Managerial Capitalism for Artificial Intelligence},
  author = {Alami, Daniel}, year = {2026},
  note = {SSRN preprint 6543019. Code: github.com/sparckix/ztare},
  url = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019}
}
```
