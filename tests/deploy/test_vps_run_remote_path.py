from __future__ import annotations

import importlib.util
import json
import os
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


def test_remote_exports_declare_host_process_boundary() -> None:
    mod = load_module()

    exports = mod.remote_exports()

    assert "ZTARE_CODEX_NESTED_SANDBOX=0" in exports


def test_posttick_forwards_formal_artifact_flags(monkeypatch) -> None:
    mod = load_module()
    remote = []
    monkeypatch.setattr(
        mod,
        "remote_cmd",
        lambda cmd, **kwargs: remote.append((cmd, kwargs)),
    )

    mod.action_posttick([
        "tick-a",
        "forecast-a",
        "substrate-a",
        "Frozen goal.",
        "codex:RD",
        "research_areas/result.md",
        "--decision-changed",
        "--thesis-path",
        "ztare_proofs/ZtareProofs/Result.lean",
        "--project-slug",
        "axiompack_result",
    ])

    assert remote == [(
        [
            "python3",
            "scripts/public/control/posttick_runner.py",
            "--tick-id",
            "tick-a",
            "--contract-id",
            "forecast-a",
            "--substrate",
            "substrate-a",
            "--owner",
            "codex:RD",
            "--goal",
            "Frozen goal.",
            "--artifact-path",
            "research_areas/result.md",
            "--thesis-path",
            "ztare_proofs/ZtareProofs/Result.lean",
            "--project-slug",
            "axiompack_result",
            "--decision-changed",
        ],
        {"owner": "codex:RD", "membrane": True},
    )]


def test_remote_path_rejects_shell_metacharacters() -> None:
    mod = load_module()

    with pytest.raises(SystemExit):
        mod.remote_path_entries("/usr/bin:$(touch /tmp/bad)")


def test_vps_transport_reuses_a_scoped_ssh_control_socket(tmp_path, monkeypatch) -> None:
    mod = load_module()
    key = tmp_path / "key"
    key.write_text("test", encoding="utf-8")
    monkeypatch.setattr(mod, "VPS", "test-host")
    monkeypatch.setattr(mod, "KEY", key)

    ssh = mod.ssh_base()
    scp = mod.scp_base()

    assert "ControlMaster=auto" in ssh and "ControlPersist=300" in ssh
    assert "ControlMaster=auto" in scp and "ControlPersist=300" in scp
    expected_prefix = f"ControlPath=/tmp/ztare-vps-{os.getuid()}-{os.getpid()}-"
    assert any(value.startswith(expected_prefix) for value in ssh)
    assert next(value for value in ssh if value.startswith("ControlPath=")) == next(
        value for value in scp if value.startswith("ControlPath=")
    )


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


def test_campaign_input_paths_follow_declared_blueprint_and_context(
    tmp_path, monkeypatch
) -> None:
    mod = load_module()
    monkeypatch.setattr(mod, "LOCAL_REPO", tmp_path)
    campaign_dir = tmp_path / "research_areas/pre_registrations/campaign_a"
    campaign_dir.mkdir(parents=True)
    campaign = campaign_dir / "campaign.md"
    campaign.write_text(
        """---
schema: leanmill.campaign.v1
lane: axiompack
typed_blueprint: typed_blueprint.json
frozen_context_ref:
  path: research_areas/pre_registrations/campaign_a/context.json
predecessor_synthesis_ref:
  path: research_areas/pre_registrations/campaign_a/predecessor.json
evidence_refs:
  - research_areas/pre_registrations/campaign_a/source.json
  - research_areas/pre_registrations/campaign_a/control.json
---
Explore.
""",
        encoding="utf-8",
    )

    paths = mod._campaign_input_paths(
        "research_areas/pre_registrations/campaign_a/campaign.md"
    )

    assert paths == [
        "research_areas/pre_registrations/campaign_a/campaign.md",
        "research_areas/pre_registrations/campaign_a/typed_blueprint.json",
        "research_areas/pre_registrations/campaign_a/context.json",
        "research_areas/pre_registrations/campaign_a/predecessor.json",
        "research_areas/pre_registrations/campaign_a/source.json",
        "research_areas/pre_registrations/campaign_a/control.json",
    ]


def test_campaign_manifest_is_authority_for_dynamic_evidence_sync(
    monkeypatch, capsys
):
    mod = load_module()
    declared = ["campaign.md", "research_areas/evidence.json"]
    synced = []
    monkeypatch.setattr(mod, "is_sync_allowlisted", lambda path: path == "campaign.md")
    monkeypatch.setattr(mod, "_campaign_input_paths", lambda _path: declared)
    monkeypatch.setattr(
        mod,
        "_sync_repo_file",
        lambda path, *, receipt_label: synced.append((path, receipt_label)),
    )

    assert mod.sync_campaign_inputs("campaign.md") == declared
    assert synced == [
        ("campaign.md", "sync-campaign-input"),
        ("research_areas/evidence.json", "sync-campaign-input"),
    ]

    with pytest.raises(SystemExit):
        mod.sync_campaign_inputs("unreviewed.md")
    assert "campaign manifest is not allowlisted" in capsys.readouterr().err


def test_leanmill_preflight_syncs_declared_inputs_then_uses_remote_cli(
    monkeypatch
) -> None:
    mod = load_module()
    declared = ["campaign.md", "typed.json", "context.json"]
    synced = []
    remote = []
    monkeypatch.setattr(
        mod,
        "sync_campaign_inputs",
        lambda _path: synced.extend(declared) or declared,
    )
    monkeypatch.setattr(mod, "remote_cmd", remote.append)

    mod.action_leanmill_preflight(["campaign.md"])

    assert synced == declared
    assert remote == [[
        "./venv/bin/python",
        "-m",
        "ztare.leanmill.cli",
        "preflight",
        "campaign.md",
    ]]


def test_detached_campaign_uses_user_systemd_without_waiting_for_child(
    monkeypatch, capsys
) -> None:
    mod = load_module()
    synced = []
    remote = []
    remote_scripts = []
    monkeypatch.setattr(
        mod,
        "sync_campaign_inputs",
        lambda _path: synced.extend(["campaign.md", "typed.json"])
        or ["campaign.md", "typed.json"],
    )
    monkeypatch.setattr(mod, "remote_cmd", remote.append)
    monkeypatch.setattr(
        mod,
        "remote_shell",
        lambda script, **_kwargs: remote_scripts.append(script) or "",
    )
    monkeypatch.setattr(mod, "REMOTE_REPO", "/home/ztare/repo")
    monkeypatch.setattr(
        mod,
        "_campaign_input_paths",
        lambda _path: ["campaign.md", "typed.json"],
    )
    monkeypatch.setattr(
        mod, "_campaign_metadata", lambda _path: {"typed_blueprint": "typed.json"}
    )

    mod.action_leanmill_campaign(
        ["campaign.md", "/tmp/axiompack-smoke", "--detach"]
    )

    assert synced == ["campaign.md", "typed.json"]
    assert remote == []
    assert len(remote_scripts) == 1
    script = remote_scripts[0]
    assert "systemd-run --user" in script
    assert "--collect" in script
    assert "--working-directory=/home/ztare/repo" in script
    assert "setsid" not in script
    assert json.loads(capsys.readouterr().out)["status"] == "launched"


def test_detached_verification_survives_ssh_control_exit(monkeypatch, capsys) -> None:
    mod = load_module()
    remote_scripts = []
    monkeypatch.setattr(
        mod,
        "remote_shell",
        lambda script, **_kwargs: remote_scripts.append(script) or "",
    )

    mod.action_leanmill_verify([
        "/tmp/attempt-1", "--with-isabelle", "--detach",
    ])

    assert len(remote_scripts) == 1
    assert "systemd-run --user" in remote_scripts[0]
    assert "ztare.leanmill.cli verify /tmp/attempt-1 --with-isabelle" in remote_scripts[0]
    launch = json.loads(capsys.readouterr().out)
    assert launch["schema"] == "leanmill.campaign_verification_launch.v1"
    assert launch["status"] == "launched"


def test_named_resume_drives_continuously_unless_one_step_is_explicit(
    monkeypatch, capsys
) -> None:
    mod = load_module()
    remote_scripts = []
    monkeypatch.setattr(
        mod,
        "remote_shell",
        lambda script, **_kwargs: remote_scripts.append(script) or "",
    )

    mod.action_leanmill_resume(["/tmp/attempt-1", "--detach"])

    assert len(remote_scripts) == 2
    assert "ztare.leanmill.resume_runtime_preflight" in remote_scripts[0]
    assert (
        "ztare.leanmill.cli resume /tmp/attempt-1 --continuous"
        in remote_scripts[1]
    )
    launch = json.loads(capsys.readouterr().out)
    assert launch["schema"] == "leanmill.campaign_resume_launch.v1"

    calls = []
    monkeypatch.setattr(
        mod,
        "remote_cmd",
        lambda argv, **_kwargs: calls.append(argv) or "",
    )
    mod.action_leanmill_resume(["/tmp/attempt-1", "--one-step"])
    assert calls[-1] == [
        "./venv/bin/python",
        "-m",
        "ztare.leanmill.cli",
        "resume",
        "/tmp/attempt-1",
    ]

    calls.clear()
    mod.action_leanmill_resume([
        "/tmp/attempt-1",
        "--one-step",
        "--authority-ref",
        "user:continue-maximally:test",
    ])
    assert calls[-1] == [
        "./venv/bin/python",
        "-m",
        "ztare.leanmill.cli",
        "resume",
        "/tmp/attempt-1",
        "--authority-ref",
        "user:continue-maximally:test",
    ]


def test_ratify_existing_is_provider_free_named_vps_action(monkeypatch) -> None:
    mod = load_module()
    synced: list[str] = []
    built: list[list[str]] = []
    remote: list[list[str]] = []
    monkeypatch.setattr(
        mod,
        "lean_import_source_closure",
        lambda _path: [
            "ztare_proofs/ZtareProofs/Dependency.lean",
            "ztare_proofs/ZtareProofs/Example.lean",
        ],
    )
    monkeypatch.setattr(mod, "sync_one_allowlisted", synced.append)
    monkeypatch.setattr(mod, "action_lean_build", lambda args: built.append(args))
    monkeypatch.setattr(mod, "remote_cmd", lambda argv: remote.append(argv) or "")

    mod.action_leanmill_ratify_existing([
        "ztare_proofs/ZtareProofs/Example.lean",
        "Example.namespaceTheorem",
    ])

    assert synced == [
        "ztare_proofs/ZtareProofs/Dependency.lean",
        "ztare_proofs/ZtareProofs/Example.lean",
    ]
    assert built == [["ZtareProofs.Example"]]
    assert remote == [[
        "./venv/bin/python",
        "scripts/public/control/leanmill/solve_adhoc.py",
        "--target",
        "Example.namespaceTheorem",
        "--source-file",
        "ztare_proofs/ZtareProofs/Example.lean",
        "--substrate",
        "ztare_proofs",
        "--mode",
        "cascade",
        "--ratify-existing-target",
        "--json",
    ]]
    assert "--provider" not in remote[0]


def test_lean_import_source_closure_is_transitive_and_comment_safe(
    tmp_path, monkeypatch
) -> None:
    mod = load_module()
    proof_dir = tmp_path / "ztare_proofs" / "ZtareProofs"
    proof_dir.mkdir(parents=True)
    (proof_dir / "Root.lean").write_text(
        "import ZtareProofs.Dependency\n"
        "/- import ZtareProofs.CommentedOut -/\n"
        "theorem root : True := by trivial\n",
        encoding="utf-8",
    )
    (proof_dir / "Dependency.lean").write_text(
        "import ZtareProofs.Leaf\n"
        "theorem dependency : True := by trivial\n",
        encoding="utf-8",
    )
    (proof_dir / "Leaf.lean").write_text(
        "theorem leaf : True := by trivial\n",
        encoding="utf-8",
    )
    (proof_dir / "CommentedOut.lean").write_text(
        "theorem ignored : True := by trivial\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "LOCAL_REPO", tmp_path)

    assert mod.lean_import_source_closure(
        "ztare_proofs/ZtareProofs/Root.lean"
    ) == [
        "ztare_proofs/ZtareProofs/Leaf.lean",
        "ztare_proofs/ZtareProofs/Dependency.lean",
        "ztare_proofs/ZtareProofs/Root.lean",
    ]


def test_leanmill_extend_budget_forwards_formal_boundary_resources(
    monkeypatch,
) -> None:
    mod = load_module()
    remote: list[list[str]] = []
    monkeypatch.setattr(mod, "remote_cmd", lambda argv: remote.append(argv) or "")

    mod.action_leanmill_extend_budget([
        "/tmp/axiompack-attempt",
        "--phase", "boundary",
        "--formal-peer-attempts", "2",
        "--formal-peer-millis", "300000",
        "--lean-attempts", "4",
        "--lean-millis", "900000",
        "--authority-ref", "operator:budget-extension",
        "--reason", "finish governed task adjudication",
    ])

    assert remote == [[
        "./venv/bin/python",
        "-m",
        "ztare.leanmill.cli",
        "extend-budget",
        "/tmp/axiompack-attempt",
        "--phase", "boundary",
        "--formal-peer-attempts", "2",
        "--formal-peer-millis", "300000",
        "--lean-attempts", "4",
        "--lean-millis", "900000",
        "--authority-ref", "operator:budget-extension",
        "--reason", "finish governed task adjudication",
    ]]


def test_external_science_admission_is_named_budgeted_remote_action(
    monkeypatch,
) -> None:
    mod = load_module()
    synced: list[str] = []
    remote: list[list[str]] = []
    monkeypatch.setattr(mod, "sync_one_allowlisted", synced.append)
    monkeypatch.setattr(mod, "remote_cmd", lambda argv: remote.append(argv) or "")

    mod.action_leanmill_admit_external_science([
        "/tmp/axiompack-attempt",
        "ztare_proofs/ZtareProofs/AxiomPackFinalistOneBridge.lean",
        "AxiomPackFinalistOneBridge.finalistOneGlobalCommutation",
        "finite-model:example",
        (
            "research_areas/pre_registrations/"
            "axiompack_elementary_tetrahedron_frontier_v1_20260713/"
            "differential_mode_prior_art_audit.md"
        ),
        "theory-lineage:example",
        "--model",
        "gpt-5.5",
        "--reasoning-effort",
        "ultra",
    ])

    assert synced == [
        "ztare_proofs/ZtareProofs/AxiomPackFinalistOneBridge.lean",
        (
            "research_areas/pre_registrations/"
            "axiompack_elementary_tetrahedron_frontier_v1_20260713/"
            "differential_mode_prior_art_audit.md"
        ),
    ]
    assert remote == [[
        "./venv/bin/python",
        "scripts/public/control/leanmill/external_science_recovery.py",
        "--attempt-dir",
        "/tmp/axiompack-attempt",
        "--source-file",
        "ztare_proofs/ZtareProofs/AxiomPackFinalistOneBridge.lean",
        "--target",
        "AxiomPackFinalistOneBridge.finalistOneGlobalCommutation",
        "--finite-witness-model-id",
        "finite-model:example",
        "--literature-audit",
        (
            "research_areas/pre_registrations/"
            "axiompack_elementary_tetrahedron_frontier_v1_20260713/"
            "differential_mode_prior_art_audit.md"
        ),
        "--lineage-id",
        "theory-lineage:example",
        "--model",
        "gpt-5.5",
        "--reasoning-effort",
        "ultra",
        "--repo-root",
        mod.REMOTE_REPO,
    ]]


def test_nl_axiompack_campaign_launches_without_provider_free_preflight(
    monkeypatch,
) -> None:
    mod = load_module()
    remote = []
    monkeypatch.setattr(mod, "sync_one_allowlisted", lambda _path: None)
    monkeypatch.setattr(mod, "remote_cmd", remote.append)
    monkeypatch.setattr(mod, "remote_shell", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        mod, "sync_campaign_inputs", lambda _path: ["campaign.md"]
    )
    monkeypatch.setattr(mod, "_campaign_metadata", lambda _path: {})

    mod.action_leanmill_campaign(
        ["campaign.md", "/tmp/axiompack-nl", "--detach"]
    )

    assert remote == []


def test_codex_upgrade_uses_user_local_prefix_and_rechecks_version(monkeypatch) -> None:
    mod = load_module()
    calls = []
    monkeypatch.setattr(mod, "REMOTE_REPO", "/home/ztare/repo")
    monkeypatch.setattr(mod, "remote_cmd", lambda argv: calls.append(argv))

    mod.action_codex_upgrade(["0.144.0"])

    assert calls == [
        [
            "npm",
            "install",
            "--global",
            "--prefix",
            "/home/ztare/.local",
            "@openai/codex@0.144.0",
        ],
        ["codex", "--version"],
    ]


def test_leanmill_source_fetch_is_generic_digest_pinned_and_bounded(monkeypatch) -> None:
    mod = load_module()
    calls = []

    def remote(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[0] == "sha256sum":
            return "a" * 64 + "  snapshot.part\n"
        return ""

    monkeypatch.setattr(mod, "remote_cmd", remote)
    mod.action_leanmill_source_fetch(
        [
            "https://example.org/reference.json",
            "a" * 64,
            "/tmp/leanmill_source_snapshots/reference.json",
        ]
    )
    assert [row[0][0] for row in calls] == ["mkdir", "curl", "sha256sum", "mv"]

    with pytest.raises(SystemExit):
        mod.action_leanmill_source_fetch(
            [
                "https://example.org/reference.json",
                "a" * 64,
                "/tmp/outside/reference.json",
            ]
        )


def test_agent_observability_accepts_every_declared_runtime_role(
    monkeypatch,
) -> None:
    mod = load_module()
    calls: list[list[str]] = []
    monkeypatch.setattr(
        mod, "remote_cmd", lambda argv, **_kwargs: calls.append(argv) or ""
    )

    for role in sorted(mod.FRONTIER_RUNTIME_ROLES):
        mod.action_leanmill_agent_output(
            ["/tmp/axiompack-attempt", role, "0", "result"]
        )
        mod.action_leanmill_agent_results(["/tmp/axiompack-attempt", role])

    assert len(calls) == 2 * len(mod.FRONTIER_RUNTIME_ROLES)
    assert {call[-2] for call in calls[::2]} == set(mod.FRONTIER_RUNTIME_ROLES)
    assert {call[-1] for call in calls[1::2]} == set(mod.FRONTIER_RUNTIME_ROLES)
    assert all(
        "frontier_role_artifact_directories" in call[2] for call in calls
    )


@pytest.mark.parametrize(
    "role",
    ("../navigator", "navigator/../../formalizer", "not_registered"),
)
def test_agent_observability_rejects_traversal_and_unregistered_roles(
    role, monkeypatch
) -> None:
    mod = load_module()
    calls: list[list[str]] = []
    monkeypatch.setattr(
        mod, "remote_cmd", lambda argv, **_kwargs: calls.append(argv) or ""
    )

    with pytest.raises(SystemExit):
        mod.action_leanmill_agent_output(
            ["/tmp/axiompack-attempt", role, "0", "result"]
        )
    with pytest.raises(SystemExit):
        mod.action_leanmill_agent_results(["/tmp/axiompack-attempt", role])
    assert calls == []


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
