---
description: "Reference of ZTARE make commands."
---
# ZTARE make commands

## Public first-run path

Run these before reading the full target list:

```bash
make first-run
```

`make first-run` runs the full offline public path:

```bash
make hello
make gaming-catalog-audit
make benchmark-evidence
make reasoning-compiler-capability-audit
make evaluator-hardening-frozen-check
make scope-boundary-audit
make public-terminology-audit
make smoke-public
make public-adversarial-smoke
make docs-check
```

- `make hello` is the smallest offline value demo: intake boundary check plus
  overclaim demotion, missing evidence, and next falsifier.
- `make gaming-catalog-audit` checks the public gaming behavior catalog against
  the live registry, promotion evidence, and hardening map.
- `make benchmark-evidence` checks the model-free public benchmark evidence and
  review-artifact coverage.
- `make reasoning-compiler-capability-audit` checks that public
  reasoning-compiler capability rows carry research anchors, local evidence
  refs, runnable anchors, and falsifiers.
- `make evaluator-hardening-frozen-check` explicitly verifies the frozen
  evaluator-hardening proof point and keeps the ordinary-review arm blocked
  until real frozen outputs exist.
- `make scope-boundary-audit` checks that broad public claim phrases have nearby
  non-claim or falsifier context.
- `make public-terminology-audit` checks that front-door public docs lead with
  understandable names and keep seam ids as provenance.
- `make smoke-public` runs the public runtime, forecast-pool, and
  action-intelligence smoke checks.
- `make public-adversarial-smoke` checks first-run doc drift, CLI help,
  command examples, runtime cleanup, project-intake fixtures, and public
  boundary language.
- `make docs-check` validates the public doc index, local links across the
  root entry files, `docs/`, and public examples, and the `papers/` public-tree
  hygiene rule.

`make benchmark-ordinary-review` is the opt-in fourth-arm path for the frozen
evaluator-hardening suite. When using `BENCH_ORDINARY_IMPORT`, every imported
row must include model, timestamp, prompt, and provider/runtime provenance. The
runner rejects provenance-free imported ordinary-review rows.
Use `make benchmark-ordinary-review-prompts` to export reviewer-safe prompt
sets with prompt hashes before collecting imported rows. Use
`make benchmark-ordinary-review-validate-import` before creating a run from
returned rows, and `make benchmark-ordinary-review-freeze-check` before
promoting a completed ordinary-review run into frozen-suite metadata.

## Advanced variables

  PROJECT=<project> RUBRIC=<rubric> MODEL=<model> MUTATOR_MODEL=<model> JUDGE_MODEL=<model>
  AGENT_MUTATOR=1 AGENT_JUDGE=1 AGENT_COMMITTEE=1 AGENT_INVERTER=1 AGENT_RECOMMENDER=1 [AGENT_RUNTIME=codex|claude]
  MODE=factory|honeypot  (default: factory; honeypot sets ITERS=50 and skips pre-run pipeline)

## Advanced run modes

  factory, standard tight-rubric mode with pre-run rubric review, 5-10 iters, synthesis output (default)
  honeypot, loose rubric, no pre-run, 50 iters, debate log is the output

## Full target list

  make setup-project PROJECT=<project> RUBRIC=<rubric> [MODEL=<model>]   # standard pre-run: fetch→prepare→review→pause
  make honeypot-loop PROJECT=<project> RUBRIC=<rubric> [ITERS=50]       # honeypot run: no pre-run, MODE=honeypot
  make source-check PROJECT=<project>                                    # offline raw/source typing preflight
  make evidence-prepare PROJECT=<project> MODEL=<model>                    # source-check + workspace-update + evidence-compile
  make evidence-prepare PROJECT=<project> MODEL=<model> EVIDENCE_LLM_TIMEOUT=120 EVIDENCE_LLM_RETRIES=1 EVIDENCE_DEBUG=1
  make workspace-update PROJECT=<project> MODEL=<model>
  make evidence-compile PROJECT=<project> MODEL=<model>
  make evidence-fetch PROJECT=<project> [SEVERITY=degrading] [MAX_FETCHES=3] [MODEL=<model>] [EVIDENCE_SEARCH_BACKEND=auto|openai|anthropic] [AUTO_COMPILE=0] [ALLOW_INFERRED_PUBLIC=1]
  make rubric-review PROJECT=<project> RUBRIC=<rubric> [MODEL=<model>]
  make loop PROJECT=<project> RUBRIC=<rubric> [ITERS=10] [MODE=factory|honeypot] [PREFLIGHT_ONLY=1] MUTATOR_MODEL=<model> JUDGE_MODEL=<model>
  make experiment-loop PROJECT=<project> RUBRIC=<rubric> ITERS=3 MUTATOR_MODEL=<model> JUDGE_MODEL=<model> AUTORESEARCH_LLM_TIMEOUT=120 AUTORESEARCH_LLM_RETRIES=1
  make experiment-loop PROJECT=<project> RUBRIC=<rubric> [ITERS=10] [PREFLIGHT_ONLY=1]  # auto-configures from rubric (holdout gate, underidentified_after)
  make experiment-loop PROJECT=<project> RUBRIC=<rubric> AGENT_MUTATOR=1 AGENT_JUDGE=1 AGENT_COMMITTEE=1 AGENT_INVERTER=1 [AGENT_RUNTIME=codex]
  make experiment-loop PROJECT=<project> RUBRIC=<rubric> MATCHED_RUN_ID=<id> MATCHED_RUN_ROLE=api|subscription
  make autoresearch-route TASK='<task>' PROJECT=<project> RUBRIC=<rubric> [BOUNDED=1 STABLE=1 RUBRIC_READY=1 ARTIFACT=1]
  make autoresearch-projection PROJECT=<project> [OUT=<path>]
  make autoresearch-trace PROJECT=<project> [RUBRIC=<rubric>] [INTAKE=<project_intake.json>] [MODEL=<model>] [FULL_HEALTH=1] [BRIEF=1] [JSON=1]
  make autoresearch-dispatch-validate [JSON=1]
  make autoresearch-dispatch-canary [CONTRACT=text|mutator|judge|committee|inverter] [DISPATCH_CALL_SITE=mutator] [AGENT_RUNTIME=codex] [LIVE=1] [JSON=1]
  make autoresearch-dispatch-parity [CONTRACTS=text,mutator,judge,committee,inverter] [AGENT_RUNTIME=codex] [LIVE=1] [JSON=1]
  make autoresearch-subscription-outcome-audit [PROJECT=<project>] [JSON=1] [STRICT=1] [MIN_ROWS=1] [PLAN_LIMIT=5]
  make autoresearch-matched-transport-pair PROJECT=<project> [RUBRIC=<rubric>] [INTAKE=<project_intake.json>] [ITERS=1] [MUTATOR_MODEL=kimi] [JUDGE_MODEL=grok] [INVERTER_MODEL=deepseek] [MODEL_FALLBACK=0] [MATCHED_RUN_ID=<id>] [AGENT_RUNTIME=codex] [AGENT_TIMEOUT=240] [RUN_MATCHED_PAIR=1]
  make autoresearch-consequence-audit [PROJECT=<project>] [WORKSPACE=<path>] [JSON=1]
  make autoresearch-rubric-mode-audit [RUBRIC=<path>] [JSON=1] [LIMIT=40] [FRESHNESS_DAYS=30] [STRICT=1]
  make autoresearch-hillclimb-audit [PROJECT=<project>] [JSON=1] [LIMIT=40] [STAGNATION_THRESHOLD=2] [RECOVERY_QUEUE=1] [RECOVERY_LIMIT=20] [RECOVERY_INTAKE_STATUS=ready|compiled_evidence_without_project_intake|missing_project_intake]
  make autoresearch-evidence-trace [PROJECT=<project> RUBRIC=<rubric> INTAKE=<project_intake.json>] [JSON=1]
  make autoresearch-kernel-health [PROJECT=<project>] [RUBRIC=<path>] [INTAKE=<project_intake.json>] [WORKSPACE=<path>] [JSON=1] [STRICT=1] [STAGNATION_THRESHOLD=2]
  make forensic-workbench-snapshot [WORKBENCH_PROJECT=<project>] [WORKBENCH_OUT=<html>]
  make forensic-workbench-data [WORKBENCH_PROJECT=<project>]
  make forensic-workbench-state [WORKBENCH_PROJECT=<project>]
  make forensic-workbench-build
  make forensic-workbench-api
  make forensic-workbench-dev
  make forensic-workbench-live
  ztare forensic-workbench apply-review --project <project> --project-check <project_check_slug> --from <project>_<project_check_slug>_review.json
  make operations-intelligence [OUT=<path>] [MD_OUT=<path>] [HTML_OUT=<path>] [FRESHNESS_DAYS=14] [MAX_PROJECTS=30] [NO_MARKDOWN=1] [JSON=1]
  make autoresearch-substrate-recommend [RECOMMENDER_MODE=cold|branch] [AGENT_RECOMMENDER=1 AGENT_RUNTIME=codex]
    # CLI front door: ztare autoresearch workbench-recommend
  make blitz-survival-report PROJECT=<project> [OUT=<json>] [MD_OUT=<md>]
  make inloop-fixture-validate [JSON=1]
  make gaming-catalog-audit
  make graph-capability-audit [JSON=1]
  make forecast-capability-audit [JSON=1]
  make move-card-router-audit [JSON=1] [SEMANTIC=1] [STRICT=1]  # SEMANTIC=1 requires live embedding access
  make gaming-vector-hardening-show
  make gaming-vector-hardening-check-plan
  make gaming-vector-hardening-sync-plan
  make gaming-vector-hardening-run-current
  make gaming-vector-hardening-run-vector VECTOR=<name> [SUBSTRATE=autoresearch]
  make gaming-vector-hardening-selftest
  make eigenquestion-propose PROJECT=<project> [MODEL=<model>]
  make eigenquestion-validate PROJECT=<project>
  make eigenquestion-status PROJECT=<project> [EIGENQUESTION_PREFLIGHT=strict]
  make primitive-catalog-health [JSON=1]
  make primitive-parent-utility [JSON=1]
  make primitive-amnesia-eval [RECORD_MISSES=1]
  make primitive-catalog-repopulate

`evidence-fetch` has two provider choices. `MODEL=` names the model used later
by auto-compile/workspace steps. `EVIDENCE_SEARCH_BACKEND=` chooses the
web-search provider for public-source recovery: `auto` follows the model family,
`openai` uses OpenAI `web_search_preview`, and `anthropic` uses Anthropic web
search. When the search backend and `MODEL=` differ, the fetch provenance records
the requested model. `evidence-prepare`, `evidence-compile`, and
`experiment-loop` use the general LLM runtime aliases from
[model_aliases.md](model_aliases.md).
  make primitive-catalog-build-atlas [EMBEDDER=<embedder>]
  make move-card-atlas-build
  make synth PROJECT=<project> MODEL=<model> QA_MODEL=<model> RENDERER=founder_memo
  make synth-contract PROJECT=<project> RENDERER=decision_brief
  make committee PROJECT=<project>
  make benchmark BENCH_JUDGE=<model> BENCH_JOBS=3
  make benchmark-stage1 BENCH_JUDGE=<model> BENCH_JOBS=3
  make benchmark-stage1-ood BENCH_JUDGE=<model> BENCH_JOBS=3
  make benchmark-stage2 BENCH_JUDGE=<model> BENCH_JOBS=3
  make benchmark-stage3 BENCH_JUDGE=<model> BENCH_JOBS=3
  make benchmark-stage4
  make benchmark-stage5
  make benchmark-stage6
  make benchmark-stage24-bridge
  make benchmark-bridge-scope
  make benchmark-bridge-discovery PROJECT=<project>
  make benchmark-runner-r1
  make benchmark-runner-r2
  make benchmark-runner-r3
  make benchmark-runner-r4
  make benchmark-supervisor
  make benchmark-supervisor-registry
  make benchmark-supervisor-seed-registry
  make benchmark-supervisor-genesis
  make benchmark-supervisor-manifest
  make benchmark-supervisor-backlog
  make benchmark-supervisor-proposal
  make benchmark-supervisor-staging
  make benchmark-supervisor-wrappers
  make benchmark-supervisor-refinement
  make benchmark-supervisor-usage
  make benchmark-supervisor-autoloop
  make benchmark-supervisor-program-autoloop
  make benchmark-supervisor-report
  make benchmark-supervisor-gate-resolution
  make benchmark-supervisor-findings-debate
  make benchmark-supervisor-findings-runner
  make benchmark-prose-verifier
  make benchmark-document-assembler
  make benchmark-supervisor-factory
  make assemble-document DOC_MANIFEST=<manifest_path> [DOC_JSON_OUT=<summary.json>]
  make supervisor-init SUP_PROGRAM=<program> SUP_TARGET=<target> SUP_RUN_ID=<run_id> [SUP_RUN_ROOT=supervisor/active_runs/<run_id>]
  make supervisor-show SUP_STATUS=supervisor/active_runs/<run_id>/status.json
  make supervisor-what-next SUP_STATUS=supervisor/active_runs/<run_id>/status.json
  make supervisor-backlog SUP_PROGRAM=<program> [SUP_EXECUTE=1]
  make supervisor-proposal SUP_SEED=<seed_id> SUP_PROGRAM=<proposed_program_id> [SUP_EXECUTE=1]
  make supervisor-emit SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_STAGING=supervisor/active_runs/<run_id>/staging
  make supervisor-commit SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_EVENTS=supervisor/active_runs/<run_id>/events.jsonl SUP_STAGING=supervisor/active_runs/<run_id>/staging SUP_REQUEST=supervisor/active_runs/<run_id>/staging/<actor_state>.json
  make supervisor-launch SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_STAGING=supervisor/active_runs/<run_id>/staging [SUP_EXECUTE=1]
  make supervisor-autoloop SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_EVENTS=supervisor/active_runs/<run_id>/events.jsonl SUP_STAGING=supervisor/active_runs/<run_id>/staging [SUP_EXECUTE=1] [SUP_AUTO_COMMIT=1]
  make supervisor-program-autoloop SUP_PROGRAM=<program> [SUP_RUN_ID=<run_id>] [SUP_EXECUTE=1] [SUP_AUTO_COMMIT=1]
  make supervisor-report SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_EVENTS=supervisor/active_runs/<run_id>/events.jsonl [SUP_REPORT_OUT=supervisor/active_runs/<run_id>/founder_memo.md]
  make supervisor-resolve-gate SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_EVENTS=supervisor/active_runs/<run_id>/events.jsonl SUP_DECISION=close|freeze|resume [SUP_NOTE='...']
  make bridge-meta-show PROJECT=<project>
  make bridge-meta-run-current PROJECT=<project>
  make bridge-meta-reset PROJECT=<project>
  make baseline
  make camouflage
  make primitives-extract
  make primitives-draft MODEL=<model>
  make primitive-approve PRIMITIVE_KEY=cooked_books PRIMITIVE_DECISION=approved
  make paper1-legacy
  make paper1-tsmc-legacy
  make paper1-epistemic-legacy
  make v4-meta-show
  make v4-meta-run-current
  make v4-meta-reset
  make v4-meta-advance
  make v4-forensic-report RUN_ID=<run_id>
  make v4-debate-init RUN_ID=<run_id>
  make v4-debate-show TASK_ID=<task_id>
  make v4-debate-merge TASK_ID=<task_id>
  make hello                                # first-run offline demo: overclaim in, demotion + missing evidence out
  make benchmark-evidence                   # model-free public benchmark-evidence check
  make reasoning-compiler-capability-audit  # reasoning-compiler capability map vs evidence refs
  make evaluator-hardening-frozen-check     # frozen evaluator-hardening proof-point check
  make scope-boundary-audit                 # public broad-claim boundary audit
  make public-terminology-audit             # front-door public terminology audit
  make first-run                            # aggregate offline public first-run path
  make benchmark-ordinary-review BENCH_ORDINARY_MODEL=<model> [BENCH_SPECIMEN=<id>] [BENCH_ORDINARY_IMPORT=<rows.json>]
  make benchmark-ordinary-review-prompts [BENCH_SPECIMEN=<id>] [BENCH_ORDINARY_EXPORT=<dir>]
  make benchmark-ordinary-review-validate-import BENCH_ORDINARY_IMPORT=<rows.json> [BENCH_SPECIMEN=<id>]
  make benchmark-ordinary-review-freeze-check BENCH_ORDINARY_RUN=<run_dir>
  make demo                                 # small model-free demo; no live model calls
  make demo-claim-discipline               # claim-discipline demo; no live model calls
  make smoke-public                         # first-run public smoke; no live model calls
  make public-adversarial-smoke             # adversarial public smoke and entry-path drift check
  make smoke-docker                         # Docker smoke for clean-machine checks
  make docs-check                           # public doc index, local-link, and papers/ hygiene check
  make compile-src                          # syntax-compile all src/ztare modules
  make flakes                               # exact undefined-name tripwire across src/ztare
  make gates                                # aggregate gate before publish/commit, including compile-src and flakes
