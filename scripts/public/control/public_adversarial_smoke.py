#!/usr/bin/env python3
"""Adversarial smoke checks for the public ZTARE runtime.

The normal smoke target proves that the core scripts can run. This check tries
to catch the ways a smoke can become misleading: leaked runtime artifacts,
accidental dependence on private stores, missing Makefile wiring, and stale
public docs.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[3]
PYTHON = os.environ.get("PYTHON", sys.executable)
TEST_PREFIX = "test_runtime_smoke"

RUNTIME_ARTIFACT_DIRS = [
    REPO / "org/tasks/active",
    REPO / "ztare_workspace/gates/pending",
    REPO / "ztare_workspace/gates/resolved",
]

REQUIRED_MAKE_SNIPPETS = [
    "smoke-public:",
    "scripts/public/control/runtime_smoke_test.py",
    "scripts/public/control/forecast/pool.py smoke",
    "scripts/public/control/action_intelligence.py smoke",
    "public-adversarial-smoke:",
    "scripts/public/control/public_adversarial_smoke.py",
    "benchmark-evidence:",
    "scripts/public/control/benchmark_evidence_check.py",
    "demo:",
    "scripts/public/control/golden_path_demo.py",
    "smoke-docker:",
    "bash scripts/public/control/docker_smoke.sh",
    "gates:",
    "scripts/private/test_publish_safety.py",
    "scripts/private/validate_seam_spec_format.py",
    "scripts/public/validators/validate_markdown_links.py",
]

REQUIRED_DOCKER_SMOKE_SNIPPETS = [
    "docker build",
    "docker run --rm",
    "make smoke-public PYTHON=python",
]

REQUIRED_USER_DOC_SNIPPETS = [
    "make demo",
    "make smoke-public",
]

REQUIRED_REFERENCE_DOC_SNIPPETS = [
    "make demo",
    "make smoke-public",
    "make public-adversarial-smoke",
    "make smoke-docker",
    "make benchmark-evidence",
    "make gates",
]

REQUIRED_IGNORE_SNIPPETS = [
    "ztare_workspace/transitions.jsonl",
    "ztare_workspace/gates/pending/*.json",
    "ztare_workspace/gates/resolved/*.json",
    "org/tasks/active/*",
    "orbit/node_modules/",
    "analytics/private/",
    "research_areas/private/",
]

FORBIDDEN_PUBLIC_TERMS = [
    "unsupported superlative claim",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fail(message: str) -> None:
    raise SystemExit(f"public adversarial smoke failed: {message}")


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def runtime_artifacts() -> list[str]:
    found: list[str] = []
    for directory in RUNTIME_ARTIFACT_DIRS:
        if not directory.exists():
            continue
        for path in directory.glob(f"{TEST_PREFIX}*"):
            found.append(str(path.relative_to(REPO)))
    return sorted(found)


def require_snippets(path: Path, snippets: Iterable[str]) -> list[str]:
    text = read(path)
    return [snippet for snippet in snippets if snippet not in text]


def check_makefile_wiring() -> dict[str, object]:
    missing = require_snippets(REPO / "Makefile", REQUIRED_MAKE_SNIPPETS)
    if missing:
        fail(f"Makefile missing required wiring: {missing}")
    docker_missing = require_snippets(
        REPO / "scripts/public/control/docker_smoke.sh",
        REQUIRED_DOCKER_SMOKE_SNIPPETS,
    )
    if docker_missing:
        fail(f"docker_smoke.sh missing required wiring: {docker_missing}")
    return {
        "ok": True,
        "checked_makefile": len(REQUIRED_MAKE_SNIPPETS),
        "checked_docker_smoke": len(REQUIRED_DOCKER_SMOKE_SNIPPETS),
    }


def check_docs_wiring() -> dict[str, object]:
    user_paths = [
        REPO / "README.md",
        REPO / "docs/guides/first-30-minutes.md",
    ]
    user_text = "\n".join(read(path) for path in user_paths if path.exists())
    missing = [snippet for snippet in REQUIRED_USER_DOC_SNIPPETS if snippet not in user_text]
    if missing:
        fail(f"user docs missing public smoke snippets: {missing}")

    reference_path = REPO / "docs/reference/make_targets.md"
    reference_missing = require_snippets(reference_path, REQUIRED_REFERENCE_DOC_SNIPPETS)
    if reference_missing:
        fail(f"make-target reference missing maintainer command snippets: {reference_missing}")

    checked_paths = user_paths + [reference_path]
    return {"ok": True, "checked_files": [str(p.relative_to(REPO)) for p in checked_paths]}


def check_gitignore_boundaries() -> dict[str, object]:
    missing = require_snippets(REPO / ".gitignore", REQUIRED_IGNORE_SNIPPETS)
    if missing:
        fail(f".gitignore missing runtime/private boundaries: {missing}")
    return {"ok": True, "checked": len(REQUIRED_IGNORE_SNIPPETS)}


def check_public_language() -> dict[str, object]:
    checked_paths = [
        REPO / "README.md",
        REPO / "docs/guides/first-30-minutes.md",
        REPO / "docs/reference/make_targets.md",
        REPO / "benchmarks/benchmark_evidence.md",
        REPO / "research_areas/synthesis/GP-245_ztare_forward_eigenquestions_20260520.md",
    ]
    hits: list[str] = []
    for path in checked_paths:
        if not path.exists():
            continue
        text = read(path)
        for term in FORBIDDEN_PUBLIC_TERMS:
            if term in text:
                hits.append(f"{path.relative_to(REPO)} contains {term!r}")
    if hits:
        fail("; ".join(hits))
    return {"ok": True, "checked_files": [str(p.relative_to(REPO)) for p in checked_paths if p.exists()]}


def check_runtime_smoke_cleanup() -> dict[str, object]:
    before = runtime_artifacts()
    if before:
        fail(f"pre-existing runtime smoke artifacts block the check: {before}")
    proc = run([PYTHON, "scripts/public/control/runtime_smoke_test.py", "--json"])
    if proc.returncode != 0:
        fail(f"runtime_smoke_test.py failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        fail(f"runtime smoke did not emit JSON: {exc}")
    if not payload.get("ok"):
        fail(f"runtime smoke JSON reported failure: {payload}")
    after = runtime_artifacts()
    if after:
        fail(f"runtime smoke left artifacts behind: {after}")
    cleanup = payload.get("cleanup") or {}
    removed = cleanup.get("removed") or []
    if not removed:
        fail("runtime smoke did not report cleanup removals")
    return {"ok": True, "removed_count": len(removed)}


def check_forecast_pool_isolation() -> dict[str, object]:
    proc = run([PYTHON, "scripts/public/control/forecast/pool.py", "smoke"])
    if proc.returncode != 0:
        fail(f"forecast_pool.py smoke failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    if '"smoke": "pass"' not in proc.stdout:
        fail("forecast_pool smoke did not report pass")
    if "forecast_pool_smoke_" not in proc.stdout:
        fail("forecast_pool smoke did not report a temporary isolated root")
    repo_root_fragment = str(REPO / "analytics/public/forecast_pool")
    if repo_root_fragment in proc.stdout:
        fail("forecast_pool smoke wrote or reported the repo forecast-pool root")
    return {"ok": True, "isolated_root": "internal_tempdir"}


def check_action_intelligence_contracts() -> dict[str, object]:
    proc = run([PYTHON, "scripts/public/control/action_intelligence.py", "smoke"])
    if proc.returncode != 0:
        fail(f"action_intelligence.py smoke failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        fail(f"action intelligence smoke did not emit JSON: {exc}")
    if not payload.get("ok"):
        fail(f"action intelligence smoke JSON reported failure: {payload}")
    checked = payload.get("checked") or []
    required = {
        "decision_use_to_action_impact",
        "shadow_policy_live_row_rejection",
        "override_without_reason_rejection",
        "surfacing_event_to_action_impact",
    }
    missing = sorted(required.difference(checked))
    if missing:
        fail(f"action intelligence smoke missing contract checks: {missing}")
    return {"ok": True, "checked": checked}


def main() -> int:
    checks = {
        "makefile_wiring": check_makefile_wiring(),
        "docs_wiring": check_docs_wiring(),
        "gitignore_boundaries": check_gitignore_boundaries(),
        "public_language": check_public_language(),
        "runtime_smoke_cleanup": check_runtime_smoke_cleanup(),
        "forecast_pool_isolation": check_forecast_pool_isolation(),
        "action_intelligence_contracts": check_action_intelligence_contracts(),
    }
    print(json.dumps({"ok": True, "checks": checks}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
