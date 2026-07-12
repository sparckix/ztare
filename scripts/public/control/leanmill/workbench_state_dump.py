"""ztare leanmill workbench-state — dump the Workbench LeanMill panel state as JSON.

CLI-master: the forensic workbench consumes THIS (`ztare leanmill workbench-state --json`) instead of
importing `server_payloads.leanmill.state_payload` in-process. The state-building logic stays in the kernel
module; this script is the thin CLI door the server shells out to (like `autoresearch research-graph`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from ztare.workspace.server_payloads import leanmill as leanmill_payloads  # noqa: E402


class _ReadOnlyStore:
    """The subset of FileWorkbenchStorage that `state_payload` uses (read_text + rel), standalone so
    the CLI needn't import the whole server. Mirrors the server storage's resolve/read semantics."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root).resolve()

    def _resolve(self, path) -> Path:
        candidate = Path(path)
        return candidate.resolve() if candidate.is_absolute() else (self._root / candidate).resolve()

    def rel(self, path) -> str:
        return str(self._resolve(path).relative_to(self._root))

    def read_text(self, path, *, errors: str | None = None) -> str:
        kwargs = {"encoding": "utf-8"}
        if errors is not None:
            kwargs["errors"] = errors
        return self._resolve(path).read_text(**kwargs)


def _leanmill_run_active(stale_s: int = 240) -> dict:
    """Report proof work, not merely connected worker processes.

    A worker may keep heartbeating after a campaign finalizes while it waits for more work. The Workbench may
    call that worker connected, but it must say proofs are being attempted only when a process-valid heartbeat
    owns a non-expired claimed work item.
    """
    try:
        import sqlite3
        from ztare.leanmill import work_queue

        db = work_queue.DEFAULT_DB
        if not Path(db).exists():
            return {"active": False, "worker_count": 0, "connected_worker_count": 0, "idle_worker_count": 0, "workers": []}
        cx = sqlite3.connect(db)
        cx.row_factory = sqlite3.Row
        health = work_queue.worker_version_health(cx, stale_after_s=stale_s)
        connected = list(health.get("active_heartbeats") or [])
        workers = []
        for heartbeat in connected:
            work_id = str(heartbeat.get("claimed_work_id") or "")
            if not work_id:
                continue
            work = cx.execute(
                "SELECT status, lease_until FROM work_items WHERE work_id=?",
                (work_id,),
            ).fetchone()
            if not work or str(work["status"] or "") != "claimed":
                continue
            workers.append({
                "worker_id": str(heartbeat.get("worker_id") or ""),
                "kind": str(heartbeat.get("worker_kind") or "worker"),
                "work_id": work_id,
                "age_s": int(heartbeat.get("heartbeat_age_s") or 0),
            })
        cx.close()
        return {
            "active": bool(workers),
            "worker_count": len(workers),
            "connected_worker_count": len(connected),
            "idle_worker_count": max(0, len(connected) - len(workers)),
            "workers": workers[:6],
            "stale_s": stale_s,
        }
    except Exception:
        return {"active": False, "worker_count": 0, "connected_worker_count": 0, "idle_worker_count": 0, "workers": []}


def main(argv: "list[str] | None" = None) -> int:
    state = leanmill_payloads.state_payload(repo=REPO, storage=_ReadOnlyStore(REPO))
    # Augment with a telemetry-based "is a run happening" signal (worker-heartbeat freshness).
    state["run"] = _leanmill_run_active()
    print(json.dumps(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
