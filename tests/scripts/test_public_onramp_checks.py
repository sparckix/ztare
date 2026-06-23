from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib

import pytest


def load_script_module(name: str, relpath: str):
    script = Path(relpath).resolve()
    spec = importlib.util.spec_from_file_location(name, script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_public_adversarial_smoke_run_timeout_is_bounded() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    proc = module.run(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        timeout=1,
    )

    assert proc.returncode == 124
    assert "command timed out after 1s" in proc.stderr


def test_scope_boundary_audit_classifies_bounded_and_unbounded_claims() -> None:
    module = load_script_module(
        "scope_boundary_audit",
        "scripts/public/control/scope_boundary_audit.py",
    )
    fake_path = module.REPO / "README.md"

    unbounded_lines = ["ZTARE is the best autonomous mathematical-research system."]
    bounded_lines = [
        "Non-claims.",
        "ZTARE is not the best autonomous mathematical-research system.",
        "The missing falsifier is an external baseline.",
    ]

    unbounded = module.classify(fake_path, 0, unbounded_lines)
    bounded = module.classify(fake_path, 1, bounded_lines)
    markdown_bounded = module.classify(
        fake_path,
        0,
        ['This is **not** "consciousness solved," and not a benchmark claim.'],
    )
    code_symbol = module.classify(
        fake_path,
        0,
        ["The `solved` field is a typed status, not a claim."],
    )
    hyphenated_descriptor = module.classify(
        fake_path,
        0,
        ["Solved-regime / classical-system asymmetry is a descriptor."],
    )

    assert unbounded is not None
    assert unbounded["boundary_context"] is False
    assert bounded is not None
    assert bounded["boundary_context"] is True
    assert markdown_bounded is not None
    assert markdown_bounded["boundary_context"] is True
    assert code_symbol is None
    assert hyphenated_descriptor is None


def test_scope_boundary_audit_includes_root_public_entry_files() -> None:
    module = load_script_module(
        "scope_boundary_audit",
        "scripts/public/control/scope_boundary_audit.py",
    )

    targets = {str(path.relative_to(module.REPO)) for path in module.iter_files()}

    assert "README.md" in targets
    assert "PRINCIPLES.md" in targets
    assert "CONTRIBUTING.md" in targets
    assert "SECURITY.md" in targets
    assert "docs/concepts/capabilities.md" in targets
    assert "docs/concepts/harness_specification.md" in targets
    assert "docs/concepts/leanmill_design_history.md" in targets
    assert "docs/guides/for_researchers.md" in targets
    assert "docs/multi_substrate_validation.md" in targets
    assert "docs/sprint_70day_journey.md" in targets


def test_public_terminology_audit_blocks_front_door_shorthand() -> None:
    module = load_script_module(
        "public_terminology_audit",
        "scripts/public/control/public_terminology_audit.py",
    )
    fake_path = module.REPO / "README.md"

    forbidden = module.classify_line(
        fake_path,
        1,
        "- GP-075 governs rubric generation for unknown domains.",
    )
    forbidden_link = module.classify_line(
        fake_path,
        2,
        "### 21.3 [GP-168](../../research_areas/seams/mission/org/GP-168_org_design_unfalsifiability_seam.md) Forced-REFRAME flags",
    )
    allowed = module.classify_line(
        fake_path,
        3,
        "- Rubric for unknown domains governs discovery rubrics. Historical seam: `GP-075`.",
    )
    adjectival = module.classify_line(
        fake_path,
        4,
        "# Provide the brief following the GP-072 sandbox discipline.",
    )
    lift = module.classify_line(
        fake_path,
        5,
        "- Not a broad apparatus-lift claim.",
    )
    apparatus_evidence = module.classify_line(
        fake_path,
        5,
        "This does not erase apparatus evidence.",
    )
    current_engine = module.classify_line(
        fake_path,
        5,
        "`make hello` runs the current-engine demo.",
    )
    dogfood = module.classify_line(
        fake_path,
        5,
        "The public demo dogfoods the gates.",
    )
    research_os = module.classify_line(
        fake_path,
        5,
        "ZTARE is strongest as a research operating system.",
    )
    load_bearing = module.classify_line(
        fake_path,
        5,
        "These are load-bearing invariants.",
    )
    real_work = module.classify_line(
        fake_path,
        5,
        "This is where real work happens.",
    )
    profile_label = module.classify_line(
        fake_path,
        5,
        "This shows a research-engineer / principal-orchestrator profile.",
    )
    apparatus_deployment = module.classify_line(
        fake_path,
        5,
        "Cross-substrate apparatus deployment is the current evidence.",
    )
    autonomous_engine = module.classify_line(
        fake_path,
        5,
        "No autonomous research engine.",
    )
    metadata_tag = module.classify_line(
        fake_path,
        5,
        'keywords = ["evidence-packets"]',
    )
    metadata_phrase = module.classify_line(
        fake_path,
        5,
        "Public evidence packets linked from release notes.",
    )
    old_example_slug = module.classify_line(
        fake_path,
        5,
        "ztare autoresearch route --project gp_example --rubric gp_example",
    )
    overfit_project_slug = module.classify_line(
        fake_path,
        5,
        "ztare autoresearch route --project single_example_overfit_2026",
    )
    venue = module.classify_line(
        fake_path,
        6,
        "The current paper and " + "TM" + "LR packet are organized under the project directory.",
    )
    lands_hard = module.classify_line(
        fake_path,
        6,
        "The claim lands hard in the README.",
    )
    quality_bar = module.classify_line(
        fake_path,
        6,
        "The repo should read as world class.",
    )
    catalog = module.classify_line(
        fake_path,
        7,
        "The cheating catalog should be the public hook.",
    )
    catalog_allowed = module.classify_line(
        fake_path,
        8,
        "The gaming behavior catalog should be the public hook.",
    )
    stale_descriptor = module.classify_line(
        fake_path,
        9,
        "The adversarial-reasoning engine wraps the public CLI.",
    )
    stale_keyword = module.classify_line(
        fake_path,
        10,
        'keywords = ["adversarial-reasoning", "research-engine"]',
    )
    stale_route_names = module.classify_line(
        fake_path,
        11,
        "The substrate-prober workflow and workbench workflow are for general-purpose engine users.",
    )
    stale_engine_name = module.classify_line(
        fake_path,
        12,
        "The epistemic engine should be public-facing.",
    )
    stale_packet_intake = module.classify_line(
        fake_path,
        13,
        "Use substrate packet intake before the loop.",
    )
    allowed_epistemic_engineering = module.classify_line(
        fake_path,
        14,
        "This is epistemic engineering discipline.",
    )
    stale_prep_ledger = module.classify_line(
        fake_path,
        15,
        "Use the substrate prep ledger before the loop.",
    )
    internal_doc_path = module.classify_line(
        fake_path,
        16,
        "See docs/internal/roadmap for the maintainer plan.",
    )
    private_research_path = module.classify_line(
        fake_path,
        17,
        "See research_areas/private/seams for the full record.",
    )
    generic_packet_route = module.classify_line(
        fake_path,
        18,
        "Choose the route, then prepare the packet before running the loop.",
    )
    review_packet_question = module.classify_line(
        fake_path,
        19,
        "Ask what can this review packet actually answer before launch.",
    )
    bounded_review_packet = module.classify_line(
        fake_path,
        20,
        "A claim against a bounded review packet enters the loop.",
    )
    packet_exists = module.classify_line(
        fake_path,
        21,
        "Run in-loop once the packet exists.",
    )
    packet_stable = module.classify_line(
        fake_path,
        22,
        "Do not leave kernel work in chat once the packet is stable.",
    )
    stale_kernel_entry = module.classify_line(
        fake_path,
        22,
        "The trace/kernel-entry console is ready.",
    )
    stale_role_word = module.classify_line(
        fake_path,
        23,
        "The first user is a technical operator inspecting local artifacts.",
    )
    stale_console_word = module.classify_line(
        fake_path,
        23,
        "Open the Operator console when you want a direct session.",
    )
    stale_patch_word = module.classify_line(
        fake_path,
        23,
        "The pre-reg should name operator-patch temptations before the run.",
    )
    stale_human_role_word = module.classify_line(
        fake_path,
        23,
        "This is a single-operator repo with operator-curated taxonomies, operator-committed fixtures, and operator remains an uncontrolled variable.",
    )
    gp_link_label = module.classify_line(
        fake_path,
        24,
        "[GP-088](../../research_areas/seams/apparatus/instrumentation/GP-088_ansatz_to_prover_seam.md) Lean-4 proof gate.",
    )
    gp_cell_label = module.classify_line(
        fake_path,
        25,
        "| **Parameter** | curve_fit | [GP-088](../../research_areas/seams/apparatus/instrumentation/GP-088_ansatz_to_prover_seam.md): d=0.562 |",
    )
    bare_gp_cell_label = module.classify_line(
        fake_path,
        26,
        "| **Apparatus** | Architecture | GP-088: grammar-guided symbolic regression could only compose additively |",
    )
    raw_path_link_label = module.classify_line(
        fake_path,
        27,
        "[`projects/gp169_consciousness_ascription_audit/`](../projects/gp169_consciousness_ascription_audit/)",
    )
    human_path_link_label = module.classify_line(
        fake_path,
        28,
        "[consciousness-ascription audit](../projects/gp169_consciousness_ascription_audit/)",
    )
    checked_targets = {
        str(path.relative_to(module.REPO))
        for path in module.iter_existing_targets()
    }

    assert forbidden
    assert forbidden[0]["kind"] == "bare_gp_label"
    assert forbidden_link
    assert forbidden_link[0]["kind"] == "bare_gp_heading"
    assert allowed == []
    assert adjectival
    assert adjectival[0]["kind"] == "adjectival_gp_id"
    assert lift
    assert lift[0]["kind"] == "forbidden_term"
    assert apparatus_evidence
    assert apparatus_evidence[0]["kind"] == "forbidden_term"
    assert current_engine
    assert current_engine[0]["kind"] == "forbidden_term"
    assert dogfood
    assert dogfood[0]["kind"] == "forbidden_term"
    assert research_os
    assert research_os[0]["kind"] == "forbidden_term"
    assert load_bearing
    assert load_bearing[0]["kind"] == "forbidden_term"
    assert real_work
    assert real_work[0]["kind"] == "forbidden_term"
    assert len(profile_label) == 2
    assert all(item["kind"] == "forbidden_term" for item in profile_label)
    assert apparatus_deployment
    assert apparatus_deployment[0]["kind"] == "forbidden_term"
    assert autonomous_engine
    assert autonomous_engine[0]["kind"] == "forbidden_term"
    assert metadata_tag
    assert metadata_tag[0]["kind"] == "forbidden_term"
    assert metadata_phrase
    assert metadata_phrase[0]["kind"] == "forbidden_term"
    assert old_example_slug
    assert old_example_slug[0]["kind"] == "forbidden_term"
    assert overfit_project_slug
    assert overfit_project_slug[0]["kind"] == "forbidden_term"
    assert venue
    assert venue[0]["kind"] == "forbidden_term"
    assert lands_hard
    assert lands_hard[0]["kind"] == "forbidden_term"
    assert quality_bar
    assert quality_bar[0]["kind"] == "forbidden_term"
    assert catalog
    assert catalog[0]["kind"] == "forbidden_term"
    assert catalog_allowed == []
    assert stale_descriptor
    assert stale_descriptor[0]["kind"] == "forbidden_term"
    assert len(stale_keyword) == 2
    assert all(item["kind"] == "forbidden_term" for item in stale_keyword)
    assert len(stale_route_names) == 3
    assert all(item["kind"] == "forbidden_term" for item in stale_route_names)
    assert stale_engine_name
    assert stale_engine_name[0]["kind"] == "forbidden_term"
    assert stale_packet_intake
    assert stale_packet_intake[0]["kind"] == "forbidden_term"
    assert allowed_epistemic_engineering == []
    assert stale_prep_ledger
    assert stale_prep_ledger[0]["kind"] == "forbidden_term"
    assert internal_doc_path
    assert internal_doc_path[0]["kind"] == "forbidden_term"
    assert private_research_path
    assert private_research_path[0]["kind"] == "forbidden_term"
    assert generic_packet_route
    assert generic_packet_route[0]["kind"] == "forbidden_term"
    assert review_packet_question
    assert review_packet_question[0]["kind"] == "forbidden_term"
    assert bounded_review_packet
    assert bounded_review_packet[0]["kind"] == "forbidden_term"
    assert packet_exists
    assert packet_exists[0]["kind"] == "forbidden_term"
    assert packet_stable
    assert packet_stable[0]["kind"] == "forbidden_term"
    assert stale_kernel_entry
    assert stale_kernel_entry[0]["kind"] == "forbidden_term"
    assert stale_role_word
    assert stale_role_word[0]["kind"] == "forbidden_term"
    assert stale_console_word
    assert stale_console_word[0]["kind"] == "forbidden_term"
    assert stale_patch_word
    assert stale_patch_word[0]["kind"] == "forbidden_term"
    assert stale_human_role_word
    assert all(item["kind"] == "forbidden_term" for item in stale_human_role_word)
    assert gp_link_label
    assert gp_link_label[0]["kind"] == "gp_link_as_label"
    assert gp_cell_label
    assert gp_cell_label[0]["kind"] == "gp_cell_label"
    assert bare_gp_cell_label
    assert bare_gp_cell_label[0]["kind"] == "gp_cell_label"
    assert raw_path_link_label
    assert raw_path_link_label[0]["kind"] == "raw_id_link_label"
    assert human_path_link_label == []
    assert "make help" in module.COMMAND_SURFACES
    assert "ztare --help" in module.COMMAND_SURFACES
    assert "pyproject.toml" in checked_targets
    assert "CITATION.cff" in checked_targets
    assert "CHANGELOG.md" in checked_targets
    assert "RELEASE_CHECKLIST.md" in checked_targets
    assert "docs/gaming_behavior_catalog.md" in checked_targets
    assert "docs/concepts/agent_agnostic_recursive_gain.md" in checked_targets
    assert "docs/concepts/agentic_engineering_patterns.md" in checked_targets
    assert "docs/concepts/capabilities.md" in checked_targets
    assert "docs/concepts/forensic_workbench_interface.md" in checked_targets
    assert "docs/concepts/epistemic_principles.md" in checked_targets
    assert "docs/concepts/glossary.md" in checked_targets
    assert "docs/concepts/goodhart_at_every_layer.md" in checked_targets
    assert "docs/concepts/reflexive_engineering.md" in checked_targets
    assert "docs/concepts/reflexive_mining_methodology.md" in checked_targets
    assert "docs/guides/README.md" in checked_targets
    assert "docs/guides/cli.md" in checked_targets
    assert "docs/multi_substrate_validation.md" in checked_targets
    assert "docs/guides/for_researchers.md" in checked_targets
    assert "docs/guides/manual_console.md" in checked_targets
    assert "docs/guides/runtime_smoke_test.md" in checked_targets
    assert "docs/guides/workflow.md" in checked_targets
    assert "docs/guides/agent-prompts.md" in checked_targets
    assert "docs/landings/README.md" in checked_targets
    assert "docs/evidence_atlas/packet_coverage.md" in checked_targets
    assert "docs/evidence_atlas/packets/README.md" in checked_targets
    assert "docs/evidence_atlas/packets/leanmill_apn_audit.md" in checked_targets
    assert "docs/sprint_70day_journey.md" in checked_targets
    assert "examples/README.md" in checked_targets
    assert "examples/project_packets/README.md" in checked_targets
    assert "examples/substrate_packets/README.md" in checked_targets
    assert "src/ztare/cli.py" in checked_targets


def test_package_keywords_use_external_discovery_terms() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    keywords = set(pyproject["project"]["keywords"])

    assert "evidence-packets" not in keywords
    assert "audit-trails" in keywords


def test_public_runtime_dependencies_are_packaged() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = set(pyproject["project"]["dependencies"])

    payload = module.check_package_metadata()

    assert payload["ok"] is True
    assert "PyYAML>=6.0" in dependencies


def test_public_workflow_uses_package_metadata_for_dependencies() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )
    workflow = Path(".github/workflows/public-smoke.yml").read_text(encoding="utf-8")

    payload = module.check_public_workflow_wiring()

    assert payload["ok"] is True
    assert "python -m pip install -e ." in workflow
    assert "python -m pip install -e . PyYAML" not in workflow


def test_public_smoke_does_not_literalize_submission_venue_guard() -> None:
    source = Path("scripts/public/control/public_adversarial_smoke.py").read_text(
        encoding="utf-8"
    ).lower()

    assert ("tm" + "lr") not in source


def test_cli_guide_lists_every_top_level_command() -> None:
    module = load_script_module("ztare_cli_for_docs_check", "src/ztare/cli.py")
    guide = Path("docs/guides/cli.md").read_text(encoding="utf-8")
    documented = set(
        re.findall(r"\| `ztare ([a-z][a-z-]*)(?: [^`]*)?` \|", guide)
    )

    assert set(module._SUBCOMMANDS) <= documented


def test_repository_citation_metadata_matches_public_front_door() -> None:
    text = Path("CITATION.cff").read_text(encoding="utf-8")

    assert "version: \"0.2.0\"" in text
    assert "ZTARE: A Local Claim-Governance Workbench for Auditable Human-Agent Research" in text
    assert "socio-technical research system" not in text
    assert "BibTeX entries" not in text
    assert "zero-trust workbench" in text
    assert "claim governance" in text
    assert "claim auditing" in text


def test_evaluator_hardening_frozen_payload_keeps_d_arm_blocked() -> None:
    module = load_script_module(
        "evaluator_hardening_frozen_check",
        "scripts/public/control/evaluator_hardening_frozen_check.py",
    )

    payload = module.build_payload()

    assert payload["ok"] is True
    assert payload["artifact_backed_arms"] == 3
    assert payload["required_future_arms"] == ["D_ordinary_review"]
    assert payload["complete_four_arm_suite"] is False
    assert payload["ordinary_review_status"] == "blocked_not_run"
    assert payload["ordinary_review_prompt_export_ready"] is True
    assert payload["ordinary_review_prompt_export"]["source_run_bound"] is True
    assert payload["ordinary_review_prompt_export"]["specimen_count"] == 9
    assert payload["ordinary_review_prompt_export"]["import_template_ready"] is True
    assert payload["ordinary_review_prompt_export"]["import_preflight_ready"] is True
    assert payload["ordinary_review_prompt_packet_ready"] is True
    assert payload["ordinary_review_prompt_packet"]["source_run_bound"] is True
    assert payload["ordinary_review_prompt_packet"]["specimen_count"] == 9
    assert payload["ordinary_review_prompt_packet"]["prompt_hashes_match_runner_export"] is True
    assert payload["ordinary_review_prompt_packet"]["import_preflight_ready"] is True
    assert any(
        "not a completed four-arm comparison" in non_claim
        for non_claim in payload["non_claims"]
    )
    assert "ordinary_review_contract" in payload["artifacts"]
    assert "ordinary_review_blocker" in payload["artifacts"]


def test_ordinary_review_freeze_check_accepts_only_promotion_ready_runs(tmp_path: Path) -> None:
    module = load_script_module(
        "ordinary_review_freeze_check",
        "scripts/public/control/ordinary_review_freeze_check.py",
    )
    source_run = tmp_path / "source_run"
    source_run.mkdir()
    (source_run / "results.json").write_text(
        json.dumps([
            {"condition": "A_baseline_soft_judge", "specimen_id": "demo"},
        ]) + "\n",
        encoding="utf-8",
    )

    run_root = tmp_path / "run"
    row_dir = run_root / "demo" / module.ORDINARY_REVIEW_CONDITION
    row_dir.mkdir(parents=True)
    prompt_path = row_dir / "ordinary_review_prompt.txt"
    raw_path = row_dir / "ordinary_review.raw.json"
    eval_path = row_dir / "eval_results.json"
    prompt_text = "prompt\n"
    reviewed_at = "2026-06-19T00:00:00Z"
    prompt_path.write_text(prompt_text, encoding="utf-8")
    raw_path.write_text('{"score": 25}\n', encoding="utf-8")
    eval_path.write_text('{"returncode": 0}\n', encoding="utf-8")
    (run_root / "results.json").write_text(
        json.dumps([
            {
                "condition": module.ORDINARY_REVIEW_CONDITION,
                "specimen_id": "demo",
                "label": "bad",
                "score": 25,
                "passed_threshold": False,
                "structural_detected": True,
                "family_detected": False,
                "ordinary_review_source": "imported",
                "ordinary_review_model": "external-reviewer",
                "ordinary_review_reviewed_at": reviewed_at,
            }
        ]) + "\n",
        encoding="utf-8",
    )
    (run_root / "metrics_summary.json").write_text(
        json.dumps({
            "conditions": {
                module.ORDINARY_REVIEW_CONDITION: {
                    "num_specimens": 1,
                    "error_count": 0,
                    "false_accept_rate": 0.0,
                }
            }
        }) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "arm_id": module.ORDINARY_REVIEW_CONDITION,
        "source_run_bound": True,
        "can_promote_to_frozen_suite": True,
        "promotion_blockers": [],
        "error_count": 0,
        "selected_specimen_count": 1,
        "expected_source_specimen_count": 1,
        "selected_specimen_ids": ["demo"],
        "expected_source_specimen_ids": ["demo"],
        "missing_source_specimen_ids": [],
        "extra_specimen_ids": [],
        "review_sources": ["imported"],
        "rows": [
            {
                "specimen_id": "demo",
                "prompt_sha256": sha256_text(prompt_text),
                "prompt_path": str(prompt_path),
                "raw_review_path": str(raw_path),
                "eval_results_path": str(eval_path),
                "source": "imported",
                "model": "external-reviewer",
                "reviewed_at": reviewed_at,
                "provider_runtime": "external",
            }
        ],
    }
    (run_root / "ordinary_review_freeze_manifest.json").write_text(
        json.dumps(manifest) + "\n",
        encoding="utf-8",
    )

    payload = module.build_payload(run_root, source_run)

    assert payload["ok"] is True
    assert payload["specimen_count"] == 1
    assert payload["review_sources"] == ["imported"]

    manifest["rows"][0]["prompt_sha256"] = "wrong-hash"
    (run_root / "ordinary_review_freeze_manifest.json").write_text(
        json.dumps(manifest) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="prompt_sha256 mismatch"):
        module.build_payload(run_root, source_run)
    manifest["rows"][0]["prompt_sha256"] = sha256_text(prompt_text)

    manifest["rows"][0]["reviewed_at"] = "2026-06-20T00:00:00Z"
    (run_root / "ordinary_review_freeze_manifest.json").write_text(
        json.dumps(manifest) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="reviewed_at mismatch"):
        module.build_payload(run_root, source_run)
    manifest["rows"][0]["reviewed_at"] = reviewed_at

    manifest["can_promote_to_frozen_suite"] = False
    manifest["promotion_blockers"] = ["fixture blocker"]
    (run_root / "ordinary_review_freeze_manifest.json").write_text(
        json.dumps(manifest) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="not promotion-ready"):
        module.build_payload(run_root, source_run)


def test_gaming_catalog_audit_covers_registry_and_public_boundary() -> None:
    module = load_script_module(
        "gaming_catalog_audit",
        "scripts/public/control/gaming_catalog_audit.py",
    )

    payload = module.build_payload()

    assert payload["ok"] is True
    assert payload["registry_count"] == 18
    assert payload["status_counts"] == {"gated": 18}
    assert payload["substrate_counts"] == {"autoresearch": 12, "leanmill": 6}
    assert payload["evidence_tier_counts"] == {
        "promotion_receipt": 8,
        "registry_row": 18,
        "reproduced_incident": 12,
        "runtime_gate": 18,
    }
    assert payload["promotion_evidence_rows"] == 8
    assert payload["original_nine_headings"] == 9
    assert payload["executable_anchor_count"] == 5
    assert payload["executable_anchor_vectors"] == [
        "assumption_as_evidence_relabeling",
        "definitional_tautology_self_confirming_metric",
        "fabricated_calibration_set_threshold_laundering",
        "receipt_replay_absence_static_asserts",
        "structural_param_smuggle_body",
    ]
    assert payload["executable_anchor_gates"] == [
        "global_project_sweep_assumption_as_evidence",
        "global_project_sweep_definitional_tautology",
        "global_project_sweep_fabricated_calibration",
        "global_project_sweep_receipt_replay_absence",
        "global_project_sweep_structural_param_smuggle",
    ]
    assert payload["executable_anchor_benign_control_passed"] is True
    assert module.PAPER_README.exists()
    assert module.PAPER_DRAFT.exists()
    assert payload["paper_boundary_files"] in {2, 4}


def test_public_adversarial_smoke_checks_front_door_language_files() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_public_language()
    checked = set(payload["checked_files"])

    assert payload["ok"] is True
    assert "README.md" in checked
    assert "CONTRIBUTING.md" in checked
    assert "SECURITY.md" in checked
    assert "pyproject.toml" in checked
    assert "CITATION.cff" in checked
    assert "docs/gaming_behavior_catalog.md" in checked
    assert "docs/concepts/architecture.md" in checked
    assert "docs/concepts/capabilities.md" in checked
    assert "docs/multi_substrate_validation.md" in checked
    assert "src/ztare/cli.py" in checked
    assert "docs/guides/cli.md" in checked
    assert "docs/guides/workflow.md" in checked
    assert "docs/guides/agent-prompts.md" in checked
    assert "load-bearing" in module.FORBIDDEN_PUBLIC_TERMS
    assert "real work" in module.FORBIDDEN_PUBLIC_TERMS
    assert "world class" in module.FORBIDDEN_PUBLIC_TERMS


def test_public_adversarial_smoke_blocks_project_specific_userland_anchors() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_userland_project_bias()
    checked = set(payload["checked_files"])

    assert payload["ok"] is True
    assert "README.md" in checked
    assert "priority_roadmap.md" in checked
    assert "docs/guides/cli.md" in checked
    assert "docs/guides/experiment_cookbook.md" in checked
    assert "examples/project_packets/README.md" in checked
    assert "src/ztare/cli.py" in checked
    assert "old_example_project_2026" in module.FORBIDDEN_USERLAND_PROJECT_TERMS
    assert "gp023_planck_sandbox" in module.FORBIDDEN_USERLAND_PROJECT_TERMS


def test_public_adversarial_smoke_keeps_first_run_reference_in_sync() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_docs_wiring()

    assert payload["ok"] is True
    assert "docs/guides/quickstart.md" in payload["checked_files"]
    assert payload["first_run_recipe"]["checked_commands"] == 9
    assert module.extract_make_target_recipe(
        "first-run:\n\t$(MAKE) hello\n\t$(MAKE) docs-check\n\nhello:\n",
        "first-run",
    ) == ["make hello", "make docs-check"]
    assert module.extract_first_run_reference_commands(
        "`make first-run` runs the full offline public path:\n\n"
        "```bash\nmake hello\nmake docs-check\n```\n"
    ) == ["make hello", "make docs-check"]


def test_public_adversarial_smoke_checks_forensic_workbench_interface_contract() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_forensic_workbench_interface_contract()

    assert payload["ok"] is True
    assert payload["checked_file"] == "docs/concepts/forensic_workbench_interface.md"
    assert payload["checked_snippets"] == len(module.REQUIRED_FORENSIC_WORKBENCH_SNIPPETS)
    assert payload["checked_cli_families"] == [
        "ztare " + " ".join(args)
        for args in module.REQUIRED_FORENSIC_WORKBENCH_CLI_FAMILIES
    ]
    assert payload["checked_make_snippets"] == 3


def test_public_adversarial_smoke_rejects_forensic_workbench_contract_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )
    doc = tmp_path / "docs/concepts/forensic_workbench_interface.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Forensic Workbench Interface\n", encoding="utf-8")
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        "\n".join([
            "synth-contract:",
            "\t$(PYTHON) -m src.ztare.synthesis.synthesize --support-contract-only",
            "\t@echo 'make synth-contract PROJECT=<project> RENDERER=decision_brief'",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "REPO", tmp_path)

    with pytest.raises(SystemExit, match="missing required contract snippets"):
        module.check_forensic_workbench_interface_contract()


def test_public_adversarial_smoke_checks_forensic_workbench_snapshot_contract() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_forensic_workbench_snapshot_contract()

    assert payload["ok"] is True
    assert payload["checked_file"] == "docs/landings/forensic_workbench_prototype.html"
    assert payload["checked_snippets"] == len(
        module.REQUIRED_FORENSIC_WORKBENCH_SNAPSHOT_SNIPPETS
    )
    assert payload["row_count"] >= 8


def test_public_adversarial_smoke_checks_forensic_workbench_react_contract() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_forensic_workbench_react_contract()

    assert payload["ok"] is True
    assert "forensic-workbench/package.json" in payload["checked_files"]
    assert "forensic-workbench/src/main.js" in payload["checked_files"]
    assert payload["checked_snippets"] == len(
        module.REQUIRED_FORENSIC_WORKBENCH_REACT_SNIPPETS
    )
    assert payload["row_count"] >= 8


def test_public_adversarial_smoke_checks_system_position_contract() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_system_position_contract()

    assert payload["ok"] is True
    assert payload["checked_file"] == "docs/concepts/system_position_and_module_map.md"
    assert payload["checked_snippets"] == len(module.REQUIRED_SYSTEM_POSITION_SNIPPETS)


def test_public_adversarial_smoke_rejects_system_position_contract_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )
    doc = tmp_path / "docs/concepts/system_position_and_module_map.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("# System Position And Module Map\n", encoding="utf-8")

    monkeypatch.setattr(module, "REPO", tmp_path)

    with pytest.raises(SystemExit, match="system-positioning doc missing"):
        module.check_system_position_contract()


def test_public_adversarial_smoke_checks_public_roadmap_contract() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_public_roadmap_contract()

    assert payload["ok"] is True
    assert payload["checked_file"] == "priority_roadmap.md"
    assert payload["checked_snippets"] == len(module.REQUIRED_PUBLIC_ROADMAP_SNIPPETS)


def test_public_adversarial_smoke_rejects_public_roadmap_contract_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )
    roadmap = tmp_path / "priority_roadmap.md"
    roadmap.write_text("# ZTARE Public Roadmap\n", encoding="utf-8")

    monkeypatch.setattr(module, "REPO", tmp_path)

    with pytest.raises(SystemExit, match="public roadmap missing"):
        module.check_public_roadmap_contract()


def test_public_adversarial_smoke_checks_researcher_workflow_cross_refs() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_researcher_workflow_cross_refs()

    assert payload["ok"] is True
    assert payload["checked_file"] == "docs/guides/experiment_cookbook.md"
    assert payload["required_snippets"] == len(
        module.REQUIRED_RESEARCHER_CROSS_REF_SNIPPETS
    )
    assert payload["forbidden_snippets"] == len(
        module.FORBIDDEN_RESEARCHER_CROSS_REF_SNIPPETS
    )


def test_public_adversarial_smoke_rejects_stale_researcher_workflow_cross_refs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )
    cookbook = tmp_path / "docs/guides/experiment_cookbook.md"
    cookbook.parent.mkdir(parents=True)
    cookbook.write_text(
        "\n".join([
            "- Full leak taxonomy + denylist construction: "
            "`docs/guides/for_researchers.md` §4 (charter contamination) "
            "and AGENTS.md hard rules",
            "- Identifiability + pre-registration protocol: "
            "`docs/guides/for_researchers.md` §4 and §6 plus AGENTS.md hard rules",
            "- Strip test procedure: `docs/guides/for_researchers.md` §2",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "REPO", tmp_path)

    with pytest.raises(SystemExit, match="stale researcher-guide cross references"):
        module.check_researcher_workflow_cross_refs()


def test_public_adversarial_smoke_checks_makefile_wiring() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_makefile_wiring()

    assert payload["ok"] is True
    assert payload["checked_makefile"] == len(module.REQUIRED_MAKE_SNIPPETS)
    assert payload["checked_forbidden_makefile"] == len(
        module.FORBIDDEN_MAKEFILE_SNIPPETS
    )


def test_public_adversarial_smoke_checks_project_intake_fixtures() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_public_project_intake_fixtures()

    assert payload["ok"] is True
    assert payload["checked"] == [
        "examples/project_packets/ready_demo_claims_intake.json",
        "ztare autoresearch trace --project demo_claims --rubric demo_claims --intake examples/project_packets/ready_demo_claims_intake.json",
        "trace run-readiness contract",
        "trace canonical intake readiness",
        "ready intake preflight-only creates loop admission receipt",
        "trace loop admission receipt",
        "trace plan_preview respects preflight and bounded-run phases",
        "ztare autoresearch run --intake malformed fixture blocks before launch",
        "malformed intake blocker uses intake labels",
        "examples/project_packets/malformed_missing_evidence_intake.json",
    ]


def test_public_adversarial_smoke_checks_autoresearch_carrier_replay_cli() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_autoresearch_carrier_replay_cli()

    assert payload["ok"] is True
    assert payload["checked"] == [
        "ztare autoresearch carrier-replay --project demo_claims --json",
        "carrier replay current-carrier readiness",
        "carrier replay legacy/current distinction",
    ]


def test_public_adversarial_smoke_checks_hello_expected_output_doc() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_hello_expected_output_doc()

    assert payload["ok"] is True
    assert payload["checked_file"] == "docs/evidence_atlas/packets/evaluator_hardening.md"
    assert payload["verdict"] == "demote_to_bounded_wording"
    assert payload["claim_allowed"] is False
    assert payload["writes_persistent_runtime_state"] is False
    assert payload["ready_intake_ok"] is True
    assert payload["ready_intake_falsifier_ok"] is True
    assert payload["malformed_intake_ok"] is False


def test_public_adversarial_smoke_checks_ops_demo_report_support_contract() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_ops_demo_report_support_contract_blocks_stale_report()

    assert payload["ok"] is True
    assert payload["status"] == "blocked"
    assert "synthesis_input_binding_unbound" in payload["status_reasons"]
    assert payload["checked"] == [
        "make synth-contract PROJECT=ops_root_cause_diagnosis_demo RENDERER=decision_brief",
        "nonzero blocked report-support exit",
        "synthesis_input_binding_unbound",
    ]


def test_public_adversarial_smoke_checks_ops_demo_kernel_health_read_models() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_ops_demo_kernel_health_read_models()

    assert payload["ok"] is True
    assert payload["overall_status"] == "attention"
    assert payload["source_health_warnings"] >= 3
    assert {
        "weak_gp233_linkage",
        "stale_trajectory_output",
        "unconsumed_surface",
    }.issubset(set(payload["source_health_issue_types"]))
    assert payload["checked"] == [
        "make autoresearch-kernel-health PROJECT=ops_root_cause_diagnosis_demo JSON=1",
        "run readiness ready",
        "provider runtime risk is advisory attention",
        "source-health warnings are non-blocking",
    ]


def test_public_adversarial_smoke_requires_intake_for_first_run_trace_examples() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    intakeless = (
        "ztare autoresearch trace --project demo_claims --rubric demo_claims --json"
    )
    intake_backed = (
        "ztare autoresearch trace --project demo_claims --rubric demo_claims "
        "--intake examples/project_packets/ready_demo_claims_intake.json --json"
    )
    historical = 'ztare autoresearch trace --project "$PROJECT" --json'

    assert module.INTAKE_AWARE_TRACE_EXAMPLE_RE.search(intakeless)
    assert module.INTAKE_AWARE_TRACE_EXAMPLE_RE.search(intake_backed)
    assert module.INTAKE_AWARE_TRACE_EXAMPLE_RE.search(historical) is None

    payload = module.check_public_command_examples()
    assert payload["ok"] is True
    assert payload["checked_intake_aware_trace_examples"] is True
    assert payload["checked_project_front_door_commands"] is True


def test_public_adversarial_smoke_rejects_nonportable_tmp_doc_examples(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )
    doc = tmp_path / "README.md"
    doc.write_text("Run `ztare project source-init demo --base /tmp/demo`.\n", encoding="utf-8")
    cli = tmp_path / "src/ztare/cli.py"
    cli.parent.mkdir(parents=True)
    cli.write_text("", encoding="utf-8")

    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module, "iter_public_markdown_paths", lambda: [doc])

    with pytest.raises(SystemExit, match="Unix-only temp paths"):
        module.check_public_command_examples()


def test_public_adversarial_smoke_extracts_last_json_object() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.extract_last_json_object(
        "command\n{\"first\": true}\ntrailer\n"
        "{\n  \"status\": \"blocked\",\n  \"nested\": {\n    \"status\": \"unbound\"\n  }\n}\n"
    )

    assert payload == {"status": "blocked", "nested": {"status": "unbound"}}


def test_public_adversarial_smoke_scans_public_examples_markdown() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    public_markdown = {
        str(path.relative_to(module.REPO))
        for path in module.iter_public_markdown_paths()
    }

    assert "examples/README.md" in public_markdown
    assert "examples/project_packets/README.md" in public_markdown
    assert "examples/substrate_packets/README.md" in public_markdown


def test_public_adversarial_smoke_checks_cli_front_door_and_completion() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_cli_front_door()

    assert payload["ok"] is True
    assert payload["checked_help_snippets"] >= 8
    assert payload["checked_forbidden_help_snippets"] >= 3
    assert payload["checked_project_help_snippets"] == len(
        module.REQUIRED_PROJECT_HELP_SNIPPETS
    )
    assert payload["checked_forbidden_project_help_snippets"] == len(
        module.FORBIDDEN_PROJECT_HELP_SNIPPETS
    )
    assert payload["checked_project_prep_ledger_help_snippets"] == len(
        module.REQUIRED_PROJECT_PREP_LEDGER_HELP_SNIPPETS
    )
    assert payload["checked_forbidden_project_prep_ledger_help_snippets"] == len(
        module.FORBIDDEN_PROJECT_PREP_LEDGER_HELP_SNIPPETS
    )
    assert payload["checked_command_contracts"] == {
        "ztare " + " ".join(args): len(snippets)
        for args, snippets in module.REQUIRED_CLI_COMMAND_CONTRACTS
    }
    assert payload["checked_completion_snippets"] == {
        "bash": len(module.REQUIRED_COMPLETION_SNIPPETS),
        "zsh": len(module.REQUIRED_COMPLETION_SNIPPETS),
        "fish": len(module.REQUIRED_COMPLETION_SNIPPETS),
    }


def test_public_adversarial_smoke_checks_cli_and_capability_doc_drift() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    cli_payload = module.check_cli_guide_command_inventory()
    capability_payload = module.check_capabilities_catalog_count()

    assert cli_payload["ok"] is True
    assert cli_payload["command_count"] >= 16
    assert cli_payload["documented_command_count"] >= cli_payload["command_count"]
    assert capability_payload["ok"] is True
    assert capability_payload["architecture_index_rows"] >= 700


def test_public_adversarial_smoke_exercises_ordinary_review_freeze_checker() -> None:
    module = load_script_module(
        "public_adversarial_smoke",
        "scripts/public/control/public_adversarial_smoke.py",
    )

    payload = module.check_ordinary_review_freeze_checker()

    assert payload["ok"] is True
    assert payload["isolated_root"] == "internal_tempdir"
    assert len(payload["checked"]) == 2
