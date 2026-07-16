from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("module_name", "mode"),
    [
        ("ztare.cli", "import"),
        ("ztare.workspace.fetch_evidence", "import"),
        ("ztare.supervisor.supervisor_wrappers", "import"),
        ("ztare.validator.autoresearch_loop", "help"),
        ("ztare.validator.test_thesis", "help"),
        ("ztare.validator.generate_committee", "help"),
    ],
)
def test_shared_entrypoints_do_not_require_api_provider_sdks(
    module_name: str,
    mode: str,
) -> None:
    script = r"""
import builtins
import runpy
import sys

target = sys.argv[1]
mode = sys.argv[2]
real_import = builtins.__import__

def provider_free_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split(".", 1)[0] in {"google", "openai", "anthropic"}:
        raise ModuleNotFoundError(f"blocked optional provider SDK: {name}", name=name)
    return real_import(name, globals, locals, fromlist, level)

builtins.__import__ = provider_free_import
if mode == "import":
    __import__(target)
else:
    sys.argv = [target, "--help"]
    try:
        runpy.run_module(target, run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", script, module_name, mode],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
