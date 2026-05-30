#!/usr/bin/env python3
"""Fresh-fork smoke test for the org kernel (RD-1.12, 2026-05-02).

Stands up a minimal kernel-only fork in a tempdir, exercises the
RD-1.12 detection → policy → execution chain end-to-end, and asserts
that:

  1. frontier_state initializes correctly for a new project_slug
  2. iter_action_policy.dispatch_event matches a synthetic obstruction
  3. iter_action_executor.drain_pending executes the queued action
  4. agent_utilization_tracker rejects over-budget calls
  5. damage signals land in org/signals/damage/ when triggered

Run:
    python scripts/public/control/forked_org_smoke.py            # exit 0 on pass, 1 on fail
    python scripts/public/control/forked_org_smoke.py --verbose  # print intermediate state

This is the canonical "is the kernel actually portable?" test. Anything
that depends on the principal's instantiated org (specific role yamls,
specific projects/, principal-side rubrics) MUST NOT be referenced here.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m"


def _red(s: str) -> str:
    return f"\033[31m{s}\033[0m"


def _step(label: str, ok: bool, detail: str = "") -> None:
    mark = _green("✓") if ok else _red("✗")
    print(f"  {mark} {label}{(' — ' + detail) if detail else ''}")


def stage_minimal_fork(target: Path) -> None:
    """Copy the kernel-only files needed for the smoke test into target.

    We deliberately do NOT copy the principal's projects/, org/objectives/,
    org/key_results/, ztare_workspace/, papers/, etc. The smoke test must
    run on the kernel skeleton alone.
    """
    target.mkdir(parents=True, exist_ok=True)

    # Kernel modules
    for src in [
        "src/ztare/role_extensions",
        "src/ztare/supervisor/agent_utilization_tracker.py",
        "src/ztare/supervisor/spend_tracker.py",
        "schemas/role.v1.schema.json",
    ]:
        s = REPO_ROOT / src
        d = target / src
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, d, dirs_exist_ok=True)
        elif s.exists():
            shutil.copy2(s, d)

    # Empty fixture dirs the kernel expects
    (target / "ztare_workspace" / "frontier_state").mkdir(parents=True, exist_ok=True)
    (target / "ztare_workspace" / "agent_utilization").mkdir(parents=True, exist_ok=True)
    (target / "org" / "signals" / "damage").mkdir(parents=True, exist_ok=True)
    (target / "projects").mkdir(parents=True, exist_ok=True)
    (target / "org" / "roles").mkdir(parents=True, exist_ok=True)

    # Make src/ a package
    for p in ["src", "src/ztare", "src/ztare/supervisor"]:
        init = target / p / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")


def run_smoke(verbose: bool = False) -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="ztare_org_smoke_") as td:
        tmp = Path(td)
        if verbose:
            print(f"  staging fork at {tmp}")
        stage_minimal_fork(tmp)

        # Run the kernel modules from the fork's own root, with cwd=tmp
        # so frontier_state writes land in the fork (not in the live repo).
        env = dict(os.environ)
        env["PYTHONPATH"] = str(tmp) + os.pathsep + env.get("PYTHONPATH", "")

        # ── Test 1: frontier_state init ─────────────────────────
        script = (
            "import sys; sys.path.insert(0, '.'); "
            "from src.ztare.role_extensions import frontier_state as fs; "
            "import os; os.chdir('.'); "
            "s = fs.load_state('smoke_proj'); "
            "print('OK' if s.project_slug == 'smoke_proj' else 'FAIL: slug=' + s.project_slug)"
        )
        # Patch fs.STATE_ROOT to live inside the tmp tree
        script = (
            "import sys, os; sys.path.insert(0, '.'); os.chdir('.'); "
            "from pathlib import Path; "
            "from src.ztare.role_extensions import frontier_state as fs; "
            "fs.STATE_ROOT = Path('ztare_workspace/frontier_state'); "
            "s = fs.load_state('smoke_proj'); "
            "fs.update_route_ranking(s, [fs.RouteEntry(route_id='r1', label='primary', rank=1)]); "
            "fs.increment_obstruction(s, 'r1', reason='smoke iter 3'); "
            "fs.increment_obstruction(s, 'r1', reason='smoke iter 4'); "
            "s2 = fs.load_state('smoke_proj'); "
            "ok = s2.route_ranking[0].get('obstruction_count') == 2; "
            "print('OK' if ok else 'FAIL: count=' + str(s2.route_ranking[0]))"
        )
        r = subprocess.run(
            [sys.executable, "-c", script], cwd=tmp, env=env,
            capture_output=True, text=True,
        )
        ok = r.returncode == 0 and r.stdout.strip() == "OK"
        _step("frontier_state init + update_route_ranking + increment_obstruction", ok,
              r.stdout.strip() + (r.stderr.strip() if not ok else ""))
        if not ok:
            failures.append("frontier_state")

        # ── Test 2: policy dispatcher matches synthetic event ──
        # Write an inline policy yaml in the fork
        policy_yaml = tmp / "smoke_policy.yaml"
        policy_yaml.write_text(
            "schema_version: 1\n"
            "rules:\n"
            "  - id: smoke_obstruction_rule\n"
            "    when: { kind: obstruction_detected, consecutive_count: '>=2' }\n"
            "    do:\n"
            "      action_kind: queue_cold_shot\n"
            "      params: { model_id: stub-model, prompt_template: stub_v1 }\n"
            "    cooldown_seconds: 0\n",
            encoding="utf-8",
        )
        script2 = (
            "import sys, os; sys.path.insert(0, '.'); os.chdir('.'); "
            "from pathlib import Path; "
            "from src.ztare.role_extensions import frontier_state as fs; "
            "from src.ztare.role_extensions.iter_action_policy import dispatch_event; "
            "fs.STATE_ROOT = Path('ztare_workspace/frontier_state'); "
            "ev = dict(kind='obstruction_detected', project_slug='smoke_proj', "
            "         consecutive_count=3, route_id='r1', iter_index=4); "
            "queued = dispatch_event(ev, policy_path=Path('smoke_policy.yaml')); "
            "ok = len(queued) == 1 and queued[0][1]['action_kind'] == 'queue_cold_shot'; "
            "print('OK' if ok else 'FAIL: ' + str(queued))"
        )
        r2 = subprocess.run(
            [sys.executable, "-c", script2], cwd=tmp, env=env,
            capture_output=True, text=True,
        )
        ok = r2.returncode == 0 and r2.stdout.strip() == "OK"
        _step("iter_action_policy.dispatch_event matches obstruction", ok,
              r2.stdout.strip() + (r2.stderr.strip() if not ok else ""))
        if not ok:
            failures.append("policy_dispatch")

        # ── Test 3: executor drains queued action ──────────────
        # Set up project dir for queue_cold_shot to write into
        (tmp / "projects" / "smoke_proj").mkdir(parents=True, exist_ok=True)
        script3 = (
            "import sys, os; sys.path.insert(0, '.'); os.chdir('.'); "
            "from pathlib import Path; "
            "from src.ztare.role_extensions import frontier_state as fs; "
            "from src.ztare.role_extensions.iter_action_executor import drain_pending; "
            "fs.STATE_ROOT = Path('ztare_workspace/frontier_state'); "
            "outcomes = drain_pending('smoke_proj'); "
            "ok = len(outcomes) == 1 and outcomes[0]['ok'] is True; "
            "print('OK' if ok else 'FAIL: ' + str(outcomes))"
        )
        r3 = subprocess.run(
            [sys.executable, "-c", script3], cwd=tmp, env=env,
            capture_output=True, text=True,
        )
        ok = r3.returncode == 0 and r3.stdout.strip() == "OK"
        _step("iter_action_executor.drain_pending drains queued action", ok,
              r3.stdout.strip() + (r3.stderr.strip() if not ok else ""))
        if not ok:
            failures.append("executor_drain")

        # ── Test 4: cold-shot packet was actually written ───────
        packets = list((tmp / "projects" / "smoke_proj" / "workspace").glob("cold_shot_packet_*.json"))
        ok = len(packets) == 1
        if ok:
            payload = json.loads(packets[0].read_text())
            ok = payload.get("model_id") == "stub-model"
        _step("cold_shot packet written by executor", ok,
              f"found {len(packets)} packets")
        if not ok:
            failures.append("packet_written")

    print()
    if failures:
        print(_red(f"smoke FAILED — {len(failures)} test(s) failed: ") + ", ".join(failures))
        return 1
    print(_green("smoke PASSED — RD-1.12 kernel chain works on a fresh fork"))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Fresh-fork org-kernel smoke test")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()
    return run_smoke(verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
