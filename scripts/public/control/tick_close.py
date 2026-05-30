#!/usr/bin/env python3
"""tick_close.py — FAIL-CLOSED artisanal/interactive tick-close wrapper.

Why this exists (operator, 2026-05-16): the autonomous VPS/SRO daemon
already drives the gates as a wrapper, so an agent cannot invoke them
wrong there. ARTISANAL (interactive, hand-driven) mode was the
underinvested hole: the agent picks how to run the gates and can run
them wrong or gloss the output. This session proved it — post_tick run
WITHOUT RD_OWNER (legacy-global, backlog-poisoned exit-1 then glossed),
fabricated `forecast contract success=true` tokens, missing F-rows,
unresolved contracts narrated as resolved.

The fix is to remove agent discretion at close: there is exactly ONE
sanctioned way to close an artisanal tick, and it is FAIL-CLOSED — it
refuses (non-zero) unless every discretionary hole is mechanically shut:

  H1  RD_OWNER MUST resolve (--owner or $RD_OWNER). Absent ⇒ REFUSE.
      (Closes the "ran post_tick bare ⇒ legacy-global ⇒ glossed" hole.)
  H2  owner-scoped `post_tick_check.py` (RD_OWNER set) HARD-clears.
      (Reuses the canonical gate; no reimplementation.)
  H3  the tick's proposed F-row body exists, is `owner:<RD_OWNER>`-
      tagged, and carries a grammar-valid `dispatch_ledger:`. In the
      GP-241 daemon-owned mode this row is supplied as --f-row-body or
      --f-row-body-file and is materialized by the daemon after
      validation. Legacy fallback may still read EXPERIMENT_TRACK_
      RECORD.md, but the wrapper must not force agents to hand-write it.
  H4  the tick's forecast contract (--contract-id) is RESOLVED — an
      outcome file exists. (Closes "no prediction market / unresolved
      contract narrated as resolved".)

Composes existing gates only (post_tick_check, dispatch_ledger_check,
forecast_pool outcomes/) — reimplements none of them. NOT yet trusted:
pencil + this implementation go to adversarial review before it is the
mandatory artisanal close path.

Usage:
  RD_OWNER=agent:RD ./venv/bin/python scripts/public/control/tick_close.py \
      --tick-row F-NS-TICK629 --contract-id tick629-... \
      --f-row-body-file /tmp/tick629_f_row.txt [--window-hours 24]
Exit: 0 = TICK CLOSE OK; non-zero = TICK CLOSE REFUSED (tick NOT closed).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TRACK = REPO / "research_areas/EXPERIMENT_TRACK_RECORD.md"
OUTCOMES = REPO / "analytics/public/forecast_pool/outcomes"
POST_TICK = REPO / "scripts/public/control/post_tick_check.py"
DLC = REPO / "src/ztare/validator/dispatch_ledger_check.py"
STATE = REPO / "analytics/public/control/tick_close_state.json"
HIST = REPO / "analytics/public/control/tick_close_history.jsonl"
PY = sys.executable
SANCTIONED_DISPATCH_CLASSES = {
    "adversarial_kill",
    "divide_and_conquer",
    "cold_deanchor_carveout3",
}


def _refuse(reason: str) -> int:
    print(f"\n🛑 TICK CLOSE REFUSED — {reason}\n   (the tick is NOT "
          f"closed; fix the cause and re-run; this gate is fail-closed "
          f"by design — do not work around it).")
    return 1


def _load_f_row_body(args: argparse.Namespace) -> tuple[str | None, str]:
    """Return the proposed row body + source.

    GP-241 makes the daemon the official F-row writer. The close wrapper
    therefore accepts a proposed body directly. Reading
    EXPERIMENT_TRACK_RECORD.md is retained only as legacy compatibility.
    """
    if args.f_row_body_file:
        p = Path(args.f_row_body_file)
        if not p.is_absolute():
            p = REPO / p
        if not p.is_file():
            return None, f"--f-row-body-file not found: {p}"
        return p.read_text(encoding="utf-8", errors="ignore").strip(), (
            f"proposed f_row_body from {p}"
        )
    if args.f_row_body:
        return args.f_row_body.strip(), "proposed f_row_body from CLI"
    if not TRACK.exists():
        return None, f"{TRACK} missing and no --f-row-body-file supplied"
    for ln in TRACK.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ln.lstrip().startswith("| F-") and args.tick_row in ln:
            return ln, f"legacy row from {TRACK}"
    return None, (
        f"no F-row matching '{args.tick_row}' in {TRACK} and no "
        "--f-row-body-file supplied"
    )


def _dispatch_ledger_errors(row: str) -> list[str]:
    m = re.search(r"dispatch_ledger:\s*([^|]*)", row, re.IGNORECASE)
    if not m:
        return ["missing dispatch_ledger:"]
    body = m.group(1).strip().strip("`").strip()
    if not body:
        return ["empty dispatch_ledger:"]
    if body.lower().startswith("none"):
        return []
    errors: list[str] = []
    for entry in re.split(r"[;,]", body):
        entry = entry.strip()
        if not entry:
            continue
        cls = entry.split("=", 1)[1].strip() if "=" in entry else entry
        cls = cls.split()[0].strip().lower() if cls else ""
        if cls not in SANCTIONED_DISPATCH_CLASSES:
            errors.append(
                f"unsanctioned dispatch class '{cls or '<empty>'}' "
                f"(sanctioned: {sorted(SANCTIONED_DISPATCH_CLASSES)})"
            )
    return errors


def _frozen_start(tick_id: str) -> dict | None:
    """F1 (Meta-Darwin bwdcoww2y): the daemon b1djdevru check requires
    close.contract_id == the frozen start row's contract_id, which is
    the COMPILER cid (start_tick(goal).contract_id) — NOT the forecast
    slug. tick_close.py only knows the slug, so honest closes were
    quarantining. Fix: read the SAME chain-valid SIGNED start row the
    daemon froze (via stamped_state — no recompute, no namespace
    drift) and send ITS contract_id + goal. Returns the FIRST
    chain-valid signed start_tick row for this tick, or None."""
    try:
        sys.path.insert(0, str(REPO))
        from src.ztare.gates.stamped_state import official_transitions
        rows, _errs = official_transitions()
        for r in rows:
            if (r.get("transition_type") == "start_tick"
                    and str(r.get("tick_id", "")) == str(tick_id)):
                return r
    except Exception:
        rows = []
    # Cold review bq4z7midf F1: enforce-mode stamped_state hardcodes
    # the LOCAL /srv store. On a laptop (remote-enforce, only
    # ZTARE_VERIFICATOR_SSH set) the official store is REMOTE, so the
    # local read above is empty and an honest remote-started tick
    # would false-refuse. Fall back to the SAME read-only base64-cat
    # of the VPS ledger that propose uses (NO remote code), then
    # chain_valid LOCALLY — identical trust model, no namespace drift.
    if os.environ.get("ZTARE_VERIFICATOR_SSH", "").strip():
        try:
            import base64 as _b64
            import shlex as _shlex
            from src.ztare.gates.propose import _ssh_base, VPS_STORE
            from src.ztare.gates.stamped_state import chain_valid
            _lg = f"{VPS_STORE}/official/transitions.stamped.jsonl"
            _cmd = (f"base64 {_shlex.quote(_lg)} 2>/dev/null")
            _r = subprocess.run(_ssh_base() + [_cmd], text=True,
                                capture_output=True, timeout=30)
            if _r.returncode == 0 and _r.stdout.strip():
                _txt = _b64.b64decode(
                    "".join(_r.stdout.split())).decode(
                        "utf-8", "replace")
                _raw = []
                for _ln in _txt.splitlines():
                    _ln = _ln.strip()
                    if not _ln:
                        continue
                    try:
                        _raw.append(json.loads(_ln))
                    except Exception:
                        continue
                _valid, _ = chain_valid(_raw)
                for r in _valid:
                    if (r.get("transition_type") == "start_tick"
                            and str(r.get("tick_id", ""))
                            == str(tick_id)):
                        return r
        except Exception:
            return None
    return None


def _judge_feedback(tick_id: str) -> str:
    """GP-241 #60: surface the out-of-loop judge's verdict + WHY
    IN-BAND, the way the autoresearch loop feeds the verifier's
    feedback back to the agent. Without this the closing agent had to
    ssh+cat the ztare_judge-owned verdicts queue to learn why a
    judge:auto obligation FAILED (information asymmetry / spelunking).
    Reads the agent-readable chain-valid stamped ledger only; advisory,
    never blocks. Returns the latest verdict+reason per obligation for
    this tick."""
    try:
        sys.path.insert(0, str(REPO))
        from src.ztare.gates.stamped_state import official_transitions
        rows, _ = official_transitions()
    except Exception:
        return ""
    latest: dict = {}
    for r in rows:
        if r.get("transition_type") != "judge_verdict":
            continue
        c = r.get("close") if isinstance(r.get("close"), dict) else r
        if str(c.get("tick_id", "")) != str(tick_id):
            continue
        iid = str(c.get("item_id", "") or "?")
        latest[iid] = (str(c.get("verdict", "") or r.get(
            "judge_verdict", "") or "?"),
            str(c.get("judge_reason", "") or "")[:600],
            str(r.get("ts", "")))
    if not latest:
        return ("\n   JUDGE FEEDBACK (#60): no judge_verdict yet for "
                "this tick — judge:auto pending; the ztare-judge-worker "
                "has not produced a verdict. Re-submit the IDENTICAL "
                "close after the worker runs.")
    out = ["\n   JUDGE FEEDBACK (#60, in-band — do NOT ssh to read it):"]
    for iid, (v, why, ts) in sorted(latest.items()):
        out.append(f"     · {iid}: verdict={v.upper()}"
                   + (f" — {why}" if why else
                      " — (no reason surfaced; older verdict pre-#60)"))
    out.append("     → If FAIL: the discharge TYPE/content is wrong, "
               "not the judge. For a negative-result tick a successful-"
               "construction witness is a category error — use why_not "
               "with the obligation's own why_not_enum value that is "
               "TRUE (e.g. contradicted_by_goal), not an engineered "
               "PASS. Correct it and re-submit; do NOT game the judge.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tick-row", required=True,
                    help="substring of THIS tick's F-row id (e.g. "
                         "F-NS-TICK629) — must appear in the proposed "
                         "F-row body, which must be owner-tagged and "
                         "carry a valid dispatch_ledger")
    ap.add_argument("--contract-id", required=True,
                    help="THIS tick's forecast_pool contract id — its "
                         "outcome (resolution) file must exist")
    ap.add_argument("--owner", default=None)
    ap.add_argument("--window-hours", type=int, default=24)
    # H7 pass-throughs: the obligation discharge the daemon recomputes.
    ap.add_argument("--declared-json", default="{}",
                    help="3-layer L1/L2/L3 + witnesses for commit_membrane")
    ap.add_argument("--witnesses-json", default="{}",
                    help="obligation witnesses (item_id → required fields)")
    ap.add_argument("--why-not-json", default="{}",
                    help="verifiable why_not enum for non-applicable obligs")
    ap.add_argument("--declare", default="",
                    help="comma-separated typed signals forwarded to "
                         "propose.py --declare")
    ap.add_argument("--declare-file", default="",
                    help="file containing comma-separated typed signals "
                         "forwarded to propose.py --declare")
    ap.add_argument("--f-row-body", default="",
                    help="proposed F-row body for daemon materialization. "
                         "Do not hand-edit EXPERIMENT_TRACK_RECORD.md.")
    ap.add_argument("--f-row-body-file", default="",
                    help="file containing the proposed F-row body for "
                         "daemon materialization")
    a = ap.parse_args()

    # H1 — RD_OWNER mandatory (no bare runs).
    owner = a.owner or os.environ.get("RD_OWNER") or None
    if not owner:
        return _refuse("H1: no RD_OWNER/--owner. Artisanal close MUST be "
                       "owner-scoped (bare runs go legacy-global and "
                       "backlog-poison — the proven gloss). "
                       "Set RD_OWNER=<id>.")
    env = dict(os.environ, RD_OWNER=owner)
    print(f"tick_close: owner={owner} row~{a.tick_row} "
          f"contract={a.contract_id}")

    # H4 — forecast contract RESOLVED, EXACT-STEM (no substring
    # collision: `tick62` must not satisfy via `tick629`) AND fresh
    # (outcome mtime within --window-hours, so a stale already-resolved
    # contract can't be reused — converged must-fix Q1).
    win_s = a.window_hours * 3600
    out_f = OUTCOMES / f"{a.contract_id}.json"
    if not out_f.is_file():
        return _refuse(f"H4: no EXACT outcome file {out_f.name} in "
                       f"{OUTCOMES} — the prediction market for THIS "
                       f"contract was not resolved (substring/near-miss "
                       f"does not count).")
    age = (datetime.now(timezone.utc)
           - datetime.fromtimestamp(out_f.stat().st_mtime,
                                     tz=timezone.utc)).total_seconds()
    if age > win_s:
        return _refuse(f"H4: outcome {out_f.name} resolved {age/3600:.1f}h "
                       f"ago (> --window-hours={a.window_hours}) — a "
                       f"STALE already-resolved contract cannot close a "
                       f"fresh tick (stale-reuse bypass, Q1).")
    print(f"  H4 OK: contract resolved & fresh ({out_f.name}, "
          f"{age/3600:.1f}h)")

    # H6 — #28 scoped-HARD catch-attest. ONLY fires on the OBJECTIVE
    # catch trigger (this tick's contract resolved success=FALSE = a
    # conceded adversarial-kill / correction). Then an INDEPENDENT
    # catch-ledger entry (author≠concurring) referencing it is required
    # before close. success=true / no outcome ⇒ advisory (no false-fire,
    # the GAP-H lesson). Never auto-writes the append-only ledger.
    try:
        _src = str(REPO / "src")
        if _src not in sys.path:
            sys.path.insert(0, _src)
        from ztare.validator.catch_attest_gate import catch_attested
        ca_ok, ca_why = catch_attested(a.contract_id, a.tick_row)
    except Exception as e:
        ca_ok, ca_why = True, f"catch_attest_gate degraded ({e}) — advisory"
    if not ca_ok:
        return _refuse(f"H6 (#28 catch-attest, objective-trigger): {ca_why}")
    print(f"  H6 OK: {ca_why}")

    # H3a — proposed F-row body exists and is self-consistent. In
    # daemon-owned mode this body is NOT required to already exist in
    # EXPERIMENT_TRACK_RECORD.md; the daemon materializes it after
    # validation.
    from datetime import timedelta as _td
    win_lo = (datetime.now(timezone.utc)
              - _td(hours=a.window_hours)).strftime("%Y-%m-%d")
    row, row_source = _load_f_row_body(a)
    if row is None:
        return _refuse(f"H3a: {row_source}. The proposed F-row body is owed "
                       f"at close and must be submitted to the daemon via "
                       f"--f-row-body-file or --f-row-body; do NOT "
                       f"hand-edit EXPERIMENT_TRACK_RECORD.md.")
    # MUTUAL BINDING (Q1): the row must be dated TODAY (no stale-row
    # reuse) AND textually reference THIS contract-id (the row and the
    # resolved contract must be the same tick, not an opportunistic pair).
    _dm = re.search(r"`(\d{4}-\d{2}-\d{2})`", row)
    if not _dm or _dm.group(1) < win_lo:
        return _refuse(f"H3a: F-row '{a.tick_row}' date "
                       f"{_dm.group(1) if _dm else '∅'} is older than the "
                       f"window floor {win_lo} (--window-hours="
                       f"{a.window_hours}) — a stale prior row cannot "
                       f"close a fresh tick (Q1; UTC-rollover-robust: "
                       f"within-window not strict-today).")
    if a.contract_id not in row:
        return _refuse(f"H3a: F-row '{a.tick_row}' does not reference "
                       f"contract '{a.contract_id}' — the F-row and the "
                       f"resolved contract must be mutually bound (same "
                       f"tick), else any old row+any resolved contract "
                       f"satisfies the gate (Q1 bypass).")
    if not re.search(rf"owner:\s*{re.escape(owner)}\b", row):
        return _refuse(f"H3b: F-row '{a.tick_row}' is not "
                       f"`owner:{owner}`-tagged — un-attributable, so it "
                       f"cannot be owner-scoped-enforced (the gloss "
                       f"surface).")
    print(f"  H3a/b OK: owner-tagged proposed F-row present "
          f"({row_source})")

    # H3c — dispatch_ledger grammar-valid on THIS proposed row. The
    # old owner-scoped record scan is intentionally not used here; it
    # reintroduced the stale requirement that the row already be
    # hand-written to EXPERIMENT_TRACK_RECORD.md.
    dl_errors = _dispatch_ledger_errors(row)
    if dl_errors:
        return _refuse("H3c: proposed F-row dispatch_ledger invalid — "
                       + "; ".join(dl_errors))
    print("  H3c OK: proposed F-row dispatch_ledger clean")

    # H5 — RC3 forced-consumption: the F-row MUST carry
    # `consumes_surfaced:<id>` and that id MUST validate against the
    # live void-audit surfaced set. Closes the anchored-free-recall
    # gloss at the SELECTION step (a probe not drawn from the surfaced
    # set cannot close its tick). Degrade-safe: no artifact ⇒ advisory.
    m_cs = re.search(r"consumes_surfaced:\s*([^\s|;]+)", row)
    claimed = m_cs.group(1) if m_cs else None
    try:
        _src = str(REPO / "src")
        if _src not in sys.path:
            sys.path.insert(0, _src)
        from ztare.validator.surfaced_consumption_gate import (
            consumed_id_is_surfaced,
        )
        # NS-scope guard: pass the tick-row id AND the H3a-anchored
        # F-ROW BODY (`row`) as the substrate hint. #27 spoof must-fix:
        # id-only was spoofable (mislabel the F-row id non-NS); the
        # F-row body is anchored against the tracked ledger by H3a and
        # an NS tick's findings text inevitably trips the broadened
        # NS-marker detection — far harder to spoof than the id.
        cs_ok, cs_why = consumed_id_is_surfaced(claimed, f"{a.tick_row} {row}")
    except Exception as e:
        cs_ok, cs_why = True, f"surfaced_consumption_gate degraded ({e}) — advisory"
    if not cs_ok:
        return _refuse(f"H5 (RC3 forced-consumption): {cs_why}")
    # CONTRACT-INIT BINDING (review must-fix: locus + cite-without-
    # consume). H5 alone is post-hoc; bind the probe to the surfaced id
    # at contract-CREATION by requiring the forecast contract's
    # question (written at init, BEFORE the science) to reference the
    # claimed id. A close-time paste cannot satisfy this — the contract
    # json predates the science. Only enforced when a claim exists +
    # the gate was HARD (NS, surfaced set live).
    if claimed and "ADVISORY" not in cs_why and "non-NS" not in cs_why:
        cj = REPO / "analytics/public/forecast_pool/contracts" / f"{a.contract_id}.json"
        cval = None
        if cj.is_file():
            try:
                cval = json.loads(cj.read_text(errors="ignore")).get(
                    "consumes_surfaced")
            except Exception:
                cval = None
        nclaim = re.sub(r"[^a-z0-9]+", "", (claimed or "").lower())
        ncval = re.sub(r"[^a-z0-9]+", "", (cval or "").lower())
        # #27 stronger bind: the contract's `consumes_surfaced` field
        # is GATE-VALIDATED at init (forecast_pool cmd_init_contract
        # refuses NS contract creation unless it is a real surfaced id).
        # Requiring F-row.claimed == contract.consumes_surfaced (exact
        # normalized) defeats BOTH a close-time paste AND an
        # init-time free-text question paste — the field is
        # machine-validated at creation, not prose.
        if not ncval:
            return _refuse(
                f"H5b (RC3 #27 contract-INIT bind): forecast contract "
                f"'{a.contract_id}' has NO gate-validated "
                f"`consumes_surfaced` field — it was not created via "
                f"the #27 init-time forced-consumption path (probe not "
                f"bound to the surfaced set at SELECTION).")
        if nclaim != ncval:
            return _refuse(
                f"H5b (RC3 #27 contract-INIT bind): F-row cites "
                f"`consumes_surfaced:{claimed}` but the contract's "
                f"gate-validated field is '{cval}' — mismatch ⇒ the "
                f"F-row claim was NOT the surfaced id bound+validated "
                f"at contract-init (relocated-paste gloss). They must "
                f"be the same surfaced id.")
        print(f"  H5b OK: F-row id == contract gate-validated "
              f"consumes_surfaced (bound at init, not pasted)")
    print(f"  H5 OK: {cs_why}")

    # H2 — owner-scoped post_tick HARD must clear.
    pt = subprocess.run([PY, str(POST_TICK), "--window-hours",
                         str(a.window_hours)], capture_output=True,
                        text=True, env=env, timeout=180)
    if pt.returncode != 0:
        return _refuse("H2: owner-scoped post_tick_check HARD-FAILED "
                       f"(exit {pt.returncode}).\n--- post_tick tail ---\n"
                       f"{pt.stdout[-1600:]}")
    print("  H2 OK: owner-scoped post_tick HARD-clear")

    # H7 — GP-241 commit-membrane: this close is NOT official until the
    # verificator daemon stamps it (synchronous fail-closed). Bootstrap-
    # safe by construction: gates THIS close only (no prior-tick
    # dependency ⇒ no bootstrap deadlock; the reader-side bootstrap risk
    # is the separate, deferred rd_tick_brief half). The agent must have
    # discharged the obligations (--witnesses-json) — generic/absent ⇒
    # daemon quarantines ⇒ H7 refuses (you cannot close un-discharged).
    # FORCED-CLOSE (2-cold-pass synthesis 2026-05-17): submit a typed
    # `tick_close` transaction — NOT `--type closure` (the prior
    # :277 type-boundary bug). The H1-H6 above are now ADVISORY
    # pre-checks; the DAEMON is the authority: it re-validates and
    # materializes the official F-row itself (reverse-H3). tick_close.py
    # is a thin client/proposal-builder, it no longer DECIDES closure.
    import subprocess as _sp
    # F1: bind the close to the FROZEN SIGNED start row. close.
    # contract_id MUST be the daemon-namespace compiler cid (the
    # start row's contract_id) — the forecast slug is carried
    # separately as forecast_contract_id (H4/forecast resolution).
    # --goal MUST be the frozen start goal, not the tick-row id.
    _sr = _frozen_start(a.tick_row)
    if _sr is None:
        return _refuse(
            f"F1: no chain-valid SIGNED start_tick row for "
            f"'{a.tick_row}' (cannot bind the close to a frozen "
            f"tick; a tick that never started through the membrane "
            f"cannot be closed — fail-closed).")
    _compiler_cid = str(_sr.get("contract_id", "") or "")
    _frozen_goal = str(_sr.get("goal", "") or "")
    if not _compiler_cid or not _frozen_goal:
        return _refuse(
            f"F1: frozen start row for '{a.tick_row}' is missing "
            f"contract_id/goal — cannot bind (fail-closed).")
    _close = json.dumps({
        "tick_id": a.tick_row,
        "contract_id": _compiler_cid,
        "forecast_contract_id": a.contract_id,
        "f_row_id": a.tick_row,
        "f_row_body": row[:6000],
    })
    _declared_signals = a.declare.strip()
    if a.declare_file:
        _df = Path(a.declare_file)
        if not _df.is_absolute():
            _df = REPO / _df
        if not _df.is_file():
            return _refuse(f"H7: --declare-file not found: {_df}")
        _declared_signals = _df.read_text(
            encoding="utf-8", errors="ignore").strip()
    _cmd = [sys.executable, "-m", "src.ztare.gates.propose",
            "--type", "tick_close", "--text", row[:1200],
            "--goal", _frozen_goal,
            "--declared", a.declared_json,
            "--witnesses", a.witnesses_json,
            "--why-not", a.why_not_json,
            "--close", _close]
    if _declared_signals:
        _cmd += ["--declare", _declared_signals]
    _pr = _sp.run(
        _cmd,
        capture_output=True, text=True, env=env, timeout=180)
    if _pr.returncode != 0:
        _dmsg = (_pr.stdout or _pr.stderr or "")
        _fb = (_judge_feedback(a.tick_row)
               if "judge" in _dmsg.lower() else "")
        return _refuse(
            "H7 (GP-241 commit-membrane): this close was NOT "
            "daemon-stamped — the verificator quarantined it (obligations "
            "un-discharged or relapse). Work is NOT official; the tick "
            "does NOT close.\n   daemon: "
            + _dmsg[-700:] + _fb)
    print("  H7 OK: daemon-stamped (commit-membrane); close is official")

    # Tier-1 STAMP: record the successful close so the NEXT tick's
    # pre-gate (rd_tick_brief via tick_close_gate) can refuse to start
    # a new tick unless the previous one was closed HERE. This is what
    # makes skipping tick_close self-defeating (the next pre-tick blocks)
    # rather than free. Owner-scoped, append-only history + latest.
    STATE.parent.mkdir(parents=True, exist_ok=True)
    rec = {"owner": owner, "tick_row": a.tick_row,
           "contract_id": a.contract_id,
           "closed_at_utc": datetime.now(timezone.utc).isoformat()}
    state = {}
    if STATE.is_file():
        try:
            state = json.loads(STATE.read_text())
        except Exception:
            state = {}
    state.setdefault("by_owner", {})[owner] = rec
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    HIST.parent.mkdir(parents=True, exist_ok=True)
    with HIST.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")

    print(f"\n✅ TICK CLOSE OK — {a.tick_row} / {a.contract_id} "
          f"(owner={owner}): H1 owner ✓  H2 post_tick ✓  H3 F-row+owner+"
          f"ledger ✓  H4 contract resolved ✓. Tick closed; stamp written "
          f"({STATE.name}) — next pre-tick is now unblocked for {owner}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
