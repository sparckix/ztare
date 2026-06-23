from __future__ import annotations

import json
from pathlib import Path

import pytest

from ztare.scaffold.substrate_walkthrough import (
    custom_walkthrough,
    default_expected_command,
    demo_walkthrough,
    main,
    ops_demo_walkthrough,
)


class _Args:
    demo = False
    project = "demo_walkthrough"
    rubric = "demo_walkthrough"
    task = "test whether the bounded claim has enough evidence"
    bounded_claim = "the bounded claim has enough evidence for review"
    next_falsifier = "remove the evidence file and validation must fail"
    expected_command = None
    enqueue = False
    queue_dir = None
    notes = None
    json = False

    def __init__(self, root: Path) -> None:
        self.source_ref = [str(root / "source.md")]
        self.evidence_ref = [str(root / "evidence.json")]
        self.non_claim = ["not a full reproduction"]
        self.packet_out = str(root / "packet.json")


def test_demo_walkthrough_validates_ready_and_malformed_fixtures() -> None:
    report = demo_walkthrough()

    assert report["schema"] == "ztare-project-walkthrough-v1"
    assert report["mode"] == "demo"
    assert report["writes"] == []
    assert report["steps"][0]["name"] == "validate_ready_packet"
    assert report["steps"][0]["canonical_name"] == "validate_ready_intake"
    assert report["steps"][0]["ok"] is True
    assert report["steps"][0]["command"].startswith("ztare project intake validate")
    assert report["steps"][1]["name"] == "validate_malformed_packet"
    assert report["steps"][1]["canonical_name"] == "validate_malformed_intake"
    assert report["steps"][1]["ok"] is True
    assert report["next_command"].startswith("ztare project walkthrough")


def test_ops_demo_walkthrough_points_at_ready_operational_diagnosis_fixture() -> None:
    report = ops_demo_walkthrough()

    assert report["mode"] == "ops_demo"
    assert report["ok"] is True
    assert report["writes"] == []
    assert report["project"] == "ops_root_cause_diagnosis_demo"
    assert report["command_plan"][2]["phase"] == "in_loop_gate"
    assert report["command_plan"][2]["ready"] is True
    assert any("autoresearch trace" in command for command in report["next_commands"])


def test_custom_walkthrough_writes_and_validates_packet(tmp_path: Path) -> None:
    (tmp_path / "source.md").write_text("source\n", encoding="utf-8")
    (tmp_path / "evidence.json").write_text("{}\n", encoding="utf-8")

    report = custom_walkthrough(_Args(tmp_path))

    packet_path = tmp_path / "packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert "packet" not in report
    assert report["intake"]["intake_id"].startswith("pp_")
    assert report["intake"]["legacy_receipt_surface"] == "project_packet"
    assert str(packet_path) in report["writes"]
    assert packet["project"] == "demo_walkthrough"
    assert packet["expected_command"] == default_expected_command(
        "demo_walkthrough",
        "demo_walkthrough",
        "test whether the bounded claim has enough evidence",
    )
    assert report["command_plan"][0]["phase"] == "source_and_evidence_prep"
    assert report["command_plan"][0]["work_mode"] == "pre_kernel_project_prep"
    assert report["command_plan"][0]["ready"] is False
    assert report["command_plan"][1]["phase"] == "read_only_trace"
    assert report["command_plan"][1]["ready"] is True
    assert "inspect intake" in report["command_plan"][1]["purpose"]
    assert report["command_plan"][2]["phase"] == "in_loop_gate"
    assert report["command_plan"][2]["ready"] is False
    assert "after the intake" in report["command_plan"][2]["purpose"]
    assert report["command_plan"][2]["commands"] == [packet["expected_command"]]
    assert report["next_commands"][-1] == packet["expected_command"]


def test_custom_walkthrough_enqueue_requires_source_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "source.md").write_text("source\n", encoding="utf-8")
    (tmp_path / "evidence.json").write_text("{}\n", encoding="utf-8")
    args = _Args(tmp_path)
    args.enqueue = True
    args.queue_dir = str(tmp_path / "queue")

    report = custom_walkthrough(args)

    assert report["ok"] is False
    assert "refusing to enqueue an intake that does not validate" in report["errors"]
    assert "packet" not in report
    validation = report["intake"]["validation"]
    assert any(error.startswith("source_preflight:") for error in validation["errors"])
    assert not (tmp_path / "queue" / "pending.jsonl").exists()


def test_custom_walkthrough_enqueue_uses_strict_packet_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    raw = tmp_path / "projects" / "demo_walkthrough" / "raw"
    raw.mkdir(parents=True)
    (raw / "source.md").write_text("Primary source text.\n", encoding="utf-8")
    (raw / "source_type_map.json").write_text(
        json.dumps({"source.md": "source_evidence"}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "source.md").write_text("source\n", encoding="utf-8")
    (tmp_path / "evidence.json").write_text("{}\n", encoding="utf-8")
    args = _Args(tmp_path)
    args.enqueue = True
    args.queue_dir = str(tmp_path / "queue")

    report = custom_walkthrough(args)

    assert report["ok"] is True
    assert report["queued"]["kind"] == "project_intake"
    assert report["queued"]["project"] == "demo_walkthrough"
    assert report["command_plan"][0]["ready"] is True
    assert report["command_plan"][1]["ready"] is True
    assert report["command_plan"][2]["ready"] is True
    assert report["queued"]["readiness_criteria"] == [
        "intake_validates",
        "source_refs_present",
        "evidence_refs_present",
        "non_claims_present",
        "next_falsifier_present",
    ]
    assert (tmp_path / "queue" / "pending.jsonl").exists()


def test_walkthrough_no_args_runs_demo(capsys) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "ZTARE project walkthrough" in out
    assert "validate_ready_intake: ok" in out
    assert "source-preflight: ready_for_evidence_prepare (1 source evidence, 0 untyped)" in out
    assert "validate_malformed_intake: ok" in out
