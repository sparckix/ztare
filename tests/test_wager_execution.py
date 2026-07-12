from __future__ import annotations

from ztare.scenarios import adapters
from ztare.scenarios import wager as wager_module
from ztare.scenarios.governed_types import GovernedElement, GovernedState
from ztare.scenarios.wager import GraphEdit, Outcome, Wager, execute_project_outcome, preview_project_outcome, to_payload


def _registered_wager() -> Wager:
    return Wager(
        id="latency_audit",
        claim_ref="thesis",
        test="Run the latency audit",
        outcomes=(
            Outcome("confirmed", (
                GraphEdit("add_evidence", "ev_confirmed", text="The audit confirmed the claim."),
                GraphEdit("support", "thesis", source="ev_confirmed", warrant="W2"),
            ), label="The audit confirms the claim"),
            Outcome("refuted", (
                GraphEdit("add_evidence", "ev_refuted", text="The audit refuted the claim."),
                GraphEdit("attack", "thesis", source="ev_refuted", relation="CONTRADICTS", warrant="W2"),
            ), label="The audit finds a material gap"),
        ),
        exhaustive=True,
        lifecycle="open",
    )


def test_project_outcome_preview_then_execute(monkeypatch, tmp_path):
    state = GovernedState([GovernedElement("thesis", "thesis", "Latency falls under bounded load.")], [])
    stored = [to_payload(_registered_wager())]
    saved = []
    appended = []

    monkeypatch.setattr(adapters, "governed_state_from_research_map", lambda _project, _root: state)
    monkeypatch.setattr(adapters, "append_governed_overlay",
                        lambda project, root, elements, edges: appended.append((project, root, elements, edges)))
    monkeypatch.setattr(wager_module, "load_wagers", lambda _project: list(stored))
    monkeypatch.setattr(wager_module, "save_wagers", lambda _project, payloads: saved.extend(payloads))

    preview = preview_project_outcome("demo", "latency_audit", "confirmed", tmp_path)

    assert preview["status"] == "needs_confirmation"
    assert preview["outcome"]["label"] == "The audit confirms the claim"
    assert preview["applied"] == {"evidence": 1, "edges": 1}
    assert preview["decision_delta"]["decision_changed"] is True
    assert appended == []
    assert saved == []

    receipt = execute_project_outcome("demo", "latency_audit", "confirmed", tmp_path)

    assert receipt["status"] == "executed"
    assert receipt["wager"]["resolved_outcome"] == "confirmed"
    assert receipt["decision_delta"] == preview["decision_delta"]
    assert len(appended) == 1
    assert appended[0][2][0]["id"] == "ev_confirmed"
    assert appended[0][3][0]["kind"] == "SUPPORTS"
    assert saved[0]["lifecycle"] == "executed"
    assert saved[0]["resolved_outcome"] == "confirmed"
