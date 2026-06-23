import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from ztare.common.paths import PROJECTS_DIR, REPO_ROOT, RUBRICS_DIR
from ztare.reports.autoresearch_trace import build_autoresearch_trace
from ztare.scaffold.substrate_queue import build_project_packet, write_project_packet
from ztare.workspace.update_workspace import checkpoint_source_index


def _slug() -> str:
    return f"__ztare_loop_canary_{int(time.time())}_{os.getpid()}"


def _write_fixture(project_dir: Path, rubric_path: Path, slug: str) -> None:
    project_dir.mkdir(parents=True, exist_ok=False)
    for name in ("workspace", "history", "raw"):
        (project_dir / name).mkdir()
    rubric = {
        "rubric_version": "1.0",
        "project": slug,
        "rubric_mode": "kepler",
        "falsification_mode": "bounded_discriminator",
        "fit_score_mode": "continuous_l2",
        "persona": (
            "You are a strict bounded canary judge. Evaluate only whether the "
            "submitted local discriminator is coherent with the tiny visible fixture."
        ),
        "criteria": {
            "Local_Coherence": "The thesis defines a narrow local discriminator.",
            "Executable_Surface": "test_model.py is importable and exposes I_model.",
        },
        "dimensions": [
            {"name": "Local Coherence", "weight": 50, "description": "Narrow thesis/evidence alignment."},
            {"name": "Executable Surface", "weight": 50, "description": "Importable bounded Python surface."},
        ],
    }
    rubric_path.write_text(json.dumps(rubric, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (project_dir / "verified_axioms.json").write_text("[]\n", encoding="utf-8")
    (project_dir / "evidence.txt").write_text(
        "Visible canary rows:\n- x=0 -> y=1\n- x=1 -> y=2\n",
        encoding="utf-8",
    )
    (project_dir / "project_charter.md").write_text(
        "# Autoresearch Loop Canary\n\n"
        "## Core Question\n"
        "Can the loop run against a temporary bounded discriminator fixture?\n",
        encoding="utf-8",
    )
    thesis = (
        "# Canary Thesis\n\n"
        "This is a narrow local discriminator canary. For the two visible rows, "
        "the model returns y = x + 1. No broader claim is made.\n"
    )
    (project_dir / "thesis.md").write_text(thesis, encoding="utf-8")
    (project_dir / "current_iteration.md").write_text(thesis, encoding="utf-8")
    (project_dir / "test_model.py").write_text(
        "MODEL_PARAMS = {'bias': 1.0}\n\n"
        "def I_model(features, params=None):\n"
        "    params = params or MODEL_PARAMS\n"
        "    return float(features.get('x', 0.0)) + float(params['bias'])\n\n"
        "def test_visible_rows():\n"
        "    assert I_model({'x': 0.0}) == 1.0\n"
        "    assert I_model({'x': 1.0}) == 2.0\n",
        encoding="utf-8",
    )


def _validate_fixture(slug: str, rubric_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/public/validators/validate_rubric.py"),
            slug,
            "--rubric",
            str(rubric_path),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_loop(slug: str, *, runtime: str = "codex", timeout_seconds: int = 90) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(REPO_ROOT / "src")
        if not env.get("PYTHONPATH")
        else f"{REPO_ROOT / 'src'}{os.pathsep}{env['PYTHONPATH']}"
    )
    env["ZTARE_AGENT_DISPATCH_JUDGE"] = "agent"
    env["ZTARE_AGENT_DISPATCH_INVERTER_REVIEW"] = "agent"
    env["ZTARE_AUTORESEARCH_JUDGE_AGENT_RUNTIME"] = runtime
    env["ZTARE_AUTORESEARCH_INVERTER_REVIEW_AGENT_RUNTIME"] = runtime
    env["ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS"] = str(timeout_seconds)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "src.ztare.validator.autoresearch_loop",
            "--project",
            slug,
            "--rubric",
            slug,
            "--iters",
            "0",
            "--mutator_model",
            "gemini",
            "--judge_model",
            "gpt4.1",
            "--disable_attacker_tools",
            "--run-mode",
            "canary",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=max(timeout_seconds * 3, 180),
        check=False,
    )


def _run_loop_canary(*, live: bool = False) -> dict[str, Any]:
    slug = _slug()
    project_dir = PROJECTS_DIR / slug
    rubric_path = RUBRICS_DIR / f"{slug}.json"
    report: dict[str, Any] = {
        "slug": slug,
        "project_path": str(project_dir.relative_to(REPO_ROOT)),
        "rubric_path": str(rubric_path.relative_to(REPO_ROOT)),
        "fixture_ok": False,
        "loop_ok": None,
        "cleanup_ok": None,
    }
    try:
        _write_fixture(project_dir, rubric_path, slug)
        fixture = _validate_fixture(slug, rubric_path)
        report["fixture_returncode"] = fixture.returncode
        report["fixture_ok"] = fixture.returncode == 0
        if live and report["fixture_ok"]:
            loop = _run_loop(slug)
            latest_eval = project_dir / "latest_eval_results.json"
            eval_payload = json.loads(latest_eval.read_text(encoding="utf-8")) if latest_eval.exists() else {}
            report["loop_returncode"] = loop.returncode
            report["latest_eval_exists"] = latest_eval.exists()
            report["latest_eval_score"] = eval_payload.get("score")
            report["latest_eval_has_weakest_point"] = bool(eval_payload.get("weakest_point"))
            report["loop_ok"] = bool(
                loop.returncode == 0
                and latest_eval.exists()
                and isinstance(eval_payload.get("score"), int)
                and eval_payload.get("weakest_point")
            )
        return report
    finally:
        for path in (project_dir, rubric_path):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        report["cleanup_ok"] = not project_dir.exists() and not rubric_path.exists()


def test_loop_canary_dry_fixture_validates_and_cleans_up() -> None:
    report = _run_loop_canary(live=False)

    assert report["fixture_ok"] is True
    assert report["loop_ok"] is None
    assert report["cleanup_ok"] is True
    assert not (REPO_ROOT / Path(report["project_path"])).exists()
    assert not (REPO_ROOT / Path(report["rubric_path"])).exists()


def test_autoresearch_loop_help_accepts_deepseek_model_aliases() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.ztare.validator.autoresearch_loop",
            "--help",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0
    assert "deepseek-chat" in proc.stdout
    assert "deepseek-reasoner" in proc.stdout
    assert "--packet" in proc.stdout
    assert "--preflight-only" in proc.stdout


def test_loop_preflight_only_does_not_require_gemini_key_or_write_eval() -> None:
    slug = _slug()
    project_dir = PROJECTS_DIR / slug
    rubric_path = RUBRICS_DIR / f"{slug}.json"
    try:
        _write_fixture(project_dir, rubric_path, slug)
        fixture = _validate_fixture(slug, rubric_path)
        assert fixture.returncode == 0
        env = os.environ.copy()
        env["PYTHONPATH"] = (
            str(REPO_ROOT / "src")
            if not env.get("PYTHONPATH")
            else f"{REPO_ROOT / 'src'}{os.pathsep}{env['PYTHONPATH']}"
        )
        env.pop("GEMINI_API_KEY", None)
        env.pop("GOOGLE_API_KEY", None)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.ztare.validator.autoresearch_loop",
                "--project",
                slug,
                "--rubric",
                slug,
                "--iters",
                "1",
                "--preflight-only",
                "--disable_attacker_tools",
            ],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        telemetry_path = project_dir / "workspace" / "iteration_telemetry.jsonl"
        telemetry_rows = [
            json.loads(line)
            for line in telemetry_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        assert proc.returncode == 0, proc.stderr
        assert "preflight-only" in proc.stdout
        assert "GEMINI_API_KEY is not set" not in proc.stderr
        assert not (project_dir / "latest_eval_results.json").exists()
        assert [row["record_type"] for row in telemetry_rows] == ["run_start", "run_end"]
        assert telemetry_rows[0]["preflight_only"] is True
        assert telemetry_rows[1]["run_exit_reason"] == "preflight_only"
        assert telemetry_rows[1]["final_score"] is None
    finally:
        for path in (project_dir, rubric_path):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()


def test_loop_preflight_only_records_packet_admission_digest() -> None:
    slug = f"ztare_loop_canary_{int(time.time())}_{os.getpid()}"
    project_dir = PROJECTS_DIR / slug
    rubric_path = RUBRICS_DIR / f"{slug}.json"
    packet_path = project_dir / "project_packet.json"
    try:
        _write_fixture(project_dir, rubric_path, slug)
        source_path = project_dir / "raw" / "source.md"
        source_path.write_text(
            "---\nsource_type: source_evidence\n---\n"
            "Visible canary rows:\n- x=0 -> y=1\n- x=1 -> y=2\n",
            encoding="utf-8",
        )
        checkpoint_source_index(
            project_dir=project_dir,
            raw_dir=project_dir / "raw",
            workspace_dir=project_dir / "workspace",
            model_family="gemini",
            max_files=10,
            max_chars_per_file=1000,
            max_total_chars=5000,
        )
        source_index = json.loads(
            (project_dir / "workspace" / "source_index.json").read_text(
                encoding="utf-8"
            )
        )
        evidence_path = project_dir / "evidence.txt"
        evidence_sha = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        (project_dir / "compiled_evidence_provenance.json").write_text(
            json.dumps(
                {
                    "mode": "raw",
                    "source_count": len(source_index["sources"]),
                    "sources": source_index["sources"],
                    "output_path": str(evidence_path),
                    "output_sha256": evidence_sha,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        write_project_packet(
            packet_path,
            build_project_packet(
                project=slug,
                rubric=slug,
                task="test packet-bound preflight",
                bounded_claim="preflight can bind packet-backed launch state",
                source_refs=[f"projects/{slug}/raw/source.md"],
                evidence_refs=[f"projects/{slug}/evidence.txt"],
                non_claims=["not a substantive research result"],
                next_falsifier="edit packet or evidence after trace and rerun preflight",
                expected_command=(
                    "ztare autoresearch route --task 'test packet-bound preflight' "
                    f"--project {slug} --rubric {slug}"
                ),
            ),
        )
        fixture = _validate_fixture(slug, rubric_path)
        assert fixture.returncode == 0

        packet_arg = str(packet_path.relative_to(REPO_ROOT))
        trace = build_autoresearch_trace(
            project=slug,
            rubric=slug,
            packet=packet_arg,
            repo=REPO_ROOT,
            full_health=False,
        )
        assert trace["kernel_entry"]["can_enter_kernel"] is True
        expected_kernel_entry_sha = hashlib.sha256(
            json.dumps(
                trace["kernel_entry"],
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        expected_packet_sha = hashlib.sha256(packet_path.read_bytes()).hexdigest()

        env = os.environ.copy()
        env["PYTHONPATH"] = (
            str(REPO_ROOT / "src")
            if not env.get("PYTHONPATH")
            else f"{REPO_ROOT / 'src'}{os.pathsep}{env['PYTHONPATH']}"
        )
        env.pop("GEMINI_API_KEY", None)
        env.pop("GOOGLE_API_KEY", None)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.ztare.validator.autoresearch_loop",
                "--project",
                slug,
                "--rubric",
                slug,
                "--packet",
                packet_arg,
                "--iters",
                "1",
                "--preflight-only",
                "--disable_attacker_tools",
            ],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
        telemetry_rows = [
            json.loads(line)
            for line in (project_dir / "workspace" / "iteration_telemetry.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

        assert proc.returncode == 0, proc.stderr
        admission = telemetry_rows[0]["project_packet"]
        assert admission["packet_path"] == packet_arg
        assert admission["packet_sha256"] == expected_packet_sha
        assert admission["packet_status"] == "valid_packet"
        assert admission["readiness"] == "ready_for_first_in_loop_run"
        assert admission["kernel_entry_status"] == "ready"
        assert admission["kernel_entry_sha256"] == expected_kernel_entry_sha
    finally:
        for path in (project_dir, rubric_path):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()


@pytest.mark.skipif(
    os.environ.get("ZTARE_LIVE_AUTORESEARCH_LOOP_CANARY") != "1",
    reason="live subscription CLI canary; set ZTARE_LIVE_AUTORESEARCH_LOOP_CANARY=1",
)
def test_loop_canary_live_subscription_judge_entrypoint() -> None:
    report = _run_loop_canary(live=True)

    assert report["fixture_ok"] is True
    assert report["loop_ok"] is True
    assert report["cleanup_ok"] is True
