import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from src.ztare.common.paths import PROJECTS_DIR, REPO_ROOT, RUBRICS_DIR


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


@pytest.mark.skipif(
    os.environ.get("ZTARE_LIVE_AUTORESEARCH_LOOP_CANARY") != "1",
    reason="live subscription CLI canary; set ZTARE_LIVE_AUTORESEARCH_LOOP_CANARY=1",
)
def test_loop_canary_live_subscription_judge_entrypoint() -> None:
    report = _run_loop_canary(live=True)

    assert report["fixture_ok"] is True
    assert report["loop_ok"] is True
    assert report["cleanup_ok"] is True
