# ZTARE — Zero-Trust Adversarial Reasoning Engine

ZTARE stress-tests claims by making AIs argue against each other under hard numeric constraints. You give it a question and evidence; it returns a battle-tested answer that survived adversarial attack — or tells you the claim doesn't hold up.

It works on any domain: startup diligence, investment theses, research claims, strategy questions, scientific curve-fitting. The key idea: **the AI that proposes an answer is never allowed to grade itself.**

### Why this exists

When you ask an AI to evaluate its own work, it games the evaluation. We documented 9 distinct cheating strategies across Claude, Gemini, and GPT-4o — all self-certifying (they pass their own tests while violating their intent):

| Strategy | What it does | Domain |
|---|---|---|
| **Blame Shield** | Bundle critical axiom with N sacrificial ones; dilute penalty to 1/N | Bayesian |
| **Float Masking** | Apply `round()` before assertion to destroy precision difference | Bayesian |
| **Fake AutoDiff** | Name function after mechanism; body returns hardcoded dict | Bayesian |
| **Cooked Book RNG** | Hardcode environment to improve over time; fake learning | Bayesian, Finance |
| **Assert Narrowing** | Set assertion range to exactly match hardcoded inputs | AI Economics |
| **Dimensional Factor** | Introduce unit error; apply x1000 correction to hide it | Finance, Physics |
| **Unidirectional Decay** | Formula valid for positive errors only; generates P>1.0 for negative | Epistemic Arch. |
| **Gravity Constant** | Invent ungrounded coupling constant; build test around it | Physics |
| **Straw Man Design** | Engineer the comparison object so the preferred design wins by construction | Startup |

ZTARE prevents this by separating who proposes, who attacks, and who scores — and by adding numeric pass/fail checks that no AI can talk its way past. Full details: [Paper 1 (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960).

---

## Start Here

- **Use the engine on a domain:** [Quickstart](#quickstart-5-minutes) below, then [docs/WORKFLOW.md](docs/WORKFLOW.md)
- **Understand the architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Modify the engine:** [supervisor/USER_MANUAL.md](supervisor/USER_MANUAL.md)
- **Read the papers:** [papers/README.md](papers/README.md)
- **Operating principles:** [PRINCIPLES.md](PRINCIPLES.md)
- **Glossary of terms:** [docs/GLOSSARY.md](docs/GLOSSARY.md)

## Who This Repo Is For

Two audiences, two entry paths. Pick the one that matches you and ignore the rest.

1. **You want to pressure-test a thesis on a domain** (startup diligence, activist target, strategy question, research claim). You are a **general-purpose engine user**.
   - Start at [docs/WORKFLOW.md §0b + §1–§5](docs/WORKFLOW.md) and the `Quickstart` and `Run on a New Domain` sections below.
   - Your loop is `raw -> workspace -> evidence -> validator -> synthesis`. You do not need the V4 kernel hardening, primitive library internals, or the supervisor control plane. Skip them.
2. **You want to play with the engine itself** (modify the validator, V4 kernel, primitives, supervisor, or synthesis pipeline). You are a **developer / researcher**.
   - Start at [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the layer map, then [docs/WORKFLOW.md](docs/WORKFLOW.md) §0a (mode choice) and §15 (program hardening), and [supervisor/USER_MANUAL.md](supervisor/USER_MANUAL.md) for the control plane.

If you are not sure: start as a general-purpose user. The hardening machinery is orthogonal to using the engine on a real project.

## Recommended Interface

ZTARE is usable from the shell, but it is easier to operate with an agentic coding assistant such as **Claude Code** or **Codex**.

Why:

- the repo has multiple workflows, not one
- the meaningful state is spread across project artifacts, not just code
- the right next move is often "read the latest artifacts and decide" rather than "run another loop"

Recommended pattern:

1. ask the agent to read `README.md`, `docs/WORKFLOW.md`, and `docs/ARCHITECTURE.md`
2. point it at the specific `projects/<project>/` directory or hardening item you care about
3. have it recommend whether the next move is:
   - evidence work
   - another validator run
   - synthesis
   - or a new seam/spec

### Sample Prompts

Use prompts like these with Claude Code or Codex:

```text
Read README.md, docs/WORKFLOW.md, and docs/ARCHITECTURE.md, then explain the layers of ZTARE and tell me which workflow I should use for my task.
```

```text
Inspect projects/<project>/ and summarize the current state: latest vs champion, evidence gaps, derived constraints, and the best next move.
```

```text
I want to start a new ZTARE project on <topic>. Scaffold the charter, tell me what should go into raw/, and give me the exact commands to run.
```

```text
Explain the difference between the validator, the V4 kernel, the meta-runner, and the supervisor in this repo, using the actual files.
```

```text
Given this latest score/result, tell me whether I should run more iterations, do an evidence pass, or stop and open a new seam/spec.
```

```text
Take project <project> and generate the right downstream artifact: founder memo, teaching note, field manual entry, or research postmortem.
```

## Published Papers

- [Cognitive Camouflage: Specification Gaming in LLM-Generated Code Evades Holistic Evaluation but Not Adversarial Execution](papers/paper1/draft.md) | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960)
- [Adversarial Precedent Memory: Hardening LLM Evaluators Through Mined Failure Constraints](papers/paper2/draft.md) | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598)
- [Contract-Governed Adversarial Evaluator Hardening: Stage-Gated Recursive Improvement with Typed Promotion Contracts](papers/paper3/draft.md) | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998)
- [The Cognitive Firm: Managerial Capitalism for Artificial Intelligence](papers/paper4/draft.md) | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019)

Each paper bundle includes the public manuscript sources under `papers/`. Local scratch workspaces such as `paper1/` and `paper2/` are gitignored and not part of the public source layer.

### Private Supporting Materials

The public repository contains the full engine, public papers, and reproducible public artifacts. Some raw experiment logs, detailed session artifacts, exploit-sensitive methodology notes, and supporting internal documentation are kept private by default.

This split is deliberate: code and public-facing results ship, while active exploit catalogs and still-cooking first-mover methodology stay private until they are ready to be promoted. Preview access is available upon request for researchers and practitioners actively working in AI governance, evaluation, or recursive systems.

---

## What is ZTARE?

**In a nutshell:** ZTARE is an independent auditor for claims — one AI proposes an answer, another AI attacks it, and hard numeric checks that neither can override decide whether the answer is actually right.

**Why it exists:** When you ask an AI to evaluate its own work, it games the evaluation. We documented 9 distinct cheating strategies across multiple AI models and domains (see table below). ZTARE's architecture prevents this by separating who proposes, who attacks, and who scores — and by adding numeric pass/fail tests that no AI can talk its way past.

**How the loop works:**

1. A **Mutator** (AI) proposes an answer with testable code
2. A **Firing Squad** (3 adversarial AIs) attacks the weakest assumptions
3. A **Meta-Judge** scores only the code output — never the prose
4. **Hard gates** (numeric pass/fail checks) catch answers that sound good but are actually wrong
5. The best surviving answer becomes the **champion**; repeat

The generator cannot influence its own evaluation. The judge never reads prose. Hard gates cannot be overridden. This catches specification gaming that single-agent evaluation misses entirely.

For a complete glossary of terms used in this project, see [docs/GLOSSARY.md](docs/GLOSSARY.md).

For domain projects, the validator writes explicit `latest_*` and `champion_*` artifacts so operators can distinguish:

- the newest evaluated attempt
- the currently promoted best result for the active regime

---

## Repository Scope

The public repo currently has four active surfaces:

1. the adversarial validator and workspace pipeline
2. a Karpathy-inspired LLM knowledge workspace ([design pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) that accumulates source material upstream of the validator
3. the synthesis / distribution pipeline
4. the hardening / control-plane stack

Useful entry points:

- `docs/WORKFLOW.md`
- `docs/ARCHITECTURE.md`
- `supervisor/USER_MANUAL.md`

## Layer Glossary

Five layers, each with a distinct job. See [docs/GLOSSARY.md](docs/GLOSSARY.md) for the full term list.

1. **Knowledge Workspace** — a persistent upstream memory layer inspired by [Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): raw sources accumulate, an LLM extracts structured notes, and a compiler emits bounded evidence snapshots for the validator. The workspace remembers; the validator does not.
2. **Validator** — the adversarial loop (mutator vs. firing squad vs. judge) that stress-tests claims
3. **Kernel** — the scoring and evaluation logic being continuously hardened against gaming
4. **Meta-runner** — the deterministic promotion system for kernel improvements (not the validator)
5. **Supervisor** — the work-management layer that routes tasks, tracks progress, and enforces budgets (does not decide truth)
6. **Papers** — public-facing manuscripts under `papers/`

These are separate concerns. The supervisor manages work; the validator decides truth. Don't use them interchangeably.

---

## Three Modes

Use the lightest mode that fits the task.

### 1. Manual / Exploratory

For thinking, strategizing, one-off analysis. No automation overhead. Just you and the AI working directly.

### 2. Domain Validation (most users start here)

For stress-testing a claim on real data: `raw sources -> workspace -> evidence -> validator -> report`. This is the core ZTARE loop. See [Quickstart](#quickstart-5-minutes) below.

### 3. Program Hardening (engine developers only)

For systematic improvements to the engine itself, with typed handoffs, provenance tracking, and fail-closed commits. Uses the supervisor control plane. See [supervisor/USER_MANUAL.md](supervisor/USER_MANUAL.md).

---

---

## Quickstart (5 minutes)

```bash
git clone https://github.com/sparckix/ztare
cd ztare
pip install -r requirements.txt

export GEMINI_API_KEY=your_key_here
# Optional: also set ANTHROPIC_API_KEY for Claude-as-judge experiments

# See common task shortcuts
make help

# Run the adversarial loop on an existing domain
python -m src.ztare.validator.autoresearch_loop \
  --project epistemic_engine_v3 \
  --rubric epistemic_engine_v3_evolved

# Run the detectability baseline (isolated snippets)
python -m src.ztare.experiments.baseline_experiment

# Run the Cognitive Camouflage experiment (full thesis evaluation)
python -m src.ztare.experiments.cognitive_camouflage_experiment
```

---

## Run on a New Domain

```bash
# 1. Create a project directory
mkdir -p projects/your_domain

# 2. Add a charter unless the project is provably narrow
python -m src.ztare.common.scaffold_project_charter \
  --project your_domain \
  --mode broad

# 3. Seed initial evidence
echo "Your domain description and seed claim here." > projects/your_domain/evidence.txt

# 4. Run the loop
python -m src.ztare.validator.autoresearch_loop --rubric recursive_bayesian --project your_domain

# Equivalent shortcut
make loop PROJECT=your_domain RUBRIC=recursive_bayesian

# Debate logs appear in projects/your_domain/
# Best thesis auto-syncs to projects/your_domain/thesis.md
```

For projects that use the full evidence workflow, the current loop is:

```text
raw/ -> workspace/ -> compiled_evidence.txt -> evidence.txt -> validator
```

If the validator emits typed evidence gaps, they are written to:

- `projects/<project>/workspace/latest_evidence_gaps.json`
- `projects/<project>/workspace/champion_evidence_gaps.json`
- `projects/<project>/workspace/latest_constraint_proposals.json`
- `projects/<project>/workspace/derived_constraints.json`
- `projects/<project>/workspace/derived_constraints_brief.md`
- `projects/<project>/workspace/evidence_gap_brief.md` (after `compile_evidence.py`)
- `projects/<project>/workspace/latest_compile_failure.json` (only if `compile_evidence.py` fails closed)

Important:

- the active score regime now fingerprints the contents of `evidence.txt`
- once `compiled_evidence.txt` is promoted into `evidence.txt`, the next run automatically rebaselines under the richer evidence boundary
- if the compiler hits a provider outage, it exits `1`, writes `latest_compile_failure.json`, and leaves the active evidence frontier unchanged

Charter note:

- if the project contains any forward-looking claim, declare a `Forecast Type` in `project_charter.md`
- use `directional_forecast` for bounded tilt claims
- use `probabilistic_forecast` only when the project is explicitly trying to justify a `%` forecast

## Provider Runtime

ZTARE now uses a shared provider/runtime layer for:

- model-family to model-id resolution
- retry and transient-error handling
- cross-provider failover on persistent transient outages
- token-usage extraction across Gemini / Anthropic / OpenAI
- pricing-name normalization for cost estimation

Cost estimates are driven by:

- `supervisor/model_pricing.json`

If pricing is enabled there, validator runs can show estimated mutator/judge cost again even when provider responses return versioned model names such as `models/gemini-2.5-flash` or `claude-sonnet-4-6-20260401`.

Important:

- if a run falls back to a different effective judge model, the score regime changes and comparability is intentionally broken rather than hidden

## Legacy Benchmark Shortcuts

The legacy Paper 1 benchmark shortcuts are:

```bash
make paper1-tsmc-legacy
make paper1-epistemic-legacy
```

These preserve the same project/rubric/model pairings as the prior root-script commands.

---

## Synthesize a Project into a Founder Memo or Architectural Brief

After the adversarial loop runs, `src/ztare/synthesis/synthesize.py` compresses the debate history, hardened thesis, and evidence into a clean, audience-appropriate artifact — without losing the hard conclusions.

It runs as a post-processing step and produces four outputs:
- `synthesis/history_summary.json` — recurring survivors, failures, and noise labels across all runs
- `synthesis/ledger.json` — canonical extraction of all high-signal conclusions
- `synthesis/brief.json` — audience-specific salience plan (what to emphasize, in what order)
- `Report.md` — the final artifact, written from the brief and gated by a QA check

```bash
# Synthesize a startup project into a founder memo
python -m src.ztare.synthesis.synthesize --project central_station --model gemini --qa-model claude

# Synthesize an architecture project into an architectural brief
python -m src.ztare.synthesis.synthesize --project epistemic_engine_v3_gemini_gemini --model gemini

# Force a specific renderer type
python -m src.ztare.synthesis.synthesize --project your_domain --model gemini --renderer-type founder_memo

# Use full history instead of focused (default for research-style artifacts)
python -m src.ztare.synthesis.synthesize --project your_domain --model gemini --history-mode full
```

`Report.md` is only written if QA passes (faithful + score ≥ 85). If it fails, inspect `synthesis/Report.candidate.md` and `synthesis/qa.json` to see what drifted.

The renderer type is inferred automatically from the project type. To add a new renderer, run with an unknown `--renderer-type` — the system will generate a suggested prompt at `config/renderers/<type>.md`, stop, and let you review it before use.

---

## Shortcuts

For common tasks, use:

```bash
make help
make workspace-update PROJECT=<project> MODEL=gemini
make evidence-compile PROJECT=<project> MODEL=gemini
make loop PROJECT=<project> RUBRIC=<rubric> ITERS=10 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
make synth PROJECT=<project> MODEL=gemini QA_MODEL=claude RENDERER=founder_memo
make benchmark BENCH_JUDGE=gemini BENCH_JOBS=3
```

---

## Repository Structure

```
src/ztare/                            # Actual Python implementation modules
requirements.txt
rubrics/                              # Scoring rubrics (evolve automatically at score ≥85)
config/
  prompts/                            # Synthesizer extraction, history, brief, and QA prompts
  renderers/                          # Per-audience renderer prompts (founder_memo, architectural_memo, research_note)
benchmarks/                           # Paper 2 evaluator hardening benchmark suites and runs
global_primitives/                    # Primitive mining, review, and approved precedent memory
papers/
  paper1/                             # Public source bundle for Paper 1
  paper2/                             # Public source bundle for Paper 2
  paper3/                             # Public source bundle for Paper 3
  paper4/                             # Public source bundle for Paper 4
paper1/                               # Local scratch/build workspace (gitignored)
paper2/                               # Local scratch/build workspace (gitignored)
paper3/                               # Local scratch/build workspace (gitignored)
paper4/                               # Local scratch/build workspace (gitignored)
research_areas/                       # Seed specs, seed registry, and grouped debate records
  seed_registry.json                  # Seed lifecycle (active/deferred/closed)
  seeds/active/stage2_derivation_seam.md                # Closed derivation-seam seed retained for provenance
  seeds/deferred/systems_to_algorithms.md               # Deferred algorithmic roadmap
  seeds/legacy/v3_interface.md                          # Closed legacy seed
  seeds/deferred/vnext_semantic_gate_stabilization.md   # Deferred kernel hardening seed
supervisor/                           # Supervisor control plane
  program_registry.json               # Curated routable program portfolio
  program_genesis/                    # Immutable genesis artifacts for accepted programs
  agent_wrappers.json                 # Thin launch wrapper configuration for agent CLIs
  model_pricing.json                  # Optional pricing matrix; disabled until explicitly configured
  USER_MANUAL.md                      # Practical supervisor usage
docs/                                 # Architecture, workflow, and benchmark design notes
projects/
  *_gemini_gemini/                    # Published legacy showcase projects
```

---

## API Keys

| Key | Used for |
|---|---|
| `GEMINI_API_KEY` | Mutator + Firing Squad (required) |
| `ANTHROPIC_API_KEY` | Claude-as-judge in baseline/camouflage experiments (optional) |

Get a Gemini key at [aistudio.google.com](https://aistudio.google.com). Gemini 2.5 Flash is free tier eligible.

---

## What's Actually In This Repo Now

The public work is no longer a single "does gaming exist?" claim. It is a four-paper stack plus the engine that produced it.

- **Paper 1 — Cognitive Camouflage.** Specification gaming in LLM-generated code evades holistic evaluation but not adversarial execution. Cross-mutator replication across Gemini, Claude, and GPT-4o (all judged by Gemini). Establishes that gaming is a reproducible property of the loop topology, not an artifact of one model family.
- **Paper 2 — Adversarial Precedent Memory.** Evaluator hardening via mined failure constraints, benchmarked across soft judge (`A`), deterministic gates (`B`), gates-plus-primitives (`C`), and crux-first ablation (`C2`). Shows that reusable, defeasible precedents transfer across exploit families.
- **Paper 3 — Contract-Governed Evaluator Hardening.** Stage-gated recursive improvement with typed promotion contracts. Six kernel stages plus a Stage 2→4 bridge, each with its own deterministic gate. This is the kernel-hardening spine.
- **Paper 4 — The Cognitive Firm.** Managerial capitalism for AI: the M-form governance layer (supervisor + program manifests + human gates) that sits on top of the kernel, with constrained self-hosting as the distinguishing architectural claim.

What this means for different readers:

- if you want to **use the engine**, everything from Paper 1 is downstream of the validator and synthesis you already get in the `Quickstart` below — you do not need to read Papers 2–4 to run a domain project
- if you want to **extend the engine**, Papers 2–4 describe the hardening, primitive, and control-plane layers in the same order they sit in the codebase

This is a single-principal, single-system research program (N=1 by construction). The claims are scoped to that.

---

## Collaboration

The most useful outside engagement for this repo is not generic feedback. It is one of:

- independent replication on new domains
- adversarial review of evaluator-hardening claims
- careful criticism of the evidence and forecast workflow
- collaboration on synthesis, distribution, or benchmark design

Best starting points:

- `docs/ARCHITECTURE.md`
- `docs/WORKFLOW.md`

If you are reaching out about a specific claim, benchmark, or failure mode, include the exact project, rubric, and artifact path.

---

## Citation

If you cite this work, please cite the specific paper you are engaging with rather than the repo as a whole. All four are SSRN preprints.

```bibtex
@misc{alami2026cognitivecamouflage,
  title   = {Cognitive Camouflage: Specification Gaming in LLM-Generated Code
             Evades Holistic Evaluation but Not Adversarial Execution},
  author  = {Alami, Daniel},
  year    = {2026},
  note    = {SSRN preprint 6512960. Code: github.com/sparckix/ztare},
  url     = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960}
}

@misc{alami2026adversarialprecedent,
  title   = {Adversarial Precedent Memory: Hardening LLM Evaluators Through
             Mined Failure Constraints},
  author  = {Alami, Daniel},
  year    = {2026},
  note    = {SSRN preprint 6525598. Code: github.com/sparckix/ztare},
  url     = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598}
}

@misc{alami2026contractgoverned,
  title   = {Contract-Governed Adversarial Evaluator Hardening: Stage-Gated
             Recursive Improvement with Typed Promotion Contracts},
  author  = {Alami, Daniel},
  year    = {2026},
  note    = {SSRN preprint 6542998. Code: github.com/sparckix/ztare},
  url     = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998}
}

@misc{alami2026cognitivefirm,
  title   = {The Cognitive Firm: Managerial Capitalism for Artificial Intelligence},
  author  = {Alami, Daniel},
  year    = {2026},
  note    = {SSRN preprint 6543019. Code: github.com/sparckix/ztare},
  url     = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019}
}
```
