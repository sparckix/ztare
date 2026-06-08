# ZTARE

**Scale the environment, not the model.** A *frozen, swappable* frontier model — Claude, GPT, Gemini,
the same one anyone can call — turns its capability into *auditable evidence* (claims, demotions, nulls,
next falsifiers) rather than slop *only inside a governed epistemic-discipline apparatus*. The model is
the interchangeable **leaf**; the apparatus around it — separation of proposing from grading,
anti-laundering governance, faithfulness checks, memory, accountability — is what decides whether
capability becomes evidence or premature closure. That apparatus, not the model, is the thing being
built here, and it is the moat: as models improve you swap the leaf in; the discipline compounds across
all of them. This single thesis runs through everything below — the published LLM-specification-gaming
work, the validator, a governed Lean proof-search factory, an org runtime that governs persistent AI
roles, and bounded scientific case studies.

Built by one operator and a rotating set of agentic operators during a spring-2026 sprint, then
pointed at itself. Single operator, N=1, non-expert. **Discovery over benchmarking** — the goal is
information about how a research search fails, not a score. Nothing here claims a solved Millennium
problem, an autonomous research engine, or a general law.

```text
research org chooses work → validator / leanmill / proof / panel / human-agent co-work
→ governance ratifies (or rejects) → ledgers + outcomes → forecasts / impact / trajectory mining
→ next action, split, defer, or kill
```

## What this repo is

Public tracks, designed to compose — the original LLM-gaming work is one subset, not the whole:

| Track | Maturity | What it does |
|---|---:|---|
| **ZTARE Kernel (discovery + validation)** | stable / evolving | A structure-DISCOVERY engine governed by adversarial validation — not just a verifier. A mutator PROPOSES candidate structural forms, the fit engine SOLVES their constants, and compression SELECTS the simplest gate-passing law by BIC (symbolic regression over a pre-registered grammar — it recovered forms like `n/U(n)` unguided); separate stages then RATIFY it — verification panel → judge → deterministic hard gates → telemetry → synthesis → closure — the proposer never grading itself. It solves AND verifies. Where the published [LLM-specification-gaming](docs/cheating_catalog.md) work lives. |
| **leanmill (governed proof search)** | active / current frontier | A governed Lean proof-search factory: swappable agent "leaves" PROPOSE proofs; one **governance kernel** RATIFIES (kernel compile + axiom allowlist + matched-negative-control + anti-laundering organs). A proof is a *closure* only when governance ratifies — never when the agent says so. The environment-multiplies-the-leaf thesis, executable. |
| **Org runtime (cognitive-firm)** | working prototype | Persistent role offices, mandates, tasks, gates, transition logs, damage signals — an applied instance of the reusable [cognitive-firm](https://github.com/sparckix/cognitive-firm) kernel. A fresh clone runs kernel-only; `org/` here is a thin tenant overlay. |
| **Reflexive layer** | dogfood / active | The apparatus mines its own forecasts, actions, catches, trajectories, and experiment records and feeds the result back — it reasons about, and corrects, itself (the audit that demoted its own claims is one). |
| **Scientific case studies** | experimental / status-labeled | Gravity, neural scaling, Navier-Stokes, transformer-successor, and other bounded campaigns that stress-test the kernel as falsifier pressure, not discovery rhetoric. |

The larger object is a disciplined research operating model for one operator — not a productized platform.

## Why this is different (the moat)

- **Anti-laundering governance.** Frontier provers and agents trust the kernel's `compile_ok`; this repo
  has shown that is *necessary but not sufficient* — a proof can compile yet launder the result (cite the
  target, assume the conclusion, exploit a vacuous hypothesis). The governance kernel is built to catch
  exactly that. No competing system ships this faithfulness firewall; it is the distinctive asset.
- **The leaf is swappable; the discipline compounds.** Every result here was produced by frontier models
  available to everyone. The difference is the apparatus, not model access — and a better model (a future
  trained prover) plugs in as one more leaf, inheriting the same governance.
- **The apparatus audits itself, and demotes its own claims.** A reflexive capability-ROI audit found
  that of ~18 catalogued primitives only four were engaged, seven were dead, seven never instantiated —
  and recorded it. The catch-ledger's own integrity validator was found dead for weeks and resurrected
  (surfacing ~300 integrity errors); a mis-selected rater was demoted mid-cycle. Both sit next to the
  original claims.

## Read it skeptically (evidence first)

- [Evidence atlas](docs/evidence_atlas/README.md) — reviewer crosswalk from public claims to summaries, experiments, runnable checks, caveats.
- [Public claim register](docs/public_claim_register.md) — claim-by-claim scope, evidence, non-claims, next falsifiers.
- [Executable review pack](docs/evidence_atlas/executable_review_pack.md) — commands a reviewer can run.
- [LLM gaming behavior catalog](docs/cheating_catalog.md) — original self-certifying code strategies plus mined cross-substrate vectors, each tied to the audit or gate pattern that catches it.
- The live record is [`research_areas/EXPERIMENT_TRACK_RECORD.md`](research_areas/EXPERIMENT_TRACK_RECORD.md) and [`research_areas/insights_ledger.md`](research_areas/insights_ledger.md) — read those, not a marketing number.

*Scale (a reflexive audit re-mines every artifact; treat as an internal signal, not a benchmark): tens
of thousands of authored artifacts, the trailing-window share dominated by out-of-loop agent dispatch +
governance + mining; triple-digit ratified self-audited catches across dozens of categories; recursive
insight-density gain that rose then plateaued (in-system rubric).*

## Core principles

- **The proposer does not grade itself.** Generation, adversarial review, scoring, and deterministic gates are separate.
- **Capability needs an environment.** Stronger models widen the search; discipline decides whether it becomes evidence or premature closure.
- **Prose is not evidence.** A claim survives executable checks, a kernel, holdout surfaces, or explicit refusal.
- **A compile is not a closure.** Verification is necessary, not sufficient; governance must also rule out laundering.
- **Failures are signal.** Nulls, refusals, residuals, and instrument failures are recorded — they change what to build next.
- **Chat is not the system of record.** Durable artifacts live under `projects/`, `research_areas/`, `org/`, and `papers/`.

## Quickstart

```bash
git clone https://github.com/sparckix/ztare && cd ztare
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && pip install -e .   # registers the `ztare` console script

make help
make demo          # offline, no live model calls
make smoke-public  # offline
ztare --help       # operator surface: forecast / leanmill / bundle subcommands
```

Add keys only for an LLM-backed loop (`GEMINI_API_KEY`; `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` optional by
model pairing — subscription-CLI dispatch is also supported). Run the validator on a project:

```bash
make experiment-loop PROJECT=<project> RUBRIC=<rubric> ITERS=10 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
```

Walkthrough + CLI tour: [docs/guides/quickstart.md](docs/guides/quickstart.md) · [docs/guides/cli.md](docs/guides/cli.md). leanmill architecture: [docs/concepts/leanmill_architecture.md](docs/concepts/leanmill_architecture.md).

## What transfers beyond this repo

Most of the value is substrate-independent:

- **[Agentic engineering patterns](docs/concepts/agentic_engineering_patterns.md)** — stub-replay testing, eligibility pre-filters, provenance telemetry, decomposed wire-in, cross-reference knowledge graphs.
- **[Reflexive primitives](docs/concepts/reflexive_engineering.md)** — capabilities the architecture runs on its own infrastructure (the audit that demoted its own claims is one).
- **[Epistemic discipline](docs/concepts/epistemic_principles.md)** — the proposer-doesn't-grade-itself constitution, a [mined anti-pattern catalog](docs/concepts/anti_pattern_catalog.md), an append-only [catch ledger](LEDGERS.md).
- **The cognitive-firm org runtime** — M-form role/mandate/gate separation; reusable kernel at [cognitive-firm](https://github.com/sparckix/cognitive-firm) (this repo is a tenant overlay).
- **Research-supervision traces** — attempts, critiques, source-readiness labels, demotions, nulls, next falsifiers preserved as training/eval material, not just final answers.

## Where to go

| If you want to… | Start at |
|---|---|
| See what the apparatus actually has, in two minutes | [docs/concepts/capabilities.md](docs/concepts/capabilities.md) |
| Review the evidence graph before trusting anything | [docs/evidence_atlas/README.md](docs/evidence_atlas/README.md) |
| Understand the governed proof-search factory | [docs/concepts/leanmill_architecture.md](docs/concepts/leanmill_architecture.md) |
| Understand the validator architecture | [docs/concepts/architecture.md](docs/concepts/architecture.md) |
| Understand proof execution + governance gate + residual compiler | [docs/concepts/closure_claim_governance.md](docs/concepts/closure_claim_governance.md) |
| Why a constrained loop beats a chat loop | [docs/concepts/cognitive_gym.md](docs/concepts/cognitive_gym.md) |
| How a new primitive is surfaced (anti-amnesia) | [docs/concepts/primitive_surfacing.md](docs/concepts/primitive_surfacing.md) |
| Read the papers | [papers/README.md](papers/README.md) |
| Work inside the repo as an agent | [AGENTS.md](AGENTS.md) (the repo constitution) |

## Repository map

| Path | Purpose |
|---|---|
| `src/ztare/` | Implementation: validator, fit/MDL/BIC primitives, gates, the leanmill solver + governance kernel, orchestration. |
| `projects/` | Domain projects, evidence, workspaces, validator artifacts, scientific sandboxes, Lean substrates. |
| `docs/` | Architecture, guides, concepts, evidence atlas. |
| `papers/` | Public manuscript sources + replication packages. |
| `ztare_proofs/` | Lean proof sources. |
| `research_areas/` | Experiment track record, seams, specs, debates, research logs. |
| `org/` | Roles, mandates, tasks, channels, runtime state (cognitive-firm tenant overlay). |

Public by default: the engine, validators, governance gates, Lean modules, public docs and papers.
Local/gitignored: active strategy, sealed pre-registrations, credentials, in-flight tactics — the
instrument is inspectable; live experiments keep sealed envelopes so later results stay interpretable.

## Published papers

- [Specification Gaming in LLM-Generated Code](papers/cognitive-camouflage/draft.md) — paper frozen to the original 9 benchmarked strategies; Cognitive Camouflage as an LLM-evaluation failure mode · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960)
- [Adversarial Precedent Memory](papers/adversarial-precedent-memory/draft.md) — hardening evaluators through mined failure constraints · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598)
- [Contract-Governed Hardening](papers/contract-governed-hardening/draft.md) — stage-gated recursive improvement with typed promotion contracts · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998)
- [Cognitive Firm](papers/cognitive-firm/draft.md) — managerial capitalism for artificial intelligence · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019)
- [Epistemic Verification](papers/epistemic-verification/draft.md) — manuscript in revision.

Read as a stack: (1) LLMs game underspecified evaluation; (2) mined precedents + gates harden
evaluators; (3) typed promotion contracts make recursive hardening safer; (4) persistent organizational
roles govern AI work; (5) epistemic verification decomposes judgment into repeatable operations plus a
bounded residual. The science case studies (gravity, neural scaling, Navier-Stokes, leanmill closures)
apply the stack as falsifier pressure — read them through the experiment records, not private drafts.

## Claims to read carefully

ZTARE improves research discipline; it does not guarantee truth. Do not infer that a high score proves a
discovery, that a kernel compile proves a non-laundered closure, that calibration recoveries are new
science, that an LLM cold shot is a controlled baseline (unless model/date/prompt are recorded), that
hard gates cover every failure mode, or that "works on any domain" means no domain-specific evidence
engineering. The standard is stricter: if a result matters, it needs artifacts, gates, closure rows, and
a clear statement of what would falsify it. **Named personas** (Dijkstra, Knuth, Munger) in synthetic
review panels are shorthand for reasoning styles loosely inspired by published work — not the
individuals' views, no affiliation implied (`src/ztare/personas/registry.py`).

## Intellectual lineage

Karpathy's LLM-wiki pattern for source memory upstream of the validator; Popperian falsification (cheap
refutation over persuasive confirmation); Mungerian inversion and checklists (name what would make
success uninterpretable before celebrating it); Hofstadter's strange loops (*Gödel, Escher, Bach*) for
the reflexive structure — a system that reasons about its own reasoning; scientific management and
cybernetics (roles, handoffs, ledgers, closure).

## License & citation

MIT. The governance/orchestration code (`org/`, `supervisor/`, `orbit/`, `deploy/`, and
`src/ztare/{orchestration,supervisor,sessions,signals,notifications}/`) is a tenant-overlay integration
of the upstream [cognitive-firm](https://github.com/sparckix/cognitive-firm) kernel. Gitignored files are
not part of the public grant until promoted. Map: [LICENSES.md](LICENSES.md) · [LICENSE](LICENSE) ·
[NOTICE.md](NOTICE.md). Cite the specific paper or artifact you use, not the repository as a monolith
(BibTeX in `papers/README.md`).
