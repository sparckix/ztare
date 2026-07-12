"""Adapter-Width Law — measure and receipt the interface breadth of a substrate adapter.

The Adapter-Width Law (AWL):
  An adapter's interface IS the machine-readable enumeration of every abduction
  outsourced to humans ("givens").  Generality = the ordered DELETION of adapter
  fields, each replaced by an abduction organ + validation receipt.

Width = number of fields still at status "given".  A field graduates when its
abduction organ exists AND a validation receipt confirms it.

Analytics written to analytics/public/adapter_width/<substrate>.json
(repo-level metric; persists across workspaces).

CLI:
  python -m ztare.common.adapter_width --declare-worldmodel
  python -m ztare.common.adapter_width --report <substrate>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical field registry
# ---------------------------------------------------------------------------

ADAPTER_FIELDS: dict[str, str] = {
    "variables": (
        "The substrate's state vocabulary: named objects, spatial roles, counters,"
        " or regions that a transition law T(s,a)->s' must reference."
    ),
    "actions": (
        "The discrete action alphabet available to the agent at each step."
    ),
    "success_signal": (
        "The substrate-provided reward or success indicator (score, level flag,"
        " termination condition) used to define the win condition."
    ),
    "reset_semantics": (
        "The rules governing episode reset: what state is wiped, what persists,"
        " and whether the reset is deterministic and history-free."
    ),
    "time_structure": (
        "The temporal indexing scheme: whether time is a discrete integer, a"
        " phase-derived counter, or a substrate-provided clock."
    ),
    "observability": (
        "The extent to which the agent can see the full state vs a partial"
        " projection; includes hidden-state assumptions."
    ),
    "verification_oracle": (
        "The gate battery that certifies a candidate law (replay, holdout,"
        " terminal-event witness); hand-designed or formally derived."
    ),
}

_VALID_STATUSES = {"given", "abduced_candidate", "abduced_validated"}

# ---------------------------------------------------------------------------
# Ledger path
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LEDGER_DIR = _REPO_ROOT / "analytics" / "public" / "adapter_width"


def _ledger_path(substrate: str) -> Path:
    _LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    return _LEDGER_DIR / f"{substrate}.json"


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


def declare_adapter_contract(substrate: str, fields: dict[str, dict]) -> dict:
    """Validate and persist an adapter contract for *substrate*.

    *fields* maps each canonical field name to a descriptor dict with keys:
      status      : "given" | "abduced_candidate" | "abduced_validated"
      supplied_by : str   (who/what provides this when status=="given")
      abduced_by  : str | None
      validated_by: str | None  (receipt ref; required when abduced_validated)
      note        : str | None  (optional annotation)

    Raises ValueError on unknown fields, missing canonical fields, or bad status.
    Writes/updates analytics/public/adapter_width/<substrate>.json.
    Returns the written entry.
    """
    unknown = set(fields) - set(ADAPTER_FIELDS)
    if unknown:
        raise ValueError(f"Unknown adapter fields: {sorted(unknown)}")
    missing = set(ADAPTER_FIELDS) - set(fields)
    if missing:
        raise ValueError(f"Missing canonical fields: {sorted(missing)}")

    for fname, desc in fields.items():
        status = desc.get("status")
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"Field '{fname}' has invalid status '{status}'."
                f" Must be one of {sorted(_VALID_STATUSES)}."
            )
        if status == "abduced_validated" and not desc.get("validated_by"):
            raise ValueError(
                f"Field '{fname}' is abduced_validated but lacks 'validated_by' receipt ref."
            )

    entry = {
        "substrate": substrate,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": fields,
        "width": sum(1 for d in fields.values() if d.get("status") == "given"),
        "total": len(ADAPTER_FIELDS),
    }

    path = _ledger_path(substrate)
    history: list[dict] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text())
            history = existing.get("history", [])
        except (json.JSONDecodeError, KeyError):
            history = []

    history.append(entry)
    ledger = {"substrate": substrate, "latest": entry, "history": history}
    path.write_text(json.dumps(ledger, indent=2))
    return entry


def adapter_width(substrate: str) -> dict:
    """Return width metrics for *substrate* from the persisted ledger.

    Returns:
      {width, total, fields, trend: [list of historical widths]}
    Raises FileNotFoundError if no contract has been declared.
    """
    path = _ledger_path(substrate)
    if not path.exists():
        raise FileNotFoundError(
            f"No adapter contract found for '{substrate}' at {path}."
            " Run declare_adapter_contract() first."
        )
    ledger = json.loads(path.read_text())
    latest = ledger["latest"]
    trend = [h["width"] for h in ledger.get("history", [])]
    return {
        "width": latest["width"],
        "total": latest["total"],
        "fields": latest["fields"],
        "trend": trend,
    }


# ---------------------------------------------------------------------------
# WORLDMODEL declaration (arc3 / GP-250)
# ---------------------------------------------------------------------------


def _variables_status() -> dict:
    """Honest variables status: given always; abduced_candidate if causal_objects.jsonl exists."""
    causal_objects = (
        _REPO_ROOT / "projects" / "arc3_ls20_gov" / "workspace" / "causal_objects.jsonl"
    )
    if causal_objects.exists():
        # causal_compiler v1 has produced candidates — not yet validated.
        return {
            "status": "abduced_candidate",
            "supplied_by": "ArcAgi3Adapter grid + hand-authored roles/regions",
            "abduced_by": "causal_compiler v1 (projects/arc3_ls20_gov/workspace/causal_objects.jsonl)",
            "validated_by": None,
            "note": (
                "causal_objects.jsonl exists at run-time: causal_compiler v1 has produced"
                " variable candidates. Status upgraded from 'given' to 'abduced_candidate'."
                " Remains abduced_candidate until a validation receipt is registered."
            ),
        }
    return {
        "status": "given",
        "supplied_by": "ArcAgi3Adapter grid + hand-authored roles/regions",
        "abduced_by": None,
        "validated_by": None,
        "note": "causal_objects.jsonl not found at run-time; no abduction organ confirmed.",
    }


def declare_worldmodel() -> dict:
    """Declare the GP-250 worldmodel adapter contract and return the ledger entry.

    This is the honest baseline.  Expected initial width: 6/7 or 7/7 depending
    on whether causal_objects.jsonl is present at run-time (variables may be
    abduced_candidate rather than given).
    """
    fields: dict[str, dict] = {
        "variables": _variables_status(),
        "actions": {
            "status": "given",
            "supplied_by": "ArcAgi3Adapter — 4 discrete actions (up/down/left/right)",
            "abduced_by": None,
            "validated_by": None,
            "note": None,
        },
        "success_signal": {
            "status": "given",
            "supplied_by": "ARC-AGI-3 adapter level/score field",
            "abduced_by": None,
            "validated_by": None,
            "note": None,
        },
        "reset_semantics": {
            "status": "given",
            "supplied_by": "ARC-AGI-3 adapter reset call",
            "abduced_by": None,
            "validated_by": None,
            "note": (
                "Reset-invariance is UNTESTED (cold-review finding 6): episode boundary"
                " is a causal identity only after reset-invariance tests confirm the physics"
                " resets cleanly rather than carrying hidden state across lives."
            ),
        },
        "time_structure": {
            "status": "given",
            "supplied_by": "t integer from adapter; lawful_time declared in kernel",
            "abduced_by": None,
            "validated_by": None,
            "note": None,
        },
        "observability": {
            "status": "given",
            "supplied_by": "full-grid assumption (ArcAgi3Adapter grid observation)",
            "abduced_by": None,
            "validated_by": None,
            "note": "Full observability assumed; partial-observability not tested.",
        },
        "verification_oracle": {
            "status": "given",
            "supplied_by": "replay/holdout gates hand-designed in governed_verification.py",
            "abduced_by": None,
            "validated_by": None,
            "note": None,
        },
    }
    return declare_adapter_contract("worldmodel", fields)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Adapter-Width Law — declare or report adapter interface width."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--declare-worldmodel",
        action="store_true",
        help="Declare the GP-250 worldmodel adapter contract.",
    )
    group.add_argument(
        "--report",
        metavar="SUBSTRATE",
        help="Print the current width report for SUBSTRATE.",
    )
    args = parser.parse_args()

    if args.declare_worldmodel:
        entry = declare_worldmodel()
        print(json.dumps(entry, indent=2))
    else:
        try:
            report = adapter_width(args.report)
            print(json.dumps(report, indent=2))
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    _cli()
