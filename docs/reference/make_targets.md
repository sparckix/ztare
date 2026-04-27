ZTARE commands

Variables:
  PROJECT=<project> RUBRIC=<rubric> MODEL=<model> MUTATOR_MODEL=<model> JUDGE_MODEL=<model>
  MODE=factory|honeypot  (default: factory; honeypot sets ITERS=50 and skips pre-run pipeline)

Run modes:
  factory  — tight rubric, GP-054 pre-run, 5-10 iters, synthesis output (default)
  honeypot — loose rubric, no pre-run, 50 iters, debate log is the output

Targets:
  make setup-project PROJECT=<project> RUBRIC=<rubric> [MODEL=gemini]   # factory pre-run: fetch→compile→review→pause
  make honeypot-loop PROJECT=<project> RUBRIC=<rubric> [ITERS=50]       # honeypot run: no pre-run, MODE=honeypot
  make evidence-prepare PROJECT=<project> MODEL=gemini                    # workspace-update + evidence-compile in one step
  make workspace-update PROJECT=<project> MODEL=gemini
  make evidence-compile PROJECT=<project> MODEL=gemini
  make evidence-fetch PROJECT=<project> [SEVERITY=degrading] [MAX_FETCHES=3] [MODEL=gemini]
  make rubric-review PROJECT=<project> RUBRIC=<rubric> [MODEL=gemini]
  make loop PROJECT=<project> RUBRIC=<rubric> [ITERS=10] [MODE=factory|honeypot] MUTATOR_MODEL=gemini JUDGE_MODEL=gemini
  make experiment-loop PROJECT=<project> RUBRIC=<rubric> [ITERS=10]   # auto-configures from rubric (holdout gate, underidentified_after)
  make synth PROJECT=<project> MODEL=gemini QA_MODEL=claude RENDERER=founder_memo
  make committee PROJECT=<project>
  make benchmark BENCH_JUDGE=gemini BENCH_JOBS=3
  make benchmark-stage1 BENCH_JUDGE=gemini BENCH_JOBS=3
  make benchmark-stage1-ood BENCH_JUDGE=gemini BENCH_JOBS=3
  make benchmark-stage2 BENCH_JUDGE=gemini BENCH_JOBS=3
  make benchmark-stage3 BENCH_JUDGE=gemini BENCH_JOBS=3
  make benchmark-stage4
  make benchmark-stage5
  make benchmark-stage6
  make benchmark-stage24-bridge
  make benchmark-bridge-scope
  make benchmark-bridge-discovery PROJECT=epistemic_engine_v4_bridge_hardening
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
  make bridge-meta-show PROJECT=epistemic_engine_v4_bridge_hardening
  make bridge-meta-run-current PROJECT=epistemic_engine_v4_bridge_hardening
  make bridge-meta-reset PROJECT=epistemic_engine_v4_bridge_hardening
  make baseline
  make camouflage
  make primitives-extract
  make primitives-draft MODEL=gemini
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
