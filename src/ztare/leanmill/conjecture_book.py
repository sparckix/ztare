#!/usr/bin/env python3
"""Conjecture book (#124, mathematician leg) — OPEN conjectures as typed WorkItems (kind="conjecture")
accumulating EVIDENCE EVENTS append-only, keyed by the CANONICAL statement key (`proof_cache.
normalize_statement` — the same key the proof cache and no-good store collapse on, ONE source of truth).

What it is: the ledger of "what we believe and why" — each conjecture's row plus its event stream
(`instance_confirmed` from the instances-first gate, `special_case_proven` when a model-case rung
ratifies — the exp-rungs-are-evidence-for-the-residue-crux pattern, `falsification_failed` when a
falsify probe came back empty, `counterexample_found` as the honest negative). Rendered into leaf/planner
prompts as comment-inert evidence tallies.

What it is NOT (the route-don't-one-off rule): a credence CALCULATOR. The book stores events and renders
tallies; numeric CREDENCE is stamped only through `stamp_credence` by the forecast POOL (the canonical
diverse-forecaster market, via `forecast_pool_bridge`) — this module never computes a probability, so a
hand-rolled single-perspective "market" can't creep in. Evidence ≠ proof; the kernel stays the arbiter.

  python -m ztare.leanmill.conjecture_book --selftest
"""
from __future__ import annotations

import json
from pathlib import Path

from ztare.leanmill.contracts.work_items import WorkItem

CONJECTURE_BOOK_LEDGER = "analytics/public/queries/conjecture_book.jsonl"   # append-only, repo-relative

EVENT_KINDS = (
    "instance_confirmed",     # instances-first gate: concrete instances evaluated TRUE (positive dual)
    "counterexample_found",   # instances-first gate / looks_false: a concrete refuting assignment
    "special_case_proven",    # a kernel-RATIFIED rung that is a model case of this conjecture
    "falsification_failed",   # a falsify probe ran and found nothing (weak positive evidence)
    "resolved_proven",        # the conjecture itself ratified (it leaves the open set)
    "resolved_refuted",       # kernel-proved ¬G (it leaves the open set)
    "credence_stamp",         # forecast-POOL credence (stamp_credence only — never computed here)
)


def statement_key(statement: str) -> str:
    """The canonical key — REUSE the proof-cache normalizer (decl-name- + whitespace-agnostic) so a
    conjecture, its cached proof, and its no-goods all collapse to the same identity."""
    from ztare.leanmill.solver.proof_cache import normalize_statement
    return normalize_statement(statement)


def _ledger_path(repo_root: "Path | str") -> Path:
    return Path(repo_root) / CONJECTURE_BOOK_LEDGER


def _rows(led: Path) -> "list[dict]":
    try:
        return [json.loads(l) for l in led.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return []


def register(statement: str, *, residual_class: str = "", campaign: str = "",
             repo_root: "Path | str", ts: str = "") -> str:
    """Add an OPEN conjecture (idempotent by canonical key — re-registering is a no-op). Returns the key."""
    key = statement_key(statement)
    led = _ledger_path(repo_root)
    for r in _rows(led):
        if r.get("key") == key and r.get("item") is not None:
            return key
    item = WorkItem(kind="conjecture", statement=statement.strip(),
                    residual_class=residual_class, campaign=campaign)
    led.parent.mkdir(parents=True, exist_ok=True)
    with led.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"key": key, "item": item.model_dump(), "ts": ts}) + "\n")
    return key


def record_event(statement: str, event: str, *, evidence: str = "", run_tag: str = "",
                 repo_root: "Path | str", ts: str = "", auto_register: bool = True) -> str:
    """Append an evidence event for a conjecture (by statement; key derived canonically). Unknown event
    kinds are rejected loudly — the event vocabulary is the contract."""
    if event not in EVENT_KINDS:
        raise ValueError(f"unknown conjecture-book event {event!r} (allowed: {EVENT_KINDS})")
    key = statement_key(statement)
    led = _ledger_path(repo_root)
    if auto_register and not any(r.get("key") == key and r.get("item") is not None for r in _rows(led)):
        register(statement, repo_root=repo_root, ts=ts)
    with led.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"key": key, "event": event, "evidence": evidence[:400],
                            "run_tag": run_tag, "ts": ts}) + "\n")
    return key


def stamp_credence(statement: str, credence: float, *, source: str, repo_root: "Path | str",
                   ts: str = "") -> str:
    """The forecast-POOL seam: stamp an externally-aggregated credence. `source` must name the pool
    aggregation that produced it (fail-loud on empty — an unsourced number is exactly the hand-rolled
    forecaster this module refuses to be)."""
    if not (source or "").strip():
        raise ValueError("stamp_credence requires a non-empty source (the forecast-pool aggregation ref)")
    cred = min(1.0, max(0.0, float(credence)))   # clamp to [0,1] (2026-06-13 audit) — rendered verbatim into prompts
    return record_event(statement, "credence_stamp",
                        evidence=json.dumps({"credence": cred, "source": source}),
                        repo_root=repo_root, ts=ts)


def route_credence_via_pool(statement: str, *, repo_root: "Path | str", ts: str = "") -> "float | None":
    """CLOSE the credence seam through the CANONICAL forecast POOL (route-don't-one-off): emit a micro
    contract for this conjecture (the pool's diverse external forecasters bet on it), read the
    aggregate consensus, stamp it via `stamp_credence`. Returns the credence, or None (pool absent /
    no forecasts landed yet / gate off) — best-effort, never breaks a campaign.

    OPT-IN (`ZTARE_LEANMILL_CONJECTURE_POOL=1`, default OFF): each emission wakes warm forecaster
    dispatches — real token cost per conjecture, so a campaign flips it deliberately (the A/B knob),
    unlike the free-evidence events which are always on."""
    import os
    if os.environ.get("ZTARE_LEANMILL_CONJECTURE_POOL", "0") != "1":
        return None
    try:
        from ztare.leanmill.solver import forecast_pool_bridge as _fpb
        if not _fpb.pool_available():
            return None
        cid = _fpb.emit_micro_contract(f"conjecture::{statement_key(statement)[:24]}", statement)
        if not cid:
            return None
        agg = _fpb.read_aggregate(cid)
        if agg is None:
            return None
        stamp_credence(statement, float(agg), source=f"forecast_pool:{cid}", repo_root=repo_root, ts=ts)
        return float(agg)
    except Exception:  # noqa: BLE001 — the pool is an external system; absence is not an error here
        return None


def summarize(repo_root: "Path | str") -> "dict[str, dict]":
    """Fold the ledger: {key: {statement, residual_class, campaign, tallies, credence, open}}."""
    out: "dict[str, dict]" = {}
    for r in _rows(_ledger_path(repo_root)):
        key = r.get("key") or ""
        if not key:
            continue
        ent = out.setdefault(key, {"statement": "", "residual_class": "", "campaign": "",
                                   "tallies": {}, "credence": None, "open": True})
        if r.get("item") is not None:
            it = r["item"] or {}
            ent["statement"] = it.get("statement") or ent["statement"]
            ent["residual_class"] = it.get("residual_class") or ent["residual_class"]
            ent["campaign"] = it.get("campaign") or ent["campaign"]
        ev = r.get("event")
        if ev:
            ent["tallies"][ev] = ent["tallies"].get(ev, 0) + 1
            if ev == "credence_stamp":
                try:
                    ent["credence"] = json.loads(r.get("evidence") or "{}")
                except ValueError:
                    pass
            if ev in ("resolved_proven", "resolved_refuted"):
                ent["open"] = False
    return out


def render_block(statement: str, repo_root: "Path | str") -> str:
    """Comment-inert prompt block for THIS goal's book entry (empty string if it has none) — the same
    inform-never-block contract as no_good_store.prompt_block."""
    ent = summarize(repo_root).get(statement_key(statement))
    if not ent or not ent.get("tallies"):
        return ""
    t = ent["tallies"]
    parts = [f"{n}× {k}" for k, n in sorted(t.items()) if k != "credence_stamp"]
    lines = ["-- CONJECTURE BOOK (recorded evidence on THIS statement — evidence ≠ proof; the kernel arbitrates):",
             "--   " + "; ".join(parts)]
    cred = ent.get("credence") or {}
    if cred.get("credence") is not None:
        lines.append(f"--   forecast-pool credence: {cred['credence']} (source: {cred.get('source', '?')})")
    if t.get("counterexample_found"):
        lines.append("--   WARNING: a concrete counterexample is recorded — treat the statement as LIKELY"
                     " FALSE; consider the corrected statement / STATEMENT-FALSE marker.")
    return "\n".join(lines)


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    td = Path(tempfile.mkdtemp(prefix="cbk_"))
    stmt = "theorem p1_residue (n : ℕ) : n <= n * n + 1 := by sorry"
    k1 = register(stmt, residual_class="library_gap:residue", campaign="p1n1_v7",
                  repo_root=td, ts="2026-06-12T00:00:00+00:00")
    k2 = register("theorem  p1_residue (n : ℕ) :  n <= n * n + 1 := by sorry", repo_root=td)  # ws-variant
    ok("register idempotent under the canonical key (ws/name-agnostic)",
       k1 == k2 and sum(1 for r in _rows(_ledger_path(td)) if r.get("item")) == 1)
    record_event(stmt, "instance_confirmed", evidence="5 instances: n=0,1,2,3,5", run_tag="t", repo_root=td)
    record_event(stmt, "instance_confirmed", evidence="re-confirmed", repo_root=td)
    record_event(stmt, "special_case_proven", evidence="exp-rung cert 5f78c94e", repo_root=td)
    s = summarize(td)[k1]
    ok("events tally per canonical key",
       s["tallies"] == {"instance_confirmed": 2, "special_case_proven": 1} and s["open"] is True)
    try:
        record_event(stmt, "vibes_good", repo_root=td)
        ok("unknown event kind rejected loudly", False)
    except ValueError:
        ok("unknown event kind rejected loudly", True)
    try:
        stamp_credence(stmt, 0.7, source="", repo_root=td)
        ok("unsourced credence rejected (no hand-rolled forecaster)", False)
    except ValueError:
        ok("unsourced credence rejected (no hand-rolled forecaster)", True)
    stamp_credence(stmt, 0.62, source="forecast_pool:p1n1_v7:agg7", repo_root=td)
    ok("pool credence stamped + folded", summarize(td)[k1]["credence"]["credence"] == 0.62)
    blk = render_block(stmt, td)
    ok("render is comment-inert evidence (inform, never block)",
       blk.startswith("-- CONJECTURE BOOK") and "2× instance_confirmed" in blk and "0.62" in blk
       and all(l.startswith("--") for l in blk.splitlines()))
    ok("render empty for an unknown statement", render_block("theorem other : True := by sorry", td) == "")
    record_event(stmt, "counterexample_found", evidence="n=-1 (over ℤ-misread)", repo_root=td)
    ok("counterexample renders the LIKELY-FALSE warning", "LIKELY" in render_block(stmt, td))
    record_event(stmt, "resolved_proven", evidence="ratified cert", repo_root=td)
    ok("resolution closes the entry", summarize(td)[k1]["open"] is False)
    # pool-credence routing (hermetic: bridge monkeypatched; gate honored)
    import os as _os
    stmt2 = "theorem crux2 (n : ℕ) : n = n := by sorry"
    ok("pool route: gate OFF (default) ⇒ None, nothing stamped",
       route_credence_via_pool(stmt2, repo_root=td) is None)
    from ztare.leanmill.solver import forecast_pool_bridge as _fpb
    _sv_pa, _sv_em, _sv_ra = _fpb.pool_available, _fpb.emit_micro_contract, _fpb.read_aggregate
    _sv_env = _os.environ.get("ZTARE_LEANMILL_CONJECTURE_POOL")
    try:
        _os.environ["ZTARE_LEANMILL_CONJECTURE_POOL"] = "1"
        _fpb.pool_available = lambda: True
        _fpb.emit_micro_contract = lambda target, goal, **kw: "cbk_test_cid"
        _fpb.read_aggregate = lambda cid, **kw: 0.41
        cr = route_credence_via_pool(stmt2, repo_root=td, ts="2026-06-13T01:30:00+00:00")
        ent = summarize(td)[statement_key(stmt2)]
        ok("pool route: aggregate stamped through the canonical seam (source names the contract)",
           cr == 0.41 and ent["credence"]["credence"] == 0.41
           and ent["credence"]["source"] == "forecast_pool:cbk_test_cid")
        _fpb.read_aggregate = lambda cid, **kw: None
        ok("pool route: no aggregate yet ⇒ None, no stale stamp",
           route_credence_via_pool(stmt2, repo_root=td) is None)
    finally:
        _fpb.pool_available, _fpb.emit_micro_contract, _fpb.read_aggregate = _sv_pa, _sv_em, _sv_ra
        _os.environ.pop("ZTARE_LEANMILL_CONJECTURE_POOL", None) if _sv_env is None else _os.environ.__setitem__("ZTARE_LEANMILL_CONJECTURE_POOL", _sv_env)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
