# ZTARE Quickstart

Two-page orientation for a new operator. Assumes you have API keys for at least one LLM (Claude, Gemini, GPT-4). Full reference: `docs/guides/workflow.md` and `docs/concepts/glossary.md`.

---

## What ZTARE Does in One Sentence

ZTARE runs an LLM inside a constrained validation loop. The LLM proposes hypotheses, deterministic gates accept or reject them, and failure signals drive the next proposal. The LLM never touches arithmetic or geometric characterization; the cage handles those.

---

## Two Ways to Use It

### A. Test a thesis or claim (domain project)

You have a question ("Is this startup overvalued?", "What drives EU stability?"). ZTARE runs an adversarial loop that forces the LLM to propose, test, and revise a thesis under gate pressure.

```bash
# 1. Put your evidence in projects/<project>/evidence.txt
# 2. Write or generate a rubric
# 3. Run
make loop PROJECT=<project> RUBRIC=rubrics/<rubric>.json ITERS=10 \
    MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gpt4.1
```

### B. Recover a mathematical law from data (science experiment)

You have input-output data. ZTARE tries to find the closed-form law that generated it. Two options:

**Fully autonomous (recommended for OEIS and 1D sequences):**

```bash
make discover PROJECT=<slug> RUBRIC=<slug> ITERS=15
```

This runs Phase 1 (hypothesis loop), Phase 2 (template compression), and Phase 3 (Lean stubs) end to end.

**Manual control (for multi-variable or custom substrates):**

```bash
# See §§ below for full command sequence
make loop PROJECT=<slug> RUBRIC=<slug> ITERS=10 \
    MUTATOR_MODEL=gpt4.1 JUDGE_MODEL=gpt4.1
```

---

## Five-Minute Setup: Science Experiment

### Prerequisites

```bash
export GEMINI_API_KEY=...
export OPENAI_API_KEY=...    # for gpt4.1 judge
export ANTHROPIC_API_KEY=... # for claude judge (optional)
```

### Step 1: Write the ground truth script

```python
# src/ztare/substrates/my_experiment_gt.py
import math

_A, _B = 2.5, 0.3

def f_true(x1: float, x2: float) -> float:
    return _A * math.exp(-_B * x1) * x2

def f_dominant(x1: float, x2: float) -> float:
    return f_true(x1, x2)   # use f_true if no simpler dominant term

def evidence_grid() -> list[tuple[float, float]]:
    """Visible training points: list of (x1, x2) pairs."""
    times = [0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 24.0]
    doses = [1.0, 2.0, 3.0]
    return [(t, d) for t in times for d in doses]

def holdout_grid() -> list[tuple[float, float]]:
    """Hidden evaluation points: never shown to mutator."""
    times = [1.5, 3.0, 5.0, 9.0, 16.0]
    doses = [1.5, 4.0]
    return [(t, d) for t in times for d in doses]
```

**Key rules:**
- Slug must be opaque (`exp01`, not `exp_decay_01`): the slug leaks into mutator-visible files
- Name variables `x1, x2` (or `n` for 1D integer sequences): domain names like `time`, `dose` are semantic hints
- `f_true` computes GT; `evidence_grid`/`holdout_grid` define data partitions

### Step 2: Generate substrate

```bash
make generate-substrate \
    SLUG=exp01 \
    GT_SCRIPT=src/ztare/substrates/my_experiment_gt.py \
    VARIABLES=x1,x2 \
    PROBLEM_BRIEF="Find a mathematical law governing z as a continuous function of two inputs x1 and x2."
```

This creates:
- `projects/exp01/evidence.txt`: visible data (mutator sees this)
- `projects/exp01/evidence_holdout.txt`: held-out data (gated)
- `projects/exp01/gate_harness.py`: RMSE evaluator
- `projects/exp01/test_model.py`: mutator rewrites this each iteration
- `rubrics/exp01.json`: rubric
- `src/ztare/substrates/exp01_gt.py`: opaque re-export stub

### Step 3: Check the RMSE gate rejects the zero model

```bash
python projects/exp01/gate_harness.py --run-smoke-test
```

`harness_ok` must be `false` on the blank `test_model.py`. If it's `true`, tighten `_RMSE_THRESHOLD` in `gate_harness.py` and in `rubrics/exp01.json` (`fit_rmse_threshold`). For noiseless synthetic data, `0.05` usually works.

### Step 4: Seal

```bash
make seal PROJECT=exp01 RUBRIC=rubrics/exp01.json
```

Must see `SENTINEL PASSED` and `SEALED`. Do not proceed without a clean seal.

### Step 5: Run

```bash
make experiment-loop \
    PROJECT=exp01 \
    RUBRIC=rubrics/exp01.json \
    ITERS=10 \
    MUTATOR_MODEL=gemini-pro \
    JUDGE_MODEL=gpt4.1
```

---

## Five-Minute Setup: Domain Thesis

Use `generate-gp` to scaffold a qualitative project with correct gate configuration and an LLM-drafted rubric.

```bash
make generate-gp \
    PROJECT=my_project \
    BRIEF="Your one-paragraph thesis question here — be specific about domain and claim direction" \
    JUDGE_MODEL=gpt4.1
```

This creates:
- `projects/my_project/evidence.txt`: blank evidence file (edit directly, or compile from `raw/`)
- `projects/my_project/raw/`: drop source documents here for `make evidence-compile`
- `projects/my_project/thesis.md`: seeded thesis template
- `projects/my_project/project_charter.md`: auto-drafted from your brief
- `rubrics/my_project.json`: LLM-drafted adversarial persona + criteria, with all qualitative gate opt-outs pre-filled

**Important:** Review and edit `rubrics/my_project.json` before sealing — the LLM draft is a starting point, not a final rubric. Check that the persona is genuinely adversarial for your domain.

```bash
# Option A: Add evidence directly
# Edit projects/my_project/evidence.txt

# Option B: Compile from raw documents
cp my_report.pdf projects/my_project/raw/
make evidence-compile PROJECT=my_project MODEL=gpt4.1

# Then seal and run
make seal PROJECT=my_project RUBRIC=rubrics/my_project.json
make loop PROJECT=my_project RUBRIC=rubrics/my_project.json ITERS=10 \
    MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gpt4.1
```

**Why not `mkdir` + manual rubric?** Qualitative projects require three gate opt-out keys (`farther_tail_region: null`, `disable_evidence_fit_gate`, `disable_uniqueness_gap_gate`) that are non-obvious and whose absence causes hard fails that look like scoring failures. `generate-gp` pre-fills them.

---

## Model Options

| Role | Recommended | Alternative |
|---|---|---|
| Mutator | `gemini-pro` | `claude-opus-4-6`, `gpt4.1` |
| Judge | `gpt4.1` | `gemini-pro`, `claude-sonnet-4-6` |

Gemini Pro as mutator + GPT-4.1 as judge is the default pairing. Cross-family pairing (different model families) reduces correlated blind spots.

---

## Reading the Output

Each iteration prints:

```
Iteration N, score: XX
  Gate: harness_ok = true, rmse = 0.031
  Information yield: [...]
  Component C: [shape hint]
```

Key signals:
- **Score 0 with `harness_ok=false`**: gate fired; model is wrong, loop continues searching
- **Score 0 with `harness_error`**: infrastructure bug; check imports, fix before rerunning
- **Score stagnant for 3+ iters**: stagnation pivot fires automatically
- **FEYNMAN WALL**: all 32 library primitives exhausted; Component D composition mode activates

---

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `No module named 'src.ztare.substrates.<slug>_gt'` | GT stub not created | Run `make generate-substrate` again; stub now auto-created |
| `harness_ok=True` on blank model | RMSE threshold too loose | Tighten `_RMSE_THRESHOLD` in gate_harness.py and rubric |
| `--reviewer-domains` crash | Passed to loop instead of findings runner | Remove from `make experiment-loop`; routing is automatic via `latent_distance.jsonl` |
| Score 0 every iteration | Hard gate too tight OR zero model passes | Check gate calibration; check evidence float parsing |
| Seal fails sentinel | Domain name leaked into mutator-visible file | Audit evidence.txt, charter, rubric for biological/domain terms |

---

## Where Things Live

```
projects/<slug>/          ← per-run artifacts (evidence, gate harness, test_model)
rubrics/<slug>.json       ← scoring rubric (GT-blind)
src/ztare/substrates/     ← GT scripts (Division A, private)
research_areas/private/   ← seams, specs, boards (private)
docs/                     ← operator docs (this file)
config/prompts/           ← reviewer domain personas
```

---

## Next Steps

- Full workflow reference: `docs/guides/workflow.md` §16
- Division A/B protocol deep-dive: `docs/guides/workflow.md` §12
- Architecture overview: `docs/concepts/architecture.md`
- Glossary: `docs/concepts/glossary.md`
- Cognitive Gym (why the cage works): `research_areas/private/philosophy/cognitive_gym.md`
- Three Legs of ZTARE (core philosophy): `research_areas/private/philosophy/three_legs_of_ztare.md`
- Operational Manual: `research_areas/private/philosophy/operational_manual_substrate_construction.md`
- Experiment track record: `research_areas/EXPERIMENT_TRACK_RECORD.md`
