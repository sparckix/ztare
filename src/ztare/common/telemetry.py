"""Shared telemetry interface — the ONE home for timing / event emission across the codebase.

WHY THIS EXISTS. Timing + event emission had accreted into parallel copies: four `append_jsonl` siblings
(`common/file_io.append_jsonl`, `orchestrator/telemetry.append_jsonl`, `iteration_telemetry._append_json_dict`,
and `autoresearch_loop`'s local one — the last even documents "Mirrors autoresearch_loop's local append_jsonl,
same shape, different home"), a per-domain `utc_now_iso`, and no shared *stopwatch* at all. Both autoresearch
(orchestrator/iteration_telemetry, loop_event_recorder) and leanmill (phase_timing) need the same three things:
a timestamp, an append-one-event, and a phase stopwatch + a phase-decomposed read model. This module is that
single seam, so improving it benefits both lanes instead of forking a fifth copy.

LAYERING. Base layer: depends only on stdlib + `common.file_io` (the canonical dict→JSONL append). It imports
NOTHING from orchestrator/leanmill, so every higher layer can import it without a cycle.

INTERFACE.
  utc_now_iso() -> str
  record_event(ledger, event, *, enabled=True) -> None        # append one event dict (best-effort, stamps ts)
  phase_timer(phase, *, ledger, run_tag="", tags=None, enabled=True)  # ctx mgr: wall duration → timing event
  summarize_timings(ledger, *, run_tag="", group_key="phase") -> dict # decompose where the wall-clock went

SAFETY. Emit is best-effort — telemetry must never break the work it measures — but every `except` uses stdlib
names imported LOCALLY inside the `try` (the NameError-then-silently-noop bug class: a best-effort writer that
references an un-imported name no-ops forever, and the empty file reads as "nothing happened"). The selftest RUNS
the writer once and asserts a non-empty ledger.
"""
from __future__ import annotations

import contextlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ztare.common.file_io import append_jsonl  # the canonical dict→JSONL append (single primitive, mkdir+dumps)


def utc_now_iso() -> str:
    """Current ISO-8601 UTC timestamp with explicit timezone offset (the one canonical timestamp)."""
    return datetime.now(timezone.utc).isoformat()


def record_event(ledger: "str | Path", event: dict, *, enabled: bool = True) -> None:
    """Append one telemetry event (a dict) to `ledger` (JSONL). Stamps `ts` if absent. Best-effort: a failure
    can never break the caller, and stdlib names are imported locally so it can never NameError-then-silently-noop."""
    if not enabled:
        return
    try:
        ev = dict(event)
        ev.setdefault("ts", utc_now_iso())
        append_jsonl(Path(ledger), ev)
    except Exception:  # noqa: BLE001 — telemetry must never break the measured work
        pass


@contextlib.contextmanager
def phase_timer(
    phase: str,
    *,
    ledger: "str | Path",
    run_tag: str = "",
    tags: "Optional[dict]" = None,
    enabled: bool = True,
):
    """`with phase_timer('govern.mnc', ledger=path, tags={'target': name}):` — records the wall duration on
    exit, INCLUDING on exception (the error class is recorded, then the exception re-raised; timing never
    swallows the real failure). Emits a `kind="phase_timing"` event."""
    t0 = time.monotonic()
    _err = ""
    try:
        yield
    except Exception as e:  # noqa: BLE001 — record-then-reraise; never swallow
        _err = type(e).__name__
        raise
    finally:
        ev = {
            "kind": "phase_timing",
            "phase": str(phase),
            "duration_s": round(time.monotonic() - t0, 4),
            "run_tag": run_tag or "",
            "outcome": ("error:" + _err) if _err else "",
        }
        if tags:
            ev["tags"] = tags
        record_event(ledger, ev, enabled=enabled)


def _percentile(sorted_vals: "list[float]", q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(round(q * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def summarize_timings(
    ledger: "str | Path",
    *,
    run_tag: str = "",
    group_key: str = "phase",
) -> dict:
    """Aggregate a phase_timing ledger into a decomposed cycle-time report. Returns:
      { groups: {<group>: {count,total_s,mean_s,p50_s,p95_s,max_s}},   # ranked by total_s desc — where time went
        runs:   {run_tag: {lead_time_s, total_wall_s, span_start, span_end, event_count}},
        total_wall_s, total_events }
    `lead_time_s` per run = the span from the first to the last event timestamp (a proxy for time-to-insight;
    join with a domain closure ledger for the precise input→first-result lead). Read-only; safe to call live."""
    import json as _json

    path = Path(ledger)
    if not path.exists():
        return {"groups": {}, "runs": {}, "total_wall_s": 0.0, "total_events": 0}
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(_json.loads(line))
        except Exception:  # noqa: BLE001 — a torn line never breaks the read
            continue
    rows = [r for r in rows if r.get("kind") == "phase_timing"]
    if run_tag:
        rows = [r for r in rows if (r.get("run_tag") or "") == run_tag]

    by_group: dict[str, list[float]] = {}
    by_run: dict[str, list[dict]] = {}
    for r in rows:
        by_group.setdefault(str(r.get(group_key) or "?"), []).append(float(r.get("duration_s") or 0.0))
        by_run.setdefault(str(r.get("run_tag") or ""), []).append(r)

    def agg(ds: "list[float]") -> dict:
        s = sorted(ds)
        n = len(s)
        return {
            "count": n,
            "total_s": round(sum(s), 2),
            "mean_s": round(sum(s) / n, 3) if n else 0.0,
            "p50_s": round(_percentile(s, 0.50), 3),
            "p95_s": round(_percentile(s, 0.95), 3),
            "max_s": round(s[-1], 3) if n else 0.0,
        }

    groups = {k: agg(v) for k, v in sorted(by_group.items(), key=lambda kv: -sum(kv[1]))}

    runs: dict[str, dict] = {}
    for rt, rrows in by_run.items():
        tss = sorted(str(x.get("ts") or "") for x in rrows if x.get("ts"))
        wall = round(sum(float(x.get("duration_s") or 0.0) for x in rrows), 2)
        lead = 0.0
        if len(tss) >= 2:
            try:
                a = datetime.fromisoformat(tss[0])
                b = datetime.fromisoformat(tss[-1])
                lead = round((b - a).total_seconds(), 2)
            except Exception:  # noqa: BLE001
                lead = 0.0
        runs[rt] = {
            "lead_time_s": lead,
            "total_wall_s": wall,
            "span_start": tss[0] if tss else "",
            "span_end": tss[-1] if tss else "",
            "event_count": len(rrows),
        }

    return {
        "groups": groups,
        "runs": dict(sorted(runs.items())),
        "total_wall_s": round(sum(sum(v) for v in by_group.values()), 2),
        "total_events": len(rows),
    }


def _selftest() -> int:
    import json as _json
    import os as _os
    import tempfile as _tmp

    fails = 0
    with _tmp.TemporaryDirectory() as td:
        led = Path(td) / "tele.jsonl"
        try:
            record_event(led, {"kind": "phase_timing", "phase": "govern.mnc", "duration_s": 0.12, "run_tag": "self"})
            with phase_timer("verify.warm", ledger=led, run_tag="self", tags={"target": "t1"}):
                time.sleep(0.01)
            raised = False
            try:
                with phase_timer("native", ledger=led, run_tag="self"):
                    raise ValueError("boom")
            except ValueError:
                raised = True
            assert raised, "phase_timer swallowed the exception"
            assert led.exists() and led.stat().st_size > 0, "ledger empty — the best-effort-writer bug"
            recs = [_json.loads(l) for l in led.read_text().splitlines() if l.strip()]
            assert len(recs) == 3, f"expected 3 events, got {len(recs)}"
            assert all("ts" in r for r in recs), "ts not stamped"
            assert any(r["phase"] == "native" and r["outcome"].startswith("error:") for r in recs), "error outcome missing"
            rep = summarize_timings(led)
            assert rep["total_events"] == 3 and "govern.mnc" in rep["groups"], rep
            assert rep["runs"]["self"]["event_count"] == 3, rep
            # enabled=False must be a no-op
            led2 = Path(td) / "off.jsonl"
            record_event(led2, {"kind": "phase_timing", "phase": "x", "duration_s": 1.0}, enabled=False)
            assert not led2.exists(), "enabled=False still wrote"
            print("common.telemetry selftest: OK (record_event/phase_timer/summarize, exception-safe, gate honored)")
        except AssertionError as e:
            print(f"common.telemetry selftest FAIL: {e}")
            fails = 1
    return fails


if __name__ == "__main__":
    import sys

    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    import argparse
    import json as _json

    ap = argparse.ArgumentParser(description="Phase-timing report (time-to-insight decomposition) over any ledger.")
    ap.add_argument("ledger", help="path to a phase_timing JSONL ledger")
    ap.add_argument("--run-tag", default="")
    ap.add_argument("--group-key", default="phase")
    a = ap.parse_args()
    print(_json.dumps(summarize_timings(a.ledger, run_tag=a.run_tag, group_key=a.group_key), indent=2))
