#!/usr/bin/env python3
"""Per-run INTERNAL STANDARDS (#116, from the apparatus isomorphism run — analytical chemistry's isotope
dilution): every run carries a known-POSITIVE and a known-NEGATIVE control THROUGH THE SAME pipeline, so each
run's closures are traceable to an instrument that was demonstrably alive AND demonstrably refusing cheats
IN THAT RUN — not certified post-hoc by archaeology (the recurring dead-instrument disease).

  • POSITIVE standard — a trivially-provable probe through the REAL compile/verify path: must CLOSE.
    Failure ⇒ the prover instrument is dead (toolchain drift, dead REPL, broken carrier).
  • NEGATIVE standard — a canned statement-ALTERED pair through `statement_integrity`: must be REJECTED.
    Acceptance ⇒ the anti-laundering gate is dead (the worse failure: false trust).

DETERMINISTIC (no LLM dispatch; seconds warm, ≤ a cold reload). FAIL-CLOSED: the run entry treats a failed
standard as INSTRUMENT-DEAD and aborts loudly rather than burning the wallclock on untrustworthy verdicts.
Both legs injectable ⇒ hermetic selftest.

Usage:  from ztare.leanmill.run_standards import run_instrument_standards
        cert = run_instrument_standards(lean_root)   # {"ok", "positive", "negative", "detail"}
Gate:   ZTARE_LEANMILL_RUN_STANDARDS (DEFAULT-ON; =0 reverts — the sound-knob principle).
"""
from __future__ import annotations

import os
from pathlib import Path

_POSITIVE_PROBE = "theorem leanmill_run_standard_pos : 2 + 2 = 4 := by norm_num\n"
# the canned NEGATIVE pair: the "proof" file RENAMES/ALTERS the target's statement (the classic launder) —
# statement_integrity must flag `target_signature_altered`.
_NEG_ORIGINAL = "theorem leanmill_run_standard_neg (n : Nat) : n + 0 = n := by sorry\n"
_NEG_ALTERED = "theorem leanmill_run_standard_neg (n : Nat) : n + 1 = n + 1 := by rfl\n"


def _default_positive(lean_root: "Path | str") -> "tuple[bool, str]":
    """The trivial probe through the REAL verify path (warm REPL preferred, cold lake fallback)."""
    try:
        # WARM path: RAW probe (the REPL pre-loads Mathlib and REJECTS a mid-session `import` — the
        # warm-vs-verify asymmetry in REVERSE; v4's first standards run false-failed on exactly this).
        from ztare.formal.repl_compile import _get_repl
        pl = _get_repl(str(lean_root))
        if pl is not None:
            r = pl.check(_POSITIVE_PROBE, timeout=240)
            ok = bool(r.get("success")) if isinstance(r, dict) else bool(getattr(r, "ok", False))
            return ok, "warm-repl"
        import subprocess
        import tempfile
        scratch = Path(lean_root) / ".solver_scratch"
        scratch.mkdir(exist_ok=True)
        from ztare.leanmill.lean_source import ensure_import_header
        with tempfile.NamedTemporaryFile("w", suffix=".lean", dir=scratch, delete=False) as f:
            f.write(ensure_import_header(_POSITIVE_PROBE))
            tmp = f.name
        r = subprocess.run(["lake", "env", "lean", tmp], cwd=str(lean_root),
                           capture_output=True, text=True, timeout=600)
        return r.returncode == 0, "cold-lake"
    except Exception as e:  # noqa: BLE001 — an erroring instrument is a DEAD instrument (fail-closed)
        return False, f"error: {repr(e)[:120]}"


def _default_negative() -> "tuple[bool, str]":
    """The canned altered-statement pair through statement_integrity: True iff the alteration is CAUGHT."""
    try:
        from ztare.leanmill.solver.statement_integrity import check as _si_check
        v = _si_check(_NEG_ORIGINAL, _NEG_ALTERED, "leanmill_run_standard_neg")
        caught = not getattr(v, "ok", True) or bool(getattr(v, "violations", []))
        return caught, "statement_integrity.check"
    except Exception as e:  # noqa: BLE001 — an erroring gate is a DEAD gate (fail-closed)
        return False, f"error: {repr(e)[:120]}"


def run_instrument_standards(lean_root: "Path | str", *, positive_fn=None, negative_fn=None) -> dict:
    """Run both standards; return the run's instrument certificate. `ok` iff the positive CLOSED and the
    negative was REJECTED. Gated ZTARE_LEANMILL_RUN_STANDARDS (default-on; =0 ⇒ {"ok": True, "skipped": True})."""
    if os.environ.get("ZTARE_LEANMILL_RUN_STANDARDS", "1") == "0":
        return {"ok": True, "skipped": True}
    pos_ok, pos_via = (positive_fn or _default_positive)(lean_root) if positive_fn is None \
        else positive_fn(lean_root)
    neg_ok, neg_via = (negative_fn or _default_negative)() if negative_fn is None else negative_fn()
    return {"ok": bool(pos_ok and neg_ok), "skipped": False,
            "positive": {"closed": bool(pos_ok), "via": pos_via},
            "negative": {"cheat_rejected": bool(neg_ok), "via": neg_via},
            "detail": ("instrument LIVE (positive closed + cheat rejected)" if pos_ok and neg_ok else
                       ("PROVER DEAD: the trivial standard did not close" if not pos_ok else
                        "GATE DEAD: the canned statement-alteration was NOT rejected"))}


def run_instrument_liveness_battery(*, embed_fn=None, atlas_nonempty=None, backtranslate_fn=None) -> dict:
    """UNIFIED run-start liveness for the ADVISORY external instruments whose SILENT death causes a
    false-DEGRADE / false-REJECT — distinct from the fail-closed carriers (`assert_carriers_live`) and the
    prover/gate standards (`run_instrument_standards`). Two instruments, both LLM-provider-backed and both
    bitten this session:
      • the semantic-shelf EMBEDDER — dead ⇒ shelf returns empty ⇒ "no prior work" ⇒ re-derivation treadmill;
      • the firewall ROUND-TRIP judge (back-translate + cross-family fallback) — dead ⇒ empty back-translation ⇒
        the firewall FAIL-CLOSES every target (the BFT campaign burned theory-consolidation, THEN round-trip
        false-rejected, because the judge was never probed at start).
    Each is probed with its own canary; a dead one gets a LOUD banner. ADVISORY (never aborts — a transient
    quota may clear and the cross-family fallback is the resilience) but VISIBLE at run-start, so a dead
    instrument is caught BEFORE the wall is spent. Injectable ⇒ hermetic selftest. Gate
    ZTARE_LEANMILL_INSTRUMENT_LIVENESS (default-on; =0 skips)."""
    if os.environ.get("ZTARE_LEANMILL_INSTRUMENT_LIVENESS", "1") == "0":
        return {"skipped": True, "banners": []}
    from ztare.common.embedder_liveness import embedder_live, liveness_banner
    out: dict = {"banners": []}
    # 1) semantic-shelf embedder (the compounding READ path)
    if embed_fn is None:
        try:
            from ztare.research_director.mathlib_semantic import _embed_query_genai as _eq
            from ztare.leanmill.semantic_premise_shelf import own_ledger_corpus as _olc
            embed_fn = _eq
            if atlas_nonempty is None:
                atlas_nonempty = bool(_olc())
        except Exception:  # noqa: BLE001 — no embedder wired here ⇒ skip that leg (never block)
            embed_fn = None
    if embed_fn is not None:
        live, why = embedder_live(embed_fn, atlas_nonempty=atlas_nonempty)
        out["embedder"] = {"live": bool(live), "why": why}
        if not live:
            out["banners"].append(liveness_banner(live, why, instrument="compounding premise-shelf embedder"))
    # 2) firewall round-trip judge — back-translate a canary; empty ⇒ primary + ALL cross-family fallbacks dead
    if backtranslate_fn is None:
        try:
            from ztare.leanmill.solver.autoformalize import default_backtranslate as backtranslate_fn
        except Exception:  # noqa: BLE001
            backtranslate_fn = None
    if backtranslate_fn is not None:
        try:
            _bt = (backtranslate_fn("theorem canary (n : Nat) : n + 0 = n := by sorry") or "").strip()
        except Exception as _e:  # noqa: BLE001
            _bt = ""
        live = bool(_bt)
        why = "live" if live else "empty back-translation from primary + all cross-family fallbacks (quota / rate-limit / key)"
        out["roundtrip"] = {"live": live, "why": why}
        if not live:
            out["banners"].append(liveness_banner(live, why, instrument="firewall round-trip judge"))
    # 3) Mathlib SEARCH (Loogle) — the agent's premise-discovery backstop. A DEAD search silently degrades to
    #    "guess from memory", and the agent invents lemma names (the EF1 `list_sum_le_of_get` RCA, 2026-07-03: the
    #    default urllib User-Agent 403'd, unprobed). Probe it LOUD at run start; a local-grep fallback counts live.
    try:
        from ztare.leanmill.agent_tools import loogle_search_text
        _r = loogle_search_text("Nat.add_zero", max_hits=1)
        live = ("declarations match" in _r) or ("local Mathlib grep" in _r)
        why = ("live (Loogle)" if "declarations match" in _r
               else "live (local grep; Loogle down)" if "local Mathlib grep" in _r else _r[:90])
        out["mathlib_search"] = {"live": bool(live), "why": why}
        if not live:
            out["banners"].append(liveness_banner(live, why, instrument="Mathlib search (Loogle)"))
    except Exception:  # noqa: BLE001 — probe wiring failure ⇒ skip that leg, never block the run
        pass
    return out


_V33_ORGANS = ("vacuity", "gold_name_verbatim", "single_lemma_exact",
               "indirect_leakage", "consequence_exposure", "currency_mismatch")
_CLEAN_PROBE = "import Mathlib\n\ntheorem t : ∀ n : ℕ, n + 0 = n := by intro n; ring\n"
# discriminating cheats a BLOCKING organ MUST catch (passed=False AND the named confirmed flag present).
_ORGAN_CHEATS = (
    # (organ, lean_source, original_source, expected_confirmed_flag)
    ("gold_name_verbatim", "import Mathlib\n\ntheorem t : ∀ (n : ℕ), n + 0 = n := Nat.add_zero\n",
     None, "gold_name_verbatim_confirmed"),
    ("statement_integrity", "import Mathlib\n\ntheorem t : (2 : ℕ) = 2 := by rfl\n",
     "import Mathlib\n\ntheorem t : (2 : ℕ) = 999 := by sorry\n", "statement_altered_confirmed"),
)


def organ_liveness_battery(lean_root: "Path | str" = "ztare_proofs", *, kernel_fn=None) -> dict:
    """Per-ORGAN liveness — the generalization of `run_instrument_standards`' single-organ negative leg.

    RCA 2026-06-18: TWO anti-laundering organs were found silently DEAD this session (a matched-negative-control
    that crashed on `NameError: re` and fail-opened), and `run_instrument_standards` only ever exercised the
    statement_integrity organ — so a dead organ slipped through. This battery closes that gap:
      (a) REACHABILITY — every v33 organ must run on a clean probe WITHOUT landing in `detail[organ]={'error':…}`
          or being absent (the dead-MNC class: a crashing organ is caught here, advisory-or-not).
      (b) DETECTION — each BLOCKING organ must FIRE its `_confirmed` flag (passed=False) on a discriminating
          cheat (gold-name-verbatim on a verbatim Mathlib citation; statement-integrity on an altered statement).
    `kernel_fn(src, original_source, target) -> {passed, flags, detail}` is injectable ⇒ hermetic selftest; the
    real run uses `run_anti_laundering_kernel` (cold Lean — a diagnostic/CI guard, NOT a per-solve tax)."""
    import tempfile
    from pathlib import Path as _P
    if kernel_fn is None:
        from ztare.gates.lean_proof_gate import run_anti_laundering_kernel as _k
        root = _P(lean_root).resolve()
        def kernel_fn(src, orig, tgt):  # noqa: E306
            return _k(src, _P(tempfile.mkdtemp(prefix="organ_")) / "K.lean", root,
                      original_source=orig or src, target_name=tgt)
    clean = kernel_fn(_CLEAN_PROBE, None, "t") or {}
    det = clean.get("detail", {}) or {}
    reachable = {o: (o in det and not (isinstance(det.get(o), dict) and "error" in det[o]))
                 for o in _V33_ORGANS}
    fires: dict = {}
    for organ, src, orig, flag in _ORGAN_CHEATS:
        r = kernel_fn(src, orig, "t") or {}
        fires[organ] = (flag in (r.get("flags") or [])) and (r.get("passed") is False)
    dead = [o for o, v in reachable.items() if not v] + [f"{o}(no-fire)" for o, v in fires.items() if not v]
    return {"ok": not dead, "organs_reachable": reachable, "blockers_fire": fires,
            "detail": ("all v33 organs reachable + blocking organs fire on a discriminating cheat" if not dead
                       else "ORGAN-LIVENESS FAILURE (dead/silent organ — the exact class the dead MNC was): "
                            + ", ".join(dead))}


def trust_conservation_audit(since_iso: str, *, run_tag: str = "",
                             db_path=None, ledger=None) -> dict:
    """POST-RUN TRUST-CONSERVATION CHECK (v3 RCA 2026-06-12): assert the trust layers AGREE for this run —
    every attempts-DB `ratified=1` win must have a closed certificate that is integrity-VERIFIED with a
    non-empty recompilable probe. The v3 disease was exactly a conservation violation (DB said ratified=1,
    the cert was hollow, the notes said "none closed") that no layer-local selftest could see: each layer
    was locally correct; the SEAM carried no check. Runs in seconds, read-only, fail-LOUD (the run is
    already over — report, never mask). `db_path`/`ledger` injectable ⇒ hermetic selftest."""
    import json
    import sqlite3
    if db_path is None or ledger is None:
        from ztare.leanmill.solver.solver_core import ATTEMPTS_DB as _DB, ADHOC_CLOSURE_CERTIFICATES as _L
        db_path = db_path or _DB
        ledger = ledger or _L
    viol: "list[str]" = []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        q = "select row_id from attempts where ratified=1 and attempt_at>=?"
        args: tuple = (since_iso,)
        if run_tag:
            q += " and run_tag=?"
            args = (since_iso, run_tag)
        # row_id is '<mode>::<target>' (e.g. adhoc::seam_t); certs key by bare target — join on the suffix.
        ratified = [str(r[0]).split("::")[-1] for r in con.execute(q, args)]
    except Exception as e:  # noqa: BLE001 — an unreadable trust layer IS a violation, never a silent pass
        return {"ok": False, "violations": [f"attempts DB unreadable: {repr(e)[:120]}"], "counts": {}}
    certs: dict = {}
    try:
        for ln in Path(ledger).read_text(encoding="utf-8").splitlines():
            try:
                c = json.loads(ln)
            except ValueError:
                continue
            if str(c.get("ts") or "") >= since_iso and c.get("outcome") == "closed":
                certs[c.get("target")] = c
    except OSError as e:
        if ratified:   # ratified wins with NO ledger at all = the worst violation
            return {"ok": False, "violations": [f"cert ledger unreadable with {len(ratified)} ratified "
                                                f"win(s): {repr(e)[:120]}"], "counts": {}}
    for t in ratified:
        c = certs.get(t)
        if c is None:
            viol.append(f"ratified '{t}': NO closed certificate in the run window")
        elif (c.get("governance") or {}).get("integrity_unverified"):
            viol.append(f"ratified '{t}': certificate is integrity-UNVERIFIED (hollow — must be ratified=0)")
        elif not (c.get("recompilable_probe") or "").strip():
            viol.append(f"ratified '{t}': certificate has an EMPTY recompilable probe (unauditable)")
    return {"ok": not viol, "violations": viol,
            "counts": {"ratified_attempts": len(ratified), "closed_certs_in_window": len(certs)}}


def closure_telemetry_conservation_audit(since_iso: str, *, run_tag: str = "",
                                         db_path=None, ledger=None) -> dict:
    """POST-RUN CLOSURE-CONSERVATION CHECK (2026-06-22) — the INVERSE of `trust_conservation_audit`, and the net
    that would have caught the proposer-pool closure-drop. `trust_conservation_audit` asserts ratified=1 ⟹ a real
    cert; THIS asserts the other direction: every `closed` (compile_ok=1) attempt must be traceable to a
    RATIFICATION — its target has a `ratified=1` row OR a closed certificate in the window. A `closed` with NEITHER
    is a producer that recorded a closure it NEVER put through governance — exactly the pool's bare-name
    `closed/ratified=NULL/no-cert` rows that read closed-NOT-ratified. The class is otherwise invisible in the
    summaries (which read these very rows as wins), so it must be a mechanical post-run guard, not vigilance.
    Read-only, fail-LOUD (the run is over — report, never mask). `db_path`/`ledger` injectable ⇒ hermetic selftest."""
    import json
    import sqlite3
    if db_path is None or ledger is None:
        from ztare.leanmill.solver.solver_core import ATTEMPTS_DB as _DB, ADHOC_CLOSURE_CERTIFICATES as _L
        db_path = db_path or _DB
        ledger = ledger or _L
    viol: "list[str]" = []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        _w = " and run_tag=?" if run_tag else ""
        _a: tuple = (since_iso, run_tag) if run_tag else (since_iso,)
        # closure CLAIMS this run (a compile_ok 'closed' row), keyed by bare target (row_id = '<mode>::<target>').
        # A row that is ALREADY ratified=1 is conserved by definition, so exclude it from the claim set.
        claims: dict = {}
        for r in con.execute(
                f"select row_id, move from attempts where outcome='closed' and compile_ok=1 "
                f"and (ratified IS NULL or ratified=0) and attempt_at>=?{_w}", _a):
            claims.setdefault(str(r[0]).split("::")[-1], []).append((str(r[0]), r[1]))
        ratified = {str(r[0]).split("::")[-1] for r in con.execute(
                f"select row_id from attempts where ratified=1 and attempt_at>=?{_w}", _a)}
    except Exception as e:  # noqa: BLE001 — an unreadable trust layer IS a violation, never a silent pass
        return {"ok": False, "violations": [f"attempts DB unreadable: {repr(e)[:120]}"], "counts": {}}
    certs: set = set()
    try:
        for ln in Path(ledger).read_text(encoding="utf-8").splitlines():
            try:
                c = json.loads(ln)
            except ValueError:
                continue
            if str(c.get("ts") or "") >= since_iso and c.get("outcome") == "closed":
                certs.add(c.get("target"))
    except OSError:
        certs = set()
    for tgt, rows in claims.items():
        if tgt in ratified or tgt in certs:
            continue   # the closure was ratified (stamped) or has a cert → conserved
        _mv = ", ".join(sorted({str(m) for (_rid, m) in rows if m}))
        viol.append(f"closed-but-unratified '{tgt}': {len(rows)} 'closed' attempt(s) (move={_mv or '?'}) with NO "
                    f"ratified=1 row and NO closure cert — a producer recorded a closure that never went through "
                    f"governance (the proposer-pool-drop signature).")
    return {"ok": not viol, "violations": viol,
            "counts": {"unratified_closed_targets": len(claims), "ratified_targets": len(ratified),
                       "closed_certs_in_window": len(certs)}}


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    good_pos = lambda root: (True, "mock")          # noqa: E731
    dead_pos = lambda root: (False, "mock")         # noqa: E731
    good_neg = lambda: (True, "mock")               # noqa: E731
    dead_neg = lambda: (False, "mock")              # noqa: E731
    c = run_instrument_standards(".", positive_fn=good_pos, negative_fn=good_neg)
    ok("both standards pass ⇒ instrument LIVE", c["ok"] is True and "LIVE" in c["detail"])
    c = run_instrument_standards(".", positive_fn=dead_pos, negative_fn=good_neg)
    ok("positive fails ⇒ PROVER DEAD (fail-closed)", c["ok"] is False and "PROVER DEAD" in c["detail"])
    c = run_instrument_standards(".", positive_fn=good_pos, negative_fn=dead_neg)
    ok("cheat accepted ⇒ GATE DEAD (the worse failure)", c["ok"] is False and "GATE DEAD" in c["detail"])
    os.environ["ZTARE_LEANMILL_RUN_STANDARDS"] = "0"
    ok("=0 reverts (skip, ok)", run_instrument_standards(".")["skipped"] is True)
    os.environ.pop("ZTARE_LEANMILL_RUN_STANDARDS", None)
    # the REAL negative leg (deterministic, no Lean): statement_integrity must catch the canned alteration
    caught, via = _default_negative()
    ok(f"real negative standard: canned alteration CAUGHT (via {via})", caught is True)

    # ── per-organ liveness battery (RCA 2026-06-18: catch a silently-dead organ — the dead MNC class).
    #    Hermetic: a MOCK kernel_fn simulates organ behavior (no Lean), so we test the BATTERY LOGIC. ──
    def _mk_kernel(*, dead_organ=None, nonfire=None):
        def k(src, orig, tgt):
            det = {o: {"ran": True} for o in _V33_ORGANS}
            if dead_organ:
                det[dead_organ] = {"error": "simulated organ crash"}   # the dead-MNC class
            flags, passed = [], True
            if "Nat.add_zero" in src and nonfire != "gold_name_verbatim":
                flags, passed = ["gold_name_verbatim_confirmed"], False
            elif orig and "999" in orig and nonfire != "statement_integrity":
                flags, passed = ["statement_altered_confirmed"], False
            return {"passed": passed, "flags": flags, "detail": det}
        return k
    ok("organ-liveness: all organs reachable + blockers fire ⇒ ok",
       organ_liveness_battery(kernel_fn=_mk_kernel())["ok"] is True)
    _rc = organ_liveness_battery(kernel_fn=_mk_kernel(dead_organ="vacuity"))
    ok("organ-liveness: a CRASHING organ is CAUGHT (the exact dead-MNC class)",
       _rc["ok"] is False and _rc["organs_reachable"]["vacuity"] is False and "vacuity" in _rc["detail"])
    _nf = organ_liveness_battery(kernel_fn=_mk_kernel(nonfire="gold_name_verbatim"))
    ok("organ-liveness: a blocking organ that does NOT fire is CAUGHT",
       _nf["ok"] is False and _nf["blockers_fire"]["gold_name_verbatim"] is False)

    # ── trust-conservation audit (hermetic: temp DB + temp ledger) ──
    import json
    import sqlite3
    import tempfile
    td = Path(tempfile.mkdtemp(prefix="tca_"))
    db = td / "a.db"
    con = sqlite3.connect(db)
    con.execute("create table attempts (row_id text, attempt_at text, ratified int, run_tag text)")
    con.executemany("insert into attempts values (?,?,?,?)", [
        ("adhoc::good_t", "2026-06-12T10:00:00+00:00", 1, "r1"),
        ("adhoc::hollow_t", "2026-06-12T10:01:00+00:00", 1, "r1"),
        ("adhoc::lost_t", "2026-06-12T10:02:00+00:00", 1, "r1"),
        ("adhoc::old_t", "2026-06-11T00:00:00+00:00", 1, "r0"),      # outside window+tag — ignored
        ("adhoc::unrat_t", "2026-06-12T10:03:00+00:00", 0, "r1"),    # not ratified — no cert required
    ])
    con.commit(); con.close()
    led = td / "certs.jsonl"
    led.write_text("\n".join(json.dumps(c) for c in [
        {"ts": "2026-06-12T10:00:01+00:00", "target": "good_t", "outcome": "closed",
         "recompilable_probe": "import Mathlib\ntheorem good_t : True := trivial", "governance": {}},
        {"ts": "2026-06-12T10:01:01+00:00", "target": "hollow_t", "outcome": "closed",
         "recompilable_probe": "", "governance": {"integrity_unverified": True}},
    ]) + "\n", encoding="utf-8")
    r = trust_conservation_audit("2026-06-12T00:00:00+00:00", run_tag="r1", db_path=db, ledger=led)
    ok("conservation: hollow + missing certs FLAGGED, good + unratified pass",
       r["ok"] is False and len(r["violations"]) == 2
       and any("hollow_t" in v and "UNVERIFIED" in v for v in r["violations"])
       and any("lost_t" in v and "NO closed certificate" in v for v in r["violations"]))
    led.write_text(json.dumps({"ts": "2026-06-12T10:00:01+00:00", "target": "good_t", "outcome": "closed",
                               "recompilable_probe": "x", "governance": {}}) + "\n", encoding="utf-8")
    con = sqlite3.connect(db)
    con.execute("delete from attempts where row_id in ('adhoc::hollow_t','adhoc::lost_t')")
    con.commit(); con.close()
    r2 = trust_conservation_audit("2026-06-12T00:00:00+00:00", run_tag="r1", db_path=db, ledger=led)
    ok("conservation: all-consistent run ⇒ ok", r2["ok"] is True and r2["counts"]["ratified_attempts"] == 1)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
