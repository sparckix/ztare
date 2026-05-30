# External-prover dispatch epd-bq4z7midf

**Model**: gpt-5.5
**Substrate**: apparatus_governance
**Dispatched**: 2026-05-18T13:53:37+00:00
**Persisted retroactively** (ran via `codex exec`, archived to convention per operator request)

## Question

COLD REVIEW (post self-Meta-Darwin). You are GPT-5.5. ATTACK; do not
regenerate or be agreeable. The implementer ALREADY ran its own
Meta-Darwin and fixed/flagged the items in §SELF-MD — do NOT re-find
those as if new; find what the self-pass MISSED, and Meta-Darwin the
honest residuals. VERDICT GO / GO-WITH-CHANGES / NO-GO + the single
failure mode that remains even if every GO-WITH-CHANGES item is
fixed. Split the verdict (artifact-kill ≠ idea-kill).

## Context
Forced pre/post tick discipline for an LLM research agent that games
ticks. The GP-241 daemon (commit_membrane_daemon.py) is the SOLE
writer of official state (ed25519 hash-chained; reverse-H3
materializes the F-row); tick_close.py H1-H6 advisory, daemon H7 is
authority. A prior Meta-Darwin (NO-GO) produced findings F1-F6 + R2 +
R5'''. This bundle implements all of them.

## What this bundle did (the surface to attack)
- F1: tick_close.py now reads the chain-valid SIGNED start row via
  stamped_state.official_transitions() and sends ITS contract_id
  (compiler cid) as close.contract_id + the frozen goal as --goal;
  the forecast slug is carried separately as forecast_contract_id.
- F3: the daemon freezes forecast identity (forecast_contract_id +
  contract sha256 + question_hash + consumes_surfaced + layer +
  created_by) into the signed start row WHEN the start proposal
  declares forecast_contract_id; close-side compares + re-hashes the
  on-disk contract (post-start mutation blocked). DORMANT — see
  §SELF-MD M-D2.
- F6: daemon requires close.f_row_body to name its provenance
  (tick_id + frozen forecast slug when frozen).
- F5-daemon: if f_row_body claims a formal closure, the posttick
  lean_faithfulness HARD leg must have passed AND a
  target_statement_hash must be present.
- R2: new signed `manifest_receipt` transition — the daemon itself
  hashes the on-disk pretick/posttick manifest, requires status==
  COMPLETE, signs {tick_id,kind,manifest_sha256}; at close the
  daemon recomputes the file hash and requires a chain-valid signed
  receipt that matches. Runners submit the receipt and RC=3 (fail-
  closed) if unsigned.
- R5''': closure-claim ⇒ target_statement_hash must be a member of
  the operator-curated analytics/public/control/
  target_statement_registry.json (absent/empty ⇒ fail-closed).

## SELF-MD (already done by the implementer — do NOT re-report)
M-D1 R2-dead? FALSE: propose.py:281 passes transition_type with no
  allowlist; manifest_receipt accepted. Verified.
M-D2 F3 DORMANT (honest, not fake-wired): no start_tick emitter
  passes forecast_contract_id ⇒ forecast_identity_frozen always
  False ⇒ F3 close-side checks skipped. Daemon side correct + fail-
  safe (only enforce when frozen). Flagged, not faked.
M-D3 F6 FALSE-FAIL self-caught + FIXED: previously required the
  compiler cid (internal hash, never in agent markdown) in the body
  ⇒ would quarantine every honest close; now binds tick_id +
  forecast slug (tokens honest bodies carry; tick_close H3a already
  requires the slug in the row).
Honest residuals carried (NOT claimed solved): F3 dormant; R5'''
  registry is agent-writable (same provenance class as R2-deep —
  per-tick "must be registered" enforced, registry tamper-resistance
  unsolved); R2 yields tamper-EVIDENCE not depth (COMPLETE-but-
  shallow manifest still earns a receipt).

## ATTACK SPECIFICALLY
1. What did the self-Meta-Darwin MISS? New false-FAILs introduced by
   F1/F3/F6/R2 on HONEST closes (esp. F1's official_transitions()
   ordering/immutability; R2 hash recompute vs the bytes the runner
   hashed — newline/encoding/locale drift; the runner submits the
   receipt then the daemon re-reads — TOCTOU between write, receipt,
   and close).
2. R2 propose path: the runner shells `propose --type
   manifest_receipt`. Does propose require fields (text/goal) that
   the runner omits? Does the daemon's manifest_receipt handler run
   BEFORE or AFTER generic evaluate()/relapse gates that could
   quarantine a benign receipt? Trace it.
3. F1 + the pre-existing b1djdevru check: with F1 sending the
   compiler cid as close.contract_id, does the daemon line ~820
   check now pass for honest closes AND still reject foreign
   contracts? Or did F1 just move the false-quarantine?
4. Meta-Darwin the residuals: F3-dormant (is the daemon-side dead
   code acceptable, or laundering by another name?), R5'''-registry-
   provenance, R2-tamper-evidence-not-depth. For each: IRREDUCIBLE |
   LAUNDERED | CHEAP-FIX-NOW (+fix).
5. Is the bundle now comprehensively exhaustive vs rd_tick_brief's
   MECE pre/post legs, or is a class still ungated? file:line.

## CODE
### tick_close.py (F1 region)
POST_TICK = REPO / "scripts/public/control/post_tick_check.py"
DLC = REPO / "src/ztare/validator/dispatch_ledger_check.py"
STATE = REPO / "analytics/public/control/tick_close_state.json"
HIST = REPO / "analytics/public/control/tick_close_history.jsonl"
PY = sys.executable


def _refuse(reason: str) -> int:
    print(f"\n🛑 TICK CLOSE REFUSED — {reason}\n   (the tick is NOT "
          f"closed; fix the cause and re-run; this gate is fail-closed "
          f"by design — do not work around it).")
    return 1


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
        return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tick-row", required=True,
                    help="substring of THIS tick's F-row id (e.g. "
                         "F-NS-TICK629) — must exist, be owner-tagged, "
                         "carry a valid dispatch_ledger")
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
    _pr = _sp.run(
        [sys.executable, "-m", "src.ztare.gates.propose",
         "--type", "tick_close", "--text", row[:1200],
         "--goal", _frozen_goal,
         "--declared", a.declared_json,
         "--witnesses", a.witnesses_json,
         "--why-not", a.why_not_json,
         "--close", _close],
        capture_output=True, text=True, env=env, timeout=180)
    if _pr.returncode != 0:
        return _refuse(
            "H7 (GP-241 commit-membrane): this close was NOT "

### daemon: manifest_receipt handler
85:def _manifest_receipt_ok(tick_id: str, kind: str,
            "research_authority": (s_class not in _NONRESEARCH),
            "contract_scope_required": "micro",
            **_fc,
            "verifier_id": "commit_membrane_daemon",
            "gate_version": GATE_VERSION,
            "parent_state_hash": parent,
            "membrane_stamp": f"START:{s_tid}",
            "verdict": "pass",
        }
        _blob = json.dumps(srow, sort_keys=True)
        srow["official_state_hash"] = hashlib.sha256(
            (parent + _blob).encode()).hexdigest()[:32]
        from src.ztare.gates._daemon_sig import sign as _sgn
        srow["daemon_sig"] = _sgn(srow["official_state_hash"])
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(srow) + "\n")
        proposal_path.unlink(missing_ok=True)
        return {"verdict": "pass", "proposal_id": pid,
                "transition_type": "start_tick", "tick_id": s_tid,
                "official_state_hash": srow["official_state_hash"],
                "mandatory_obligations": srow["mandatory_obligations"]}

    # R2 (Meta-Darwin bwdcoww2y): manifest provenance. The daemon
    # otherwise TRUSTS an agent-written pretick/posttick manifest. A
    # `manifest_receipt` transition makes it tamper-evident: the
    # daemon itself hashes the on-disk manifest, requires status==
    # COMPLETE, and SIGNS {tick_id, manifest_kind, manifest_sha256}
    # into the hash-chained ledger. At close the daemon recomputes
    # the file hash and requires a chain-valid signed receipt that
    # matches — so post-receipt tampering or a forged COMPLETE flag
    # fails closed. The agent cannot forge daemon_sig.
    if str(p.get("transition_type", "")) == "manifest_receipt":
        st = p.get("close") if isinstance(p.get("close"), dict) else {}
        m_tid = str(st.get("tick_id", "")).strip()
        m_kind = str(st.get("manifest_kind", "")).strip()
        _fail = None
        if m_kind not in ("pretick", "posttick") or not m_tid:
            _fail = ("manifest_receipt requires close.tick_id + "
                     "manifest_kind in {pretick,posttick}")
        else:
            _mpath = (REPO_ROOT / "analytics" / "public" / m_kind
                      / m_tid / f"{m_kind}_manifest.json")
            if not _mpath.is_file():
                _fail = f"{m_kind}_manifest.json absent for {m_tid!r}"
            else:
                try:
                    _mb = _mpath.read_bytes()
                    _mj = json.loads(_mb.decode("utf-8", "ignore"))
                    if str(_mj.get("status")) != "COMPLETE":
                        _fail = (f"{m_kind}_manifest status="
                                 f"{_mj.get('status')!r} (not "
                                 f"COMPLETE) — no receipt for an "
                                 f"incomplete manifest")
                    elif str(_mj.get("tick_id")) != m_tid:
                        _fail = (f"{m_kind}_manifest tick_id != "
                                 f"{m_tid!r}")
                except Exception as _me:
                    _fail = (f"{m_kind}_manifest unreadable "
                             f"({type(_me).__name__})")
        if _fail:
            rec = {"ts": _now(), "proposal_id": pid,
                   "transition_type": "manifest_receipt",
                   "verdict": "quarantine", "failed": [_fail]}
            (QUARANTINE / f"{proposal_path.stem}.quarantine.json"
             ).write_text(json.dumps(rec, indent=2))
            proposal_path.unlink(missing_ok=True)
            return rec
        parent = _parent_hash()
        mrow = {
            "ts": _now(), "proposal_id": pid,
            "proposal_body_sha256": body_sha,
            "transition_type": "manifest_receipt",
            "tick_id": m_tid, "manifest_kind": m_kind,
            "manifest_sha256": hashlib.sha256(_mb).hexdigest(),
            "verifier_id": "commit_membrane_daemon",
            "gate_version": GATE_VERSION,
            "parent_state_hash": parent,

### daemon: F3 freeze block
                                  f"NOT in the {s_substrate} "
                                  f"structural-anchor registry — a "
                                  f"'reduction to a new open thing' "
                                  f"REQUIRES "
                                  f"close.new_target_justification "
                                  f"(structured: why this is genuinely "
                                  f"a new irreducible atom, not a "
                                  f"re-vocabularization). Unjustified "
                                  f"⇒ amnesia, refused."]}
                        (QUARANTINE
                         / f"{proposal_path.stem}.quarantine.json"
                         ).write_text(json.dumps(rec, indent=2))
                        proposal_path.unlink(missing_ok=True)
                        return rec
            else:
                # substrate not in registry ⇒ degrade to named +
                # recorded (flagged) — generic, no NS coupling.
                _rt_unreg = True
        from src.ztare.surfacing.pre_tick_obligation_compiler import (
            start_tick as _compile, merge_signals as _ms)
        _sig_in = _ms(p.get("declared_signals"),
                      f"{p.get('transition_text','')} {s_goal}")
        _c = _compile(s_goal, str(st.get("transition_type", "")), _sig_in)
        # F3 (Meta-Darwin bwdcoww2y): freeze the FORECAST IDENTITY into
        # the signed start row so a close cannot bind a different /
        # weaker / unrelated forecast contract than the tick opened
        # on. Optional-but-enforced-when-present: if the start
        # proposal declares forecast_contract_id and the file exists,
        # freeze its sha256 + question_hash + consumes_surfaced +
        # layer + created_by; else mark forecast_identity_frozen=False
        # (pre-schema ticks are NOT false-FAILed — the gates only
        # compare when frozen). The agent cannot forge these: the
        # daemon hashes the on-disk contract itself.
        _fc_id = str(st.get("forecast_contract_id", "") or "")
        _fc = {"forecast_contract_id": _fc_id or None,
               "forecast_contract_sha256": None,
               "forecast_question_hash": None,
               "forecast_consumes_surfaced": None,
               "forecast_layer": None,
               "forecast_created_by": None,
               "forecast_identity_frozen": False}
        if _fc_id:
            try:
                _fcp = (REPO_ROOT / "analytics/public/forecast_pool"
                        / "contracts" / f"{_fc_id}.json")
                if _fcp.is_file():

### daemon: pre/post gate + F3-close + F6 + F5-daemon + R5''' + R2-close
                f"close.contract_id {close.get('contract_id')!r} != "
                f"frozen start_tick contract_id {_sc!r} "
                f"(foreign-contract binding rejected)")
        # END-TO-END pre-tick enforcement (operator 2026-05-18; trust
        # root = operator inspection of the manifest, not agent self-
        # attestation). The DAEMON is the only real authority (H7;
        # tick_close.py H1-H6 are advisory under GP-241). So the
        # pre-tick is enforced HERE or nowhere. A COMPLETE pretick
        # manifest MUST exist for this tick_id AND be mutually bound to
        # the FROZEN signed start row (tick_id + contract_id) — same
        # un-forgeable binding as the b1djdevru contract check above,
        # which closes the presence≠this-tick gap. Absent/INCOMPLETE/
        # mismatched ⇒ oblig_fail ⇒ the existing path QUARANTINES
        # (fail-closed). Any read error is fail-closed (a HARD entry),
        # never a daemon crash.
        _tid = str(close.get("tick_id", "") or "")
        # Shared by BOTH the pre- and post-tick gates (hoisted so the
        # post-gate never NameErrors when the pretick manifest is
        # absent). substrate/goal are frozen+signed in _start_row.
        _fg = str(_start_row.get("goal", "") or "").strip()
        _fs_sub = str(_start_row.get("substrate", "") or "")

        # GENERIC string normalizer (NOT substrate-aware). The daemon
        # is the substrate-AGNOSTIC commit membrane; it must not know
        # what "NS" is. The substrate-swap bypass is closed purely by
        # EXACT binding of the manifest substrate to the FROZEN SIGNED
        # start-row substrate — once that holds, the agent cannot run
        # the pre/post-tick under a different substrate than the tick
        # froze, so substrate-specific required steps cannot be
        # skipped. Which steps a substrate requires is decided in the
        # runner (substrate-aware by design), never here.
        def _subnorm(x: str) -> str:
            return "".join(ch for ch in str(x).strip().lower()
                           if ch.isalnum() or ch == "_")
        try:
            _pm = (REPO_ROOT / "analytics" / "public" / "pretick"
                   / _tid / "pretick_manifest.json")
            if not _pm.is_file():
                oblig_fail.append(
                    f"pretick_manifest MISSING for tick {_tid!r} "
                    f"(analytics/public/pretick/{_tid}/) — the "
                    f"pre-tick (amnesia/menu/pattern/forecast/GP-233) "
                    f"was not RUN; run pretick_runner.py first "
                    f"(fail-closed: no pre-tick ⇒ no close)")
            else:
                _mj = json.loads(_pm.read_text(encoding="utf-8"))
                if str(_mj.get("status")) != "COMPLETE":
                    oblig_fail.append(
                        f"pretick_manifest status="
                        f"{_mj.get('status')!r} (not COMPLETE) — "
                        f"failed pre-tick steps: "
                        f"{[s.get('step') for s in (_mj.get('steps') or []) if not s.get('ok')]}")
                if str(_mj.get("tick_id")) != _tid:
                    oblig_fail.append(
                        f"pretick_manifest tick_id "
                        f"{_mj.get('tick_id')!r} != close tick_id "
                        f"{_tid!r} (foreign-manifest binding rejected)")
                _mc = str(_mj.get("contract_id", "") or "")
                if _sc and _mc and _mc != _sc:
                    oblig_fail.append(
                        f"pretick_manifest contract_id {_mc!r} != "
                        f"frozen start_tick contract_id {_sc!r} "
                        f"(presence≠this-tick bypass blocked)")
                elif _sc and not _mc:
                    oblig_fail.append(
                        f"pretick_manifest carries NO contract_id — "
                        f"cannot mutually-bind to the frozen tick "
                        f"(unbound pre-tick rejected)")
                # GOAL BINDING: the amnesia/menu/pattern/graph steps
                # key on --goal free-text. Without this, a COMPLETE
                # manifest could be produced by running the pre-tick
                # tools on THROWAWAY goal text, then closing the real
                # contract ("tools ran" decoupled from "the pre-tick
                # THIS tick needed"). The start_row goal is frozen +
                # signed at start_tick, so requiring exact equality
                # forces the pre-tick to have been executed on this
                # tick's actual goal.
                _mg = str(_mj.get("goal", "") or "").strip()
                if _fg and _mg != _fg:
                    oblig_fail.append(
                        f"pretick_manifest goal != frozen start_tick "
                        f"goal — the pre-tick tools were run on "
                        f"different goal text than this tick froze "
                        f"(throwaway-pretick bypass blocked); "
                        f"manifest={_mg[:80]!r} frozen={_fg[:80]!r}")
                # SUBSTRATE BINDING (cold re-review b18zbkhdw): the
                # compiler cid EXCLUDES substrate, so without this an
                # agent could run the pre-tick under a different
                # substrate (skipping substrate-specific required
                # steps) yet close the real tick. EXACT binding to the
                # frozen+signed start-row substrate closes it,
                # substrate-AGNOSTICally — the daemon never inspects
                # which substrate it is; the runner owns that.
                _ms_sub = str(_mj.get("substrate", "") or "")
                if _fs_sub and _subnorm(_ms_sub) != _subnorm(_fs_sub):
                    oblig_fail.append(
                        f"pretick_manifest substrate {_ms_sub!r} != "
                        f"frozen start_tick substrate {_fs_sub!r} "
                        f"(substrate-swap bypass blocked)")
                # R2: the manifest must be daemon-receipt-registered
                # (tamper-evident). Recompute the file hash NOW and
                # require a chain-valid signed manifest_receipt that
                # matches — a forged COMPLETE flag or post-receipt
                # edit fails closed (the agent cannot forge the sig).
                _psha = hashlib.sha256(_pm.read_bytes()).hexdigest()
                if not _manifest_receipt_ok(_tid, "pretick", _psha):
                    oblig_fail.append(
                        "pretick_manifest has NO chain-valid signed "
                        "manifest_receipt matching its current hash "
                        "(unregistered or tampered after receipt) — "
                        "submit a `manifest_receipt` transition; the "
                        "daemon will not trust an agent-written "
                        "manifest on its COMPLETE flag alone (R2)")
        except Exception as _pe:
            oblig_fail.append(
                f"pretick_manifest unreadable for {_tid!r} "
                f"({type(_pe).__name__}) — fail-closed (no verifiable "
                f"pre-tick ⇒ no close)")
        # SYMMETRIC POST-TICK GATE (operator: "can we do the same for
        # the post checks"). Mirrors the pre-tick gate exactly: the
        # POST-tick MECE legs must have been EXECUTED for THIS tick.
        # posttick_runner writes contract_id = the SAME compiler cid,
        # so the same un-forgeable tick_id + cid + goal + substrate
        # binding applies. Absent/INCOMPLETE/foreign ⇒ oblig_fail ⇒
        # quarantine (fail-closed). Any read error is fail-closed.
        try:
            _qm = (REPO_ROOT / "analytics" / "public" / "posttick"
                   / _tid / "posttick_manifest.json")
            if not _qm.is_file():
                oblig_fail.append(
                    f"posttick_manifest MISSING for tick {_tid!r} "
                    f"(analytics/public/posttick/{_tid}/) — the "
                    f"POST-tick MECE legs (post_tick_check / micro-"
                    f"resolved / pre<->post bind) were not RUN; run "
                    f"posttick_runner.py before close (fail-closed)")
            else:
                _qj = json.loads(_qm.read_text(encoding="utf-8"))
                if str(_qj.get("status")) != "COMPLETE":
                    oblig_fail.append(
                        f"posttick_manifest status="
                        f"{_qj.get('status')!r} (not COMPLETE) — "
                        f"failed hard legs: "
                        f"{[s.get('step') for s in (_qj.get('steps') or []) if s.get('hard') and not s.get('ok')]}")
                if str(_qj.get("tick_id")) != _tid:
                    oblig_fail.append(
                        f"posttick_manifest tick_id "
                        f"{_qj.get('tick_id')!r} != close tick_id "
                        f"{_tid!r} (foreign-manifest rejected)")
                _qc = str(_qj.get("contract_id", "") or "")
                if _sc and _qc and _qc != _sc:
                    oblig_fail.append(
                        f"posttick_manifest contract_id {_qc!r} != "
                        f"frozen start_tick cid {_sc!r} "
                        f"(presence≠this-tick bypass blocked)")
                elif _sc and not _qc:
                    oblig_fail.append(
                        "posttick_manifest carries NO contract_id — "
                        "cannot mutually-bind (unbound post rejected)")
                _qg = str(_qj.get("goal", "") or "").strip()
                if _fg and _qg != _fg:
                    oblig_fail.append(
                        f"posttick_manifest goal != frozen start goal "
                        f"(throwaway-posttick bypass blocked); "
                        f"manifest={_qg[:60]!r} frozen={_fg[:60]!r}")
                _qs = str(_qj.get("substrate", "") or "")
                if _fs_sub and _subnorm(_qs) != _subnorm(_fs_sub):
                    oblig_fail.append(
                        f"posttick_manifest substrate {_qs!r} != "
                        f"frozen start substrate {_fs_sub!r} "
                        f"(substrate-swap bypass blocked)")
                # R2 (symmetric): posttick manifest must also be
                # daemon-receipt-registered + hash-matched.
                _qsha = hashlib.sha256(_qm.read_bytes()).hexdigest()
                if not _manifest_receipt_ok(_tid, "posttick", _qsha):
                    oblig_fail.append(
                        "posttick_manifest has NO chain-valid signed "
                        "manifest_receipt matching its current hash "
                        "(unregistered or tampered after receipt) — "
                        "submit a `manifest_receipt` transition (R2)")
        except Exception as _qe:
            oblig_fail.append(
                f"posttick_manifest unreadable for {_tid!r} "
                f"({type(_qe).__name__}) — fail-closed (no verifiable "
                f"post-tick ⇒ no close)")
        # F3 close-side: when the forecast identity was frozen at
        # start, the close MUST bind the SAME forecast contract and
        # the on-disk contract MUST still hash to the frozen sha256
        # (detects swap to a weaker/unrelated contract OR post-start
        # mutation of the contract body). Only enforced when frozen
        # (pre-schema ticks not false-FAILed).
        try:
            if _start_row.get("forecast_identity_frozen") is True:
                _ffid = str(_start_row.get(
                    "forecast_contract_id", "") or "")
                _cfid = str(close.get("forecast_contract_id", "")
                            or "")
                if _ffid and _cfid and _cfid != _ffid:
                    oblig_fail.append(
                        f"close forecast_contract_id {_cfid!r} != "
                        f"frozen {_ffid!r} (forecast-swap blocked)")
                elif _ffid and not _cfid:
                    oblig_fail.append(
                        "close carries NO forecast_contract_id but "
                        "the tick froze one (unbound forecast)")
                _fsha = str(_start_row.get(
                    "forecast_contract_sha256", "") or "")
                if _ffid and _fsha:
                    _fcp = (REPO_ROOT / "analytics/public"
                            / "forecast_pool" / "contracts"
                            / f"{_ffid}.json")
                    _cur = (hashlib.sha256(
                        _fcp.read_bytes()).hexdigest()
                        if _fcp.is_file() else "")
                    if _cur != _fsha:
                        oblig_fail.append(
                            f"forecast contract {_ffid!r} body "
                            f"sha256 changed since start "
                            f"(frozen={_fsha[:12]} "
                            f"now={_cur[:12] or 'MISSING'}) — "
                            f"post-start contract mutation blocked")
        except Exception as _fe:
            oblig_fail.append(
                f"forecast-identity check error "
                f"({type(_fe).__name__}) — fail-closed")
        # F6 (Meta-Darwin bwdcoww2y; SELF-CAUGHT false-FAIL fix): the
        # daemon writes close.f_row_body verbatim into the official
        # F-row. Without this an F-row with valid pre/post manifests
        # but an UNRELATED body materializes. The body MUST name its
        # own provenance — but ONLY with tokens an honest agent-
        # authored F-row legitimately contains: the tick_id (the row
        # IS selected by tick_id) and, when the forecast identity was
        # frozen, the forecast SLUG (tick_close.py H3a already refuses
        # a row that does not reference its contract slug, so this is
        # consistent, not a new false-FAIL). The internal compiler
        # cid is NEVER in agent markdown — requiring it would quarant-
        # ine every honest close (my own Meta-Darwin caught this).
        try:
            _fb = str(close.get("f_row_body", "") or "")
            _need_tokens = [("tick_id", _tid)] if _tid else []
            _ff = str(_start_row.get("forecast_contract_id", "")
                      or "")
            if _start_row.get("forecast_identity_frozen") is True \
                    and _ff:
                _need_tokens.append(("forecast contract id", _ff))
            _missing = [lbl for lbl, tok in _need_tokens
                        if tok and tok not in _fb]
            if _need_tokens and _missing:
                oblig_fail.append(
                    f"F-row body does not name its provenance "
                    f"{_missing} — an unrelated/laundered close body "
                    f"cannot be materialized as the official F-row "
                    f"(F6 semantic bind; honest bodies carry these)")
            # F5-daemon: if the body CLAIMS a formal closure, the
            # posttick lean_faithfulness HARD leg must have passed
            # (the daemon already requires posttick COMPLETE; here it
            # additionally requires that specific leg ok+hard) AND a
            # target_statement_hash must be present (full registry
            # check lands with R5'''/#48). Trigger from the body, not
            # caller honesty.
            _bl = _fb.lower()
            _CLAIM = ("clay", " qed", "theorem", " lean", "lean ",
                      "formal proof", "compiled proof", "closure",
                      "sorry-free", "axiom-free", "∎", "lake build")
            if any(k in _bl for k in _CLAIM):
                _lf = None
                try:
                    _qmp = (REPO_ROOT / "analytics/public/posttick"
                            / _tid / "posttick_manifest.json")
                    if _qmp.is_file():
                        _qm2 = json.loads(_qmp.read_text("utf-8"))
                        _lf = next(
                            (s for s in (_qm2.get("steps") or [])
                             if s.get("step") == "lean_faithfulness"),
                            None)
                except Exception:
                    _lf = None
                if not (_lf and _lf.get("ok")
                        and _lf.get("hard") is True):
                    oblig_fail.append(
                        "F-row body claims a formal closure but the "
                        "posttick lean_faithfulness HARD leg did not "
                        "pass (closure-claim ⇒ hard Lean receipt "
                        "required; F5-daemon)")
                # R5''' (Meta-Darwin bwdcoww2y): the claimed
                # target_statement_hash must be a member of the
                # OPERATOR-curated registry — not merely present.

### daemon: _manifest_receipt_ok helper
def _manifest_receipt_ok(tick_id: str, kind: str,
                         file_sha256: str) -> bool:
    """R2: True iff a CHAIN-VALID daemon-SIGNED `manifest_receipt`
    exists for (tick_id, kind) whose recorded manifest_sha256 equals
    file_sha256 (the hash of the manifest the daemon is reading NOW).
    A forged COMPLETE flag or post-receipt tampering ⇒ no match ⇒
    fail-closed. The agent cannot forge daemon_sig."""
    try:
        from src.ztare.gates._daemon_sig import verify as _vrfy
    except Exception:
        return False
    for r in _ledger_rows_raw():
        if (r.get("transition_type") == "manifest_receipt"
                and str(r.get("tick_id", "")) == str(tick_id)
                and str(r.get("manifest_kind", "")) == str(kind)
                and str(r.get("manifest_sha256", "")) == str(file_sha256)
                and _vrfy(str(r.get("official_state_hash", "")),
                          r.get("daemon_sig"))):
            return True
    return False


def _canon_wsha(witness: dict) -> str:

### posttick_runner lean_faithfulness + R2 submit
                             "(meso/macro genuinely optional here)"}))

    # 5 — lean_faithfulness: composes the EXISTING deterministic
    #     faithfulness layer (run_lean_proof_gate = extract → compile
    #     → axiom audit → v33 anti-laundering organs: vacuity /
    #     paraphrase / single-lemma / scalar-wrapper). The vacuity
    #     residual was over-claimed as human-only WITHOUT this; it is
    #     gateable for the known organ families. HARD when a thesis
    #     is declared. When NOT declared it is recorded (advisory) and
    #     the trigger-bind ("a closure-claiming tick MUST declare its
    #     Lean artifact") is the explicit residual sent to Meta-Darwin
    #     — NOT silently asserted complete.
    _tp = str(a.thesis_path).strip()
    if _tp:
        _thp = pathlib.Path(_tp)
        if not _thp.is_absolute():
            _thp = REPO / _thp
        _slug = (a.project_slug.strip()
                 or (_thp.parent.name if _thp.parent else "tick"))
        _lf_ok, _lf_rec = False, {}
        try:
            sys.path.insert(0, str(REPO))
            from src.ztare.gates.lean_proof_gate import (  # noqa: E402
                run_lean_proof_gate)
            _gr = run_lean_proof_gate(
                thesis_path=_thp, project_slug=_slug,
                ztare_proofs_root=(REPO / "ztare_proofs"),
                timeout_seconds=300, enforce_anti_laundering=True)
            _lf_ok = bool(_gr.get("gate_passed"))
            _lf_rec = {"gate_passed": _gr.get("gate_passed"),
                       "compiled": _gr.get("compiled"),
                       "axiom_audit_passed": _gr.get(
                           "axiom_audit_passed"),
                       "anti_laundering_passed": _gr.get(
                           "anti_laundering_passed"),
                       "v33_organ_flags": _gr.get("v33_organ_flags"),
                       "thesis": str(_thp.relative_to(REPO))
                       if str(_thp).startswith(str(REPO))
                       else str(_thp)}
        except Exception as e:  # noqa: BLE001
            _lf_ok = False
            _lf_rec = {"error": f"{type(e).__name__}: {e}"}
        steps.append(_step("lean_faithfulness", _lf_ok, _lf_rec,
                            hard=True))
    else:
        # F5 (Meta-Darwin bwdcoww2y): no-thesis must NOT be a free
        # advisory pass for a closure-claiming tick. Trigger from the
        # FROZEN goal text (runner sees --goal, which the daemon binds
        # == frozen start goal): if the goal claims a formal closure,
        # --thesis-path is MANDATORY ⇒ HARD FAIL when omitted. Only a
        # genuinely non-closure tick is honest N/A. Residual (claims
        # detectable only from close.f_row_body, not the goal) ⇒
        # daemon-side trigger, in the operator-routed schema bundle.
        _gl = str(a.goal).lower()
        _CLAIM = ("clay", "qed", "theorem", " lean", "lean ",
                  "formal proof", "compiled proof", "closure",
                  "proven", "∎", "lake build", "no sorry",
                  "sorry-free", "axiom-free")
        _claims = any(k in _gl for k in _CLAIM)
        if _claims:
            steps.append(_step(
                "lean_faithfulness", False,
                {"declared": False, "goal_claims_closure": True,
                 "matched": [k for k in _CLAIM if k in _gl],
                 "why": ("goal claims a formal closure but no "
                         "--thesis-path ⇒ HARD FAIL (caller-honesty "
                         "bypass closed for goal-detectable claims)")},
                hard=True))
        else:
            steps.append(_step(
                "lean_faithfulness", True,
                {"declared": False, "goal_claims_closure": False,
                 "residual": ("non-closure goal ⇒ honest N/A; "
    }
    (rdir / "posttick_manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False))
    # R2: register the manifest with the daemon (tamper-evident).
    _receipt_ok = False
    if complete:
        _rc, _ro = _run([PY, "-m", "src.ztare.gates.propose",
                         "--type", "manifest_receipt",
                         "--text", f"posttick manifest receipt {a.tick_id}",
                         "--goal", a.tick_id,
                         "--close", json.dumps(
                             {"tick_id": a.tick_id,
                              "manifest_kind": "posttick"})],
                        timeout=180)
        _receipt_ok = (_rc == 0)
    print(json.dumps({"status": manifest["status"],
                       "manifest": str((rdir / "posttick_manifest.json"
                                        ).relative_to(REPO)),
                       "receipt_registered": _receipt_ok,
                       "failed_hard_steps": [
                           s["step"] for s in steps
                           if s.get("hard") and not s["ok"]]}, indent=1))
    # FAIL-CLOSED: COMPLETE manifest AND a daemon-signed receipt.
    if not complete:
        return 2
    return 0 if _receipt_ok else 3


if __name__ == "__main__":
    raise SystemExit(main())


## Response (final codex verdict block)

**Verdict**

Artifact: **NO-GO** as a comprehensive close authority. Patchable, but not safe to bless as “done.”

Idea: **GO-WITH-CHANGES**. Daemon-stamped official state + signed receipts is the right shape. The artifact still has liveness and coverage gaps.

Single remaining failure mode even after fixes: **schema-complete, insight-empty ticks**. The daemon can prove the agent ran the required surfaces on the right tick; it still cannot prove the tick’s mathematical judgment was deep rather than shallow-but-valid paperwork.

**Findings**

1. **F1 false-fails the intended laptop→VPS path.**  
[tick_close.py](/scripts/public/control/tick_close.py:77) reads `stamped_state.official_transitions()` locally before calling `propose`. But enforce-mode `stamped_state` hardcodes local `/srv/ztare_official_store` [stamped_state.py](/src/ztare/gates/stamped_state.py:37), while `propose` supports remote-enforce by fetching/polling the VPS store [propose.py](/src/ztare/gates/propose.py:303). On a laptop with only `ZTARE_VERIFICATOR_SSH`, honest remote-started ticks can be refused before H7 submission.  
Fix: share `propose`’s remote fetch/verify path, or add `remote_official_transitions()` using the same base64 `cat` + local `chain_valid`.

2. **Decision-changed posttick closes crash.**  
[posttick_runner.py](/scripts/public/control/posttick_runner.py:205) enters the big-decision branch, then references undefined `fp` at line 208. Honest `--decision-changed` ticks cannot produce a COMPLETE posttick manifest.  
Fix: define `fp = _fpr / "contracts"` or use that path directly.

3. **“Chain-valid” is claimed but not enforced in daemon close-side lookups.**  
`_manifest_receipt_ok()` scans `_ledger_rows_raw()` and checks only `daemon_sig` [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:85). The close-side start row lookup does the same [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:597). Signature over `official_state_hash` is not the same as recomputing the row body and parent chain.  
Fix: call `chain_valid(_ledger_rows_raw())` once inside the daemon and use that set for start rows, duplicate checks, judge start lookups, and manifest receipts.

4. **Posttick is not exhaustive against rd_tick_brief’s MECE list.**  
`rd_tick_brief` says post-tick MECE includes Tier-3 pattern_026, Tier-3 closure_claim, adversarial steelman-kill, F-row, manifest maintenance, and memory [rd_tick_brief.py](/scripts/public/control/rd_tick_brief.py:599). `posttick_runner` only records `pattern_026` as advisory, calls the Tier-3 linter with the wrong CLI shape, and never runs `closure_claim` or steelman-kill as closure-adjacent hard legs [posttick_runner.py](/scripts/public/control/posttick_runner.py:306), while the linter requires `check <path>` [closure_claim_discipline_linter_tier3.py](/scripts/public/control/closure_claim_discipline_linter_tier3.py:401).  
Fix: add artifact path args; run `check <artifact> --check-type pattern_026`; run `closure_claim` + adversarial receipt when closure-adjacent; make those hard for closure-adjacent ticks.

5. **Locale drift is small but real.**  
The runners write manifests with `write_text(...)` and `ensure_ascii=False` [pretick_runner.py](/scripts/public/control/pretick_runner.py:340), [posttick_runner.py](/scripts/public/control/posttick_runner.py:351). Once written, daemon byte hashing is stable; the risk is write-time encoding under non-UTF-8 locale.  
Fix: `write_text(..., encoding="utf-8")`.

**Specific Answers**

R2 propose path: OK on argparse and ordering. `propose` requires `--type` and `--text`; `--goal` is optional; runners pass text, goal, and close JSON [propose.py](/src/ztare/gates/propose.py:229). The daemon handles `manifest_receipt` before generic `evaluate()` [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:860), so relapse gates do not quarantine benign receipts.

F1/b1djdevru: In an untampered local ledger, sending compiler cid now makes the line-958 foreign-contract check pass honest closes and reject foreign contracts [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:957). But the daemon-side raw-row lookup means the guarantee is weaker than the prose.

Residual Meta-Darwin:
- F3 dormant: **CHEAP-FIX-NOW**. Require `forecast_contract_id` on research `start_tick`, update the start emitter, freeze or fail.
- R5 registry provenance: **CHEAP-FIX-NOW for provenance, IRREDUCIBLE for curation**. Move registry hash into daemon-signed official state; operator still curates target truth.
- R2 depth: **IRREDUCIBLE** as depth certification. Receipts prove execution/tamper evidence, not adequacy. Current prose should stop implying more.
tokens used
192.104
**Verdict**

Artifact: **NO-GO** as a comprehensive close authority. Patchable, but not safe to bless as “done.”

Idea: **GO-WITH-CHANGES**. Daemon-stamped official state + signed receipts is the right shape. The artifact still has liveness and coverage gaps.

Single remaining failure mode even after fixes: **schema-complete, insight-empty ticks**. The daemon can prove the agent ran the required surfaces on the right tick; it still cannot prove the tick’s mathematical judgment was deep rather than shallow-but-valid paperwork.

**Findings**

1. **F1 false-fails the intended laptop→VPS path.**  
[tick_close.py](/scripts/public/control/tick_close.py:77) reads `stamped_state.official_transitions()` locally before calling `propose`. But enforce-mode `stamped_state` hardcodes local `/srv/ztare_official_store` [stamped_state.py](/src/ztare/gates/stamped_state.py:37), while `propose` supports remote-enforce by fetching/polling the VPS store [propose.py](/src/ztare/gates/propose.py:303). On a laptop with only `ZTARE_VERIFICATOR_SSH`, honest remote-started ticks can be refused before H7 submission.  
Fix: share `propose`’s remote fetch/verify path, or add `remote_official_transitions()` using the same base64 `cat` + local `chain_valid`.

2. **Decision-changed posttick closes crash.**  
[posttick_runner.py](/scripts/public/control/posttick_runner.py:205) enters the big-decision branch, then references undefined `fp` at line 208. Honest `--decision-changed` ticks cannot produce a COMPLETE posttick manifest.  
Fix: define `fp = _fpr / "contracts"` or use that path directly.

3. **“Chain-valid” is claimed but not enforced in daemon close-side lookups.**  
`_manifest_receipt_ok()` scans `_ledger_rows_raw()` and checks only `daemon_sig` [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:85). The close-side start row lookup does the same [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:597). Signature over `official_state_hash` is not the same as recomputing the row body and parent chain.  
Fix: call `chain_valid(_ledger_rows_raw())` once inside the daemon and use that set for start rows, duplicate checks, judge start lookups, and manifest receipts.

4. **Posttick is not exhaustive against rd_tick_brief’s MECE list.**  
`rd_tick_brief` says post-tick MECE includes Tier-3 pattern_026, Tier-3 closure_claim, adversarial steelman-kill, F-row, manifest maintenance, and memory [rd_tick_brief.py](/scripts/public/control/rd_tick_brief.py:599). `posttick_runner` only records `pattern_026` as advisory, calls the Tier-3 linter with the wrong CLI shape, and never runs `closure_claim` or steelman-kill as closure-adjacent hard legs [posttick_runner.py](/scripts/public/control/posttick_runner.py:306), while the linter requires `check <path>` [closure_claim_discipline_linter_tier3.py](/scripts/public/control/closure_claim_discipline_linter_tier3.py:401).  
Fix: add artifact path args; run `check <artifact> --check-type pattern_026`; run `closure_claim` + adversarial receipt when closure-adjacent; make those hard for closure-adjacent ticks.

5. **Locale drift is small but real.**  
The runners write manifests with `write_text(...)` and `ensure_ascii=False` [pretick_runner.py](/scripts/public/control/pretick_runner.py:340), [posttick_runner.py](/scripts/public/control/posttick_runner.py:351). Once written, daemon byte hashing is stable; the risk is write-time encoding under non-UTF-8 locale.  
Fix: `write_text(..., encoding="utf-8")`.

**Specific Answers**

R2 propose path: OK on argparse and ordering. `propose` requires `--type` and `--text`; `--goal` is optional; runners pass text, goal, and close JSON [propose.py](/src/ztare/gates/propose.py:229). The daemon handles `manifest_receipt` before generic `evaluate()` [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:860), so relapse gates do not quarantine benign receipts.

F1/b1djdevru: In an untampered local ledger, sending compiler cid now makes the line-958 foreign-contract check pass honest closes and reject foreign contracts [commit_membrane_daemon.py](/src/ztare/gates/commit_membrane_daemon.py:957). But the daemon-side raw-row lookup means the guarantee is weaker than the prose.

Residual Meta-Darwin:
- F3 dormant: **CHEAP-FIX-NOW**. Require `forecast_contract_id` on research `start_tick`, update the start emitter, freeze or fail.
- R5 registry provenance: **CHEAP-FIX-NOW for provenance, IRREDUCIBLE for curation**. Move registry hash into daemon-signed official state; operator still curates target truth.
- R2 depth: **IRREDUCIBLE** as depth certification. Receipts prove execution/tamper evidence, not adequacy. Current prose should stop implying more.
