PYTHON ?= ./venv/bin/python
PROJECT ?= your_project
MODEL ?= gemini
MUTATOR_MODEL ?= gemini
JUDGE_MODEL ?= gemini
QA_MODEL ?= claude
MODE ?= factory
ITERS ?= 10
RUBRIC ?= $(PROJECT)
DYNAMIC ?= 0
EVOLVE ?= 0
CROSS_FAMILY ?= 0
COMMITTEE_MODEL ?=
# Internal computed flag: when DYNAMIC=1, append --dynamic to the loop invocation.
# Usage: make loop PROJECT=<p> RUBRIC=<r> DYNAMIC=1  (uses rubrics/dynamic_<p>.json via autoresearch_loop's --dynamic flag)
# Optional COMMITTEE_MODEL=<label> overrides the committee generator model.
# Default: committee uses --judge_model when DYNAMIC=1 and COMMITTEE_MODEL is unset.
# EVOLVE=1 appends --auto-evolve: monotonic-ratchet evolution of the rubric
# fires ONLY when a single iter reaches score >= 85, rewriting rubrics/<RUBRIC>.json
# in place. Not useful below 85; designed to prevent reward-hacking after a win.
DYNAMIC_FLAG := $(if $(filter 1,$(DYNAMIC)),--dynamic,)
EVOLVE_FLAG := $(if $(filter 1,$(EVOLVE)),--auto-evolve,)
CROSS_FAMILY_FLAG := $(if $(filter 1,$(CROSS_FAMILY)),--require_cross_family,)
COMMITTEE_MODEL_FLAG := $(if $(COMMITTEE_MODEL),--committee_model $(COMMITTEE_MODEL),)
RENDERER ?=
PDF ?= 0
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
SEVERITY ?= degrading
MAX_FETCHES ?= 3

COMMAND_LINE_JUDGE_VARS := $(foreach v,$(filter JUDGE_%,$(.VARIABLES)),$(if $(filter command line,$(origin $(v))),$(v)))
UNKNOWN_JUDGE_VARS := $(filter-out JUDGE_MODEL,$(COMMAND_LINE_JUDGE_VARS))
ifneq ($(strip $(UNKNOWN_JUDGE_VARS)),)
$(error Unknown judge Make variable(s): $(UNKNOWN_JUDGE_VARS). Use JUDGE_MODEL=<model>)
endif

COMMAND_LINE_MUTATOR_VARS := $(foreach v,$(filter MUTATOR_%,$(.VARIABLES)),$(if $(filter command line,$(origin $(v))),$(v)))
UNKNOWN_MUTATOR_VARS := $(filter-out MUTATOR_MODEL,$(COMMAND_LINE_MUTATOR_VARS))
ifneq ($(strip $(UNKNOWN_MUTATOR_VARS)),)
$(error Unknown mutator Make variable(s): $(UNKNOWN_MUTATOR_VARS). Use MUTATOR_MODEL=<model>)
endif

.PHONY: help workspace-update evidence-compile evidence-prepare evidence-fetch rubric-review setup-project honeypot-loop loop audit-prompt _preflight_leak_audit synth committee benchmark benchmark-stage1 benchmark-stage1-ood benchmark-stage2 benchmark-stage3 benchmark-stage4 benchmark-stage5 benchmark-stage6 benchmark-stage24-bridge benchmark-bridge-scope benchmark-bridge-discovery benchmark-runner-r1 benchmark-runner-r2 benchmark-runner-r3 benchmark-runner-r4 benchmark-supervisor benchmark-supervisor-registry benchmark-supervisor-seed-registry benchmark-supervisor-genesis benchmark-supervisor-manifest benchmark-supervisor-backlog benchmark-supervisor-proposal benchmark-supervisor-staging benchmark-supervisor-wrappers benchmark-supervisor-refinement benchmark-supervisor-usage benchmark-supervisor-autoloop benchmark-supervisor-program-autoloop benchmark-supervisor-report benchmark-supervisor-gate-resolution benchmark-supervisor-findings-debate benchmark-supervisor-findings-runner benchmark-prose-verifier benchmark-document-assembler benchmark-supervisor-factory assemble-document supervisor-init supervisor-show supervisor-what-next supervisor-backlog supervisor-proposal supervisor-emit supervisor-commit supervisor-launch supervisor-autoloop supervisor-program-autoloop supervisor-report supervisor-resolve-gate bridge-meta-show bridge-meta-run-current bridge-meta-reset baseline camouflage gp-index arch-validate arch-validate-ex-ante audit-gate-coverage audit-gate-coverage-strict audit-gate-coverage-self-test \
	primitives-extract primitives-draft primitive-approve paper1-legacy paper1-tsmc-legacy paper1-epistemic-legacy \
	v4-meta-show v4-meta-run-current v4-meta-reset v4-meta-advance v4-forensic-report \
	v4-debate-init v4-debate-merge v4-debate-show experiment-loop seal wipe-sandbox

help:
	@echo "ZTARE commands"
	@echo ""
	@echo "Variables:"
	@echo "  PROJECT=<project> RUBRIC=<rubric> MODEL=<model> MUTATOR_MODEL=<model> JUDGE_MODEL=<model>"
	@echo "  MODE=factory|honeypot  (default: factory; honeypot sets ITERS=50 and skips pre-run pipeline)"
	@echo ""
	@echo "Run modes:"
	@echo "  factory  — tight rubric, GP-054 pre-run, 5-10 iters, synthesis output (default)"
	@echo "  honeypot — loose rubric, no pre-run, 50 iters, debate log is the output"
	@echo ""
	@echo "Targets:"
	@echo "  make setup-project PROJECT=<project> RUBRIC=<rubric> [MODEL=gemini]   # factory pre-run: fetch→compile→review→pause"
	@echo "  make honeypot-loop PROJECT=<project> RUBRIC=<rubric> [ITERS=50]       # honeypot run: no pre-run, MODE=honeypot"
	@echo "  make evidence-prepare PROJECT=<project> MODEL=gemini                    # workspace-update + evidence-compile in one step"
	@echo "  make workspace-update PROJECT=<project> MODEL=gemini"
	@echo "  make evidence-compile PROJECT=<project> MODEL=gemini"
	@echo "  make evidence-fetch PROJECT=<project> [SEVERITY=degrading] [MAX_FETCHES=3] [MODEL=gemini]"
	@echo "  make rubric-review PROJECT=<project> RUBRIC=<rubric> [MODEL=gemini]"
	@echo "  make loop PROJECT=<project> RUBRIC=<rubric> [ITERS=10] [MODE=factory|honeypot] MUTATOR_MODEL=gemini JUDGE_MODEL=gemini"
	@echo "  make experiment-loop PROJECT=<project> RUBRIC=<rubric> [ITERS=10]   # auto-configures from rubric (holdout gate, underidentified_after)"
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
	@echo "  make benchmark-evidence   # model-free check of public benchmark evidence"
	@echo "  make demo   # small model-free evaluation-failure demos"
	@echo "  make demo-current   # model-free current-engine claim-discipline demo"
	@echo "  make smoke-public   # runtime + forecast pool + action intelligence smoke checks"
	@echo "  make public-adversarial-smoke   # isolation, cleanup, docs, and boundary checks"
	@echo "  make smoke-docker   # build the public image and run the public smoke checks inside it"
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

setup-project:
	@if [ "$(MODE)" = "honeypot" ]; then \
		echo ""; \
		echo "WARNING: MODE=honeypot — pre-run pipeline suppressed."; \
		echo "Honeypot runs skip evidence-fetch, evidence-compile, and rubric-review."; \
		echo "Run directly: make honeypot-loop PROJECT=$(PROJECT) RUBRIC=$(RUBRIC)"; \
		echo ""; \
	else \
		mkdir -p projects/$(PROJECT)/workspace projects/$(PROJECT)/raw; \
		if [ ! -f "projects/$(PROJECT)/workspace/latest_evidence_gaps.json" ]; then \
			echo "Fresh project — running rubric-review to generate initial evidence gaps..."; \
			$(MAKE) rubric-review PROJECT=$(PROJECT) RUBRIC=$(RUBRIC) MODEL=$(MODEL) || true; \
		fi; \
		if $(MAKE) evidence-fetch PROJECT=$(PROJECT) MODEL=$(MODEL) SEVERITY=$(SEVERITY) MAX_FETCHES=$(MAX_FETCHES) \
			&& $(MAKE) evidence-compile PROJECT=$(PROJECT) MODEL=$(MODEL) \
			&& $(MAKE) rubric-review PROJECT=$(PROJECT) RUBRIC=$(RUBRIC) MODEL=$(MODEL); then \
			echo ""; \
			echo "Review complete. Check projects/$(PROJECT)/workspace/rubric_patch_*.json."; \
			echo "Approve patch, then run: make loop PROJECT=$(PROJECT) RUBRIC=$(RUBRIC)"; \
			echo ""; \
		else \
			echo ""; \
			echo "setup-project pipeline failed. Check errors above."; \
			echo ""; \
			exit 1; \
		fi; \
	fi

honeypot-loop:
	$(MAKE) loop PROJECT=$(PROJECT) RUBRIC=$(RUBRIC) ITERS=$(ITERS) \
		MUTATOR_MODEL=$(MUTATOR_MODEL) JUDGE_MODEL=$(JUDGE_MODEL) MODE=honeypot \
		CROSS_FAMILY=$(CROSS_FAMILY)

workspace-update:
	$(PYTHON) -m src.ztare.workspace.update_workspace --project $(PROJECT) --model $(MODEL)

evidence-compile:
	$(PYTHON) -m src.ztare.workspace.compile_evidence --project $(PROJECT) --mode workspace --model $(MODEL)

evidence-prepare:
	$(MAKE) workspace-update PROJECT=$(PROJECT) MODEL=$(MODEL)
	$(MAKE) evidence-compile PROJECT=$(PROJECT) MODEL=$(MODEL)

evidence-fetch:
	$(PYTHON) -m src.ztare.workspace.fetch_evidence --project $(PROJECT) --severity $(SEVERITY) --max-fetches $(MAX_FETCHES) --model $(MODEL)

# GP-226 charter-critic V1 advisory commit. Apply pending patches from
# a previous run's workspace/charter_patch_candidate_<RUN>.md to the
# project's evidence/charter/rubric. DRY=1 previews without writing.
# Usage: make charter-commit PROJECT=<slug> RUN=<run_id>
#        make charter-commit PROJECT=<slug> RUN=<run_id> PATCHES=1,3
#        make charter-commit PROJECT=<slug> RUN=<run_id> DRY=1
charter-commit:
	@if [ -z "$(PROJECT)" ] || [ -z "$(RUN)" ]; then \
		echo "ERROR: PROJECT and RUN are required."; \
		echo "Usage: make charter-commit PROJECT=<slug> RUN=<run_id> [PATCHES=1,3] [DRY=1]"; \
		exit 1; \
	fi
	$(PYTHON) scripts/charter_commit.py $(PROJECT) --run $(RUN) \
		$(if $(PATCHES),--patches $(PATCHES),) \
		$(if $(filter 1,$(DRY)),--dry-run,)

rubric-review:
	$(PYTHON) -m src.ztare.rubrics.review_rubric --project $(PROJECT) --rubric $(RUBRIC) --model $(MODEL)

# GP-228 — Substrate portfolio: list / scaffold / run members from
# org/runtime/substrate_portfolio.yaml. Sequential dispatch (cross-
# substrate exclusion ledger §25 in rubric_specification.md depends on
# ordering). See src/ztare/research_director/substrate_portfolio.py.
portfolio-list:
	$(PYTHON) -m src.ztare.research_director.substrate_portfolio list

portfolio-scaffold:
	$(PYTHON) -m src.ztare.research_director.substrate_portfolio scaffold

# Usage: make portfolio-run [ITERS=5] [ONLY=<slug-substring>] [MUTATOR=gpt4.1] [JUDGE=gpt4.1]
portfolio-run:
	$(PYTHON) -m src.ztare.research_director.substrate_portfolio run \
		--iters $(if $(ITERS),$(ITERS),5) \
		--mutator $(if $(MUTATOR),$(MUTATOR),gpt4.1) \
		--judge $(if $(JUDGE),$(JUDGE),gpt4.1) \
		$(if $(ONLY),--only $(ONLY),)

# GP-228 — Frontier-eigenquestion generator: draft an advisory
# eigenquestion orthogonal to a substrate's explored primitive
# classes. Output is markdown the operator manually merges into
# project_charter.md.
# Usage: make eigenquestion-propose PROJECT=<slug> [MODEL=claude-sonnet-4-6]
eigenquestion-propose:
	@if [ -z "$(PROJECT)" ] || [ "$(PROJECT)" = "your_project" ]; then \
		echo "ERROR: PROJECT is required. Usage: make eigenquestion-propose PROJECT=<slug> [MODEL=<model>]"; \
		exit 1; \
	fi
	$(PYTHON) -m src.ztare.research_director.eigenquestion_generator \
		--project $(PROJECT) \
		$(if $(MODEL),--model $(MODEL),)

# Seamless VPS bootstrap. Run from your laptop, pointing at a fresh Ubuntu VPS.
# Idempotent — safe to re-run. Mechanizes everything except interactive auth steps
# (which it prints as a checklist at the end).
# Usage: make setup-vps VPS=root@<vps-ip>
#        make setup-vps VPS=root@<vps-ip> TENANT_REPO=<your-org>/[tenant]
setup-vps:
	@if [ -z "$(VPS)" ]; then \
		echo "ERROR: VPS is required. Usage: make setup-vps VPS=root@<vps-ip> [TENANT_REPO=...]"; \
		exit 1; \
	fi
	$(if $(TENANT_REPO),TENANT_REPO=$(TENANT_REPO),) ./scripts/setup_vps.sh $(VPS)

# GP-134 prompt-layer leak audit: cold cross-family auditor scans the
# fully-built mutator prompt + evidence for target leakage before any
# iteration runs. Soft gate (prints and continues) unless
# STRICT_LEAK_AUDIT=1 is set, in which case failure aborts the run.
gates-engagement:
	@$(PYTHON) scripts/audit_gate_engagement.py $(if $(JSON),--json,) $(if $(STRICT),--strict,)

gates-strict:
	@$(PYTHON) scripts/audit_gate_engagement.py --strict

gates-json:
	@$(PYTHON) scripts/audit_gate_engagement.py --json

# META-GATE 2B: dynamic gate-effectiveness audit. Cross-references
# cage_engagement.jsonl, structural_anti_pattern_iter_*.json, eval_history.jsonl
# across every project workspace (incl. archives) to flag gates that engage
# but never raise verdicts -- the form_str-key-bug fingerprint -- vs gates
# missing only because gate_harness_result.json is absent (harness-output gap).
audit-gate-effectiveness:
	@$(PYTHON) scripts/audit_gate_effectiveness.py $(if $(JSON),--json,) $(if $(STRICT),--strict,) $(if $(VERBOSE),--verbose,)

audit-gate-effectiveness-strict:
	@$(PYTHON) scripts/audit_gate_effectiveness.py --strict

# META-GATE 2A — static scope-narrowing linter. AST-walks every function
# in src/ztare/{diagnostics,gates,orchestrator}, flags any function whose
# parameter list mentions a partition pair (visible/withheld, etc.) but
# whose body iterates only one side. Catches the gp163d-class blind
# spot statically — the source-level twin of the R26 runtime gate.
# Use --strict to fail CI on HIGH-severity findings.
audit-gate-coverage:
	@$(PYTHON) scripts/audit_gate_coverage.py $(if $(JSON),--json,) $(if $(STRICT),--strict,)

audit-gate-coverage-strict:
	@$(PYTHON) scripts/audit_gate_coverage.py --strict

audit-gate-coverage-self-test:
	@$(PYTHON) scripts/audit_gate_coverage.py --self-test

# GP-157 v5.0 Phase 5 Fix 1 (panel-approved 2026-04-25 night) — Linus
# MAINTAINERS-style auto-generated index. Regenerates docs/internal/gp_index.{md,tsv}
# from the live repo. Run after any GP-NNN add/move/archive.
gp-index:
	@$(PYTHON) scripts/build_gp_index.py

# GP-101 arch-map drift check. Iterates the validator's MAP_REGISTRY
# (currently autoresearch_loop; Phase 4b/4c will add orchestrator/{telemetry,state}).
# Use ex-ante before editing, ex-post after. ARCH_MAP=label restricts scope.
arch-validate:
	@$(PYTHON) -m scripts.validate_autoresearch_arch_map ex-post $(if $(ARCH_MAP),--only $(ARCH_MAP),)

arch-validate-ex-ante:
	@$(PYTHON) -m scripts.validate_autoresearch_arch_map ex-ante $(if $(ARCH_MAP),--only $(ARCH_MAP),)

# META-GATE 2C — retroactive post-run meta-audit. Runs the LLM diagnostic
# auditor against a completed project's workspace WITHOUT touching the
# main loop. Reads workspace/eval_history.jsonl + cage_engagement.jsonl +
# substrate_critique.json + iteration_telemetry.jsonl. Writes
# workspace/post_run_meta_audit.{json,md}. Default audit model is
# claude-haiku-4-5 (override via AUDIT_MODEL=...). Default newton 90.
# AUDIT_MODEL is its own variable so the global MODEL=gemini default
# does not override the cross-family-hygiene auditor pick.
AUDIT_MODEL ?= claude-haiku-4-5
NEWTON ?= 90
audit-run-meta:
ifndef PROJECT
	$(error PROJECT is required. Example: make audit-run-meta PROJECT=gp163d_unified_accel)
endif
	@echo "🧭 META-GATE 2C post-run meta-audit: project=$(PROJECT) audit_model=$(AUDIT_MODEL) newton=$(NEWTON)"
	@$(PYTHON) -c "import sys; from pathlib import Path; \
		from src.ztare.orchestrator.post_run_meta_audit import run_post_run_meta_audit; \
		v = run_post_run_meta_audit( \
			project_dir=Path('projects')/'$(PROJECT)', \
			run_id='retroactive', \
			audit_model_id='$(AUDIT_MODEL)', \
			newton_threshold=int('$(NEWTON)'), \
		); \
		import json; print(json.dumps(v, indent=2)[:4000])"

audit-prompt:
ifndef PROJECT
	$(error PROJECT is required. Example: make audit-prompt PROJECT=gp090_01 MUTATOR_MODEL=o3)
endif
	@echo "🔒 GP-134 prompt-layer leak audit: project=$(PROJECT), mutator=$(MUTATOR_MODEL)"
	@$(PYTHON) -m src.ztare.gates.prompt_leak_audit \
		--project $(PROJECT) \
		--mutator_model $(MUTATOR_MODEL) \
		--cache_dir ztare_workspace/prompt_leak_audit_cache \
		|| if [ "$(STRICT_LEAK_AUDIT)" = "1" ]; then \
			echo "❌ STRICT_LEAK_AUDIT=1 and audit failed — aborting"; exit 1; \
		else \
			echo "⚠️  Prompt leak audit reported potential leak (non-strict mode — continuing)"; \
		fi

loop: validate-rubric _preflight_leak_audit _preflight_charter_patches
ifeq ($(PROJECT),your_project)
	$(error PROJECT is required. Example: make loop PROJECT=gp161_mdl_anti_goodhart MUTATOR_MODEL=gpt4.1 JUDGE_MODEL=gpt4.1. \
	  Note: make variables must be on the SAME line as the target, or escape newlines with backslash.)
endif
	@RUBRIC_SLUG=$$(echo "$(RUBRIC)" | sed -e 's|^rubrics/||' -e 's|\.json$$||'); \
	$(PYTHON) -m src.ztare.validator.autoresearch_loop \
		--project $(PROJECT) \
		--rubric "$$RUBRIC_SLUG" \
		--iters $(ITERS) \
		--mutator_model $(MUTATOR_MODEL) \
		--judge_model $(JUDGE_MODEL) \
		--run-mode $(MODE) \
		$(DYNAMIC_FLAG) \
		$(EVOLVE_FLAG) \
		$(CROSS_FAMILY_FLAG) \
		$(COMMITTEE_MODEL_FLAG) \
		$(EXTRA_ARGS)

# Pre-flight rubric+project validation hook (deterministic).
# Runs on every `make loop` to catch malformed rubrics + missing project files
# BEFORE the autoresearch loop launches and burns iteration budget. Mirrors
# the rules in docs/concepts/rubric_specification.md and
# docs/internal/rubric_authoring_map.md. Hard fail on any violation.
# Override: skip with VALIDATE_RUBRIC=0 (not recommended).
validate-rubric:
ifeq ($(PROJECT),your_project)
	$(error PROJECT is required. Did you split the make command across multiple shell lines without backslash continuation? \
	  Example: make loop PROJECT=gp161_mdl_anti_goodhart MUTATOR_MODEL=gpt4.1 JUDGE_MODEL=gpt4.1)
endif
	@if [ "$(VALIDATE_RUBRIC)" = "0" ]; then \
		echo "⚠️  VALIDATE_RUBRIC=0 — skipping rubric pre-flight validator (NOT RECOMMENDED)"; \
	else \
		RUBRIC_PATH=$$(echo "$(RUBRIC)" | grep -q '/' && echo "$(RUBRIC)" || echo "rubrics/$(RUBRIC).json"); \
		$(PYTHON) scripts/validate_rubric.py $(PROJECT) --rubric $$RUBRIC_PATH || \
		(echo ""; echo "❌ Rubric pre-flight FAILED. Fix before launching."; \
		echo "   Spec: docs/concepts/rubric_specification.md"; \
		echo "   Map:  docs/internal/rubric_authoring_map.md"; exit 1); \
	fi

# Pre-flight leak-audit hook: only runs when last_prompt_debug.txt exists
# (i.e., after the first iteration of a prior run seeded the prompt artifact).
# First-run behavior: skip silently. Iteration 2+: audit before launching.
# STRICT_LEAK_AUDIT=1 upgrades this to a hard pre-flight gate.
_preflight_leak_audit:
	@if [ -f "projects/$(PROJECT)/last_prompt_debug.txt" ]; then \
		$(MAKE) audit-prompt PROJECT=$(PROJECT) MUTATOR_MODEL=$(MUTATOR_MODEL) \
			STRICT_LEAK_AUDIT=$(STRICT_LEAK_AUDIT) PYTHON=$(PYTHON) || true; \
	else \
		echo "🔒 No prior prompt artifact at projects/$(PROJECT)/last_prompt_debug.txt — skipping pre-flight leak audit (first run)"; \
	fi

# GP-226 charter-patch pre-iter-1 confirmation. Runs only when
# `enable_charter_critic: true` AND `charter_patches_preflight_mode` is set
# to "interactive" or "auto_confirm" in the rubric. Default mode "skip" is
# a no-op so this never blocks runs that haven't opted in.
_preflight_charter_patches:
	@RUBRIC_PATH=$$(echo "$(RUBRIC)" | grep -q '/' && echo "$(RUBRIC)" || echo "rubrics/$(RUBRIC).json"); \
	$(PYTHON) scripts/preflight_charter_patches.py $(PROJECT) \
		--rubric $$RUBRIC_PATH \
		--mutator-model $(MUTATOR_MODEL) || true

compress:
ifndef PROJECT
	$(error PROJECT is required. Example: make compress PROJECT=gp088_calibration_a01)
endif
	$(PYTHON) -m src.ztare.fit.compress_champion --project $(PROJECT)

# Full autonomous pipeline: run experiment → compress champion → generate Lean proofs
discover: _preflight_leak_audit
ifndef PROJECT
	$(error PROJECT is required)
endif
	@echo "════════════════════════════════════════════════════════════"
	@echo "  ZTARE Full Discovery Pipeline — $(PROJECT)"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Phase 1: Hypothesis generation (experiment-loop)..."
	$(PYTHON) -m src.ztare.validator.autoresearch_loop \
		--project $(PROJECT) \
		--rubric $$(echo "$(RUBRIC)" | sed 's/\.json$$//') \
		--iters $(ITERS) \
		--mutator_model $(MUTATOR_MODEL) \
		--judge_model $(JUDGE_MODEL) \
		--disable_attacker_tools \
		--underidentified_after $(ITERS) \
		$(DYNAMIC_FLAG) \
		$(EVOLVE_FLAG) \
		$(CROSS_FAMILY_FLAG) \
		$(COMMITTEE_MODEL_FLAG) \
		$(EXTRA_ARGS) || true
	@echo ""
	@echo "Phase 2: Compression (GP-103 template enumeration)..."
	$(PYTHON) -m src.ztare.fit.compress_champion --project $(PROJECT) --install-best || true
	@echo ""
	@echo "Phase 2.5: Margin of safety + remediation (GP-112)..."
	$(PYTHON) -m src.ztare.fit.margin_of_safety --project $(PROJECT) || true
	@echo ""
	@echo "Phase 2.7: Post-UNDERIDENTIFIED pipeline (observable rotation + gap accumulation)..."
	$(PYTHON) -c "from src.ztare.fit.post_underidentified import run_post_underidentified; \
		from pathlib import Path; \
		p = Path('projects/$(PROJECT)'); \
		ms = p / 'workspace' / 'margin_of_safety.json'; \
		import json; \
		verdict = json.loads(ms.read_text()).get('remediation',{}).get('verdict','') if ms.exists() else ''; \
		run_post_underidentified(p) if 'PERSIST' in verdict or 'UNDERIDENTIFIED' in verdict else print('  No PERSIST/UNDERIDENTIFIED — skipping')" || true
	@echo ""
	@echo "Phase 2.6: Diagnosis feedback check (GP-113)..."
	$(PYTHON) -c "from src.ztare.fit.diagnosis_feedback import inject_diagnosis_into_constraints; \
		from pathlib import Path; \
		r = inject_diagnosis_into_constraints(Path('projects/$(PROJECT)')); \
		print('  Diagnosis injected into derived_constraints_brief.md' if r else '  No PERSIST — skipping Phase 1b')" || true
	@echo ""
	@echo "Phase 3: Lean proof generation..."
	$(PYTHON) -m src.ztare.formal.lean_compiler --project $(PROJECT) || true
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Discovery pipeline complete"
	@echo "  Champion: projects/$(PROJECT)/test_model.py"
	@echo "  Compression: projects/$(PROJECT)/workspace/compression_results.json"
	@echo "  Margin: projects/$(PROJECT)/workspace/margin_of_safety.json"
	@echo "  Lean stubs: projects/$(PROJECT)/$(PROJECT).lean"
	@echo "════════════════════════════════════════════════════════════"

prove:
ifndef PROJECT
	$(error PROJECT is required. Example: make prove PROJECT=gp088_calibration_a01)
endif
	@echo "════════════════════════════════════════════════════════════"
	@echo "  ZTARE → Lean 4 Proof Pipeline — $(PROJECT)"
	@echo "════════════════════════════════════════════════════════════"
	@echo "Step 1: Compiling gate results to Lean 4..."
	$(PYTHON) -m src.ztare.formal.lean_compiler --project $(PROJECT)
	@echo ""
	@LEAN_FILE="projects/$(PROJECT)/$(PROJECT).lean"; \
	PROOF_DIR="ztare_proofs/ZtareProofs"; \
	if [ ! -d "$$PROOF_DIR" ]; then mkdir -p "$$PROOF_DIR"; fi; \
	DEST="$$PROOF_DIR/$$(echo $(PROJECT) | sed 's/[^a-zA-Z0-9]//g').lean"; \
	echo "Step 2: Copying to ztare_proofs..."; \
	cp "$$LEAN_FILE" "$$DEST"; \
	echo "  $$LEAN_FILE → $$DEST"; \
	echo ""; \
	echo "Step 3: Building with lake..."; \
	cd ztare_proofs && lake build 2>&1 || true; \
	echo ""; \
	echo "════════════════════════════════════════════════════════════"; \
	echo "  ✅ Proof pipeline complete"; \
	echo "  Output: $$DEST"; \
	echo "  Run 'cd ztare_proofs && lake build' to re-check"; \
	echo "════════════════════════════════════════════════════════════"

experiment-loop:
	@RUBRIC_PATH=$$(echo "$(RUBRIC)" | grep -q '/' && echo "$(RUBRIC)" || echo "rubrics/$(RUBRIC).json"); \
	RUBRIC_BARE=$$(basename "$$RUBRIC_PATH" .json); \
	PROJECT_BARE=$$(echo "$(PROJECT)" | sed 's|^projects/||'); \
	PROJ_DIR="projects/$$PROJECT_BARE"; \
	if [ ! -f "$$RUBRIC_PATH" ]; then echo "ERROR: rubric not found at $$RUBRIC_PATH"; exit 1; fi; \
	$(MAKE) validate-rubric PROJECT=$$PROJECT_BARE RUBRIC=$$RUBRIC_PATH PYTHON=$(PYTHON) || exit 1; \
	HARD_GATE=$$($(PYTHON) -c "import json; r=json.load(open('$$RUBRIC_PATH')); print('1' if r.get('holdout_hard_gate') else '0')"); \
	COMPUTED_EXTRA="--disable_attacker_tools"; \
	if [ "$$HARD_GATE" = "1" ]; then \
		echo "📋 Rubric has holdout_hard_gate=true — auto-setting --underidentified_after=$(ITERS)"; \
		if [ ! -f "$$PROJ_DIR/gate_harness.py" ]; then echo "ERROR: holdout_hard_gate declared but $$PROJ_DIR/gate_harness.py missing"; exit 1; fi; \
		if [ ! -f "$$PROJ_DIR/evidence_holdout.txt" ]; then echo "ERROR: holdout_hard_gate declared but $$PROJ_DIR/evidence_holdout.txt missing"; exit 1; fi; \
		echo "🔍 Pre-flight: verifying gate harness executes..."; \
		HARNESS_OUT=$$($(PYTHON) "$$PROJ_DIR/gate_harness.py" --emit-deterministic-gates 2>/dev/null || true); \
		if echo "$$HARNESS_OUT" | $(PYTHON) -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then \
			echo "✅ Gate harness produces valid JSON (baseline model may fail holdout — that is expected)"; \
		else \
			echo "ERROR: gate_harness.py did not produce valid JSON — fix before launching"; \
			echo "$$HARNESS_OUT"; \
			exit 1; \
		fi; \
		UNDERIDENTIFIED_AFTER=$(ITERS); \
		COMPUTED_EXTRA="$$COMPUTED_EXTRA --underidentified_after $$UNDERIDENTIFIED_AFTER"; \
	fi; \
	REVIEWER_DOMAINS=$$($(PYTHON) -c "import json; r=json.load(open('$$RUBRIC_PATH')); d=r.get('reviewer_domains',[]); print(','.join(d)) if d else print('')" 2>/dev/null); \
	if [ -n "$$REVIEWER_DOMAINS" ]; then \
		echo "🔍 Rubric declares reviewer_domains: $$REVIEWER_DOMAINS (used by findings runner, not loop)"; \
	fi; \
	echo "🚀 Launching: make loop PROJECT=$$PROJECT_BARE RUBRIC=$$RUBRIC_BARE ITERS=$(ITERS) EXTRA_ARGS=\"$$COMPUTED_EXTRA\""; \
	$(MAKE) loop PROJECT=$$PROJECT_BARE RUBRIC=$$RUBRIC_BARE ITERS=$(ITERS) MUTATOR_MODEL=$(MUTATOR_MODEL) JUDGE_MODEL=$(JUDGE_MODEL) MODE=$(MODE) DYNAMIC=$(DYNAMIC) EVOLVE=$(EVOLVE) CROSS_FAMILY=$(CROSS_FAMILY) COMMITTEE_MODEL=$(COMMITTEE_MODEL) EXTRA_ARGS="$$COMPUTED_EXTRA"

## GP-104: Generate qualitative project scaffold with correct Type B gate configuration
## Usage: make generate-gp PROJECT=my_project BRIEF="one paragraph thesis question" [JUDGE_MODEL=gpt4.1]
generate-gp:
ifndef PROJECT
	$(error PROJECT is required: make generate-gp PROJECT=name BRIEF="...")
endif
ifndef BRIEF
	$(error BRIEF is required: make generate-gp PROJECT=name BRIEF="...")
endif
	$(PYTHON) -m src.ztare.scaffold.generate_gp_project \
		--slug $(PROJECT) \
		--brief "$(BRIEF)" \
		--judge-model $(or $(JUDGE_MODEL),gpt4.1)

## GP-072 Phase 4+6 pre-run seal gate
## Usage: make seal PROJECT=gp078_cal_sigma_02 RUBRIC=rubrics/gp078_cal_sigma_02.json
seal:
ifndef PROJECT
	$(error PROJECT is required. Example: make seal PROJECT=foo RUBRIC=rubrics/foo.json)
endif
	@RUBRIC_PATH=$$(echo "$(RUBRIC)" | grep -q '/' && echo "$(RUBRIC)" || echo "rubrics/$(RUBRIC).json"); \
	PROJECT_BARE=$$(echo "$(PROJECT)" | sed 's|^projects/||'); \
	PROJ_DIR="projects/$$PROJECT_BARE"; \
	DENYLIST="$$PROJ_DIR/.denylist"; \
	echo ""; \
	echo "════════════════════════════════════════════════════════════"; \
	echo "  GP-072 Seal Gate — $$PROJECT_BARE"; \
	echo "════════════════════════════════════════════════════════════"; \
	echo ""; \
	echo "── Phase 3.5: Evidence Quality ──────────────────────────────"; \
	$(PYTHON) scripts/validate_evidence.py "$$PROJECT_BARE" --rubric "$$RUBRIC_PATH" && echo "  ✅ Evidence pre-flight PASSED" || { echo "  ❌ Evidence pre-flight FAILED — fix evidence.txt before sealing"; exit 1; }; \
	echo ""; \
	echo "── Phase 4: Leak Sentinel ──────────────────────────────────"; \
	if [ ! -f "$$DENYLIST" ]; then \
		echo "  ⚠️  WARNING: no .denylist found at $$DENYLIST — sentinel passes vacuously"; \
	else \
		$(PYTHON) -m src.ztare.validator.leak_sentinel "$$PROJ_DIR" "$$RUBRIC_PATH" --denylist-file "$$DENYLIST" && echo "  ✅ Sentinel PASSED" || { echo "  ❌ Sentinel FAILED — fix leaks before running"; exit 1; }; \
	fi; \
	echo ""; \
	echo "── Phase 5: Domain-Expert Rubric Review ────────────────────"; \
	echo "  GP-072 Phase 5 is a blocking gate. Answer all three questions."; \
	echo "  (Press enter to confirm each, or Ctrl-C to abort and fix the rubric.)"; \
	echo ""; \
	echo "  5.1 RUBRIC-TO-GT COMPATIBILITY"; \
	echo "      Is the rubric's dimension set and weight distribution compatible"; \
	echo "      with the true answer class? (Requires Division A GT knowledge.)"; \
	read -p "  Answer (pass/fail): " P5_1; \
	if [ "$$P5_1" != "pass" ]; then echo "  ❌ Phase 5.1 FAILED — fix rubric before sealing"; exit 1; fi; \
	echo ""; \
	echo "  5.2 GP-103 REJECTION CHECKLIST (anti-recurrence of known rubric defects)"; \
	echo "      Check ALL of the following in the rubric JSON text fields:"; \
	echo "      [ ] No absolute parameter count ceiling in persona (e.g. '3-parameter model')"; \
	echo "      [ ] No parameter count ceiling in Dimension 3 / Criterion 3"; \
	echo "      [ ] Parsimony framing rewards structural justification, not numeric limits"; \
	echo "      [ ] Persona does not name the correct answer class or any physical law"; \
	echo "      [ ] Rubric admits multi-regime additive composites if substrate requires them"; \
	PARAM_CEILING=$$($(PYTHON) -c "import json,re; r=json.load(open('$$RUBRIC_PATH')); hits=re.findall(r'\b[0-9]+-parameter\b',json.dumps(r)); print(' '.join(hits) if hits else 'none')" 2>/dev/null); \
	if [ "$$PARAM_CEILING" != "none" ]; then \
		echo "  ❌ GP-103 AUTO-CHECK FAILED: found parameter ceiling(s): $$PARAM_CEILING"; \
		echo "     Remove numeric parameter ceilings from rubric text before sealing."; \
		exit 1; \
	else \
		echo "  ✅ GP-103 auto-check: no numeric parameter ceilings found"; \
	fi; \
	read -p "  All five checklist items confirmed? (yes/no): " P5_2; \
	if [ "$$P5_2" != "yes" ]; then echo "  ❌ Phase 5.2 FAILED — fix rubric before sealing"; exit 1; fi; \
	echo ""; \
	echo "  5.3 PERSONA ADVERSARIAL AUDIT"; \
	echo "      Would the persona guide the judge toward or away from the correct answer type?"; \
	read -p "  Answer (pass/fail): " P5_3; \
	if [ "$$P5_3" != "pass" ]; then echo "  ❌ Phase 5.3 FAILED — fix rubric persona before sealing"; exit 1; fi; \
	echo "  ✅ Phase 5 domain-expert review PASSED"; \
	echo ""; \
	echo "── Phase 6: Integration Tests ──────────────────────────────"; \
	HARNESS="$$PROJ_DIR/gate_harness.py"; \
	if [ ! -f "$$HARNESS" ]; then \
		echo "  ⚠️  No gate_harness.py — skipping Phase 6 (not a holdout-gate project)"; \
	else \
		echo "  6.1 smoke-test..."; \
		$(PYTHON) "$$HARNESS" --run-smoke-test && echo "  ✅ smoke-test PASSED" || { echo "  ❌ smoke-test FAILED"; exit 1; }; \
		echo "  6.2 emit-deterministic-gates..."; \
		GATE_OUT=$$($(PYTHON) "$$HARNESS" --emit-deterministic-gates 2>/dev/null); \
		echo "$$GATE_OUT" | $(PYTHON) -c "import sys,json; d=json.load(sys.stdin); print('  ✅ gates JSON valid | harness_ok=' + str(d.get('harness_ok')))" 2>/dev/null || { echo "  ❌ gates JSON invalid"; exit 1; }; \
	fi; \
	echo ""; \
	echo "── Attestation ─────────────────────────────────────────────"; \
	SEAL_PATH="$$PROJ_DIR/sandbox_seal.json"; \
	$(PYTHON) -m src.ztare.scaffold.write_seal "$$PROJECT_BARE" "$$PROJ_DIR" "$$RUBRIC_PATH" "$$SEAL_PATH" && \
	echo ""; \
	echo "  🔒 SANDBOX SEALED — ready for: make experiment-loop PROJECT=$$PROJECT_BARE RUBRIC=$$RUBRIC_PATH ITERS=15 MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gpt4.1"; \
	echo "════════════════════════════════════════════════════════════"; \
	echo ""

## GP-072 sandbox wipe — resets iteration state, restores baseline, preserves sealed artifacts
## Removes: workspace/, history/, debate logs, eval/dag JSONs, pycache, current_iteration, last_prompt_debug
## Preserves: evidence files, gate_harness.py, project_charter.md, sandbox_seal.json, .denylist
## Restores: test_model.py to trivial baseline; thesis.md Fit Declaration to constant placeholder
## Usage: make wipe-sandbox PROJECT=gp096_sandbox_19_gagorder
wipe-sandbox:
ifndef PROJECT
	$(error PROJECT is required. Example: make wipe-sandbox PROJECT=gp096_sandbox_19_gagorder)
endif
	@PROJECT_BARE=$$(echo "$(PROJECT)" | sed 's|^projects/||'); \
	PROJ_DIR="projects/$$PROJECT_BARE"; \
	if [ ! -d "$$PROJ_DIR" ]; then echo "ERROR: $$PROJ_DIR does not exist"; exit 1; fi; \
	if [ -f "$$PROJ_DIR/sandbox_freeze.json" ]; then echo "ERROR: $$PROJECT_BARE is frozen. Wipe is blocked. Create a new project instead."; exit 1; fi; \
	echo ""; \
	echo "════════════════════════════════════════════════════════════"; \
	echo "  GP-072 Wipe — $$PROJECT_BARE"; \
	echo "════════════════════════════════════════════════════════════"; \
	echo "Removing iteration artifacts..."; \
	rm -rf "$$PROJ_DIR/workspace"; \
	rm -rf "$$PROJ_DIR/history"; \
	rm -rf "$$PROJ_DIR/__pycache__"; \
	rm -f "$$PROJ_DIR"/debate_log_iter_*.md; \
	rm -f "$$PROJ_DIR/current_iteration.md"; \
	rm -f "$$PROJ_DIR/last_prompt_debug.txt"; \
	rm -f "$$PROJ_DIR/latest_eval_results.json"; \
	rm -f "$$PROJ_DIR/latest_probability_dag.json"; \
	rm -f "$$PROJ_DIR/champion_eval_results.json"; \
	rm -f "$$PROJ_DIR/champion_probability_dag.json"; \
	rm -f "$$PROJ_DIR/latest_evidence_gaps.json"; \
	rm -f "$$PROJ_DIR"/structural_memory*.json; \
	echo "Restoring baseline test_model.py..."; \
	$(PYTHON) scripts/restore_baseline_test_model.py "$$PROJECT_BARE"; \
	echo "Re-creating empty workspace/ directory..."; \
	mkdir -p "$$PROJ_DIR/workspace"; \
	echo "Clearing thesis Fit Declaration to placeholder..."; \
	$(PYTHON) -c "\
import re, pathlib; \
p = pathlib.Path('$$PROJ_DIR/thesis.md'); \
txt = p.read_text(); \
txt = re.sub(r'<!-- best_iteration:.*?-->', '', txt); \
txt = re.sub(r'(## Fit Declaration\s*\x60\x60\x60json\s*)[\s\S]*?(\x60\x60\x60)', \
	r'\1{\"variables\": [], \"expression\": \"0\", \"parameter_names\": []}\n\2', txt); \
p.write_text(txt.strip() + '\n'); \
print('thesis.md Fit Declaration reset.') \
"; \
	echo ""; \
	echo "  ✅ Wipe complete — sealed artifacts preserved, baseline restored"; \
	echo "  Relaunch: make experiment-loop PROJECT=$$PROJECT_BARE RUBRIC=$$PROJECT_BARE ITERS=20 MUTATOR_MODEL=gemini JUDGE_MODEL=gemini"; \
	echo "════════════════════════════════════════════════════════════"; \
	echo ""

## GP-072 sandbox freeze — archives a completed run, prevents further iteration
## Writes sandbox_freeze.json with timestamp, champion summary, and GP-072 closure note
## Preserves ALL artifacts (workspace, debate logs, structural memory, champion files)
## After freeze: wipe is blocked; experiment-loop should not be re-run
## Usage: make freeze-sandbox PROJECT=gp096_sandbox_19_gagorder [NOTE="optional closure note"]
freeze-sandbox:
ifndef PROJECT
	$(error PROJECT is required. Example: make freeze-sandbox PROJECT=gp096_sandbox_19_gagorder)
endif
	@PROJECT_BARE=$$(echo "$(PROJECT)" | sed 's|^projects/||'); \
	PROJ_DIR="projects/$$PROJECT_BARE"; \
	if [ ! -d "$$PROJ_DIR" ]; then echo "ERROR: $$PROJ_DIR does not exist"; exit 1; fi; \
	if [ -f "$$PROJ_DIR/sandbox_freeze.json" ]; then echo "ERROR: $$PROJECT_BARE is already frozen."; exit 1; fi; \
	echo ""; \
	echo "════════════════════════════════════════════════════════════"; \
	echo "  GP-072 Freeze — $$PROJECT_BARE"; \
	echo "════════════════════════════════════════════════════════════"; \
	CHAMPION_SCORE=""; \
	if [ -f "$$PROJ_DIR/workspace/champion_eval_results.json" ]; then \
		CHAMPION_SCORE=$$($(PYTHON) -c "import json,sys; d=json.load(open('$$PROJ_DIR/workspace/champion_eval_results.json')); print(d.get('total_score', d.get('score', '?')))"); \
	fi; \
	SEAL_DATE=$$($(PYTHON) -c "import json; d=json.load(open('$$PROJ_DIR/sandbox_seal.json')); print(d.get('sealed_at','unknown'))" 2>/dev/null || echo "unknown"); \
	$(PYTHON) -c "\
import json, datetime, pathlib; \
p = pathlib.Path('$$PROJ_DIR/sandbox_freeze.json'); \
data = { \
  'project': '$$PROJECT_BARE', \
  'frozen_at': datetime.datetime.utcnow().isoformat() + 'Z', \
  'sealed_at': '$$SEAL_DATE', \
  'champion_score': '$$CHAMPION_SCORE' or None, \
  'note': '$(NOTE)' or None, \
  'status': 'FROZEN', \
}; \
p.write_text(json.dumps(data, indent=2) + '\n'); \
print('sandbox_freeze.json written.') \
"; \
	echo ""; \
	echo "  ✅ Freeze complete — all run artifacts preserved"; \
	echo "  Project is now archived. Do not re-run experiment-loop on a frozen sandbox."; \
	echo "  To start fresh: create a new project (e.g. gp096_sandbox_20)"; \
	echo "════════════════════════════════════════════════════════════"; \
	echo ""

synth:
	$(PYTHON) -m src.ztare.synthesis.synthesize \
		--project $(PROJECT) \
		--model $(MODEL) \
		--qa-model $(QA_MODEL) \
		$(if $(RENDERER),--renderer-type $(RENDERER),) \
		$(if $(filter 1,$(PDF)),--pdf,)

committee:
	$(PYTHON) -m src.ztare.validator.generate_committee --project $(PROJECT)

benchmark:
	$(PYTHON) benchmarks/constraint_memory/run_benchmark.py --judge-model $(BENCH_JUDGE) --jobs $(BENCH_JOBS)

benchmark-evidence:
	$(PYTHON) scripts/public/control/benchmark_evidence_check.py

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
	$(PYTHON) -m src.ztare.supervisor.supervisor_fixture_regression

benchmark-supervisor-registry:
	$(PYTHON) -m src.ztare.supervisor.supervisor_registry_check

benchmark-supervisor-seed-registry:
	$(PYTHON) -m src.ztare.supervisor.supervisor_seed_registry_check

benchmark-supervisor-genesis:
	$(PYTHON) -m src.ztare.supervisor.supervisor_genesis_fixture_regression

benchmark-supervisor-manifest:
	$(PYTHON) -m src.ztare.supervisor.supervisor_manifest_fixture_regression

benchmark-supervisor-backlog:
	$(PYTHON) -m src.ztare.supervisor.supervisor_backlog_fixture_regression

benchmark-supervisor-proposal:
	$(PYTHON) -m src.ztare.supervisor.supervisor_proposal_fixture_regression

benchmark-supervisor-staging:
	$(PYTHON) -m src.ztare.supervisor.supervisor_staging_fixture_regression

benchmark-supervisor-wrappers:
	$(PYTHON) -m src.ztare.supervisor.supervisor_wrapper_fixture_regression

benchmark-supervisor-refinement:
	$(PYTHON) -m src.ztare.supervisor.supervisor_refinement_fixture_regression

benchmark-supervisor-usage:
	$(PYTHON) -m src.ztare.supervisor.supervisor_usage_fixture_regression

benchmark-supervisor-autoloop:
	$(PYTHON) -m src.ztare.supervisor.supervisor_attended_autoloop_fixture_regression

benchmark-supervisor-program-autoloop:
	$(PYTHON) -m src.ztare.supervisor.supervisor_program_autoloop_fixture_regression

benchmark-supervisor-report:
	$(PYTHON) -m src.ztare.supervisor.supervisor_report_fixture_regression

benchmark-supervisor-gate-resolution:
	$(PYTHON) -m src.ztare.supervisor.supervisor_gate_resolution_fixture_regression

benchmark-supervisor-findings-debate:
	$(PYTHON) -m src.ztare.supervisor.supervisor_findings_debate_fixture_regression

benchmark-supervisor-findings-runner:
	$(PYTHON) -m src.ztare.supervisor.supervisor_findings_runner_fixture_regression

benchmark-prose-verifier:
	$(PYTHON) -m src.ztare.findings.prose_verifier_fixture_regression

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
	$(PYTHON) -m src.ztare.supervisor.supervisor_loop init \
		--status-path $(SUP_STATUS) \
		--run-id $(SUP_RUN_ID) \
		--program $(SUP_PROGRAM) \
		--target $(SUP_TARGET) \
		$(if $(SUP_MAX_REFINEMENT_COST),--max-refinement-cost-usd $(SUP_MAX_REFINEMENT_COST),)

supervisor-show:
	$(PYTHON) -m src.ztare.supervisor.supervisor_loop show \
		--status-path $(SUP_STATUS)

supervisor-what-next:
	$(PYTHON) -m src.ztare.supervisor.supervisor_what_next \
		--status-path $(SUP_STATUS)

supervisor-backlog:
	$(PYTHON) -m src.ztare.supervisor.supervisor_backlog \
		--program $(SUP_PROGRAM) \
		$(if $(SUP_PLAN_DIR),--output-dir $(SUP_PLAN_DIR),) \
		$(if $(SUP_EXECUTE),--execute,)

supervisor-proposal:
	$(PYTHON) -m src.ztare.supervisor.supervisor_proposal \
		--seed-id $(SUP_SEED) \
		--program-id $(SUP_PROGRAM) \
		$(if $(SUP_PLAN_DIR),--output-dir $(SUP_PLAN_DIR),) \
		$(if $(SUP_EXECUTE),--execute,)

supervisor-emit:
	$(PYTHON) -m src.ztare.supervisor.supervisor_loop emit-staging \
		--status-path $(SUP_STATUS) \
		--staging-dir $(SUP_STAGING)

supervisor-commit:
	$(PYTHON) -m src.ztare.supervisor.supervisor_loop commit-staging \
		--status-path $(SUP_STATUS) \
		--events-path $(SUP_EVENTS) \
		--staging-dir $(SUP_STAGING) \
		--staging-path $(SUP_REQUEST)

supervisor-launch:
	$(PYTHON) -m src.ztare.supervisor.supervisor_loop launch-staging \
		--status-path $(SUP_STATUS) \
		--staging-dir $(SUP_STAGING) \
		$(if $(SUP_EXECUTE),--execute,)

supervisor-autoloop:
	$(PYTHON) -m src.ztare.supervisor.supervisor_attended_autoloop \
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
	$(PYTHON) -m src.ztare.supervisor.supervisor_program_autoloop \
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
	$(PYTHON) -m src.ztare.supervisor.supervisor_report \
		--status-path $(SUP_STATUS) \
		$(if $(SUP_EVENTS),--events-path $(SUP_EVENTS),) \
		$(if $(SUP_REPORT_OUT),--output-path $(SUP_REPORT_OUT),) \
		$(if $(SUP_JSON_OUT),--json-out $(SUP_JSON_OUT),)

supervisor-resolve-gate:
	$(PYTHON) -m src.ztare.supervisor.supervisor_gate_resolution \
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
	$(PYTHON) -m src.ztare.reports.forensic_reporter --project epistemic_engine_v4 $(if $(RUN_ID),--run-id $(RUN_ID),)

v4-debate-init:
	$(PYTHON) -m src.ztare.orchestration.debate_orchestrator --project epistemic_engine_v4 init-stage1-fail $(if $(RUN_ID),--run-id $(RUN_ID),)

v4-debate-show:
	$(PYTHON) -m src.ztare.orchestration.debate_orchestrator --project epistemic_engine_v4 show $(TASK_ID)

v4-debate-merge:
	$(PYTHON) -m src.ztare.orchestration.debate_orchestrator --project epistemic_engine_v4 merge $(TASK_ID)


# GP-216 — Theory-Building Operations vocabulary v3 (descriptive registry)
theory-building-ops:
	$(PYTHON) -m src.ztare.research_director.theory_building_ops

theory-building-ops-json:
	$(PYTHON) -c "from src.ztare.research_director.theory_building_ops import VOCABULARY_V3; import json; print(json.dumps({k: {'name': v.name, 'tier': v.tier, 'mech': v.structural_mechanism, 'arcs': list(v.arc_examples), 'overlaps': list(v.overlaps_with), 'deployable': v.deployable, 'novel_residue': v.novel_residue} for k,v in VOCABULARY_V3.items()}, indent=2))"

structural-language-catalog:
	$(PYTHON) scripts/public/control/render_structural_language_catalog.py

# GP-216f Item 6 — knowledge-graph CI integration (Pattern 10 + cross-scale linter)

# Regenerate the unified knowledge graph (seams + arch maps + ops + gates).
# Output: analytics/queries/ztare_knowledge_graph.json
seam-graph:
	$(PYTHON) /tmp/gp216_unified_graph_extractor.py

# Validate graph drift: every seam node has a file; every depends_on resolves;
# every op_id is canonical; every gate reference exists.
validate-knowledge-graph:
	$(PYTHON) -m scripts.validate_knowledge_graph

# Validate cross-scale aliases: every documented alias (e.g., coordinate_compression
# at iteration scale ↔ core_01 at research scale) still resolves on both sides.
validate-cross-references:
	$(PYTHON) -m scripts.check_cross_scale_aliases

# Director query helper. Examples:
#   make query-graph ARGS="--hubs 8"
#   make query-graph ARGS="--depends-on GP-216"
#   make query-graph ARGS="--instantiates core_07"
query-graph:
	$(PYTHON) -m scripts.query_graph $(ARGS)

# NS Track B content-layer proof graph.  Examples:
#   make ns-trackb-graph ARGS="--summary"
#   make ns-trackb-graph ARGS="--depends-on PhaseLatencyLipschitzReserveBridge"
#   make ns-trackb-graph ARGS="--cycles"
NS_GRAPH_PYTHON ?= ./venv/bin/python3

ns-graph:
	$(NS_GRAPH_PYTHON) projects/ns_millennium_hunt/scripts/ns_graph.py $(ARGS)

ns-trackb-graph:
	$(NS_GRAPH_PYTHON) projects/ns_millennium_hunt/scripts/ns_graph.py artifact $(ARGS)

# Regenerate the NS Track B proof graph from Lean declarations.
# Output: projects/ns_millennium_hunt/workspace/queries/ns_trackb_artifact_graph.json
ns-trackb-graph-extract:
	$(NS_GRAPH_PYTHON) projects/ns_millennium_hunt/scripts/ns_graph.py artifact --extract $(ARGS)

# Run all knowledge-graph checks (graph drift + cross-scale aliases).
check-graph: validate-knowledge-graph validate-cross-references


# NS Track B continuous antitautology lint.
#
# Detects seven failure-mode patterns from TAUTOLOGY-SCOUR (2026-05-07):
#   A  : top-level `: Prop := True`
#   B  : axiom hypothesis `∀ T > 0, ∃ <vars>, <ineq>` not referencing `sol`
#   C  : `:= True` populating a Prop-valued structure field
#   D  : theorem with `∃ _, True` conclusion
#   E  : axiom with vacuous conclusion (`True` or `∃ _, True`)
#   F  : self-referential Prop definition (alias detector)
#   H  : witness-producing axiom for a canonical opaque sol-binding Prop
#        whose argument list lacks any function-space-bound term
#        (apparatus-Goodhart on FIX-D / SUBSTRATE-FIX, DARWIN 2026-05-07)
#
# Outputs:
#   analytics/queries/ns_antitautology_lint_<date>.json
#   projects/ns_millennium_hunt/workspace/research_notes/
#       ns_antitautology_lint_<date>.md
#
# Use `make ns-antitautology-check-strict` as a CI gate; it exits non-zero
# on any CRITICAL or HIGH finding. Run before shipping new ns_trackb_*.lean.
NS_LINT_PYTHON ?= ./venv/bin/python3

ns-antitautology-check:
	$(NS_LINT_PYTHON) scripts/ns_antitautology_continuous_lint.py

ns-antitautology-check-strict:
	$(NS_LINT_PYTHON) scripts/ns_antitautology_continuous_lint.py --strict

.PHONY: demo demo-current benchmark-evidence docs-check
demo:  ## Run small model-free evaluation-failure demos
	$(PYTHON) scripts/public/control/golden_path_demo.py

demo-current:  ## Run the model-free current-engine claim-discipline demo
	$(PYTHON) scripts/public/control/current_engine_demo.py

.PHONY: docs-check
docs-check:  ## Fail if docs index is stale or any public doc lacks a description
	$(PYTHON) scripts/private/validate_docs_index.py
	$(PYTHON) scripts/public/validators/validate_markdown_links.py

.PHONY: smoke-public
smoke-public:  ## Public clone smoke: org runtime, forecast pool, and action intelligence
	$(PYTHON) scripts/public/control/runtime_smoke_test.py
	$(PYTHON) scripts/public/control/forecast/pool.py smoke
	$(PYTHON) scripts/public/control/action_intelligence.py smoke

.PHONY: public-adversarial-smoke
public-adversarial-smoke:  ## Adversarial public smoke: isolation, cleanup, docs, and boundary checks
	$(PYTHON) scripts/public/control/public_adversarial_smoke.py

.PHONY: smoke-docker
smoke-docker:  ## Docker smoke: build image and run public smoke checks inside it
	bash scripts/public/control/docker_smoke.sh

.PHONY: gates gates-engagement install-hooks
gates:  ## Run the publish-safety + docs-freshness + seam/spec-format forcing gates
	$(PYTHON) scripts/public/control/benchmark_evidence_check.py
	$(PYTHON) scripts/public/control/public_adversarial_smoke.py
	$(PYTHON) -m pytest scripts/private/test_publish_safety.py scripts/private/test_docs_freshness.py -q
	$(PYTHON) scripts/private/validate_seam_spec_format.py
install-hooks:  ## Install the local pre-push gate hook
	ln -sf ../../scripts/private/git-hooks/pre-push .git/hooks/pre-push && echo "pre-push hook installed"
