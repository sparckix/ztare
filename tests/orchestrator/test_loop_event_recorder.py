from __future__ import annotations

import json

from ztare.orchestrator.loop_event_recorder import event_label_for, record_loop_event


class _Profile:
    name = "newton_discovery"
    modules = ("category_switch", "fixed_point_scan")


def test_loop_event_preserves_legacy_event_id_and_adds_operator_label(tmp_path):
    record_loop_event(
        tmp_path,
        event_type="topological_pivot_profile_injected",
        iteration_index=2,
        stagnation_count=2,
        falsification_mode="bounded_discriminator",
        is_v4_project=False,
        pivot_profile=_Profile(),
        pending_loop_action="stagnation_pivot",
        mutator_model_id="gemini",
        judge_model_id="gemini",
        run_id="RUN-1",
        project_name="demo",
    )

    latest = json.loads((tmp_path / "latest_loop_event.json").read_text())
    rows = [
        json.loads(line)
        for line in (tmp_path / "loop_events.jsonl").read_text().splitlines()
        if line.strip()
    ]

    assert latest["event_type"] == "topological_pivot_profile_injected"
    assert latest["event_label"] == "structural_pivot_profile_injected"
    assert rows[-1]["event_label"] == "structural_pivot_profile_injected"
    assert latest["pivot_profile"] == "newton_discovery"
    assert latest["pivot_modules"] == ["category_switch", "fixed_point_scan"]


def test_event_label_falls_back_to_unknown_event_type():
    assert event_label_for("custom_event") == "custom_event"
