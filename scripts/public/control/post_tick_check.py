#!/usr/bin/env python3
"""post_tick_check.py — Research Director close-out gate (the post-tick
counterpart to the rd_tick_brief pre-tick surface).

The apparatus was pre-tick-heavy / post-tick-light: closing obligations
(resolve prediction ledger, ex-post close GP-230 contracts, add a GP-233
evidence row when a decision changed, log a catch, write the F-row) had
NO mechanized close gate — they were only caught retroactively by the
*next* tick's pre-check, or relied on agent memory. This gate asserts
them at tick close.

Enforcement (per operator decision 2026-05-15 — "blocking on hard
obligations"):

  HARD FAIL (exit 1 -> next pre-tick blocks dispatch):
    - fresh unresolved Tier-1 prediction-ledger debt
      (REUSES rd_tick_brief.prediction_closure_hygiene — not reimplemented)
    - a GP-230 contract created in the tick window whose internal id
      appears in NO outcome AND NO score file (deterministically unmet)
    - --decision-changed declared but no GP-233 evidence-ledger update
      in the window (the caller asserted it, so the row is a hard duty)

  WARN (advisory — judgment-laden, cannot be auto-proven):
    - no F-row in EXPERIMENT_TRACK_RECORD.md for the window
    - catch self-attestation (a catch cannot be auto-detected; the
      independence rule author!=concurring is a human/meta-audit call)
    - a contract whose id could not be extracted (not a false block)

A blocking gate must never false-FAIL: anything not deterministically
provable is downgraded to WARN.

Usage:
  ./venv/bin/python scripts/public/control/post_tick_check.py
  ... --window-hours 12 [--since ISO8601] [--decision-changed] [--json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONTRACTS = REPO / "analytics/public/forecast_pool/contracts"
OUTCOMES = REPO / "analytics/public/forecast_pool/outcomes"
SCORES = REPO / "analytics/public/forecast_pool/scores"
GP233 = REPO / "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"
CATCH = REPO / "analytics/public/ledgers/catch/catch_ledger.jsonl"
TRACK = REPO / "research_areas/EXPERIMENT_TRACK_RECORD.md"
RD_TICK_BRIEF = REPO / "scripts/public/control/rd_tick_brief.py"


def _load_rd_tick_brief():
    """Reuse rd_tick_brief's canonical PL logic — do not reimplement."""
    spec = importlib.util.spec_from_file_location("rd_tick_brief", RD_TICK_BRIEF)
    m = importlib.util.module_from_spec(spec)
    sys.modules["rd_tick_brief"] = m
    spec.loader.exec_module(m)  # type: ignore[attr-defined]
    return m


def _mtime(p: Path) -> datetime:
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)


def _extract_id(obj: dict) -> str | None:
    for k in ("contract_id", "id", "name", "slug", "question_id", "question"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def check(window_hours: int, since: datetime | None,
          decision_changed: bool, owner: str | None = None) -> dict:
    cutoff = since or (datetime.now(timezone.utc) - timedelta(hours=window_hours))
    hard_fail: list[str] = []
    warn: list[str] = []

    # ── CALIB-CLASS REGISTRY (2026-05-16) ────────────────────────────
    # Makes the calibration_gate guarantee LEGIBLE + prevents the
    # "universal-wire" over-reach. Each HARD-capable leg is exactly one
    # of two classes; only `heuristic-calibration-gated` legs route
    # through calibration_gate.hard_allowed (empty ledger ⇒ stays
    # advisory). Routing a deterministic leg through it = REGRESSION
    # (would refuse a legitimate deterministic block on an empty ledger).
    #   #1  PL-debt ............................. deterministic-exempt
    #   #2  GP-230 contract-not-closed (owner-sc) deterministic-exempt
    #   #3  GP-233 on --decision-changed ........ deterministic-exempt
    #   #3b conclusion-soundness ................ deterministic-by-token
    #         -convention-exempt (FAIL = missing [MD-SURVIVED] token;
    #          gating it on an empty ledger would DISABLE a working
    #          decision-critical gate — exempt, NOT calibration-gated)
    #   #8  prescription-surfacing (gap_e) ...... advisory-only; a flip
    #          to HARD is mechanically forbidden absent a calibration
    #          entry (calibration_gate refuses absent-entry) — nothing
    #          to wire today; guarantee already holds by mechanism
    #   #8b primitives-considered (gap_f) ....... advisory-only (idem)
    #   #8c dispatch-ledger (gap_g) ............. heuristic-calibration
    #         -gated → ALREADY routes via hard_allowed("gap_g", owner)
    # FUTURE-FLIP RULE (policy; lint is the other agent's reviewed
    # calibration thread, NOT a mid-session build): any NEW heuristic→
    # HARD leg MUST call calibration_gate.hard_allowed before HARD; a
    # deterministic leg MUST NOT (document its class here instead).
    # ─────────────────────────────────────────────────────────────────

    # 1. Tier-1 prediction-ledger closure — reuse the canonical gate.
    try:
        rtb = _load_rd_tick_brief()
        # prediction_closure_hygiene prints its section + returns 1 on
        # fresh Tier-1 debt. That return IS the authoritative signal.
        pl_rc = rtb.prediction_closure_hygiene(hours=window_hours)
        if pl_rc != 0:
            hard_fail.append(
                "fresh unresolved Tier-1 prediction-ledger debt "
                "(see prediction_closure_hygiene output above)")
    except Exception as e:  # never false-block on harness error
        warn.append(f"PL closure check degraded (advisory): {e}")

    # 2. GP-230 contracts created in window with no outcome/score.
    if CONTRACTS.exists():
        out_blob = ""
        for d in (OUTCOMES, SCORES):
            if d.exists():
                for f in d.glob("*.json"):
                    try:
                        out_blob += f.read_text(errors="ignore")
                    except Exception:
                        pass
        macro_meso_open = 0
        for cf in CONTRACTS.glob("*.json"):
            try:
                if _mtime(cf) < cutoff:
                    continue
                cobj = json.loads(cf.read_text(errors="ignore"))
                cid = _extract_id(cobj)
            except Exception:
                continue
            if cid is None:
                warn.append(f"contract {cf.name}: no extractable id "
                            "(cannot prove closed — self-verify)")
                continue
            if cid in out_blob:
                continue
            # LAYER-AWARE (2026-05-15): only `micro` contracts are
            # tick-scoped and owed at close. macro/meso span their own
            # horizon (30d/multi-tick) — an open macro/meso contract is
            # EXPECTED, not debt. Hard-blocking it would be a false-FAIL
            # (a blocking gate must never false-FAIL). Unknown layer ->
            # advisory (don't hard-block on a missing field either).
            layer = str(cobj.get("layer", "")).lower()
            if layer == "micro":
                # OWNER-SCOPED (2026-05-16): isolation unit = substrate/RD.
                # A blocking gate must gate the ACTING RD on ITS OWN debt
                # only — another RD's open micro contract (different
                # `created_by`) must be VISIBLE but ADVISORY, never
                # cross-block this RD's loop. (Concrete defect this fixes:
                # the NS RD's tick6xx contracts HARD-blocked the bundle
                # RD's post_tick repeatedly.) Back-compat: owner=None ⇒
                # legacy global behavior, no regression. Unattributable
                # (no created_by) under a set owner ⇒ advisory, not
                # hard-block and not silently passed. Mirrors the
                # rd_tick_brief --blocking-substrate + conclusion-soundness
                # own=HARD/other=WARN precedent.
                creator = str(cobj.get("created_by") or "").strip()
                if owner is None or creator == owner:
                    hard_fail.append(
                        f"micro GP-230 contract created this window not "
                        f"ex-post closed: id '{cid}' ({cf.name}) absent from "
                        f"outcomes/ and scores/"
                        + ("" if owner is None
                           else f" [owner={owner}: own-debt, HARD]"))
                elif creator:
                    warn.append(
                        f"micro GP-230 contract '{cid}' created by "
                        f"'{creator}' (≠ acting RD '{owner}') open in-window "
                        f"— OTHER-RD/substrate: advisory, NOT cross-blocking "
                        f"this RD's loop (owner-scoped isolation).")
                else:
                    warn.append(
                        f"micro GP-230 contract '{cid}' has no `created_by` "
                        f"— unattributable under owner='{owner}'; advisory "
                        f"(backfill created_by to enable owner-scoping).")
            elif layer in ("macro", "meso"):
                macro_meso_open += 1
            else:
                warn.append(f"contract {cf.name}: no/unknown layer "
                            f"('{cobj.get('layer')}') — backfill layer; "
                            "treated advisory, not blocking")
        if macro_meso_open:
            warn.append(f"{macro_meso_open} macro/meso contract(s) open "
                        "in-window — expected (multi-tick horizon); "
                        "tracked, NOT a tick-close obligation")

    # 3. GP-233 evidence row when a decision changed.
    if decision_changed:
        fresh_gp233 = GP233.exists() and _mtime(GP233) >= cutoff
        if not fresh_gp233:
            hard_fail.append(
                "--decision-changed declared but GP-233 evidence ledger "
                f"not updated in window ({GP233.relative_to(REPO)})")
    else:
        warn.append("if any decision changed this tick, re-run with "
                    "--decision-changed (GP-233 evidence row then required)")

    # 3b. CONCLUSION-TIME ADVERSARIAL-SURVIVAL GATE (mechanizes
    # be-Meta-Darwin-to-self so the operator need not be the external
    # Meta-Darwin). RCA 2026-05-16: every major correction this session
    # came from the operator attacking a just-formed conclusion, never
    # from self-triggered recursion — close-out gates checked bookkeeping
    # not soundness; negatives got an asymmetric pass; tick-throughput
    # pressure suppressed self-attack. Forcing fix: a today F-row whose
    # verdict tags assert a refutation / settled-negative / terminal
    # belief-change MUST carry an adversarial-survival block — strongest
    # counter-hypothesis + a discriminating test + evidence the test was
    # RUN (not imagined) before the verdict was stamped. Scoped to
    # explicit refutation tags to avoid false-blocking (a noisy gate gets
    # ignored — the buried-prescription failure mode).
    if TRACK.exists():
        _today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # SYMMETRIC trigger set (cross-agent feedback 2026-05-16): a
        # reversal of a prior settled-negative ("the kill was a category
        # error / route alive / provenance restored") is ITSELF a strong
        # belief-change claim and needs the SAME adversarial-survival
        # block — else the gate has an asymmetry loophole (blocks naked
        # negatives but lets naked over-optimistic reversals through).
        _NEG = ("_refuted", "empirically_refuted", "settled_negative",
                "terminal_verdict", "_terminal", "preconcluded_refuted",
                # reversal / over-kill side (symmetric):
                "reverses", "reverses_", "kill_reverted", "over-killed",
                "overkilled", "category_error", "category-error",
                "re-confirmed", "reconfirmed", "_restored", "downgrade_lifted",
                "falsified-prior", "un-refuted", "prior_kill_wrong",
                "was_wrong", "_lifted", "route_alive", "revives")
        _SURV_HYP = ("counter-hypothesis", "counter hypothesis",
                     "strongest counter", "adversari", "meta-darwin",
                     "steelman")
        _SURV_TEST = ("discriminating test", "discriminating experiment",
                      "discriminating measurement")
        _SURV_RUN = ("ran ", "was run", "run, not imagined", "verified through",
                     "executed", "diagnosed the", "read the actual",
                     "actual error")
        # Explicit cheap satisfier the author controls (unambiguous, and it
        # admits CROSS-ROW adversarial recursion: a naked conclusion row may
        # be survived by a later corrector row that carries the token and
        # cites it). Compliance is one structured tag — trivial to add,
        # impossible to satisfy without actually naming the counter +
        # the test that was run.
        _TOKEN = "md-survived"  # tag: [MD-SURVIVED counter=… test=… ran=…]
        # Ownership scope: this workstream authors F-GP225-/F-METHODOLOGY-
        # rows; F-NS- belongs to the parallel NS agent — its hygiene is
        # surfaced (WARN) but does NOT hard-block this loop (no cross-agent
        # false-block; same principle as --blocking-substrate for PL).
        _OWN = ("f-gp225-", "f-methodology-")
        try:
            text = TRACK.read_text(errors="ignore")
            survived_ids = set()  # rows explicitly cited as adversarially survived
            for ln in text.splitlines():
                lo = ln.lower()
                if _TOKEN in lo or "survives:" in lo or "corrects-and-tests:" in lo:
                    import re as _re
                    survived_ids |= set(_re.findall(r"f-[a-z0-9\-]+", lo))
            for ln in text.splitlines():
                if _today not in ln or not ln.startswith("| F-"):
                    continue
                low = ln.lower()
                if not any(t in low for t in _NEG):
                    continue
                rid = ln.split("|", 2)[1].strip()
                ridl = rid.lower()[:70]
                cited = any(ridl in sid or sid in ridl
                            for sid in survived_ids)
                has_block = (
                    _TOKEN in low
                    or (any(h in low for h in _SURV_HYP)
                        and any(t in low for t in _SURV_TEST)
                        and any(r in low for r in _SURV_RUN))
                    or cited)
                if has_block:
                    continue
                msg = (f"conclusion-soundness: F-row '{rid[:70]}' asserts a "
                       "refutation/terminal/settled-negative verdict without "
                       "an adversarial-survival block. Add tag "
                       "`[MD-SURVIVED counter=<strongest counter-hyp> "
                       "test=<discriminating test> ran=<evidence it was RUN "
                       "not imagined>]` (or a later corrector row citing this "
                       "id via `survives:<id>`). Be-Meta-Darwin-to-self is a "
                       "precondition for recording a negative.")
                if ridl.startswith(_OWN):
                    hard_fail.append(msg)
                else:
                    warn.append(msg + " [other-agent row: WARN, not "
                                "cross-blocking this loop]")
        except Exception:
            pass

    # 4. F-row presence (advisory).
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if TRACK.exists():
        try:
            if today not in TRACK.read_text(errors="ignore"):
                warn.append("no EXPERIMENT_TRACK_RECORD row dated today "
                            "(F/E-row owed per Findings Recording Procedure)")
        except Exception:
            pass

    # 5. Catch self-attestation (advisory + visible counts).
    pend = rat = 0
    if CATCH.exists():
        for ln in CATCH.read_text(errors="ignore").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                s = json.loads(ln).get("status")
                pend += s == "pending"
                rat += s == "ratified"
            except Exception:
                pass
    warn.append(f"catch self-attest: if a catch occurred, log it "
                f"(author!=concurring) — ledger now pending={pend} "
                f"ratified={rat}")

    # 6. Forward-evidence clean-corpus hygiene (v35) — advisory, never
    # hard-blocks on schema (feedback's hard-fails are PL/contract/GP-233).
    try:
        import subprocess
        fe = subprocess.run(
            [sys.executable, str(REPO / "scripts/public/validators/validate_forward_evidence.py")],
            capture_output=True, text=True, timeout=30)
        if fe.returncode != 0:
            warn.append("forward_evidence_ledger fails validation "
                        "(v35 clean-corpus) — fix before accruing more rows")
    except Exception as e:
        warn.append(f"forward-evidence check degraded (advisory): {e}")

    # FORECAST-CONTRACT-SCHEMA leg (alias GAP-D; advisory). As of 2026-05-16
    # status_rows / cmd_warm_daemon_once skip-and-flag malformed
    # contracts (next_action=malformed_skipped) instead of aborting, so
    # the daemon / market re-derive / warm-consumer path keeps running on
    # valid work. This check stays wired so the validator can't go dead
    # (the validate_catch_ledger lesson) and malformed stubs still get
    # surfaced for hygiene quarantine.
    try:
        import subprocess
        fc = subprocess.run(
            [sys.executable, str(REPO / "scripts/public/validators/validate_forecast_contracts.py")],
            capture_output=True, text=True, timeout=30)
        if fc.returncode != 0:
            warn.append("forecast_pool/contracts has malformed entries "
                        "(GAP-D) — daemon now SKIPS+FLAGS them "
                        "(next_action=malformed_skipped), valid work "
                        "unaffected; quarantine the stubs for hygiene")
    except Exception as e:
        warn.append(f"forecast-contract check degraded (advisory): {e}")

    # 7. PENDING-RATIFICATION-AGING leg (alias GAP-B) — surfaces the independent-
    # ratifier bottleneck: forward rows that can never become real
    # closures until a DISTINCT agent / human:operator ratifies them.
    fe_ledger = REPO / "analytics/public/ledgers/forward_evidence/forward_evidence_ledger.jsonl"
    if fe_ledger.exists():
        pend = ratified = 0
        for ln in fe_ledger.read_text(errors="ignore").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                st = json.loads(ln).get("status")
                pend += st == "pending_ratification"
                ratified += st == "ratified"
            except Exception:
                pass
        if pend and ratified == 0:
            warn.append(
                f"forward-evidence: {pend} row(s) pending_ratification, "
                f"0 ever ratified — the independent-ratifier bottleneck is "
                f"unbroken (a row only counts once a DISTINCT agent / "
                f"human:operator ratifies it). Designate a ratifier.")
        elif pend:
            warn.append(f"forward-evidence: {pend} pending_ratification "
                        f"vs {ratified} ratified — ratifier throughput lag")

    # 8. PRESCRIPTION-SURFACING-COVERAGE leg (alias GAP-E; calib channel
    #    `gap_e`; advisory). Mechanizes
    # away the buried-prescription / point-fix treadmill: a prescribed
    # move (menu leaf/sub_class, pattern, mandate duty) that lands
    # NON-FORCING goes dead-at-precheck silently until the operator
    # notices the Nth recurrence and a bespoke block is hand-authored.
    # This leg surfaces the whole gap set EVERY tick so the treadmill
    # cannot re-form. Advisory (the surfacing test is a grep heuristic;
    # never false-FAIL — flip blocking only after calibration). Stays
    # wired so the validator can't go dead (validate_catch_ledger lesson).
    try:
        import subprocess
        ps = subprocess.run(
            [sys.executable, str(REPO / "scripts/public/validators/validate_prescription_surfacing.py")],
            capture_output=True, text=True, timeout=30)
        n_gap = ps.stdout.count("surfacing_gap")
        if n_gap:
            warn.append(
                f"prescription-surfacing (GAP-E): {n_gap} prescription(s) "
                f"have NO forcing surfacing on the precheck path — they "
                f"are dead-at-precheck (buried-prescription treadmill). "
                f"Run validate_prescription_surfacing.py; force the "
                f"decision-critical ones or accept+annotate the rest.")
    except Exception as e:
        warn.append(f"prescription-surfacing check degraded (advisory): {e}")

    # 8b. PRIMITIVES-CONSIDERED leg (alias GAP-F; calib channel `gap_f`;
    #     advisory). Sibling of
    # GAP-E (does NOT fork §3b). Mechanizes away "surfaced-but-not-used
    # primitive": a post-announce tick F-row whose scope class-matches a
    # high-impact registry primitive must NAME it via
    # `primitives_considered:<ID>` / `why_not:<ID>`. Retroactive-exempt
    # + advisory until calibrated (never false-FAIL); registry-derived
    # (auto-tracks renames). Stays wired so it can't go dead.
    try:
        import subprocess
        pc = subprocess.run(
            [sys.executable, str(REPO / "scripts/public/validators/validate_primitives_considered.py")],
            capture_output=True, text=True, timeout=30)
        n_pc = pc.stdout.count("primitives_considered (GAP-F)")
        if n_pc:
            warn.append(
                f"primitives-considered (GAP-F): {n_pc} post-announce "
                f"tick F-row(s) class-match a high-impact registry "
                f"primitive but do not NAME it via "
                f"`primitives_considered:<ID>`/`why_not:<ID>`. Run "
                f"validate_primitives_considered.py; consider+name it or "
                f"record why_not.")
    except Exception as e:
        warn.append(f"primitives-considered check degraded (advisory): {e}")

    # 8c. DISPATCH-LEDGER-SELF-ACCOUNT leg (alias GAP-G; calib channel
    #     `gap_g`). OWNER-SCOPED HARD
    # (the mechanization-guarantee fix, 2026-05-16): an advisory gate is
    # glossable ⇒ guarantees nothing. Reuses the post_tick --owner /
    # RD_OWNER meta-architecture: subprocess runs GAP-G with
    # `--owner <owner> --blocking`; a non-zero exit = the ACTING owner
    # has an OWN `owner:<id>`-tagged F-row that gloss-omits / mis-classes
    # `dispatch_ledger:` ⇒ HARD-FAIL (un-glossable for the author,
    # attributable = the consequence). Other-owner / unattributed
    # (legacy backlog) rows stay advisory ⇒ never poison the block,
    # never false-FAIL. owner=None ⇒ legacy global advisory (back-compat,
    # no regression). Path-independent; stays wired so it can't go dead.
    try:
        import subprocess
        dl_cmd = [sys.executable,
                  str(REPO / "src/ztare/validator/dispatch_ledger_check.py")]
        if owner:
            dl_cmd += ["--owner", owner, "--blocking"]
        dl = subprocess.run(dl_cmd, capture_output=True, text=True,
                             timeout=30)
        own_hard = [ln for ln in dl.stdout.splitlines()
                    if ln.startswith("HARD [owner=")]
        n_adv = dl.stdout.count("WARN: dispatch_ledger (GAP-G)")
        if owner and dl.returncode == 1 and own_hard:
            hard_fail.append(
                f"dispatch-ledger (GAP-G) OWNER-SCOPED HARD: "
                f"{len(own_hard)} F-row(s) owned by '{owner}' "
                f"(owner:<id> tag) gloss-omit or mis-class "
                f"`dispatch_ledger:`. This tick cannot close until the "
                f"acting owner's own rows carry "
                f"`dispatch_ledger: none|<sanctioned_class>`. "
                f"(un-glossable, attributable; other/legacy rows advisory)")
        if n_adv:
            warn.append(
                f"dispatch-ledger (GAP-G): {n_adv} advisory (other-owner "
                f"/ unattributed legacy) F-row(s) lack a "
                f"`dispatch_ledger:` self-account — not the acting "
                f"owner's HARD debt; backfill `owner:`+ledger to retire.")
    except Exception as e:
        warn.append(f"dispatch-ledger check degraded (advisory): {e}")

    return {"hard_fail": hard_fail, "warn": warn,
            "passed": not hard_fail, "window_hours": window_hours,
            "cutoff_utc": cutoff.isoformat()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-hours", type=int, default=12)
    ap.add_argument("--since", help="ISO8601; overrides --window-hours")
    ap.add_argument("--decision-changed", action="store_true")
    ap.add_argument("--owner", default=None,
                    help="acting RD identity (= contract `created_by`). "
                         "When set, only THIS RD's own unresolved micro "
                         "contracts HARD-block; other RDs'/substrates' are "
                         "advisory (owner-scoped isolation). Absent = "
                         "legacy global behavior (no regression).")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    since = None
    if a.since:
        try:
            since = datetime.fromisoformat(a.since.replace("Z", "+00:00"))
        except ValueError:
            print(f"bad --since: {a.since}", file=sys.stderr)
            return 2
    # De-orphan the owner-scoped isolation fix: the standard tick-close
    # carries owner via RD_OWNER env when --owner is not passed (set once
    # per RD/session, same pattern as FORECAST_POOL_ROOT). Truly-unset =>
    # owner=None => legacy global (back-compat, no regression). This is
    # the activation follow-through — without it the fix is opt-in and
    # orphans (the orphan trap, flagged in the fix F-row).
    owner = a.owner or os.environ.get("RD_OWNER") or None
    if owner and not a.owner:
        print(f"  (owner-scoped via RD_OWNER={owner})")
    r = check(a.window_hours, since, a.decision_changed, owner)
    # PREV-TICK-CLOSEOUT-HANDSHAKE leg (alias GAP-C): persist verdict so
    # the pre-tick (rd_tick_brief) can
    # MECHANICALLY block the next dispatch when the last post-tick did
    # not clear — "exit 1 -> next pre-tick blocks dispatch" was mandate
    # prose until this state handshake existed.
    try:
        state_p = REPO / "analytics/public/forecast_pool/status/post_tick_state.json"
        state_p.parent.mkdir(parents=True, exist_ok=True)
        state_p.write_text(json.dumps({
            "passed": r["passed"],
            "hard_fail_count": len(r["hard_fail"]),
            "hard_fail": r["hard_fail"],
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2) + "\n")
    except Exception:
        pass  # never let state-write break the gate itself
    if a.json:
        print(json.dumps(r, indent=2))
        return 0 if r["passed"] else 1
    print("\n=== post_tick_check (RD close-out gate) ===")
    print(f"  window: last {r['window_hours']}h (cutoff {r['cutoff_utc']})")
    if r["hard_fail"]:
        print(f"  HARD FAIL ({len(r['hard_fail'])}) — close these before next dispatch:")
        for x in r["hard_fail"]:
            print(f"    FAIL  {x}")
    else:
        print("  HARD obligations: all clear")
    for x in r["warn"]:
        print(f"    WARN  {x}")
    print(f"  -> exit {0 if r['passed'] else 1}"
          + ("" if r["passed"] else " (next pre-tick blocks dispatch)"))
    return 0 if r["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
