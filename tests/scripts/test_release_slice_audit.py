from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "docs" / "internal" / "roadmap" / "release_slice_audit.py"


def load_module():
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


def test_forensic_workbench_interface_stays_in_public_onramp_slice() -> None:
    module = load_module()

    classification = module.classify_path("docs/concepts/forensic_workbench_interface.md")

    assert classification["class"] == "release_group"
    assert classification["group"] == "group_1_public_onramp_positioning"


def test_leanmill_output_roots_remain_holdbacks() -> None:
    module = load_module()

    for path in (
        "analytics/public/leanmill/witness_transport_separation/README.md",
        "analytics/public/leanmill/witness_transport_separation/factoring_separation_run.json",
        "projects/leanmill_experiments/public/witness_vs_bare_controlled.py",
    ):
        classification = module.classify_path(path)
        assert classification["class"] == "holdback"
        assert classification["group"] is None
