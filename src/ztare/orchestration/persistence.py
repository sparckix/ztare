"""GP-070 Goal Orchestrator — Persistence layer.

Implements:
- Write-ahead log: transitions.jsonl before state.json (C-6)
- Unconditional startup consistency check (C-7)
- Per-goal filesystem lock (C-24)
- Diff-on-resume artifact hash comparison (C-25)
"""

from __future__ import annotations

import datetime
import fcntl
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from ztare.orchestration.core import GoalState, GoalStatus

GOALS_ROOT = Path("[internal-ref]")


def goal_dir(slug: str) -> Path:
    return GOALS_ROOT / slug


def state_path(slug: str) -> Path:
    return goal_dir(slug) / "state.json"


def transitions_path(slug: str) -> Path:
    return goal_dir(slug) / "transitions.jsonl"


def lock_path(slug: str) -> Path:
    return goal_dir(slug) / ".goal.lock"


@contextmanager
def goal_lock(slug: str, timeout: float = 30.0):
    """Acquire exclusive per-goal filesystem lock (C-24)."""
    lp = lock_path(slug)
    lp.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lp), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        import signal

        def _timeout_handler(signum, frame):
            raise TimeoutError(
                f"Could not acquire lock for goal '{slug}' within {timeout}s. "
                f"Check if another process holds it: {lp}"
            )

        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(int(timeout))
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        os.write(fd, str(os.getpid()).encode())
        os.ftruncate(fd, os.lseek(fd, 0, os.SEEK_CUR))
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def write_state(slug: str, state: GoalState) -> None:
    sp = state_path(slug)
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(state.to_dict(), indent=2) + "\n")


def read_state(slug: str) -> Optional[GoalState]:
    sp = state_path(slug)
    if not sp.exists():
        return None
    return GoalState.from_dict(json.loads(sp.read_text()))


def append_transition(
    slug: str,
    *,
    from_stage: str,
    to_stage: str,
    action: str,
    reason: str = "",
    artifact_hashes: Optional[dict[str, str]] = None,
    artifact_drift: bool = False,
    drifted_files: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Append a transition record to transitions.jsonl (C-6: log before state)."""
    record = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "from_stage": from_stage,
        "to_stage": to_stage,
        "action": action,
        "reason": reason,
        "artifact_hashes": artifact_hashes or {},
        "artifact_drift": artifact_drift,
        "drifted_files": drifted_files or [],
        "metadata": metadata or {},
    }
    tp = transitions_path(slug)
    tp.parent.mkdir(parents=True, exist_ok=True)
    with open(tp, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def read_transitions(slug: str) -> list[dict[str, Any]]:
    tp = transitions_path(slug)
    if not tp.exists():
        return []
    records = []
    for line in tp.read_text().splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def replay_transitions(slug: str) -> Optional[str]:
    """Replay transitions.jsonl to determine the authoritative current stage (C-7)."""
    records = read_transitions(slug)
    if not records:
        return None
    current = records[0].get("from_stage")
    for r in records:
        current = r["to_stage"]
    return current


def check_consistency(slug: str) -> Optional[str]:
    """Unconditional startup consistency check (C-7).

    Returns None if consistent, or an error message if not.
    state.json stage must equal the result of replaying transitions.jsonl.
    """
    state = read_state(slug)
    if state is None:
        return None

    replayed = replay_transitions(slug)
    if replayed is None:
        return None

    if state.current_stage != replayed:
        return (
            f"AUDIT_INTEGRITY_VIOLATION: state.json says '{state.current_stage}' "
            f"but transitions.jsonl replays to '{replayed}'. "
            f"Halting. Operator must decide which is authoritative."
        )
    return None


def hash_file(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_artifacts(artifact_paths: list[Path]) -> dict[str, str]:
    return {str(p): hash_file(p) for p in artifact_paths}


def check_artifact_drift(
    slug: str, current_hashes: dict[str, str]
) -> tuple[bool, list[str]]:
    """Compare current artifact hashes against those recorded at gate escalation (C-25)."""
    state = read_state(slug)
    if state is None or not state.gate_escalation_hashes:
        return False, []

    drifted = []
    for path, old_hash in state.gate_escalation_hashes.items():
        new_hash = current_hashes.get(path, "MISSING")
        if new_hash != old_hash:
            drifted.append(path)

    return len(drifted) > 0, drifted
