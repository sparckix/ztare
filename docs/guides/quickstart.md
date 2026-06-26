---
description: "Two-page orientation for a new reviewer."
---

# ZTARE Quickstart

> Up: [Documentation map](../README.md)

Two-page orientation for a new reviewer. Start with
[first-30-minutes.md](first-30-minutes.md) if this is your first time in the
repo. This page is the fast path for running ZTARE after you know which route
you want. Full reference: `docs/guides/workflow.md` and
`docs/concepts/glossary.md`.

---

## What ZTARE does in one sentence

ZTARE is a zero-trust claim-governance workbench. It turns local sources and a
bounded claim into an inspectable verdict, then separates proposals from
critique, deterministic gates, ledgers, review artifacts, and non-claims.

## First value check

Before choosing a workflow, run the smallest offline demo:

```bash
make hello
```

Expected result: a ready project-intake file validates, its missing-reference
falsifier blocks a simulated missing evidence artifact, a malformed intake file is
blocked before in-loop routing, and an overbroad claim is demoted to bounded
wording with missing evidence and a next falsifier. In one command, plausible
output must survive separate evidence surfaces before it becomes a public
claim.

For the full offline public review path, run:

```bash
make first-run
```

That aggregate target chains the value demo, gaming-catalog audit,
benchmark-evidence checks, the frozen evaluator-hardening proof-point check,
claim-boundary audit, terminology audit, public smoke, adversarial entry-path
checks, and docs checks. The catalog audit checks that the public gaming
catalog, live registry, promotion evidence, hardening map, and executable
fixture anchors agree.

---

## Three ways to use it

### A. Test a bounded claim (in-loop autoresearch)

You have a question ("Is this startup overvalued?", "What drives EU stability?").
Start by writing the boundary object: bounded task, claim, sources, evidence,
non-claims, and next falsifier. Then inspect readiness before launching the
loop.

```bash
# 1. Guided intake setup. The JSON includes prep, trace, and in-loop phases.
ztare project walkthrough --project <project> --rubric <rubric> \
  --task "<bounded task>" \
  --bounded-claim "<claim the loop may evaluate>" \
  --source-ref "<source ref>" --evidence-ref "<evidence artifact>" \
  --non-claim "<what this intake file does not prove>" \
  --next-falsifier "<test that could demote the claim>" \
  --intake-out <project>_intake.json --json

# Equivalent explicit intake creation command.
ztare project intake create --path <project>_intake.json \
  --project <project> --rubric <rubric> --task "<bounded task>" \
  --bounded-claim "<claim the loop may evaluate>" \
  --source-ref "<source ref>" --evidence-ref "<evidence artifact>" \
  --non-claim "<what this intake file does not prove>" \
  --next-falsifier "<test that could demote the claim>" \
  --expected-command "ztare autoresearch route --task '<bounded task>' --project <project> --rubric <rubric>"
ztare project intake validate --path <project>_intake.json

# 2. Inspect readiness and the no-model-call plan preview.
ztare autoresearch trace --project <project> --rubric <rubric> --intake <project>_intake.json --json

# 3. Run plan_preview.recommended_first_command.
# Before a fresh admission, this is the no-model-call preflight:
ztare autoresearch run --project <project> --rubric <rubric> \
    --intake <project>_intake.json --preflight-only

# After a fresh admission, trace advances the recommended command to the bounded run:
ztare autoresearch trace --project <project> --rubric <rubric> --intake <project>_intake.json --json
ztare autoresearch run --project <project> --rubric <rubric> \
    --intake <project>_intake.json --iters 10 \
    --mutator gemini-pro --judge gpt4.1 --inverter claude
```

After the preflight command, the trace JSON should include `loop_admission`.
That receipt tells you whether the current intake bytes still match the intake
admitted by the loop, and whether the current run-readiness contract still
matches the admitted entry digest.

Model aliases are listed in
[`docs/reference/model_aliases.md`](../reference/model_aliases.md). The runtime
currently supports Google, Anthropic, OpenAI, DeepSeek, Kimi/Moonshot, and
Grok/xAI API providers, plus subscription-worker dispatch at selected call
sites. For consequential runs, use a cross-family mutator/judge pair and set
`--inverter <model>` explicitly when the post-champion falsifier should avoid
the historical `gpt4.1` default. Add `CROSS_FAMILY=1` when shared-provider
evaluation should fail before any model call.

If the project already exists locally, intake validation also checks the
offline raw/source typing preflight. Add `--source-preflight` when you want the
intake file to require a source surface before validation can pass. Intake enqueue
always requires that local source surface. Use the prep ledger when source
files or typing still need work.

### B. Create or probe a project/data surface
You have a project surface, review artifact, decision process, or input-output
data. ZTARE searches for candidate forms, bounded claims, or justified nulls
under gates. It does not promote a result without separate source-readiness,
non-claim, and falsifier discipline.

For a source-ingest project, start with the source initializer. It creates the
portable `raw/` and `workspace/` directories plus an empty
`raw/source_type_map.json`, but does not create evidence or launch the loop:

```bash
ztare project source-init --project <slug> --rubric <slug>
ztare project source-check --project <slug> --json
ztare project source-index --project <slug> --json
```

Put text-like source files under `projects/<slug>/raw/`. Mark each source with
`source_type` frontmatter or `raw/source_type_map.json`; use
`source_evidence` for sources allowed to support immutable facts and
constraints.
Run `source-check` again after adding or renaming raw files. It is an offline
preflight (it does not compile evidence). `source-index` writes the deterministic
workspace source index, metadata, and receipt without model calls.
`make evidence-prepare` runs the same preflight before workspace update and
evidence compilation.

For a generated numeric/data project, use `new`. `prepare` runs the standard
setup pipeline before any in-loop run:

```bash
ztare project new --help
ztare project prepare --project <slug> --rubric <slug>
ztare project seal --project <slug> --rubric <slug>
```

If a project surface still needs setup or reproduction prep before the
validation engine can evaluate it, create a project-intake file first.
`ztare project intake` is the preferred command; `ztare project packet` is the
legacy spelling for the same JSON. Use the intake ledger only when there is
follow-up prep to track. It is not an autoresearch scheduler.
For concrete fixtures, see
[examples/project_packets/](../../examples/project_packets/): one ready intake
file and one malformed intake file that must fail validation.

For a less toy example, try the synthetic operational-diagnosis pilot. It uses
local incident, metric, staffing, change, export-log, ticket-sample,
baseline, cache, and counter-hypothesis sources to test a bounded root-cause
claim. The fixture is not customer data. It is a public way to inspect the
claim/evidence/falsifier path and launch a one-iteration in-loop run.

```bash
ztare project walkthrough --ops-demo
ztare project source-check --project ops_root_cause_diagnosis_demo --json
ztare project source-index --project ops_root_cause_diagnosis_demo --json
ztare project intake validate \
  --path projects/ops_root_cause_diagnosis_demo/ops_root_cause_diagnosis_demo_intake.json
ztare autoresearch trace \
  --project ops_root_cause_diagnosis_demo \
  --rubric ops_root_cause_diagnosis_demo \
  --intake projects/ops_root_cause_diagnosis_demo/ops_root_cause_diagnosis_demo_intake.json \
  --brief
ztare autoresearch run \
  --project ops_root_cause_diagnosis_demo \
  --rubric ops_root_cause_diagnosis_demo \
  --intake projects/ops_root_cause_diagnosis_demo/ops_root_cause_diagnosis_demo_intake.json \
  --preflight-only
```

Expected trace shape: before any paid run, `readiness` should be
`ready_for_first_in_loop_run`, `kernel_entry.status=ready`, and the
`source_claim_graph` should validate. If run artifacts are already present,
the trace may instead report `complete_trace`. In that case inspect
`recent_loop` for the latest score, provider failures, and next command. After
the preflight command, `loop_admission` should verify the intake and
run-readiness hashes.

To exercise the validation engine with live model calls, run the exact command
stored in the intake file:

```bash
ztare autoresearch run \
  --project ops_root_cause_diagnosis_demo \
  --rubric ops_root_cause_diagnosis_demo \
  --intake projects/ops_root_cause_diagnosis_demo/ops_root_cause_diagnosis_demo_intake.json \
  --iters 1 --mutator kimi --judge grok --inverter deepseek \
  --llm-timeout-seconds 240 --llm-retries 1
```

That paid run uses a cross-family mutator/judge pair and keeps the post-champion
inverter off the historical `gpt4.1` default. It should stay bounded to the
fixture's non-claims and next falsifier. Provider failures are recorded in the
trace and stay there; the loop does not promote them as research results.

```bash
ztare project walkthrough --project <slug> --rubric <slug> \
  --task "<bounded task>" \
  --bounded-claim "<claim the validation engine may evaluate>" \
  --source-ref "<paper/code/source ref>" \
  --evidence-ref "<local evidence artifact>" \
  --non-claim "<what this intake file does not prove>" \
  --next-falsifier "<next test that could demote the claim>" \
  --intake-out <slug>_intake.json --json
ztare project intake create --path <slug>_intake.json \
  --project <slug> --rubric <slug> --task "<bounded task>" \
  --bounded-claim "<claim the validation engine may evaluate>" \
  --source-ref "<paper/code/source ref>" \
  --evidence-ref "<local evidence artifact>" \
  --non-claim "<what this intake file does not prove>" \
  --next-falsifier "<next test that could demote the claim>" \
  --expected-command "ztare autoresearch route --task '<bounded task>' --project <slug> --rubric <slug>"
ztare project intake validate --path <slug>_intake.json
ztare project intake validate --path <slug>_intake.json --source-preflight
ztare project intake enqueue --path <slug>_intake.json
```

If the intake file is blocked on concrete prep work, record that separately:

```bash
ztare project prep-ledger add --task "prepare minimal reproduction and cost estimate" \
  --kind minimal_reproduction --project <slug> --rubric <slug>
ztare project prep-ledger list
```

Then choose one of the run paths:

Guarded end-to-end path (legacy/demo path for OEIS and 1D sequences):

```bash
make discover PROJECT=<slug> RUBRIC=<slug> ITERS=15
```

This runs Phase 1 (hypothesis loop), Phase 2 (template compression), and Phase
3 (Lean gate artifacts) end to end. Treat the output as candidate evidence, not
autonomous discovery.

Manual control (for multi-variable or custom project surfaces):

```bash
# See the manual-control sequence below for the full project-intake path
ztare autoresearch trace --project <slug> --rubric <slug> --intake <slug>_intake.json --json
ztare autoresearch run --project <slug> --rubric <slug> \
    --intake <slug>_intake.json --preflight-only
ztare autoresearch run --project <slug> --rubric <slug> \
    --intake <slug>_intake.json --iters 10 \
    --mutator kimi --judge gpt4.1 --inverter claude
```

Same-family pairs are useful for transport smoke tests, but they are weak
evidence for a research claim. Prefer `kimi` + `gpt4.1`, `grok` +
`gemini-pro`, `gemini-pro` + `gpt4.1`, or another cross-family pair when the
judge is meant to catch the mutator's blind spots.

### C. Use the workbench or org runtime

Not every serious task should start with `make experiment-loop`. If the work is
frontier research, proof splitting, evidence acquisition, trajectory mining,
human-agent co-work, or a role-daemon task, route it first:

```bash
ztare autoresearch route --task "<task description>" --project <project> --rubric <rubric>
```

Then read:

- [workflow.md](workflow.md), especially section 0 route choice
- [cli.md](cli.md), for `ztare project`, `ztare autoresearch route`, `run`,
  and `projection`
- [org_runtime_quickstart.md](org_runtime_quickstart.md), for role-daemon and
  executive-inbox work
- [agent-prompts.md](agent-prompts.md), for paste-ready Codex/Claude prompts

---

## Advanced: controlled hidden-target experiment

Use this path only when the target must stay hidden until close, such as a
synthetic function-recovery experiment or another sealed discriminating test.
For ordinary project, paper, policy, market, operations, or reproduction work,
use the project-intake path above instead.

### 1. Write the hidden target

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

Rules for sealed targets:

- Use an opaque slug such as `exp01` (it appears in loop-visible files).
- Use generic variable names such as `x1`, `x2`, or `n`.
- Keep target form, parameters, derivation, and mechanism hints out of the
  charter, rubric, thesis, and visible evidence.
- Treat this as a controlled experiment with its own path; the normal public
  project intake path does not apply here. Read
  [for_researchers.md](for_researchers.md) before using the result as evidence.

### 2. Generate and inspect the surface

```bash
ztare project new --help
ztare project prepare --project exp01 --rubric exp01
ztare project source-check --project exp01 --json
```

The exact generated files depend on the project type selected by `ztare
project new`. Inspect the generated project directory, rubric, gate harness,
and visible evidence before sealing. Do not assume a historical file layout if
the CLI help says otherwise.

### 3. Check the gate before sealing

```bash
python projects/exp01/gate_harness.py --run-smoke-test
```

For numeric recovery experiments, the blank or zero model should fail the
project gate. If it passes, fix the threshold or harness before running the
loop.

### 4. Seal and run

```bash
make seal PROJECT=exp01 RUBRIC=rubrics/exp01.json
make experiment-loop \
    PROJECT=exp01 \
    RUBRIC=rubrics/exp01.json \
    ITERS=10 \
    MUTATOR_MODEL=gemini-pro \
    JUDGE_MODEL=gpt4.1
```

---

## Advanced: domain thesis scaffold

Use `generate-gp` when you already have an API-backed judge available and want
a qualitative project scaffold from a brief. For a source-first project, prefer
`ztare project source-init`, `source-check`, and a project-intake file instead.

```bash
make generate-gp \
    PROJECT=my_project \
    BRIEF="Your one-paragraph thesis question here, be specific about domain and claim direction" \
    JUDGE_MODEL=gpt4.1
```

This creates:
- `projects/my_project/evidence.txt`: blank evidence file (edit directly, or compile from `raw/`)
- `projects/my_project/raw/`: drop source documents here for `make evidence-compile`
- `projects/my_project/thesis.md`: seeded thesis template
- `projects/my_project/project_charter.md`: auto-drafted from your brief
- `rubrics/my_project.json`: LLM-drafted adversarial persona + criteria, with all qualitative gate opt-outs pre-filled

*Important:* Review and edit `rubrics/my_project.json` before sealing. The
LLM draft is a starting point, not a final rubric. Check that the persona is
genuinely adversarial for your domain and that the evidence surface is typed
before compilation.

```bash
# Option A: Add evidence directly
# Edit projects/my_project/evidence.txt

# Option B: Compile from raw documents
cp my_report.pdf projects/my_project/raw/
make evidence-compile PROJECT=my_project MODEL=gpt4.1

# Then seal, create the intake file, inspect run-readiness readiness, and run
make seal PROJECT=my_project RUBRIC=rubrics/my_project.json
ztare project intake create --path my_project_intake.json \
  --project my_project --rubric rubrics/my_project.json \
  --task "evaluate the bounded thesis in projects/my_project/thesis.md" \
  --bounded-claim "the thesis is supported by the compiled evidence surface" \
  --source-ref projects/my_project/raw \
  --evidence-ref projects/my_project/evidence.txt \
  --non-claim "not a full external replication or literature review" \
  --next-falsifier "add a primary source that contradicts one core premise" \
  --expected-command "ztare autoresearch route --task 'evaluate the bounded thesis in projects/my_project/thesis.md' --project my_project --rubric rubrics/my_project.json"
ztare project intake validate --path my_project_intake.json --source-preflight
ztare autoresearch trace --project my_project --rubric rubrics/my_project.json --intake my_project_intake.json --json
ztare autoresearch run --project my_project --rubric rubrics/my_project.json \
    --intake my_project_intake.json --iters 10 \
    --mutator gemini-pro --judge gpt4.1
```

Why not `mkdir` + manual rubric? Qualitative projects require three gate opt-out keys (`farther_tail_region: null`, `disable_evidence_fit_gate`, `disable_uniqueness_gap_gate`) that are non-obvious and whose absence causes hard fails that look like scoring failures. `generate-gp` pre-fills them.

---

## Model options

| Role | Recommended | Alternative |
|---|---|---|
| Mutator | `gemini-pro` | `claude-opus-4-6`, `gpt4.1` |
| Judge | `gpt4.1` | `gemini-pro`, `claude-sonnet-4-6` |

Gemini Pro as mutator + GPT-4.1 as judge is the default pairing. Cross-family pairing (different model families) reduces correlated blind spots.

---

## Reading the output

Each iteration prints:

```
Iteration N, score: XX
  Gate: harness_ok = true, rmse = 0.031
  Information yield: [...]
  Residual diagnostics: [shape hint]
```

Key signals:
- *Score 0 with `harness_ok=false`*: gate fired; model is wrong, loop continues searching
- *Score 0 with `harness_error`*: infrastructure bug; check imports, fix before rerunning
- *Score stagnant for 3+ iters*: stagnation pivot fires automatically
- *FEYNMAN WALL*: all 32 library primitives exhausted; grammar-guided symbolic regression activates

---

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `No module named 'src.ztare.substrates.<slug>_gt'` | Ground-truth fixture stub not created | Re-run `ztare project new`; the fixture stub is auto-created |
| `harness_ok=True` on blank model | RMSE threshold too loose | Tighten `_RMSE_THRESHOLD` in gate_harness.py and rubric |
| `--reviewer-domains` crash | Passed to the loop, which is the wrong consumer; the findings runner owns it | Remove from `make experiment-loop`; routing is automatic via `latent_distance.jsonl` |
| Score 0 every iteration | Hard gate too tight OR zero model passes | Check gate calibration; check evidence float parsing |
| Seal fails sentinel | Domain name leaked into mutator-visible file | Audit evidence.txt, charter, rubric for biological/domain terms |

---

## Where things live

```
projects/<slug>/          ← per-run artifacts (evidence, gate harness, test_model)
rubrics/<slug>.json       ← scoring rubric (ground-truth-blind)
src/ztare/substrates/     ← controlled-fixture target helpers
research_areas/            ← public seams, specs, boards, and experiment records
docs/                     <- reviewer docs (this file)
config/prompts/           ← reviewer domain personas
```

---

## Next steps

- First-run orientation: `docs/guides/first-30-minutes.md`
- Full workflow reference: `docs/guides/workflow.md`
- Experiment procedure: `docs/guides/experiment_cookbook.md`
- Architecture overview: `docs/concepts/architecture.md`
- How the validator works: `docs/concepts/cognitive_gym.md`
- Epistemic principles: `docs/concepts/epistemic_principles.md`
- Reflexive engineering: `docs/concepts/reflexive_engineering.md`
- Glossary: `docs/concepts/glossary.md`
- Experiment track record: `research_areas/EXPERIMENT_TRACK_RECORD.md`
