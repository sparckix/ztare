#!/usr/bin/env python3
"""Exhaustive provider×row matrix — the apparatus orchestration_alpha needs.

WHY THIS EXISTS: the production solver lane is a cost-optimal FALLBACK CASCADE.
`run_llm_layers` runs the warm agent first and RETURNS on closure; the cold-shot
fan-out only runs if warm fails, and even then breaks on the first provider that
closes (`for prov_name in chain: … break`). So when warm-claude closes a row, NO
other provider is ever asked — which is exactly why `orchestration_alpha` measured
0 (the ensemble was never exercised, not "no provider adds value").

To MEASURE orchestration alpha you must attempt EVERY provider on EVERY row
INDEPENDENTLY (no warm short-circuit, no break-on-close), then let
orchestration_alpha.py compute ensemble-vs-best-single over the resulting matrix.
This harness does exactly that, reusing the worker's EXACT verify path
(`_build_solver_context` + `_verify_compile`) so the measurement is apples-to-apples
with production, and the kernel-trust oracle (`_is_compile_ok`) stays authoritative
(the provider PROPOSES proof text; WE compile it).

Leak-tight: set `ZTARE_LEANMILL_APN_CORPUS=<quarantined corpus>` before running so
the premise shelf cannot hand the solver the target's own proof DAG.

No silent caps: a provider whose backend is absent (binary_not_found /
provider_unavailable / no endpoint) is recorded as `unavailable` (NOT a closure
failure) and reported, so a dropped provider can never masquerade as alpha=0.

Usage:
  orchestration_matrix.py --slice <rows.jsonl> --providers native_hammer,claude_opus,codex_gpt5 \
      --db <out.db> [--lean-root <dir>] [--timeout 300] [--dry-run]
  then: orchestration_alpha.py <out.db>
"""
from __future__ import annotations
import argparse, json, sqlite3, sys, time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.solver.proof_state import proof_state_signal  # noqa: E402
import provider_registry as reg  # noqa: E402

# Provider errors that mean "backend absent", not "tried and failed to prove".
_UNAVAILABLE_ERRORS = {
    "binary_not_found", "provider_unavailable", "endpoint_unset",
    "not_installed", "auth_missing", "credit_exhausted", "rate_limited",
}


def _conn(db: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db))
    con.execute(
        """CREATE TABLE IF NOT EXISTS attempts (
            row_id TEXT NOT NULL, attempt_at TEXT NOT NULL, provider TEXT,
            outcome TEXT, compile_ok INTEGER NOT NULL, notes TEXT,
            goals_remaining INTEGER, error_class TEXT, progress REAL,
            provider_error TEXT, wallclock_s REAL,
            proof_text TEXT, mnc_passed INTEGER, kernel_clean INTEGER
        )"""
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_rp ON attempts(row_id, provider)")
    return con


def _done_pairs(con) -> set:
    return {(r[0], r[1]) for r in con.execute("SELECT row_id, provider FROM attempts").fetchall()}


def _verify():
    from solver_lane_worker import _verify_compile  # noqa: E402
    return _verify_compile


def _invoke_with_retry(prov, goal_text, timeout_s, retries=4, base_sleep=20):
    """reg.invoke with bounded backoff on rate_limited (codex/gpt-5.x hits limits
    on big contexts — a rate limit is NOT a capability failure, so don't record it
    as one until retries are exhausted)."""
    for attempt in range(retries + 1):
        res = reg.invoke(prov, goal_text=goal_text, timeout_s=timeout_s)
        if res.get("provider_error") != "rate_limited" or attempt == retries:
            return res
        time.sleep(base_sleep * (attempt + 1))
    return res


def run(slice_path: Path, providers: list[str], db: Path, lean_root: Path,
        timeout_s: int, dry_run: bool, mnc: bool = True) -> int:
    rows = [json.loads(l) for l in slice_path.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if (r.get("goal") or "").strip()]
    print(f"[matrix] {len(rows)} rows with goal × {len(providers)} providers = "
          f"{len(rows)*len(providers)} independent attempts")
    if not rows:
        print("[matrix] FATAL: no rows carry a 'goal' body. On the VPS the slice must "
              "be materialized with statement bodies (goal=None locally is expected).")
        return 2
    if dry_run:
        for r in rows[:3]:
            print(f"  row {r.get('row_id')} target={r.get('target_theorem_name')} "
                  f"goal_len={len(r.get('goal',''))}")
        print(f"  providers: {providers}")
        print("[matrix] dry-run only; no provider invoked.")
        return 0

    con = _conn(db); done = _done_pairs(con)
    unavailable = {}
    closed = {p: 0 for p in providers}
    verify_compile = _verify()
    for r in rows:
        # The materialized goal is SELF-CONTAINED + leak-clean (statement closure,
        # proof helpers withheld). Use it DIRECTLY — NOT _build_solver_context, which
        # prepends the source-file prelude and on a materialized row both DUPLICATES
        # the statement defs ("already declared") AND re-injects the withheld helpers
        # (re-leak). That double bug invalidated the earlier runs.
        enriched = (r.get("goal") or "").strip()
        rid = r.get("row_id", "anon")
        for prov in providers:
            if (rid, prov) in done:
                continue
            t0 = time.time()
            perr = None
            proof_text = ""
            if prov == "native_hammer":
                # Deterministic tactic cascade — different invocation shape
                # (goal_file/proof_file, not goal_text). Use the worker's probe,
                # which runs the cascade and kernel-verifies each tactic itself.
                from solver_lane_worker import _native_hammer_probe  # noqa: E402
                try:
                    ok, _proof, tail = _native_hammer_probe(r, lean_root, timeout_s)
                    proof_text = f"by {_proof}" if _proof else ""
                except Exception as e:  # noqa: BLE001
                    ok, tail = False, f"native_hammer_exception: {e!r}"
            else:
                try:
                    res = _invoke_with_retry(prov, enriched, timeout_s)  # backoff on rate_limited
                except Exception as e:  # noqa: BLE001
                    res = {"proof_text": "", "provider_error": "invoke_exception", "error": repr(e)}
                perr = res.get("provider_error")
                if perr in _UNAVAILABLE_ERRORS:
                    unavailable.setdefault(prov, 0)
                    unavailable[prov] += 1
                    con.execute(
                        "INSERT INTO attempts (row_id, attempt_at, provider, outcome, compile_ok, "
                        "notes, goals_remaining, error_class, progress, provider_error, wallclock_s) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (rid, datetime.now(timezone.utc).isoformat(), prov, "unavailable", 0,
                         (res.get("error") or perr)[:500], None, "provider_unavailable", 0.0,
                         perr, round(time.time()-t0, 2)))
                    con.commit()
                    continue
                proof_text = res.get("proof_text", "")
                ok, tail = verify_compile(rid, enriched, proof_text, lean_root, timeout_s)
            sig = proof_state_signal(0 if ok else 1, tail)
            # CREDIT-GRADE gate via the CANONICAL governance contract — the SAME
            # `_validate_against_contract` the production solver lane and the DAG
            # move-runner use (NOT a parallel credit check). It runs the matched-
            # negative-control (strip-prelude leakage test) and marks axiom-allowlist
            # + L3 as deferred-to-governance. `credit_ready_at_solver_layer` =
            # kernel-clean AND MNC-passed. --no-mnc downgrades to a kernel-only pilot.
            kernel_clean = bool(ok)
            mnc_ok = None
            if kernel_clean and mnc:
                from solver_lane_worker import (  # noqa: E402
                    _validate_against_contract, _build_solver_action_contract)
                tgt = r.get("target_theorem_name") or ""
                try:
                    contract = _build_solver_action_contract(r, lean_root)
                    validation = _validate_against_contract(
                        contract=contract, proof_text=proof_text, enriched_goal=enriched,
                        target_name=tgt, lean_root=lean_root, timeout_s=timeout_s,
                        kernel_compile_ok=ok, kernel_compile_tail=tail)
                    mnc_ok = validation["receipts"]["matched_negative_control_receipt"]["passed"]
                    ratified = bool(validation["credit_ready_at_solver_layer"])
                except Exception:  # noqa: BLE001
                    mnc_ok, ratified = False, False
            else:
                ratified = kernel_clean
            if ratified:
                closed[prov] += 1
            con.execute(
                "INSERT INTO attempts (row_id, attempt_at, provider, outcome, compile_ok, "
                "notes, goals_remaining, error_class, progress, provider_error, wallclock_s, "
                "proof_text, mnc_passed, kernel_clean) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (rid, datetime.now(timezone.utc).isoformat(), prov,
                 "ratified_closure" if ratified else
                 ("rejected_negative_control" if (kernel_clean and mnc and not mnc_ok) else "open"),
                 1 if ratified else 0,
                 (tail or "")[-1000:], sig["goals_remaining"], sig["error_class"],
                 sig["progress"], perr, round(time.time()-t0, 2),
                 (proof_text or "")[:2000], (1 if mnc_ok else 0) if mnc_ok is not None else None,
                 1 if kernel_clean else 0))
            con.commit()
            verdict = ("RATIFIED" if ratified else
                       ("kernel_ok_but_MNC_FAIL" if (kernel_clean and mnc and not mnc_ok)
                        else sig["error_class"]))
            print(f"  [{rid[:22]:<22}] {prov:<14} {verdict:<22} "
                  f"goals={sig['goals_remaining']} ({round(time.time()-t0)}s)", flush=True)
    print(f"\n[matrix] per-provider closures: {closed}")
    if unavailable:
        print(f"[matrix] UNAVAILABLE (backend absent, NOT counted as failure): {unavailable}")
        print("[matrix] ^ a 5-provider alpha claim is only valid once these have real backends.")
    print(f"[matrix] DONE. Next: python {HERE/'orchestration_alpha.py'} {db}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True)
    ap.add_argument("--providers", default="native_hammer,claude_opus,codex_gpt5")
    ap.add_argument("--db", default=str(REPO / "analytics/public/leanmill/orchestration_matrix.db"))
    ap.add_argument("--lean-root", default=str(REPO / "ztare_proofs"))
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-mnc", action="store_true",
                    help="skip the matched-negative-control gate (kernel-clean only; "
                         "faster pilot, but the resulting alpha is NOT credit-grade)")
    a = ap.parse_args()
    return run(Path(a.slice), [p.strip() for p in a.providers.split(",") if p.strip()],
               Path(a.db), Path(a.lean_root), a.timeout, a.dry_run, mnc=not a.no_mnc)


if __name__ == "__main__":
    sys.exit(main())
