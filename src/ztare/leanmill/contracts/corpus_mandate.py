"""Corpus mandate registry — typed contract.

A mandate is a typed declaration of (corpus_path × lane_eligibility ×
anti_laundering_rule × credit_lanes_allowed). Mandates ROUTE work; the
governance + strict-C credit gates DECIDE credit. A mandate listed here
does NOT grant credit; it only declares which lanes may consume the corpus
and what anti-laundering rule applies.

The registry is the typed source of truth. The legacy seed plan field
`active_corpus_paths` is a derived projection over mandates active for the
`source_scout` lane. Workers that need to know "which mandate sourced this
row" should call `mandate_for_corpus_path()`.

Files:
- registry JSON: analytics/public/leanmill/dashboard_data/corpus_mandates.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = [
    "REGISTRY_PATH",
    "VALID_STATUSES",
    "VALID_LANES",
    "VALID_CREDIT_LANES",
    "read_registry",
    "active_mandates",
    "active_corpus_paths",
    "mandate_for_corpus_path",
    "mandate_by_id",
    "validate_registry",
]

# Resolve repo root from this file's location: src/ztare/leanmill/contracts/corpus_mandate.py
_REPO = Path(__file__).resolve().parents[4]
REGISTRY_PATH = _REPO / "analytics/public/leanmill/dashboard_data/corpus_mandates.json"

VALID_STATUSES = {"active", "calibration_only", "deprecated", "draft"}
VALID_LANES = {
    "source_scout",
    "source_binding_probe",
    "solver_lane",
    "family_birth",
    "static_sweep_calibration",
}
VALID_CREDIT_LANES = {"strict_c", "calibration_only", "audit_only"}


def read_registry(path: Path | None = None) -> dict[str, Any]:
    p = Path(path) if path is not None else REGISTRY_PATH
    if not p.exists():
        raise FileNotFoundError(f"corpus_mandates.json not found at {p}")
    return json.loads(p.read_text())


def active_mandates(lane: str, path: Path | None = None) -> list[dict[str, Any]]:
    """Return mandates with status='active' that include `lane` in lane_eligibility."""
    if lane not in VALID_LANES:
        raise ValueError(f"unknown lane: {lane!r}; valid: {sorted(VALID_LANES)}")
    reg = read_registry(path)
    return [
        m
        for m in reg.get("mandates", [])
        if m.get("status") == "active" and lane in (m.get("lane_eligibility") or [])
    ]


def active_corpus_paths(lane: str, path: Path | None = None) -> list[str]:
    """Derived: the corpus_path list for active mandates on `lane`. Used to
    regenerate the legacy `active_corpus_paths` field in the seed plan."""
    return [m["corpus_path"] for m in active_mandates(lane, path)]


def active_solver_slice_pair(path: Path | None = None) -> tuple[str, str] | None:
    """Derived: (slice_path, row_context_path) of the active mandate registered
    for the solver_lane. The solver_lane_worker calls this instead of carrying
    hardcoded slice constants — adding another mandate is a registry edit, not
    a code change.

    Returns the first active mandate that declares solver_lane in
    lane_eligibility AND carries both solver_lane_slice_path and
    solver_lane_row_context_path. Returns None if no active mandate is
    materialized for the solver lane.
    """
    for m in active_mandates("solver_lane", path):
        s = m.get("solver_lane_slice_path")
        c = m.get("solver_lane_row_context_path")
        if s and c:
            return (s, c)
    return None


def mandate_for_corpus_path(corpus_path: str, path: Path | None = None) -> dict[str, Any] | None:
    reg = read_registry(path)
    for m in reg.get("mandates", []):
        if m.get("corpus_path") == corpus_path:
            return m
    return None


def mandate_by_id(mandate_id: str, path: Path | None = None) -> dict[str, Any] | None:
    reg = read_registry(path)
    for m in reg.get("mandates", []):
        if m.get("mandate_id") == mandate_id:
            return m
    return None


def validate_registry(reg: dict[str, Any]) -> list[str]:
    """Return a list of error messages. Empty = valid."""
    errors: list[str] = []
    if reg.get("schema") != "corpus_mandate_registry_v1":
        errors.append(f"unexpected schema: {reg.get('schema')!r}")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for i, m in enumerate(reg.get("mandates", []) or []):
        ctx = f"mandate[{i}] {m.get('mandate_id', '?')}"
        mid = m.get("mandate_id")
        if not mid or not isinstance(mid, str):
            errors.append(f"{ctx}: missing/invalid mandate_id")
        elif mid in seen_ids:
            errors.append(f"{ctx}: duplicate mandate_id {mid!r}")
        else:
            seen_ids.add(mid)
        cpath = m.get("corpus_path")
        if not cpath:
            errors.append(f"{ctx}: missing corpus_path")
        elif cpath in seen_paths:
            errors.append(f"{ctx}: duplicate corpus_path {cpath!r}")
        else:
            seen_paths.add(cpath)
        status = m.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"{ctx}: status={status!r} not in {sorted(VALID_STATUSES)}")
        for lane in m.get("lane_eligibility") or []:
            if lane not in VALID_LANES:
                errors.append(f"{ctx}: lane_eligibility contains unknown lane {lane!r}")
        for cl in m.get("credit_lanes_allowed") or []:
            if cl not in VALID_CREDIT_LANES:
                errors.append(f"{ctx}: credit_lanes_allowed contains unknown {cl!r}")
        if not m.get("anti_laundering_rule"):
            errors.append(f"{ctx}: missing anti_laundering_rule")
    return errors


def _self_test() -> int:
    """Validate the registry on disk and exercise the API."""
    try:
        reg = read_registry()
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}")
        return 1
    errors = validate_registry(reg)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1
    src_scout = active_mandates("source_scout")
    paths = active_corpus_paths("source_scout")
    if len(paths) != len(src_scout):
        print(f"FAIL: active_corpus_paths/active_mandates length mismatch")
        return 1
    # Round-trip: mandate_for_corpus_path on each active path
    for p in paths:
        m = mandate_for_corpus_path(p)
        if m is None:
            print(f"FAIL: mandate_for_corpus_path({p!r}) returned None")
            return 1
    print(
        f"PASS: registry valid, mandates_total={len(reg.get('mandates', []))}, "
        f"active_source_scout={len(src_scout)}"
    )
    for m in src_scout:
        print(f"  active source_scout mandate: {m['mandate_id']}  rows={m.get('row_count')}")
    return 0


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    print("usage: python -m ztare.leanmill.contracts.corpus_mandate --self-test")
    sys.exit(2)
