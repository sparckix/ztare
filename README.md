# ZTARE

ZTARE is a research workbench for turning model-generated proposals into
inspectable evidence. A model may propose a form, proof move, critique, or next
question; separate gates, judges, ledgers, and close rules decide what that
proposal means.

The design principle is **discovery over benchmarking**: a run should teach why
a search failed, where the evidence ceiling is, or which next falsifier matters.
A higher score is useful only when the artifacts explain what changed.

The repo was built by a single human reviewer during a spring-2026 sprint and
then used on itself. It does not claim a solved Millennium problem, an
autonomous research engine, or a general law. See
[What ZTARE Does Not Claim](#what-ztare-does-not-claim).

## What's actually here

Five tracks compose into the current workbench:

| Track | Maturity | What it does |
|---|---:|---|
| **ZTARE kernel** | stable / evolving | In-loop validation for bounded claims: mutator, fit/compression, judge, deterministic gates, projection, and run history. Home of the published [LLM specification-gaming catalog](docs/cheating_catalog.md). |
| **leanmill** | active / current frontier | Governed Lean proof search: agents propose proof moves, while compile checks, axiom policy, negative controls, and anti-laundering gates decide whether anything closes. |
| **Org runtime** | working prototype | Persistent roles, mandates, tasks, gates, and transition logs. `org/` is this repo's tenant overlay on the reusable [cognitive-firm](https://github.com/sparckix/cognitive-firm) kernel. |
| **Reflexive layer** | active | Mining over forecasts, actions, catches, experiment records, and in-loop/out-of-loop split. It surfaces dead instruments, stale ledgers, and underused capabilities. |
| **Scientific case studies** | experimental / labeled | Gravity, neural scaling, Navier-Stokes, transformer-successor, policy/market, and other bounded campaigns used as pressure tests. Treat them as evidence trails with status labels, not polished product demos. |

The in-loop kernel is appropriate when a task has four surfaces: a bounded
claim, stable evaluator or gate, rubric, and artifact output. Research
Directors and subscription agents operate outside the loop when the work is
source gathering, proof decomposition, project setup, synthesis, or surface
preparation. That boundary is inspectable through:

| Need | Command |
|---|---|
| Ask whether a task belongs in autoresearch | `ztare autoresearch route --task "<task>" --project <project> --rubric <rubric>` |
| Run the loop | `ztare autoresearch run ...` or `make experiment-loop PROJECT=<project> RUBRIC=<rubric>` |
| Use subscription workers for wired call sites | `make experiment-loop ... AGENT_MUTATOR=1 AGENT_JUDGE=1 AGENT_COMMITTEE=1 AGENT_INVERTER=1 AGENT_RUNTIME=codex` |
| Recommend next RD substrate/workbench surfaces | `ztare autoresearch substrate-recommend --prompt-only` |
| Compare API and subscription dispatch fixtures | `ztare autoresearch dispatch-parity --json` |
| Check actual API vs subscription run outcomes | `ztare autoresearch subscription-outcomes --json` |
| Check pending advisory eigenquestions | `ztare eigenquestion status --project <project>` |
| Inspect the hypothesis/evidence projection | `ztare autoresearch projection --project <project> --out /tmp/<project>_projection.json` |
| Record why agent work stayed outside the loop | `ztare action-intel record-agentic-route --route-json <route.json> --decision-id <id>` |
| Audit stagnant run traces | `ztare autoresearch hillclimb-audit --project <project>` |
| Check first-page autoresearch kernel health | `ztare autoresearch health --json` |
| Build the RD operations packet | `ztare autoresearch operations-intelligence --out /tmp/ztare_intel.json --markdown /tmp/ztare_intel.md` |
| Check primitive catalog and atlas health | `ztare primitive health` |
| Validate dormant in-loop fixtures | `make inloop-fixture-validate` |
| Check dispatch wrapper coverage | `make autoresearch-dispatch-validate` |

Typical flow:

```text
research org chooses work → autoresearch / proof / panel / human-agent co-work
→ governance ratifies (or rejects) → ledgers + outcomes → forecasts / impact / trajectory mining
→ next action: split, defer, or kill
```

This is a research operating model for one human reviewer. Public platform
hardening is still out of scope.

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
- [LLM gaming behavior catalog](docs/cheating_catalog.md) — self-certifying code strategies plus mined cross-substrate vectors, each tied to the gate that catches it.
- [`research_areas/EXPERIMENT_TRACK_RECORD.md`](research_areas/EXPERIMENT_TRACK_RECORD.md) and [`research_areas/insights_ledger.md`](research_areas/insights_ledger.md) — the durable experiment and finding record.

Scale is tracked as an internal health signal, not a benchmark: artifact
volume, in-loop versus out-of-loop work, ratified catches, and insight-density
changes are mined by the reflexive dashboard.

## Current Release Questions

ZTARE is best read through five questions:

1. Can a bounded loop produce a measurable research improvement under a hardened evaluator?
2. Does the kernel make fake progress visible before it becomes a claim?
3. Does research state survive across in-loop runs and out-of-loop agent work?
4. Can API calls, subscription agents, and local workers share the same typed artifact contract?
5. Can an outside reader reproduce the evidence path from command to artifact to gate?

Read the answers through the [public claim register](docs/public_claim_register.md)
and the [evidence atlas five-question map](docs/evidence_atlas/README.md#reading-the-evidence-through-five-questions),
not through repo volume.
Several claims already have L2-L4 evidence: project summaries, controlled or
ablated packets, benchmark evidence, runnable checks, demotions, and explicit
non-claims. What is still missing is uniformity and externalization: not every
claim has the same machine-readable packet, and external validation is sparse.
End-to-end benchmark-style improvement should therefore be claimed only where a
specific packet supports it, not generalized into a blanket system claim.

## Start here

```bash
git clone https://github.com/sparckix/ztare && cd ztare
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && pip install -e .   # registers the `ztare` console script

make help
make demo          # offline, no live model calls
make smoke-public  # offline
ztare --help       # human-facing CLI: autoresearch / action-intel / forecast / bundle / other surfaces
```

Add keys only for an LLM-backed loop (`GEMINI_API_KEY`; `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` optional by
model pairing — subscription-CLI dispatch is also supported). Run the validator on a project:

```bash
make experiment-loop PROJECT=<project> RUBRIC=<rubric> ITERS=10 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
```

Before using a persistent agent outside the loop, ask whether the task belongs
in autoresearch; after a run, inspect the projection:

```bash
ztare autoresearch route --task "<task>" --project <project> --rubric <rubric>
ztare autoresearch projection --project <project> --out /tmp/<project>_projection.json
ztare autoresearch health --json
```

Walkthrough + CLI tour: [docs/guides/quickstart.md](docs/guides/quickstart.md) · [docs/guides/cli.md](docs/guides/cli.md). leanmill architecture: [docs/concepts/leanmill_architecture.md](docs/concepts/leanmill_architecture.md).

## Go deeper

| If you want to… | Start at |
|---|---|
| See what the apparatus actually has, in two minutes | [docs/concepts/capabilities.md](docs/concepts/capabilities.md) |
| Review the evidence graph before trusting anything | [docs/evidence_atlas/README.md](docs/evidence_atlas/README.md) |
| Understand the governed proof-search workflow | [docs/concepts/leanmill_architecture.md](docs/concepts/leanmill_architecture.md) |
| Understand the validator architecture | [docs/concepts/architecture.md](docs/concepts/architecture.md) |
| Understand proof execution + governance gate + residual compiler | [docs/concepts/closure_claim_governance.md](docs/concepts/closure_claim_governance.md) |
| See why a constrained loop is used instead of a chat loop | [docs/concepts/cognitive_gym.md](docs/concepts/cognitive_gym.md) |
| Read the "why" behind the architecture (the three legs) | [research_areas/philosophy/three_legs_of_ztare.md](research_areas/philosophy/three_legs_of_ztare.md) |
| See how a new primitive is surfaced (anti-amnesia) | [docs/concepts/primitive_surfacing.md](docs/concepts/primitive_surfacing.md) |
| Read the papers | [papers/README.md](papers/README.md) |
| Work inside the repo as an agent | [AGENTS.md](AGENTS.md) (the repo constitution) |

### What transfers beyond this repo

Most of the value is substrate-independent:

- **[Agentic engineering patterns](docs/concepts/agentic_engineering_patterns.md)** — stub-replay testing, eligibility pre-filters, provenance telemetry, decomposed wire-in, cross-reference knowledge graphs.
- **[Reflexive primitives](docs/concepts/reflexive_engineering.md)** — capabilities the architecture runs on its own infrastructure (the audit that demoted its own claims is one).
- **[Epistemic discipline](docs/concepts/epistemic_principles.md)** — the proposer-doesn't-grade-itself constitution, a [mined anti-pattern catalog](docs/concepts/anti_pattern_catalog.md), an append-only [catch ledger](LEDGERS.md).
- **The cognitive-firm org runtime** — role/mandate/gate separation; reusable kernel at [cognitive-firm](https://github.com/sparckix/cognitive-firm) (this repo is a tenant overlay).
- **Research-supervision traces** — attempts, critiques, source-readiness labels, demotions, nulls, and next falsifiers preserved as training/eval material.

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

Public by default: the engine, validators, governance gates, Lean modules, public docs, and papers.
Local/gitignored: active strategy, sealed pre-registrations, credentials, and in-flight tactics — the
instrument is inspectable, while live experiments keep sealed envelopes so later results stay
interpretable.

## Published papers

- [Specification Gaming in LLM-Generated Code](papers/cognitive-camouflage/draft.md) — frozen to the original 9 benchmarked strategies; Cognitive Camouflage as an LLM-evaluation failure mode · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960)
- [Adversarial Precedent Memory](papers/adversarial-precedent-memory/draft.md) — hardening evaluators through mined failure constraints · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598)
- [Contract-Governed Hardening](papers/contract-governed-hardening/draft.md) — stage-gated recursive improvement with typed promotion contracts · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998)
- [Cognitive Firm](papers/cognitive-firm/draft.md) — managerial capitalism for artificial intelligence · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019)
- [Epistemic Verification](papers/epistemic-verification/draft.md) — manuscript in revision.

They read as a stack: (1) LLMs game underspecified evaluation; (2) mined precedents + gates harden
evaluators; (3) typed promotion contracts make recursive hardening safer; (4) persistent organizational
roles govern AI work; (5) epistemic verification decomposes judgment into repeatable operations plus a
bounded residual. The science case studies (gravity, neural scaling, Navier-Stokes, leanmill closures)
apply the stack as falsifier pressure — read them through the experiment records, not private drafts.

## What ZTARE does not claim

ZTARE improves research discipline; it does not guarantee truth. Do not read it as claiming that a high
score proves a discovery, that a kernel compile proves a non-laundered closure, that calibration
recoveries are new science, that an LLM cold shot is a controlled baseline (unless model, date, and prompt
are recorded), that hard gates cover every failure mode, or that "works on any domain" means no
domain-specific evidence engineering. The standard is stricter: if a result matters, it needs artifacts,
gates, closure rows, and a clear statement of what would falsify it. **Named personas** (Dijkstra, Knuth,
Munger) in synthetic review panels are shorthand for reasoning styles loosely inspired by published work —
not the individuals' views, and no affiliation is implied (`src/ztare/personas/registry.py`).

## Philosophical underpinnings & lineage

The "why" behind the architecture lives in the philosophy notes: [The Three Legs of
ZTARE](research_areas/philosophy/three_legs_of_ztare.md) — the constitutional derivation (invert,
compress, nurture) — plus the rest of the [philosophy folder](research_areas/philosophy/) (operational
manual, recursive-verification framework, reflexive primitives) and the transferable laws in
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
[NOTICE.md](NOTICE.md). Cite the specific paper or artifact you use, not the repository as a monolith
(BibTeX in `papers/README.md`).
