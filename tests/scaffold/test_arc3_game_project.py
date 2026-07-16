from __future__ import annotations

import json


class FakeArc3Adapter:
    game_id = "fx00-fake"
    action_arity = 2

    def __init__(self) -> None:
        self._state = ((0,),)
        self._t = 0

    @property
    def state(self):
        return self._state

    @property
    def t(self):
        return self._t

    def reset(self):
        self._state = ((0,),)
        self._t = 0
        return self._state

    def step(self, action: int):
        self._state = ((self._state[0][0] + int(action) + 1,),)
        self._t += 1
        return self._state


def test_scaffold_game_project_writes_arc3_surfaces(tmp_path, monkeypatch):
    from ztare.scaffold import arc3_game_project as agp
    from ztare.worldmodel.adapter import episode_log_path
    from ztare.worldmodel.episode_log import EpisodeLog

    projects = tmp_path / "projects"
    rubrics = tmp_path / "rubrics"
    canonical = projects / agp.CANONICAL_ARC3
    canonical.mkdir(parents=True)
    (canonical / "gate_harness.py").write_text(
        '"""Frozen deterministic-gate harness for arc3_ls20_gov."""\n',
        encoding="utf-8",
    )
    rubrics.mkdir()
    (rubrics / f"{agp.CANONICAL_ARC3}.json").write_text(
        json.dumps({
            "rubric_id": agp.CANONICAL_ARC3,
            "evidence_carrier_kind": "transition_stream",
            "substrate_class": "interactive_environment",
            "fit_expression_grammar": "grid_dsl",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(agp, "PROJECTS", projects)
    monkeypatch.setattr(agp, "RUBRICS", rubrics)

    receipt = agp.scaffold_game_project(
        "fx00",
        project_slug="arc3_fx00_gov",
        adapter=FakeArc3Adapter(),
        holdout_actions=3,
    )

    project = projects / "arc3_fx00_gov"
    assert receipt.project == "arc3_fx00_gov"
    assert receipt.action_arity == 2
    assert receipt.holdout_rows == 3
    assert (project / "play_config.json").exists()
    assert (project / "project_charter.md").read_text().count("2 actions") == 1
    assert "arc3_fx00_gov" in (project / "gate_harness.py").read_text()
    written_rubric = json.loads((rubrics / "arc3_fx00_gov.json").read_text())
    assert written_rubric["rubric_id"] == "arc3_fx00_gov"
    assert written_rubric["evidence_carrier_kind"] == "transition_stream"
    assert len(EpisodeLog.read_jsonl(episode_log_path(project))) == 0
    assert len(EpisodeLog.read_jsonl(episode_log_path(project, 2))) == 3
    assert (project / "evidence.txt").exists()
    assert (project / "compiled_evidence_provenance.json").exists()
    assert (project / "workspace" / "arc3_scaffold_receipt.json").exists()
