from __future__ import annotations

import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def test_makefile_python_script_paths_exist() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    refs = sorted(set(re.findall(r"(?<![A-Za-z0-9_./-])((?:scripts|projects)/[A-Za-z0-9_./-]+\.py)", makefile)))
    missing = [ref for ref in refs if not (REPO / ref).is_file()]
    assert missing == []


def test_public_smoke_workflow_make_targets_exist() -> None:
    workflow = REPO / ".github/workflows/public-smoke.yml"
    assert workflow.is_file()
    workflow_text = workflow.read_text(encoding="utf-8")
    makefile_text = (REPO / "Makefile").read_text(encoding="utf-8")
    declared_targets = set(
        re.findall(r"^([A-Za-z0-9_.-]+):(?:\s|$)", makefile_text, flags=re.MULTILINE)
    )
    invoked_targets = sorted(
        set(re.findall(r"^\s*run:\s*make\s+([A-Za-z0-9_.-]+)\b", workflow_text, flags=re.MULTILINE))
    )

    assert invoked_targets
    assert [target for target in invoked_targets if target not in declared_targets] == []


def test_evidence_prepare_runs_source_check_before_compilation() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "source-check:\n\t$(PYTHON) -m ztare.scaffold.source_check --project $(PROJECT)" in makefile
    assert (
        "workspace-update:\n"
        "\t$(MODEL_FALLBACK_ENV) $(PYTHON) -m ztare.workspace.update_workspace --project $(PROJECT) --model $(MODEL) "
        "--llm-timeout-seconds $(EVIDENCE_LLM_TIMEOUT) --llm-retries $(EVIDENCE_LLM_RETRIES)"
    ) in makefile
    assert (
        "evidence-compile:\n"
        "\t$(MODEL_FALLBACK_ENV) $(PYTHON) -m ztare.workspace.compile_evidence --project $(PROJECT) --mode workspace --model $(MODEL) "
        "--llm-timeout-seconds $(EVIDENCE_LLM_TIMEOUT) --llm-retries $(EVIDENCE_LLM_RETRIES)"
    ) in makefile

    match = re.search(
        r"^evidence-prepare:\n(?P<body>(?:\t.*\n)+)",
        makefile,
        flags=re.MULTILINE,
    )
    assert match is not None
    body = match.group("body")
    expected = [
        "$(MAKE) source-check PROJECT=$(PROJECT)",
        "$(MAKE) workspace-update PROJECT=$(PROJECT) MODEL=$(MODEL) MODEL_FALLBACK=$(MODEL_FALLBACK) EVIDENCE_LLM_TIMEOUT=$(EVIDENCE_LLM_TIMEOUT)",
        "$(MAKE) evidence-compile PROJECT=$(PROJECT) MODEL=$(MODEL) MODEL_FALLBACK=$(MODEL_FALLBACK) EVIDENCE_LLM_TIMEOUT=$(EVIDENCE_LLM_TIMEOUT)",
    ]
    positions = [body.index(snippet) for snippet in expected]
    assert positions == sorted(positions)


def test_setup_project_uses_single_source_checked_prepare_path() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert (
        "$(MAKE) evidence-fetch PROJECT=$(PROJECT) MODEL=$(MODEL) "
        "SEVERITY=$(SEVERITY) MAX_FETCHES=$(MAX_FETCHES) "
        "EVIDENCE_SEARCH_BACKEND=$(EVIDENCE_SEARCH_BACKEND) AUTO_COMPILE=0"
    ) in makefile
    assert (
        "&& $(MAKE) evidence-prepare PROJECT=$(PROJECT) MODEL=$(MODEL) "
        "EVIDENCE_LLM_TIMEOUT=$(EVIDENCE_LLM_TIMEOUT)"
    ) in makefile
    assert "&& $(MAKE) evidence-compile PROJECT=$(PROJECT) MODEL=$(MODEL)" not in makefile
    assert (
        "$(PYTHON) -m ztare.workspace.fetch_evidence --project $(PROJECT) "
        "--severity $(SEVERITY) --max-fetches $(MAX_FETCHES) --model $(MODEL) "
        "--search-backend $(EVIDENCE_SEARCH_BACKEND) $(AUTO_COMPILE_FLAG)"
    ) in makefile


def test_experiment_loop_passes_autoresearch_llm_budget() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "--llm_timeout_seconds $(AUTORESEARCH_LLM_TIMEOUT)" in makefile
    assert "--llm_retries $(AUTORESEARCH_LLM_RETRIES)" in makefile
    assert "AUTORESEARCH_LLM_TIMEOUT=$(AUTORESEARCH_LLM_TIMEOUT)" in makefile
    assert "AUTORESEARCH_LLM_RETRIES=$(AUTORESEARCH_LLM_RETRIES)" in makefile


def test_subscription_codex_workers_inherit_declared_model_and_effort_budget() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "AGENT_CODEX_MODEL ?= $(MUTATOR_MODEL)" in makefile
    assert "AGENT_CODEX_REASONING_EFFORT ?= low" in makefile
    assert "ZTARE_CODEX_AGENT_MODEL=$(AGENT_CODEX_MODEL)" in makefile
    assert "ZTARE_CODEX_AGENT_REASONING_EFFORT=$(AGENT_CODEX_REASONING_EFFORT)" not in makefile
    assert "$(PYTHON) -m src.ztare.common.env_launch $(AGENT_DISPATCH_ENV)" in makefile


def test_experiment_loop_propagates_intake_boundary_to_loop() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "INTAKE ?= $(PACKET)" in makefile
    assert "AUTORESEARCH_INTAKE_FLAG := $(if $(INTAKE),--intake $(INTAKE),)" in makefile
    assert "INTAKE=$(INTAKE)" in makefile
    assert "Use either INTAKE or PACKET for project intake" in makefile


def test_experiment_loop_propagates_preflight_only_boundary_to_loop() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "$(if $(PREFLIGHT_ONLY),--preflight-only,)" in makefile
    assert "PREFLIGHT_ONLY=$(PREFLIGHT_ONLY)" in makefile


def test_autoresearch_route_make_target_accepts_intake_boundary() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    match = re.search(
        r"^autoresearch-route:\n(?P<body>(?:\t.*\n)+)",
        makefile,
        flags=re.MULTILINE,
    )
    assert match is not None
    assert "$(AUTORESEARCH_INTAKE_FLAG)" in match.group("body")


def test_autoresearch_trace_make_target_uses_canonical_package_namespace() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    match = re.search(
        r"^autoresearch-trace:\n(?P<body>(?:\t.*\n)+)",
        makefile,
        flags=re.MULTILINE,
    )
    assert match is not None
    body = match.group("body")
    assert "$(PYTHON) -m ztare.reports.autoresearch_trace" in body
    assert "$(PYTHON) -m src.ztare.reports.autoresearch_trace" not in body
    assert "$(AUTORESEARCH_INTAKE_FLAG)" in body


def test_autoresearch_health_make_target_accepts_intake_boundary() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    match = re.search(
        r"^autoresearch-kernel-health:\n(?P<body>(?:\t.*\n)+)",
        makefile,
        flags=re.MULTILINE,
    )
    assert match is not None
    assert "$(AUTORESEARCH_INTAKE_FLAG)" in match.group("body")


def test_publish_gate_runs_public_claim_boundary_checks() -> None:
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    match = re.search(r"^gates:.*?(?=^install-hooks:)", makefile, flags=re.MULTILINE | re.DOTALL)
    assert match is not None
    gate_block = match.group(0)
    gate_header = gate_block.splitlines()[0]
    assert "compile-src" in gate_header
    assert "flakes" in gate_header
    assert "flakes-leanmill" in gate_header
    assert "$(PYTHON) -m compileall -q src/ztare" in makefile
    assert "scripts/public/control/undefined_name_gate.py" in makefile
    assert "pyflakes src/ztare" not in makefile

    required = [
        "scripts/public/control/benchmark_evidence_check.py",
        "scripts/public/control/evaluator_hardening_frozen_check.py",
        "scripts/public/control/evidence_packet_check.py",
        "scripts/public/control/scope_boundary_audit.py",
        "scripts/public/control/public_terminology_audit.py",
        "scripts/public/control/research_move_routing_drift_audit.py",
        "scripts/public/control/public_adversarial_smoke.py",
    ]
    assert [snippet for snippet in required if snippet not in gate_block] == []
