from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "docs" / "internal" / "roadmap" / "release_slice_audit.py"


def load_module():
    if not SCRIPT.exists():
        pytest.skip("internal release-slice audit is not present in this checkout")
    spec = importlib.util.spec_from_file_location("release_slice_audit_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gitignore_hunk_audit_splits_demo_fixture_from_holdback(monkeypatch) -> None:
    module = load_module()
    diff = """diff --git a/.gitignore b/.gitignore
index 000000000..111111111 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1,3 +1,13 @@
+# Public demo project-intake fixture. Keep the minimal source surface tracked so
+# clean checkouts can validate `examples/project_packets/ready_demo_claims_packet.json`.
+!projects/demo_claims/
+projects/demo_claims/*
+!projects/demo_claims/raw/
+!projects/demo_claims/raw/source.md
+!projects/demo_claims/raw/source_type_map.json
+/llm-forecast-calibration-cross-corpus/
"""
    monkeypatch.setattr(module, "git_diff_for_path", lambda path: diff)

    audit = module.inspect_gitignore_hunks()

    assert audit["ok"] is True
    assert audit["partial_stage_required"] is True
    assert "!projects/demo_claims/raw/source.md" in audit["public_onramp_added_lines"]
    assert "/llm-forecast-calibration-cross-corpus/" in audit["known_holdback_added_lines"]
    assert audit["unexpected_change_lines"] == []


def test_gitignore_hunk_audit_rejects_unrecognized_lines(monkeypatch) -> None:
    module = load_module()
    diff = """diff --git a/.gitignore b/.gitignore
index 000000000..111111111 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1,3 +1,4 @@
+/unclassified-root-workspace/
"""
    monkeypatch.setattr(module, "git_diff_for_path", lambda path: diff)

    audit = module.inspect_gitignore_hunks()

    assert audit["ok"] is False
    assert audit["partial_stage_required"] is False
    assert audit["unexpected_change_lines"] == ["+/unclassified-root-workspace/"]


def test_group1_plan_marks_gitignore_partial_stage_when_hunks_are_split(monkeypatch) -> None:
    module = load_module()
    audit = {
        "partial_stage_required": True,
        "public_onramp_added_lines": ["!projects/demo_claims/raw/source.md"],
    }
    monkeypatch.setattr(module, "inspect_gitignore_hunks", lambda: audit)
    monkeypatch.setattr(module, "concepts_index_mentions_leanmill_holdback", lambda: False)
    monkeypatch.setattr(
        module,
        "inspect_group7_mechanical_risk",
        lambda paths: {"ok": True, "checked_count": 0, "mechanical_count": 0, "risky_count": 0},
    )

    payload = module.build_payload(["README.md", ".gitignore"])
    group1 = payload["release_group_plan"]["group_1_public_onramp_positioning"]

    assert group1["stage_command_is_complete"] is False
    assert group1["manual_partial_stage_required"] == [".gitignore"]
    assert group1["manual_partial_stage_lines"] == {
        ".gitignore": ["!projects/demo_claims/raw/source.md"]
    }
    assert ".gitignore" not in group1["stage_command"]
    assert ".gitignore" not in group1["stage_paths"]
    assert "Stage only the public-onramp .gitignore hunks" in group1["stage_notes"][1]
    assert "manual_partial_stage_lines" in group1["stage_notes"][2]


def test_group1_plan_marks_concepts_index_partial_stage_for_leanmill_holdback(monkeypatch) -> None:
    module = load_module()
    audit = {
        "partial_stage_required": False,
        "public_onramp_added_lines": [],
    }
    monkeypatch.setattr(module, "inspect_gitignore_hunks", lambda: audit)
    monkeypatch.setattr(module, "concepts_index_mentions_leanmill_holdback", lambda: True)
    monkeypatch.setattr(
        module,
        "inspect_group7_mechanical_risk",
        lambda paths: {"ok": True, "checked_count": 0, "mechanical_count": 0, "risky_count": 0},
    )

    payload = module.build_payload(["README.md", "docs/concepts/README.md"])
    group1 = payload["release_group_plan"]["group_1_public_onramp_positioning"]

    assert group1["stage_command_is_complete"] is False
    assert group1["manual_partial_stage_required"] == ["docs/concepts/README.md"]
    assert "leanmill_formalization_roadmap.md" in group1["manual_partial_stage_lines"]["docs/concepts/README.md"][0]
    assert "docs/concepts/README.md" in group1["paths"]
    assert "docs/concepts/README.md" not in group1["stage_paths"]
    assert "docs/concepts/README.md" not in group1["stage_command"]
    assert "LeanMill holdback" in " ".join(group1["stage_notes"])


def test_staging_checklist_marks_incomplete_group_and_keeps_holdback_guidance(monkeypatch) -> None:
    module = load_module()
    audit = {
        "partial_stage_required": True,
        "public_onramp_added_lines": ["!projects/demo_claims/raw/source.md"],
    }
    monkeypatch.setattr(module, "inspect_gitignore_hunks", lambda: audit)
    monkeypatch.setattr(module, "concepts_index_mentions_leanmill_holdback", lambda: False)
    monkeypatch.setattr(
        module,
        "inspect_group7_mechanical_risk",
        lambda paths: {"ok": True, "checked_count": 0, "mechanical_count": 0, "risky_count": 0},
    )

    payload = module.build_payload(["README.md", ".gitignore"])
    checklist = module.build_staging_checklist(payload)
    group1 = checklist["groups"][0]

    assert checklist["dry_run_only"] is True
    assert checklist["ok_to_stage_release_groups"] is True
    assert checklist["safe_to_stage_all"] is False
    assert group1["group"] == "group_1_public_onramp_positioning"
    assert group1["stage_command_is_complete"] is False
    assert group1["manual_partial_stage_required"] == [".gitignore"]
    assert "--paths-only > /tmp/ztare_group_1_public_onramp_positioning_paths.txt" in group1["path_list_command"]
    assert group1["stage_from_path_file_command"] == 'git add --pathspec-from-file="/tmp/ztare_group_1_public_onramp_positioning_paths.txt"'
    assert group1["staged_group_check_command"].endswith(
        "--staged-summary --staged-group group_1_public_onramp_positioning"
    )
    assert "Keep holdbacks unstaged" in checklist["guidance"][-1]


def test_name_status_parser_includes_both_sides_of_renames() -> None:
    module = load_module()

    paths = module.parse_name_status_line(
        "R093\tdocs/guides/operator_console.md\tdocs/guides/manual_console.md"
    )

    assert paths == [
        "docs/guides/operator_console.md",
        "docs/guides/manual_console.md",
    ]


def test_group7_mechanical_audit_accepts_public_private_path_scrub(monkeypatch) -> None:
    module = load_module()
    private_path = "research_areas/" + "private/specs/example.md"
    diff = f"""diff --git a/src/ztare/example.py b/src/ztare/example.py
index 000000000..111111111 100644
--- a/src/ztare/example.py
+++ b/src/ztare/example.py
@@ -1,7 +1,7 @@
 \"\"\"Example.

-Spec: {private_path}
+Spec: maintainer-only example spec
 \"\"\"
-from src.ztare.common.dispatch_model import dispatch_call_text
+from ztare.common.dispatch_model import dispatch_call_text
"""

    monkeypatch.setattr(module, "git_diff_for_path", lambda path: diff)

    audit = module.inspect_group7_mechanical_risk(["src/ztare/example.py"])

    assert audit["ok"] is True
    assert audit["risky_count"] == 0


def test_staged_audit_flags_holdbacks_and_unclassified_paths() -> None:
    module = load_module()

    audit = module.build_staged_audit([
        "README.md",
        "papers/cognitive-camouflage/draft.md",
        "unexpected/path.md",
    ])

    assert audit["ok"] is False
    assert audit["has_staged_paths"] is True
    assert audit["staged_path_count"] == 3
    assert audit["release_counts_by_group"]["group_1_public_onramp_positioning"] == 1
    assert audit["holdback_count"] == 1
    assert audit["holdbacks"][0]["path"] == "papers/cognitive-camouflage/draft.md"
    assert audit["unclassified_count"] == 1
    assert audit["unclassified"][0]["path"] == "unexpected/path.md"


def test_staged_audit_accepts_public_gitignore_hunk(monkeypatch) -> None:
    module = load_module()
    diff = """diff --git a/.gitignore b/.gitignore
index 000000000..111111111 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1,3 +1,8 @@
+# Public demo project-intake fixture. Keep the minimal source surface tracked so
+# clean checkouts can validate `examples/project_packets/ready_demo_claims_packet.json`.
+!projects/demo_claims/
+projects/demo_claims/*
+!projects/demo_claims/raw/source.md
"""
    monkeypatch.setattr(module, "git_cached_diff_for_path", lambda path: diff)

    audit = module.build_staged_audit(
        ["README.md", ".gitignore"],
        expected_group="group_1_public_onramp_positioning",
    )

    assert audit["ok"] is True
    assert audit["holdback_count"] == 0
    assert audit["release_counts_by_group"]["group_1_public_onramp_positioning"] == 2


def test_staged_audit_can_require_one_release_group() -> None:
    module = load_module()

    matching = module.build_staged_audit(
        ["README.md"],
        expected_group="group_1_public_onramp_positioning",
    )
    mixed = module.build_staged_audit(
        ["README.md", "scripts/public/control/action_intelligence.py"],
        expected_group="group_1_public_onramp_positioning",
    )

    assert matching["ok"] is True
    assert matching["expected_group"] == "group_1_public_onramp_positioning"
    assert matching["unexpected_release_groups"] == []
    assert matching["missing_expected_group"] is False
    assert mixed["ok"] is False
    assert mixed["unexpected_release_groups"] == [
        "group_4_agentic_reflexive_contract_hardening"
    ]


def test_repo_health_scripts_stay_in_repo_health_slice() -> None:
    module = load_module()
    expected_group = "group_6_repo_health_compatibility"

    for path in (
        "scripts/public/control/undefined_name_gate.py",
        "scripts/public/control/v32_llm_l2_classifier.py",
        "scripts/public/control/v32_route_c_replay_batch.py",
        "tests/scripts/test_undefined_name_gate.py",
    ):
        classification = module.classify_path(path)
        assert classification["class"] == "release_group"
        assert classification["group"] == expected_group


def test_git_diff_for_path_includes_staged_and_unstaged_changes(monkeypatch) -> None:
    module = load_module()
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ["git", "diff", "--cached"]:
            return SimpleNamespace(stdout="cached diff")
        return SimpleNamespace(stdout="unstaged diff")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    diff = module.git_diff_for_path("src/ztare/formal/lean_repl.py")

    assert diff == "unstaged diff\ncached diff"
    assert ["git", "diff", "--", "src/ztare/formal/lean_repl.py"] in calls
    assert ["git", "diff", "--cached", "--", "src/ztare/formal/lean_repl.py"] in calls


def test_forensic_workbench_interface_stays_in_public_onramp_slice() -> None:
    module = load_module()

    for path in (
        "docs/concepts/forensic_workbench_interface.md",
        "scripts/public/control/forensic_workbench_snapshot.py",
        "scripts/public/control/forensic_workbench_server.py",
        "forensic-workbench/src/main.js",
    ):
        classification = module.classify_path(path)
        assert classification["class"] == "release_group"
        assert classification["group"] == "group_1_public_onramp_positioning"


def test_shared_telemetry_stays_in_agentic_contract_slice() -> None:
    module = load_module()

    classification = module.classify_path("src/ztare/common/telemetry.py")

    assert classification["class"] == "release_group"
    assert classification["group"] == "group_4_agentic_reflexive_contract_hardening"


def test_manual_console_rename_stays_in_public_onramp_slice() -> None:
    module = load_module()

    for path in (
        "docs/guides/manual_console.md",
        "docs/guides/operator_console.md",
    ):
        classification = module.classify_path(path)
        assert classification["class"] == "release_group"
        assert classification["group"] == "group_1_public_onramp_positioning"


def test_leanmill_output_roots_remain_holdbacks() -> None:
    module = load_module()

    for path in (
        "analytics/public/leanmill/witness_transport_separation/README.md",
        "analytics/public/leanmill/witness_transport_separation/factoring_separation_run.json",
        "formalizations/finance/ftap_easy/FtapEasy.lean",
        "projects/leanmill_experiments/public/witness_vs_bare_controlled.py",
    ):
        classification = module.classify_path(path)
        assert classification["class"] == "holdback"
        assert classification["group"] is None


def test_internal_writing_style_stays_internal_planning() -> None:
    module = load_module()

    classification = module.classify_path("internal/writing-style/anti_neuralese_guide.md")

    assert classification["class"] == "internal_planning"
    assert classification["group"] is None
