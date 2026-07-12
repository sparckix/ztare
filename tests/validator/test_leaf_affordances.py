from __future__ import annotations

import json
import sys
from pathlib import Path


class _Resp:
    def __init__(self, text: str):
        self.text = text


def test_leaf_prompt_exposes_menu_and_scratchpad(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test_thesis.py", "--project", "demo", "--judge_model", "gpt4o", "--mutator_model", "gpt4o"])
    from ztare.validator import test_thesis as tt

    monkeypatch.setattr(tt, "LEAF_SCRATCHPAD_PATH", str(tmp_path / "leaf_scratchpad.md"))
    monkeypatch.setattr(tt, "LEAF_FRICTION_LEDGER_PATH", str(tmp_path / "leaf_friction.jsonl"))
    prompt = tt._render_leaf_mutator_prompt(
        thesis_text="THESIS",
        evidence_text="EVIDENCE",
        scratchpad_text="carry me verbatim",
        query_rounds_left=2,
    )
    assert "continue(query)" in prompt
    assert "commit(candidate)" in prompt
    assert "stuck(diagnosis, friction)" in prompt
    assert "carry me verbatim" in prompt
    assert "thesis_excerpt" in prompt
    assert "Python carrier is sovereign" in prompt
    assert "Registered tools are conveniences" in prompt
    assert "Remaining query budget: 2" in prompt
    assert "LOWERABILITY_BLOCKED" not in prompt


def test_run_specialized_attacker_uses_queries_and_persists_scratchpad(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test_thesis.py", "--project", "demo", "--judge_model", "gpt4o", "--mutator_model", "gpt4o"])
    from ztare.validator import test_thesis as tt

    monkeypatch.setattr(tt, "LEAF_SCRATCHPAD_PATH", str(tmp_path / "leaf_scratchpad.md"))
    monkeypatch.setattr(tt, "LEAF_FRICTION_LEDGER_PATH", str(tmp_path / "leaf_friction.jsonl"))
    monkeypatch.setattr(tt, "test_code_content", "print('ok')")
    monkeypatch.setattr(tt.args, "project", "demo")
    monkeypatch.setattr(tt.args, "use_primitives", False)
    monkeypatch.setattr(tt, "JUDGE_PROVIDER_FAMILY", "openai")
    calls = iter([
        _Resp(json.dumps({"queries": [{"name": "thesis_excerpt"}], "scratchpad": "seed"})),
        _Resp(json.dumps({"commit": {"candidate": "done"}, "scratchpad": "seed"})),
    ])
    monkeypatch.setattr(tt, "safe_generate", lambda *a, **k: next(calls))

    out = tt.run_specialized_attacker("thesis text", "evidence text", {"role": "mutator", "focus_area": "focus", "persona": "persona"})
    assert '"candidate": "done"' in out
    assert Path(tt.LEAF_SCRATCHPAD_PATH).read_text(encoding="utf-8") == "seed"
    assert not Path(tt.LEAF_FRICTION_LEDGER_PATH).exists()


def test_run_specialized_attacker_records_stuck_friction(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test_thesis.py", "--project", "demo", "--judge_model", "gpt4o", "--mutator_model", "gpt4o"])
    from ztare.validator import test_thesis as tt

    monkeypatch.setattr(tt, "LEAF_SCRATCHPAD_PATH", str(tmp_path / "leaf_scratchpad.md"))
    monkeypatch.setattr(tt, "LEAF_FRICTION_LEDGER_PATH", str(tmp_path / "leaf_friction.jsonl"))
    monkeypatch.setattr(tt.args, "project", "demo")
    monkeypatch.setattr(tt.args, "use_primitives", False)
    monkeypatch.setattr(tt, "JUDGE_PROVIDER_FAMILY", "openai")
    monkeypatch.setattr(
        tt,
        "safe_generate",
        lambda *a, **k: _Resp(json.dumps({
            "stuck": {"diagnosis": "need query menu", "friction": "no query affordance"},
            "scratchpad": "remain verbatim",
        })),
    )

    out = tt.run_specialized_attacker("thesis text", "evidence text", {"role": "mutator", "focus_area": "focus", "persona": "persona"})
    assert "no query affordance" in out
    rows = [json.loads(line) for line in Path(tt.LEAF_FRICTION_LEDGER_PATH).read_text(encoding="utf-8").splitlines()]
    assert rows[0]["friction"] == "no query affordance"
    assert rows[0]["diagnosis"] == "need query menu"


def test_recurring_leaf_friction_detector(tmp_path):
    from ztare.worldmodel.machinery_contradictions import recurring_leaf_friction

    ledger = tmp_path / "leaf_friction.jsonl"
    ledger.write_text(
        "\n".join([
            json.dumps({"friction": "no query affordance", "diagnosis": "need query menu", "outcome": "stuck"}),
            json.dumps({"friction": "no query affordance", "diagnosis": "need query menu", "outcome": "stuck"}),
            json.dumps({"friction": "missing scratchpad carry-over", "diagnosis": "state lost", "outcome": "stuck"}),
        ]),
        encoding="utf-8",
    )
    cards = recurring_leaf_friction(ledger, min_count=2)
    assert cards and cards[0]["failure_family"] == "leaf-friction:recurring:stuck-exits"
    assert cards[0]["spatial_footprint"]["top_friction"] == "no query affordance"


def test_proposal_only_turn_persists_leaf_proposal_without_completion(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test_thesis.py", "--project", "demo", "--judge_model", "gpt4o", "--mutator_model", "gpt4o"])
    from ztare.validator import test_thesis as tt

    monkeypatch.setattr(tt, "LEAF_SCRATCHPAD_PATH", str(tmp_path / "leaf_scratchpad.md"))
    monkeypatch.setattr(tt, "LEAF_FRICTION_LEDGER_PATH", str(tmp_path / "leaf_friction.jsonl"))
    monkeypatch.setattr(tt, "LEAF_PROPOSALS_PATH", str(tmp_path / "leaf_proposals.jsonl"))
    monkeypatch.setattr(tt, "LEAF_PROPOSAL_DIGEST_PATH", str(tmp_path / "leaf_proposals_digest.json"))
    monkeypatch.setattr(tt.args, "project", "demo")
    monkeypatch.setattr(tt.args, "use_primitives", False)
    monkeypatch.setattr(tt, "JUDGE_PROVIDER_FAMILY", "openai")
    monkeypatch.setattr(tt, "safe_generate", lambda *a, **k: _Resp(json.dumps({
        "improvement_proposal": {
            "observed_friction_refs": ["workspace/leaf_friction.jsonl#1"],
            "proposed_change": "add query affordance",
            "expected_number_moved": {"interventions": -1},
            "certifier_touched": False,
        },
        "scratchpad": "carry forward",
    })))

    out = tt.run_specialized_attacker("thesis text", "evidence text", {"role": "mutator", "focus_area": "focus", "persona": "persona"})
    assert "proposal_only" in out
    assert "completed science turn" not in out
    rows = [json.loads(line) for line in Path(tt.LEAF_PROPOSALS_PATH).read_text(encoding="utf-8").splitlines()]
    assert rows[0]["proposal"]["proposed_change"] == "add query affordance"
    assert rows[0]["outcome"] == "proposal_only"
