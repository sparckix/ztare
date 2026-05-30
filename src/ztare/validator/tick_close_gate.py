"""tick_close_gate.py — Tier-1 next-tick punisher.

A fail-closed tick-close wrapper the agent must *choose* to call still
guarantees nothing (it's the gloss one level up). This makes SKIPPING it
self-defeating: the NEXT tick's already-mandatory pre-gate
(rd_tick_brief) refuses to brief a new tick unless the PREVIOUS tick was
closed via tick_close.py (owner-keyed stamp
`analytics/public/control/tick_close_state.json`).

REAL upstream fix (2026-05-16, operator: "why don't you make the real
upstream fix?"): the obligation must key on ACTUAL TICK ACTIVITY, not on
`post_tick_state.json` mtime. post_tick_state is GLOBAL and bumped by
ANY post_tick run — including verification/dogfood runs that are not
ticks — so keying on it over-tripped (punished non-ticks; forced an
advisory workaround). The true definition of "a tick happened that owes
a close" is: **the owner authored a new tick F-row in
EXPERIMENT_TRACK_RECORD.md** (a tick's irreducible artifact). So the
gate now keys on the latest owner-tagged F-row vs the owner's last
tick_close stamp:
  - No owner-tagged F-row at all ⇒ bootstrap ⇒ OK.
  - The owner's latest tick F-row id is covered by the owner's
    tick_close stamp (`stamp.tick_row` is a substring of that F-row id)
    ⇒ the most recent recorded tick WAS closed ⇒ OK.
  - The owner's latest tick F-row is NOT the one the stamp closed
    (a newer recorded tick with no subsequent close) ⇒ REFUSE.
Verification/dogfood post_tick runs create no F-row ⇒ never trip it.
post_tick_state is no longer consulted (the global-granularity residual
is eliminated at the source, not worked around).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TRACK = REPO / "research_areas/EXPERIMENT_TRACK_RECORD.md"
TICK_CLOSE_STATE = REPO / "analytics/public/control/tick_close_state.json"


def _latest_owner_frow(owner: str) -> str | None:
    """The id of the LAST (most recent — F-rows are appended) F-row in
    EXPERIMENT_TRACK_RECORD.md tagged `owner:<owner>`. None ⇒ this owner
    has authored no tick ⇒ bootstrap. A tick's irreducible artifact is
    its F-row, so this — not post_tick mtime — is 'a tick happened'."""
    if not TRACK.is_file():
        return None
    latest = None
    pat = re.compile(rf"owner:\s*{re.escape(owner)}\b")
    for ln in TRACK.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = ln.lstrip()
        if not s.startswith("| F-") or not pat.search(ln):
            continue
        m = re.match(r"\|\s*(F-[^\s|]+)", s)
        if m:
            latest = m.group(1)
    return latest


def previous_tick_closed(owner: str | None) -> tuple[bool, str]:
    """(ok, reason). ok=False ⇒ rd_tick_brief MUST refuse the new tick.
    Keys on ACTUAL tick activity (latest owner F-row) vs the owner's
    tick_close stamp — NOT post_tick_state mtime (the over-trip the
    operator told me to fix at source, not work around)."""
    if not owner:
        return False, ("tick_close_gate: no owner — pre-tick MUST be "
                       "owner-scoped (set RD_OWNER); bare runs are the "
                       "proven gloss.")
    latest = _latest_owner_frow(owner)
    if latest is None:
        return True, (f"tick_close_gate: owner '{owner}' has authored no "
                      f"tick F-row ⇒ no prior tick to close (bootstrap "
                      f"OK).")
    # C4 RETIRE CHECK — HOISTED (root-cause fix, operator-authorised
    # mid-session patch, self-Meta-Darwin'd): a CHAIN-VALID daemon-
    # signed operator-attested `tick_retire` for the CURRENT latest
    # F-row is dispositive and MUST be checked BEFORE the stale-stamp
    # dichotomy. Bug: it was inside `if not stamp:`, but a leftover
    # owner-global tick_close_state.json stamp (from a *different*
    # earlier tick) made `if not stamp:` False, so the retire path
    # was never reached and flow fell to the close-only branch which
    # cannot validate a retire and fail-closed. Hoisting does NOT
    # weaken it: still requires exact tick_row==latest + daemon-sig
    # (chain_valid) + operator_attested + counts_as_tick_close False.
    # chain_valid raise ⇒ _valid=[] ⇒ no match ⇒ falls through to the
    # original logic (no regression vs prior behaviour).
    # ROOT-CAUSE FIX (operator-authorised mid-session, self-MD'd):
    # tick_close_gate is imported under TWO layouts — `src.ztare.…`
    # (repo root on sys.path) and `ztare.…` (repo/src on sys.path, as
    # rd_tick_brief does). A hard `from src.ztare.…` import RAISES in
    # the second layout ⇒ the old `except` swallowed it ⇒ this gate
    # ALWAYS fell to "stamped_state unavailable". Try BOTH spellings.
    # Pure import-path robustness; identical module, no logic/security
    # change. Pre-existing bug (the in_legacy/tick_closed import below
    # had it too) — fixed there as well.
    def _imp_stamped():
        # RCA fix: import CANONICAL `ztare.*` FIRST. The brief, the
        # daemon, and stamped_state's readers all run with repo/src on
        # sys.path ⇒ `ztare.gates.stamped_state` is THE module. A
        # `from src.ztare.…` first-try loads a SECOND, distinct module
        # object from the same file (sys.modules key differs) whenever
        # repo-root is ALSO on sys.path (rd_tick_brief adds both) — the
        # dual-identity that made this fail launcher-dependently and
        # be non-reproducible in isolation. `src.` is ONLY a fallback
        # for the rare repo-root-only layout. Mechanized guard:
        # tests/gates/test_no_src_prefixed_imports.py.
        import importlib
        m = importlib.import_module("ztare.gates.stamped_state")
        return (m.chain_valid, m._rows, m.in_legacy, m.tick_closed)
    try:
        _chain_valid, _rows_fn, _in_legacy, _tick_closed = _imp_stamped()
        _cv, _ = _chain_valid(_rows_fn())
    except Exception:
        # #49 RCA: _imp_stamped's `import ztare.gates.stamped_state`
        # transitively hits a `src.`-prefixed import; under the
        # canonical layout (REPO/src on sys.path, REPO root NOT) that
        # raises `No module named 'src'`. The OLD bare `except: _cv=[]`
        # then SILENTLY made this gate blind to a chain-valid,
        # operator-signed `tick_retire` and emit a HARD false-refuse
        # (recurring multi-session failure). Make the import robust to
        # BOTH layouts (ensure REPO + REPO/src on sys.path, try
        # canonical then `src.` fallback). Pure import-path robustness:
        # the retire predicate below is byte-identical and the security
        # binding (operator_attested + chain_valid + daemon sig) is
        # unchanged — this only restores the gate's ability to READ
        # tamper-evident state, it does not weaken what counts.
        _cv = []
        _in_legacy = _tick_closed = None
        try:
            import sys as _sys
            import importlib as _il
            from pathlib import Path as _P
            _root = _P(__file__).resolve().parents[3]
            for _p in (str(_root), str(_root / "src")):
                if _p not in _sys.path:
                    _sys.path.insert(0, _p)
            try:
                _m = _il.import_module("ztare.gates.stamped_state")
            except Exception:
                _m = _il.import_module("src.ztare.gates.stamped_state")
            _chain_valid, _rows_fn = _m.chain_valid, _m._rows
            _in_legacy, _tick_closed = _m.in_legacy, _m.tick_closed
            _cv, _ = _chain_valid(_rows_fn())
        except Exception:
            _cv = []
            _in_legacy = _tick_closed = None
    for _r in _cv:
        if (_r.get("transition_type") == "tick_retire"
                and str(_r.get("owner")) == owner
                and str(_r.get("tick_row", "")) == str(latest)
                and _r.get("counts_as_tick_close") is False
                and _r.get("operator_attested") is True):
            return True, (
                f"⚠ DEBT BANNER — tick_close_gate: owner '{owner}' "
                f"previous tick F-row '{latest}' was NOT closed; it "
                f"was operator-RETIRED via a chain-valid daemon-"
                f"signed `tick_retire` (C4; reason="
                f"{_r.get('reason')}). UNBLOCKS the next tick for "
                f"liveness but is NOT a valid RD close and is NOT "
                f"creditable for micro_forecast/GP-230/GP-233/"
                f"surfaced_consumption. Recorded as debt, not "
                f"laundered.")
    stamp = ""
    if TICK_CLOSE_STATE.is_file():
        try:
            import json as _json
            stamp = str((_json.loads(TICK_CLOSE_STATE.read_text())
                         .get("by_owner", {}).get(owner, {})
                         .get("tick_row", "")))
        except Exception:
            stamp = ""
    if not stamp:
        # (C4 retire check is HOISTED above — runs regardless of stamp
        # state. If we reach here there is no stamp AND no chain-valid
        # retire for `latest`, so the tick is genuinely un-closed.)
        return False, (f"tick_close_gate: owner '{owner}' authored tick "
                       f"F-row '{latest}' but has NO tick_close stamp — "
                       f"the previous tick was NOT closed via "
                       f"tick_close.py. REFUSE: run `RD_OWNER={owner} "
                       f"tick_close.py --tick-row {latest} --contract-id "
                       f"<that tick's contract>` first (skipping the close "
                       f"gate is self-defeating by design). If this is a "
                       f"legacy raw-propose/audit row with NO forecast "
                       f"contract (uncloseable by H4), the OPERATOR may "
                       f"run admin_retire_uncloseable_tick.py "
                       f"(operator-gated; debt, not a close).")
    # The stamp's --tick-row was a substring of the F-row id it closed.
    if stamp in latest:
        # READER-REPOINT (GP-241, FAIL-CLOSED per cold GPT-5.5 must-fix):
        # tick_close_state.json is AGENT-WRITABLE ⇒ a skipped/forged
        # local stamp could fake "closed". NO ts/date heuristic (the
        # fail-open hole). Rule: the latest F-row is OK iff it is in the
        # verified frozen pre-cutover legacy manifest (legitimate
        # history) OR an un-forgeable daemon official closure backs it.
        # A post-cutover / no-date / forged id not in the manifest and
        # not daemon-stamped ⇒ REFUSE (fail-closed).
        try:
            # dual-path: reuse the resolved fns (src. import RAISES
            # under the `ztare.*` layout — the original bug here).
            if _in_legacy is None or _tick_closed is None:
                _, _, in_legacy, tick_closed = _imp_stamped()
            else:
                in_legacy, tick_closed = _in_legacy, _tick_closed
            if in_legacy(latest):
                return True, (f"tick_close_gate: owner '{owner}' latest "
                              f"F-row '{latest}' is in the frozen "
                              f"pre-cutover legacy manifest ⇒ OK "
                              f"(legitimate history).")
            # COLD-PASS MANDATORY REPAIR (2026-05-17, bc0no0wng): the
            # prior acceptance — ANY signed row whose goal/transition_
            # text merely SUBSTRING-MENTIONS the stamp/F-row id — was a
            # forgeable "previous tick closed" decision (fake .md F-row
            # + forged tick_close_state.json + any non-close stamped
            # row that mentions the id ⇒ next tick unblocked). Replaced
            # with EXACT signed-close semantics: a chain-valid,
            # daemon-SIGNED row, transition_type=='tick_close',
            # close_verified True, tick_id==latest. No substring path.
            if tick_closed(latest):
                return True, (f"tick_close_gate: owner '{owner}' latest "
                              f"F-row '{latest}' has an EXACT "
                              f"daemon-signed tick_close transition "
                              f"(close_verified + tick_id-bound) ⇒ OK.")
            return False, (
                f"tick_close_gate READER-REPOINT (fail-closed): owner "
                f"'{owner}' F-row '{latest}' is NOT in the frozen "
                f"pre-cutover legacy manifest AND has NO exact "
                f"daemon-signed `tick_close` transition (close_verified "
                f"+ tick_id-bound) — substring-mention no longer counts. "
                f"REFUSE: close via the daemon-owned tick_close "
                f"transaction (`tick_close.py --tick-row {latest} "
                f"--contract-id <c> --witnesses-json '<discharge>'`).")
        except Exception:
            # stamped_state unreadable ⇒ FAIL-CLOSED (was: degrade to
            # local stamp = fail-open; cold-fix flips this).
            return False, (
                f"tick_close_gate: stamped_state unavailable ⇒ cannot "
                f"verify an un-forgeable closure for '{latest}'. "
                f"FAIL-CLOSED (refuse) rather than trust the agent-"
                f"writable local stamp.")
    return False, (f"tick_close_gate: owner '{owner}' latest tick F-row "
                   f"'{latest}' is NEWER than the last closed tick "
                   f"(stamp closed '{stamp}') — a recorded tick was not "
                   f"closed. REFUSE: `RD_OWNER={owner} tick_close.py "
                   f"--tick-row {latest} --contract-id <its contract>` "
                   f"first.")


def main() -> int:
    import os
    import sys
    owner = (sys.argv[1] if len(sys.argv) > 1 else None) \
        or os.environ.get("RD_OWNER")
    ok, why = previous_tick_closed(owner)
    print(("OK: " if ok else "REFUSE: ") + why)
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
