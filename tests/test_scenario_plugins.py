from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from ztare.scenarios import registry
from ztare.scenarios.config import DeliverableSpec, ScenarioConfig
from ztare.scenarios.declarative import compose_declarative
from ztare.scenarios.firewall import provenance_firewall, render
from ztare.scenarios.governed_types import Deliverable, GovernedEdge, GovernedElement, GovernedState
from ztare.scenarios.rice import load_rice_inputs, rice_scores, save_rice_inputs


def test_workbench_panel_refs_target_supported_host_slots() -> None:
    config = ScenarioConfig(workbench_panels=["results:governed-rice"])
    assert config.workbench_panels == ["results:governed-rice"]

    with pytest.raises(ValidationError):
        ScenarioConfig(workbench_panels=["governed-rice"])
    with pytest.raises(ValidationError):
        ScenarioConfig(workbench_panels=["sidebar:governed-rice"])


def test_declarative_deliverable_is_governed_and_keeps_presentation_metadata() -> None:
    state = GovernedState(
        [
            GovernedElement("t", "thesis", "Ship initiative A"),
            GovernedElement("e", "evidence", "Reach 1,000; impact 2."),
            GovernedElement("f", "falsifier", "If retention falls, stop."),
        ],
        [GovernedEdge("e", "SUPPORTS", "t")],
    )
    spec = DeliverableSpec(
        name="handoff",
        label="Decision handoff",
        audience="Leadership",
        description="A bounded handoff.",
        presentation_brief="Lead with the decision boundary.",
        sections=[
            {"label": "Decision", "kinds": ["thesis", "claim"]},
            {"label": "Backing", "kinds": ["evidence"]},
            {"label": "Revisit if", "kinds": ["falsifier"]},
        ],
    )
    deliverable = compose_declarative(spec, state)
    assert provenance_firewall([deliverable], state, ["handoff"]).ok
    text = render(deliverable, state)
    assert "# Decision handoff" in text
    assert "_For: Leadership_" in text
    assert "Renderer guidance" not in text
    assert "Lead with the decision boundary." not in text
    assert text.count("## Decision") == 1
    assert text.count("## Backing") == 1
    assert "governed-edge:e-SUPPORTS-t" in text


def test_declarative_spec_rejects_unknown_governed_kind() -> None:
    with pytest.raises(ValidationError, match="unknown governed deliverable kind"):
        DeliverableSpec(name="handoff", sections=[{"label": "Bad", "kinds": ["invented"]}])


def test_editable_document_design_owns_a_same_named_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """A visible document design must not be silently ignored by a provider template."""
    from ztare.scenarios.firewall import _TEMPLATES
    from ztare.scenarios.production import deliverable_gaps

    state = GovernedState([GovernedElement("t", "thesis", "Make the call")])
    spec = DeliverableSpec(name="handoff", sections=[{"label": "Decision", "kinds": ["thesis"]}])
    monkeypatch.setitem(_TEMPLATES, "handoff", lambda _state: Deliverable("handoff"))

    result = deliverable_gaps(state, ["handoff"], specs=[spec])

    assert result["deliverables"][0]["status"] == "composable"
    assert result["deliverables"][0]["slots"] == 1


def test_external_capability_reload_removes_deleted_plugins_and_reports_collisions(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_a = tmp_path / "a_solver.py"
    plugin_b = tmp_path / "b_solver.py"
    plugin_a.write_text(
        "from ztare.scenarios.registry import capability\n"
        "@capability('solver', 'test_reload_solver')\n"
        "class A:\n"
        "    name = 'test_reload_solver'\n"
        "    def solve(self, problem): return {'provider': 'a'}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ZTARE_SCENARIO_PLUGINS", str(tmp_path))
    registry.reload()
    assert registry.get("solver", "test_reload_solver").solve({}) == {"provider": "a"}

    plugin_b.write_text(
        "from ztare.scenarios.registry import capability\n"
        "@capability('solver', 'test_reload_solver')\n"
        "class B:\n"
        "    name = 'test_reload_solver'\n"
        "    def solve(self, problem): return {'provider': 'b'}\n",
        encoding="utf-8",
    )
    registry.reload()
    assert registry.get("solver", "test_reload_solver").solve({}) == {"provider": "a"}
    assert any("capability collision" in row["error"] for row in registry.diagnostics()["load_errors"])

    plugin_a.unlink()
    plugin_b.unlink()
    registry.reload()
    assert registry.get("solver", "test_reload_solver") is None


def _pm_state() -> GovernedState:
    return GovernedState(
        [
            GovernedElement("thesis", "thesis", "Prioritize the roadmap"),
            GovernedElement("claim:a", "claim", "Ship initiative A"),
            GovernedElement("ev:a", "evidence", "Reach 1,000; impact 2; effort 4 weeks."),
        ],
        [
            GovernedEdge("ev:a", "SUPPORTS", "claim:a", "W2"),
            GovernedEdge("claim:a", "SUPPORTS", "thesis", "W2"),
        ],
    )


def test_rice_inputs_are_atomic_and_warrants_are_derived(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import ztare.scenarios.adapters as adapters

    monkeypatch.setattr(adapters, "governed_state_from_research_map", lambda *_args: _pm_state())
    factors = {
        "reach": {"low": 800, "value": 1000, "high": 1200, "ref": "ev:a", "warrant": "W0"},
        "impact": {"low": 1.5, "value": 2, "high": 2.5, "ref": "ev:a"},
        "effort": {"low": 3, "value": 4, "high": 6, "ref": "ev:a", "unit": "weeks"},
    }
    saved = save_rice_inputs("demo", tmp_path, "claim:a", factors)
    assert "warrant" not in saved["reach"]
    assert load_rice_inputs("demo", tmp_path)["claim:a"] == saved

    row = rice_scores(_pm_state(), {"claim:a": saved})[0]
    assert row["reach"]["tier"] == "cited"
    assert row["score_low"] < row["score"] < row["score_high"]

    path = tmp_path / "projects" / "demo" / "workspace" / "rice_inputs.json"
    before = path.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="low <= likely <= high"):
        save_rice_inputs("demo", tmp_path, "claim:a", {
            **factors,
            "reach": {"low": 1200, "value": 1000, "high": 800, "ref": "ev:a"},
        })
    assert path.read_text(encoding="utf-8") == before
    assert json.loads(before)["claim:a"]["reach"]["value"] == 1000


def test_rice_rejects_stale_evidence_refs(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import ztare.scenarios.adapters as adapters

    monkeypatch.setattr(adapters, "governed_state_from_research_map", lambda *_args: _pm_state())
    with pytest.raises(ValueError, match="not governed evidence"):
        save_rice_inputs("demo", tmp_path, "claim:a", {
            "reach": {"low": 1, "value": 1, "high": 1, "ref": "ev:deleted"},
            "impact": {"low": 1, "value": 1, "high": 1},
            "effort": {"low": 1, "value": 1, "high": 1},
        })
