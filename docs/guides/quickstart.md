---
description: "Two-page orientation for a new reviewer: value check, workbench, the four routes, sealed experiments."
---

# ZTARE Quickstart

> Up: [Documentation map](../README.md)

Two-page orientation for a new reviewer. Start with [first-30-minutes.md](first-30-minutes.md) if this is your first time in the repo, and use this page for the fast path once you know which route you want. Full reference: [workflow.md](workflow.md) and the [glossary](../concepts/glossary.md).

---

## What ZTARE does in one sentence

ZTARE helps you decide what you can stand behind from your own project files. It turns a thesis, local sources, evidence state, run readiness, report readiness, and saved review history into an inspectable project record.

## First value check

Before choosing a workflow, run the smallest offline demo:

```bash
make hello
```

Expected result: a ready project-intake file validates, its missing-reference falsifier blocks a simulated missing evidence file, a malformed intake file is blocked before in-loop routing, and an overbroad claim is demoted to bounded wording with missing evidence and a next falsifier. In one command, plausible output must survive separate evidence checks before it becomes a public claim.

For the full offline public review path, run:

```bash
make first-run
```

It chains the value demo, gaming-catalog audit, benchmark-evidence checks, the frozen evaluator-hardening proof-point check, claim-boundary audit, terminology audit, public smoke, adversarial entry-path checks, and docs checks.

## Open the Project Workbench

Everything below has a visual counterpart. The workbench is a local web app over your projects that walks each one from charter and thesis through sources, evidence, pressure-testing, and verdict:

```bash
docker compose --profile workbench up --build workbench   # one container, http://127.0.0.1:8765
# or, without Docker:
make forensic-workbench-live                              # API on :8765, app on :5174
```

From a project's pages you can critique its scoring rubric before spending a run, ask plain-language questions against the research map, stress-test a single claim, draft a bounded starting claim from a source document, and export the verified research graph to an Obsidian vault. Details in the [workbench interface guide](../concepts/forensic_workbench_interface.md). The browser never gets raw filesystem access; every action relays through the CLI.

---

## Four ways to use it

### A. Test a bounded claim (in-loop autoresearch)

You have a question ("Is this startup overvalued?", "What drives EU stability?"). Start by writing the boundary object: bounded task, claim, sources, evidence, non-claims, and next falsifier. Then inspect readiness before launching the loop.

```bash
# 1. Guided intake setup. The JSON includes prep, trace, and in-loop phases.
ztare project walkthrough --project <project> --rubric <rubric> \
  --task "<bounded task>" \
  --bounded-claim "<claim the loop may evaluate>" \
  --source-ref "<source ref>" --evidence-ref "<evidence file>" \
  --non-claim "<what this intake file does not prove>" \
  --next-falsifier "<test that could demote the claim>" \
  --intake-out <project>_intake.json --json

# Equivalent explicit intake creation command.
ztare project intake create --path <project>_intake.json \
  --project <project> --rubric <rubric> --task "<bounded task>" \
  --bounded-claim "<claim the loop may evaluate>" \
  --source-ref "<source ref>" --evidence-ref "<evidence file>" \
  --non-claim "<what this intake file does not prove>" \
  --next-falsifier "<test that could demote the claim>" \
  --expected-command "ztare autoresearch route --task '<bounded task>' --project <project> --rubric <rubric>"
ztare project intake validate --path <project>_intake.json

# 2. Inspect readiness and the no-model-call plan preview.
ztare autoresearch trace --project <project> --rubric <rubric> --intake <project>_intake.json --json

# 3. Run plan_preview.recommended_first_command.
# If readiness is blocked, this is the first repair command. If inputs are ready
# but not freshly admitted, this is the no-model-call readiness check:
ztare autoresearch run --project <project> --rubric <rubric> \
    --intake <project>_intake.json --preflight-only

# After a fresh admission, trace advances the recommended command to the bounded run:
ztare autoresearch trace --project <project> --rubric <rubric> --intake <project>_intake.json --json
ztare autoresearch run --project <project> --rubric <rubric> \
    --intake <project>_intake.json --iters 10 \
    --mutator <mutator-model> --judge <judge-model> --inverter <inverter-model>
```

After the readiness-check command, the trace JSON should include `loop_admission`. That saved entry tells you whether the current intake bytes still match the intake admitted by the loop, and whether the current run-readiness contract still matches the admitted entry digest.

Model aliases are listed in [model_aliases.md](../reference/model_aliases.md). Prefer the workbench Settings page or environment variables for provider choices: `ZTARE_WORKBENCH_MODEL`, `ZTARE_WORKBENCH_RUN_MUTATOR_MODEL`, `ZTARE_WORKBENCH_RUN_JUDGE_MODEL`, and `ZTARE_WORKBENCH_RUN_INVERTER_MODEL`. For consequential runs, use models from different provider families when possible, set `--inverter <model>` explicitly, and add `CROSS_FAMILY=1` when shared-provider evaluation should fail before any model call.

If the project already exists locally, intake validation also checks the offline raw/source typing readiness. Add `--source-preflight` when the intake file should require local source files before validation can pass. Intake enqueue always requires those local source files. Use the prep ledger when source files or typing still need work.

### B. Create or probe project data

You have project files, a review file, a decision process, or input-output data. ZTARE searches for candidate forms, bounded claims, or justified nulls under gates. It does not promote a result without separate source-readiness, non-claim, and falsifier discipline.

For a source-ingest project, start with the source initializer. It creates the portable `raw/` and `workspace/` directories plus an empty `raw/source_type_map.json`, without creating evidence or launching the loop:

```bash
ztare project source-init --project <slug> --rubric <slug>
ztare project source-check --project <slug> --json
ztare project source-index --project <slug> --json
```

Put text-like source files under `projects/<slug>/raw/`. Mark each source with `source_type` frontmatter or `raw/source_type_map.json`, using `source_evidence` for sources allowed to support immutable facts and constraints. Rerun `source-check` after adding or renaming raw files; it is an offline readiness check and compiles nothing. `source-index` writes the deterministic workspace source index, metadata, and saved history without model calls, and `make evidence-prepare` runs the same readiness check before workspace update and evidence compilation.

For a generated numeric or data project, use `new`, then `prepare` for the standard setup pipeline before any in-loop run:

```bash
ztare project new --help
ztare project prepare --project <slug> --rubric <slug>
ztare project seal --project <slug> --rubric <slug>
```

For concrete intake fixtures, see [examples/project_packets/](../../examples/project_packets/): one ready intake file and one malformed intake file that must fail validation. Older scripts may still use the legacy packet spelling for the same JSON; new user-facing docs say intake.

For a less toy example, try the synthetic [operational-diagnosis pilot](../../projects/ops_root_cause_diagnosis_demo/). It uses local incident, metric, staffing, change, export-log, ticket-sample, baseline, cache, and counter-hypothesis sources to test a bounded root-cause claim. The fixture is not customer data.

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

Expected trace shape before any paid run: `readiness` is `ready_for_first_in_loop_run`, `kernel_entry.status=ready`, and the `source_claim_graph` validates. If run files are already present, the trace may instead report `complete_trace`; inspect `recent_loop` for the latest score, provider failures, and next command. After the readiness check, `loop_admission` should verify the intake and run-readiness hashes.

To exercise the validation engine with live model calls, run the exact command stored in the intake file:

```bash
ztare autoresearch run \
  --project ops_root_cause_diagnosis_demo \
  --rubric ops_root_cause_diagnosis_demo \
  --intake projects/ops_root_cause_diagnosis_demo/ops_root_cause_diagnosis_demo_intake.json \
  --iters 1 \
  --mutator "$ZTARE_WORKBENCH_RUN_MUTATOR_MODEL" \
  --judge "$ZTARE_WORKBENCH_RUN_JUDGE_MODEL" \
  --inverter "$ZTARE_WORKBENCH_RUN_INVERTER_MODEL" \
  --llm-timeout-seconds 240 --llm-retries 1
```

A paid run should use deliberately chosen mutator, judge, and inverter models, set through the workbench Settings page or environment variables, and should stay bounded to the fixture's non-claims and next falsifier. Provider failures are recorded in the trace and stay there; the loop does not promote them as research results.

For your own project, follow the section A intake sequence with your slug, then enqueue and track any remaining prep:

```bash
ztare project intake validate --path <slug>_intake.json --source-preflight
ztare project intake enqueue --path <slug>_intake.json
ztare project prep-ledger add --task "prepare minimal reproduction and cost estimate" \
  --kind minimal_reproduction --project <slug> --rubric <slug>
ztare project prep-ledger list
```

A guarded end-to-end path also exists for OEIS-style 1D sequences (`make discover PROJECT=<slug> RUBRIC=<slug> ITERS=15`), running hypothesis loop, template compression, and Lean gate files in sequence. Treat its output as candidate evidence. Same-family model pairs are useful for transport smoke tests and weak evidence for a research claim; prefer different provider families when the judge is meant to catch the mutator's blind spots.

### C. Prove something (LeanMill)

For Lean formalization, governed proof search, or proof-credit governance, use the LeanMill track:

```bash
ztare leanmill --help
```

Read the [LeanMill architecture](../concepts/leanmill_architecture.md) first: it explains stations, the governance kernel, and why a compile is treated as necessary but insufficient (anti-laundering checks, vacuity probes, and the faithfulness firewall on autoformalized statements all run separately). Come to this track after the main path; it is the deepest evidence discipline in the repo.

### D. Route frontier or org work first

Not every serious task should start with a loop. If the work is frontier research, proof splitting, evidence acquisition, trajectory mining, human-agent co-work, or a role-daemon task, route it first:

```bash
ztare autoresearch route --task "<task description>" --project <project> --rubric <rubric>
```

Then read [workflow.md](workflow.md) section 0 for route choice, [cli.md](cli.md) for the full command surface, [org_runtime_quickstart.md](org_runtime_quickstart.md) for role-daemon and executive-inbox work, and [agent-prompts.md](agent-prompts.md) for paste-ready agent prompts.

---

## Advanced: controlled hidden-target experiment

Use this path only when the target must stay hidden until close, such as a synthetic function-recovery experiment or another sealed discriminating test. For ordinary project, paper, policy, market, operations, or reproduction work, use the project-intake path above.

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

Rules for sealed targets: use an opaque slug such as `exp01` (it appears in loop-visible files) and generic variable names such as `x1`, `x2`, or `n`, and keep target form, parameters, derivation, and mechanism hints out of the charter, rubric, thesis, and visible evidence. Treat the whole thing as a controlled experiment with its own path; the normal public project-intake path does not apply here. Read [for_researchers.md](for_researchers.md) before using the result as evidence.

### 2. Generate and inspect the project

```bash
ztare project new --help
ztare project prepare --project exp01 --rubric exp01
ztare project source-check --project exp01 --json
```

The generated files depend on the project type selected by `ztare project new`. Inspect the generated project directory, rubric, gate harness, and visible evidence before sealing, and trust the CLI help over any historical file layout.

### 3. Check the gate before sealing

```bash
python projects/exp01/gate_harness.py --run-smoke-test
```

For numeric recovery experiments, the blank or zero model should fail the project gate. If it passes, fix the threshold or harness before running the loop.

### 4. Seal and run

```bash
make seal PROJECT=exp01 RUBRIC=rubrics/exp01.json
make experiment-loop \
    PROJECT=exp01 \
    RUBRIC=rubrics/exp01.json \
    ITERS=10 \
    MUTATOR_MODEL="$ZTARE_WORKBENCH_RUN_MUTATOR_MODEL" \
    JUDGE_MODEL="$ZTARE_WORKBENCH_RUN_JUDGE_MODEL"
```

---

## Advanced: domain thesis scaffold

Use `generate-gp` when you already have an API-backed judge available and want a qualitative project scaffold from a brief. For a source-first project, prefer `ztare project source-init`, `source-check`, and a project-intake file.

```bash
make generate-gp \
    PROJECT=my_project \
    BRIEF="Your one-paragraph thesis question here, be specific about domain and claim direction" \
    JUDGE_MODEL="$ZTARE_WORKBENCH_RUN_JUDGE_MODEL"
```

This creates:

- `projects/my_project/evidence.txt`: blank evidence file (edit directly, or compile from `raw/`)
- `projects/my_project/raw/`: drop source documents here for `make evidence-compile`
- `projects/my_project/thesis.md`: seeded thesis template
- `projects/my_project/project_charter.md`: auto-drafted from your brief
- `rubrics/my_project.json`: LLM-drafted adversarial persona and criteria, with all qualitative gate opt-outs pre-filled

Review and edit `rubrics/my_project.json` before sealing. The LLM draft is a starting point. Check that the persona is genuinely adversarial for your domain and that the evidence files are typed before compilation.

```bash
# Option A: Add evidence directly
# Edit projects/my_project/evidence.txt

# Option B: Compile from raw documents
cp my_report.pdf projects/my_project/raw/
make evidence-compile PROJECT=my_project MODEL="$ZTARE_WORKBENCH_MODEL"

# Then seal, create the intake file, inspect run readiness, and run
make seal PROJECT=my_project RUBRIC=rubrics/my_project.json
ztare project intake create --path my_project_intake.json \
  --project my_project --rubric rubrics/my_project.json \
  --task "evaluate the bounded thesis in projects/my_project/thesis.md" \
  --bounded-claim "the thesis is supported by the compiled evidence file" \
  --source-ref projects/my_project/raw \
  --evidence-ref projects/my_project/evidence.txt \
  --non-claim "not a full external replication or literature review" \
  --next-falsifier "add a primary source that contradicts one core premise" \
  --expected-command "ztare autoresearch route --task 'evaluate the bounded thesis in projects/my_project/thesis.md' --project my_project --rubric rubrics/my_project.json"
ztare project intake validate --path my_project_intake.json --source-preflight
ztare autoresearch trace --project my_project --rubric rubrics/my_project.json --intake my_project_intake.json --json
ztare autoresearch run --project my_project --rubric rubrics/my_project.json \
    --intake my_project_intake.json --iters 10 \
    --mutator "$ZTARE_WORKBENCH_RUN_MUTATOR_MODEL" \
    --judge "$ZTARE_WORKBENCH_RUN_JUDGE_MODEL"
```

Why not `mkdir` and a manual rubric? Qualitative projects require three gate opt-out keys (`farther_tail_region: null`, `disable_evidence_fit_gate`, `disable_uniqueness_gap_gate`) that are non-obvious and whose absence causes hard fails that look like scoring failures. `generate-gp` pre-fills them.

---

## Model options

Choose models in the workbench Settings page or through environment variables:

| Role | Setting |
|---|---|
| Default model | `ZTARE_WORKBENCH_MODEL` |
| Mutator | `ZTARE_WORKBENCH_RUN_MUTATOR_MODEL` |
| Judge | `ZTARE_WORKBENCH_RUN_JUDGE_MODEL` |
| Inverter | `ZTARE_WORKBENCH_RUN_INVERTER_MODEL` |

For consequential runs, choose different provider families when possible. Cross-family pairing reduces correlated blind spots; it does not make the result true without sources, saved history, and review.

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

- Score 0 with `harness_ok=false`: gate fired; the model is wrong and the loop continues searching
- Score 0 with `harness_error`: infrastructure bug; check imports and fix before rerunning
- Score stagnant for 3+ iterations: the stagnation pivot fires automatically
- Library primitives exhausted (the grammar ceiling): grammar-guided symbolic regression activates

---

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `No module named 'src.ztare.substrates.<slug>_gt'` | Ground-truth fixture stub not created | Re-run `ztare project new`; the fixture stub is auto-created |
| `harness_ok=True` on blank model | RMSE threshold too loose | Tighten `_RMSE_THRESHOLD` in gate_harness.py and rubric |
| `--reviewer-domains` crash | Passed to the loop, which is the wrong consumer; the findings runner owns it | Remove from `make experiment-loop`; routing is automatic via `latent_distance.jsonl` |
| Score 0 every iteration | Hard gate too tight, or the zero model passes | Check gate calibration; check evidence float parsing |
| Seal fails sentinel | Domain name leaked into a mutator-visible file | Audit evidence.txt, charter, and rubric for domain terms |

---

## Where things live

```
projects/<slug>/           <- per-run files (evidence, gate harness, test_model)
rubrics/<slug>.json        <- scoring rubric (ground-truth-blind)
forensic-workbench/        <- the Project Workbench web app
src/ztare/substrates/      <- controlled-fixture target helpers
research_areas/            <- public seams, specs, boards, and experiment records
docs/                      <- reviewer docs (this file)
config/prompts/            <- reviewer domain personas
```

---

## Next steps

- First-run orientation: [first-30-minutes.md](first-30-minutes.md)
- Full workflow reference: [workflow.md](workflow.md)
- Experiment procedure: [experiment_cookbook.md](experiment_cookbook.md)
- Architecture overview: [architecture.md](../concepts/architecture.md)
- How the validator works: [cognitive_gym.md](../concepts/cognitive_gym.md)
- Epistemic principles: [epistemic_principles.md](../concepts/epistemic_principles.md)
- Reflexive engineering: [reflexive_engineering.md](../concepts/reflexive_engineering.md)
- Glossary: [glossary.md](../concepts/glossary.md)
- Experiment track record: [EXPERIMENT_TRACK_RECORD.md](../../research_areas/EXPERIMENT_TRACK_RECORD.md)
