"""GP-215 acceptance ledger + scope-limit + lift display.

The discipline that prevents "meta solver for any problem" overclaiming. The
matcher cannot honestly claim to be a meta solver until its recommendations
are empirically calibrated against operator behavior. This module makes that
calibration measurable:

  1. Every matcher recommendation gets a record in the ledger
  2. When the operator either acts on it or doesn't, that action is logged
  3. After N records, the lift over modal-baseline is computed
  4. The current accept rate appears in every output

Until the ledger has data, the matcher's outputs include a scope-limit
disclaimer that names exactly what is and is not validated.

Three CLIs:
  ledger-record     — operator-recorded acceptance/rejection of a recommendation
  ledger-score      — compute current accept rate, modal-baseline lift,
                      per-substrate accuracy
  scope-limit       — emits the standard scope-limit string used in matcher
                      outputs; importable as a constant
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
LEDGER_PATH = REPO_ROOT / "analytics" / "queries" / "meta_arc_acceptance_ledger.jsonl"


# ---------------- The scope-limit string -----------------------------------
#
# Updated when the catalog is broadened. Every matcher output includes this.
# Operators reading any matcher recommendation should be able to see — at
# the moment of decision — exactly what has been validated and what has not.

SCOPE_LIMIT_VERSION = "2026-05-04"

SCOPE_LIMIT_STRING = """**Scope-limit disclosure (v2026-05-04)** — the matcher catalog is what it is:

- **Domain:** ZTARE adversarial-verification substrates only. NOT validated for: software engineering, drug discovery, policy, or any non-research domain.
- **Catalog size:** 40 cycles across 3 substrates (NS Track B 22 + AQUAL gp163d 9 + Neural gp140 9).
- **Substrate coverage:** 1 proof-bound substrate (NS), 2 apparatus-bound substrates (AQUAL + Neural). Cross-substrate transfer evidence is partial.
- **Empirical operator-acceptance data:** {acceptance_summary}
- **The matcher is not validated to provide differential signal across distinct candidates** at this catalog size. Treat its recommendations as advisory annotations on BRIDGE-1's rationale, not as a substrate-routing signal.
- **Path forward to a wider claim:** mine a second proof-bound substrate (paper 7 or 8 arc) AND accumulate ≥ 30 ledger entries with stable lift over modal baseline. Until then, the headline "meta solver" claim is overstated for what's shipped."""


# ---------------- Ledger model ---------------------------------------------


@dataclass
class LedgerEntry:
    """One matcher recommendation + the operator's eventual action on it."""

    recommendation_id: str   # ULID-like, generated at recommendation time
    timestamp_iso: str
    stall_text: str
    catalog_version: str     # for replay; bumps when catalog changes
    top1_move_id: str
    top1_cluster_id: str
    top1_source_substrate: str
    top1_cosine_raw: float
    adversary_move_id: str | None
    saturation_flag: bool
    modal_share: float       # for modal-baseline comparison
    # Operator action — filled in later via record_action()
    operator_action: str | None = None        # "accepted" | "rejected" | "modified" | "ignored"
    operator_outcome: str | None = None       # "worked" | "failed" | "in_progress" | None
    operator_notes: str | None = None
    action_timestamp_iso: str | None = None


# ---------------- Ledger I/O -----------------------------------------------


def append_ledger(entry: LedgerEntry) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry)) + "\n")


def load_ledger() -> list[LedgerEntry]:
    if not LEDGER_PATH.is_file():
        return []
    out: list[LedgerEntry] = []
    with LEDGER_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                out.append(LedgerEntry(**d))
            except Exception:
                continue
    return out


def update_ledger_action(
    recommendation_id: str,
    *,
    action: str,
    outcome: str | None = None,
    notes: str | None = None,
) -> bool:
    """Update an existing ledger entry with the operator's action. Rewrites
    the file (acceptable at this scale)."""
    entries = load_ledger()
    found = False
    for e in entries:
        if e.recommendation_id == recommendation_id:
            e.operator_action = action
            e.operator_outcome = outcome
            e.operator_notes = notes
            e.action_timestamp_iso = datetime.now(timezone.utc).isoformat()
            found = True
            break
    if not found:
        return False
    LEDGER_PATH.write_text("\n".join(json.dumps(asdict(e)) for e in entries) + "\n")
    return True


# ---------------- Acceptance summary (used in scope-limit string) ----------


def acceptance_summary() -> str:
    entries = load_ledger()
    if not entries:
        return "0 ledger entries — system not yet calibrated."
    n_total = len(entries)
    n_actioned = sum(1 for e in entries if e.operator_action)
    n_accepted = sum(1 for e in entries if e.operator_action == "accepted")
    n_rejected = sum(1 for e in entries if e.operator_action == "rejected")
    n_modified = sum(1 for e in entries if e.operator_action == "modified")
    n_worked = sum(1 for e in entries if e.operator_outcome == "worked")
    n_failed = sum(1 for e in entries if e.operator_outcome == "failed")
    if n_actioned == 0:
        return f"{n_total} recommendations issued; none yet actioned by operator."
    accept_rate = n_accepted / n_actioned
    return (
        f"{n_total} recommendations issued; {n_actioned} actioned "
        f"(accepted {n_accepted}, modified {n_modified}, rejected {n_rejected}); "
        f"of accepted: {n_worked} worked, {n_failed} failed. "
        f"Current operator-acceptance rate: {accept_rate:.0%}."
    )


def current_scope_limit() -> str:
    return SCOPE_LIMIT_STRING.format(acceptance_summary=acceptance_summary())


# ---------------- Lift score ------------------------------------------------


def compute_lift_score() -> dict[str, Any]:
    """Compute the matcher's lift over modal baseline. The honest version.

    For each ledger entry where the operator accepted the matcher's top-1 AND
    the outcome is known, count it as a hit. Compare to the modal baseline,
    which would have predicted the modal cluster every time. Without
    ledger-level ground truth on which substrate was the right move, this
    metric is partial — but it is the right shape and updates as data
    accumulates."""
    entries = load_ledger()
    n = len(entries)
    if n == 0:
        return {
            "n_entries": 0,
            "matcher_top1_accept_rate": None,
            "modal_baseline_estimate": None,
            "lift_estimate": None,
            "notes": "No ledger entries. The matcher cannot yet claim differential signal.",
        }

    actioned = [e for e in entries if e.operator_action]
    if not actioned:
        return {
            "n_entries": n,
            "n_actioned": 0,
            "matcher_top1_accept_rate": None,
            "modal_baseline_estimate": None,
            "lift_estimate": None,
            "notes": f"{n} recommendations issued, none actioned. Score one of: ledger-record --recommendation-id <id> --action accepted|rejected|modified",
        }
    accepted = [e for e in actioned if e.operator_action == "accepted"]
    accept_rate = len(accepted) / len(actioned)

    # Modal baseline estimate: assume the top-1 was the modal cluster's match.
    # If saturation_flag was set, the matcher refused — those entries don't
    # count in lift since the matcher made no positive claim.
    non_saturated = [e for e in actioned if not e.saturation_flag]
    if not non_saturated:
        modal_baseline = None
        lift = None
    else:
        # Approximate modal baseline by mean modal_share across recommendations.
        # If modal_share is 0.4, a chance-by-modal classifier would accept ~40% of
        # the time on average. (Honest under-estimate; the real baseline depends
        # on how many distinct clusters the operator is choosing among.)
        modal_baseline = sum(e.modal_share for e in non_saturated) / len(non_saturated)
        lift = accept_rate - modal_baseline

    return {
        "n_entries": n,
        "n_actioned": len(actioned),
        "matcher_top1_accept_rate": round(accept_rate, 3),
        "modal_baseline_estimate": round(modal_baseline, 3) if modal_baseline is not None else None,
        "lift_estimate": round(lift, 3) if lift is not None else None,
        "n_accepted": sum(1 for e in actioned if e.operator_action == "accepted"),
        "n_rejected": sum(1 for e in actioned if e.operator_action == "rejected"),
        "n_modified": sum(1 for e in actioned if e.operator_action == "modified"),
        "n_saturation_correctly_refused": sum(1 for e in actioned if e.saturation_flag),
        "notes": (
            "Lift > 0 means the matcher beats 'always predict modal cluster'. "
            "Lift ≈ 0 means the matcher is at parity — a wrapper around modal. "
            "Lift < 0 means the matcher is worse than always-predict-modal — "
            "negative information; should not be used."
        ),
    }


# ---------------- CLI -------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ztare.research_director.meta_arc_acceptance")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_record = sub.add_parser("record", help="Record operator action on a previously-issued recommendation")
    p_record.add_argument("--recommendation-id", required=True)
    p_record.add_argument("--action", required=True, choices=["accepted", "rejected", "modified", "ignored"])
    p_record.add_argument("--outcome", choices=["worked", "failed", "in_progress"], default=None)
    p_record.add_argument("--notes", default=None)

    sub.add_parser("score", help="Compute current accept rate + modal-baseline lift")

    sub.add_parser("scope-limit", help="Print the standard scope-limit disclosure string")

    sub.add_parser("ledger-summary", help="Print summary of the ledger")

    args = parser.parse_args(argv)

    if args.cmd == "record":
        ok = update_ledger_action(
            args.recommendation_id,
            action=args.action,
            outcome=args.outcome,
            notes=args.notes,
        )
        if ok:
            print(f"Updated {args.recommendation_id}: action={args.action}")
        else:
            print(f"Recommendation id not found: {args.recommendation_id}")
            return 1
        return 0

    if args.cmd == "score":
        result = compute_lift_score()
        print(json.dumps(result, indent=2))
        return 0

    if args.cmd == "scope-limit":
        print(current_scope_limit())
        return 0

    if args.cmd == "ledger-summary":
        entries = load_ledger()
        print(f"Total entries: {len(entries)}")
        print(acceptance_summary())
        if entries:
            print("\nMost recent 5:")
            for e in entries[-5:]:
                action = e.operator_action or "(no action yet)"
                print(f"  {e.recommendation_id} {e.timestamp_iso[:10]} → {e.top1_move_id} → {action}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
