# ZTARE Workflow

The day-to-day guide for running ZTARE on a real project. The basic loop:

```
Gather sources -> Build workspace -> Extract evidence -> Run adversarial loop -> Generate report
```

For a plain-English glossary of terms, see [../concepts/glossary.md](../concepts/glossary.md). This is the operator-facing reference. It does **not** replace `README.md`.

---

## 0. Two Workflows Now Exist

There are now two different workflows in this repo:

1. general project workflow
   - `raw -> workspace -> evidence -> validator -> synthesis`
2. program hardening workflow
   - `seed spec -> genesis -> supervisor-routed debate/build/verify loop`

The second workflow is the modern replacement for ad hoc `ur turn` routing.

## 0a. Choose The Right Mode

There are now three practical operating modes:

1. artisanal / manual
   - use for exploratory work, fuzzy architecture, or one-off prompting
2. program hardening
   - use for bounded kernel or infrastructure improvements where provenance matters
3. domain validation
   - use for the original ZTARE workspace -> evidence -> validator -> synthesis path

Rule:

- do not force everything through the supervisor
- do not keep high-rigor kernel work in untracked chat-only routing once the packet is stable

The supervisor is for bounded programs, not for every thought.

## 0b. Two Audiences

This repo now serves two distinct readers. If you can identify which one you are, you can skip most of the document.

1. **General-purpose engine users**: you want to test a thesis or a claim on a domain (startup, activist target, strategy question, research area). You do not care about kernel internals, benchmarks, or the supervisor.
   - Read: §1 (When to use), §2 (Mental model), §3 (Standard loop), §3a (Rerun cadence), §4 commands for `workspace-update` / `evidence-compile` / `loop` / `synth`, §5 (Human role), and whichever of §6–§8 matches your project type.
   - Skip: §0a modes 1 and 2, §15 (Program hardening), the supervisor-specific command blocks.
   - Your entire loop is: `raw -> workspace -> evidence -> validator -> synthesis`. Nothing else should be load-bearing for you.

2. **Developers / researchers playing with the engine**: you are modifying the validator, the workspace compiler, the V4 kernel, primitives, or the supervisor control plane.
   - Read everything, but pay special attention to §0a (mode choice), §14 (primitive workflow), §15 (program hardening workflow), and the supervisor command surface. Pair this doc with `docs/ARCHITECTURE.md` and `supervisor/USER_MANUAL.md`.
   - The V4 six-stage kernel hardening path and supervisor-routed programs are for you, not for the general-purpose user.

If you are not sure which you are: start as a general-purpose engine user. You almost certainly do not need the hardening machinery on day one.

Inside the supervisor path:

- verifier success advances the active manifest automatically
- dependent packets unblock when prerequisites complete
- reporting is read-only and renders from `status.json` + `events.jsonl`
- human gate resolution is handled by `supervisor-resolve-gate`
- research programs now support deterministic prose-spec artifacts at `A2/B/C`
- the runtime can prefill a prose spec path, a draft markdown path, and a deterministic `prose_verifier` command
- research `A2` now carries the burden of exact contract emission: canonical `ProseSpec` only, with exact phrase/citation strings that `B` must include verbatim
- research `C` remains a dumb exact gate; only reversible canonicalization like newline / trailing-space normalization is allowed there
- generic document assembly is deterministic plumbing, not LLM work: ordered fragments can be concatenated into one output artifact after section packets verify cleanly
- cross-model `A1/A2` debate and optional manual ZTARE passes remain outside the runtime for now
- active runs should live under `supervisor/active_runs/<run_id>/` rather than `/tmp/` so wrapper sandboxes can access staging files reliably

## 0c. Researcher Discipline (Read If You Care Whether A Run Counts As Evidence)

If you are running ZTARE as an experiment (not just pressure-testing a domain thesis), three rules govern whether the run is diagnostic. Full version in [`docs/guides/for_researchers.md`](for_researchers.md).

1. **Charter contamination.** `autoresearch_loop.py:1319` injects `project_charter.md` verbatim into the mutator prompt every turn. Any target form, parameter values, or derivation you write to "motivate" or "explain" the target becomes a turn-1 cheat sheet. The target itself lives only in the sealed pre-reg under `research_areas/private/seams/`. Before sealing a charter, sha256 it, grep it for GT substrings, and ask whether a stranger could reconstruct the target from it alone. Origin: GP-023 sandbox_07, 2026-04-14. Two mutators transcribed the charter's derivation on iter 1 and "recovered" the GT to six decimals. Neither run was diagnostic.

2. **Visibility rule: closed = public, open/testing = private.** Closed seams and pre-regs move to `research_areas/seams/` at close time. In-flight experiment artifacts (pre-regs, GT derivations, blind oracle details) stay in `research_areas/private/seams/` until the experiment closes, even if other materials are public. One seam, one place. No toggle, no symlink. Full rule in `AGENTS.md` §4a.

3. **Honeypot mode is bug-bounty, not discovery-proof.** `rubrics/honeypot_minimal.json` uses a loose discovery rubric (max 115 including +15 gaming bonus). A high honeypot score is a free bug report: it names something the factory gate battery missed. Those bugs are candidates for new deterministic gates. A 115 honeypot run does *not* mean discovery; read the judge's weakest-point note and treat it as the handle to grab next. Honeypot scores are not comparable to factory scores.

If you are a general-purpose engine user (§0b path 1), you can skip this section. If you are running experiments whose outcomes will be cited, read `docs/guides/for_researchers.md` end-to-end before sealing your first pre-reg.

---

## 1. When To Use This Workflow

Use this workflow when:

- the project will evolve over time
- source material accumulates
- contradictions matter
- you want reproducible evidence snapshots
- you expect to rerun the validator as new information arrives

Do **not** use this full workflow for:

- tiny one-off tests
- toy projects with 1-2 source files
- cases where writing `evidence.txt` manually is faster

---

## 2. Core Mental Model

There are four layers:

1. `raw/`
   - the source bucket
2. `workspace/`
   - persistent structured memory, inspired by [Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): raw sources accumulate, an LLM extracts structured notes, and the system compounds knowledge over time without the validator ever trusting it as authority
3. `evidence.txt`
   - bounded validation snapshot
4. ZTARE + synthesis
   - adversarial validation and final artifacts

In one line:

```text
raw -> workspace -> evidence snapshot -> validator -> artifact
```

---

## 3. Standard Loop

For a real project, the loop is:

1. add or update source material in `projects/<project>/raw/`
2. update the workspace
3. review facts, contradictions, and open questions
4. compile a bounded evidence snapshot
5. promote it to `evidence.txt` if running the current validator unchanged
6. run ZTARE
7. synthesize the result
8. repeat when new evidence arrives

---

## 3a. Rerun Cadence (General-Purpose Engine Users)

The most common question for general-purpose users is "which step do I have to rerun when X changes?" This table answers it. The rule is: only rerun downstream of what changed; upstream artifacts stay valid.

| Trigger                                                         | Rerun starting at                                   | Why                                                                                                 |
|-----------------------------------------------------------------|-----------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| You added or edited files under `projects/<project>/raw/`      | `workspace-update`                                  | Workspace is derived from raw. Anything downstream is stale until the workspace reflects new sources. |
| `contradictions.md` / `facts.md` / `open_questions.md` changed from a workspace update | `evidence-compile`                          | Evidence snapshot is derived from workspace memory.                                                 |
| `compiled_evidence.txt` changed (new bounded snapshot)          | promote to `evidence.txt`, then `loop`              | Promotion is a rebaseline event: score regime fingerprints the bytes of `evidence.txt`; prior champions become `regime_mismatch` by design. |
| You changed the rubric, model pairing, or iteration budget      | `loop`                                              | Validator is stateless. No upstream rerun needed; workspace and evidence are independent of rubric. |
| You want a fresh report for the current champion                | `synth`                                             | Synthesis is downstream of `champion_*` artifacts; earlier stages are untouched.                    |
| Provider outage / compile failed closed (`latest_compile_failure.json` written) | `evidence-compile` (retry), then promote + `loop` | Compiler fails closed for a reason. Retry the compile rather than skipping it.                      |
| `thesis.md` changed (new claim to test) but same evidence base  | `loop` (optionally `synth` after)                   | Thesis lives with the validator input, not with the workspace.                                      |
| You reach `UNDERIDENTIFIED` and want to branch                  | See §5b: use `hypotheses/<candidate>/`              | Do not overwrite the active thesis ad hoc; preserve the current branch and promote a candidate.     |

Two rules to keep rerun cost bounded:

1. **Do not rerun `workspace-update` just because you reran the loop.** Workspace is expensive and deterministic against `raw/`; if raw did not change, workspace is still fresh.
2. **Do not skip the `compiled_evidence.txt -> evidence.txt` promotion step silently.** Promotion is a rebaseline; if you skip it, the validator is running against an older frontier than the compiler just produced, and champions will look better than they are.

---

## 4. Commands

All operational commands now run as Python modules from repo root:

```bash
python -m src.ztare.<area>.<module> ...
```

For common tasks, you can also use the repo `Makefile`:

```bash
make help
make workspace-update PROJECT=<project> MODEL=gemini
make evidence-compile PROJECT=<project> MODEL=gemini
make loop PROJECT=<project> RUBRIC=<rubric> ITERS=10 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
make synth PROJECT=<project> MODEL=gemini QA_MODEL=claude RENDERER=founder_memo
make benchmark-stage1 BENCH_JUDGE=gemini BENCH_JOBS=3
```

### When to use `make loop` vs `make experiment-loop`

`make experiment-loop` is a wrapper around `make loop` that adds two layers of safety:

1. **Always** passes `--disable_attacker_tools` (closes the attacker-exfil class — any live run, blind or not, wants this default).
2. **Iff** the rubric declares `holdout_hard_gate: true`, it also verifies `gate_harness.py` and `evidence_holdout.txt` exist, pre-flights that the harness produces valid JSON, and auto-sets `--underidentified_after=$(ITERS)` to prevent the underidentified-kill bug on hard-gate runs.

Decision tree:

```
Choose make experiment-loop by default.
  └── If rubric declares holdout_hard_gate: true, hardening kicks in automatically
      (harness + holdout pre-flight + underidentified fix).
  └── Otherwise, it passes through to make loop with --disable_attacker_tools added.

Choose make loop ONLY when:
  • Actively debugging and you need attacker tools available, OR
  • You are hand-pinning all flags yourself and understand the safety trade-off.
```

In practice: **`make experiment-loop` is the correct default for any live run, including qualitative / exploratory / no-ground-truth projects.** The "experiment" prefix is about pre-registered safety, not about requiring a hidden GT. The hard-gate-specific hardening only activates when the rubric asks for it.

Pre-registered falsification runs (blind law recovery with sealed GT) additionally require `make seal` before launch — see `docs/guides/experiment_cookbook.md`. That discipline is separate from the loop vs experiment-loop choice.

Supervisor commands:

```bash
make benchmark-supervisor
make benchmark-supervisor-registry
make benchmark-supervisor-seed-registry
make benchmark-supervisor-genesis
make benchmark-supervisor-staging
make benchmark-supervisor-report
```

### Step 0: Scope-Anchor Broad Projects

Before the first serious run on a broad project, scaffold and edit a charter:

```bash
python -m src.ztare.common.scaffold_project_charter \
  --project <project> \
  --mode broad
```

Use `project_charter.md` when:

- the question has multiple plausible sub-questions
- a project could drift into a narrower seam and still look good rhetorically
- end states need to remain distinct
- the project inherits from another project

The charter is advisory in prose and deterministic in anchors:

- `Core Question` / `Out Of Scope` / `End States` guide the judge
- `Forecast Type` tells the system whether bounded tilt or `%` claims are even in-bounds
- `Anchor Proxies` drive mathematical drift detection

Forecast typing rule:

- use `directional_forecast` when the project may include a bounded forward-looking tilt but is not a calibrated `%` forecast project
- use `probabilistic_forecast` only when the project explicitly targets a point probability for a defined event and horizon
- do not let the existence of a probability DAG silently convert a directional project into a probabilistic one
- directional projects that sneak in unsupported `%` claims are now intended to be capped by the scorer, not merely discouraged in the prompt

Stagnation pivoting:

- at `stagnation_count >= 3`, the loop now injects a named pivot profile rather than a silent monolithic prompt
- profiles currently include:
  - `legacy_generic`
  - `bounded_discriminator`
  - `kernel_bounded`
- stdout reports which profile and heuristic modules were injected

### Artifact roles

Validation runs now maintain two explicit artifact families:

- `latest_*`
  - the most recent evaluated attempt
- `champion_*`
  - the current promoted best result for the active regime

This matters because the newest evaluated candidate may be worse than the promoted champion.

For domain projects, expect:

- `projects/<project>/latest_eval_results.json`
- `projects/<project>/champion_eval_results.json`
- `projects/<project>/latest_probability_dag.json`
- `projects/<project>/champion_probability_dag.json`
- `projects/<project>/workspace/latest_evidence_gaps.json`
- `projects/<project>/workspace/champion_evidence_gaps.json`
- `projects/<project>/workspace/latest_constraint_proposals.json`
- `projects/<project>/workspace/derived_constraints.json`
- `projects/<project>/workspace/derived_constraints_brief.md`

If `champion_*` artifacts are missing or stale relative to the project's saved-best history marker, the loop now reconstructs them from history before trusting them as the active baseline.

This migration path is covered by a local regression:

```bash
python -m src.ztare.validator.champion_artifacts_fixture_regression
```

### Step 1: Update The Workspace

```bash
python -m src.ztare.workspace.update_workspace --project <project> --model gemini
```

This reads `projects/<project>/raw/` and updates:

- `workspace/source_notes/*.json`
- `workspace/source_index.json`
- `workspace/workspace_snapshot.json`
- `workspace/facts.md`
- `workspace/ranges.md`
- `workspace/contradictions.md`
- `workspace/open_questions.md`
- `workspace/candidate_claims.md`

### Step 2: Review The Workspace

The minimum useful files to inspect are:

- `projects/<project>/workspace/facts.md`
- `projects/<project>/workspace/contradictions.md`
- `projects/<project>/workspace/open_questions.md`
- `projects/<project>/workspace/candidate_claims.md`
- `projects/<project>/workspace/champion_evidence_gaps.json` (preferred, if present)
- `projects/<project>/workspace/latest_evidence_gaps.json` (if present)
- `projects/<project>/workspace/derived_constraints.json` (confirmed structural limits)
- `projects/<project>/workspace/latest_constraint_proposals.json` (fresh candidate constraints from the latest run)
- `projects/<project>/workspace/evidence_gap_brief.md` (after compile, if present)

Human job here:

- make sure obvious contradictions were preserved
- make sure important unknowns were not smoothed away
- decide what claim or thesis is worth testing next
- if typed evidence gaps exist, decide whether the next bottleneck is evidence collection rather than more blind iterations
- if confirmed derived constraints exist, treat them as read-only structural limits rather than new evidence

### Step 3: Compile Evidence

```bash
python -m src.ztare.workspace.compile_evidence --project <project> --mode workspace
```

Default outputs:

- `projects/<project>/compiled_evidence.txt`
- `projects/<project>/compiled_evidence_packet.json`
- `projects/<project>/compiled_evidence_provenance.json`
- `projects/<project>/workspace/evidence_gap_brief.md` (if champion/latest gap artifacts exist)
- `projects/<project>/workspace/latest_compile_failure.json` (only on fail-closed compile errors)

If the compiler hits a provider outage or other compile-time exception, it now fails closed:

- exit code is `1`
- no Python traceback is required for the operator path
- a structured failure artifact is written to `workspace/latest_compile_failure.json`
- recovery is: retry later or switch model, then rerun `compile_evidence.py`

### Step 4: Promote The Snapshot For The Current Validator

ZTARE still reads `projects/<project>/evidence.txt`, so for now:

```bash
cp projects/<project>/compiled_evidence.txt projects/<project>/evidence.txt
```

Important:

- the active score regime fingerprints the byte content of `evidence.txt`
- promoting `compiled_evidence.txt` into `evidence.txt` is therefore a rebaseline event
- old champions from the prior evidence frontier are intentionally treated as `regime_mismatch` after promotion
- the evidence compiler prefers `champion_evidence_gaps.json` when present and falls back to `latest_evidence_gaps.json`

### Step 5: Run ZTARE

Example:

```bash
python -m src.ztare.validator.autoresearch_loop \
  --project <project> \
  --rubric <rubric> \
  --iters 10 \
  --mutator_model gemini \
  --judge_model gemini
```

Legacy *Cognitive Camouflage* benchmark shortcuts:

```bash
make paper1-tsmc-legacy
make paper1-epistemic-legacy
```

Stagnation handling is now explicit:

- on non-V4 projects, the generic topological-pivot prompt is injected only once `stagnation_count >= 3`
- at `stagnation_count >= 4`, the loop also purges visible axiom context and forces a blank-slate reset
- on V4-family projects, the generic pivot is intentionally suppressed; `stagnation_count >= 3` injects a bounded mutation override instead of a free-form pivot
- these modes are now announced in loop stdout so the operator can see when the prompt contract changes

## Runtime Notes

- provider/model resolution, retry handling, and usage extraction now come from `src/ztare/common/llm_runtime.py`
- persistent transient provider failures can trigger automatic cross-provider failover instead of killing the run immediately
- cost estimates depend on `supervisor/model_pricing.json`
- versioned provider model names are normalized before pricing lookup, so telemetry can still price runs when providers return names like `models/gemini-2.5-flash`
- if a judge call falls back to a different effective model, the scoring regime fingerprint changes on purpose so mixed-provider evaluations do not masquerade as directly comparable

V4 kernel meta-runner shell shortcuts:

```bash
make v4-meta-show
make v4-meta-run-current
make v4-meta-reset
```

### Step 5a: Use A Short Probe Budget Before Declaring Closure

Do not treat a single `iter0 = 0` or similar hard baseline as automatic proof that the current project has no viable on-charter basin.

A baseline is a local readout, not a proof of global exhaustion.

Use a short additional probe budget (`2-3` iterations) before declaring the current framing closed when all of the following are true:

- the falsification suite passes
- drift is controlled or not firing
- the failure is substantive rather than infrastructure/provider noise
- the project, regime, or charter was recently reframed, hardened, or rebaselined

Why:

- the mutator may still discover a different basin inside the same charter and evidence frontier
- the operator's "there is nothing here" instinct can itself be wrong

Do **not** turn this into open-ended grinding.

If the same hard failure repeats with no meaningful basin movement after the probe budget:

- stop iterating
- change the evidence frontier
- or branch the hypothesis explicitly

If a materially better on-charter basin appears during the probe budget:

- treat that as genuine new information
- update the active champion
- and continue from there rather than from the earlier failed baseline

### Step 5b: Branch After `UNDERIDENTIFIED`

If a project reaches `UNDERIDENTIFIED`, do not overwrite the active thesis ad hoc.

Use project-local hypothesis bundles instead:

```text
projects/<project>/
  thesis.md
  test_model.py
  workspace/
  hypotheses/
    <candidate_name>/
      thesis.md
      test_model.py   # optional
      notes.md
```

Why:

- the active thesis and active falsification suite must travel together
- copying only a new `thesis.md` can leave a stale `test_model.py` evaluating the wrong object
- `workspace/` is machine-owned and should not hold operator exploration notes

Recommended workflow:

1. preserve the current best branch as its own hypothesis bundle
2. draft alternative candidates under `hypotheses/`
3. promote one candidate into the project root
4. run a fresh loop episode
5. compare against the preserved baseline

For `eu_union_stability`, use:

```bash
python projects/eu_union_stability/promote_hypothesis.py <candidate_name> --clear-status
python -m src.ztare.validator.autoresearch_loop \
  --project eu_union_stability \
  --rubric eu_union_integration \
  --iters 3 \
  --mutator_model claude \
  --judge_model claude \
  --deterministic_score_gates
```

`promote_hypothesis.py` does three things safely:

- copies the candidate `thesis.md` into the project root
- copies the candidate `test_model.py` if present
- otherwise deletes the stale project-root `test_model.py` so the next run fail-closes instead of evaluating a new thesis with an old suite

Optional:

- `--clear-status` archives stale workspace status files for operator clarity

This is a project workflow convention, not a supervisor feature.

These commands are for the kernel-local promotion runner, not the supervisor control plane.

V4 bounded debate-orchestration shortcuts:

```bash
make v4-debate-init RUN_ID=<run_id>
make v4-debate-show TASK_ID=<task_id>
make v4-debate-merge TASK_ID=<task_id>
```

### Step 6: Synthesize

Founder pack:

```bash
python -m src.ztare.synthesis.synthesize --project <project> --model gemini --pack founder
```

Single artifact:

```bash
python -m src.ztare.synthesis.synthesize --project <project> --model gemini --renderer-type founder_memo
```

Multi-project artifact:

```bash
python -m src.ztare.synthesis.synthesize --projects p1,p2 --model gemini --renderer-type research_note
```

---

## 5. Human Role At Each Step

### In `raw/`

Human decides what source material belongs in scope.

Examples:

- startup: customer interviews, pricing pages, pilot results, attendance logs, founder notes
- strategy: filings, earnings calls, transcripts, market notes, competitor pricing
- research/architecture: logs, papers, failure notes, architecture constraints, benchmark results

### In `workspace/`

Human does not rewrite everything manually. The human reviews for:

- omitted contradictions
- obvious extraction mistakes
- missing source categories
- whether the candidate claims are actually worth testing

### In ZTARE

Human chooses:

- the rubric
- the iteration budget
- the model pairing
- whether the project is exploratory, diligence-oriented, or architectural

### In synthesis

Human chooses:

- the audience
- the renderer
- whether to send memo, appendix, or both

---

## 6. Example: Startup Project

Goal:

- pressure-test a startup thesis using interviews, product notes, and pilot data

Loop:

1. add founder notes, customer interviews, pricing, and pilot metrics to `raw/`
2. run `python -m src.ztare.workspace.update_workspace`
3. inspect:
   - contradictions between founder narrative and user behavior
   - unresolved unknowns such as real conversion or retention
4. compile evidence
5. run ZTARE on one bounded question
   - example: “Does repeat same-group attendance drive the core growth mechanism?”
6. synthesize into:
   - founder memo
   - quantitative appendix

What the human is actually doing:

- deciding what strategic question is load-bearing
- ensuring the evidence base is not missing the obvious blockers

---

## 7. Example: Strategy / Activist Thesis

Goal:

- stress-test an investment or activist thesis against filings, earnings calls, and market evidence

Loop:

1. add filings, transcript excerpts, market notes, competitor benchmarks to `raw/`
2. update workspace
3. inspect:
   - contradictions between management claims and economics
   - open questions that block the short or long thesis
4. compile evidence
5. run ZTARE on one bounded claim
   - example: “Price compression destroys the current margin narrative”
6. synthesize into a research note or decision brief

What the human is actually doing:

- scoping the thesis tightly
- deciding which claim is important enough to attack first

---

## 8. Example: Engine / Architecture Project

Goal:

- evolve the epistemic engine using its own failure logs and constraints

Loop:

1. add debate logs, architecture notes, benchmark failures, and design constraints to `raw/`
2. update workspace
3. inspect:
   - recurring architectural contradictions
   - unresolved open problems
4. compile evidence
5. run ZTARE on one architectural claim
   - example: “Static evidence is the bottleneck”
6. synthesize into an architectural memo or research note

What the human is actually doing:

- choosing whether the next loop should improve the validator, the evidence substrate, or the synthesis layer

---

## 9. What This Adds Versus The Old Workflow

Old workflow:

- human manually rewrites `evidence.txt`
- contradictions are easy to omit
- evidence does not accumulate cleanly over time
- provenance is fragile

New workflow:

- source material accumulates in `raw/`
- structured memory accumulates in `workspace/`
- evidence snapshots are reproducible
- contradictions and unknowns are preserved explicitly
- ZTARE receives a cleaner bounded input

The change is:

**from manual brief-writing to persistent evidence operations**

---

## 10. What This Still Does Not Do

It does **not** yet:

- autonomously search the web
- autonomously decide truth
- replace human thesis selection
- remove the need for adversarial validation

The workspace helps prepare claims.
ZTARE helps break claims.

---

## 11. Recommended Initial Practice

For a new project:

1. start with `raw/`
2. update workspace
3. compile evidence
4. compare compiled evidence against your manual intuition
5. only then run ZTARE

For an existing project:

1. backfill important source material into `raw/`
2. build the workspace once
3. compare:
   - old manual `evidence.txt`
   - new `compiled_evidence.txt`
4. run the same rubric with fixed settings
5. evaluate whether the compiled evidence improves downstream thesis quality

---

## 12. Sandbox Construction: GP-072 Division A/B Protocol

When setting up a science sandbox (closed experiment with known GT), use the Division A / Division B information isolation protocol. **Do not** have a single agent that knows GT also write mutator-visible files. Contamination is an information flow problem, not a discipline problem.

### Division A (Lab Tech, knows GT)

Produces GT-aware artifacts only:
- `evidence.txt`, `evidence_holdout.txt` (generated from GT formula)
- GT module (e.g., `src/ztare/substrates/<slug>_gt.py` with `f_true`, `f_dominant`)
- `.denylist` file (GT-specific patterns for the leak sentinel)
- Pre-registration document (private, names GT, seals protocol)

Division A artifacts live in `research_areas/private/` or the project directory (never in mutator-visible files).

### Division B (Principal Investigator, GT-blind)

Receives only the abstract problem brief and evidence data. Produces:
- `project_charter.md` (neutral language, no structural hypotheses)
- Rubric JSON (no GT framework vocabulary like "corrector", "dominant term")
- `test_model.py` (trivial baseline: `f(u, v) -> 0`)
- `gate_harness.py` (frozen, imports from test_model.py)

### Pre-Seal Gate: Leak Sentinel

```bash
python -m src.ztare.validator.leak_sentinel \
    projects/<project> \
    rubrics/<rubric>.json \
    --denylist-file projects/<project>/.denylist
```

Exits 0 if clean, 1 if any denylist pattern appears in mutator-visible files. The sentinel is necessary but not sufficient; also run integration tests (all harness flags) before sealing.

### Agent Implementation

When using Claude Code, spawn Division A and Division B as **separate agents** with information barriers:
- Division A agent: briefed with GT formula, produces GT-aware artifacts
- Division B agent: briefed with only the abstract problem description, produces mutator-visible artifacts
- Run the leak sentinel after both agents finish

See `research_areas/private/seams/GP-072_role_separation_sandbox_construction_seam.md` for the full protocol and lessons learned.

## 13. Current Limitations

1. PDFs/images need conversion before ingest.
2. The validator still reads `evidence.txt`, so snapshot promotion is manual.
3. Workspace quality depends on source-note extraction and merge quality.
4. This workflow is worth it only when the project has enough source complexity to justify it.

---

## 13. Practical Rule

Use the workspace when the project has memory.

If the project does not accumulate sources, contradictions, and updates over time, skip it and write `evidence.txt` manually.

---

## 14. Optional Primitive Workflow

Use the primitive workflow only after you have enough run history for repeated adversarial failures to show up.

1. extract incidents from prior runs
```bash
python -m src.ztare.workspace.extract_incidents
```

2. draft candidate primitives
```bash
python -m src.ztare.primitives.draft_primitives --model gemini --skip-existing
```

3. review and promote selectively
```bash
python -m src.ztare.primitives.approve_primitive --primitive-key cooked_books --decision approved
```

4. arm the validator with approved precedents
```bash
python -m src.ztare.validator.autoresearch_loop --project <project> --rubric <rubric> --use_primitives
```

Default usage is attacker/judge-side only. That is the non-overfitting setting.

Only expose primitives to the mutator when you explicitly want transfer hypotheses:
```bash
python -m src.ztare.validator.autoresearch_loop --project <project> --rubric <rubric> --use_primitives --use_transfer_hypotheses
```

That second mode is stronger but riskier. Keep it off unless you want the mutator to explore cross-project pattern transfer explicitly.

---

## 15. Program Hardening Workflow

Use this when the work is not a domain project but a kernel/program improvement track.

This workflow now has two sublayers:

1. proposal layer
   - seed -> proposal manifest -> human acceptance
2. active program layer
   - genesis -> program manifest -> supervisor loop

### Step 1: Write Or Select A Seed

Seed specs live in:

- `research_areas/seeds/active/`
- `research_areas/seeds/deferred/`
- `research_areas/seeds/legacy/`

Current active critical-path seed:

- `research_areas/seeds/active/stage2_derivation_seam.md`

Deferred future seeds:

- `research_areas/seeds/deferred/systems_to_algorithms.md`
- `research_areas/seeds/deferred/ztare_open_source.md`

### Step 2: Ensure Seed Registry Status

The seed must be represented in:

- `research_areas/seed_registry.json`

### Step 3: Accept A Program

Only after human acceptance:

- write `supervisor/program_genesis/<program>.json`
- add the program to `supervisor/program_registry.json`

Optional pre-registry planning tools:

- `python -m src.ztare.validator.supervisor_proposal ...`
- outputs:
  - `supervisor/proposed_manifests/`
  - `research_areas/proposal_plans/`
  - `research_areas/debates/planning/`

### Step 4: Route With The Supervisor

See:

- `supervisor/USER_MANUAL.md`

Core commands:

```bash
python -m src.ztare.validator.supervisor_what_next ...
python -m src.ztare.validator.supervisor_backlog ...
python -m src.ztare.validator.supervisor_loop init ...
python -m src.ztare.validator.supervisor_loop emit-staging ...
python -m src.ztare.validator.supervisor_loop launch-staging ...
python -m src.ztare.validator.supervisor_loop commit-staging ...
python -m src.ztare.validator.supervisor_attended_autoloop ...
```

Notes:

- `launch-staging` removes manual copy/paste by invoking configured wrappers from `supervisor/agent_wrappers.json`
- verifier turns can now be launched locally and will prefill the verification request
- when wrapper telemetry is available, the wrapper writes `turn_usage` into the staged request and a usage JSON file under `staging/launch/`
- bounded spec refinement is supported as `A2 -> A1`, capped at 2 rounds before forcing `B` or `D`
- budget-aware refinement is supported but remains disabled until `supervisor/model_pricing.json` is populated and a run is initialized with `--max-refinement-cost-usd`
- attended autoloop can remove repeated command entry while preserving the manual `D` gate and fail-closed preview behavior
- active human-readable plans live in:
  - `research_areas/program_plans/`
- proposal-stage human-readable plans live in:
  - `research_areas/proposal_plans/`

For document programs, the intended long-term shape is:

- bounded fragment packets in `research_areas/drafts/<program_id>/`
- deterministic section specs in `research_areas/specs/`
- one assembly manifest that concatenates fragments into a canonical full-document artifact

That keeps drafting bounded while still allowing one final manuscript file.

### RACI For Seed / Debate / Spec / Draft Separation

`A = Accountable`, `R = Responsible`, `C = Consulted`, `I = Informed`

| Activity / Artifact | Human | A1/A2 Spec Agent | B Writer / Builder | C Verifier | Supervisor |
|---|---|---|---|---|---|
| Select or revise seed specs in `research_areas/seeds/**/*.md` | A/R | C | I | I | I |
| Append bounded turns in `research_areas/debates/**/*.md` | C | R | C | I | A |
| Lock deterministic contracts in `research_areas/specs/**` | C | R | I | I | A |
| Write generated artifacts in `research_areas/drafts/**` or approved implementation paths | I | C | R | I | A |
| Run deterministic verification and produce verification reports | I | I | I | R | A |
| Commit state transition, manifest advancement, and staged archive | I | I | I | I | A/R |
| Resolve freeze / close / resume at `D` | A/R | C | C | C | I |

The folder split is intentional:

- `research_areas/seeds/**` = strategic starting contracts
- `research_areas/debates/**` = bounded argument history
- `research_areas/specs/**` = locked deterministic contracts
- `research_areas/drafts/**` = generated manuscript or draft artifacts

Do not let generated debate or draft artifacts silently overwrite seed specs.

### Step 5: Close Or Freeze

When the program finishes:

- update `supervisor/program_registry.json`
- preserve the genesis artifact
- do not mutate the seed spec

### Rules

- do not derive the portfolio by scanning `projects/`
- do not let tactical debate logs overwrite seed specs
- do not create routable work without genesis
- do not reopen closed/frozen programs without a human gate
- do not confuse proposal planning with active program execution

---

## 16. Scientific Experiment Workflow: Law Recovery from Synthetic Data

Use this when the goal is to test whether ZTARE can recover a known mathematical law from evidence, with a sealed ground truth for verification. This workflow is distinct from general-purpose domain projects: the GT is known, the sandbox is constructed under Division A/B information isolation, and the gate is deterministic (RMSE or exact-match).

### When to use

- Testing a new Component D grammar command or primitive on a controlled target
- Calibration runs before pointing ZTARE at a genuinely unknown domain
- Infrastructure verification (continuous substrate, bivariate evidence, new mutator plumbing)

### Full Command Sequence

**1. Write the GT script (Division A)**

```python
# src/ztare/substrates/<slug>_gt.py
def f_true(x1, x2) -> float: ...       # ground truth
def f_dominant(x1, x2) -> float: ...   # dominant term (for Component C)
def evidence_grid() -> list[tuple[float, float]]: ...   # visible training points
def holdout_grid() -> list[tuple[float, float]]: ...    # hidden evaluation points
```

For discrete 1-variable substrates, `evidence_grid()` / `holdout_grid()` are optional; generate_substrate uses integer ranges instead.

**2. Generate substrate artifacts**

```bash
make generate-substrate \
    SLUG=<slug> \
    GT_SCRIPT=src/ztare/substrates/<slug>_gt.py \
    VARIABLES=x1,x2 \
    PROBLEM_BRIEF="Find a mathematical law governing z as a continuous function of two inputs x1 and x2."
```

This writes Division B artifacts (rubric, gate_harness.py, test_model.py, evidence files, charter) and an opaque re-export stub at `src/ztare/substrates/<slug>_gt.py`. The rubric field `component_c_gt_module` points to the stub, not the Division A script.

**3. Seal the sandbox**

```bash
make seal PROJECT=<slug> RUBRIC=rubrics/<slug>.json
```

Runs the leak sentinel (sentinel must pass), integration tests (smoke-test + gates must produce valid JSON), and writes `projects/<slug>/sandbox_seal.json`. **Must run before the loop. Never skip.**

**4. Launch the experiment loop**

```bash
make experiment-loop \
    PROJECT=<slug> \
    RUBRIC=rubrics/<slug>.json \
    ITERS=10 \
    MUTATOR_MODEL=gemini-pro \
    JUDGE_MODEL=gpt4.1
```

**5. If you stop and restart**

```bash
# Reset thesis to virgin state (remove any best_iteration tag)
# Clear workspace
rm -f projects/<slug>/workspace/*.json projects/<slug>/workspace/*.jsonl projects/<slug>/workspace/*.md
# Re-seal
make seal PROJECT=<slug> RUBRIC=rubrics/<slug>.json
# Relaunch
make experiment-loop PROJECT=<slug> RUBRIC=rubrics/<slug>.json ITERS=10 MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gpt4.1
```

### RMSE Gate Calibration Rule

The RMSE threshold must reject the zero model (`f(x1, x2) = 0`). Before sealing:

```bash
python projects/<slug>/gate_harness.py --run-smoke-test
```

If `harness_ok: true` on the zero model, tighten the threshold. For noiseless synthetic data, `0.05` is a reasonable default. The zero model RMSE should be >> threshold.

### Division A / B Boundary

| Artifact | Division | Mutator-visible? |
|---|---|---|
| `src/ztare/substrates/<slug>_<domain>_gt.py` | A (Division A GT script) | No |
| `src/ztare/substrates/<slug>_gt.py` (stub) | A (opaque re-export) | No |
| `projects/<slug>/evidence.txt` | B | Yes |
| `projects/<slug>/evidence_holdout.txt` | B (locked) | No |
| `projects/<slug>/gate_harness.py` | B | No |
| `projects/<slug>/test_model.py` | B | Yes (mutator rewrites this) |
| `rubrics/<slug>.json` | B | No |

Slug must be opaque (`gp080_01`, not `gp080_tacrolimus_01`). The slug leaks into rubric `project` field and charter; a domain name in the slug is a semantic hint to the mutator.

### Boundary: This Is Not Rebuilding ZTARE

This organization of labor does **not** replace ZTARE or replicate the old V4 hardening path if the boundary is kept clean.

- ZTARE remains the epistemic engine for adversarial reasoning, attack/defense pressure, and truth-sensitive thesis work.
- V4 hardening remains the kernel/program hardening path for core system integrity.
- The supervisor research pipeline is narrower:
  - form the bounded contract
  - route labor
  - preserve provenance
  - verify deterministic conformance
  - stop at human gates

If semantic truth judgment, novelty scoring, or open-ended epistemic attack gets pushed into supervisor `C`, that would be a bad duplicate of ZTARE. The current intent is organization of labor, not a second epistemic engine.
