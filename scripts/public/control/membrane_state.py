#!/usr/bin/env python3
"""membrane_state.py — DERIVED read-only lifecycle oracle (GP-241).

The mutator stays GATED (the commit-membrane daemon is the sole
authority — unchanged). This is a pure read-only NUDGE so the agent
stops grinding opaque `frozen=False` refusals.

LOAD-BEARING INVARIANT (spec SPEC-v2.1; hardened over self-MD cycles
1,3,4): the oracle asserts an AUTHORITATIVE state ONLY from the
membrane's real chain-valid daemon predicates. Exactly TWO such
predicates exist (`stamped_state.tick_started`, `tick_closed`; both
run `chain_valid` internally). There is NO chain-valid predicate for
"resolved" / "catch logged" / "pretick·posttick receipted"
(confirmed: grep found none; outcomes/*.json and catch_ledger are
AGENT-WRITABLE, hence forgeable). Therefore the oracle:
  * asserts only CONTRACT_UNFROZEN | IN_LIFECYCLE | CLOSED;
  * for IN_LIFECYCLE it emits the ordered remaining sequence and, at
    most, clearly-labeled NON-AUTHORITATIVE hints (file presence) —
    never a claimed sub-state mirroring a daemon check (that would be
    the parallel-FSM the spec forbids; MD cycle 1/3 fix);
  * performs ZERO writes; fails LOUD only on its own misuse;
  * distinguishes "predicate says False" from "could not evaluate"
    (permission/exception) — never silently downgrades (MD cycle 3).

Usage:
  python3 scripts/public/control/membrane_state.py \
      --tick-id <F-...> --contract-id <cid> [--owner <o>] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    d = Path(__file__).resolve()
    for p in (d, *d.parents):
        if (p / "scripts/public/control/membrane_state.py").is_file():
            return p
    print(f"ABORT: cannot locate repo root from {__file__}",
          file=sys.stderr)
    raise SystemExit(2)


REPO = _repo_root()
# Canonical spelling for THIS file is `ztare.*` (C5 discipline; this
# file never writes `src.ztare.*`). BUT `stamped_state.chain_valid`
# itself does `from src.ztare.gates._daemon_sig import verify` (the
# pre-existing #49 dual-module bug). The working daemon runs with the
# repo ROOT importable, so that `src.*` import resolves there. To be
# FUNCTIONAL (not a security-safe dead-letter — bounded-review
# finding), match the daemon's runtime: put BOTH repo/src (for
# `ztare.*`) AND repo root (so stamped_state's own `src.*` import
# resolves) on the path. #49 is the canonical fix; this only mirrors
# the environment the predicates already run under.
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

try:
    from ztare.gates import stamped_state as _ss
except Exception as e:  # fail LOUD — never fabricate a state
    print(json.dumps({
        "error": "stamped_state_unimportable",
        "detail": repr(e),
        "note": "oracle refuses to guess without the real predicates",
    }))
    raise SystemExit(2)

_FP = REPO / "analytics/public/forecast_pool"
_CATCH = REPO / "analytics/public/ledgers/catch/catch_ledger.jsonl"


def _hint(path: Path) -> str:
    """Non-authoritative file-presence hint, explicitly labelled.
    Distinguishes present / absent / unreadable (MD cycle 3: never
    silently treat unreadable as absent)."""
    try:
        if not path.exists():
            return "absent"
        path.read_bytes() if path.is_file() else None
        return "present"
    except PermissionError:
        return "unreadable(permission)"
    except Exception as e:  # pragma: no cover
        return f"unreadable({type(e).__name__})"


def _read_json_silent(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _market_state_hint(cid: str) -> dict:
    """NON-authoritative GP-230 read model for RD speed.

    The membrane state remains derived only from daemon predicates. This hint
    only tells the RD which forecast-market artifact to consume next.
    """
    path = _FP / "market_state" / "contracts" / f"{cid}.json"
    payload = _read_json_silent(path)
    if not payload:
        return {
            "market_state_file": _hint(path),
            "refresh_command": "forecast_pool.py materialize-state --contract-id " + cid,
        }
    rd = payload.get("rd_fast_read") if isinstance(payload.get("rd_fast_read"), dict) else {}
    lifecycle = payload.get("lifecycle") if isinstance(payload.get("lifecycle"), dict) else {}
    decision_use = payload.get("decision_use") if isinstance(payload.get("decision_use"), dict) else {}
    return {
        "market_state_file": str(path.relative_to(REPO)),
        "lifecycle_state": lifecycle.get("state"),
        "next_action": rd.get("next_action") or lifecycle.get("next_action"),
        "routing_hint": rd.get("routing_hint"),
        "p_success": rd.get("p_success"),
        "expected_cost_agent_minutes": rd.get("expected_cost_agent_minutes"),
        "top_failure_modes": rd.get("top_failure_modes") or [],
        "decision_use_rows": decision_use.get("row_count"),
        "latest_decision_use": decision_use.get("latest"),
    }


def _catch_hint(tick_id: str, cid: str) -> str:
    """NON-authoritative catch hint. The authoritative check is the
    daemon's H6 catch-attest AT close — this oracle does NOT re-derive
    it (MD cycle 3: doing so was the same parallel-FSM violation as
    the receipt heuristic fixed in cycle 1). Substring scan only as a
    labelled hint; unreadable ≠ absent."""
    try:
        if not _CATCH.is_file():
            return "ledger-absent"
        txt = _CATCH.read_text(encoding="utf-8", errors="ignore")
    except PermissionError:
        return "unreadable(permission) — cannot hint; daemon H6 is authoritative"
    except Exception as e:
        return f"unreadable({type(e).__name__})"
    return ("a-line-mentions-it (NON-authoritative; H6 decides)"
            if (cid in txt or tick_id in txt)
            else "no-line-mentions-it (NON-authoritative; H6 decides)")


def derive(tick_id: str, cid: str, owner: str | None) -> dict:
    o = owner or "<owner>"
    contract = _FP / "contracts" / f"{cid}.json"

    def out(state: str, nxt: str, why: str, **extra) -> dict:
        d = {
            "tick_id": tick_id, "contract_id": cid,
            "current_state": state,
            "next_legal_transition": nxt,
            "derived_from": why,
            "authority": ("ADVISORY ONLY — the commit-membrane daemon "
                          "is the sole authority; this oracle cannot "
                          "weaken or bypass any gate"),
        }
        d.update(extra)
        return d

    # (0) STORE REACHABILITY (cold-review b11rcv46f #1, decision-critical):
    # _rows() returns [] when LEDGER is absent — and enforce mode
    # silently points at /nonexistent when /srv is unverified. Then
    # tick_started/tick_closed are False NOT because the tick is
    # unfrozen but because the oracle cannot SEE the authoritative
    # store. Asserting CONTRACT_UNFROZEN there is a false-negative.
    # Gate it: an empty/absent ledger ⇒ UNEVALUABLE, never a state.
    try:
        _ledger = getattr(_ss, "LEDGER", None)
        _seen = bool(_ss._rows())
    except Exception as e:
        return out("UNEVALUABLE", "run where the official store lives",
                   f"could not read the authoritative ledger: {e!r}")
    if not _seen:
        return out(
            "UNEVALUABLE", "run where the official store lives (VPS)",
            f"authoritative ledger empty/absent ({_ledger}) — the "
            f"oracle cannot SEE official state from this cwd/host, so "
            f"tick_started/closed=False would be a FALSE-NEGATIVE. "
            f"NOT asserting CONTRACT_UNFROZEN (cold-review fix).")

    # (1) CLOSED — chain-valid daemon predicate
    try:
        if _ss.tick_closed(tick_id):
            return out("CLOSED", "(none)",
                       "stamped_state.tick_closed(tick_id)=True "
                       "(chain-valid daemon-signed tick_close)")
    except Exception as e:
        return out("UNEVALUABLE", "inspect manually",
                   f"tick_closed raised: {e!r} (NOT treated as "
                   f"closed — fail-loud, not silent)")

    # (1b) RETIRED — TERMINAL (Meta-Darwin fix 2026-05-18, caught
    # live: the nudge said `IN_LIFECYCLE → do pretick` on an
    # operator-RETIRED throwaway, because the oracle only checked
    # tick_closed/tick_started, not tick_retire). A chain-valid
    # daemon-signed `tick_retire` is terminal: the tick is DONE as
    # C4 bypass-debt — NOT in-lifecycle, NOT owed pretick. Surface
    # it so the nudge points PAST it (to the genuinely owed tick).
    try:
        _v, _ = _ss.chain_valid(_ss._rows())
        for _r in _v:
            if (_r.get("transition_type") == "tick_retire"
                    and tick_id in (str(_r.get("tick_row", "")),
                                    str(_r.get("tick_id", "")))):
                return out(
                    "RETIRED", "(none — terminal; pick the genuinely "
                    "owed OPEN tick, not this one)",
                    "chain-valid daemon-signed tick_retire (C4 "
                    "bypass-debt) — terminal, NOT in-lifecycle; the "
                    f"nudge must not send pretick here",
                    retire_reason=str(_r.get("reason", "")))
    except Exception:
        pass  # fail-safe: absence of retire ⇒ fall through

    # (2) STARTED? — chain-valid daemon predicate
    try:
        started = _ss.tick_started(tick_id)
    except Exception as e:
        return out("UNEVALUABLE", "inspect manually",
                   f"tick_started raised: {e!r} (NOT assumed either "
                   f"way — fail-loud)")

    if not started:
        return out(
            "CONTRACT_UNFROZEN",
            "start_tick (THIS freezes the contract)",
            "stamped_state.tick_started(tick_id)=False — no "
            "chain-valid daemon-signed start_tick row. start_tick is "
            "the freeze trigger (daemon hashes the contract).",
            contract_file=_hint(contract),
            exact_next_command=(
                f"start_tick.py --tick-id {tick_id} --goal <g> "
                f"--forecast-contract-id {cid} --substrate <s> "
                f"--residual-target <r> --tick-class micro "
                f"--transition-type tick_open"
                + ("" if contract.is_file() else
                   f"   (contract file absent → first run "
                   f"forecast_pool.py init-contract --contract-id "
                   f"{cid} --created-by {o} --emit-warm-wake "
                   f"--warm-forecasters "
                   f"<runtime>:<independent_agent_id>:forecasting_agent …)")))

    # (3) STARTED ∧ ¬CLOSED = IN_LIFECYCLE. No chain-valid predicate
    # exists for the intermediate steps — the oracle does NOT claim a
    # sub-state. It emits the ordered remaining sequence + labelled
    # non-authoritative hints; the daemon enforces every step at
    # resolve/close.
    return out(
        "IN_LIFECYCLE",
        "follow the ordered remaining sequence below; the daemon "
        "enforces each step (oracle does NOT re-derive sub-states — "
        "no chain-valid predicate exists for them: surface-not-mirror)",
        "stamped_state.tick_started=True ∧ tick_closed=False. "
        "Intermediate progress (resolved / catch / pretick·posttick "
        "receipts) has NO chain-valid predicate and rests on "
        "agent-writable artifacts ⇒ NOT asserted as state.",
        remaining_sequence=[
            f"pretick_runner.py --goal <g> --substrate <s> --owner {o} "
            f"--tick-id {tick_id} --contract-id {cid} "
            f"--universal-ops <real> --scopes <4>",
            "research work (RD depth-n + swarm, aggregated)",
            "produce a recognized independent-agent forecast "
            "(resolve HARD-requires it)",
            f"forecast_pool.py resolve --contract-id {cid} …",
            "if success=FALSE: append an independent catch_ledger "
            "entry referencing the contract/tick (daemon H6 HARD)",
            f"posttick_runner.py --goal <g> --substrate <s> --owner "
            f"{o} --tick-id {tick_id} --contract-id {cid}",
            f"tick_close.py --tick-row {tick_id} --contract-id {cid} "
            f"--owner {o} --witnesses-json '<…>'",
        ],
        non_authoritative_hints={
            "outcome_file (agent-writable, NOT daemon-authoritative)":
                _hint(_FP / "outcomes" / f"{cid}.json"),
            "independent_forecast_aliases (resolve precondition; hint only)": {
                "codex": _hint(_FP / "forecasts" / cid / "codex.json"),
                "codex_forecaster": _hint(
                    _FP / "forecasts" / cid / "codex_forecaster.json"),
                "claude": _hint(_FP / "forecasts" / cid / "claude.json"),
                "claude_forecaster": _hint(
                    _FP / "forecasts" / cid / "claude_forecaster.json"),
            },
            "forecast_market_read_model (NON-authoritative RD speed hint)":
                _market_state_hint(cid),
            "catch_ledger (H6 is authoritative at close)":
                _catch_hint(tick_id, cid),
        })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tick-id", required=True)
    ap.add_argument("--contract-id", required=True)
    ap.add_argument("--owner", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    st = derive(a.tick_id, a.contract_id, a.owner)
    print(json.dumps(st) if a.json else json.dumps(st, indent=2))
    if not a.json:
        print(f"\n→ STATE: {st['current_state']}  "
              f"NEXT: {st['next_legal_transition']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
