#!/usr/bin/env python3
"""posttick_runner — the SYMMETRIC back half of pretick_runner.

Operator (2026-05-18): "can we do the same for the post checks ...
have we been comprehensively exhaustive". The pre-tick is forced by
pretick_runner + the GP-241 daemon HARD gate; this forces the
POST-tick MECE legs the brief enumerates (rd_tick_brief l.599-606)
the same way: each leg RUNS an existing tool and emits a receipt;
fail-closed unless every HARD leg passes; bound to the FROZEN signed
start row by the SAME compiler-cid namespace the daemon uses
(presence != this-tick). The daemon post-gate (mirrored from the
cold-cleared pre-gate) HARD-requires this manifest on tick_close.

HARD legs (gate `complete`):
  1 pretick_bound        — the COMPLETE pretick_manifest for THIS
                           tick exists and is contract/goal-bound
                           (post presupposes a real pre; binds
                           pre<->post symmetrically).
  2 post_tick_check      — post_tick_check.py --owner [..] exit 0
                           (its deterministic HARD legs clear).
  3 micro_resolved       — the tick's micro forecast contract is
                           RESOLVED *and* a recognized independent
                           forecaster bet existed first
                           (never-resolve-before-forecaster; verified,
                           not performed here).
  4 micro_scored         — the resolved micro contract has a score
                           artifact, so the market actually learns
                           from the outcome.
  5 big_decision_forecast (only if --decision-changed) — a FRESH
                           meso OR macro contract exists. Operation-
                           alises "meso/macro optional, but MANDATORY
                           for big decisions".

ADVISORY-recorded (NOT gated — quality/scope of a linter is the
irreducibly-advisory class; a hard flip would false-FAIL honest work,
violating the post_tick_check don't-false-FAIL invariant):
  closed_reflection_wake, tier3_pattern_026, memory_touched.

Honest bound (carried): forces the post-tick is EXECUTED. Does not
certify the closure is mathematically faithful (the BKM Icc-vs-Ico
class) — that residual stays with break-only adversary + operator.
Composes: post_tick_check.py, forecast_pool contracts/forecaster state,
closure_claim_discipline_linter_tier3.py, pre_tick_obligation_
compiler.start_tick (cid namespace).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[3]
PY = sys.executable
FORECASTER_ALIASES = {
    "codex": "codex",
    "codex_forecaster": "codex",
    "codexforecaster": "codex",
    "claude": "claude",
    "claude_forecaster": "claude",
    "claudeforecaster": "claude",
}


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()[:16]


def _run(cmd: list[str], timeout: int = 240) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=str(REPO), capture_output=True,
                            text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 99, f"__RUN_ERROR__ {type(e).__name__}: {e}"


def _step(name: str, ok: bool, receipt: dict, hard: bool = True) -> dict:
    return {"step": name, "ok": bool(ok), "hard": bool(hard),
            "receipt": receipt,
            "receipt_sha": _sha(json.dumps(receipt, sort_keys=True,
                                           ensure_ascii=False))}


def _frozen_start_binding_error(
    *,
    tick_id: str,
    contract_id: str,
    substrate: str,
    goal: str,
) -> str | None:
    """Fail before writing a posttick manifest if frozen fields differ.

    This is a client-side guard only. The daemon remains authoritative at
    close, but catching mismatches here prevents agent-writable bad receipts
    that otherwise surface only after all close payload work is done.
    """
    store_raw = os.environ.get("ZTARE_OFFICIAL_STORE")
    if not store_raw:
        return None
    ledger = pathlib.Path(store_raw) / "official" / "transitions.stamped.jsonl"
    if not ledger.is_file():
        return None
    start: dict | None = None
    for line in reversed(ledger.read_text(
        encoding="utf-8", errors="ignore"
    ).splitlines()):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(row, dict)
            and row.get("transition_type") == "start_tick"
            and row.get("tick_id") == tick_id
        ):
            start = row
            break
    if not start:
        return None
    frozen_contract = str(start.get("forecast_contract_id") or "")
    if frozen_contract and frozen_contract != contract_id:
        return (
            "posttick contract mismatch: "
            f"{contract_id!r} != frozen start {frozen_contract!r}. "
            "Use the forecast contract bound at start_tick."
        )
    frozen_substrate = str(start.get("substrate") or "")
    if frozen_substrate and frozen_substrate != substrate:
        return (
            "posttick substrate mismatch: "
            f"{substrate!r} != frozen start {frozen_substrate!r}. "
            "Rerun posttick with the frozen start substrate."
        )
    frozen_goal = str(start.get("goal") or "").strip()
    if frozen_goal and frozen_goal != goal.strip():
        return (
            "posttick goal mismatch: supplied goal does not byte-match the "
            "frozen start_tick goal. Copy the frozen goal verbatim."
        )
    return None


def _norm_agent_id(value: object) -> str:
    return "".join(ch for ch in str(value or "").strip().lower()
                   if ch.isalnum() or ch in "_:-")


def _recognized_forecaster_rows(root: pathlib.Path, cid: str) -> list[dict]:
    out: list[dict] = []
    fdir = root / "forecasts" / cid
    if not fdir.is_dir():
        return out
    for path in sorted(fdir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        agent_id = str(payload.get("agent_id") or path.stem)
        canonical = FORECASTER_ALIASES.get(_norm_agent_id(agent_id))
        if canonical not in {"claude", "codex"}:
            continue
        out.append({
            "agent_id": agent_id,
            "canonical_agent_id": canonical,
            "forecasted_at": payload.get("forecasted_at"),
            "path": str(path.relative_to(REPO)),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal", required=True)
    ap.add_argument("--substrate", required=True)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--tick-id", required=True)
    ap.add_argument("--contract-id", required=True,
                    help="the tick's forecast-pool contract slug "
                         "(must be RESOLVED with a prior recognized "
                         "independent forecaster bet).")
    ap.add_argument("--decision-changed", action="store_true",
                    help="declare this tick changed a decision-critical "
                         "decision ⇒ a FRESH meso/macro forecast is "
                         "then MANDATORY (big-decision trigger).")
    ap.add_argument("--thesis-path", default="",
                    help="path to the tick's thesis.md (Lean closure "
                         "artifact). If given, lean_faithfulness is a "
                         "HARD leg: run_lean_proof_gate (compile + "
                         "axiom audit + v33 anti-laundering organs) "
                         "must pass. This composes the EXISTING "
                         "deterministic faithfulness layer — the "
                         "vacuity residual was over-claimed as "
                         "human-only without it.")
    ap.add_argument("--project-slug", default="",
                    help="project slug for the Lean gate (defaults to "
                         "the thesis parent dir name).")
    ap.add_argument("--artifact-path", default="",
                    help="path to the tick's primary written artifact "
                         "(thesis/analysis md). Cold review bq4z7midf "
                         "F4: closure-adjacent ticks REQUIRE it — the "
                         "deterministic Tier-1 closure_claim linter is "
                         "then a HARD leg; Tier-3 multi-LLM is recorded "
                         "advisory (a provider outage must not "
                         "false-FAIL an honest close).")
    ap.add_argument("--skip-closed-reflection-wake", action="store_true",
                    help="do not enqueue the advisory closed-contract "
                         "calibration-reflection wake after scoring. The "
                         "micro score remains a hard close condition.")
    a = ap.parse_args()

    binding_error = _frozen_start_binding_error(
        tick_id=a.tick_id,
        contract_id=a.contract_id,
        substrate=a.substrate,
        goal=a.goal,
    )
    if binding_error:
        raise SystemExit(binding_error)

    rdir = REPO / "analytics" / "public" / "posttick" / a.tick_id
    rdir.mkdir(parents=True, exist_ok=True)
    steps: list[dict] = []

    # compiler-cid (daemon namespace) — recomputed from the goal via
    # the SAME import the daemon's start row uses. The daemon post-
    # gate binds manifest.contract_id == frozen start cid.
    try:
        sys.path.insert(0, str(REPO))
        from src.ztare.surfacing.pre_tick_obligation_compiler import (  # noqa: E402
            start_tick as _start_tick)
        _compiler_cid = str(_start_tick(a.goal).contract_id)
    except Exception as e:  # noqa: BLE001
        _compiler_cid = f"__CID_RECOMPUTE_ERROR__ {type(e).__name__}"

    # 1 — pretick_bound: a COMPLETE pretick_manifest for THIS tick,
    #     bound to the same compiler cid + goal. Post presupposes a
    #     real pre; this is the pre<->post symmetry the brief wants.
    _pm = (REPO / "analytics" / "public" / "pretick" / a.tick_id
           / "pretick_manifest.json")
    _pb_ok = False
    _pb_why = "pretick_manifest absent (no pre-tick ⇒ no post-tick)"
    if _pm.is_file():
        try:
            _pj = json.loads(_pm.read_text(encoding="utf-8"))
            _conds = {
                "status_COMPLETE": str(_pj.get("status")) == "COMPLETE",
                "tick_id_match": str(_pj.get("tick_id")) == a.tick_id,
                "cid_match": str(_pj.get("contract_id")) == _compiler_cid,
                "goal_match": str(_pj.get("goal", "")).strip()
                == a.goal.strip(),
            }
            _pb_ok = all(_conds.values())
            _pb_why = ("pre<->post bound" if _pb_ok
                       else f"unmet: {[k for k,v in _conds.items() if not v]}")
        except Exception as e:  # noqa: BLE001
            _pb_why = f"pretick_manifest unreadable ({type(e).__name__})"
    steps.append(_step("pretick_bound", _pb_ok,
                        {"why": _pb_why,
                         "expected_cid": _compiler_cid}))

    # 2 — post_tick_check.py (known CLI: --owner [--decision-changed]).
    #     Its deterministic HARD legs (PL closure / GP-230 unresolved /
    #     GP-233-on-decision-changed) must clear ⇒ exit 0.
    ptc = REPO / "scripts/public/control/post_tick_check.py"
    _cmd = [PY, str(ptc), "--owner", a.owner]
    if a.decision_changed:
        _cmd.append("--decision-changed")
    rc, out = _run(_cmd)
    steps.append(_step("post_tick_check", rc == 0,
                        {"rc": rc, "tail": out[-1200:]}))

    # 3 — micro_resolved: the tick's forecast contract is RESOLVED and
    #     a recognized independent forecaster bet existed BEFORE resolve
    #     (never-resolve-before-forecaster). Verified from on-disk state — NOT performed here
    #     (resolving is the agent's tick action; the runner audits it).
    # F4 (Meta-Darwin bwdcoww2y): the REAL forecast_pool schema is
    #   outcomes/<id>.json (success_bool/resolved_at/voided) and
    #   forecasts/<id>/<independent-agent alias>.json (forecasted_at).
    #   The prior code probed the wrong contract-local legacy path
    #   (wrong) ⇒ always INCOMPLETE. Now: RESOLVED iff a non-voided
    #   outcome with resolved_at; forecaster bet iff a canonical
    #   independent-forecaster identity exists; ordering forecasted_at < resolved_at
    #   (audited not performed).
    _fpr = REPO / "analytics/public/forecast_pool"
    _cid = a.contract_id
    _outf = _fpr / "outcomes" / f"{_cid}.json"
    _o = None
    try:
        if _outf.is_file():
            _o = json.loads(_outf.read_text(encoding="utf-8"))
    except Exception:
        _o = None
    _resolved = bool(_o) and not _o.get("voided") and bool(
        _o.get("resolved_at"))
    _forecasters = _recognized_forecaster_rows(_fpr, _cid)
    _prior_forecasters = [
        row for row in _forecasters
        if _resolved
        and row.get("forecasted_at")
        and str(row.get("forecasted_at")) < str(_o.get("resolved_at"))
    ]
    _order_ok = bool(_resolved and _prior_forecasters)
    steps.append(_step("micro_resolved",
                        _resolved and bool(_forecasters) and _order_ok,
                        {"contract_id": _cid,
                         "outcome_file": _outf.is_file(),
                         "resolved": _resolved,
                         "recognized_forecaster_bet_present": bool(_forecasters),
                         "recognized_forecaster_bets": _forecasters,
                         "recognized_forecaster_before_resolve": _order_ok,
                         "note": ("non-voided outcome.resolved_at + "
                                  "a recognized independent-agent "
                                  "forecast row with forecasted_at < "
                                  "resolved_at (audited, not "
                                  "performed)")}))

    # 4 — micro_scored: resolution without scoring preserves no market
    #     learning signal. This hard leg forces the resolved tick
    #     contract into the calibration corpus before close.
    _scoref = _fpr / "scores" / f"{_cid}.json"
    _score = None
    try:
        if _scoref.is_file():
            _score = json.loads(_scoref.read_text(encoding="utf-8"))
    except Exception:
        _score = None
    _score_rows = _score.get("scores") if isinstance(_score, dict) else None
    _scored = (
        isinstance(_score, dict)
        and str(_score.get("contract_id")) == _cid
        and bool(_score.get("scored_at"))
        and isinstance(_score_rows, list)
        and bool(_score_rows)
    )
    steps.append(_step("micro_scored", _scored,
                        {"contract_id": _cid,
                         "score_file": _scoref.is_file(),
                         "score_path": str(_scoref.relative_to(REPO)),
                         "score_rows": len(_score_rows)
                         if isinstance(_score_rows, list) else 0,
                         "scored_at": _score.get("scored_at")
                         if isinstance(_score, dict) else None,
                         "why": ("a resolved micro contract must be scored "
                                 "before close, otherwise GP-230 cannot "
                                 "calibrate or price future work")}))

    if a.skip_closed_reflection_wake:
        steps.append(_step(
            "closed_reflection_wake", True,
            {"skipped": True,
             "why": "caller requested no advisory closed-contract wake"},
            hard=False))
    elif _scored:
        _fp = REPO / "scripts/public/control/forecast/pool.py"
        _rcw_cmd = [
            PY, str(_fp), "warm-daemon-once",
            "--contract-id", _cid,
            "--include-closed",
            "--include-calibration",
            "--include-gp233",
            "--write",
            "--emit-agent-channel",
            "--max-events", "2",
        ]
        _rcw_rc, _rcw_out = _run(_rcw_cmd, timeout=120)
        steps.append(_step(
            "closed_reflection_wake", _rcw_rc == 0,
            {"rc": _rcw_rc,
             "tail": _rcw_out[-1200:],
             "why": ("post-close scoring should trigger an independent "
                     "calibration reflection/no-update opportunity")},
            hard=False))
    else:
        steps.append(_step(
            "closed_reflection_wake", False,
            {"skipped": "micro_scored hard leg failed; no reflection wake "
                        "should be emitted until the score exists"},
            hard=False))

    # 5 — big-decision trigger (#42): --decision-changed ⇒ a FRESH
    #     (<7d) meso OR macro contract is MANDATORY. Operationalises
    #     "meso/macro optional, but mandatory for big decisions"
    #     deterministically. Skipped (honest N/A) otherwise.
    if a.decision_changed:
        _now = time.time()
        _big = []
        _cdir = _fpr / "contracts"
        if _cdir.is_dir():
            for c in _cdir.glob("*.json"):
                try:
                    d = json.loads(c.read_text(encoding="utf-8"))
                except Exception:
                    continue
                # cold review b5upqb5kz F4: bind to THIS owner — "any
                # fresh meso/macro" let an unrelated contract satisfy
                # a big-decision tick. created_by/owner must match.
                _cb = str(d.get("created_by", "")
                          or d.get("owner", ""))
                if str(d.get("layer", "")).lower() in {"meso", "macro"} \
                        and (_now - c.stat().st_mtime) / 86400.0 <= 7 \
                        and _cb == a.owner:
                    _big.append({"id": d.get("contract_id"),
                                 "layer": d.get("layer"),
                                 "created_by": _cb})
        steps.append(_step("big_decision_forecast", bool(_big),
                            {"decision_changed": True,
                             "fresh_meso_macro": _big[-3:],
                             "why": ("a decision-critical decision change "
                                     "requires a fresh meso/macro "
                                     "forecast, not micro alone")}))
    else:
        steps.append(_step("big_decision_forecast", True,
                            {"decision_changed": False,
                             "skipped": "no big-decision declared "
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
    _tsh: list = []  # SM3 proven statement hashes (safe default if
    #                  no thesis / non-Lean tick — avoids NameError)
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
            _tsh = list(_gr.get("theorem_statement_hashes") or [])
            _lf_rec = {"gate_passed": _gr.get("gate_passed"),
                       "compiled": _gr.get("compiled"),
                       "axiom_audit_passed": _gr.get(
                           "axiom_audit_passed"),
                       "anti_laundering_passed": _gr.get(
                           "anti_laundering_passed"),
                       "v33_organ_flags": _gr.get("v33_organ_flags"),
                       # SM3 (ProofFlow/Aristotle): the PROVEN
                       # statement hashes — the daemon close requires
                       # the claimed target ∈ registered ∩ THESE, so a
                       # tick cannot cite a registered hash while
                       # proving a weaker theorem.
                       "theorem_statement_hashes": _tsh,
                       "thesis": str(_thp.relative_to(REPO))
                       if str(_thp).startswith(str(REPO))
                       else str(_thp)}
        except Exception as e:  # noqa: BLE001
            _lf_ok = False
            _tsh = []
            _lf_rec = {"error": f"{type(e).__name__}: {e}"}
        steps.append(_step("lean_faithfulness", _lf_ok, _lf_rec,
                            hard=True))
    else:
        # F5 (Meta-Darwin bwdcoww2y) + REVERT of round-2 finding 5
        # (r2 bq…: generic tokens "theorem"/"closure"/"proven"
        # false-FAILed honest NON-Lean analysis closures). Narrowed:
        # lean_faithfulness HARD fires ONLY on tokens that genuinely
        # indicate a formal LEAN proof claim — NOT generic closure
        # language. A non-Lean closure is honest N/A here; its
        # discipline is covered by the closure_artifact_present HARD
        # (F4) + Tier-1/Tier-3 recorded. (Typed --closure-kind is the
        # specced upgrade; this revert removes the false-FAIL now.)
        _gl = str(a.goal).lower()
        _CLAIM = ("lean", "lake build", "sorry-free", "no sorry",
                  "axiom-free", "compiled proof", " qed", "∎",
                  "mathlib")
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
                              "close.f_row_body-only claims ⇒ "
                              "daemon-side trigger (schema bundle)")},
                hard=False))

    # F4 (cold review bq4z7midf): rd_tick_brief's POST MECE list
    # includes Tier-3 pattern_026 + Tier-1 closure_claim. The prior
    # call was CLI-malformed (no `check <path>` subcommand ⇒ always
    # errored). Corrected. The DETERMINISTIC Tier-1 closure_claim
    # linter is HARD for closure-adjacent ticks (goal/thesis claims a
    # formal closure); the Tier-3 MULTI-LLM linter stays advisory-
    # recorded — gating an honest close on a cross-provider network
    # call would false-FAIL on a provider outage (don't-false-FAIL
    # invariant). No artifact for a closure-adjacent tick ⇒ HARD FAIL
    # (caller cannot dodge the discipline by withholding the artifact).
    _gl2 = str(a.goal).lower()
    _CLOSEADJ = ("clay", " qed", "theorem", " lean", "lean ",
                 "formal proof", "compiled proof", "closure",
                 "proven", "sorry-free", "axiom-free", "∎",
                 "lake build")
    _closeadj = any(k in _gl2 for k in _CLOSEADJ)
    _ap = str(a.artifact_path).strip()
    _app = pathlib.Path(_ap)
    if _ap and not _app.is_absolute():
        _app = REPO / _ap
    t1 = REPO / "scripts/public/control/closure_claim_discipline_linter.py"
    t3 = REPO / "scripts/public/control/closure_claim_discipline_linter_tier3.py"
    # SELF-MD SM1 (verified): closure_claim_discipline_linter passes
    # ONLY if the artifact carries an explicit 6-point verification
    # block at all 4 scopes — a discipline-FORMAT check, NOT closure
    # validity. Making it HARD would false-FAIL essentially every
    # honest closure-adjacent tick (violates the don't-false-FAIL
    # invariant; same class as post_tick_check #8/#8b advisory-only).
    # So: RUN + RECORD (advisory). The HARD closure-faithfulness
    # obligation correctly stays with lean_faithfulness (the Lean
    # gate). What IS hard here: a closure-adjacent tick must at least
    # PROVIDE the artifact so the discipline can be inspected.
    if _closeadj and not (_ap and _app.is_file()):
        steps.append(_step("closure_artifact_present", False,
                            {"close_adjacent": True,
                             "why": ("goal claims a formal closure "
                                     "but no readable --artifact-path "
                                     "— a closure-adjacent tick MUST "
                                     "provide its artifact (HARD)")},
                            hard=True))
    if _ap and _app.is_file() and t1.is_file():
        rc1, o1 = _run([PY, str(t1), "check", str(_app)], timeout=120)
        steps.append(_step("tier1_closure_claim", rc1 == 0,
                            {"rc": rc1, "tail": o1[-800:],
                             "artifact": str(_app),
                             "advisory": ("6-point/4-scope discipline "
                                          "FORMAT check; recorded NOT "
                                          "gated (SM1: HARD would "
                                          "false-FAIL honest closes)")},
                            hard=False))
    if _ap and _app.is_file() and t3.is_file():
        rc3, out3 = _run([PY, str(t3), "check", str(_app),
                          "--check-type", "pattern_026"], timeout=180)
        steps.append(_step("tier3_pattern_026", rc3 == 0,
                            {"rc": rc3, "tail": out3[-800:],
                             "advisory": ("multi-LLM cross-provider; "
                                          "recorded NOT gated — a "
                                          "provider outage must not "
                                          "false-FAIL an honest close")},
                            hard=False))
    mem = pathlib.Path(
        os.environ.get(
            "ZTARE_CLAUDE_PROJECT_MEMORY",
            str(pathlib.Path.home() / ".claude/projects" / os.environ.get("CLAUDE_PROJECT_SLUG", "") / "memory"),
        )
    )
    _mfresh = False
    if mem.is_dir():
        try:
            _mfresh = any(
                (time.time() - p.stat().st_mtime) / 86400.0 <= 7
                for p in mem.glob("*.md"))
        except Exception:
            _mfresh = False
    steps.append(_step("memory_touched", _mfresh,
                        {"memory_fresh_within_7d": _mfresh,
                         "advisory": "memory-update quality is not "
                         "deterministically checkable; recorded only"},
                        hard=False))

    complete = all(s["ok"] for s in steps if s.get("hard"))
    manifest = {
        "tick_id": a.tick_id, "goal": a.goal,
        "substrate": a.substrate, "owner": a.owner,
        "contract_id": _compiler_cid,
        "forecast_contract_id": a.contract_id,
        "proven_statement_hashes": [
            str(h.get("statement_sha256", "")).lower()
            for h in _tsh if h.get("statement_sha256")],
        "decision_changed": bool(a.decision_changed),
        "ts": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "authored_by": "agent",
        "trust_root": "operator_inspection (NOT operator-authored; "
                       "operator 2026-05-18)",
        "status": "COMPLETE" if complete else "INCOMPLETE",
        "steps": steps,
        "honest_bound": ("forces the post-tick MECE legs are "
                         "EXECUTED; does NOT certify the closure is "
                         "mathematically faithful — break-only "
                         "adversary + operator review (irreducible)."),
    }
    (rdir / "posttick_manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False),
        encoding="utf-8")
    # R2: register the manifest with the daemon (tamper-evident).
    _receipt_ok = False
    if complete:
        import base64 as _b64
        _mbytes = (rdir / "posttick_manifest.json").read_bytes()
        _rc, _ro = _run([PY, "-m", "src.ztare.gates.propose",
                         "--type", "manifest_receipt",
                         "--text", f"posttick manifest receipt {a.tick_id}",
                         "--goal", a.tick_id,
                         "--close", json.dumps(
                             {"tick_id": a.tick_id,
                              "manifest_kind": "posttick",
                              # F1 remote transport: carry the bytes.
                              "manifest_b64": _b64.b64encode(
                                  _mbytes).decode("ascii")})],
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
