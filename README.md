# ZTARE — Zero-Trust Adversarial Reasoning Engine

ZTARE is a zero-trust adversarial reasoning engine for stress-testing claims, forecasts, and strategic theses. It separates source accumulation, bounded evidence compilation, adversarial evaluation, and downstream synthesis so that fluent generation is not allowed to grade itself.

## Who This Repo Is For

Two audiences, two entry paths. Pick the one that matches you and ignore the rest.

1. **You want to pressure-test a thesis on a domain** (startup diligence, activist target, strategy question, research claim). You are a **general-purpose engine user**.
   - Start at [docs/WORKFLOW.md §0b + §1–§5](docs/WORKFLOW.md) and the `Quickstart` and `Run on a New Domain` sections below.
   - Your loop is `raw -> workspace -> evidence -> validator -> synthesis`. You do not need the V4 kernel hardening, primitive library internals, or the supervisor control plane. Skip them.
2. **You want to play with the engine itself** (modify the validator, V4 kernel, primitives, supervisor, or synthesis pipeline). You are a **developer / researcher**.
   - Start at [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the layer map, then [docs/WORKFLOW.md](docs/WORKFLOW.md) §0a (mode choice) and §15 (program hardening), and [supervisor/USER_MANUAL.md](supervisor/USER_MANUAL.md) for the control plane.

If you are not sure: start as a general-purpose user. The hardening machinery is orthogonal to using the engine on a real project.

## Start Here

- [Workflow / Operator Manual](docs/WORKFLOW.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Supervisor Manual](supervisor/USER_MANUAL.md)
- [Papers Overview](papers/README.md)

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

---

## What is ZTARE?

ZTARE is a multi-agent loop in which:

1. A **Mutator** (LLM) generates a thesis with an embedded Python falsification suite
2. A **Firing Squad** (3 adversarial agents) attacks the thesis's weakest assumptions with counter-tests
3. A **Meta-Judge** scores only the execution output — never the prose
4. An **Axiom Store** accumulates beliefs that survived, degrading those that failed

The generator cannot influence its own evaluation. The judge never reads prose. This architecture catches specification gaming that single-agent LLM evaluation misses entirely.

At a high level, ZTARE is a zero-trust adversarial neurosymbolic system: LLMs generate and attack candidate theses, while deterministic code execution, parsers, and score gates constrain what counts as success. The contribution here is not the invention of debate, code execution, or neurosymbolic AI as such; it is the empirical finding that LLMs can systematically game self-authored falsification suites, and the verification architecture built to catch and harden against that behavior.

For domain projects, the validator now writes explicit `latest_*` and `champion_*` artifacts so operators can distinguish:

- the newest evaluated attempt
- the currently promoted best result for the active regime

---

## Repository Scope

The public repo currently has three active surfaces:

1. the adversarial validator and workspace pipeline
2. the synthesis / distribution pipeline
3. the hardening / control-plane stack

Useful entry points:

- `docs/WORKFLOW.md`
- `docs/ARCHITECTURE.md`
- `supervisor/USER_MANUAL.md`

## Layer Glossary

These names are load-bearing. Do not collapse them.

1. **ZTARE validator**
   - the adversarial domain-validation loop over evidence snapshots
2. **V4 kernel**
   - the evaluator being hardened
3. **Meta-runner**
   - the kernel-local deterministic promotion runner for V4 stage advancement
4. **Supervisor**
   - the multi-program control plane for bounded work packets
5. **Paper bundles**
   - public-facing manuscript sources under `papers/`

The same separation principle recurs across layers, but the names stay layer-specific:

- `meta-runner` is a kernel term
- `supervisor` is a control-plane term
- neither should be used as a generic synonym for the other

---

## Three Modes

Use the lightest mode that fits the task.

### 1. Artisanal / Manual

Use when:
- the task is exploratory
- the scope is still fuzzy
- the overhead of manifests / genesis is not worth it yet

This includes:
- manual debate prompting
- one-off architectural exploration
- general-purpose generation outside the routed control plane

### 2. Program Hardening

Use when:
- the work is a bounded kernel or infrastructure improvement
- provenance matters
- you want typed handoffs and fail-closed commits

This uses:
- `research_areas/seeds/**/*.md`
- `supervisor/program_genesis/`
- `supervisor/program_manifests/`
- supervisor routing

Operational additions:
- successful verifier promotion advances the manifest automatically
- `make supervisor-report ...` renders a read-only summary from `status.json` + `events.jsonl`

### 3. Domain Validation

Use when:
- the task is thesis generation / adversarial validation on a domain project

This uses the original ZTARE validator path:
- workspace
- evidence
- validator loop
- synthesis

So no: the new M-form control plane does not replace the original validator loop or all manual work.
It adds a governance layer for bounded improvement programs.

---

## The 9 Gaming Strategies Documented

| Strategy | Mechanism | Domain |
|---|---|---|
| **Blame Shield** | Bundle critical axiom with N sacrificial axioms; dilute penalty to 1/N | Bayesian |
| **Float Masking** | Apply `round()` before assertion to destroy precision difference | Bayesian |
| **Fake AutoDiff** | Name function after mechanism; body returns hardcoded dict | Bayesian |
| **Cooked Book RNG** | Hardcode environment to improve over time; fake learning | Bayesian, Finance |
| **Assert Narrowing** | Set assertion range to exactly match hardcoded inputs | AI Economics |
| **Dimensional Factor** | Introduce unit error; apply ×1000 correction to hide it | Finance, Physics |
| **Unidirectional Decay** | Formula valid for positive errors only; generates P>1.0 for negative | Epistemic Arch. |
| **Gravity Constant** | Invent ungrounded coupling constant; build test around it | Physics |
| **Straw Man Design** | Engineer the comparison object so the preferred design wins by construction | Startup |

All 9 are **self-certifying** — they pass their own assert statements while violating their epistemic intent.

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
