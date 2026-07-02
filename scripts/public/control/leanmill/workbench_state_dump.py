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
    """Is a LeanMill run happening right now? PURE TELEMETRY — the freshness of worker heartbeats in the
    work-queue SQLite (`last_seen_at`), NOT a process/pgrep check. Missing DB → no run. Never raises."""
    try:
        import sqlite3
        import time
        from ztare.leanmill import work_queue

        db = work_queue.DEFAULT_DB
        if not Path(db).exists():
            return {"active": False, "worker_count": 0, "workers": []}
        cx = sqlite3.connect(db)
        cx.row_factory = sqlite3.Row
        now = int(time.time())
        rows = cx.execute(
            "SELECT worker_id, worker_kind, last_seen_at FROM worker_heartbeats "
            "WHERE last_seen_at >= ? ORDER BY last_seen_at DESC",
            (now - stale_s,),
        ).fetchall()
        cx.close()
        workers = [
            {"worker_id": r["worker_id"], "kind": r["worker_kind"] or "worker", "age_s": now - int(r["last_seen_at"])}
            for r in rows[:6]
        ]
        return {"active": len(workers) > 0, "worker_count": len(workers), "workers": workers, "stale_s": stale_s}
    except Exception:
        return {"active": False, "worker_count": 0, "workers": []}


def main(argv: "list[str] | None" = None) -> int:
    state = leanmill_payloads.state_payload(repo=REPO, storage=_ReadOnlyStore(REPO))
    # Augment with a telemetry-based "is a run happening" signal (worker-heartbeat freshness).
    state["run"] = _leanmill_run_active()
    print(json.dumps(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
