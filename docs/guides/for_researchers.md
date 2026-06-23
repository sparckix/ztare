---
description: "How researchers and reviewers should inspect ZTARE runs, traces, and claims."
---

# ZTARE For Researchers

> **Up:** [Documentation map](../README.md)

This document is for researchers and reviewers who need to decide what a ZTARE
run honestly supports. It covers public project intake, in-loop autoresearch,
sealed hidden-target experiments, trace inspection, proof-work boundaries, and
reproduction. The examples include science and proof search, but the same
discipline applies to high-stakes project claims: policy analysis, market
research, operations decisions, reproduction tasks, or any agent output where a
plausible answer is not enough.

If this is your first time in the repo, start with `README.md`,
`docs/guides/first-30-minutes.md`, `docs/guides/quickstart.md`, and
`docs/guides/cli.md`. Come back here when the question changes from "did the
command finish?" to "what can this run honestly support?"

If you want the shortest executable proof point before reading, run
`make hello` and `make gaming-catalog-audit`. The first shows intake validation,
missing-evidence blocking, and claim demotion without model calls. The second
checks that the public gaming behavior catalog still matches the live registry,
promotion evidence, hardening map, and executable fixture anchors.

The housekeeping layout of `research_areas/` is documented in
`research_areas/README.md`. This document is about the discipline a run must
satisfy to count as evidence.

---

## Reviewer checklist

Before treating a ZTARE output as evidence, answer these five questions:

| Question | What to inspect |
|---|---|
| What was the bounded claim before the run? | project-intake JSON, sealed pre-registration, or review artifact |
| Which sources and evidence were allowed? | raw/source files, source index, compile provenance, evidence refs, evidence-gap receipts |
| Who proposed and who checked? | mutator/judge pairing, deterministic gates, proof governance, or review path |
| What status did the run earn? | route status, trace readiness, gate result, A/B/C/D sealed outcome, or explicit non-claim |
| What would change the conclusion? | next falsifier, recovery command, unresolved evidence gap, or benchmark arm still missing |

If any row is missing, the output may still be useful, but it is not yet a
result claim.

## 1. What makes a run count as evidence

A ZTARE run may produce a score, a claim candidate, a route decision, a review
artifact, and ledger rows. None of that is evidence by itself. A run is
usable evidence only when:

1. **There is a written boundary before the run.** For public project intake,
   use a project-intake file (`ztare project intake ...`) with a bounded claim,
   source refs, evidence refs, non-claims, next falsifier, and one parsed
   in-loop command. For controlled hidden-target experiments, use a
   pre-registration with a falsifiable claim, discriminating test, and success
   criterion written before the run.
2. **The trace can show its evidence chain.** A reader can inspect the raw
   sources, workspace provenance, source-claim graph records, compiled
   evidence, derived constraints, prediction receipts when present, projection
   rows, health gaps, and next commands. A score without this chain is a
   partial trace, not a result claim.
3. **The mutator cannot see the hidden target.** No target form, no target
   parameter values, no algebraic derivation of the target representation in any file
   `autoresearch_loop.py` reads on turn 1 (`project_charter.md`, `thesis.md`,
   `current_iteration.md`, rubric).
4. **The gates are real gates, not narratives.** A deterministic gate battery
   (fit-contract, farther-tail residual, fixture regression, source-contract
   checks, etc.), not a persona judging prose.
5. **The outcome has a typed status.** Public project intake uses route and
   trace statuses such as `invoke_autoresearch`, `prepare_autoresearch_surface`,
   `stay_out_of_loop`, `complete_trace`, or `partial_trace`. Controlled sealed
   experiments still close as Outcome A/B/C/D. "Interesting but inconclusive"
   is not an outcome.

If any of these is missing, treat the run as a setup check, diagnostic, or
exploratory note. It can still teach the next move; it should not be promoted
as a result claim.

---

## 1a. Choose The Evidence Route

Start by naming the route. Most mistakes come from using the right tool at the
wrong stage.

| Situation | Use | Evidence boundary |
|---|---|---|
| You have a bounded claim, sources, evidence refs, non-claims, and a next falsifier | Public project intake, then `ztare autoresearch trace` | Intake JSON plus read-only trace |
| You have raw files but no admissible evidence chain yet | Source preflight and evidence preparation | Source index, compile provenance, evidence-gap receipts |
| You need to discover the claim, proof split, setup fix, or missing source first | Out-of-loop research operations | Probe, note, source artifact, proof file, or prep-ledger row |
| You are doing Lean formalization, proof search, or proof-credit review | LeanMill/proof workflow | LeanMill receipts, proof-governance checks, and the proof-subsystem docs |
| You are testing a hidden target where leakage would invalidate the result | Sealed controlled experiment | Pre-registration and closed A/B/C/D outcome |
| You are making a public claim from prior work | Review artifact / evidence atlas | Claim, command, expected output, non-claims, next falsifier |

Do not use a project-intake file as a review artifact. Do not use compiled
evidence material as an intake file. Do not use the prep ledger as an
autoresearch scheduler. Do not treat proof-search activity as proof credit
unless the proof-governance boundary says the artifact earned credit.

---

## 2. Public intake before in-loop autoresearch

Project intake is the public boundary before a task enters the in-loop
autoresearch kernel. It is not RD out-of-loop agent execution and it is not a
scheduler. It answers one question: does this bounded intake file have enough
source, evidence, non-claim, rubric, and command information to be reviewed or
routed?

```bash
ztare project walkthrough
ztare project walkthrough --ops-demo
ztare project intake validate --path examples/project_packets/ready_demo_claims_intake.json
ztare project intake falsify --path examples/project_packets/ready_demo_claims_intake.json --remove-ref 'evidence_refs[1]'
ztare autoresearch trace --project demo_claims --rubric demo_claims --intake examples/project_packets/ready_demo_claims_intake.json --brief
ztare autoresearch run --project demo_claims --rubric demo_claims --intake examples/project_packets/ready_demo_claims_intake.json --preflight-only
ztare project intake enqueue --path examples/project_packets/ready_demo_claims_intake.json --queue-dir .ztare_project_prep_queue
```

`ztare project walkthrough` is no-write by default: it validates the ready and
malformed intake fixtures, then prints the commands to create a real intake file.
For an actual project, pass `--project`, `--rubric`, `--task`,
`--bounded-claim`, at least one `--source-ref`, at least one `--evidence-ref`,
one or more `--non-claim`, `--next-falsifier`, and `--intake-out`. The JSON
output includes a phased `command_plan`: pre-run source/evidence prep,
read-only trace, and the in-loop route/run gate. Use the `ready` flags to avoid
entering the loop before the intake file and local source preflight are ready.
`--ops-demo` shows the concrete operational-diagnosis fixture with typed local
sources, source-claim graph focus, and the exact preflight/run commands. Use
trace `--brief` for human review and `--json` for scripts.

The intake validator fails before run readiness when:

- required scalar fields are empty: `project`, `rubric`, `task`,
  `bounded_claim`, `expected_command`, or `next_falsifier`;
- required list fields are empty: `source_refs`, `evidence_refs`, or
  `non_claims`;
- local source/evidence refs do not exist;
- the intake project exists locally and its raw/source typing preflight has a
  blocking issue; use `--source-preflight` to require this check explicitly;
- `expected_command` is not a single parsed in-loop command;
- `expected_command` does not name the intake file's exact project and rubric.

`project intake enqueue` is stricter than shape validation: it always requires
the local source preflight, because the intake ledger is for source-ready
intake. Missing source or evidence prep goes in `project prep-ledger`.

Supported intake entry commands are intentionally narrow:

- `ztare autoresearch route ... --project <project> --rubric <rubric>`;
- `ztare autoresearch run ... --project <project> --rubric <rubric>`;
- `make experiment-loop PROJECT=<project> RUBRIC=<rubric>`.

The router can return three decisions:

- `invoke_autoresearch`: the task has a bounded claim, stable evaluator or
  gate, rubric, and artifact output.
- `prepare_autoresearch_surface`: one or more required inputs are missing;
  record prep artifacts if useful, then reroute.
- `stay_out_of_loop`: the task is still exploratory. Use out-of-loop RD work to
  define the claim/evaluator first; do not enqueue it as project prep.

The prep ledger is only an ordered list of missing artifacts. It can track
"write the minimal reproduction" or "add the gate harness"; it should not be
presented as an autoresearch run and should not execute research.

## 3. Inspect the trace before trusting a run

After an intake file is created, or after an old project is found in the repo, inspect
the project trace before running more iterations:

```bash
ztare autoresearch trace --project <project> --rubric <rubric> --intake <project>_intake.json --model gemini --json
make autoresearch-trace PROJECT=<project> RUBRIC=<rubric> INTAKE=<project>_intake.json MODEL=gemini JSON=1
```

The trace is read-only. The `--model` / `MODEL=` value only appears in suggested
recovery commands; the trace command does not call a model. Default trace health
is local and bounded; add `--full-health` only when you need the aggregate
autoresearch health report.

When `route_preview.can_run_now=true`, inspect `plan_preview.status` and run
`plan_preview.recommended_first_command`. There are two ready states:

- `ready_for_preflight`: run the no-spend launch check before a full iteration.
- `ready_for_bounded_run`: the trace already sees a fresh, hash-verified intake
  and run-readiness admission, so the recommended command is the bounded run.

```bash
ztare autoresearch run --project <project> --rubric <rubric> --intake <project>_intake.json --preflight-only
```

The preflight command exits before baseline judge evaluation and before
model-backed iteration work. Intake-backed preflight and full runs write `run_start`
telemetry with the admitted intake hash and run-readiness contract digest, so a
later trace or health report can bind the run to the exact intake file and
entry state that passed. If the intake file is edited after admission, trace
marks the receipt stale instead of silently treating the current file as the
one that passed. The top-level `loop_admission` summary reports intake hash
status and run-readiness hash status for the latest unique admitted receipts.
Treat a stale intake hash as a reason to inspect before reusing run evidence. Treat a
changed run-readiness hash as context, since history and project surfaces can
legitimately change after a run.

Trace statuses and readiness:

`project_intake.status=valid_packet` is a legacy machine label meaning the
intake shape and project/rubric binding validated. Older receipts still expose
the same data under `project_packet`; use `project_intake` in new docs and
tools. The top-level
`readiness` field preserves legacy status IDs for old readers; use
`readiness_canonical` when you want the current intake-facing name. The
`readiness`/`readiness_canonical` decision and `route_preview.can_run_now` are
the actual in-loop decision.
When a rubric resolves, trace also runs the same rubric/project launch preflight
as `make experiment-loop`; `can_run_now=true` requires that preflight to pass.

- `complete_trace`: raw/source material, workspace metadata, source index,
  compiled evidence/provenance, derived constraints, eval history, projection,
  and trace-local health records are present enough to inspect a historical
  run.
- `ready_for_in_loop_candidate`: the trace records are present and the
  supplied or discovered intake file validates against the traced project and
  rubric, with no source-claim graph prep blocker.
- `ready_for_first_in_loop_run`: intake and project/evidence surfaces are
  ready, but `eval_history` is absent because no loop has run yet. This is a
  valid first-run state; read `blocking_missing` before treating
  `partial_trace` as a blocker.
- `blocked_on_out_of_loop_prep`: intake may validate, but the trace read model
  found prep debt that should be handled before the validation engine runs. The
  common case is a source-claim graph routing public-source evidence gaps to
  `make evidence-fetch ...`; `route_preview.can_run_now` is false until that
  debt is cleared or explicitly justified. Local verifier gaps, such as
  preflight or falsifier-execution gaps, are carried as in-loop focus receipts
  instead of being treated as public evidence-fetch work.
- `blocked_on_launch_preflight`: the trace records are otherwise close enough,
  but `make experiment-loop` would fail before the first model call. Fix the
  reported rubric/project preflight item, often `project_charter.md`,
  `thesis.md`, or a malformed rubric field.
- `traceable_but_no_project_intake` (`traceable_but_no_project_packet` in
  legacy `readiness`): historical project state can be inspected, but a new
  in-loop candidate still needs bounded intake before it should be treated as
  ready.
- `partial_trace`: one or more trace records are missing. Read `missing`,
  `blocking_missing`, `history_missing`, `recovery_actions`, and
  `next_commands` before launching another loop.

When trace reports missing source files or source typing, prefer the CLI recovery command it
prints, such as `ztare project source-init --project <slug> --rubric <slug>`.
That command creates the source-ingest directories and `raw/source_type_map.json`;
source documents, compiled evidence, project intake, and loop execution remain
separate steps. After adding raw files, run `ztare project source-check --project
<slug> --json` for an offline readiness report; `make evidence-prepare` repeats
that preflight before the model-backed evidence compiler.
For older projects where compile provenance is fresh but the rendered evidence
output was not hashed, `ztare project evidence-bind --project <slug> --json`
writes an offline receipt for the current `evidence.txt` bytes. This is only a
compatibility receipt: it does not call a model, recompile evidence, refresh
stale source provenance, or prove the output existed at compile time. Trace
accepts it only while the compile-provenance file and bound output artifacts
keep the same hashes; edits after the receipt become `evidence_output_stale`.
When trace reports `out_of_loop_evidence_recovery`, prefer fetching the missing
public evidence. If the gap is genuinely outside the bounded claim surface, use
`ztare project evidence-gap justify --project <slug> --gap-id <id> --reason
"..." --json` instead of editing `latest_evidence_gaps.json`. The receipt is
bound to the exact current gap row; if the gap text, target, or id changes, the
old justification no longer retires it.
Evidence-gap rows are routed by a small contract, not by prose alone:
`recovery_kind=public_evidence` means the next step is public source or dataset
recovery, while `recovery_kind=local_verification` means the next step belongs
inside local verifier, fixture, code/log, preflight, receipt, or in-loop
discriminator work. Trace and evidence briefs also show `recovery_channel`,
`required_surface`, `can_public_fetch`, and `in_loop_consumable`; use those
fields before deciding whether to fetch, justify, or run another bounded loop.
`make evidence-fetch` acts only on explicit public recovery contracts by
default. If a row is only legacy prose inference, promote it to
`recovery_kind=public_evidence` or use `ALLOW_INFERRED_PUBLIC=1` intentionally
for an old run.

Current trace fields to read before making a claim. Some field names use older
`carrier` wording because telemetry and tests already depend on them; read
them as trace/read-model rows unless the text says otherwise.

- `carrier_chain`: compact ordered read model over project directory, raw
  sources, source preflight, source index, compile provenance, rendered evidence
  binding, evidence gaps, intake, launch preflight, mutator briefing, prediction
  contracts, eval history, and loop admission. Start here when deciding
  which recovery command is legitimate; after a run, the mutator-briefing row
  shows whether graph-focus receipts were actually carried into the candidate
  prompt, including evidence-gap ids/targets or a rubric-enabled probability-DAG
  focus. The prediction-contract row is score-only unless it reports an invalid
  authority claim.
- `graph_carriers[]`: graph-shaped evidence such as probability-DAG or
  source-claim graphs. These are useful only when their decision receipt
  names a recovery action, focus receipt, route demotion, or explicit
  `no_strategy_change`.
- `graph_rd_actions[]`: advisory out-of-loop recovery or in-loop focus rows
  derived from graph decision receipts. They are prep/read-model actions, not
  hidden execution. When a row comes from an evidence gap, it carries exact
  `gap_ids` and `targets` for the candidate artifact to address. It also
  carries `operator_card_routes[]` and `operator_card_ids[]` for `OP-GDC-01`,
  so graph-derived decisions remain distinguishable from ordinary prep rows.
- `prediction_summary`: normalized forecast or prediction receipts when a
  project has them. The summary reports binary Brier readiness against a
  constant-0.5 baseline; it does not steer autoresearch iterations and does not
  turn scratch forecasts into certified forecast-pool evidence.
- `project_intake`: bounded claim, source/evidence refs, non-claims, expected
  command, and next falsifier. Intake failure blocks readiness; it does not
  run the loop. `project_packet` remains as a legacy receipt alias.
- `route_preview`: the exact in-loop route command from the validated intake
  when available, plus the loop command that may run only when `can_run_now`
  is true.
- `kernel_health`: stale or missing evidence, projection, route, and loop
  records. Treat a red or partial health record as a reason to fix the
  project state before expanding the claim.

For a multi-project audit, run carrier replay after inspecting the individual
trace:

```bash
ztare autoresearch carrier-replay --project <project> --json
```

Read `current_carrier` first. A `complete` current carrier means the latest
materialized projection row has the worker, transport, failure signature, and
artifact fields needed for future replay. The top-level project can still be
`attention` when older rows are missing fields; that is legacy trace debt, not
proof that the current row is unusable. If `latest_eval_status` reports
`latest_eval_not_in_eval_history`, replay or append the latest evaluation before
using the projection for a claim or UI surface.

Loop-control health has one extra rule: a pivot, blitz, or primitive-class
rotation is only an activation row until follow-up exists. The hill-climb audit
therefore reports both raw control events and non-overlapping control episodes.
Use the episode view when deciding whether loop control helped. When health
reports `hill_climb_control_outcomes`, read
`control_episode_recovery_queue`: each row names the workspace, project, rubric,
run, control episode, action, reason, and trace command to inspect next. When a
project-intake file is present, the row also includes the intake path and a
no-spend `preflight_command` for checking launch/admission state before
spending on more iterations. The queue also separates loop intake from compiled
evidence artifacts: `compiled_evidence_packet.json` is evidence material, not a
valid `--intake` boundary unless a project-intake file with task, claim, refs,
non-claims, and falsifier fields has been created.
When a recovery row is `compiled_evidence_without_project_intake` (or the
legacy alias `compiled_evidence_without_admission_packet`), use
`ztare project intake draft-from-compiled --project <project> --path projects/<project>/<project>_intake.json`
to draft the intake file, then validate it. The draft remains fail-closed: stale
compile provenance or missing raw refs keep the intake invalid until repaired.
If the raw files were only moved, rerun with `--repair-moved-sources`; the
intake records each substitution in `draft_source.source_ref_repairs` and still
does not count as refreshed compiled evidence.
Fixture or controlled-demo rows stay visible but should not displace ordinary
project episodes. The queue is an audit surface, not a scheduler. To print just
that queue, run `ztare autoresearch hillclimb-audit --recovery-queue --json` or
`make autoresearch-hillclimb-audit RECOVERY_QUEUE=1 RECOVERY_LIMIT=10 JSON=1`.
To inspect only rows with existing project intake, add
`--recovery-intake-status ready` or `RECOVERY_INTAKE_STATUS=ready`. Intake
presence is only a handoff status; each queue row still reports run-readiness
status, blockers, and the trace-derived repair command before another in-loop
run is allowed.
If review shows that an item should not launch another iteration, record that
decision in the workspace instead of letting the queue stay ambiguous:

```bash
ztare autoresearch hillclimb-audit --record-resolution \
  --workspace projects/<project>/workspace \
  --run-id <run-id> \
  --iteration <first-control-iteration> \
  --last-control-iteration <last-control-iteration> \
  --outcome-status control_fired_without_followup \
  --resolution-status reason_recorded \
  --reason "<why no follow-up is justified>"
```

Resolution receipts remove the row from the active recovery queue only. They do
not change the measured post-control success, no-follow-up, or no-lift counts.

Typical recovery commands are explicit and filesystem-first:

```bash
make evidence-fetch PROJECT=<project> SEVERITY=blocking MAX_FETCHES=3 MODEL=gemini EVIDENCE_SEARCH_BACKEND=auto
make evidence-prepare PROJECT=<project> MODEL=gemini
ztare project evidence-bind --project <project> --json
ztare project evidence-gap justify --project <project> --gap-id <id> --reason "<why the gap is out of scope or already covered>" --json
ztare autoresearch trace --project <project> --rubric <rubric> --intake <project_intake.json> --model gemini --evidence-search-backend auto --json
ztare autoresearch route --task "<bounded task>" --project <project> --rubric <rubric>
```

`SEVERITY=` should match the active gap reported by trace; blocking gaps should
be cleared before degrading ones. `EVIDENCE_SEARCH_BACKEND=` controls only the
public web-search provider used by evidence fetch. `MODEL=` is still the model
label passed to workspace update, evidence compile, and later loop commands.

`MODEL`, `MUTATOR_MODEL`, and `JUDGE_MODEL` accept the short aliases in
[`docs/reference/model_aliases.md`](../reference/model_aliases.md), including
DeepSeek, Kimi/Moonshot, and Grok/xAI. For evidence-prep and loop debugging,
prefer bounded runs with explicit timeout knobs, for example
`EVIDENCE_LLM_TIMEOUT=120 EVIDENCE_LLM_RETRIES=1` or
`AUTORESEARCH_LLM_TIMEOUT=120 AUTORESEARCH_LLM_RETRIES=1`. Those knobs are
transport controls; they do not change the evidence standard.

Do not upgrade a project from `partial_trace` to a claim because later
iterations look persuasive. Fix or acknowledge the missing trace input first.

## 3a. Inspect the report boundary

Reports are review artifacts, not a second source of truth. After a run has an
intake file, trace, and evidence surface, inspect the deterministic report
boundary before you read generated prose:

```bash
make synth-contract PROJECT=<project> RENDERER=research_note
```

This path does not call a model. It refreshes the trace-derived review context
and writes `projects/<project>/synthesis/report_support_contract.json`. If that
contract is blocked, stale, unbound, or names runtime risks, the report is not a
current result even if an older `Report.md` exists.

Generate prose only after the support contract is acceptable:

```bash
make synth PROJECT=<project> MODEL=gemini QA_MODEL=claude RENDERER=research_note
```

For projects with autoresearch state, synthesis writes two trace-derived files
under `projects/<project>/synthesis/` before the renderer produces prose:

- `autoresearch_review_context.json`: compact trace context, including
  readiness, run-readiness status, recent-loop state, graph/evidence-gap
  actions, recovery commands, and runtime caveats.
- `report_support_contract.json`: the deterministic authority boundary for the
  report. It lists supported claims, unsupported or unresolved claims,
  blockers, runtime risks, graph/evidence-gap actions, and next actions.

Read `report_support_contract.json` before treating `Report.md` as a review
artifact. A good report may summarize, prioritize, and translate; it must not
promote trace readiness, graph focus, provider failures, stale synthesis
inputs, or health gaps into substantive evidence. If the report makes a
stronger claim than the support contract allows, keep `Report.candidate.md` as
a failed draft and fix the ledger, evidence, or renderer prompt before using
the report.

## 4. Charter contamination, the most common way runs die silently

`autoresearch_loop.py` injects `project_charter.md` verbatim into the mutator
prompt every turn. Anything you write to motivate, justify, or explain the
target in the charter becomes a turn-1 cheat sheet.

**The rule.** The charter may describe *that* a target exists and *how* grading works. It must not contain:

- the target functional form (even as an example, even in LaTeX, even "hypothetically")
- target parameter values
- worked derivations of the target representation (reparameterizations, limits, factorizations)
- prose that names the specific mechanism the mutator is supposed to discover

For hidden-target experiments, the target itself lives outside the loop-visible
project files.

**The proof case.** [GP-023](../../research_areas/seams/substrates/planck/GP-023_ontology_trap_planck_mechanism_seam.md) sandbox_07, 2026-04-14. Two separate mutators transcribed the charter's derivation on iter 1 and "recovered" the hidden target to six decimal places. Neither run was diagnostic. After scrub, iter 1 returned 0 with the mutator genuinely searching.

**The check.** Before sealing a charter:

1. `sha256sum project_charter.md`, record in the pre-reg.
2. Grep the charter for any substring of the target form and its parameter names.
3. Ask: if a stranger read only this charter, could they reconstruct the target? If yes, scrub.

**The pre-run discipline.** Before the first `autoresearch_loop.py` invocation,
a controlled hidden-target scaffold must pass: the charter contamination scrub
and strip test, an identifiability check, a sealed pre-registration, a smoke
gate, and a dry-run of the sealed command. A sandbox missing any of these is a
warm-up, not a data point.

---

## 5. The gate battery, how to read a score

A ZTARE score is a compression of a gate battery, not a fitness number. When you look at a run, look at which gates passed and which failed, not at the headline.

Standard deterministic gates currently enforced:

- **Fit contract** (`validator/core/information_yield.py` and the fit/gate call sites), the declared `fit_declaration` block must be algebraically consistent with the Python `I_model` body. Catches "fit a different function than you claim to fit" gaming.
- **Farther-tail global residual** (`validator/tests/runner_r4_fixture_regression.py`), out-of-window residual sampled beyond the fit window. Catches finite-window surrogates that terminal-only tests would miss. [GP-046](../../research_areas/seams/protocol/GP-046_asymptotic_regime_claim_discipline_seam.md) is the empirical anchor.
- **Fixture regression**, closed-form fixtures whose expected output is pinned. Any drift flags immediately.
- **Fit-primitive contract ([GP-035](../../research_areas/seams/engine/grammar/GP-035_mutator_missing_fit_primitive_seam.md))**, always injected. Prevents mutators from declaring a fit that cannot run.
- **NaN-stub fail-closed**, any primitive returning NaN/inf fails the turn. No "robust to missing data" dodges.

Honeypot mode (`rubrics/honeypot_minimal.json`) replaces the gate battery with a loose discovery-oriented rubric. Honeypot scores are not comparable to standard-run scores. Use honeypot to *find new gates*, not to claim a result. See §8.

---

## 6. Pre-registration format

A pre-reg is a single markdown file for controlled experiments whose target
must stay hidden until close. Public project intake is the normal path
for external readers; sealed pre-regs are for experiments where target leakage
would destroy interpretability. Minimum structure:

```markdown
# <experiment-id> pre-registration
Status: sealed | in-flight | closed
Sealed: YYYY-MM-DD HH:MM:SS
Charter fingerprint: sha256:<hash of project_charter.md at seal time>

## Decisive question
One sentence. The smallest question whose answer changes what to build next.

## Falsifiable claim
One sentence. Must be falsifiable by the discriminating test below, not by general skepticism.

## Discriminating test
What command will run. What rubric. Which gates. Expected pass/fail pattern under each rival hypothesis.

## Success criterion
Binary. "Champion score ≥ X on gate Y", not "seems to work better."

## What would make this uninterpretable
Contamination paths, known escape hatches, and maintainer-patch temptations.
Written *before* the run so a later "success" can be audited against them
(Mungerian inversion, AGENTS.md §6c).
```

The pre-reg is sealed by dry-running the exact sealed command string and pinning
all implicit defaults (model family, rubric path resolution). A pre-reg that has
never been dry-run is not sealed. See AGENTS.md for the full sealed-experiment
rule.

---

## 7. Outcome taxonomy

Controlled experiments close as one of four outcomes. Write the closing status
on the pre-reg, then publish the safe summary in the appropriate historical
seam or review artifact.

- **A, Confirmed.** Discriminating test passed the pre-registered success criterion. The falsifiable claim survives.
- **B, Falsified.** Discriminating test ran cleanly and returned the negative. The claim is dead. This is a successful experiment.
- **C, Inconclusive (system).** The run revealed a problem with the system
  under test, such as a gate bug, contamination path, or maintainer-patch drift.
  The claim is neither confirmed nor falsified. The system gets a new
  historical record; the original claim goes back to open.
- **D, Withdrawn.** The claim stopped being decisive before the test ran (the question changed, the blocker shipped, the direction was abandoned). Close without a result.

If you cannot pick one of these, the experiment is not closable. Keep it open or rewrite the pre-reg.

Public project intake and ordinary in-loop runs should still use the route and
trace statuses described above. Do not force an A/B/C/D label onto a project
that was never designed as a sealed discriminating test.

---

## 8. Honeypot mode, bug-bounty, not discovery-proof

Honeypot mode (`rubrics/honeypot_minimal.json`) uses a loose rubric that rewards surprise (40), failure-mode revelation (35), falsifiability (25), and a gaming-detection bonus (+15). Max score 115.

**What honeypot is good at.** Finding gates the standard suite is missing. A champion that scores high in honeypot by exposing a structural bug in a prior model is a bug report: it names something the normal run would have missed. Those bugs become candidates for new deterministic gates in kernel hardening.

**What honeypot is not.** It is not a discovery proof. A 115/115 honeypot run does not mean the validator recovered the law; it means the rubric could not disqualify the champion. Read the judge's "weakest point" and treat it as the handle to grab next.

**Integration pattern (bug-bounty loop).** A standard run produces a champion → honeypot red-teams it → if honeypot breaks it, either the standard run has a gap or the champion has a weakness the gate suite did not catch. Either way, the next action is a new gate, not a result claim.

---

## 9. Replication procedure

To reproduce a closed controlled experiment from this repo:

1. Find the closed seam in `research_areas/seams/` and the sealed pre-reg alongside it. The charter fingerprint in the pre-reg is the canonical charter state for that run.
2. Check the current `project_charter.md` hash against the pre-reg fingerprint. If they differ, the charter has drifted, replication must use the pinned version from git at the pre-reg seal time, not `HEAD`.
3. Run the exact sealed command string from the pre-reg. Do not substitute a "same thing" alternative, pinned defaults matter.
4. Compare the closing outcome (A/B/C/D) to the seam's recorded outcome. A divergence is a finding; file it as a new experiment, not as a correction to the old one.

Sealed artifacts (pre-regs after seal, scoring sheets) are never edited in
place. Corrections go in post-mortems. Do not invent addenda or supplements;
use the correction vocabulary the project already has.

To reproduce ordinary public project intake:

1. Validate the intake file:
   `ztare project intake validate --path <intake.json>`.
2. Run the trace:
   `ztare autoresearch trace --project <project> --rubric <rubric> --intake <intake.json> --json`.
3. If the trace is partial, run the named recovery command or record the
   limitation as a non-claim.
4. Only then run the expected command recorded in the intake file.
5. If a report is generated, inspect `synthesis/report_support_contract.json`
   before citing `Report.md`.

If the intake file is for a general project rather than a scientific experiment,
keep the same evidence rule: bounded claim, source refs, evidence refs,
non-claims, next falsifier, and one parsed route/run command. Do not replace
that with a narrative deliverable or a broad consulting-style conclusion.

---

## 10. Where to look

- `AGENTS.md`, standing rules, visibility rules, and hard rules. Compatible agent runtimes load it at repo entry.
- `docs/guides/workflow.md`, reviewer-facing workflow reference.
- `docs/concepts/architecture.md`, kernel internals, primitives, validator surface.
- `docs/concepts/capabilities.md`, current command-to-capability map and
  bounded evidence levels.
- `research_areas/seams/`, closed historical records (public). Start here if you want to inspect closed experiments and provenance.
- `examples/project_packets/`, public fixtures for ready and malformed
  project intake.
- `docs/guides/cli.md`, command reference for `ztare project`, `ztare
  autoresearch route`, `ztare autoresearch trace`, and related inspection
  commands.
- Maintainer-only live strategy, credentials, and in-flight sealed targets are
  deliberately absent from the public path.

If this document and AGENTS.md disagree, AGENTS.md wins and this document is stale, flag it.
