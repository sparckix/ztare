"""LeanMill phase-timing — a thin leanmill VIEW over the shared `common.telemetry` interface.

This is NOT a parallel telemetry implementation (that would be the dup-sibling/frankenstein anti-pattern). The
emit + stopwatch + read-model live ONCE in `ztare.common.telemetry` and are shared with autoresearch; this module
only adds the leanmill-specific surface: the ledger path, the `ZTARE_LEANMILL_PHASE_TIMING` gate, and the leanmill
phase vocabulary. Improving the shared core (e.g. a richer read-model) benefits both lanes at once.

WHY PHASE TIMING. `run_diagnostics` records per-MOVE `wallclock_s`; `factory_intelligence` projects per-STATION
lead/cycle time from the WorkItem queue. Neither answers "*where* did the wall-clock go inside one campaign?" —
formalize vs pool vs native vs warm/cold compile vs govern(mnc/kernel/axiom) vs decompose vs bank. That
decomposition turns a raw wall-time into an actionable "time to insight" (it is how the cold-`lake env lean` MNC
on the governance path was found).

Phase-name convention (dotted, coarse.fine): `formalize`, `pool`, `native`, `verify.warm`, `verify.cold`,
`govern.mnc`, `govern.kernel`, `govern.axiom`, `decompose`, `bank`, `leaf.dispatch`. Keep new names in this
vocabulary so the read-model groups cleanly.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ztare.common.telemetry import (
    phase_timer as _shared_phase_timer,
    record_event as _shared_record_event,
    summarize_timings as _shared_summarize_timings,
)

# Repo-relative default (PORTABLE — no operator path baked in): src/ztare/leanmill/phase_timing.py
# -> parents[3] is the repo root. Override with ZTARE_LEANMILL_PHASE_TIMING_LEDGER for tests / scratch isolation.
_LEDGER_DEFAULT_REL = "analytics/public/queries/solver_lane_phase_timings.jsonl"


def _enabled() -> bool:
    """Default-on; `ZTARE_LEANMILL_PHASE_TIMING=0` reverts to no emission (byte-parity for the solve)."""
    return os.environ.get("ZTARE_LEANMILL_PHASE_TIMING", "1") != "0"


def ledger_path() -> Path:
    p = os.environ.get("ZTARE_LEANMILL_PHASE_TIMING_LEDGER")
    if p:
        return Path(p)
    return Path(__file__).resolve().parents[3] / _LEDGER_DEFAULT_REL


def _tags(target: str, extra: "Optional[dict]") -> dict:
    t: dict = {}
    if target:
        t["target"] = target
    if extra:
        t.update(extra)
    return t


def phase_timer(phase: str, *, target: str = "", run_tag: str = "", extra: "Optional[dict]" = None):
    """`with phase_timer('govern.mnc', target=name):` — times the block via the shared core, writing to the
    leanmill ledger under the `ZTARE_LEANMILL_PHASE_TIMING` gate. Records on exception too (re-raises)."""
    return _shared_phase_timer(
        phase,
        ledger=ledger_path(),
        run_tag=run_tag or os.environ.get("ZTARE_SOLVER_RUN_TAG", "") or "",
        tags=_tags(target, extra) or None,
        enabled=_enabled(),
    )


def record_phase(
    phase: str,
    duration_s: float,
    *,
    target: str = "",
    run_tag: str = "",
    outcome: str = "",
    extra: "Optional[dict]" = None,
) -> None:
    """Append one phase-timing event (for code paths that measure their own duration)."""
    ev = {
        "kind": "phase_timing",
        "phase": str(phase),
        "duration_s": round(float(duration_s), 4),
        "run_tag": run_tag or os.environ.get("ZTARE_SOLVER_RUN_TAG", "") or "",
        "outcome": outcome or "",
    }
    tg = _tags(target, extra)
    if tg:
        ev["tags"] = tg
    _shared_record_event(ledger_path(), ev, enabled=_enabled())


def summarize_phase_timings(*, run_tag: str = "", ledger: "Optional[str | Path]" = None) -> dict:
    """Phase-decomposed cycle-time report for leanmill (delegates to the shared read-model). The shared core's
    `groups` key is surfaced as `phases` here for leanmill-domain clarity."""
    rep = _shared_summarize_timings(Path(ledger) if ledger else ledger_path(), run_tag=run_tag, group_key="phase")
    rep = dict(rep)
    rep["phases"] = rep.pop("groups", {})
    return rep


# ── Campaign cycle-time (the factory "time-to-insight on closures" metric) ─────────────────────────────────────
# Per-phase timing answers "where did the wall go inside one campaign"; this answers "how LONG until a campaign
# CLOSED a rung, and how much did it COST" — segmented by DOMAIN (math vs non-math formalization) so the avg
# time-to-closure of, e.g., corporate/legal faithfulness work is reportable distinctly. factory_intelligence
# surfaces it; the computation lives here (next to the phase read-model) and takes the solver attempts ledger as
# INJECTED rows so this module stays storage-agnostic + hermetically testable.
_CAMPAIGN_PHASE = "campaign"


def record_campaign(domain: str, *, run_tag: str = "", target: str = "") -> None:
    """Stamp a run-level `campaign` marker carrying the DOMAIN label (e.g. 'math', 'formalization-nonmath') so
    `summarize_campaign_cycle_time` can segment time-to-closure by domain. ONE canonical emitter — callers must
    NOT hand-roll the marker event. Emitted once at campaign start; duration is irrelevant (the marker exists for
    its `domain` tag). Best-effort + gate-honored (byte-parity when phase timing is off)."""
    record_phase(_CAMPAIGN_PHASE, 0.0, target=target, run_tag=run_tag,
                 extra={"domain": (domain or "unspecified").strip() or "unspecified"})


def _epoch(ts) -> "Optional[float]":
    """Parse an attempt timestamp (ISO-8601 string OR epoch number) → epoch seconds; None if unparseable."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    s = str(ts).strip()
    if not s:
        return None
    try:
        return float(s)                                   # bare epoch string
    except ValueError:
        pass
    try:
        from datetime import datetime
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:  # noqa: BLE001
        return None


def _pct(xs: "list[float]", q: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return round(float(s[i]), 2)


def _domains_from_ledger(ledger) -> "dict[str, str]":
    """run_tag → domain, from the `campaign` marker events in the phase ledger (last marker wins)."""
    out: "dict[str, str]" = {}
    import json as _json
    try:
        p = Path(ledger) if ledger else ledger_path()
        if not p.exists():
            return out
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or '"campaign"' not in line:
                continue
            try:
                ev = _json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if ev.get("kind") == "phase_timing" and ev.get("phase") == _CAMPAIGN_PHASE:
                rt = str(ev.get("run_tag") or "")
                dom = str((ev.get("tags") or {}).get("domain") or "").strip()
                if rt:
                    out[rt] = dom or "unspecified"
    except Exception:  # noqa: BLE001
        return out
    return out


def _campaign_starts_from_ledger(ledger) -> "dict[str, float]":
    """run_tag → campaign START epoch, from the EARLIEST `campaign` marker in the phase ledger. record_campaign
    stamps this marker at RUN START — BEFORE theory-consolidation + formalize — so it is the honest launch time.
    The first solve ATTEMPT is ~theory+formalize LATER for a theory-building run, so measuring time-to-closure
    from the first attempt UNDER-reports the real launch→closure wall (2026-07-01 RCA: BFT read 207s vs the true
    ~804s; VCG 362/730s vs 1335s). Mirrors `_domains_from_ledger`; `ts` parsed via `_epoch`."""
    out: "dict[str, float]" = {}
    import json as _json
    try:
        p = Path(ledger) if ledger else ledger_path()
        if not p.exists():
            return out
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or '"campaign"' not in line:
                continue
            try:
                ev = _json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if ev.get("kind") == "phase_timing" and ev.get("phase") == _CAMPAIGN_PHASE:
                rt = str(ev.get("run_tag") or "")
                t = _epoch(ev.get("ts"))
                if rt and t is not None and (rt not in out or t < out[rt]):
                    out[rt] = t
    except Exception:  # noqa: BLE001
        return out
    return out


def _consolidate_from_ledger(ledger) -> "dict[str, float]":
    """run_tag → total `consolidate` phase seconds (the theory-consolidation dispatch). Splits time_to_formalize
    into consolidate + statement-formalize so the P0 shows where the formalize window went; consolidation is the
    dominant, now-auto-skipped rerun cost (an auto-skipped rerun records ~0). Mirrors `_campaign_starts_from_ledger`."""
    out: "dict[str, float]" = {}
    import json as _json
    try:
        p = Path(ledger) if ledger else ledger_path()
        if not p.exists():
            return out
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or '"consolidate"' not in line:
                continue
            try:
                ev = _json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if ev.get("kind") == "phase_timing" and ev.get("phase") == "consolidate":
                rt = str(ev.get("run_tag") or "")
                if rt:
                    out[rt] = round(out.get(rt, 0.0) + float(ev.get("duration_s") or 0.0), 2)
    except Exception:  # noqa: BLE001
        return out
    return out


def campaign_family(run_tag: str) -> str:
    """Group run_tags that are RE-RUNS of the same campaign (`_v2`/`_v3`, `_dbg`) under one family, so a campaign
    worked across several runs gets a SINGLE P0 view (e.g. `amm_cpmm`, `amm_cpmm_v2`, `amm_cpmm_v3` → `amm_cpmm`).
    Strips a trailing `_v<N>` or `_dbg<N>` suffix; a tag with no such suffix is its own family."""
    import re as _re
    return _re.sub(r"_(v\d+|dbg\d*)$", "", run_tag or "") or (run_tag or "")


def summarize_campaign_cycle_time(attempt_rows, *, ledger: "Optional[str | Path]" = None) -> dict:
    """Per-campaign TIME-TO-CLOSURE read model (the factory 'time to insight on closures' metric).

    `attempt_rows`: iterable of mappings with `run_tag`, `attempt_at` (ISO str or epoch), `outcome`, `ratified`,
    `wallclock_s` — the solver attempts ledger, passed IN (storage-agnostic, hermetically testable). A CLOSURE is
    `outcome == 'closed'` (a kernel-ratified rung). Per campaign (run_tag) the WALL splits into two scoped numbers
    that SUM (the world-class P0 timing, 2026-07-01): **time_to_formalize** = launch(`campaign` marker) → first
    solve attempt (preflight + theory-consolidation + statement formalize + firewall) and **time_to_close** (the
    PROVING window) = first attempt → closure. **wall** = launch → closure = formalize + prove (== phase-ledger
    lead). The attempts ledger has NO row before the solve phase, so `closure − first_attempt` alone is only the
    proving window — measuring it AS the time-to-closure silently drops the formalize minutes (the recurring
    under-report). `time_to_closure_s` is kept as a backward-compat alias of the proving window. cost-to-closure =
    cumulative wallclock_s up to the closure. Segmented by `domain` (the `campaign` markers). Pure read."""
    doms = _domains_from_ledger(ledger)
    starts = _campaign_starts_from_ledger(ledger)   # run_tag → LAUNCH epoch (marker); enables the formalize/prove split
    consolidates = _consolidate_from_ledger(ledger)   # run_tag → consolidate seconds; splits the formalize window
    by_run: "dict[str, list[dict]]" = {}
    for r in attempt_rows or []:
        g = r if isinstance(r, dict) else dict(r)
        rt = str(g.get("run_tag") or "")
        if rt:
            by_run.setdefault(rt, []).append(g)

    campaigns: "dict[str, dict]" = {}
    for rt, rows in by_run.items():
        timed = [(_epoch(g.get("attempt_at")), g) for g in rows]
        timed = [(t, g) for (t, g) in timed if t is not None]
        if not timed:
            continue
        timed.sort(key=lambda tg: tg[0])
        first_attempt = timed[0][0]
        # THE FIX (2026-07-01 RCA — recurring under-report): the attempts ledger has NO row before the SOLVE
        # phase, so `closure − first_attempt` is only the PROVING window — it silently excludes theory-
        # consolidation + statement-formalize (~minutes for a theory-building run). The honest launch is the
        # `campaign` marker (stamped at run start). Split into three scoped numbers that SUM, rather than one
        # ambiguous "time-to-closure": formalize (launch→first attempt) + prove (first attempt→closure) = wall.
        _launch = starts.get(rt)
        launch = _launch if (_launch is not None and _launch <= first_attempt) else first_attempt  # fall back: old runs / synthetic tests
        closures = [(t, g) for (t, g) in timed if str(g.get("outcome")) == "closed"]
        ttc = [round(t - first_attempt, 2) for (t, _g) in closures]        # PROVING window (first attempt → closure)
        wall = [round(t - launch, 2) for (t, _g) in closures]             # WALL (launch → closure) = formalize + prove
        t_formalize = round(first_attempt - launch, 2)                    # FORMALIZE (launch → first attempt)
        ctc = [round(sum(float(g.get("wallclock_s") or 0.0) for (t, g) in timed if t <= ct), 2)
               for (ct, _g) in closures]
        n = len(timed)
        n_failed = sum(1 for (_t, g) in timed if str(g.get("outcome")) in ("failed", "failed_compile"))
        def _stat(xs):
            return {"first": xs[0] if xs else None,
                    "mean": round(sum(xs) / len(xs), 2) if xs else None,
                    "p50": _pct(xs, 0.5) if xs else None, "p95": _pct(xs, 0.95) if xs else None}
        campaigns[rt] = {
            "domain": doms.get(rt, "unspecified"),
            "span_s": round(timed[-1][0] - launch, 2),                    # honest elapsed: launch → last attempt
            "attempts": n,
            "closures": len(closures),
            "time_to_formalize_s": t_formalize,                          # launch → first attempt (theory + statement + firewall)
            "consolidate_s": consolidates.get(rt, 0.0),                  # of which: theory-consolidation dispatch (auto-skipped on reruns)
            "statement_formalize_s": round(max(0.0, t_formalize - consolidates.get(rt, 0.0)), 2),  # of which: statement formalize + firewall
            "time_to_close_s": _stat(ttc),                              # PROVING window (first attempt → closure) — clear name
            "wall_s": _stat(wall),                                      # launch → closure (headline; == phase-ledger lead)
            "time_to_closure_s": _stat(ttc),                           # BACKWARD-COMPAT alias of time_to_close_s (proving window)
            "cost_to_closure_s": {
                "first": ctc[0] if ctc else None,
                "mean": round(sum(ctc) / len(ctc), 2) if ctc else None,
                "total_wall_s": round(sum(float(g.get("wallclock_s") or 0.0) for (_t, g) in timed), 2),
            },
            "yield": {"closed": len(closures), "failed": n_failed, "other": n - len(closures) - n_failed},
        }

    by_domain: "dict[str, dict]" = {}
    for rt, c in campaigns.items():
        agg = by_domain.setdefault(c["domain"], {"campaigns": 0, "closures": 0, "_ttc": []})
        agg["campaigns"] += 1
        agg["closures"] += c["closures"]
        if c["time_to_closure_s"]["mean"] is not None:
            agg["_ttc"].append(c["time_to_closure_s"]["mean"])
    for _d, agg in by_domain.items():
        ttcs = agg.pop("_ttc")
        agg["avg_time_to_closure_s"] = round(sum(ttcs) / len(ttcs), 2) if ttcs else None

    # by_campaign_family: ONE P0 view per campaign across its re-runs (v1/v2/v3). Each family lists its member
    # runs with their role-relevant numbers (so prove-cost vs clean-close-cost vs a discarded attempt stay
    # visible — never a blob) plus combined totals. This is what makes a multi-run milestone a single cert.
    by_family: "dict[str, dict]" = {}
    for rt, c in campaigns.items():
        fam = campaign_family(rt)
        agg = by_family.setdefault(fam, {"members": {}, "combined_wall_s": 0.0, "combined_closures": 0, "runs": 0})
        agg["members"][rt] = {
            "domain": c["domain"],
            "attempts": c["attempts"],
            "closures": c["closures"],
            "total_wall_s": c["cost_to_closure_s"]["total_wall_s"],
            "first_time_to_closure_s": c["time_to_closure_s"]["first"],
        }
        agg["combined_wall_s"] = round(agg["combined_wall_s"] + c["cost_to_closure_s"]["total_wall_s"], 2)
        agg["combined_closures"] += c["closures"]
        agg["runs"] += 1

    return {
        "schema": "leanmill-campaign-cycle-time-v1",
        "campaigns": campaigns,
        "by_domain": by_domain,
        "by_campaign_family": by_family,
        "campaign_count": len(campaigns),
    }


def _selftest() -> int:
    import json as _json
    import tempfile as _tmp

    fails = 0
    with _tmp.TemporaryDirectory() as td:
        led = Path(td) / "pt.jsonl"
        os.environ["ZTARE_LEANMILL_PHASE_TIMING_LEDGER"] = str(led)
        os.environ["ZTARE_LEANMILL_PHASE_TIMING"] = "1"
        try:
            record_phase("govern.mnc", 0.12, target="t1", run_tag="self", outcome="ok")
            with phase_timer("verify.warm", target="t1", run_tag="self"):
                pass
            assert led.exists() and led.stat().st_size > 0, "ledger empty — best-effort-writer bug"
            recs = [_json.loads(l) for l in led.read_text().splitlines() if l.strip()]
            assert len(recs) == 2, f"expected 2 events, got {len(recs)}"
            rep = summarize_phase_timings(ledger=led)
            assert "govern.mnc" in rep["phases"] and rep["total_events"] == 2, rep
            # gate off ⇒ no emission
            os.environ["ZTARE_LEANMILL_PHASE_TIMING"] = "0"
            record_phase("native", 1.0, run_tag="self")
            recs2 = [l for l in led.read_text().splitlines() if l.strip()]
            assert len(recs2) == 2, "gate=0 still wrote"
            # campaign cycle-time: domain stamp + time/cost-to-closure from INJECTED attempt rows (gate back ON)
            os.environ["ZTARE_LEANMILL_PHASE_TIMING"] = "1"
            record_campaign("formalization-nonmath", run_tag="self", target="t1")
            rows = [
                {"run_tag": "self", "attempt_at": 1000.0, "outcome": "failed", "ratified": None, "wallclock_s": 10.0},
                {"run_tag": "self", "attempt_at": 1100.0, "outcome": "closed", "ratified": 1, "wallclock_s": 90.0},
            ]
            cct = summarize_campaign_cycle_time(rows, ledger=led)
            assert cct["campaigns"]["self"]["domain"] == "formalization-nonmath", cct
            assert cct["campaigns"]["self"]["time_to_closure_s"]["first"] == 100.0, cct   # 1100 − 1000
            assert cct["campaigns"]["self"]["cost_to_closure_s"]["first"] == 100.0, cct   # 10 + 90 cumulative
            assert cct["campaigns"]["self"]["closures"] == 1 and cct["campaigns"]["self"]["yield"]["failed"] == 1, cct
            assert cct["by_domain"]["formalization-nonmath"]["avg_time_to_closure_s"] == 100.0, cct
            # campaign-FAMILY rollup: re-runs of one campaign (v2/v3) join into a SINGLE P0 view, members visible
            assert campaign_family("amm_cpmm_v3") == "amm_cpmm" and campaign_family("amm_cpmm") == "amm_cpmm", "family strip"
            fam_rows = [
                {"run_tag": "amm_cpmm_v2", "attempt_at": 0.0, "outcome": "closed", "wallclock_s": 240.0},
                {"run_tag": "amm_cpmm_v3", "attempt_at": 0.0, "outcome": "closed", "wallclock_s": 60.0},
            ]
            fam = summarize_campaign_cycle_time(fam_rows)["by_campaign_family"]
            assert "amm_cpmm" in fam and fam["amm_cpmm"]["runs"] == 2, fam
            assert set(fam["amm_cpmm"]["members"]) == {"amm_cpmm_v2", "amm_cpmm_v3"}, fam
            assert fam["amm_cpmm"]["combined_wall_s"] == 300.0 and fam["amm_cpmm"]["combined_closures"] == 2, fam
            # ISO-timestamp parsing (the attempts-DB format) lands in the same bucket
            assert _epoch("2026-06-24T20:25:59+00:00") is not None, "ISO attempt_at must parse"
            print("leanmill.phase_timing selftest: OK (adapter delegates to common.telemetry, gate honored, "
                  "campaign cycle-time + domain segmentation)")
        except AssertionError as e:
            print(f"leanmill.phase_timing selftest FAIL: {e}")
            fails = 1
        finally:
            os.environ.pop("ZTARE_LEANMILL_PHASE_TIMING_LEDGER", None)
            os.environ["ZTARE_LEANMILL_PHASE_TIMING"] = "1"
    return fails


if __name__ == "__main__":
    import sys

    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    import argparse
    import json as _json

    ap = argparse.ArgumentParser(description="LeanMill phase-timing report (time-to-insight decomposition).")
    ap.add_argument("--run-tag", default="")
    ap.add_argument("--ledger", default="")
    a = ap.parse_args()
    print(_json.dumps(summarize_phase_timings(run_tag=a.run_tag, ledger=(a.ledger or None)), indent=2))
