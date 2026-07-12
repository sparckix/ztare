from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from ztare.common.subscription_agent_runtime import (
    OwnedDispatch,
    _owned_dispatch_for_process,
    _run_cli,
    build_subscription_agent_command,
    prompt_inline_max_bytes,
    cancel_owned_dispatch,
    owned_dispatch_status,
    owned_dispatch_receipt_status,
    cancel_owned_dispatch_receipt,
    subscription_dispatch_budget_scope,
)


def test_large_subscription_prompt_uses_stdin_and_binds_receipt(tmp_path: Path):
    prompt = "p" * (prompt_inline_max_bytes() + 1)
    command = build_subscription_agent_command(
        runtime="codex", prompt=prompt, repo=tmp_path
    )
    assert command[-1] == "-"
    receipt = tmp_path / "large-prompt.dispatch.json"
    result = _run_cli(
        [sys.executable, "-c", "import sys; print(len(sys.stdin.read()))"],
        runtime="claude",
        repo=tmp_path,
        timeout_seconds=5,
        stdin_text=prompt,
        dispatch_receipt_path=receipt,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == str(len(prompt))
    row = receipt.read_text(encoding="utf-8")
    assert '"stdin_sha256": "sha256:' in row


def test_owned_dispatch_identity_and_guarded_cancel(tmp_path: Path):
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
        start_new_session=True,
    )
    dispatch = _owned_dispatch_for_process(proc, [sys.executable, "sleep"])
    try:
        assert dispatch.leader_pid == dispatch.pgid == dispatch.sid
        assert dispatch.pgid != os.getpgrp()
        assert owned_dispatch_status(dispatch) == "running"
        assert cancel_owned_dispatch(dispatch)
        proc.wait(timeout=3)
        assert owned_dispatch_status(dispatch) == "exited"
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


def test_cancel_refuses_current_or_mutated_group():
    with pytest.raises(ValueError, match="parent group"):
        OwnedDispatch(
            call_id="bad",
            leader_pid=os.getpgrp(),
            pgid=os.getpgrp(),
            sid=os.getpgrp(),
            parent_pgid=os.getpgrp(),
            command_sha256="sha256:x",
        )

    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    dispatch = _owned_dispatch_for_process(proc, [sys.executable, "sleep"])
    mutated = OwnedDispatch(
        **{**dispatch.to_json(), "leader_pid": dispatch.leader_pid + 100000,
           "pgid": dispatch.leader_pid + 100000, "sid": dispatch.leader_pid + 100000}
    )
    try:
        assert owned_dispatch_status(mutated) == "exited"
        assert not cancel_owned_dispatch(mutated)
        assert proc.poll() is None
    finally:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


def test_timeout_kills_descendant_group_without_touching_parent(tmp_path: Path):
    sentinel = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    command = [
        sys.executable,
        "-c",
        (
            "import subprocess,sys,time; "
            "subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
            "print('started', flush=True); time.sleep(30)"
        ),
    ]
    started = time.monotonic()
    try:
        result = _run_cli(
            command,
            runtime="claude",
            repo=tmp_path,
            timeout_seconds=0.15,
            dispatch_receipt_path=tmp_path / "dispatch.json",
            stdout_path=str(tmp_path / "stdout.txt"),
            stderr_path=str(tmp_path / "stderr.txt"),
        )
        assert result.returncode == 124
        assert "started" in result.stdout
        assert time.monotonic() - started < 3
        assert sentinel.poll() is None
        assert owned_dispatch_receipt_status(tmp_path / "dispatch.json") == "completed"
        assert not cancel_owned_dispatch_receipt(tmp_path / "dispatch.json")
    finally:
        sentinel.terminate()
        sentinel.wait(timeout=3)


def test_subscription_dispatch_budget_scope_wraps_the_existing_runtime(tmp_path: Path):
    events = []
    with subscription_dispatch_budget_scope(
        before_dispatch=lambda runtime, command: events.append(
            ("before", runtime, command[-1])
        ) or "reservation-1",
        after_dispatch=lambda reservation: events.append(("after", reservation)),
    ):
        result = _run_cli(
            [sys.executable, "-c", "print('bounded')"],
            runtime="claude",
            repo=tmp_path,
            timeout_seconds=5,
        )
    assert result.returncode == 0
    assert result.stdout.strip() == "bounded"
    assert events == [
        ("before", "claude", "print('bounded')"),
        ("after", "reservation-1"),
    ]


def test_subscription_dispatch_budget_exhaustion_blocks_before_spawn(
    tmp_path: Path, monkeypatch
):
    spawned = []

    def forbidden_spawn(*args, **kwargs):
        spawned.append((args, kwargs))
        raise AssertionError("dispatch reached the process launcher")

    monkeypatch.setattr(
        "ztare.common.subscription_agent_runtime._run_cli_unbudgeted",
        forbidden_spawn,
    )
    with pytest.raises(RuntimeError, match="provider budget exhausted"):
        with subscription_dispatch_budget_scope(
            before_dispatch=lambda _runtime, _command: (_ for _ in ()).throw(
                RuntimeError("provider budget exhausted")
            ),
            after_dispatch=lambda _reservation: None,
        ):
            _run_cli(
                [sys.executable, "-c", "print('must not run')"],
                runtime="claude",
                repo=tmp_path,
                timeout_seconds=5,
            )
    assert spawned == []


def test_parallel_solver_threads_inherit_subscription_budget_scope(
    tmp_path: Path, monkeypatch
):
    from ztare.leanmill.solver.proposer_pool import attack_node

    events = []

    def fake_unbudgeted(command, **_kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="```lean\nrfl\n```",
            stderr="",
        )

    monkeypatch.setattr(
        "ztare.common.subscription_agent_runtime._run_cli_unbudgeted",
        fake_unbudgeted,
    )
    monkeypatch.setenv("ZTARE_LEANMILL_PROPOSER_PRIOR_FLOOR", "0")

    def dispatch(model, _prompt):
        return _run_cli(
            [model, "prompt"],
            runtime=model,
            repo=tmp_path,
            timeout_seconds=5,
        ).stdout

    with subscription_dispatch_budget_scope(
        before_dispatch=lambda runtime, _command: events.append(runtime) or runtime,
        after_dispatch=lambda _reservation: None,
    ):
        outcome = attack_node(
            "node",
            "prompt",
            lambda _proposal: True,
            repo=str(tmp_path),
            timeout=5,
            portfolio=["codex", "claude"],
            priors={"codex": 0.5, "claude": 0.5},
            dispatch_fn=dispatch,
        )
    assert outcome.closed is True
    assert sorted(events) == ["claude", "codex"]
