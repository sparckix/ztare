from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "deploy" / "vps_run.py"


def load_module():
    spec = importlib.util.spec_from_file_location("vps_run_under_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_remote_path_defaults_are_portable_and_include_elan() -> None:
    mod = load_module()

    entries = mod.remote_path_entries(
        "$REMOTE_REPO/venv/bin:$HOME/.elan/bin:$HOME/.local/bin:/usr/bin",
        remote_repo="/srv/app",
    )

    assert entries == [
        "/srv/app/venv/bin",
        "$HOME/.elan/bin",
        "$HOME/.local/bin",
        "/usr/bin",
    ]


def test_remote_path_expr_leaves_remote_home_expansion() -> None:
    mod = load_module()

    expr = mod.remote_path_expr()

    assert "$HOME/.elan/bin" in expr
    assert "$PATH" in expr
    assert "/venv/bin" in expr


def test_remote_path_rejects_shell_metacharacters() -> None:
    mod = load_module()

    with pytest.raises(SystemExit):
        mod.remote_path_entries("/usr/bin:$(touch /tmp/bad)")


def test_structural_residual_target_rejects_unregistered_source_id(
    tmp_path, monkeypatch
) -> None:
    mod = load_module()
    monkeypatch.setattr(mod, "LOCAL_REPO", tmp_path)
    registry = tmp_path / "org/structural_anchors/registry.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        """
schema_version: 1
math_substrate:
  targets:
    - id: structural_target_a
      aliases: [target-a-alias]
    - id: structural_target_b
      aliases: [target-b-alias]
""",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc:
        mod.validate_structural_residual_target(
            "math_substrate",
            "surface_source_id",
        )
    assert "structural anchor registry" in str(exc.value)
    assert "consumes_surfaced" in str(exc.value)
    assert "structural_target_a" in str(exc.value)
    mod.validate_structural_residual_target(
        "math_substrate", "target-a-alias"
    )


def test_local_close_payload_lint_normalizes_date_and_rejects_unsynced_repo_ref(
    tmp_path, monkeypatch
) -> None:
    mod = load_module()
    monkeypatch.setattr(mod, "LOCAL_REPO", tmp_path)
    script_dir = tmp_path / "deploy"
    script_dir.mkdir()
    monkeypatch.setattr(mod, "SCRIPT_DIR", script_dir)
    (script_dir / "vps_sync_files.txt").write_text(
        "allowed/orientation.md\nallowed/stress.md\nallowed/verification.md\n",
        encoding="utf-8",
    )
    for rel in (
        "allowed/orientation.md",
        "allowed/stress.md",
        "allowed/verification.md",
        "scratch/pack.md",
    ):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rel, encoding="utf-8")

    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "f_row.txt").write_text(
        "F-ROW\nowner: codex:RD\ndate: 2099-01-01\n",
        encoding="utf-8",
    )
    (payload / "research_done.json").write_text(
        json.dumps(
            {
                "loops": [
                    {
                        "orientation_artifact": {
                            "root": "repo",
                            "path": "scratch/pack.md",
                        },
                        "stress_test_artifact": {
                            "root": "repo",
                            "path": "allowed/stress.md",
                        },
                        "verification_artifact": {
                            "root": "repo",
                            "path": "allowed/verification.md",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        mod.lint_local_close_payload(payload)
    assert "date: `2099-01-01`" in (payload / "f_row.txt").read_text(
        encoding="utf-8"
    )


def test_local_close_payload_lint_rejects_invalid_l2_move(
    tmp_path, monkeypatch, capsys
) -> None:
    mod = load_module()
    monkeypatch.setattr(mod, "LOCAL_REPO", REPO)

    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "f_row.txt").write_text(
        (
            "date: `2099-01-01`\n"
            "owner: codex:RD; consumes_surfaced: surfaced_id "
            "dispatch_ledger: label=adversarial_kill\n"
        ),
        encoding="utf-8",
    )
    (payload / "declared.json").write_text(
        json.dumps(
            {
                "l1_pattern": "swarm_dispatch",
                "l1_witness": (
                    "A bounded split was used and consolidated with specific "
                    "lanes rather than a generic solo close."
                ),
                "l2_move": "descriptive prose that is not a catalog move",
                "l2_witness": (
                    "The mathematical object and its exact supplied property "
                    "are described here with concrete evidence."
                ),
                "l3_antipattern": "scientific_amnesia",
                "l3_witness": (
                    "The prior residual ledger was checked and the next lever "
                    "was distinguished from a vocabulary alias."
                ),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc:
        mod.lint_local_close_payload(payload)

    assert exc.value.code == 2
    assert "L2 structural-language move" in capsys.readouterr().err
