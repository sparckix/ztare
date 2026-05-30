#!/usr/bin/env python3
"""CLI for PATTERN-012 prediction-ledger logging decisions."""
from __future__ import annotations

import argparse

from src.ztare.research_director.prediction_logging_discriminator import (
    decide_prediction_logging,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--action-kind", required=True,
                    help="e.g. agent_dispatch, external_dispatch, promote, prioritization, housekeeping")
    ap.add_argument("--gates-typed-action", action="store_true")
    ap.add_argument("--outcome-not-observable", action="store_true")
    ap.add_argument("--cost-usd", type=float, default=0.0)
    ap.add_argument("--agent-count", type=int, default=1)
    args = ap.parse_args()

    decision = decide_prediction_logging(
        action_kind=args.action_kind,
        gates_typed_action=args.gates_typed_action,
        outcome_observable=not args.outcome_not_observable,
        cost_usd=args.cost_usd,
        agent_count=args.agent_count,
    )
    print(f"tier={decision.tier}")
    print(f"must_log={decision.must_log}")
    print(f"should_log={decision.should_log}")
    print(f"reason={decision.reason}")
    print(f"anti_gaming_note={decision.anti_gaming_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
