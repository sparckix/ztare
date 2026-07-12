"""Lightweight phase timing context manager for workspace instrumentation.

Appends one JSON line per phase to workspace/phase_timings.jsonl:
    {"schema": "ztare.phase_timing.v1", "phase": name, "seconds": ...,
     "started": ISO8601, "depth": int}

Usage:
    from ztare.common.phase_timing import phase

    with phase("frontier_expand", workspace_dir):
        ...  # timed body

Nested phases are supported; depth records the nesting level (0 = top-level).
The file is opened in append mode per record — no handle is held across phases.
No adoption wiring; callers opt in by importing this module.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_depth: int = 0  # ponytail: global counter fine for single-threaded BFS


@contextmanager
def phase(name: str, workspace_dir: "str | Path"):
    """Time a named phase and append one record to workspace/phase_timings.jsonl."""
    global _depth
    out_path = Path(workspace_dir) / "phase_timings.jsonl"
    started_ts = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()
    c0 = time.process_time()
    depth = _depth
    _depth += 1
    try:
        yield
    finally:
        _depth -= 1
        elapsed = time.monotonic() - t0
        cpu = time.process_time() - c0
        try:
            import resource
            rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1 << 20)
        except Exception:  # noqa: BLE001 — non-POSIX
            rss_mb = None
        record = {
            "schema": "ztare.phase_timing.v1",
            "phase": name,
            "seconds": round(elapsed, 6),
            # cpu_seconds/seconds ≈ 1 → CPU-bound (vectorize/memoize);
            # ≈ 0 → waiting on I/O or a remote API (parallelize instead).
            # Nested phases overlap in CPU accounting — compare within a depth.
            "cpu_seconds": round(cpu, 6),
            "max_rss_mb": round(rss_mb, 1) if rss_mb is not None else None,
            "started": started_ts,
            "depth": depth,
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a") as f:
            f.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Self-check (python -m ztare.common.phase_timing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile, pathlib

    with tempfile.TemporaryDirectory() as tmp:
        ws = pathlib.Path(tmp)
        with phase("outer", ws):
            with phase("inner", ws):
                pass
        lines = (ws / "phase_timings.jsonl").read_text().splitlines()
        assert len(lines) == 2, f"expected 2 records, got {len(lines)}"
        inner = json.loads(lines[0])  # inner closes first
        outer = json.loads(lines[1])
        assert outer["phase"] == "outer" and outer["depth"] == 0
        assert inner["phase"] == "inner" and inner["depth"] == 1
        assert outer["seconds"] >= inner["seconds"]
        assert outer["schema"] == "ztare.phase_timing.v1"
        assert "cpu_seconds" in outer and outer["cpu_seconds"] >= 0
        assert "max_rss_mb" in outer
    print("phase_timing self-check passed")
