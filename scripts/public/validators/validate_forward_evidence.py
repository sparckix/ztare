#!/usr/bin/env python3
"""Validate analytics/public/ledgers/forward_evidence/forward_evidence_ledger.jsonl.

v35 forward clean-corpus accrual gate. Same SOX §1220 independence +
§1215 path-retention discipline as validate_catch_ledger.py, plus the
load-bearing anti-mush rule: strict `target_kind` enum so closure /
consequence / gap / killed cannot be laundered into one success word.

Schema: analytics/public/ledgers/forward_evidence/forward_evidence_schema.md
Exit 0 if all rows valid, 1 otherwise.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEDGER = REPO / "analytics/public/ledgers/forward_evidence/forward_evidence_ledger.jsonl"

REQUIRED = ["row_id", "claim", "target_kind", "source_artifact",
            "attempt_trace", "result", "evidence_pointer",
            "anti_pattern_audit", "author_agent", "ratifier_identity",
            "status", "created_at"]
TARGET_KINDS = {"proof_closure", "consequence_exposure", "gap_isolation",
                "falsifier", "route_reduction", "apparatus_audit"}
RESULTS = {"achieved", "not_achieved", "partial", "inconclusive"}
STATUSES = {"pending_ratification", "ratified", "retired"}
ROW_RE = re.compile(r"^FE-\d{4}-\d{2}-\d{2}-\d{2,}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def validate_row(r: dict, ln: int) -> list[str]:
    rid = r.get("row_id", f"<line {ln}>")
    e: list[str] = []
    for f in REQUIRED:
        if f not in r or r[f] in (None, ""):
            e.append(f"{rid}: missing/empty required field '{f}'")
    if e:
        return e
    if not ROW_RE.match(r["row_id"]):
        e.append(f"{rid}: row_id not FE-YYYY-MM-DD-NN")
    if r["target_kind"] not in TARGET_KINDS:
        e.append(f"{rid}: target_kind '{r['target_kind']}' not in {sorted(TARGET_KINDS)}")
    if r["result"] not in RESULTS:
        e.append(f"{rid}: result '{r['result']}' not in {sorted(RESULTS)}")
    if r["status"] not in STATUSES:
        e.append(f"{rid}: status '{r['status']}' not in {sorted(STATUSES)}")
    # Independence (SOX §1220 analog)
    if r["author_agent"] == r["ratifier_identity"]:
        e.append(f"{rid}: author_agent == ratifier_identity — independence violation")
    if r["ratifier_identity"] == "pending" and r["status"] != "pending_ratification":
        e.append(f"{rid}: ratifier_identity='pending' requires status='pending_ratification'")
    if r["status"] == "ratified" and r["ratifier_identity"] in ("pending", r["author_agent"]):
        e.append(f"{rid}: status='ratified' requires an independent ratifier_identity")
    # xpanel ratification (no external human; 2026-05-16). Guards so it is
    # genuine independence, not self-review. See schema "Independent
    # ratification without an external human".
    if r.get("status") == "ratified":
        ev = r.get("ratification_evidence")
        if not isinstance(ev, dict):
            e.append(f"{rid}: status='ratified' requires ratification_evidence object")
        else:
            mode = ev.get("mode")
            if mode == "xpanel":
                provs = ev.get("providers") or []
                if not ev.get("steelman_first"):
                    e.append(f"{rid}: xpanel ratification requires steelman_first=true (RC-B)")
                if not (len(provs) >= 2 or ev.get("operator_inversion") is True):
                    e.append(f"{rid}: xpanel requires >=2 independent providers OR operator_inversion=true")
                author_prov = str(r["author_agent"]).split(":")[0]
                if any(author_prov and author_prov in str(p) for p in provs):
                    e.append(f"{rid}: xpanel provider overlaps author provider '{author_prov}' — not independent")
                if r.get("target_kind") == "proof_closure" and ev.get("operator_inversion") is not True:
                    e.append(f"{rid}: proof_closure xpanel ratification requires operator_inversion=true "
                             "(xpanel scope is discipline+reproducibility, NOT idea-truth — AP-014 RC-A)")
                if ev.get("scope") not in ("discipline_and_reproducibility", "discipline_only"):
                    e.append(f"{rid}: xpanel ratification_evidence.scope must be explicit "
                             "(discipline_and_reproducibility | discipline_only) — never idea-truth")
    # Anti-mush: only proof_closure may co-occur with a 'closed/closure' claim
    if r["target_kind"] != "proof_closure" and re.search(
            r"\bclos(e|ed|ure)\b", str(r["claim"]), re.I):
        e.append(f"{rid}: non-proof_closure target_kind but claim says 'closed/closure' "
                 "(mushy-vocabulary violation — restate as consequence/gap/route_reduction)")
    # Path retention (§1215)
    for f in ("source_artifact", "evidence_pointer"):
        if not (REPO / r[f]).exists():
            e.append(f"{rid}: {f} path does not exist: {r[f]}")
    if r["attempt_trace"] != "none" and not (REPO / r["attempt_trace"]).exists():
        e.append(f"{rid}: attempt_trace path does not exist: {r['attempt_trace']}")
    if not ISO_RE.match(str(r["created_at"])):
        e.append(f"{rid}: created_at not ISO 8601")
    return e


def main() -> int:
    if not LEDGER.exists():
        print(f"FATAL: ledger not found at {LEDGER}", file=sys.stderr)
        return 1
    rows, errs, ids = [], [], {}
    for ln, raw in enumerate(LEDGER.read_text().splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            r = json.loads(raw)
        except json.JSONDecodeError as ex:
            errs.append(f"line {ln}: JSON parse error: {ex}")
            continue
        rows.append(r)
        rid = r.get("row_id", f"<line {ln}>")
        if rid in ids:
            errs.append(f"{rid}: duplicate row_id (also line {ids[rid]})")
        else:
            ids[rid] = ln
        errs.extend(validate_row(r, ln))

    by_kind = {}
    for r in rows:
        by_kind[r.get("target_kind")] = by_kind.get(r.get("target_kind"), 0) + 1
    real_closures = sum(
        1 for r in rows
        if r.get("target_kind") == "proof_closure"
        and r.get("result") == "achieved"
        and r.get("status") == "ratified")

    print("=== forward_evidence_ledger.jsonl validation ===")
    print(f"Path: {LEDGER}")
    print(f"Total rows: {len(rows)}")
    print(f"By target_kind: {by_kind}")
    print(f"REAL closures (proof_closure + achieved + ratified): {real_closures}")
    print()
    if errs:
        print(f"FAIL — {len(errs)} error(s):")
        for x in errs:
            print(f"  - {x}")
        return 1
    print("OK — all forward-evidence rows valid (clean corpus).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
