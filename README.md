# ZTARE: Zero-Trust Adversarial Reasoning Engine

ZTARE makes AIs argue against each other under hard numeric constraints. You give it a question and evidence; it returns an answer that survived adversarial attack, or tells you the claim doesn't hold up.

It works on any domain: startup diligence, investment theses, research claims, strategy questions, scientific curve-fitting. The key idea: **the AI that proposes an answer is never allowed to grade itself.**

The loop works in five steps:

1. A **Mutator** proposes an answer with testable code.
2. A **Verification Panel** (3 adversarial AIs) attacks the weakest assumptions.
3. A **Meta-Judge** scores only the code output, not the prose.
4. **Hard gates** (numeric pass/fail checks) catch answers that sound right but compute wrong.
5. The best surviving answer becomes the **champion**; repeat.

The generator cannot influence its own evaluation. The judge never reads prose. Hard gates cannot be overridden.

### Why this exists

When you ask an AI to evaluate its own work, it games the evaluation. We documented 9 distinct cheating strategies across Claude, Gemini, and GPT-4o. All are self-certifying (they pass their own tests while violating their intent):

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

ZTARE prevents this by separating who proposes, who attacks, and who scores, and by adding numeric pass/fail checks that no AI can talk its way past. Full details: [Cognitive Camouflage (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960).

---

## Start Here

- **Use the engine on a domain:** [Quickstart](#quickstart-5-minutes) below, then [docs/guides/workflow.md](docs/guides/workflow.md)
- **Understand the architecture:** [docs/concepts/architecture.md](docs/concepts/architecture.md)
- **Run ZTARE as an experiment (pre-regs, contamination, gates, replication):** [docs/guides/for_researchers.md](docs/guides/for_researchers.md)
- **Modify the engine:** [supervisor/USER_MANUAL.md](supervisor/USER_MANUAL.md)
- **Read the papers:** [papers/README.md](papers/README.md)
- **Operating principles:** [PRINCIPLES.md](PRINCIPLES.md)
- **Orbit — governance interface:** [orbit/](orbit/) — spatial constellation UI for governing autonomous AI agents. Orbs encode state; you set gravity, agents orbit. Event-sourced, git-backed.
- **Reflexive engineering (Paper 5 in code):** [docs/concepts/reflexive_engineering.md](docs/concepts/reflexive_engineering.md) — six primitives for LLM agent self-improvement
- **Organizational primitives (Paper 4 in code):** [docs/concepts/organizational_primitives.md](docs/concepts/organizational_primitives.md) — four primitives for multi-agent governance
- **Cognitive gym (Paper 5 in code):** [docs/concepts/cognitive_gym.md](docs/concepts/cognitive_gym.md) — the epistemic discipline architecture that makes LLMs produce better science
- **Glossary of terms:** [docs/concepts/glossary.md](docs/concepts/glossary.md)

## Who This Repo Is For

Three audiences. Pick the one that matches you and ignore the rest.

1. **You want to pressure-test a thesis on a domain** (startup diligence, activist target, strategy question, research claim). You are a **general-purpose engine user**.
   - Start at [docs/guides/workflow.md §0b + §1-§5](docs/guides/workflow.md) and the `Quickstart` and `Run on a New Domain` sections below.
   - Your loop is `raw -> workspace -> evidence -> validator -> synthesis`. You do not need the hardening internals or the supervisor control plane. Skip them.
2. **You want to discover asymptotic laws from numerical data** (OEIS sequences, physical measurements, any observable). You are a **science track user**.
   - Start at `make discover`. The engine takes unlabeled data, proposes functional forms, fits parameters deterministically, tests against sealed holdout gates, compresses to the minimal surviving template, and optionally generates Lean 4 proof stubs. See [Science Track](#science-track) below.
   - Track record: 10 substrates, zero false positives. Recovered Hardy-Ramanujan, estimated the Lucky number density constant (unpublished), identified Meinardus n^(1/3) topology, characterized Ulam density fluctuations as 1/f fractal noise.
3. **You want to play with the engine itself** (modify the validator, kernel, primitives, supervisor, or synthesis pipeline). You are a **developer / researcher**.
   - Start at [docs/concepts/architecture.md](docs/concepts/architecture.md) for the layer map, then [docs/guides/workflow.md](docs/guides/workflow.md) §0a (mode choice) and §15 (program hardening), and [supervisor/USER_MANUAL.md](supervisor/USER_MANUAL.md) for the control plane.

If you are not sure: start as a general-purpose user.

## Recommended Interface

ZTARE is usable from the shell, but it is easier to operate with an agentic coding assistant such as **Claude Code** or **Codex**.

Why:

- the repo has multiple workflows, not one
- the meaningful state is spread across project artifacts, not just code
- the right next move is often "read the latest artifacts and decide" rather than "run another loop"

Recommended pattern:

1. ask the agent to read `README.md`, `docs/guides/workflow.md`, and `docs/concepts/architecture.md`
2. point it at the specific `projects/<project>/` directory or hardening item you care about
3. have it recommend whether the next move is:
   - evidence work
   - another validator run
   - synthesis
   - or a new seam/spec

### Sample Prompts

Use prompts like these with Claude Code or Codex:

```text
Read README.md, docs/guides/workflow.md, and docs/concepts/architecture.md, then explain the layers of ZTARE and tell me which workflow I should use for my task.
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

**Science track prompts:**

```text
I have a sequence of (n, z) pairs in evidence.txt. Run `make discover` to find the asymptotic law, compress to the minimal template, and generate Lean proof stubs.
```

```text
The compression found a*sqrt(n)+b*log(n)+c. Run the rival exclusion test: fit loglog, sqrt(log), free power, and log-polynomial rivals. Report which pass the holdout gate.
```

```text
Check the Lucky 500K coefficient stability: refit at scales 5K, 10K, 50K, 100K, 200K, 500K. Does the leading coefficient drift?
```

## Published Papers

- [Cognitive Camouflage: Specification Gaming in LLM-Generated Code Evades Holistic Evaluation but Not Adversarial Execution](papers/paper1/draft.md) | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960)
- [Adversarial Precedent Memory: Hardening LLM Evaluators Through Mined Failure Constraints](papers/paper2/draft.md) | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6525598)
- [Contract-Governed Adversarial Evaluator Hardening: Stage-Gated Recursive Improvement with Typed Promotion Contracts](papers/paper3/draft.md) | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6542998)
- [The Cognitive Firm: Managerial Capitalism for Artificial Intelligence](papers/paper4/draft.md) | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019)
- *The Principles of Epistemic Verification: How Judgment Decomposes, and What Does Not* (work in progress)
- *Automated Asymptotic Discovery via Adversarial Compression* ([papers/experimental_math_letter/main.tex](papers/experimental_math_letter/main.tex)) -- submitted to Experimental Mathematics

Each paper bundle includes the public manuscript sources under `papers/`.

---

## Engine Track Record

Empirical results the apparatus has produced across 11+ substrates,
classified honestly against a cold zero-shot LLM null. Detailed
per-substrate documentation lives in
[`research_areas/private/philosophy/cognitive_gym.md`](research_areas/private/philosophy/cognitive_gym.md)
(Part 5), the per-project `champion_eval_results.json` files, and the
2026-04-25 novelty audit + cold-LLM null tests at
`research_areas/private/seams/2026_04_25_novelty_audit_vs_cold_llm.md`
and `research_areas/private/seams/cold_llm_null_*.md`.

### Headline — apparatus-reproducibility evidence

The single strongest piece of evidence for what ZTARE adds beyond an
unconstrained LLM is the cross-family matched-pair on a novel substrate:

| Substrate | Cross-family pairing | Same-family pairing | Outcome |
|---|---|---|---|
| gp159 (`retrieval_trap`) | gemini-pro mutator + gpt-4.1 judge → **93** | claude-opus mutator + gpt-4.1 judge → **90** | Matched-pair convergence within 3 points on identical substrate across two independent LLM families. A cold-shot of either model on the same problem does NOT converge to the same answer. The convergence is the apparatus's contribution, not the LLM's. |

### Apparatus-original findings (cold zero-shot LLM cannot reproduce)

These survived the cold-LLM null test at
`research_areas/private/seams/cold_llm_null_*.md`. A fresh GPT-5 / Opus
/ Gemini-Pro tier model, given only the substrate's cold-variable
problem statement, either punted, said "I don't know," or assembled
only a partial sketch with explicit concessions.

| Substrate | Apparatus output | Why a cold LLM cannot produce it |
|---|---|---|
| gp145b — SAW μ_square closed-form null (score 48) | Rigorous null-result theorem: no closed form exists for μ ≈ 2.638158 in `Δ₀_small = {1, π, √2, √3, ln 2}` at integer-coefficient height H ≤ 10⁸, dimension d ≤ 2 | Cold LLM punted: *"can't construct a constructive null without empirical PSLQ at 25-40 digits."* The apparatus actually ran the empirical PSLQ trajectories and constrained to a smaller dictionary where the κ-bound is provable. |
| gp145 — SAW PSLQ κ̂-bound (score 56) | Empirical κ̂-bound theorem with 6 independent PSLQ runs giving p < 10⁻¹¹⁵ via Bailey-Ferguson 2⁻⁶⁴ stacking | Cold LLM produced only a **partial sketch with concessions**: *"q is hand-set, runs not statistically independent, theorem assembled not recalled."* |
| gp146 — Arnold Cat Map gate-stack discrimination (score 92) | Apparatus gate stack (G1-G8 + G-CIRC + G-FALSIFY) correctly distinguishes the true Lyapunov exponent from inverter-planted false-positives | Value `λ₁ = log((3+√5)/2)` is textbook (cold LLM nails it instantly). The **gate-stack discrimination claim** cannot be reproduced by a cold LLM — it requires running the gates against adversarially planted candidates. |
| A000959 — Lucky numbers validity horizon | Log-asymptotic fit at n ≤ 50K, validity drift detected at n = 500K, (log n)² correction term | Cold LLM got the leading n log n asymptotic but **explicitly answered "I don't know"** on the drift scale and correction term. No published source for the validity horizon. |
| gp154 — neural-scaling-law bounded null with form-class robustness | Best 5-fold stratified CV MRE = **1.6355** across 13 hand-authored forms in 6 hypothesis families the autonomous mutator never tried. Statistically indistinguishable from the constant predictor (1.6860). | The bounded-null + form-class enumeration requires systematic empirical work across 13 forms. A cold LLM cannot generate "the K ≤ 7 wall is robust to form-class augmentation" as a one-shot claim. (Charter caveat: v4 conversion-transform reframe is exploratory pending external T14 holdout.) |

### Calibration recoveries (LLM training-data-known forms recovered under cold-variable rigor)

These are honest calibration results, NOT discoveries on dark domains.
A cold zero-shot LLM, given the cold-variable problem statement,
produces the same answer in seconds. The apparatus's contribution is
**reproducibility under cold-variable rigor**, NOT novelty of the form.
Useful as competence baselines; should not be presented as discoveries.

| Substrate | Recovered form | Cold-LLM verdict |
|---|---|---|
| GP-088 — partition function p(n) | sqrt + log (Hardy-Ramanujan family) | Hardy-Ramanujan asymptotic is textbook (1918). |
| A000009 — Q(n) | sqrt + log | Same family, textbook. |
| A000607 — sums of distinct prime parts | sqrt(n / log(n)) | Standard partition asymptotic. |
| A001156 — partitions into squares | n^(1/3) + log | Standard. |
| A002865 — partitions with no part = 1 | sqrt + log | Standard. |
| KWW — polymer relaxation | exp(-b · t^c) | Cold LLM nails this instantly from the Weibull-plot slope alone. **"Suitable as a null baseline for any discovery-framework claim of 'finding' KWW."** |
| sandbox_20 — real polymer (`t^(-B) · exp(-Ct)`) | t^(-B) · exp(-Ct), externally validated by domain practitioner | The form is in the published literature; external validation is rigor, not novelty. |

The partition-family recoveries (GP-088, A000009, A000607, A001156,
A002865) are best read as *the apparatus correctly recovers the
Hardy-Ramanujan asymptotic family from raw OEIS data under cold
variable names with zero false families across 5 substrates.* That's
defensible as competence/calibration evidence; it is NOT a discovery
on a dark domain.

### Correct refusals (apparatus says "I cannot compress this")

These are apparatus-original because cold LLMs do not refuse on novel
data — they hallucinate plausible-sounding answers.

| Substrate | Reason for refusal |
|---|---|
| A002858 — Ulam | UNDERIDENTIFIED + non-stationary, anti-persistent residuals |
| DFDO — two-regime test | Refused single-regime fit; correctly identified the topology-induction gap |

### Honest novelty audit verdict (2026-04-25 + cold-LLM null tests)

Across ~32 audited findings:

| Bucket | Share | Examples |
|---|---|---|
| A — Pure recital | ~10% | KWW polymer (cold LLM matches in one shot from Weibull slope alone) |
| B — Recital + rigor | ~50% | Partition family, Arnold Cat Map *value*, sandbox_20 polymer form |
| **C — Apparatus-only** | **~30-35%** | gp159 matched pair, gp145/gp145b SAW null, gp146 gate-stack discrimination, Lucky-number validity horizon, gp154 bounded null, correct refusals (Ulam, DFDO) |
| D — Indeterminate | ~5% | Awaiting cold-LLM tests on remaining substrates |

The apparatus's distinctive value is the **~30-35% Bucket C** core,
not the calibration recoveries. The headline reproducibility claim
should lead with gp159's cross-family matched pair; the calibration
table is provided for transparency, not as discovery evidence.

---

For domain projects, the validator writes explicit `latest_*` and `champion_*` artifacts so operators can distinguish:

- the newest evaluated attempt
- the currently promoted best result for the active regime

---

## Repository Scope

The public repo currently has six active surfaces:

1. the adversarial validator and workspace pipeline
2. a Karpathy-inspired LLM knowledge workspace ([design pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) that accumulates source material upstream of the validator
3. the synthesis / distribution pipeline
4. the hardening / control-plane stack (supervisor + goal orchestrator)
5. the evidence compiler (`compile_evidence.py`) with `source_type_map.json` support for typing raw sources without modifying their content
6. the science track: autonomous asymptotic discovery via `make discover` (hypothesis loop, template compression, Lean proof stubs)

Useful entry points:

- `docs/guides/workflow.md`
- `docs/concepts/architecture.md`
- `supervisor/USER_MANUAL.md`

## Layer Glossary

Six layers, each with a distinct job. See [docs/concepts/glossary.md](docs/concepts/glossary.md) for the full term list.

1. **Knowledge Workspace**: a persistent upstream memory layer inspired by [Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): raw sources accumulate, an LLM extracts structured notes, and a compiler emits bounded evidence snapshots for the validator. The workspace remembers; the validator does not.
2. **Validator**: the adversarial loop (mutator vs. verification panel vs. judge) that runs and scores claims
3. **Kernel**: the scoring and evaluation logic being continuously hardened against gaming
4. **Meta-runner**: the deterministic promotion system for kernel improvements (not the validator)
5. **Supervisor**: the work-management layer that routes tasks, tracks progress, and enforces budgets (does not decide truth). Organized as three sub-layers: **OS** (state machine driver with hard gates), **Config** (typed goal-lifecycle contracts), and **App** (agent runtime within fences)
6. **Papers**: public-facing manuscripts under `papers/`

These are separate concerns. The supervisor manages work; the validator decides truth. Don't use them interchangeably.

### Goal Orchestrator (GP-070)

The supervisor includes a goal orchestrator that tracks active goals in `AGENTS.md` and routes agent work through typed lifecycle stages (e.g., `RUNNING`, `CLOSED`). Goals are advanced via `python -m src.ztare.orchestration.cli goal advance <slug>`. The orchestrator sits in the Config layer. It defines the goal contract but does not replace the OS state machine or the App agent runtime.

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

## Science Track

The science track runs ZTARE as an automated asymptotic discovery engine. Given unlabeled numerical data, it estimates the functional form, compresses to the minimal template that survives holdout gates, and optionally generates Lean 4 proof stubs.

### Full autonomous pipeline

```bash
# Discover the asymptotic law for integer partitions (calibration target)
make discover PROJECT=gp088_calibration_a01 RUBRIC=gp088_calibration_a01 ITERS=15

# Discover the asymptotic law for Lucky numbers (prospective target)
make discover PROJECT=oeis_a000959 RUBRIC=oeis_a000959 ITERS=15
```

`make discover` runs three phases:
1. **Phase 1 (hypothesis loop):** LLM proposes functional forms, SciPy fits parameters, holdout gates enforce generalization. 15 iterations.
2. **Phase 2 (compression):** Template enumeration (22 additive + 13 compositional templates) strips overparameterized surrogates to the minimal gate-passing form. Selection by BIC. No LLM in the loop.
3. **Phase 3 (Lean stubs):** Generates Lean 4 proof obligations from gate results. PSLQ maps fitted floats to exact mathematical constants.

### Individual phases

```bash
make loop PROJECT=oeis_a000959 RUBRIC=oeis_a000959 ITERS=15   # Phase 1 only
make compress PROJECT=oeis_a000959                              # Phase 2 only
make prove PROJECT=oeis_a000959                                 # Phase 3 only
```

### Track record (10 substrates, zero false positives)

| Substrate | Result | Leading coefficient |
|-----------|--------|-------------------|
| A000041 (partitions) | sqrt+log, ALL PASS | a=2.631 (theory: pi*sqrt(2/3)=2.565) |
| A000009 (distinct parts) | sqrt+log, HO PASS | a=1.813 (theory: pi/sqrt(3)=1.814) |
| A000959 (Lucky numbers) | log+1/n, ALL PASS | **a=1.200 (unpublished estimate)** |
| A000607 (prime parts) | sqrt(n/log(n)), ALL PASS | Compositional Stage 2 |
| A001156 (square parts) | n^(1/3)+log, topology ID | b=0.335 (theory: 1/3) |
| A002858 (Ulam) | UNDERIDENTIFIED | Correct refusal (oscillatory) |
| KWW (polymer decay) | exp(-b*t^c), ALL PASS | c=0.630 |
| sandbox_20 (real polymer) | t^(-B)*exp(-Ct) | B=0.433 (theory: 2/5) |

### Evidence preparation

Each science project needs three evidence files:

```
projects/<name>/evidence.txt              # visible (fit window)
projects/<name>/evidence_holdout.txt      # holdout (generalization test)
projects/<name>/evidence_farther_tail.txt # farther-tail (extrapolation test)
```

Format: tab-separated `n\tz` pairs with `#` comment header. The variable name and evidence splits are sealed before any iteration runs.

---

## Legacy Benchmark Shortcuts

The legacy *Cognitive Camouflage* benchmark shortcuts are:

```bash
make paper1-tsmc-legacy
make paper1-epistemic-legacy
```

These preserve the same project/rubric/model pairings as the prior root-script commands.

---

## Synthesize a Project into a Founder Memo or Architectural Brief

After the adversarial loop runs, `src/ztare/synthesis/synthesize.py` compresses the debate history, thesis, and evidence into a clean, audience-appropriate artifact.

It runs as a post-processing step and produces four outputs:
- `synthesis/history_summary.json`: recurring survivors, failures, and noise labels across all runs
- `synthesis/ledger.json`: canonical extraction of all high-signal conclusions
- `synthesis/brief.json`: audience-specific salience plan (what to emphasize, in what order)
- `Report.md`: the final artifact, written from the brief and gated by a QA check

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

The renderer type is inferred automatically from the project type. To add a new renderer, run with an unknown `--renderer-type`; the system generates a suggested prompt at `config/renderers/<type>.md`, stops, and lets you review it before use.

---

## Shortcuts

For common tasks, use:

```bash
make help
make workspace-update PROJECT=<project> MODEL=gemini
make evidence-compile PROJECT=<project> MODEL=gemini
make loop PROJECT=<project> RUBRIC=<rubric> ITERS=10 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
make synth PROJECT=<project> MODEL=gemini QA_MODEL=claude RENDERER=founder_memo
make discover PROJECT=<project> RUBRIC=<rubric> ITERS=15  # Full autonomous pipeline
make compress PROJECT=<project>                          # Compression only (Phase 2)
make prove PROJECT=<project>                             # Lean stubs only (Phase 3)
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
benchmarks/                           # Adversarial Precedent Memory evaluator hardening benchmark suites and runs
global_primitives/                    # Primitive mining, review, and approved precedent memory
papers/
  paper1/                             # Cognitive Camouflage (public source bundle)
  paper2/                             # Adversarial Precedent Memory (public source bundle)
  paper3/                             # Contract-Governed Evaluator Hardening (public source bundle)
  paper4/                             # The Cognitive Firm (public source bundle)
paper1/                               # local scratch workspace (gitignored)
paper2/                               # local scratch workspace (gitignored)
paper3/                               # local scratch workspace (gitignored)
paper4/                               # local scratch workspace (gitignored)
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
| `GEMINI_API_KEY` | Mutator + Verification Panel (required) |
| `ANTHROPIC_API_KEY` | Claude-as-judge in baseline/camouflage experiments (optional) |

Get a Gemini key at [aistudio.google.com](https://aistudio.google.com). Gemini 2.5 Flash is free tier eligible.

---

## What's Actually In This Repo Now

The public work is no longer a single "does gaming exist?" claim. It is a five-paper stack plus the engine that produced it.

- **Cognitive Camouflage.** Specification gaming in LLM-generated code evades holistic evaluation but not adversarial execution. Cross-mutator replication across Gemini, Claude, and GPT-4o (all judged by Gemini). Establishes that gaming is a reproducible property of the loop topology, not an artifact of one model family.
- **Adversarial Precedent Memory.** Evaluator hardening via mined failure constraints, benchmarked across soft judge (`A`), deterministic gates (`B`), gates-plus-primitives (`C`), and crux-first ablation (`C2`). Shows that reusable, defeasible precedents transfer across exploit families.
- **Contract-Governed Evaluator Hardening.** Stage-gated recursive improvement with typed promotion contracts. Six kernel stages plus a Stage 2→4 bridge, each with its own deterministic gate. This is the kernel-hardening spine.
- **The Cognitive Firm.** Managerial capitalism for AI: the M-form governance layer (supervisor + program manifests + human gates) that sits on top of the kernel, with constrained self-hosting as the distinguishing architectural claim.
- **The Principles of Epistemic Verification.** The operational companion to *The Cognitive Firm*: ten named operations that decompose "senior review," seven structural principles, a three-tier epistemological ledger, and a bounded residual of three commitments that resist decomposition. Work in progress.

What this means for different readers:

- if you want to **use the engine**, everything from *Cognitive Camouflage* is downstream of the validator and synthesis you already get in the Quickstart below. You do not need to read the later papers to run a domain project.
- if you want to **extend the engine**, *Adversarial Precedent Memory*, *Contract-Governed Evaluator Hardening*, and *The Cognitive Firm* describe the hardening, primitive, and control-plane layers in the same order they sit in the codebase

This is a single-principal, single-system research program (N=1 by construction). The claims are scoped to that.

---

## Reflexive Engineering: Primitives for Any LLM Workflow

ZTARE rests on three principles: Invert (falsification is cheaper than construction), Compress (asymptotic survival, not parameter count), and Adversarial Disagreement (truth survives structured disagreement). These were derived for the science the engine does — evaluating candidate models, testing claims, detecting gaming.

The reflexive engineering primitives are what happens when you apply those same principles to the engine itself. Each primitive is a specific instance of a ZTARE principle turned inward. **These primitives are domain-general — they apply to any LLM agent workflow, not just ZTARE.**

| Primitive | Principle | What it solves | Any-LLM applicability |
|-----------|-----------|---------------|----------------------|
| **Token-Optimized Self-Modeling** | Compress | Partial-view mistakes on large files | Any agent reading codebases through narrow context windows |
| **Inception Pattern** | Invert | Agent edits without understanding the validation cage | Any agent modifying systems with constraints it doesn't see |
| **Hybrid Persona Router** | Disagreement | Fixed reviewer personas miss failure families | Any multi-agent review system |
| **Residual Isomorphism** | Compress + Invert | Grammar ceiling blocks discovery | Any symbolic regression or form-search system |
| **Reflexive Orchestration** | Disagreement + Compress | Workflow friction accumulates silently | Any agent-operated pipeline with recurring tasks |
| **Procedural Self-Audit** | Compress + Invert | Agents skip procedural steps under context pressure | **Any LLM agent workflow with defined procedures** |

### Procedural Self-Audit (Primitive 6) — the most transferable

LLM agents systematically skip procedural steps. Not from inability — from procedural drift under context pressure. "Try harder" doesn't fix systematic failures; a deterministic check does.

The pattern: the agent declares a typed task (experiment, substrate build, paper edit), the validator prints the required checklist, the agent executes, the validator checks completion before the agent declares done.

```bash
# Before starting: what steps does this task type require?
python scripts/validate_agent_task_discipline.py pre experiment_run

# After finishing: did I complete all required steps?
python scripts/validate_agent_task_discipline.py post experiment_run

# Audit a full session for incomplete tasks
python scripts/validate_agent_task_discipline.py audit
```

Six task types with typed pre/post checks: `experiment_run`, `substrate_build`, `paper_edit`, `seam_update`, `recording`, `infrastructure`. Each derived from standing rules in [AGENTS.md](AGENTS.md).

Full details: [docs/concepts/reflexive_engineering.md](docs/concepts/reflexive_engineering.md)

### Organizational Primitives (Paper 4: The Cognitive Firm)

A separate set of primitives governs how multiple agents coordinate without dissolving the governance layer. These instantiate Paper 4's M-form architecture — the same way the reflexive primitives above instantiate Paper 5's decomposition.

| Primitive | Biological analog | What it does |
|-----------|------------------|-------------|
| **Damage signals** | Matzinger danger model | Typed "something went wrong" channel; any code emits, supervisor reads |
| **Session claims** | Membrane exclusion | When two agents could act on the same task, one claims it; the other defers |
| **M-Form alignment audit** | Immune self/non-self | Stochastic audit of high-scoring outputs against original intent, blinded to scoring rubric |
| **Closure map** | Kauffman autocatalytic sets | Enumerate the workflow; flag steps with only one qualified agent |

Full details: [docs/concepts/organizational_primitives.md](docs/concepts/organizational_primitives.md)

---

## Collaboration

The most useful outside engagement for this repo is not generic feedback. It is one of:

- independent replication on new domains
- adversarial review of evaluator-hardening claims
- careful criticism of the evidence and forecast workflow
- collaboration on synthesis, distribution, or benchmark design

Best starting points:

- `docs/concepts/architecture.md`
- `docs/guides/workflow.md`

If you are reaching out about a specific claim, benchmark, or failure mode, include the exact project, rubric, and artifact path.

---

## Intellectual Lineage

ZTARE builds on ideas from several sources that shaped its architecture:

- **Andrej Karpathy's LLM wiki pattern** ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)): the upstream knowledge workspace that accumulates structured source material before the validator runs. The workspace remembers; the validator does not.
- **Andrzej Odrzywołek's EML primitive**: `eml(x,y) = exp(x) - ln(y)`, a single binary operator that [generates all elementary functions](https://arxiv.org/abs/2603.21852) (Odrzywołek, 2026). In ZTARE, this removes the mutator's regression-toolbox comfort bias by replacing familiar named functions with a uniform compositional grammar: `S -> 1 | eml(S,S)`. Used in expression grammars for curve-fitting sandboxes.
- **Charlie Munger / Poor Charlie's Almanack**: inversion ("tell me where I'm going to die, so I don't go there"), anti-self-deception, circle of competence, and checklist discipline. These are not decorative references. They are load-bearing in ZTARE's architecture. The holdout gate is inversion applied to validation. The adversarial debate loop is a checklist against self-congratulatory convergence.
- **Karl Popper**: ZTARE's deepest claim is that it makes falsification cheap. The holdout gate is a Popperian falsification instrument: a hypothesis that survives is not confirmed, merely not yet refuted.
- **Richard Feynman**: "The first principle is that you must not fool yourself — and you are the easiest person to fool." The Feynman Wall (library exhaustion boundary) is named after this principle. When the engine hits the wall, it reports the failure honestly rather than hallucinating epicycles.

---

## License

This repository uses a split license:

**MIT License** — the research engine, validator, fit primitives, synthesis pipeline, and all scientific tooling.
Covers: `src/ztare/validator/`, `src/ztare/fit/`, `src/ztare/synthesis/`, `src/ztare/scaffold/`, `src/ztare/gates/`, `src/ztare/composition/`, `src/ztare/formal/`, `src/ztare/workspace/`, `papers/`, `docs/`, `rubrics/`, `projects/`, `scripts/` (except `agent_daemon.py`).

**Business Source License 1.1** — the governance kernel: organizational primitives, damage signals, session management, notifications, agent daemon, and mandate infrastructure.
Covers: `org/`, `src/ztare/signals/`, `src/ztare/sessions/`, `src/ztare/roles/`, `src/ztare/notifications/`, `src/ztare/orchestration/`, `src/ztare/cli_org.py`, `scripts/agent_daemon.py`, `deploy/`.

The BSL permits free use, modification, and non-production deployment. Production use that competes with the licensor's offerings requires a commercial license. The BSL converts to Apache 2.0 after four years. See [LICENSE](LICENSE) (MIT) and [LICENSE-BSL](LICENSE-BSL) for full terms.

**Why the split:** The research engine is a scientific instrument — it should be freely available for replication, extension, and criticism. The governance kernel is organizational infrastructure with commercial value — it solves the "how do you safely run autonomous AI agents?" problem that every company deploying agents will face. The split lets researchers use everything freely while preserving a commercial lane for the governance layer.

For commercial licensing inquiries: daniel@figs.ai

---

## Support This Work

This is an independent research project built and funded by a student. If you find it useful, consider supporting it:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/sparckix)

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
