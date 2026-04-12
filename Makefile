PYTHON ?= python
PROJECT ?= your_project
RUBRIC ?= recursive_bayesian
MODEL ?= gemini
MUTATOR_MODEL ?= gemini
JUDGE_MODEL ?= gemini
QA_MODEL ?= claude
ITERS ?= 10
RENDERER ?= founder_memo
BENCH_JUDGE ?= gemini
BENCH_JOBS ?= 3
PRIMITIVE_KEY ?= cooked_books
PRIMITIVE_DECISION ?= approved
SUP_RUN_ID ?= supervisor_run
SUP_RUN_ROOT ?= supervisor/active_runs/$(SUP_RUN_ID)
SUP_STATUS ?= $(SUP_RUN_ROOT)/status.json
SUP_EVENTS ?= $(SUP_RUN_ROOT)/events.jsonl
SUP_STAGING ?= $(SUP_RUN_ROOT)/staging
SUP_PROGRAM ?= supervisor_loop
SUP_SEED ?=
SUP_TARGET ?= current_target
SUP_REQUEST ?=

.PHONY: help workspace-update evidence-compile loop synth committee benchmark benchmark-stage1 benchmark-stage1-ood benchmark-stage2 benchmark-stage3 benchmark-stage4 benchmark-stage5 benchmark-stage6 benchmark-stage24-bridge benchmark-bridge-scope benchmark-bridge-discovery benchmark-runner-r1 benchmark-runner-r2 benchmark-runner-r3 benchmark-runner-r4 benchmark-supervisor benchmark-supervisor-registry benchmark-supervisor-seed-registry benchmark-supervisor-genesis benchmark-supervisor-manifest benchmark-supervisor-backlog benchmark-supervisor-proposal benchmark-supervisor-staging benchmark-supervisor-wrappers benchmark-supervisor-refinement benchmark-supervisor-usage benchmark-supervisor-autoloop benchmark-supervisor-program-autoloop benchmark-supervisor-report benchmark-supervisor-gate-resolution benchmark-prose-verifier benchmark-document-assembler benchmark-supervisor-factory assemble-document supervisor-init supervisor-show supervisor-what-next supervisor-backlog supervisor-proposal supervisor-emit supervisor-commit supervisor-launch supervisor-autoloop supervisor-program-autoloop supervisor-report supervisor-resolve-gate bridge-meta-show bridge-meta-run-current bridge-meta-reset baseline camouflage \
	primitives-extract primitives-draft primitive-approve paper1-legacy paper1-tsmc-legacy paper1-epistemic-legacy \
	v4-meta-show v4-meta-run-current v4-meta-reset v4-meta-advance v4-forensic-report \
	v4-debate-init v4-debate-merge v4-debate-show

help:
	@echo "ZTARE commands"
	@echo ""
	@echo "Variables:"
	@echo "  PROJECT=<project> RUBRIC=<rubric> MODEL=<model> MUTATOR_MODEL=<model> JUDGE_MODEL=<model>"
	@echo ""
	@echo "Targets:"
	@echo "  make workspace-update PROJECT=<project> MODEL=gemini"
	@echo "  make evidence-compile PROJECT=<project> MODEL=gemini"
	@echo "  make loop PROJECT=<project> RUBRIC=<rubric> ITERS=10 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini"
	@echo "  make synth PROJECT=<project> MODEL=gemini QA_MODEL=claude RENDERER=founder_memo"
	@echo "  make committee PROJECT=<project>"
	@echo "  make benchmark BENCH_JUDGE=gemini BENCH_JOBS=3"
	@echo "  make benchmark-stage1 BENCH_JUDGE=gemini BENCH_JOBS=3"
	@echo "  make benchmark-stage1-ood BENCH_JUDGE=gemini BENCH_JOBS=3"
	@echo "  make benchmark-stage2 BENCH_JUDGE=gemini BENCH_JOBS=3"
	@echo "  make benchmark-stage3 BENCH_JUDGE=gemini BENCH_JOBS=3"
	@echo "  make benchmark-stage4"
	@echo "  make benchmark-stage5"
	@echo "  make benchmark-stage6"
	@echo "  make benchmark-stage24-bridge"
	@echo "  make benchmark-bridge-scope"
	@echo "  make benchmark-bridge-discovery PROJECT=epistemic_engine_v4_bridge_hardening"
	@echo "  make benchmark-runner-r1"
	@echo "  make benchmark-runner-r2"
	@echo "  make benchmark-runner-r3"
	@echo "  make benchmark-runner-r4"
	@echo "  make benchmark-supervisor"
	@echo "  make benchmark-supervisor-registry"
	@echo "  make benchmark-supervisor-seed-registry"
	@echo "  make benchmark-supervisor-genesis"
	@echo "  make benchmark-supervisor-manifest"
	@echo "  make benchmark-supervisor-backlog"
	@echo "  make benchmark-supervisor-proposal"
	@echo "  make benchmark-supervisor-staging"
	@echo "  make benchmark-supervisor-wrappers"
	@echo "  make benchmark-supervisor-refinement"
	@echo "  make benchmark-supervisor-usage"
	@echo "  make benchmark-supervisor-autoloop"
	@echo "  make benchmark-supervisor-program-autoloop"
	@echo "  make benchmark-supervisor-report"
	@echo "  make benchmark-supervisor-gate-resolution"
	@echo "  make benchmark-supervisor-findings-debate"
	@echo "  make benchmark-supervisor-findings-runner"
	@echo "  make benchmark-prose-verifier"
	@echo "  make benchmark-document-assembler"
	@echo "  make benchmark-supervisor-factory"
	@echo "  make assemble-document DOC_MANIFEST=<manifest_path> [DOC_JSON_OUT=<summary.json>]"
	@echo "  make supervisor-init SUP_PROGRAM=<program> SUP_TARGET=<target> SUP_RUN_ID=<run_id> [SUP_RUN_ROOT=supervisor/active_runs/<run_id>]"
	@echo "  make supervisor-show SUP_STATUS=supervisor/active_runs/<run_id>/status.json"
	@echo "  make supervisor-what-next SUP_STATUS=supervisor/active_runs/<run_id>/status.json"
	@echo "  make supervisor-backlog SUP_PROGRAM=<program> [SUP_EXECUTE=1]"
	@echo "  make supervisor-proposal SUP_SEED=<seed_id> SUP_PROGRAM=<proposed_program_id> [SUP_EXECUTE=1]"
	@echo "  make supervisor-emit SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_STAGING=supervisor/active_runs/<run_id>/staging"
	@echo "  make supervisor-commit SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_EVENTS=supervisor/active_runs/<run_id>/events.jsonl SUP_STAGING=supervisor/active_runs/<run_id>/staging SUP_REQUEST=supervisor/active_runs/<run_id>/staging/<actor_state>.json"
	@echo "  make supervisor-launch SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_STAGING=supervisor/active_runs/<run_id>/staging [SUP_EXECUTE=1]"
	@echo "  make supervisor-autoloop SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_EVENTS=supervisor/active_runs/<run_id>/events.jsonl SUP_STAGING=supervisor/active_runs/<run_id>/staging [SUP_EXECUTE=1] [SUP_AUTO_COMMIT=1]"
	@echo "  make supervisor-program-autoloop SUP_PROGRAM=<program> [SUP_RUN_ID=<run_id>] [SUP_EXECUTE=1] [SUP_AUTO_COMMIT=1]"
	@echo "  make supervisor-report SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_EVENTS=supervisor/active_runs/<run_id>/events.jsonl [SUP_REPORT_OUT=supervisor/active_runs/<run_id>/founder_memo.md]"
	@echo "  make supervisor-resolve-gate SUP_STATUS=supervisor/active_runs/<run_id>/status.json SUP_EVENTS=supervisor/active_runs/<run_id>/events.jsonl SUP_DECISION=close|freeze|resume [SUP_NOTE='...']"
	@echo "  make bridge-meta-show PROJECT=epistemic_engine_v4_bridge_hardening"
	@echo "  make bridge-meta-run-current PROJECT=epistemic_engine_v4_bridge_hardening"
	@echo "  make bridge-meta-reset PROJECT=epistemic_engine_v4_bridge_hardening"
	@echo "  make baseline"
	@echo "  make camouflage"
	@echo "  make primitives-extract"
	@echo "  make primitives-draft MODEL=gemini"
	@echo "  make primitive-approve PRIMITIVE_KEY=cooked_books PRIMITIVE_DECISION=approved"
	@echo "  make paper1-legacy"
	@echo "  make paper1-tsmc-legacy"
	@echo "  make paper1-epistemic-legacy"
	@echo "  make v4-meta-show"
	@echo "  make v4-meta-run-current"
	@echo "  make v4-meta-reset"
	@echo "  make v4-meta-advance"
	@echo "  make v4-forensic-report RUN_ID=<run_id>"
	@echo "  make v4-debate-init RUN_ID=<run_id>"
	@echo "  make v4-debate-show TASK_ID=<task_id>"
	@echo "  make v4-debate-merge TASK_ID=<task_id>"

workspace-update:
	$(PYTHON) -m src.ztare.workspace.update_workspace --project $(PROJECT) --model $(MODEL)

evidence-compile:
	$(PYTHON) -m src.ztare.workspace.compile_evidence --project $(PROJECT) --mode workspace --model $(MODEL)

loop:
	$(PYTHON) -m src.ztare.validator.autoresearch_loop \
		--project $(PROJECT) \
		--rubric $(RUBRIC) \
		--iters $(ITERS) \
		--mutator_model $(MUTATOR_MODEL) \
		--judge_model $(JUDGE_MODEL) \
		$(EXTRA_ARGS)

synth:
	$(PYTHON) -m src.ztare.synthesis.synthesize \
		--project $(PROJECT) \
		--model $(MODEL) \
		--qa-model $(QA_MODEL) \
		--renderer-type $(RENDERER)

committee:
	$(PYTHON) -m src.ztare.validator.generate_committee --project $(PROJECT)

benchmark:
	$(PYTHON) benchmarks/constraint_memory/run_benchmark.py --judge-model $(BENCH_JUDGE) --jobs $(BENCH_JOBS)

benchmark-stage1:
	$(PYTHON) benchmarks/constraint_memory/run_benchmark.py --judge-model $(BENCH_JUDGE) --jobs $(BENCH_JOBS) --suite stage1_regression

benchmark-stage1-ood:
	$(PYTHON) benchmarks/constraint_memory/run_benchmark.py --judge-model $(BENCH_JUDGE) --jobs $(BENCH_JOBS) --suite stage1_ood

benchmark-stage2:
	$(PYTHON) benchmarks/constraint_memory/run_benchmark.py --judge-model $(BENCH_JUDGE) --jobs $(BENCH_JOBS) --suite stage2_regression

benchmark-stage3:
	$(PYTHON) benchmarks/constraint_memory/run_benchmark.py --judge-model $(BENCH_JUDGE) --jobs $(BENCH_JOBS) --suite stage3_regression

benchmark-stage4:
	$(PYTHON) -m src.ztare.validator.stage4_fixture_regression --json-out projects/epistemic_engine_v4/stage4_fixture_regression_summary.json

benchmark-stage5:
	$(PYTHON) -m src.ztare.validator.stage5_fixture_regression --json-out projects/epistemic_engine_v4/stage5_fixture_regression_summary.json

benchmark-stage6:
	$(PYTHON) -m src.ztare.validator.stage6_fixture_regression --json-out projects/epistemic_engine_v4/stage6_fixture_regression_summary.json

benchmark-stage24-bridge:
	$(PYTHON) -m src.ztare.validator.stage24_bridge_fixture_regression

benchmark-bridge-scope:
	$(PYTHON) -m src.ztare.validator.bridge_scope_fixture_regression

benchmark-bridge-discovery:
	$(PYTHON) -m src.ztare.validator.bridge_discovery_evaluator --project $(PROJECT)

benchmark-runner-r1:
	$(PYTHON) -m src.ztare.validator.runner_r1_fixture_regression

benchmark-runner-r2:
	$(PYTHON) -m src.ztare.validator.runner_r2_fixture_regression

benchmark-runner-r3:
	$(PYTHON) -m src.ztare.validator.runner_r3_fixture_regression

benchmark-runner-r4:
	$(PYTHON) -m src.ztare.validator.runner_r4_fixture_regression

benchmark-supervisor:
	$(PYTHON) -m src.ztare.validator.supervisor_fixture_regression

benchmark-supervisor-registry:
	$(PYTHON) -m src.ztare.validator.supervisor_registry_check

benchmark-supervisor-seed-registry:
	$(PYTHON) -m src.ztare.validator.supervisor_seed_registry_check

benchmark-supervisor-genesis:
	$(PYTHON) -m src.ztare.validator.supervisor_genesis_fixture_regression

benchmark-supervisor-manifest:
	$(PYTHON) -m src.ztare.validator.supervisor_manifest_fixture_regression

benchmark-supervisor-backlog:
	$(PYTHON) -m src.ztare.validator.supervisor_backlog_fixture_regression

benchmark-supervisor-proposal:
	$(PYTHON) -m src.ztare.validator.supervisor_proposal_fixture_regression

benchmark-supervisor-staging:
	$(PYTHON) -m src.ztare.validator.supervisor_staging_fixture_regression

benchmark-supervisor-wrappers:
	$(PYTHON) -m src.ztare.validator.supervisor_wrapper_fixture_regression

benchmark-supervisor-refinement:
	$(PYTHON) -m src.ztare.validator.supervisor_refinement_fixture_regression

benchmark-supervisor-usage:
	$(PYTHON) -m src.ztare.validator.supervisor_usage_fixture_regression

benchmark-supervisor-autoloop:
	$(PYTHON) -m src.ztare.validator.supervisor_attended_autoloop_fixture_regression

benchmark-supervisor-program-autoloop:
	$(PYTHON) -m src.ztare.validator.supervisor_program_autoloop_fixture_regression

benchmark-supervisor-report:
	$(PYTHON) -m src.ztare.validator.supervisor_report_fixture_regression

benchmark-supervisor-gate-resolution:
	$(PYTHON) -m src.ztare.validator.supervisor_gate_resolution_fixture_regression

benchmark-supervisor-findings-debate:
	$(PYTHON) -m src.ztare.validator.supervisor_findings_debate_fixture_regression

benchmark-supervisor-findings-runner:
	$(PYTHON) -m src.ztare.validator.supervisor_findings_runner_fixture_regression

benchmark-prose-verifier:
	$(PYTHON) -m src.ztare.validator.prose_verifier_fixture_regression

benchmark-document-assembler:
	$(PYTHON) -m src.ztare.validator.document_assembler_fixture_regression

benchmark-supervisor-factory:
	$(MAKE) benchmark-supervisor-registry
	$(MAKE) benchmark-supervisor-manifest
	$(MAKE) benchmark-supervisor-staging
	$(MAKE) benchmark-supervisor-wrappers
	$(MAKE) benchmark-supervisor-autoloop
	$(MAKE) benchmark-supervisor-program-autoloop
	$(MAKE) benchmark-prose-verifier
	$(MAKE) benchmark-document-assembler
	$(MAKE) benchmark-supervisor-findings-debate
	$(MAKE) benchmark-supervisor-findings-runner

assemble-document:
	$(PYTHON) -m src.ztare.validator.document_assembler \
		--manifest-path $(DOC_MANIFEST) \
		$(if $(DOC_JSON_OUT),--json-out $(DOC_JSON_OUT),)

supervisor-init:
	$(PYTHON) -m src.ztare.validator.supervisor_loop init \
		--status-path $(SUP_STATUS) \
		--run-id $(SUP_RUN_ID) \
		--program $(SUP_PROGRAM) \
		--target $(SUP_TARGET) \
		$(if $(SUP_MAX_REFINEMENT_COST),--max-refinement-cost-usd $(SUP_MAX_REFINEMENT_COST),)

supervisor-show:
	$(PYTHON) -m src.ztare.validator.supervisor_loop show \
		--status-path $(SUP_STATUS)

supervisor-what-next:
	$(PYTHON) -m src.ztare.validator.supervisor_what_next \
		--status-path $(SUP_STATUS)

supervisor-backlog:
	$(PYTHON) -m src.ztare.validator.supervisor_backlog \
		--program $(SUP_PROGRAM) \
		$(if $(SUP_PLAN_DIR),--output-dir $(SUP_PLAN_DIR),) \
		$(if $(SUP_EXECUTE),--execute,)

supervisor-proposal:
	$(PYTHON) -m src.ztare.validator.supervisor_proposal \
		--seed-id $(SUP_SEED) \
		--program-id $(SUP_PROGRAM) \
		$(if $(SUP_PLAN_DIR),--output-dir $(SUP_PLAN_DIR),) \
		$(if $(SUP_EXECUTE),--execute,)

supervisor-emit:
	$(PYTHON) -m src.ztare.validator.supervisor_loop emit-staging \
		--status-path $(SUP_STATUS) \
		--staging-dir $(SUP_STAGING)

supervisor-commit:
	$(PYTHON) -m src.ztare.validator.supervisor_loop commit-staging \
		--status-path $(SUP_STATUS) \
		--events-path $(SUP_EVENTS) \
		--staging-dir $(SUP_STAGING) \
		--staging-path $(SUP_REQUEST)

supervisor-launch:
	$(PYTHON) -m src.ztare.validator.supervisor_loop launch-staging \
		--status-path $(SUP_STATUS) \
		--staging-dir $(SUP_STAGING) \
		$(if $(SUP_EXECUTE),--execute,)

supervisor-autoloop:
	$(PYTHON) -m src.ztare.validator.supervisor_attended_autoloop \
		--status-path $(SUP_STATUS) \
		--events-path $(SUP_EVENTS) \
		--staging-dir $(SUP_STAGING) \
		$(if $(SUP_EXECUTE),--execute,) \
		$(if $(SUP_AUTO_COMMIT),--auto-commit,) \
		$(if $(SUP_MAX_ADVANCES),--max-advances $(SUP_MAX_ADVANCES),) \
		$(if $(SUP_MAX_SECONDS),--max-seconds $(SUP_MAX_SECONDS),) \
		$(if $(SUP_MAX_PROGRAM_COST),--max-program-cost-usd $(SUP_MAX_PROGRAM_COST),) \
		$(if $(SUP_MAX_OUTPUT_TOKENS),--max-output-tokens $(SUP_MAX_OUTPUT_TOKENS),) \
		$(if $(SUP_MAX_FRESH_INPUT_TOKENS),--max-fresh-input-tokens $(SUP_MAX_FRESH_INPUT_TOKENS),)

supervisor-program-autoloop:
	$(PYTHON) -m src.ztare.validator.supervisor_program_autoloop \
		--program $(SUP_PROGRAM) \
		$(if $(SUP_RUN_ID),--run-id $(SUP_RUN_ID),) \
		$(if $(SUP_EXECUTE),--execute,) \
		$(if $(SUP_AUTO_COMMIT),--auto-commit,) \
		$(if $(SUP_MAX_ADVANCES),--max-advances $(SUP_MAX_ADVANCES),) \
		$(if $(SUP_MAX_SECONDS),--max-seconds $(SUP_MAX_SECONDS),) \
		$(if $(SUP_MAX_PROGRAM_COST),--max-program-cost-usd $(SUP_MAX_PROGRAM_COST),) \
		$(if $(SUP_MAX_OUTPUT_TOKENS),--max-output-tokens $(SUP_MAX_OUTPUT_TOKENS),) \
		$(if $(SUP_MAX_FRESH_INPUT_TOKENS),--max-fresh-input-tokens $(SUP_MAX_FRESH_INPUT_TOKENS),) \
		$(if $(SUP_MAX_PACKETS),--max-packets $(SUP_MAX_PACKETS),) \
		$(if $(SUP_MAX_REFINEMENT_COST),--max-refinement-cost-usd $(SUP_MAX_REFINEMENT_COST),)

supervisor-report:
	$(PYTHON) -m src.ztare.validator.supervisor_report \
		--status-path $(SUP_STATUS) \
		$(if $(SUP_EVENTS),--events-path $(SUP_EVENTS),) \
		$(if $(SUP_REPORT_OUT),--output-path $(SUP_REPORT_OUT),) \
		$(if $(SUP_JSON_OUT),--json-out $(SUP_JSON_OUT),)

supervisor-resolve-gate:
	$(PYTHON) -m src.ztare.validator.supervisor_gate_resolution \
		--status-path $(SUP_STATUS) \
		--events-path $(SUP_EVENTS) \
		--decision $(SUP_DECISION) \
		$(if $(SUP_NOTE),--note "$(SUP_NOTE)",)

bridge-meta-show:
	$(PYTHON) -m src.ztare.validator.bridge_meta_runner --project $(PROJECT) show

bridge-meta-run-current:
	$(PYTHON) -m src.ztare.validator.bridge_meta_runner --project $(PROJECT) run-current

bridge-meta-reset:
	$(PYTHON) -m src.ztare.validator.bridge_meta_runner --project $(PROJECT) reset

baseline:
	$(PYTHON) -m src.ztare.experiments.baseline_experiment

camouflage:
	$(PYTHON) -m src.ztare.experiments.cognitive_camouflage_experiment

primitives-extract:
	$(PYTHON) -m src.ztare.workspace.extract_incidents

primitives-draft:
	$(PYTHON) -m src.ztare.primitives.draft_primitives --model $(MODEL)

primitive-approve:
	$(PYTHON) -m src.ztare.primitives.approve_primitive --primitive-key $(PRIMITIVE_KEY) --decision $(PRIMITIVE_DECISION)

paper1-legacy:
	@echo "Legacy Paper 1 runs:"
	@echo "  make paper1-tsmc-legacy"
	@echo "  make paper1-epistemic-legacy"
	@echo "  make v4-meta-advance"

paper1-tsmc-legacy:
	$(PYTHON) -m src.ztare.validator.autoresearch_loop \
		--project tsmc_fragility_claude_gemini \
		--rubric tsmc_fragility \
		--iters 10 \
		--mutator_model claude \
		--judge_model gemini

paper1-epistemic-legacy:
	$(PYTHON) -m src.ztare.validator.autoresearch_loop \
		--project epistemic_engine_v3_claude_gemini \
		--rubric epistemic_engine_v3_evolved \
		--iters 10 \
		--mutator_model claude \
		--judge_model gemini


v4-meta-show:
	$(PYTHON) -m src.ztare.validator.v4_meta_runner --project epistemic_engine_v4 show

v4-meta-run-current:
	$(PYTHON) -m src.ztare.validator.v4_meta_runner --project epistemic_engine_v4 run-current

v4-meta-reset:
	$(PYTHON) -m src.ztare.validator.v4_meta_runner --project epistemic_engine_v4 reset


v4-meta-advance:
	$(PYTHON) -m src.ztare.validator.v4_meta_runner --project epistemic_engine_v4 advance

v4-forensic-report:
	$(PYTHON) -m src.ztare.validator.forensic_reporter --project epistemic_engine_v4 $(if $(RUN_ID),--run-id $(RUN_ID),)

v4-debate-init:
	$(PYTHON) -m src.ztare.orchestration.debate_orchestrator --project epistemic_engine_v4 init-stage1-fail $(if $(RUN_ID),--run-id $(RUN_ID),)

v4-debate-show:
	$(PYTHON) -m src.ztare.orchestration.debate_orchestrator --project epistemic_engine_v4 show $(TASK_ID)

v4-debate-merge:
	$(PYTHON) -m src.ztare.orchestration.debate_orchestrator --project epistemic_engine_v4 merge $(TASK_ID)
