import importlib
import os
import sys
from pathlib import Path

import pytest

# Project root layout uses `ztare...` as the canonical import path;
# ensure the project root is on sys.path when tests are run directly or via pytest.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# Workbench command-surfacing tests assert commands built from workbench settings. Those settings resolve from
# the repo's real `.env` + `ZTARE_WORKBENCH_*` env (the operator's model/retry config) — which must not leak
# into the assertions (a dev with `ZTARE_WORKBENCH_MODEL=deepseek` or a populated `.env` would otherwise see
# spurious `MODEL=deepseek` / `--mutator deepseek` in the surfaced commands). This fixture makes those tests
# hermetic: clear the env vars and point every settings/.env resolution at a clean empty dir. Scoped to the two
# affected modules by node id, so the other suites are untouched. Tests that WANT a value set it explicitly and
# run after this fixture (their monkeypatch wins).
_WORKBENCH_CFG_TESTS = ("test_forensic_workbench_snapshot", "test_autoresearch_workbench_router")
_WORKBENCH_CFG_ROOTS = (
    ("ztare.workspace.workbench_settings", "REPO_ROOT"),
    ("ztare.reports.autoresearch_trace", "REPO"),
    ("ztare.research_director.autoresearch_workbench_router", "REPO_ROOT"),
)


@pytest.fixture(autouse=True)
def _isolate_workbench_config(request, monkeypatch, tmp_path_factory):
    if not any(name in request.node.nodeid for name in _WORKBENCH_CFG_TESTS):
        return
    for key in list(os.environ):
        if key.startswith("ZTARE_WORKBENCH_"):
            monkeypatch.delenv(key, raising=False)
    clean = tmp_path_factory.mktemp("wb_clean_cfg")  # a dir with no .env → settings resolve to defaults
    for module_name, attr in _WORKBENCH_CFG_ROOTS:
        try:
            module = importlib.import_module(module_name)
        except Exception:  # noqa: BLE001 — a module that isn't importable simply isn't the leak source
            continue
        if hasattr(module, attr):
            monkeypatch.setattr(module, attr, clean, raising=False)
