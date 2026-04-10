# ZTARE — Zero-Trust Adversarial Reasoning Engine

**Papers:**
- [Paper 1: Cognitive Camouflage](papers/paper1/draft.md)
- [Paper 2: Adversarial Precedent Memory](papers/paper2/draft.md)
- [Paper 3: Contract-Governed Adversarial Evaluator Hardening](papers/paper3/draft.md)
- [Paper 4: The Cognitive Firm](papers/paper4/draft.md)

> The repo now contains four paper bundles: specification gaming (Paper 1), evaluator hardening (Paper 2), contract-governed kernel hardening (Paper 3), and AI governance / managerial capitalism (Paper 4).

---

## Three Interpretations

There are at least three plausible readings of this repo:

1. It is an overbuilt response to a problem that did not justify this much machinery.
2. It is an instructive failure: a concrete record of how quickly language-model systems can generate bureaucratic complexity.
3. It is evidence that a single researcher, working for roughly 10 days and spending about $212 in model tokens, can build a surprisingly capable stack: four papers, a hardened evaluator path, a supervisor control plane, and a reproducible benchmark harness.

My view is that the third interpretation is at least plausible enough to be worth publishing. If that view is wrong, the repo still exposes the costs, failure modes, and control surfaces in a way that is easier to inspect than vague claims about autonomous agents.

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
3. the work-tracking and hardening stack

Useful entry points:

- `docs/WORKFLOW.md`
- `docs/ARCHITECTURE.md`
- `supervisor/USER_MANUAL.md`

---

## Two Loops

There are now two distinct loops in this repo.

### 1. Kernel Loop

This is the logic hardening path for the epistemic engine itself:

- derivation
- hinge extraction
- gates
- bridge / runner / stage contracts

Goal:
- improve truth-handling and fail-closed behavior inside V4

Example:
- `research_areas/seeds/active/stage2_derivation_seam.md`

### 2. Supervisor Loop

This is the infrastructure path for how bounded packets get routed and executed:

- seeds
- proposals
- genesis
- manifests
- wrappers
- state routing

Goal:
- improve work routing, write-scope discipline, telemetry, and human gates

Important:
- the supervisor loop does **not** supersede kernel hardening
- it exists to make kernel hardening and future program work less manual

Public technical provenance for the hardening path lives in:
- `research_areas/debates/kernel/v4_core.md`
- `research_areas/debates/kernel/runner_hardening.md`
- `research_areas/debates/kernel/v4_bridge_hardening.md`
- `research_areas/debates/kernel/stage2_derivation_seam_hardening.md`
- `research_areas/debates/supervisor/supervisor_loop.md`

In short:

- kernel loop = improve the evaluator
- supervisor loop = improve the factory around evaluator work

---

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
- token-usage extraction across Gemini / Anthropic / OpenAI
- pricing-name normalization for cost estimation

Cost estimates are driven by:

- `supervisor/model_pricing.json`

If pricing is enabled there, validator runs can show estimated mutator/judge cost again even when provider responses return versioned model names such as `models/gemini-2.5-flash` or `claude-sonnet-4-6-20260401`.

## Paper 1 Legacy Runs

The legacy Paper 1 commands are now:

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

## Replication Status

Paper 1 now includes cross-mutator replication:
- Gemini / Gemini
- Claude / Gemini
- GPT-4o / Gemini

Paper 2 adds evaluator-hardening benchmarks:
- baseline soft judge (`A`)
- deterministic gates (`B`)
- gates plus primitives (`C`)
- crux-first ablation (`C2`)

The current public work is not “does gaming exist?” but:
- how stable semantic gates can become
- how far evaluator hardening generalizes across exploit families
- how much benchmark evidence is needed beyond the audited historical core

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

```bibtex
@misc{alami2025cognitivecamouflage,
  title   = {Cognitive Camouflage: Specification Gaming in LLM-Generated Code
             Evades Holistic Evaluation but Not Adversarial Execution},
  author  = {Alami, Daniel},
  year    = {2025},
  note    = {Preprint. Code: github.com/sparckix/ztare}
}
```

---

*Daniel Alami — MBA Candidate, Harvard Business School*
