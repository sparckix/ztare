"""Dump a single rolled-up JSON state file for the leanmill UI.

Reads from the canonical receipt locations and produces
`analytics/public/queries/leanmill_ui_state.json` — the only file the
static HTML dashboard needs to load. Idempotent; safe to re-run on demand.

Sources read:
  - analytics/public/queries/lane_b_apn_audit_receipts.json
  - analytics/public/queries/leanmill_solver_lane_results.json
  - analytics/public/queries/leanmill_solver_lane_typed_exits.json
  - analytics/public/queries/solver_lane_attempts.db
  - analytics/public/queries/solver_lane_carrier_receipt_use_ledger.jsonl
  - analytics/public/leanmill/dashboard_data/corpus_mandates.json

CLI:
  python -m scripts.public.control.leanmill.ui_state_dump
  ztare leanmill ui-state                     (via the CLI verb registered below)
"""
from __future__ import annotations
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
Q = REPO / "analytics" / "public" / "queries"
DASH = REPO / "analytics" / "public" / "leanmill" / "dashboard_data"

ATTEMPTS_DB = Q / "solver_lane_attempts.db"
CARRIER_LEDGER = Q / "solver_lane_carrier_receipt_use_ledger.jsonl"
LANE_B_RECEIPTS = Q / "lane_b_apn_audit_receipts.json"
SOLVER_RESULTS = Q / "leanmill_solver_lane_results.json"
MANDATES = DASH / "corpus_mandates.json"
OUT = Q / "leanmill_ui_state.json"


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _attempts_summary() -> dict:
    if not ATTEMPTS_DB.exists():
        return {"total_attempts": 0, "distinct_rows": 0, "closures": 0, "by_provider": [], "recent": []}
    con = sqlite3.connect(str(ATTEMPTS_DB))
    total = con.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
    distinct = con.execute("SELECT COUNT(DISTINCT row_id) FROM attempts").fetchone()[0]
    closures = con.execute("SELECT COUNT(*) FROM attempts WHERE compile_ok=1").fetchone()[0]
    by_provider = [
        {"provider": r[0], "outcome": r[1], "count": r[2]}
        for r in con.execute(
            "SELECT provider, outcome, COUNT(*) FROM attempts GROUP BY provider, outcome ORDER BY 3 DESC"
        )
    ]
    recent = [
        {"attempt_at": r[0], "row_id": r[1], "provider": r[2], "outcome": r[3], "compile_ok": bool(r[4])}
        for r in con.execute(
            "SELECT attempt_at, row_id, provider, outcome, compile_ok FROM attempts ORDER BY attempt_at DESC LIMIT 10"
        )
    ]
    con.close()
    return {
        "total_attempts": total, "distinct_rows": distinct, "closures": closures,
        "by_provider": by_provider, "recent": recent,
    }


def _lane_b_summary() -> dict:
    d = _read_json(LANE_B_RECEIPTS)
    if not d:
        return {"available": False}
    receipts = d.get("receipts", [])
    rows = []
    for r in receipts:
        name = r.get("target_name_in_lean") or (
            Path(r.get("candidate_path") or "").stem.replace("_candidate", "")
        )
        status = r.get("status")
        compile_ok = (r.get("compile") or {}).get("ok")
        axiom_ok = (r.get("kernel_axiom_policy") or {}).get("allowlist_ok")
        drift = r.get("likely_toolchain_drift")
        sidecar = r.get("sidecar_audit") or r.get("sidecar_v427_audit") or {}
        combined = r.get("combined_verdict")
        rows.append({
            "target": name, "status": status, "compile_ok": compile_ok,
            "axiom_allowlist_ok": axiom_ok, "drift": drift,
            "sidecar_status": sidecar.get("status"),
            "combined_verdict": combined,
        })
    # rollup
    audit_clean = sum(
        1 for r in rows
        if (r["status"] or "").startswith("compile_pass_l3_advisory_review")
        or (r["combined_verdict"] or "") == "passes_at_native_toolchain"
        or (r["combined_verdict"] or "") == "passes_at_pinned_toolchain_only"
    )
    return {
        "available": True,
        "generated_at": d.get("generated_at"),
        "n_targets": len(receipts),
        "audit_clean": audit_clean,
        "summary_by_status": d.get("summary_by_status") or {},
        "rows": rows,
    }


def _solver_summary() -> dict:
    d = _read_json(SOLVER_RESULTS)
    if not d:
        return {"available": False}
    results = d.get("results", [])
    rows = []
    for r in results:
        rows.append({
            "row_id": r.get("name") or r.get("row_id"),
            "target": r.get("target_name"),
            "outcome": r.get("outcome"),
            "compile_ok": r.get("compile_ok"),
            "provider": r.get("provider"),
            "providers_tried": [pt.get("provider") for pt in (r.get("providers_tried") or [])],
        })
    return {
        "available": True,
        "generated_at": d.get("generated_at"),
        "lane": d.get("lane"),
        "rows": rows,
    }


def _mandates_summary() -> dict:
    d = _read_json(MANDATES)
    if not d:
        return {"available": False}
    items = []
    for m in d.get("mandates") or []:
        items.append({
            "mandate_id": m.get("mandate_id"),
            "status": m.get("status"),
            "purpose": (m.get("purpose") or "")[:240],
            "row_count": m.get("row_count"),
            "lane_eligibility": m.get("lane_eligibility"),
            "credit_lanes_allowed": m.get("credit_lanes_allowed"),
        })
    return {"available": True, "mandates": items}


def _ledger_recent() -> list:
    if not CARRIER_LEDGER.exists():
        return []
    rows = []
    for line in CARRIER_LEDGER.read_text().splitlines()[-20:]:
        if not line.strip(): continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def main() -> int:
    state = {
        "schema": "leanmill-ui-state-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lane_b": _lane_b_summary(),
        "solver_lane": _solver_summary(),
        "solver_attempts": _attempts_summary(),
        "corpus_mandates": _mandates_summary(),
        "carrier_receipt_ledger_recent": _ledger_recent(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, indent=2) + "\n")
    print(f"wrote {OUT}")
    print(f"  lane_b targets: {state['lane_b'].get('n_targets') or 0}, audit_clean: {state['lane_b'].get('audit_clean') or 0}")
    print(f"  solver attempts: {state['solver_attempts']['total_attempts']}, closures: {state['solver_attempts']['closures']}")
    print(f"  corpus mandates: {len(state['corpus_mandates'].get('mandates') or [])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
