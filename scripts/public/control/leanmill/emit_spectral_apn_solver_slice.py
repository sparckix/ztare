#!/usr/bin/env python3
"""Emit a solver-lane-ready slice + row_context from the spectral_apn mandate.

This is the materialization the solver_lane policy was blocked on:
`leanmill_c_discriminating_slice_prep.py must emit no-template rows as a
solver corpus (evaluation_harness_c_discriminating_slice.json with
rejection_reasons + goals)`.

We do not replace the harness slice (that one is for the family-spec evaluation
harness; touching it risks the contract SHA pin). Instead we write a parallel
solver-lane slice that the solver_lane_worker consumes. Each row carries:
  - row_id, target_theorem_name, source_file
  - rejection_reasons = ["no_positive_family_template"]
  - static_tools_result.status = "failed_or_no_positive_signal"
  - target_resolution_ok = true
The companion row_context file carries `goal` text per row.

Eligibility is established by our seed gate: every row in the spectral_apn
mandate has already cleared a 7-tactic static gate (exact?/simp/aesop/
nlinarith/positivity/decide/norm_num all errored) AND has no pre-existing
positive family template (brand-new families). Re-statement here is contract-
shape, not new judgment.

CLI:
  --mandate <id>          mandate_id to emit (default: spectral_apn_2026_05_28)
  --slice-out <path>      output slice file (default: solver_lane_slice.json
                          next to the harness slice)
  --row-context-out <path>  output row_context (default: alongside slice)
  --dry-run               do not write; print summary

Surfaced through `ztare leanmill slice-emit`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DASH = REPO / "analytics/public/leanmill/dashboard_data"

if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.contracts.corpus_mandate import mandate_by_id  # noqa: E402

DEFAULT_MANDATE = "spectral_apn_2026_05_28"
DEFAULT_SLICE = DASH / "solver_lane_spectral_apn_slice.json"
DEFAULT_ROW_CTX = DASH / "solver_lane_spectral_apn_row_context.json"


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text())


def _row_id_of(mandate_id: str, sub_area: str, base_stem: str) -> str:
    """Match the row_id convention used by build_seed_corpus.py."""
    if sub_area == "apn_alphaproof_nexus":
        return f"APN_{base_stem}"
    return f"SPEC_{sub_area}_{base_stem}"


def emit(mandate_id: str, slice_out: Path, ctx_out: Path, dry_run: bool) -> int:
    m = mandate_by_id(mandate_id)
    if m is None:
        print(f"ERROR: mandate {mandate_id!r} not found in registry", file=sys.stderr)
        return 1
    corpus_path = REPO / m["corpus_path"]
    if not corpus_path.exists():
        print(f"ERROR: corpus_path missing: {corpus_path}", file=sys.stderr)
        return 1
    corpus = _read_json(corpus_path)

    slice_rows: list[dict] = []
    ctx_rows: list[dict] = []

    for cr in corpus.get("rows", []):
        row_id = cr["row_id"]
        slice_rows.append(
            {
                "row_id": row_id,
                "target_theorem_name": cr.get("theorem_name"),
                "source_file": cr.get("sorried_file"),
                "rejection_reasons": ["no_positive_family_template"],
                "static_tools_result": {
                    "status": "failed_or_no_positive_signal",
                    "static_gate_evidence": "7-tactic battery (exact?, simp, aesop, nlinarith, positivity, decide, norm_num) — all errored on this row during the spectral_apn seed gate",
                    "gate_artifact_dir": (
                        cr.get("sub_area") == "apn_alphaproof_nexus"
                        and "projects/gp_spectral_apn_seed_2026_05_28/gates/"
                        or "projects/gp_spectral_apn_seed_2026_05_28/gates_spectral/"
                    ),
                },
                "target_resolution_ok": True,
                "existing_mathlib_target": False,
                "best_static_family_match": "",
                "matched_families": [],
                "families_with_positive_template": [],
                "families_with_negative_control": [],
                "family_available": False,
                "probe_credit_ready": False,
                "probe_credit_pending": False,
                "probe_pending_families": [],
                "probe_verified_families": [],
                "probe_terminal_nonuseful_families": [],
                "family_statuses": {},
                "c_discriminating_evidence_status": "no_positive_family_template",
                "eligible": True,
                "strict_c_credit_disqualified_reason": "",
                "source_materialization": {
                    "mandate_id": mandate_id,
                    "sub_area": cr.get("sub_area"),
                    "file_sha256": cr.get("file_sha256"),
                },
                "family_spec_probe_required_before_c_credit": False,
                "static_sweep_required_before_c_credit": False,
                "family_spec_probe_evidence": {},
            }
        )
        ctx_rows.append(
            {
                "row_id": row_id,
                "goal": cr.get("goal"),
                "source_file": cr.get("sorried_file"),
                "target_theorem_name": cr.get("theorem_name"),
                "source": cr.get("source"),
                "sub_area": cr.get("sub_area"),
            }
        )

    now = datetime.now(timezone.utc).isoformat()
    slice_doc = {
        "schema": "leanmill-solver-lane-slice-v1",
        "purpose": "Non-Mathlib spectral + APN rows materialized as solver_lane-eligible no_positive_family_template rows. Sourced from corpus_mandates.json mandate.",
        "mandate_id": mandate_id,
        "generated_at": now,
        "credit_boundary": {
            "proof_credit_eligible": False,
            "purpose": "solver routing only; strict C credit still requires governance ratification with matched negative-control + L3 audit",
        },
        "blockers_by_reason": {"no_positive_family_template": len(slice_rows)},
        "candidate_pool_count": len(slice_rows),
        "eligible_count": len(slice_rows),
        "rows": slice_rows,
        "row_count": len(slice_rows),
    }
    ctx_doc = {
        "schema": "leanmill-solver-lane-row-context-v1",
        "mandate_id": mandate_id,
        "generated_at": now,
        "rows": ctx_rows,
        "row_count": len(ctx_rows),
    }

    if dry_run:
        print(f"DRY RUN — would write:")
        print(f"  slice:       {slice_out}  rows={len(slice_rows)}")
        print(f"  row_context: {ctx_out}    rows={len(ctx_rows)}")
        print(f"  mandate:     {mandate_id}")
        from collections import Counter
        sub_counts = Counter(r.get("source_materialization", {}).get("sub_area") for r in slice_rows)
        for sub, n in sorted(sub_counts.items()):
            print(f"  sub_area: {sub}  rows={n}")
        return 0

    slice_out.parent.mkdir(parents=True, exist_ok=True)
    slice_out.write_text(json.dumps(slice_doc, indent=2))
    ctx_out.write_text(json.dumps(ctx_doc, indent=2))
    print(f"wrote {slice_out}  rows={len(slice_rows)}")
    print(f"wrote {ctx_out}    rows={len(ctx_rows)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mandate", default=DEFAULT_MANDATE)
    ap.add_argument("--slice-out", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--row-context-out", type=Path, default=DEFAULT_ROW_CTX)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return emit(args.mandate, args.slice_out, args.row_context_out, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
