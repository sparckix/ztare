---
description: "Command-line entry points for the workbench: demo, smoke, gates, loop, and the public model-free surfaces."
---

# The `ztare` CLI

> Up: [`docs/README.md`](../README.md)

A single command entry point for the zero-trust workbench's
human-facing surface. Replaces `cd repo && python scripts/public/control/<name>.py …`
with `ztare <subcommand> …`.

The CLI is deliberately a thin user route. Reusable behavior lives under
[`src/ztare`](../../src/ztare); files under
[`scripts/public/control`](../../scripts/public/control) are public adapters for
Make targets, local scripts, and compatibility entry points. A new command
should put the product behavior in `src/ztare/...` first, then expose it through
`ztare ...` and, when needed, a thin control script.

## Scope

The CLI covers the ZTARE workbench's human-facing surface only. The
governance / org side (roles, mandates, role daemons, closure
daemons, OKR-tree polling) belongs to the sibling
[`cognitive-firm`](https://github.com/sparckix/cognitive-firm) project
and is deliberately not exposed here. Reviewers who want to compose
ZTARE with a governed organisation should treat that repository as the
reusable org-kernel source and this repository's `org/` tree as the ZTARE
tenant overlay.

## Subcommands

| Command | What it does | Underlying script |
|---|---|---|
| `ztare forecast <verb> …` | Forecast-pool, calibration DB, and experiment execution operations | `scripts/public/control/forecast/` plus selected experiment runners |
| `ztare leanmill <verb> …` | LeanMill governed proof search: station control, source review, proof audit, harness runs | `scripts/public/control/leanmill/` |
| `ztare research <verb> …` | Advisory research scaffold: eigenquestion (the question that matters most), isomorphism (what is this like) | `src/ztare/research_director/` |
| `ztare bundle <verb> …` | Sealed-bundle run / verify | `bundle_run.py`, `bundle_verify.py` |
| `ztare charter …` | Project-charter commit | `charter_commit.py` |
| `ztare routine-review …` | RD routine reviews | `rd_routine_review.py` |
| `ztare action-intel …` | Action intelligence read surface: decisions, routes, and outcome impact | `action_intelligence.py` |
| `ztare autoresearch …` | In-loop autoresearch run and read-only trace/projection/replay surfaces | `Makefile` targets plus report modules |
| `ztare forensic-workbench …` | Local Project Workbench state, review receipts, and saved next steps | `forensic_workbench_state.py`, `forensic_workbench_review.py`, `forensic_workbench_action.py` |
| `ztare project ...` | Public project userland before run readiness: walkthrough, source files/checks, evidence-output binding, project-local checks, create, prepare, seal, intake, optional prep ledger | `generate_substrate.py` + `Makefile` targets + workspace modules + `substrate_queue.py` |
| `ztare synth ...` | Build or refresh a project report support contract and synthesis outputs | `src/ztare/synthesis/synthesize.py` |
| `ztare card build|verify|open ...` | Build or verify a portable project claim card from the synthesis contract | `src/ztare/workspace/claim_card.py`; optional wrapper `scripts/public/control/claim_card.py` |
| `ztare substrate …` | Compatibility namespace for the same project/data surface commands | same implementation as `ztare project …` |
| `ztare eigenquestion …` | Advisory eigenquestion proposal + explored-class evidence lint | `eigenquestion_generator.py` |
| `ztare mine …` | Weekly reflexive-mining orchestrator | `reflexive_mining_weekly.py` |
| `ztare primitive …` | Primitive catalog / amnesia health checks | `Makefile` + `primitive_amnesia` |
| `ztare audit …` | Gate, coverage, graph-capability, forecast-capability, and move-card routing audits | selected `Makefile` targets and report modules |
| `ztare arch-validate …` | Architecture-map drift checks | selected `Makefile` targets |
| `ztare version` | Version, git commit, and Python version | package metadata + git |
| `ztare doctor` | Environment health check | package, script, tool, and env-var probes |
| `ztare completion <shell>` | Shell completion script emitter | CLI completion generator |

`ztare leanmill` verbs include station control (`schedule`, `run`,
`andon`, `triage`, `backlog`), source review (`source-scout`,
`source-search`, `source-review`, `source-bind`), proof work
(`target`, `autoformalize-notes`, `solver`, `slice-prep`, `proof-audit`, `external-proof-audit`),
and read models (`ui-state`, `intel`, `credit`, `growth`, `convert`).
Historical provenance: the older GNN lemma-relevance seam is
[`GP-225`](../../research_areas/seams/engine/lean/GP-225_gnn_lemma_relevance_ranker_seam.md);
newer governed-DAG proof search is tracked separately in the LeanMill docs.

`ztare bundle` verbs: `run`, `verify`.

`ztare audit` verbs: `gates`, `effectiveness`, `coverage`,
`graph-capability`, `forecast-capability`, and the move-card router
(`move-card-router`).

`ztare arch-validate` verbs: `ex-ante`, `ex-post`.

## Pass-through `--help`

For any subcommand, `--help` flows through to the underlying control
script's argument parser or verb router. So `ztare forecast --help`
shows the user-facing forecast verb list; `ztare bundle run --help`
shows the `bundle_run.py` flags; and so on. The CLI's own help
(`ztare --help`) is short by design.

`ztare forecast` exposes three kinds of forecast surfaces:
public control scripts, package modules, and registered project tools from the
forecasting-calibration program. Help output labels those kinds without making
project-local file paths the public vocabulary. Use `ztare doctor` when you
need the exact target-resolution paths. Public control surfaces include
`pool`, `resolve`, `score`, `ingest-smoke`, `elo-refresh`, `brier-elo`, and
`resolve-open-metaculus`. Package surfaces include `capability-audit`,
`calibration-stats`, and `calibration-db`. The remaining verbs are registered
project-program tools.

## Repository root discovery

The CLI runs the control scripts via subprocess and needs to know
where the repository root is. It tries, in order:

1. `$ZTARE_REPO` environment variable.
2. Walk up from the installed `ztare.cli` module's location.
3. Current working directory if it contains `scripts/public/control/`.

For a `pip install -e .` checkout this resolves automatically. For a
plain `pip install ztare` from PyPI, the control scripts live inside
the installed package data, set `$ZTARE_REPO` to the repository
checkout where ledgers and `org/` state actually live.

## Adding a subcommand

Each new subcommand is one entry in the `_SUBCOMMANDS` table in
[`src/ztare/cli.py`](../../src/ztare/cli.py): a help line plus a
callable that takes the remaining argv and returns an exit code.
Most callables are one-liners that delegate via `_delegate(script,
rest)`. Multi-verb subcommands (LeanMill, bundle) define a small
verb-router function alongside.

Subcommand names should be nouns or noun-verb pairs (e.g.
`routine-review`), match the underlying script's capability rather
than its implementation file, and stay short.

## Examples

```bash
# Forecast pool and calibration surfaces
ztare forecast pool smoke
ztare audit forecast-capability --json
# Move-card routing audit
ztare audit move-card-router --json
ztare forecast calibration-stats --help
ztare forecast calibration-db --help

# Forecasting experiment execution surfaces
ztare forecast cutoff-panel-run --mode preview --max-calls 6
ztare forecast nurture-score --pilot-id <pilot_id> --queue <dispatch_queue.jsonl>

# LeanMill: one-shot station-scheduler plan, then start the 24/7 worker
ztare leanmill target --title "Example target" --target "State the theorem or formalization target." --notes-file notes.md --json
ztare leanmill target --title "Example target" --target "State the theorem or formalization target." --notes-file notes.md --save --yes --json
ztare leanmill target --project my_project --title "Project target" --target "State the theorem or formalization target." --notes-file notes.md --save --yes --json
ztare leanmill autoformalize-notes ztare_proofs/leanmill-formalizations/blueprints/example_target_blueprint.md
# Project-local LeanMill layout: projects/<project>/leanmill/{targets,lean,notes,history}/
ztare leanmill schedule --contract analytics/public/leanmill/_legacy_lemma_relevance/...
ztare leanmill run --max-rows 100

# Bundle: run a sealed candidate, then verify
ztare bundle run --substrate demo_claims --rubric demo_claims
ztare bundle verify --bundle path/to/bundle.json

# Project charter commit
ztare charter --substrate demo_claims --hypothesis-class S

# Action intelligence read
ztare action-intel materialize --no-write
ztare action-intel record-agentic-route --route-json autoresearch_route.json --decision-id decision_demo_claims_route

# Project/data userland: create a project surface, prepare it, then seal it.
# Replace demo_claims with your own project/rubric slug.
ztare project walkthrough
ztare project walkthrough --project demo_claims --rubric demo_claims --task "test bounded claim X" --bounded-claim "bounded claim X holds on fixture Y" --source-ref paper.md --evidence-ref projects/demo_claims/workspace/min_repro.json --non-claim "not a full replication" --next-falsifier "run the full setup from a clean checkout" --intake-out demo_claims_intake.json
ztare project source-init --project demo_claims --rubric demo_claims
ztare project source-check --project demo_claims --json
ztare project source-file add --project demo_claims --filename notes.md --source-type source_evidence --kind project_note --body "Paste the source note here." --json
ztare project source-file edit --project demo_claims --relative notes.md --source-type source_evidence --body "Updated source note." --json
ztare project source-index --project demo_claims
ztare project evidence-bind --project demo_claims --json
ztare project evidence-replay --project demo_claims --json
ztare project claim-support --project demo_claims --json
ztare project evidence-gap list --project demo_claims --json
ztare project evidence-gap justify --project demo_claims --gap-id gap1 --reason "Covered by the bounded non-claim; no extra public fetch is needed." --json
ztare project check --project demo_claims --rubric demo_claims --json
ztare project new --help
ztare project prepare --project demo_claims --rubric demo_claims
ztare project seal --project demo_claims --rubric demo_claims

# Project intake: explicit boundary before run readiness
ztare project intake create --path demo_claims_intake.json --project demo_claims --rubric demo_claims --task "test bounded claim X" --bounded-claim "bounded claim X holds on fixture Y" --source-ref paper.md --evidence-ref projects/demo_claims/workspace/min_repro.json --non-claim "not a full replication" --next-falsifier "run the full setup from a clean checkout" --expected-command "ztare autoresearch route --task 'test bounded claim X' --project demo_claims --rubric demo_claims"
ztare project intake draft-from-compiled --project demo_claims --path projects/demo_claims/demo_claims_intake.json
ztare project intake draft-from-compiled --project demo_claims --path projects/demo_claims/demo_claims_intake.json --repair-moved-sources
ztare project intake validate --path demo_claims_intake.json
ztare project brief-edit --project demo_claims --intake projects/demo_claims/demo_claims_intake.json --field next_falsifier="Run the next source-backed check." --json
ztare project intake falsify --path demo_claims_intake.json --remove-ref 'evidence_refs[1]'
ztare project intake validate --path demo_claims_intake.json --source-preflight
ztare project intake enqueue --path demo_claims_intake.json
# Optional prep ledger for missing intake-readiness artifacts; not a scheduler
ztare project prep-ledger add --task "prepare minimal reproduction for paper X" --kind minimal_reproduction --project demo_claims --rubric demo_claims --requested-artifact projects/demo_claims/workspace/min_repro.json
ztare project prep-ledger add-from-route --route-json autoresearch_route.json
ztare project prep-ledger list
ztare project prep-ledger resolve-next --result ready_for_autoresearch --reason "minimal reproduction and cost estimate are present" --artifact-ref projects/demo_claims/workspace/min_repro.json

# Autoresearch: route a bounded task, run in-loop, then inspect the read-only projection
ztare autoresearch route --task "test bounded claim X" --project demo_claims --rubric demo_claims > autoresearch_route.json
ztare autoresearch route --task "test bounded claim X" --project demo_claims --rubric demo_claims --record-decision-id decision_demo_claims_route
ztare autoresearch route --task "test bounded claim X" --project demo_claims --rubric demo_claims --record-decision-id decision_demo_claims_route --queue-missing-surface
ztare autoresearch run --project demo_claims --rubric demo_claims --intake demo_claims_intake.json --preflight-only
ztare autoresearch run --project demo_claims --rubric demo_claims --intake demo_claims_intake.json --iters 10
ztare autoresearch run --project demo_claims --rubric demo_claims --intake demo_claims_intake.json --iters 10 --mutator <model> --judge <review_model> --inverter <inverter_model>
ztare autoresearch run --project demo_claims --rubric demo_claims --intake demo_claims_intake.json --agent-mutator --agent-runtime codex
ztare autoresearch run --project demo_claims --rubric demo_claims --intake demo_claims_intake.json --agent-mutator --agent-judge --agent-committee --agent-inverter --agent-runtime codex
ztare autoresearch workbench-recommend --prompt-only
ztare autoresearch workbench-recommend --agent-recommender --agent-runtime codex
# Legacy spelling kept for older scripts:
ztare autoresearch substrate-recommend --prompt-only
ztare autoresearch projection --project demo_claims --out demo_claims_projection.json
ztare autoresearch trace --project demo_claims --rubric demo_claims --intake demo_claims_intake.json --model <model> --json
ztare autoresearch carrier-replay --project demo_claims --json
ztare autoresearch hillclimb-audit --project demo_claims
ztare autoresearch hillclimb-audit --json --limit 20
ztare autoresearch hillclimb-audit --recovery-queue --recovery-limit 10 --json
ztare autoresearch hillclimb-audit --recovery-queue --recovery-intake-status ready
ztare autoresearch consequence-audit --project demo_claims --json
ztare autoresearch consequence-audit --json
ztare autoresearch rubric-mode-audit --json
ztare autoresearch rubric-mode-audit --rubric rubrics/demo_claims.json
ztare autoresearch rubric-mode-audit --freshness-days 14
ztare autoresearch rubric-mode-audit --strict
ztare autoresearch health
ztare autoresearch health --project demo_claims --rubric demo_claims --json
ztare autoresearch health --json --strict
ztare autoresearch control-demo --json
ztare autoresearch parent-utility --json
ztare autoresearch operations-intelligence --json --no-markdown --out ztare_intel.json
ztare autoresearch dispatch-audit --json
ztare autoresearch dispatch-canary --contract mutator --runtime codex --live --json
ztare autoresearch dispatch-canary --contract judge --call-site judge --runtime codex --live --json
ztare autoresearch dispatch-canary --contract committee --call-site committee --runtime codex --live --json
ztare autoresearch dispatch-canary --contract inverter --call-site inverter_review --runtime codex --live --json
ztare autoresearch subscription-outcomes --json
ztare autoresearch dispatch-parity --json
ztare autoresearch dispatch-parity --contracts text,mutator,judge,committee,inverter --runtime codex --live --json

# Project Workbench: inspect the live project object used by the browser.
ztare forensic-workbench project-state --project ops_root_cause_diagnosis_demo --json --strict
ztare forensic-workbench settings get --json
ztare forensic-workbench settings save --set ZTARE_WORKBENCH_MODEL=claude --set ZTARE_WORKBENCH_MODEL_FALLBACK=0 --json

# Project Workbench: apply an inspectable review file copied from the workbench.
# --project-check takes the project-check slug, then refreshes the project data.
ztare forensic-workbench brief-edit --project ops_root_cause_diagnosis_demo --field next_falsifier="Check the causal direction against source timing." --json
ztare forensic-workbench source-file add --project ops_root_cause_diagnosis_demo --filename timing_note.md --source-type source_evidence --kind project_note --body "Source timing note."
ztare forensic-workbench source-action --project ops_root_cause_diagnosis_demo --action evidence_prepare --json
ztare project evidence-fetch --project ops_root_cause_diagnosis_demo --severity degrading --max-fetches 1 --search-backend openai --no-auto-compile
ztare forensic-workbench report-action --project ops_root_cause_diagnosis_demo --action check_readiness --json
ztare forensic-workbench run-project-check --project ops_root_cause_diagnosis_demo --json
ztare forensic-workbench save-charter --project ops_root_cause_diagnosis_demo --from project_charter.md --json
ztare forensic-workbench apply-review --project ops_root_cause_diagnosis_demo --project-check report_support --from ops_root_cause_diagnosis_demo_report_support_review.json
ztare forensic-workbench save-scoring-guide --project ops_root_cause_diagnosis_demo --rubric ops_root_cause_diagnosis_demo --from rubric.json --json
ztare forensic-workbench save-project-file --project ops_root_cause_diagnosis_demo --from prepared_project_file.json --json
ztare forensic-workbench save-research-map --project ops_root_cause_diagnosis_demo --from prepared_research_map.json --json
make forensic-workbench-data WORKBENCH_PROJECT=ops_root_cause_diagnosis_demo

# Advisory eigenquestion rotation
ztare eigenquestion propose --project demo_claims
ztare eigenquestion status --project demo_claims
ztare eigenquestion validate --project demo_claims

# Primitive catalog and semantic atlas health
ztare primitive health
ztare primitive health --semantic-live --eval
make move-card-router-audit  # fixed paraphrase audit for move-card routing
make move-card-atlas-build   # refresh when router audit reports a stale card atlas
```

`ztare autoresearch route` returns a JSON decision object. Check the
move-card route fields before acting on it: the normal in-loop workbench route
should carry `OP-AWR-01` with matched terms, score, and route mode. That field
is the compact provenance for why the task entered, prepared for, or stayed
outside the autoresearch kernel. The same JSON includes
`plan_preview`: a no-model-call execution preview with the first command to
run, dependency order, worker roles, iteration budget source, fallback policy,
expected outputs, and the main quality risk to inspect before spending tokens.

`project walkthrough` is the guided path. With no arguments, it runs a
no-write demo over the bundled ready and malformed intake files. Use
`ztare project walkthrough --ops-demo` for the concrete operational-diagnosis
fixture: typed local sources, bounded root-cause claim, source-claim graph,
trace command, preflight, and optional in-loop run. With project arguments and
`--intake-out`, it writes an intake file, validates it, and prints the next
trace/route commands. Its JSON output also includes a `command_plan` with
three phases: `source_and_evidence_prep` (pre-run project prep),
`read_only_trace` (inspection only), and `in_loop_gate` (the route/run boundary).
Each phase carries a `ready` flag so a caller can see whether to keep preparing
the source surface or move to the in-loop gate. It is a deterministic tutorial
over the same intake primitives, and stays clear of any scheduling role. `--packet-out`
remains a compatibility alias.

`project source-init` creates the portable source-ingest surface:
`projects/<slug>/raw/`, `projects/<slug>/workspace/`, and an empty
`projects/<slug>/raw/source_type_map.json`. It does not create fake evidence,
launch autoresearch, or enqueue out-of-loop work. Type raw documents with
frontmatter or the source-type map before running
`ztare forensic-workbench source-action --project <project> --action evidence_prepare`.
`source_evidence` is the type allowed to support immutable facts and
constraints. `project source-check` runs the same source-type preflight without
calling a model or compiling evidence. The Make target runs that preflight
again before workspace update and evidence compilation.
`project source-index` is the next offline checkpoint: it writes
`workspace/source_index.json`, `workspace/workspace_meta.json`, and
`workspace/source_index_receipt.json` from typed raw sources without an LLM call.
The index lists every supported text source with a hash even when the extraction
character budget is exhausted. `chars_used` only says how much text would be fed
to extraction. Trace treats the receipt as valid only while both indexed
artifacts still exist and match the receipt hashes. Use `--json` when a script
needs the receipt paths. It still does not extract notes, merge evidence,
compile evidence, or launch the loop.
`project evidence-bind` is a compatibility checkpoint for older compiled
evidence manifests that tracked source provenance but did not hash rendered
outputs. It writes `workspace/evidence_output_binding_receipt.json`, binding the
current `evidence.txt` and optional compiled-evidence artifacts to the current
compile-provenance file hash. It does not recompile evidence, refresh stale raw
source provenance, prove that the current output existed at compile time, or
launch the loop. If any bound file changes afterward, trace reports stale
evidence output.
Newer evidence compiles also write
`compiled_evidence_replay_manifest.json`. That manifest is the preferred
identity surface for compiled evidence: it binds source rows, workspace
snapshot or raw-cache replay mode, structured input hash, support-binding
hash, evidence output hash, and evidence-gap action hash. The rendered
markdown can carry date metadata, so scripts should compare the manifest
hashes; `evidence.txt` alone is not a reliable replay key.
`project evidence-replay` verifies that manifest against current files and
exits non-zero if compiled evidence, intake JSON, gap action, workspace
snapshot, or raw-cache artifacts no longer match. It is offline and does not
refresh evidence. Health reports summarize these checks as evidence readiness:
raw source index freshness, compile provenance, rendered output binding, and
replay status. If no replay manifest exists and compile provenance does not
require one, human-facing trace and health summaries report replay as
`not_required`. The raw carrier status is still retained for audit. A stale or
invalid required replay manifest remains a blocker.
`project claim-support` classifies compiled-evidence claim rows against the
current source index. It reports direct source support, synthesized support
across sources, local/seed-only support, mixed support, missing source refs,
and unsourced rows. It is deterministic and does not claim semantic entailment.
Use it as the source-binding demotion surface before a report calls a claim
source-backed. It also verifies the referenced raw source files against the
source-index hashes and emits bounded previews, so stale or missing source
context blocks the audit, with no silent pass to support.
`project evidence-gap list` is the read-only inspection step. It reports active
gap rows after resolution/justification filtering and returns the same next
action contract used by evidence compilation, so users can see whether the next
move is public-source recovery, a local verifier, or no action.
`project evidence-gap justify` is the offline counterpart to trace's "fetch or
justify" recovery language. It writes `workspace/evidence_gap_resolutions.json`
for the exact current gap row, including a hash of that row and optional local
evidence refs. It does not edit `latest_evidence_gaps.json`, fetch public
sources, or launch the loop. If the judge later changes the gap row, the old
resolution no longer retires it.
Use `--source active` when `project evidence-gap list` or `autoresearch trace`
is reading a champion gap file when it should read `latest_evidence_gaps.json`. The
receipt remains bound to the exact row that was active.
Evidence-gap producers should set the route contract fields directly:
`recovery_kind`, `recovery_channel`, `required_surface`, `can_public_fetch`, and
`in_loop_consumable`. Public rows use `public_evidence` plus
`out_of_loop_evidence_recovery`. Local verifier, fixture, code/log, preflight,
receipt, and in-loop discriminator rows use `local_verification` plus
`in_loop_focus_receipt`. Older rows are still inferred, but new integrations
should not depend on wording in `description` or `fetch_query`.

Project intake is pre-run userland. Prefer `ztare project ...` in new docs
and scripts. `ztare substrate ...` remains a compatibility namespace for the
same implementation. The `project intake` and prep-ledger commands record bounded
tasks, sources, evidence references, non-claims, expected commands, and missing
prep artifacts before a task enters the validation engine. They do not execute
out-of-loop RD agent work, and they do not schedule autoresearch iterations.
Use them when the project surface needs to be made auditable before
`ztare autoresearch route` or `ztare autoresearch run`.
`project intake enqueue` is a source-ready handoff and requires the local
source preflight to pass. If intake is blocked on source files, source
typing, or evidence artifacts, record the concrete prep item in
`project prep-ledger`; leave the file unenqueued until the block clears.

`autoresearch route` is the boundary check. It decides whether a task has the
bounded claim, stable evaluator, rubric, and artifact surface required for an
in-loop run. If not, it returns a prep decision that can be recorded in
the intake ledger. When the project already exposes raw source, source-index,
evidence, or compile-provenance surfaces, the router also runs the trace-local
source/evidence preflight and refuses loop entry on stale or blocked trace
surfaces.

`autoresearch trace` is the read-only project inspection path. It reports the
project-intake boundary when `--intake` is supplied, raw file count,
evidence readiness, claim-support status, workspace source-index state,
source/provenance freshness against the current raw source hashes, derived
constraints, eval history, graph records, prediction receipts when present,
projection summary, bounded trace-local health, missing surfaces, readiness,
and exact next commands. If a replay manifest exists or compile provenance
names one, trace treats a stale replay manifest as a run-readiness blocker and
points to `ztare project evidence-replay --project <project> --json` for
diagnosis. If replay is optional and absent, brief output shows
`replay=not_required`, which keeps the missing manifest from reading as hidden
debt. Claim-support demotions are surfaced for reporting and review, but do
not by themselves block run readiness.
Its literal `carrier_chain` field is the compact first read, listing each admission
surface, status, blocking flag, and recovery command in source-to-loop order.
The default text output also renders this as `carrier_chain_table`. `--brief`
renders the human first-read view and `--json` preserves the full
structured rows for scripts.
`make synth` reuses the same trace surface for projects with autoresearch
artifacts: it writes `synthesis/autoresearch_review_context.json` and feeds that
compact review context into the report renderer, alongside the ordinary project
artifacts. This keeps reporting tied to readiness, graph-focus gaps, provider
failures, and next actions, reaching past a bare summary of `history/`. The
synthesis path also writes `synthesis/report_support_contract.json`, passes it
to rendering/refinement/QA, blocks high-severity unsupported additions and
overclaims, and runs a bounded QA-guided repair loop before failing closed. A
blocked support contract is stronger than model QA: it prevents final report
promotion even if the QA step scores the prose highly. The
contract includes `synthesis_input_binding`, which blocks stale or unbound
generated ledgers after artifact content changes, and
`report_action_authority`, which separates actions that can be recommended now
from conditional branches, deferred work, and forbidden claim upgrades. Use
`ztare forensic-workbench report-action --project <project> --action check_readiness`
to refresh that deterministic contract without model calls.
After an in-loop iteration has rendered a mutator briefing, `carrier_chain`
also includes `mutator_briefing`; that row reports the latest briefing record
count and any graph-focus receipt that was actually surfaced to the candidate
prompt, including evidence-gap ids/targets or a rubric-enabled probability-DAG
focus.
`prediction_contracts` is also part of the chain when prediction rows exist:
it remains a score-only trace row unless it reports invalid forecast-pool,
membrane, or routing authority claims.
When graph-derived focus rows come from evidence gaps, `graph_rd_actions[]`
also carries the exact gap ids and targets so an in-loop artifact can address
the row identity directly, down to the specific gap.
Those graph-derived rows also carry move-card route ids for `OP-GDC-01`, which
makes the graph-decision action path auditable as a distinct path, set apart from ordinary
prep rows.
It also runs the same rubric/project launch preflight that `make
experiment-loop` enforces when a rubric is resolved. When intake is supplied,
`kernel_entry.can_enter_kernel=true` means the intake file, source/evidence surfaces,
trace records, and launcher preflight all agree; `ztare autoresearch run
--intake <path>` consumes that contract before launching the loop.
Use `ztare autoresearch run --preflight-only --intake <path>` when you want the
same launch and intake-boundary check to write run boundary telemetry without
running baseline judge evaluation or iteration work.
After that receipt is fresh, `ztare autoresearch trace` may report
`plan_preview.status=ready_for_bounded_run` and make the bounded run the next
recommended command. Re-run preflight only when the project, intake, or
run-readiness state changed.
In-loop runs seal the requested model family by default: `make experiment-loop`
passes `--no_model_fallback` unless you opt in with `MODEL_FALLBACK=1`. The CLI
spells the same exception as `ztare autoresearch run --allow-model-fallback`.
Use the default for comparable runs and pre-registered checks. Use the opt-in
only when continuity matters more than model-family provenance.
`complete_trace` means the raw-source, workspace, evidence, projection, and
health surfaces are all present for a historical run; `ready_for_in_loop_candidate`
additionally means the supplied or discovered intake file validates and no
trace record is blocking prep.
`ready_for_first_in_loop_run` is allowed to be `partial_trace` because a fresh
project has no `eval_history` yet. In that case `blocking_missing` should be
empty and `history_missing` should name the absent run history. Other
`partial_trace` reports named missing trace surfaces and recovery commands.
`blocked_on_out_of_loop_prep` means a trace record, usually the source-claim
graph, found prep debt that belongs outside the autoresearch loop. Public-source
evidence gaps route to `ztare project evidence-fetch ...` and keep
`route_preview.can_run_now=false` until the debt is cleared or justified.
`ztare project evidence-fetch` now requires an explicit public recovery contract by
default (`recovery_kind=public_evidence`, or equivalent public-fetch booleans).
Rows classified only by legacy prose inference are skipped until promoted. Use
`ALLOW_INFERRED_PUBLIC=1` only when intentionally replaying old rows.
After evidence compilation, `workspace/evidence_gap_brief.md` selects the next
active gap and names whether it is public-source recovery or local verification.
`workspace/evidence_gap_action.json` carries the same selected action for
scripts or future UI surfaces.
Use `--evidence-search-backend auto|openai|anthropic` when you want the
suggested evidence-fetch command to name a specific public-source search
backend separately from the model label rendered with `--model`.

`autoresearch carrier-replay` is the batch integrity check for projection
read-model rows. Use it when you want to inspect one or more projects for stale
latest-eval overlays, missing artifact refs, unrecorded worker provenance,
missing transport, missing failure signatures, or absent action links. It does
not run the loop or call a model.
Local verifier gaps, such as preflight or falsifier-execution gaps, remain
in-loop focus receipts under `graph_rd_actions[]` and do not block route
readiness by themselves.
`blocked_on_launch_preflight` means the trace surfaces are otherwise ready but
`make experiment-loop` would fail before the first model call, commonly because
`project_charter.md`, `thesis.md`, or rubric launch rules are missing.
`source_index_stale` or `evidence_compile_stale` means raw sources changed after
the workspace source index or compiled evidence manifest was generated. Rerun
`ztare forensic-workbench source-action --project <project> --action evidence_prepare`
before routing.
When a project-intake file validates, `route_preview` uses its exact
`expected_command`; placeholders appear only for legacy or missing-intake
traces. It does not run out-of-loop agents, schedule iterations, or call a
model; `--model` only chooses the model label rendered in suggested
evidence-recovery commands. Use `--full-health` only when you also want the
aggregate health report. The default trace path stays local and bounded.
Trace JSON also exposes `plan_preview`, which is the read-before-run contract:
it shows the route decision, model-free preflight, paid loop step, expected
workspace outputs, and whether fallback is still disabled by default.
In JSON output, `project_intake.status=valid_packet` is a legacy status name. It means the intake shape,
project, rubric, and applicable missing-reference falsifier validated. Inspect
`project_intake.missing_ref_falsifier`: when local refs exist it should show
`status=passed` and the selected `source_refs[N]` or `evidence_refs[N]`. When an
intake uses only external refs it is skipped. Older receipts still expose
`project_packet` for compatibility. Use `readiness_canonical` for the current
intake-facing status name. `readiness` keeps legacy status IDs for old readers.
Use that status plus `route_preview.can_run_now` for the actual in-loop go/no-go.

`dispatch-parity` replays fixed typed contracts through the API and
subscription paths. The JSON report includes contract parity, per-contract
`quality_score`, and a latency/call-count `cost_proxy`. `--live` only promotes
the subscription leg.

`subscription-outcomes` reads run history only. Fresh rows can carry
prompt-free worker-dispatch receipts. The report separates completed
subscription receipt counts from aggregate transport rows.

`consequence-audit` is a read-only check for whether the listed kernel
mechanisms do something observable. It classifies each mechanism by consequence
type, names the consumer, samples the current evidence paths, and flags
mechanisms that are unobserved in the selected project or workspace.

`rubric-mode-audit` scans the rubric corpus for Newton/Kepler/calibration
coherence. It uses the same mode contract as launch validation and flags
invalid modes, Newton rubrics with missing projects, missing charters, or
missing secondary-observable sections, and Kepler rubrics that still carry
Generative Yield. Historical unset modes stay summarized. Unset modes with
recent run telemetry become attention rows. Use `--strict` when this should
fail the command while attention rows remain.

`health` aggregates the cheap kernel checks into one first page: dispatch
coverage, primitive-catalog freshness, mechanism consequences, in-loop fixture
status, graph capability, forecast capability, raw/evidence/constraint/projection/graph-record
trace health, rubric-mode attention, and hill-climb control evidence. Each component
includes a `next_command` pointing to the narrow audit that owns the details;
when health is scoped to a project, rubric, or workspace, those commands carry
the same scope. `evidence_gap` rows are non-blocking by default: they name
transport comparisons that are wired but not yet outcome-evidenced in the
selected scope. `coverage_opportunity` rows are weaker: they name dormant
optional mechanisms to exercise before claiming coverage.

For the raw-to-evidence trace itself, `make autoresearch-evidence-trace`
stays synthetic by default and becomes a real-project audit when called with
`PROJECT=<project> RUBRIC=<rubric> INTAKE=<project_intake.json> JSON=1`.
That path checks source freshness, compile provenance, evidence-output binding,
projection, route preview, and the guarded run command without making model
calls.

`fixtures` runs the cheap in-loop mechanism matrix. The text and JSON reports
name each mechanism's status, proof boundary, command to try next, and focused
test reference, so dormant mechanisms can be inspected without reading the loop
source first.

`control-demo` materializes a local replay project whose optional in-loop
controls are visible to the normal consequence audit. It is useful for checking
that parallel blitz, control follow-up policy, primitive-class rotation, and
eigenquestion preflight produce project-scoped artifacts. It also writes a
source-preflight-valid intake file for the generated replay, so the pre-run
handoff can be validated without launching the loop. It is not a live
research-quality or transport lift result.

`operations-intelligence` writes the fuller read-only operations report. Use it
when health points at route logging, source warnings, or workbench bypass
questions and you need the underlying action-guidance report behind the
compact first-page summary.
