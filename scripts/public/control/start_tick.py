#!/usr/bin/env python3
"""start_tick.py — the sanctioned tick-OPEN wrapper (symmetric to
tick_close.py).

Why this exists (cold review bq4z7midf, F3): the daemon freezes the
forecast identity into the signed start row ONLY when the start_tick
proposal declares forecast_contract_id. No emitter did — start_tick
proposals were ad-hoc `propose --type start_tick` calls — so F3 was
DORMANT (forecast_identity_frozen always False ⇒ all F3 close-side
binding skipped). There was a sanctioned CLOSE path (tick_close.py)
but no sanctioned OPEN path; this is it. Opening a research tick
through this wrapper makes F3 decision-critical: the daemon hashes the
on-disk forecast contract and binds it into the signed start row, so
the close cannot later swap to a weaker/unrelated/ mutated contract.

Fail-closed: a research tick MUST carry --substrate, --residual-target
and --forecast-contract-id (the daemon quarantines a research
start_tick missing substrate/target anyway; requiring the forecast id
here is the F3 wiring). The daemon remains the authority — this only
builds + submits the proposal it will re-validate and sign.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PY = sys.executable


def _auto_record_decision_use(contract_id: str, tick_id: str, owner: str) -> None:
    """Best-effort action-boundary forecast consumption record.

    The start wrapper is the first concrete RD action boundary. If an aggregate
    exists, record that the tick consumed the market signal so RDs do not have
    to remember a separate meta-ledger step.
    """
    aggregate_path = (
        REPO / "analytics/public/forecast_pool/aggregates"
        / f"{contract_id}.json"
    )
    if not aggregate_path.is_file():
        print(
            "⚠️  decision-use auto-record skipped — aggregate absent; "
            "market_state will continue surfacing this as forecast/aggregate debt.",
            file=sys.stderr,
        )
        return
    try:
        aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  decision-use auto-record skipped — aggregate unreadable: {exc}",
              file=sys.stderr)
        return
    allocation = aggregate.get("allocation_recommendation")
    if not isinstance(allocation, dict):
        allocation = {}
    recommendation = str(
        allocation.get("action")
        or allocation.get("recommendation")
        or "run_now"
    )
    used_for = {
        "run_now": "run",
        "split_contract": "split",
        "ask_another_independent_agent": "ask_more",
        "defer": "override",
        "kill_branch": "override",
    }.get(recommendation, "run")
    agg = aggregate.get("aggregate")
    if not isinstance(agg, dict):
        agg = {}
    cmd = [
        PY,
        str(REPO / "scripts/public/control/forecast/pool.py"),
        "record-decision-use",
        "--contract-id", contract_id,
        "--tick-id", tick_id,
        "--owner", owner,
        "--decision-stage", "membrane",
        "--used-for", used_for,
        "--no-decision-changed-bool",
        "--forecast-delta",
        (
            "auto-recorded at start_tick; "
            f"allocation_recommendation={recommendation}; "
            f"p_success={agg.get('p_success')}; "
            f"expected_cost_agent_minutes={agg.get('expected_cost_agent_minutes')}"
        ),
        "--notes",
        "automatic action-boundary forecast consumption from start_tick.py",
        "--dedupe",
    ]
    if used_for == "override":
        cmd += [
            "--ignored-forecast-reason",
            (
                "start_tick opened the tick despite aggregate allocation "
                f"recommendation={recommendation}; review RD/principal context"
            ),
        ]
    pr = subprocess.run(cmd, cwd=str(REPO), capture_output=True,
                         text=True, timeout=60)
    if pr.returncode == 0:
        print("✅ decision-use auto-recorded at start_tick.")
    else:
        print("⚠️  decision-use auto-record failed; continuing with start_tick.",
              file=sys.stderr)
        sys.stderr.write(pr.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tick-id", required=True)
    ap.add_argument("--goal", required=True,
                    help="the tick's research goal (the daemon "
                         "recomputes the compiler cid from this).")
    ap.add_argument("--forecast-contract-id", required=True,
                    help="the GP-230 forecast contract this tick will "
                         "consume — frozen (sha256 + question_hash + "
                         "consumes_surfaced + layer + created_by) into "
                         "the signed start row (F3).")
    ap.add_argument("--substrate", default="",
                    help="required for a research tick (daemon "
                         "quarantines a research start without it).")
    ap.add_argument("--residual-target", default="",
                    help="required for a research tick.")
    ap.add_argument("--tick-class", default="research")
    ap.add_argument("--transition-type", default="")
    ap.add_argument("--declared", default="",
                    help="comma-sep declared signals (optional).")
    ap.add_argument("--new-target-justification", default="")
    a = ap.parse_args()

    if a.tick_class == "research" and not (
            a.substrate and a.residual_target):
        print("🛑 START REFUSED — a research tick requires "
              "--substrate AND --residual-target (the daemon would "
              "quarantine it anyway; fail-closed here for a clear "
              "message).", file=sys.stderr)
        return 1
    if not a.forecast_contract_id.strip():
        print("🛑 START REFUSED — --forecast-contract-id is "
              "mandatory (F3: no frozen forecast identity ⇒ the "
              "close-side forecast binding is unenforceable).",
              file=sys.stderr)
        return 1

    _fc_id = a.forecast_contract_id.strip()
    # GP-241 #52 fix: the daemon runs from the agent-UNWRITABLE
    # trusted install (/srv/ztare_gate) and used to re-read the
    # contract at ITS REPO_ROOT — which never sees the agent-authored
    # contract in ~ztare/figs_activist_loop ⇒ forecast_identity_frozen
    # was ALWAYS False (whole-session root cause). Fix: carry the
    # contract BYTES in the proposal (agent can read its own tree; the
    # proposal travels through the daemon-OWNED inbox whose exact
    # content the daemon already hashes into the chain). Trust model
    # unchanged: freezing binds IDENTITY not trust — bytes are
    # agent-authored either way; a forged proposal only freezes the
    # forged thing, exactly as a forged file did before.
    _cpath = (REPO / "analytics/public/forecast_pool"
              / "contracts" / f"{_fc_id}.json")
    if not _cpath.is_file():
        print(f"🛑 START REFUSED — forecast contract not found at "
              f"{_cpath} (run forecast_pool.py init-contract first; "
              f"clearer than the daemon's cryptic frozen=False).",
              file=sys.stderr)
        return 1
    import base64 as _b64
    import hashlib as _hl
    _raw = _cpath.read_bytes()
    try:
        _contract = json.loads(_raw.decode("utf-8"))
    except Exception:
        _contract = {}
    _owner = (
        os.environ.get("RD_OWNER")
        or str(_contract.get("created_by") or "").strip()
        or "unknown"
    )
    _close = {
        "tick_id": a.tick_id,
        "forecast_contract_id": _fc_id,
        "forecast_contract_b64": _b64.b64encode(_raw).decode("ascii"),
        "forecast_contract_sha256": _hl.sha256(_raw).hexdigest(),
        "substrate": a.substrate,
        "residual_target": a.residual_target,
        "tick_class": a.tick_class,
        "transition_type": a.transition_type,
    }
    if a.new_target_justification:
        _close["new_target_justification"] = a.new_target_justification

    cmd = [PY, "-m", "src.ztare.gates.propose",
           "--type", "start_tick",
           "--text", f"open tick {a.tick_id}",
           "--goal", a.goal,
           "--close", json.dumps(_close)]
    if a.declared:
        cmd += ["--declare", a.declared]
    pr = subprocess.run(cmd, cwd=str(REPO), capture_output=True,
                         text=True, timeout=180)
    sys.stdout.write(pr.stdout)
    if pr.returncode != 0:
        sys.stderr.write(pr.stderr)
        print(f"\n🛑 START REFUSED — daemon did not stamp the "
              f"start_tick (see above).", file=sys.stderr)
        return 1
    print(f"\n✅ TICK OPENED — {a.tick_id} (forecast identity frozen "
          f"into the signed start row; F3 live for the close).")
    _auto_record_decision_use(_fc_id, a.tick_id, _owner)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
